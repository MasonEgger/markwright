# ABOUTME: Mermaid fence extension for Python-Markdown.
# Converts ```mermaid fenced blocks to <pre class="mermaid"> blocks that a host script renders.

from __future__ import annotations

import html
import uuid
from typing import TYPE_CHECKING

from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor

from markwright._fences import find_fenced_blocks

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from markdown import Markdown

MERMAID_CLASS = "mermaid"
# The open tag of an emitted diagram. The icons stage reads it back to leave the diagram text alone.
PRE_OPEN = f'<pre class="{MERMAID_CLASS}">'

# A line holding only a deferred diagram's token: the in-process stage stashes that diagram later, below the
# whitespace normalizer, which would strip a stash placeholder's markers
_PENDING_PREFIX = "mw-mermaid-pending-"
# Four columns is where a line is no longer top-level prose: _fences reads a fence that deep as one under a list
# marker line or in a block opener's body, and in a list item's or an opener's body Python-Markdown does not read
# a raw <pre> as an HTML block
_NESTED_INDENT = 4


def _expand_lines(lines: list[str], defer: Callable[[str], str] | None = None) -> list[str]:
    """Replace each closed mermaid fence with a raw ``<pre class="mermaid">`` block.

    In ``mw pre`` (no ``defer``) the block is emitted inline as raw HTML, every line of it at the fence's
    indentation. An indented fence leaves that indentation inside the ``<pre>`` on each line after the first,
    unless the renderer strips it as the indent of the list item or block around the fence. A blank diagram
    line stays empty, because a CommonMark renderer keeps the spaces of a whitespace-only line inside the
    ``<pre>``.

    In-process (``defer`` given), a fence indented four or more columns, which ``_fences`` reads as a fence
    under a list marker line or in a block opener's body, is replaced by the one placeholder line ``defer``
    returns, at the fence's indentation, and stashed later: raw lines left that deep in a list item's or an
    opener's body would be wrapped in a paragraph or split at a blank line, and the preprocessor runs above
    Python-Markdown's whitespace normalizer, which would strip a stash placeholder's markers. spec.md's
    Mermaid entry lists the marker lines a renderer reads otherwise (``* * *``), where the stashed block lands
    in a code block. Any other fence, one under a list item included, is emitted inline as in ``mw pre``, so
    Python-Markdown reads the same raw HTML block in both.

    :param lines: Source lines.
    :param defer: Takes the ``<pre>`` block of a diagram and returns the line that stands in for it.
    :returns: The lines with mermaid fences replaced; other lines pass through.
    """
    result: list[str] = []
    next_line = 0
    for block in find_fenced_blocks(lines):
        if block.info.strip() != MERMAID_CLASS:
            continue

        result.extend(lines[next_line : block.opening])
        # CommonMark removes up to the fence's indentation from each content line
        diagram_lines: list[str] = []
        for line in lines[block.opening + 1 : block.closing]:
            leading_spaces = len(line) - len(line.lstrip(" "))
            strip_width = min(len(block.indent), leading_spaces)
            diagram_lines.append(line[strip_width:])
        escaped = html.escape("\n".join(diagram_lines) + "\n", quote=False)
        pre_block = f"{PRE_OPEN}{escaped}</pre>"
        if defer is not None and len(block.indent) >= _NESTED_INDENT:
            result.append(f"{block.indent}{defer(pre_block)}")
        else:
            # A blank diagram line stays empty: a CommonMark renderer keeps a whitespace-only line's spaces
            result.extend(f"{block.indent}{pre_line}" if pre_line else "" for pre_line in pre_block.split("\n"))
        next_line = block.closing + 1

    result.extend(lines[next_line:])
    return result


def expand_source(text: str, options: Mapping[str, object] | None = None) -> str:
    """Convert mermaid fences to raw ``<pre class="mermaid">`` blocks in raw source.

    Used by the ``mw pre`` CLI stage.

    :param text: The source text.
    :param options: Ignored; accepted so the registry calls every pre stage with one signature.
    :returns: The text with mermaid fences replaced.
    """
    return "\n".join(_expand_lines(text.split("\n")))


class MermaidPreprocessor(Preprocessor):
    """Replace each mermaid fence with a raw ``<pre>`` block, or with a placeholder line, ahead of superfences.

    A fence indented four or more columns gets the placeholder line.

    :param md: The Markdown instance.
    :param pending: The diagrams this run defers, keyed by their placeholder token and shared with
        :class:`MermaidStashPreprocessor`.
    """

    def __init__(self, md: Markdown, pending: dict[str, str]) -> None:
        super().__init__(md)
        self.pending = pending

    def run(self, lines: list[str]) -> list[str]:
        """Process lines, replacing mermaid fences.

        :param lines: Source lines to process.
        :returns: Lines with each mermaid fence replaced by raw HTML, or by a placeholder line when the
            fence is indented four or more columns.
        """
        self.pending.clear()

        def defer(pre_block: str) -> str:
            # A random token, so no line of the source can read as a placeholder
            token = f"{_PENDING_PREFIX}{uuid.uuid4().hex}"
            self.pending[token] = pre_block
            return token

        return _expand_lines(lines, defer)


class MermaidStashPreprocessor(Preprocessor):
    """Stash the diagrams :class:`MermaidPreprocessor` deferred, below the whitespace normalizer.

    A stashed block in an admonition, details, tab, definition, footnote, or list body stays one ``<pre>``,
    with or without a blank line in the diagram or a text line beside it.

    :param md: The Markdown instance.
    :param pending: The deferred ``<pre>`` blocks, keyed by the token of the placeholder line that stands in for each.
    """

    def __init__(self, md: Markdown, pending: dict[str, str]) -> None:
        super().__init__(md)
        self.pending = pending

    def run(self, lines: list[str]) -> list[str]:
        """Replace each placeholder line with a stash placeholder at the same indentation.

        :param lines: Source lines to process.
        :returns: The lines with every deferred diagram stashed.
        """
        result: list[str] = []
        for line in lines:
            token = line.strip()
            if token in self.pending:
                stash_key = self.md.htmlStash.store(self.pending[token])
                result.append(f"{line[: len(line) - len(line.lstrip())]}{stash_key}")
            else:
                result.append(line)
        return result


class MermaidExtension(Extension):
    """Python-Markdown extension for mermaid diagrams.

    :param \\*\\*kwargs: Configuration options passed to the extension.
    """

    def extendMarkdown(self, md: Markdown) -> None:  # noqa: N802 - Python-Markdown's hook name
        """Register the mermaid preprocessor ahead of superfences and the fence preprocessor.

        A second preprocessor, below the whitespace normalizer (30) and above ``html_block`` (20), stashes the
        diagrams the first one deferred. It runs at 26, not at superfences' 25, so its order against
        superfences does not depend on the host's extension order.

        :param md: The Markdown instance to extend.
        """
        pending: dict[str, str] = {}
        md.preprocessors.register(MermaidPreprocessor(md, pending), "mw-mermaid", 45)
        md.preprocessors.register(MermaidStashPreprocessor(md, pending), "mw-mermaid-stash", 26)


def makeExtension(**kwargs: object) -> MermaidExtension:  # noqa: N802 - Python-Markdown's loader name
    """Create and return the MermaidExtension instance.

    :param \\*\\*kwargs: Configuration options.
    :returns: A configured MermaidExtension.
    """
    return MermaidExtension(**kwargs)
