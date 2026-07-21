import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from urbanvision_risk.detection.train import train_experiment
from urbanvision_risk.errors import ProjectError
from urbanvision_risk.paths import get_paths


class FakeResult:
    def __init__(self) -> None:
        self.results_dict = {"metrics/mAP50(B)": 0.25}


class FakeModel:
    def __init__(self, checkpoint: str) -> None:
        assert checkpoint == "yolo26n.pt"

    def train(self, **kwargs: Any) -> FakeResult:
        run_dir = Path(kwargs["project"]) / kwargs["name"]
        weights = run_dir / "weights"
        weights.mkdir(parents=True, exist_ok=True)
        (weights / "best.pt").write_bytes(b"best")
        (weights / "last.pt").write_bytes(b"last")
        (run_dir / "results.csv").write_text(
            "epoch,map50\n0,0.25\n",
            encoding="utf-8",
        )
        return FakeResult()


def write_training_fixture(root: Path) -> None:
    configs = root / "configs"
    processed = root / "data" / "processed" / "rdd2022-china-motorbike"
    configs.mkdir(parents=True)
    processed.mkdir(parents=True)
    (processed / "manifest.json").write_text(
        json.dumps({"input_digest": "a" * 64}),
        encoding="utf-8",
    )
    (configs / "dataset-rdd2022-china-motorbike.yaml").write_text(
        yaml.safe_dump(
            {
                "path": "data/processed/rdd2022-china-motorbike",
                "train": "images/train",
                "val": "images/val",
                "test": "images/test",
                "names": {0: "D00", 1: "D10", 2: "D20", 3: "D40"},
            }
        ),
        encoding="utf-8",
    )
    (configs / "train-smoke.yaml").write_text(
        yaml.safe_dump(
            {
                "model": "yolo26n.pt",
                "epochs": 1,
                "imgsz": 640,
                "batch": 4,
                "device": "mps",
                "workers": 2,
                "seed": 42,
                "deterministic": True,
                "cache": False,
                "fraction": 0.1,
            }
        ),
        encoding="utf-8",
    )


def test_train_experiment_writes_summary_and_weights(tmp_path: Path) -> None:
    write_training_fixture(tmp_path)

    run_dir = train_experiment(
        "smoke",
        "smoke-test-001",
        paths=get_paths(tmp_path),
        model_factory=FakeModel,
        git_commit_resolver=lambda _root: "test-commit",
    )

    summary = json.loads((run_dir / "training_summary.json").read_text(encoding="utf-8"))
    assert (run_dir / "weights" / "best.pt").is_file()
    assert summary["run_name"] == "smoke-test-001"
    assert summary["dataset_manifest_digest"] == "a" * 64
    assert summary["metrics"]["metrics/mAP50(B)"] == 0.25


def test_train_experiment_refuses_existing_run(tmp_path: Path) -> None:
    write_training_fixture(tmp_path)
    run_dir = get_paths(tmp_path).experiments / "smoke-test-001"
    run_dir.mkdir(parents=True)

    with pytest.raises(ProjectError, match="E204"):
        train_experiment(
            "smoke",
            "smoke-test-001",
            paths=get_paths(tmp_path),
            model_factory=FakeModel,
        )
