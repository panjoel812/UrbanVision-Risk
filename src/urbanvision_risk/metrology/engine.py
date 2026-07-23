from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np
from numpy.typing import NDArray

from urbanvision_risk.errors import ProjectError
from urbanvision_risk.metrology.calibration import PlanarCalibration
from urbanvision_risk.metrology.skeleton import (
    SkeletonGraph,
    build_skeleton_graph,
    summarize_skeleton,
    zhang_suen_thinning,
)


def metrology_error(context: str) -> ProjectError:
    return ProjectError(
        "E502",
        "裂缝量测输入非法或没有前景像素",
        "The crack-metrology input is invalid or contains no foreground pixels",
        "提供二维二值掩膜；白色表示裂缝，黑色表示背景",
        "Provide a 2-D binary mask with white cracks on a black background",
        context,
    )


@dataclass(frozen=True, slots=True)
class MetrologyAnalysis:
    payload: dict[str, object]
    source_mask: NDArray[np.bool_]
    source_skeleton: NDArray[np.bool_]
    source_width_map: NDArray[np.float32]
    rectified_mask: NDArray[np.bool_] | None
    rectified_skeleton: NDArray[np.bool_] | None
    rectified_width_map: NDArray[np.float32] | None


def _normalize_mask(mask: NDArray[np.generic]) -> NDArray[np.bool_]:
    array = np.asarray(mask)
    if array.ndim != 2 or array.size == 0:
        raise metrology_error(f"mask shape={array.shape!r}")
    binary = np.ascontiguousarray(array > 0)
    if not np.any(binary):
        raise metrology_error("mask foreground count=0")
    return binary


def _skeletonize(mask: NDArray[np.bool_]) -> NDArray[np.bool_]:
    padded = np.pad(mask, 1, mode="constant", constant_values=False)
    return zhang_suen_thinning(padded)[1:-1, 1:-1]


def _width_map(mask: NDArray[np.bool_]) -> NDArray[np.float32]:
    distance = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_5)
    return (2.0 * distance).astype(np.float32)


def _round(value: float) -> float:
    return round(float(value), 6)


def _width_statistics(
    width_map: NDArray[np.float32],
    skeleton: NDArray[np.bool_],
    scale: float = 1.0,
) -> dict[str, int | float | None]:
    values = width_map[skeleton].astype(np.float64) / scale
    values = values[np.isfinite(values) & (values > 0)]
    if values.size == 0:
        return {
            "sample_count": 0,
            "minimum": None,
            "p05": None,
            "median": None,
            "mean": None,
            "p95": None,
            "maximum": None,
            "standard_deviation": None,
        }
    return {
        "sample_count": int(values.size),
        "minimum": _round(np.min(values)),
        "p05": _round(np.quantile(values, 0.05)),
        "median": _round(np.median(values)),
        "mean": _round(np.mean(values)),
        "p95": _round(np.quantile(values, 0.95)),
        "maximum": _round(np.max(values)),
        "standard_deviation": _round(np.std(values)),
    }


def _pixel_geometry(
    mask: NDArray[np.bool_],
    skeleton: NDArray[np.bool_],
    graph: SkeletonGraph,
    width_map: NDArray[np.float32],
) -> dict[str, object]:
    topology = summarize_skeleton(skeleton, graph)
    return {
        "unit": "pixel",
        "area_unit": "pixel^2",
        "foreground_area": int(np.count_nonzero(mask)),
        "coverage_ratio": _round(np.mean(mask)),
        "centerline_network_length": topology["network_length_pixels"],
        "width_distribution": _width_statistics(width_map, skeleton),
    }


def _transform_network_length(
    graph: SkeletonGraph,
    homography: NDArray[np.float64],
) -> float:
    if graph.edges.size == 0:
        return 0.0
    coordinates_xy = graph.coordinates_yx[:, ::-1].astype(np.float32).reshape((-1, 1, 2))
    transformed = cv2.perspectiveTransform(coordinates_xy, homography).reshape((-1, 2))
    vectors = transformed[graph.edges[:, 0]] - transformed[graph.edges[:, 1]]
    return float(np.sum(np.linalg.norm(vectors, axis=1)))


def _metric_geometry(
    *,
    source_graph: SkeletonGraph,
    calibration: PlanarCalibration,
    rectified_mask: NDArray[np.bool_],
    rectified_skeleton: NDArray[np.bool_],
    rectified_graph: SkeletonGraph,
    rectified_width_map: NDArray[np.float32],
) -> dict[str, object]:
    unit = calibration.unit
    network_length = _transform_network_length(
        source_graph,
        calibration.metric_homography(),
    )
    topology = summarize_skeleton(rectified_skeleton, rectified_graph)
    physical_area = calibration.physical_width * calibration.physical_height
    foreground_area = float(np.mean(rectified_mask)) * physical_area
    return {
        "unit": unit,
        "area_unit": f"{unit}^2",
        "foreground_area": _round(foreground_area),
        "calibrated_plane_area": _round(physical_area),
        "coverage_ratio": _round(np.mean(rectified_mask)),
        "centerline_network_length": _round(network_length),
        "network_length_density": _round(network_length / physical_area),
        "junction_density": _round(
            float(topology["junction_cluster_count"]) / physical_area
        ),
        "width_distribution": _width_statistics(
            rectified_width_map,
            rectified_skeleton,
            calibration.pixels_per_unit,
        ),
        "rectified_principal_orientation_degrees": topology[
            "principal_orientation_degrees"
        ],
        "method": {
            "length": "homography-transformed skeleton graph",
            "width": "distance transform sampled on the rectified skeleton",
            "area": "rectified binary-mask occupancy",
        },
    }


