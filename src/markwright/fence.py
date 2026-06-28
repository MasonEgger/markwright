# ABOUTME: Fence extension adding labels, environments, and line prefixes to code blocks.
# Coordinates a Preprocessor and Postprocessor for all fence enhancements.

from __future__ import annotations

import html
import json
import re

from markdown import Markdown
from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor
from markdown.preprocessors import Preprocessor

FENCE_RE = re.compile(r"^(`{3,}|~{3,})")
LABEL_RE = re.compile(r"^\[label (.+)\]$")
SECONDARY_LABEL_RE = re.compile(r"^\[secondary_label (.+)\]$")
ENVIRONMENT_RE = re.compile(r"^\[environment (.+)\]$")
COMMENT_RE = re.compile(r"<!-- do-fence:(.*?) -->")
CUSTOM_PREFIX_RE = re.compile(r"^custom_prefix\((.+)\)$")


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


def _wrap_lines_with_prefix(code_content: str, prefix_metadata: dict[str, str]) -> str:
    """Wrap each code line in <li> elements with data-prefix attributes inside an <ol>.

    :param code_content: The raw content between <code> and </code> tags.
    :param prefix_metadata: Metadata dict containing prefix_type and optionally prefix_value.
    :returns: The content wrapped in <ol><li data-prefix="..."> elements.
    """
    prefix_type = prefix_metadata["prefix_type"]
    prefix_value = prefix_metadata.get("prefix_value", "")

    # Split content into lines. The content typically ends with \n before </code>,
    # so we strip the trailing newline before splitting, then re-add structure.
    if code_content.endswith("\n"):
        code_content = code_content[:-1]

    code_lines = code_content.split("\n")
    wrapped_lines: list[str] = []

    for line_index, line_text in enumerate(code_lines):
        current_prefix = str(line_index + 1) if prefix_type == "line_numbers" else prefix_value
        escaped_prefix = html.escape(current_prefix)
        wrapped_lines.append(f'<li data-prefix="{escaped_prefix}">{line_text}\n</li>')

    return "<ol>" + "".join(wrapped_lines) + "</ol>\n"


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
                        allowed = self.extension.getConfig("allowed_environments")
                        if not allowed or env_name in allowed:
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
                output.append(f"<!-- do-fence:{json.dumps(metadata)} -->")

            output.append(fence_line)
            output.extend(content_lines)

            # Append closing fence if found
            if scan_index < len(lines):
                output.append(lines[scan_index])
                scan_index += 1

            line_index = scan_index
            continue

        return output


CODE_TAG_RE = re.compile(r"<code[^>]*>")
CODE_CLOSE_RE = re.compile(r"</code>")
PRE_TAG_RE = re.compile(r"<pre[^>]*>")


class FencePostprocessor(Postprocessor):
    """Inject label HTML and line prefixes based on metadata comments.

    :param md: The Markdown instance.
    :param extension: The parent FenceExtension instance.
    """

    def __init__(self, md: Markdown, extension: FenceExtension) -> None:
        super().__init__(md)
        self.extension = extension

    def _add_pre_classes(self, text: str, search_start: int, css_classes: str) -> str:
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

    def run(self, text: str) -> str:
        """Process rendered HTML, replacing metadata comments with label elements and prefixes.

        :param text: Rendered HTML string.
        :returns: Modified HTML with label divs, environment classes, and line prefixes injected.
        """
        for match in reversed(list(COMMENT_RE.finditer(text))):
            metadata = json.loads(match.group(1))
            label_html = ""
            comment_start = match.start()
            comment_end = match.end()

            if "label" in metadata:
                label_text = html.escape(metadata["label"])
                label_class = self.extension.getConfig("label_class")
                label_html = f'<div class="{label_class}" title="{label_text}">{label_text}</div>\n'

            # Replace the comment with the label div (or empty string)
            text = text[:comment_start] + label_html + text[comment_end:]

            # Add environment class to <pre>
            if "environment" in metadata:
                env_name = re.sub(r"[^a-zA-Z0-9-]", "", metadata["environment"])
                env_class = f"environment-{env_name}"
                text = self._add_pre_classes(text, comment_start, env_class)

            # Add prefix classes to <pre> and wrap code lines
            if "prefix_type" in metadata:
                prefix_type = metadata["prefix_type"]
                prefix_classes = f"prefixed {prefix_type}"
                text = self._add_pre_classes(text, comment_start, prefix_classes)

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
                secondary_class = self.extension.getConfig("secondary_label_class")
                secondary_html = f'<div class="{secondary_class}" title="{secondary_text}">{secondary_text}</div>'

                # Find the first <code...> tag after where the comment was
                code_match = CODE_TAG_RE.search(text, comment_start)
                if code_match:
                    insert_pos = code_match.end()
                    text = text[:insert_pos] + secondary_html + text[insert_pos:]

        return text


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
        md.preprocessors.register(preprocessor, "do-fence-pre", 40)

        postprocessor = FencePostprocessor(md, self)
        md.postprocessors.register(postprocessor, "do-fence-post", 25)


def makeExtension(**kwargs: object) -> FenceExtension:
    """Create and return the FenceExtension instance.

    :param \\*\\*kwargs: Configuration options.
    :returns: A configured FenceExtension.
    """
    return FenceExtension(**kwargs)
