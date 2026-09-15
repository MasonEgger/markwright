# ABOUTME: Tests for the Instagram embed extension.
# Covers basic embeds, caption flag, alignment, width clamping, and script injection.

from __future__ import annotations

import markdown

from markwright.instagram import apply_html, expand_source


def render(source: str) -> str:
    """Render Markdown source with the Instagram extension loaded."""
    md = markdown.Markdown(extensions=["markwright.instagram"])
    return md.convert(source)


class TestInstagramBasic:
    """Tests for basic Instagram embed functionality."""

    def test_basic_embed(self) -> None:
        result = render("[instagram https://www.instagram.com/p/CkQuv3_LRgS]")
        assert '<div class="instagram">' in result
        assert '<blockquote class="instagram-media"' in result
        assert 'data-instgrm-permalink="https://www.instagram.com/p/CkQuv3_LRgS"' in result
        assert 'data-instgrm-version="14"' in result
        assert "instagram.com/embed.js" in result

    def test_fallback_link(self) -> None:
        result = render("[instagram https://www.instagram.com/p/CkQuv3_LRgS]")
        assert "View post" in result
        assert "https://www.instagram.com/p/CkQuv3_LRgS" in result


class TestInstagramCaption:
    """Tests for the caption flag."""

    def test_caption_flag(self) -> None:
        result = render("[instagram https://www.instagram.com/p/ABC caption]")
        assert "data-instgrm-captioned" in result

    def test_no_caption_by_default(self) -> None:
        result = render("[instagram https://www.instagram.com/p/ABC]")
        assert "data-instgrm-captioned" not in result


class TestInstagramAlignment:
    """Tests for Instagram alignment flags."""

    def test_left_alignment(self) -> None:
        result = render("[instagram https://www.instagram.com/p/ABC left]")
        assert 'align="left"' in result

    def test_right_alignment(self) -> None:
        result = render("[instagram https://www.instagram.com/p/ABC right]")
        assert 'align="right"' in result

    def test_center_alignment_default(self) -> None:
        """Center is the default — no align attribute should be present."""
        result = render("[instagram https://www.instagram.com/p/ABC]")
        assert "align=" not in result


class TestInstagramWidth:
    """Tests for Instagram width flags and clamping."""

    def test_custom_width(self) -> None:
        result = render("[instagram https://www.instagram.com/p/ABC 400]")
        assert 'style="width: 400px;"' in result

    def test_width_clamped_min(self) -> None:
        """Width below 326 should be clamped to 326."""
        result = render("[instagram https://www.instagram.com/p/ABC 100]")
        assert 'style="width: 326px;"' in result

    def test_width_clamped_max(self) -> None:
        """Width above 550 should be clamped to 550."""
        result = render("[instagram https://www.instagram.com/p/ABC 999]")
        assert 'style="width: 550px;"' in result

    def test_no_width_style_by_default(self) -> None:
        """Default width is 0 (auto) — no style attribute should be present."""
        result = render("[instagram https://www.instagram.com/p/ABC]")
        assert "style=" not in result


class TestInstagramCombined:
    """Tests for combined flags."""

    def test_combined_flags(self) -> None:
        result = render("[instagram https://www.instagram.com/p/ABC left caption 400]")
        assert 'align="left"' in result
        assert "data-instgrm-captioned" in result
        assert 'style="width: 400px;"' in result


class TestInstagramScript:
    """Tests for script injection behavior."""

    def test_script_injected_once_for_multiple_posts(self) -> None:
        result = render(
            "[instagram https://www.instagram.com/p/ABC]\n\nSome text\n\n[instagram https://www.instagram.com/p/DEF]"
        )
        script_count = result.count("instagram.com/embed.js")
        assert script_count == 1

    def test_no_script_without_embed(self) -> None:
        result = render("Just some text")
        assert "instagram.com/embed.js" not in result


class TestInstagramEdgeCases:
    """Tests for edge cases."""

    def test_not_matched_inside_paragraph(self) -> None:
        result = render("Some text [instagram https://www.instagram.com/p/ABC] more text")
        assert "instagram-media" not in result

    def test_not_matched_inside_fence(self) -> None:
        md = markdown.Markdown(extensions=["pymdownx.superfences", "markwright.instagram"])
        result = md.convert("```\n[instagram https://www.instagram.com/p/ABC]\n```")
        assert "instagram-media" not in result

    def test_not_wrapped_in_paragraph(self) -> None:
        result = render("[instagram https://www.instagram.com/p/ABC]")
        assert "<p><div" not in result


