import subprocess
import os
import json
import time

SCRIPT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "scripts", "run_sync_evaluation.py"))
DATASET = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "sample_dataset_v1.json"))
RESULTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "results"))


def test_run_sync_evaluation_creates_results(tmp_path):
    # ensure results dir exists and is empty
    os.makedirs(RESULTS_DIR, exist_ok=True)
    # remove existing results file for local-sync job if present
    rf = os.path.join(RESULTS_DIR, "results_local-sync.ndjson")
    if os.path.exists(rf):
        os.remove(rf)

    # run the script
    proc = subprocess.run(["python", SCRIPT, "--dataset", DATASET], capture_output=True, text=True)
    assert proc.returncode == 0, f"Runner failed: {proc.stderr}"

    # wait up to 5s for file to appear
    for _ in range(5):
        if os.path.exists(rf):
            break
        time.sleep(1)
    assert os.path.exists(rf), "Results file not created"

    # check number of lines equals number of test cases
    with open(DATASET, "r", encoding="utf-8") as f:
        payload = json.load(f)
    expected = len(payload.get("test_cases", []))
    with open(rf, "r", encoding="utf-8") as f:
        lines = [l for l in f.read().splitlines() if l.strip()]
    assert len(lines) == expected
