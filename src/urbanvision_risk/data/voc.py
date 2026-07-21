from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from urbanvision_risk.errors import ProjectError

CLASS_INFO = {
    0: {"code": "D00", "name_en": "Longitudinal crack", "name_zh": "纵向裂缝"},
    1: {"code": "D10", "name_en": "Transverse crack", "name_zh": "横向裂缝"},
    2: {"code": "D20", "name_en": "Alligator crack", "name_zh": "网状裂缝"},
    3: {"code": "D40", "name_en": "Pothole", "name_zh": "坑洞"},
}
CLASS_TO_INDEX = {details["code"]: index for index, details in CLASS_INFO.items()}
IGNORED_CLASS_CODES = frozenset({"Repair"})


@dataclass(frozen=True, slots=True)
class VocObject:
    class_code: str
    box: tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class VocRecord:
    filename: str
    width: int
    height: int
    objects: tuple[VocObject, ...]


def _required_text(parent: ET.Element, path: str, xml_path: Path) -> str:
    value = parent.findtext(path)
    if value is None or not value.strip():
        raise ProjectError(
            "E202",
            "XML 缺少必需字段",
            "XML is missing a required field",
            "检查或重新下载原始标注",
            "Inspect or redownload the source annotation",
            f"{xml_path}: {path}",
        )
    return value.strip()


def parse_voc_annotation(path: Path) -> VocRecord:
    try:
        root = ET.parse(path).getroot()
        filename = _required_text(root, "filename", path)
        width = int(_required_text(root, "size/width", path))
        height = int(_required_text(root, "size/height", path))
    except (ET.ParseError, ValueError) as error:
        raise ProjectError(
            "E202",
            "XML 标注损坏",
            "XML annotation is malformed",
            "检查或重新下载原始标注",
            "Inspect or redownload the source annotation",
            str(path),
        ) from error
    if width <= 0 or height <= 0:
        raise ProjectError(
            "E203",
            "图片尺寸非法",
            "Image dimensions are invalid",
            "检查 XML 的 size 字段",
            "Inspect the XML size fields",
            str(path),
        )

    objects: list[VocObject] = []
    for item in root.findall("object"):
        class_code = _required_text(item, "name", path)
        if class_code in IGNORED_CLASS_CODES:
            continue
        if class_code not in CLASS_TO_INDEX:
            raise ProjectError(
                "E203",
                "发现未知缺陷类别",
                "Unknown damage class found",
                "仅保留 D00、D10、D20、D40",
                "Keep only D00, D10, D20, and D40",
                f"{path}: {class_code}",
            )
        try:
            box = tuple(
                float(_required_text(item, f"bndbox/{coordinate}", path))
                for coordinate in ("xmin", "ymin", "xmax", "ymax")
            )
        except ValueError as error:
            raise ProjectError(
                "E203",
                "边界框坐标不是数字",
                "Bounding-box coordinates are not numeric",
                "检查 XML 的 bndbox 字段",
                "Inspect the XML bndbox fields",
                str(path),
            ) from error
        voc_box_to_yolo(box, (width, height))
        objects.append(VocObject(class_code=class_code, box=box))
    return VocRecord(
        filename=filename,
        width=width,
        height=height,
        objects=tuple(objects),
    )


def voc_box_to_yolo(
    box: tuple[float, float, float, float],
    image_size: tuple[int, int],
) -> tuple[float, float, float, float]:
    xmin, ymin, xmax, ymax = box
    width, height = image_size
    values = (*box, float(width), float(height))
    if not all(math.isfinite(value) for value in values):
        valid = False
    else:
        valid = (
            width > 0 and height > 0 and 0 <= xmin < xmax <= width and 0 <= ymin < ymax <= height
        )
    if not valid:
        raise ProjectError(
            "E203",
            "边界框超界或尺寸为零",
            "Bounding box is out of bounds or has zero size",
            "检查 XML 坐标和图片尺寸",
            "Inspect XML coordinates and image dimensions",
            f"box={box}, image_size={image_size}",
        )
    return (
        ((xmin + xmax) / 2) / width,
        ((ymin + ymax) / 2) / height,
        (xmax - xmin) / width,
        (ymax - ymin) / height,
    )


def to_yolo_lines(record: VocRecord) -> list[str]:
    lines: list[str] = []
    for item in record.objects:
        normalized = voc_box_to_yolo(item.box, (record.width, record.height))
        values = " ".join(f"{value:.6f}" for value in normalized)
        lines.append(f"{CLASS_TO_INDEX[item.class_code]} {values}")
    return lines
