# ABOUTME: Tests for the grid extension turning a [grid] or [grid cards] line into classes on the next list.
# Covers the source stage, the HTML stage, fail-soft marker skips, and the in-process render.

import markdown

from markwright.grid import apply_html, expand_source

GRID_MARKER = '<!-- mw-grid:{"version": 1} -->'
CARDS_MARKER = '<!-- mw-grid:{"version": 1, "cards": true} -->'
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


class TestApplyHtml:
    def test_cards_marker_classes_the_next_list(self) -> None:
        result = apply_html(CARDS_MARKER + "\n" + LIST_HTML)
        assert result == '\n<ul class="mw-grid mw-cards">\n<li>a</li>\n<li>b</li>\n</ul>'

    def test_plain_marker_adds_only_the_grid_class(self) -> None:
        result = apply_html(GRID_MARKER + "\n" + LIST_HTML)
        assert result == '\n<ul class="mw-grid">\n<li>a</li>\n<li>b</li>\n</ul>'

    def test_existing_classes_follow_the_added_ones(self) -> None:
        result = apply_html(GRID_MARKER + '\n<ol class="steps">\n<li>a</li>\n</ol>')
        assert '<ol class="mw-grid steps">' in result

    def test_each_marker_styles_only_its_own_list(self) -> None:
        html_page = f"{CARDS_MARKER}\n{LIST_HTML}\n{LIST_HTML}\n{GRID_MARKER}\n{LIST_HTML}"
        result = apply_html(html_page)
        assert result.count('class="mw-grid mw-cards"') == 1
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


class TestInProcess:
    def test_cards_list_is_classed(self) -> None:
        result = render_grid("[grid cards]\n\n- a\n- b")
        assert result == '<ul class="mw-grid mw-cards">\n<li>a</li>\n<li>b</li>\n</ul>'

    def test_marker_without_a_list_is_consumed(self) -> None:
        assert render_grid("[grid]\n\ntext") == "<p>text</p>"