def _interval(values: list[float]) -> dict[str, float] | None:
    finite = np.asarray([value for value in values if math.isfinite(value)], dtype=np.float64)
    if finite.size == 0:
        return None
    return {
        "minimum": _round(np.min(finite)),
        "p05": _round(np.quantile(finite, 0.05)),
        "median": _round(np.median(finite)),
        "p95": _round(np.quantile(finite, 0.95)),
        "maximum": _round(np.max(finite)),
    }


def _segmentation_variants(
    mask: NDArray[np.bool_],
    radius: int,
) -> dict[str, NDArray[np.bool_]]:
    if radius <= 0:
        return {"nominal": mask}
    size = radius * 2 + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))
    uint_mask = mask.astype(np.uint8)
    return {
        "eroded": cv2.erode(uint_mask, kernel, iterations=1) > 0,
        "nominal": mask,
        "dilated": cv2.dilate(uint_mask, kernel, iterations=1) > 0,
    }


def _calibration_samples(
    *,
    graph: SkeletonGraph,
    calibration: PlanarCalibration,
    sample_count: int,
    seed: int,
) -> tuple[list[float], int]:
    if sample_count <= 0:
        return [], 0
    generator = np.random.default_rng(seed)
    base_points = calibration.points_array()
    lengths: list[float] = []
    attempts = 0
    max_attempts = max(sample_count * 8, sample_count)
    while len(lengths) < sample_count and attempts < max_attempts:
        attempts += 1
        perturbed = base_points + generator.normal(
            loc=0.0,
            scale=calibration.point_sigma_pixels,
            size=(4, 2),
        )
        try:
            homography = calibration.metric_homography(perturbed)
        except ProjectError:
            continue
        length = _transform_network_length(graph, homography)
        if math.isfinite(length):
            lengths.append(length)
    return lengths, attempts


def _uncertainty_analysis(
    *,
    source_mask: NDArray[np.bool_],
    source_graph: SkeletonGraph,
    calibration: PlanarCalibration,
    uncertainty_samples: int,
    seed: int,
    segmentation_radius_pixels: int,
    nominal_metric: dict[str, object],
) -> dict[str, object]:
    calibration_lengths, attempts = _calibration_samples(
        graph=source_graph,
        calibration=calibration,
        sample_count=uncertainty_samples,
        seed=seed,
    )
    segmentation_lengths: dict[str, float | None] = {}
    segmentation_mean_widths: dict[str, float | None] = {}
    segmentation_p95_widths: dict[str, float | None] = {}
    for label, variant in _segmentation_variants(
        source_mask, segmentation_radius_pixels
    ).items():
        if not np.any(variant):
            segmentation_lengths[label] = None
            segmentation_mean_widths[label] = None
            segmentation_p95_widths[label] = None
            continue
        skeleton = _skeletonize(variant)
        graph = build_skeleton_graph(skeleton)
        segmentation_lengths[label] = _round(
            _transform_network_length(graph, calibration.metric_homography())
        )
        rectified = calibration.warp_mask(variant)
        rectified_skeleton = _skeletonize(rectified)
        width_stats = _width_statistics(
            _width_map(rectified),
            rectified_skeleton,
            calibration.pixels_per_unit,
        )
        mean_width = width_stats["mean"]
        p95_width = width_stats["p95"]
        segmentation_mean_widths[label] = (
            float(mean_width) if isinstance(mean_width, (int, float)) else None
        )
        segmentation_p95_widths[label] = (
            float(p95_width) if isinstance(p95_width, (int, float)) else None
        )

    nominal_length = float(nominal_metric["centerline_network_length"])
    length_values = calibration_lengths + [
        value
        for value in segmentation_lengths.values()
        if isinstance(value, (int, float))
    ]
    if not length_values:
        length_values = [nominal_length]
    return {
        "interpretation": "sensitivity_interval_not_certified_confidence_interval",
        "interpretation_zh": "这是输入扰动敏感性区间，不是法定或认证置信区间",
        "sources": {
            "calibration_corner_gaussian_sigma_pixels": calibration.point_sigma_pixels,
            "segmentation_boundary_radius_pixels": segmentation_radius_pixels,
            "monte_carlo_samples_requested": uncertainty_samples,
            "monte_carlo_samples_accepted": len(calibration_lengths),
            "monte_carlo_attempts": attempts,
            "random_seed": seed,
        },
        "centerline_network_length": {
            "nominal": nominal_length,
            "interval": _interval(length_values),
            "segmentation_variants": segmentation_lengths,
        },
        "mean_width": {
            "nominal": nominal_metric["width_distribution"]["mean"],
            "segmentation_variants": segmentation_mean_widths,
            "interval": _interval(
                [
                    value
                    for value in segmentation_mean_widths.values()
                    if isinstance(value, (int, float))
                ]
            ),
        },
        "p95_width": {
            "nominal": nominal_metric["width_distribution"]["p95"],
            "segmentation_variants": segmentation_p95_widths,
            "interval": _interval(
                [
                    value
                    for value in segmentation_p95_widths.values()
                    if isinstance(value, (int, float))
                ]
            ),
        },
    }


