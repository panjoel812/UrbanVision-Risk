from pathlib import Path
from types import SimpleNamespace

from urbanvision_risk.environment import inspect_environment
from urbanvision_risk.paths import get_paths


class FakeTensor:
    def __mul__(self, value: int) -> "FakeTensor":
        assert value == 2
        return self


def fake_torch(*, built: bool, available: bool) -> SimpleNamespace:
    backend = SimpleNamespace(is_built=lambda: built, is_available=lambda: available)
    mps = SimpleNamespace(synchronize=lambda: None)
    return SimpleNamespace(
        __version__="test",
        backends=SimpleNamespace(mps=backend),
        mps=mps,
        ones=lambda size, device: FakeTensor()
        if size == 2 and device == "mps"
        else None,
    )


def test_supported_python_and_mps_pass(tmp_path: Path) -> None:
    report = inspect_environment(
        version=(3, 11, 9),
        torch_module=fake_torch(built=True, available=True),
        paths=get_paths(tmp_path),
    )

    assert report.ok is True
    assert [check.code for check in report.checks] == [
        "PYTHON",
        "ROOT",
        "TORCH",
        "MPS",
    ]
    assert all(check.passed for check in report.checks)


def test_wrong_python_reports_e101(tmp_path: Path) -> None:
    report = inspect_environment(
        version=(3, 9, 6),
        torch_module=fake_torch(built=True, available=True),
        paths=get_paths(tmp_path),
    )

    assert report.ok is False
    assert report.error_code == "E101"


def test_unavailable_mps_reports_e102(tmp_path: Path) -> None:
    report = inspect_environment(
        version=(3, 11, 9),
        torch_module=fake_torch(built=True, available=False),
        paths=get_paths(tmp_path),
    )

    assert report.ok is False
    assert report.error_code == "E102"
