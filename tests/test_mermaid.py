# ABOUTME: Tests for the mermaid fence extension.
# Validates the pre-stage conversion, escaping, untouched fences, indentation, and the in-process render.

from __future__ import annotations

import markdown
import pytest

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


def render_pipeline(source: str) -> str:
    """Render the ``mw pre`` output of ``source`` through a generic stack with no markwright extensions.

    :param source: Markdown source text.
    :returns: Rendered HTML string.
    """
    md = markdown.Markdown(extensions=["pymdownx.superfences", "pymdownx.highlight"])
    return md.convert(expand_source(source))


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

    @pytest.mark.parametrize(
        ("before", "indent"),
        [
            ("", " "),
            ("", "   "),
            ("- item\n\n", " "),
            ("- item\n\n", "  "),
            ("1. item\n\n", "    "),
            ("- item\n\n", "      "),
            ("1. - a\n\n", "      "),
            ("- 1. a\n\n", "     "),
            ("100. - a\n\n", "        "),
            ("Term\n: def\n", "  "),
            ("[^1]: note\n\n", "    "),
            ("!!! note\n    - a\n\n", "        "),
        ],
        ids=[
            "top-level-one-column",
            "top-level-three-columns",
            "short-of-the-item-text",
            "at-the-item-text",
            "past-the-item-text",
            "four-columns-past-the-item-text",
            "item-opened-on-an-ordered-marker-line",
            "item-opened-on-a-bullet-marker-line",
            "item-opened-on-a-wide-marker-line",
            "definition-body",
            "footnote-body",
            "list-in-an-admonition",
        ],
    )
    def test_every_line_of_the_block_takes_the_fence_indent(self, before: str, indent: str) -> None:
        source = f"{before}{indent}```mermaid\n{indent}graph LR\n{indent}    A --> B\n{indent}```"
        expected = f'{before}{indent}<pre class="mermaid">graph LR\n{indent}    A --&gt; B\n{indent}</pre>'
        assert expand_source(source) == expected

    @pytest.mark.parametrize(
        ("before", "indent"), [("", ""), ("", "  "), ("- item\n\n", "  "), ("1. - a\n\n", "      ")]
    )
    def test_blank_diagram_line_stays_empty(self, before: str, indent: str) -> None:
        source = f"{before}{indent}```mermaid\n{indent}graph LR\n\n{indent}  A-->B\n{indent}```"
        expected = f'{before}{indent}<pre class="mermaid">graph LR\n\n{indent}  A--&gt;B\n{indent}</pre>'
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


class TestMermaidInListItem:
    """A diagram four columns deep in a list item renders in-process as one block with its exact text."""

    def test_list_item_diagram_is_one_pre_not_wrapped_in_a_paragraph(self) -> None:
        html = render_mermaid("- item\n\n    ```mermaid\n    graph LR\n      A-->B\n    ```\n\n- next\n")

        assert html.count('<pre class="mermaid">') == 1
        assert '<pre class="mermaid">graph LR\n  A--&gt;B\n</pre>' in html
        assert "<p><pre" not in html

    def test_blank_line_in_a_list_item_diagram_does_not_split_it(self) -> None:
        html = render_mermaid("- item\n\n    ```mermaid\n    graph LR\n\n      A-->B\n    ```\n")

        assert html.count('<pre class="mermaid">') == 1
        assert "graph LR\n\n  A--&gt;B\n</pre>" in html

    def test_top_level_diagram_is_unchanged(self) -> None:
        assert render_mermaid(DIAGRAM) == EXPECTED


