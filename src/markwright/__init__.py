# ABOUTME: Package root for markwright; re-exports the public config API for host tools.
# Extensions load by name (markwright.<name>) and need nothing from here.

from __future__ import annotations

from markwright.config import Config, ConfigError, config_from_mapping, extension_configs, selected_extensions

__all__ = [
    "Config",
    "ConfigError",
    "config_from_mapping",
    "extension_configs",
    "selected_extensions",
]
