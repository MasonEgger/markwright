# Session Summary: Cut Four Items From the 0.4.0 Fix Plan

**Date**: 2026-11-20
**Duration**: not measured
**Conversation Turns**: one orchestrator turn, between the `pre-stage-order` and `highlight-escape` batches of the `/goal` run
**Estimated Cost**: not measured
**Model**: claude-fable-5-2 (orchestrator)

## Goal Context

- **Outcome**: plan edit only; the `/goal` run continues at Step 10
- **Subagent dispatches**: none
- **Steps completed**: 9 of 26 (the plan had 29 before this edit)

## Key Actions

- Removed Step 16 (parser hygiene), Step 19 (one integer helper), and Step 20 (`decode_marker` payload failures) from `plan.md` and `todo.md`.
- Trimmed Step 25 to front matter pass-through; the multi-line HTML comment region is gone from it.
- Step numbers keep their gaps (16, 19, 20), so the cross-references to Steps 27 and 28 still hold.
- Batches after the edit: `config-warn` is Step 15 alone, `hardening-a` is Steps 21 and 22, `hardening-b` is Steps 23 to 25.
- Step 15 now drops `warn` default (#33) from the `mw` CLI row of Feature Status, which Step 16 used to do.
- Step 28 no longer owes a CHANGELOG line for abbreviated options, since they keep working.
- `spec.md`: each cut `Planned` sentence and its `Today` sentence became one `Known gap` sentence that states what the code does today; the two Component boundaries `Planned` sentences for the cut items are deleted; Roadmap Upcoming drops the cut clauses; Roadmap Deferred gains three lines; Feature Status sets the six ported embed rows to `none` and drops `warn` default (#33) from the config row.
- `CLAUDE.md`: the plan line says 26 steps.
- Probed the four behaviors the new `Known gap` sentences state before writing them: `mw post --w` exits 0, `mw` with no subcommand prints usage on stdout, `--config ""` exits 0, and a 4,301-digit `[youtube]` height ends `mw pre` in a `ValueError` traceback.

## Prompt Inventory

| Prompt | Action | Outcome |
|--------|--------|---------|
| "a 4301 digit number? ... Who would want that many?" | Listed the plan steps that fix input nobody types | Mason picked the cuts |
| "Cut the ones you said to cut, I just want to ... ship this library" | Edited `plan.md`, `todo.md`, `spec.md`, `CLAUDE.md` after Step 9 committed | This commit |

## Observations

- The cut steps came from the 0.4.0 adversarial review, which reported every input that ends in a traceback without asking whether an author could type it.
- Steps 11, 18, and 23 are small and stay in the plan; Mason has not asked to cut them.
- Open with Mason: whether Step 13's generated differential corpus becomes hand-written cases, and whether the mermaid `Known gap` list collapses to one sentence in the docs catch-up batch.

## Suggested Skills for Next Session

- `python:python` for Steps 10 through 25.
- `content-design:review-content` for Steps 26 through 29.
