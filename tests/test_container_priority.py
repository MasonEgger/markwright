# ABOUTME: Tests that the in-process grid, annotate, and tabs postprocessors work in any extension load order.
# They run below raw_html, so the markers are restored first whichever side md_in_html is listed on.

from __future__ import annotations

import markdown
import pytest

MARKWRIGHT_EXTENSIONS = ["markwright.grid", "markwright.annotate", "markwright.tabs"]

SOURCE = """\
[tab Python]

print(1)

[/tab]

[tab Node.js]

console.log(1)

[/tab]

[grid]

[card]

Card text.

[/card]

[/grid]

[grid cards]

- one
- two

[annotate]

Run (1) now.

1. first
"""


def render_with_order(md_in_html_first: bool) -> str:
    """Render SOURCE with md_in_html listed before or after the markwright extensions."""
    extensions = ["md_in_html", *MARKWRIGHT_EXTENSIONS] if md_in_html_first else [*MARKWRIGHT_EXTENSIONS, "md_in_html"]
    return markdown.Markdown(extensions=extensions).convert(SOURCE)


class TestLoadOrder:
    @pytest.mark.parametrize("md_in_html_first", [True, False], ids=["md_in_html_before", "md_in_html_after"])
    def test_markup_is_produced_and_no_marker_survives(self, md_in_html_first: bool) -> None:
        result = render_with_order(md_in_html_first)
        assert "tabbed-set tabbed-alternate mw-tabs" in result
        assert 'class="mw-grid' in result
        assert 'class="mw-annotation"' in result
        for marker in ("<!-- mw-tab", "<!-- mw-grid", "<!-- mw-annotate"):
            assert marker not in result


DIRECTIVE_EXTENSIONS = [
    "youtube",
    "button",
    "lightbox",
    "annotate",
    "codepen",
    "twitter",
    "instagram",
    "slideshow",
    "image_compare",
]
DIRECTIVE_LINES = (
    "[youtube dQw4w9WgXcQ]",
    "[button /start Go]",
    "[lightbox /a.png A]",
    "[slideshow https://a.png https://b.png]",
)


def render_all(source: str, names: list[str]) -> str:
    """Render source with the superfences stack and the named markwright extensions, in that order."""
    return markdown.Markdown(
        extensions=["pymdownx.superfences", *(f"markwright.{name}" for name in names)],
    ).convert(source)


class TestDirectivesAtTheContainerPriority:
    """The embed, button, lightbox, and annotate preprocessors sit beside grid and tabs, ahead of html_block."""

    @pytest.mark.parametrize("directive", DIRECTIVE_LINES)
    @pytest.mark.parametrize(
        "template",
        [
            "```\n{}\n```\n",
            "text\n\n    {}\n",
            "<!--\n{}\n-->\n",
            "<pre>\n{}\n</pre>\n",
        ],
        ids=["fence", "indented-code", "comment", "pre"],
    )
    def test_a_directive_in_code_or_a_verbatim_region_stays_literal(self, template: str, directive: str) -> None:
        rendered = render_all(template.format(directive), DIRECTIVE_EXTENSIONS)

        assert "mw-button" not in rendered
        assert "<iframe" not in rendered
        assert "mw-lightbox" not in rendered
        assert "mw-slideshow" not in rendered
        assert directive.replace("&", "&amp;") in rendered

    @pytest.mark.parametrize(
        "names",
        [DIRECTIVE_EXTENSIONS + ["grid", "tabs"], ["grid", "tabs", *DIRECTIVE_EXTENSIONS]],
        ids=["embeds-first", "containers-first"],
    )
    def test_load_order_among_the_21_preprocessors_changes_nothing(self, names: list[str]) -> None:
        source = (
            "[grid]\n\n[card]\n\n[button /start Go]\n\n[/card]\n\n[/grid]\n\n"
            "[tab One]\n\n[youtube dQw4w9WgXcQ]\n\n[/tab]\n\n[tab Two]\n\n[lightbox /a.png A]\n\n[/tab]\n"
        )
        reference = render_all(source, ["grid", "tabs", *DIRECTIVE_EXTENSIONS])

        assert render_all(source, names) == reference
        assert 'class="mw-card"' in reference
        assert 'class="mw-button"' in reference
        assert "mw-tab-1-1" in reference

    def test_a_directive_at_column_zero_outside_raw_html_is_unchanged(self) -> None:
        rendered = render_all("[button /start Go]", ["button"])

        assert rendered == '<p><a class="mw-button" href="/start">Go</a></p>'
