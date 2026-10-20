# ABOUTME: Tests for markwright._fences.map_prose, which transforms prose and skips fenced and inline code.
# The shared scanner is private infrastructure with its own contract, so it is tested directly.

from __future__ import annotations

from markwright._fences import map_prose


class TestMapProse:
    def test_transforms_a_plain_paragraph(self) -> None:
        assert map_prose("hello world", str.upper) == "HELLO WORLD"

    def test_leaves_a_fenced_code_block_untouched(self) -> None:
        source = "before\n```\ncode here\n```\nafter"

        assert map_prose(source, str.upper) == "BEFORE\n```\ncode here\n```\nAFTER"

    def test_leaves_an_inline_code_span_untouched(self) -> None:
        assert map_prose("say `:x:` now", str.upper) == "SAY `:x:` NOW"

    def test_handles_a_multi_backtick_code_span(self) -> None:
        assert map_prose("a ``b ` c`` d", str.upper) == "A ``b ` c`` D"

    def test_preserves_text_with_no_prose_to_change(self) -> None:
        assert map_prose("", str.upper) == ""
