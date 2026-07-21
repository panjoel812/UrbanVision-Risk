from pathlib import Path

import pytest

from urbanvision_risk.detection.config import load_training_profile, validate_run_name
from urbanvision_risk.errors import ProjectError


def test_load_smoke_profile_from_committed_config() -> None:
    configs = Path(__file__).resolve().parents[1] / "configs"

    profile = load_training_profile("smoke", configs)

    assert profile.model == "yolo26n.pt"
    assert profile.epochs == 1
    assert profile.batch == 4
    assert profile.device == "mps"
    assert profile.fraction == 0.1


@pytest.mark.parametrize("name", ["../escape", "Bad Name", "", "a" * 65])
def test_invalid_run_names_are_rejected(name: str) -> None:
    with pytest.raises(ProjectError, match="E302"):
        validate_run_name(name)
