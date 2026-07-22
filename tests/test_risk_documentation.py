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
    assert "confidence never changes risk_score" in guide
    assert "置信度绝不改变 risk_score" in guide
    assert "does not replace a certified engineering safety assessment" in guide
    assert "不能替代经过认证的工程安全鉴定" in guide
    assert "Lesson 09" in learning
    assert "risks/" in results
