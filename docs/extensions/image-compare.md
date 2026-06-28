# Image Compare

Creates side-by-side image comparisons with an interactive slider control.

## Usage

```python
import markdown

md = markdown.Markdown(extensions=["markwright.image_compare"])
html = md.convert("[compare https://example.com/before.jpg https://example.com/after.jpg]")
```

See [Using with MkDocs](../using-with-mkdocs.md) to load it in a MkDocs site.

## Syntax

```
[compare URL1 URL2 HEIGHT WIDTH]
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `URL1` | required | Left image URL |
| `URL2` | required | Right image URL |
| `HEIGHT` | `270` | Widget height in pixels |
| `WIDTH` | `480` | Widget width in pixels |

## Examples

### Basic Comparison

```
[compare https://picsum.photos/id/10/480/270 https://picsum.photos/id/20/480/270]
```

[compare https://picsum.photos/id/10/480/270 https://picsum.photos/id/20/480/270]

### Custom Dimensions

```
[compare https://picsum.photos/id/10/600/400 https://picsum.photos/id/20/600/400 400 600]
```

[compare https://picsum.photos/id/10/600/400 https://picsum.photos/id/20/600/400 400 600]

## Notes

- The embed must be on its own line
- Exactly 2 image URLs are required (no more, no fewer)
- The slider starts at 50% and uses a CSS custom property (`--value`) for positioning
- No script injection required; uses an inline `oninput` handler
