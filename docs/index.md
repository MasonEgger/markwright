# markwright

A Python port of DigitalOcean's [`do-markdownit`](https://github.com/digitalocean/do-markdownit) JavaScript library. These are [Python-Markdown](https://python-markdown.github.io/) extensions that can be used with any tool built on Python-Markdown, including [MkDocs](https://www.mkdocs.org/).

The original `do-markdownit` is licensed under the [Apache License 2.0](https://github.com/digitalocean/do-markdownit/blob/master/LICENSE). This port maintains compatibility with the original HTML output format.

## Features

- **[Highlight](extensions/highlight.md)** wraps `<^>text<^>` in `<mark>`, and works inside inline code and fenced code blocks where `==text==` cannot reach.
- **[Fence](extensions/fence.md)** adds labels, secondary labels, environment classes, and command-line prefixes to code blocks.
- **[YouTube](extensions/youtube.md)** turns `[youtube ID]` into a responsive iframe embed.
- **[CodePen](extensions/codepen.md)** embeds a pen with theme, default-tab, and layout options.
- **[Twitter](extensions/twitter.md)** embeds a tweet with theme and alignment options.
- **[Instagram](extensions/instagram.md)** embeds a post with caption and alignment options.
- **[Slideshow](extensions/slideshow.md)** builds an image slideshow with navigation arrows.
- **[Image Compare](extensions/image-compare.md)** renders two images with a draggable before/after slider.

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

md = markdown.Markdown(extensions=[
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
])

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

Using MkDocs? See [Using with MkDocs](using-with-mkdocs.md) for the `mkdocs.yml` configuration.

!!! note
    The fence extension should be used alongside `pymdownx.superfences` and `pymdownx.highlight` for proper code block rendering. Without them, the fence preprocessor will still extract directives, but the code block HTML structure may differ from what the postprocessor expects.

## Architecture

Each extension is a standalone Python-Markdown extension loaded by name (e.g., `markwright.highlight`). The extensions use three processor patterns:

1. **Fence** uses a Preprocessor (priority 40) that runs *before* `pymdownx.superfences` to extract directives. A Postprocessor (priority 25) injects labels, classes, and prefix markup into rendered HTML.

2. **Embeds** use Preprocessors (priority 20) that run *after* superfences, matching standalone `[name ...]` lines. Social embeds add a Postprocessor (priority 15) for one-time script injection.

3. **Highlight** uses an InlineProcessor (priority 175) for regular text, plus a Postprocessor (priority 25) for `<^>` markers inside code blocks where the delimiters are HTML-escaped.

## License

This project is a port of [do-markdownit](https://github.com/digitalocean/do-markdownit) by DigitalOcean, which is licensed under the Apache License 2.0. See the [NOTICE](https://github.com/MasonEgger/markwright/blob/main/NOTICE) file for attribution details.
