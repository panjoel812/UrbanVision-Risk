from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from urbanvision_risk.errors import ProjectError

SUPPORTED_UNITS = {"mm", "cm", "m"}
MAX_RECTIFIED_PIXELS = 32_000_000
MAX_RECTIFIED_SIDE = 8192


def calibration_error(context: str) -> ProjectError:
    return ProjectError(
        "E501",
        "平面标定配置非法",
        "The planar-calibration configuration is invalid",
        "按文档提供 TL、TR、BR、BL 四点、真实宽高、单位和分辨率",
        "Provide TL, TR, BR, BL points, physical size, unit, and resolution as documented",
        context,
    )


def _finite_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise calibration_error(label)
    result = float(value)
    if not math.isfinite(result):
        raise calibration_error(label)
    return result


def _validate_points(points: NDArray[np.float64], context: str) -> None:
    if points.shape != (4, 2) or not np.all(np.isfinite(points)):
        raise calibration_error(context)
    pairwise_distances = [
        float(np.linalg.norm(points[left] - points[right]))
        for left in range(4)
        for right in range(left + 1, 4)
    ]
    if min(pairwise_distances) < 2.0:
        raise calibration_error(f"{context}: calibration points overlap")
    contour = points.astype(np.float32).reshape((-1, 1, 2))
    if not cv2.isContourConvex(contour) or abs(float(cv2.contourArea(contour))) < 16.0:
        raise calibration_error(f"{context}: quadrilateral is crossed or degenerate")


@dataclass(frozen=True, slots=True)
class PlanarCalibration:
    image_points: tuple[
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
    ]
    physical_width: float
    physical_height: float
    unit: str
    pixels_per_unit: float
    point_sigma_pixels: float = 1.5

    def __post_init__(self) -> None:
        points = self.points_array()
        _validate_points(points, "image_points")
        if self.unit not in SUPPORTED_UNITS:
            raise calibration_error(f"unit={self.unit!r}")
        for label, value in (
            ("physical_width", self.physical_width),
            ("physical_height", self.physical_height),
            ("pixels_per_unit", self.pixels_per_unit),
        ):
            if not math.isfinite(value) or value <= 0:
                raise calibration_error(f"{label}={value!r}")
        if not math.isfinite(self.point_sigma_pixels) or self.point_sigma_pixels < 0:
            raise calibration_error(f"point_sigma_pixels={self.point_sigma_pixels!r}")
        self.rectified_size()

    def points_array(self) -> NDArray[np.float64]:
        return np.asarray(self.image_points, dtype=np.float64)

    def rectified_size(self) -> tuple[int, int]:
        width = max(2, round(self.physical_width * self.pixels_per_unit) + 1)
        height = max(2, round(self.physical_height * self.pixels_per_unit) + 1)
        if (
            width > MAX_RECTIFIED_SIDE
            or height > MAX_RECTIFIED_SIDE
            or width * height > MAX_RECTIFIED_PIXELS
        ):
            raise calibration_error(
                f"rectified raster {width}x{height} exceeds the safety limit"
            )
        return width, height

    def validate_for_image(self, shape: tuple[int, int]) -> None:
        height, width = shape
        if height <= 0 or width <= 0:
            raise calibration_error(f"image shape={shape!r}")
        points = self.points_array()
        if (
            np.any(points[:, 0] < 0)
            or np.any(points[:, 0] > width - 1)
            or np.any(points[:, 1] < 0)
            or np.any(points[:, 1] > height - 1)
        ):
            raise calibration_error(
                f"image_points must stay within width={width}, height={height}"
            )

    def metric_homography(
        self,
        image_points: NDArray[np.float64] | None = None,
    ) -> NDArray[np.float64]:
        source = self.points_array() if image_points is None else np.asarray(image_points)
        _validate_points(source.astype(np.float64), "perturbed image_points")
        destination = np.asarray(
            [
                [0.0, 0.0],
                [self.physical_width, 0.0],
                [self.physical_width, self.physical_height],
                [0.0, self.physical_height],
            ],
            dtype=np.float32,
        )
        return cv2.getPerspectiveTransform(source.astype(np.float32), destination)

    def raster_homography(
        self,
        image_points: NDArray[np.float64] | None = None,
    ) -> NDArray[np.float64]:
        width, height = self.rectified_size()
        source = self.points_array() if image_points is None else np.asarray(image_points)
        _validate_points(source.astype(np.float64), "perturbed image_points")
        destination = np.asarray(
            [
                [0.0, 0.0],
                [float(width - 1), 0.0],
                [float(width - 1), float(height - 1)],
                [0.0, float(height - 1)],
            ],
            dtype=np.float32,
        )
        return cv2.getPerspectiveTransform(source.astype(np.float32), destination)

    def warp_mask(self, mask: NDArray[np.generic]) -> NDArray[np.bool_]:
        binary = np.asarray(mask) > 0
        if binary.ndim != 2:
            raise calibration_error(f"mask shape={binary.shape!r}")
        self.validate_for_image(binary.shape)
        size = self.rectified_size()
        warped = cv2.warpPerspective(
            binary.astype(np.uint8) * 255,
            self.raster_homography(),
            size,
            flags=cv2.INTER_NEAREST,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )
        return warped > 0

    def to_dict(self) -> dict[str, object]:
        width, height = self.rectified_size()
        return {
            "schema_version": "planar-calibration-v3.0.0",
            "point_order": ["TL", "TR", "BR", "BL"],
            "image_points": [list(point) for point in self.image_points],
            "physical_size": {
                "width": self.physical_width,
                "height": self.physical_height,
                "unit": self.unit,
            },
            "pixels_per_unit": self.pixels_per_unit,
            "point_sigma_pixels": self.point_sigma_pixels,
            "rectified_raster": {"width": width, "height": height},
        }


def calibration_from_dict(payload: object, context: str = "calibration") -> PlanarCalibration:
    if not isinstance(payload, dict):
        raise calibration_error(context)
    points_raw = payload.get("image_points")
    physical_size = payload.get("physical_size")
    if not isinstance(points_raw, list) or len(points_raw) != 4:
        raise calibration_error(f"{context}: image_points")
    points: list[tuple[float, float]] = []
    for index, point in enumerate(points_raw):
        if not isinstance(point, list) or len(point) != 2:
            raise calibration_error(f"{context}: image_points[{index}]")
        points.append(
            (
                _finite_number(point[0], f"image_points[{index}][0]"),
                _finite_number(point[1], f"image_points[{index}][1]"),
            )
        )
    if not isinstance(physical_size, dict):
        raise calibration_error(f"{context}: physical_size")
    unit = physical_size.get("unit")
    if not isinstance(unit, str):
        raise calibration_error(f"{context}: physical_size.unit")
    calibration = PlanarCalibration(
        image_points=(points[0], points[1], points[2], points[3]),
        physical_width=_finite_number(
            physical_size.get("width"), f"{context}: physical_size.width"
        ),
        physical_height=_finite_number(
            physical_size.get("height"), f"{context}: physical_size.height"
        ),
        unit=unit,
        pixels_per_unit=_finite_number(
            payload.get("pixels_per_unit"), f"{context}: pixels_per_unit"
        ),
        point_sigma_pixels=_finite_number(
            payload.get("point_sigma_pixels", 1.5),
            f"{context}: point_sigma_pixels",
        ),
    )
    return calibration


def load_calibration(path: Path) -> PlanarCalibration:
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise calibration_error(str(path)) from error
    return calibration_from_dict(payload, str(path))
