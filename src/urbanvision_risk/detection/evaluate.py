from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from urbanvision_risk.data.voc import DETECTION_CLASS_INFO
from urbanvision_risk.detection.config import validate_run_name
from urbanvision_risk.errors import ProjectError, report_error
from urbanvision_risk.paths import ProjectPaths, get_paths


def _number(value: Any) -> float:
    if hasattr(value, "item"):
        value = value.item()
    return float(value)


def metrics_payload(metrics: Any) -> dict[str, object]:
    box = metrics.box
    class_positions = {
        int(class_index): position for position, class_index in enumerate(box.ap_class_index)
    }
    per_class: dict[str, dict[str, float | str | None]] = {}
    for class_index, details in DETECTION_CLASS_INFO.items():
        position = class_positions.get(class_index)
        if position is None:
            per_class[details["code"]] = {
                "status": "no_ground_truth_instances",
                "precision": None,
                "recall": None,
                "f1": None,
                "mAP50": None,
                "mAP50-95": None,
            }
            continue
        precision = _number(box.p[position])
        recall = _number(box.r[position])
        denominator = precision + recall
        per_class[details["code"]] = {
            "status": "evaluated",
            "precision": precision,
            "recall": recall,
            "f1": 0.0 if denominator == 0 else 2 * precision * recall / denominator,
            "mAP50": _number(box.ap50[position]),
            "mAP50-95": _number(box.maps[class_index]),
        }
    overall_precision = _number(box.mp)
    overall_recall = _number(box.mr)
    denominator = overall_precision + overall_recall
    return {
        "overall": {
            "precision": overall_precision,
            "recall": overall_recall,
            "f1": (
                0.0 if denominator == 0 else 2 * overall_precision * overall_recall / denominator
            ),
            "mAP50": _number(box.map50),
            "mAP50-95": _number(box.map),
        },
        "per_class": per_class,
    }


def evaluate_run(
    run_name: str,
    paths: ProjectPaths | None = None,
    model_factory: Callable[[str], Any] | None = None,
) -> Path:
    active_paths = paths or get_paths()
    validate_run_name(run_name)
    run_dir = active_paths.experiments / run_name
    checkpoint = run_dir / "weights" / "best.pt"
    dataset_yaml = run_dir / "dataset-resolved.yaml"
    summary_path = run_dir / "training_summary.json"
    for required in (checkpoint, dataset_yaml, summary_path):
        if not required.is_file():
            raise ProjectError(
                "E301",
                "评估所需文件不存在",
                "A required evaluation file is missing",
                "确认基线训练完整结束",
                "Confirm that baseline training completed",
                str(required),
            )

    output_dir = active_paths.evaluations / run_name
    try:
        output_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise ProjectError(
            "E204",
            "评估目录已经存在",
            "Evaluation directory already exists",
            "保留已有评估；如需新评估请使用新的训练运行名",
            "Keep it; use a new training run name for another evaluation",
            str(output_dir),
        ) from error

    factory = model_factory
    if factory is None:
        from ultralytics import YOLO

        factory = YOLO
    model = factory(str(checkpoint))
    metrics = model.val(
        data=str(dataset_yaml),
        split="test",
        device="mps",
        project=str(active_paths.evaluations),
        name=run_name,
        exist_ok=True,
        plots=True,
    )
    payload = metrics_payload(metrics)
    evaluation_path = output_dir / "evaluation.json"
    evaluation_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["held_out_test_metrics"] = payload
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return evaluation_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate UrbanVision-Risk / 评估道路缺陷模型")
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    try:
        output = evaluate_run(args.run_name)
        print(f"[PASS] 留出测试评估完成 / Held-out evaluation complete: {output}")
        return 0
    except ProjectError as error:
        return report_error(error, debug=args.debug)


if __name__ == "__main__":
    raise SystemExit(main())
