from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from urbanvision_risk.detection.config import validate_run_name
from urbanvision_risk.errors import ProjectError, report_error
from urbanvision_risk.metrology.calibration import PlanarCalibration, load_calibration
from urbanvision_risk.metrology.engine import MetrologyAnalysis, analyze_crack_mask
from urbanvision_risk.metrology.skeleton import build_skeleton_graph
from urbanvision_risk.paths import ProjectPaths, get_paths


def _output_exists_error(path: Path) -> ProjectError:
    return ProjectError(
        "E204",
        "量测输出目录已经存在",
        "The metrology output directory already exists",
        "保留现有结果并使用新的 --output-name",
        "Keep the existing result and use a new --output-name",
        str(path),
    )


def _read_error(path: Path, kind_zh: str, kind_en: str) -> ProjectError:
    return ProjectError(
        "E503",
        f"{kind_zh}无法读取",
        f"The {kind_en} cannot be read",
        "检查文件路径和图像格式",
        "Check the file path and image format",
        str(path),
    )


def _write_error(path: Path) -> ProjectError:
    return ProjectError(
        "E504",
        "量测结果写入失败；不完整目录已保留",
        "Metrology output failed; the incomplete directory was preserved",
        "检查磁盘空间和权限，然后使用新的 --output-name",
        "Check disk space and permissions, then use a new --output-name",
        str(path),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
    except OSError as error:
        raise _read_error(path, "输入文件", "input file") from error
    return digest.hexdigest()


def _load_mask(path: Path) -> NDArray[np.uint8]:
    if not path.is_file():
        raise _read_error(path, "裂缝掩膜", "crack mask")
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise _read_error(path, "裂缝掩膜", "crack mask")
    return image


def _load_source_image(
    path: Path | None,
    expected_shape: tuple[int, int],
) -> NDArray[np.uint8] | None:
    if path is None:
        return None
    if not path.is_file():
        raise _read_error(path, "道路原图", "source road image")
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise _read_error(path, "道路原图", "source road image")
    if image.shape[:2] != expected_shape:
        raise ProjectError(
            "E503",
            "道路原图与掩膜尺寸不一致",
            "The source road image and crack mask have different dimensions",
            "导出与原图同宽同高的二值掩膜",
            "Export a binary mask with the same width and height as the source image",
            f"source={image.shape[:2]}, mask={expected_shape}",
        )
    return image


def _json_text(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _write_image(path: Path, image: NDArray[np.generic]) -> None:
    if not cv2.imwrite(str(path), image):
        raise OSError(f"cv2.imwrite failed: {path}")


def _heatmap(width_map: NDArray[np.float32], mask: NDArray[np.bool_]) -> NDArray[np.uint8]:
    positive = width_map[mask]
    scale_max = max(float(np.quantile(positive, 0.99)), 1.0) if positive.size else 1.0
    normalized = np.clip(width_map / scale_max * 255.0, 0, 255).astype(np.uint8)
    color = cv2.applyColorMap(normalized, cv2.COLORMAP_TURBO)
    color[~mask] = 0
    return color


def _base_image(
    mask: NDArray[np.bool_],
    source_image: NDArray[np.uint8] | None,
) -> NDArray[np.uint8]:
    if source_image is not None:
        return source_image.copy()
    background = np.full((*mask.shape, 3), 34, dtype=np.uint8)
    background[mask] = (70, 70, 70)
    return background


def _overlay(
    *,
    mask: NDArray[np.bool_],
    skeleton: NDArray[np.bool_],
    source_image: NDArray[np.uint8] | None,
    calibration: PlanarCalibration | None,
) -> NDArray[np.uint8]:
    canvas = _base_image(mask, source_image)
    tint = canvas.copy()
    tint[mask] = (32, 116, 245)
    canvas = cv2.addWeighted(canvas, 0.65, tint, 0.35, 0.0)
    canvas[skeleton] = (80, 255, 80)

    graph = build_skeleton_graph(skeleton)
    if graph.coordinates_yx.size:
        endpoint_coordinates = graph.coordinates_yx[graph.degree == 1]
        junction_coordinates = graph.coordinates_yx[graph.degree >= 3]
        for y, x in endpoint_coordinates:
            cv2.circle(canvas, (int(x), int(y)), 3, (255, 190, 20), -1, cv2.LINE_AA)
        for y, x in junction_coordinates:
            cv2.circle(canvas, (int(x), int(y)), 3, (230, 40, 230), -1, cv2.LINE_AA)

    if calibration is not None:
        points = np.rint(calibration.points_array()).astype(np.int32)
        cv2.polylines(canvas, [points], True, (255, 220, 50), 2, cv2.LINE_AA)
        for label, (x, y) in zip(("TL", "TR", "BR", "BL"), points, strict=True):
            cv2.circle(canvas, (int(x), int(y)), 5, (255, 220, 50), -1, cv2.LINE_AA)
            cv2.putText(
                canvas,
                label,
                (int(x) + 7, int(y) - 7),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
    return canvas


def _write_artifacts(
    *,
    output_dir: Path,
    analysis: MetrologyAnalysis,
    payload: dict[str, object],
    source_image: NDArray[np.uint8] | None,
    calibration: PlanarCalibration | None,
) -> None:
    _write_image(output_dir / "mask.png", analysis.source_mask.astype(np.uint8) * 255)
    _write_image(
        output_dir / "skeleton.png",
        analysis.source_skeleton.astype(np.uint8) * 255,
    )
    _write_image(
        output_dir / "width-heatmap.png",
        _heatmap(analysis.source_width_map, analysis.source_mask),
    )
    _write_image(
        output_dir / "overlay.jpg",
        _overlay(
            mask=analysis.source_mask,
            skeleton=analysis.source_skeleton,
            source_image=source_image,
            calibration=calibration,
        ),
    )
    if (
        calibration is not None
        and analysis.rectified_mask is not None
        and analysis.rectified_skeleton is not None
        and analysis.rectified_width_map is not None
    ):
        rectified_source = None
        if source_image is not None:
            rectified_source = cv2.warpPerspective(
                source_image,
                calibration.raster_homography(),
                calibration.rectified_size(),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(0, 0, 0),
            )
        _write_image(
            output_dir / "rectified-mask.png",
            analysis.rectified_mask.astype(np.uint8) * 255,
        )
        _write_image(
            output_dir / "rectified-skeleton.png",
            analysis.rectified_skeleton.astype(np.uint8) * 255,
        )
        _write_image(
            output_dir / "rectified-width-heatmap.png",
            _heatmap(analysis.rectified_width_map, analysis.rectified_mask),
        )
        _write_image(
            output_dir / "rectified-overlay.jpg",
            _overlay(
                mask=analysis.rectified_mask,
                skeleton=analysis.rectified_skeleton,
                source_image=rectified_source,
                calibration=None,
            ),
        )
    (output_dir / "measurement.json").write_text(
        _json_text(payload),
        encoding="utf-8",
    )


def create_metrology_run(
    *,
    mask: NDArray[np.generic],
    output_name: str,
    calibration: PlanarCalibration | None = None,
    source_image: NDArray[np.uint8] | None = None,
    input_evidence: dict[str, object] | None = None,
    uncertainty_samples: int = 64,
    seed: int = 42,
    segmentation_radius_pixels: int = 1,
    paths: ProjectPaths | None = None,
) -> Path:
    validate_run_name(output_name)
    active_paths = paths or get_paths()
    analysis = analyze_crack_mask(
        mask,
        calibration=calibration,
        uncertainty_samples=uncertainty_samples,
        seed=seed,
        segmentation_radius_pixels=segmentation_radius_pixels,
    )
    if source_image is not None and source_image.shape[:2] != analysis.source_mask.shape:
        raise ProjectError(
            "E503",
            "道路原图与掩膜尺寸不一致",
            "The source road image and crack mask have different dimensions",
            "提供相同宽高的原图与掩膜",
            "Provide source and mask images with identical dimensions",
            f"source={source_image.shape[:2]}, mask={analysis.source_mask.shape}",
        )
    output_dir = active_paths.metrology / output_name
    if output_dir.exists():
        raise _output_exists_error(output_dir)

    payload = dict(analysis.payload)
    payload["run"] = {
        "output_name": output_name,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "implementation_version": "3.0.0",
        "input_evidence": input_evidence
        or {
            "kind": "in_memory",
            "privacy": "No source path was recorded",
        },
    }
    try:
        output_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise _output_exists_error(output_dir) from error
    except OSError as error:
        raise _write_error(output_dir) from error
    try:
        _write_artifacts(
            output_dir=output_dir,
            analysis=analysis,
            payload=payload,
            source_image=source_image,
            calibration=calibration,
        )
    except OSError as error:
        raise _write_error(output_dir) from error
    return output_dir


def measure_files(
    *,
    mask_path: Path,
    output_name: str,
    source_image_path: Path | None = None,
    calibration_path: Path | None = None,
    uncertainty_samples: int = 64,
    seed: int = 42,
    segmentation_radius_pixels: int = 1,
    paths: ProjectPaths | None = None,
) -> Path:
    mask = _load_mask(mask_path)
    source_image = _load_source_image(source_image_path, mask.shape)
    calibration = load_calibration(calibration_path) if calibration_path else None
    input_evidence: dict[str, object] = {
        "mask": {
            "filename": mask_path.name,
            "sha256": _sha256(mask_path),
        },
        "source_image": None,
        "calibration": None,
        "privacy": "Filenames and SHA-256 digests only; absolute input paths are omitted",
    }
    if source_image_path is not None:
        input_evidence["source_image"] = {
            "filename": source_image_path.name,
            "sha256": _sha256(source_image_path),
        }
    if calibration_path is not None:
        input_evidence["calibration"] = {
            "filename": calibration_path.name,
            "sha256": _sha256(calibration_path),
        }
    return create_metrology_run(
        mask=mask,
        output_name=output_name,
        calibration=calibration,
        source_image=source_image,
        input_evidence=input_evidence,
        uncertainty_samples=uncertainty_samples,
        seed=seed,
        segmentation_radius_pixels=segmentation_radius_pixels,
        paths=paths,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure a calibrated crack mask / 量测已标定裂缝掩膜"
    )
    parser.add_argument("--mask", type=Path, required=True)
    parser.add_argument("--source-image", type=Path)
    parser.add_argument("--calibration", type=Path)
    parser.add_argument("--output-name", default="metrology-001")
    parser.add_argument("--uncertainty-samples", type=int, default=64)
    parser.add_argument("--segmentation-radius-pixels", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    try:
        output = measure_files(
            mask_path=args.mask,
            source_image_path=args.source_image,
            calibration_path=args.calibration,
            output_name=args.output_name,
            uncertainty_samples=args.uncertainty_samples,
            segmentation_radius_pixels=args.segmentation_radius_pixels,
            seed=args.seed,
        )
        print(f"[PASS] 裂缝量测完成 / Crack metrology complete: {output}")
        return 0
    except ProjectError as error:
        return report_error(error, debug=args.debug)


if __name__ == "__main__":
    raise SystemExit(main())
