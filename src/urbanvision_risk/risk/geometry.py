from __future__ import annotations

import math
from collections.abc import Sequence
from itertools import pairwise

from urbanvision_risk.errors import ProjectError

Rectangle = tuple[float, float, float, float]


def _geometry_error(context: str) -> ProjectError:
    return ProjectError(
        "E403",
        "检测框几何信息非法",
        "Detection-box geometry is invalid",
        "检查图片尺寸和 bbox_xyxy 坐标",
        "Inspect the image dimensions and bbox_xyxy coordinates",
        context,
    )


def _number(value: object, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _geometry_error(context)
    result = float(value)
    if not math.isfinite(result):
        raise _geometry_error(context)
    return result


def clip_rectangle(
    box: Sequence[object],
    *,
    width: int,
    height: int,
    tolerance: float,
    context: str,
) -> tuple[Rectangle, bool]:
    if (
        len(box) != 4
        or isinstance(width, bool)
        or isinstance(height, bool)
        or not isinstance(width, int)
        or not isinstance(height, int)
        or width <= 0
        or height <= 0
        or not math.isfinite(tolerance)
        or tolerance < 0
    ):
        raise _geometry_error(context)

    x1, y1, x2, y2 = (_number(value, context) for value in box)
    if x2 <= x1 or y2 <= y1:
        raise _geometry_error(context)
    if x1 < -tolerance or y1 < -tolerance or x2 > width + tolerance or y2 > height + tolerance:
        raise _geometry_error(context)

    clipped_rectangle = (
        max(0.0, min(float(width), x1)),
        max(0.0, min(float(height), y1)),
        max(0.0, min(float(width), x2)),
        max(0.0, min(float(height), y2)),
    )
    if clipped_rectangle[2] <= clipped_rectangle[0] or clipped_rectangle[3] <= clipped_rectangle[1]:
        raise _geometry_error(context)
    return clipped_rectangle, clipped_rectangle != (x1, y1, x2, y2)


def rectangle_union_area(rectangles: Sequence[Rectangle]) -> float:
    if not rectangles:
        return 0.0

    x_coordinates = sorted({x for rectangle in rectangles for x in (rectangle[0], rectangle[2])})
    area = 0.0
    for left, right in pairwise(x_coordinates):
        if right <= left:
            continue
        intervals = sorted((y1, y2) for x1, y1, x2, y2 in rectangles if x1 < right and x2 > left)
        if not intervals:
            continue
        covered_y = 0.0
        start, end = intervals[0]
        for next_start, next_end in intervals[1:]:
            if next_start > end:
                covered_y += end - start
                start, end = next_start, next_end
            else:
                end = max(end, next_end)
        covered_y += end - start
        area += (right - left) * covered_y
    return area
