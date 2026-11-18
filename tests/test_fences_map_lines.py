# ABOUTME: Tests for markwright._fences.map_lines, the line-level twin that transforms lines and skips fenced code.
# Exempt from the public-API-only rule: the _fences scanner has a contract of its own and is tested directly.

from __future__ import annotations

import time

from markwright._fences import map_directive_lines, map_lines


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


_BLOCK_OPENERS = [
    '!!! note "Title"',
    "!!!note",
    "??? note",
    "???+ note",
    '??? "Title"',
    '=== "Tab"',
    '===+ "Tab"',
    '===! "Tab"',
    ": definition",
    "[^note]: footnote",
]


def _keep_indent_x(line: str) -> list[str]:
    """Replace a "hit" line with "X" at the same indentation, as an expanding stage keeps it."""
    return [line.replace("hit", "X")] if line.strip() == "hit" else [line]


class TestMapLinesBlockBodies:
    def test_transforms_a_directive_in_each_block_opener_body(self) -> None:
        for opener in _BLOCK_OPENERS:
            source = f"term\n{opener}\n\n    hit\n"

            assert map_lines(source, _keep_indent_x) == f"term\n{opener}\n\n    X\n", opener

    def test_transforms_a_directive_straight_under_an_opener(self) -> None:
        assert map_lines("!!! note\n    hit", _keep_indent_x) == "!!! note\n    X"

    def test_transforms_a_directive_after_a_second_body_paragraph(self) -> None:
        source = "!!! note\n    first\n\n    hit"

        assert map_lines(source, _keep_indent_x) == "!!! note\n    first\n\n    X"

    def test_skips_a_fence_in_an_opener_body(self) -> None:
        source = "!!! note\n\n    ```\n    hit\n    ```\n"

        assert map_lines(source, _keep_indent_x) == source

    def test_skips_a_line_four_columns_further_after_a_blank_line(self) -> None:
        source = "!!! note\n    body\n\n        hit"

        assert map_lines(source, _keep_indent_x) == source

    def test_still_skips_indented_code_after_an_unrelated_paragraph(self) -> None:
        source = "!!! note\n    body\n\npara\n\n    hit"

        assert map_lines(source, _keep_indent_x) == source

    def test_transforms_a_body_nested_in_a_list_item(self) -> None:
        assert map_lines("- item\n\n    !!! note\n        hit", _keep_indent_x) == "- item\n\n    !!! note\n        X"

    def test_a_bare_marker_is_not_an_opener(self) -> None:
        source = "!!!\n\n    hit"

        assert map_lines(source, _keep_indent_x) == source


class TestMapLinesBlockBodyBoundaries:
    def test_skips_indented_code_that_starts_a_body(self) -> None:
        source = "!!! note\n\n        hit"

        assert map_lines(source, _keep_indent_x) == source

    def test_transforms_body_prose_after_indented_code_in_the_body(self) -> None:
        source = "!!! note\n    body\n\n        code\n\n    hit"

        assert map_lines(source, _keep_indent_x) == "!!! note\n    body\n\n        code\n\n    X"

    def test_skips_a_line_that_follows_a_false_opener(self) -> None:
        for false_opener in ["=== Tab", '!!! "Title"', "!!! note: hi", "!!! ", "???", '=== "Tab" extra', ":nospace"]:
            source = f"para\n{false_opener}\n\n    hit"

            assert map_lines(source, _keep_indent_x) == source, false_opener

    def test_skips_a_line_after_a_definition_at_the_start_of_the_document(self) -> None:
        source = ": definition\n\n    hit"

        assert map_lines(source, _keep_indent_x) == source

    def test_skips_a_line_after_an_opener_that_is_indented_code(self) -> None:
        source = "para\n\n    !!! note\n\n        hit"

        assert map_lines(source, _keep_indent_x) == source

    def test_transforms_a_directive_after_a_multi_word_admonition_class(self) -> None:
        assert map_lines("!!! note inline end\n    hit", _keep_indent_x) == "!!! note inline end\n    X"


