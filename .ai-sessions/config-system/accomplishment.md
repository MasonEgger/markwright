# Accomplishment: markwright 0.2.0 Config System and CLI Simplification

**Archived**: 2026-10-11
**Convergence**: converged (all 6 steps, 24 of 24 todo items, shipped as 0.2.0 in PR #10)

## Spec Slice

Add a tuneable configuration layer to markwright and simplify how the `mw` CLI selects extensions.
The CLI could not set per-extension options at all, and selection used two flags (`--use` allowlist and `--exclude` denylist).
The fix is one system: a config file (`markwright.toml` or a `[tool.markwright]` table) becomes the durable, primary tuning surface for selection and per-extension options, and the CLI flags shrink to thin overrides.
The all-on default is unchanged.
The full phase spec is preserved beside this file at `spec.md`, and the TDD roadmap at `plan.md` / `todo.md`.

## What Got Done

- R1 + R2: a new `config.py` with `pathlib` walk-up discovery, `tomllib` parsing, and fail-loud validation into a resolved `Config` with a per-value source map.
- R3 + R5a: config-driven selection (`enable`/`disable`) across `pre`, `post`, and `render`; added `--config PATH`; removed the `--use` flag (the breaking change).
- R4: per-extension options in `mw render`, assembling `extension_configs` for the selected extensions from config.
- R5b: the `mw config` command, printing the resolved configuration and the source of each value.
- R6: per-extension options threaded through the `mw pre` stage path via `run_pre`, so a Hugo user gets the same options as `mw render`.
- R7: `docs/config.md`, updates to `docs/cli.md`, `docs/pipeline.md`, and the README, and the 0.2.0 version bump.

## Deferred or Dropped

- R6 threaded options through `run_pre` only; `run_post` took no options at the time, since no post-stage extension consumed options. (0.3.0 later gave `run_post` the same options channel for fence label classes.)
- D4: a user-level `~/.config/markwright/` config layer was deferred; project-level config only.

## Notable Decisions

- D1: the standalone config file is `markwright.toml` (no leading dot).
- D2: drop `--use`; the allowlist lives in config as `enable`, and the CLI keeps `--exclude` for ad-hoc drops.
- D3: read both a standalone `markwright.toml` and a `[tool.markwright]` table; in one directory, `markwright.toml` wins (matching ruff).
- D4: no user-level config layer this cycle.
- D5: R6 (stage-path options) is in scope for 0.2.0, sequenced last as the invasive part.

## Files Touched

- src/markwright/config.py (new)
- src/markwright/cli.py
- src/markwright/registry.py
- src/markwright/fence.py (and the other extension modules, option-channel signatures)
- docs/config.md (new), docs/cli.md, docs/pipeline.md
- mkdocs.yml, README.md, pyproject.toml

## Lessons Cross-Reference

- "A breaking CLI change (removing the `--use` flag) is a minor bump under 0.x SemVer (0.1.0 -> 0.2.0), never a patch" (lessons.md, 2026-09-23)
- "To add a per-extension options channel to the pre stage, follow the existing `PostFn`/`warnings` convention: give every `expand_source` an `options` param it ignores (only `fence` reads `allowed_environments`), so `run_pre` threads `options.get(name)` uniformly" (lessons.md, 2026-09-23)
