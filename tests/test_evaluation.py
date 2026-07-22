import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from urbanvision_risk.detection.evaluate import evaluate_run, metrics_payload
from urbanvision_risk.errors import ProjectError
from urbanvision_risk.paths import get_paths


def _metrics() -> SimpleNamespace:
    return SimpleNamespace(
        box=SimpleNamespace(
            mp=0.5,
            mr=0.4,
            map50=0.45,
            map=0.3,
            ap_class_index=[0, 1, 2, 3],
            p=[0.1, 0.2, 0.3, 0.4],
            r=[0.2, 0.3, 0.4, 0.5],
            ap50=[0.15, 0.25, 0.35, 0.45],
            maps=[0.1, 0.2, 0.3, 0.4],
        )
    )


def test_metrics_payload_contains_overall_and_per_class_values() -> None:
    payload = metrics_payload(_metrics())

    assert payload["overall"]["mAP50"] == 0.45
    assert payload["per_class"]["D40"]["precision"] == 0.4
    assert payload["per_class"]["D00"]["f1"] == pytest.approx(0.1333333333)
    assert payload["per_class"]["Repair"]["status"] == "no_ground_truth_instances"


def test_evaluate_run_requires_best_checkpoint(tmp_path: Path) -> None:
    run_dir = get_paths(tmp_path).experiments / "china-baseline-001"
    run_dir.mkdir(parents=True)

    with pytest.raises(ProjectError, match="E301"):
        evaluate_run(
            "china-baseline-001",
            paths=get_paths(tmp_path),
            model_factory=lambda _: None,
        )


def test_evaluate_run_writes_metrics_and_updates_training_summary(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)
    run_dir = paths.experiments / "china-baseline-001"
    weights_dir = run_dir / "weights"
    weights_dir.mkdir(parents=True)
    (weights_dir / "best.pt").write_bytes(b"checkpoint")
    (run_dir / "dataset-resolved.yaml").write_text("path: dataset\n", encoding="utf-8")
    summary_path = run_dir / "training_summary.json"
    summary_path.write_text('{"run_name": "china-baseline-001"}\n', encoding="utf-8")

    calls: dict[str, object] = {}

    class FakeModel:
        def val(self, **kwargs: object) -> SimpleNamespace:
            calls.update(kwargs)
            return _metrics()

    output = evaluate_run(
        "china-baseline-001",
        paths=paths,
        model_factory=lambda checkpoint: FakeModel(),
    )

    evaluation = json.loads(output.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert evaluation["overall"]["mAP50-95"] == 0.3
    assert summary["held_out_test_metrics"] == evaluation
    assert calls["split"] == "test"
    assert calls["device"] == "mps"
