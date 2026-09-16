# Plan: markwright 0.2.0 Config System and CLI Simplification

This plan turns `spec.md` (R1 through R7, Decisions D1 through D5) into TDD-sized steps.
Every step is test-first, keeps `just check` green (100 percent line and branch coverage), and changes no extension output or upstream parity.

## Current Status

- [ ] Step 1: R1 + R2: the `config` module: discovery, parse, validate, resolved `Config` object
- [ ] Step 2: R3 + R5a: config-driven selection across `pre`/`post`/`render`; add `--config`; drop `--use`
- [ ] Step 3: R4: per-extension options in `mw render`
- [ ] Step 4: R5b: the `mw config` command
- [ ] Step 5: R6: per-extension options through the `mw pre` / `mw post` stage path (invasive; D5, in scope)
- [ ] Step 6: R7: docs (`config.md` and updates) and the 0.2.0 version bump

Status: not started.

## Ordering and Dependencies

- Step 1 is the foundation; everything reads the resolved `Config`.
- Step 2 makes selection config-aware and lands the breaking CLI change (drop `--use`) early so the rest builds on the final flag surface.
- Steps 3 and 5 are the two option-wiring paths: Step 3 does the render path (self-contained), Step 5 does the stage path (invasive, sequenced last so it can be reviewed in isolation).
- Step 4 (`mw config`) depends on Step 1's resolved config carrying its value sources.
- Step 6 is docs plus the version bump, last.

## Architecture Notes

- **New `config.py` owns everything config.** Discovery (pathlib walk-up), TOML parse (`tomllib`), validation, and a resolved `Config` object (frozen dataclass) that records both values and where each came from (default / file path / flag) for `mw config`. It does not import `cli.py`.
- **Selection stays in `registry.select_extensions`.** Config resolves to a name set that feeds it; do not duplicate selection logic in `config.py` or `cli.py`.
- **Two option paths, one config.** `mw render` maps per-extension config to `markdown.Markdown` `extension_configs` (Step 3). The pure stage functions (`expand_source`, `apply_html`) and `run_pre`/`run_post` gain an options channel (Step 5). The config object is the single source both read.
- **Precedence:** CLI flag > project config (`markwright.toml`, else `[tool.markwright]`) > built-in default. Resolved once, early, per invocation.
- **`tomllib` is stdlib on the 3.11 floor**, so no dependency is added.

## Steps

### Step 1: R1 + R2: The `config` Module

**NOTE**: Create `src/markwright/config.py` (2-line `# ABOUTME:` header, `from __future__ import annotations`, RST docstrings). Discovery walks up with `pathlib`: from `Path.cwd()`, for each of `[cwd, *cwd.parents]`, prefer `dir / "markwright.toml"`, else a `dir / "pyproject.toml"` whose parsed content has a `[tool.markwright]` table; first hit wins, stop there. `--config PATH` bypasses discovery. Parse with `tomllib` (binary read mode). Recognized top-level keys: `enable`, `disable`, `warn`, and per-extension tables keyed by `EXTENSION_NAMES`. `enable`/`disable` mutually exclusive. Unknown top-level key or unknown extension name is an error. The resolved object is a frozen dataclass carrying the selection intent, the per-extension option dicts, `warn`, and a source map for `mw config`.

```text
1. RED: tests/test_config.py. New cases: discovery finds markwright.toml in a parent dir (use tmp_path); markwright.toml wins over pyproject.toml in the same dir; --config path loads explicitly; a missing --config path errors; malformed TOML errors with a clear message (not a traceback); enable+disable together errors; unknown top-level key errors; unknown extension name errors; a valid file resolves to the expected Config (selection, options, warn, sources). Assert error TYPES/messages at the boundary. Confirm they fail (module absent).
2. GREEN: implement config.py: a Config frozen dataclass, load_config(explicit_path: Path | None, start_dir: Path) -> Config, discovery via pathlib, tomllib parse, validation raising a ConfigError (a clear boundary exception) with actionable messages. No dependency on cli/registry beyond EXTENSION_NAMES for name validation.
3. REFACTOR: keep parsing, validation, and discovery as separate small functions; one ConfigError type; no Any.
4. just check (new branches: each validation path, both discovery outcomes, the source map) fully covered.
```

### Step 2: R3 + R5a: Config-Driven Selection, `--config`, Drop `--use`

**NOTE**: Wire the resolved config into `pre`/`post`/`render`. Selection resolves as: config `enable` (allowlist) or `disable` (denylist) produce the base set via `select_extensions`; CLI `--exclude` removes on top. Add `--config PATH` to all three subcommands. Remove `--use` and its parser wiring; update the shared selection helper. `--exclude` stays. Unknown names remain exit 2.

