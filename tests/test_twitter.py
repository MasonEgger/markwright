# ABOUTME: Tests for the Twitter embed extension.
# Covers basic embeds, x.com canonicalization, theme, alignment, width clamping, and script injection.

from __future__ import annotations

import markdown

from markwright.twitter import apply_html, expand_source


def render(source: str) -> str:
    """Render Markdown source with the Twitter extension loaded."""
    md = markdown.Markdown(extensions=["markwright.twitter"])
    return md.convert(source)


class TestTwitterBasic:
    """Tests for basic Twitter embed functionality."""

    def test_basic_embed(self) -> None:
        result = render("[twitter https://twitter.com/User/status/123]")
        assert '<div class="twitter">' in result
        assert '<blockquote class="twitter-tweet"' in result
        assert 'data-dnt="true"' in result
        assert 'data-width="550"' in result
        assert 'data-theme="light"' in result
        assert "https://twitter.com/User/status/123" in result
        assert "platform.twitter.com/widgets.js" in result

    def test_xcom_domain_canonicalized(self) -> None:
        """x.com URLs should be canonicalized to twitter.com in the output."""
        result = render("[twitter https://x.com/User/status/123]")
        assert "https://twitter.com/User/status/123" in result
        assert "x.com" not in result


class TestTwitterTheme:
    """Tests for Twitter theme flags."""

    def test_dark_theme(self) -> None:
        result = render("[twitter https://twitter.com/U/status/1 dark]")
        assert 'data-theme="dark"' in result

    def test_light_theme_default(self) -> None:
        result = render("[twitter https://twitter.com/U/status/1]")
        assert 'data-theme="light"' in result


class TestTwitterAlignment:
    """Tests for Twitter alignment flags."""

    def test_left_alignment(self) -> None:
        result = render("[twitter https://twitter.com/U/status/1 left]")
        assert 'align="left"' in result

    def test_right_alignment(self) -> None:
        result = render("[twitter https://twitter.com/U/status/1 right]")
        assert 'align="right"' in result

    def test_center_alignment_default(self) -> None:
        """Center is the default — no align attribute should be present."""
        result = render("[twitter https://twitter.com/U/status/1]")
        assert "align=" not in result

    def test_center_alignment_explicit(self) -> None:
        """Explicit center should also produce no align attribute."""
        result = render("[twitter https://twitter.com/U/status/1 center]")
        assert "align=" not in result


class TestTwitterWidth:
    """Tests for Twitter width flags and clamping."""

    def test_custom_width(self) -> None:
        result = render("[twitter https://twitter.com/U/status/1 400]")
        assert 'data-width="400"' in result

    def test_width_clamped_min(self) -> None:
        """Width below 250 should be clamped to 250."""
        result = render("[twitter https://twitter.com/U/status/1 100]")
        assert 'data-width="250"' in result

    def test_width_clamped_max(self) -> None:
        """Width above 550 should be clamped to 550."""
        result = render("[twitter https://twitter.com/U/status/1 999]")
        assert 'data-width="550"' in result


class TestTwitterCombined:
    """Tests for combined flags."""

    def test_combined_flags(self) -> None:
        result = render("[twitter https://twitter.com/U/status/1 left 400 dark]")
        assert 'data-theme="dark"' in result
        assert 'align="left"' in result
        assert 'data-width="400"' in result


class TestTwitterScript:
    """Tests for script injection behavior."""

    def test_script_injected_once_for_multiple_tweets(self) -> None:
        result = render(
            "[twitter https://twitter.com/A/status/1]\n\nSome text\n\n[twitter https://twitter.com/B/status/2]"
        )
        script_count = result.count("platform.twitter.com/widgets.js")
        assert script_count == 1

    def test_no_script_without_embed(self) -> None:
        result = render("Just some text")
        assert "platform.twitter.com" not in result


class TestTwitterEdgeCases:
    """Tests for edge cases."""

    def test_not_matched_inside_paragraph(self) -> None:
        result = render("Some text [twitter https://twitter.com/U/status/1] more text")
        assert "twitter-tweet" not in result

    def test_not_matched_inside_fence(self) -> None:
        md = markdown.Markdown(extensions=["pymdownx.superfences", "markwright.twitter"])
        result = md.convert("```\n[twitter https://twitter.com/U/status/1]\n```")
        assert "twitter-tweet" not in result

    def test_not_wrapped_in_paragraph(self) -> None:
        result = render("[twitter https://twitter.com/U/status/1]")
        assert "<p><div" not in result


class TestTwitterUrlGrammar:
    """Tests for the permissive upstream URL grammar (R6, D2: full parity).

    Scheme, ``www.``, and the host itself are all optional, so inputs
    ranging from a bare ``user/status/id`` up to a full
    ``https://www.twitter.com/user/status/id`` all match.
    """

    def test_scheme_less_host(self) -> None:
        result = render("[twitter twitter.com/User/status/123]")
        assert "https://twitter.com/User/status/123" in result
        assert '<blockquote class="twitter-tweet"' in result

    def test_www_prefixed_host(self) -> None:
        result = render("[twitter https://www.twitter.com/User/status/123]")
        assert "https://twitter.com/User/status/123" in result
        assert '<blockquote class="twitter-tweet"' in result

    def test_xcom_host(self) -> None:
        result = render("[twitter https://x.com/User/status/123]")
        assert "https://twitter.com/User/status/123" in result
        assert '<blockquote class="twitter-tweet"' in result

    def test_bare_user_status_id(self) -> None:
        result = render("[twitter User/status/123]")
        assert "https://twitter.com/User/status/123" in result
        assert '<blockquote class="twitter-tweet"' in result


class TestTwitterStageFunctions:
    """Tests for the pure expand_source and apply_html stage functions."""

    def test_expand_source_emits_signature(self) -> None:
        result = expand_source("[twitter https://twitter.com/User/status/123]")
        assert 'class="twitter-tweet"' in result
        assert "https://twitter.com/User/status/123" in result

    def test_expand_source_no_stash_placeholder(self) -> None:
        result = expand_source("[twitter https://twitter.com/User/status/123]")
        assert "\x02" not in result

    def test_apply_html_injects_one_script(self) -> None:
        result = apply_html('<blockquote class="twitter-tweet"></blockquote>')
        assert result.count("widgets.js") == 1

    def test_apply_html_idempotent(self) -> None:
        once = apply_html('<blockquote class="twitter-tweet"></blockquote>')
        twice = apply_html(once)
        assert twice.count("widgets.js") == 1

    def test_apply_html_no_signature_no_script(self) -> None:
        result = apply_html("<p>nothing here</p>")
        assert "widgets.js" not in result

    def test_apply_html_warnings_stay_empty(self) -> None:
        warnings: list[str] = []
        apply_html('<blockquote class="twitter-tweet"></blockquote>', warnings)
        assert warnings == []
