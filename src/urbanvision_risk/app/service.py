from __future__ import annotations

import hashlib
import io
import json
import secrets
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from urbanvision_risk import __version__
from urbanvision_risk.detection.config import validate_run_name
from urbanvision_risk.detection.predict import serialize_result
from urbanvision_risk.errors import ProjectError
from urbanvision_risk.paths import ProjectPaths, get_paths
from urbanvision_risk.risk.config import load_risk_config, resolved_config_yaml
from urbanvision_risk.risk.schema import validate_prediction_payload
from urbanvision_risk.risk.score import score_prediction

APP_VERSION = __version__
DEVICE = "mps"
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
ALLOWED_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})


def _json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _upload_error(context: str) -> ProjectError:
    return ProjectError(
        "E601",
        "上传图片无效或超出本地应用限制",
        "The uploaded image is invalid or exceeds the local-app limits",
        "使用不超过 15 MiB、4000 万像素的 JPEG、PNG 或 WebP 图片",
        "Use a JPEG, PNG, or WebP image no larger than 15 MiB and 40 megapixels",
        context,
    )


def _model_error(context: str) -> ProjectError:
    return ProjectError(
        "E301",
        "本地模型加载或推理失败",
        "The local model failed to load or run inference",
        "检查 best.pt、MPS 环境和输入图片，然后重试",
        "Check best.pt, the MPS environment, and the input image, then retry",
        context,
    )


def _write_error(path: Path) -> ProjectError:
    return ProjectError(
        "E602",
        "本地巡检结果写入失败；已有半成品会保留",
        "Writing the local inspection failed; any partial output is preserved",
        "检查磁盘空间和权限，再上传一次以生成新的巡检编号",
        "Check disk space and permissions, then upload again for a new inspection ID",
        str(path),
    )


def _existing_error(path: Path) -> ProjectError:
    return ProjectError(
        "E204",
        "巡检输出目录已经存在",
        "The inspection output directory already exists",
        "保留现有结果，并重新上传以生成新的巡检编号",
        "Keep the existing result and upload again for a new inspection ID",
        str(path),
    )


def _safe_display_filename(filename: str | None) -> str:
    cleaned = (filename or "uploaded-image").replace("\\", "/").rsplit("/", 1)[-1].strip()
    return (cleaned or "uploaded-image")[:255]


def _new_inspection_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dt%H%M%S")
    return f"inspection-{timestamp}-{secrets.token_hex(4)}"


def _encode_jpeg(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=92, optimize=True)
    return buffer.getvalue()


def _decode_image(content: bytes, content_type: str) -> Image.Image:
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise _upload_error(f"content_type={content_type or 'missing'}")
    if not content or len(content) > MAX_UPLOAD_BYTES:
        raise _upload_error(f"bytes={len(content)}")
    try:
        with Image.open(io.BytesIO(content)) as opened:
            width, height = opened.size
            if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
                raise _upload_error(f"dimensions={width}x{height}")
            opened.load()
            normalized = ImageOps.exif_transpose(opened).convert("RGB")
    except ProjectError:
        raise
    except (Image.DecompressionBombError, OSError, UnidentifiedImageError) as error:
        raise _upload_error("image decoding failed") from error
    return normalized


