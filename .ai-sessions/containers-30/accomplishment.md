# Accomplishment: Containers (Block Grids, Cards, and Tabs) (Issue #30)

**Archived**: 2026-11-12
**Convergence**: converged

## Spec Slice

This plan implemented the Containers goals in spec.md: block grids closed by `[/grid]`, `[card]` blocks inside them, column counts (`[grid N]` for 1 to 6) on both the block grid and the list shortcut, and a new `tabs` extension, all on one shared open/close pairing scanner.
It renamed the cards class from `mw-cards` to `mw-grid-cards`, added the `mw-grid-block`, `mw-grid-end`, `mw-card`, `mw-card-end`, `mw-tab`, and `mw-tab-end` marker contracts, and gave every extension page a Host CSS and Script section.
It sits under the `## Invariants` `paths:` and `deps: frozen` fences and the parity law, and adds no dependency.

## What Got Done

- Step 1: `_containers.scan_containers` pairs each `[/grid]`, `[/card]`, or `[/tab]` with the nearest unpaired opener of its kind at the same indentation, skipping fenced and indented code through `_fences` (8a394b9).
- Step 2: column counts on the grid shortcut, the `columns` field on the `mw-grid` payload, and the `mw-cards` to `mw-grid-cards` rename (4010bd1).
- Step 3: block grids and cards, emitted as paired markers in `mw pre` and stack-wrapped into `<div>` elements in `mw post`, plus the `mw-grid-problem` marker for `--warn` reports (15b3a77).
- Step 4: the `tabs` extension and its registry entry, emitting pymdownx `tabbed` alternate-style markup with `mw-tab-S-T` ids, plus the `mw-tab-problem` marker and marker-line recognition in the scanner (2dd020e).
- Step 5: Hugo integration tests for a block grid with cards, a tab set, a Chroma block inside a card, and both problem markers (28afb56).
- Step 6: the grid and tabs docs pages, the sample CSS for columns, cards, and CSS-only tabs, and the Tabs nav entry (82494d9).
- Step 7: a Host CSS and Script section on all 15 extension pages (e0b053f).
- Step 8: CHANGELOG, README, CLAUDE.md, and the docs pages that list extensions (842c1cf).
- After the run: spec.md reconciled with the implementation, seven amendments and one Deferred line (40d3cef).

## Deferred or Dropped

- An invalid `[grid ...]` opener (`[grid 7]`, `[grid foo]`) still pairs with its `[/grid]`: both lines stay literal with no report, but a `[card]` inside is still wrapped.
  Found by the post-run spec reconciliation; the rule is decided (an invalid opener is not an opener) and goes to a fix cycle on `containers-30`.
- The sample CSS has no rule for a list inside a `cards` block grid (`.mw-grid-cards > ul`).
  The plan wrote the selector as `ul.mw-grid-cards`, the Step 6 executor dropped it as broken, and the spec's case shipped unstyled; same fix cycle.
- Full `mw pre` idempotence for a document with container problems: in the spec's Deferred list.

## Notable Decisions

- A pre stage has no `skip_reasons` channel, so a container problem travels to `mw post --warn` as an inline `mw-grid-problem` or `mw-tab-problem` marker with a closed reason vocabulary (Steps 3 and 4).
  The plan had said "reported in post" without a way for post to see a fully literal line.
- Grid and tabs both run their pre stage at 20, so the scanner reads a line that is solely one of the six paired container markers as the opener or closer it stands for, and results carry `from_marker` so a stage leaves its own markers alone (Step 4).
  Pairing and card enclosure come out the same in either order.
- The shared marker helpers (`marker_block`, `inline_problem_marker`, `match_marker_pairs`, `report_problem_markers`) live in `_markers.py` and the six marker names in `_containers.py`; `_wrap_paired` stayed in grid because tabs builds set-level markup (Step 4).
- An empty `[tab ]` is not an opener: it stays literal with no report, and a `[/tab]` it leaves unpaired is a stray closer (Step 4).
- The docs CSS keeps `ul.mw-grid` and `ol.mw-grid` selectors beside `.md-typeset .mw-grid`, because a bare `.mw-grid` loses to mkdocs-material's `.md-typeset ul` rules (Step 6).

## Files Touched

- src/markwright/_containers.py (new), src/markwright/tabs.py (new)
- src/markwright/grid.py, src/markwright/_markers.py, src/markwright/registry.py
- tests/test_containers.py (new), tests/test_tabs.py (new)
- tests/test_grid.py, tests/test_registry.py, tests/test_roundtrip.py, tests/integration/test_hugo_pipeline.py
- docs/extensions/tabs.md (new), docs/extensions/grid.md, and the other 13 extension pages
- docs/stylesheets/extra.css, docs/index.md, docs/cli.md, docs/config.md, docs/integrations/mkdocs.md, mkdocs.yml
- CHANGELOG.md, README.md, CLAUDE.md, spec.md

## Lessons Cross-Reference

- "When a plan step says a pre stage finding is reported under `--warn`, confirm at plan time that a pre-to-post channel exists" (2026-11-11, .ai-sessions/lessons.md).
- "When a pre stage's scanner starts recognizing the stage's own emitted output, test the stage on its own output before calling it done" (2026-11-11).
- "Generalizing a docs-site CSS selector from `ul.mw-grid` to a bare `.mw-grid` drops it below mkdocs-material's rules" (2026-11-11).
- "After a `/bpe:goal` run, reconcile spec.md before calling the run done" and "A plan step that restates a spec CSS rule must copy the selector's subject from the spec" (2026-11-12).
