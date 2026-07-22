import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from urbanvision_risk.app.service import MAX_UPLOAD_BYTES, LocalInspectionService
from urbanvision_risk.errors import ProjectError
from urbanvision_risk.paths import get_paths

ROOT = Path(__file__).resolve().parents[1]
RUN = "china-baseline-001"
INSPECTION = "inspection-test-001"


class Scalar:
    def __init__(self, value: float) -> None:
        self.value = value

    def item(self) -> float:
        return self.value


class Vector:
    def __init__(self, values: list[float]) -> None:
        self.values = values

    def tolist(self) -> list[float]:
        return self.values


class FakeResult(SimpleNamespace):
    def plot(self) -> np.ndarray:
        plotted = np.zeros((100, 100, 3), dtype=np.uint8)
        plotted[:, :, 1] = 140
        return plotted


class FakeModel:
    def __init__(self, result: FakeResult, calls: list[dict[str, object]]) -> None:
        self.result = result
        self.calls = calls

    def predict(self, **kwargs: object) -> list[FakeResult]:
        self.calls.append(kwargs)
        return [self.result]


def _image_bytes(
    *, image_format: str = "JPEG", size: tuple[int, int] = (100, 100)
) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, (91, 104, 96)).save(buffer, format=image_format)
    return buffer.getvalue()


