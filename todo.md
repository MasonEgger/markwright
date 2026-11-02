# Todo: 0.4.0 Adversarial Review Fixes (Issue #29)

Mirrors plan.md. Each top-level item is a step; sub-items are its numbered sub-steps.

## Section 1: Annotate Chaining

- [ ] Step 1: Bound the annotation-list search by the marker's region
  - [ ] RED: chained-marker tests in tests/test_annotate.py (TestSkippedMarkers: skipped and reported, both markers removed; TestInProcess: one mw-annotations list, no corrupted tag)
  - [ ] GREEN: _locate searches for the list in range(block_close + 1, block_end); docstring updated
  - [ ] Verify tests/test_annotate.py passes in full
  - [ ] `just check` green

## Section 2: Code Detection in `_fences`

- [ ] Step 2: Tab-aware indentation and indented code blocks
  - [ ] RED: tests in tests/test_fences_map_lines.py (tab fence, indented code, tab top-level, four-column fence shape, list content transformed, lazy continuation transformed, blank inside block, block end), tests/test_fences_map_prose.py, tests/test_fence.py (tab fence with label), tests/test_highlight.py, tests/test_button.py, tests/test_roundtrip.py (_directive_in_tab_fence, _directive_in_indented_code, INDENTED_DIRECTIVE_FIXTURE, TestRoundTripIndentedDirective)
  - [ ] GREEN: _indent_width, expandtabs(4) matching, _indented_code_lines, _code_line_indexes shared by map_prose and map_lines, docstrings and ABOUTME updated in src/markwright/_fences.py
  - [ ] Document: CHANGELOG.md "### Fixed" entry; CLAUDE.md _fences.py bullet
  - [ ] Verify existing suites unchanged; `just check` and `just test-integration` green
- [ ] Step 3: Skip HTML tags in map_prose
  - [ ] RED: tests in tests/test_fences_map_prose.py (attribute, comment single and multi-line, autolink, bare less-than, tag inside code span), tests/test_icons.py (attribute literal, trailing shortcode wrapped), tests/test_highlight.py (attribute, autolink, marker in tag text content)
  - [ ] GREEN: _HTML_TAG_RE and _SKIPPED_SPAN_RE in src/markwright/_fences.py; map_prose iterates the alternation; docstring updated
  - [ ] Document: CHANGELOG.md "### Fixed" entry; CLAUDE.md patterns 3 and 6
  - [ ] Verify tests/test_fences_map_prose.py, tests/test_highlight.py, tests/test_icons.py pass; `just check` green

## Section 3: Inline Processor Priority

- [ ] Step 4: Move the icons and highlight InlineProcessors to 85
  - [ ] RED: tests in tests/test_icons.py TestIconsInProcess (alt, title, autolink, inline attribute literal; link text and emphasis still render), tests/test_highlight.py TestInlineHighlight (same five shapes), tests/test_roundtrip.py (_prose_block inline-tag variant, FIXTURE prose)
  - [ ] GREEN: register at 85 in src/markwright/icons.py and src/markwright/highlight.py with docstring notes
  - [ ] Document: CLAUDE.md priority table (85 row, 50 row) and pattern 6; docs/index.md items 3 and 5; CHANGELOG.md "### Fixed" highlight entry
  - [ ] Verify tests/test_icons.py, tests/test_highlight.py, tests/test_roundtrip.py pass; `just check` and `just docs-build` green

## Section 4: Test Policy and Conformity

- [ ] Step 5: Public-API coverage for the _html helpers (task)
  - [ ] Map the nine tests/test_html_helpers.py cases to grid and annotate apply_html (name the already-covered ones; add the four missing to tests/test_annotate.py TestProse)
  - [ ] Delete tests/test_html_helpers.py; confirm the three exempt files state the exemption in their ABOUTME
  - [ ] CLAUDE.md Testing Approach: the _fences and _markers exemption sentence
  - [ ] Verify grep shows only the three exempt private imports; `just check` green with _html.py at 100%
- [ ] Step 6: Fold _apply_markers and add the future import (task)
  - [ ] Fold _apply_markers into apply_html in src/markwright/grid.py and src/markwright/annotate.py; postprocessors call apply_html(text)
  - [ ] Add from __future__ import annotations to tests/test_annotate.py, tests/test_fence.py, tests/test_grid.py, tests/test_highlight.py, tests/test_markers.py
  - [ ] Verify grep -L prints nothing, grep _apply_markers prints nothing; `just check` green
