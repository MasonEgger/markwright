# ABOUTME: Tests for the tabs extension: paired [tab NAME]/[/tab] grouped into tabbed sets.
# Covers the source stage, the HTML stage, set numbering, name escaping, problem reports, and the in-process render.

from __future__ import annotations

import markdown

from markwright.tabs import apply_html, expand_source


def render_plain(source: str) -> str:
    """Render source through Python-Markdown with no markwright extensions."""
    return markdown.Markdown().convert(source)


def report_markers(source: str) -> list[str]:
    """Expand, render, and post-process source, collecting the --warn reports."""
    skip_reasons: list[str] = []
    apply_html(render_plain(expand_source(source)), skip_reasons)
    return skip_reasons


def render_tabs(source: str) -> str:
    """Render source with the tabs extension loaded."""
    return markdown.Markdown(extensions=["markwright.tabs"]).convert(source)


TAB_OPEN = '<!-- mw-tab:{"version": 1, "name": "Python", "first": true} -->'
TAB_OPEN_SECOND = '<!-- mw-tab:{"version": 1, "name": "Node.js 20", "first": false} -->'
TAB_END = '<!-- mw-tab-end:{"version": 1} -->'

SINGLE_SOURCE = "[tab Python]\n\n    print(1)\n\n[/tab]\n\n[tab Node.js 20]\n\npara\n\n[/tab]"


class TestExpandSource:
    def test_consecutive_tabs_emit_paired_markers_with_first_flags(self) -> None:
        result = expand_source(SINGLE_SOURCE)
        assert '<!-- mw-tab:{"version": 1, "name": "Python", "first": true} -->' in result
        assert '<!-- mw-tab:{"version": 1, "name": "Node.js 20", "first": false} -->' in result
        assert result.count(TAB_END) == 2
        assert "[tab Python]" not in result
        assert "[/tab]" not in result

    def test_tabs_split_by_prose_each_start_a_set(self) -> None:
        result = expand_source("[tab A]\n\nx\n\n[/tab]\n\nprose\n\n[tab B]\n\ny\n\n[/tab]")
        assert '"name": "A", "first": true' in result
        assert '"name": "B", "first": true' in result

    def test_a_single_tab_starts_a_set(self) -> None:
        result = expand_source("[tab Only]\n\nx\n\n[/tab]")
        assert '"name": "Only", "first": true' in result

    def test_empty_tab_is_left_literal_with_no_set(self) -> None:
        # [tab ] is not an opener, so no tab marker is emitted and no set forms; the literal text
        # survives. The trailing [/tab] is a stray closer and is reported, but its text stays too.
        result = render_tabs("[tab ]\n\nx\n\n[/tab]")
        assert "tabbed-set" not in result
        assert "[tab ]" in result
        assert "[/tab]" in result

    def test_name_keeps_its_markdown_characters_verbatim(self) -> None:
        result = expand_source("[tab C *star*]\n\nx\n\n[/tab]")
        assert '"name": "C *star*"' in result

    def test_a_tab_opener_inside_a_fence_stays_literal(self) -> None:
        source = "```\n[tab A]\n\n[/tab]\n```"
        assert expand_source(source) == source

    def test_grid_containers_are_left_untouched(self) -> None:
        assert expand_source("[grid]\n\nx\n\n[/grid]") == "[grid]\n\nx\n\n[/grid]"
        assert "mw-tab-problem" not in expand_source("[/grid]")


class TestMarkerSourcedContainers:
    """Marker lines are a public contract. A pre stage that meets its own markers again (mw pre run
    twice, or hand-written markers) leaves them untouched instead of re-emitting or crashing."""

    def test_expand_is_idempotent(self) -> None:
        once = expand_source(SINGLE_SOURCE)
        assert expand_source(once) == once

    def test_a_hand_written_tab_marker_pair_passes_through(self) -> None:
        source = f"{TAB_OPEN}\n\ncontent\n\n{TAB_END}"
        assert expand_source(source) == source

    def test_a_marker_sourced_tab_pair_gets_no_problem_marker(self) -> None:
        source = f"{TAB_OPEN}\n\ncontent\n\n{TAB_END}"
        assert "mw-tab-problem" not in expand_source(source)

    def test_a_lone_marker_tab_end_gets_no_problem_marker(self) -> None:
        source = f"text\n\n{TAB_END}"
        assert expand_source(source) == source
        assert "mw-tab-problem" not in expand_source(source)

    def test_a_marker_sourced_set_survives_a_second_pre_and_renders_once(self) -> None:
        twice = expand_source(expand_source(SINGLE_SOURCE))
        result = apply_html(render_plain(twice))
        assert result.count("tabbed-set") == 1

    def test_a_mixed_directive_marker_tab_pair_does_not_crash(self) -> None:
        # A directive opener with a marker closer is malformed input; it stays fail-soft, no crash.
        source = f"[tab A]\n\ncontent\n\n{TAB_END}"
        result = apply_html(render_plain(expand_source(source)))
        assert "mw-tab" not in result


