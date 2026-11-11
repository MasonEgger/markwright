# Tabs

Groups content into a tab set.
Each `[tab NAME]` paired with `[/tab]` is one tab, and consecutive tabs join one set with the first tab selected.

[tab Python]

Call the extensions in-process with Python-Markdown, the same way the other extensions load.

[/tab]

[tab CLI]

Run the same stages as a shell filter with `mw pre` and `mw post`, so the syntax works around any renderer.

[/tab]

````
[label Markdown]
[tab Python]

Call the extensions in-process with Python-Markdown, the same way the other extensions load.

[/tab]

[tab CLI]

Run the same stages as a shell filter with `mw pre` and `mw post`, so the syntax works around any renderer.

[/tab]
````

The directive lines are inside the source fence above, so the pre stage leaves them literal and the fence renders the source as written.

## Usage

```python
import markdown

md = markdown.Markdown(extensions=["markwright.tabs"])
```

See [Using with MkDocs](../integrations/mkdocs.md) to load it in a MkDocs site.
Tabs reuses pymdown-extensions' `tabbed` classes, so a host theme that already styles tab sets styles these too, with no extra configuration and no dependency on `pymdownx.tabbed`.

## Syntax

Put each tab between a `[tab NAME]` opener and a `[/tab]` closer, each alone on its line:

````
[label Markdown]
[tab First]

Any Markdown goes here.

[/tab]

[tab Second]

So does the content of the next tab.

[/tab]
````

- NAME is the rest of the opener line, trimmed.
  It is non-empty, holds no `]`, and may hold spaces, so `[tab Node.js 20]` is one tab named `Node.js 20`.
- The name renders as escaped plain text; inline Markdown in it is not rendered.
- Tabs separated only by blank lines group into one set.
- Any other content between two tabs starts a new set, and the first tab in each set is selected.

## How It Works

Tabs is a two-stage extension.
The source stage (`mw pre`) replaces each tab with an open and a close marker comment:

```html
<!-- mw-tab:{"version": 1, "name": "Python", "first": true} -->
<!-- mw-tab-end:{"version": 1} -->
```

The `first` field is true for the tab that starts a set.
The HTML stage (`mw post`) orders the markers by position, matches them like brackets, groups the tabs into sets at each `first` marker, and wraps each set in the tabbed markup.
Every marker comment is removed.

## HTML Contract

A set renders as pymdown-extensions' `tabbed` `alternate_style` markup:

```html
<div class="tabbed-set tabbed-alternate mw-tabs" data-tabs="1:2">
<input checked="checked" type="radio" id="mw-tab-1-1" name="mw-tab-1" />
<input type="radio" id="mw-tab-1-2" name="mw-tab-1" />
<div class="tabbed-labels">
<label for="mw-tab-1-1">Python</label>
<label for="mw-tab-1-2">CLI</label>
</div>
<div class="tabbed-content">
<div class="tabbed-block">
<p>The first tab's body.</p>
</div>
<div class="tabbed-block">
<p>The second tab's body.</p>
</div>
</div>
</div>
```

One radio `<input>` per tab shares the set's `name="mw-tab-S"`, so checking one unchecks the rest, and the first is `checked`.
S counts sets and T counts tabs within a set, both from 1 per document, so the ids run `mw-tab-S-T`.
The `mw-tab-` prefix keeps the ids from colliding with pymdown-extensions' own `__tabbed_` ids when a host loads both.
`data-tabs="S:N"` records the set number and its tab count.

## Marker Contracts

Each marker is a versioned public contract, read fail-soft.

| Marker | Payload | Role |
|--------|---------|------|
| `mw-tab` / `mw-tab-end` | `version`, `name`, `first` on the opener | Wrap one tab, grouped into sets at each `first`. |
| `mw-tab-problem` | `version`, `line`, `directive`, `reason` | Mark a tab left literal so `mw post --warn` reports it. |

A payload bumps its version with no migration shim when a field changes, since the project is pre-1.0 with one host.

## Fail-Soft and Warnings

A tab the extension cannot pair stays literal and is reported by `mw post --warn`, never raised:

- an unclosed `[tab NAME]`;
- a stray `[/tab]`.

The pre stage attaches an inline `mw-tab-problem` marker to each literal directive, and the post stage composes one `--warn` line from the marker and removes the comment.
An empty `[tab ]` with no name is not an opener and stays literal with no report.
An opener or closer inside fenced or indented code also stays literal.

## Host CSS

markwright ships no CSS.
The `tabbed-set`, `tabbed-alternate`, `mw-tabs`, `tabbed-labels`, `tabbed-content`, and `tabbed-block` classes are the public contract, inert until the host styles them.
This site's sample in [`docs/stylesheets/extra.css`](https://github.com/MasonEgger/markwright/blob/main/docs/stylesheets/extra.css) ties each radio's `:checked` state to the block at its position, so the demo above switches tabs with no JavaScript.
The sample's `:nth-child` chains stop at six tabs, so a set's seventh tab and beyond would not switch under it; a host that needs more extends those chains, and a host with JavaScript or an existing `.tabbed-set` style has no such ceiling.
