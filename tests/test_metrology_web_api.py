import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from urbanvision_risk.app.api import create_app
from urbanvision_risk.errors import ProjectError


class InspectionStub:
    def __init__(self, annotated: Path) -> None:
        self.annotated = annotated
        self.run_name = "china-repair-mps-003"

    def health_payload(self) -> dict[str, object]:
        return {"local_only": True, "device": "mps"}

    def inspect_bytes(
        self, content: bytes, *, filename: str | None, content_type: str
    ) -> dict[str, object]:
        return {"inspection_id": "inspection-web-001"}

    def annotated_path(self, inspection_id: str) -> Path:
        return self.annotated

    def narrative(self, inspection_id: str) -> dict[str, object]:
        return {"inspection_id": inspection_id}

    def review_queue(self, *, limit: int = 50) -> dict[str, object]:
        return {"local_only": True, "items": []}


class MetrologyStub:
    def __init__(self, artifact: Path) -> None:
        self.artifact = artifact
        self.feedback = artifact.with_name("active-learning-feedback.zip")
        self.feedback.write_bytes(b"active-learning-feedback")
        self.analyze_arguments: dict[str, Any] | None = None
        self.plan_arguments: dict[str, Any] | None = None
        self.compare_arguments: dict[str, Any] | None = None
        self.proposal_arguments: dict[str, Any] | None = None
        self.failure: ProjectError | None = None
        self.feedback_catalog_limit: int | None = None
        self.feedback_curation_arguments: dict[str, Any] | None = None
        self.feedback_snapshot_curation_id: str | None = None
        self.autopilot_batch_arguments: dict[str, Any] | None = None
        self.arbitration_arguments: dict[str, Any] | None = None

    def demo(self) -> dict[str, object]:
        return {
            "run_id": "metrology-demo-web-001",
            "local_only": True,
            "measurement": {"measurement_space": "rectified_physical_plane"},
            "artifacts": {"overlay.jpg": "/api/metrology/runs/x/overlay.jpg"},
        }

    def analyze_bytes(self, **kwargs: Any) -> dict[str, object]:
        if self.failure:
            raise self.failure
        self.analyze_arguments = kwargs
        return {
            "run_id": "metrology-web-001",
            "local_only": True,
            "measurement": {"measurement_space": "pixel_only"},
            "artifacts": {"overlay.jpg": "/api/metrology/runs/x/overlay.jpg"},
        }

    def artifact_path(self, run_id: str, artifact_name: str) -> Path:
        if run_id != "metrology-web-001" or artifact_name not in {
            "overlay.jpg",
            "active-learning-feedback.zip",
        }:
            raise ProjectError("E201", "文件不存在", "Missing", "检查", "Check")
        if artifact_name == "active-learning-feedback.zip":
            return self.feedback
        return self.artifact

    def propose_mask_bytes(self, **kwargs: Any) -> dict[str, object]:
        self.proposal_arguments = kwargs
        return {
            "local_only": True,
            "proposal_id": "proposal-001",
            "candidate_found": True,
            "evidence": {
                "selection": {"coverage_ratio": 0.04},
                "review_guidance": {
                    "review_hotspot_image_ratio": 0.01,
                    "disagreement_ratio_of_union": 0.25,
                    "ranking": {
                        "ranked_hotspots": [
                            {
                                "hotspot_id": "hotspot-001",
                                "rank": 1,
                                "bounding_box": {
                                    "x": 10,
                                    "y": 20,
                                    "width": 30,
                                    "height": 40,
                                },
                                "disagreement_pixels": 42,
                                "candidate_overlap_ratio": 0.5,
                                "priority_score": 63.0,
                            }
                        ]
                    },
                },
            },
            "artifacts": {
                "proposal-mask.png": ("/api/metrology/proposals/proposal-001/proposal-mask.png"),
                "review-hotspots.png": (
                    "/api/metrology/proposals/proposal-001/review-hotspots.png"
                ),
                "evidence.json": ("/api/metrology/proposals/proposal-001/evidence.json"),
            },
        }

    def proposal_artifact_path(
        self,
        proposal_id: str,
        artifact_name: str,
    ) -> Path:
        if proposal_id != "proposal-001" or artifact_name not in {
            "proposal-mask.png",
            "review-hotspots.png",
            "evidence.json",
        }:
            raise ProjectError("E201", "不存在", "Missing", "检查", "Check")
        return self.artifact

    def list_runs(self, *, limit: int = 50) -> dict[str, object]:
        return {
            "local_only": True,
            "returned_count": 1,
            "items": [{"run_id": "metrology-baseline-001"}],
        }

    def feedback_catalog(self, *, limit: int = 50) -> dict[str, object]:
        self.feedback_catalog_limit = limit
        return {
            "local_only": True,
            "available_package_count": 1,
            "returned_package_count": 1,
            "item_count": 2,
            "unique_source_count": 1,
            "quality_counts": {
                "pass": 1,
                "warning": 0,
                "deferred": 1,
                "unknown": 0,
            },
            "duplicate_fingerprint_group_count": 0,
            "packages": [],
        }

    def create_feedback_curation(self, **kwargs: Any) -> dict[str, object]:
        self.feedback_curation_arguments = kwargs
        return {
            "local_only": True,
            "curation": {
                "curation_id": "feedback-curation-001",
                "status": "not_training_ready",
                "training_authorized": False,
            },
            "curation_url": (
                "/api/metrology/feedback-curations/feedback-curation-001.json"
            ),
        }

    def feedback_curation_path(self, curation_id: str) -> Path:
        if curation_id != "feedback-curation-001":
            raise ProjectError("E201", "不存在", "Missing", "检查", "Check")
        return self.artifact

    def create_feedback_snapshot_preflight(
        self,
        curation_id: str,
    ) -> dict[str, object]:
        self.feedback_snapshot_curation_id = curation_id
        return {
            "local_only": True,
            "snapshot": {
                "snapshot_id": "feedback-snapshot-001",
                "status": "not_snapshot_ready",
                "training_authorized": False,
            },
            "snapshot_url": (
                "/api/metrology/feedback-snapshots/"
                "feedback-snapshot-001.json"
            ),
        }

    def feedback_snapshot_path(self, snapshot_id: str) -> Path:
        if snapshot_id != "feedback-snapshot-001":
            raise ProjectError("E201", "不存在", "Missing", "检查", "Check")
        return self.artifact

    def finalize_autopilot_batch(self, **kwargs: Any) -> dict[str, object]:
        self.autopilot_batch_arguments = kwargs
        return {
            "local_only": True,
            "batch": {
                "batch_id": "autopilot-batch-001",
                "status": "completed_with_governance_blockers",
                "training_authorized": False,
            },
            "batch_url": (
                "/api/metrology/autopilot-batches/"
                "autopilot-batch-001.json"
            ),
            "curation": {
                "curation_id": "feedback-curation-001",
                "status": "not_training_ready",
                "training_authorized": False,
            },
            "curation_url": (
                "/api/metrology/feedback-curations/"
                "feedback-curation-001.json"
            ),
            "snapshot": {
                "snapshot_id": "feedback-snapshot-001",
                "status": "not_snapshot_ready",
                "training_authorized": False,
            },
            "snapshot_url": (
                "/api/metrology/feedback-snapshots/"
                "feedback-snapshot-001.json"
            ),
        }

    def autopilot_batch_path(self, batch_id: str) -> Path:
        if batch_id != "autopilot-batch-001":
            raise ProjectError("E201", "不存在", "Missing", "检查", "Check")
        return self.artifact

    def create_evidence_arbitration(
        self,
        **kwargs: Any,
    ) -> dict[str, object]:
        self.arbitration_arguments = kwargs
        return {
            "local_only": True,
            "arbitration": {
                "arbitration_id": "evidence-arbitration-001",
                "decision": {
                    "evidence_state": "proposal_only_semantic_miss",
                    "review_required": True,
                },
                "training_authorized": False,
            },
            "arbitration_url": (
                "/api/evidence/arbitrations/"
                "evidence-arbitration-001.json"
            ),
        }

    def evidence_arbitration_path(self, arbitration_id: str) -> Path:
        if arbitration_id != "evidence-arbitration-001":
            raise ProjectError("E201", "不存在", "Missing", "检查", "Check")
        return self.artifact

    def create_maintenance_plan(
        self,
        run_id: str,
        **kwargs: Any,
    ) -> dict[str, object]:
        self.plan_arguments = {"run_id": run_id, **kwargs}
        return {
            "local_only": True,
            "plan": {"plan_id": "maintenance-001"},
            "plan_url": (f"/api/metrology/runs/{run_id}/plans/maintenance-001.json"),
        }

    def plan_path(self, run_id: str, plan_id: str) -> Path:
        if run_id != "metrology-web-001" or plan_id != "maintenance-001":
            raise ProjectError("E201", "不存在", "Missing", "检查", "Check")
        return self.artifact

    def compare_runs(self, **kwargs: Any) -> dict[str, object]:
        self.compare_arguments = kwargs
        return {
            "local_only": True,
            "comparison": {"comparison_id": "comparison-001"},
            "comparison_url": "/api/metrology/comparisons/comparison-001.json",
            "artifacts": {
                "change-map.png": ("/api/metrology/comparisons/comparison-001/change-map.png")
            },
        }

    def comparison_path(self, comparison_id: str) -> Path:
        if comparison_id != "comparison-001":
            raise ProjectError("E201", "不存在", "Missing", "检查", "Check")
        return self.artifact

    def comparison_artifact_path(
        self,
        comparison_id: str,
        artifact_name: str,
    ) -> Path:
        if comparison_id != "comparison-001" or artifact_name != "change-map.png":
            raise ProjectError("E201", "不存在", "Missing", "检查", "Check")
        return self.artifact


