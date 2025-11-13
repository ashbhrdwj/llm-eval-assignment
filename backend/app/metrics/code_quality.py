from typing import Dict, Any
from .base import Metric

class CodeQualityMetric(Metric):
    def __init__(self):
        super().__init__(id="code_quality")

    def evaluate(self, judge_output: Dict[str, Any], case: Dict[str, Any]) -> Dict[str, Any]:
        # For cases related to code (subject may be 'math' for coding examples), check if tutor_response contains 'def' or code markers
        resp = judge_output.get("tutor_response", "")
        if "def " in resp or "```" in resp or "return" in resp:
            value = 4
            confidence = 0.8
            notes = "Code present; not deeply analyzed"
        else:
            # If the case asked for tests or code, penalize
            if "code" in case.get("student_query", "").lower() or "test" in case.get("student_query", "").lower():
                value = 2
                confidence = 0.5
                notes = "No code provided when asked"
            else:
                value = 3
                confidence = 0.5
                notes = "Not applicable / no code"
        return {"value": int(value), "confidence": float(confidence), "notes": notes}
