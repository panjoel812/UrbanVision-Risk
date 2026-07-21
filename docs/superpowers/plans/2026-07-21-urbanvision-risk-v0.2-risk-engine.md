# UrbanVision-Risk v0.2 Risk Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert v0.1 prediction JSON into deterministic, explainable per-image maintenance-priority scores and a bilingual batch ranking, entirely on-device.

**Architecture:** A new `risk` package separates configuration, rectangle geometry, prediction-schema validation, pure scoring, and filesystem orchestration. The command reads existing prediction JSON without invoking YOLO, validates the entire batch before creating output, calculates exact per-class rectangle-union coverage, then writes immutable per-image JSON, a summary, a ranking CSV, and the resolved YAML configuration.

**Tech Stack:** Python 3.11, standard library (`csv`, `dataclasses`, `hashlib`, `json`, `math`, `statistics`), PyYAML, pytest, Ruff, uv.

## Global Constraints

- Use project-scoped CPython `3.11.x` through `uv`; never replace macOS `/usr/bin/python3`.
- Runtime is fully local. Risk scoring must not import Ultralytics, call a model, access the network, or use a paid/cloud API.
- Reuse `/Users/panjoel/Documents/Project/UrbanVision-Risk/.worktrees/urbanvision-v0.1` for execution because it contains ignored v0.1 data, weights, evaluation, and prediction artifacts.
- Create branch `feature/urbanvision-v0.2` from `main` inside that preserved worktree before implementation.
- Never permanently delete any file or directory. Never use `rm`, `unlink`, `rmdir`, destructive Git cleanup, or automatic partial-output cleanup.
- Never modify v0.1 prediction JSON or annotated JPG files.
- Never overwrite a risk output directory; raise bilingual `E204` and require a new output name.
- The main score is a heuristic maintenance-priority prototype, not a certified engineering safety assessment.
- `risk_score` is `0–100`, rounded to one decimal, and confidence never appears in its formula.
- Default formula parameters must match the approved design exactly: count cap `5`, reference coverage `0.05`, count/coverage mix `0.35/0.65`, class maxima `15/20/25/40`, risk thresholds `20/40/70`, evidence thresholds `0.50/0.75`, coordinate tolerance `1` pixel.
- All learner-facing text, errors, recommendations, and limitations are bilingual Chinese/English.
- Every test is network-independent and must preserve all 40 v0.1 tests.
- Generated `results/risks/` artifacts remain Git-ignored.

## Execution Workspace / 执行工作区

Run these commands once before Task 1:

```bash
cd "/Users/panjoel/Documents/Project/UrbanVision-Risk/.worktrees/urbanvision-v0.1"
git status --short --branch
git switch -c feature/urbanvision-v0.2 main
uv sync --extra dev
uv run pytest -q
```

Expected:

- Git reports no tracked changes before the switch.
- The new branch includes design commit `e333711` or a descendant of it.
- `40 passed` establishes the v0.1 baseline.
- Existing files below `data/` and `results/` remain present and untouched.

If `feature/urbanvision-v0.2` already exists, stop and inspect it instead of creating or resetting any branch.

## Planned File Structure

| File | Responsibility |
|---|---|
| `.gitignore` | Ignore generated `results/risks/`. |
| `configs/risk-v0.2.yaml` | Store formula version, scoring parameters, thresholds, recommendations, and limitation text. |
| `src/urbanvision_risk/paths.py` | Expose `ProjectPaths.risks`. |
| `src/urbanvision_risk/risk/__init__.py` | Mark the risk package and state its purpose. |
| `src/urbanvision_risk/risk/config.py` | Load, validate, render, and classify against the risk configuration. |
| `src/urbanvision_risk/risk/geometry.py` | Clip boxes with tolerance and calculate exact rectangle-union area. |
| `src/urbanvision_risk/risk/schema.py` | Convert untrusted v0.1 JSON payloads into typed validated records. |
| `src/urbanvision_risk/risk/score.py` | Calculate one image's score and bilingual explanation without filesystem I/O. |
| `src/urbanvision_risk/risk/assess.py` | Discover a batch, validate before output, rank, serialize, and provide the CLI. |
| `tests/test_risk_config.py` | Configuration and threshold contracts. |
| `tests/test_risk_geometry.py` | Rectangle clipping and union-area contracts. |
| `tests/test_risk_schema.py` | Prediction JSON validation contracts. |
| `tests/test_risk_scoring.py` | Formula, confidence independence, empty result, and safety wording. |
| `tests/test_risk_assessment.py` | Batch artifacts, provenance, ranking, preflight failure, and non-overwrite. |
| `tests/test_risk_documentation.py` | Bilingual command, formula, and safety-documentation contract. |
| `docs/risk-engine-guide.md` | Beginner-focused bilingual formula and artifact guide. |
| `README.md`, `docs/learning-guide.md`, `results/README.md` | Link the v0.2 command and artifacts from existing documentation. |

---

### Task 1: Exact Bounding-Box Geometry

**Files:**
- Create: `src/urbanvision_risk/risk/__init__.py`
- Create: `src/urbanvision_risk/risk/geometry.py`
- Create: `tests/test_risk_geometry.py`

**Interfaces:**
- Produces: `Rectangle`; `clip_rectangle(box, width, height, tolerance, context) -> tuple[Rectangle, bool]`; `rectangle_union_area(rectangles) -> float`.
- Contract: a coordinate up to the configured tolerance outside the image is clipped and audited; anything farther outside, non-finite, reversed, or zero-area raises bilingual `E403`.

- [ ] **Step 1: Write failing geometry tests**

Create `tests/test_risk_geometry.py`:

```python
import pytest

from urbanvision_risk.errors import ProjectError
from urbanvision_risk.risk.geometry import clip_rectangle, rectangle_union_area


@pytest.mark.parametrize(
    ("rectangles", "expected"),
    [
        ([(0.0, 0.0, 10.0, 10.0), (20.0, 0.0, 30.0, 10.0)], 200.0),
        ([(0.0, 0.0, 10.0, 10.0), (5.0, 0.0, 15.0, 10.0)], 150.0),
        ([(0.0, 0.0, 10.0, 10.0), (2.0, 2.0, 8.0, 8.0)], 100.0),
        ([(0.0, 0.0, 10.0, 10.0), (10.0, 0.0, 20.0, 10.0)], 200.0),
        ([], 0.0),
    ],
)
def test_rectangle_union_area_handles_overlap(
    rectangles: list[tuple[float, float, float, float]], expected: float
) -> None:
    assert rectangle_union_area(rectangles) == pytest.approx(expected)


def test_clip_rectangle_accepts_small_rounding_drift() -> None:
    rectangle, clipped = clip_rectangle(
        (-0.5, 0, 10, 10), width=100, height=100, tolerance=1, context="sample"
    )

    assert rectangle == (0.0, 0.0, 10.0, 10.0)
    assert clipped is True


@pytest.mark.parametrize(
    "box",
    [
        (-2, 0, 10, 10),
        (10, 0, 5, 10),
        (0, 0, float("nan"), 10),
        (0, 0, 0, 10),
    ],
)
def test_clip_rectangle_rejects_invalid_geometry(box: tuple[float, ...]) -> None:
    with pytest.raises(ProjectError, match="E403"):
        clip_rectangle(box, width=100, height=100, tolerance=1, context="sample")
```

- [ ] **Step 2: Run the tests and verify RED**

```bash
uv run pytest tests/test_risk_geometry.py -v
```

Expected: collection fails because `urbanvision_risk.risk.geometry` does not exist.

- [ ] **Step 3: Implement clipping and exact rectangle union**

Create `src/urbanvision_risk/risk/__init__.py` first so the new package has an explicit boundary:

```python
"""Explainable local maintenance-priority scoring / 可解释本地维护优先级评分。"""
```

Create `src/urbanvision_risk/risk/geometry.py`:

```python
from __future__ import annotations

import math
from collections.abc import Sequence

from urbanvision_risk.errors import ProjectError


Rectangle = tuple[float, float, float, float]


def _geometry_error(context: str) -> ProjectError:
    return ProjectError(
        "E403",
        "检测框几何信息非法",
        "Detection-box geometry is invalid",
        "检查图片尺寸和 bbox_xyxy 坐标",
        "Inspect the image dimensions and bbox_xyxy coordinates",
        context,
    )


def _number(value: object, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _geometry_error(context)
    result = float(value)
    if not math.isfinite(result):
        raise _geometry_error(context)
    return result


def clip_rectangle(
    box: Sequence[object],
    *,
    width: int,
    height: int,
    tolerance: float,
    context: str,
) -> tuple[Rectangle, bool]:
    if (
        len(box) != 4
        or isinstance(width, bool)
        or isinstance(height, bool)
        or not isinstance(width, int)
        or not isinstance(height, int)
        or width <= 0
        or height <= 0
        or not math.isfinite(tolerance)
        or tolerance < 0
    ):
        raise _geometry_error(context)

    x1, y1, x2, y2 = (_number(value, context) for value in box)
    if x2 <= x1 or y2 <= y1:
        raise _geometry_error(context)
    if (
        x1 < -tolerance
        or y1 < -tolerance
        or x2 > width + tolerance
        or y2 > height + tolerance
    ):
        raise _geometry_error(context)

    clipped_rectangle = (
        max(0.0, min(float(width), x1)),
        max(0.0, min(float(height), y1)),
        max(0.0, min(float(width), x2)),
        max(0.0, min(float(height), y2)),
    )
    if clipped_rectangle[2] <= clipped_rectangle[0] or clipped_rectangle[3] <= clipped_rectangle[1]:
        raise _geometry_error(context)
    return clipped_rectangle, clipped_rectangle != (x1, y1, x2, y2)


def rectangle_union_area(rectangles: Sequence[Rectangle]) -> float:
    if not rectangles:
        return 0.0

    x_coordinates = sorted({x for rectangle in rectangles for x in (rectangle[0], rectangle[2])})
    area = 0.0
    for left, right in zip(x_coordinates, x_coordinates[1:], strict=False):
        if right <= left:
            continue
        intervals = sorted(
            (y1, y2)
            for x1, y1, x2, y2 in rectangles
            if x1 < right and x2 > left
        )
        if not intervals:
            continue
        covered_y = 0.0
        start, end = intervals[0]
        for next_start, next_end in intervals[1:]:
            if next_start > end:
                covered_y += end - start
                start, end = next_start, next_end
            else:
                end = max(end, next_end)
        covered_y += end - start
        area += (right - left) * covered_y
    return area
```

- [ ] **Step 4: Verify geometry and commit**

```bash
uv run pytest tests/test_risk_geometry.py -v
uv run ruff format src/urbanvision_risk/risk/geometry.py tests/test_risk_geometry.py
uv run ruff check src/urbanvision_risk/risk/geometry.py tests/test_risk_geometry.py
git add src/urbanvision_risk/risk/__init__.py src/urbanvision_risk/risk/geometry.py tests/test_risk_geometry.py
git commit -m "feat: calculate road damage coverage"
```

Expected: all geometry cases pass and Ruff prints `All checks passed!`.

---

### Task 2: Risk Paths and Auditable Configuration

**Files:**
- Modify: `.gitignore`
- Create: `configs/risk-v0.2.yaml`
- Modify: `src/urbanvision_risk/paths.py`
- Create: `src/urbanvision_risk/risk/config.py`
- Create: `tests/test_risk_config.py`
- Modify: `tests/test_foundation.py`

**Interfaces:**
- Consumes: `ProjectError`, existing `get_paths(root)` convention, PyYAML.
- Produces: `RiskConfig`; `load_risk_config(path: Path) -> RiskConfig`; `resolved_config_yaml(config: RiskConfig) -> str`; `RiskConfig.risk_level(score: float) -> str`; `RiskConfig.evidence_quality(mean_confidence: float | None) -> str`; `ProjectPaths.risks`.

- [ ] **Step 1: Write failing path and configuration tests**

Create `tests/test_risk_config.py`:

```python
from pathlib import Path

import pytest

from urbanvision_risk.errors import ProjectError
from urbanvision_risk.risk.config import load_risk_config, resolved_config_yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "risk-v0.2.yaml"


def test_committed_risk_config_has_approved_defaults() -> None:
    config = load_risk_config(CONFIG_PATH)

    assert config.formula_version == "risk-v0.2.0"
    assert config.count_cap == 5
    assert config.reference_coverage == 0.05
    assert config.count_mix == 0.35
    assert config.coverage_mix == 0.65
    assert config.class_max_points == {"D00": 15.0, "D10": 20.0, "D20": 25.0, "D40": 40.0}
    assert config.risk_level(19.9) == "low"
    assert config.risk_level(20.0) == "moderate"
    assert config.risk_level(40.0) == "high"
    assert config.risk_level(70.0) == "critical"
    assert config.evidence_quality(None) == "not_applicable"
    assert config.evidence_quality(0.49) == "low"
    assert config.evidence_quality(0.50) == "moderate"
    assert config.evidence_quality(0.75) == "high"
    assert "formula_version" in resolved_config_yaml(config)


def test_config_rejects_weights_that_do_not_total_one_hundred(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text(
        CONFIG_PATH.read_text(encoding="utf-8").replace("D40: 40", "D40: 39"),
        encoding="utf-8",
    )

    with pytest.raises(ProjectError, match="E401"):
        load_risk_config(invalid)


def test_config_rejects_mix_that_does_not_total_one(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text(
        CONFIG_PATH.read_text(encoding="utf-8").replace("coverage_mix: 0.65", "coverage_mix: 0.60"),
        encoding="utf-8",
    )

    with pytest.raises(ProjectError, match="E401"):
        load_risk_config(invalid)
```

Append this test to `tests/test_foundation.py`:

```python
def test_get_paths_exposes_risk_results(tmp_path: Path) -> None:
    assert get_paths(tmp_path).risks == tmp_path / "results" / "risks"
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
uv run pytest tests/test_risk_config.py tests/test_foundation.py::test_get_paths_exposes_risk_results -v
```

Expected: collection fails because `urbanvision_risk.risk.config` and `ProjectPaths.risks` do not exist.

- [ ] **Step 3: Add the committed YAML**

Append to `.gitignore`:

```gitignore
results/risks/
```

Create `configs/risk-v0.2.yaml`:

```yaml
formula_version: risk-v0.2.0
count_cap: 5
reference_coverage: 0.05
count_mix: 0.35
coverage_mix: 0.65
class_max_points:
  D00: 15
  D10: 20
  D20: 25
  D40: 40
risk_thresholds:
  moderate: 20
  high: 40
  critical: 70
evidence_thresholds:
  moderate: 0.50
  high: 0.75
coordinate_tolerance_pixels: 1
recommendations:
  low:
    en: Routine review; no urgent maintenance priority was detected.
    zh: 常规复核；未检测到紧急维护优先项。
  moderate:
    en: Schedule a manual review.
    zh: 安排人工复检。
  high:
    en: Prioritize manual inspection.
    zh: 优先人工检查。
  critical:
    en: Urgent manual inspection; a human decides any control action.
    zh: 紧急人工检查；任何管制措施由人工决定。
limitation:
  en: This heuristic maintenance-priority score does not replace a certified engineering safety assessment.
  zh: 此启发式维护优先级分数不能替代经过认证的工程安全鉴定。
```

- [ ] **Step 4: Add the risk results path**

Add the field to `ProjectPaths` in `src/urbanvision_risk/paths.py`:

```python
    risks: Path
```

Add the constructor argument after `predictions`:

```python
        risks=results / "risks",
```

- [ ] **Step 5: Implement strict configuration loading**

Create `src/urbanvision_risk/risk/config.py`:

```python
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from urbanvision_risk.data.voc import CLASS_INFO
from urbanvision_risk.errors import ProjectError


CLASS_CODES = tuple(details["code"] for details in CLASS_INFO.values())
RISK_LEVELS = ("low", "moderate", "high", "critical")


def _config_error(path: Path, field: str) -> ProjectError:
    return ProjectError(
        "E401",
        "风险配置非法",
        "Risk configuration is invalid",
        "检查配置字段和设计文档中的约束",
        "Inspect the field and the constraints in the design document",
        f"{path}: {field}",
    )


def _mapping(value: Any, path: Path, field: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise _config_error(path, field)
    return value


def _finite_number(value: Any, path: Path, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _config_error(path, field)
    result = float(value)
    if not math.isfinite(result):
        raise _config_error(path, field)
    return result


def _positive_integer(value: Any, path: Path, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise _config_error(path, field)
    return value


def _text(value: Any, path: Path, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _config_error(path, field)
    return value.strip()


@dataclass(frozen=True, slots=True)
class RiskConfig:
    formula_version: str
    count_cap: int
    reference_coverage: float
    count_mix: float
    coverage_mix: float
    class_max_points: dict[str, float]
    risk_thresholds: dict[str, float]
    evidence_thresholds: dict[str, float]
    coordinate_tolerance_pixels: float
    recommendations: dict[str, dict[str, str]]
    limitation: dict[str, str]

    def risk_level(self, score: float) -> str:
        if score >= self.risk_thresholds["critical"]:
            return "critical"
        if score >= self.risk_thresholds["high"]:
            return "high"
        if score >= self.risk_thresholds["moderate"]:
            return "moderate"
        return "low"

    def evidence_quality(self, mean_confidence: float | None) -> str:
        if mean_confidence is None:
            return "not_applicable"
        if mean_confidence >= self.evidence_thresholds["high"]:
            return "high"
        if mean_confidence >= self.evidence_thresholds["moderate"]:
            return "moderate"
        return "low"

    def to_payload(self) -> dict[str, object]:
        return {
            "formula_version": self.formula_version,
            "count_cap": self.count_cap,
            "reference_coverage": self.reference_coverage,
            "count_mix": self.count_mix,
            "coverage_mix": self.coverage_mix,
            "class_max_points": dict(self.class_max_points),
            "risk_thresholds": dict(self.risk_thresholds),
            "evidence_thresholds": dict(self.evidence_thresholds),
            "coordinate_tolerance_pixels": self.coordinate_tolerance_pixels,
            "recommendations": {
                level: dict(messages) for level, messages in self.recommendations.items()
            },
            "limitation": dict(self.limitation),
        }


def load_risk_config(path: Path) -> RiskConfig:
    if not path.is_file():
        raise ProjectError(
            "E201",
            "风险配置不存在",
            "Risk configuration does not exist",
            "检查 --config 路径",
            "Check the --config path",
            str(path),
        )
    try:
        root = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), path, "root")
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise _config_error(path, "root") from error

    formula_version = _text(root.get("formula_version"), path, "formula_version")
    count_cap = _positive_integer(root.get("count_cap"), path, "count_cap")
    reference_coverage = _finite_number(
        root.get("reference_coverage"), path, "reference_coverage"
    )
    count_mix = _finite_number(root.get("count_mix"), path, "count_mix")
    coverage_mix = _finite_number(root.get("coverage_mix"), path, "coverage_mix")
    tolerance = _finite_number(
        root.get("coordinate_tolerance_pixels"), path, "coordinate_tolerance_pixels"
    )

    class_raw = _mapping(root.get("class_max_points"), path, "class_max_points")
    if set(class_raw) != set(CLASS_CODES):
        raise _config_error(path, "class_max_points")
    class_points = {
        code: _finite_number(class_raw[code], path, f"class_max_points.{code}")
        for code in CLASS_CODES
    }

    risk_raw = _mapping(root.get("risk_thresholds"), path, "risk_thresholds")
    evidence_raw = _mapping(root.get("evidence_thresholds"), path, "evidence_thresholds")
    if set(risk_raw) != {"moderate", "high", "critical"}:
        raise _config_error(path, "risk_thresholds")
    if set(evidence_raw) != {"moderate", "high"}:
        raise _config_error(path, "evidence_thresholds")
    risk_thresholds = {
        name: _finite_number(risk_raw[name], path, f"risk_thresholds.{name}")
        for name in ("moderate", "high", "critical")
    }
    evidence_thresholds = {
        name: _finite_number(evidence_raw[name], path, f"evidence_thresholds.{name}")
        for name in ("moderate", "high")
    }

    recommendations_raw = _mapping(root.get("recommendations"), path, "recommendations")
    if set(recommendations_raw) != set(RISK_LEVELS):
        raise _config_error(path, "recommendations")
    recommendations: dict[str, dict[str, str]] = {}
    for level in RISK_LEVELS:
        messages = _mapping(recommendations_raw[level], path, f"recommendations.{level}")
        if set(messages) != {"en", "zh"}:
            raise _config_error(path, f"recommendations.{level}")
        recommendations[level] = {
            language: _text(messages[language], path, f"recommendations.{level}.{language}")
            for language in ("en", "zh")
        }

    limitation_raw = _mapping(root.get("limitation"), path, "limitation")
    if set(limitation_raw) != {"en", "zh"}:
        raise _config_error(path, "limitation")
    limitation = {
        language: _text(limitation_raw[language], path, f"limitation.{language}")
        for language in ("en", "zh")
    }

    if not 0 < reference_coverage <= 1:
        raise _config_error(path, "reference_coverage")
    if count_mix < 0 or coverage_mix < 0 or not math.isclose(
        count_mix + coverage_mix, 1.0
    ):
        raise _config_error(path, "count_mix/coverage_mix")
    if any(value <= 0 for value in class_points.values()) or not math.isclose(
        sum(class_points.values()), 100.0
    ):
        raise _config_error(path, "class_max_points")
    if not 0 < risk_thresholds["moderate"] < risk_thresholds["high"] < risk_thresholds[
        "critical"
    ] <= 100:
        raise _config_error(path, "risk_thresholds")
    if not 0 < evidence_thresholds["moderate"] < evidence_thresholds["high"] <= 1:
        raise _config_error(path, "evidence_thresholds")
    if tolerance < 0:
        raise _config_error(path, "coordinate_tolerance_pixels")

    return RiskConfig(
        formula_version=formula_version,
        count_cap=count_cap,
        reference_coverage=reference_coverage,
        count_mix=count_mix,
        coverage_mix=coverage_mix,
        class_max_points=class_points,
        risk_thresholds=risk_thresholds,
        evidence_thresholds=evidence_thresholds,
        coordinate_tolerance_pixels=tolerance,
        recommendations=recommendations,
        limitation=limitation,
    )


def resolved_config_yaml(config: RiskConfig) -> str:
    return yaml.safe_dump(
        config.to_payload(),
        allow_unicode=True,
        sort_keys=False,
    )
```

- [ ] **Step 6: Run Task 2 verification**

Run:

```bash
uv run pytest tests/test_risk_config.py tests/test_foundation.py -v
uv run ruff check src/urbanvision_risk/risk/config.py tests/test_risk_config.py src/urbanvision_risk/paths.py tests/test_foundation.py
```

Expected: all selected tests pass and Ruff prints `All checks passed!`.

- [ ] **Step 7: Commit configuration foundation**

```bash
git add .gitignore configs/risk-v0.2.yaml src/urbanvision_risk/paths.py src/urbanvision_risk/risk/config.py tests/test_risk_config.py tests/test_foundation.py
git commit -m "feat: configure explainable risk scoring"
```

---

### Task 3: Strict v0.1 Prediction Schema

**Files:**
- Create: `src/urbanvision_risk/risk/schema.py`
- Create: `tests/test_risk_schema.py`

**Interfaces:**
- Consumes: the JSON shape produced by `detection.predict.serialize_result`, `CLASS_INFO`, `RiskConfig`, and `clip_rectangle`.
- Produces: immutable `DetectionRecord`, immutable `PredictionRecord`, and `validate_prediction_payload(payload, config, context) -> PredictionRecord`.
- Error boundary: malformed JSON structure is `E402`; internally inconsistent values or invalid semantics are `E403`.

- [ ] **Step 1: Write schema tests and fixture helper**

Create `tests/test_risk_schema.py`:

```python
from pathlib import Path

import pytest

from urbanvision_risk.errors import ProjectError
from urbanvision_risk.risk.config import load_risk_config
from urbanvision_risk.risk.schema import validate_prediction_payload


ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_risk_config(ROOT / "configs" / "risk-v0.2.yaml")


def prediction_payload() -> dict[str, object]:
    return {
        "source_image": "/tmp/road.jpg",
        "model_checkpoint": "/tmp/best.pt",
        "confidence_threshold": 0.25,
        "image_dimensions": {"width": 100, "height": 80},
        "detections": [
            {
                "class_id": 3,
                "code": "D40",
                "name_en": "Pothole",
                "name_zh": "坑洞",
                "confidence": 0.8,
                "bbox_xyxy": [10, 20, 30, 40],
            }
        ],
        "counts": {"D00": 0, "D10": 0, "D20": 0, "D40": 1},
    }


def test_valid_payload_becomes_typed_record() -> None:
    record = validate_prediction_payload(prediction_payload(), CONFIG, "sample.json")

    assert record.width == 100
    assert record.height == 80
    assert record.counts["D40"] == 1
    assert record.detections[0].rectangle == (10.0, 20.0, 30.0, 40.0)
    assert record.detections[0].clipped is False


def test_small_coordinate_drift_is_clipped_and_audited() -> None:
    payload = prediction_payload()
    payload["detections"][0]["bbox_xyxy"] = [-0.5, 20, 30, 40]  # type: ignore[index]

    record = validate_prediction_payload(payload, CONFIG, "sample.json")

    assert record.detections[0].rectangle[0] == 0.0
    assert record.detections[0].clipped is True


def test_missing_required_field_is_e402() -> None:
    payload = prediction_payload()
    payload.pop("image_dimensions")

    with pytest.raises(ProjectError, match="E402"):
        validate_prediction_payload(payload, CONFIG, "sample.json")


def test_counts_must_match_detections() -> None:
    payload = prediction_payload()
    payload["counts"] = {"D00": 0, "D10": 0, "D20": 0, "D40": 0}

    with pytest.raises(ProjectError, match="E403"):
        validate_prediction_payload(payload, CONFIG, "sample.json")


def test_class_metadata_must_be_canonical() -> None:
    payload = prediction_payload()
    payload["detections"][0]["class_id"] = 99  # type: ignore[index]

    with pytest.raises(ProjectError, match="E403"):
        validate_prediction_payload(payload, CONFIG, "sample.json")


def test_box_far_outside_image_is_e403() -> None:
    payload = prediction_payload()
    payload["detections"][0]["bbox_xyxy"] = [-2, 20, 30, 40]  # type: ignore[index]

    with pytest.raises(ProjectError, match="E403"):
        validate_prediction_payload(payload, CONFIG, "sample.json")
```

