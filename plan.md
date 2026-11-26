# Plan: polish-gaps

Close every remaining `Known gap` in `spec.md` and the polish findings, so the spec holds no `Known gap` sentence when the cycle ends.
The source of each requirement is a `Planned (polish-gaps):` sentence in `spec.md`; every step names the sentences it clears.

## Current Status

- Branch: `polish-gaps`, stacked on PR #39 (`spec-drop-fringe-gaps`); the spec commit is `014dbe4`.
- Not started. 15 steps in 5 sections.
- Gate: `just check` (ruff, ruff format, mypy strict, pytest with the Hugo integration tests, coverage reported) after every step; `just docs-build` is also the gate for every step that edits `docs/` or `mkdocs.yml`.
- Fences honored: no step edits `pyproject.toml` or `uv.lock` (outside `paths:`, and `deps: frozen`); no step adds a runtime dependency (`difflib` is stdlib); no step implements a Roadmap Deferred item (a MkDocs plugin in the package, the one-scan-per-`run_pre` refactor, fence marker binding, `[button]` argument checks, parser hygiene, hardening, release pipeline hygiene).
- New invariant to keep in every step: a diagnostic never changes the rendered HTML or an exit code; it only reports.

## Section 1: Diagnostics

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: none

**Batch:** diagnostics-a

### Step 1: Diagnostic Records and the Report Call

**NOTE**: `_diagnostics.py` is a leaf module today (`ConfigWarning`, `OptionError`) and must stay one: it imports nothing from markwright. `__init__.py` re-exports the public API with `__all__` and nothing else. RST docstrings, frozen pydantic models, descriptive names.

```text
1. RED: Write tests first in tests/test_diagnostics.py (new; public API only, so import from `markwright`):
   - Test that `Diagnostic(extension="tabs", line=4, directive="[/tab]", reason="stray-closer", message="...")` is frozen (assigning a field raises `pydantic.ValidationError`).
   - Test that `line` and `directive` accept `None`.
   - Test that `reason` rejects a value outside the closed vocabulary (pydantic `Literal`): `unclosed`, `stray-closer`, `card-outside-grid`, `disallowed-environment`, plus one reason per other problem a post stage reports today. Read every `skip_reasons.append(...)` and `message_for` call in `src/markwright/` (fence, grid, tabs, annotate, `_markers.report_problem_markers`) and name a reason for each, for example `malformed-marker` (an `InvalidMarkerError` from `decode_marker`), `no-target` (a marker with no block or list after it), `unmatched-marker` (an open or close marker with no partner). Write the list into the test as the expected `typing.get_args` of the `reason` annotation.
   - Test that `RenderWarning` is a `UserWarning` subclass and that `RenderWarning(diagnostic).diagnostic is diagnostic` and `str(RenderWarning(diagnostic)) == diagnostic.message`.
   - Test that `report(md, diagnostic)` appends to `md.markwright_diagnostics` and emits exactly one `RenderWarning` carrying the same object (`pytest.warns`). Use a real `markdown.Markdown()` as `md`.
   - Test that `report` creates `md.markwright_diagnostics` when the attribute is missing.
2. Document: add a "Diagnostics" section to docs/config.md (host API part) describing `Diagnostic`, `RenderWarning`, the reason vocabulary, and `md.markwright_diagnostics`; one sentence per line, Title Case headings.
3. GREEN: in src/markwright/_diagnostics.py add:
   - `DiagnosticReason = Literal[...]` with the vocabulary from step 1.
   - `class Diagnostic(BaseModel)` with `model_config = ConfigDict(frozen=True)`, fields `extension: str`, `line: int | None`, `directive: str | None`, `reason: DiagnosticReason`, `message: str`, `:ivar` docstring.
   - `class RenderWarning(UserWarning)` whose `__init__(self, diagnostic: Diagnostic)` stores `self.diagnostic` and passes `diagnostic.message` to `super().__init__`.
   - `def report(md: markdown.Markdown, diagnostic: Diagnostic) -> None`: append to `md.markwright_diagnostics` (create the list when missing; type it through a `getattr`/`setattr` pair, no `assert`), then `warnings.warn(RenderWarning(diagnostic), stacklevel=2)`. The list is the record and the warning is the side effect of the same call.
   - Update the ABOUTME header to name the new contents.
4. GREEN: re-export `Diagnostic` and `RenderWarning` from src/markwright/__init__.py and add them to `__all__` (`report` stays private to the package).
5. REFACTOR: keep `_diagnostics.py` free of markwright imports; `markdown` is the only new import.
6. Update CLAUDE.md, Code Conventions: the `__init__.py` re-export list gains `Diagnostic` and `RenderWarning`.
7. Run `just check` and `just docs-build`.
```

### Step 2: Post Stages Return Diagnostics

