# CodePen

Embeds CodePen pens with configurable theme, default tab, height, and behavior flags.

## Configuration

```yaml
markdown_extensions:
  - do_markdown.codepen
```

No configuration options.

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

## Notes

- The embed must be on its own line
- The CodePen embed script is injected once, even with multiple embeds on a page
