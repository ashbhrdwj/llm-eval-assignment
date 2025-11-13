"""Start an RQ worker programmatically.
Requires REDIS_URL env var to be set.
Usage: python backend/scripts/start_rq_worker.py
"""
import os
import sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from rq import Worker, Queue, Connection
from redis import Redis

if __name__ == "__main__":
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    conn = Redis.from_url(redis_url)
    with Connection(conn):
        q = Queue("llm-eval")
        worker = Worker([q], name="worker-default")
        print("Starting RQ worker (CTRL+C to exit)...")
        worker.work()
