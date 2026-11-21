# Spec: Material Reference Parity (Issue #16)

Six additive extensions so a host theme (first consumer: Bartleby) can render every feature on the mkdocs-material reference from markwright markup alone.
markwright owns the authoring syntax and the HTML contract; the host owns CSS, JavaScript, and bundled assets.
The package keeps shipping no JavaScript and no CSS.

Decisions recorded here were taken with Mason on 2026-10-14 (issue #16 open questions).

## Decisions

- **D1: Directive lines, not attr_list forms.**
  Buttons, grids and cards, and lightbox use single-line directives in the `[youtube ...]` family.
  Material's `{ .md-button }`, `<div class="grid cards" markdown>`, and `{ lightbox }` depend on `attr_list` and `md_in_html`, which exist only in-process; Goldmark ignores them, so the `mw pre | hugo | mw post` pipeline would get nothing.
  A directive works in every renderer, the same as every existing extension.
- **D2: Annotations keep the list and link by id.**
  Each marker becomes a link to its list item, the way Python-Markdown's footnotes link `fnref` to `fn`.
  Without a host script the list reads as footnotes; a host positions a tooltip from the link and the item.
  Inlining each item at its marker (what mkdocs-material's script does) would put hidden block content inside `<pre><code>` and paragraphs and drop the list for feed readers.
- **D3: Icon packs are a prefix-to-directory mapping.**
  `[icons.packs] octicons = "path"` resolves `:octicons-rocket-16:` to `rocket-16.svg` under that directory (nested paths join with `-`, as mkdocs-material does).
  Each pack keeps its own namespace, so two packs with the same leaf name never collide.
- **D4: All six ship in one cycle.**
  One branch, one PR, one docs page per extension, one spec update; Bartleby's Goal 10 consumes a single release.
- **D5: Class hooks are `mw-` prefixed, flat kebab-case, matching the `mw-embed-*` hooks from 0.3.0.**
  The one exception is mermaid, where a well-known hook exists: mermaid.js's default selector is `.mermaid`, and Hugo's documented render hook emits `<pre class="mermaid">`.
  markwright emits that shape with the escaped source as direct text and no `<code>` wrapper, so stock `mermaid.initialize({ startOnLoad: true })` renders it.
  (mkdocs-material's `<pre class="mermaid"><code>` form needs Material's own renderer, because `mermaid.run()` reads `innerHTML`.)
- **D6: Mermaid is its own extension, not a fence feature.**
  It can be disabled on its own, and the fence extension's `do-markdownit` parity invariant stays untouched.
- **D7: Marker comments reuse the fence marker contract.**
  Grid and annotate travel from pre to post as `<!-- mw-grid:{JSON} -->` and `<!-- mw-annotate:{JSON} -->`, each carrying `"version": 1` and read fail-soft (malformed JSON, an unsupported version, or no following element is skipped and reported under `--warn`).

## Contracts

Every contract below is public and documented on its extension's docs page.
Adding a hook or attribute keeps the version; renaming or moving one bumps it.

### Button (`markwright.button`)

Syntax, a standalone line: `[button URL TEXT]` or `[button primary URL TEXT]`.

```html
<a class="mw-button" href="URL">TEXT</a>
<a class="mw-button mw-button-primary" href="URL">TEXT</a>
```

Inline raw HTML, so the renderer wraps it in `<p>`; consecutive button lines with no blank line between share a paragraph and sit side by side.
`TEXT` is HTML-escaped; the renderer still processes inline Markdown inside it, the same as text in any raw inline tag.

### Grid and cards (`markwright.grid`)

Syntax: `[grid]` or `[grid cards]` on its own line, directly before a list.
The pre stage replaces the line with a marker comment (`<!-- mw-grid:{"version": 1, "cards": true} -->`) and a blank line.
The post stage adds the classes to the first `<ul>` or `<ol>` after the marker and consumes the marker.

```html
<ul class="mw-grid">...</ul>
<ul class="mw-grid mw-cards">...</ul>
```

A marker with no following list is skipped and reported.

### Mermaid (`markwright.mermaid`)

Syntax: a fenced code block whose info string is `mermaid`.

```html
<pre class="mermaid">graph LR
    A --&gt; B
</pre>
```

The source is HTML-escaped (`&lt;`, `&gt;`, `&amp;`) and otherwise byte-identical, so `pre.textContent` is the diagram.
Fence directives (`[label ...]`) are not read inside a mermaid fence.

### Icons (`markwright.icons`)

Syntax, inline: `:PACK-NAME:` where `PACK` is a configured pack prefix and `NAME` is the SVG's path under the pack directory with `/` replaced by `-` and no `.svg`.

```html
<span aria-hidden="true" class="mw-icon"><svg ...>...</svg></span>
```

A name with no configured pack, or no matching file, stays literal text.
Icons are decorative; a text label next to an icon-only link is the author's job.
Option `packs` is a table of prefix to directory; a relative directory resolves against the current working directory.
Omitting `packs` renders no icons silently (the default); an explicit empty table emits a `ConfigWarning`; a missing directory or a non-string value is an `OptionError`.

### Lightbox (`markwright.lightbox`)

Syntax, a standalone line: `[lightbox URL ALT TEXT]` (alt text optional).

```html
<a class="mw-lightbox" href="URL"><img src="URL" alt="ALT TEXT" /></a>
```

Without a host script the link opens the image; a host opens a `<dialog>` from the link's `href` and the image's `alt`.

### Annotations (`markwright.annotate`)

Syntax: `[annotate]` on its own line, then the annotated block (a paragraph, a list, a fenced code block), then an ordered list of annotations.
Markers are `(1)`, `(2)` in the block's text; in code, `# (1)!` with a trailing `!` drops the surrounding comment token when the highlighter marked it as a comment.

The pre stage replaces the line with `<!-- mw-annotate:{"version": 1} -->` and a blank line.
The post stage, for the N-th annotate marker on the page:

- adds `mw-annotated` to the first element after the marker (the block);
- finds the first `<ol>` after that block, adds `class="mw-annotations"` and `data-mw-version="1"`, and gives its M-th direct `<li>` the id `mw-annotation-N-M`;
- replaces each `(M)` in the block's text (text tokens only, never attributes, `<script>`, or `<style>`) with `<a class="mw-annotation" href="#mw-annotation-N-M">M</a>` when item M exists; a `(M)` with no item M stays text.

```html
<p class="mw-annotated">Run <code>mw pre</code> first <a class="mw-annotation" href="#mw-annotation-1-1">1</a>.</p>
<ol class="mw-annotations" data-mw-version="1">
<li id="mw-annotation-1-1">It expands the directives.</li>
</ol>
```

A marker with no following element, or no `<ol>` after it, is skipped and reported.
The post stage runs before the fence and highlight post stages, so the fence's marker comment is still in place when the block is located.

## Stage Priorities

| Extension | Pre | Post | Why |
|-----------|-----|------|-----|
| icons | 50 | none | before mermaid, so a fence still shields its text from icon expansion |
| mermaid | 45 | none | before fence, so a mermaid fence never gets directive parsing |
| fence | 40 | 25 | unchanged |
| annotate | 20 | 30 | post runs before fence consumes its marker comment |
| grid | 20 | 30 | |
| button, lightbox | 20 | none | embeds' priority |
| highlight | 10 | 25 | unchanged |

In-process processors register at the same numbers.
