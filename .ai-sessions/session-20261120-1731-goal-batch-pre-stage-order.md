# Session Summary: Icons After the Directive Stages

**Date**: 2026-11-20
**Duration**: not measured (the batch ran over 2026-11-18 to 2026-11-20)
**Conversation Turns**: 14 executor dispatches (implement, twelve fix rounds, finalize), with thirteen validator passes between
**Estimated Cost**: not measured
**Model**: claude-fable-5-2 for fix rounds 9 to 12 and finalize (a second executor, started cold at round 9); the first executor's model is not recorded

## Goal Context

- **Outcome**: converged, after thirteen validator passes (eight past the 5-pass cap; Mason set the scope of rounds 10 to 12 himself)
- **Subagent dispatches**: 14 executor dispatches (implement, twelve fix rounds, finalize) and 13 validator passes
- **Steps completed**: 9 of 29

## Why Thirteen Validator Passes

The batch took thirteen validator passes.
The mermaid half of Step 9 asked for a `mermaid` fence in a list item to render as one exact `<pre>` at any indentation.
No rule delivered that across the three renderers (Python-Markdown in-process, Python-Markdown after `mw pre`, and Hugo) without a regression against the previous commit, 9a76768.
The three renderers strip different columns from the same indented raw HTML line, so each content-column rule of rounds 1 to 8 traded a Hugo regression for a stub or in-process one.
Round 9 took the rules out, round 10 gave back the one in-process gain that was worse than 9a76768 in some family, and rounds 11 and 12 were prose corrections.
The mermaid code ended at the previous commit's behavior: the in-process render is byte-identical to 9a76768, and the new mermaid tests lock in what it already did.
Mason dropped a mermaid fence in a list item below four columns as a goal in round 12 ("We can just not implement that").

## Key Actions

- Step 9, the icons half, shipped: the icons `mw pre` stage moved from registry pre priority 50 to 5, below every directive stage, so a shortcode inside a `[button]`, `[lightbox]`, `[tab]`, or embed line is read as part of the directive, as in-process.
- The icons stage leaves a diagram the mermaid stage emitted alone: `_fences.map_prose(skip_blocks_opened_by=mermaid.PRE_OPEN)` reads each emitted block as opaque, from the open tag through the first `</pre>`, and text after that tag on the line is prose.
- `mermaid.PRE_OPEN` is the one constant both stages read, so the tag the mermaid stage writes and the tag the icons stage recognizes cannot drift.
- `mw pre` leaves a blank diagram line empty instead of writing the fence's indentation on it, since a CommonMark renderer keeps the spaces of a whitespace-only line inside the `<pre>`.
- Step 9, the mermaid half, is not delivered: the in-process rule is still "defer and stash a fence indented four or more columns, emit every shallower fence inline", as at 9a76768.
- spec.md: the `Planned (pre-stage order)` sentences and their `Today` sentences are gone from Mermaid and Icons, Feature Status drops pre-stage order, and the remaining differences are written as Known gaps (indented mermaid fence, a fence under a list item at fewer than four columns, a fence four or more columns past its list item, a line `_fences` reads as a list marker, an author-written mermaid tag, and the smaller ones listed under Mermaid and Icons).
- spec.md Icons carries `Decision (2026-11-20)`: `mw pre` reads a block that opens with the mermaid stage's exact tag as raw HTML through the first `</pre>`, whoever wrote it.
- CLAUDE.md (pattern 5, pattern 6, the `_fences` bullet, the priority table), docs/index.md, docs/extensions/icons.md, and docs/extensions/mermaid.md say the same.
- Tests: 37 added test functions (one replaces an earlier test) and nine new test classes, across tests/test_icons.py, tests/test_mermaid.py, tests/test_fences_map_prose.py, tests/test_roundtrip.py, and tests/integration/test_hugo_pipeline.py.
- Ran `uv run pytest -q` and `just check` (1034 passed, 100% line and branch coverage, Hugo integration included).

