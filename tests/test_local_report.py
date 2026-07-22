import csv
import hashlib
import json
from pathlib import Path

import pytest

from urbanvision_risk.errors import ProjectError
from urbanvision_risk.paths import ProjectPaths, get_paths
from urbanvision_risk.reporting.build import build_report

RUN = "china-baseline-001"
PREDICTION = "prediction-001"
RISK = "risk-001"
CONFIG_TEXT = "formula_version: risk-v0.2.0\n"
CONFIG_DIGEST = hashlib.sha256(CONFIG_TEXT.encode()).hexdigest()


def _class_breakdown() -> list[dict[str, object]]:
    rows = []
    classes = [
        (0, "D00", "Longitudinal crack", "纵向裂缝", 15.0),
        (1, "D10", "Transverse crack", "横向裂缝", 20.0),
        (2, "D20", "Alligator crack", "网状裂缝", 25.0),
        (3, "D40", "Pothole", "坑洞", 40.0),
    ]
    for class_id, code, name_en, name_zh, maximum in classes:
        rows.append(
            {
                "class_id": class_id,
                "code": code,
                "name_en": name_en,
                "name_zh": name_zh,
                "count": 1 if code == "D40" else 0,
                "union_area_pixels": 100.0 if code == "D40" else 0.0,
                "coverage_ratio": 0.01 if code == "D40" else 0.0,
                "count_factor": 0.2 if code == "D40" else 0.0,
                "coverage_factor": 0.4472136 if code == "D40" else 0.0,
                "maximum_points": maximum,
                "score_contribution": 14.4 if code == "D40" else 0.0,
            }
        )
    return rows


def _risk_payload(name: str, score: float, level: str) -> dict[str, object]:
    return {
        "formula_version": "risk-v0.2.0",
        "source_prediction": f"{name}.json",
        "source_prediction_sha256": "a" * 64,
        "resolved_config_sha256": CONFIG_DIGEST,
        "source_image": f"/tmp/{name}.jpg",
        "model_checkpoint": "/tmp/best.pt",
        "confidence_threshold": 0.25,
        "image_dimensions": {"width": 100, "height": 100},
        "risk_score": score,
        "risk_level": level,
        "recommendation": {"en": "Manual review.", "zh": "人工复核。"},
        "class_breakdown": _class_breakdown(),
        "evidence": {
            "mean_detection_confidence": 0.8,
            "minimum_detection_confidence": 0.7,
            "quality": "high",
            "en": "Confidence never changes risk_score.",
            "zh": "置信度绝不改变 risk_score。",
        },
        "audit_flags": [],
        "formula": {"en": "formula", "zh": "公式", "parameters": {}},
        "limitation": {
            "en": "This does not replace a certified engineering safety assessment.",
            "zh": "这不能替代经过认证的工程安全鉴定。",
        },
    }


