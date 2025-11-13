import pytest
from backend.app.metrics.clarity import ClarityMetric
from backend.app.metrics.completeness import CompletenessMetric


def make_judge_resp(tutor_response: str):
    return {"tutor_response": tutor_response}


def test_clarity_finds_expected_concepts():
    case = {"expected_concepts": ["sunlight", "chlorophyll"]}
    jr = make_judge_resp("This mentions sunlight and Chlorophyll in clear language.")
    m = ClarityMetric()
    out = m.evaluate(jr, case)
    assert out["value"] >= 3
    assert out["confidence"] >= 0.5


def test_completeness_full():
    case = {"expected_concepts": ["step1", "step2"]}
    jr = make_judge_resp("We cover step1 and step2 in detail.")
    m = CompletenessMetric()
    out = m.evaluate(jr, case)
    assert out["value"] >= 4

if __name__ == "__main__":
    pytest.main([__file__])
