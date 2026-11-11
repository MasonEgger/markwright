# ABOUTME: Pairing scanner that matches container openers and closers in Markdown source.
# Reports matched pairs, unpaired-or-misplaced lines, and unclosed grid shortcuts; emits no markers or HTML.

# A container is a standalone opener line and a matching closer line: [grid]/[/grid],
# [card]/[/card], and [tab NAME]/[/tab]. The scanner walks the non-code lines with a stack,
# pairing each closer with the nearest unpaired opener of its kind at the same indentation
# (bracket matching), so nested and mixed containers pair with no special cases. Lines inside
# fenced or indented code are skipped through _fences, so an opener or closer in code stays
# literal. A line that is solely one of the paired container marker comments (mw-grid-block,
# mw-grid-end, mw-card, mw-card-end, mw-tab, mw-tab-end) counts as the opener or closer it
# stands for, so when grid and tabs both scan a document the second to run pairs from the same
# structure the first saw even though the first replaced its own lines with markers. Each pair,
# problem, and shortcut carries a from_marker flag recording whether its lines came from a marker
# comment or a directive, so a stage that meets its own markers again (mw pre run twice, or
# hand-written markers) skips them instead of re-emitting. The scanner reports structure only; the
# extensions decide what markup each pair earns.

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict

from markwright._fences import _code_line_indexes

# Openers and closers are matched against the stripped line, the whole line and nothing else.
_GRID_OPEN_RE = re.compile(r"^\[grid(?P<args>(?:\s+\w+)*)\]$")
_CARD_OPEN_RE = re.compile(r"^\[card\]$")
_TAB_OPEN_RE = re.compile(r"^\[tab\s+(?P<name>[^\]]+)\]$")
# A [tab] or [tab ] with no name: a malformed opener reported as a problem, never a pair.
_EMPTY_TAB_RE = re.compile(r"^\[tab\s*\]$")
_ContainerKind = Literal["grid", "card", "tab"]

_CLOSERS: dict[str, _ContainerKind] = {"[/grid]": "grid", "[/card]": "card", "[/tab]": "tab"}

# Marker-comment names the paired container pre stages emit. grid and tabs import these as the
# one home for the names; the scanner recognizes a line that is solely one of these marker
# comments as the corresponding opener or closer, so grid and tabs pair and compute enclosure
# from the original structure whichever of the two ran first and already rewrote its own lines.
# The mw-grid list shortcut is deliberately absent: it is an unclosed opener, not a container.
GRID_BLOCK_MARKER_NAME = "mw-grid-block"
GRID_END_MARKER_NAME = "mw-grid-end"
CARD_MARKER_NAME = "mw-card"
CARD_END_MARKER_NAME = "mw-card-end"
TAB_MARKER_NAME = "mw-tab"
TAB_END_MARKER_NAME = "mw-tab-end"

_MARKER_OPENERS: dict[str, _ContainerKind] = {
    GRID_BLOCK_MARKER_NAME: "grid",
    CARD_MARKER_NAME: "card",
    TAB_MARKER_NAME: "tab",
}
_MARKER_CLOSERS: dict[str, _ContainerKind] = {
    GRID_END_MARKER_NAME: "grid",
    CARD_END_MARKER_NAME: "card",
    TAB_END_MARKER_NAME: "tab",
}
_MARKER_RE = re.compile(r"<!-- (?P<name>mw-[\w-]+):.* -->")


class ContainerPair(BaseModel):
    """A matched opener and closer.

    :ivar kind: The container kind, ``grid``, ``card``, or ``tab``.
    :ivar open_line: Zero-based line index of the opener.
    :ivar close_line: Zero-based line index of the closer.
    :ivar indent: The opener's leading whitespace, shared with the closer.
    :ivar tokens: The opener's argument tokens: for a grid the whitespace-split words after
        ``grid``, for a tab a single element holding the trimmed name, for a card empty.
    :ivar enclosed_by_grid: Whether the nearest enclosing open container at the opener was a grid.
    :ivar from_marker: Whether the opener or the closer was an emitted marker comment rather than a
        directive. True when a pre stage meets its own markers again (mw pre run twice, or
        hand-written markers), so the owning stage skips the pair instead of re-emitting it.
    """

    model_config = ConfigDict(frozen=True)

    kind: _ContainerKind
    open_line: int
    close_line: int
    indent: str
    tokens: tuple[str, ...]
    enclosed_by_grid: bool
    from_marker: bool


