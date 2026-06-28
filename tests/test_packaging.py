# ABOUTME: Packaging smoke tests that run the installed mw console script via subprocess.
# Confirms the [project.scripts] entry point is wired so `mw --version` and `mw list` exit 0.

from __future__ import annotations

import shutil
import subprocess
from importlib.metadata import version as package_version

import pytest


def _mw_command() -> list[str]:
    """Resolve the installed ``mw`` console script, skipping if it is not on PATH.

    :returns: A single-element argument list naming the ``mw`` executable.
    """
    executable = shutil.which("mw")
    if executable is None:
        pytest.skip("mw console script is not on PATH")
    return [executable]


class TestPackagingSmoke:
    """Smoke tests that exercise the installed console script as a real subprocess."""

    def test_version_subprocess_returns_zero_and_reports_version(self) -> None:
        result = subprocess.run([*_mw_command(), "--version"], capture_output=True, text=True, check=False)
        assert result.returncode == 0
        assert package_version("markwright") in result.stdout

    def test_list_subprocess_returns_zero_and_lists_extensions(self) -> None:
        result = subprocess.run([*_mw_command(), "list"], capture_output=True, text=True, check=False)
        assert result.returncode == 0
        assert "youtube" in result.stdout
        assert "fence" in result.stdout
