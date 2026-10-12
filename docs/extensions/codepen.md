# CodePen

Embeds CodePen pens with configurable theme, default tab, height, and behavior flags.

## Usage

```python
import markdown

md = markdown.Markdown(extensions=["markwright.codepen"])
html = md.convert("[codepen MattCowley vwPzeX]")
```

See [Using with MkDocs](../integrations/mkdocs.md) to load it in a MkDocs site.

## Syntax

```
[codepen USER HASH flags...]
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `USER` | required | CodePen username |
| `HASH` | required | Pen hash/slug |

### Flags

Flags can appear in any order after USER and HASH:

| Flag | Description |
|------|-------------|
| `light` | Light theme (default) |
| `dark` | Dark theme |
| `html` | Show HTML tab |
| `css` | Show CSS tab |
| `js` | Show JS tab |
| `result` | Show result tab (default; combines with other tabs) |
| `lazy` | Lazy load the pen (adds `data-preview="true"`) |
| `editable` | Allow editing (adds `data-editable="true"`) |
| *integer* | Custom height in pixels (default: 256) |

Tab priority when multiple are specified: html > css > js.

## Examples

### Basic Embed

```
[codepen MattCowley vwPzeX]
```

[codepen MattCowley vwPzeX]

### Dark Theme with CSS Tab

```
[codepen MattCowley vwPzeX dark css]
```

[codepen MattCowley vwPzeX dark css]

### Custom Height, Lazy, Editable

```
[codepen MattCowley vwPzeX 400 lazy editable]
```

[codepen MattCowley vwPzeX 400 lazy editable]

## Load Mode

The `load` option decides when the embed contacts the provider.
Set it in `markwright.toml`, or pass it through `extension_configs` in-process.

| Value | Output |
|-------|--------|
| `eager` (default) | The live embed, with the provider script injected once per page. |
| `click` | An inert preview with a load button and a direct link; no provider script. |

```toml
[codepen]
load = "click"
```

```python
md = markdown.Markdown(
    extensions=["markwright.codepen"],
    extension_configs={"markwright.codepen": {"load": "click"}},
)
```

The `load` option is separate from the `lazy` flag above.
The flag is CodePen's own preview mode, which still loads the CodePen script; `load = "click"` loads nothing from CodePen until the reader asks.

See [Click-to-Load](../click-to-load.md) for the preview markup and a host script that swaps in the live embed.

## Notes

- The embed must be on its own line
- The CodePen embed script is injected once, even with multiple embeds on a page, and only when at least one embed is `eager`
