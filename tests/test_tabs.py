# ABOUTME: Tests for the tabs extension: paired [tab NAME]/[/tab] grouped into tabbed sets.
# Covers the source stage, the HTML stage, set numbering, name escaping, problem reports, and the in-process render.

from __future__ import annotations

import warnings

import markdown
import pytest

from markwright import Diagnostic, RenderWarning
from markwright.tabs import apply_html, expand_source


def messages(diagnostics: list[Diagnostic]) -> list[str]:
    """Return the --warn message of each diagnostic."""
    return [diagnostic.message for diagnostic in diagnostics]


def render_plain(source: str) -> str:
    """Render source through Python-Markdown with no markwright extensions."""
    return markdown.Markdown().convert(source)


def report_markers(source: str) -> list[str]:
    """Expand, render, and post-process source, collecting the --warn reports."""
    diagnostics: list[Diagnostic] = []
    apply_html(render_plain(expand_source(source)), diagnostics)
    return messages(diagnostics)


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
        diagnostics: list[Diagnostic] = []
        result = apply_html(f"<!-- mw-tab:{{nope -->\n<p>x</p>\n{TAB_END}", diagnostics)
        assert "tabbed-set" not in result
        assert messages(diagnostics) == ["Skipping malformed mw-tab marker: '{nope'"]

    def test_open_with_no_close_is_skipped_and_reported(self) -> None:
        diagnostics: list[Diagnostic] = []
        result = apply_html(f"{TAB_OPEN}\n<p>x</p>", diagnostics)
        assert "tabbed-set" not in result
        assert messages(diagnostics) == ["Skipping mw-tab marker with no matching mw-tab-end"]

    def test_close_with_no_open_is_skipped_and_reported(self) -> None:
        diagnostics: list[Diagnostic] = []
        result = apply_html(f"<p>x</p>\n{TAB_END}", diagnostics)
        assert result == "<p>x</p>\n"
        assert messages(diagnostics) == ["Skipping mw-tab-end marker with no matching mw-tab"]

    def test_first_false_with_no_preceding_tab_starts_a_set(self) -> None:
        marker = '<!-- mw-tab:{"version": 1, "name": "Lonely", "first": false} -->'
        result = apply_html(f"{marker}\n<p>x</p>\n{TAB_END}")
        assert 'data-tabs="1:1"' in result
        assert 'id="mw-tab-1-1"' in result

    def test_an_escaped_marker_inside_a_code_block_is_left_alone(self) -> None:
        # In real rendered HTML a marker inside code is escaped text, not a comment token.
        page = "<pre><code>&lt;!-- mw-tab:x --&gt;\nx\n</code></pre>"
        assert apply_html(page) == page

    def test_fail_soft_without_a_diagnostics_list(self) -> None:
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
        diagnostics: list[Diagnostic] = []
        result = apply_html("<p>x</p>\n<!-- mw-tab-problem:{nope -->", diagnostics)
        assert "mw-tab-problem" not in result
        assert messages(diagnostics) == ["Skipping malformed mw-tab-problem marker: '{nope'"]


class TestSiblingRule:
    def test_a_tab_nested_in_a_tab_starts_its_own_set(self) -> None:
        source = "[tab A]\n\n[tab B]\n\nb\n\n[/tab]\n\n[/tab]"
        result = apply_html(render_plain(expand_source(source)))
        assert result.count("tabbed-set tabbed-alternate") == 2
        assert result.count('data-tabs="1:1"') == 1
        assert result.count('data-tabs="2:1"') == 1

    def test_nested_set_tabs_and_the_parent_sibling_keep_their_own_sets(self) -> None:
        source = "[tab A]\n\n[tab B]\n\nb\n\n[/tab]\n\n[tab C]\n\nc\n\n[/tab]\n\n[/tab]\n\n[tab D]\n\nd\n\n[/tab]"
        result = apply_html(render_plain(expand_source(source)))
        assert '<label for="mw-tab-1-1">A</label>' in result
        assert '<label for="mw-tab-1-2">D</label>' in result
        assert '<label for="mw-tab-2-1">B</label>' in result
        assert '<label for="mw-tab-2-2">C</label>' in result

    def test_a_tab_inside_a_grid_and_a_card_in_a_tab_starts_its_own_set(self) -> None:
        source = "[tab A]\n\n[grid]\n\n[card]\n\n[tab B]\n\nb\n\n[/tab]\n\n[/card]\n\n[/grid]\n\n[/tab]"
        result = markdown.Markdown(extensions=["markwright.grid", "markwright.tabs"]).convert(source)
        assert 'data-tabs="1:1"' in result
        assert 'data-tabs="2:1"' in result
        assert result.index('for="mw-tab-1-1">A<') < result.index('for="mw-tab-2-1">B<')

    def test_a_tab_ending_a_list_item_does_not_join_a_top_level_tab(self) -> None:
        source = "- item\n\n    [tab A]\n\n    a\n\n    [/tab]\n\n[tab B]\n\nb\n\n[/tab]"
        assert '"name": "B", "first": true' in expand_source(source)
        result = apply_html(render_plain(expand_source(source)))
        assert 'data-tabs="1:1"' in result
        assert 'data-tabs="2:1"' in result

    def test_a_sibling_after_blank_lines_still_joins_the_set(self) -> None:
        source = "[tab A]\n\na\n\n[/tab]\n\n\n[tab B]\n\nb\n\n[/tab]"
        assert apply_html(render_plain(expand_source(source))).count('data-tabs="1:2"') == 1


