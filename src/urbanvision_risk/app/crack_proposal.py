from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

MAX_PROPOSAL_WORK_PIXELS = 2_000_000
MAX_PROPOSAL_COVERAGE_RATIO = 0.35
PROPOSAL_SCHEMA_VERSION = "local-crack-proposal-v4.3.0"
REVIEW_SENSITIVITY_OFFSET = 0.15


@dataclass(frozen=True)
class CrackProposal:
    mask: np.ndarray
    review_hotspots: np.ndarray
    evidence: dict[str, object]


def _normalize(response: np.ndarray, percentile: float = 99.5) -> np.ndarray:
    upper = float(np.percentile(response, percentile))
    if not math.isfinite(upper) or upper <= 1e-6:
        return np.zeros(response.shape, dtype=np.float32)
    return np.clip(response.astype(np.float32) / upper, 0.0, 1.0)


def _blackhat_score(gray: np.ndarray) -> tuple[np.ndarray, list[int]]:
    height, width = gray.shape
    base = max(1, round(min(height, width) / 400))
    diameters = sorted({max(3, base * factor * 2 + 1) for factor in (1, 2, 4, 7)})
    responses = []
    for diameter in diameters:
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (diameter, diameter),
        )
        response = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)
        responses.append(_normalize(response))
    return np.maximum.reduce(responses), diameters


def _dark_ridge_score(gray: np.ndarray) -> tuple[np.ndarray, list[float]]:
    image = gray.astype(np.float32) / 255.0
    height, width = gray.shape
    base = max(0.8, min(height, width) / 700.0)
    sigmas = [round(base * factor, 3) for factor in (0.8, 1.5, 2.8)]
    responses: list[np.ndarray] = []
    for sigma in sigmas:
        blurred = cv2.GaussianBlur(
            image,
            (0, 0),
            sigmaX=sigma,
            sigmaY=sigma,
            borderType=cv2.BORDER_REFLECT,
        )
        scale = sigma**2
        dxx = cv2.Sobel(blurred, cv2.CV_32F, 2, 0, ksize=3) * scale
        dxy = cv2.Sobel(blurred, cv2.CV_32F, 1, 1, ksize=3) * scale
        dyy = cv2.Sobel(blurred, cv2.CV_32F, 0, 2, ksize=3) * scale
        root = np.sqrt((dxx - dyy) ** 2 + 4.0 * dxy**2)
        eigen_a = 0.5 * (dxx + dyy - root)
        eigen_b = 0.5 * (dxx + dyy + root)
        swap = np.abs(eigen_a) > np.abs(eigen_b)
        lambda_small = np.where(swap, eigen_b, eigen_a)
        lambda_large = np.where(swap, eigen_a, eigen_b)
        ratio = np.abs(lambda_small) / (np.abs(lambda_large) + 1e-7)
        strength = np.sqrt(lambda_small**2 + lambda_large**2)
        contrast = float(np.percentile(strength, 95.0)) + 1e-7
        vesselness = np.exp(-(ratio**2) / (2.0 * 0.5**2)) * (
            1.0 - np.exp(-(strength**2) / (2.0 * contrast**2))
        )
        vesselness[lambda_large <= 0] = 0
        responses.append(_normalize(vesselness, 99.0))
    return np.maximum.reduce(responses), sigmas


