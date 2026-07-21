from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from urbanvision_risk.data.voc import CLASS_INFO
from urbanvision_risk.errors import ProjectError

CLASS_CODES = tuple(details["code"] for details in CLASS_INFO.values())
RISK_LEVELS = ("low", "moderate", "high", "critical")


def _config_error(path: Path, field: str) -> ProjectError:
    return ProjectError(
        "E401",
        "风险配置非法",
        "Risk configuration is invalid",
        "检查配置字段和设计文档中的约束",
        "Inspect the field and the constraints in the design document",
        f"{path}: {field}",
    )


def _mapping(value: Any, path: Path, field: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise _config_error(path, field)
    return value


def _finite_number(value: Any, path: Path, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _config_error(path, field)
    result = float(value)
    if not math.isfinite(result):
        raise _config_error(path, field)
    return result


def _positive_integer(value: Any, path: Path, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise _config_error(path, field)
    return value


def _text(value: Any, path: Path, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _config_error(path, field)
    return value.strip()


@dataclass(frozen=True, slots=True)
class RiskConfig:
    formula_version: str
    count_cap: int
    reference_coverage: float
    count_mix: float
    coverage_mix: float
    class_max_points: dict[str, float]
    risk_thresholds: dict[str, float]
    evidence_thresholds: dict[str, float]
    coordinate_tolerance_pixels: float
    recommendations: dict[str, dict[str, str]]
    limitation: dict[str, str]

    def risk_level(self, score: float) -> str:
        if score >= self.risk_thresholds["critical"]:
            return "critical"
        if score >= self.risk_thresholds["high"]:
            return "high"
        if score >= self.risk_thresholds["moderate"]:
            return "moderate"
        return "low"

    def evidence_quality(self, mean_confidence: float | None) -> str:
        if mean_confidence is None:
            return "not_applicable"
        if mean_confidence >= self.evidence_thresholds["high"]:
            return "high"
        if mean_confidence >= self.evidence_thresholds["moderate"]:
            return "moderate"
        return "low"

    def to_payload(self) -> dict[str, object]:
        return {
            "formula_version": self.formula_version,
            "count_cap": self.count_cap,
            "reference_coverage": self.reference_coverage,
            "count_mix": self.count_mix,
            "coverage_mix": self.coverage_mix,
            "class_max_points": dict(self.class_max_points),
            "risk_thresholds": dict(self.risk_thresholds),
            "evidence_thresholds": dict(self.evidence_thresholds),
            "coordinate_tolerance_pixels": self.coordinate_tolerance_pixels,
            "recommendations": {
                level: dict(messages) for level, messages in self.recommendations.items()
            },
            "limitation": dict(self.limitation),
        }


def load_risk_config(path: Path) -> RiskConfig:
    if not path.is_file():
        raise ProjectError(
            "E201",
            "风险配置不存在",
            "Risk configuration does not exist",
            "检查 --config 路径",
            "Check the --config path",
            str(path),
        )
    try:
        root = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), path, "root")
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise _config_error(path, "root") from error

    formula_version = _text(root.get("formula_version"), path, "formula_version")
    count_cap = _positive_integer(root.get("count_cap"), path, "count_cap")
    reference_coverage = _finite_number(
        root.get("reference_coverage"), path, "reference_coverage"
    )
    count_mix = _finite_number(root.get("count_mix"), path, "count_mix")
    coverage_mix = _finite_number(root.get("coverage_mix"), path, "coverage_mix")
    tolerance = _finite_number(
        root.get("coordinate_tolerance_pixels"), path, "coordinate_tolerance_pixels"
    )

    class_raw = _mapping(root.get("class_max_points"), path, "class_max_points")
    if set(class_raw) != set(CLASS_CODES):
        raise _config_error(path, "class_max_points")
    class_points = {
        code: _finite_number(class_raw[code], path, f"class_max_points.{code}")
        for code in CLASS_CODES
    }

    risk_raw = _mapping(root.get("risk_thresholds"), path, "risk_thresholds")
    evidence_raw = _mapping(root.get("evidence_thresholds"), path, "evidence_thresholds")
    if set(risk_raw) != {"moderate", "high", "critical"}:
        raise _config_error(path, "risk_thresholds")
    if set(evidence_raw) != {"moderate", "high"}:
        raise _config_error(path, "evidence_thresholds")
    risk_thresholds = {
        name: _finite_number(risk_raw[name], path, f"risk_thresholds.{name}")
        for name in ("moderate", "high", "critical")
    }
    evidence_thresholds = {
        name: _finite_number(evidence_raw[name], path, f"evidence_thresholds.{name}")
        for name in ("moderate", "high")
    }

    recommendations_raw = _mapping(root.get("recommendations"), path, "recommendations")
    if set(recommendations_raw) != set(RISK_LEVELS):
        raise _config_error(path, "recommendations")
    recommendations: dict[str, dict[str, str]] = {}
    for level in RISK_LEVELS:
        messages = _mapping(recommendations_raw[level], path, f"recommendations.{level}")
        if set(messages) != {"en", "zh"}:
            raise _config_error(path, f"recommendations.{level}")
        recommendations[level] = {
            language: _text(messages[language], path, f"recommendations.{level}.{language}")
            for language in ("en", "zh")
        }

    limitation_raw = _mapping(root.get("limitation"), path, "limitation")
    if set(limitation_raw) != {"en", "zh"}:
        raise _config_error(path, "limitation")
    limitation = {
        language: _text(limitation_raw[language], path, f"limitation.{language}")
        for language in ("en", "zh")
    }

    if not 0 < reference_coverage <= 1:
        raise _config_error(path, "reference_coverage")
    if count_mix < 0 or coverage_mix < 0 or not math.isclose(count_mix + coverage_mix, 1.0):
        raise _config_error(path, "count_mix/coverage_mix")
    if any(value <= 0 for value in class_points.values()) or not math.isclose(
        sum(class_points.values()), 100.0
    ):
        raise _config_error(path, "class_max_points")
    if not 0 < risk_thresholds["moderate"] < risk_thresholds["high"] < risk_thresholds[
        "critical"
    ] <= 100:
        raise _config_error(path, "risk_thresholds")
    if not 0 < evidence_thresholds["moderate"] < evidence_thresholds["high"] <= 1:
        raise _config_error(path, "evidence_thresholds")
    if tolerance < 0:
        raise _config_error(path, "coordinate_tolerance_pixels")

    return RiskConfig(
        formula_version=formula_version,
        count_cap=count_cap,
        reference_coverage=reference_coverage,
        count_mix=count_mix,
        coverage_mix=coverage_mix,
        class_max_points=class_points,
        risk_thresholds=risk_thresholds,
        evidence_thresholds=evidence_thresholds,
        coordinate_tolerance_pixels=tolerance,
        recommendations=recommendations,
        limitation=limitation,
    )


def resolved_config_yaml(config: RiskConfig) -> str:
    return yaml.safe_dump(
        config.to_payload(),
        allow_unicode=True,
        sort_keys=False,
    )
