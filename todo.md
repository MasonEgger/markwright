# markwright 0.4.0 Fix Plan: Todo

Mirrors `plan.md`.
One top-level checkbox per step; sub-items track the step's own sub-steps.
The `/goal` loop checks items as it goes.

## Section 1: Container Postprocessor Priority

- [x] Step 1: Move the grid, annotate, and tabs postprocessors to 27
  - [x] RED: load-order test with md_in_html before and after (tests/test_container_priority.py)
  - [x] GREEN: priority 30 to 27 in grid.py, annotate.py, tabs.py, registry.py
  - [x] Docs: CLAUDE.md priority table, spec.md Containers and Feature Status
  - [x] just check

## Section 2: Containers Fixes (#30)

- [ ] Step 2: An invalid `[grid ...]` is not an opener
  - [ ] RED: tests/test_containers.py, tests/test_grid.py
  - [ ] GREEN: _containers.py rejects invalid grid openers, reuse grid.py validity rule
  - [ ] Docs: spec.md Grid and Cards
  - [ ] just check
- [ ] Step 3: Column-based indentation pairing and the less-indented-line rule
  - [ ] RED: tests/test_containers.py (tab/space column equality, less-indented ends container, list-item case)
  - [ ] GREEN: _containers.py column indentation and less-indented-line rule
  - [ ] Docs: spec.md Containers
  - [ ] just check
- [ ] Step 4: A card needs a paired grid
  - [ ] RED: tests/test_containers.py, tests/test_grid.py
  - [ ] GREEN: _containers.py card enclosure requires a paired grid
  - [ ] Docs: spec.md Grid and Cards
  - [ ] just check
- [ ] Step 5: Emit the shortcut and annotate markers as blocks; keep a CRLF line end
  - [ ] RED: tests/test_grid.py, tests/test_annotate.py, tests/test_tabs.py
  - [ ] GREEN: grid.py and annotate.py via marker_block; _markers.py CRLF-safe problem marker
  - [ ] Docs: spec.md Containers (Both paths)
  - [ ] just check
- [ ] Step 6: Tabs grouping, set numbering, backtick names, and closer validation
  - [ ] RED: tests/test_tabs.py (sibling rule, S numbering, backtick names, closer decode)
  - [ ] GREEN: tabs.py grouping, numbering, html_block ordering, strict closer decode
  - [ ] Docs: spec.md Tabs, CLAUDE.md priority note
  - [ ] just check
