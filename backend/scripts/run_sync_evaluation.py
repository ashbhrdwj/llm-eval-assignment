"""Run a synchronous evaluation over a dataset using the mock adapter and local metric pipeline.
Usage: python backend/scripts/run_sync_evaluation.py --dataset data/sample_dataset_v1.json
"""
import argparse
import json
import os
import sys
# ensure project root is on path so we can import backend package
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from backend.app.workers.worker import process_case


def run(dataset_path: str):
    with open(dataset_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    cases = payload.get("test_cases", [])
    summary = []
    for c in cases:
        task = {"job_id": "local-sync", "tenant_id": "local", "case": c, "engine_selector": {"primary": "mock"}, "evaluation_config": {}}
        out = process_case(task, job_id="local-sync")
        summary.append(out)
        print(f"Processed case {c.get('id')}: {out.get('status')} elapsed={out.get('elapsed')}")
    print("Done. Processed", len(summary), "cases")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "sample_dataset_v1.json")))
    args = parser.parse_args()
    run(args.dataset)
