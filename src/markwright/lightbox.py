# ABOUTME: Lightbox directive extension for Python-Markdown.
# Converts [lightbox URL ALT TEXT] lines to an <a class="mw-lightbox"> link wrapping an <img>.

from __future__ import annotations

import html
import re
from typing import TYPE_CHECKING

from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor

if TYPE_CHECKING:
    from collections.abc import Mapping

    from markdown import Markdown

LIGHTBOX_RE = re.compile(r"^\[lightbox\s+(?P<url>\S+)(?:\s+(?P<alt>.+))?\]$")


def _render_match(line: str) -> str | None:
    """Build the lightbox link for a standalone lightbox directive line.

    :param line: A single source line.
    :returns: The ``<a>`` element if the line is a lightbox directive, else ``None``.
    """
    lightbox_match = LIGHTBOX_RE.match(line.strip())
    if not lightbox_match:
        return None

    escaped_url = html.escape(lightbox_match.group("url"))
    escaped_alt = html.escape(lightbox_match.group("alt") or "")

    return f'<a class="mw-lightbox" href="{escaped_url}"><img src="{escaped_url}" alt="{escaped_alt}" /></a>'


def expand_source(text: str, options: Mapping[str, object] | None = None) -> str:
    """Expand standalone lightbox directive lines to linked images in raw source.

    Used by the ``mw pre`` CLI stage. The link is inline HTML, so a renderer
    wraps it in a paragraph.

    :param text: The source text.
    :param options: Ignored; accepted so the registry calls every pre stage with one signature.
    :returns: The text with standalone lightbox directives replaced by linked images.
    """
    return "\n".join(_render_match(line) or line for line in text.split("\n"))


class LightboxPreprocessor(Preprocessor):
    """Replace [lightbox ...] lines with linked images.

    :param md: The Markdown instance.
    """

    def run(self, lines: list[str]) -> list[str]:
        """Process lines, replacing lightbox directives with linked images.

        :param lines: Source lines to process.
        :returns: Modified lines with lightbox directives replaced by inline HTML.
        """
        return [_render_match(line) or line for line in lines]


class LightboxExtension(Extension):
    """Python-Markdown extension for lightbox images.

    :param \\*\\*kwargs: Configuration options passed to the extension.
    """

    def extendMarkdown(self, md: Markdown) -> None:  # noqa: N802 - Python-Markdown's hook name
        """Register the lightbox preprocessor.

        :param md: The Markdown instance to extend.
        """
        md.preprocessors.register(LightboxPreprocessor(md), "mw-lightbox", 20)


def makeExtension(**kwargs: object) -> LightboxExtension:  # noqa: N802 - Python-Markdown's loader name
    """Create and return the LightboxExtension instance.

    :param \\*\\*kwargs: Configuration options.
    :returns: A configured LightboxExtension.
    """
    return LightboxExtension(**kwargs)
