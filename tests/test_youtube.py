# ABOUTME: Tests for the YouTube embed extension.
# Validates iframe generation, dimensions, aspect ratio, and edge cases.

from __future__ import annotations

import markdown

from markwright.youtube import expand_source


def render_youtube(source: str) -> str:
    """Render Markdown source with the YouTube extension loaded.

    :param source: Markdown source text.
    :returns: Rendered HTML string.
    """
    md = markdown.Markdown(extensions=["markwright.youtube"])
    return md.convert(source)


class TestYouTubeBasic:
    """Tests for basic YouTube embed rendering."""

    def test_basic_embed(self) -> None:
        result = render_youtube("[youtube iom_nhYQIYk]")
        assert '<iframe src="https://www.youtube.com/embed/iom_nhYQIYk"' in result
        assert 'height="270"' in result
        assert 'width="480"' in result
        assert 'class="youtube"' in result
        assert 'frameborder="0"' in result
        assert "allowfullscreen" in result
        assert '<a href="https://www.youtube.com/watch?v=iom_nhYQIYk"' in result
        assert 'target="_blank"' in result
        assert "View YouTube video" in result

    def test_default_aspect_ratio(self) -> None:
        result = render_youtube("[youtube iom_nhYQIYk]")
        assert 'style="aspect-ratio: 16/9"' in result


class TestYouTubeDimensions:
    """Tests for custom height and width dimensions."""

    def test_custom_height_and_width(self) -> None:
        result = render_youtube("[youtube iom_nhYQIYk 225 400]")
        assert 'height="225"' in result
        assert 'width="400"' in result

    def test_height_only(self) -> None:
        result = render_youtube("[youtube iom_nhYQIYk 380]")
        assert 'height="380"' in result
        assert 'width="480"' in result

    def test_aspect_ratio_default_dimensions(self) -> None:
        result = render_youtube("[youtube abc 270 480]")
        assert 'style="aspect-ratio: 16/9"' in result

    def test_aspect_ratio_square(self) -> None:
        result = render_youtube("[youtube abc 100 100]")
        assert 'style="aspect-ratio: 1/1"' in result

    def test_aspect_ratio_custom(self) -> None:
        result = render_youtube("[youtube abc 225 400]")
        assert 'style="aspect-ratio: 16/9"' in result


class TestYouTubeEdgeCases:
    """Tests for edge cases and non-matching input."""

    def test_not_matched_inside_paragraph(self) -> None:
        result = render_youtube("Some text [youtube abc] more text")
        assert "<iframe" not in result

    def test_not_matched_inside_fence(self) -> None:
        md = markdown.Markdown(extensions=["pymdownx.superfences", "pymdownx.highlight", "markwright.youtube"])
        result = md.convert("```\n[youtube abc]\n```")
        assert "<iframe" not in result

    def test_video_id_url_encoded(self) -> None:
        result = render_youtube("[youtube a&b<c]")
        assert "a%26b%3Cc" in result
        assert "a&b<c" not in result

    def test_not_wrapped_in_paragraph(self) -> None:
        result = render_youtube("[youtube dQw4w9WgXcQ]")
        assert "<p><iframe" not in result


class TestYouTubeExpandSource:
    """Tests for the pure expand_source stage function."""

    def test_expands_standalone_embed(self) -> None:
        result = expand_source("[youtube dQw4w9WgXcQ]")
        assert "<iframe" in result
        assert "youtube.com/embed/dQw4w9WgXcQ" in result

    def test_no_stash_placeholder(self) -> None:
        result = expand_source("[youtube dQw4w9WgXcQ]")
        assert "\x02" not in result

    def test_inline_embed_unchanged(self) -> None:
        source = "text [youtube abc] text"
        assert expand_source(source) == source

    def test_multiline_only_standalone_expanded(self) -> None:
        source = "before line\n[youtube dQw4w9WgXcQ]\nafter line"
        result = expand_source(source)
        lines = result.split("\n")
        assert lines[0] == "before line"
        assert lines[-1] == "after line"
        assert "<iframe" in lines[1]

    def test_no_embed_passes_through(self) -> None:
        source = "just some text\nmore text"
        assert expand_source(source) == source
