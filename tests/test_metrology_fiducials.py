import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from urbanvision_risk.errors import ProjectError
from urbanvision_risk.metrology.fiducials import (
    FIELD_MARKER_IDS,
    calibrate_from_field_markers,
    calibrate_image_file,
    detect_field_markers,
)
from urbanvision_risk.metrology.target import generate_field_marker_kit
from urbanvision_risk.paths import get_paths


def _synthetic_marker_scene() -> tuple[np.ndarray, dict[str, tuple[float, float]]]:
    image = np.full((600, 900), 255, dtype=np.uint8)
    top_lefts = {
        "TL": (90, 90),
        "TR": (690, 90),
        "BR": (690, 390),
        "BL": (90, 390),
    }
    expected_centers: dict[str, tuple[float, float]] = {}
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_100)
    for position, marker_id in FIELD_MARKER_IDS.items():
        marker = cv2.aruco.generateImageMarker(dictionary, marker_id, 120)
        x, y = top_lefts[position]
        image[y : y + 120, x : x + 120] = marker
        expected_centers[position] = (x + 59.5, y + 59.5)
    return image, expected_centers


def test_four_marker_centers_are_detected_in_semantic_order() -> None:
    image, expected = _synthetic_marker_scene()

    points, quality = detect_field_markers(image)

    for point, position in zip(points, ("TL", "TR", "BR", "BL"), strict=True):
        assert np.allclose(point, expected[position], atol=1.0)
    assert quality["detected_id_count"] == 4
    assert quality["minimum_marker_perimeter_pixels"] > 400
    assert quality["calibration_quadrilateral_image_ratio"] > 0.2


def test_marker_scene_builds_a_metric_calibration() -> None:
    image, _ = _synthetic_marker_scene()

    calibration, quality = calibrate_from_field_markers(
        image,
        physical_width=3.0,
        physical_height=1.5,
        unit="m",
        pixels_per_unit=100.0,
    )

    assert calibration.rectified_size() == (301, 151)
    assert calibration.physical_width == 3.0
    assert quality["marker_ids"] == FIELD_MARKER_IDS


def test_missing_marker_fails_closed() -> None:
    image, _ = _synthetic_marker_scene()
    image[390:510, 90:210] = 255

    with pytest.raises(ProjectError, match="E505"):
        detect_field_markers(image)


def test_calibration_file_has_detection_quality_but_omits_absolute_source_path(
    tmp_path: Path,
) -> None:
    image, _ = _synthetic_marker_scene()
    source = tmp_path / "private-field-scene.png"
    output = tmp_path / "field-calibration.json"
    assert cv2.imwrite(str(source), image)

    calibrate_image_file(
        source_image=source,
        output=output,
        physical_width=3.0,
        physical_height=1.5,
        unit="m",
        pixels_per_unit=100.0,
    )

    text = output.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert str(tmp_path) not in text
    assert payload["field_detection"]["source_filename"] == source.name
    assert len(payload["field_detection"]["source_sha256"]) == 64
    assert payload["field_detection"]["minimum_marker_perimeter_pixels"] > 400

    with pytest.raises(ProjectError, match="E204"):
        calibrate_image_file(
            source_image=source,
            output=output,
            physical_width=3.0,
            physical_height=1.5,
            unit="m",
            pixels_per_unit=100.0,
        )


def test_printable_marker_kit_contains_four_svg_targets_and_manifest(
    tmp_path: Path,
) -> None:
    output = generate_field_marker_kit(
        "field-kit-001",
        paths=get_paths(tmp_path),
    )

    svg_paths = sorted(output.glob("*.svg"))
    assert len(svg_paths) == 4
    assert all('width="70mm"' in path.read_text(encoding="utf-8") for path in svg_paths)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["marker_ids"] == FIELD_MARKER_IDS
    assert manifest["measurement_reference"] == "marker centers"

    with pytest.raises(ProjectError, match="E204"):
        generate_field_marker_kit("field-kit-001", paths=get_paths(tmp_path))
