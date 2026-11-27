# ABOUTME: Fence extension adding labels, environments, and line prefixes to code blocks.
# Coordinates a Preprocessor and Postprocessor and exposes the mw-fence stage functions.

# Fence directives travel from the pre stage to the post stage as an HTML comment
# placed immediately before the fence: ``<!-- mw-fence:{JSON} -->``. This comment is
# a cross-tool contract, so its payload is versioned. The v1 schema is::
#
#     {
#       "version": 1,             # integer, the only required field
#       "label": "deploy.sh",     # optional
#       "secondary_label": "...", # optional
#       "environment": "local",   # optional
#       "prefix_type": "command", # optional: line_numbers | command | super_user | custom_prefix
#       "prefix_value": "$",      # optional: rendered prefix, absent for line_numbers
#       "disallowed_environment": "prod",  # optional: an [environment ...] outside the allowlist
#       "line": 12                # optional: source line of that directive, 1-based
#     }
#
# Every field other than ``version`` is optional and present only when the author used
# that directive. The post stage applies whatever fields it recognizes and skips a
# marker (fail-soft, optionally warning) when the JSON is malformed, the version is
# unsupported, or no code block follows.
#
# The serialized payload is comment-safe: ``_markers.encode_marker`` escapes every
# literal ``<``/``>`` in the JSON to its ``\uXXXX`` form before it is written between
# ``<!--`` and ``-->``, so a directive value containing ``-->`` can never close the
# comment early. The transform is self-reversing: ``json.loads`` restores the
# characters on read, so the post stage needs no manual decode step.

from __future__ import annotations

import html
import re
import warnings
from typing import TYPE_CHECKING, Literal

from markdown.postprocessors import Postprocessor
from markdown.preprocessors import Preprocessor
from pydantic import BaseModel, ConfigDict

from markwright._diagnostics import ConfigWarning, Diagnostic, OptionError, ReportingExtension, report
from markwright._fences import FencedBlock, find_fenced_blocks, is_shallow_indent, item_text_end, strip_quote
from markwright._html import HtmlToken, add_classes, apply_edits, tokenize
from markwright._markers import (
    InvalidMarkerError,
    decode_marker,
    encode_marker,
    find_markers,
    rebase_marker_lines,
    skipped_diagnostic,
)
from markwright.mermaid import MERMAID_CLASS

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from markdown import Markdown

MARKER_NAME = "mw-fence"
DEFAULT_LABEL_CLASS = "code-label"
DEFAULT_SECONDARY_LABEL_CLASS = "secondary-code-label"

# The in-process default for allowed_environments, meaning "omitted". Python-Markdown runs a None
# default through parseBoolValue, which would turn a list into a bool, so a sentinel stands in.
_ALL_ENVIRONMENTS = object()

LABEL_RE = re.compile(r"^\[label (.+)\]$")
SECONDARY_LABEL_RE = re.compile(r"^\[secondary_label (.+)\]$")
ENVIRONMENT_RE = re.compile(r"^\[environment (.+)\]$")
CUSTOM_PREFIX_RE = re.compile(r"^custom_prefix\((.+)\)$")
# One single-line grammar for an info string: the head (comma-separated flags and language, a
# parenthesized flag argument kept whole), then the space before a highlighter attribute, then the
# attributes. A brace starts the attributes with no space. It matches at the start of any string, even an empty one.
INFO_STRING_RE = re.compile(r"(?P<head>(?:\([^)]*\)|[^\s{])*)(?P<separator>\s*)(?P<attributes>.*)")
CLASS_TOKENS_RE = re.compile(r"[A-Za-z0-9_-]+(?: [A-Za-z0-9_-]+)*")


