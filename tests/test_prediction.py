import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from urbanvision_risk.detection.predict import predict_source, serialize_result
from urbanvision_risk.errors import ProjectError
from urbanvision_risk.paths import get_paths


class Scalar:
    def __init__(self, value: float) -> None:
        self.value = value

    def item(self) -> float:
        return self.value


class Vector:
    def __init__(self, values: list[float]) -> None:
        self.values = values

    def tolist(self) -> list[float]:
        return self.values


def _result(path: Path, boxes: list[object]) -> SimpleNamespace:
    return SimpleNamespace(path=str(path), orig_shape=(300, 400), boxes=boxes)


def test_serialize_result_contains_engineering_class_names() -> None:
    box = SimpleNamespace(
        cls=[Scalar(3)],
        conf=[Scalar(0.87)],
        xyxy=[Vector([120.0, 80.0, 260.0, 210.0])],
    )
    result = _result(Path("road.jpg"), [box])

    payload = serialize_result(result, Path("best.pt"), confidence=0.25)

    assert payload["image_dimensions"] == {"width": 400, "height": 300}
    assert payload["counts"] == {"D00": 0, "D10": 0, "D20": 0, "D40": 1}
    assert payload["detections"][0] == {
        "class_id": 3,
        "code": "D40",
        "name_en": "Pothole",
        "name_zh": "坑洞",
        "confidence": 0.87,
        "bbox_xyxy": [120.0, 80.0, 260.0, 210.0],
    }


def test_serialize_empty_detection_is_explicit() -> None:
    result = _result(Path("clear-road.jpg"), [])

    payload = serialize_result(result, Path("best.pt"), confidence=0.25)

    assert payload["detections"] == []
    assert payload["message_zh"] == "在当前置信度阈值下未检测到道路缺陷"
    assert (
        payload["message_en"]
        == "No road damage was detected at the current confidence threshold"
    )


def test_predict_source_writes_annotated_image_and_json(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)
    checkpoint = paths.experiments / "china-baseline-001" / "weights" / "best.pt"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_bytes(b"checkpoint")
    source = tmp_path / "road.jpg"
    source.write_bytes(b"image")
    box = SimpleNamespace(
        cls=[Scalar(0)],
        conf=[Scalar(0.75)],
        xyxy=[Vector([1.0, 2.0, 30.0, 40.0])],
    )

    class FakeResult(SimpleNamespace):
        def save(self, filename: str) -> None:
            Path(filename).write_bytes(b"annotated")

    result = FakeResult(path=str(source), orig_shape=(300, 400), boxes=[box])
    calls: dict[str, object] = {}

    class FakeModel:
        def predict(self, **kwargs: object) -> list[FakeResult]:
            calls.update(kwargs)
            return [result]

    output = predict_source(
        "china-baseline-001",
        source,
        paths=paths,
        model_factory=lambda _: FakeModel(),
    )

    payload = json.loads((output / "road.json").read_text(encoding="utf-8"))
    assert (output / "road-annotated.jpg").read_bytes() == b"annotated"
    assert payload["counts"]["D00"] == 1
    assert calls["device"] == "mps"
    assert calls["conf"] == 0.25


def test_predict_source_rejects_invalid_confidence(tmp_path: Path) -> None:
    with pytest.raises(ProjectError, match="E302"):
        predict_source("china-baseline-001", tmp_path, confidence=1.1, paths=get_paths(tmp_path))