**NOTE**: Every `apply_html(rendered_html, skip_reasons, options)` takes `skip_reasons: list[str] | None`, and `registry.run_post` threads it; `_markers.report_problem_markers` takes the same list; `cli._run_post` prints each string. The printed text of `mw post --warn` must stay what it is today, line for line, so the existing `tests/test_cli.py` stderr assertions keep passing unchanged.

```text
1. RED: update tests first:
   - tests/test_fence.py, tests/test_grid.py, tests/test_tabs.py, tests/test_annotate.py: every test that passes a `skip_reasons` list now passes a `diagnostics: list[Diagnostic]` and asserts on `[diagnostic.message for diagnostic in diagnostics]` with the same strings, plus the `extension` and `reason` of each.
   - Test, for a grid and a tab problem marker, that the `Diagnostic` carries `line` and `directive` from the payload.
   - Test that a malformed marker yields `reason="malformed-marker"` and `line=None`.
   - tests/test_markers.py: `report_problem_markers` collects `Diagnostic` objects.
2. GREEN: rename the parameter to `diagnostics: list[Diagnostic] | None` in every `apply_html` in src/markwright/ (fence, grid, tabs, annotate, highlight, codepen, twitter, instagram), in `_markers.report_problem_markers`, and in `registry.run_post`; build a `Diagnostic` at every append site with the reason named in Step 1; the `message` is exactly the string appended today.
   - `Diagnostic` is used at runtime in these modules; import it normally.
3. GREEN: src/markwright/cli.py `_run_post` prints `diagnostic.message` for each entry.
4. REFACTOR: where grid and tabs compose the same message shape, keep one composer per module; no new one-caller helpers.
5. Update docs/cli.md: list the reason vocabulary under `--warn` (closed list, one line each).
6. Update CLAUDE.md: the stage-function signature line (`apply_html(rendered_html, diagnostics, options)`).
7. Run `just check` and `just docs-build`.
```

### Step 3: In-Process Reporting and `mw render --warn`

**NOTE**: The in-process postprocessors call `apply_html(text)` with no list today, so in-process problems vanish. Clears spec.md: the CLI entry's Planned sentences on `report`, `md.markwright_diagnostics`, `mw render --warn`, and the de-duplication note, and its Today sentence.

```text
1. RED: write tests first:
   - tests/test_grid.py and tests/test_tabs.py: an in-process render (`render_*` helper) of a document with an unclosed `[card]` and a stray `[/tab]` fills `md.markwright_diagnostics` with the same `Diagnostic` values `apply_html` returns for the pipeline, and emits one `RenderWarning` per entry (`pytest.warns`).
   - Test that a second `md.convert()` on the same instance starts with an empty list (reset per document), and so does `md.reset()`.
   - Test that a document with no problem leaves the list empty and emits no warning.
   - Test that the rendered HTML is byte-identical with warnings filtered to `"ignore"` and to `"always"` (the invariant).
   - tests/test_cli.py: `mw render --warn` prints each diagnostic as one `mw: warning: <message>` stderr line; `mw render` with no flag and `warn` unset prints none; `--no-warn` beats `warn = true`; the last of `--warn`/`--no-warn` wins; exit code 0 in every case; with `PYTHONWARNINGS=error` (set through `monkeypatch.setenv` plus the CLI's own filter) `mw render --warn` still exits 0.
2. GREEN: in each extension with a postprocessor that reports (fence, grid, tabs, annotate), have `run` collect into a local list, then call `_diagnostics.report(self.md, diagnostic)` per entry.
   - Each such `Extension.extendMarkdown` calls `md.registerExtension(self)` and defines `reset(self)` that sets `self.md.markwright_diagnostics = []`, and sets the attribute at `extendMarkdown` time, so the list is fresh per document. Python-Markdown calls `reset()` on registered extensions at the start of every `convert()`; confirm that by reading `markdown.core.Markdown.reset` before relying on it.
3. GREEN: src/markwright/cli.py: give `render` the `--warn`/`--no-warn` pair (reuse the existing flag builder at line 35); resolve with the config `warn` default the way `_run_post` does; inside `warnings.catch_warnings()` set `simplefilter("always", RenderWarning)` when on and `"ignore"` when off, so `PYTHONWARNINGS=error` never escalates them; route `RenderWarning` through `_show_warning` as `mw: warning: <message>`.
4. REFACTOR: one place in the CLI decides "warn on" for both `post` and `render`.
5. Docs: docs/cli.md (`render` flags), docs/config.md Diagnostics section (in-process list, warning, `always` filter for multi-page builds, a host that runs with warnings as errors gets the exception), docs/integrations/mkdocs.md one sentence pointing at Step 6's hook (write the sentence in Step 6 if the page structure makes it awkward here).
6. spec.md: clear the CLI entry's Planned sentences (drop the prefix, keep the text as current behavior), delete their Today sentence, and rewrite "The pair exists on `mw post` only" to name `render` too.
7. Run `just check` and `just docs-build`.
```

### Step 4: Source Lines Through a Line Map

**Batch:** diagnostics-b

