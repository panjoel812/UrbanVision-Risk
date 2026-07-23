from pathlib import Path

import pytest

from urbanvision_risk.errors import ProjectError, report_error
from urbanvision_risk.paths import get_paths


def test_project_error_renders_bilingual_message() -> None:
    error = ProjectError(
        code="E201",
        message_zh="数据不存在",
        message_en="Data is missing",
        recovery_zh="检查路径",
        recovery_en="Check the path",
        context="/tmp/example",
    )

    rendered = str(error)

    assert "[ERROR E201]" in rendered
    assert "数据不存在" in rendered
    assert "Data is missing" in rendered
    assert "检查路径" in rendered
    assert "Check the path" in rendered
    assert "/tmp/example" in rendered


def test_report_error_prints_normally_and_reraises_in_debug(
    capsys: pytest.CaptureFixture[str],
) -> None:
    error = ProjectError("E201", "缺少数据", "Data missing", "检查路径", "Check path")

    assert report_error(error) == 1
    assert "[ERROR E201]" in capsys.readouterr().out
    with pytest.raises(ProjectError):
        report_error(error, debug=True)


def test_get_paths_uses_supplied_repository_root(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)

    assert paths.root == tmp_path.resolve()
    assert paths.data == tmp_path.resolve() / "data"
    assert paths.downloads == tmp_path.resolve() / "data" / "downloads"
    assert paths.raw == tmp_path.resolve() / "data" / "raw"
    assert paths.processed == tmp_path.resolve() / "data" / "processed"
    assert paths.experiments == tmp_path.resolve() / "results" / "experiments"


def test_get_paths_exposes_risk_results(tmp_path: Path) -> None:
    assert get_paths(tmp_path).risks == tmp_path / "results" / "risks"


def test_get_paths_exposes_v1_inspection_results(tmp_path: Path) -> None:
    assert get_paths(tmp_path).inspections == tmp_path / "results" / "inspections"


def test_get_paths_exposes_v3_metrology_results(tmp_path: Path) -> None:
    assert get_paths(tmp_path).metrology == tmp_path / "results" / "metrology"
