# ABOUTME: Image compare embed extension for Python-Markdown.
# Converts [compare URL1 URL2 height width] syntax to side-by-side image comparison with slider.

from __future__ import annotations

import html
import re

from markdown import Markdown
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor

COMPARE_RE = re.compile(r"^\[compare\s+(\S+)\s+(\S+)(?:\s+(\d+))?(?:\s+(\d+))?\]$")

DEFAULT_HEIGHT = 270
DEFAULT_WIDTH = 480

SVG_ARROW = (
    '<svg class="control-arrow" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">'
    '<path fill="currentColor" d="M504.3 273.6c4.9-4.5 7.7-10.9 7.7-17.6s-2.8-13-7.7-17.6l-112-104c-7-6.5-17.2-8.2'
    "-25.9-4.4s-14.4 12.5-14.4 22l0 56-192 0 0-56c0-9.5-5.7-18.2-14.4-22s-18.9-2.1-25.9 4.4l-112 104C2.8 243 0 "
    "249.3 0 256s2.8 13 7.7 17.6l112 104c7 6.5 17.2 8.2 25.9 4.4s14.4-12.5 14.4-22l0-56 192 0 0 56c0 9.5 5.7 18.2 "
    '14.4 22s18.9 2.1 25.9-4.4l112-104z"/>'
    "</svg>"
)


def _render_match(line: str) -> str | None:
    """Build the image compare HTML for a standalone compare embed line.

    :param line: A single source line.
    :returns: The compare HTML if the line is a compare embed, else ``None``.
    """
    compare_match = COMPARE_RE.match(line.strip())
    if not compare_match:
        return None

    left_url = compare_match.group(1)
    right_url = compare_match.group(2)
    height = int(compare_match.group(3)) if compare_match.group(3) else DEFAULT_HEIGHT
    width = int(compare_match.group(4)) if compare_match.group(4) else DEFAULT_WIDTH

    return _build_compare_html(left_url, right_url, height, width)


def expand_source(text: str) -> str:
    """Expand standalone compare embed lines to HTML in raw source.

    Used by the ``mw pre`` CLI stage. Emits the HTML inline without any
    Python-Markdown stash placeholder.

    :param text: The source text.
    :returns: The text with standalone compare embeds replaced by HTML.
    """
    return "\n".join(_render_match(line) or line for line in text.split("\n"))


class ImageComparePreprocessor(Preprocessor):
    """Replace [compare ...] lines with image comparison HTML.

    :param md: The Markdown instance.
    """

    def run(self, lines: list[str]) -> list[str]:
        """Process lines, replacing image compare syntax with HTML.

        :param lines: Source lines to process.
        :returns: Modified lines with image compare embeds replaced by HTML.
        """
        output: list[str] = []
        for line in lines:
            # Stash the raw HTML so Markdown does not parse its contents. The
            # oninput handler contains a JS backtick template literal that
            # would otherwise be turned into an inline <code> span, and the
            # block-level <div> would be wrapped in an invalid <p>.
            compare_html = _render_match(line)
            if compare_html is not None:
                output.append(self.md.htmlStash.store(compare_html))
            else:
                output.append(line)
        return output


def _build_compare_html(left_url: str, right_url: str, height: int, width: int) -> str:
    """Build the image compare HTML from parsed arguments.

    :param left_url: URL for the left image.
    :param right_url: URL for the right image.
    :param height: Compare widget height in pixels.
    :param width: Compare widget width in pixels.
    :returns: Complete image compare HTML string.
    """
    escaped_left = html.escape(left_url)
    escaped_right = html.escape(right_url)

    return (
        f'<div class="image-compare" style="--value:50%; height: {height}px; width: {width}px;">\n'
        f'    <img class="image-left" src="{escaped_left}" alt="Image left"/>\n'
        f'    <img class="image-right" src="{escaped_right}" alt="Image right"/>\n'
        f'    <input type="range" class="control" min="0" max="100" value="50"\n'
        f"      oninput=\"this.parentNode.style.setProperty('--value', `${{this.value}}%`)\" />\n"
        f"    {SVG_ARROW}\n"
        f"</div>"
    )


class ImageCompareExtension(Extension):
    """Python-Markdown extension for side-by-side image comparison.

    :param \\*\\*kwargs: Configuration options passed to the extension.
    """

    def extendMarkdown(self, md: Markdown) -> None:
        """Register the image compare preprocessor.

        :param md: The Markdown instance to extend.
        """
        preprocessor = ImageComparePreprocessor(md)
        md.preprocessors.register(preprocessor, "do-image-compare", 20)


def makeExtension(**kwargs: object) -> ImageCompareExtension:
    """Create and return the ImageCompareExtension instance.

    :param \\*\\*kwargs: Configuration options.
    :returns: A configured ImageCompareExtension.
    """
    return ImageCompareExtension(**kwargs)
