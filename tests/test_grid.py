# ABOUTME: Tests for the grid extension: the [grid ...] list shortcut and the paired [grid]/[/grid] and [card] blocks.
# Covers the source stage, the HTML stage, stack-matched wrapping, problem reports, and the in-process render.

from __future__ import annotations

import markdown

from markwright.grid import apply_html, expand_source


def render_plain(source: str) -> str:
    """Render source through Python-Markdown with no markwright extensions."""
    return markdown.Markdown().convert(source)


def report_markers(source: str) -> list[str]:
    """Expand, render, and post-process source, collecting the --warn reports."""
    skip_reasons: list[str] = []
    apply_html(render_plain(expand_source(source)), skip_reasons)
    return skip_reasons


GRID_MARKER = '<!-- mw-grid:{"version": 1} -->'
CARDS_MARKER = '<!-- mw-grid:{"version": 1, "cards": true} -->'
COLS_MARKER = '<!-- mw-grid:{"version": 1, "columns": 3} -->'
CARDS_COLS_MARKER = '<!-- mw-grid:{"version": 1, "cards": true, "columns": 2} -->'
LIST_HTML = "<ul>\n<li>a</li>\n<li>b</li>\n</ul>"

BLOCK_MARKER = '<!-- mw-grid-block:{"version": 1} -->'
BLOCK_COLS_MARKER = '<!-- mw-grid-block:{"version": 1, "columns": 2} -->'
BLOCK_COLS3_MARKER = '<!-- mw-grid-block:{"version": 1, "columns": 3} -->'
BLOCK_CARDS_MARKER = '<!-- mw-grid-block:{"version": 1, "cards": true} -->'
BLOCK_END_MARKER = '<!-- mw-grid-end:{"version": 1} -->'
CARD_MARKER = '<!-- mw-card:{"version": 1} -->'
CARD_END_MARKER = '<!-- mw-card-end:{"version": 1} -->'
CARD_OUTSIDE_PROBLEM = (
    '<!-- mw-grid-problem:{"version": 1, "line": 1, "directive": "[card]", "reason": "card-outside-grid"} -->'
)


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


class TestExpandSourceContainers:
    def test_block_grid_emits_paired_markers(self) -> None:
        result = expand_source("[grid]\n\n## A\n\ntext\n\n[/grid]")
        assert BLOCK_MARKER in result
        assert BLOCK_END_MARKER in result
        assert "[grid]" not in result
        assert "[/grid]" not in result
        assert "## A" in result
        assert "text" in result

    def test_block_grid_columns_emits_a_block_cols_marker(self) -> None:
        result = expand_source("[grid 2]\n\nx\n\n[/grid]")
        assert BLOCK_COLS_MARKER in result

    def test_block_grid_cards_emits_a_block_cards_marker(self) -> None:
        result = expand_source("[grid cards]\n\nx\n\n[/grid]")
        assert BLOCK_CARDS_MARKER in result

    def test_card_inside_a_grid_emits_card_markers(self) -> None:
        result = expand_source("[grid]\n\n[card]\n\n### Install\n\ntext\n\n[/card]\n\n[/grid]")
        assert CARD_MARKER in result
        assert CARD_END_MARKER in result
        assert BLOCK_MARKER in result
        assert "[card]" not in result
        assert "### Install" in result

    def test_top_level_card_stays_literal_with_a_problem_marker(self) -> None:
        result = expand_source("[card]\n\ntext\n\n[/card]")
        assert "[card]" in result
        assert "[/card]" in result
        assert CARD_MARKER not in result
        assert "mw-grid-problem" in result

    def test_card_not_directly_inside_a_grid_stays_literal(self) -> None:
        # The inner card's nearest enclosing container is the outer card, not the grid.
        source = "[grid]\n\n[card]\n\n[card]\n\ntext\n\n[/card]\n\n[/card]\n\n[/grid]"
        result = expand_source(source)
        assert result.count(CARD_MARKER) == 1
        assert "[card]" in result

    def test_invalid_block_grid_opener_stays_literal(self) -> None:
        source = "[grid 7]\n\nx\n\n[/grid]"
        assert expand_source(source) == source

    def test_container_opener_inside_a_fence_stays_literal(self) -> None:
        source = "```\n[grid]\n\n[/grid]\n```"
        assert expand_source(source) == source

    def test_shortcut_and_block_grid_coexist(self) -> None:
        result = expand_source("[grid cards 2]\n\n- a\n\n[grid]\n\nx\n\n[/grid]")
        assert CARDS_COLS_MARKER in result
        assert BLOCK_MARKER in result


