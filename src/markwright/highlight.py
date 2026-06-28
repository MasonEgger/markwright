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
        highlighted = _ESCAPED_HIGHLIGHT_RE.sub(_wrap_highlight_segments, text)
        # Reveal escaped markers as literal ``<^>`` by dropping the backslash.
        return _BACKSLASH_MARKER_RE.sub("&lt;^&gt;", highlighted)


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
