# ABOUTME: CodePen embed extension for Python-Markdown.
# Converts [codepen USER HASH flags...] syntax to CodePen embed HTML with script injection.

from __future__ import annotations

import html
import re
import urllib.parse

from markdown import Markdown
from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor
from markdown.preprocessors import Preprocessor

CODEPEN_RE = re.compile(r"^\[codepen\s+(\S+)\s+(\S+)((?:\s+(?:lazy|light|dark|editable|html|css|js|result|\d+))*)\]$")

TAB_PRIORITY = ["html", "css", "js"]

DEFAULT_HEIGHT = 256

CODEPEN_SCRIPT = (
    '<script async defer src="https://static.codepen.io/assets/embed/ei.js" type="text/javascript"></script>'
)


def _parse_flags(raw_flags: str) -> dict[str, str | int | bool]:
    """Parse space-separated CodePen flags into a settings dictionary.

    :param raw_flags: Raw space-separated flags string.
    :returns: Dictionary with theme, height, tab, lazy, and editable settings.
    """
    flags = raw_flags.split()

    # Theme: dark wins if both present
    theme = "dark" if "dark" in flags else "light"

    # Height: first integer found, or default
    height = DEFAULT_HEIGHT
    for flag in flags:
        if flag.isdigit():
            height = int(flag)
            break

    # Lazy and editable
    lazy = "lazy" in flags
    editable = "editable" in flags

    # Tab: priority is html > css > js; result can combine with another tab
    selected_tab = ""
    for tab_name in TAB_PRIORITY:
        if tab_name in flags:
            selected_tab = tab_name
            break

    has_result = "result" in flags

    if selected_tab and has_result:
        tab = f"{selected_tab},result"
    elif selected_tab:
        tab = selected_tab
    else:
        tab = "result"

    return {
        "theme": theme,
        "height": height,
        "tab": tab,
        "lazy": lazy,
        "editable": editable,
    }


class CodePenPreprocessor(Preprocessor):
    """Replace [codepen ...] lines with CodePen embed HTML.

    :param md: The Markdown instance.
    """

    found: bool

    def __init__(self, md: Markdown) -> None:
        """Initialize the preprocessor.

        :param md: The Markdown instance.
        """
        super().__init__(md)
        self.found = False

    def run(self, lines: list[str]) -> list[str]:
        """Process lines, replacing CodePen embed syntax with HTML.

        :param lines: Source lines to process.
        :returns: Modified lines with CodePen embeds replaced by HTML.
        """
        self.found = False
        output: list[str] = []

        for line in lines:
            stripped_line = line.strip()
            codepen_match = CODEPEN_RE.match(stripped_line)
            if codepen_match:
                self.found = True
                user = codepen_match.group(1)
                hash_id = codepen_match.group(2)
                raw_flags = codepen_match.group(3).strip()
                settings = _parse_flags(raw_flags)

                escaped_user = html.escape(str(user))
                escaped_hash = html.escape(str(hash_id))
                encoded_user = urllib.parse.quote(str(user), safe="")
                encoded_hash = urllib.parse.quote(str(hash_id), safe="")
                height = settings["height"]
                theme = settings["theme"]
                tab = settings["tab"]

                lazy_attr = ' data-preview="true"' if settings["lazy"] else ""
                editable_attr = ' data-editable="true"' if settings["editable"] else ""

                embed_html = (
                    f'<p class="codepen" data-height="{height}"'
                    f' data-theme-id="{theme}" data-default-tab="{tab}"'
                    f' data-user="{escaped_user}" data-slug-hash="{escaped_hash}"'
                    f"{lazy_attr}{editable_attr}"
                    f' style="height: {height}px; box-sizing: border-box;'
                    f" display: flex; align-items: center; justify-content: center;"
                    f' border: 2px solid; margin: 1em 0; padding: 1em;">\n'
                    f"    <span>See the Pen"
                    f' <a href="https://codepen.io/{encoded_user}/pen/{encoded_hash}">'
                    f"{escaped_hash} by {escaped_user}</a>"
                    f' (<a href="https://codepen.io/{encoded_user}">@{escaped_user}</a>)'
                    f" on <a href='https://codepen.io'>CodePen</a>.</span>\n"
                    f"</p>"
                )
                output.append(self.md.htmlStash.store(embed_html))
            else:
                output.append(line)

        return output


class CodePenPostprocessor(Postprocessor):
    """Append the CodePen embed script tag once if any embeds were found.

    :param md: The Markdown instance.
    :param preprocessor: The CodePenPreprocessor to check for found embeds.
    """

    def __init__(self, md: Markdown, preprocessor: CodePenPreprocessor) -> None:
        """Initialize the postprocessor with a reference to the preprocessor.

        :param md: The Markdown instance.
        :param preprocessor: The CodePenPreprocessor to check for found embeds.
        """
        super().__init__(md)
        self.preprocessor = preprocessor

    def run(self, text: str) -> str:
        """Append script tag if CodePen embeds were found.

        :param text: Rendered HTML content.
        :returns: HTML with CodePen script appended if needed.
        """
        if self.preprocessor.found:
            return text + "\n" + CODEPEN_SCRIPT
        return text


class CodePenExtension(Extension):
    """Python-Markdown extension for CodePen embeds.

    :param \\*\\*kwargs: Configuration options passed to the extension.
    """

    def extendMarkdown(self, md: Markdown) -> None:
        """Register the CodePen preprocessor and postprocessor.

        :param md: The Markdown instance to extend.
        """
        preprocessor = CodePenPreprocessor(md)
        postprocessor = CodePenPostprocessor(md, preprocessor)
        md.preprocessors.register(preprocessor, "do-codepen", 20)
        md.postprocessors.register(postprocessor, "do-codepen-script", 15)


def makeExtension(**kwargs: object) -> CodePenExtension:
    """Create and return the CodePenExtension instance.

    :param \\*\\*kwargs: Configuration options.
    :returns: A configured CodePenExtension.
    """
    return CodePenExtension(**kwargs)
