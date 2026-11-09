# Grid

Adds grid classes to the list that follows a `[grid]` or `[grid cards]` line.

[grid cards]

-   :lucide-check: **Mark text**

    ---

    Highlight a word in prose, in inline code, or inside a code block.

    [:lucide-arrow-right: Highlight](highlight.md)

-   :mw-bolt: **Label code**

    ---

    Add labels, environments, and `$` or `#` prompts to fenced code.

    [:lucide-arrow-right: Fence](fence.md)

-   :lucide-info: **Explain code**

    ---

    Link `(1)` markers in a block to notes that open as tooltips.

    [:lucide-arrow-right: Annotate](annotate.md)

-   :mw-star: **Lay out content**

    ---

    Turn any list into a responsive grid of plain items or cards.

    [:lucide-arrow-right: Syntax](#syntax)

````
[label Markdown]
[grid cards]

-   :lucide-check: **Mark text**

    ---

    Highlight a word in prose, in inline code, or inside a code block.

    [:lucide-arrow-right: Highlight](highlight.md)

-   :mw-bolt: **Label code**

    ---

    Add labels, environments, and `$` or `#` prompts to fenced code.

    [:lucide-arrow-right: Fence](fence.md)

-   :lucide-info: **Explain code**

    ---

    Link `(1)` markers in a block to notes that open as tooltips.

    [:lucide-arrow-right: Annotate](annotate.md)

-   :mw-star: **Lay out content**

    ---

    Turn any list into a responsive grid of plain items or cards.

    [:lucide-arrow-right: Syntax](#syntax)
````

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

## Card Content

A card is a list item, so it holds any Markdown a list item can.
The cards at the top of this page follow mkdocs-material's card pattern:

- an icon from the [icons](icons.md) extension, then a bold title;
- a `---` rule;
- a sentence or two;
- a link.

Indent everything after the first line by four spaces so it stays inside the item.

## Host CSS

markwright ships no CSS, JavaScript, or icons.
The classes are inert until the host styles them.
This site's grid rules in [`docs/stylesheets/extra.css`](https://github.com/MasonEgger/markwright/blob/main/docs/stylesheets/extra.css) follow mkdocs-material's:

- `ul.mw-grid` is a CSS grid with `repeat(auto-fit, minmax(min(100%, 16rem), 1fr))` columns, so items fill as many columns as fit and drop to one on a narrow screen.
- `ul.mw-grid.mw-cards > li` gets a hairline border that turns into a shadow on hover or focus.
- A card's opening icon is drawn at twice the text size, centered on the title.
