# Lessons Learned

## Recent
<!-- 10 most recent lessons, newest first -->
- An "A render equals B render" equivalence test can pass vacuously when both sides degrade identically (mis-placed fence directives rendered as inert prose in both paths); pair it with a presence-assertion test confirming each feature actually appears in the output. When only inter-block whitespace differs, normalize by collapsing blank lines *outside* `<pre>` (stash pre blocks first) so significant code-block whitespace is preserved (2026-06-28)
- When a REFACTOR prompt says "factor stdin/stdout helpers" but the project bans trivial stdlib wrappers, factor only the non-trivial shared logic (e.g. a `_resolve_selection` that calls `select_extensions` and prints the `ValueError` to stderr, returning `None` to signal exit 2) and leave `sys.stdin.read()`/`sys.stdout.write()` inline (2026-06-28)
- Give an argparse-based `main(argv) -> int` a testable exit-code contract by wrapping `parser.parse_args` in `try/except SystemExit` and returning `exit_error.code`; this captures both the `action="version"` exit (0) and invalid-choice usage errors (2) without letting `SystemExit` escape to `capsys`-driven tests (2026-06-28)
- mypy strict rejects indexing a `TypedDict` with a runtime/variable key (`spec[stage_key]` raises `literal-required`); to iterate over fields generically, pass literal-key accessor callables (`lambda spec: spec["pre"]`) instead of string key names (2026-06-28)
- Keep a registry-facing stage function at a fixed signature (`apply_html(html, warnings=None)`) and route the in-process processor through the same private core (`_apply_marker(..., label_class, secondary_label_class)`) so configurable in-process options survive without giving the pure function config parameters (2026-06-28)
- Script-embed postprocessors can drop the `found` flag and detect their class signature in the rendered HTML instead: the raw-HTML restore postprocessor (priority 30) runs before script injection (priority 15), so the stashed embed HTML is already in the text; `SIGNATURE in html and SCRIPT not in html` makes injection idempotent and shares one path with the `mw post` CLI stage (2026-06-28)
- Design diagnostics around locally observable state: a post-only filter cannot detect what an upstream stage stripped (a removed HTML comment leaves no trace), so `mw --warn` reports only the malformed or unsupported markers it can actually see (2026-06-27)
- Commit the spec/plan/todo artifacts before `/bpe:goal`; it refuses on a dirty tree and on a non-gitignored `goal.md`, and a clean tree keeps the run's "git status empty" completion condition valid (2026-06-27)
- When renaming a project, check whether the old name is a substring of a name you must keep (`do-markdown` is inside the upstream `do-markdownit`); use a negative-lookahead replace `do-markdown(?!it)` so the attribution is not corrupted (2026-06-27)
- Embed extensions that emit raw HTML must stash it via `self.md.htmlStash.store(...)`; returning raw HTML as preprocessor text lets Markdown keep parsing it (JS backticks became a `<code>` span and broke the image-compare slider; block elements got an invalid `<p>` wrap) (2026-06-27)

## CLI
- When a REFACTOR prompt says "factor stdin/stdout helpers" but the project bans trivial stdlib wrappers, factor only the non-trivial shared logic (e.g. a `_resolve_selection` that calls `select_extensions` and prints the `ValueError` to stderr, returning `None` to signal exit 2) and leave `sys.stdin.read()`/`sys.stdout.write()` inline (2026-06-28)
- Give an argparse-based `main(argv) -> int` a testable exit-code contract by wrapping `parser.parse_args` in `try/except SystemExit` and returning `exit_error.code`; this captures both the `action="version"` exit (0) and invalid-choice usage errors (2) without letting `SystemExit` escape to `capsys`-driven tests (2026-06-28)

## Testing
- An "A render equals B render" equivalence test can pass vacuously when both sides degrade identically; pair it with a presence-assertion test confirming each feature actually lands in the output. When only inter-block whitespace differs, normalize by collapsing blank lines outside `<pre>` (stash pre blocks first) to keep significant code-block whitespace intact (2026-06-28)
- A test can pass while the bug is live if it only asserts substrings that survive the corruption; write the RED assertion against the actual broken output (no `<code>`, no `<p><tag>`) (2026-06-27)
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
- Keep a registry-facing stage function at a fixed signature (`apply_html(html, warnings=None)`) and route the in-process processor through the same private core (`_apply_marker(..., label_class, secondary_label_class)`) so configurable in-process options survive without giving the pure function config parameters (2026-06-28)
- Script-embed postprocessors can detect their class signature in the rendered HTML instead of carrying a preprocessor `found` flag: raw-HTML restore (priority 30) runs before script injection (priority 15), so the stashed embed HTML is already present; `SIGNATURE in html and SCRIPT not in html` makes the inject idempotent and shares one code path with the CLI post stage (2026-06-28)
- Extensions that emit raw HTML from a preprocessor must stash it via `self.md.htmlStash.store(html)`; otherwise Markdown keeps parsing the output (JS backticks become `<code>`, block elements get an invalid `<p>` wrap) (2026-06-27)
- Diagnose render bugs by converting the failing case through the real extension stack and reading the HTML; that separates markdown-output bugs from theme CSS (2026-06-27)
