from fastapi import APIRouter, Header
from typing import Optional
from ..metrics import registry as metrics_registry

router = APIRouter()

@router.get("/api/v1/metrics")
async def list_metrics(x_api_key: Optional[str] = Header(None)):
    from os import getenv
    dev_key = getenv("DEV_API_KEY")
    if dev_key and x_api_key != dev_key:
        return []
    out = []
    for mid in metrics_registry.registry.keys():
        out.append({"id": mid})
    return out
