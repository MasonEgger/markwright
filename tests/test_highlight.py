# ABOUTME: Tests for the highlight extension converting <^>text<^> to <mark> tags.
# Covers inline text, inline code, fenced code blocks, and edge cases.

from __future__ import annotations

import re

import markdown
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor

from markwright import registry
from markwright.highlight import apply_html, expand_source


def _render(source: str) -> str:
    """Render Markdown source with the highlight extension loaded."""
    md = markdown.Markdown(extensions=["markwright.highlight"])
    return md.convert(source)


def _render_with_superfences(source: str) -> str:
    """Render with highlight + superfences, matching the real site stack."""
    md = markdown.Markdown(
        extensions=["pymdownx.superfences", "pymdownx.highlight", "markwright.highlight"],
        extension_configs={"pymdownx.highlight": {"pygments_lang_class": True}},
    )
    return md.convert(source)


def _stub_render(markdown_text: str) -> str:
    """Render Markdown through superfences and highlight only, preserving raw HTML.

    Stands in for an external renderer (the ``mw pre | post`` path) that knows
    nothing about markwright directives, mirroring ``tests/test_roundtrip.py``'s
    ``stub_render``.
    """
    instance = markdown.Markdown(
        extensions=["pymdownx.superfences", "pymdownx.highlight"],
        extension_configs={"pymdownx.highlight": {"pygments_lang_class": True}},
    )
    return instance.convert(markdown_text)


class _StashPreprocessor(Preprocessor):
    """Replace ``[raw]`` with the placeholder of a stashed block, as a preprocessor that stashes HTML does."""

    def run(self, lines: list[str]) -> list[str]:
        return [line.replace("[raw]", self.md.htmlStash.store("<b>raw</b>")) for line in lines]


class _StashAtToken(Extension):
    """Register :class:`_StashPreprocessor` below ``normalize_whitespace``, which strips placeholder markers."""

    def extendMarkdown(self, md: markdown.Markdown) -> None:  # noqa: N802 - Python-Markdown's hook name
        md.preprocessors.register(_StashPreprocessor(md), "stash_at_token", 10)


class TestInlineHighlight:
    """Test <^>...<^> in regular inline text."""

    def test_basic_inline(self) -> None:
        result = _render("This is a <^>variable<^>")
        assert "<mark>variable</mark>" in result

    def test_multiple_highlights_same_line(self) -> None:
        result = _render("<^>a<^> and <^>b<^>")
        assert "<mark>a</mark>" in result
        assert "<mark>b</mark>" in result

    def test_highlight_in_paragraph(self) -> None:
        result = _render("Before <^>middle<^> after")
        assert "<mark>middle</mark>" in result
        assert "Before" in result
        assert "after" in result


class TestInlineSameLinePairing:
    """In prose a marker pairs with the next prose marker on the same line, never across a line end."""

    def test_markers_on_two_lines_of_a_paragraph_do_not_pair(self) -> None:
        result = _render("e <^>f\ng<^> h")
        assert "<mark>" not in result
        assert result.count("&lt;^&gt;") == 2

    def test_pair_around_a_code_span_marks_the_code_span(self) -> None:
        assert _render("a <^>b `x` c<^> d") == "<p>a <mark>b <code>x</code> c</mark> d</p>"

    def test_opener_without_a_same_line_closer_stays_literal_and_a_later_pair_matches(self) -> None:
        result = _render("a <^>b\nc <^>d<^> e")
        assert "<mark>d</mark>" in result
        assert result.count("&lt;^&gt;") == 1

    def test_an_opener_pairs_with_the_next_marker_on_its_line(self) -> None:
        assert _render("a <^>b <^>c<^> d") == "<p>a <mark>b </mark>c&lt;^&gt; d</p>"

    def test_pair_whose_text_holds_a_stashed_block_placeholder_is_declined(self) -> None:
        md = markdown.Markdown(extensions=["markwright.highlight", _StashAtToken()])
        result = md.convert("a <^>b [raw] c<^> d")
        # The inline processor declines the pair, so the stashed block never sits inside one <mark>; the post
        # stage then pairs the two literal markers and wraps each text run around the restored block
        assert result == "<p>a <mark>b </mark><b><mark>raw</mark></b><mark> c</mark> d</p>"

    def test_marker_on_either_side_of_a_code_block_does_not_wrap_it(self) -> None:
        result = _render_with_superfences("a <^>b\n\n```\ncode\n```\n\nc<^> d")
        assert "<mark>" not in result

    def test_marker_before_a_list_item_does_not_pair_with_one_in_it(self) -> None:
        result = _render("a <^>b\n- c<^> d")
        assert "<mark>" not in result


