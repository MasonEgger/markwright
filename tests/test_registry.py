# ABOUTME: Tests for the stage registry that selects and composes pipeline stages.
# Covers run_pre/run_post ordering, warning and option threading, option names, and describe.

from __future__ import annotations

import pytest

from markwright.registry import EXTENSION_NAMES, OPTION_NAMES, describe, run_post, run_pre


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

    def test_threads_options_into_fence_stage(self) -> None:
        html_input = '<!-- mw-fence:{"version": 1, "label": "a.sh"} -->\n<pre><code>x\n</code></pre>'
        result = run_post(html_input, ["fence"], options={"fence": {"label_class": "my-label"}})
        assert '<div class="my-label" title="a.sh">a.sh</div>' in result


class TestOptionNames:
    """Tests that each extension's accepted option names come from its Python-Markdown config."""

    def test_option_names_per_extension(self) -> None:
        assert OPTION_NAMES["fence"] == {"label_class", "secondary_label_class", "allowed_environments"}
        assert OPTION_NAMES["youtube"] == {"load"}
        assert OPTION_NAMES["slideshow"] == frozenset()
        assert set(OPTION_NAMES) == set(EXTENSION_NAMES)


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

        def _noop_post(html: str, warnings: list[str] | None = None, options: object = None) -> str:
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
