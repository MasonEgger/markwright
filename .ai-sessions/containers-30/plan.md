# Implementation Plan: Containers (Block Grids, Cards, and Tabs): Issue #30

Derived from `spec.md`, the `### Containers: Block Grids, Cards, and Tabs (Issue #30)` goal.
Builds one shared pairing scanner, extends `grid` with column counts and a block form plus cards, adds a `tabs` extension, and carries all of it through the `mw pre | render | mw post` parity path and the docs demo.

## Current Status

- [ ] Section 1: Container pairing scanner (`_containers.py`)
- [ ] Section 2: Grid column counts and the `mw-grid-cards` rename
- [ ] Section 3: Block grids and cards
- [ ] Section 4: Tabs extension
- [ ] Section 5: Integration, docs, and project records

## Architecture Notes (read before any step)

- **Marker pairs, stack-matched in post.** The list-shortcut grid keeps its single `mw-grid` marker. Every container (block grid, card, tab) instead emits a pair: an open marker before the content and a close marker after it. The content between is rendered by Markdown, so the post stage wraps by offset: collect the open and close markers, order them by source offset, stack-match (push on open, pop on close), and wrap each popped span in its `<div>`. This composes for nesting (a grid in a grid, a grid in a card) with no special cases.
- **`first` for tabs is adjacency, computed in `tabs.py`.** `_containers` returns the matched pairs in document order; `tabs.py` decides which tab opens a new set (only blank lines since the previous tab's closer) and records `first` in the `mw-tab` payload. The post stage groups tabs into sets by walking them in order and starting a set at each `first: true`.
- **Pre stages still scan through `_fences`.** `_containers` skips fenced and indented code via `_fences`, so an opener or closer inside code stays literal. No Markdown parser is added.
- **In-process post priority 30** for grid and tabs (with annotate), ahead of fence (25), matching the registry `post_priority`.
- **Contracts are versioned, pre-1.0, no shim.** `mw-cards` becomes `mw-grid-cards`; the `mw-grid` payload gains an optional `columns`; the new markers (`mw-grid-block`, `mw-grid-end`, `mw-card`, `mw-card-end`, `mw-tab`, `mw-tab-end`) are version 1 and read fail-soft.

---

## Section 1: Container pairing scanner (`_containers.py`)

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: ruff check --output-format=json

The pairing algorithm is a self-contained scanner with its own contract, like `_fences` and `_markers`, so it is built and tested in isolation before any extension uses it.

### Step 1: The `_containers.py` pairing scanner

**NOTE**: New private module. Depends only on `_fences` (for skipping fenced and indented code). Returns matched open/close pairs and unpaired-or-misplaced lines with reasons. It does not emit markers or HTML; it only reports structure. `tests/test_containers.py` tests it directly (a new exemption to the public-API-only test rule, alongside `_fences` and `_markers`).

```text
1. RED: Write the scanner's contract tests first in tests/test_containers.py:
   - Import from markwright._containers (direct private-module test, like tests/test_fences_map_lines.py). Add `from __future__ import annotations` at the top.
   - Decide and test this public surface: a function `scan_containers(text: str) -> ContainersScan` returning a frozen pydantic result with `.pairs` (a tuple of ContainerPair) and `.problems` (a tuple of ContainerProblem). ContainerPair carries: kind ("grid" | "card" | "tab"), open_line (int, 0-based), close_line (int), indent (str, the leading whitespace), and tokens (tuple[str, ...], the opener's argument tokens: for grid the words after "grid", for tab a single-element tuple holding the trimmed name, for card an empty tuple). ContainerProblem carries: line (int), text (str, the offending line stripped), and reason (str).
   - Test these scenarios (table-style or one test each):
     - A single `[grid]` ... `[/grid]` pair at column 0: one pair, kind "grid", tokens (), no problems.
     - `[grid cards 3]` ... `[/grid]`: tokens ("cards", "3").
     - `[card]` ... `[/card]`: kind "card", tokens ().
     - `[tab Node.js 20]` ... `[/tab]`: kind "tab", tokens ("Node.js 20",).
     - A `[tab ]` opener with an empty name: not a pair; a problem on the opener line, reason mentions an empty name. (A `[tab]` with no name is likewise not an opener.)
     - Nested same kind: `[grid]` / `[grid]` / `[/grid]` / `[/grid]` → two grid pairs, the inner pair's lines inside the outer pair's lines; no problems.
     - Nested mixed: `[grid]` / `[card]` / `[/card]` / `[/grid]` → a grid pair and a card pair; no problems.
     - Indentation must match: `[grid]` at column 0 with `[/grid]` indented four spaces → the opener is unclosed (a problem), the closer is stray (a problem).
     - A closer pairs with the NEAREST unpaired opener of its kind at the same indent (bracket matching), and an opener a closer skips over is unclosed.
     - A stray `[/card]` with no open `[card]`: a problem, reason mentions no matching opener.
     - An unclosed `[card]` or `[tab]`: a problem on the opener line.
     - An opener or closer inside a fenced code block (``` ... ```): NOT scanned; no pair, no problem (left literal). Build the fixture so the directive sits between fences.
     - An opener inside an indented code block (four-space indent after a blank line): not scanned.
     - `[grid ...]` openers are REPORTED AS PAIRS ONLY WHEN CLOSED. An unclosed `[grid]` is NOT a problem here (it is the list shortcut, handled by grid.py); the scanner returns it in a separate `.unclosed_grids` tuple (line, indent, tokens) so grid.py can treat it as the shortcut. Test that an unclosed `[grid cards]` with no `[/grid]` appears in `.unclosed_grids`, not `.problems`.
     - A `[card]` whose nearest enclosing OPEN container is not a grid (e.g. a `[card]` paired inside a `[tab]`, or at top level) is still returned as a card pair with a flag `enclosed_by_grid: bool` on ContainerPair, computed from the pairing stack. Test enclosed_by_grid is True for a card directly inside a block grid and False for a card at top level. (grid.py decides what to do with a misplaced card; the scanner only reports the fact.)

2. Document the scanner:
   - Add a module docstring (RST style, `:param:`/`:returns:`) describing the pairing rules and the three result fields, and the `# ABOUTME:` two-line header.

3. GREEN: Write minimal code in src/markwright/_containers.py to pass:
   - `from __future__ import annotations`.
   - Define the opener/closer regexes: grid opener `^\[grid(?P<args>(?:\s+\w+)*)\]$`, card opener `^\[card\]$`, tab opener `^\[tab\s+(?P<name>[^\]]+)\]$`, and closers `^\[/grid\]$`, `^\[/card\]$`, `^\[/tab\]$`, each matched against the stripped line.
   - Scan lines via `_fences.map_lines`-style skipping: get the set of line indices that are fenced or indented code by reusing `_fences.find_fenced_blocks` and the indented-code detection `_fences` already exposes, and ignore those lines. (Read _fences.py to find the exact helper the directive stages use to skip code; mirror it rather than re-deriving indentation rules.)
   - Walk the non-code lines with a stack. On an opener, push (kind, line, indent, tokens). On a closer, pop the nearest same-kind opener at the same indent; mismatches and leftovers become problems; an unclosed `[grid]` goes to `.unclosed_grids`. Set `enclosed_by_grid` from whether a grid frame is on the stack when a card opener is pushed.
   - Parse tokens: grid args split on whitespace; tab name is the trimmed match group; card tokens empty.
   - Return the frozen pydantic `ContainersScan`. Models use `model_config = ConfigDict(frozen=True)`.

4. RED: Add edge-case tests:
   - A tab name containing `]` cannot occur (the regex stops at `]`); test `[tab a]b]` parses the name as "a" and leaves "b]": assert the opener line is still the full line and document the behavior chosen. (Decide: the opener regex requires the whole stripped line to match, so `[tab a]b]` does NOT match and is not an opener; test it is neither a pair nor a problem.)
   - Mixed indentation nesting inside a list item (two-space indent) pairs correctly at that indent.

5. GREEN: Adjust the scanner so the edge cases pass with no change to the Step-1 behavior.

6. REFACTOR: Collapse the opener/closer dispatch into one table of (kind, open_re, close_re) if it reduces duplication without hiding the logic; keep single-concern helpers only where they carry a real grammar.

7. Document: confirm the module docstring matches the final field names and the `enclosed_by_grid` and `unclosed_grids` semantics.

8. Verify branch coverage of the scanner's own paths and run `just check`.
```

---

## Section 2: Grid column counts and the `mw-grid-cards` rename

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: ruff check --output-format=json

The list shortcut gains a column count and the class rename, with no block form yet. This is the smallest grid change and keeps `grid` fully working on its own.

### Step 2: Column counts on the grid shortcut and `mw-cards` → `mw-grid-cards`

**NOTE**: Edits `src/markwright/grid.py` only (plus tests and the two parity assertions that name the old class). The shortcut keeps the single `mw-grid` marker; the payload gains `columns`. `GRID_RE` is replaced to accept `cards` and a 1-6 count in any order. The `mw-grid-cols-N` class and `mw-grid-cards` (renamed from `mw-cards`) are new versioned contracts.

```text
1. RED: Write stage-function tests in tests/test_grid.py (extend the existing file):
   - expand_source / apply_html round-trips for the shortcut:
     - `[grid 3]` before a bullet list → the `<ul>` gets `mw-grid mw-grid-cols-3`.
     - `[grid cards]` → `mw-grid mw-grid-cards` (the renamed class; assert `mw-cards` is NOT present).
     - `[grid cards 2]` and `[grid 2 cards]` both → `mw-grid mw-grid-cards mw-grid-cols-2` (token order free).
     - `[grid]` (bare) → `mw-grid` only, no cols class (unchanged from today except the class names).
     - `[grid 7]`, `[grid 0]`, `[grid foo]` → the line is left literal (no marker, no class); assert the directive text survives to output.
     - Count bounds: `[grid 1]` and `[grid 6]` are valid; `[grid 6]` → `mw-grid-cols-6`.
   - Payload/fail-soft tests:
     - An `mw-grid` marker payload with `columns` out of 1-6 or non-int is skipped fail-soft (collect skip_reasons), class unchanged, marker removed. (Add to GridMarker a validator or field constraint so a bad `columns` fails decode.)
   - Update the in-process render tests the same way (the GridExtension path), mirroring the existing test style.

2. Document the contract:
   - Update the GridMarker docstring in grid.py to describe `columns: int | None` (1-6, omitted means auto).

3. GREEN: Edit src/markwright/grid.py:
   - Rename CARDS_CLASS value to "mw-grid-cards"; add COLS_CLASS_PREFIX = "mw-grid-cols-".
   - Replace GRID_RE with one that matches `[grid]` plus optional whitespace-separated tokens, each `cards` or a 1-9 digit run, order-free: match the whole stripped line, capture the token run, then parse tokens in `_transform_line`: reject on an unknown token, a second `cards`, a second count, or a count outside 1-6 (return [line] unchanged).
   - GridMarker gains `columns: int | None = None` with a constraint rejecting values outside 1-6 (use a pydantic field validator; strict mode already rejects non-int).
   - `_transform_line` builds the payload {"cards": True?, "columns": N?} dropping absent keys.
   - apply_html builds the class string from marker.cards and marker.columns: base "mw-grid", add "mw-grid-cards" when cards, add f"mw-grid-cols-{columns}" when columns is set.

4. RED: Add integration-with-existing-features tests:
   - A `[grid cards 3]` shortcut and an `[annotate]` block in the same document both render correctly (no interference), through apply_html.

5. GREEN: No new code expected; confirm the ordering holds.

6. REFACTOR: Factor the grid-opener token parse into a small helper only if Step 3 will reuse it (block grids parse the same tokens): leave a `_parse_grid_tokens(token_run: str) -> dict | None` returning the payload dict or None for an invalid opener, since Step 3's block-grid opener reuses it.

7. Update the parity assertions that name the old class:
   - tests/test_roundtrip.py: change the `'<ul class="mw-grid mw-cards">'` assertion to `'<ul class="mw-grid mw-grid-cards">'`.
   - tests/integration/test_hugo_pipeline.py: update any `mw-cards` assertion string to `mw-grid-cards` (string edit only; no Hugo run needed to make the edit).

8. Verify coverage of the token-parse branches and run `just check`.
```

---

## Section 3: Block grids and cards

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: ruff check --output-format=json

### Step 3: Block grid and card pairs, emitted in pre and stack-wrapped in post

**NOTE**: Edits `src/markwright/grid.py`. Uses `_containers.scan_containers` for pairing. Pre emits paired markers (`mw-grid-block`/`mw-grid-end`, `mw-card`/`mw-card-end`) around the block content and keeps the shortcut path from Step 2 for unclosed `[grid]`. Post adds a stack-matching wrap for the paired markers. A `[card]` whose `enclosed_by_grid` is False is left literal and reported under `--warn`.

```text
1. RED: Write stage-function tests in tests/test_grid.py:
   - Block grid, no list:
     - `[grid]\n\n## A\n\ntext\n\n[/grid]` → the rendered content is wrapped in `<div class="mw-grid"> ... </div>`; the heading and paragraph are inside.
     - `[grid 2]` ... `[/grid]` → `<div class="mw-grid mw-grid-cols-2">`.
     - `[grid cards]` ... `[/grid]` → `<div class="mw-grid mw-grid-cards">`.
   - Cards inside a block grid:
     - A block grid containing `[card]\n### Install\n\ntext\n[/card]` and a fenced code block → the card content is wrapped in `<div class="mw-card">`, and the code block is a sibling inside the grid div.
     - A card with several blocks (heading + paragraph + list) wraps all of them in one `<div class="mw-card">`.
   - Nesting (the stack-matching case):
     - `[grid]` / `[card]` / `[grid 3]` / (list) / `[/grid]` / `[/card]` / `[/grid]` → outer grid div, inner card div, innermost grid div with cols-3, correctly nested; assert the three opening divs appear in order and close in reverse.
   - Shortcut still works: an unclosed `[grid cards 2]` before a list still classes the `<ul>` (Step 2 behavior), and a `[grid]` with a `[/grid]` does NOT also class a list inside it twice.
   - Fail-soft / literal:
     - A `[card]` at top level (no enclosing grid) is left literal and, with a skip_reasons list, reports a reason; assert the `[card]` text survives to output and no `mw-card` div appears.
     - An opener inside a fenced code block stays literal (reuse the _containers guarantee; assert end to end).
   - In-process GridExtension tests mirroring the block-grid and card cases.

2. Document the contracts:
   - grid.py module docstring and new marker-model docstrings for the block-grid and card payloads (GridBlockMarker with version/cards/columns, CardMarker with version). Note the open/close pairing and stack-wrap in the docstring.

3. GREEN: Edit src/markwright/grid.py:
   - expand_source: run `scan_containers` on the text. For each grid pair and card pair, record line-indexed edits: at the opener line emit the open marker comment (`mw-grid-block` with payload from `_parse_grid_tokens`, or `mw-card`) at the opener's indent with a blank line, and at the closer line emit the close marker (`mw-grid-end` / `mw-card-end`). For each entry in `.unclosed_grids`, emit the shortcut `mw-grid` marker as in Step 2. For each card pair with enclosed_by_grid False, leave the lines untouched (literal): the warn report is surfaced in post, not pre (pre has no skip_reasons channel). Keep using `map_lines` only for the shortcut's line replacement; the paired markers are inserted by line index from the scan. Ensure the two mechanisms do not double-process a line.
   - Define GridBlockMarker (version:int, cards:bool=False, columns:int|None=None) and CardMarker (version:int), both strict frozen, columns constrained 1-6.
   - apply_html: keep the shortcut `mw-grid` handling from Step 2. Add paired-marker handling: find `mw-grid-block`+`mw-grid-end` and `mw-card`+`mw-card-end` markers, order all open/close comments by offset, stack-match per kind, and for each matched span insert `<div class="...">` right after the open comment's end and `</div>` right before the close comment's start, removing both comments. Build the grid div class from the block payload (mw-grid [+ mw-grid-cards] [+ mw-grid-cols-N]); the card div is always `mw-card`. A `[card]` marker that decodes but was emitted outside a grid cannot occur (pre left those literal), so no post-side enclosed check is needed; a malformed block/card payload is skipped fail-soft with a reason.
   - Thread skip_reasons through the new paths.

4. RED: Add integration tests within tests/test_grid.py:
   - A document mixing a shortcut grid, a block grid with two cards, and an annotate block renders all three without interference.
   - Running apply_html twice is stable (idempotent on already-wrapped HTML: the second pass finds no markers and changes nothing).

5. GREEN: Wire the above; adjust until green.

6. REFACTOR: Extract the offset-ordered stack-matching wrap into one helper in grid.py if block grids and cards share it (they do: same algorithm, different open/close names and div class). Name it so the concern is clear (e.g. `_wrap_paired(tokens, rendered_html, open_name, close_name, div_class_for)`).

7. Update the roundtrip grammar and assert parity:
   - tests/test_roundtrip.py: add a `_block_grid` composite (a `[grid N?]`/`[/grid]` wrapping a short prose block and a `[card]`/`[/card]` with a heading + paragraph) to the document-building strategy, so the hypothesis property exercises block grids and cards. Confirm the existing `test_pipeline_equals_in_process_render` covers it.

8. Verify branch coverage of the pairing/wrap/fail-soft paths and run `just check`.
```

---

## Section 4: Tabs extension

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: ruff check --output-format=json

### Step 4: The `tabs` extension (`tabs.py`) and its registry entry

**NOTE**: New module `src/markwright/tabs.py`, a marker pre/post pair like grid. New registry name `tabs` (on by default). Pre emits `mw-tab`/`mw-tab-end` pairs with a `first` flag computed from adjacency. Post groups tabs into sets at each `first: true` and builds pymdownx `tabbed` `alternate_style` markup with `mw-tab-S-T` ids.

```text
1. RED: Write stage-function tests in a new tests/test_tabs.py (`from __future__ import annotations`; public-API-only, through expand_source/apply_html and the in-process extension):
   - A single set of two tabs:
     - Source: `[tab Python]\n\n    print(1)\n\n[/tab]\n\n[tab Node.js 20]\n\npara\n\n[/tab]`
       (use indented or fenced code and prose as tab bodies).
     - Rendered output is one `<div class="tabbed-set tabbed-alternate mw-tabs" data-tabs="1:2">` containing two radio `<input>`s (`id="mw-tab-1-1"` checked, `id="mw-tab-1-2"`, both `name="mw-tab-1"`), a `<div class="tabbed-labels">` with `<label for="mw-tab-1-1">Python</label>` and `<label for="mw-tab-1-2">Node.js 20</label>`, then a `<div class="tabbed-content">` with two `<div class="tabbed-block">`s holding the bodies.
     - The first tab's input carries `checked`; the second does not.
   - Grouping:
     - Two tabs separated only by blank lines are ONE set (data-tabs="1:2").
     - Two tabs with a paragraph of prose between them are TWO sets (data-tabs="1:1" then "2:1"), ids `mw-tab-1-1` and `mw-tab-2-1`.
   - Name handling:
     - A name with Markdown-ish characters (`[tab C *star*]`) renders the label as escaped plain text, `C *star*`, not `<em>`.
     - `[tab ]` (empty) is left literal (no set); assert the text survives.
   - Fail-soft:
     - A lone `[tab X]` with no `[/tab]` is left literal and, with skip_reasons, reports a reason.
     - A malformed `mw-tab` payload is skipped fail-soft.
   - In-process TabsExtension tests mirroring the single-set and two-set cases.

2. Document the contract:
   - tabs.py module docstring: the `mw-tab` payload (version, name, first), the `mw-tab-end` close marker, the set-numbering and id scheme, and the emitted markup. `# ABOUTME:` header.

3. GREEN: Write src/markwright/tabs.py:
   - `from __future__ import annotations`. MARKER_OPEN = "mw-tab", MARKER_CLOSE = "mw-tab-end".
   - TabMarker (strict frozen): version:int, name:str, first:bool.
   - expand_source: `scan_containers(text)`; for each tab pair, compute `first` (True when this tab is the first overall, or the previous pair was a tab whose closer line is separated from this opener by blank lines only: i.e. consecutive tabs with nothing but blanks between them join a set; anything else starts one). Emit `mw-tab` (with name and first) at the opener line and `mw-tab-end` at the closer line, at the pair's indent. Leave non-tab pairs alone. Lone/unclosed tabs are already problems from the scan and stay literal.
   - apply_html: find `mw-tab`/`mw-tab-end` markers ordered by offset and stack-match into per-tab spans (tabs do not nest, but use the same ordered match for consistency). Walk tabs in order, decode each `mw-tab`; a `first: true` starts a new set (increment S, reset T), else increment T. For each set, after collecting its tabs, build: the inputs+labels header, then wrap each tab's rendered body (the span between its open and close marker) in `<div class="tabbed-block">`, all inside the set divs. Insert the set's opening markup before the first tab's content and the closing `</div></div>` after the last tab's content; remove every tab marker comment. Escape the label name with html.escape. Set `checked` on the first input of each set.
   - makeExtension/TabsExtension with a Preprocessor at pre 20 and Postprocessor at post 30 (mirror grid.py), names "mw-tabs-pre" / "mw-tabs-post".

4. RED: Register and wire:
   - Add tests in tests/test_registry.py (or the existing registry test file) that `tabs` is in EXTENSION_NAMES, has pre_priority 20 and post_priority 30, and run_pre/run_post include it by default.

5. GREEN: Add the registry entry in src/markwright/registry.py:
   - import tabs; add `"tabs": StageSpec(pre=tabs.expand_source, post=tabs.apply_html, pre_priority=20, post_priority=30, extension=tabs.TabsExtension)`. Place it after "annotate" so EXTENSION_NAMES order is grouped with the other container-ish extensions.

6. REFACTOR: If the offset-ordered stack-match helper from Step 3 lives in grid.py and tabs would import a private name across modules, promote that helper to `_markers.py` or `_html.py` (whichever it depends on) so both grid and tabs call it from a shared home; update grid.py to use the moved helper. Keep the move behavior-preserving (grid tests stay green).

7. Update the roundtrip grammar and assert parity:
   - tests/test_roundtrip.py: add a `_tab_set` composite (two or three `[tab NAME]`/`[/tab]` blocks with prose/code bodies, consecutive so they form one set) to the document strategy; include "tabs" in the names list the parity property renders with. Confirm pre|post equals in-process for tab sets.

8. Verify branch coverage (set boundaries, first-flag, escaping, fail-soft) and run `just check`.
```

---

## Section 5: Integration, docs, and project records

**Tools:**
- Skills: python:python, content-design:review-content
- MCPs: none
- Linters: ruff check --output-format=json

### Step 5: Hugo integration cases for a block grid with cards and a tab set (task)

**NOTE**: Extends `tests/integration/test_hugo_pipeline.py`. Needs a real `hugo` and the installed `mw`; `just check` runs it and it skips without them. Goldmark with `unsafe = true` must pass the marker comments and the wrapped `<div>`s through.

```text
1. Scope:
   - Artifact(s): tests/integration/test_hugo_pipeline.py.
   - Desired end state: one test drives `mw pre | hugo | mw post` over a document containing a block grid with two cards and column count, and a two-tab set, asserting the final HTML has the `mw-grid` wrapper div with `mw-grid-cols-N`, two `mw-card` divs, and one `tabbed-set ... mw-tabs` with two `mw-tab-1-1`/`mw-tab-1-2` inputs. Update MATERIAL_SOURCE's existing grid assertion to `mw-grid-cards` if not already done in Step 2.

2. Tooling:
   - Skills: python:python
   - MCPs: none
   - External: hugo (pinned), the installed mw console script; run via `just test-integration` or `just check`.

3. Do the work:
   - Add a module-level CONTAINERS_SOURCE string with a `[grid cards 2]` ... `[card]` ... `[/card]` ... `[card]` ... `[/card]` ... `[/grid]` block and a consecutive `[tab A]`/`[/tab]` `[tab B]`/`[/tab]` set.
   - Add `test_container_constructs_survive_hugo(tmp_path)` mirroring `test_pre_render_post_pipeline_through_hugo`: write the Hugo site config with `unsafe = true`, run `_run_mw(["pre"], CONTAINERS_SOURCE)`, build with hugo, run `_run_mw(["post"], rendered)`, and assert the wrapper divs, card divs, cols class, and the tabbed-set markup are present and no `<!-- mw-grid-block` / `<!-- mw-tab` comments remain.

4. Verify:
   - `just test-integration` exits 0 (or skips cleanly where hugo is absent); `just check` stays green.

5. Document: none.
```

### Step 6: Container docs: grid.md, tabs.md, extra.css, and the nav (task)

**NOTE**: Docs-only. grid.md leads with a block-grid demo; a new tabs.md leads with a tab-set demo; extra.css gains the column, card, narrow-screen, and CSS-only tab rules; the nav adds Tabs. Prose follows the writing rules (one sentence per line, Title Case headings, no banned vocabulary, straight quotes).

```text
1. Scope:
   - Artifact(s): docs/extensions/grid.md, docs/extensions/tabs.md (new), docs/stylesheets/extra.css, mkdocs.yml.
   - Desired end state: `just docs-build --strict` clean; both pages lead with a rendered demo then its labeled Markdown source (a fence with no language, per the #31 escape bug); the tab sample switches with CSS alone.

2. Tooling:
   - Skills: content-design:review-content
   - MCPs: none
   - External: `just docs-build`.

3. Do the work:
   - grid.md: open with a block-grid demo (a `[grid cards 3]` of cards with a heading, text, and a link), then sections for the list shortcut, column counts (`[grid 3]`), block grids (`[grid]`/`[/grid]`), and cards (`[card]`/`[/card]`), each with a no-language source fence. Update the class names to `mw-grid-cards` and document `mw-grid-cols-N`.
   - tabs.md (new): open with a two-tab demo, then the syntax (consecutive `[tab NAME]`/`[/tab]`, grouping, the first tab selected), and the emitted markup. Note tabs reuse pymdownx `tabbed`'s classes so a host's tab CSS applies.
   - extra.css: add `.mw-grid` column rules (grid-template-columns from `mw-grid-cols-N`, auto-fit default, narrow-screen single column), `.mw-card` styling, `ul.mw-grid-cards { display: contents }` (renamed), and a CSS-only `.mw-tabs` radio sample so the docs tabs switch without JS.
   - mkdocs.yml: add `- Tabs: extensions/tabs.md` to the Extensions nav after Grid.

4. Verify:
   - `just docs-build` exits 0 under `--strict`; open the built grid and tabs pages and confirm the demos render and the tabs switch.

5. Document: the two pages ARE the documentation; no other file.
```

### Step 7: "Host CSS and Script" section on every extension page (task)

**NOTE**: Docs-only. Each of the 14 extension pages gets a "Host CSS and Script" section listing the classes, data attributes, and ids a host styles or scripts, and linking the sample in `docs/stylesheets/extra.css` / `docs/javascripts/`. A page whose extension needs neither says so plainly. This satisfies the spec's progressive-enhancement and markup-is-the-contract invariants.

```text
1. Scope:
   - Artifact(s): docs/extensions/*.md (all 14).
   - Desired end state: every page has a "Host CSS and Script" section; `just docs-build --strict` clean.

2. Tooling:
   - Skills: content-design:review-content
   - MCPs: none
   - External: `just docs-build`.

3. Do the work:
   - For each extension page, add a "Host CSS and Script" section near the end: list the exact `mw-` classes / data attributes / ids the extension emits (pull them from the extension's source), state what host CSS or JS would do with them, and link the docs sample. annotate.md and grid.md already have equivalents; normalize them to the same heading. For button, lightbox, mermaid, icons, highlight, fence, and the embeds, name the hooks and the sample file; where an extension needs no host code, say so.

4. Verify:
   - `just docs-build` exits 0 under `--strict`; spot-check three pages for the section.

5. Document: the pages ARE the documentation.
```

### Step 8: CHANGELOG, README, and CLAUDE.md (task)

**NOTE**: Project records. The spec change itself is already committed; this step records the shipped surface and updates the developer guide. `spec.md` is outside the spec's `paths:` fence, so this step makes no spec.md edit (the `#32` number on the Upcoming public-fence-API line was added in the plan commit).

```text
1. Scope:
   - Artifact(s): CHANGELOG.md, README.md, CLAUDE.md.
   - Desired end state: CHANGELOG and README describe the containers and the rename; CLAUDE.md's architecture, priority table, and test-exemption text name `_containers.py`, `tabs.py`, and the new markers.

2. Tooling:
   - Skills: content-design:review-content, python:python
   - MCPs: none
   - External: none.

3. Do the work:
   - CHANGELOG.md: under [Unreleased] Added, list block grids, cards, column counts, and the `tabs` extension; under a Changed note the `mw-cards` → `mw-grid-cards` rename and the `mw-grid` payload's new `columns`. Since pre-1.0 with one user, state the rename plainly with no migration shim.
   - README.md: add tabs and block grids to the extension list / feature summary where the other extensions appear.
   - CLAUDE.md: add `tabs` to the extension list and the pattern descriptions; add `_containers.py` and `tabs.py` to the Architecture module list; add `tabs` (pre 20 / post 30) and confirm grid's post 30 in the Processor Priority Reference table; extend the `_fences`/`_markers` test-exemption sentence to include `_containers` and `tests/test_containers.py`; note the scope rule (markwright owns what Python-Markdown and pymdownx lack, plus block features Hugo lacks).

4. Verify:
   - `just check` stays green (CLAUDE.md/README/CHANGELOG are prose, but run it to confirm nothing references a renamed symbol); `just docs-build --strict` clean if any changed file is in the docs build.

5. Document: these files ARE the records.
```

---

## Implementation Guidelines

- TDD for every Feature step: RED (failing test against OUR logic) then GREEN (minimal code) then REFACTOR. Task steps follow Scope / Tooling / Do / Verify / Document.
- `just check` must pass before a step is done; read the coverage report and either test or delete what it shows uncovered.
- No new runtime dependency (`deps: frozen`); all changes stay inside the spec's `paths:` fence.
- Markup only: no CSS or JS in `src/`; the docs `extra.css` and `docs/javascripts/` are the host samples.
- No inline `style` attributes in emitted markup; classes, data attributes, and ids only.
- Contracts are versioned and read fail-soft; pre-1.0, a contract change bumps its version with no shim.
- Prose (docs, CHANGELOG, README, CLAUDE.md) follows the writing hard rules: no em/en dashes, no banned vocabulary, straight quotes, one sentence per line, Title Case headings.
- Commit sequence per CLAUDE.md: `/bpe:session-summary`, `/bpe:commit-message`, `git commit -S -F commit-msg.md`, then the CLAUDE.md updates by hand. Never commit to main; this work is on `containers-30`.

## Success Metrics

- `just check` green (ruff, ruff format, mypy strict, pytest, coverage read).
- `just test-integration` green: the `mw pre | hugo | mw post` pipeline carries a block grid with cards and a tab set.
- `just docs-build --strict` clean; the grid and tabs pages lead with a working demo, the docs tabs switch with CSS alone, and every extension page has a Host CSS and Script section.
- `scan_containers` is tested directly in `tests/test_containers.py`; grid and tabs are tested through their stage functions and the in-process render.
- The roundtrip hypothesis property covers block grids, cards, and tab sets: `run_post(stub_render(run_pre(doc)))` equals the in-process render.
- The `mw-grid`, `mw-grid-block`, `mw-grid-end`, `mw-card`, `mw-card-end`, `mw-tab`, and `mw-tab-end` markers are versioned and read fail-soft; `mw-cards` no longer appears anywhere.
