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
