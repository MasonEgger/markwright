# ABOUTME: Tests for markwright._fences.map_prose, which transforms prose and skips fenced and inline code.
# Exempt from the public-API-only rule: the _fences scanner has a contract of its own and is tested directly.

from __future__ import annotations

import pytest

from markwright._fences import find_fenced_blocks, find_inline_code_spans, map_directive_lines, map_lines, map_prose


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

    def test_leaves_a_top_level_indented_code_block_untouched(self) -> None:
        assert map_prose("para\n\n    code here\n", str.upper) == "PARA\n\n    code here\n"

    def test_leaves_a_tab_indented_in_list_fence_untouched(self) -> None:
        source = "- item\n\n\t```\n\tcode\n\t```\nafter"

        assert map_prose(source, str.upper) == "- ITEM\n\n\t```\n\tcode\n\t```\nAFTER"


def _mark_hit(prose: str) -> str:
    return prose.replace("hit", "HIT").replace("x", "X")


class TestMapProseHtml:
    def test_the_default_leaves_a_tags_attribute_as_prose(self) -> None:
        assert map_prose('<span title="hit">x</span> hit', _mark_hit) == '<span title="HIT">X</span> HIT'

    def test_skips_an_attribute_value_and_transforms_the_tag_content(self) -> None:
        assert (
            map_prose('<span title="hit">x</span> hit', _mark_hit, skip_html=True) == '<span title="hit">X</span> HIT'
        )

    def test_skips_a_single_line_comment(self) -> None:
        assert map_prose("<!-- hit -->\nhit", _mark_hit, skip_html=True) == "<!-- hit -->\nHIT"

    def test_skips_a_comment_spanning_lines(self) -> None:
        assert map_prose("<!--\nhit\n-->\nhit", _mark_hit, skip_html=True) == "<!--\nhit\n-->\nHIT"

    def test_skips_an_autolink(self) -> None:
        assert map_prose("<https://x.test/hit> hit", _mark_hit, skip_html=True) == "<https://x.test/hit> HIT"

    def test_a_bare_less_than_sign_is_prose(self) -> None:
        assert map_prose("a < hit and c > d", _mark_hit, skip_html=True) == "a < HIT and c > d"

    def test_a_code_span_holding_a_tag_is_still_a_code_span(self) -> None:
        assert map_prose('`<b title="hit">` hit', _mark_hit, skip_html=True) == '`<b title="hit">` HIT'

    def test_a_backtick_inside_an_attribute_does_not_start_a_code_span(self) -> None:
        assert (
            map_prose('<a title="`">hit</a> `hit` hit', _mark_hit, skip_html=True) == '<a title="`">HIT</a> `hit` HIT'
        )

    def test_a_tag_inside_a_code_span_does_not_split_it(self) -> None:
        assert map_prose("`a <b` hit>", _mark_hit, skip_html=True) == "`a <b` HIT>"

    def test_a_tag_holding_an_angle_bracket_is_prose(self) -> None:
        assert (
            map_prose('<span title="<^>hit<^>">x</span> hit', _mark_hit, skip_html=True)
            == '<span title="<^>HIT<^>">X</span> HIT'
        )


class TestMapProseBlockBodies:
    def test_transforms_prose_in_each_block_opener_body(self) -> None:
        for opener in ['!!! note "Title"', "??? note", '===+ "Tab"', ": definition", "[^note]: footnote"]:
            source = f"term\n{opener}\n\n    body text\n"

            assert map_prose(source, str.upper) == f"TERM\n{opener.upper()}\n\n    BODY TEXT\n", opener

    def test_leaves_a_line_four_columns_further_untouched(self) -> None:
        source = "!!! note\n    body\n\n        code here"

        assert map_prose(source, str.upper) == "!!! NOTE\n    BODY\n\n        code here"


