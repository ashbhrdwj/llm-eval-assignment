import os
import json
from fastapi import APIRouter, Body, HTTPException, Header
from fastapi import status
from typing import Optional, Dict, Any
from ..orchestrator.orchestrator import Orchestrator
from .models import EvaluationCreateRequest, JobCreateResponse
from ..db.session import SessionLocal, init_db
from ..db.models import Job as DBJob, CaseResult

router = APIRouter()
orch = Orchestrator()


@router.post("/api/v1/tenants/{tenant_id}/evaluations", status_code=status.HTTP_202_ACCEPTED)
async def create_evaluation(tenant_id: str, payload: EvaluationCreateRequest = Body(...), x_api_key: Optional[str] = Header(None)) -> JobCreateResponse:
    from os import getenv
    dev_key = getenv("DEV_API_KEY")
    if dev_key and x_api_key != dev_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    dataset_id = payload.dataset_id
    case_filters = payload.case_filters or {}
    engine_selector = payload.engine_selector or {"primary": "mock"}
    evaluation_config = payload.evaluation_config.dict() if payload.evaluation_config else {}
    mode = payload.mode or "async"

    # find dataset path
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
    dataset_path = None
    for fn in os.listdir(data_dir):
        if dataset_id and dataset_id in fn:
            dataset_path = os.path.join(data_dir, fn)
            break
    if not dataset_path:
        raise HTTPException(status_code=404, detail="Dataset not found")

    job = orch.create_job(tenant_id=tenant_id, dataset_path=dataset_path, case_filters=case_filters, engine_selector=engine_selector, evaluation_config=evaluation_config, mode=mode)
    return {"job_id": job["job_id"], "status": job["status"], "trace_id": ""}


@router.get("/api/v1/tenants/{tenant_id}/evaluations/{job_id}")
async def get_evaluation_status(tenant_id: str, job_id: str, x_api_key: Optional[str] = Header(None)):
    from os import getenv
    dev_key = getenv("DEV_API_KEY")
    if dev_key and x_api_key != dev_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Try to read job metadata from DB first
    init_db()
    db = SessionLocal()
    try:
        jb = db.query(DBJob).filter(DBJob.job_id == job_id, DBJob.tenant_id == tenant_id).first()
        if not jb:
            # fallback to file-based job metadata
            jf = orch.get_job_file(job_id)
            if not jf:
                raise HTTPException(status_code=404, detail="Job not found")
            with open(jf, "r", encoding="utf-8") as f:
                data = f.read()
            return {"job_id": job_id, "meta": data}

        # return DB-backed metadata including stored meta/summary
        return {
            "job_id": jb.job_id,
            "tenant_id": jb.tenant_id,
            "dataset_id": jb.dataset_id,
            "status": jb.status,
            "num_cases": jb.num_cases,
            "mode": jb.mode,
            "created_at": jb.created_at.isoformat() if jb.created_at else None,
            "meta": jb.meta or {}
        }
    finally:
        db.close()


