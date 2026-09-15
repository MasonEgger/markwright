# Instagram

Embeds Instagram posts with optional caption display, alignment, and width.

## Usage

```python
import markdown

md = markdown.Markdown(extensions=["markwright.instagram"])
html = md.convert("[instagram https://www.instagram.com/p/CkQuv3_LRgS]")
```

See [Using with MkDocs](../integrations/mkdocs.md) to load it in a MkDocs site.

## Syntax

```
[instagram URL flags...]
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `URL` | required | Post reference: a full URL, a scheme-less URL, or a bare shortcode |

### Accepted URL forms

All of these resolve to the same post, and the embed permalink is canonicalized to `https://www.instagram.com/p/<shortcode>`:

```
[instagram https://www.instagram.com/p/CkQuv3_LRgS]
[instagram instagram.com/p/CkQuv3_LRgS]
[instagram CkQuv3_LRgS]
```

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
