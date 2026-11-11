# YouTube

Embeds YouTube videos as responsive iframes with automatic aspect ratio calculation.

[youtube dQw4w9WgXcQ]

```
[label Markdown]
[youtube dQw4w9WgXcQ]
```

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

## Host CSS and Script

markwright ships no CSS, JavaScript, or icons.
In `eager` and `lazy` modes the embed is an `<iframe class="youtube">` that loads YouTube's own player, so the host needs no code; `lazy` only adds `loading="lazy"`.
This site sizes the frame with the `iframe.youtube` rule in [`docs/stylesheets/extra.css`](https://github.com/MasonEgger/markwright/blob/main/docs/stylesheets/extra.css): capped at the content width, centered, no border.

In `click` mode the embed is the `mw-embed` preview instead, whose hooks a host script swaps for the live iframe.
[Click-to-Load](../click-to-load.md) is the contract for that markup and carries a worked host script.
