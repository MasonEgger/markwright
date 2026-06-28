# ABOUTME: Slideshow embed extension for Python-Markdown.
# Converts [slideshow URL1 URL2 ... height width] syntax to image slideshow HTML.

from __future__ import annotations

import html
import re

from markdown import Markdown
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor

SLIDESHOW_RE = re.compile(r"^\[slideshow\s+(.+)\]$")

DEFAULT_HEIGHT = 270
DEFAULT_WIDTH = 480


def _parse_slideshow_args(raw_args: str) -> tuple[list[str], int, int]:
    """Parse slideshow arguments into URLs and optional dimensions.

    Separates URLs from trailing integer arguments (height, width).
    Requires at least 2 URLs.

    :param raw_args: The raw argument string after 'slideshow'.
    :returns: Tuple of (urls, height, width). Returns empty urls list if fewer than 2 URLs.
    """
    parts = raw_args.split()

    # Separate trailing integers from URLs
    trailing_ints: list[int] = []
    while parts and parts[-1].isdigit():
        trailing_ints.insert(0, int(parts.pop()))

    urls = parts

    if len(urls) < 2:
        return [], DEFAULT_HEIGHT, DEFAULT_WIDTH

    height = trailing_ints[0] if len(trailing_ints) >= 1 else DEFAULT_HEIGHT
    width = trailing_ints[1] if len(trailing_ints) >= 2 else DEFAULT_WIDTH

    return urls, height, width


class SlideshowPreprocessor(Preprocessor):
    """Replace [slideshow ...] lines with slideshow HTML.

    :param md: The Markdown instance.
    """

    def run(self, lines: list[str]) -> list[str]:
        """Process lines, replacing slideshow embed syntax with HTML.

        :param lines: Source lines to process.
        :returns: Modified lines with slideshow embeds replaced by HTML.
        """
        output: list[str] = []
        for line in lines:
            stripped_line = line.strip()
            slideshow_match = SLIDESHOW_RE.match(stripped_line)
            if slideshow_match:
                urls, height, width = _parse_slideshow_args(slideshow_match.group(1))
                if urls:
                    slideshow_html = _build_slideshow_html(urls, height, width)
                    output.append(self.md.htmlStash.store(slideshow_html))
                else:
                    output.append(line)
            else:
                output.append(line)
        return output


def _build_slideshow_html(urls: list[str], height: int, width: int) -> str:
    """Build the slideshow HTML from parsed arguments.

    :param urls: List of image URLs.
    :param height: Slideshow height in pixels.
    :param width: Slideshow width in pixels.
    :returns: Complete slideshow HTML string.
    """
    slides = "\n".join(
        f'    <img src="{html.escape(url)}" alt="Slide #{slide_index}" />'
        for slide_index, url in enumerate(urls, start=1)
    )

    scroll_js = "this.parentElement.querySelector('.slides').scrollBy"
    left_arrow = f'  <div class="action left" onclick="{scroll_js}(-{width}, 0)">&#8249;</div>\n'
    right_arrow = f'  <div class="action right" onclick="{scroll_js}({width}, 0)">&#8250;</div>\n'

    return (
        f'<div class="slideshow" style="height: {height}px; width: {width}px;">\n'
        f"{left_arrow}"
        f"{right_arrow}"
        f'  <div class="slides">\n'
        f"{slides}\n"
        f"  </div>\n"
        f"</div>"
    )


class SlideshowExtension(Extension):
    """Python-Markdown extension for image slideshow embeds.

    :param \\*\\*kwargs: Configuration options passed to the extension.
    """

    def extendMarkdown(self, md: Markdown) -> None:
        """Register the slideshow preprocessor.

        :param md: The Markdown instance to extend.
        """
        preprocessor = SlideshowPreprocessor(md)
        md.preprocessors.register(preprocessor, "do-slideshow", 20)


def makeExtension(**kwargs: object) -> SlideshowExtension:
    """Create and return the SlideshowExtension instance.

    :param \\*\\*kwargs: Configuration options.
    :returns: A configured SlideshowExtension.
    """
    return SlideshowExtension(**kwargs)
