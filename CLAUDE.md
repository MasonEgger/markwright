# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## First Step: Load the Python Skill

**Before writing any code**, load the `/python` skill. It contains critical rules (empty `__init__.py`, type hints, import style, docstring format, line-length) that override defaults. Failing to load it first will cause repeated corrections.

## Commands

```bash
just install              # uv sync
just test                 # pytest with coverage
just test-verbose         # pytest -v with coverage
just lint                 # ruff check + ruff format --check
just format               # ruff format
just typecheck            # mypy --strict
just check                # runs test + lint + typecheck
just docs-build           # mkdocs build --strict
just docs-serve           # mkdocs serve (localhost:8000)
just docs-serve-tailnet   # mkdocs serve on Tailscale IP
```

Run a single test file: `uv run pytest tests/test_highlight.py -v`
Run a single test: `uv run pytest tests/test_highlight.py::TestInlineHighlight::test_basic_inline -v`

**`just check` must pass before any step is considered complete.**

## Project Overview

Python-Markdown extensions ported from DigitalOcean's [`do-markdownit`](https://github.com/digitalocean/do-markdownit) (JavaScript/markdown-it, Apache 2.0). Works with any Python-Markdown consumer: MkDocs, Flask, CLI tools, etc. The bundled MkDocs Material site in `docs/` is both documentation and a live demo. CI via GitHub Actions runs tests and deploys docs to GitHub Pages on push to main. The `gh-pages` branch is the Pages deploy target, force-pushed by `mkdocs gh-deploy` in the CI `deploy` job; it is auto-managed build output, not a source branch, so never commit to it, merge it, or delete it.

## Architecture

Each extension is a standalone Python-Markdown extension in `src/do_markdown/` with a `makeExtension(**kwargs)` entry point. Extensions are loaded by name (e.g., `do_markdown.highlight`).

**Three processor patterns:**

1. **Fence extension** (`fence.py`): Preprocessor extracts directives (`[label]`, `[secondary_label]`, `[environment]`) from fence content and prefix flags (`line_numbers`, `command`, `super_user`, `custom_prefix(...)`) from the info string. Stores metadata as `<!-- do-fence:{JSON} -->` HTML comments. Postprocessor applies transformations (label divs, CSS classes, `<ol><li data-prefix>` wrapping) to rendered HTML. All fence features share this single coordinated extension to avoid ordering bugs.

2. **Embed extensions** (youtube, codepen, twitter, instagram, slideshow, image_compare): Preprocessor matches standalone `[name ...]` lines and replaces with raw HTML. Social embeds (codepen, twitter, instagram) add a Postprocessor for one-time script injection.

3. **Highlight extension** (`highlight.py`): InlineProcessor for regular text + Postprocessor for HTML-escaped `<^>` markers inside code blocks.

### Processor Priority Reference

| Priority | Type | Extension | Relationship |
|----------|------|-----------|-------------|
| 40 | Preprocessor | fence | Runs *before* `pymdownx.superfences` (~38) |
| 20 | Preprocessor | all embeds | Runs *after* superfences (embed syntax in fences is already stashed) |
| 175 | InlineProcessor | highlight | Runs before emphasis |
| 25 | Postprocessor | fence, highlight | Standard post-processing |
| 15 | Postprocessor | codepen, twitter, instagram | Script injection (runs after other postprocessors) |

### Recurring Implementation Patterns

**Script injection** (codepen, twitter, instagram): The Preprocessor sets a `found` boolean when it matches any embed. The Postprocessor checks `self.preprocessor.found` and appends the `<script>` tag exactly once at the end of the rendered content.

**Flag parser** (codepen, twitter, instagram): Each embed with flags has a module-level `_parse_flags()` (or `_parse_*_flags()`) function that takes a raw string and returns a typed dict. This keeps the preprocessor's `run()` method focused on line matching and HTML generation.

**Dimension parser** (slideshow): Separates trailing integers (height, width) from a variable-length list of URLs by popping numeric values from the end of the argument list.

**Shared utilities** (`_util.py`): Contains `reduce_fraction()` used by embed extensions for aspect-ratio calculations. Do not add trivial wrappers here.

## Code Conventions

- `__init__.py` is **always empty**; never add anything to it
- Every source file uses `from __future__ import annotations` as the first import
- Type hints on everything, no `Any`; mypy strict is enforced
- Absolute imports only (e.g., `from do_markdown._util import reduce_fraction`)
- RST docstrings (`:param:`, `:returns:`) on public interfaces
- `line-length = 120`, `target-version = "py314"`
- Every source file starts with a 2-line `# ABOUTME:` comment
- **Descriptive variable names always**: single-letter variables are NEVER allowed (`line_index` not `i`, `label_match` not `m`, `mark_element` not `el`)
- No trivial wrappers: call `html.escape()` directly, don't wrap stdlib functions
- HTML output must match the do-markdownit reference format (see the HTML Output Contracts in `.ai-sessions/v1-init/plan.md`)

## Testing Approach

- TDD: write failing tests first (RED), implement (GREEN), then refactor
- Each extension has its own test file with a `render_*(source)` helper that creates a `markdown.Markdown` instance with the extension loaded (e.g., `render_youtube()`, `render_fence()`)
- `tests/conftest.py` provides `md_with_superfences` fixture matching the real site stack
- Test **our extension logic only**: do not test Python-Markdown or pymdownx behavior
- Do not test trivial code; test behavior and outcomes

## Plan & Progress Tracking

- `spec.md`: Current spec, a pipeline CLI that exposes the extensions as pre/post filter stages so DO markdown can run in toolchains outside Python-Markdown (e.g. Go/Hugo). Wraps the existing extensions; not a Go port. Not yet implemented.
- `.ai-sessions/v1-init/plan.md`: The v1 implementation plan (extensions) with detailed per-step prompts and HTML Output Contracts. Archived; v1 is complete.
- `.ai-sessions/v1-init/todo.md`: The v1 step-completion checklist. Archived.
- `.ai-sessions/`: Session summaries from previous work; read the most recent one for context. `.ai-sessions/lessons.md` accumulates lessons across sessions.