**NOTE**: Grid and tabs write `line` as the line in their stage's input (`grid.py:198`, `tabs.py:190`), which is wrong after mermaid (45) or fence (40) added lines above, and `mw pre` hands stages the text after the front matter block. `Markdown.convert` splits the source into `self.lines` with no other change before the first preprocessor runs. Clears spec.md: the Host API entry's `line` and `run_pre` line-map sentences, the Containers entry's Planned sentence and its Today sentence, and the registry Component boundaries sentence.

```text
1. RED: write tests first:
   - tests/test_markers.py: `rebase_marker_lines(source_lines, stage_input_lines, stage_output, names)` rewrites the `line` field of each marker named in `names` that is new in `stage_output` (not present in `stage_input_lines`) from a stage-input line to the matching source line; a marker already present is untouched; a stage-input line with no source counterpart maps to the nearest source line above it; a malformed payload is left as it is (fail-soft).
   - tests/test_roundtrip.py or tests/test_registry.py (whichever already tests `run_pre`): a document with a labeled fence and a `mermaid` fence above a stray `[/tab]` and an unclosed `[card]` reports the true 1-based source line for each through `run_post(stub_render(run_pre(doc)))`, and the in-process render's `md.markwright_diagnostics` reports the same lines.
   - tests/test_cli.py: `mw pre | mw post --warn` over a file with a YAML front matter block reports the line counted from the top of the file.
2. GREEN: src/markwright/_markers.py: add `rebase_marker_lines`. Map lines with `difflib.SequenceMatcher(None, source_lines, stage_input_lines, autojunk=False)`: `equal` opcodes map line for line, an equal-length `replace` maps line for line, anything else maps to the nearest mapped line above. Decode with the existing fail-soft reader and re-encode with `encode_marker`.
3. GREEN: src/markwright/registry.py `run_pre`: keep the source lines and, after each stage, call `rebase_marker_lines` with the problem-marker names (`grid.PROBLEM_MARKER_NAME`, `tabs.PROBLEM_MARKER_NAME`, and fence's marker name for Step 5). Take the names from a field on `StageSpec` (`line_markers: tuple[str, ...] = ()`) so registry stays generic.
4. GREEN: src/markwright/cli.py `_run_pre`: pass the front matter line count so the line map counts the front matter block (for example, run the stages over the body and add the block's line count when rebasing, or rebase against the whole file's lines); pick the simpler and test it.
5. GREEN: in-process: a `SourceLinesPreprocessor` registered at the highest priority any markwright extension uses plus one (above mermaid's 45, so 46) stores `md.markwright_source_lines = list(lines)` and returns the lines unchanged; register it from grid and tabs (and fence in Step 5) under one name so loading several extensions registers it once. The grid and tabs preprocessors rebase their output against it before returning.
6. REFACTOR: one mapping function, used by `run_pre` and the in-process preprocessors.
7. spec.md: clear the Host API `line` and line-map Planned sentences, the Containers Planned sentence (delete its Today sentence and rewrite the payload sentence to say `line` is the source line), and the registry Component boundaries Planned sentence. CLAUDE.md: registry and `_markers.py` descriptions.
8. Run `just check`.
```

### Step 5: Report a Disallowed Environment

**NOTE**: `_expand_lines` stops reading directives at an unlisted `[environment NAME]` and leaves it in the code; nothing reports it. `FenceMarker` ignores unknown fields, so version 1 holds. Clears spec.md: the Fence entry's disallowed-environment Planned sentence and its Today sentence.

```text
1. RED: write tests first in tests/test_fence.py:
   - `expand_source` with `allowed_environments=["local"]` over a fence holding `[environment prod]` emits an `mw-fence` marker with `disallowed_environment: "prod"` and `line` (the directive's 1-based line); a fence with a label and a disallowed environment carries both; a fence with only the disallowed line gets a marker with only that field plus `version` and `line`.
   - The `[environment prod]` line stays in the code, as today.
   - `apply_html` over that marker returns a `Diagnostic(extension="fence", reason="disallowed-environment", directive="[environment prod]", line=N)` and changes no HTML beyond removing the comment (byte-compare against the same render with the field absent).
   - In-process render reports the same `Diagnostic` in `md.markwright_diagnostics`.
   - With `allowed_environments` omitted nothing is reported.
   - Round trip: tests/test_roundtrip.py pipeline and in-process agree on HTML and on the diagnostics.
2. GREEN: src/markwright/fence.py: in `_expand_lines`, when the environment is not allowed, record `disallowed_environment` and `line` in the metadata, and emit the marker even when nothing else is set; add `disallowed_environment: str | None = None` and `line: int | None = None` to `FenceMarker`; `_apply_marker` appends the `Diagnostic`; register fence's marker name in `StageSpec.line_markers` and the source-lines preprocessor from Step 4.
3. REFACTOR: `environment_names` keeps its own rules (it reports every disallowed name, the marker only the first, matching where fence stops reading).
4. Docs: docs/extensions/fence.md (the report and the payload field in the marker contract table).
5. spec.md: clear the Fence Planned sentence on reporting and delete its Today sentence; add `disallowed_environment` and `line` to the `mw-fence` marker field list.
6. Run `just check` and `just docs-build`.
```

