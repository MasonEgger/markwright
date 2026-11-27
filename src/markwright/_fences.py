# ABOUTME: Shared scanner for fenced code blocks in Markdown source, following CommonMark's fence rules.
# Used by the fence, mermaid, highlight, and icons pre stages and, through map_lines, every directive-line stage.

from __future__ import annotations

import functools
import itertools
import re
from types import MappingProxyType
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict

# How many documents' scans the pre stages remember; stages run in turn over one document
_REGION_CACHE_SIZE = 8

# Python-Markdown expands a tab to four columns, so every pattern below runs on tab-expanded text.
_TAB_WIDTH = 4

# One block quote marker: up to three columns of indentation, ">", and the optional space after it
_QUOTE_MARKER = r"[ ]{0,3}>[ ]?"
# An opening fence: any block quote markers, indentation, three or more backticks or tildes, then the info string
_FENCE_OPEN_RE = re.compile(
    rf"^(?P<quote>(?:{_QUOTE_MARKER})*)(?P<indent>[ ]*)(?P<marker>`{{3,}}|~{{3,}})(?P<info>.*)$"
)
# A list item's first line: indentation, a bullet or ordinal marker, then content
_LIST_ITEM_RE = re.compile(r"^(?P<indent>[ ]*)(?:[-*+]|\d{1,9}[.)])[ ]+\S")
# The block openers whose body is content, matched against the stripped line and mirroring the grammars of
# Python-Markdown's admonition and footnotes extensions and of pymdownx.details and pymdownx.tabbed. The
# first three (an admonition "!!! note", a details block "???+ note", a content tab "===+ \"Tab\"") must sit
# at the column of the block that holds them. A footnote definition may sit up to three columns in at the top
# level, and a definition up to three columns in at the top level or in an opener's body.
_COLUMN_OPENER_RES = (
    re.compile(r"!!! ?[\w\-]+(?: +[\w\-]+)*(?: +\".*?\")? *$"),
    re.compile(r"\?{3}\+? ?(?:(?:[\w\-]+(?: +[\w\-]+)*?)?(?: +\".*?\")|[\w\-]+(?: +[\w\-]+)*?) *$"),
    re.compile(r"={3}(?:\+!|!\+|\+|!)? +\".*?\" *$"),
)
_FOOTNOTE_RE = re.compile(r"\[\^[^\]]*\]:")
# A definition line (extra def_list's ": text"); it opens a body only when a line precedes it
_DEFINITION_RE = re.compile(r":[ ]{1,3}")

# The first characters an opener can start with, so a line that starts with anything else skips the opener patterns
_OPENER_FIRST_CHARACTERS = "!?=:["
# The first characters of a list marker besides a decimal digit (any Unicode decimal digit starts an ordered
# marker, as in the pattern's \d), so a line that starts with anything else skips the list item pattern
_LIST_FIRST_CHARACTERS = "-*+"

# The columns a block opener's body sits past the opener, and the extra columns that make a line code there
_BODY_OFFSET = 4


# An inline code span: a backtick run, content, and a closing run of exactly the same length
_INLINE_CODE_RE = re.compile(r"(?<!`)(?P<ticks>`+)(?!`).+?(?<!`)(?P=ticks)(?!`)")

# An inline code span as Python-Markdown and CommonMark read it inside a paragraph: like the pattern above, but
# the content may hold a line end, never a blank line, because a blank line ends the paragraph
_PARAGRAPH_CODE_SPAN_RE = re.compile(r"(?<!`)(?P<ticks>`+)(?!`)(?:(?!\n[ \t]*\n).)+?(?<!`)(?P=ticks)(?!`)", re.DOTALL)

# An HTML tag or comment, in the shape of Python-Markdown's inline HTML_RE. The letter after "<" keeps
# "a < b" prose. It also covers autolinks and automail ("<https://x>"), which start with a letter too and
# must not be rewritten for the same reason. Like Python-Markdown's, neither body admits "<" or ">", so a
# span holding a "<^>" marker is prose, as it is to in-process highlight.
_HTML_TAG_RE = re.compile(r"<(?:/?[A-Za-z][^<>]*|!--(?:(?!-->)[^<>])*--)>")