class TestInlineCodeHighlight:
    """Test <^>...<^> inside inline code spans."""

    def test_inline_code_highlight(self) -> None:
        result = _render("`code <^>var<^>`")
        assert "<mark>var</mark>" in result
        assert "<code>" in result


class TestFencedCodeHighlight:
    """Test <^>...<^> inside fenced code blocks."""

    def test_fenced_code_highlight(self) -> None:
        source = "```\nhello\n<^>highlighted<^>\n```"
        result = _render_with_superfences(source)
        assert "<mark>highlighted</mark>" in result
        assert "<pre" in result

    def test_fenced_code_with_language(self) -> None:
        source = "```python\nprint(<^>value<^>)\n```"
        result = _render_with_superfences(source)
        assert "<mark>" in result

    def test_fenced_code_with_language_valid_nesting(self) -> None:
        """Marks must not cross Pygments ``<span>`` boundaries.

        Pygments wraps language-tagged code in ``<span>`` tokens. A naive
        replacement emits ``<mark>``/``</mark>`` that interleave with those
        spans, producing overlapping HTML that browsers fail to render. Each
        mark must wrap only text, never partial tags.
        """
        source = "```python\nprint(<^>value<^>)\n```"
        result = _render_with_superfences(source)
        assert result.count("<mark>") == result.count("</mark>")
        # No tag may appear between a <mark> and its matching </mark>.
        assert re.search(r"<mark>[^<]*<(?!/mark>)", result) is None
        # The highlighted token survives intact.
        assert "<mark>value</mark>" in result

    def test_fenced_code_highlight_spanning_tokens(self) -> None:
        """A highlight that spans several syntax tokens stays well-formed."""
        source = '```python\nprint(f"Hello, <^>{name}<^>!")\n```'
        result = _render_with_superfences(source)
        assert result.count("<mark>") == result.count("</mark>")
        assert re.search(r"<mark>[^<]*<(?!/mark>)", result) is None
        # Every visible character of the highlighted region is inside a mark.
        assert "name" in result
        marked = "".join(re.findall(r"<mark>(.*?)</mark>", result))
        assert "name" in re.sub(r"<[^>]+>", "", marked)

    def test_empty_highlight_in_fenced_code_produces_empty_mark(self) -> None:
        """An empty highlight inside code yields ``<mark></mark>``.

        Empty markers reach the postprocessor's segment wrapper with no text
        between them, which must emit an empty mark rather than crashing on the
        missing region.
        """
        source = "```\n<^><^>\n```"
        result = _render_with_superfences(source)
        assert "<mark></mark>" in result


class TestEscapedMarkers:
    """Test that ``\\<^>`` renders a literal marker instead of highlighting.

    This lets documentation show the literal ``<^>`` syntax inside code without
    the markers being consumed and turned into a highlight.
    """

    def test_escaped_markers_in_fenced_code(self) -> None:
        source = "```\n" + r"\<^>literal\<^>" + "\n```"
        result = _render_with_superfences(source)
        assert "<mark>" not in result
        assert "&lt;&#94;&gt;literal&lt;&#94;&gt;" in result

    def test_escaped_markers_in_inline_code(self) -> None:
        result = _render(r"Write `\<^>text\<^>` to highlight.")
        assert "<mark>" not in result
        assert "<code>&lt;&#94;&gt;text&lt;&#94;&gt;</code>" in result

    def test_escaped_and_real_markers_coexist(self) -> None:
        source = "```\n" + r"\<^>shown\<^> and <^>marked<^>" + "\n```"
        result = _render_with_superfences(source)
        assert "&lt;&#94;&gt;shown&lt;&#94;&gt;" in result
        assert "<mark>marked</mark>" in result