def _write_batch(paths: ProjectPaths, *, include_image: bool = True) -> Path:
    risk_dir = paths.risks / RUN / PREDICTION / RISK
    per_image = risk_dir / "per-image"
    per_image.mkdir(parents=True)
    records = [
        _risk_payload("road-a", 14.4, "low"),
        _risk_payload("road-b", 44.0, "high"),
    ]
    for record in records:
        stem = Path(str(record["source_prediction"])).stem
        (per_image / f"{stem}-risk.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if include_image:
            image = paths.predictions / RUN / PREDICTION / f"{stem}-annotated.jpg"
            image.parent.mkdir(parents=True, exist_ok=True)
            image.write_bytes(b"jpeg")

    summary = {
        "created_at_utc": "2026-07-22T00:00:00+00:00",
        "run_name": RUN,
        "prediction_name": PREDICTION,
        "output_name": RISK,
        "source_directory": str(paths.predictions / RUN / PREDICTION),
        "file_count": 2,
        "input_digest_sha256": "c" * 64,
        "resolved_config_sha256": CONFIG_DIGEST,
        "formula_version": "risk-v0.2.0",
        "score_statistics": {"minimum": 14.4, "mean": 29.2, "median": 29.2, "maximum": 44.0},
        "risk_level_counts": {"low": 1, "moderate": 0, "high": 1, "critical": 0},
        "evidence_quality_counts": {
            "not_applicable": 0,
            "low": 0,
            "moderate": 0,
            "high": 2,
        },
        "detection_counts": {"D00": 0, "D10": 0, "D20": 0, "D40": 2},
        "top_priority": [
            {
                "rank": 1,
                "source_prediction": "road-b.json",
                "risk_score": 44.0,
                "risk_level": "high",
            },
            {
                "rank": 2,
                "source_prediction": "road-a.json",
                "risk_score": 14.4,
                "risk_level": "low",
            },
        ],
    }
    (risk_dir / "risk-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (risk_dir / "risk-config-resolved.yaml").write_text(CONFIG_TEXT, encoding="utf-8")

    fieldnames = [
        "rank",
        "source_prediction",
        "source_image",
        "risk_score",
        "risk_level",
        "evidence_quality",
        "mean_detection_confidence",
        "minimum_detection_confidence",
    ]
    for code in ("D00", "D10", "D20", "D40"):
        fieldnames.extend([f"{code}_count", f"{code}_coverage_ratio", f"{code}_score_contribution"])
    with (risk_dir / "ranking.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for rank, record in enumerate(reversed(records), start=1):
            row: dict[str, object] = {
                "rank": rank,
                "source_prediction": record["source_prediction"],
                "source_image": record["source_image"],
                "risk_score": record["risk_score"],
                "risk_level": record["risk_level"],
                "evidence_quality": "high",
                "mean_detection_confidence": 0.8,
                "minimum_detection_confidence": 0.7,
            }
            for code in ("D00", "D10", "D20", "D40"):
                row[f"{code}_count"] = 1 if code == "D40" else 0
                row[f"{code}_coverage_ratio"] = 0.01 if code == "D40" else 0.0
                row[f"{code}_score_contribution"] = 14.4 if code == "D40" else 0.0
            writer.writerow(row)
    return risk_dir


def test_build_report_writes_offline_bilingual_dashboard(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)
    risk_dir = _write_batch(paths)

    output = build_report(RUN, PREDICTION, RISK, paths=paths)

    html = (output / "index.html").read_text(encoding="utf-8")
    manifest = json.loads((output / "report-manifest.json").read_text(encoding="utf-8"))
    assert paths.reports == tmp_path / "results" / "reports"
    assert "UrbanVision-Risk" in html
    assert "维护复核优先级，不是道路安全判定" in html
    assert "Maintenance-review priority, not a road-safety verdict" in html
    assert "road-b.json" in html
    assert "road-b-annotated.jpg" in html
    assert "https://" not in html
    assert "http://" not in html
    assert "fetch(" not in html
    assert "XMLHttpRequest" not in html
    assert "WebSocket" not in html
    assert manifest["file_count"] == 2
    assert manifest["source_risk_directory"] == str(risk_dir.resolve())
    assert manifest["index_html_sha256"] == hashlib.sha256(html.encode()).hexdigest()


def test_report_rejects_existing_output_without_modifying_it(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)
    _write_batch(paths)
    output = paths.reports / RUN / PREDICTION / RISK / "report-001"
    output.mkdir(parents=True)
    marker = output / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(ProjectError, match="E204"):
        build_report(RUN, PREDICTION, RISK, paths=paths)

    assert marker.read_text(encoding="utf-8") == "keep"


def test_report_missing_risk_directory_is_e201(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)

    with pytest.raises(ProjectError, match="E201"):
        build_report(RUN, PREDICTION, RISK, paths=paths)

    assert not paths.reports.exists()


def test_report_rejects_inconsistent_batch_before_output(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)
    risk_dir = _write_batch(paths)
    summary_path = risk_dir / "risk-summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["file_count"] = 3
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    with pytest.raises(ProjectError, match="E501"):
        build_report(RUN, PREDICTION, RISK, paths=paths)

    assert not paths.reports.exists()


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("score_statistics", {"minimum": 14.4, "mean": 99.0, "median": 29.2, "maximum": 44.0}),
        ("detection_counts", {"D00": 0, "D10": 0, "D20": 0, "D40": 99}),
    ),
)
def test_report_rejects_summary_that_disagrees_with_records(
    tmp_path: Path, field: str, value: object
) -> None:
    paths = get_paths(tmp_path)
    risk_dir = _write_batch(paths)
    summary_path = risk_dir / "risk-summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary[field] = value
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    with pytest.raises(ProjectError, match="E501"):
        build_report(RUN, PREDICTION, RISK, paths=paths)

    assert not paths.reports.exists()


def test_report_rejects_config_that_disagrees_with_its_digest(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)
    risk_dir = _write_batch(paths)
    (risk_dir / "risk-config-resolved.yaml").write_text("changed: true\n", encoding="utf-8")

    with pytest.raises(ProjectError, match="E501"):
        build_report(RUN, PREDICTION, RISK, paths=paths)

    assert not paths.reports.exists()


def test_report_rejects_overflowed_number_as_e501(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)
    risk_dir = _write_batch(paths)
    risk_path = risk_dir / "per-image" / "road-b-risk.json"
    payload = json.loads(risk_path.read_text(encoding="utf-8"))
    payload["risk_score"] = 10**400
    risk_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ProjectError, match="E501"):
        build_report(RUN, PREDICTION, RISK, paths=paths)

    assert not paths.reports.exists()


def test_report_rejects_missing_annotated_image_before_output(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)
    _write_batch(paths, include_image=False)

    with pytest.raises(ProjectError, match="E501"):
        build_report(RUN, PREDICTION, RISK, paths=paths)

    assert not paths.reports.exists()
