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
- Output stays at `do-markdownit` parity (the eight ported extensions) unless a Decision documents a divergence; the cross-tool contracts are versioned and read fail-soft: the `mw-fence`, `mw-grid`, and `mw-annotate` marker-comment payloads, the `mw-embed` preview, and the `mw-annotation` list's `data-mw-version`
- The package ships no JavaScript, no CSS, and no bundled assets, icons included: markwright owns markup and inlines host-supplied SVGs; hosts own behavior, styling, and the icon files
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
- config-system: the 0.2.0 config system and `mw` CLI simplification, converged (.ai-sessions/config-system/)

**Upcoming:**
- material-parity (0.4.0): issue #16, the six Material-reference extensions (button, lightbox, grid, mermaid, icons, annotate) so a host theme can render every feature on the mkdocs-material reference from markwright markup alone. Decided: directive and fence syntax in the existing family, `mw-` hooks, a fully-live docs demo (a pinned mermaid.js CDN, a new `docs/javascripts/`, and a small committed demo icon set), and `fence` refactored onto a shared marker-comment module with no change to its output. Decisions D1 through D7 and the byte-level contracts are in .ai-sessions/material-parity/spec.md, with a draft step plan beside it

**Deferred:**
- New embeds (Bluesky, Mastodon, Vimeo): possible later; each should support the `load` option when it lands
- User-level config layer (`~/.config/markwright/`): project-level config only for now
- `youtube-nocookie` option: reduces tracking even for `eager`; worth a separate issue
- `mw-` rename of the existing embed CSS classes: align them with the `mw-embed` preview hooks; still deferred, not folded into 0.4.0, since it is a breaking change to shipped embed hooks and a separate concern from the additive extensions
- Richer Material-parity features past the 0.4.0 contracts: lightbox galleries, captions, and `srcset`; grid column controls and nested grids; annotation forms beyond a block plus its following list; each 0.4.0 extension stays minimal, revisit per issue

## Goals

markwright is edited in place as it evolves; today it delivers:

- The eight ported extensions, with HTML output matching the `do-markdownit` reference: highlight, fence, youtube, codepen, twitter, instagram, slideshow, image_compare.
- The `mw` CLI (`pre`, `post`, `render`, `config`, `list`) so the syntax works around any renderer, not only an in-process Python-Markdown call.
- A config surface (`markwright.toml` or a `[tool.markwright]` table) for extension selection and per-extension options, with a public API (`config_from_mapping`, `selected_extensions`, `extension_configs`, plus `Config`, `ConfigError`, `ConfigWarning`, `OptionError`) that host tools build on and `mw render` itself uses.
- Click-to-load embeds (the `load` option: `eager`, `lazy`, `click`) so third-party embeds defer until a reader asks, with a versioned preview contract and no shipped JS.
- The MkDocs Material docs site that documents and demonstrates every extension and the renderer contract.

### 0.4.0, Material reference parity (issue #16)

Six additive extensions so a host theme can render every feature on the mkdocs-material reference from markwright markup alone. Each is additive: documents 0.3.0 rendered stay byte-identical. markwright owns the authoring syntax and the `mw-` HTML contract; the host supplies CSS, JavaScript, and icon files. The full byte-level contracts and decisions D1 through D7 live in `.ai-sessions/material-parity/spec.md`.

- `button`: `[button URL TEXT]` (and `[button primary URL TEXT]`) on its own line becomes `<a class="mw-button">` (plus `mw-button-primary`). Pre-stage only; inline raw HTML, so a renderer wraps it in `<p>` and inline Markdown in the text still renders.
- `lightbox`: `[lightbox URL ALT]` becomes `<a class="mw-lightbox" href="URL"><img src="URL" alt="ALT" /></a>`. Pre-stage only. Without a host script the link opens the image.
- `grid`: `[grid]` or `[grid cards]` before a list classes the following `<ul>` or `<ol>` with `mw-grid` (plus `mw-cards`), carried pre-to-post as a `<!-- mw-grid -->` marker comment.
- `mermaid`: a `mermaid` fence becomes `<pre class="mermaid">` with the source HTML-escaped and otherwise intact and no `<code>` wrapper, matching mermaid.js's default selector. Pre-stage only; its own extension, not a fence feature, so it can be disabled on its own and fence parity is untouched.
- `icons`: `:pack-name:` resolves against the `packs` option, a prefix-to-directory map the host supplies, and inlines the SVG as `<span aria-hidden="true" class="mw-icon"><svg>...</svg></span>`. markwright ships no icons; an unconfigured or unmatched shortcode stays literal text, an empty `packs` warns, a missing directory is a boundary error. Resolves in prose only, never inside code.
- `annotate`: `[annotate]` before a block links each `(1)` marker in the block to the M-th item of the ordered list after it (`<a class="mw-annotation" href="#mw-annotation-N-M">`), classes the block `mw-annotated` and the list `mw-annotations` with `data-mw-version`, and for a `# (1)!` form in code strips the comment token around the marker (Pygments in-process, Chroma through Hugo; other highlighters degrade to the plain form). Carried as a `<!-- mw-annotate -->` marker comment; its post stage runs before fence's so the fence marker is still a comment when the block is located.
- The marker-comment handling (comment-safe encode, locate with block bounds, fail-soft decode) is extracted to a shared module, and `fence` moves onto it with no change to the `mw-fence` payload or output.
- The docs site renders all six live: a pinned mermaid.js from a CDN plus a small `docs/javascripts/` wire the mermaid init, the lightbox `<dialog>`, and the annotation tooltips, and a small, credited, liberally-licensed icon set is committed under `docs/icons/` and configured as a demo pack. Each extension gets a docs page with its contract and a demo, and the `mw pre | hugo | mw post` pipeline carries all six.