class TestEdgeCases:
    """Test edge cases and non-matching inputs."""

    def test_unclosed_marker_no_match(self) -> None:
        result = _render("<^>unclosed")
        assert "<mark>" not in result

    def test_empty_highlight_produces_empty_mark(self) -> None:
        """The JS reference regex (.*?) matches empty, producing <mark></mark>."""
        result = _render("<^><^>")
        assert "<mark></mark>" in result

    def test_no_markers_passthrough(self) -> None:
        result = _render("plain text with no markers")
        assert "<mark>" not in result
        assert "plain text with no markers" in result


class TestHighlightApplyHtml:
    """Test the pure ``apply_html`` HTML-stage transform (``mw post``)."""

    def test_wraps_escaped_marker_run(self) -> None:
        result = apply_html("a &lt;^&gt;word&lt;^&gt; b")
        assert "<mark>word</mark>" in result

    def test_backslash_escaped_marker_left_literal(self) -> None:
        result = apply_html(r"a \&lt;^&gt;word\&lt;^&gt; b")
        assert "<mark>" not in result
        assert "&lt;&#94;&gt;word&lt;&#94;&gt;" in result


class TestHighlightExpandSource:
    """Test the pure ``expand_source`` source-stage transform (``mw pre``)."""

    def test_wraps_prose_marker(self) -> None:
        assert expand_source("a <^>word<^> b") == "a <mark>word</mark> b"

    def test_marker_in_fenced_code_untouched(self) -> None:
        source = "```\nfoo <^>x<^> bar\n```"
        assert expand_source(source) == source

    def test_marker_in_inline_code_untouched(self) -> None:
        source = "use `<^>x<^>` here"
        assert expand_source(source) == source

    def test_marker_in_an_html_attribute_is_wrapped_as_released(self) -> None:
        assert expand_source('<span title="<^>s<^>">y</span>') == '<span title="<mark>s</mark>">y</span>'

    def test_marker_in_an_autolink_is_wrapped_as_released(self) -> None:
        assert expand_source("<https://x.test/<^>q<^>>") == "<https://x.test/<mark>q</mark>>"

    def test_marker_in_an_inline_comment_is_wrapped_as_released(self) -> None:
        assert expand_source("x <!-- <^>a<^> --> y") == "x <!-- <mark>a</mark> --> y"

    def test_marker_in_a_tags_text_content_is_wrapped(self) -> None:
        assert expand_source('<span title="x"><^>y<^></span>') == '<span title="x"><mark>y</mark></span>'

    def test_pair_around_inline_html_is_wrapped_as_released(self) -> None:
        assert (
            expand_source('see <^>the <a href="u">link</a><^> now') == 'see <mark>the <a href="u">link</a></mark> now'
        )

    def test_pair_around_an_inline_comment_is_wrapped_as_released(self) -> None:
        assert expand_source("<^>a <!-- c --> b<^>") == "<mark>a <!-- c --> b</mark>"

    def test_backtick_in_an_attribute_pairs_the_code_span_as_released(self) -> None:
        assert expand_source('<a title="`"><^>d<^></a> `<^>e<^>`') == '<a title="`"><^>d<^></a> `<mark>e</mark>`'

    def test_marker_in_tab_indented_list_fence_untouched(self) -> None:
        source = "- item\n\n\t```\n\t<^>x<^>\n\t```"
        assert expand_source(source) == source

    def test_marker_in_indented_code_block_untouched(self) -> None:
        source = "para\n\n    <^>x<^>\n"
        assert expand_source(source) == source

    def test_odd_backslash_run_before_a_prose_marker_is_an_escape_both_renderers_hand_back(self) -> None:
        """An odd run escapes the marker: one backslash is added and the marker's ``<`` is written ``&lt;``.

        That form renders as a backslash and a literal ``&lt;^&gt;`` under Python-Markdown and under a
        CommonMark renderer alike, which is the form ``mw post`` reveals.
        """
        assert expand_source(r"a \<^>x\<^> b") == r"a \\&lt;^>x\\&lt;^> b"

    def test_three_backslashes_before_a_prose_marker_are_an_escape_with_one_added(self) -> None:
        assert expand_source(r"a \\\<^>x") == r"a \\\\&lt;^>x"

    def test_even_backslash_run_leaves_the_prose_marker_live(self) -> None:
        assert expand_source(r"a \\<^>x<^> b") == r"a \\<mark>x</mark> b"

    def test_escaped_marker_between_a_live_pair_is_rewritten_and_the_pair_wraps(self) -> None:
        assert expand_source(r"<^>a \<^> b<^>") == r"<mark>a \\&lt;^> b</mark>"

    def test_escaped_marker_does_not_close_a_pair(self) -> None:
        assert expand_source(r"<^>a\<^> b") == r"<^>a\\&lt;^> b"

    def test_escape_in_fenced_code_stays_for_the_post_stage(self) -> None:
        source = "```\n" + r"\<^>x\<^>" + "\n```"
        assert expand_source(source) == source

    def test_marker_without_a_closer_on_its_line_stays_literal(self) -> None:
        assert expand_source("a <^>b\nc<^> d <^>e<^>") == "a <^>b\nc<mark> d </mark>e<^>"

    def test_pair_around_a_code_span_is_wrapped_in_one_mark(self) -> None:
        assert expand_source("a <^>b `x` c<^> d") == "a <mark>b `x` c</mark> d"

    def test_marker_inside_a_code_span_stays_literal(self) -> None:
        assert expand_source("a <^>b `x<^>y` c<^> d") == "a <mark>b `x<^>y` c</mark> d"

    def test_marker_inside_a_code_span_does_not_close_a_prose_pair(self) -> None:
        source = "a <^>b `x<^>y` c"
        assert expand_source(source) == source

    def test_pair_around_a_code_span_that_holds_a_line_end_is_wrapped(self) -> None:
        assert expand_source("a <^>b `x\ny` c<^> d") == "a <mark>b `x\ny` c</mark> d"

    def test_code_span_is_not_followed_across_a_blank_line(self) -> None:
        assert expand_source("`a <^>b<^> c\n\nd`") == "`a <mark>b</mark> c\n\nd`"

    def test_markers_on_two_lines_do_not_pair(self) -> None:
        source = "e <^>f\ng<^> h"
        assert expand_source(source) == source

    def test_escape_inside_a_code_span_is_untouched(self) -> None:
        source = r"a `\<^>x` b"
        assert expand_source(source) == source

    def test_running_the_pre_stage_twice_is_stable(self) -> None:
        once = expand_source(r"a \<^>x\<^> <^>y<^> b")
        assert expand_source(once) == once


