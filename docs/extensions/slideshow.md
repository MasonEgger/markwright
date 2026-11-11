# Slideshow

Creates image slideshows with left/right navigation arrows and scroll-snap behavior.

[slideshow https://picsum.photos/id/10/480/270 https://picsum.photos/id/20/480/270 https://picsum.photos/id/30/480/270]

```
[label Markdown]
[slideshow https://picsum.photos/id/10/480/270 https://picsum.photos/id/20/480/270 https://picsum.photos/id/30/480/270]
```

## Usage

```python
import markdown

md = markdown.Markdown(extensions=["markwright.slideshow"])
html = md.convert("[slideshow https://example.com/a.jpg https://example.com/b.jpg]")
```

See [Using with MkDocs](../integrations/mkdocs.md) to load it in a MkDocs site.

## Syntax

```
[slideshow URL1 URL2 ...URLs HEIGHT WIDTH]
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| URLs | required (1+) | Image URLs (one or more) |
| `HEIGHT` | `270` | Slideshow height in pixels |
| `WIDTH` | `480` | Slideshow width in pixels |

Height and width are optional trailing integers. They are distinguished from URLs by being purely numeric.

## Examples

### Custom Dimensions

```
[slideshow https://picsum.photos/id/10/600/400 https://picsum.photos/id/20/600/400 400 600]
```

[slideshow https://picsum.photos/id/10/600/400 https://picsum.photos/id/20/600/400 400 600]

## Notes

- The embed must be on its own line
- At least one image URL is required (a single-image slideshow is valid, matching upstream `do-markdownit`)
- Navigation arrows appear on left and right sides
- Uses CSS scroll-snap for smooth slide transitions
- No script injection required

## Host CSS and Script

markwright ships no CSS, JavaScript, or icons.
The hooks are the `slideshow` wrapper (do-markdownit's own shape), its `slides` track of `<img>` slides, and the `action left` and `action right` arrows whose inline `onclick` scrolls the track, so paging works with no host script.
This site lays out the track with CSS scroll-snap and styles the arrows in the `.slideshow` rules of [`docs/stylesheets/extra.css`](https://github.com/MasonEgger/markwright/blob/main/docs/stylesheets/extra.css); without that CSS the slides stack rather than scroll.
