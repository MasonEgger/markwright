# markwright 0.4.0 Fix Plan: Todo

Mirrors `plan.md`.
One top-level checkbox per step; sub-items track the step's own sub-steps.
The `/goal` loop checks items as it goes.
Steps 16, 19, and 20 were cut on 2026-11-20, so the numbering has gaps.

## Section 1: Container Postprocessor Priority

- [x] Step 1: Move the grid, annotate, and tabs postprocessors to 27
  - [x] RED: load-order test with md_in_html before and after (tests/test_container_priority.py)
  - [x] GREEN: priority 30 to 27 in grid.py, annotate.py, tabs.py, registry.py
  - [x] Docs: CLAUDE.md priority table, spec.md Containers and Feature Status
  - [x] just check

## Section 2: Containers Fixes (#30)

- [x] Step 2: An invalid `[grid ...]` is not an opener
  - [x] RED: tests/test_containers.py, tests/test_grid.py
  - [x] GREEN: _containers.py rejects invalid grid openers, reuse grid.py validity rule
  - [x] Docs: spec.md Grid and Cards
  - [x] just check
- [x] Step 3: Column-based indentation pairing and the less-indented-line rule
  - [x] RED: tests/test_containers.py (tab/space column equality, less-indented ends container, list-item case)
  - [x] GREEN: _containers.py column indentation and less-indented-line rule
  - [x] Docs: spec.md Containers
  - [x] just check
- [x] Step 4: A card needs a paired grid
  - [x] RED: tests/test_containers.py, tests/test_grid.py
  - [x] GREEN: _containers.py card enclosure requires a paired grid
  - [x] Docs: spec.md Grid and Cards
  - [x] just check
- [x] Step 5: Emit the shortcut and annotate markers as blocks; keep a CRLF line end
  - [x] RED: tests/test_grid.py, tests/test_annotate.py, tests/test_tabs.py
  - [x] GREEN: grid.py and annotate.py via marker_block; _markers.py CRLF-safe problem marker
  - [x] Docs: spec.md Containers (Both paths)
  - [x] just check
- [x] Step 6: Tabs grouping, set numbering, backtick names, and closer validation
  - [x] RED: tests/test_tabs.py (sibling rule, S numbering, backtick names, closer decode)
  - [x] GREEN: tabs.py grouping, numbering, html_block ordering, strict closer decode
  - [x] Docs: spec.md Tabs, CLAUDE.md priority note
  - [x] just check
