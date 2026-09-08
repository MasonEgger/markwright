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

from markdown import Markdown
from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor
from markdown.preprocessors import Preprocessor

MARKER_NAME = "mw-fence"
MARKER_VERSION = 1
DEFAULT_LABEL_CLASS = "code-label"
DEFAULT_SECONDARY_LABEL_CLASS = "secondary-code-label"

FENCE_RE = re.compile(r"^(`{3,}|~{3,})")
LABEL_RE = re.compile(r"^\[label (.+)\]$")
SECONDARY_LABEL_RE = re.compile(r"^\[secondary_label (.+)\]$")
ENVIRONMENT_RE = re.compile(r"^\[environment (.+)\]$")
COMMENT_RE = re.compile(rf"<!-- {MARKER_NAME}:(.*?) -->")
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


_LINE_SPAN_OPEN = '<span class="line"'
_SPAN_TAG_RE = re.compile(r"<(/?)span\b[^>]*>")


def _split_line_spans(code_content: str) -> list[str]:
    """Split Chroma-wrapped code into one string per ``<span class="line">`` block.

    :param code_content: Rendered code containing ``<span class="line">`` line wrappers.
    :returns: One balanced ``<span class="line">...</span>`` string per line.
    """
    lines: list[str] = []
    cursor = 0
    while True:
        start = code_content.find(_LINE_SPAN_OPEN, cursor)
        if start == -1:
            break
        depth = 0
        end = len(code_content)
        for tag_match in _SPAN_TAG_RE.finditer(code_content, start):
            depth += -1 if tag_match.group(1) else 1
            if depth == 0:
                end = tag_match.end()
                break
        lines.append(code_content[start:end])
        cursor = end
    return lines


def _split_rendered_lines(code_content: str) -> list[str]:
    """Split rendered code content into visual lines for prefix wrapping.

    Pygments-style highlighters emit flat, newline-delimited lines, so a split on
    newlines is correct. Chroma (Hugo) wraps each line in ``<span class="line">...
    </span>`` with the newline inside the span; splitting that on newlines would cut
    a line span in half and emit a spurious empty prefixed line, so its line spans
    are split on their own boundaries instead.

    :param code_content: The raw content between <code> and </code> tags.
    :returns: One string per visual line.
    """
    if _LINE_SPAN_OPEN in code_content:
        return _split_line_spans(code_content)
    flat = code_content[:-1] if code_content.endswith("\n") else code_content
    return flat.split("\n")


def _wrap_lines_with_prefix(code_content: str, prefix_metadata: dict[str, str]) -> str:
    """Wrap each code line in <li> elements with data-prefix attributes inside an <ol>.

    :param code_content: The raw content between <code> and </code> tags.
    :param prefix_metadata: Metadata dict containing prefix_type and optionally prefix_value.
    :returns: The content wrapped in <ol><li data-prefix="..."> elements.
    """
    prefix_type = prefix_metadata["prefix_type"]
    prefix_value = prefix_metadata.get("prefix_value", "")

    code_lines = _split_rendered_lines(code_content)
    wrapped_lines: list[str] = []

    for line_index, line_text in enumerate(code_lines):
        current_prefix = str(line_index + 1) if prefix_type == "line_numbers" else prefix_value
        escaped_prefix = html.escape(current_prefix)
        wrapped_lines.append(f'<li data-prefix="{escaped_prefix}">{line_text}\n</li>')

    return "<ol>" + "".join(wrapped_lines) + "</ol>\n"


