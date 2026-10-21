# ABOUTME: Icons extension resolving :pack-name: shortcodes to inline SVG from configured directories.
# markwright ships no icons; each pack is a prefix mapped to a directory of SVG files.

from __future__ import annotations

import re
import warnings

# Path is used only in a model field annotation, but pydantic resolves those at runtime, so it stays a runtime import
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING
from xml.etree import ElementTree

from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor
from pydantic import BaseModel, ConfigDict

from markwright._diagnostics import ConfigWarning, OptionError
from markwright._fences import map_prose

if TYPE_CHECKING:
    from collections.abc import Mapping

    from markdown import Markdown

ICON_CLASS = "mw-icon"

# The in-process default for packs, meaning "omitted". Python-Markdown runs a None default through
# parseBoolValue, which would turn a table into a bool, so a sentinel stands in.
_NO_PACKS = object()

# A pattern that can never match, used when no packs are configured
_NEVER_MATCHES = r"(?!)"


class IconOptions(BaseModel):
    """Validated icons options.

    :ivar packs: Shortcode prefix mapped to the directory holding that pack's SVG files.
    """

    model_config = ConfigDict(frozen=True)

    packs: dict[str, Path]


def read_options(options: Mapping[str, object] | None) -> IconOptions:
    """Read and validate an icons option table.

    Shared by the stage function, the in-process extension, and config validation, so every path
    applies the same rules. An omitted or ``None`` ``packs`` means no packs, silently, because the
    default all-on selection would otherwise warn for every user. An explicit empty table is a
    no-op and emits a :class:`ConfigWarning`.

    :param options: The icons option table (config table or extension configs), or ``None``.
    :returns: The validated options.
    :raises OptionError: If ``packs`` is not a table of strings, or a directory does not exist.
    """
    table = options or {}
    packs = table.get("packs")
    if packs is _NO_PACKS or packs is None:
        return IconOptions(packs={})

    if not isinstance(packs, dict) or not all(
        isinstance(prefix, str) and isinstance(directory, str) for prefix, directory in packs.items()
    ):
        raise OptionError("'packs' must be a table of pack name to directory")
    if not packs:
        warnings.warn(
            "icons 'packs' is empty, so every :pack-name: shortcode stays text; omit the key or name a pack",
            ConfigWarning,
            stacklevel=1,
        )

    pack_directories: dict[str, Path] = {}
    for prefix, directory in packs.items():
        directory_path = Path(directory)
        if not directory_path.is_dir():
            raise OptionError(f"'packs' directory for '{prefix}' not found: {directory}")
        pack_directories[prefix] = directory_path
    return IconOptions(packs=pack_directories)


def _shortcode_pattern(packs: Mapping[str, Path]) -> str:
    """Build the shortcode regex for the configured prefixes.

    :param packs: Pack prefix to directory.
    :returns: A pattern with the prefix in group 1 and the icon name in group 2, or one that
        matches nothing when there are no packs.
    """
    if not packs:
        return _NEVER_MATCHES
    prefixes = sorted(packs, key=len, reverse=True)
    alternatives = "|".join(re.escape(prefix) for prefix in prefixes)
    return rf":({alternatives})-([A-Za-z0-9_-]+):"


def _load_icon(packs: Mapping[str, Path], pack: str, name: str) -> str | None:
    """Find a pack's SVG by name and return it as a single line of markup.

    A nested file joins its path parts with ``-``, so ``arrows/up.svg`` is the name ``arrows-up``.
    Anything before the first ``<svg`` (an XML declaration or a license comment) is dropped.

    :param packs: Pack prefix to directory.
    :param pack: The pack prefix the shortcode named.
    :param name: The icon name after the prefix.
    :returns: The SVG markup on one line, or ``None`` when no file matches.
    """
    directory = packs[pack]
    for svg_file in sorted(directory.rglob("*.svg")):
        relative_parts = svg_file.relative_to(directory).with_suffix("").parts
        if "-".join(relative_parts) != name:
            continue
        text = svg_file.read_text(encoding="utf-8")
        svg_start = text.find("<svg")
        svg_text = text[svg_start:] if svg_start >= 0 else text
        return " ".join(line.strip() for line in svg_text.strip().splitlines())
    return None


