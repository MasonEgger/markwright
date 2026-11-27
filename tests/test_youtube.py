# ABOUTME: Tests for the YouTube embed extension.
# Validates iframe generation, dimensions, aspect ratio, and edge cases.

from __future__ import annotations

import markdown
import pytest

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


class TestYouTubeDegenerateDimensions:
    """Tests for zero and negative dimensions, which must fall back to 16:9."""

    def test_both_dimensions_zero_falls_back_to_default_ratio(self) -> None:
        result = expand_source("[youtube dQw4w9WgXcQ 0 0]")
        assert "<iframe" in result
        assert 'style="aspect-ratio: 16/9"' in result

    def test_second_dimension_zero_falls_back_to_default_ratio(self) -> None:
        result = expand_source("[youtube ID 480 0]")
        assert "<iframe" in result
        assert 'style="aspect-ratio: 16/9"' in result

    def test_negative_dimension_falls_back_to_default_ratio(self) -> None:
        result = expand_source("[youtube ID -1 9]")
        assert "<iframe" in result
        assert 'style="aspect-ratio: 16/9"' in result

    def test_valid_dimensions_still_unchanged(self) -> None:
        result = expand_source("[youtube dQw4w9WgXcQ 450 800]")
        assert 'style="aspect-ratio: 16/9"' in result
        assert 'height="450"' in result
        assert 'width="800"' in result


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
        assert lines[1] == ""
        assert lines[-1] == "after line"
        assert lines[-2] == ""
        assert "<iframe" in lines[2]

    def test_no_embed_passes_through(self) -> None:
        source = "just some text\nmore text"
        assert expand_source(source) == source

    def test_directive_inside_fence_is_unchanged(self) -> None:
        source = "```\n[youtube dQw4w9WgXcQ]\n```"
        assert expand_source(source) == source


class TestYoutubeSkipsIndentedCode:
    """The in-process preprocessor leaves a directive in an indented code block literal."""

    def test_indented_code_block_stays_literal(self) -> None:
        result = render_youtube("para\n\n    [youtube iom_nhYQIYk]\n")
        assert "<pre><code>[youtube iom_nhYQIYk]" in result
        assert "<iframe" not in result

    def test_directive_under_a_list_item_still_expands(self) -> None:
        assert "<iframe" in render_youtube("- item\n\n    [youtube iom_nhYQIYk]\n")


class TestInsideVerbatimRegions:
    """A directive line inside a comment or a <pre> block stays literal in both paths."""

    @pytest.mark.parametrize(
        "source",
        [
            "<!--\n[youtube dQw4w9WgXcQ]\n-->\n",
            "<pre>\n[youtube dQw4w9WgXcQ]\n</pre>\n",
            "<script>\n[youtube dQw4w9WgXcQ]\n</script>\n",
        ],
        ids=["comment", "pre", "script"],
    )
    def test_directive_stays_literal(self, source: str) -> None:
        assert expand_source(source) == source
        assert "<iframe" not in render_youtube(source)
        assert "[youtube dQw4w9WgXcQ]" in render_youtube(source)


class TestYouTubeInsideRawHtml:
    """A directive line in a raw ``<div>`` with no blank lines expands in-process, as ``expand_source`` does."""

    DIRECTIVE = "[youtube dQw4w9WgXcQ]"
    SOURCE = f'<div class="note">\n{DIRECTIVE}\n</div>'

    def test_the_directive_expands_in_the_div(self) -> None:
        rendered = render_youtube(self.SOURCE)

        assert expand_source(self.DIRECTIVE) in rendered
        assert self.DIRECTIVE not in rendered
        assert rendered.startswith('<div class="note">')


