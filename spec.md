# markwright

## Starting context

Recorded at the pre-0.7 spec migration on 2026-10-11, not at project start.
markwright is a maintained library and 0.3.0 is shipping.
Mason authors it and knows the codebase deeply.
Future work is issue-driven, not a planned phase.

## Project overview

markwright is a set of [Python-Markdown](https://python-markdown.github.io/) extensions plus an `mw` command-line tool that runs the same extensions as pre and post filter stages so the author-facing syntax works in any toolchain (Hugo, a plain Unix pipe), not only an in-process Python-Markdown render.
Part of it is a port: the eight original extensions reproduce the syntax and HTML output of DigitalOcean's [`do-markdownit`](https://github.com/digitalocean/do-markdownit) (JavaScript/markdown-it, Apache 2.0), so those render the way DigitalOcean's do.
Everything else is markwright's own, most notably the CLI, a config surface with a public API host tools build on, click-to-load embeds, and the 0.4.0 and later extensions modeled on the mkdocs-material reference.
The bundled MkDocs Material site in `docs/` is both documentation and a live demo.
It moves to Bartleby (Mason's static site generator and markwright's first host) once Bartleby reaches parity and releases, well ahead of Material for MkDocs' end of life on May 5, 2027.

markwright is pre-1.0 and has one user, so its cross-tool contracts are versioned and read fail-soft but carry no compatibility obligation until 1.0: a contract change bumps its version and ships with no shim.
It grows through issues.
Its scope rule: markwright owns syntax that no maintained Python-Markdown or pymdown-extensions extension provides, plus block-level features the `mw` pipeline needs because Hugo has no equivalent (tabs is the one such feature so far).
Material for MkDocs is in maintenance until its end of life, so its reference pages are a frozen snapshot to compare against, not a target to track; Python-Markdown and pymdown-extensions are the maintained line.
markwright emits markup only; hosts (Bartleby's themes, or anyone's) own the JavaScript and CSS, and markwright's docs carry small working samples of both.
Likely future directions are tracked under Roadmap Deferred.

## Invariants

- Python: per the `python:python` skill and the Code Conventions in CLAUDE.md
- Docs prose: per the `content-design` skill and the writing rules in CLAUDE.md
- Stack: a pure-Python package on Python 3.11 through 3.15, built with `hatchling`, managed with `uv`; `just check` (ruff, ruff format, mypy strict, pytest) is the gate and runs after every change
- Runtime dependencies are `markdown`, `pymdown-extensions` (floor `>=11.0.1`, set by a security fix), and `pydantic`; adding another needs a spec change
- deps: frozen
- paths: src/markwright/**, tests/**, docs/**, mkdocs.yml, README.md, CHANGELOG.md, CLAUDE.md, plan.md, todo.md, .ai-sessions/**
- Coverage is reported (line and branch) but not gated; read it and either test or delete what it shows uncovered
- Output stays at `do-markdownit` parity (the eight ported extensions) unless a Decision documents a divergence; the cross-tool contracts are versioned and read fail-soft: the `mw-fence`, `mw-grid`, `mw-grid-block`, `mw-grid-end`, `mw-card`, `mw-card-end`, `mw-grid-problem`, `mw-tab`, `mw-tab-end`, `mw-tab-problem`, and `mw-annotate` marker-comment payloads, the `mw-embed` preview, the `mw-annotation` list's `data-mw-version`, the grid and card classes, and the tab markup with its `mw-tab-S-T` ids; before 1.0 a contract change bumps its version with no compatibility shim
- The package ships no JavaScript, no CSS, and no bundled assets, icons included: markwright owns markup and inlines host-supplied SVGs; hosts own behavior, styling, and the icon files
- Progressive enhancement: every extension's markup is readable with no host CSS and no host JavaScript, and host code only enhances it (annotations fall back to a numbered list, click-to-load embeds to a direct link, tabs switch with CSS alone)
- New author-facing syntax is a standalone `[name ...]` line, either a directive or a container's opener or closer; markwright adds no inline delimiters (`$`, `~`, `^`, `==`, `++`, and the like belong to pymdown-extensions)
- markwright emits classes, data attributes, and ids, never inline `style` attributes
- Container pairing scans lines through `_fences`, so an opener or closer inside fenced or indented code stays literal; no Markdown parser is added
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
- material-parity-0.4.0: the six Material-reference extensions (#16) and the shared `_markers` module, converged and staged for the 0.4.0 release (.ai-sessions/material-parity-0.4.0/)
- fenced-directives-20: `mw pre` leaves a directive line inside fenced code literal across all ten directive stages through `_fences.map_lines` (#20), converged (.ai-sessions/fenced-directives-20/)
- review-fixes-29: the eight 0.4.0 adversarial-review fixes (annotate chaining, tab and indented-code detection, HTML-tag skipping, icons at priority 85, and the test-policy cleanup) (#29), converged (.ai-sessions/review-fixes-29/)
- containers-30: block grids, cards, column counts, and the `tabs` extension on one shared open/close pairing scanner (#30), converged (.ai-sessions/containers-30/)

**Upcoming:**
- public fence API: a public function that reports a document's disallowed fence environments, so Bartleby stops importing `markwright._fences` and fence's regexes; a separate issue (#32)
- Material mapping docs page: maps each mkdocs-material reference feature to the Python-Markdown or pymdown-extensions extension that provides it in-process and the Goldmark setting that provides it in Hugo, with the gaps; docs-only, done directly

**Deferred:**
- New embeds (Bluesky, Mastodon, Vimeo): possible later; each should support the `load` option when it lands
- User-level config layer (`~/.config/markwright/`): project-level config only for now
- `youtube-nocookie` option: reduces tracking even for `eager`; worth a separate issue
- `mw-` rename of the existing embed CSS classes: align them with the `mw-embed` preview hooks; nothing blocks it before 1.0, but it is a separate concern from the containers phase
- Richer Material-parity features past the 0.4.0 contracts: lightbox galleries, captions, and `srcset`; annotation forms beyond a block plus its following list; each 0.4.0 extension stays minimal, revisit per issue
- `mw pre` parity inside Markdown constructs it cannot see without a parser: a highlight marker or icon shortcode inside an image's alt text, a link title, or the text content of a raw HTML block is rewritten by `mw pre` and left literal in-process; `map_prose` skips HTML tags, comments, and autolinks (the single-line grammar) and indented code (the line scanner), the rest needs a block-level scanner or a Decision that the CLI's behavior is the reference, revisit per issue
- Grid extras: card column spans (`[card 2]`), per-breakpoint column counts (`[grid 1 2 3]`), and config defaults for columns, gap, or minimum width; revisit per issue
- Tab extras: a marker that selects a tab other than the first, and one that forces a new set right after another; revisit when a page needs either
- Move the docs site to Bartleby: once Bartleby reaches parity and releases, before May 5, 2027; the docs keep loading markwright's own CSS and JavaScript samples through Bartleby's `extra_css` and `extra_js`, so the samples stay exercised
- Full `mw pre` idempotence for a document with container problems: a line that already carries a problem marker is not read as a directive on a second pass, so a `[card]` outside a grid leaves its `[/card]` to gain a stray-closer report; a valid document is unaffected, revisit if a pipeline runs `mw pre` twice
- pymdown-extensions 13.0: check markwright and Bartleby against it before the next markwright release, since the `>=11.0.1` floor resolves to it on a fresh install

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
- `grid`: `[grid]` or `[grid cards]` before a list classes the following `<ul>` or `<ol>` with `mw-grid` (plus `mw-grid-cards`, renamed from `mw-cards` in the containers phase), carried pre-to-post as a `<!-- mw-grid -->` marker comment. Block grids, cards, and column counts are under Containers below.
- `mermaid`: a `mermaid` fence becomes `<pre class="mermaid">` with the source HTML-escaped and otherwise intact and no `<code>` wrapper, matching mermaid.js's default selector. Pre-stage only; its own extension, not a fence feature, so it can be disabled on its own and fence parity is untouched.
- `icons`: `:pack-name:` resolves against the `packs` option, a prefix-to-directory map the host supplies, and inlines the SVG as `<span aria-hidden="true" class="mw-icon"><svg>...</svg></span>`. markwright ships no icons; an unconfigured or unmatched shortcode stays literal text, an empty `packs` warns, a missing directory is a boundary error. Resolves in prose only, never inside code.
- `annotate`: `[annotate]` before a block links each `(1)` marker in the block to the M-th item of the ordered list after it (`<a class="mw-annotation" href="#mw-annotation-N-M">`), classes the block `mw-annotated` and the list `mw-annotations` with `data-mw-version`, and for a `# (1)!` form in code strips the comment token around the marker (Pygments in-process, Chroma through Hugo; other highlighters degrade to the plain form). Carried as a `<!-- mw-annotate -->` marker comment; its post stage runs before fence's so the fence marker is still a comment when the block is located.
- The marker-comment handling (comment-safe encode, locate with block bounds, fail-soft decode) is extracted to a shared module, and `fence` moves onto it with no change to the `mw-fence` payload or output.
- The docs site renders all six live: a pinned mermaid.js from a CDN plus a small `docs/javascripts/` wire the mermaid init, the lightbox `<dialog>`, and the annotation tooltips, and a small, credited, liberally-licensed icon set is committed under `docs/icons/` and configured as a demo pack. Each extension gets a docs page with its contract and a demo, and the `mw pre | hugo | mw post` pipeline carries all six.

### Containers: Block Grids, Cards, and Tabs (Issue #30)

A container is an opener line and a closer line with arbitrary Markdown between them.
It is the first markwright syntax that is neither a single line nor a marker for the single block after it.
Block grids, cards, and tabs share one pairing scanner, so the rules are written once.

Pairing:

- Openers are `[grid ...]`, `[card]`, and `[tab NAME]`; closers are `[/grid]`, `[/card]`, and `[/tab]`, each alone on its line.
- A closer pairs with the nearest unpaired opener of the same kind at the same indentation, matched like brackets; an opener a closer skips over is unclosed.
- An opener and its closer sit at the same indentation, at the top level or inside a list item; in any other context (a blockquote, say) the lines stay literal.
- Containers nest freely: a grid in a card, a grid in a grid, tabs in a card, a grid in a tab.
- An opener or closer line inside fenced or indented code stays literal.
- An unclosed `[card]` or `[tab]`, a stray closer, or a paired `[card]` whose nearest enclosing container is not a block grid stays literal text and is reported under `--warn`.
  A `[card]` outside a block grid is reported once, on its opener.
- `mw pre` and `mw post` are separate processes, so each report travels as a problem marker: the pre stage appends an `mw-grid-problem` (grid and card lines) or `mw-tab-problem` (tab lines) comment to the literal line, and the post stage composes one `--warn` message from it and removes the comment.
  The payload is `version` 1, the 1-based source `line`, the `directive`, and a `reason` from a closed vocabulary (`unclosed`, `stray-closer`, `card-outside-grid`), so a hand-written marker cannot put arbitrary text on stderr.
- An unclosed `[grid ...]` is the list shortcut from 0.4.0: it classes the following list, or is skipped and reported under `--warn` when no list follows.
  A shortcut grid inside a block grid therefore needs its own `[/grid]`, since the outer closer would otherwise pair with it.
  A `[/grid]` with no opener at its indentation is a stray closer, and the nearest `[grid ...]` still open at another indentation then stays literal instead of becoming the shortcut, since its author meant a block grid; only the closer is reported.

Grids and cards:

- The grid opener is `[grid]` with optional tokens in any order, each at most once: `cards`, and a column count from 1 to 6.
  `[grid 3]`, `[grid cards 3]`, and `[grid 3 cards]` are all valid; any other token or count leaves the line literal.
- A paired grid wraps everything between its lines in `<div class="mw-grid">`, plus `mw-grid-cards` with `cards` and `mw-grid-cols-N` with a count; each child block is a grid cell.
- The list shortcut takes the same tokens and puts the same classes on the `<ul>` or `<ol>`.
- `mw-cards` is renamed `mw-grid-cards` everywhere.
- `[card]` ... `[/card]` wraps its content in `<div class="mw-card">`, so one card can hold several blocks (a heading, a paragraph, a list, a link).
- A list inside a block grid with `cards` keeps its markup; host CSS makes each item a cell (the sample uses `display: contents` on the list, as Material did).
- Markers: the list shortcut keeps `mw-grid` (version 1, gaining an optional `columns`); a block grid is `mw-grid-block` (version 1, with `cards` and `columns`) and `mw-grid-end`; a card is `mw-card` and `mw-card-end` (version 1).

Tabs:

- `[tab NAME]` ... `[/tab]` is one tab; NAME is the rest of the opener line, trimmed, non-empty, without `]`, and may hold spaces (`[tab Node.js 20]`).
  A `[tab ]` with no name is not an opener: it stays literal with no report, and a `[/tab]` it leaves unpaired is a stray closer.
- Tabs separated only by blank lines group into one set, any other content between them starts a new set, and the first tab in a set is selected.
- The name renders as escaped plain text; inline Markdown in it is not rendered.
- A set renders as pymdown-extensions' `tabbed` `alternate_style` markup, so a host's existing tab CSS styles it: `<div class="tabbed-set tabbed-alternate mw-tabs" data-tabs="S:N">`, one radio `<input>` per tab (`id="mw-tab-S-T"`, `name="mw-tab-S"`, the first `checked`), a `<div class="tabbed-labels">` of `<label for="mw-tab-S-T">`, then a `<div class="tabbed-content">` holding one `<div class="tabbed-block">` per tab.
- S counts sets and T counts tabs within a set, both from 1, per document; the `mw-tab-` prefix keeps the ids from colliding with pymdown-extensions' `__tabbed_` ids when a host loads both.
- Markers: `mw-tab` (version 1, with `name`, and `first`, true for a tab that starts a set) and `mw-tab-end`.
- `tabs` is a new extension name with no options, on by default like the rest.

Both paths:

- The pre stages emit each container marker as an HTML comment on its own line with a blank line on either side, at the opener's indentation, so the content between renders as normal Markdown in Python-Markdown and in Goldmark.
  A problem marker is the exception: it sits on the literal line, after the directive, so the line still renders as the text the author wrote.
- Grid and tabs both run their pre stage at 20, so either may scan a document the other has already rewritten.
  The scanner reads a line that is solely one of the six paired container markers as the opener or closer it stands for, so pairing and card enclosure come out the same in either order, and a stage leaves a pair that is already its own markers alone.
  `mw pre` over its own output therefore leaves a valid document's container markers unchanged.
- The post stages wrap the content through `_html` span edits and remove the markers; the in-process postprocessors run at 30 with grid and annotate, ahead of fence.
- `tests/test_roundtrip.py` and its hypothesis grammar cover containers, and the Hugo integration test carries a block grid with cards and a tab set.

Docs:

- `docs/extensions/grid.md` leads with a block-grid demo, and a new `docs/extensions/tabs.md` leads with a tab-set demo.
- `docs/stylesheets/extra.css` gains the column, card, and narrow-screen rules and a CSS-only tab sample whose selector chains cover six tabs per set.
- Every extension page has a "Host CSS and Script" section that lists the classes, data attributes, and ids a host styles and links the sample; a page whose extension needs neither says so.
- The README and the CHANGELOG list the containers and the `mw-grid-cards` rename.

## Non-goals

Permanent; markwright does not do these:

- Ship JavaScript or CSS in the package. markwright emits stable class and data hooks; the host supplies behavior and styling.
- Change the all-on default (every extension loaded unless config says otherwise).
- Change extension output or break `do-markdownit` parity without a documented Decision.
- Reimplement syntax Python-Markdown or pymdown-extensions already provide: admonitions, math, critic markup, keys, mark, caret, tilde, abbreviations, and task and definition lists.
  Tabs is the one exception, kept because Hugo has no tabs; markwright's tabs emit `tabbed`'s markup rather than competing with it.
- Ship the theme behavior Material for MkDocs carried in its own JavaScript and CSS: linked tabs, tab anchor selection, styled tooltips, sortable tables, math loading, and code copy.
  That is host work, and Bartleby's themes port what Bartleby needs.
- A `:::name` container delimiter, or an alias for one; containers use the `[name]` and `[/name]` family.
- A generic container that adds arbitrary classes (`[div .class]`); that is Python-Markdown's `md_in_html` and `attr_list`.
- Bundle or depend on an icon set, or ship SVG or other assets in the package. The icons extension resolves against directories the host supplies.

## Component boundaries

- **Two consumers over one set of pure stage functions.** Each extension module exposes `expand_source` (the `mw pre` source stage) and, where it has one, `apply_html` (the `mw post` HTML stage). The in-process Python-Markdown `Extension` classes and the `mw` CLI both delegate to these, so the logic is written once.
- **`config.py`** owns discovery, parsing, validation, the resolved `Config` (a frozen pydantic model), and the public host API. It depends on `registry` (`EXTENSION_NAMES`, `OPTION_NAMES`, `REGISTRY`) and nothing else; never on `cli`.
- **`registry.py`** maps each extension name to a pydantic `StageSpec` (stage functions, priorities, the extension class, its option checker) and provides `run_pre`, `run_post`, and `describe`. Selection lives in `config.selected_extensions`; there is no `registry.select_extensions`.
- **`_fences.py`** (CommonMark fenced-code scanning) and **`_html.py`** (offset-preserving tokenizing over the stdlib `html.parser`) own structured-text parsing. No stage hand-rolls Markdown-structure or HTML regex; single-line token grammars (embed directives, the marker comment) may stay regex.
- **`_markers.py`** owns the marker-comment contract the post stages share: comment-safe encoding (every `<` and `>` escaped so a payload can never close the comment early), locating markers among `_html` tokens with each marker's block bounds, and fail-soft decode into a strict pydantic payload model. It also owns the emission and pairing helpers `grid` and `tabs` share: `marker_block` (one marker as its own indented block, blank lines around it), `inline_problem_marker`, `match_marker_pairs` (stack-match open and close markers by position), and `report_problem_markers`. `fence`, `grid`, `tabs`, and `annotate` depend on it; it depends only on `_html`.
- **`_containers.py`** owns container pairing: from the source text it returns each pair (kind, opener line, closer line, indentation, opener tokens, whether the nearest enclosing container is a grid, and whether its lines were already marker comments), each unpaired or misplaced line with its reason, and each unclosed `[grid ...]` shortcut, skipping fenced and indented code through `_fences`. It holds the opener and closer grammars and the names of the six paired container markers, which `grid` and `tabs` import, so it can read an emitted marker line as the opener or closer it stands for. `grid` (block grids and cards) and `tabs` call it, the second caller that justifies the module; it depends only on `_fences`. Its pairing rules are a self-contained algorithm with a contract of its own, so `tests/test_containers.py` tests it directly, as the `_fences` and `_markers` tests do.
- **`tabs.py`** is a marker-comment pre-plus-post pair like `grid`; its post stage builds each set's inputs and labels from that set's `mw-tab` payloads.
- **The six 0.4.0 extensions follow the existing patterns**, so no new machinery: `button` and `lightbox` are directive-expand pre stages like the embeds; `mermaid` and `icons` are pre-only (a fence rewrite and an inline-processor resolver); `grid` and `annotate` are marker-comment pre-plus-post pairs like `fence`. Their shared helpers are second-caller extractions: `_fences.map_prose` (prose outside fences and inline code, shared by `highlight` and `icons`), and `_html.add_classes` and `_html.matching_end` (shared by `fence`, `grid`, and `annotate`).
- **`cli.py`** wires config into each subcommand and is the single place exceptions become exit codes (`ConfigError`, or a `ConfigWarning` escalated with `-W error`, prints `mw: error:` and exits 2).

## Success criteria

- `just check` is green: ruff clean, ruff format clean, mypy strict clean, pytest passing, coverage reported.
- `just test-integration` is green: the `mw pre | hugo | mw post` pipeline through a real Hugo build, and a clean-venv wheel install.
- `just docs-build` (strict) is clean and every page in the MkDocs nav exists.
- Rendered output matches the `do-markdownit` reference format for the eight ported extensions; the `mw-fence`, `mw-grid`, container, and `mw-annotate` markers and the `mw-embed` preview stay versioned and read fail-soft.
- Containers render on the docs demo (block grids with column counts and cards, and a tab set that switches with the CSS sample alone), and the `mw pre | hugo | mw post` integration test carries a block grid with cards and a tab set.
- Every extension page has its Host CSS and Script section, and every extension's markup reads correctly with the docs site's CSS and JavaScript turned off.
- The six 0.4.0 extensions render live on the docs demo (mermaid, lightbox, and annotations wired through the committed `docs/javascripts/` and icon set) and the `mw pre | hugo | mw post` integration test carries all six.
