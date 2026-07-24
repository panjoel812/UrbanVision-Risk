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
    _autopilot_batch_accounting,
    _autopilot_batch_arbitration_ids,
    _autopilot_batch_run_ids,
    _autopilot_batch_source_digests,
    _bounded_feedback_layers,
    _canonical_merkle_root,
    _cross_channel_evidence_state,
    _curation_ratios,
    _curation_readiness_remediation,
    _deterministic_zip_bytes,
    _difference_hash64,
    _drift_feature_vector,
    _drift_two_sample_statistics,
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


def test_autopilot_batch_run_ids_are_bounded_unique_and_path_safe() -> None:
    assert _autopilot_batch_run_ids('["run-001", "run-002"]') == [
        "run-001",
        "run-002",
    ]

    invalid_values = (
        "not-json",
        "{}",
        "[]",
        json.dumps([f"run-{index:03d}" for index in range(101)]),
        '["run-001", "run-001"]',
        '["../private"]',
        '["run-001", 2]',
    )
    for value in invalid_values:
        with pytest.raises(ProjectError):
            _autopilot_batch_run_ids(value)

    digests = ["1" * 64, "2" * 64]
    assert _autopilot_batch_source_digests(
        json.dumps(digests),
        run_count=2,
    ) == digests
    with pytest.raises(ProjectError):
        _autopilot_batch_source_digests(
            json.dumps([digests[0], digests[0]]),
            run_count=2,
        )
    with pytest.raises(ProjectError):
        _autopilot_batch_source_digests(
            json.dumps([digests[0]]),
            run_count=2,
        )
    assert _autopilot_batch_arbitration_ids(
        '["arbitration-001", "arbitration-002"]',
        run_count=2,
    ) == ["arbitration-001", "arbitration-002"]
    with pytest.raises(ProjectError):
        _autopilot_batch_arbitration_ids(
            '["arbitration-001", "arbitration-001"]',
            run_count=2,
        )

    assert _autopilot_batch_accounting(
        run_count=2,
        selected_count=5,
        failed_count=2,
        duplicate_count=1,
        retry_count=2,
        max_attempts=2,
    )["accounting_validated"] is True
    with pytest.raises(ProjectError):
        _autopilot_batch_accounting(
            run_count=2,
            selected_count=4,
            failed_count=2,
            duplicate_count=1,
            retry_count=0,
            max_attempts=2,
        )


@pytest.mark.parametrize(
    ("proposal", "semantic", "support", "expected"),
    [
        (True, False, 0.0, "proposal_only_semantic_miss"),
        (False, True, 0.0, "detector_only_semantic_evidence"),
        (True, True, 0.10, "cross_channel_supported"),
        (True, True, 0.099, "spatial_disagreement"),
        (False, False, 0.0, "inconclusive_no_positive_evidence"),
    ],
)
def test_cross_channel_evidence_state_is_policy_bounded(
    proposal: bool,
    semantic: bool,
    support: float,
    expected: str,
) -> None:
    assert _cross_channel_evidence_state(
        proposal_significant=proposal,
        semantic_positive=semantic,
        proposal_supported_ratio=support,
    ) == expected


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


def test_drift_features_and_permutation_test_are_bounded_and_deterministic() -> None:
    source = np.full((80, 120, 3), 180, dtype=np.uint8)
    source[:, 55:65] = 20
    mask = np.zeros((80, 120), dtype=np.uint8)
    mask[:, 58:62] = 255

    features = _drift_feature_vector(source, mask)

    assert features.shape == (9,)
    assert np.all(features >= 0)
    assert np.all(features <= 1)
    generator = np.random.default_rng(17)
    reference = np.clip(
        generator.normal(0.15, 0.015, size=(10, 9)),
        0,
        1,
    )
    current = np.clip(
        generator.normal(0.85, 0.015, size=(6, 9)),
        0,
        1,
    )
    first = _drift_two_sample_statistics(
        current,
        reference,
        permutations=199,
        seed=91,
    )
    second = _drift_two_sample_statistics(
        current,
        reference,
        permutations=199,
        seed=91,
    )

    assert first == second
    assert first["p_value"] <= 0.05
    assert first["mmd_squared"] > 0
    assert first["coverage"]["novel_source_ratio"] == 1.0
    assert len(first["feature_attribution"]) == 9


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


