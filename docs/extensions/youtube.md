# YouTube

Embeds YouTube videos as responsive iframes with automatic aspect ratio calculation.

## Configuration

```yaml
markdown_extensions:
  - do_markdown.youtube
```

No configuration options.

## Syntax

```
[youtube VIDEO_ID]
[youtube VIDEO_ID HEIGHT]
[youtube VIDEO_ID HEIGHT WIDTH]
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `VIDEO_ID` | required | The YouTube video ID |
| `HEIGHT` | `270` | Height in pixels |
| `WIDTH` | `480` | Width in pixels |

The aspect ratio is calculated automatically from the dimensions.

## Examples

### Default Dimensions (480x270)

```
[youtube dQw4w9WgXcQ]
```

[youtube dQw4w9WgXcQ]

### Custom Dimensions

```
[youtube dQw4w9WgXcQ 360 640]
```

[youtube dQw4w9WgXcQ 360 640]

## Notes

- The embed must be on its own line (not inline with other text)
- The video ID is URL-encoded for safety
- A fallback link is included inside the iframe for accessibility