class TestMapProseVerbatimBlocks:
    """A ``<pre>``, ``<script>``, ``<style>``, or ``<textarea>`` block is skipped through its close tag."""

    @pytest.mark.parametrize("tag", ["pre", "script", "style", "textarea"])
    def test_block_is_skipped_through_the_line_holding_the_close_tag(self, tag: str) -> None:
        source = f"a\n<{tag} class=x>b\n  c\n</{tag}>\nd"
        assert map_prose(source, str.upper) == f"A\n<{tag} class=x>b\n  c\n</{tag}>\nD"

    def test_open_and_close_tags_are_case_insensitive(self) -> None:
        source = "a\n<PRE>b\n</Pre>\nc"
        assert map_prose(source, str.upper) == "A\n<PRE>b\n</Pre>\nC"

    def test_a_bare_tag_with_no_attributes_opens_a_block(self) -> None:
        assert map_prose("<pre>\nb\n</pre>", str.upper) == "<pre>\nb\n</pre>"

    def test_a_longer_tag_name_is_prose(self) -> None:
        assert map_prose("<pre-x>b\n</pre-x>", str.upper) == "<PRE-X>B\n</PRE-X>"

    def test_a_tag_in_the_middle_of_a_line_is_prose(self) -> None:
        assert map_prose("text <pre>b\n</pre>", str.upper) == "TEXT <PRE>B\n</PRE>"

    def test_block_is_skipped_at_any_indentation_under_a_list_item(self) -> None:
        source = "- a\n\n    <pre>b\n      c\n    </pre>\n\n    d"
        assert map_prose(source, str.upper) == "- A\n\n    <pre>b\n      c\n    </pre>\n\n    D"

    def test_text_after_the_close_tag_on_its_line_is_prose(self) -> None:
        source = "<pre>a\nb</pre> c\nd\n<script>e</script> f"
        assert map_prose(source, str.upper) == "<pre>a\nb</pre> C\nD\n<script>e</script> F"

    def test_an_unclosed_block_runs_to_the_end_of_the_document(self) -> None:
        source = "a\n<pre>b\n\nc\n```\nd\n```\ne"
        assert map_prose(source, str.upper) == "A\n<pre>b\n\nc\n```\nd\n```\ne"

    @pytest.mark.parametrize(
        "block_text",
        ["b\n\n    c\n  d", "b\n```\n  c\n```\n  d", "b\n\n    c\n\n```\n  d\n```"],
        ids=["indented-code-line", "closed-fence", "indented-code-then-a-fence"],
    )
    def test_block_text_that_reads_as_code_stays_inside_the_block(self, block_text: str) -> None:
        source = f"a\n<pre>{block_text}\n</pre> e\nf"
        assert map_prose(source, str.upper) == f"A\n<pre>{block_text}\n</pre> E\nF"

    def test_a_fence_line_inside_a_block_changes_nothing_after_it(self) -> None:
        source = "<pre>a\n```\nb\n</pre>\nc\n```\nd"
        assert map_prose(source, str.upper) == "<pre>a\n```\nb\n</pre>\nC\n```\nD"

    def test_an_opener_inside_a_fence_is_code(self) -> None:
        source = "```\n<pre>\n```\n\nb\n\n```\n</pre>\n```"
        assert "\nB\n" in map_prose(source, str.upper)

    def test_a_block_indented_four_columns_at_the_top_level_is_indented_code(self) -> None:
        assert map_prose("a\n\n    <pre>b\n    </pre>\nc", str.upper) == "A\n\n    <pre>b\n    </pre>\nC"


