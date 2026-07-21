import pytest

from urbanvision_risk.data.split import split_ids


def test_split_is_deterministic_and_disjoint() -> None:
    identifiers = [f"image-{index:02d}" for index in range(20)]

    first = split_ids(identifiers)
    second = split_ids(reversed(identifiers))

    assert first == second
    assert len(first.train) == 16
    assert len(first.val) == 2
    assert len(first.test) == 2
    assert set(first.train).isdisjoint(first.val)
    assert set(first.train).isdisjoint(first.test)
    assert set(first.val).isdisjoint(first.test)


def test_split_rejects_duplicate_identifiers() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        split_ids(["same", "same"])
