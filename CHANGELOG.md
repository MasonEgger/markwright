# Changelog

All notable changes to markwright are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [0.3.0]

Default output is byte-identical to 0.2.0.
Both additions are opt-in.

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
