# markwright

## Starting context

Recorded at the pre-0.7 spec migration on 2026-10-11, not at project start.
markwright is a maintained library and 0.3.0 is shipping.
Mason authors it and knows the codebase deeply.
Future work is issue-driven, not a planned phase.

## Project overview

markwright is a set of [Python-Markdown](https://python-markdown.github.io/) extensions plus an `mw` command-line tool that runs the same extensions as pre and post filter stages so the author-facing syntax works in any toolchain (Hugo, a plain Unix pipe), not only an in-process Python-Markdown render.
Part of it is a port: the eight original extensions reproduce the syntax and HTML output of DigitalOcean's [`do-markdownit`](https://github.com/digitalocean/do-markdownit) (JavaScript/markdown-it, Apache 2.0), so those render the way DigitalOcean's do.
Everything else is markwright's own, most notably the CLI, a config surface with a public API host tools build on, click-to-load embeds, and the 0.4.0 and later extensions modeled on the mkdocs-material reference.
The bundled MkDocs Material site in `docs/` is both documentation and a live demo.
It moves to Bartleby (Mason's static site generator and markwright's first host) once Bartleby reaches parity and releases, well ahead of Material for MkDocs' end of life on May 5, 2027.

markwright is pre-1.0 and has one user, so its cross-tool contracts are versioned and read fail-soft but carry no compatibility obligation until 1.0: a contract change bumps its version and ships with no shim.
It grows through issues.
Its scope rule: markwright owns syntax that no maintained Python-Markdown or pymdown-extensions extension provides, plus block-level features the `mw` pipeline needs because Hugo has no equivalent (tabs is the one such feature so far).
Material for MkDocs is in maintenance until its end of life, so its reference pages are a frozen snapshot to compare against, not a target to track; Python-Markdown and pymdown-extensions are the maintained line.
markwright emits markup only; hosts (Bartleby's themes, or anyone's) own the JavaScript and CSS, and markwright's docs carry small working samples of both.
Likely future directions are tracked under Roadmap Deferred.

## Invariants

- Python: per the `python:python` skill and the Code Conventions in CLAUDE.md
- Docs prose: per the `content-design` skill and the writing rules in CLAUDE.md
- Stack: a pure-Python package on Python 3.11 through 3.15, built with `hatchling`, managed with `uv`; `just check` (ruff, ruff format, mypy strict, pytest) is the gate and runs after every change
- Runtime dependencies are `markdown`, `pymdown-extensions` (floor `>=11.0.1`, set by a security fix), and `pydantic`; the 0.4.0 release raises the `markdown` floor from `>=3.4` to `>=3.8.2`, the first version that passes the suite; adding another needs a spec change
- deps: frozen
- paths: src/markwright/**, tests/**, docs/**, mkdocs.yml, README.md, CHANGELOG.md, CLAUDE.md, spec.md, plan.md, todo.md, .ai-sessions/**
- Coverage is reported (line and branch) but not gated; read it and either test or delete what it shows uncovered
- Output stays at `do-markdownit` parity (the eight ported extensions) unless a Decision documents a divergence; the cross-tool contracts are versioned and read fail-soft: the `mw-fence`, `mw-grid`, `mw-grid-block`, `mw-grid-end`, `mw-card`, `mw-card-end`, `mw-grid-problem`, `mw-tab`, `mw-tab-end`, `mw-tab-problem`, and `mw-annotate` marker-comment payloads, the `mw-embed` preview, the `mw-annotations` list's `data-mw-version`, the grid and card classes, and the tab markup with its `mw-tab-S-T` ids; before 1.0 a contract change bumps its version with no compatibility shim
- The package ships no JavaScript, no CSS, and no bundled assets, icons included: markwright owns markup and inlines host-supplied SVGs; hosts own behavior, styling, and the icon files
- Progressive enhancement: every extension's markup is readable with no host CSS and no host JavaScript, and host code only enhances it (annotations fall back to a numbered list, click-to-load embeds to a direct link, tabs switch with CSS alone)
- New block-level author syntax is a standalone `[name ...]` line, either a directive or a container's opener or closer; the inline forms are highlight's `<^>` pair, the icon shortcode `:PACK-NAME:`, and the `(N)` and `(N)!` markers inside an annotated block, and `mermaid` claims a fence language; markwright adds no inline delimiter pairs (`$`, `~`, `^`, `==`, `++`, and the like belong to pymdown-extensions)
- markwright's own extensions emit classes, data attributes, and ids, never inline `style` attributes or inline event handlers; the ported embeds keep the inline `style` and handlers `do-markdownit` emits, for parity
- Container pairing scans lines through `_fences`, so an opener or closer inside fenced or indented code stays literal; no Markdown parser is added
- Config law (see `docs/config.md`, Config Rules): omitting a key means its default, a list names exactly what it holds (empty allowlist allows nothing, empty denylist removes nothing), a setting that makes a feature a no-op is legal but emits a `ConfigWarning`, and every option is validated at the boundary with a `ConfigError`, never a traceback
- Library code raises; only the `mw` CLI boundary turns exceptions into exit codes
- `__init__.py` re-exports only the public API with `__all__`
- The `do-markdownit` name is preserved in attribution (NOTICE, README); the package and CLI use the `markwright` / `mw` brand
- Never commit to `main`; branch, open a PR, squash-merge, and only Mason merges

## Available tooling

Tools the `bpe:validator` agent should consult when reviewing diffs in `/bpe:goal` runs. `/bpe:plan` propagates these to per-section declarations in plan.md.

**MCPs:**
- none

**Skills:**
- python:python
- content-design:review-content

**Notes:** Validator should apply the `python:python` taste profile to code under `src/markwright/` and `tests/`, and the `content-design` review to prose under `docs/`, the README, and the CHANGELOG. The repo's own gate (`just check`) owns correctness, coverage, lint, and types, so the validator focuses on taste and convention rather than re-running tests.

## Roadmap / phase log

**Shipped:**
- v1-init: the initial `do-markdownit` port (the eight extensions) and the `mw` pipeline CLI (.ai-sessions/v1-init/)
- v0.1-remediation: the step-55 audit remediation (R1 through R11), shipped as 0.1.0 (.ai-sessions/v0.1-remediation/)
- config-system: the 0.2.0 config system and `mw` CLI simplification, converged (.ai-sessions/config-system/)
- material-parity-0.4.0: the six Material-reference extensions (#16) and the shared `_markers` module, converged and staged for the 0.4.0 release (.ai-sessions/material-parity-0.4.0/)
- fenced-directives-20: `mw pre` leaves a directive line inside fenced code literal across all ten directive stages through `_fences.map_lines` (#20), converged (.ai-sessions/fenced-directives-20/)
- review-fixes-29: the eight 0.4.0 adversarial-review fixes (annotate chaining, tab and indented-code detection, HTML-tag skipping, icons at priority 85, and the test-policy cleanup) (#29), converged (.ai-sessions/review-fixes-29/)
- containers-30: block grids, cards, column counts, and the `tabs` extension on one shared open/close pairing scanner (#30), converged (.ai-sessions/containers-30/)

**Upcoming:**
- container postprocessor priority (no issue): the grid, annotate, and tabs postprocessors move from 30 to 27, below Python-Markdown's `raw_html` and above fence, so the stashed markers are restored first whatever order a host lists its extensions in; today a host that lists `md_in_html` after markwright gets no tab set and no grid, and the marker comments stay in the page; first in the plan, since it is the smallest change and Bartleby's extension order hits it
- containers fixes (#30): an invalid `[grid ...]` is not an opener; indentation pairs by column, and a less-indented line ends a container's block; a card needs a paired grid; tabs group by a sibling rule, number their sets in opening order, and render a backticked name as text in both paths; closer markers are validated; the shortcut and annotate markers are emitted as blocks, and a problem marker keeps a CRLF line end; the backslash escape for a literal directive line is documented and tested; and the sample CSS covers a list inside a `cards` block grid; written as `Planned (containers fixes)` sentences under Goals in Containers, Grid and Cards, and Tabs
- block bodies (no issue): a directive line, a fence with its directives, and a `mermaid` fence work inside the body of an admonition, a details block, a content tab, a definition, or a footnote, in both paths; `_fences` reads those four-column bodies as content, so an embed that 0.3.0 expanded there expands again
- pre-stage order (no issue): in `mw pre` the icons stage runs after the directive stages, and a `mermaid` fence in a list item renders as one block; the two land together, since icons after mermaid would otherwise rewrite a shortcode inside a diagram
- highlight same-line pairing (#34): a prose pair never holds a line end, in either path; the in-process path stops pairing across a soft line break, which departs from `do-markdownit`, and `mw pre` wraps a same-line pair in one `<mark>`, code spans included; decided on 2026-11-16, after the plan review found that no paragraph-end test brings the two renderers together
- annotate overlap (no issue): a comment that holds a plain marker and a `!` marker is replaced by the links for every marker in it, and `_html.apply_edits` refuses overlapping spans; today that comment renders as broken HTML in both paths
- config `warn` default (#33): `mw post` ignores `warn = true`; make it the default for the diagnostics, as `docs/config.md` says, and add `--no-warn` so the command line can still turn them off
- public fence API (#32): `disallowed_environments(source, config)`, a public function that reports a document's disallowed fence environments, so Bartleby stops importing `markwright._fences` and fence's regexes; the same item makes `config_from_mapping` raise `ConfigError` for a table that is not a mapping and check key names before it drops `None` values
- hardening (no issue): no input a pipeline plausibly sends ends in a traceback (unreadable or non-UTF-8 files, closed streams); `mw` reads and writes UTF-8 whatever the locale; the label class options are validated as class tokens; a Chroma prefixed line gains no second newline; highlight skips `<title>` and `<textarea>`; a replaced prefix flag leaves no `prefix_value`; and `mw pre` passes a leading front matter block through untouched; written as `Planned (hardening)` sentences across Goals
- docs catch-up (no issue): the docs gaps and the CHANGELOG corrections listed under Goals, Docs Site; docs-only, done after the code items so the CHANGELOG's Fixed list is final
- 0.4.0 release: done by hand, outside the bpe loop, since `pyproject.toml`, `uv.lock`, and the workflows are outside `paths:`; it closes #16, #20, #29, and #30 and turns the Unreleased rows of Goals, Feature Status into Released 0.4.0
  - draft PR #35 of `containers-30` into `main` is open, so CI runs on every push; mark it ready for review when the plan items and the docs catch-up have landed
  - at the release: the version bump in `pyproject.toml` and `uv.lock`, the `markdown` floor raised to `>=3.8.2`, the MkDocs bound settled (`<2` in `pyproject.toml`, or the sentence dropped from the two docs pages that state it), the CHANGELOG date and `[0.4.0]` compare link, and a check by hand that the tag equals the version, which the publish workflow does not make
  - right after the merge: publish the GitHub Release, which is what triggers the PyPI publish; the docs deploy on the merge, so until the Release the live docs describe fifteen extensions and PyPI delivers eight
  - same day: the Bartleby follow-up, since `selected_extensions` with no `enable` list goes from eight names to fifteen and Bartleby pins the eight in a test, and its private imports wait on the public fence API
- Material mapping docs page: maps each mkdocs-material reference feature to the Python-Markdown or pymdown-extensions extension that provides it in-process and the Goldmark setting that provides it in Hugo, with the gaps; docs-only, done directly

**Deferred:**
- New embeds (Bluesky, Mastodon, Vimeo): possible later; each should support the `load` option when it lands
- User-level config layer (`~/.config/markwright/`): project-level config only for now
- `youtube-nocookie` option: reduces tracking even for `eager`; worth a separate issue
- `mw-` rename of the existing embed CSS classes: align them with the `mw-embed` preview hooks; nothing blocks it before 1.0, but it is a separate concern from the containers phase
- Richer Material-parity features past the 0.4.0 contracts: lightbox galleries, captions, and `srcset`; annotation forms beyond a block plus its following list; each 0.4.0 extension stays minimal, revisit per issue
- `mw pre` parity inside Markdown constructs it cannot see without a parser: a highlight marker or icon shortcode inside an image's alt text, a link title, a link destination, a link reference definition, or the text content of a raw HTML block is rewritten by `mw pre` (a block that opens with exactly the mermaid stage's `<pre class="mermaid">` tag is the one exception: the icons stage leaves it literal), which leaves markup inside an attribute or breaks the link, while in-process a marker in alt text, a title, or a destination is consumed and every other case stays literal; a directive line inside a raw HTML block or a `<pre>` block is expanded by `mw pre`, and in-process too when it is a `[grid]`, `[card]`, or `[tab]` container line (those preprocessors run ahead of `html_block`), while any other directive line there is left literal in-process; the icons pre stage skips HTML tags, comments, and autolinks (the single-line grammar), and the highlight pre stage does not, so a pair inside an autolink or a tag's attribute breaks the link or the tag; the code `_fences` does not see is listed under Rules Every Feature Follows; the rest needs a block-level scanner or a Decision that the CLI's behavior is the reference, revisit per issue
- Grid extras: card column spans (`[card 2]`), per-breakpoint column counts (`[grid 1 2 3]`), and config defaults for columns, gap, or minimum width; revisit per issue
- Tab extras: a marker that selects a tab other than the first, and one that forces a new set right after another; revisit when a page needs either
- Move the docs site to Bartleby: once Bartleby reaches parity and releases, before May 5, 2027; the docs keep loading markwright's own CSS and JavaScript samples through Bartleby's `extra_css` and `extra_js`, so the samples stay exercised
- Full `mw pre` idempotence for a document with container problems: a line that already carries a problem marker is not read as a directive on a second pass, so a `[card]` outside a grid leaves its `[/card]` to gain a stray-closer report, and a `[grid]` left literal by a stray `[/grid]` is read as the list shortcut; a valid document is unaffected, revisit if a pipeline runs `mw pre` twice
- pymdown-extensions 13.x: checked on 2026-11-16 by the plan review (markwright's suite passes on 13.0 and 13.1 with `mw render` byte-identical to 12.2, and Bartleby's suite gives the same result on 13.1 as on 12.2); re-check when a release past 13.1 appears
- In-process diagnostics: a way for `mw render`, MkDocs, and a host that renders through Python-Markdown to collect what `mw post --warn` reports; today only the pipeline reports, and the public fence API gives a host the disallowed environment names; revisit when a host asks for the rest
- Problem report line numbers: a line map through `run_pre`, so a report names the source line even when an earlier stage added lines above it; the report already names the directive and the reason
- Fence marker binding: bind an `mw-fence` marker only to a `<pre>` that follows it with nothing but whitespace between; every case that differs needs a fence the renderer failed to render, unchanged since 0.1.0
- `[button]` argument checks: a style word followed by one token reads the style word as the URL; it needs an author mistake and is visibly wrong on the page
- Pre-stage scan cost: the fence and indented-code scan runs once per stage and is quadratic for a document of unclosed fence openers, and two directive regexes backtrack on a line of thousands of spaces; ordinary documents scale linearly (about 0.06 s for the 24 pages under `docs/` on the development machine, measured by timing `run_pre` over each page, with the result of a scan remembered per document so stages that leave the text unchanged share it); a stage that rewrites the text still makes the next stage scan it again, and one scan per `run_pre` shared by every stage is the fix, and a host that renders untrusted Markdown should know before 1.0
- Parser hygiene (cut from the 0.4.0 plan on 2026-11-20): no abbreviated long options, the missing-subcommand usage on stderr, `--config ""` as an error, and the source named in every no-op warning; none changes a correct invocation, and the two `Known gap` sentences under Goals say what happens today
- Hardening for input no author types (cut from the 0.4.0 plan on 2026-11-20): one integer helper for directive and annotation integers, and `decode_marker` skipping a payload no JSON reader accepts; each needs a digit string past 4,300 characters, a non-ASCII digit, or a marker comment edited by hand, and the `Known gap` sentences under Goals say what happens today; revisit if a host renders untrusted Markdown
- Multi-line HTML comment region (cut from the 0.4.0 plan on 2026-11-20): `_fences` reading a block from `<!--` to `-->` as a region its callers skip, so a commented-out directive stays commented out; the `Known gap` sentence under Rules Every Feature Follows says what happens today; revisit per issue
- Release pipeline hygiene: actions pinned by SHA, protection rules on the `pypi` environment and on `main`, a tag-equals-version check in the publish workflow, and the `Typing :: Typed` classifier; none changes what installs or runs

## Goals

Goals describes markwright as it behaves today, one entry per feature, and is the first place to look for what exists.
A sentence that starts `Planned (ITEM):` is behavior the named Roadmap Upcoming item will build; it is not built yet, and it loses the prefix when the item ships.
A sentence that starts `Known gap:` is a place where the code or the docs fall short of the entry, with the Upcoming item or issue that covers it.
A sentence that starts `Today` sits under a Planned sentence and says what the code does until the item ships.
A sentence that starts `Decision (DATE):` records a choice that departs from an earlier rule or from `do-markdownit`.
A phase edits the entry of the feature it changes; it never adds a section named for a release or an issue.
An entry holds the syntax, the output contract, the options, and the rules that were decisions.
The docs page it names carries the examples and the full reference, and the module carries the implementation.
Planned work is listed under Roadmap Upcoming, and work set aside is under Roadmap Deferred.
The byte-level contracts and decision records stay in the archives: the HTML Output Contracts of the eight ported extensions in `.ai-sessions/v1-init/plan.md`, the `mw-fence` marker and parity decisions D1 through D3 in `.ai-sessions/v0.1-remediation/spec.md`, the config design in `.ai-sessions/config-system/spec.md`, and the button, lightbox, mermaid, icons, grid, and annotate contracts with decisions D1 through D7 in `.ai-sessions/material-parity/spec.md`.
The later cycles keep their records in their archives' `plan.md` and `accomplishment.md`: containers in `.ai-sessions/containers-30/`, directives inside fenced code in `.ai-sessions/fenced-directives-20/`, and the 0.4.0 review fixes in `.ai-sessions/review-fixes-29/`.
Click-to-load and the host API were issue-driven (#11 and #13) and have no archive; their contracts are `docs/click-to-load.md` and `docs/config.md`.

### Feature Status

`Released` means in a tagged release on `main`.
`Unreleased` means built and passing `just check`, not yet in a tagged release.
Open Work names the Roadmap Upcoming item or issue that still changes the feature.
Docs paths are under `docs/` and code paths under `src/markwright/`.

| Feature | Origin | State | Open Work | Docs | Code |
|---------|--------|-------|-----------|------|------|
| highlight | ported | Released 0.1.0 | same-line pairing (#34), hardening | `extensions/highlight.md` | `highlight.py` |
| fence | ported | Released 0.1.0 | public fence API (#32), hardening | `extensions/fence.md` | `fence.py` |
| youtube | ported | Released 0.1.0 | none | `extensions/youtube.md` | `youtube.py` |
| codepen | ported | Released 0.1.0 | none | `extensions/codepen.md` | `codepen.py` |
| twitter | ported | Released 0.1.0 | none | `extensions/twitter.md` | `twitter.py` |
| instagram | ported | Released 0.1.0 | none | `extensions/instagram.md` | `instagram.py` |
| slideshow | ported | Released 0.1.0 | none | `extensions/slideshow.md` | `slideshow.py` |
| image_compare | ported | Released 0.1.0 | none | `extensions/image-compare.md` | `image_compare.py` |
| `mw` CLI | own | Released 0.1.0 | `warn` default (#33), hardening | `cli.md`, `pipeline.md`, `renderer-requirements.md` | `cli.py`, `registry.py` |
| config | own | Released 0.2.0 | hardening | `config.md` | `config.py` |
| host API | own | Released 0.3.0 | public fence API (#32) | `config.md` | `config.py`, `__init__.py` |
| click-to-load | own | Released 0.3.0 | none | `click-to-load.md` | `_embed_load.py` |
| button | own | Unreleased | none | `extensions/button.md` | `button.py` |
| lightbox | own | Unreleased | none | `extensions/lightbox.md` | `lightbox.py` |
| mermaid | own | Unreleased | none | `extensions/mermaid.md` | `mermaid.py` |
| icons | own | Unreleased | hardening | `extensions/icons.md` | `icons.py` |
| annotate | own | Unreleased | annotate overlap | `extensions/annotate.md` | `annotate.py` |
| grid and cards | own | Unreleased | none | `extensions/grid.md` | `grid.py`, `_containers.py` |
| tabs | own | Unreleased | none | `extensions/tabs.md` | `tabs.py`, `_containers.py` |

### Rules Every Feature Follows

- Every extension is on by default.
  A new extension is additive: it claims only its own syntax, so a document that contains none of it renders as before.
  A document that happens to contain the new syntax renders differently, and the CHANGELOG's upgrade notes name each case.
- A directive is a whole line: `[name ...]` alone on its line.
  The same text inside a sentence, or a line with fewer tokens than its required arguments, stays literal with no report; a `[button]` line whose style word is followed by one token reads the style word as the URL.
- Code is not prose.
  A directive line or an icon shortcode inside a fenced code block or a top-level indented code block stays literal, found through `_fences`.
  Highlight is the deliberate exception: its markers work inside code, through its post stage.
  The body of an admonition (`!!!`), a details block (`???`, `???+`), a content tab (`===`), a definition (`:`), or a footnote definition (`[^name]:`) is not indented code: `_fences` reads the lines indented four columns under such an opener as that block's content, the way it reads a list item's, so a directive line, a fence with its directives, and a `mermaid` fence inside the body work, and a line indented four columns further after a blank line is still code.
  The rule lives in `_fences`, so both paths apply it, and an expanded line keeps its indentation, so the result stays inside the block; `tests/test_roundtrip.py` covers each of the five bodies with `admonition`, `def_list`, `footnotes`, `pymdownx.details`, and `pymdownx.tabbed` loaded in both paths.
  The openers follow the grammars of Python-Markdown's `admonition` and `footnotes` and of `pymdownx.details` and `pymdownx.tabbed`: `!!! note`, `!!!note`, `??? note`, `???+ "Title"`, `=== "Tab"`, `===+ "Tab"`, `===! "Tab"`, and `[^name]:` open a body, while `=== Tab` (no quotes), `!!! "Title"` (no class), and `!!! note: text` do not.
  An admonition, details, or content-tab opener counts only at the column of the block that holds it (column 0 at the top level, an item's content column under a list item, which is four columns for an item indented 0 to 3 columns, and another opener's body column inside an opener's body), as in Python-Markdown; a footnote definition counts at the top level, up to three columns in, and a definition counts up to three columns in at the top level or inside an opener's body, not inside a list item.
  The body starts at the holding block's column plus four, and a line four columns further after a blank line is code.
  Known gap (body after an ended block): a footnote or definition indented one to three columns after a list item and a blank line (`- item`, a blank line, ` [^9]: fn`, a blank line, a five-column line) is a top-level footnote or definition to Python-Markdown, since the list ends, but `_fences` reads its body as code, so a directive in that body stays literal; in the same way a line one to three columns past a nested opener's body column (`!!! note`, a four-column `!!! tip`, a blank line, a six-column line) is content of the outer opener to Python-Markdown and code to `_fences`; both paths agree, because both read through `_fences`.
  A definition (`: text`) needs a line before it, since extra `def_list` reads a leading colon line as a paragraph; markwright does not check that the preceding line is a term, and it does not read `md_in_html` or `attr_list` blocks.
  A directive's expansion starts every line at the directive line's indentation, which keeps it in the body in-process; a directive at column 0 expands byte-identically.
  Known gap (block-level HTML nested four columns deep, `mw pre` path): the `mw pre` output keeps the expansion indented, but Python-Markdown wraps raw HTML nested in a body, a list item, a nested list, or a card in `<p>` (`md_in_html` does not change this), so the embeds that emit a `<div>`, `<iframe>`, or `<pre>` render as a `<p>`-wrapped block through a Python-Markdown stub while the in-process stash keeps them a block; the slideshow's `onclick` attribute holds `=>`, which Python-Markdown's inline HTML pattern cannot read, so its tag also breaks there; `tests/test_roundtrip.py` states the difference.
  Known gap (footnote body): Python-Markdown appends a footnote's back link to the body's last paragraph, so a block-level expansion that ends the body shares a paragraph with the back link, in-process and through `mw pre`.
  `mw pre` follows the opener, since a document that carries `!!!`, `???`, or `===` is written for a renderer that reads them; under a CommonMark renderer with no such extension the body is indented code, and an expanded directive there shows as code text.
  Known gap (directive in a multi-line HTML comment): `_fences` does not read a multi-line HTML comment as a region its callers skip, so `mw pre` writes a tab, grid, or annotate marker comment inside the author's comment, the marker's `-->` ends that comment, and the commented-out text is published; for a fence directive the in-process path does the same.
  Known gap (code `mw pre` reads as prose): `_fences` does not see a fenced block behind a block quote marker, a fence that opens on a list marker line, indented code inside a list item, or a four-column line straight after a heading or a thematic break, and it reads inline code spans one line at a time; `mw pre` rewrites a highlight marker or an icon shortcode in any of these and the reader sees the markup as code text, and fence directives behind a block quote marker are inert in both paths.
  Known gap (line `_fences` reads as a list marker): `_fences` reads a list marker line by its own text, so a thematic break written with a space after its first `*` or `-` (`* * *`, `- - -`, `* **`) is a list marker line to it, and a line indented four or more columns under one, with or without a blank line between, is that item's content, where Python-Markdown and Hugo read a rule and then indented code.
  A directive line and a fence's directives there are expanded in both paths and `mw pre` rewrites a highlight marker, and the result lands in that code block: as escaped code text, or unescaped for an embed or a diagram stashed in-process.
  Known gap (fence on a list marker line): `_fences` reads the closing line of a fence that opens on a list marker line as an opener, so under a CommonMark renderer the directives of the next fence are inert and a directive line before that fence stays literal.
  Known gap (code only one renderer sees): an unclosed fence is code to a CommonMark renderer and prose to `_fences` and `pymdownx.superfences`; a fence whose content is indented less than its opener, a tilde fence whose info string holds a backtick, and a fence closed by a longer fence line are code to `_fences` and CommonMark and prose to superfences; in each case one path transforms text that another shows as code.
- Two paths give one result: the in-process Python-Markdown render and `mw pre | renderer | mw post` produce the same HTML for the same source apart from blank lines between blocks, and `tests/test_roundtrip.py` asserts it after dropping blank lines outside `<pre>`, a hypothesis property over markwright's grammar included.
  Where the two paths differ today, the entry says so under `Known gap`.
  Known gap (lone CR line ends): `mw pre` splits lines on `\n` only, so a file whose lines end in a lone `\r` is one line to every pre stage, while Python-Markdown reads it line by line.
- A pre stage that needs its post stage hands data over in a marker comment, `<!-- NAME:{JSON} -->`, with `"version": 1` in the payload.
  A marker is read fail-soft: malformed JSON, a non-object payload, an unsupported version, a wrongly typed field, or no `<pre>` or `<code>` element before the next marker is skipped and reported under `--warn`, and unknown fields are ignored.
  Known gap (marker payload no JSON reader accepts): a number too long to convert, nesting too deep to decode, or a string that holds a lone surrogate ends `mw post` in a traceback; `mw pre` writes no such payload, so it takes a marker comment edited by hand.
- markwright emits markup only.
  The markwright-own extensions exist so a host theme can render every feature on the mkdocs-material reference from markwright markup alone; that is the scope test for another one.
  Each extension's docs page has a Host CSS and Script section listing the classes, data attributes, and ids a host styles, and a page whose extension needs neither says so.

### Highlight

- `<^>text<^>` becomes `<mark>text</mark>` in prose, in inline code, and in fenced code, the places `pymdownx.mark` cannot reach.
- In code, inline or fenced, a marker pairs with the next marker on the same line, a line can hold several pairs, and a pair never spans lines.
- In prose the in-process path pairs a marker with the next prose marker in the same paragraph, so a pair may hold a soft or hard line break and an inline code span: ``a <^>b `x` c<^> d`` marks `b` through `c`, code span included.
  In-process, a marker inside a code span never opens or closes a prose pair.
  Known gap (highlight same-line pairing, #34): the two paths pair differently in prose.
  `mw pre` pairs only inside one prose run, the text between two code spans on one line, so `e <^>f` followed on the next line by `g<^> h` is highlighted in-process and stays literal through the pipeline.
  A pair around a code span is left for `mw post`, which wraps it in three pieces, and in `mw post` a marker inside a code span closes a prose pair (``a <^>b `x<^>y` c<^> d``).
  The in-process path also pairs across a line that Python-Markdown reads as paragraph text and CommonMark reads as a new block (`a <^>b` followed by `- c<^> d`), and it wraps a code block in `<mark>` when a marker sits on either side of it.
  Planned (highlight same-line pairing): in prose a marker pairs with the next prose marker on the same line, in both paths, so a pair never holds a line end; a pair may still hold an inline code span.
  Planned (highlight same-line pairing): the in-process inline processor matches an opener alone and searches for its closer on the same line; with no closer there the opener stays literal and matching resumes just after it, and a pair whose text holds a stashed block's placeholder is declined the same way.
  Planned (highlight same-line pairing): `mw pre` wraps everything between a same-line pair in one `<mark>`, code spans included; a marker inside a code span stays literal in `mw pre` and never closes a prose pair in `mw post`, and a code span is followed across a line end, never across a blank line, when deciding what is inside one.
  Planned (highlight same-line pairing): the tests are differential: over a corpus of two-line and three-line documents generated from the block starts of both renderers, the in-process render, the stub pipeline, and the Hugo pipeline highlight the same text.
  Decision (2026-11-16): prose pairing departs from `do-markdownit`, which pairs across a soft line break; a pair that crosses a line end has no single meaning under Python-Markdown and CommonMark, and the plan review measured a paragraph-end test at 294 path differences over 1,133 generated documents against none for the same-line rule; the CHANGELOG's upgrade notes name the pairs that stop highlighting.
  Known gap (highlight across inline constructs): a pair that starts inside emphasis or a link and ends outside it (`*a <^>b* c<^>`) loses the emphasis in-process and mis-nests the `<mark>` through the pipeline.
- `\<^>` renders a literal marker in all three contexts and in both paths.
  Inside a code block the post stage reads markers and escapes from the text of each rendered code line, tags ignored, so a marker pairs and a backslash escapes it whatever tags sit between or inside them, under Pygments and under Chroma.
  Exactly one backslash is removed for an escape, a paired marker's characters are removed, and every tag stays where it is, so a `<span>` that held only a backslash or part of a marker remains, empty; a revealed literal marker is written `&lt;&#94;&gt;`, so a second `mw post` leaves it alone.
  In prose `mw pre` reads the backslashes before a marker in pairs: an odd run escapes the marker, and `mw pre` then adds one backslash and writes the marker's `<` as `&lt;`, so Python-Markdown and a CommonMark renderer both hand `mw post` the escaped form; an even run leaves the marker live, as the in-process path already reads it.
  Known gap (literal backslash before a highlight): in code, where a backslash is not an escape character, a highlight that starts directly after a literal backslash cannot be written (`C:\<^>Users<^>\me`).
- The pre stage wraps prose markers only, outside fenced code, indented code, and inline code spans.
  The post stage reads the escaped `&lt;^&gt;` form from text tokens only (never an attribute, a `<script>`, or a `<style>`) and wraps each text run between a pair on its own, so a `<mark>` never crosses a syntax-highlight `<span>`.
  Planned (hardening): the post stage also skips `<title>` and `<textarea>`, whose content a browser shows as characters.
  Today a pair in a page's `<title>` is wrapped, and the browser tab shows the `<mark>` tags as text.
- It takes no options.

### Fence

- Directives are the first lines inside a fence: `[label TEXT]`, `[secondary_label TEXT]`, and `[environment NAME]`.
- Prefix flags go in the info string, comma-separated, with the language before or after them (`line_numbers,python`): `line_numbers`, `command` (a `$` prefix), `super_user` (a `#` prefix), and `custom_prefix(TEXT)` with `\s` for a space.
  The last three set the language to `bash` when the info string names none.
- Output: `<div class="code-label" title="TEXT">` before the block, `<div class="secondary-code-label" title="TEXT">` inside the `<code>`, `environment-NAME` on the `<pre>`, and for a prefix `prefixed TYPE` on the `<pre>` with each line wrapped in `<ol><li data-prefix="...">`.
- Directives work in every closed fence `_fences` finds (indented up to three columns, or inside a list item); a fence behind a block quote marker is not found, and an unclosed fence is read as prose, so its directives stay text.
  Known gap (fence in a tight list): in-process, an indented fence with a directive or prefix flag directly under a tight list item's text ends the list at that item; put a blank line before the fence.
- Options: `allowed_environments` (omitted allows every name; an empty list allows none and warns; an unlisted `[environment NAME]` line stays in the code as text), `label_class`, and `secondary_label_class`.
  Planned (hardening): `label_class` and `secondary_label_class` accept space-separated class tokens of letters, digits, `-`, and `_`; any other value is a `ConfigError`, or an `OptionError` in-process.
  Today the value goes into the `class` attribute unescaped.
  Planned (public fence API): `fence.py` exposes the scan that lists the environment names a document's fence directives name, by the same rules the pre stage extracts them with; the host API function below is built on it.
- The `mw-fence` marker (version 1: `label`, `secondary_label`, `environment`, `prefix_type`, `prefix_value`, each present only when set) sits before the fence at the fence's indentation, followed by a blank line when the fence is indented.
  Planned (hardening): a `line_numbers` flag that replaces an earlier `command`, `super_user`, or `custom_prefix` drops `prefix_value`; today the earlier value stays in the marker.
  The fence itself is kept, so the renderer still highlights the code, and the post stage styles the first `<pre>` or `<code>` after the marker and before the next one, however far away, an inline code span included.
- Line prefixes handle two renderers: Pygments emits flat newline-delimited lines, and Chroma (Hugo) wraps each line in `<span class="line">` when `noClasses = false`.
  Planned (hardening): a Chroma line that already ends with a newline gains no second one, and the Chroma test asserts the whole `<li>`; today each prefixed line under Chroma ends with two.
  Known gap (line prefixes and wrapping spans): a span the highlighter wraps around a whole line is cut by the prefix wrap, so under Pygments with `hl_lines` or `line_spans`, and under Chroma with Hugo's default `noClasses = true`, the span closes in the next `<li>` and one empty prefixed line is added.
  Known gap (line-number tables): with `linenums` under Pygments or `lineNos = true` under Hugo the marker binds to the gutter `<pre>`, so the classes, and under Hugo the label and the prefixes, land on the line numbers.

### Embeds

Each embed line becomes raw HTML that matches `do-markdownit`'s output, its inline `style` attributes and inline handlers included.

| Extension | Line | Arguments | Output |
|-----------|------|-----------|--------|
| youtube | `[youtube ID HEIGHT WIDTH]` | height and width optional (270, 480) | `<iframe class="youtube">` with the aspect ratio computed from the dimensions and a fallback link |
| codepen | `[codepen USER HASH flags]` | flags in any order: `light` or `dark`, `html`, `css`, `js`, `result`, `lazy`, `editable`, and an integer height (256) | `<p class="codepen">` with `data-` attributes |
| twitter | `[twitter URL flags]` | a full URL, a scheme-less URL, or a bare `user/status/id`, on `twitter.com` or `x.com`; flags `light` or `dark`, `left`, `center`, `right`, and an integer width clamped to 250 through 550 | `<div class="twitter">` around a `blockquote.twitter-tweet`, with the link canonicalized to `twitter.com` |
| instagram | `[instagram URL flags]` | a full URL, a scheme-less URL, or a bare shortcode; flags `caption`, `left`, `center`, `right`, and an integer width clamped to 326 through 550 | `<div class="instagram">` around a `blockquote.instagram-media` |
| slideshow | `[slideshow URL ... HEIGHT WIDTH]` | one or more image URLs; trailing integers are the height and width (270, 480) | `<div class="slideshow">` with left and right arrows that scroll the slides through an inline `onclick` |
| image_compare | `[compare URL1 URL2 HEIGHT WIDTH]` | exactly two image URLs; height and width optional (270, 480) | `<div class="image-compare">` with a range input that moves the divider through an inline `oninput` |

- codepen, twitter, and instagram need a provider script.
  Their post stage appends the `<script>` once, at the end of its input, when the HTML holds an embed element outside every `<template>` and no script with that `src`; on a full page the end is after `</html>`, where a browser still runs it.
  The decision comes from the HTML alone, so it works on hand-written embeds, both paths agree, and running the stage twice adds nothing, except on input that ends inside an unterminated comment, which gains one more script on every run.
- In-process, the expanded HTML is stashed so Markdown does not re-parse it; `mw pre` emits it inline.
- youtube, codepen, twitter, and instagram take the `load` option, described under Click-to-Load.
  slideshow and image_compare take no options.
- Known gap (integer no author types): a directive or annotation integer written as a digit string of 4,301 characters or more, or with a non-ASCII digit such as `²`, ends the stage in a traceback, in-process too.
- Known gap (embed beside other content): an embed line with no blank line before and after it renders inside the neighboring paragraph, list item, or heading in-process and as its own block through `mw pre`, and under a CommonMark renderer the lines that follow it up to the next blank line are raw HTML; put a blank line on both sides.
  An embed indented under a list item stays in the item in-process, since the expansion keeps the line's indentation.

### Click-to-Load

- `load` decides when a third-party embed contacts its provider: `eager` (the default), `lazy` (youtube only), or `click`.
  An unsupported value, or `load` on an extension that does not take it, is a `ConfigError`.
- `eager` output stays byte-identical to the releases before the option existed.
- `lazy` keeps the live iframe and adds `loading="lazy"`.
- `click` replaces the embed with an inert preview, the `mw-embed` contract (version 1): `<div class="mw-embed" data-mw-version="1" data-mw-embed="NAME" data-mw-load="click">`, plus `data-mw-script` for the script embeds.
  Inside it, `<template class="mw-embed-content">` holds the exact `eager` markup without the provider script, and `<div class="mw-embed-preview">` holds the provider text, a `button.mw-embed-load`, and an `a.mw-embed-link` to the original.
  The preview text is fixed English.
- Nothing loads until a host script swaps the template in; markwright ships none, and with JavaScript off the direct link still reaches the content.
- The provider script is skipped when every embed of that kind on the page is a preview, and appended once when eager and click embeds mix.
- `docs/click-to-load.md` is the public contract a host script codes against, with a sample script and the provider calls to run after the swap.

### Button and Lightbox

- `[button URL TEXT]` becomes `<a class="mw-button" href="URL">TEXT</a>`, and `[button primary URL TEXT]` adds `mw-button-primary`.
- `[lightbox URL ALT]` becomes `<a class="mw-lightbox" href="URL"><img src="URL" alt="ALT" /></a>`; without a host script the link opens the image.
  ALT is optional, and `[lightbox URL]` renders `alt=""`.
- Both are pre-stage only and take no options.
  They emit inline raw HTML, so the renderer wraps the link in `<p>` and inline Markdown in a button's text still renders.

### Mermaid

- A closed `mermaid` fence becomes `<pre class="mermaid">` with the source HTML-escaped and otherwise intact and no `<code>` wrapper, matching mermaid.js's default selector.
- It is pre-stage only and its own extension, not a fence feature, so it can be disabled alone and fence parity is untouched.
- It runs ahead of fence and `pymdownx.superfences`, so a `custom_fences` mermaid entry in the host config is inert for the fences markwright converts; a `mermaid` fence it does not convert (behind a block quote marker) still reaches that entry.
  `mw pre` emits the `<pre>` inline as raw HTML, with the fence's indentation before every line of it and a blank diagram line left empty.
  In-process, a fence indented four or more columns is replaced by a line holding a random token and stashed below Python-Markdown's whitespace normalizer, so the `<pre>` holds the exact diagram text with no indent and a blank line in the diagram does not split it.
  `_fences` reads a fence that deep as a fence under a line it reads as a list marker or in a block opener's body (Rules Every Feature Follows says which four-column lines it reads as content).
  In a list item or an opener's body Python-Markdown wraps raw `<pre>` lines left that deep in a paragraph or splits them at a blank line, which is why the fence is stashed.
  A fence indented fewer than four columns, one under a list item included, is emitted inline in-process, the same text `mw pre` emits, so a diagram at column 0 is its own block beside a paragraph line or a table.
  Known gap (indented mermaid fence): a fence that is emitted inline keeps its indentation inside the `<pre>`, before every line after the first and before `</pre>`, unless the renderer strips it with the list item around the fence, so the later lines keep their indentation against each other and gain one uniform indent.
  A fence indented one to three columns keeps all of it under Python-Markdown in both paths, at the top level and under a list item alike, and at the top level it keeps all of it under a CommonMark renderer too.
  Under a CommonMark renderer such as Hugo, a fence in a list item keeps the columns it sits past the item's content column: none at that column (two under `- item`, three under `1. item`), and one to three when it sits that far past it.
  Known gap (mermaid diagram beside a text line): when a text line stands directly above an indented fence, Python-Markdown reads the `<pre>` as part of that line's paragraph, in-process and after `mw pre`, and in-process a text line directly below a stashed diagram joins the diagram's paragraph; a CommonMark renderer makes a diagram fewer than four columns past its list item, or past column 0 outside one, its own block.
  Known gap (nested mermaid diagram through `mw pre` and Python-Markdown): Python-Markdown with no markwright extension reads the emitted `<pre>` of a fence indented four or more columns, under a list item or in a block opener's body, as paragraph text, where in-process the diagram is stashed.
  In a tight list item the `<pre>` keeps the fence's whole indentation on its later lines; in a loose list item or an opener's body Python-Markdown strips four columns a level and wraps the `<pre>` in a `<p>`; and a blank line in a diagram indented four or more columns breaks the `<pre>`, whose later lines land in a second paragraph or a code block.
  Known gap (mermaid diagram in a footnote body): in-process, the footnote's own `<p>` wraps the `<pre>` together with the back link.
  Known gap (mermaid fence under a list item at fewer than four columns): a fence indented one to three columns under a list item is emitted inline in both paths, so the `<pre>` keeps the fence's indentation under Python-Markdown; a CommonMark renderer keeps a fence at or past the item's content column inside the item.
  With no blank line above the fence (`- item`, then the fence at two columns), Python-Markdown keeps the diagram in the item, after a `<br />` when the fence is indented two or three columns, and a text line directly below the closing fence is its own paragraph after the list.
  After a blank line Python-Markdown reads a line indented fewer than four columns as outside the list item, so the list ends before the diagram.
  The same holds for a fence at two columns under `: definition`, which is short of the definition's body column: it is emitted inline in both paths and keeps its indentation after the definition list, where a CommonMark renderer with definition lists holds it in the `<dd>`.
  Known gap (mermaid fence after a lazy continuation line or a marker-only line): a fence at one to three columns that follows a line at the list item's own indentation (`- item`, then `lazy`), or a line holding only a list marker (`-` or `1.`), is emitted inline in both paths like every fence that shallow, and Python-Markdown keeps the fence's indentation inside the `<pre>`; a CommonMark renderer holds the fence in the item when it sits at or past the item's content column, except after a marker-only line followed by a blank line.
  Known gap (mermaid fence right after an HTML block line): with no blank line between an HTML block line such as `<div>` and a fence at column 0, a CommonMark renderer reads the diagram as part of that HTML block, so a blank line inside the diagram ends the block and splits the `<pre>`; Python-Markdown renders one `<pre>` in both paths.
  Known gap (mermaid fence four or more columns past its list item): `_fences` reads a fence under a list item at any depth as a fence, so the stage converts one that the renderer reads as indented code or as paragraph text.
  A CommonMark renderer does so from four columns past the item's content column (`- item` with the fence at six columns): after a blank line the escaped `<pre>` shows as a code block, and with no blank line it is paragraph text, so the diagram's lines lose their leading spaces and a blank line in it ends the paragraph.
  Python-Markdown does so after a blank line from four columns past the item's body column (the fence at eight columns under `- item`): after `mw pre` the escaped `<pre>` shows as a code block, and in-process the code block holds the stashed `<pre>` unescaped.
  `_fences` also reads as a list marker a line the renderer reads otherwise (Rules Every Feature Follows, Known gap: line `_fences` reads as a list marker), so a `mermaid` fence indented four or more columns under a thematic break written `* * *` or `- - -`, with or without a blank line between, is converted: Python-Markdown and Hugo show the rule and then a code block, which holds the escaped `<pre>` after `mw pre` and the stashed `<pre>` unescaped in-process.
  A fence four columns in, after a blank line, under a break written `---`, `***`, `___`, or `_ _ _` is not converted and shows as a code block.
  Known gap (mermaid fence `_fences` does not read): a fence `_fences` does not read as one (the cases under Rules Every Feature Follows, and a fence at four columns after a lazy continuation line or under a marker-only line) is not converted in either path.
  Known gap (directive inside a mermaid fence): `mw pre` replaces the mermaid fence before the directive stages run, so a directive line in the diagram source is expanded, while in-process it stays literal.
- The host loads mermaid.js; markwright ships none.

### Icons

- `:PACK-NAME:` in prose inlines an SVG as `<span aria-hidden="true" class="mw-icon"><svg>...</svg></span>`.
- The `packs` option maps a prefix to a directory of SVG files the host supplies; markwright ships no icons.
  `:lucide-check:` reads `check.svg` from the `lucide` pack, a file in a subdirectory joins its path parts with hyphens, and prefixes match longest first.
- Anything before the `<svg` tag in a file is dropped and the markup is joined onto one line; in-process the SVG is otherwise unchanged, and through `mw pre` the renderer parses Markdown in its text content, a `<title>` included.
- A shortcode that names no pack or no file stays literal text.
- Shortcodes resolve in prose only: never in fenced code, indented code, an inline code span, or an HTML tag, and `mw pre` also leaves a diagram that the mermaid stage emitted alone (a line that starts with exactly `<pre class="mermaid">`, through the first `</pre>` after it; text after the tag on that line is prose), since in-process the diagram is stashed, by markwright or by Python-Markdown's own raw HTML pass, and never read.
  The icons pre stage runs after every directive stage, so a shortcode inside a `[button]`, `[lightbox]`, `[tab]`, or embed line gives what the in-process render gives, and a converted `mermaid` diagram keeps its shortcode text.
  Decision (2026-11-20): `mw pre` reads a block that opens with the mermaid stage's tag as a CommonMark renderer reads it, as raw HTML through the first `</pre>` with no fence line inside it read as a fence, so under Hugo a shortcode after the block renders as an icon whatever the block holds; under a Python-Markdown renderer with a fenced code extension, which reads a fence line inside the block as a fence, an author-written block that holds one does not match the in-process render, as the next Known gap says.
  Known gap (author-written mermaid tag): `mw pre` reads a block an author wrote that starts with exactly `<pre class="mermaid">` as it reads an emitted one, so a shortcode in its text stays literal and a fence line in its text opens no fence for the icons stage.
  In-process a shortcode inside such a block renders as an icon when the block sits under a list item at four or more columns after a blank line, or in a block opener's body, because Python-Markdown does not stash it there.
  When the author's block holds a fence line, Python-Markdown with a fenced code extension reads a fence from that line on, so a shortcode after the `</pre>` that `mw pre` replaces lands as escaped markup inside a code block, where in-process it stays literal.
  Known gap (shortcode in a comment or tag that holds a directive line): the icons stage skips a multi-line HTML comment or tag only when no `<` or `>` stands inside it, and a directive stage that runs first writes markup into one that holds a directive line (see Deferred), so `mw pre` then replaces a shortcode on the other lines of it, where in-process the whole comment or tag stays literal; the `Planned (hardening)` comment region under Rules Every Feature Follows closes the comment case.
- A relative pack path resolves against the directory `mw` or the host runs from.
- With `packs` omitted the extension does nothing, an empty `packs` warns, and a `packs` that is not a table, a path that is not a string, or a directory that does not exist is a boundary error.
  Planned (hardening): an SVG file that cannot be read or is not UTF-8 is a boundary error that names the file; today it is a traceback.

### Annotate

- `[annotate]` before a block links each `(N)` marker in the block to the N-th item of the ordered list after it: `<a class="mw-annotation" href="#mw-annotation-B-N">N</a>`, where B counts annotated blocks in the document.
  In highlighted code a marker is linked only where the highlighter keeps `(N)` in one text run, in practice inside a comment; in an unhighlighted block every `(N)` is linked, a call such as `compute(1)` included.
- The block gains `mw-annotated`, and the list gains `mw-annotations`, `data-mw-version="1"`, and an `id="mw-annotation-B-N"` on each item.
- In code, the `# (1)!` form strips the comment token around the marker (Pygments in-process, Chroma through Hugo with `noClasses = false`); a highlighter that emits no comment class, Hugo's default inline styles included, degrades to the plain form.
  Planned (annotate overlap): when a comment token holds a `!` marker, the comment is replaced by the links for every valid marker in it, in order, and `_html.apply_edits` refuses overlapping spans with an exception.
  Today a comment that holds a plain marker and a `!` marker (`# (1) and (2)!`) produces two overlapping edits and broken HTML, in both paths.
- It travels as an `mw-annotate` marker comment, and its post stage runs ahead of fence's so the fence marker is still a comment when the block is located.
- With no host script the result is a numbered list under the block; tooltips are host work.
- The classes and the `mw-annotation-B-N` id scheme are a public contract.
- Known gap (annotate and existing attributes): a list item that already carries an `id`, or a list that carries `data-mw-version`, gains a second attribute of the same name, and the author's `id` is lost to the browser.

### Containers

A container is an opener line and a closer line with arbitrary Markdown between them.
Block grids, cards, and tabs share one pairing scanner (`_containers.py`), so the rules are written once.

Pairing:

- Openers are `[grid ...]`, `[card]`, and `[tab NAME]`; closers are `[/grid]`, `[/card]`, and `[/tab]`, each alone on its line.
- A closer pairs with the nearest unpaired opener of the same kind at the same indentation, matched like brackets; an opener a closer skips over is unclosed.
- An opener and its closer sit at the same indentation, at the top level or inside a list item; in any other context (a blockquote, say) the lines stay literal.
  Indentation is compared by column with a tab stop every four columns, the way `_fences` reads it, so an opener indented with a tab pairs with a closer indented with four spaces.
  A non-blank line indented less than an open container's opener ends that container's block: the opener is unclosed, and a closer after that line no longer pairs with it.
  An unclosed `[tab]` or `[card]` and its stray closer then stay literal and are reported, and an unclosed `[grid]` follows the rules for one (the list shortcut, or literal when a stray `[/grid]` follows).
- A directive is the whole line, so a line with anything else on it is never an opener or closer.
  A backslash before the bracket (`\[grid 3]`, `\[tab Name]`, `\[/tab]`) keeps a standalone line literal through Markdown's own escape, with no report.
  The grid and tabs pages document the escape and tests pin it in both paths.
- Containers nest: a grid in a card, a grid in a grid, tabs in a card, a grid in a tab, and a tab set in a tab (it starts a set of its own inside that tab's block, per the sibling rule under Tabs).
- An opener or closer line inside fenced or indented code stays literal.

Problems:

- An unclosed `[card]` or `[tab]`, a stray closer, or a paired `[card]` whose nearest enclosing container is not a block grid stays literal text and is reported under `--warn`.
  A `[card]` outside a block grid is reported once, on its opener.
- `mw pre` and `mw post` are separate processes, so each report travels as a problem marker: the pre stage appends an `mw-grid-problem` (grid and card lines) or `mw-tab-problem` (tab lines) comment to the literal line, and the post stage composes one `--warn` message from it and removes the comment.
  The payload is `version` 1, the 1-based `line` in the stage's input, which is the source line only when no earlier stage added lines above it, the `directive`, and a `reason` from a closed vocabulary (`unclosed`, `stray-closer`, `card-outside-grid`), so a marker that decodes puts only fixed text on stderr; a marker that fails to decode is reported on one line with its payload shown through `repr`, which escapes control characters.
- A line that is not an opener at all (an invalid `[grid ...]`, a `[tab ]` with no name) stays literal with no report.

Both paths:

- The pre stages emit each container marker as an HTML comment on its own line with a blank line on either side, at the opener's indentation, so the content between renders as normal Markdown in Python-Markdown and in Goldmark.
  A problem marker is the exception: it sits on the literal line, after the directive, so the line still renders as the text the author wrote.
  The `[grid]` shortcut marker and the `[annotate]` marker are emitted like the container markers, on a line of their own with a blank line on either side, and a problem marker is appended before a trailing carriage return, so a CRLF line keeps its line end.
- Grid and tabs both run their pre stage at 21, so either may scan a document the other has already rewritten.
  The scanner reads a line that is solely one of the six paired container markers as the opener or closer it stands for, so pairing and card enclosure come out the same in either order, and a stage leaves a pair that is already its own markers alone.
  `mw pre` over its own output therefore leaves a valid document's container markers unchanged.
- The post stages wrap the content through `_html` span edits and remove the markers.
  The in-process grid, annotate, and tabs postprocessors run at 27, below Python-Markdown's `raw_html` at 30, so the stashed markers are restored first whatever the extension load order, and ahead of fence at 25; a test renders tabs, both grid forms, and annotate with `md_in_html` listed before and after the markwright extensions.
- `tests/test_roundtrip.py` and its hypothesis grammar cover containers, and the Hugo integration test carries a block grid with cards and a tab set.

### Grid and Cards

- The grid opener is `[grid]` with optional tokens in any order, each at most once: `cards`, and a column count from 1 to 6.
  `[grid 3]`, `[grid cards 3]`, and `[grid 3 cards]` are all valid; any other token or count leaves the line literal.
  Such a line is not an opener, like `[tab ]`: it stays literal with no report of its own, never pairs, and never becomes the list shortcut.
  A `[/grid]` it leaves unpaired is a stray closer, and a `[card]` it leaves outside any block grid is reported as one.
  A `[card]` is inside a block grid only when the `[grid ...]` it opened in is paired; a card in a `[grid ...]` that is never closed stays literal and is reported like a card outside a grid.
- A paired `[grid ...]` ... `[/grid]` is a block grid: it wraps everything between its lines in `<div class="mw-grid">`, plus `mw-grid-cards` with `cards` and `mw-grid-cols-N` with a count, and each child block is a grid cell.
- An unclosed `[grid ...]` is the list shortcut: it puts the same classes on the `<ul>` or `<ol>` that follows, or is skipped and reported under `--warn` when no list follows.
  A shortcut grid inside a block grid therefore needs its own `[/grid]`, since the outer closer would otherwise pair with it.
  A `[/grid]` with no opener at its indentation is a stray closer, and the nearest `[grid ...]` still open at another indentation then stays literal instead of becoming the shortcut, since its author meant a block grid; only the closer is reported.
- `[card]` ... `[/card]` directly inside a block grid wraps its content in `<div class="mw-card">`, so one card can hold several blocks (a heading, a paragraph, a list, a link).
- A list inside a block grid with `cards` keeps its markup; host CSS makes each item a cell.
  The docs sample covers it with `display: contents` on the list (`.md-typeset .mw-grid-cards > ul`, `.md-typeset .mw-grid-cards > ol`, the prefix being what outranks Material's own list rule) and with the card rules extended to its items (`.md-typeset .mw-grid-cards > ul > li`, `.md-typeset .mw-grid-cards > ol > li`), each item laid out as a cell and styled as a card, as Material did.
- Markers: the list shortcut is `mw-grid`; a block grid is `mw-grid-block` and `mw-grid-end`; a card is `mw-card` and `mw-card-end`.
  Each carries version 1, and `mw-grid` and `mw-grid-block` add `cards` and `columns`, each present only when set.
- It takes no options.
  The grid and card classes are a public contract; the docs sample in `docs/stylesheets/extra.css` carries the column, card, and narrow-screen rules.

### Tabs

- `[tab NAME]` ... `[/tab]` is one tab; NAME is the rest of the opener line, trimmed, non-empty, without `]`, and may hold spaces (`[tab Node.js 20]`).
  A `[tab ]` with no name is not an opener: it stays literal with no report, and a `[/tab]` it leaves unpaired is a stray closer.
- Tabs separated only by blank lines group into one set, any other content between them starts a new set, and the first tab in a set is selected.
  A tab joins the set of the tab before it only when the nearest non-blank line above its opener is the closer of a paired tab at the same indentation; any other tab starts a new set, so a tab opened inside another tab's body, directly or inside a grid and a card, starts a set of its own inside that tab's block, and a set never runs past the end of a list item.
- The name renders as escaped plain text; inline Markdown in it is not rendered.
  The tabs and grid preprocessors run ahead of Python-Markdown's `html_block` preprocessor, which then stashes each marker comment whole, so a tab name that holds backticks renders as the same escaped text in both paths, at any indentation, because `encode_marker` also writes a backtick as `\u0060` and no inline processor can open a code span inside a payload; a `[tab]` or `[grid]` line inside a raw HTML block is then expanded in-process, as `mw pre` already expands it.
- A set renders as pymdown-extensions' `tabbed` `alternate_style` markup, so a host's existing tab CSS styles it: `<div class="tabbed-set tabbed-alternate mw-tabs" data-tabs="S:N">`, one radio `<input>` per tab (`id="mw-tab-S-T"`, `name="mw-tab-S"`, the first `checked`), a `<div class="tabbed-labels">` of `<label for="mw-tab-S-T">`, then a `<div class="tabbed-content">` holding one `<div class="tabbed-block">` per tab.
- S counts sets and T counts tabs within a set, both from 1, per document; the `mw-tab-` prefix keeps the ids from colliding with pymdown-extensions' `__tabbed_` ids when a host loads both.
  S follows the order in which each set's first tab opens in the document, so an enclosing set has a lower number than a set nested in it.
- Markers: `mw-tab` (version 1, with `name`, and `first`, true for a tab that starts a set) and `mw-tab-end`.
  The post stages decode a closer marker's payload with the same strict model as its opener, and a pair whose closer fails is skipped and reported under `--warn`.
- It takes no options.
  Tabs switch with CSS alone; the docs sample's selector chains cover six tabs per set.
- The `mw-tabs` class, the markup, and the `mw-tab-S-T` id scheme are a public contract.

### The `mw` CLI

- `mw` is a stdin-to-stdout filter, so the syntax works around any renderer: `mw pre < in.md | some-renderer | mw post > out.html`.
  Planned (hardening): `mw` reads and writes UTF-8 whatever the locale or `PYTHONIOENCODING` says, and input that is not UTF-8 is one `mw: error:` line and exit 2.
  Today it uses Python's stdio encoding, which is UTF-8 only under a UTF-8 locale.
  Planned (hardening): `mw pre` passes a leading YAML (`---`) or TOML (`+++`) front matter block through untouched.
  Today it reads front matter as Markdown, so a highlight marker, an icon shortcode, or a directive line inside it is rewritten and can break the host's build.
- `mw pre` runs every selected extension's source stage, and `mw post` runs every HTML stage, in the registry's priority order, which mirrors the in-process order; CLAUDE.md, Processor Priority Reference, holds the full table.
- `mw post` is complete on its own: it needs no marker to inject a provider script, and running it twice neither double-injects a script nor double-wraps a mark.
- `mw render` is the one-shot in-process path: a `markdown.Markdown` with `pymdownx.superfences`, `pymdownx.highlight`, and the selected extensions, and no other extension, so it renders no admonitions and no `md_in_html`; its syntax highlighting needs Pygments, which markwright does not depend on.
- `mw config` prints the resolved configuration and the source of every value, `mw list` prints each extension and its stages and takes no flags, and `mw --version` prints the version.
- Flags on `pre`, `post`, `render`, and `config`: `--config PATH` loads exactly that file, and `--exclude NAME` (repeatable, applied last) drops an extension.
  `--warn` (`post` only) writes advisory diagnostics to stderr without changing the output or the exit code.
  Known gap (config `warn` default, #33): `mw post` does not read the config key `warn`, which `docs/config.md` calls the default for `--warn`; the key is validated and shown by `mw config` and does nothing else.
  Planned (config `warn` default): `mw post` takes the config key `warn` as the default for its diagnostics; `--warn` turns them on and `--no-warn` turns them off, whatever the config says, and the last of the two on the command line wins.
  The pair exists on `mw post` only, `mw config` shows the resolved value and its source, and the diagnostics stay plain stderr lines that `PYTHONWARNINGS=error` does not escalate.
  Known gap (parser hygiene): a subcommand accepts an abbreviated long option, so `mw post --w` is read as `--warn`; `mw` with no subcommand prints its usage line on stdout; and `--config ""` falls back to discovery.
  Known gap (in-process diagnostics): the in-process path collects no diagnostics, so `mw render`, MkDocs, and a host that renders through Python-Markdown never see what `mw post --warn` reports, and no path reports a disallowed environment; a host gets those names from `disallowed_environments` once the public fence API ships.
- Exit codes: 0 on success, an empty selection included; 2 on a config error, with one `mw: error:` line, and on a usage error, with argparse's usage text; 1, with a traceback, if an I/O or decoding error propagates, an unreadable or non-UTF-8 config file included; 120 if stdout cannot be flushed at exit (a full device, or a closed pipe on a small output).
  Planned (hardening): a decode error, a closed stream, a broken pipe, and an unreadable or non-UTF-8 config file are each one `mw: error:` line and exit 2, so no input ends in a traceback.
- An empty selection prints one `mw: warning:` line and exits 0; `mw pre` and `mw post` then pass input through unchanged, and `mw render` renders it as plain Markdown.
  Each `ConfigWarning` is one `mw: warning:` line, so a config with two no-op settings prints two, and other warnings keep Python's format.
- The renderer between the two stages must pass raw HTML through, preserve HTML comments, and should emit span-based syntax highlighting.
  A renderer that misses one loses the features that depend on it: without comments that is fence styling, grids, cards, annotations, tabs, and the container problem reports, and the text a marker carries (fence labels, tab names) is lost with it.
  `docs/renderer-requirements.md` is the contract.

### Config and the Host API

- The file is a standalone `markwright.toml`, or a `[tool.markwright]` table in `pyproject.toml`; in one directory `markwright.toml` wins.
- Discovery walks up from the current directory and stops at the first directory that has either; `--config PATH` bypasses it, and a missing path or a `pyproject.toml` with no table is an error.
- Precedence, highest first: a CLI flag, the config file, the built-in default (every extension on, no options, `warn` off).
- The keys are `enable` and `disable` (lists of extension names, mutually exclusive), `warn` (a boolean), and one options table per extension.
  A `None` value, which only a host's mapping can carry, counts as omitted.
  An unknown key, extension name, or option is an error.
  Today the key of a `None` value is not checked, so an unknown key with a `None` value passes.
- The options that exist: `fence.allowed_environments`, `fence.label_class`, `fence.secondary_label_class`, `load` on youtube, codepen, twitter, and instagram, and `icons.packs`.
- Every setting follows the config law in Invariants and in `docs/config.md`, Config Rules.
  A `ConfigError` names the extension, the key, and the source; the Python-Markdown path raises `OptionError` (a `ValueError` subclass) for the same bad value.
  Known gap (no-op warning source): a no-op `ConfigWarning` that comes from an extension's own option reader names the key and no source.
  Planned (hardening): a config file that cannot be read or is not UTF-8 is a `ConfigError`; today it is a traceback and exit 1.
- The host API, re-exported from the package root, lets a host tool carry a markwright table in its own config file: `config_from_mapping(table, source)` validates a parsed table with the same rules as a file, `selected_extensions(config)` applies `enable` and `disable` (an empty selection warns and returns an empty list), and `extension_configs(config, names)` builds the `markwright.<name>` option dicts for `markdown.Markdown`.
  `mw render` builds its own `Markdown` through `selected_extensions` and `extension_configs`.
- The public names are `Config`, `ConfigError`, `ConfigWarning`, `OptionError`, and those three functions; `load_config` is not public, and Bartleby is the first consumer.
  Known gap (public fence API, #32): Bartleby reports disallowed fence environments by importing `markwright._fences.find_fenced_blocks` and fence's private regexes and `read_options`, so a refactor of either breaks it.
  Planned (public fence API): `disallowed_environments(source, config)` joins the public names and returns each environment name a fence directive names outside `fence.allowed_environments`, once each, in order of first appearance.
  Planned (public fence API): it scans with fence's own rules (a directive counts only among a fence's leading lines, label and secondary-label lines are skipped, and a directive inside a nested fence's source is code), with two stated additions: a disallowed environment line does not end the scan of that fence, so each disallowed name among the leading lines is reported although fence stops reading directives at the first; and a `mermaid` fence is skipped when `mermaid` is selected, since that stage replaces the fence before fence reads it.
  A name is everything after the first space of the directive, compared as written.
  Planned (public fence API): it returns an empty list when `allowed_environments` is omitted or when `fence` is not selected, emitting no warning, its own or from the option and selection readers it calls; with an empty allowlist it reports every name; whether to print the result stays the host's decision.
  Planned (public fence API): the tests call it under `warnings.simplefilter("error")` with an empty allowlist and with an empty selection, and cover two environment lines one after the other, a `mermaid` fence with `mermaid` selected and excluded, and a name with padding.
  Planned (public fence API): `config_from_mapping` raises `ConfigError` with the source label for a table that is not a mapping, reads `None` as an empty table, and checks key names before it drops `None` values, so an unknown key is an error whatever its value.

### Docs Site

- The MkDocs Material site in `docs/` documents and demonstrates every feature: one page per extension with its usage, its syntax, rendered examples, the HTML and marker contracts where the extension has them, and a Host CSS and Script section.
  The grid page leads with a block-grid demo and the tabs page with a tab-set demo.
- It is also the worked host example: `docs/stylesheets/extra.css`, `docs/javascripts/` (a pinned mermaid.js from a CDN, the lightbox `<dialog>`, the annotation tooltips), and two small, credited, liberally licensed icon packs (`lucide` and `mw`) under `docs/icons/`.
  None of it ships in the package.
- The reference pages are Configuration, Click-to-Load, the CLI reference, the Pipeline Guide, Renderer Requirements, the MkDocs and Hugo integration guides, and the Demo page.
- Known gap (docs catch-up): the docs fall short of the code in the places below, and the docs catch-up item fixes each.
  The Demo page shows only the eight ported extensions, and the eight ported extension pages show no HTML output.
  `docs/cli.md` covers no containers (its `mw pre` and `mw post` paragraphs name fence, the grid list shortcut, and annotate), its `--warn` section names only the `mw-fence` marker, its synopsis writes `--exclude NAME ...` for a flag that takes one name each time, and it tells the reader to escalate warnings with `python -W error`, where `PYTHONWARNINGS=error mw ...` is what works.
  `docs/cli.md` and the README do not say that `mw render` loads no other extension, or that its syntax highlighting needs Pygments.
  `docs/renderer-requirements.md` names only the `mw-fence` comment.
  `docs/pipeline.md`, `docs/integrations/hugo.md`, and the README describe the two stages through embeds, fence, and highlight only, and the README's usage examples load eight extensions.
  The Architecture list in `docs/index.md` has no tabs pattern.
  `docs/config.md` omits `fence.label_class` and `fence.secondary_label_class`, and its Hugo one-liner does not run.
  `docs/extensions/grid.md` says the `mw-cards` class is "from 0.4.0", though it never shipped in a release, and calls the list shortcut "the 0.4.0 behavior", though the block containers ship in 0.4.0 too.
  `docs/extensions/annotate.md` has no Marker Contracts section, its "Annotating a List" example needs `md_in_html`, which `mw render` does not load, and its comment-stripping note leaves out the `noClasses = false` condition.
  `docs/index.md` and `docs/integrations/mkdocs.md` say MkDocs is pinned below 2.0, which `pyproject.toml` does not do.
  `docs/integrations/hugo.md` says its commands are the ones CI runs and that Hugo strips output silently, and neither holds.
  The embed pages do not say that an embed line needs a blank line on both sides.
- Known gap (docs catch-up): the CHANGELOG's Unreleased section misstates 0.4.0 in the places below.
  It says a document with none of the new syntax renders as it did, with no pointer to the exceptions under Upgrading and Fixed.
  Its upgrade notes leave out that `selected_extensions` with no `enable` list returns fifteen names where 0.3.0 returned eight, the `[grid N]` forms, that a `mermaid` entry in `custom_fences` goes inert, and that a directive with nothing to apply to is removed.
  It lists the `mw-cards` to `mw-grid-cards` rename under Changed, though `mw-cards` never shipped, and it names fewer than the nine markers the release adds.
  Its Fixed entries for #20 and #29 describe the embed-in-code fix backwards, and the entry for a `<^>` pair inside indented code is missing.
  Each plan item above owes it a line: the pairs that stop highlighting under same-line pairing, and an existing `warn = true` that starts printing.
- `just docs-build` (strict) is the gate for it.

## Non-goals

Permanent; markwright does not do these:

- Ship JavaScript or CSS in the package. markwright emits stable class and data hooks; the host supplies behavior and styling.
- Change the all-on default (every extension loaded unless config says otherwise).
- Change extension output or break `do-markdownit` parity without a documented Decision.
- Reimplement syntax Python-Markdown or pymdown-extensions already provide: admonitions, math, critic markup, keys, mark, caret, tilde, abbreviations, and task and definition lists.
  Tabs is the one exception, kept because Hugo has no tabs; markwright's tabs emit `tabbed`'s markup rather than competing with it.
- Ship the theme behavior Material for MkDocs carried in its own JavaScript and CSS: linked tabs, tab anchor selection, styled tooltips, sortable tables, math loading, and code copy.
  That is host work, and Bartleby's themes port what Bartleby needs.
- A `:::name` container delimiter, or an alias for one; containers use the `[name]` and `[/name]` family.
- A generic container that adds arbitrary classes (`[div .class]`); that is Python-Markdown's `md_in_html` and `attr_list`.
- Bundle or depend on an icon set, or ship SVG or other assets in the package. The icons extension resolves against directories the host supplies.

## Component boundaries

- **Two consumers over one set of pure stage functions.** Each extension module exposes `expand_source` (the `mw pre` source stage) and, where it has one, `apply_html` (the `mw post` HTML stage). The in-process Python-Markdown `Extension` classes and the `mw` CLI both delegate to these, so the logic is written once.
- **`config.py`** owns discovery, parsing, validation, the resolved `Config` (a frozen pydantic model), and the public host API. It depends on `registry` (`EXTENSION_NAMES`, `OPTION_NAMES`, `REGISTRY`) and `_diagnostics` (`OptionError`), and nothing else; never on `cli`.
  Planned (public fence API): `disallowed_environments` lives here with the other host API functions and calls the scan `fence.py` exposes, so `config` gains `fence` as a dependency and `fence` never imports `config`.
- **`registry.py`** maps each extension name to a pydantic `StageSpec` (stage functions, priorities, the extension class, its option checker) and provides `run_pre`, `run_post`, and `describe`. Selection lives in `config.selected_extensions`; there is no `registry.select_extensions`.
- **`_fences.py`** (CommonMark fenced-code scanning) and **`_html.py`** (offset-preserving tokenizing over the stdlib `html.parser`) own structured-text parsing. No stage hand-rolls Markdown-structure or HTML regex; single-line token grammars (embed directives, the marker comment) may stay regex.
  `_fences` also reads the body of a Python-Markdown block opener (an admonition, a details block, a content tab, a definition, a footnote definition) as that block's content, not as indented code.
- **`_markers.py`** owns the marker-comment contract the post stages share: comment-safe encoding (every `<` and `>` escaped so a payload can never close the comment early, and every backtick escaped so no code span can open inside it), locating markers among `_html` tokens with each marker's block bounds, and fail-soft decode into a strict pydantic payload model. It also owns the emission and pairing helpers `grid` and `tabs` share: `marker_block` (one marker as its own indented block, blank lines around it), `inline_problem_marker`, `match_marker_pairs` (stack-match open and close markers by position), and `report_problem_markers`. `fence`, `grid`, `tabs`, and `annotate` depend on it; it depends only on `_html`.
- **`_containers.py`** owns container pairing: from the source text it returns each pair (kind, opener line, closer line, indentation, opener tokens, whether the nearest enclosing container is a paired grid, and whether its lines were already marker comments), each unpaired or misplaced line with its reason, and each unclosed `[grid ...]` shortcut, skipping fenced and indented code through `_fences`. It holds the opener and closer grammars and the names of the six paired container markers, which `grid` and `tabs` import, so it can read an emitted marker line as the opener or closer it stands for. `grid` (block grids and cards) and `tabs` call it, the second caller that justifies the module; it depends only on `_fences`. Its pairing rules are a self-contained algorithm with a contract of its own, so `tests/test_containers.py` tests it directly, as the `_fences` and `_markers` tests do.
  Column comparison, the less-indented-line rule, and a card's paired-grid test live here.
  The tab sibling rule lives in `tabs.py`, which owns grouping.
- **`tabs.py`** is a marker-comment pre-plus-post pair like `grid`; its post stage builds each set's inputs and labels from that set's `mw-tab` payloads.
- **Extension patterns.** Every extension but `highlight` follows one of three, so a new one needs no new machinery: the embeds, `button`, and `lightbox` are directive-expand pre stages (codepen, twitter, and instagram add a script-injecting post stage); `mermaid` and `icons` are pre-only (a fence rewrite and an inline-processor resolver); `fence`, `grid`, `tabs`, and `annotate` are marker-comment pre-plus-post pairs; `highlight` wraps prose in its pre stage and in-code markers in its post stage, with no marker comment. Their shared helpers are second-caller extractions: `_fences.map_prose` (prose outside fences and inline code, shared by `highlight` and `icons`), and `_html.add_classes` (shared by `fence`, `grid`, and `annotate`); `_html.matching_end` has one caller, `annotate`.
- **`cli.py`** wires config into each subcommand and is the single place exceptions become exit codes (`ConfigError`, or a `ConfigWarning` escalated with `PYTHONWARNINGS=error`, prints `mw: error:` and exits 2).
  Planned (hardening): it sets UTF-8 on stdin and stdout and reports a decode error, a closed stream, or a broken pipe as one `mw: error:` line, and it passes a leading front matter block around `run_pre`; `load_config` and `icons.read_options` turn `OSError` and `UnicodeDecodeError` into `ConfigError` and `OptionError`.

## Success criteria

- `just check` is green: ruff clean, ruff format clean, mypy strict clean, pytest passing, coverage reported.
- `just test-integration` is green: the `mw pre | hugo | mw post` pipeline through a real Hugo build, and a clean-venv wheel install.
- `just docs-build` (strict) is clean and every page in the MkDocs nav exists.
- Rendered output matches the `do-markdownit` reference format for the eight ported extensions; the `mw-fence`, `mw-grid`, container, and `mw-annotate` markers and the `mw-embed` preview stay versioned and read fail-soft.
- Every extension page has its Host CSS and Script section, and every extension's markup reads correctly with the docs site's CSS and JavaScript turned off.
- Every extension renders live on its own docs page: mermaid, lightbox, and annotations through the committed `docs/javascripts/`, icons through the committed icon set, and block grids, cards, and a tab set that switches with the CSS sample alone.
- The `mw pre | hugo | mw post` integration test carries youtube, codepen, twitter, highlight, fence, button, lightbox, mermaid, icons, both annotate forms, the grid shortcut, a block grid with cards, a tab set, and two container problems.
