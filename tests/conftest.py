# ABOUTME: Shared pytest fixtures for markwright extension tests.
# Provides pre-configured Markdown instances that mirror the real site stack.

import markdown
import pytest


@pytest.fixture
def md_with_superfences() -> markdown.Markdown:
    """Return a Markdown instance with pymdownx.superfences and pymdownx.highlight.

    Mirrors the real site configuration so our extensions can be tested
    alongside the stack they'll run with in production.
    """
    return markdown.Markdown(
        extensions=["pymdownx.superfences", "pymdownx.highlight"],
        extension_configs={"pymdownx.highlight": {"pygments_lang_class": True}},
    )
