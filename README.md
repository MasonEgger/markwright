# do-markdown

A Python port of DigitalOcean's [`do-markdownit`](https://github.com/digitalocean/do-markdownit) JavaScript library.

These are [Python-Markdown](https://python-markdown.github.io/) extensions that bring DigitalOcean's markdown syntax (highlighted text, labeled code fences, and a set of media embeds) to any tool built on Python-Markdown, including [MkDocs](https://www.mkdocs.org/), Flask, or a plain script.
The port maintains compatibility with the original `do-markdownit` HTML output, so rendered pages match what DigitalOcean produces.

Full documentation and a live demo: https://masonegger.github.io/do-markdown/

## Features

Each extension is standalone and can be loaded on its own or alongside the others.

- **Highlight** wraps `<^>text<^>` in `<mark>`, and works inside inline code and fenced code blocks where `==text==` cannot reach.
- **Fence** adds labels, secondary labels, environment classes, and command-line prefixes (line numbers, `$`/`#` prompts, custom prefixes) to code blocks.
- **YouTube** turns `[youtube ID]` into a responsive iframe embed.
- **CodePen** embeds a pen with theme, default-tab, and layout options.
- **Twitter** embeds a tweet with theme and alignment options.
- **Instagram** embeds a post with caption and alignment options.
- **Slideshow** builds an image slideshow with navigation arrows.
- **Image Compare** renders two images with a draggable before/after slider.

## Installation

```bash
uv add do-markdown
```

or

```bash
pip install do-markdown
```

To work against a local checkout, install it editable:

```bash
uv add --editable ../do-markdown
```

## Usage

### With MkDocs

Add the extensions to `mkdocs.yml`.
Load `do_markdown.fence` after `pymdownx.superfences` and `pymdownx.highlight` so the code-block HTML is in the shape the fence postprocessor expects.

```yaml
markdown_extensions:
  - pymdownx.superfences
  - pymdownx.highlight:
      pygments_lang_class: true
  - do_markdown.highlight
  - do_markdown.fence:
      allowed_environments:
        - local
        - second
        - third
  - do_markdown.youtube
  - do_markdown.codepen
  - do_markdown.twitter
  - do_markdown.instagram
  - do_markdown.slideshow
  - do_markdown.image_compare
```

### Standalone

The extensions work with Python-Markdown directly, so you can use them in any Python program.

```python
import markdown

md = markdown.Markdown(extensions=[
    "pymdownx.superfences",
    "pymdownx.highlight",
    "do_markdown.highlight",
    "do_markdown.fence",
    "do_markdown.youtube",
    "do_markdown.codepen",
    "do_markdown.twitter",
    "do_markdown.instagram",
    "do_markdown.slideshow",
    "do_markdown.image_compare",
])

html = md.convert("This has a <^>highlighted word<^> in it.")
print(html)
```

Load only what you need:

```python
import markdown

# Just YouTube embeds
md = markdown.Markdown(extensions=["do_markdown.youtube"])
html = md.convert("[youtube dQw4w9WgXcQ]")
```

The fence extension expects `pymdownx.superfences` and `pymdownx.highlight` to be loaded too.
Without them the preprocessor still extracts directives, but the code-block HTML may not match what the postprocessor rewrites.

## Syntax at a glance

````text
Highlight:       <^>important<^>

Fenced code with a label and command prompts:
    ```command
    [label deploy.sh]
    ssh root@server
    apt update
    ```

YouTube:         [youtube dQw4w9WgXcQ]
                 [youtube dQw4w9WgXcQ 360 640]
CodePen:         [codepen MattCowley vwPzeX]
                 [codepen MattCowley vwPzeX dark css]
Twitter:         [twitter https://twitter.com/github/status/1234567890]
Instagram:       [instagram https://www.instagram.com/p/CkQuv3_LRgS]
Slideshow:       [slideshow https://picsum.photos/id/10/480/270 https://picsum.photos/id/20/480/270]
Image Compare:   [image_compare before.jpg after.jpg]
````

See the [extension docs](https://masonegger.github.io/do-markdown/) for every flag and the exact HTML each one produces.

## Development

This project uses [`uv`](https://docs.astral.sh/uv/) and [`just`](https://github.com/casey/just).

```bash
just install      # uv sync
just test         # pytest with coverage
just lint         # ruff check + ruff format --check
just typecheck    # mypy --strict
just check        # test + lint + typecheck
just docs-serve   # serve the docs site at localhost:8000
```

`just check` must pass before a change is complete.
The tooling bar is strict: `mypy --strict`, a clean `ruff`, and full test coverage.

## License

do-markdown is released under the [MIT License](LICENSE).

It is a port of [`do-markdownit`](https://github.com/digitalocean/do-markdownit) by DigitalOcean, which is licensed under the Apache License 2.0.
See the [NOTICE](NOTICE) file for attribution details.
