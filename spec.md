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
- Runtime dependencies are `markdown` (floor `>=3.8.2`, the first version that passes the suite, raised from `>=3.4` in 0.4.0), `pymdown-extensions` (floor `>=11.0.1`, set by a security fix), and `pydantic`; adding another needs a spec change
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
- A diagnostic never changes the rendered HTML or an exit code; it only reports
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

## External tool candidates

Cached by `/bpe:plan` on 2026-11-26 from `bpe:cheap-research`; unverified community listings, none installed in the session, so no plan section declares them.

- mkdocs (jamie-bitflight python3-development) :: MkDocs CLI, mkdocs.yml, Material theme and plugin guidance :: https://www.claudepluginhub.com/skills/jamie-bitflight-python3-development-plugins-python3-development-2/mkdocs
- mkdocs-documentation (kettleofketchup) :: MkDocs docs skill, may cover hooks and strict builds :: https://www.claudepluginhub.com/skills/kettleofketchup-mkdocs-documentation-plugins-mkdocs-documentation/mkdocs-documentation
- mkdocs (julianobarbosa claude-code-skills) :: MkDocs config and usage, overlaps the two above :: https://www.skills.sh/julianobarbosa/claude-code-skills/mkdocs
- python3-development (jamie-bitflight) :: pytest, mutmut, and pytest-mock guidance; overlaps python:python :: https://skills.sh/jamie-bitflight/claude_skills/python3-development
- markdown-linting (melodic-software) :: Markdown linting for authored docs, not scanner internals :: https://www.skills.sh/melodic-software/claude-code-plugins/markdown-linting
- docs-as-code (spjoshis) :: Markdown-to-static-site workflow with an MkDocs layout; low relevance :: https://skills.sh/spjoshis/claude-code-plugins/docs-as-code
- md-docs (paulrberg) :: Markdown docs conventions; low relevance :: https://www.skills.sh/paulrberg/dot-agents/md-docs

## Roadmap / phase log

