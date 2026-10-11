# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## First Step: Load the Python Skill

**Before writing any code**, load the `/python` skill and read its `references/profile.md`. It holds the rules this repo follows (type hints, pydantic data shapes, import style, exceptions, the canonical toolchain blocks) and overrides defaults. The project-specific exemptions are listed under Code Conventions below.

## Commands

```bash
just                      # list the recipes
just check                # the gate: ruff check ., ruff format --check ., mypy ., pytest
just fmt                  # ruff format . and ruff check --fix .
just test                 # pytest (unit plus integration; integration skips without hugo or mw on PATH)
just test-all             # pytest across Python 3.11 through 3.15
just test-integration     # only the end-to-end Hugo and clean-install tests
just docs-build           # mkdocs build --strict
just docs-serve           # mkdocs serve (localhost:8000)
just docs-serve-tailnet   # mkdocs serve on Tailscale IP
```

Run a single test file: `uv run pytest tests/test_highlight.py -v`
Run a single test: `uv run pytest tests/test_highlight.py::TestHighlightPostStageScope::test_marker_in_an_attribute_is_untouched -v`
Run the CLI from a checkout: `uv run mw <pre|post|render|config|list>` (a stdin-to-stdout filter).

**`just check` must pass before any step is considered complete.** Coverage is reported (line and branch, `term-missing`) but not gated: read the report and either test or delete what it shows uncovered.

## Project Overview

markwright is a set of Python-Markdown extensions ported from DigitalOcean's [`do-markdownit`](https://github.com/digitalocean/do-markdownit) (JavaScript/markdown-it, Apache 2.0), plus an `mw` command-line tool that exposes the same extensions as pre/post filter stages so the syntax works in any toolchain (Hugo, a plain Unix pipe, etc.), not only an in-process Python-Markdown render. The bundled MkDocs Material site in `docs/` is both documentation and a live demo. The upstream name `do-markdownit` appears in attribution (NOTICE, README) and must be preserved; the package and the CLI use the `markwright` / `mw` brand. Runtime dependencies are `markdown`, `pymdown-extensions` (floor set by a security fix), and `pydantic`.

CI (GitHub Actions, `ci.yml`) runs on push and PR to main and monthly: one `check` job per Python 3.11 through 3.15 that installs a pinned Hugo and runs `just check` (plus `pip-audit` once), then `deploy` (docs to GitHub Pages, push to main only, the only job with write permission). `workflow.yml` publishes to PyPI via trusted publishing when a GitHub Release is published, after the same audit and gate. Dependabot updates uv and Actions weekly. The `gh-pages` branch is auto-managed build output, force-pushed by `mkdocs gh-deploy`; never commit to it, merge it, or delete it.

## Architecture

The codebase has **two consumers over one set of pure stage functions**, so the extension logic is written once and used by both the in-process Python-Markdown render and the CLI.

**Pure stage functions (per extension module):**

- `expand_source(text: str, options: Mapping[str, object] | None = None) -> str` is the source stage (`mw pre`): expands embed directives to raw HTML, extracts fence directives into a marker comment, and (highlight) wraps prose `<^>` runs. Fence reads `options` (its `allowed_environments`) and the four third-party embeds read `load`; the others accept and ignore it so the registry can call every pre function with one signature.
- `apply_html(rendered_html: str, skip_reasons: list[str] | None = None, options: Mapping[str, object] | None = None) -> str` is the HTML stage (`mw post`): applies fence styling, wraps in-code highlight markers, injects embed scripts. Only fence uses `skip_reasons` and `options` (its label classes); the others accept and ignore them.

**In-process adapters.** The Python-Markdown `Extension`/`Preprocessor`/`Postprocessor` classes are thin adapters that delegate to the stage functions. Embed preprocessors stash raw HTML via `self.md.htmlStash.store(...)` (so Markdown does not re-parse it and break JS backticks or wrap blocks in `<p>`); the `expand_source` path emits the HTML inline for the CLI. Both go through a per-extension `_render_match(line) -> str | None` helper (`_render_match(line, load)` for the embeds that take `load`). Extensions are loaded by name, e.g. `markwright.highlight`.

