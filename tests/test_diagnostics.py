# ABOUTME: Tests for the Diagnostic record, the RenderWarning category, and the report call.
# Covers the closed reason vocabulary, immutability, and the list-plus-warning pairing.

from __future__ import annotations

from typing import get_args

import markdown
import pytest
from pydantic import ValidationError

from markwright import Diagnostic, RenderWarning
from markwright._diagnostics import DiagnosticReason, report


def make_diagnostic(**overrides: object) -> Diagnostic:
    """Build a tabs diagnostic, with any field overridden."""
    fields: dict[str, object] = {
        "extension": "tabs",
        "line": 4,
        "directive": "[/tab]",
        "reason": "stray-closer",
        "message": "Leaving [/tab] on line 4 literal: no matching opener",
    }
    return Diagnostic.model_validate(fields | overrides)


class TestDiagnostic:
    def test_is_frozen(self) -> None:
        diagnostic = make_diagnostic()
        with pytest.raises(ValidationError):
            diagnostic.line = 5

    def test_line_and_directive_accept_none(self) -> None:
        diagnostic = make_diagnostic(line=None, directive=None)
        assert diagnostic.line is None
        assert diagnostic.directive is None

    def test_rejects_a_reason_outside_the_vocabulary(self) -> None:
        with pytest.raises(ValidationError):
            make_diagnostic(reason="because")

    def test_reason_vocabulary_is_closed(self) -> None:
        assert get_args(DiagnosticReason) == (
            "unclosed",
            "stray-closer",
            "card-outside-grid",
            "disallowed-environment",
            "malformed-marker",
            "no-target",
            "unmatched-marker",
        )


class TestRenderWarning:
    def test_is_a_user_warning_carrying_the_diagnostic(self) -> None:
        diagnostic = make_diagnostic()
        warning = RenderWarning(diagnostic)
        assert isinstance(warning, UserWarning)
        assert warning.diagnostic is diagnostic
        assert str(warning) == diagnostic.message


class TestReport:
    def test_appends_to_the_list_and_warns_once(self) -> None:
        md = markdown.Markdown()
        diagnostic = make_diagnostic()
        with pytest.warns(RenderWarning) as recorded:
            report(md, diagnostic)
        assert md.markwright_diagnostics == [diagnostic]  # type: ignore[attr-defined]
        assert len(recorded) == 1
        assert recorded[0].message.diagnostic is diagnostic  # type: ignore[union-attr]

    def test_keeps_earlier_entries(self) -> None:
        md = markdown.Markdown()
        first = make_diagnostic()
        second = make_diagnostic(line=9)
        with pytest.warns(RenderWarning):
            report(md, first)
            report(md, second)
        assert md.markwright_diagnostics == [first, second]  # type: ignore[attr-defined]
