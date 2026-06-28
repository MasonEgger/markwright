# Lessons Learned

## Recent
<!-- 10 most recent lessons, newest first -->
- When renaming a project, check whether the old name is a substring of a name you must keep (`do-markdown` is inside the upstream `do-markdownit`); use a negative-lookahead replace `do-markdown(?!it)` so the attribution is not corrupted (2026-06-27)
- Embed extensions that emit raw HTML must stash it via `self.md.htmlStash.store(...)`; returning raw HTML as preprocessor text lets Markdown keep parsing it (JS backticks became a `<code>` span and broke the image-compare slider; block elements got an invalid `<p>` wrap) (2026-06-27)
- Diagnose render bugs by converting the case through the real extension stack and reading the HTML; it splits markdown-output bugs from MkDocs/Material CSS with evidence (2026-06-27)
- A test can pass while the bug is live if it only asserts substrings that survive the corruption; write the RED assertion against the actual broken output (no `<code>`, no `<p><tag>`) (2026-06-27)
- A 3-backtick fence inside a 3-backtick code block closes it early; use a 4-backtick outer fence to show nested triple-backtick examples (2026-06-27)
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
- Mason's writing-style rules (no em/en-dashes, Title Case headings, no banned vocab, straight quotes) apply to all prose including README, CLAUDE.md, docs, and lessons; audit before claiming compliance (2026-06-27)
- When porting `docs/index.md` content into a GitHub README, strip MkDocs `!!!` admonitions (they render as raw text on GitHub) and convert em-dashes (2026-06-26)
- A 3-backtick fence inside a 3-backtick code block closes it early; use a 4-backtick outer fence to show nested triple-backtick examples (2026-06-27)

## Python-Markdown
- Extensions that emit raw HTML from a preprocessor must stash it via `self.md.htmlStash.store(html)`; otherwise Markdown keeps parsing the output (JS backticks become `<code>`, block elements get an invalid `<p>` wrap) (2026-06-27)
- Diagnose render bugs by converting the failing case through the real extension stack and reading the HTML; that separates markdown-output bugs from theme CSS (2026-06-27)
