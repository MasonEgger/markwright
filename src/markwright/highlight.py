# ABOUTME: Highlight extension converting <^>text<^> to <mark> tags.
# Works in regular text, inline code, and fenced code blocks.

from __future__ import annotations

import itertools
import re
from typing import TYPE_CHECKING
from xml.etree import ElementTree

from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor
from markdown.postprocessors import Postprocessor

from markwright._fences import find_fenced_blocks
from markwright._html import RAW_TEXT_ELEMENTS, apply_edits, tokenize

if TYPE_CHECKING:
    from collections.abc import Mapping

    from markdown import Markdown

# A backslash before a marker (``\<^>``) escapes it. Every consumer (the
# in-process InlineProcessor, the escaped post-stage regex, and the prose
# pre-stage regex) shares this guard so the escape survives as a literal
# marker no matter which stage resolves it.
_ESCAPE_GUARD = r"(?<!\\)"
_HIGHLIGHT_PATTERN = rf"{_ESCAPE_GUARD}<\^>(.*?){_ESCAPE_GUARD}<\^>"
# Markers are HTML-escaped to ``&lt;^&gt;`` inside code.
_ESCAPED_MARKER_RE = re.compile(rf"{_ESCAPE_GUARD}&lt;\^&gt;")
_BACKSLASH_MARKER_RE = re.compile(r"\\&lt;\^&gt;")

# Source-stage (``mw pre``) markers operate on raw, un-escaped text. They mirror
# the escaped post-stage regex above.
_PROSE_HIGHLIGHT_RE = re.compile(rf"{_ESCAPE_GUARD}<\^>(.*?){_ESCAPE_GUARD}<\^>")
# An inline code span: a backtick run, content, and a closing run of exactly the same length.
# Markers inside code are HTML-escaped during rendering and handled by :func:`apply_html` instead.
_INLINE_CODE_RE = re.compile(r"(?<!`)(?P<ticks>`+)(?!`).+?(?<!`)(?P=ticks)(?!`)")


def _text_token_spans(rendered_html: str) -> list[tuple[int, int]]:
    """Return the spans of rendered text, the only place an escaped marker can be.

    Tag attributes and the contents of ``<script>`` and ``<style>`` are excluded, so a marker
    inside, say, a ``title`` attribute is never touched.

    :param rendered_html: Rendered HTML content.
    :returns: ``(start, end)`` spans of text tokens in source order.
    """
    tokens = tokenize(rendered_html)
    return [
        (token.start, token.end)
        for previous_token, token in zip([None, *tokens], tokens, strict=False)
        if token.kind == "text"
        and not (previous_token and previous_token.kind == "start" and previous_token.tag in RAW_TEXT_ELEMENTS)
    ]


def apply_html(
    rendered_html: str, skip_reasons: list[str] | None = None, options: Mapping[str, object] | None = None
) -> str:
    """Convert HTML-escaped ``&lt;^&gt;`` markers in rendered text to ``<mark>``.

    The HTML-stage transform for ``mw post`` and the in-process postprocessor. A marker pairs
    with the next marker on the same line. Syntax highlighters wrap code in ``<span>`` tokens,
    so each run of text between a pair is wrapped in its own ``<mark>`` and the tags between
    are left untouched, keeping the markup well-formed. Backslash-escaped markers are then
    revealed as a literal ``&lt;^&gt;``.

    :param rendered_html: Rendered HTML content.
    :param skip_reasons: Ignored (highlighting never skips anything); accepted so the registry calls
        every post stage with one signature.
    :param options: Ignored; accepted so the registry calls every post stage with one signature.
    :returns: HTML with escaped highlight markers converted to ``<mark>``.
    """
    text_spans = _text_token_spans(rendered_html)
    markers = [
        (marker_match.start(), marker_match.end())
        for span_start, span_end in text_spans
        for marker_match in _ESCAPED_MARKER_RE.finditer(rendered_html, span_start, span_end)
    ]

    # Pair each marker with the next one on the same line, wrapping every text run between them
    edits: list[tuple[int, int, str]] = []
    marker_index = 0
    while marker_index + 1 < len(markers):
        (open_start, region_start), (region_end, close_end) = markers[marker_index], markers[marker_index + 1]
        if "\n" in rendered_html[region_start:region_end]:
            marker_index += 1
            continue
        region_parts: list[str] = []
        cursor = region_start
        for span_start, span_end in text_spans:
            text_start, text_end = max(span_start, region_start), min(span_end, region_end)
            if text_start >= text_end:
                continue
            # Markup between text runs (syntax-highlight spans) is kept as is
            region_parts.append(rendered_html[cursor:text_start])
            region_parts.append(f"<mark>{rendered_html[text_start:text_end]}</mark>")
            cursor = text_end
        region_parts.append(rendered_html[cursor:region_end])
        edits.append((open_start, close_end, "".join(region_parts) or "<mark></mark>"))
        marker_index += 2
    highlighted = apply_edits(rendered_html, edits)

    # Reveal backslash-escaped markers, again only in text
    unescape_edits = [
        (escape_match.start(), escape_match.end(), "&lt;^&gt;")
        for span_start, span_end in _text_token_spans(highlighted)
        for escape_match in _BACKSLASH_MARKER_RE.finditer(highlighted, span_start, span_end)
    ]
    return apply_edits(highlighted, unescape_edits)


