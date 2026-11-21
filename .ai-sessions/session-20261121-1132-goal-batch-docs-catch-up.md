# Session Summary: Docs Catch-Up

**Date**: 2026-11-21
**Duration**: about 1 hour
**Conversation Turns**: 3 dispatches (implement, fix, finalize)
**Estimated Cost**: not tracked
**Model**: claude-sonnet-5-5

## Goal Context

- **Condition**: /bpe:goal run of plan.md Section 11, Docs Catch-Up, batch docs-catch-up
- **Mode**: section
- **Outcome**: converged (validator pass 2 clean)
- **Turn count**: 3
- **Subagent dispatches**: 3 `bpe:step-executor` invocations (implement, fix, finalize)
- **Steps completed**: 3 of 3 (Steps 26, 27, 28)

## Key Actions

- Step 26: docs/cli.md, renderer-requirements.md (new Marker Comments section), pipeline.md, integrations/hugo.md, integrations/mkdocs.md, index.md, and the README now describe containers, every marker, all fifteen extensions, and the real CLI behavior (`--exclude NAME`, `PYTHONWARNINGS=error`, `mw render` loads nothing else and needs Pygments, front matter and `***` note, broken-pipe scope).
- Step 27: the demo shows all fifteen extensions, the eight ported pages gained an HTML Contract section, the embed pages say an embed line needs blank lines around it, grid.md, annotate.md (new Marker Contracts), mermaid.md (top level only), and config.md (`label_class`, `secondary_label_class`, a Hugo example that runs) were corrected.
- Step 28: the CHANGELOG Unreleased section was corrected and given the per-item lines (upgrade notes, #33, #34, block bodies, `disallowed_environments`, stricter `config_from_mapping`, class tokens, prefix value, `<title>` and `<textarea>`, front matter, UTF-8 and exit 2).
- spec.md: both `Known gap (docs catch-up)` entries and the Roadmap item removed; the Mermaid placement gaps collapsed into one `Known gap (placement)` sentence; CLAUDE.md pointers to the removed sentences fixed.
- Validator pass 1: two blocks (the Hugo page said marker comments get the `raw HTML omitted` placeholder and a warning, when Hugo drops them silently; the CHANGELOG exit 2 line covered every subcommand), one warn (three sentences on one admonition line in two files), one info (the script placement sentence on three embed pages).
  The fix round resolved all four; pass 2 was clean.

## Prompt Inventory

| Prompt/Command | Action Taken | Outcome |
|---|---|---|
| Mode: implement, Steps 26-28 | Probed each claim, edited docs, CHANGELOG, spec | just check and docs-build green |
| Mode: fix, pass 1 findings | Four exact-string edits | green, tree d107425 |
| Mode: finalize | Summary, one commit, push | see Finalize-Report |

## Efficiency Insights

**What went well:**
- Probing each claim with `mw` and a real Hugo build caught wrong statements before writing them.

**What could improve:**
- The Hugo probe checked raw HTML but not comments, which the validator then caught.

**Course corrections:**
- `mw list` takes no `--config`, so the CHANGELOG config-file sentence names `mw config` only.

## Deviations from Plan

- Plan said: name all nine markers the release adds.
  Deviated: the code writes ten new marker names (`mw-grid`, `mw-grid-block`, `mw-grid-end`, `mw-card`, `mw-card-end`, `mw-annotate`, `mw-tab`, `mw-tab-end`, `mw-grid-problem`, `mw-tab-problem`), so the CHANGELOG names all ten.
  Impact: none beyond the count.
- Plan said: note the priority 27 move in the CHANGELOG.
  Deviated: skipped, since grid, annotate, and tabs are new in 0.4.0 and 0.3.0 had nothing at priority 30 for a host to notice.
  Impact: none.
- Plan said: correct the `mw-cards` to `mw-grid-cards` rename line.
  Deviated: removed the bullet, since `mw-cards` never shipped; `mw-grid-cards` is named in the grid Added line.
  Impact: none.

## Open Info Findings

None.

## Process Improvements

- A claim about what another tool does needs a probe per kind of node (see lessons.md).
