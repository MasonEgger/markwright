# ABOUTME: Smoke test verifying the markwright package is importable.
# Validates that the package installs and exposes expected metadata.

from importlib.metadata import version


def test_package_is_importable() -> None:
    import markwright  # noqa: F401


def test_package_version_is_set() -> None:
    assert version("markwright") == "0.1.0"
