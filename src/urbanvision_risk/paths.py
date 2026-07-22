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
    risks: Path
    reports: Path


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
        risks=results / "risks",
        reports=results / "reports",
    )
