# ABOUTME: Tests for the CodePen embed extension.
# Covers basic embeds, flag parsing (theme, height, tabs, lazy, editable), combined flags, and script injection.

from __future__ import annotations

import markdown


def render(source: str) -> str:
    """Render Markdown source with the CodePen extension loaded."""
    md = markdown.Markdown(extensions=["markwright.codepen"])
    return md.convert(source)


class TestCodePenBasic:
    """Tests for basic CodePen embed functionality."""

    def test_basic_embed(self) -> None:
        result = render("[codepen MattCowley vwPzeX]")
        assert 'data-user="MattCowley"' in result
        assert 'data-slug-hash="vwPzeX"' in result
        assert 'data-height="256"' in result
        assert 'data-theme-id="light"' in result
        assert 'data-default-tab="result"' in result
        assert 'class="codepen"' in result
        assert "static.codepen.io/assets/embed/ei.js" in result

    def test_fallback_link(self) -> None:
        result = render("[codepen MattCowley vwPzeX]")
        assert "See the Pen" in result
        assert "https://codepen.io/MattCowley/pen/vwPzeX" in result
        assert "vwPzeX by MattCowley" in result
        assert "@MattCowley" in result


class TestCodePenFlags:
    """Tests for individual CodePen flags."""

    def test_dark_theme(self) -> None:
        result = render("[codepen User Hash dark]")
        assert 'data-theme-id="dark"' in result

    def test_light_theme_default(self) -> None:
        result = render("[codepen User Hash]")
        assert 'data-theme-id="light"' in result

    def test_custom_height(self) -> None:
        result = render("[codepen User Hash 512]")
        assert 'data-height="512"' in result
        assert "height: 512px;" in result

    def test_tab_css(self) -> None:
        result = render("[codepen User Hash css]")
        assert 'data-default-tab="css"' in result

    def test_tab_js(self) -> None:
        result = render("[codepen User Hash js]")
        assert 'data-default-tab="js"' in result

    def test_tab_html_with_result(self) -> None:
        result = render("[codepen User Hash html result]")
        assert 'data-default-tab="html,result"' in result

    def test_tab_result_with_css(self) -> None:
        result = render("[codepen User Hash result css]")
        assert 'data-default-tab="css,result"' in result

    def test_lazy(self) -> None:
        result = render("[codepen User Hash lazy]")
        assert 'data-preview="true"' in result

    def test_editable(self) -> None:
        result = render("[codepen User Hash editable]")
        assert 'data-editable="true"' in result

    def test_no_lazy_by_default(self) -> None:
        result = render("[codepen User Hash]")
        assert "data-preview" not in result

    def test_no_editable_by_default(self) -> None:
        result = render("[codepen User Hash]")
        assert "data-editable" not in result


class TestCodePenCombinedFlags:
    """Tests for combined flag interactions."""

    def test_combined_flags(self) -> None:
        result = render("[codepen User Hash dark css 384 lazy]")
        assert 'data-theme-id="dark"' in result
        assert 'data-default-tab="css"' in result
        assert 'data-height="384"' in result
        assert 'data-preview="true"' in result

    def test_tab_priority_html_over_css(self) -> None:
        """When both html and css flags are present, html should win."""
        result = render("[codepen User Hash css html]")
        assert 'data-default-tab="html"' in result

    def test_tab_priority_css_over_js(self) -> None:
        """When both css and js flags are present, css should win."""
        result = render("[codepen User Hash js css]")
        assert 'data-default-tab="css"' in result

    def test_dark_overrides_light(self) -> None:
        """When both light and dark are present, dark wins."""
        result = render("[codepen User Hash light dark]")
        assert 'data-theme-id="dark"' in result


class TestCodePenScript:
    """Tests for script injection behavior."""

    def test_script_injected_once_for_multiple_embeds(self) -> None:
        result = render("[codepen A B]\n\nSome text\n\n[codepen C D]")
        script_count = result.count("static.codepen.io/assets/embed/ei.js")
        assert script_count == 1

    def test_no_script_without_embed(self) -> None:
        result = render("Just some text")
        assert "static.codepen.io" not in result


class TestCodePenEdgeCases:
    """Tests for edge cases."""

    def test_not_matched_inside_paragraph(self) -> None:
        result = render("Some text [codepen User Hash] more text")
        assert "data-user" not in result

    def test_not_matched_inside_fence(self) -> None:
        md = markdown.Markdown(extensions=["pymdownx.superfences", "markwright.codepen"])
        result = md.convert("```\n[codepen User Hash]\n```")
        assert "data-user" not in result

    def test_not_wrapped_in_paragraph(self) -> None:
        result = render("[codepen User Hash]")
        assert "<p><p" not in result
