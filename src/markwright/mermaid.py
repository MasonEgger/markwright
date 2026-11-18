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

# A line holding only a deferred diagram's token: the in-process stage stashes the diagram later, below the
# whitespace normalizer, because the normalizer would strip a stash placeholder's markers
_PENDING_PREFIX = "mw-mermaid-pending-"
# Four columns is where a line is no longer top-level prose: it is a list item's or a block opener's body
_NESTED_INDENT = 4


def _expand_lines(lines: list[str], defer: Callable[[str], str] | None = None) -> list[str]:
    """Replace each closed mermaid fence with a raw ``<pre class="mermaid">`` block.

    The block is emitted inline as raw HTML, never stashed: the in-process preprocessor runs above
    Python-Markdown's whitespace normalizer, which would strip a stash placeholder's markers. A
    block under a list item or a block opener (indented four or more columns) is the exception when
    ``defer`` is given: Python-Markdown parses it as a paragraph there, so it is replaced by the
    placeholder line ``defer`` returns, and the block is stashed later.

    :param lines: Source lines.
    :param defer: Takes the ``<pre>`` block of a nested diagram and returns the line that stands in for it.
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
        pre_block = f'<pre class="{MERMAID_CLASS}">{escaped}</pre>'
        if defer is not None and len(block.indent) >= _NESTED_INDENT:
            result.append(f"{block.indent}{defer(pre_block)}")
        else:
            result.extend(f"{block.indent}{pre_line}" for pre_line in pre_block.split("\n"))
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
    """Replace mermaid fences with raw ``<pre>`` blocks ahead of superfences.

    :param md: The Markdown instance.
    :param pending: The nested diagrams this run defers, keyed by their placeholder token and shared with
        :class:`MermaidStashPreprocessor`.
    """

    def __init__(self, md: Markdown, pending: dict[str, str]) -> None:
        super().__init__(md)
        self.pending = pending

    def run(self, lines: list[str]) -> list[str]:
        """Process lines, replacing mermaid fences.

        :param lines: Source lines to process.
        :returns: Lines with mermaid fences replaced by raw HTML, or a placeholder line for a nested one.
        """
        self.pending.clear()

        def defer(pre_block: str) -> str:
            # A random token, so no line of the source can read as a placeholder
            token = f"{_PENDING_PREFIX}{uuid.uuid4().hex}"
            self.pending[token] = pre_block
            return token

        return _expand_lines(lines, defer)


class MermaidStashPreprocessor(Preprocessor):
    """Stash the nested diagrams :class:`MermaidPreprocessor` deferred, below the whitespace normalizer.

    A stashed block inside an admonition, details, tab, definition, footnote, or list body stays a block
    instead of being wrapped in a paragraph.

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
