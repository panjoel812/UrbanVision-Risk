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


def _straight_sample(end_x: int = 350) -> tuple[bytes, bytes]:
    source = np.full((221, 421, 3), 128, dtype=np.uint8)
    mask = np.zeros((221, 421), dtype=np.uint8)
    cv2.line(mask, (50, 110), (end_x, 110), 255, 11)
    source[mask > 0] = 28
    return _encode_image(source), _encode_image(mask)


def _transparent_straight_mask() -> bytes:
    mask = np.zeros((221, 421, 4), dtype=np.uint8)
    cv2.line(mask, (50, 110), (350, 110), (255, 255, 255, 255), 11)
    image = Image.fromarray(mask, mode="RGBA")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


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
        source[y : y + 120, x : x + 120] = cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)
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
        manual_points=json.dumps([[10.0, 10.0], [410.0, 10.0], [410.0, 210.0], [10.0, 210.0]]),
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
    assert measurement["run"]["input_evidence"]["calibration"]["mode"] == ("manual_four_point")
    assert "rectified-overlay.jpg" in result["artifacts"]


def test_transparent_browser_mask_keeps_only_painted_pixels(tmp_path: Path) -> None:
    source, _ = _straight_sample()
    service = LocalMetrologyService(
        paths=get_paths(tmp_path),
        id_factory=lambda: "web-transparent-001",
    )

    result = service.analyze_bytes(
        source_content=source,
        source_filename="road.png",
        source_content_type="image/png",
        mask_content=_transparent_straight_mask(),
        mask_filename="browser-mask.png",
        mask_content_type="image/png",
        calibration_mode="pixel",
        uncertainty_samples=0,
    )

    foreground = result["measurement"]["run"]["input_evidence"]["mask"]["foreground_pixels"]
    assert 3900 < foreground < 4200
    assert result["measurement"]["topology"]["component_count"] == 1


def test_local_proposal_is_private_and_human_revision_is_audited(
    tmp_path: Path,
) -> None:
    source, _ = _straight_sample()
    edited_mask = np.zeros((221, 421), dtype=np.uint8)
    cv2.line(edited_mask, (50, 110), (300, 110), 255, 11)
    run_ids = iter(["proposal-draft-001", "proposal-measurement-001"])
    service = LocalMetrologyService(
        paths=get_paths(tmp_path),
        id_factory=lambda: next(run_ids),
        record_id_factory=lambda prefix: f"{prefix}-001",
    )

    proposal = service.propose_mask_bytes(
        source_content=source,
        source_filename="/Users/private/road.png",
        source_content_type="image/png",
        sensitivity=0.55,
    )

    assert proposal["proposal_id"] == "proposal-001"
    assert proposal["candidate_found"] is True
    assert proposal["evidence"]["selection"]["quality_status"] == "usable"
    assert proposal["evidence"]["selection"]["candidate_pixels"] > 3000
    proposal_path = service.proposal_artifact_path(
        "proposal-001",
        "proposal-mask.png",
    )
    evidence_path = service.proposal_artifact_path(
        "proposal-001",
        "evidence.json",
    )
    assert proposal_path.is_file()
    evidence_text = evidence_path.read_text(encoding="utf-8")
    assert "/Users/" not in evidence_text
    assert '"filename": "road.png"' in evidence_text

    draft = service.analyze_bytes(
        source_content=source,
        source_filename="road.png",
        source_content_type="image/png",
        mask_content=proposal_path.read_bytes(),
        mask_filename="browser-mask.png",
        mask_content_type="image/png",
        calibration_mode="pixel",
        uncertainty_samples=0,
        proposal_id="proposal-001",
        review_state="automatic_draft",
    )
    draft_evidence = draft["measurement"]["run"]["input_evidence"]
    draft_revision = draft_evidence["mask"]["proposal_revision"]
    assert draft_evidence["review_state"] == "automatic_draft"
    assert draft_evidence["mask"]["origin"] == "local_proposal_automatic_draft"
    assert draft_revision["human_added_pixels"] == 0
    assert draft_revision["human_removed_pixels"] == 0
    assert draft_revision["proposal_final_iou"] == 1

    result = service.analyze_bytes(
        source_content=source,
        source_filename="road.png",
        source_content_type="image/png",
        mask_content=_encode_image(edited_mask),
        mask_filename="browser-mask.png",
        mask_content_type="image/png",
        calibration_mode="pixel",
        uncertainty_samples=0,
        proposal_id="proposal-001",
    )

    mask_evidence = result["measurement"]["run"]["input_evidence"]["mask"]
    revision = mask_evidence["proposal_revision"]
    assert result["measurement"]["run"]["input_evidence"]["review_state"] == "human_reviewed"
    assert mask_evidence["origin"] == ("local_proposal_submitted_after_human_editing")
    assert revision["proposal_id"] == "proposal-001"
    assert revision["human_removed_pixels"] > 0
    assert revision["human_added_pixels"] == 0
    assert 0 < revision["proposal_final_iou"] < 1


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
    assert result["measurement"]["run"]["input_evidence"]["kind"] == ("deterministic_web_demo")
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

    _, valid_mask = _straight_sample()
    with pytest.raises(ProjectError, match="E506"):
        service.analyze_bytes(
            source_content=source,
            source_filename="road.png",
            source_content_type="image/png",
            mask_content=valid_mask,
            mask_filename="mask.png",
            mask_content_type="image/png",
            calibration_mode="pixel",
            review_state="self_certified",
        )

    with pytest.raises(ProjectError, match="E201"):
        service.artifact_path("web-invalid-001", "../private.txt")


