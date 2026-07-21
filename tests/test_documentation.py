from pathlib import Path

from PIL import Image

from urbanvision_risk.data.voc import parse_voc_annotation

ROOT = Path(__file__).resolve().parents[1]


def test_readme_contains_the_real_milestone_commands() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    commands = (
        "uv python install 3.11",
        "uv sync --extra dev",
        "uv run python -m urbanvision_risk.environment",
        "uv run python -m urbanvision_risk.data.download",
        "uv run python -m urbanvision_risk.data.prepare",
        "uv run python -m urbanvision_risk.data.validate",
        "--profile smoke --run-name smoke-test-001",
        "--profile baseline --run-name china-baseline-001",
        "urbanvision_risk.detection.evaluate",
        "urbanvision_risk.detection.predict",
    )
    assert all(command in readme for command in commands)
    assert "中文" in readme
    assert "English" in readme


def test_learning_guide_contains_eight_lessons() -> None:
    guide = (ROOT / "docs" / "learning-guide.md").read_text(encoding="utf-8")

    assert guide.count("## Lesson ") == 8
    assert guide.count("复习问题 / Review question") == 8


def test_committed_fixture_image_matches_xml() -> None:
    fixture_root = ROOT / "tests" / "fixtures"
    record = parse_voc_annotation(fixture_root / "sample.xml")
    with Image.open(fixture_root / "sample.jpg") as image:
        assert image.size == (record.width, record.height)
