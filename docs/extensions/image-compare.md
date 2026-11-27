# Image Compare

Creates side-by-side image comparisons with an interactive slider control.

[compare https://picsum.photos/id/10/480/270 https://picsum.photos/id/20/480/270]

```
[label Markdown]
[compare https://picsum.photos/id/10/480/270 https://picsum.photos/id/20/480/270]
```

An embed is always its own block: `mw pre` writes a blank line before and after it when the neighboring line is not blank, so it splits the paragraph it sat beside, and the text after it renders as Markdown.
Inside a raw HTML block no blank line is added.
In-process, an embed indented one to three columns under a list item gets none either, since Python-Markdown ends the item at a blank line there; the item stays tight and the embed stays in it.

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

- The embed must be on its own line; a blank line before and after it is optional, since the pre stage writes one wherever the neighboring line is not blank
- Exactly 2 image URLs are required (no more, no fewer)
- The slider starts at 50% and uses a CSS custom property (`--value`) for positioning
- No script injection required; uses an inline `oninput` handler

## HTML Contract

```html
<div class="image-compare" style="--value:50%; height: 270px; width: 480px;">
    <img class="image-left" src="https://picsum.photos/id/10/480/270" alt="Image left"/>
    <img class="image-right" src="https://picsum.photos/id/20/480/270" alt="Image right"/>
    <input type="range" class="control" min="0" max="100" value="50"
      oninput="this.parentNode.style.setProperty('--value', `${this.value}%`)" />
    <svg class="control-arrow" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><path fill="currentColor" d="..."/></svg>
</div>
```

The `<path>` data is shortened here.

## Host CSS and Script

markwright ships no CSS, JavaScript, or icons.
The hooks are the `image-compare` wrapper (do-markdownit's own shape), its `image-left` and `image-right` images, and the `control` range input with its `control-arrow`; the slider position rides a `--value` custom property that an inline `oninput` handler updates, so the comparison works with no host script.
This site sizes and clips the two images and styles the slider in the `.image-compare` rules of [`docs/stylesheets/extra.css`](https://github.com/MasonEgger/markwright/blob/main/docs/stylesheets/extra.css); without that CSS markwright emits only the structure, so the host CSS is what makes the overlay visible.
