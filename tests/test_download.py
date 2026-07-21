import io
import zipfile
from pathlib import Path

import pytest

from urbanvision_risk.data.download import (
    RDD2022_CHINA_MOTORBIKE_URL,
    download_file,
    safe_extract_zip,
    sha256_file,
)
from urbanvision_risk.errors import ProjectError


class Response(io.BytesIO):
    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def test_dataset_url_uses_complete_official_s3_object_path() -> None:
    assert RDD2022_CHINA_MOTORBIKE_URL == (
        "https://bigdatacup.s3.ap-northeast-1.amazonaws.com/"
        "2022/CRDDC2022/RDD2022/Country_Specific_Data_CRDDC2022/"
        "RDD2022_China_MotorBike.zip"
    )


def test_download_streams_to_final_file_and_returns_digest(tmp_path: Path) -> None:
    destination = tmp_path / "archive.zip"
    payload = b"urbanvision-test-payload"

    digest = download_file(
        "https://example.invalid/archive.zip",
        destination,
        opener=lambda _url: Response(payload),
        chunk_size=5,
    )

    assert destination.read_bytes() == payload
    assert digest == sha256_file(destination)
    assert not destination.with_suffix(".zip.part").exists()


def test_download_refuses_to_overwrite_existing_file(tmp_path: Path) -> None:
    destination = tmp_path / "archive.zip"
    destination.write_bytes(b"existing")

    with pytest.raises(ProjectError, match="E204"):
        download_file("https://example.invalid/archive.zip", destination)


def test_safe_extract_rejects_traversal_before_writing(tmp_path: Path) -> None:
    archive = tmp_path / "malicious.zip"
    destination = tmp_path / "raw"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("valid/file.txt", "valid")
        bundle.writestr("../escape.txt", "escape")

    with pytest.raises(ProjectError, match="E203"):
        safe_extract_zip(archive, destination)

    assert not destination.exists()
    assert not (tmp_path / "escape.txt").exists()


def test_safe_extract_writes_only_inside_destination(tmp_path: Path) -> None:
    archive = tmp_path / "valid.zip"
    destination = tmp_path / "raw"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("dataset/images/road.jpg", "image-bytes")

    extracted = safe_extract_zip(archive, destination)

    assert extracted == (destination / "dataset/images/road.jpg",)
    assert extracted[0].read_text(encoding="utf-8") == "image-bytes"
