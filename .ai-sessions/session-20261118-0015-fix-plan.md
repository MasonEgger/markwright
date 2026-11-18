# Session Summary: Write the 0.4.0 Fix Plan

**Date**: 2026-11-18
**Duration**: about 45 minutes
**Conversation Turns**: 4
**Estimated Cost**: not measured
**Model**: Claude Fable 5 (claude-fable-5-2)

## Key Actions

- Ran `/bpe:plan` against `spec.md` and wrote `plan.md` and `todo.md` at the repo root: 29 steps in 12 sections, in the build order of Roadmap Upcoming.
- Took every step from a `Planned (ITEM):` sentence under Goals. Each step's documentation sub-step names the sentence it clears, the `Today` sentence it deletes, and the Feature Status cell it updates.
- Declared the validator tooling per section: `python:python` for the ten code sections, `content-design:review-content` for docs catch-up and the Material mapping page, and `**Tools:** none` for the one-line priority change in Section 1.
- Skipped the plan skill's external tool discovery (Pass 2). The spec's Available tooling already covers a Python-Markdown library, and no candidates were cached to `spec.md`.
- Stopped the first `/bpe:plan` run because the session was on Opus and `~/.claude/bpe.local.md` pins `plan` to Fable; Mason switched models and ran it again.
- Added the active plan to the Plan & Progress Tracking list in `CLAUDE.md`.

## Prompt Inventory

| Prompt/Command | Action Taken | Outcome |
|---|---|---|
| `/bpe:plan` (on Opus) | Model profile check failed; asked which model to use | "Switch to Fable first" |
| `/model` (three ids), "Ok, is fable selected" | Confirmed the session model | Fable 5 selected |
| `/bpe:plan` (on Fable) | Read `spec.md`, confirmed file names, wrote the plan | `plan.md`, `todo.md` |
| "Do what we need to do to run goal" | Committed the plan, pushed, ran the `/bpe:goal` pre-flight, wrote `goal.md` | This commit; `goal.md` (gitignored) |

## Efficiency Insights

**What went well:**
- The `Planned (ITEM):` convention made the plan a lookup: one grep per Upcoming item gave the step's behavior, and the `Today` sentence beside it gave the failing test.
- File names in the steps were checked against `src/markwright/`, `tests/`, and `docs/` before the plan was written, so no step names a file that does not exist.

**What could improve:**
- The profile pins `claude-fable-5-1` and the session id is `claude-fable-5-2`, so the mismatch note fires on every plan run even when the family is right.

## Process Improvements

- Pin the model family in `~/.claude/bpe.local.md`, or update the pin when the id moves.

## Observations

- No step edits `pyproject.toml` or `uv.lock`, and no step builds a Deferred item. The 0.4.0 release stays a by-hand job after the merge.
- Step 13 owes Step 28 a CHANGELOG line for the highlight pairs that stop highlighting under the same-line rule.
- The block bodies rule (Step 8), the front matter pass-through, and the HTML comment region (Step 25) are designs without a prototype. Expect those steps to need the fix loop.
- `pytest` is not on PATH in this checkout, so `goal.md` names `uv run pytest -q` as the verification command.

## Suggested Skills for Next Session

- `python:python`: Steps 1 through 25 change code under `src/markwright/` and `tests/`.
- `content-design:review-content`: Steps 26 through 29 are docs.
