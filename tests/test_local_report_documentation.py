from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMAND = (
    "uv run python -m urbanvision_risk.reporting.build "
    "--run-name china-baseline-001 "
    "--prediction-name prediction-001 "
    "--risk-name risk-001 "
    "--output-name report-001"
)


def test_local_report_workflow_is_bilingual_offline_and_safety_bounded() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    guide = (ROOT / "docs" / "local-report-guide.md").read_text(encoding="utf-8")
    learning = (ROOT / "docs" / "learning-guide.md").read_text(encoding="utf-8")
    results = (ROOT / "results" / "README.md").read_text(encoding="utf-8")

    assert COMMAND in readme
    assert COMMAND in guide
    assert "No server, network, CDN, or cloud API is required" in guide
    assert "不需要服务器、网络、CDN 或云 API" in guide
    assert "Maintenance-review priority, not a road-safety verdict" in guide
    assert "维护复核优先级，不是道路安全判定" in guide
    assert "does not replace a certified engineering safety assessment" in guide
    assert "不能替代经过认证的工程安全鉴定" in guide
    assert "E204" in guide
    assert "report-manifest.json" in guide
    assert "Lesson 10" in learning
    assert "reports/" in results
