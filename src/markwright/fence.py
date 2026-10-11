# ABOUTME: Fence extension adding labels, environments, and line prefixes to code blocks.
# Coordinates a Preprocessor and Postprocessor and exposes the mw-fence stage functions.

# Fence directives travel from the pre stage to the post stage as an HTML comment
# placed immediately before the fence: ``<!-- mw-fence:{JSON} -->``. This comment is
# the only cross-tool contract, so its payload is versioned. The v1 schema is::
#
#     {
#       "version": 1,             # integer, the only required field
#       "label": "deploy.sh",     # optional
#       "secondary_label": "...", # optional
#       "environment": "local",   # optional
#       "prefix_type": "command", # optional: line_numbers | command | super_user | custom_prefix
#       "prefix_value": "$"       # optional: rendered prefix, absent for line_numbers
#     }
#
# Every field other than ``version`` is optional and present only when the author used
# that directive. The post stage applies whatever fields it recognizes and skips a
# marker (fail-soft, optionally warning) when the JSON is malformed, the version is
# unsupported, or no code block follows.
#
# The serialized payload is comment-safe: ``_encode_marker_payload`` escapes every
# literal ``<``/``>`` in the JSON to its ``\uXXXX`` form before it is written between
# ``<!--`` and ``-->``, so a directive value containing ``-->`` can never close the
# comment early. The transform is self-reversing: ``json.loads`` restores the
# characters on read, so the post stage needs no manual decode step.

from __future__ import annotations

import html
import json
import re
import warnings
from typing import TYPE_CHECKING, Literal

from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor
from markdown.preprocessors import Preprocessor
from pydantic import BaseModel, ConfigDict, ValidationError

from markwright._diagnostics import ConfigWarning, OptionError
from markwright._fences import find_fenced_blocks
from markwright._html import HtmlToken, apply_edits, render_start_tag, tokenize

if TYPE_CHECKING:
    from collections.abc import Mapping

    from markdown import Markdown

MARKER_NAME = "mw-fence"
MARKER_VERSION = 1
DEFAULT_LABEL_CLASS = "code-label"
DEFAULT_SECONDARY_LABEL_CLASS = "secondary-code-label"

# The in-process default for allowed_environments, meaning "omitted". Python-Markdown runs a None
# default through parseBoolValue, which would turn a list into a bool, so a sentinel stands in.
_ALL_ENVIRONMENTS = object()

LABEL_RE = re.compile(r"^\[label (.+)\]$")
SECONDARY_LABEL_RE = re.compile(r"^\[secondary_label (.+)\]$")
ENVIRONMENT_RE = re.compile(r"^\[environment (.+)\]$")
MARKER_COMMENT_RE = re.compile(rf"<!-- {MARKER_NAME}:(.*?) -->")
CUSTOM_PREFIX_RE = re.compile(r"^custom_prefix\((.+)\)$")


def _encode_marker_payload(payload: dict[str, object]) -> str:
    """Serialize a marker payload for safe embedding inside an HTML comment.

    ``json.dumps`` leaves ``<`` and ``>`` as literal characters, so a directive
    value containing ``-->`` would close the comment early and inject live
    markup. Escaping both to their JSON ``\\uXXXX`` forms removes every literal
    ``<``/``>`` from the comment body, so ``-->`` and ``<!--`` can never form
    inside it. ``json.loads`` restores the original characters on read, so this
    is self-reversing and requires no read-side change.

    :param payload: The marker payload to serialize.
    :returns: JSON text with every literal ``<`` and ``>`` unicode-escaped.
    """
    return json.dumps(payload).replace("<", "\\u003c").replace(">", "\\u003e")