class TestApplyHtmlContainers:
    def test_block_grid_wraps_content_in_a_div(self) -> None:
        result = apply_html(f"{BLOCK_MARKER}\n<h2>A</h2>\n<p>text</p>\n{BLOCK_END_MARKER}")
        assert result == '<div class="mw-grid">\n<h2>A</h2>\n<p>text</p>\n</div>'

    def test_block_grid_columns_class(self) -> None:
        result = apply_html(f"{BLOCK_COLS_MARKER}\n<p>x</p>\n{BLOCK_END_MARKER}")
        assert result == '<div class="mw-grid mw-grid-cols-2">\n<p>x</p>\n</div>'

    def test_block_grid_cards_class(self) -> None:
        result = apply_html(f"{BLOCK_CARDS_MARKER}\n<p>x</p>\n{BLOCK_END_MARKER}")
        assert result == '<div class="mw-grid mw-grid-cards">\n<p>x</p>\n</div>'

    def test_card_wraps_content_in_a_card_div(self) -> None:
        result = apply_html(f"{CARD_MARKER}\n<h3>Install</h3>\n<p>text</p>\n{CARD_END_MARKER}")
        assert result == '<div class="mw-card">\n<h3>Install</h3>\n<p>text</p>\n</div>'

    def test_nested_grid_card_grid_wraps_in_order_and_closes_in_reverse(self) -> None:
        page = (
            f"{BLOCK_MARKER}\n"
            f"{CARD_MARKER}\n"
            f"{BLOCK_COLS3_MARKER}\n"
            "<ul>\n<li>a</li>\n</ul>\n"
            f"{BLOCK_END_MARKER}\n"
            f"{CARD_END_MARKER}\n"
            f"{BLOCK_END_MARKER}"
        )
        result = apply_html(page)
        assert result == (
            '<div class="mw-grid">\n'
            '<div class="mw-card">\n'
            '<div class="mw-grid mw-grid-cols-3">\n'
            "<ul>\n<li>a</li>\n</ul>\n"
            "</div>\n"
            "</div>\n"
            "</div>"
        )

    def test_a_fenced_code_block_is_a_sibling_inside_the_grid(self) -> None:
        page = (
            f"{BLOCK_MARKER}\n{CARD_MARKER}\n<p>text</p>\n{CARD_END_MARKER}\n"
            f"<pre><code>x</code></pre>\n{BLOCK_END_MARKER}"
        )
        result = apply_html(page)
        assert result == (
            '<div class="mw-grid">\n<div class="mw-card">\n<p>text</p>\n</div>\n<pre><code>x</code></pre>\n</div>'
        )

    def test_running_twice_is_stable(self) -> None:
        once = apply_html(f"{BLOCK_MARKER}\n<p>x</p>\n{BLOCK_END_MARKER}")
        assert apply_html(once) == once

    def test_page_without_container_markers_is_unchanged(self) -> None:
        assert apply_html("<p>plain</p>") == "<p>plain</p>"


class TestSkippedContainerMarkers:
    def test_malformed_block_payload_is_skipped_and_reported(self) -> None:
        skip_reasons: list[str] = []
        result = apply_html(f"<!-- mw-grid-block:{{nope -->\n<p>x</p>\n{BLOCK_END_MARKER}", skip_reasons)
        assert "<div" not in result
        assert skip_reasons == ["Skipping malformed mw-grid-block marker: '{nope'"]

    def test_close_marker_with_no_open_is_skipped_and_reported(self) -> None:
        skip_reasons: list[str] = []
        result = apply_html(f"<p>x</p>\n{BLOCK_END_MARKER}", skip_reasons)
        assert result == "<p>x</p>\n"
        assert skip_reasons == ["Skipping mw-grid-end marker with no matching mw-grid-block"]

    def test_open_marker_with_no_close_is_skipped_and_reported(self) -> None:
        skip_reasons: list[str] = []
        result = apply_html(f"{BLOCK_MARKER}\n<p>x</p>", skip_reasons)
        assert result == "\n<p>x</p>"
        assert skip_reasons == ["Skipping mw-grid-block marker with no matching mw-grid-end"]

    def test_card_open_with_no_close_is_skipped_and_reported(self) -> None:
        skip_reasons: list[str] = []
        apply_html(f"{CARD_MARKER}\n<p>x</p>", skip_reasons)
        assert skip_reasons == ["Skipping mw-card marker with no matching mw-card-end"]

    def test_fail_soft_without_a_skip_reasons_list(self) -> None:
        # The in-process path passes no skip_reasons; hostile markers must still not raise, and
        # every recognized marker comment is removed.
        assert "mw-grid-end" not in apply_html(f"<p>x</p>\n{BLOCK_END_MARKER}")
        assert "mw-grid-block" not in apply_html(f"{BLOCK_MARKER}\n<p>x</p>")
        assert "mw-grid-block" not in apply_html(f"<!-- mw-grid-block:{{nope -->\n<p>x</p>\n{BLOCK_END_MARKER}")


