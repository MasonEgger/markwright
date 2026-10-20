# Plan: Material Reference Parity (Issue #16)

Turns `spec.md` (D1 through D7 and the six contracts) into TDD-sized steps.
Every step is test-first and keeps `just check` green; no existing extension's output changes.

## Ordering

Shared helpers first (two callers each), then the four pre-only extensions from simplest to hardest, then the two marker-comment extensions, then the cross-cutting tests, docs, and spec.
Each extension step adds its registry entry, so the roundtrip and CLI tests see it as soon as it lands.

## Steps

### Step 1: Shared helpers

- `_html.matching_end(tokens, start_index)`: index of the end tag closing a start token (depth by tag name). Callers: grid, annotate.
- `_html.add_classes(tag, classes)`: move fence's private `_with_classes` here. Callers: fence, grid, annotate.
- `_fences.map_prose(text, transform)`: apply a transform to text outside fenced blocks and inline code spans. Callers: highlight (refactor of `expand_source`), icons.

Tests: `test_highlight.py` already covers `map_prose` through `expand_source`; `test_fence.py` covers `add_classes` through `apply_html`. `matching_end` gets its first tests through grid.

### Step 2: button

`tests/test_button.py`: standalone line renders `<a class="mw-button">`, `primary` adds the modifier, text is escaped, an inline mention is left alone, in-process render wraps in `<p>`, two consecutive lines share one `<p>`.

### Step 3: lightbox

`tests/test_lightbox.py`: URL only, URL plus alt text, escaping, in-process render.

### Step 4: mermaid

`tests/test_mermaid.py`: a mermaid fence becomes `<pre class="mermaid">` with escaped source, other fences untouched, an indented fence in a list item, in-process render passes it through verbatim (stash), a `[label]` line inside stays diagram text.

### Step 5: icons

`tests/test_icons.py` with a `tmp_path` pack fixture: resolves `:pack-name:`, nested path joins with `-`, unknown pack and unknown name stay literal, inside inline code and fences untouched, XML declaration stripped, in-process render, options: omitted is silent, `{}` warns, non-table and missing directory raise `OptionError`, config validation wraps it in `ConfigError`.

### Step 6: grid

`tests/test_grid.py`: pre emits the marker and blank line (indent preserved), post adds classes to the next list, cards variant, no following list is skipped and reported, marker consumed, running post twice is stable, in-process render.

### Step 7: annotate

`tests/test_annotate.py`: paragraph with markers, fenced code with `# (1)!` under Pygments (comment span removed) and under a Chroma fixture, plain `<pre><code>` keeps the comment text, ids count per page, a `(9)` with no item stays text, no `<ol>` is skipped and reported, works together with a `[label]` fence directive, markers in attributes untouched, in-process render.

### Step 8: Cross-cutting

- `test_roundtrip.py`: extend `FIXTURE`, the presence assertions, and the hypothesis grammar with the six constructs.
- `test_registry.py`, `test_cli.py`: option names, `mw list` and `mw config` output.
- `tests/integration/test_hugo_pipeline.py`: one page using every new construct through Hugo (Chroma comment spans for the `!` form).

### Step 9: Docs, demo assets, and release

Decided in the 2026-10-15 brainstorm: the docs site is a fully-live demo, version is 0.4.0, and markwright ships no icons (the demo supplies its own).

- `docs/extensions/{button,grid,mermaid,icons,lightbox,annotate}.md`, each with usage, syntax, the `mw-` contract, a live demo, and the host CSS or script it needs.
- Host CSS in `docs/stylesheets/extra.css` for all six (button and grid are CSS-only).
- `docs/javascripts/` (first JS in the repo), wired in `mkdocs.yml` `extra_javascript`: a pinned mermaid.js from a CDN with `mermaid.initialize`, a lightbox `<dialog>` opener, and an annotation tooltip. Each is a documented host starting point, like the click-to-load sample script.
- A small, liberally-licensed, credited icon set committed under `docs/icons/`, configured as a demo pack in `mkdocs.yml` (`markwright.icons` `packs`). markwright itself ships none. The icons docs page credits the set and its license.
- `mkdocs.yml` nav, `docs/index.md`, `docs/cli.md` (list and config output), `docs/config.md` (the icons `packs` option), `docs/integrations/mkdocs.md`, README, CHANGELOG (an Added section for 0.4.0), and the version bump to 0.4.0.
- CLAUDE.md: the new extension patterns, the priority table, and the `_markers.py` boundary.

## Implementation Notes

A first pass on 2026-10-14 implemented steps 1 through 8 and was discarded so the work could run under the goal loop.
These are what it hit; each one cost a cycle to find.

- Python-Markdown's `normalize_whitespace` preprocessor (priority 30) strips the STX and ETX bytes around an `htmlStash` placeholder, so a preprocessor registered above 30 (mermaid at 45, ahead of superfences) cannot stash; emit the raw `<pre>` block inline and let the `html_block` preprocessor (priority 20) carry it. The embeds get away with stashing because they run at 20.
- Python-Markdown's raw-HTML block scanner allows at most three spaces of indentation, so a raw block inside a list item (an indented mermaid fence, or any embed) renders wrapped in `<p>` in-process; Goldmark handles it. Test the indented case on the pre stage and through Hugo, not in-process.
- Python-Markdown serializes element attributes in sorted order, so the pre stage must emit the icon wrapper as `<span aria-hidden="true" class="mw-icon">` (alphabetical) for byte parity with the in-process `InlineProcessor` output.
- Python-Markdown treats a lone `<a ...>...</a>` line as a paragraph with inline raw HTML, so button and lightbox need no stash in-process; one `_render_match` serves both paths and the renderer still processes Markdown inside the text.
- Pygments and Chroma both emit a single-line comment as `<span class="c1">`; neither includes the trailing newline in the span, but keep a trailing newline if a comment span carries one, or stripping the `(1)!` comment merges two code lines.
- The annotate post stage must run before the fence post stage (post priority 30 over 25) so the fence marker comment is still a comment token when the annotated block is located; otherwise the label `<div>` the fence stage inserts becomes the "block".
- A shared `_markers.py` (encode, find with block ends, fail-soft decode into a strict pydantic model) removes the duplicated marker handling from fence, grid, and annotate; moving fence onto it is behavior-preserving under the existing fence tests. The empty-page case (no markers) needs an explicit test; a strict `zip` over an empty marker list raised.
- `_fences.map_prose(text, transform)` (prose outside fences and inline code spans) is the second-caller extraction that highlight's `expand_source` and icons share; `_html.add_classes` and `_html.matching_end` likewise serve fence, grid, and annotate.
- With no icon packs configured the extension must pass text through silently: the default all-on selection would otherwise warn for every user. An explicit `packs = {}` warns; a missing directory is an `OptionError` at the boundary.
