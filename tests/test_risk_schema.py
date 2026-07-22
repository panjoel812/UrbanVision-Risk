from pathlib import Path

import pytest

from urbanvision_risk.errors import ProjectError
from urbanvision_risk.risk.config import load_risk_config
from urbanvision_risk.risk.schema import validate_prediction_payload

ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_risk_config(ROOT / "configs" / "risk-v0.2.yaml")


def prediction_payload() -> dict[str, object]:
    return {
        "source_image": "/tmp/road.jpg",
        "model_checkpoint": "/tmp/best.pt",
        "confidence_threshold": 0.25,
        "image_dimensions": {"width": 100, "height": 80},
        "detections": [
            {
                "class_id": 3,
                "code": "D40",
                "name_en": "Pothole",
                "name_zh": "坑洞",
                "confidence": 0.8,
                "bbox_xyxy": [10, 20, 30, 40],
            }
        ],
        "counts": {"D00": 0, "D10": 0, "D20": 0, "D40": 1},
    }


def test_valid_payload_becomes_typed_record() -> None:
    record = validate_prediction_payload(prediction_payload(), CONFIG, "sample.json")

    assert record.width == 100
    assert record.height == 80
    assert record.counts["D40"] == 1
    assert record.detections[0].rectangle == (10.0, 20.0, 30.0, 40.0)
    assert record.detections[0].clipped is False


def test_validated_counts_are_read_only() -> None:
    record = validate_prediction_payload(prediction_payload(), CONFIG, "sample.json")

    with pytest.raises(TypeError):
        record.counts["D40"] = 0  # type: ignore[index]


def test_small_coordinate_drift_is_clipped_and_audited() -> None:
    payload = prediction_payload()
    payload["detections"][0]["bbox_xyxy"] = [-0.5, 20, 30, 40]  # type: ignore[index]

    record = validate_prediction_payload(payload, CONFIG, "sample.json")

    assert record.detections[0].rectangle[0] == 0.0
    assert record.detections[0].clipped is True


def test_missing_required_field_is_e402() -> None:
    payload = prediction_payload()
    payload.pop("image_dimensions")

    with pytest.raises(ProjectError, match="E402"):
        validate_prediction_payload(payload, CONFIG, "sample.json")


def test_counts_must_match_detections() -> None:
    payload = prediction_payload()
    payload["counts"] = {"D00": 0, "D10": 0, "D20": 0, "D40": 0}

    with pytest.raises(ProjectError, match="E403"):
        validate_prediction_payload(payload, CONFIG, "sample.json")


def test_auxiliary_detection_requires_five_class_counts() -> None:
    payload = prediction_payload()
    payload["detections"].append(
        {
            "class_id": 4,
            "code": "Repair",
            "name_en": "Previously repaired area",
            "name_zh": "历史修补区域",
            "confidence": 0.9,
            "bbox_xyxy": [40, 20, 70, 50],
        }
    )

    with pytest.raises(ProjectError, match="E403"):
        validate_prediction_payload(payload, CONFIG, "sample.json")


def test_class_metadata_must_be_canonical() -> None:
    payload = prediction_payload()
    payload["detections"][0]["class_id"] = 99  # type: ignore[index]

    with pytest.raises(ProjectError, match="E403"):
        validate_prediction_payload(payload, CONFIG, "sample.json")


def test_box_far_outside_image_is_e403() -> None:
    payload = prediction_payload()
    payload["detections"][0]["bbox_xyxy"] = [-2, 20, 30, 40]  # type: ignore[index]

    with pytest.raises(ProjectError, match="E403"):
        validate_prediction_payload(payload, CONFIG, "sample.json")


@pytest.mark.parametrize("coordinate", ["ten", True])
def test_bbox_coordinate_wrong_type_is_bilingual_e402(coordinate: object) -> None:
    payload = prediction_payload()
    payload["detections"][0]["bbox_xyxy"] = [0, 20, coordinate, 40]  # type: ignore[index]

    with pytest.raises(ProjectError) as caught:
        validate_prediction_payload(payload, CONFIG, "sample.json")

    assert caught.value.code == "E402"
    assert "类型错误" in caught.value.message_zh
    assert "invalid type" in caught.value.message_en


def test_empty_detection_payload_with_optional_messages_is_valid() -> None:
    payload = prediction_payload()
    payload["detections"] = []
    payload["counts"] = {"D00": 0, "D10": 0, "D20": 0, "D40": 0}
    payload["message_zh"] = "没有检测到道路缺陷"
    payload["message_en"] = "No road damage detected"

    record = validate_prediction_payload(payload, CONFIG, "empty.json")

    assert record.detections == ()
    assert dict(record.counts) == {"D00": 0, "D10": 0, "D20": 0, "D40": 0}


def test_overflowed_confidence_is_e403() -> None:
    payload = prediction_payload()
    payload["confidence_threshold"] = 10**1000

    with pytest.raises(ProjectError, match="E403"):
        validate_prediction_payload(payload, CONFIG, "sample.json")


def test_overflowed_coordinate_is_e403() -> None:
    payload = prediction_payload()
    payload["detections"][0]["bbox_xyxy"] = [0, 20, 10**1000, 40]  # type: ignore[index]

    with pytest.raises(ProjectError, match="E403"):
        validate_prediction_payload(payload, CONFIG, "sample.json")


def test_image_area_too_large_for_finite_float_is_bilingual_e403() -> None:
    payload = prediction_payload()
    payload["image_dimensions"] = {"width": 10**1000, "height": 1}
    payload["detections"] = []
    payload["counts"] = {"D00": 0, "D10": 0, "D20": 0, "D40": 0}

    with pytest.raises(ProjectError) as caught:
        validate_prediction_payload(payload, CONFIG, "huge.json")

    assert caught.value.code == "E403"
    assert "互相矛盾" in caught.value.message_zh
    assert "inconsistent" in caught.value.message_en
    assert "image_dimensions.width*height" in caught.value.context