class TestInProcessContainers:
    def test_block_grid_renders_a_div(self) -> None:
        result = render_grid("[grid]\n\n## A\n\ntext\n\n[/grid]")
        assert '<div class="mw-grid">' in result
        assert "<h2>A</h2>" in result
        assert result.index('<div class="mw-grid">') < result.index("<h2>A</h2>") < result.index("</div>")

    def test_block_grid_columns_renders_the_cols_class(self) -> None:
        assert '<div class="mw-grid mw-grid-cols-2">' in render_grid("[grid 2]\n\ntext\n\n[/grid]")

    def test_card_inside_a_grid_renders_nested_divs(self) -> None:
        result = render_grid("[grid]\n\n[card]\n\n### Install\n\n[/card]\n\n[/grid]")
        assert '<div class="mw-grid">' in result
        assert '<div class="mw-card">' in result
        assert result.index('<div class="mw-grid">') < result.index('<div class="mw-card">')

    def test_top_level_card_stays_literal_in_process(self) -> None:
        result = render_grid("[card]\n\ntext\n\n[/card]")
        assert "mw-card" not in result
        assert "[card]" in result


class TestContainersIntegration:
    def test_shortcut_block_and_annotate_together(self) -> None:
        md = markdown.Markdown(extensions=["markwright.grid", "markwright.annotate"])
        source = (
            "[grid cards 2]\n\n- a\n- b\n\n"
            "[grid]\n\n[card]\n\n## One\n\n[/card]\n\n[card]\n\n## Two\n\n[/card]\n\n[/grid]\n\n"
            "[annotate]\n\nRun (1) now.\n\n1. first\n"
        )
        result = md.convert(source)
        assert '<ul class="mw-grid mw-grid-cards mw-grid-cols-2">' in result
        assert '<div class="mw-grid">' in result
        assert result.count('<div class="mw-card">') == 2
        assert '<a class="mw-annotation" href="#mw-annotation-1-1">1</a>' in result


class TestContainerProblems:
    def test_card_outside_grid_is_reported_by_apply_html(self) -> None:
        skip_reasons: list[str] = []
        result = apply_html(f"<p>[card]{CARD_OUTSIDE_PROBLEM}</p>", skip_reasons)
        assert result == "<p>[card]</p>"
        assert skip_reasons == ["Leaving [card] on line 1 literal: a card must be directly inside a block grid"]

    def test_top_level_card_pair_reports_once_and_stays_literal(self) -> None:
        source = "[card]\n\ntext\n\n[/card]"
        skip_reasons: list[str] = []
        result = apply_html(render_plain(expand_source(source)), skip_reasons)
        assert "mw-card" not in result
        assert "mw-grid-problem" not in result
        assert "[card]" in result
        assert "[/card]" in result
        assert skip_reasons == ["Leaving [card] on line 1 literal: a card must be directly inside a block grid"]

    def test_unclosed_card_inside_a_grid_is_reported(self) -> None:
        source = "[grid]\n\n[card]\n\ntext\n\n[/grid]"
        skip_reasons: list[str] = []
        result = apply_html(render_plain(expand_source(source)), skip_reasons)
        assert '<div class="mw-grid">' in result
        assert '<div class="mw-card">' not in result
        assert skip_reasons == ["Leaving [card] on line 3 literal: unclosed, no matching closer"]

    def test_stray_card_closer_is_reported(self) -> None:
        assert report_markers("text\n\n[/card]") == ["Leaving [/card] on line 3 literal: no matching opener"]

    def test_stray_grid_closer_is_reported(self) -> None:
        assert report_markers("text\n\n[/grid]") == ["Leaving [/grid] on line 3 literal: no matching opener"]

    def test_a_problem_inside_a_paragraph_renders_unchanged(self) -> None:
        # Text on the line before, no blank line: the directive must stay in the same paragraph.
        source = "before text\n[/card]"
        assert render_grid(source) == render_plain(source)

    def test_a_problem_document_matches_the_grid_free_render(self) -> None:
        source = "before\n[/card]\n\n[card]\n\ninside\n\n[/card]\n\nafter"
        assert render_grid(source) == render_plain(source)

    def test_the_marker_never_survives_output(self) -> None:
        expanded = expand_source("text\n\n[/card]")
        assert "mw-grid-problem" not in apply_html(render_plain(expanded))
        assert "mw-grid-problem" not in apply_html(render_plain(expanded), [])

    def test_malformed_problem_marker_is_skipped_and_reported(self) -> None:
        skip_reasons: list[str] = []
        result = apply_html("<p>x</p>\n<!-- mw-grid-problem:{nope -->", skip_reasons)
        assert "mw-grid-problem" not in result
        assert skip_reasons == ["Skipping malformed mw-grid-problem marker: '{nope'"]

    def test_wrongly_typed_problem_marker_is_skipped(self) -> None:
        bad = '<!-- mw-grid-problem:{"version": 1, "line": 1, "directive": "[div]", "reason": "unclosed"} -->'
        skip_reasons: list[str] = []
        result = apply_html(f"<p>x{bad}</p>", skip_reasons)
        assert result == "<p>x</p>"
        assert len(skip_reasons) == 1
        assert skip_reasons[0].startswith("Skipping mw-grid-problem marker with invalid fields")

    def test_a_problem_directive_inside_a_fence_produces_no_marker(self) -> None:
        source = "```\n[/card]\n```"
        assert expand_source(source) == source

    def test_an_invalid_grid_opener_gets_no_problem_marker(self) -> None:
        source = "[grid 7]\n\nx\n\n[/grid]"
        expanded = expand_source(source)
        assert "mw-grid-problem" not in expanded
        assert expanded == source

    def test_in_process_problem_document_has_literal_text_and_no_comment(self) -> None:
        result = render_grid("before\n[/card]\n\n[card]\n\ntext\n\n[/card]")
        assert "mw-grid-problem" not in result
        assert "mw-card" not in result
        assert "[/card]" in result

    def test_running_twice_is_stable_on_a_problem_document(self) -> None:
        once = apply_html(render_plain(expand_source("text\n\n[/card]")))
        assert apply_html(once) == once

    def test_tab_containers_are_left_untouched(self) -> None:
        # Tabs belong to the tabs extension; grid emits nothing for a tab pair or a tab problem.
        assert expand_source("[tab x]\n\ntext\n\n[/tab]") == "[tab x]\n\ntext\n\n[/tab]"
        assert expand_source("[tab x]\n\ntext") == "[tab x]\n\ntext"
        assert "mw-grid-problem" not in expand_source("[/tab]")

    def test_malformed_problem_marker_without_a_skip_reasons_list(self) -> None:
        assert "mw-grid-problem" not in apply_html("<p>x</p>\n<!-- mw-grid-problem:{nope -->")


