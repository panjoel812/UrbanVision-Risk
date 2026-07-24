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
    assert "complete workflow directly at `http://127.0.0.1:8000`" in readme
    assert "完整单页流程" in readme
    assert "Run calibrated demo / 运行完整标定 Demo" in guide
    assert "Choosing one image starts three-view detection" in readme
    assert "画笔/橡皮" in readme
    assert "automatic_draft" in readme
    assert "human_reviewed" in readme
    assert "review-hotspots.png" in readme
    assert "three_level_sensitivity_vote_disagreement" in guide
    assert "priority score = disagreement pixels" in guide
    assert "proposal_revision.hotspot_review" in guide
    assert "640 \u00d7 360" in guide
    assert "source_x = viewport_x" in guide
    assert "同步复核放大窗" in guide
    assert "Structured hotspot dispositions" in guide
    assert "accepted_as_proposed" in guide
    assert "ranked_decision_priority_coverage_ratio" in guide
    assert "active-learning-feedback.zip" in guide
    assert "512,000" in guide
    assert "No absolute path is stored" in guide
    assert "Feedback quality gates and registry" in guide
    assert "feedback-catalog?limit=100" in guide
    assert "64-bit difference hash" in guide
    assert "Leakage-safe candidate curation" in guide
    assert "feedback-curations" in guide
    assert 'quality_gate.status == "pass"' in guide
    assert "source_sha256" in guide
    assert "candidate_plan_requires_training_approval" in guide
    assert "`training_authorized` remains `false`" in guide
    assert "防泄漏候选数据策划" in guide
    assert "Build leakage-safe candidate plan" in readme
    assert "source-grouped 80/10/10 allocation" in portfolio
    assert "不是模型不确定性校准" in guide
    assert "local_proposal_automatic_draft" in guide
    assert "ArUco" in portfolio
    assert "Ground truth / 人工参考值" in template
    assert "Absolute length error" in template
