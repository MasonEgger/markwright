# ABOUTME: The ConfigWarning category for settings that turn a markwright feature into a no-op.
# A leaf module so config, fence, and the CLI can share it without an import cycle through the registry.

from __future__ import annotations


class ConfigWarning(UserWarning):
    """Emitted when a setting makes a feature do nothing, for example ``enable = []``.

    Such settings stay legal (they switch markwright off inside a tool chain) but are never silent.
    A host can turn them into errors with ``warnings.simplefilter("error", ConfigWarning)``.
    """
