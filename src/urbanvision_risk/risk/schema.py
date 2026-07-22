from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from urbanvision_risk.data.voc import CLASS_INFO
from urbanvision_risk.errors import ProjectError
from urbanvision_risk.risk.config import RiskConfig
from urbanvision_risk.risk.geometry import Rectangle, clip_rectangle


@dataclass(frozen=True, slots=True)
class DetectionRecord:
    class_id: int
    code: str
    name_en: str
    name_zh: str
    confidence: float
    rectangle: Rectangle
    clipped: bool


@dataclass(frozen=True, slots=True)
class PredictionRecord:
    source_image: str
    model_checkpoint: str
    confidence_threshold: float
    width: int
    height: int
    detections: tuple[DetectionRecord, ...]
    counts: Mapping[str, int]


def _malformed(context: str, field: str) -> ProjectError:
    return ProjectError(
        "E402",
        "预测 JSON 结构不完整或类型错误",
        "Prediction JSON has a missing field or invalid type",
        "重新运行 v0.1 预测，或检查该 JSON 字段",
        "Rerun v0.1 prediction or inspect this JSON field",
        f"{context}: {field}",
    )


def _semantic(context: str, field: str) -> ProjectError:
    return ProjectError(
        "E403",
        "预测 JSON 的值互相矛盾",
        "Prediction JSON contains inconsistent values",
        "不要手工修改预测 JSON；重新运行 v0.1 预测",
        "Do not hand-edit prediction JSON; rerun v0.1 prediction",
        f"{context}: {field}",
    )


def _mapping(value: object, context: str, field: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise _malformed(context, field)
    return value


def _text(value: object, context: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _malformed(context, field)
    return value


def _integer(value: object, context: str, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _malformed(context, field)
    return value


def _number(value: object, context: str, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _malformed(context, field)
    try:
        result = float(value)
    except OverflowError:
        raise _semantic(context, field) from None
    if not math.isfinite(result):
        raise _semantic(context, field)
    return result


def validate_prediction_payload(
    payload: object,
    config: RiskConfig,
    context: str,
) -> PredictionRecord:
    root = _mapping(payload, context, "root")
    required = {
        "source_image",
        "model_checkpoint",
        "confidence_threshold",
        "image_dimensions",
        "detections",
        "counts",
    }
    if not required.issubset(root):
        raise _malformed(context, "required fields")

    dimensions = _mapping(root["image_dimensions"], context, "image_dimensions")
    if not {"width", "height"}.issubset(dimensions):
        raise _malformed(context, "image_dimensions")
    width = _integer(dimensions["width"], context, "image_dimensions.width")
    height = _integer(dimensions["height"], context, "image_dimensions.height")
    if width <= 0 or height <= 0:
        raise _semantic(context, "image_dimensions")
    try:
        image_area = float(width * height)
    except OverflowError:
        raise _semantic(context, "image_dimensions.width*height") from None
    if not math.isfinite(image_area):
        raise _semantic(context, "image_dimensions.width*height")

    confidence_threshold = _number(root["confidence_threshold"], context, "confidence_threshold")
    if not 0 <= confidence_threshold <= 1:
        raise _semantic(context, "confidence_threshold")
    raw_detections = root["detections"]
    if not isinstance(raw_detections, list):
        raise _malformed(context, "detections")

    detections: list[DetectionRecord] = []
    observed: Counter[str] = Counter()
    for index, raw_detection in enumerate(raw_detections):
        field = f"detections[{index}]"
        detection = _mapping(raw_detection, context, field)
        expected_fields = {
            "class_id",
            "code",
            "name_en",
            "name_zh",
            "confidence",
            "bbox_xyxy",
        }
        if not expected_fields.issubset(detection):
            raise _malformed(context, field)
        class_id = _integer(detection["class_id"], context, f"{field}.class_id")
        details = CLASS_INFO.get(class_id)
        if details is None:
            raise _semantic(context, f"{field}.class_id")
        code = _text(detection["code"], context, f"{field}.code")
        name_en = _text(detection["name_en"], context, f"{field}.name_en")
        name_zh = _text(detection["name_zh"], context, f"{field}.name_zh")
        if (code, name_en, name_zh) != (
            details["code"],
            details["name_en"],
            details["name_zh"],
        ):
            raise _semantic(context, f"{field}.class metadata")
        confidence = _number(detection["confidence"], context, f"{field}.confidence")
        if not 0 <= confidence <= 1:
            raise _semantic(context, f"{field}.confidence")
        raw_box = detection["bbox_xyxy"]
        if not isinstance(raw_box, list) or len(raw_box) != 4:
            raise _malformed(context, f"{field}.bbox_xyxy")
        if any(
            isinstance(coordinate, bool) or not isinstance(coordinate, (int, float))
            for coordinate in raw_box
        ):
            raise _malformed(context, f"{field}.bbox_xyxy")
        try:
            rectangle, clipped = clip_rectangle(
                raw_box,
                width=width,
                height=height,
                tolerance=config.coordinate_tolerance_pixels,
                context=f"{context}: {field}.bbox_xyxy",
            )
        except OverflowError:
            raise _semantic(context, f"{field}.bbox_xyxy") from None
        detections.append(
            DetectionRecord(
                class_id=class_id,
                code=code,
                name_en=name_en,
                name_zh=name_zh,
                confidence=confidence,
                rectangle=rectangle,
                clipped=clipped,
            )
        )
        observed[code] += 1

    raw_counts = _mapping(root["counts"], context, "counts")
    class_codes = tuple(details["code"] for details in CLASS_INFO.values())
    if set(raw_counts) != set(class_codes):
        raise _semantic(context, "counts keys")
    counts = {code: _integer(raw_counts[code], context, f"counts.{code}") for code in class_codes}
    if any(count < 0 for count in counts.values()) or any(
        counts[code] != observed[code] for code in class_codes
    ):
        raise _semantic(context, "counts")

    return PredictionRecord(
        source_image=_text(root["source_image"], context, "source_image"),
        model_checkpoint=_text(root["model_checkpoint"], context, "model_checkpoint"),
        confidence_threshold=confidence_threshold,
        width=width,
        height=height,
        detections=tuple(detections),
        counts=MappingProxyType(counts),
    )