## Deviations from Plan

### Step 9

- State after iteration 12. The entries below are the deviations as the tree stands; the iteration entries after them are the history.
- For the finalize commit message and the CHANGELOG: Step 9 changes nothing in-process. The in-process render is byte-identical to HEAD (10,503 of my shapes and 16,466 validator documents), and `TestMermaidInListItem` and `TestMermaidUnderAListItemBelowFourColumns` in tests/test_mermaid.py lock in behavior HEAD already has. No commit or CHANGELOG text may claim an in-process mermaid fix. What Step 9 ships: icons' pre stage at priority 5 after the directive stages, a diagram the mermaid stage emitted left alone by icons, and a blank diagram line left empty in `mw pre`.
- Plan said: (RED) "a fence indented one to three columns does not keep that indent on every line after the first".
- Deviated: not delivered, and no test asserts it. A fence emitted inline keeps its indentation before every line after the first and before `</pre>`, in `mw pre` and in-process, unless the renderer strips it with the list item around the fence. Rounds 1 to 8 tried content-column rules; each traded a Hugo regression for a stub or in-process one.
- Impact: spec.md Mermaid carries `Known gap (indented mermaid fence)` with no Roadmap item. The maintainer's round 10 decision A ships it as a Known gap and says not to reopen it.
- Plan said: (RED and GREEN) a mermaid fence inside a list item renders as a single `<pre class="mermaid">`, with the in-process preprocessor below the whitespace normalizer stashing the block.
- Deviated: true in-process only for a fence indented four or more columns, which HEAD already did (Step 8 built that stash). A fence indented one to three columns under a list item is emitted inline in-process, as at HEAD, and keeps its indentation under Python-Markdown. Round 9 stashed those too; round 10 gave that back, because every rule tried for deferring a shallow fence was worse than HEAD in some family.
- Impact: spec.md Mermaid carries `Known gap (mermaid fence under a list item at fewer than four columns)`. The four-column rule is HEAD's own. Validator pass 11 confirmed by probe that its trial rule is worse than HEAD in three families and that the tree is worse than HEAD nowhere. The maintainer accepted HEAD's four-column rule in round 12: a mermaid fence in a list item is no longer a goal ("We can just not implement that").
- Plan said: (GREEN) "in src/markwright/fence.py, skip a mermaid fence when mermaid is selected".
- Deviated: no change to fence.py. Mermaid runs ahead of fence (45 over 40) in both paths, so fence never reads a fence mermaid converted, and a fence mermaid does not convert reaches fence as before.
- Impact: none on output. The Planned public fence API step still owns the mermaid skip in `disallowed_environments`.
- Plan said: (REFACTOR) "Confirm a custom_fences mermaid entry stays inert for the fences markwright converts and still reaches an unconverted fence."
- Deviated: confirmed by probe only. No test in tests/ names `custom_fences`.
- Impact: the sentence in spec.md Mermaid and the `custom_fences` line in docs/extensions/mermaid.md rest on that probe; a later change to the mermaid priorities has no test to catch a change here.
- Plan said: icons runs after the directive stages and a shortcode inside a converted mermaid diagram is left literal in `mw pre`.
- Deviated: icons moves to pre priority 5 (below every directive stage and highlight) and reads each diagram the mermaid stage emitted as opaque through `map_prose(skip_blocks_opened_by=mermaid.PRE_OPEN)`, from the open tag through the first `</pre>`.
- Impact: a `<pre class="mermaid">` block the author wrote is read the same way. spec.md Icons carries `Decision (2026-11-20)` and `Known gap (author-written mermaid tag)`.
- Iteration 1 fixes (validator pass 1: 2 block, 1 warn).
  - Plan said: defer every diagram in-process. Deviated: only a nested diagram (`FencedBlock.holding_column` > 0, a new field) is deferred; a top-level one is emitted inline as HEAD did, so a column-0 diagram is byte-identical to HEAD beside any text line. Impact: none.
  - Plan said: icons skip a raw pre block (first design: whole-text regex plus uuid hold). Deviated: `map_prose(skip_raw_pre=True)` skips a line that starts with a `<pre` tag up to three columns in through the first `</pre>` (unclosed: to the end of the prose run), plus a mermaid diagram's own tag at any indentation. Probed against in-process html_block for 27 placements; all match. Impact: no module-level state, other stages unchanged.
  - Plan said: a 1-3 column fence keeps no indent on later lines (both paths). Deviated: none; a top-level fence indents the first line only, a nested one (list item, block opener) keeps every line, so the container holds it. Hugo test added. The Known gap sentence is deleted.
  - Residual: under Python-Markdown (stub renderer) a nested 2 or 3 column fence in `mw pre` output keeps the indent inside the `<pre>`, as the 4-column case already did; CommonMark strips it with the container.
