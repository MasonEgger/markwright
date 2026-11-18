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