## Section 2: Strict Docs Builds

**Tools:**
- Skills: python:python, content-design:review-content
- MCPs: none
- Linters: none

**Batch:** single

### Step 6: The MkDocs Strict-Mode Hook (task)

**NOTE**: MkDocs 1.6 replaces `warnings.showwarning` to log a Python warning at INFO with a traceback, and `--strict` counts only WARNING records on the `mkdocs` loggers. The hook is a host example in the docs site, never package code. Clears spec.md: the Docs Site Planned sentence and its Today sentence.

```text
1. Scope:
   - Artifacts: docs/hooks/markwright.py (new), mkdocs.yml, docs/integrations/mkdocs.md, docs/config.md.
   - End state: `mkdocs build --strict` fails on a markwright diagnostic in any page and passes on the docs as they are.
2. Tooling:
   - Skills: python:python (the hook is Python), content-design:review-content (the docs page).
   - MCPs: none.
   - External: `uv run mkdocs build --strict`.
3. Do the work:
   - Write docs/hooks/markwright.py with an ABOUTME header and `from __future__ import annotations`: an `on_startup` (or `on_config`) hook that calls `warnings.simplefilter("always", RenderWarning)` and wraps `warnings.showwarning` so a `RenderWarning` is logged through `logging.getLogger("mkdocs.plugins.markwright").warning(str(message))` and every other warning goes to the previous handler. Type hints on every function; import `RenderWarning` from `markwright`.
   - Add `hooks: [docs/hooks/markwright.py]` to mkdocs.yml.
   - Document the hook on docs/integrations/mkdocs.md as the host example (what it does, the file, the `hooks:` line), and say that a host reading `md.markwright_diagnostics` needs no hook.
   - Check no docs page renders a live problem: grep the built site's build log; if one does, move that example into a code block.
4. Verify:
   - `just docs-build` exits 0.
   - In a scratch copy (never committed), add a page with a stray `[/tab]` and confirm `uv run mkdocs build --strict` exits non-zero with the `mw` message in its log; delete the scratch copy.
   - `just check` exits 0.
5. Document:
   - spec.md: clear the Docs Site Planned sentence and delete its Today sentence; name `docs/hooks/` in the worked-host-example sentence.
   - CLAUDE.md: name `docs/hooks/markwright.py` beside the other worked host example files.
```

## Section 3: Regions Every Stage Skips or Reads

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: none

**Batch:** regions-a

### Step 7: Multi-Line HTML Comments Are Skipped

**NOTE**: `_fences._code_regions` returns the fenced blocks and the code lines that `map_prose`, `map_lines`, `map_directive_lines`, and `_containers.scan_containers` skip, and `find_fenced_blocks` feeds fence and mermaid. A comment line that closes on its own line must stay readable: markwright's marker comments are single-line and the container scanner reads them. Clears spec.md: the comment-region Planned sentences under Rules Every Feature Follows and their Today sentence; deletes nothing else.

```text
1. RED: write tests first:
   - tests/test_fences_map_prose.py (or a new tests/test_fences_regions.py): a line starting with `<!--` (0 to 3 columns) and holding no `-->` opens a region through the first later line holding `-->`; `map_prose`, `map_lines`, and `map_directive_lines` leave every line of it untouched; a fence opener inside it is not a `FencedBlock`; a one-line comment is not a region; `<!--` inside fenced code opens nothing; an unclosed comment runs to the end of the document (as CommonMark reads it); a comment indented four columns at the top level after a blank line is indented code, not a region.
   - tests/test_containers.py: `[tab A]` ... `[/tab]` inside a multi-line comment is not paired and not reported; the scanner still reads one-line `mw-tab` marker comments.
   - tests/test_grid.py, tests/test_tabs.py, tests/test_annotate.py, tests/test_fence.py, tests/test_youtube.py: a commented-out directive or fence directive comes out of `expand_source` unchanged and the in-process render keeps the comment whole (the commented text is not published).
   - tests/test_roundtrip.py: add a commented-out tab set and fence directive to the round-trip cases; add the comment region to the hypothesis grammar if it has a block-start strategy.
   - tests/integration/test_hugo_pipeline.py: a commented-out `[tab A]`/`[/tab]` and `[youtube ID]` stay inside the comment through Hugo.
2. GREEN: src/markwright/_fences.py: find comment regions in the same forward pass that classifies lines (`_scan_blocks`), only where a line is outside code, and add their lines to the skipped set `_code_regions` returns; exclude them from fence detection. Keep the per-document cache.
3. REFACTOR: name the region grammar as one compiled pattern with an intent comment.
4. Docs: one sentence on each directive page that has a "Syntax" section is too many; add one sentence to docs/pipeline.md (or the page that lists what stages skip) instead.
5. spec.md: clear the comment-region Planned sentences and delete their Today sentence. CLAUDE.md: the `_fences.py` description gains the comment region.
6. Run `just check` and `just docs-build`.
```