- [ ] **Step 2: Run the schema tests and verify RED**

```bash
uv run pytest tests/test_risk_schema.py -v
```

Expected: collection fails because `urbanvision_risk.risk.schema` does not exist.

- [ ] **Step 3: Implement structural and semantic validation**

Create `src/urbanvision_risk/risk/schema.py`:

```python
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Any

from urbanvision_risk.data.voc import CLASS_INFO
from urbanvision_risk.errors import ProjectError
from urbanvision_risk.risk.config import RiskConfig
from urbanvision_risk.risk.geometry import Rectangle, clip_rectangle


@dataclass(frozen=True, slots=True)
class DetectionRecord:
    class_id: int
    code: str
    name_en: str
    name_zh: str
    confidence: float
    rectangle: Rectangle
    clipped: bool


@dataclass(frozen=True, slots=True)
class PredictionRecord:
    source_image: str
    model_checkpoint: str
    confidence_threshold: float
    width: int
    height: int
    detections: tuple[DetectionRecord, ...]
    counts: dict[str, int]


def _malformed(context: str, field: str) -> ProjectError:
    return ProjectError(
        "E402",
        "预测 JSON 结构不完整或类型错误",
        "Prediction JSON has a missing field or invalid type",
        "重新运行 v0.1 预测，或检查该 JSON 字段",
        "Rerun v0.1 prediction or inspect this JSON field",
        f"{context}: {field}",
    )


def _semantic(context: str, field: str) -> ProjectError:
    return ProjectError(
        "E403",
        "预测 JSON 的值互相矛盾",
        "Prediction JSON contains inconsistent values",
        "不要手工修改预测 JSON；重新运行 v0.1 预测",
        "Do not hand-edit prediction JSON; rerun v0.1 prediction",
        f"{context}: {field}",
    )


def _mapping(value: object, context: str, field: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise _malformed(context, field)
    return value


def _text(value: object, context: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _malformed(context, field)
    return value


def _integer(value: object, context: str, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _malformed(context, field)
    return value


def _number(value: object, context: str, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _malformed(context, field)
    result = float(value)
    if not math.isfinite(result):
        raise _semantic(context, field)
    return result


def validate_prediction_payload(
    payload: object,
    config: RiskConfig,
    context: str,
) -> PredictionRecord:
    root = _mapping(payload, context, "root")
    required = {
        "source_image",
        "model_checkpoint",
        "confidence_threshold",
        "image_dimensions",
        "detections",
        "counts",
    }
    if not required.issubset(root):
        raise _malformed(context, "required fields")

    dimensions = _mapping(root["image_dimensions"], context, "image_dimensions")
    if not {"width", "height"}.issubset(dimensions):
        raise _malformed(context, "image_dimensions")
    width = _integer(dimensions["width"], context, "image_dimensions.width")
    height = _integer(dimensions["height"], context, "image_dimensions.height")
    if width <= 0 or height <= 0:
        raise _semantic(context, "image_dimensions")

    confidence_threshold = _number(
        root["confidence_threshold"], context, "confidence_threshold"
    )
    if not 0 <= confidence_threshold <= 1:
        raise _semantic(context, "confidence_threshold")
    raw_detections = root["detections"]
    if not isinstance(raw_detections, list):
        raise _malformed(context, "detections")

    detections: list[DetectionRecord] = []
    observed: Counter[str] = Counter()
    for index, raw_detection in enumerate(raw_detections):
        field = f"detections[{index}]"
        detection = _mapping(raw_detection, context, field)
        expected_fields = {
            "class_id",
            "code",
            "name_en",
            "name_zh",
            "confidence",
            "bbox_xyxy",
        }
        if not expected_fields.issubset(detection):
            raise _malformed(context, field)
        class_id = _integer(detection["class_id"], context, f"{field}.class_id")
        details = CLASS_INFO.get(class_id)
        if details is None:
            raise _semantic(context, f"{field}.class_id")
        code = _text(detection["code"], context, f"{field}.code")
        name_en = _text(detection["name_en"], context, f"{field}.name_en")
        name_zh = _text(detection["name_zh"], context, f"{field}.name_zh")
        if (code, name_en, name_zh) != (
            details["code"],
            details["name_en"],
            details["name_zh"],
        ):
            raise _semantic(context, f"{field}.class metadata")
        confidence = _number(detection["confidence"], context, f"{field}.confidence")
        if not 0 <= confidence <= 1:
            raise _semantic(context, f"{field}.confidence")
        raw_box = detection["bbox_xyxy"]
        if not isinstance(raw_box, list):
            raise _malformed(context, f"{field}.bbox_xyxy")
        rectangle, clipped = clip_rectangle(
            raw_box,
            width=width,
            height=height,
            tolerance=config.coordinate_tolerance_pixels,
            context=f"{context}: {field}.bbox_xyxy",
        )
        detections.append(
            DetectionRecord(
                class_id=class_id,
                code=code,
                name_en=name_en,
                name_zh=name_zh,
                confidence=confidence,
                rectangle=rectangle,
                clipped=clipped,
            )
        )
        observed[code] += 1

    raw_counts = _mapping(root["counts"], context, "counts")
    class_codes = tuple(details["code"] for details in CLASS_INFO.values())
    if set(raw_counts) != set(class_codes):
        raise _semantic(context, "counts keys")
    counts = {
        code: _integer(raw_counts[code], context, f"counts.{code}") for code in class_codes
    }
    if any(count < 0 for count in counts.values()) or any(
        counts[code] != observed[code] for code in class_codes
    ):
        raise _semantic(context, "counts")

    return PredictionRecord(
        source_image=_text(root["source_image"], context, "source_image"),
        model_checkpoint=_text(root["model_checkpoint"], context, "model_checkpoint"),
        confidence_threshold=confidence_threshold,
        width=width,
        height=height,
        detections=tuple(detections),
        counts=counts,
    )
```

- [ ] **Step 4: Verify the schema boundary and commit**

```bash
uv run pytest tests/test_risk_schema.py -v
uv run ruff format src/urbanvision_risk/risk/schema.py tests/test_risk_schema.py
uv run ruff check src/urbanvision_risk/risk/schema.py tests/test_risk_schema.py
git add src/urbanvision_risk/risk/schema.py tests/test_risk_schema.py
git commit -m "feat: validate prediction risk inputs"
```

Expected: all schema tests pass; malformed and inconsistent inputs retain distinct stable error codes.

---

### Task 4: Pure Explainable Scoring

**Files:**
- Create: `src/urbanvision_risk/risk/score.py`
- Create: `tests/test_risk_scoring.py`

**Interfaces:**
- Produces: `score_prediction(record, config, source_prediction, source_sha256, config_sha256) -> dict[str, object]`.
- Contract: the score uses only class, count, and exact union coverage. Detection confidence is reported only as evidence quality and cannot alter `risk_score`.

- [ ] **Step 1: Write formula and safety-contract tests**

Create `tests/test_risk_scoring.py`:

