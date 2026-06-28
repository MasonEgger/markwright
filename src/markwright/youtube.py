# ABOUTME: YouTube embed extension for Python-Markdown.
# Converts [youtube ID height width] syntax to responsive iframe embeds.

from __future__ import annotations

import re
import urllib.parse

from markdown import Markdown
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor

from markwright._util import reduce_fraction

YOUTUBE_RE = re.compile(r"^\[youtube (\S+?)(?:\s+(\d+))?(?:\s+(\d+))?\]$")

DEFAULT_HEIGHT = 270
DEFAULT_WIDTH = 480


def _render_match(line: str) -> str | None:
    """Build the iframe HTML for a standalone YouTube embed line.

    :param line: A single source line.
    :returns: The iframe HTML if the line is a YouTube embed, else ``None``.
    """
    youtube_match = YOUTUBE_RE.match(line.strip())
    if not youtube_match:
        return None

    video_id = youtube_match.group(1)
    height = int(youtube_match.group(2)) if youtube_match.group(2) else DEFAULT_HEIGHT
    width = int(youtube_match.group(3)) if youtube_match.group(3) else DEFAULT_WIDTH

    encoded_id = urllib.parse.quote(video_id, safe="")
    aspect_width, aspect_height = reduce_fraction(width, height)
    aspect_ratio = f"{aspect_width}/{aspect_height}"

    return (
        f'<iframe src="https://www.youtube.com/embed/{encoded_id}"'
        f' class="youtube" height="{height}" width="{width}"'
        f' style="aspect-ratio: {aspect_ratio}" frameborder="0" allowfullscreen>\n'
        f'    <a href="https://www.youtube.com/watch?v={encoded_id}"'
        f' target="_blank">View YouTube video</a>\n'
        f"</iframe>"
    )


def expand_source(text: str) -> str:
    """Expand standalone YouTube embed lines to iframe HTML in raw source.

    Used by the ``mw pre`` CLI stage. Unlike the preprocessor, this emits the
    HTML inline without any Python-Markdown stash placeholder.

    :param text: The source text.
    :returns: The text with standalone YouTube embeds replaced by iframe HTML.
    """
    return "\n".join(_render_match(line) or line for line in text.split("\n"))


class YouTubePreprocessor(Preprocessor):
    """Replace [youtube ...] lines with responsive iframe HTML.

    :param md: The Markdown instance.
    """

    def run(self, lines: list[str]) -> list[str]:
        """Process lines, replacing YouTube embed syntax with iframe HTML.

        :param lines: Source lines to process.
        :returns: Modified lines with YouTube embeds replaced by HTML.
        """
        output: list[str] = []
        for line in lines:
            iframe_html = _render_match(line)
            if iframe_html is not None:
                output.append(self.md.htmlStash.store(iframe_html))
            else:
                output.append(line)
        return output


class YouTubeExtension(Extension):
    """Python-Markdown extension for YouTube video embeds.

    :param \\*\\*kwargs: Configuration options passed to the extension.
    """

    def extendMarkdown(self, md: Markdown) -> None:
        """Register the YouTube preprocessor.

        :param md: The Markdown instance to extend.
        """
        preprocessor = YouTubePreprocessor(md)
        md.preprocessors.register(preprocessor, "do-youtube", 20)


def makeExtension(**kwargs: object) -> YouTubeExtension:
    """Create and return the YouTubeExtension instance.

    :param \\*\\*kwargs: Configuration options.
    :returns: A configured YouTubeExtension.
    """
    return YouTubeExtension(**kwargs)
