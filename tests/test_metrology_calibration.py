import math

import cv2
import numpy as np
import pytest

from urbanvision_risk.errors import ProjectError
from urbanvision_risk.metrology.calibration import (
    PlanarCalibration,
    calibration_from_dict,
)
from urbanvision_risk.metrology.engine import measure_crack_mask


def _calibration() -> PlanarCalibration:
    return PlanarCalibration(
        image_points=((10.0, 10.0), (410.0, 10.0), (410.0, 210.0), (10.0, 210.0)),
        physical_width=2.0,
        physical_height=1.0,
        unit="m",
        pixels_per_unit=200.0,
        point_sigma_pixels=1.0,
    )


def _straight_crack() -> np.ndarray:
    mask = np.zeros((221, 421), dtype=np.uint8)
    cv2.line(mask, (50, 110), (350, 110), 255, 11)
    return mask


def test_calibration_maps_pixels_to_physical_length_width_and_area() -> None:
    result = measure_crack_mask(
        _straight_crack(),
        calibration=_calibration(),
        uncertainty_samples=24,
        seed=17,
    )

    physical = result["physical_geometry"]
    assert result["measurement_space"] == "rectified_physical_plane"
    assert physical["unit"] == "m"
    assert math.isclose(physical["centerline_network_length"], 1.5, abs_tol=0.03)
    assert 0.04 < physical["width_distribution"]["mean"] < 0.08
    assert physical["foreground_area"] > 0
    assert result["decision_boundary"]["physical_measurement_valid"] is True
    interval = result["uncertainty"]["centerline_network_length"]["interval"]
    assert interval["minimum"] <= physical["centerline_network_length"] <= interval["maximum"]


def test_uncertainty_sampling_is_deterministic_for_a_fixed_seed() -> None:
    first = measure_crack_mask(
        _straight_crack(),
        calibration=_calibration(),
        uncertainty_samples=16,
        seed=91,
    )
    second = measure_crack_mask(
        _straight_crack(),
        calibration=_calibration(),
        uncertainty_samples=16,
        seed=91,
    )

    assert first["uncertainty"] == second["uncertainty"]
    assert first["uncertainty"]["sources"]["monte_carlo_samples_accepted"] == 16
    assert (
        first["uncertainty"]["interpretation"]
        == "sensitivity_interval_not_certified_confidence_interval"
    )


def test_calibration_serialization_round_trips() -> None:
    calibration = _calibration()

    restored = calibration_from_dict(calibration.to_dict())

    assert restored == calibration
    assert restored.rectified_size() == (401, 201)


def test_crossed_or_out_of_frame_calibration_is_rejected() -> None:
    with pytest.raises(ProjectError, match="E501"):
        PlanarCalibration(
            image_points=((10.0, 10.0), (410.0, 210.0), (410.0, 10.0), (10.0, 210.0)),
            physical_width=2.0,
            physical_height=1.0,
            unit="m",
            pixels_per_unit=200.0,
        )

    calibration = _calibration()
    with pytest.raises(ProjectError, match="E501"):
        calibration.validate_for_image((100, 100))
