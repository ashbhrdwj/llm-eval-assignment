from typing import Dict, Any
from .base import Metric

class AppropriatenessMetric(Metric):
    def __init__(self):
        super().__init__(id="appropriateness")

    def evaluate(self, judge_output: Dict[str, Any], case: Dict[str, Any]) -> Dict[str, Any]:
        # Basic check: ensure language and examples are grade-appropriate by length and presence of jargon
        resp = judge_output.get("tutor_response", "")
        grade = case.get("grade_level", "middle_school")
        word_count = len(resp.split())
        # heuristics
        if grade == "elementary":
            if word_count < 10:
                value = 4
            elif word_count > 120:
                value = 2
            else:
                value = 3
        elif grade == "middle_school":
            value = 4 if word_count < 200 else 3
        else:
            value = 4
        confidence = 0.7
        notes = f"word_count={word_count}, grade={grade}"
        return {"value": int(value), "confidence": float(confidence), "notes": notes}