def _hysteresis_components(
    score: np.ndarray,
    *,
    sensitivity: float,
) -> tuple[np.ndarray, dict[str, object]]:
    positive = score[score > 0.03]
    if positive.size < 8:
        return np.zeros(score.shape, dtype=bool), {
            "high_threshold": None,
            "low_threshold": None,
            "candidate_component_count": 0,
            "kept_component_count": 0,
        }
    high_percentile = 98.5 - sensitivity * 4.5
    high_threshold = max(
        0.28,
        float(np.percentile(positive, high_percentile)),
    )
    low_threshold = max(0.12, high_threshold * (0.48 + 0.12 * sensitivity))
    high = score >= high_threshold
    low = score >= low_threshold
    low = (
        cv2.morphologyEx(
            low.astype(np.uint8),
            cv2.MORPH_CLOSE,
            np.ones((3, 3), dtype=np.uint8),
        )
        > 0
    )
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        low.astype(np.uint8),
        connectivity=8,
    )
    minimum_area = max(6, round(score.size * 0.000003))
    maximum_area = round(score.size * 0.18)
    strong_labels = {int(label) for label in np.unique(labels[high]) if int(label) != 0}
    kept_labels: list[int] = []
    kept = 0
    rejected_no_seed = 0
    rejected_geometry = 0
    for label in range(1, count):
        if label not in strong_labels:
            rejected_no_seed += 1
            continue
        _x, _y, width, height, area = stats[label]
        elongation = max(width, height) / max(1, min(width, height))
        fill_ratio = area / max(1, width * height)
        plausible_geometry = elongation >= 1.7 or fill_ratio <= 0.58 or area <= minimum_area * 4
        if area < minimum_area or area > maximum_area or not plausible_geometry:
            rejected_geometry += 1
            continue
        kept_labels.append(label)
        kept += 1
    selected = np.isin(labels, kept_labels)
    return selected, {
        "high_threshold": round(high_threshold, 6),
        "low_threshold": round(low_threshold, 6),
        "candidate_component_count": count - 1,
        "kept_component_count": kept,
        "rejected_without_strong_seed": rejected_no_seed,
        "rejected_by_geometry": rejected_geometry,
    }


