# ABOUTME: Shared marker-comment contract carrying data from a pre stage to a post stage.
# Encodes, emits, finds, stack-matches, and fail-soft decodes the versioned <!-- NAME:{JSON} --> comments.

# A marker is an HTML comment placed in the source by a pre stage: ``<!-- NAME:{JSON} -->``.
# The JSON payload carries an integer ``version`` plus the extension's own fields. The
# payload is comment-safe: every literal ``<`` and ``>`` is written as its ``\uXXXX``
# escape, so a value containing ``-->`` can never close the comment early. ``json.loads``
# restores the characters, so reading needs no manual decode step. Post stages read
# markers fail-soft: a marker that is malformed, not an object, an unsupported version,
# or has a wrongly typed field is skipped with a reason, never an exception. Fence, grid,
# tabs, and annotate share this module so the contract lives in one place: it also owns the
# standalone and inline emission helpers (``marker_block``, ``inline_problem_marker``), the
# offset-ordered bracket matcher for paired markers (``match_marker_pairs``), and the
# inline problem-marker reader (``report_problem_markers``) that grid and tabs both call.

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from markwright._html import HtmlToken

MARKER_VERSION = 1

ModelT = TypeVar("ModelT", bound=BaseModel)


class InvalidMarkerError(Exception):
    """A marker the post stage skips fail-soft; the message is the skip reason."""


class MarkerComment(BaseModel):
    """One marker comment found in rendered HTML.

    :ivar token_index: Index of the comment in the token list.
    :ivar raw_payload: The text between ``NAME:`` and the comment's closing `` -->``.
    :ivar block_end: Index of the next same-name marker's token, or the token count for the last.
    """

    model_config = ConfigDict(frozen=True)

    token_index: int
    raw_payload: str
    block_end: int


def encode_marker(name: str, payload: Mapping[str, object]) -> str:
    """Serialize a versioned marker payload as an HTML comment.

    :param name: The marker name, such as ``mw-fence``.
    :param payload: The extension's fields; ``version`` is added first.
    :returns: ``<!-- NAME:{JSON} -->`` with every literal ``<`` and ``>`` unicode-escaped.
    """
    encoded = json.dumps({"version": MARKER_VERSION, **payload}).replace("<", "\\u003c").replace(">", "\\u003e")
    return f"<!-- {name}:{encoded} -->"


def marker_block(indent: str, name: str, payload: Mapping[str, object]) -> list[str]:
    """Render a marker comment as its own block, a blank line on either side.

    The blank lines keep the comment a standalone block, so the content a paired opener and
    closer surround renders as normal Markdown in Python-Markdown and in Goldmark.

    :param indent: The opener's leading whitespace, shared by the closer.
    :param name: The marker name.
    :param payload: The marker payload; ``version`` is added by the encoder.
    :returns: A blank line, the indented marker comment, and a blank line.
    """
    return ["", f"{indent}{encode_marker(name, payload)}", ""]


def inline_problem_marker(line: str, name: str, payload: Mapping[str, object]) -> str:
    """Attach a marker comment inline, directly after a literal directive line.

    The comment rides on the same line so the literal text keeps its paragraph structure: a
    comment on its own line would split a paragraph the directive belonged to.

    :param line: The original source line, kept verbatim.
    :param name: The marker name.
    :param payload: The marker payload; ``version`` is added by the encoder.
    :returns: The line with the marker comment appended.
    """
    return f"{line}{encode_marker(name, payload)}"


def find_markers(name: str, rendered_html: str, tokens: list[HtmlToken]) -> list[MarkerComment]:
    """Find every ``NAME`` marker comment among the tokens of rendered HTML.

    :param name: The marker name to look for.
    :param rendered_html: The HTML the tokens were produced from.
    :param tokens: The tokens of ``rendered_html``.
    :returns: The markers in document order; empty when the page has none.
    """
    comment_re = re.compile(rf"<!-- {re.escape(name)}:(.*?) -->")
    found = [
        (token_index, comment_match.group(1))
        for token_index, token in enumerate(tokens)
        if token.kind == "comment" and (comment_match := comment_re.fullmatch(rendered_html, token.start, token.end))
    ]
    markers: list[MarkerComment] = []
    for position, (token_index, raw_payload) in enumerate(found):
        block_end = found[position + 1][0] if position + 1 < len(found) else len(tokens)
        markers.append(MarkerComment(token_index=token_index, raw_payload=raw_payload, block_end=block_end))
    return markers


