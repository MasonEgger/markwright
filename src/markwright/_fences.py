# ABOUTME: Shared scanner for fenced code blocks in Markdown source, following CommonMark's fence rules.
# Used by the fence, mermaid, highlight, and icons pre stages and, through map_lines, every directive-line stage.

from __future__ import annotations

import itertools
import re
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

# Python-Markdown expands a tab to four columns, so every pattern below runs on tab-expanded text.
_TAB_WIDTH = 4

# An opening fence: indentation, then three or more backticks or tildes, then the info string
_FENCE_OPEN_RE = re.compile(r"^(?P<indent>[ ]*)(?P<marker>`{3,}|~{3,})(?P<info>.*)$")
# A list item's first line: indentation, a bullet or ordinal marker, then content
_LIST_ITEM_RE = re.compile(r"^(?P<indent>[ ]*)(?:[-*+]|\d{1,9}[.)])[ ]+\S")


# An inline code span: a backtick run, content, and a closing run of exactly the same length
_INLINE_CODE_RE = re.compile(r"(?<!`)(?P<ticks>`+)(?!`).+?(?<!`)(?P=ticks)(?!`)")

# An HTML tag or comment, in the shape of Python-Markdown's inline HTML_RE. The letter after "<" keeps
# "a < b" prose. It also covers autolinks and automail ("<https://x>"), which start with a letter too and
# must not be rewritten for the same reason. Like Python-Markdown's, neither body admits "<" or ">", so a
# span holding a "<^>" marker is prose, as it is to in-process highlight.
_HTML_TAG_RE = re.compile(r"<(?:/?[A-Za-z][^<>]*|!--(?:(?!-->)[^<>])*--)>")

# One left-to-right pass over both grammars, so whichever starts first wins
_SKIPPED_SPAN_RE = re.compile(f"{_INLINE_CODE_RE.pattern}|{_HTML_TAG_RE.pattern}")

if TYPE_CHECKING:
    from collections.abc import Callable


class FencedBlock(BaseModel):
    """A closed fenced code block found in Markdown source.

    :ivar opening: Line index of the opening fence.
    :ivar closing: Line index of the closing fence.
    :ivar indent: The opening fence's indentation with tabs expanded to four columns, as spaces, repeated
        on lines the pre stage inserts.
    :ivar marker: The opening fence run, for example ``\\`\\`\\``` or ``~~~~``.
    :ivar info: The info string after the opening fence, unstripped.
    """

    model_config = ConfigDict(frozen=True)

    opening: int
    closing: int
    indent: str
    marker: str
    info: str


def find_fenced_blocks(lines: list[str]) -> list[FencedBlock]:
    """Find the closed fenced code blocks in Markdown source lines.

    Follows CommonMark: an opening fence is indented up to three columns (or sits inside a list
    item, under the item's content), a tab counts as four columns, a backtick fence's info string
    holds no backtick, and the closing fence uses the same character, is at least as long, and carries nothing else. An
    unclosed fence is not a code block, matching ``pymdownx.superfences``.

    :param lines: Source lines.
    :returns: The fenced blocks in source order; nested fences inside a block are content.
    """
    blocks: list[FencedBlock] = []
    line_index = 0
    while line_index < len(lines):
        open_match = _FENCE_OPEN_RE.match(lines[line_index].expandtabs(_TAB_WIDTH))
        if (
            open_match is None
            or (open_match["marker"][0] == "`" and "`" in open_match["info"])
            or not _is_outside_indented_code(lines, line_index, len(open_match["indent"]))
        ):
            line_index += 1
            continue

        # The closing fence: same character, at least as long, nothing after it
        marker = open_match["marker"]
        closing = next(
            (
                scan_index
                for scan_index in range(line_index + 1, len(lines))
                if (stripped := lines[scan_index].strip()).startswith(marker)
                and set(stripped) == {marker[0]}
                and _indent_width(lines[scan_index]) <= len(open_match["indent"]) + 3
            ),
            None,
        )
        if closing is None:
            line_index += 1
            continue

        blocks.append(
            FencedBlock(
                opening=line_index,
                closing=closing,
                indent=open_match["indent"],
                marker=marker,
                info=open_match["info"],
            )
        )
        line_index = closing + 1
    return blocks


def _indent_width(line: str) -> int:
    """Count a line's leading columns, reading a tab as four columns like Python-Markdown.

    :param line: A source line.
    :returns: The number of leading spaces after tab expansion.
    """
    expanded = line.expandtabs(_TAB_WIDTH)
    return len(expanded) - len(expanded.lstrip(" "))


