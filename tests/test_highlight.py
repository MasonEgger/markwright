# ABOUTME: Tests for the highlight extension converting <^>text<^> to <mark> tags.
# Covers inline text, inline code, fenced code blocks, and edge cases.

import re

import markdown


def _render(source: str) -> str:
    """Render Markdown source with the highlight extension loaded."""
    md = markdown.Markdown(extensions=["do_markdown.highlight"])
    return md.convert(source)


def _render_with_superfences(source: str) -> str:
    """Render with highlight + superfences, matching the real site stack."""
    md = markdown.Markdown(
        extensions=["pymdownx.superfences", "pymdownx.highlight", "do_markdown.highlight"],
        extension_configs={"pymdownx.highlight": {"pygments_lang_class": True}},
    )
    return md.convert(source)


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
        assert "&lt;^&gt;literal&lt;^&gt;" in result

    def test_escaped_markers_in_inline_code(self) -> None:
        result = _render(r"Write `\<^>text\<^>` to highlight.")
        assert "<mark>" not in result
        assert "<code>&lt;^&gt;text&lt;^&gt;</code>" in result

    def test_escaped_and_real_markers_coexist(self) -> None:
        source = "```\n" + r"\<^>shown\<^> and <^>marked<^>" + "\n```"
        result = _render_with_superfences(source)
        assert "&lt;^&gt;shown&lt;^&gt;" in result
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