@router.get("/api/v1/tenants/{tenant_id}/evaluations/{job_id}/results")
async def get_evaluation_results(tenant_id: str, job_id: str, x_api_key: Optional[str] = Header(None)):
    """Return per-case NDJSON results for a job as JSON list (for demo/local use)."""
    from os import getenv
    dev_key = getenv("DEV_API_KEY")
    if dev_key and x_api_key != dev_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "results"))
    results_file = os.path.join(results_dir, f"results_{job_id}.ndjson")
    if not os.path.exists(results_file):
        raise HTTPException(status_code=404, detail="Results not found yet")
    out = []
    with open(results_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                # skip malformed lines
                continue

    return {"job_id": job_id, "results": out}


@router.get("/api/v1/tenants/{tenant_id}/evaluations/{job_id}/results.csv")
async def get_evaluation_results_csv(tenant_id: str, job_id: str, x_api_key: Optional[str] = Header(None)):
    """Return results as a CSV download (demo)."""
    from fastapi.responses import StreamingResponse
    import io

    results_resp = await get_evaluation_results(tenant_id, job_id, x_api_key)
    rows = results_resp.get("results", [])
    if not rows:
        raise HTTPException(status_code=404, detail="Results not found or empty")

    # Flatten simple columns: case_id, aggregated_score, evaluated_at
    output = io.StringIO()
    headers = ["case_id", "aggregated_score", "evaluated_at"]
    output.write(",".join(headers) + "\n")
    for r in rows:
        line = [str(r.get(h, "")) for h in headers]
        # escape commas in fields
        output.write(",".join('"' + v.replace('"','""') + '"' for v in line) + "\n")
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=results_{job_id}.csv"})


@router.get("/api/v1/tenants/{tenant_id}/evaluations")
async def list_evaluations(tenant_id: str, x_api_key: Optional[str] = Header(None)):
    """List jobs for a tenant (DB-backed)."""
    from os import getenv
    dev_key = getenv("DEV_API_KEY")
    if dev_key and x_api_key != dev_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    init_db()
    db = SessionLocal()
    try:
        rows = db.query(DBJob).filter(DBJob.tenant_id == tenant_id).order_by(DBJob.created_at.desc()).all()
        out = []
        for jb in rows:
            out.append({
                "job_id": jb.job_id,
                "status": jb.status,
                "num_cases": jb.num_cases,
                "mode": jb.mode,
                "created_at": jb.created_at.isoformat() if jb.created_at else None,
                "meta": jb.meta or {}
            })
        return {"tenant_id": tenant_id, "jobs": out}
    finally:
        db.close()


@router.get("/api/v1/tenants/{tenant_id}/evaluations/{job_id}/cases")
async def list_case_results(tenant_id: str, job_id: str, limit: int = 50, offset: int = 0, min_score: Optional[float] = None, max_score: Optional[float] = None, x_api_key: Optional[str] = Header(None)):
    """List per-case results for a job. Supports simple pagination and score filtering."""
    from os import getenv
    dev_key = getenv("DEV_API_KEY")
    if dev_key and x_api_key != dev_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    init_db()
    db = SessionLocal()
    try:
        q = db.query(CaseResult).filter(CaseResult.tenant_id == tenant_id, CaseResult.job_id == job_id)
        if min_score is not None:
            q = q.filter(CaseResult.aggregated_score >= float(min_score))
        if max_score is not None:
            q = q.filter(CaseResult.aggregated_score <= float(max_score))
        total = q.count()
        rows = q.order_by(CaseResult.evaluated_at.desc()).offset(offset).limit(limit).all()
        out = []
        for r in rows:
            out.append({
                "case_id": r.case_id,
                "aggregated_score": r.aggregated_score,
                "scores": r.scores,
                "engine_id": r.engine_id,
                "status": r.status,
                "evaluated_at": r.evaluated_at.isoformat() if r.evaluated_at else None,
            })
        return {"job_id": job_id, "total": total, "limit": limit, "offset": offset, "cases": out}
    finally:
        db.close()


@router.get("/api/v1/tenants/{tenant_id}/evaluations/{job_id}/cases/{case_id}")
async def get_case_result(tenant_id: str, job_id: str, case_id: str, x_api_key: Optional[str] = Header(None)):
    from os import getenv
    dev_key = getenv("DEV_API_KEY")
    if dev_key and x_api_key != dev_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    init_db()
    db = SessionLocal()
    try:
        r = db.query(CaseResult).filter(CaseResult.tenant_id == tenant_id, CaseResult.job_id == job_id, CaseResult.case_id == case_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Case result not found")
        return {
            "case_id": r.case_id,
            "aggregated_score": r.aggregated_score,
            "scores": r.scores,
            "engine_id": r.engine_id,
            "raw": r.raw,
            "status": r.status,
            "evaluated_at": r.evaluated_at.isoformat() if r.evaluated_at else None,
        }
    finally:
        db.close()
