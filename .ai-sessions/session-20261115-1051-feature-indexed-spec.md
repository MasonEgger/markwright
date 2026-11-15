# Session Summary: Rebuild spec.md Goals by Feature

**Date**: 2026-11-13 to 2026-11-15
**Duration**: about 5 hours across two sittings
**Conversation Turns**: 7 in this segment
**Estimated Cost**: not measured
**Model**: Claude Fable 5 (claude-fable-5-2)

## Key Actions

- Took Mason's concern that the checked-in spec.md listed no features and read as a set of rules, and traced it: Goals held five one-line bullets for everything through 0.3.0 plus two long subsections named for 0.4.0 and for issue #30.
- Traced the cause to the bpe plugin, not to one bad run: since 0.7.0 its text defines the spec's fences and never says what Goals holds, how built differs from planned, or what happens to a phase's requirements after they ship.
- Rebuilt `## Goals` by feature: a Feature Status table (kind, release state, open work, docs page, module), the rules every feature follows, and one entry per feature for all fifteen extensions, the CLI, the config system and host API, click-to-load, and the docs site.
- Had one subagent review the root-cause analysis and a second review the rebuilt spec claim by claim against the code, then reproduced each finding before acting on it.
- Rewrote plugin issue MasonEgger/bpe-claude-code-plugin#55 in place so an agent can pick it up cold: four changes, a file-by-file list at 0.7.3 line numbers, and acceptance criteria.
- Filed #33 (`mw post` ignores the config key `warn`) and #34 (prose highlight pairs across a soft line break in-process and not in `mw pre`), both found by the spec review.
- Added the Goals shape to the CLAUDE.md Plan & Progress Tracking entry.

## Spec Decisions

- A sentence starting `Planned (ITEM):` is behavior a named Roadmap Upcoming item will build; it loses the prefix when the item ships. The four containers fix-cycle rules carry it, each with a sentence on what happens today.
- A sentence starting `Known gap:` marks where the code or the docs fall short of the entry, with the Upcoming item or issue that covers it.
- `Unreleased` in the status table means built and passing `just check`, not yet in a tagged release. Everything from #16, #20, #29, and #30 is Unreleased until 0.4.0.
- The Invariant on inline `style` and event handlers now covers markwright's own extensions; the ported embeds keep theirs for `do-markdownit` parity (Mason's call).
- Upcoming gains five items: #31, #34, #33, a docs catch-up (docs-only, its own item by Mason's call, no issue yet), and the 0.4.0 release, done by hand outside the bpe loop.
- Component boundaries and Success criteria were corrected where the review found them stale (`_html.matching_end` has one caller; `config` also depends on `_diagnostics`).

## Prompt Inventory

| Prompt/Command | Action Taken | Outcome |
|---|---|---|
| "isn't our spec supposed to be a living document about what's present, planned, and deferred?" | Read the spec's history commit by commit | Goals never held a per-feature description |
| "why this happened, when it happened, and if this is an error in our plugin" | Read the plugin text at each release | A design gap since 0.7.0; filed plugin issue #55 |
| "spin up a subagent and review all this ... Also spin up a subagent to review the spec.md" | Two background reviewers; verified their citations | Root cause confirmed with four added causes; spec verdict "yes, with fixes" |
| AskUserQuestion answers | Filed #33 and #34, put their numbers in the spec, committed | This commit |

## Efficiency Insights

**What went well:**
- The spec was assembled by a script from a separate Goals file, so each review fix was one exact-once replacement and a rebuild, and the diff stayed reviewable.
- The second reviewer ran the sentences instead of reading them, which is how the two defects surfaced.

**What could improve:**
- The first plugin issue went up before anyone checked it; the review found errors in its timeline and in two claims about `/bpe:retrofit`.
- The first Goals draft wrote fix-cycle rules in the present tense, and they read as shipped.

**Course corrections:**
- The first analysis proposed banning phase-named Goals subsections. The review showed `/bpe:plan` finds its work through that block, so the ban needs a plan-side handle; the `Planned (ITEM):` prefix is that handle.

## Process Improvements

- Run every behavior sentence in a spec against the tool before committing it.
- Have an independent reviewer check an issue's facts before it is filed on a public repo.

## Observations

- `spec.md` grew from 205 to 389 lines (26 KB to 45 KB). Every agent that opens the whole file pays for that; bpe has no size rule yet, and plugin issue #55 asks for one.
- Starting context still says 0.3.0 is shipping. bpe keeps that section verbatim, so it stays until a brainstorm refreshes it.
- `pyproject.toml` and `uv.lock` are outside the `paths:` fence, so the 0.4.0 release cannot run through the bpe loop; the Upcoming item says so.
- Issues #16, #20, #29, and #30 stay open until the 0.4.0 release.
- The GitHub repository description still reads "Port of DigitalOcean Markdown to Python"; Mason has not said whether to change it.

## Suggested Skills for Next Session

- `bpe:plan`: plan the containers fix cycle from the `Planned (containers fixes)` sentences under Goals.
- `python:python`: the fix cycle changes `_containers.py` and `grid.py`.
