# Annotate

Links `(N)` markers inside a block, usually a code block, to the items of the numbered list that follows it.

[annotate]

```python
name = "markwright"  # (1)
debug = False  # (2)!
```

1. The package name.
2. Switches off debug output.

````
[label Markdown]
[annotate]

```python
name = "markwright"  # (1)
debug = False  # (2)!
```

1. The package name.
2. Switches off debug output.
````

## Usage

```python
import markdown

md = markdown.Markdown(
    extensions=[
        "pymdownx.superfences",
        "pymdownx.highlight",
        "markwright.annotate",
    ]
)
```

See [Using with MkDocs](../integrations/mkdocs.md) to load it in a MkDocs site.

## Syntax

Put `[annotate]` on its own line before a block, write `(N)` in the block, and follow the block with an ordered list:

````
[annotate]

```python
name = "markwright"  # (1)
debug = False  # (2)!
```

1. The package name.
2. Switches off debug output.
````

| Marker | Result |
|--------|--------|
| `(N)` | Replaced by a link to list item N. |
| `(N)!` | In a code comment, the whole comment is replaced by the link, so the comment text does not show. |

A number outside `1` to the item count is left as written.
Only text counts: a `(N)` inside an attribute, a `<script>`, or a `<style>` is never touched.

## How It Works

Annotate is a two-stage extension.
The source stage (`mw pre`) replaces `[annotate]` with an `<!-- mw-annotate:... -->` marker comment.
The HTML stage (`mw post`) finds the block after the marker and the `<ol>` after the block.
It then:

1. Adds `mw-annotated` to the block.
2. Adds `mw-annotations` and `data-mw-version="1"` to the list.
3. Gives each top-level list item an id of the form `mw-annotation-B-N`, where B counts annotated blocks on the page and N is the item number.
4. Replaces each marker with `<a class="mw-annotation" href="#mw-annotation-B-N">N</a>`.

A marker with an invalid payload, no following block, or no ordered list after the block is skipped, and `--warn` reports why.
In-process, annotate's postprocessor (priority 30) runs ahead of fence's (25), so it still sees the fence marker as a comment.

## HTML Contract

```html
<div class="mw-annotated language-python highlight"><pre><span></span><code><span class="n">x</span> <span class="o">=</span> <span class="mi">1</span>  <span class="c1"># <a class="mw-annotation" href="#mw-annotation-1-1">1</a></span>
<span class="n">y</span> <span class="o">=</span> <span class="mi">2</span>  <a class="mw-annotation" href="#mw-annotation-1-2">2</a>
</code></pre></div>
<ol class="mw-annotations" data-mw-version="1">
<li id="mw-annotation-1-1">First</li>
<li id="mw-annotation-1-2">Second</li>
</ol>
```

The `mw-annotation` link class, the `mw-annotated` and `mw-annotations` classes, and the `mw-annotation-B-N` id scheme are the public contract.

## Examples

### A Paragraph

Any block works, not only code.
Put `[annotate]` before a paragraph and write `(N)` in its text:

```
[annotate]

Python-Markdown (1) parses the source, and markwright (2) adds the extensions.

1. The reference parser.
2. This package.
```

[annotate]

Python-Markdown (1) parses the source, and markwright (2) adds the extensions.

1. The reference parser.
2. This package.

### Inside a List Item

Indent `[annotate]`, the block, and its annotation list under the list item, the same as any other list content:

````
- Install the package:

    [annotate]

    ```bash
    uv add markwright  # (1)
    ```

    1. Adds it to `pyproject.toml`.

- Run the CLI:

    [annotate]

    The `mw` tool (1) runs the same stages as the in-process render.

    1. Installed with the package.
````

- Install the package:

    [annotate]

    ```bash
    uv add markwright  # (1)
    ```

    1. Adds it to `pyproject.toml`.

- Run the CLI:

    [annotate]

    The `mw` tool (1) runs the same stages as the in-process render.

    1. Installed with the package.

### Annotating a List

To put markers in a list's own items, wrap the list in `<div markdown>`:

```
[annotate]

<div markdown>

- Write the source (1)
- Render it (2)

</div>

1. Plain Markdown with markwright syntax.
2. In-process, or through `mw pre` and `mw post`.
```

[annotate]

<div markdown>

- Write the source (1)
- Render it (2)

</div>

1. Plain Markdown with markwright syntax.
2. In-process, or through `mw pre` and `mw post`.

The wrapper is for Python-Markdown.
It merges any list into a list directly before it, bullet or numbered, so without the `</div>` the annotation items become more items of the annotated list and annotate finds no annotation list.
The `markdown` attribute needs the `md_in_html` extension.
CommonMark renderers such as Hugo start a new list when the list type changes, so through `mw pre | hugo | mw post` the wrapper is not needed.

The same merge applies to an annotation list followed directly by a bullet list: put a paragraph between them.

### Nested Annotations

An annotation can hold an annotated block of its own.
Indent `[annotate]`, the block, and its list under the annotation item:

```
[annotate]

markwright (1) runs in two places.

1. A set of Python-Markdown extensions, plus a CLI.

    [annotate]

    The CLI is called `mw` (1).

    1. Short for markwright.
```

[annotate]

markwright (1) runs in two places.

1. A set of Python-Markdown extensions, plus a CLI.

    [annotate]

    The CLI is called `mw` (1).

    1. Short for markwright.

Each annotated block numbers its own ids, so the outer item is `mw-annotation-1-1` and the inner one `mw-annotation-2-1`; nothing collides.

## Host CSS and Script

markwright ships no CSS, JavaScript, or icons.
With no script, each marker is a plain link that jumps to its list item.
This site styles annotations after mkdocs-material's:

- [`docs/javascripts/annotate.js`](https://github.com/MasonEgger/markwright/blob/main/docs/javascripts/annotate.js) moves each list item's content into a tooltip card and hides the list.
  Hovering, focusing, or tapping a marker opens its card, and the card stays open while the pointer is over it.
  A marker inside a card opens a second card on top, which is what makes nested annotations work.
  A click pins a card until the next click outside it, and Escape closes every card.
  Printing puts the content back in the list.
- [`docs/stylesheets/extra.css`](https://github.com/MasonEgger/markwright/blob/main/docs/stylesheets/extra.css) draws the marker as a pulsing circled plus that turns into a cross while its card is open, and slides the card in.
  The marker's number stays in the link text, hidden on screen, so screen readers announce it and print shows it.
  Motion is off under `prefers-reduced-motion`.

To copy the setup into your own MkDocs site, add both files to `extra_javascript` and `extra_css`, and enable `attr_list` and `md_in_html` if you annotate lists.
