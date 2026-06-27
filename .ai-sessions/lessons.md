# Lessons Learned

## Recent
<!-- 10 most recent lessons, newest first -->
- For "no forbidden characters" audits, use a Python codepoint scan (`for c in line if c in '...'`), never a shell grep with a zsh `$'...'` Unicode pattern; the latter silently matched nothing and falsely passed an em-dash (2026-06-26)
- When writing prose that bears Mason's name, run the writing-style audit before claiming compliance, not after being asked; the global no-em-dash rule applies to CLAUDE.md and lessons too (2026-06-26)
- When a coverage gap points at one line, trace it to the exact code path before writing the test — `highlight.py:36` lived in the postprocessor's `_wrap_highlight_segments`, not the inline path that an existing empty-marker test already covered (2026-06-26)
- Adding a parallel code path for an existing behavior needs its own test even when an analogous test exists for the old path (2026-06-26)

## Testing
- When a coverage gap points at one line, trace it to the exact code path before writing the test — a same-looking input may exercise a different path (2026-06-26)
- Adding a parallel code path for an existing behavior needs its own test even when an analogous test exists for the old path (2026-06-26)

## Tooling
- `.coverage` is a tracked binary artifact in this repo that shows as modified after every test run; do not stage it (2026-06-26)
- For "no forbidden characters" audits, use a Python codepoint scan (`for c in line if c in '...'`), never a shell grep with a zsh `$'...'` Unicode pattern; the latter silently matched nothing and falsely passed an em-dash (2026-06-26)

## Documentation
- Mason's writing-style rules (no em/en-dashes, sentence-case headings, no banned vocab, straight quotes) apply to all prose including README, CLAUDE.md, docs, and lessons; audit before claiming compliance (2026-06-26)
- When porting `docs/index.md` content into a GitHub README, strip MkDocs `!!!` admonitions (they render as raw text on GitHub) and convert em-dashes (2026-06-26)
