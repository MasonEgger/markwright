# ABOUTME: Cross-stage round-trip integration tests for the mw pipeline.
# Proves run_pre | external-render | run_post equals the in-process markwright render.

from __future__ import annotations

import itertools
import re
from typing import TYPE_CHECKING

import markdown
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from markwright import Diagnostic, RenderWarning, registry
from markwright.codepen import CODEPEN_SCRIPT
from markwright.instagram import INSTAGRAM_SCRIPT
from markwright.twitter import TWITTER_SCRIPT

if TYPE_CHECKING:
    from pathlib import Path

# A fixture exercising every feature in one document: a labeled command fence
# (label directive + command prefix), an environment fence, a line-numbered
# fence, an in-code highlight marker, two embeds (one pre-only, one with a post
# script), and a prose highlight marker.
FIXTURE = """\
```command
[label deploy.sh]
[environment local]
echo deploy
```

```python,line_numbers
first = 1
second = 2
```

A fenced highlight:

```python
value = "<^>token<^>"
```

[youtube dQw4w9WgXcQ]

[codepen jcoulterdesign npyBME]

Prose with a <^>marked<^> word.

[button primary /start Get started]

[lightbox /a.png A diagram]

```mermaid
graph LR
    A --> B
```

[grid cards]

- card one
- card two

[annotate]
```python
x = 1  # (1)!
```

1. The first note.

[annotate]
Prose with a marker (1).

1. A prose note.
"""

_PRE_BLOCK_RE = re.compile(r"<pre.*?</pre>", re.DOTALL)


def stub_render(markdown_text: str) -> str:
    """Render Markdown through a generic stack with no markwright extensions.

    Stands in for an external renderer that preserves raw HTML and HTML comments
    but knows nothing about markwright directives. Mirrors the site stack's
    superfences plus pygments configuration so only the markwright stages differ.

    :param markdown_text: Source text, typically the output of :func:`run_pre`.
    :returns: Rendered HTML with markwright markers left intact.
    """
    instance = markdown.Markdown(
        extensions=["pymdownx.superfences", "pymdownx.highlight"],
        extension_configs={"pymdownx.highlight": {"pygments_lang_class": True}},
    )
    return instance.convert(markdown_text)


def in_process_render(markdown_text: str, names: list[str], options: dict[str, dict[str, object]] | None = None) -> str:
    """Render Markdown through the in-process stack the ``mw render`` path builds.

    :param markdown_text: Source text.
    :param names: markwright extension names to load alongside the site stack.
    :param options: Per-extension option tables keyed by extension name, or ``None``.
    :returns: Final HTML with every markwright stage applied in-process.
    """
    markwright_configs = {f"markwright.{name}": table for name, table in (options or {}).items()}
    instance = markdown.Markdown(
        extensions=["pymdownx.superfences", "pymdownx.highlight", *(f"markwright.{name}" for name in names)],
        extension_configs={"pymdownx.highlight": {"pygments_lang_class": True}, **markwright_configs},
    )
    return instance.convert(markdown_text)


def _normalize(html: str) -> str:
    """Drop blank lines outside ``<pre>`` blocks so two renders compare exactly.

    The in-process path stashes embed HTML and restores it verbatim, while the
    round-trip path inlines that HTML and lets the external renderer surround it
    with blank lines between block elements. Those blank lines carry no meaning
    outside ``<pre>`` (where whitespace is significant), so collapsing them lets
    the comparison stay byte-exact on every span, class, attribute, and script
    without coupling to the external renderer's block-spacing.

    :param html: Rendered HTML to normalize.
    :returns: HTML with significant ``<pre>`` whitespace preserved and other blank
        lines removed.
    """
    protected_blocks: list[str] = []

    def _stash(match: re.Match[str]) -> str:
        protected_blocks.append(match.group(0))
        return f"\x00{len(protected_blocks) - 1}\x00"

    protected = _PRE_BLOCK_RE.sub(_stash, html)
    collapsed = "\n".join(line for line in protected.split("\n") if line.strip())
    for index, original_block in enumerate(protected_blocks):
        collapsed = collapsed.replace(f"\x00{index}\x00", original_block)
    return collapsed


class TestRoundTripEquivalence:
    """The pre | external-render | post pipeline reproduces the in-process render."""

    def test_full_feature_pipeline_equals_in_process_render(self) -> None:
        names = list(registry.EXTENSION_NAMES)
        pipeline = registry.run_post(stub_render(registry.run_pre(FIXTURE, names)), names, None)
        in_process = in_process_render(FIXTURE, names)
        assert _normalize(pipeline) == _normalize(in_process)

    def test_pipeline_applies_every_feature(self) -> None:
        # Guard the equivalence test against silently comparing two empty renders:
        # assert each feature actually landed in the round-trip output.
        names = list(registry.EXTENSION_NAMES)
        pipeline = registry.run_post(stub_render(registry.run_pre(FIXTURE, names)), names, None)
        assert '<div class="code-label" title="deploy.sh">deploy.sh</div>' in pipeline
        assert "environment-local" in pipeline
        assert 'data-prefix="1"' in pipeline
        assert "<mark>token</mark>" in pipeline
        assert "<mark>marked</mark>" in pipeline
        assert "youtube.com/embed/dQw4w9WgXcQ" in pipeline
        assert 'class="codepen"' in pipeline
        assert CODEPEN_SCRIPT in pipeline
        assert '<a class="mw-button mw-button-primary" href="/start">Get started</a>' in pipeline
        assert '<a class="mw-lightbox" href="/a.png"><img src="/a.png" alt="A diagram" /></a>' in pipeline
        assert '<pre class="mermaid">graph LR\n    A --&gt; B\n</pre>' in pipeline
        assert '<ul class="mw-grid mw-grid-cards">' in pipeline
        assert '<a class="mw-annotation" href="#mw-annotation-1-1">1</a>' in pipeline
        assert "(1)!" not in pipeline
        assert '<li id="mw-annotation-2-1">A prose note.</li>' in pipeline


class TestRoundTripRawHtml:
    """Embeds inside a raw ``<div>`` with no blank lines render the same in both paths."""

    SOURCE = '<div class="note">\n[youtube dQw4w9WgXcQ]\n[button /start Get started]\n</div>\n'

    def test_both_paths_agree(self) -> None:
        names = ["youtube", "button"]
        pipeline = registry.run_post(stub_render(registry.run_pre(self.SOURCE, names)), names, None)
        in_process = in_process_render(self.SOURCE, names)

        assert _normalize(pipeline) == _normalize(in_process)
        assert "youtube.com/embed/dQw4w9WgXcQ" in in_process
        assert '<a class="mw-button" href="/start">Get started</a>' in in_process


