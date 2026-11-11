# ABOUTME: Tests for the grid extension turning a [grid], [grid cards], or [grid N] line into classes on the next list.
# Covers the source stage, the HTML stage, fail-soft marker skips, and the in-process render.

from __future__ import annotations

import markdown

from markwright.grid import apply_html, expand_source

GRID_MARKER = '<!-- mw-grid:{"version": 1} -->'
CARDS_MARKER = '<!-- mw-grid:{"version": 1, "cards": true} -->'
COLS_MARKER = '<!-- mw-grid:{"version": 1, "columns": 3} -->'
CARDS_COLS_MARKER = '<!-- mw-grid:{"version": 1, "cards": true, "columns": 2} -->'
LIST_HTML = "<ul>\n<li>a</li>\n<li>b</li>\n</ul>"


def render_grid(source: str) -> str:
    """Render source with the grid extension loaded."""
    return markdown.Markdown(extensions=["markwright.grid"]).convert(source)


class TestExpandSource:
    def test_cards_line_becomes_marker_and_blank_line(self) -> None:
        assert expand_source("[grid cards]\n- a\n- b") == CARDS_MARKER + "\n\n- a\n- b"

    def test_plain_grid_line_becomes_marker_and_blank_line(self) -> None:
        assert expand_source("[grid]\n\n- a") == GRID_MARKER + "\n\n\n- a"

    def test_indent_is_preserved(self) -> None:
        result = expand_source("- item\n\n    [grid cards]\n    - a")
        assert result == f"- item\n\n    {CARDS_MARKER}\n\n    - a"

    def test_inline_mention_is_unchanged(self) -> None:
        source = "Use [grid cards] in prose."
        assert expand_source(source) == source

    def test_unknown_variant_is_unchanged(self) -> None:
        source = "[grid tiles]\n- a"
        assert expand_source(source) == source

    def test_column_count_becomes_marker_and_blank_line(self) -> None:
        assert expand_source("[grid 3]\n- a") == COLS_MARKER + "\n\n- a"

    def test_cards_and_count_becomes_marker(self) -> None:
        assert expand_source("[grid cards 2]\n- a") == CARDS_COLS_MARKER + "\n\n- a"

    def test_count_out_of_range_is_unchanged(self) -> None:
        for source in ("[grid 7]\n- a", "[grid 0]\n- a", "[grid foo]\n- a"):
            assert expand_source(source) == source

    def test_non_ascii_digit_count_is_unchanged(self) -> None:
        # str.isdigit() is True for these yet int() rejects the superscript and
        # misreads the Arabic-Indic digit, so the count must be ASCII digits only.
        for source in ("[grid ³]\n- a", "[grid ٣]\n- a"):
            assert expand_source(source) == source

    def test_count_bounds_are_markers(self) -> None:
        assert expand_source("[grid 1]\n- a") == '<!-- mw-grid:{"version": 1, "columns": 1} -->\n\n- a'
        assert expand_source("[grid 6]\n- a") == '<!-- mw-grid:{"version": 1, "columns": 6} -->\n\n- a'

    def test_repeated_token_is_unchanged(self) -> None:
        for source in ("[grid cards cards]\n- a", "[grid 2 3]\n- a"):
            assert expand_source(source) == source

    def test_cards_line_inside_a_fence_is_unchanged(self) -> None:
        source = "```\n[grid cards]\n- a\n```"
        assert expand_source(source) == source

    def test_plain_grid_line_inside_a_fence_is_unchanged(self) -> None:
        source = "```\n[grid]\n- a\n```"
        assert expand_source(source) == source


class TestApplyHtml:
    def test_cards_marker_classes_the_next_list(self) -> None:
        result = apply_html(CARDS_MARKER + "\n" + LIST_HTML)
        assert result == '\n<ul class="mw-grid mw-grid-cards">\n<li>a</li>\n<li>b</li>\n</ul>'
        assert "mw-cards" not in result.replace("mw-grid-cards", "")

    def test_plain_marker_adds_only_the_grid_class(self) -> None:
        result = apply_html(GRID_MARKER + "\n" + LIST_HTML)
        assert result == '\n<ul class="mw-grid">\n<li>a</li>\n<li>b</li>\n</ul>'

    def test_columns_marker_adds_the_cols_class(self) -> None:
        result = apply_html(COLS_MARKER + "\n" + LIST_HTML)
        assert result == '\n<ul class="mw-grid mw-grid-cols-3">\n<li>a</li>\n<li>b</li>\n</ul>'

    def test_cards_and_columns_marker_adds_both_classes(self) -> None:
        result = apply_html(CARDS_COLS_MARKER + "\n" + LIST_HTML)
        assert result == '\n<ul class="mw-grid mw-grid-cards mw-grid-cols-2">\n<li>a</li>\n<li>b</li>\n</ul>'

    def test_existing_classes_follow_the_added_ones(self) -> None:
        result = apply_html(GRID_MARKER + '\n<ol class="steps">\n<li>a</li>\n</ol>')
        assert '<ol class="mw-grid steps">' in result

    def test_each_marker_styles_only_its_own_list(self) -> None:
        html_page = f"{CARDS_MARKER}\n{LIST_HTML}\n{LIST_HTML}\n{GRID_MARKER}\n{LIST_HTML}"
        result = apply_html(html_page)
        assert result.count('class="mw-grid mw-grid-cards"') == 1
        assert result.count('class="mw-grid"') == 1
        assert result.count("<ul>") == 1

    def test_running_twice_is_stable(self) -> None:
        once = apply_html(CARDS_MARKER + "\n" + LIST_HTML)
        assert apply_html(once) == once

    def test_page_without_markers_is_unchanged(self) -> None:
        assert apply_html(LIST_HTML) == LIST_HTML


