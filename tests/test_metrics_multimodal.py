from backend.app.metrics.multimodal_appropriateness import MultimodalAppropriatenessMetric


def test_multimodal_no_suggestions():
    metric = MultimodalAppropriatenessMetric()
    out = metric.evaluate({}, {"topic": "fractions"})
    assert isinstance(out, dict)
    assert out["value"] == 2


def test_multimodal_unsafe():
    metric = MultimodalAppropriatenessMetric()
    judge = {"suggested_media": ["an unsafe NSFW image"]}
    out = metric.evaluate(judge, {"topic": "history"})
    assert out["value"] <= 1


def test_multimodal_topic_match():
    metric = MultimodalAppropriatenessMetric()
    judge = {"suggested_media": [{"caption": "fractions diagram for math"}]}
    out = metric.evaluate(judge, {"topic": "fractions"})
    assert out["value"] >= 4
