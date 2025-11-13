from typing import Dict, Any

class Metric:
    id: str

    def __init__(self, id: str):
        self.id = id

    def evaluate(self, judge_output: Dict[str, Any], case: Dict[str, Any]) -> Dict[str, Any]:
        """Return {'value': int(1..5), 'confidence': float, 'notes':str}"""
        raise NotImplementedError()


def value_to_norm(value: int) -> float:
    """Convert 1..5 to normalized 0..1"""
    return max(0.0, min(1.0, (value - 1) / 4))
