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
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

from urbanvision_risk import __version__
from urbanvision_risk.data.voc import DETECTION_CLASS_INFO
from urbanvision_risk.detection.config import validate_run_name
from urbanvision_risk.detection.predict import serialize_detections
from urbanvision_risk.detection.tiled import (
    DetectionCandidate,
    class_aware_nms,
    extract_candidates,
    tile_windows,
)
from urbanvision_risk.errors import ProjectError
from urbanvision_risk.paths import ProjectPaths, get_paths
from urbanvision_risk.reporting.local_narrative import LocalNarrativeGenerator
from urbanvision_risk.risk.config import load_risk_config, resolved_config_yaml
from urbanvision_risk.risk.schema import validate_prediction_payload
from urbanvision_risk.risk.score import score_prediction

APP_VERSION = __version__
DEVICE = "mps"
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
ALLOWED_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
HIGH_RES_THRESHOLD = 1280
EMPTY_DETECTION_RETRY_SIZE = 1280
TILE_SIZE = 1024
TILE_OVERLAP = 0.20
TILE_NMS_IOU = 0.50
TILE_BATCH_SIZE = 2
CLASS_COLORS = {
    0: (23, 181, 128),
    1: (39, 128, 230),
    2: (237, 167, 39),
    3: (222, 69, 72),
    4: (151, 93, 214),
}


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


