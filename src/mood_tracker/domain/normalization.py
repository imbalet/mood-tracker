from __future__ import annotations


def normalize_integer(value: int, minimum: int, maximum: int) -> float:
    """Normalize an inclusive integer scale value into the range 0..1."""
    if minimum >= maximum:
        msg = "minimum must be smaller than maximum"
        raise ValueError(msg)
    if not minimum <= value <= maximum:
        msg = "value must be inside the scale range"
        raise ValueError(msg)
    return (value - minimum) / (maximum - minimum)