# The start of an HTML block that CommonMark and Python-Markdown pass through whole, so its lines are never
# prose: a comment (up to three columns in) that does not close on its own line, which runs through the first
# line holding "-->", and the first HTML block kind, which starts a line with <pre, <script, <style, or
# <textarea (any case, then a space, ">", or the line end) and runs through the line holding the matching
# close tag. Text after the close tag on its line is prose again.
_COMMENT_OPEN_RE = re.compile(r"[ ]{0,3}<!--")
_VERBATIM_OPEN_RE = re.compile(r"\s*<(?P<tag>pre|script|style|textarea)(?=[\s>]|$)", re.IGNORECASE)

# One left-to-right pass over both grammars, so whichever starts first wins
_SKIPPED_SPAN_RE = re.compile(f"{_INLINE_CODE_RE.pattern}|{_HTML_TAG_RE.pattern}")

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping


class FencedBlock(BaseModel):
    """A closed fenced code block found in Markdown source.

    :ivar opening: Line index of the opening fence.
    :ivar closing: Line index of the closing fence.
    :ivar quote: The block quote markers before the opening fence as written (``"> "``), empty when the
        fence is not in a block quote, repeated on lines the pre stage inserts.
    :ivar indent: The opening fence's indentation after any block quote markers, with tabs expanded to
        four columns, as spaces, repeated on lines the pre stage inserts.
    :ivar marker: The opening fence run, for example ``\\`\\`\\``` or ``~~~~``.
    :ivar info: The info string after the opening fence, unstripped.
    """

    model_config = ConfigDict(frozen=True)

    opening: int
    closing: int
    quote: str
    indent: str
    marker: str
    info: str


def find_fenced_blocks(lines: list[str]) -> list[FencedBlock]:
    """Find the closed fenced code blocks in Markdown source lines.

    Follows CommonMark: an opening fence is indented up to three columns (or sits inside a list
    item, under the item's content, or in a block opener's body), a tab counts as four columns, a
    backtick fence's info string holds no backtick, and the closing fence uses the same character, is
    at least as long, and carries nothing else. An unclosed fence is not a code block, matching
    ``pymdownx.superfences``. A fence may sit behind block quote markers (``> ``); every line through
    its closing fence then carries as many markers, and the quote ending first leaves it unclosed.

    :param lines: Source lines.
    :returns: The fenced blocks in source order; nested fences inside a block are content.
    """
    return list(_code_regions(tuple(lines))[0])


def _quote_re(quote: str) -> re.Pattern[str]:
    """Build the pattern for the block quote markers a fenced block's lines start with.

    :param quote: The block's quote markers, empty for a block outside a block quote.
    :returns: A pattern that matches, at the start of a line, as many markers as ``quote`` holds.
    """
    return re.compile(f"^(?:{_QUOTE_MARKER}){{{quote.count('>')}}}")


def strip_quote(line: str, quote: str) -> str:
    """Remove a fenced block's block quote markers from one of its lines.

    :param line: A line of the block.
    :param quote: The block's quote markers, empty for a block outside a block quote.
    :returns: The line after the markers; the whole line when ``quote`` is empty.
    """
    return _quote_re(quote).sub("", line, count=1)


def _indent_width(line: str) -> int:
    """Count a line's leading columns, reading a tab as four columns like Python-Markdown.

    :param line: A source line.
    :returns: The number of leading spaces after tab expansion.
    """
    expanded = line.expandtabs(_TAB_WIDTH)
    return len(expanded) - len(expanded.lstrip(" "))


class _Holder(BaseModel):
    """An earlier line that may hold the lines after it: a list item, a block opener, or plain text.

    :ivar indent: The line's indentation in columns.
    :ivar kind: ``list`` for a list item, ``opener`` for a block opener, else ``plain``.
    :ivar body_column: The holding block's column plus four, read only for a list item or an opener.
    """

    model_config = ConfigDict(frozen=True)

    indent: int
    kind: Literal["plain", "list", "opener"]
    body_column: int


