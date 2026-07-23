from __future__ import annotations

import argparse

import cv2
import numpy as np

from urbanvision_risk.errors import ProjectError, report_error
from urbanvision_risk.metrology.calibration import PlanarCalibration
from urbanvision_risk.metrology.measure import create_metrology_run


def synthetic_field_sample(seed: int = 42) -> tuple[
    np.ndarray,
    np.ndarray,
    PlanarCalibration,
]:
    generator = np.random.default_rng(seed)
    height, width = 480, 640
    texture = generator.normal(0.0, 8.0, size=(height, width)).astype(np.float32)
    gradient = np.linspace(112.0, 72.0, height, dtype=np.float32)[:, None]
    gray = np.clip(gradient + texture, 0, 255).astype(np.uint8)
    source = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    mask = np.zeros((height, width), dtype=np.uint8)

    main_crack = np.asarray(
        [
            [92, 72],
            [140, 110],
            [185, 145],
            [225, 194],
            [280, 238],
            [330, 291],
            [375, 340],
            [430, 390],
            [492, 428],
        ],
        dtype=np.int32,
    )
    branch_a = np.asarray(
        [[280, 238], [320, 214], [365, 199], [415, 205]],
        dtype=np.int32,
    )
    branch_b = np.asarray(
        [[375, 340], [410, 318], [448, 310], [487, 322]],
        dtype=np.int32,
    )
    cv2.polylines(mask, [main_crack], False, 255, 11, cv2.LINE_AA)
    cv2.polylines(mask, [branch_a], False, 255, 7, cv2.LINE_AA)
    cv2.polylines(mask, [branch_b], False, 255, 5, cv2.LINE_AA)
    mask = (mask > 64).astype(np.uint8) * 255
    source[mask > 0] = (28, 28, 28)

    calibration = PlanarCalibration(
        image_points=((48.0, 45.0), (584.0, 61.0), (602.0, 448.0), (31.0, 457.0)),
        physical_width=1.2,
        physical_height=0.8,
        unit="m",
        pixels_per_unit=400.0,
        point_sigma_pixels=1.5,
    )
    points = np.rint(calibration.points_array()).astype(np.int32)
    for point in points:
        cv2.drawMarker(
            source,
            tuple(int(value) for value in point),
            (30, 220, 255),
            cv2.MARKER_CROSS,
            18,
            2,
            cv2.LINE_AA,
        )
    return source, mask, calibration


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the v3 calibrated metrology demo / 运行 v3 标定量测演示"
    )
    parser.add_argument("--output-name", default="metrology-demo-001")
    parser.add_argument("--uncertainty-samples", type=int, default=64)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    try:
        source, mask, calibration = synthetic_field_sample(args.seed)
        output = create_metrology_run(
            mask=mask,
            output_name=args.output_name,
            calibration=calibration,
            source_image=source,
            uncertainty_samples=args.uncertainty_samples,
            seed=args.seed,
            input_evidence={
                "kind": "deterministic_synthetic_field_fixture",
                "seed": args.seed,
                "claim_boundary": (
                    "This fixture verifies algorithms and reproducibility; it is not field "
                    "accuracy evidence"
                ),
            },
        )
        print(f"[PASS] v3 量测演示完成 / v3 metrology demo complete: {output}")
        return 0
    except ProjectError as error:
        return report_error(error, debug=args.debug)


if __name__ == "__main__":
    raise SystemExit(main())
