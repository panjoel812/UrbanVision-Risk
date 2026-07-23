from __future__ import annotations

import hashlib
import io
import json
import math
import secrets
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from urbanvision_risk.detection.config import validate_run_name
from urbanvision_risk.errors import ProjectError
from urbanvision_risk.metrology.calibration import (
    PlanarCalibration,
    calibration_from_dict,
)
from urbanvision_risk.metrology.demo import synthetic_field_sample
from urbanvision_risk.metrology.fiducials import calibrate_from_field_markers
from urbanvision_risk.metrology.measure import create_metrology_run
from urbanvision_risk.paths import ProjectPaths, get_paths

MAX_METROLOGY_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_METROLOGY_PIXELS = 20_000_000
SOURCE_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
MASK_CONTENT_TYPES = frozenset({"image/png", "image/webp"})
CALIBRATION_MODES = frozenset({"pixel", "manual", "aruco"})
METROLOGY_ARTIFACTS = frozenset(
    {
        "mask.png",
        "skeleton.png",
        "width-heatmap.png",
        "overlay.jpg",
        "rectified-mask.png",
        "rectified-skeleton.png",
        "rectified-width-heatmap.png",
        "rectified-overlay.jpg",
        "measurement.json",
    }
)


def _input_error(context: str) -> ProjectError:
    return ProjectError(
        "E506",
        "量测网页输入无效",
        "The metrology web input is invalid",
        "检查原图、白色裂缝掩膜、标定模式、四点顺序和真实尺寸",
        "Check the source, white crack mask, calibration mode, point order, and dimensions",
        context,
    )


def _safe_filename(filename: str | None, fallback: str) -> str:
    cleaned = (filename or fallback).replace("\\", "/").rsplit("/", 1)[-1].strip()
    return (cleaned or fallback)[:255]


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _new_metrology_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dt%H%M%S")
    return f"metrology-{timestamp}-{secrets.token_hex(4)}"


def _decode_source(content: bytes, content_type: str) -> tuple[np.ndarray, tuple[int, int]]:
    if content_type not in SOURCE_CONTENT_TYPES:
        raise _input_error(f"source content_type={content_type or 'missing'}")
    if not content or len(content) > MAX_METROLOGY_UPLOAD_BYTES:
        raise _input_error(f"source bytes={len(content)}")
    try:
        with Image.open(io.BytesIO(content)) as opened:
            width, height = opened.size
            if width <= 0 or height <= 0 or width * height > MAX_METROLOGY_PIXELS:
                raise _input_error(f"source dimensions={width}x{height}")
            opened.load()
            normalized = ImageOps.exif_transpose(opened).convert("RGB")
    except ProjectError:
        raise
    except (Image.DecompressionBombError, OSError, UnidentifiedImageError) as error:
        raise _input_error("source image decoding failed") from error
    rgb = np.asarray(normalized, dtype=np.uint8)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), (normalized.height, normalized.width)


def _decode_mask(
    content: bytes,
    content_type: str,
    expected_shape: tuple[int, int],
) -> np.ndarray:
    if content_type not in MASK_CONTENT_TYPES:
        raise _input_error(f"mask content_type={content_type or 'missing'}")
    if not content or len(content) > MAX_METROLOGY_UPLOAD_BYTES:
        raise _input_error(f"mask bytes={len(content)}")
    try:
        with Image.open(io.BytesIO(content)) as opened:
            width, height = opened.size
            if width <= 0 or height <= 0 or width * height > MAX_METROLOGY_PIXELS:
                raise _input_error(f"mask dimensions={width}x{height}")
            opened.load()
            grayscale = opened.convert("L")
    except ProjectError:
        raise
    except (Image.DecompressionBombError, OSError, UnidentifiedImageError) as error:
        raise _input_error("mask image decoding failed") from error
    if (grayscale.height, grayscale.width) != expected_shape:
        raise _input_error(
            f"source shape={expected_shape}, mask shape={(grayscale.height, grayscale.width)}"
        )
    mask = np.asarray(grayscale, dtype=np.uint8) >= 128
    foreground = int(np.count_nonzero(mask))
    if foreground < 3:
        raise _input_error(f"mask foreground pixels={foreground}")
    return mask


def _finite_positive(value: float | None, label: str) -> float:
    if value is None or isinstance(value, bool):
        raise _input_error(f"{label}=missing")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise _input_error(f"{label}={value!r}")
    return result


def _finite_nonnegative(value: float | None, label: str) -> float:
    if value is None or isinstance(value, bool):
        raise _input_error(f"{label}=missing")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise _input_error(f"{label}={value!r}")
    return result


def _calibration(
    *,
    mode: str,
    source_image: np.ndarray,
    manual_points: str | None,
    physical_width: float | None,
    physical_height: float | None,
    unit: str | None,
    pixels_per_unit: float | None,
    point_sigma_pixels: float | None,
) -> tuple[PlanarCalibration | None, dict[str, object]]:
    if mode not in CALIBRATION_MODES:
        raise _input_error(f"calibration_mode={mode!r}")
    if mode == "pixel":
        return None, {
            "mode": "pixel_only",
            "physical_measurement_valid": False,
        }
    width = _finite_positive(physical_width, "physical_width")
    height = _finite_positive(physical_height, "physical_height")
    resolution = _finite_positive(pixels_per_unit, "pixels_per_unit")
    sigma = _finite_nonnegative(point_sigma_pixels, "point_sigma_pixels")
    if unit not in {"mm", "cm", "m"}:
        raise _input_error(f"unit={unit!r}")

    if mode == "aruco":
        calibration, quality = calibrate_from_field_markers(
            source_image,
            physical_width=width,
            physical_height=height,
            unit=unit,
            pixels_per_unit=resolution,
            point_sigma_pixels=sigma,
        )
        return calibration, {
            "mode": "aruco_auto",
            "field_detection": quality,
        }

    try:
        points = json.loads(manual_points or "")
    except json.JSONDecodeError as error:
        raise _input_error("manual_points is not valid JSON") from error
    calibration = calibration_from_dict(
        {
            "image_points": points,
            "physical_size": {
                "width": width,
                "height": height,
                "unit": unit,
            },
            "pixels_per_unit": resolution,
            "point_sigma_pixels": sigma,
        },
        "manual web calibration",
    )
    calibration.validate_for_image(source_image.shape[:2])
    return calibration, {
        "mode": "manual_four_point",
        "point_order": ["TL", "TR", "BR", "BL"],
    }


