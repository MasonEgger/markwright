# polish-gaps: Todo

Mirrors `plan.md`.
One top-level checkbox per step; sub-items track the step's own sub-steps.
The `/goal` loop checks items as it goes.

## Section 1: Diagnostics

- [x] Step 1: Diagnostic Records and the Report Call
  - [x] RED: tests/test_diagnostics.py (frozen record, reason vocabulary, RenderWarning, report)
  - [x] Docs: docs/config.md Diagnostics section
  - [x] GREEN: _diagnostics.py Diagnostic, RenderWarning, report; __init__.py re-exports
  - [x] CLAUDE.md __init__ list; just check, just docs-build
- [x] Step 2: Post Stages Return Diagnostics
  - [x] RED: fence, grid, tabs, annotate, markers tests take a Diagnostic list
  - [x] GREEN: every apply_html, report_problem_markers, run_post; cli prints message
  - [x] Docs: docs/cli.md reason vocabulary; CLAUDE.md signature
  - [x] just check, just docs-build
- [x] Step 3: In-Process Reporting and `mw render --warn`
  - [x] RED: in-process list and warnings, reset per document, byte-identical HTML, mw render flags
  - [x] GREEN: postprocessors call report; reset; mw render --warn/--no-warn
  - [x] Docs: docs/cli.md, docs/config.md; spec.md CLI entry cleared
  - [x] just check, just docs-build
- [x] Step 4: Source Lines Through a Line Map
  - [x] RED: rebase_marker_lines, true lines in both paths, front matter counted
  - [x] GREEN: _markers.rebase_marker_lines, run_pre, StageSpec.line_markers, cli front matter, source-lines preprocessor
  - [x] spec.md Host API, Containers, registry sentences cleared; CLAUDE.md
  - [x] just check
- [x] Step 5: Report a Disallowed Environment
  - [x] RED: marker field and line, Diagnostic in both paths, no HTML change
  - [x] GREEN: fence.py _expand_lines, FenceMarker, _apply_marker
  - [x] Docs: docs/extensions/fence.md; spec.md Fence sentence cleared
  - [x] just check, just docs-build

## Section 2: Strict Docs Builds

- [ ] Step 6: The MkDocs Strict-Mode Hook (task)
  - [ ] docs/hooks/markwright.py and the mkdocs.yml hooks line
  - [ ] docs/integrations/mkdocs.md
  - [ ] Verify: just docs-build, a scratch stray [/tab] fails --strict, just check
  - [ ] spec.md Docs Site cleared; CLAUDE.md

## Section 3: Regions Every Stage Skips or Reads

- [ ] Step 7: Multi-Line HTML Comments Are Skipped
  - [ ] RED: _fences region tests, containers, directive stages, round trip, Hugo
  - [ ] GREEN: comment regions in _scan_blocks and _code_regions
  - [ ] Docs: docs/pipeline.md; spec.md and CLAUDE.md
  - [ ] just check, just docs-build
- [ ] Step 8: `<pre>`, `<script>`, `<style>`, and `<textarea>` Blocks Are Verbatim
  - [ ] RED: _fences, icons, youtube, tabs, highlight, round trip
  - [ ] GREEN: verbatim blocks in _fences; drop skip_blocks_opened_by
  - [ ] spec.md Icons Decision deleted, rules cleared; CLAUDE.md
  - [ ] just check
- [ ] Step 9: Highlight Skips Tags, and Directives Expand Inside Raw HTML In-Process
  - [ ] RED: highlight tag skipping; nine directive modules inside a div in-process; round trip
  - [ ] GREEN: highlight uses the tag grammar; preprocessors at 21
  - [ ] CLAUDE.md priority table; spec.md clauses cleared
  - [ ] just check
- [ ] Step 10: Highlight and Icons Inside Raw HTML In-Process
  - [ ] RED: raw_html_blocks extents; highlight and icons in a div in-process; round trip
  - [ ] GREEN: _fences.raw_html_blocks; preprocessors at 21 in highlight and icons
  - [ ] Docs: highlight and icons pages; spec.md and CLAUDE.md
  - [ ] just check, just docs-build

## Section 4: Blocks and Code Lines

- [ ] Step 11: An Embed Is Its Own Block
  - [ ] RED: blank lines around an embed, byte-identical when present, none inside raw HTML, in-process, Hugo
  - [ ] GREEN: map_directive_lines own_block for the six embeds
  - [ ] Docs; spec.md Embeds cleared; CHANGELOG upgrading note
  - [ ] just check, just docs-build
- [ ] Step 12: A Marked Fence Is Its Own Block
  - [ ] RED: blank line before the marker, tight list in-process, round trip, Hugo
  - [ ] GREEN: fence.py _expand_lines blank-line rule
  - [ ] spec.md Fence tight-list cleared; CHANGELOG note
  - [ ] just check
- [ ] Step 13: Highlighter Attributes Beside a Prefix Flag
  - [ ] RED: hl_lines, title, Hugo braces, commas inside values, in-process, Hugo
  - [ ] GREEN: split at the first space or brace
  - [ ] Docs: docs/extensions/fence.md; spec.md cleared
  - [ ] just check, just docs-build
- [ ] Step 14: Line Prefixes Around Spans That Wrap a Whole Line
  - [ ] RED: Pygments hl_lines and line_spans, Chroma noClasses fixture, Hugo hugo_config argument
  - [ ] GREEN: a line ends at its newline plus the closing tags after it
  - [ ] spec.md cleared
  - [ ] just check
- [ ] Step 15: Line-Number Tables and Inline Line Numbers
  - [ ] RED: Pygments table and inline layouts, Chroma table and inline fixtures, Hugo lineNos
  - [ ] GREEN: _apply_marker skips the gutter cell
  - [ ] Docs: docs/extensions/fence.md; spec.md cleared
  - [ ] just check, just docs-build

## Section 5: Records

- [ ] Step 16: Close the Cycle's Records (task)
  - [ ] spec.md: Upcoming line deleted, Open Work none, no Known gap or Planned sentence
  - [ ] CHANGELOG.md Unreleased complete
  - [ ] CLAUDE.md matches the code
  - [ ] Verify: grep prints nothing, just check, just docs-build
