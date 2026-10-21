# Todo: Material Reference Parity (0.4.0, Issue #16)

Mirrors plan.md. Each top-level item is a step; sub-items are its numbered sub-steps.

## Section 1: Shared helpers and the marker module

- [x] Step 1: Shared helpers in `_html` and `_fences`
  - [x] RED: tests/test_html_helpers.py (matching_end nesting and unclosed, add_classes front-insert, no-class, added_attrs) and tests/test_fences_map_prose.py (prose, fenced, inline-code boundaries)
  - [x] GREEN: add_classes (moved from fence, with added_attrs), matching_end, map_prose; move _INLINE_CODE_RE into _fences
  - [x] REFACTOR: fence uses _html.add_classes; highlight.expand_source uses map_prose
  - [x] Verify tests/test_fence.py and tests/test_highlight.py pass unchanged
  - [x] `just check` green
- [x] Step 2: The `_markers` module and `fence` refactored onto it
  - [x] RED: tests/test_markers.py (encode version/comment-safe, find_markers block_end and empty-page, decode fail-soft cases)
  - [x] Document the marker contract in the module header
  - [x] GREEN: src/markwright/_markers.py (encode_marker, MarkerComment, find_markers, InvalidMarkerError, decode_marker)
  - [x] REFACTOR: fence onto _markers (delete its private marker code); messages match
  - [x] Verify tests/test_fence.py and tests/test_markers.py pass
  - [x] `just check` green

## Section 2: Pre-only extensions

- [x] Step 3: `button` extension
  - [x] RED: tests/test_button.py (basic, primary, escaping, no-text literal, inline mention, in-process `<p>`, shared paragraph, inline Markdown in text)
  - [x] GREEN: src/markwright/button.py (BUTTON_RE, _render_match, expand_source, preprocessor, extension)
  - [x] Wire up: register "button" in registry.py (pre_priority 20)
  - [x] `just check` green
- [x] Step 4: `lightbox` extension
  - [x] RED: tests/test_lightbox.py (url+alt, url-only empty alt, escaping, inline mention, in-process `<p>`)
  - [x] GREEN: src/markwright/lightbox.py (LIGHTBOX_RE, _render_match, expand_source, preprocessor, extension)
  - [x] Wire up: register "lightbox" in registry.py (pre_priority 20)
  - [x] `just check` green
- [ ] Step 5: `mermaid` extension
  - [ ] RED: tests/test_mermaid.py (fence to pre, tilde, escaping, other fences, prose, label-stays-text, indented in list, unclosed, in-process no highlight)
  - [ ] GREEN: src/markwright/mermaid.py (_expand_lines inline raw, no stash; preprocessor priority 45)
  - [ ] Wire up: register "mermaid" in registry.py (pre_priority 45)
  - [ ] `just check` green
- [ ] Step 6: `icons` extension
  - [ ] RED: tests/test_icons.py (flat resolve, nested join + XML strip, unknown pack/name literal, code untouched, no-packs passthrough, in-process, options: empty warns, non-table/bad-value/missing-dir OptionError, construction error, config ConfigError, valid config stored)
  - [ ] GREEN: src/markwright/icons.py (read_options, _shortcode_pattern, _load_icon, expand_source via map_prose, InlineProcessor priority 175, sentinel _NO_PACKS)
  - [ ] Wire up: register "icons" in registry.py (pre_priority 50, check_options)
  - [ ] `just check` green

## Section 3: Marker-comment extensions

- [ ] Step 7: `grid` extension
  - [ ] RED: tests/test_grid.py (marker + blank line, indent kept, inline/unknown-variant literal, classes on next list, cards, existing classes, one-marker-one-list, no-list skip+report, malformed/version/typed skips, idempotent, in-process)
  - [ ] GREEN: src/markwright/grid.py (GridMarker, _expand_lines, apply_html via _markers + add_classes, pre/post processors priority 20/30)
  - [ ] Wire up: register "grid" in registry.py (pre 20, post 30)
  - [ ] `just check` green
- [ ] Step 8: `annotate` extension
  - [ ] RED: tests/test_annotate.py (source stage; prose links/ids/per-page/nested/existing-classes/idempotent/nested-same-tag; code Pygments+Chroma whole-comment, trailing newline, no-span marker-only, no-bang keeps comment; skips: no-block/unclosed/no-list/malformed/version; in-process paragraph, labeled fence, no-list consumed)
  - [ ] GREEN: src/markwright/annotate.py (AnnotateMarker, _expand_lines, _locate, apply_html, _enclosing_comment_span, pre/post processors priority 20/30)
  - [ ] Wire up: register "annotate" in registry.py (pre 20, post 30)
  - [ ] `just check` green

## Section 4: Cross-cutting tests and registration checks

- [ ] Step 9: Round-trip, registry, CLI, and Hugo coverage
  - [ ] Extend tests/test_roundtrip.py (FIXTURE, presence assertions, degradation, TestRoundTripIcons, hypothesis grammar)
  - [ ] Extend tests/test_registry.py and tests/test_cli.py (OPTION_NAMES icons, describe stages, list/config output)
  - [ ] Extend tests/integration/test_hugo_pipeline.py (MATERIAL_SOURCE through Hugo with a demo pack)
  - [ ] Fix the responsible extension for any failing assertion (not the test)
  - [ ] `just check` and `just test-integration` green

## Section 5: Demo assets, docs, and release

- [ ] Step 10: Demo host assets (task)
  - [ ] extra.css additions for all six hooks and the annotation tooltip
  - [ ] docs/javascripts/mermaid.js (pinned CDN + initialize), lightbox.js (dialog), annotate.js (tooltip)
  - [ ] docs/icons/<pack>/*.svg demo set + docs/icons/LICENSE credit
  - [ ] mkdocs.yml extra_javascript and markwright.icons packs
  - [ ] Verify `just docs-build` strict-clean; human visual check on `just docs-serve`
- [ ] Step 11: Docs pages, nav, README, CHANGELOG, and the 0.4.0 bump (task)
  - [ ] Six docs/extensions/*.md pages (contract + live demo)
  - [ ] mkdocs.yml nav; docs/index.md and README feature lists
  - [ ] docs/cli.md list/config output; docs/config.md icons packs; docs/integrations/mkdocs.md example
  - [ ] CHANGELOG 0.4.0 Added section; pyproject version 0.4.0
  - [ ] CLAUDE.md patterns, priority table, _markers boundary
  - [ ] Verify `just docs-build` strict-clean, `just check` green, content-design review of prose
