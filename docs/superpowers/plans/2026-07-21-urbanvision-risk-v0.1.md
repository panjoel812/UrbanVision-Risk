# UrbanVision-Risk v0.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully local, bilingual, reproducible RDD2022-to-YOLO26n road-damage training, evaluation, and prediction pipeline for a 24 GB Apple Silicon MacBook Pro.

**Architecture:** A project-scoped Python package separates environment checks, immutable data acquisition, VOC-to-YOLO preparation, dataset validation, model training, evaluation, and prediction. Commands exchange durable YAML/JSON artifacts, fail with stable bilingual error codes, and never silently overwrite or delete user data.

**Tech Stack:** Python 3.11, uv, PyTorch with Apple MPS, Ultralytics YOLO26n, OpenCV, Pillow, PyYAML, NumPy, pytest, Ruff, Git.

## Global Constraints

- Use Python `>=3.11,<3.12` through `uv`; never replace macOS `/usr/bin/python3`.
- Runtime dependencies are Ultralytics, PyTorch, OpenCV, Pillow, PyYAML, and NumPy; pytest and Ruff are installed through the `dev` optional dependency extra.
- Commit the fully resolved `uv.lock`; after it exists, reproduce with `uv sync --frozen --extra dev`.
- Use only the official approximately 183.1 MB `RDD2022_China_MotorBike` subset for v0.1.
- Preserve the immutable class mapping `0=D00`, `1=D10`, `2=D20`, `3=D40`.
- Split annotated image identifiers 80/10/10 after sorted input is shuffled by `random.Random(42)`.
- Keep `data/raw` immutable; write converted output only under `data/processed`.
- Reject absolute and `..` ZIP members before extracting any archive entry.
- Never permanently delete files, modify raw data, or silently overwrite processed data or experiments.
- If removal is required, instruct the learner to use `/usr/bin/trash <absolute-path>`.
- Use `yolo26n.pt`; smoke profile is 1 epoch, image size 640, batch 4, MPS, 2 workers, seed 42, deterministic mode, no cache, fraction 0.1.
- Baseline profile is 30 epochs, image size 640, batch 8, MPS, 2 workers, seed 42, deterministic mode, no cache, fraction 1.0.
- Do not silently fall back from MPS to CPU.
- All learner-facing commands, pass/fail messages, recovery instructions, README content, and lessons are bilingual Chinese/English.
- Use repository-relative defaults that remain correct regardless of the caller's current working directory.
- Use `AGPL-3.0-or-later` for repository code; do not redistribute RDD2022.
- Do not add the Web dashboard, risk engine, local LLM, GIS, multi-country training, or commercial distribution to v0.1.

---

## File Responsibility Map

| File | Single responsibility |
|---|---|
| `.python-version` | Select Python 3.11 for uv. |
| `pyproject.toml` | Declare package metadata, dependencies, pytest, and Ruff settings. |
| `.gitignore` | Exclude generated environments, data, weights, and experiment artifacts. |
| `LICENSE` | State the AGPL-3.0-or-later license and canonical license URL. |
| `src/urbanvision_risk/errors.py` | Define stable bilingual project errors. |
| `src/urbanvision_risk/paths.py` | Resolve all repository-relative paths. |
| `src/urbanvision_risk/environment.py` | Inspect Python, project paths, PyTorch, and MPS. |
| `src/urbanvision_risk/data/voc.py` | Parse and convert one Pascal VOC annotation. |
| `src/urbanvision_risk/data/split.py` | Produce deterministic disjoint dataset splits. |
| `src/urbanvision_risk/data/download.py` | Stream the official archive and safely extract it. |
| `src/urbanvision_risk/data/validate.py` | Validate prepared images, labels, splits, and counts. |
| `src/urbanvision_risk/data/prepare.py` | Orchestrate pairing, splitting, copying, conversion, validation, and manifest writing. |
| `src/urbanvision_risk/detection/config.py` | Load and validate training profiles and dataset configuration. |
| `src/urbanvision_risk/detection/train.py` | Run one uniquely named Ultralytics training experiment. |
| `src/urbanvision_risk/detection/evaluate.py` | Evaluate `best.pt` on the held-out local test split. |
| `src/urbanvision_risk/detection/predict.py` | Save annotated predictions and structured JSON. |
| `configs/*.yaml` | Store accepted dataset and training settings. |
| `README.md` | Provide the concise bilingual milestone path. |
| `docs/learning-guide.md` | Teach the eight approved beginner lessons. |
| `data/README.md` | Explain local data directories and data citation. |
| `models/README.md` | Explain weight caching and generated checkpoints. |
| `results/README.md` | Explain experiment, evaluation, and prediction artifacts. |

---

### Task 1: Reproducible Project Foundation

**Files:**
- Create: `.python-version`
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `LICENSE`
- Create: `README.md`
- Create: `src/urbanvision_risk/__init__.py`
- Create: `src/urbanvision_risk/errors.py`
- Create: `src/urbanvision_risk/paths.py`
- Create: `tests/test_foundation.py`
- Generate: `uv.lock`

**Interfaces:**
- Consumes: repository root containing `docs/superpowers/specs/2026-07-21-urbanvision-risk-v0.1-design.md`.
- Produces: `ProjectError(code: str, message_zh: str, message_en: str, recovery_zh: str, recovery_en: str, context: str | None = None)`; `report_error(error: ProjectError, debug: bool = False) -> int`; `ProjectPaths`; `get_paths(root: Path | None = None) -> ProjectPaths`; installable package `urbanvision-risk`.

- [ ] **Step 1: Create project metadata before dependency installation**

Create `.python-version`:

```text
3.11
```

Create `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling>=1.27,<2"]
build-backend = "hatchling.build"

[project]
name = "urbanvision-risk"
version = "0.1.0"
description = "Fully local road-damage detection and risk-research foundation"
readme = "README.md"
requires-python = ">=3.11,<3.12"
license = { text = "AGPL-3.0-or-later" }
authors = [{ name = "UrbanVision-Risk Contributors" }]
dependencies = [
  "numpy>=2.0,<3",
  "opencv-python>=4.10,<5",
  "pillow>=11,<13",
  "pyyaml>=6,<7",
  "torch>=2.7,<3",
  "ultralytics>=8.4,<9",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.4,<10",
  "ruff>=0.12,<1",
]

[tool.hatch.build.targets.wheel]
packages = ["src/urbanvision_risk"]

[tool.pytest.ini_options]
addopts = "-ra"
testpaths = ["tests"]

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "RUF"]
```

Create `.gitignore`:

```gitignore
.DS_Store
.venv/
.pytest_cache/
.ruff_cache/
__pycache__/
*.py[cod]
*.egg-info/

data/downloads/
data/raw/
data/processed/
models/checkpoints/
models/cache/
results/experiments/
results/evaluations/
results/predictions/
*.pt
*.part
```

Create `LICENSE`:

```text
UrbanVision-Risk
Copyright (C) 2026 UrbanVision-Risk Contributors

SPDX-License-Identifier: AGPL-3.0-or-later

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or any later version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. The complete license text is available at:
https://www.gnu.org/licenses/agpl-3.0.txt
```

Create the initial `README.md` required by the package metadata:

```markdown
# UrbanVision-Risk

**中文：** UrbanVision-Risk v0.1 是一个完全本地运行的道路缺陷检测学习项目，使用 RDD2022、YOLO26n 和 Apple MPS。

**English:** UrbanVision-Risk v0.1 is a fully local road-damage detection learning project using RDD2022, YOLO26n, and Apple MPS.

The approved design is documented in `docs/superpowers/specs/2026-07-21-urbanvision-risk-v0.1-design.md`.

已批准设计位于 `docs/superpowers/specs/2026-07-21-urbanvision-risk-v0.1-design.md`。
```

Create `src/urbanvision_risk/__init__.py`:

```python
"""UrbanVision-Risk local road-damage detection package."""

__version__ = "0.1.0"
```

- [ ] **Step 2: Let the learner create Python 3.11 and the locked environment**

Run:

```bash
uv python install 3.11
uv sync --extra dev
```

Expected: uv selects a Python 3.11 interpreter, creates `.venv`, installs the runtime and development dependencies, and writes `uv.lock`. It must not change `/usr/bin/python3`.

- [ ] **Step 3: Write the failing foundation tests**

Create `tests/test_foundation.py`:

```python
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

    assert "[E201]" in rendered
    assert "数据不存在" in rendered
    assert "Data is missing" in rendered
    assert "检查路径" in rendered
    assert "Check the path" in rendered
    assert "/tmp/example" in rendered


def test_report_error_prints_normally_and_reraises_in_debug(capsys: pytest.CaptureFixture[str]) -> None:
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
```

- [ ] **Step 4: Run the foundation tests and verify the intended failure**

Run: `uv run pytest tests/test_foundation.py -v`

Expected: FAIL during collection with `ModuleNotFoundError` for `urbanvision_risk.errors` or `urbanvision_risk.paths`.

- [ ] **Step 5: Implement stable bilingual errors and path resolution**

Create `src/urbanvision_risk/errors.py`:

```python
from dataclasses import dataclass


@dataclass(slots=True)
class ProjectError(Exception):
    code: str
    message_zh: str
    message_en: str
    recovery_zh: str
    recovery_en: str
    context: str | None = None

    def __str__(self) -> str:
        lines = [
            f"[ERROR {self.code}] {self.message_zh}",
            self.message_en,
        ]
        if self.context:
            lines.append(f"Context / 上下文: {self.context}")
        lines.extend(
            [
                f"恢复方法 / Recovery: {self.recovery_zh}",
                self.recovery_en,
            ]
        )
        return "\n".join(lines)


def report_error(error: ProjectError, debug: bool = False) -> int:
    if debug:
        raise error
    print(error)
    return 1
```

Create `src/urbanvision_risk/paths.py`:

```python
from dataclasses import dataclass
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]


@dataclass(frozen=True, slots=True)
class ProjectPaths:
    root: Path
    configs: Path
    data: Path
    downloads: Path
    raw: Path
    processed: Path
    models: Path
    results: Path
    experiments: Path
    evaluations: Path
    predictions: Path


def get_paths(root: Path | None = None) -> ProjectPaths:
    resolved_root = (root or REPOSITORY_ROOT).resolve()
    data = resolved_root / "data"
    results = resolved_root / "results"
    return ProjectPaths(
        root=resolved_root,
        configs=resolved_root / "configs",
        data=data,
        downloads=data / "downloads",
        raw=data / "raw",
        processed=data / "processed",
        models=resolved_root / "models",
        results=results,
        experiments=results / "experiments",
        evaluations=results / "evaluations",
        predictions=results / "predictions",
    )
```