def _parse_prefix_from_info(info_string: str) -> tuple[str, dict[str, str]]:
    """Parse prefix flags from a fence info string and return cleaned info + prefix metadata.

    :param info_string: The raw info string after the opening fence markers.
    :returns: Tuple of (cleaned info string, prefix metadata dict).
    """
    parts = info_string.split(",")
    prefix_metadata: dict[str, str] = {}
    remaining_parts: list[str] = []
    add_bash = False

    for part in parts:
        stripped_part = part.strip()
        if stripped_part == "line_numbers":
            prefix_metadata["prefix_type"] = "line_numbers"
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

    cleaned_info = ",".join(remaining_parts)
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
        code_lines = code_content.removesuffix("\n").split("\n")

    wrapped_lines: list[str] = []
    for line_index, line_text in enumerate(code_lines):
        current_prefix = str(line_index + 1) if prefix_type == "line_numbers" else prefix_value
        wrapped_lines.append(f'<li data-prefix="{html.escape(current_prefix)}">{line_text}\n</li>')
    return "<ol>" + "".join(wrapped_lines) + "</ol>\n"


def _expand_lines(lines: list[str], allowed_environments: list[str] | None) -> list[str]:
    """Extract fence directives and prefix flags, inserting the mw-fence marker comment.

    Shared by the in-process preprocessor and the ``mw pre`` stage function. Fences are found
    by the shared CommonMark scanner, so indented fences and fences in list items count. A marker
    for an indented fence is written at the fence's indentation and followed by a blank line,
    so it stays inside the list item and renders as its own block.

    :param lines: Source lines to process.
    :param allowed_environments: Allowed environment names, or ``None`` to allow every environment;
        an empty list allows none.
    :returns: Modified lines with directives replaced by mw-fence marker comments.
    """
    output: list[str] = []
    cursor = 0
    for block in find_fenced_blocks(lines):
        output.extend(lines[cursor : block.opening])

        # Parse prefix flags from the info string; the fence line keeps the language
        cleaned_info, prefix_metadata = _parse_prefix_from_info(block.info.strip())
        fence_line = lines[block.opening]
        if prefix_metadata:
            fence_line = block.indent + block.marker + cleaned_info

        # Directives are the leading content lines; the first other line ends them
        metadata: dict[str, str] = dict(prefix_metadata)
        content_index = block.opening + 1
        while content_index < block.closing:
            stripped_line = lines[content_index].strip()
            if label_match := LABEL_RE.match(stripped_line):
                metadata["label"] = label_match.group(1)
            elif secondary_match := SECONDARY_LABEL_RE.match(stripped_line):
                metadata["secondary_label"] = secondary_match.group(1)
            elif (environment_match := ENVIRONMENT_RE.match(stripped_line)) and (
                allowed_environments is None or environment_match.group(1) in allowed_environments
            ):
                metadata["environment"] = environment_match.group(1)
            else:
                break
            content_index += 1

        if metadata:
            payload: dict[str, object] = {"version": MARKER_VERSION, **metadata}
            output.append(f"{block.indent}<!-- {MARKER_NAME}:{_encode_marker_payload(payload)} -->")
            if block.indent:
                output.append("")
        output.append(fence_line)
        output.extend(lines[content_index : block.closing + 1])
        cursor = block.closing + 1

    output.extend(lines[cursor:])
    return output


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
    :raises OptionError: If ``allowed_environments`` is not a list of names, or a label class is not a string.
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
        return _expand_lines(lines, self.options.allowed_environments)


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
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="ignore")

    version: int
    label: str | None = None
    secondary_label: str | None = None
    environment: str | None = None
    prefix_type: Literal["line_numbers", "command", "super_user", "custom_prefix"] | None = None
    prefix_value: str | None = None


class _InvalidMarkerError(Exception):
    """A marker the post stage skips fail-soft; the message is the skip reason."""


def _parse_marker(raw_payload: str) -> FenceMarker:
    """Decode and validate a marker comment's JSON payload.

    :param raw_payload: The text between ``mw-fence:`` and the comment's end.
    :returns: The validated marker.
    :raises _InvalidMarkerError: If the JSON is malformed, not an object, an unsupported version, or
        has a field of the wrong type.
    """
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as decode_error:
        raise _InvalidMarkerError(f"Skipping malformed {MARKER_NAME} marker: {raw_payload!r}") from decode_error
    if not isinstance(payload, dict):
        raise _InvalidMarkerError(f"Skipping {MARKER_NAME} marker whose payload is not an object: {raw_payload!r}")
    if payload.get("version") != MARKER_VERSION:
        raise _InvalidMarkerError(f"Skipping {MARKER_NAME} marker with unsupported version {payload.get('version')!r}")
    try:
        return FenceMarker.model_validate(payload)
    except ValidationError as validation_error:
        invalid_fields = ", ".join(str(error["loc"][0]) for error in validation_error.errors())
        raise _InvalidMarkerError(
            f"Skipping {MARKER_NAME} marker with invalid fields ({invalid_fields}): {raw_payload!r}"
        ) from validation_error


