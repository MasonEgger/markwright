# Grid

Lays content out in a grid.
A `[grid ...]` line classes the list after it, and a paired `[grid ...]` and `[/grid]` wrap any blocks between them in a grid `<div>`, with `[card]` and `[/card]` grouping those blocks into cards.

[grid cards 3]

[card]

**Mark Text**

Highlight a word in prose, in inline code, or inside a code block.

[Highlight](highlight.md)

[/card]

[card]

**Label Code**

Add labels, environments, and `$` or `#` prompts to fenced code.

[Fence](fence.md)

[/card]

[card]

**Explain Code**

Link `(1)` markers in a block to notes that open as tooltips.

[Annotate](annotate.md)

[/card]

[/grid]

````
[label Markdown]
[grid cards 3]

[card]

**Mark Text**

Highlight a word in prose, in inline code, or inside a code block.

[Highlight](highlight.md)

[/card]

[card]

**Label Code**

Add labels, environments, and `$` or `#` prompts to fenced code.

[Fence](fence.md)

[/card]

[card]

**Explain Code**

Link `(1)` markers in a block to notes that open as tooltips.

[Annotate](annotate.md)

[/card]

[/grid]
````

The directive lines are inside the source fence above, so the pre stage leaves them literal and the fence renders the source as written.

## Usage

```python
import markdown

md = markdown.Markdown(extensions=["markwright.grid"])
```

See [Using with MkDocs](../integrations/mkdocs.md) to load it in a MkDocs site.

## Grid Shortcut

A `[grid ...]` line with no closer is the list shortcut.
It classes the first `<ul>` or `<ol>` that follows it and is the 0.4.0 behavior.
The directive is on its own line, with a blank line before the list.

[grid cards]

- **Mark**: highlight a word in prose or code.
- **Label**: add a label and a prompt to a fence.
- **Explain**: link a marker to a note.

````
[label Markdown]
[grid cards]

- **Mark**: highlight a word in prose or code.
- **Label**: add a label and a prompt to a fence.
- **Explain**: link a marker to a note.
````

| Directive | Result |
|-----------|--------|
| `[grid]` | The next list gets `class="mw-grid"`. |
| `[grid cards]` | The next list gets `class="mw-grid mw-grid-cards"`. |

## Column Counts

Add a count from 1 to 6 to pin the number of columns.
The token order is free, so `[grid 3]`, `[grid cards 3]`, and `[grid 3 cards]` are all the same.
Any other token, a second count, a count outside 1 to 6, or a repeated flag leaves the line literal.

A count adds `mw-grid-cols-N` to the grid.
Without one, this site's sample flows into as many columns as fit and drops to one on a narrow screen.

| Directive | Classes |
|-----------|---------|
| `[grid 3]` | `mw-grid mw-grid-cols-3` |
| `[grid cards 3]` | `mw-grid mw-grid-cards mw-grid-cols-3` |

## Block Grids

A `[grid ...]` paired with `[/grid]` is a block grid.
It wraps everything between its lines in a `<div class="mw-grid">`, and each child block is a grid cell.
The opener takes the same `cards` and count tokens as the shortcut, so a block grid can be `[grid cards 2]` ... `[/grid]`.

[grid 2]

A block grid holds any Markdown block, from a heading to a list.

Each top-level block between the opener and the closer is one cell.

[/grid]

````
[label Markdown]
[grid 2]

A block grid holds any Markdown block, from a heading to a list.

Each top-level block between the opener and the closer is one cell.

[/grid]
````

An unclosed `[grid ...]` falls back to the list shortcut.
A list shortcut cannot sit directly inside a block grid at the same indentation: the block grid's `[/grid]` pairs with the nearer inner opener, turning that inner opener into a block grid and leaving the outer `[grid]` unclosed, so the outer grid demotes to a shortcut.
To nest a shortcut list, put it inside a `[card]`, whose `[/card]` leaves the unclosed `[grid ...]` intact as a shortcut, or close the inner grid to get a nested block grid instead.

## Cards

A `[card]` paired with `[/card]` directly inside a block grid wraps its content in `<div class="mw-card">`.
One card holds several blocks, such as a heading, a paragraph, a list, and a link.