def propose_crack_mask(
    source_bgr: np.ndarray,
    *,
    sensitivity: float = 0.55,
) -> CrackProposal:
    if source_bgr.ndim != 3 or source_bgr.shape[2] != 3 or source_bgr.dtype != np.uint8:
        raise ValueError("source_bgr must be a uint8 HxWx3 image")
    if not math.isfinite(sensitivity) or not 0.0 <= sensitivity <= 1.0:
        raise ValueError("sensitivity must be finite and between 0 and 1")
    source_height, source_width = source_bgr.shape[:2]
    work_scale = min(
        1.0,
        math.sqrt(MAX_PROPOSAL_WORK_PIXELS / max(1, source_height * source_width)),
    )
    if work_scale < 1.0:
        work_width = max(2, round(source_width * work_scale))
        work_height = max(2, round(source_height * work_scale))
        work = cv2.resize(
            source_bgr,
            (work_width, work_height),
            interpolation=cv2.INTER_AREA,
        )
    else:
        work = source_bgr
    gray = cv2.cvtColor(work, cv2.COLOR_BGR2GRAY)
    normalized = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8),
    ).apply(gray)
    blackhat, blackhat_diameters = _blackhat_score(normalized)
    ridge, ridge_sigmas = _dark_ridge_score(normalized)
    score = 0.64 * blackhat + 0.36 * ridge
    review_sensitivities = sorted(
        {
            round(max(0.0, sensitivity - REVIEW_SENSITIVITY_OFFSET), 6),
            round(sensitivity, 6),
            round(min(1.0, sensitivity + REVIEW_SENSITIVITY_OFFSET), 6),
        }
    )
    masks_by_sensitivity: dict[float, np.ndarray] = {}
    component_evidence: dict[str, object] | None = None
    for review_sensitivity in review_sensitivities:
        candidate_mask, candidate_evidence = _hysteresis_components(
            score,
            sensitivity=review_sensitivity,
        )
        masks_by_sensitivity[review_sensitivity] = candidate_mask
        if math.isclose(review_sensitivity, sensitivity, abs_tol=1e-6):
            component_evidence = candidate_evidence
    work_mask = masks_by_sensitivity[round(sensitivity, 6)]
    if component_evidence is None:
        raise RuntimeError("nominal proposal sensitivity was not evaluated")
    vote_count = np.sum(
        np.stack(list(masks_by_sensitivity.values()), axis=0),
        axis=0,
        dtype=np.uint8,
    )
    sample_count = len(masks_by_sensitivity)
    work_union = vote_count > 0
    work_stable = vote_count == sample_count
    work_disagreement = work_union & ~work_stable
    work_hotspots = (
        cv2.dilate(
            work_disagreement.astype(np.uint8),
            np.ones((3, 3), dtype=np.uint8),
            iterations=1,
        )
        > 0
    )
    if work_mask.shape != (source_height, source_width):
        mask = (
            cv2.resize(
                work_mask.astype(np.uint8),
                (source_width, source_height),
                interpolation=cv2.INTER_NEAREST,
            )
            > 0
        )
        review_hotspots = (
            cv2.resize(
                work_hotspots.astype(np.uint8),
                (source_width, source_height),
                interpolation=cv2.INTER_NEAREST,
            )
            > 0
        )
        stable = (
            cv2.resize(
                work_stable.astype(np.uint8),
                (source_width, source_height),
                interpolation=cv2.INTER_NEAREST,
            )
            > 0
        )
        union = (
            cv2.resize(
                work_union.astype(np.uint8),
                (source_width, source_height),
                interpolation=cv2.INTER_NEAREST,
            )
            > 0
        )
    else:
        mask = work_mask
        review_hotspots = work_hotspots
        stable = work_stable
        union = work_union
    candidate_pixels = int(np.count_nonzero(mask))
    candidate_scores = score[work_mask]
    coverage_ratio = candidate_pixels / (source_width * source_height)
    candidate_found = candidate_pixels >= 3 and coverage_ratio <= MAX_PROPOSAL_COVERAGE_RATIO
    quality_status = (
        "usable"
        if candidate_found
        else "too_broad"
        if coverage_ratio > MAX_PROPOSAL_COVERAGE_RATIO
        else "empty"
    )
    union_pixels = int(np.count_nonzero(union))
    stable_pixels = int(np.count_nonzero(stable))
    disagreement_pixels = max(0, union_pixels - stable_pixels)
    hotspot_pixels = int(np.count_nonzero(review_hotspots))
    hotspot_count = max(
        0,
        cv2.connectedComponents(
            review_hotspots.astype(np.uint8),
            connectivity=8,
        )[0]
        - 1,
    )
    evidence: dict[str, object] = {
        "schema_version": PROPOSAL_SCHEMA_VERSION,
        "method": {
            "family": "human_in_the_loop_local_vision_ensemble",
            "normalization": "CLAHE",
            "views": [
                "multi_scale_morphological_blackhat",
                "multi_scale_dark_hessian_ridge",
                "seeded_component_hysteresis",
                "three_level_sensitivity_disagreement",
            ],
            "blackhat_kernel_diameters": blackhat_diameters,
            "ridge_sigmas": ridge_sigmas,
        },
        "parameters": {
            "sensitivity": sensitivity,
            "maximum_work_pixels": MAX_PROPOSAL_WORK_PIXELS,
        },
        "work_raster": {
            "source_width": source_width,
            "source_height": source_height,
            "work_width": work.shape[1],
            "work_height": work.shape[0],
            "scale": round(work_scale, 8),
        },
        "selection": {
            **component_evidence,
            "candidate_found": candidate_found,
            "quality_status": quality_status,
            "candidate_pixels": candidate_pixels,
            "coverage_ratio": round(coverage_ratio, 8),
            "maximum_usable_coverage_ratio": (MAX_PROPOSAL_COVERAGE_RATIO),
            "mean_selected_score": (
                round(float(np.mean(candidate_scores)), 6) if candidate_scores.size else None
            ),
        },
        "review_guidance": {
            "method": "three_level_sensitivity_vote_disagreement",
            "sensitivities": review_sensitivities,
            "sample_count": sample_count,
            "stable_vote_requirement": sample_count,
            "union_pixels": union_pixels,
            "stable_pixels": stable_pixels,
            "disagreement_pixels": disagreement_pixels,
            "disagreement_ratio_of_union": (
                round(disagreement_pixels / union_pixels, 8) if union_pixels else None
            ),
            "review_hotspot_pixels": hotspot_pixels,
            "review_hotspot_image_ratio": round(
                hotspot_pixels / (source_width * source_height),
                8,
            ),
            "review_hotspot_component_count": hotspot_count,
            "interpretation": (
                "Yellow review hotspots mark pixels whose inclusion changes across "
                "nearby sensitivity settings; this is sensitivity disagreement, "
                "not a calibrated uncertainty probability"
            ),
        },
        "decision_boundary": {
            "message_zh": (
                "候选掩膜只是本地多视图计算机视觉建议，不是人工真值或道路安全结论；"
                "阴影、接缝、标线和污渍可能产生误检，提交量测前必须人工复核和修订"
            ),
            "message_en": (
                "The candidate mask is a local multi-view computer-vision proposal, "
                "not human ground truth or a road-safety verdict; shadows, joints, "
                "markings, and stains can cause false positives, so human review and "
                "revision are required before metrology"
            ),
        },
    }
    return CrackProposal(
        mask=mask,
        review_hotspots=review_hotspots,
        evidence=evidence,
    )
