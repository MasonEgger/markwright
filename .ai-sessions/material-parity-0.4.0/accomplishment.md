# Accomplishment: markwright 0.4.0 Material Reference Parity (Issue #16)

**Archived**: 2026-10-23
**Convergence**: converged (all 11 steps, 51 of 51 todo items, under the goal loop on branch material-parity-0.4.0; staged for release, not yet version-bumped or merged)

## Spec Slice

Six additive extensions so a host theme (Bartleby) can render every feature on the mkdocs-material reference from markwright markup alone.
markwright owns the authoring syntax and the `mw-` HTML contract; the host supplies CSS, JavaScript, and icon files.
Each is additive: documents 0.3.0 already rendered stay byte-identical.
The phase also refactored the fence marker contract into a shared module that grid and annotate reuse.
The full byte-level contracts and decisions D1 through D7 are preserved beside this file's sibling draft at `.ai-sessions/material-parity/spec.md`, and the TDD roadmap at `plan.md` / `todo.md` here.

## What Got Done

- Step 1: shared helpers `_html.add_classes` (with `added_attrs`), `_html.matching_end`, and `_fences.map_prose`, with fence and highlight refactored onto them and no output change.
- Step 2: the `_markers.py` module (comment-safe `encode_marker`, `find_markers` with block bounds, fail-soft `decode_marker`), with fence moved onto it and the `mw-fence` payload unchanged.
- Steps 3 to 6: the four pre-only extensions, button and lightbox (directive-expand, inline raw HTML), mermaid (a fence rewrite to `<pre class="mermaid">` with no stash, preprocessor priority 45), and icons (an inline-processor SVG resolver over host-supplied `packs`, priority 175, with full config-law validation).
- Steps 7 and 8: the two marker-comment pre-plus-post pairs, grid and annotate, annotate's post stage at priority 30 so it runs before fence's at 25.
- Step 9: round-trip, registry, CLI, and Hugo-integration coverage extended to all six, including a hypothesis grammar and a real Chroma build.
- Step 10: demo host assets under docs/ (extra.css hooks, docs/javascripts/ for mermaid, lightbox, and annotation, two credited demo icon packs), with mkdocs.yml wiring. The package still ships no JS, CSS, or icons.
- Step 11: six extension docs pages, nav, README and index feature lists, CLI and config docs, the mkdocs integration example, a CHANGELOG Unreleased entry, and CLAUDE.md updates.

## Deferred or Dropped

- The pyproject.toml version bump to 0.4.0 was moved out of Step 11 to Mason's release step, since the spec's `deps: frozen` invariant fences pyproject.toml. The CHANGELOG entry sits under `## [Unreleased]`.
- The `just docs-serve` visual check of the six live demos is a human check left for Mason.
- Richer Material-parity features past the 0.4.0 contracts (lightbox galleries, captions, srcset; grid column controls and nested grids; annotation forms) stay deferred per the spec roadmap.

## Notable Decisions

- D1 through D7 and the six byte-level contracts: see `.ai-sessions/material-parity/spec.md`.
- Icon credits live in docs/icons/CREDITS.txt, not a LICENSE file, because hatch's license-files glob pulled a LICENSE-named file into the sdist and failed the sdist allowlist test.
- The Extensions nav follows the existing logical grouping rather than alphabetical order, matching README and docs/index.md.
- The inert pymdownx.superfences custom_fence named mermaid was removed from mkdocs.yml, since markwright.mermaid replaces the fence at preprocessor priority 45, before superfences.

## Files Touched

- src/markwright/_markers.py (new), button.py (new), lightbox.py (new), mermaid.py (new), icons.py (new), grid.py (new), annotate.py (new)
- src/markwright/_html.py, _fences.py, fence.py, highlight.py, registry.py
- tests/test_html_helpers.py, test_fences_map_prose.py, test_markers.py, test_button.py, test_lightbox.py, test_mermaid.py, test_icons.py, test_grid.py, test_annotate.py (new); test_roundtrip.py, test_registry.py, test_cli.py, integration/test_hugo_pipeline.py (extended)
- docs/stylesheets/extra.css, docs/javascripts/{mermaid,lightbox,annotate}.js, docs/icons/, docs/extensions/{button,lightbox,mermaid,icons,grid,annotate}.md, docs/index.md, docs/cli.md, docs/config.md, docs/integrations/mkdocs.md
- mkdocs.yml, README.md, CHANGELOG.md, CLAUDE.md
