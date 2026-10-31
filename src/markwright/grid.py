# ABOUTME: Grid extension turning a [grid] or [grid cards] line into mw-grid classes on the next list.
# Carries the request in an mw-grid marker comment from the pre stage to the post stage.

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor
from markdown.preprocessors import Preprocessor
from pydantic import BaseModel, ConfigDict

from markwright._fences import map_lines
from markwright._html import add_classes, apply_edits, tokenize
from markwright._markers import InvalidMarkerError, decode_marker, encode_marker, find_markers

if TYPE_CHECKING:
    from collections.abc import Mapping

    from markdown import Markdown

MARKER_NAME = "mw-grid"
GRID_CLASS = "mw-grid"
CARDS_CLASS = "mw-cards"

GRID_RE = re.compile(r"^\[grid(?P<cards>\s+cards)?\]$")


class GridMarker(BaseModel):
    """A validated v1 mw-grid marker payload.

    Strict, so a field of the wrong type fails validation instead of being coerced; unknown
    fields are ignored.

    :ivar version: The payload version, ``1``.
    :ivar cards: Whether the list renders as cards.
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="ignore")

    version: int
    cards: bool = False


def _transform_line(line: str) -> list[str]:
    """Replace a ``[grid]`` or ``[grid cards]`` line with a marker comment and a blank line.

    :param line: A single source line.
    :returns: The marker comment and a blank line for a grid directive, else the line unchanged.
    """
    grid_match = GRID_RE.match(line.strip())
    if grid_match is None:
        return [line]
    indent = line[: len(line) - len(line.lstrip())]
    payload = {"cards": True} if grid_match.group("cards") else {}
    return [f"{indent}{encode_marker(MARKER_NAME, payload)}", ""]


def expand_source(text: str, options: Mapping[str, object] | None = None) -> str:
    """Replace grid directives with mw-grid marker comments in raw source.

    Used by the ``mw pre`` CLI stage. A directive inside a fenced code block is left literal.

    :param text: The source text.
    :param options: Accepted for the registry's shared signature; grid has no options.
    :returns: The text with grid directives replaced by markers.
    """
    return map_lines(text, _transform_line)


def _apply_markers(rendered_html: str, skip_reasons: list[str] | None) -> str:
    """Class the list after each mw-grid marker, then remove the marker.

    A marker is skipped (and optionally reported) when its payload is invalid or no list
    follows it before the next marker. A recognized marker comment is always removed.

    :param rendered_html: Rendered HTML containing mw-grid marker comments.
    :param skip_reasons: Optional list collecting skip reasons; ``None`` drops them.
    :returns: HTML with the grid classes added.
    """
    tokens = tokenize(rendered_html)
    edits: list[tuple[int, int, str]] = []
    for marker_comment in find_markers(MARKER_NAME, rendered_html, tokens):
        comment = tokens[marker_comment.token_index]
        edits.append((comment.start, comment.end, ""))

        block = tokens[marker_comment.token_index + 1 : marker_comment.block_end]
        list_tag = next((token for token in block if token.kind == "start" and token.tag in ("ul", "ol")), None)

        try:
            marker = decode_marker(MARKER_NAME, marker_comment.raw_payload, GridMarker)
            if list_tag is None:
                raise InvalidMarkerError(f"Skipping {MARKER_NAME} marker with no following list")
        except InvalidMarkerError as skipped:
            if skip_reasons is not None:
                skip_reasons.append(str(skipped))
            continue

        grid_classes = f"{GRID_CLASS} {CARDS_CLASS}" if marker.cards else GRID_CLASS
        edits.append((list_tag.start, list_tag.end, add_classes(list_tag, grid_classes)))

    return apply_edits(rendered_html, edits)


def apply_html(
    rendered_html: str, skip_reasons: list[str] | None = None, options: Mapping[str, object] | None = None
) -> str:
    """Class lists from their mw-grid marker comments.

    Used by the ``mw post`` CLI stage. Markers are validated and skipped fail-soft;
    pass a ``skip_reasons`` list to collect why.

    :param rendered_html: Rendered HTML containing mw-grid marker comments.
    :param skip_reasons: Optional list collecting skip reasons; ``None`` drops them.
    :param options: Accepted for the registry's shared signature; grid has no options.
    :returns: HTML with ``mw-grid`` classes on the marked lists and the markers removed.
    """
    return _apply_markers(rendered_html, skip_reasons)


class GridPreprocessor(Preprocessor):
    """Replace grid directives with mw-grid marker comments."""

    def run(self, lines: list[str]) -> list[str]:
        """Process lines, replacing grid directives with markers.

        :param lines: Source lines to process.
        :returns: Modified lines.
        """
        return [output_line for line in lines for output_line in _transform_line(line)]


class GridPostprocessor(Postprocessor):
    """Class the lists that follow mw-grid markers."""

    def run(self, text: str) -> str:
        """Process rendered HTML, classing marked lists and removing the markers.

        :param text: Rendered HTML string.
        :returns: Modified HTML.
        """
        return _apply_markers(text, None)


class GridExtension(Extension):
    """Python-Markdown extension for grid lists."""

    def extendMarkdown(self, md: Markdown) -> None:  # noqa: N802 - Python-Markdown's hook name
        """Register the grid preprocessor and postprocessor.

        :param md: The Markdown instance to extend.
        """
        md.preprocessors.register(GridPreprocessor(md), "mw-grid-pre", 20)
        md.postprocessors.register(GridPostprocessor(md), "mw-grid-post", 30)


def makeExtension(**kwargs: object) -> GridExtension:  # noqa: N802 - Python-Markdown's loader name
    """Create and return the GridExtension instance.

    :param \\*\\*kwargs: Configuration options.
    :returns: A configured GridExtension.
    """
    return GridExtension(**kwargs)
