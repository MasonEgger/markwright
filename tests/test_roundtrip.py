# ABOUTME: Cross-stage round-trip integration tests for the mw pipeline.
# Proves run_pre | external-render | run_post equals the in-process markwright render.

from __future__ import annotations

import re

import markdown

from markwright import registry
from markwright.codepen import CODEPEN_SCRIPT

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


def in_process_render(markdown_text: str, names: list[str]) -> str:
    """Render Markdown through the in-process stack the ``mw render`` path builds.

    :param markdown_text: Source text.
    :param names: markwright extension names to load alongside the site stack.
    :returns: Final HTML with every markwright stage applied in-process.
    """
    instance = markdown.Markdown(
        extensions=["pymdownx.superfences", "pymdownx.highlight", *(f"markwright.{name}" for name in names)],
        extension_configs={"pymdownx.highlight": {"pygments_lang_class": True}},
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


class TestRoundTripIdempotency:
    """Running the post stage twice does not double-apply any transform."""

    def test_running_post_twice_is_stable(self) -> None:
        names = list(registry.EXTENSION_NAMES)
        once = registry.run_post(stub_render(registry.run_pre(FIXTURE, names)), names, None)
        twice = registry.run_post(once, names, None)
        assert once == twice
        assert once.count(CODEPEN_SCRIPT) == 1
        assert twice.count(CODEPEN_SCRIPT) == 1


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
