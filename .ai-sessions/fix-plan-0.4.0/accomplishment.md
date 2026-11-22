# Accomplishment: The 0.4.0 Fix Plan

**Archived**: 2026-11-21
**Convergence**: converged

## Spec Slice

This plan implemented the code and docs items that stood in spec.md's Roadmap Upcoming ahead of the 0.4.0 release: the container postprocessor priority, the containers fixes the #30 spec reconciliation found, block bodies, the pre-stage order, the highlight escape in split spans (#31), highlight same-line pairing (#34), annotate overlap, the config `warn` default (#33), the public fence API (#32), hardening, the docs catch-up, and the Material mapping docs page.
Every step was grounded in a `Planned (ITEM):` sentence under Goals; a step that shipped cleared the sentence and deleted its `Today` sentence.
It sits under the `## Invariants` `paths:` and `deps: frozen` fences and the parity law, and adds no dependency.
The release itself was never in the plan.

## What Got Done

- Step 1: the grid, annotate, and tabs postprocessors run at 27, below `raw_html` and above fence, so `md_in_html` load order no longer matters (83c7be6).
- Step 2: an invalid `[grid ...]` line is not an opener (f49d7a3).
- Steps 3 and 4: containers pair by indentation column, a less-indented line ends a container, and a card needs a paired grid (2080799).
- Steps 5 through 7: the shortcut and annotate markers are emitted as blocks, a CRLF line end survives a problem marker, tabs group by the sibling rule with stable set numbers, backtick tab names stay text, and the docs carry the escape note and the cards-list CSS (24a1a6f).
- Step 8: `_fences` reads the body of an admonition, details, content-tab, definition, or footnote opener as content, and a directive's expansion stays at the directive line's indentation (9a76768).
- Step 9: the icons pre stage runs at 5, after every directive stage, and leaves a diagram the mermaid stage emitted alone (78a8fb7).
- Steps 10 and 11: `mw post` reads in-code highlight markers and escapes from each code line's text with the tags taken out, and `mw pre` writes a prose escape that Python-Markdown and a CommonMark renderer both hand back (9e291ec).
- Steps 12 and 13: highlight pairs markers on one line only, in both paths, and `mw pre` wraps a same-line pair in one `<mark>`, code spans included (03e7561).
- Step 14: a comment token with a `!` marker is replaced by every marker's links in one edit, and `_html.apply_edits` refuses overlapping edits (02d3f26).
- Step 15: `mw post` takes the config `warn` key as its diagnostics default, with `--warn` and `--no-warn` applied last (a99c9a5).
- Steps 17 and 18: the public `disallowed_environments(source, config)`, and `config_from_mapping` input checks (39c0427).
- Steps 21 and 22: fence class tokens are validated, a dropped `prefix_value` is reported, a Chroma line gets no second newline, and highlight skips `<title>` and `<textarea>` (9dae14b).
- Steps 23 through 25: an unreadable or non-UTF-8 SVG or config file is a one-line error, `mw` I/O never ends in a traceback, and `mw pre` passes YAML and TOML front matter through (2a78c8b).
- Steps 26 through 28: the CLI, reference, integration, extension, demo, and config docs and the CHANGELOG brought up to the code (9d2d408).
- Step 29: `docs/material-mapping.md`, the Material-to-extension mapping page (f2d99ca).
- Final sweep: four shipped Upcoming lines deleted, the block-bodies rule made to agree with the Mermaid Known gap, and prose reflowed (0b4c67f).
- After the run: spec.md reconciled against all 45 recorded deviations, with one mismatch fixed (two stale sentences about inline code spans).

## Deferred or Dropped

- Step 16 (parser hygiene), Step 19 (one integer helper), Step 20 (`decode_marker` payload failures), and the HTML-comment half of Step 25 were cut on 2026-11-20 to ship 0.4.0 (0312155).
  Each is a `Known gap` sentence under Goals and a Roadmap Deferred line in spec.md.
- A `mermaid` fence in a list item or inside another block: Step 9 promised one exact `<pre>` at any indentation and could not deliver it across three renderers.
  Mermaid is supported at the top level only; anything else is best effort and its output is not specified.

## Notable Decisions

- Step 9 took thirteen validator passes on renderer corner cases before the maintainer cut the scope: mermaid at the top level only, recorded as a Known gap (placement) and a Decision in spec.md.
  The rule since: a validator's bar is documented, supported behavior, and input no author types is declared unsupported, never hardened.
- Grid and tabs moved their in-process preprocessor from 20 to 21, ahead of Python-Markdown's `html_block`, so a marker comment is stashed whole and a tab name with backticks stays text (Step 6).
- `_markers.encode_marker` writes a backtick as a `\uXXXX` escape, so no marker payload can open a code span (Step 6).
- `_fences` classifies every line's block context in one forward pass (`_scan_blocks`) and caches the result per document, so successive pre stages over unchanged text share it (Step 8).
- Highlight got its own code-span reader, `_fences.find_inline_code_spans`, and calls `map_prose(skip_inline_code=False)`, because a same-line pair may hold a code span and a span may hold a line end (Step 13).
  Icons keeps the default and cuts spans out one line at a time.
- Highlight same-line pairing (#34) is the rule in both paths; pairs that crossed a line end stop highlighting, and the CHANGELOG says so.
- `fence.environment_names` is the one scan behind `disallowed_environments`; `fence` never imports `config` (Step 17).
- `parse_grid_tokens` lives in `_containers`, so the scanner and grid share one validity rule (Step 2).
- Front matter pass-through in `mw pre` was kept when the other half of Step 25 was cut.

## Files Touched

- src/markwright/_containers.py, _fences.py, _html.py, _markers.py, registry.py, cli.py, config.py, __init__.py
- src/markwright/grid.py, tabs.py, annotate.py, highlight.py, fence.py, icons.py, mermaid.py, button.py, lightbox.py, and the six embed modules
- tests/test_container_priority.py (new), and the tests for containers, grid, tabs, annotate, highlight, fence, fences, html, markers, icons, mermaid, button, slideshow, cli, config, registry, and roundtrip
- tests/integration/test_hugo_pipeline.py
- docs/material-mapping.md (new), docs/cli.md, config.md, demo.md, index.md, pipeline.md, renderer-requirements.md, both integration pages, thirteen extension pages, docs/stylesheets/extra.css, mkdocs.yml
- CHANGELOG.md, README.md, CLAUDE.md, spec.md

## Lessons Cross-Reference

- "A plan line that predicts how several renderers treat the same indented raw HTML is a research question, so probe it on every supported renderer before it becomes a step" (2026-11-20, .ai-sessions/lessons.md).
- "Set a validator's review bar at documented, supported behavior, and write the rest as Known gaps" (2026-11-20).
- "A fix round answers the finding and stops, and a sentence added to spec.md beyond the finding needs its own probe of every variant it names" (2026-11-20).
- "A parity test between two paths passes when both are wrong the same way; assert containment as well" (2026-11-18).
- "Check that spec.md is inside the spec's `paths:` fence before a plan whose every step edits it" (2026-11-18).
- "A step that ships a Roadmap Upcoming item deletes that Upcoming line in the same commit" (2026-11-21).
