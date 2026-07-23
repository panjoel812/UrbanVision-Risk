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

from urbanvision_risk.app.crack_proposal import propose_crack_mask
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
COMPARISON_ARTIFACTS = frozenset({"change-map.png"})
PROPOSAL_ARTIFACTS = frozenset({"proposal-mask.png", "evidence.json"})
MAX_FRAME_DIMENSION_MISMATCH_RATIO = 0.05
MAX_CHANGE_MAP_PIXELS_PER_METER = 2_000.0
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


def _new_record_id(prefix: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dt%H%M%S")
    return f"{prefix}-{timestamp}-{secrets.token_hex(4)}"


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
            rgba = opened.convert("RGBA")
            black = Image.new("RGBA", rgba.size, (0, 0, 0, 255))
            grayscale = Image.alpha_composite(black, rgba).convert("L")
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
        record_id_factory: Callable[[str], str] | None = None,
    ) -> None:
        self.paths = paths or get_paths()
        self._id_factory = id_factory or _new_metrology_id
        self._record_id_factory = record_id_factory or _new_record_id
        self._write_lock = threading.Lock()

    def _measurement_bytes(self, run_id: str) -> tuple[bytes, dict[str, object]]:
        safe_id = validate_run_name(run_id)
        path = self.paths.metrology / safe_id / "measurement.json"
        try:
            raw = path.read_bytes()
            payload = json.loads(raw)
        except (OSError, json.JSONDecodeError) as error:
            raise ProjectError(
                "E201",
                "量测记录不存在或损坏",
                "The metrology record is missing or malformed",
                "检查量测编号，或重新完成一次量测",
                "Check the metrology run ID or complete metrology again",
                safe_id,
            ) from error
        if not isinstance(payload, dict):
            raise _input_error(f"measurement payload for {safe_id} is not an object")
        return raw, payload

    @staticmethod
    def _physical_geometry(
        payload: dict[str, object],
        run_id: str,
    ) -> dict[str, object]:
        geometry = payload.get("physical_geometry")
        boundary = payload.get("decision_boundary")
        valid = isinstance(boundary, dict) and boundary.get("physical_measurement_valid")
        if not isinstance(geometry, dict) or not valid:
            raise _input_error(f"{run_id} has no valid calibrated physical measurement")
        unit = geometry.get("unit")
        if unit not in {"m", "cm", "mm"}:
            raise _input_error(f"{run_id} physical unit={unit!r}")
        return geometry

    @staticmethod
    def _length_m(value: object, unit: object, label: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise _input_error(f"{label}={value!r}")
        factors = {"m": 1.0, "cm": 0.01, "mm": 0.001}
        if unit not in factors:
            raise _input_error(f"{label} unit={unit!r}")
        result = float(value) * factors[str(unit)]
        if not math.isfinite(result) or result < 0:
            raise _input_error(f"{label}={value!r}")
        return result

    @staticmethod
    def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8") as stream:
                stream.write(
                    json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
                )
        except FileExistsError as error:
            raise ProjectError(
                "E204",
                "规划或对比记录已经存在",
                "The planning or comparison record already exists",
                "保留现有记录并重新运行以生成新编号",
                "Keep the record and rerun to generate a new ID",
                str(path),
            ) from error
        except OSError as error:
            raise ProjectError(
                "E504",
                "规划或对比记录写入失败",
                "Writing the planning or comparison record failed",
                "检查本地磁盘空间和目录权限",
                "Check local disk space and directory permissions",
                str(path),
            ) from error

    @staticmethod
    def _write_bytes_exclusive(path: Path, content: bytes) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(content)
        except FileExistsError as error:
            raise ProjectError(
                "E204",
                "变化图记录已经存在",
                "The spatial-change artifact already exists",
                "保留现有记录并重新运行以生成新编号",
                "Keep the record and rerun to generate a new ID",
                str(path),
            ) from error
        except OSError as error:
            raise ProjectError(
                "E504",
                "变化图写入失败",
                "Writing the spatial-change artifact failed",
                "检查本地磁盘空间和目录权限",
                "Check local disk space and directory permissions",
                str(path),
            ) from error

    def _calibration_frame(
        self,
        payload: dict[str, object],
        run_id: str,
    ) -> dict[str, float]:
        calibration = payload.get("calibration")
        if not isinstance(calibration, dict):
            raise _input_error(f"{run_id} calibration is missing")
        physical_size = calibration.get("physical_size")
        if not isinstance(physical_size, dict):
            raise _input_error(f"{run_id} physical calibration size is missing")
        unit = physical_size.get("unit")
        unit_m = self._length_m(1.0, unit, f"{run_id} physical unit")
        width_m = self._length_m(
            physical_size.get("width"),
            unit,
            f"{run_id} calibration width",
        )
        height_m = self._length_m(
            physical_size.get("height"),
            unit,
            f"{run_id} calibration height",
        )
        pixels_per_unit = calibration.get("pixels_per_unit")
        if (
            isinstance(pixels_per_unit, bool)
            or not isinstance(pixels_per_unit, (int, float))
            or not math.isfinite(float(pixels_per_unit))
            or float(pixels_per_unit) <= 0
        ):
            raise _input_error(f"{run_id} pixels_per_unit={pixels_per_unit!r}")
        return {
            "width_m": width_m,
            "height_m": height_m,
            "pixels_per_meter": float(pixels_per_unit) / unit_m,
        }

    def _rectified_mask(self, run_id: str) -> np.ndarray:
        path = self.paths.metrology / run_id / "rectified-mask.png"
        mask = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if mask is None or mask.ndim != 2 or mask.size < 3 or mask.size > MAX_METROLOGY_PIXELS:
            raise _input_error(f"{run_id} rectified mask is missing or invalid")
        return mask >= 128

    @staticmethod
    def _crop_and_resize_mask(
        mask: np.ndarray,
        *,
        source_width_m: float,
        source_height_m: float,
        common_width_m: float,
        common_height_m: float,
        target_width: int,
        target_height: int,
    ) -> np.ndarray:
        crop_width = max(
            2,
            min(
                mask.shape[1],
                round((mask.shape[1] - 1) * common_width_m / source_width_m) + 1,
            ),
        )
        crop_height = max(
            2,
            min(
                mask.shape[0],
                round((mask.shape[0] - 1) * common_height_m / source_height_m) + 1,
            ),
        )
        cropped = mask[:crop_height, :crop_width].astype(np.uint8)
        return (
            cv2.resize(
                cropped,
                (target_width, target_height),
                interpolation=cv2.INTER_NEAREST,
            )
            > 0
        )

    def _spatial_change(
        self,
        *,
        baseline_run_id: str,
        current_run_id: str,
        baseline: dict[str, object],
        current: dict[str, object],
        match_tolerance_mm: float,
    ) -> tuple[dict[str, object], bytes]:
        tolerance_mm = _finite_nonnegative(
            match_tolerance_mm,
            "match_tolerance_mm",
        )
        if tolerance_mm > 100:
            raise _input_error(f"match_tolerance_mm={tolerance_mm}")
        baseline_frame = self._calibration_frame(baseline, baseline_run_id)
        current_frame = self._calibration_frame(current, current_run_id)
        width_mismatch = abs(baseline_frame["width_m"] - current_frame["width_m"]) / max(
            baseline_frame["width_m"], current_frame["width_m"]
        )
        height_mismatch = abs(baseline_frame["height_m"] - current_frame["height_m"]) / max(
            baseline_frame["height_m"], current_frame["height_m"]
        )
        frame_mismatch = max(width_mismatch, height_mismatch)
        if frame_mismatch > MAX_FRAME_DIMENSION_MISMATCH_RATIO:
            raise _input_error(
                "calibrated frame mismatch "
                f"{frame_mismatch * 100:.3f}% exceeds "
                f"{MAX_FRAME_DIMENSION_MISMATCH_RATIO * 100:.1f}%"
            )

        baseline_mask = self._rectified_mask(baseline_run_id)
        current_mask = self._rectified_mask(current_run_id)
        common_width_m = min(
            baseline_frame["width_m"],
            current_frame["width_m"],
        )
        common_height_m = min(
            baseline_frame["height_m"],
            current_frame["height_m"],
        )
        target_pixels_per_meter = min(
            baseline_frame["pixels_per_meter"],
            current_frame["pixels_per_meter"],
            MAX_CHANGE_MAP_PIXELS_PER_METER,
        )
        target_width = max(2, round(common_width_m * target_pixels_per_meter) + 1)
        target_height = max(2, round(common_height_m * target_pixels_per_meter) + 1)
        if target_width * target_height > MAX_METROLOGY_PIXELS:
            scale = math.sqrt(MAX_METROLOGY_PIXELS / (target_width * target_height))
            target_width = max(2, math.floor(target_width * scale))
            target_height = max(2, math.floor(target_height * scale))
            target_pixels_per_meter *= scale

        baseline_normalized = self._crop_and_resize_mask(
            baseline_mask,
            source_width_m=baseline_frame["width_m"],
            source_height_m=baseline_frame["height_m"],
            common_width_m=common_width_m,
            common_height_m=common_height_m,
            target_width=target_width,
            target_height=target_height,
        )
        current_normalized = self._crop_and_resize_mask(
            current_mask,
            source_width_m=current_frame["width_m"],
            source_height_m=current_frame["height_m"],
            common_width_m=common_width_m,
            common_height_m=common_height_m,
            target_width=target_width,
            target_height=target_height,
        )
        tolerance_pixels = round(tolerance_mm / 1000.0 * target_pixels_per_meter)
        if tolerance_pixels > 0:
            baseline_distance = cv2.distanceTransform(
                (~baseline_normalized).astype(np.uint8),
                cv2.DIST_L2,
                cv2.DIST_MASK_PRECISE,
            )
            current_distance = cv2.distanceTransform(
                (~current_normalized).astype(np.uint8),
                cv2.DIST_L2,
                cv2.DIST_MASK_PRECISE,
            )
            baseline_near = baseline_distance <= tolerance_pixels
            current_near = current_distance <= tolerance_pixels
        else:
            baseline_near = baseline_normalized
            current_near = current_normalized

        baseline_stable = baseline_normalized & current_near
        current_stable = current_normalized & baseline_near
        stable = baseline_stable | current_stable
        added = current_normalized & ~baseline_near
        missing = baseline_normalized & ~current_near
        change_map = np.zeros(
            (target_height, target_width, 3),
            dtype=np.uint8,
        )
        change_map[stable] = (99, 193, 115)
        change_map[missing] = (226, 133, 57)
        change_map[added] = (58, 119, 239)
        encoded_ok, encoded = cv2.imencode(".png", change_map)
        if not encoded_ok:
            raise ProjectError(
                "E504",
                "变化图编码失败",
                "Encoding the spatial-change map failed",
                "保留量测记录并检查 OpenCV 环境",
                "Keep the measurements and inspect the OpenCV environment",
            )

        baseline_pixels = int(np.count_nonzero(baseline_normalized))
        current_pixels = int(np.count_nonzero(current_normalized))
        if baseline_pixels == 0 or current_pixels == 0:
            raise _input_error(
                "one normalized mask has no foreground inside the common calibrated frame"
            )
        pixel_area_cm2 = 10_000.0 / target_pixels_per_meter**2
        added_pixels = int(np.count_nonzero(added))
        missing_pixels = int(np.count_nonzero(missing))
        stable_pixels = int(np.count_nonzero(stable))
        quality_status = "strong" if frame_mismatch <= 0.02 else "acceptable"
        spatial_change: dict[str, object] = {
            "method": "four_point_physical_plane_normalization",
            "alignment_quality": {
                "status": quality_status,
                "comparable": True,
                "frame_dimension_mismatch_percent": round(
                    frame_mismatch * 100,
                    4,
                ),
                "maximum_allowed_mismatch_percent": (MAX_FRAME_DIMENSION_MISMATCH_RATIO * 100),
                "effective_pixels_per_meter": round(
                    target_pixels_per_meter,
                    4,
                ),
                "match_tolerance_mm": tolerance_mm,
                "tolerance_pixels": tolerance_pixels,
                "comparison_raster": {
                    "width": target_width,
                    "height": target_height,
                },
                "physical_overlap_m": {
                    "width": round(common_width_m, 6),
                    "height": round(common_height_m, 6),
                },
            },
            "classification": {
                "stable_union_pixels": stable_pixels,
                "suspected_added_pixels": added_pixels,
                "suspected_missing_pixels": missing_pixels,
                "suspected_added_area_cm2": round(
                    added_pixels * pixel_area_cm2,
                    4,
                ),
                "suspected_missing_area_cm2": round(
                    missing_pixels * pixel_area_cm2,
                    4,
                ),
                "baseline_matched_percent": round(
                    int(np.count_nonzero(baseline_stable)) / baseline_pixels * 100,
                    4,
                ),
                "current_matched_percent": round(
                    int(np.count_nonzero(current_stable)) / current_pixels * 100,
                    4,
                ),
            },
            "legend": {
                "green": "stable_within_tolerance",
                "orange": "suspected_added_in_current",
                "blue": "suspected_missing_from_current",
            },
        }
        return spatial_change, encoded.tobytes()

    def _response(self, run_id: str, output_dir: Path) -> dict[str, object]:
        try:
            measurement = json.loads((output_dir / "measurement.json").read_text(encoding="utf-8"))
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

    def propose_mask_bytes(
        self,
        *,
        source_content: bytes,
        source_filename: str | None,
        source_content_type: str,
        sensitivity: float = 0.55,
    ) -> dict[str, object]:
        if not math.isfinite(sensitivity) or not 0 <= sensitivity <= 1:
            raise _input_error(f"proposal sensitivity={sensitivity!r}")
        source_image, _ = _decode_source(
            source_content,
            source_content_type,
        )
        proposal = propose_crack_mask(
            source_image,
            sensitivity=sensitivity,
        )
        proposal_id = validate_run_name(self._record_id_factory("proposal"))
        mask = proposal.mask.astype(np.uint8) * 255
        encoded_ok, encoded = cv2.imencode(".png", mask)
        if not encoded_ok:
            raise ProjectError(
                "E504",
                "候选掩膜编码失败",
                "Encoding the proposed mask failed",
                "保留原图并检查 OpenCV 环境",
                "Keep the source image and inspect the OpenCV environment",
            )
        mask_bytes = encoded.tobytes()
        evidence: dict[str, object] = {
            **proposal.evidence,
            "proposal_id": proposal_id,
            "created_at_utc": datetime.now(UTC).isoformat(),
            "source": {
                "filename": _safe_filename(source_filename, "road-image"),
                "sha256": _sha256(source_content),
            },
            "proposal_mask": {
                "filename": "proposal-mask.png",
                "sha256": _sha256(mask_bytes),
                "foreground_pixels": int(np.count_nonzero(proposal.mask)),
            },
            "privacy": (
                "No absolute input path or source pixels are stored; processing stays on loopback"
            ),
        }
        output_dir = self.paths.metrology / "proposals" / proposal_id
        mask_path = output_dir / "proposal-mask.png"
        evidence_path = output_dir / "evidence.json"
        with self._write_lock:
            if mask_path.exists() or evidence_path.exists():
                raise ProjectError(
                    "E204",
                    "候选掩膜记录已经存在",
                    "The proposed-mask record already exists",
                    "保留现有记录并重新生成候选掩膜",
                    "Keep the record and generate a new proposal",
                    proposal_id,
                )
            self._write_bytes_exclusive(mask_path, mask_bytes)
            self._write_json_exclusive(evidence_path, evidence)
        return {
            "local_only": True,
            "proposal_id": proposal_id,
            "candidate_found": proposal.evidence["selection"]["candidate_found"],
            "evidence": evidence,
            "artifacts": {
                name: f"/api/metrology/proposals/{proposal_id}/{name}"
                for name in sorted(PROPOSAL_ARTIFACTS)
            },
        }

    def _proposal_revision(
        self,
        *,
        proposal_id: str,
        source_sha256: str,
        final_mask: np.ndarray,
    ) -> dict[str, object]:
        safe_id = validate_run_name(proposal_id)
        evidence_path = self.paths.metrology / "proposals" / safe_id / "evidence.json"
        mask_path = self.paths.metrology / "proposals" / safe_id / "proposal-mask.png"
        try:
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            proposal_bytes = mask_path.read_bytes()
        except (OSError, json.JSONDecodeError) as error:
            raise _input_error(f"proposal {safe_id} is missing or malformed") from error
        if not isinstance(evidence, dict):
            raise _input_error(f"proposal {safe_id} evidence is not an object")
        source = evidence.get("source")
        if not isinstance(source, dict) or source.get("sha256") != source_sha256:
            raise _input_error(f"proposal {safe_id} belongs to a different source image")
        proposal_image = cv2.imdecode(
            np.frombuffer(proposal_bytes, dtype=np.uint8),
            cv2.IMREAD_GRAYSCALE,
        )
        if proposal_image is None or proposal_image.shape != final_mask.shape:
            raise _input_error(f"proposal {safe_id} mask dimensions do not match")
        proposed = proposal_image >= 128
        intersection = int(np.count_nonzero(proposed & final_mask))
        union = int(np.count_nonzero(proposed | final_mask))
        added = int(np.count_nonzero(final_mask & ~proposed))
        removed = int(np.count_nonzero(proposed & ~final_mask))
        changed = added + removed
        algorithm_version = evidence.get("schema_version")
        return {
            "proposal_id": safe_id,
            "proposal_schema_version": algorithm_version,
            "proposal_mask_sha256": _sha256(proposal_bytes),
            "final_mask_sha256": _sha256(final_mask.astype(np.uint8).tobytes()),
            "proposal_foreground_pixels": int(np.count_nonzero(proposed)),
            "final_foreground_pixels": int(np.count_nonzero(final_mask)),
            "human_added_pixels": added,
            "human_removed_pixels": removed,
            "changed_pixels": changed,
            "changed_image_ratio": round(changed / final_mask.size, 8),
            "proposal_final_iou": (round(intersection / union, 8) if union else None),
            "interpretation": (
                "Difference between the immutable local proposal and the "
                "mask submitted from the human-editable browser"
            ),
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
        proposal_id: str | None = None,
    ) -> dict[str, object]:
        if not 0 <= uncertainty_samples <= 512:
            raise _input_error(f"uncertainty_samples={uncertainty_samples}")
        if not 0 <= segmentation_radius_pixels <= 5:
            raise _input_error(f"segmentation_radius_pixels={segmentation_radius_pixels}")
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
        source_digest = _sha256(source_content)
        mask_evidence: dict[str, object] = {
            "filename": _safe_filename(
                mask_filename,
                "browser-mask.png",
            ),
            "sha256": _sha256(mask_content),
            "foreground_pixels": int(np.count_nonzero(mask)),
            "origin": (
                "local_proposal_submitted_after_human_editing"
                if proposal_id
                else "manual_browser_mask"
            ),
        }
        if proposal_id:
            mask_evidence["proposal_revision"] = self._proposal_revision(
                proposal_id=proposal_id,
                source_sha256=source_digest,
                final_mask=mask,
            )
        input_evidence = {
            "kind": "local_web_metrology",
            "source": {
                "filename": _safe_filename(source_filename, "road-image"),
                "sha256": source_digest,
            },
            "mask": mask_evidence,
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
                    "claim_boundary": ("Algorithm demonstration only; not field-accuracy evidence"),
                },
                paths=self.paths,
            )
        return self._response(run_id, output_dir)

    def list_runs(self, *, limit: int = 50) -> dict[str, object]:
        if not 1 <= limit <= 100:
            raise _input_error(f"run list limit={limit}")
        items: list[dict[str, object]] = []
        if self.paths.metrology.is_dir():
            for path in self.paths.metrology.iterdir():
                measurement_path = path / "measurement.json"
                if not path.is_dir() or not measurement_path.is_file():
                    continue
                try:
                    payload = json.loads(measurement_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if not isinstance(payload, dict):
                    continue
                geometry = payload.get("physical_geometry")
                boundary = payload.get("decision_boundary")
                run = payload.get("run")
                if (
                    not isinstance(geometry, dict)
                    or not isinstance(boundary, dict)
                    or not boundary.get("physical_measurement_valid")
                    or not isinstance(run, dict)
                ):
                    continue
                widths = geometry.get("width_distribution")
                if not isinstance(widths, dict):
                    continue
                evidence = run.get("input_evidence")
                source_name = None
                if isinstance(evidence, dict):
                    source = evidence.get("source")
                    if isinstance(source, dict):
                        source_name = source.get("filename")
                items.append(
                    {
                        "run_id": path.name,
                        "created_at_utc": run.get("created_at_utc"),
                        "source_filename": source_name,
                        "unit": geometry.get("unit"),
                        "network_length": geometry.get("centerline_network_length"),
                        "mean_width": widths.get("mean"),
                        "p95_width": widths.get("p95"),
                    }
                )
        items.sort(
            key=lambda item: str(item.get("created_at_utc") or ""),
            reverse=True,
        )
        return {
            "local_only": True,
            "returned_count": min(limit, len(items)),
            "items": items[:limit],
        }

    def create_maintenance_plan(
        self,
        run_id: str,
        *,
        route_width_mm: float,
        route_depth_mm: float,
        waste_percent: float,
        unit_cost_per_liter: float | None = None,
    ) -> dict[str, object]:
        safe_id = validate_run_name(run_id)
        width = _finite_positive(route_width_mm, "route_width_mm")
        depth = _finite_positive(route_depth_mm, "route_depth_mm")
        waste = _finite_nonnegative(waste_percent, "waste_percent")
        if width > 200 or depth > 200 or waste > 200:
            raise _input_error(f"width_mm={width}, depth_mm={depth}, waste_percent={waste}")
        cost = None
        if unit_cost_per_liter is not None:
            cost = _finite_nonnegative(unit_cost_per_liter, "unit_cost_per_liter")
        measurement_raw, measurement = self._measurement_bytes(safe_id)
        geometry = self._physical_geometry(measurement, safe_id)
        length_m = self._length_m(
            geometry.get("centerline_network_length"),
            geometry.get("unit"),
            "centerline_network_length",
        )
        base_volume_liters = length_m * width * depth / 1000.0
        procurement_volume_liters = base_volume_liters * (1.0 + waste / 100.0)
        estimated_cost = procurement_volume_liters * cost if cost is not None else None
        plan_id = validate_run_name(self._record_id_factory("maintenance"))
        payload: dict[str, object] = {
            "schema_version": "maintenance-plan-v3.2.0",
            "created_at_utc": datetime.now(UTC).isoformat(),
            "plan_id": plan_id,
            "run_id": safe_id,
            "measurement_sha256": _sha256(measurement_raw),
            "assumptions": {
                "route_width_mm": width,
                "route_depth_mm": depth,
                "waste_percent": waste,
                "unit_cost_per_liter": cost,
            },
            "quantities": {
                "treatment_length_m": round(length_m, 6),
                "base_fill_volume_liters": round(base_volume_liters, 6),
                "procurement_volume_liters": round(procurement_volume_liters, 6),
                "estimated_material_cost": (
                    round(estimated_cost, 2) if estimated_cost is not None else None
                ),
            },
            "decision_boundary": {
                "message_zh": (
                    "这是基于用户输入槽宽、槽深和损耗率的材料规划估算，"
                    "不是施工规范、报价或道路安全结论"
                ),
                "message_en": (
                    "This is a material-planning estimate based on user-entered route "
                    "width, depth, and waste; it is not a specification, quote, or "
                    "road-safety verdict"
                ),
            },
        }
        path = self.paths.metrology / safe_id / "plans" / f"{plan_id}.json"
        with self._write_lock:
            self._write_json_exclusive(path, payload)
        return {
            "local_only": True,
            "plan": payload,
            "plan_url": f"/api/metrology/runs/{safe_id}/plans/{plan_id}.json",
        }

    @staticmethod
    def _change(current: float, baseline: float) -> dict[str, float | None]:
        delta = current - baseline
        percent = delta / baseline * 100.0 if baseline > 0 else None
        return {
            "baseline": round(baseline, 6),
            "current": round(current, 6),
            "delta": round(delta, 6),
            "percent": round(percent, 4) if percent is not None else None,
        }

    def compare_runs(
        self,
        *,
        baseline_run_id: str,
        current_run_id: str,
        elapsed_days: float,
        length_review_threshold_percent: float,
        width_review_threshold_percent: float,
        match_tolerance_mm: float = 5.0,
    ) -> dict[str, object]:
        baseline_id = validate_run_name(baseline_run_id)
        current_id = validate_run_name(current_run_id)
        if baseline_id == current_id:
            raise _input_error("baseline and current run IDs must differ")
        days = _finite_positive(elapsed_days, "elapsed_days")
        length_threshold = _finite_nonnegative(
            length_review_threshold_percent,
            "length_review_threshold_percent",
        )
        width_threshold = _finite_nonnegative(
            width_review_threshold_percent,
            "width_review_threshold_percent",
        )
        if days > 36525 or length_threshold > 1000 or width_threshold > 1000:
            raise _input_error(
                f"days={days}, length_threshold={length_threshold}, "
                f"width_threshold={width_threshold}"
            )
        baseline_raw, baseline = self._measurement_bytes(baseline_id)
        current_raw, current = self._measurement_bytes(current_id)
        baseline_geometry = self._physical_geometry(baseline, baseline_id)
        current_geometry = self._physical_geometry(current, current_id)

        def metric_m(geometry: dict[str, object], key: str) -> float:
            return self._length_m(geometry.get(key), geometry.get("unit"), key)

        def width_m(geometry: dict[str, object], key: str) -> float:
            widths = geometry.get("width_distribution")
            if not isinstance(widths, dict):
                raise _input_error("width_distribution is missing")
            return self._length_m(widths.get(key), geometry.get("unit"), key)

        baseline_length_m = metric_m(baseline_geometry, "centerline_network_length")
        current_length_m = metric_m(current_geometry, "centerline_network_length")
        baseline_mean_width_mm = width_m(baseline_geometry, "mean") * 1000.0
        current_mean_width_mm = width_m(current_geometry, "mean") * 1000.0
        baseline_p95_width_mm = width_m(baseline_geometry, "p95") * 1000.0
        current_p95_width_mm = width_m(current_geometry, "p95") * 1000.0

        length_change = self._change(current_length_m, baseline_length_m)
        mean_width_change = self._change(current_mean_width_mm, baseline_mean_width_mm)
        p95_width_change = self._change(current_p95_width_mm, baseline_p95_width_mm)
        length_percent = length_change["percent"]
        width_percent = p95_width_change["percent"]
        review_required = (
            isinstance(length_percent, float) and length_percent >= length_threshold
        ) or (isinstance(width_percent, float) and width_percent >= width_threshold)
        baseline_topology = baseline.get("topology")
        current_topology = current.get("topology")
        baseline_junctions = (
            int(baseline_topology.get("junction_cluster_count", 0))
            if isinstance(baseline_topology, dict)
            else 0
        )
        current_junctions = (
            int(current_topology.get("junction_cluster_count", 0))
            if isinstance(current_topology, dict)
            else 0
        )
        spatial_change, change_map_png = self._spatial_change(
            baseline_run_id=baseline_id,
            current_run_id=current_id,
            baseline=baseline,
            current=current,
            match_tolerance_mm=match_tolerance_mm,
        )
        comparison_id = validate_run_name(self._record_id_factory("comparison"))
        change_map_name = f"{comparison_id}-change-map.png"
        payload: dict[str, object] = {
            "schema_version": "metrology-comparison-v3.3.0",
            "created_at_utc": datetime.now(UTC).isoformat(),
            "comparison_id": comparison_id,
            "baseline_run_id": baseline_id,
            "current_run_id": current_id,
            "elapsed_days": days,
            "measurement_sha256": {
                "baseline": _sha256(baseline_raw),
                "current": _sha256(current_raw),
            },
            "changes": {
                "network_length_m": length_change,
                "mean_width_mm": mean_width_change,
                "p95_width_mm": p95_width_change,
                "junction_cluster_count": {
                    "baseline": baseline_junctions,
                    "current": current_junctions,
                    "delta": current_junctions - baseline_junctions,
                },
                "network_length_growth_m_per_day": round(
                    (current_length_m - baseline_length_m) / days, 8
                ),
                "p95_width_growth_mm_per_day": round(
                    (current_p95_width_mm - baseline_p95_width_mm) / days,
                    8,
                ),
            },
            "spatial_change": spatial_change,
            "artifacts": {
                "change_map_png": change_map_name,
                "change_map_sha256": _sha256(change_map_png),
            },
            "review_rule": {
                "length_growth_threshold_percent": length_threshold,
                "p95_width_growth_threshold_percent": width_threshold,
                "status": (
                    "change_exceeds_user_threshold" if review_required else "within_user_threshold"
                ),
                "human_review_required": review_required,
            },
            "decision_boundary": {
                "message_zh": (
                    "变化图依赖同一物理参考框、统一掩膜协议和用户输入的空间容差；"
                    "橙色/蓝色是疑似变化而非自动确认的新增/修复，复核阈值不是道路安全标准"
                ),
                "message_en": (
                    "The change map requires the same physical reference frame, a "
                    "consistent masking protocol, and a user-entered spatial tolerance; "
                    "orange/blue are suspected rather than confirmed additions/repairs, "
                    "and review thresholds are not road-safety standards"
                ),
            },
        }
        path = self.paths.metrology / "comparisons" / f"{comparison_id}.json"
        change_map_path = self.paths.metrology / "comparisons" / change_map_name
        with self._write_lock:
            if path.exists() or change_map_path.exists():
                raise ProjectError(
                    "E204",
                    "增长对比记录已经存在",
                    "The growth-comparison record already exists",
                    "保留现有记录并重新运行以生成新编号",
                    "Keep the record and rerun to generate a new ID",
                    comparison_id,
                )
            self._write_bytes_exclusive(change_map_path, change_map_png)
            self._write_json_exclusive(path, payload)
        return {
            "local_only": True,
            "comparison": payload,
            "comparison_url": (f"/api/metrology/comparisons/{comparison_id}.json"),
            "artifacts": {
                "change-map.png": (f"/api/metrology/comparisons/{comparison_id}/change-map.png"),
            },
        }

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

    def plan_path(self, run_id: str, plan_id: str) -> Path:
        safe_run_id = validate_run_name(run_id)
        safe_plan_id = validate_run_name(plan_id)
        path = self.paths.metrology / safe_run_id / "plans" / f"{safe_plan_id}.json"
        if not path.is_file():
            raise ProjectError(
                "E201",
                "材料规划记录不存在",
                "The maintenance plan does not exist",
                "检查量测编号和规划编号",
                "Check the metrology run and plan IDs",
                f"{safe_run_id}/{safe_plan_id}",
            )
        return path

    def proposal_artifact_path(
        self,
        proposal_id: str,
        artifact_name: str,
    ) -> Path:
        safe_id = validate_run_name(proposal_id)
        if artifact_name not in PROPOSAL_ARTIFACTS:
            raise ProjectError(
                "E201",
                "候选掩膜文件不存在",
                "The proposed-mask artifact does not exist",
                "检查候选编号和文件名",
                "Check the proposal ID and artifact name",
                artifact_name,
            )
        path = self.paths.metrology / "proposals" / safe_id / artifact_name
        if not path.is_file():
            raise ProjectError(
                "E201",
                "候选掩膜文件不存在",
                "The proposed-mask artifact does not exist",
                "重新为当前原图生成一次本地候选掩膜",
                "Generate another local proposal for the current image",
                f"{safe_id}/{artifact_name}",
            )
        return path

    def comparison_path(self, comparison_id: str) -> Path:
        safe_id = validate_run_name(comparison_id)
        path = self.paths.metrology / "comparisons" / f"{safe_id}.json"
        if not path.is_file():
            raise ProjectError(
                "E201",
                "增长对比记录不存在",
                "The growth-comparison record does not exist",
                "检查对比编号，或重新运行对比",
                "Check the comparison ID or run the comparison again",
                safe_id,
            )
        return path

    def comparison_artifact_path(
        self,
        comparison_id: str,
        artifact_name: str,
    ) -> Path:
        safe_id = validate_run_name(comparison_id)
        if artifact_name not in COMPARISON_ARTIFACTS:
            raise ProjectError(
                "E201",
                "变化图文件不存在",
                "The spatial-change artifact does not exist",
                "检查对比编号和文件名",
                "Check the comparison ID and artifact name",
                artifact_name,
            )
        path = self.paths.metrology / "comparisons" / f"{safe_id}-{artifact_name}"
        if not path.is_file():
            raise ProjectError(
                "E201",
                "变化图文件不存在",
                "The spatial-change artifact does not exist",
                "重新运行同一路段的两期标定对比",
                "Rerun a calibrated two-date comparison of the same area",
                f"{safe_id}/{artifact_name}",
            )
        return path
