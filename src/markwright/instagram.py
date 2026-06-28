# ABOUTME: Instagram embed extension for Python-Markdown.
# Converts [instagram URL flags...] syntax to Instagram blockquote embeds with script injection.

from __future__ import annotations

import html
import re

from markdown import Markdown
from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor
from markdown.preprocessors import Preprocessor

INSTAGRAM_RE = re.compile(
    r"^\[instagram\s+(https?://(?:www\.)?instagram\.com/p/\S+)"
    r"((?:\s+(?:caption|left|center|right|\d+))*)\]$"
)

INSTAGRAM_MIN_WIDTH = 326
INSTAGRAM_MAX_WIDTH = 550

INSTAGRAM_SCRIPT = (
    '<script async defer src="https://www.instagram.com/embed.js"'
    ' onload="window.instgrm && window.instgrm.Embeds.process()"></script>'
)


def _parse_instagram_flags(raw_flags: str) -> dict[str, str | int | bool]:
    """Parse space-separated Instagram flags into a settings dictionary.

    :param raw_flags: Raw space-separated flags string.
    :returns: Dictionary with caption, alignment, and width settings.
    """
    flags = raw_flags.split()

    caption = "caption" in flags

    alignment = "center"
    for align_option in ("left", "right", "center"):
        if align_option in flags:
            alignment = align_option
            break

    width = 0
    for flag in flags:
        if flag.isdigit():
            parsed_width = int(flag)
            width = max(INSTAGRAM_MIN_WIDTH, min(INSTAGRAM_MAX_WIDTH, parsed_width))
            break

    return {
        "caption": caption,
        "alignment": alignment,
        "width": width,
    }


class InstagramPreprocessor(Preprocessor):
    """Replace [instagram ...] lines with Instagram embed HTML.

    :param md: The Markdown instance.
    """

    found: bool

    def __init__(self, md: Markdown) -> None:
        """Initialize the preprocessor.

        :param md: The Markdown instance.
        """
        super().__init__(md)
        self.found = False

    def run(self, lines: list[str]) -> list[str]:
        """Process lines, replacing Instagram embed syntax with HTML.

        :param lines: Source lines to process.
        :returns: Modified lines with Instagram embeds replaced by HTML.
        """
        self.found = False
        output: list[str] = []

        for line in lines:
            stripped_line = line.strip()
            instagram_match = INSTAGRAM_RE.match(stripped_line)
            if instagram_match:
                self.found = True
                url = instagram_match.group(1)
                raw_flags = instagram_match.group(2).strip()
                settings = _parse_instagram_flags(raw_flags)

                escaped_url = html.escape(url)

                alignment = settings["alignment"]
                width = int(settings["width"])
                caption = settings["caption"]

                align_attr = f' align="{alignment}"' if alignment != "center" else ""
                caption_attr = " data-instgrm-captioned" if caption else ""
                width_style = f' style="width: {width}px;"' if width > 0 else ""

                embed_html = (
                    f'<div class="instagram"{align_attr}>\n'
                    f'    <blockquote class="instagram-media"'
                    f' data-instgrm-permalink="{escaped_url}"'
                    f' data-instgrm-version="14"{caption_attr}{width_style}>\n'
                    f'        <a href="{escaped_url}">View post</a>\n'
                    f"    </blockquote>\n"
                    f"</div>"
                )
                output.append(self.md.htmlStash.store(embed_html))
            else:
                output.append(line)

        return output


class InstagramPostprocessor(Postprocessor):
    """Append the Instagram embed script tag once if any embeds were found.

    :param md: The Markdown instance.
    :param preprocessor: The InstagramPreprocessor to check for found embeds.
    """

    def __init__(self, md: Markdown, preprocessor: InstagramPreprocessor) -> None:
        """Initialize the postprocessor with a reference to the preprocessor.

        :param md: The Markdown instance.
        :param preprocessor: The InstagramPreprocessor to check for found embeds.
        """
        super().__init__(md)
        self.preprocessor = preprocessor

    def run(self, text: str) -> str:
        """Append script tag if Instagram embeds were found.

        :param text: Rendered HTML content.
        :returns: HTML with Instagram script appended if needed.
        """
        if self.preprocessor.found:
            return text + "\n" + INSTAGRAM_SCRIPT
        return text


class InstagramExtension(Extension):
    """Python-Markdown extension for Instagram embeds.

    :param \\*\\*kwargs: Configuration options passed to the extension.
    """

    def extendMarkdown(self, md: Markdown) -> None:
        """Register the Instagram preprocessor and postprocessor.

        :param md: The Markdown instance to extend.
        """
        preprocessor = InstagramPreprocessor(md)
        postprocessor = InstagramPostprocessor(md, preprocessor)
        md.preprocessors.register(preprocessor, "do-instagram", 20)
        md.postprocessors.register(postprocessor, "do-instagram-script", 15)


def makeExtension(**kwargs: object) -> InstagramExtension:
    """Create and return the InstagramExtension instance.

    :param \\*\\*kwargs: Configuration options.
    :returns: A configured InstagramExtension.
    """
    return InstagramExtension(**kwargs)
