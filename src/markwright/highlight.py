# ABOUTME: Highlight extension converting <^>text<^> to <mark> tags.
# Works in regular text, inline code, and fenced code blocks.

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from xml.etree import ElementTree

from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor
from markdown.postprocessors import Postprocessor

from markwright._fences import map_prose
from markwright._html import RAW_TEXT_ELEMENTS, apply_edits, tokenize

if TYPE_CHECKING:
    from collections.abc import Mapping

    from markdown import Markdown

# A backslash before a marker (``\<^>``) escapes it. The in-process InlineProcessor shares this guard
# so the escape survives as a literal marker no matter which stage resolves it.
_ESCAPE_GUARD = r"(?<!\\)"
_HIGHLIGHT_PATTERN = rf"{_ESCAPE_GUARD}<\^>(.*?){_ESCAPE_GUARD}<\^>"
# Markers are HTML-escaped to ``&lt;^&gt;`` inside code.
_ESCAPED_MARKER_RE = re.compile(r"&lt;\^&gt;")
# A revealed literal marker writes the caret as a character reference, so a second ``mw post`` does not
# read it as a marker again.
_LITERAL_CARET = "&#94;"

# Source-stage (``mw pre``) markers operate on raw, un-escaped text: the backslashes before each marker
# are captured so their parity decides whether the marker is an escape.
_PROSE_MARKER_RE = re.compile(r"(\\*)<\^>")


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


def _visible_text(rendered_html: str) -> tuple[str, list[int]]:
    """Join the rendered text with every tag removed, remembering where each character came from.

    A syntax highlighter may put a tag between a backslash and a marker, or inside the marker itself,
    so markers and escapes are read from this text rather than from one text token at a time.

    :param rendered_html: Rendered HTML content.
    :returns: The joined text, and for each of its characters the offset it has in ``rendered_html``.
    """
    spans = _text_token_spans(rendered_html)
    visible = "".join(rendered_html[span_start:span_end] for span_start, span_end in spans)
    offsets = [offset for span_start, span_end in spans for offset in range(span_start, span_end)]
    return visible, offsets


def apply_html(
    rendered_html: str, skip_reasons: list[str] | None = None, options: Mapping[str, object] | None = None
) -> str:
    """Convert HTML-escaped ``&lt;^&gt;`` markers in rendered text to ``<mark>``.

    The HTML-stage transform for ``mw post`` and the in-process postprocessor. Markers and
    escapes are read from the text with the tags taken out, so a marker pairs and a backslash
    escapes it whatever tags a syntax highlighter puts between or inside them. A marker pairs with
    the next marker on the same line. Each run of text between a pair is wrapped in its own
    ``<mark>``, the marker characters are removed, and every tag stays where it was (a ``<span>``
    that held only part of a marker remains, empty), so the markup stays well-formed. A marker
    directly after a backslash is an escape: the backslash is removed and the marker is revealed as
    a literal ``&lt;&#94;&gt;``, which a second pass leaves alone.

    :param rendered_html: Rendered HTML content.
    :param skip_reasons: Ignored (highlighting never skips anything); accepted so the registry calls
        every post stage with one signature.
    :param options: Ignored; accepted so the registry calls every post stage with one signature.
    :returns: HTML with escaped highlight markers converted to ``<mark>``.
    """
    visible, offsets = _visible_text(rendered_html)
    edits: list[tuple[int, int, str]] = []

    # Separate the escapes from the live markers; an escape drops its backslash and writes its caret as a reference
    live_markers: list[tuple[int, int]] = []
    for marker_match in _ESCAPED_MARKER_RE.finditer(visible):
        marker_start, marker_end = marker_match.span()
        if marker_start and visible[marker_start - 1] == "\\":
            backslash_offset = offsets[marker_start - 1]
            # The caret follows the four characters of "&lt;"
            caret_offset = offsets[marker_start + 4]
            edits.append((backslash_offset, backslash_offset + 1, ""))
            edits.append((caret_offset, caret_offset + 1, _LITERAL_CARET))
        else:
            live_markers.append((marker_start, marker_end))

    # Pair each live marker with the next one on the same line, wrapping every run of text between them
    marker_index = 0
    while marker_index + 1 < len(live_markers):
        (open_start, open_end), (close_start, close_end) = live_markers[marker_index], live_markers[marker_index + 1]
        if "\n" in visible[open_end:close_start]:
            marker_index += 1
            continue

        # Source spans of the text between the pair; tags between runs are kept as they are
        runs: list[tuple[int, int]] = []
        for offset in offsets[open_end:close_start]:
            if runs and runs[-1][1] == offset:
                runs[-1] = (runs[-1][0], offset + 1)
            else:
                runs.append((offset, offset + 1))
        for run_start, run_end in runs:
            edits.append((run_start, run_start, "<mark>"))
            edits.append((run_end, run_end, "</mark>"))
        if not runs:
            edits.append((offsets[open_start], offsets[open_start], "<mark></mark>"))

        edits.extend(
            (offset, offset + 1, "") for offset in (*offsets[open_start:open_end], *offsets[close_start:close_end])
        )
        marker_index += 2
    return apply_edits(rendered_html, edits)


def _wrap_prose_markers(prose: str) -> str:
    """Wrap prose markers in ``<mark>`` and write each escaped marker in a form both renderers hand back.

    The backslashes before a marker are read in pairs: an even run leaves the marker live, an odd run
    escapes it. For an escape one backslash is added and the marker's ``<`` is written ``&lt;``, so
    Python-Markdown and a CommonMark renderer both render a backslash and a literal marker, which
    :func:`apply_html` then reveals. A live marker pairs with the next live marker on the same line.

    :param prose: A run of prose from outside code.
    :returns: The prose with live pairs wrapped and escapes rewritten.
    """
    edits: list[tuple[int, int, str]] = []
    live_markers: list[tuple[int, int]] = []
    for marker_match in _PROSE_MARKER_RE.finditer(prose):
        marker_start = marker_match.end(1)
        if len(marker_match.group(1)) % 2:
            edits.append((marker_start, marker_start + 1, "\\&lt;"))
        else:
            live_markers.append((marker_start, marker_match.end()))

    marker_index = 0
    while marker_index + 1 < len(live_markers):
        (open_start, open_end), (close_start, close_end) = live_markers[marker_index], live_markers[marker_index + 1]
        if "\n" in prose[open_end:close_start]:
            marker_index += 1
            continue
        edits.extend([(open_start, open_end, "<mark>"), (close_start, close_end, "</mark>")])
        marker_index += 2
    return apply_edits(prose, edits)


def expand_source(text: str, options: Mapping[str, object] | None = None) -> str:
    """Wrap prose highlight markers in ``<mark>`` outside code.

    The source-stage transform for ``mw pre``. Fenced code blocks (found by the shared CommonMark
    scanner the fence stage uses) and inline code spans are left untouched: their markers are
    HTML-escaped during rendering and resolved by :func:`apply_html` in the post stage. In prose an
    odd run of backslashes before a marker escapes it and is rewritten as ``mw post`` expects (see
    :func:`_wrap_prose_markers`); an even run leaves the marker live.

    :param text: Raw Markdown source.
    :param options: Ignored; accepted so the registry calls every pre stage with one signature.
    :returns: Source with unescaped prose ``<^>...<^>`` markers wrapped in ``<mark>``.
    """
    return map_prose(text, _wrap_prose_markers)


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