class TestRoundTripIcons:
    """Icon shortcodes expand from a configured pack the same through the pipeline and in-process."""

    def test_pipeline_equals_in_process_render(self, tmp_path: Path) -> None:
        pack = tmp_path / "pack"
        pack.mkdir()
        (pack / "check.svg").write_text('<svg viewBox="0 0 24 24"><path d="M1 1h22v22H1z"/></svg>')
        names = list(registry.EXTENSION_NAMES)
        options: dict[str, dict[str, object]] = {"icons": {"packs": {"demo": str(pack)}}}
        source = "A :demo-check: icon and `:demo-check:` as code.\n"
        pipeline = registry.run_post(stub_render(registry.run_pre(source, names, options)), names, None, options)
        assert pipeline.count('<span aria-hidden="true" class="mw-icon"><svg') == 1
        assert _normalize(pipeline) == _normalize(in_process_render(source, names, options))

    def test_attribute_and_autolink_shortcodes_match_in_process(self, tmp_path: Path) -> None:
        pack = tmp_path / "pack"
        pack.mkdir()
        (pack / "check.svg").write_text('<svg viewBox="0 0 24 24"><path d="M1 1h22v22H1z"/></svg>')
        names = list(registry.EXTENSION_NAMES)
        options: dict[str, dict[str, object]] = {"icons": {"packs": {"demo": str(pack)}}}
        source = 'Prose :demo-check: here, <span title=":demo-check:">x</span>, and <https://x.test/:demo-check:>.\n'
        pipeline = registry.run_post(stub_render(registry.run_pre(source, names, options)), names, None, options)
        assert pipeline.count('<span aria-hidden="true" class="mw-icon"><svg') == 1
        assert _normalize(pipeline) == _normalize(in_process_render(source, names, options))

    def test_shortcodes_beside_directives_and_a_diagram_match_in_process(self, tmp_path: Path) -> None:
        pack = tmp_path / "pack"
        pack.mkdir()
        (pack / "check.svg").write_text('<svg viewBox="0 0 24 24"><path d="M1 1h22v22H1z"/></svg>')
        names = list(registry.EXTENSION_NAMES)
        options: dict[str, dict[str, object]] = {"icons": {"packs": {"demo": str(pack)}}}
        source = (
            "[tab :demo-check: One]\nbody :demo-check:\n[/tab]\n\n"
            "[button https://x.test :demo-check: Go]\n\n"
            "[youtube abc123 :demo-check:]\n\n"
            "```mermaid\ngraph LR\n  A[:demo-check:] --> B\n```\n"
        )
        pipeline = registry.run_post(stub_render(registry.run_pre(source, names, options)), names, None, options)
        assert '<pre class="mermaid">graph LR\n  A[:demo-check:] --&gt; B\n</pre>' in pipeline
        assert _normalize(pipeline) == _normalize(in_process_render(source, names, options))


class TestRoundTripMermaid:
    """A mermaid diagram renders the same through the pipeline and in-process, beside text and indented."""

    @pytest.mark.parametrize(
        "source",
        [
            "para\n```mermaid\ngraph LR\n  A --> B\n```\nafter\n",
            "  ```mermaid\n  graph LR\n  ```\n",
            "para\n   ```mermaid\n   graph LR\n\n     A --> B\n   ```\nafter\n",
        ],
        ids=["beside-text", "indented-two", "indented-three-with-blank-line"],
    )
    def test_pipeline_equals_in_process_render(self, source: str) -> None:
        names = list(registry.EXTENSION_NAMES)
        pipeline = registry.run_post(stub_render(registry.run_pre(source, names)), names)
        assert pipeline.count('<pre class="mermaid">') == 1
        assert _normalize(pipeline) == _normalize(in_process_render(source, names))


class TestRoundTripMermaidInAnItem:
    """Four columns or more under a list item the in-process text is exact; the pipeline keeps what the item leaves."""

    @staticmethod
    def diagram_texts(source: str) -> tuple[list[str], list[str]]:
        """Render ``source`` both ways and read the text of each diagram.

        :param source: Markdown source holding a mermaid fence.
        :returns: The diagram texts of the pipeline render, then of the in-process render.
        """
        names = ["mermaid"]
        pipeline = registry.run_post(stub_render(registry.run_pre(source, names)), names)
        in_process = in_process_render(source, names)
        diagram_re = re.compile(r'<pre class="mermaid">(.*?)</pre>', re.DOTALL)
        return diagram_re.findall(pipeline), diagram_re.findall(in_process)

    def test_fence_at_the_item_column_matches_in_process(self) -> None:
        source = "- item\n\n    ```mermaid\n    mindmap\n      root\n        a\n      b\n    ```\n"
        pipeline_text, in_process_text = self.diagram_texts(source)
        assert pipeline_text == in_process_text == ["mindmap\n  root\n    a\n  b\n"]

    @pytest.mark.parametrize(
        "source",
        [
            "- item\n\n     ```mermaid\n     mindmap\n       root\n         a\n       b\n     ```\n",
            "1. item\n\n     ```mermaid\n     mindmap\n       root\n         a\n       b\n     ```\n",
        ],
        ids=["bullet-five", "ordered-five"],
    )
    def test_fence_one_column_past_the_item_keeps_that_column_in_the_pipeline(self, source: str) -> None:
        pipeline_text, in_process_text = self.diagram_texts(source)
        assert in_process_text == ["mindmap\n  root\n    a\n  b\n"]
        assert pipeline_text == ["mindmap\n   root\n     a\n   b\n "]


class TestRoundTripHighlightEscape:
    """A prose escape reads the same through ``mw pre | render | mw post`` as in-process."""

    @pytest.mark.parametrize(
        "source",
        [
            r"a \<^>x\<^> b",
            r"a \\<^>x<^> b",
            r"a \\\<^>x<^> b",
            r"a \\\\<^>x<^> b",
            r"<^>a \<^> b<^> c",
            r"<^>a\<^> b",
            r"\<^>x<^>",
            r"x \<^>y\<^> and <^>z<^>",
            'See <a title="<^>x<^>" href="/y">link</a> and <^>z<^>.',
            "See <!-- <^>x<^> --> and <^>z<^>.",
            "See <https://e.com/<^>x<^>> and <^>z<^>.",
        ],
    )
    def test_prose_escape_matches_in_process(self, source: str) -> None:
        names = ["highlight"]
        pipeline = registry.run_post(stub_render(registry.run_pre(source, names)), names)
        assert _normalize(pipeline) == _normalize(in_process_render(source, names))

    def test_an_odd_run_is_a_literal_marker_and_an_even_run_is_live(self) -> None:
        names = ["highlight"]
        literal = registry.run_post(stub_render(registry.run_pre(r"a \<^>x\<^> b", names)), names)
        live = registry.run_post(stub_render(registry.run_pre(r"a \\<^>x<^> b", names)), names)
        assert "<mark>" not in literal
        assert "&lt;&#94;&gt;x" in literal
        assert "<mark>x</mark>" in live


