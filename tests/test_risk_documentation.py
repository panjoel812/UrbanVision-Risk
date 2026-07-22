from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMAND = (
    "uv run python -m urbanvision_risk.risk.assess "
    "--run-name china-baseline-001 "
    "--prediction-name prediction-001 "
    "--output-name risk-001"
)


def test_risk_workflow_is_bilingual_and_safety_bounded() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    guide = (ROOT / "docs" / "risk-engine-guide.md").read_text(encoding="utf-8")
    learning = (ROOT / "docs" / "learning-guide.md").read_text(encoding="utf-8")
    results = (ROOT / "results" / "README.md").read_text(encoding="utf-8")

    assert COMMAND in readme
    assert COMMAND in guide
    assert "count_factor = min(count / 5, 1)" in guide
    assert "coverage_factor = min(sqrt(coverage_ratio / 0.05), 1)" in guide
    class_score_formula = (
        "class_score = class_max_points \u00d7 "
        "(0.35 \u00d7 count_factor + 0.65 \u00d7 coverage_factor)"
    )
    assert class_score_formula in guide
    assert "risk_score = round(min(100, sum(class_score)), 1)" in guide
    assert "risk-v0.2.0" in guide
    assert "count_cap" in guide
    assert "5" in guide
    assert "reference_coverage" in guide
    assert "0.05" in guide
    assert "count_mix / coverage_mix" in guide
    assert "0.35 / 0.65" in guide
    assert "D00=15, D10=20, D20=25, and D40=40" in guide
    assert "D00=15、D10=20、D20=25、D40=40" in guide
    assert "[0,20)" in guide
    assert "[20,40)" in guide
    assert "[40,70)" in guide
    assert "[70,100]" in guide
    assert "[0,0.50)" in guide
    assert "[0.50,0.75)" in guide
    assert "[0.75,1]" in guide
    assert "not_applicable" in guide
    assert "coordinate_tolerance_pixels" in guide
    assert "1 pixel" in guide
    assert "1 个像素" in guide
    assert "confidence never changes risk_score" in guide
    assert "置信度绝不改变 risk_score" in guide
    assert "mean and minimum detection confidence" in guide
    assert "平均和最低检测置信度" in guide
    assert "low_confidence_evidence" in guide
    for artifact in (
        "per-image/*-risk.json",
        "ranking.csv",
        "risk-summary.json",
        "risk-config-resolved.yaml",
    ):
        assert artifact in guide
    for code in ("E201", "E204", "E401", "E402", "E403", "E404"):
        assert code in guide
    for recovery_term in (
        "disk space",
        "permissions",
        "partial directory",
        "new unused output name",
        "磁盘空间",
        "权限",
        "不完整目录",
        "新的未使用的输出名",
    ):
        assert recovery_term in guide
    assert "does not replace a certified engineering safety assessment" in guide
    assert "不能替代经过认证的工程安全鉴定" in guide
    assert "does not mean the road is safe" in guide
    assert "不代表道路安全" in guide
    assert "A human engineer decides inspection, closure, and repair actions." in guide
    assert "检查、封闭和维修措施必须由人类工程人员决定。" in guide
    for excluded_input in (
        "physical scale",
        "GPS",
        "traffic exposure",
        "pavement history",
        "calibrated engineering severity labels",
        "物理尺度",
        "交通暴露",
        "路面历史",
        "经过标定的工程严重度标签",
    ):
        assert excluded_input in guide
    assert "Lesson 09" in learning
    assert "risks/" in results
