from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any

from urbanvision_risk.paths import ProjectPaths, get_paths


@dataclass(frozen=True, slots=True)
class CheckResult:
    code: str
    passed: bool
    message_zh: str
    message_en: str


@dataclass(frozen=True, slots=True)
class EnvironmentReport:
    checks: tuple[CheckResult, ...]
    error_code: str | None = None

    @property
    def ok(self) -> bool:
        return self.error_code is None and all(check.passed for check in self.checks)


def inspect_environment(
    version: tuple[int, int, int] | None = None,
    torch_module: Any | None = None,
    paths: ProjectPaths | None = None,
) -> EnvironmentReport:
    active_version = version or sys.version_info[:3]
    active_paths = paths or get_paths()
    checks: list[CheckResult] = []

    python_ok = active_version[:2] == (3, 11)
    checks.append(
        CheckResult(
            code="PYTHON",
            passed=python_ok,
            message_zh=f"Python 版本: {'.'.join(map(str, active_version))}",
            message_en=f"Python version: {'.'.join(map(str, active_version))}",
        )
    )
    if not python_ok:
        return EnvironmentReport(tuple(checks), error_code="E101")

    managed_paths = (
        active_paths.configs,
        active_paths.data,
        active_paths.downloads,
        active_paths.raw,
        active_paths.processed,
        active_paths.models,
        active_paths.results,
        active_paths.experiments,
        active_paths.evaluations,
        active_paths.predictions,
    )
    root_ok = active_paths.root.is_dir() and all(
        path.resolve().is_relative_to(active_paths.root) for path in managed_paths
    )
    checks.append(
        CheckResult(
            code="ROOT",
            passed=root_ok,
            message_zh=f"项目根目录: {active_paths.root}",
            message_en=f"Project root: {active_paths.root}",
        )
    )

    if torch_module is None:
        import torch as torch_module

    checks.append(
        CheckResult(
            code="TORCH",
            passed=True,
            message_zh=f"PyTorch 版本: {torch_module.__version__}",
            message_en=f"PyTorch version: {torch_module.__version__}",
        )
    )

    built = bool(torch_module.backends.mps.is_built())
    available = bool(torch_module.backends.mps.is_available())
    tensor_ok = False
    if built and available:
        try:
            tensor = torch_module.ones(2, device="mps")
            _ = tensor * 2
            torch_module.mps.synchronize()
            tensor_ok = True
        except RuntimeError:
            tensor_ok = False

    mps_ok = built and available and tensor_ok
    checks.append(
        CheckResult(
            code="MPS",
            passed=mps_ok,
            message_zh=f"MPS 已构建={built}, 可用={available}, 张量测试={tensor_ok}",
            message_en=(f"MPS built={built}, available={available}, tensor test={tensor_ok}"),
        )
    )
    return EnvironmentReport(tuple(checks), error_code=None if mps_ok else "E102")


def main() -> int:
    report = inspect_environment()
    for check in report.checks:
        prefix = "PASS" if check.passed else "FAIL"
        print(f"[{prefix}] {check.message_zh} / {check.message_en}")
    if report.ok:
        print("[PASS] 环境准备完成 / Environment is ready")
        return 0
    if report.error_code == "E101":
        print("[ERROR E101] 请使用 uv 管理的 Python 3.11 / Use uv-managed Python 3.11")
    else:
        print(
            "[ERROR E102] MPS 不可用且未回退到 CPU / MPS is unavailable; CPU fallback is disabled"
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
