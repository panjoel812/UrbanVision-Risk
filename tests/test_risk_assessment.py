import csv
import hashlib
import json
from pathlib import Path

import pytest

from urbanvision_risk.errors import ProjectError
from urbanvision_risk.paths import ProjectPaths, get_paths
from urbanvision_risk.risk.assess import assess_predictions
from urbanvision_risk.risk.config import load_risk_config, resolved_config_yaml

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
    b_path = write_prediction(paths, "b.json", prediction_payload([0, 0, 10, 10]))
    a_path = write_prediction(paths, "a.json", prediction_payload([0, 0, 10, 10]))

    output = assess(paths)

    per_image = sorted((output / "per-image").glob("*-risk.json"))
    assert [path.name for path in per_image] == ["a-risk.json", "b-risk.json"]
    assert (output / "risk-summary.json").is_file()
    assert (output / "ranking.csv").is_file()
    assert (output / "risk-config-resolved.yaml").is_file()
    with (output / "ranking.csv").open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert reader.fieldnames == [
        "rank",
        "source_prediction",
        "source_image",
        "risk_score",
        "risk_level",
        "evidence_quality",
        "mean_detection_confidence",
        "minimum_detection_confidence",
        "D00_count",
        "D00_coverage_ratio",
        "D00_score_contribution",
        "D10_count",
        "D10_coverage_ratio",
        "D10_score_contribution",
        "D20_count",
        "D20_coverage_ratio",
        "D20_score_contribution",
        "D40_count",
        "D40_coverage_ratio",
        "D40_score_contribution",
    ]
    assert [row["source_prediction"] for row in rows] == ["a.json", "b.json"]
    assert rows[0]["D40_count"] == "1"
    assert "D40_coverage_ratio" in rows[0]
    assert "D40_score_contribution" in rows[0]
    assert rows[0]["minimum_detection_confidence"] == "0.8"

    aggregate = hashlib.sha256()
    for source_path in (a_path, b_path):
        source_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
        aggregate.update(source_path.name.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(source_sha256.encode("ascii"))
        aggregate.update(b"\n")
    expected_input_digest = aggregate.hexdigest()
    resolved_yaml = resolved_config_yaml(load_risk_config(CONFIG_PATH)).encode("utf-8")
    expected_config_digest = hashlib.sha256(resolved_yaml).hexdigest()

    summary = json.loads((output / "risk-summary.json").read_text(encoding="utf-8"))
    assert summary["run_name"] == "china-baseline-001"
    assert summary["prediction_name"] == "prediction-001"
    assert summary["output_name"] == "risk-001"
    assert summary["source_directory"] == str(a_path.parent.resolve())
    assert summary["file_count"] == 2
    assert summary["input_digest_sha256"] == expected_input_digest
    assert summary["resolved_config_sha256"] == expected_config_digest
    assert summary["formula_version"] == "risk-v0.2.0"
    assert summary["score_statistics"] == {
        "minimum": 14.4,
        "mean": 14.4,
        "median": 14.4,
        "maximum": 14.4,
    }
    assert summary["risk_level_counts"] == {
        "low": 2,
        "moderate": 0,
        "high": 0,
        "critical": 0,
    }
    assert summary["evidence_quality_counts"] == {
        "not_applicable": 0,
        "low": 0,
        "moderate": 0,
        "high": 2,
    }
    assert summary["detection_counts"] == {"D00": 0, "D10": 0, "D20": 0, "D40": 2}
    assert summary["top_priority"] == [
        {
            "rank": 1,
            "source_prediction": "a.json",
            "risk_score": 14.4,
            "risk_level": "low",
        },
        {
            "rank": 2,
            "source_prediction": "b.json",
            "risk_score": 14.4,
            "risk_level": "low",
        },
    ]
    assert (output / "risk-config-resolved.yaml").read_bytes() == resolved_yaml


def test_higher_score_ranks_before_lexically_earlier_filename(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)
    write_prediction(paths, "a.json", prediction_payload([0, 0, 10, 10]))
    write_prediction(paths, "z.json", prediction_payload([0, 0, 30, 30]))

    output = assess(paths)

    with (output / "ranking.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["source_prediction"] for row in rows] == ["z.json", "a.json"]
    assert float(rows[0]["risk_score"]) > float(rows[1]["risk_score"])


def test_missing_prediction_directory_uses_e201(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)

    with pytest.raises(ProjectError, match="E201"):
        assess(paths)

    assert not paths.risks.exists()


def test_invalid_json_fails_before_output_creation(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)
    bad = write_prediction(paths, "broken.json", {})
    bad.write_text("{not-json}\n", encoding="utf-8")

    with pytest.raises(ProjectError, match="E402"):
        assess(paths)

    assert not (paths.risks / "china-baseline-001").exists()


def test_later_invalid_prediction_fails_before_output_creation(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)
    write_prediction(paths, "a.json", prediction_payload([0, 0, 10, 10]))
    bad = write_prediction(paths, "z.json", {})
    bad.write_text("{not-json}\n", encoding="utf-8")

    with pytest.raises(ProjectError, match="E402"):
        assess(paths)

    assert not paths.risks.exists()


def test_empty_prediction_directory_fails_before_output_creation(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)
    (paths.predictions / "china-baseline-001" / "prediction-001").mkdir(parents=True)

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

    assert (first / "per-image" / "a-risk.json").read_bytes() == (
        second / "per-image" / "a-risk.json"
    ).read_bytes()
    assert (first / "ranking.csv").read_bytes() == (second / "ranking.csv").read_bytes()
    assert (first / "risk-config-resolved.yaml").read_bytes() == (
        second / "risk-config-resolved.yaml"
    ).read_bytes()
    first_summary = json.loads((first / "risk-summary.json").read_text())
    second_summary = json.loads((second / "risk-summary.json").read_text())
    first_summary.pop("created_at_utc")
    second_summary.pop("created_at_utc")
    assert first_summary.pop("output_name") == "risk-001"
    assert second_summary.pop("output_name") == "risk-002"
    assert first_summary == second_summary


def test_write_failure_preserves_partial_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = get_paths(tmp_path)
    write_prediction(paths, "a.json", prediction_payload([0, 0, 10, 10]))
    output = paths.risks / "china-baseline-001" / "prediction-001" / "risk-001"
    original_write_text = Path.write_text

    def fail_summary(path: Path, data: str, **kwargs: object) -> int:
        if path.name == "risk-summary.json":
            raise OSError("simulated disk failure")
        return original_write_text(path, data, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_summary)

    with pytest.raises(ProjectError, match="E404") as caught:
        assess(paths)

    assert "不完整目录已保留" in str(caught.value)
    assert "incomplete directory was preserved" in str(caught.value)
    assert output.is_dir()
    assert (output / "per-image" / "a-risk.json").is_file()


def test_initial_output_directory_failure_does_not_claim_preservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = get_paths(tmp_path)
    write_prediction(paths, "a.json", prediction_payload([0, 0, 10, 10]))
    output = paths.risks / "china-baseline-001" / "prediction-001" / "risk-001"
    original_mkdir = Path.mkdir

    def fail_output_creation(path: Path, *args: object, **kwargs: object) -> None:
        if path == output:
            raise OSError("simulated parent permission failure")
        original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fail_output_creation)

    with pytest.raises(ProjectError, match="E404") as caught:
        assess(paths)

    message = str(caught.value)
    assert "目录创建失败" in message
    assert "directory creation failed" in message
    assert "不完整目录已保留" not in message
    assert "incomplete directory was preserved" not in message
    assert "检查磁盘空间、父目录和权限，修复后重试" in message
    assert "Check disk space, the parent directory, and permissions, then retry" in message
    assert not output.exists()
