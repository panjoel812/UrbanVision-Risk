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
    counts: Counter[str] = Counter(
        {details["code"]: 0 for details in CLASS_INFO.values()}
    )
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
        payload["message_en"] = (
            "No road damage was detected at the current confidence threshold"
        )
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
    results = model.predict(
        source=str(source),
        conf=confidence,
        device="mps",
        stream=True,
    )
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