```text
1. RED: tests/test_cli.py additions (new classes; do not break existing except those pinning --use, which are updated as the red step). Cases: config disable drops an extension for pre/post/render; config enable restricts; --exclude removes from the config-resolved set; --config points at an explicit file; --use is gone (argparse rejects it, exit 2); no config and no flags still selects all. Confirm they fail.
2. GREEN: load config in main() (or per handler) via config.load_config, feed select_extensions, apply --exclude. Drop --use from the shared flag helper; add --config. Thread the resolved config down to the render/pre/post handlers.
3. REFACTOR: one selection-resolution helper shared by the three subcommands; keep IO helpers intact.
4. just check.
```

### Step 3: R4: Per-Extension Options in `mw render`

**NOTE**: `render` currently builds `markdown.Markdown` with only the `pymdownx.highlight` config. Build `extension_configs` for the selected `markwright.*` extensions from the resolved config's per-extension option dicts, merged with the existing pymdownx entry.

```text
1. RED: TestCliRenderOptions in tests/test_cli.py. With a config carrying [fence] allowed_environments = ["staging"], mw render accepts a `[environment staging]` fence directive (styled), where without the config it is rejected/untinted. Confirm it fails against current render.
2. GREEN: in the render handler, construct extension_configs from config.options for each selected markwright extension, keeping pymdownx.highlight's pygments_lang_class. Pass through to markdown.Markdown.
3. REFACTOR: keep the extension_configs assembly in one small function.
4. just check.
```

### Step 4: R5b: The `mw config` Command

**NOTE**: Add a `config` subcommand that prints the resolved configuration: the effective extension set (on/off), each per-extension option, the `warn` default, and the source of each value (default, the config file path, or a flag). It reads the same `config.load_config` plus the CLI flags, so it reflects exactly what a real run would use. Honors `--config`.

```text
1. RED: TestCliConfig. mw config from a dir with a markwright.toml prints the effective set and cites the file path as the source; with no config it shows all-on from defaults; --config is honored; --exclude is reflected in the effective set and marked as a flag source. Confirm it fails (subcommand absent).
2. GREEN: add the config subparser and handler; format the resolved Config and its source map to stdout deterministically.
3. REFACTOR: reuse the selection-resolution helper from Step 2 so mw config and the transform subcommands agree.
4. just check.
```

### Step 5: R6: Per-Extension Options Through the Stage Path (Invasive; D5)

**NOTE**: `mw pre` and `mw post` run the pure stage functions via `run_pre`/`run_post`, which today take no options. Thread per-extension options through so a Hugo user gets the same options as `mw render`. Give the stage functions that need options an optional parameter (e.g., `expand_source(text, options=None)` where fence uses `allowed_environments`), and have `run_pre`/`run_post` pass each extension its option dict from the resolved config. Extensions that ignore options keep working. Keep the in-process adapters (Preprocessor/Postprocessor) reading their options as they do now; the pure functions gain the options channel. This is the one step that touches multiple extension modules, so isolate it and drive all consumers from one parametrized test.

```text
1. RED: tests/test_roundtrip.py + per-extension. TestStageOptions: with [fence] allowed_environments = ["staging"], run_pre(text, ["fence"], options=cfg) validates a `[environment staging]` directive the same as mw render; the mw pre CLI path (via subprocess or handler) honors config options; extensions without options are unaffected (regression). Confirm failures.
2. GREEN: extend the stage-function signatures that need options (start with fence) and run_pre/run_post to pass per-extension options from config; wire the pre/post handlers to load config and pass it. Keep signatures backward-friendly (options default None = current behavior) so untouched extensions and existing tests pass.
3. REFACTOR: one options-threading path in the registry; do not special-case per extension in run_pre/run_post.
4. just check (the new options branches covered for both the with-options and without-options paths).
```

### Step 6: R7: Docs and Version Bump

**NOTE**: Document the config system and update the CLI docs for the new surface. Public prose follows the repo writing rules (no em/en dashes, straight quotes). Bump the version.

```text
1. Write docs/config.md: file names (markwright.toml, [tool.markwright]), pathlib walk-up discovery, precedence, the schema (enable/disable/warn + per-extension tables), and worked examples including a Hugo one. Add it to mkdocs.yml nav.
2. Update docs/cli.md (drop --use; add --config and mw config), docs/pipeline.md (config in the pipeline), and README.md (mention config + the mw config command).
3. Bump version to 0.2.0 in pyproject.toml. Note the breaking change (removal of --use) for the release notes.
4. just check and just docs-build (strict) both clean.
```

## Implementation Guidelines

- Load the `python` skill before writing any code each step. RST docstrings, `from __future__ import annotations`, absolute imports, no `Any`, 2-line `# ABOUTME:` headers, descriptive names.
- Discovery uses `pathlib.Path`, never `os.path` string joins.
- Parse config errors fail loud at the boundary with a clear message; never let a traceback reach the user.
- Do not duplicate selection logic; `registry.select_extensions` stays the one resolver.
- Do not change extension output or upstream parity.
- Coverage stays 100 percent line and branch; new validation and options branches carry their own cases.
- Test only markwright logic, not tomllib, argparse, or Python-Markdown.
