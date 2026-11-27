# ABOUTME: Package root for markwright; re-exports the public config API for host tools.
# Extensions load by name (markwright.<name>) and need nothing from here.

from __future__ import annotations

from markwright._diagnostics import ConfigWarning, Diagnostic, OptionError, RenderWarning
from markwright.config import (
    Config,
    ConfigError,
    config_from_mapping,
    disallowed_environments,
    extension_configs,
    selected_extensions,
)

__all__ = [
    "Config",
    "ConfigError",
    "ConfigWarning",
    "Diagnostic",
    "OptionError",
    "RenderWarning",
    "config_from_mapping",
    "disallowed_environments",
    "extension_configs",
    "selected_extensions",
]
