# ABOUTME: Tests for the mw CLI entry point: --version, list, usage errors, and post.
# Drives main() with explicit argv and captures stdout/stderr via capsys.

from __future__ import annotations

import io
from importlib.metadata import version as package_version

import markdown
import pytest

from markwright.cli import main
from markwright.codepen import CODEPEN_SCRIPT
from markwright.registry import EXTENSION_NAMES


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


def _in_process_render(text: str, names: list[str]) -> str:
    """Render ``text`` through the same in-process stack the render handler builds.

    :param text: Markdown source text.
    :param names: markwright extension names to load alongside the site stack.
    :returns: Final HTML from the configured ``markdown.Markdown`` instance.
    """
    instance = markdown.Markdown(
        extensions=["pymdownx.superfences", "pymdownx.highlight", *(f"markwright.{name}" for name in names)],
        extension_configs={"pymdownx.highlight": {"pygments_lang_class": True}},
    )
    return instance.convert(text)


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


class TestCliPre:
    """Tests for the pre subcommand: stdin to stdout source-stage expansion."""

    def test_pre_expands_youtube_line_to_iframe(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _feed_stdin(monkeypatch, "[youtube dQw4w9WgXcQ]")
        exit_code = main(["pre"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert '<iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ"' in captured.out

    def test_pre_wraps_prose_highlight_marker(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _feed_stdin(monkeypatch, "Text with a <^>prose<^> marker.")
        exit_code = main(["pre"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "<mark>prose</mark>" in captured.out

    def test_pre_fence_label_emits_mw_fence_comment_and_keeps_fence(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _feed_stdin(monkeypatch, "```\n[label deploy.sh]\necho hi\n```")
        exit_code = main(["pre"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "<!-- mw-fence:" in captured.out
        assert '"label": "deploy.sh"' in captured.out
        assert "```" in captured.out
        assert "echo hi" in captured.out

    def test_pre_use_selects_only_named_stage(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _feed_stdin(monkeypatch, "[youtube dQw4w9WgXcQ]\n\nText with a <^>prose<^> marker.")
        exit_code = main(["pre", "--use", "youtube"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "<iframe" in captured.out
        assert "<mark>prose</mark>" not in captured.out

    def test_pre_exclude_drops_named_stage(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _feed_stdin(monkeypatch, "[youtube dQw4w9WgXcQ]\n\nText with a <^>prose<^> marker.")
        exit_code = main(["pre", "--exclude", "youtube"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "<iframe" not in captured.out
        assert "<mark>prose</mark>" in captured.out

    def test_pre_unknown_use_name_returns_two_with_stderr(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _feed_stdin(monkeypatch, "[youtube dQw4w9WgXcQ]")
        exit_code = main(["pre", "--use", "bogus"])
        captured = capsys.readouterr()
        assert exit_code == 2
        assert "bogus" in captured.err


class TestCliRender:
    """Tests for the render subcommand: stdin Markdown to final HTML via the in-process stack."""

    def test_render_matches_in_process_markwright_render(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        source = "[youtube dQw4w9WgXcQ]\n\nText with a <^>prose<^> marker."
        _feed_stdin(monkeypatch, source)
        exit_code = main(["render"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert '<iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ"' in captured.out
        assert "<mark>prose</mark>" in captured.out
        assert captured.out == _in_process_render(source, list(EXTENSION_NAMES))

    def test_render_use_subset_loads_only_named_extension(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        source = "[youtube dQw4w9WgXcQ]\n\n```\n[label deploy.sh]\necho hi\n```"
        _feed_stdin(monkeypatch, source)
        exit_code = main(["render", "--use", "youtube"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "<iframe" in captured.out
        # fence is not loaded, so the [label ...] directive is never styled into a label div.
        assert "code-label" not in captured.out
        assert captured.out == _in_process_render(source, ["youtube"])

    def test_render_unknown_use_name_returns_two_with_stderr(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _feed_stdin(monkeypatch, "[youtube dQw4w9WgXcQ]")
        exit_code = main(["render", "--use", "bogus"])
        captured = capsys.readouterr()
        assert exit_code == 2
        assert "bogus" in captured.err