- Iteration 2 fixes (validator pass 2: 4 block, 2 warn, 1 info).
  - Plan said: icons skip a raw `<pre>` block. Deviated: that generic rule is gone, since spec.md's Deferred entry already assigns an author's raw HTML block to later work and each imitation of html_block opened another parity hole. `map_prose(skip_blocks_opened_by=mermaid.PRE_OPEN)` skips only a line that starts with the exact tag mermaid emits, through the first line holding `</pre>`; mermaid.py emits from the same constant. Known gap in spec.md Icons names an author-written tag nested where Python-Markdown does not stash it. Impact: an author's raw `<pre>` behaves as at HEAD; the Deferred sentence is restored to HEAD wording.
  - Plan said: nested fences keep every-line indent in `mw pre`. Deviated: later lines take only `FencedBlock.content_column` (CommonMark's list item content column or opener body column, 0 when the fence is short of it), so `- item\n\n ```mermaid` and `1. item\n\n  ```mermaid` are top level and `1. item\n\n    ```mermaid` loses no extra column under Hugo. In-process still defers on `holding_column` (Python-Markdown's reading). Hugo test covers the five shapes; RED seen.
  - Known gaps written for the remaining mermaid differences: nested diagram under a Python-Markdown renderer after `mw pre`, and a two or three column fence after a blank line under a list item in-process.
- Iteration 3 fixes (validator pass 3: 2 block, 2 warn, 2 info).
  - Plan said: content_column from the same chain as holding_column. Deviated: `_scan_blocks` keeps a separate `content_chain` for CommonMark's reading, so a list item stays open across a lazy continuation line and an opener body reads as Python-Markdown does; holding_column and every code-region classification are untouched. Impact: none on other stages.
  - Plan said: icons skip the whole closing line of a diagram block. Deviated: the block ends right after the first `</pre>`, and the rest of that line is prose.
  - A blank diagram line is emitted empty, not indented, so no container indent lands inside the `<pre>` (a footnote body under Hugo leaked it).
  - Differential against HEAD (git archive of src, PYTHONPATH): 52 mermaid shapes x in-process, mw pre plus Python-Markdown stub, mw pre plus Hugo, scored for one clean `<pre>`: no shape worse than HEAD. Icons: 24 sources, shortcode counts in-process vs pipeline: no regression except the author-written nested tag already named as a Known gap.
