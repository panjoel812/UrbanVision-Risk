from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest

from urbanvision_risk.data.voc import CLASS_INFO
from urbanvision_risk.risk.config import RiskConfig, load_risk_config
from urbanvision_risk.risk.schema import validate_prediction_payload
from urbanvision_risk.risk.score import score_prediction

ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_risk_config(ROOT / "configs" / "risk-v0.2.yaml")


def payload(detections: list[dict[str, object]]) -> dict[str, object]:
    counts: Counter[str] = Counter({details["code"]: 0 for details in CLASS_INFO.values()})
    for detection_item in detections:
        counts[str(detection_item["code"])] += 1
    return {
        "source_image": "/tmp/road.jpg",
        "model_checkpoint": "/tmp/best.pt",
        "confidence_threshold": 0.25,
        "image_dimensions": {"width": 100, "height": 100},
        "detections": detections,
        "counts": dict(counts),
    }


def detection(class_id: int = 3, confidence: float = 0.8) -> dict[str, object]:
    details = CLASS_INFO[class_id]
    return {
        "class_id": class_id,
        "code": details["code"],
        "name_en": details["name_en"],
        "name_zh": details["name_zh"],
        "confidence": confidence,
        "bbox_xyxy": [0, 0, 10, 10],
    }


def scored(detections: list[dict[str, object]]) -> dict[str, object]:
    record = validate_prediction_payload(payload(detections), CONFIG, "sample.json")
    return score_prediction(
        record,
        CONFIG,
        source_prediction="sample.json",
        source_sha256="prediction-sha",
        config_sha256="config-sha",
    )


def scored_with_config(
    detections: list[dict[str, object]], config: RiskConfig
) -> dict[str, object]:
    record = validate_prediction_payload(payload(detections), config, "sample.json")
    return score_prediction(
        record,
        config,
        source_prediction="sample.json",
        source_sha256="prediction-sha",
        config_sha256="config-sha",
    )


def test_single_pothole_matches_approved_formula() -> None:
    result = scored([detection()])

    assert result["risk_score"] == 14.4
    assert result["risk_level"] == "low"
    d40 = result["class_breakdown"][3]
    assert d40["coverage_ratio"] == pytest.approx(0.01)
    assert d40["count_factor"] == pytest.approx(0.2)
    assert d40["coverage_factor"] == pytest.approx(0.4472136)


def test_confidence_changes_evidence_not_risk_score() -> None:
    low_confidence = scored([detection(confidence=0.3)])
    high_confidence = scored([detection(confidence=0.9)])

    assert low_confidence["risk_score"] == high_confidence["risk_score"]
    assert low_confidence["evidence"]["quality"] == "low"
    assert high_confidence["evidence"]["quality"] == "high"


def test_evidence_reports_rounded_mean_and_minimum_confidence() -> None:
    first = detection(confidence=0.87654321)
    second = detection(confidence=0.2)
    second["bbox_xyxy"] = [20, 20, 30, 30]

    result = scored([first, second])

    assert result["evidence"]["mean_detection_confidence"] == 0.538272
    assert result["evidence"]["minimum_detection_confidence"] == 0.2


def test_low_evidence_uses_canonical_audit_flag() -> None:
    result = scored([detection(confidence=0.3)])

    assert [flag["code"] for flag in result["audit_flags"]] == ["low_confidence_evidence"]


def test_empty_detection_is_zero_not_a_safety_claim() -> None:
    result = scored([])

    assert result["risk_score"] == 0.0
    assert result["risk_level"] == "low"
    assert result["evidence"]["quality"] == "not_applicable"
    assert result["evidence"]["mean_detection_confidence"] is None
    assert result["evidence"]["minimum_detection_confidence"] is None
    assert "does not replace" in result["limitation"]["en"]
    assert "不能替代" in result["limitation"]["zh"]


def test_all_classes_saturate_at_one_hundred() -> None:
    detections = []
    for class_id in CLASS_INFO:
        for _ in range(5):
            item = detection(class_id=class_id)
            item["bbox_xyxy"] = [0, 0, 30, 20]
            detections.append(item)

    result = scored(detections)

    assert result["risk_score"] == 100.0
    assert result["risk_level"] == "critical"


def test_same_class_overlap_contributes_covered_pixels_once() -> None:
    first = detection()
    second = detection()
    second["bbox_xyxy"] = [5, 0, 15, 10]

    result = scored([first, second])
    d40 = result["class_breakdown"][3]

    assert d40["count"] == 2
    assert d40["union_area_pixels"] == 150.0
    assert d40["coverage_ratio"] == pytest.approx(0.015)


def test_custom_mix_is_used_in_score_and_bilingual_explanation() -> None:
    custom = replace(CONFIG, count_mix=0.8, coverage_mix=0.2)

    result = scored_with_config([detection()], custom)

    assert result["risk_score"] == 10.0
    assert result["formula"]["parameters"]["count_mix"] == 0.8
    assert result["formula"]["parameters"]["coverage_mix"] == 0.2
    assert "0.8 * count_factor + 0.2 * coverage_factor" in result["formula"]["en"]
    assert "0.8 * 数量因子 + 0.2 * 覆盖因子" in result["formula"]["zh"]
