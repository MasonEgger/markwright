# ABOUTME: Tests for the fence extension handling label, secondary_label, environment, and prefix directives.
# Verifies directive extraction, HTML injection, environment classes, line prefixes, and edge cases.

from __future__ import annotations

import warnings

import markdown
import pytest

from markwright import ConfigWarning, Diagnostic, OptionError, RenderWarning
from markwright.fence import FenceExtension, apply_html, environment_names, expand_source
from markwright.registry import run_post, run_pre


def messages(diagnostics: list[Diagnostic]) -> list[str]:
    """Return the --warn message of each diagnostic."""
    return [diagnostic.message for diagnostic in diagnostics]


def _stub_render(markdown_text: str) -> str:
    """Render Markdown through superfences and highlight only, preserving raw HTML comments.

    Stands in for an external renderer (the ``mw pre | post`` path) that knows
    nothing about markwright directives, mirroring ``tests/test_roundtrip.py``'s
    ``stub_render``.
    """
    instance = markdown.Markdown(
        extensions=["pymdownx.superfences", "pymdownx.highlight"],
        extension_configs={"pymdownx.highlight": {"pygments_lang_class": True}},
    )
    return instance.convert(markdown_text)


def render_fence(source: str, allowed_environments: list[str] | None = None) -> str:
    """Render source with superfences, highlight, and fence extensions loaded."""
    extension_configs: dict[str, dict[str, object]] = {"pymdownx.highlight": {"pygments_lang_class": True}}
    if allowed_environments is not None:
        extension_configs["markwright.fence"] = {"allowed_environments": allowed_environments}
    md = markdown.Markdown(
        extensions=["pymdownx.superfences", "pymdownx.highlight", "markwright.fence"],
        extension_configs=extension_configs,
    )
    return md.convert(source)


class TestLabelBasic:
    def test_label_renders_div_before_code(self) -> None:
        source = "```\n[label test.py]\nhello\n```"
        result = render_fence(source)
        assert '<div class="code-label" title="test.py">test.py</div>' in result

    def test_label_content_preserved(self) -> None:
        source = "```\n[label test.py]\nhello\n```"
        result = render_fence(source)
        assert "hello" in result

    def test_label_directive_stripped(self) -> None:
        source = "```\n[label test.py]\nhello\n```"
        result = render_fence(source)
        assert "[label test.py]" not in result


class TestLabelWithLanguage:
    def test_label_with_python(self) -> None:
        source = "```python\n[label app.py]\nprint('hi')\n```"
        result = render_fence(source)
        assert '<div class="code-label" title="app.py">app.py</div>' in result

    def test_language_class_preserved(self) -> None:
        source = "```python\n[label app.py]\nprint('hi')\n```"
        result = render_fence(source)
        assert "python" in result


class TestSecondaryLabel:
    def test_secondary_label_renders(self) -> None:
        source = "```\n[secondary_label Output]\nerror msg\n```"
        result = render_fence(source)
        assert '<div class="secondary-code-label" title="Output">Output</div>' in result

    def test_secondary_label_directive_stripped(self) -> None:
        source = "```\n[secondary_label Output]\nerror msg\n```"
        result = render_fence(source)
        assert "[secondary_label Output]" not in result


class TestNoDirectives:
    def test_no_label_no_comment(self) -> None:
        source = "```\nplain code\n```"
        result = render_fence(source)
        assert "do-fence" not in result

    def test_no_label_no_label_div(self) -> None:
        source = "```\nplain code\n```"
        result = render_fence(source)
        assert "code-label" not in result

    def test_text_surrounding_fence_preserved(self) -> None:
        source = "Some text before\n\n```\n[label test.py]\ncode\n```\n\nSome text after"
        result = render_fence(source)
        assert "Some text before" in result
        assert "Some text after" in result
        assert '<div class="code-label" title="test.py">test.py</div>' in result


class TestLabelSpecialChars:
    def test_label_with_path(self) -> None:
        source = "```\n[label /etc/nginx/sites-available/default]\ncode\n```"
        result = render_fence(source)
        assert "/etc/nginx/sites-available/default" in result
        assert '<div class="code-label"' in result

    def test_label_html_escaped(self) -> None:
        source = '```\n[label <script>alert("xss")</script>]\ncode\n```'
        result = render_fence(source)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


class TestBothLabels:
    def test_both_label_and_secondary_label(self) -> None:
        source = "```\n[label file.py]\n[secondary_label Output]\ncode\n```"
        result = render_fence(source)
        assert '<div class="code-label" title="file.py">file.py</div>' in result
        assert '<div class="secondary-code-label" title="Output">Output</div>' in result

    def test_directives_stripped_from_content(self) -> None:
        source = "```\n[label file.py]\n[secondary_label Output]\ncode\n```"
        result = render_fence(source)
        assert "[label file.py]" not in result
        assert "[secondary_label Output]" not in result


class TestEnvironmentBasic:
    def test_environment_class_on_pre(self) -> None:
        source = "```\n[environment local]\nssh root@server\n```"
        result = render_fence(source)
        assert "environment-local" in result

    def test_environment_directive_stripped(self) -> None:
        source = "```\n[environment local]\nssh root@server\n```"
        result = render_fence(source)
        assert "[environment local]" not in result