class _BlockScan(BaseModel):
    """What one pass over the source learns about each line's block context.

    :ivar outside_code: Per line, whether it is prose or fence territory rather than indented code.
    :ivar code_floor: Per line, the indentation an indented code block starting at it needs to continue.
    """

    model_config = ConfigDict(frozen=True)

    outside_code: list[bool]
    code_floor: list[int]


def _holding_column(chain: list[_Holder], indent_width: int) -> int:
    """Find the column of the block that holds a line: 0, a list item's content column, or an opener's body column.

    Walks up the chain of earlier, less indented lines. A list item on the way holds the line at its
    content column, an opener holds it at its body column when the line sits at or past that column,
    and a plain line on the way is a body line, so the walk goes on.

    :param chain: The earlier lines indented less than the line, outermost first.
    :param indent_width: The line's indentation in columns.
    :returns: The column of the holding block.
    """
    body_indent = indent_width
    for holder in reversed(chain):
        if holder.kind == "list":
            return holder.body_column
        if holder.kind == "opener" and body_indent >= holder.body_column:
            return holder.body_column
        body_indent = holder.indent
    return 0


def _enclosing_opener(chain: list[_Holder], indent_width: int) -> _Holder | None:
    """Find the block opener whose body holds a line.

    Walks up the chain. A plain line on the way is a body line of the opener, so the line must sit at
    or past the opener's body column. A list item on the way ends the search: the line belongs to the
    list item.

    :param chain: The earlier lines indented less than the line, outermost first.
    :param indent_width: The line's indentation in columns.
    :returns: The opener, or ``None`` when the line is not in an opener's body.
    """
    body_indent = indent_width
    for holder in reversed(chain):
        if holder.kind == "list":
            return None
        if holder.kind == "opener":
            return holder if body_indent >= holder.body_column else None
        body_indent = holder.indent
    return None