class TestSetNumbering:
    def test_an_enclosing_set_has_a_lower_number_than_a_set_nested_in_its_first_tab(self) -> None:
        source = "[tab A]\n\n[tab B]\n\nb\n\n[/tab]\n\n[/tab]"
        result = apply_html(render_plain(expand_source(source)))
        assert '<label for="mw-tab-1-1">A</label>' in result
        assert '<label for="mw-tab-2-1">B</label>' in result
        assert '<input checked="checked" type="radio" id="mw-tab-2-1" name="mw-tab-2" />' in result


class TestBacktickName:
    SOURCE = "[tab `x`]\n\nbody\n\n[/tab]"

    def test_the_in_process_render_shows_the_backticks_as_text(self) -> None:
        result = render_tabs(self.SOURCE)
        assert "<code>" not in result
        assert '<label for="mw-tab-1-1">`x`</label>' in result

    def test_the_pipeline_matches_the_in_process_render(self) -> None:
        assert apply_html(render_plain(expand_source(self.SOURCE))) == render_tabs(self.SOURCE)


class TestBacktickNameWhenIndented:
    SOURCE = "- item\n\n    [tab `x`]\n\n    body\n\n    [/tab]"

    def test_a_backticked_name_stays_text_in_a_four_space_list_item_in_process(self) -> None:
        result = render_tabs(self.SOURCE)
        assert "<code>" not in result
        assert "`x`" in result

    def test_the_pipeline_matches_the_in_process_render(self) -> None:
        assert apply_html(render_plain(expand_source(self.SOURCE))) == render_tabs(self.SOURCE)


class TestRawHtmlBlock:
    def test_a_tab_line_inside_a_raw_html_block_is_expanded_in_process_as_in_the_pipeline(self) -> None:
        source = "<div>\n[tab A]\n\nx\n\n[/tab]\n</div>"
        result = render_tabs(source)
        assert '<label for="mw-tab-1-1">A</label>' in result
        assert result == apply_html(render_plain(expand_source(source)))


class TestPreBlock:
    def test_a_tab_line_inside_a_pre_block_is_expanded_in_process_as_in_the_pipeline(self) -> None:
        source = "<pre>\n[tab A]\n\nx\n\n[/tab]\n</pre>"
        assert render_tabs(source) == apply_html(render_plain(expand_source(source)))


class TestCloserValidation:
    def test_a_closer_with_an_unsupported_version_does_not_close_its_tab(self) -> None:
        diagnostics: list[Diagnostic] = []
        page = f'{TAB_OPEN}\n<p>x</p>\n<!-- mw-tab-end:{{"version": 2}} -->'
        result = apply_html(page, diagnostics)
        assert "tabbed-set" not in result
        assert "mw-tab" not in result
        assert messages(diagnostics) == ["Skipping mw-tab-end marker with unsupported version 2"]

    def test_a_malformed_closer_is_skipped_and_reported(self) -> None:
        diagnostics: list[Diagnostic] = []
        apply_html(f"{TAB_OPEN}\n<p>x</p>\n<!-- mw-tab-end:{{nope -->", diagnostics)
        assert messages(diagnostics) == ["Skipping malformed mw-tab-end marker: '{nope'"]

    def test_a_valid_closer_is_unaffected(self) -> None:
        diagnostics: list[Diagnostic] = []
        apply_html(f"{TAB_OPEN}\n<p>x</p>\n{TAB_END}", diagnostics)
        assert messages(diagnostics) == []


class TestCrlfProblemMarker:
    def test_a_problem_marker_lands_before_the_carriage_return(self) -> None:
        result = expand_source("text\r\n\r\n[/tab]\r\n")
        problem = '{"version": 1, "line": 3, "directive": "[/tab]", "reason": "stray-closer"}'
        assert result.endswith(f"[/tab]<!-- mw-tab-problem:{problem} -->\r\n")