class TestEnvironmentAllowedList:
    def test_allowed_environment_applied(self) -> None:
        source = "```\n[environment local]\ncode\n```"
        result = render_fence(source, allowed_environments=["local", "staging", "production"])
        assert "environment-local" in result

    def test_disallowed_environment_not_applied(self) -> None:
        source = "```\n[environment unknown]\ncode\n```"
        result = render_fence(source, allowed_environments=["local", "staging", "production"])
        assert "environment-unknown" not in result
        assert "[environment unknown]" in result

    def test_omitted_allowed_list_allows_all(self) -> None:
        source = "```\n[environment custom]\ncode\n```"
        result = render_fence(source)
        assert "environment-custom" in result

    def test_empty_allowed_list_allows_none_and_warns(self) -> None:
        source = "```\n[environment custom]\ncode\n```"
        with pytest.warns(ConfigWarning, match="allowed_environments"):
            result = render_fence(source, allowed_environments=[])
        assert "environment-custom" not in result
        assert "[environment custom]" in result

    def test_null_allowed_list_counts_as_omitted(self) -> None:
        source = "```\n[environment custom]\ncode\n```"
        assert "environment-custom" in render_fence(source, allowed_environments=None)
        assert '"environment": "custom"' in expand_source(source, {"allowed_environments": None})

    def test_set_config_after_construction_is_honored(self) -> None:
        extension = FenceExtension()
        extension.setConfig("allowed_environments", ["local"])
        instance = markdown.Markdown(extensions=["pymdownx.superfences", extension])
        result = instance.convert("```\n[environment staging]\ncode\n```")
        assert "environment-staging" not in result

    def test_non_string_label_class_raises(self) -> None:
        with pytest.raises(OptionError, match="label_class"):
            markdown.Markdown(
                extensions=["markwright.fence"], extension_configs={"markwright.fence": {"label_class": 3}}
            )

    @pytest.mark.parametrize("bad_value", ['a"b', "a<b", "a.b", "", "  ", "a  b ;"])
    def test_label_class_that_is_not_class_tokens_raises(self, bad_value: str) -> None:
        with pytest.raises(OptionError, match="label_class"):
            apply_html("", None, {"label_class": bad_value})

    def test_secondary_label_class_that_is_not_class_tokens_raises(self) -> None:
        with pytest.raises(OptionError, match="secondary_label_class"):
            apply_html("", None, {"secondary_label_class": "bad>"})

    def test_space_separated_class_tokens_are_accepted(self) -> None:
        marked = '<!-- mw-fence:{"version": 1, "label": "a.sh"} -->\n<pre><code>x\n</code></pre>'
        result = apply_html(marked, None, {"label_class": "my-label a_b c1"})
        assert '<div class="my-label a_b c1" title="a.sh">a.sh</div>' in result

    def test_non_list_allowed_environments_raises(self) -> None:
        with pytest.raises(OptionError, match="allowed_environments"):
            markdown.Markdown(
                extensions=["markwright.fence"],
                extension_configs={"markwright.fence": {"allowed_environments": "local"}},
            )


class TestEnvironmentWithLabel:
    def test_environment_and_label_together(self) -> None:
        source = "```\n[environment local]\n[label server.sh]\ncode\n```"
        result = render_fence(source)
        assert "environment-local" in result
        assert '<div class="code-label" title="server.sh">server.sh</div>' in result

    def test_environment_and_secondary_label_together(self) -> None:
        source = "```\n[environment second]\n[secondary_label Output]\ncode\n```"
        result = render_fence(source)
        assert "environment-second" in result
        assert '<div class="secondary-code-label" title="Output">Output</div>' in result


class TestEnvironmentVariants:
    def test_second_environment(self) -> None:
        source = "```\n[environment second]\ncode\n```"
        result = render_fence(source)
        assert "environment-second" in result

    def test_third_environment(self) -> None:
        source = "```\n[environment third]\ncode\n```"
        result = render_fence(source)
        assert "environment-third" in result

    def test_directive_order_environment_after_label(self) -> None:
        source = "```\n[label server.sh]\n[environment local]\ncode\n```"
        result = render_fence(source)
        assert "environment-local" in result
        assert '<div class="code-label" title="server.sh">server.sh</div>' in result


class TestLineNumbers:
    def test_line_numbers_data_prefix(self) -> None:
        source = "```line_numbers,js\nconst a = 1;\nconst b = 2;\n```"
        result = render_fence(source)
        assert 'data-prefix="1"' in result
        assert 'data-prefix="2"' in result

    def test_line_numbers_ol_wrapper(self) -> None:
        source = "```line_numbers,js\nconst a = 1;\nconst b = 2;\n```"
        result = render_fence(source)
        assert "<ol>" in result
        assert "</ol>" in result

    def test_line_numbers_prefixed_class(self) -> None:
        source = "```line_numbers,js\nconst a = 1;\n```"
        result = render_fence(source)
        assert "prefixed" in result
        assert "line_numbers" in result

    def test_line_numbers_with_language(self) -> None:
        source = "```line_numbers,python\nprint('hi')\n```"
        result = render_fence(source)
        assert 'data-prefix="1"' in result
        assert "python" in result


class TestCommand:
    def test_command_dollar_prefix(self) -> None:
        source = "```command\nsudo apt update\n```"
        result = render_fence(source)
        assert 'data-prefix="$"' in result

    def test_command_prefixed_class(self) -> None:
        source = "```command\nsudo apt update\n```"
        result = render_fence(source)
        assert "prefixed" in result
        assert "command" in result

    def test_command_bash_language(self) -> None:
        source = "```command\nsudo apt update\n```"
        result = render_fence(source)
        assert "bash" in result


class TestSuperUser:
    def test_super_user_hash_prefix(self) -> None:
        source = "```super_user\nshutdown\n```"
        result = render_fence(source)
        assert 'data-prefix="#"' in result

    def test_super_user_prefixed_class(self) -> None:
        source = "```super_user\nshutdown\n```"
        result = render_fence(source)
        assert "prefixed" in result
        assert "super_user" in result


class TestCustomPrefix:
    def test_custom_prefix_value(self) -> None:
        source = "```custom_prefix(mysql>)\nSELECT 1;\n```"
        result = render_fence(source)
        assert 'data-prefix="mysql&gt;"' in result

    def test_custom_prefix_class(self) -> None:
        source = "```custom_prefix(mysql>)\nSELECT 1;\n```"
        result = render_fence(source)
        assert "prefixed" in result
        assert "custom_prefix" in result

    def test_custom_prefix_backslash_s(self) -> None:
        source = "```custom_prefix((srv)\\smysql>)\nSELECT 1;\n```"
        result = render_fence(source)
        assert 'data-prefix="(srv) mysql&gt;"' in result


