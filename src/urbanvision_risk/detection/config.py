from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

from urbanvision_risk.errors import ProjectError

RUN_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


@dataclass(frozen=True, slots=True)
class TrainingProfile:
    model: str
    epochs: int
    imgsz: int
    batch: int
    device: str
    workers: int
    seed: int
    deterministic: bool
    cache: bool
    fraction: float

    def as_train_kwargs(self) -> dict[str, object]:
        values = asdict(self)
        values.pop("model")
        return values


def validate_run_name(name: str) -> str:
    if not RUN_NAME_PATTERN.fullmatch(name):
        raise ProjectError(
            "E302",
            "运行名称不合法",
            "Run name is invalid",
            "使用 1-64 位小写字母、数字和连字符",
            "Use 1-64 lowercase letters, digits, and hyphens",
            name,
        )
    return name


def load_training_profile(name: str, configs_dir: Path) -> TrainingProfile:
    path = configs_dir / f"train-{name}.yaml"
    if not path.is_file():
        raise ProjectError(
            "E302",
            "训练配置不存在",
            "Training profile does not exist",
            "使用 smoke 或 baseline",
            "Use smoke or baseline",
            str(path),
        )
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ProjectError(
            "E302",
            "训练配置不是映射",
            "Training profile is not a mapping",
            "检查 YAML",
            "Inspect the YAML",
            str(path),
        )
    required = {
        "model",
        "epochs",
        "imgsz",
        "batch",
        "device",
        "workers",
        "seed",
        "deterministic",
        "cache",
        "fraction",
    }
    if set(payload) != required:
        raise ProjectError(
            "E302",
            "训练配置字段不匹配",
            "Training-profile fields do not match",
            "恢复已提交的训练 YAML",
            "Restore the committed training YAML",
            f"expected={sorted(required)}, actual={sorted(payload)}",
        )
    profile = TrainingProfile(**payload)
    valid = (
        bool(profile.model.strip())
        and profile.model.endswith(".pt")
        and profile.epochs > 0
        and profile.imgsz > 0
        and profile.batch > 0
        and profile.device == "mps"
        and profile.workers >= 0
        and profile.seed == 42
        and profile.deterministic is True
        and profile.cache is False
        and 0 < profile.fraction <= 1
    )
    if not valid:
        raise ProjectError(
            "E302",
            "训练配置值不符合本地训练约束",
            "Training values violate the local-training constraints",
            "恢复已批准的 smoke 或 baseline 配置",
            "Restore the approved smoke or baseline profile",
            str(path),
        )
    return profile
