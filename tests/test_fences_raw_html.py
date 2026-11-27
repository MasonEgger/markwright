# ABOUTME: Tests for markwright._fences.raw_html_blocks and map_raw_html_blocks, the reader of raw HTML blocks.
# Exempt from the public-API-only rule: the _fences scanner has a contract of its own and is tested directly.

from __future__ import annotations

from markwright._fences import map_raw_html_blocks, raw_html_blocks


def _blocks(source: str) -> list[tuple[int, int]]:
    return raw_html_blocks(source.split("\n"))


class TestRawHtmlBlocks:
    def test_a_div_runs_from_its_opening_line_to_its_closing_line(self) -> None:
        assert _blocks("before\n<div>\nline\n</div>\nafter") == [(1, 3)]

    def test_a_blank_line_inside_the_div_does_not_end_the_block(self) -> None:
        assert _blocks("<div>\none\n\ntwo\n</div>\nafter") == [(0, 4)]

    def test_nested_divs_close_at_the_outer_close_tag(self) -> None:
        assert _blocks('<div class="a">\n<div>\nx\n</div>\ny\n</div>\nafter') == [(0, 5)]

    def test_a_block_may_open_a_few_columns_in(self) -> None:
        assert _blocks("  <div>\nx\n</div>") == [(0, 2)]

    def test_two_blocks_are_listed_separately(self) -> None:
        assert _blocks("<div>\na\n</div>\n\n<table>\n<tr><td>b</td></tr>\n</table>") == [(0, 2), (4, 6)]

    def test_a_single_line_block_is_a_block(self) -> None:
        assert _blocks("<p>one</p>\nprose") == [(0, 0)]

    def test_an_inline_tag_does_not_open_a_block(self) -> None:
        assert _blocks("<span>\nx\n</span>") == []

    def test_a_block_tag_inside_a_paragraph_line_does_not_open_a_block(self) -> None:
        assert _blocks("text <div>\nx\n</div>") == []

    def test_a_block_tag_indented_four_columns_does_not_open_a_block(self) -> None:
        assert _blocks("    <div>\nx\n</div>") == []

    def test_an_unclosed_block_runs_to_the_end_of_the_document(self) -> None:
        assert _blocks("<div>\nx\ny") == [(0, 2)]

    def test_a_close_tag_with_no_open_tag_is_not_a_block(self) -> None:
        assert _blocks("x\n</div>\ny") == []

    def test_a_self_closing_block_tag_is_not_a_block(self) -> None:
        assert _blocks('<hr>\n<div class="x"/>\ntext') == []

    def test_a_second_block_opening_on_the_closing_line_extends_the_first(self) -> None:
        assert _blocks("<div>\na\n</div><div>\nb\n</div>\nafter") == [(0, 4)]

    def test_a_close_tag_pops_an_unclosed_inner_tag(self) -> None:
        assert _blocks("<div>\n<br>\nx\n</div>\nafter") == [(0, 3)]

    def test_a_stray_close_tag_inside_the_block_does_not_end_it(self) -> None:
        assert _blocks("<div>\n</span>\nx\n</div>\nafter") == [(0, 3)]

    def test_a_tag_inside_a_comment_inside_the_block_is_not_read(self) -> None:
        assert _blocks("<div>\n<!-- </div> -->\nx\n</div>\nafter") == [(0, 3)]

    def test_a_fenced_block_is_not_a_raw_block(self) -> None:
        assert _blocks("```html\n<div>\nx\n</div>\n```") == []

    def test_indented_code_is_not_a_raw_block(self) -> None:
        assert _blocks("para\n\n    <div>\n    x\n    </div>") == []

    def test_a_verbatim_block_is_not_a_raw_block(self) -> None:
        assert _blocks("<pre>\n<div>\n</div>\n</pre>\n<script>\n<div>\n</script>") == []

    def test_a_multi_line_comment_is_not_a_raw_block(self) -> None:
        assert _blocks("<!--\n<div>\n</div>\n-->") == []


class TestMapRawHtmlBlocks:
    def test_the_transform_sees_only_the_block_lines(self) -> None:
        lines = ["out x", "<div>", "in x", "</div>", "out x"]

        result = map_raw_html_blocks(lines, lambda block: block.replace("x", "Y"))

        assert result == ["out x", "<div>", "in Y", "</div>", "out x"]

    def test_a_document_with_no_block_is_returned_unchanged(self) -> None:
        lines = ["plain x"]

        assert map_raw_html_blocks(lines, lambda block: block.upper()) == lines