**Parsing structured text.** Two private modules own it, so no stage parses Markdown structure or HTML with ad hoc regex:

- `_fences.py` finds fenced code blocks by CommonMark's rules (0 to 3 space indent or under a list item, closing fence of the same character and at least the opening length, unclosed fences are not code). Fence's directive extraction and highlight's prose pass both use it, which is what keeps the two pre stages in parity.
- `_html.py` tokenizes rendered HTML with the stdlib `html.parser` and keeps each token's source offsets (`HtmlToken`). Post stages find elements from tokens and apply span edits (`apply_edits`), so everything they do not touch stays byte-identical. A tree parser (lxml, selectolax) would re-serialize the whole page and is deliberately not used. `provider_script_needed` decides script injection from parsed classes and `src` attributes.

Regex remains for single-line token grammars (the `[youtube ...]`-style directive lines ported from do-markdownit, fence info strings, the marker comment's own format, inline code spans and `<^>` markers within known text).

**Config.** `config.py` owns the tuning surface: `load_config(explicit_path, start_dir) -> Config` discovers a standalone `markwright.toml` or a `[tool.markwright]` table in `pyproject.toml` by walking up with `pathlib`, parses it with stdlib `tomllib`, and validates it fail-loud into a frozen pydantic `Config` (a boundary `ConfigError`, never a traceback). `Config` carries the selection intent (`enable`/`disable`), per-extension option tables, the `warn` default, and a source map for `mw config`. It depends on `registry` (`EXTENSION_NAMES`, `OPTION_NAMES`, `REGISTRY`) and nothing else; keep that direction. It drops `None` values (omitted), rejects option keys outside `OPTION_NAMES`, and runs each `StageSpec.check_options` (the extension's own reader), wrapping its `OptionError` (a `ValueError` subclass in `_diagnostics.py`) in a `ConfigError`; any other exception from a checker is a bug and propagates.

**Public host API.** `config.py` also exposes the API host tools (first consumer: Bartleby) build on, re-exported from the package root: `config_from_mapping(table, source)` validates an already-parsed table with the same rules as a file (errors prefixed with the `source` label, `source_path` left `None`), `selected_extensions(config)` applies `enable`/`disable` (an empty selection emits a `ConfigWarning`, never an error), and `extension_configs(config, names)` builds `markwright.<name>` option dicts for `markdown.Markdown`. `mw render` uses these same functions; only `--exclude` and the `pymdownx.highlight` entry stay CLI-side.

**Registry and CLI.** `registry.py` maps each extension name to a frozen pydantic `StageSpec` (`pre`, optional `post`, priorities, the Python-Markdown `extension` class, optional `check_options`) and provides `run_pre`, `run_post` (each threads every extension its option dict from config), and `describe`. `OPTION_NAMES` derives each extension's accepted keys from its class's declared `config`, so a new option is declared once. `cli.py` is a stdlib `argparse` CLI (`main(argv) -> int`) with subcommands `pre`, `post`, `render`, `config`, and `list`; the entry point is `mw = markwright.cli:main`. Selection resolves from config with `--exclude` (argparse `choices`) applied last via `_resolve`. Helpers raise; `main` is the only place exceptions become exit codes (`ConfigError`, or a `ConfigWarning` escalated by `-W error`, prints `mw: error:` and returns 2), because library code raises and only the CLI boundary returns codes. `render` builds a `markdown.Markdown` with `pymdownx.superfences` + `pymdownx.highlight` + the selected extensions and their config. `config` prints the resolved configuration and the source of each value.

### The Three Extension Patterns

1. **Fence** (`fence.py`): `expand_source` extracts directives (`[label]`, `[secondary_label]`, `[environment]`) and prefix flags (`line_numbers`, `command`, `super_user`, `custom_prefix(...)`) and emits one `<!-- mw-fence:{JSON} -->` comment before the fence (at the fence's indentation, plus a blank line when indented, so it stays inside a list item), keeping the fence so the renderer still highlights it. `apply_html` validates each marker with the strict pydantic `FenceMarker` (unknown fields ignored), then applies label divs, environment classes, and `<ol><li data-prefix>` wrapping to the first `<pre>`/`<code>` before the next marker. The marker is a cross-tool contract: it carries `"version": 1` and is read fail-soft (malformed JSON, a non-object payload, an unsupported version, a wrongly typed field, or no following block is skipped and reported under `--warn`). Line-prefix wrapping handles two renderers: Pygments emits flat newline-delimited lines, while Chroma (Hugo) wraps each line in `<span class="line">`, which are taken whole from the tokens.

2. **Embeds** (youtube, slideshow, image_compare, codepen, twitter, instagram): `expand_source` replaces standalone `[name ...]` lines with raw HTML. Flag parsing lives on pydantic settings models (`CodePenSettings.from_flags` and friends). The script embeds (codepen, twitter, instagram) also have `apply_html`, which appends the provider `<script>` once when `_html.provider_script_needed` finds an embed element outside every `<template>` and no script with that `src`. This is idempotent and shared by the in-process postprocessor and the CLI.

   **Load modes.** youtube (`eager|lazy|click`) and codepen, twitter, instagram (`eager|click`) take a `load` option, declared in each `Extension.config` (Python-Markdown raises `KeyError` on undeclared keys) and read by `expand_source` from `options`. `eager` output must stay byte-identical to earlier releases. `click` wraps the eager markup in the versioned `mw-embed` preview (`data-mw-version="1"`, live markup in `<template class="mw-embed-content">`), documented in `docs/click-to-load.md` as a public contract like the fence marker. `_embed_load.py` holds `load_mode`, `wrap_preview`, and the shared URL-prefix grammar.

3. **Highlight** (`highlight.py`): keeps an InlineProcessor for in-process prose. `apply_html` reads escaped `&lt;^&gt;` markers only from text tokens (never attributes, `<script>`, or `<style>`), pairs each with the next on the same line, and wraps every text run between them so it never crosses a syntax-highlight `<span>`. `expand_source` is the CLI pre stage: it wraps prose `<^>` only outside fenced code (via `_fences`) and inline code spans (n-backtick runs), leaving in-code markers for `apply_html`. The `\<^>` backslash escape renders a literal marker in both stages.

### Processor Priority Reference (in-process)

| Priority | Type | Extension | Relationship |
|----------|------|-----------|-------------|
| 40 | Preprocessor | fence | Runs *before* `pymdownx.superfences` (~38) |
| 20 | Preprocessor | all embeds | Runs *after* superfences (embed syntax in fences is already stashed) |
| 175 | InlineProcessor | highlight | Runs before emphasis |
| 25 | Postprocessor | fence, highlight | Standard post-processing |
| 15 | Postprocessor | codepen, twitter, instagram | Script injection (runs after other postprocessors) |

The registry's stage priorities mirror these so the CLI composes stages in the same order as the in-process render.

## Code Conventions

The `python` skill's rules apply. Project-specific points and the deliberate exemptions:

- `__init__.py` only re-exports the public API (`Config`, `ConfigError`, `ConfigWarning`, `OptionError`, and the three config functions) with `__all__` (the skill's library carve-out); add nothing else to it
- Data shapes are frozen pydantic models (`model_config = ConfigDict(frozen=True)`). An import used only in a model's field annotations must stay a runtime import, since pydantic resolves annotations at runtime; mark it `# noqa: TC00x` with that reason
- **Exemption: RST docstrings** (`:param:`, `:returns:`, `:raises:`) instead of the skill's Google style, for consistency across every existing module; there are no doctests and MkDocs does not render docstrings
- **Exemption: Python-Markdown's API names** (`extendMarkdown`, `makeExtension`, `handleMatch`) carry a per-line `# noqa: N802` with the reason, never a config-level ignore
- The ruff, mypy, and justfile blocks are the skill's canonical ones, pasted verbatim; do not add per-repo rules or ignores
- Every source file starts with a 2-line `# ABOUTME:` comment and uses `from __future__ import annotations`
- **Descriptive variable names always**: single-letter variables are NEVER allowed (`line_index` not `i`, `label_match` not `m`, `mark_element` not `el`)
- A one-caller private helper must hold a genuinely separate concern (a grammar, a scanner, a validator); otherwise inline it
- No `assert` for narrowing in `src/`; restructure (walrus in the comprehension, yield pairs) instead
- HTML output must match the do-markdownit reference format (see the HTML Output Contracts in `.ai-sessions/v1-init/plan.md`)
- **Config law** (also in `docs/config.md`, Config Rules): omitting a key means its default (for a list, no restriction); a list names exactly what it holds, so an empty allowlist allows nothing and an empty denylist removes nothing, and no list treats empty as "everything"; a setting that makes a feature a no-op is legal but emits `ConfigWarning` (via `warnings.warn`, never `logging` or `print`) naming the key and source; every option markwright defines is validated in `config.py` and in the extension. New options must follow it. A `None` value counts as omitted. Python-Markdown coerces a `None` config default through `parseBoolValue`, so an option that must tell omitted from empty uses a sentinel default (`fence._ALL_ENVIRONMENTS`) and reads options in `extendMarkdown`, never `__init__`, so `setConfig` after construction applies
- `mw` prints `ConfigWarning` as one `mw: warning:` stderr line via `cli._show_warning` inside `warnings.catch_warnings()` (other categories keep Python's format)
- The `mw-fence` marker payload and the `mw-embed` preview are public cross-tool contracts: changes are versioned and read fail-soft

## Testing Approach

- TDD: RED (failing test) then GREEN (minimal code) then REFACTOR.
- Unit tests are `tests/test_<module>.py`, class-grouped, against the public API only (no imports of private names). In-process behavior uses `render_*(source)` helpers; the pure stage functions are tested by calling `expand_source` / `apply_html` directly. Shared setup is a factory fixture in the module that uses it (`feed_stdin` in `test_cli.py`, `write_file` in `test_config.py`).
- CLI tests assert on `capsys` stderr; library warning tests use `pytest.warns`.
- `tests/test_roundtrip.py` is the safety net for the pure path: it asserts `run_post(stub_render(run_pre(doc)))` equals the in-process render, including a hypothesis property over random documents built from markwright's grammar.
- `tests/integration/` (marked `integration`) drives `mw pre | hugo | mw post` through a real Hugo build and installs the wheel in a clean venv. `just check` runs it; it skips when `hugo` or `mw` is not on PATH. Touching fence line-prefix or fence-scanning logic? Exercise it here (or the Chroma fixtures in `test_fence.py`): the in-process round-trip uses Pygments and will not catch Chroma-only bugs.
- Test our logic only; do not test Python-Markdown, pymdownx, argparse, or pygments behavior.

## Plan & Progress Tracking

- `spec.md`, `plan.md`, `todo.md` (repo root): the 0.2.0 config-system cycle (shipped in #10, not yet archived). `spec.md` still documents the config schema, discovery, and precedence.
- GitHub issues drive work since 0.2.0 (0.3.0 was issues #11 and #13 plus the skill 2.0 audit). `CHANGELOG.md` records each release.
- `.ai-sessions/v0.1-remediation/{spec,plan,todo,accomplishment}.md`: the **completed** step-55 remediation (R1 through R11, shipped as 0.1.0). `accomplishment.md` is the durable record; the marker contract and parity Decisions (D1, D2, D3) live in its `spec.md`.
- `.ai-sessions/v1-init/{plan,todo}.md`: the archived v1 extension plan with the HTML Output Contracts.
- `.ai-sessions/`: session summaries (read the most recent for context). `.ai-sessions/lessons.md` accumulates cross-session lessons.
