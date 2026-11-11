# ABOUTME: Grid extension: a [grid ...] shortcut classes the next list; paired [grid]/[/grid] and [card] wrap blocks.
# Carries each request in mw-grid, mw-grid-block, and mw-card marker comments from the pre stage to the post stage.

# A [grid ...] opener with no closer is the list shortcut: it classes the following <ul> or <ol>
# through an mw-grid marker, the 0.4.0 behavior. A [grid ...] paired with [/grid] is a block grid:
# the pre stage emits an mw-grid-block open marker and an mw-grid-end close marker around the
# content, and the post stage wraps everything between them in a <div>. A [card] paired with
# [/card] directly inside a block grid is emitted as mw-card and mw-card-end and wrapped in a
# <div class="mw-card">, so one card can hold several blocks. The pre stage pairs containers with
# _containers.scan_containers, so an opener or closer inside fenced or indented code stays literal,
# and a card not directly inside a grid, or an invalid grid opener, is left literal. A grid-owned
# problem left literal (an unclosed [card], a stray [/card] or [/grid], or a card outside a grid)
# gains an inline mw-grid-problem marker carrying a closed-vocabulary reason, so the post stage
# reports it under --warn and removes the comment; the directive text renders unchanged. The post
# stage orders every open and close marker of a kind by position and stack-matches them like
# brackets, so nested grids and cards wrap in order and close in reverse. Every marker is a
# versioned public contract read fail-soft: a malformed payload, an unsupported version, a wrongly
# typed field, or an unmatched open or close is skipped with a reason and its comment removed,
# never raised.

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal

from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor
from markdown.preprocessors import Preprocessor
from pydantic import BaseModel, ConfigDict, Field

from markwright._containers import scan_containers
from markwright._html import add_classes, apply_edits, tokenize
from markwright._markers import InvalidMarkerError, decode_marker, encode_marker, find_markers

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from markdown import Markdown

    from markwright._html import HtmlToken

MARKER_NAME = "mw-grid"
BLOCK_MARKER_NAME = "mw-grid-block"
BLOCK_END_NAME = "mw-grid-end"
CARD_MARKER_NAME = "mw-card"
CARD_END_NAME = "mw-card-end"
PROBLEM_MARKER_NAME = "mw-grid-problem"
GRID_CLASS = "mw-grid"
CARDS_CLASS = "mw-grid-cards"
COLS_CLASS_PREFIX = "mw-grid-cols-"
CARD_CLASS = "mw-card"

_ProblemDirective = Literal["[card]", "[/card]", "[/grid]"]
_ProblemReason = Literal["unclosed", "stray-closer", "card-outside-grid"]

# scan_containers reports problems as free text; map the grid-owned ones to a closed vocabulary.
# Tab problems and a [grid] opener demoted by a stray [/grid] are absent on purpose: tabs belong
# to the tabs extension, and spec line 128 asks only that an invalid or demoted grid opener stay
# literal, with no report.
_GRID_OWNED_PROBLEMS: dict[str, tuple[_ProblemDirective, _ProblemReason]] = {
    "unclosed [card] opener": ("[card]", "unclosed"),
    "no matching [card] opener": ("[/card]", "stray-closer"),
    "no matching [grid] opener": ("[/grid]", "stray-closer"),
}

# Post composes the stderr message from the validated reason code, so a hand-written marker
# cannot push arbitrary text to stderr.
_PROBLEM_DETAIL: dict[_ProblemReason, str] = {
    "unclosed": "unclosed, no matching closer",
    "stray-closer": "no matching opener",
    "card-outside-grid": "a card must be directly inside a block grid",
}


class GridMarker(BaseModel):
    """A validated v1 mw-grid shortcut marker payload.

    Carried from an unclosed ``[grid ...]`` opener to the list after it. Strict, so a field of the
    wrong type fails validation instead of being coerced; unknown fields are ignored.

    :ivar version: The payload version, ``1``.
    :ivar cards: Whether the list renders as cards.
    :ivar columns: The column count from 1 to 6, or ``None`` for auto.
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="ignore")

    version: int
    cards: bool = False
    columns: Annotated[int, Field(ge=1, le=6)] | None = None


class GridBlockMarker(BaseModel):
    """A validated v1 mw-grid-block marker payload for a paired block grid.

    The pre stage emits it at a ``[grid ...]`` opener that has a matching ``[/grid]``; the post
    stage pairs it with the next mw-grid-end marker (stack-matched by position) and wraps the span
    between them in a ``<div>``. Strict; unknown fields are ignored.

    :ivar version: The payload version, ``1``.
    :ivar cards: Whether the grid renders as cards.
    :ivar columns: The column count from 1 to 6, or ``None`` for auto.
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="ignore")

    version: int
    cards: bool = False
    columns: Annotated[int, Field(ge=1, le=6)] | None = None