def _annotate_image(
    image: Image.Image,
    candidates: list[DetectionCandidate],
) -> Image.Image:
    annotated = image.copy()
    draw = ImageDraw.Draw(annotated)
    line_width = max(3, round(min(image.size) / 320))
    for candidate in candidates:
        color = CLASS_COLORS[candidate.class_id]
        draw.rectangle(candidate.bbox_xyxy, outline=color, width=line_width)
        code = DETECTION_CLASS_INFO[candidate.class_id]["code"]
        label = f"{code} {candidate.confidence:.2f}"
        text_box = draw.textbbox((0, 0), label, stroke_width=1)
        text_width = text_box[2] - text_box[0]
        text_height = text_box[3] - text_box[1]
        x1, y1, _, _ = candidate.bbox_xyxy
        label_y = max(0.0, y1 - text_height - 8)
        draw.rectangle(
            (x1, label_y, x1 + text_width + 10, label_y + text_height + 8),
            fill=color,
        )
        draw.text(
            (x1 + 5, label_y + 3),
            label,
            fill=(255, 255, 255),
            stroke_width=1,
            stroke_fill=(0, 0, 0),
        )
    return annotated


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
        narrative_generator: LocalNarrativeGenerator | None = None,
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
        self._narrative_lock = threading.Lock()
        self.narrative_generator = narrative_generator or LocalNarrativeGenerator()
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
            "high_resolution_tiling": True,
            "empty_detection_retry_size": EMPTY_DETECTION_RETRY_SIZE,
            "tile_size": TILE_SIZE,
            "tile_overlap": TILE_OVERLAP,
            "tile_batch_size": TILE_BATCH_SIZE,
            "local_narrative": self.narrative_generator.health_payload(),
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

    def narrative(self, inspection_id: str) -> dict[str, object]:
        """Generate once, then reuse an immutable local bilingual narrative."""
        safe_id = validate_run_name(inspection_id)
        output_dir = self.paths.inspections / self.run_name / safe_id
        prediction_path = output_dir / "prediction.json"
        risk_path = output_dir / "risk.json"
        narrative_path = output_dir / "narrative.json"
        if not prediction_path.is_file() or not risk_path.is_file():
            raise ProjectError(
                "E201",
                "巡检结构化结果不存在",
                "The structured inspection result does not exist",
                "检查巡检编号，或先完成一次图片巡检",
                "Check the inspection ID or complete an image inspection first",
                safe_id,
            )

        with self._narrative_lock:
            if narrative_path.is_file():
                try:
                    existing = json.loads(narrative_path.read_bytes())
                except (json.JSONDecodeError, OSError) as error:
                    raise _write_error(narrative_path) from error
                if not isinstance(existing, dict):
                    raise _write_error(narrative_path) from None
                return existing

            try:
                prediction_bytes = prediction_path.read_bytes()
                risk_bytes = risk_path.read_bytes()
                prediction = json.loads(prediction_bytes)
                risk = json.loads(risk_bytes)
            except (json.JSONDecodeError, OSError) as error:
                raise _write_error(output_dir) from error
            if not isinstance(prediction, dict) or not isinstance(risk, dict):
                raise _write_error(output_dir)

            generated = self.narrative_generator.generate(prediction, risk)
            narrative = {
                **generated,
                "inspection_id": safe_id,
                "created_at_utc": datetime.now(UTC).isoformat(),
                "source_prediction_sha256": _sha256(prediction_bytes),
                "source_risk_sha256": _sha256(risk_bytes),
                "limitation": risk.get("limitation", {}),
            }
            narrative_bytes = _json_bytes(narrative)
            try:
                with narrative_path.open("xb") as file:
                    file.write(narrative_bytes)
            except FileExistsError:
                try:
                    existing = json.loads(narrative_path.read_bytes())
                except (json.JSONDecodeError, OSError) as error:
                    raise _write_error(narrative_path) from error
                if not isinstance(existing, dict):
                    raise _write_error(narrative_path) from None
                return existing
            except OSError as error:
                raise _write_error(narrative_path) from error
            return narrative

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

        # Ultralytics treats NumPy image sources as OpenCV-style BGR. Pillow gives us RGB,
        # so passing the array unchanged can suppress otherwise confident detections.
        inference_array = np.ascontiguousarray(np.asarray(image)[:, :, ::-1])
        width, height = image.size
        use_tiles = max(width, height) > HIGH_RES_THRESHOLD
        windows = tile_windows(
            width,
            height,
            tile_size=TILE_SIZE,
            overlap=TILE_OVERLAP,
        ) if use_tiles else ()
        try:
            with self._inference_lock:
                full_results = list(
                    self.model.predict(
                        source=inference_array,
                        conf=self.confidence,
                        device=DEVICE,
                        verbose=False,
                    )
                )
                tile_results = []
                for start in range(0, len(windows), TILE_BATCH_SIZE):
                    window_batch = windows[start : start + TILE_BATCH_SIZE]
                    tile_results.extend(
                        self.model.predict(
                            source=[
                                np.ascontiguousarray(inference_array[y1:y2, x1:x2])
                                for x1, y1, x2, y2 in window_batch
                            ],
                            conf=self.confidence,
                            device=DEVICE,
                            imgsz=TILE_SIZE,
                            verbose=False,
                        )
                    )
            if len(full_results) != 1:
                raise ValueError(f"expected one full result, received {len(full_results)}")
            if len(tile_results) != len(windows):
                raise ValueError(
                    f"expected {len(windows)} tile results, received {len(tile_results)}"
                )
            candidates = extract_candidates(
                full_results[0],
                image_width=width,
                image_height=height,
            )
            for result, (x1, y1, _, _) in zip(tile_results, windows, strict=True):
                candidates.extend(
                    extract_candidates(
                        result,
                        offset_x=x1,
                        offset_y=y1,
                        image_width=width,
                        image_height=height,
                    )
                )
            retry_used = False
            if not candidates and not windows:
                # Thin cracks in small source images can disappear when the model's
                # default 640px inference size resamples them. Retry only an empty
                # first pass at 1280px so normal detections keep their current speed
                # and confidence threshold.
                with self._inference_lock:
                    retry_results = list(
                        self.model.predict(
                            source=inference_array,
                            conf=self.confidence,
                            device=DEVICE,
                            imgsz=EMPTY_DETECTION_RETRY_SIZE,
                            verbose=False,
                        )
                    )
                if len(retry_results) != 1:
                    raise ValueError(
                        "expected one high-resolution retry result, "
                        f"received {len(retry_results)}"
                    )
                retry_used = True
                candidates.extend(
                    extract_candidates(
                        retry_results[0],
                        image_width=width,
                        image_height=height,
                    )
                )
            candidates = class_aware_nms(candidates, iou_threshold=TILE_NMS_IOU)
            prediction = serialize_detections(
                (
                    (candidate.class_id, candidate.confidence, candidate.bbox_xyxy)
                    for candidate in candidates
                ),
                source_image=source_path,
                width=width,
                height=height,
                model_path=self.checkpoint,
                confidence=self.confidence,
            )
            prediction["inference"] = {
                "mode": (
                    "full_and_tiled"
                    if windows
                    else "full_image_high_resolution_retry"
                    if retry_used
                    else "full_image"
                ),
                "empty_detection_retry_used": retry_used,
                "empty_detection_retry_size": (
                    EMPTY_DETECTION_RETRY_SIZE if retry_used else None
                ),
                "tile_count": len(windows),
                "tile_size": TILE_SIZE if windows else None,
                "tile_overlap": TILE_OVERLAP if windows else None,
                "tile_batch_size": TILE_BATCH_SIZE if windows else None,
                "nms_iou": TILE_NMS_IOU,
            }
            record = validate_prediction_payload(
                prediction, self.risk_config, f"inspection:{inspection_id}"
            )
            source_bytes = _encode_jpeg(image)
            annotated_bytes = _encode_jpeg(_annotate_image(image, candidates))
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
            "inference": prediction["inference"],
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
                "decision_status",
                "review_required",
                "recommendation",
                "class_breakdown",
                "auxiliary_observations",
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
