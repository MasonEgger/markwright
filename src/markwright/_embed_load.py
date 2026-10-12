# ABOUTME: The load option (eager, lazy, click) shared by the embeds that reach a third party.
# Validates the option and wraps live markup in the versioned click-to-load preview.

from __future__ import annotations

import html
from typing import TYPE_CHECKING

from markwright._diagnostics import OptionError

if TYPE_CHECKING:
    from collections.abc import Mapping

URL_SCHEME_WWW_PREFIX = r"(?:(?:https?:)?//)?(?:www\.)?"
"""Regex fragment matching an optional ``scheme://`` and an optional ``www.``.

Shared by the Twitter and Instagram embed grammars (upstream ``twitter.js`` and ``instagram.js``),
which both accept a URL prefix ranging from nothing (a bare path) up to a full ``https://www.<host>``.
"""

LOAD_EAGER = "eager"
LOAD_LAZY = "lazy"
LOAD_CLICK = "click"

# Version of the preview markup hosts code against; bump it on any breaking change to the contract.
PREVIEW_VERSION = 1


def load_mode(options: Mapping[str, object] | None, allowed: tuple[str, ...]) -> str:
    """Read and validate the ``load`` option from an embed's option table.

    :param options: The embed's option table (config table or extension configs), or ``None``.
    :param allowed: The load values this embed supports.
    :returns: The load value, ``"eager"`` when omitted or ``None``.
    :raises OptionError: If ``load`` is not one of ``allowed``.
    """
    load = (options or {}).get("load")
    if load is None:
        return LOAD_EAGER
    if not isinstance(load, str) or load not in allowed:
        raise OptionError(f"'load' must be one of {', '.join(allowed)}; got {load!r}")
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