def _parse_prefix_from_info(info_string: str) -> tuple[str, dict[str, str]]:
    """Parse prefix flags from a fence info string and return cleaned info + prefix metadata.

    Flags and the language are the comma-separated head of the string, up to its first space or ``{``. The
    rest is a highlighter attribute (``hl_lines="1"``, ``title="x.sh"``, Hugo's ``{hl_lines=[1]}``) and
    passes through untouched, so a comma inside an attribute value is not a separator.

    :param info_string: The raw info string after the opening fence markers.
    :returns: Tuple of (cleaned info string, prefix metadata dict).
    """
    info_parts = next(INFO_STRING_RE.finditer(info_string))
    parts = info_parts.group("head").split(",")
    prefix_metadata: dict[str, str] = {}
    remaining_parts: list[str] = []
    add_bash = False

    for part in parts:
        stripped_part = part.strip()
        if stripped_part == "line_numbers":
            prefix_metadata["prefix_type"] = "line_numbers"
            # line_numbers wins over an earlier flag, so its value goes too
            prefix_metadata.pop("prefix_value", None)
        elif stripped_part == "command":
            prefix_metadata["prefix_type"] = "command"
            prefix_metadata["prefix_value"] = "$"
            add_bash = True
        elif stripped_part == "super_user":
            prefix_metadata["prefix_type"] = "super_user"
            prefix_metadata["prefix_value"] = "#"
            add_bash = True
        else:
            custom_match = CUSTOM_PREFIX_RE.match(stripped_part)
            if custom_match:
                raw_prefix = custom_match.group(1).replace("\\s", " ")
                prefix_metadata["prefix_type"] = "custom_prefix"
                prefix_metadata["prefix_value"] = raw_prefix
                add_bash = True
            else:
                remaining_parts.append(stripped_part)

    if add_bash and not remaining_parts:
        remaining_parts.append("bash")

    # An attribute with no language would be read as the language, so a plain text one goes first
    if not remaining_parts and info_parts.group("attributes"):
        remaining_parts.append("text")

    # A space before the attributes collapses to one; a brace stays where it was written
    cleaned_info = (
        ",".join(remaining_parts) + (" " if info_parts.group("separator") else "") + info_parts.group("attributes")
    )
    return cleaned_info, prefix_metadata


def _wrap_lines_with_prefix(code_content: str, prefix_type: str, prefix_value: str) -> str:
    """Wrap each code line in <li> elements with data-prefix attributes inside an <ol>.

    Pygments-style highlighters emit flat, newline-delimited lines, so a split on newlines is
    correct. Chroma (Hugo) wraps each line in ``<span class="line">...</span>`` with the newline
    inside the span; splitting that on newlines would cut a line span in half and emit a
    spurious empty prefixed line, so its top-level line spans are taken whole instead.

    :param code_content: The raw content between <code> and </code> tags.
    :param prefix_type: The marker's prefix type; ``line_numbers`` numbers the lines.
    :param prefix_value: The prefix for every line, unused for ``line_numbers``.
    :returns: The content wrapped in <ol><li data-prefix="..."> elements.
    """
    code_tokens = tokenize(code_content)

    # Collect Chroma's top-level line spans, if there are any
    code_lines: list[str] = []
    is_chroma = True
    span_depth = 0
    line_span: HtmlToken | None = None
    for token in code_tokens:
        if token.kind == "start" and token.tag == "span":
            if span_depth == 0 and token.has_class("line"):
                line_span = token
            span_depth += 1
        elif token.kind == "end" and token.tag == "span" and span_depth:
            span_depth -= 1
            if span_depth == 0 and line_span is not None:
                code_lines.append(code_content[line_span.start : token.end])
                line_span = None
    if not code_lines:
        is_chroma = False
        code_lines = code_content.removesuffix("\n").split("\n")

    # A Chroma line span already holds its own newline; a flat line has none
    line_ending = "" if is_chroma else "\n"
    wrapped_lines: list[str] = []
    for line_index, line_text in enumerate(code_lines):
        current_prefix = str(line_index + 1) if prefix_type == "line_numbers" else prefix_value
        wrapped_lines.append(f'<li data-prefix="{html.escape(current_prefix)}">{line_text}{line_ending}</li>')
    return "<ol>" + "".join(wrapped_lines) + "</ol>\n"


def _leading_directives(lines: list[str], block: FencedBlock) -> Iterator[tuple[str, str]]:
    """Read a fence's leading directive lines, the one grammar the pre stage and the scan share.

    A directive is a content line that is exactly ``[label ...]``, ``[secondary_label ...]`` or
    ``[environment ...]``, after the block quote markers of a fence in a block quote; the first other
    line ends the run. The value is everything after the first space of the directive, as written.

    :param lines: The document's source lines.
    :param block: The fenced block whose content lines are read.
    :returns: ``(directive, value)`` pairs in order, where ``directive`` is ``label``,
        ``secondary_label``, or ``environment``.
    """
    for content_line in lines[block.opening + 1 : block.closing]:
        stripped_line = strip_quote(content_line, block.quote).strip()
        if label_match := LABEL_RE.match(stripped_line):
            yield "label", label_match.group(1)
        elif secondary_match := SECONDARY_LABEL_RE.match(stripped_line):
            yield "secondary_label", secondary_match.group(1)
        elif environment_match := ENVIRONMENT_RE.match(stripped_line):
            yield "environment", environment_match.group(1)
        else:
            return


