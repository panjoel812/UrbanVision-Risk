from __future__ import annotations

import hashlib
import io
import json
import math
import secrets
import threading
import zipfile
from collections.abc import Callable
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from urbanvision_risk.app.crack_proposal import (
    MAX_RANKED_REVIEW_HOTSPOTS,
    propose_crack_mask,
)
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
REVIEW_AUTHORITIES = {
    "automatic_draft": "machine_unreviewed",
    "machine_reviewed_candidate": "machine_heuristic",
    "human_reviewed": "human_operator",
}
HOTSPOT_DISPOSITIONS = frozenset(
    {
        "accepted_as_proposed",
        "false_positive_removed",
        "missed_crack_added",
        "deferred_for_follow_up",
    }
)
MAX_HOTSPOT_NOTE_CHARS = 160
AUTOPILOT_ACCEPT_OVERLAP = 0.10
ACTIVE_LEARNING_FEEDBACK_ARTIFACT = "active-learning-feedback.zip"
MAX_FEEDBACK_CROP_PIXELS = 512_000
MAX_FEEDBACK_CATALOG_PACKAGES = 100
MAX_FEEDBACK_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_SCENE_FINGERPRINTS_PER_SOURCE = 128
MAX_FEEDBACK_SNAPSHOT_ITEMS = 5_000
MAX_FEEDBACK_SNAPSHOT_MEMBER_BYTES = 8 * 1024 * 1024
MAX_FEEDBACK_SNAPSHOT_TOTAL_BYTES = 512 * 1024 * 1024
MAX_FEEDBACK_SNAPSHOT_FINDINGS = 500
MAX_AUTOPILOT_BATCH_IMAGES = 100
CURATION_SPLITS = ("train", "val", "test")
FEEDBACK_FILE_ROLES = (
    "source_roi",
    "proposal_mask",
    "final_mask",
    "disagreement_layer",
)
COMPARISON_ARTIFACTS = frozenset({"change-map.png"})
PROPOSAL_ARTIFACTS = frozenset(
    {"proposal-mask.png", "review-hotspots.png", "evidence.json"}
)
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
        ACTIVE_LEARNING_FEEDBACK_ARTIFACT,
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


def _reviewed_hotspot_ids(value: str | None) -> list[str]:
    if value is None or not value.strip():
        return []
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise _input_error("reviewed_hotspots is not valid JSON") from error
    if not isinstance(payload, list):
        raise _input_error("reviewed_hotspots must be a JSON array")
    if len(payload) > MAX_RANKED_REVIEW_HOTSPOTS:
        raise _input_error(
            f"reviewed_hotspots count={len(payload)} exceeds "
            f"{MAX_RANKED_REVIEW_HOTSPOTS}"
        )
    result: list[str] = []
    for hotspot_id in payload:
        if not isinstance(hotspot_id, str) or not hotspot_id:
            raise _input_error("reviewed_hotspots contains a non-string ID")
        if hotspot_id in result:
            raise _input_error(f"reviewed_hotspots contains duplicate ID {hotspot_id}")
        result.append(hotspot_id)
    return result


def _autopilot_batch_run_ids(value: str) -> list[str]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise _input_error("autopilot batch run_ids is not valid JSON") from error
    if not isinstance(payload, list):
        raise _input_error("autopilot batch run_ids must be a JSON array")
    if not 1 <= len(payload) <= MAX_AUTOPILOT_BATCH_IMAGES:
        raise _input_error(
            f"autopilot batch run count={len(payload)} must be between "
            f"1 and {MAX_AUTOPILOT_BATCH_IMAGES}"
        )
    result: list[str] = []
    for run_id in payload:
        if not isinstance(run_id, str):
            raise _input_error(
                "autopilot batch run_ids contains a non-string ID"
            )
        safe_id = validate_run_name(run_id)
        if safe_id in result:
            raise _input_error(
                f"autopilot batch run_ids contains duplicate ID {safe_id}"
            )
        result.append(safe_id)
    return result


def _hotspot_decisions(value: str | None) -> list[dict[str, str]]:
    if value is None or not value.strip():
        return []
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise _input_error("hotspot_decisions is not valid JSON") from error
    if not isinstance(payload, list):
        raise _input_error("hotspot_decisions must be a JSON array")
    if len(payload) > MAX_RANKED_REVIEW_HOTSPOTS:
        raise _input_error(
            f"hotspot_decisions count={len(payload)} exceeds "
            f"{MAX_RANKED_REVIEW_HOTSPOTS}"
        )
    result: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            raise _input_error("hotspot_decisions contains a non-object entry")
        unknown_fields = set(item) - {"hotspot_id", "disposition", "note"}
        if unknown_fields:
            raise _input_error(
                "hotspot_decisions contains unsupported fields: "
                + ", ".join(sorted(unknown_fields))
            )
        hotspot_id = item.get("hotspot_id")
        disposition = item.get("disposition")
        note = item.get("note", "")
        if not isinstance(hotspot_id, str) or not hotspot_id:
            raise _input_error("hotspot_decisions contains an invalid hotspot_id")
        if hotspot_id in seen_ids:
            raise _input_error(
                f"hotspot_decisions contains duplicate ID {hotspot_id}"
            )
        if not isinstance(disposition, str) or disposition not in HOTSPOT_DISPOSITIONS:
            raise _input_error(
                f"hotspot_decisions contains invalid disposition {disposition!r}"
            )
        if not isinstance(note, str):
            raise _input_error("hotspot_decisions note must be a string")
        note = note.strip()
        if len(note) > MAX_HOTSPOT_NOTE_CHARS:
            raise _input_error(
                f"hotspot_decisions note exceeds {MAX_HOTSPOT_NOTE_CHARS} characters"
            )
        if any(ord(character) < 32 for character in note):
            raise _input_error("hotspot_decisions note contains control characters")
        decision = {
            "hotspot_id": hotspot_id,
            "disposition": str(disposition),
        }
        if note:
            decision["note"] = note
        result.append(decision)
        seen_ids.add(hotspot_id)
    return result


def _png_bytes(image: np.ndarray, label: str) -> bytes:
    encoded_ok, encoded = cv2.imencode(".png", image)
    if not encoded_ok:
        raise ProjectError(
            "E504",
            "主动学习图像编码失败",
            "Encoding an active-learning image failed",
            "保留量测结果并重新运行",
            "Keep the measurement and rerun",
            label,
        )
    return encoded.tobytes()


def _feedback_crop_bounds(
    bounding_box: dict[str, object],
    image_shape: tuple[int, int],
) -> tuple[int, int, int, int]:
    try:
        x = float(bounding_box["x"])
        y = float(bounding_box["y"])
        width = float(bounding_box["width"])
        height = float(bounding_box["height"])
    except (KeyError, TypeError, ValueError) as error:
        raise _input_error("ranked hotspot bounding box is malformed") from error
    if not all(math.isfinite(value) for value in (x, y, width, height)):
        raise _input_error("ranked hotspot bounding box is not finite")
    if width <= 0 or height <= 0:
        raise _input_error("ranked hotspot bounding box is empty")
    image_height, image_width = image_shape
    padding = max(8, math.ceil(max(width, height) * 0.15))
    x0 = max(0, math.floor(x) - padding)
    y0 = max(0, math.floor(y) - padding)
    x1 = min(image_width, math.ceil(x + width) + padding)
    y1 = min(image_height, math.ceil(y + height) + padding)
    if x1 <= x0 or y1 <= y0:
        raise _input_error("ranked hotspot crop is outside the source image")
    return x0, y0, x1, y1


