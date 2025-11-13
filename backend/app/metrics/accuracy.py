from typing import Dict, Any
from .base import Metric

class AccuracyMetric(Metric):
    def __init__(self):
        super().__init__(id="accuracy")

    def evaluate(self, judge_output: Dict[str, Any], case: Dict[str, Any]) -> Dict[str, Any]:
        # Heuristic accuracy: if ground_truth_answer exists, check overlap; else rely on expected concepts presence
        resp = judge_output.get("tutor_response", "")
        gt = case.get("ground_truth_answer")
        expected = [s.lower() for s in case.get("expected_concepts", []) or []]
        if gt:
            # simple substring match (conservative)
            is_present = 1 if gt.strip().lower() in resp.lower() else 0
            value = 5 if is_present else 3
            confidence = 0.8
            notes = "matched ground truth" if is_present else "did not match ground truth"
        else:
            # assess via expected concepts overlap
            present = sum(1 for e in expected if e and e.lower() in resp.lower())
            if present == 0:
                value = 2
            elif present < max(1, len(expected) // 2):
                value = 3
            else:
                value = 4
            confidence = 0.6 if present > 0 else 0.4
            notes = f"{present}/{len(expected)} expected concepts matched"
        return {"value": int(value), "confidence": float(confidence), "notes": notes}
