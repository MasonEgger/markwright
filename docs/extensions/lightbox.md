# Lightbox

Turns a standalone `[lightbox ...]` line into an image wrapped in a link to the full-size file.

## Usage

```python
import markdown

md = markdown.Markdown(extensions=["markwright.lightbox"])
html = md.convert("[lightbox https://picsum.photos/id/10/480/270 A forest path]")
```

See [Using with MkDocs](../integrations/mkdocs.md) to load it in a MkDocs site.

## Syntax

```
[lightbox URL]
[lightbox URL ALT TEXT]
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `URL` | required | The image address, one word with no spaces. It is used for both the link and the image. |
| `ALT TEXT` | empty | The alt text, everything after the URL up to the closing bracket. |

The URL and the alt text are HTML-escaped.
The directive must be on its own line.

## HTML Contract

```html
<a class="mw-lightbox" href="https://picsum.photos/id/10/480/270"><img src="https://picsum.photos/id/10/480/270" alt="A forest path" /></a>
```

Without a script, the link opens the image on its own page.
With a host script, a click on `a.mw-lightbox` can open the image in an overlay instead.

## Examples

```
[lightbox https://picsum.photos/id/10/480/270 A forest path]
```

[lightbox https://picsum.photos/id/10/480/270 A forest path]

## Host CSS and Script

markwright ships no CSS, JavaScript, or icons.
This site supplies both pieces:

- [`docs/javascripts/lightbox.js`](https://github.com/MasonEgger/markwright/blob/main/docs/javascripts/lightbox.js) listens for clicks on `a.mw-lightbox`, cancels the navigation, and shows the image in a `<dialog>`.
- [`docs/stylesheets/extra.css`](https://github.com/MasonEgger/markwright/blob/main/docs/stylesheets/extra.css) sizes the thumbnail and styles the dialog and its backdrop.

Both are worked examples.
Register the script in `mkdocs.yml` under `extra_javascript`, as this site does.