```python
from collections import Counter
from pathlib import Path

import pytest

from urbanvision_risk.data.voc import CLASS_INFO
from urbanvision_risk.risk.config import load_risk_config
from urbanvision_risk.risk.schema import validate_prediction_payload
from urbanvision_risk.risk.score import score_prediction


ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_risk_config(ROOT / "configs" / "risk-v0.2.yaml")


def payload(detections: list[dict[str, object]]) -> dict[str, object]:
    counts: Counter[str] = Counter(
        {details["code"]: 0 for details in CLASS_INFO.values()}
    )
    for detection in detections:
        counts[str(detection["code"])] += 1
    return {
        "source_image": "/tmp/road.jpg",
        "model_checkpoint": "/tmp/best.pt",
        "confidence_threshold": 0.25,
        "image_dimensions": {"width": 100, "height": 100},
        "detections": detections,
        "counts": dict(counts),
    }


def detection(class_id: int = 3, confidence: float = 0.8) -> dict[str, object]:
    details = CLASS_INFO[class_id]
    return {
        "class_id": class_id,
        "code": details["code"],
        "name_en": details["name_en"],
        "name_zh": details["name_zh"],
        "confidence": confidence,
        "bbox_xyxy": [0, 0, 10, 10],
    }


def scored(detections: list[dict[str, object]]) -> dict[str, object]:
    record = validate_prediction_payload(payload(detections), CONFIG, "sample.json")
    return score_prediction(
        record,
        CONFIG,
        source_prediction="sample.json",
        source_sha256="prediction-sha",
        config_sha256="config-sha",
    )


def test_single_pothole_matches_approved_formula() -> None:
    result = scored([detection()])

    assert result["risk_score"] == 14.4
    assert result["risk_level"] == "low"
    d40 = result["class_breakdown"][3]
    assert d40["coverage_ratio"] == pytest.approx(0.01)
    assert d40["count_factor"] == pytest.approx(0.2)
    assert d40["coverage_factor"] == pytest.approx(0.4472136)


def test_confidence_changes_evidence_not_risk_score() -> None:
    low_confidence = scored([detection(confidence=0.3)])
    high_confidence = scored([detection(confidence=0.9)])

    assert low_confidence["risk_score"] == high_confidence["risk_score"]
    assert low_confidence["evidence"]["quality"] == "low"
    assert high_confidence["evidence"]["quality"] == "high"


def test_empty_detection_is_zero_not_a_safety_claim() -> None:
    result = scored([])

    assert result["risk_score"] == 0.0
    assert result["risk_level"] == "low"
    assert result["evidence"]["quality"] == "not_applicable"
    assert "does not replace" in result["limitation"]["en"]
    assert "不能替代" in result["limitation"]["zh"]


def test_all_classes_saturate_at_one_hundred() -> None:
    detections = []
    for class_id in CLASS_INFO:
        for _ in range(5):
            item = detection(class_id=class_id)
            item["bbox_xyxy"] = [0, 0, 30, 20]
            detections.append(item)

    result = scored(detections)

    assert result["risk_score"] == 100.0
    assert result["risk_level"] == "critical"
```

- [ ] **Step 2: Run the score tests and verify RED**

```bash
uv run pytest tests/test_risk_scoring.py -v
```

Expected: collection fails because `urbanvision_risk.risk.score` does not exist.

- [ ] **Step 3: Implement the pure score function**

Create `src/urbanvision_risk/risk/score.py`:

```python
from __future__ import annotations

import math
import statistics
from collections import defaultdict

from urbanvision_risk.data.voc import CLASS_INFO
from urbanvision_risk.risk.config import RiskConfig
from urbanvision_risk.risk.geometry import Rectangle, rectangle_union_area
from urbanvision_risk.risk.schema import PredictionRecord


def score_prediction(
    record: PredictionRecord,
    config: RiskConfig,
    *,
    source_prediction: str,
    source_sha256: str,
    config_sha256: str,
) -> dict[str, object]:
    rectangles_by_code: defaultdict[str, list[Rectangle]] = defaultdict(list)
    for detection in record.detections:
        rectangles_by_code[detection.code].append(detection.rectangle)

    image_area = float(record.width * record.height)
    class_breakdown: list[dict[str, object]] = []
    raw_total = 0.0
    for class_id, details in CLASS_INFO.items():
        code = details["code"]
        count = record.counts[code]
        union_area = rectangle_union_area(rectangles_by_code[code])
        coverage_ratio = min(1.0, union_area / image_area)
        count_factor = min(count / config.count_cap, 1.0)
        coverage_factor = min(
            math.sqrt(coverage_ratio / config.reference_coverage), 1.0
        )
        contribution = config.class_max_points[code] * (
            config.count_mix * count_factor
            + config.coverage_mix * coverage_factor
        )
        raw_total += contribution
        class_breakdown.append(
            {
                "class_id": class_id,
                "code": code,
                "name_en": details["name_en"],
                "name_zh": details["name_zh"],
                "count": count,
                "union_area_pixels": round(union_area, 4),
                "coverage_ratio": round(coverage_ratio, 8),
                "count_factor": round(count_factor, 8),
                "coverage_factor": round(coverage_factor, 8),
                "maximum_points": config.class_max_points[code],
                "score_contribution": round(contribution, 4),
            }
        )

    risk_score = round(min(100.0, raw_total), 1)
    risk_level = config.risk_level(risk_score)
    confidences = [detection.confidence for detection in record.detections]
    mean_confidence = statistics.fmean(confidences) if confidences else None
    evidence_quality = config.evidence_quality(mean_confidence)
    clipped_count = sum(detection.clipped for detection in record.detections)
    audit_flags: list[dict[str, str]] = []
    if clipped_count:
        audit_flags.append(
            {
                "code": "coordinates_clipped",
                "en": f"{clipped_count} detection box(es) were clipped within tolerance.",
                "zh": f"{clipped_count} 个检测框在容差范围内被裁剪。",
            }
        )
    if evidence_quality == "low":
        audit_flags.append(
            {
                "code": "low_evidence_quality",
                "en": "Mean detection confidence is low; prioritize human review.",
                "zh": "平均检测置信度较低；请优先人工复核。",
            }
        )

    return {
        "formula_version": config.formula_version,
        "source_prediction": source_prediction,
        "source_prediction_sha256": source_sha256,
        "resolved_config_sha256": config_sha256,
        "source_image": record.source_image,
        "model_checkpoint": record.model_checkpoint,
        "confidence_threshold": record.confidence_threshold,
        "image_dimensions": {"width": record.width, "height": record.height},
        "risk_score": risk_score,
        "risk_level": risk_level,
        "recommendation": dict(config.recommendations[risk_level]),
        "class_breakdown": class_breakdown,
        "evidence": {
            "mean_detection_confidence": (
                round(mean_confidence, 6) if mean_confidence is not None else None
            ),
            "quality": evidence_quality,
            "en": "Confidence describes evidence quality and never changes risk_score.",
            "zh": "置信度只描述证据质量，绝不改变 risk_score。",
        },
        "audit_flags": audit_flags,
        "formula": {
            "en": "Per class: max_points × (0.35 × count_factor + 0.65 × coverage_factor).",
            "zh": "每类：最高分 ×（0.35 × 数量因子 + 0.65 × 覆盖因子）。",
        },
        "limitation": dict(config.limitation),
    }
```

- [ ] **Step 4: Verify score determinism and commit**

```bash
uv run pytest tests/test_risk_scoring.py -v
uv run ruff format src/urbanvision_risk/risk/score.py tests/test_risk_scoring.py
uv run ruff check src/urbanvision_risk/risk/score.py tests/test_risk_scoring.py
git add src/urbanvision_risk/risk/score.py tests/test_risk_scoring.py
git commit -m "feat: score explainable maintenance priority"
```

Expected: all score tests pass, including identical risk scores at different confidences.

---

### Task 5: Deterministic Batch Assessment and CLI

**Files:**
- Create: `src/urbanvision_risk/risk/assess.py`
- Create: `tests/test_risk_assessment.py`

**Interfaces:**
- Produces: `assess_predictions(run_name, prediction_name, output_name="risk-001", config_path=None, paths=None) -> Path`; `main() -> int`.
- Filesystem transaction boundary: read and validate every input plus the config first; only then create the immutable output directory. Preserve a partial directory if a later operating-system write fails.

- [ ] **Step 1: Write batch integration tests**

Create `tests/test_risk_assessment.py`:

