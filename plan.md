# markwright 0.4.0 Fix Plan

Turns the ten Roadmap Upcoming code items plus the docs catch-up and the Material mapping page into executor-ready steps, in the spec's build order.
Every step grounds in a `Planned (ITEM)` sentence under Goals in `spec.md`; when a step ships, its sentences lose the `Planned` prefix and the matching `Today` sentences are deleted.

The 0.4.0 release itself is not in this plan.
It is done by hand after the merge, because `pyproject.toml`, `uv.lock`, and the workflows are outside the `paths:` fence (the version bump, the `markdown` floor to `>=3.8.2`, the MkDocs bound, the CHANGELOG date and compare link, the tag check, and the GitHub Release).

## Current Status

- Branch: `containers-30`, draft PR #35 into `main`, CI green on Python 3.11 through 3.15.
- Not started. 0 of 29 steps complete.
- Gate: `just check` (ruff, ruff format, mypy strict, pytest, coverage reported) after every step; `just docs-build --strict` is the gate for the docs sections.
- Fences honored: no step edits `pyproject.toml` or `uv.lock` (outside `paths:`); no step implements a Roadmap Deferred item (in-process diagnostics, the shared one-scan-per-`run_pre` refactor, problem-report line numbers, fence marker binding, `[button]` argument checks, release pipeline hygiene).

## Section 1: Container Postprocessor Priority

**Tools:** none

**Batch:** single

### Step 1: Move the grid, annotate, and tabs postprocessors to 27

**NOTE**: Grounded in `Planned (container postprocessor priority)` under Goals, Containers ("Both paths").
Today the three postprocessors run at 30 and tie with `raw_html`, which `md_in_html` re-registers, so a host that lists `md_in_html` after the markwright extensions gets no tab set and no grid and the marker comments stay in the page.
The fix is to run them at 27: below `raw_html` at 30 (stashed markers restored first, whatever the load order) and above fence at 25.

```text
1. RED: Write a load-order test first:
   - Create tests/test_container_priority.py:
     - Build two markdown.Markdown instances that load the markwright grid, annotate, and tabs extensions plus md_in_html, one with md_in_html listed BEFORE the markwright extensions and one AFTER.
     - Render a source that holds a tab set, a [grid]...[/grid] block grid, a [grid cards]...[/grid] grid, and an [annotate] block with its list.
     - Assert both instances produce the tab markup (class "tabbed-set tabbed-alternate mw-tabs"), the grid div (class "mw-grid"), and the annotation links (class "mw-annotation"), and that no raw "mw-tab", "mw-grid", or "mw-annotate" marker comment survives in either output.
   - Confirm the AFTER case fails on the current priority 30.

2. GREEN: Change the postprocessor priority:
   - In src/markwright/grid.py, src/markwright/annotate.py, and src/markwright/tabs.py, change the Postprocessor registration priority from 30 to 27.
   - In src/markwright/registry.py, change each of these three extensions' post priority from 30 to 27 so the CLI composes stages in the same order.

3. REFACTOR: Confirm the in-process order still reads grid/annotate/tabs after raw_html (30) and before fence (25); leave fence and highlight at 25 and the script embeds at 15 unchanged.

4. Update documentation:
   - In CLAUDE.md, Processor Priority Reference, change the grid/annotate/tabs Postprocessor row from 30 to 27 and update its "Relationship" text to say it runs below raw_html (30) and above fence (25).
   - In spec.md, Goals, Containers, remove the "Planned (container postprocessor priority)" prefix from its sentence and delete the matching "Today they run at 30 and tie with raw_html" sentence; update the Feature Status "Open Work" column to drop "container postprocessor priority" from annotate, grid and cards, and tabs.

5. Verify meaningful coverage and run just check.
```

## Section 2: Containers Fixes (#30)

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: none

### Step 2: An invalid `[grid ...]` is not an opener

**Batch:** containers-a

**NOTE**: Grounded in `Planned (containers fixes)` under Goals, Grid and Cards.
Today an invalid `[grid ...]` (a bad token or a count outside 1 to 6) stays literal, but its `[/grid]` also stays literal with no report and a `[card]` between the two still becomes a card.
The fix makes an invalid opener behave like `[tab ]`: not an opener, so it never pairs and never becomes the list shortcut, its unpaired `[/grid]` is a stray closer, and a `[card]` it leaves outside any grid is reported once.

```text
1. RED: Write container-scanner tests first:
   - In tests/test_containers.py:
     - Test that scan_containers over "[grid 7]\n[card]\nx\n[/card]\n[/grid]" treats the [grid 7] line as a non-opener: no pair for it, the [/grid] is reported as a stray closer, and the [card] is reported as card-outside-grid.
     - Test that an invalid [grid foo] followed by a list is NOT turned into a shortcut grid.
     - Test that a valid [grid 3] still opens and pairs as before (guard against over-broad rejection).
   - In tests/test_grid.py:
     - Test (both the in-process render and expand_source/apply_html) that "[grid 7]" with a following [card] leaves the [card] literal and reports card-outside-grid, and that the [grid 7] line renders as literal text.

2. GREEN: Make the scanner reject invalid grid openers:
   - In src/markwright/_containers.py, where the opener grammar recognizes a [grid ...] line, parse its tokens with the same validity rule grid.py uses (cards at most once, one count 1 to 6, nothing else); when the tokens are invalid, do not record it as an opener, a shortcut, or a pairing candidate.
   - Keep the token-parsing rule in one place: if grid.py already owns grid-opener validation, expose or reuse that predicate from _containers.py rather than duplicating the 1-to-6 rule.

3. REFACTOR: Ensure a [card] whose enclosing [grid ...] is invalid falls out as card-outside-grid through the existing enclosure logic, not a new branch.

4. Update documentation:
   - In spec.md, Goals, Grid and Cards, remove the "Planned (containers fixes)" prefix from the "it is not an opener, like [tab ]" sentence and delete its "Today" sentence.

5. Verify meaningful coverage and run just check.
```

### Step 3: Column-based indentation pairing and the less-indented-line rule

**Batch:** containers-a

**NOTE**: Grounded in two `Planned (containers fixes)` sentences under Goals, Containers ("Pairing").
Today the scanner pairs by indentation compared as raw string prefix and pairs across list items, so a container opened in one list item and closed in the next straddles both, and a tab-indented opener does not pair with a four-space-indented closer in `mw pre`.
The fix compares indentation by column (tab stop every four columns, the way `_fences` reads it) and ends a container's block at the first non-blank line indented less than its opener.

```text
1. RED: Write container-scanner tests first:
   - In tests/test_containers.py:
     - Test that an opener indented with one tab pairs with a closer indented with four spaces (column equality, not string equality).
     - Test that a non-blank line indented LESS than an open container's opener ends that container: the opener becomes unclosed and a later closer at the opener's indentation no longer pairs with it.
     - Test that an unclosed [tab] or [card] ended this way, plus its now-stray closer, are reported, and that an unclosed [grid ...] ended this way follows the shortcut-or-literal rules.
     - Test the list-item case: "[grid]\n- a\n\n  [card]\n  x\n\n- b\n\n  [/card]" no longer pairs the [card] across the two list items.

2. GREEN: Compute indentation as columns:
   - In src/markwright/_containers.py, replace the raw-prefix indentation comparison with a column count that expands tabs to the next multiple of four, reusing the column helper in _fences.py if one exists rather than writing a second tab-expansion.
   - Add the less-indented-line rule: while scanning inside an open container, a non-blank line whose column indent is less than the opener's closes that container as unclosed before considering the current line as a closer.

3. REFACTOR: Keep the stack-matching and the from_marker handling intact; the column change is to the comparison only.

4. Update documentation:
   - In spec.md, Goals, Containers, remove the "Planned (containers fixes)" prefix from the column-comparison and less-indented-line sentences and delete their "Today" sentences.

5. Verify meaningful coverage and run just check.
```