- [ ] **Step 6: Run foundation verification**

Run:

```bash
uv run pytest tests/test_foundation.py -v
uv run ruff check src/urbanvision_risk tests/test_foundation.py
```

Expected: 3 tests PASS and Ruff exits with `All checks passed!`.

- [ ] **Step 7: Commit the reproducible foundation**

```bash
git add .python-version pyproject.toml uv.lock .gitignore LICENSE README.md src/urbanvision_risk tests/test_foundation.py
git commit -m "build: establish reproducible Python project"
```

---

### Task 2: Bilingual Python and Apple MPS Environment Check

**Files:**
- Create: `src/urbanvision_risk/environment.py`
- Create: `tests/test_environment.py`

**Interfaces:**
- Consumes: `ProjectError`, `ProjectPaths`, `get_paths()` from Task 1; an optional PyTorch-compatible probe for unit tests.
- Produces: `CheckResult`; `EnvironmentReport`; `inspect_environment(version: tuple[int, int, int] | None = None, torch_module: Any | None = None, paths: ProjectPaths | None = None) -> EnvironmentReport`; `main() -> int`.

- [ ] **Step 1: Write failing environment tests with a fake MPS probe**

Create `tests/test_environment.py`:

```python
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
        ones=lambda size, device: FakeTensor() if size == 2 and device == "mps" else None,
    )


def test_supported_python_and_mps_pass(tmp_path: Path) -> None:
    report = inspect_environment(
        version=(3, 11, 9),
        torch_module=fake_torch(built=True, available=True),
        paths=get_paths(tmp_path),
    )

    assert report.ok is True
    assert [check.code for check in report.checks] == ["PYTHON", "ROOT", "TORCH", "MPS"]
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
```

- [ ] **Step 2: Run the environment tests and verify they fail**

Run: `uv run pytest tests/test_environment.py -v`

Expected: FAIL during collection because `urbanvision_risk.environment` does not exist.

- [ ] **Step 3: Implement environment inspection and bilingual CLI output**

Create `src/urbanvision_risk/environment.py`:

```python
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
            message_zh=f"MPS 已构建={built}，可用={available}，张量测试={tensor_ok}",
            message_en=f"MPS built={built}, available={available}, tensor test={tensor_ok}",
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
        print("[ERROR E102] MPS 不可用且未回退到 CPU / MPS is unavailable; CPU fallback is disabled")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run unit tests and static checks**

Run:

```bash
uv run pytest tests/test_environment.py -v
uv run ruff check src/urbanvision_risk/environment.py tests/test_environment.py
```

Expected: 3 tests PASS and Ruff exits successfully.

- [ ] **Step 5: Learner checkpoint — run the real environment check**

Run: `uv run python -m urbanvision_risk.environment`

Expected on the target Mac: four `[PASS]` lines followed by `[PASS] 环境准备完成 / Environment is ready`. If E101 or E102 appears, stop and diagnose before any dataset download.

- [ ] **Step 6: Commit the environment checker**

```bash
git add src/urbanvision_risk/environment.py tests/test_environment.py
git commit -m "feat: add bilingual MPS environment check"
```

---

### Task 3: Pascal VOC Conversion and Deterministic Splitting

**Files:**
- Create: `src/urbanvision_risk/data/__init__.py`
- Create: `src/urbanvision_risk/data/voc.py`
- Create: `src/urbanvision_risk/data/split.py`
- Create: `tests/test_voc_conversion.py`
- Create: `tests/test_dataset_split.py`

**Interfaces:**
- Consumes: `ProjectError` from Task 1.
- Produces: `CLASS_INFO`; `CLASS_TO_INDEX`; `VocObject`; `VocRecord`; `parse_voc_annotation(path: Path) -> VocRecord`; `voc_box_to_yolo(box: tuple[float, float, float, float], image_size: tuple[int, int]) -> tuple[float, float, float, float]`; `to_yolo_lines(record: VocRecord) -> list[str]`; `DatasetSplit`; `split_ids(ids: Sequence[str], seed: int = 42, val_ratio: float = 0.1, test_ratio: float = 0.1) -> DatasetSplit`.

- [ ] **Step 1: Write failing VOC conversion tests**

Create `tests/test_voc_conversion.py`:

```python
from pathlib import Path

import pytest

from urbanvision_risk.data.voc import parse_voc_annotation, to_yolo_lines, voc_box_to_yolo
from urbanvision_risk.errors import ProjectError


VALID_XML = """\
<annotation>
  <filename>road.jpg</filename>
  <size><width>400</width><height>200</height></size>
  <object>
    <name>D40</name>
    <bndbox><xmin>100</xmin><ymin>50</ymin><xmax>300</xmax><ymax>150</ymax></bndbox>
  </object>
</annotation>
"""


def test_parse_and_convert_valid_voc(tmp_path: Path) -> None:
    xml_path = tmp_path / "road.xml"
    xml_path.write_text(VALID_XML, encoding="utf-8")

    record = parse_voc_annotation(xml_path)

    assert record.filename == "road.jpg"
    assert record.width == 400
    assert record.height == 200
    assert to_yolo_lines(record) == ["3 0.500000 0.500000 0.500000 0.500000"]


def test_voc_box_rejects_zero_width() -> None:
    with pytest.raises(ProjectError, match="E203"):
        voc_box_to_yolo((100, 10, 100, 50), (400, 200))


def test_parser_rejects_unknown_class(tmp_path: Path) -> None:
    xml_path = tmp_path / "unknown.xml"
    xml_path.write_text(VALID_XML.replace("D40", "D99"), encoding="utf-8")

    with pytest.raises(ProjectError, match="E203"):
        parse_voc_annotation(xml_path)


def test_parser_rejects_malformed_xml(tmp_path: Path) -> None:
    xml_path = tmp_path / "broken.xml"
    xml_path.write_text("<annotation><filename>road.jpg", encoding="utf-8")

    with pytest.raises(ProjectError, match="E202"):
        parse_voc_annotation(xml_path)
```

- [ ] **Step 2: Write failing deterministic split tests**

Create `tests/test_dataset_split.py`:

```python
import pytest

from urbanvision_risk.data.split import split_ids


def test_split_is_deterministic_and_disjoint() -> None:
    identifiers = [f"image-{index:02d}" for index in range(20)]

    first = split_ids(identifiers)
    second = split_ids(reversed(identifiers))

    assert first == second
    assert len(first.train) == 16
    assert len(first.val) == 2
    assert len(first.test) == 2
    assert set(first.train).isdisjoint(first.val)
    assert set(first.train).isdisjoint(first.test)
    assert set(first.val).isdisjoint(first.test)


def test_split_rejects_duplicate_identifiers() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        split_ids(["same", "same"])
```

- [ ] **Step 3: Run both test files and verify they fail**

Run: `uv run pytest tests/test_voc_conversion.py tests/test_dataset_split.py -v`

Expected: FAIL during collection because `urbanvision_risk.data.voc` and `urbanvision_risk.data.split` do not exist.

- [ ] **Step 4: Implement Pascal VOC parsing and conversion**

Create `src/urbanvision_risk/data/__init__.py`:

```python
"""RDD2022 acquisition, conversion, and validation."""
```

Create `src/urbanvision_risk/data/voc.py`:

```python
from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from urbanvision_risk.errors import ProjectError


CLASS_INFO = {
    0: {"code": "D00", "name_en": "Longitudinal crack", "name_zh": "纵向裂缝"},
    1: {"code": "D10", "name_en": "Transverse crack", "name_zh": "横向裂缝"},
    2: {"code": "D20", "name_en": "Alligator crack", "name_zh": "网状裂缝"},
    3: {"code": "D40", "name_en": "Pothole", "name_zh": "坑洞"},
}
CLASS_TO_INDEX = {details["code"]: index for index, details in CLASS_INFO.items()}


@dataclass(frozen=True, slots=True)
class VocObject:
    class_code: str
    box: tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class VocRecord:
    filename: str
    width: int
    height: int
    objects: tuple[VocObject, ...]


def _required_text(parent: ET.Element, path: str, xml_path: Path) -> str:
    value = parent.findtext(path)
    if value is None or not value.strip():
        raise ProjectError(
            "E202",
            "XML 缺少必需字段",
            "XML is missing a required field",
            "检查或重新下载原始标注",
            "Inspect or redownload the source annotation",
            f"{xml_path}: {path}",
        )
    return value.strip()


def parse_voc_annotation(path: Path) -> VocRecord:
    try:
        root = ET.parse(path).getroot()
        filename = _required_text(root, "filename", path)
        width = int(_required_text(root, "size/width", path))
        height = int(_required_text(root, "size/height", path))
    except (ET.ParseError, ValueError) as error:
        raise ProjectError(
            "E202",
            "XML 标注损坏",
            "XML annotation is malformed",
            "检查或重新下载原始标注",
            "Inspect or redownload the source annotation",
            str(path),
        ) from error
    if width <= 0 or height <= 0:
        raise ProjectError(
            "E203",
            "图片尺寸非法",
            "Image dimensions are invalid",
            "检查 XML 的 size 字段",
            "Inspect the XML size fields",
            str(path),
        )

    objects: list[VocObject] = []
    for item in root.findall("object"):
        class_code = _required_text(item, "name", path)
        if class_code not in CLASS_TO_INDEX:
            raise ProjectError(
                "E203",
                "发现未知缺陷类别",
                "Unknown damage class found",
                "仅保留 D00、D10、D20、D40",
                "Keep only D00, D10, D20, and D40",
                f"{path}: {class_code}",
            )
        try:
            box = tuple(
                float(_required_text(item, f"bndbox/{coordinate}", path))
                for coordinate in ("xmin", "ymin", "xmax", "ymax")
            )
        except ValueError as error:
            raise ProjectError(
                "E203",
                "边界框坐标不是数字",
                "Bounding-box coordinates are not numeric",
                "检查 XML 的 bndbox 字段",
                "Inspect the XML bndbox fields",
                str(path),
            ) from error
        voc_box_to_yolo(box, (width, height))
        objects.append(VocObject(class_code=class_code, box=box))
    return VocRecord(filename=filename, width=width, height=height, objects=tuple(objects))