class TestPrefixCombined:
    def test_command_with_environment_and_label(self) -> None:
        source = "```command\n[environment local]\n[label server.sh]\nssh root@ip\n```"
        result = render_fence(source)
        assert 'data-prefix="$"' in result
        assert "environment-local" in result
        assert '<div class="code-label" title="server.sh">server.sh</div>' in result

    def test_no_prefix_plain_code(self) -> None:
        source = "```python\ncode\n```"
        result = render_fence(source)
        assert "<ol>" not in result
        assert "data-prefix" not in result
        assert "prefixed" not in result


class TestPrefixFullCombo:
    def test_line_numbers_environment_label_language(self) -> None:
        source = "```line_numbers,html\n[environment second]\n[label index.html]\n<html>\n<body>\n</body>\n</html>\n```"
        result = render_fence(source)
        assert 'data-prefix="1"' in result
        assert 'data-prefix="4"' in result
        assert "environment-second" in result
        assert '<div class="code-label" title="index.html">index.html</div>' in result
        assert "prefixed" in result
        assert "line_numbers" in result


class TestFenceExpandSource:
    def test_label_emits_mw_fence_marker(self) -> None:
        source = "```\n[label deploy.sh]\necho hi\n```"
        result = expand_source(source)
        assert "<!-- mw-fence:" in result
        assert '"version": 1' in result
        assert '"label": "deploy.sh"' in result

    def test_label_directive_removed_fence_and_code_remain(self) -> None:
        source = "```\n[label deploy.sh]\necho hi\n```"
        result = expand_source(source)
        assert "[label deploy.sh]" not in result
        assert "echo hi" in result
        assert "```" in result

    def test_command_fence_emits_prefix_metadata(self) -> None:
        source = "```command\necho hi\n```"
        result = expand_source(source)
        assert '"prefix_type": "command"' in result
        assert '"prefix_value": "$"' in result

    def test_plain_fence_no_marker_unchanged(self) -> None:
        source = "```\nplain code\n```"
        result = expand_source(source)
        assert "mw-fence" not in result
        assert result == source

    def test_options_allowed_environments_restrict_extraction(self) -> None:
        source = "```\n[environment production]\necho hi\n```"
        result = expand_source(source, {"allowed_environments": ["staging"]})
        assert '"environment"' not in result

    def test_options_empty_environment_list_allows_none_and_warns(self) -> None:
        source = "```\n[environment production]\necho hi\n```"
        with pytest.warns(ConfigWarning, match="allowed_environments"):
            result = expand_source(source, {"allowed_environments": []})
        assert '"environment"' not in result

    @pytest.mark.parametrize("earlier_flag", ["command", "super_user", "custom_prefix(>)"])
    def test_line_numbers_after_a_prefix_flag_drops_prefix_value(self, earlier_flag: str) -> None:
        result = expand_source(f"```{earlier_flag},line_numbers\ncode\n```")
        assert '"prefix_type": "line_numbers"' in result
        assert "prefix_value" not in result

    def test_options_non_list_environment_value_raises(self) -> None:
        with pytest.raises(OptionError, match="allowed_environments"):
            expand_source("text", {"allowed_environments": [1]})

    def test_apply_html_honors_label_class_options(self) -> None:
        marked = (
            '<!-- mw-fence:{"version": 1, "label": "a.sh", "secondary_label": "out"} -->\n<pre><code>x\n</code></pre>'
        )
        result = apply_html(marked, None, {"label_class": "my-label", "secondary_label_class": "my-secondary"})
        assert '<div class="my-label" title="a.sh">a.sh</div>' in result
        assert '<div class="my-secondary" title="out">out</div>' in result

    def test_options_without_environment_list_allow_all(self) -> None:
        source = "```\n[environment production]\necho hi\n```"
        result = expand_source(source, {})
        assert '"environment": "production"' in result


class TestFenceApplyHtml:
    def test_label_marker_injects_div_and_removes_comment(self) -> None:
        html_input = '<!-- mw-fence:{"version": 1, "label": "deploy.sh"} -->\n<pre><code>echo hi\n</code></pre>'
        result = apply_html(html_input)
        assert '<div class="code-label" title="deploy.sh">deploy.sh</div>' in result
        assert "<!-- mw-fence:" not in result

    def test_command_marker_wraps_lines_with_prefix(self) -> None:
        html_input = (
            '<!-- mw-fence:{"version": 1, "prefix_type": "command", "prefix_value": "$"} -->\n'
            "<pre><code>sudo apt update\n</code></pre>"
        )
        result = apply_html(html_input)
        assert "<ol>" in result
        assert 'data-prefix="$"' in result

    @pytest.mark.parametrize(
        ("payload", "reason"),
        [
            ("[1]", "not an object"),
            ("null", "not an object"),
            ('"x"', "not an object"),
            ('{"version": 1, "label": 5}', "invalid fields (label)"),
            ('{"version": 1, "prefix_type": "bogus"}', "invalid fields (prefix_type)"),
        ],
    )
    def test_wrong_shape_payload_skips_instead_of_crashing(self, payload: str, reason: str) -> None:
        diagnostics: list[Diagnostic] = []
        result = apply_html(f"<!-- mw-fence:{payload} -->\n<pre><code>x\n</code></pre>", diagnostics)
        assert result == "\n<pre><code>x\n</code></pre>"
        assert len(diagnostics) == 1
        assert reason in diagnostics[0].message

    def test_unknown_payload_fields_are_ignored(self) -> None:
        marked = '<!-- mw-fence:{"version": 1, "label": "a.sh", "future_field": 3} -->\n<pre><code>x\n</code></pre>'
        assert '<div class="code-label" title="a.sh">a.sh</div>' in apply_html(marked)

    def test_each_marker_styles_only_its_own_block(self) -> None:
        marked = (
            '<!-- mw-fence:{"version": 1, "environment": "a"} -->\n<p>no code</p>\n'
            '<!-- mw-fence:{"version": 1, "environment": "b"} -->\n<pre><code>x\n</code></pre>'
        )
        diagnostics: list[Diagnostic] = []
        result = apply_html(marked, diagnostics)
        assert '<pre class="environment-b">' in result
        assert "environment-a" not in result
        assert messages(diagnostics) == ["Skipping mw-fence marker with no following code block"]

    def test_malformed_json_warns_and_skips(self) -> None:
        html_input = "<!-- mw-fence:{not json -->\n<pre><code>x\n</code></pre>"
        diagnostics: list[Diagnostic] = []
        result = apply_html(html_input, diagnostics)
        assert len(diagnostics) == 1
        assert "code-label" not in result
        assert "<!-- mw-fence:" not in result

    def test_unsupported_version_warns_and_skips(self) -> None:
        html_input = '<!-- mw-fence:{"version": 999, "label": "x"} -->\n<pre><code>x\n</code></pre>'
        diagnostics: list[Diagnostic] = []
        result = apply_html(html_input, diagnostics)
        assert len(diagnostics) == 1
        assert "code-label" not in result

    def test_no_following_code_block_warns(self) -> None:
        html_input = '<!-- mw-fence:{"version": 1, "label": "x"} -->\n<p>no code here</p>'
        diagnostics: list[Diagnostic] = []
        result = apply_html(html_input, diagnostics)
        assert len(diagnostics) == 1
        assert "code-label" not in result

    def test_warnings_none_is_silent_no_op(self) -> None:
        malformed = "<!-- mw-fence:{not json -->\n<pre><code>x\n</code></pre>"
        bad_version = '<!-- mw-fence:{"version": 999, "label": "x"} -->\n<pre><code>x\n</code></pre>'
        no_block = '<!-- mw-fence:{"version": 1, "label": "x"} -->\n<p>no code here</p>'
        for html_input in (malformed, bad_version, no_block):
            result = apply_html(html_input)
            assert "code-label" not in result


