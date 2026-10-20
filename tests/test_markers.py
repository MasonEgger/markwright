# ABOUTME: Tests for the shared marker-comment module: encoding, finding, and fail-soft decoding.
# Uses a tiny strict pydantic model to stand in for an extension's own marker schema.

import json

import pytest
from pydantic import BaseModel, ConfigDict

from markwright._html import tokenize
from markwright._markers import InvalidMarkerError, decode_marker, encode_marker, find_markers


class _Marker(BaseModel):
    model_config = ConfigDict(strict=True)

    version: int
    size: int | None = None


class TestEncodeMarker:
    def test_injects_version_first(self) -> None:
        assert encode_marker("mw-x", {"a": 1}) == '<!-- mw-x:{"version": 1, "a": 1} -->'

    def test_payload_cannot_close_the_comment(self) -> None:
        comment = encode_marker("mw-x", {"v": "a-->b<!--c"})
        inner = comment.removeprefix("<!-- mw-x:").removesuffix(" -->")

        assert "-->" not in inner
        assert "<" not in inner
        assert ">" not in inner
        assert json.loads(inner)["v"] == "a-->b<!--c"


class TestFindMarkers:
    def test_blocks_run_to_the_next_marker(self) -> None:
        first = encode_marker("mw-x", {"n": 1})
        second = encode_marker("mw-x", {"n": 2})
        html = f"{first}<pre>a</pre>{second}<pre>b</pre>"
        tokens = tokenize(html)

        markers = find_markers("mw-x", html, tokens)

        assert [marker.token_index for marker in markers] == [0, 4]
        assert [marker.block_end for marker in markers] == [4, len(tokens)]
        assert json.loads(markers[1].raw_payload)["n"] == 2

    def test_ignores_other_names_and_plain_comments(self) -> None:
        html = f"<!-- note --><!-- mw-y:{{}} -->{encode_marker('mw-x', {})}"

        markers = find_markers("mw-x", html, tokenize(html))

        assert [marker.token_index for marker in markers] == [2]

    def test_page_without_markers_yields_nothing(self) -> None:
        html = "<p>plain</p>"

        assert find_markers("mw-x", html, tokenize(html)) == []


class TestDecodeMarker:
    def test_valid_payload_returns_the_model(self) -> None:
        assert decode_marker("mw-x", '{"version": 1, "size": 3}', _Marker) == _Marker(version=1, size=3)

    def test_malformed_json(self) -> None:
        with pytest.raises(InvalidMarkerError) as skipped:
            decode_marker("mw-x", "{nope", _Marker)

        assert str(skipped.value) == "Skipping malformed mw-x marker: '{nope'"

    def test_non_object_payload(self) -> None:
        with pytest.raises(InvalidMarkerError) as skipped:
            decode_marker("mw-x", "[1]", _Marker)

        assert str(skipped.value) == "Skipping mw-x marker whose payload is not an object: '[1]'"

    def test_unsupported_version(self) -> None:
        with pytest.raises(InvalidMarkerError) as skipped:
            decode_marker("mw-x", '{"version": 2}', _Marker)

        assert str(skipped.value) == "Skipping mw-x marker with unsupported version 2"

    def test_wrongly_typed_field(self) -> None:
        raw_payload = '{"version": 1, "size": "big"}'

        with pytest.raises(InvalidMarkerError) as skipped:
            decode_marker("mw-x", raw_payload, _Marker)

        assert str(skipped.value) == f"Skipping mw-x marker with invalid fields (size): {raw_payload!r}"