def voc_box_to_yolo(
    box: tuple[float, float, float, float],
    image_size: tuple[int, int],
) -> tuple[float, float, float, float]:
    xmin, ymin, xmax, ymax = box
    width, height = image_size
    values = (*box, float(width), float(height))
    if not all(math.isfinite(value) for value in values):
        valid = False
    else:
        valid = width > 0 and height > 0 and 0 <= xmin < xmax <= width and 0 <= ymin < ymax <= height
    if not valid:
        raise ProjectError(
            "E203",
            "边界框超界或尺寸为零",
            "Bounding box is out of bounds or has zero size",
            "检查 XML 坐标和图片尺寸",
            "Inspect XML coordinates and image dimensions",
            f"box={box}, image_size={image_size}",
        )
    return (
        ((xmin + xmax) / 2) / width,
        ((ymin + ymax) / 2) / height,
        (xmax - xmin) / width,
        (ymax - ymin) / height,
    )


def to_yolo_lines(record: VocRecord) -> list[str]:
    lines: list[str] = []
    for item in record.objects:
        normalized = voc_box_to_yolo(item.box, (record.width, record.height))
        values = " ".join(f"{value:.6f}" for value in normalized)
        lines.append(f"{CLASS_TO_INDEX[item.class_code]} {values}")
    return lines
```

- [ ] **Step 5: Implement deterministic splitting**

Create `src/urbanvision_risk/data/split.py`:

```python
import random
from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True, slots=True)
class DatasetSplit:
    train: tuple[str, ...]
    val: tuple[str, ...]
    test: tuple[str, ...]


def split_ids(
    ids: Sequence[str] | Iterable[str],
    seed: int = 42,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
) -> DatasetSplit:
    ordered = sorted(ids)
    if len(ordered) != len(set(ordered)):
        raise ValueError("duplicate identifiers are not allowed")
    if not ordered:
        raise ValueError("at least one identifier is required")
    if val_ratio < 0 or test_ratio < 0 or val_ratio + test_ratio >= 1:
        raise ValueError("validation and test ratios must be non-negative and sum to less than 1")

    shuffled = ordered.copy()
    random.Random(seed).shuffle(shuffled)
    val_count = round(len(shuffled) * val_ratio)
    test_count = round(len(shuffled) * test_ratio)
    train_count = len(shuffled) - val_count - test_count
    return DatasetSplit(
        train=tuple(shuffled[:train_count]),
        val=tuple(shuffled[train_count : train_count + val_count]),
        test=tuple(shuffled[train_count + val_count :]),
    )
```

- [ ] **Step 6: Run conversion and split verification**

Run:

```bash
uv run pytest tests/test_voc_conversion.py tests/test_dataset_split.py -v
uv run ruff check src/urbanvision_risk/data tests/test_voc_conversion.py tests/test_dataset_split.py
```

Expected: 6 tests PASS and Ruff exits successfully.

- [ ] **Step 7: Commit conversion and splitting**

```bash
git add src/urbanvision_risk/data tests/test_voc_conversion.py tests/test_dataset_split.py
git commit -m "feat: convert VOC labels and split datasets"
```

---
### Task 4: Official Archive Download and Safe Extraction

**Files:**
- Create: `src/urbanvision_risk/data/download.py`
- Create: `tests/test_download.py`

**Interfaces:**
- Consumes: `ProjectError` and `get_paths()` from Task 1.
- Produces: `RDD2022_CHINA_MOTORBIKE_URL`; `sha256_file(path: Path) -> str`; `download_file(url: str, destination: Path, opener: Callable[..., Any] = urlopen, chunk_size: int = 1024 * 1024) -> str`; `safe_extract_zip(archive: Path, destination: Path) -> tuple[Path, ...]`; `main() -> int`.

- [ ] **Step 1: Write failing download and ZIP-safety tests**

Create `tests/test_download.py`:

```python
import io
import zipfile
from pathlib import Path

import pytest

from urbanvision_risk.data.download import download_file, safe_extract_zip, sha256_file
from urbanvision_risk.errors import ProjectError


class Response(io.BytesIO):
    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def test_download_streams_to_final_file_and_returns_digest(tmp_path: Path) -> None:
    destination = tmp_path / "archive.zip"
    payload = b"urbanvision-test-payload"

    digest = download_file(
        "https://example.invalid/archive.zip",
        destination,
        opener=lambda _url: Response(payload),
        chunk_size=5,
    )

    assert destination.read_bytes() == payload
    assert digest == sha256_file(destination)
    assert not destination.with_suffix(".zip.part").exists()


def test_download_refuses_to_overwrite_existing_file(tmp_path: Path) -> None:
    destination = tmp_path / "archive.zip"
    destination.write_bytes(b"existing")

    with pytest.raises(ProjectError, match="E204"):
        download_file("https://example.invalid/archive.zip", destination)


def test_safe_extract_rejects_traversal_before_writing(tmp_path: Path) -> None:
    archive = tmp_path / "malicious.zip"
    destination = tmp_path / "raw"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("valid/file.txt", "valid")
        bundle.writestr("../escape.txt", "escape")

    with pytest.raises(ProjectError, match="E203"):
        safe_extract_zip(archive, destination)

    assert not destination.exists()
    assert not (tmp_path / "escape.txt").exists()


def test_safe_extract_writes_only_inside_destination(tmp_path: Path) -> None:
    archive = tmp_path / "valid.zip"
    destination = tmp_path / "raw"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("dataset/images/road.jpg", "image-bytes")

    extracted = safe_extract_zip(archive, destination)

    assert extracted == (destination / "dataset/images/road.jpg",)
    assert extracted[0].read_text(encoding="utf-8") == "image-bytes"
```

- [ ] **Step 2: Run the download tests and verify they fail**

Run: `uv run pytest tests/test_download.py -v`

Expected: FAIL during collection because `urbanvision_risk.data.download` does not exist.

- [ ] **Step 3: Implement streaming download, digesting, and prevalidated extraction**

Create `src/urbanvision_risk/data/download.py`:

```python
from __future__ import annotations

import argparse
import hashlib
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from urbanvision_risk.errors import ProjectError, report_error
from urbanvision_risk.paths import get_paths


RDD2022_CHINA_MOTORBIKE_URL = (
    "https://bigdatacup.s3.ap-northeast-1.amazonaws.com/"
    "RDD2022_China_MotorBike.zip"
)
ARCHIVE_NAME = "RDD2022_China_MotorBike.zip"
RAW_RELATIVE_PATH = Path("rdd2022/china-motorbike")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(
    url: str,
    destination: Path,
    opener: Callable[..., Any] = urlopen,
    chunk_size: int = 1024 * 1024,
) -> str:
    partial = destination.with_suffix(destination.suffix + ".part")
    if destination.exists() or partial.exists():
        raise ProjectError(
            "E204",
            "下载目标或未完成文件已存在",
            "Download target or partial file already exists",
            "确认内容后使用新的路径，或把旧文件移入废纸篓",
            "Use a new path or move the old file to Trash after inspection",
            str(destination),
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    try:
        with opener(url) as response, partial.open("xb") as output:
            while chunk := response.read(chunk_size):
                output.write(chunk)
                digest.update(chunk)
    except OSError as error:
        raise ProjectError(
            "E201",
            "数据集下载失败，未完成文件已保留",
            "Dataset download failed; the partial file was preserved",
            "检查网络；确认后把 .part 文件移入废纸篓再重试",
            "Check the network; inspect and move the .part file to Trash before retrying",
            str(partial),
        ) from error
    partial.rename(destination)
    return digest.hexdigest()


def safe_extract_zip(archive: Path, destination: Path) -> tuple[Path, ...]:
    if not archive.is_file():
        raise ProjectError(
            "E201",
            "压缩包不存在",
            "Archive does not exist",
            "先运行数据下载命令",
            "Run the dataset download command first",
            str(archive),
        )
    if destination.exists() and any(destination.iterdir()):
        raise ProjectError(
            "E204",
            "原始数据目录已经包含文件",
            "Raw-data directory already contains files",
            "保留现有数据，或检查后把整个目录移入废纸篓",
            "Keep the existing data or inspect and move the directory to Trash",
            str(destination),
        )

    destination_root = destination.resolve()
    try:
        with zipfile.ZipFile(archive) as bundle:
            members = bundle.infolist()
            targets: list[Path] = []
            for member in members:
                target = (destination / member.filename).resolve()
                if member.filename.startswith("/") or not target.is_relative_to(destination_root):
                    raise ProjectError(
                        "E203",
                        "压缩包包含不安全路径",
                        "Archive contains an unsafe path",
                        "不要解压该文件，重新从官方来源下载",
                        "Do not extract it; redownload from the official source",
                        member.filename,
                    )
                if not member.is_dir():
                    targets.append(target)
            destination.mkdir(parents=True, exist_ok=True)
            bundle.extractall(destination)
    except zipfile.BadZipFile as error:
        raise ProjectError(
            "E202",
            "压缩包损坏",
            "Archive is corrupt",
            "检查后把压缩包移入废纸篓并重新下载",
            "Inspect, move the archive to Trash, and redownload it",
            str(archive),
        ) from error
    return tuple(targets)


def main(debug: bool = False) -> int:
    paths = get_paths()
    archive = paths.downloads / ARCHIVE_NAME
    raw_destination = paths.raw / RAW_RELATIVE_PATH
    try:
        if archive.exists():
            digest = sha256_file(archive)
            print(f"[INFO] 使用已有压缩包 / Reusing archive: {archive}")
        else:
            print(f"[INFO] 开始下载 / Starting download: {RDD2022_CHINA_MOTORBIKE_URL}")
            digest = download_file(RDD2022_CHINA_MOTORBIKE_URL, archive)
        if raw_destination.exists() and any(raw_destination.iterdir()):
            print(f"[INFO] 使用已有原始数据 / Reusing raw data: {raw_destination}")
        else:
            safe_extract_zip(archive, raw_destination)
        print(f"[PASS] 下载与解压完成 / Download and extraction complete\nSHA-256: {digest}")
        return 0
    except ProjectError as error:
        return report_error(error, debug=debug)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download RDD2022 / 下载 RDD2022")
    parser.add_argument("--debug", action="store_true")
    raise SystemExit(main(debug=parser.parse_args().debug))
```

- [ ] **Step 4: Run downloader verification**

Run:

```bash
uv run pytest tests/test_download.py -v
uv run ruff check src/urbanvision_risk/data/download.py tests/test_download.py
```

Expected: 4 tests PASS and Ruff exits successfully. Do not run the real download yet.

- [ ] **Step 5: Commit the safe downloader**

```bash
git add src/urbanvision_risk/data/download.py tests/test_download.py
git commit -m "feat: add safe RDD2022 downloader"
```

---

### Task 5: Prepared-Dataset Validation

**Files:**
- Create: `src/urbanvision_risk/data/validate.py`
- Create: `tests/test_dataset_validation.py`

**Interfaces:**
- Consumes: immutable `CLASS_INFO` from Task 3; `ProjectError` and default processed path from Task 1.
- Produces: `ValidationReport`; `validate_prepared_dataset(dataset_root: Path) -> ValidationReport`; `main() -> int`.

- [ ] **Step 1: Write failing prepared-dataset validation tests**

Create `tests/test_dataset_validation.py`:

```python
from pathlib import Path

from PIL import Image

from urbanvision_risk.data.validate import validate_prepared_dataset


def write_sample(root: Path, split: str, name: str, label: str) -> None:
    image_dir = root / "images" / split
    label_dir = root / "labels" / split
    image_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (40, 20), color="gray").save(image_dir / f"{name}.jpg")
    (label_dir / f"{name}.txt").write_text(label, encoding="utf-8")


