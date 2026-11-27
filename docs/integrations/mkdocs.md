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
  - markwright.tabs
  - markwright.icons:
      packs:
        lucide: docs/icons/lucide
        mw: docs/icons/mw
```

`markwright.icons` needs a `packs` table that maps each shortcode prefix to a directory of SVG files; relative paths resolve against the directory you run `mkdocs` from.
`markwright.mermaid` replaces `mermaid` fences itself, so drop any `custom_fences` entry named `mermaid` from `pymdownx.superfences`.
The seven material-style extensions emit classes and markup only.
Add your own CSS under `extra_css` and scripts under `extra_javascript`; the [Lightbox](../extensions/lightbox.md), [Mermaid](../extensions/mermaid.md), and [Annotate](../extensions/annotate.md) pages link the ones this site uses.

The fence extension expects `pymdownx.superfences` and `pymdownx.highlight` to be loaded too.
Without them the fence preprocessor still extracts directives, but the code-block HTML may not match what the postprocessor rewrites.

## Failing the Build on a Diagnostic

When markwright skips or reports something in a page, such as a stray `[/tab]`, the fence, grid, tabs, and annotate extensions emit a `RenderWarning`.
MkDocs logs a Python warning at INFO, which `mkdocs build --strict` does not count.
This site ships a hook that sends each `RenderWarning` to the `mkdocs.plugins.markwright` logger at WARNING, prefixed with the page's source path, so `--strict` fails on it and the log names the page.

```yaml
hooks:
  - docs/hooks/strict_warnings.py

exclude_docs: |
  hooks/
```

`exclude_docs` keeps the hook file out of the built site.

The hook is `docs/hooks/strict_warnings.py`.
It sets the `always` filter for `RenderWarning`, so a page that repeats a problem is reported every time.
It wraps `warnings.showwarning` to log each `RenderWarning` and pass every other warning to the previous handler.
It also records the page being rendered in `on_page_markdown`, which is how the log line names the page.
Copy the file into your site and add both the `hooks:` and `exclude_docs:` keys.
It is a host example and does not ship in the package.

A host that reads `md.markwright_diagnostics` after each `convert()` needs no hook.

!!! warning "MkDocs 2.0 Compatibility"
    MkDocs 2.0 removes the plugin system and rewrites the theming architecture, breaking all existing plugins and themes including Material for MkDocs.
    There is no migration path.
    This project's dev dependency is `mkdocs>=1.6,<2`, and its lock file resolves to MkDocs 1.6.1.
