# Changelog

All notable changes to markwright are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [0.3.0]

Default output is byte-identical to 0.2.0 for well-formed input, and both feature additions are opt-in.
Two changes break 0.2.0 behavior, both from one rule: an empty list now means "none" everywhere (see Changed).
`pydantic` is a new runtime dependency, and the `pymdown-extensions` floor rises to 11.0.1 for a security fix.

### Added

- A public config API for host tools: `config_from_mapping(table, source)` validates an already-parsed markwright table with the same rules as `markwright.toml`, `selected_extensions(config)` applies `enable` and `disable`, and `extension_configs(config, names)` builds the `extension_configs` argument for `markdown.Markdown`.
  The package root re-exports these with `Config` and `ConfigError`.
  `mw render` uses the same functions.
- A `load` option on the `youtube`, `codepen`, `twitter`, and `instagram` embeds.
  `eager` is the default and unchanged.
  `click` emits a versioned click-to-load preview with the live markup inside a `<template>`, so nothing reaches the provider until a host script loads it.
  `lazy` (YouTube only) adds `loading="lazy"` to the iframe.
- Script injection for the CodePen, Twitter, and Instagram embeds now skips the provider script when every embed of that kind on the page is a click-to-load preview.
- `mw config` reports the resolved `load` for each embed and where it came from.
- Config validation rejects an unsupported `load` value, and `load` on an extension that does not take it.
- A Click-to-Load docs page with the markup contract, the provider processor calls, and a sample host script.
- `markwright.ConfigWarning`, emitted when a setting turns a feature into a no-op. `mw` prints it as one `mw: warning:` line on stderr.
- `markwright.OptionError`, a `ValueError` subclass raised for an invalid extension option value.
- Fence directives now apply to fences indented up to three spaces and to fences inside list items, following CommonMark; they used to render as literal code text.
- Config Rules in the configuration docs: omitted means default, a list names exactly what it holds, a no-op setting warns, every option is validated.

### Changed

- Breaking: `fence.allowed_environments = []` now allows no environments and warns; omit the key to allow every environment. It used to allow all.
- Config validation rejects a non-list `fence.allowed_environments`, and the extension raises `ValueError` for one; both used to ignore it silently.
- Config validation rejects an option key an extension does not take (it used to pass through and crash `mw render` with a `KeyError` traceback), and runs each extension's own value checks.
- `mw` reports config problems as one `mw: error:` line with exit code 2, including a `ConfigWarning` escalated with `python -W error`.
- `apply_html` and `registry.run_post` take per-extension options, mirroring `expand_source` and `run_pre`.
- Removed `registry.select_extensions`; selection lives in `config.selected_extensions`.
- Requires `pymdown-extensions>=11.0.1` (was `>=10.5`), the first release without PYSEC-2026-3654, and adds `pydantic` as a dependency.
- The post stages read rendered HTML with the stdlib `html.parser` instead of regex, editing only the spans they change.
- The `warnings` parameter of `apply_html` and `registry.run_post` is now `skip_reasons`, and `highlight.apply_html`'s first parameter is `rendered_html` like its siblings.
- The script embeds' `*_SIGNATURE` constants are now `*_EMBED_CLASS` (the bare class name), and `registry.REGISTRY` holds pydantic `StageSpec` models; `OPTION_CHECKS` and `LOAD_MODES` are gone from the registry.
- An unclosed fence is no longer treated as code by the pre stages, matching `pymdownx.superfences`.

### Fixed

- Breaking: `enable = []` now runs no extensions and warns; it used to run all of them (#13).
- An empty extension selection (from `enable = []`, a `disable` listing every extension, or `--exclude`) warns with its cause instead of passing input through silently.
- `fence.label_class` and `secondary_label_class` now apply in `mw post`; the pipeline used to drop them while `mw render` honored them.
- The fence extension reads its options when it registers, so a `setConfig` call after construction applies.
- A config value of null counts as omitted.
- `mw` prints only markwright's own warnings as `mw: warning:` lines; other libraries' warnings keep Python's format.
- A fence marker whose JSON is valid but the wrong shape (`[1]`, `null`, a numeric `label`) is skipped with a warning instead of crashing the post stage with `AttributeError`.
- A highlight marker inside an HTML attribute (for example `title="&lt;^&gt;"`) is no longer wrapped in `<mark>`, which produced broken markup.
- A `<^>` marker inside a fence nested in a longer fence is no longer highlighted by `mw pre`, and inline code spans of two or more backticks are skipped like single-backtick ones.
- Each fence marker styles only its own code block, so a marker with no block can no longer style the next marker's.

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
