# Twitter

Embeds tweets with configurable theme, alignment, and width. Accepts `twitter.com` and `x.com` references in several forms (full URL, scheme-less, or a bare `user/status/id`), canonicalizing the output to `twitter.com`.

## Usage

```python
import markdown

md = markdown.Markdown(extensions=["markwright.twitter"])
html = md.convert("[twitter https://twitter.com/User/status/123]")
```

See [Using with MkDocs](../integrations/mkdocs.md) to load it in a MkDocs site.

## Syntax

```
[twitter URL flags...]
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `URL` | required | Tweet reference: a full URL, a scheme-less URL, or a bare `user/status/id` (`twitter.com` or `x.com`) |

### Accepted URL forms

All of these resolve to the same tweet:

```
[twitter https://twitter.com/User/status/123]
[twitter https://x.com/User/status/123]
[twitter twitter.com/User/status/123]
[twitter User/status/123]
```

### Flags

| Flag | Description |
|------|-------------|
| `light` | Light theme (default) |
| `dark` | Dark theme |
| `left` | Left-align the tweet |
| `center` | Center-align (default) |
| `right` | Right-align the tweet |
| *integer* | Width in pixels (clamped 250-550, default: 550) |

## Examples

### Basic Tweet

```
[twitter https://twitter.com/github/status/1234567890]
```

[twitter https://twitter.com/github/status/1234567890]

### Dark Theme, Left-Aligned

```
[twitter https://twitter.com/github/status/1234567890 dark left]
```

[twitter https://twitter.com/github/status/1234567890 dark left]

### Custom Width

```
[twitter https://twitter.com/github/status/1234567890 400]
```

[twitter https://twitter.com/github/status/1234567890 400]

## Notes

- The embed must be on its own line
- `x.com` URLs are automatically converted to `twitter.com`
- Width is clamped to 250-550px (Twitter's supported range)
- The Twitter widgets script is injected once per page
