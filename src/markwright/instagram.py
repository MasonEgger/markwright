# ABOUTME: Instagram embed extension for Python-Markdown.
# Converts [instagram URL flags...] syntax to Instagram blockquote embeds with script injection.

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

# Scheme, "www.", the instagram.com host, and a "p/"-style path segment are
# all optional, so inputs from a bare shortcode up to a full
# "https://www.instagram.com/p/<shortcode>" all match. Ported verbatim from
# upstream instagram.js's URL-matching grammar.
INSTAGRAM_RE = re.compile(
    r"^\[instagram\s+(?:(?:" + URL_SCHEME_WWW_PREFIX + r"instagram\.com)?/)?(?:\w+/)?(\w+)"
    r"((?:\s+(?:caption|left|center|right|\d+))*)\]$"
)

INSTAGRAM_PERMALINK_TEMPLATE = "https://www.instagram.com/p/{post_id}"
INSTAGRAM_HREF_TEMPLATE = "https://instagram.com/p/{post_id}"

INSTAGRAM_MIN_WIDTH = 326
INSTAGRAM_MAX_WIDTH = 550

INSTAGRAM_SIGNATURE = 'class="instagram-media"'

INSTAGRAM_SCRIPT_SRC = "https://www.instagram.com/embed.js"
INSTAGRAM_SCRIPT = (
    f'<script async defer src="{INSTAGRAM_SCRIPT_SRC}"'
    ' onload="window.instgrm && window.instgrm.Embeds.process()"></script>'
)

LOAD_MODES = (LOAD_EAGER, LOAD_CLICK)


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


def _render_match(line: str, load: str) -> str | None:
    """Build the Instagram embed HTML for a standalone embed line.

    :param line: A single source line.
    :param load: The load mode: ``eager`` or ``click``.
    :returns: The embed HTML (or its click-to-load preview) if the line is an Instagram embed, else ``None``.
    """
    instagram_match = INSTAGRAM_RE.match(line.strip())
    if not instagram_match:
        return None

    post_id = instagram_match.group(1)
    raw_flags = instagram_match.group(2).strip()
    settings = _parse_instagram_flags(raw_flags)

    escaped_href = html.escape(INSTAGRAM_HREF_TEMPLATE.format(post_id=post_id))
    permalink = INSTAGRAM_PERMALINK_TEMPLATE.format(post_id=post_id)
    escaped_permalink = html.escape(permalink)

    alignment = settings["alignment"]
    width = int(settings["width"])
    caption = settings["caption"]

    align_attr = f' align="{alignment}"' if alignment != "center" else ""
    caption_attr = " data-instgrm-captioned" if caption else ""
    width_style = f' style="width: {width}px;"' if width > 0 else ""

    embed_html = (
        f'<div class="instagram"{align_attr}>\n'
        f'    <blockquote class="instagram-media"'
        f' data-instgrm-permalink="{escaped_permalink}"'
        f' data-instgrm-version="14"{caption_attr}{width_style}>\n'
        f'        <a href="{escaped_href}">View post</a>\n'
        f"    </blockquote>\n"
        f"</div>"
    )
    if load != LOAD_CLICK:
        return embed_html
    return wrap_preview(
        embed="instagram",
        load=load,
        content=embed_html,
        script_src=INSTAGRAM_SCRIPT_SRC,
        provider="Instagram post",
        action="Load post",
        link_href=permalink,
        link_text="View on Instagram",
    )


def expand_source(text: str, options: Mapping[str, object] | None = None) -> str:
    """Expand standalone Instagram embed lines to embed HTML in raw source.

    Used by the ``mw pre`` CLI stage. Unlike the preprocessor, this emits the
    HTML inline without any Python-Markdown stash placeholder.

    :param text: The source text.
    :param options: The instagram option table from config; its ``load`` picks the load mode.
    :returns: The text with standalone Instagram embeds replaced by HTML.
    :raises ValueError: If ``load`` is not a supported value.
    """
    load = load_mode(options, LOAD_MODES)
    return "\n".join(_render_match(line, load) or line for line in text.split("\n"))


def apply_html(
    rendered_html: str, warnings: list[str] | None = None, options: Mapping[str, object] | None = None
) -> str:
    """Inject the Instagram embed script once if an eager Instagram embed is present.

    Used by the ``mw post`` CLI stage and the in-process postprocessor. The
    script is appended only when the Instagram class signature is present outside
    a click-to-load template and the script is not already injected, so the
    transform is idempotent.

    :param rendered_html: Rendered HTML content.
    :param warnings: Optional warnings list; unused (signature injection never warns).
    :param options: Ignored; accepted so the registry calls every post stage with one signature.
    :returns: HTML with the Instagram script appended if needed.
    """
    if has_eager_embed(rendered_html, INSTAGRAM_SIGNATURE) and INSTAGRAM_SCRIPT not in rendered_html:
        return rendered_html + "\n" + INSTAGRAM_SCRIPT
    return rendered_html


class InstagramPreprocessor(Preprocessor):
    """Replace [instagram ...] lines with Instagram embed HTML.

    :param md: The Markdown instance.
    :param load: The validated load mode.
    """

    def __init__(self, md: Markdown, load: str) -> None:
        super().__init__(md)
        self.load = load

    def run(self, lines: list[str]) -> list[str]:
        """Process lines, replacing Instagram embed syntax with HTML.

        :param lines: Source lines to process.
        :returns: Modified lines with Instagram embeds replaced by HTML.
        """
        output: list[str] = []
        for line in lines:
            embed_html = _render_match(line, self.load)
            if embed_html is not None:
                output.append(self.md.htmlStash.store(embed_html))
            else:
                output.append(line)
        return output


class InstagramPostprocessor(Postprocessor):
    """Append the Instagram embed script tag once if any embeds are present.

    :param md: The Markdown instance.
    """

    def run(self, text: str) -> str:
        """Append the script tag if an Instagram embed signature is present.

        :param text: Rendered HTML content.
        :returns: HTML with Instagram script appended if needed.
        """
        return apply_html(text)


class InstagramExtension(Extension):
    """Python-Markdown extension for Instagram embeds.

    :param \\*\\*kwargs: Configuration options passed to the extension.
    """

    def __init__(self, **kwargs: object) -> None:
        self.config: dict[str, list[object]] = {
            "load": [LOAD_EAGER, "Load mode: eager or click"],
        }
        super().__init__(**kwargs)

    def extendMarkdown(self, md: Markdown) -> None:
        """Register the Instagram preprocessor and postprocessor.

        :param md: The Markdown instance to extend.
        :raises ValueError: If the ``load`` config is not a supported value.
        """
        preprocessor = InstagramPreprocessor(md, load_mode(self.getConfigs(), LOAD_MODES))
        postprocessor = InstagramPostprocessor(md)
        md.preprocessors.register(preprocessor, "do-instagram", 20)
        md.postprocessors.register(postprocessor, "do-instagram-script", 15)


def makeExtension(**kwargs: object) -> InstagramExtension:
    """Create and return the InstagramExtension instance.

    :param \\*\\*kwargs: Configuration options.
    :returns: A configured InstagramExtension.
    """
    return InstagramExtension(**kwargs)
