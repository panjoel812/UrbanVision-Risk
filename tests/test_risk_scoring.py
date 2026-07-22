from collections import Counter
from pathlib import Path

import pytest

from urbanvision_risk.data.voc import CLASS_INFO
from urbanvision_risk.risk.config import load_risk_config
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


def test_empty_detection_is_zero_not_a_safety_claim() -> None:
    result = scored([])

    assert result["risk_score"] == 0.0
    assert result["risk_level"] == "low"
    assert result["evidence"]["quality"] == "not_applicable"
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