# The block starts of both renderers (Python-Markdown and CommonMark), as a line prefix. A raw HTML block start
# (`<div>`, `<!-- `) is left out because it is not highlight pairing: `mw pre` rewrites the text content of an HTML
# block and the in-process path leaves it alone (spec.md, Roadmap Deferred, mw pre parity).
_PAIRING_BLOCK_STARTS = (
    "",
    "- ",
    "* ",
    "+ ",
    "1. ",
    "1) ",
    "- [ ] ",
    "> ",
    "# ",
    "    ",
    "\t",
    "    - ",
    "```",
    "~~~",
    "[x]: ",
    "| ",
    ": ",
    "!!! ",
    "??? ",
    "=== ",
    "---",
)
_INDENTED_STARTS = frozenset({"    ", "\t", "    - "})

# The text of each line, with the pair opening on the first line and closing on the last
_PAIRING_TWO_LINE_TEXTS = (
    ("a <^>b", "c<^> d"),
    ("a <^>b<^> c", "d <^>e<^> f"),
    ("a <^>b `x<^>y` c<^> d", "e <^>f<^> g"),
)
_PAIRING_THREE_LINE_TEXTS = (
    ("a <^>b", "x", "c<^> d"),
    ("a <^>b<^> c", "x <^>y<^> z", "c<^> d"),
)
# A code span that holds a line end, in one paragraph: the continuation lines start no block, since a block
# start inside a code span has no single reading in the two renderers and nobody types one
_PAIRING_CODE_SPAN_TEXTS = (
    ("a <^>b `x", "y` c<^> d"),
    ("a <^>b `x", "y", "z` c<^> d"),
)
_PAIRING_CODE_SPAN_STARTS = ("", "- ", "* ", "+ ", "1. ", "> ", "- [ ] ", "1) ")


def _is_supported_pairing_document(starts: tuple[str, ...], lines: list[str]) -> bool:
    """Report whether a generated document stays inside what the two renderers read alike.

    Left out: indented text straight after a heading line, which CommonMark reads as indented code and
    ``_fences`` reads as prose (code needs a blank line before it there), and a backtick fence opener that
    holds a backtick, which CommonMark does not read as a fence.
    """
    follows_heading = any(
        previous == "# " and start in _INDENTED_STARTS for previous, start in zip(starts, starts[1:], strict=False)
    )
    backtick_in_fence_opener = any(line.startswith("```") and "`" in line[3:] for line in lines)
    return not follows_heading and not backtick_in_fence_opener


def _pairing_documents() -> list[str]:
    """Generate the two-line and three-line documents that join each pair of block starts with each text."""
    documents: list[str] = []
    for (first_text, second_text), first_start, second_start in itertools.product(
        _PAIRING_TWO_LINE_TEXTS, _PAIRING_BLOCK_STARTS, _PAIRING_BLOCK_STARTS
    ):
        lines = [f"{first_start}{first_text}", f"{second_start}{second_text}"]
        if _is_supported_pairing_document((first_start, second_start), lines):
            documents.append("\n".join(lines) + "\n")
    for (first_text, middle_text, last_text), middle_start, last_start in itertools.product(
        _PAIRING_THREE_LINE_TEXTS, _PAIRING_BLOCK_STARTS, _PAIRING_BLOCK_STARTS
    ):
        lines = [first_text, f"{middle_start}{middle_text}", f"{last_start}{last_text}"]
        if _is_supported_pairing_document(("", middle_start, last_start), lines):
            documents.append("\n".join(lines) + "\n")
    for code_span_lines, first_start in itertools.product(_PAIRING_CODE_SPAN_TEXTS, _PAIRING_CODE_SPAN_STARTS):
        documents.append(f"{first_start}{code_span_lines[0]}\n" + "\n".join(code_span_lines[1:]) + "\n")
    return documents


class TestRoundTripHighlightPairing:
    """A prose pair never holds a line end, so every path highlights the same text whatever block starts a line."""

    def test_pipeline_equals_in_process_render_over_generated_documents(self) -> None:
        names = ["highlight"]
        documents = _pairing_documents()

        differing = [
            document
            for document in documents
            if _normalize(registry.run_post(stub_render(registry.run_pre(document, names)), names))
            != _normalize(in_process_render(document, names))
        ]

        assert differing == []
        # The corpus must reach a highlight, or equality proves nothing
        assert any("<mark>" in in_process_render(document, names) for document in documents)

    def test_a_pair_around_a_code_span_is_one_mark_in_both_paths(self) -> None:
        names = ["highlight"]
        document = "a <^>b `x<^>y` c<^> d\n"

        pipeline = registry.run_post(stub_render(registry.run_pre(document, names)), names)

        assert pipeline == in_process_render(document, names)
        assert pipeline.count("<mark>") == 1


class TestRoundTripIdempotency:
    """Running the post stage twice does not double-apply any transform."""

    def test_running_post_twice_is_stable(self) -> None:
        names = list(registry.EXTENSION_NAMES)
        once = registry.run_post(stub_render(registry.run_pre(FIXTURE, names)), names, None)
        twice = registry.run_post(once, names, None)
        assert once == twice
        assert once.count(CODEPEN_SCRIPT) == 1
        assert twice.count(CODEPEN_SCRIPT) == 1

    # A grid shortcut, a paired block grid holding a card whose body is a two-tab set: every
    # construct grid and tabs turn into their own paired markers, so a second pre pass meets them
    # all as markers. The degrade-to-literal problem directives are excluded: a top-level [card]
    # leaves its [/card] a bare directive that re-reports as a stray on a second pass, a literal
    # degradation unrelated to the marker contract.
    _CONTAINER_FIXTURE = (
        "[grid cards 2]\n\n- a\n- b\n\n"
        "[grid]\n\n[card]\n\n[tab One]\n\nx\n\n[/tab]\n\n[tab Two]\n\ny\n\n[/tab]\n\n[/card]\n\n[/grid]\n"
    )

    def test_running_pre_twice_is_stable(self) -> None:
        # Pre stages carry their own marker comments; a second pre pass meets them as markers and
        # must leave them untouched, not re-emit, re-report, or crash on a marker-sourced pair.
        names = list(registry.EXTENSION_NAMES)
        once = registry.run_pre(FIXTURE, names)
        assert registry.run_pre(once, names) == once

    def test_running_pre_twice_is_stable_over_nested_containers(self) -> None:
        names = list(registry.EXTENSION_NAMES)
        once = registry.run_pre(self._CONTAINER_FIXTURE, names)
        assert registry.run_pre(once, names) == once
        # The second pass pairs from the markers but emits nothing new and renders the same.
        twice_post = registry.run_post(stub_render(registry.run_pre(once, names)), names)
        assert twice_post == registry.run_post(stub_render(once), names)


