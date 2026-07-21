from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from urbanvision_risk.data.voc import CLASS_INFO
from urbanvision_risk.paths import get_paths

SPLITS = ("train", "val", "test")


@dataclass(frozen=True, slots=True)
class ValidationReport:
    image_counts: dict[str, int]
    object_counts: dict[str, int]
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def _validate_label(
    path: Path,
    object_counts: Counter[str],
    errors: list[str],
) -> None:
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        parts = raw_line.split()
        if len(parts) != 5:
            errors.append(f"{path}:{line_number}: label must have 5 values")
            continue
        try:
            class_index = int(parts[0])
            coordinates = tuple(float(value) for value in parts[1:])
        except ValueError:
            errors.append(f"{path}:{line_number}: label values must be numeric")
            continue
        if class_index not in CLASS_INFO:
            errors.append(f"{path}:{line_number}: unknown class index {class_index}")
            continue
        x_center, y_center, width, height = coordinates
        coordinate_ok = all(
            math.isfinite(value) and 0 <= value <= 1 for value in coordinates
        )
        if not coordinate_ok or width <= 0 or height <= 0:
            errors.append(f"{path}:{line_number}: invalid normalized box {coordinates}")
            continue
        if width > 1 or height > 1 or x_center < 0 or y_center < 0:
            errors.append(f"{path}:{line_number}: normalized box is outside [0, 1]")
            continue
        object_counts[CLASS_INFO[class_index]["code"]] += 1


def validate_prepared_dataset(dataset_root: Path) -> ValidationReport:
    errors: list[str] = []
    image_counts: dict[str, int] = {}
    object_counts: Counter[str] = Counter(
        {details["code"]: 0 for details in CLASS_INFO.values()}
    )
    seen_stems: dict[str, str] = {}

    for split in SPLITS:
        image_dir = dataset_root / "images" / split
        label_dir = dataset_root / "labels" / split
        if not image_dir.is_dir() or not label_dir.is_dir():
            errors.append(f"{split}: image or label directory is missing")
            image_counts[split] = 0
            continue
        images = sorted(
            path
            for path in image_dir.iterdir()
            if path.suffix.lower() in {".jpg", ".jpeg", ".png"}
        )
        image_counts[split] = len(images)
        image_stems = {path.stem for path in images}
        label_stems = {path.stem for path in label_dir.glob("*.txt")}
        for missing in sorted(image_stems - label_stems):
            errors.append(f"{split}/{missing}: image has no label")
        for missing in sorted(label_stems - image_stems):
            errors.append(f"{split}/{missing}: label has no image")

        for image_path in images:
            previous_split = seen_stems.setdefault(image_path.stem, split)
            if previous_split != split:
                errors.append(
                    f"{image_path.stem}: identifier appears in multiple splits: "
                    f"{previous_split}, {split}"
                )
            try:
                with Image.open(image_path) as image:
                    image.verify()
            except (OSError, UnidentifiedImageError):
                errors.append(f"{image_path}: image cannot be opened")
            label_path = label_dir / f"{image_path.stem}.txt"
            if label_path.is_file():
                _validate_label(label_path, object_counts, errors)

    return ValidationReport(
        image_counts=image_counts,
        object_counts=dict(object_counts),
        errors=tuple(errors),
    )


def main() -> int:
    dataset_root = get_paths().processed / "rdd2022-china-motorbike"
    report = validate_prepared_dataset(dataset_root)
    for split, count in report.image_counts.items():
        print(f"[INFO] {split} 图片数量 / image count: {count}")
    print(f"[INFO] 缺陷实例 / object counts: {report.object_counts}")
    if report.ok:
        print("[PASS] 数据验证通过 / Dataset validation passed")
        return 0
    for error in report.errors:
        print(f"[ERROR E203] 数据记录无效 / Invalid dataset record: {error}")
    print("[FAIL] 数据验证失败 / Dataset validation failed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
