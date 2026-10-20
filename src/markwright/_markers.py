# ABOUTME: Shared marker-comment contract carrying data from a pre stage to a post stage.
# Encodes, finds, and fail-soft decodes the versioned <!-- NAME:{JSON} --> comments.

# A marker is an HTML comment placed in the source by a pre stage: ``<!-- NAME:{JSON} -->``.
# The JSON payload carries an integer ``version`` plus the extension's own fields. The
# payload is comment-safe: every literal ``<`` and ``>`` is written as its ``\uXXXX``
# escape, so a value containing ``-->`` can never close the comment early. ``json.loads``
# restores the characters, so reading needs no manual decode step. Post stages read
# markers fail-soft: a marker that is malformed, not an object, an unsupported version,
# or has a wrongly typed field is skipped with a reason, never an exception. Fence, grid,
# and annotate share this module so the contract lives in one place.

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

if TYPE_CHECKING:
    from collections.abc import Mapping

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