class TestFenceDegradesOnIncompleteBlocks:
    """Markers and fences with missing pieces degrade to plain output without raising."""

    def test_unclosed_fence_is_not_a_code_block(self) -> None:
        # superfences renders an unclosed fence as text, so no marker is emitted for it
        source = "```command\n[label deploy.sh]\nssh root@server"
        assert expand_source(source) == source

    def test_prefix_code_without_trailing_newline(self) -> None:
        # Code content with no trailing newline before </code>.
        html_input = (
            '<!-- mw-fence:{"version": 1, "prefix_type": "command", "prefix_value": "$"} -->\n'
            "<pre><code>echo hi</code></pre>"
        )
        result = apply_html(html_input)
        assert '<li data-prefix="$">echo hi' in result

    def test_environment_marker_with_code_but_no_pre(self) -> None:
        # A <code> follows (passes the adjacency check) but there is no <pre> to class.
        html_input = '<!-- mw-fence:{"version": 1, "environment": "local"} -->\n<code>x</code>'
        result = apply_html(html_input)
        assert "<!-- mw-fence:" not in result
        assert "<code>x</code>" in result

    def test_prefix_marker_with_pre_but_no_code(self) -> None:
        # A <pre> follows but there is no <code> block to wrap.
        html_input = '<!-- mw-fence:{"version": 1, "prefix_type": "command", "prefix_value": "$"} -->\n<pre>x</pre>'
        result = apply_html(html_input)
        assert 'class="prefixed command"' in result
        assert "<ol>" not in result

    def test_prefix_marker_with_unclosed_code(self) -> None:
        # A <code> opens but never closes: nothing to wrap.
        html_input = '<!-- mw-fence:{"version": 1, "prefix_type": "command", "prefix_value": "$"} -->\n<code>x'
        result = apply_html(html_input)
        assert "<!-- mw-fence:" not in result
        assert "<ol>" not in result

    def test_secondary_label_marker_with_pre_but_no_code(self) -> None:
        # secondary_label present but no <code> to insert it after.
        html_input = '<!-- mw-fence:{"version": 1, "secondary_label": "config"} -->\n<pre>y</pre>'
        result = apply_html(html_input)
        assert "<!-- mw-fence:" not in result
        assert "secondary-code-label" not in result


class TestFenceChromaPrefix:
    """Prefix wrapping must handle Chroma (Hugo) output, which wraps each line in
    <span class="line"><span class="cl">...newline...</span></span>. Splitting that
    on newlines cuts the line span in half and emits a spurious empty prefixed line."""

    def test_single_line_command_one_prefix(self) -> None:
        # One Chroma line must produce exactly one <li>, not two.
        html_input = (
            '<!-- mw-fence:{"version": 1, "prefix_type": "command", "prefix_value": "$"} -->\n'
            '<pre class="chroma"><code class="language-bash">'
            '<span class="line"><span class="cl">./deploy.sh --prod\n</span></span></code></pre>'
        )
        result = apply_html(html_input)
        assert result.count('<li data-prefix="$">') == 1
        # The line span stays intact inside the single <li> (no cross-<li> split).
        assert '<li data-prefix="$"><span class="line"><span class="cl">./deploy.sh --prod' in result
        assert "</li><li" not in result
        # The newline Chroma put inside the span is the only one; the wrap adds none.
        assert (
            '<ol><li data-prefix="$"><span class="line"><span class="cl">./deploy.sh --prod\n</span></span></li></ol>\n'
            in result
        )

    def test_multi_line_chroma_one_prefix_per_line(self) -> None:
        html_input = (
            '<!-- mw-fence:{"version": 1, "prefix_type": "line_numbers"} -->\n'
            '<pre class="chroma"><code class="language-js">'
            '<span class="line"><span class="cl">const value = x;\n</span></span>'
            '<span class="line"><span class="cl">console.log(value);\n</span></span></code></pre>'
        )
        result = apply_html(html_input)
        assert result.count("<li data-prefix=") == 2
        assert 'data-prefix="1"' in result
        assert 'data-prefix="2"' in result
        assert 'data-prefix="3"' not in result

    def test_chroma_unclosed_line_span_does_not_raise(self) -> None:
        # Defensive: a line span with no matching close still yields one line.
        html_input = (
            '<!-- mw-fence:{"version": 1, "prefix_type": "command", "prefix_value": "$"} -->\n'
            '<pre class="chroma"><code><span class="line"><span class="cl">x</code></pre>'
        )
        result = apply_html(html_input)
        assert result.count('<li data-prefix="$">') == 1


