# ABOUTME: CodePen embed extension for Python-Markdown.
# Converts [codepen USER HASH flags...] syntax to CodePen embed HTML with script injection.

from __future__ import annotations

import html
import re
import urllib.parse
from typing import TYPE_CHECKING

from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor
from markdown.preprocessors import Preprocessor
from pydantic import BaseModel, ConfigDict

from markwright._embed_load import LOAD_CLICK, LOAD_EAGER, load_mode, wrap_preview
from markwright._html import provider_script_needed

if TYPE_CHECKING:
    from collections.abc import Mapping

    from markdown import Markdown

CODEPEN_RE = re.compile(r"^\[codepen\s+(\S+)\s+(\S+)((?:\s+(?:lazy|light|dark|editable|html|css|js|result|\d+))*)\]$")

TAB_PRIORITY = ["html", "css", "js"]

DEFAULT_HEIGHT = 256

# The class every codepen embed element carries; an eager one needs the provider script
CODEPEN_EMBED_CLASS = "codepen"

CODEPEN_SCRIPT_SRC = "https://static.codepen.io/assets/embed/ei.js"
CODEPEN_SCRIPT = f'<script async defer src="{CODEPEN_SCRIPT_SRC}" type="text/javascript"></script>'

LOAD_MODES = (LOAD_EAGER, LOAD_CLICK)


class CodePenSettings(BaseModel):
    """Settings parsed from a CodePen embed line's flags.

    :ivar theme: ``light`` or ``dark``.
    :ivar height: Embed height in pixels.
    :ivar tab: Default tab, for example ``result`` or ``css,result``.
    :ivar lazy: Whether CodePen's own preview mode is on.
    :ivar editable: Whether the pen is editable.
    """

    model_config = ConfigDict(frozen=True)

    theme: str
    height: int
    tab: str
    lazy: bool
    editable: bool

    @classmethod
    def from_flags(cls, raw_flags: str) -> CodePenSettings:
        """Parse space-separated CodePen flags.

        :param raw_flags: Raw space-separated flags string.
        :returns: The parsed settings.
        """
        flags = raw_flags.split()

        # Theme: dark wins if both present
        theme = "dark" if "dark" in flags else "light"

        # Height: first integer found, or default
        height = DEFAULT_HEIGHT
        for flag in flags:
            if flag.isdigit():
                height = int(flag)
                break

        # Lazy and editable
        lazy = "lazy" in flags
        editable = "editable" in flags

        # Tab: priority is html > css > js; result can combine with another tab
        selected_tab = ""
        for tab_name in TAB_PRIORITY:
            if tab_name in flags:
                selected_tab = tab_name
                break

        has_result = "result" in flags

        if selected_tab and has_result:
            tab = f"{selected_tab},result"
        elif selected_tab:
            tab = selected_tab
        else:
            tab = "result"

        return cls(
            theme=theme,
            height=height,
            tab=tab,
            lazy=lazy,
            editable=editable,
        )


def _render_match(line: str, load: str) -> str | None:
    """Build the CodePen embed HTML for a standalone embed line.

    :param line: A single source line.
    :param load: The load mode: ``eager`` or ``click``.
    :returns: The embed HTML (or its click-to-load preview) if the line is a CodePen embed, else ``None``.
    """
    codepen_match = CODEPEN_RE.match(line.strip())
    if not codepen_match:
        return None

    user = codepen_match.group(1)
    hash_id = codepen_match.group(2)
    raw_flags = codepen_match.group(3).strip()
    settings = CodePenSettings.from_flags(raw_flags)

    escaped_user = html.escape(user)
    escaped_hash = html.escape(hash_id)
    encoded_user = urllib.parse.quote(user, safe="")
    encoded_hash = urllib.parse.quote(hash_id, safe="")
    height = settings.height
    theme = settings.theme
    tab = settings.tab

    lazy_attr = ' data-preview="true"' if settings.lazy else ""
    editable_attr = ' data-editable="true"' if settings.editable else ""
    pen_url = f"https://codepen.io/{encoded_user}/pen/{encoded_hash}"

    embed_html = (
        f'<p class="codepen" data-height="{height}"'
        f' data-theme-id="{theme}" data-default-tab="{tab}"'
        f' data-user="{escaped_user}" data-slug-hash="{escaped_hash}"'
        f"{lazy_attr}{editable_attr}"
        f' style="height: {height}px; box-sizing: border-box;'
        f" display: flex; align-items: center; justify-content: center;"
        f' border: 2px solid; margin: 1em 0; padding: 1em;">\n'
        f"    <span>See the Pen"
        f' <a href="{pen_url}">'
        f"{escaped_hash} by {escaped_user}</a>"
        f' (<a href="https://codepen.io/{encoded_user}">@{escaped_user}</a>)'
        f" on <a href='https://codepen.io'>CodePen</a>.</span>\n"
        f"</p>"
    )
    if load != LOAD_CLICK:
        return embed_html
    return wrap_preview(
        embed="codepen",
        load=load,
        content=embed_html,
        script_src=CODEPEN_SCRIPT_SRC,
        provider="CodePen",
        action="Load pen",
        link_href=pen_url,
        link_text="View on CodePen",
    )