class TestMapProseCommentRegions:
    """A multi-line HTML comment is skipped through the line that closes it."""

    def test_comment_is_skipped_through_the_closing_line(self) -> None:
        source = "a\n<!--\nb\nc -->\nd"
        assert map_prose(source, str.upper) == "A\n<!--\nb\nc -->\nD"

    def test_text_after_the_closing_marker_on_its_line_stays_in_the_region(self) -> None:
        assert map_prose("<!-- a\nb --> c\nd", str.upper) == "<!-- a\nb --> c\nD"

    def test_a_comment_up_to_three_columns_in_opens_a_region(self) -> None:
        assert map_prose("   <!-- a\nb\n-->\nc", str.upper) == "   <!-- a\nb\n-->\nC"

    def test_a_comment_that_closes_on_its_own_line_is_not_a_region(self) -> None:
        assert map_prose("<!-- a -->\nb", str.upper) == "<!-- A -->\nB"

    def test_a_comment_in_the_middle_of_a_line_is_not_a_region(self) -> None:
        assert map_prose("a <!-- b\nc\n-->", str.upper) == "A <!-- B\nC\n-->"

    def test_an_unclosed_comment_runs_to_the_end_of_the_document(self) -> None:
        assert map_prose("a\n<!-- b\nc\n\nd", str.upper) == "A\n<!-- b\nc\n\nd"

    def test_an_opener_inside_a_fence_opens_nothing(self) -> None:
        source = "```\n<!--\n```\n\nb\n\n```\n-->\n```"
        assert "\nB\n" in map_prose(source, str.upper)

    def test_a_fence_opener_inside_a_comment_is_not_a_fence(self) -> None:
        source = "<!--\n```\n-->\nb\n```\nc"
        assert map_prose(source, str.upper) == "<!--\n```\n-->\nB\n```\nC"

    def test_a_comment_indented_four_columns_at_the_top_level_is_indented_code(self) -> None:
        assert map_prose("a\n\n    <!-- b\nc", str.upper) == "A\n\n    <!-- b\nC"

    def test_map_lines_and_map_directive_lines_leave_the_region_alone(self) -> None:
        source = "<!--\n[x]\n-->\n[x]"
        assert map_lines(source, lambda line: ["Y"] if line == "[x]" else [line]) == "<!--\n[x]\n-->\nY"
        assert map_directive_lines(source, lambda line: "Y" if line == "[x]" else None) == "<!--\n[x]\n-->\nY"

    def test_find_fenced_blocks_ignores_a_fence_inside_a_comment(self) -> None:
        assert find_fenced_blocks(["<!--", "```", "x", "```", "-->"]) == []


class TestMapProseBlockQuote:
    def test_leaves_a_fence_behind_a_quote_marker_untouched(self) -> None:
        source = "> note\n> ```\n> code here\n> ```\nafter"

        assert map_prose(source, str.upper) == "> NOTE\n> ```\n> code here\n> ```\nAFTER"

    def test_a_quoted_fence_the_quote_ends_before_closing_is_prose(self) -> None:
        assert map_prose("> ```\n> code\nafter\n```", str.upper) == "> ```\n> CODE\nAFTER\n```"

    def test_a_deeper_quoted_fence_line_is_code_text_not_the_closer(self) -> None:
        source = "> ```\n> > ```\n> code\n> ```\nafter"

        assert map_prose(source, str.upper) == "> ```\n> > ```\n> code\n> ```\nAFTER"


class TestMapProseKeepingInlineCode:
    def test_transform_sees_the_code_span_inside_the_run(self) -> None:
        assert map_prose("say `x` now", str.upper, skip_inline_code=False) == "SAY `X` NOW"

    def test_a_fenced_block_is_still_skipped(self) -> None:
        source = "a `x`\n```\ncode\n```\nb"
        assert map_prose(source, str.upper, skip_inline_code=False) == "A `X`\n```\ncode\n```\nB"


class TestFindInlineCodeSpans:
    def test_finds_a_span_with_its_backticks(self) -> None:
        assert find_inline_code_spans("a `x` b ``y`` c") == [(2, 5), (8, 13)]

    def test_a_span_may_hold_a_line_end(self) -> None:
        assert find_inline_code_spans("a `x\ny` b") == [(2, 7)]

    def test_a_span_does_not_cross_a_blank_line(self) -> None:
        assert find_inline_code_spans("a `x\n\ny` b") == []

    def test_a_span_does_not_cross_a_whitespace_only_line(self) -> None:
        assert find_inline_code_spans("a `x\n  \ny` b") == []

    def test_a_run_with_no_closer_of_the_same_length_is_not_a_span(self) -> None:
        assert find_inline_code_spans("a ``x` b") == []