A `[card]` outside a block grid, an unclosed `[card]`, and a stray `[/card]` stay literal text; see [Fail-Soft and Warnings](#fail-soft-and-warnings).

````
[label Markdown]
[grid cards 2]

[card]

### Pre Stage

`mw pre` expands the source to markers.

[/card]

[card]

### Post Stage

`mw post` applies the markers to the rendered HTML.

[/card]

[/grid]
````

## Nesting

Containers nest freely: a card in a grid, a grid in a card, a grid in a grid.
A nested opener and its closer sit at the same indentation as each other.

````
[label Markdown]
[grid 2]

[card]

### Outer

[grid 2]

Nested cell one.

Nested cell two.

[/grid]

[/card]

[/grid]
````

## How It Works

Grid is a two-stage extension.
The source stage (`mw pre`) replaces each directive with a marker comment:

```html
<!-- mw-grid:{"version": 1, "cards": true, "columns": 3} -->
<!-- mw-grid-block:{"version": 1, "cards": true, "columns": 3} -->
<!-- mw-grid-end:{"version": 1} -->
<!-- mw-card:{"version": 1} -->
<!-- mw-card-end:{"version": 1} -->
```

The HTML stage (`mw post`) classes the list a shortcut marker precedes, wraps the span between each block-grid or card open and close marker in a `<div>`, and removes every marker.
It orders the open and close markers of a kind by position and matches them like brackets, so nested grids and cards wrap in order and close in reverse.

## HTML Contract

A list shortcut classes the list in place:

```html
<ul class="mw-grid mw-grid-cards mw-grid-cols-3">
<li>One</li>
<li>Two</li>
</ul>
```

A block grid wraps its blocks, and each card wraps its own:

```html
<div class="mw-grid mw-grid-cards mw-grid-cols-3">
<div class="mw-card">
<h3>Pre Stage</h3>
<p>Expands the source to markers.</p>
</div>
</div>
```

The `mw-grid`, `mw-grid-cards`, `mw-grid-cols-N`, and `mw-card` classes are the public contract.
The `mw-cards` class from 0.4.0 is renamed `mw-grid-cards`.

## Marker Contracts

Each marker is a versioned public contract, read fail-soft like the [fence](fence.md) marker.

| Marker | Payload | Role |
|--------|---------|------|
| `mw-grid` | `version`, `cards`, `columns` | Classes the list shortcut that follows it. |
| `mw-grid-block` / `mw-grid-end` | `version`, `cards`, `columns` on the opener | Wrap a block grid in a `<div>`. |
| `mw-card` / `mw-card-end` | `version` | Wrap a card in a `<div class="mw-card">`. |
| `mw-grid-problem` | `version`, `line`, `directive`, `reason` | Mark a container left literal so `mw post --warn` reports it. |

The `cards` and `columns` fields are present only when the opener carries them.
A payload bumps its version with no migration shim when a field changes, since the project is pre-1.0 with one host.

## Fail-Soft and Warnings

A directive the extension cannot turn into markup stays literal and is reported by `mw post --warn`, never raised:

- an unclosed `[card]`;
- a stray `[/card]` or `[/grid]`;
- a `[card]` whose nearest enclosing container is not a block grid.

The pre stage attaches an inline `mw-grid-problem` marker to each literal directive, and the post stage composes one `--warn` line from the marker and removes the comment.
An invalid `[grid ...]` opener and an opener or closer inside fenced or indented code also stay literal, with no report.
A shortcut marker is skipped, and `--warn` reports why, when its payload is invalid or no list follows it.

## Host CSS and Script

markwright ships no CSS, JavaScript, or icons.
The hooks are the `mw-grid` wrapper, the `mw-grid-cards` class on a cards grid, the `mw-grid-cols-N` column count, and the `mw-card` class on each card; they are inert until the host styles them, and no host script is involved.
This site's grid rules in [`docs/stylesheets/extra.css`](https://github.com/MasonEgger/markwright/blob/main/docs/stylesheets/extra.css) follow mkdocs-material's:

- `.mw-grid` is a CSS grid that flows items into as many columns as fit and drops to one on a narrow screen; `mw-grid-cols-N` pins an exact count.
- `.mw-card` and a cards list's items get a hairline border that lifts into a shadow on hover or focus.
- A card's opening icon is drawn at twice the text size, centered on the title.
