# ABOUTME: YouTube embed extension for Python-Markdown.
# Converts [youtube ID height width] syntax to responsive iframe embeds, eager, lazy, or click-to-load.

from __future__ import annotations

import math
import re
import urllib.parse
from typing import TYPE_CHECKING

from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor

from markwright._embed_load import LOAD_CLICK, LOAD_EAGER, LOAD_LAZY, load_mode, wrap_preview
from markwright._fences import map_lines

if TYPE_CHECKING:
    from collections.abc import Mapping

    from markdown import Markdown

YOUTUBE_RE = re.compile(r"^\[youtube (\S+?)(?:\s+(-?\d+))?(?:\s+(-?\d+))?\]$")

DEFAULT_HEIGHT = 270
DEFAULT_WIDTH = 480

LOAD_MODES = (LOAD_EAGER, LOAD_LAZY, LOAD_CLICK)


def _render_match(line: str, load: str) -> str | None:
    """Build the iframe HTML for a standalone YouTube embed line.

    :param line: A single source line.
    :param load: The load mode: ``eager``, ``lazy`` (native iframe lazy loading), or ``click``.
    :returns: The iframe HTML (or its click-to-load preview) if the line is a YouTube embed, else ``None``.
    """
    youtube_match = YOUTUBE_RE.match(line.strip())
    if not youtube_match:
        return None

    video_id = youtube_match.group(1)
    height = int(youtube_match.group(2)) if youtube_match.group(2) else DEFAULT_HEIGHT
    width = int(youtube_match.group(3)) if youtube_match.group(3) else DEFAULT_WIDTH
    if height <= 0 or width <= 0:
        height, width = DEFAULT_HEIGHT, DEFAULT_WIDTH

    encoded_id = urllib.parse.quote(video_id, safe="")
    # Both dimensions are positive here, so their greatest common divisor reduces the ratio
    divisor = math.gcd(width, height)
    aspect_ratio = f"{width // divisor}/{height // divisor}"
    lazy_attr = ' loading="lazy"' if load == LOAD_LAZY else ""
    watch_url = f"https://www.youtube.com/watch?v={encoded_id}"

    iframe_html = (
        f'<iframe src="https://www.youtube.com/embed/{encoded_id}"'
        f' class="youtube" height="{height}" width="{width}"'
        f' style="aspect-ratio: {aspect_ratio}" frameborder="0" allowfullscreen{lazy_attr}>\n'
        f'    <a href="{watch_url}"'
        f' target="_blank">View YouTube video</a>\n'
        f"</iframe>"
    )
    if load != LOAD_CLICK:
        return iframe_html
    return wrap_preview(
        embed="youtube",
        load=load,
        content=iframe_html,
        script_src=None,
        provider="YouTube video",
        action="Load video",
        link_href=watch_url,
        link_text="Watch on YouTube",
    )


def expand_source(text: str, options: Mapping[str, object] | None = None) -> str:
    """Expand standalone YouTube embed lines to iframe HTML in raw source.

    Used by the ``mw pre`` CLI stage. Unlike the preprocessor, this emits the
    HTML inline without any Python-Markdown stash placeholder.

    :param text: The source text.
    :param options: The youtube option table from config; its ``load`` picks the load mode.
    :returns: The text with standalone YouTube embeds replaced by iframe HTML.
    :raises OptionError: If ``load`` is not a supported value.
    """
    load = load_mode(options, LOAD_MODES)
    return map_lines(text, lambda line: [_render_match(line, load) or line])


class YouTubePreprocessor(Preprocessor):
    """Replace [youtube ...] lines with responsive iframe HTML.

    :param md: The Markdown instance.
    :param load: The validated load mode.
    """

    def __init__(self, md: Markdown, load: str) -> None:
        super().__init__(md)
        self.load = load

    def run(self, lines: list[str]) -> list[str]:
        """Process lines, replacing YouTube embed syntax with iframe HTML.

        :param lines: Source lines to process.
        :returns: Modified lines with YouTube embeds replaced by HTML.
        """
        output: list[str] = []
        for line in lines:
            iframe_html = _render_match(line, self.load)
            if iframe_html is not None:
                output.append(self.md.htmlStash.store(iframe_html))
            else:
                output.append(line)
        return output


class YouTubeExtension(Extension):
    """Python-Markdown extension for YouTube video embeds.

    :param \\*\\*kwargs: Configuration options passed to the extension.
    """

    def __init__(self, **kwargs: object) -> None:
        self.config: dict[str, list[object]] = {
            "load": [LOAD_EAGER, "Load mode: eager, lazy, or click"],
        }
        super().__init__(**kwargs)

    def extendMarkdown(self, md: Markdown) -> None:  # noqa: N802 - Python-Markdown's hook name
        """Register the YouTube preprocessor.

        :param md: The Markdown instance to extend.
        :raises OptionError: If the ``load`` config is not a supported value.
        """
        preprocessor = YouTubePreprocessor(md, load_mode(self.getConfigs(), LOAD_MODES))
        md.preprocessors.register(preprocessor, "do-youtube", 20)


def makeExtension(**kwargs: object) -> YouTubeExtension:  # noqa: N802 - Python-Markdown's loader name
    """Create and return the YouTubeExtension instance.

    :param \\*\\*kwargs: Configuration options.
    :returns: A configured YouTubeExtension.
    """
    return YouTubeExtension(**kwargs)