class TestFenceMarkerXss:
    """Step-55 regression: a directive value containing "-->" must not close the
    mw-fence marker comment early and inject live markup (stored XSS)."""

    PROBE = "```\n[label foo --> <script>alert(1)</script>]\ncode\n```"

    def test_expand_source_marker_has_no_early_terminator(self) -> None:
        result = expand_source(self.PROBE)
        marker_line = next(line for line in result.split("\n") if line.startswith("<!-- mw-fence:"))
        # The only "-->" in the line must be the comment's own terminator.
        assert marker_line.count("-->") == 1
        assert "<script>" not in marker_line

    def test_render_path_has_no_live_script(self) -> None:
        result = render_fence(self.PROBE)
        assert "<script>alert(1)</script>" not in result

    def test_pre_post_path_has_no_live_script(self) -> None:
        rendered = _stub_render(expand_source(self.PROBE))
        result = apply_html(rendered)
        assert "<script>alert(1)</script>" not in result

    def test_benign_greater_than_label_round_trips(self) -> None:
        source = "```\n[label a > b]\ncode\n```"
        result = render_fence(source)
        assert '<div class="code-label" title="a &gt; b">a &gt; b</div>' in result

    def test_benign_hyphen_label_round_trips(self) -> None:
        source = "```\n[label build-all]\ncode\n```"
        result = render_fence(source)
        assert '<div class="code-label" title="build-all">build-all</div>' in result

    def test_benign_labels_survive_pre_post_path(self) -> None:
        source = "```\n[label a > b]\ncode\n```"
        rendered = _stub_render(expand_source(source))
        result = apply_html(rendered)
        assert '<div class="code-label" title="a &gt; b">a &gt; b</div>' in result


class TestFenceScanner:
    """Fences are found by CommonMark's rules, the same way the renderer finds them."""

    def test_fence_indented_up_to_three_spaces_gets_its_directives(self) -> None:
        result = render_fence("  ```bash\n  [label a.sh]\n  echo\n  ```\n")
        assert '<div class="code-label" title="a.sh">a.sh</div>' in result
        assert "[label" not in result

    def test_fence_in_a_list_item_renders_valid_html(self) -> None:
        result = render_fence("- item\n\n    ```bash\n    [label a.sh]\n    echo\n    ```\n")
        assert '<div class="code-label" title="a.sh">a.sh</div>' in result
        assert "[label" not in result
        assert "<p><div" not in result

    def test_four_space_indented_code_is_not_a_fence(self) -> None:
        source = "Text.\n\n    ```\n    [label a.sh]\n    ```\n"
        assert expand_source(source) == source

    def test_nested_shorter_fence_is_content(self) -> None:
        source = "````\n[label outer.md]\n```\n[label inner]\n```\n````\n"
        result = expand_source(source)
        assert '"label": "outer.md"' in result
        assert "[label inner]" in result

    def test_closing_fence_must_match_character_and_length(self) -> None:
        source = "~~~~\n[label a.sh]\n~~~\n```\n~~~~\n"
        result = expand_source(source)
        assert result.endswith("~~~~\n~~~\n```\n~~~~\n")
        assert '"label": "a.sh"' in result

    def test_backtick_fence_info_with_a_backtick_is_not_a_fence(self) -> None:
        source = "``` a`b\n[label a.sh]\n```\n"
        assert expand_source(source) == source

    def test_indented_code_at_document_start_is_not_a_fence(self) -> None:
        source = "    ```\n    [label a.sh]\n    ```\n"
        assert expand_source(source) == source

    def test_tab_indented_in_list_fence_gets_its_directives(self) -> None:
        result = expand_source("- item\n\n\t```\n\t[label a.sh]\n\techo\n\t```")
        assert "[label a.sh]" not in result
        assert '    <!-- mw-fence:{"version": 1, "label": "a.sh"} -->\n\n' in result
        assert result.endswith("\t```\n\techo\n\t```")

    def test_fence_holding_only_directives(self) -> None:
        result = expand_source("```\n[label a.sh]\n```\n")
        assert result == '<!-- mw-fence:{"version": 1, "label": "a.sh"} -->\n```\n```\n'


class TestFenceInBlockQuote:
    """A fence behind a block quote marker, as in a ``> [!NOTE]`` alert, gets its directives and prefix flags."""

    ALERT = "> [!NOTE]\n> Run this:\n> ```command\n> [label restart.sh]\n> systemctl restart nginx\n> ```\n"

    def test_marker_is_its_own_quoted_block_before_the_fence(self) -> None:
        assert expand_source(self.ALERT) == (
            "> [!NOTE]\n> Run this:\n>\n"
            '> <!-- mw-fence:{"version": 1, "prefix_type": "command", "prefix_value": "$", "label": "restart.sh"} -->\n'
            ">\n> ```bash\n> systemctl restart nginx\n> ```\n"
        )

    def test_in_process_render_applies_the_label_and_prefix_inside_the_quote(self) -> None:
        result = render_fence(self.ALERT)
        quote_end = result.index("</blockquote>")
        assert result.index('<div class="code-label" title="restart.sh">restart.sh</div>') < quote_end
        assert result.index('<li data-prefix="$">systemctl') < quote_end
        assert "[label" not in result
        assert "mw-fence" not in result
        assert "<p><div" not in result

    def test_fence_without_directives_is_unchanged(self) -> None:
        source = "> ```bash\n> echo hi\n> ```\n"
        assert expand_source(source) == source

    def test_quoted_looking_code_line_in_a_plain_fence_is_not_a_directive(self) -> None:
        source = "```\n> [label a.sh]\n```\n"
        assert expand_source(source) == source

    def test_environment_behind_a_quote_marker_is_listed(self) -> None:
        assert environment_names("> ```\n> [environment local]\n> ```\n", skip_mermaid=True) == ["local"]


