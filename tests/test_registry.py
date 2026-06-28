# ABOUTME: Tests for the stage registry that selects and composes pipeline stages.
# Covers select_extensions validation, run_pre/run_post ordering, warning threading, and describe.

from __future__ import annotations

import pytest

from markwright.registry import EXTENSION_NAMES, describe, run_post, run_pre, select_extensions


class TestSelectExtensions:
    """Tests for select_extensions resolving the active extension set."""

    def test_default_returns_all_eight(self) -> None:
        selected = select_extensions(use=[], exclude=[])
        assert set(selected) == set(EXTENSION_NAMES)
        assert len(selected) == 8

    def test_use_returns_only_named(self) -> None:
        selected = select_extensions(use=["youtube", "highlight"], exclude=[])
        assert set(selected) == {"youtube", "highlight"}

    def test_exclude_drops_named(self) -> None:
        selected = select_extensions(use=[], exclude=["youtube"])
        assert "youtube" not in selected
        assert set(selected) == set(EXTENSION_NAMES) - {"youtube"}

    def test_unknown_name_raises_value_error_naming_token(self) -> None:
        with pytest.raises(ValueError, match="bogus"):
            select_extensions(use=["bogus"], exclude=[])

    def test_unknown_exclude_name_raises_value_error_naming_token(self) -> None:
        with pytest.raises(ValueError, match="nope"):
            select_extensions(use=[], exclude=["nope"])


class TestRunPre:
    """Tests for run_pre composing the selected source-stage functions."""

    def test_composes_embed_and_prose_mark(self) -> None:
        source = "[youtube dQw4w9WgXcQ]\n\nText with a <^>prose<^> marker."
        result = run_pre(source, ["youtube", "highlight"])
        assert '<iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ"' in result
        assert "<mark>prose</mark>" in result

    def test_unselected_stage_is_skipped(self) -> None:
        source = "[youtube dQw4w9WgXcQ]\n\nText with a <^>prose<^> marker."
        result = run_pre(source, ["highlight"])
        assert "<iframe" not in result
        assert "<mark>prose</mark>" in result


class TestRunPost:
    """Tests for run_post composing the selected HTML-stage functions."""

    def test_composes_script_inject_and_mark_wrap(self) -> None:
        html_input = '<p class="codepen" data-slug-hash="vwPzeX"></p>\n<p>a &lt;^&gt;word&lt;^&gt; b</p>'
        result = run_post(html_input, ["codepen", "highlight"])
        assert result.count("static.codepen.io/assets/embed/ei.js") == 1
        assert "<mark>word</mark>" in result

    def test_threads_warnings_into_fence_stage(self) -> None:
        html_input = "<!-- mw-fence:{not json -->\n<pre><code>x\n</code></pre>"
        warnings: list[str] = []
        run_post(html_input, ["fence"], warnings)
        assert len(warnings) == 1


class TestDescribe:
    """Tests for describe reporting each extension's available stages."""

    def test_lists_every_extension_with_stages(self) -> None:
        described = dict(describe())
        assert set(described) == set(EXTENSION_NAMES)
        assert described["youtube"] == ["pre"]
        assert described["fence"] == ["pre", "post"]
        assert described["highlight"] == ["pre", "post"]
        assert described["codepen"] == ["pre", "post"]

    def test_describe_handles_post_only_extension(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # No real extension is post-only (all have a pre stage), so exercise the
        # pre-is-None branch of describe() with a synthetic post-only entry.
        from markwright import registry

        def _noop_post(html: str, warnings: list[str] | None = None) -> str:
            return html

        patched = dict(registry.REGISTRY)
        patched["synthetic_post_only"] = {
            "pre": None,
            "post": _noop_post,
            "pre_priority": 0,
            "post_priority": 0,
        }
        monkeypatch.setattr(registry, "REGISTRY", patched)
        monkeypatch.setattr(registry, "EXTENSION_NAMES", [*registry.EXTENSION_NAMES, "synthetic_post_only"])
        described = dict(registry.describe())
        assert described["synthetic_post_only"] == ["post"]
