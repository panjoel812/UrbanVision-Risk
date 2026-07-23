from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from urbanvision_risk.detection.config import validate_run_name
from urbanvision_risk.paths import ProjectPaths


def _load_object(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def build_review_queue(
    run_name: str,
    paths: ProjectPaths,
    *,
    limit: int = 50,
) -> dict[str, object]:
    """Build a deterministic active-learning queue from immutable inspections."""
    safe_run = validate_run_name(run_name)
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")
    root = paths.inspections / safe_run
    entries: list[dict[str, object]] = []
    if root.is_dir():
        for inspection_dir in sorted(path for path in root.iterdir() if path.is_dir()):
            reliability = _load_object(inspection_dir / "reliability.json")
            manifest = _load_object(inspection_dir / "inspection-manifest.json")
            prediction = _load_object(inspection_dir / "prediction.json")
            risk = _load_object(inspection_dir / "risk.json")
            if not all((reliability, manifest, prediction, risk)):
                continue
            summary = reliability.get("summary")
            if not isinstance(summary, dict):
                continue
            priority = summary.get("active_learning_priority")
            if not isinstance(priority, int | float):
                continue
            entries.append(
                {
                    "inspection_id": inspection_dir.name,
                    "created_at_utc": manifest.get("created_at_utc"),
                    "source_filename": manifest.get("source_filename"),
                    "priority": float(priority),
                    "tier": summary.get("active_learning_tier"),
                    "review_recommended": bool(summary.get("review_recommended")),
                    "accepted_clusters": summary.get("accepted_cluster_count"),
                    "disputed_clusters": summary.get("disputed_cluster_count"),
                    "counts": prediction.get("counts"),
                    "decision_status": risk.get("decision_status"),
                }
            )
    entries.sort(
        key=lambda item: (
            -float(item["priority"]),
            str(item["created_at_utc"] or ""),
            str(item["inspection_id"]),
        )
    )
    selected = entries[:limit]
    return {
        "schema_version": "active-learning-queue-v2.0.0",
        "run_name": safe_run,
        "local_only": True,
        "candidate_count": len(entries),
        "returned_count": len(selected),
        "items": selected,
    }