### Step 8: `<pre>`, `<script>`, `<style>`, and `<textarea>` Blocks Are Verbatim

**NOTE**: Icons passes `skip_blocks_opened_by=mermaid.PRE_OPEN` to `map_prose`, which skips only a block opening with exactly the mermaid stage's tag (`_fences._read_emitted_blocks`). CommonMark's first HTML block kind starts a line with `<pre`, `<script`, `<style`, or `<textarea` (case-insensitive, followed by space, `>`, or line end) and ends at the line holding the matching close tag; Python-Markdown passes the same block through raw. Clears spec.md: the verbatim-block Planned sentence under Rules Every Feature Follows, the Icons entry Planned sentence, and the 2026-11-20 icons Decision.

```text
1. RED: write tests first:
   - tests/test_fences_map_prose.py: every pre stage helper skips the lines of a `<pre>`, `<script>`, `<style>`, or `<textarea>` block through its close tag; the opener is case-insensitive; text after the close tag on its line is prose; an unclosed block runs to the end of the document.
   - tests/test_icons.py: a shortcode in an author-written `<pre class="mermaid">`, a plain `<pre>`, and a `<script>` block stays literal through `expand_source` and in-process; a mermaid diagram the stage emitted keeps its shortcode text (existing test keeps passing).
   - tests/test_youtube.py, tests/test_tabs.py: a directive line inside a `<pre>` block stays literal in both paths.
   - tests/test_highlight.py: a `<^>` pair inside a `<script>` block is left alone by `expand_source`.
   - tests/test_roundtrip.py: a `<pre>` block holding a directive and a shortcode matches in both paths.
2. GREEN: src/markwright/_fences.py: classify verbatim blocks in `_scan_blocks` and add their lines to the skipped set; remove `skip_blocks_opened_by` and `_read_emitted_blocks` once icons no longer needs them; update src/markwright/icons.py to drop the argument.
3. GREEN: in-process: the directive preprocessors already see the block as raw lines; confirm by test that none expands inside it (it reads through `_fences`).
4. REFACTOR: one pattern for the four tag names.
5. spec.md: clear the verbatim-block Planned sentence, the Icons Planned sentence, and delete the Decision (2026-11-20) and the icons sentence that describes the mermaid-tag rule; rewrite the Icons "Shortcodes resolve in prose only" sentence to name verbatim blocks. Delete the part of the raw-HTML Today sentence that describes the icons mermaid rule. CLAUDE.md: Icons pattern and `map_prose` description.
6. Run `just check`.
```

### Step 9: Highlight Skips Tags, and Directives Expand Inside Raw HTML In-Process

**Batch:** regions-b

**NOTE**: The icons pre stage skips HTML tags, comments, and autolinks through its single-line grammar; the highlight pre stage does not, so a pair inside an attribute breaks the tag. In-process the embed, button, lightbox, and annotate preprocessors run at 20, tied with Python-Markdown's `html_block`, and a directive inside a raw `<div>` stays literal there while `mw pre` expands it. Grid and tabs already run at 21. Clears spec.md: the raw-HTML Planned sentence's tag-skipping and preprocessor-priority clauses (Step 10 clears the rest), and the Highlight entry Planned sentence's tag clause.

```text
1. RED: write tests first:
   - tests/test_highlight.py: `expand_source` leaves `<a title="<^>x<^>">`, `<!-- <^>x<^> -->`, and `<https://e.com/<^>x<^>>` untouched and still wraps `<^>y<^>` in the text beside them on the same line.
   - tests/test_youtube.py, tests/test_button.py, tests/test_lightbox.py, tests/test_annotate.py, tests/test_codepen.py, tests/test_twitter.py, tests/test_instagram.py, tests/test_slideshow.py, tests/test_image_compare.py: a directive line inside `<div class="note">` ... `</div>` (no blank lines) expands in-process, matching `expand_source`.
   - tests/test_roundtrip.py: a `<div>` holding a youtube line and a button line matches in both paths.
