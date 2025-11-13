from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from ..api.models import EngineRegisterRequest, EngineInfo
from ..utils.engine_registry import register_engine, list_engines, get_engine

router = APIRouter()

@router.post("/api/v1/engines", status_code=201)
async def register_engine_endpoint(payload: EngineRegisterRequest, x_api_key: Optional[str] = Header(None)):
    # simple dev auth
    from os import getenv
    dev_key = getenv("DEV_API_KEY")
    if dev_key and x_api_key != dev_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    register_engine(payload.name, payload.type, payload.config or {})
    return {"name": payload.name, "type": payload.type, "config": payload.config}

@router.get("/api/v1/engines")
async def list_engines_endpoint(x_api_key: Optional[str] = Header(None)):
    from os import getenv
    dev_key = getenv("DEV_API_KEY")
    if dev_key and x_api_key != dev_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return list_engines()