def test_valid_dataset_reports_counts(tmp_path: Path) -> None:
    write_sample(tmp_path, "train", "train-road", "3 0.5 0.5 0.5 0.5\n")
    write_sample(tmp_path, "val", "val-road", "0 0.5 0.5 0.2 0.2\n")
    write_sample(tmp_path, "test", "test-road", "")

    report = validate_prepared_dataset(tmp_path)

    assert report.ok is True
    assert report.image_counts == {"train": 1, "val": 1, "test": 1}
    assert report.object_counts == {"D00": 1, "D10": 0, "D20": 0, "D40": 1}
    assert report.errors == ()


def test_invalid_label_and_duplicate_stem_are_reported(tmp_path: Path) -> None:
    write_sample(tmp_path, "train", "same-road", "9 0.5 0.5 0.5 0.5\n")
    write_sample(tmp_path, "val", "same-road", "0 0.5 0.5 0.2 0.2\n")
    (tmp_path / "images" / "test").mkdir(parents=True)
    (tmp_path / "labels" / "test").mkdir(parents=True)

    report = validate_prepared_dataset(tmp_path)

    assert report.ok is False
    assert any("class index" in error for error in report.errors)
    assert any("multiple splits" in error for error in report.errors)


def test_corrupt_image_is_reported(tmp_path: Path) -> None:
    image_dir = tmp_path / "images" / "train"
    label_dir = tmp_path / "labels" / "train"
    image_dir.mkdir(parents=True)
    label_dir.mkdir(parents=True)
    (image_dir / "broken.jpg").write_bytes(b"not-a-jpeg")
    (label_dir / "broken.txt").write_text("", encoding="utf-8")
    for split in ("val", "test"):
        (tmp_path / "images" / split).mkdir(parents=True)
        (tmp_path / "labels" / split).mkdir(parents=True)

    report = validate_prepared_dataset(tmp_path)

    assert report.ok is False
    assert any("cannot be opened" in error for error in report.errors)
```

- [ ] **Step 2: Run validation tests and verify they fail**

Run: `uv run pytest tests/test_dataset_validation.py -v`

Expected: FAIL during collection because `urbanvision_risk.data.validate` does not exist.

- [ ] **Step 3: Implement image, label, coordinate, and split validation**

Create `src/urbanvision_risk/data/validate.py`:

```python
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from urbanvision_risk.data.voc import CLASS_INFO
from urbanvision_risk.paths import get_paths


SPLITS = ("train", "val", "test")


@dataclass(frozen=True, slots=True)
class ValidationReport:
    image_counts: dict[str, int]
    object_counts: dict[str, int]
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def _validate_label(path: Path, object_counts: Counter[str], errors: list[str]) -> None:
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        parts = raw_line.split()
        if len(parts) != 5:
            errors.append(f"{path}:{line_number}: label must have 5 values")
            continue
        try:
            class_index = int(parts[0])
            coordinates = tuple(float(value) for value in parts[1:])
        except ValueError:
            errors.append(f"{path}:{line_number}: label values must be numeric")
            continue
        if class_index not in CLASS_INFO:
            errors.append(f"{path}:{line_number}: unknown class index {class_index}")
            continue
        x_center, y_center, width, height = coordinates
        coordinate_ok = all(math.isfinite(value) and 0 <= value <= 1 for value in coordinates)
        if not coordinate_ok or width <= 0 or height <= 0:
            errors.append(f"{path}:{line_number}: invalid normalized box {coordinates}")
            continue
        if width > 1 or height > 1 or x_center < 0 or y_center < 0:
            errors.append(f"{path}:{line_number}: normalized box is outside [0, 1]")
            continue
        object_counts[CLASS_INFO[class_index]["code"]] += 1


def validate_prepared_dataset(dataset_root: Path) -> ValidationReport:
    errors: list[str] = []
    image_counts: dict[str, int] = {}
    object_counts: Counter[str] = Counter({details["code"]: 0 for details in CLASS_INFO.values()})
    seen_stems: dict[str, str] = {}

    for split in SPLITS:
        image_dir = dataset_root / "images" / split
        label_dir = dataset_root / "labels" / split
        if not image_dir.is_dir() or not label_dir.is_dir():
            errors.append(f"{split}: image or label directory is missing")
            image_counts[split] = 0
            continue
        images = sorted(path for path in image_dir.iterdir() if path.suffix.lower() in {".jpg", ".jpeg", ".png"})
        image_counts[split] = len(images)
        image_stems = {path.stem for path in images}
        label_stems = {path.stem for path in label_dir.glob("*.txt")}
        for missing in sorted(image_stems - label_stems):
            errors.append(f"{split}/{missing}: image has no label")
        for missing in sorted(label_stems - image_stems):
            errors.append(f"{split}/{missing}: label has no image")

        for image_path in images:
            previous_split = seen_stems.setdefault(image_path.stem, split)
            if previous_split != split:
                errors.append(
                    f"{image_path.stem}: identifier appears in multiple splits: {previous_split}, {split}"
                )
            try:
                with Image.open(image_path) as image:
                    image.verify()
            except (OSError, UnidentifiedImageError):
                errors.append(f"{image_path}: image cannot be opened")
            label_path = label_dir / f"{image_path.stem}.txt"
            if label_path.is_file():
                _validate_label(label_path, object_counts, errors)

    return ValidationReport(
        image_counts=image_counts,
        object_counts=dict(object_counts),
        errors=tuple(errors),
    )


