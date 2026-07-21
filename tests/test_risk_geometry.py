import pytest

from urbanvision_risk.errors import ProjectError
from urbanvision_risk.risk.geometry import clip_rectangle, rectangle_union_area


@pytest.mark.parametrize(
    ("rectangles", "expected"),
    [
        ([(0.0, 0.0, 10.0, 10.0), (20.0, 0.0, 30.0, 10.0)], 200.0),
        ([(0.0, 0.0, 10.0, 10.0), (5.0, 0.0, 15.0, 10.0)], 150.0),
        ([(0.0, 0.0, 10.0, 10.0), (2.0, 2.0, 8.0, 8.0)], 100.0),
        ([(0.0, 0.0, 10.0, 10.0), (10.0, 0.0, 20.0, 10.0)], 200.0),
        ([], 0.0),
    ],
)
def test_rectangle_union_area_handles_overlap(
    rectangles: list[tuple[float, float, float, float]], expected: float
) -> None:
    assert rectangle_union_area(rectangles) == pytest.approx(expected)


def test_clip_rectangle_accepts_small_rounding_drift() -> None:
    rectangle, clipped = clip_rectangle(
        (-0.5, 0, 10, 10), width=100, height=100, tolerance=1, context="sample"
    )

    assert rectangle == (0.0, 0.0, 10.0, 10.0)
    assert clipped is True


@pytest.mark.parametrize(
    "box",
    [
        (-2, 0, 10, 10),
        (10, 0, 5, 10),
        (0, 0, float("nan"), 10),
        (0, 0, 0, 10),
    ],
)
def test_clip_rectangle_rejects_invalid_geometry(box: tuple[float, ...]) -> None:
    with pytest.raises(ProjectError, match="E403"):
        clip_rectangle(box, width=100, height=100, tolerance=1, context="sample")
