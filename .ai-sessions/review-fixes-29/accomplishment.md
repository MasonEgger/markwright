# Accomplishment: 0.4.0 Adversarial Review Fixes (Issue #29)

**Archived**: 2026-11-08
**Convergence**: converged

## Spec Slice

This plan fixed the eight findings from the 2026-11-01 adversarial review of the `material-parity-0.4.0` branch (the six 0.4.0 extensions plus the #20 fenced-directive fix), filed as issue #29.
It sits under the `## Invariants` `paths:` and `deps: frozen` fences and the parity law in spec.md.
It touches no dependency and no public contract payload; it moves `mw pre` toward the in-process reference and tightens the branch's test policy.
The two halves it could not reach without a Markdown parser (a marker or shortcode inside alt text, a link title, or a raw HTML block's text content) stay in the spec's Deferred list.

## What Got Done

- Step 1: bounded `annotate._locate`'s list search by the marker's region, so two chained `[annotate]` markers no longer claim the same `<ol>` or corrupt the tag; the first is skipped fail-soft and reported (cbdd03e).
- Step 2: `_fences` reads a tab as four columns and detects top-level indented code, so `mw pre` treats a tab-indented in-list fence as code and leaves indented code alone across both mappers; the duplicated fenced-line set from the #20 cycle is now one helper (05ba9ff).
- Step 2b: routed the ten in-process directive preprocessors through `_fences.map_lines`, so a directive line inside indented code stays literal in both paths (8137d66).
- Step 3: added an HTML-tag grammar to `map_prose` behind a `skip_html` flag that only icons passes, so `mw pre` no longer rewrites an icon shortcode inside an HTML tag, comment, or autolink (72da70c).
- Step 4: moved the icons InlineProcessor from 175 to 85, so an in-process shortcode inside alt text, a link title, an autolink, or an inline HTML attribute stays literal; highlight stays at 175 (8d0f9c0).
- Step 5: deleted `tests/test_html_helpers.py` and covered `_html.add_classes` and `_html.matching_end` through grid and annotate `apply_html`; wrote the `_fences` and `_markers` test exemption into CLAUDE.md (59612d1).
- Step 6: folded `_apply_markers` into `apply_html` in grid and annotate, and added `from __future__ import annotations` to five test files (2bffb0a).

## Deferred or Dropped

- `mw pre` parity inside alt text, link titles, and raw HTML block content: left in the spec's Deferred list; it needs a block-level parser, and the CLI rewriting those is the more useful behavior until a Decision says otherwise.
- The `spec.md` Deferred wording was not widened to name link destinations and image sources: `spec.md` is outside the `paths:` fence, so that edit is a human-approved spec change, not a step here.

## Notable Decisions

- Highlight stays at 175, not moved to 85 with icons: its output is already released, and a `<^>` marker holds `<` and `>`, so moving it below Python-Markdown's inline HTML pattern at 90 would change released output. Only icons, which is unreleased, moved.
- Exempt `_fences` and `_markers` from the public-API-only test rule (self-contained algorithms with their own contracts), and rewrite the rest. `test_markers.py` may import `_html.tokenize` to build inputs, named in the exemption.
- Step 2b was added mid-run after Step 2's implement pass found the plan's premise wrong: in-process directive preprocessors at priority 20 expanded a directive out of indented code, so the two paths disagreed until they were routed through `map_lines`.

## Files Touched

- src/markwright/_fences.py
- src/markwright/icons.py
- src/markwright/annotate.py
- src/markwright/grid.py
- src/markwright/{youtube,slideshow,image_compare,codepen,twitter,instagram,button,lightbox}.py
- tests/test_annotate.py, tests/test_fence.py, tests/test_grid.py, tests/test_highlight.py, tests/test_icons.py, tests/test_markers.py
- tests/test_fences_map_lines.py, tests/test_fences_map_prose.py, tests/test_roundtrip.py
- tests/test_button.py and the ten directive-stage suites
- tests/test_html_helpers.py (deleted)
- CHANGELOG.md, CLAUDE.md, docs/index.md

## Lessons Cross-Reference

- "Check the spec `paths:` fence before directing an executor to edit `spec.md`" (2026-11-07, .ai-sessions/lessons.md): a Step 4 fix pass edited `spec.md` outside the fence on my instruction and failed validator iteration 2 as a fence block; it was reverted and the wording left for a human-approved spec step.
