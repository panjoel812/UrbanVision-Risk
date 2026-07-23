from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Any

from urbanvision_risk.data.voc import DETECTION_CLASS_INFO
from urbanvision_risk.detection.tiled import DetectionCandidate, class_aware_nms

CONSENSUS_SCHEMA_VERSION = "reliability-consensus-v2.0.0"


@dataclass(frozen=True, slots=True)
class ViewObservation:
    view_id: str
    candidate: DetectionCandidate


@dataclass(frozen=True, slots=True)
class ConsensusResult:
    """Accepted detections plus JSON-safe reliability evidence."""

    candidates: tuple[DetectionCandidate, ...]
    evidence: dict[str, Any]


@dataclass(slots=True)
class _Cluster:
    class_id: int
    observations: list[ViewObservation]


def _iou(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> float:
    x1 = max(first[0], second[0])
    y1 = max(first[1], second[1])
    x2 = min(first[2], second[2])
    y2 = min(first[3], second[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if intersection == 0:
        return 0.0
    first_area = (first[2] - first[0]) * (first[3] - first[1])
    second_area = (second[2] - second[0]) * (second[3] - second[1])
    return intersection / (first_area + second_area - intersection)


def _fused_box(cluster: _Cluster) -> tuple[float, float, float, float]:
    weights = [max(observation.candidate.confidence, 1e-9) for observation in cluster.observations]
    total = sum(weights)
    return tuple(
        sum(
            weight * observation.candidate.bbox_xyxy[index]
            for weight, observation in zip(weights, cluster.observations, strict=True)
        )
        / total
        for index in range(4)
    )  # type: ignore[return-value]


def horizontal_flip_candidates(
    candidates: list[DetectionCandidate], image_width: int
) -> list[DetectionCandidate]:
    """Map candidates inferred on a horizontally flipped image back to source coordinates."""
    if image_width <= 0:
        raise ValueError("image_width must be positive")
    return [
        DetectionCandidate(
            class_id=candidate.class_id,
            confidence=candidate.confidence,
            bbox_xyxy=(
                float(image_width) - candidate.bbox_xyxy[2],
                candidate.bbox_xyxy[1],
                float(image_width) - candidate.bbox_xyxy[0],
                candidate.bbox_xyxy[3],
            ),
        )
        for candidate in candidates
    ]


def _active_learning_tier(priority: float) -> str:
    if priority >= 60:
        return "high"
    if priority >= 30:
        return "medium"
    return "low"


def analyze_consensus(
    view_candidates: dict[str, list[DetectionCandidate]],
    *,
    decision_confidence: float,
    association_iou: float = 0.45,
    minimum_view_support: int = 2,
    per_view_nms_iou: float = 0.50,
) -> ConsensusResult:
    """Associate detections across transformed views and quantify epistemic instability.

    A detection is accepted only when at least ``minimum_view_support`` independent
    views agree on its class and location and one observation reaches the configured
    decision confidence. Confidence is averaged across supporting views instead of
    taking the most optimistic prediction.
    """
    if len(view_candidates) < 2:
        raise ValueError("consensus requires at least two views")
    if not 0 <= decision_confidence <= 1:
        raise ValueError("decision_confidence must be in [0, 1]")
    if not 0 <= association_iou <= 1:
        raise ValueError("association_iou must be in [0, 1]")
    if not 1 < minimum_view_support <= len(view_candidates):
        raise ValueError("minimum_view_support must be between 2 and the view count")

    normalized: dict[str, list[DetectionCandidate]] = {
        view_id: class_aware_nms(candidates, iou_threshold=per_view_nms_iou)
        for view_id, candidates in sorted(view_candidates.items())
    }
    observations = sorted(
        (
            ViewObservation(view_id=view_id, candidate=candidate)
            for view_id, candidates in normalized.items()
            for candidate in candidates
        ),
        key=lambda item: (
            -item.candidate.confidence,
            item.candidate.class_id,
            item.view_id,
            item.candidate.bbox_xyxy,
        ),
    )

    clusters: list[_Cluster] = []
    for observation in observations:
        compatible: list[tuple[float, int]] = []
        for index, cluster in enumerate(clusters):
            used_views = {item.view_id for item in cluster.observations}
            if (
                cluster.class_id != observation.candidate.class_id
                or observation.view_id in used_views
            ):
                continue
            overlap = _iou(observation.candidate.bbox_xyxy, _fused_box(cluster))
            if overlap >= association_iou:
                compatible.append((overlap, index))
        if compatible:
            _, best_index = max(compatible, key=lambda item: (item[0], -item[1]))
            clusters[best_index].observations.append(observation)
        else:
            clusters.append(
                _Cluster(
                    class_id=observation.candidate.class_id,
                    observations=[observation],
                )
            )

    view_count = len(normalized)
    accepted_candidates: list[DetectionCandidate] = []
    cluster_payloads: list[dict[str, Any]] = []
    accepted_stabilities: list[float] = []
    accepted_uncertainties: list[float] = []
    disputed_count = 0
    for cluster_id, cluster in enumerate(clusters, start=1):
        box = _fused_box(cluster)
        confidences = [item.candidate.confidence for item in cluster.observations]
        mean_confidence = statistics.fmean(confidences)
        maximum_confidence = max(confidences)
        confidence_std = statistics.pstdev(confidences) if len(confidences) > 1 else 0.0
        localization_agreement = statistics.fmean(
            _iou(item.candidate.bbox_xyxy, box) for item in cluster.observations
        )
        support_views = sorted({item.view_id for item in cluster.observations})
        support_count = len(support_views)
        support_ratio = support_count / view_count
        stability = math.sqrt(max(0.0, support_ratio * localization_agreement))
        uncertainty = 1.0 - (0.65 * stability + 0.35 * mean_confidence)
        accepted = (
            support_count >= minimum_view_support
            and maximum_confidence >= decision_confidence
        )
        if accepted:
            accepted_candidates.append(
                DetectionCandidate(
                    class_id=cluster.class_id,
                    confidence=mean_confidence,
                    bbox_xyxy=box,
                )
            )
            accepted_stabilities.append(stability)
            accepted_uncertainties.append(uncertainty)
            disposition = "accepted_consensus"
        elif maximum_confidence >= decision_confidence:
            disputed_count += 1
            disposition = "disputed_single_view"
        else:
            disposition = "below_decision_confidence"

        details = DETECTION_CLASS_INFO[cluster.class_id]
        cluster_payloads.append(
            {
                "cluster_id": cluster_id,
                "class_id": cluster.class_id,
                "code": details["code"],
                "accepted": accepted,
                "disposition": disposition,
                "support_views": support_views,
                "support_count": support_count,
                "support_ratio": round(support_ratio, 6),
                "mean_confidence": round(mean_confidence, 6),
                "maximum_confidence": round(maximum_confidence, 6),
                "confidence_std": round(confidence_std, 6),
                "localization_agreement": round(localization_agreement, 6),
                "stability_score": round(stability, 6),
                "uncertainty_score": round(uncertainty, 6),
                "fused_bbox_xyxy": [round(value, 4) for value in box],
            }
        )

    accepted_count = len(accepted_candidates)
    relevant_count = accepted_count + disputed_count
    disagreement_ratio = disputed_count / relevant_count if relevant_count else 0.0
    mean_stability = (
        statistics.fmean(accepted_stabilities) if accepted_stabilities else None
    )
    mean_uncertainty = (
        statistics.fmean(accepted_uncertainties) if accepted_uncertainties else 1.0
    )
    priority = min(100.0, 100.0 * (0.70 * mean_uncertainty + 0.30 * disagreement_ratio))
    review_recommended = (
        accepted_count == 0
        or disputed_count > 0
        or (mean_stability is not None and mean_stability < 0.60)
    )
    evidence: dict[str, Any] = {
        "schema_version": CONSENSUS_SCHEMA_VERSION,
        "mode": "transform_consensus",
        "view_count": view_count,
        "views": list(normalized),
        "association_iou": association_iou,
        "minimum_view_support": minimum_view_support,
        "per_view_nms_iou": per_view_nms_iou,
        "summary": {
            "raw_candidate_count": sum(len(items) for items in normalized.values()),
            "cluster_count": len(cluster_payloads),
            "accepted_cluster_count": accepted_count,
            "disputed_cluster_count": disputed_count,
            "mean_stability": round(mean_stability, 6) if mean_stability is not None else None,
            "mean_uncertainty": round(mean_uncertainty, 6),
            "active_learning_priority": round(priority, 1),
            "active_learning_tier": _active_learning_tier(priority),
            "review_recommended": review_recommended,
        },
        "clusters": cluster_payloads,
        "method": {
            "en": (
                "Class-aware cross-view IoU association, confidence-weighted box fusion, "
                "and conservative mean-confidence aggregation."
            ),
            "zh": "分类感知的跨视图 IoU 关联、置信度加权框融合与保守平均置信度聚合。",
        },
    }
    return ConsensusResult(
        candidates=tuple(
            sorted(
                accepted_candidates,
                key=lambda item: (-item.confidence, item.class_id, item.bbox_xyxy),
            )
        ),
        evidence=evidence,
    )
