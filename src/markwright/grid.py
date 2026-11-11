# ABOUTME: Grid extension turning a [grid], [grid cards], or [grid N] opener line into mw-grid classes on the next list.
# Carries the request in an mw-grid marker comment from the pre stage to the post stage.

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Annotated

from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor
from markdown.preprocessors import Preprocessor
from pydantic import BaseModel, ConfigDict, Field

from markwright._fences import map_lines
from markwright._html import add_classes, apply_edits, tokenize
from markwright._markers import InvalidMarkerError, decode_marker, encode_marker, find_markers

if TYPE_CHECKING:
    from collections.abc import Mapping

    from markdown import Markdown

MARKER_NAME = "mw-grid"
GRID_CLASS = "mw-grid"
CARDS_CLASS = "mw-grid-cards"
COLS_CLASS_PREFIX = "mw-grid-cols-"

GRID_RE = re.compile(r"^\[grid(?P<tokens>(?:\s+\w+)*)\]$")


class GridMarker(BaseModel):
    """A validated v1 mw-grid marker payload.

    Strict, so a field of the wrong type fails validation instead of being coerced; unknown
    fields are ignored.

    :ivar version: The payload version, ``1``.
    :ivar cards: Whether the list renders as cards.
    :ivar columns: The column count from 1 to 6, or ``None`` for auto.
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="ignore")

    version: int
    cards: bool = False
    columns: Annotated[int, Field(ge=1, le=6)] | None = None


def _parse_grid_tokens(token_run: str) -> dict[str, object] | None:
    """Parse the whitespace-separated tokens after ``grid`` into a marker payload.

    Tokens are order-free: ``cards`` sets the cards flag and a 1-to-6 digit run sets the
    column count. A repeated flag, a second count, an out-of-range count, or an unknown
    token makes the opener invalid.

    :param token_run: The captured text after ``grid`` and before ``]``.
    :returns: The payload with the present keys, or ``None`` when a token is invalid.
    """
    payload: dict[str, object] = {}
    for token in token_run.split():
        if token == "cards":
            if "cards" in payload:
                return None
            payload["cards"] = True
        elif token.isascii() and token.isdigit():
            # ASCII digits only: str.isdigit() also accepts non-decimal Unicode
            # digits (superscripts int() rejects, Arabic-Indic digits it misreads).
            if "columns" in payload:
                return None
            count = int(token)
            if not 1 <= count <= 6:
                return None
            payload["columns"] = count
        else:
            return None
    return payload


def _transform_line(line: str) -> list[str]:
    """Replace a ``[grid ...]`` line with a marker comment and a blank line.

    :param line: A single source line.
    :returns: The marker comment and a blank line for a valid grid directive, else the line
        unchanged.
    """
    grid_match = GRID_RE.match(line.strip())
    if grid_match is None:
        return [line]
    payload = _parse_grid_tokens(grid_match.group("tokens"))
    if payload is None:
        return [line]
    indent = line[: len(line) - len(line.lstrip())]
    return [f"{indent}{encode_marker(MARKER_NAME, payload)}", ""]


def expand_source(text: str, options: Mapping[str, object] | None = None) -> str:
    """Replace grid directives with mw-grid marker comments in raw source.

    Used by the ``mw pre`` CLI stage. A directive inside a fenced code block is left literal.

    :param text: The source text.
    :param options: Accepted for the registry's shared signature; grid has no options.
    :returns: The text with grid directives replaced by markers.
    """
    return map_lines(text, _transform_line)


def apply_html(
    rendered_html: str, skip_reasons: list[str] | None = None, options: Mapping[str, object] | None = None
) -> str:
    """Class lists from their mw-grid marker comments.

    Used by the ``mw post`` CLI stage. Markers are validated and skipped fail-soft;
    pass a ``skip_reasons`` list to collect why.
    A marker is skipped when its payload is invalid or no list follows it before the next marker.
    A recognized marker comment is always removed.

    :param rendered_html: Rendered HTML containing mw-grid marker comments.
    :param skip_reasons: Optional list collecting skip reasons; ``None`` drops them.
    :param options: Accepted for the registry's shared signature; grid has no options.
    :returns: HTML with ``mw-grid`` classes on the marked lists and the markers removed.
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

        grid_classes = GRID_CLASS
        if marker.cards:
            grid_classes += f" {CARDS_CLASS}"
        if marker.columns is not None:
            grid_classes += f" {COLS_CLASS_PREFIX}{marker.columns}"
        edits.append((list_tag.start, list_tag.end, add_classes(list_tag, grid_classes)))

    return apply_edits(rendered_html, edits)


class GridPreprocessor(Preprocessor):
    """Replace grid directives with mw-grid marker comments."""

    def run(self, lines: list[str]) -> list[str]:
        """Process lines, replacing grid directives with markers.

        :param lines: Source lines to process.
        :returns: Modified lines.
        """
        return map_lines("\n".join(lines), _transform_line).split("\n")


class GridPostprocessor(Postprocessor):
    """Class the lists that follow mw-grid markers."""

    def run(self, text: str) -> str:
        """Process rendered HTML, classing marked lists and removing the markers.

        :param text: Rendered HTML string.
        :returns: Modified HTML.
        """
        return apply_html(text)


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
