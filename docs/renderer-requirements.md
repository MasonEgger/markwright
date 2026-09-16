# Renderer Requirements

The `mw pre` and `mw post` stages coordinate through markers that survive a normal Markdown render, not through any knowledge of the renderer.
For that round-trip to work, the renderer you place between the two stages has to meet three requirements.
Each requirement maps to a feature, and a renderer that does not meet one disables that feature while leaving the rest working.

## The Three Requirements

### 1. Raw HTML Passthrough

The pre stage expands embed directives into raw HTML and, with highlight active, wraps prose markers in `<mark>`.
A renderer that strips raw HTML by default has to enable its passthrough option (`--unsafe` for cmark, `unsafe = true` for Hugo's Goldmark, and the equivalent elsewhere).
Without passthrough, the expanded embeds and pre-stage highlights are dropped by the renderer before the post stage ever sees them.

### 2. Comment Preservation

The pre stage encodes fence directives as an `<!-- mw-fence:{JSON} -->` comment placed immediately before the fence.
The post stage reads that comment to style the adjacent code block.
A renderer that preserves HTML comments lets fence styling round-trip.
A renderer that drops comments disables fence styling and breaks nothing else: the code block still renders, just without its label, environment tint, or line prefixes.

### 3. Span-Based Syntax Highlighting

In-code highlighting (`\<^>...\<^>` inside a fence) depends on the renderer wrapping syntax-highlighted tokens in tags, so the post stage can place `<mark>` without crossing a token boundary.
Any Pygments- or Chroma-style highlighter qualifies.
A renderer that emits plain, untagged code text still highlights, but the `<mark>` placement has fewer token boundaries to respect.

## The `mw-fence` Marker Contract

The fence directives travel from `pre` to `post` as a single HTML comment immediately before the fence:

```
<!-- mw-fence:{"version": 1, "label": "deploy.sh"} -->
```

The fence itself is left intact, so your renderer still syntax-highlights the real code.
There is no placeholder and no rewritten language token.
The post stage associates a marker with the code block that immediately follows it.
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
A malformed payload (invalid JSON, or a missing or wrongly typed required field) is skipped, never executed, and reported under `--warn`.

## What Degrades, and How

The post stage degrades gracefully.
If a marker or signature is absent, the matching feature is a no-op rather than an error.

| Unmet Requirement | Feature That Stops | Behavior |
|-------------------|--------------------|----------|
| Raw HTML passthrough | Embeds, pre-stage prose highlight | The renderer drops the expanded HTML before post runs |
| Comment preservation | Fence labels, environments, prefixes | Code blocks render unstyled; the skip is silent |
| Span-based highlighting | In-code highlight | Markers still wrap, with fewer token boundaries to respect |

The comment-stripping case is special.
Once a renderer drops the `mw-fence` comment, the post stage has no evidence the directive ever existed, so a stripped marker is silently absent rather than a detectable skip.
That is why `--warn` cannot report it: a post-only filter sees nothing to warn about.
Embed script injection is unaffected, since it keys on the embed class signature in the HTML, not on any comment.