def test_material_plan_uses_calibrated_length_and_records_assumptions(
    tmp_path: Path,
) -> None:
    source, mask = _straight_sample()
    service = LocalMetrologyService(
        paths=get_paths(tmp_path),
        id_factory=lambda: "web-plan-source-001",
        record_id_factory=lambda prefix: f"{prefix}-001",
    )
    service.analyze_bytes(
        source_content=source,
        source_filename="road.png",
        source_content_type="image/png",
        mask_content=mask,
        mask_filename="mask.png",
        mask_content_type="image/png",
        calibration_mode="manual",
        manual_points=json.dumps([[10.0, 10.0], [410.0, 10.0], [410.0, 210.0], [10.0, 210.0]]),
        physical_width=2.0,
        physical_height=1.0,
        unit="m",
        pixels_per_unit=200.0,
        point_sigma_pixels=1.0,
        uncertainty_samples=0,
    )

    result = service.create_maintenance_plan(
        "web-plan-source-001",
        route_width_mm=10,
        route_depth_mm=10,
        waste_percent=10,
        unit_cost_per_liter=20,
    )

    quantities = result["plan"]["quantities"]
    assert quantities["treatment_length_m"] == pytest.approx(1.5, abs=0.03)
    assert quantities["base_fill_volume_liters"] == pytest.approx(0.15, abs=0.003)
    assert quantities["procurement_volume_liters"] == pytest.approx(0.165, abs=0.004)
    assert quantities["estimated_material_cost"] == pytest.approx(3.3, abs=0.08)
    assert result["plan"]["measurement_sha256"]
    assert service.plan_path("web-plan-source-001", "maintenance-001").is_file()

    with pytest.raises(ProjectError, match="E204"):
        service.create_maintenance_plan(
            "web-plan-source-001",
            route_width_mm=10,
            route_depth_mm=10,
            waste_percent=10,
        )