class TestCrlfSourceLine:
    def test_in_process_problem_reports_the_true_line_of_a_crlf_document(self) -> None:
        instance = markdown.Markdown(extensions=["markwright.tabs"])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            instance.convert("text\r\n\r\nmore\r\n\r\n[/tab]\r\n")
        assert [diagnostic.line for diagnostic in instance.markwright_diagnostics] == [5]  # type: ignore[attr-defined]


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


class TestEscapedDirective:
    def test_an_escaped_tab_pair_stays_literal_in_both_paths(self) -> None:
        source = "\\[tab Name]\n\ntext\n\n\\[/tab]"
        diagnostics: list[Diagnostic] = []
        piped = apply_html(render_plain(expand_source(source)), diagnostics)
        assert piped == render_tabs(source)
        assert "<p>[tab Name]</p>" in piped
        assert "<p>[/tab]</p>" in piped
        assert "tabbed-set" not in piped
        assert messages(diagnostics) == []


class TestDiagnostics:
    def collect(self, source: str) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        apply_html(render_plain(expand_source(source)), diagnostics)
        return diagnostics

    def test_a_problem_marker_carries_its_line_and_directive(self) -> None:
        assert self.collect("[tab One]\n\ntext") == [
            Diagnostic(
                extension="tabs",
                line=1,
                directive="[tab]",
                reason="unclosed",
                message="Leaving [tab] on line 1 literal: unclosed, no matching closer",
            )
        ]

    def test_a_stray_closer_is_a_stray_closer_report(self) -> None:
        diagnostics = self.collect("text\n\n[/tab]")
        assert [(item.reason, item.line, item.directive) for item in diagnostics] == [("stray-closer", 3, "[/tab]")]

    def test_a_malformed_marker_is_a_malformed_marker_report_with_no_line(self) -> None:
        diagnostics: list[Diagnostic] = []
        apply_html(f"<!-- mw-tab:{{nope -->\n<p>x</p>\n{TAB_END}", diagnostics)
        assert [(item.extension, item.reason, item.line) for item in diagnostics] == [
            ("tabs", "malformed-marker", None)
        ]

    def test_an_unpaired_marker_is_an_unmatched_marker_report(self) -> None:
        diagnostics: list[Diagnostic] = []
        apply_html(f"{TAB_OPEN}\n<p>x</p>", diagnostics)
        assert [(item.reason, item.line) for item in diagnostics] == [("unmatched-marker", None)]


class TestInProcessDiagnostics:
    SOURCE = "[tab One]\n\ntext\n\n[/tab]\n\n[/tab]"

    def make_md(self) -> markdown.Markdown:
        return markdown.Markdown(extensions=["markwright.tabs"])

    def test_the_list_matches_the_pipeline_and_one_warning_is_emitted_per_entry(self) -> None:
        md = self.make_md()
        with pytest.warns(RenderWarning) as recorded:
            md.convert(self.SOURCE)
        expected: list[Diagnostic] = []
        apply_html(render_plain(expand_source(self.SOURCE)), expected)
        assert md.markwright_diagnostics == expected  # type: ignore[attr-defined]
        assert [warning.message.diagnostic for warning in recorded] == expected  # type: ignore[union-attr]
        assert len(expected) == 1

    def test_a_second_convert_starts_with_an_empty_list(self) -> None:
        md = self.make_md()
        with pytest.warns(RenderWarning):
            md.convert(self.SOURCE)
        md.convert("plain text")
        assert md.markwright_diagnostics == []  # type: ignore[attr-defined]

    def test_reset_empties_the_list(self) -> None:
        md = self.make_md()
        with pytest.warns(RenderWarning):
            md.convert(self.SOURCE)
        md.reset()
        assert md.markwright_diagnostics == []  # type: ignore[attr-defined]

    def test_a_clean_document_reports_nothing(self) -> None:
        md = self.make_md()
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            md.convert("[tab One]\n\ntext\n\n[/tab]")
        assert md.markwright_diagnostics == []  # type: ignore[attr-defined]

    def test_the_html_is_byte_identical_whatever_the_warning_filter(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ignored = self.make_md().convert(self.SOURCE)
        with warnings.catch_warnings():
            warnings.simplefilter("always")
            shown = self.make_md().convert(self.SOURCE)
        assert ignored == shown

    def test_a_blank_document_keeps_the_earlier_entries_until_reset(self) -> None:
        # Python-Markdown returns before any preprocessor runs on blank input; reset() is the documented way out.
        md = self.make_md()
        with pytest.warns(RenderWarning):
            md.convert(self.SOURCE)
        md.convert("  \n")
        assert len(md.markwright_diagnostics) == 1  # type: ignore[attr-defined]
        md.reset()
        assert md.markwright_diagnostics == []  # type: ignore[attr-defined]