class TestStageOptions:
    """Per-extension config options thread through run_pre the way mw render applies them."""

    _ENV_SOURCE = "```\n[environment production]\necho hi\n```"

    def test_run_pre_without_options_allows_any_environment(self) -> None:
        output = registry.run_pre(self._ENV_SOURCE, ["fence"])
        assert '"environment": "production"' in output

    def test_run_pre_honors_fence_allowed_environments(self) -> None:
        options = {"fence": {"allowed_environments": ["staging"]}}
        output = registry.run_pre(self._ENV_SOURCE, ["fence"], options=options)
        assert '"environment"' not in output

    def test_run_pre_options_leave_extensions_without_options_unaffected(self) -> None:
        options = {"fence": {"allowed_environments": ["staging"]}}
        output = registry.run_pre("[youtube dQw4w9WgXcQ]", ["youtube"], options=options)
        assert "youtube.com/embed/dQw4w9WgXcQ" in output


class TestRoundTripDegradation:
    """A comment-stripping renderer drops fence styling but raises no error."""

    def test_comment_stripping_renderer_degrades_gracefully(self) -> None:
        names = list(registry.EXTENSION_NAMES)
        rendered = stub_render(registry.run_pre(FIXTURE, names))
        comment_stripped = re.sub(r"<!--.*?-->", "", rendered, flags=re.DOTALL)
        degraded = registry.run_post(comment_stripped, names, None)
        # Fence directives travel as HTML comments; without them the fences render
        # unstyled rather than erroring.
        assert "mw-fence" not in degraded
        assert 'class="code-label"' not in degraded
        assert "environment-local" not in degraded
        # Features that do not depend on the comment channel still work.
        assert "youtube.com/embed/dQw4w9WgXcQ" in degraded
        assert "<mark>token</mark>" in degraded
        assert CODEPEN_SCRIPT in degraded
        # The marker-comment extensions degrade; the comment-free ones survive.
        assert "mw-grid" not in degraded
        assert "mw-annotation" not in degraded
        assert 'class="mw-button' in degraded
        assert '<pre class="mermaid">' in degraded


# One of each embed that takes a load option, so every load value runs through both paths.
EMBED_FIXTURE = """\
[youtube dQw4w9WgXcQ]

[codepen jcoulterdesign npyBME]

[twitter MattIPv4/status/1576415168426573825]

[instagram CkQuv3_LRgS]
"""


class TestRoundTripEmbedBlock:
    """An embed is its own block in both paths, beside text, in a tight list item, and in a div."""

    @pytest.mark.parametrize(
        "source",
        [
            "Intro\n[youtube abc]\nOutro *line*\n",
            '<div class="note">\n[youtube abc]\nbeside\n</div>\n',
        ],
        ids=["beside-text", "raw-div"],
    )
    def test_both_paths_agree(self, source: str) -> None:
        names = ["youtube"]
        pipeline = registry.run_post(stub_render(registry.run_pre(source, names)), names, None)

        assert _normalize(pipeline) == _normalize(in_process_render(source, names))

    def test_a_tight_list_item_holding_an_embed_renders_loose_in_both_paths(self) -> None:
        # The stub renderer is Python-Markdown, which wraps an indented raw iframe in a paragraph, so the
        # two outputs are compared on structure; the Hugo integration test covers a CommonMark renderer.
        source = "- item\n    [youtube abc]\n- next\n"
        names = ["youtube"]
        pipeline = registry.run_post(stub_render(registry.run_pre(source, names)), names, None)
        in_process = in_process_render(source, names)

        for html in (pipeline, in_process):
            assert html.count("<li>") == 2
            assert "<p>item</p>" in html
            assert "<p>next</p>" in html
            assert html.count("youtube.com/embed/abc") == 1

    def test_the_item_after_text_that_follows_an_embed_stays_an_item_in_both_paths(self) -> None:
        # Compared on structure, for the stub renderer's paragraph around the iframe (see the test above).
        source = "1. Watch this:\n    [youtube abc]\n    Then run *this* command.\n2. Next\n"
        names = ["youtube"]
        pipeline = registry.run_post(stub_render(registry.run_pre(source, names)), names, None)
        in_process = in_process_render(source, names)

        for html in (pipeline, in_process):
            assert html.count("<li>") == 2
            assert "<p>Then run <em>this</em> command.</p>" in html
            assert "<p>Next</p>" in html


class TestRoundTripMarkedFenceInATightList:
    """A marked fence under a tight list item keeps the list in both paths."""

    SOURCE = "- Run this:\n    ```command\n    ls\n    ```\n- next\n"

    def test_both_paths_agree(self) -> None:
        names = ["fence"]
        pipeline = registry.run_post(stub_render(registry.run_pre(self.SOURCE, names)), names, None)
        in_process = in_process_render(self.SOURCE, names)

        assert _normalize(pipeline) == _normalize(in_process)
        assert in_process.count("<li>") == 2
        assert 'data-prefix="$"' in in_process

    def test_the_item_after_text_that_follows_the_fence_stays_an_item_in_both_paths(self) -> None:
        source = "- Run this:\n    ```command\n    ls\n    ```\n    After.\n- next\n"
        names = ["fence"]
        pipeline = registry.run_post(stub_render(registry.run_pre(source, names)), names, None)
        in_process = in_process_render(source, names)

        assert _normalize(pipeline) == _normalize(in_process)
        assert in_process.count("<li>") == 2
        assert "<p>After.</p>" in in_process


class TestRoundTripPrefixFlagBesideAttribute:
    """A flag beside a highlighter attribute renders the same in both paths."""

    SOURCE = '```command title="x.sh"\nls\n```\n'

    def test_both_paths_agree(self) -> None:
        names = ["fence"]
        pipeline = registry.run_post(stub_render(registry.run_pre(self.SOURCE, names)), names, None)
        in_process = in_process_render(self.SOURCE, names)

        assert _normalize(pipeline) == _normalize(in_process)
        assert 'data-prefix="$"' in in_process
        assert "x.sh" in in_process