## Non-goals

Permanent; markwright does not do these:

- Ship JavaScript or CSS in the package. markwright emits stable class and data hooks; the host supplies behavior and styling.
- Change the all-on default (every extension loaded unless config says otherwise).
- Change extension output or break `do-markdownit` parity without a documented Decision.
- Reimplement features stock pymdownx or Material already provide: admonitions, content tabs, code copy and select, sortable tables, and math. Issue #16's analysis confirms markwright adds nothing for these; they are existing pymdownx extensions or host CSS and JavaScript.
- Bundle or depend on an icon set, or ship SVG or other assets in the package. The icons extension resolves against directories the host supplies.

## Component boundaries

- **Two consumers over one set of pure stage functions.** Each extension module exposes `expand_source` (the `mw pre` source stage) and, where it has one, `apply_html` (the `mw post` HTML stage). The in-process Python-Markdown `Extension` classes and the `mw` CLI both delegate to these, so the logic is written once.
- **`config.py`** owns discovery, parsing, validation, the resolved `Config` (a frozen pydantic model), and the public host API. It depends on `registry` (`EXTENSION_NAMES`, `OPTION_NAMES`, `REGISTRY`) and nothing else; never on `cli`.
- **`registry.py`** maps each extension name to a pydantic `StageSpec` (stage functions, priorities, the extension class, its option checker) and provides `run_pre`, `run_post`, and `describe`. Selection lives in `config.selected_extensions`; there is no `registry.select_extensions`.
- **`_fences.py`** (CommonMark fenced-code scanning) and **`_html.py`** (offset-preserving tokenizing over the stdlib `html.parser`) own structured-text parsing. No stage hand-rolls Markdown-structure or HTML regex; single-line token grammars (embed directives, the marker comment) may stay regex.
- **`_markers.py`** owns the marker-comment contract the post stages share: comment-safe encoding (every `<` and `>` escaped so a payload can never close the comment early), locating markers among `_html` tokens with each marker's block bounds, and fail-soft decode into a strict pydantic payload model. `fence`, `grid`, and `annotate` depend on it; it depends only on `_html`.
- **The six 0.4.0 extensions follow the existing patterns**, so no new machinery: `button` and `lightbox` are directive-expand pre stages like the embeds; `mermaid` and `icons` are pre-only (a fence rewrite and an inline-processor resolver); `grid` and `annotate` are marker-comment pre-plus-post pairs like `fence`. Their shared helpers are second-caller extractions: `_fences.map_prose` (prose outside fences and inline code, shared by `highlight` and `icons`), and `_html.add_classes` and `_html.matching_end` (shared by `fence`, `grid`, and `annotate`).
- **`cli.py`** wires config into each subcommand and is the single place exceptions become exit codes (`ConfigError`, or a `ConfigWarning` escalated with `-W error`, prints `mw: error:` and exits 2).

## Success criteria

- `just check` is green: ruff clean, ruff format clean, mypy strict clean, pytest passing, coverage reported.
- `just test-integration` is green: the `mw pre | hugo | mw post` pipeline through a real Hugo build, and a clean-venv wheel install.
- `just docs-build` (strict) is clean and every page in the MkDocs nav exists.
- Rendered output matches the `do-markdownit` reference format for the eight ported extensions; the `mw-fence`, `mw-grid`, and `mw-annotate` markers and the `mw-embed` preview stay versioned and read fail-soft.
- The six 0.4.0 extensions render live on the docs demo (mermaid, lightbox, and annotations wired through the committed `docs/javascripts/` and icon set) and the `mw pre | hugo | mw post` integration test carries all six.
