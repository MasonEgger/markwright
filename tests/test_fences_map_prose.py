# ABOUTME: Tests for markwright._fences.map_prose, which transforms prose and skips fenced and inline code.
# Exempt from the public-API-only rule: the _fences scanner has a contract of its own and is tested directly.

from __future__ import annotations

import pytest

from markwright._fences import find_inline_code_spans, map_prose


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


class TestMapProseSkipBlocksOpenedBy:
    """With ``skip_blocks_opened_by``, a block whose first line starts with the opener is left alone."""

    OPENER = '<pre class="mermaid">'

    def skip(self, source: str) -> str:
        return map_prose(source, str.upper, skip_blocks_opened_by=self.OPENER)

    def test_block_is_skipped_through_the_line_holding_the_closing_tag(self) -> None:
        source = f"a\n{self.OPENER}b\n  c\n</pre>\nd"
        assert self.skip(source) == f"A\n{self.OPENER}b\n  c\n</pre>\nD"

    def test_block_is_skipped_at_any_indentation(self) -> None:
        source = f"- a\n\n    {self.OPENER}b\n      c\n    </pre>\n\n    d"
        assert self.skip(source) == f"- A\n\n    {self.OPENER}b\n      c\n    </pre>\n\n    D"

    def test_text_after_the_closing_tag_on_its_line_is_prose(self) -> None:
        source = f"{self.OPENER}a\nb</pre> c\nd\n{self.OPENER}e</pre> f"
        assert self.skip(source) == f"{self.OPENER}a\nb</pre> C\nD\n{self.OPENER}e</pre> F"

    @pytest.mark.parametrize(
        "block_text",
        ["b\n\n    c\n  d", "b\n```\n  c\n```\n  d", "b\n\n    c\n\n```\n  d\n```"],
        ids=["indented-code-line", "closed-fence", "indented-code-then-a-fence"],
    )
    def test_block_text_that_reads_as_code_stays_inside_the_block(self, block_text: str) -> None:
        source = f"a\n{self.OPENER}{block_text}\n</pre> e\nf"
        assert self.skip(source) == f"A\n{self.OPENER}{block_text}\n</pre> E\nF"

    @pytest.mark.parametrize(
        ("source", "expected"),
        [
            (f"{OPENER}a\n```\nb\n</pre>\nc\n```\nd", f"{OPENER}a\n```\nb\n</pre>\nC\n```\nD"),
            (f"{OPENER}a\n~~~\nb\n</pre>\n~~~\nc\n~~~\nd", f"{OPENER}a\n~~~\nb\n</pre>\n~~~\nc\n~~~\nD"),
            (
                f"{OPENER}a\n```\n</pre>\nb\n{OPENER}c\n```\n</pre>\nd",
                f"{OPENER}a\n```\n</pre>\nB\n{OPENER}c\n```\n</pre>\nD",
            ),
        ],
        ids=["fence-line-in-the-block", "fence-after-the-block", "fence-line-in-each-of-two-blocks"],
    )
    def test_block_text_changes_nothing_after_the_block(self, source: str, expected: str) -> None:
        assert self.skip(source) == expected

    def test_two_blocks_are_both_skipped(self) -> None:
        source = f"{self.OPENER}a\n</pre>\nb\n{self.OPENER}c\n</pre>"
        assert self.skip(source) == f"{self.OPENER}a\n</pre>\nB\n{self.OPENER}c\n</pre>"

    @pytest.mark.parametrize(
        "source",
        [
            '<pre class="mermaid" id="x">b\n</pre>',
            '<PRE CLASS="MERMAID">b\n</PRE>',
            "<pre>b\n</pre>",
            f"text {OPENER}b\n</pre>",
            f"{OPENER}b\nno closing tag",
        ],
        ids=["other-attribute", "upper-case", "plain-pre", "mid-line", "unclosed"],
    )
    def test_other_shapes_are_prose(self, source: str) -> None:
        assert self.skip(source) == source.upper()

    def test_nothing_is_skipped_by_default(self) -> None:
        assert map_prose(f"{self.OPENER}b\n</pre>", str.upper) == f"{self.OPENER.upper()}B\n</PRE>"

    def test_an_opener_inside_a_fence_is_code(self) -> None:
        source = f"```\n{self.OPENER}\n```\n\nb\n\n```\n</pre>\n```"
        assert "\nB\n" in self.skip(source)


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
