import hashlib
import io
import json
import zipfile
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from urbanvision_risk.app.metrology_service import (
    LocalMetrologyService,
    _assign_curation_groups,
    _bounded_feedback_layers,
    _curation_ratios,
    _deterministic_zip_bytes,
    _difference_hash64,
    _feedback_quality_gate,
    _fingerprint_hamming_distance,
    _near_duplicate_scene_groups,
)
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


def test_active_learning_feedback_layers_are_size_bounded() -> None:
    source = np.full((1200, 1200, 3), 128, dtype=np.uint8)
    proposal = np.zeros((1200, 1200), dtype=np.uint8)
    final = proposal.copy()
    disagreement = proposal.copy()

    exported = _bounded_feedback_layers(
        source,
        proposal,
        final,
        disagreement,
    )

    exported_source, exported_proposal, exported_final, exported_disagreement, scale = (
        exported
    )
    assert scale < 1
    assert exported_source.shape[0] * exported_source.shape[1] <= 512_000
    assert exported_proposal.shape == exported_source.shape[:2]
    assert exported_final.shape == exported_source.shape[:2]
    assert exported_disagreement.shape == exported_source.shape[:2]


def test_active_learning_feedback_zip_is_deterministic_and_sorted() -> None:
    entries = {
        "items/02/data.txt": b"second",
        "items/01/data.txt": b"first",
    }

    first = _deterministic_zip_bytes(entries)
    second = _deterministic_zip_bytes(entries)

    assert first == second
    with zipfile.ZipFile(io.BytesIO(first)) as archive:
        assert archive.namelist() == sorted(entries)
        assert all(
            info.date_time == (1980, 1, 1, 0, 0, 0)
            for info in archive.infolist()
        )


def test_feedback_quality_gate_and_fingerprint_are_deterministic() -> None:
    proposal = np.zeros((40, 40), dtype=np.uint8)
    proposal[10:30, 10:30] = 255
    unchanged = proposal.copy()
    removed = proposal.copy()
    removed[10:20, 10:20] = 0

    accepted = _feedback_quality_gate(
        "accepted_as_proposed",
        proposal,
        unchanged,
    )
    inconsistent = _feedback_quality_gate(
        "missed_crack_added",
        proposal,
        unchanged,
    )
    corrected = _feedback_quality_gate(
        "false_positive_removed",
        proposal,
        removed,
    )

    assert accepted["status"] == "pass"
    assert inconsistent["status"] == "warning"
    assert inconsistent["warning_codes"] == [
        "addition_disposition_without_added_pixels"
    ]
    assert corrected["status"] == "pass"
    assert corrected["removed_pixels"] == 100
    gradient = np.tile(np.arange(40, dtype=np.uint8), (40, 1))
    assert _difference_hash64(gradient) == _difference_hash64(gradient.copy())
    assert len(_difference_hash64(gradient)) == 16


def test_feedback_curation_group_assignment_is_deterministic_and_leakage_safe() -> None:
    ratios = _curation_ratios(0.8, 0.1, 0.1)
    groups = {
        f"{index:064x}": [
            {
                "source_sha256": f"{index:064x}",
                "run_id": f"run-{index:03d}",
                "rank": 1,
                "hotspot_id": f"hotspot-{index:03d}",
            }
        ]
        for index in range(10)
    }

    first = _assign_curation_groups(groups, ratios, seed=42)
    second = _assign_curation_groups(groups, ratios, seed=42)

    assert first == second
    assert {split: len(items) for split, items in first.items()} == {
        "train": 8,
        "val": 1,
        "test": 1,
    }
    source_splits: dict[str, set[str]] = {}
    for split, items in first.items():
        for item in items:
            source_splits.setdefault(str(item["source_sha256"]), set()).add(split)
    assert all(len(splits) == 1 for splits in source_splits.values())
    with pytest.raises(ProjectError, match="ratios sum"):
        _curation_ratios(0.8, 0.15, 0.1)


