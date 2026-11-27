# Changelog

All notable changes to markwright are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- An `[environment NAME]` directive outside `fence.allowed_environments` is now reported, in `mw post --warn`, `mw render --warn`, and in-process, as a `Diagnostic` with the reason `disallowed-environment`.
  The `mw-fence` marker (still version 1) carries `disallowed_environment` and `line` for it.
  A fence holding an unlisted `[environment NAME]` now gains an `mw-fence` marker, so it renders as its own block like any fence with a directive.
- The docs site loads `docs/hooks/strict_warnings.py`, which logs each `RenderWarning` at WARNING so `mkdocs build --strict` fails on a markwright diagnostic.
  The MkDocs integration page documents it as a host example.

### Fixed

- A multi-line HTML comment is now skipped by every stage, in both paths: a `[tab]`, `[youtube ...]`, or `[annotate]` line, a fence directive, a highlight marker, or an icon shortcode inside one stays as written.
  Before, the `-->` of a marker comment `mw pre` wrote inside the author's comment ended it, and the commented-out text was published.
- A `<pre>`, `<script>`, `<style>`, or `<textarea>` block is now verbatim to every pre stage, so a directive, a highlight marker, or an icon shortcode inside one stays literal.
  Before, only icons skipped a block, and only one that opened with `<pre class="mermaid">`.
- A fenced code block inside a block quote, such as a `> [!NOTE]` alert, is now read as code.
  Its `[label]`, `[secondary_label]`, and `[environment]` directives and its prefix flags apply in-process and through `mw pre | renderer | mw post`; they used to stay in the block as text.
  `mw pre` also leaves a highlight marker, an icon shortcode, and a directive line inside such a block for the code, where it used to rewrite them as prose.
  A `mermaid` fence inside a block quote stays a code block.

## [0.4.0] - 2026-11-22

