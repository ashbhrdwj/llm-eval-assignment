import os
import uuid
import json
from fastapi import APIRouter, UploadFile, File, HTTPException, Header
from fastapi import status
from typing import Optional
from jsonschema import validate, ValidationError
from ..db.session import SessionLocal, init_db
from ..db.models import Dataset as DBDataset

router = APIRouter()

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "schemas", "testcase_schema.json")
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data"))
os.makedirs(DATA_DIR, exist_ok=True)


def load_schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@router.post("/api/v1/tenants/{tenant_id}/datasets", status_code=status.HTTP_201_CREATED)
async def upload_dataset(tenant_id: str, file: UploadFile = File(...), x_api_key: Optional[str] = Header(None)):
    # basic dev auth - use env DEV_API_KEY
    from os import getenv
    dev_key = getenv("DEV_API_KEY")
    if dev_key and x_api_key != dev_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    content = await file.read()
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    if "test_cases" not in payload or not isinstance(payload["test_cases"], list):
        raise HTTPException(status_code=400, detail="File must contain top-level 'test_cases' array")

    schema = load_schema()
    # validate each case
    try:
        for case in payload["test_cases"]:
            validate(case, schema)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Schema validation error: {e.message}")

    dataset_id = str(uuid.uuid4())
    version = 1
    filename = f"dataset_{tenant_id}_{dataset_id}_v{version}.json"
    out_path = os.path.join(DATA_DIR, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    # persist metadata to DB (init DB if needed)
    try:
        init_db()
        db = SessionLocal()
        # store minimal dataset metadata in DB under metadata_json (avoid reserved name 'metadata')
        ds = DBDataset(tenant_id=tenant_id, dataset_id=dataset_id, path=out_path, version=version, num_cases=len(payload.get("test_cases", [])), metadata_json={})
        db.add(ds)
        db.commit()
        db.refresh(ds)
    finally:
        try:
            db.close()
        except Exception:
            pass

    return {"dataset_id": dataset_id, "version": version, "path": out_path}


@router.get("/api/v1/tenants/{tenant_id}/datasets/{dataset_id}")
async def get_dataset_metadata(tenant_id: str, dataset_id: str, x_api_key: Optional[str] = Header(None)):
    from os import getenv
    dev_key = getenv("DEV_API_KEY")
    if dev_key and x_api_key != dev_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # naive search in data dir
    for fn in os.listdir(DATA_DIR):
        if dataset_id in fn and fn.startswith("dataset_"):
            path = os.path.join(DATA_DIR, fn)
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            return {"dataset_id": dataset_id, "version": 1, "num_cases": len(payload.get("test_cases", [])), "path": path}
    raise HTTPException(status_code=404, detail="Dataset not found")
