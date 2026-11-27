# CLI Reference (`mw`)

The `mw` command exposes the markwright extensions as Unix filters, so their Markdown syntax works in toolchains that are not built on Python-Markdown.
It is a stdin-to-stdout tool: every transform subcommand reads standard input and writes standard output, so it composes in any pipe.
Input and output are UTF-8.

The console script ships with the package.
After `uv add markwright` (or `pip install markwright`), the `mw` command is on your path.

## Subcommands

```
mw pre    [--config PATH] [--exclude NAME]
mw post   [--config PATH] [--exclude NAME] [--warn | --no-warn]
mw render [--config PATH] [--exclude NAME] [--warn | --no-warn]
mw config [--config PATH] [--exclude NAME]
mw list
mw --version
```

Which extensions run, and how each is configured, come from a config file.
See [Configuration](config.md) for the file format, discovery, and precedence.

### `mw pre`

Reads Markdown source and writes Markdown with the source-stage transforms applied.
It expands the embed, `[button ...]`, and `[lightbox ...]` directives into raw HTML, turns `mermaid` fences into `<pre class="mermaid">` blocks, and resolves `:pack-name:` icon shortcodes to inline SVG.
It extracts fence, `[grid]`, `[annotate]`, and `[tab NAME]` directives into marker comments (`<!-- mw-fence:{JSON} -->` and its siblings) that the post stage reads back later.
It pairs the containers (`[grid]` ... `[/grid]` with its `[card]` ... `[/card]` cards, and `[tab NAME]` ... `[/tab]`) into marker comments the same way, and leaves an unpaired opener or closer literal with a problem marker that `mw post --warn` reports.
With the highlight extension active, it also wraps prose `\<^>...\<^>` runs in `<mark>`, leaving in-code markers for the post stage.
A leading YAML (`---`) or TOML (`+++`) front matter block passes through untouched.
A first line of `---` counts as front matter when a later `---` line closes it, so start a document that opens with a thematic break with `***` or `___`.

The output is meant to feed your renderer.
Because the expanded embeds and the `<mark>` wrappers are raw HTML, your renderer must pass raw HTML through.
See [Renderer Requirements](renderer-requirements.md).

### `mw post`

Reads rendered HTML and writes HTML with the HTML-stage transforms applied.
It styles fence code blocks from their `mw-fence` markers (label divs, environment classes, `<ol><li data-prefix>` wrapping), classes grid lists, wraps block grids, cards, and tab sets from their markers, links annotations, wraps any remaining highlight markers in `<mark>`, and injects each embed script exactly once.

The post stage is the complete path on its own.
It needs no marker from the pre stage to inject scripts: it detects each embed's class signature in the rendered HTML, so it also works on hand-authored embeds.
Running post twice does not double-inject a script or double-wrap a mark.

### `mw render`

Runs the full Markdown-to-HTML pipeline in one shot using the in-process Python-Markdown path.
This is the standalone renderer for callers who do not have their own.
It builds a `markdown.Markdown` with `pymdownx.superfences` and `pymdownx.highlight` plus the selected `markwright.*` extensions, matching the bundled site stack.
It loads no other extension, so tables, admonitions, and the rest of Python-Markdown's and pymdownx's syntax are not available through it.
Its syntax highlighting needs Pygments, which markwright does not install; without it code blocks render unhighlighted.
`--warn` prints each problem the render found (an unclosed `[card]`, a stray `[/tab]`) as an `mw: warning:` line on stderr; see [`--warn` and `--no-warn`](#-warn-and-no-warn-post-and-render).

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
  button: on (default)
  lightbox: on (default)
  mermaid: on (default)
  icons: on (default)
  grid: on (default)
  annotate: on (default)
  tabs: on (default)
warn: false (default)
load:
  youtube: eager (default)
  codepen: eager (default)
  twitter: eager (default)
  instagram: eager (default)
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
button: pre
lightbox: pre
mermaid: pre
icons: pre
grid: pre, post
annotate: pre, post
tabs: pre, post
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

If the selection ends up empty (`enable = []`, a `disable` that lists every extension, or `--exclude` removing the rest), the run still succeeds: `pre` and `post` pass their input through unchanged, and `render` renders plain Markdown with every markwright directive left as literal text.
That is useful for switching markwright off inside a longer tool chain, but it is never silent: `mw` writes one `mw: warning:` line to stderr naming the cause and the config file, and stdout stays clean for the pipe.
An empty `fence.allowed_environments` warns the same way.
Warnings from other libraries keep Python's standard format, so `mw: warning:` always means markwright's own.
See [Config Rules](config.md#config-rules).

### `--warn` and `--no-warn` (`post` and `render`)

`--warn` turns the diagnostics on and `--no-warn` turns them off, whatever the [`warn` config key](config.md) says.
When both appear, the last one wins.
With neither, the config key decides, and it defaults to off.

The diagnostics are advisory lines on stderr for markers the post stage sees but cannot fully apply.
They change no output and do not change the exit code.
They are plain stderr lines, not Python warnings, so `PYTHONWARNINGS=error` does not escalate them.

`mw render` reports the same problems from its in-process render.
Each one prints as one `mw: warning: <message>` line, only when the diagnostics are on, and `PYTHONWARNINGS=error` does not escalate them there either.

They report the conditions a post-only filter can detect, for the `mw-fence`, `mw-grid`, `mw-annotate`, and `mw-tab` markers and the others the pre stage writes (see [Renderer Requirements](renderer-requirements.md#marker-comments)):

- A malformed JSON payload, which is skipped rather than executed.
- A marker whose `version` this tool does not support.
- A marker with nothing to apply to, such as a fence marker with no code block after it or an annotate marker with no block after it.
- An open marker with no matching close marker, or the reverse.
- A grid or tab directive the pre stage left literal because it had no partner or no grid around it (an unclosed `[card]`, a stray `[/tab]`, a `[card]` outside a grid).

Each report has a `reason` code from a closed vocabulary, which a host reads from a `markwright.Diagnostic` (see [Diagnostics](config.md#diagnostics)):

- `unclosed`: an opener with no closer.
- `stray-closer`: a closer with no opener.
- `card-outside-grid`: a `[card]` that is not directly inside a block grid.
- `disallowed-environment`: a fence environment outside `fence.allowed_environments`.
- `malformed-marker`: a payload that is malformed, not an object, an unsupported version, or has a wrongly typed field.
- `no-target`: a marker with no block, list, or code block to act on.
- `unmatched-marker`: an open or close marker with no partner.

`mw post` prints only the message of each report.

With the diagnostics off, each of these is a silent no-op.
A renderer that strips a marker comment outright is undetectable here, since the marker is simply gone; that case is covered by the [renderer requirements](renderer-requirements.md), not by runtime detection.

### `--version`

Prints the installed package version and exits.

## Exit Codes

- `0` on success, including a run with no extensions selected (which warns on stderr).
- `2` on a usage error: an unknown subcommand, an unknown name passed to `--exclude`, or a config problem (a missing, unreadable, non-UTF-8, or malformed file, an unknown extension or option, or a bad value).
  A config problem, or, for `mw pre`, `mw post`, and `mw render`, input that is not UTF-8, a closed stdout, a broken pipe, or an icon file that cannot be read, prints one `mw: error:` line on stderr; argparse reports its own usage errors.
  `mw list` and `mw config` write with plain `print`, so a broken pipe on them is not covered by that rule.
  A `ConfigWarning` escalated with `PYTHONWARNINGS=error mw ...` also exits `2` with an `mw: error:` line.

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
