from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from urbanvision_risk.detection.config import validate_run_name
from urbanvision_risk.errors import ProjectError, report_error
from urbanvision_risk.metrology.fiducials import FIELD_MARKER_IDS
from urbanvision_risk.paths import ProjectPaths, get_paths


def _marker_modules(marker_id: int) -> np.ndarray:
    image = cv2.aruco.generateImageMarker(
        cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_100),
        marker_id,
        600,
    )
    module_count = 6
    module_size = image.shape[0] // module_count
    centers = np.arange(module_count) * module_size + module_size // 2
    return image[np.ix_(centers, centers)] == 0


def _marker_svg(position: str, marker_id: int) -> str:
    modules = _marker_modules(marker_id)
    rectangles: list[str] = []
    marker_origin_mm = 10
    module_mm = 50 / modules.shape[0]
    for row, column in np.argwhere(modules):
        x = marker_origin_mm + float(column) * module_mm
        y = marker_origin_mm + float(row) * module_mm
        rectangles.append(
            f'<rect x="{x:.6f}" y="{y:.6f}" width="{module_mm:.6f}" '
            f'height="{module_mm:.6f}" fill="#000"/>'
        )
    body = "\n  ".join(rectangles)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="70mm" height="80mm" viewBox="0 0 70 80">
  <rect x="0.25" y="0.25" width="69.5" height="79.5" fill="#fff" stroke="#999"
        stroke-width="0.5" stroke-dasharray="2 2"/>
  {body}
  <circle cx="35" cy="35" r="1.2" fill="none" stroke="#ff3b30" stroke-width="0.35"/>
  <text x="35" y="69" text-anchor="middle" font-family="Arial,sans-serif"
        font-size="5" font-weight="700">{position} · ID {marker_id}</text>
  <text x="35" y="75" text-anchor="middle" font-family="Arial,sans-serif"
        font-size="2.8">PRINT 100% · DO NOT FIT TO PAGE</text>
</svg>
"""


def generate_field_marker_kit(
    output_name: str = "aruco-field-kit-001",
    *,
    paths: ProjectPaths | None = None,
) -> Path:
    validate_run_name(output_name)
    active_paths = paths or get_paths()
    output_dir = active_paths.metrology / "calibration-targets" / output_name
    if output_dir.exists():
        raise ProjectError(
            "E204",
            "标记套件目录已经存在",
            "The marker-kit directory already exists",
            "保留现有套件并使用新的 --output-name",
            "Keep the existing kit and use a new --output-name",
            str(output_dir),
        )
    try:
        output_dir.mkdir(parents=True, exist_ok=False)
        for position, marker_id in FIELD_MARKER_IDS.items():
            (output_dir / f"marker-{position.lower()}-id{marker_id}.svg").write_text(
                _marker_svg(position, marker_id),
                encoding="utf-8",
            )
        manifest = {
            "schema_version": "field-marker-kit-v3.0.0",
            "dictionary": "DICT_4X4_100",
            "marker_ids": FIELD_MARKER_IDS,
            "tile_size_mm": {"width": 70, "height": 80},
            "printed_marker_size_mm": 50,
            "measurement_reference": "marker centers",
            "print_instruction_zh": "必须按 100% 原始比例打印，禁止适合页面缩放",
            "print_instruction_en": "Print at exactly 100%; disable fit-to-page scaling",
            "field_boundary_zh": (
                "四个标记中心必须在同一道路平面上；中心间真实宽高必须由卷尺独立测量"
            ),
            "field_boundary_en": (
                "All four marker centers must be coplanar with the road; independently "
                "measure their physical center-to-center width and height with a tape"
            ),
        }
        (output_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        raise ProjectError(
            "E504",
            "现场标记套件写入失败；不完整目录已保留",
            "Field marker-kit output failed; the incomplete directory was preserved",
            "检查磁盘空间和权限，然后使用新的 --output-name",
            "Check disk space and permissions, then use a new --output-name",
            str(output_dir),
        ) from error
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a printable field marker kit / 生成可打印现场标记套件"
    )
    parser.add_argument("--output-name", default="aruco-field-kit-001")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    try:
        output = generate_field_marker_kit(args.output_name)
        print(f"[PASS] 标记套件生成完成 / Marker kit complete: {output}")
        return 0
    except ProjectError as error:
        return report_error(error, debug=args.debug)


if __name__ == "__main__":
    raise SystemExit(main())
