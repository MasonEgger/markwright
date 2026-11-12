# ABOUTME: Tabs extension: paired [tab NAME]/[/tab] blocks group into tabbed sets with mw-tab-S-T ids.
# Carries each tab in mw-tab and mw-tab-end marker comments from the pre stage to the post stage.

# A [tab NAME] opener paired with [/tab] is one tab. The pre stage pairs containers with
# _containers.scan_containers, so an opener or closer inside fenced or indented code stays literal,
# and it emits an mw-tab open marker (carrying the name and a first flag) and an mw-tab-end close
# marker around each tab's content. Tabs separated only by blank lines join one set; any other
# content between them starts a new set, so the first flag is True for the opener that starts a
# set. The post stage orders every mw-tab and mw-tab-end by position, stack-matches them, groups
# the tabs into sets at each first marker, and wraps each set in pymdown-extensions' tabbed
# alternate_style markup: a <div class="tabbed-set tabbed-alternate mw-tabs" data-tabs="S:N">, one
# radio <input> per tab (id="mw-tab-S-T", name="mw-tab-S", the first checked), a tabbed-labels div
# of <label for="mw-tab-S-T"> with the name html-escaped, and a tabbed-content div holding one
# tabbed-block per tab. S counts sets and T counts tabs within a set, both from 1 per document; the
# mw-tab- prefix keeps the ids from colliding with pymdown-extensions' own __tabbed_ ids. An
# unclosed [tab] or a stray [/tab] stays literal and gains an inline mw-tab-problem marker so the
# post stage reports it under --warn and removes the comment; an empty [tab ] is not an opener and
# is left literal with no report. Every marker is a versioned public contract read fail-soft: a
# malformed payload, an unsupported version, a wrongly typed field, or an unmatched open or close
# is skipped with a reason and its comment removed, never raised.

from __future__ import annotations

import html
from typing import TYPE_CHECKING, Annotated, Literal

from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor
from markdown.preprocessors import Preprocessor
from pydantic import BaseModel, ConfigDict, Field

from markwright._containers import TAB_END_MARKER_NAME, TAB_MARKER_NAME, scan_containers
from markwright._html import apply_edits, tokenize
from markwright._markers import (
    InvalidMarkerError,
    decode_marker,
    inline_problem_marker,
    marker_block,
    match_marker_pairs,
    report_problem_markers,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from markdown import Markdown

    from markwright._html import HtmlToken
    from markwright._markers import MarkerComment

MARKER_OPEN = TAB_MARKER_NAME
MARKER_CLOSE = TAB_END_MARKER_NAME
PROBLEM_MARKER_NAME = "mw-tab-problem"

_ProblemDirective = Literal["[tab]", "[/tab]"]
_ProblemReason = Literal["unclosed", "stray-closer"]

# scan_containers reports problems as free text; map the tab-owned ones to a closed vocabulary.
# An empty [tab ] is absent on purpose: spec.md (Containers, Tabs) says it is not an opener, so
# it stays literal with no report.
_TAB_OWNED_PROBLEMS: dict[str, tuple[_ProblemDirective, _ProblemReason]] = {
    "unclosed [tab] opener": ("[tab]", "unclosed"),
    "no matching [tab] opener": ("[/tab]", "stray-closer"),
}

# Post composes the stderr message from the validated reason code, so a hand-written marker
# cannot push arbitrary text to stderr.
_PROBLEM_DETAIL: dict[_ProblemReason, str] = {
    "unclosed": "unclosed, no matching closer",
    "stray-closer": "no matching opener",
}


class TabMarker(BaseModel):
    """A validated v1 mw-tab marker payload for one tab.

    The pre stage emits it at a ``[tab NAME]`` opener; the post stage pairs it with the next
    mw-tab-end marker, groups it into a set, and builds the tab's input, label, and block. Strict,
    so a field of the wrong type fails validation instead of being coerced; unknown fields are
    ignored.

    :ivar version: The payload version, ``1``.
    :ivar name: The tab label, rendered as html-escaped plain text.
    :ivar first: Whether this tab starts a new set.
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="ignore")

    version: int
    name: str
    first: bool


class TabProblemMarker(BaseModel):
    """A validated v1 mw-tab-problem marker payload for a tab container left literal.

    The pre stage attaches it, inline, to an unclosed ``[tab]`` or a stray ``[/tab]`` it cannot
    pair. The directive text stays literal; the post stage reads the marker, composes one
    ``--warn`` message from the validated fields, and removes the comment. Strict with a closed
    vocabulary, so a hand-written marker cannot push free text to stderr; unknown fields are
    ignored.

    :ivar version: The payload version, ``1``.
    :ivar line: The 1-based source line of the literal directive.
    :ivar directive: The literal directive kind, ``[tab]`` or ``[/tab]``.
    :ivar reason: The problem code, ``unclosed`` or ``stray-closer``.
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="ignore")

    version: int
    line: Annotated[int, Field(ge=1)]
    directive: _ProblemDirective
    reason: _ProblemReason