class TestHighlightConsumerParity:
    """Cross-consumer parity: ``mw render``, ``mw pre``, and ``mw pre | post`` agree.

    Every consumer must treat an escaped marker (``\\<^>``) as a literal, never
    highlighted, and an unescaped marker (``<^>``) as a highlight, regardless of
    which stage resolves it.
    """

    def _consumers(self, source: str) -> dict[str, str]:
        """Render ``source`` through all three highlight consumers.

        :param source: Prose Markdown source containing a highlight marker.
        :returns: A mapping of consumer name to its rendered output.
        """
        pre_output = registry.run_pre(source, ["highlight"])
        return {
            "in-process": _render(source),
            "mw pre": pre_output,
            "mw pre | post": registry.run_post(_stub_render(pre_output), ["highlight"]),
        }

    def test_escaped_marker_is_literal_on_every_consumer(self) -> None:
        outputs = self._consumers(r"a \<^>x\<^> b")
        for consumer, result in outputs.items():
            assert "<mark>" not in result, f"{consumer} produced <mark> for an escaped marker: {result!r}"

    def test_unescaped_marker_is_highlighted_on_every_consumer(self) -> None:
        outputs = self._consumers("a <^>x<^> b")
        for consumer, result in outputs.items():
            assert "<mark>x</mark>" in result, f"{consumer} did not highlight an unescaped marker: {result!r}"