def environment_names(text: str, *, skip_mermaid: bool) -> list[str]:
    """List the environment names a document's fence directives name.

    Reads fences and directives by the rules the pre stage extracts them with, with one
    difference: a disallowed ``[environment ...]`` line does not end the scan of its fence, so
    every environment line among a fence's leading lines is listed. A directive inside a nested
    fence's source is code and not listed.

    :param text: The source text.
    :param skip_mermaid: Skip ``mermaid`` fences, which the mermaid stage replaces before fence
        reads them.
    :returns: Every name in document order, repeats included, each as written.
    """
    lines = text.split("\n")
    return [
        value
        for block in find_fenced_blocks(lines)
        if not (skip_mermaid and block.info.strip() == MERMAID_CLASS)
        for directive, value in _leading_directives(lines, block)
        if directive == "environment"
    ]


def _expand_lines(lines: list[str], allowed_environments: list[str] | None) -> list[str]:
    """Extract fence directives and prefix flags, inserting the mw-fence marker comment.

    Shared by the in-process preprocessor and the ``mw pre`` stage function. Fences are found
    by the shared CommonMark scanner, so indented fences, fences in list items, and fences behind
    block quote markers count. A marker for an indented fence is written at the fence's indentation
    and followed by a blank line, so it stays inside the list item and renders as its own block, and a
    blank line goes before it unless the line above is blank, so a tight list item's text does not absorb it. An
    indented marked fence also gets a blank line after its closing fence when text follows, and that text
    ends in one before the first less indented line, so the next list item stays an item. A
    marker for a fence in a block quote is written behind the same quote markers, with a blank quoted
    line on each side, so it stays inside the quote and outside the paragraph before the fence.

    :param lines: Source lines to process.
    :param allowed_environments: Allowed environment names, or ``None`` to allow every environment;
        an empty list allows none.
    :returns: Modified lines with directives replaced by mw-fence marker comments. An environment
        outside the allowlist stays in the code and is named in the marker's ``disallowed_environment``,
        with its ``line`` in ``lines``.
    """
    output: list[str] = []
    text_ends: set[int] = set()
    cursor = 0
    for block in find_fenced_blocks(lines):
        _copy_text(output, lines[cursor : block.opening], cursor, text_ends)

        # Parse prefix flags from the info string; the fence line keeps the language
        cleaned_info, prefix_metadata = _parse_prefix_from_info(block.info.strip())
        fence_line = lines[block.opening]
        line_start = block.quote + block.indent
        if prefix_metadata:
            fence_line = line_start + block.marker + cleaned_info

        # Directives are the leading content lines; the first other line, or an environment
        # outside the allowlist, ends them
        metadata: dict[str, str | int] = dict(prefix_metadata)
        content_index = block.opening + 1
        for directive, value in _leading_directives(lines, block):
            if directive == "environment" and allowed_environments is not None and value not in allowed_environments:
                metadata["disallowed_environment"] = value
                metadata["line"] = content_index + 1
                break
            metadata[directive] = value
            content_index += 1

        if metadata:
            # A blank line is the bare quote markers behind a block quote, and empty otherwise
            blank_line = block.quote.rstrip()
            spaced = bool(block.quote) or not (is_shallow_indent(block.indent) and output and output[-1].strip())
            if spaced and (block.quote or (output and output[-1].strip())):
                output.append(blank_line)

            # A fence of one to three columns right under a line of text is usually a tight list item's. There
            # Python-Markdown ends the item at a blank line, so the marker goes without one, at four columns,
            # where it is the item's own text
            marker_start = line_start if spaced else "    "
            output.append(f"{marker_start}{encode_marker(MARKER_NAME, metadata)}")
            if spaced and line_start:
                output.append(blank_line)
        output.append(fence_line)
        output.extend(lines[content_index : block.closing + 1])
        cursor = block.closing + 1

        # Under a list item, a line right after the fence would join the fence's paragraph in Python-Markdown
        # (a "- next" item vanishes into it), so a marked fence ends in a blank line there too, and so does
        # the item text after it, before the first less indented line
        if (
            metadata
            and block.indent
            and not block.quote
            and not is_shallow_indent(block.indent)
            and cursor < len(lines)
            and lines[cursor].strip()
        ):
            output.append("")
            if (text_end := item_text_end(lines, cursor, block.indent)) is not None:
                text_ends.add(text_end)

    _copy_text(output, lines[cursor:], cursor, text_ends)
    return output