class ContainerProblem(BaseModel):
    """A line that could not pair: a stray closer, an unclosed opener, or a malformed opener.

    :ivar line: Zero-based line index of the offending line.
    :ivar text: The offending line, stripped.
    :ivar reason: Why it could not pair.
    :ivar from_marker: Whether the offending line was an emitted marker comment rather than a
        directive, so the owning stage skips it instead of attaching a problem marker.
    """

    model_config = ConfigDict(frozen=True)

    line: int
    text: str
    reason: str
    from_marker: bool


class UnclosedGrid(BaseModel):
    """A ``[grid]`` opener with no closer: the list-shortcut form, not a problem.

    :ivar line: Zero-based line index of the opener.
    :ivar indent: The opener's leading whitespace.
    :ivar tokens: The whitespace-split words after ``grid``.
    :ivar from_marker: Whether the opener was an emitted marker comment rather than a directive, so
        grid leaves it untouched instead of re-emitting the shortcut marker.
    """

    model_config = ConfigDict(frozen=True)

    line: int
    indent: str
    tokens: tuple[str, ...]
    from_marker: bool


class ContainersScan(BaseModel):
    """The result of scanning source for containers.

    :ivar pairs: The matched pairs in document order.
    :ivar problems: The unpaired or misplaced lines in line order.
    :ivar unclosed_grids: The unclosed ``[grid]`` shortcuts in line order.
    """

    model_config = ConfigDict(frozen=True)

    pairs: tuple[ContainerPair, ...]
    problems: tuple[ContainerProblem, ...]
    unclosed_grids: tuple[UnclosedGrid, ...]


class _Frame(BaseModel):
    """An open container on the pairing stack, awaiting its closer.

    :ivar kind: The container kind.
    :ivar open_line: Zero-based line index of the opener.
    :ivar indent: The opener's leading whitespace.
    :ivar tokens: The opener's argument tokens.
    :ivar enclosed_by_grid: Whether the nearest enclosing open container at push was a grid.
    :ivar from_marker: Whether the opener was an emitted marker comment rather than a directive.
    """

    model_config = ConfigDict(frozen=True)

    kind: _ContainerKind
    open_line: int
    indent: str
    tokens: tuple[str, ...]
    enclosed_by_grid: bool
    from_marker: bool


def _parse_opener(stripped: str) -> tuple[_ContainerKind, tuple[str, ...]] | None:
    """Parse a stripped line as a container opener.

    :param stripped: The line with leading and trailing whitespace removed.
    :returns: The kind and argument tokens, or ``None`` when the line is not an opener.
    """
    grid_match = _GRID_OPEN_RE.match(stripped)
    if grid_match is not None:
        return "grid", tuple(grid_match["args"].split())
    if _CARD_OPEN_RE.match(stripped) is not None:
        return "card", ()
    tab_match = _TAB_OPEN_RE.match(stripped)
    if tab_match is not None:
        name = tab_match["name"].strip()
        if name:
            return "tab", (name,)
    return None


def _classify_opener(stripped: str) -> tuple[_ContainerKind, tuple[str, ...], bool] | None:
    """Classify a stripped line as a container opener, literal directive or emitted marker.

    :param stripped: The line with leading and trailing whitespace removed.
    :returns: The kind, argument tokens, and a from-marker flag, or ``None`` when the line is not an
        opener. A line that is solely an emitted open-marker comment opens its kind with no tokens
        and the flag True; the owning stage reads the tokens back from the marker payload, not from
        the scan. A directive opener carries its tokens and the flag False.
    """
    parsed = _parse_opener(stripped)
    if parsed is not None:
        kind, tokens = parsed
        return kind, tokens, False
    marker_match = _MARKER_RE.fullmatch(stripped)
    if marker_match is not None:
        marker_kind = _MARKER_OPENERS.get(marker_match["name"])
        if marker_kind is not None:
            return marker_kind, (), True
    return None


def _classify_closer(stripped: str) -> tuple[_ContainerKind, bool] | None:
    """Classify a stripped line as a container closer, literal directive or emitted marker.

    :param stripped: The line with leading and trailing whitespace removed.
    :returns: The closer's kind and a from-marker flag (True for an emitted close-marker comment,
        False for a directive), or ``None`` when the line is not a closer.
    """
    close_kind = _CLOSERS.get(stripped)
    if close_kind is not None:
        return close_kind, False
    marker_match = _MARKER_RE.fullmatch(stripped)
    if marker_match is not None:
        marker_kind = _MARKER_CLOSERS.get(marker_match["name"])
        if marker_kind is not None:
            return marker_kind, True
    return None


def _find_match(stack: list[_Frame], kind: _ContainerKind, indent: str) -> int | None:
    """Find the nearest unpaired opener of a kind at an indentation.

    :param stack: The open containers, oldest first.
    :param kind: The closer's kind.
    :param indent: The closer's leading whitespace.
    :returns: The stack index of the matching opener, or ``None`` when none matches.
    """
    for frame_index in range(len(stack) - 1, -1, -1):
        if stack[frame_index].kind == kind and stack[frame_index].indent == indent:
            return frame_index
    return None


