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

1. A CLI flag (`--exclude`, and `--warn` or `--no-warn` on `mw post` and `mw render`).
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

The valid names are `fence`, `highlight`, `youtube`, `codepen`, `twitter`, `instagram`, `slideshow`, `image_compare`, `button`, `lightbox`, `mermaid`, `icons`, `grid`, `annotate`, and `tabs`.
An unknown name is an error.

### `warn`

A boolean default for the marker diagnostics of `mw post` and `mw render`.
It defaults to `false`.

### Per-Extension Options

Each extension may take an options table named for it.
Config validates every key and value with the same reader the extension uses, so an option the extension does not take, or a bad value, is an error before anything renders.
The fence extension reads `allowed_environments`, a list restricting which `[environment ...]` directives are honored.
Omitting it allows every environment; an empty list allows none and emits a warning.

It also reads `label_class` and `secondary_label_class`, the CSS classes on the label `<div>` and the secondary label `<div>`.
They default to `code-label` and `secondary-code-label`.
Each is one or more space-separated class tokens of letters, digits, `-`, and `_`; an empty value, a non-string, or any other character is a `ConfigError`.

```toml
[fence]
allowed_environments = ["local", "staging", "production"]
label_class = "code-label"
secondary_label_class = "secondary-code-label"
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

The `icons` extension reads `packs`, a table that maps a shortcode prefix to a directory of SVG files.
markwright ships no icons, so with `packs` omitted the extension does nothing and `:pack-name:` shortcodes pass through unchanged.

```toml
[icons.packs]
lucide = "docs/icons/lucide"
mw = "docs/icons/mw"
```

An empty `packs` table is a no-op and emits a `ConfigWarning`.
A `packs` value that is not a table, a path that is not a string, or a directory that does not exist is a `ConfigError`.
Relative directories resolve against the directory you run from.
See [Icons](extensions/icons.md).

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
   The Python-Markdown path raises `markwright.OptionError` (a `ValueError` subclass) for the same bad values.

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

A Hugo site runs `mw pre` on its content, then `hugo`, then `mw post` on the rendered pages.
Both stages discover the same `markwright.toml` at the project root, so a single file configures the whole pipeline.
With the fence `allowed_environments` set as above, `mw pre` honors an `[environment staging]` directive and rejects an unlisted one, exactly as the in-process `mw render` does.

```bash
mw pre < content/post.md > content/post.md.tmp && mv content/post.md.tmp content/post.md
hugo
mw post < public/post/index.html > public/post/index.html.tmp && mv public/post/index.html.tmp public/post/index.html
```

See the [Hugo guide](integrations/hugo.md) for the `hugo.toml` settings and a script that does this for every file.

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
  A table that is not a mapping is a `ConfigError`, `None` reads as an empty table, and an unknown key is an error whatever its value, `None` included.
- `selected_extensions(config)` applies `enable` and `disable` and returns extension names in registry order.
- `extension_configs(config, names)` returns the per-extension option tables keyed `markwright.<name>`, ready for `markdown.Markdown`.
- `disallowed_environments(source, config)` returns the fence environment names a document uses outside `fence.allowed_environments`, each once, in order of first appearance.
  A name is everything after the first space of the `[environment NAME]` line, compared as written.
  Every disallowed environment line among a fence's leading lines is reported, although `mw pre` stops reading directives at the first one, and a directive inside a nested fence's source is code.
  A `mermaid` fence is skipped when `mermaid` is selected and scanned when it is excluded.
  The list is empty when `allowed_environments` is omitted or `fence` is not selected, and an empty allowlist reports every name.
  It emits no warning of its own, so printing the result is the host's decision.

`mw render` builds its own `markdown.Markdown` from `selected_extensions` and `extension_configs`, so a host and the CLI resolve a given table the same way.

When a config selects no extensions, `selected_extensions` returns an empty list and emits a `markwright.ConfigWarning` with the cause and the `source` label.
It does not raise, since an empty selection is a legitimate way to switch markwright off.
A host that wants it fatal (in its own test suite, say) can escalate it:

```python
import warnings

from markwright import ConfigWarning

warnings.simplefilter("error", ConfigWarning)
```

## Diagnostics

A post stage that skips a marker or leaves a directive literal reports it as a `markwright.Diagnostic`, and never changes the rendered HTML or an exit code because of it.
A `Diagnostic` is a frozen record with five fields:

- `extension`: the extension that reported it, such as `tabs`.
- `line`: the 1-based source line of the directive, or `None` when the report has none.
- `directive`: the literal directive text, such as `[/tab]`, or `None` when the report has none.
- `reason`: a code from a closed vocabulary.
- `message`: the one-line text `mw post --warn` prints.

The `reason` vocabulary is:

- `unclosed`: an opener with no closer.
- `stray-closer`: a closer with no opener.
- `card-outside-grid`: a `[card]` that is not directly inside a block grid.
- `disallowed-environment`: a fence environment outside `fence.allowed_environments`.
- `malformed-marker`: a marker whose payload is malformed, not an object, an unsupported version, or has a wrongly typed field.
- `no-target`: a marker with no block, list, or code block after it to act on.
- `unmatched-marker`: an open or close marker with no partner.

`markwright.RenderWarning` is a `UserWarning` subclass that carries one `Diagnostic` in its `diagnostic` attribute, and its text is the diagnostic's message.

### In-Process Reports

A render through Python-Markdown reports the same problems.
Each post stage that reports (`fence`, `grid`, `tabs`, and `annotate`) appends every `Diagnostic` to `md.markwright_diagnostics` and emits one `RenderWarning` that carries it, so the list is the record and the warning is a side effect of the same call.
The list is empty at the start of each `md.convert()` and after `md.reset()`, and it exists (empty) as soon as one of those extensions is loaded.
The one exception is a blank document: Python-Markdown returns an empty string before any preprocessor runs, so the list keeps the previous document's entries.
A host that reuses one instance calls `md.reset()` between documents, or reads the list only after a non-blank `convert()`.
A document with no problem leaves the list empty and emits no warning, and a diagnostic never changes the rendered HTML.

```python
import markdown

md = markdown.Markdown(extensions=["markwright.tabs"])
md.convert("[tab One]\n\ntext")
for diagnostic in md.markwright_diagnostics:
    print(diagnostic.line, diagnostic.reason, diagnostic.message)
```

Python's default warning filter shows an identical message once per location.
A host that wants every report from a multi-page build reads the list, or sets the `always` filter for `RenderWarning`:

```python
import warnings

from markwright import RenderWarning

warnings.simplefilter("always", RenderWarning)
```

A host that runs with warnings as errors gets the exception it asked for.
`mw render` sets its own filter, so `PYTHONWARNINGS=error` never turns a diagnostic into a failure there.
