from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from urbanvision_risk.data.download import (
    ARCHIVE_NAME,
    RAW_RELATIVE_PATH,
    RDD2022_CHINA_MOTORBIKE_URL,
    sha256_file,
)
from urbanvision_risk.data.split import split_ids
from urbanvision_risk.data.validate import validate_prepared_dataset
from urbanvision_risk.data.voc import (
    DETECTION_CLASS_INFO,
    parse_voc_annotation,
    to_yolo_lines,
)
from urbanvision_risk.errors import ProjectError, report_error
from urbanvision_risk.paths import get_paths


@dataclass(frozen=True, slots=True)
class ImageAnnotationPair:
    identifier: str
    image: Path
    annotation: Path


def discover_pairs(raw_root: Path) -> dict[str, ImageAnnotationPair]:
    image_index: dict[str, Path] = {}
    images = sorted(
        path for path in raw_root.rglob("*") if path.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    for image in images:
        if image.name in image_index:
            raise ProjectError(
                "E202",
                "发现重复图片文件名",
                "Duplicate image filename found",
                "检查原始数据目录结构",
                "Inspect the raw-data directory structure",
                image.name,
            )
        image_index[image.name] = image

    pairs: dict[str, ImageAnnotationPair] = {}
    for annotation in sorted(raw_root.rglob("*.xml")):
        record = parse_voc_annotation(annotation)
        image = image_index.get(Path(record.filename).name)
        if image is None:
            raise ProjectError(
                "E202",
                "XML 对应的图片不存在",
                "The image referenced by XML is missing",
                "检查原始数据是否完整",
                "Check that the raw dataset is complete",
                f"{annotation}: {record.filename}",
            )
        identifier = annotation.stem
        if identifier in pairs:
            raise ProjectError(
                "E202",
                "发现重复标注标识符",
                "Duplicate annotation identifier found",
                "检查原始数据目录结构",
                "Inspect the raw-data directory structure",
                identifier,
            )
        pairs[identifier] = ImageAnnotationPair(identifier, image, annotation)
    if not pairs:
        raise ProjectError(
            "E201",
            "原始目录中没有 XML 标注",
            "No XML annotations were found in the raw directory",
            "先运行数据下载命令并检查解压目录",
            "Run the download command and inspect the extracted directory",
            str(raw_root),
        )
    return pairs


def _canonical_digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def prepare_dataset(
    raw_root: Path,
    archive_path: Path,
    output_root: Path,
) -> dict[str, object]:
    if not raw_root.is_dir() or not archive_path.is_file():
        raise ProjectError(
            "E201",
            "原始数据目录或压缩包不存在",
            "Raw-data directory or archive is missing",
            "先运行数据下载命令",
            "Run the dataset download command first",
            f"raw={raw_root}, archive={archive_path}",
        )
    if output_root.exists():
        raise ProjectError(
            "E204",
            "处理后数据目录已经存在",
            "Processed dataset directory already exists",
            "保留现有结果，或检查后把整个目录移入废纸篓",
            "Keep it or inspect and move the entire directory to Trash",
            str(output_root),
        )
    staging = output_root.parent / f".{output_root.name}.staging"
    if staging.exists():
        raise ProjectError(
            "E204",
            "发现未完成的数据准备目录",
            "An unfinished preparation directory exists",
            "检查该目录，并在确认后移入废纸篓",
            "Inspect it and move it to Trash after confirmation",
            str(staging),
        )

    pairs = discover_pairs(raw_root)
    split = split_ids(pairs)
    split_members = {"train": split.train, "val": split.val, "test": split.test}
    for split_name in split_members:
        (staging / "images" / split_name).mkdir(parents=True, exist_ok=True)
        (staging / "labels" / split_name).mkdir(parents=True, exist_ok=True)

    for split_name, identifiers in split_members.items():
        for identifier in identifiers:
            pair = pairs[identifier]
            record = parse_voc_annotation(pair.annotation)
            image_target = (
                staging / "images" / split_name / f"{identifier}{pair.image.suffix.lower()}"
            )
            label_target = staging / "labels" / split_name / f"{identifier}.txt"
            shutil.copy2(pair.image, image_target)
            lines = to_yolo_lines(record)
            label_target.write_text(
                "\n".join(lines) + ("\n" if lines else ""),
                encoding="utf-8",
            )

    report = validate_prepared_dataset(staging)
    if not report.ok:
        raise ProjectError(
            "E203",
            "处理后数据验证失败，暂存目录已保留",
            "Prepared-data validation failed; staging was preserved",
            "检查错误并在确认后把暂存目录移入废纸篓",
            "Inspect errors and move the staging directory to Trash after confirmation",
            "\n".join(report.errors),
        )

    archive_digest = sha256_file(archive_path)
    digest_inputs: dict[str, object] = {
        "archive_sha256": archive_digest,
        "classes": DETECTION_CLASS_INFO,
        "seed": 42,
        "ratios": {"train": 0.8, "val": 0.1, "test": 0.1},
        "splits": split_members,
    }
    manifest: dict[str, object] = {
        "source_url": RDD2022_CHINA_MOTORBIKE_URL,
        "archive_sha256": archive_digest,
        "prepared_at": datetime.now(UTC).isoformat(),
        "seed": 42,
        "ratios": {"train": 0.8, "val": 0.1, "test": 0.1},
        "file_counts": report.image_counts,
        "object_counts": report.object_counts,
        "invalid_records": 0,
        "input_digest": _canonical_digest(digest_inputs),
    }
    (staging / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    staging.rename(output_root)
    return manifest


def main(debug: bool = False) -> int:
    paths = get_paths()
    try:
        manifest = prepare_dataset(
            raw_root=paths.raw / RAW_RELATIVE_PATH,
            archive_path=paths.downloads / ARCHIVE_NAME,
            output_root=paths.processed / "rdd2022-china-motorbike-repair-v1.1",
        )
        print(
            "[PASS] 数据准备完成 / Dataset preparation complete\n"
            f"{json.dumps(manifest, ensure_ascii=False, indent=2)}"
        )
        return 0
    except ProjectError as error:
        return report_error(error, debug=debug)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare RDD2022 / 准备 RDD2022")
    parser.add_argument("--debug", action="store_true")
    raise SystemExit(main(debug=parser.parse_args().debug))
