from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class DetectionCandidate:
    class_id: int
    confidence: float
    bbox_xyxy: tuple[float, float, float, float]


def _axis_starts(length: int, tile_size: int, overlap: float) -> tuple[int, ...]:
    if length <= tile_size:
        return (0,)
    step = max(1, round(tile_size * (1 - overlap)))
    starts = list(range(0, length - tile_size + 1, step))
    last = length - tile_size
    if starts[-1] != last:
        starts.append(last)
    return tuple(starts)


def tile_windows(
    width: int,
    height: int,
    *,
    tile_size: int = 1024,
    overlap: float = 0.20,
) -> tuple[tuple[int, int, int, int], ...]:
    if width <= 0 or height <= 0 or tile_size <= 0:
        raise ValueError("image and tile dimensions must be positive")
    if not 0 <= overlap < 1:
        raise ValueError("overlap must be in [0, 1)")
    return tuple(
        (x, y, min(x + tile_size, width), min(y + tile_size, height))
        for y in _axis_starts(height, tile_size, overlap)
        for x in _axis_starts(width, tile_size, overlap)
    )


def extract_candidates(
    result: Any,
    *,
    offset_x: int = 0,
    offset_y: int = 0,
    image_width: int,
    image_height: int,
) -> list[DetectionCandidate]:
    candidates: list[DetectionCandidate] = []
    for box in result.boxes:
        x1, y1, x2, y2 = (float(value) for value in box.xyxy[0].tolist())
        translated = (
            max(0.0, min(float(image_width), x1 + offset_x)),
            max(0.0, min(float(image_height), y1 + offset_y)),
            max(0.0, min(float(image_width), x2 + offset_x)),
            max(0.0, min(float(image_height), y2 + offset_y)),
        )
        if translated[0] >= translated[2] or translated[1] >= translated[3]:
            continue
        candidates.append(
            DetectionCandidate(
                class_id=int(box.cls[0].item()),
                confidence=float(box.conf[0].item()),
                bbox_xyxy=translated,
            )
        )
    return candidates


def _intersection_over_union(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> float:
    x1 = max(first[0], second[0])
    y1 = max(first[1], second[1])
    x2 = min(first[2], second[2])
    y2 = min(first[3], second[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if intersection == 0:
        return 0.0
    first_area = (first[2] - first[0]) * (first[3] - first[1])
    second_area = (second[2] - second[0]) * (second[3] - second[1])
    return intersection / (first_area + second_area - intersection)


def class_aware_nms(
    candidates: list[DetectionCandidate],
    *,
    iou_threshold: float = 0.50,
) -> list[DetectionCandidate]:
    if not 0 <= iou_threshold <= 1:
        raise ValueError("iou_threshold must be in [0, 1]")
    ordered = sorted(
        candidates,
        key=lambda item: (-item.confidence, item.class_id, item.bbox_xyxy),
    )
    kept: list[DetectionCandidate] = []
    for candidate in ordered:
        duplicate = any(
            candidate.class_id == existing.class_id
            and _intersection_over_union(candidate.bbox_xyxy, existing.bbox_xyxy)
            >= iou_threshold
            for existing in kept
        )
        if not duplicate:
            kept.append(candidate)
    return kept
