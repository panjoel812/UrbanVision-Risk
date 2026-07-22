from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import statistics
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from urbanvision_risk.data.voc import CLASS_INFO
from urbanvision_risk.detection.config import validate_run_name
from urbanvision_risk.errors import ProjectError, report_error
from urbanvision_risk.paths import ProjectPaths, get_paths
from urbanvision_risk.reporting.dashboard import render_dashboard

CLASS_CODES = tuple(details["code"] for details in CLASS_INFO.values())
RISK_LEVELS = ("low", "moderate", "high", "critical")
EVIDENCE_LEVELS = ("not_applicable", "low", "moderate", "high")


def _ranking_fields() -> list[str]:
    fields = [
        "rank",
        "source_prediction",
        "source_image",
        "risk_score",
        "risk_level",
        "evidence_quality",
        "mean_detection_confidence",
        "minimum_detection_confidence",
    ]
    for code in CLASS_CODES:
        fields.extend(
            [
                f"{code}_count",
                f"{code}_coverage_ratio",
                f"{code}_score_contribution",
            ]
        )
    return fields


def _missing(path: Path) -> ProjectError:
    return ProjectError(
        "E201",
        "风险报告输入不存在",
        "Risk-report input does not exist",
        "检查运行、预测和风险名称；必要时先运行 v0.2",
        "Check the run, prediction, and risk names; run v0.2 first if needed",
        str(path),
    )


def _invalid(path: Path, detail: str) -> ProjectError:
    return ProjectError(
        "E501",
        "风险报告输入损坏或互相矛盾",
        "Risk-report inputs are malformed or inconsistent",
        "检查指定文件，或使用新名称重新生成 v0.2 风险批次",
        "Inspect the named file or regenerate the v0.2 risk batch with a new name",
        f"{path}: {detail}",
    )


def _existing(output_dir: Path) -> ProjectError:
    return ProjectError(
        "E204",
        "本地报告输出目录已经存在",
        "Local report output directory already exists",
        "保留现有报告，并使用新的 --output-name",
        "Keep the existing report and use a new --output-name",
        str(output_dir),
    )


def _creation_error(output_dir: Path) -> ProjectError:
    return ProjectError(
        "E502",
        "本地报告目录创建失败；未留下半成品",
        "Local report directory creation failed; no partial output remains",
        "检查磁盘空间、父目录和权限，修复后重试",
        "Check disk space, the parent directory, and permissions, then retry",
        str(output_dir),
    )


def _write_error(output_dir: Path) -> ProjectError:
    return ProjectError(
        "E502",
        "本地报告写入失败；半成品目录已保留",
        "Local report writing failed; the partial directory was preserved",
        "检查磁盘空间和权限，并使用新的 --output-name 重试",
        "Check disk space and permissions, then retry with a new --output-name",
        str(output_dir),
    )