Six new extensions that cover the Material for MkDocs authoring features (#16), a `tabs` extension plus block grids and cards on the `grid` extension (#30), and the docs-site pieces that demonstrate them.
A document that uses none of the new directives or shortcodes renders as it did, apart from the changes listed under Upgrading from 0.3.0 and Fixed.

### Upgrading from 0.3.0

- The new extensions are on by default in `mw`, so `mw list` and `mw config` show 15 extensions instead of 8.
  A document that happens to contain a standalone `[button ...]`, `[lightbox ...]`, `[grid]`, `[grid cards]`, `[grid N]`, `[grid cards N]`, `[card]`, `[tab NAME]`, `[/grid]`, `[/card]`, `[/tab]`, or `[annotate]` line, or a `mermaid` fence, now renders differently; use `disable` or `--exclude` to turn one off.
- `selected_extensions` with no `enable` list now returns fifteen names where 0.3.0 returned eight, so a host tool that passes its result to Python-Markdown loads the seven new extensions unless it sets `disable` or `enable`.
- A `[grid]` or `[annotate]` line with no list or block after it is removed from the output; it used to stay as text.
- An existing `warn = true` in a config file now makes `mw post` print its diagnostics, since `mw post` reads that key as the default for `--warn` (#33).
- A highlight pair no longer spans a line break: a `<^>` marker pairs with the next marker on the same line, in the in-process render and in `mw pre` alike, so a pair that crossed a line end stops highlighting and an opener with no closer on its line stays literal (#34).
- A directive line indented under a list item, or in the body of an admonition, details block, content tab, definition, or footnote, now expands at its own indentation, so the expansion stays inside the item or body (an embed under a list item no longer ends the list in-process).
  A directive at column 0 renders as before.
- `config_from_mapping` is stricter: a table that is not a mapping is a `ConfigError`, and an unknown key is an error whatever its value, `None` included.
- `fence.label_class` and `fence.secondary_label_class` must be space-separated class tokens of letters, digits, `-`, and `_`; an empty value or one with other characters is a config error.
- The `markdown` floor is `>=3.8.2`, up from `>=3.4`: 3.8.2 is the first Python-Markdown release that passes the suite, so an environment pinned below it has to upgrade.
- `icons` does nothing until you configure `packs`, so `:name:` text is untouched by default.
- If your `mkdocs.yml` has a `pymdownx.superfences` `custom_fences` entry named `mermaid` and you load `markwright.mermaid`, the entry goes inert because markwright replaces the fence first; remove it.

### Added

- `markwright.button`: `[button URL TEXT]` and `[button primary URL TEXT]` become `<a class="mw-button">` links.
- `markwright.lightbox`: `[lightbox URL ALT]` becomes an `<a class="mw-lightbox">` wrapping an `<img>`.
- `markwright.mermaid`: a `mermaid` fence becomes `<pre class="mermaid">` for a host script to draw.
- `markwright.icons`: `:pack-name:` shortcodes become inline SVG wrapped in `<span class="mw-icon">`, read from directories named by the new `packs` option.
  markwright ships no icons.
- `markwright.grid`: `[grid]` and `[grid cards]` add `mw-grid` and `mw-grid-cards` classes to the next list; a paired `[grid]` ... `[/grid]` wraps any Markdown blocks as grid cells, `[card]` ... `[/card]` wraps one card inside a block grid, and `[grid N]` sets a 1-to-6 column count as `mw-grid-cols-N`.
  Carried through versioned `mw-grid`, `mw-grid-block`, `mw-grid-end`, `mw-card`, and `mw-card-end` marker comments, with an `mw-grid-problem` marker for a container left literal (#30).
- `markwright.annotate`: `[annotate]` links `(N)` markers in a block to the items of the ordered list after it, through a versioned `mw-annotate` marker comment.
- `markwright.tabs`: consecutive `[tab NAME]` ... `[/tab]` blocks become one `tabbed` set with the `mw-tabs` class, `mw-tab-S-T` ids, and `mw-tab-S` radio names, through versioned `mw-tab` and `mw-tab-end` marker comments, with an `mw-tab-problem` marker for a tab left literal (#30).
- `disallowed_environments(source, config)`, a public function that lists the fence environments a document names outside `fence.allowed_environments` (#32).
- A shared marker module for the fence, grid, annotate, and tabs marker comments, and a container-pairing scanner shared by grid and tabs (#30).
- Docs pages for the six material extensions and `tabs`, each with the `mw-` HTML contract and a live demo, and a Host CSS and Script section on every extension page (#30).
- A Material Mapping docs page that maps each Material for MkDocs reference feature to its in-process and Hugo providers, with the gaps.
- Demo-site host assets that show how a host styles the output: CSS in `extra.css` (including grid columns, cards, and CSS-only tabs), scripts for mermaid, the lightbox, and annotation tooltips, and two small icon packs under `docs/icons/` with credits in `CREDITS.txt`.
  These are not part of the package.
- The docs `mw list` and `mw config` samples, `config.md`, and the MkDocs integration guide now cover the six extensions, `tabs`, and the `icons` `packs` option.

### Changed

- The docs site no longer carries a `custom_fences` mermaid entry; `markwright.mermaid` replaces it.

### Fixed

- `mw pre` expanded directive lines inside fenced code blocks, so the code showed an iframe or a marker comment instead of the directive.
  The six embeds, `button`, `lightbox`, `grid`, and `annotate` now leave a directive literal inside a fence, matching the in-process render (#20).
- `mw pre` now reads a tab as four columns when scanning fences, so a tab-indented fence inside a list item is code to every pre stage, matching the in-process render (#29).
  `mw pre` and the in-process render both leave a directive line inside a top-level indented code block literal.
  Before this, both expanded the embed, button, or lightbox out of the code block, and `grid` and `annotate` wrote their marker into it (#29).
- `mw pre` wrapped a `<^>` pair inside a top-level indented code block in `<mark>`.
  It now leaves the pair as written, as it does inside a fence, and `mw post` marks it.
- A fence with `line_numbers` after a `command`, `super_user`, or `custom_prefix` flag no longer carries the earlier flag's prefix value in its marker.
- Highlight no longer wraps markers inside `<title>` and `<textarea>`, where the browser shows the tag as text.
- `mw pre` passes a leading YAML (`---`) or TOML (`+++`) front matter block through untouched.
- `mw` reads and writes UTF-8 whatever the locale.
  For `mw pre`, `mw post`, and `mw render`, a decode error, a closed stream, a broken pipe, and an unreadable icon file are each one `mw: error:` line and exit 2 instead of a traceback.
  An unreadable or non-UTF-8 config file is the same for `mw config` and for those three.

## [0.3.0] - 2026-10-11

Two opt-in features (a config API for host tools and click-to-load embeds), one rule for every config list, a round of correctness fixes, and Python 3.15 support.
With default settings, output is unchanged for documents 0.2.0 already rendered correctly; the differences are the fixes listed below.

### Upgrading from 0.2.0

- `enable = []` now runs no extensions, and `fence.allowed_environments = []` now allows no environments; both used to mean "everything".
  Both now emit a `ConfigWarning`.
  Omit the key to get the old behavior.
- Config validation is stricter: an option key an extension does not take, a `load` value it does not support, or a non-list `fence.allowed_environments` is now a `ConfigError` (`mw` exits 2 with an `mw: error:` line) instead of being ignored.
- Python API renames, if you call the stage functions directly: the `warnings` parameter of `apply_html` and `registry.run_post` is now `skip_reasons`, and `highlight.apply_html`'s first parameter is now `rendered_html`.
- Removed APIs: `registry.select_extensions`, `registry.OPTION_CHECKS`, `registry.LOAD_MODES`, and the `*_SIGNATURE` constants (see Removed).
- New runtime dependency `pydantic>=2.14.1`, and the `pymdown-extensions` floor rises to 11.0.1.

### Added

- A public config API for host tools: `config_from_mapping(table, source)` validates an already-parsed markwright table with the same rules as `markwright.toml`, `selected_extensions(config)` applies `enable` and `disable`, and `extension_configs(config, names)` builds the `extension_configs` argument for `markdown.Markdown`.
  The package root re-exports these with `Config`, `ConfigError`, `ConfigWarning`, and `OptionError`.
  `mw render` uses the same functions.
- A `load` option on the `youtube`, `codepen`, `twitter`, and `instagram` embeds.
  `eager` is the default and unchanged.
  `click` emits a versioned click-to-load preview with the live markup inside a `<template>`, so nothing reaches the provider until a host script loads it.
  `lazy` (YouTube only) adds `loading="lazy"` to the iframe.
  Provider scripts are injected only when at least one embed of that kind on the page is eager.
- A Click-to-Load docs page with the markup contract, the provider processor calls (checked against the providers' live scripts), and a sample host script.
- `mw config` reports the resolved `load` for each embed and where it came from.
- `markwright.ConfigWarning`, emitted when a setting turns a feature into a no-op (an empty selection or an empty `allowed_environments`).
  It never raises unless you escalate it, for example with `warnings.simplefilter("error", ConfigWarning)`.
  `mw` prints it as one `mw: warning:` line on stderr.
- `markwright.OptionError`, a `ValueError` subclass raised for an invalid extension option value.
- Config Rules in the configuration docs: omitting a key means its default, a list names exactly what it holds, a no-op setting warns, and every option is validated.
- Python 3.15 support, tested in CI.

### Changed

- `enable = []` runs no extensions and `fence.allowed_environments = []` allows no environments, each with a `ConfigWarning`; both used to mean "everything" (#13).
- Config validation runs each extension's own option checks and rejects option keys an extension does not take; an unknown key used to pass through and crash `mw render` with a `KeyError` traceback.
- `mw` reports config problems as one `mw: error:` line with exit code 2, including a `ConfigWarning` escalated with `python -W error`, and prints only markwright's own warnings as `mw: warning:` lines.
- A config value of null (a YAML key with no value) counts as omitted.
- `apply_html` and `registry.run_post` take per-extension options, mirroring `expand_source` and `run_pre`, and name their skip-reason list `skip_reasons`.
- The post stages read rendered HTML with the stdlib `html.parser` instead of regex and edit only the spans they change.
- Fence directives and prose highlights find fenced code by CommonMark's rules, through one scanner shared by both pre stages.
- `registry.REGISTRY` holds pydantic `StageSpec` models, and the embed flag settings are pydantic models.

### Removed

- `registry.select_extensions`; selection lives in `config.selected_extensions`.
- `registry.OPTION_CHECKS` and `registry.LOAD_MODES`; each `StageSpec` carries its option checker, and `LOAD_MODES` stays on each embed module.
- The `CODEPEN_SIGNATURE`, `TWITTER_SIGNATURE`, and `INSTAGRAM_SIGNATURE` constants, replaced by `*_EMBED_CLASS` (the bare class name).

### Fixed

- Fence directives apply to fences indented up to three spaces and to fences inside list items; they used to render as literal code text.
- A fence marker whose JSON is valid but the wrong shape (`[1]`, `null`, a numeric `label`) is skipped with a warning instead of crashing the post stage with `AttributeError`.
- Each fence marker styles only its own code block, so a marker with no block can no longer style the next marker's.
- `fence.label_class` and `secondary_label_class` apply in `mw post`; the pipeline used to drop them while `mw render` honored them.
- The fence extension reads its options when it registers, so a `setConfig` call after construction applies.
- A highlight marker inside an HTML attribute (for example `title="&lt;^&gt;"`) is no longer wrapped in `<mark>`, which produced broken markup.
- A `<^>` marker inside a fence nested in a longer fence is no longer highlighted by `mw pre`, and inline code spans of two or more backticks are skipped like single-backtick ones.
- An unclosed fence is no longer treated as code by the pre stages, matching `pymdownx.superfences`.
- An empty extension selection (from `enable = []`, a `disable` listing every extension, or `--exclude`) warns with its cause instead of passing input through silently.

### Security

- Requires `pymdown-extensions>=11.0.1` (was `>=10.5`), the first release without PYSEC-2026-3654.

## [0.2.0] - 2026-09-23

### Added

- The config system: `markwright.toml` or `[tool.markwright]` discovery, `enable`/`disable`, per-extension options, `warn`, and the `mw config` command.

### Removed

- The `mw --use` flag; its allowlist lives in config as `enable`.

## [0.1.0] - 2026-09-15

### Added

- First release: the highlight, fence, YouTube, CodePen, Twitter, Instagram, slideshow, and image compare extensions, and the `mw` pipeline CLI.

[Unreleased]: https://github.com/MasonEgger/markwright/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/MasonEgger/markwright/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/MasonEgger/markwright/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/MasonEgger/markwright/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/MasonEgger/markwright/releases/tag/v0.1.0
