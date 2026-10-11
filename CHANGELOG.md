# Changelog

All notable changes to markwright are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

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

## [0.2.0]

### Added

- The config system: `markwright.toml` or `[tool.markwright]` discovery, `enable`/`disable`, per-extension options, `warn`, and the `mw config` command.

### Removed

- The `mw --use` flag; its allowlist lives in config as `enable`.

## [0.1.0]

### Added

- First release: the highlight, fence, YouTube, CodePen, Twitter, Instagram, slideshow, and image compare extensions, and the `mw` pipeline CLI.

[0.3.0]: https://github.com/MasonEgger/markwright/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/MasonEgger/markwright/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/MasonEgger/markwright/releases/tag/v0.1.0
