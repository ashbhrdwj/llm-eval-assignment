import subprocess
import sys
import time

from fastapi.testclient import TestClient


def run_sync_runner():
    # run the sync runner which uses job_id 'local-sync' and tenant 'local'
    cmd = [sys.executable, "backend/scripts/run_sync_evaluation.py"]
    subprocess.run(cmd, check=True)


def test_sync_runner_and_endpoints():
    # run the sync runner
    run_sync_runner()

    # now query the endpoints using TestClient
    from backend.app.main import app
    client = TestClient(app)

    # list case results for the run
    resp = client.get("/api/v1/tenants/local/evaluations/local-sync/cases")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("job_id") == "local-sync"
    # ensure there are some cases returned
    assert isinstance(body.get("cases"), list)
    assert len(body.get("cases")) > 0

    # call distribution endpoint for a metric (should return buckets)
    resp2 = client.get("/api/v1/tenants/local/evaluations/local-sync/metrics/distribution?metric=clarity")
    assert resp2.status_code == 200
    j = resp2.json()
    assert "buckets" in j
