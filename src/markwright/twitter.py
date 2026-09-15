# ABOUTME: Twitter embed extension for Python-Markdown.
# Converts [twitter URL flags...] syntax to Twitter blockquote embeds with script injection.

from __future__ import annotations

import html
import re

from markdown import Markdown
from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor
from markdown.preprocessors import Preprocessor

from markwright._util import URL_SCHEME_WWW_PREFIX

# Scheme, "www.", and the twitter.com/x.com host are all optional, and when
# present must be followed by a "/", so inputs from a bare "user/status/id"
# up to a full "https://www.twitter.com/user/status/id" all match. Ported
# verbatim from upstream twitter.js's URL-matching grammar.
TWITTER_RE = re.compile(
    r"^\[twitter\s+(?:(?:" + URL_SCHEME_WWW_PREFIX + r"(?:twitter|x)\.com)?/)?(\w+)/status/(\d+)"
    r"((?:\s+(?:light|dark|left|center|right|\d+))*)\]$"
)

TWITTER_MIN_WIDTH = 250
TWITTER_MAX_WIDTH = 550
TWITTER_DEFAULT_WIDTH = 550

TWITTER_SIGNATURE = 'class="twitter-tweet"'

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


def _render_match(line: str) -> str | None:
    """Build the Twitter embed HTML for a standalone embed line.

    :param line: A single source line.
    :returns: The embed HTML if the line is a Twitter embed, else ``None``.
    """
    twitter_match = TWITTER_RE.match(line.strip())
    if not twitter_match:
        return None

    user = twitter_match.group(1)
    status_id = twitter_match.group(2)
    raw_flags = twitter_match.group(3).strip()
    settings = _parse_twitter_flags(raw_flags)

    # Canonicalize to twitter.com
    canonical_url = f"https://twitter.com/{user}/status/{status_id}"
    escaped_url = html.escape(canonical_url)
    escaped_user = html.escape(user)

    theme = settings["theme"]
    alignment = settings["alignment"]
    width = settings["width"]

    align_attr = f' align="{alignment}"' if alignment != "center" else ""

    return (
        f'<div class="twitter"{align_attr}>\n'
        f'    <blockquote class="twitter-tweet" data-dnt="true"'
        f' data-width="{width}" data-theme="{theme}">\n'
        f'        <a href="{escaped_url}">View tweet by @{escaped_user}</a>\n'
        f"    </blockquote>\n"
        f"</div>"
    )


def expand_source(text: str) -> str:
    """Expand standalone Twitter embed lines to embed HTML in raw source.

    Used by the ``mw pre`` CLI stage. Unlike the preprocessor, this emits the
    HTML inline without any Python-Markdown stash placeholder.

    :param text: The source text.
    :returns: The text with standalone Twitter embeds replaced by HTML.
    """
    return "\n".join(_render_match(line) or line for line in text.split("\n"))


def apply_html(rendered_html: str, warnings: list[str] | None = None) -> str:
    """Inject the Twitter widgets script once if a Twitter embed is present.

    Used by the ``mw post`` CLI stage and the in-process postprocessor. The
    script is appended only when the Twitter class signature is present and the
    script is not already injected, so the transform is idempotent.

    :param rendered_html: Rendered HTML content.
    :param warnings: Optional warnings list; unused (signature injection never warns).
    :returns: HTML with the Twitter script appended if needed.
    """
    if TWITTER_SIGNATURE in rendered_html and TWITTER_SCRIPT not in rendered_html:
        return rendered_html + "\n" + TWITTER_SCRIPT
    return rendered_html


class TwitterPreprocessor(Preprocessor):
    """Replace [twitter ...] lines with Twitter embed HTML.

    :param md: The Markdown instance.
    """

    def run(self, lines: list[str]) -> list[str]:
        """Process lines, replacing Twitter embed syntax with HTML.

        :param lines: Source lines to process.
        :returns: Modified lines with Twitter embeds replaced by HTML.
        """
        output: list[str] = []
        for line in lines:
            embed_html = _render_match(line)
            if embed_html is not None:
                output.append(self.md.htmlStash.store(embed_html))
            else:
                output.append(line)
        return output


class TwitterPostprocessor(Postprocessor):
    """Append the Twitter widgets script tag once if any embeds are present.

    :param md: The Markdown instance.
    """

    def run(self, text: str) -> str:
        """Append the script tag if a Twitter embed signature is present.

        :param text: Rendered HTML content.
        :returns: HTML with Twitter script appended if needed.
        """
        return apply_html(text)


class TwitterExtension(Extension):
    """Python-Markdown extension for Twitter embeds.

    :param \\*\\*kwargs: Configuration options passed to the extension.
    """

    def extendMarkdown(self, md: Markdown) -> None:
        """Register the Twitter preprocessor and postprocessor.

        :param md: The Markdown instance to extend.
        """
        preprocessor = TwitterPreprocessor(md)
        postprocessor = TwitterPostprocessor(md)
        md.preprocessors.register(preprocessor, "do-twitter", 20)
        md.postprocessors.register(postprocessor, "do-twitter-script", 15)


def makeExtension(**kwargs: object) -> TwitterExtension:
    """Create and return the TwitterExtension instance.

    :param \\*\\*kwargs: Configuration options.
    :returns: A configured TwitterExtension.
    """
    return TwitterExtension(**kwargs)
