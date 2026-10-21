# Using with MkDocs

markwright is a set of Python-Markdown extensions, so it works in any Python-Markdown consumer.
This page covers the MkDocs case. Each extension page shows the plain Python-Markdown usage.

To use the extensions in a MkDocs site, add them under `markdown_extensions` in `mkdocs.yml`.
List only the ones you need.

```yaml
markdown_extensions:
  - pymdownx.superfences
  - pymdownx.highlight:
      pygments_lang_class: true
  - markwright.highlight
  - markwright.fence:
      allowed_environments:
        - local
        - second
        - third
        - fourth
        - fifth
  - markwright.youtube
  - markwright.codepen
  - markwright.twitter
  - markwright.instagram
  - markwright.slideshow
  - markwright.image_compare
  - markwright.button
  - markwright.lightbox
  - markwright.mermaid
  - markwright.grid
  - markwright.annotate
  - markwright.icons:
      packs:
        lucide: docs/icons/lucide
        mw: docs/icons/mw
```

`markwright.icons` needs a `packs` table that maps each shortcode prefix to a directory of SVG files; relative paths resolve against the directory you run `mkdocs` from.
`markwright.mermaid` replaces `mermaid` fences itself, so drop any `custom_fences` entry named `mermaid` from `pymdownx.superfences`.
The six material-style extensions emit classes and markup only.
Add your own CSS under `extra_css` and scripts under `extra_javascript`; the [Lightbox](../extensions/lightbox.md), [Mermaid](../extensions/mermaid.md), and [Annotate](../extensions/annotate.md) pages link the ones this site uses.

The fence extension expects `pymdownx.superfences` and `pymdownx.highlight` to be loaded too.
Without them the fence preprocessor still extracts directives, but the code-block HTML may not match what the postprocessor rewrites.

!!! warning "MkDocs 2.0 Compatibility"
    MkDocs 2.0 removes the plugin system and rewrites the theming architecture, breaking all existing plugins and themes including Material for MkDocs. There is no migration path. This project pins **MkDocs 1.x** (`mkdocs>=1.6,<2`).