class TestMermaidUnderAListItemBelowFourColumns:
    """A fence fewer than four columns deep under a list item renders in-process as it does through the pipeline."""

    def test_text_line_after_the_fence_is_its_own_paragraph(self) -> None:
        html = render_mermaid("- item\n\n  ```mermaid\n  graph LR\n    A-->B\n  ```\nafter\n")

        assert html == (
            '<ul>\n<li>item</li>\n</ul>\n<pre class="mermaid">graph LR\n    A--&gt;B\n  </pre>\n<p>after</p>'
        )

    def test_rule_line_after_the_fence_does_not_turn_the_diagram_into_a_heading(self) -> None:
        html = render_mermaid("- item\n\n  ```mermaid\n  graph LR\n    A-->B\n  ```\n---\n")

        assert html == '<ul>\n<li>item</li>\n</ul>\n<pre class="mermaid">graph LR\n    A--&gt;B\n  </pre>\n<hr />'

    @pytest.mark.parametrize(
        "source",
        [
            "- item\n  ```mermaid\n  graph LR\n\n    A-->B\n  ```\n",
            "- item\n  ```mermaid\n  graph LR\n    A-->B\n  ```\nafter\n",
            "1. item\n\n   ```mermaid\n   graph LR\n     A-->B\n   ```\nafter\n",
            "- a\n  - b\n\n  ```mermaid\n  graph LR\n    A-->B\n  ```\nafter\n",
            "- item\n\n  ```mermaid\n  graph LR\n  ```\n  ```mermaid\n  graph TD\n  ```\nafter\n",
            "- item\n\n* * *\n  ```mermaid\n  graph LR\n    A-->B\n  ```\nafter\n",
        ],
        ids=["tight", "tight-then-text", "ordered-three", "nested-item", "second-of-two", "below-a-rule-line"],
    )
    def test_in_process_render_equals_the_pipeline(self, source: str) -> None:
        in_process = render_mermaid(source)

        assert in_process == render_pipeline(source)
        assert in_process.count('<pre class="mermaid">') == source.count("```mermaid")
        assert "<p><pre" not in in_process


class TestMermaidBesideText:
    """A diagram under no list item or opener renders in-process as it does through the pipeline, beside any text."""

    @pytest.mark.parametrize(
        ("source", "expected"),
        [
            ("para\n```mermaid\ngraph LR\n```\n", '<p>para</p>\n<pre class="mermaid">graph LR\n</pre>'),
            ("```mermaid\ngraph LR\n```\npara\n", '<pre class="mermaid">graph LR\n</pre>\n<p>para</p>'),
            (
                "a | b\n--|--\n1 | 2\n```mermaid\ngraph LR\n```\n",
                '<p>a | b\n--|--\n1 | 2</p>\n<pre class="mermaid">graph LR\n</pre>',
            ),
            ("# Head\n```mermaid\ngraph LR\n```\n- item\n", None),
        ],
    )
    def test_top_level_diagram_beside_text(self, source: str, expected: str | None) -> None:
        in_process = render_mermaid(source)

        assert in_process == render_pipeline(source)
        if expected is not None:
            assert in_process == expected

    @pytest.mark.parametrize("indent", [" ", "  ", "   "])
    def test_indented_top_level_diagram_matches_the_pipeline_and_keeps_its_indent(self, indent: str) -> None:
        fence = f"{indent}```mermaid\n{indent}graph LR\n{indent}  A-->B\n{indent}```\n"
        for source in (
            f"para\n{fence}after\n",
            f"para\n\n{fence}\nafter\n",
            fence,
            fence.replace("graph LR", "graph LR\n"),
        ):
            assert render_mermaid(source) == render_pipeline(source)
            assert "<p><pre" not in render_mermaid(source)
            assert f"\n{indent}  A--&gt;B\n{indent}</pre>" in render_mermaid(source)


class TestMermaidInAnOpenerBody:
    """A diagram under a list inside a block opener's body stays inside the list when Python-Markdown renders it."""

    def test_pipeline_closes_the_diagram_before_the_list(self) -> None:
        source = "!!! note\n    - a\n\n        ```mermaid\n        graph LR\n\n          A-->B\n        ```\n"

        md = markdown.Markdown(extensions=["pymdownx.superfences", "admonition"])
        html = md.convert(expand_source(source))

        assert html.index("</pre>") < html.index("</ul>")
