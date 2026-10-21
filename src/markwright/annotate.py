# ABOUTME: Annotate extension linking (N) markers in a block to the items of the ordered list after it.
# Carries the request in an mw-annotate marker comment from the pre stage to the post stage.

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor
from markdown.preprocessors import Preprocessor
from pydantic import BaseModel, ConfigDict

from markwright._html import (
    RAW_TEXT_ELEMENTS,
    HtmlToken,
    add_classes,
    apply_edits,
    matching_end,
    render_start_tag,
    tokenize,
)
from markwright._markers import InvalidMarkerError, decode_marker, encode_marker, find_markers

if TYPE_CHECKING:
    from collections.abc import Mapping

    from markdown import Markdown

MARKER_NAME = "mw-annotate"
BLOCK_CLASS = "mw-annotated"
LIST_CLASS = "mw-annotations"
LINK_CLASS = "mw-annotation"
CONTRACT_VERSION = "1"

ANNOTATE_RE = re.compile(r"^\[annotate\]$")
MARKER_RE = re.compile(r"\((?P<number>\d+)\)(?P<bang>!?)")

# Pygments and Chroma class a comment span with one of these (c1 is a single-line comment)
COMMENT_CLASSES = frozenset({"c", "c1", "cm", "cp", "cpf", "cs", "ch"})