def _problem_message(problem: TabProblemMarker) -> str:
    """Compose a ``--warn`` message from a validated problem marker.

    :param problem: The decoded marker carrying the directive, line, and reason code.
    :returns: A one-line diagnostic naming the directive and its source line.
    """
    return f"Leaving {problem.directive} on line {problem.line} literal: {_PROBLEM_DETAIL[problem.reason]}"


def expand_source(text: str, options: Mapping[str, object] | None = None) -> str:
    """Replace tab containers with marker comments in raw source.

    Used by the ``mw pre`` CLI stage. Pairs containers with :func:`scan_containers`, so an opener
    or closer inside fenced or indented code stays literal. Each ``[tab NAME]``/``[/tab]`` pair
    becomes an mw-tab open marker carrying the name and a first flag, and an mw-tab-end close
    marker. The first flag is True when the tab starts a set: for the first tab, or when any
    non-blank content separates it from the previous tab. An unclosed ``[tab]`` or a stray
    ``[/tab]`` stays literal and gains an inline mw-tab-problem marker; an empty ``[tab ]`` and
    every non-tab container are left untouched.

    :param text: The source text.
    :param options: Accepted for the registry's shared signature; tabs has no options.
    :returns: The text with tab containers replaced by markers.
    """
    scan = scan_containers(text)
    lines = text.split("\n")
    replacements: dict[int, list[str]] = {}
    previous_close: int | None = None
    for pair in scan.pairs:
        if pair.kind != "tab" or pair.from_marker:
            # A tab pair whose lines are already tabs' own markers (mw pre run twice, or
            # hand-written) stays in place; re-emitting would crash on its empty tokens.
            continue
        if previous_close is None:
            first = True
        else:
            gap = lines[previous_close + 1 : pair.open_line]
            first = any(gap_line.strip() for gap_line in gap)
        replacements[pair.open_line] = marker_block(pair.indent, MARKER_OPEN, {"name": pair.tokens[0], "first": first})
        replacements[pair.close_line] = marker_block(pair.indent, MARKER_CLOSE, {})
        previous_close = pair.close_line
    for problem in scan.problems:
        if problem.from_marker:
            # The problem line is one of tabs' own markers; the post stage reports the lone marker
            # fail-soft, so a second inline problem marker here would double the --warn report.
            continue
        owned = _TAB_OWNED_PROBLEMS.get(problem.reason)
        if owned is None:
            continue
        directive, reason = owned
        payload = {"line": problem.line + 1, "directive": directive, "reason": reason}
        replacements[problem.line] = [inline_problem_marker(lines[problem.line], PROBLEM_MARKER_NAME, payload)]

    if not replacements:
        return text
    expanded: list[str] = []
    for line_index, line in enumerate(lines):
        expanded.extend(replacements.get(line_index, [line]))
    return "\n".join(expanded)


def _render_set(
    set_number: int, tab_group: list[tuple[TabMarker, MarkerComment, MarkerComment]], tokens: list[HtmlToken]
) -> list[tuple[int, int, str]]:
    """Build the span edits that wrap one set's tabs in the tabbed markup.

    The set's inputs and labels are composed from every tab, so the header is known only after the
    set is collected. Each tab's rendered body stays in place between its markers; the open marker
    becomes the block opener (the whole set header for the first tab) and the close marker becomes
    the block closer (plus the content and set closers for the last tab).

    :param set_number: The 1-based set number ``S``.
    :param tab_group: The set's tabs as ``(marker, open_marker, close_marker)`` in order.
    :param tokens: The tokens of the rendered HTML, for each marker comment's span.
    :returns: The span edits for the set.
    """
    count = len(tab_group)
    set_name = f"mw-tab-{set_number}"
    inputs: list[str] = []
    labels: list[str] = []
    for position, (marker, _open_marker, _close_marker) in enumerate(tab_group, start=1):
        tab_id = f"mw-tab-{set_number}-{position}"
        checked = 'checked="checked" ' if position == 1 else ""
        inputs.append(f'<input {checked}type="radio" id="{tab_id}" name="{set_name}" />')
        labels.append(f'<label for="{tab_id}">{html.escape(marker.name)}</label>')
    header = (
        f'<div class="tabbed-set tabbed-alternate mw-tabs" data-tabs="{set_number}:{count}">\n'
        + "".join(f"{input_tag}\n" for input_tag in inputs)
        + '<div class="tabbed-labels">\n'
        + "".join(f"{label}\n" for label in labels)
        + "</div>\n"
        + '<div class="tabbed-content">\n'
        + '<div class="tabbed-block">'
    )

    edits: list[tuple[int, int, str]] = []
    for position, (_marker, open_marker, close_marker) in enumerate(tab_group, start=1):
        open_comment = tokens[open_marker.token_index]
        close_comment = tokens[close_marker.token_index]
        open_replacement = header if position == 1 else '<div class="tabbed-block">'
        close_replacement = "</div>\n</div>\n</div>" if position == count else "</div>"
        edits.append((open_comment.start, open_comment.end, open_replacement))
        edits.append((close_comment.start, close_comment.end, close_replacement))
    return edits


