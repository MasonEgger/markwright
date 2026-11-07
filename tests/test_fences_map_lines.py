# ABOUTME: Tests for markwright._fences.map_lines, the line-level twin that transforms lines and skips fenced code.
# Exempt from the public-API-only rule: the _fences scanner has a contract of its own and is tested directly.

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


def _hit_to_x(line: str) -> list[str]:
    return ["X"] if line.strip() == "hit" else [line]


class TestMapLinesIndentation:
    def test_skips_a_tab_indented_in_list_fence(self) -> None:
        source = "- item\n\n\t```\n\thit\n\t```"

        assert map_lines(source, _hit_to_x) == source

    def test_skips_a_top_level_indented_code_block(self) -> None:
        source = "para\n\n    hit\n"

        assert map_lines(source, _hit_to_x) == source

    def test_treats_a_tab_indented_top_level_line_as_code(self) -> None:
        source = "para\n\n\thit"

        assert map_lines(source, _hit_to_x) == source

    def test_treats_four_column_fence_lines_outside_a_list_as_code(self) -> None:
        source = "para\n\n    ```\n    hit\n    ```"

        assert map_lines(source, _hit_to_x) == source

    def test_transforms_an_indented_line_under_a_list_item(self) -> None:
        assert map_lines("- item\n\n    hit", _hit_to_x) == "- item\n\nX"

    def test_transforms_a_lazy_continuation_line(self) -> None:
        assert map_lines("para\n    hit", _hit_to_x) == "para\nX"

    def test_keeps_an_indented_code_block_open_across_a_blank_line(self) -> None:
        source = "para\n\n    hit\n\n    hit\n"

        assert map_lines(source, _hit_to_x) == source

    def test_ends_an_indented_code_block_at_a_less_indented_line(self) -> None:
        assert map_lines("para\n\n    hit\nhit", _hit_to_x) == "para\n\n    hit\nX"
