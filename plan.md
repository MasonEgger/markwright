# Plan: 0.4.0 Adversarial Review Fixes (Issue #29)

The 2026-11-01 adversarial review of the `material-parity-0.4.0` branch (the six 0.4.0 extensions plus the #20 fix) returned eight findings, filed as issue #29: one HTML-corrupting bug, three parity gaps between `mw pre` and the in-process render, and four conformity items.
Mason chose to fix all eight before the 0.4.0 PR, exempting `_fences` and `_markers` from the public-API-only test rule and rewriting the rest.

The findings, in the order this plan fixes them:

1. block: two chained `[annotate]` markers claim the same `<ol>`, and the tag comes out as `<ol class="mw-annotated">class="mw-annotations" ...>` (`annotate._locate` searches for the list to the end of the page instead of to the next marker).
2. warn: `_fences` counts spaces only, so a tab-indented in-list fence is not seen as code, and `mw pre` expands directives inside it; a 4-space indented code block is treated the same way.
3. warn: `map_prose` skips only fenced code and inline code spans, so `mw pre` rewrites highlight markers and icon shortcodes inside an HTML tag's attributes, an autolink, and indented code.
4. warn: the icons InlineProcessor at 175 runs before links, images, autolinks, and inline HTML (90), so in-process the stashed SVG lands raw inside `alt`, `title`, `href`, and inline-HTML attributes; highlight at 175 has the same exposure (`<span title="<^>s<^>">` renders `title="<mark>s</mark>"`).
5. warn: four test files import private modules with no precedent on main; `_fences` and `_markers` are exempted as self-contained algorithms, `test_html_helpers.py` is rewritten through grid and annotate.
6. nit: `_apply_markers` in grid and annotate is a pass-through for `apply_html`.
7. nit: five test files lack `from __future__ import annotations`.
8. nit: `_fences.py`'s ABOUTME and the CLAUDE.md priority table are stale.

Two halves of finding 3 and 4 stay out of scope and are recorded under Deferred in spec.md: `mw pre` has no Markdown parser, so a marker or shortcode inside an image's alt text, a link title, or the text content of a raw HTML block is still rewritten by `mw pre` and left literal in-process.
The fix here covers what a single-line token grammar can see (HTML tags, comments, autolinks) and what the CommonMark line scanner can see (tabs, indented code).

No dependency changes.
Every change is inside `src/markwright/**`, `tests/**`, `docs/**`, `CHANGELOG.md`, and `CLAUDE.md`, within the spec's `paths:` fence.
The version bump stays Mason's release step.

## Current Status

- [ ] Section 1: Annotate chaining (Step 1)
- [ ] Section 2: Code detection in `_fences` (Steps 2, 2b, 3)
- [ ] Section 3: Inline processor priority (Step 4)
- [ ] Section 4: Test policy and conformity (Steps 5-6)

## Ordering and Dependencies

- Section 1 is the one HTML-corrupting bug and stands alone.
- Section 2 changes what `_fences` counts as code: Step 2 adds tab-aware indentation and indented-code detection to both mappers (and resolves the Step 1 info finding from the #20 cycle, the duplicated fenced-line set); Step 3 adds HTML-tag skipping to `map_prose`. Step 3's round-trip case needs Step 4, so its property-grammar addition lands there.
- Step 2b, added after Step 2's implement pass, moves the ten in-process directive preprocessors onto `map_lines` so a directive line inside indented code stays literal in both paths, and restores the indented-code round-trip cases Step 2 dropped.
- Section 3 moves the two InlineProcessors from 175 to 85 and extends the round-trip grammar with the inline-HTML-attribute case that Steps 3 and 4 together make parity-safe.
- Section 4 is test policy and refactoring with no behavior change, last so every behavior fix is already guarded.

## Why 85 for the Inline Processors

Python-Markdown's built-in inline priorities: backtick 190, escape 180, reference 170, link 160, image_link 150, image_reference 140, short_reference 130, autolink 120, automail 110, linebreak 100, html 90, entity 80, not_strong 70, em_strong 60, em_strong2 50.
At 175 a shortcode or marker is matched before the link, image, autolink, and inline-HTML processors see the text, so its placeholder ends up inside an attribute value.
At 85 those processors run first (an autolink's text is an `AtomicString`, an inline tag is stashed whole), and link text and emphasis still recurse into child text, so an icon or marker inside `[text](url)` or `*em*` still renders.
The `\<^>` escape (180) and inline code (190) are unaffected either way.
This is a bug fix inside the existing output contract, not a parity divergence: prose output is byte-identical; only text that was already broken (a raw `<svg>` or `<mark>` inside an attribute) changes.

---

## Section 1: Annotate Chaining

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: none

### Step 1: Bound the Annotation-List Search by the Marker's Region

**NOTE**: `annotate._locate` finds the annotated block within `range(token_index + 1, block_end)` but then finds the list within `range(block_close + 1, len(tokens))`, skipping every comment, including the next `mw-annotate` marker.
`find_markers` already gives each marker a `block_end` (the next same-name marker's token index, or the token count).
The fix is to bound the list search by `block_end` too; a marker whose block is followed by another marker before any `<ol>` is then skipped fail-soft with the existing "no annotation list after the block" reason, its comment removed, and the next marker annotates normally.
`block_number` counts only annotated blocks (`test_skipped_marker_does_not_use_a_number`), so the second marker's ids start at `mw-annotation-1-1`.
Do not add an overlap guard to `_html.apply_edits`: once `_locate` is bounded nothing public can reach it, and an unreachable branch fails the coverage rule.

```text
1. RED: Write the chained-marker tests first:
   - Modify tests/test_annotate.py, class TestSkippedMarkers:
     - Test that a marker whose block is followed by another marker is skipped and reported: apply_html(MARKER + "\n<p>a (1)</p>\n" + MARKER + "\n<p>b (1)</p>\n" + ONE_NOTE, skip_reasons) leaves skip_reasons == ["Skipping mw-annotate marker with no annotation list after the block"], contains exactly one '<ol class="mw-annotations"', does not contain 'class="mw-annotated">class=', and links the second block's (1) to "#mw-annotation-1-1".
     - Test that both markers are removed from that result (the string "mw-annotate:" does not appear).
   - Modify tests/test_annotate.py, class TestInProcess:
     - Test that render_annotate("[annotate]\nPara (1).\n\n[annotate]\n1. Item (1)\n\n<!-- split -->\n\n1. Note\n") contains exactly one '<ol class="mw-annotations"' and does not contain 'class="mw-annotated">class=' (today the output holds '<ol class="mw-annotated">class="mw-annotations" data-mw-version="1">').
   - Confirm both fail.

2. GREEN: Bound the search:
   - In src/markwright/annotate.py, _locate: change the list search range from range(block_close + 1, len(tokens)) to range(block_close + 1, block_end).
   - Update _locate's docstring: the list is the first thing after the block and before the next marker that is not a comment or whitespace.

3. REFACTOR: none expected. The existing test_ids_count_per_page guards the normal two-marker case (block numbers 1 and 2).

4. Verify tests/test_annotate.py passes in full.

5. Run `just check` and confirm green.
```

---

## Section 2: Code Detection in `_fences`

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: none

### Step 2: Tab-Aware Indentation and Indented Code Blocks

**NOTE**: `_FENCE_OPEN_RE`, `_LIST_ITEM_RE`, and the indent math in `find_fenced_blocks` and `_fence_can_open` count spaces (`[ ]*`, `lstrip(" ")`), while Python-Markdown expands tabs to four columns.
So `"- item\n\n\t```\n\t[button /x Go]\n\t```"` is not a fence to `mw pre`, and both `map_lines` and `map_prose` transform its content.
Separately, neither mapper skips an indented code block: `"para\n\n    [button /x Go]\n"` is code in-process (verified: `para\n\n    code` renders `<pre><code>`) but `map_lines` expands the button, dropping its indentation.
Python-Markdown's rules, verified in-process: a 4-column line directly after a paragraph line is a lazy continuation (`para\n    more` is one paragraph); a 4-column line after a blank line at top level is code; a 4-column line after a blank line under a list item is list content; a tab counts as four columns (`\tcode` at top level is code, `- item\n\n\tcode` is list content).
`_fence_can_open` already answers "is this four-plus-column line list content rather than indented code"; reuse it for the indented-code rule (rename it if the new call site reads wrong) rather than writing a second list-item scanner.
Known imprecision, documented in the docstring: a line indented eight or more columns under a list item is indented code to Python-Markdown but list content to this scanner, so it is still transformed; erring toward transforming is the safer failure.
`FencedBlock.indent` becomes the tab-expanded indentation (spaces), which the fence and mermaid pre stages repeat on the lines they insert; four spaces and a tab are the same column to every renderer.
`fence._expand_lines` matches directive lines with `.strip()` and passes content lines through unchanged, so a tab-indented fence's content keeps its tabs.
This step also resolves the #20 cycle's open info finding: the fenced-line index set is built twice; one helper now builds the full skipped set for both mappers.

```text
1. RED: Write the scanner tests first:
   - Modify tests/test_fences_map_lines.py (exempt private-module test; see Step 5):
     - Test a tab-indented in-list fence is skipped: map_lines("- item\n\n\t```\n\thit\n\t```", transform) keeps "\thit" (transform returns ["X"] when line.strip() == "hit", else [line]).
     - Test a top-level indented code block is skipped: map_lines("para\n\n    hit\n", transform) keeps "    hit".
     - Test a tab-indented top-level line is code: map_lines("para\n\n\thit", transform) keeps "\thit".
     - Test fence-shaped lines at four columns outside a list are code: map_lines("para\n\n    ```\n    hit\n    ```", transform) keeps "    hit".
     - Test an indented line under a list item is transformed: map_lines("- item\n\n    hit", transform) == "- item\n\nX".
     - Test a four-column line directly after a paragraph line is a lazy continuation and is transformed: map_lines("para\n    hit", transform) == "para\nX".
     - Test a blank line inside an indented code block does not end it: map_lines("para\n\n    hit\n\n    hit\n", transform) keeps both "    hit" lines.
     - Test the first non-blank line indented less than four columns ends the block: map_lines("para\n\n    code\nhit", transform) == "para\n\n    code\nX".
   - Modify tests/test_fences_map_prose.py:
     - Test a top-level indented code block is skipped: map_prose("para\n\n    code here\n", str.upper) == "PARA\n\n    code here\n".
     - Test a tab-indented in-list fence is skipped: map_prose("- item\n\n\t```\n\tcode\n\t```\nafter", str.upper) keeps "\tcode" and uppercases "after".
   - Modify tests/test_fence.py (public API): expand_source("- item\n\n\t```\n\t[label a.sh]\n\techo\n\t```") removes the "[label a.sh]" line, writes the mw-fence marker carrying label "a.sh" at four-space indentation followed by a blank line, and keeps "\t```" and "\techo" unchanged.
   - Modify tests/test_highlight.py, class TestHighlightExpandSource: a "<^>x<^>" inside a tab-indented in-list fence is unchanged by expand_source; "para\n\n    <^>x<^>\n" is unchanged by expand_source.
   - Modify tests/test_button.py: expand_source("para\n\n    [button /x Go]\n") is unchanged; expand_source("- item\n\n\t```\n\t[button /x Go]\n\t```") is unchanged.
   - Modify tests/test_roundtrip.py:
     - Add a composite _directive_in_tab_fence that draws one directive from the same five as _directive_in_fence and returns f"- item\n\n\t```\n\t{directive}\n\t```".
     - Add a composite _directive_in_indented_code that draws one of those directives and returns f"para\n\n    {directive}".
     - Add both to the st.one_of block sampler in TestRoundTripProperty.
     - Add INDENTED_DIRECTIVE_FIXTURE (a tab-indented in-list fence holding "[button primary /start Get started]" and a four-space indented block holding "[grid]") and a TestRoundTripIndentedDirective class with the same two assertions TestRoundTripFencedDirective makes.
   - Confirm each new test fails for the right reason (the directive is expanded, the marker is absent, or the pipeline diverges).

2. GREEN: Implement in src/markwright/_fences.py:
   - Add _indent_width(line: str) -> int: the leading-space count of line.expandtabs(4).
   - Match _FENCE_OPEN_RE and _LIST_ITEM_RE against line.expandtabs(4); measure every indentation in find_fenced_blocks and _fence_can_open with _indent_width (the closing-fence check included). FencedBlock.indent is the expanded indentation; say so in its docstring.
   - Add _indented_code_lines(lines: list[str]) -> set[int]: a non-blank line of four or more columns that follows a blank line (or starts the document) and that _fence_can_open does not place under a list item opens an indented code block; the block continues through blank lines and lines of four or more columns; the first non-blank line of fewer than four columns ends it.
   - Add _code_line_indexes(lines: list[str]) -> set[int]: the union of every closed fence's lines (from find_fenced_blocks) and _indented_code_lines; map_prose and map_lines both call it, replacing their duplicated comprehensions. Rename map_prose's groupby key from is_fenced to is_code.
   - Update the docstrings of find_fenced_blocks, map_prose, and map_lines to name tabs and indented code, and the module's ABOUTME line 2 to name its current callers: the fence, mermaid, highlight, and icons pre stages and, through map_lines, every directive-line stage.

3. REFACTOR: keep the scanner as one pass; a second list-item scanner or a second fence regex is a smell. Confirm no stage outside _fences changed (fence, mermaid, highlight, icons, and the ten directive stages all pick the change up through the module).

4. Document:
   - CHANGELOG.md, under "## [Unreleased]" / "### Fixed", add: "`mw pre` now reads a tab as four columns when scanning fences, so a tab-indented fence inside a list item is code to every pre stage, and it leaves top-level indented code blocks alone, matching the in-process render (#29)." One sentence per line, straight quotes, no em-dashes, no banned vocabulary.
   - CLAUDE.md, Architecture, the _fences.py bullet: add tabs and indented code to what the scanner recognizes.

5. Verify every existing suite passes unchanged (tests/test_fence.py, tests/test_highlight.py, tests/test_mermaid.py, tests/test_icons.py, the ten directive-stage suites, tests/test_roundtrip.py); then run `just check` and `just test-integration` and confirm both green.
```

### Step 2b: In-Process Directive Preprocessors Skip Code

**NOTE**: Added 2026-11-07 by Mason's decision, after Step 2's implement pass found that the plan's premise was wrong for directive lines.
At priority 20 `pymdownx.superfences` has already stashed every fence, but nothing has stashed an indented code block, and the ten directive preprocessors (youtube, slideshow, image_compare, codepen, twitter, instagram, button, lightbox, grid, annotate) transform every line.
Verified in-process: `para\n\n    [button /x Go]` renders `<p><a class="mw-button" href="/x">Go</a></p>`, so the button escapes the code block, and `para\n\n    [grid]` puts the escaped `mw-grid` marker inside `<pre><code>`.
After Step 2, `mw pre` leaves both literal, so the two paths disagree.
The fix routes each in-process `Preprocessor.run` through the same `_fences.map_lines` the `expand_source` stages use: `return map_lines("\n".join(lines), transform).split("\n")`, with the same per-line transform the stage already applies.
The source lines hold no newline, so the join and split are lossless.
The fence lines superfences stashed are placeholder lines by then, so only the indented-code rule changes anything in-process.
This changes released behavior for the six embeds: a directive line in an indented code block no longer renders an embed in-process.
That is a bug fix, since the embed escaped the code block, and it gets a CHANGELOG line.
Step 2's dropped round-trip cases come back here.

```text
1. RED: Write the in-process tests first:
   - In each of tests/test_{youtube,slideshow,image_compare,codepen,twitter,instagram,button,lightbox}.py, using that file's existing in-process render helper (add one in the file's style if it has none): a document "para\n\n    <directive>\n" with a directive the stage recognizes renders the directive literally inside <pre><code> and emits none of the stage's markup.
   - tests/test_grid.py: render_grid("para\n\n    [grid]\n\n- a\n") has no "mw-grid" anywhere and a plain <ul>; the <pre><code> holds "[grid]".
   - tests/test_annotate.py: render_annotate("para\n\n    [annotate]\n\nText (1)\n\n1. note\n") has no "mw-annotat" anywhere; the <pre><code> holds "[annotate]".
   - Guard tests, which must pass before and after: in each of the ten files, a directive line under a list item ("- item\n\n    <directive>") still expands in-process, since that is list content and not code.
   - tests/test_roundtrip.py: restore the `_directive_in_indented_code` composite Step 2 dropped (f"para\n\n    {directive}" over the same five directives as _directive_in_fence), add it to the st.one_of sampler in TestRoundTripProperty, and restore the four-space "[grid]" block in INDENTED_DIRECTIVE_FIXTURE so TestRoundTripIndentedDirective covers both shapes.
   - Confirm the ten in-process tests and the restored round-trip cases fail and the ten guard tests pass.

2. GREEN: Route the ten preprocessors through map_lines:
   - In src/markwright/{youtube,codepen,twitter,instagram}.py, the Preprocessor.run builds its output line by line through `_render_match(line, self.load)` and the stash. Move that per-line body into a closure returning a one-element list and return `map_lines("\n".join(lines), closure).split("\n")`.
   - In src/markwright/{slideshow,image_compare,button,lightbox}.py, do the same with that file's in-process per-line expression, keeping the stash call where the file has one.
   - In src/markwright/{grid,annotate}.py, return `map_lines("\n".join(lines), _transform_line).split("\n")`.
   - map_lines is already imported in each module for expand_source.

3. REFACTOR: where a module's expand_source and its Preprocessor.run now differ only in the per-line transform, leave them as two calls. The two paths emit different HTML (inline versus stashed), so they are not duplicate knowledge.

4. Document:
   - CHANGELOG.md, under "## [Unreleased]" / "### Fixed", rewrite Step 2's continuation line so it claims parity now that both paths agree: `mw pre` and the in-process render both leave a directive line inside a top-level indented code block literal; before this, in-process rendered the embed or button out of the code block, and grid and annotate wrote their marker into it (#29).
     One sentence per line, straight quotes, no em-dashes, no banned vocabulary.
   - CLAUDE.md, the Processor Priority Reference rows for button, lightbox, grid, annotate, and the embeds: add that they skip fenced and indented code through `_fences.map_lines`.

5. Verify every existing suite passes, plus the new and restored tests; run `just check` and `just test-integration` and confirm both green.
```

### Step 3: Skip HTML Tags in `map_prose`

**NOTE**: `map_prose` skips inline code spans inside a prose chunk through `_INLINE_CODE_RE`; it has no idea of HTML.
So `mw pre` rewrites `:octicons-rocket-16:` or `<^>s<^>` inside `<span title="...">` into markup inside an attribute (broken HTML), and inside `<https://x.test/...>` into markup inside a URL.
In-process, Python-Markdown's inline `html` processor (90) stashes a tag whole and `autolink` (120) makes the URL atomic, so neither is ever prose.
Mirror Python-Markdown's inline HTML_RE shape (a tag `</?[A-Za-z][^<>]*>` or a comment `<!-- ... -->`) as a second skipped-span grammar; the `[A-Za-z]` first character is what keeps `a < b and c > d` prose, exactly as Python-Markdown does.
The tag branch is deliberately a superset of Python-Markdown's (which excludes `@` from the tag name so `<a@b.c>` goes to automail): an autolink and an automail start with a letter too and must be skipped for the same reason.
Combine the code-span and tag grammars into one alternation so whichever starts first is skipped; a tag's text content between its start and end tags stays prose.
The text content of a raw HTML block (`<div>\n:name:\n</div>`) is out of scope (Deferred in spec.md): detecting it needs an HTML-block parser, and `mw pre` rewriting it is the more useful behavior until a Decision says otherwise.
The round-trip grammar case for this step lands in Step 4, because in-process highlight at 175 still mangles the attribute until Step 4 moves it.

```text
1. RED: Write the tag-skipping tests first:
   - Modify tests/test_fences_map_prose.py (exempt private-module test):
     - Test an attribute value inside a start tag is skipped and the text after the tag is transformed: map_prose('<span title="hit">x</span> hit', transform) == '<span title="hit">X</span> HIT' with transform = lambda prose: prose.replace("hit", "HIT").replace("x", "X") (the tag's text content "x" is still prose).
     - Test an HTML comment is skipped, including one spanning lines: map_prose("<!-- hit -->\nhit", transform) and map_prose("<!--\nhit\n-->\nhit", transform) transform only the final "hit".
     - Test an autolink is skipped: map_prose("<https://x.test/hit> hit", transform) transforms only the trailing "hit".
     - Test a bare less-than sign is prose: map_prose("a < hit and c > d", transform) transforms "hit".
     - Test a code span containing a tag is still a code span: map_prose("`<b title=\"hit\">` hit", transform) transforms only the trailing "hit".
   - Modify tests/test_icons.py, class TestIconsExpandSource: expand_source('<span title=":octicons-rocket-16:">x</span> :octicons-rocket-16:', {"packs": packs}) keeps the attribute literal and wraps only the trailing shortcode.
   - Modify tests/test_highlight.py, class TestHighlightExpandSource: expand_source('<span title="<^>s<^>">y</span>') is unchanged; expand_source("<https://x.test/<^>q<^>>") is unchanged; expand_source('<span title="x"><^>y<^></span>') wraps y (a marker in a tag's text content is still prose).
   - Confirm each fails (the attribute or URL is rewritten).

2. GREEN: Implement in src/markwright/_fences.py:
   - Add _HTML_TAG_RE = re.compile(r"<(?:/?[A-Za-z][^<>]*|!--(?:(?!<!--|-->).)*--)>", re.DOTALL) with a comment naming Python-Markdown's inline HTML_RE as the shape and why autolinks are covered.
   - Build _SKIPPED_SPAN_RE as the alternation of the inline-code grammar and _HTML_TAG_RE; map_prose iterates its matches in place of _INLINE_CODE_RE's.
   - Update map_prose's docstring: fenced code, indented code, inline code spans, HTML tags, HTML comments, and autolinks pass through; transform sees the text between them.

3. REFACTOR: none expected beyond the regex composition. Confirm the inline-code tests in tests/test_fences_map_prose.py still pass unchanged.

4. Document:
   - CHANGELOG.md, "### Fixed": "`mw pre` no longer rewrites a highlight marker or an icon shortcode inside an HTML tag, an HTML comment, or an autolink; the in-process render never touched them (#29)."
   - CLAUDE.md, pattern 3 (Highlight) and pattern 6 (Icons): the pre stage skips fenced code, indented code, inline code spans, and HTML tags.

5. Verify tests/test_fences_map_prose.py, tests/test_highlight.py, and tests/test_icons.py pass; run `just check` and confirm green.
```

---

## Section 3: Inline Processor Priority

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: none

### Step 4: Move the Icons and Highlight InlineProcessors to 85

**NOTE**: Verified in-process today: `![Star :octicons-rocket-16:](a.png)` renders `alt="Star <svg ...` (the attribute breaks at the SVG's first quote); `<span title="<^>s<^>">y</span>` renders `title="<mark>s</mark>"`; `![Star <^>x<^>](a.png)` renders `alt="Star x"` (the markers vanish); `<https://x.test/<^>q<^>>` renders the href without the markers and the link text with a `<mark>`.
At 85 every one of these keeps the attribute literal, and `[go :octicons-rocket-16:](/a)`, `[go <^>w<^>](/a)`, `*em :octicons-rocket-16:*`, and `*em <^>z<^>*` still render the icon or mark inside the link text or emphasis (the reviewer confirmed icons at 85; the same mechanism applies to highlight).
See "Why 85 for the Inline Processors" above.
`icons.py` registers through `IconInlineProcessor` in `extendMarkdown`; `highlight.py` registers `HighlightInlineProcessor` under the name `do_highlight_inline`.
This step also fixes the two stale CLAUDE.md table rows (finding 8): the 175 row, and the 50 row, which calls icons an in-process Preprocessor when 50 is only its `mw pre` registry priority.

```text
1. RED: Write the in-process attribute tests first:
   - Modify tests/test_icons.py, class TestIconsInProcess (use the packs fixture and render_icons):
     - Test an image's alt text keeps the shortcode literal: render_icons("![Star :octicons-rocket-16:](a.png)", packs) contains 'alt="Star :octicons-rocket-16:"' and no "<svg".
     - Test a link title keeps it literal: render_icons('[go](/a ":octicons-rocket-16: tip")', packs) contains 'title=":octicons-rocket-16: tip"'.
     - Test an autolink keeps it literal: render_icons("<https://x.test/:octicons-rocket-16:>", packs) contains 'href="https://x.test/:octicons-rocket-16:"' and no "<svg".
     - Test an inline HTML attribute keeps it literal: render_icons('<span title=":octicons-rocket-16:">y</span>', packs) contains 'title=":octicons-rocket-16:"'.
     - Test link text still renders the icon: render_icons("[go :octicons-rocket-16:](/a)", packs) has the mw-icon span inside the <a>.
     - Test emphasis still renders the icon: render_icons("*em :octicons-rocket-16:*", packs) has the mw-icon span inside the <em>.
   - Modify tests/test_highlight.py, class TestInlineHighlight (use _render):
     - Test _render('<span title="<^>s<^>">y</span>') contains 'title="<^>s<^>"' and no "<mark>".
     - Test _render("![Star <^>x<^>](a.png)") contains 'alt="Star <^>x<^>"'.
     - Test _render("<https://x.test/<^>q<^>>") contains 'href="https://x.test/<^>q<^>"' and no "<mark>".
     - Test _render("[go <^>w<^>](/a)") still contains "<mark>w</mark>" inside the <a>.
     - Test _render("*em <^>z<^>*") still contains "<mark>z</mark>" inside the <em>.
   - Modify tests/test_roundtrip.py: extend _prose_block so it can draw an inline tag with a marker in its attribute, f'<span title="<^>{word}<^>">{phrase}</span>', and add that shape to FIXTURE's prose (the pipeline leaves the attribute literal after Step 3, the in-process render after this step).
   - Confirm the attribute tests fail today and the link-text and emphasis tests pass today (they guard the move).

2. GREEN: Re-register both processors:
   - In src/markwright/icons.py, IconsExtension.extendMarkdown: register at 85; docstring: after links, images, autolinks, and inline HTML (90) so a shortcode inside an attribute stays literal, before entities and emphasis.
   - In src/markwright/highlight.py, HighlightExtension.extendMarkdown: register do_highlight_inline at 85 with the same docstring note.

3. REFACTOR: none expected.

4. Document:
   - CLAUDE.md, Processor Priority Reference: change the 175 row to "| 85 | InlineProcessor | highlight, icons | After links, images, autolinks, and inline HTML (90), so a marker or shortcode inside an attribute stays literal; before entities and emphasis |"; change the 50 row to "| 50 | pre stage (`mw pre` only) | icons | The registry's pre priority; in-process icons registers only the InlineProcessor |"; update pattern 6's "(175)" to "(85)".
   - docs/index.md, items 3 and 5: priority 175 becomes 85, and item 5 says icons has a pre stage (priority 50) for `mw pre` and an InlineProcessor (priority 85) in-process.
   - CHANGELOG.md, "### Fixed": "The highlight InlineProcessor runs after links, images, and inline HTML, so a `<^>` marker inside an image's alt text, a link title, or an HTML attribute stays literal instead of being dropped or written into the attribute (#29)." Icons is unreleased, so it gets no entry.

5. Verify tests/test_icons.py, tests/test_highlight.py, and tests/test_roundtrip.py pass; run `just check` and `just docs-build` and confirm both green.
```

---

## Section 4: Test Policy and Conformity

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: none

### Step 5: Public-API Coverage for the `_html` Helpers (task)

**NOTE**: CLAUDE.md's Testing Approach says tests run against the public API only, and `main` has no test importing a private module.
This branch added four: `tests/test_fences_map_lines.py`, `tests/test_fences_map_prose.py`, `tests/test_html_helpers.py`, and `tests/test_markers.py`.
Mason's call: `_fences` (the CommonMark scanner) and `_markers` (the marker-comment contract) are self-contained algorithms with their own contracts and stay tested directly, written into CLAUDE.md as the exemption; `_html.add_classes` and `_html.matching_end` are covered through `grid.apply_html` and `annotate.apply_html` instead, and `tests/test_html_helpers.py` is deleted.
Coverage is reported, not gated, but CLAUDE.md says to test or delete whatever it shows uncovered, so `_html.py` must stay at 100% line and branch after the deletion.
The hand-written HTML fixtures the existing `apply_html` tests use are the pattern; `apply_html` takes any renderer's HTML, so a self-closing `<div/>` in a fixture is a legitimate input even though Python-Markdown never emits one.

```text
1. Scope:
   - Artifact(s): tests/test_html_helpers.py (deleted), tests/test_grid.py, tests/test_annotate.py, CLAUDE.md (Testing Approach).
   - Desired end state: no test imports markwright._html; every case tests/test_html_helpers.py held is asserted through grid or annotate apply_html or is named as already covered; `just check` reports _html.py at 100% line and branch; CLAUDE.md states the exemption.

2. Tooling:
   - Skills: python:python
   - MCPs: none
   - External: none

3. Do the work:
   - Map each of the nine cases in tests/test_html_helpers.py to its public-API home before deleting anything:
     - add_classes "new classes in front of existing": already covered by tests/test_grid.py::TestApplyHtml::test_existing_classes_follow_the_added_ones and tests/test_annotate.py::TestProse::test_existing_classes_follow_the_added_ones.
     - add_classes "adds a class attribute when the tag has none": already covered by tests/test_grid.py::TestApplyHtml::test_plain_marker_adds_only_the_grid_class.
     - add_classes "added attrs after existing attributes": add to tests/test_annotate.py::TestProse: apply_html(MARKER + "\n<p>a (1)</p>\n<ol class=\"steps\" id=\"x\">\n<li>x</li>\n</ol>") contains '<ol class="mw-annotations steps" id="x" data-mw-version="1">'.
     - add_classes "added attrs when the tag has no class": add to tests/test_annotate.py::TestProse: the list '<ol id="x">' becomes '<ol class="mw-annotations" id="x" data-mw-version="1">'.
     - matching_end "simple element" and "never closed": already covered by the annotate TestProse and TestSkippedMarkers suites (test_unclosed_block_is_skipped_and_reported, test_unclosed_list_is_skipped_and_reported).
     - matching_end "counts nesting": already covered by tests/test_annotate.py::TestProse::test_nested_same_tag_block_ends_at_its_own_close.
     - matching_end "ignores other tag names and self-closing tags": add to tests/test_annotate.py::TestProse: a block "<p>a<br/>(1)</p>" followed by ONE_NOTE is annotated whole (the <p> closes at its own </p>).
     - matching_end "ignores a self-closing tag of the same name": add to tests/test_annotate.py::TestProse: a block "<div><div/>(1)</div>" followed by ONE_NOTE is annotated whole and the link lands inside the outer div.
   - Delete tests/test_html_helpers.py.
   - Add to tests/test_fences_map_lines.py and tests/test_fences_map_prose.py nothing; their ABOUTME line 2 already states the exemption. Confirm tests/test_markers.py's ABOUTME line 2 states it too (edit it if not).
   - CLAUDE.md, Testing Approach, the "Unit tests are ..." bullet: after "(no imports of private names)" add: "Exception: `_fences` (the CommonMark scanner) and `_markers` (the marker-comment contract) are self-contained algorithms with contracts of their own and are tested directly in `tests/test_fences_*.py` and `tests/test_markers.py`, which may import `_html.tokenize` to build their inputs; every other private module is covered through the stage functions."

4. Verify:
   - `grep -rn "markwright\._" tests/` lists only tests/test_fences_map_lines.py, tests/test_fences_map_prose.py, and tests/test_markers.py.
   - `just check` green with src/markwright/_html.py at 100% line and branch in the coverage report.

5. Document:
   - CLAUDE.md edit above; none elsewhere.
```

### Step 6: Fold `_apply_markers` and Add the Future Import (task)

**NOTE**: In `grid.py` and `annotate.py`, `apply_html` only forwards to `_apply_markers(rendered_html, skip_reasons)`, and the postprocessor calls `_apply_markers(text, None)`.
Fence's split earns its place by resolving options first; these two extensions have no options, so the helper is a pass-through (the profile: a private helper earns extraction by a second caller or a separate concern, never by shortening its caller).
Separately, CLAUDE.md requires `from __future__ import annotations` in every source file; tests/test_annotate.py, tests/test_grid.py, and tests/test_markers.py (this branch) and tests/test_fence.py and tests/test_highlight.py (older) lack it.
No behavior changes in this step.

```text
1. Scope:
   - Artifact(s): src/markwright/grid.py, src/markwright/annotate.py, tests/test_annotate.py, tests/test_fence.py, tests/test_grid.py, tests/test_highlight.py, tests/test_markers.py.
   - Desired end state: grid and annotate have no _apply_markers; their postprocessors call apply_html(text); every file under tests/ and src/markwright/ has from __future__ import annotations; output is byte-identical (the existing suites prove it).

2. Tooling:
   - Skills: python:python
   - MCPs: none
   - External: none

3. Do the work:
   - In src/markwright/grid.py: move _apply_markers' body into apply_html (keep apply_html's signature and docstring, merging the skip semantics sentence from _apply_markers' docstring); delete _apply_markers; GridPostprocessor.run returns apply_html(text).
   - In src/markwright/annotate.py: the same fold; AnnotatePostprocessor.run returns apply_html(text).
   - Add from __future__ import annotations after the ABOUTME header in the five test files; let `ruff format` and `ruff check --fix` settle import order.

4. Verify:
   - `grep -L "from __future__ import annotations" tests/test_*.py tests/integration/*.py src/markwright/*.py` prints nothing.
   - `grep -n _apply_markers src/markwright/*.py` prints nothing.
   - `just check` green with every existing grid and annotate test passing unchanged.

5. Document:
   - none (the CLAUDE.md Architecture text does not name _apply_markers).
```

---

## Implementation Guidelines

- TDD: RED (failing test) then GREEN (minimal code) then REFACTOR, per the `python:python` skill; Task steps follow Scope / Tooling / Do / Verify / Document. `just check` must pass before a step is considered complete.
- Every source file keeps its 2-line `# ABOUTME:` header and `from __future__ import annotations`, RST docstrings, descriptive names (never single letters), and frozen pydantic models, per CLAUDE.md.
- Parity is the law: `run_post(stub_render(run_pre(doc)))` equals the in-process render. Steps 2 and 3 move `mw pre` toward the in-process reference; Step 4 fixes in-process output that was already broken. No prose output outside the named cases may change; the existing suites and the round-trip property are the guard.
- Test the project's own logic only: the scanner and the mappers directly (the exempted files), each stage's `expand_source` and `apply_html` directly, the in-process `render_*` helpers, and the round-trip property. Do not test Python-Markdown, pymdownx, or Pygments.
- Regex is for single-line token grammars only; the HTML-tag grammar in Step 3 mirrors Python-Markdown's own inline grammar and is the only new one.
- No dependency changes (`deps: frozen`). No version bump; the CHANGELOG entries sit under `## [Unreleased]`.
- Prose edits (CHANGELOG, CLAUDE.md, docs) follow the writing rules: one sentence per line, straight quotes, no em-dashes, no banned vocabulary.
- Never commit to `main`; the work is on `material-parity-0.4.0`, one PR, merged by Mason.

## Success Metrics

- `just check` green: ruff, ruff format, mypy strict, pytest, coverage at 100% line and branch (test or delete every uncovered line).
- `just test-integration` and `just docs-build` green.
- Chained `[annotate]` markers never corrupt a tag; the first marker is skipped and reported.
- `mw pre` treats a tab-indented in-list fence as code, leaves top-level indented code alone, and leaves HTML tags, comments, and autolinks alone, for the fence, highlight, icons, and all ten directive stages.
- In-process icons and highlight keep a shortcode or marker literal inside `alt`, `title`, `href`, and inline-HTML attributes, and still render inside link text and emphasis.
- No test imports a private module other than `_fences` and `_markers` (with `_html.tokenize` for inputs), and CLAUDE.md records the exemption.
- grid and annotate have no `_apply_markers`; every file in `src/markwright/` and `tests/` carries the future import; the CLAUDE.md priority table and `_fences.py`'s ABOUTME match the code.