def test_visual_scene_clustering_is_deterministic_transitive_and_auditable() -> None:
    source_a = "a" * 64
    source_b = "b" * 64
    source_c = "c" * 64
    source_d = "d" * 64
    fingerprints = {
        source_a: {"0000000000000000"},
        source_b: {"0000000000000001"},
        source_c: {"0000000000000003"},
        source_d: {"ffffffffffffffff"},
    }

    first = _near_duplicate_scene_groups(fingerprints, max_hamming_distance=1)
    second = _near_duplicate_scene_groups(fingerprints, max_hamming_distance=1)

    assert first == second
    assert _fingerprint_hamming_distance(
        "0000000000000000",
        "0000000000000003",
    ) == 2
    assert len(first["groups"]) == 2
    assert first["source_to_scene_group"][source_a] == (
        first["source_to_scene_group"][source_c]
    )
    assert first["source_to_scene_group"][source_d] != (
        first["source_to_scene_group"][source_a]
    )
    assert [link["hamming_distance"] for link in first["links"]] == [1, 1]
    with pytest.raises(ProjectError, match="max_scene_hamming_distance"):
        _near_duplicate_scene_groups(fingerprints, max_hamming_distance=17)


def test_feedback_curation_requires_separate_approval_after_all_gates_pass(
    tmp_path: Path,
) -> None:
    paths = get_paths(tmp_path)
    feedback_name = "active-learning-feedback.zip"
    scene_fingerprints = [
        "0000000000000000",
        "0000000000000001",
        "ffffffffffffffff",
        "aaaaaaaaaaaaaaaa",
        "5555555555555555",
        "cccccccccccccccc",
        "3333333333333333",
        "f0f0f0f0f0f0f0f0",
        "0f0f0f0f0f0f0f0f",
        "9696969696969696",
    ]
    for index in range(10):
        run_id = f"feedback-source-{index:03d}"
        run_dir = paths.metrology / run_id
        run_dir.mkdir(parents=True)
        item_root = f"items/01-hotspot-{index:03d}"
        file_digest = f"{index + 100:064x}"
        scene_fingerprint = scene_fingerprints[index]
        manifest = {
            "schema_version": "urbanvision-active-learning-feedback-v1.1.0",
            "run_id": run_id,
            "proposal_id": f"proposal-{index:03d}",
            "created_at_utc": f"2026-07-24T00:00:{index:02d}+00:00",
            "source_sha256": f"{index + 1:064x}",
            "items": [
                {
                    "hotspot_id": f"hotspot-{index:03d}",
                    "rank": 1,
                    "disposition": "accepted_as_proposed",
                    "priority_score": float(100 - index),
                    "source_roi_difference_hash64": scene_fingerprint,
                    "quality_gate": {"status": "pass"},
                    "source_bounding_box": {
                        "x": 1,
                        "y": 2,
                        "width": 30,
                        "height": 40,
                    },
                    "export_crop": {
                        "x": 0,
                        "y": 0,
                        "width": 36,
                        "height": 48,
                        "scale": 1.0,
                        "export_width": 36,
                        "export_height": 48,
                    },
                    "files": {
                        role: {
                            "path": f"{item_root}/{role}.png",
                            "sha256": file_digest,
                        }
                        for role in (
                            "source_roi",
                            "proposal_mask",
                            "final_mask",
                            "disagreement_layer",
                        )
                    },
                }
            ],
        }
        (run_dir / feedback_name).write_bytes(
            _deterministic_zip_bytes(
                {
                    "manifest.json": (
                        json.dumps(manifest, sort_keys=True) + "\n"
                    ).encode()
                }
            )
        )
    service = LocalMetrologyService(
        paths=paths,
        record_id_factory=lambda prefix: f"{prefix}-governed-001",
    )

    result = service.create_feedback_curation(
        seed=42,
        minimum_unique_sources=9,
        privacy_review_confirmed=True,
        label_qa_confirmed=True,
    )
    curation = result["curation"]

    assert curation["status"] == "candidate_plan_requires_training_approval"
    assert curation["training_authorized"] is False
    assert curation["readiness"]["blockers"] == []
    assert curation["selection"]["selected_item_count"] == 10
    assert curation["selection"]["visual_scene_group_count"] == 9
    assert curation["visual_scene_clustering"]["near_duplicate_link_count"] == 1
    assert curation["visual_scene_clustering"]["scene_group_count"] == 9
    assert curation["visual_scene_clustering"][
        "multi_source_scene_group_count"
    ] == 1
    assert {
        split: curation["splits"][split]["item_count"]
        for split in ("train", "val", "test")
    } == {"train": 8, "val": 1, "test": 1}
    assert curation["leakage_audit"]["passed"] is True
    assert curation["leakage_audit"]["visual_scene_group_overlaps"] == {
        "train_val": [],
        "train_test": [],
        "val_test": [],
    }
    split_by_source = {
        source: split
        for split, split_payload in curation["splits"].items()
        for source in split_payload["source_sha256s"]
    }
    assert split_by_source[f"{1:064x}"] == split_by_source[f"{2:064x}"]