def _service(
    tmp_path: Path, *, inspection_id: str = INSPECTION
) -> tuple[LocalInspectionService, list[dict[str, object]]]:
    paths = get_paths(tmp_path)
    checkpoint = paths.experiments / RUN / "weights" / "best.pt"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_bytes(b"checkpoint")
    paths.configs.mkdir(parents=True)
    (paths.configs / "risk-v0.2.yaml").write_text(
        (ROOT / "configs" / "risk-v0.2.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    box = SimpleNamespace(
        cls=[Scalar(3)],
        conf=[Scalar(0.87)],
        xyxy=[Vector([10.0, 10.0, 40.0, 40.0])],
    )
    result = FakeResult(path="memory-image.jpg", orig_shape=(100, 100), boxes=[box])
    calls: list[dict[str, object]] = []
    service = LocalInspectionService(
        RUN,
        paths=paths,
        model_factory=lambda _: FakeModel(result, calls),
        id_factory=lambda: inspection_id,
    )
    return service, calls


def test_local_inspection_runs_detection_risk_and_writes_auditable_artifacts(
    tmp_path: Path,
) -> None:
    service, calls = _service(tmp_path)

    response = service.inspect_bytes(
        _image_bytes(),
        filename="../unsafe/road.jpg",
        content_type="image/jpeg",
    )

    output = service.paths.inspections / RUN / INSPECTION
    assert response["inspection_id"] == INSPECTION
    assert response["source_filename"] == "road.jpg"
    assert response["annotated_url"] == f"/api/inspections/{INSPECTION}/annotated.jpg"
    assert response["prediction"]["counts"] == {
        "D00": 0,
        "D10": 0,
        "D20": 0,
        "D40": 1,
        "Repair": 0,
    }
    assert response["risk"]["risk_score"] == 28.8
    assert response["risk"]["risk_level"] == "moderate"
    assert sorted(path.name for path in output.iterdir()) == [
        "annotated.jpg",
        "inspection-manifest.json",
        "prediction.json",
        "risk.json",
        "source.jpg",
    ]
    manifest = json.loads((output / "inspection-manifest.json").read_text(encoding="utf-8"))
    for filename, digest_key in (
        ("source.jpg", "source_jpg_sha256"),
        ("annotated.jpg", "annotated_jpg_sha256"),
        ("prediction.json", "prediction_json_sha256"),
        ("risk.json", "risk_json_sha256"),
    ):
        assert hashlib.sha256((output / filename).read_bytes()).hexdigest() == manifest[digest_key]
    assert calls[0]["device"] == "mps"
    assert calls[0]["conf"] == 0.25
    assert isinstance(calls[0]["source"], np.ndarray)


def test_local_inspection_health_does_not_expose_absolute_paths(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)

    health = service.health_payload()

    assert health["local_only"] is True
    assert health["device"] == "mps"
    assert health["checkpoint"] == "best.pt"
    assert str(tmp_path) not in json.dumps(health)


def test_high_resolution_image_runs_overlapping_tiles_and_keeps_repair_unscored(
    tmp_path: Path,
) -> None:
    paths = get_paths(tmp_path)
    checkpoint = paths.experiments / RUN / "weights" / "best.pt"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_bytes(b"checkpoint")
    paths.configs.mkdir(parents=True)
    (paths.configs / "risk-v0.2.yaml").write_text(
        (ROOT / "configs" / "risk-v0.2.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    repair_box = SimpleNamespace(
        cls=[Scalar(4)],
        conf=[Scalar(0.81)],
        xyxy=[Vector([20.0, 30.0, 300.0, 260.0])],
    )
    calls: list[dict[str, object]] = []

    class TiledModel:
        def predict(self, **kwargs: object) -> list[FakeResult]:
            calls.append(kwargs)
            source = kwargs["source"]
            if isinstance(source, list):
                return [
                    FakeResult(path="tile.jpg", orig_shape=(1000, 1024), boxes=[repair_box]),
                    FakeResult(path="tile.jpg", orig_shape=(1000, 1024), boxes=[]),
                ]
            return [FakeResult(path="full.jpg", orig_shape=(1000, 1300), boxes=[])]

    service = LocalInspectionService(
        RUN,
        paths=paths,
        model_factory=lambda _: TiledModel(),
        id_factory=lambda: INSPECTION,
    )

    response = service.inspect_bytes(
        _image_bytes(size=(1300, 1000)),
        filename="large-road.jpg",
        content_type="image/jpeg",
    )

    assert len(calls) == 2
    assert calls[1]["imgsz"] == 1024
    assert len(calls[1]["source"]) == 2  # type: ignore[arg-type]
    assert response["prediction"]["counts"]["Repair"] == 1
    assert response["risk"]["risk_score"] == 0.0
    assert response["risk"]["decision_status"] == "review_required"
    assert response["risk"]["auxiliary_observations"][0]["count"] == 1
    manifest = json.loads(
        (
            paths.inspections / RUN / INSPECTION / "inspection-manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["inference"]["mode"] == "full_and_tiled"
    assert manifest["inference"]["tile_count"] == 2


@pytest.mark.parametrize(
    ("content", "content_type"),
    (
        (b"not-an-image", "image/jpeg"),
        (_image_bytes(), "application/octet-stream"),
        (b"x" * (MAX_UPLOAD_BYTES + 1), "image/jpeg"),
    ),
)
def test_local_inspection_rejects_invalid_uploads(
    tmp_path: Path, content: bytes, content_type: str
) -> None:
    service, calls = _service(tmp_path)

    with pytest.raises(ProjectError, match="E601"):
        service.inspect_bytes(content, filename="road.jpg", content_type=content_type)

    assert calls == []
    assert not service.paths.inspections.exists()


def test_local_inspection_never_overwrites_an_existing_id(tmp_path: Path) -> None:
    service, calls = _service(tmp_path)
    content = _image_bytes()
    service.inspect_bytes(content, filename="road.jpg", content_type="image/jpeg")

    with pytest.raises(ProjectError, match="E204"):
        service.inspect_bytes(content, filename="road.jpg", content_type="image/jpeg")

    assert len(calls) == 1


def test_local_inspection_converts_model_failure_to_bilingual_error(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)

    class BrokenModel:
        def predict(self, **_: object) -> list[object]:
            raise RuntimeError("inference failed")

    service.model = BrokenModel()

    with pytest.raises(ProjectError, match="E301"):
        service.inspect_bytes(_image_bytes(), filename="road.jpg", content_type="image/jpeg")

    assert not service.paths.inspections.exists()
