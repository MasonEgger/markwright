# Instagram

Embeds Instagram posts with optional caption display, alignment, and width.

## Configuration

```yaml
markdown_extensions:
  - do_markdown.instagram
```

No configuration options.

## Syntax

```
[instagram URL flags...]
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `URL` | required | Instagram post URL (`instagram.com/p/...`) |

### Flags

| Flag | Description |
|------|-------------|
| `caption` | Show the post caption |
| `left` | Left-align the post |
| `center` | Center-align (default) |
| `right` | Right-align the post |
| *integer* | Width in pixels (clamped 326-550, default: auto) |

## Examples

### Basic Post

```
[instagram https://www.instagram.com/p/CkQuv3_LRgS]
```

[instagram https://www.instagram.com/p/CkQuv3_LRgS]

### With Caption

```
[instagram https://www.instagram.com/p/CkQuv3_LRgS caption]
```

[instagram https://www.instagram.com/p/CkQuv3_LRgS caption]

### Left-Aligned with Custom Width

```
[instagram https://www.instagram.com/p/CkQuv3_LRgS left 400]
```

[instagram https://www.instagram.com/p/CkQuv3_LRgS left 400]

## Notes

- The embed must be on its own line
- Width is clamped to 326-550px (Instagram's supported range)
- The Instagram embed script is injected once per page