class TestEnvironmentNames:
    """Tests the public scan that lists the environment names a document's fence directives name."""

    def test_lists_names_in_document_order_with_repeats(self) -> None:
        source = "```\n[environment a]\nx\n```\n\n```\n[environment b]\n[environment a]\ny\n```\n"
        assert environment_names(source, skip_mermaid=False) == ["a", "b", "a"]

    def test_a_directive_after_the_first_code_line_is_not_listed(self) -> None:
        assert environment_names("```\n[label x]\ncode\n[environment late]\n```\n", skip_mermaid=False) == []

    def test_mermaid_fences_are_skipped_on_request(self) -> None:
        source = "```mermaid\n[environment a]\ngraph TD\n```\n"
        assert environment_names(source, skip_mermaid=True) == []
        assert environment_names(source, skip_mermaid=False) == ["a"]


class TestDiagnostics:
    def test_a_malformed_marker_is_a_malformed_marker_report_with_no_line(self) -> None:
        diagnostics: list[Diagnostic] = []
        apply_html("<!-- mw-fence:{not json -->\n<pre><code>x\n</code></pre>", diagnostics)
        assert [(item.extension, item.reason, item.line, item.directive) for item in diagnostics] == [
            ("fence", "malformed-marker", None, None)
        ]

    def test_a_marker_with_no_code_block_is_a_no_target_report(self) -> None:
        diagnostics: list[Diagnostic] = []
        apply_html('<!-- mw-fence:{"version": 1, "label": "x"} -->\n<p>no code</p>', diagnostics)
        assert [(item.extension, item.reason) for item in diagnostics] == [("fence", "no-target")]

    def test_an_in_process_render_reports_a_marker_with_no_code_block(self) -> None:
        md = markdown.Markdown(extensions=["markwright.fence"])
        with pytest.warns(RenderWarning):
            md.convert('<!-- mw-fence:{"version": 1, "label": "x"} -->\n\ntext')
        assert [item.reason for item in md.markwright_diagnostics] == ["no-target"]  # type: ignore[attr-defined]


class TestDisallowedEnvironmentReport:
    """An unlisted [environment NAME] is reported in both paths."""

    ALLOWED = {"allowed_environments": ["local"]}
    SOURCE = "```\n[environment prod]\nssh root@server\n```"

    def test_the_marker_carries_the_name_and_the_directive_line(self) -> None:
        result = expand_source(self.SOURCE, self.ALLOWED)
        assert '"disallowed_environment": "prod"' in result
        assert '"line": 2' in result
        assert "[environment prod]" in result.split("-->", 1)[1]

    def test_the_marker_sits_beside_a_label(self) -> None:
        result = expand_source("```\n[label a.sh]\n[environment prod]\ncode\n```", self.ALLOWED)
        assert '"label": "a.sh"' in result
        assert '"disallowed_environment": "prod"' in result
        assert '"line": 3' in result

    def test_a_fence_with_only_the_disallowed_line_gets_a_marker_with_only_that_field(self) -> None:
        result = expand_source(self.SOURCE, self.ALLOWED)
        marker = result.split("\n", 1)[0]
        assert marker.startswith('<!-- mw-fence:{"version": 1')
        assert '"label"' not in marker
        assert '"environment"' not in marker

    def test_an_allowed_environment_is_not_reported(self) -> None:
        result = expand_source("```\n[environment local]\ncode\n```", self.ALLOWED)
        assert "disallowed_environment" not in result

    def test_omitting_the_allowlist_reports_nothing(self) -> None:
        assert "disallowed_environment" not in expand_source(self.SOURCE)

    def test_the_post_stage_reports_a_diagnostic_and_changes_no_html(self) -> None:
        rendered = _stub_render(expand_source(self.SOURCE, self.ALLOWED))
        diagnostics: list[Diagnostic] = []
        result = apply_html(rendered, diagnostics)
        assert diagnostics == [
            Diagnostic(
                extension="fence",
                line=2,
                directive="[environment prod]",
                reason="disallowed-environment",
                message=diagnostics[0].message,
            )
        ]
        assert "prod" in diagnostics[0].message
        assert "2" in diagnostics[0].message
        without_field = rendered.replace(', "disallowed_environment": "prod"', "").replace(', "line": 2', "")
        assert apply_html(without_field) == result

    def test_an_in_process_render_reports_the_same_diagnostic(self) -> None:
        md = markdown.Markdown(
            extensions=["pymdownx.superfences", "markwright.fence"],
            extension_configs={"markwright.fence": self.ALLOWED},
        )
        with pytest.warns(RenderWarning):
            md.convert(self.SOURCE)
        pipeline: list[Diagnostic] = []
        apply_html(_stub_render(expand_source(self.SOURCE, self.ALLOWED)), pipeline)
        assert md.markwright_diagnostics == pipeline  # type: ignore[attr-defined]

    def test_an_in_process_render_reports_the_source_line_under_a_directive_line_above(self) -> None:
        source = "Intro\n\n```\n[environment prod]\ncode\n```"
        md = markdown.Markdown(
            extensions=["pymdownx.superfences", "markwright.fence"],
            extension_configs={"markwright.fence": self.ALLOWED},
        )
        with pytest.warns(RenderWarning):
            md.convert(source)
        assert [item.line for item in md.markwright_diagnostics] == [4]  # type: ignore[attr-defined]


class TestDisallowedEnvironmentIsAMarkedFence:
    """A fence marked only for a disallowed environment has the block structure of any marked fence."""

    @staticmethod
    def render_under_paragraph(environment: str) -> str:
        md = markdown.Markdown(
            extensions=["pymdownx.superfences", "markwright.fence"],
            extension_configs={"markwright.fence": {"allowed_environments": ["local"]}},
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RenderWarning)
            return md.convert(f"Run this:\n```bash\n[environment {environment}]\nssh root@x\n```")

    def test_the_fence_leaves_the_paragraph_as_it_does_with_an_allowed_environment(self) -> None:
        allowed = self.render_under_paragraph("local")
        disallowed = self.render_under_paragraph("prod")
        assert allowed.startswith("<p>Run this:</p>")
        assert disallowed.startswith("<p>Run this:</p>")

    def test_the_disallowed_line_stays_in_the_code(self) -> None:
        rendered = self.render_under_paragraph("prod")
        assert "environment" in rendered
        assert "prod" in rendered
        assert "environment-prod" not in rendered