class AnnotateMarker(BaseModel):
    """A validated v1 mw-annotate marker payload.

    Strict, so a field of the wrong type fails validation instead of being coerced; unknown
    fields are ignored.

    :ivar version: The payload version, ``1``.
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="ignore")

    version: int


def _expand_lines(lines: list[str]) -> list[str]:
    """Replace each ``[annotate]`` line with a marker comment and a blank line.

    :param lines: Source lines to process.
    :returns: The lines with annotate directives replaced by mw-annotate markers, indented as the directive was.
    """
    output: list[str] = []
    for line in lines:
        if ANNOTATE_RE.match(line.strip()) is None:
            output.append(line)
            continue
        indent = line[: len(line) - len(line.lstrip())]
        output.append(f"{indent}{encode_marker(MARKER_NAME, {})}")
        output.append("")
    return output


def expand_source(text: str, options: Mapping[str, object] | None = None) -> str:
    """Replace annotate directives with mw-annotate marker comments in raw source.

    Used by the ``mw pre`` CLI stage.

    :param text: The source text.
    :param options: Accepted for the registry's shared signature; annotate has no options.
    :returns: The text with annotate directives replaced by markers.
    """
    return "\n".join(_expand_lines(text.split("\n")))


def _locate(rendered_html: str, tokens: list[HtmlToken], token_index: int, block_end: int) -> tuple[int, int, int, int]:
    """Find the annotated block and the annotation list that follows a marker.

    The block is the first element after the marker; the list is the first thing after the block
    that is not a comment or whitespace, and it must be an ``<ol>``.

    :param rendered_html: The HTML the tokens were produced from.
    :param tokens: The tokens of ``rendered_html``.
    :param token_index: Index of the marker comment.
    :param block_end: Index where the marker's region ends (the next marker, or the token count).
    :returns: Token indexes of the block's start and end tags, then of the list's start and end tags.
    :raises InvalidMarkerError: If no closed block follows, or no closed ``<ol>`` follows the block.
    """
    block_start = next(
        (index for index in range(token_index + 1, block_end) if tokens[index].kind == "start"),
        None,
    )
    block_close = None if block_start is None else matching_end(tokens, block_start)
    if block_start is None or block_close is None:
        raise InvalidMarkerError(f"Skipping {MARKER_NAME} marker with no following block")

    list_start = next(
        (
            index
            for index in range(block_close + 1, len(tokens))
            if tokens[index].kind != "comment"
            and not (
                tokens[index].kind == "text" and not rendered_html[tokens[index].start : tokens[index].end].strip()
            )
        ),
        None,
    )
    list_close = None
    if list_start is not None and tokens[list_start].kind == "start" and tokens[list_start].tag == "ol":
        list_close = matching_end(tokens, list_start)
    if list_start is None or list_close is None:
        raise InvalidMarkerError(f"Skipping {MARKER_NAME} marker with no annotation list after the block")
    return block_start, block_close, list_start, list_close


def _enclosing_comment_span(tokens: list[HtmlToken], token_index: int) -> tuple[HtmlToken, HtmlToken] | None:
    """Find the syntax-highlighter comment span that holds a text token and nothing else.

    :param tokens: The tokens of the page.
    :param token_index: Index of a text token with a token on each side.
    :returns: The span's start and end tags, or ``None`` when the text is not alone in a comment span.
    """
    opening = tokens[token_index - 1]
    closing = tokens[token_index + 1]
    is_comment_span = (
        opening.kind == "start"
        and opening.tag == "span"
        and not COMMENT_CLASSES.isdisjoint((opening.attribute("class") or "").split())
        and closing.kind == "end"
        and closing.tag == "span"
    )
    return (opening, closing) if is_comment_span else None


def _apply_markers(rendered_html: str, skip_reasons: list[str] | None) -> str:
    """Annotate the block after each mw-annotate marker, then remove the marker.

    A marker is skipped (and optionally reported) when its payload is invalid, no block follows
    it, or no ``<ol>`` follows the block. A recognized marker comment is always removed.

    :param rendered_html: Rendered HTML containing mw-annotate marker comments.
    :param skip_reasons: Optional list collecting skip reasons; ``None`` drops them.
    :returns: HTML with the annotations linked.
    """
    tokens = tokenize(rendered_html)
    edits: list[tuple[int, int, str]] = []
    block_number = 0
    for marker_comment in find_markers(MARKER_NAME, rendered_html, tokens):
        comment = tokens[marker_comment.token_index]
        edits.append((comment.start, comment.end, ""))

        try:
            decode_marker(MARKER_NAME, marker_comment.raw_payload, AnnotateMarker)
            block_start, block_close, list_start, list_close = _locate(
                rendered_html, tokens, marker_comment.token_index, marker_comment.block_end
            )
        except InvalidMarkerError as skipped:
            if skip_reasons is not None:
                skip_reasons.append(str(skipped))
            continue

        block_number += 1
        list_tag = tokens[list_start]
        edits.append(
            (list_tag.start, list_tag.end, add_classes(list_tag, LIST_CLASS, (("data-mw-version", CONTRACT_VERSION),)))
        )

        item_count = 0
        list_depth = 0
        for token in tokens[list_start + 1 : list_close]:
            if token.tag in ("ul", "ol"):
                list_depth += 1 if token.kind == "start" else -1
            elif token.tag == "li" and token.kind == "start" and list_depth == 0:
                item_count += 1
                item_id = f"mw-annotation-{block_number}-{item_count}"
                edits.append((token.start, token.end, render_start_tag("li", (("id", item_id), *token.attrs))))

        block_tag = tokens[block_start]
        edits.append((block_tag.start, block_tag.end, add_classes(block_tag, BLOCK_CLASS)))

        for token_index in range(block_start + 1, block_close):
            token = tokens[token_index]
            previous = tokens[token_index - 1]
            if token.kind != "text" or (previous.kind == "start" and previous.tag in RAW_TEXT_ELEMENTS):
                continue
            text = rendered_html[token.start : token.end]
            for marker_match in MARKER_RE.finditer(text):
                number = int(marker_match.group("number"))
                if not 1 <= number <= item_count:
                    continue
                link = f'<a class="{LINK_CLASS}" href="#mw-annotation-{block_number}-{number}">{number}</a>'
                comment_span = _enclosing_comment_span(tokens, token_index) if marker_match.group("bang") else None
                if comment_span is None:
                    edits.append((token.start + marker_match.start(), token.start + marker_match.end(), link))
                    continue
                # Dropping a newline the comment carries would merge two code lines
                line_break = "\n" if text.endswith("\n") else ""
                edits.append((comment_span[0].start, comment_span[1].end, link + line_break))
                break

    return apply_edits(rendered_html, edits)


def apply_html(
    rendered_html: str, skip_reasons: list[str] | None = None, options: Mapping[str, object] | None = None
) -> str:
    """Link annotation markers from their mw-annotate marker comments.

    Used by the ``mw post`` CLI stage. Markers are validated and skipped fail-soft;
    pass a ``skip_reasons`` list to collect why.

    :param rendered_html: Rendered HTML containing mw-annotate marker comments.
    :param skip_reasons: Optional list collecting skip reasons; ``None`` drops them.
    :param options: Accepted for the registry's shared signature; annotate has no options.
    :returns: HTML with the blocks, lists, and markers annotated and the markers removed.
    """
    return _apply_markers(rendered_html, skip_reasons)


class AnnotatePreprocessor(Preprocessor):
    """Replace annotate directives with mw-annotate marker comments."""

    def run(self, lines: list[str]) -> list[str]:
        """Process lines, replacing annotate directives with markers.

        :param lines: Source lines to process.
        :returns: Modified lines.
        """
        return _expand_lines(lines)


class AnnotatePostprocessor(Postprocessor):
    """Annotate the blocks that follow mw-annotate markers."""

    def run(self, text: str) -> str:
        """Process rendered HTML, linking annotations and removing the markers.

        :param text: Rendered HTML string.
        :returns: Modified HTML.
        """
        return _apply_markers(text, None)


class AnnotateExtension(Extension):
    """Python-Markdown extension for annotations."""

    def extendMarkdown(self, md: Markdown) -> None:  # noqa: N802 - Python-Markdown's hook name
        """Register the annotate preprocessor and postprocessor.

        The postprocessor outranks the fence one (25), so the fence marker is still a comment
        when the annotated block is located.

        :param md: The Markdown instance to extend.
        """
        md.preprocessors.register(AnnotatePreprocessor(md), "mw-annotate-pre", 20)
        md.postprocessors.register(AnnotatePostprocessor(md), "mw-annotate-post", 30)


def makeExtension(**kwargs: object) -> AnnotateExtension:  # noqa: N802 - Python-Markdown's loader name
    """Create and return the AnnotateExtension instance.

    :param \\*\\*kwargs: Configuration options.
    :returns: A configured AnnotateExtension.
    """
    return AnnotateExtension(**kwargs)
