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
        comparison_id = validate_run_name(self._record_id_factory("comparison"))
        payload: dict[str, object] = {
            "schema_version": "metrology-comparison-v3.2.0",
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
                    "对比要求两次巡检覆盖同一裂缝区域并采用一致标定与掩膜协议；"
                    "阈值由用户输入，不是道路安全标准"
                ),
                "message_en": (
                    "Comparison requires the same crack region and a consistent "
                    "calibration/masking protocol; user thresholds are not road-safety "
                    "standards"
                ),
            },
        }
        path = self.paths.metrology / "comparisons" / f"{comparison_id}.json"
        with self._write_lock:
            self._write_json_exclusive(path, payload)
        return {
            "local_only": True,
            "comparison": payload,
            "comparison_url": (f"/api/metrology/comparisons/{comparison_id}.json"),
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