def _nearest_of_kind(stack: list[_Frame], kind: _ContainerKind) -> int | None:
    """Find the nearest unpaired opener of a kind at any indentation.

    :param stack: The open containers, oldest first.
    :param kind: The opener kind to search for.
    :returns: The stack index of the nearest matching opener, or ``None`` when none is open.
    """
    for frame_index in range(len(stack) - 1, -1, -1):
        if stack[frame_index].kind == kind:
            return frame_index
    return None


def scan_containers(text: str) -> ContainersScan:
    """Scan Markdown source for container openers and closers.

    Walks the lines outside fenced and indented code with a stack. Each opener is pushed; each
    closer pairs with the nearest unpaired opener of its kind at the same indentation, and the
    openers it skips over are left unclosed. A stray closer, an unclosed ``[card]`` or ``[tab]``,
    and a malformed ``[tab]`` are problems; an unclosed ``[grid]`` is the list shortcut and is
    returned in ``unclosed_grids`` rather than as a problem. A stray ``[/grid]`` with no
    same-indent opener pulls the nearest still-open ``[grid]`` down as an unclosed-opener problem
    and is itself reported stray, leaving every other grid shortcut untouched.

    :param text: Raw Markdown source.
    :returns: The matched pairs, the problems, and the unclosed grid shortcuts.
    """
    lines = text.split("\n")
    code_lines = _code_line_indexes(lines)
    stack: list[_Frame] = []
    pairs: list[ContainerPair] = []
    problems: list[ContainerProblem] = []
    unpaired: list[_Frame] = []

    for line_index, line in enumerate(lines):
        if line_index in code_lines:
            continue
        stripped = line.strip()
        indent = line[: len(line) - len(line.lstrip())]

        closer = _classify_closer(stripped)
        if closer is not None:
            close_kind, close_from_marker = closer
            match_index = _find_match(stack, close_kind, indent)
            if match_index is None:
                problems.append(
                    ContainerProblem(
                        line=line_index,
                        text=stripped,
                        reason=f"no matching [{close_kind}] opener",
                        from_marker=close_from_marker,
                    )
                )
                if close_kind == "grid":
                    stray_index = _nearest_of_kind(stack, "grid")
                    if stray_index is not None:
                        stray_frame = stack.pop(stray_index)
                        problems.append(
                            ContainerProblem(
                                line=stray_frame.open_line,
                                text=lines[stray_frame.open_line].strip(),
                                reason="unclosed [grid] opener",
                                from_marker=stray_frame.from_marker,
                            )
                        )
                continue
            unpaired.extend(stack[match_index + 1 :])
            opener = stack[match_index]
            pairs.append(
                ContainerPair(
                    kind=opener.kind,
                    open_line=opener.open_line,
                    close_line=line_index,
                    indent=opener.indent,
                    tokens=opener.tokens,
                    enclosed_by_grid=opener.enclosed_by_grid,
                    from_marker=opener.from_marker or close_from_marker,
                )
            )
            del stack[match_index:]
            continue

        opened = _classify_opener(stripped)
        if opened is not None:
            kind, tokens, open_from_marker = opened
            stack.append(
                _Frame(
                    kind=kind,
                    open_line=line_index,
                    indent=indent,
                    tokens=tokens,
                    enclosed_by_grid=bool(stack) and stack[-1].kind == "grid",
                    from_marker=open_from_marker,
                )
            )
            continue

        if _EMPTY_TAB_RE.match(stripped) is not None:
            problems.append(
                ContainerProblem(line=line_index, text=stripped, reason="empty tab name", from_marker=False)
            )

    unpaired.extend(stack)
    unclosed_grids: list[UnclosedGrid] = []
    for frame in unpaired:
        if frame.kind == "grid":
            unclosed_grids.append(
                UnclosedGrid(
                    line=frame.open_line, indent=frame.indent, tokens=frame.tokens, from_marker=frame.from_marker
                )
            )
        else:
            problems.append(
                ContainerProblem(
                    line=frame.open_line,
                    text=lines[frame.open_line].strip(),
                    reason=f"unclosed [{frame.kind}] opener",
                    from_marker=frame.from_marker,
                )
            )

    return ContainersScan(
        pairs=tuple(sorted(pairs, key=lambda pair: pair.open_line)),
        problems=tuple(sorted(problems, key=lambda problem: problem.line)),
        unclosed_grids=tuple(sorted(unclosed_grids, key=lambda grid: grid.line)),
    )
