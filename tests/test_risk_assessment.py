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
    assert summary["top_priority"][0]["source_prediction"] == "a.json"


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

    first_risk = json.loads((first / "per-image" / "a-risk.json").read_text())
    second_risk = json.loads((second / "per-image" / "a-risk.json").read_text())
    first_summary = json.loads((first / "risk-summary.json").read_text())
    second_summary = json.loads((second / "risk-summary.json").read_text())
    assert first_risk == second_risk
    assert first_summary["input_digest_sha256"] == second_summary["input_digest_sha256"]
    assert first_summary["resolved_config_sha256"] == second_summary["resolved_config_sha256"]


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