```python
import csv
import json
from pathlib import Path

import pytest

from urbanvision_risk.errors import ProjectError
from urbanvision_risk.paths import ProjectPaths, get_paths
from urbanvision_risk.risk.assess import assess_predictions


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "risk-v0.2.yaml"


def prediction_payload(box: list[float] | None = None) -> dict[str, object]:
    detections = []
    if box is not None:
        detections.append(
            {
                "class_id": 3,
                "code": "D40",
                "name_en": "Pothole",
                "name_zh": "坑洞",
                "confidence": 0.8,
                "bbox_xyxy": box,
            }
        )
    return {
        "source_image": "/tmp/road.jpg",
        "model_checkpoint": "/tmp/best.pt",
        "confidence_threshold": 0.25,
        "image_dimensions": {"width": 100, "height": 100},
        "detections": detections,
        "counts": {"D00": 0, "D10": 0, "D20": 0, "D40": len(detections)},
    }


def write_prediction(paths: ProjectPaths, name: str, payload: object) -> Path:
    directory = paths.predictions / "china-baseline-001" / "prediction-001"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def assess(paths: ProjectPaths, output_name: str = "risk-001") -> Path:
    return assess_predictions(
        "china-baseline-001",
        "prediction-001",
        output_name=output_name,
        config_path=CONFIG_PATH,
        paths=paths,
    )


def test_batch_writes_ranked_auditable_artifacts(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)
    write_prediction(paths, "b.json", prediction_payload([0, 0, 10, 10]))
    write_prediction(paths, "a.json", prediction_payload([0, 0, 10, 10]))

    output = assess(paths)

    per_image = sorted((output / "per-image").glob("*-risk.json"))
    assert [path.name for path in per_image] == ["a-risk.json", "b-risk.json"]
    assert (output / "risk-summary.json").is_file()
    assert (output / "ranking.csv").is_file()
    assert (output / "risk-config-resolved.yaml").is_file()
    with (output / "ranking.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["source_prediction"] for row in rows] == ["a.json", "b.json"]
    assert rows[0]["D40_count"] == "1"
    assert "D40_coverage_ratio" in rows[0]
    assert "D40_score_contribution" in rows[0]
    summary = json.loads((output / "risk-summary.json").read_text(encoding="utf-8"))
    assert summary["file_count"] == 2
    assert len(summary["input_digest_sha256"]) == 64
    assert len(summary["resolved_config_sha256"]) == 64


def test_invalid_json_fails_before_output_creation(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)
    bad = write_prediction(paths, "broken.json", {})
    bad.write_text("{not-json}\n", encoding="utf-8")

    with pytest.raises(ProjectError, match="E402"):
        assess(paths)

    assert not (paths.risks / "china-baseline-001").exists()


def test_empty_prediction_directory_fails_before_output_creation(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)
    (paths.predictions / "china-baseline-001" / "prediction-001").mkdir(
        parents=True
    )

    with pytest.raises(ProjectError, match="E402"):
        assess(paths)

    assert not paths.risks.exists()


def test_existing_output_is_preserved(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)
    write_prediction(paths, "a.json", prediction_payload([]))
    output = paths.risks / "china-baseline-001" / "prediction-001" / "risk-001"
    output.mkdir(parents=True)
    marker = output / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(ProjectError, match="E204"):
        assess(paths)

    assert marker.read_text(encoding="utf-8") == "keep"


def test_new_output_name_reproduces_scores_and_digests(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)
    write_prediction(paths, "a.json", prediction_payload([0, 0, 10, 10]))

    first = assess(paths, "risk-001")
    second = assess(paths, "risk-002")

    first_risk = json.loads((first / "per-image" / "a-risk.json").read_text())
    second_risk = json.loads((second / "per-image" / "a-risk.json").read_text())
    first_summary = json.loads((first / "risk-summary.json").read_text())
    second_summary = json.loads((second / "risk-summary.json").read_text())
    assert first_risk == second_risk
    assert first_summary["input_digest_sha256"] == second_summary["input_digest_sha256"]
    assert first_summary["resolved_config_sha256"] == second_summary["resolved_config_sha256"]
```

- [ ] **Step 2: Run the batch tests and verify RED**

```bash
uv run pytest tests/test_risk_assessment.py -v
```

Expected: collection fails because `urbanvision_risk.risk.assess` does not exist.

- [ ] **Step 3: Implement preflight, provenance, ranking, and serialization**

Create `src/urbanvision_risk/risk/assess.py`:

```python
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import statistics
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from urbanvision_risk.data.voc import CLASS_INFO
from urbanvision_risk.detection.config import validate_run_name
from urbanvision_risk.errors import ProjectError, report_error
from urbanvision_risk.paths import ProjectPaths, get_paths
from urbanvision_risk.risk.config import load_risk_config, resolved_config_yaml
from urbanvision_risk.risk.schema import validate_prediction_payload
from urbanvision_risk.risk.score import score_prediction


def _json_text(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _prediction_error(context: str) -> ProjectError:
    return ProjectError(
        "E402",
        "预测 JSON 损坏、不完整或目录为空",
        "Prediction JSON is malformed, incomplete, or the directory is empty",
        "检查或重新生成指定的预测 JSON",
        "Inspect or regenerate the named prediction JSON",
        context,
    )


def _write_error(output_dir: Path) -> ProjectError:
    return ProjectError(
        "E404",
        "风险结果写入失败；不完整目录已保留",
        "Risk output failed; the incomplete directory was preserved",
        "检查磁盘空间和权限，然后使用新的 --output-name",
        "Check disk space and permissions, then use a new --output-name",
        str(output_dir),
    )


def _ranking_fields() -> list[str]:
    fields = [
        "rank",
        "source_prediction",
        "source_image",
        "risk_score",
        "risk_level",
        "evidence_quality",
        "mean_detection_confidence",
    ]
    for details in CLASS_INFO.values():
        code = details["code"]
        fields.extend(
            [
                f"{code}_count",
                f"{code}_coverage_ratio",
                f"{code}_score_contribution",
            ]
        )
    return fields


def _ranking_row(rank: int, result: dict[str, Any]) -> dict[str, object]:
    evidence = result["evidence"]
    row: dict[str, object] = {
        "rank": rank,
        "source_prediction": result["source_prediction"],
        "source_image": result["source_image"],
        "risk_score": result["risk_score"],
        "risk_level": result["risk_level"],
        "evidence_quality": evidence["quality"],
        "mean_detection_confidence": evidence["mean_detection_confidence"],
    }
    for item in result["class_breakdown"]:
        code = item["code"]
        row[f"{code}_count"] = item["count"]
        row[f"{code}_coverage_ratio"] = item["coverage_ratio"]
        row[f"{code}_score_contribution"] = item["score_contribution"]
    return row


def _summary(
    *,
    run_name: str,
    prediction_name: str,
    output_name: str,
    source_dir: Path,
    input_digest: str,
    config_digest: str,
    formula_version: str,
    ranked: list[tuple[str, dict[str, Any]]],
) -> dict[str, object]:
    scores = [float(result["risk_score"]) for _, result in ranked]
    risk_levels = Counter({level: 0 for level in ("low", "moderate", "high", "critical")})
    evidence_levels = Counter(
        {level: 0 for level in ("not_applicable", "low", "moderate", "high")}
    )
    class_totals = Counter({details["code"]: 0 for details in CLASS_INFO.values()})
    for _, result in ranked:
        risk_levels[result["risk_level"]] += 1
        evidence_levels[result["evidence"]["quality"]] += 1
        for item in result["class_breakdown"]:
            class_totals[item["code"]] += item["count"]
    return {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "run_name": run_name,
        "prediction_name": prediction_name,
        "output_name": output_name,
        "source_directory": str(source_dir.resolve()),
        "file_count": len(ranked),
        "input_digest_sha256": input_digest,
        "resolved_config_sha256": config_digest,
        "formula_version": formula_version,
        "score_statistics": {
            "minimum": min(scores),
            "mean": round(statistics.fmean(scores), 4),
            "median": round(statistics.median(scores), 4),
            "maximum": max(scores),
        },
        "risk_level_counts": dict(risk_levels),
        "evidence_quality_counts": dict(evidence_levels),
        "detection_counts": dict(class_totals),
        "top_priority": [
            {
                "rank": rank,
                "source_prediction": filename,
                "risk_score": result["risk_score"],
                "risk_level": result["risk_level"],
            }
            for rank, (filename, result) in enumerate(ranked[:10], start=1)
        ],
    }


def assess_predictions(
    run_name: str,
    prediction_name: str,
    output_name: str = "risk-001",
    *,
    config_path: Path | None = None,
    paths: ProjectPaths | None = None,
) -> Path:
    validate_run_name(run_name)
    validate_run_name(prediction_name)
    validate_run_name(output_name)
    active_paths = paths or get_paths()
    source_dir = active_paths.predictions / run_name / prediction_name
    if not source_dir.is_dir():
        raise ProjectError(
            "E201",
            "预测结果目录不存在",
            "Prediction result directory does not exist",
            "检查 --run-name 和 --prediction-name",
            "Check --run-name and --prediction-name",
            str(source_dir),
        )
    output_dir = active_paths.risks / run_name / prediction_name / output_name
    if output_dir.exists():
        raise ProjectError(
            "E204",
            "风险输出目录已经存在",
            "Risk output directory already exists",
            "保留现有结果，并使用新的 --output-name",
            "Keep the existing result and use a new --output-name",
            str(output_dir),
        )

    config = load_risk_config(config_path or active_paths.configs / "risk-v0.2.yaml")
    resolved_yaml = resolved_config_yaml(config)
    config_digest = hashlib.sha256(resolved_yaml.encode("utf-8")).hexdigest()
    json_paths = sorted(source_dir.glob("*.json"), key=lambda path: path.name)
    if not json_paths:
        raise _prediction_error(str(source_dir))

    aggregate = hashlib.sha256()
    assessed: list[tuple[str, dict[str, Any]]] = []
    for path in json_paths:
        try:
            raw = path.read_bytes()
            payload = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise _prediction_error(str(path)) from error
        source_digest = hashlib.sha256(raw).hexdigest()
        record = validate_prediction_payload(payload, config, str(path))
        result = score_prediction(
            record,
            config,
            source_prediction=path.name,
            source_sha256=source_digest,
            config_sha256=config_digest,
        )
        assessed.append((path.name, result))
        aggregate.update(path.name.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(source_digest.encode("ascii"))
        aggregate.update(b"\n")

    ranked = sorted(
        assessed,
        key=lambda item: (-float(item[1]["risk_score"]), item[0]),
    )
    summary = _summary(
        run_name=run_name,
        prediction_name=prediction_name,
        output_name=output_name,
        source_dir=source_dir,
        input_digest=aggregate.hexdigest(),
        config_digest=config_digest,
        formula_version=config.formula_version,
        ranked=ranked,
    )
    csv_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(csv_buffer, fieldnames=_ranking_fields())
    writer.writeheader()
    for rank, (_, result) in enumerate(ranked, start=1):
        writer.writerow(_ranking_row(rank, result))

    try:
        output_dir.mkdir(parents=True, exist_ok=False)
        per_image_dir = output_dir / "per-image"
        per_image_dir.mkdir()
        for filename, result in assessed:
            (per_image_dir / f"{Path(filename).stem}-risk.json").write_text(
                _json_text(result), encoding="utf-8"
            )
        (output_dir / "risk-summary.json").write_text(
            _json_text(summary), encoding="utf-8"
        )
        (output_dir / "ranking.csv").write_text(
            csv_buffer.getvalue(), encoding="utf-8"
        )
        (output_dir / "risk-config-resolved.yaml").write_text(
            resolved_yaml, encoding="utf-8"
        )
    except FileExistsError as error:
        raise ProjectError(
            "E204",
            "风险输出目录已经存在",
            "Risk output directory already exists",
            "保留现有结果，并使用新的 --output-name",
            "Keep the existing result and use a new --output-name",
            str(output_dir),
        ) from error
    except OSError as error:
        raise _write_error(output_dir) from error
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assess maintenance priority / 评估维护优先级"
    )
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--prediction-name", required=True)
    parser.add_argument("--output-name", default="risk-001")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    try:
        output = assess_predictions(
            args.run_name,
            args.prediction_name,
            output_name=args.output_name,
            config_path=args.config,
        )
        print(f"[PASS] 风险评估完成 / Risk assessment complete: {output}")
        return 0
    except ProjectError as error:
        return report_error(error, debug=args.debug)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Verify batch behavior and commit**

```bash
uv run pytest tests/test_risk_assessment.py -v
uv run ruff format src/urbanvision_risk/risk/assess.py tests/test_risk_assessment.py
uv run ruff check src/urbanvision_risk/risk/assess.py tests/test_risk_assessment.py
git add src/urbanvision_risk/risk/assess.py tests/test_risk_assessment.py
git commit -m "feat: assess and rank prediction batches"
```

Expected: five batch tests pass; failed preflight leaves no risk directory; existing output and marker remain unchanged.

---

### Task 6: Bilingual Learner Documentation and Final Acceptance

**Files:**
- Create: `tests/test_risk_documentation.py`
- Create: `docs/risk-engine-guide.md`
- Modify: `README.md`
- Modify: `docs/learning-guide.md`
- Modify: `results/README.md`

**Interfaces:**
- Documents the exact CLI, formula, evidence/risk separation, output files, error recovery, and prototype limitation in Chinese and English.
- Leaves `risk-001` unused so the learner can run the first named assessment after the implementation handoff.

- [ ] **Step 1: Write a failing documentation contract**

Create `tests/test_risk_documentation.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMMAND = (
    "uv run python -m urbanvision_risk.risk.assess "
    "--run-name china-baseline-001 "
    "--prediction-name prediction-001 "
    "--output-name risk-001"
)