class CardMarker(BaseModel):
    """A validated v1 mw-card marker payload for a card inside a block grid.

    The pre stage emits it at a ``[card]`` opener directly inside a block grid; the post stage pairs
    it with the next mw-card-end marker and wraps the span between them in ``<div class="mw-card">``.
    Strict; unknown fields are ignored.

    :ivar version: The payload version, ``1``.
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="ignore")

    version: int


class GridProblemMarker(BaseModel):
    """A validated v1 mw-grid-problem marker payload for a container problem left literal.

    The pre stage attaches it, inline, to a grid-owned container problem it cannot turn into
    markup: an unclosed ``[card]``, a stray ``[/card]`` or ``[/grid]``, or a ``[card]`` not
    directly inside a block grid. The directive text stays literal; the post stage reads the
    marker, composes one ``--warn`` message from the validated fields, and removes the comment.
    Strict with a closed vocabulary, so a hand-written marker cannot push free text to stderr;
    unknown fields are ignored.

    :ivar version: The payload version, ``1``.
    :ivar line: The 1-based source line of the literal directive.
    :ivar directive: The literal directive text, one of ``[card]``, ``[/card]``, ``[/grid]``.
    :ivar reason: The problem code, one of ``unclosed``, ``stray-closer``, ``card-outside-grid``.
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="ignore")

    version: int
    line: Annotated[int, Field(ge=1)]
    directive: _ProblemDirective
    reason: _ProblemReason


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


def _grid_classes(marker: GridMarker | GridBlockMarker) -> str:
    """Build the grid class list from a validated shortcut or block-grid marker.

    :param marker: The decoded marker carrying the cards flag and column count.
    :returns: ``mw-grid`` plus ``mw-grid-cards`` for cards and ``mw-grid-cols-N`` for a count.
    """
    classes = GRID_CLASS
    if marker.cards:
        classes += f" {CARDS_CLASS}"
    if marker.columns is not None:
        classes += f" {COLS_CLASS_PREFIX}{marker.columns}"
    return classes


def _marker_block(indent: str, name: str, payload: Mapping[str, object]) -> list[str]:
    """Render a paired marker comment as its own block, a blank line on either side.

    The blank lines keep the comment a standalone block, so the content between an opener and its
    closer renders as normal Markdown in Python-Markdown and in Goldmark.

    :param indent: The opener's leading whitespace, shared by the closer.
    :param name: The marker name.
    :param payload: The marker payload; ``version`` is added by the encoder.
    :returns: A blank line, the indented marker comment, and a blank line.
    """
    return ["", f"{indent}{encode_marker(name, payload)}", ""]


def _problem_marker(line: str, source_line: int, directive: _ProblemDirective, reason: _ProblemReason) -> list[str]:
    """Attach a problem marker inline to a literal directive line.

    The comment rides on the same line, directly after the directive, so the literal text keeps
    the paragraph structure it had: a comment on its own line would split a paragraph the directive
    belonged to.

    :param line: The original source line, kept verbatim.
    :param source_line: The 1-based line number of the directive.
    :param directive: The literal directive text.
    :param reason: The problem code.
    :returns: The line with the mw-grid-problem comment appended.
    """
    payload = {"line": source_line, "directive": directive, "reason": reason}
    return [f"{line}{encode_marker(PROBLEM_MARKER_NAME, payload)}"]


