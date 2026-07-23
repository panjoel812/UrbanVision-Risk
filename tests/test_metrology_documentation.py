from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v3_metrology_is_documented_as_calibrated_auditable_and_field_testable() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    guide = (ROOT / "docs" / "metrology-field-guide.md").read_text(encoding="utf-8")
    template = (ROOT / "docs" / "field-experiment-template.md").read_text(
        encoding="utf-8"
    )
    portfolio = (ROOT / "docs" / "portfolio-guide.md").read_text(encoding="utf-8")

    commands = (
        "urbanvision_risk.metrology.demo",
        "urbanvision_risk.metrology.target",
        "urbanvision_risk.metrology.fiducials",
        "urbanvision_risk.metrology.measure",
    )
    assert all(command in guide for command in commands)
    assert "pixel_only" in guide
    assert "physical_measurement_valid" in guide
    assert "TL → TR → BR → BL" in guide
    assert "sensitivity_interval_not_certified_confidence_interval" in guide
    assert "100%" in guide
    assert "held-out field" in guide
    assert "留出现场" in guide
    assert "OpenCV homography documentation" in guide
    assert "measurement.json" in readme
    assert "http://127.0.0.1:8000/metrology" in readme
    assert "Run calibrated demo / 运行完整标定 Demo" in guide
    assert "mask brush" in readme
    assert "画笔/橡皮" in readme
    assert "ArUco" in portfolio
    assert "Ground truth / 人工参考值" in template
    assert "Absolute length error" in template
