# ABOUTME: Tests for the lightbox directive extension.
# Validates the pre-stage expansion, escaping, literal fall-through, and the in-process render.

from __future__ import annotations

import markdown

from markwright.lightbox import expand_source


def render_lightbox(source: str) -> str:
    """Render Markdown source with the lightbox extension loaded.

    :param source: Markdown source text.
    :returns: Rendered HTML string.
    """
    md = markdown.Markdown(extensions=["markwright.lightbox"])
    return md.convert(source)


class TestLightboxExpandSource:
    """Tests for the pre-stage expansion."""

    def test_url_and_alt(self) -> None:
        result = expand_source("[lightbox https://example.com/a.png A diagram]")
        assert result == (
            '<a class="mw-lightbox" href="https://example.com/a.png">'
            '<img src="https://example.com/a.png" alt="A diagram" /></a>'
        )

    def test_url_only_has_empty_alt(self) -> None:
        result = expand_source("[lightbox /a.png]")
        assert result == '<a class="mw-lightbox" href="/a.png"><img src="/a.png" alt="" /></a>'

    def test_url_and_alt_are_escaped(self) -> None:
        result = expand_source('[lightbox /a.png?x=1&y=2 Tom & Jerry "q"]')
        assert 'href="/a.png?x=1&amp;y=2"' in result
        assert 'src="/a.png?x=1&amp;y=2"' in result
        assert 'alt="Tom &amp; Jerry &quot;q&quot;"' in result

    def test_inline_mention_is_unchanged(self) -> None:
        source = "Use [lightbox /a.png Alt] here."
        assert expand_source(source) == source

    def test_directive_inside_fence_is_unchanged(self) -> None:
        source = "```\n[lightbox /a.png Alt]\n```"
        assert expand_source(source) == source


class TestLightboxInProcess:
    """Tests for the in-process Python-Markdown render."""

    def test_lone_lightbox_is_wrapped_in_a_paragraph(self) -> None:
        result = render_lightbox("[lightbox /a.png A diagram]")
        assert result == '<p><a class="mw-lightbox" href="/a.png"><img src="/a.png" alt="A diagram" /></a></p>'