def expand_source(text: str, options: Mapping[str, object] | None = None) -> str:
    """Replace grid and card containers with marker comments in raw source.

    Used by the ``mw pre`` CLI stage. Pairs containers with :func:`scan_containers`, so an opener
    or closer inside fenced or indented code stays literal. A paired ``[grid ...]`` becomes an
    mw-grid-block open marker and an mw-grid-end close marker; a ``[card]`` directly inside a block
    grid becomes mw-card and mw-card-end; an unclosed ``[grid ...]`` becomes the mw-grid shortcut
    marker. A grid-owned problem (an unclosed ``[card]``, a stray ``[/card]`` or ``[/grid]``, or a
    ``[card]`` not directly inside a block grid) stays literal and gains an inline mw-grid-problem
    marker so the post stage can report it. An invalid grid opener stays literal with no report,
    and tab problems are left untouched for the tabs extension.

    :param text: The source text.
    :param options: Accepted for the registry's shared signature; grid has no options.
    :returns: The text with grid and card containers replaced by markers.
    """
    scan = scan_containers(text)
    lines = text.split("\n")
    replacements: dict[int, list[str]] = {}
    for pair in scan.pairs:
        if pair.kind == "grid":
            payload = _parse_grid_tokens(" ".join(pair.tokens))
            if payload is None:
                continue
            replacements[pair.open_line] = _marker_block(pair.indent, BLOCK_MARKER_NAME, payload)
            replacements[pair.close_line] = _marker_block(pair.indent, BLOCK_END_NAME, {})
        elif pair.kind == "card" and pair.enclosed_by_grid:
            replacements[pair.open_line] = _marker_block(pair.indent, CARD_MARKER_NAME, {})
            replacements[pair.close_line] = _marker_block(pair.indent, CARD_END_NAME, {})
        elif pair.kind == "card":
            # A matched card not directly inside a block grid stays literal; report on its opener.
            replacements[pair.open_line] = _problem_marker(
                lines[pair.open_line], pair.open_line + 1, "[card]", "card-outside-grid"
            )
    for unclosed in scan.unclosed_grids:
        payload = _parse_grid_tokens(" ".join(unclosed.tokens))
        if payload is None:
            continue
        replacements[unclosed.line] = [f"{unclosed.indent}{encode_marker(MARKER_NAME, payload)}", ""]
    for problem in scan.problems:
        owned = _GRID_OWNED_PROBLEMS.get(problem.reason)
        if owned is None:
            continue
        directive, reason = owned
        replacements[problem.line] = _problem_marker(lines[problem.line], problem.line + 1, directive, reason)

    if not replacements:
        return text
    expanded: list[str] = []
    for line_index, line in enumerate(lines):
        expanded.extend(replacements.get(line_index, [line]))
    return "\n".join(expanded)


def _grid_block_class(raw_payload: str) -> str:
    """Decode an mw-grid-block payload and build its div class list.

    :param raw_payload: The marker comment's JSON text.
    :returns: The grid class list.
    :raises InvalidMarkerError: If the payload is malformed or a field is wrongly typed.
    """
    return _grid_classes(decode_marker(BLOCK_MARKER_NAME, raw_payload, GridBlockMarker))


def _card_class(raw_payload: str) -> str:
    """Validate an mw-card payload and return the card div class.

    :param raw_payload: The marker comment's JSON text.
    :returns: ``mw-card``.
    :raises InvalidMarkerError: If the payload is malformed or a field is wrongly typed.
    """
    decode_marker(CARD_MARKER_NAME, raw_payload, CardMarker)
    return CARD_CLASS


def _problem_message(problem: GridProblemMarker) -> str:
    """Compose a ``--warn`` message from a validated problem marker.

    :param problem: The decoded marker carrying the directive, line, and reason code.
    :returns: A one-line diagnostic naming the directive and its source line.
    """
    return f"Leaving {problem.directive} on line {problem.line} literal: {_PROBLEM_DETAIL[problem.reason]}"