class TestCommentedOutFence:
    """A fence with directives inside a multi-line HTML comment stays the author's text."""

    SOURCE = "<!--\n```command\n[label deploy.sh]\nmake\n```\n-->\n\nafter\n"

    def test_expand_source_leaves_the_comment_unchanged(self) -> None:
        assert expand_source(self.SOURCE) == self.SOURCE

    def test_in_process_render_keeps_the_comment_whole(self) -> None:
        rendered = render_fence(self.SOURCE)

        # superfences still highlights the fence inside the comment; markwright applies nothing to it
        assert rendered.startswith("<!--\n")
        assert "[label deploy.sh]" in rendered
        assert "code-label" not in rendered
        assert "mw-fence" not in rendered
        assert "<p>after</p>" in rendered


class TestMarkedFenceIsItsOwnBlock:
    """A fence that gains a marker gets a blank line before it, so it never joins the paragraph above."""

    TIGHT_LIST = "- Run this:\n    ```command\n    ls\n    ```\n- next\n"
    MARKER = '<!-- mw-fence:{"version": 1, "prefix_type": "command", "prefix_value": "$"} -->'

    def test_the_marker_gets_a_blank_line_before_it_under_a_tight_list_item(self) -> None:
        assert expand_source(self.TIGHT_LIST) == (
            f"- Run this:\n\n    {self.MARKER}\n\n    ```bash\n    ls\n    ```\n\n- next\n"
        )

    def test_a_marker_at_column_zero_gets_a_blank_line_after_a_text_line(self) -> None:
        assert expand_source("Intro\n```command\nls\n```\n") == f"Intro\n\n{self.MARKER}\n```bash\nls\n```\n"

    def test_a_fence_after_a_blank_line_gets_no_extra_blank_line(self) -> None:
        assert expand_source("Intro\n\n```command\nls\n```\n") == f"Intro\n\n{self.MARKER}\n```bash\nls\n```\n"

    def test_a_fence_at_the_start_of_the_document_gets_no_leading_blank_line(self) -> None:
        assert expand_source("```command\nls\n```\n").startswith("<!--")

    def test_an_unmarked_fence_under_a_list_item_is_unchanged(self) -> None:
        source = "- Run this:\n    ```bash\n    ls\n    ```\n- next\n"

        assert expand_source(source) == source

    def test_a_quoted_fence_is_unchanged(self) -> None:
        source = "> Run this:\n> ```command\n> ls\n> ```\n"

        assert expand_source(source) == (f"> Run this:\n>\n> {self.MARKER}\n>\n> ```bash\n> ls\n> ```\n")

    def test_in_process_the_fence_stays_in_the_first_item_and_the_second_item_survives(self) -> None:
        result = render_fence(self.TIGHT_LIST)

        assert result.count("<li>") == 2
        assert "<p>Run this:</p>" in result
        assert result.index('data-prefix="$"') < result.index("next")
        assert "<li>\n<p>next</p>\n</li>" in result
        assert "mw-fence" not in result

    def test_item_text_after_the_fence_ends_in_a_blank_line_before_the_next_item(self) -> None:
        result = expand_source("- Run this:\n    ```command\n    ls\n    ```\n    After.\n- next\n")

        assert result.endswith("    ```\n\n    After.\n\n- next\n")

    def test_item_text_after_the_fence_that_ends_in_a_blank_line_is_unchanged(self) -> None:
        result = expand_source("- Run this:\n    ```command\n    ls\n    ```\n    After.\n\n- next\n")

        assert result.endswith("    ```\n\n    After.\n\n- next\n")

    def test_item_text_that_holds_a_second_fence_ends_in_a_blank_line_after_that_fence(self) -> None:
        source = "- Run this:\n    ```command\n    ls\n    ```\n    Then:\n    ```bash\n    pwd\n    ```\n- next\n"

        assert expand_source(source).endswith("    Then:\n    ```bash\n    pwd\n    ```\n\n- next\n")

    def test_in_process_the_item_after_text_that_follows_the_fence_stays_an_item(self) -> None:
        result = render_fence("- Run this:\n    ```command\n    ls\n    ```\n    After.\n- next\n")

        assert result.count("<li>") == 2
        assert "<p>After.</p>" in result
        assert "<li>\n<p>next</p>\n</li>" in result

    def test_in_process_a_list_with_an_unmarked_fence_stays_tight(self) -> None:
        result = render_fence("- Run this:\n    ```bash\n    ls\n    ```\n- next\n")

        assert "<li>Run this:" in result


class TestPrefixFlagBesideHighlighterAttributes:
    """A flag in the info string keeps working beside a highlighter attribute such as ``hl_lines``."""

    @pytest.mark.parametrize(
        ("info", "prefix_type", "fence_line"),
        [
            ('command hl_lines="1"', "command", '```bash hl_lines="1"'),
            ('command title="x.sh"', "command", '```bash title="x.sh"'),
            ("command {hl_lines=[1]}", "command", "```bash {hl_lines=[1]}"),
            ("command{hl_lines=[1]}", "command", "```bash{hl_lines=[1]}"),
            ('command,python hl_lines="1 2"', "command", '```python hl_lines="1 2"'),
            ('line_numbers,python linenums="1"', "line_numbers", '```python linenums="1"'),
            ('command title="a,b"', "command", '```bash title="a,b"'),
            ('super_user   title="x"', "super_user", '```bash title="x"'),
        ],
    )
    def test_the_flag_is_read_and_the_attribute_passes_through(
        self, info: str, prefix_type: str, fence_line: str
    ) -> None:
        result = expand_source(f"```{info}\nls\n```\n")

        assert f'"prefix_type": "{prefix_type}"' in result
        assert fence_line in result.split("\n")

    @pytest.mark.parametrize("info", ['python hl_lines="1,2"', 'python title="a,b"', "python", "bash {hl_lines=[1]}"])
    def test_an_info_string_with_no_flag_is_unchanged_byte_for_byte(self, info: str) -> None:
        source = f"```{info}\nls\n```\n"

        assert expand_source(source) == source

    def test_an_attribute_with_no_language_gets_a_plain_text_language(self) -> None:
        assert '```text hl_lines="1"' in expand_source('```line_numbers hl_lines="1"\nls\n```\n')
        assert "```text{hl_lines=[1]}" in expand_source("```line_numbers{hl_lines=[1]}\nls\n```\n")

    def test_a_flag_with_no_attribute_and_no_language_stays_empty(self) -> None:
        assert expand_source("```line_numbers\nls\n```\n").split("\n")[1] == "```"

    def test_in_process_command_with_hl_lines_renders_the_prefix_and_the_highlighted_line(self) -> None:
        result = render_fence('```command hl_lines="1"\nls\n```\n')

        assert 'data-prefix="$"' in result
        assert 'class="hll"' in result

    def test_in_process_command_with_a_title_renders_the_filename_and_the_prefix(self) -> None:
        result = render_fence('```command title="x.sh"\nls\n```\n')

        assert 'data-prefix="$"' in result
        assert "x.sh" in result


