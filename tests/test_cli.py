# ABOUTME: Tests for the mw CLI entry point: --version, list, usage errors, and post.
# Drives main() with explicit argv and captures stdout/stderr via capsys.

from __future__ import annotations

import io
from importlib.metadata import version as package_version

import pytest

from markwright.cli import main
from markwright.codepen import CODEPEN_SCRIPT


class TestCliVersion:
    """Tests for the top-level --version action."""

    def test_version_returns_zero_and_prints_package_version(self, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = main(["--version"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert package_version("markwright") in captured.out


class TestCliList:
    """Tests for the list subcommand."""

    def test_list_returns_zero_and_reports_each_extension_with_stages(self, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = main(["list"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "youtube" in captured.out
        assert "fence" in captured.out
        # A pre-only extension and a pre+post extension are labeled differently.
        assert "youtube: pre" in captured.out
        assert "youtube: pre, post" not in captured.out
        assert "fence: pre, post" in captured.out


class TestCliUsageError:
    """Tests for argparse usage errors."""

    def test_unknown_subcommand_returns_two(self, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = main(["bogus"])
        assert exit_code == 2

    def test_no_subcommand_prints_usage_and_returns_two(self, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = main([])
        captured = capsys.readouterr()
        assert exit_code == 2
        assert "usage: mw" in captured.out


def _feed_stdin(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    """Replace ``sys.stdin`` with a text stream yielding ``text``.

    :param monkeypatch: Pytest monkeypatch fixture.
    :param text: Content the CLI handler will read from stdin.
    """
    monkeypatch.setattr("sys.stdin", io.StringIO(text))


class TestCliPost:
    """Tests for the post subcommand: stdin to stdout HTML post-processing."""

    def test_post_injects_codepen_script_once(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _feed_stdin(monkeypatch, '<p class="codepen">embed</p>')
        exit_code = main(["post"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert captured.out.count(CODEPEN_SCRIPT) == 1

    def test_post_use_subset_runs_only_selected_stage(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _feed_stdin(monkeypatch, '<p class="codepen">&lt;^&gt;mark me&lt;^&gt;</p>')
        exit_code = main(["post", "--use", "highlight"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert CODEPEN_SCRIPT not in captured.out
        assert "<mark>mark me</mark>" in captured.out

    def test_post_exclude_removes_extension(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _feed_stdin(monkeypatch, '<p class="codepen">embed</p>')
        exit_code = main(["post", "--exclude", "codepen"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert CODEPEN_SCRIPT not in captured.out

    def test_post_warn_reports_malformed_marker_on_stderr(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _feed_stdin(monkeypatch, "<!-- mw-fence:not json --><p>body</p>")
        exit_code = main(["post", "--warn"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "<p>body</p>" in captured.out
        assert "malformed mw-fence marker" in captured.err

    def test_post_without_warn_is_silent_on_malformed_marker(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _feed_stdin(monkeypatch, "<!-- mw-fence:not json --><p>body</p>")
        exit_code = main(["post"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "<p>body</p>" in captured.out
        assert captured.err == ""

    def test_post_unknown_use_name_returns_two_with_stderr(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _feed_stdin(monkeypatch, "<p>body</p>")
        exit_code = main(["post", "--use", "bogus"])
        captured = capsys.readouterr()
        assert exit_code == 2
        assert "bogus" in captured.err
