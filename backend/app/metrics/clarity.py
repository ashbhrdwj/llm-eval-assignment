from typing import Dict, Any
from .base import Metric

class ClarityMetric(Metric):
    def __init__(self):
        super().__init__(id="clarity")

    def evaluate(self, judge_output: Dict[str, Any], case: Dict[str, Any]) -> Dict[str, Any]:
        # Simple heuristic: presence of expected concepts in tutor_response and length
        resp = judge_output.get("tutor_response", "")
        expected = [s.lower() for s in case.get("expected_concepts", []) or []]
        present = 0
        for e in expected:
            if e and e.lower() in resp.lower():
                present += 1
        # base score
        if present == 0:
            value = 2
        elif present < max(1, len(expected) // 2):
            value = 3
        else:
            value = 4
        # adjust for brevity
        if len(resp.split()) < 10:
            value = max(1, value - 1)
        confidence = 0.8 if present > 0 else 0.5
        return {"value": int(value), "confidence": float(confidence), "notes": f"{present} expected concepts found"}
