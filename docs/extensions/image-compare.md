# Image Compare

Creates side-by-side image comparisons with an interactive slider control.

[compare https://picsum.photos/id/10/480/270 https://picsum.photos/id/20/480/270]

```
[label Markdown]
[compare https://picsum.photos/id/10/480/270 https://picsum.photos/id/20/480/270]
```

## Usage

```python
import markdown

md = markdown.Markdown(extensions=["markwright.image_compare"])
html = md.convert("[compare https://example.com/before.jpg https://example.com/after.jpg]")
```

See [Using with MkDocs](../integrations/mkdocs.md) to load it in a MkDocs site.

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

## Host CSS and Script

markwright ships no CSS, JavaScript, or icons.
The hooks are the `image-compare` wrapper (do-markdownit's own shape), its `image-left` and `image-right` images, and the `control` range input with its `control-arrow`; the slider position rides a `--value` custom property that an inline `oninput` handler updates, so the comparison works with no host script.
This site sizes and clips the two images and styles the slider in the `.image-compare` rules of [`docs/stylesheets/extra.css`](https://github.com/MasonEgger/markwright/blob/main/docs/stylesheets/extra.css); without that CSS markwright emits only the structure, so the host CSS is what makes the overlay visible.
