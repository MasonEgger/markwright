# ABOUTME: Tests for the span-edit guard in the shared HTML token module.
# Exempt from the public-API-only rule: no public path can produce overlapping edits, so the guard is tested directly.

from __future__ import annotations

import pytest

from markwright._html import apply_edits


class TestApplyEdits:
    def test_overlapping_spans_raise(self) -> None:
        with pytest.raises(ValueError, match="Overlapping"):
            apply_edits("0123456789", [(2, 6, "a"), (4, 8, "b")])

    def test_nested_spans_raise(self) -> None:
        with pytest.raises(ValueError, match="Overlapping"):
            apply_edits("0123456789", [(2, 8, "a"), (3, 4, "b")])

    def test_adjacent_spans_apply(self) -> None:
        assert apply_edits("0123456789", [(2, 4, "a"), (4, 6, "b")]) == "01ab6789"

    def test_insertions_at_a_span_edge_apply(self) -> None:
        assert apply_edits("0123", [(1, 3, "x"), (3, 3, "y"), (1, 1, "z")]) == "0zxy3"
