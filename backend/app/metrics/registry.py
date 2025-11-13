from typing import Dict
from .clarity import ClarityMetric
from .completeness import CompletenessMetric
from .accuracy import AccuracyMetric
from .appropriateness import AppropriatenessMetric
from .long_term_memory import LongTermMemoryMetric
from .code_quality import CodeQualityMetric
from .pedagogy_alignment import PedagogyAlignmentMetric
from .multimodal_appropriateness import MultimodalAppropriatenessMetric

# mapping id -> class (callable to create metric)
registry: Dict[str, type] = {
    "clarity": ClarityMetric,
    "completeness": CompletenessMetric,
    "accuracy": AccuracyMetric,
    "appropriateness": AppropriatenessMetric,
    "long_term_memory": LongTermMemoryMetric,
    "code_quality": CodeQualityMetric,
    "pedagogy_alignment": PedagogyAlignmentMetric,
    "multimodal_appropriateness": MultimodalAppropriatenessMetric,
}

# categories indicate which query types a metric is most relevant for
metric_categories = {
    "clarity": "explanation",
    "completeness": "explanation",
    "accuracy": "problem_solving",
    "code_quality": "problem_solving",
    "appropriateness": "analysis",
    "long_term_memory": "analysis",
    "pedagogy_alignment": "explanation",
    "multimodal_appropriateness": "multimodal",
}

__all__ = ["registry"]