class TestHighlightTildeFence:
    """``expand_source`` must skip markers inside tilde fences, matching backtick fences."""

    def test_marker_in_tilde_fence_untouched(self) -> None:
        source = "~~~\n<^>x<^>\n~~~"
        assert expand_source(source) == source

    def test_marker_in_backtick_fence_untouched(self) -> None:
        """Regression guard: the existing backtick-fence behavior stays intact."""
        source = "```\n<^>x<^>\n```"
        assert expand_source(source) == source


class TestHighlightPostStageScope:
    """The post stage reads markers from rendered text only, never from markup."""

    def test_marker_in_an_attribute_is_untouched(self) -> None:
        rendered = '<span title="&lt;^&gt;">x</span>&lt;^&gt;y&lt;^&gt;'
        assert apply_html(rendered) == '<span title="&lt;^&gt;">x</span><mark>y</mark>'

    def test_marker_in_a_script_is_untouched(self) -> None:
        rendered = "<script>var a = '&lt;^&gt;b&lt;^&gt;';</script>"
        assert apply_html(rendered) == rendered

    def test_marker_in_a_title_is_untouched(self) -> None:
        rendered = "<head><title>a &amp; &lt;^&gt;b&lt;^&gt;</title></head>"
        assert apply_html(rendered) == rendered

    def test_marker_in_a_textarea_is_untouched(self) -> None:
        rendered = "<textarea>&lt;^&gt;b&lt;^&gt; &amp; c</textarea>"
        assert apply_html(rendered) == rendered

    def test_marker_in_body_text_beside_a_title_is_still_wrapped(self) -> None:
        rendered = "<title>t</title><p>&lt;^&gt;b&lt;^&gt;</p>"
        assert apply_html(rendered) == "<title>t</title><p><mark>b</mark></p>"

    def test_markers_on_different_lines_do_not_pair(self) -> None:
        rendered = "<code>&lt;^&gt;a\nb&lt;^&gt;</code>"
        assert apply_html(rendered) == rendered

    def test_full_documents_pass_through_except_markers(self) -> None:
        # Doctypes, processing instructions, CDATA, character references, and self-closing tags are copied byte for byte
        page = (
            '<?xml version="1.0"?>\n<!DOCTYPE html>\n<html><body><br/>'
            "<![CDATA[raw]]><code>it&#39;s &#x27;a&#x27; &lt;^&gt;b&lt;^&gt;</code></body></html>"
        )
        assert apply_html(page) == page.replace("&lt;^&gt;b&lt;^&gt;", "<mark>b</mark>")


