from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from urbanvision_risk.app.api import create_app
from urbanvision_risk.app.serve import validate_bind
from urbanvision_risk.errors import ProjectError


class StubService:
    def __init__(self, annotated: Path) -> None:
        self.annotated = annotated
        self.upload: tuple[bytes, str | None, str] | None = None
        self.failure: ProjectError | None = None

    def health_payload(self) -> dict[str, object]:
        return {
            "app_version": "1.0.0",
            "run_name": "china-baseline-001",
            "checkpoint": "best.pt",
            "device": "mps",
            "confidence": 0.25,
            "local_only": True,
        }

    def inspect_bytes(
        self, content: bytes, *, filename: str | None, content_type: str
    ) -> dict[str, object]:
        if self.failure:
            raise self.failure
        self.upload = (content, filename, content_type)
        return {
            "inspection_id": "inspection-test-001",
            "annotated_url": "/api/inspections/inspection-test-001/annotated.jpg",
            "prediction": {"counts": {}, "detections": []},
            "risk": {"risk_score": 0.0},
        }

    def annotated_path(self, inspection_id: str) -> Path:
        if inspection_id != "inspection-test-001":
            raise ProjectError("E201", "图片不存在", "Image missing", "检查编号", "Check the ID")
        return self.annotated


@pytest.fixture
def local_client(tmp_path: Path) -> tuple[TestClient, StubService]:
    annotated = tmp_path / "annotated.jpg"
    annotated.write_bytes(b"jpeg")
    service = StubService(annotated)
    return TestClient(create_app(service)), service  # type: ignore[arg-type]


def test_local_app_page_is_bilingual_private_and_self_contained(
    local_client: tuple[TestClient, StubService],
) -> None:
    client, _ = local_client

    response = client.get("/")

    assert response.status_code == 200
    assert "道路缺陷，" in response.text
    assert "从图片到可解释结果" in response.text
    assert "Road damage," in response.text
    assert "from image to explainable result" in response.text
    assert "维护复核优先级，不是道路安全判定" in response.text
    assert "image-input" in response.text
    assert "https://" not in response.text
    assert "http://" not in response.text
    assert response.headers["x-frame-options"] == "DENY"
    assert "connect-src 'self'" in response.headers["content-security-policy"]


def test_health_and_upload_contract(local_client: tuple[TestClient, StubService]) -> None:
    client, service = local_client

    health = client.get("/api/health")
    response = client.post(
        "/api/inspect",
        files={"image": ("road.jpg", b"image-bytes", "image/jpeg")},
    )

    assert health.status_code == 200
    assert health.json()["local_only"] is True
    assert response.status_code == 200
    assert response.json()["inspection_id"] == "inspection-test-001"
    assert service.upload == (b"image-bytes", "road.jpg", "image/jpeg")


def test_annotated_image_is_served_from_the_service(
    local_client: tuple[TestClient, StubService],
) -> None:
    client, _ = local_client

    response = client.get("/api/inspections/inspection-test-001/annotated.jpg")

    assert response.status_code == 200
    assert response.content == b"jpeg"
    assert response.headers["content-type"] == "image/jpeg"


def test_missing_upload_and_project_errors_are_structured_and_bilingual(
    local_client: tuple[TestClient, StubService],
) -> None:
    client, service = local_client
    missing = client.post("/api/inspect")
    service.failure = ProjectError(
        "E601",
        "上传图片无效",
        "Uploaded image is invalid",
        "使用 JPEG",
        "Use JPEG",
        "content_type=text/plain",
    )
    invalid = client.post(
        "/api/inspect",
        files={"image": ("road.txt", b"bad", "text/plain")},
    )

    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "E601"
    assert "有效的图片" in missing.json()["error"]["message_zh"]
    assert invalid.status_code == 400
    assert invalid.json()["error"] == {
        "code": "E601",
        "message_zh": "上传图片无效",
        "message_en": "Uploaded image is invalid",
        "recovery_zh": "使用 JPEG",
        "recovery_en": "Use JPEG",
        "context": "content_type=text/plain",
    }


@pytest.mark.parametrize(
    ("host", "port"),
    (("0.0.0.0", 8000), ("192.168.1.4", 8000), ("127.0.0.1", 0), ("localhost", 70000)),
)
def test_server_rejects_nonlocal_or_invalid_bindings(host: str, port: int) -> None:
    with pytest.raises(ProjectError, match="E302"):
        validate_bind(host, port)


def test_server_accepts_loopback_binding() -> None:
    assert validate_bind("127.0.0.1", 8000) == ("127.0.0.1", 8000)
