# Todo: 0.4.0 Adversarial Review Fixes (Issue #29)

Mirrors plan.md. Each top-level item is a step; sub-items are its numbered sub-steps.

## Section 1: Annotate Chaining

- [x] Step 1: Bound the annotation-list search by the marker's region
  - [x] RED: chained-marker tests in tests/test_annotate.py (TestSkippedMarkers: skipped and reported, both markers removed; TestInProcess: one mw-annotations list, no corrupted tag)
  - [x] GREEN: _locate searches for the list in range(block_close + 1, block_end); docstring updated
  - [x] Verify tests/test_annotate.py passes in full
  - [x] `just check` green

## Section 2: Code Detection in `_fences`

- [x] Step 2: Tab-aware indentation and indented code blocks
  - [ ] RED: tests in tests/test_fences_map_lines.py (tab fence, indented code, tab top-level, four-column fence shape, list content transformed, lazy continuation transformed, blank inside block, block end), tests/test_fences_map_prose.py, tests/test_fence.py (tab fence with label), tests/test_highlight.py, tests/test_button.py, tests/test_roundtrip.py (_directive_in_tab_fence, _directive_in_indented_code, INDENTED_DIRECTIVE_FIXTURE, TestRoundTripIndentedDirective)
  - [ ] GREEN: _indent_width, expandtabs(4) matching, _indented_code_lines, _code_line_indexes shared by map_prose and map_lines, docstrings and ABOUTME updated in src/markwright/_fences.py
  - [ ] Document: CHANGELOG.md "### Fixed" entry; CLAUDE.md _fences.py bullet
  - [ ] Verify existing suites unchanged; `just check` and `just test-integration` green
- [x] Step 2b: In-process directive preprocessors skip code
  - [x] RED: in-process indented-code tests in the ten directive test files (literal in <pre><code>, no stage markup) plus list-content guard tests; restore _directive_in_indented_code, its sampler entry, and the [grid] block of INDENTED_DIRECTIVE_FIXTURE in tests/test_roundtrip.py
  - [x] GREEN: the ten Preprocessor.run methods return map_lines("\n".join(lines), transform).split("\n")
  - [x] Document: CHANGELOG.md Fixed continuation line claims parity; CLAUDE.md priority rows note the code skipping
  - [x] Verify every suite; `just check` and `just test-integration` green
- [x] Step 3: Skip HTML tags in map_prose
  - [x] RED: tests in tests/test_fences_map_prose.py (attribute, comment single and multi-line, autolink, bare less-than, tag inside code span), tests/test_icons.py (attribute literal, trailing shortcode wrapped), tests/test_highlight.py (guards that highlight output stays as released)
  - [x] GREEN: _HTML_TAG_RE and _SKIPPED_SPAN_RE in src/markwright/_fences.py; map_prose skips them only with skip_html=True, which icons passes; docstring updated
  - [x] Document: CLAUDE.md pattern 6 and the _fences notes; no CHANGELOG entry (icons is unreleased)
  - [x] Verify tests/test_fences_map_prose.py, tests/test_highlight.py, tests/test_icons.py pass; `just check` green

## Section 3: Inline Processor Priority

- [x] Step 4: Move the icons InlineProcessor to 85
  - [x] RED: tests in tests/test_icons.py TestIconsInProcess (alt, title, autolink, inline attribute literal; link text and emphasis still render)
  - [x] GREEN: register at 85 in src/markwright/icons.py with a docstring note
  - [x] Document: CLAUDE.md priority table (85 row, 50 row) and pattern 6; docs/index.md item 5; no CHANGELOG entry
  - [x] Verify tests/test_icons.py, tests/test_highlight.py, tests/test_roundtrip.py pass; `just check` and `just docs-build` green

## Section 4: Test Policy and Conformity

- [x] Step 5: Public-API coverage for the _html helpers (task)
  - [x] Map the nine tests/test_html_helpers.py cases to grid and annotate apply_html (name the already-covered ones; add the four missing to tests/test_annotate.py TestProse)
  - [x] Delete tests/test_html_helpers.py; confirm the three exempt files state the exemption in their ABOUTME
  - [x] CLAUDE.md Testing Approach: the _fences and _markers exemption sentence
  - [x] Verify grep shows only the three exempt private imports; `just check` green with _html.py at 100%
- [x] Step 6: Fold _apply_markers and add the future import (task)
  - [x] Fold _apply_markers into apply_html in src/markwright/grid.py and src/markwright/annotate.py; postprocessors call apply_html(text)
  - [x] Add from __future__ import annotations to tests/test_annotate.py, tests/test_fence.py, tests/test_grid.py, tests/test_highlight.py, tests/test_markers.py
  - [x] Verify grep -L prints nothing, grep _apply_markers prints nothing; `just check` green