def expand_source(text: str, options: Mapping[str, object] | None = None) -> str:
    """Wrap prose highlight markers in ``<mark>`` outside code.

    The source-stage transform for ``mw pre``. Fenced code blocks (found by the shared CommonMark
    scanner the fence stage uses), inline code spans, and backslash-escaped markers are left
    untouched: they are HTML-escaped during rendering and resolved by :func:`apply_html` in the
    post stage. Resolving an escape here would strip the backslash before the renderer sees it,
    and the renderer's escaping of the exposed marker would then look like a genuine marker.

    :param text: Raw Markdown source.
    :param options: Ignored; accepted so the registry calls every pre stage with one signature.
    :returns: Source with unescaped prose ``<^>...<^>`` markers wrapped in ``<mark>``.
    """
    lines = text.split("\n")
    fenced_lines = {
        line_index for block in find_fenced_blocks(lines) for line_index in range(block.opening, block.closing + 1)
    }

    output_chunks: list[str] = []
    for is_fenced, line_group in itertools.groupby(enumerate(lines), key=lambda entry: entry[0] in fenced_lines):
        chunk = "\n".join(line for _, line in line_group)
        if is_fenced:
            output_chunks.append(chunk)
            continue

        # Within prose, inline code spans are skipped as well
        highlighted_parts: list[str] = []
        cursor = 0
        for code_span in _INLINE_CODE_RE.finditer(chunk):
            highlighted_parts.append(_PROSE_HIGHLIGHT_RE.sub(r"<mark>\1</mark>", chunk[cursor : code_span.start()]))
            highlighted_parts.append(code_span.group(0))
            cursor = code_span.end()
        highlighted_parts.append(_PROSE_HIGHLIGHT_RE.sub(r"<mark>\1</mark>", chunk[cursor:]))
        output_chunks.append("".join(highlighted_parts))
    return "\n".join(output_chunks)


class HighlightInlineProcessor(InlineProcessor):
    """Inline processor that converts ``<^>text<^>`` to ``<mark>text</mark>``.

    :param pattern: Regex pattern for matching highlight markers.
    :param md: The Markdown instance.
    """

    # Python-Markdown names this hook, and its stubs type it as the older Pattern.handleMatch(m), so the
    # InlineProcessor signature it is called with at runtime needs the override ignore
    def handleMatch(self, match: re.Match[str], data: str) -> tuple[ElementTree.Element, int, int]:  # type: ignore[override]  # noqa: N802
        """Create a ``<mark>`` element from the matched text.

        :param match: The regex match object.
        :param data: The full source string being processed.
        :returns: A tuple of (element, start, end).
        """
        mark_element = ElementTree.Element("mark")
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

    def extendMarkdown(self, md: Markdown) -> None:  # noqa: N802 - Python-Markdown's hook name
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


def makeExtension(**kwargs: object) -> HighlightExtension:  # noqa: N802 - Python-Markdown's loader name
    """Entry point for Python-Markdown extension loading.

    :param \\*\\*kwargs: Extension configuration options.
    :returns: A configured HighlightExtension instance.
    """
    return HighlightExtension(**kwargs)