def _textured_crack_source() -> bytes:
    random = np.random.default_rng(42)
    road = np.clip(random.normal(170, 12, (360, 540)), 0, 255).astype(np.uint8)
    source = cv2.cvtColor(road, cv2.COLOR_GRAY2BGR)
    cv2.line(source, (35, 280), (490, 80), (35, 35, 35), 5)
    cv2.line(source, (250, 190), (410, 315), (100, 100, 100), 2)
    cv2.line(source, (250, 190), (180, 80), (125, 125, 125), 1)
    return _encode_image(source)


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
    hotspot_path = service.proposal_artifact_path(
        "proposal-001",
        "review-hotspots.png",
    )
    evidence_path = service.proposal_artifact_path(
        "proposal-001",
        "evidence.json",
    )
    assert proposal_path.is_file()
    assert hotspot_path.is_file()
    hotspot = cv2.imdecode(
        np.frombuffer(hotspot_path.read_bytes(), dtype=np.uint8),
        cv2.IMREAD_GRAYSCALE,
    )
    assert hotspot is not None
    assert hotspot.shape == (221, 421)
    assert proposal["evidence"]["review_guidance"]["sample_count"] == 3
    assert proposal["evidence"]["review_hotspots"]["foreground_pixels"] == int(
        np.count_nonzero(hotspot)
    )
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