class TestApplyHtml:
    def test_single_set_builds_the_tabbed_markup(self) -> None:
        page = f"{TAB_OPEN}\n<pre><code>print(1)\n</code></pre>\n{TAB_END}\n{TAB_OPEN_SECOND}\n<p>para</p>\n{TAB_END}"
        result = apply_html(page)
        assert result == (
            '<div class="tabbed-set tabbed-alternate mw-tabs" data-tabs="1:2">\n'
            '<input checked="checked" type="radio" id="mw-tab-1-1" name="mw-tab-1" />\n'
            '<input type="radio" id="mw-tab-1-2" name="mw-tab-1" />\n'
            '<div class="tabbed-labels">\n'
            '<label for="mw-tab-1-1">Python</label>\n'
            '<label for="mw-tab-1-2">Node.js 20</label>\n'
            "</div>\n"
            '<div class="tabbed-content">\n'
            '<div class="tabbed-block">\n'
            "<pre><code>print(1)\n</code></pre>\n"
            "</div>\n"
            '<div class="tabbed-block">\n'
            "<p>para</p>\n"
            "</div>\n"
            "</div>\n"
            "</div>"
        )

    def test_single_tab_set_closes_every_wrapper(self) -> None:
        page = f'<!-- mw-tab:{{"version": 1, "name": "Solo", "first": true}} -->\n<p>x</p>\n{TAB_END}'
        result = apply_html(page)
        assert result == (
            '<div class="tabbed-set tabbed-alternate mw-tabs" data-tabs="1:1">\n'
            '<input checked="checked" type="radio" id="mw-tab-1-1" name="mw-tab-1" />\n'
            '<div class="tabbed-labels">\n'
            '<label for="mw-tab-1-1">Solo</label>\n'
            "</div>\n"
            '<div class="tabbed-content">\n'
            '<div class="tabbed-block">\n'
            "<p>x</p>\n"
            "</div>\n"
            "</div>\n"
            "</div>"
        )

    def test_two_sets_number_independently(self) -> None:
        first = '<!-- mw-tab:{"version": 1, "name": "A", "first": true} -->'
        second = '<!-- mw-tab:{"version": 1, "name": "B", "first": true} -->'
        page = f"{first}\n<p>x</p>\n{TAB_END}\n{second}\n<p>y</p>\n{TAB_END}"
        result = apply_html(page)
        assert 'data-tabs="1:1"' in result
        assert 'data-tabs="2:1"' in result
        assert 'id="mw-tab-1-1"' in result
        assert 'id="mw-tab-2-1"' in result

    def test_label_escapes_html_special_characters(self) -> None:
        marker = '<!-- mw-tab:{"version": 1, "name": "a \\u003cb\\u003e & \\"c\\"", "first": true} -->'
        page = f"{marker}\n<p>x</p>\n{TAB_END}"
        result = apply_html(page)
        assert "<label " in result
        assert "&lt;b&gt; &amp; &quot;c&quot;" in result
        assert "<b>" not in result

    def test_page_without_markers_is_unchanged(self) -> None:
        assert apply_html("<p>plain</p>") == "<p>plain</p>"

    def test_running_twice_is_stable(self) -> None:
        page = f"{TAB_OPEN}\n<p>x</p>\n{TAB_END}"
        once = apply_html(page)
        assert apply_html(once) == once


class TestSkippedMarkers:
    def test_malformed_payload_is_skipped_and_reported(self) -> None:
        skip_reasons: list[str] = []
        result = apply_html(f"<!-- mw-tab:{{nope -->\n<p>x</p>\n{TAB_END}", skip_reasons)
        assert "tabbed-set" not in result
        assert skip_reasons == ["Skipping malformed mw-tab marker: '{nope'"]

    def test_open_with_no_close_is_skipped_and_reported(self) -> None:
        skip_reasons: list[str] = []
        result = apply_html(f"{TAB_OPEN}\n<p>x</p>", skip_reasons)
        assert "tabbed-set" not in result
        assert skip_reasons == ["Skipping mw-tab marker with no matching mw-tab-end"]

    def test_close_with_no_open_is_skipped_and_reported(self) -> None:
        skip_reasons: list[str] = []
        result = apply_html(f"<p>x</p>\n{TAB_END}", skip_reasons)
        assert result == "<p>x</p>\n"
        assert skip_reasons == ["Skipping mw-tab-end marker with no matching mw-tab"]

    def test_first_false_with_no_preceding_tab_starts_a_set(self) -> None:
        marker = '<!-- mw-tab:{"version": 1, "name": "Lonely", "first": false} -->'
        result = apply_html(f"{marker}\n<p>x</p>\n{TAB_END}")
        assert 'data-tabs="1:1"' in result
        assert 'id="mw-tab-1-1"' in result

    def test_an_escaped_marker_inside_a_code_block_is_left_alone(self) -> None:
        # In real rendered HTML a marker inside code is escaped text, not a comment token.
        page = "<pre><code>&lt;!-- mw-tab:x --&gt;\nx\n</code></pre>"
        assert apply_html(page) == page

    def test_fail_soft_without_a_skip_reasons_list(self) -> None:
        assert "mw-tab-end" not in apply_html(f"<p>x</p>\n{TAB_END}")
        assert "mw-tab" not in apply_html(f"{TAB_OPEN}\n<p>x</p>")
        assert "mw-tab" not in apply_html(f"<!-- mw-tab:{{nope -->\n<p>x</p>\n{TAB_END}")