class TestMarkedFenceUnderAShallowListItem:
    """A marked fence indented one to three columns stays in its item, where a blank line would end it."""

    @pytest.mark.parametrize(
        "source",
        [
            "- Run this:\n  ```command\n  ls\n  ```\n- next\n",
            "1. Run this:\n   ```command\n   ls\n   ```\n2. next\n",
            "- Run this:\n    ```command\n    ls\n    ```\n- next\n",
        ],
        ids=["bullet-2", "ordered-3", "bullet-4"],
    )
    def test_in_process_the_list_stays_one_list_with_the_fence_in_the_first_item(self, source: str) -> None:
        result = render_fence(source)

        assert result.count("<ul>") + result.count("<ol>") == 2
        assert result.count("</ul>") + result.count("</ol>") == 2
        assert result.index('data-prefix="$"') < result.index("next")
        assert result.index("<li>") < result.index('data-prefix="$"') < result.rindex("<li>")

    def test_a_two_column_marker_goes_at_four_columns_with_no_blank_line_around_it(self) -> None:
        result = expand_source("- Run this:\n  ```command\n  ls\n  ```\n- next\n")

        assert "\n\n" not in result
        assert result.split("\n")[1].startswith("    <!-- mw-fence:")
        assert result.split("\n")[2] == "  ```bash"


class TestInProcessFlagWithAttributeAndNoLanguage:
    def test_the_highlighted_line_and_the_prefixes_survive(self) -> None:
        result = render_fence('```line_numbers hl_lines="1"\nalpha\nbeta\n```\n')

        assert 'class="hll"' in result
        assert 'data-prefix="1"' in result
        assert 'data-prefix="2"' in result


class TestPrefixAroundSpansThatWrapAWholeLine:
    """A span a highlighter wraps around a whole line closes inside that line's <li>, with no empty line after."""

    COMMAND_MARKER = '<!-- mw-fence:{"version": 1, "prefix_type": "command", "prefix_value": "$"} -->\n'
    HL_LINES_SOURCE = '```command hl_lines="1"\nls\ncd x\n```\n'

    @staticmethod
    def render_with_highlight_config(source: str, highlight_config: dict[str, object]) -> str:
        instance = markdown.Markdown(
            extensions=["pymdownx.superfences", "pymdownx.highlight", "markwright.fence"],
            extension_configs={"pymdownx.highlight": highlight_config},
        )
        return instance.convert(source)

    def test_in_process_hl_lines_closes_the_span_inside_the_first_item(self) -> None:
        result = self.render_with_highlight_config(self.HL_LINES_SOURCE, {})

        assert (
            '<ol><li data-prefix="$"><span class="hll">ls\n</span></li>'
            '<li data-prefix="$"><span class="nb">cd</span><span class="w"> </span>x\n</li></ol>\n'
        ) in result

    def test_in_process_line_spans_close_both_spans_inside_each_item(self) -> None:
        result = self.render_with_highlight_config(self.HL_LINES_SOURCE, {"line_spans": "__span"})

        assert (
            '<ol><li data-prefix="$"><span id="__span-0-1"><span class="hll">ls\n</span></span></li>'
            '<li data-prefix="$"><span id="__span-0-2"><span class="nb">cd</span><span class="w"> </span>x\n'
            "</span></li></ol>\n"
        ) in result

    def test_registry_round_trip_gives_the_same_wrap(self) -> None:
        pre_output = run_pre(self.HL_LINES_SOURCE, ["fence"])
        rendered = _stub_render(pre_output)

        result = run_post(rendered, ["fence"])

        assert (
            '<ol><li data-prefix="$"><span class="hll">ls\n</span></li>'
            '<li data-prefix="$"><span class="nb">cd</span><span class="w"> </span>x\n</li></ol>\n'
        ) in result

    def test_pygments_hl_lines_fixture_has_no_trailing_empty_item(self) -> None:
        html_input = (
            self.COMMAND_MARKER + '<div class="highlight"><pre><span></span><code>'
            '<span class="hll">ls\n</span><span class="hll">cd x\n</span>pwd\n</code></pre></div>'
        )

        result = apply_html(html_input)

        assert (
            '<ol><li data-prefix="$"><span class="hll">ls\n</span></li>'
            '<li data-prefix="$"><span class="hll">cd x\n</span></li>'
            '<li data-prefix="$">pwd\n</li></ol>\n'
        ) in result

    def test_chroma_inline_style_fixture_gives_one_item_per_line(self) -> None:
        # Line markup captured from a Hugo build (noClasses = true, hl_lines=[1]); the <pre> style is shortened
        html_input = (
            self.COMMAND_MARKER + '<div class="highlight"><pre tabindex="0" style="color:#f8f8f2;">'
            '<code class="language-bash" data-lang="bash">'
            '<span style="display:flex; background-color:#3c3d38"><span>ls\n</span></span>'
            '<span style="display:flex;"><span>cd x\n</span></span></code></pre></div>'
        )

        result = apply_html(html_input)

        assert (
            '<ol><li data-prefix="$"><span style="display:flex; background-color:#3c3d38"><span>ls\n</span></span></li>'
            '<li data-prefix="$"><span style="display:flex;"><span>cd x\n</span></span></li></ol>\n'
        ) in result
        assert result.count("<li data-prefix=") == 2
