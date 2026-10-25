# Todo: mw pre Skips Directives Inside Fenced Code (Issue #20)

Mirrors plan.md. Each top-level item is a step; sub-items are its numbered sub-steps.

## Section 1: The fence-aware line mapper

- [ ] Step 1: `_fences.map_lines`
  - [ ] RED: tests/test_fences_map_lines.py (one-to-one skips a fence, one-to-many expands only outside, indented in-list fence skipped, unclosed fence still transformed)
  - [ ] GREEN: add map_lines to src/markwright/_fences.py (fenced-line index set from find_fenced_blocks, extend with [line] inside a fence else transform(line))
  - [ ] Verify tests/test_fences_map_prose.py and tests/test_fences_map_lines.py pass
  - [ ] `just check` green

## Section 2: Directive stages onto the mapper

- [ ] Step 2: The eight one-to-one directive stages
  - [ ] RED: a directive-in-fence assertion in each of tests/test_{youtube,slideshow,image_compare,codepen,twitter,instagram,button,lightbox}.py
  - [ ] GREEN: expand_source onto map_lines in each of src/markwright/{youtube,codepen,twitter,instagram}.py (closure over load) and {slideshow,image_compare,button,lightbox}.py; import map_lines
  - [ ] Verify the eight existing suites pass unchanged; correct any test that encoded the bug
  - [ ] `just check` green
- [ ] Step 3: `grid` and `annotate` (one-to-many)
  - [ ] RED: a directive-in-fence assertion in tests/test_grid.py and tests/test_annotate.py
  - [ ] GREEN: replace _expand_lines with _transform_line(line) -> list[str] and call via map_lines in src/markwright/grid.py and annotate.py; import map_lines; delete old _expand_lines
  - [ ] Verify tests/test_grid.py and tests/test_annotate.py pass unchanged plus the two new assertions
  - [ ] `just check` green

## Section 3: Cross-tool parity net and release note

- [ ] Step 4: Round-trip grammar coverage and the CHANGELOG entry
  - [ ] RED/extend: _directive_in_fence composite + st.one_of entry + TestRoundTripFencedDirective explicit fixture in tests/test_roundtrip.py
  - [ ] GREEN: no source change expected; fix the responsible stage if a hypothesis example fails
  - [ ] Document: CHANGELOG.md "### Fixed" under "## [Unreleased]" referencing #20
  - [ ] Verify `just check` and `just test-integration` green
