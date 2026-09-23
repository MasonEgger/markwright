# Configuration

markwright reads a config file to decide which extensions run and how each one is tuned.
The file is the durable, primary tuning surface; the CLI flags are thin per-run overrides.
The default, with no config and no flags, is every extension on.

## File Names

markwright looks for two files, in this order within a directory:

1. A standalone `markwright.toml`.
2. A `pyproject.toml` with a `[tool.markwright]` table.

If both exist in the same directory, `markwright.toml` wins (matching how ruff resolves its own config).
In a standalone `markwright.toml`, the settings are top-level tables and keys.
In `pyproject.toml`, the same settings live under `[tool.markwright]` (so an extension table is `[tool.markwright.fence]`).

## Discovery

Without `--config`, markwright discovers the file by walking up from the current directory to the filesystem root.
The first directory that has a `markwright.toml`, or a `pyproject.toml` with a `[tool.markwright]` table, wins; the search stops there.
This is the same walk-up model ruff and other tools use, so a config at your project root applies to a run started from any subdirectory.

`--config PATH` bypasses discovery and loads exactly that file.
A missing path, or a `pyproject.toml` with no `[tool.markwright]` table, is an error.

## Precedence

Three layers resolve each run, highest priority first:

1. A CLI flag (`--exclude`).
2. The project config file (`markwright.toml`, else `[tool.markwright]`).
3. The built-in default (all extensions on, no per-extension options, `warn` off).

Run `mw config` to print the resolved result and the source of every value.

## Schema

The recognized top-level keys are `enable`, `disable`, `warn`, and one table per extension.

### `enable` and `disable`

Both are lists of extension names, and they are mutually exclusive: setting both is an error.

- `enable = ["fence", "youtube"]` runs only those two.
- `disable = ["codepen"]` runs every extension except that one.
- Neither key runs every extension (the default).

The valid names are `fence`, `highlight`, `youtube`, `codepen`, `twitter`, `instagram`, `slideshow`, and `image_compare`.
An unknown name is an error.

### `warn`

A boolean default for the `mw post` stage's marker diagnostics.
It defaults to `false`.

### Per-Extension Options

Each extension may take an options table named for it.
The option keys are passed to the extension, which validates them.
Today the fence extension reads `allowed_environments`, a list restricting which `[environment ...]` directives are honored (an empty list or an absent table allows every environment).

```toml
[fence]
allowed_environments = ["local", "staging", "production"]
```

An unknown top-level key, or a table named for an extension that does not exist, is an error.
This catches typos rather than ignoring them.

## Worked Examples

### A Standalone `markwright.toml`

```toml
# Run every extension except CodePen, and restrict fence environments.
disable = ["codepen"]

[fence]
allowed_environments = ["local", "staging", "production"]
```

### The Same Config in `pyproject.toml`

```toml
[tool.markwright]
disable = ["codepen"]

[tool.markwright.fence]
allowed_environments = ["local", "staging", "production"]
```

### A Hugo Pipeline

A Hugo site runs `mw pre | hugo | mw post` around its own renderer.
Both stages discover the same `markwright.toml` at the project root, so a single file configures the whole pipeline.
With the fence `allowed_environments` set as above, `mw pre` honors an `[environment staging]` directive and rejects an unlisted one, exactly as the in-process `mw render` does.

```bash
mw pre < content/post.md | hugo | mw post > public/post.html
```

Because the options come from the config file both stages read, you set them once and both the pre and post stages agree.
