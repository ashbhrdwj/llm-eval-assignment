from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class MetricSpec(BaseModel):
    id: str
    weight: Optional[float] = None

class EvaluationConfig(BaseModel):
    metrics: List[MetricSpec]
    rubric_version: Optional[str] = "v1"
    deterministic_seed: Optional[int] = 42
    timeout: Optional[int] = 60

class EvaluationCreateRequest(BaseModel):
    dataset_id: str
    case_filters: Optional[Dict[str, Any]] = {}
    engine_selector: Optional[Dict[str, Any]] = {"primary": "mock"}
    evaluation_config: Optional[EvaluationConfig] = EvaluationConfig(metrics=[])
    mode: Optional[str] = "async"
    notify: Optional[Dict[str, Any]] = None

class DatasetUploadResponse(BaseModel):
    dataset_id: str
    version: int
    path: str

class JobCreateResponse(BaseModel):
    job_id: str
    status: str
    trace_id: Optional[str] = None

class EngineRegisterRequest(BaseModel):
    name: str
    type: str
    config: Optional[Dict[str, Any]] = {}

class EngineInfo(BaseModel):
    name: str
    type: str
    config: Optional[Dict[str, Any]] = {}

class MetricInfo(BaseModel):
    id: str
    description: Optional[str] = None