def _expand_lines(lines: list[str], allowed_environments: list[str] | None) -> list[str]:
    """Extract fence directives and prefix flags, inserting the mw-fence marker comment.

    Shared by the in-process preprocessor and the ``mw pre`` stage function.

    :param lines: Source lines to process.
    :param allowed_environments: Allowed environment names; an empty list or ``None`` allows all.
    :returns: Modified lines with directives replaced by mw-fence marker comments.
    """
    output: list[str] = []
    line_index = 0
    while line_index < len(lines):
        fence_match = FENCE_RE.match(lines[line_index])
        if not fence_match:
            output.append(lines[line_index])
            line_index += 1
            continue

        fence_marker = fence_match.group(1)
        fence_char = fence_marker[0]
        fence_len = len(fence_marker)
        fence_line = lines[line_index]

        # Parse prefix flags from the info string (text after the fence markers)
        info_string = fence_line[fence_len:].strip()
        cleaned_info, prefix_metadata = _parse_prefix_from_info(info_string)

        # Reconstruct the fence line with cleaned info (prefix flags removed, language kept)
        if prefix_metadata:
            fence_line = fence_marker + cleaned_info if cleaned_info else fence_marker

        # Scan content lines for directives
        metadata: dict[str, str] = {}
        metadata.update(prefix_metadata)
        content_lines: list[str] = []
        scan_index = line_index + 1
        directive_zone = True
        while scan_index < len(lines):
            # Check for closing fence
            close_match = FENCE_RE.match(lines[scan_index])
            if (
                close_match
                and close_match.group(1)[0] == fence_char
                and len(close_match.group(1)) >= fence_len
                and lines[scan_index].strip() == close_match.group(1)
            ):
                break

            if directive_zone:
                stripped_line = lines[scan_index].strip()
                label_match = LABEL_RE.match(stripped_line)
                secondary_match = SECONDARY_LABEL_RE.match(stripped_line)
                environment_match = ENVIRONMENT_RE.match(stripped_line)

                if label_match:
                    metadata["label"] = label_match.group(1)
                    scan_index += 1
                    continue
                elif secondary_match:
                    metadata["secondary_label"] = secondary_match.group(1)
                    scan_index += 1
                    continue
                elif environment_match:
                    env_name = environment_match.group(1)
                    if not allowed_environments or env_name in allowed_environments:
                        metadata["environment"] = env_name
                        scan_index += 1
                        continue
                    else:
                        directive_zone = False
                else:
                    directive_zone = False

            content_lines.append(lines[scan_index])
            scan_index += 1

        if metadata:
            payload: dict[str, object] = {"version": MARKER_VERSION}
            payload.update(metadata)
            output.append(f"<!-- {MARKER_NAME}:{_encode_marker_payload(payload)} -->")

        output.append(fence_line)
        output.extend(content_lines)

        # Append closing fence if found
        if scan_index < len(lines):
            output.append(lines[scan_index])
            scan_index += 1

        line_index = scan_index
        continue

    return output


def expand_source(text: str) -> str:
    """Extract fence directives and emit mw-fence marker comments in raw source.

    Used by the ``mw pre`` CLI stage. Environments are not restricted (the
    allow-list is an in-process configuration option only).

    :param text: The source text.
    :returns: The text with directives replaced by mw-fence marker comments.
    """
    return "\n".join(_expand_lines(text.split("\n"), None))


class FencePreprocessor(Preprocessor):
    """Extract directives and prefix flags from fenced code blocks.

    :param md: The Markdown instance.
    :param extension: The parent FenceExtension instance.
    """

    def __init__(self, md: Markdown, extension: FenceExtension) -> None:
        super().__init__(md)
        self.extension = extension

    def run(self, lines: list[str]) -> list[str]:
        """Process lines, extracting fence directives and injecting metadata comments.

        :param lines: Source lines to process.
        :returns: Modified lines with directives replaced by metadata comments.
        """
        return _expand_lines(lines, self.extension.getConfig("allowed_environments"))


CODE_TAG_RE = re.compile(r"<code[^>]*>")
CODE_CLOSE_RE = re.compile(r"</code>")
PRE_TAG_RE = re.compile(r"<pre[^>]*>")


def _add_pre_classes(text: str, search_start: int, css_classes: str) -> str:
    """Add CSS classes to the <pre> tag nearest after search_start.

    :param text: The full HTML string.
    :param search_start: Position to start searching from.
    :param css_classes: Space-separated CSS class string to add.
    :returns: Modified HTML with classes added to <pre>.
    """
    pre_match = PRE_TAG_RE.search(text, search_start)
    if pre_match:
        pre_tag = pre_match.group(0)
        if 'class="' in pre_tag:
            new_pre_tag = pre_tag.replace('class="', f'class="{css_classes} ')
        else:
            new_pre_tag = pre_tag.replace("<pre", f'<pre class="{css_classes}"')
        text = text[: pre_match.start()] + new_pre_tag + text[pre_match.end() :]
    return text


