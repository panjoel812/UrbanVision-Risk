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


def _existing_output_error(output_dir: Path) -> ProjectError:
    return ProjectError(
        "E204",
        "风险输出目录已经存在",
        "Risk output directory already exists",
        "保留现有结果，并使用新的 --output-name",
        "Keep the existing result and use a new --output-name",
        str(output_dir),
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


def _output_creation_error(output_dir: Path) -> ProjectError:
    return ProjectError(
        "E404",
        "风险输出目录创建失败；未留下不完整目录",
        "Risk output directory creation failed; no partial output directory exists",
        "检查磁盘空间、父目录和权限，修复后重试",
        "Check disk space, the parent directory, and permissions, then retry",
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
    evidence_levels = Counter({level: 0 for level in ("not_applicable", "low", "moderate", "high")})
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
        raise _existing_output_error(output_dir)

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
    except FileExistsError as error:
        raise _existing_output_error(output_dir) from error
    except OSError as error:
        raise _output_creation_error(output_dir) from error

    try:
        per_image_dir = output_dir / "per-image"
        per_image_dir.mkdir()
        for filename, result in assessed:
            (per_image_dir / f"{Path(filename).stem}-risk.json").write_text(
                _json_text(result), encoding="utf-8"
            )
        (output_dir / "risk-summary.json").write_text(_json_text(summary), encoding="utf-8")
        (output_dir / "ranking.csv").write_text(csv_buffer.getvalue(), encoding="utf-8")
        (output_dir / "risk-config-resolved.yaml").write_text(resolved_yaml, encoding="utf-8")
    except OSError as error:
        raise _write_error(output_dir) from error
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Assess maintenance priority / 评估维护优先级")
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