class TestMapDirectiveLines:
    def test_keeps_the_indentation_on_every_line_of_an_expansion(self) -> None:
        def render(line: str) -> str | None:
            return "<div>\n\n  <b>x</b>\n</div>" if line.strip() == "hit" else None

        source = "!!! note\n\n    hit"

        assert map_directive_lines(source, render) == "!!! note\n\n    <div>\n\n      <b>x</b>\n    </div>"

    def test_expands_a_column_zero_directive_without_indentation(self) -> None:
        assert map_directive_lines("hit", lambda line: "<a>\n<b>") == "<a>\n<b>"

    def test_leaves_a_directive_in_a_fence_and_other_lines_alone(self) -> None:
        source = "keep\n```\nhit\n```"

        assert map_directive_lines(source, lambda line: "X" if line == "hit" else None) == source


class TestMapLinesListBeforeOpener:
    def test_skips_indented_code_under_a_list_item_continuation(self) -> None:
        source = "!!! note\n    - item\n      text\n\n            hit"

        assert map_lines(source, _keep_indent_x) == source


class TestMapLinesOpenerColumn:
    def test_skips_a_body_under_an_admonition_opener_indented_in_a_top_level_block(self) -> None:
        for opener in ["  !!! note", "  ??? note", '  === "Tab"', "   !!! note"]:
            source = f"{opener}\n\n        hit"

            assert map_lines(source, _keep_indent_x) == source, opener

    def test_skips_a_body_under_an_opener_that_is_off_the_list_content_column(self) -> None:
        source = "- item\n\n      !!! note\n\n          hit"

        assert map_lines(source, _keep_indent_x) == source

    def test_transforms_a_body_under_an_opener_at_the_list_content_column(self) -> None:
        source = "- item\n\n    !!! note\n\n        hit"

        assert map_lines(source, _keep_indent_x) == "- item\n\n    !!! note\n\n        X"

    def test_transforms_a_body_under_an_indented_footnote_or_definition(self) -> None:
        for opener in ["  [^1]: foot", "  : dd"]:
            source = f"term\n{opener}\n\n    hit"

            assert map_lines(source, _keep_indent_x) == f"term\n{opener}\n\n    X", opener

    def test_skips_a_footnote_body_inside_a_list_item(self) -> None:
        source = "- item\n\n    [^1]: foot\n\n        hit"

        assert map_lines(source, _keep_indent_x) == source

    def test_transforms_a_definition_body_inside_an_admonition(self) -> None:
        source = "!!! note\n\n    term\n    : dd\n\n        hit"

        assert map_lines(source, _keep_indent_x) == "!!! note\n\n    term\n    : dd\n\n        X"


class TestMapLinesListItemColumn:
    def test_transforms_a_body_under_an_opener_in_an_indented_or_ordered_item(self) -> None:
        for item in ["  - item", " 1. item", "   - item", "10. item"]:
            source = f"{item}\n\n    !!! note\n\n        hit"

            assert map_lines(source, _keep_indent_x) == f"{item}\n\n    !!! note\n\n        X", item

    def test_transforms_a_body_under_an_opener_in_a_two_column_nested_item(self) -> None:
        source = "- a\n  - b\n\n    !!! note\n\n        hit"

        assert map_lines(source, _keep_indent_x) == "- a\n  - b\n\n    !!! note\n\n        X"

    def test_skips_a_body_under_an_opener_off_the_content_column_of_a_nested_item(self) -> None:
        source = "- a\n  - b\n\n      !!! note\n\n          hit"

        assert map_lines(source, _keep_indent_x) == source


class TestMapLinesDeepNesting:
    def test_scans_deeply_nested_openers_in_bounded_time(self) -> None:
        depth = 40
        source = "\n\n".join("    " * level + "!!! note" for level in range(depth))
        source += "\n\n" + "    " * depth + "hit"

        started = time.perf_counter()
        result = map_lines(source, _keep_indent_x)
        elapsed = time.perf_counter() - started

        assert result.endswith("    " * depth + "X")
        # A scan whose cost doubles per nesting level would not finish; this bound is generous for a linear one
        assert elapsed < 5


class TestMapLinesUnicodeDigitListItem:
    def test_transforms_a_directive_under_an_ordered_item_with_a_non_ascii_digit(self) -> None:
        for item in ["１. item", "٣. item", "١٠) item"]:
            source = f"{item}\n\n    hit"

            assert map_lines(source, _keep_indent_x) == f"{item}\n\n    X", item
