from pathlib import Path

from PIL import Image

from urbanvision_risk.data.validate import validate_prepared_dataset


def write_sample(root: Path, split: str, name: str, label: str) -> None:
    image_dir = root / "images" / split
    label_dir = root / "labels" / split
    image_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (40, 20), color="gray").save(image_dir / f"{name}.jpg")
    (label_dir / f"{name}.txt").write_text(label, encoding="utf-8")


def test_valid_dataset_reports_counts(tmp_path: Path) -> None:
    write_sample(tmp_path, "train", "train-road", "3 0.5 0.5 0.5 0.5\n")
    write_sample(tmp_path, "val", "val-road", "0 0.5 0.5 0.2 0.2\n")
    write_sample(tmp_path, "test", "test-road", "")

    report = validate_prepared_dataset(tmp_path)

    assert report.ok is True
    assert report.image_counts == {"train": 1, "val": 1, "test": 1}
    assert report.object_counts == {
        "D00": 1,
        "D10": 0,
        "D20": 0,
        "D40": 1,
        "Repair": 0,
    }
    assert report.errors == ()


def test_invalid_label_and_duplicate_stem_are_reported(tmp_path: Path) -> None:
    write_sample(tmp_path, "train", "same-road", "9 0.5 0.5 0.5 0.5\n")
    write_sample(tmp_path, "val", "same-road", "0 0.5 0.5 0.2 0.2\n")
    (tmp_path / "images" / "test").mkdir(parents=True)
    (tmp_path / "labels" / "test").mkdir(parents=True)

    report = validate_prepared_dataset(tmp_path)

    assert report.ok is False
    assert any("class index" in error for error in report.errors)
    assert any("multiple splits" in error for error in report.errors)


def test_corrupt_image_is_reported(tmp_path: Path) -> None:
    image_dir = tmp_path / "images" / "train"
    label_dir = tmp_path / "labels" / "train"
    image_dir.mkdir(parents=True)
    label_dir.mkdir(parents=True)
    (image_dir / "broken.jpg").write_bytes(b"not-a-jpeg")
    (label_dir / "broken.txt").write_text("", encoding="utf-8")
    for split in ("val", "test"):
        (tmp_path / "images" / split).mkdir(parents=True)
        (tmp_path / "labels" / split).mkdir(parents=True)

    report = validate_prepared_dataset(tmp_path)

    assert report.ok is False
    assert any("cannot be opened" in error for error in report.errors)
