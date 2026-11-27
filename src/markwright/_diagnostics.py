# ABOUTME: Shared diagnostics: OptionError, ConfigWarning, Diagnostic, RenderWarning, and reporting.
# A leaf module so config, the extensions, and the CLI can share them without an import cycle through the registry.

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Literal

from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor
from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    import markdown

DiagnosticReason = Literal[
    "unclosed",
    "stray-closer",
    "card-outside-grid",
    "disallowed-environment",
    "malformed-marker",
    "no-target",
    "unmatched-marker",
]


class ConfigWarning(UserWarning):
    """Emitted when a setting makes a feature do nothing, for example ``enable = []``.

    Such settings stay legal (they switch markwright off inside a tool chain) but are never silent.
    A host can turn them into errors with ``warnings.simplefilter("error", ConfigWarning)``.
    """


class OptionError(ValueError):
    """Raised when an extension option has an invalid value, for example ``load = "sometimes"``.

    A ``ValueError`` subclass, so callers that catch ``ValueError`` from Python-Markdown keep working.
    Config validation converts it to a :class:`~markwright.config.ConfigError` naming the source.
    """


class Diagnostic(BaseModel):
    """One problem a post stage found and reported without changing the HTML.

    :ivar extension: The extension that reported it, such as ``tabs``.
    :ivar line: The 1-based source line of the directive, or ``None`` when the report has none.
    :ivar directive: The literal directive text, or ``None`` when the report has none.
    :ivar reason: A code from the closed vocabulary.
    :ivar message: The one-line text ``mw post --warn`` prints.
    """

    model_config = ConfigDict(frozen=True)

    extension: str
    line: int | None
    directive: str | None
    reason: DiagnosticReason
    message: str


class RenderWarning(UserWarning):
    """Emitted for each :class:`Diagnostic` an in-process render reports.

    :param diagnostic: The record the warning carries; its message is the warning text.
    """

    def __init__(self, diagnostic: Diagnostic) -> None:
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


def report(md: markdown.Markdown, diagnostic: Diagnostic) -> None:
    """Record a diagnostic on the Markdown instance and warn about it.

    The list ``md.markwright_diagnostics`` is the record; the warning is the side effect of the same call.

    :param md: The Markdown instance the render runs on.
    :param diagnostic: The problem to report.
    """
    recorded: list[Diagnostic] = getattr(md, "markwright_diagnostics", [])
    recorded.append(diagnostic)
    setattr(md, "markwright_diagnostics", recorded)  # noqa: B010 - an attribute Python-Markdown does not declare
    warnings.warn(RenderWarning(diagnostic), stacklevel=2)


class _DiagnosticsResetPreprocessor(Preprocessor):
    """Empty ``md.markwright_diagnostics`` before each document, ahead of every other preprocessor."""

    def run(self, lines: list[str]) -> list[str]:
        """Start the document with no diagnostics.

        :param lines: Source lines, returned unchanged.
        :returns: The same lines.
        """
        setattr(self.md, "markwright_diagnostics", [])  # noqa: B010 - an attribute Python-Markdown does not declare
        return lines


class ReportingExtension(Extension):
    """Base for the extensions whose postprocessor reports diagnostics in-process.

    ``convert`` never calls ``reset``, so a preprocessor registered once under a fixed name (above
    every markwright preprocessor) empties the list for each document, and ``reset`` empties it for
    a host that calls ``md.reset()`` between documents.
    """

    def attach_reporting(self, md: markdown.Markdown) -> None:
        """Register this extension for ``reset`` and the shared per-document reset preprocessor.

        Call it from ``extendMarkdown``. Loading several reporting extensions registers the
        preprocessor once.

        :param md: The Markdown instance being extended.
        """
        self.reporting_md = md
        md.registerExtension(self)
        if "mw-diagnostics-reset" not in md.preprocessors:
            md.preprocessors.register(_DiagnosticsResetPreprocessor(md), "mw-diagnostics-reset", 46)
        setattr(md, "markwright_diagnostics", [])  # noqa: B010 - an attribute Python-Markdown does not declare

    def reset(self) -> None:
        """Empty the diagnostics list when the host resets the Markdown instance."""
        setattr(self.reporting_md, "markwright_diagnostics", [])  # noqa: B010 - an attribute Python-Markdown does not declare
