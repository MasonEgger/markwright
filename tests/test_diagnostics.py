# ABOUTME: Tests for the Diagnostic record and the RenderWarning category.
# Covers the closed reason vocabulary and immutability.

from __future__ import annotations

from typing import get_args

import pytest
from pydantic import ValidationError

from markwright import Diagnostic, RenderWarning


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
        assert get_args(Diagnostic.model_fields["reason"].annotation) == (
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
