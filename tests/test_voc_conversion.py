from pathlib import Path

import pytest

from urbanvision_risk.data.voc import parse_voc_annotation, to_yolo_lines, voc_box_to_yolo
from urbanvision_risk.errors import ProjectError

VALID_XML = """\
<annotation>
  <filename>road.jpg</filename>
  <size><width>400</width><height>200</height></size>
  <object>
    <name>D40</name>
    <bndbox><xmin>100</xmin><ymin>50</ymin><xmax>300</xmax><ymax>150</ymax></bndbox>
  </object>
</annotation>
"""


def test_parse_and_convert_valid_voc(tmp_path: Path) -> None:
    xml_path = tmp_path / "road.xml"
    xml_path.write_text(VALID_XML, encoding="utf-8")

    record = parse_voc_annotation(xml_path)

    assert record.filename == "road.jpg"
    assert record.width == 400
    assert record.height == 200
    assert to_yolo_lines(record) == ["3 0.500000 0.500000 0.500000 0.500000"]


def test_voc_box_rejects_zero_width() -> None:
    with pytest.raises(ProjectError, match="E203"):
        voc_box_to_yolo((100, 10, 100, 50), (400, 200))


def test_parser_rejects_unknown_class(tmp_path: Path) -> None:
    xml_path = tmp_path / "unknown.xml"
    xml_path.write_text(VALID_XML.replace("D40", "D99"), encoding="utf-8")

    with pytest.raises(ProjectError, match="E203"):
        parse_voc_annotation(xml_path)


def test_parser_rejects_malformed_xml(tmp_path: Path) -> None:
    xml_path = tmp_path / "broken.xml"
    xml_path.write_text("<annotation><filename>road.jpg", encoding="utf-8")

    with pytest.raises(ProjectError, match="E202"):
        parse_voc_annotation(xml_path)
