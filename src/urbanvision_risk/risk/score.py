from __future__ import annotations

import math
import statistics
from collections import defaultdict

from urbanvision_risk.data.voc import CLASS_INFO
from urbanvision_risk.risk.config import RiskConfig
from urbanvision_risk.risk.geometry import Rectangle, rectangle_union_area
from urbanvision_risk.risk.schema import PredictionRecord


def score_prediction(
    record: PredictionRecord,
    config: RiskConfig,
    *,
    source_prediction: str,
    source_sha256: str,
    config_sha256: str,
) -> dict[str, object]:
    """Produce an explainable maintenance-priority score without side effects."""
    rectangles_by_code: defaultdict[str, list[Rectangle]] = defaultdict(list)
    for detection in record.detections:
        rectangles_by_code[detection.code].append(detection.rectangle)

    image_area = float(record.width * record.height)
    class_breakdown: list[dict[str, object]] = []
    raw_total = 0.0
    for class_id, details in CLASS_INFO.items():
        code = details["code"]
        count = record.counts[code]
        union_area = rectangle_union_area(rectangles_by_code[code])
        coverage_ratio = min(1.0, union_area / image_area)
        count_factor = min(count / config.count_cap, 1.0)
        coverage_factor = min(math.sqrt(coverage_ratio / config.reference_coverage), 1.0)
        contribution = config.class_max_points[code] * (
            config.count_mix * count_factor + config.coverage_mix * coverage_factor
        )
        raw_total += contribution
        class_breakdown.append(
            {
                "class_id": class_id,
                "code": code,
                "name_en": details["name_en"],
                "name_zh": details["name_zh"],
                "count": count,
                "union_area_pixels": round(union_area, 4),
                "coverage_ratio": round(coverage_ratio, 8),
                "count_factor": round(count_factor, 8),
                "coverage_factor": round(coverage_factor, 8),
                "maximum_points": config.class_max_points[code],
                "score_contribution": round(contribution, 4),
            }
        )

    risk_score = round(min(100.0, raw_total), 1)
    risk_level = config.risk_level(risk_score)
    confidences = [detection.confidence for detection in record.detections]
    mean_confidence = statistics.fmean(confidences) if confidences else None
    evidence_quality = config.evidence_quality(mean_confidence)
    clipped_count = sum(detection.clipped for detection in record.detections)
    audit_flags: list[dict[str, str]] = []
    if clipped_count:
        audit_flags.append(
            {
                "code": "coordinates_clipped",
                "en": f"{clipped_count} detection box(es) were clipped within tolerance.",
                "zh": f"{clipped_count} 个检测框在容差范围内被裁剪。",
            }
        )
    if evidence_quality == "low":
        audit_flags.append(
            {
                "code": "low_evidence_quality",
                "en": "Mean detection confidence is low; prioritize human review.",
                "zh": "平均检测置信度较低；请优先人工复核。",
            }
        )

    return {
        "formula_version": config.formula_version,
        "source_prediction": source_prediction,
        "source_prediction_sha256": source_sha256,
        "resolved_config_sha256": config_sha256,
        "source_image": record.source_image,
        "model_checkpoint": record.model_checkpoint,
        "confidence_threshold": record.confidence_threshold,
        "image_dimensions": {"width": record.width, "height": record.height},
        "risk_score": risk_score,
        "risk_level": risk_level,
        "recommendation": dict(config.recommendations[risk_level]),
        "class_breakdown": class_breakdown,
        "evidence": {
            "mean_detection_confidence": (
                round(mean_confidence, 6) if mean_confidence is not None else None
            ),
            "quality": evidence_quality,
            "en": "Confidence describes evidence quality and never changes risk_score.",
            "zh": "置信度只描述证据质量，绝不改变 risk_score。",
        },
        "audit_flags": audit_flags,
        "formula": {
            "en": "Per class: max_points * (0.35 * count_factor + 0.65 * coverage_factor).",
            "zh": "每类: 最高分 * (0.35 * 数量因子 + 0.65 * 覆盖因子)。",
        },
        "limitation": dict(config.limitation),
    }