- Iteration 4 fixes (validator pass 4: 2 block, 2 warn, 2 info).
  - Plan said: a line starting with `#` or `>` ends a lazy continuation. Deviated: `_starts_block` follows CommonMark's paragraph-interruption rules, checked against Hugo with 27 candidate lines: a heading needs one to six `#` then a space, tab or line end; a fence, thematic break, quote, HTML block of types 1 to 6, or any list item (marker alone, any ordinal) starts a block; `--- text`, `===`, type 7 HTML, `#tag` and two backticks are lazy.
  - A marker-only list item (`-`, `1.`) is a content-chain holder at marker width plus one when it follows a blank line or ends the item before it, never inside a paragraph (`para\n-` is a setext heading); a blank line right after it closes it.
  - A fence at four or more columns that no item holds (content_column 0) keeps its indent on every line, as HEAD did, so Hugo keeps one code block.
  - Differential against HEAD: 130 mermaid shapes x 3 renderers, no shape worse; `find_fenced_blocks` fields, `map_lines`, `map_directive_lines`, `map_prose` (both skip_html values) and `scan_containers` identical over 332 sources. Hugo and HEAD agree for every lazy-line and marker-only shape; in-process is unchanged from HEAD.
- Iteration 5 fix (validator pass 5: 1 block, 2 info).
  - Plan said: an empty list item opens after a blank line or a dropped item. Deviated: it opens whenever the previous line is not paragraph text (CommonMark 5.2: it cannot interrupt a paragraph). The scan tracks `previous_paragraph`: false after a blank line, a block start, a setext `=` underline, indented code, an empty item, or a line with a pipe (a possible table row, so the rule over-recognizes toward HEAD's behavior); true after plain text and after a list item's text line. Content chain only.
  - Differential against HEAD over 386 mermaid shapes (the 130 plus a marker-only matrix of 8 markers x 16 prefixes x next-line and after-content): no shape worse in any renderer. Scanner functions identical to HEAD over 588 sources.
  - Left as Known gaps: text under an empty item at less than its content column, and a fence right after an HTML block line.
- Iteration 6 fix (validator pass 6: 1 block, 2 info).
  - Plan said: track whether the previous line is paragraph text and open a marker-only item only elsewhere. Deviated: every marker-only line opens a content-chain holder, since opening one by mistake only leaves the fence indent inside the `<pre>` (HEAD's output) while failing to open one broke the HTML. The `previous_paragraph` state, the setext, pipe and dropped-block rules and the `_close_unreached_blocks` return value are removed.
  - Differential against HEAD over 813 sources (611 mermaid shapes x 3 renderers): no shape worse in any renderer by the clean-pre check and by an indent and stray-tag score, except seven Python-Markdown stub shapes that were already broken at HEAD and differ only in leaked whitespace. Scanner functions identical to HEAD over 813 sources; `mw pre` twice equals once.
- Iteration 7 fixes (validator pass 7: 2 block, 2 info).
  - Plan said: a fence at four columns that no item holds keeps its indent on every line. Deviated: one rule, `len(fence indent) - content_column >= 4`, so a fence four or more columns past its holder (a list item or column 0) keeps its indent on every line as HEAD did.
  - A spaced thematic break (`* * *`, `- - -`) no longer opens a content-chain item (CommonMark 4.1); `chain` is untouched, so `holding_column` and the code regions equal HEAD's.
  - Differential over 324 shapes (fences 0 to 8 columns past the content column under `-`, `1.`, `10.` and a nested item, tight and loose, with and without a blank diagram line; six thematic breaks before a fence at 0 to 4 columns, top level, after an item, after a paragraph) x 3 renderers: no shape HEAD rendered as one intact `<pre>` or one code block is worse now; 384 improved. In 22 stub shapes (fence 1 to 3 columns past the content column in a tight or loose item, blank line in the diagram) a leak and stray-tag score is higher, and HEAD's output was broken too (its `A` line became a nested code block).
- Iteration 8 fix (validator pass 8: 2 block, 3 info).
  - Plan said: later lines take the CommonMark content column. Deviated: a fence at or past `holding_column` (where Python-Markdown reads an item's body) puts every later line at `holding_column`, after the four-columns-past rule (indented code keeps the fence's indent). Python-Markdown then strips the same columns from every line, so an indentation-sensitive diagram stays exact; Hugo keeps one or two uniform extra columns, as HEAD did.
  - No scanner change. The finding-1 shapes `- - a`, `* * b`, `- -`, `- * x`, `- - - a` are repaired by this rule. A second item opened on a marker line under an outer marker wider than a bullet (`1. - a`, `1. 1. a`, `10. - a`, `-  - a`) stays worse than HEAD under Hugo and is a Known gap.
  - Tests changed because of the rule: the bullet-past-content and ordered-four-columns unit cases (later lines now at four), and the `1. item` fence-at-four Hugo assertion (one uniform column remains).
- Iteration 9 fix (validator pass 9: 3 block, 2 info), by a second executor taking the round over cold.
  - Approach: subtraction. `content_column`, the content chain, and every rule that served them are removed, and `mw pre` again puts the fence's own indentation before every line of the `<pre>`, as HEAD does (a blank diagram line stays empty). Each content-column rule of rounds 1 to 8 traded a Hugo regression for a stub or in-process one, because the three renderers strip different columns from the same line and no single column suits all of them. HEAD's every-line indent is the one emission no renderer reads worse than HEAD. The in-process exactness never came from the emission: it comes from the stash at 26, which stays.
  - Plan said: a fence indented one to three columns does not keep that indent on every line after the first (Step 9 RED). Deviated: not delivered for a fence emitted inline (`mw pre`, and in-process when `holding_column` is 0); it keeps its indentation on every line unless the renderer strips it with the list item. Delivered in-process for a fence under a list item or in a block opener's body, which is stashed with its exact text. Impact: spec.md carries `Known gap (indented mermaid fence)` with no Upcoming item; the maintainer decides whether one is wanted.
  - Plan said: icons skips the diagram the mermaid stage emitted. Deviated: `map_prose(skip_blocks_opened_by=...)` reads each emitted block as opaque, from its open tag through the first `</pre>`, and rescans the document only when a line of a block read as code. Impact: an author-written `<pre class="mermaid">` is read the same way, so a shortcode in it stays literal in `mw pre`, and when that block holds a fence line a shortcode after its `</pre>` is now replaced (HEAD left it literal); both are in `Known gap (author-written mermaid tag)`.
  - Left as a Known gap, same mechanism as HEAD: a shortcode inside a multi-line comment or tag that also holds a directive line. The directive stage writes a `<` into the comment body, `_HTML_TAG_RE` then no longer reads the comment as one tag, and the icon is written on the first pass (HEAD wrote it on the second). The `Planned (hardening)` comment region covers it; the tag regex is unchanged.
  - Shape that differs debatably in-process (dates from iteration 1, the stash): a text line directly below a stashed diagram at two columns under `- item` joins the diagram's paragraph, where HEAD started a new `<p>`. The diagram text is exact now and was indented at HEAD. Not padded with blank lines, since that would turn a tight list loose.
  - Differential against HEAD (`git archive HEAD src`), 10,503 mermaid shapes x 3 renderers. Stub: identical in all 10,503. Hugo: 8,123 identical; the other 2,380 differ only in whitespace-only lines now empty inside the block (79 exact where HEAD was not, 1,902 same uniform indent, 399 broken in both). In-process: 9,428 identical, 1,075 better by diagram text (1,074 from a uniform indent to exact, 1 from broken to exact). No output with worse diagram text than HEAD in any renderer. The round-8 tree was worse than HEAD in 494 Hugo outputs and 1 stub output.
  - Given up against the round-8 tree (exact text becomes the whole text with a uniform indent): Hugo 2,831, stub 1,961, in-process 1,250 shapes.
  - Scanner comparison over 25,076 documents: `find_fenced_blocks` (HEAD's fields), `map_prose`, `map_prose(skip_html=True)`, `map_lines`, `map_directive_lines`, and `scan_containers` identical to HEAD. `mw pre` with every stage: 5,630 differ only in emptied blank lines, 7 otherwise (2 author-written tag, 5 comment or tag holding a directive). `mw pre` twice not equal to once: 61 documents at HEAD, 39 now, none newly failing.
  - Icons, 40,000 adversarial documents: 1,039 differ from HEAD, each one holding an author-written `<pre class="mermaid">` tag.
  - For the maintainer, an idea not tried here: a single-line `<pre>` with `&#10;` for each line break might be exact in every renderer, since none strips or wraps inside one line. It changes the emitted bytes of every diagram, so it is a design decision.
- Iteration 10 fix (validator pass 10: 2 block, 4 info).
  - Finding 1 (`parity.inprocess-regression-vs-head.deferred-short-fence`). Validator said: defer only when `holding_column > 0` and the fence is at least `min(holding_column, 4)` columns deep or the line above it is non-blank. Deviated: shipped HEAD's own rule, defer only a fence indented four or more columns (`_NESTED_INDENT`); every shallower fence is emitted inline, under a list item or not. Reason: the validator's rule is still worse than HEAD in two families outside its sets, and in the tight family it keeps. (i) The second of two adjacent two-column fences under a loose item, then a text line: HEAD gives two standalone `<pre>` blocks and `<p>after</p>`, the validator's rule wraps the second `<pre>` and `after` in one `<p>`. (ii) A two-column fence directly below a `* * *` line, then a text line: same `<p>` wrap. (iii) The tight shape (`- item`, the fence at two columns, `after`): HEAD gives `<li>item<br /><pre>...</pre></li>` and `<p>after</p>` after the list; the validator's rule puts `after` inside the `<li>`. `min(holding_column, 4)` is also always 4, so half the rule never fires.
  - Impact: in-process output is byte-identical to HEAD on every document tested, so the round-9 gain (exact text for a one to three column fence under a list item, 1,075 of my shapes, 491 of the validator's tight documents) is given back; those diagrams keep the fence's indentation as at HEAD. In-process and the Python-Markdown stub now agree on every fence fewer than four columns deep.
  - Removed: `FencedBlock.holding_column`, the scanner field behind it, and `tests/test_fences_find_blocks.py`, which tested only that field. Every fence indented four or more columns has a holder (20,210 documents, none without), so the field carried nothing the indent does not.
  - Finding 2 (`parity.stub-regression-vs-head.author-mermaid-tag`). No code change, by the maintainer's decision. spec.md Icons carries `Decision (2026-11-20)` and the existing `Known gap (author-written mermaid tag)`.
  - Differential against HEAD after the last source edit. `mermaid.expand_source` and `run_pre`: identical to the round-9 tree on 16,466 of 16,466 validator documents and 10,503 of 10,503 of my shapes. My 10,503 shapes: in-process 10,503 identical to HEAD, stub 10,503 identical, Hugo 8,123 identical and 2,380 differing only in whitespace-only lines now empty (79 better, 2,301 same level, none worse). The validator's 16,466 documents: in-process 16,466 identical, stub 16,466 identical, Hugo 14,677 identical, 1,788 emptied whitespace-only lines, 1 same-score difference (an emptied line inside a Chroma code block), none worse by its scorer.
  - Seen while probing, unchanged from HEAD and left alone: `_fences` reads `* * *` as a list marker line, so a fence four columns deep under it is converted, and Python-Markdown shows it as a code block.
- Iteration 11 fix (validator pass 11: 1 block, 3 info). Prose only, by the maintainer's scope: no code path, test, or output changed.
  - Finding 1 (`prose.false-claim.deep-fence-only-under-item-or-opener`). The round 10 prose said `_fences` reads a fence four or more columns deep only under a list item or in a block opener's body. False: `_fences` reads a list marker line by its own text, so it reads a spaced thematic break as one.
  - Probed in-process, through the Python-Markdown stub, and through Hugo, repo tree against HEAD, every output equal to HEAD (a blank diagram line is the one `mw pre` difference, as since round 9).
  - `* * *`, `- - -`, `* * * *`, `*  *  *`, `- - - -`, ` * * *`, `- --`, `* **`, then a four-column mermaid fence, with a blank line between (and with none for `* * *` and `- - -`): converted. In-process `<hr />` and a code block holding the stashed `<pre>` unescaped; stub `<hr />` and a code block holding the escaped `<pre>`; Hugo `<hr>` and a code block holding the escaped `<pre>`. An eight-column fence behaves the same; a two-column fence is a plain block after the rule in all three.
  - `---`, `***`, `___`, `_ _ _`, `**  *`: not read as a list marker, the fence is not converted and shows as a code block.
  - `+ + +`, `- * *`, `* - -` (not thematic breaks) and the tab forms `*\t*\t*`, `-\t-\t-`: Python-Markdown reads a nested list and keeps the diagram in it; Hugo reads nested empty lists (a rule for the tab forms) and shows the escaped `<pre>` as a code block. Not written into spec.md.
  - Other stages four columns under `* * *` and `- - -`: `[button]`, `[youtube]`, `[annotate]`, `[tab]`, and a fence `[label]` are expanded in both paths and `mw pre` rewrites a highlight marker; the result lands in the code block (escaped; the youtube iframe unescaped in-process). Also `[codepen]`, `[lightbox]`, `[grid]` in `mw pre` only. Icons not probed (needs a pack).
  - A second shape found by the same probe: a list marker line directly under a paragraph line (`para`, then `- item`, `1. item`, or `2. item`). Python-Markdown reads it as paragraph text, so a four-column fence or `[button]` after a blank line lands in a code block, and with no blank line the `<pre>` joins the paragraph. Hugo starts a list at `- item` and `1. item` and not at `2. item`. Same at HEAD.
  - Also seen, not written into spec.md: `<div>`, then `- item`, a blank line, a four-column fence. Converted; Python-Markdown keeps it raw inside the HTML block, Hugo shows a code block.
  - Edits: spec.md gains `Known gap (line `_fences` reads as a list marker)` under Rules Every Feature Follows (three lines), the Mermaid sentence loses "only" and is split in two, and `Known gap (mermaid fence four or more columns past its list item)` gains three lines. CLAUDE.md pattern 5 and the 26 row, and the `_NESTED_INDENT` comment and `_expand_lines` docstring in src/markwright/mermaid.py, lose the "only" claim. docs/extensions/mermaid.md does not say "only" and is unchanged.
  - Info findings 2 to 4 (no edit this round): carried in the State entries at the top of this section for the finalize commit message.
- Iteration 12 fix (validator pass 12: 1 block, 1 info). Deletion only, by the maintainer's choice ("Delete, then quick check").
  - Finding 1 (`prose.false-claim.hugo-2-item-diagram-code-block`). A sentence I added in round 11 beyond the pass-11 finding said Hugo reads `2. item` after `para` as paragraph text and the diagram as a code block. False with no blank line above the fence: Hugo joins the raw `<pre>` to that paragraph. My round 11 probe of `2. item` had a blank line only.
  - Deleted from spec.md, nothing added and nothing reworded: the sentence starting "A list marker line directly under a paragraph line" (Rules Every Feature Follows, was line 178) and the sentence starting "Under a list marker line that directly follows a paragraph line" (Mermaid, was line 312). The paragraph-then-marker shape is now recorded only in the iteration 11 entry above, not in spec.md.
  - `grep -rn "paragraph line" spec.md CLAUDE.md docs src` leaves two hits, neither about that shape: spec.md Mermaid ("its own block beside a paragraph line or a table", a diagram at column 0) and the `_indented_code_lines` docstring in src/markwright/_fences.py (a lazy continuation line, HEAD text).
  - The maintainer accepted HEAD's four-column rule and dropped a mermaid fence in a list item as a goal.
  - Info finding: the pass-11 block is resolved.

## Prompt Inventory

| Prompt/Command | Action Taken | Outcome |
|---|---|---|
| Mode: implement, Step 9 | Wrote failing tests, moved the icons pre priority, stashed mermaid diagrams in-process | Tree dirty, tests green |
| Mode: fix, iterations 1 to 8 | Content-column rules for the emitted `<pre>`, a second scanner chain, lazy-line and marker-only rules | Green each round; each pass found a new regression against 9a76768 in one renderer |
| Mode: fix, iteration 9 (second executor, cold) | Removed `content_column` and the content chain; `mw pre` back to the every-line indent | Diagram text never worse than 9a76768 in any renderer; pass 10 still found two blocks |
| Mode: fix, iteration 10 | Shipped 9a76768's four-column deferral rule, removed `FencedBlock.holding_column` and its test file, wrote the icons Decision | In-process and stub byte-identical to 9a76768 |
| Mode: fix, iteration 11 | Prose only: dropped a false "only", wrote the spaced thematic break Known gap | One sentence beyond the finding was false |
| Mode: fix, iteration 12 | Deleted the two sentences added beyond the finding | Validator pass 13 clean |
| Mode: finalize | Ran the gate, wrote this summary, the lessons, and the commit message, committed, pushed | One commit |

## Efficiency Insights

**What went well:**
- A differential against a `git archive` copy of the previous commit, over 10,503 generated mermaid shapes and the validator's 16,466 documents in all three renderers, turned "is this worse than before" into a count.
- Subtraction in round 9 ended the trade: removing the content-column rules left the one emission no renderer reads worse than the previous commit.

**What could improve:**
- The plan line about a fence indented one to three columns was a claim about three renderers that nobody had measured. Eight rounds went to finding out that no rule tried makes it hold.
- In round 11 I wrote two sentences beyond the finding's scope, from a probe that covered one of the two variants, and round 12 existed only to delete them.
- A second executor had to take round 9 over cold, and its context was compacted twice after that.

**Course corrections:**
- Round 9: from adding rules to removing them.
- Round 10: from the validator's suggested deferral rule to the previous commit's own rule, after showing the suggested rule was worse in three families.
- Round 12: Mason dropped the list-item mermaid goal.

## Process Improvements

- Probe a plan line that predicts renderer behavior before it becomes a step, on every renderer the project supports.
- Give the validator a review bar of documented, supported behavior. "No generated document worse than the previous commit in any renderer" has no end.
- A fix round answers the finding and stops; a new claim needs its own probe of every variant it names.

## Observations

- The one design idea left untried: a single-line `<pre>` with `&#10;` for each line break might be exact in every renderer, since none strips or wraps inside one line. It changes the emitted bytes of every diagram, so it is Mason's decision.
- `_fences` reads a spaced thematic break (`* * *`, `- - -`) as a list marker line. It did before this batch too; it is now a Known gap in spec.md.
- No test names `custom_fences`. The inertness sentence in spec.md and docs/extensions/mermaid.md rests on a probe.

## Info Findings Carried Forward

- The plan's line about a fence indented one to three columns is not delivered: `Known gap (indented mermaid fence)`.
- A mermaid fence in a list item below four columns keeps the previous commit's behavior, by Mason's decision: `Known gap (mermaid fence under a list item at fewer than four columns)`.
- src/markwright/fence.py gained no mermaid skip, since mermaid at 45 runs ahead of fence at 40.
- The `custom_fences` inertness was confirmed by probe and has no test.
- `_fences` reads a spaced thematic break as a list marker line: `Known gap (line _fences reads as a list marker)`.
- `mw pre` reads an author-written block that opens with the mermaid stage's exact tag as an emitted diagram: `Decision (2026-11-20)` in spec.md Icons.
- The CHANGELOG step (Step 28) must not claim an in-process mermaid fix; what changed for users is the `mw pre` icons order and the empty blank diagram line.

## Suggested Skills for Next Session

- python:python: Step 10 (the highlight escape in split spans, #31) is Python work under the repo's profile.