def test_feedback_curation_repairs_empty_splits_and_reports_exact_deficits() -> None:
    ratios = _curation_ratios(0.8, 0.1, 0.1)
    groups = {
        "scene-large": [{"source_sha256": "1" * 64}] * 40,
        "scene-medium": [{"source_sha256": "2" * 64}] * 20,
        "scene-small": [{"source_sha256": "3" * 64}] * 7,
    }

    assigned = _assign_curation_groups(groups, ratios, seed=42)

    assert {
        split: len(items) for split, items in assigned.items()
    } == {"train": 40, "val": 20, "test": 7}
    remediation = _curation_readiness_remediation(
        source_count=3,
        scene_group_count=3,
        minimum_unique_sources=10,
        machine_candidate_count=67,
        human_reviewed_count=0,
        ratios=ratios,
        split_item_counts={
            split: len(items) for split, items in assigned.items()
        },
        privacy_review_confirmed=True,
        label_qa_confirmed=True,
        scope_kind="explicit_autopilot_batch",
    )
    assert remediation["deficits"] == {
        "additional_unique_sources_required": 7,
        "additional_visual_scene_groups_required": 7,
        "empty_positive_splits": [],
        "machine_candidates_pending_independent_approval": 67,
    }
    assert remediation["recommended_next_batch"][
        "additional_distinct_images_for_current_registry"
    ] == 7
    assert remediation["recommended_next_batch"][
        "minimum_distinct_images_for_new_scoped_batch"
    ] == 10
    assert remediation["external_benchmark_reference"][
        "data_license"
    ] == "CC-BY-SA-4.0"
    two_way = _assign_curation_groups(
        groups,
        {"train": 0.8, "val": 0.2, "test": 0.0},
        seed=42,
    )
    assert two_way["train"]
    assert two_way["val"]
    assert two_way["test"] == []


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


