import json
from pathlib import Path

from urbanvision_risk.paths import get_paths
from urbanvision_risk.reliability.queue import build_review_queue


def _write_inspection(
    root: Path,
    inspection_id: str,
    *,
    priority: float,
    created_at: str,
) -> None:
    directory = root / inspection_id
    directory.mkdir(parents=True)
    payloads = {
        "reliability.json": {
            "summary": {
                "active_learning_priority": priority,
                "active_learning_tier": "high" if priority >= 60 else "low",
                "review_recommended": priority >= 60,
                "accepted_cluster_count": 1,
                "disputed_cluster_count": 1 if priority >= 60 else 0,
            }
        },
        "inspection-manifest.json": {
            "created_at_utc": created_at,
            "source_filename": f"{inspection_id}.jpg",
        },
        "prediction.json": {"counts": {"D00": 1}},
        "risk.json": {"decision_status": "review_required"},
    }
    for filename, payload in payloads.items():
        (directory / filename).write_text(json.dumps(payload), encoding="utf-8")


def test_active_learning_queue_is_ranked_and_contains_no_absolute_paths(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)
    root = paths.inspections / "china-repair-mps-003"
    _write_inspection(root, "inspection-low", priority=12.0, created_at="2026-01-01T00:00:00Z")
    _write_inspection(root, "inspection-high", priority=82.0, created_at="2026-01-02T00:00:00Z")

    queue = build_review_queue("china-repair-mps-003", paths)

    assert queue["candidate_count"] == 2
    assert [item["inspection_id"] for item in queue["items"]] == [
        "inspection-high",
        "inspection-low",
    ]
    assert queue["items"][0]["priority"] == 82.0
    assert str(tmp_path) not in json.dumps(queue)


def test_active_learning_queue_skips_incomplete_or_invalid_records(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)
    incomplete = paths.inspections / "china-repair-mps-003" / "inspection-incomplete"
    incomplete.mkdir(parents=True)
    (incomplete / "reliability.json").write_text("not-json", encoding="utf-8")

    queue = build_review_queue("china-repair-mps-003", paths)

    assert queue["candidate_count"] == 0
    assert queue["items"] == []
