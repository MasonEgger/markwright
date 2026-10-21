# markwright

markwright is a set of [Python-Markdown](https://python-markdown.github.io/) extensions plus a companion CLI, `mw`, for author-friendly markdown: highlighted text, labeled code fences, and media embeds.
Use the extensions in any tool built on Python-Markdown (including [MkDocs](https://www.mkdocs.org/)), or the `mw` pipeline in toolchains that are not, like Hugo.

The author-facing syntax and HTML output are derived from DigitalOcean's [`do-markdownit`](https://github.com/digitalocean/do-markdownit) (licensed under the [Apache License 2.0](https://github.com/digitalocean/do-markdownit/blob/master/LICENSE)); markwright ports those to Python-Markdown and adds the `mw` CLI on top.
See [NOTICE](https://github.com/MasonEgger/markwright/blob/main/NOTICE) for attribution.

## Features

- **[Highlight](extensions/highlight.md)** wraps `\<^>text\<^>` in `<mark>`, and works inside inline code and fenced code blocks where `==text==` cannot reach.
- **[Fence](extensions/fence.md)** adds labels, secondary labels, environment classes, and command-line prefixes to code blocks.
- **[YouTube](extensions/youtube.md)** turns `[youtube ID]` into a responsive iframe embed.
- **[CodePen](extensions/codepen.md)** embeds a pen with theme, default-tab, and layout options.
- **[Twitter](extensions/twitter.md)** embeds a tweet with theme and alignment options.
- **[Instagram](extensions/instagram.md)** embeds a post with caption and alignment options.
- **[Slideshow](extensions/slideshow.md)** builds an image slideshow with navigation arrows.
- **[Image Compare](extensions/image-compare.md)** renders two images with a draggable before/after slider.
- **[Button](extensions/button.md)** turns `[button URL TEXT]` into a link styled as a button.
- **[Lightbox](extensions/lightbox.md)** turns `[lightbox URL ALT]` into an image link a host script can open in an overlay.
- **[Mermaid](extensions/mermaid.md)** turns a `mermaid` code fence into a `<pre class="mermaid">` block a host script draws.
- **[Icons](extensions/icons.md)** replaces `:pack-name:` shortcodes with inline SVG from directories you configure.
- **[Grid](extensions/grid.md)** classes the list after `[grid]` or `[grid cards]` for a grid or card layout.
- **[Annotate](extensions/annotate.md)** links `(N)` markers in a code block to the items of the numbered list after it.

## Installation

```bash
uv add markwright
```

Or install from a local path:

```bash
uv add --editable ../markwright
```

!!! warning "MkDocs 2.0 Compatibility"
    MkDocs 2.0 removes the plugin system and rewrites the theming architecture, breaking all existing plugins and themes including Material for MkDocs. There is no migration path. This project pins **MkDocs 1.x** (`mkdocs>=1.6,<2`).

## Usage

These extensions work with Python-Markdown directly, so you can use them in any Python program (a Flask app, a CLI tool, a static site generator, or a simple script).

````python
import markdown

md = markdown.Markdown(
    extensions=[
        "pymdownx.superfences",
        "pymdownx.highlight",
        "markwright.highlight",
        "markwright.fence",
        "markwright.youtube",
        "markwright.codepen",
        "markwright.twitter",
        "markwright.instagram",
        "markwright.slideshow",
        "markwright.image_compare",
        "markwright.button",
        "markwright.lightbox",
        "markwright.mermaid",
        "markwright.grid",
        "markwright.annotate",
    ]
)

source = """
```command
[label deploy.sh]
ssh root@server
apt update
```
"""

html = md.convert(source)
print(html)
````

You can also load only the extensions you need by listing just those in the `extensions` list.

Using MkDocs? See [Using with MkDocs](integrations/mkdocs.md) for the `mkdocs.yml` configuration.

!!! note
    The fence extension should be used alongside `pymdownx.superfences` and `pymdownx.highlight` for proper code block rendering. Without them, the fence preprocessor will still extract directives, but the code block HTML structure may differ from what the postprocessor expects.

## Using It Outside Python

If your toolchain is not built on Python-Markdown, the `mw` command-line tool runs the same extensions as pre and post filters around any renderer:

```bash
mw pre < in.md | your-renderer | mw post > out.html
```

See the [CLI Reference](cli.md) for the commands and flags, and the [Hugo integration guide](integrations/hugo.md) for a worked setup.

## Architecture

Each extension is a standalone Python-Markdown extension loaded by name (e.g., `markwright.highlight`). The extensions use these processor patterns:

1. **Fence** uses a Preprocessor (priority 40) that runs *before* `pymdownx.superfences` to extract directives. A Postprocessor (priority 25) injects labels, classes, and prefix markup into rendered HTML.

2. **Embeds** use Preprocessors (priority 20) that run *after* superfences, matching standalone `[name ...]` lines. Social embeds add a Postprocessor (priority 15) for one-time script injection.

3. **Highlight** uses an InlineProcessor (priority 175) for regular text, plus a Postprocessor (priority 25) for `<^>` markers inside code blocks where the delimiters are HTML-escaped.

4. **Button, Lightbox, and Mermaid** use Preprocessors only. Button and Lightbox (priority 20) match standalone directive lines like the embeds. Mermaid (priority 45) replaces `mermaid` fences with a raw `<pre>` before superfences sees them.

5. **Icons** uses a Preprocessor (priority 50) for the `mw pre` stage and an InlineProcessor (priority 175) in-process, both resolving `:pack-name:` shortcodes against SVG directories you configure.

6. **Grid and Annotate** follow the fence marker-comment pattern: a Preprocessor (priority 20) swaps the directive for a versioned marker comment, and a Postprocessor (priority 30) reads it from the rendered HTML.

markwright ships no CSS, JavaScript, or icons. The extensions emit classes and markup, and the host site styles them.

## License

This project is a port of [do-markdownit](https://github.com/digitalocean/do-markdownit) by DigitalOcean, which is licensed under the Apache License 2.0. See the [NOTICE](https://github.com/MasonEgger/markwright/blob/main/NOTICE) file for attribution details.
