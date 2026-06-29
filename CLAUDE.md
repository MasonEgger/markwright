# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## First Step: Load the Python Skill

**Before writing any code**, load the `/python` skill. It contains critical rules (empty `__init__.py`, type hints, import style, docstring format, line-length) that override defaults. Failing to load it first will cause repeated corrections.

## Commands

```bash
just                      # default: list the recipes
just install              # uv sync
just test                 # unit tests, 100% line + branch coverage (excludes integration)
just test-verbose         # same, verbose
just test-integration     # end-to-end Hugo pipeline test (needs hugo on PATH)
just lint                 # ruff check + ruff format --check
just format               # ruff format
just typecheck            # mypy --strict
just check                # test + lint + typecheck (the gate)
just docs-build           # mkdocs build --strict
just docs-serve           # mkdocs serve (localhost:8000)
just docs-serve-tailnet   # mkdocs serve on Tailscale IP
```

Run a single test file: `uv run pytest tests/test_highlight.py -v`
Run a single test: `uv run pytest tests/test_highlight.py::TestInlineHighlight::test_basic_inline -v`
Run the CLI from a checkout: `uv run mw <pre|post|render|list>` (a stdin-to-stdout filter).

**`just check` must pass before any step is considered complete.** It enforces 100% line AND branch coverage (`--cov-branch --cov-fail-under=100`); a line-only pass is not enough. `just check` runs unit tests only. The Hugo integration test is excluded via `-m "not integration"` and run separately.

## Project Overview

markwright is a set of Python-Markdown extensions ported from DigitalOcean's [`do-markdownit`](https://github.com/digitalocean/do-markdownit) (JavaScript/markdown-it, Apache 2.0), plus an `mw` command-line tool that exposes the same extensions as pre/post filter stages so the syntax works in any toolchain (Hugo, a plain Unix pipe, etc.), not only an in-process Python-Markdown render. The bundled MkDocs Material site in `docs/` is both documentation and a live demo. The upstream name `do-markdownit` appears in attribution (NOTICE, README) and must be preserved; the package and the CLI use the `markwright` / `mw` brand.

CI (GitHub Actions) has two jobs that both run on push and PR to main: `check` (unit tests + lint + typecheck) and `integration` (installs Hugo, runs `tests/integration`). The `deploy` job (docs to GitHub Pages) needs both and runs only on push to main. The `gh-pages` branch is auto-managed build output, force-pushed by `mkdocs gh-deploy`; never commit to it, merge it, or delete it.

## Architecture

The codebase has **two consumers over one set of pure stage functions**, so the extension logic is written once and used by both the in-process Python-Markdown render and the CLI.

**Pure stage functions (per extension module):**

- `expand_source(text: str) -> str` is the source stage (`mw pre`): expands embed directives to raw HTML, extracts fence directives into a marker comment, and (highlight) wraps prose `<^>` runs.
- `apply_html(html: str, warnings: list[str] | None = None) -> str` is the HTML stage (`mw post`): applies fence styling, wraps in-code highlight markers, injects embed scripts. Only fence uses `warnings`; the others accept and ignore it so the registry can call every post function with one signature.

**In-process adapters.** The Python-Markdown `Extension`/`Preprocessor`/`Postprocessor` classes are thin adapters that delegate to the stage functions. Embed preprocessors still stash raw HTML via `self.md.htmlStash.store(...)` (so Markdown does not re-parse it and break JS backticks or wrap blocks in `<p>`); the `expand_source` path emits the HTML inline for the CLI. Both go through a per-extension `_render_match(line) -> str | None` helper. Extensions are loaded by name, e.g. `markwright.highlight`.

**Registry and CLI.** `registry.py` maps each extension name to `{pre, post, pre_priority, post_priority}` and provides `select_extensions`, `run_pre`, `run_post`, and `describe`. `cli.py` is a stdlib `argparse` CLI (`main(argv) -> int`) with subcommands `pre`, `post`, `render`, and `list`; the entry point is `mw = markwright.cli:main`. `render` builds a `markdown.Markdown` with `pymdownx.superfences` + `pymdownx.highlight` + the selected `markwright.*` extensions (the in-process path).

### The Three Extension Patterns

1. **Fence** (`fence.py`): `expand_source` extracts directives (`[label]`, `[secondary_label]`, `[environment]`) and prefix flags (`line_numbers`, `command`, `super_user`, `custom_prefix(...)`) and emits one `<!-- mw-fence:{JSON} -->` comment, keeping the fence so the renderer still highlights it. `apply_html` reads the comment and applies label divs, environment classes, and `<ol><li data-prefix>` wrapping. The marker is a cross-tool contract: it carries `"version": 1` (`MARKER_NAME` / `MARKER_VERSION`) and is validated fail-soft (malformed JSON, an unsupported version, or no adjacent code block is skipped, and reported under `--warn`). Line-prefix wrapping handles two renderers: Pygments emits flat newline-delimited lines, while Chroma (Hugo) wraps each line in `<span class="line">...\n</span>`, so `_split_rendered_lines` splits on line-span boundaries when present and on newlines otherwise.

