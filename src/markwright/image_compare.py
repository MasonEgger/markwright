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
    '<svg class="control-arrow" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
    '<polygon points="30,50 45,35 45,48 70,48 70,52 45,52 45,65" fill="currentColor"/>'
    '<polygon points="70,50 55,35 55,48 30,48 30,52 55,52 55,65" fill="currentColor"/>'
    "</svg>"
)


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
            stripped_line = line.strip()
            compare_match = COMPARE_RE.match(stripped_line)
            if compare_match:
                left_url = compare_match.group(1)
                right_url = compare_match.group(2)
                height = int(compare_match.group(3)) if compare_match.group(3) else DEFAULT_HEIGHT
                width = int(compare_match.group(4)) if compare_match.group(4) else DEFAULT_WIDTH

                compare_html = _build_compare_html(left_url, right_url, height, width)
                # Stash the raw HTML so Markdown does not parse its contents. The
                # oninput handler contains a JS backtick template literal that
                # would otherwise be turned into an inline <code> span, and the
                # block-level <div> would be wrapped in an invalid <p>.
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
