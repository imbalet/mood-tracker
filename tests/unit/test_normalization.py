import pytest

from mood_tracker.domain.normalization import normalize_integer


def test_normalize_integer_returns_fraction() -> None:
    assert normalize_integer(value=2, minimum=0, maximum=4) == 0.5


@pytest.mark.parametrize(
    ("value", "minimum", "maximum"),
    [(0, 1, 2), (3, 0, 2), (1, 1, 1)],
)
def test_normalize_integer_rejects_invalid_ranges(
    value: int, minimum: int, maximum: int
) -> None:
    with pytest.raises(ValueError):
        normalize_integer(value=value, minimum=minimum, maximum=maximum)
