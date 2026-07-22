import json
from pathlib import Path

import pytest
from PIL import Image

from urbanvision_risk.data.prepare import discover_pairs, prepare_dataset
from urbanvision_risk.errors import ProjectError


def write_source_pair(root: Path, index: int) -> None:
    images = root / "train" / "images"
    annotations = root / "train" / "annotations" / "xmls"
    images.mkdir(parents=True, exist_ok=True)
    annotations.mkdir(parents=True, exist_ok=True)
    name = f"road-{index:02d}"
    Image.new("RGB", (100, 50), color="gray").save(images / f"{name}.jpg")
    (annotations / f"{name}.xml").write_text(
        f"""<annotation>
        <filename>{name}.jpg</filename>
        <size><width>100</width><height>50</height></size>
        <object><name>D40</name><bndbox>
        <xmin>10</xmin><ymin>5</ymin><xmax>40</xmax><ymax>25</ymax>
        </bndbox></object></annotation>""",
        encoding="utf-8",
    )


def test_prepare_dataset_writes_split_labels_and_manifest(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    output_root = tmp_path / "processed"
    archive = tmp_path / "archive.zip"
    archive.write_bytes(b"fixture archive digest input")
    for index in range(10):
        write_source_pair(raw_root, index)

    manifest = prepare_dataset(raw_root, archive, output_root)

    assert manifest["file_counts"] == {"train": 8, "val": 1, "test": 1}
    assert manifest["object_counts"] == {
        "D00": 0,
        "D10": 0,
        "D20": 0,
        "D40": 10,
        "Repair": 0,
    }
    assert manifest["invalid_records"] == 0
    assert len(manifest["input_digest"]) == 64
    assert len(list((output_root / "labels" / "train").glob("*.txt"))) == 8
    persisted = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))
    assert persisted == manifest


def test_discover_pairs_rejects_xml_with_missing_image(tmp_path: Path) -> None:
    annotation = tmp_path / "missing.xml"
    annotation.write_text(
        """<annotation><filename>missing.jpg</filename>
        <size><width>100</width><height>50</height></size></annotation>""",
        encoding="utf-8",
    )

    with pytest.raises(ProjectError, match="E202"):
        discover_pairs(tmp_path)
