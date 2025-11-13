from typing import Dict, Any
from .base import Metric

class CompletenessMetric(Metric):
    def __init__(self):
        super().__init__(id="completeness")

    def evaluate(self, judge_output: Dict[str, Any], case: Dict[str, Any]) -> Dict[str, Any]:
        resp = judge_output.get("tutor_response", "")
        expected = [s.lower() for s in case.get("expected_concepts", []) or []]
        present = 0
        for e in expected:
            if e and e.lower() in resp.lower():
                present += 1
        if not expected:
            value = 3
            confidence = 0.5
        else:
            fraction = present / max(1, len(expected))
            if fraction == 0:
                value = 2
            elif fraction < 0.5:
                value = 3
            elif fraction < 1.0:
                value = 4
            else:
                value = 5
            confidence = 0.7 + 0.3 * fraction
        return {"value": int(value), "confidence": float(round(confidence, 2)), "notes": f"{present}/{len(expected)} expected concepts present"}
