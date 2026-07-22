from types import SimpleNamespace

from urbanvision_risk.detection.tiled import (
    DetectionCandidate,
    class_aware_nms,
    extract_candidates,
    tile_windows,
)


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


def test_tile_windows_cover_large_image_edges_with_overlap() -> None:
    windows = tile_windows(3648, 2736)

    assert windows[0] == (0, 0, 1024, 1024)
    assert windows[-1] == (2624, 1712, 3648, 2736)
    assert len(windows) == 20


def test_extract_translates_tile_coordinates_to_full_image() -> None:
    box = SimpleNamespace(
        cls=[Scalar(2)],
        conf=[Scalar(0.8)],
        xyxy=[Vector([10.0, 20.0, 110.0, 220.0])],
    )

    candidates = extract_candidates(
        SimpleNamespace(boxes=[box]),
        offset_x=800,
        offset_y=1600,
        image_width=3648,
        image_height=2736,
    )

    assert candidates == [
        DetectionCandidate(2, 0.8, (810.0, 1620.0, 910.0, 1820.0))
    ]


def test_nms_removes_same_class_overlap_but_keeps_other_classes() -> None:
    candidates = [
        DetectionCandidate(0, 0.9, (0, 0, 100, 100)),
        DetectionCandidate(0, 0.8, (5, 5, 105, 105)),
        DetectionCandidate(4, 0.7, (5, 5, 105, 105)),
    ]

    kept = class_aware_nms(candidates)

    assert kept == [candidates[0], candidates[2]]