class TestRoundTripShallowListItem:
    """A marked fence one to three columns under a list item stays in it, and renders the same in both paths."""

    @pytest.mark.parametrize(
        "source",
        [
            "- Run this:\n  ```command\n  ls\n  ```\n- next\n",
            "1. Run this:\n   ```command\n   ls\n   ```\n2. next\n",
        ],
        ids=["fence-bullet-2", "fence-ordered-3"],
    )
    def test_a_marked_fence_matches_in_both_paths(self, source: str) -> None:
        names = ["fence"]
        pipeline = registry.run_post(stub_render(registry.run_pre(source, names)), names, None)
        in_process = in_process_render(source, names)

        assert _normalize(pipeline) == _normalize(in_process)
        assert in_process.count("<li>") == 2

    # The shallow embed shapes (an embed 1 to 3 columns under a list item) are not compared here: `mw pre` writes
    # blank lines around them, and the stub renderer, Python-Markdown, ends the item at a blank line before a
    # line indented less than four columns. The Decision in spec.md's Embeds entry records the difference.
    # The in-process unit tests in tests/test_youtube.py and the Hugo
    # integration tests in tests/integration/test_hugo_pipeline.py carry them.


class TestRoundTripLoad:
    """The pipeline and the in-process render agree for every load value."""

    @pytest.mark.parametrize(
        "load_by_embed",
        [
            {},
            {"youtube": "eager", "codepen": "eager", "twitter": "eager", "instagram": "eager"},
            {"youtube": "lazy"},
            {"youtube": "click", "codepen": "click", "twitter": "click", "instagram": "click"},
            {"youtube": "lazy", "codepen": "click", "twitter": "eager", "instagram": "click"},
        ],
    )
    def test_pipeline_equals_in_process_render(self, load_by_embed: dict[str, str]) -> None:
        names = list(registry.EXTENSION_NAMES)
        options: dict[str, dict[str, object]] = {name: {"load": load} for name, load in load_by_embed.items()}
        pipeline = registry.run_post(stub_render(registry.run_pre(EMBED_FIXTURE, names, options)), names, None)
        in_process = in_process_render(EMBED_FIXTURE, names, options)
        assert _normalize(pipeline) == _normalize(in_process)

    def test_click_everywhere_injects_no_script(self) -> None:
        names = list(registry.EXTENSION_NAMES)
        options: dict[str, dict[str, object]] = {
            name: {"load": "click"} for name in ("youtube", "codepen", "twitter", "instagram")
        }
        pipeline = registry.run_post(stub_render(registry.run_pre(EMBED_FIXTURE, names, options)), names, None)
        assert pipeline.count('class="mw-embed"') == 4
        assert "<script" not in pipeline

    def test_mixed_page_injects_only_the_eager_embed_script(self) -> None:
        names = list(registry.EXTENSION_NAMES)
        options: dict[str, dict[str, object]] = {"codepen": {"load": "click"}, "instagram": {"load": "click"}}
        pipeline = registry.run_post(stub_render(registry.run_pre(EMBED_FIXTURE, names, options)), names, None)
        assert pipeline.count(TWITTER_SCRIPT) == 1
        assert CODEPEN_SCRIPT not in pipeline
        assert INSTAGRAM_SCRIPT not in pipeline


class TestRoundTripFenceOptions:
    """Fence label classes from config apply the same through the pipeline and in-process."""

    def test_label_classes_match_in_process_render(self) -> None:
        names = list(registry.EXTENSION_NAMES)
        options: dict[str, dict[str, object]] = {
            "fence": {"label_class": "my-label", "secondary_label_class": "my-sub"}
        }
        source = "```\n[label a.sh]\n[secondary_label Output]\necho hi\n```\n"
        pipeline = registry.run_post(stub_render(registry.run_pre(source, names, options)), names, None, options)
        in_process = in_process_render(source, names, options)
        assert 'class="my-label"' in pipeline
        assert 'class="my-sub"' in pipeline
        assert _normalize(pipeline) == _normalize(in_process)


class TestRoundTripBlockQuote:
    """A fence behind a block quote marker renders the same through the pipeline and in-process."""

    def test_alert_fence_matches_in_process_render(self) -> None:
        names = list(registry.EXTENSION_NAMES)
        source = (
            "> [!NOTE]\n> Run this:\n> ```command\n> [label restart.sh]\n"
            "> systemctl restart <^>nginx<^>\n> ```\n> Then check it.\n"
        )
        pipeline = registry.run_post(stub_render(registry.run_pre(source, names)), names, None)
        assert '<div class="code-label" title="restart.sh">restart.sh</div>' in pipeline
        assert '<li data-prefix="$">' in pipeline
        assert "<mark>nginx</mark>" in pipeline
        assert _normalize(pipeline) == _normalize(in_process_render(source, names))


# Plain words for prose, labels, and code; markwright's grammar supplies the structure
_WORDS = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=8)
_PHRASES = st.lists(_WORDS, min_size=1, max_size=4).map(" ".join)


@st.composite
def _prose_block(draw: st.DrawFn) -> str:
    """Draw a paragraph, optionally with a highlighted word."""
    phrase = draw(_PHRASES)
    if draw(st.booleans()):
        return f"{phrase} <^>{draw(_WORDS)}<^> {draw(_PHRASES)}"
    return phrase


@st.composite
def _fence_block(draw: st.DrawFn) -> str:
    """Draw a fenced code block with any mix of directives, a prefix flag, and in-code highlights."""
    fence = draw(st.sampled_from(["```", "````", "~~~"]))
    info = draw(st.sampled_from(["", "python", "bash", "command", "super_user", "line_numbers", "python,line_numbers"]))
    directives = [
        directive
        for directive, include in (
            (f"[label {draw(_WORDS)}.sh]", draw(st.booleans())),
            (f"[secondary_label {draw(_PHRASES)}]", draw(st.booleans())),
            (f"[environment {draw(st.sampled_from(['local', 'staging', 'production']))}]", draw(st.booleans())),
        )
        if include
    ]
    code_lines = draw(st.lists(_PHRASES, min_size=1, max_size=3))
    if draw(st.booleans()):
        code_lines[0] = f"{code_lines[0]} <^>{draw(_WORDS)}<^>"
    return "\n".join([f"{fence}{info}", *directives, *code_lines, fence])


_EMBED_BLOCKS = st.sampled_from(
    [
        "[youtube dQw4w9WgXcQ]",
        "[codepen jcoulterdesign npyBME]",
        "[twitter MattIPv4/status/1576415168426573825]",
        "[instagram CkQuv3_LRgS]",
    ]
)


