import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from urbanvision_risk.errors import ProjectError
from urbanvision_risk.metrology.calibration import PlanarCalibration
from urbanvision_risk.metrology.measure import create_metrology_run, measure_files
from urbanvision_risk.paths import get_paths


def _sample_arrays() -> tuple[np.ndarray, np.ndarray]:
    source = np.full((160, 240, 3), 120, dtype=np.uint8)
    mask = np.zeros((160, 240), dtype=np.uint8)
    cv2.line(mask, (30, 80), (210, 80), 255, 9)
    source[mask > 0] = 30
    return source, mask


def test_create_run_writes_auditable_pixel_artifacts(tmp_path: Path) -> None:
    source, mask = _sample_arrays()

    output = create_metrology_run(
        mask=mask,
        source_image=source,
        output_name="pixel-run-001",
        uncertainty_samples=0,
        paths=get_paths(tmp_path),
    )

    assert (output / "measurement.json").is_file()
    assert (output / "mask.png").is_file()
    assert (output / "skeleton.png").is_file()
    assert (output / "width-heatmap.png").is_file()
    assert (output / "overlay.jpg").is_file()
    payload = json.loads((output / "measurement.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == "crack-metrology-v3.0.0"
    assert payload["run"]["implementation_version"] == "3.0.0"

    with pytest.raises(ProjectError, match="E204"):
        create_metrology_run(
            mask=mask,
            output_name="pixel-run-001",
            uncertainty_samples=0,
            paths=get_paths(tmp_path),
        )


def test_file_run_omits_absolute_input_paths_and_writes_rectified_artifacts(
    tmp_path: Path,
) -> None:
    source, mask = _sample_arrays()
    source_path = tmp_path / "private-road-photo.png"
    mask_path = tmp_path / "private-mask.png"
    calibration_path = tmp_path / "field-calibration.json"
    assert cv2.imwrite(str(source_path), source)
    assert cv2.imwrite(str(mask_path), mask)
    calibration = PlanarCalibration(
        image_points=((10.0, 20.0), (230.0, 20.0), (230.0, 140.0), (10.0, 140.0)),
        physical_width=1.1,
        physical_height=0.6,
        unit="m",
        pixels_per_unit=160.0,
        point_sigma_pixels=1.0,
    )
    calibration_path.write_text(
        json.dumps(calibration.to_dict()),
        encoding="utf-8",
    )

    output = measure_files(
        mask_path=mask_path,
        source_image_path=source_path,
        calibration_path=calibration_path,
        output_name="metric-run-001",
        uncertainty_samples=8,
        paths=get_paths(tmp_path),
    )

    payload_text = (output / "measurement.json").read_text(encoding="utf-8")
    payload = json.loads(payload_text)
    assert str(tmp_path) not in payload_text
    assert payload["run"]["input_evidence"]["mask"]["filename"] == mask_path.name
    assert len(payload["run"]["input_evidence"]["mask"]["sha256"]) == 64
    assert (output / "rectified-mask.png").is_file()
    assert (output / "rectified-skeleton.png").is_file()
    assert (output / "rectified-width-heatmap.png").is_file()
    assert (output / "rectified-overlay.jpg").is_file()
