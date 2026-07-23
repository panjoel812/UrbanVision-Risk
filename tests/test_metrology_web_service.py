import io
import json
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from urbanvision_risk.app.metrology_service import LocalMetrologyService
from urbanvision_risk.errors import ProjectError
from urbanvision_risk.paths import get_paths


def _encode_image(array: np.ndarray, image_format: str = "PNG") -> bytes:
    if array.ndim == 3:
        array = cv2.cvtColor(array, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(array.astype(np.uint8))
    buffer = io.BytesIO()
    image.save(buffer, format=image_format)
    return buffer.getvalue()


def _straight_sample() -> tuple[bytes, bytes]:
    source = np.full((221, 421, 3), 128, dtype=np.uint8)
    mask = np.zeros((221, 421), dtype=np.uint8)
    cv2.line(mask, (50, 110), (350, 110), 255, 11)
    source[mask > 0] = 28
    return _encode_image(source), _encode_image(mask)


def _aruco_sample() -> tuple[bytes, bytes]:
    source = np.full((600, 900, 3), 230, dtype=np.uint8)
    mask = np.zeros((600, 900), dtype=np.uint8)
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_100)
    placements = {
        17: (90, 90),
        23: (690, 90),
        42: (690, 390),
        56: (90, 390),
    }
    for marker_id, (x, y) in placements.items():
        marker = cv2.aruco.generateImageMarker(dictionary, marker_id, 120)
        source[y : y + 120, x : x + 120] = cv2.cvtColor(
            marker, cv2.COLOR_GRAY2BGR
        )
    cv2.line(mask, (250, 300), (650, 300), 255, 13)
    source[mask > 0] = 25
    return _encode_image(source), _encode_image(mask)


def test_pixel_web_run_is_local_immutable_and_path_private(tmp_path: Path) -> None:
    source, mask = _straight_sample()
    service = LocalMetrologyService(
        paths=get_paths(tmp_path),
        id_factory=lambda: "web-pixel-001",
    )

    result = service.analyze_bytes(
        source_content=source,
        source_filename="/Users/private/road.png",
        source_content_type="image/png",
        mask_content=mask,
        mask_filename="browser-mask.png",
        mask_content_type="image/png",
        calibration_mode="pixel",
        uncertainty_samples=0,
    )

    assert result["run_id"] == "web-pixel-001"
    assert result["local_only"] is True
    assert result["measurement"]["measurement_space"] == "pixel_only"
    assert result["measurement"]["decision_boundary"]["physical_measurement_valid"] is False
    assert "rectified-overlay.jpg" not in result["artifacts"]
    measurement_path = service.artifact_path("web-pixel-001", "measurement.json")
    text = measurement_path.read_text(encoding="utf-8")
    assert "/Users/" not in text
    assert '"filename": "road.png"' in text

    with pytest.raises(ProjectError, match="E204"):
        service.analyze_bytes(
            source_content=source,
            source_filename="road.png",
            source_content_type="image/png",
            mask_content=mask,
            mask_filename="mask.png",
            mask_content_type="image/png",
            calibration_mode="pixel",
            uncertainty_samples=0,
        )


def test_manual_web_calibration_returns_physical_geometry(tmp_path: Path) -> None:
    source, mask = _straight_sample()
    service = LocalMetrologyService(
        paths=get_paths(tmp_path),
        id_factory=lambda: "web-manual-001",
    )

    result = service.analyze_bytes(
        source_content=source,
        source_filename="road.png",
        source_content_type="image/png",
        mask_content=mask,
        mask_filename="mask.png",
        mask_content_type="image/png",
        calibration_mode="manual",
        manual_points=json.dumps(
            [[10.0, 10.0], [410.0, 10.0], [410.0, 210.0], [10.0, 210.0]]
        ),
        physical_width=2.0,
        physical_height=1.0,
        unit="m",
        pixels_per_unit=200.0,
        point_sigma_pixels=1.0,
        uncertainty_samples=8,
    )

    measurement = result["measurement"]
    assert measurement["measurement_space"] == "rectified_physical_plane"
    assert measurement["physical_geometry"]["unit"] == "m"
    assert measurement["physical_geometry"]["centerline_network_length"] == pytest.approx(
        1.5, abs=0.03
    )
    assert measurement["run"]["input_evidence"]["calibration"]["mode"] == (
        "manual_four_point"
    )
    assert "rectified-overlay.jpg" in result["artifacts"]


def test_aruco_web_calibration_preserves_detection_quality(tmp_path: Path) -> None:
    source, mask = _aruco_sample()
    service = LocalMetrologyService(
        paths=get_paths(tmp_path),
        id_factory=lambda: "web-aruco-001",
    )

    result = service.analyze_bytes(
        source_content=source,
        source_filename="aruco-road.png",
        source_content_type="image/png",
        mask_content=mask,
        mask_filename="mask.png",
        mask_content_type="image/png",
        calibration_mode="aruco",
        physical_width=3.0,
        physical_height=1.5,
        unit="m",
        pixels_per_unit=100.0,
        point_sigma_pixels=1.0,
        uncertainty_samples=8,
    )

    evidence = result["measurement"]["run"]["input_evidence"]["calibration"]
    assert evidence["mode"] == "aruco_auto"
    assert evidence["field_detection"]["detected_id_count"] == 4
    assert evidence["field_detection"]["minimum_marker_perimeter_pixels"] > 400
    assert result["measurement"]["physical_geometry"]["centerline_network_length"] > 1


def test_web_demo_exposes_all_calibrated_artifacts(tmp_path: Path) -> None:
    service = LocalMetrologyService(
        paths=get_paths(tmp_path),
        id_factory=lambda: "web-demo-001",
    )

    result = service.demo()

    assert result["measurement"]["measurement_space"] == "rectified_physical_plane"
    assert result["measurement"]["run"]["input_evidence"]["kind"] == (
        "deterministic_web_demo"
    )
    assert "overlay.jpg" in result["artifacts"]
    assert "rectified-overlay.jpg" in result["artifacts"]
    assert "rectified-width-heatmap.png" in result["artifacts"]


def test_web_service_fails_closed_for_bad_masks_and_artifact_names(
    tmp_path: Path,
) -> None:
    source, _ = _straight_sample()
    empty_mask = _encode_image(np.zeros((221, 421), dtype=np.uint8))
    wrong_mask = _encode_image(np.ones((100, 100), dtype=np.uint8) * 255)
    service = LocalMetrologyService(
        paths=get_paths(tmp_path),
        id_factory=lambda: "web-invalid-001",
    )

    for mask in (empty_mask, wrong_mask):
        with pytest.raises(ProjectError, match="E506"):
            service.analyze_bytes(
                source_content=source,
                source_filename="road.png",
                source_content_type="image/png",
                mask_content=mask,
                mask_filename="mask.png",
                mask_content_type="image/png",
                calibration_mode="pixel",
            )

    with pytest.raises(ProjectError, match="E201"):
        service.artifact_path("web-invalid-001", "../private.txt")
