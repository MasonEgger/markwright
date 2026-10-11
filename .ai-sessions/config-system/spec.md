# markwright 0.2.0: Config System and CLI Simplification

## Overview

Add a tuneable configuration layer to markwright and simplify how the `mw` CLI selects extensions.

Two things motivate this.
First, the CLI cannot set per-extension options at all: `mw render` builds its `markdown.Markdown` with a hardcoded extension list and empty configs, so a `mw` user (a Hugo site, a plain pipeline) has no way to set `fence`'s `allowed_environments` or any other extension option.
That is a missing capability, not a defect, but it means several documented options are unreachable outside an in-process Python-Markdown call.
Second, extension selection used two flags (`--use` allowlist and `--exclude` denylist) whose distinction users had to hold in their head.

The fix is one system: a config file becomes the durable, primary tuning surface (selection plus per-extension options), and the CLI flags shrink to thin overrides.
The default stays all extensions on, decided in the 0.1 cycle and unchanged here.

## Scope

In scope:

- A config file: a standalone `markwright.toml`, and a `[tool.markwright]` table in `pyproject.toml`.
- Config-driven extension selection (`enable` / `disable`).
- Per-extension options read from config and applied to the render path (and the pre/post stage path, R6).
- CLI changes: drop `--use`, keep `--exclude`, add `--config PATH`, add a `mw config` command.
- A stated precedence order and clear errors on conflicts.
- Docs and a version bump to 0.2.0.

Out of scope:

- A user-level `~/.config/markwright/` layer (deferred; project-level only for now).
- New extensions or any change to extension output or parity.
- Changing the all-on default.

## Decisions

Settled with Mason before this spec (confirm if any flipped):

- D1: the standalone config file is `markwright.toml` (no leading dot).
- D2: drop the `--use` flag; the allowlist lives in config as `enable`; the CLI keeps `--exclude` for ad-hoc drops.
- D3: read config from both a standalone `markwright.toml` and a `[tool.markwright]` table in `pyproject.toml`; if both exist in the same directory, `markwright.toml` wins (matching ruff).
- D4: no user-level config layer this cycle.
- D5: R6 (per-extension options through the `mw pre` / `mw post` stage path) lands in 0.2.0. It is the invasive part, so the plan sequences it last, but it is in scope because it unlocks options like fence environments for Hugo users, the motivating case.

## Requirements

### R1: Config discovery and parsing

Discover config by walking up from the current directory to the filesystem root using `pathlib.Path` (`Path.cwd()` and its `.parents`), not `os.path` string manipulation.
In each directory, prefer a `markwright.toml`; otherwise use a `pyproject.toml` that contains a `[tool.markwright]` table.
The first directory with either wins; discovery stops there.
`--config PATH` bypasses discovery and loads exactly that file (a `pathlib.Path`; error if it is missing or has no markwright table).
Parse with `tomllib` from the standard library (available on the 3.11 floor, so no new dependency).

Acceptance: given a `markwright.toml` in a parent directory, a `mw` run from a subdirectory loads it; `--config` overrides discovery; a malformed TOML file is a clear boundary error, not a traceback.

### R2: Config schema and validation

The recognized top-level keys are `enable`, `disable`, and `warn`, plus one table per extension (`[fence]`, `[youtube]`, ... in `markwright.toml`, or `[tool.markwright.fence]` in `pyproject.toml`).
`enable` and `disable` are lists of extension names and are mutually exclusive: declaring both is an error.
`warn` is a boolean default for the post stage.
An unknown top-level key is an error (typo protection).
An unknown extension name in `enable`/`disable` or as a table is an error.
Per-extension option keys are passed to the extension; the extension validates them.

Acceptance: both-`enable`-and-`disable` errors clearly; an unknown key or extension name errors with the offending name; a valid file parses into a resolved config object.

### R3: Config-driven selection across all subcommands

Selection resolves from config, then CLI overrides:

- No config and no flags: all extensions (unchanged default).
- Config `enable = [...]`: only those.
- Config `disable = [...]`: all but those.
- CLI `--exclude NAME` (repeatable): removes names from the resolved set, applied last.

This applies uniformly to `mw pre`, `mw post`, and `mw render`.
Unknown names remain a usage error (exit 2).

Acceptance: config `disable` drops an extension for all three subcommands; `--exclude` removes from the config-resolved set; the all-on default holds with no config and no flags.

### R4: Per-extension options in `mw render`

`mw render` builds `extension_configs` for the selected `markwright.*` extensions from the per-extension tables in config, so options such as `fence.allowed_environments` take effect through the CLI.

Acceptance: a `markwright.toml` with `[fence] allowed_environments = ["staging"]` makes `mw render` accept a `[environment staging]` fence directive that it would otherwise reject.

### R5: The `mw config` command and CLI surface

- Drop `--use` from `pre`, `post`, and `render`.
- Add `--config PATH` to `pre`, `post`, and `render`.
- Add `mw config`: print the resolved configuration (effective extension set, each per-extension option, the `warn` default) and the source of each value (default, project config file path, or CLI flag).

Acceptance: `mw config` from a project with a `markwright.toml` prints the effective set and cites the file; `--use` is gone; `--config` selects an explicit file.

### R6: Per-extension options in the `mw pre` / `mw post` stage path (invasive; D5-gated)

Thread per-extension options through the pure stage functions and the registry so that `mw pre` and `mw post` honor config options too, not only `mw render`.
This is what lets a Hugo user (who runs `mw pre | hugo | mw post`) set fence environments and other options.
The plan isolates and sequences this last so it can ship in 0.2.0 or defer to 0.3.0 per D5.

Acceptance: with the same `[fence] allowed_environments` config, `mw pre` validates a `[environment staging]` directive the same way `mw render` does.

### R7: Docs and packaging

- New `docs/config.md`: the file names, discovery, precedence, schema, and examples.
- Update `docs/cli.md` (drop `--use`, add `--config` and `mw config`), the pipeline guide, and the README.
- Bump the version to `0.2.0`.
- Note the breaking change (removal of `--use`) in the release notes.

Acceptance: `just docs-build` strict-clean; `docs/config.md` in the nav; version reads `0.2.0`.

## Global Requirements

1. Test-first: each requirement lands with a failing test first, per the project TDD rule.
2. The gate `just check` (100 percent line and branch coverage, ruff, mypy strict) passes after every step.
3. No change to extension output or upstream parity.
4. Config parsing errors fail loud at the boundary with a clear message, never a traceback.
5. RST docstrings, `from __future__ import annotations`, absolute imports, the 2-line `# ABOUTME:` header, and the other project conventions in CLAUDE.md.
6. Public prose follows the repo writing rules (no em-dashes or en-dashes, straight quotes).

## Component Boundaries

- A new `config.py` owns discovery, parsing, validation, and the resolved `Config` object. It has no dependency on `cli.py`.
- `registry.select_extensions` stays; it is fed the resolved set. Selection logic is not duplicated.
- `cli.py` wires config into each subcommand and adds `mw config`.
- R4 (render options) and R6 (stage-path options) are separable; R6 is the isolated, deferrable unit.

## Verification

The cycle is done when every acceptance criterion above has a passing test, `just check` is green at 100 percent coverage, `docs/config.md` exists and the docs build is clean, and the version is `0.2.0`.
R6 either lands with its tests or is explicitly deferred to 0.3.0 with D5 recorded.
