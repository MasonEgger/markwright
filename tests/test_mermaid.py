# ABOUTME: Tests for the mermaid fence extension.
# Validates the pre-stage conversion, escaping, untouched fences, indentation, and the in-process render.

from __future__ import annotations

import markdown

from markwright.mermaid import expand_source

DIAGRAM = "```mermaid\ngraph LR\n    A --> B\n```"
EXPECTED = '<pre class="mermaid">graph LR\n    A --&gt; B\n</pre>'


def render_mermaid(source: str) -> str:
    """Render Markdown source with superfences, highlight, and the mermaid extension loaded.

    :param source: Markdown source text.
    :returns: Rendered HTML string.
    """
    md = markdown.Markdown(extensions=["pymdownx.superfences", "pymdownx.highlight", "markwright.mermaid"])
    return md.convert(source)


class TestMermaidExpandSource:
    """Tests for the pre-stage conversion."""

    def test_backtick_fence(self) -> None:
        assert expand_source(DIAGRAM) == EXPECTED

    def test_tilde_fence(self) -> None:
        assert expand_source("~~~mermaid\ngraph LR\n    A --> B\n~~~") == EXPECTED

    def test_source_is_escaped_and_otherwise_intact(self) -> None:
        source = '```mermaid\nA["x & y"] --> B\n\n  C\n```'
        assert expand_source(source) == '<pre class="mermaid">A["x &amp; y"] --&gt; B\n\n  C\n</pre>'

    def test_other_fences_untouched(self) -> None:
        source = "```python\nx = 1\n```\n\n```\nplain\n```"
        assert expand_source(source) == source

    def test_prose_is_preserved(self) -> None:
        assert expand_source(f"Intro\n\n{DIAGRAM}\n\nOutro") == f"Intro\n\n{EXPECTED}\n\nOutro"

    def test_label_line_stays_diagram_text(self) -> None:
        result = expand_source("```mermaid\n[label a]\ngraph LR\n```")
        assert result == '<pre class="mermaid">[label a]\ngraph LR\n</pre>'

    def test_indented_fence_keeps_its_indent(self) -> None:
        source = "- item\n\n    ```mermaid\n    graph LR\n        A --> B\n    ```"
        expected = '- item\n\n    <pre class="mermaid">graph LR\n        A --&gt; B\n    </pre>'
        assert expand_source(source) == expected

    def test_unclosed_fence_unchanged(self) -> None:
        source = "```mermaid\ngraph LR"
        assert expand_source(source) == source


class TestMermaidInProcess:
    """Tests for the Python-Markdown preprocessor."""

    def test_render_is_a_raw_pre_block(self) -> None:
        result = render_mermaid(DIAGRAM)
        assert result == EXPECTED
        assert "<code" not in result
        assert "<span" not in result


class TestMermaidInBlockBody:
    """A diagram nested four columns deep is stashed in-process, so it is not wrapped in a paragraph."""

    def test_nested_diagram_is_not_wrapped_in_a_paragraph(self) -> None:
        md = markdown.Markdown(extensions=["admonition", "markwright.mermaid"])

        html = md.convert("!!! note\n\n    ```mermaid\n    graph TD\n      A-->B\n    ```\n\n    after\n")

        assert '<pre class="mermaid">graph TD\n  A--&gt;B\n</pre>\n<p>after</p>' in html


class TestMermaidPlaceholderLine:
    """A source line that looks like a deferred-diagram placeholder is plain text."""

    def test_a_literal_placeholder_line_passes_through(self) -> None:
        md = markdown.Markdown(extensions=["markwright.mermaid"])

        html = md.convert("mw-mermaid-pending-0\n\nmw-mermaid-pending-99999999999\n")

        assert html == "<p>mw-mermaid-pending-0</p>\n<p>mw-mermaid-pending-99999999999</p>"

    def test_a_literal_placeholder_line_beside_a_nested_diagram_is_not_replaced(self) -> None:
        md = markdown.Markdown(extensions=["admonition", "markwright.mermaid"])

        html = md.convert("mw-mermaid-pending-0\n\n!!! note\n\n    ```mermaid\n    graph TD\n    ```\n")

        assert html.count('<pre class="mermaid">') == 1
        assert "<p>mw-mermaid-pending-0</p>" in html

    def test_both_extension_orders_render_a_nested_diagram_the_same(self) -> None:
        source = "!!! note\n\n    ```mermaid\n    graph TD\n    ```\n"
        fenced_first = markdown.Markdown(extensions=["pymdownx.superfences", "admonition", "markwright.mermaid"])
        mermaid_first = markdown.Markdown(extensions=["markwright.mermaid", "admonition", "pymdownx.superfences"])

        assert fenced_first.convert(source) == mermaid_first.convert(source)