def expand_source(text: str, options: Mapping[str, object] | None = None) -> str:
    """Expand standalone CodePen embed lines to embed HTML in raw source.

    Used by the ``mw pre`` CLI stage. Unlike the preprocessor, this emits the
    HTML inline without any Python-Markdown stash placeholder.

    :param text: The source text.
    :param options: The codepen option table from config; its ``load`` picks the load mode.
    :returns: The text with standalone CodePen embeds replaced by HTML.
    :raises OptionError: If ``load`` is not a supported value.
    """
    load = load_mode(options, LOAD_MODES)
    return "\n".join(_render_match(line, load) or line for line in text.split("\n"))


def apply_html(
    rendered_html: str, skip_reasons: list[str] | None = None, options: Mapping[str, object] | None = None
) -> str:
    """Inject the CodePen embed script once if an eager CodePen embed is present.

    Used by the ``mw post`` CLI stage and the in-process postprocessor. The
    script is appended only when an embed element sits outside every ``<template>``
    (an eager embed) and no ``<script>`` already loads the provider, so the transform
    is idempotent.

    :param rendered_html: Rendered HTML content.
    :param skip_reasons: Ignored (script injection never skips anything); accepted so the registry calls
        every post stage with one signature.
    :param options: Ignored; accepted so the registry calls every post stage with one signature.
    :returns: HTML with the CodePen script appended if needed.
    """
    if provider_script_needed(rendered_html, CODEPEN_EMBED_CLASS, CODEPEN_SCRIPT_SRC):
        return rendered_html + "\n" + CODEPEN_SCRIPT
    return rendered_html


class CodePenPreprocessor(Preprocessor):
    """Replace [codepen ...] lines with CodePen embed HTML.

    :param md: The Markdown instance.
    :param load: The validated load mode.
    """

    def __init__(self, md: Markdown, load: str) -> None:
        super().__init__(md)
        self.load = load

    def run(self, lines: list[str]) -> list[str]:
        """Process lines, replacing CodePen embed syntax with HTML.

        :param lines: Source lines to process.
        :returns: Modified lines with CodePen embeds replaced by HTML.
        """
        output: list[str] = []
        for line in lines:
            embed_html = _render_match(line, self.load)
            if embed_html is not None:
                output.append(self.md.htmlStash.store(embed_html))
            else:
                output.append(line)
        return output


class CodePenPostprocessor(Postprocessor):
    """Append the CodePen embed script tag once if any embeds are present.

    :param md: The Markdown instance.
    """

    def run(self, text: str) -> str:
        """Append the script tag if a CodePen embed signature is present.

        :param text: Rendered HTML content.
        :returns: HTML with CodePen script appended if needed.
        """
        return apply_html(text)


class CodePenExtension(Extension):
    """Python-Markdown extension for CodePen embeds.

    :param \\*\\*kwargs: Configuration options passed to the extension.
    """

    def __init__(self, **kwargs: object) -> None:
        self.config: dict[str, list[object]] = {
            "load": [LOAD_EAGER, "Load mode: eager or click"],
        }
        super().__init__(**kwargs)

    def extendMarkdown(self, md: Markdown) -> None:  # noqa: N802 - Python-Markdown's hook name
        """Register the CodePen preprocessor and postprocessor.

        :param md: The Markdown instance to extend.
        :raises OptionError: If the ``load`` config is not a supported value.
        """
        preprocessor = CodePenPreprocessor(md, load_mode(self.getConfigs(), LOAD_MODES))
        postprocessor = CodePenPostprocessor(md)
        md.preprocessors.register(preprocessor, "do-codepen", 20)
        md.postprocessors.register(postprocessor, "do-codepen-script", 15)


def makeExtension(**kwargs: object) -> CodePenExtension:  # noqa: N802 - Python-Markdown's loader name
    """Create and return the CodePenExtension instance.

    :param \\*\\*kwargs: Configuration options.
    :returns: A configured CodePenExtension.
    """
    return CodePenExtension(**kwargs)