def _copy_text(output: list[str], text_lines: list[str], start: int, text_ends: set[int]) -> None:
    """Copy the lines between two fences, with a blank line before each line that ends a loose item's text.

    :param output: The lines written so far, extended in place.
    :param text_lines: The source lines to copy.
    :param start: The source index of the first of them.
    :param text_ends: The source indexes that get a blank line before them unless one is there.
    """
    for line_index, line in enumerate(text_lines, start):
        if line_index in text_ends and output[-1].strip():
            output.append("")
        output.append(line)


def expand_source(text: str, options: Mapping[str, object] | None = None) -> str:
    """Extract fence directives and emit mw-fence marker comments in raw source.

    Used by the ``mw pre`` CLI stage. When ``options`` carries an
    ``allowed_environments`` list, ``[environment ...]`` directives outside it are left
    unextracted, matching the in-process ``allowed_environments`` config option.

    :param text: The source text.
    :param options: The fence option table from config, or ``None`` for no restriction.
    :returns: The text with directives replaced by mw-fence marker comments.
    :raises OptionError: If an option is invalid (see :func:`read_options`).
    """
    return "\n".join(_expand_lines(text.split("\n"), read_options(options).allowed_environments))


class FenceOptions(BaseModel):
    """Validated fence options.

    :ivar allowed_environments: Environment names to honor, or ``None`` to honor every one.
    :ivar label_class: CSS class for the label div.
    :ivar secondary_label_class: CSS class for the secondary label div.
    """

    model_config = ConfigDict(frozen=True)

    allowed_environments: list[str] | None = None
    label_class: str = DEFAULT_LABEL_CLASS
    secondary_label_class: str = DEFAULT_SECONDARY_LABEL_CLASS


def read_options(options: Mapping[str, object] | None) -> FenceOptions:
    """Read and validate a fence option table.

    Shared by both stage functions, the in-process extension, and config validation, so every
    path applies the same rules. An omitted or ``None`` key takes its default. A list names
    exactly the environments it holds, so an empty one allows none and emits a :class:`ConfigWarning`.

    :param options: The fence option table (config table or extension configs), or ``None``.
    :returns: The validated options.
    :raises OptionError: If ``allowed_environments`` is not a list of names, or a label class is not
        a string of class tokens.
    """
    table = options or {}

    # allowed_environments: omitted (None or the in-process sentinel) allows every environment
    environments = table.get("allowed_environments")
    if environments is _ALL_ENVIRONMENTS:
        environments = None
    if environments is not None and (
        not isinstance(environments, list) or not all(isinstance(item, str) for item in environments)
    ):
        raise OptionError("'allowed_environments' must be a list of environment names")
    if environments == []:
        warnings.warn(
            "fence 'allowed_environments' is empty, so every [environment ...] directive is left as text;"
            " omit the key to allow every environment",
            ConfigWarning,
            stacklevel=1,
        )

    # Label classes: omitted takes the default, anything else must be a string
    label_classes: dict[str, str] = {}
    for key, default in (
        ("label_class", DEFAULT_LABEL_CLASS),
        ("secondary_label_class", DEFAULT_SECONDARY_LABEL_CLASS),
    ):
        value = table.get(key)
        if value is None:
            value = default
        if not isinstance(value, str):
            raise OptionError(f"'{key}' must be a string")
        if not CLASS_TOKENS_RE.fullmatch(value):
            raise OptionError(f"'{key}' must be space-separated class tokens of letters, digits, '-', and '_'")
        label_classes[key] = value

    return FenceOptions(
        allowed_environments=environments,
        label_class=label_classes["label_class"],
        secondary_label_class=label_classes["secondary_label_class"],
    )


