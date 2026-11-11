# TODO: Containers (Block Grids, Cards, and Tabs): Issue #30

Mirrors `plan.md`. Check each sub-item as `/bpe:execute-plan` or `/bpe:goal` completes it.

## Section 1: Container pairing scanner (`_containers.py`)

### Step 1: The `_containers.py` pairing scanner
- [x] 1. RED: contract tests in tests/test_containers.py (pairs, problems, unclosed_grids, enclosed_by_grid, nesting, indentation, code-skipping, empty/invalid openers)
- [x] 2. Module docstring and ABOUTME header describing the pairing rules and result fields
- [x] 3. GREEN: src/markwright/_containers.py scanner (opener/closer regexes, code-skip via _fences, stack pairing, token parse, frozen pydantic result)
- [x] 4. RED: edge-case tests (tab name with `]`, list-item indentation nesting)
- [x] 5. GREEN: edge cases pass with no Step-1 regression
- [x] 6. REFACTOR: collapse opener/closer dispatch if it reduces duplication cleanly
- [x] 7. Document: docstring matches final field names and semantics
- [x] 8. Verify branch coverage and run `just check`

## Section 2: Grid column counts and the `mw-grid-cards` rename

### Step 2: Column counts on the grid shortcut and `mw-cards` → `mw-grid-cards`
- [x] 1. RED: tests/test_grid.py for column counts, the rename, order-free tokens, bounds, invalid counts left literal, fail-soft bad columns
- [x] 2. Document: GridMarker docstring for `columns`
- [x] 3. GREEN: grid.py rename CARDS_CLASS, add cols prefix, new GRID_RE + `_parse_grid_tokens`, GridMarker.columns, class assembly
- [x] 4. RED: grid + annotate same-document tests
- [x] 5. GREEN: confirm ordering holds
- [x] 6. REFACTOR: leave `_parse_grid_tokens` for Step 3 reuse
- [x] 7. Update parity assertions naming the old class (roundtrip and integration strings)
- [x] 8. Verify token-parse branch coverage and run `just check`

## Section 3: Block grids and cards

### Step 3: Block grid and card pairs, emitted in pre and stack-wrapped in post
- [x] 1. RED: tests/test_grid.py for block grids, cards, nesting (stack match), shortcut-still-works, fail-soft/literal card, in-process cases
- [x] 2. Document: module docstring and GridBlockMarker / CardMarker docstrings
- [x] 3. GREEN: expand_source emits paired markers via scan_containers + keeps shortcut; apply_html stack-wrap for paired markers; new marker models; skip_reasons threaded
- [x] 4. RED: mixed-document and apply_html-idempotence tests
- [x] 5. GREEN: wire until green
- [x] 6. REFACTOR: extract `_wrap_paired` shared by grid blocks and cards
- [x] 7. Update roundtrip grammar with `_block_grid` composite and confirm parity
- [x] 8. Verify pairing/wrap/fail-soft coverage and run `just check`

## Section 4: Tabs extension

### Step 4: The `tabs` extension (`tabs.py`) and its registry entry
- [x] 1. RED: tests/test_tabs.py for single set, grouping (one vs two sets), name escaping, empty name literal, fail-soft, in-process cases
- [x] 2. Document: tabs.py docstring (payload, id scheme, markup) and ABOUTME header
- [x] 3. GREEN: src/markwright/tabs.py (TabMarker, expand_source with first-flag, apply_html building tabbed markup with mw-tab-S-T ids, extension classes)
- [x] 4. RED: registry tests (tabs in EXTENSION_NAMES, priorities, default selection)
- [x] 5. GREEN: registry.py entry for tabs after annotate
- [x] 6. REFACTOR: promote the shared stack-match helper to a shared home if tabs needs it; keep grid green
- [x] 7. Update roundtrip grammar with `_tab_set` composite and include tabs in parity names
- [x] 8. Verify set-boundary/first-flag/escaping/fail-soft coverage and run `just check`

## Section 5: Integration, docs, and project records

### Step 5: Hugo integration cases for a block grid with cards and a tab set (task)
- [x] 1. Scope: tests/integration/test_hugo_pipeline.py end state
- [x] 2. Tooling: python:python, hugo, mw via `just test-integration`
- [x] 3. Do: CONTAINERS_SOURCE + test_container_constructs_survive_hugo asserting wrapper/card divs, cols class, tabbed-set, no leftover comments
- [x] 4. Verify: `just test-integration` exits 0 or skips cleanly; `just check` green
- [x] 5. Document: none

### Step 6: Container docs: grid.md, tabs.md, extra.css, and the nav (task)
- [x] 1. Scope: grid.md, tabs.md (new), extra.css, mkdocs.yml end state
- [x] 2. Tooling: content-design:review-content, `just docs-build`
- [x] 3. Do: grid.md block-grid demo + sections; new tabs.md; extra.css column/card/narrow + CSS-only tabs; nav adds Tabs
- [x] 4. Verify: `just docs-build --strict` exits 0; demos render and tabs switch
- [x] 5. Document: the two pages are the documentation

### Step 7: "Host CSS and Script" section on every extension page (task)
- [x] 1. Scope: docs/extensions/*.md (all 14) end state
- [x] 2. Tooling: content-design:review-content, `just docs-build`
- [x] 3. Do: add/normalize a Host CSS and Script section per page listing hooks and linking samples
- [x] 4. Verify: `just docs-build --strict` exits 0; spot-check three pages
- [x] 5. Document: the pages are the documentation

### Step 8: CHANGELOG, README, and CLAUDE.md (task)
- [ ] 1. Scope: CHANGELOG.md, README.md, CLAUDE.md end state
- [ ] 2. Tooling: content-design:review-content, python:python
- [ ] 3. Do: CHANGELOG Added/Changed; README extension list; CLAUDE.md architecture + priority table + test exemption + scope rule
- [ ] 4. Verify: `just check` green; `just docs-build --strict` clean if docs touched
- [ ] 5. Document: these files are the records
