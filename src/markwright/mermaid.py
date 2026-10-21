# ABOUTME: Mermaid fence extension for Python-Markdown.
# Converts ```mermaid fenced blocks to <pre class="mermaid"> blocks that a host script renders.

from __future__ import annotations

import html
from typing import TYPE_CHECKING

from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor

from markwright._fences import find_fenced_blocks

if TYPE_CHECKING:
    from collections.abc import Mapping

    from markdown import Markdown

MERMAID_CLASS = "mermaid"


def _expand_lines(lines: list[str]) -> list[str]:
    """Replace each closed mermaid fence with a raw ``<pre class="mermaid">`` block.

    The block is emitted inline as raw HTML, never stashed: the in-process preprocessor runs above
    Python-Markdown's whitespace normalizer, which would strip a stash placeholder's markers.

    :param lines: Source lines.
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
    """

    def run(self, lines: list[str]) -> list[str]:
        """Process lines, replacing mermaid fences.

        :param lines: Source lines to process.
        :returns: Lines with mermaid fences replaced by raw HTML.
        """
        return _expand_lines(lines)


class MermaidExtension(Extension):
    """Python-Markdown extension for mermaid diagrams.

    :param \\*\\*kwargs: Configuration options passed to the extension.
    """

    def extendMarkdown(self, md: Markdown) -> None:  # noqa: N802 - Python-Markdown's hook name
        """Register the mermaid preprocessor ahead of superfences and the fence preprocessor.

        :param md: The Markdown instance to extend.
        """
        md.preprocessors.register(MermaidPreprocessor(md), "mw-mermaid", 45)


def makeExtension(**kwargs: object) -> MermaidExtension:  # noqa: N802 - Python-Markdown's loader name
    """Create and return the MermaidExtension instance.

    :param \\*\\*kwargs: Configuration options.
    :returns: A configured MermaidExtension.
    """
    return MermaidExtension(**kwargs)
