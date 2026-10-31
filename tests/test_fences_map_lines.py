# ABOUTME: Tests for markwright._fences.map_lines, the line-level twin that transforms lines and skips fenced code.
# The shared scanner is private infrastructure with its own contract, so it is tested directly.

from __future__ import annotations

from markwright._fences import map_lines


class TestMapLines:
    def test_transforms_a_plain_line_one_to_one(self) -> None:
        assert map_lines("hello", lambda line: [line.upper()]) == "HELLO"

    def test_leaves_a_fenced_code_block_untouched(self) -> None:
        source = "before\n```\ncode\n```\nafter"

        assert map_lines(source, lambda line: [line.upper()]) == "BEFORE\n```\ncode\n```\nAFTER"

    def test_expands_one_to_many_only_outside_a_fence(self) -> None:
        def transform(line: str) -> list[str]:
            return ["X", ""] if line == "hit" else [line]

        assert map_lines("hit\n```\nhit\n```", transform) == "X\n\n```\nhit\n```"

    def test_skips_an_indented_in_list_fence(self) -> None:
        def transform(line: str) -> list[str]:
            return ["X"] if line.strip() == "hit" else [line]

        source = "- item\n\n    ```\n    hit\n    ```"

        assert map_lines(source, transform) == source

    def test_transforms_a_line_after_an_unclosed_fence(self) -> None:
        def transform(line: str) -> list[str]:
            return ["X"] if line.strip() == "hit" else [line]

        assert map_lines("```\nhit", transform) == "```\nX"
