# Twitter

Embeds tweets with configurable theme, alignment, and width. Accepts both `twitter.com` and `x.com` URLs, canonicalizing to `twitter.com`.

## Configuration

```yaml
markdown_extensions:
  - do_markdown.twitter
```

No configuration options.

## Syntax

```
[twitter URL flags...]
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `URL` | required | Tweet URL (`twitter.com` or `x.com`) |

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