class LocalInspectionService:
    """Load one local model and create immutable single-image inspections."""

    def __init__(
        self,
        run_name: str,
        *,
        confidence: float = 0.25,
        paths: ProjectPaths | None = None,
        model_factory: Callable[[str], Any] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.run_name = validate_run_name(run_name)
        if not 0 <= confidence <= 1:
            raise ProjectError(
                "E302",
                "置信度阈值必须位于 0 到 1",
                "Confidence threshold must be between 0 and 1",
                "使用例如 --confidence 0.25",
                "Use a value such as --confidence 0.25",
                str(confidence),
            )
        self.confidence = float(confidence)
        self.paths = paths or get_paths()
        self.checkpoint = self.paths.experiments / self.run_name / "weights" / "best.pt"
        if not self.checkpoint.is_file():
            raise ProjectError(
                "E201",
                "最佳模型不存在",
                "The best model checkpoint is missing",
                "先完成基线训练，或检查 --run-name",
                "Complete baseline training first or check --run-name",
                str(self.checkpoint),
            )
        self.config_path = self.paths.configs / "risk-v0.2.yaml"
        self.risk_config = load_risk_config(self.config_path)
        resolved_config = resolved_config_yaml(self.risk_config).encode("utf-8")
        self.config_sha256 = _sha256(resolved_config)
        self._id_factory = id_factory or _new_inspection_id
        self._inference_lock = threading.Lock()
        if model_factory is None:
            from ultralytics import YOLO

            model_factory = YOLO
        try:
            self.model = model_factory(str(self.checkpoint))
        except Exception as error:
            raise _model_error(str(self.checkpoint)) from error

    def health_payload(self) -> dict[str, object]:
        return {
            "app_version": APP_VERSION,
            "run_name": self.run_name,
            "checkpoint": self.checkpoint.name,
            "device": DEVICE,
            "confidence": self.confidence,
            "local_only": True,
            "accepted_content_types": sorted(ALLOWED_CONTENT_TYPES),
            "max_upload_mib": MAX_UPLOAD_BYTES // (1024 * 1024),
            "max_image_megapixels": MAX_IMAGE_PIXELS // 1_000_000,
        }

    def annotated_path(self, inspection_id: str) -> Path:
        safe_id = validate_run_name(inspection_id)
        path = self.paths.inspections / self.run_name / safe_id / "annotated.jpg"
        if not path.is_file():
            raise ProjectError(
                "E201",
                "巡检标注图片不存在",
                "The annotated inspection image does not exist",
                "检查巡检编号，或重新上传图片",
                "Check the inspection ID or upload the image again",
                safe_id,
            )
        return path

    def inspect_bytes(
        self,
        content: bytes,
        *,
        filename: str | None,
        content_type: str,
    ) -> dict[str, object]:
        image = _decode_image(content, content_type)
        display_filename = _safe_display_filename(filename)
        inspection_id = validate_run_name(self._id_factory())
        output_dir = self.paths.inspections / self.run_name / inspection_id
        if output_dir.exists():
            raise _existing_error(output_dir)
        source_path = output_dir / "source.jpg"

        rgb_array = np.asarray(image)
        try:
            with self._inference_lock:
                results = list(
                    self.model.predict(
                        source=rgb_array,
                        conf=self.confidence,
                        device=DEVICE,
                        verbose=False,
                    )
                )
            if len(results) != 1:
                raise ValueError(f"expected one result, received {len(results)}")
            model_result = results[0]
            prediction = serialize_result(model_result, self.checkpoint, self.confidence)
            prediction["source_image"] = str(source_path.resolve())
            record = validate_prediction_payload(
                prediction, self.risk_config, f"inspection:{inspection_id}"
            )
            source_bytes = _encode_jpeg(image)
            plotted = np.asarray(model_result.plot())
            if plotted.ndim != 3 or plotted.shape[2] < 3:
                raise ValueError("model plot is not a color image")
            annotated_rgb = np.ascontiguousarray(plotted[:, :, :3][:, :, ::-1])
            annotated_bytes = _encode_jpeg(Image.fromarray(annotated_rgb))
        except ProjectError:
            raise
        except Exception as error:
            raise _model_error(f"inspection:{inspection_id}") from error

        prediction_bytes = _json_bytes(prediction)
        risk = score_prediction(
            record,
            self.risk_config,
            source_prediction="prediction.json",
            source_sha256=_sha256(prediction_bytes),
            config_sha256=self.config_sha256,
        )
        risk_bytes = _json_bytes(risk)
        created_at = datetime.now(UTC).isoformat()
        manifest = {
            "app_version": APP_VERSION,
            "created_at_utc": created_at,
            "inspection_id": inspection_id,
            "run_name": self.run_name,
            "source_filename": display_filename,
            "source_content_type": content_type,
            "device": DEVICE,
            "confidence": self.confidence,
            "checkpoint": self.checkpoint.name,
            "risk_formula_version": risk["formula_version"],
            "risk_config_sha256": self.config_sha256,
            "source_jpg_sha256": _sha256(source_bytes),
            "annotated_jpg_sha256": _sha256(annotated_bytes),
            "prediction_json_sha256": _sha256(prediction_bytes),
            "risk_json_sha256": _sha256(risk_bytes),
        }
        manifest_bytes = _json_bytes(manifest)

        try:
            output_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError as error:
            raise _existing_error(output_dir) from error
        except OSError as error:
            raise _write_error(output_dir) from error
        try:
            source_path.write_bytes(source_bytes)
            (output_dir / "annotated.jpg").write_bytes(annotated_bytes)
            (output_dir / "prediction.json").write_bytes(prediction_bytes)
            (output_dir / "risk.json").write_bytes(risk_bytes)
            (output_dir / "inspection-manifest.json").write_bytes(manifest_bytes)
        except OSError as error:
            raise _write_error(output_dir) from error

        response_prediction = {
            "image_dimensions": prediction["image_dimensions"],
            "counts": prediction["counts"],
            "detections": prediction["detections"],
            **{key: prediction[key] for key in ("message_zh", "message_en") if key in prediction},
        }
        response_risk = {
            key: risk[key]
            for key in (
                "formula_version",
                "risk_score",
                "risk_level",
                "recommendation",
                "class_breakdown",
                "evidence",
                "audit_flags",
                "limitation",
            )
        }
        return {
            "inspection_id": inspection_id,
            "created_at_utc": created_at,
            "source_filename": display_filename,
            "annotated_url": f"/api/inspections/{inspection_id}/annotated.jpg",
            "prediction": response_prediction,
            "risk": response_risk,
        }
