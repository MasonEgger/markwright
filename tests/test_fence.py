# ABOUTME: Tests for the fence extension handling label, secondary_label, environment, and prefix directives.
# Verifies directive extraction, HTML injection, environment classes, line prefixes, and edge cases.

import markdown

from markwright.fence import apply_html, expand_source


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

    def test_empty_allowed_list_allows_all(self) -> None:
        source = "```\n[environment custom]\ncode\n```"
        result = render_fence(source, allowed_environments=[])
        assert "environment-custom" in result


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

    def test_malformed_json_warns_and_skips(self) -> None:
        html_input = "<!-- mw-fence:{not json -->\n<pre><code>x\n</code></pre>"
        warnings: list[str] = []
        result = apply_html(html_input, warnings)
        assert len(warnings) == 1
        assert "code-label" not in result
        assert "<!-- mw-fence:" not in result

    def test_unsupported_version_warns_and_skips(self) -> None:
        html_input = '<!-- mw-fence:{"version": 999, "label": "x"} -->\n<pre><code>x\n</code></pre>'
        warnings: list[str] = []
        result = apply_html(html_input, warnings)
        assert len(warnings) == 1
        assert "code-label" not in result

    def test_no_following_code_block_warns(self) -> None:
        html_input = '<!-- mw-fence:{"version": 1, "label": "x"} -->\n<p>no code here</p>'
        warnings: list[str] = []
        result = apply_html(html_input, warnings)
        assert len(warnings) == 1
        assert "code-label" not in result

    def test_warnings_none_is_silent_no_op(self) -> None:
        malformed = "<!-- mw-fence:{not json -->\n<pre><code>x\n</code></pre>"
        bad_version = '<!-- mw-fence:{"version": 999, "label": "x"} -->\n<pre><code>x\n</code></pre>'
        no_block = '<!-- mw-fence:{"version": 1, "label": "x"} -->\n<p>no code here</p>'
        for html_input in (malformed, bad_version, no_block):
            result = apply_html(html_input)
            assert "code-label" not in result


class TestFenceBranchCoverage:
    """Exercise the remaining fence branches: an unclosed fence, and markers whose
    adjacent HTML is missing a <pre>, a <code>, a closing </code>, or a trailing
    newline. Each must degrade without raising."""

    def test_unclosed_fence_with_directive_still_emits_marker(self) -> None:
        # No closing fence: the scan loop reaches end-of-input instead of breaking.
        source = "```command\n[label deploy.sh]\nssh root@server"
        result = expand_source(source)
        assert "<!-- mw-fence:" in result
        assert '"label": "deploy.sh"' in result
        assert "ssh root@server" in result

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
