import os
import json
import time
import uuid
from typing import Dict, Any
from datetime import datetime

from ..engines.base import JudgeResult
from ..engines.mock_adapter import MockEngine
from ..engines.ollama_adapter import OllamaAdapter
from ..engines.hf_adapter import HuggingFaceAdapter
from ..metrics import registry as metrics_registry
from ..db.session import SessionLocal, init_db
from ..db.models import Job as DBJob, CaseResult

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
RESULTS_DIR = os.path.join(DATA_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def load_engine_from_selector(selector: Dict[str, Any]):
    """selector can be a string or dict: {primary: 'mock', fallbacks: []} or {'primary':'ollama:llama2'}"""
    primary = selector.get("primary") if isinstance(selector, dict) else selector
    if isinstance(primary, str):
        if primary.startswith("ollama") or primary.startswith("ollama:"):
            # allow formats: 'ollama' or 'ollama:llama2' or dict config
            parts = primary.split(":", 1)
            model = parts[1] if len(parts) > 1 else "llama"
            return OllamaAdapter({"model": model})
        if primary.startswith("hf") or primary.startswith("hf:"):
            parts = primary.split(":", 1)
            model = parts[1] if len(parts) > 1 else "mistral"
            return HuggingFaceAdapter({"model": model})
        # default to mock
        return MockEngine({})
    if isinstance(primary, dict):
        # assume it's an engine config with type
        t = primary.get("type")
        if t == "ollama":
            return OllamaAdapter(primary.get("config", {}))
        if t == "hf":
            return HuggingFaceAdapter(primary.get("config", {}))
        return MockEngine(primary.get("config", {}))
    return MockEngine({})


def process_case(task_payload: Dict[str, Any], job_id: str = None):
    """Entrypoint for RQ worker. task_payload contains job_id, tenant_id, case, engine_selector, evaluation_config"""
    start = time.time()
    try:
        task = task_payload
        job_id = job_id or task.get("job_id")
        tenant_id = task.get("tenant_id")
        case = task.get("case")
        engine_selector = task.get("engine_selector", {"primary": "mock"})
        evaluation_config = task.get("evaluation_config", {})

        engine = load_engine_from_selector(engine_selector)
        # mark job as processing in DB if present
        try:
            init_db()
            db = SessionLocal()
            jb = db.query(DBJob).filter(DBJob.job_id == job_id, DBJob.tenant_id == tenant_id).first()
            if jb and jb.status == "queued":
                jb.status = "processing"
                db.add(jb)
                db.commit()
        except Exception:
            # DB is best-effort; continue if not available
            jb = None
        finally:
            try:
                db.close()
            except Exception:
                pass
        # use a simple prompt template from orchestrator
        prompt_template = "Evaluate the tutor response to: {student_query}\nRespond with structured JSON scores."
        # call engine (async adapters are sync-capable stubs here)
        # If engine.evaluate is a coroutine, we can't await here; adapters return quickly
        try:
            result = engine.evaluate(case=case, prompt_template=prompt_template, schema={}, timeout=evaluation_config.get("timeout", 30), seed=evaluation_config.get("deterministic_seed", 42))
            # If it's a coroutine, run it
            if hasattr(result, "__await__"):
                import asyncio
                result = asyncio.get_event_loop().run_until_complete(result)
        except Exception as e:
            result = JudgeResult(raw_output={"tutor_response": f"[engine error] {e}"}, model_version=getattr(engine, "model_version", "unknown"), latency_ms=0)

        judge_output = result.get("raw_output") if isinstance(result, dict) else result.raw_output
        engine_id = getattr(engine, "model_version", "mock")

        # Evaluate metrics
        scores = {}
        for metric_id, metric_cls in metrics_registry.items():
            metric = metric_cls()
            try:
                out = metric.evaluate(judge_output, case)
            except Exception as e:
                out = {"value": 1, "confidence": 0.0, "notes": f"metric error: {e}"}
            scores[metric_id] = out

        # aggregate simple normalized score
        from ..metrics.base import value_to_norm
        norms = []
        for v in scores.values():
            val = v.get("value", 1)
            conf = v.get("confidence", 1.0)
            norm = value_to_norm(int(val)) * (conf if conf < 0.4 else 1.0)
            norms.append(norm)
        aggregated = sum(norms) / max(1, len(norms))

        case_result = {
            "case_id": case.get("id"),
            "job_id": job_id,
            "engine_id": engine_id,
            "scores": scores,
            "aggregated_score": aggregated,
            "status": "evaluated",
            "evaluated_at": datetime.utcnow().isoformat() + "Z",
            "trace_id": str(uuid.uuid4()),
            "raw": judge_output
        }

        # write to results file (one file per job)
        out_file = os.path.join(RESULTS_DIR, f"results_{job_id}.ndjson")
        with open(out_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(case_result) + "\n")

        # Persist per-case result to DB (best-effort)
        try:
            init_db()
            db = SessionLocal()
            cr = CaseResult(
                tenant_id=tenant_id,
                job_id=job_id,
                case_id=case.get("id"),
                engine_id=engine_id,
                aggregated_score=float(aggregated),
                scores=scores,
                raw=judge_output,
                status=case_result.get("status"),
            )
            db.add(cr)
            db.commit()
        except Exception:
            # don't fail evaluation on DB problems
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            try:
                db.close()
            except Exception:
                pass

        # After writing, update job progress in DB and aggregate if complete
        try:
            init_db()
            db = SessionLocal()
            jb = db.query(DBJob).filter(DBJob.job_id == job_id, DBJob.tenant_id == tenant_id).first()
            # update processed count in meta
            if jb:
                # count lines in results file
                try:
                    with open(out_file, "r", encoding="utf-8") as rf:
                        processed = sum(1 for _ in rf)
                except Exception:
                    processed = None
                meta = jb.meta or {}
                meta = dict(meta)
                if processed is not None:
                    meta["processed_count"] = processed
                jb.meta = meta
                db.add(jb)
                db.commit()

                # if all processed, compute aggregation and mark completed
                if processed is not None and jb.num_cases and processed >= jb.num_cases:
                    # read all results and compute mean aggregated_score and percent failing
                    scores = []
                    failing = 0
                    with open(out_file, "r", encoding="utf-8") as rf:
                        for line in rf:
                            if not line.strip():
                                continue
                            try:
                                r = json.loads(line)
                                sc = float(r.get("aggregated_score", 0.0))
                                scores.append(sc)
                                if sc < 0.4:
                                    failing += 1
                            except Exception:
                                continue
                    mean_score = sum(scores) / max(1, len(scores)) if scores else 0.0
                    percent_failing = failing / max(1, len(scores))
                    jb.meta = dict(jb.meta or {}, summary={"mean_score": mean_score, "percent_failing": percent_failing, "completed_at": datetime.utcnow().isoformat() + "Z"})
                    jb.status = "completed"
                    db.add(jb)
                    db.commit()
        except Exception:
            pass
        finally:
            try:
                db.close()
            except Exception:
                pass
        elapsed = time.time() - start
        return {"status": "ok", "case_id": case.get("id"), "elapsed": elapsed}

    except Exception as e:
        return {"status": "error", "error": str(e)}
