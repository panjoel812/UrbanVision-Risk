import cv2
import numpy as np
import pytest

from urbanvision_risk.app.crack_proposal import (
    MAX_RANKED_REVIEW_HOTSPOTS,
    PROPOSAL_SCHEMA_VERSION,
    propose_crack_mask,
)


def _road_with_cracks() -> np.ndarray:
    random = np.random.default_rng(42)
    road = np.clip(random.normal(170, 12, (360, 540)), 0, 255).astype(np.uint8)
    image = cv2.cvtColor(road, cv2.COLOR_GRAY2BGR)
    cv2.line(image, (35, 280), (490, 80), (35, 35, 35), 5)
    cv2.line(image, (250, 190), (410, 315), (100, 100, 100), 2)
    cv2.line(image, (250, 190), (180, 80), (125, 125, 125), 1)
    return image


def test_proposal_exposes_three_level_review_guidance() -> None:
    proposal = propose_crack_mask(_road_with_cracks(), sensitivity=0.55)

    assert proposal.mask.shape == (360, 540)
    assert proposal.review_hotspots.shape == proposal.mask.shape
    assert proposal.mask.dtype == np.bool_
    assert proposal.review_hotspots.dtype == np.bool_
    assert proposal.evidence["schema_version"] == PROPOSAL_SCHEMA_VERSION
    guidance = proposal.evidence["review_guidance"]
    assert guidance["sensitivities"] == [0.4, 0.55, 0.7]
    assert guidance["sample_count"] == 3
    assert guidance["stable_pixels"] + guidance["disagreement_pixels"] == (
        guidance["union_pixels"]
    )
    assert guidance["review_hotspot_pixels"] == int(
        np.count_nonzero(proposal.review_hotspots)
    )
    assert guidance["disagreement_pixels"] > 0
    assert guidance["review_hotspot_pixels"] > 0
    ranking = guidance["ranking"]
    hotspots = ranking["ranked_hotspots"]
    assert 0 < len(hotspots) <= MAX_RANKED_REVIEW_HOTSPOTS
    assert ranking["ranked_hotspot_count"] == len(hotspots)
    assert ranking["ranked_hotspot_count"] + ranking["unranked_component_count"] == (
        guidance["review_zone_component_count"]
    )
    assert guidance["review_zone_component_count"] <= (
        guidance["review_hotspot_component_count"]
    )
    assert guidance["review_zone_grouping_diameter_pixels"] % 2 == 1
    assert 0 < ranking["ranked_disagreement_pixel_coverage_ratio"] <= 1
    assert 0 < ranking["ranked_priority_mass_ratio"] <= 1
    assert [hotspot["hotspot_id"] for hotspot in hotspots] == [
        f"hotspot-{index:03d}" for index in range(1, len(hotspots) + 1)
    ]
    assert [hotspot["priority_score"] for hotspot in hotspots] == sorted(
        [hotspot["priority_score"] for hotspot in hotspots],
        reverse=True,
    )
    for hotspot in hotspots:
        box = hotspot["bounding_box"]
        assert 0 <= box["x"] < proposal.mask.shape[1]
        assert 0 <= box["y"] < proposal.mask.shape[0]
        assert box["x"] + box["width"] <= proposal.mask.shape[1]
        assert box["y"] + box["height"] <= proposal.mask.shape[0]
        assert hotspot["disagreement_pixels"] > 0
    assert "not a calibrated uncertainty probability" in guidance["interpretation"]


@pytest.mark.parametrize("sensitivity", (0.0, 1.0))
def test_review_guidance_remains_defined_at_sensitivity_boundaries(
    sensitivity: float,
) -> None:
    proposal = propose_crack_mask(_road_with_cracks(), sensitivity=sensitivity)

    guidance = proposal.evidence["review_guidance"]
    assert guidance["sample_count"] == 2
    assert sensitivity in guidance["sensitivities"]


@pytest.mark.parametrize("sensitivity", (-0.01, 1.01, float("nan")))
def test_proposal_rejects_invalid_sensitivity(sensitivity: float) -> None:
    with pytest.raises(ValueError, match="sensitivity"):
        propose_crack_mask(_road_with_cracks(), sensitivity=sensitivity)
