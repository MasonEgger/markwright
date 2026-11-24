# Session Summary: Drop the Fringe Known Gaps From the Spec

**Date**: 2026-11-23
**Duration**: about 40 minutes
**Conversation Turns**: 2 user prompts
**Estimated Cost**: not tracked
**Model**: claude-fable-5-2

## Key Actions

- Triaged every `Known gap` sentence in `spec.md` for a polish session: which ones an ordinary author reaches, and which describe input nobody writes.
- An Opus research agent checked each construct against CommonMark, Python-Markdown with superfences, Goldmark, and markdown-it, and counted it in about 11,500 Markdown files from six docs repos (github/docs, vscode-docs, hugoDocs, mkdocs-material, pymdown-extensions, fastapi).
- `spec.md`: deleted 17 `Known gap` sentences and their three continuation lines, and added one rule under Goals: a gap is recorded only when a document an author is likely to write reaches it.
- `spec.md`: the Mermaid placement sentence loses its `Known gap` prefix, since top level only is the supported scope and not a shortfall.
- `spec.md`: the Deferred lines for parser hygiene and hardening no longer point at the deleted sentences; the hardening line now says the stage ends in a traceback today.
- `CLAUDE.md`: two pointers at the deleted sentences updated.
- `just check` passes (1162 tests). No code or docs page changed.

## Findings

- A fenced block behind a block quote marker is not fringe: github/docs has about 40, most of them under a `> [!NOTE]` alert, and Hugo renders that alert syntax. A `command` fence or a `[label]` there does nothing in either path today. Its gap sentence stays.
- A prefix flag followed by a highlighter attribute (`command title="x.sh"`, `command hl_lines="1"`) is dropped without a warning, because the info string is split on commas only. `command,bash hl_lines="1"` works. This is not in the spec yet.
- In a code block, `C:\Users\<^>sammy<^>\Documents` loses the backslash and shows both markers. `C:\Users<^>\sammy<^>` is the workaround.
- Nine `Known gap` sentences remain: six are polish candidates, and three wait for a decision (code behind a block quote marker, a fence on a list marker line, the backslash before a highlight).

## Prompt Inventory

| Prompt/Command | Action Taken | Outcome |
|---|---|---|
| "in the spec, what more do we need to do? I want to prep for a polish session" | Read the Roadmap and every gap, probed the common shapes in-process | Six polish candidates, one of them new |
| "spin up a subagent using Opus ... research them ... it may be worth just deleting entirely" | Research agent, spot-checks of its three surprising claims, then the spec edit | 17 gaps deleted, 4 held for a decision |

## Observations

- The corpus scan settled in minutes what the adversarial review could not: whether anyone writes the input.

## Suggested Skills for Next Session

- bpe:brainstorm (promote the polish items into Goals)