class TestInCodeEscapeAndSplitMarkers:
    """Markers and escapes are read from each code line's text, whatever tags split them."""

    def test_escape_split_from_the_marker_by_a_tag_renders_a_literal_marker(self) -> None:
        # The python lexer puts the backslash outside the operator span that holds the marker
        result = _render_with_superfences("```python\nx = " + r"\<^>a\<^>" + "\n```")
        assert "<mark>" not in result
        assert "&lt;&#94;&gt;" in result
        assert "\\&lt;" not in re.sub(r"<[^>]+>", "", result)

    def test_marker_split_by_the_lexer_still_pairs(self) -> None:
        for language in ("bash", "html", "xml"):
            result = _render_with_superfences(f"```{language}\n<^>word<^> tail\n```")
            visible_text = re.sub(r"<[^>]+>", "", result)
            assert "<mark>word</mark>" in result, language
            assert "^" not in visible_text, language

    def test_escape_in_a_split_marker_is_one_backslash_removed(self) -> None:
        rendered = '<pre><code><span class="x">\\&lt;</span><span class="y">^&gt;</span>a</code></pre>'
        expected = '<pre><code><span class="x">&lt;</span><span class="y">&#94;&gt;</span>a</code></pre>'
        assert apply_html(rendered) == expected

    def test_paired_marker_characters_are_removed_and_every_tag_stays(self) -> None:
        rendered = (
            '<code><span class="o">&lt;</span><span class="p">^&gt;</span>ab<span class="o">&lt;^&gt;</span></code>'
        )
        assert apply_html(rendered) == (
            '<code><span class="o"></span><span class="p"></span><mark>ab</mark><span class="o"></span></code>'
        )

    def test_a_span_that_held_only_a_backslash_remains_empty(self) -> None:
        rendered = '<code><span class="se">\\</span><span class="o">&lt;^&gt;</span>a</code>'
        assert apply_html(rendered) == '<code><span class="se"></span><span class="o">&lt;&#94;&gt;</span>a</code>'

    def test_revealed_literal_marker_is_left_alone_by_a_second_pass(self) -> None:
        once = apply_html(r"x \&lt;^&gt;a\&lt;^&gt; y")
        assert once == "x &lt;&#94;&gt;a&lt;&#94;&gt; y"
        assert apply_html(once) == once

    def test_escaped_marker_inside_a_pair_is_revealed_within_the_mark(self) -> None:
        assert apply_html(r"&lt;^&gt;a \&lt;^&gt; b&lt;^&gt;") == "<mark>a &lt;&#94;&gt; b</mark>"

    def test_pair_across_tags_wraps_each_text_run(self) -> None:
        rendered = '<code>&lt;^&gt;a<span class="n">b</span>c&lt;^&gt;</code>'
        assert apply_html(rendered) == '<code><mark>a</mark><span class="n"><mark>b</mark></span><mark>c</mark></code>'


class TestInCodeEscapeUnderChroma:
    """The same cases under Chroma, which wraps each code line in ``<span class="line">``."""

    def test_escape_split_from_the_marker_by_a_span(self) -> None:
        rendered = (
            '<pre class="chroma"><code class="language-python" data-lang="python">'
            '<span class="line"><span class="cl"><span class="n">x</span> <span class="o">=</span> '
            '\\<span class="o">&lt;^&gt;</span><span class="n">a</span>'
            '\\<span class="o">&lt;^&gt;</span>\n</span></span>'
            "</code></pre>"
        )
        result = apply_html(rendered)
        assert "<mark>" not in result
        assert result.count("&lt;&#94;&gt;") == 2
        assert "\\" not in result

    def test_marker_split_across_spans_pairs_on_one_line(self) -> None:
        rendered = (
            '<pre class="chroma"><code>'
            '<span class="line"><span class="cl"><span class="o">&lt;</span>^&gt;<span class="n">v</span>'
            '<span class="o">&lt;</span>^&gt; t\n</span></span>'
            '<span class="line"><span class="cl">next\n</span></span></code></pre>'
        )
        result = apply_html(rendered)
        assert "<mark>v</mark>" in result
        assert "^" not in re.sub(r"<[^>]+>", "", result)

    def test_markers_on_different_chroma_lines_do_not_pair(self) -> None:
        rendered = (
            '<pre class="chroma"><code>'
            '<span class="line"><span class="cl">&lt;^&gt;a\n</span></span>'
            '<span class="line"><span class="cl">b&lt;^&gt;\n</span></span></code></pre>'
        )
        assert apply_html(rendered) == rendered