def test_risk_workflow_is_bilingual_and_safety_bounded() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    guide = (ROOT / "docs" / "risk-engine-guide.md").read_text(encoding="utf-8")
    learning = (ROOT / "docs" / "learning-guide.md").read_text(encoding="utf-8")
    results = (ROOT / "results" / "README.md").read_text(encoding="utf-8")

    assert COMMAND in readme
    assert COMMAND in guide
    assert "count_factor = min(count / 5, 1)" in guide
    assert "coverage_factor = min(sqrt(coverage_ratio / 0.05), 1)" in guide
    assert "confidence never changes risk_score" in guide
    assert "置信度绝不改变 risk_score" in guide
    assert "does not replace a certified engineering safety assessment" in guide
    assert "不能替代经过认证的工程安全鉴定" in guide
    assert "Lesson 09" in learning
    assert "risks/" in results
```

- [ ] **Step 2: Run the documentation test and verify RED**

```bash
uv run pytest tests/test_risk_documentation.py -v
```

Expected: failure because `docs/risk-engine-guide.md` and the v0.2 links do not exist.

- [ ] **Step 3: Write the standalone bilingual risk guide**

Create `docs/risk-engine-guide.md`:

````markdown
# UrbanVision-Risk v0.2 Risk Engine / 风险引擎指南

## What it does / 它做什么

**English:** v0.2 reads the JSON files produced by v0.1 and ranks images for human maintenance review. It does not run YOLO again, use the network, or call a cloud API.

**中文：** v0.2 读取 v0.1 已生成的 JSON，把图片按人工维护复核优先级排序。它不会再次运行 YOLO，不访问网络，也不调用云 API。

## Run one batch / 运行一批数据

From the repository root / 从仓库根目录运行：

```bash
uv run python -m urbanvision_risk.risk.assess --run-name china-baseline-001 --prediction-name prediction-001 --output-name risk-001
```

The command first validates all 198 prediction JSON files. It creates output only after every input passes. Existing output is never overwritten.

命令会先验证全部 198 个预测 JSON。只有所有输入都通过后才创建输出；已有输出绝不覆盖。

## Formula / 公式

For each class D00, D10, D20, and D40 / 分别对 D00、D10、D20、D40 计算：

```text
count_factor = min(count / 5, 1)
coverage_factor = min(sqrt(coverage_ratio / 0.05), 1)
class_score = class_max_points × (0.35 × count_factor + 0.65 × coverage_factor)
risk_score = round(min(100, sum(class_score)), 1)
```

Class maximum points are D00=15, D10=20, D20=25, and D40=40. `coverage_ratio` uses the exact union of same-class boxes, so overlapping pixels are counted once.

类别最高分是 D00=15、D10=20、D20=25、D40=40。`coverage_ratio` 使用同类检测框的精确并集，所以重叠像素只计算一次。

Risk levels / 风险等级：low `[0,20)`、moderate `[20,40)`、high `[40,70)`、critical `[70,100]`。

## Confidence is separate / 置信度单独处理

Detection confidence describes evidence quality; confidence never changes risk_score. Mean confidence below 0.50 is low evidence, 0.50–0.75 is moderate, and at least 0.75 is high. No detections means evidence quality is `not_applicable`.

检测置信度描述证据质量；置信度绝不改变 risk_score。平均置信度低于 0.50 是低证据质量，0.50–0.75 是中等，至少 0.75 是高；没有检测结果时证据质量为 `not_applicable`。

This separation is important: a model can be confident about a small defect, or uncertain about a large one. Human review should see both facts.

这种分离很重要：模型可能对一个小缺陷很自信，也可能对一个大缺陷不确定。人工复核需要同时看到两种信息。

## Output files / 输出文件

`results/risks/china-baseline-001/prediction-001/risk-001/` contains / 包含：

- `per-image/*-risk.json`: score, class contributions, provenance hashes, evidence, flags, and bilingual recommendation / 分数、类别贡献、来源哈希、证据、审计标记和双语建议；
- `ranking.csv`: descending score order with filename as deterministic tie-breaker / 按分数降序，同分时按文件名稳定排序；
- `risk-summary.json`: batch digest, statistics, counts, and top ten / 批次摘要哈希、统计、计数和前十名；
- `risk-config-resolved.yaml`: the exact validated settings used / 本次实际使用且验证过的完整配置。

## Error recovery / 错误恢复

| Code | English | 中文 |
|---|---|---|
| E201 | Prediction directory or config is missing; check names and paths. | 预测目录或配置不存在；检查名称和路径。 |
| E204 | Output exists; keep it and choose a new output name. | 输出已存在；保留它并换一个输出名。 |
| E401 | Configuration violates a formula constraint. | 配置违反公式约束。 |
| E402 | JSON is malformed, incomplete, or the directory is empty. | JSON 损坏、不完整，或目录为空。 |
| E403 | Geometry, class metadata, or counts contradict each other. | 几何、类别信息或计数互相矛盾。 |
| E404 | A write failed; the partial directory is preserved for inspection. | 写入失败；保留不完整目录供检查。 |

Never manually change v0.1 prediction JSON to make an error disappear. Regenerate the prediction or fix the named configuration field.

不要为了消除错误而手工修改 v0.1 预测 JSON。请重新生成预测，或修复错误中指出的配置字段。

## Safety boundary / 安全边界

This heuristic maintenance-priority score does not replace a certified engineering safety assessment. A score of zero means only that this model detected no current maintenance priority; it does not mean the road is safe. The prototype has no physical scale, GPS, traffic exposure, pavement history, or calibrated engineering severity labels. A human engineer decides inspection, closure, and repair actions.

此启发式维护优先级分数不能替代经过认证的工程安全鉴定。零分只表示本模型当前未检测到维护优先项，不代表道路安全。原型没有物理尺度、GPS、交通暴露、路面历史或经过标定的工程严重度标签。检查、封闭和维修措施必须由人类工程人员决定。
````

- [ ] **Step 4: Link v0.2 from the existing documentation**

In `README.md`, change the two opening version sentences to:

```markdown
**中文：** 面向城市基础设施智能巡检与风险评估的端侧 AI 项目。v0.1 完成道路缺陷检测，v0.2 把预测转换成可解释、可审计的人工维护复核优先级。

**English:** An on-device AI project for urban-infrastructure inspection and risk assessment. Version 0.1 detects road damage; v0.2 turns predictions into explainable, auditable priorities for human maintenance review.
```

Append after the v0.1 prediction command in `README.md`:

```markdown

# v0.2: score an existing prediction batch; this does not rerun YOLO
uv run python -m urbanvision_risk.risk.assess --run-name china-baseline-001 --prediction-name prediction-001 --output-name risk-001
```

Append to `Generated Artifacts / 生成物`:

```markdown
- `results/risks/<run>/<prediction>/<output>/`: per-image risk JSON, deterministic ranking, summary, and resolved config / 单图风险 JSON、确定性排序、摘要和实际配置。
```

Append to `Learning Guide / 学习指南`:

```markdown

The v0.2 formula, output schema, recovery steps, and safety boundary are explained in [`docs/risk-engine-guide.md`](docs/risk-engine-guide.md).

v0.2 的公式、输出结构、恢复步骤和安全边界见 [`docs/risk-engine-guide.md`](docs/risk-engine-guide.md)。
```

Append to `docs/learning-guide.md`:

```markdown

## Lesson 09 — Explainable Maintenance Priority / 可解释维护优先级

**中文：** v0.2 不重新运行模型，而是读取预测 JSON。它分别计算每类缺陷的数量因子和检测框并集覆盖因子，再按固定权重生成 0–100 的维护复核优先级。置信度只描述证据质量，不进入风险公式。

**English:** v0.2 does not rerun the model; it reads prediction JSON. It combines each class's capped count factor and exact box-union coverage factor into a 0–100 maintenance-review priority. Confidence reports evidence quality and does not enter the risk formula.

File / 文件: `src/urbanvision_risk/risk/score.py`, `configs/risk-v0.2.yaml`

Command / 命令: `uv run python -m urbanvision_risk.risk.assess --run-name china-baseline-001 --prediction-name prediction-001 --output-name risk-001`

Expected / 预期: 198 per-image risk JSON files, a deterministic ranking CSV, a batch summary, and the resolved configuration; no YOLO inference log.

**复习问题 / Review question:** Why must confidence remain separate from risk_score? / 为什么置信度必须与 risk_score 分开？
```

Append to `results/README.md`:

```markdown
- `risks/`: explainable per-image maintenance priorities, deterministic ranking CSV, batch summary, and resolved configuration / 可解释单图维护优先级、确定性排序 CSV、批次摘要和实际配置。
```

- [ ] **Step 5: Run documentation and complete automated acceptance**

```bash
uv run pytest tests/test_risk_documentation.py -v
uv run pytest tests/test_risk_config.py tests/test_risk_geometry.py tests/test_risk_schema.py tests/test_risk_scoring.py tests/test_risk_assessment.py tests/test_risk_documentation.py -v
uv run pytest -q
uv run ruff format --check src tests
uv run ruff check src tests
uv run python -m urbanvision_risk.environment
git diff --check
git status --short
```

Expected:

- the risk-focused suite passes;
- the full suite reports `70 passed`;
- formatting and lint checks pass;
- environment reports Python 3.11, PyTorch, real MPS tensor operation, and final PASS;
- only intended v0.2 files are tracked as changed.

- [ ] **Step 6: Commit documentation**

```bash
git add README.md docs/learning-guide.md docs/risk-engine-guide.md results/README.md tests/test_risk_documentation.py
git commit -m "docs: add bilingual v0.2 risk guide"
```

- [ ] **Step 7: Run the real 198-image acceptance without consuming the learner's `risk-001` name**

First confirm the verification output name is unused:

```bash
test ! -e results/risks/china-baseline-001/prediction-001/risk-verification-001
```

Expected: exit code 0 and no text. If it already exists, preserve it and select the next unused name; never remove or overwrite it.

Run:

```bash
uv run python -m urbanvision_risk.risk.assess --run-name china-baseline-001 --prediction-name prediction-001 --output-name risk-verification-001
```

Expected: one bilingual PASS in seconds, with no Ultralytics/YOLO model summary or inference progress because v0.2 reads JSON only.

Verify the artifact count and summary:

```bash
rg --files results/risks/china-baseline-001/prediction-001/risk-verification-001/per-image | wc -l
uv run python -c 'import json; from pathlib import Path; p=Path("results/risks/china-baseline-001/prediction-001/risk-verification-001/risk-summary.json"); s=json.loads(p.read_text()); print(s["file_count"], s["score_statistics"], s["risk_level_counts"], s["evidence_quality_counts"])'
sed -n '1,6p' results/risks/china-baseline-001/prediction-001/risk-verification-001/ranking.csv
```

Expected: `198` per-image files; summary `file_count` is `198`; CSV contains one header plus highest-priority rows. Record the real score distribution in the handoff without calling it a safety verdict.

- [ ] **Step 8: Re-run final verification after all commits**

```bash
uv run pytest -q
uv run ruff format --check src tests
uv run ruff check src tests
git status --short --branch
git log --oneline --decorate -7
```

Expected: `70 passed`, both Ruff commands pass, the worktree is clean, and the branch contains the six focused v0.2 commits plus design commit `e333711`.

## Acceptance Checklist / 验收清单

- [ ] Existing v0.1 JSON and JPG artifacts remain byte-for-byte untouched.
- [ ] The runtime path imports no Ultralytics code and performs no network access.
- [ ] All JSON and YAML inputs are validated before an output directory is created.
- [ ] Same-class overlap is counted once through exact rectangle-union area.
- [ ] The approved formula and thresholds are represented in committed YAML and provenance hashes.
- [ ] Confidence changes evidence only, never `risk_score`.
- [ ] Ranking is score-descending and filename-ascending for ties.
- [ ] Per-image JSON, ranking CSV, summary JSON, and resolved YAML are deterministic except documented creation time/output identity.
- [ ] Existing output returns `E204` and remains unchanged; a later write failure preserves partial output.
- [ ] Every learner-facing recommendation, limitation, and recovery message is bilingual.
- [ ] Zero detections is valid but never described as proof that a road is safe.
- [ ] The documentation says this prototype cannot replace certified engineering assessment or human decisions.
- [ ] All 40 v0.1 tests and all 30 new/parameterized v0.2 cases pass.
