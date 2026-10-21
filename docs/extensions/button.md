# Button

Turns a standalone `[button ...]` line into a link styled as a button.

## Usage

```python
import markdown

md = markdown.Markdown(extensions=["markwright.button"])
html = md.convert("[button primary https://example.com Get Started]")
```

See [Using with MkDocs](../integrations/mkdocs.md) to load it in a MkDocs site.

## Syntax

```
[button URL TEXT]
[button primary URL TEXT]
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `primary` | omitted | Optional keyword that adds the `mw-button-primary` class. |
| `URL` | required | The link target, one word with no spaces. |
| `TEXT` | required | The label, everything after the URL up to the closing bracket. |

The URL and the text are HTML-escaped.
The directive must be on its own line, like the embeds.

## HTML Contract

```html
<a class="mw-button" href="https://example.com">Read More</a>
<a class="mw-button mw-button-primary" href="https://example.com">Get Started</a>
```

The classes `mw-button` and `mw-button-primary` are the whole contract.
markwright adds no inline styles, no attributes beyond `class` and `href`, and no script.

## Examples

```
[button primary https://example.com Get Started]

[button https://example.com Read More]
```

[button primary https://example.com Get Started]

[button https://example.com Read More]

## Host CSS

markwright ships no CSS, JavaScript, or icons.
The page that renders the HTML supplies the look.
This site styles the buttons in [`docs/stylesheets/extra.css`](https://github.com/MasonEgger/markwright/blob/main/docs/stylesheets/extra.css), under the `a.mw-button` rules, using Material's theme colors.
Copy those rules as a starting point, or write your own selectors against the two classes.