class TestSkippedMarkers:
    def test_no_following_list_is_skipped_and_reported(self) -> None:
        skip_reasons: list[str] = []
        result = apply_html(CARDS_MARKER + "\n<p>text</p>", skip_reasons)
        assert result == "\n<p>text</p>"
        assert skip_reasons == ["Skipping mw-grid marker with no following list"]

    def test_malformed_marker_is_skipped_and_reported(self) -> None:
        skip_reasons: list[str] = []
        result = apply_html("<!-- mw-grid:{nope -->\n" + LIST_HTML, skip_reasons)
        assert result == "\n" + LIST_HTML
        assert skip_reasons == ["Skipping malformed mw-grid marker: '{nope'"]

    def test_unsupported_version_is_skipped_and_reported(self) -> None:
        skip_reasons: list[str] = []
        apply_html('<!-- mw-grid:{"version": 2} -->\n' + LIST_HTML, skip_reasons)
        assert skip_reasons == ["Skipping mw-grid marker with unsupported version 2"]

    def test_wrongly_typed_field_is_skipped_and_reported(self) -> None:
        skip_reasons: list[str] = []
        result = apply_html('<!-- mw-grid:{"version": 1, "cards": "yes"} -->\n' + LIST_HTML, skip_reasons)
        assert result == "\n" + LIST_HTML
        expected = 'Skipping mw-grid marker with invalid fields (cards): \'{"version": 1, "cards": "yes"}\''
        assert skip_reasons == [expected]

    def test_columns_out_of_range_is_skipped_and_reported(self) -> None:
        skip_reasons: list[str] = []
        result = apply_html('<!-- mw-grid:{"version": 1, "columns": 7} -->\n' + LIST_HTML, skip_reasons)
        assert result == "\n" + LIST_HTML
        expected = 'Skipping mw-grid marker with invalid fields (columns): \'{"version": 1, "columns": 7}\''
        assert skip_reasons == [expected]

    def test_non_integer_columns_is_skipped_and_reported(self) -> None:
        skip_reasons: list[str] = []
        result = apply_html('<!-- mw-grid:{"version": 1, "columns": "3"} -->\n' + LIST_HTML, skip_reasons)
        assert result == "\n" + LIST_HTML
        expected = 'Skipping mw-grid marker with invalid fields (columns): \'{"version": 1, "columns": "3"}\''
        assert skip_reasons == [expected]


class TestInProcess:
    def test_cards_list_is_classed(self) -> None:
        result = render_grid("[grid cards]\n\n- a\n- b")
        assert result == '<ul class="mw-grid mw-grid-cards">\n<li>a</li>\n<li>b</li>\n</ul>'

    def test_columns_list_is_classed(self) -> None:
        result = render_grid("[grid 3]\n\n- a\n- b")
        assert result == '<ul class="mw-grid mw-grid-cols-3">\n<li>a</li>\n<li>b</li>\n</ul>'

    def test_token_order_is_free(self) -> None:
        classed = '<ul class="mw-grid mw-grid-cards mw-grid-cols-2">\n<li>a</li>\n<li>b</li>\n</ul>'
        assert render_grid("[grid cards 2]\n\n- a\n- b") == classed
        assert render_grid("[grid 2 cards]\n\n- a\n- b") == classed

    def test_out_of_range_count_stays_literal(self) -> None:
        result = render_grid("[grid 7]\n\n- a\n- b")
        assert "mw-grid" not in result
        assert "[grid 7]" in result

    def test_non_ascii_digit_count_stays_literal(self) -> None:
        result = render_grid("[grid ٣]\n\n- a\n- b")
        assert "mw-grid" not in result
        assert "[grid ٣]" in result

    def test_marker_without_a_list_is_consumed(self) -> None:
        assert render_grid("[grid]\n\ntext") == "<p>text</p>"


class TestAlongsideAnnotate:
    def test_cards_grid_and_annotate_do_not_interfere(self) -> None:
        md = markdown.Markdown(extensions=["markwright.grid", "markwright.annotate"])
        source = "[grid cards 3]\n\n- a\n- b\n\n[annotate]\n\nRun (1) now.\n\n1. first\n"
        result = md.convert(source)
        assert '<ul class="mw-grid mw-grid-cards mw-grid-cols-3">' in result
        assert '<a class="mw-annotation" href="#mw-annotation-1-1">1</a>' in result
        assert "mw-cards" not in result.replace("mw-grid-cards", "")


class TestInProcessSkipsIndentedCode:
    def test_indented_code_block_stays_literal(self) -> None:
        result = render_grid("para\n\n    [grid]\n\n- a\n")
        assert "mw-grid" not in result
        assert "<ul>" in result
        assert "<pre><code>[grid]" in result

    def test_directive_under_a_list_item_still_expands(self) -> None:
        assert '<ul class="mw-grid">' in render_grid("- item\n\n    [grid]\n\n    - a\n")
