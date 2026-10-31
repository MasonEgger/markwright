# ABOUTME: Tests for the button directive extension.
# Validates the pre-stage expansion, escaping, literal fall-through, and the in-process render.

from __future__ import annotations

import markdown

from markwright.button import expand_source


def render_button(source: str) -> str:
    """Render Markdown source with the button extension loaded.

    :param source: Markdown source text.
    :returns: Rendered HTML string.
    """
    md = markdown.Markdown(extensions=["markwright.button"])
    return md.convert(source)


class TestButtonExpandSource:
    """Tests for the pre-stage expansion."""

    def test_basic_button(self) -> None:
        result = expand_source("[button https://example.com/start Get started]")
        assert result == '<a class="mw-button" href="https://example.com/start">Get started</a>'

    def test_primary_button(self) -> None:
        result = expand_source("[button primary /start Get started]")
        assert result == '<a class="mw-button mw-button-primary" href="/start">Get started</a>'

    def test_url_and_text_are_escaped(self) -> None:
        result = expand_source("[button /a?b=1&c=2 Tom & Jerry <3]")
        assert 'href="/a?b=1&amp;c=2"' in result
        assert ">Tom &amp; Jerry &lt;3</a>" in result

    def test_missing_text_stays_literal(self) -> None:
        assert expand_source("[button /docs]") == "[button /docs]"

    def test_inline_mention_is_unchanged(self) -> None:
        source = "Use [button /docs Docs] here."
        assert expand_source(source) == source

    def test_directive_inside_fence_is_unchanged(self) -> None:
        source = "```\n[button /start Go]\n```"
        assert expand_source(source) == source


class TestButtonInProcess:
    """Tests for the in-process Python-Markdown render."""

    def test_lone_button_is_wrapped_in_a_paragraph(self) -> None:
        result = render_button("[button /start Get started]")
        assert result == '<p><a class="mw-button" href="/start">Get started</a></p>'

    def test_consecutive_buttons_share_a_paragraph(self) -> None:
        result = render_button("[button /one One]\n[button primary /two Two]")
        assert result.count("<p>") == 1
        assert result.count('class="mw-button') == 2

    def test_inline_markdown_in_text_renders(self) -> None:
        result = render_button("[button /docs Read *the* docs]")
        assert ">Read <em>the</em> docs</a>" in result
