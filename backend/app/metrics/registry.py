from typing import Dict
from .clarity import ClarityMetric
from .completeness import CompletenessMetric
from .accuracy import AccuracyMetric
from .appropriateness import AppropriatenessMetric
from .long_term_memory import LongTermMemoryMetric
from .code_quality import CodeQualityMetric
from .pedagogy_alignment import PedagogyAlignmentMetric

# mapping id -> class (callable to create metric)
registry: Dict[str, type] = {
    "clarity": ClarityMetric,
    "completeness": CompletenessMetric,
    "accuracy": AccuracyMetric,
    "appropriateness": AppropriatenessMetric,
    "long_term_memory": LongTermMemoryMetric,
    "code_quality": CodeQualityMetric,
    "pedagogy_alignment": PedagogyAlignmentMetric,
}

__all__ = ["registry"]