def apply_html(
    rendered_html: str, skip_reasons: list[str] | None = None, options: Mapping[str, object] | None = None
) -> str:
    """Group tab markers into sets and wrap each set in the tabbed markup.

    Used by the ``mw post`` CLI stage. Orders every mw-tab and mw-tab-end marker by position and
    stack-matches them; a ``first`` marker (or the first tab seen) starts a set, the rest join it.
    Each set wraps in a ``tabbed-set`` ``<div>`` with one radio ``<input>`` and ``<label>`` per
    tab and one ``tabbed-block`` per tab's body. An mw-tab-problem marker reports a tab container
    left literal and is removed. Markers are validated and skipped fail-soft; pass a
    ``skip_reasons`` list to collect the reports and the skips. Every recognized marker comment is
    removed.

    :param rendered_html: Rendered HTML containing tab marker comments.
    :param skip_reasons: Optional list collecting skip reasons; ``None`` drops them.
    :param options: Accepted for the registry's shared signature; tabs has no options.
    :returns: HTML with the tab sets wrapped and the markers removed.
    """
    tokens = tokenize(rendered_html)
    edits = report_problem_markers(
        PROBLEM_MARKER_NAME, rendered_html, tokens, TabProblemMarker, _problem_message, skip_reasons
    )

    match = match_marker_pairs(MARKER_OPEN, MARKER_CLOSE, rendered_html, tokens)
    sets: list[list[tuple[TabMarker, MarkerComment, MarkerComment]]] = []
    for open_marker, close_marker in match.pairs:
        try:
            marker = decode_marker(MARKER_OPEN, open_marker.raw_payload, TabMarker)
        except InvalidMarkerError as skipped:
            edits.append((tokens[open_marker.token_index].start, tokens[open_marker.token_index].end, ""))
            edits.append((tokens[close_marker.token_index].start, tokens[close_marker.token_index].end, ""))
            if skip_reasons is not None:
                skip_reasons.append(str(skipped))
            continue
        if marker.first or not sets:
            sets.append([])
        sets[-1].append((marker, open_marker, close_marker))
    for set_number, tab_group in enumerate(sets, start=1):
        edits += _render_set(set_number, tab_group, tokens)

    for close_marker in match.unmatched_closes:
        comment = tokens[close_marker.token_index]
        edits.append((comment.start, comment.end, ""))
        if skip_reasons is not None:
            skip_reasons.append(f"Skipping {MARKER_CLOSE} marker with no matching {MARKER_OPEN}")
    for open_marker in match.unmatched_opens:
        comment = tokens[open_marker.token_index]
        edits.append((comment.start, comment.end, ""))
        if skip_reasons is not None:
            skip_reasons.append(f"Skipping {MARKER_OPEN} marker with no matching {MARKER_CLOSE}")
    return apply_edits(rendered_html, edits)


class TabsPreprocessor(Preprocessor):
    """Replace tab containers with marker comments."""

    def run(self, lines: list[str]) -> list[str]:
        """Process lines, replacing tab containers with markers.

        :param lines: Source lines to process.
        :returns: Modified lines.
        """
        return expand_source("\n".join(lines)).split("\n")


class TabsPostprocessor(Postprocessor):
    """Group the tabs that mw-tab markers mark into sets and wrap each in tabbed markup."""

    def run(self, text: str) -> str:
        """Process rendered HTML, wrapping the marked tabs and removing the markers.

        :param text: Rendered HTML string.
        :returns: Modified HTML.
        """
        return apply_html(text)


class TabsExtension(Extension):
    """Python-Markdown extension for tabs."""

    def extendMarkdown(self, md: Markdown) -> None:  # noqa: N802 - Python-Markdown's hook name
        """Register the tabs preprocessor and postprocessor.

        :param md: The Markdown instance to extend.
        """
        md.preprocessors.register(TabsPreprocessor(md), "mw-tabs-pre", 20)
        md.postprocessors.register(TabsPostprocessor(md), "mw-tabs-post", 30)


def makeExtension(**kwargs: object) -> TabsExtension:  # noqa: N802 - Python-Markdown's loader name
    """Create and return the TabsExtension instance.

    :param \\*\\*kwargs: Configuration options.
    :returns: A configured TabsExtension.
    """
    return TabsExtension(**kwargs)
