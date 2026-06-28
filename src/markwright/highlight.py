# ABOUTME: Highlight extension converting <^>text<^> to <mark> tags.
# Works in regular text, inline code, and fenced code blocks.

from __future__ import annotations

import re
import xml.etree.ElementTree as etree

from markdown import Markdown
from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor
from markdown.postprocessors import Postprocessor

_HIGHLIGHT_PATTERN = r"<\^>(.*?)<\^>"
# Markers are HTML-escaped to ``&lt;^&gt;`` inside code. A backslash before a
# marker (``\<^>``) escapes it, so neither lookbehind-guarded marker matches.
_ESCAPED_HIGHLIGHT_RE = re.compile(r"(?<!\\)&lt;\^&gt;(.*?)(?<!\\)&lt;\^&gt;")
_BACKSLASH_MARKER_RE = re.compile(r"\\&lt;\^&gt;")
_HTML_TAG_RE = re.compile(r"<[^>]+>")

# Source-stage (``mw pre``) markers operate on raw, un-escaped text. They mirror
# the escaped post-stage regexes above: a backslash before a marker escapes it.
_PROSE_HIGHLIGHT_RE = re.compile(r"(?<!\\)<\^>(.*?)(?<!\\)<\^>")
_PROSE_BACKSLASH_MARKER_RE = re.compile(r"\\<\^>")
# Code regions the pre stage must skip: fenced code blocks and inline code
# spans. Markers inside code are HTML-escaped during rendering and handled by
# :func:`apply_html` in the post stage instead.
_CODE_REGION_RE = re.compile(
    r"(?P<fence>^```[^\n]*\n.*?^```)|(?P<inline>`[^`\n]*`)",
    re.DOTALL | re.MULTILINE,
)


def _wrap_highlight_segments(match: re.Match[str]) -> str:
    """Wrap the text between escaped markers in ``<mark>`` without crossing tags.

    Syntax highlighters such as Pygments wrap code in ``<span>`` tokens, so the
    region between two markers may contain tag boundaries. Wrapping the whole
    region in a single ``<mark>`` would produce overlapping HTML; instead each
    run of plain text is wrapped individually, leaving the intervening tags
    untouched and the markup well-formed.

    :param match: A match of :data:`_ESCAPED_HIGHLIGHT_RE`.
    :returns: The marked-up replacement for the matched region.
    """
    region = match.group(1)
    if not region:
        return "<mark></mark>"

    rebuilt_parts: list[str] = []
    text_cursor = 0
    for tag_match in _HTML_TAG_RE.finditer(region):
        text_run = region[text_cursor : tag_match.start()]
        if text_run:
            rebuilt_parts.append(f"<mark>{text_run}</mark>")
        rebuilt_parts.append(tag_match.group(0))
        text_cursor = tag_match.end()
    trailing_text = region[text_cursor:]
    if trailing_text:
        rebuilt_parts.append(f"<mark>{trailing_text}</mark>")
    return "".join(rebuilt_parts)


def apply_html(html: str, warnings: list[str] | None = None) -> str:
    """Convert HTML-escaped ``&lt;^&gt;`` markers in rendered HTML to ``<mark>``.

    The HTML-stage transform for ``mw post`` and the in-process postprocessor.
    Escaped markers inside rendered code are wrapped span-safely (see
    :func:`_wrap_highlight_segments`); backslash-escaped markers are revealed as
    a literal ``&lt;^&gt;``.

    :param html: Rendered HTML content.
    :param warnings: Optional warnings list; unused (highlighting never warns).
    :returns: HTML with escaped highlight markers converted to ``<mark>``.
    """
    highlighted = _ESCAPED_HIGHLIGHT_RE.sub(_wrap_highlight_segments, html)
    return _BACKSLASH_MARKER_RE.sub("&lt;^&gt;", highlighted)


def _highlight_prose(segment: str) -> str:
    """Wrap prose ``<^>...<^>`` markers in ``<mark>``, honoring backslash escapes.

    :param segment: A run of source text known to be outside any code region.
    :returns: The segment with un-escaped markers wrapped and backslash-escaped
        markers revealed as a literal ``<^>``.
    """
    marked = _PROSE_HIGHLIGHT_RE.sub(r"<mark>\1</mark>", segment)
    return _PROSE_BACKSLASH_MARKER_RE.sub("<^>", marked)


def expand_source(text: str) -> str:
    """Wrap prose highlight markers in ``<mark>`` outside code regions.

    The source-stage transform for ``mw pre``. Fenced code blocks and inline
    code spans are left untouched: their markers are HTML-escaped during
    rendering and converted by :func:`apply_html` in the post stage.

    :param text: Raw Markdown source.
    :returns: Source with prose ``<^>...<^>`` markers wrapped in ``<mark>``.
    """
    result_parts: list[str] = []
    last_end = 0
    for code_match in _CODE_REGION_RE.finditer(text):
        result_parts.append(_highlight_prose(text[last_end : code_match.start()]))
        result_parts.append(code_match.group(0))
        last_end = code_match.end()
    result_parts.append(_highlight_prose(text[last_end:]))
    return "".join(result_parts)


class HighlightInlineProcessor(InlineProcessor):
    """Inline processor that converts ``<^>text<^>`` to ``<mark>text</mark>``.

    :param pattern: Regex pattern for matching highlight markers.
    :param md: The Markdown instance.
    """

    def handleMatch(self, match: re.Match[str], data: str) -> tuple[etree.Element, int, int]:  # type: ignore[override]
        """Create a ``<mark>`` element from the matched text.

        :param match: The regex match object.
        :param data: The full source string being processed.
        :returns: A tuple of (element, start, end).
        """
        mark_element = etree.Element("mark")
        mark_element.text = match.group(1)
        return mark_element, match.start(0), match.end(0)


class HighlightPostprocessor(Postprocessor):
    """Postprocessor that replaces HTML-escaped ``<^>`` markers in rendered code blocks.

    Code blocks render ``<`` and ``>`` as ``&lt;`` and ``&gt;``, so the inline
    processor cannot reach them. This postprocessor catches those escaped markers
    in the final HTML and converts them to ``<mark>`` tags.
    """

    def run(self, text: str) -> str:
        """Replace escaped highlight markers with ``<mark>`` tags.

        :param text: The rendered HTML string.
        :returns: HTML with highlight markers replaced.
        """
        return apply_html(text)


class HighlightExtension(Extension):
    """Python-Markdown extension for ``<^>text<^>`` highlight syntax.

    Registers an :class:`HighlightInlineProcessor` for regular inline text and a
    :class:`HighlightPostprocessor` for code blocks where markers are HTML-escaped.
    """

    def extendMarkdown(self, md: Markdown) -> None:
        """Register the highlight processors with the Markdown instance.

        :param md: The Markdown instance to extend.
        """
        md.inlinePatterns.register(
            HighlightInlineProcessor(_HIGHLIGHT_PATTERN, md),
            "do_highlight_inline",
            175,
        )
        md.postprocessors.register(
            HighlightPostprocessor(md),
            "do_highlight_post",
            25,
        )


def makeExtension(**kwargs: str) -> HighlightExtension:
    """Entry point for Python-Markdown extension loading.

    :param kwargs: Extension configuration options.
    :returns: A configured HighlightExtension instance.
    """
    return HighlightExtension(**kwargs)
