import os
import json
import uuid
from typing import List, Dict, Any, Optional
from redis import Redis
from rq import Queue
from datetime import datetime
from ..db.session import SessionLocal, init_db
from ..db.models import Job as DBJob

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
JOBS_DIR = os.path.join(DATA_DIR, "jobs")
os.makedirs(JOBS_DIR, exist_ok=True)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_conn = Redis.from_url(REDIS_URL)
queue = Queue("llm-eval", connection=redis_conn)

PROMPT_TEMPLATE = "Evaluate the tutor response to: {student_query}\nProvide JSON with per-metric scores."

class Orchestrator:
    def __init__(self):
        self.queue = queue

    def create_job(self, tenant_id: str, dataset_path: str, case_filters: Optional[Dict[str, Any]], engine_selector: Dict[str, Any], evaluation_config: Dict[str, Any], mode: str = "async") -> Dict[str, Any]:
        job_id = str(uuid.uuid4())
        with open(dataset_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        cases = payload.get("test_cases", [])
        # Apply simple filters
        if case_filters:
            if "grade_levels" in case_filters:
                cases = [c for c in cases if c.get("grade_level") in case_filters["grade_levels"]]
            if "subjects" in case_filters:
                cases = [c for c in cases if c.get("subject") in case_filters["subjects"]]
        tasks = []
        for c in cases:
            tasks.append({"job_id": job_id, "tenant_id": tenant_id, "case": c, "engine_selector": engine_selector, "evaluation_config": evaluation_config})

        job_meta = {"job_id": job_id, "tenant_id": tenant_id, "created_at": datetime.utcnow().isoformat() + "Z", "num_cases": len(tasks), "status": "queued", "mode": mode}
        job_file = os.path.join(JOBS_DIR, f"job_{job_id}.json")
        with open(job_file, "w", encoding="utf-8") as f:
            json.dump({"meta": job_meta, "tasks": tasks}, f, indent=2)

        # persist job metadata to DB
        try:
            init_db()
            db = SessionLocal()
            jb = DBJob(tenant_id=tenant_id, job_id=job_id, dataset_id=os.path.basename(dataset_path), status=job_meta["status"], num_cases=len(tasks), mode=mode, meta={})
            db.add(jb)
            db.commit()
            db.refresh(jb)
        finally:
            try:
                db.close()
            except Exception:
                pass

        # enqueue tasks
        if mode == "async":
            for t in tasks:
                self.queue.enqueue("backend.app.workers.worker.process_case", t, job_id, ttl=evaluation_config.get("timeout", 60))
            job_meta["status"] = "queued"
        else:
            # synchronous processing: process in current thread by enqueuing and waiting
            for t in tasks:
                self.queue.enqueue("backend.app.workers.worker.process_case", t, job_id, ttl=evaluation_config.get("timeout", 60))
            job_meta["status"] = "processing"

        # update job file
        with open(job_file, "w", encoding="utf-8") as f:
            json.dump({"meta": job_meta, "tasks": tasks}, f, indent=2)

        return {"job_id": job_id, "status": job_meta["status"], "num_cases": len(tasks)}

    def get_job_file(self, job_id: str) -> Optional[str]:
        job_file = os.path.join(JOBS_DIR, f"job_{job_id}.json")
        if os.path.exists(job_file):
            return job_file
        return None

    def list_jobs(self) -> List[Dict[str, Any]]:
        out = []
        for fn in os.listdir(JOBS_DIR):
            if fn.startswith("job_") and fn.endswith(".json"):
                with open(os.path.join(JOBS_DIR, fn), "r", encoding="utf-8") as f:
                    out.append(json.load(f).get("meta", {}))
        return out
