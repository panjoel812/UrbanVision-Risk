from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMAND = "uv run python -m urbanvision_risk.app.serve --run-name china-repair-mps-003"


def test_v2_local_app_is_documented_as_complete_bilingual_and_private() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    guide = (ROOT / "docs" / "local-app-guide.md").read_text(encoding="utf-8")
    learning = (ROOT / "docs" / "learning-guide.md").read_text(encoding="utf-8")
    narrative = (ROOT / "docs" / "local-ai-narrative-guide.md").read_text(
        encoding="utf-8"
    )
    reliability = (ROOT / "docs" / "reliability-engineering-guide.md").read_text(
        encoding="utf-8"
    )
    portfolio = (ROOT / "docs" / "portfolio-guide.md").read_text(encoding="utf-8")
    results = (ROOT / "results" / "README.md").read_text(encoding="utf-8")

    assert COMMAND in readme
    assert COMMAND in guide
    assert "native 640, native 1280, and horizontally mirrored 1280" in guide
    assert "原图 640、原图 1280 和水平镜像 1280" in guide
    assert "reliability.json" in guide
    assert "active-learning priority" in guide
    assert "Human review required" in guide
    assert "需要人工复核" in guide
    assert "no AWS, Azure, Google Cloud, paid API" in guide
    assert "不使用 AWS、Azure、Google Cloud、付费 API" in guide
    assert "127.0.0.1" in guide
    assert "15 MiB" in guide
    assert "40 megapixels" in guide
    assert "4000 万像素" in guide
    assert "inspection-manifest.json" in guide
    assert "narrative.json" in guide
    assert "Local AI Narrative" in narrative
    assert "本地 AI 巡检说明" in narrative
    assert "127.0.0.1:11434" in narrative
    assert "source or annotated image bytes" in narrative
    assert "原图或标注图内容" in narrative
    assert "generator.fallback_reason" in narrative
    assert "not a certified engineering report" in narrative
    assert "不是认证工程报告" in narrative
    assert "Maintenance-review priority, not a road-safety verdict" in guide
    assert "维护复核优先级，不是道路安全判定" in guide
    assert "Lesson 11" in learning
    assert "inspections/" in results
    assert "Association and fusion" in reliability
    assert "跨视图聚类" in reliability
    assert "active_learning_priority" in reliability
    assert "/api/review-queue" in reliability
    assert "Resume bullets" in portfolio
    assert "简历要点" in portfolio
    assert "Claims to avoid" in portfolio