def expand_source(text: str, options: Mapping[str, object] | None = None) -> str:
    """Replace ``:pack-name:`` shortcodes in prose with inline SVG.

    The source-stage transform for ``mw pre``. Fenced code blocks and inline code spans are
    skipped, and a shortcode with no matching icon is left as text.

    :param text: Raw Markdown source.
    :param options: The icons option table, or ``None`` for no packs.
    :returns: Source with each resolvable shortcode wrapped in an ``mw-icon`` span.
    """
    packs = read_options(options).packs
    pattern = re.compile(_shortcode_pattern(packs))

    def replace(shortcode_match: re.Match[str]) -> str:
        svg = _load_icon(packs, shortcode_match.group(1), shortcode_match.group(2))
        if svg is None:
            return shortcode_match.group(0)
        return f'<span aria-hidden="true" class="{ICON_CLASS}">{svg}</span>'

    return map_prose(text, lambda prose: pattern.sub(replace, prose))


class IconInlineProcessor(InlineProcessor):
    """Inline processor that turns a ``:pack-name:`` shortcode into an ``mw-icon`` span.

    :param pattern: The shortcode regex from :func:`_shortcode_pattern`.
    :param md: The Markdown instance.
    :param packs: Pack prefix to directory.
    """

    def __init__(self, pattern: str, md: Markdown, packs: Mapping[str, Path]) -> None:
        super().__init__(pattern, md)
        self.packs = packs

    # Python-Markdown names this hook, and its stubs type it as the older Pattern.handleMatch(m), so the
    # InlineProcessor signature it is called with at runtime needs the override ignore
    def handleMatch(  # type: ignore[override]  # noqa: N802
        self, match: re.Match[str], data: str
    ) -> tuple[ElementTree.Element | None, int | None, int | None]:
        """Create an ``mw-icon`` span holding the stashed SVG, or decline an unknown icon.

        :param match: The regex match object.
        :param data: The full source string being processed.
        :returns: A tuple of (element, start, end), or ``(None, None, None)`` when no icon matches.
        """
        svg = _load_icon(self.packs, match.group(1), match.group(2))
        if svg is None:
            return None, None, None
        icon_element = ElementTree.Element("span", {"class": ICON_CLASS, "aria-hidden": "true"})
        icon_element.text = self.md.htmlStash.store(svg)
        return icon_element, match.start(0), match.end(0)


class IconsExtension(Extension):
    """Python-Markdown extension for ``:pack-name:`` icon shortcodes.

    :param \\*\\*kwargs: Configuration options passed to the extension.
    """

    def __init__(self, **kwargs: object) -> None:
        self.config: dict[str, list[object]] = {
            "packs": [_NO_PACKS, "Pack prefix to SVG directory; omit for no packs, an empty table warns"],
        }
        super().__init__(**kwargs)

    def extendMarkdown(self, md: Markdown) -> None:  # noqa: N802 - Python-Markdown's hook name
        """Register the icon inline processor.

        Options are read here rather than at construction, so a ``setConfig`` call made
        after construction still applies.

        :param md: The Markdown instance to extend.
        :raises OptionError: If an option is invalid (see :func:`read_options`).
        """
        packs = read_options(self.getConfigs()).packs
        processor = IconInlineProcessor(_shortcode_pattern(packs), md, packs)
        md.inlinePatterns.register(processor, "mw-icons", 175)


def makeExtension(**kwargs: object) -> IconsExtension:  # noqa: N802 - Python-Markdown's loader name
    """Create and return the IconsExtension instance.

    :param \\*\\*kwargs: Configuration options.
    :returns: A configured IconsExtension.
    """
    return IconsExtension(**kwargs)
