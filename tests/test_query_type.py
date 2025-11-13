from backend.app.metrics.query_type import classify_query_text


def test_classify_explanation():
    assert classify_query_text("Explain why photosynthesis occurs") == "explanation"


def test_classify_problem_solving():
    assert classify_query_text("Solve the quadratic equation") == "problem_solving"


def test_classify_analysis():
    assert classify_query_text("Compare and contrast two algorithms") == "analysis"


def test_classify_other():
    assert classify_query_text("") == "other"