2. GREEN: src/markwright/highlight.py `expand_source`: skip tags, comments, and autolinks with the same single-line grammar icons uses (import it from where it lives, or move it into `_fences` if icons owns it privately; the second caller justifies the move).
3. GREEN: register the embed, button, lightbox, and annotate preprocessors at 21 (beside grid and tabs, after superfences' fenced-code preprocessor at 25, ahead of `html_block` at 20). Check the priority table: 21 must stay below fence (40) and mermaid (45, 26) and above `html_block`; update `registry.py` pre priorities only if the CLI order changes (it should not).
4. REFACTOR: none beyond the move.
5. CLAUDE.md: the Processor Priority Reference rows for the embeds, button, lightbox, and annotate.
6. spec.md: clear the tag-skipping and priority clauses of the raw-HTML Planned sentence and the Highlight Planned sentence's tag clause, and delete the matching parts of the Today sentence.
7. Run `just check`.
```

### Step 10: Highlight and Icons Inside Raw HTML In-Process

**NOTE**: The inline processors never see a raw HTML block, because `html_block` (20) stashes it. Python-Markdown's extent: a line starting with a block-level opening tag through the line holding its matching close tag, blank lines included (read `markdown.preprocessors.HtmlBlockPreprocessor` and `markdown.htmlparser` before coding). Clears spec.md: the rest of the raw-HTML Planned sentences and their Today sentence.

```text
1. RED: write tests first:
   - tests/test_fences_regions.py (or the file Step 7 created): `raw_html_blocks(lines)` returns the Python-Markdown extent of each raw block (a `<div>` with and without blank lines inside, nested `<div>`s, a block-level tag Python-Markdown knows versus an inline tag such as `<span>` that does not open a block), and excludes verbatim blocks, comments, and code.
   - tests/test_highlight.py: in-process `<div>\nSee <^>this<^>.\n</div>` renders `See <mark>this</mark>.` inside the div, as `mw pre` does; a pair in an attribute in the block stays as written.
   - tests/test_icons.py: in-process a shortcode in the text of a raw `<div>` renders the icon, as `mw pre` does; a shortcode inside an attribute stays literal.
   - tests/test_roundtrip.py: a `<div>` with a pair and a shortcode, without blank lines, matches in both paths.
2. GREEN: src/markwright/_fences.py: add `raw_html_blocks` (Python-Markdown's extent) as the in-process reader of raw blocks.
3. GREEN: src/markwright/highlight.py and src/markwright/icons.py: an in-process preprocessor at 21 applies the pre-stage transform (`expand_source`, with the icons options read in `extendMarkdown`) to the lines of each raw block only, so the inline processors keep handling ordinary prose.
4. REFACTOR: share the "apply a line transform to raw-block lines" loop between the two only if both callers use the same shape; otherwise keep each inline in its module.
5. Docs: docs/extensions/highlight.md and docs/extensions/icons.md: one sentence each that the syntax works inside a raw HTML block.
6. spec.md: clear the remaining raw-HTML Planned sentences and delete their Today sentence; clear the Highlight Planned sentence. CLAUDE.md: the `_fences.py` description (`raw_html_blocks`), the Highlight and Icons patterns, and a Processor Priority row for the 21 preprocessors.
7. Run `just check` and `just docs-build`.
```

## Section 4: Blocks and Code Lines

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: none

**Batch:** blocks-a

### Step 11: An Embed Is Its Own Block

**NOTE**: `_fences.map_directive_lines` replaces a directive line with its expansion at the line's indentation. Only the six embeds (youtube, codepen, twitter, instagram, slideshow, image_compare) are blocks; button and lightbox are inline and keep today's output. `eager` output for an embed line that already has a blank line on each side must stay byte-identical. Inside a raw HTML block no blank line is added (CommonMark's extent for `mw pre`: from the opening tag line to the first blank line; in-process the Step 10 extent). Clears spec.md: the Embeds Planned sentence and its Today sentence.

```text
1. RED: write tests first:
   - tests/test_youtube.py (and one representative test each in the other five embed test files): `expand_source("Intro\n[youtube abc]\nOutro\n")` puts a blank line before and after the expansion; an embed between blank lines is byte-identical to today; an indented embed under a list item gets blank lines that keep it in the item (the blank line carries no indentation, or the indentation, whichever renders inside the item in both paths; test both renderers); an embed inside `<div>` ... `</div>` gets no blank lines.
   - In-process: the same documents render the embed as its own block (no `<p>` around the iframe, the paragraph split around it); a tight list item that holds an embed renders loose.
   - tests/test_button.py, tests/test_lightbox.py: unchanged output beside text (inline).
   - tests/test_roundtrip.py: the three shapes match in both paths.
   - tests/integration/test_hugo_pipeline.py: `Intro\n[youtube abc]\nOutro *line*\n` renders `Outro <em>line</em>` as Markdown through Hugo.
2. GREEN: give `map_directive_lines` a keyword (for example `own_block: bool = False`) that adds the blank lines where the neighbor is not blank, skipping lines inside a raw HTML block; pass it from the six embed modules, in-process and in `expand_source`, so the stash placeholder gets the same blank lines.
3. REFACTOR: the raw-block extent lookup comes from `_fences`, never re-derived in an embed module.
4. Docs: one sentence on each embed page, or one shared sentence on the page that introduces directives, that an embed is always its own block.
5. spec.md: clear the Embeds Planned sentence and delete its Today sentence. CHANGELOG.md Unreleased gets an "Upgrading" note: an embed beside text now splits the paragraph, and a tight list item holding one renders loose.
6. Run `just check` and `just docs-build`.
```

### Step 12: A Marked Fence Is Its Own Block

**NOTE**: `_expand_lines` writes the marker at the fence's indentation and a blank line after it when indented; it writes nothing before it. Under a tight list item's text the marker line becomes a lazy continuation of the paragraph in-process. Quoted fences already get a blank quoted line on both sides. Clears spec.md: the Fence tight-list Planned sentence and its Today sentence.

```text
1. RED: write tests first in tests/test_fence.py:
   - `expand_source("- Run this:\n    ```command\n    ls\n    ```\n- next\n")` writes a blank line before the marker.
   - In-process the same document renders a two-item list, the fence inside the first item, the second item intact (the first item loose).
   - A fence already after a blank line gets no extra blank line (byte-identical to today); a list with an unmarked fence stays tight; a quoted fence is unchanged from today.
   - tests/test_roundtrip.py: the tight-list document matches in both paths.
   - tests/integration/test_hugo_pipeline.py: the same document through Hugo keeps both items and the prefix.
2. GREEN: src/markwright/fence.py `_expand_lines`: when the line before the marker is not blank, append a blank line first (empty, or the bare quote markers for a quoted fence; the quoted case already does this).
3. REFACTOR: one blank-line rule for the plain, indented, and quoted cases.
4. spec.md: clear the Fence tight-list Planned sentence and delete its Today sentence. CHANGELOG.md Unreleased: a fence with a directive or flag under a tight list item now keeps the list, and that item renders loose.
5. Run `just check`.
```

### Step 13: Highlighter Attributes Beside a Prefix Flag

**NOTE**: `_parse_prefix_from_info` splits the whole info string on commas. Clears spec.md: the Fence attribute Planned sentence and its Today sentence.

```text
1. RED: write tests first in tests/test_fence.py:
   - `command hl_lines="1"` gives `prefix_type: command` and the fence line `bash hl_lines="1"`; `command title="x.sh"` gives `bash title="x.sh"`; `command {hl_lines=[1]}` gives `bash {hl_lines=[1]}`; `command,python hl_lines="1 2"` gives `python hl_lines="1 2"`; `line_numbers,python linenums="1"` keeps the attribute; an info string with no flag is unchanged byte for byte; a comma inside an attribute value (`title="a,b"`) is not a flag separator.
   - In-process: `command hl_lines="1"` renders the `$` prefix and the `hll` span; `command title="x.sh"` renders the filename and the prefix.
   - tests/integration/test_hugo_pipeline.py: `command {hl_lines=[1]}` through Hugo keeps the prefix and Chroma highlighting (`class="language-bash"`).
2. GREEN: split the info string at the first space or `{`; read flags and the language from the part before it, comma-separated; append the rest untouched after one space (or directly for `{`, as written).
3. REFACTOR: the split is a single-line grammar; one compiled pattern with an intent comment.
4. Docs: docs/extensions/fence.md: a sentence and an example showing a flag beside `hl_lines` and `title`.
5. spec.md: clear the Fence attribute Planned sentence and delete its Today sentence.
6. Run `just check` and `just docs-build`.
```

### Step 14: Line Prefixes Around Spans That Wrap a Whole Line

**Batch:** blocks-b

**NOTE**: The prefix wrap splits Pygments output at newlines (`_wrap_lines_with_prefix`) and takes Chroma's `<span class="line">` whole when `noClasses = false`. A Pygments `hl_lines` span wraps the line's newline (`<span class="hll">ls\n</span>`), and Chroma with Hugo's default `noClasses = true` writes `<span style="display:flex;"><span>ls\n</span></span>`. Touching fence line-prefix logic: exercise Hugo, not only the Pygments round trip. Clears spec.md: the wrapping-span Planned sentence and its Today sentence.

```text
1. RED: write tests first:
   - tests/test_fence.py: a Pygments block with `hl_lines` (render in-process with `pymdownx.highlight` config, and a captured fixture) wraps each line in its own `<li>` with the `hll` span closed inside the first `<li>`, and adds no empty prefixed line; `line_spans` likewise; a Chroma `noClasses = true` fixture (capture it from a real Hugo build into the test file) gives one `<li>` per line with both spans closed inside it and no trailing empty `<li>`.
   - Existing Pygments flat and Chroma `noClasses = false` tests stay byte-identical.
   - tests/integration/test_hugo_pipeline.py: give `_pipeline_through_hugo` an optional `hugo_config` argument and build one prefixed fence with `noClasses = true`; assert the `<li>` count equals the line count and every `<span` opened in an `<li>` closes in it.
2. GREEN: src/markwright/fence.py: a line ends at its newline plus the closing tags right after it (read from the `_html` tokens), for both the flat and the Chroma paths.
3. REFACTOR: keep one line splitter for both renderers if the token rule covers Chroma's `span.line` case; delete the special case only when its tests still pass.
4. spec.md: clear the wrapping-span Planned sentence and delete its Today sentence.
5. Run `just check`.
```

### Step 15: Line-Number Tables and Inline Line Numbers

**NOTE**: With `linenums` under Pygments the first `<pre>` after the marker is the gutter's (`td.linenos`), and under Hugo `lineNos = true` it is the first `td.lntd`'s. Clears spec.md: the two line-number Planned sentences and their Today sentence.

```text
1. RED: write tests first:
   - tests/test_fence.py: in-process with `pymdownx.highlight` `linenums: true` (table), a labeled `command` fence puts `prefixed command` and the `<li data-prefix>` wrap on the code `<pre>`, leaves the gutter `<pre>` untouched, and keeps the label before the table; with `linenums_style: inline` and `pymdownx-inline` each `<li>` holds its number and its code.
   - A Chroma `lineNos = true` table fixture and a `lineNumbersInTable = false` fixture, captured from real Hugo builds: the same assertions.
   - tests/integration/test_hugo_pipeline.py: one prefixed labeled fence with `lineNos = true` (through the `hugo_config` argument from Step 14): the gutter `<pre>` has no `prefixed` class and no `<li>`, and the code `<pre>` has both.
2. GREEN: src/markwright/fence.py `_apply_marker`: when the bound `<pre>` sits in a gutter cell (`td.linenos`, or the first `td.lntd` of an `lntable`), bind to the next `<pre>` inside the same table instead.
3. REFACTOR: the gutter test is one predicate over the token's ancestors; no ad hoc regex.
4. Docs: docs/extensions/fence.md: line numbers work with labels and prefixes in every layout.
5. spec.md: clear both line-number Planned sentences and delete their Today sentence.
6. Run `just check` and `just docs-build`.
```

## Section 5: Records

**Tools:**
- Skills: content-design:review-content
- MCPs: none
- Linters: none

**Batch:** single

### Step 16: Close the Cycle's Records (task)

```text
1. Scope:
   - Artifacts: spec.md, CLAUDE.md, CHANGELOG.md, README.md (only if it lists limitations), docs/material-mapping.md (only rows the cycle changed).
   - End state: spec.md holds no `Known gap` and no `Planned (polish-gaps)` sentence and no `Today` sentence for this item; the Roadmap Upcoming `polish-gaps` line is deleted; every Feature Status Open Work cell reads `none`; CHANGELOG.md Unreleased lists every behavior change of the cycle; CLAUDE.md matches the code.
2. Tooling:
   - Skills: content-design:review-content.
   - MCPs: none.
   - External: `grep -n 'Known gap\|Planned (polish-gaps)' spec.md` (must print nothing), `just check`, `just docs-build`.
3. Do the work:
   - spec.md: delete the `polish-gaps` Upcoming line; set Open Work to `none` on the 17 rows; sweep for any leftover Planned or Today sentence and fold it into current behavior; reread every entry the cycle touched for a sentence the code now contradicts.
   - CHANGELOG.md Unreleased: Added (in-process diagnostics, `Diagnostic`, `RenderWarning`, `mw render --warn`, the docs hook), Fixed (each gap), Upgrading (the `apply_html` parameter rename, embeds and marked fences as their own blocks, tight items going loose, syntax inside raw HTML blocks working in-process, verbatim blocks skipped).
   - CLAUDE.md: the architecture sections for `_diagnostics.py`, `_fences.py` regions, the priority table, the `__init__` list, and the Plan & Progress note on the archive.
4. Verify:
   - The grep above prints nothing; `just check` and `just docs-build` exit 0.
5. Document:
   - none beyond the above.
```

## Implementation Guidelines

- TDD in every Feature step: the RED tests fail for the reason the step names before any `src/` change.
- Public API only in tests, except `_fences`, `_markers`, and `_containers`, which are tested directly (CLAUDE.md, Testing Approach).
- A step clears exactly the `Planned (polish-gaps):` sentences it ships and deletes their `Today` sentences; no step adds a `Known gap` sentence. If a step finds a case it cannot fix inside its scope, it stops and reports instead of writing a gap.
- Byte-identity: any document that has none of the shapes a step targets renders as before; each step proves it with an existing test or a new byte-compare.
- Both paths: every behavior is asserted in-process and through `run_post(stub_render(run_pre(...)))`; anything touching fence line prefixes or scanning also gets a Hugo integration assertion.
- No one-caller private helper unless it holds a separate concern; descriptive names; RST docstrings; `# ABOUTME:` headers on new files.
- Writing rules for docs and spec text: no em or en dashes, straight quotes, one sentence per line, Title Case headings.

## Success Metrics

- `grep -n 'Known gap' spec.md` prints nothing.
- `just check` and `just docs-build` exit 0, with 100% line and branch coverage reported (or each uncovered line tested or deleted).
- A stray `[/tab]` in a page fails `mkdocs build --strict` through the docs hook.
- The Hugo integration test covers a block quote alert, a tight-list labeled fence, an embed beside text, a flag beside an attribute, `noClasses = true` prefixes, and a `lineNos = true` table.
