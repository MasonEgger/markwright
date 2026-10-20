# ABOUTME: Button directive extension for Python-Markdown.
# Converts [button URL TEXT] and [button primary URL TEXT] lines to an <a class="mw-button"> link.

from __future__ import annotations

import html
import re
from typing import TYPE_CHECKING

from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor

if TYPE_CHECKING:
    from collections.abc import Mapping

    from markdown import Markdown

BUTTON_RE = re.compile(r"^\[button(?:\s+(?P<primary>primary))?\s+(?P<url>\S+)\s+(?P<text>.+)\]$")


def _render_match(line: str) -> str | None:
    """Build the button link for a standalone button directive line.

    :param line: A single source line.
    :returns: The ``<a>`` element if the line is a button directive, else ``None``.
    """
    button_match = BUTTON_RE.match(line.strip())
    if not button_match:
        return None

    classes = "mw-button mw-button-primary" if button_match.group("primary") else "mw-button"
    escaped_url = html.escape(button_match.group("url"))
    escaped_text = html.escape(button_match.group("text"))

    return f'<a class="{classes}" href="{escaped_url}">{escaped_text}</a>'


def expand_source(text: str, options: Mapping[str, object] | None = None) -> str:
    """Expand standalone button directive lines to links in raw source.

    Used by the ``mw pre`` CLI stage. The link is inline HTML, so a renderer
    wraps it in a paragraph and still processes Markdown inside the text.

    :param text: The source text.
    :param options: Ignored; accepted so the registry calls every pre stage with one signature.
    :returns: The text with standalone button directives replaced by links.
    """
    return "\n".join(_render_match(line) or line for line in text.split("\n"))


class ButtonPreprocessor(Preprocessor):
    """Replace [button ...] lines with button links.

    :param md: The Markdown instance.
    """

    def run(self, lines: list[str]) -> list[str]:
        """Process lines, replacing button directives with links.

        :param lines: Source lines to process.
        :returns: Modified lines with button directives replaced by inline HTML.
        """
        return [_render_match(line) or line for line in lines]


class ButtonExtension(Extension):
    """Python-Markdown extension for button links.

    :param \\*\\*kwargs: Configuration options passed to the extension.
    """

    def extendMarkdown(self, md: Markdown) -> None:  # noqa: N802 - Python-Markdown's hook name
        """Register the button preprocessor.

        :param md: The Markdown instance to extend.
        """
        md.preprocessors.register(ButtonPreprocessor(md), "mw-button", 20)


def makeExtension(**kwargs: object) -> ButtonExtension:  # noqa: N802 - Python-Markdown's loader name
    """Create and return the ButtonExtension instance.

    :param \\*\\*kwargs: Configuration options.
    :returns: A configured ButtonExtension.
    """
    return ButtonExtension(**kwargs)