@st.composite
def _grid_block(draw: st.DrawFn) -> str:
    """Draw a grid shortcut directive followed by a short bullet list."""
    directive = draw(st.sampled_from(["[grid]", "[grid cards]", "[grid 2]", "[grid cards 2]", "[grid 2 cards]"]))
    items = draw(st.lists(_PHRASES, min_size=1, max_size=3))
    return directive + "\n\n" + "\n".join(f"- {item}" for item in items)


@st.composite
def _block_grid(draw: st.DrawFn) -> str:
    """Draw a paired block grid wrapping a prose block and a card with a heading and paragraph."""
    opener = draw(st.sampled_from(["[grid]", "[grid 2]", "[grid cards]", "[grid cards 2]", "[grid 2 cards]"]))
    heading = draw(_WORDS)
    para = draw(_PHRASES)
    card_heading = draw(_WORDS)
    card_para = draw(_PHRASES)
    return f"{opener}\n\n## {heading}\n\n{para}\n\n[card]\n\n### {card_heading}\n\n{card_para}\n\n[/card]\n\n[/grid]"


# Container problems grid leaves literal and reports through an mw-grid-problem marker; the pipeline
# and the in-process render must still agree once the marker is attached and removed.
_CONTAINER_PROBLEMS = st.sampled_from(
    [
        "[card]\n\ninside\n\n[/card]",
        "[/card]",
        "[/grid]",
    ]
)

# Tab containers tabs leaves literal and reports through an mw-tab-problem marker.
_TAB_PROBLEMS = st.sampled_from(
    [
        "[tab Orphan]\n\ninside",
        "[/tab]",
    ]
)


@st.composite
def _tab_set(draw: st.DrawFn) -> str:
    """Draw two or three consecutive tabs that form one set, with prose or code bodies."""
    count = draw(st.integers(min_value=2, max_value=3))
    tabs = []
    for _tab_index in range(count):
        name = draw(_PHRASES)
        body = f"```python\n{draw(_WORDS)} = 1\n```" if draw(st.booleans()) else draw(_PHRASES)
        tabs.append(f"[tab {name}]\n\n{body}\n\n[/tab]")
    return "\n\n".join(tabs)


@st.composite
def _grid_with_tabs(draw: st.DrawFn) -> str:
    """Draw a block grid holding a card whose body is a two-tab set, so containers nest."""
    tab_a = draw(_PHRASES)
    tab_b = draw(_PHRASES)
    body_a = draw(_PHRASES)
    body_b = draw(_PHRASES)
    return (
        "[grid]\n\n[card]\n\n"
        f"[tab {tab_a}]\n\n{body_a}\n\n[/tab]\n\n[tab {tab_b}]\n\n{body_b}\n\n[/tab]\n\n"
        "[/card]\n\n[/grid]"
    )


@st.composite
def _annotate_block(draw: st.DrawFn) -> str:
    """Draw an annotate directive with a prose or code body and its numbered notes."""
    marker = draw(st.integers(min_value=1, max_value=3))
    if draw(st.booleans()):
        body = f"{draw(_PHRASES)} ({marker}) {draw(_PHRASES)}"
    else:
        body = f"```python\n{draw(_WORDS)} = 1  # ({marker})!\n```"
    notes = draw(st.lists(_PHRASES, min_size=1, max_size=3))
    numbered = "\n".join(f"{note_number}. {note}" for note_number, note in enumerate(notes, start=1))
    return f"[annotate]\n{body}\n\n{numbered}"


_DIRECTIVE_BLOCKS = st.sampled_from(
    [
        "[button primary /start Get started]",
        "[button /docs Read the docs]",
        "[lightbox /a.png A diagram]",
        "```mermaid\ngraph LR\n    A --> B\n```",
    ]
)


@st.composite
def _directive_in_fence(draw: st.DrawFn) -> str:
    """Draw one directive line wrapped in a fenced code block."""
    directive = draw(
        st.sampled_from(
            [
                "[button primary /start Get started]",
                "[lightbox /a.png A diagram]",
                "[youtube dQw4w9WgXcQ]",
                "[grid]",
                "[annotate]",
            ]
        )
    )
    return f"```\n{directive}\n```"


_FENCED_DIRECTIVES = [
    "[button primary /start Get started]",
    "[lightbox /a.png A diagram]",
    "[youtube dQw4w9WgXcQ]",
    "[grid]",
    "[annotate]",
]


@st.composite
def _directive_in_tab_fence(draw: st.DrawFn) -> str:
    """Draw one directive line wrapped in a tab-indented fence inside a list item."""
    directive = draw(st.sampled_from(_FENCED_DIRECTIVES))
    return f"- item\n\n\t```\n\t{directive}\n\t```"


@st.composite
def _directive_in_indented_code(draw: st.DrawFn) -> str:
    """Draw one directive line as a top-level indented code block."""
    directive = draw(st.sampled_from(_FENCED_DIRECTIVES))
    return f"para\n\n    {directive}"


# One fence per directive form, so the explicit test reads the whole case at a glance.
FENCED_DIRECTIVE_FIXTURE = """\
```
[button primary /start Get started]
```

```
[lightbox /a.png A diagram]
```

```
[youtube dQw4w9WgXcQ]
```

```
[grid]
```

```
[annotate]
```
"""


class TestRoundTripFencedDirective:
    """A directive inside a fenced code block stays literal through both paths."""

    def test_run_pre_leaves_every_fenced_directive_literal(self) -> None:
        names = list(registry.EXTENSION_NAMES)
        expanded = registry.run_pre(FENCED_DIRECTIVE_FIXTURE, names)
        # No stage expands a directive line that sits inside a fence.
        assert '<a class="mw-button' not in expanded
        assert '<a class="mw-lightbox"' not in expanded
        assert "youtube.com/embed/" not in expanded
        assert "mw-grid" not in expanded
        assert "mw-annotate" not in expanded
        assert '<pre class="mermaid"' not in expanded

    def test_pipeline_equals_in_process_render(self) -> None:
        names = list(registry.EXTENSION_NAMES)
        pipeline = registry.run_post(stub_render(registry.run_pre(FENCED_DIRECTIVE_FIXTURE, names)), names)
        assert _normalize(pipeline) == _normalize(in_process_render(FENCED_DIRECTIVE_FIXTURE, names))


# A tab-indented in-list fence and a four-space indented code block, each holding a directive.
INDENTED_DIRECTIVE_FIXTURE = "- item\n\n\t```\n\t[button primary /start Get started]\n\t```\n\npara\n\n    [grid]\n"


