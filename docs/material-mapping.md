# Material Mapping

This page answers one question: you use a feature from the Material for MkDocs reference, and you want to know what provides it in-process and what provides it under Hugo.
In-process means Python-Markdown, with or without MkDocs.
Under Hugo means Goldmark and Chroma, with markwright's `mw pre` and `mw post` filters around the build (see the [Hugo guide](integrations/hugo.md)).

The in-process column follows this site's `mkdocs.yml`.
The Hugo column was checked with a pipeline build on a small Hugo site using the settings from the Hugo guide.
Where a cell says "no equivalent", markwright and Hugo give you nothing for that feature, and the gap is yours to fill.
markwright emits classes and markup only and ships no CSS, JavaScript, or icons, so a row that needs styling or a script depends on your host; this site's `docs/` folder is the worked example.

## Reference Features

| Material feature | In-process | Under Hugo | Gap |
|------------------|------------|------------|-----|
| Admonitions, collapsible blocks | `admonition` and `pymdownx.details` (Python-Markdown and pymdown-extensions) | no equivalent | markwright has no admonition stage. A `> [!NOTE]` blockquote rendered as a plain blockquote with no render hook, and `!!! note` rendered as a paragraph. |
| Content tabs | [Tabs](extensions/tabs.md), or `pymdownx.tabbed` | [Tabs](extensions/tabs.md) through `mw pre` and `mw post` | The syntax is markwright's `[tab NAME]` ... `[/tab]`; `pymdownx.tabbed` takes `=== "Name"` in-process only. |
| Grids and cards | [Grid](extensions/grid.md) | [Grid](extensions/grid.md) through `mw pre` and `mw post` | The syntax is markwright's `[grid]` and `[card]`. Styling is yours. |
| Annotations | [Annotate](extensions/annotate.md) | [Annotate](extensions/annotate.md) through `mw pre` and `mw post` | The markup is a link per `(N)` marker and a numbered list; any popup is host CSS and JavaScript. The `(N)!` form needs `noClasses = false` under Hugo. |
| Code highlighting | `pymdownx.highlight` with `pymdownx.superfences` | Chroma, set with `noClasses = false` for classes | none |
| Code line numbers | `linenums="1"` on a fence, through `pymdownx.highlight` | `linenos=true` on a fence, native to Hugo | The attribute names differ between the two. |
| Code line highlighting | `hl_lines="2"` on a fence | `hl_lines=[2]` on a fence, native to Hugo | The attribute syntax differs. |
| Code block titles and labels | `title="x.py"` on a fence, through `pymdownx.highlight` | [Fence](extensions/fence.md) `[label x.py]` through `mw pre` and `mw post` | Hugo's own `title` attribute landed on the wrapping `div` with no visible label, so use the fence label. |
| Icons | [Icons](extensions/icons.md), or `pymdownx.emoji` | [Icons](extensions/icons.md) through `mw pre` | markwright ships no icons: you point each pack prefix at a directory of SVG files. |
| Buttons | [Button](extensions/button.md) | [Button](extensions/button.md) through `mw pre` | The syntax is `[button URL TEXT]`. Styling is yours. |
| Diagrams | [Mermaid](extensions/mermaid.md) | [Mermaid](extensions/mermaid.md) through `mw pre` | Documented for a top-level fence only. A fence in a list item or inside another block is listed as unsupported on the Mermaid page. The page needs the Mermaid script. |

## Features Material Does Not Have

These come from markwright and have no entry in the Material reference.
Each works in both paths.

| Feature | What it does |
|---------|--------------|
| [Highlight](extensions/highlight.md) | `\<^>text\<^>` becomes `<mark>`, including inside code. |
| [Fence](extensions/fence.md) | Labels, environment classes, and command-line prefixes on code blocks. |
| [YouTube](extensions/youtube.md), [CodePen](extensions/codepen.md), [Twitter](extensions/twitter.md), [Instagram](extensions/instagram.md) | Embeds from a one-line directive, with an optional [click-to-load](click-to-load.md) mode. |
| [Slideshow](extensions/slideshow.md), [Image Compare](extensions/image-compare.md) | An image slideshow and a before/after slider. |
| [Lightbox](extensions/lightbox.md) | An image link that a host script can open in an overlay. |
