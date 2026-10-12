# ABOUTME: Shared scanner for fenced code blocks in Markdown source, following CommonMark's fence rules.
# Used by the fence pre stage (directive extraction) and the highlight pre stage (skipping code) so both agree.

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

# An opening fence: indentation, then three or more backticks or tildes, then the info string
_FENCE_OPEN_RE = re.compile(r"^(?P<indent>[ ]*)(?P<marker>`{3,}|~{3,})(?P<info>.*)$")
# A list item's first line: indentation, a bullet or ordinal marker, then content
_LIST_ITEM_RE = re.compile(r"^(?P<indent>[ ]*)(?:[-*+]|\d{1,9}[.)])[ ]+\S")


class FencedBlock(BaseModel):
    """A closed fenced code block found in Markdown source.

    :ivar opening: Line index of the opening fence.
    :ivar closing: Line index of the closing fence.
    :ivar indent: The opening fence's indentation, repeated on lines the pre stage inserts.
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

    Follows CommonMark: an opening fence is indented up to three spaces (or sits inside a list
    item, under the item's content), a backtick fence's info string holds no backtick, and the
    closing fence uses the same character, is at least as long, and carries nothing else. An
    unclosed fence is not a code block, matching ``pymdownx.superfences``.

    :param lines: Source lines.
    :returns: The fenced blocks in source order; nested fences inside a block are content.
    """
    blocks: list[FencedBlock] = []
    line_index = 0
    while line_index < len(lines):
        open_match = _FENCE_OPEN_RE.match(lines[line_index])
        if (
            open_match is None
            or (open_match["marker"][0] == "`" and "`" in open_match["info"])
            or not _fence_can_open(lines, line_index, len(open_match["indent"]))
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
                and len(lines[scan_index]) - len(lines[scan_index].lstrip(" ")) <= len(open_match["indent"]) + 3
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


def _fence_can_open(lines: list[str], line_index: int, indent_width: int) -> bool:
    """Report whether a fence-shaped line at this indentation opens a fence or is indented code.

    Up to three spaces always opens a fence. Four or more opens one only inside a list item: the
    nearest earlier non-blank line indented less than the fence must be a list item, and the fence
    must sit at or past that item's content.

    :param lines: Source lines.
    :param line_index: Index of the fence-shaped line.
    :param indent_width: The line's indentation in spaces.
    :returns: ``True`` if the line opens a fence.
    """
    if indent_width <= 3:
        return True
    for earlier_line in reversed(lines[:line_index]):
        earlier_indent = len(earlier_line) - len(earlier_line.lstrip(" "))
        if not earlier_line.strip() or earlier_indent >= indent_width:
            continue
        item_match = _LIST_ITEM_RE.match(earlier_line)
        return item_match is not None and indent_width >= len(item_match["indent"]) + 2
    return False