def test_ranked_hotspot_review_progress_is_validated_and_audited(
    tmp_path: Path,
) -> None:
    source = _textured_crack_source()
    service = LocalMetrologyService(
        paths=get_paths(tmp_path),
        id_factory=lambda: "ranked-review-001",
        record_id_factory=lambda prefix: f"{prefix}-ranked-001",
    )
    proposal = service.propose_mask_bytes(
        source_content=source,
        source_filename="/Users/private/textured-road.png",
        source_content_type="image/png",
        sensitivity=0.55,
    )
    proposal_id = proposal["proposal_id"]
    ranked = proposal["evidence"]["review_guidance"]["ranking"]["ranked_hotspots"]
    reviewed_ids = [ranked[0]["hotspot_id"], ranked[1]["hotspot_id"]]
    decisions = [
        {
            "hotspot_id": reviewed_ids[0],
            "disposition": "accepted_as_proposed",
            "note": "No correction required",
        },
        {
            "hotspot_id": reviewed_ids[1],
            "disposition": "deferred_for_follow_up",
        },
    ]
    mask_path = service.proposal_artifact_path(
        proposal_id,
        "proposal-mask.png",
    )

    with pytest.raises(ProjectError, match="outside the current proposal"):
        service.analyze_bytes(
            source_content=source,
            source_filename="textured-road.png",
            source_content_type="image/png",
            mask_content=mask_path.read_bytes(),
            mask_filename="proposal-mask.png",
            mask_content_type="image/png",
            calibration_mode="pixel",
            uncertainty_samples=0,
            proposal_id=proposal_id,
            reviewed_hotspots='["hotspot-999"]',
        )

    with pytest.raises(ProjectError, match="invalid disposition"):
        service.analyze_bytes(
            source_content=source,
            source_filename="textured-road.png",
            source_content_type="image/png",
            mask_content=mask_path.read_bytes(),
            mask_filename="proposal-mask.png",
            mask_content_type="image/png",
            calibration_mode="pixel",
            uncertainty_samples=0,
            proposal_id=proposal_id,
            reviewed_hotspots=json.dumps([reviewed_ids[0]]),
            hotspot_decisions=json.dumps(
                [
                    {
                        "hotspot_id": reviewed_ids[0],
                        "disposition": "model_was_definitely_correct",
                    }
                ]
            ),
        )

    with pytest.raises(ProjectError, match="same IDs in reviewed_hotspots"):
        service.analyze_bytes(
            source_content=source,
            source_filename="textured-road.png",
            source_content_type="image/png",
            mask_content=mask_path.read_bytes(),
            mask_filename="proposal-mask.png",
            mask_content_type="image/png",
            calibration_mode="pixel",
            uncertainty_samples=0,
            proposal_id=proposal_id,
            reviewed_hotspots=json.dumps([reviewed_ids[0]]),
            hotspot_decisions=json.dumps(decisions),
        )

    result = service.analyze_bytes(
        source_content=source,
        source_filename="textured-road.png",
        source_content_type="image/png",
        mask_content=mask_path.read_bytes(),
        mask_filename="proposal-mask.png",
        mask_content_type="image/png",
        calibration_mode="pixel",
        uncertainty_samples=0,
        proposal_id=proposal_id,
        reviewed_hotspots=json.dumps(reviewed_ids),
        hotspot_decisions=json.dumps(decisions),
    )

    revision = result["measurement"]["run"]["input_evidence"]["mask"][
        "proposal_revision"
    ]
    review = revision["hotspot_review"]
    assert review["status"] == "partial"
    assert review["reviewed_hotspot_ids"] == reviewed_ids
    assert review["reviewed_hotspot_count"] == 2
    assert review["decision_status"] == "partial"
    assert review["decisions"] == decisions
    assert review["decided_hotspot_count"] == 2
    assert review["disposition_counts"]["accepted_as_proposed"] == 1
    assert review["disposition_counts"]["deferred_for_follow_up"] == 1
    assert review["disposition_counts"]["false_positive_removed"] == 0
    assert review["ranked_hotspot_count"] == len(ranked)
    assert 0 < review["ranked_disagreement_pixel_coverage_ratio"] <= 1
    assert 0 < review["ranked_priority_mass_ratio"] <= 1
    assert review["ranked_review_completion_ratio"] == pytest.approx(
        2 / len(ranked),
        abs=1e-8,
    )
    assert 0 < review["ranked_priority_coverage_ratio"] <= 1
    assert review["ranked_decision_completion_ratio"] == pytest.approx(
        2 / len(ranked),
        abs=1e-8,
    )
    assert 0 < review["ranked_decision_priority_coverage_ratio"] <= 1
    feedback_name = "active-learning-feedback.zip"
    assert result["artifacts"][feedback_name].endswith(feedback_name)
    feedback_path = service.artifact_path(result["run_id"], feedback_name)
    with zipfile.ZipFile(feedback_path) as archive:
        names = set(archive.namelist())
        manifest_bytes = archive.read("manifest.json")
        manifest = json.loads(manifest_bytes)
        assert manifest["schema_version"] == (
            "urbanvision-active-learning-feedback-v1.1.0"
        )
        assert manifest["item_count"] == 2
        assert manifest["source_sha256"] == proposal["evidence"]["source"]["sha256"]
        measurement_bytes = (
            feedback_path.parent / "measurement.json"
        ).read_bytes()
        assert manifest["measurement_sha256"] == hashlib.sha256(
            measurement_bytes
        ).hexdigest()
        assert manifest["items"][0]["disposition"] == "accepted_as_proposed"
        assert manifest["items"][0]["note"] == "No correction required"
        assert manifest["items"][0]["quality_gate"]["status"] == "pass"
        assert len(manifest["items"][0]["source_roi_difference_hash64"]) == 16
        assert manifest["items"][1]["disposition"] == "deferred_for_follow_up"
        assert manifest["items"][1]["quality_gate"]["status"] == "deferred"
        assert manifest["quality_summary"]["pass"] == 1
        assert manifest["quality_summary"]["deferred"] == 1
        for item in manifest["items"]:
            export = item["export_crop"]
            assert export["export_width"] * export["export_height"] <= 512_000
            for file_evidence in item["files"].values():
                path = file_evidence["path"]
                assert path in names
                assert hashlib.sha256(archive.read(path)).hexdigest() == (
                    file_evidence["sha256"]
                )
        assert all(
            info.date_time == (1980, 1, 1, 0, 0, 0)
            for info in archive.infolist()
        )
        assert "/Users/" not in manifest_bytes.decode("utf-8")
    duplicate_manifest = {
        "schema_version": manifest["schema_version"],
        "run_id": "duplicate-feedback-001",
        "proposal_id": manifest["proposal_id"],
        "created_at_utc": "2026-07-24T00:00:00+00:00",
        "source_sha256": manifest["source_sha256"],
        "items": [manifest["items"][0]],
    }
    duplicate_dir = feedback_path.parent.parent / "duplicate-feedback-001"
    duplicate_dir.mkdir()
    (duplicate_dir / feedback_name).write_bytes(
        _deterministic_zip_bytes(
            {
                "manifest.json": (
                    json.dumps(duplicate_manifest, sort_keys=True) + "\n"
                ).encode()
            }
        )
    )
    corrupt_dir = feedback_path.parent.parent / "corrupt-feedback-001"
    corrupt_dir.mkdir()
    (corrupt_dir / feedback_name).write_bytes(b"not-a-zip")
    catalog = service.feedback_catalog(limit=100)
    assert catalog["available_package_count"] == 2
    assert catalog["returned_package_count"] == 2
    assert catalog["item_count"] == 3
    assert catalog["unique_source_count"] == 1
    assert catalog["invalid_package_count"] == 1
    assert catalog["quality_counts"]["pass"] == 2
    assert catalog["quality_counts"]["deferred"] == 1
    assert catalog["duplicate_fingerprint_group_count"] >= 1
    assert catalog["duplicate_fingerprint_item_count"] >= 2
    curation_result = service.create_feedback_curation(
        seed=42,
        minimum_unique_sources=1,
    )
    curation = curation_result["curation"]
    assert curation["curation_id"] == "feedback-curation-ranked-001"
    assert curation["status"] == "not_training_ready"
    assert curation["training_authorized"] is False
    assert curation["selection"]["candidate_count_before_deduplication"] == 2
    assert curation["selection"]["selected_item_count"] == 1
    assert curation["selection"]["unique_source_count"] == 1
    assert curation["selection"]["exclusion_counts"] == {
        "quality_warning": 0,
        "deferred": 1,
        "quality_unknown": 0,
        "invalid_candidate": 0,
        "duplicate_fingerprint": 1,
    }
    assert curation["splits"]["train"]["item_count"] == 1
    assert curation["splits"]["val"]["item_count"] == 0
    assert curation["splits"]["test"]["item_count"] == 0
    assert curation["leakage_audit"]["passed"] is True
    assert curation["leakage_audit"]["source_overlaps"] == {
        "train_val": [],
        "train_test": [],
        "val_test": [],
    }
    assert set(curation["readiness"]["blockers"]) >= {
        "empty_val_split",
        "empty_test_split",
        "privacy_review_pending",
        "label_qa_pending",
        "invalid_feedback_packages_present",
    }
    curation_path = service.feedback_curation_path(
        "feedback-curation-ranked-001"
    )
    assert curation_path.is_file()
    assert curation_result["curation_url"].endswith(
        "/feedback-curation-ranked-001.json"
    )
    assert "/Users/" not in curation_path.read_text(encoding="utf-8")
    assert feedback_path.is_file()
    assert (duplicate_dir / feedback_name).is_file()


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