2. **Embeds** (youtube, slideshow, image_compare, codepen, twitter, instagram): `expand_source` replaces standalone `[name ...]` lines with raw HTML. The script embeds (codepen, twitter, instagram) also have `apply_html`, which injects the `<script>` exactly once via **signature detection** (it appends the script only when the embed's class is present and the script is not already there). This is idempotent and shared by both the in-process postprocessor and the CLI; there is no `found` flag.

3. **Highlight** (`highlight.py`): keeps an InlineProcessor for in-process prose. `apply_html` handles escaped or raw `<^>` markers in rendered HTML span-boundary-safe (it never crosses a syntax-highlight `<span>`). `expand_source` is the CLI pre stage: it wraps prose `<^>` only outside fenced and inline code, leaving in-code markers for `apply_html`. The `\<^>` backslash escape renders a literal marker in both stages.

### Processor Priority Reference (in-process)

| Priority | Type | Extension | Relationship |
|----------|------|-----------|-------------|
| 40 | Preprocessor | fence | Runs *before* `pymdownx.superfences` (~38) |
| 20 | Preprocessor | all embeds | Runs *after* superfences (embed syntax in fences is already stashed) |
| 175 | InlineProcessor | highlight | Runs before emphasis |
| 25 | Postprocessor | fence, highlight | Standard post-processing |
| 15 | Postprocessor | codepen, twitter, instagram | Script injection (runs after other postprocessors) |

The registry's stage priorities mirror these so the CLI composes stages in the same order as the in-process render.

### Shared Utilities

`_util.py` contains `reduce_fraction()` used by embed extensions for aspect-ratio calculations. Do not add trivial wrappers here.

## Code Conventions

- `__init__.py` is **always empty**; never add anything to it
- Every source file uses `from __future__ import annotations` as the first import
- Type hints on everything, no `Any`; mypy strict is enforced
- Absolute imports only (e.g., `from markwright._util import reduce_fraction`)
- RST docstrings (`:param:`, `:returns:`) on public interfaces
- `line-length = 120`, `target-version = "py314"`
- Every source file starts with a 2-line `# ABOUTME:` comment
- **Descriptive variable names always**: single-letter variables are NEVER allowed (`line_index` not `i`, `label_match` not `m`, `mark_element` not `el`)
- No trivial wrappers: call `html.escape()` directly, don't wrap stdlib functions
- HTML output must match the do-markdownit reference format (see the HTML Output Contracts in `.ai-sessions/v1-init/plan.md`)
- The `mw-fence` marker payload is a public cross-tool contract: changes are versioned and read fail-soft (see `spec.md`)

## Testing Approach

- TDD: RED (failing test) then GREEN (minimal code) then REFACTOR.
- Unit tests are `tests/test_<module>.py`. In-process behavior uses `render_*(source)` helpers (e.g. `render_fence()`); the pure stage functions are tested by calling `expand_source` / `apply_html` directly; the CLI, registry, round-trip, and packaging have their own files. `tests/conftest.py` provides the `md_with_superfences` fixture matching the real site stack.
- `tests/test_roundtrip.py` is the safety net for the pure path: it asserts `run_post(stub_render(run_pre(doc)))` equals the in-process render.
- `tests/integration/test_hugo_pipeline.py` (marked `integration`) drives `mw pre | hugo | mw post` through a real Hugo build. It is excluded from `just check` and run via `just test-integration` and the CI `integration` job; it skips when `hugo` or `mw` is not on PATH. Touching fence line-prefix logic? Exercise it (or the Chroma fixtures in `test_fence.py`): the in-process round-trip uses Pygments and will not catch Chroma-only bugs.
- Coverage is 100% line AND branch, enforced by the gate.
- Test our logic only; do not test Python-Markdown, pymdownx, argparse, or pygments behavior.

## Plan & Progress Tracking

- `spec.md`, `plan.md`, `todo.md` (repo root): the **completed** `mw` pipeline CLI work (a 12-step TDD plan, all items checked). Read `spec.md` for the design rationale, the marker contract, and the renderer requirements.
- `.ai-sessions/v1-init/{plan,todo}.md`: the archived v1 extension plan with the HTML Output Contracts. Both v1 and v2 are done.
- `.ai-sessions/`: session summaries (read the most recent for context). `.ai-sessions/lessons.md` accumulates cross-session lessons.