class TestInstagramPermalinkNormalization:
    """Tests for the normalized data-instgrm-permalink attribute (R7a)."""

    def test_permalink_normalized_for_www_url(self) -> None:
        result = render("[instagram https://www.instagram.com/p/CkQuv3_LRgS]")
        assert 'data-instgrm-permalink="https://www.instagram.com/p/CkQuv3_LRgS"' in result

    def test_permalink_normalized_without_www_host(self) -> None:
        result = render("[instagram https://instagram.com/p/CkQuv3_LRgS]")
        assert 'data-instgrm-permalink="https://www.instagram.com/p/CkQuv3_LRgS"' in result

    def test_permalink_normalized_for_bare_shortcode(self) -> None:
        result = render("[instagram CkQuv3_LRgS]")
        assert 'data-instgrm-permalink="https://www.instagram.com/p/CkQuv3_LRgS"' in result


class TestInstagramShortcodeGrammar:
    """Tests for the permissive upstream shortcode grammar (R6, D2: full parity).

    Scheme, ``www.``, the host, and the ``p/`` path segment are all optional,
    so inputs ranging from a bare shortcode up to a full
    ``https://www.instagram.com/p/<shortcode>`` all match, and the permalink
    stays normalized to the canonical ``www`` URL (R7a) for every input shape.
    """

    def test_bare_shortcode(self) -> None:
        result = render("[instagram CkQuv3_LRgS]")
        assert '<blockquote class="instagram-media"' in result
        assert 'data-instgrm-permalink="https://www.instagram.com/p/CkQuv3_LRgS"' in result

    def test_scheme_less_host_with_path(self) -> None:
        result = render("[instagram instagram.com/p/CkQuv3_LRgS]")
        assert '<blockquote class="instagram-media"' in result
        assert 'data-instgrm-permalink="https://www.instagram.com/p/CkQuv3_LRgS"' in result

    def test_www_host_with_path(self) -> None:
        result = render("[instagram www.instagram.com/p/CkQuv3_LRgS]")
        assert '<blockquote class="instagram-media"' in result
        assert 'data-instgrm-permalink="https://www.instagram.com/p/CkQuv3_LRgS"' in result

    def test_bare_shortcode_visible_href_is_canonical(self) -> None:
        """A bare shortcode has no URL to reuse for the visible anchor, so it

        must be built from the canonical non-www form instead, matching
        upstream's ``https://instagram.com/p/<post>`` anchor.
        """
        result = render("[instagram CkQuv3_LRgS]")
        assert '<a href="https://instagram.com/p/CkQuv3_LRgS">View post</a>' in result


class TestInstagramStageFunctions:
    """Tests for the pure expand_source and apply_html stage functions."""

    def test_expand_source_emits_signature(self) -> None:
        result = expand_source("[instagram https://www.instagram.com/p/CkQuv3_LRgS]")
        assert 'class="instagram-media"' in result
        assert "https://www.instagram.com/p/CkQuv3_LRgS" in result

    def test_expand_source_no_stash_placeholder(self) -> None:
        result = expand_source("[instagram https://www.instagram.com/p/CkQuv3_LRgS]")
        assert "\x02" not in result

    def test_apply_html_injects_one_script(self) -> None:
        result = apply_html('<blockquote class="instagram-media"></blockquote>')
        assert result.count("embed.js") == 1

    def test_apply_html_idempotent(self) -> None:
        once = apply_html('<blockquote class="instagram-media"></blockquote>')
        twice = apply_html(once)
        assert twice.count("embed.js") == 1

    def test_apply_html_no_signature_no_script(self) -> None:
        result = apply_html("<p>nothing here</p>")
        assert "embed.js" not in result

    def test_apply_html_warnings_stay_empty(self) -> None:
        warnings: list[str] = []
        apply_html('<blockquote class="instagram-media"></blockquote>', warnings)
        assert warnings == []