class TestRoundTripIndentedDirective:
    """A directive inside a tab-indented fence or an indented code block stays literal through both paths."""

    def test_run_pre_leaves_an_indented_directive_literal(self) -> None:
        names = list(registry.EXTENSION_NAMES)
        expanded = registry.run_pre(INDENTED_DIRECTIVE_FIXTURE, names)
        assert '<a class="mw-button' not in expanded
        assert "mw-grid" not in expanded

    def test_pipeline_equals_in_process_render(self) -> None:
        names = list(registry.EXTENSION_NAMES)
        pipeline = registry.run_post(stub_render(registry.run_pre(INDENTED_DIRECTIVE_FIXTURE, names)), names)
        assert _normalize(pipeline) == _normalize(in_process_render(INDENTED_DIRECTIVE_FIXTURE, names))


_BODY_EXTENSIONS = ["admonition", "def_list", "footnotes", "pymdownx.details", "pymdownx.tabbed"]
# Each opener with the tag that starts the block in the render and the tag that ends it
_BODY_OPENERS = {
    "admonition": ('!!! note "Title"', '<div class="admonition', "</div>"),
    "details": ("??? note", "<details", "</details>"),
    "tab": ('=== "Tab"', '<div class="tabbed-content"', "</div>"),
    "definition": ("Term\n: A definition", "<dd>", "</dd>"),
    "footnote": ("Text[^1]\n\n[^1]: A footnote", '<div class="footnote"', "</div>"),
}
# Each body with the text that marks its expansion in the output
_BODY_CONTENT = {
    "directive": ("    [button primary /start Get started]", 'class="mw-button'),
    "embed": ("    [youtube dQw4w9WgXcQ]", "youtube.com/embed/"),
    "fence with a label": ("    ```python\n    [label app.py]\n    x = 1\n    ```", 'class="code-label"'),
    "mermaid": ("    ```mermaid\n    graph TD\n      A-->B\n    ```", '<pre class="mermaid"'),
}
_UNWRAPPED_BLOCK_RE = re.compile(r"<p>(<(?P<tag>iframe|pre|div)\b.*?</(?P=tag)>)</p>", re.DOTALL)


def _body_document(opener: str, content: str) -> str:
    """Build one block opener with a content body under it."""
    return f"{opener}\n\n{content}\n"


def _body_pipeline(document: str, names: list[str]) -> str:
    """Run the pre stage, a stub renderer holding the block extensions, and the post stage."""
    instance = markdown.Markdown(
        extensions=["pymdownx.superfences", "pymdownx.highlight", *_BODY_EXTENSIONS],
        extension_configs={"pymdownx.highlight": {"pygments_lang_class": True}},
    )
    return registry.run_post(instance.convert(registry.run_pre(document, names)), names)


def _body_in_process(document: str, names: list[str]) -> str:
    """Render in-process with the block extensions beside the markwright ones."""
    instance = markdown.Markdown(
        extensions=[
            "pymdownx.superfences",
            "pymdownx.highlight",
            *_BODY_EXTENSIONS,
            *(f"markwright.{name}" for name in names),
        ],
        extension_configs={"pymdownx.highlight": {"pygments_lang_class": True}},
    )
    return instance.convert(document)


def _is_inside_block(html: str, start_tag: str, end_tag: str, expansion: str) -> bool:
    """Report whether the expansion sits between the block's start tag and its end tag."""
    block_start = html.index(start_tag)
    return block_start < html.index(expansion) < html.index(end_tag, block_start)


class TestRoundTripBlockBodies:
    """A directive, an embed, a labelled fence, and a mermaid fence in a block opener body stay in the body."""

    @pytest.mark.parametrize("opener_name", list(_BODY_OPENERS))
    @pytest.mark.parametrize("content_name", list(_BODY_CONTENT))
    def test_in_process_render_keeps_the_expansion_inside_the_block(self, opener_name: str, content_name: str) -> None:
        opener, start_tag, end_tag = _BODY_OPENERS[opener_name]
        content, expansion = _BODY_CONTENT[content_name]
        names = list(registry.EXTENSION_NAMES)

        html = _body_in_process(_body_document(opener, content), names)

        assert _is_inside_block(html, start_tag, end_tag, expansion)

    @pytest.mark.parametrize("opener_name", list(_BODY_OPENERS))
    @pytest.mark.parametrize("content_name", list(_BODY_CONTENT))
    def test_pipeline_keeps_the_expansion_inside_the_block_and_equals_in_process(
        self, opener_name: str, content_name: str
    ) -> None:
        opener, start_tag, end_tag = _BODY_OPENERS[opener_name]
        content, expansion = _BODY_CONTENT[content_name]
        names = list(registry.EXTENSION_NAMES)
        document = _body_document(opener, content)

        pipeline = _body_pipeline(document, names)

        assert _is_inside_block(pipeline, start_tag, end_tag, expansion)
        # The stub renderer wraps an embed's block-level HTML in a paragraph that the in-process stash avoids
        assert _normalize(_UNWRAPPED_BLOCK_RE.sub(r"\1", pipeline)) == _normalize(_body_in_process(document, names))

    @pytest.mark.parametrize("opener_name", list(_BODY_OPENERS))
    def test_run_pre_keeps_a_mermaid_diagram_at_the_body_indentation(self, opener_name: str) -> None:
        opener, _, _ = _BODY_OPENERS[opener_name]
        document = _body_document(opener, _BODY_CONTENT["mermaid"][0])

        expanded = registry.run_pre(document, list(registry.EXTENSION_NAMES))

        assert '\n    <pre class="mermaid">' in expanded

    @pytest.mark.parametrize("opener_name", ["admonition", "details", "tab", "definition"])
    def test_in_process_render_does_not_wrap_a_mermaid_diagram_in_a_paragraph(self, opener_name: str) -> None:
        opener, _, _ = _BODY_OPENERS[opener_name]
        document = _body_document(opener, _BODY_CONTENT["mermaid"][0])

        html = _body_in_process(document, list(registry.EXTENSION_NAMES))

        assert "<p><pre" not in html


