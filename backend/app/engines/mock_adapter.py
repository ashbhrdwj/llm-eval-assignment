import time
import random
from typing import Dict, Any
from .base import BaseEngine, JudgeResult

class MockEngine(BaseEngine):
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.model_version = "mock/0.1"

    async def evaluate(self, case: Dict[str, Any], prompt_template: str, schema: Dict[str, Any], timeout: int = 10, seed: int = 42) -> JudgeResult:
        start = time.time()
        rnd = random.Random(seed + hash(case.get("id")))
        # Simulate a tutor response by echoing the query + sprinkling expected concepts
        expected = case.get("expected_concepts", []) or []
        response = case.get("student_query", "") + "\n\nAnswer: "
        if expected:
            response += "This explanation mentions: " + ", ".join(expected[:3]) + "."
        else:
            response += "A short helpful answer."

        # Create a deterministic per-metric judgments
        metrics_out = {}
        metric_ids = ["clarity","completeness","accuracy","appropriateness","long_term_memory","code_quality","pedagogy_alignment"]
        for i, m in enumerate(metric_ids):
            # produce value 1..5 biased by presence of expected concepts
            base = 3
            bonus = min(len(expected), 3)
            noise = rnd.randint(-1, 1)
            val = max(1, min(5, base + (bonus // 2) + noise))
            confidence = round(rnd.random() * 0.4 + 0.6, 2)  # between 0.6 and 1.0
            metrics_out[m] = {"value": val, "confidence": confidence, "notes": f"Mocked score for {m}"}

        raw = {
            "tutor_response": response,
            "metrics": metrics_out,
            "meta": {
                "seed": seed,
                "case_id": case.get("id")
            }
        }
        latency_ms = int((time.time() - start) * 1000)
        return JudgeResult(raw_output=raw, model_version=self.model_version, latency_ms=latency_ms)
