# ABOUTME: The load option (eager, lazy, click) shared by the embeds that reach a third party.
# Validates the option, wraps live markup in the versioned click-to-load preview, and finds eager embeds.

from __future__ import annotations

import html
import re
from collections.abc import Mapping

LOAD_EAGER = "eager"
LOAD_LAZY = "lazy"
LOAD_CLICK = "click"

# Version of the preview markup hosts code against; bump it on any breaking change to the contract.
PREVIEW_VERSION = 1

# The <template> wrapper holding live markup. Signatures inside it belong to deferred embeds.
_DEFERRED_CONTENT_RE = re.compile(r'<template class="mw-embed-content">.*?</template>', re.DOTALL)


def load_mode(options: Mapping[str, object] | None, allowed: tuple[str, ...]) -> str:
    """Read and validate the ``load`` option from an embed's option table.

    :param options: The embed's option table (config table or extension configs), or ``None``.
    :param allowed: The load values this embed supports.
    :returns: The load value, ``"eager"`` when omitted or ``None``.
    :raises ValueError: If ``load`` is not one of ``allowed``.
    """
    load = (options or {}).get("load")
    if load is None:
        return LOAD_EAGER
    if not isinstance(load, str) or load not in allowed:
        raise ValueError(f"'load' must be one of {', '.join(allowed)}; got {load!r}")
    return load


def wrap_preview(
    *,
    embed: str,
    load: str,
    content: str,
    script_src: str | None,
    provider: str,
    action: str,
    link_href: str,
    link_text: str,
) -> str:
    """Wrap an embed's live markup in the click-to-load preview.

    The live markup goes inside a ``<template>``, which browsers parse but never render or
    fetch from, so nothing loads until a host script clones it into the page.

    :param embed: The extension name, for ``data-mw-embed``.
    :param load: The load value, for ``data-mw-load``.
    :param content: The embed's eager markup, without any provider ``<script>``.
    :param script_src: The provider script a host injects after cloning, or ``None``.
    :param provider: Text naming what the embed is, for example ``"YouTube video"``.
    :param action: The load button text, for example ``"Load video"``.
    :param link_href: Direct URL of the original content, unescaped.
    :param link_text: The direct link text.
    :returns: The preview HTML.
    """
    script_attr = f' data-mw-script="{html.escape(script_src)}"' if script_src is not None else ""
    return (
        f'<div class="mw-embed" data-mw-version="{PREVIEW_VERSION}" data-mw-embed="{embed}"'
        f' data-mw-load="{load}"{script_attr}>\n'
        f'    <template class="mw-embed-content">{content}</template>\n'
        f'    <div class="mw-embed-preview">\n'
        f'        <p class="mw-embed-provider">{provider}</p>\n'
        f'        <button type="button" class="mw-embed-load">{action}</button>\n'
        f'        <a class="mw-embed-link" href="{html.escape(link_href)}">{link_text}</a>\n'
        f"    </div>\n"
        f"</div>"
    )


def has_eager_embed(rendered_html: str, signature: str) -> bool:
    """Report whether an embed signature appears outside every deferred-content template.

    :param rendered_html: Rendered HTML content.
    :param signature: The embed's class signature, for example ``'class="twitter-tweet"'``.
    :returns: ``True`` if at least one embed on the page loads eagerly.
    """
    return signature in _DEFERRED_CONTENT_RE.sub("", rendered_html)
