import os
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from .api import datasets as datasets_router
from .api import evaluations as evaluations_router
from .api import engines as engines_router
from .api import metrics as metrics_router
from .db.session import init_db

app = FastAPI(title="LLM Evaluation API")
app.include_router(datasets_router.router)
app.include_router(evaluations_router.router)
app.include_router(engines_router.router)
app.include_router(metrics_router.router)


@app.on_event("startup")
def on_startup():
    # Ensure DB tables exist on startup
    try:
        init_db()
    except Exception:
        # don't crash startup in local dev if DB isn't available
        pass


@app.middleware("http")
async def add_trace_id(request: Request, call_next):
    trace_id = str(uuid.uuid4())
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    return response


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    trace_id = getattr(request.state, "trace_id", None) or ""
    return JSONResponse(status_code=500, content={"error": {"code": "internal_error", "message": str(exc)}, "trace_id": trace_id})


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