### Step 4: A card needs a paired grid

**Batch:** containers-a

**NOTE**: Grounded in `Planned (containers fixes)` under Goals, Grid and Cards.
Today a `[card]` inside a `[grid ...]` that is never closed still becomes a card with no grid around it.
The fix: a `[card]` is inside a block grid only when the `[grid ...]` it opened in is itself paired; a card in an unclosed grid is reported like a card outside a grid.

```text
1. RED: Write tests first:
   - In tests/test_containers.py:
     - Test that scan_containers over "[grid]\n[card]\nx\n[/card]" (grid never closed) reports the [card] as card-outside-grid and does not record a card pair whose enclosure is a grid.
   - In tests/test_grid.py:
     - Test (both paths) that a [card]...[/card] inside an unclosed [grid] renders literal with a card-outside-grid report, not a mw-card div.

3. GREEN: Tie card enclosure to a paired grid:
   - In src/markwright/_containers.py, when deciding whether a card's nearest enclosing container is a grid, require that enclosing [grid ...] to be a paired opener (has a matched [/grid]); an unclosed grid does not count as an enclosure.

4. REFACTOR: Make sure a card in a VALID paired grid is unaffected.

5. Update documentation:
   - In spec.md, Goals, Grid and Cards, remove the "Planned (containers fixes)" prefix from the "a [card] is inside a block grid only when ... paired" sentence and delete its "Today" sentence.

6. Verify meaningful coverage and run just check.
```

### Step 5: Emit the shortcut and annotate markers as blocks; keep a CRLF line end

**Batch:** containers-b

