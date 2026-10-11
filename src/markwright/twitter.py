# ABOUTME: Twitter embed extension for Python-Markdown.
# Converts [twitter URL flags...] syntax to Twitter blockquote embeds with script injection.

from __future__ import annotations

import html
import re
from collections.abc import Mapping

from markdown import Markdown
from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor
from markdown.preprocessors import Preprocessor

from markwright._embed_load import LOAD_CLICK, LOAD_EAGER, has_eager_embed, load_mode, wrap_preview
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

TWITTER_SCRIPT_SRC = "https://platform.twitter.com/widgets.js"
TWITTER_SCRIPT = f'<script async defer src="{TWITTER_SCRIPT_SRC}"></script>'

LOAD_MODES = (LOAD_EAGER, LOAD_CLICK)


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


def _render_match(line: str, load: str) -> str | None:
    """Build the Twitter embed HTML for a standalone embed line.

    :param line: A single source line.
    :param load: The load mode: ``eager`` or ``click``.
    :returns: The embed HTML (or its click-to-load preview) if the line is a Twitter embed, else ``None``.
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

    embed_html = (
        f'<div class="twitter"{align_attr}>\n'
        f'    <blockquote class="twitter-tweet" data-dnt="true"'
        f' data-width="{width}" data-theme="{theme}">\n'
        f'        <a href="{escaped_url}">View tweet by @{escaped_user}</a>\n'
        f"    </blockquote>\n"
        f"</div>"
    )
    if load != LOAD_CLICK:
        return embed_html
    return wrap_preview(
        embed="twitter",
        load=load,
        content=embed_html,
        script_src=TWITTER_SCRIPT_SRC,
        provider="X (Twitter) post",
        action="Load post",
        link_href=canonical_url,
        link_text="View on X",
    )


def expand_source(text: str, options: Mapping[str, object] | None = None) -> str:
    """Expand standalone Twitter embed lines to embed HTML in raw source.

    Used by the ``mw pre`` CLI stage. Unlike the preprocessor, this emits the
    HTML inline without any Python-Markdown stash placeholder.

    :param text: The source text.
    :param options: The twitter option table from config; its ``load`` picks the load mode.
    :returns: The text with standalone Twitter embeds replaced by HTML.
    :raises ValueError: If ``load`` is not a supported value.
    """
    load = load_mode(options, LOAD_MODES)
    return "\n".join(_render_match(line, load) or line for line in text.split("\n"))


def apply_html(
    rendered_html: str, warnings: list[str] | None = None, options: Mapping[str, object] | None = None
) -> str:
    """Inject the Twitter widgets script once if an eager Twitter embed is present.

    Used by the ``mw post`` CLI stage and the in-process postprocessor. The
    script is appended only when the Twitter class signature is present outside
    a click-to-load template and the script is not already injected, so the
    transform is idempotent.

    :param rendered_html: Rendered HTML content.
    :param warnings: Optional warnings list; unused (signature injection never warns).
    :param options: Ignored; accepted so the registry calls every post stage with one signature.
    :returns: HTML with the Twitter script appended if needed.
    """
    if has_eager_embed(rendered_html, TWITTER_SIGNATURE) and TWITTER_SCRIPT not in rendered_html:
        return rendered_html + "\n" + TWITTER_SCRIPT
    return rendered_html


class TwitterPreprocessor(Preprocessor):
    """Replace [twitter ...] lines with Twitter embed HTML.

    :param md: The Markdown instance.
    :param load: The validated load mode.
    """

    def __init__(self, md: Markdown, load: str) -> None:
        super().__init__(md)
        self.load = load

    def run(self, lines: list[str]) -> list[str]:
        """Process lines, replacing Twitter embed syntax with HTML.

        :param lines: Source lines to process.
        :returns: Modified lines with Twitter embeds replaced by HTML.
        """
        output: list[str] = []
        for line in lines:
            embed_html = _render_match(line, self.load)
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

    def __init__(self, **kwargs: object) -> None:
        self.config: dict[str, list[object]] = {
            "load": [LOAD_EAGER, "Load mode: eager or click"],
        }
        super().__init__(**kwargs)

    def extendMarkdown(self, md: Markdown) -> None:
        """Register the Twitter preprocessor and postprocessor.

        :param md: The Markdown instance to extend.
        :raises ValueError: If the ``load`` config is not a supported value.
        """
        preprocessor = TwitterPreprocessor(md, load_mode(self.getConfigs(), LOAD_MODES))
        postprocessor = TwitterPostprocessor(md)
        md.preprocessors.register(preprocessor, "do-twitter", 20)
        md.postprocessors.register(postprocessor, "do-twitter-script", 15)


def makeExtension(**kwargs: object) -> TwitterExtension:
    """Create and return the TwitterExtension instance.

    :param \\*\\*kwargs: Configuration options.
    :returns: A configured TwitterExtension.
    """
    return TwitterExtension(**kwargs)
