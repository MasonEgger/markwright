# markwright

## Starting context

Recorded at the pre-0.7 spec migration on 2026-10-11, not at project start.
markwright is a maintained library and 0.3.0 is shipping.
Mason authors it and knows the codebase deeply.
Future work is issue-driven, not a planned phase.

## Project overview

markwright is a set of [Python-Markdown](https://python-markdown.github.io/) extensions ported from DigitalOcean's [`do-markdownit`](https://github.com/digitalocean/do-markdownit) (JavaScript/markdown-it, Apache 2.0), plus an `mw` command-line tool that runs the same extensions as pre and post filter stages so the author-facing syntax works in any toolchain (Hugo, a plain Unix pipe), not only an in-process Python-Markdown render.
The author-facing syntax and HTML output are derived from `do-markdownit`, so rendered pages match what DigitalOcean produces; markwright adds its own pieces on top, most notably the CLI, a config surface with a public API host tools build on, and click-to-load embeds.
The bundled MkDocs Material site in `docs/` is both documentation and a live demo.

The project is maintained rather than in active feature development: it stays at parity with `do-markdownit`, keeps its cross-tool contracts stable, and grows through issues. Likely future directions are tracked under Roadmap Deferred.

## Invariants

- Python: per the `python:python` skill and the Code Conventions in CLAUDE.md
- Docs prose: per the `content-design` skill and the writing rules in CLAUDE.md
- Stack: a pure-Python package on Python 3.11 through 3.15, built with `hatchling`, managed with `uv`; `just check` (ruff, ruff format, mypy strict, pytest) is the gate and runs after every change
- Runtime dependencies are `markdown`, `pymdown-extensions` (floor `>=11.0.1`, set by a security fix), and `pydantic`; adding another needs a spec change
- deps: frozen
- paths: src/markwright/**, tests/**, docs/**
- Coverage is reported (line and branch) but not gated; read it and either test or delete what it shows uncovered
- Output stays at `do-markdownit` parity unless a Decision documents a divergence; the `mw-fence` marker payload and the `mw-embed` preview are versioned cross-tool contracts, read fail-soft
- The package ships no JavaScript and no CSS: markwright owns markup, hosts own behavior and styling
- Config law (see `docs/config.md`, Config Rules): omitting a key means its default, a list names exactly what it holds (empty allowlist allows nothing, empty denylist removes nothing), a setting that makes a feature a no-op is legal but emits a `ConfigWarning`, and every option is validated at the boundary with a `ConfigError`, never a traceback
- Library code raises; only the `mw` CLI boundary turns exceptions into exit codes
- `__init__.py` re-exports only the public API with `__all__`
- The `do-markdownit` name is preserved in attribution (NOTICE, README); the package and CLI use the `markwright` / `mw` brand
- Never commit to `main`; branch, open a PR, squash-merge, and only Mason merges

## Available tooling

Tools the `bpe:validator` agent should consult when reviewing diffs in `/bpe:goal` runs. `/bpe:plan` propagates these to per-section declarations in plan.md.

**MCPs:**
- none

**Skills:**
- python:python
- content-design:review-content

**Notes:** Validator should apply the `python:python` taste profile to code under `src/markwright/` and `tests/`, and the `content-design` review to prose under `docs/`, the README, and the CHANGELOG. The repo's own gate (`just check`) owns correctness, coverage, lint, and types, so the validator focuses on taste and convention rather than re-running tests.

## Roadmap / phase log

**Shipped:**
- v1-init: the initial `do-markdownit` port (the eight extensions) and the `mw` pipeline CLI (.ai-sessions/v1-init/)
- v0.1-remediation: the step-55 audit remediation (R1 through R11), shipped as 0.1.0 (.ai-sessions/v0.1-remediation/)

**Upcoming:**
- none; work is issue-driven

**Deferred:**
- New embeds (Bluesky, Mastodon, Vimeo): possible later; each should support the `load` option when it lands
- User-level config layer (`~/.config/markwright/`): project-level config only for now
- `youtube-nocookie` option: reduces tracking even for `eager`; worth a separate issue
- `mw-` rename of the existing embed CSS classes: align them with the `mw-embed` preview hooks

## Goals

markwright is edited in place as it evolves; today it delivers:

- The eight ported extensions, with HTML output matching the `do-markdownit` reference: highlight, fence, youtube, codepen, twitter, instagram, slideshow, image_compare.
- The `mw` CLI (`pre`, `post`, `render`, `config`, `list`) so the syntax works around any renderer, not only an in-process Python-Markdown call.
- A config surface (`markwright.toml` or a `[tool.markwright]` table) for extension selection and per-extension options, with a public API (`config_from_mapping`, `selected_extensions`, `extension_configs`, plus `Config`, `ConfigError`, `ConfigWarning`, `OptionError`) that host tools build on and `mw render` itself uses.
- Click-to-load embeds (the `load` option: `eager`, `lazy`, `click`) so third-party embeds defer until a reader asks, with a versioned preview contract and no shipped JS.
- The MkDocs Material docs site that documents and demonstrates every extension and the renderer contract.

## Non-goals

Permanent; markwright does not do these:

- Ship JavaScript or CSS in the package. markwright emits stable class and data hooks; the host supplies behavior and styling.
- Change the all-on default (every extension loaded unless config says otherwise).
- Change extension output or break `do-markdownit` parity without a documented Decision.

## Component boundaries

- **Two consumers over one set of pure stage functions.** Each extension module exposes `expand_source` (the `mw pre` source stage) and, where it has one, `apply_html` (the `mw post` HTML stage). The in-process Python-Markdown `Extension` classes and the `mw` CLI both delegate to these, so the logic is written once.
- **`config.py`** owns discovery, parsing, validation, the resolved `Config` (a frozen pydantic model), and the public host API. It depends on `registry` (`EXTENSION_NAMES`, `OPTION_NAMES`, `REGISTRY`) and nothing else; never on `cli`.
- **`registry.py`** maps each extension name to a pydantic `StageSpec` (stage functions, priorities, the extension class, its option checker) and provides `run_pre`, `run_post`, and `describe`. Selection lives in `config.selected_extensions`; there is no `registry.select_extensions`.
- **`_fences.py`** (CommonMark fenced-code scanning) and **`_html.py`** (offset-preserving tokenizing over the stdlib `html.parser`) own structured-text parsing. No stage hand-rolls Markdown-structure or HTML regex; single-line token grammars (embed directives, the marker comment) may stay regex.
- **`cli.py`** wires config into each subcommand and is the single place exceptions become exit codes (`ConfigError`, or a `ConfigWarning` escalated with `-W error`, prints `mw: error:` and exits 2).

## Success criteria

- `just check` is green: ruff clean, ruff format clean, mypy strict clean, pytest passing, coverage reported.
- `just test-integration` is green: the `mw pre | hugo | mw post` pipeline through a real Hugo build, and a clean-venv wheel install.
- `just docs-build` (strict) is clean and every page in the MkDocs nav exists.
- Rendered output matches the `do-markdownit` reference format; the `mw-fence` marker and `mw-embed` preview stay versioned and read fail-soft.