def main() -> int:
    dataset_root = get_paths().processed / "rdd2022-china-motorbike"
    report = validate_prepared_dataset(dataset_root)
    for split, count in report.image_counts.items():
        print(f"[INFO] {split} 图片数量 / image count: {count}")
    print(f"[INFO] 缺陷实例 / object counts: {report.object_counts}")
    if report.ok:
        print("[PASS] 数据验证通过 / Dataset validation passed")
        return 0
    for error in report.errors:
        print(f"[ERROR E203] 数据记录无效 / Invalid dataset record: {error}")
    print("[FAIL] 数据验证失败 / Dataset validation failed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run dataset-validation verification**

Run:

```bash
uv run pytest tests/test_dataset_validation.py -v
uv run ruff check src/urbanvision_risk/data/validate.py tests/test_dataset_validation.py
```

Expected: 3 tests PASS and Ruff exits successfully.

- [ ] **Step 5: Commit the validator**

```bash
git add src/urbanvision_risk/data/validate.py tests/test_dataset_validation.py
git commit -m "feat: validate prepared road-damage data"
```

---

### Task 6: End-to-End Dataset Preparation and Manifest

**Files:**
- Create: `src/urbanvision_risk/data/prepare.py`
- Create: `tests/test_dataset_preparation.py`
- Create: `configs/dataset-rdd2022-china-motorbike.yaml`

**Interfaces:**
- Consumes: `parse_voc_annotation()`, `to_yolo_lines()`, `split_ids()`, `sha256_file()`, `validate_prepared_dataset()`, `ProjectError`, and `get_paths()` from Tasks 1, 3, 4, and 5.
- Produces: `ImageAnnotationPair`; `discover_pairs(raw_root: Path) -> dict[str, ImageAnnotationPair]`; `prepare_dataset(raw_root: Path, archive_path: Path, output_root: Path) -> dict[str, object]`; `main() -> int`; committed dataset YAML.

- [ ] **Step 1: Write a failing end-to-end preparation test**

Create `tests/test_dataset_preparation.py`:

```python
import json
from pathlib import Path

import pytest
from PIL import Image

from urbanvision_risk.data.prepare import discover_pairs, prepare_dataset
from urbanvision_risk.errors import ProjectError


def write_source_pair(root: Path, index: int) -> None:
    images = root / "train" / "images"
    annotations = root / "train" / "annotations" / "xmls"
    images.mkdir(parents=True, exist_ok=True)
    annotations.mkdir(parents=True, exist_ok=True)
    name = f"road-{index:02d}"
    Image.new("RGB", (100, 50), color="gray").save(images / f"{name}.jpg")
    (annotations / f"{name}.xml").write_text(
        f"""<annotation>
        <filename>{name}.jpg</filename>
        <size><width>100</width><height>50</height></size>
        <object><name>D40</name><bndbox>
        <xmin>10</xmin><ymin>5</ymin><xmax>40</xmax><ymax>25</ymax>
        </bndbox></object></annotation>""",
        encoding="utf-8",
    )


def test_prepare_dataset_writes_split_labels_and_manifest(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    output_root = tmp_path / "processed"
    archive = tmp_path / "archive.zip"
    archive.write_bytes(b"fixture archive digest input")
    for index in range(10):
        write_source_pair(raw_root, index)

    manifest = prepare_dataset(raw_root, archive, output_root)

    assert manifest["file_counts"] == {"train": 8, "val": 1, "test": 1}
    assert manifest["object_counts"] == {"D00": 0, "D10": 0, "D20": 0, "D40": 10}
    assert manifest["invalid_records"] == 0
    assert len(manifest["input_digest"]) == 64
    assert len(list((output_root / "labels" / "train").glob("*.txt"))) == 8
    persisted = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))
    assert persisted == manifest


def test_discover_pairs_rejects_xml_with_missing_image(tmp_path: Path) -> None:
    annotation = tmp_path / "missing.xml"
    annotation.write_text(
        """<annotation><filename>missing.jpg</filename>
        <size><width>100</width><height>50</height></size></annotation>""",
        encoding="utf-8",
    )

    with pytest.raises(ProjectError, match="E202"):
        discover_pairs(tmp_path)
```

- [ ] **Step 2: Run the preparation test and verify it fails**

Run: `uv run pytest tests/test_dataset_preparation.py -v`

Expected: FAIL during collection because `urbanvision_risk.data.prepare` does not exist.

- [ ] **Step 3: Add the portable committed dataset configuration**

Create `configs/dataset-rdd2022-china-motorbike.yaml`:

```yaml
path: data/processed/rdd2022-china-motorbike
train: images/train
val: images/val
test: images/test
names:
  0: D00
  1: D10
  2: D20
  3: D40
```

- [ ] **Step 4: Implement pairing, staging, conversion, validation, and manifest writing**

Create `src/urbanvision_risk/data/prepare.py`:

```python
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from urbanvision_risk.data.download import (
    ARCHIVE_NAME,
    RAW_RELATIVE_PATH,
    RDD2022_CHINA_MOTORBIKE_URL,
    sha256_file,
)
from urbanvision_risk.data.split import split_ids
from urbanvision_risk.data.validate import validate_prepared_dataset
from urbanvision_risk.data.voc import CLASS_INFO, parse_voc_annotation, to_yolo_lines
from urbanvision_risk.errors import ProjectError, report_error
from urbanvision_risk.paths import get_paths


@dataclass(frozen=True, slots=True)
class ImageAnnotationPair:
    identifier: str
    image: Path
    annotation: Path


def discover_pairs(raw_root: Path) -> dict[str, ImageAnnotationPair]:
    image_index: dict[str, Path] = {}
    for image in sorted(path for path in raw_root.rglob("*") if path.suffix.lower() in {".jpg", ".jpeg", ".png"}):
        if image.name in image_index:
            raise ProjectError(
                "E202",
                "发现重复图片文件名",
                "Duplicate image filename found",
                "检查原始数据目录结构",
                "Inspect the raw-data directory structure",
                image.name,
            )
        image_index[image.name] = image

    pairs: dict[str, ImageAnnotationPair] = {}
    for annotation in sorted(raw_root.rglob("*.xml")):
        record = parse_voc_annotation(annotation)
        image = image_index.get(Path(record.filename).name)
        if image is None:
            raise ProjectError(
                "E202",
                "XML 对应的图片不存在",
                "The image referenced by XML is missing",
                "检查原始数据是否完整",
                "Check that the raw dataset is complete",
                f"{annotation}: {record.filename}",
            )
        identifier = annotation.stem
        if identifier in pairs:
            raise ProjectError(
                "E202",
                "发现重复标注标识符",
                "Duplicate annotation identifier found",
                "检查原始数据目录结构",
                "Inspect the raw-data directory structure",
                identifier,
            )
        pairs[identifier] = ImageAnnotationPair(identifier, image, annotation)
    if not pairs:
        raise ProjectError(
            "E201",
            "原始目录中没有 XML 标注",
            "No XML annotations were found in the raw directory",
            "先运行数据下载命令并检查解压目录",
            "Run the download command and inspect the extracted directory",
            str(raw_root),
        )
    return pairs


def _canonical_digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def prepare_dataset(raw_root: Path, archive_path: Path, output_root: Path) -> dict[str, object]:
    if not raw_root.is_dir() or not archive_path.is_file():
        raise ProjectError(
            "E201",
            "原始数据目录或压缩包不存在",
            "Raw-data directory or archive is missing",
            "先运行数据下载命令",
            "Run the dataset download command first",
            f"raw={raw_root}, archive={archive_path}",
        )
    if output_root.exists():
        raise ProjectError(
            "E204",
            "处理后数据目录已经存在",
            "Processed dataset directory already exists",
            "保留现有结果，或检查后把整个目录移入废纸篓",
            "Keep it or inspect and move the entire directory to Trash",
            str(output_root),
        )
    staging = output_root.parent / f".{output_root.name}.staging"
    if staging.exists():
        raise ProjectError(
            "E204",
            "发现未完成的数据准备目录",
            "An unfinished preparation directory exists",
            "检查该目录，并在确认后移入废纸篓",
            "Inspect it and move it to Trash after confirmation",
            str(staging),
        )

    pairs = discover_pairs(raw_root)
    split = split_ids(pairs)
    split_members = {"train": split.train, "val": split.val, "test": split.test}
    for split_name in split_members:
        (staging / "images" / split_name).mkdir(parents=True, exist_ok=True)
        (staging / "labels" / split_name).mkdir(parents=True, exist_ok=True)

    for split_name, identifiers in split_members.items():
        for identifier in identifiers:
            pair = pairs[identifier]
            record = parse_voc_annotation(pair.annotation)
            image_target = staging / "images" / split_name / f"{identifier}{pair.image.suffix.lower()}"
            label_target = staging / "labels" / split_name / f"{identifier}.txt"
            shutil.copy2(pair.image, image_target)
            lines = to_yolo_lines(record)
            label_target.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    report = validate_prepared_dataset(staging)
    if not report.ok:
        raise ProjectError(
            "E203",
            "处理后数据验证失败，暂存目录已保留",
            "Prepared-data validation failed; staging was preserved",
            "检查错误并在确认后把暂存目录移入废纸篓",
            "Inspect errors and move the staging directory to Trash after confirmation",
            "\n".join(report.errors),
        )

    archive_digest = sha256_file(archive_path)
    digest_inputs: dict[str, object] = {
        "archive_sha256": archive_digest,
        "classes": CLASS_INFO,
        "seed": 42,
        "ratios": {"train": 0.8, "val": 0.1, "test": 0.1},
        "splits": split_members,
    }
    manifest: dict[str, object] = {
        "source_url": RDD2022_CHINA_MOTORBIKE_URL,
        "archive_sha256": archive_digest,
        "prepared_at": datetime.now(UTC).isoformat(),
        "seed": 42,
        "ratios": {"train": 0.8, "val": 0.1, "test": 0.1},
        "file_counts": report.image_counts,
        "object_counts": report.object_counts,
        "invalid_records": 0,
        "input_digest": _canonical_digest(digest_inputs),
    }
    (staging / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    staging.rename(output_root)
    return manifest


def main(debug: bool = False) -> int:
    paths = get_paths()
    try:
        manifest = prepare_dataset(
            raw_root=paths.raw / RAW_RELATIVE_PATH,
            archive_path=paths.downloads / ARCHIVE_NAME,
            output_root=paths.processed / "rdd2022-china-motorbike",
        )
        print(f"[PASS] 数据准备完成 / Dataset preparation complete\n{json.dumps(manifest, ensure_ascii=False, indent=2)}")
        return 0
    except ProjectError as error:
        return report_error(error, debug=debug)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare RDD2022 / 准备 RDD2022")
    parser.add_argument("--debug", action="store_true")
    raise SystemExit(main(debug=parser.parse_args().debug))
```

- [ ] **Step 5: Run preparation and complete regression verification**

Run:

```bash
uv run pytest tests/test_dataset_preparation.py tests/test_dataset_validation.py tests/test_voc_conversion.py tests/test_dataset_split.py -v
uv run ruff check src/urbanvision_risk/data tests/test_dataset_preparation.py
```

Expected: all selected tests PASS and Ruff exits successfully.

- [ ] **Step 6: Commit dataset preparation**

```bash
git add configs/dataset-rdd2022-china-motorbike.yaml src/urbanvision_risk/data/prepare.py tests/test_dataset_preparation.py
git commit -m "feat: prepare reproducible RDD2022 subset"
```

- [ ] **Step 7: Learner checkpoint — acquire, prepare, and validate real data**

Run one command at a time and return each complete output:

```bash
uv run python -m urbanvision_risk.data.download
uv run python -m urbanvision_risk.data.prepare
uv run python -m urbanvision_risk.data.validate
```

Expected: the first command reports an official archive SHA-256; the second reports 80/10/10 file counts and class counts; the third ends with `[PASS] 数据验证通过 / Dataset validation passed`. Stop on any E201–E204 code.

---

### Task 7: Validated YOLO26n Training Profiles and Unique Experiments

**Files:**
- Create: `configs/train-smoke.yaml`
- Create: `configs/train-baseline.yaml`
- Create: `src/urbanvision_risk/detection/__init__.py`
- Create: `src/urbanvision_risk/detection/config.py`
- Create: `src/urbanvision_risk/detection/train.py`
- Create: `tests/test_training_config.py`
- Create: `tests/test_training.py`

**Interfaces:**
- Consumes: dataset YAML and manifest from Task 6, `ProjectError`, and `ProjectPaths`.
- Produces: `TrainingProfile`; `load_training_profile(name: str, configs_dir: Path) -> TrainingProfile`; `validate_run_name(name: str) -> str`; `train_experiment(profile_name: str, run_name: str, paths: ProjectPaths | None = None, model_factory: Callable[[str], Any] | None = None, git_commit_resolver: Callable[[Path], str] = _git_commit) -> Path`; `main() -> int`.

- [ ] **Step 1: Add the two approved training profiles**

Create `configs/train-smoke.yaml`:

```yaml
model: yolo26n.pt
epochs: 1
imgsz: 640
batch: 4
device: mps
workers: 2
seed: 42
deterministic: true
cache: false
fraction: 0.1
```

Create `configs/train-baseline.yaml`:

```yaml
model: yolo26n.pt
epochs: 30
imgsz: 640
batch: 8
device: mps
workers: 2
seed: 42
deterministic: true
cache: false
fraction: 1.0
```

Create `src/urbanvision_risk/detection/__init__.py`:

```python
"""YOLO training, evaluation, and prediction commands."""
```

- [ ] **Step 2: Write failing profile and run-safety tests**

Create `tests/test_training_config.py`:

```python
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
```

Create `tests/test_training.py`:

```python
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from urbanvision_risk.detection.train import train_experiment
from urbanvision_risk.errors import ProjectError
from urbanvision_risk.paths import get_paths


class FakeResult:
    results_dict = {"metrics/mAP50(B)": 0.25}


class FakeModel:
    def __init__(self, checkpoint: str) -> None:
        assert checkpoint == "yolo26n.pt"

    def train(self, **kwargs: Any) -> FakeResult:
        run_dir = Path(kwargs["project"]) / kwargs["name"]
        weights = run_dir / "weights"
        weights.mkdir(parents=True, exist_ok=True)
        (weights / "best.pt").write_bytes(b"best")
        (weights / "last.pt").write_bytes(b"last")
        (run_dir / "results.csv").write_text("epoch,map50\n0,0.25\n", encoding="utf-8")
        return FakeResult()


def write_training_fixture(root: Path) -> None:
    configs = root / "configs"
    processed = root / "data" / "processed" / "rdd2022-china-motorbike"
    configs.mkdir(parents=True)
    processed.mkdir(parents=True)
    (processed / "manifest.json").write_text(
        json.dumps({"input_digest": "a" * 64}), encoding="utf-8"
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
```

- [ ] **Step 3: Run training tests and verify they fail**

Run: `uv run pytest tests/test_training_config.py tests/test_training.py -v`

Expected: FAIL during collection because the detection configuration and training modules do not exist.

- [ ] **Step 4: Implement strict training-profile loading**

Create `src/urbanvision_risk/detection/config.py`:

```python
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
            "使用 1–64 位小写字母、数字和连字符",
            "Use 1–64 lowercase letters, digits, and hyphens",
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
        raise ProjectError("E302", "训练配置不是映射", "Training profile is not a mapping", "检查 YAML", "Inspect the YAML", str(path))
    required = {
        "model", "epochs", "imgsz", "batch", "device", "workers",
        "seed", "deterministic", "cache", "fraction",
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
        profile.model == "yolo26n.pt"
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
            "训练配置值不符合 v0.1 约束",
            "Training values violate v0.1 constraints",
            "恢复已批准的 smoke 或 baseline 配置",
            "Restore the approved smoke or baseline profile",
            str(path),
        )
    return profile
```

- [ ] **Step 5: Implement uniquely named training and durable summary writing**

Create `src/urbanvision_risk/detection/train.py`:

```python
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
    destination.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


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
    manifest = json.loads(
        (active_paths.processed / "rdd2022-china-motorbike" / "manifest.json").read_text(encoding="utf-8")
    )
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
    parser = argparse.ArgumentParser(description="Train UrbanVision-Risk / 训练道路缺陷模型")
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
```

- [ ] **Step 6: Run training unit verification**

Run:

```bash
uv run pytest tests/test_training_config.py tests/test_training.py -v
uv run ruff check src/urbanvision_risk/detection tests/test_training_config.py tests/test_training.py
```

Expected: 7 tests PASS and Ruff exits successfully.

- [ ] **Step 7: Commit training profiles and code**

```bash
git add configs/train-smoke.yaml configs/train-baseline.yaml src/urbanvision_risk/detection tests/test_training_config.py tests/test_training.py
git commit -m "feat: train reproducible YOLO26n experiments"
```

- [ ] **Step 8: Learner checkpoint — run one-epoch MPS smoke training**

Run: `uv run python -m urbanvision_risk.detection.train --profile smoke --run-name smoke-test-001`

Expected: Ultralytics downloads `yolo26n.pt` once if it is not cached, reports `device=mps`, completes one epoch, and writes `results/experiments/smoke-test-001/weights/best.pt`, `last.pt`, `results.csv`, and `training_summary.json`. Return the complete output before starting the baseline.

- [ ] **Step 9: Learner checkpoint — run the 30-epoch baseline only after smoke review**

Run: `uv run python -m urbanvision_risk.detection.train --profile baseline --run-name china-baseline-001`

Expected: 30 epochs complete on MPS and `results/experiments/china-baseline-001/` contains both checkpoints, `results.csv`, training plots, and `training_summary.json`.

---

### Task 8: Held-Out Evaluation and Per-Class Metrics

**Files:**
- Create: `src/urbanvision_risk/detection/evaluate.py`
- Create: `tests/test_evaluation.py`

**Interfaces:**
- Consumes: `validate_run_name()`, a completed experiment's `best.pt`, and its `dataset-resolved.yaml` and `training_summary.json` from Task 7.
- Produces: `metrics_payload(metrics: Any) -> dict[str, object]`; `evaluate_run(run_name: str, paths: ProjectPaths | None = None, model_factory: Callable[[str], Any] | None = None) -> Path`; `results/evaluations/<run-name>/evaluation.json`; updated `training_summary.json`; `main() -> int`.

- [ ] **Step 1: Write failing metric extraction and missing-checkpoint tests**

Create `tests/test_evaluation.py`:

```python
from pathlib import Path
from types import SimpleNamespace

import pytest

from urbanvision_risk.detection.evaluate import evaluate_run, metrics_payload
from urbanvision_risk.errors import ProjectError
from urbanvision_risk.paths import get_paths


def test_metrics_payload_contains_overall_and_per_class_values() -> None:
    box = SimpleNamespace(
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

    payload = metrics_payload(SimpleNamespace(box=box))

    assert payload["overall"]["mAP50"] == 0.45
    assert payload["per_class"]["D40"]["precision"] == 0.4
    assert payload["per_class"]["D00"]["f1"] == pytest.approx(0.1333333333)


def test_evaluate_run_requires_best_checkpoint(tmp_path: Path) -> None:
    run_dir = get_paths(tmp_path).experiments / "china-baseline-001"
    run_dir.mkdir(parents=True)

    with pytest.raises(ProjectError, match="E301"):
        evaluate_run("china-baseline-001", paths=get_paths(tmp_path), model_factory=lambda _: None)
```

- [ ] **Step 2: Run evaluation tests and verify they fail**

Run: `uv run pytest tests/test_evaluation.py -v`

Expected: FAIL during collection because `urbanvision_risk.detection.evaluate` does not exist.

- [ ] **Step 3: Implement real overall/per-class extraction and durable evaluation**

Create `src/urbanvision_risk/detection/evaluate.py`:

```python
from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from urbanvision_risk.data.voc import CLASS_INFO
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
        int(class_index): position
        for position, class_index in enumerate(box.ap_class_index)
    }
    per_class: dict[str, dict[str, float | str | None]] = {}
    for class_index, details in CLASS_INFO.items():
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
            "f1": 0.0 if denominator == 0 else 2 * overall_precision * overall_recall / denominator,
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
```

- [ ] **Step 4: Run evaluation verification**

Run:

```bash
uv run pytest tests/test_evaluation.py -v
uv run ruff check src/urbanvision_risk/detection/evaluate.py tests/test_evaluation.py
```

Expected: 2 tests PASS and Ruff exits successfully.

- [ ] **Step 5: Commit held-out evaluation**

```bash
git add src/urbanvision_risk/detection/evaluate.py tests/test_evaluation.py
git commit -m "feat: evaluate held-out road damage data"
```

- [ ] **Step 6: Learner checkpoint — evaluate the baseline**

Run: `uv run python -m urbanvision_risk.detection.evaluate --run-name china-baseline-001`

Expected: `results/evaluations/china-baseline-001/evaluation.json` and Ultralytics plots are written; `training_summary.json` gains `held_out_test_metrics`. Return the JSON contents for bilingual interpretation without claiming publication-grade generalization.

---

### Task 9: Annotated Prediction Images and Structured JSON

**Files:**
- Create: `src/urbanvision_risk/detection/predict.py`
- Create: `tests/test_prediction.py`

**Interfaces:**
- Consumes: `validate_run_name()`, `CLASS_INFO`, and one completed experiment's `best.pt`.
- Produces: `serialize_result(result: Any, model_path: Path, confidence: float) -> dict[str, object]`; `predict_source(run_name: str, source: Path, output_name: str = "prediction-001", confidence: float = 0.25, paths: ProjectPaths | None = None, model_factory: Callable[[str], Any] | None = None) -> Path`; annotated JPG files and matching JSON files; `main() -> int`.

- [ ] **Step 1: Write failing prediction-schema tests including no detections**

Create `tests/test_prediction.py`:

```python
from pathlib import Path
from types import SimpleNamespace

from urbanvision_risk.detection.predict import serialize_result


class Scalar:
    def __init__(self, value: float) -> None:
        self.value = value

    def item(self) -> float:
        return self.value


class Vector:
    def __init__(self, values: list[float]) -> None:
        self.values = values

    def tolist(self) -> list[float]:
        return self.values


def test_serialize_result_contains_engineering_class_names() -> None:
    box = SimpleNamespace(
        cls=[Scalar(3)],
        conf=[Scalar(0.87)],
        xyxy=[Vector([120.0, 80.0, 260.0, 210.0])],
    )
    result = SimpleNamespace(path="road.jpg", orig_shape=(300, 400), boxes=[box])

    payload = serialize_result(result, Path("best.pt"), confidence=0.25)

    assert payload["image_dimensions"] == {"width": 400, "height": 300}
    assert payload["counts"] == {"D00": 0, "D10": 0, "D20": 0, "D40": 1}
    assert payload["detections"][0] == {
        "class_id": 3,
        "code": "D40",
        "name_en": "Pothole",
        "name_zh": "坑洞",
        "confidence": 0.87,
        "bbox_xyxy": [120.0, 80.0, 260.0, 210.0],
    }


def test_serialize_empty_detection_is_explicit() -> None:
    result = SimpleNamespace(path="clear-road.jpg", orig_shape=(100, 200), boxes=[])

    payload = serialize_result(result, Path("best.pt"), confidence=0.25)

    assert payload["detections"] == []
    assert payload["message_zh"] == "在当前置信度阈值下未检测到道路缺陷"
    assert payload["message_en"] == "No road damage was detected at the current confidence threshold"
```

- [ ] **Step 2: Run prediction tests and verify they fail**

Run: `uv run pytest tests/test_prediction.py -v`

Expected: FAIL during collection because `urbanvision_risk.detection.predict` does not exist.

- [ ] **Step 3: Implement JSON serialization and non-overwriting annotated output**

Create `src/urbanvision_risk/detection/predict.py`:

```python
from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

from urbanvision_risk.data.voc import CLASS_INFO
from urbanvision_risk.detection.config import validate_run_name
from urbanvision_risk.errors import ProjectError, report_error
from urbanvision_risk.paths import ProjectPaths, get_paths


def serialize_result(result: Any, model_path: Path, confidence: float) -> dict[str, object]:
    counts: Counter[str] = Counter({details["code"]: 0 for details in CLASS_INFO.values()})
    detections: list[dict[str, object]] = []
    for box in result.boxes:
        class_id = int(box.cls[0].item())
        score = float(box.conf[0].item())
        coordinates = [float(value) for value in box.xyxy[0].tolist()]
        details = CLASS_INFO[class_id]
        counts[details["code"]] += 1
        detections.append(
            {
                "class_id": class_id,
                "code": details["code"],
                "name_en": details["name_en"],
                "name_zh": details["name_zh"],
                "confidence": score,
                "bbox_xyxy": coordinates,
            }
        )
    height, width = result.orig_shape
    payload: dict[str, object] = {
        "source_image": str(Path(result.path).resolve()),
        "model_checkpoint": str(model_path.resolve()),
        "confidence_threshold": confidence,
        "image_dimensions": {"width": int(width), "height": int(height)},
        "detections": detections,
        "counts": dict(counts),
    }
    if not detections:
        payload["message_zh"] = "在当前置信度阈值下未检测到道路缺陷"
        payload["message_en"] = "No road damage was detected at the current confidence threshold"
    return payload


def predict_source(
    run_name: str,
    source: Path,
    output_name: str = "prediction-001",
    confidence: float = 0.25,
    paths: ProjectPaths | None = None,
    model_factory: Callable[[str], Any] | None = None,
) -> Path:
    active_paths = paths or get_paths()
    validate_run_name(run_name)
    validate_run_name(output_name)
    if not 0 <= confidence <= 1:
        raise ProjectError(
            "E302",
            "置信度阈值必须位于 0 到 1",
            "Confidence threshold must be between 0 and 1",
            "使用例如 --confidence 0.25",
            "Use a value such as --confidence 0.25",
            str(confidence),
        )
    if not source.exists():
        raise ProjectError(
            "E201",
            "预测图片或目录不存在",
            "Prediction image or directory does not exist",
            "检查 --source 路径",
            "Check the --source path",
            str(source),
        )
    checkpoint = active_paths.experiments / run_name / "weights" / "best.pt"
    if not checkpoint.is_file():
        raise ProjectError(
            "E301",
            "最佳模型不存在",
            "Best model checkpoint is missing",
            "先完成基线训练",
            "Complete baseline training first",
            str(checkpoint),
        )
    output_dir = active_paths.predictions / run_name / output_name
    try:
        output_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise ProjectError(
            "E204",
            "预测输出目录已经存在",
            "Prediction output directory already exists",
            "使用新的 --output-name",
            "Use a new --output-name",
            str(output_dir),
        ) from error

    factory = model_factory
    if factory is None:
        from ultralytics import YOLO

        factory = YOLO
    model = factory(str(checkpoint))
    results = model.predict(source=str(source), conf=confidence, device="mps", stream=True)
    count = 0
    for result in results:
        source_path = Path(result.path)
        stem = source_path.stem
        result.save(filename=str(output_dir / f"{stem}-annotated.jpg"))
        payload = serialize_result(result, checkpoint, confidence)
        (output_dir / f"{stem}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        count += 1
    if count == 0:
        raise ProjectError(
            "E301",
            "模型没有返回预测结果",
            "The model returned no prediction results",
            "检查输入图片格式",
            "Check the input image format",
            str(source),
        )
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Predict road damage / 预测道路缺陷")
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-name", default="prediction-001")
    parser.add_argument("--confidence", type=float, default=0.25)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    try:
        output = predict_source(
            args.run_name,
            args.source,
            output_name=args.output_name,
            confidence=args.confidence,
        )
        print(f"[PASS] 预测完成 / Prediction complete: {output}")
        return 0
    except ProjectError as error:
        return report_error(error, debug=args.debug)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run prediction verification**

Run:

```bash
uv run pytest tests/test_prediction.py -v
uv run ruff check src/urbanvision_risk/detection/predict.py tests/test_prediction.py
```

Expected: 2 tests PASS and Ruff exits successfully.

- [ ] **Step 5: Commit structured prediction**

```bash
git add src/urbanvision_risk/detection/predict.py tests/test_prediction.py
git commit -m "feat: save annotated bilingual predictions"
```

- [ ] **Step 6: Learner checkpoint — generate the first road-damage result**

Run prediction over the prepared local test directory:

```bash
uv run python -m urbanvision_risk.detection.predict --run-name china-baseline-001 --source data/processed/rdd2022-china-motorbike/images/test
```

Expected: `results/predictions/china-baseline-001/prediction-001/` contains `<stem>-annotated.jpg` and `<stem>.json`. An empty detection list remains an honest valid result and includes both explanatory messages.

---

### Task 10: Bilingual Learner Documentation and Final Verification

**Files:**
- Modify: `README.md`
- Create: `docs/learning-guide.md`
- Create: `data/README.md`
- Create: `models/README.md`
- Create: `results/README.md`
- Create: `tests/fixtures/sample.xml`
- Generate: `tests/fixtures/sample.jpg`
- Create: `tests/test_documentation.py`

**Interfaces:**
- Consumes: every learner-facing command and artifact defined in Tasks 1–9.
- Produces: concise bilingual project entry point, eight complete beginner lessons, artifact-directory guides, a committed fixture pair, and a final verification record.

- [ ] **Step 1: Write failing documentation-contract tests**

Create `tests/test_documentation.py`:

```python
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
```

- [ ] **Step 2: Run documentation tests and verify they fail**

Run: `uv run pytest tests/test_documentation.py -v`

Expected: FAIL because the full learner documents and committed fixture pair do not exist yet.

- [ ] **Step 3: Replace the short README with the complete bilingual milestone entry point**

Write `README.md` with this content:

```markdown
# UrbanVision-Risk

**中文：** 面向城市基础设施智能巡检与风险评估的端侧 AI 项目。v0.1 在 Apple Silicon Mac 上完成 RDD2022 道路缺陷数据准备、YOLO26n 微调、真实评估和图片预测。

**English:** An on-device AI project for urban-infrastructure inspection and risk assessment. Version 0.1 prepares RDD2022 road-damage data, fine-tunes YOLO26n, evaluates real held-out metrics, and predicts locally on Apple Silicon.

## v0.1 Scope / v0.1 范围

- Four classes / 四类缺陷: D00 longitudinal crack / 纵向裂缝, D10 transverse crack / 横向裂缝, D20 alligator crack / 网状裂缝, D40 pothole / 坑洞.
- Fully local after one-time dependency, data, and model downloads / 完成一次性依赖、数据和模型下载后可完全本地运行。
- No paid API or cloud runtime / 不使用付费 API 或云端运行环境。
- No Web UI, risk engine, LLM, GIS, or multi-country research claim in v0.1 / v0.1 不包含 Web、风险引擎、LLM、GIS 或多国科研结论。

## Safety / 安全说明

The project uses uv-managed Python 3.11 and never replaces macOS `/usr/bin/python3`. Raw data is immutable. Commands never permanently delete data or silently overwrite experiments.

项目使用 uv 管理的 Python 3.11，不替换 macOS `/usr/bin/python3`。原始数据不可变，命令不永久删除数据，也不静默覆盖实验。

## Learner Workflow / 学习者流程

Run one command at a time. Return the complete terminal output for explanation before continuing.

一次只运行一条命令。继续之前，把完整终端输出发回以便解释。

```bash
uv python install 3.11
uv sync --extra dev
uv run python -m urbanvision_risk.environment
uv run pytest
uv run python -m urbanvision_risk.data.download
uv run python -m urbanvision_risk.data.prepare
uv run python -m urbanvision_risk.data.validate
uv run python -m urbanvision_risk.detection.train --profile smoke --run-name smoke-test-001
uv run python -m urbanvision_risk.detection.train --profile baseline --run-name china-baseline-001
uv run python -m urbanvision_risk.detection.evaluate --run-name china-baseline-001
uv run python -m urbanvision_risk.detection.predict --run-name china-baseline-001 --source data/processed/rdd2022-china-motorbike/images/test
```

## Generated Artifacts / 生成物

- `data/processed/rdd2022-china-motorbike/manifest.json`: data lineage and counts / 数据来源与统计。
- `results/experiments/<run>/weights/best.pt`: best checkpoint / 最佳模型。
- `results/evaluations/<run>/evaluation.json`: held-out metrics / 留出集指标。
- `results/predictions/<run>/<output>/`: annotated JPG and JSON / 带框图片与 JSON。

## Learning Guide / 学习指南

Read [`docs/learning-guide.md`](docs/learning-guide.md) for bilingual explanations of Python environments, labels, splits, training, metrics, MPS, and experiment interpretation.

阅读 [`docs/learning-guide.md`](docs/learning-guide.md)，了解 Python 环境、标签、数据划分、训练、指标、MPS 和实验解读。

## Data and Citation / 数据与引用

RDD2022 is downloaded from its maintainers and is not redistributed here: <https://github.com/sekilab/RoadDamageDetector>. Cite the dataset article: <https://arxiv.org/abs/2209.08538>.

RDD2022 从维护者来源下载，本仓库不重新分发。使用数据时请引用上述资料。

## License / 许可

Repository code is licensed under `AGPL-3.0-or-later`. Ultralytics licensing must be reviewed again before any closed-source commercial use.

仓库代码采用 `AGPL-3.0-or-later`。任何闭源商业使用前必须重新审查 Ultralytics 许可。
```

- [ ] **Step 4: Write the eight-lesson learning guide**

Create `docs/learning-guide.md`:

```markdown
# UrbanVision-Risk v0.1 Learning Guide / 学习指南

This guide connects each concept to code you can run locally. Each lesson has one command; run it from the repository root and return the output before moving on.

本指南把每个概念对应到可在本机运行的代码。每课包含一条命令；从仓库根目录运行，并在继续前返回输出。

## Lesson 01 — Python, uv, and Isolation / Python、uv 与隔离环境

**中文：** macOS 的 `/usr/bin/python3` 属于系统。`uv` 另外安装 Python 3.11，并在 `.venv` 中保存本项目依赖。隔离环境防止一个项目升级包时破坏另一个项目。

**English:** `/usr/bin/python3` belongs to macOS. uv installs a separate Python 3.11 and stores this project's dependencies in `.venv`, preventing package changes from breaking unrelated projects.

File / 文件: `.python-version`, `pyproject.toml`, `uv.lock`

Command / 命令: `uv run python --version`

Expected / 预期: `Python 3.11.x`; the exact patch and packages are locked by uv.

**复习问题 / Review question:** Why do we keep the system Python unchanged? / 为什么不修改系统 Python？

## Lesson 02 — Images, Labels, and Object Detection / 图片、标签与目标检测

**中文：** 图片是模型输入；标签说明缺陷类别和位置。目标检测同时回答“是什么”和“在哪里”，而普通分类只回答“是什么”。

**English:** Images are model inputs; labels describe defect class and location. Object detection answers both “what” and “where,” while classification answers only “what.”

File / 文件: `src/urbanvision_risk/data/voc.py`

Command / 命令: `uv run pytest tests/test_voc_conversion.py -v`

Expected / 预期: valid labels convert and invalid boxes are rejected.

**复习问题 / Review question:** What extra information does a bounding box provide? / 边界框比分类标签多提供什么信息？

## Lesson 03 — Pascal VOC and YOLO Labels / Pascal VOC 与 YOLO 标注

**中文：** RDD2022 使用 XML 中的像素坐标。YOLO 使用 `class x_center y_center width height`，并把坐标归一化到 0–1。归一化让不同分辨率图片使用同一种表示。

**English:** RDD2022 stores pixel coordinates in XML. YOLO uses `class x_center y_center width height`, normalized to 0–1 so different image resolutions share one representation.

File / 文件: `src/urbanvision_risk/data/voc.py`

Command / 命令: `uv run python -m urbanvision_risk.data.validate`

Expected / 预期: split counts, class counts, and a final bilingual PASS.

**复习问题 / Review question:** Why are YOLO coordinates divided by image width or height? / YOLO 坐标为什么除以图片宽或高？

## Lesson 04 — Train, Validation, and Test / 训练、验证与测试集

**中文：** 训练集用于更新模型参数；验证集用于训练过程中比较表现；测试集只在训练完成后估计泛化能力。v0.1 固定 seed 42 和 80/10/10 划分，保证重复实验使用相同图片。

**English:** Training data updates model parameters, validation data tracks training decisions, and held-out test data estimates generalization after training. Seed 42 and an 80/10/10 split keep membership reproducible.

File / 文件: `src/urbanvision_risk/data/split.py`

Command / 命令: `uv run pytest tests/test_dataset_split.py -v`

Expected / 预期: deterministic and disjoint split tests PASS.

**复习问题 / Review question:** Why should test images not train the model? / 为什么测试图片不能参与训练？

## Lesson 05 — Epoch, Batch, and Loss / Epoch、Batch 与损失

**中文：** 一个 epoch 表示完整学习一遍训练数据；batch 表示一次送入模型的图片数量；loss 衡量当前预测与标签的差距。冒烟测试只跑 1 epoch 验证链路，基线跑 30 epochs 学习缺陷模式。

**English:** An epoch is one complete pass through the training data, batch is the number of images processed together, and loss measures prediction error. Smoke uses one epoch for plumbing; baseline uses 30 epochs to learn patterns.

File / 文件: `configs/train-smoke.yaml`, `configs/train-baseline.yaml`

Command / 命令: `uv run python -m urbanvision_risk.detection.train --profile smoke --run-name smoke-test-001`

Expected / 预期: one epoch completes and both `best.pt` and `last.pt` are saved.

**复习问题 / Review question:** Why is high accuracy not required from the smoke run? / 为什么冒烟测试不要求高准确率？

## Lesson 06 — Precision, Recall, F1, and mAP / Precision、Recall、F1 与 mAP

**中文：** Precision 关注模型报出的缺陷有多少正确；Recall 关注真实缺陷有多少被找到；F1 平衡两者；mAP 同时考虑类别、置信度排序和框的位置质量。`mAP50-95` 比 `mAP50` 更严格。

**English:** Precision asks how many reported defects are correct, recall asks how many real defects are found, F1 balances both, and mAP evaluates ranked confidence and box localization. `mAP50-95` is stricter than `mAP50`.

File / 文件: `src/urbanvision_risk/detection/evaluate.py`

Command / 命令: `uv run python -m urbanvision_risk.detection.evaluate --run-name china-baseline-001`

Expected / 预期: real overall and per-class metrics in `evaluation.json`.

**复习问题 / Review question:** Can a model have high precision but low recall? / 模型能否 Precision 高但 Recall 低？

## Lesson 07 — Apple MPS and the Mac GPU / Apple MPS 与 Mac GPU

**中文：** MPS 是 PyTorch 通过 Apple Metal 使用 GPU 的后端。环境体检不仅检查布尔标志，还实际在 `mps` 上执行张量运算。项目不静默切换 CPU，因为这会让训练时间产生巨大变化。

**English:** MPS is PyTorch's Apple Metal GPU backend. The checker performs a real tensor operation, not only flag checks. Silent CPU fallback is disabled because it would radically change training time.

File / 文件: `src/urbanvision_risk/environment.py`

Command / 命令: `uv run python -m urbanvision_risk.environment`

Expected / 预期: Python, root, PyTorch, and MPS all report PASS.

**复习问题 / Review question:** Why does the checker run a real tensor operation? / 为什么体检要执行真实张量运算？

## Lesson 08 — Reading the First Experiment / 阅读第一次实验结果

**中文：** `best.pt` 是验证表现最好的权重，`last.pt` 是最后一轮权重。`training_summary.json` 保存代码提交、数据摘要、参数和版本；`evaluation.json` 保存留出测试指标；预测 JSON 保存每个框的类别、置信度和像素坐标。

**English:** `best.pt` is the best validation checkpoint and `last.pt` is the final epoch. `training_summary.json` records code, data digest, parameters, and versions; `evaluation.json` stores held-out metrics; prediction JSON stores each class, confidence, and pixel box.

File / 文件: `results/README.md`

Command / 命令: `uv run python -m urbanvision_risk.detection.predict --run-name china-baseline-001 --source data/processed/rdd2022-china-motorbike/images/test`

Expected / 预期: an annotated JPG and matching JSON, including an honest empty list when nothing exceeds the threshold.

**复习问题 / Review question:** Why must an empty detection result remain valid? / 为什么空检测结果也必须是合法结果？
```

- [ ] **Step 5: Document local data, model, and result directories**

Create `data/README.md`:

```markdown
# Local Data / 本地数据

`downloads/` stores the official archive, `raw/` stores immutable extraction, and `processed/` stores YOLO-format train/val/test data. These generated directories are ignored by Git.

`downloads/` 保存官方压缩包，`raw/` 保存不可变解压数据，`processed/` 保存 YOLO 格式训练、验证和测试数据；这些生成目录不提交 Git。

RDD2022 source / 数据来源: <https://github.com/sekilab/RoadDamageDetector>

Never edit `raw/`. If a generated directory must be removed, inspect it first and use `/usr/bin/trash <absolute-path>`.

不要编辑 `raw/`。确需移除生成目录时，先检查内容，再使用 `/usr/bin/trash <absolute-path>`。
```

Create `models/README.md`:

```markdown
# Models / 模型

Ultralytics downloads the pretrained `yolo26n.pt` checkpoint once. Trained checkpoints live under `results/experiments/<run-name>/weights/`; generated `.pt` files are ignored by Git.

Ultralytics 首次运行时下载预训练 `yolo26n.pt`。训练检查点位于 `results/experiments/<run-name>/weights/`；生成的 `.pt` 不提交 Git。
```

Create `results/README.md`:

```markdown
# Results / 结果

- `experiments/`: training logs, `best.pt`, `last.pt`, `results.csv`, and `training_summary.json` / 训练日志、权重、表格与训练摘要。
- `evaluations/`: held-out metrics and confusion-matrix plots / 留出集指标和混淆矩阵。
- `predictions/`: annotated JPG files and matching JSON / 带框 JPG 与匹配 JSON。

Every run name is unique. Existing results are never silently overwritten.

每个运行名称唯一；已有结果绝不被静默覆盖。
```

- [ ] **Step 6: Add the deterministic committed fixture pair**

Create `tests/fixtures/sample.xml`:

```xml
<annotation>
  <filename>sample.jpg</filename>
  <size><width>40</width><height>20</height></size>
  <object>
    <name>D40</name>
    <bndbox><xmin>10</xmin><ymin>5</ymin><xmax>30</xmax><ymax>15</ymax></bndbox>
  </object>
</annotation>
```

Generate the binary JPEG deterministically with Pillow:

```bash
uv run python -c 'from pathlib import Path; from PIL import Image; path=Path("tests/fixtures/sample.jpg"); path.parent.mkdir(parents=True, exist_ok=True); Image.new("RGB", (40, 20), "gray").save(path, quality=95, optimize=False, progressive=False)'
```

Expected: `tests/fixtures/sample.jpg` opens as a 40×20 RGB JPEG and matches `sample.xml`.

- [ ] **Step 7: Run all local verification before final learner artifacts**

Run:

```bash
uv run ruff format .
uv run ruff check .
uv run pytest -v
uv run ruff format --check .
uv run python -m urbanvision_risk.environment
git diff --check
git status --short
```

Expected: every test passes; Ruff lint and format checks pass; the real environment reports MPS PASS; `git diff --check` prints nothing; `git status --short` lists only the intended documentation and fixture changes before commit.

- [ ] **Step 8: Commit bilingual documentation and fixtures**

```bash
git add README.md docs/learning-guide.md data/README.md models/README.md results/README.md tests/fixtures tests/test_documentation.py
git commit -m "docs: add bilingual v0.1 learning path"
```

- [ ] **Step 9: Verify the complete acceptance artifact set after learner runs**

Run:

```bash
uv run python -m urbanvision_risk.data.validate
test -f results/experiments/smoke-test-001/weights/best.pt
test -f results/experiments/china-baseline-001/weights/best.pt
test -f results/experiments/china-baseline-001/training_summary.json
test -f results/evaluations/china-baseline-001/evaluation.json
rg --files results/predictions/china-baseline-001/prediction-001
git status --short --branch
```

Expected: dataset validation ends in PASS; every `test -f` exits 0; prediction output lists at least one annotated JPG and one JSON; Git status shows a clean `main` worktree because generated artifacts are ignored.

---

## Execution Checkpoints / 执行检查点

The implementation must pause for learner output at these four boundaries:

实施必须在以下四个边界等待学习者返回输出：

1. After `uv python install 3.11` and `uv sync --extra dev` / Python 与依赖安装后。
2. After the real environment check and network-independent tests / 真实环境体检和无网络测试后。
3. After download, preparation, validation, and smoke training / 下载、准备、验证和冒烟训练后。
4. After baseline training, evaluation, and first prediction / 基线训练、评估和第一次预测后。

At every checkpoint, explain the goal, command, expected output, actual output, common failures, and next action in Chinese and English before continuing.

每个检查点都必须先用中英双语解释目标、命令、预期输出、实际输出、常见错误和下一步，再继续执行。