**NOTE**: Grounded in `Planned (containers fixes)` under Goals, Containers ("Both paths").
Today the `[grid]` shortcut marker and the `[annotate]` marker gain a blank line after but none before, so a marker directly under a paragraph's text is read as part of that paragraph, and a problem marker lands after a trailing carriage return.
The fix emits those two markers like the container markers (own line, blank line on both sides, at the opener's indentation) and appends a problem marker before a trailing `\r` so a CRLF line keeps its line end.

```text
1. RED: Write tests first:
   - In tests/test_grid.py:
     - Test that the [grid] list shortcut marker is emitted on its own line with a blank line BEFORE and after it, so a shortcut directly under a paragraph line is not absorbed into that paragraph (assert the in-process and expand_source output puts a blank line before the marker comment).
   - In tests/test_annotate.py:
     - Test the same for the [annotate] marker.
   - In tests/test_grid.py and tests/test_tabs.py:
     - Test that a problem marker appended to a CRLF line ("[card]\r\n" with no grid) lands BEFORE the \r, so the line keeps its \r\n ending.

2. GREEN: Route both markers through marker_block:
   - In src/markwright/grid.py (shortcut) and src/markwright/annotate.py, emit the marker through _markers.marker_block (own-line block with surrounding blank lines) exactly as the container markers are emitted, instead of the current blank-line-after-only emission.
   - In src/markwright/_markers.py inline_problem_marker, insert the problem marker before a trailing carriage return when the literal line ends in \r.

3. REFACTOR: Confirm match_marker_pairs and the scanner still read these markers (they are own-line blocks either way).

4. Update documentation:
   - In spec.md, Goals, Containers ("Both paths"), remove the "Planned (containers fixes)" prefix from the shortcut-and-annotate-marker-as-blocks and CRLF sentences and delete their "Today" sentences.

5. Verify meaningful coverage and run just check.
```

### Step 6: Tabs grouping, set numbering, backtick names, and closer validation

**Batch:** containers-b

**NOTE**: Grounded in four `Planned (containers fixes)` sentences under Goals, Tabs.
Four changes land together because they all edit `tabs.py` grouping and emission:
the sibling rule (a tab joins the previous tab's set only when the nearest non-blank line above its opener is the closer of a paired tab at the same indentation);
set numbering S by the order each set's first tab OPENS (not closes);
the `html_block` ordering so a backticked tab name renders as the same escaped text in both paths (and a `[tab]`/`[grid]` line inside a raw HTML block is then expanded in-process, as `mw pre` already expands it, which is the accepted behavior change);
and strict decode of a closer marker's payload with the same model as its opener.

```text
1. RED: Write tests first:
   - In tests/test_tabs.py:
     - Test the sibling rule: a tab nested inside another tab's body (directly, and inside a grid and a card) starts its OWN set inside that tab's block, not beside its parent; and a tab that ends a list item does not join a top-level tab after it.
     - Test set numbering: an enclosing set gets a LOWER S than a set nested in its first tab (assert the mw-tab-S-T ids and the data-tabs="S:N").
     - Test backtick names: a tab name with a backtick span renders as escaped text (no <code> tag) in BOTH the in-process render and the expand_source/apply_html pipeline.
     - Test closer validation: an mw-tab-end marker carrying an unsupported version is skipped and reported under --warn, and its tab is NOT closed by it.
   - In tests/test_containers.py (grouping inputs if the sibling rule needs scanner support) or tests/test_tabs.py as the grouping owner.

2. GREEN: Implement in src/markwright/tabs.py:
   - Grouping: a tab joins the previous set only when the nearest non-blank line above its opener is a paired [/tab] (or its mw-tab-end marker) at the same indentation; otherwise it starts a new set; a set never runs past the end of a list item.
   - Set numbering: assign S in order of each set's first tab's OPENING position.
   - Register the tabs preprocessor (and confirm grid's) to run AHEAD of Python-Markdown's html_block preprocessor so each marker comment is stashed whole; verify the priority relationship in registry.py and the in-process order.
   - Closer validation: decode an mw-tab-end payload with the same strict pydantic model as mw-tab; on failure skip the pair and report it under --warn.

3. REFACTOR: Keep the "sibling rule lives in tabs.py, column pairing lives in _containers.py" boundary from spec.md Component boundaries; do not move grouping into _containers.py.

4. Update documentation:
   - In spec.md, Goals, Tabs, remove the "Planned (containers fixes)" prefix from the sibling-rule, html_block-ordering, S-numbering, and closer-decode sentences and delete their "Today" sentences.
   - In CLAUDE.md, Processor Priority Reference, add a note that the grid and tabs preprocessors run ahead of html_block if that relationship is not already stated.

5. Verify meaningful coverage and run just check.
```

### Step 7: Document the escape and the cards-list CSS sample (task)

**Batch:** containers-b

**NOTE**: Grounded in the `Planned (containers fixes)` escape sentence under Goals, Containers and the cards-list sentence under Goals, Grid and Cards.
The backslash escape (`\[grid 3]`, `\[tab Name]`, `\[/tab]`) already works through Markdown's own escape; this step documents and pins it.
The CSS sample for a list inside a `cards` block grid is docs-site CSS.

```text
1. Scope:
   - Artifact(s): docs/extensions/grid.md, docs/extensions/tabs.md, docs/stylesheets/extra.css, tests/test_grid.py, tests/test_tabs.py.
   - Desired end state: both pages document the backslash escape; both paths have a test pinning that "\[grid 3]" and "\[tab Name]" stay literal with no report; the CSS sample lays out a list inside a cards block grid.

2. Tooling:
   - Skills: python:python, content-design:review-content
   - MCPs: none
   - External: just check, just docs-build --strict

3. Do the work:
   - Add a test to tests/test_grid.py and tests/test_tabs.py asserting that a backslash-escaped directive line stays literal (both the in-process render and the pipeline) and produces no problem report.
   - Add an "Escaping a directive" note to docs/extensions/grid.md and docs/extensions/tabs.md.
   - In docs/stylesheets/extra.css, add the cards-list rules from spec.md Goals, Grid and Cards: ".md-typeset .mw-grid-cards > ul" and "> ol" with display: contents, and the card rules extended to ".md-typeset .mw-grid-cards > ul > li" and "> ol > li"; keep the existing "ul.mw-grid-cards > li" shortcut rule.

4. Verify:
   - just check and just docs-build --strict both exit 0.

5. Document:
   - In spec.md, Goals, Containers and Grid and Cards, remove the "Planned (containers fixes)" prefix from the escape and cards-list sentences and delete the cards-list "Today" sentence; update the Feature Status "Open Work" column to drop "containers fixes (#30)" from annotate, grid and cards, and tabs.
```

## Section 3: Block Bodies

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: none

**Batch:** block-bodies

### Step 8: `_fences` reads block-opener bodies as content, not indented code

**NOTE**: Grounded in the `Planned (block bodies)` sentences under Goals, Rules Every Feature Follows and under Component boundaries (`_fences.py`).
Since #29 `_fences` reads the four-column body of an admonition, details block, content tab, definition, or footnote as indented code, so a directive, a fence with its directives, or a `mermaid` fence there stays literal and an embed that 0.3.0 expanded there stays literal on this branch.
The fix: `_fences` reads the lines indented four columns under such an opener as that block's content (like a list item's), so directives work there; a line indented four columns FURTHER after a blank line is still code.
Because the rule lives in `_fences`, both paths apply it.

```text
1. RED: Write _fences tests first:
   - In tests/test_fences_map_lines.py:
     - Test that the four-column body under an admonition opener ("!!! note"), a details opener ("???" and "???+"), a content-tab opener ("==="), a definition (": "), and a footnote definition ("[^name]:") is reported as CONTENT (not indented code), so map_lines does NOT skip a directive line there.
     - Test that a line indented four columns FURTHER after a blank line inside such a body is still code.
   - In tests/test_fences_map_prose.py:
     - Test the prose side: a highlight marker or icon-position prose run inside such a body is visible to map_prose.
   - In tests/test_roundtrip.py:
     - Add cases: a directive line, a fence with a [label], and a mermaid fence inside each of the five bodies, with the admonition, def_list, footnotes, pymdownx.details, and pymdownx.tabbed extensions loaded, asserting the in-process render and the run_pre/stub/run_post pipeline agree.

2. GREEN: Implement in src/markwright/_fences.py:
   - Recognize the five block openers and read the four-column lines under one as that block's content, the same way list-item content is read, so those lines are not classified as top-level indented code.
   - Keep the "four columns further after a blank line is still code" rule.

3. REFACTOR: Keep the existing CommonMark fenced-code and list-item handling intact; this adds block-opener bodies as another non-code context.

4. Update documentation:
   - In spec.md, Goals, Rules Every Feature Follows, remove the "Planned (block bodies)" prefix from the three block-bodies sentences and delete the "Today _fences reads those bodies as indented code" sentence; in Component boundaries, remove the "Planned (block bodies)" prefix from the _fences.py sentence.
   - In the Feature Status "Open Work" column, drop "block bodies" from every row that lists it.

5. Verify meaningful coverage and run just check (it runs test_roundtrip including the hypothesis property).
```

## Section 4: Pre-Stage Order

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: none

**Batch:** pre-stage-order

### Step 9: Icons after the directive stages, and a mermaid fence in a list item

**NOTE**: Grounded in `Planned (pre-stage order)` under Goals, Icons and Goals, Mermaid.
The two land together, since icons after mermaid would otherwise rewrite a shortcode inside a converted diagram.
Icons' pre stage must run AFTER the directive stages so a shortcode inside a `[button]`, `[lightbox]`, `[tab]`, or embed line behaves like the in-process render and a shortcode inside a converted `mermaid` diagram is left alone.
A `mermaid` fence inside a list item (or one holding a blank line, or indented one to three columns) must render as one `<pre>`.

```text
1. RED: Write tests first:
   - In tests/test_icons.py:
     - Test that in mw pre a shortcode inside a [button URL :lucide-x:] line, a [tab :lucide-x:] line, and an embed line gives the SAME result as the in-process render (the shortcode is read as part of the directive, not replaced before it).
     - Test that a shortcode inside a converted mermaid diagram source is left literal in mw pre.
   - In tests/test_mermaid.py:
     - Test that a mermaid fence inside a list item renders as a single <pre class="mermaid"> (not wrapped in <p>), that a blank line inside the diagram does not split it across two paragraphs, and that a fence indented one to three columns does not keep that indent on every line after the first.

2. GREEN: Implement:
   - In src/markwright/registry.py, set the icons pre-stage priority so icons' source stage runs AFTER the directive stages (the registry pre priority noted in CLAUDE.md), keeping the in-process InlineProcessor at 85.
   - In src/markwright/mermaid.py, ensure the in-process preprocessor runs below Python-Markdown's whitespace normalizer and above pymdownx.superfences and stashes the block; in src/markwright/fence.py, skip a mermaid fence when mermaid is selected, so the diagram renders as one <pre>.

3. REFACTOR: Confirm a custom_fences mermaid entry stays inert for the fences markwright converts and still reaches an unconverted fence.

4. Update documentation:
   - In spec.md, Goals, Icons and Mermaid, remove the "Planned (pre-stage order)" prefix from both sentences and delete their "Today" sentences; drop "pre-stage order" from the mw CLI, mermaid, and icons rows in Feature Status "Open Work".
   - Update CLAUDE.md, Processor Priority Reference, if the icons pre priority row changes.

5. Verify meaningful coverage and run just check.
```

## Section 5: Highlight Escape in Split Spans (#31)

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: none

**Batch:** highlight-escape

### Step 10: Read in-code markers and escapes from each code line's text

**NOTE**: Grounded in the first two `Planned (highlight escape in split spans)` sentences under Goals, Highlight.
Today `\<^>` fails inside a code block whose lexer separates the backslash from the marker with a tag (the `python` lexer under Pygments and Chroma), and a lexer that splits the marker itself (`bash`, `html`, `xml`) defeats both the escape and a plain pair.
The fix: the post stage reads markers and escapes from the TEXT of each rendered code line, tags ignored, so a marker pairs and a backslash escapes it whatever tags sit between or inside them, under Pygments and under Chroma.

```text
1. RED: Write post-stage tests first:
   - In tests/test_highlight.py:
     - Test (Pygments, in-process) that "\<^>" inside a python code block renders a LITERAL marker even though the lexer splits the backslash from the marker with a <span>.
     - Test that a plain pair split by the lexer (bash/html/xml token boundaries) still pairs and wraps the text between in <mark>.
     - Test that exactly one backslash is removed for an escape, a paired marker's characters are removed, and every tag stays; a <span> that held only a backslash or part of a marker remains, empty.
     - Test that a revealed literal marker is written "&lt;&#94;&gt;" so a second mw post leaves it alone (idempotence).
   - Add Chroma fixtures in tests/test_fence.py or tests/test_highlight.py for the same cases under Chroma's <span class="line"> wrapping.

2. GREEN: Implement in src/markwright/highlight.py apply_html:
   - For a code region, assemble each rendered line's visible text across tags, locate markers and their preceding backslashes in that text, decide pairing and escaping on the text, then apply the edits back onto the token spans so tags stay in place and emptied spans remain.
   - Write a revealed literal marker as "&lt;&#94;&gt;".

3. REFACTOR: Keep the prose path and the "text tokens only, never script/style" scoping unchanged; this step is the in-code path.

4. Update documentation:
   - In spec.md, Goals, Highlight, remove the "Planned (highlight escape in split spans)" prefix from the two post-stage sentences and correct the "Known gap (highlight escape in split spans, #31)" sentence to describe only what remains (the literal-backslash-before-a-highlight gap stays).

5. Verify meaningful coverage and run just check (including the Hugo integration path if a Chroma fixture needs it).
```

### Step 11: `mw pre` writes a prose escape both renderers hand back

**NOTE**: Grounded in the third `Planned (highlight escape in split spans)` sentence under Goals, Highlight.
In prose `mw pre` reads the backslashes before a marker in pairs: an odd run escapes the marker, and `mw pre` then adds one backslash and writes the marker's `<` as `&lt;`, so Python-Markdown and a CommonMark renderer both hand `mw post` the escaped form; an even run leaves the marker live.

```text
1. RED: Write pre-stage tests first:
   - In tests/test_highlight.py:
     - Test that expand_source over a prose "\<^>" (odd backslash run) emits a form whose rendered output (through both the stub renderer and the in-process comparison) is a literal marker, and that the emitted text writes the marker's "<" as "&lt;".
     - Test that an even backslash run leaves the marker live, matching the in-process reader.
   - In tests/test_roundtrip.py:
     - Add prose-escape cases so run_pre/stub/run_post equals the in-process render.

2. GREEN: Implement in src/markwright/highlight.py expand_source:
   - Count the backslashes immediately before a prose marker; for an odd run, consume the escaping backslash, add one backslash, and write the marker's "<" as "&lt;"; for an even run, leave the marker for normal pairing.

3. REFACTOR: Keep the pre stage scoped to prose outside fenced code, indented code, and inline code spans.

4. Update documentation:
   - In spec.md, Goals, Highlight, remove the "Planned (highlight escape in split spans)" prefix from the mw pre sentence; drop "escape in split spans (#31)" from the highlight row in Feature Status "Open Work".

5. Verify meaningful coverage and run just check.
```

## Section 6: Highlight Same-Line Pairing (#34)

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: none

**Batch:** highlight-pairing

### Step 12: In-process prose pairing on the same line only

**NOTE**: Grounded in the second `Planned (highlight same-line pairing)` sentence and the `Decision (2026-11-16)` under Goals, Highlight.
Today the in-process path pairs a marker with the next prose marker in the same PARAGRAPH, so a pair can hold a line end; this departs from both renderers and was measured at 294 path differences over 1,133 documents.
The fix: the in-process inline processor matches an opener alone and searches for its closer on the SAME line; with no closer there the opener stays literal and matching resumes just after it, and a pair whose text holds a stashed block's placeholder is declined the same way.

```text
1. RED: Write in-process tests first:
   - In tests/test_highlight.py:
     - Test that "e <^>f" on one line and "g<^> h" on the next is NOT highlighted in-process (no cross-line pair).
     - Test that a same-line pair "a <^>b `x` c<^> d" marks "b" through "c", code span included.
     - Test that an opener with no same-line closer stays literal and a later same-line pair after it still matches.
     - Test that a pair whose span would hold a stashed block placeholder is declined (stays literal).
     - Test that the cross-block cases the old code wrapped (a marker on either side of a code block; "a <^>b" then "- c<^> d") are no longer wrapped.

2. GREEN: Implement in src/markwright/highlight.py:
   - Change the InlineProcessor to match a single opener and search its own line for the closer; on no closer, leave the opener literal and resume matching after it; decline a span that contains a stash placeholder.

3. REFACTOR: Keep the in-code post-stage pairing unchanged (same line, several pairs per line); this step is prose only.

4. Update documentation:
   - In spec.md, Goals, Highlight, remove the "Planned (highlight same-line pairing)" prefix from the in-process-pairing sentence; rewrite the "Known gap (highlight same-line pairing, #34)" paragraph to describe only what remains after both steps (see Step 13).

5. Verify meaningful coverage and run just check.
```

### Step 13: `mw pre` wraps a same-line pair in one `<mark>`, with differential tests

**NOTE**: Grounded in the third and fourth `Planned (highlight same-line pairing)` sentences under Goals, Highlight.
`mw pre` wraps everything between a same-line pair in one `<mark>`, code spans included; a marker inside a code span stays literal in `mw pre` and never closes a prose pair in `mw post`; a code span is followed across a line end, never across a blank line, when deciding what is inside one.
The tests are differential over a corpus of two-line and three-line documents from both renderers' block starts.

```text
1. RED: Write differential tests first:
   - In tests/test_highlight.py:
     - Test that expand_source wraps a same-line pair, including one around an inline code span, in a single <mark>.
     - Test that a marker inside a code span stays literal in expand_source.
   - In tests/test_roundtrip.py:
     - Add a differential block: generate two-line and three-line documents from the block starts of both renderers; assert the in-process render, the stub pipeline, and (where feasible) the Hugo pipeline highlight the same text. Reuse the hypothesis grammar if it already enumerates block starts.

2. GREEN: Implement in src/markwright/highlight.py expand_source:
   - Pair prose markers on the same line only; wrap the whole same-line span, code spans included, in one <mark>; leave a marker inside a code span literal; follow a code span across a line end but not across a blank line when deciding membership.

3. REFACTOR: Confirm the pre and post stages agree on "a marker inside a code span never closes a prose pair".

4. Update documentation:
   - In spec.md, Goals, Highlight, remove the remaining "Planned (highlight same-line pairing)" prefixes; confirm the "Decision (2026-11-16)" stays and the "Known gap (highlight across inline constructs)" stays; drop "same-line pairing (#34)" from the highlight row in Feature Status "Open Work".
   - Note the upgrade in CHANGELOG (the pairs that stop highlighting) is owed to the docs catch-up step; leave a reminder in that step rather than editing CHANGELOG here.

5. Verify meaningful coverage and run just check.
```

## Section 7: Annotate Overlap

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: none

**Batch:** annotate-overlap

### Step 14: A comment token with a `!` marker is replaced by every marker's links

**NOTE**: Grounded in `Planned (annotate overlap)` under Goals, Annotate.
Today a comment that holds a plain marker and a `!` marker (`# (1) and (2)!`) produces two overlapping edits and broken HTML in both paths.
The fix: when a comment token holds a `!` marker, the comment is replaced by the links for EVERY valid marker in it, in order, and `_html.apply_edits` refuses overlapping spans with an exception.

```text
1. RED: Write tests first:
   - In tests/test_annotate.py:
     - Test (both paths) that "# (1) and (2)!" in highlighted code is replaced by the links for (1) and (2) in order, with no overlapping or broken HTML.
     - Test that a comment with only a plain marker and a comment with only a "!" marker still render as before.
   - In tests/test_markers.py or a dedicated _html test (via the public path if _html has no own test module): test that _html.apply_edits raises on two overlapping span edits.

2. GREEN: Implement:
   - In src/markwright/annotate.py, when the stripped-comment ("!") path fires, collect every valid marker in that comment token and emit one edit replacing the comment with all their links in order, rather than one edit per marker that can overlap.
   - In src/markwright/_html.py apply_edits, raise an exception when two edits' spans overlap (a guarded invariant, not silent).

3. REFACTOR: Keep the plain-marker path and the comment-token detection unchanged.

4. Update documentation:
   - In spec.md, Goals, Annotate, remove the "Planned (annotate overlap)" prefix and delete its "Today" sentence; drop "annotate overlap" from the annotate row in Feature Status "Open Work".

5. Verify meaningful coverage and run just check.
```

## Section 8: Config `warn` Default (#33)

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: none

**Batch:** config-warn

### Step 15: `mw post` takes the config `warn` key as the diagnostics default

**NOTE**: Grounded in the first `Planned (config warn default)` sentence under Goals, The mw CLI.
Today `mw post` does not read the config key `warn`, which `docs/config.md` calls the default for `--warn`.
The fix: `mw post` takes `warn` as the default for its diagnostics; `--warn` turns them on and `--no-warn` turns them off whatever the config says, and the last of the two on the command line wins; the pair is on `mw post` only; `mw config` shows the resolved value and source; the diagnostics stay plain stderr lines that `PYTHONWARNINGS=error` does not escalate.

```text
1. RED: Write CLI tests first:
   - In tests/test_cli.py:
     - Test that "mw post" with a config "warn = true" prints the diagnostics, and with "warn = false" (or omitted) prints none.
     - Test that "--warn" and "--no-warn" override the config, and that the LAST of the two on the command line wins.
     - Test that --no-warn exists on "post" only (not pre/render/config).
     - Test that the diagnostics are plain "mw: warning:"-style stderr lines that PYTHONWARNINGS=error does NOT turn into an error exit.

2. GREEN: Implement in src/markwright/cli.py:
   - Add a --no-warn flag to the post subcommand; resolve the effective warn from config.warn as the default, overridden by whichever of --warn/--no-warn appears last.
   - Keep the diagnostics as direct stderr writes (not warnings.warn), so PYTHONWARNINGS does not escalate them.

3. REFACTOR: Confirm mw config already shows warn and its source (it is validated today); add the source display if missing.

4. Update documentation:
   - In spec.md, Goals, The mw CLI, remove the "Planned (config warn default)" prefix from the warn-default sentence and correct the "Known gap (config warn default, #33)" sentence to reflect that mw post now reads warn.

5. Verify meaningful coverage and run just check.
```

### Step 16: Parser hygiene in one pass

**NOTE**: Grounded in the second `Planned (config warn default)` sentence under Goals, The mw CLI and the `Planned (config warn default)` sentence under Goals, Config and the Host API.
The same parser edit turns off option abbreviations, prints the missing-subcommand usage on stderr, makes `--config ""` an error, and names the source in every no-op warning raised while a config file or host table is validated.

```text
1. RED: Write tests first:
   - In tests/test_cli.py:
     - Test that "mw post --w", "--no", "--ex", and "--conf" are usage errors (exit 2), not read as --warn/--no-warn/--exclude/--config.
     - Test that "mw" with no subcommand prints its usage line on STDERR and exits 2.
     - Test that "--config ''" (empty string) is an error, not a fallback to discovery.
   - In tests/test_config.py:
     - Test that a no-op ConfigWarning raised while validating a config file or a host mapping names that source.

2. GREEN: Implement:
   - In src/markwright/cli.py, set allow_abbrev=False on the argument parsers; print the missing-subcommand usage to stderr and exit 2; treat an empty --config value as an error (a path that does not exist).
   - In src/markwright/config.py, include the source label in a no-op ConfigWarning raised during file or mapping validation.

3. REFACTOR: Keep other warning categories in Python's default format; only markwright's ConfigWarning is reformatted by the CLI.

4. Update documentation:
   - In spec.md, Goals, The mw CLI, remove the "Planned (config warn default)" prefix from the abbreviation/usage/--config sentence and delete its "Today" sentence; in Config and the Host API, remove the prefix from the no-op-source sentence and delete its "today" clause; drop "warn default (#33)" from the mw CLI and config rows in Feature Status "Open Work".

5. Verify meaningful coverage and run just check.
```

## Section 9: Public Fence API (#32)

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: none

**Batch:** fence-api

### Step 17: `disallowed_environments(source, config)`

**NOTE**: Grounded in the four `Planned (public fence API)` sentences under Goals, Config and the Host API and the sentence under Component boundaries (`config.py`).
Bartleby today imports `markwright._fences` and fence's private regexes to report disallowed environments.
The fix adds a public `disallowed_environments(source, config)` that fence.py backs with a public scan, so `config` gains `fence` as a dependency and `fence` never imports `config`.

```text
1. RED: Write tests first:
   - In tests/test_config.py (or tests/test_fence.py for the scan):
     - Test that disallowed_environments returns each environment name a fence directive names outside fence.allowed_environments, once each, in order of first appearance.
     - Test the two additions: two [environment NAME] lines one after the other both report (a disallowed line does not end the scan of that fence), and a mermaid fence is skipped when mermaid is selected but scanned when mermaid is excluded.
     - Test that it returns an empty list when allowed_environments is omitted or when fence is not selected, emitting NO warning (run under warnings.simplefilter("error")).
     - Test that an empty allowlist reports every name, and that a name keeps its padding compared as written.
     - Test that a label or secondary-label line is skipped and a directive inside a nested fence's source is treated as code.

2. GREEN: Implement:
   - In src/markwright/fence.py, expose a public scan that lists the environment names a document's fence directives name, by the same rules the pre stage extracts them with, plus the two additions (a disallowed line does not stop the scan; skip a mermaid fence when mermaid is selected).
   - In src/markwright/config.py, add disallowed_environments(source, config) that calls that scan and filters against allowed_environments; import fence here (config -> fence, never fence -> config).
   - In src/markwright/__init__.py, add disallowed_environments to the public __all__.

3. REFACTOR: Keep load_config private; the public names stay Config, ConfigError, ConfigWarning, OptionError, the three config functions, and now disallowed_environments.

4. Update documentation:
   - In spec.md, Goals, Config and the Host API, remove the four "Planned (public fence API)" prefixes and the "Known gap (public fence API, #32)" once the function exists; in Component boundaries, remove the "Planned (public fence API)" prefix from the config.py sentence; drop "public fence API (#32)" from the fence and host API rows in Feature Status "Open Work".
   - In docs/config.md, document disallowed_environments in the host API section.

5. Verify meaningful coverage and run just check.
```

### Step 18: `config_from_mapping` input hardening

**NOTE**: Grounded in the `Planned (public fence API)` sentence under Goals, Config and the Host API.
`config_from_mapping` raises `ConfigError` with the source label for a table that is not a mapping, reads `None` as an empty table, and checks key names before it drops `None` values, so an unknown key is an error whatever its value.

```text
1. RED: Write tests first:
   - In tests/test_config.py:
     - Test that config_from_mapping([1, 2], source="x") raises ConfigError naming the source (not a mapping).
     - Test that config_from_mapping(None, source="x") reads as an empty table (valid, all defaults).
     - Test that an unknown key with a None value ({"bogus": None}) is a ConfigError (key names checked before None values are dropped).

2. GREEN: Implement in src/markwright/config.py:
   - At the top of config_from_mapping, raise ConfigError with the source label when the table is not a mapping and read None as an empty table; validate key names before dropping None values.

3. REFACTOR: Keep the file-validation path (load_config) sharing the same key-name check so the two agree.

4. Update documentation:
   - In spec.md, Goals, Config and the Host API, remove the "Planned (public fence API)" prefix from the config_from_mapping sentence and delete its "Today" sentence.

5. Verify meaningful coverage and run just check.
```

## Section 10: Hardening

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: none

Hardening is the bundle of `Planned (hardening)` sentences across Goals; the goal is that no input ends in a traceback.
It deliberately does NOT include the Roadmap Deferred "Pre-stage scan cost" refactor (one shared scan per `run_pre`); these steps only make bad input fail soft.

### Step 19: One integer helper for every directive and annotation integer

**Batch:** hardening-a

**NOTE**: Grounded in `Planned (hardening)` under Goals, Embeds.
Today a digit string of 4,301 characters, or a non-ASCII digit such as `²`, ends a stage in a traceback, in-process too.
The fix: one helper reads every integer a directive or an annotation marker carries (height, width, column count, `(N)`), accepting ASCII digits up to a fixed length; any other value leaves the line literal.

```text
1. RED: Write tests first:
   - In tests/test_youtube.py, tests/test_codepen.py, tests/test_twitter.py, tests/test_instagram.py, tests/test_slideshow.py, tests/test_image_compare.py, tests/test_grid.py, tests/test_annotate.py (the places that parse an integer):
     - Test that a 4301-character digit string and a non-ASCII digit ("²") leave the line LITERAL rather than raising, in both paths.
     - Test that ordinary small integers still parse.

2. GREEN: Implement:
   - Add one integer-reading helper (a small private function, placed where the embeds and grid/annotate can all import it without a new cross-dependency, e.g. a shared helper module or _diagnostics-adjacent location consistent with the codebase layout) that accepts ASCII digits up to a fixed maximum length and returns None otherwise.
   - Route every directive/annotation integer parse through it; a None result leaves the line literal.

3. REFACTOR: Replace each ad hoc int() on directive input with the helper; keep config-side integer options (if any) as they are unless they share the same risk.

4. Update documentation:
   - In spec.md, Goals, Embeds, remove the "Planned (hardening)" prefix from the integer-helper sentence and delete its "Today" sentence.

5. Verify meaningful coverage and run just check.
```

### Step 20: `decode_marker` turns every payload failure into a skip

**Batch:** hardening-a

**NOTE**: Grounded in `Planned (hardening)` under Goals, Rules Every Feature Follows ("marker is read fail-soft") and Component boundaries (`_markers.py`).
Today a number too long to convert, nesting too deep to decode, or a string that holds a lone surrogate ends `mw post` in a traceback.
The fix: `decode_marker` turns a `ValueError` or `RecursionError` from the JSON reader, and a lone surrogate, into a skip.

```text
1. RED: Write tests first:
   - In tests/test_markers.py:
     - Test that decode_marker returns the skip result (not a raise) for a payload with a number too long to convert, nesting too deep for the JSON reader (RecursionError), and a string holding a lone surrogate.
     - Test that a valid payload still decodes.

2. GREEN: Implement in src/markwright/_markers.py decode_marker:
   - Catch ValueError and RecursionError from the JSON reader and detect a lone surrogate, returning the fail-soft skip in each case.

3. REFACTOR: Keep the existing fail-soft cases (malformed JSON, non-object payload, unsupported version, wrong field type, no following element) unchanged.

4. Update documentation:
   - In spec.md, Goals, Rules Every Feature Follows, remove the "Planned (hardening)" prefix from the payload-skip sentence and delete its "Today" sentence; in Component boundaries, remove the prefix from the _markers.py sentence.

5. Verify meaningful coverage and run just check.
```

### Step 21: Fence hardening: class tokens, dropped `prefix_value`, Chroma newline

**Batch:** hardening-a

**NOTE**: Grounded in three `Planned (hardening)` sentences under Goals, Fence.
`label_class` and `secondary_label_class` accept space-separated class tokens of letters, digits, `-`, and `_`; any other value is a `ConfigError` (or `OptionError` in-process).
A `line_numbers` flag that replaces an earlier `command`, `super_user`, or `custom_prefix` drops `prefix_value`.
A Chroma line that already ends with a newline gains no second one.

```text
1. RED: Write tests first:
   - In tests/test_config.py:
     - Test that fence.label_class / secondary_label_class with a non-token value (spaces aside) raises ConfigError, and in-process raises OptionError; a valid space-separated token list passes.
   - In tests/test_fence.py:
     - Test that "line_numbers" after a "custom_prefix(>)" (or command/super_user) drops prefix_value from the mw-fence marker.
     - Test (Chroma fixture) that a prefixed line already ending in a newline gains no second newline, asserting the whole <li>.

2. GREEN: Implement:
   - In src/markwright/fence.py (and its config checker in config.py), validate label_class/secondary_label_class as class tokens (letters, digits, -, _, space-separated); raise OptionError in-process and let config.py wrap it as ConfigError.
   - In src/markwright/fence.py, when line_numbers overrides an earlier prefix flag, drop prefix_value from the marker payload.
   - In the Chroma line-prefix wrapping, do not add a newline to a line that already ends with one.

3. REFACTOR: Keep the Pygments flat-line path unchanged.

4. Update documentation:
   - In spec.md, Goals, Fence, remove the three "Planned (hardening)" prefixes and delete their "Today" sentences.

5. Verify meaningful coverage and run just check (exercise the Chroma case in the integration or fixture path).
```

### Step 22: Highlight skips `<title>` and `<textarea>`

**Batch:** hardening-a

**NOTE**: Grounded in `Planned (hardening)` under Goals, Highlight ("The pre stage wraps prose markers only").
Today a pair in a page's `<title>` is wrapped and the browser tab shows the `<mark>` tags as text.
The fix: the post stage also skips `<title>` and `<textarea>`, whose content a browser shows as characters.

```text
1. RED: Write tests first:
   - In tests/test_highlight.py:
     - Test that a "<^>"-pair inside <title> and inside <textarea> is NOT wrapped by apply_html (their content shows as characters).
     - Test that a pair in ordinary body text is still wrapped.

2. GREEN: Implement in src/markwright/highlight.py apply_html:
   - Add <title> and <textarea> to the elements whose text the post stage skips, alongside <script> and <style>.

3. REFACTOR: none beyond the skip list.

4. Update documentation:
   - In spec.md, Goals, Highlight, remove the "Planned (hardening)" prefix from the title/textarea sentence and delete its "Today" sentence; drop "hardening" from the highlight row in Feature Status "Open Work" once Steps 10, 11, 22 are done.

5. Verify meaningful coverage and run just check.
```

### Step 23: Icons reports an unreadable or non-UTF-8 SVG

**Batch:** hardening-b

**NOTE**: Grounded in `Planned (hardening)` under Goals, Icons.
Today an SVG file that cannot be read or is not UTF-8 is a traceback.
The fix makes it a boundary error that names the file.

```text
1. RED: Write tests first:
   - In tests/test_icons.py:
     - Test that a pack whose referenced SVG file cannot be read (permissions) or is not UTF-8 raises the boundary error (OptionError) naming the file, not a bare OSError/UnicodeDecodeError.
     - Test that a readable UTF-8 SVG still inlines.

2. GREEN: Implement in src/markwright/icons.py:
   - Wrap the SVG file read; turn OSError and UnicodeDecodeError into the boundary OptionError naming the file.

3. REFACTOR: Keep the "names no pack or no file stays literal" behavior; this is for a file that exists but cannot be read or decoded.

4. Update documentation:
   - In spec.md, Goals, Icons, remove the "Planned (hardening)" prefix from the unreadable-SVG sentence and delete its "Today" clause; drop "hardening" from the icons row in Feature Status "Open Work".

5. Verify meaningful coverage and run just check.
```

### Step 24: CLI and config I/O never end in a traceback

**Batch:** hardening-b

**NOTE**: Grounded in `Planned (hardening)` under Goals, The mw CLI (UTF-8, exit codes), Goals, Config and the Host API (unreadable config file), and Component boundaries (`cli.py`).
`mw` reads and writes UTF-8 whatever the locale or `PYTHONIOENCODING`; a decode error, a closed stream, a broken pipe, and an unreadable or non-UTF-8 config file are each one `mw: error:` line and exit 2.

```text
1. RED: Write tests first:
   - In tests/test_cli.py:
     - Test that non-UTF-8 stdin is one "mw: error:" line and exit 2 (not a traceback, not exit 1).
     - Test that a closed stdout / broken pipe is one "mw: error:" line and exit 2.
     - Test that mw reads/writes UTF-8 even with a non-UTF-8 locale or PYTHONIOENCODING set (reconfigure stdio).
   - In tests/test_config.py:
     - Test that an unreadable or non-UTF-8 config file is a ConfigError (which the CLI turns into "mw: error:" exit 2), not a traceback exit 1.

2. GREEN: Implement:
   - In src/markwright/cli.py, set UTF-8 on stdin and stdout (reconfigure) regardless of locale; catch the decode error, closed stream, and broken pipe at the CLI boundary and emit one "mw: error:" line with exit 2.
   - In src/markwright/config.py load_config (and icons.read_options), turn OSError and UnicodeDecodeError into ConfigError and OptionError.

3. REFACTOR: Keep the "library raises, only the CLI turns exceptions into exit codes" boundary; the config/icons readers raise ConfigError/OptionError, the CLI maps to exit 2.

4. Update documentation:
   - In spec.md, Goals, The mw CLI, remove the "Planned (hardening)" prefixes from the UTF-8 and exit-code sentences and delete their "Today" sentences; in Config and the Host API, remove the prefix from the unreadable-config sentence; in Component boundaries, remove the prefix from the cli.py sentence.

5. Verify meaningful coverage and run just check.
```

### Step 25: Skip a multi-line HTML comment and pass front matter through

**Batch:** hardening-b

**NOTE**: Grounded in the two `Planned (hardening)` sentences under Goals, Rules Every Feature Follows (HTML comment region) and Goals, The mw CLI (front matter), plus Component boundaries (`_fences.py`).
`_fences` reads a block that starts with `<!--` and runs to the line holding `-->` as a region its callers skip, so a directive inside a multi-line HTML comment stays commented out in both paths.
`mw pre` passes a leading YAML (`---`) or TOML (`+++`) front matter block through untouched.

```text
1. RED: Write tests first:
   - In tests/test_fences_map_lines.py and tests/test_fences_map_prose.py:
     - Test that a directive line, a highlight marker, and an icon shortcode inside a multi-line HTML comment (<!-- ... -->) are inside a skipped region in both map_lines and map_prose.
   - In tests/test_roundtrip.py:
     - Add a multi-line-HTML-comment case so both paths agree.
   - In tests/test_cli.py:
     - Test that mw pre passes a leading "---\n...\n---" YAML block and a leading "+++\n...\n+++" TOML block through UNTOUCHED, so a marker/shortcut/directive inside front matter is not rewritten.

2. GREEN: Implement:
   - In src/markwright/_fences.py, read a block from a line starting with "<!--" to the line holding "-->" as a skip region its callers (map_lines, map_prose) treat like fenced/indented code.
   - In src/markwright/cli.py, detect a leading YAML/TOML front matter block and pass it through run_pre untouched (split it off before the pre stages and re-prepend it).

3. REFACTOR: Keep the single-line HTML comment marker handling the stages already rely on; this is the multi-line author comment case.

4. Update documentation:
   - In spec.md, Goals, Rules Every Feature Follows, remove the "Planned (hardening)" prefix from the HTML-comment-region sentence and delete its "Today" sentence; in The mw CLI, remove the prefix from the front-matter sentence and delete its "Today" sentence; in Component boundaries, remove the prefix from the _fences.py HTML-comment sentence; drop the remaining "hardening" entries from Feature Status "Open Work".

5. Verify meaningful coverage and run just check.
```

## Section 11: Docs Catch-Up

**Tools:**
- Skills: content-design:review-content
- MCPs: none
- Linters: none

**Batch:** docs-catch-up

Docs-only, done after the code items so the CHANGELOG's Fixed list is final.
Grounded in the two `Known gap (docs catch-up)` entries under Goals, Docs Site.
The gate is `just docs-build --strict`.

### Step 26: CLI, reference, and integration docs (task)

**NOTE**: Covers the CLI and cross-cutting reference pages from the first docs-catch-up Known gap.

```text
1. Scope:
   - Artifact(s): docs/cli.md, docs/renderer-requirements.md, docs/pipeline.md, docs/integrations/hugo.md, docs/integrations/mkdocs.md, docs/index.md, README.md.
   - Desired end state: these pages describe the current system (containers, all markers, all fifteen extensions, the real CLI behavior).

2. Tooling:
   - Skills: content-design:review-content
   - MCPs: none
   - External: just docs-build --strict

3. Do the work:
   - docs/cli.md: cover containers in the mw pre and mw post paragraphs; name every marker in the --warn section, not just mw-fence; fix the synopsis so --exclude NAME takes one name each time; replace "python -W error" with "PYTHONWARNINGS=error mw ...".
   - docs/cli.md and README.md: state that mw render loads no other extension and that its syntax highlighting needs Pygments.
   - docs/renderer-requirements.md: name every marker comment, not only mw-fence.
   - docs/pipeline.md, docs/integrations/hugo.md, README.md: describe the two stages across all extensions, not only embeds/fence/highlight; update the README usage examples that load eight extensions.
   - docs/integrations/hugo.md: correct the claims that its commands are the ones CI runs and that Hugo strips output silently.
   - docs/integrations/mkdocs.md and docs/index.md: correct the "MkDocs pinned below 2.0" wording to match what pyproject.toml actually does after the release settles it; add the tabs pattern to the Architecture list in docs/index.md.

4. Verify:
   - just docs-build --strict exits 0.

5. Document:
   - none (spec.md Known gap stays until Step 28 finishes the whole docs-catch-up item).
```

### Step 27: Extension pages, demo, and config docs (task)

**NOTE**: Covers the extension-page and config gaps from the first docs-catch-up Known gap.

```text
1. Scope:
   - Artifact(s): docs/demo.md, the eight ported extension pages (docs/extensions/highlight.md, fence.md, youtube.md, codepen.md, twitter.md, instagram.md, slideshow.md, image-compare.md), docs/extensions/grid.md, docs/extensions/annotate.md, docs/config.md, and the embed pages.
   - Desired end state: the demo and pages show all features and HTML output, and the stated contracts match the code.

2. Tooling:
   - Skills: content-design:review-content
   - MCPs: none
   - External: just docs-build --strict

3. Do the work:
   - docs/demo.md: show all fifteen extensions, not only the eight ported ones.
   - The eight ported extension pages: add the HTML output each currently omits.
   - docs/extensions/grid.md: fix "the mw-cards class from 0.4.0" (it never shipped; it is mw-grid-cards) and "the 0.4.0 behavior" for the list shortcut (block containers ship in 0.4.0 too).
   - docs/extensions/annotate.md: add a Marker Contracts section; fix the "Annotating a List" example that needs md_in_html (which mw render does not load); add the "noClasses = false" condition to the comment-stripping note.
   - docs/config.md: document fence.label_class and fence.secondary_label_class; fix the Hugo one-liner that does not run.
   - The embed pages (youtube, codepen, twitter, instagram, slideshow, image-compare): add the note that an embed line needs a blank line on both sides.

4. Verify:
   - just docs-build --strict exits 0, and tests/test_docs_tokens.py still passes (it checks rendered docs tokens).

5. Document:
   - none (spec.md Known gap closes in Step 28).
```

### Step 28: CHANGELOG corrections (task)

**NOTE**: Covers the second docs-catch-up Known gap; done last so the Fixed list is final and every plan item that owes the CHANGELOG a line gets it.

```text
1. Scope:
   - Artifact(s): CHANGELOG.md (the Unreleased section), spec.md (close both docs-catch-up Known gaps).
   - Desired end state: the Unreleased section states 0.4.0 correctly.

2. Tooling:
   - Skills: content-design:review-content
   - MCPs: none
   - External: just docs-build --strict, just check

3. Do the work:
   - Fix the "renders as it did" claim to point at the Upgrading and Fixed exceptions.
   - Add to the upgrade notes: selected_extensions with no enable list returns fifteen names where 0.3.0 returned eight; the [grid N] forms; a mermaid entry in custom_fences goes inert; a directive with nothing to apply to is removed.
   - Correct the mw-cards -> mw-grid-cards rename line (mw-cards never shipped) and name all nine markers the release adds.
   - Fix the #20 and #29 Fixed entries that describe the embed-in-code fix backwards; add the missing entry for a <^> pair inside indented code.
   - Add the per-item lines each plan item owes: the pairs that stop highlighting under same-line pairing (#34), an existing warn = true that starts printing (#33), and the abbreviated options that stop working (#33).
   - Add the line Step 8 owes: a directive line indented under a list item or a block opener's body now expands at its own indentation, so it stays inside the item or body (an embed under a list item no longer ends the list in-process), while a directive at column 0 renders as before.

4. Verify:
   - just check and just docs-build --strict both exit 0.

5. Document:
   - In spec.md, Goals, Docs Site, remove both "Known gap (docs catch-up)" entries now that the docs and CHANGELOG match the code; update the Feature Status table if any "Open Work" still names docs catch-up.
```

## Section 12: Material Mapping Docs Page

**Tools:**
- Skills: content-design:review-content
- MCPs: none
- Linters: none

**Batch:** material-mapping

### Step 29: The Material-to-extension mapping page (task)

**NOTE**: Grounded in the "Material mapping docs page" Roadmap Upcoming item; docs-only.
Optional and independent of the 0.4.0 release: it can be dropped from this run without affecting the release.

```text
1. Scope:
   - Artifact(s): a new docs page (e.g. docs/material-mapping.md), mkdocs.yml (nav entry).
   - Desired end state: a page mapping each mkdocs-material reference feature to the Python-Markdown or pymdown-extensions extension that provides it in-process and the Goldmark setting that provides it in Hugo, with the gaps named.

2. Tooling:
   - Skills: content-design:review-content
   - MCPs: none
   - External: just docs-build --strict

3. Do the work:
   - Write docs/material-mapping.md: a table of mkdocs-material feature -> in-process extension -> Hugo/Goldmark setting -> gap, covering admonitions, content tabs, grids, annotations, code features, and the markwright-own features.
   - Add the page to the nav in mkdocs.yml.

4. Verify:
   - just docs-build --strict exits 0 and the new page is in the nav.

5. Document:
   - In spec.md, move "Material mapping docs page" from Roadmap Upcoming to the Shipped list (or mark it done) once the page exists.
```

## Implementation Guidelines

- TDD on every Feature step: RED (failing test) then GREEN (minimal code) then REFACTOR; Task steps follow Scope / Tooling / Do / Verify / Document.
- `just check` must pass before a step is complete; the docs sections also require `just docs-build --strict`.
- Each step edits the `spec.md` entry of the feature it changes: remove the shipped `Planned (ITEM)` prefix, delete the matching `Today` sentence, and update the Feature Status "Open Work" column. Keep `Decision` and remaining `Known gap` sentences.
- Do not edit `pyproject.toml` or `uv.lock` (outside `paths:`); the version bump, the `markdown` floor, and the MkDocs bound are the by-hand release.
- Do not implement a Roadmap Deferred item; in particular, do not add the shared one-scan-per-`run_pre` refactor, in-process diagnostics, or problem-report line numbers while hardening.
- Keep the two cross-tool contract rules: a changed marker payload bumps its version and reads fail-soft.
- Respect the module dependency directions in Component boundaries: `config` may import `fence`; `fence` never imports `config`; the sibling rule lives in `tabs.py`, column pairing in `_containers.py`.
- One commit per batch (a batch of one is a step), each with a new `.ai-sessions/session-*.md`, on `containers-30`; never commit to `main`.

## Success Metrics

- Every `Planned (ITEM)` sentence for the ten code items has lost its prefix and its `Today` sentence, and the Feature Status "Open Work" column is empty of these items.
- `just check` green: ruff, ruff format, mypy strict, pytest, coverage reported.
- `just test-integration` green: the `mw pre | hugo | mw post` pipeline and the clean-venv wheel install.
- `just docs-build --strict` clean, every nav page exists, and `tests/test_docs_tokens.py` passes.
- The CHANGELOG's Unreleased section states 0.4.0 correctly, and the docs describe the actual system.
- The branch is ready for the by-hand 0.4.0 release checklist in `spec.md`.
