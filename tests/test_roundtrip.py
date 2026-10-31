# ABOUTME: Cross-stage round-trip integration tests for the mw pipeline.
# Proves run_pre | external-render | run_post equals the in-process markwright render.

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import markdown
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from markwright import registry
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
        assert '<ul class="mw-grid mw-cards">' in pipeline
        assert '<a class="mw-annotation" href="#mw-annotation-1-1">1</a>' in pipeline
        assert "(1)!" not in pipeline
        assert '<li id="mw-annotation-2-1">A prose note.</li>' in pipeline


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


class TestRoundTripIdempotency:
    """Running the post stage twice does not double-apply any transform."""

    def test_running_post_twice_is_stable(self) -> None:
        names = list(registry.EXTENSION_NAMES)
        once = registry.run_post(stub_render(registry.run_pre(FIXTURE, names)), names, None)
        twice = registry.run_post(once, names, None)
        assert once == twice
        assert once.count(CODEPEN_SCRIPT) == 1
        assert twice.count(CODEPEN_SCRIPT) == 1


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
    """Draw a grid directive followed by a short bullet list."""
    directive = draw(st.sampled_from(["[grid]", "[grid cards]"]))
    items = draw(st.lists(_PHRASES, min_size=1, max_size=3))
    return directive + "\n\n" + "\n".join(f"- {item}" for item in items)


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
                _annotate_block(),
                _directive_in_fence(),
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
