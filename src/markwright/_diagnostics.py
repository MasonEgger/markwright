# ABOUTME: Shared diagnostics: OptionError for invalid extension options, ConfigWarning for no-op settings.
# A leaf module so config, the extensions, and the CLI can share them without an import cycle through the registry.

from __future__ import annotations


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
