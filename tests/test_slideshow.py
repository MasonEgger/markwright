# ABOUTME: Tests for the slideshow embed extension.
# Validates image slide generation, dimensions, navigation, and edge cases.

from __future__ import annotations

import markdown

from markwright.slideshow import expand_source


def render_slideshow(source: str) -> str:
    """Render Markdown source with the slideshow extension loaded.

    :param source: Markdown source text.
    :returns: Rendered HTML string.
    """
    md = markdown.Markdown(extensions=["markwright.slideshow"])
    return md.convert(source)


class TestSlideshowBasic:
    """Tests for basic slideshow rendering."""

    def test_basic_three_images(self) -> None:
        result = render_slideshow("[slideshow https://img1.png https://img2.png https://img3.png]")
        assert '<div class="slideshow"' in result
        assert 'alt="Slide #1"' in result
        assert 'alt="Slide #2"' in result
        assert 'alt="Slide #3"' in result
        assert 'src="https://img1.png"' in result
        assert 'src="https://img2.png"' in result
        assert 'src="https://img3.png"' in result

    def test_default_dimensions(self) -> None:
        result = render_slideshow("[slideshow https://a.png https://b.png]")
        assert "height: 270px" in result
        assert "width: 480px" in result

    def test_navigation_arrows(self) -> None:
        result = render_slideshow("[slideshow https://a.png https://b.png]")
        assert '<div class="action left"' in result
        assert '<div class="action right"' in result
        assert "&#8249;" in result
        assert "&#8250;" in result

    def test_slides_container(self) -> None:
        result = render_slideshow("[slideshow https://a.png https://b.png]")
        assert '<div class="slides">' in result


class TestSlideshowDimensions:
    """Tests for custom dimensions."""

    def test_custom_dimensions(self) -> None:
        result = render_slideshow("[slideshow https://a.png https://b.png 225 400]")
        assert "height: 225px" in result
        assert "width: 400px" in result

    def test_scroll_amount_matches_width(self) -> None:
        result = render_slideshow("[slideshow https://a.png https://b.png 225 400]")
        assert "scrollBy(400" in result or "scrollBy(-400" in result

    def test_default_scroll_amount(self) -> None:
        result = render_slideshow("[slideshow https://a.png https://b.png]")
        assert "scrollBy(480" in result or "scrollBy(-480" in result


class TestSlideshowMinImages:
    """Tests for minimum image requirements."""

    def test_two_images_minimum(self) -> None:
        result = render_slideshow("[slideshow https://a.png https://b.png]")
        assert '<div class="slideshow"' in result
        assert 'alt="Slide #1"' in result
        assert 'alt="Slide #2"' in result

    def test_single_image_not_matched(self) -> None:
        result = render_slideshow("[slideshow https://a.png]")
        assert '<div class="slideshow"' not in result


class TestSlideshowEdgeCases:
    """Tests for edge cases."""

    def test_urls_html_escaped(self) -> None:
        result = render_slideshow("[slideshow https://a.png?q=1&b=2 https://c.png]")
        assert "https://a.png?q=1&amp;b=2" in result

    def test_not_matched_inside_paragraph(self) -> None:
        result = render_slideshow("Some text [slideshow https://a.png https://b.png] more")
        assert '<div class="slideshow"' not in result

    def test_not_matched_inside_fence(self) -> None:
        md = markdown.Markdown(extensions=["pymdownx.superfences", "pymdownx.highlight", "markwright.slideshow"])
        result = md.convert("```\n[slideshow https://a.png https://b.png]\n```")
        assert '<div class="slideshow"' not in result

    def test_not_wrapped_in_paragraph(self) -> None:
        result = render_slideshow("[slideshow https://a.png https://b.png]")
        assert "<p><div" not in result


class TestSlideshowExpandSource:
    """Tests for the pure expand_source stage function."""

    def test_expands_standalone_embed(self) -> None:
        result = expand_source("[slideshow https://a.jpg https://b.jpg]")
        assert '<div class="slideshow"' in result

    def test_no_stash_placeholder(self) -> None:
        result = expand_source("[slideshow https://a.jpg https://b.jpg]")
        assert "\x02" not in result

    def test_inline_embed_unchanged(self) -> None:
        source = "text [slideshow https://a.jpg https://b.jpg] text"
        assert expand_source(source) == source

    def test_single_url_not_expanded(self) -> None:
        source = "[slideshow https://a.jpg]"
        assert expand_source(source) == source

    def test_multiline_only_standalone_expanded(self) -> None:
        source = "before line\n[slideshow https://a.jpg https://b.jpg]\nafter line"
        result = expand_source(source)
        lines = result.split("\n")
        assert lines[0] == "before line"
        assert lines[-1] == "after line"
        assert '<div class="slideshow"' in result

    def test_no_embed_passes_through(self) -> None:
        source = "just some text\nmore text"
        assert expand_source(source) == source
