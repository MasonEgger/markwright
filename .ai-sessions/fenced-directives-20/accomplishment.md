# Accomplishment: mw pre Skips Directives Inside Fenced Code (Issue #20)

**Archived**: 2026-11-01
**Convergence**: converged

## Spec Slice

Not a spec goal; markwright is issue-driven past 0.2.0.
The cycle enforced the spec's parity invariant and the round-trip law in Component boundaries: `run_post(stub_render(run_pre(doc)))` equals the in-process render.
Before it, `mw pre` expanded a directive line inside a fenced code block while the in-process render (whose directive preprocessors run at priority 20, after `pymdownx.superfences` stashes the fence) left it literal.

## What Got Done

- Step 1: `_fences.map_lines`, the line-level twin of `map_prose`, skipping the lines of every closed fence (863dec3)
- Step 2: the eight one-to-one directive stages (youtube, slideshow, image_compare, codepen, twitter, instagram, button, lightbox) routed through `map_lines` (b8c2106)
- Step 3: grid and annotate routed through `map_lines`, their `_expand_lines` replaced by a per-line `_transform_line` (283997d)
- Step 4: a `_directive_in_fence` case in the round-trip hypothesis grammar, an explicit `TestRoundTripFencedDirective` fixture, and the CHANGELOG entry (6315dc8)

## Deferred or Dropped

- Tab-indented fences and top-level indented code: `_FENCE_OPEN_RE` and the indent math count spaces only, so `mw pre` still expands a directive inside a tab-indented in-list fence or a 4-space indented code block; found by the 2026-11-01 adversarial review after the cycle closed and carried into the next plan

## Notable Decisions

- Step 1 kept the fenced-line index set inline in both `map_prose` and `map_lines` rather than extracting a helper; the validator recorded the second caller as an info finding and the extraction is open to the next cycle
- Step 4 checked off the stale Current Status boxes for Sections 1 and 2 in plan.md, which earlier finalize passes had left unchecked; recorded as a deviation in that step's session summary

## Files Touched

- src/markwright/_fences.py
- src/markwright/{youtube,slideshow,image_compare,codepen,twitter,instagram,button,lightbox}.py
- src/markwright/grid.py
- src/markwright/annotate.py
- tests/test_fences_map_lines.py
- tests/test_{youtube,slideshow,image_compare,codepen,twitter,instagram,button,lightbox}.py
- tests/test_grid.py
- tests/test_annotate.py
- tests/test_roundtrip.py
- CHANGELOG.md

## Lessons Cross-Reference

- lessons.md (2026-10-31): "Routing every directive-line pre stage through `_fences.map_lines` (not raw line iteration) is what makes `mw pre` leave a `[button]`, `[grid]`, `[annotate]`, or embed directive literal inside a fenced code block ..."