class LocalMetrologyService:
    """Create immutable, fully local crack-metrology runs for the web app."""

    def __init__(
        self,
        *,
        paths: ProjectPaths | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.paths = paths or get_paths()
        self._id_factory = id_factory or _new_metrology_id
        self._write_lock = threading.Lock()

    def _response(self, run_id: str, output_dir: Path) -> dict[str, object]:
        try:
            measurement = json.loads(
                (output_dir / "measurement.json").read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as error:
            raise ProjectError(
                "E504",
                "量测结果无法读取",
                "The metrology result cannot be read",
                "保留输出目录并检查磁盘与 measurement.json",
                "Keep the output directory and inspect the disk and measurement.json",
                str(output_dir),
            ) from error
        artifact_urls = {
            name: f"/api/metrology/runs/{run_id}/{name}"
            for name in sorted(METROLOGY_ARTIFACTS)
            if (output_dir / name).is_file()
        }
        return {
            "run_id": run_id,
            "local_only": True,
            "measurement": measurement,
            "artifacts": artifact_urls,
        }

    def analyze_bytes(
        self,
        *,
        source_content: bytes,
        source_filename: str | None,
        source_content_type: str,
        mask_content: bytes,
        mask_filename: str | None,
        mask_content_type: str,
        calibration_mode: str,
        manual_points: str | None = None,
        physical_width: float | None = None,
        physical_height: float | None = None,
        unit: str | None = None,
        pixels_per_unit: float | None = None,
        point_sigma_pixels: float | None = None,
        uncertainty_samples: int = 64,
        segmentation_radius_pixels: int = 1,
    ) -> dict[str, object]:
        if not 0 <= uncertainty_samples <= 512:
            raise _input_error(f"uncertainty_samples={uncertainty_samples}")
        if not 0 <= segmentation_radius_pixels <= 5:
            raise _input_error(
                f"segmentation_radius_pixels={segmentation_radius_pixels}"
            )
        source_image, source_shape = _decode_source(
            source_content,
            source_content_type,
        )
        mask = _decode_mask(mask_content, mask_content_type, source_shape)
        calibration, calibration_evidence = _calibration(
            mode=calibration_mode,
            source_image=source_image,
            manual_points=manual_points,
            physical_width=physical_width,
            physical_height=physical_height,
            unit=unit,
            pixels_per_unit=pixels_per_unit,
            point_sigma_pixels=point_sigma_pixels,
        )
        run_id = validate_run_name(self._id_factory())
        input_evidence = {
            "kind": "local_web_metrology",
            "source": {
                "filename": _safe_filename(source_filename, "road-image"),
                "sha256": _sha256(source_content),
            },
            "mask": {
                "filename": _safe_filename(mask_filename, "browser-mask.png"),
                "sha256": _sha256(mask_content),
                "foreground_pixels": int(np.count_nonzero(mask)),
            },
            "calibration": calibration_evidence,
            "privacy": "No absolute input path is recorded; processing stays on loopback",
        }
        with self._write_lock:
            output_dir = create_metrology_run(
                mask=mask,
                output_name=run_id,
                calibration=calibration,
                source_image=source_image,
                input_evidence=input_evidence,
                uncertainty_samples=uncertainty_samples,
                segmentation_radius_pixels=segmentation_radius_pixels,
                paths=self.paths,
            )
        return self._response(run_id, output_dir)

    def demo(self) -> dict[str, object]:
        run_id = validate_run_name(self._id_factory())
        source, mask, calibration = synthetic_field_sample(seed=42)
        with self._write_lock:
            output_dir = create_metrology_run(
                mask=mask,
                output_name=run_id,
                calibration=calibration,
                source_image=source,
                uncertainty_samples=128,
                seed=42,
                input_evidence={
                    "kind": "deterministic_web_demo",
                    "seed": 42,
                    "claim_boundary": (
                        "Algorithm demonstration only; not field-accuracy evidence"
                    ),
                },
                paths=self.paths,
            )
        return self._response(run_id, output_dir)

    def artifact_path(self, run_id: str, artifact_name: str) -> Path:
        safe_id = validate_run_name(run_id)
        if artifact_name not in METROLOGY_ARTIFACTS:
            raise ProjectError(
                "E201",
                "量测文件不存在",
                "The metrology artifact does not exist",
                "检查量测编号和文件名",
                "Check the metrology run ID and artifact name",
                artifact_name,
            )
        path = self.paths.metrology / safe_id / artifact_name
        if not path.is_file():
            raise ProjectError(
                "E201",
                "量测文件不存在",
                "The metrology artifact does not exist",
                "检查量测编号，或重新运行量测",
                "Check the metrology run ID or rerun metrology",
                f"{safe_id}/{artifact_name}",
            )
        return path
