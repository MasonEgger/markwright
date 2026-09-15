# ABOUTME: Tests for the image compare embed extension.
# Validates side-by-side image comparison with slider, dimensions, and edge cases.

from __future__ import annotations

import markdown

from markwright.image_compare import expand_source


def render_compare(source: str) -> str:
    """Render Markdown source with the image_compare extension loaded.

    :param source: Markdown source text.
    :returns: Rendered HTML string.
    """
    md = markdown.Markdown(extensions=["markwright.image_compare"])
    return md.convert(source)


class TestImageCompareBasic:
    """Tests for basic image compare rendering."""

    def test_basic_compare(self) -> None:
        result = render_compare("[compare https://left.png https://right.png]")
        assert '<div class="image-compare"' in result
        assert 'class="image-left"' in result
        assert 'class="image-right"' in result
        assert 'src="https://left.png"' in result
        assert 'src="https://right.png"' in result

    def test_default_dimensions(self) -> None:
        result = render_compare("[compare https://left.png https://right.png]")
        assert "height: 270px" in result
        assert "width: 480px" in result

    def test_value_css_variable(self) -> None:
        result = render_compare("[compare https://left.png https://right.png]")
        assert "--value:50%" in result

    def test_range_input(self) -> None:
        result = render_compare("[compare https://left.png https://right.png]")
        assert '<input type="range"' in result
        assert 'class="control"' in result
        assert 'min="0"' in result
        assert 'max="100"' in result
        assert 'value="50"' in result

    def test_svg_control_arrow(self) -> None:
        result = render_compare("[compare https://left.png https://right.png]")
        assert '<svg class="control-arrow"' in result

    def test_oninput_handler(self) -> None:
        result = render_compare("[compare https://left.png https://right.png]")
        assert "oninput=" in result
        assert "--value" in result

    def test_oninput_backticks_survive_markdown(self) -> None:
        # The oninput handler uses a JS template literal with backticks. Markdown
        # must not parse those backticks as an inline code span, which would break
        # the handler and stop the slider from clipping the image.
        result = render_compare("[compare https://left.png https://right.png]")
        assert "<code>" not in result
        assert "`${this.value}%`" in result

    def test_not_wrapped_in_paragraph(self) -> None:
        # The block-level widget must not be wrapped in an invalid <p>.
        result = render_compare("[compare https://left.png https://right.png]")
        assert "<p><div" not in result


class TestImageCompareDimensions:
    """Tests for custom dimensions."""

    def test_custom_dimensions(self) -> None:
        result = render_compare("[compare https://a.png https://b.png 500 600]")
        assert "height: 500px" in result
        assert "width: 600px" in result


class TestImageCompareEdgeCases:
    """Tests for edge cases."""

    def test_urls_html_escaped(self) -> None:
        result = render_compare("[compare https://a.png?q=1&b=2 https://b.png]")
        assert "https://a.png?q=1&amp;b=2" in result

    def test_not_matched_inside_paragraph(self) -> None:
        result = render_compare("Some text [compare https://a.png https://b.png] more")
        assert '<div class="image-compare"' not in result

    def test_not_matched_inside_fence(self) -> None:
        md = markdown.Markdown(extensions=["pymdownx.superfences", "pymdownx.highlight", "markwright.image_compare"])
        result = md.convert("```\n[compare https://a.png https://b.png]\n```")
        assert '<div class="image-compare"' not in result

    def test_single_url_not_matched(self) -> None:
        result = render_compare("[compare https://a.png]")
        assert '<div class="image-compare"' not in result

    def test_three_urls_not_matched(self) -> None:
        result = render_compare("[compare https://a.png https://b.png https://c.png]")
        assert '<div class="image-compare"' not in result


class TestCompareSvgUpstreamParity:
    """Tests that the control-arrow SVG matches upstream compare.js:110."""

    UPSTREAM_PATH_D = (
        "M504.3 273.6c4.9-4.5 7.7-10.9 7.7-17.6s-2.8-13-7.7-17.6l-112-104c-7-6.5-17.2-8.2-25.9-4.4s-14.4 12.5-14.4 "
        "22l0 56-192 0 0-56c0-9.5-5.7-18.2-14.4-22s-18.9-2.1-25.9 4.4l-112 104C2.8 243 0 249.3 0 256s2.8 13 7.7 "
        "17.6l112 104c7 6.5 17.2 8.2 25.9 4.4s14.4-12.5 14.4-22l0-56 192 0 0 56c0 9.5 5.7 18.2 14.4 22s18.9 2.1 "
        "25.9-4.4l112-104z"
    )

    def test_svg_uses_upstream_viewbox_and_single_path(self) -> None:
        result = render_compare("[compare https://left.png https://right.png]")
        assert '<svg class="control-arrow" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">' in result
        assert result.count("<path") == 1
        assert "<polygon" not in result

    def test_path_d_matches_upstream_exactly(self) -> None:
        result = render_compare("[compare https://left.png https://right.png]")
        assert f'<path fill="currentColor" d="{self.UPSTREAM_PATH_D}"/>' in result


class TestImageCompareExpandSource:
    """Tests for the pure expand_source stage function."""

    def test_expands_standalone_embed(self) -> None:
        result = expand_source("[compare https://a.jpg https://b.jpg]")
        assert '<div class="image-compare"' in result

    def test_no_stash_placeholder(self) -> None:
        result = expand_source("[compare https://a.jpg https://b.jpg]")
        assert "\x02" not in result

    def test_inline_embed_unchanged(self) -> None:
        source = "text [compare https://a.jpg https://b.jpg] text"
        assert expand_source(source) == source

    def test_multiline_only_standalone_expanded(self) -> None:
        source = "before line\n[compare https://a.jpg https://b.jpg]\nafter line"
        result = expand_source(source)
        lines = result.split("\n")
        assert lines[0] == "before line"
        assert lines[-1] == "after line"
        assert '<div class="image-compare"' in result

    def test_no_embed_passes_through(self) -> None:
        source = "just some text\nmore text"
        assert expand_source(source) == source
