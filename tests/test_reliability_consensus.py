import pytest

from urbanvision_risk.detection.tiled import DetectionCandidate
from urbanvision_risk.reliability.consensus import (
    analyze_consensus,
    horizontal_flip_candidates,
)


def _candidate(
    confidence: float,
    bbox: tuple[float, float, float, float],
    *,
    class_id: int = 0,
) -> DetectionCandidate:
    return DetectionCandidate(class_id, confidence, bbox)


def test_consensus_fuses_supported_views_and_quantifies_stability() -> None:
    result = analyze_consensus(
        {
            "native-640": [_candidate(0.72, (10.0, 20.0, 110.0, 220.0))],
            "native-1280": [_candidate(0.84, (12.0, 18.0, 112.0, 224.0))],
            "hflip-1280": [_candidate(0.78, (9.0, 22.0, 109.0, 221.0))],
        },
        decision_confidence=0.25,
    )

    assert len(result.candidates) == 1
    assert result.candidates[0].confidence == pytest.approx(0.78)
    assert result.candidates[0].bbox_xyxy[0] == pytest.approx(10.384615, rel=1e-5)
    summary = result.evidence["summary"]
    assert summary["accepted_cluster_count"] == 1
    assert summary["disputed_cluster_count"] == 0
    assert summary["mean_stability"] > 0.98
    assert summary["review_recommended"] is False
    assert result.evidence["clusters"][0]["support_count"] == 3


def test_single_view_high_confidence_detection_is_disputed_not_accepted() -> None:
    result = analyze_consensus(
        {
            "native-640": [_candidate(0.91, (10.0, 10.0, 80.0, 90.0))],
            "native-1280": [],
            "hflip-1280": [],
        },
        decision_confidence=0.25,
    )

    assert result.candidates == ()
    assert result.evidence["summary"]["disputed_cluster_count"] == 1
    assert result.evidence["summary"]["active_learning_tier"] == "high"
    assert result.evidence["summary"]["review_recommended"] is True
    assert result.evidence["clusters"][0]["disposition"] == "disputed_single_view"


def test_consensus_never_associates_different_classes() -> None:
    result = analyze_consensus(
        {
            "native-640": [_candidate(0.80, (10.0, 10.0, 100.0, 100.0), class_id=0)],
            "native-1280": [_candidate(0.75, (10.0, 10.0, 100.0, 100.0), class_id=2)],
        },
        decision_confidence=0.25,
    )

    assert result.candidates == ()
    assert result.evidence["summary"]["cluster_count"] == 2
    assert result.evidence["summary"]["disputed_cluster_count"] == 2


def test_horizontal_flip_candidates_restores_source_coordinates() -> None:
    restored = horizontal_flip_candidates(
        [_candidate(0.8, (20.0, 5.0, 60.0, 80.0))],
        image_width=200,
    )

    assert restored[0].bbox_xyxy == (140.0, 5.0, 180.0, 80.0)


@pytest.mark.parametrize(
    "views",
    ({"only": []}, {}),
)
def test_consensus_rejects_insufficient_views(
    views: dict[str, list[DetectionCandidate]],
) -> None:
    with pytest.raises(ValueError, match="at least two views"):
        analyze_consensus(views, decision_confidence=0.25)
