"""Static consistency checks for presentation texts."""

import ast
import warnings
from pathlib import Path

from mood_tracker.presentation.constants import TEXTS, TextKey

ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIR = ROOT / "src" / "mood_tracker"


class TextKeyReferenceVisitor(ast.NodeVisitor):
    """Collect explicit ``TextKey.MEMBER`` references from Python code."""

    def __init__(self) -> None:
        self.used: set[TextKey] = set()

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if (
            isinstance(node.value, ast.Name)
            and node.value.id == "TextKey"
            and node.attr in TextKey.__members__
        ):
            self.used.add(TextKey[node.attr])

        self.generic_visit(node)


def find_used_text_keys() -> set[TextKey]:
    """Return text keys referenced outside the text registry itself."""
    visitor = TextKeyReferenceVisitor()

    for path in SOURCE_DIR.rglob("*.py"):
        if path.name == "text.py":
            continue

        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        visitor.visit(tree)

    return visitor.used


def test_every_text_key_has_translation() -> None:
    """Ensure every enum member has an entry in the text registry."""
    assert set(TextKey) == set(TEXTS)


def test_unused_texts_are_reported() -> None:
    """Warn about registered texts without an explicit source reference."""
    unused = set(TextKey) - find_used_text_keys()

    for key in sorted(unused, key=lambda item: item.value):
        warnings.warn(
            f"Unused presentation text: {key.name} ({key.value})",
            UserWarning,
            stacklevel=1,
        )
