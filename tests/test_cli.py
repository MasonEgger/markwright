# ABOUTME: Tests for the mw CLI entry point: --version, list, usage errors, and post.
# Drives main() with explicit argv and captures stdout/stderr via capsys.

from __future__ import annotations

import io
import subprocess
import sys
import warnings
from importlib.metadata import version as package_version
from typing import TYPE_CHECKING

import markdown

from markwright import ConfigWarning, registry
from markwright.cli import main
from markwright.codepen import CODEPEN_SCRIPT
from markwright.registry import EXTENSION_NAMES

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


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

    def test_post_unknown_exclude_name_returns_two_with_stderr(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _feed_stdin(monkeypatch, "<p>body</p>")
        exit_code = main(["post", "--exclude", "bogus"])
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

    def test_pre_exclude_drops_named_stage(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _feed_stdin(monkeypatch, "[youtube dQw4w9WgXcQ]\n\nText with a <^>prose<^> marker.")
        exit_code = main(["pre", "--exclude", "youtube"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "<iframe" not in captured.out
        assert "<mark>prose</mark>" in captured.out

    def test_pre_honors_config_fence_environments(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        config_path = tmp_path / "markwright.toml"
        config_path.write_text('[fence]\nallowed_environments = ["staging"]\n', encoding="utf-8")
        _feed_stdin(monkeypatch, "```\n[environment production]\necho hi\n```")
        exit_code = main(["pre", "--config", str(config_path)])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert '"environment"' not in captured.out

    def test_pre_unknown_exclude_name_returns_two_with_stderr(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _feed_stdin(monkeypatch, "[youtube dQw4w9WgXcQ]")
        exit_code = main(["pre", "--exclude", "bogus"])
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

    def test_render_unknown_exclude_name_returns_two_with_stderr(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _feed_stdin(monkeypatch, "[youtube dQw4w9WgXcQ]")
        exit_code = main(["render", "--exclude", "bogus"])
        captured = capsys.readouterr()
        assert exit_code == 2
        assert "bogus" in captured.err


class TestCliConfigSelection:
    """Tests that config discovery and --config drive extension selection across subcommands."""

    def test_no_config_no_flags_selects_all(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _feed_stdin(monkeypatch, '<p class="codepen">embed</p>')
        exit_code = main(["post"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert captured.out.count(CODEPEN_SCRIPT) == 1

    def test_config_disable_drops_extension_for_post(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / "markwright.toml").write_text('disable = ["codepen"]\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        _feed_stdin(monkeypatch, '<p class="codepen">embed</p>')
        exit_code = main(["post"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert CODEPEN_SCRIPT not in captured.out

    def test_config_enable_restricts_pre(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        config_path = tmp_path / "markwright.toml"
        config_path.write_text('enable = ["youtube"]\n', encoding="utf-8")
        _feed_stdin(monkeypatch, "[youtube dQw4w9WgXcQ]\n\nText with a <^>prose<^> marker.")
        exit_code = main(["pre", "--config", str(config_path)])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "<iframe" in captured.out
        assert "<mark>prose</mark>" not in captured.out

    def test_config_disable_drops_extension_for_render(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        config_path = tmp_path / "markwright.toml"
        config_path.write_text('enable = ["youtube"]\n', encoding="utf-8")
        source = "[youtube dQw4w9WgXcQ]\n\n```\n[label deploy.sh]\necho hi\n```"
        _feed_stdin(monkeypatch, source)
        exit_code = main(["render", "--config", str(config_path)])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "<iframe" in captured.out
        # fence is not loaded, so the [label ...] directive is never styled into a label div.
        assert "code-label" not in captured.out
        assert captured.out == _in_process_render(source, ["youtube"])

    def test_config_flag_loads_explicit_file(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        config_path = tmp_path / "custom.toml"
        config_path.write_text('disable = ["codepen"]\n', encoding="utf-8")
        _feed_stdin(monkeypatch, '<p class="codepen">embed</p>')
        exit_code = main(["post", "--config", str(config_path)])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert CODEPEN_SCRIPT not in captured.out

    def test_exclude_removes_from_config_resolved_set(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        config_path = tmp_path / "markwright.toml"
        config_path.write_text('enable = ["codepen"]\n', encoding="utf-8")
        _feed_stdin(monkeypatch, '<p class="codepen">embed</p>')
        exit_code = main(["post", "--config", str(config_path), "--exclude", "codepen"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert CODEPEN_SCRIPT not in captured.out

    def test_use_flag_is_rejected(self, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = main(["post", "--use", "highlight"])
        assert exit_code == 2

    def test_config_flag_missing_file_returns_two(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _feed_stdin(monkeypatch, "<p>body</p>")
        exit_code = main(["post", "--config", str(tmp_path / "absent.toml")])
        captured = capsys.readouterr()
        assert exit_code == 2
        assert "not found" in captured.err


class TestCliRenderOptions:
    """Tests that mw render applies per-extension options from config (R4)."""

    _ENV_SOURCE = "```\n[environment production]\necho hi\n```"

    def test_render_without_config_allows_any_environment(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _feed_stdin(monkeypatch, self._ENV_SOURCE)
        exit_code = main(["render"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "environment-production" in captured.out

    def test_render_config_allowlist_rejects_unlisted_environment(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        config_path = tmp_path / "markwright.toml"
        config_path.write_text('[fence]\nallowed_environments = ["staging"]\n', encoding="utf-8")
        _feed_stdin(monkeypatch, self._ENV_SOURCE)
        exit_code = main(["render", "--config", str(config_path)])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "environment-production" not in captured.out

    def test_render_config_allowlist_accepts_listed_environment(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        config_path = tmp_path / "markwright.toml"
        config_path.write_text('[fence]\nallowed_environments = ["staging"]\n', encoding="utf-8")
        _feed_stdin(monkeypatch, "```\n[environment staging]\necho hi\n```")
        exit_code = main(["render", "--config", str(config_path)])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "environment-staging" in captured.out


class TestCliConfig:
    """Tests for the mw config command: the resolved config and the source of each value."""

    def test_no_config_shows_all_on_from_defaults(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(tmp_path)
        exit_code = main(["config"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "fence: on (default)" in captured.out
        assert "youtube: on (default)" in captured.out
        assert "warn: false (default)" in captured.out
        assert "options: none" in captured.out

    def test_config_cites_file_for_disabled_extension(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        config_path = tmp_path / "markwright.toml"
        config_path.write_text('disable = ["youtube"]\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        exit_code = main(["config"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert f"youtube: off ({config_path})" in captured.out
        assert "fence: on (default)" in captured.out

    def test_config_flag_is_honored(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        config_path = tmp_path / "custom.toml"
        config_path.write_text('enable = ["fence"]\n', encoding="utf-8")
        exit_code = main(["config", "--config", str(config_path)])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert f"fence: on ({config_path})" in captured.out
        assert f"youtube: off ({config_path})" in captured.out

    def test_config_exclude_is_marked_as_flag_source(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(tmp_path)
        exit_code = main(["config", "--exclude", "codepen"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "codepen: off (--exclude)" in captured.out

    def test_config_reports_options_with_source(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        config_path = tmp_path / "markwright.toml"
        config_path.write_text('[fence]\nallowed_environments = ["staging"]\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        exit_code = main(["config"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "options:" in captured.out
        assert "fence:" in captured.out
        assert "staging" in captured.out
        assert str(config_path) in captured.out

    def test_config_reports_warn_from_file(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        config_path = tmp_path / "markwright.toml"
        config_path.write_text("warn = true\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        exit_code = main(["config"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert f"warn: true ({config_path})" in captured.out

    def test_config_reports_load_per_embed(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        config_path = tmp_path / "markwright.toml"
        config_path.write_text('[twitter]\nload = "click"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        exit_code = main(["config"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "load:\n" in captured.out
        assert f"  twitter: click ({config_path})" in captured.out
        assert "  youtube: eager (default)" in captured.out
        assert "  slideshow: eager" not in captured.out

    def test_render_applies_configured_load(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / "markwright.toml").write_text('[youtube]\nload = "click"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("sys.stdin", io.StringIO("[youtube dQw4w9WgXcQ]\n"))
        exit_code = main(["render"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert 'data-mw-load="click"' in captured.out

    def test_empty_enable_runs_no_extensions_and_warns(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        config_path = tmp_path / "markwright.toml"
        config_path.write_text("enable = []\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("sys.stdin", io.StringIO("[youtube dQw4w9WgXcQ]\n"))
        exit_code = main(["pre", "--exclude", "fence"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert captured.out == "[youtube dQw4w9WgXcQ]\n"
        # One warning naming the config cause; --exclude adds no second warning on top
        assert captured.err == (
            f"mw: warning: no markwright extensions selected ('enable' is empty in {config_path});"
            " markwright syntax passes through unprocessed\n"
        )

    def test_exclude_removing_every_extension_warns(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("sys.stdin", io.StringIO("text\n"))
        exclude_flags = [flag for name in EXTENSION_NAMES for flag in ("--exclude", name)]
        exit_code = main(["pre", *exclude_flags])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert captured.err.count("mw: warning: ") == 1
        assert "no markwright extensions selected (--exclude removed every one)" in captured.err

    def test_empty_fence_environments_warns_once(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / "markwright.toml").write_text("[fence]\nallowed_environments = []\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("sys.stdin", io.StringIO("```\n[environment local]\necho hi\n```\n"))
        exit_code = main(["render"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "environment-local" not in captured.out
        assert captured.err.count("mw: warning: ") == 1
        assert "allowed_environments" in captured.err

    def test_empty_selection_warning_reaches_real_stderr(self, tmp_path: Path) -> None:
        # Without any logging setup, the warning must still reach stderr and leave stdout clean for the pipe
        (tmp_path / "markwright.toml").write_text("enable = []\n", encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, "-c", "import sys; from markwright.cli import main; sys.exit(main(['pre']))"],
            input="[youtube dQw4w9WgXcQ]\n",
            capture_output=True,
            text=True,
            cwd=tmp_path,
            check=False,
        )
        assert completed.returncode == 0
        assert completed.stdout == "[youtube dQw4w9WgXcQ]\n"
        assert completed.stderr.startswith("mw: warning: no markwright extensions selected")

    def test_unknown_option_key_is_a_usage_error_not_a_traceback(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / "markwright.toml").write_text("[fence]\ntypo_option = 1\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("sys.stdin", io.StringIO("x\n"))
        exit_code = main(["render"])
        captured = capsys.readouterr()
        assert exit_code == 2
        assert captured.err.startswith("mw: error: ")
        assert "unknown option 'typo_option'" in captured.err
        assert "Traceback" not in captured.err

    def test_escalated_config_warning_exits_two(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / "markwright.toml").write_text("enable = []\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("sys.stdin", io.StringIO("x\n"))
        with warnings.catch_warnings():
            warnings.simplefilter("error", ConfigWarning)
            exit_code = main(["pre"])
        captured = capsys.readouterr()
        assert exit_code == 2
        assert captured.out == ""
        assert captured.err.startswith("mw: error: no markwright extensions selected")

    def test_other_warnings_keep_the_python_format(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def warning_pre(text: str, names: list[str], options: object = None) -> str:
            warnings.warn("a library deprecation", DeprecationWarning, stacklevel=1)
            return text

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(registry, "run_pre", warning_pre)
        monkeypatch.setattr("sys.stdin", io.StringIO("x\n"))
        with warnings.catch_warnings():
            warnings.simplefilter("always")
            exit_code = main(["pre"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "DeprecationWarning: a library deprecation" in captured.err
        assert "mw: warning: a library deprecation" not in captured.err

    def test_post_applies_configured_label_class(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / "markwright.toml").write_text('[fence]\nlabel_class = "my-label"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        marked = '<!-- mw-fence:{"version": 1, "label": "a.sh"} -->\n<pre><code>x\n</code></pre>'
        monkeypatch.setattr("sys.stdin", io.StringIO(marked))
        exit_code = main(["post"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert '<div class="my-label" title="a.sh">a.sh</div>' in captured.out

    def test_config_unknown_exclude_name_returns_two(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(tmp_path)
        exit_code = main(["config", "--exclude", "bogus"])
        captured = capsys.readouterr()
        assert exit_code == 2
        assert "bogus" in captured.err