def _bounded_feedback_layers(
    source: np.ndarray,
    proposal: np.ndarray,
    final: np.ndarray,
    disagreement: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
    height, width = source.shape[:2]
    scale = min(1.0, math.sqrt(MAX_FEEDBACK_CROP_PIXELS / (height * width)))
    if scale == 1.0:
        return source, proposal, final, disagreement, scale
    target_width = max(1, math.floor(width * scale))
    target_height = max(1, math.floor(height * scale))
    size = (target_width, target_height)
    return (
        cv2.resize(source, size, interpolation=cv2.INTER_AREA),
        cv2.resize(proposal, size, interpolation=cv2.INTER_NEAREST),
        cv2.resize(final, size, interpolation=cv2.INTER_NEAREST),
        cv2.resize(disagreement, size, interpolation=cv2.INTER_NEAREST),
        scale,
    )


def _feedback_quality_gate(
    disposition: str,
    proposal: np.ndarray,
    final: np.ndarray,
) -> dict[str, object]:
    proposed = proposal >= 128
    reviewed = final >= 128
    added = int(np.count_nonzero(reviewed & ~proposed))
    removed = int(np.count_nonzero(proposed & ~reviewed))
    changed = added + removed
    intersection = int(np.count_nonzero(proposed & reviewed))
    union = int(np.count_nonzero(proposed | reviewed))
    warning_codes: list[str] = []
    if disposition == "accepted_as_proposed" and changed:
        warning_codes.append("accepted_but_mask_changed")
    elif disposition == "false_positive_removed":
        if removed == 0:
            warning_codes.append("removal_disposition_without_removed_pixels")
        if added:
            warning_codes.append("removal_disposition_also_added_pixels")
    elif disposition == "missed_crack_added":
        if added == 0:
            warning_codes.append("addition_disposition_without_added_pixels")
        if removed:
            warning_codes.append("addition_disposition_also_removed_pixels")
    status = (
        "deferred"
        if disposition == "deferred_for_follow_up"
        else "warning"
        if warning_codes
        else "pass"
    )
    return {
        "status": status,
        "warning_codes": warning_codes,
        "proposal_foreground_pixels": int(np.count_nonzero(proposed)),
        "final_foreground_pixels": int(np.count_nonzero(reviewed)),
        "added_pixels": added,
        "removed_pixels": removed,
        "changed_pixels": changed,
        "proposal_final_iou": round(intersection / union, 8) if union else None,
        "interpretation": (
            "A workflow consistency check between the operator disposition and "
            "ROI pixel changes; not label correctness or field validation"
        ),
    }


def _difference_hash64(image: np.ndarray) -> str:
    if image.ndim == 3:
        grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    elif image.ndim == 2:
        grayscale = image
    else:
        raise _input_error(f"feedback fingerprint image shape={image.shape}")
    resized = cv2.resize(grayscale, (9, 8), interpolation=cv2.INTER_AREA)
    differences = resized[:, 1:] > resized[:, :-1]
    fingerprint = 0
    for value in differences.ravel():
        fingerprint = (fingerprint << 1) | int(value)
    return f"{fingerprint:016x}"


def _deterministic_zip_bytes(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for name in sorted(entries):
            member = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            member.compress_type = zipfile.ZIP_DEFLATED
            member.create_system = 3
            member.external_attr = 0o644 << 16
            archive.writestr(member, entries[name])
    return buffer.getvalue()


def _feedback_manifest(path: Path) -> tuple[dict[str, object], str]:
    try:
        with zipfile.ZipFile(path) as archive:
            info = archive.getinfo("manifest.json")
            if info.file_size <= 0 or info.file_size > MAX_FEEDBACK_MANIFEST_BYTES:
                raise ValueError(
                    f"feedback manifest bytes={info.file_size}"
                )
            raw = archive.read(info)
            payload = json.loads(raw.decode("utf-8"))
    except (
        KeyError,
        OSError,
        UnicodeDecodeError,
        ValueError,
        json.JSONDecodeError,
        zipfile.BadZipFile,
    ) as error:
        raise _input_error(f"feedback package {path.name} is malformed") from error
    if not isinstance(payload, dict):
        raise _input_error(f"feedback package {path.name} manifest is not an object")
    return payload, _sha256(raw)


def _curation_ratios(
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
) -> dict[str, float]:
    ratios: dict[str, float] = {}
    for split, value in zip(
        CURATION_SPLITS,
        (train_ratio, val_ratio, test_ratio),
        strict=True,
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise _input_error(f"{split}_ratio={value!r}")
        ratio = float(value)
        if not math.isfinite(ratio) or not 0 < ratio < 1:
            raise _input_error(f"{split}_ratio={value!r}")
        ratios[split] = ratio
    if not math.isclose(sum(ratios.values()), 1.0, abs_tol=1e-9):
        raise _input_error(f"curation ratios sum={sum(ratios.values())!r}")
    return ratios


def _is_hex_digest(value: object, length: int) -> bool:
    if not isinstance(value, str) or len(value) != length:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _curation_file_evidence(
    value: object,
) -> dict[str, dict[str, str]] | None:
    if not isinstance(value, dict):
        return None
    result: dict[str, dict[str, str]] = {}
    for role in FEEDBACK_FILE_ROLES:
        evidence = value.get(role)
        if not isinstance(evidence, dict):
            return None
        path = evidence.get("path")
        digest = evidence.get("sha256")
        if (
            not isinstance(path, str)
            or not path.startswith("items/")
            or "\\" in path
            or ".." in path.split("/")
            or not _is_hex_digest(digest, 64)
        ):
            return None
        result[role] = {"path": path, "sha256": str(digest)}
    return result


def _fingerprint_hamming_distance(left: str, right: str) -> int:
    if not _is_hex_digest(left, 16) or not _is_hex_digest(right, 16):
        raise _input_error(
            f"invalid 64-bit fingerprints left={left!r}, right={right!r}"
        )
    return (int(left, 16) ^ int(right, 16)).bit_count()


def _near_duplicate_scene_groups(
    source_fingerprints: dict[str, set[str]],
    max_hamming_distance: int,
) -> dict[str, object]:
    """Create deterministic single-linkage groups over source ROI fingerprints."""
    if (
        isinstance(max_hamming_distance, bool)
        or not isinstance(max_hamming_distance, int)
        or not 0 <= max_hamming_distance <= 16
    ):
        raise _input_error(
            f"max_scene_hamming_distance={max_hamming_distance!r}"
        )
    for source, fingerprints in source_fingerprints.items():
        if not _is_hex_digest(source, 64) or not fingerprints:
            raise _input_error(
                f"source scene fingerprints are missing for {source!r}"
            )
        if any(not _is_hex_digest(fingerprint, 16) for fingerprint in fingerprints):
            raise _input_error(
                f"source scene fingerprints are invalid for {source!r}"
            )
    sources = sorted(source_fingerprints)
    parent = {source: source for source in sources}

    def find(source: str) -> str:
        root = source
        while parent[root] != root:
            root = parent[root]
        while parent[source] != source:
            next_source = parent[source]
            parent[source] = root
            source = next_source
        return root

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root == right_root:
            return
        first, second = sorted((left_root, right_root))
        parent[second] = first

    links: list[dict[str, object]] = []
    for left_index, left_source in enumerate(sources):
        left_fingerprints = sorted(source_fingerprints[left_source])
        for right_source in sources[left_index + 1 :]:
            right_fingerprints = sorted(source_fingerprints[right_source])
            closest = min(
                (
                    _fingerprint_hamming_distance(left, right),
                    left,
                    right,
                )
                for left in left_fingerprints
                for right in right_fingerprints
            )
            if closest[0] > max_hamming_distance:
                continue
            union(left_source, right_source)
            links.append(
                {
                    "left_source_sha256": left_source,
                    "right_source_sha256": right_source,
                    "hamming_distance": closest[0],
                    "left_difference_hash64": closest[1],
                    "right_difference_hash64": closest[2],
                }
            )
    components: dict[str, list[str]] = {}
    for source in sources:
        components.setdefault(find(source), []).append(source)
    groups: list[dict[str, object]] = []
    source_to_group: dict[str, str] = {}
    for members in sorted(components.values(), key=lambda values: tuple(values)):
        scene_group_id = "visual-scene-" + hashlib.sha256(
            ",".join(members).encode()
        ).hexdigest()[:24]
        for source in members:
            source_to_group[source] = scene_group_id
        groups.append(
            {
                "scene_group_id": scene_group_id,
                "source_count": len(members),
                "source_sha256s": members,
            }
        )
    return {
        "source_to_scene_group": source_to_group,
        "groups": groups,
        "links": links,
    }


def _canonical_merkle_root(records: list[dict[str, object]]) -> str:
    canonical_leaves = sorted(
        json.dumps(
            record,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        for record in records
    )
    if not canonical_leaves:
        return hashlib.sha256(b"\x00").hexdigest()
    level = [
        hashlib.sha256(b"\x00" + canonical).digest()
        for canonical in canonical_leaves
    ]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [
            hashlib.sha256(b"\x01" + level[index] + level[index + 1]).digest()
            for index in range(0, len(level), 2)
        ]
    return level[0].hex()


def _assign_curation_groups(
    groups: dict[str, list[dict[str, object]]],
    ratios: dict[str, float],
    seed: int,
) -> dict[str, list[dict[str, object]]]:
    """Assign whole governance groups while approximating requested item ratios."""
    total_items = sum(len(items) for items in groups.values())
    targets = {
        split: total_items * ratios[split]
        for split in CURATION_SPLITS
    }
    assigned = {split: [] for split in CURATION_SPLITS}
    counts = {split: 0 for split in CURATION_SPLITS}
    ordered_groups = sorted(
        groups.items(),
        key=lambda entry: (
            -len(entry[1]),
            hashlib.sha256(f"{seed}:{entry[0]}".encode()).hexdigest(),
            entry[0],
        ),
    )
    for _, items in ordered_groups:
        split = max(
            CURATION_SPLITS,
            key=lambda candidate: (
                targets[candidate] - counts[candidate],
                -CURATION_SPLITS.index(candidate),
            ),
        )
        assigned[split].extend(items)
        counts[split] += len(items)
    return assigned


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
        hotspot_mask = proposal.review_hotspots.astype(np.uint8) * 255
        hotspot_encoded_ok, hotspot_encoded = cv2.imencode(".png", hotspot_mask)
        if not hotspot_encoded_ok:
            raise ProjectError(
                "E504",
                "复核热点编码失败",
                "Encoding the review hotspots failed",
                "保留原图并检查 OpenCV 环境",
                "Keep the source image and inspect the OpenCV environment",
            )
        hotspot_bytes = hotspot_encoded.tobytes()
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
            "review_hotspots": {
                "filename": "review-hotspots.png",
                "sha256": _sha256(hotspot_bytes),
                "foreground_pixels": int(np.count_nonzero(proposal.review_hotspots)),
            },
            "privacy": (
                "No absolute input path or source pixels are stored; processing stays on loopback"
            ),
        }
        output_dir = self.paths.metrology / "proposals" / proposal_id
        mask_path = output_dir / "proposal-mask.png"
        hotspot_path = output_dir / "review-hotspots.png"
        evidence_path = output_dir / "evidence.json"
        with self._write_lock:
            if mask_path.exists() or hotspot_path.exists() or evidence_path.exists():
                raise ProjectError(
                    "E204",
                    "候选掩膜记录已经存在",
                    "The proposed-mask record already exists",
                    "保留现有记录并重新生成候选掩膜",
                    "Keep the record and generate a new proposal",
                    proposal_id,
                )
            self._write_bytes_exclusive(mask_path, mask_bytes)
            self._write_bytes_exclusive(hotspot_path, hotspot_bytes)
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
        reviewed_hotspot_ids: list[str],
        hotspot_decisions: list[dict[str, str]],
        review_authority: str,
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
        if review_authority == "machine_heuristic" and changed:
            raise _input_error(
                "machine_reviewed_candidate must preserve the immutable "
                "proposal mask"
            )
        algorithm_version = evidence.get("schema_version")
        review_guidance = evidence.get("review_guidance")
        ranking = (
            review_guidance.get("ranking")
            if isinstance(review_guidance, dict)
            else None
        )
        ranked_hotspots = (
            ranking.get("ranked_hotspots")
            if isinstance(ranking, dict)
            else None
        )
        available_hotspots = (
            [
                hotspot
                for hotspot in ranked_hotspots
                if isinstance(hotspot, dict)
                and isinstance(hotspot.get("hotspot_id"), str)
            ]
            if isinstance(ranked_hotspots, list)
            else []
        )
        available_ids = [
            str(hotspot["hotspot_id"]) for hotspot in available_hotspots
        ]
        unknown_ids = sorted(set(reviewed_hotspot_ids) - set(available_ids))
        if unknown_ids:
            raise _input_error(
                "reviewed_hotspots contains IDs outside the current proposal: "
                + ", ".join(unknown_ids)
            )
        decision_ids = [decision["hotspot_id"] for decision in hotspot_decisions]
        unknown_decision_ids = sorted(set(decision_ids) - set(available_ids))
        if unknown_decision_ids:
            raise _input_error(
                "hotspot_decisions contains IDs outside the current proposal: "
                + ", ".join(unknown_decision_ids)
            )
        unreviewed_decision_ids = sorted(
            set(decision_ids) - set(reviewed_hotspot_ids)
        )
        if unreviewed_decision_ids:
            raise _input_error(
                "hotspot_decisions require the same IDs in reviewed_hotspots: "
                + ", ".join(unreviewed_decision_ids)
            )
        reviewed_set = set(reviewed_hotspot_ids)
        reviewed_in_rank_order = [
            hotspot_id for hotspot_id in available_ids if hotspot_id in reviewed_set
        ]
        total_priority = sum(
            float(hotspot.get("priority_score", 0.0))
            for hotspot in available_hotspots
        )
        reviewed_priority = sum(
            float(hotspot.get("priority_score", 0.0))
            for hotspot in available_hotspots
            if hotspot["hotspot_id"] in reviewed_set
        )
        ranked_count = len(available_ids)
        reviewed_count = len(reviewed_in_rank_order)
        decisions_by_id = {
            decision["hotspot_id"]: decision for decision in hotspot_decisions
        }
        if review_authority == "machine_heuristic":
            if set(reviewed_hotspot_ids) != set(available_ids):
                raise _input_error(
                    "machine_reviewed_candidate must inspect every ranked hotspot"
                )
            if set(decisions_by_id) != set(available_ids):
                raise _input_error(
                    "machine_reviewed_candidate must disposition every ranked hotspot"
                )
            for hotspot in available_hotspots:
                overlap = float(hotspot.get("candidate_overlap_ratio", 0.0))
                expected = (
                    "accepted_as_proposed"
                    if overlap >= AUTOPILOT_ACCEPT_OVERLAP
                    else "deferred_for_follow_up"
                )
                actual = decisions_by_id[str(hotspot["hotspot_id"])][
                    "disposition"
                ]
                if actual != expected:
                    raise _input_error(
                        "machine_reviewed_candidate decision differs from "
                        f"autopilot policy for {hotspot['hotspot_id']}"
                    )
        decisions_in_rank_order = [
            decisions_by_id[hotspot_id]
            for hotspot_id in available_ids
            if hotspot_id in decisions_by_id
        ]
        decided_priority = sum(
            float(hotspot.get("priority_score", 0.0))
            for hotspot in available_hotspots
            if hotspot["hotspot_id"] in decisions_by_id
        )
        disposition_counts = {
            disposition: sum(
                decision["disposition"] == disposition
                for decision in decisions_in_rank_order
            )
            for disposition in sorted(HOTSPOT_DISPOSITIONS)
        }
        decided_count = len(decisions_in_rank_order)
        review_status = (
            "not_available"
            if ranked_count == 0
            else "complete"
            if reviewed_count == ranked_count
            else "partial"
            if reviewed_count
            else "not_started"
        )
        decision_status = (
            "not_available"
            if ranked_count == 0
            else "complete"
            if decided_count == ranked_count
            else "partial"
            if decided_count
            else "not_started"
        )
        hotspot_review = {
            "review_authority": review_authority,
            "decision_policy": (
                "candidate_overlap_ratio>=0.10_accept_else_defer"
                if review_authority == "machine_heuristic"
                else "operator_recorded"
            ),
            "status": review_status,
            "decision_status": decision_status,
            "ranked_hotspot_count": ranked_count,
            "total_detected_component_count": (
                review_guidance.get("review_zone_component_count")
                if isinstance(review_guidance, dict)
                else None
            ),
            "raw_display_hotspot_component_count": (
                review_guidance.get("review_hotspot_component_count")
                if isinstance(review_guidance, dict)
                else None
            ),
            "ranked_disagreement_pixel_coverage_ratio": (
                ranking.get("ranked_disagreement_pixel_coverage_ratio")
                if isinstance(ranking, dict)
                else None
            ),
            "ranked_priority_mass_ratio": (
                ranking.get("ranked_priority_mass_ratio")
                if isinstance(ranking, dict)
                else None
            ),
            "reviewed_hotspot_ids": reviewed_in_rank_order,
            "reviewed_hotspot_count": reviewed_count,
            "decisions": decisions_in_rank_order,
            "decided_hotspot_count": decided_count,
            "disposition_counts": disposition_counts,
            "ranked_review_completion_ratio": (
                round(reviewed_count / ranked_count, 8) if ranked_count else None
            ),
            "ranked_priority_coverage_ratio": (
                round(reviewed_priority / total_priority, 8)
                if total_priority > 0
                else None
            ),
            "ranked_decision_completion_ratio": (
                round(decided_count / ranked_count, 8) if ranked_count else None
            ),
            "ranked_decision_priority_coverage_ratio": (
                round(decided_priority / total_priority, 8)
                if total_priority > 0
                else None
            ),
            "interpretation": (
                "This records which ranked sensitivity-disagreement regions the "
                f"{review_authority} workflow dispositioned; "
                "it does not prove mask correctness or field conditions"
            ),
        }
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
            "hotspot_review": hotspot_review,
            "interpretation": (
                "Difference between the immutable local proposal and the "
                f"browser-submitted mask; review authority={review_authority}"
            ),
        }

    def _active_learning_feedback_bytes(
        self,
        *,
        run_id: str,
        output_dir: Path,
        proposal_id: str,
        source_sha256: str,
        source_image: np.ndarray,
        final_mask: np.ndarray,
        hotspot_decisions: list[dict[str, str]],
        review_authority: str,
    ) -> bytes:
        safe_proposal_id = validate_run_name(proposal_id)
        proposal_dir = self.paths.metrology / "proposals" / safe_proposal_id
        try:
            evidence = json.loads(
                (proposal_dir / "evidence.json").read_text(encoding="utf-8")
            )
            proposal_bytes = (proposal_dir / "proposal-mask.png").read_bytes()
            disagreement_bytes = (
                proposal_dir / "review-hotspots.png"
            ).read_bytes()
            measurement_bytes = (output_dir / "measurement.json").read_bytes()
            measurement_payload = json.loads(measurement_bytes)
        except (OSError, json.JSONDecodeError) as error:
            raise _input_error(
                f"proposal {safe_proposal_id} cannot produce feedback"
            ) from error
        proposal_image = cv2.imdecode(
            np.frombuffer(proposal_bytes, dtype=np.uint8),
            cv2.IMREAD_GRAYSCALE,
        )
        disagreement_image = cv2.imdecode(
            np.frombuffer(disagreement_bytes, dtype=np.uint8),
            cv2.IMREAD_GRAYSCALE,
        )
        expected_shape = final_mask.shape
        if (
            proposal_image is None
            or disagreement_image is None
            or proposal_image.shape != expected_shape
            or disagreement_image.shape != expected_shape
            or source_image.shape[:2] != expected_shape
        ):
            raise _input_error(
                f"proposal {safe_proposal_id} feedback layers do not align"
            )
        source = evidence.get("source") if isinstance(evidence, dict) else None
        if not isinstance(source, dict) or source.get("sha256") != source_sha256:
            raise _input_error(
                f"proposal {safe_proposal_id} feedback source digest differs"
            )
        review_guidance = (
            evidence.get("review_guidance") if isinstance(evidence, dict) else None
        )
        ranking = (
            review_guidance.get("ranking")
            if isinstance(review_guidance, dict)
            else None
        )
        ranked_hotspots = (
            ranking.get("ranked_hotspots") if isinstance(ranking, dict) else None
        )
        if not isinstance(ranked_hotspots, list):
            raise _input_error(
                f"proposal {safe_proposal_id} has no ranked feedback targets"
            )
        decisions_by_id = {
            decision["hotspot_id"]: decision for decision in hotspot_decisions
        }
        entries: dict[str, bytes] = {
            "README.txt": (
                "UrbanVision-Risk active-learning feedback package\n"
                "UrbanVision-Risk 主动学习反馈包\n\n"
                "Each item contains one source ROI, the immutable proposal mask, "
                "the submitted candidate mask, and the sensitivity-disagreement "
                "layer.\n"
                "每项包含原图 ROI、不可变候选掩膜、提交的候选掩膜和灵敏度分歧层。\n\n"
                "Machine or operator dispositions are workflow observations, not "
                "ground truth, "
                "engineering diagnoses, repair orders, or road-safety labels.\n"
                "机器或操作员处置是工作流观察，不是真值、工程诊断、维修工单或道路安全标签。\n"
            ).encode()
        }
        manifest_items: list[dict[str, object]] = []
        for hotspot in ranked_hotspots:
            if not isinstance(hotspot, dict):
                continue
            hotspot_id = hotspot.get("hotspot_id")
            if not isinstance(hotspot_id, str) or hotspot_id not in decisions_by_id:
                continue
            safe_hotspot_id = validate_run_name(hotspot_id)
            bounding_box = hotspot.get("bounding_box")
            if not isinstance(bounding_box, dict):
                raise _input_error(
                    f"proposal {safe_proposal_id} hotspot {safe_hotspot_id} has no box"
                )
            x0, y0, x1, y1 = _feedback_crop_bounds(
                bounding_box,
                expected_shape,
            )
            source_crop = source_image[y0:y1, x0:x1]
            proposal_crop = proposal_image[y0:y1, x0:x1]
            final_crop = np.where(final_mask[y0:y1, x0:x1], 255, 0).astype(
                np.uint8
            )
            disagreement_crop = disagreement_image[y0:y1, x0:x1]
            decision = decisions_by_id[hotspot_id]
            source_fingerprint = _difference_hash64(source_crop)
            quality_gate = _feedback_quality_gate(
                decision["disposition"],
                proposal_crop,
                final_crop,
            )
            (
                source_crop,
                proposal_crop,
                final_crop,
                disagreement_crop,
                export_scale,
            ) = _bounded_feedback_layers(
                source_crop,
                proposal_crop,
                final_crop,
                disagreement_crop,
            )
            rank = int(hotspot.get("rank", len(manifest_items) + 1))
            item_root = f"items/{rank:02d}-{safe_hotspot_id}"
            item_files = {
                "source_roi": (
                    f"{item_root}/source.png",
                    _png_bytes(source_crop, f"{safe_hotspot_id}/source"),
                ),
                "proposal_mask": (
                    f"{item_root}/proposal-mask.png",
                    _png_bytes(proposal_crop, f"{safe_hotspot_id}/proposal"),
                ),
                "final_mask": (
                    f"{item_root}/final-mask.png",
                    _png_bytes(final_crop, f"{safe_hotspot_id}/final"),
                ),
                "disagreement_layer": (
                    f"{item_root}/review-hotspots.png",
                    _png_bytes(
                        disagreement_crop,
                        f"{safe_hotspot_id}/disagreement",
                    ),
                ),
            }
            file_evidence: dict[str, object] = {}
            for role, (path, content) in item_files.items():
                entries[path] = content
                file_evidence[role] = {
                    "path": path,
                    "sha256": _sha256(content),
                }
            manifest_items.append(
                {
                    "hotspot_id": hotspot_id,
                    "rank": rank,
                    "disposition": decision["disposition"],
                    "decision_authority": review_authority,
                    **(
                        {"note": decision["note"]}
                        if decision.get("note")
                        else {}
                    ),
                    "source_bounding_box": bounding_box,
                    "export_crop": {
                        "x": x0,
                        "y": y0,
                        "width": x1 - x0,
                        "height": y1 - y0,
                        "scale": round(export_scale, 8),
                        "export_width": int(source_crop.shape[1]),
                        "export_height": int(source_crop.shape[0]),
                    },
                    "priority_score": hotspot.get("priority_score"),
                    "disagreement_pixels": hotspot.get("disagreement_pixels"),
                    "candidate_overlap_ratio": hotspot.get(
                        "candidate_overlap_ratio"
                    ),
                    "source_roi_difference_hash64": source_fingerprint,
                    "quality_gate": quality_gate,
                    "files": file_evidence,
                }
            )
        if len(manifest_items) != len(hotspot_decisions):
            missing = sorted(
                set(decisions_by_id)
                - {str(item["hotspot_id"]) for item in manifest_items}
            )
            raise _input_error(
                "active-learning feedback is missing ranked hotspots: "
                + ", ".join(missing)
            )
        disposition_counts = {
            disposition: sum(
                item["disposition"] == disposition for item in manifest_items
            )
            for disposition in sorted(HOTSPOT_DISPOSITIONS)
        }
        quality_counts = {
            status: sum(
                isinstance(item.get("quality_gate"), dict)
                and item["quality_gate"].get("status") == status
                for item in manifest_items
            )
            for status in ("pass", "warning", "deferred")
        }
        fingerprint_counts: dict[str, int] = {}
        for item in manifest_items:
            fingerprint = str(item["source_roi_difference_hash64"])
            fingerprint_counts[fingerprint] = fingerprint_counts.get(fingerprint, 0) + 1
        duplicate_fingerprint_groups = sum(
            count > 1 for count in fingerprint_counts.values()
        )
        measurement_run = (
            measurement_payload.get("run")
            if isinstance(measurement_payload, dict)
            else None
        )
        manifest = {
            "schema_version": "urbanvision-active-learning-feedback-v1.2.0",
            "run_id": run_id,
            "proposal_id": safe_proposal_id,
            "review_authority": review_authority,
            "decision_policy": (
                "candidate_overlap_ratio>=0.10_accept_else_defer"
                if review_authority == "machine_heuristic"
                else "operator_recorded"
            ),
            "created_at_utc": (
                measurement_run.get("created_at_utc")
                if isinstance(measurement_run, dict)
                else None
            ),
            "source_sha256": source_sha256,
            "measurement_sha256": _sha256(measurement_bytes),
            "item_count": len(manifest_items),
            "disposition_counts": disposition_counts,
            "quality_summary": {
                **quality_counts,
                "duplicate_fingerprint_group_count": duplicate_fingerprint_groups,
            },
            "items": manifest_items,
            "privacy": (
                "Local-only export; source ROIs may contain identifiable people, "
                "vehicles, or locations and require dataset governance"
            ),
            "intended_use": (
                "Human review, relabeling, error analysis, and candidate selection "
                "for a separately governed future training dataset"
            ),
            "claim_boundary": (
                "Machine or operator dispositions are not automatic ground truth, "
                "engineering diagnoses, repair orders, or road-safety labels"
            ),
        }
        entries["manifest.json"] = (
            json.dumps(
                manifest,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode()
        return _deterministic_zip_bytes(entries)

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
        review_state: str = "human_reviewed",
        reviewed_hotspots: str | None = None,
        hotspot_decisions: str | None = None,
    ) -> dict[str, object]:
        if not 0 <= uncertainty_samples <= 512:
            raise _input_error(f"uncertainty_samples={uncertainty_samples}")
        if not 0 <= segmentation_radius_pixels <= 5:
            raise _input_error(f"segmentation_radius_pixels={segmentation_radius_pixels}")
        if review_state not in REVIEW_AUTHORITIES:
            raise _input_error(f"review_state={review_state!r}")
        review_authority = REVIEW_AUTHORITIES[review_state]
        reviewed_hotspot_ids = _reviewed_hotspot_ids(reviewed_hotspots)
        parsed_hotspot_decisions = _hotspot_decisions(hotspot_decisions)
        if reviewed_hotspot_ids and review_state == "automatic_draft":
            raise _input_error(
                "automatic_draft cannot contain reviewed hotspot IDs"
            )
        if parsed_hotspot_decisions and review_state == "automatic_draft":
            raise _input_error(
                "automatic_draft cannot contain hotspot decisions"
            )
        if reviewed_hotspot_ids and not proposal_id:
            raise _input_error(
                "reviewed hotspot IDs require a proposal_id"
            )
        if parsed_hotspot_decisions and not proposal_id:
            raise _input_error("hotspot decisions require a proposal_id")
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
        if proposal_id and review_state == "automatic_draft":
            mask_origin = "local_proposal_automatic_draft"
        elif proposal_id and review_state == "machine_reviewed_candidate":
            mask_origin = "local_proposal_machine_reviewed_candidate"
        elif proposal_id:
            mask_origin = "local_proposal_submitted_after_human_editing"
        else:
            mask_origin = "manual_browser_mask"
        mask_evidence: dict[str, object] = {
            "filename": _safe_filename(
                mask_filename,
                "browser-mask.png",
            ),
            "sha256": _sha256(mask_content),
            "foreground_pixels": int(np.count_nonzero(mask)),
            "origin": mask_origin,
        }
        if proposal_id:
            mask_evidence["proposal_revision"] = self._proposal_revision(
                proposal_id=proposal_id,
                source_sha256=source_digest,
                final_mask=mask,
                reviewed_hotspot_ids=reviewed_hotspot_ids,
                hotspot_decisions=parsed_hotspot_decisions,
                review_authority=review_authority,
            )
        input_evidence = {
            "kind": "local_web_metrology",
            "review_state": review_state,
            "review_authority": review_authority,
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
            if proposal_id and parsed_hotspot_decisions:
                feedback_bytes = self._active_learning_feedback_bytes(
                    run_id=run_id,
                    output_dir=output_dir,
                    proposal_id=proposal_id,
                    source_sha256=source_digest,
                    source_image=source_image,
                    final_mask=mask,
                    hotspot_decisions=parsed_hotspot_decisions,
                    review_authority=review_authority,
                )
                self._write_bytes_exclusive(
                    output_dir / ACTIVE_LEARNING_FEEDBACK_ARTIFACT,
                    feedback_bytes,
                )
        return self._response(run_id, output_dir)

    def _feedback_packages(self) -> tuple[list[dict[str, object]], int]:
        packages: list[dict[str, object]] = []
        invalid_package_count = 0
        if self.paths.metrology.is_dir():
            for run_dir in self.paths.metrology.iterdir():
                package_path = run_dir / ACTIVE_LEARNING_FEEDBACK_ARTIFACT
                if not run_dir.is_dir() or not package_path.is_file():
                    continue
                try:
                    run_id = validate_run_name(run_dir.name)
                    manifest, manifest_sha256 = _feedback_manifest(package_path)
                except ProjectError:
                    invalid_package_count += 1
                    continue
                items = manifest.get("items")
                if not isinstance(items, list):
                    invalid_package_count += 1
                    continue
                packages.append(
                    {
                        "run_id": run_id,
                        "proposal_id": manifest.get("proposal_id"),
                        "created_at_utc": manifest.get("created_at_utc"),
                        "source_sha256": manifest.get("source_sha256"),
                        "review_authority": manifest.get(
                            "review_authority",
                            "legacy_unknown",
                        ),
                        "schema_version": manifest.get("schema_version"),
                        "manifest_sha256": manifest_sha256,
                        "items": [item for item in items if isinstance(item, dict)],
                        "feedback_url": (
                            f"/api/metrology/runs/{run_id}/"
                            f"{ACTIVE_LEARNING_FEEDBACK_ARTIFACT}"
                        ),
                    }
                )
        packages.sort(
            key=lambda package: (
                str(package.get("created_at_utc") or ""),
                str(package["run_id"]),
            ),
            reverse=True,
        )
        return packages, invalid_package_count

    def feedback_catalog(self, *, limit: int = 50) -> dict[str, object]:
        if not 1 <= limit <= MAX_FEEDBACK_CATALOG_PACKAGES:
            raise _input_error(f"feedback catalog limit={limit}")
        packages, invalid_package_count = self._feedback_packages()
        available_package_count = len(packages)
        returned_packages = packages[:limit]
        disposition_counts = {
            disposition: 0 for disposition in sorted(HOTSPOT_DISPOSITIONS)
        }
        quality_counts = {
            "pass": 0,
            "warning": 0,
            "deferred": 0,
            "unknown": 0,
        }
        review_authority_counts = {
            "human_operator": 0,
            "machine_heuristic": 0,
            "machine_unreviewed": 0,
            "legacy_unknown": 0,
        }
        fingerprints: dict[str, list[dict[str, str]]] = {}
        unique_sources: set[str] = set()
        item_count = 0
        package_summaries: list[dict[str, object]] = []
        for package in returned_packages:
            source_sha256 = package.get("source_sha256")
            if isinstance(source_sha256, str) and source_sha256:
                unique_sources.add(source_sha256)
            package_items = package["items"]
            if not isinstance(package_items, list):
                continue
            package_quality = {
                "pass": 0,
                "warning": 0,
                "deferred": 0,
                "unknown": 0,
            }
            package_dispositions = {
                disposition: 0 for disposition in sorted(HOTSPOT_DISPOSITIONS)
            }
            for item in package_items:
                if not isinstance(item, dict):
                    continue
                item_count += 1
                authority = item.get(
                    "decision_authority",
                    package.get(
                        "review_authority",
                        "legacy_unknown",
                    ),
                )
                if authority not in review_authority_counts:
                    authority = "legacy_unknown"
                review_authority_counts[str(authority)] += 1
                disposition = item.get("disposition")
                if (
                    isinstance(disposition, str)
                    and disposition in disposition_counts
                ):
                    disposition_counts[disposition] += 1
                    package_dispositions[disposition] += 1
                gate = item.get("quality_gate")
                quality_status = (
                    gate.get("status") if isinstance(gate, dict) else "unknown"
                )
                if (
                    not isinstance(quality_status, str)
                    or quality_status not in quality_counts
                ):
                    quality_status = "unknown"
                quality_counts[quality_status] += 1
                package_quality[quality_status] += 1
                fingerprint = item.get("source_roi_difference_hash64")
                hotspot_id = item.get("hotspot_id")
                if isinstance(fingerprint, str) and isinstance(hotspot_id, str):
                    fingerprints.setdefault(fingerprint, []).append(
                        {
                            "run_id": str(package["run_id"]),
                            "hotspot_id": hotspot_id,
                        }
                    )
            package_summaries.append(
                {
                    key: value
                    for key, value in package.items()
                    if key != "items"
                }
                | {
                    "item_count": len(package_items),
                    "disposition_counts": package_dispositions,
                    "quality_counts": package_quality,
                }
            )
        duplicate_groups = [
            {
                "difference_hash64": fingerprint,
                "item_count": len(items),
                "items": items,
            }
            for fingerprint, items in sorted(fingerprints.items())
            if len(items) > 1
        ]
        return {
            "local_only": True,
            "available_package_count": available_package_count,
            "returned_package_count": len(package_summaries),
            "invalid_package_count": invalid_package_count,
            "item_count": item_count,
            "unique_source_count": len(unique_sources),
            "disposition_counts": disposition_counts,
            "quality_counts": quality_counts,
            "review_authority_counts": review_authority_counts,
            "duplicate_fingerprint_group_count": len(duplicate_groups),
            "duplicate_fingerprint_item_count": sum(
                group["item_count"] for group in duplicate_groups
            ),
            "duplicate_fingerprint_groups": duplicate_groups,
            "packages": package_summaries,
            "interpretation": (
                "A local curation registry. Quality gates check workflow "
                "consistency, and equal difference hashes are duplicate candidates; "
                "neither proves label correctness or image identity"
            ),
        }

    def create_feedback_curation(
        self,
        *,
        seed: int = 42,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        minimum_unique_sources: int = 10,
        max_scene_hamming_distance: int = 4,
        privacy_review_confirmed: bool = False,
        label_qa_confirmed: bool = False,
        included_run_ids: list[str] | None = None,
    ) -> dict[str, object]:
        if (
            isinstance(seed, bool)
            or not isinstance(seed, int)
            or not 0 <= seed <= 2_147_483_647
        ):
            raise _input_error(f"curation seed={seed!r}")
        if (
            isinstance(minimum_unique_sources, bool)
            or not isinstance(minimum_unique_sources, int)
            or not 1 <= minimum_unique_sources <= 10_000
        ):
            raise _input_error(
                f"minimum_unique_sources={minimum_unique_sources!r}"
            )
        if not isinstance(privacy_review_confirmed, bool):
            raise _input_error(
                f"privacy_review_confirmed={privacy_review_confirmed!r}"
            )
        if not isinstance(label_qa_confirmed, bool):
            raise _input_error(f"label_qa_confirmed={label_qa_confirmed!r}")
        if (
            isinstance(max_scene_hamming_distance, bool)
            or not isinstance(max_scene_hamming_distance, int)
            or not 0 <= max_scene_hamming_distance <= 16
        ):
            raise _input_error(
                f"max_scene_hamming_distance={max_scene_hamming_distance!r}"
            )
        ratios = _curation_ratios(train_ratio, val_ratio, test_ratio)
        packages, invalid_package_count = self._feedback_packages()
        safe_included_run_ids: list[str] | None = None
        if included_run_ids is not None:
            if len(included_run_ids) > MAX_AUTOPILOT_BATCH_IMAGES:
                raise _input_error(
                    "included_run_ids exceeds the autopilot batch limit"
                )
            safe_included_run_ids = []
            for run_id in included_run_ids:
                safe_id = validate_run_name(run_id)
                if safe_id in safe_included_run_ids:
                    raise _input_error(
                        f"included_run_ids contains duplicate ID {safe_id}"
                    )
                safe_included_run_ids.append(safe_id)
            requested = set(safe_included_run_ids)
            packages = [
                package
                for package in packages
                if package["run_id"] in requested
            ]
            found = {str(package["run_id"]) for package in packages}
            missing = sorted(requested - found)
            if missing:
                raise _input_error(
                    "included_run_ids has no valid feedback package: "
                    + ", ".join(missing)
                )
            invalid_package_count = 0
        inventory_truncated = len(packages) > MAX_FEEDBACK_CATALOG_PACKAGES
        selected_packages = packages[:MAX_FEEDBACK_CATALOG_PACKAGES]
        inventory_refs = [
            {
                "run_id": package["run_id"],
                "manifest_sha256": package["manifest_sha256"],
                "source_sha256": package.get("source_sha256"),
            }
            for package in selected_packages
        ]
        inventory_digest = _sha256(
            json.dumps(
                inventory_refs,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ).encode()
        )
        exclusion_counts = {
            "quality_warning": 0,
            "deferred": 0,
            "quality_unknown": 0,
            "invalid_candidate": 0,
            "duplicate_fingerprint": 0,
        }
        candidates: list[dict[str, object]] = []
        for package in selected_packages:
            source_sha256 = package.get("source_sha256")
            package_authority = package.get("review_authority")
            if package_authority not in set(REVIEW_AUTHORITIES.values()):
                package_authority = "legacy_unknown"
            valid_source = _is_hex_digest(source_sha256, 64)
            package_items = package.get("items")
            if not isinstance(package_items, list):
                continue
            for item in package_items:
                if not isinstance(item, dict) or not valid_source:
                    exclusion_counts["invalid_candidate"] += 1
                    continue
                disposition = item.get("disposition")
                quality_gate = item.get("quality_gate")
                quality_status = (
                    quality_gate.get("status")
                    if isinstance(quality_gate, dict)
                    else None
                )
                if (
                    quality_status == "deferred"
                    or disposition == "deferred_for_follow_up"
                ):
                    exclusion_counts["deferred"] += 1
                    continue
                if quality_status == "warning":
                    exclusion_counts["quality_warning"] += 1
                    continue
                if quality_status != "pass":
                    exclusion_counts["quality_unknown"] += 1
                    continue
                fingerprint = item.get("source_roi_difference_hash64")
                hotspot_id = item.get("hotspot_id")
                rank = item.get("rank")
                files = item.get("files")
                source_box = item.get("source_bounding_box")
                export_crop = item.get("export_crop")
                priority = item.get("priority_score", 0.0)
                try:
                    priority_score = float(priority)
                except (TypeError, ValueError):
                    priority_score = math.nan
                safe_files = _curation_file_evidence(files)
                safe_source_box = (
                    {
                        key: source_box.get(key)
                        for key in ("x", "y", "width", "height")
                    }
                    if isinstance(source_box, dict)
                    else None
                )
                safe_export_crop = (
                    {
                        key: export_crop.get(key)
                        for key in (
                            "x",
                            "y",
                            "width",
                            "height",
                            "scale",
                            "export_width",
                            "export_height",
                        )
                    }
                    if isinstance(export_crop, dict)
                    else None
                )
                geometry_values = [
                    value
                    for mapping in (safe_source_box, safe_export_crop)
                    if mapping is not None
                    for value in mapping.values()
                ]
                valid_geometry = (
                    safe_source_box is not None
                    and safe_export_crop is not None
                    and all(
                        not isinstance(value, bool)
                        and isinstance(value, (int, float))
                        and math.isfinite(float(value))
                        for value in geometry_values
                    )
                    and float(safe_source_box["x"]) >= 0
                    and float(safe_source_box["y"]) >= 0
                    and float(safe_source_box["width"]) > 0
                    and float(safe_source_box["height"]) > 0
                    and float(safe_export_crop["x"]) >= 0
                    and float(safe_export_crop["y"]) >= 0
                    and float(safe_export_crop["width"]) > 0
                    and float(safe_export_crop["height"]) > 0
                    and float(safe_export_crop["scale"]) > 0
                    and float(safe_export_crop["export_width"]) > 0
                    and float(safe_export_crop["export_height"]) > 0
                )
                if (
                    not isinstance(disposition, str)
                    or disposition not in HOTSPOT_DISPOSITIONS
                    or not _is_hex_digest(fingerprint, 16)
                    or not isinstance(hotspot_id, str)
                    or not hotspot_id
                    or isinstance(rank, bool)
                    or not isinstance(rank, int)
                    or rank <= 0
                    or not math.isfinite(priority_score)
                    or safe_files is None
                    or not valid_geometry
                ):
                    exclusion_counts["invalid_candidate"] += 1
                    continue
                candidates.append(
                    {
                        "run_id": package["run_id"],
                        "proposal_id": package.get("proposal_id"),
                        "review_authority": (
                            item.get("decision_authority")
                            if item.get("decision_authority")
                            in set(REVIEW_AUTHORITIES.values())
                            else package_authority
                        ),
                        "source_sha256": source_sha256,
                        "manifest_sha256": package["manifest_sha256"],
                        "hotspot_id": hotspot_id,
                        "rank": rank,
                        "disposition": disposition,
                        "priority_score": round(priority_score, 8),
                        "source_roi_difference_hash64": fingerprint,
                        "feedback_url": package["feedback_url"],
                        "files": safe_files,
                        "source_bounding_box": safe_source_box,
                        "export_crop": safe_export_crop,
                    }
                )
        candidates.sort(
            key=lambda item: (
                -float(item["priority_score"]),
                str(item["run_id"]),
                str(item["hotspot_id"]),
            )
        )
        deduplicated: list[dict[str, object]] = []
        seen_fingerprints: set[str] = set()
        for candidate in candidates:
            fingerprint = str(candidate["source_roi_difference_hash64"])
            if fingerprint in seen_fingerprints:
                exclusion_counts["duplicate_fingerprint"] += 1
                continue
            seen_fingerprints.add(fingerprint)
            deduplicated.append(candidate)
        source_groups: dict[str, list[dict[str, object]]] = {}
        for candidate in deduplicated:
            source_groups.setdefault(
                str(candidate["source_sha256"]),
                [],
            ).append(candidate)
        review_authority_counts = {
            authority: sum(
                item["review_authority"] == authority
                for item in deduplicated
            )
            for authority in (
                "human_operator",
                "machine_heuristic",
                "machine_unreviewed",
                "legacy_unknown",
            )
        }
        machine_only_selected_count = (
            len(deduplicated)
            - review_authority_counts["human_operator"]
        )
        raw_source_fingerprints = {
            source: {
                str(item["source_roi_difference_hash64"])
                for item in items
            }
            for source, items in source_groups.items()
        }
        truncated_scene_fingerprint_count = sum(
            max(0, len(fingerprints) - MAX_SCENE_FINGERPRINTS_PER_SOURCE)
            for fingerprints in raw_source_fingerprints.values()
        )
        truncated_scene_source_count = sum(
            len(fingerprints) > MAX_SCENE_FINGERPRINTS_PER_SOURCE
            for fingerprints in raw_source_fingerprints.values()
        )
        source_fingerprints = {
            source: set(
                sorted(fingerprints)[:MAX_SCENE_FINGERPRINTS_PER_SOURCE]
            )
            for source, fingerprints in raw_source_fingerprints.items()
        }
        scene_clustering = _near_duplicate_scene_groups(
            source_fingerprints,
            max_scene_hamming_distance,
        )
        source_to_scene_group = scene_clustering["source_to_scene_group"]
        if not isinstance(source_to_scene_group, dict):
            raise RuntimeError("scene clustering did not return a source map")
        scene_candidate_groups: dict[str, list[dict[str, object]]] = {}
        for candidate in deduplicated:
            source_sha256 = str(candidate["source_sha256"])
            scene_group_id = str(source_to_scene_group[source_sha256])
            candidate["visual_scene_group_id"] = scene_group_id
            scene_candidate_groups.setdefault(scene_group_id, []).append(candidate)
        raw_scene_groups = scene_clustering["groups"]
        if not isinstance(raw_scene_groups, list):
            raise RuntimeError("scene clustering did not return groups")
        scene_groups: list[dict[str, object]] = []
        for group in raw_scene_groups:
            if not isinstance(group, dict):
                continue
            scene_group_id = str(group["scene_group_id"])
            scene_groups.append(
                {
                    **group,
                    "item_count": len(
                        scene_candidate_groups.get(scene_group_id, [])
                    ),
                }
            )
        assigned = _assign_curation_groups(
            scene_candidate_groups,
            ratios,
            seed,
        )
        split_payloads: dict[str, dict[str, object]] = {}
        source_sets: dict[str, set[str]] = {}
        scene_sets: dict[str, set[str]] = {}
        for split in CURATION_SPLITS:
            items = sorted(
                assigned[split],
                key=lambda item: (
                    str(item["visual_scene_group_id"]),
                    str(item["source_sha256"]),
                    str(item["run_id"]),
                    int(item["rank"]),
                    str(item["hotspot_id"]),
                ),
            )
            sources = {str(item["source_sha256"]) for item in items}
            scenes = {str(item["visual_scene_group_id"]) for item in items}
            source_sets[split] = sources
            scene_sets[split] = scenes
            split_payloads[split] = {
                "item_count": len(items),
                "unique_source_count": len(sources),
                "visual_scene_group_count": len(scenes),
                "source_sha256s": sorted(sources),
                "visual_scene_group_ids": sorted(scenes),
                "disposition_counts": {
                    disposition: sum(
                        item["disposition"] == disposition for item in items
                    )
                    for disposition in sorted(HOTSPOT_DISPOSITIONS)
                },
                "review_authority_counts": {
                    authority: sum(
                        item["review_authority"] == authority
                        for item in items
                    )
                    for authority in (
                        "human_operator",
                        "machine_heuristic",
                        "machine_unreviewed",
                        "legacy_unknown",
                    )
                },
                "items": items,
            }
        source_overlaps = {
            "train_val": sorted(source_sets["train"] & source_sets["val"]),
            "train_test": sorted(source_sets["train"] & source_sets["test"]),
            "val_test": sorted(source_sets["val"] & source_sets["test"]),
        }
        scene_overlaps = {
            "train_val": sorted(scene_sets["train"] & scene_sets["val"]),
            "train_test": sorted(scene_sets["train"] & scene_sets["test"]),
            "val_test": sorted(scene_sets["val"] & scene_sets["test"]),
        }
        leakage_passed = (
            not any(source_overlaps.values())
            and not any(scene_overlaps.values())
        )
        blockers: list[str] = []
        if not deduplicated:
            blockers.append("no_quality_passing_candidates")
        if len(source_groups) < minimum_unique_sources:
            blockers.append("insufficient_unique_sources")
        elif len(scene_groups) < minimum_unique_sources:
            blockers.append("insufficient_independent_visual_scene_groups")
        for split in CURATION_SPLITS:
            if not assigned[split]:
                blockers.append(f"empty_{split}_split")
        if not privacy_review_confirmed:
            blockers.append("privacy_review_pending")
        if not label_qa_confirmed:
            blockers.append("label_qa_pending")
        if machine_only_selected_count:
            blockers.append("machine_labels_require_human_approval")
        if invalid_package_count:
            blockers.append("invalid_feedback_packages_present")
        if inventory_truncated:
            blockers.append("feedback_inventory_truncated")
        if truncated_scene_fingerprint_count:
            blockers.append("scene_fingerprint_inventory_truncated")
        if any(source_overlaps.values()):
            blockers.append("source_group_leakage_detected")
        if any(scene_overlaps.values()):
            blockers.append("visual_scene_group_leakage_detected")
        raw_scene_links = scene_clustering["links"]
        if not isinstance(raw_scene_links, list):
            raise RuntimeError("scene clustering did not return links")
        multi_source_scene_group_count = sum(
            int(group["source_count"]) > 1 for group in scene_groups
        )
        curation_id = validate_run_name(
            self._record_id_factory("feedback-curation")
        )
        payload: dict[str, object] = {
            "schema_version": "urbanvision-feedback-curation-v2.1.0",
            "curation_id": curation_id,
            "created_at_utc": datetime.now(UTC).isoformat(),
            "local_only": True,
            "status": (
                "not_training_ready"
                if blockers
                else "candidate_plan_requires_training_approval"
            ),
            "training_authorized": False,
            "configuration": {
                "seed": seed,
                "ratios": ratios,
                "minimum_unique_sources": minimum_unique_sources,
                "max_scene_hamming_distance": max_scene_hamming_distance,
                "privacy_review_confirmed": privacy_review_confirmed,
                "label_qa_confirmed": label_qa_confirmed,
                "scope": (
                    {
                        "kind": "explicit_autopilot_batch",
                        "run_ids": safe_included_run_ids,
                    }
                    if safe_included_run_ids is not None
                    else {"kind": "all_local_feedback"}
                ),
            },
            "inventory": {
                "digest_sha256": inventory_digest,
                "available_package_count": len(packages),
                "examined_package_count": len(selected_packages),
                "invalid_package_count": invalid_package_count,
                "truncated": inventory_truncated,
                "manifests": inventory_refs,
            },
            "selection": {
                "candidate_count_before_deduplication": len(candidates),
                "selected_item_count": len(deduplicated),
                "unique_source_count": len(source_groups),
                "visual_scene_group_count": len(scene_groups),
                "review_authority_counts": review_authority_counts,
                "machine_only_selected_count": (
                    machine_only_selected_count
                ),
                "exclusion_counts": exclusion_counts,
                "duplicate_policy": (
                    "Retain the highest-priority deterministic representative "
                    "for each equal 64-bit difference fingerprint; original ZIP "
                    "packages remain unchanged"
                ),
            },
            "visual_scene_clustering": {
                "algorithm": (
                    "deterministic single-linkage union-find over 64-bit "
                    "source-ROI difference hashes"
                ),
                "max_hamming_distance": max_scene_hamming_distance,
                "fingerprints_per_source_limit": (
                    MAX_SCENE_FINGERPRINTS_PER_SOURCE
                ),
                "truncated_fingerprint_count": (
                    truncated_scene_fingerprint_count
                ),
                "truncated_source_count": truncated_scene_source_count,
                "scene_group_count": len(scene_groups),
                "multi_source_scene_group_count": (
                    multi_source_scene_group_count
                ),
                "near_duplicate_link_count": len(raw_scene_links),
                "near_duplicate_links": raw_scene_links,
                "groups": scene_groups,
                "interpretation": (
                    "A conservative visual-similarity firewall. A link keeps "
                    "sources in one split but is not proof that files are "
                    "identical or depict the same physical location"
                ),
            },
            "splits": split_payloads,
            "leakage_audit": {
                "group_keys": [
                    "source_sha256",
                    "visual_scene_group_id",
                ],
                "passed": leakage_passed,
                "source_overlaps": source_overlaps,
                "visual_scene_group_overlaps": scene_overlaps,
                "interpretation": (
                    "Every exact source and every conservatively linked visual "
                    "scene group is assigned to exactly one split. Perceptual "
                    "similarity reduces near-duplicate leakage but cannot prove "
                    "physical-location identity"
                ),
            },
            "readiness": {
                "blockers": blockers,
                "requires_separate_training_approval": True,
            },
            "claim_boundary": (
                "This immutable JSON is a candidate curation plan, not a "
                "materialized dataset, privacy clearance, label certification, "
                "training authorization, model result, or field-safety evidence"
            ),
        }
        path = self.paths.metrology / "curations" / f"{curation_id}.json"
        with self._write_lock:
            self._write_json_exclusive(path, payload)
        return {
            "local_only": True,
            "curation": payload,
            "curation_url": (
                f"/api/metrology/feedback-curations/{curation_id}.json"
            ),
        }

    def create_feedback_snapshot_preflight(
        self,
        curation_id: str,
    ) -> dict[str, object]:
        safe_curation_id = validate_run_name(curation_id)
        curation_path = self.feedback_curation_path(safe_curation_id)
        try:
            curation_bytes = curation_path.read_bytes()
            curation = json.loads(curation_bytes)
        except (OSError, json.JSONDecodeError) as error:
            raise _input_error(
                f"curation {safe_curation_id} cannot be read"
            ) from error
        if not isinstance(curation, dict):
            raise _input_error(
                f"curation {safe_curation_id} is not an object"
            )
        blockers: list[str] = []
        findings: list[dict[str, str]] = []
        truncated_finding_count = 0

        def add_blocker(code: str) -> None:
            if code not in blockers:
                blockers.append(code)

        def add_finding(
            code: str,
            *,
            run_id: str | None = None,
            hotspot_id: str | None = None,
        ) -> None:
            nonlocal truncated_finding_count
            if len(findings) >= MAX_FEEDBACK_SNAPSHOT_FINDINGS:
                truncated_finding_count += 1
                return
            finding = {"code": code}
            if run_id is not None:
                finding["run_id"] = run_id
            if hotspot_id is not None:
                finding["hotspot_id"] = hotspot_id
            findings.append(finding)

        if curation.get("schema_version") not in {
            "urbanvision-feedback-curation-v2.0.0",
            "urbanvision-feedback-curation-v2.1.0",
        }:
            add_blocker("unsupported_curation_schema")
        readiness = curation.get("readiness")
        upstream_blockers = (
            readiness.get("blockers")
            if isinstance(readiness, dict)
            else None
        )
        if (
            curation.get("status")
            != "candidate_plan_requires_training_approval"
            or not isinstance(upstream_blockers, list)
            or upstream_blockers
        ):
            add_blocker("upstream_curation_not_ready")
        current_packages, current_invalid_package_count = (
            self._feedback_packages()
        )
        current_packages_by_run = {
            str(package["run_id"]): package
            for package in current_packages
        }
        if current_invalid_package_count:
            add_blocker("invalid_feedback_packages_present")
        inventory = curation.get("inventory")
        inventory_refs = (
            inventory.get("manifests")
            if isinstance(inventory, dict)
            else None
        )
        expected_manifest_by_run: dict[str, str] = {}
        inventory_matches = True
        if not isinstance(inventory_refs, list):
            inventory_matches = False
            add_blocker("curation_inventory_invalid")
        else:
            for reference in inventory_refs:
                if not isinstance(reference, dict):
                    inventory_matches = False
                    continue
                run_id = reference.get("run_id")
                manifest_sha256 = reference.get("manifest_sha256")
                if (
                    not isinstance(run_id, str)
                    or not _is_hex_digest(manifest_sha256, 64)
                ):
                    inventory_matches = False
                    continue
                try:
                    safe_run_id = validate_run_name(run_id)
                except ProjectError:
                    inventory_matches = False
                    continue
                expected_manifest_by_run[safe_run_id] = str(
                    manifest_sha256
                )
                current = current_packages_by_run.get(safe_run_id)
                if (
                    current is None
                    or current.get("manifest_sha256")
                    != manifest_sha256
                ):
                    inventory_matches = False
                    add_finding(
                        "manifest_missing_or_changed",
                        run_id=safe_run_id,
                    )
        if not inventory_matches:
            add_blocker("feedback_inventory_changed")
        splits = curation.get("splits")
        if not isinstance(splits, dict):
            raise _input_error(
                f"curation {safe_curation_id} has no split payload"
            )
        requested_items: list[tuple[str, dict[str, object]]] = []
        for split in CURATION_SPLITS:
            split_payload = splits.get(split)
            split_items = (
                split_payload.get("items")
                if isinstance(split_payload, dict)
                else None
            )
            if not isinstance(split_items, list):
                add_blocker(f"invalid_{split}_split")
                continue
            requested_items.extend(
                (split, item)
                for item in split_items
                if isinstance(item, dict)
            )
            if any(not isinstance(item, dict) for item in split_items):
                add_blocker("invalid_training_pairs")
        expected_pair_count = len(requested_items)
        if expected_pair_count > MAX_FEEDBACK_SNAPSHOT_ITEMS:
            add_blocker("snapshot_item_limit_exceeded")
            requested_items = requested_items[
                :MAX_FEEDBACK_SNAPSHOT_ITEMS
            ]
        requested_items.sort(
            key=lambda entry: (
                CURATION_SPLITS.index(entry[0]),
                str(entry[1].get("run_id") or ""),
                (
                    int(entry[1]["rank"])
                    if isinstance(entry[1].get("rank"), int)
                    and not isinstance(entry[1].get("rank"), bool)
                    else 0
                ),
                str(entry[1].get("hotspot_id") or ""),
            )
        )
        verified_pairs: list[dict[str, object]] = []
        total_member_bytes = 0
        read_budget_exceeded = False
        with ExitStack() as archive_stack:
            archives: dict[str, zipfile.ZipFile] = {}
            for split, item in requested_items:
                if read_budget_exceeded:
                    break
                run_id = item.get("run_id")
                hotspot_id = item.get("hotspot_id")
                rank = item.get("rank")
                if (
                    not isinstance(run_id, str)
                    or not isinstance(hotspot_id, str)
                    or isinstance(rank, bool)
                    or not isinstance(rank, int)
                ):
                    add_blocker("invalid_training_pairs")
                    add_finding("invalid_pair_identity")
                    continue
                try:
                    safe_run_id = validate_run_name(run_id)
                    safe_hotspot_id = validate_run_name(hotspot_id)
                except ProjectError:
                    add_blocker("invalid_training_pairs")
                    add_finding("invalid_pair_identity")
                    continue
                package = current_packages_by_run.get(safe_run_id)
                expected_manifest = expected_manifest_by_run.get(
                    safe_run_id
                )
                if (
                    package is None
                    or expected_manifest is None
                    or item.get("manifest_sha256") != expected_manifest
                    or package.get("manifest_sha256") != expected_manifest
                ):
                    add_blocker("feedback_inventory_changed")
                    add_finding(
                        "pair_manifest_binding_failed",
                        run_id=safe_run_id,
                        hotspot_id=safe_hotspot_id,
                    )
                    continue
                package_items = package.get("items")
                current_item = next(
                    (
                        candidate
                        for candidate in package_items
                        if isinstance(candidate, dict)
                        and candidate.get("hotspot_id")
                        == safe_hotspot_id
                        and candidate.get("rank") == rank
                    ),
                    None,
                ) if isinstance(package_items, list) else None
                files = _curation_file_evidence(item.get("files"))
                current_files = (
                    _curation_file_evidence(current_item.get("files"))
                    if isinstance(current_item, dict)
                    else None
                )
                source_sha256 = item.get("source_sha256")
                visual_scene_group_id = item.get(
                    "visual_scene_group_id"
                )
                review_authority = item.get(
                    "review_authority",
                    "legacy_unknown",
                )
                current_review_authority = (
                    current_item.get(
                        "decision_authority",
                        package.get(
                            "review_authority",
                            "legacy_unknown",
                        ),
                    )
                    if isinstance(current_item, dict)
                    else None
                )
                if (
                    files is None
                    or current_files != files
                    or package.get("source_sha256") != source_sha256
                    or not _is_hex_digest(source_sha256, 64)
                    or not isinstance(visual_scene_group_id, str)
                    or not visual_scene_group_id.startswith(
                        "visual-scene-"
                    )
                    or review_authority not in {
                        *REVIEW_AUTHORITIES.values(),
                        "legacy_unknown",
                    }
                    or review_authority != current_review_authority
                ):
                    add_blocker("invalid_training_pairs")
                    add_finding(
                        "pair_manifest_content_mismatch",
                        run_id=safe_run_id,
                        hotspot_id=safe_hotspot_id,
                    )
                    continue
                archive = archives.get(safe_run_id)
                if archive is None:
                    package_path = (
                        self.paths.metrology
                        / safe_run_id
                        / ACTIVE_LEARNING_FEEDBACK_ARTIFACT
                    )
                    try:
                        archive = archive_stack.enter_context(
                            zipfile.ZipFile(package_path)
                        )
                    except (OSError, zipfile.BadZipFile):
                        add_blocker("invalid_training_pairs")
                        add_finding(
                            "feedback_archive_unreadable",
                            run_id=safe_run_id,
                            hotspot_id=safe_hotspot_id,
                        )
                        continue
                    archives[safe_run_id] = archive
                member_infos: dict[str, zipfile.ZipInfo] = {}
                invalid_member = False
                for role in ("source_roi", "final_mask"):
                    member_path = files[role]["path"]
                    try:
                        member_info = archive.getinfo(member_path)
                    except KeyError:
                        invalid_member = True
                        add_finding(
                            f"{role}_member_missing",
                            run_id=safe_run_id,
                            hotspot_id=safe_hotspot_id,
                        )
                        continue
                    if (
                        member_info.file_size <= 0
                        or member_info.file_size
                        > MAX_FEEDBACK_SNAPSHOT_MEMBER_BYTES
                    ):
                        invalid_member = True
                        add_finding(
                            f"{role}_member_size_invalid",
                            run_id=safe_run_id,
                            hotspot_id=safe_hotspot_id,
                        )
                    member_infos[role] = member_info
                if invalid_member:
                    add_blocker("invalid_training_pairs")
                    continue
                pair_bytes = sum(
                    info.file_size for info in member_infos.values()
                )
                if (
                    total_member_bytes + pair_bytes
                    > MAX_FEEDBACK_SNAPSHOT_TOTAL_BYTES
                ):
                    read_budget_exceeded = True
                    add_blocker("snapshot_read_budget_exceeded")
                    continue
                total_member_bytes += pair_bytes
                contents: dict[str, bytes] = {}
                for role, info in member_infos.items():
                    try:
                        content = archive.read(info)
                    except (OSError, RuntimeError, zipfile.BadZipFile):
                        invalid_member = True
                        add_finding(
                            f"{role}_member_unreadable",
                            run_id=safe_run_id,
                            hotspot_id=safe_hotspot_id,
                        )
                        continue
                    if _sha256(content) != files[role]["sha256"]:
                        invalid_member = True
                        add_finding(
                            f"{role}_digest_mismatch",
                            run_id=safe_run_id,
                            hotspot_id=safe_hotspot_id,
                        )
                    contents[role] = content
                if invalid_member:
                    add_blocker("invalid_training_pairs")
                    continue
                source_image = cv2.imdecode(
                    np.frombuffer(contents["source_roi"], dtype=np.uint8),
                    cv2.IMREAD_UNCHANGED,
                )
                final_mask = cv2.imdecode(
                    np.frombuffer(contents["final_mask"], dtype=np.uint8),
                    cv2.IMREAD_GRAYSCALE,
                )
                if (
                    source_image is None
                    or source_image.ndim not in {2, 3}
                    or final_mask is None
                    or final_mask.ndim != 2
                    or source_image.shape[:2] != final_mask.shape
                    or final_mask.size > MAX_FEEDBACK_CROP_PIXELS
                ):
                    add_blocker("invalid_training_pairs")
                    add_finding(
                        "source_mask_geometry_invalid",
                        run_id=safe_run_id,
                        hotspot_id=safe_hotspot_id,
                    )
                    continue
                mask_values = {
                    int(value) for value in np.unique(final_mask)
                }
                if not mask_values.issubset({0, 255}):
                    add_blocker("invalid_training_pairs")
                    add_finding(
                        "final_mask_not_binary",
                        run_id=safe_run_id,
                        hotspot_id=safe_hotspot_id,
                    )
                    continue
                foreground_pixels = int(
                    np.count_nonzero(final_mask == 255)
                )
                pair = {
                    "split": split,
                    "run_id": safe_run_id,
                    "hotspot_id": safe_hotspot_id,
                    "rank": rank,
                    "source_sha256": source_sha256,
                    "visual_scene_group_id": visual_scene_group_id,
                    "disposition": item.get("disposition"),
                    "review_authority": review_authority,
                    "width": int(final_mask.shape[1]),
                    "height": int(final_mask.shape[0]),
                    "foreground_pixels": foreground_pixels,
                    "foreground_ratio": round(
                        foreground_pixels / final_mask.size,
                        8,
                    ),
                    "source_roi": {
                        "feedback_url": package["feedback_url"],
                        **files["source_roi"],
                    },
                    "final_mask": {
                        "feedback_url": package["feedback_url"],
                        **files["final_mask"],
                    },
                }
                verified_pairs.append(pair)
        if len(verified_pairs) != expected_pair_count:
            add_blocker("incomplete_snapshot_pairs")
        split_sources = {split: set() for split in CURATION_SPLITS}
        split_scenes = {split: set() for split in CURATION_SPLITS}
        source_content_splits: dict[str, set[str]] = {}
        for pair in verified_pairs:
            split = str(pair["split"])
            split_sources[split].add(str(pair["source_sha256"]))
            split_scenes[split].add(
                str(pair["visual_scene_group_id"])
            )
            source_roi = pair["source_roi"]
            if isinstance(source_roi, dict):
                digest = source_roi.get("sha256")
                if isinstance(digest, str):
                    source_content_splits.setdefault(
                        digest,
                        set(),
                    ).add(split)
        source_overlaps = {
            "train_val": sorted(
                split_sources["train"] & split_sources["val"]
            ),
            "train_test": sorted(
                split_sources["train"] & split_sources["test"]
            ),
            "val_test": sorted(
                split_sources["val"] & split_sources["test"]
            ),
        }
        scene_overlaps = {
            "train_val": sorted(
                split_scenes["train"] & split_scenes["val"]
            ),
            "train_test": sorted(
                split_scenes["train"] & split_scenes["test"]
            ),
            "val_test": sorted(
                split_scenes["val"] & split_scenes["test"]
            ),
        }
        source_content_overlaps = [
            {
                "source_roi_sha256": digest,
                "splits": sorted(split_names),
            }
            for digest, split_names in sorted(
                source_content_splits.items()
            )
            if len(split_names) > 1
        ]
        if any(source_overlaps.values()):
            add_blocker("source_group_leakage_detected")
        if any(scene_overlaps.values()):
            add_blocker("visual_scene_group_leakage_detected")
        if source_content_overlaps:
            add_blocker("cross_split_source_content_duplicate")
        split_payloads: dict[str, dict[str, object]] = {}
        for split in CURATION_SPLITS:
            pairs = [
                pair
                for pair in verified_pairs
                if pair["split"] == split
            ]
            total_pixels = sum(
                int(pair["width"]) * int(pair["height"])
                for pair in pairs
            )
            foreground_pixels = sum(
                int(pair["foreground_pixels"]) for pair in pairs
            )
            split_payloads[split] = {
                "pair_count": len(pairs),
                "unique_source_count": len(split_sources[split]),
                "visual_scene_group_count": len(split_scenes[split]),
                "empty_mask_count": sum(
                    int(pair["foreground_pixels"]) == 0
                    for pair in pairs
                ),
                "total_pixels": total_pixels,
                "foreground_pixels": foreground_pixels,
                "foreground_ratio": (
                    round(foreground_pixels / total_pixels, 8)
                    if total_pixels
                    else None
                ),
                "disposition_counts": {
                    disposition: sum(
                        pair["disposition"] == disposition
                        for pair in pairs
                    )
                    for disposition in sorted(HOTSPOT_DISPOSITIONS)
                },
                "review_authority_counts": {
                    authority: sum(
                        pair["review_authority"] == authority
                        for pair in pairs
                    )
                    for authority in (
                        "human_operator",
                        "machine_heuristic",
                        "machine_unreviewed",
                        "legacy_unknown",
                    )
                },
                "pairs": pairs,
            }
        merkle_records = [
            {
                "split": pair["split"],
                "run_id": pair["run_id"],
                "hotspot_id": pair["hotspot_id"],
                "source_sha256": pair["source_sha256"],
                "visual_scene_group_id": pair[
                    "visual_scene_group_id"
                ],
                "source_roi_sha256": pair["source_roi"]["sha256"],
                "final_mask_sha256": pair["final_mask"]["sha256"],
                "review_authority": pair["review_authority"],
            }
            for pair in verified_pairs
        ]
        snapshot_id = validate_run_name(
            self._record_id_factory("feedback-snapshot")
        )
        payload: dict[str, object] = {
            "schema_version": (
                "urbanvision-feedback-snapshot-preflight-v1.0.0"
            ),
            "snapshot_id": snapshot_id,
            "created_at_utc": datetime.now(UTC).isoformat(),
            "local_only": True,
            "status": (
                "not_snapshot_ready"
                if blockers
                else (
                    "verified_candidate_snapshot_requires_"
                    "training_approval"
                )
            ),
            "training_authorized": False,
            "curation_binding": {
                "curation_id": safe_curation_id,
                "curation_sha256": _sha256(curation_bytes),
                "curation_url": (
                    f"/api/metrology/feedback-curations/"
                    f"{safe_curation_id}.json"
                ),
            },
            "integrity": {
                "inventory_matches": inventory_matches,
                "current_invalid_package_count": (
                    current_invalid_package_count
                ),
                "expected_pair_count": expected_pair_count,
                "verified_pair_count": len(verified_pairs),
                "invalid_pair_count": (
                    expected_pair_count - len(verified_pairs)
                ),
                "member_bytes_read": total_member_bytes,
                "source_overlaps": source_overlaps,
                "visual_scene_group_overlaps": scene_overlaps,
                "source_roi_content_overlaps": (
                    source_content_overlaps
                ),
                "review_authority_counts": {
                    authority: sum(
                        pair["review_authority"] == authority
                        for pair in verified_pairs
                    )
                    for authority in (
                        "human_operator",
                        "machine_heuristic",
                        "machine_unreviewed",
                        "legacy_unknown",
                    )
                },
                "findings": findings,
                "truncated_finding_count": truncated_finding_count,
            },
            "merkle": {
                "root_sha256": _canonical_merkle_root(
                    merkle_records
                ),
                "leaf_count": len(merkle_records),
                "scheme": (
                    "sorted canonical JSON leaves; SHA-256 0x00 leaf "
                    "domain; duplicated odd node; SHA-256 0x01 parent "
                    "domain"
                ),
                "leaf_fields": [
                    "split",
                    "run_id",
                    "hotspot_id",
                    "source_sha256",
                    "visual_scene_group_id",
                    "source_roi_sha256",
                    "final_mask_sha256",
                    "review_authority",
                ],
            },
            "splits": split_payloads,
            "readiness": {
                "blockers": blockers,
                "requires_separate_training_approval": True,
            },
            "claim_boundary": (
                "This preflight verifies referenced bytes, image-mask "
                "structure, split isolation, and a content-addressed root. "
                "It is not extracted training data, privacy clearance, "
                "label correctness, training authorization, or model "
                "performance evidence"
            ),
        }
        path = (
            self.paths.metrology
            / "snapshots"
            / f"{snapshot_id}.json"
        )
        with self._write_lock:
            self._write_json_exclusive(path, payload)
        return {
            "local_only": True,
            "snapshot": payload,
            "snapshot_url": (
                f"/api/metrology/feedback-snapshots/{snapshot_id}.json"
            ),
        }

    def finalize_autopilot_batch(
        self,
        *,
        run_ids: str,
        seed: int = 42,
        minimum_unique_sources: int = 10,
        max_scene_hamming_distance: int = 4,
    ) -> dict[str, object]:
        safe_run_ids = _autopilot_batch_run_ids(run_ids)
        run_records: list[dict[str, object]] = []
        feedback_run_ids: list[str] = []
        for run_id in safe_run_ids:
            measurement_bytes, measurement = self._measurement_bytes(run_id)
            run = measurement.get("run")
            input_evidence = (
                run.get("input_evidence")
                if isinstance(run, dict)
                else None
            )
            if (
                not isinstance(input_evidence, dict)
                or input_evidence.get("review_state")
                != "machine_reviewed_candidate"
                or input_evidence.get("review_authority")
                != "machine_heuristic"
            ):
                raise _input_error(
                    f"autopilot batch run {run_id} is not a "
                    "machine-reviewed candidate"
                )
            source = input_evidence.get("source")
            source_sha256 = (
                source.get("sha256")
                if isinstance(source, dict)
                else None
            )
            if not _is_hex_digest(source_sha256, 64):
                raise _input_error(
                    f"autopilot batch run {run_id} has invalid source evidence"
                )
            feedback_path = (
                self.paths.metrology
                / run_id
                / ACTIVE_LEARNING_FEEDBACK_ARTIFACT
            )
            feedback_exported = feedback_path.is_file()
            if feedback_exported:
                feedback_run_ids.append(run_id)
            run_records.append(
                {
                    "run_id": run_id,
                    "measurement_sha256": _sha256(measurement_bytes),
                    "source_sha256": source_sha256,
                    "feedback_exported": feedback_exported,
                }
            )

        curation_result = self.create_feedback_curation(
            seed=seed,
            minimum_unique_sources=minimum_unique_sources,
            max_scene_hamming_distance=max_scene_hamming_distance,
            privacy_review_confirmed=False,
            label_qa_confirmed=False,
            included_run_ids=feedback_run_ids,
        )
        curation = curation_result["curation"]
        if not isinstance(curation, dict):
            raise RuntimeError("autopilot curation did not return a record")
        curation_id = curation.get("curation_id")
        if not isinstance(curation_id, str):
            raise RuntimeError("autopilot curation has no ID")
        snapshot_result = self.create_feedback_snapshot_preflight(
            curation_id
        )
        snapshot = snapshot_result["snapshot"]
        if not isinstance(snapshot, dict):
            raise RuntimeError("autopilot snapshot did not return a record")
        batch_id = validate_run_name(
            self._record_id_factory("autopilot-batch")
        )
        snapshot_blockers = snapshot.get("readiness")
        blocker_codes = (
            snapshot_blockers.get("blockers")
            if isinstance(snapshot_blockers, dict)
            else []
        )
        payload: dict[str, object] = {
            "schema_version": "urbanvision-autopilot-batch-v1.0.0",
            "batch_id": batch_id,
            "created_at_utc": datetime.now(UTC).isoformat(),
            "local_only": True,
            "status": (
                "completed_with_governance_blockers"
                if blocker_codes
                else "completed_requires_training_approval"
            ),
            "training_authorized": False,
            "run_count": len(run_records),
            "feedback_run_count": len(feedback_run_ids),
            "runs": run_records,
            "governance": {
                "curation_id": curation_id,
                "curation_url": curation_result["curation_url"],
                "snapshot_id": snapshot.get("snapshot_id"),
                "snapshot_url": snapshot_result["snapshot_url"],
                "blockers": blocker_codes,
            },
            "configuration": {
                "seed": seed,
                "minimum_unique_sources": minimum_unique_sources,
                "max_scene_hamming_distance": (
                    max_scene_hamming_distance
                ),
                "execution": (
                    "browser serial queue; per-image detection and proposal "
                    "may run concurrently"
                ),
            },
            "claim_boundary": (
                "This record proves which completed machine-candidate runs "
                "entered one bounded governance pass. It is not privacy "
                "clearance, label approval, training authorization, physical "
                "calibration, or a road-safety conclusion"
            ),
        }
        path = (
            self.paths.metrology
            / "autopilot-batches"
            / f"{batch_id}.json"
        )
        with self._write_lock:
            self._write_json_exclusive(path, payload)
        return {
            "local_only": True,
            "batch": payload,
            "batch_url": (
                f"/api/metrology/autopilot-batches/{batch_id}.json"
            ),
            "curation": curation,
            "curation_url": curation_result["curation_url"],
            "snapshot": snapshot,
            "snapshot_url": snapshot_result["snapshot_url"],
        }

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

    def feedback_curation_path(self, curation_id: str) -> Path:
        safe_id = validate_run_name(curation_id)
        path = self.paths.metrology / "curations" / f"{safe_id}.json"
        if not path.is_file():
            raise ProjectError(
                "E201",
                "反馈数据策划记录不存在",
                "The feedback-curation record does not exist",
                "检查策划编号，或重新生成防泄漏策划",
                "Check the curation ID or build another leakage-safe plan",
                safe_id,
            )
        return path

    def feedback_snapshot_path(self, snapshot_id: str) -> Path:
        safe_id = validate_run_name(snapshot_id)
        path = self.paths.metrology / "snapshots" / f"{safe_id}.json"
        if not path.is_file():
            raise ProjectError(
                "E201",
                "反馈数据快照预检不存在",
                "The feedback-snapshot preflight does not exist",
                "检查快照编号，或重新运行数据快照预检",
                "Check the snapshot ID or run snapshot preflight again",
                safe_id,
            )
        return path

    def autopilot_batch_path(self, batch_id: str) -> Path:
        safe_id = validate_run_name(batch_id)
        path = (
            self.paths.metrology
            / "autopilot-batches"
            / f"{safe_id}.json"
        )
        if not path.is_file():
            raise ProjectError(
                "E201",
                "自动驾驶批次记录不存在",
                "The autopilot batch record does not exist",
                "检查批次编号，或重新运行批量自动巡检",
                "Check the batch ID or rerun batch autopilot",
                safe_id,
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