class FencePreprocessor(Preprocessor):
    """Extract directives and prefix flags from fenced code blocks.

    :param md: The Markdown instance.
    :param options: The validated fence options.
    """

    def __init__(self, md: Markdown, options: FenceOptions) -> None:
        super().__init__(md)
        self.options = options

    def run(self, lines: list[str]) -> list[str]:
        """Process lines, extracting fence directives and injecting metadata comments.

        :param lines: Source lines to process.
        :returns: Modified lines with directives replaced by metadata comments.
        """
        expanded = "\n".join(_expand_lines(lines, self.options.allowed_environments))
        source_lines: list[str] = getattr(self.md, "markwright_source_lines", lines)
        return rebase_marker_lines(source_lines, lines, expanded, (MARKER_NAME,)).split("\n")


class FenceMarker(BaseModel):
    """A validated v1 mw-fence marker payload.

    Strict, so a field of the wrong type fails validation instead of being coerced; unknown
    fields are ignored, so a newer marker's additions do not stop its v1 fields from applying.

    :ivar version: The payload version, ``1``.
    :ivar label: The label text, if the author set one.
    :ivar secondary_label: The secondary label text, if set.
    :ivar environment: The environment name, if set.
    :ivar prefix_type: The line-prefix style, if set.
    :ivar prefix_value: The rendered prefix, absent for ``line_numbers``.
    :ivar disallowed_environment: The name of an ``[environment ...]`` directive outside the allowlist.
    :ivar line: The source line of that directive, 1-based.
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="ignore")

    version: int
    label: str | None = None
    secondary_label: str | None = None
    environment: str | None = None
    prefix_type: Literal["line_numbers", "command", "super_user", "custom_prefix"] | None = None
    prefix_value: str | None = None
    disallowed_environment: str | None = None
    line: int | None = None


def _apply_marker(
    rendered_html: str,
    diagnostics: list[Diagnostic] | None,
    label_class: str,
    secondary_label_class: str,
) -> str:
    """Style code blocks from their mw-fence marker comments, validating each marker.

    Each marker styles the first ``<pre>`` and ``<code>`` that follow it, before the next
    marker. A marker is skipped (and optionally reported) when its payload is invalid (see
    :func:`decode_marker`) or no code block follows it. A recognized marker comment is always
    removed from the output.

    :param rendered_html: Rendered HTML containing mw-fence marker comments.
    :param diagnostics: Optional list collecting diagnostics; ``None`` drops them.
    :param label_class: CSS class for the label div.
    :param secondary_label_class: CSS class for the secondary label div.
    :returns: HTML with label divs, environment classes, and line prefixes injected.
    """
    tokens = tokenize(rendered_html)
    edits: list[tuple[int, int, str]] = []
    for marker_comment in find_markers(MARKER_NAME, rendered_html, tokens):
        comment = tokens[marker_comment.token_index]

        # The marker's block is everything up to the next marker
        block = tokens[marker_comment.token_index + 1 : marker_comment.block_end]
        pre_tag = next((token for token in block if token.kind == "start" and token.tag == "pre"), None)
        code_tag = next((token for token in block if token.kind == "start" and token.tag == "code"), None)

        try:
            marker = decode_marker(MARKER_NAME, marker_comment.raw_payload, FenceMarker)
            if pre_tag is None and code_tag is None:
                raise InvalidMarkerError(f"Skipping {MARKER_NAME} marker with no following code block", "no-target")
        except InvalidMarkerError as skipped:
            if diagnostics is not None:
                diagnostics.append(skipped_diagnostic("fence", skipped))
            edits.append((comment.start, comment.end, ""))
            continue

        if marker.disallowed_environment is not None and diagnostics is not None:
            directive = f"[environment {marker.disallowed_environment}]"
            where = f" on line {marker.line}" if marker.line is not None else ""
            diagnostics.append(
                Diagnostic(
                    extension="fence",
                    line=marker.line,
                    directive=directive,
                    reason="disallowed-environment",
                    message=f"Leaving {directive}{where} in the code: the environment is not in allowed_environments",
                )
            )

        # Replace the comment with the label div (or nothing)
        label_html = ""
        if marker.label is not None:
            label_text = html.escape(marker.label)
            label_html = f'<div class="{label_class}" title="{label_text}">{label_text}</div>\n'
        edits.append((comment.start, comment.end, label_html))

        # Prefix and environment classes go in front of the <pre>'s existing classes
        added_classes = []
        if marker.prefix_type is not None:
            added_classes.append(f"prefixed {marker.prefix_type}")
        if marker.environment is not None:
            added_classes.append(f"environment-{re.sub(r'[^a-zA-Z0-9-]', '', marker.environment)}")
        if pre_tag is not None and added_classes:
            edits.append((pre_tag.start, pre_tag.end, add_classes(pre_tag, " ".join(added_classes))))

        # The secondary label opens the <code>; line prefixes wrap its content
        if code_tag is not None:
            code_inner = ""
            if marker.secondary_label is not None:
                secondary_text = html.escape(marker.secondary_label)
                code_inner = f'<div class="{secondary_label_class}" title="{secondary_text}">{secondary_text}</div>'
            code_close = next(
                (
                    token
                    for token in tokens
                    if token.kind == "end" and token.tag == "code" and token.start >= code_tag.end
                ),
                None,
            )
            if marker.prefix_type is not None and code_close is not None:
                code_content = rendered_html[code_tag.end : code_close.start]
                code_inner += _wrap_lines_with_prefix(code_content, marker.prefix_type, marker.prefix_value or "")
                edits.append((code_tag.end, code_close.start, code_inner))
            elif code_inner:
                edits.append((code_tag.end, code_tag.end, code_inner))

    return apply_edits(rendered_html, edits)


def apply_html(
    rendered_html: str, diagnostics: list[Diagnostic] | None = None, options: Mapping[str, object] | None = None
) -> str:
    """Style code blocks from their mw-fence marker comments.

    Used by the ``mw post`` CLI stage. Markers are validated and skipped fail-soft;
    pass a ``diagnostics`` list to collect why.

    :param rendered_html: Rendered HTML containing mw-fence marker comments.
    :param diagnostics: Optional list collecting diagnostics; ``None`` drops them.
    :param options: The fence option table from config; its label classes style the label divs.
    :returns: HTML with label divs, environment classes, and line prefixes injected.
    :raises OptionError: If an option is invalid (see :func:`read_options`).
    """
    fence_options = read_options(options)
    return _apply_marker(rendered_html, diagnostics, fence_options.label_class, fence_options.secondary_label_class)


class FencePostprocessor(Postprocessor):
    """Inject label HTML and line prefixes based on metadata comments.

    :param md: The Markdown instance.
    :param options: The validated fence options.
    """

    def __init__(self, md: Markdown, options: FenceOptions) -> None:
        super().__init__(md)
        self.options = options

    def run(self, text: str) -> str:
        """Process rendered HTML, replacing metadata comments with label elements and prefixes.

        :param text: Rendered HTML string.
        :returns: Modified HTML with label divs, environment classes, and line prefixes injected.
        """
        diagnostics: list[Diagnostic] = []
        rendered = _apply_marker(
            text,
            diagnostics,
            self.options.label_class,
            self.options.secondary_label_class,
        )
        for diagnostic in diagnostics:
            report(self.md, diagnostic)
        return rendered


class FenceExtension(ReportingExtension):
    """Python-Markdown extension for fence labels, environments, and prefixes.

    :param \\*\\*kwargs: Configuration options passed to the extension.
    """

    def __init__(self, **kwargs: object) -> None:
        self.config: dict[str, list[object]] = {
            "label_class": [DEFAULT_LABEL_CLASS, "CSS class for the label div"],
            "secondary_label_class": [DEFAULT_SECONDARY_LABEL_CLASS, "CSS class for the secondary label div"],
            "allowed_environments": [
                _ALL_ENVIRONMENTS,
                "Allowed environment names; omit to allow all, an empty list allows none",
            ],
        }
        super().__init__(**kwargs)

    def extendMarkdown(self, md: Markdown) -> None:  # noqa: N802 - Python-Markdown's hook name
        """Register the fence preprocessor and postprocessor.

        Options are read here rather than at construction, so a ``setConfig`` call made
        after construction still applies.

        :param md: The Markdown instance to extend.
        :raises OptionError: If an option is invalid (see :func:`read_options`).
        """
        options = read_options(self.getConfigs())
        self.attach_reporting(md)
        preprocessor = FencePreprocessor(md, options)
        md.preprocessors.register(preprocessor, "mw-fence-pre", 40)

        postprocessor = FencePostprocessor(md, options)
        md.postprocessors.register(postprocessor, "mw-fence-post", 25)


def makeExtension(**kwargs: object) -> FenceExtension:  # noqa: N802 - Python-Markdown's loader name
    """Create and return the FenceExtension instance.

    :param \\*\\*kwargs: Configuration options.
    :returns: A configured FenceExtension.
    """
    return FenceExtension(**kwargs)
