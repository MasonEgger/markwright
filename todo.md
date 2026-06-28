# TODO: markwright Pipeline CLI (`mw`)

Mirrors `plan.md`. `/bpe:execute-plan` checks off sub-steps as it goes.

## Step 1: Simple Embed Stage Functions
- [x] 1. RED: stage-function tests for youtube, slideshow, image_compare (new classes; existing untouched)
- [x] 2. GREEN: add `_render_match` + `expand_source`; refactor each Preprocessor to delegate (keep htmlStash)
- [x] 3. REFACTOR: no duplicated regex/builder between expand_source and the Preprocessor
- [x] 4. Existing in-process tests pass; `just check`

## Step 2: Script Embed Stage Functions
- [x] 1. RED: stage-function + idempotency + no-signature tests for codepen, twitter, instagram
- [x] 2. GREEN: `_render_match`, `expand_source`, `apply_html` (signature inject, idempotent); Postprocessor delegates to apply_html; drop the `found` flag
- [x] 3. REFACTOR: single signature + script constant per module
- [x] 4. Existing script-injection tests pass; `just check`

## Step 3: Fence Stage Functions, `mw-fence` Marker, Version Validation
- [x] 1. RED: TestFenceExpandSource + TestFenceApplyHtml (label, prefix, malformed, bad version, no-block, silent-no-op)
- [x] 2. Document the marker contract in the module header
- [x] 3. GREEN: rename to `mw-fence` + add `version: 1`; `expand_source`; `apply_html` with validation + warnings; adapters delegate
- [x] 4. REFACTOR: MARKER_NAME / MARKER_VERSION constants shared
- [x] 5. Existing fence tests pass; `just check`

## Step 4: Highlight Stage Functions
- [x] 1. RED: TestHighlightApplyHtml + TestHighlightExpandSource (prose wrap, in-code untouched, inline-code untouched, backslash literal)
- [x] 2. GREEN: extract `apply_html` (Postprocessor delegates); add code-region-aware `expand_source`
- [x] 3. REFACTOR: share marker/backslash regexes; keep span-safe wrapper in apply_html only
- [x] 4. Existing highlight tests pass; `just check`

## Step 5: Stage Registry and Selection
- [ ] 1. RED: tests/test_registry.py (select default/use/exclude/unknown, run_pre, run_post, warnings threading, describe)
- [ ] 2. GREEN: registry.py with REGISTRY, select_extensions, run_pre, run_post, describe; priorities per plan
- [ ] 3. REFACTOR: declarative, no per-extension branching in run_pre/run_post
- [ ] 4. `just check`

## Step 6: CLI Skeleton, `list`, `--version`, Entry Point
- [ ] 1. RED: tests/test_cli.py (--version, list, usage error)
- [ ] 2. GREEN: cli.py main() with argparse subparsers; implement list + --version
- [ ] 3. Add `[project.scripts] mw = "markwright.cli:main"` to pyproject.toml
- [ ] 4. REFACTOR: shared parser-builder helper
- [ ] 5. `just check`

## Step 7: CLI `post` Subcommand
- [ ] 1. RED: TestCliPost (stdin->stdout inject once, --use, --exclude, --warn stderr, no-warn silent, unknown name exit 2)
- [ ] 2. GREEN: post handler (stdin, select, run_post, warnings->stderr); add --use/--exclude/--warn
- [ ] 3. REFACTOR: factor stdin/stdout + selection-error helpers
- [ ] 4. `just check`

## Step 8: CLI `pre` Subcommand
- [ ] 1. RED: TestCliPre (youtube expand, prose mark wrap, fence marker emit, --use/--exclude, unknown name exit 2)
- [ ] 2. GREEN: pre handler via run_pre; add --use/--exclude (no --warn)
- [ ] 3. `just check`

## Step 9: CLI `render` Subcommand
- [ ] 1. RED: TestCliRender (matches in-process render, --use subset, unknown name exit 2)
- [ ] 2. GREEN: render handler builds markdown.Markdown (superfences + highlight + selected markwright.*)
- [ ] 3. REFACTOR: all four subcommands share parser-builder + IO helpers
- [ ] 4. `just check`

## Step 10: Cross-Stage Round-Trip Integration Tests
- [ ] 1. RED: tests/test_roundtrip.py (stub render; full-feature fixture pre|render|post == in-process; idempotency; comment-strip degradation)
- [ ] 2. GREEN: adjust priorities/internals only as needed to match
- [ ] 3. REFACTOR: encode fence/highlight post order explicitly if needed
- [ ] 4. `just check`

## Step 11: Docs
- [ ] 1. docs/cli.md (subcommands, flags, exit codes, pipeline example)
- [ ] 2. docs/pipeline.md (integration guide, Hugo + Unix examples)
- [ ] 3. docs/renderer-requirements.md (the three requirements, mw-fence v1 schema, degradation)
- [ ] 4. mkdocs.yml nav: add CLI section
- [ ] 5. `just docs-build` strict, no warnings

## Step 12: Packaging Smoke Test
- [ ] 1. RED: tests/test_packaging.py (`mw --version` and `mw list` via subprocess return 0)
- [ ] 2. GREEN: verify entry point; `uv sync` installs `mw`
- [ ] 3. `just check`