def _apply_marker(
    rendered_html: str,
    skip_reasons: list[str] | None,
    label_class: str,
    secondary_label_class: str,
) -> str:
    """Style code blocks from their mw-fence marker comments, validating each marker.

    Each marker styles the first ``<pre>`` and ``<code>`` that follow it, before the next
    marker. A marker is skipped (and optionally reported) when its payload is invalid (see
    :func:`_parse_marker`) or no code block follows it. A recognized marker comment is always
    removed from the output.

    :param rendered_html: Rendered HTML containing mw-fence marker comments.
    :param skip_reasons: Optional list collecting skip reasons; ``None`` drops them.
    :param label_class: CSS class for the label div.
    :param secondary_label_class: CSS class for the secondary label div.
    :returns: HTML with label divs, environment classes, and line prefixes injected.
    """
    tokens = tokenize(rendered_html)
    markers = [
        (token_index, comment_match)
        for token_index, token in enumerate(tokens)
        if token.kind == "comment"
        and (comment_match := MARKER_COMMENT_RE.fullmatch(rendered_html, token.start, token.end))
    ]

    edits: list[tuple[int, int, str]] = []
    for marker_number, (token_index, comment_match) in enumerate(markers):
        comment = tokens[token_index]

        # The marker's block is everything up to the next marker
        block_end = markers[marker_number + 1][0] if marker_number + 1 < len(markers) else len(tokens)
        block = tokens[token_index + 1 : block_end]
        pre_tag = next((token for token in block if token.kind == "start" and token.tag == "pre"), None)
        code_tag = next((token for token in block if token.kind == "start" and token.tag == "code"), None)

        try:
            marker = _parse_marker(comment_match.group(1))
            if pre_tag is None and code_tag is None:
                raise _InvalidMarkerError(f"Skipping {MARKER_NAME} marker with no following code block")
        except _InvalidMarkerError as skipped:
            if skip_reasons is not None:
                skip_reasons.append(str(skipped))
            edits.append((comment.start, comment.end, ""))
            continue

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
            edits.append((pre_tag.start, pre_tag.end, _with_classes(pre_tag, " ".join(added_classes))))

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


def _with_classes(tag: HtmlToken, added_classes: str) -> str:
    """Rebuild a start tag with classes placed in front of its existing ones.

    :param tag: The start tag token.
    :param added_classes: Space-separated classes to add.
    :returns: The rebuilt start tag; a tag without a ``class`` attribute gets one first.
    """
    existing_classes = tag.attribute("class")
    if existing_classes is None:
        return render_start_tag(tag.tag, (("class", added_classes), *tag.attrs))
    attrs = tuple(
        (name, f"{added_classes} {existing_classes}" if name == "class" else value) for name, value in tag.attrs
    )
    return render_start_tag(tag.tag, attrs)


def apply_html(
    rendered_html: str, skip_reasons: list[str] | None = None, options: Mapping[str, object] | None = None
) -> str:
    """Style code blocks from their mw-fence marker comments.

    Used by the ``mw post`` CLI stage. Markers are validated and skipped fail-soft;
    pass a ``skip_reasons`` list to collect why.

    :param rendered_html: Rendered HTML containing mw-fence marker comments.
    :param skip_reasons: Optional list collecting skip reasons; ``None`` drops them.
    :param options: The fence option table from config; its label classes style the label divs.
    :returns: HTML with label divs, environment classes, and line prefixes injected.
    :raises OptionError: If an option is invalid (see :func:`read_options`).
    """
    fence_options = read_options(options)
    return _apply_marker(rendered_html, skip_reasons, fence_options.label_class, fence_options.secondary_label_class)


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
        return _apply_marker(
            text,
            None,
            self.options.label_class,
            self.options.secondary_label_class,
        )


class FenceExtension(Extension):
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