class TestProblems:
    def test_unclosed_tab_is_reported(self) -> None:
        assert report_markers("[tab One]\n\ntext") == ["Leaving [tab] on line 1 literal: unclosed, no matching closer"]

    def test_stray_tab_closer_is_reported(self) -> None:
        assert report_markers("text\n\n[/tab]") == ["Leaving [/tab] on line 3 literal: no matching opener"]

    def test_empty_tab_is_not_reported(self) -> None:
        assert report_markers("[tab ]\n\ntext") == []

    def test_a_problem_document_matches_the_tabs_free_render(self) -> None:
        source = "before\n[/tab]\n\n[tab X]\n\ninside"
        assert render_tabs(source) == render_plain(source)

    def test_the_problem_marker_never_survives_output(self) -> None:
        assert "mw-tab-problem" not in render_tabs("text\n\n[/tab]")
        assert "mw-tab-problem" not in apply_html(render_plain(expand_source("text\n\n[/tab]")))

    def test_malformed_problem_marker_is_skipped_and_reported(self) -> None:
        skip_reasons: list[str] = []
        result = apply_html("<p>x</p>\n<!-- mw-tab-problem:{nope -->", skip_reasons)
        assert "mw-tab-problem" not in result
        assert skip_reasons == ["Skipping malformed mw-tab-problem marker: '{nope'"]


class TestInProcess:
    def test_single_set_renders_a_tabbed_set(self) -> None:
        result = render_tabs("[tab Python]\n\ncode\n\n[/tab]\n\n[tab Shell]\n\nmore\n\n[/tab]")
        assert '<div class="tabbed-set tabbed-alternate mw-tabs" data-tabs="1:2">' in result
        assert '<label for="mw-tab-1-1">Python</label>' in result
        assert '<label for="mw-tab-1-2">Shell</label>' in result
        assert result.count('<div class="tabbed-block">') == 2

    def test_prose_between_tabs_starts_a_second_set(self) -> None:
        result = render_tabs("[tab A]\n\nx\n\n[/tab]\n\nbetween\n\n[tab B]\n\ny\n\n[/tab]")
        assert 'data-tabs="1:1"' in result
        assert 'data-tabs="2:1"' in result

    def test_empty_tab_stays_literal_in_process(self) -> None:
        result = render_tabs("[tab ]\n\ntext\n\n[/tab]")
        assert "tabbed-set" not in result
        assert "[tab ]" in result


class TestOrderIndependenceWithGrid:
    def _both_orders(self, source: str) -> tuple[str, str]:
        grid_first = markdown.Markdown(extensions=["markwright.grid", "markwright.tabs"]).convert(source)
        tabs_first = markdown.Markdown(extensions=["markwright.tabs", "markwright.grid"]).convert(source)
        return grid_first, tabs_first

    def test_crossed_grid_then_tab_is_order_independent(self) -> None:
        source = "[grid]\n\n[tab A]\n\n[/grid]\n\n[/tab]"
        grid_first, tabs_first = self._both_orders(source)
        assert grid_first == tabs_first
        # The skipped-over tab opener is unclosed and its closer stray: no tab set, no crossing.
        assert "tabbed-set" not in grid_first
        assert '<div class="mw-grid">' in grid_first

    def test_crossed_tab_then_grid_is_order_independent(self) -> None:
        # [/tab] pairs with [tab A] (bracket rule), so tab A closes and the grid is crossed: the
        # grid becomes an unclosed shortcut and its closer stray. A tab set forms; no grid div.
        source = "[tab A]\n\n[grid]\n\n[/tab]\n\n[/grid]"
        grid_first, tabs_first = self._both_orders(source)
        assert grid_first == tabs_first
        assert '<div class="tabbed-set' in grid_first
        assert '<div class="mw-grid">' not in grid_first

    def test_card_in_tab_in_grid_is_not_wrapped_in_either_order(self) -> None:
        source = "[grid]\n\n[tab A]\n\n[card]\n\ntext\n\n[/card]\n\n[/tab]\n\n[/grid]"
        grid_first, tabs_first = self._both_orders(source)
        assert grid_first == tabs_first
        assert "mw-card" not in grid_first
        assert '<div class="mw-grid">' in grid_first
        assert '<div class="tabbed-set' in grid_first

    def test_tab_in_card_in_grid_nests_in_both_orders(self) -> None:
        source = "[grid]\n\n[card]\n\n[tab A]\n\nx\n\n[/tab]\n\n[tab B]\n\ny\n\n[/tab]\n\n[/card]\n\n[/grid]"
        grid_first, tabs_first = self._both_orders(source)
        assert grid_first == tabs_first
        assert '<div class="mw-grid">' in grid_first
        assert '<div class="mw-card">' in grid_first
        assert '<div class="tabbed-set' in grid_first