def test_canonical_merkle_root_is_order_independent_and_content_sensitive() -> None:
    records = [
        {"split": "train", "source_roi_sha256": "a" * 64},
        {"split": "test", "source_roi_sha256": "b" * 64},
        {"split": "val", "source_roi_sha256": "c" * 64},
    ]

    first = _canonical_merkle_root(records)
    reordered = _canonical_merkle_root(list(reversed(records)))
    changed = _canonical_merkle_root(
        [
            *records[:-1],
            {"split": "val", "source_roi_sha256": "d" * 64},
        ]
    )

    assert len(first) == 64
    assert first == reordered
    assert first != changed
    assert _canonical_merkle_root([]) == _canonical_merkle_root([])


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
    archive_entries_by_run: dict[str, dict[str, bytes]] = {}
    for index in range(10):
        run_id = f"feedback-source-{index:03d}"
        run_dir = paths.metrology / run_id
        run_dir.mkdir(parents=True)
        item_root = f"items/01-hotspot-{index:03d}"
        scene_fingerprint = scene_fingerprints[index]
        source_roi = np.full(
            (48, 36, 3),
            80 + index,
            dtype=np.uint8,
        )
        final_mask = np.zeros((48, 36), dtype=np.uint8)
        final_mask[8:24, 10:22] = 255
        role_contents = {
            "source_roi": _encode_image(source_roi),
            "proposal_mask": _encode_image(final_mask),
            "final_mask": _encode_image(final_mask),
            "disagreement_layer": _encode_image(
                np.zeros_like(final_mask)
            ),
        }
        files = {
            role: {
                "path": f"{item_root}/{role}.png",
                "sha256": hashlib.sha256(content).hexdigest(),
            }
            for role, content in role_contents.items()
        }
        manifest = {
            "schema_version": "urbanvision-active-learning-feedback-v1.2.0",
            "run_id": run_id,
            "proposal_id": f"proposal-{index:03d}",
            "review_authority": "human_operator",
            "created_at_utc": f"2026-07-24T00:00:{index:02d}+00:00",
            "source_sha256": f"{index + 1:064x}",
            "items": [
                {
                    "hotspot_id": f"hotspot-{index:03d}",
                    "rank": 1,
                    "disposition": "accepted_as_proposed",
                    "decision_authority": "human_operator",
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
                    "files": files,
                }
            ],
        }
        entries = {
            evidence["path"]: role_contents[role]
            for role, evidence in files.items()
        }
        entries["manifest.json"] = (
            json.dumps(manifest, sort_keys=True) + "\n"
        ).encode()
        archive_entries_by_run[run_id] = entries
        (run_dir / feedback_name).write_bytes(
            _deterministic_zip_bytes(entries)
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
    assert curation["schema_version"] == (
        "urbanvision-feedback-curation-v2.3.0"
    )
    assert curation["training_authorized"] is False
    assert curation["readiness"]["blockers"] == []
    assert curation["readiness"]["technical"] == {
        "status": "ready",
        "blockers": [],
    }
    assert curation["readiness"]["governance"] == {
        "status": "ready",
        "blockers": [],
    }
    assert curation["allocation"][
        "non_empty_positive_split_seeding_applied"
    ] is True
    assert curation["readiness"]["remediation"]["deficits"][
        "empty_positive_splits"
    ] == []
    assert curation["selection"]["selected_item_count"] == 10
    assert curation["selection"]["visual_scene_group_count"] == 9
    assert curation["selection"]["machine_only_selected_count"] == 0
    assert curation["selection"]["review_authority_counts"][
        "human_operator"
    ] == 10
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
    snapshot_result = service.create_feedback_snapshot_preflight(
        "feedback-curation-governed-001"
    )
    snapshot = snapshot_result["snapshot"]
    assert snapshot["status"] == (
        "verified_candidate_snapshot_requires_training_approval"
    )
    assert snapshot["schema_version"] == (
        "urbanvision-feedback-snapshot-preflight-v1.2.0"
    )
    assert snapshot["training_authorized"] is False
    assert snapshot["readiness"]["blockers"] == []
    assert snapshot["readiness"]["technical"]["status"] == "ready"
    assert snapshot["readiness"]["governance"]["status"] == "ready"
    assert snapshot["readiness"]["remediation"] == (
        curation["readiness"]["remediation"]
    )
    assert snapshot["integrity"]["inventory_matches"] is True
    assert snapshot["integrity"]["expected_pair_count"] == 10
    assert snapshot["integrity"]["verified_pair_count"] == 10
    assert snapshot["integrity"]["invalid_pair_count"] == 0
    assert snapshot["integrity"]["review_authority_counts"][
        "human_operator"
    ] == 10
    assert snapshot["merkle"]["leaf_count"] == 10
    assert len(snapshot["merkle"]["root_sha256"]) == 64
    assert {
        split: snapshot["splits"][split]["pair_count"]
        for split in ("train", "val", "test")
    } == {"train": 8, "val": 1, "test": 1}
    snapshot_path = service.feedback_snapshot_path(
        "feedback-snapshot-governed-001"
    )
    assert snapshot_path.is_file()
    assert "/Users/" not in snapshot_path.read_text(encoding="utf-8")

    current_drift_curation_result = service.create_feedback_curation(
        seed=42,
        minimum_unique_sources=3,
        included_run_ids=[
            "feedback-source-000",
            "feedback-source-001",
            "feedback-source-002",
        ],
        _record_prefix="drift-current-curation",
    )
    drift_result = service.create_feedback_drift_audit(
        current_curation_id=current_drift_curation_result["curation"][
            "curation_id"
        ],
        cumulative_curation_id=curation["curation_id"],
        _record_prefix="feedback-drift",
    )
    drift_audit = drift_result["drift_audit"]
    assert drift_audit["status"] in {
        "no_statistically_detectable_shift",
        "distribution_shift_or_coverage_warning",
    }
    assert drift_audit["readiness"]["blockers"] == []
    assert drift_audit["samples"]["current"]["source_count"] == 3
    assert drift_audit["samples"]["historical_reference"][
        "source_count"
    ] == 7
    assert drift_audit["statistics"] is not None
    assert 0 < drift_audit["statistics"]["p_value"] <= 1
    assert drift_audit["statistics"]["permutation_count"] == 199
    assert drift_audit["training_authorized"] is False
    drift_path = service.feedback_drift_audit_path(
        "feedback-drift-governed-001"
    )
    assert drift_path.is_file()
    assert "/Users/" not in drift_path.read_text(encoding="utf-8")

    tampered_run_id = "feedback-source-000"
    tampered_entries = dict(archive_entries_by_run[tampered_run_id])
    tampered_source_path = (
        "items/01-hotspot-000/source_roi.png"
    )
    tampered_entries[tampered_source_path] = _encode_image(
        np.full((48, 36, 3), 250, dtype=np.uint8)
    )
    (
        paths.metrology / tampered_run_id / feedback_name
    ).write_bytes(_deterministic_zip_bytes(tampered_entries))
    tampered_service = LocalMetrologyService(
        paths=paths,
        record_id_factory=lambda prefix: f"{prefix}-tampered-001",
    )
    tampered_result = (
        tampered_service.create_feedback_snapshot_preflight(
            "feedback-curation-governed-001"
        )
    )
    tampered_snapshot = tampered_result["snapshot"]
    assert tampered_snapshot["status"] == "not_snapshot_ready"
    assert set(tampered_snapshot["readiness"]["blockers"]) >= {
        "invalid_training_pairs",
        "incomplete_snapshot_pairs",
    }
    assert tampered_snapshot["integrity"]["verified_pair_count"] == 9
    assert "source_roi_digest_mismatch" in {
        finding["code"]
        for finding in tampered_snapshot["integrity"]["findings"]
    }


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
            "urbanvision-active-learning-feedback-v1.2.0"
        )
        assert manifest["review_authority"] == "human_operator"
        assert manifest["decision_policy"] == "operator_recorded"
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
        "review_authority": manifest["review_authority"],
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
    assert catalog["review_authority_counts"]["human_operator"] == 3
    assert catalog["duplicate_fingerprint_group_count"] >= 1
    assert catalog["duplicate_fingerprint_item_count"] >= 2
    curation_result = service.create_feedback_curation(
        seed=42,
        minimum_unique_sources=1,
    )
    curation = curation_result["curation"]
    assert curation["curation_id"] == "feedback-curation-ranked-001"
    assert curation["status"] == "technical_data_not_ready"
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
    assert curation["readiness"]["technical"]["status"] == "blocked"
    assert set(curation["readiness"]["technical"]["blockers"]) >= {
        "empty_val_split",
        "empty_test_split",
        "invalid_feedback_packages_present",
    }
    assert curation["readiness"]["governance"]["status"] == "blocked"
    assert set(curation["readiness"]["governance"]["blockers"]) == {
        "privacy_review_pending",
        "label_qa_pending",
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


def test_machine_reviewed_candidate_is_audited_and_training_blocked(
    tmp_path: Path,
) -> None:
    source = _textured_crack_source()
    service = LocalMetrologyService(
        paths=get_paths(tmp_path),
        id_factory=lambda: "machine-candidate-001",
        record_id_factory=lambda prefix: f"{prefix}-machine-001",
    )
    proposal = service.propose_mask_bytes(
        source_content=source,
        source_filename="machine-road.png",
        source_content_type="image/png",
        sensitivity=0.55,
    )
    proposal_id = proposal["proposal_id"]
    hotspots = proposal["evidence"]["review_guidance"]["ranking"][
        "ranked_hotspots"
    ]
    hotspot_ids = [hotspot["hotspot_id"] for hotspot in hotspots]
    decisions = [
        {
            "hotspot_id": hotspot["hotspot_id"],
            "disposition": (
                "accepted_as_proposed"
                if hotspot["candidate_overlap_ratio"] >= 0.10
                else "deferred_for_follow_up"
            ),
        }
        for hotspot in hotspots
    ]
    mask_path = service.proposal_artifact_path(
        proposal_id,
        "proposal-mask.png",
    )

    result = service.analyze_bytes(
        source_content=source,
        source_filename="machine-road.png",
        source_content_type="image/png",
        mask_content=mask_path.read_bytes(),
        mask_filename="proposal-mask.png",
        mask_content_type="image/png",
        calibration_mode="pixel",
        uncertainty_samples=0,
        proposal_id=proposal_id,
        review_state="machine_reviewed_candidate",
        reviewed_hotspots=json.dumps(hotspot_ids),
        hotspot_decisions=json.dumps(decisions),
    )

    input_evidence = result["measurement"]["run"]["input_evidence"]
    assert input_evidence["review_state"] == "machine_reviewed_candidate"
    assert input_evidence["review_authority"] == "machine_heuristic"
    assert len(
        input_evidence["mask"]["normalized_binary_sha256"]
    ) == 64
    assert input_evidence["mask"]["origin"] == (
        "local_proposal_machine_reviewed_candidate"
    )
    assert input_evidence["mask"]["proposal_revision"]["hotspot_review"][
        "review_authority"
    ] == "machine_heuristic"
    assert input_evidence["mask"]["proposal_revision"]["hotspot_review"][
        "decision_policy"
    ] == "candidate_overlap_ratio>=0.10_accept_else_defer"
    feedback_path = service.artifact_path(
        result["run_id"],
        "active-learning-feedback.zip",
    )
    with zipfile.ZipFile(feedback_path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
    assert manifest["review_authority"] == "machine_heuristic"
    assert manifest["decision_policy"] == (
        "candidate_overlap_ratio>=0.10_accept_else_defer"
    )
    assert {
        item["decision_authority"] for item in manifest["items"]
    } == {"machine_heuristic"}
    assert {
        item["disposition"] for item in manifest["items"]
    } >= {
        "accepted_as_proposed",
        "deferred_for_follow_up",
    }

    decoded_source = cv2.imdecode(
        np.frombuffer(source, dtype=np.uint8),
        cv2.IMREAD_COLOR,
    )
    assert decoded_source is not None
    height, width = decoded_source.shape[:2]
    prediction = {
        "image_dimensions": {"width": width, "height": height},
        "detections": [],
    }
    risk = {
        "decision_status": "review_required",
        "review_required": True,
        "risk_score": 0.0,
    }
    prediction_bytes = (
        json.dumps(prediction, sort_keys=True) + "\n"
    ).encode()
    risk_bytes = (json.dumps(risk, sort_keys=True) + "\n").encode()
    inspection_run_name = "china-repair-mps-003"
    inspection_id = "inspection-machine-001"
    inspection_dir = (
        service.paths.inspections / inspection_run_name / inspection_id
    )
    inspection_dir.mkdir(parents=True)
    (inspection_dir / "prediction.json").write_bytes(prediction_bytes)
    (inspection_dir / "risk.json").write_bytes(risk_bytes)
    (inspection_dir / "inspection-manifest.json").write_text(
        json.dumps(
            {
                "inspection_id": inspection_id,
                "run_name": inspection_run_name,
                "source_upload_sha256": input_evidence["source"]["sha256"],
                "prediction_json_sha256": hashlib.sha256(
                    prediction_bytes
                ).hexdigest(),
                "risk_json_sha256": hashlib.sha256(
                    risk_bytes
                ).hexdigest(),
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    arbitration_result = service.create_evidence_arbitration(
        inspection_run_name=inspection_run_name,
        inspection_id=inspection_id,
        metrology_run_id=result["run_id"],
    )
    arbitration = arbitration_result["arbitration"]
    assert arbitration["schema_version"] == (
        "urbanvision-cross-channel-arbitration-v1.0.0"
    )
    assert arbitration["decision"]["evidence_state"] == (
        "proposal_only_semantic_miss"
    )
    assert arbitration["decision"]["review_required"] is True
    assert arbitration["decision"]["risk_score_display"] == (
        "withheld_pending_review"
    )
    assert arbitration["source_binding"] == {
        "source_sha256": input_evidence["source"]["sha256"],
        "inspection_metrology_match": True,
    }
    arbitration_id = arbitration["arbitration_id"]
    arbitration_path = service.evidence_arbitration_path(arbitration_id)
    assert "/Users/" not in arbitration_path.read_text(encoding="utf-8")

    with pytest.raises(ProjectError, match="inspect every ranked hotspot"):
        service.analyze_bytes(
            source_content=source,
            source_filename="machine-road.png",
            source_content_type="image/png",
            mask_content=mask_path.read_bytes(),
            mask_filename="proposal-mask.png",
            mask_content_type="image/png",
            calibration_mode="pixel",
            uncertainty_samples=0,
            proposal_id=proposal_id,
            review_state="machine_reviewed_candidate",
            reviewed_hotspots=json.dumps(hotspot_ids[:-1]),
            hotspot_decisions=json.dumps(decisions[:-1]),
        )

    with pytest.raises(ProjectError, match="decision differs"):
        invalid_decisions = [dict(decision) for decision in decisions]
        invalid_decisions[0]["disposition"] = (
            "accepted_as_proposed"
            if decisions[0]["disposition"] == "deferred_for_follow_up"
            else "deferred_for_follow_up"
        )
        service.analyze_bytes(
            source_content=source,
            source_filename="machine-road.png",
            source_content_type="image/png",
            mask_content=mask_path.read_bytes(),
            mask_filename="proposal-mask.png",
            mask_content_type="image/png",
            calibration_mode="pixel",
            uncertainty_samples=0,
            proposal_id=proposal_id,
            review_state="machine_reviewed_candidate",
            reviewed_hotspots=json.dumps(hotspot_ids),
            hotspot_decisions=json.dumps(invalid_decisions),
        )

    source_sha256 = input_evidence["source"]["sha256"]
    with pytest.raises(ProjectError, match="browser source digest"):
        service.finalize_autopilot_batch(
            run_ids=json.dumps([result["run_id"]]),
            source_digests=json.dumps(["0" * 64]),
            minimum_unique_sources=1,
        )

    duplicate_run_id = "machine-candidate-copy-001"
    duplicate_dir = service.paths.metrology / duplicate_run_id
    duplicate_dir.mkdir()
    duplicate_measurement = json.loads(
        (service.paths.metrology / result["run_id"] / "measurement.json").read_text(
            encoding="utf-8"
        )
    )
    duplicate_measurement["run"]["output_name"] = duplicate_run_id
    (duplicate_dir / "measurement.json").write_text(
        json.dumps(duplicate_measurement, sort_keys=True),
        encoding="utf-8",
    )
    with pytest.raises(ProjectError, match="duplicate source evidence"):
        service.finalize_autopilot_batch(
            run_ids=json.dumps([result["run_id"], duplicate_run_id]),
            minimum_unique_sources=1,
        )

    governance_only_result = service.create_feedback_curation(
        train_ratio=1.0,
        val_ratio=0.0,
        test_ratio=0.0,
        minimum_unique_sources=1,
        included_run_ids=[result["run_id"]],
        _record_prefix="governance-only-curation",
    )
    governance_only = governance_only_result["curation"]
    assert governance_only["status"] == (
        "technical_data_ready_governance_blocked"
    )
    assert governance_only["readiness"]["technical"]["status"] == "ready"
    assert governance_only["readiness"]["governance"]["status"] == "blocked"
    governance_snapshot_result = (
        service.create_feedback_snapshot_preflight(
            governance_only["curation_id"],
            _record_prefix="governance-only-snapshot",
        )
    )
    governance_snapshot = governance_snapshot_result["snapshot"]
    assert governance_snapshot["status"] == (
        "integrity_verified_governance_blocked"
    )
    assert governance_snapshot["readiness"]["technical"]["status"] == "ready"
    assert governance_snapshot["readiness"]["governance"]["status"] == (
        "blocked"
    )

    with zipfile.ZipFile(feedback_path) as archive:
        historical_entries = {
            name: archive.read(name) for name in archive.namelist()
        }
    historical_manifest = json.loads(
        json.dumps(manifest, sort_keys=True)
    )
    historical_manifest["run_id"] = "historical-feedback-001"
    historical_manifest["source_sha256"] = "f" * 64
    for item in historical_manifest["items"]:
        fingerprint = int(
            item["source_roi_difference_hash64"],
            16,
        )
        item["source_roi_difference_hash64"] = (
            f"{fingerprint ^ 0x00FF00FF00FF00FF:016x}"
        )
        source_roi_evidence = item["files"]["source_roi"]
        original_source_roi = cv2.imdecode(
            np.frombuffer(
                historical_entries[source_roi_evidence["path"]],
                dtype=np.uint8,
            ),
            cv2.IMREAD_COLOR,
        )
        assert original_source_roi is not None
        historical_source_roi = _encode_image(
            np.full_like(original_source_roi, 173)
        )
        historical_entries[source_roi_evidence["path"]] = (
            historical_source_roi
        )
        source_roi_evidence["sha256"] = hashlib.sha256(
            historical_source_roi
        ).hexdigest()
    historical_entries["manifest.json"] = (
        json.dumps(historical_manifest, sort_keys=True) + "\n"
    ).encode()
    historical_dir = (
        service.paths.metrology / "historical-feedback-001"
    )
    historical_dir.mkdir()
    (historical_dir / "active-learning-feedback.zip").write_bytes(
        _deterministic_zip_bytes(historical_entries)
    )

    batch_result = service.finalize_autopilot_batch(
        run_ids=json.dumps([result["run_id"]]),
        source_digests=json.dumps([source_sha256]),
        arbitration_ids=json.dumps([arbitration_id]),
        selected_count=3,
        failed_count=1,
        duplicate_count=1,
        retry_count=1,
        max_attempts=2,
        minimum_unique_sources=1,
    )
    curation = batch_result["curation"]
    assert curation["selection"]["machine_only_selected_count"] >= 1
    assert curation["selection"]["review_authority_counts"][
        "machine_heuristic"
    ] == curation["selection"]["machine_only_selected_count"]
    assert "machine_labels_require_human_approval" in (
        curation["readiness"]["blockers"]
    )
    assert curation["training_authorized"] is False
    assert curation["configuration"]["scope"] == {
        "kind": "explicit_autopilot_batch",
        "run_ids": [result["run_id"]],
    }
    batch = batch_result["batch"]
    assert batch["schema_version"] == "urbanvision-autopilot-batch-v1.4.0"
    assert batch["status"] == "completed_with_technical_constraints"
    assert batch["run_count"] == 1
    assert batch["feedback_run_count"] == 1
    assert batch["training_authorized"] is False
    assert batch["input_accounting"] == {
        "selected_count": 3,
        "completed_count": 1,
        "failed_count": 1,
        "duplicate_skipped_count": 1,
        "retry_count": 1,
        "max_attempts": 2,
        "accounting_validated": True,
        "failure_counts_source": "local_browser_queue",
    }
    assert batch["source_integrity"] == {
        "unique_source_count": 1,
        "browser_digest_match_count": 1,
        "server_duplicate_source_rejection": True,
    }
    assert batch["cross_channel_arbitration"] == {
        "bound_count": 1,
        "all_completed_runs_bound": True,
    }
    assert batch["runs"][0]["arbitration"]["arbitration_id"] == (
        arbitration_id
    )
    assert batch["runs"][0]["arbitration"]["evidence_state"] == (
        "proposal_only_semantic_miss"
    )
    assert batch["runs"][0]["run_id"] == result["run_id"]
    assert batch["runs"][0]["feedback_exported"] is True
    assert batch["governance"]["curation_id"] == (
        "feedback-curation-machine-001"
    )
    assert batch["governance"]["snapshot_id"] == (
        "feedback-snapshot-machine-001"
    )
    assert batch["governance"]["technical"]["status"] == "blocked"
    assert batch["governance"]["governance"]["status"] == "blocked"
    assert batch["cumulative_registry"]["automatically_refreshed"] is True
    assert batch["cumulative_registry"]["scope"] == (
        "all_local_feedback_across_sessions"
    )
    assert batch["cumulative_registry"]["curation_id"] == (
        "cumulative-curation-machine-001"
    )
    assert batch["cumulative_registry"]["snapshot_id"] == (
        "cumulative-snapshot-machine-001"
    )
    assert batch["cumulative_registry"]["unique_source_count"] == 2
    assert batch["cumulative_registry"]["unique_source_count"] > (
        batch["source_integrity"]["unique_source_count"]
    )
    assert batch_result["cumulative_curation"]["configuration"]["scope"] == {
        "kind": "all_local_feedback"
    }
    assert batch_result["cumulative_curation"]["readiness"]["technical"][
        "status"
    ] == "blocked"
    assert batch_result["cumulative_curation"]["readiness"]["governance"][
        "status"
    ] == "blocked"
    assert batch_result["cumulative_snapshot"]["curation_binding"][
        "curation_id"
    ] == "cumulative-curation-machine-001"
    drift_audit = batch_result["drift_audit"]
    assert drift_audit["schema_version"] == (
        "urbanvision-feedback-drift-audit-v1.0.0"
    )
    assert drift_audit["status"] == "insufficient_or_invalid_evidence"
    assert set(drift_audit["readiness"]["blockers"]) >= {
        "insufficient_current_sources_for_drift",
        "insufficient_reference_sources_for_drift",
    }
    assert drift_audit["statistics"] is None
    assert drift_audit["training_authorized"] is False
    assert batch["distribution_monitoring"]["drift_id"] == (
        "feedback-drift-machine-001"
    )
    assert batch["distribution_monitoring"]["monitoring_only"] is True
    drift_path = service.feedback_drift_audit_path(
        "feedback-drift-machine-001"
    )
    assert drift_path.is_file()
    assert "/Users/" not in drift_path.read_text(encoding="utf-8")
    batch_path = service.autopilot_batch_path(
        "autopilot-batch-machine-001"
    )
    assert batch_path.is_file()
    assert "/Users/" not in batch_path.read_text(encoding="utf-8")

    saved_mask_path = (
        service.paths.metrology / result["run_id"] / "mask.png"
    )
    saved_mask = cv2.imread(str(saved_mask_path), cv2.IMREAD_GRAYSCALE)
    assert saved_mask is not None
    shifted_mask = np.roll(saved_mask, 1, axis=1)
    encoded, shifted_mask_bytes = cv2.imencode(".png", shifted_mask)
    assert encoded
    saved_mask_path.write_bytes(shifted_mask_bytes.tobytes())
    with pytest.raises(ProjectError, match="mask evidence does not match"):
        service.create_evidence_arbitration(
            inspection_run_name=inspection_run_name,
            inspection_id=inspection_id,
            metrology_run_id=result["run_id"],
        )
    with pytest.raises(ProjectError, match="mask digest does not match"):
        service.finalize_autopilot_batch(
            run_ids=json.dumps([result["run_id"]]),
            source_digests=json.dumps([source_sha256]),
            arbitration_ids=json.dumps([arbitration_id]),
            minimum_unique_sources=1,
        )


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
