# Renderer Requirements

The `mw pre` and `mw post` stages coordinate through markers that survive a normal Markdown render, not through any knowledge of the renderer.
For that round-trip to work, the renderer you place between the two stages has to meet three requirements.
Each requirement maps to a feature, and a renderer that does not meet one disables that feature while leaving the rest working.

## The Three Requirements

### 1. Raw HTML Passthrough

The pre stage expands embed, button, and lightbox directives into raw HTML, turns mermaid fences into a `<pre>` block, inlines icon SVG, and, with highlight active, wraps prose markers in `<mark>`.
A renderer that strips raw HTML by default has to enable its passthrough option (`--unsafe` for cmark, `unsafe = true` for Hugo's Goldmark, and the equivalent elsewhere).
Without passthrough, the expanded HTML and pre-stage highlights are dropped by the renderer before the post stage ever sees them.

### 2. Comment Preservation

The pre stage encodes the fence, grid, annotate, and tabs directives as HTML comments (listed under [Marker Comments](#marker-comments)) and the post stage reads them back.
For a fence, the `<!-- mw-fence:{JSON} -->` comment sits immediately before the fence, and the post stage uses it to style the adjacent code block.
A renderer that preserves HTML comments lets all of these round-trip.
A renderer that drops comments disables those four features and breaks nothing else: a code block still renders, just without its label, environment tint, or line prefixes, and a grid, annotation, or tab directive does nothing.

### 3. Span-Based Syntax Highlighting

In-code highlighting (`\<^>...\<^>` inside a fence) depends on the renderer wrapping syntax-highlighted tokens in tags, so the post stage can place `<mark>` without crossing a token boundary.
Any Pygments- or Chroma-style highlighter qualifies.
A renderer that emits plain, untagged code text still highlights, but the `<mark>` placement has fewer token boundaries to respect.

## Marker Comments

Four extensions carry data from the pre stage to the post stage in versioned HTML comments.
Each is a public contract, read fail-soft, and each has its payload documented on its own page.

| Marker | Extension | Role |
|--------|-----------|------|
| `mw-fence` | [Fence](extensions/fence.md) | Carries the fence directives to the code block that follows. |
| `mw-grid` | [Grid](extensions/grid.md) | Classes the list that follows a `[grid]` or `[grid cards]` shortcut. |
| `mw-grid-block`, `mw-grid-end` | [Grid](extensions/grid.md) | Open and close a block grid. |
| `mw-card`, `mw-card-end` | [Grid](extensions/grid.md) | Open and close a card inside a block grid. |
| `mw-annotate` | [Annotate](extensions/annotate.md) | Links the `(N)` markers in the block that follows to the numbered list after it. |
| `mw-tab`, `mw-tab-end` | [Tabs](extensions/tabs.md) | Open and close one tab, grouped into sets. |
| `mw-grid-problem`, `mw-tab-problem` | [Grid](extensions/grid.md), [Tabs](extensions/tabs.md) | Sit after a directive the pre stage left literal, so `mw post --warn` can report it. |

The post stage removes every one of them from its output.
The rest of this page describes `mw-fence` in detail; the others follow the same versioning policy.

## The `mw-fence` Marker Contract

The fence directives travel from `pre` to `post` as a single HTML comment immediately before the fence:

```
<!-- mw-fence:{"version": 1, "label": "deploy.sh"} -->
```

The fence itself is left intact, so your renderer still syntax-highlights the real code.
There is no placeholder and no rewritten language token.
The post stage associates a marker with the first code block that follows it, before the next marker.
For an indented fence (up to three spaces, or inside a list item), the comment carries the fence's indentation and is followed by a blank line, so it stays inside the list item and renders as its own block.
This comment is the only cross-tool surface, so its shape is a versioned contract.

### v1 Payload

```json
{
  "version": 1,
  "label": "deploy.sh",
  "secondary_label": "optional second label",
  "environment": "local",
  "prefix_type": "command",
  "prefix_value": "$"
}
```

`version` is an integer and the only required field.
Every other field is optional and present only when the author used that directive.
`prefix_type` is one of `line_numbers`, `command`, `super_user`, or `custom_prefix`.
`prefix_value` carries the rendered prefix (`$`, `#`, or custom text) and is absent for `line_numbers`.
The post stage applies whatever fields are present and ignores any it does not recognize.

### Versioning Policy

The policy is best-effort, backward compatible, and fail-soft.

The schema grows additively: a new optional field does not bump `version`, and only a breaking change does.
The post stage reads any marker whose `version` it knows (currently only `1`) and ignores unknown fields, so a newer pre stage that only added fields still works with an older post stage.
A marker whose `version` is greater than the post stage knows is skipped as a no-op and reported under `--warn`.
A malformed payload is skipped, never executed, and reported under `--warn`: invalid JSON, a payload that is not a JSON object, or a known field of the wrong type (for example a numeric `label`, or a `prefix_type` outside the four values).
A marker with no code block before the next marker is skipped the same way.

## What Degrades, and How

The post stage degrades gracefully.
If a marker or signature is absent, the matching feature is a no-op rather than an error.

| Unmet Requirement | Feature That Stops | Behavior |
|-------------------|--------------------|----------|
| Raw HTML passthrough | Embeds, buttons, lightboxes, mermaid, icons, pre-stage prose highlight | The renderer drops the expanded HTML before post runs |
| Comment preservation | Fence labels, environments, prefixes; grids, annotations, and tabs | Code blocks render unstyled and the other directives do nothing; the skip is silent |
| Span-based highlighting | In-code highlight | Markers still wrap, with fewer token boundaries to respect |

The comment-stripping case is special.
Once a renderer drops a marker comment, the post stage has no evidence the directive ever existed, so a stripped marker is silently absent rather than a detectable skip.
That is why `--warn` cannot report it: a post-only filter sees nothing to warn about.
Embed script injection is unaffected, since it keys on the embed class signature in the HTML, not on any comment.
