# ABOUTME: Twitter embed extension for Python-Markdown.
# Converts [twitter URL flags...] syntax to Twitter blockquote embeds with script injection.

from __future__ import annotations

import html
import re

from markdown import Markdown
from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor
from markdown.preprocessors import Preprocessor

TWITTER_RE = re.compile(
    r"^\[twitter\s+(https?://(?:twitter\.com|x\.com)/(\S+)/status/(\S+))"
    r"((?:\s+(?:light|dark|left|center|right|\d+))*)\]$"
)

TWITTER_MIN_WIDTH = 250
TWITTER_MAX_WIDTH = 550
TWITTER_DEFAULT_WIDTH = 550

TWITTER_SCRIPT = '<script async defer src="https://platform.twitter.com/widgets.js"></script>'


def _parse_twitter_flags(raw_flags: str) -> dict[str, str | int]:
    """Parse space-separated Twitter flags into a settings dictionary.

    :param raw_flags: Raw space-separated flags string.
    :returns: Dictionary with theme, alignment, and width settings.
    """
    flags = raw_flags.split()

    theme = "dark" if "dark" in flags else "light"

    alignment = "center"
    for align_option in ("left", "right", "center"):
        if align_option in flags:
            alignment = align_option
            break

    width = TWITTER_DEFAULT_WIDTH
    for flag in flags:
        if flag.isdigit():
            width = max(TWITTER_MIN_WIDTH, min(TWITTER_MAX_WIDTH, int(flag)))
            break

    return {
        "theme": theme,
        "alignment": alignment,
        "width": width,
    }


class TwitterPreprocessor(Preprocessor):
    """Replace [twitter ...] lines with Twitter embed HTML.

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
        """Process lines, replacing Twitter embed syntax with HTML.

        :param lines: Source lines to process.
        :returns: Modified lines with Twitter embeds replaced by HTML.
        """
        self.found = False
        output: list[str] = []

        for line in lines:
            stripped_line = line.strip()
            twitter_match = TWITTER_RE.match(stripped_line)
            if twitter_match:
                self.found = True
                user = twitter_match.group(2)
                status_id = twitter_match.group(3)
                raw_flags = twitter_match.group(4).strip()
                settings = _parse_twitter_flags(raw_flags)

                # Canonicalize to twitter.com
                canonical_url = f"https://twitter.com/{user}/status/{status_id}"
                escaped_url = html.escape(canonical_url)
                escaped_user = html.escape(user)

                theme = settings["theme"]
                alignment = settings["alignment"]
                width = settings["width"]

                align_attr = f' align="{alignment}"' if alignment != "center" else ""

                embed_html = (
                    f'<div class="twitter"{align_attr}>\n'
                    f'    <blockquote class="twitter-tweet" data-dnt="true"'
                    f' data-width="{width}" data-theme="{theme}">\n'
                    f'        <a href="{escaped_url}">View tweet by @{escaped_user}</a>\n'
                    f"    </blockquote>\n"
                    f"</div>"
                )
                output.append(self.md.htmlStash.store(embed_html))
            else:
                output.append(line)

        return output


class TwitterPostprocessor(Postprocessor):
    """Append the Twitter widgets script tag once if any embeds were found.

    :param md: The Markdown instance.
    :param preprocessor: The TwitterPreprocessor to check for found embeds.
    """

    def __init__(self, md: Markdown, preprocessor: TwitterPreprocessor) -> None:
        """Initialize the postprocessor with a reference to the preprocessor.

        :param md: The Markdown instance.
        :param preprocessor: The TwitterPreprocessor to check for found embeds.
        """
        super().__init__(md)
        self.preprocessor = preprocessor

    def run(self, text: str) -> str:
        """Append script tag if Twitter embeds were found.

        :param text: Rendered HTML content.
        :returns: HTML with Twitter script appended if needed.
        """
        if self.preprocessor.found:
            return text + "\n" + TWITTER_SCRIPT
        return text


class TwitterExtension(Extension):
    """Python-Markdown extension for Twitter embeds.

    :param \\*\\*kwargs: Configuration options passed to the extension.
    """

    def extendMarkdown(self, md: Markdown) -> None:
        """Register the Twitter preprocessor and postprocessor.

        :param md: The Markdown instance to extend.
        """
        preprocessor = TwitterPreprocessor(md)
        postprocessor = TwitterPostprocessor(md, preprocessor)
        md.preprocessors.register(preprocessor, "do-twitter", 20)
        md.postprocessors.register(postprocessor, "do-twitter-script", 15)


def makeExtension(**kwargs: object) -> TwitterExtension:
    """Create and return the TwitterExtension instance.

    :param \\*\\*kwargs: Configuration options.
    :returns: A configured TwitterExtension.
    """
    return TwitterExtension(**kwargs)
