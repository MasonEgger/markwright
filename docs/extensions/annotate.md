# Annotate

Links `(N)` markers inside a block, usually a code block, to the items of the numbered list that follows it.

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

## Example

[annotate]

```python
name = "markwright"  # (1)
debug = False  # (2)!
```

1. The package name.
2. Switches off debug output.

## Host CSS and Script

markwright ships no CSS, JavaScript, or icons.
With no script, each marker is a plain link that jumps to its list item.
This site adds a tooltip:

- [`docs/javascripts/annotate.js`](https://github.com/MasonEgger/markwright/blob/main/docs/javascripts/annotate.js) shows the target item's content when a marker is hovered or focused.
- [`docs/stylesheets/extra.css`](https://github.com/MasonEgger/markwright/blob/main/docs/stylesheets/extra.css) styles `a.mw-annotation`, `ol.mw-annotations`, and the tooltip.