def test_run_history_and_longitudinal_comparison_normalize_units(
    tmp_path: Path,
) -> None:
    source, mask = _straight_sample()
    _, current_mask = _straight_sample(390)
    run_ids = iter(["baseline-001", "current-001"])
    record_ids = iter(["comparison-001"])
    service = LocalMetrologyService(
        paths=get_paths(tmp_path),
        id_factory=lambda: next(run_ids),
        record_id_factory=lambda _prefix: next(record_ids),
    )
    common = {
        "source_content": source,
        "source_content_type": "image/png",
        "mask_content": mask,
        "mask_filename": "mask.png",
        "mask_content_type": "image/png",
        "calibration_mode": "manual",
        "manual_points": json.dumps([[10.0, 10.0], [410.0, 10.0], [410.0, 210.0], [10.0, 210.0]]),
        "pixels_per_unit": 200.0,
        "point_sigma_pixels": 1.0,
        "uncertainty_samples": 0,
    }
    service.analyze_bytes(
        **common,
        source_filename="baseline.png",
        physical_width=2.0,
        physical_height=1.0,
        unit="m",
    )
    service.analyze_bytes(
        **{
            **common,
            "mask_content": current_mask,
            "pixels_per_unit": 2.0,
        },
        source_filename="current.png",
        physical_width=200.0,
        physical_height=100.0,
        unit="cm",
    )

    history = service.list_runs(limit=10)
    assert history["returned_count"] == 2
    assert {item["run_id"] for item in history["items"]} == {
        "baseline-001",
        "current-001",
    }

    result = service.compare_runs(
        baseline_run_id="baseline-001",
        current_run_id="current-001",
        elapsed_days=10,
        length_review_threshold_percent=10,
        width_review_threshold_percent=10,
        match_tolerance_mm=5,
    )

    comparison = result["comparison"]
    length = comparison["changes"]["network_length_m"]
    assert length["baseline"] == pytest.approx(1.5, abs=0.03)
    assert length["current"] == pytest.approx(1.7, abs=0.04)
    assert length["percent"] == pytest.approx(13.333, abs=0.8)
    assert comparison["changes"]["network_length_growth_m_per_day"] == (
        pytest.approx(0.02, abs=0.004)
    )
    assert comparison["schema_version"] == "metrology-comparison-v3.3.0"
    spatial = comparison["spatial_change"]
    assert spatial["alignment_quality"]["status"] == "strong"
    assert spatial["alignment_quality"]["comparable"] is True
    assert spatial["alignment_quality"]["match_tolerance_mm"] == 5
    assert spatial["classification"]["suspected_added_pixels"] > 0
    assert spatial["classification"]["suspected_added_area_cm2"] > 0
    assert result["artifacts"]["change-map.png"].endswith("/comparison-001/change-map.png")
    assert comparison["review_rule"]["human_review_required"] is True
    assert comparison["review_rule"]["status"] == ("change_exceeds_user_threshold")
    assert service.comparison_path("comparison-001").is_file()
    change_map = service.comparison_artifact_path(
        "comparison-001",
        "change-map.png",
    )
    assert change_map.is_file()
    decoded_map = cv2.imread(str(change_map), cv2.IMREAD_COLOR)
    assert decoded_map is not None
    assert np.count_nonzero(decoded_map) > 0


def test_pixel_only_run_cannot_generate_material_or_growth_claims(
    tmp_path: Path,
) -> None:
    source, mask = _straight_sample()
    service = LocalMetrologyService(
        paths=get_paths(tmp_path),
        id_factory=lambda: "pixel-only-001",
    )
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

    assert service.list_runs()["items"] == []
    with pytest.raises(ProjectError, match="E506"):
        service.create_maintenance_plan(
            "pixel-only-001",
            route_width_mm=10,
            route_depth_mm=10,
            waste_percent=10,
        )


def test_spatial_comparison_rejects_mismatched_physical_frames(
    tmp_path: Path,
) -> None:
    source, mask = _straight_sample()
    run_ids = iter(["frame-a-001", "frame-b-001"])
    service = LocalMetrologyService(
        paths=get_paths(tmp_path),
        id_factory=lambda: next(run_ids),
    )
    common = {
        "source_content": source,
        "source_filename": "road.png",
        "source_content_type": "image/png",
        "mask_content": mask,
        "mask_filename": "mask.png",
        "mask_content_type": "image/png",
        "calibration_mode": "manual",
        "manual_points": json.dumps([[10.0, 10.0], [410.0, 10.0], [410.0, 210.0], [10.0, 210.0]]),
        "unit": "m",
        "pixels_per_unit": 200.0,
        "point_sigma_pixels": 1.0,
        "uncertainty_samples": 0,
    }
    service.analyze_bytes(
        **common,
        physical_width=2.0,
        physical_height=1.0,
    )
    service.analyze_bytes(
        **common,
        physical_width=2.2,
        physical_height=1.1,
    )

    with pytest.raises(ProjectError, match="E506") as captured:
        service.compare_runs(
            baseline_run_id="frame-a-001",
            current_run_id="frame-b-001",
            elapsed_days=30,
            length_review_threshold_percent=10,
            width_review_threshold_percent=10,
            match_tolerance_mm=5,
        )

    assert "frame mismatch" in str(captured.value)
