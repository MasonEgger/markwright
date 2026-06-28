# ABOUTME: Tests for the fence extension handling label, secondary_label, environment, and prefix directives.
# Verifies directive extraction, HTML injection, environment classes, line prefixes, and edge cases.

import markdown


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
