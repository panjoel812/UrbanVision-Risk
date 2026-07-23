from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from urbanvision_risk.errors import ProjectError, report_error
from urbanvision_risk.metrology.calibration import PlanarCalibration

FIELD_MARKER_IDS = {"TL": 17, "TR": 23, "BR": 42, "BL": 56}


def fiducial_error(context: str) -> ProjectError:
    return ProjectError(
        "E505",
        "现场 ArUco 标记识别或配置失败",
        "Field ArUco-marker detection or configuration failed",
        "确保四张标记均清晰、完整、位于同一平面，并使用默认 ID 17/23/42/56",
        "Keep all four markers sharp, complete, coplanar, and use IDs 17/23/42/56",
        context,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
    except OSError as error:
        raise fiducial_error(str(path)) from error
    return digest.hexdigest()


def _aruco_dictionary() -> object:
    return cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_100)


def detect_field_markers(
    image: NDArray[np.generic],
    *,
    marker_ids: dict[str, int] | None = None,
) -> tuple[
    tuple[
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
    ],
    dict[str, object],
]:
    array = np.asarray(image)
    if array.ndim == 3 and array.shape[2] == 3:
        gray = cv2.cvtColor(array.astype(np.uint8), cv2.COLOR_BGR2GRAY)
    elif array.ndim == 2:
        gray = array.astype(np.uint8)
    else:
        raise fiducial_error(f"image shape={array.shape!r}")

    expected = marker_ids or FIELD_MARKER_IDS
    if set(expected) != {"TL", "TR", "BR", "BL"} or len(set(expected.values())) != 4:
        raise fiducial_error(f"marker_ids={expected!r}")
    detector = cv2.aruco.ArucoDetector(
        _aruco_dictionary(),
        cv2.aruco.DetectorParameters(),
    )
    corners, ids, rejected = detector.detectMarkers(gray)
    detected: dict[int, NDArray[np.float32]] = {}
    if ids is not None:
        for marker_corners, marker_id in zip(corners, ids.flatten(), strict=True):
            detected[int(marker_id)] = marker_corners.reshape((4, 2)).astype(np.float32)
    missing = [
        f"{position}:{marker_id}"
        for position, marker_id in expected.items()
        if marker_id not in detected
    ]
    if missing:
        raise fiducial_error(
            f"missing={missing}, detected={sorted(detected)}, rejected_candidates={len(rejected)}"
        )

    ordered_corners = [detected[expected[position]] for position in ("TL", "TR", "BR", "BL")]
    centers_array = np.asarray(
        [np.mean(marker_corners, axis=0) for marker_corners in ordered_corners],
        dtype=np.float32,
    )
    contour = centers_array.reshape((-1, 1, 2))
    if not cv2.isContourConvex(contour) or abs(float(cv2.contourArea(contour))) < 64:
        raise fiducial_error("marker centers form a crossed or degenerate quadrilateral")

    perimeters = [
        float(cv2.arcLength(marker_corners.reshape((-1, 1, 2)), True))
        for marker_corners in ordered_corners
    ]
    image_area = float(gray.shape[0] * gray.shape[1])
    quadrilateral_area = abs(float(cv2.contourArea(contour)))
    centers = tuple(
        (float(center[0]), float(center[1])) for center in centers_array
    )
    return (
        (centers[0], centers[1], centers[2], centers[3]),
        {
            "dictionary": "DICT_4X4_100",
            "marker_ids": dict(expected),
            "detected_id_count": len(detected),
            "rejected_candidate_count": len(rejected),
            "minimum_marker_perimeter_pixels": round(min(perimeters), 4),
            "mean_marker_perimeter_pixels": round(float(np.mean(perimeters)), 4),
            "calibration_quadrilateral_area_pixels": round(quadrilateral_area, 4),
            "calibration_quadrilateral_image_ratio": round(
                quadrilateral_area / image_area, 6
            ),
        },
    )


def calibrate_from_field_markers(
    image: NDArray[np.generic],
    *,
    physical_width: float,
    physical_height: float,
    unit: str,
    pixels_per_unit: float,
    point_sigma_pixels: float = 1.0,
    marker_ids: dict[str, int] | None = None,
) -> tuple[PlanarCalibration, dict[str, object]]:
    points, quality = detect_field_markers(image, marker_ids=marker_ids)
    calibration = PlanarCalibration(
        image_points=points,
        physical_width=physical_width,
        physical_height=physical_height,
        unit=unit,
        pixels_per_unit=pixels_per_unit,
        point_sigma_pixels=point_sigma_pixels,
    )
    calibration.validate_for_image(np.asarray(image).shape[:2])
    return calibration, quality


def calibrate_image_file(
    *,
    source_image: Path,
    output: Path,
    physical_width: float,
    physical_height: float,
    unit: str,
    pixels_per_unit: float,
    point_sigma_pixels: float = 1.0,
) -> Path:
    if output.exists():
        raise ProjectError(
            "E204",
            "标定输出文件已经存在",
            "The calibration output file already exists",
            "保留现有文件并使用新的 --output",
            "Keep the existing file and use a new --output",
            str(output),
        )
    image = cv2.imread(str(source_image), cv2.IMREAD_COLOR)
    if image is None:
        raise fiducial_error(str(source_image))
    calibration, quality = calibrate_from_field_markers(
        image,
        physical_width=physical_width,
        physical_height=physical_height,
        unit=unit,
        pixels_per_unit=pixels_per_unit,
        point_sigma_pixels=point_sigma_pixels,
    )
    payload = calibration.to_dict()
    payload["field_detection"] = {
        **quality,
        "source_filename": source_image.name,
        "source_sha256": _sha256(source_image),
        "privacy": "Absolute source path omitted",
    }
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            stream.write(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            )
    except FileExistsError as error:
        raise ProjectError(
            "E204",
            "标定输出文件已经存在",
            "The calibration output file already exists",
            "保留现有文件并使用新的 --output",
            "Keep the existing file and use a new --output",
            str(output),
        ) from error
    except OSError as error:
        raise fiducial_error(str(output)) from error
    return output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect field markers and build calibration / 检测现场标记并生成标定"
    )
    parser.add_argument("--source-image", type=Path, required=True)
    parser.add_argument("--physical-width", type=float, required=True)
    parser.add_argument("--physical-height", type=float, required=True)
    parser.add_argument("--unit", choices=("mm", "cm", "m"), required=True)
    parser.add_argument("--pixels-per-unit", type=float, required=True)
    parser.add_argument("--point-sigma-pixels", type=float, default=1.0)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    try:
        output = calibrate_image_file(
            source_image=args.source_image,
            output=args.output,
            physical_width=args.physical_width,
            physical_height=args.physical_height,
            unit=args.unit,
            pixels_per_unit=args.pixels_per_unit,
            point_sigma_pixels=args.point_sigma_pixels,
        )
        print(f"[PASS] 现场标定完成 / Field calibration complete: {output.resolve()}")
        return 0
    except ProjectError as error:
        return report_error(error, debug=args.debug)


if __name__ == "__main__":
    raise SystemExit(main())