- [x] Step 7: Document the escape and the cards-list CSS sample (task)
  - [x] Tests pin the backslash escape (tests/test_grid.py, tests/test_tabs.py)
  - [x] docs/extensions/grid.md and tabs.md escape note
  - [x] docs/stylesheets/extra.css cards-list rules
  - [x] Docs: spec.md Containers and Grid and Cards, Feature Status drops containers fixes (#30)
  - [x] just check and just docs-build --strict

## Section 3: Block Bodies

- [x] Step 8: `_fences` reads block-opener bodies as content, not indented code
  - [x] RED: tests/test_fences_map_lines.py, tests/test_fences_map_prose.py, tests/test_roundtrip.py (five bodies)
  - [x] GREEN: _fences.py reads block-opener bodies as content
  - [x] Docs: spec.md Rules Every Feature Follows, Component boundaries, Feature Status drops block bodies
  - [x] just check

## Section 4: Pre-Stage Order

- [x] Step 9: Icons after the directive stages, and a mermaid fence in a list item
  - [x] RED: tests/test_icons.py, tests/test_mermaid.py
  - [x] GREEN: registry.py icons pre priority; mermaid.py and fence.py for list-item mermaid
  - [x] Docs: spec.md Icons and Mermaid, CLAUDE.md priority table, Feature Status drops pre-stage order
  - [x] just check

## Section 5: Highlight Escape in Split Spans (#31)

- [x] Step 10: Read in-code markers and escapes from each code line's text
  - [x] RED: tests/test_highlight.py (Pygments), Chroma fixtures in tests/test_fence.py or tests/test_highlight.py
  - [x] GREEN: highlight.py apply_html reads markers/escapes from code-line text, tags ignored
  - [x] Docs: spec.md Highlight (two post-stage sentences, correct the #31 Known gap)
  - [x] just check
- [x] Step 11: `mw pre` writes a prose escape both renderers hand back
  - [x] RED: tests/test_highlight.py, tests/test_roundtrip.py
  - [x] GREEN: highlight.py expand_source pairs backslashes, writes the marker's < as &lt;
  - [x] Docs: spec.md Highlight, Feature Status drops escape in split spans (#31)
  - [x] just check

## Section 6: Highlight Same-Line Pairing (#34)

- [x] Step 12: In-process prose pairing on the same line only
  - [x] RED: tests/test_highlight.py (no cross-line pair, same-line with code span, literal opener, declined stash span, old cross-block cases gone)
  - [x] GREEN: highlight.py InlineProcessor same-line matching
  - [x] Docs: spec.md Highlight (in-process sentence, rewrite the #34 Known gap)
  - [x] just check
- [x] Step 13: `mw pre` wraps a same-line pair in one `<mark>`, with differential tests
  - [x] RED: tests/test_highlight.py, tests/test_roundtrip.py differential corpus
  - [x] GREEN: highlight.py expand_source same-line pair, code spans included
  - [x] Docs: spec.md Highlight, keep the Decision, Feature Status drops same-line pairing (#34)
  - [x] just check
  - [x] Reminder: the CHANGELOG line for the pairs that stop highlighting is owed to Step 28

## Section 7: Annotate Overlap

- [x] Step 14: A comment token with a `!` marker is replaced by every marker's links
  - [x] RED: tests/test_annotate.py, overlapping-span test for _html.apply_edits
  - [x] GREEN: annotate.py one edit for all markers in a comment; _html.py apply_edits refuses overlap
  - [x] Docs: spec.md Annotate, Feature Status drops annotate overlap
  - [x] just check

## Section 8: Config `warn` Default (#33)

- [x] Step 15: `mw post` takes the config `warn` key as the diagnostics default
  - [x] RED: tests/test_cli.py (config warn, --warn/--no-warn last wins, post-only, PYTHONWARNINGS not escalated)
  - [x] GREEN: cli.py --no-warn and resolved warn default
  - [x] Docs: spec.md The mw CLI (warn default, correct the #33 Known gap), Feature Status drops warn default (#33) from the mw CLI row
  - [x] just check

## Section 9: Public Fence API (#32)

- [x] Step 17: `disallowed_environments(source, config)`
  - [x] RED: tests/test_config.py or tests/test_fence.py (order, two additions, empty list no warning, empty allowlist, padding, nested fence)
  - [x] GREEN: fence.py public scan; config.py disallowed_environments; __init__.py export
  - [x] Docs: spec.md Config and the Host API and Component boundaries, docs/config.md, Feature Status drops public fence API (#32)
  - [x] just check
- [x] Step 18: `config_from_mapping` input hardening
  - [x] RED: tests/test_config.py (non-mapping ConfigError, None as empty, unknown key with None value)
  - [x] GREEN: config.py config_from_mapping checks before dropping None
  - [x] Docs: spec.md Config and the Host API
  - [x] just check

## Section 10: Hardening

- [x] Step 21: Fence hardening: class tokens, dropped `prefix_value`, Chroma newline
  - [x] RED: tests/test_config.py (class tokens), tests/test_fence.py (dropped prefix_value, Chroma newline)
  - [x] GREEN: fence.py and config.py class-token validation; drop prefix_value; no second Chroma newline
  - [x] Docs: spec.md Fence
  - [x] just check
- [x] Step 22: Highlight skips `<title>` and `<textarea>`
  - [x] RED: tests/test_highlight.py (title and textarea not wrapped)
  - [x] GREEN: highlight.py apply_html adds title and textarea to the skip list
  - [x] Docs: spec.md Highlight, Feature Status drops hardening from highlight
  - [x] just check
- [ ] Step 23: Icons reports an unreadable or non-UTF-8 SVG
  - [ ] RED: tests/test_icons.py (unreadable and non-UTF-8 SVG name the file)
  - [ ] GREEN: icons.py turns OSError/UnicodeDecodeError into OptionError naming the file
  - [ ] Docs: spec.md Icons, Feature Status drops hardening from icons
  - [ ] just check
- [ ] Step 24: CLI and config I/O never end in a traceback
  - [ ] RED: tests/test_cli.py (non-UTF-8 stdin, closed stdout/broken pipe, UTF-8 regardless of locale), tests/test_config.py (unreadable config)
  - [ ] GREEN: cli.py UTF-8 stdio and boundary error mapping; config.py and icons.read_options turn OSError/UnicodeDecodeError into ConfigError/OptionError
  - [ ] Docs: spec.md The mw CLI, Config and the Host API, Component boundaries
  - [ ] just check
- [ ] Step 25: `mw pre` passes front matter through
  - [ ] RED: tests/test_cli.py (YAML and TOML front matter untouched)
  - [ ] GREEN: cli.py front matter pass-through
  - [ ] Docs: spec.md The mw CLI, Component boundaries, Feature Status clears hardening
  - [ ] just check

## Section 11: Docs Catch-Up

- [ ] Step 26: CLI, reference, and integration docs (task)
  - [ ] docs/cli.md, renderer-requirements.md, pipeline.md, integrations/hugo.md, integrations/mkdocs.md, index.md, README.md
  - [ ] just docs-build --strict
- [ ] Step 27: Extension pages, demo, and config docs (task)
  - [ ] docs/demo.md, eight ported pages, grid.md, annotate.md, config.md, embed pages
  - [ ] just docs-build --strict and tests/test_docs_tokens.py
- [ ] Step 28: CHANGELOG corrections (task)
  - [ ] CHANGELOG.md Unreleased section corrected and per-item lines added
  - [ ] Reminder: the CHANGELOG line for an indented directive that now stays inside its list item or block body is owed to Step 28 (from Step 8)
  - [ ] Docs: spec.md closes both docs-catch-up Known gaps
  - [ ] just check and just docs-build --strict

## Section 12: Material Mapping Docs Page

- [ ] Step 29: The Material-to-extension mapping page (task)
  - [ ] docs/material-mapping.md and mkdocs.yml nav
  - [ ] Docs: spec.md moves Material mapping docs page to Shipped
  - [ ] just docs-build --strict
