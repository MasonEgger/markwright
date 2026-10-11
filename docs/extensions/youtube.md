# YouTube

Embeds YouTube videos as responsive iframes with automatic aspect ratio calculation.

## Usage

```python
import markdown

md = markdown.Markdown(extensions=["markwright.youtube"])
html = md.convert("[youtube dQw4w9WgXcQ]")
```

See [Using with MkDocs](../integrations/mkdocs.md) to load it in a MkDocs site.

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

## Load Mode

The `load` option decides when the embed contacts the provider.
Set it in `markwright.toml`, or pass it through `extension_configs` in-process.

| Value | Output |
|-------|--------|
| `eager` (default) | The live iframe. |
| `lazy` | The live iframe with `loading="lazy"`, so the browser fetches it when it scrolls near the viewport. |
| `click` | An inert preview with a "Load video" button and a "Watch on YouTube" link; no iframe until a host script loads it. |

```toml
[youtube]
load = "click"
```

```python
md = markdown.Markdown(
    extensions=["markwright.youtube"],
    extension_configs={"markwright.youtube": {"load": "click"}},
)
```

See [Click-to-Load](../click-to-load.md) for the preview markup and a host script that swaps in the live embed.

## Notes

- The embed must be on its own line (not inline with other text)
- The video ID is URL-encoded for safety
- A fallback link is included inside the iframe for accessibility