**Shipped:**
- v1-init: the initial `do-markdownit` port (the eight extensions) and the `mw` pipeline CLI (.ai-sessions/v1-init/)
- v0.1-remediation: the step-55 audit remediation (R1 through R11), shipped as 0.1.0 (.ai-sessions/v0.1-remediation/)
- config-system: the 0.2.0 config system and `mw` CLI simplification, converged (.ai-sessions/config-system/)
- material-parity-0.4.0: the six Material-reference extensions (#16) and the shared `_markers` module, converged and staged for the 0.4.0 release (.ai-sessions/material-parity-0.4.0/)
- fenced-directives-20: `mw pre` leaves a directive line inside fenced code literal across all ten directive stages through `_fences.map_lines` (#20), converged (.ai-sessions/fenced-directives-20/)
- review-fixes-29: the eight 0.4.0 adversarial-review fixes (annotate chaining, tab and indented-code detection, HTML-tag skipping, icons at priority 85, and the test-policy cleanup) (#29), converged (.ai-sessions/review-fixes-29/)
- containers-30: block grids, cards, column counts, and the `tabs` extension on one shared open/close pairing scanner (#30), converged (.ai-sessions/containers-30/)
- material-mapping: the Material mapping docs page, `docs/material-mapping.md`, listing what gives each Material reference feature in-process and under Hugo, with the gaps; docs-only, Step 29 of the fix plan (.ai-sessions/fix-plan-0.4.0/)
- fix-plan-0.4.0: the 26-step 0.4.0 fix plan (container postprocessor priority, the containers fixes, block bodies, pre-stage order, #31, #32, #33, #34, annotate overlap, hardening, and the docs catch-up), converged (.ai-sessions/fix-plan-0.4.0/)
- 0.4.0 release: PR #35 merged on 2026-11-22 and tagged `v0.4.0`; done by hand, outside the bpe loop, since `pyproject.toml`, `uv.lock`, and the workflows are outside `paths:`; version 0.4.0, the `markdown` floor at `>=3.8.2`, and the dev dependency `mkdocs>=1.6,<2`; it closes #16, #20, #29, #30, #31, #32, #33, and #34

**Upcoming:**
- polish-gaps: close every remaining `Known gap` and the polish findings, on branch `polish-gaps` stacked on PR #39: in-process diagnostics as `Diagnostic` records that name the true source line, the docs-site MkDocs hook for strict mode, multi-line comment regions, markwright syntax inside raw HTML blocks, embeds and marked fences as their own blocks, highlighter attributes beside a prefix flag, line-number tables, and line prefixes around wrapping spans; it ships when spec.md holds no `Known gap` sentence
- Bartleby follow-up to 0.4.0, in the Bartleby repo: `selected_extensions` with no `enable` list goes from eight names to fifteen and Bartleby pins the eight in a test, and its private imports move to the public `disallowed_environments`

**Deferred:**
- New embeds (Bluesky, Mastodon, Vimeo): possible later; each should support the `load` option when it lands
- User-level config layer (`~/.config/markwright/`): project-level config only for now
- `youtube-nocookie` option: reduces tracking even for `eager`; worth a separate issue
- `mw-` rename of the existing embed CSS classes: align them with the `mw-embed` preview hooks; nothing blocks it before 1.0, but it is a separate concern from the containers phase
- Richer Material-parity features past the 0.4.0 contracts: lightbox galleries, captions, and `srcset`; annotation forms beyond a block plus its following list; each 0.4.0 extension stays minimal, revisit per issue
- Grid extras: card column spans (`[card 2]`), per-breakpoint column counts (`[grid 1 2 3]`), and config defaults for columns, gap, or minimum width; revisit per issue
- Tab extras: a marker that selects a tab other than the first, and one that forces a new set right after another; revisit when a page needs either
- Move the docs site to Bartleby: once Bartleby reaches parity and releases, before May 5, 2027; the docs keep loading markwright's own CSS and JavaScript samples through Bartleby's `extra_css` and `extra_js`, so the samples stay exercised
- Full `mw pre` idempotence for a document with container problems: a line that already carries a problem marker is not read as a directive on a second pass, so a `[card]` outside a grid leaves its `[/card]` to gain a stray-closer report, and a `[grid]` left literal by a stray `[/grid]` is read as the list shortcut; a valid document is unaffected, revisit if a pipeline runs `mw pre` twice
- pymdown-extensions 13.x: checked on 2026-11-16 by the plan review (markwright's suite passes on 13.0 and 13.1 with `mw render` byte-identical to 12.2, and Bartleby's suite gives the same result on 13.1 as on 12.2); re-check when a release past 13.1 appears
- Fence marker binding: bind an `mw-fence` marker only to a `<pre>` that follows it with nothing but whitespace between; every case that differs needs a fence the renderer failed to render, unchanged since 0.1.0
- `[button]` argument checks: a style word followed by one token reads the style word as the URL; it needs an author mistake and is visibly wrong on the page
- Pre-stage scan cost: the fence and indented-code scan runs once per stage and is quadratic for a document of unclosed fence openers, and two directive regexes backtrack on a line of thousands of spaces; ordinary documents scale linearly (about 0.09 s for the 25 pages under `docs/` on the development machine, measured by timing `run_pre` over each page, with the result of a scan remembered per document so stages that leave the text unchanged share it); a stage that rewrites the text still makes the next stage scan it again, and one scan per `run_pre` shared by every stage is the fix, and a host that renders untrusted Markdown should know before 1.0
- Parser hygiene (cut from the 0.4.0 plan on 2026-11-20): no abbreviated long options, the missing-subcommand usage on stderr, `--config ""` as an error, and the source named in every no-op warning; none changes a correct invocation
- Hardening for input no author types (cut from the 0.4.0 plan on 2026-11-20): one integer helper for directive and annotation integers, and `decode_marker` skipping a payload no JSON reader accepts; each needs a digit string past 4,300 characters, a non-ASCII digit, or a marker comment edited by hand, and ends the stage in a traceback today; revisit if a host renders untrusted Markdown
- A MkDocs plugin in the package: the docs site's hook (`docs/hooks/markwright.py`) is the worked example of routing `RenderWarning` into MkDocs' logger for `--strict`; a plugin needs an entry point in `pyproject.toml` and ties markwright to MkDocs, which reaches end of life on May 5, 2027; revisit if a second MkDocs host asks
- Release pipeline hygiene: actions pinned by SHA, protection rules on the `pypi` environment and on `main`, a tag-equals-version check in the publish workflow, and the `Typing :: Typed` classifier; none changes what installs or runs

## Goals

Goals describes markwright as it behaves today, one entry per feature, and is the first place to look for what exists.
A sentence that starts `Planned (ITEM):` is behavior the named Roadmap Upcoming item will build; it is not built yet, and it loses the prefix when the item ships.
A sentence that starts `Known gap:` is a place where the code or the docs fall short of the entry, with the Upcoming item or issue that covers it.
A gap is recorded only when a document an author is likely to write reaches it; input no author writes is not listed.
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
| highlight | ported | Released 0.1.0 | polish-gaps | `extensions/highlight.md` | `highlight.py` |
| fence | ported | Released 0.1.0 | polish-gaps | `extensions/fence.md` | `fence.py` |
| youtube | ported | Released 0.1.0 | polish-gaps | `extensions/youtube.md` | `youtube.py` |
| codepen | ported | Released 0.1.0 | polish-gaps | `extensions/codepen.md` | `codepen.py` |
| twitter | ported | Released 0.1.0 | polish-gaps | `extensions/twitter.md` | `twitter.py` |
| instagram | ported | Released 0.1.0 | polish-gaps | `extensions/instagram.md` | `instagram.py` |
| slideshow | ported | Released 0.1.0 | polish-gaps | `extensions/slideshow.md` | `slideshow.py` |
| image_compare | ported | Released 0.1.0 | polish-gaps | `extensions/image-compare.md` | `image_compare.py` |
| `mw` CLI | own | Released 0.1.0 | polish-gaps | `cli.md`, `pipeline.md`, `renderer-requirements.md` | `cli.py`, `registry.py` |
| config | own | Released 0.2.0 | none | `config.md` | `config.py` |
| host API | own | Released 0.3.0 | polish-gaps | `config.md` | `config.py`, `__init__.py` |
| click-to-load | own | Released 0.3.0 | none | `click-to-load.md` | `_embed_load.py` |
| button | own | Released 0.4.0 | polish-gaps | `extensions/button.md` | `button.py` |
| lightbox | own | Released 0.4.0 | polish-gaps | `extensions/lightbox.md` | `lightbox.py` |
| mermaid | own | Released 0.4.0 | polish-gaps | `extensions/mermaid.md` | `mermaid.py` |
| icons | own | Released 0.4.0 | polish-gaps | `extensions/icons.md` | `icons.py` |
| annotate | own | Released 0.4.0 | polish-gaps | `extensions/annotate.md` | `annotate.py` |
| grid and cards | own | Released 0.4.0 | polish-gaps | `extensions/grid.md` | `grid.py`, `_containers.py` |
| tabs | own | Released 0.4.0 | polish-gaps | `extensions/tabs.md` | `tabs.py`, `_containers.py` |

### Rules Every Feature Follows

- Every extension is on by default.
  A new extension is additive: it claims only its own syntax, so a document that contains none of it renders as before.
  A document that happens to contain the new syntax renders differently, and the CHANGELOG's upgrade notes name each case.
- A directive is a whole line: `[name ...]` alone on its line.
  The same text inside a sentence, or a line with fewer tokens than its required arguments, stays literal with no report; a `[button]` line whose style word is followed by one token reads the style word as the URL.
- Code is not prose.
  A directive line or an icon shortcode inside a fenced code block or a top-level indented code block stays literal, found through `_fences`.
  A fenced block behind block quote markers (`> `, as in a `> [!NOTE]` alert) is found too: every line through its closing fence carries the opener's markers, and a quote that ends first leaves the fence unclosed.
  Highlight is the deliberate exception: its markers work inside code, through its post stage.
  The body of an admonition (`!!!`), a details block (`???`, `???+`), a content tab (`===`), a definition (`:`), or a footnote definition (`[^name]:`) is not indented code: `_fences` reads the lines indented four columns under such an opener as that block's content, the way it reads a list item's, so a directive line and a fence with its directives inside the body work, and a line indented four columns further after a blank line is still code.
  A `mermaid` fence in such a body is converted on a best-effort basis, as the Mermaid entry says.
  The rule lives in `_fences`, so both paths apply it, and an expanded line keeps its indentation, so the result stays inside the block; `tests/test_roundtrip.py` covers each of the five bodies with `admonition`, `def_list`, `footnotes`, `pymdownx.details`, and `pymdownx.tabbed` loaded in both paths.
  The openers follow the grammars of Python-Markdown's `admonition` and `footnotes` and of `pymdownx.details` and `pymdownx.tabbed`: `!!! note`, `!!!note`, `??? note`, `???+ "Title"`, `=== "Tab"`, `===+ "Tab"`, `===! "Tab"`, and `[^name]:` open a body, while `=== Tab` (no quotes), `!!! "Title"` (no class), and `!!! note: text` do not.
  An admonition, details, or content-tab opener counts only at the column of the block that holds it (column 0 at the top level, an item's content column under a list item, which is four columns for an item indented 0 to 3 columns, and another opener's body column inside an opener's body), as in Python-Markdown; a footnote definition counts at the top level, up to three columns in, and a definition counts up to three columns in at the top level or inside an opener's body, not inside a list item.
  The body starts at the holding block's column plus four, and a line four columns further after a blank line is code.
  A definition (`: text`) needs a line before it, since extra `def_list` reads a leading colon line as a paragraph; markwright does not check that the preceding line is a term, and it does not read `md_in_html` or `attr_list` blocks.
  A directive's expansion starts every line at the directive line's indentation, which keeps it in the body in-process; a directive at column 0 expands byte-identically.
  `mw pre` follows the opener, since a document that carries `!!!`, `???`, or `===` is written for a renderer that reads them; under a CommonMark renderer with no such extension the body is indented code, and an expanded directive there shows as code text.
  Planned (polish-gaps): a multi-line HTML comment is a region every stage skips, as CommonMark's HTML block reads a comment: a line that starts, after up to three columns of indentation, with `<!--` and holds no `-->` opens it, and the first later line that holds `-->` closes it.
  A directive, a fence, a highlight marker, or an icon shortcode inside it stays as the author wrote it, in both paths, so commented-out text stays commented out.
  A comment that closes on its opening line is not a region, so the marker comments markwright emits keep being read.
  Today `mw pre` writes a tab, grid, or annotate marker inside the author's comment, the marker's `-->` ends that comment, and the commented-out text is published; for a fence directive the in-process path does the same.
- Raw HTML is not a barrier.
  Planned (polish-gaps): markwright syntax works inside a raw HTML block the author wrote (a `<div>` and its content), in both paths, as containers already do: a directive line expands, and a highlight pair or an icon shortcode in the text between tags renders.
  In-process the directive preprocessors run ahead of Python-Markdown's `html_block` (20), at 21 beside grid and tabs, and the highlight and icons source transforms run over the lines of a raw HTML block, which the inline processors never see.
  In-process a block runs through its matching closing tag, as Python-Markdown reads it, and through `mw pre` through the first blank line, as CommonMark reads it; the markwright markup agrees in both paths, and what each renderer does with plain text after a blank line inside a block stays the renderer's.
  The highlight pre stage skips HTML tags, comments, and autolinks, as the icons pre stage does, so a marker inside a tag's attribute never breaks the tag.
  An embed inside a raw HTML block gains no blank line around it, since under CommonMark a blank line ends the block and turns the lines after it into Markdown.
  Planned (polish-gaps): a `<pre>`, `<script>`, `<style>`, or `<textarea>` block (CommonMark's first HTML block kind, which runs through its closing tag in both renderers) is verbatim content: every pre stage skips it, in both paths, the way it skips fenced code, so a block the mermaid stage emitted keeps its text with no rule of its own.
  Today a directive line inside a raw HTML block expands through `mw pre`, and in-process only when it is a `[grid]`, `[card]`, or `[tab]` container line; a highlight pair or a shortcode in one renders through `mw pre` and stays literal in-process; the highlight pre stage rewrites a pair inside a tag's attribute; and the icons pre stage skips only a block that opens with exactly `<pre class="mermaid">`.
- Two paths give one result: the in-process Python-Markdown render and `mw pre | renderer | mw post` produce the same HTML for the same source apart from blank lines between blocks, and `tests/test_roundtrip.py` asserts it after dropping blank lines outside `<pre>`, a hypothesis property over markwright's grammar included.
  Where the two paths differ on a document an author is likely to write, the entry says so under `Known gap`.
- A pre stage that needs its post stage hands data over in a marker comment, `<!-- NAME:{JSON} -->`, with `"version": 1` in the payload.
  A marker is read fail-soft: malformed JSON, a non-object payload, an unsupported version, a wrongly typed field, or no `<pre>` or `<code>` element before the next marker is skipped and reported under `--warn`, and unknown fields are ignored.
- markwright emits markup only.
  The markwright-own extensions exist so a host theme can render every feature on the mkdocs-material reference from markwright markup alone; that is the scope test for another one.
  Each extension's docs page has a Host CSS and Script section listing the classes, data attributes, and ids a host styles, and a page whose extension needs neither says so.

### Highlight

- `<^>text<^>` becomes `<mark>text</mark>` in prose, in inline code, and in fenced code, the places `pymdownx.mark` cannot reach.
- In code, inline or fenced, a marker pairs with the next marker on the same line, a line can hold several pairs, and a pair never spans lines.
- In prose a marker pairs with the next prose marker on the same line, in both paths, so a pair never holds a line end; a pair may hold an inline code span: ``a <^>b `x` c<^> d`` marks `b` through `c`, code span included.
  A marker inside a code span never opens or closes a prose pair, in-process or in `mw pre`, which leaves it literal; `mw post` then reads it as an in-code marker.
  In-process the inline processor matches an opener alone and searches for its closer on the same line; with no closer there the opener stays literal and matching resumes just after it, and a pair whose text holds a stashed block's placeholder is declined the same way.
  `mw pre` wraps everything between a same-line pair in one `<mark>`, code spans included; a code span is followed across a line end, never across a blank line, when deciding what is inside one, so a span that holds a line end does not end the line, as in-process, where the span is already a placeholder when highlight runs.
  The tests are differential: over a corpus of two-line and three-line documents generated from the block starts of both renderers, the in-process render, the stub pipeline (`tests/test_roundtrip.py`), and the Hugo pipeline (`tests/integration/`) highlight the same text.
  Decision (2026-11-16): prose pairing departs from `do-markdownit`, which pairs across a soft line break; a pair that crosses a line end has no single meaning under Python-Markdown and CommonMark, and the plan review measured a paragraph-end test at 294 path differences over 1,133 generated documents against none for the same-line rule; the CHANGELOG's upgrade notes name the pairs that stop highlighting.
- `\<^>` renders a literal marker in all three contexts and in both paths.
  Inside a code block the post stage reads markers and escapes from the text of each rendered code line, tags ignored, so a marker pairs and a backslash escapes it whatever tags sit between or inside them, under Pygments and under Chroma.
  Exactly one backslash is removed for an escape, a paired marker's characters are removed, and every tag stays where it is, so a `<span>` that held only a backslash or part of a marker remains, empty; a revealed literal marker is written `&lt;&#94;&gt;`, so a second `mw post` leaves it alone.
  In prose `mw pre` reads the backslashes before a marker in pairs: an odd run escapes the marker, and `mw pre` then adds one backslash and writes the marker's `<` as `&lt;`, so Python-Markdown and a CommonMark renderer both hand `mw post` the escaped form; an even run leaves the marker live, as the in-process path already reads it.
- The pre stage wraps prose markers only, outside fenced code, indented code, and inline code spans.
  Planned (polish-gaps): it also skips HTML tags, comments, and autolinks, and works inside a raw HTML block, by the raw HTML rule under Rules Every Feature Follows.
  The post stage reads the escaped `&lt;^&gt;` form from text tokens only (never an attribute, a `<script>`, a `<style>`, a `<title>`, or a `<textarea>`, whose content a browser shows as characters) and wraps each text run between a pair on its own, so a `<mark>` never crosses a syntax-highlight `<span>`.
- It takes no options.

### Fence

- Directives are the first lines inside a fence: `[label TEXT]`, `[secondary_label TEXT]`, and `[environment NAME]`.
- Prefix flags go in the info string, comma-separated, with the language before or after them (`line_numbers,python`): `line_numbers`, `command` (a `$` prefix), `super_user` (a `#` prefix), and `custom_prefix(TEXT)` with `\s` for a space.
  The last three set the language to `bash` when the info string names none.
  Planned (polish-gaps): the info string splits at its first space or `{`: before it are the comma-separated language and flags, and the rest passes through untouched, so a highlighter attribute keeps working beside a flag; `command hl_lines="1"`, `command title="x.sh"`, and Hugo's `command {hl_lines=[1]}` all give the `$` prefix, and `mw pre` writes `bash hl_lines="1"`.
  Today the whole string is split on commas, so a flag followed by an attribute is not read: the prefix is dropped in both paths, and under Hugo the flag is also taken as the language, which turns syntax highlighting off.
- Output: `<div class="code-label" title="TEXT">` before the block, `<div class="secondary-code-label" title="TEXT">` inside the `<code>`, `environment-NAME` on the `<pre>`, and for a prefix `prefixed TYPE` on the `<pre>` with each line wrapped in `<ol><li data-prefix="...">`.
- Directives work in every closed fence `_fences` finds (indented up to three columns, inside a list item, or behind block quote markers); an unclosed fence is read as prose, so its directives stay text.
  For a fence behind block quote markers `mw pre` writes the marker comment behind the same markers, with a blank quoted line (`>`) on each side, so it stays inside the quote and outside the paragraph before the fence under Python-Markdown and under a CommonMark renderer.
  Planned (polish-gaps): a fence that gains a marker is always its own block: when the line before the marker is not blank, the pre stage writes a blank line there (empty, or the bare quote markers for a quoted fence), in both paths, so a fence directly under a tight list item's text stays in that item and the item renders loose, as Hugo already renders it; a list with no marked fence stays tight.
  Today, in-process, such a fence ends the list at that item.
- Options: `allowed_environments` (omitted allows every name; an empty list allows none and warns; an unlisted `[environment NAME]` line stays in the code as text), `label_class`, and `secondary_label_class`.
  Planned (polish-gaps): an unlisted environment is reported: the `mw-fence` marker carries `disallowed_environment` with the name (a fence with nothing else to carry gets a marker with only that field), still version 1 since unknown fields are ignored, and the post stage reports it in both paths.
  Today no path reports it, and a host gets the names from `disallowed_environments`.
  `label_class` and `secondary_label_class` accept space-separated class tokens of letters, digits, `-`, and `_`; any other value is a `ConfigError`, or an `OptionError` in-process.
  `fence.py` exposes the scan (`environment_names`) that lists the environment names a document's fence directives name, by the same rules the pre stage extracts them with; the host API function below is built on it.
- The `mw-fence` marker (version 1: `label`, `secondary_label`, `environment`, `prefix_type`, `prefix_value`, each present only when set) sits before the fence at the fence's indentation, followed by a blank line when the fence is indented.
  A `line_numbers` flag that replaces an earlier `command`, `super_user`, or `custom_prefix` drops `prefix_value`.
  The fence itself is kept, so the renderer still highlights the code, and the post stage styles the first `<pre>` or `<code>` after the marker and before the next one, however far away, an inline code span included.
- Line prefixes handle two renderers: Pygments emits flat newline-delimited lines, and Chroma (Hugo) wraps each line in `<span class="line">` when `noClasses = false`.
  A Chroma line that already ends with a newline gains no second one.
  Planned (polish-gaps): a line ends at its newline plus the closing tags right after it, so a span the highlighter wraps around a whole line (Pygments `hl_lines` and `line_spans`, Chroma with Hugo's default `noClasses = true`) stays inside that line's `<li>`, and no empty prefixed line is added.
  Today the wrap cuts such a span, which closes in the next `<li>`, and one empty prefixed line is added.
  Planned (polish-gaps): with line numbers in a table (`linenums` under Pygments, `lineNos = true` under Hugo) the marker skips the gutter cell (`td.linenos`, or Chroma's first `td.lntd`) and binds to the code `<pre>` in the same table, so the classes and the prefixes land on the code; the label sits before the table.
  An inline line-number layout (Pygments `linenums_style` `inline` or `pymdownx-inline`, Hugo `lineNumbersInTable = false`) keeps each number in its line's `<li>`, so a prefixed line shows its prefix, its number, and its code.
  Today the marker binds to the gutter `<pre>`, so the classes and the prefixes land on the line numbers.

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
- Planned (polish-gaps): an embed is always its own block: when the line before or after an embed line is not blank, the pre stage adds a blank line there, in both paths, so the embed splits the paragraph, list item text, or heading it sat beside, and under a CommonMark renderer the lines after it render as Markdown; inside a raw HTML block no blank line is added, by the raw HTML rule under Rules Every Feature Follows.
  The expansion itself is unchanged, so `eager` output for an embed line that already had a blank line on each side stays byte-identical, and a tight list item that holds an embed renders loose.
  Today an embed line with no blank line around it renders inside the neighboring paragraph, list item, or heading in-process and as its own block through `mw pre`, and under a CommonMark renderer the lines after it up to the next blank line are raw HTML.
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
- It runs ahead of fence and `pymdownx.superfences`, so a `custom_fences` mermaid entry in the host config is inert for the fences markwright converts; a `mermaid` fence it does not convert (behind block quote markers, where it stays a code block) still reaches that entry.
  `mw pre` emits the `<pre>` inline as raw HTML, with the fence's indentation before every line of it and a blank diagram line left empty.
  In-process, a fence indented four or more columns is replaced by a line holding a random token and stashed below Python-Markdown's whitespace normalizer, so the `<pre>` holds the exact diagram text with no indent and a blank line in the diagram does not split it.
  `_fences` reads a fence that deep as a fence under a line it reads as a list marker or in a block opener's body (Rules Every Feature Follows says which four-column lines it reads as content).
  In a list item or an opener's body Python-Markdown wraps raw `<pre>` lines left that deep in a paragraph or splits them at a blank line, which is why the fence is stashed.
  A fence indented fewer than four columns, one under a list item included, is emitted inline in-process, the same text `mw pre` emits, so a diagram at column 0 is its own block beside a paragraph line or a table.
  A mermaid fence is supported at the top level only, at column 0 with a blank line before and after; a fence in a list item or inside another block is converted on a best-effort basis and its output is not specified.
- The host loads mermaid.js; markwright ships none.

### Icons

- `:PACK-NAME:` in prose inlines an SVG as `<span aria-hidden="true" class="mw-icon"><svg>...</svg></span>`.
- The `packs` option maps a prefix to a directory of SVG files the host supplies; markwright ships no icons.
  `:lucide-check:` reads `check.svg` from the `lucide` pack, a file in a subdirectory joins its path parts with hyphens, and prefixes match longest first.
- Anything before the `<svg` tag in a file is dropped and the markup is joined onto one line; in-process the SVG is otherwise unchanged, and through `mw pre` the renderer parses Markdown in its text content, a `<title>` included.
- A shortcode that names no pack or no file stays literal text.
- Shortcodes resolve in prose only: never in fenced code, indented code, an inline code span, or an HTML tag, and `mw pre` also leaves a diagram that the mermaid stage emitted alone (a line that starts with exactly `<pre class="mermaid">`, through the first `</pre>` after it; text after the tag on that line is prose), since in-process the diagram is stashed, by markwright or by Python-Markdown's own raw HTML pass, and never read.
  The icons pre stage runs after every directive stage, so a shortcode inside a `[button]`, `[lightbox]`, `[tab]`, or embed line gives what the in-process render gives, and a converted `mermaid` diagram keeps its shortcode text.
  Planned (polish-gaps): this rule becomes the verbatim-block rule under Rules Every Feature Follows, which skips every `<pre>` block, so the stage needs no mermaid tag of its own and the Decision below is deleted when the item ships.
  Decision (2026-11-20): `mw pre` reads a block that opens with the mermaid stage's tag as a CommonMark renderer reads it, as raw HTML through the first `</pre>` with no fence line inside it read as a fence, so under Hugo a shortcode after the block renders as an icon whatever the block holds; under a Python-Markdown renderer with a fenced code extension, which reads a fence line inside the block as a fence, an author-written block that holds one does not match the in-process render.
- A relative pack path resolves against the directory `mw` or the host runs from.
- With `packs` omitted the extension does nothing, an empty `packs` warns, and a `packs` that is not a table, a path that is not a string, or a directory that does not exist is a boundary error.
  An SVG file that cannot be read or is not UTF-8 is a boundary error that names the file.

### Annotate

- `[annotate]` before a block links each `(N)` marker in the block to the N-th item of the ordered list after it: `<a class="mw-annotation" href="#mw-annotation-B-N">N</a>`, where B counts annotated blocks in the document.
  In highlighted code a marker is linked only where the highlighter keeps `(N)` in one text run, in practice inside a comment; in an unhighlighted block every `(N)` is linked, a call such as `compute(1)` included.
- The block gains `mw-annotated`, and the list gains `mw-annotations`, `data-mw-version="1"`, and an `id="mw-annotation-B-N"` on each item.
- In code, the `# (1)!` form strips the comment token around the marker (Pygments in-process, Chroma through Hugo with `noClasses = false`); a highlighter that emits no comment class, Hugo's default inline styles included, degrades to the plain form.
  When a comment token holds a `!` marker, the comment is replaced by the links for every valid marker in it, in order and separated by a space, and `_html.apply_edits` refuses overlapping spans with an exception.
- It travels as an `mw-annotate` marker comment, and its post stage runs ahead of fence's so the fence marker is still a comment when the block is located.
- With no host script the result is a numbered list under the block; tooltips are host work.
- The classes and the `mw-annotation-B-N` id scheme are a public contract.

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
  The payload is `version` 1, the 1-based `line` in the source (through the line map under Config and the Host API), the `directive`, and a `reason` from a closed vocabulary (`unclosed`, `stray-closer`, `card-outside-grid`), so a marker that decodes puts only fixed text on stderr; a marker that fails to decode is reported on one line with its payload shown through `repr`, which escapes control characters.
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
  `mw` reads and writes UTF-8 whatever the locale or `PYTHONIOENCODING` says, and input that is not UTF-8 is one `mw: error:` line and exit 2.
  `mw pre` passes a leading YAML (`---`) or TOML (`+++`) front matter block through untouched: the block starts on the first line and ends at the next line that is the same delimiter, and a first line of `---` with no closing line is read as Markdown.
- `mw pre` runs every selected extension's source stage, and `mw post` runs every HTML stage, in the registry's priority order, which mirrors the in-process order; CLAUDE.md, Processor Priority Reference, holds the full table.
- `mw post` is complete on its own: it needs no marker to inject a provider script, and running it twice neither double-injects a script nor double-wraps a mark.
- `mw render` is the one-shot in-process path: a `markdown.Markdown` with `pymdownx.superfences`, `pymdownx.highlight`, and the selected extensions, and no other extension, so it renders no admonitions and no `md_in_html`; its syntax highlighting needs Pygments, which markwright does not depend on.
- `mw config` prints the resolved configuration and the source of every value, `mw list` prints each extension and its stages and takes no flags, and `mw --version` prints the version.
- Flags on `pre`, `post`, `render`, and `config`: `--config PATH` loads exactly that file, and `--exclude NAME` (repeatable, applied last) drops an extension.
  `--warn` (`post` and `render`) writes advisory diagnostics to stderr without changing the output or the exit code.
  `mw post` and `mw render` take the config key `warn` as the default for their diagnostics; `--warn` turns them on and `--no-warn` turns them off, whatever the config says, and the last of the two on the command line wins.
  The pair exists on `mw post` and `mw render`, and `mw config` shows the resolved value and its source.
  The diagnostics are stderr lines that `PYTHONWARNINGS=error` does not escalate: plain lines from `mw post`, and `mw: warning:` lines from `mw render`, where each is a `RenderWarning`.
  The in-process path reports the same diagnostics: each post stage hands every problem to one `report` call, which appends a `Diagnostic` to `md.markwright_diagnostics` (a fresh list for each non-blank document, reset with the `Markdown` instance; Python-Markdown returns before any preprocessor runs on a blank document, so a reused instance keeps the earlier entries until `md.reset()`) and calls `warnings.warn` with a `RenderWarning` that carries it, so the list is the record and the warning is a side effect of the same call.
  `mw render` prints each `RenderWarning` as one `mw: warning:` line only when the diagnostics are on, while a host that runs with warnings as errors gets the exception it asked for.
  Python's default warning filter shows an identical message once per location, so a host that wants every report from a multi-page build reads the list or sets the `always` filter for `RenderWarning`; the docs say so.
- Exit codes: 0 on success, an empty selection included; 2 on a config error, with one `mw: error:` line, and on a usage error, with argparse's usage text; for `mw pre`, `mw post`, and `mw render`, a decode error, a closed stream, a broken pipe, and an unreadable icon file are each one `mw: error:` line and exit 2, as is an unreadable or non-UTF-8 config file, so no input to those three ends in a traceback; `mw list` and `mw config` write with plain `print`, so a broken pipe on them is not covered.
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
- The options that exist: `fence.allowed_environments`, `fence.label_class`, `fence.secondary_label_class`, `load` on youtube, codepen, twitter, and instagram, and `icons.packs`.
- Every setting follows the config law in Invariants and in `docs/config.md`, Config Rules.
  A `ConfigError` names the extension, the key, and the source; the Python-Markdown path raises `OptionError` (a `ValueError` subclass) for the same bad value.
  A config file that cannot be read or is not UTF-8 is a `ConfigError`.
- The host API, re-exported from the package root, lets a host tool carry a markwright table in its own config file: `config_from_mapping(table, source)` validates a parsed table with the same rules as a file, `selected_extensions(config)` applies `enable` and `disable` (an empty selection warns and returns an empty list), and `extension_configs(config, names)` builds the `markwright.<name>` option dicts for `markdown.Markdown`.
  `mw render` builds its own `Markdown` through `selected_extensions` and `extension_configs`.
- Planned (polish-gaps): a `Diagnostic` is a frozen record of `extension`, `line`, `directive`, `reason`, and `message`, and the package root re-exports it with `RenderWarning`; `mw post --warn` prints each one's `message`.
  `reason` comes from a closed vocabulary listed on the CLI docs page: the container reasons `unclosed`, `stray-closer`, and `card-outside-grid`, one reason for each other problem a post stage reports today, and `disallowed-environment`; `directive` is the directive as written, or `None` for a problem with no directive.
- `line` is the 1-based line in the text the author wrote: for `mw`, the input file with its front matter block counted; in-process, the text handed to `convert()`, so a host that strips front matter itself adds that block's length.
  `run_pre` keeps a line map through the stages (`rebase_marker_lines`), so a line an earlier stage added above a problem never shifts it; in-process, the preprocessor that resets the diagnostics also keeps the source lines for grid and tabs to rebase against.
  A problem only the post stage can see (a malformed marker, a marker with no block after it) has `line` `None`.
- The public names are `Config`, `ConfigError`, `ConfigWarning`, `OptionError`, those three functions, and `disallowed_environments`; `load_config` is not public, and Bartleby is the first consumer.
  `disallowed_environments(source, config)` returns each environment name a fence directive names outside `fence.allowed_environments`, once each, in order of first appearance.
  It scans with fence's own rules (a directive counts only among a fence's leading lines, label and secondary-label lines are skipped, and a directive inside a nested fence's source is code), with two stated additions: a disallowed environment line does not end the scan of that fence, so each disallowed name among the leading lines is reported although fence stops reading directives at the first; and a `mermaid` fence is skipped when `mermaid` is selected, since that stage replaces the fence before fence reads it.
  A name is everything after the first space of the directive, compared as written.
  It returns an empty list when `allowed_environments` is omitted or when `fence` is not selected, emitting no warning, its own or from the option and selection readers it calls; with an empty allowlist it reports every name; whether to print the result stays the host's decision.
  The tests call it under `warnings.simplefilter("error")` with an empty allowlist and with an empty selection, and cover two environment lines one after the other, a `mermaid` fence with `mermaid` selected and excluded, and a name with padding.
  `config_from_mapping` raises `ConfigError` with the source label for a table that is not a mapping, reads `None` as an empty table, and checks key names before it drops `None` values, so an unknown key is an error whatever its value.

### Docs Site

- The MkDocs Material site in `docs/` documents and demonstrates every feature: one page per extension with its usage, its syntax, rendered examples, the HTML and marker contracts where the extension has them, and a Host CSS and Script section.
  The grid page leads with a block-grid demo and the tabs page with a tab-set demo.
- It is also the worked host example: `docs/stylesheets/extra.css`, `docs/javascripts/` (a pinned mermaid.js from a CDN, the lightbox `<dialog>`, the annotation tooltips), and two small, credited, liberally licensed icon packs (`lucide` and `mw`) under `docs/icons/`.
  None of it ships in the package.
- The reference pages are Configuration, Click-to-Load, the CLI reference, the Pipeline Guide, Renderer Requirements, the MkDocs and Hugo integration guides, the Material Mapping page (each Material reference feature against its in-process and Hugo providers, with the gaps), and the Demo page.
- `just docs-build` (strict) is the gate for it.
  Planned (polish-gaps): `docs/hooks/markwright.py`, loaded through `hooks:` in `mkdocs.yml`, sends each `RenderWarning` to the `mkdocs.plugins.markwright` logger at WARNING with the `always` filter, so `mkdocs build --strict`, and with it `just docs-build`, fails on a markwright diagnostic; the MkDocs integration page documents the hook as the host example, and no docs page renders a live problem.
  Today MkDocs logs a Python warning at INFO with a traceback, which `--strict` does not count.

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
- Bundle or depend on an icon set, or ship SVG or other assets in the package.
  The icons extension resolves against directories the host supplies.

## Component boundaries

- **Two consumers over one set of pure stage functions.** Each extension module exposes `expand_source` (the `mw pre` source stage) and, where it has one, `apply_html` (the `mw post` HTML stage). The in-process Python-Markdown `Extension` classes and the `mw` CLI both delegate to these, so the logic is written once.
- **`config.py`** owns discovery, parsing, validation, the resolved `Config` (a frozen pydantic model), and the public host API. It depends on `registry` (`EXTENSION_NAMES`, `OPTION_NAMES`, `REGISTRY`), `_diagnostics` (`ConfigWarning`, `OptionError`), and `fence` (the environment scan behind `disallowed_environments`), and nothing else; never on `cli`.
  `disallowed_environments` lives here with the other host API functions and calls the scan `fence.py` exposes, so `config` imports `fence` and `fence` never imports `config`.
- **`registry.py`** maps each extension name to a pydantic `StageSpec` (stage functions, priorities, the extension class, its option checker) and provides `run_pre`, `run_post`, and `describe`. Selection lives in `config.selected_extensions`; there is no `registry.select_extensions`.
  `run_pre` keeps the line map from each stage's input back to the source, through `StageSpec.line_markers`, so a stage writes the source line into a problem marker.
- **`_diagnostics.py`** owns `ConfigWarning` and `OptionError`.
  Planned (polish-gaps): it also owns `Diagnostic`, `RenderWarning`, and the one `report` function every in-process post stage calls; it depends on nothing in markwright.
- **`_fences.py`** (CommonMark fenced-code scanning) and **`_html.py`** (offset-preserving tokenizing over the stdlib `html.parser`) own structured-text parsing. No stage hand-rolls Markdown-structure or HTML regex; single-line token grammars (embed directives, the marker comment) may stay regex.
  `_fences` also reads the body of a Python-Markdown block opener (an admonition, a details block, a content tab, a definition, a footnote definition) as that block's content, not as indented code.
  Planned (polish-gaps): it also finds multi-line comment regions and raw HTML blocks, the verbatim kind every pre stage skips and the other kind the in-process transforms read.
- **`_markers.py`** owns the marker-comment contract the post stages share: comment-safe encoding (every `<` and `>` escaped so a payload can never close the comment early, and every backtick escaped so no code span can open inside it), locating markers among `_html` tokens with each marker's block bounds, and fail-soft decode into a strict pydantic payload model.
  It also owns the emission and pairing helpers `grid` and `tabs` share: `marker_block` (one marker as its own indented block, blank lines around it), `inline_problem_marker`, `match_marker_pairs` (stack-match open and close markers by position), and `report_problem_markers`.
  `fence`, `grid`, `tabs`, and `annotate` depend on it; it depends only on `_html`.
- **`_containers.py`** owns container pairing: from the source text it returns each pair (kind, opener line, closer line, indentation, opener tokens, whether the nearest enclosing container is a paired grid, and whether its lines were already marker comments), each unpaired or misplaced line with its reason, and each unclosed `[grid ...]` shortcut, skipping fenced and indented code through `_fences`.
  It holds the opener and closer grammars and the names of the six paired container markers, which `grid` and `tabs` import, so it can read an emitted marker line as the opener or closer it stands for.
  `grid` (block grids and cards) and `tabs` call it, the second caller that justifies the module; it depends only on `_fences`.
  Its pairing rules are a self-contained algorithm with a contract of its own, so `tests/test_containers.py` tests it directly, as the `_fences` and `_markers` tests do.
  Column comparison, the less-indented-line rule, and a card's paired-grid test live here.
  The tab sibling rule lives in `tabs.py`, which owns grouping.
- **`tabs.py`** is a marker-comment pre-plus-post pair like `grid`; its post stage builds each set's inputs and labels from that set's `mw-tab` payloads.
- **Extension patterns.** Every extension but `highlight` follows one of three, so a new one needs no new machinery: the embeds, `button`, and `lightbox` are directive-expand pre stages (codepen, twitter, and instagram add a script-injecting post stage); `mermaid` and `icons` are pre-only (a fence rewrite and an inline-processor resolver); `fence`, `grid`, `tabs`, and `annotate` are marker-comment pre-plus-post pairs; `highlight` wraps prose in its pre stage and in-code markers in its post stage, with no marker comment.
  Their shared helpers are second-caller extractions: `_fences.map_prose` (prose outside fenced and indented code, shared by `highlight` and `icons`; `icons` has it cut inline code spans out, and `highlight` passes `skip_inline_code=False` so a pair can hold a span), and `_html.add_classes` (shared by `fence`, `grid`, and `annotate`); `_html.matching_end` has one caller, `annotate`, and `_fences.find_inline_code_spans` has one caller, `highlight`.
- **`cli.py`** wires config into each subcommand and is the single place exceptions become exit codes (`ConfigError`, an icons `OptionError`, or a `ConfigWarning` escalated with `PYTHONWARNINGS=error`, prints `mw: error:` and exits 2).
  It sets UTF-8 on stdin and stdout and reports a decode error, a closed stream, or a broken pipe as one `mw: error:` line, and it passes a leading front matter block around `run_pre`; `load_config` turns `OSError` and `UnicodeDecodeError` from the config file into `ConfigError`, and the icons stage turns them from an SVG file into `OptionError`.

## Success criteria

- `just check` is green: ruff clean, ruff format clean, mypy strict clean, pytest passing, coverage reported.
- `just test-integration` is green: the `mw pre | hugo | mw post` pipeline through a real Hugo build, and a clean-venv wheel install.
- `just docs-build` (strict) is clean and every page in the MkDocs nav exists.
- Rendered output matches the `do-markdownit` reference format for the eight ported extensions; the `mw-fence`, `mw-grid`, container, and `mw-annotate` markers and the `mw-embed` preview stay versioned and read fail-soft.
- Every extension page has its Host CSS and Script section, and every extension's markup reads correctly with the docs site's CSS and JavaScript turned off.
- Every extension renders live on its own docs page: mermaid, lightbox, and annotations through the committed `docs/javascripts/`, icons through the committed icon set, and block grids, cards, and a tab set that switches with the CSS sample alone.
- The `mw pre | hugo | mw post` integration test carries youtube, codepen, twitter, highlight, fence, button, lightbox, mermaid, icons, both annotate forms, the grid shortcut, a block grid with cards, a tab set, and two container problems.
