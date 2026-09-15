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
        assert "scrollLeft -= 400" in result
        assert "scrollLeft += 400" in result

    def test_default_scroll_amount(self) -> None:
        result = render_slideshow("[slideshow https://a.png https://b.png]")
        assert "scrollLeft -= 480" in result
        assert "scrollLeft += 480" in result


class TestSlideshowNavUpstreamParity:
    """Tests matching the upstream slideshow nav JavaScript (slideshow.js:112-113) exactly."""

    def test_nav_uses_upstream_scroll_left_iife(self) -> None:
        result = render_slideshow("[slideshow https://a.png https://b.png]")
        assert "getElementsByClassName" in result
        assert "scrollLeft" in result
        assert "scrollBy" not in result

    def test_left_button_onclick_matches_upstream(self) -> None:
        result = render_slideshow("[slideshow https://a.png https://b.png]")
        assert "onclick=\"(() => this.parentNode.getElementsByClassName('slides')[0].scrollLeft -= 480)()\"" in result

    def test_right_button_onclick_matches_upstream(self) -> None:
        result = render_slideshow("[slideshow https://a.png https://b.png]")
        assert "onclick=\"(() => this.parentNode.getElementsByClassName('slides')[0].scrollLeft += 480)()\"" in result


class TestSlideshowMinImages:
    """Tests for minimum image requirements."""

    def test_two_images_minimum(self) -> None:
        result = render_slideshow("[slideshow https://a.png https://b.png]")
        assert '<div class="slideshow"' in result
        assert 'alt="Slide #1"' in result
        assert 'alt="Slide #2"' in result

    def test_single_image_matched(self) -> None:
        # Corrected per D1 (spec.md Decisions, 2026-09-14): upstream slideshow.js:82
        # rejects only zero images, so a single image is accepted for code parity.
        result = render_slideshow("[slideshow https://a.png]")
        assert '<div class="slideshow"' in result
        assert 'alt="Slide #1"' in result


class TestSingleImageSlideshow:
    """Tests for single-image slideshow parity (D1, spec.md Decisions, 2026-09-14)."""

    def test_single_image_produces_one_slide(self) -> None:
        result = expand_source("[slideshow https://a.jpg]")
        assert '<div class="slideshow"' in result
        assert 'alt="Slide #1"' in result
        assert 'alt="Slide #2"' not in result

    def test_two_image_case_unchanged(self) -> None:
        result = expand_source("[slideshow https://a.jpg https://b.jpg]")
        assert '<div class="slideshow"' in result
        assert 'alt="Slide #1"' in result
        assert 'alt="Slide #2"' in result

    def test_zero_urls_still_rejected(self) -> None:
        source = "[slideshow 225 400]"
        assert expand_source(source) == source


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

    def test_single_url_expanded(self) -> None:
        # Corrected per D1 (spec.md Decisions, 2026-09-14): a single-image slideshow
        # is now accepted for upstream code parity.
        result = expand_source("[slideshow https://a.jpg]")
        assert '<div class="slideshow"' in result

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