class TestYouTubeIsItsOwnBlock:
    """An embed beside text gets a blank line on each side, so it never joins a paragraph."""

    IFRAME_OPEN = '<iframe src="https://www.youtube.com/embed/abc"'

    def test_expand_source_adds_a_blank_line_on_each_side(self) -> None:
        result = expand_source("Intro\n[youtube abc]\nOutro\n")

        lines = result.split("\n")
        assert lines[0] == "Intro"
        assert lines[1] == ""
        assert lines[-3] == ""
        assert lines[-2] == "Outro"

    def test_an_embed_between_blank_lines_is_byte_identical(self) -> None:
        source = "Intro\n\n[youtube abc]\n\nOutro\n"

        result = expand_source(source)

        assert result.startswith("Intro\n\n<iframe")
        assert result.endswith("</iframe>\n\nOutro\n")
        assert "\n\n\n" not in result

    def test_consecutive_embeds_share_one_blank_line(self) -> None:
        result = expand_source("[youtube abc]\n[youtube def]\n")

        assert "\n\n\n" not in result
        assert result.count("<iframe") == 2

    def test_an_embed_at_the_start_and_end_of_a_document_adds_no_outer_blank_line(self) -> None:
        result = expand_source("[youtube abc]")

        assert result.startswith("<")
        assert not result.endswith("\n")

    def test_an_indented_embed_under_a_list_item_keeps_empty_blank_lines(self) -> None:
        result = expand_source("- item\n    [youtube abc]\n    more\n")

        lines = result.split("\n")
        assert lines[0] == "- item"
        assert lines[1] == ""
        assert lines[2].startswith("    <")
        assert lines[-3] == ""
        assert lines[-2] == "    more"

    def test_an_embed_inside_a_raw_div_gets_no_blank_lines(self) -> None:
        source = '<div class="note">\n[youtube abc]\nbeside\n</div>\n'

        result = expand_source(source)

        assert result.startswith('<div class="note">\n<')
        assert result.endswith("\nbeside\n</div>\n")

    def test_an_embed_after_a_blank_line_inside_a_div_is_outside_the_block_for_commonmark(self) -> None:
        source = "<div>\n\n[youtube abc]\nbeside\n</div>\n"

        result = expand_source(source)

        assert "\n\n<iframe" in result
        assert "</iframe>\n\nbeside" in result

    def test_in_process_the_paragraph_splits_around_the_embed(self) -> None:
        result = render_youtube("Intro\n[youtube abc]\nOutro *line*\n")

        assert "<p>Intro</p>" in result
        assert f"<p>{self.IFRAME_OPEN}" not in result
        assert "<p>Outro <em>line</em></p>" in result

    def test_in_process_a_tight_list_item_holding_an_embed_renders_loose(self) -> None:
        result = render_youtube("- item\n    [youtube abc]\n- next\n")

        assert "<li>\n<p>item</p>" in result
        assert self.IFRAME_OPEN in result
        assert result.count("<li>") == 2

    def test_expand_source_ends_the_item_text_after_an_embed_in_a_blank_line(self) -> None:
        result = expand_source("1. Watch this:\n    [youtube abc]\n    Then run *this* command.\n2. Next\n")

        assert result.endswith("</iframe>\n\n    Then run *this* command.\n\n2. Next\n")

    def test_in_process_the_item_after_text_that_follows_an_embed_stays_an_item(self) -> None:
        result = render_youtube("1. Watch this:\n    [youtube abc]\n    Then run *this* command.\n2. Next\n")

        assert result.count("<li>") == 2
        assert "<p>Then run <em>this</em> command.</p>" in result
        assert "<li>\n<p>Next</p>\n</li>" in result

    def test_in_process_an_embed_in_a_div_stays_where_it_is(self) -> None:
        result = render_youtube("<div>\n[youtube abc]\nbeside\n</div>\n")

        assert result.startswith("<div>\n<iframe")
        assert "<p>" not in result


class TestYouTubeUnderAShallowListItem:
    """An embed under a list item at two, three, and four columns renders in the first item of one list in-process."""

    @pytest.mark.parametrize(
        "source",
        [
            "- item\n  [youtube abc]\n- next\n",
            "1. Step\n   [youtube abc]\n2. Next\n",
            "- item\n    [youtube abc]\n- next\n",
        ],
        ids=["bullet-2", "ordered-3", "bullet-4"],
    )
    def test_in_process_the_list_stays_one_list_with_the_embed_in_the_first_item(self, source: str) -> None:
        result = render_youtube(source)

        assert result.count("<ul>") + result.count("<ol>") == 1
        assert result.index("<li>") < result.index("<iframe") < result.rindex("<li>")

    @pytest.mark.parametrize(
        ("source", "indent"),
        [("- item\n  [youtube abc]\n- next\n", "  "), ("1. Step\n   [youtube abc]\n2. Next\n", "   ")],
        ids=["bullet-2", "ordered-3"],
    )
    def test_expand_source_adds_blank_lines_at_two_and_three_columns(self, source: str, indent: str) -> None:
        lines = expand_source(source).split("\n")

        assert lines[1] == ""
        assert lines[2].startswith(f"{indent}<iframe")
        assert lines[-3] == ""

    def test_expand_source_is_stable_over_its_own_output(self) -> None:
        once = expand_source("- item\n  [youtube abc]\n  Then *this*.\n- next\n")

        assert expand_source(once) == once
