from typing import Dict, Any
from .base import Metric

class PedagogyAlignmentMetric(Metric):
    def __init__(self):
        super().__init__(id="pedagogy_alignment")

    def evaluate(self, judge_output: Dict[str, Any], case: Dict[str, Any]) -> Dict[str, Any]:
        # Heuristic: check for scaffolding words, steps, or suggestions
        resp = judge_output.get("tutor_response", "").lower()
        scaffolding_words = ["first","then","next","suggest","practice","exercise","example","check"]
        count = sum(1 for w in scaffolding_words if w in resp)
        if count >= 3:
            value = 5
            confidence = 0.8
            notes = f"scaffolding indicators found: {count}"
        elif count >= 1:
            value = 4
            confidence = 0.6
            notes = f"some scaffolding indicators found: {count}"
        else:
            value = 2
            confidence = 0.4
            notes = "no scaffolding indicators found"
        return {"value": int(value), "confidence": float(confidence), "notes": notes}
