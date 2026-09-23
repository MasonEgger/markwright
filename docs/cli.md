# CLI Reference (`mw`)

The `mw` command exposes the markwright extensions as Unix filters, so their Markdown syntax works in toolchains that are not built on Python-Markdown.
It is a stdin-to-stdout tool: every transform subcommand reads standard input and writes standard output, so it composes in any pipe.
Input and output are UTF-8.

The console script ships with the package.
After `uv add markwright` (or `pip install markwright`), the `mw` command is on your path.

## Subcommands

```
mw pre    [--config PATH] [--exclude NAME ...]
mw post   [--config PATH] [--exclude NAME ...] [--warn]
mw render [--config PATH] [--exclude NAME ...]
mw config [--config PATH] [--exclude NAME ...]
mw list
mw --version
```

Which extensions run, and how each is configured, come from a config file.
See [Configuration](config.md) for the file format, discovery, and precedence.

### `mw pre`

Reads Markdown source and writes Markdown with the source-stage transforms applied.
It expands the embed directives (`[youtube ...]`, `[codepen ...]`, and the rest) into raw HTML and extracts fence directives into an `<!-- mw-fence:{JSON} -->` comment that the post stage reads back later.
With the highlight extension active, it also wraps prose `<^>...<^>` runs in `<mark>`, leaving in-code markers for the post stage.

The output is meant to feed your renderer.
Because the expanded embeds and the `<mark>` wrappers are raw HTML, your renderer must pass raw HTML through.
See [Renderer Requirements](renderer-requirements.md).

### `mw post`

Reads rendered HTML and writes HTML with the HTML-stage transforms applied.
It styles fence code blocks from their `mw-fence` markers (label divs, environment classes, `<ol><li data-prefix>` wrapping), wraps any remaining highlight markers in `<mark>`, and injects each embed script exactly once.

The post stage is the complete path on its own.
It needs no marker from the pre stage to inject scripts: it detects each embed's class signature in the rendered HTML, so it also works on hand-authored embeds.
Running post twice does not double-inject a script or double-wrap a mark.

### `mw render`

Runs the full Markdown-to-HTML pipeline in one shot using the in-process Python-Markdown path.
This is the standalone renderer for callers who do not have their own.
It builds a `markdown.Markdown` with `pymdownx.superfences` and `pymdownx.highlight` plus the selected `markwright.*` extensions, matching the bundled site stack.

### `mw config`

Prints the resolved configuration: each extension's on/off state, the per-extension options, and the `warn` default, with the source of every value (the built-in default, the config file path, or a CLI flag).
It reads the same config discovery and flags a real run would, so it shows exactly what `mw pre`, `mw post`, and `mw render` will use.

```
$ mw config
extensions:
  youtube: on (default)
  slideshow: on (default)
  image_compare: on (default)
  codepen: on (default)
  twitter: on (default)
  instagram: on (default)
  fence: on (default)
  highlight: on (default)
warn: false (default)
options: none
```

### `mw list`

Prints every registered extension and the stages it provides.

```
$ mw list
youtube: pre
slideshow: pre
image_compare: pre
codepen: pre, post
twitter: pre, post
instagram: pre, post
fence: pre, post
highlight: pre, post
```

An extension labeled `pre` has only a source-stage transform.
An extension labeled `pre, post` participates in both stages.

## Flags

### `--config PATH`

Load configuration from `PATH`, bypassing the walk-up discovery.
The file may be a standalone `markwright.toml` or a `pyproject.toml` with a `[tool.markwright]` table.
A missing path, or a `pyproject.toml` with no `[tool.markwright]` table, is a usage error.
Without `--config`, discovery walks up from the current directory.
See [Configuration](config.md).

### `--exclude NAME`

Drop the named extension from the selected set.
The flag is repeatable.
`--exclude` applies last, after the config-resolved selection, so you can start from what the config selects and remove a few for one run.

Selection order does not matter.
Stages always run in their defined priority order, matching the in-process behavior.
An unknown name passed to `--exclude` (or named in config) is a usage error (see exit codes).

The allowlist that older versions set with `--use` now lives in config as `enable`.
`--use` was removed in 0.2.0.

### `--warn` (`post` only)

Writes advisory diagnostics to stderr for markers the post stage sees but cannot fully apply.
It changes no output and does not change the exit code.

It reports the three conditions a post-only filter can detect:

- A malformed `mw-fence` JSON payload, which is skipped rather than executed.
- A marker whose `version` this tool does not support.
- A marker with no adjacent code block to style.

Without `--warn`, each of these is a silent no-op.
A renderer that strips the `mw-fence` comment outright is undetectable here, since the marker is simply gone; that case is covered by the [renderer requirements](renderer-requirements.md), not by runtime detection.

### `--version`

Prints the installed package version and exits.

## Exit Codes

- `0` on success.
- `2` on a usage error: an unknown subcommand, an unknown name passed to `--exclude` or named in config, or a config file that is missing or malformed.
  The offending name or the config error is reported to stderr.
- A nonzero code (`1`) if an I/O error propagates, since the tool fails loud rather than swallowing it.

## The Canonical Pipeline

Bracket any renderer with the two stages:

```bash
mw pre < in.md | some-renderer | mw post > out.html
```

The pre stage prepares the source, your renderer turns Markdown into HTML, and the post stage applies the HTML-level styling and script injection.
To select a subset of features, set `enable` (or `disable`) in a config file both stages discover, or pass the same `--exclude` flags to both:

```bash
mw pre --exclude codepen < in.md | some-renderer | mw post --exclude codepen > out.html
```

For the full integration model, including when to run only the post stage, see the [Pipeline Guide](pipeline.md).
