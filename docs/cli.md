# CLI Reference (`mw`)

The `mw` command exposes the markwright extensions as Unix filters, so their Markdown syntax works in toolchains that are not built on Python-Markdown.
It is a stdin-to-stdout tool: every transform subcommand reads standard input and writes standard output, so it composes in any pipe.
Input and output are UTF-8.

The console script ships with the package.
After `uv add markwright` (or `pip install markwright`), the `mw` command is on your path.

## Subcommands

```
mw pre    [--use NAME ...] [--exclude NAME ...]
mw post   [--use NAME ...] [--exclude NAME ...] [--warn]
mw render [--use NAME ...] [--exclude NAME ...]
mw list
mw --version
```

### `mw pre`

Reads Markdown source and writes Markdown with the source-stage transforms applied.
It expands the embed directives (`[youtube ...]`, `[codepen ...]`, and the rest) into raw HTML and extracts fence directives into an `<!-- mw-fence:{JSON} -->` comment that the post stage reads back later.
With the highlight extension active, it also wraps prose `\<^>...\<^>` runs in `<mark>`, leaving in-code markers for the post stage.

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

### `--use NAME`

Restrict the run to the named extension.
The flag is repeatable, so `--use youtube --use highlight` runs exactly those two.
The default, with no `--use`, is every extension.

### `--exclude NAME`

Drop the named extension from the selected set.
The flag is repeatable.
`--exclude` applies after `--use`, so you can start from all extensions and remove a few.

Selection order does not matter.
Stages always run in their defined priority order, matching the in-process behavior.
An unknown name passed to either flag is a usage error (see exit codes).

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
- `2` on a usage error: an unknown subcommand, or an unknown name passed to `--use` or `--exclude`.
  The offending name is reported to stderr.
- A nonzero code (`1`) if an I/O error propagates, since the tool fails loud rather than swallowing it.

## The Canonical Pipeline

Bracket any renderer with the two stages:

```bash
mw pre < in.md | some-renderer | mw post > out.html
```

The pre stage prepares the source, your renderer turns Markdown into HTML, and the post stage applies the HTML-level styling and script injection.
To select a subset of features, pass the same `--use` or `--exclude` flags to both stages:

```bash
mw pre --use youtube --use highlight < in.md | some-renderer | mw post --use highlight > out.html
```

For the full integration model, including when to run only the post stage, see the [Pipeline Guide](pipeline.md).