class TestMarkerSourcedContainers:
    """Marker lines are a public contract. A pre stage that meets its own markers again (mw pre run
    twice, or hand-written markers) leaves them untouched rather than re-emitting or re-reporting."""

    def test_double_expand_preserves_the_block_payload(self) -> None:
        # A second pre pass must not strip cards and columns back to a bare {"version": 1}.
        once = expand_source("[grid cards 2]\n\n- a\n- b\n\n[/grid]")
        assert BLOCK_END_MARKER in once
        assert '<!-- mw-grid-block:{"version": 1, "cards": true, "columns": 2} -->' in once
        assert expand_source(once) == once

    def test_a_hand_written_block_marker_pair_passes_through(self) -> None:
        source = f"{BLOCK_CARDS_MARKER}\n\n- a\n- b\n\n{BLOCK_END_MARKER}"
        assert expand_source(source) == source

    def test_a_hand_written_card_marker_pair_passes_through(self) -> None:
        source = f"{CARD_MARKER}\n\ntext\n\n{CARD_END_MARKER}"
        assert expand_source(source) == source

    def test_a_marker_sourced_card_outside_a_grid_gets_no_problem_marker(self) -> None:
        source = f"{CARD_MARKER}\n\ntext\n\n{CARD_END_MARKER}"
        assert "mw-grid-problem" not in expand_source(source)

    def test_a_lone_marker_grid_end_gets_no_problem_marker(self) -> None:
        source = f"text\n\n{BLOCK_END_MARKER}"
        assert expand_source(source) == source
        assert "mw-grid-problem" not in expand_source(source)

    def test_a_lone_marker_grid_block_is_not_turned_into_a_shortcut(self) -> None:
        source = f"text\n\n{BLOCK_MARKER}"
        assert expand_source(source) == source
        assert GRID_MARKER not in expand_source(source)

    def test_a_directive_card_inside_a_marker_grid_is_wrapped(self) -> None:
        source = f"{BLOCK_MARKER}\n\n[card]\n\ntext\n\n[/card]\n\n{BLOCK_END_MARKER}"
        expanded = expand_source(source)
        assert CARD_MARKER in expanded
        assert "[card]" not in expanded
        result = apply_html(render_plain(expanded))
        assert '<div class="mw-grid">' in result
        assert '<div class="mw-card">' in result

    def test_a_marker_sourced_pair_reports_once_and_renders_once(self) -> None:
        # A hand-written block grid run through pre twice stays a single wrapped grid.
        twice = expand_source(expand_source(f"{BLOCK_CARDS_MARKER}\n\n- a\n- b\n\n{BLOCK_END_MARKER}"))
        result = apply_html(render_plain(twice))
        assert result.count('<div class="mw-grid mw-grid-cards">') == 1
