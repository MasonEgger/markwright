# Icons

Replaces `:pack-name:` shortcodes in prose with inline SVG read from directories you configure.

markwright ships no icons.
You name a pack (a prefix) and point it at a directory of SVG files, and the extension inlines the file whose name matches.

## Usage

```python
import markdown

md = markdown.Markdown(
    extensions=["markwright.icons"],
    extension_configs={
        "markwright.icons": {
            "packs": {
                "lucide": "docs/icons/lucide",
                "mw": "docs/icons/mw",
            },
        },
    },
)
```

See [Using with MkDocs](../integrations/mkdocs.md) to load it in a MkDocs site.

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `packs` | omitted (no packs) | A table of pack prefix to the directory holding that pack's SVG files. |

The same option works in `markwright.toml`:

```toml
[icons.packs]
lucide = "docs/icons/lucide"
mw = "docs/icons/mw"
```

Relative directories resolve against the directory you run from.
With no `packs`, the extension does nothing and shortcodes stay text.
An empty `packs` table emits a `ConfigWarning`, and a non-table value, a non-string path, or a directory that does not exist is a `ConfigError`.
See [Configuration](../config.md#config-rules).

## Syntax

```
:PACK-NAME:
```

The shortcode is the pack prefix, a hyphen, and the icon name.
`:lucide-check:` reads `check.svg` from the `lucide` pack's directory.
A file in a subdirectory joins its path parts with hyphens, so `arrows/up.svg` is the name `arrows-up`.
Prefixes are matched longest first.

A shortcode that names no pack, or a pack with no matching file, is left as text.
Shortcodes inside fenced code blocks and inline code spans are never replaced.
Anything before the `<svg` tag in the file (an XML declaration or a license comment) is dropped, and the markup is joined onto a single line.

## HTML Contract

```html
<span aria-hidden="true" class="mw-icon"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg></span>
```

The wrapper is a `span` with `class="mw-icon"` and `aria-hidden="true"`, in that serialized order, so icons are decorative to screen readers.
The SVG inside is the file's own markup, unchanged.

## Examples

```
Build passed :lucide-check:

Rated :mw-star: :mw-star: :mw-star: by readers who :mw-heart: it.

Next step :lucide-arrow-right: install, then :mw-bolt: run.
```

Build passed :lucide-check:

Rated :mw-star: :mw-star: :mw-star: by readers who :mw-heart: it.

Next step :lucide-arrow-right: install, then :mw-bolt: run.

An unknown icon stays text: `:lucide-nope:` and :lucide-nope:.

## Host CSS

markwright ships no CSS, JavaScript, or icons.
The demo packs on this site are committed under `docs/icons/`.
`lucide` holds `check`, `arrow-right`, and `info` (ISC license), and `mw` holds `star`, `heart`, and `bolt`, drawn for this repository.
Credits and license text are in [`docs/icons/CREDITS.txt`](https://github.com/MasonEgger/markwright/blob/main/docs/icons/CREDITS.txt).

Sizing and color are the host's job, and the `.mw-icon` rules in [`docs/stylesheets/extra.css`](https://github.com/MasonEgger/markwright/blob/main/docs/stylesheets/extra.css) show one way.
Icons that use `currentColor`, as both demo packs do, take the surrounding text color.
