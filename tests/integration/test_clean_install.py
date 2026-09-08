# ABOUTME: Clean-venv install probe that builds the wheel and installs it with no dev group.
# Guards against runtime dependencies (e.g. pymdown-extensions) declared only in dev.

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

UV = shutil.which("uv")

requires_uv = pytest.mark.skipif(UV is None, reason="needs the uv binary on PATH")

REPO_ROOT = Path(__file__).resolve().parents[2]

# A tiny document exercising an embed extension, so a rendered `<iframe>` proves both
# that the wheel's runtime dependencies (e.g. pymdown-extensions) are actually installed
# and that the `render` subcommand's Markdown pipeline works end to end.
DOCUMENT = "[youtube dQw4w9WgXcQ]\n"

# Substrings that indicate the build backend warned about an unsupported/mismatched
# uv version rather than building cleanly.
_BUILD_BACKEND_WARNING_MARKERS = ("does not contain the", "does not satisfy")


@requires_uv
def test_build_and_render_in_clean_venv(tmp_path: Path) -> None:
    assert UV is not None
    dist_directory = tmp_path / "dist"

    build_result = subprocess.run(
        [UV, "build", "--out-dir", str(dist_directory)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    build_output = build_result.stdout + build_result.stderr
    assert build_result.returncode == 0, build_output
    assert "uv_build" not in build_output or not any(
        marker in build_output for marker in _BUILD_BACKEND_WARNING_MARKERS
    ), f"uv build warned about the build-backend pin: {build_output}"

    wheel_paths = list(dist_directory.glob("*.whl"))
    assert len(wheel_paths) == 1, f"expected exactly one built wheel, found {wheel_paths}"
    wheel_path = wheel_paths[0]

    venv_directory = tmp_path / "venv"
    venv_result = subprocess.run(
        [UV, "venv", "--python", "3.14", str(venv_directory)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert venv_result.returncode == 0, venv_result.stdout + venv_result.stderr
    venv_python = venv_directory / "bin" / "python"

    # Install ONLY the built wheel into the isolated venv: no dev group, no editable
    # install, no dependency on the outer environment already having pymdown-extensions.
    install_result = subprocess.run(
        [UV, "pip", "install", "--python", str(venv_python), str(wheel_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert install_result.returncode == 0, install_result.stdout + install_result.stderr

    installed_mw = venv_directory / "bin" / "mw"
    render_result = subprocess.run(
        [str(installed_mw), "render"],
        input=DOCUMENT,
        capture_output=True,
        text=True,
        check=False,
    )
    combined_output = render_result.stdout + render_result.stderr
    assert render_result.returncode == 0, combined_output
    assert "ModuleNotFoundError" not in combined_output
    assert "<iframe" in render_result.stdout
