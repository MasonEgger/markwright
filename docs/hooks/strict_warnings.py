# ABOUTME: MkDocs hook that turns each markwright RenderWarning into a WARNING log record.
# With it, `mkdocs build --strict` fails when a page holds a markwright diagnostic.
from __future__ import annotations

import logging
import warnings
from typing import TYPE_CHECKING, TextIO

from markwright import RenderWarning

if TYPE_CHECKING:
    from mkdocs.config.defaults import MkDocsConfig
    from mkdocs.structure.files import Files
    from mkdocs.structure.pages import Page

_LOGGER = logging.getLogger("mkdocs.plugins.markwright")
_current_page: list[str] = [""]


def on_page_markdown(markdown: str, page: Page, config: MkDocsConfig, files: Files) -> str:  # noqa: ARG001
    """Remember the page being rendered so a diagnostic can name it.

    :param markdown: The page source, returned unchanged.
    :param page: The page about to be converted.
    :param config: The MkDocs configuration.
    :param files: The site's files.
    :returns: ``markdown`` unchanged.
    """
    _current_page[0] = page.file.src_uri
    return markdown


def on_startup(command: str, dirty: bool) -> None:  # noqa: ARG001
    """Route every ``RenderWarning`` to the ``mkdocs.plugins.markwright`` logger.

    MkDocs counts a WARNING record under ``--strict``; a Python warning logged at
    INFO is not counted. Other warning categories go to the previous handler.

    :param command: The MkDocs command running (``build``, ``serve``, or ``gh-deploy``).
    :param dirty: Whether this is a dirty (incremental) build.
    """
    previous_handler = warnings.showwarning

    def show_warning(
        message: Warning | str,
        category: type[Warning],
        filename: str,
        lineno: int,
        file: TextIO | None = None,
        line: str | None = None,
    ) -> None:
        if issubclass(category, RenderWarning):
            _LOGGER.warning("%s: %s", _current_page[0], message)
            return
        previous_handler(message, category, filename, lineno, file, line)

    warnings.simplefilter("always", RenderWarning)
    warnings.showwarning = show_warning