def _is_outside_indented_code(lines: list[str], line_index: int, indent_width: int) -> bool:
    """Report whether a line at this indentation is not an indented code line.

    Up to three columns is never indented code. Four or more is list content, not code, only inside
    a list item: the nearest earlier non-blank line indented less than this line must be a list
    item, and this line must sit at or past that item's content. A fence opens at such a position,
    and an indented code block cannot start there. A line eight or more columns deep under a list
    item is indented code to Python-Markdown but list content here, so it is still transformed;
    erring toward transforming is the safer failure.

    :param lines: Source lines.
    :param line_index: Index of the line.
    :param indent_width: The line's indentation in columns.
    :returns: ``True`` if the line is prose or fence territory rather than indented code.
    """
    if indent_width <= 3:
        return True
    for earlier_line in reversed(lines[:line_index]):
        earlier_indent = _indent_width(earlier_line)
        if not earlier_line.strip() or earlier_indent >= indent_width:
            continue
        item_match = _LIST_ITEM_RE.match(earlier_line.expandtabs(_TAB_WIDTH))
        return item_match is not None and indent_width >= len(item_match["indent"]) + 2
    return False


def _indented_code_lines(lines: list[str], fenced_lines: set[int]) -> set[int]:
    """Find the lines of top-level indented code blocks.

    A non-blank line of four or more columns that follows a blank line (or starts the document) and
    is not list content opens a block. The block runs through blank lines and lines of four or more
    columns; the first non-blank line of fewer columns ends it. A four-column line straight after a
    paragraph line is a lazy continuation, not code. Fenced lines are skipped and end any open block.

    :param lines: Source lines.
    :param fenced_lines: Indexes of lines inside closed fences.
    :returns: The indexes of indented code lines.
    """
    code_lines: set[int] = set()
    in_block = False
    previous_blank = True
    for line_index, line in enumerate(lines):
        if line_index in fenced_lines:
            in_block = False
            previous_blank = False
            continue
        if not line.strip():
            previous_blank = True
            continue
        indent_width = _indent_width(line)
        if indent_width >= 4 and (
            in_block or (previous_blank and not _is_outside_indented_code(lines, line_index, indent_width))
        ):
            in_block = True
            code_lines.add(line_index)
        else:
            in_block = False
        previous_blank = False
    return code_lines


def _code_line_indexes(lines: list[str]) -> set[int]:
    """Find every line that is code: closed fences and indented code blocks.

    :param lines: Source lines.
    :returns: The indexes of lines the mappers must leave untouched.
    """
    fenced_lines = {
        line_index for block in find_fenced_blocks(lines) for line_index in range(block.opening, block.closing + 1)
    }
    return fenced_lines | _indented_code_lines(lines, fenced_lines)


def map_prose(text: str, transform: Callable[[str], str], *, skip_html: bool = False) -> str:
    """Apply a transform to the prose of Markdown source, skipping code.

    Fenced code blocks (found by :func:`find_fenced_blocks`), indented code blocks (four columns or
    a tab after a blank line, outside a list item) and inline code spans pass through unchanged;
    ``transform`` sees only the runs of text between them.

    With ``skip_html``, HTML tags, HTML comments, and autolinks pass through unchanged too (a tag's
    text content is prose), and a backtick inside a tag does not open a code span. The flag exists
    because a highlight pair may span inline HTML (``<^>a <b>c</b><^>``), so highlight must see the
    tags as prose, while a single-token shortcode never spans a tag.

    :param text: Raw Markdown source.
    :param transform: A function applied to each prose run.
    :param skip_html: Also skip HTML tags, comments, and autolinks.
    :returns: The source with every prose run transformed.
    """
    lines = text.split("\n")
    code_lines = _code_line_indexes(lines)
    skipped_span_re = _SKIPPED_SPAN_RE if skip_html else _INLINE_CODE_RE

    output_chunks: list[str] = []
    for is_code, line_group in itertools.groupby(enumerate(lines), key=lambda entry: entry[0] in code_lines):
        chunk = "\n".join(line for _, line in line_group)
        if is_code:
            output_chunks.append(chunk)
            continue

        # Within prose, inline code spans (and HTML, when asked) are skipped as well
        mapped_parts: list[str] = []
        cursor = 0
        for skipped_span in skipped_span_re.finditer(chunk):
            mapped_parts.append(transform(chunk[cursor : skipped_span.start()]))
            mapped_parts.append(skipped_span.group(0))
            cursor = skipped_span.end()
        mapped_parts.append(transform(chunk[cursor:]))
        output_chunks.append("".join(mapped_parts))
    return "\n".join(output_chunks)


def map_lines(text: str, transform: Callable[[str], list[str]]) -> str:
    """Apply a line-level transform to Markdown source, skipping fenced and indented code.

    The line-level twin of :func:`map_prose`. Lines inside a fenced code block (found by
    :func:`find_fenced_blocks`) or an indented code block pass through unchanged; every other line is replaced by the
    lines ``transform`` returns, so a directive can rewrite in place (a one-element list) or expand to a
    marker plus a blank line (several lines).

    :param text: Raw Markdown source.
    :param transform: A function returning the replacement lines for one source line.
    :returns: The source with every non-code line transformed.
    """
    lines = text.split("\n")
    code_lines = _code_line_indexes(lines)

    output: list[str] = []
    for line_index, line in enumerate(lines):
        output.extend([line] if line_index in code_lines else transform(line))
    return "\n".join(output)