def _client(tmp_path: Path) -> tuple[TestClient, MetrologyStub]:
    annotated = tmp_path / "annotated.jpg"
    annotated.write_bytes(b"inspection")
    artifact = tmp_path / "overlay.jpg"
    artifact.write_bytes(b"metrology-overlay")
    metrology = MetrologyStub(artifact)
    return (
        TestClient(create_app(InspectionStub(annotated), metrology)),  # type: ignore[arg-type]
        metrology,
    )


def test_precision_lab_page_contains_the_complete_local_workflow(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

    response = client.get("/metrology")

    assert response.status_code == 200
    assert "Unified Local Inspection" in response.text
    assert "上传一次" in response.text
    assert "One upload" in response.text
    assert "editor-canvas" in response.text
    assert "brush-tool" in response.text
    assert "eraser-tool" in response.text
    assert "manual_points" in response.text
    assert "Auto ArUco" in response.text
    assert "/api/metrology/demo" in response.text
    assert "/api/metrology/analyze" in response.text
    assert "destination-out" in response.text
    assert "hoverPoint" in response.text
    assert 'id="plan-button"' in response.text
    assert 'id="compare-button"' in response.text
    assert 'id="match-tolerance"' in response.text
    assert 'id="comparison-map"' in response.text
    assert 'id="proposal-button"' not in response.text
    assert 'id="proposal-sensitivity"' in response.text
    assert 'id="hotspot-toggle"' in response.text
    assert 'id="hotspot-review"' in response.text
    assert 'id="hotspot-previous"' in response.text
    assert 'id="hotspot-next"' in response.text
    assert 'id="hotspot-reviewed"' in response.text
    assert 'id="hotspot-loupe"' in response.text
    assert 'id="decision-accept"' in response.text
    assert 'id="decision-remove"' in response.text
    assert 'id="decision-add"' in response.text
    assert 'id="decision-defer"' in response.text
    assert 'id="hotspot-note"' in response.text
    assert 'id="feedback-panel"' in response.text
    assert 'id="feedback-download"' in response.text
    assert 'id="feedback-catalog-summary"' in response.text
    assert 'id="curation-button"' in response.text
    assert 'id="curation-privacy"' in response.text
    assert 'id="curation-label-qa"' in response.text
    assert 'id="curation-scene-distance"' in response.text
    assert 'id="curation-result"' in response.text
    assert 'id="snapshot-button"' in response.text
    assert 'id="snapshot-result"' in response.text
    assert "calculateLoupeViewport" in response.text
    assert "loupeCanvasPosition" in response.text
    assert "synchronized_hotspot_loupe" in response.text
    assert "recordHotspotDecision" in response.text
    assert "false_positive_removed" in response.text
    assert "missed_crack_added" in response.text
    assert "active-learning-feedback.zip" in response.text
    assert "/api/metrology/feedback-catalog?limit=100" in response.text
    assert "/api/metrology/feedback-curations" in response.text
    assert "loadFeedbackCatalog" in response.text
    assert "createFeedbackCuration" in response.text
    assert "createFeedbackSnapshot" in response.text
    assert "snapshot-preflight" in response.text
    assert "payload.snapshot_url" in response.text
    assert 'form.append("max_scene_hamming_distance"' in response.text
    assert 'hotspotLoupe.addEventListener("pointerdown"' in response.text
    assert 'id="inspection-section"' in response.text
    assert 'id="narrative-button"' in response.text
    assert "/api/inspect" in response.text
    assert "Promise.allSettled" in response.text
    assert "runAutomaticInspection" in response.text
    assert "generateProposalAndDraft" in response.text
    assert 'id="autopilot-toggle"' in response.text
    assert (
        'id="source-input" type="file" '
        'accept="image/jpeg,image/png,image/webp" multiple'
    ) in response.text
    assert 'id="batch-panel"' in response.text
    assert 'id="batch-list"' in response.text
    assert 'id="batch-result"' in response.text
    assert 'id="arbitration-panel"' in response.text
    assert 'id="evidence-arbitration"' in response.text
    assert "applyAutopilotDecisions" in response.text
    assert "AUTOPILOT_ACCEPT_OVERLAP = 0.10" in response.text
    assert "runGovernanceAutopilot" in response.text
    assert "runAutopilotBatch" in response.text
    assert "finalizeAutopilotBatch" in response.text
    assert "/api/metrology/autopilot-batches/finalize" in response.text
    assert "fileSha256" in response.text
    assert 'globalThis.crypto.subtle.digest(' in response.text
    assert "MAX_BATCH_ATTEMPTS = 2" in response.text
    assert 'setBatchItemState(index, "hashing")' in response.text
    assert 'setBatchItemState(index, "duplicate"' in response.text
    assert '"source_digests"' in response.text
    assert '"retry_count"' in response.text
    assert "runEvidenceArbitration" in response.text
    assert "renderEvidenceArbitration" in response.text
    assert "v5.6 · Self-remediating data readiness" in response.text
    assert "readinessRemediationLines" in response.text
    assert "全新独立批次至少选择" in response.text
    assert "/api/evidence/arbitrate" in response.text
    assert '"arbitration_ids"' in response.text
    assert "proposalSuppressed" in response.text
    assert '"machine_reviewed_candidate"' in response.text
    assert 'form.append("review_state", reviewState)' in response.text
    assert 'id="review-state"' in response.text
    assert "/api/metrology/compare" in response.text
    assert "/api/metrology/proposals" in response.text
    assert "review-hotspots.png" in response.text
    assert "sensitivityDisagreement" in response.text
    assert 'form.append("reviewed_hotspots"' in response.text
    assert 'form.append("hotspot_decisions"' in response.text
    assert "change-map.png" in response.text
    assert "https://" not in response.text
    assert "http://" not in response.text
    assert response.headers["x-frame-options"] == "DENY"
    assert "connect-src 'self'" in response.headers["content-security-policy"]


def test_home_is_the_unified_workflow_and_legacy_route_is_an_alias(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

    response = client.get("/")
    legacy = client.get("/metrology")

    assert response.status_code == 200
    assert response.text == legacy.text
    assert 'href="/metrology"' not in response.text
    assert "自动检测、风险与可靠性" in response.text
    assert "复核并修正自动掩膜" in response.text
    assert "材料与成本规划" in response.text
    assert "多期裂缝增长对比" in response.text


def test_demo_and_analyze_api_contracts(tmp_path: Path) -> None:
    client, metrology = _client(tmp_path)

    demo = client.post("/api/metrology/demo")
    analyzed = client.post(
        "/api/metrology/analyze",
        files={
            "image": ("road.png", b"source-bytes", "image/png"),
            "mask": ("mask.png", b"mask-bytes", "image/png"),
        },
        data={
            "calibration_mode": "manual",
            "manual_points": "[[1,1],[9,1],[9,9],[1,9]]",
            "physical_width": "1.2",
            "physical_height": "0.8",
            "unit": "m",
            "pixels_per_unit": "400",
            "point_sigma_pixels": "1.5",
            "uncertainty_samples": "32",
            "segmentation_radius_pixels": "2",
            "proposal_id": "proposal-001",
            "reviewed_hotspots": '["hotspot-001"]',
            "hotspot_decisions": (
                '[{"hotspot_id":"hotspot-001",'
                '"disposition":"accepted_as_proposed"}]'
            ),
        },
    )

    assert demo.status_code == 200
    assert demo.json()["measurement"]["measurement_space"] == ("rectified_physical_plane")
    assert analyzed.status_code == 200
    assert analyzed.json()["run_id"] == "metrology-web-001"
    assert metrology.analyze_arguments is not None
    assert metrology.analyze_arguments["source_content"] == b"source-bytes"
    assert metrology.analyze_arguments["mask_content"] == b"mask-bytes"
    assert metrology.analyze_arguments["calibration_mode"] == "manual"
    assert metrology.analyze_arguments["uncertainty_samples"] == 32
    assert metrology.analyze_arguments["proposal_id"] == "proposal-001"
    assert metrology.analyze_arguments["review_state"] == "human_reviewed"
    assert metrology.analyze_arguments["reviewed_hotspots"] == '["hotspot-001"]'
    assert metrology.analyze_arguments["hotspot_decisions"] == (
        '[{"hotspot_id":"hotspot-001","disposition":"accepted_as_proposed"}]'
    )

    health = client.get("/api/health")
    assert health.json()["precision_metrology"] is True
    assert health.json()["metrology_modes"] == ["pixel", "manual", "aruco"]
    assert health.json()["automatic_pixel_draft"] is True
    assert health.json()["ranked_hotspot_review"] is True
    assert health.json()["synchronized_review_loupe"] is True
    assert health.json()["auditable_hotspot_dispositions"] is True
    assert health.json()["active_learning_feedback_export"] is True
    assert health.json()["feedback_quality_registry"] is True
    assert health.json()["leakage_safe_feedback_curation"] is True
    assert health.json()["visual_near_duplicate_split_firewall"] is True
    assert health.json()["content_addressed_snapshot_preflight"] is True
    assert health.json()["policy_bounded_local_autopilot"] is True
    assert health.json()["resilient_batch_autopilot"] is True
    assert health.json()["self_healing_content_deduplication"] is True
    assert health.json()["cross_channel_evidence_arbitration"] is True
    assert health.json()["self_remediating_data_readiness"] is True


def test_artifact_and_bilingual_error_responses(tmp_path: Path) -> None:
    client, metrology = _client(tmp_path)

    artifact = client.get("/api/metrology/runs/metrology-web-001/overlay.jpg")
    feedback = client.get(
        "/api/metrology/runs/metrology-web-001/active-learning-feedback.zip"
    )
    missing_form = client.post("/api/metrology/analyze")
    metrology.failure = ProjectError(
        "E506",
        "量测输入无效",
        "Invalid metrology input",
        "检查掩膜",
        "Check the mask",
    )
    invalid = client.post(
        "/api/metrology/analyze",
        files={
            "image": ("road.png", b"source", "image/png"),
            "mask": ("mask.png", b"mask", "image/png"),
        },
        data={"calibration_mode": "pixel"},
    )

    assert artifact.status_code == 200
    assert artifact.content == b"metrology-overlay"
    assert artifact.headers["content-type"] == "image/jpeg"
    assert feedback.status_code == 200
    assert feedback.content == b"active-learning-feedback"
    assert feedback.headers["content-type"] == "application/zip"
    assert missing_form.status_code == 422
    assert missing_form.json()["error"]["code"] == "E506"
    assert invalid.status_code == 422
    assert invalid.json()["error"]["message_zh"] == "量测输入无效"


def test_planning_and_comparison_api_contracts(tmp_path: Path) -> None:
    client, metrology = _client(tmp_path)

    runs = client.get("/api/metrology/runs?limit=12")
    feedback_catalog = client.get("/api/metrology/feedback-catalog?limit=25")
    feedback_curation = client.post(
        "/api/metrology/feedback-curations",
        data={
            "seed": "7",
            "train_ratio": "0.7",
            "val_ratio": "0.2",
            "test_ratio": "0.1",
            "minimum_unique_sources": "12",
            "max_scene_hamming_distance": "5",
            "privacy_review_confirmed": "true",
            "label_qa_confirmed": "false",
        },
    )
    feedback_snapshot = client.post(
        "/api/metrology/feedback-curations/"
        "feedback-curation-001/snapshot-preflight"
    )
    autopilot_batch = client.post(
        "/api/metrology/autopilot-batches/finalize",
        data={
            "run_ids": '["metrology-web-001"]',
            "source_digests": json.dumps(["a" * 64]),
            "arbitration_ids": '["evidence-arbitration-001"]',
            "selected_count": "3",
            "failed_count": "1",
            "duplicate_count": "1",
            "retry_count": "1",
            "max_attempts": "2",
            "seed": "9",
            "minimum_unique_sources": "6",
            "max_scene_hamming_distance": "3",
        },
    )
    arbitration = client.post(
        "/api/evidence/arbitrate",
        data={
            "inspection_id": "inspection-web-001",
            "metrology_run_id": "metrology-web-001",
        },
    )
    plan = client.post(
        "/api/metrology/runs/metrology-web-001/maintenance-plan",
        data={
            "route_width_mm": "10",
            "route_depth_mm": "8",
            "waste_percent": "12",
            "unit_cost_per_liter": "25",
        },
    )
    comparison = client.post(
        "/api/metrology/compare",
        data={
            "baseline_run_id": "metrology-baseline-001",
            "current_run_id": "metrology-web-001",
            "elapsed_days": "30",
            "length_review_threshold_percent": "8",
            "width_review_threshold_percent": "12",
            "match_tolerance_mm": "4",
        },
    )
    downloaded_plan = client.get("/api/metrology/runs/metrology-web-001/plans/maintenance-001.json")
    downloaded_curation = client.get(
        "/api/metrology/feedback-curations/feedback-curation-001.json"
    )
    downloaded_snapshot = client.get(
        "/api/metrology/feedback-snapshots/feedback-snapshot-001.json"
    )
    downloaded_batch = client.get(
        "/api/metrology/autopilot-batches/autopilot-batch-001.json"
    )
    downloaded_arbitration = client.get(
        "/api/evidence/arbitrations/evidence-arbitration-001.json"
    )
    downloaded_comparison = client.get("/api/metrology/comparisons/comparison-001.json")
    downloaded_change_map = client.get("/api/metrology/comparisons/comparison-001/change-map.png")

    assert runs.status_code == 200
    assert runs.json()["returned_count"] == 1
    assert feedback_catalog.status_code == 200
    assert feedback_catalog.json()["item_count"] == 2
    assert metrology.feedback_catalog_limit == 25
    assert feedback_curation.status_code == 200
    assert feedback_curation.json()["curation"]["training_authorized"] is False
    assert metrology.feedback_curation_arguments == {
        "seed": 7,
        "train_ratio": 0.7,
        "val_ratio": 0.2,
        "test_ratio": 0.1,
        "minimum_unique_sources": 12,
        "max_scene_hamming_distance": 5,
        "privacy_review_confirmed": True,
        "label_qa_confirmed": False,
    }
    assert feedback_snapshot.status_code == 200
    assert feedback_snapshot.json()["snapshot"]["training_authorized"] is False
    assert metrology.feedback_snapshot_curation_id == "feedback-curation-001"
    assert autopilot_batch.status_code == 200
    assert autopilot_batch.json()["batch"]["training_authorized"] is False
    assert metrology.autopilot_batch_arguments == {
        "run_ids": '["metrology-web-001"]',
        "source_digests": json.dumps(["a" * 64]),
        "arbitration_ids": '["evidence-arbitration-001"]',
        "selected_count": 3,
        "failed_count": 1,
        "duplicate_count": 1,
        "retry_count": 1,
        "max_attempts": 2,
        "seed": 9,
        "minimum_unique_sources": 6,
        "max_scene_hamming_distance": 3,
    }
    assert arbitration.status_code == 200
    assert arbitration.json()["arbitration"]["training_authorized"] is False
    assert metrology.arbitration_arguments == {
        "inspection_run_name": "china-repair-mps-003",
        "inspection_id": "inspection-web-001",
        "metrology_run_id": "metrology-web-001",
    }
    assert plan.status_code == 200
    assert metrology.plan_arguments == {
        "run_id": "metrology-web-001",
        "route_width_mm": 10.0,
        "route_depth_mm": 8.0,
        "waste_percent": 12.0,
        "unit_cost_per_liter": 25.0,
    }
    assert comparison.status_code == 200
    assert metrology.compare_arguments == {
        "baseline_run_id": "metrology-baseline-001",
        "current_run_id": "metrology-web-001",
        "elapsed_days": 30.0,
        "length_review_threshold_percent": 8.0,
        "width_review_threshold_percent": 12.0,
        "match_tolerance_mm": 4.0,
    }
    assert downloaded_plan.status_code == 200
    assert downloaded_plan.headers["content-type"] == "application/json"
    assert downloaded_curation.status_code == 200
    assert downloaded_curation.headers["content-type"] == "application/json"
    assert downloaded_snapshot.status_code == 200
    assert downloaded_snapshot.headers["content-type"] == "application/json"
    assert downloaded_batch.status_code == 200
    assert downloaded_batch.headers["content-type"] == "application/json"
    assert downloaded_arbitration.status_code == 200
    assert downloaded_arbitration.headers["content-type"] == (
        "application/json"
    )
    assert downloaded_comparison.status_code == 200
    assert downloaded_comparison.headers["content-type"] == "application/json"
    assert downloaded_change_map.status_code == 200
    assert downloaded_change_map.headers["content-type"] == "image/png"


def test_local_proposal_api_contract(tmp_path: Path) -> None:
    client, metrology = _client(tmp_path)

    proposal = client.post(
        "/api/metrology/proposals",
        files={"image": ("road.png", b"source-bytes", "image/png")},
        data={"sensitivity": "0.65"},
    )
    mask = client.get("/api/metrology/proposals/proposal-001/proposal-mask.png")
    hotspots = client.get(
        "/api/metrology/proposals/proposal-001/review-hotspots.png"
    )
    evidence = client.get("/api/metrology/proposals/proposal-001/evidence.json")

    assert proposal.status_code == 200
    assert proposal.json()["candidate_found"] is True
    assert metrology.proposal_arguments == {
        "source_content": b"source-bytes",
        "source_filename": "road.png",
        "source_content_type": "image/png",
        "sensitivity": 0.65,
    }
    assert mask.status_code == 200
    assert mask.headers["content-type"] == "image/png"
    assert hotspots.status_code == 200
    assert hotspots.headers["content-type"] == "image/png"
    assert evidence.status_code == 200
    assert evidence.headers["content-type"] == "application/json"
