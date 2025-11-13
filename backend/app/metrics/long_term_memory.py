from typing import Dict, Any
from .base import Metric

class LongTermMemoryMetric(Metric):
    def __init__(self):
        super().__init__(id="long_term_memory")

    def evaluate(self, judge_output: Dict[str, Any], case: Dict[str, Any]) -> Dict[str, Any]:
        # This heuristic: check meta for a 'context' or memory mention; mock adapters won't provide context, so return neutral
        meta = judge_output.get("meta", {}) or {}
        tutor_resp = judge_output.get("tutor_response", "")
        # If the case has metadata 'previous' context, check mention
        prev = case.get("metadata", {}).get("previous_context")
        if prev:
            found = prev.lower() in tutor_resp.lower()
            value = 5 if found else 2
            confidence = 0.8
            notes = "previous context referenced" if found else "no previous context reference"
        else:
            value = 3
            confidence = 0.4
            notes = "no prior context in case"
        return {"value": int(value), "confidence": float(confidence), "notes": notes}