def _scan_blocks(lines: list[str]) -> _BlockScan:
    """Classify every line's block context in one forward pass.

    Keeps the chain of earlier lines that are each indented less than the next, which is the chain a
    backward search for the nearest less indented line would walk, so each line costs the length of its
    chain and nothing recurses.

    A line of up to three columns is never indented code. Four or more is content, not code, only
    inside a list item or a block opener's body. In a list item, the nearest earlier line indented less
    must be the item and this line must sit at or past its content. In an opener's body, this line must
    sit from the body column through three more columns, and a line four columns past the body column
    is code, so a line four columns further than the body's lines after a blank line is still code.
    A line eight or more columns deep under a list item is indented code to Python-Markdown but list
    content here, so it is still transformed; erring toward transforming is the safer failure.

    An opener is a line that opens an admonition, details, content-tab, definition, or footnote body.
    An admonition, details, or content-tab opener must start at the column of the block that holds it
    (column 0 at the top level, the content column under a list item, an enclosing opener's body column),
    because Python-Markdown reads such a line at the start of a block. A list item's content column is
    its level (its indentation divided by four, rounded down, plus one) times four, as in Python-Markdown.
    A footnote definition sits at the top level and up to three columns in. A definition sits up to three
    columns in at the top level or in an opener's body, not in a list item, and needs a line before it,
    so it is not an opener at the start of the document.

    :param lines: Source lines.
    :returns: Each line's ``outside_code`` and ``code_floor``; blank lines carry the defaults.
    """
    outside_code = [True] * len(lines)
    code_floor = [_BODY_OFFSET] * len(lines)
    chain: list[_Holder] = []
    seen_text = False
    for line_index, line in enumerate(lines):
        if not line.strip():
            continue

        expanded = line.expandtabs(_TAB_WIDTH)
        stripped = expanded.strip()
        indent_width = len(expanded) - len(expanded.lstrip(" "))
        while chain and chain[-1].indent >= indent_width:
            chain.pop()

        enclosing = _enclosing_opener(chain, indent_width)
        if indent_width > _BODY_OFFSET - 1 and not chain:
            outside_code[line_index] = False
        elif indent_width > _BODY_OFFSET - 1 and chain[-1].kind == "list":
            outside_code[line_index] = indent_width >= min(chain[-1].indent + 2, chain[-1].body_column)
        elif indent_width > _BODY_OFFSET - 1:
            outside_code[line_index] = enclosing is not None and indent_width < enclosing.body_column + _BODY_OFFSET
        if enclosing is not None:
            code_floor[line_index] = enclosing.body_column + _BODY_OFFSET

        if (stripped[0] in _LIST_FIRST_CHARACTERS or stripped[0].isdecimal()) and _LIST_ITEM_RE.match(expanded):
            holder = _Holder(
                indent=indent_width, kind="list", body_column=(indent_width // _BODY_OFFSET + 1) * _BODY_OFFSET
            )
        else:
            column = _holding_column(chain, indent_width)
            if stripped[0] not in _OPENER_FIRST_CHARACTERS:
                is_opener = False
            elif any(opener_re.match(stripped) for opener_re in _COLUMN_OPENER_RES):
                is_opener = indent_width == column
            elif _FOOTNOTE_RE.match(stripped):
                is_opener = column == 0 and indent_width < _BODY_OFFSET
            else:
                # A definition works at the top level and in an opener's body, but not in a list item
                is_opener = (
                    _DEFINITION_RE.match(stripped) is not None
                    and seen_text
                    and 0 <= indent_width - column < _BODY_OFFSET
                    and (column == 0 or enclosing is not None)
                )
            holder = _Holder(
                indent=indent_width, kind="opener" if is_opener else "plain", body_column=column + _BODY_OFFSET
            )
        chain.append(holder)
        seen_text = True
    return _BlockScan(outside_code=outside_code, code_floor=code_floor)


def _indented_code_lines(lines: list[str], fenced_lines: set[int], scan: _BlockScan) -> set[int]:
    """Find the lines of top-level indented code blocks.

    A non-blank line of four or more columns that follows a blank line (or starts the document) and
    is not list or block-opener content opens a block. The block runs through blank lines and lines
    indented at least as far as its first line's floor (four columns, or four past the body column when it
    starts in an opener's body); the first non-blank line of fewer columns ends it. A four-column line straight after a
    paragraph line is a lazy continuation, not code. Fenced lines are skipped and end any open block.

    :param lines: Source lines.
    :param fenced_lines: Indexes of lines inside closed fences.
    :param scan: The :func:`_scan_blocks` result for ``lines``.
    :returns: The indexes of indented code lines.
    """
    code_lines: set[int] = set()
    in_block = False
    block_floor = _BODY_OFFSET
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
        if in_block and indent_width >= block_floor:
            code_lines.add(line_index)
        elif indent_width >= _BODY_OFFSET and previous_blank and not scan.outside_code[line_index]:
            in_block = True
            block_floor = scan.code_floor[line_index]
            code_lines.add(line_index)
        else:
            in_block = False
        previous_blank = False
    return code_lines


def _html_region(lines: tuple[str, ...], line_index: int) -> tuple[int, int | None] | None:
    """Find the comment or verbatim HTML block that starts at a line.

    :param lines: Source lines.
    :param line_index: The line to test; the caller has checked it is outside code.
    :returns: ``None`` when no block starts there. Otherwise the index of the line the block ends on (the
        last line of the document when nothing closes it), and for a verbatim block whose closing line
        holds more text, the offset where that text starts; ``None`` in the offset slot otherwise.
    """
    expanded = lines[line_index].expandtabs(_TAB_WIDTH)
    if comment_open := _COMMENT_OPEN_RE.match(expanded):
        if "-->" in expanded[comment_open.end() :]:
            return None
        for scan_index in range(line_index + 1, len(lines)):
            if "-->" in lines[scan_index]:
                return scan_index, None
        return len(lines) - 1, None

    if (verbatim_open := _VERBATIM_OPEN_RE.match(expanded)) is None:
        return None
    close_tag = f"</{verbatim_open['tag'].lower()}>"
    search_from = verbatim_open.end()
    for scan_index in range(line_index, len(lines)):
        scanned = lines[scan_index].expandtabs(_TAB_WIDTH) if scan_index == line_index else lines[scan_index]
        close_start = scanned.lower().find(close_tag, search_from if scan_index == line_index else 0)
        if close_start >= 0:
            tail_start = close_start + len(close_tag)
            return scan_index, tail_start if scanned[tail_start:].strip() else None
    return len(lines) - 1, None


@functools.lru_cache(maxsize=_REGION_CACHE_SIZE)
def _code_regions(
    lines: tuple[str, ...],
) -> tuple[tuple[FencedBlock, ...], frozenset[int], Mapping[int, int]]:
    """Find the closed fenced blocks and every skipped line of one document, remembering the answer.

    The pre stages run one after another over text that most of them leave unchanged, so each stage
    that scans the same lines again reads this cache instead of scanning twice.

    :param lines: Source lines.
    :returns: The fenced blocks; the indexes of lines that are closed fences, indented code, multi-line
        comments, or verbatim HTML blocks; and, for each verbatim block that ends before the end of its
        closing line, the offset where the prose after the close tag starts.
    """
    scan = _scan_blocks(list(lines))
    blocks: list[FencedBlock] = []
    html_lines: set[int] = set()
    prose_tails: dict[int, int] = {}
    line_index = 0
    while line_index < len(lines):
        if scan.outside_code[line_index] and (html_region := _html_region(lines, line_index)) is not None:
            region_end, tail_start = html_region
            html_lines.update(range(line_index, region_end + 1))
            if tail_start is not None:
                prose_tails[region_end] = tail_start
            line_index = region_end + 1
            continue

        open_match = _FENCE_OPEN_RE.match(lines[line_index].expandtabs(_TAB_WIDTH))
        if (
            open_match is None
            or (open_match["marker"][0] == "`" and "`" in open_match["info"])
            or not scan.outside_code[line_index]
        ):
            line_index += 1
            continue

        # The closing fence: same character, at least as long, nothing after it. Behind block quote
        # markers every line through it carries the opener's markers; the quote ending first leaves it unclosed
        marker = open_match["marker"]
        quote_re = _quote_re(open_match["quote"])
        closing = None
        for scan_index in range(line_index + 1, len(lines)):
            quote_match = quote_re.match(lines[scan_index])
            if quote_match is None:
                break
            content = lines[scan_index][quote_match.end() :]
            if (
                (stripped := content.strip()).startswith(marker)
                and set(stripped) == {marker[0]}
                and _indent_width(content) <= len(open_match["indent"]) + 3
            ):
                closing = scan_index
                break
        if closing is None:
            line_index += 1
            continue

        blocks.append(
            FencedBlock(
                opening=line_index,
                closing=closing,
                quote=open_match["quote"],
                indent=open_match["indent"],
                marker=marker,
                info=open_match["info"],
            )
        )
        line_index = closing + 1

    skipped_lines = {line_index for block in blocks for line_index in range(block.opening, block.closing + 1)}
    skipped_lines |= html_lines
    code_lines = skipped_lines | _indented_code_lines(list(lines), skipped_lines, scan)
    return tuple(blocks), frozenset(code_lines), MappingProxyType(prose_tails)


def find_inline_code_spans(prose: str) -> list[tuple[int, int]]:
    """Find the inline code spans of a run of prose, where a span may hold a line end.

    A span is a backtick run, content, and a closing run of exactly the same length. Unlike the spans
    :func:`map_prose` skips, the content may cross a line end, as a paragraph's code span does, but never a
    blank line, which ends the paragraph.

    :param prose: A run of prose, such as the one :func:`map_prose` hands a transform with
        ``skip_inline_code`` off.
    :returns: ``(start, end)`` offsets of each span, backticks included, in source order.
    """
    return [span_match.span() for span_match in _PARAGRAPH_CODE_SPAN_RE.finditer(prose)]


def map_prose(
    text: str,
    transform: Callable[[str], str],
    *,
    skip_html: bool = False,
    skip_inline_code: bool = True,
) -> str:
    """Apply a transform to the prose of Markdown source, skipping code.

    Fenced code blocks (found by :func:`find_fenced_blocks`), indented code blocks (four columns or
    a tab after a blank line, outside a list item and a block opener's body) and inline code spans pass
    through unchanged; ``transform`` sees only the runs of text between them.

    With ``skip_html``, HTML tags, HTML comments, and autolinks pass through unchanged too (a tag's
    text content is prose), and a backtick inside a tag does not open a code span. The flag exists
    because a highlight pair may span inline HTML (``<^>a <b>c</b><^>``), so highlight must see the
    tags as prose, while a single-token shortcode never spans a tag.

    With ``skip_inline_code`` off, inline code spans are not cut out: ``transform`` sees each whole run of
    prose lines, blank lines included, and finds the spans itself with :func:`find_inline_code_spans`.
    Highlight needs this because a pair may hold a code span.

    A multi-line HTML comment and a ``<pre>``, ``<script>``, ``<style>``, or ``<textarea>`` block pass
    through unchanged as well, the way CommonMark's HTML blocks run through their end line. Text after a
    verbatim block's close tag on its line is prose.

    :param text: Raw Markdown source.
    :param transform: A function applied to each prose run.
    :param skip_html: Also skip HTML tags, comments, and autolinks.
    :param skip_inline_code: Skip inline code spans; ``False`` leaves them inside the runs.
    :returns: The source with every prose run transformed.
    """
    lines = text.split("\n")
    _, code_lines, prose_tails = _code_regions(tuple(lines))
    if skip_html:
        skipped_span_re = _SKIPPED_SPAN_RE
    elif skip_inline_code:
        skipped_span_re = _INLINE_CODE_RE
    else:
        skipped_span_re = None

    # Cut the source into prose and skipped pieces. The newline between two lines is prose only when the text
    # on both sides of it is, so a prose run never starts or ends with a newline.
    pieces: list[tuple[bool, str]] = []
    for line_index, line in enumerate(lines):
        tail_start = prose_tails.get(line_index)
        if tail_start is None:
            line_pieces = [(line_index not in code_lines, line)]
        else:
            line_pieces = [(False, line[:tail_start]), (True, line[tail_start:])]

        if pieces:
            previous_is_prose, _ = pieces[-1]
            next_is_prose, _ = line_pieces[0]
            pieces.append((previous_is_prose and next_is_prose, "\n"))
        pieces.extend(line_pieces)

    output: list[str] = []
    for is_prose, piece_group in itertools.groupby(pieces, key=lambda piece: piece[0]):
        run = "".join(piece_text for _, piece_text in piece_group)
        if not is_prose:
            output.append(run)
            continue

        # Within prose, inline code spans and HTML (when asked) are skipped as well
        if skipped_span_re is None:
            output.append(transform(run))
            continue

        cursor = 0
        for skipped_span in skipped_span_re.finditer(run):
            output.append(transform(run[cursor : skipped_span.start()]))
            output.append(skipped_span.group(0))
            cursor = skipped_span.end()
        output.append(transform(run[cursor:]))
    return "".join(output)


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
    _, code_lines, _ = _code_regions(tuple(lines))

    output: list[str] = []
    for line_index, line in enumerate(lines):
        output.extend([line] if line_index in code_lines else transform(line))
    return "\n".join(output)


def map_directive_lines(text: str, render: Callable[[str], str | None]) -> str:
    """Replace each standalone directive line with its expansion, keeping the line's indentation.

    A directive inside an admonition, details, content-tab, definition, or footnote body, or a list item,
    sits at four or more columns. The expansion starts every one of its lines at that indentation, so
    the renderer keeps it inside the block instead of closing the block before it. A directive at
    column 0 expands byte-identically. Empty lines of a multi-line expansion stay empty, and lines
    inside fenced or indented code are left alone, as in :func:`map_lines`.

    :param text: Raw Markdown source.
    :param render: A function returning the expansion of one source line, or ``None`` when the line is
        not a directive. The expansion may hold several lines.
    :returns: The source with every directive line replaced by its indented expansion.
    """

    def transform(line: str) -> list[str]:
        expansion = render(line)
        if expansion is None:
            return [line]

        indent = line[: len(line) - len(line.lstrip())]
        return [f"{indent}{part}" if part else part for part in expansion.split("\n")]

    return map_lines(text, transform)
