from __future__ import annotations

import argparse
import importlib.metadata
import json
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from urbanvision_risk.detection.config import load_training_profile, validate_run_name
from urbanvision_risk.errors import ProjectError, report_error
from urbanvision_risk.paths import ProjectPaths, get_paths


def _json_scalar(value: Any) -> int | float | str | bool | None:
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    return str(value)


def _git_commit(root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _resolve_dataset_yaml(paths: ProjectPaths, destination: Path) -> None:
    source = paths.configs / "dataset-rdd2022-china-motorbike.yaml"
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    dataset_root = (paths.root / payload["path"]).resolve()
    manifest = dataset_root / "manifest.json"
    if not manifest.is_file():
        raise ProjectError(
            "E201",
            "处理后数据或清单不存在",
            "Prepared data or manifest is missing",
            "先运行 download、prepare 和 validate 命令",
            "Run download, prepare, and validate first",
            str(manifest),
        )
    payload["path"] = str(dataset_root)
    destination.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


def train_experiment(
    profile_name: str,
    run_name: str,
    paths: ProjectPaths | None = None,
    model_factory: Callable[[str], Any] | None = None,
    git_commit_resolver: Callable[[Path], str] = _git_commit,
) -> Path:
    active_paths = paths or get_paths()
    validate_run_name(run_name)
    profile = load_training_profile(profile_name, active_paths.configs)
    run_dir = active_paths.experiments / run_name
    try:
        run_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise ProjectError(
            "E204",
            "实验目录已经存在",
            "Experiment directory already exists",
            "使用新的运行名称；不要覆盖已有实验",
            "Use a new run name; do not overwrite an existing experiment",
            str(run_dir),
        ) from error

    resolved_dataset = run_dir / "dataset-resolved.yaml"
    _resolve_dataset_yaml(active_paths, resolved_dataset)
    manifest_path = (
        active_paths.processed / "rdd2022-china-motorbike" / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    factory = model_factory
    if factory is None:
        from ultralytics import YOLO

        factory = YOLO

    started_at = datetime.now(UTC)
    model = factory(profile.model)
    result = model.train(
        data=str(resolved_dataset),
        project=str(active_paths.experiments),
        name=run_name,
        exist_ok=True,
        **profile.as_train_kwargs(),
    )
    ended_at = datetime.now(UTC)
    metrics = {
        str(key): _json_scalar(value)
        for key, value in getattr(result, "results_dict", {}).items()
    }
    versions: dict[str, str] = {}
    for package in ("ultralytics", "torch", "opencv-python", "numpy"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not-installed"
    summary = {
        "run_name": run_name,
        "profile": profile_name,
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "git_commit": git_commit_resolver(active_paths.root),
        "dataset_manifest_digest": manifest["input_digest"],
        "model": profile.model,
        "parameters": profile.as_train_kwargs(),
        "device": profile.device,
        "library_versions": versions,
        "metrics": metrics,
    }
    (run_dir / "training_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return run_dir


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Train UrbanVision-Risk / 训练道路缺陷模型"
    )
    parser.add_argument("--profile", choices=("smoke", "baseline"), required=True)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    try:
        run_dir = train_experiment(args.profile, args.run_name)
        print(f"[PASS] 训练完成 / Training complete: {run_dir}")
        return 0
    except ProjectError as error:
        return report_error(error, debug=args.debug)


if __name__ == "__main__":
    raise SystemExit(main())
