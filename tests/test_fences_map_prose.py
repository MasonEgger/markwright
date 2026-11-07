# ABOUTME: Tests for markwright._fences.map_prose, which transforms prose and skips fenced and inline code.
# Exempt from the public-API-only rule: the _fences scanner has a contract of its own and is tested directly.

from __future__ import annotations

from markwright._fences import map_prose


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