class TestRoundTripProperty:
    """Any document built from markwright's grammar renders the same through the pipeline and in-process."""

    @settings(max_examples=150, deadline=None)
    @given(
        blocks=st.lists(
            st.one_of(
                _prose_block(),
                _fence_block(),
                _EMBED_BLOCKS,
                _DIRECTIVE_BLOCKS,
                _grid_block(),
                _block_grid(),
                _CONTAINER_PROBLEMS,
                _tab_set(),
                _grid_with_tabs(),
                _TAB_PROBLEMS,
                _annotate_block(),
                _directive_in_fence(),
                _directive_in_tab_fence(),
                _directive_in_indented_code(),
            ),
            min_size=1,
            max_size=6,
        )
    )
    def test_pipeline_equals_in_process_render(self, blocks: list[str]) -> None:
        document = "\n\n".join(blocks) + "\n"
        names = list(registry.EXTENSION_NAMES)
        pipeline = registry.run_post(stub_render(registry.run_pre(document, names)), names)
        assert _normalize(pipeline) == _normalize(in_process_render(document, names))


class TestRoundTripDisallowedEnvironment:
    """The pipeline and the in-process render agree on the HTML and the diagnostics."""

    def test_pipeline_equals_in_process_render_and_diagnostics(self) -> None:
        source = "# Title\n\n```bash\n[label a.sh]\n[environment prod]\necho hi\n```\n"
        options = {"fence": {"allowed_environments": ["local"]}}
        names = ["fence"]
        pipeline_diagnostics: list[Diagnostic] = []
        pipeline = registry.run_post(
            stub_render(registry.run_pre(source, names, options)), names, pipeline_diagnostics, options
        )
        instance = markdown.Markdown(
            extensions=["pymdownx.superfences", "pymdownx.highlight", "markwright.fence"],
            extension_configs={
                "pymdownx.highlight": {"pygments_lang_class": True},
                "markwright.fence": options["fence"],
            },
        )
        with pytest.warns(RenderWarning):
            in_process = instance.convert(source)
        assert _normalize(pipeline) == _normalize(in_process)
        assert pipeline_diagnostics == instance.markwright_diagnostics  # type: ignore[attr-defined]
        assert [item.line for item in pipeline_diagnostics] == [5]


class TestRoundTripHtmlRegions:
    """A commented-out directive set and a verbatim block read the same in both paths."""

    COMMENTED = (
        "<!--\n[tab A]\n\nbody\n\n[/tab]\n[youtube dQw4w9WgXcQ]\n"
        "```command\n[label x.sh]\nmake\n```\n-->\n\nafter <^>this<^>\n"
    )
    VERBATIM = "<pre>\n[youtube dQw4w9WgXcQ]\n<^>x<^> :demo-check:\n</pre>\n\nafter <^>this<^> :demo-check:\n"

    @pytest.mark.parametrize("source", [COMMENTED, VERBATIM], ids=["comment", "pre-block"])
    def test_pipeline_equals_in_process_render(self, source: str, tmp_path: Path) -> None:
        pack = tmp_path / "pack"
        pack.mkdir()
        (pack / "check.svg").write_text('<svg viewBox="0 0 24 24"><path d="M1 1h22v22H1z"/></svg>')
        names = list(registry.EXTENSION_NAMES)
        options: dict[str, dict[str, object]] = {"icons": {"packs": {"demo": str(pack)}}}
        pipeline = registry.run_post(stub_render(registry.run_pre(source, names, options)), names, None, options)

        assert _normalize(pipeline) == _normalize(in_process_render(source, names, options))
        assert "<mark>this</mark>" in pipeline
        assert "[youtube dQw4w9WgXcQ]" in pipeline
        assert "<iframe" not in pipeline

    def test_a_shortcode_after_a_pre_block_is_an_icon_and_the_one_inside_stays_literal(self, tmp_path: Path) -> None:
        pack = tmp_path / "pack"
        pack.mkdir()
        (pack / "check.svg").write_text('<svg viewBox="0 0 24 24"><path d="M1 1h22v22H1z"/></svg>')
        names = list(registry.EXTENSION_NAMES)
        options: dict[str, dict[str, object]] = {"icons": {"packs": {"demo": str(pack)}}}
        pipeline = registry.run_post(stub_render(registry.run_pre(self.VERBATIM, names, options)), names, None, options)

        assert pipeline.count('<span aria-hidden="true" class="mw-icon"><svg') == 1
        assert "<pre>\n[youtube dQw4w9WgXcQ]\n<^>x<^> :demo-check:\n</pre>" in pipeline


class TestRoundTripRawHtmlProse:
    """A pair and a shortcode in a raw ``<div>`` with no blank lines read the same in both paths."""

    SOURCE = '<div class="note">\nSee <^>this<^> :demo-check: now.\n<a title="<^>x<^>">link</a>\n</div>\n'

    def test_both_paths_agree(self, tmp_path: Path) -> None:
        pack = tmp_path / "pack"
        pack.mkdir()
        (pack / "check.svg").write_text('<svg viewBox="0 0 24 24"><path d="M1 1h22v22H1z"/></svg>')
        names = ["highlight", "icons"]
        options: dict[str, dict[str, object]] = {"icons": {"packs": {"demo": str(pack)}}}
        pipeline = registry.run_post(stub_render(registry.run_pre(self.SOURCE, names, options)), names, None, options)
        in_process = in_process_render(self.SOURCE, names, options)

        assert _normalize(pipeline) == _normalize(in_process)
        assert "<mark>this</mark>" in in_process
        assert 'class="mw-icon"' in in_process
        assert 'title="<^>x<^>"' in in_process


class TestRoundTripRawHtmlLoadOrder:
    """The raw-HTML preprocessors run after every directive preprocessor, so extension load order never matters."""

    DOCUMENTS = (
        "<div>\n[tab :demo-check: One]\nbody\n[/tab]\n</div>\n",
        "<div>\n[button /start Go :demo-check:]\n</div>\n",
        "<div>\n[youtube dQw4w9WgXcQ]\nSee <^>this<^>.\n</div>\n",
    )
    ORDERS = (
        ["icons", "highlight", "button", "tabs", "youtube"],
        ["button", "tabs", "youtube", "icons", "highlight"],
        list(registry.EXTENSION_NAMES),
    )

    @pytest.mark.parametrize("names", ORDERS, ids=["icons-first", "icons-last", "registry"])
    @pytest.mark.parametrize("source", DOCUMENTS, ids=["tab-name", "button-text", "embed-beside-pair"])
    def test_in_process_equals_the_pipeline(self, source: str, names: list[str], tmp_path: Path) -> None:
        pack = tmp_path / "pack"
        pack.mkdir()
        (pack / "check.svg").write_text('<svg viewBox="0 0 24 24"><path d="M1 1h22v22H1z"/></svg>')
        options: dict[str, dict[str, object]] = {"icons": {"packs": {"demo": str(pack)}}}
        pipeline = registry.run_post(stub_render(registry.run_pre(source, names, options)), names, None, options)

        assert _normalize(in_process_render(source, names, options)) == _normalize(pipeline)