def _json_text(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise _missing(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise _invalid(path, "invalid JSON") from error
    if not isinstance(payload, dict):
        raise _invalid(path, "JSON root must be an object")
    return payload


def _mapping(value: object, path: Path, field: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise _invalid(path, field)
    return value


def _text(value: object, path: Path, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _invalid(path, field)
    return value


def _integer(value: object, path: Path, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _invalid(path, field)
    return value


def _number(value: object, path: Path, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _invalid(path, field)
    try:
        result = float(value)
    except OverflowError as error:
        raise _invalid(path, field) from error
    if not result == result or result in (float("inf"), float("-inf")):
        raise _invalid(path, field)
    return result


def _bilingual(value: object, path: Path, field: str) -> dict[str, str]:
    mapping = _mapping(value, path, field)
    if set(mapping) != {"en", "zh"}:
        raise _invalid(path, field)
    return {
        "en": _text(mapping["en"], path, f"{field}.en"),
        "zh": _text(mapping["zh"], path, f"{field}.zh"),
    }


def _validate_summary(
    summary: dict[str, Any],
    path: Path,
    *,
    run_name: str,
    prediction_name: str,
    risk_name: str,
) -> dict[str, object]:
    required = {
        "created_at_utc",
        "run_name",
        "prediction_name",
        "output_name",
        "file_count",
        "input_digest_sha256",
        "resolved_config_sha256",
        "formula_version",
        "score_statistics",
        "risk_level_counts",
        "evidence_quality_counts",
        "detection_counts",
    }
    if not required.issubset(summary):
        raise _invalid(path, "required summary fields")
    if (
        summary["run_name"] != run_name
        or summary["prediction_name"] != prediction_name
        or summary["output_name"] != risk_name
    ):
        raise _invalid(path, "batch identity")
    file_count = _integer(summary["file_count"], path, "file_count")
    if file_count <= 0:
        raise _invalid(path, "file_count")

    score_raw = _mapping(summary["score_statistics"], path, "score_statistics")
    if set(score_raw) != {"minimum", "mean", "median", "maximum"}:
        raise _invalid(path, "score_statistics")
    score_statistics = {
        name: _number(score_raw[name], path, f"score_statistics.{name}")
        for name in ("minimum", "mean", "median", "maximum")
    }
    if not (
        0
        <= score_statistics["minimum"]
        <= score_statistics["mean"]
        <= score_statistics["maximum"]
        <= 100
        and score_statistics["minimum"] <= score_statistics["median"] <= score_statistics["maximum"]
    ):
        raise _invalid(path, "score_statistics range")

    risk_raw = _mapping(summary["risk_level_counts"], path, "risk_level_counts")
    evidence_raw = _mapping(summary["evidence_quality_counts"], path, "evidence_quality_counts")
    detection_raw = _mapping(summary["detection_counts"], path, "detection_counts")
    if set(risk_raw) != set(RISK_LEVELS):
        raise _invalid(path, "risk_level_counts")
    if set(evidence_raw) != set(EVIDENCE_LEVELS):
        raise _invalid(path, "evidence_quality_counts")
    if set(detection_raw) != set(CLASS_CODES):
        raise _invalid(path, "detection_counts")
    risk_counts = {
        level: _integer(risk_raw[level], path, f"risk_level_counts.{level}")
        for level in RISK_LEVELS
    }
    evidence_counts = {
        level: _integer(evidence_raw[level], path, f"evidence_quality_counts.{level}")
        for level in EVIDENCE_LEVELS
    }
    detection_counts = {
        code: _integer(detection_raw[code], path, f"detection_counts.{code}")
        for code in CLASS_CODES
    }
    if sum(risk_counts.values()) != file_count or sum(evidence_counts.values()) != file_count:
        raise _invalid(path, "summary counts do not equal file_count")
    if any(
        value < 0
        for value in (*risk_counts.values(), *evidence_counts.values(), *detection_counts.values())
    ):
        raise _invalid(path, "negative summary count")

    return {
        "created_at_utc": _text(summary["created_at_utc"], path, "created_at_utc"),
        "file_count": file_count,
        "input_digest_sha256": _text(summary["input_digest_sha256"], path, "input_digest_sha256"),
        "resolved_config_sha256": _text(
            summary["resolved_config_sha256"], path, "resolved_config_sha256"
        ),
        "formula_version": _text(summary["formula_version"], path, "formula_version"),
        "score_statistics": score_statistics,
        "risk_level_counts": risk_counts,
        "evidence_quality_counts": evidence_counts,
        "detection_counts": detection_counts,
    }


def _read_ranking(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise _missing(path)
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != _ranking_fields():
                raise _invalid(path, "ranking columns")
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as error:
        raise _invalid(path, "invalid CSV") from error
    if not rows:
        raise _invalid(path, "empty ranking")
    return rows


def _validate_item(
    path: Path,
    payload: dict[str, Any],
    row: dict[str, str],
    *,
    annotated_image: Path,
    output_dir: Path,
    expected_formula_version: str,
    expected_config_sha256: str,
) -> dict[str, object]:
    required = {
        "formula_version",
        "resolved_config_sha256",
        "source_prediction",
        "source_image",
        "risk_score",
        "risk_level",
        "recommendation",
        "class_breakdown",
        "evidence",
        "audit_flags",
        "limitation",
    }
    if not required.issubset(payload):
        raise _invalid(path, "required per-image fields")
    source_prediction = _text(payload["source_prediction"], path, "source_prediction")
    formula_version = _text(payload["formula_version"], path, "formula_version")
    config_sha256 = _text(payload["resolved_config_sha256"], path, "resolved_config_sha256")
    risk_score = _number(payload["risk_score"], path, "risk_score")
    risk_level = _text(payload["risk_level"], path, "risk_level")
    source_image = _text(payload["source_image"], path, "source_image")
    if formula_version != expected_formula_version or config_sha256 != expected_config_sha256:
        raise _invalid(path, "formula version or resolved config digest differs from summary")
    if source_prediction != row["source_prediction"]:
        raise _invalid(path, "source_prediction differs from ranking")
    if source_image != row["source_image"]:
        raise _invalid(path, "source_image differs from ranking")
    try:
        ranking_score = float(row["risk_score"])
    except (TypeError, ValueError, OverflowError) as error:
        raise _invalid(path, "ranking risk_score") from error
    if not 0 <= risk_score <= 100:
        raise _invalid(path, "risk_score range")
    if risk_score != ranking_score or risk_level != row["risk_level"]:
        raise _invalid(path, "score or level differs from ranking")
    if risk_level not in RISK_LEVELS:
        raise _invalid(path, "risk_level")
    if not annotated_image.is_file():
        raise _invalid(annotated_image, "annotated image is missing")

    evidence = _mapping(payload["evidence"], path, "evidence")
    evidence_required = {
        "mean_detection_confidence",
        "minimum_detection_confidence",
        "quality",
        "en",
        "zh",
    }
    if not evidence_required.issubset(evidence):
        raise _invalid(path, "evidence")
    quality = _text(evidence["quality"], path, "evidence.quality")
    if quality not in EVIDENCE_LEVELS or quality != row["evidence_quality"]:
        raise _invalid(path, "evidence quality differs from ranking")
    mean_confidence = evidence["mean_detection_confidence"]
    minimum_confidence = evidence["minimum_detection_confidence"]
    if mean_confidence is not None:
        mean_confidence = _number(mean_confidence, path, "evidence.mean")
    if minimum_confidence is not None:
        minimum_confidence = _number(minimum_confidence, path, "evidence.minimum")
    if quality == "not_applicable" and (
        mean_confidence is not None or minimum_confidence is not None
    ):
        raise _invalid(path, "not_applicable confidence must be null")
    if mean_confidence is not None and not 0 <= mean_confidence <= 1:
        raise _invalid(path, "evidence.mean range")
    if minimum_confidence is not None and not 0 <= minimum_confidence <= 1:
        raise _invalid(path, "evidence.minimum range")
    if (
        mean_confidence is not None
        and minimum_confidence is not None
        and minimum_confidence > mean_confidence
    ):
        raise _invalid(path, "minimum confidence exceeds mean confidence")

    raw_classes = payload["class_breakdown"]
    if not isinstance(raw_classes, list) or len(raw_classes) != len(CLASS_CODES):
        raise _invalid(path, "class_breakdown")
    class_rows: list[dict[str, object]] = []
    observed_codes: list[str] = []
    for index, raw_class in enumerate(raw_classes):
        item = _mapping(raw_class, path, f"class_breakdown[{index}]")
        required_class = {
            "code",
            "name_en",
            "name_zh",
            "count",
            "coverage_ratio",
            "score_contribution",
            "maximum_points",
        }
        if not required_class.issubset(item):
            raise _invalid(path, f"class_breakdown[{index}]")
        code = _text(item["code"], path, f"class_breakdown[{index}].code")
        observed_codes.append(code)
        count = _integer(item["count"], path, f"class_breakdown[{index}].count")
        coverage_ratio = _number(
            item["coverage_ratio"], path, f"class_breakdown[{index}].coverage_ratio"
        )
        contribution = _number(
            item["score_contribution"],
            path,
            f"class_breakdown[{index}].score_contribution",
        )
        maximum_points = _number(
            item["maximum_points"], path, f"class_breakdown[{index}].maximum_points"
        )
        if (
            count < 0
            or not 0 <= coverage_ratio <= 1
            or maximum_points <= 0
            or not 0 <= contribution <= maximum_points
        ):
            raise _invalid(path, f"class_breakdown[{index}] range")
        class_rows.append(
            {
                "code": code,
                "name_en": _text(item["name_en"], path, f"class_breakdown[{index}].name_en"),
                "name_zh": _text(item["name_zh"], path, f"class_breakdown[{index}].name_zh"),
                "count": count,
                "coverage_ratio": coverage_ratio,
                "score_contribution": contribution,
                "maximum_points": maximum_points,
            }
        )
    if tuple(observed_codes) != CLASS_CODES:
        raise _invalid(path, "class order")

    raw_flags = payload["audit_flags"]
    if not isinstance(raw_flags, list):
        raise _invalid(path, "audit_flags")
    flags: list[dict[str, str]] = []
    for index, raw_flag in enumerate(raw_flags):
        flag = _mapping(raw_flag, path, f"audit_flags[{index}]")
        flags.append(
            {
                "code": _text(flag.get("code"), path, f"audit_flags[{index}].code"),
                "en": _text(flag.get("en"), path, f"audit_flags[{index}].en"),
                "zh": _text(flag.get("zh"), path, f"audit_flags[{index}].zh"),
            }
        )

    return {
        "rank": int(row["rank"]),
        "source_prediction": source_prediction,
        "source_image": source_image,
        "annotated_image": Path(os.path.relpath(annotated_image, output_dir)).as_posix(),
        "risk_score": risk_score,
        "risk_level": risk_level,
        "evidence_quality": quality,
        "mean_confidence": mean_confidence,
        "minimum_confidence": minimum_confidence,
        "detection_count": sum(int(item["count"]) for item in class_rows),
        "recommendation": _bilingual(payload["recommendation"], path, "recommendation"),
        "limitation": _bilingual(payload["limitation"], path, "limitation"),
        "flags": flags,
        "classes": class_rows,
    }


def _prepare_payload(
    *,
    run_name: str,
    prediction_name: str,
    risk_name: str,
    risk_dir: Path,
    output_dir: Path,
    paths: ProjectPaths,
) -> tuple[dict[str, object], dict[str, str]]:
    summary_path = risk_dir / "risk-summary.json"
    ranking_path = risk_dir / "ranking.csv"
    config_path = risk_dir / "risk-config-resolved.yaml"
    per_image_dir = risk_dir / "per-image"
    for required_path in (summary_path, ranking_path, config_path, per_image_dir):
        if not required_path.exists():
            raise _missing(required_path)
    if not per_image_dir.is_dir():
        raise _invalid(per_image_dir, "per-image is not a directory")

    summary = _validate_summary(
        _read_json(summary_path),
        summary_path,
        run_name=run_name,
        prediction_name=prediction_name,
        risk_name=risk_name,
    )
    rows = _read_ranking(ranking_path)
    per_image_paths = sorted(per_image_dir.glob("*-risk.json"), key=lambda item: item.name)
    if len(rows) != summary["file_count"] or len(per_image_paths) != summary["file_count"]:
        raise _invalid(risk_dir, "summary, ranking, and per-image counts differ")

    expected_ranks = list(range(1, len(rows) + 1))
    try:
        actual_ranks = [int(row["rank"]) for row in rows]
    except (TypeError, ValueError, OverflowError) as error:
        raise _invalid(ranking_path, "rank") from error
    if actual_ranks != expected_ranks:
        raise _invalid(ranking_path, "ranks must be consecutive")

    per_image_by_name = {
        path.name.removesuffix("-risk.json") + ".json": path for path in per_image_paths
    }
    if set(per_image_by_name) != {row["source_prediction"] for row in rows}:
        raise _invalid(risk_dir, "ranking and per-image filenames differ")

    items = []
    for row in rows:
        source_prediction = row["source_prediction"]
        per_image_path = per_image_by_name[source_prediction]
        annotated_image = (
            paths.predictions
            / run_name
            / prediction_name
            / f"{Path(source_prediction).stem}-annotated.jpg"
        )
        items.append(
            _validate_item(
                per_image_path,
                _read_json(per_image_path),
                row,
                annotated_image=annotated_image,
                output_dir=output_dir,
                expected_formula_version=str(summary["formula_version"]),
                expected_config_sha256=str(summary["resolved_config_sha256"]),
            )
        )

    risk_counts = Counter(str(item["risk_level"]) for item in items)
    evidence_counts = Counter(str(item["evidence_quality"]) for item in items)
    if any(risk_counts[level] != summary["risk_level_counts"][level] for level in RISK_LEVELS):
        raise _invalid(summary_path, "risk level counts differ from per-image records")
    if any(
        evidence_counts[level] != summary["evidence_quality_counts"][level]
        for level in EVIDENCE_LEVELS
    ):
        raise _invalid(summary_path, "evidence counts differ from per-image records")

    scores = [float(item["risk_score"]) for item in items]
    expected_statistics = {
        "minimum": min(scores),
        "mean": round(statistics.fmean(scores), 4),
        "median": round(statistics.median(scores), 4),
        "maximum": max(scores),
    }
    if summary["score_statistics"] != expected_statistics:
        raise _invalid(summary_path, "score statistics differ from per-image records")
    detection_counts = Counter({code: 0 for code in CLASS_CODES})
    for item in items:
        for class_item in item["classes"]:
            detection_counts[str(class_item["code"])] += int(class_item["count"])
    if any(detection_counts[code] != summary["detection_counts"][code] for code in CLASS_CODES):
        raise _invalid(summary_path, "detection counts differ from per-image records")

    digests = {}
    for name, path in (
        ("risk_summary_sha256", summary_path),
        ("ranking_csv_sha256", ranking_path),
        ("resolved_config_sha256", config_path),
    ):
        try:
            digests[name] = _sha256_bytes(path.read_bytes())
        except OSError as error:
            raise _invalid(path, "cannot read artifact") from error
    if digests["resolved_config_sha256"] != summary["resolved_config_sha256"]:
        raise _invalid(config_path, "content does not match resolved_config_sha256")

    generated_at = datetime.now(UTC).isoformat()
    payload: dict[str, object] = {
        "report_version": "report-v0.3.0",
        "generated_at_utc": generated_at,
        "run_name": run_name,
        "prediction_name": prediction_name,
        "risk_name": risk_name,
        "summary": summary,
        "items": items,
    }
    return payload, digests


def build_report(
    run_name: str,
    prediction_name: str,
    risk_name: str,
    output_name: str = "report-001",
    *,
    paths: ProjectPaths | None = None,
) -> Path:
    validate_run_name(run_name)
    validate_run_name(prediction_name)
    validate_run_name(risk_name)
    validate_run_name(output_name)
    active_paths = paths or get_paths()
    risk_dir = active_paths.risks / run_name / prediction_name / risk_name
    if not risk_dir.is_dir():
        raise _missing(risk_dir)
    output_dir = active_paths.reports / run_name / prediction_name / risk_name / output_name
    if output_dir.exists():
        raise _existing(output_dir)

    payload, digests = _prepare_payload(
        run_name=run_name,
        prediction_name=prediction_name,
        risk_name=risk_name,
        risk_dir=risk_dir,
        output_dir=output_dir,
        paths=active_paths,
    )
    html = render_dashboard(payload)
    html_digest = _sha256_bytes(html.encode("utf-8"))
    manifest = {
        "report_version": payload["report_version"],
        "generated_at_utc": payload["generated_at_utc"],
        "run_name": run_name,
        "prediction_name": prediction_name,
        "risk_name": risk_name,
        "output_name": output_name,
        "file_count": payload["summary"]["file_count"],
        "source_risk_directory": str(risk_dir.resolve()),
        **digests,
        "index_html_sha256": html_digest,
    }

    try:
        output_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise _existing(output_dir) from error
    except OSError as error:
        raise _creation_error(output_dir) from error
    try:
        (output_dir / "index.html").write_text(html, encoding="utf-8")
        (output_dir / "report-manifest.json").write_text(_json_text(manifest), encoding="utf-8")
    except OSError as error:
        raise _write_error(output_dir) from error
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build an offline risk dashboard / 生成离线风险仪表板"
    )
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--prediction-name", required=True)
    parser.add_argument("--risk-name", required=True)
    parser.add_argument("--output-name", default="report-001")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    try:
        output = build_report(
            args.run_name,
            args.prediction_name,
            args.risk_name,
            output_name=args.output_name,
        )
        print(f"[PASS] 本地报告生成完成 / Local report complete: {output / 'index.html'}")
        return 0
    except ProjectError as error:
        return report_error(error, debug=args.debug)


if __name__ == "__main__":
    raise SystemExit(main())
