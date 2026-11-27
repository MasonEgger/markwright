# Pipeline Guide

The `mw` CLI lets you use markwright syntax in a toolchain that is not built on Python-Markdown.
It brackets your existing renderer with two filters: a pre stage that runs on Markdown source, and a post stage that runs on the rendered HTML.
This page covers the model and shows worked Hugo and plain-Unix examples.

For the per-flag reference, see the [CLI Reference](cli.md).

## The Pre / Render / Post Model

Every markwright feature decomposes into at most two pure string transforms.
A source-stage transform takes Markdown text and returns Markdown with embedded HTML and marker comments.
An HTML-stage transform takes rendered HTML and returns rendered HTML.
Your renderer runs between them.

```mermaid
flowchart LR
    A[Markdown source] --> B[mw pre]
    B --> C[your renderer]
    C --> D[mw post]
    D --> E[final HTML]
```

The pre stage expands the embed, button, lightbox, mermaid, and icon directives into raw HTML, resolves prose highlights, and turns the fence, grid, card, annotate, and tab directives into marker comments (see [Renderer Requirements](renderer-requirements.md#marker-comments)).
Your renderer turns Markdown into HTML, passing the raw HTML and the comments through.
The post stage reads the marker comments back to apply fence labels and prefixes, grid, card, and tab markup, and annotation links, and it resolves the remaining highlight markers and injects one-time embed scripts.

The pre stage reads a document as a CommonMark renderer does and leaves four kinds of text alone: fenced code, indented code, a multi-line HTML comment, and a `<pre>`, `<script>`, `<style>`, or `<textarea>` block.
A directive, a fence directive, a highlight marker, or an icon shortcode inside one of them stays as you wrote it, so commented-out text stays commented out.
A comment starts at a line that begins with `<!--` and holds no `-->`, and it ends at the first later line that holds `-->`.
The opener may be indented up to three columns.
A comment that opens and closes on the same line is not skipped, which is how the marker comments the stages write keep working.

## When to Run Only Post

You do not always need both stages.

Run **both stages** when your source contains pre-stage syntax: embed, button, and lightbox directives like `[youtube ID]`, `mermaid` fences and icon shortcodes, or directives that leave a marker for the post stage, like `[label deploy.sh]`, `[grid]`, `[annotate]`, and `[tab NAME]`.
The pre stage has to expand those before your renderer sees them.

Run **only the post stage** when your HTML already carries the embed markup and any highlight markers, and you want the post-stage styling and script injection.
The post stage detects each embed's class signature on its own, so it injects scripts for hand-authored embeds with no pre-stage marker.
Highlight is also complete in the post stage: after a render, both prose and in-code markers surface as escaped text, and a single post pass handles both.

Run **only the pre stage** when you want prose highlights resolved to `<mark>` before your renderer runs, and nothing else.

The two stages are safe to combine.
Pre resolves prose highlights, post resolves whatever markers remain, and running post twice changes nothing.

## Plain Unix Example

The shortest path is a single pipe:

```bash
mw pre < in.md | cmark --unsafe | mw post > out.html
```

`cmark --unsafe` is [CommonMark](https://github.com/commonmark/cmark) with raw-HTML passthrough enabled, which the expanded embeds require.
To run a subset, pass matching flags to both stages:

```bash
mw pre --exclude twitter --exclude instagram < in.md \
  | cmark --unsafe \
  | mw post --exclude twitter --exclude instagram > out.html
```

If your source has no other directives and you only want highlight styling, restrict the run to that extension.
Set it once in a config file both stages discover:

```toml
# markwright.toml
enable = ["highlight"]
```

```bash
cmark --unsafe < in.md | mw post > out.html
```

See [Configuration](config.md) for the file format and precedence.

## Hugo

Hugo is a worked, tested instance of this model, with Goldmark as the renderer.
See the [Hugo integration guide](integrations/hugo.md) for the exact `hugo.toml` settings and a build script that brackets a real site.
