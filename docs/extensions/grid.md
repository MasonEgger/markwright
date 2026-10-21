# Grid

Adds grid classes to the list that follows a `[grid]` or `[grid cards]` line.

## Usage

```python
import markdown

md = markdown.Markdown(extensions=["markwright.grid"])
```

See [Using with MkDocs](../integrations/mkdocs.md) to load it in a MkDocs site.

## Syntax

```
[grid]

- First
- Second

[grid cards]

- **Card One**: Text
- **Card Two**: Text
```

| Directive | Result |
|-----------|--------|
| `[grid]` | The next list gets `class="mw-grid"`. |
| `[grid cards]` | The next list gets `class="mw-grid mw-cards"`. |

The directive must be on its own line, with a blank line before the list.
It affects the first `<ul>` or `<ol>` that follows it.

## How It Works

Grid is a two-stage extension.
The source stage (`mw pre`) replaces the directive with a marker comment:

```html
<!-- mw-grid:{"version": 1, "cards": true} -->
```

The HTML stage (`mw post`) finds the marker, adds the classes to the list that follows, and removes the marker.
The payload is versioned and read fail-soft, like the [fence](fence.md) marker.
A marker with an invalid payload, or with no list after it, is skipped, and `--warn` reports why.
A plain `[grid]` carries an empty payload besides `version`; only `cards` is recorded.

## HTML Contract

```html
<ul class="mw-grid mw-cards">
<li>One</li>
<li>Two</li>
</ul>
```

## Examples

```
[grid cards]

- **Highlight**: marks text with `<mark>`.
- **Fence**: labels and prefixes for code.
- **Button**: a link styled as a button.
```

[grid cards]

- **Highlight**: marks text with `<mark>`.
- **Fence**: labels and prefixes for code.
- **Button**: a link styled as a button.

## Host CSS

markwright ships no CSS, JavaScript, or icons.
The classes are inert until the host styles them.
This site's `ul.mw-grid` and `ul.mw-grid.mw-cards` rules in [`docs/stylesheets/extra.css`](https://github.com/MasonEgger/markwright/blob/main/docs/stylesheets/extra.css) lay the items out in a CSS grid and draw the card borders.
