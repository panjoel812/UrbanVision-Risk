import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DatasetSplit:
    train: tuple[str, ...]
    val: tuple[str, ...]
    test: tuple[str, ...]


def split_ids(
    ids: Sequence[str] | Iterable[str],
    seed: int = 42,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
) -> DatasetSplit:
    ordered = sorted(ids)
    if len(ordered) != len(set(ordered)):
        raise ValueError("duplicate identifiers are not allowed")
    if not ordered:
        raise ValueError("at least one identifier is required")
    if val_ratio < 0 or test_ratio < 0 or val_ratio + test_ratio >= 1:
        raise ValueError(
            "validation and test ratios must be non-negative and sum to less than 1"
        )

    shuffled = ordered.copy()
    random.Random(seed).shuffle(shuffled)
    val_count = round(len(shuffled) * val_ratio)
    test_count = round(len(shuffled) * test_ratio)
    train_count = len(shuffled) - val_count - test_count
    return DatasetSplit(
        train=tuple(shuffled[:train_count]),
        val=tuple(shuffled[train_count : train_count + val_count]),
        test=tuple(shuffled[train_count + val_count :]),
    )
