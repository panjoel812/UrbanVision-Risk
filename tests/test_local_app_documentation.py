from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMAND = "uv run python -m urbanvision_risk.app.serve --run-name china-baseline-001"


def test_v1_local_app_is_documented_as_complete_bilingual_and_private() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    guide = (ROOT / "docs" / "local-app-guide.md").read_text(encoding="utf-8")
    learning = (ROOT / "docs" / "learning-guide.md").read_text(encoding="utf-8")
    results = (ROOT / "results" / "README.md").read_text(encoding="utf-8")

    assert COMMAND in readme
    assert COMMAND in guide
    assert "complete first product" in guide
    assert "完整的第一版产品" in guide
    assert "no AWS, Azure, Google Cloud, paid API" in guide
    assert "不使用 AWS、Azure、Google Cloud、付费 API" in guide
    assert "127.0.0.1" in guide
    assert "15 MiB" in guide
    assert "40 megapixels" in guide
    assert "4000 万像素" in guide
    assert "inspection-manifest.json" in guide
    assert "Maintenance-review priority, not a road-safety verdict" in guide
    assert "维护复核优先级，不是道路安全判定" in guide
    assert "Lesson 11" in learning
    assert "inspections/" in results
