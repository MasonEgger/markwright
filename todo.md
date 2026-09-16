# TODO: markwright 0.2.0 Config System and CLI Simplification

Mirrors `plan.md`. `/bpe:execute-plan` checks off sub-steps as it goes.
Steps 1-6 turn `spec.md` (R1-R7, D1-D5) into TDD work. R6 (Step 5) is in scope for 0.2.0 per D5.

## Step 1: R1 + R2: The config Module (discovery, parse, validate, resolved Config)
- [ ] 1. RED: `tests/test_config.py`: parent-dir discovery (tmp_path), `markwright.toml` wins over `pyproject.toml` in one dir, explicit `--config` load, missing `--config` path errors, malformed TOML errors clearly, `enable`+`disable` together errors, unknown top-level key errors, unknown extension name errors, a valid file resolves to the expected `Config` (selection/options/warn/sources); confirm they fail (module absent)
- [ ] 2. GREEN: implement `src/markwright/config.py`: frozen `Config` dataclass, `load_config(explicit_path: Path | None, start_dir: Path) -> Config`, `pathlib` walk-up discovery, `tomllib` parse, validation raising a clear `ConfigError`; validate names against `EXTENSION_NAMES` only
- [ ] 3. REFACTOR: separate small functions for discovery, parse, validate; one `ConfigError`; no `Any`
- [ ] 4. `just check` with every validation path, both discovery outcomes, and the source map covered

## Step 2: R3 + R5a: Config-Driven Selection, `--config`, Drop `--use`
- [ ] 1. RED: `tests/test_cli.py`: config `disable` drops an extension for pre/post/render, config `enable` restricts, `--exclude` removes from the config-resolved set, `--config` loads an explicit file, `--use` is gone (argparse exit 2), no-config-no-flags still selects all; update the existing `--use` tests as the red step; confirm failures
- [ ] 2. GREEN: load config in `main()`/handlers via `config.load_config`, feed `select_extensions`, apply `--exclude`; drop `--use` from the shared flag helper; add `--config`; thread the resolved config to the handlers
- [ ] 3. REFACTOR: one selection-resolution helper shared by the three subcommands; keep IO helpers intact
- [ ] 4. `just check`

## Step 3: R4: Per-Extension Options in `mw render`
- [ ] 1. RED: `TestCliRenderOptions`: with `[fence] allowed_environments = ["staging"]` in config, `mw render` accepts a `[environment staging]` directive (styled) where without config it is rejected/untinted; confirm it fails
- [ ] 2. GREEN: build `extension_configs` for selected `markwright.*` extensions from `config.options`, merged with the existing `pymdownx.highlight` entry; pass to `markdown.Markdown`
- [ ] 3. REFACTOR: keep the `extension_configs` assembly in one small function
- [ ] 4. `just check`

## Step 4: R5b: The `mw config` Command
- [ ] 1. RED: `TestCliConfig`: `mw config` from a dir with `markwright.toml` prints the effective set and cites the file as source; no config shows all-on from defaults; `--config` honored; `--exclude` reflected and marked as a flag source; confirm it fails (subcommand absent)
- [ ] 2. GREEN: add the `config` subparser and handler; format the resolved `Config` and source map to stdout deterministically
- [ ] 3. REFACTOR: reuse the Step 2 selection-resolution helper so `mw config` and the transform subcommands agree
- [ ] 4. `just check`

## Step 5: R6: Per-Extension Options Through the Stage Path (invasive; D5, in scope)
- [ ] 1. RED: `TestStageOptions`: with `[fence] allowed_environments = ["staging"]`, `run_pre(text, ["fence"], options=cfg)` validates a `[environment staging]` directive like `mw render`; the `mw pre` CLI path honors config options; extensions without options are unaffected (regression); confirm failures
- [ ] 2. GREEN: extend the stage-function signatures that need options (start with fence) and `run_pre`/`run_post` to pass each extension its option dict from config; wire the pre/post handlers to load and pass config; keep `options` defaulting to None = current behavior so untouched extensions and existing tests pass
- [ ] 3. REFACTOR: one options-threading path in the registry; no per-extension special-casing in `run_pre`/`run_post`
- [ ] 4. `just check` with both the with-options and without-options branches covered

## Step 6: R7: Docs and Version Bump
- [ ] 1. Write `docs/config.md` (file names, pathlib discovery, precedence, schema, worked examples including Hugo); add it to `mkdocs.yml` nav
- [ ] 2. Update `docs/cli.md` (drop `--use`, add `--config` and `mw config`), `docs/pipeline.md`, and `README.md`
- [ ] 3. Bump the version to `0.2.0` in `pyproject.toml`; note the breaking change (removal of `--use`) for the release notes
- [ ] 4. `just check` and `just docs-build` (strict) both clean