class MarkerMatch(BaseModel):
    """The result of bracket-matching a kind's open and close markers.

    :ivar pairs: Each matched ``(open, close)`` pair, in the order its closer was reached.
    :ivar unmatched_opens: Open markers that never found a closer, oldest first.
    :ivar unmatched_closes: Close markers that never found an opener, in document order.
    """

    model_config = ConfigDict(frozen=True)

    pairs: tuple[tuple[MarkerComment, MarkerComment], ...]
    unmatched_opens: tuple[MarkerComment, ...]
    unmatched_closes: tuple[MarkerComment, ...]


def match_marker_pairs(open_name: str, close_name: str, rendered_html: str, tokens: list[HtmlToken]) -> MarkerMatch:
    """Order a kind's open and close markers by position and stack-match them like brackets.

    Shared by the paired-marker post stages (grid's block grids and cards, tabs' sets): a
    close pairs with the nearest still-open opener, so nested pairs match in order and close
    in reverse. Markers with no partner are returned separately for the caller to skip
    fail-soft.

    :param open_name: The open marker name, such as ``mw-grid-block``.
    :param close_name: The close marker name, such as ``mw-grid-end``.
    :param rendered_html: The HTML the tokens were produced from.
    :param tokens: The tokens of ``rendered_html``.
    :returns: The matched pairs and the unmatched open and close markers.
    """
    opens = find_markers(open_name, rendered_html, tokens)
    closes = find_markers(close_name, rendered_html, tokens)
    events = sorted(
        [(marker.token_index, True, marker) for marker in opens]
        + [(marker.token_index, False, marker) for marker in closes],
        key=lambda event: event[0],
    )
    pairs: list[tuple[MarkerComment, MarkerComment]] = []
    open_stack: list[MarkerComment] = []
    unmatched_closes: list[MarkerComment] = []
    for _, is_open, marker in events:
        if is_open:
            open_stack.append(marker)
        elif open_stack:
            pairs.append((open_stack.pop(), marker))
        else:
            unmatched_closes.append(marker)
    return MarkerMatch(pairs=tuple(pairs), unmatched_opens=tuple(open_stack), unmatched_closes=tuple(unmatched_closes))


def decode_marker(name: str, raw_payload: str, model: type[ModelT]) -> ModelT:
    """Decode and validate a marker comment's JSON payload.

    :param name: The marker name, used in skip reasons.
    :param raw_payload: The text between ``NAME:`` and the comment's end.
    :param model: The pydantic model that validates the payload.
    :returns: The validated marker.
    :raises InvalidMarkerError: If the JSON is malformed, not an object, an unsupported version, or
        has a field of the wrong type.
    """
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as decode_error:
        raise InvalidMarkerError(f"Skipping malformed {name} marker: {raw_payload!r}") from decode_error
    if not isinstance(payload, dict):
        raise InvalidMarkerError(f"Skipping {name} marker whose payload is not an object: {raw_payload!r}")
    if payload.get("version") != MARKER_VERSION:
        raise InvalidMarkerError(f"Skipping {name} marker with unsupported version {payload.get('version')!r}")
    try:
        return model.model_validate(payload)
    except ValidationError as validation_error:
        invalid_fields = ", ".join(str(error["loc"][0]) for error in validation_error.errors())
        raise InvalidMarkerError(
            f"Skipping {name} marker with invalid fields ({invalid_fields}): {raw_payload!r}"
        ) from validation_error


def report_problem_markers(
    name: str,
    rendered_html: str,
    tokens: list[HtmlToken],
    model: type[ModelT],
    message_for: Callable[[ModelT], str],
    skip_reasons: list[str] | None,
) -> list[tuple[int, int, str]]:
    """Read every inline problem marker of a kind, report it, and remove its comment.

    Shared by grid and tabs: both leave a container problem literal and attach an inline marker
    so the post stage can surface it under ``--warn``. A marker that decodes contributes its
    composed message; a malformed one contributes its skip reason. Either way the comment is
    removed.

    :param name: The problem marker name, such as ``mw-grid-problem``.
    :param rendered_html: The HTML the tokens were produced from.
    :param tokens: The tokens of ``rendered_html``.
    :param model: The pydantic model that validates the payload.
    :param message_for: Composes the ``--warn`` message from a decoded marker.
    :param skip_reasons: Optional list collecting the reports and skips; ``None`` drops them.
    :returns: The edits that remove every problem-marker comment.
    """
    edits: list[tuple[int, int, str]] = []
    for marker_comment in find_markers(name, rendered_html, tokens):
        comment = tokens[marker_comment.token_index]
        edits.append((comment.start, comment.end, ""))
        try:
            problem = decode_marker(name, marker_comment.raw_payload, model)
        except InvalidMarkerError as skipped:
            if skip_reasons is not None:
                skip_reasons.append(str(skipped))
            continue
        if skip_reasons is not None:
            skip_reasons.append(message_for(problem))
    return edits
