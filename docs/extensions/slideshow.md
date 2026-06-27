# Slideshow

Creates image slideshows with left/right navigation arrows and scroll-snap behavior.

## Configuration

```yaml
markdown_extensions:
  - do_markdown.slideshow
```

No configuration options.

## Syntax

```
[slideshow URL1 URL2 ...URLs HEIGHT WIDTH]
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| URLs | required (2+) | Image URLs (at least 2 required) |
| `HEIGHT` | `270` | Slideshow height in pixels |
| `WIDTH` | `480` | Slideshow width in pixels |

Height and width are optional trailing integers. They are distinguished from URLs by being purely numeric.

## Examples

### Basic Slideshow

```
[slideshow https://picsum.photos/id/10/480/270 https://picsum.photos/id/20/480/270 https://picsum.photos/id/30/480/270]
```

[slideshow https://picsum.photos/id/10/480/270 https://picsum.photos/id/20/480/270 https://picsum.photos/id/30/480/270]

### Custom Dimensions

```
[slideshow https://picsum.photos/id/10/600/400 https://picsum.photos/id/20/600/400 400 600]
```

[slideshow https://picsum.photos/id/10/600/400 https://picsum.photos/id/20/600/400 400 600]

## Notes

- The embed must be on its own line
- At least 2 image URLs are required
- Navigation arrows appear on left and right sides
- Uses CSS scroll-snap for smooth slide transitions
- No script injection required
