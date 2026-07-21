from pathlib import Path

import pytest

from urbanvision_risk.errors import ProjectError
from urbanvision_risk.risk.config import load_risk_config, resolved_config_yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "risk-v0.2.yaml"


def test_committed_risk_config_has_approved_defaults() -> None:
    config = load_risk_config(CONFIG_PATH)

    assert config.formula_version == "risk-v0.2.0"
    assert config.count_cap == 5
    assert config.reference_coverage == 0.05
    assert config.count_mix == 0.35
    assert config.coverage_mix == 0.65
    assert config.class_max_points == {"D00": 15.0, "D10": 20.0, "D20": 25.0, "D40": 40.0}
    assert config.risk_level(19.9) == "low"
    assert config.risk_level(20.0) == "moderate"
    assert config.risk_level(40.0) == "high"
    assert config.risk_level(70.0) == "critical"
    assert config.evidence_quality(None) == "not_applicable"
    assert config.evidence_quality(0.49) == "low"
    assert config.evidence_quality(0.50) == "moderate"
    assert config.evidence_quality(0.75) == "high"
    assert "formula_version" in resolved_config_yaml(config)


def test_config_rejects_weights_that_do_not_total_one_hundred(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text(
        CONFIG_PATH.read_text(encoding="utf-8").replace("D40: 40", "D40: 39"),
        encoding="utf-8",
    )

    with pytest.raises(ProjectError, match="E401"):
        load_risk_config(invalid)


def test_config_rejects_mix_that_does_not_total_one(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text(
        CONFIG_PATH.read_text(encoding="utf-8").replace("coverage_mix: 0.65", "coverage_mix: 0.60"),
        encoding="utf-8",
    )

    with pytest.raises(ProjectError, match="E401"):
        load_risk_config(invalid)