- [ ] Step 7: Document the escape and the cards-list CSS sample (task)
  - [ ] Tests pin the backslash escape (tests/test_grid.py, tests/test_tabs.py)
  - [ ] docs/extensions/grid.md and tabs.md escape note
  - [ ] docs/stylesheets/extra.css cards-list rules
  - [ ] Docs: spec.md Containers and Grid and Cards, Feature Status drops containers fixes (#30)
  - [ ] just check and just docs-build --strict

## Section 3: Block Bodies

- [ ] Step 8: `_fences` reads block-opener bodies as content, not indented code
  - [ ] RED: tests/test_fences_map_lines.py, tests/test_fences_map_prose.py, tests/test_roundtrip.py (five bodies)
  - [ ] GREEN: _fences.py reads block-opener bodies as content
  - [ ] Docs: spec.md Rules Every Feature Follows, Component boundaries, Feature Status drops block bodies
  - [ ] just check

## Section 4: Pre-Stage Order

- [ ] Step 9: Icons after the directive stages, and a mermaid fence in a list item
  - [ ] RED: tests/test_icons.py, tests/test_mermaid.py
  - [ ] GREEN: registry.py icons pre priority; mermaid.py and fence.py for list-item mermaid
  - [ ] Docs: spec.md Icons and Mermaid, CLAUDE.md priority table, Feature Status drops pre-stage order
  - [ ] just check

## Section 5: Highlight Escape in Split Spans (#31)

- [ ] Step 10: Read in-code markers and escapes from each code line's text
  - [ ] RED: tests/test_highlight.py (Pygments), Chroma fixtures in tests/test_fence.py or tests/test_highlight.py
  - [ ] GREEN: highlight.py apply_html reads markers/escapes from code-line text, tags ignored
  - [ ] Docs: spec.md Highlight (two post-stage sentences, correct the #31 Known gap)
  - [ ] just check
- [ ] Step 11: `mw pre` writes a prose escape both renderers hand back
  - [ ] RED: tests/test_highlight.py, tests/test_roundtrip.py
  - [ ] GREEN: highlight.py expand_source pairs backslashes, writes the marker's < as &lt;
  - [ ] Docs: spec.md Highlight, Feature Status drops escape in split spans (#31)
  - [ ] just check

## Section 6: Highlight Same-Line Pairing (#34)

- [ ] Step 12: In-process prose pairing on the same line only
  - [ ] RED: tests/test_highlight.py (no cross-line pair, same-line with code span, literal opener, declined stash span, old cross-block cases gone)
  - [ ] GREEN: highlight.py InlineProcessor same-line matching
  - [ ] Docs: spec.md Highlight (in-process sentence, rewrite the #34 Known gap)
  - [ ] just check
- [ ] Step 13: `mw pre` wraps a same-line pair in one `<mark>`, with differential tests
  - [ ] RED: tests/test_highlight.py, tests/test_roundtrip.py differential corpus
  - [ ] GREEN: highlight.py expand_source same-line pair, code spans included
  - [ ] Docs: spec.md Highlight, keep the Decision, Feature Status drops same-line pairing (#34)
  - [ ] just check
  - [ ] Reminder: the CHANGELOG line for the pairs that stop highlighting is owed to Step 28

## Section 7: Annotate Overlap

- [ ] Step 14: A comment token with a `!` marker is replaced by every marker's links
  - [ ] RED: tests/test_annotate.py, overlapping-span test for _html.apply_edits
  - [ ] GREEN: annotate.py one edit for all markers in a comment; _html.py apply_edits refuses overlap
  - [ ] Docs: spec.md Annotate, Feature Status drops annotate overlap
  - [ ] just check

## Section 8: Config `warn` Default (#33)

- [ ] Step 15: `mw post` takes the config `warn` key as the diagnostics default
  - [ ] RED: tests/test_cli.py (config warn, --warn/--no-warn last wins, post-only, PYTHONWARNINGS not escalated)
  - [ ] GREEN: cli.py --no-warn and resolved warn default
  - [ ] Docs: spec.md The mw CLI (warn default, correct the #33 Known gap)
  - [ ] just check
- [ ] Step 16: Parser hygiene in one pass
  - [ ] RED: tests/test_cli.py (no abbreviations, missing-subcommand usage on stderr, --config "" error), tests/test_config.py (no-op warning names source)
  - [ ] GREEN: cli.py allow_abbrev=False, usage on stderr, empty --config error; config.py source in no-op warning
  - [ ] Docs: spec.md The mw CLI and Config and the Host API, Feature Status drops warn default (#33)
  - [ ] just check

## Section 9: Public Fence API (#32)

- [ ] Step 17: `disallowed_environments(source, config)`
  - [ ] RED: tests/test_config.py or tests/test_fence.py (order, two additions, empty list no warning, empty allowlist, padding, nested fence)
  - [ ] GREEN: fence.py public scan; config.py disallowed_environments; __init__.py export
  - [ ] Docs: spec.md Config and the Host API and Component boundaries, docs/config.md, Feature Status drops public fence API (#32)
  - [ ] just check
- [ ] Step 18: `config_from_mapping` input hardening
  - [ ] RED: tests/test_config.py (non-mapping ConfigError, None as empty, unknown key with None value)
  - [ ] GREEN: config.py config_from_mapping checks before dropping None
  - [ ] Docs: spec.md Config and the Host API
  - [ ] just check

## Section 10: Hardening

- [ ] Step 19: One integer helper for every directive and annotation integer
  - [ ] RED: embed tests, tests/test_grid.py, tests/test_annotate.py (long digit string, non-ASCII digit stay literal)
  - [ ] GREEN: one integer helper; route every directive/annotation integer through it
  - [ ] Docs: spec.md Embeds
  - [ ] just check
- [ ] Step 20: `decode_marker` turns every payload failure into a skip
  - [ ] RED: tests/test_markers.py (too-long number, deep nesting, lone surrogate)
  - [ ] GREEN: _markers.py decode_marker catches ValueError/RecursionError and lone surrogate
  - [ ] Docs: spec.md Rules Every Feature Follows and Component boundaries
  - [ ] just check
- [ ] Step 21: Fence hardening: class tokens, dropped `prefix_value`, Chroma newline
  - [ ] RED: tests/test_config.py (class tokens), tests/test_fence.py (dropped prefix_value, Chroma newline)
  - [ ] GREEN: fence.py and config.py class-token validation; drop prefix_value; no second Chroma newline
  - [ ] Docs: spec.md Fence
  - [ ] just check
- [ ] Step 22: Highlight skips `<title>` and `<textarea>`
  - [ ] RED: tests/test_highlight.py (title and textarea not wrapped)
  - [ ] GREEN: highlight.py apply_html adds title and textarea to the skip list
  - [ ] Docs: spec.md Highlight, Feature Status drops hardening from highlight
  - [ ] just check
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
- [ ] Step 25: Skip a multi-line HTML comment and pass front matter through
  - [ ] RED: tests/test_fences_map_lines.py, tests/test_fences_map_prose.py, tests/test_roundtrip.py, tests/test_cli.py
  - [ ] GREEN: _fences.py HTML-comment skip region; cli.py front matter pass-through
  - [ ] Docs: spec.md Rules Every Feature Follows, The mw CLI, Component boundaries, Feature Status clears hardening
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
  - [ ] Docs: spec.md closes both docs-catch-up Known gaps
  - [ ] just check and just docs-build --strict

## Section 12: Material Mapping Docs Page

- [ ] Step 29: The Material-to-extension mapping page (task)
  - [ ] docs/material-mapping.md and mkdocs.yml nav
  - [ ] Docs: spec.md moves Material mapping docs page to Shipped
  - [ ] just docs-build --strict