def analyze_crack_mask(
    mask: NDArray[np.generic],
    *,
    calibration: PlanarCalibration | None = None,
    uncertainty_samples: int = 64,
    seed: int = 42,
    segmentation_radius_pixels: int = 1,
) -> MetrologyAnalysis:
    if uncertainty_samples < 0 or uncertainty_samples > 1000:
        raise metrology_error(f"uncertainty_samples={uncertainty_samples}")
    if segmentation_radius_pixels < 0 or segmentation_radius_pixels > 10:
        raise metrology_error(
            f"segmentation_radius_pixels={segmentation_radius_pixels}"
        )
    source_mask = _normalize_mask(mask)
    source_skeleton = _skeletonize(source_mask)
    source_graph = build_skeleton_graph(source_skeleton)
    source_width_map = _width_map(source_mask)
    topology = summarize_skeleton(source_skeleton, source_graph)
    pixel_geometry = _pixel_geometry(
        source_mask,
        source_skeleton,
        source_graph,
        source_width_map,
    )
    payload: dict[str, object] = {
        "schema_version": "crack-metrology-v3.0.0",
        "measurement_space": "pixel_only",
        "mask_dimensions": {
            "width": int(source_mask.shape[1]),
            "height": int(source_mask.shape[0]),
        },
        "topology": topology,
        "pixel_geometry": pixel_geometry,
        "physical_geometry": None,
        "calibration": None,
        "uncertainty": None,
        "decision_boundary": {
            "physical_measurement_valid": False,
            "message_zh": "未提供现场平面标定；像素值不能用于实际养护尺寸决策",
            "message_en": (
                "No field planar calibration was supplied; pixel values must not be used "
                "for physical maintenance decisions"
            ),
        },
    }

    rectified_mask: NDArray[np.bool_] | None = None
    rectified_skeleton: NDArray[np.bool_] | None = None
    rectified_width_map: NDArray[np.float32] | None = None
    if calibration is not None:
        calibration.validate_for_image(source_mask.shape)
        rectified_mask = calibration.warp_mask(source_mask)
        if not np.any(rectified_mask):
            raise metrology_error("the calibrated quadrilateral contains no crack mask")
        rectified_skeleton = _skeletonize(rectified_mask)
        rectified_graph = build_skeleton_graph(rectified_skeleton)
        rectified_width_map = _width_map(rectified_mask)
        metric_geometry = _metric_geometry(
            source_graph=source_graph,
            calibration=calibration,
            rectified_mask=rectified_mask,
            rectified_skeleton=rectified_skeleton,
            rectified_graph=rectified_graph,
            rectified_width_map=rectified_width_map,
        )
        payload.update(
            {
                "measurement_space": "rectified_physical_plane",
                "physical_geometry": metric_geometry,
                "calibration": calibration.to_dict(),
                "uncertainty": _uncertainty_analysis(
                    source_mask=source_mask,
                    source_graph=source_graph,
                    calibration=calibration,
                    uncertainty_samples=uncertainty_samples,
                    seed=seed,
                    segmentation_radius_pixels=segmentation_radius_pixels,
                    nominal_metric=metric_geometry,
                ),
                "decision_boundary": {
                    "physical_measurement_valid": True,
                    "message_zh": (
                        "物理量基于单平面标定，仅对标定平面内的裂缝有效；"
                        "区间是敏感性分析而非认证置信区间"
                    ),
                    "message_en": (
                        "Physical values use a single-plane calibration and are valid only "
                        "inside that plane; intervals are sensitivity analyses, not certified "
                        "confidence intervals"
                    ),
                },
            }
        )
    return MetrologyAnalysis(
        payload=payload,
        source_mask=source_mask,
        source_skeleton=source_skeleton,
        source_width_map=source_width_map,
        rectified_mask=rectified_mask,
        rectified_skeleton=rectified_skeleton,
        rectified_width_map=rectified_width_map,
    )


def measure_crack_mask(
    mask: NDArray[np.generic],
    *,
    calibration: PlanarCalibration | None = None,
    uncertainty_samples: int = 64,
    seed: int = 42,
    segmentation_radius_pixels: int = 1,
) -> dict[str, object]:
    return analyze_crack_mask(
        mask,
        calibration=calibration,
        uncertainty_samples=uncertainty_samples,
        seed=seed,
        segmentation_radius_pixels=segmentation_radius_pixels,
    ).payload
