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
- `enable = []` runs no extensions and emits a warning (see [Config Rules](#config-rules)).
- `disable = ["codepen"]` runs every extension except that one.
- Neither key runs every extension (the default).

The valid names are `fence`, `highlight`, `youtube`, `codepen`, `twitter`, `instagram`, `slideshow`, and `image_compare`.
An unknown name is an error.

### `warn`

A boolean default for the `mw post` stage's marker diagnostics.
It defaults to `false`.

### Per-Extension Options

Each extension may take an options table named for it.
Config validates every key and value with the same reader the extension uses, so an option the extension does not take, or a bad value, is an error before anything renders.
The fence extension reads `allowed_environments`, a list restricting which `[environment ...]` directives are honored.
Omitting it allows every environment; an empty list allows none and emits a warning.

```toml
[fence]
allowed_environments = ["local", "staging", "production"]
```

The embeds that contact a third party (`youtube`, `codepen`, `twitter`, `instagram`) read `load`, which decides when the embed reaches out.

| Value | Extensions | Output |
|-------|------------|--------|
| `eager` (default) | all four | The live embed, unchanged from earlier releases. |
| `lazy` | `youtube` only | The iframe gets `loading="lazy"`, so the browser fetches it when it scrolls near the viewport. |
| `click` | all four | An inert preview with a load button; nothing loads until a host script swaps in the live embed. |

```toml
[youtube]
load = "click"

[twitter]
load = "click"
```

Config validation checks `load`: an unsupported value, or `load` on an extension that does not take it, is an error.
See [Click-to-Load](click-to-load.md) for the preview markup and a host script.

An unknown top-level key, or a table named for an extension that does not exist, is an error.
This catches typos rather than ignoring them.

## Config Rules

These rules hold for every markwright setting, including any added later.

1. **Omitting a key means its default.**
   For a list, the default is no restriction.
   A key set to null (a YAML key with no value, from a host tool's config) counts as omitted.
2. **A list names exactly what it holds.**
   An empty allowlist (`enable`, `fence.allowed_environments`) allows nothing.
   An empty denylist (`disable`) removes nothing.
   No list treats empty as "everything".
3. **A setting that turns a feature into a no-op is legal and never silent.**
   It emits a `markwright.ConfigWarning` naming the key and, when markwright loaded the config, its source.
   `mw` prints it as one `mw: warning:` line on stderr and keeps stdout clean; a host sees a standard Python warning it can filter or escalate.
   Python's default filter shows a given warning message once per call site, so a site that builds one `Markdown` per page prints it once per build.
   Filtering Python warnings (`PYTHONWARNINGS=ignore`) silences it; escalating them (`python -W error`) turns it into an error, which `mw` reports as `mw: error:` with exit code 2.
   MkDocs routes Python warnings into its log, so there it appears as a log line, and `mkdocs build --strict` does not fail on it.
4. **Every option markwright defines is validated, and only those are accepted.**
   An unknown option key, a wrong type, or an unsupported value is a `ConfigError` naming the extension, the key, and the source, never a fallback or a traceback.
   The Python-Markdown path raises `ValueError` for the same bad values.

Rule 3 is why an empty selection does not error: switching markwright off is useful when testing a longer tool chain, but it should never happen by accident without a trace.

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

## Using markwright Config from Another Tool

A host tool (a static site generator, for example) can carry a markwright table inside its own config file and get the same validation `markwright.toml` gets.
The host parses its own file, then hands markwright the table:

```python
from pathlib import Path

import markdown
import yaml

from markwright import ConfigError, config_from_mapping, extension_configs, selected_extensions

host_config = yaml.safe_load(Path("bartleby.yml").read_text(encoding="utf-8"))

try:
    config = config_from_mapping(host_config.get("markwright", {}), source="bartleby.yml: markwright")
except ConfigError as config_error:
    raise SystemExit(str(config_error)) from config_error

names = selected_extensions(config)
md = markdown.Markdown(
    extensions=[f"markwright.{name}" for name in names],
    extension_configs=extension_configs(config, names),
)
```

- `config_from_mapping(table, source)` validates the table with the same rules as a config file and returns a `Config`.
  Every error message starts with the `source` label, and no file discovery happens.
- `selected_extensions(config)` applies `enable` and `disable` and returns extension names in registry order.
- `extension_configs(config, names)` returns the per-extension option tables keyed `markwright.<name>`, ready for `markdown.Markdown`.

`mw render` builds its own `markdown.Markdown` from these same three functions, so a host and the CLI resolve a given table the same way.

When a config selects no extensions, `selected_extensions` returns an empty list and emits a `markwright.ConfigWarning` with the cause and the `source` label.
It does not raise, since an empty selection is a legitimate way to switch markwright off.
A host that wants it fatal (in its own test suite, say) can escalate it:

```python
import warnings

from markwright import ConfigWarning

warnings.simplefilter("error", ConfigWarning)
```
