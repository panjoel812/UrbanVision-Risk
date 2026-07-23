from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from urbanvision_risk.app.api import create_app
from urbanvision_risk.errors import ProjectError


class InspectionStub:
    def __init__(self, annotated: Path) -> None:
        self.annotated = annotated

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
        self.analyze_arguments: dict[str, Any] | None = None
        self.plan_arguments: dict[str, Any] | None = None
        self.compare_arguments: dict[str, Any] | None = None
        self.failure: ProjectError | None = None

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
        if run_id != "metrology-web-001" or artifact_name != "overlay.jpg":
            raise ProjectError("E201", "文件不存在", "Missing", "检查", "Check")
        return self.artifact

    def list_runs(self, *, limit: int = 50) -> dict[str, object]:
        return {
            "local_only": True,
            "returned_count": 1,
            "items": [{"run_id": "metrology-baseline-001"}],
        }

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
    assert "Precision Lab" in response.text
    assert "从检测框" in response.text
    assert "verifiable measurement" in response.text
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
    assert "/api/metrology/compare" in response.text
    assert "change-map.png" in response.text
    assert "https://" not in response.text
    assert "http://" not in response.text
    assert response.headers["x-frame-options"] == "DENY"
    assert "connect-src 'self'" in response.headers["content-security-policy"]


def test_detection_console_links_to_precision_lab(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

    response = client.get("/")

    assert response.status_code == 200
    assert 'href="/metrology"' in response.text
    assert "精密量测" in response.text
    assert "Precision Lab" in response.text


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

    health = client.get("/api/health")
    assert health.json()["precision_metrology"] is True
    assert health.json()["metrology_modes"] == ["pixel", "manual", "aruco"]


def test_artifact_and_bilingual_error_responses(tmp_path: Path) -> None:
    client, metrology = _client(tmp_path)

    artifact = client.get("/api/metrology/runs/metrology-web-001/overlay.jpg")
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
    assert missing_form.status_code == 422
    assert missing_form.json()["error"]["code"] == "E506"
    assert invalid.status_code == 422
    assert invalid.json()["error"]["message_zh"] == "量测输入无效"


def test_planning_and_comparison_api_contracts(tmp_path: Path) -> None:
    client, metrology = _client(tmp_path)

    runs = client.get("/api/metrology/runs?limit=12")
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
    downloaded_comparison = client.get("/api/metrology/comparisons/comparison-001.json")
    downloaded_change_map = client.get("/api/metrology/comparisons/comparison-001/change-map.png")

    assert runs.status_code == 200
    assert runs.json()["returned_count"] == 1
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
    assert downloaded_comparison.status_code == 200
    assert downloaded_comparison.headers["content-type"] == "application/json"
    assert downloaded_change_map.status_code == 200
    assert downloaded_change_map.headers["content-type"] == "image/png"