def _wrap_paired(
    rendered_html: str,
    tokens: list[HtmlToken],
    open_name: str,
    close_name: str,
    div_class_for: Callable[[str], str],
    skip_reasons: list[str] | None,
) -> list[tuple[int, int, str]]:
    """Wrap the span between each open and close marker of a kind in a ``<div>``.

    Orders every open and close comment of the kind by position and stack-matches them like
    brackets, so nested pairs wrap in order and close in reverse. For a matched pair the open
    comment becomes the opening ``<div>`` and the close comment becomes ``</div>``. A payload that
    will not decode, a close with no open, and an open with no close are skipped fail-soft: the
    comment is removed, a reason recorded, and no div emitted.

    :param rendered_html: The HTML the tokens were produced from.
    :param tokens: The tokens of ``rendered_html``.
    :param open_name: The open marker name, such as ``mw-grid-block``.
    :param close_name: The close marker name, such as ``mw-grid-end``.
    :param div_class_for: Reads an open marker's raw payload and returns its div class, raising
        ``InvalidMarkerError`` for a payload to skip.
    :param skip_reasons: Optional list collecting skip reasons; ``None`` drops them.
    :returns: The span edits that wrap each matched pair and remove every marker comment.
    """
    opens = find_markers(open_name, rendered_html, tokens)
    closes = find_markers(close_name, rendered_html, tokens)
    ordered = sorted(
        [(marker.token_index, True, marker.raw_payload) for marker in opens]
        + [(marker.token_index, False, "") for marker in closes],
        key=lambda event: event[0],
    )

    edits: list[tuple[int, int, str]] = []
    open_stack: list[tuple[int, str]] = []
    for token_index, is_open, raw_payload in ordered:
        comment = tokens[token_index]
        if is_open:
            open_stack.append((token_index, raw_payload))
            continue
        if not open_stack:
            edits.append((comment.start, comment.end, ""))
            if skip_reasons is not None:
                skip_reasons.append(f"Skipping {close_name} marker with no matching {open_name}")
            continue
        open_index, open_payload = open_stack.pop()
        open_comment = tokens[open_index]
        try:
            div_class = div_class_for(open_payload)
        except InvalidMarkerError as skipped:
            edits.append((open_comment.start, open_comment.end, ""))
            edits.append((comment.start, comment.end, ""))
            if skip_reasons is not None:
                skip_reasons.append(str(skipped))
            continue
        edits.append((open_comment.start, open_comment.end, f'<div class="{div_class}">'))
        edits.append((comment.start, comment.end, "</div>"))

    for open_index, _ in open_stack:
        open_comment = tokens[open_index]
        edits.append((open_comment.start, open_comment.end, ""))
        if skip_reasons is not None:
            skip_reasons.append(f"Skipping {open_name} marker with no matching {close_name}")
    return edits


def apply_html(
    rendered_html: str, skip_reasons: list[str] | None = None, options: Mapping[str, object] | None = None
) -> str:
    """Class shortcut lists and wrap block grids and cards from their marker comments.

    Used by the ``mw post`` CLI stage. An mw-grid marker classes the list that follows it; an
    mw-grid-block and mw-grid-end pair wraps its content in a grid ``<div>``; an mw-card and
    mw-card-end pair wraps its content in ``<div class="mw-card">``. An mw-grid-problem marker
    reports a container problem left literal and is removed. Markers are validated and skipped
    fail-soft; pass a ``skip_reasons`` list to collect the reports and the skips. Every recognized
    marker comment is removed. A shortcut marker is skipped when its payload is invalid or no list
    follows it.

    :param rendered_html: Rendered HTML containing grid and card marker comments.
    :param skip_reasons: Optional list collecting skip reasons; ``None`` drops them.
    :param options: Accepted for the registry's shared signature; grid has no options.
    :returns: HTML with the grids and cards wrapped or classed and the markers removed.
    """
    tokens = tokenize(rendered_html)
    edits: list[tuple[int, int, str]] = []
    for marker_comment in find_markers(PROBLEM_MARKER_NAME, rendered_html, tokens):
        comment = tokens[marker_comment.token_index]
        edits.append((comment.start, comment.end, ""))
        try:
            problem = decode_marker(PROBLEM_MARKER_NAME, marker_comment.raw_payload, GridProblemMarker)
        except InvalidMarkerError as skipped:
            if skip_reasons is not None:
                skip_reasons.append(str(skipped))
            continue
        if skip_reasons is not None:
            skip_reasons.append(_problem_message(problem))

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
        edits.append((list_tag.start, list_tag.end, add_classes(list_tag, _grid_classes(marker))))

    edits += _wrap_paired(rendered_html, tokens, BLOCK_MARKER_NAME, BLOCK_END_NAME, _grid_block_class, skip_reasons)
    edits += _wrap_paired(rendered_html, tokens, CARD_MARKER_NAME, CARD_END_NAME, _card_class, skip_reasons)
    return apply_edits(rendered_html, edits)


class GridPreprocessor(Preprocessor):
    """Replace grid and card containers with marker comments."""

    def run(self, lines: list[str]) -> list[str]:
        """Process lines, replacing grid and card containers with markers.

        :param lines: Source lines to process.
        :returns: Modified lines.
        """
        return expand_source("\n".join(lines)).split("\n")


class GridPostprocessor(Postprocessor):
    """Class the lists and wrap the blocks that mw-grid, mw-grid-block, and mw-card markers mark."""

    def run(self, text: str) -> str:
        """Process rendered HTML, classing and wrapping the marked content and removing the markers.

        :param text: Rendered HTML string.
        :returns: Modified HTML.
        """
        return apply_html(text)


class GridExtension(Extension):
    """Python-Markdown extension for grids and cards."""

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