def _apply_marker(
    rendered_html: str,
    warnings: list[str] | None,
    label_class: str,
    secondary_label_class: str,
) -> str:
    """Style code blocks from their mw-fence marker comments, validating each marker.

    A marker is skipped (and optionally warned about) when its JSON is malformed,
    its version is unsupported, or no code block follows it. The recognized marker
    comment is always removed from the output.

    :param rendered_html: Rendered HTML containing mw-fence marker comments.
    :param warnings: Optional list to collect skip reasons; ``None`` suppresses warnings.
    :param label_class: CSS class for the label div.
    :param secondary_label_class: CSS class for the secondary label div.
    :returns: HTML with label divs, environment classes, and line prefixes injected.
    """
    text = rendered_html
    for match in reversed(list(COMMENT_RE.finditer(text))):
        raw_payload = match.group(1)
        comment_start = match.start()
        comment_end = match.end()

        try:
            metadata = json.loads(raw_payload)
        except json.JSONDecodeError:
            if warnings is not None:
                warnings.append(f"Skipping malformed {MARKER_NAME} marker: {raw_payload!r}")
            text = text[:comment_start] + text[comment_end:]
            continue

        version = metadata.get("version")
        if version != MARKER_VERSION:
            if warnings is not None:
                warnings.append(f"Skipping {MARKER_NAME} marker with unsupported version {version!r}")
            text = text[:comment_start] + text[comment_end:]
            continue

        if PRE_TAG_RE.search(text, comment_end) is None and CODE_TAG_RE.search(text, comment_end) is None:
            if warnings is not None:
                warnings.append(f"Skipping {MARKER_NAME} marker with no following code block")
            text = text[:comment_start] + text[comment_end:]
            continue

        label_html = ""
        if "label" in metadata:
            label_text = html.escape(metadata["label"])
            label_html = f'<div class="{label_class}" title="{label_text}">{label_text}</div>\n'

        # Replace the comment with the label div (or empty string)
        text = text[:comment_start] + label_html + text[comment_end:]

        # Add environment class to <pre>
        if "environment" in metadata:
            env_name = re.sub(r"[^a-zA-Z0-9-]", "", metadata["environment"])
            env_class = f"environment-{env_name}"
            text = _add_pre_classes(text, comment_start, env_class)

        # Add prefix classes to <pre> and wrap code lines
        if "prefix_type" in metadata:
            prefix_type = metadata["prefix_type"]
            prefix_classes = f"prefixed {prefix_type}"
            text = _add_pre_classes(text, comment_start, prefix_classes)

            # Find <code>...</code> block and wrap lines
            code_open_match = CODE_TAG_RE.search(text, comment_start)
            if code_open_match:
                code_close_match = CODE_CLOSE_RE.search(text, code_open_match.end())
                if code_close_match:
                    code_content = text[code_open_match.end() : code_close_match.start()]
                    wrapped_content = _wrap_lines_with_prefix(code_content, metadata)
                    text = text[: code_open_match.end()] + wrapped_content + text[code_close_match.start() :]

        if "secondary_label" in metadata:
            secondary_text = html.escape(metadata["secondary_label"])
            secondary_html = f'<div class="{secondary_label_class}" title="{secondary_text}">{secondary_text}</div>'

            # Find the first <code...> tag after where the comment was
            code_match = CODE_TAG_RE.search(text, comment_start)
            if code_match:
                insert_pos = code_match.end()
                text = text[:insert_pos] + secondary_html + text[insert_pos:]

    return text


def apply_html(rendered_html: str, warnings: list[str] | None = None) -> str:
    """Style code blocks from their mw-fence marker comments.

    Used by the ``mw post`` CLI stage and the in-process postprocessor. Markers are
    validated and skipped fail-soft; pass a ``warnings`` list to collect skip reasons.

    :param rendered_html: Rendered HTML containing mw-fence marker comments.
    :param warnings: Optional list to collect skip reasons; ``None`` suppresses warnings.
    :returns: HTML with label divs, environment classes, and line prefixes injected.
    """
    return _apply_marker(rendered_html, warnings, DEFAULT_LABEL_CLASS, DEFAULT_SECONDARY_LABEL_CLASS)


class FencePostprocessor(Postprocessor):
    """Inject label HTML and line prefixes based on metadata comments.

    :param md: The Markdown instance.
    :param extension: The parent FenceExtension instance.
    """

    def __init__(self, md: Markdown, extension: FenceExtension) -> None:
        super().__init__(md)
        self.extension = extension

    def run(self, text: str) -> str:
        """Process rendered HTML, replacing metadata comments with label elements and prefixes.

        :param text: Rendered HTML string.
        :returns: Modified HTML with label divs, environment classes, and line prefixes injected.
        """
        return _apply_marker(
            text,
            None,
            self.extension.getConfig("label_class"),
            self.extension.getConfig("secondary_label_class"),
        )


class FenceExtension(Extension):
    """Python-Markdown extension for fence labels, environments, and prefixes.

    :param \\*\\*kwargs: Configuration options passed to the extension.
    """

    def __init__(self, **kwargs: object) -> None:
        self.config: dict[str, list[object]] = {
            "label_class": ["code-label", "CSS class for the label div"],
            "secondary_label_class": ["secondary-code-label", "CSS class for the secondary label div"],
            "allowed_environments": [[], "List of allowed environment names (empty = allow all)"],
        }
        super().__init__(**kwargs)

    def extendMarkdown(self, md: Markdown) -> None:
        """Register the fence preprocessor and postprocessor.

        :param md: The Markdown instance to extend.
        """
        preprocessor = FencePreprocessor(md, self)
        md.preprocessors.register(preprocessor, "mw-fence-pre", 40)

        postprocessor = FencePostprocessor(md, self)
        md.postprocessors.register(postprocessor, "mw-fence-post", 25)


def makeExtension(**kwargs: object) -> FenceExtension:
    """Create and return the FenceExtension instance.

    :param \\*\\*kwargs: Configuration options.
    :returns: A configured FenceExtension.
    """
    return FenceExtension(**kwargs)
