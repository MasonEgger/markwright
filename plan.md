# Implementation Plan: markwright Pipeline CLI (`mw`)

This plan turns `spec.md` into TDD-sized steps. The strategy from the spec: refactor each extension into pure stage functions (`expand_source(text) -> text`, `apply_html(html) -> html`), make the existing Python-Markdown `Extension`/processor classes thin adapters over those functions so every current test stays green, then build a stage registry and the `mw` CLI on top of the same functions.

## Current Status

- [x] Step 1: Simple embed stage functions (youtube, slideshow, image_compare)
- [x] Step 2: Script embed stage functions (codepen, twitter, instagram)
- [x] Step 3: Fence stage functions, `mw-fence` marker, version validation
- [x] Step 4: Highlight stage functions
- [ ] Step 5: Stage registry and selection
- [ ] Step 6: CLI skeleton, `list`, `--version`, entry point
- [ ] Step 7: CLI `post` subcommand (+ `--use`/`--exclude`/`--warn`)
- [x] Step 8: CLI `pre` subcommand
- [x] Step 9: CLI `render` subcommand
- [x] Step 10: Cross-stage round-trip integration tests
- [ ] Step 11: Docs (CLI reference, pipeline guide, renderer contract)
- [ ] Step 12: Packaging smoke test

Status: not started.

## Architecture Decisions

- **Pure stage functions live in each extension module.** `expand_source(text: str) -> str` is the source-stage (`mw pre`) transform; `apply_html(html: str, warnings: list[str] | None = None) -> str` is the HTML-stage (`mw post`) transform. Only fence uses the `warnings` argument; the others accept and ignore it so the registry can call every post function with one signature.
- **One shared per-match builder per embed.** A module-level `_render_match(line: str) -> str | None` returns the raw HTML for a matching standalone line or `None`. Both `expand_source` (inline text, for the CLI) and the existing Preprocessor (which still stashes via `self.md.htmlStash.store(...)`, for the in-process path) go through it. This keeps the htmlStash fix intact and avoids duplicating the regex and HTML builders.
- **Script injection unifies on signature detection.** The post-stage `apply_html` scans for the embed's class signature and appends the script tag once, only if no matching script tag is already present (idempotent). The in-process Postprocessor delegates to the same `apply_html`, replacing the `found`-flag path. Existing "inject once" and "no script without embed" tests stay green.
- **Highlight keeps its in-process InlineProcessor.** Prose highlighting during an in-process render still runs through the InlineProcessor. `expand_source` is new logic (prose-only, code-region-aware) used only by `mw pre`. `apply_html` is the current Postprocessor logic extracted into a pure function.
- **The `mw-fence` marker is the only cross-tool contract.** `expand_source` emits `<!-- mw-fence:{JSON} -->` with `"version": 1`; `apply_html` validates it (skip + optional warning on malformed JSON, unsupported version, or no adjacent code block). This replaces the current internal `do-fence` comment.
- **Registry composes by priority.** `src/markwright/registry.py` maps name to `{pre, post, pre_priority, post_priority}`. `pre` runs selected pre functions high-to-low priority; `post` runs selected post functions high-to-low. Priorities mirror the in-process processor priorities (fence pre 40, embeds 20, highlight pre 10; fence and highlight post 25, script injection 15).
- **CLI is stdlib `argparse`.** `src/markwright/cli.py` exposes `main(argv: list[str] | None = None) -> int`. Subcommands read stdin and write stdout. Entry point `mw = "markwright.cli:main"`.

## Steps

### Step 1: Simple Embed Stage Functions

**NOTE**: youtube, slideshow, and image_compare have a pre stage only (no post). Each already has a module-level HTML builder (`_build_*` or inline in `run`) and a compiled regex. The current Preprocessor stashes the built HTML. Preserve that; add the pure path beside it.

```text
1. RED: Add stage-function tests. Do NOT modify existing test classes.
   - In tests/test_youtube.py add class TestYouTubeExpandSource:
     - Test expand_source("[youtube dQw4w9WgXcQ]") returns a string containing '<iframe' and 'youtube.com/embed/dQw4w9WgXcQ' and contains no Python-Markdown stash placeholder (assert '\x02' not in result)
     - Test a line that is not exactly an embed ("text [youtube abc] text") is returned unchanged
     - Test multi-line input expands only the standalone embed line and leaves other lines byte-for-byte unchanged
     - Test input with no embed passes through unchanged
   - In tests/test_slideshow.py add class TestSlideshowExpandSource (syntax "[slideshow https://a.jpg https://b.jpg]", expect '<div class="slideshow"')
   - In tests/test_image_compare.py add class TestImageCompareExpandSource (syntax "[compare https://a.jpg https://b.jpg]", expect '<div class="image-compare"')

2. GREEN: Add the pure functions, minimal.
   - In src/markwright/youtube.py:
     - Add `_render_match(line: str) -> str | None`: strip the line, match YOUTUBE_RE; on match build and return the iframe HTML (move the body of the current run() match branch into here); else return None.
     - Add `expand_source(text: str) -> str`: split text on "\n", replace each line with `_render_match(line) or line`, join on "\n".
     - Refactor YouTubePreprocessor.run to call `_render_match`: for each line, if it returns HTML, append `self.md.htmlStash.store(html)`, else append the line. Behavior is unchanged.
   - Repeat the same three additions in src/markwright/slideshow.py and src/markwright/image_compare.py, reusing their existing builders and regexes. For slideshow keep the "fewer than 2 URLs -> no match" rule inside `_render_match`.

3. REFACTOR: Confirm expand_source and the Preprocessor share `_render_match` with no duplicated regex or builder logic.

4. Verify the existing in-process tests for all three modules still pass, then run `just check`.
```

### Step 2: Script Embed Stage Functions

**NOTE**: codepen, twitter, and instagram have a pre stage (expand) and a post stage (inject one `<script>`). Today the Preprocessor sets a `found` flag and the Postprocessor appends the script if `found`. Replace the post path with signature detection so the same `apply_html` serves the CLI and the in-process render.

```text
1. RED: Add stage-function tests. Do NOT modify existing test classes.
   - In tests/test_codepen.py add class TestCodePenStageFunctions:
     - Test expand_source("[codepen MattCowley vwPzeX]") returns text containing 'class="codepen"' and 'data-slug-hash="vwPzeX"', no stash placeholder
     - Test apply_html on HTML that contains 'class="codepen"' appends exactly one '<script ... ei.js ...>' (assert result.count("ei.js") == 1)
     - Test apply_html is idempotent: apply_html(apply_html(html)) still contains the script exactly once
     - Test apply_html on HTML with no codepen signature appends no script (assert "ei.js" not in result)
     - Test apply_html accepts a warnings list argument and leaves it empty (signature injection never warns)
   - Add the analogous class to tests/test_twitter.py (signature 'class="twitter-tweet"', script 'widgets.js') and tests/test_instagram.py (signature 'class="instagram-media"', script 'embed.js').

2. GREEN: Add the pure functions and rewire the adapters.
   - In src/markwright/codepen.py:
     - Add `_render_match(line) -> str | None` (move the run() match-branch body here, reusing _parse_flags and CODEPEN_RE).
     - Add `expand_source(text: str) -> str` (split/replace/join via _render_match).
     - Add `apply_html(html: str, warnings: list[str] | None = None) -> str`: if the codepen class signature is present AND the script src is not already in html, return html + "\n" + CODEPEN_SCRIPT; otherwise return html unchanged.
     - Refactor CodePenPreprocessor.run to use `_render_match` + `self.md.htmlStash.store(...)`.
     - Refactor CodePenPostprocessor.run to `return apply_html(text)`. Remove the dependency on the preprocessor `found` flag (delete the field and its references only if nothing else uses them).
   - Repeat for src/markwright/twitter.py and src/markwright/instagram.py.

3. REFACTOR: Ensure each module has a single signature constant and script constant used by both apply_html and any test.

4. Verify the existing script-injection tests (inject once for multiple embeds, no script without embed, not-matched-inside-fence) still pass, then run `just check`.
```

### Step 3: Fence Stage Functions, `mw-fence` Marker, Version Validation

**NOTE**: fence.py currently emits an internal `<!-- do-fence:{JSON} -->` comment in the Preprocessor and reads it in the Postprocessor (COMMENT_RE). This step renames it to `mw-fence`, adds `"version": 1`, extracts the pure functions, and adds read-side validation with `--warn`-collectable messages.

```text
1. RED: Add stage-function and validation tests in tests/test_fence.py. Do NOT modify existing classes.
   - Add class TestFenceExpandSource:
     - Test expand_source on a fence with "[label deploy.sh]" emits a line '<!-- mw-fence:' and the JSON payload contains '"version": 1' and '"label": "deploy.sh"', and the directive line "[label deploy.sh]" is removed while the code lines and the fence markers remain
     - Test a command fence emits '"prefix_type": "command"' and '"prefix_value": "$"'
     - Test a plain fence with no directives emits no mw-fence comment and is unchanged
   - Add class TestFenceApplyHtml:
     - Test apply_html on rendered HTML that contains an mw-fence(label) comment immediately before a <pre><code> block injects the label div and removes the comment
     - Test a command-prefix marker produces <ol><li data-prefix="$"> wrapping
     - Test apply_html(html, warnings) appends a warning and skips styling when the marker JSON is malformed (e.g. "<!-- mw-fence:{not json -->")
     - Test apply_html(html, warnings) appends a warning and skips styling when "version" is an unsupported value (e.g. 999)
     - Test apply_html(html, warnings) appends a warning when a well-formed marker has no following code block
     - Test apply_html(html) with warnings=None on those same malformed inputs is a silent no-op (no exception, marker left or removed but no styling)

2. Document the marker contract:
   - In src/markwright/fence.py update the module docstring/comment to state the marker is `<!-- mw-fence:{JSON} -->` with the v1 schema from spec.md.

3. GREEN: Implement.
   - Change COMMENT_RE and the emitted comment to `mw-fence`. Add "version": 1 to the metadata dict before json.dumps.
   - Add `expand_source(text: str) -> str`: run the existing directive/flag extraction over the text and return text with the mw-fence comment inserted and directive lines removed (reuse the existing preprocessor scanning logic; operate on text split into lines).
   - Add `apply_html(html: str, warnings: list[str] | None = None) -> str`: the existing postprocessor transform, plus: wrap json.loads in a try/except (malformed -> if warnings is not None append a message, skip); check the parsed "version" == 1 (else warn + skip); if no <pre>/<code> follows the comment, warn + skip. Always remove the recognized comment.
   - Make FencePreprocessor.run and FencePostprocessor.run thin adapters that delegate to expand_source / apply_html (the preprocessor still returns lines; join, transform, split, or call the shared extraction helper directly).

4. REFACTOR: Ensure the marker name and v1 version are single named constants (e.g. MARKER_NAME = "mw-fence", MARKER_VERSION = 1) used by both functions.

5. Verify all existing fence tests pass (they assert final HTML, which is unchanged), then run `just check`.
```

### Step 4: Highlight Stage Functions

**NOTE**: highlight.py has an InlineProcessor (in-process prose) and a Postprocessor (escaped/code markers). Keep the InlineProcessor. Add a pure `apply_html` (extract the Postprocessor logic) and a new `expand_source` (prose-only, skips fenced and inline code regions).

```text
1. RED: Add tests in tests/test_highlight.py. Do NOT modify existing classes.
   - Add class TestHighlightApplyHtml:
     - Test apply_html("a &lt;^&gt;word&lt;^&gt; b") wraps the escaped run in <mark> (matches current postprocessor output)
     - Test apply_html leaves a backslash-escaped marker (\\&lt;^&gt;) as a literal &lt;^&gt; with no <mark>
   - Add class TestHighlightExpandSource:
     - Test expand_source("a <^>word<^> b") returns 'a <mark>word</mark> b'
     - Test a marker inside a fenced code block (```...<^>x<^>...```) is left untouched by expand_source (the post stage handles in-code)
     - Test a marker inside an inline code span (`<^>x<^>`) is left untouched
     - Test a backslash-escaped prose marker (\\<^>x\\<^>) is left as a literal <^> with no <mark>

2. GREEN: Implement.
   - Add `apply_html(html: str, warnings: list[str] | None = None) -> str` containing the current HighlightPostprocessor.run body (escaped-run wrapping + backslash reveal). Ignore the warnings argument.
   - Make HighlightPostprocessor.run delegate to apply_html.
   - Add `expand_source(text: str) -> str`: scan text, identify fenced (triple-backtick) and inline (single-backtick) code regions, and wrap `<^>...<^>` in <mark> only in the regions OUTSIDE code, honoring the backslash escape. Leave in-code markers for the post stage.

3. REFACTOR: Share the marker/backslash regexes between expand_source and apply_html where they overlap; keep the span-boundary-safe wrapper (_wrap_highlight_segments) used only by apply_html.

4. Verify existing highlight tests pass, then run `just check`.
```

### Step 5: Stage Registry and Selection

**NOTE**: First consumer-facing composition layer. No CLI yet; this is pure logic the CLI will call.

```text
1. RED: Create tests/test_registry.py:
   - Test select_extensions(use=[], exclude=[]) returns all 8 extension names
   - Test select_extensions(use=["youtube","highlight"], exclude=[]) returns exactly those two
   - Test select_extensions(use=[], exclude=["youtube"]) returns all names except youtube
   - Test select_extensions with an unknown name raises a ValueError naming the bad token
   - Test run_pre composes selected pre functions in priority order: given input with a [youtube ...] line and a <^>prose<^> marker, run_pre expands the embed and wraps the prose mark
   - Test run_post composes selected post functions: given HTML with a codepen signature and an escaped highlight marker, run_post injects the script once and wraps the mark
   - Test run_post(html, names, warnings) threads the warnings list into the fence post function (a malformed mw-fence marker yields a warning entry)
   - Test describe() returns, for each extension, its name and which stages (pre/post) it has

2. GREEN: Create src/markwright/registry.py:
   - Define EXTENSION_NAMES (the 8 names) and REGISTRY: dict[str, dict] mapping name -> {"pre": fn|None, "post": fn|None, "pre_priority": int, "post_priority": int}, importing expand_source/apply_html from each module. Priorities: fence pre 40; youtube/codepen/twitter/instagram/slideshow/image_compare pre 20; highlight pre 10. Post: fence 25, highlight 25, codepen/twitter/instagram 15; others None.
   - Implement select_extensions(use, exclude) -> list[str] with validation.
   - Implement run_pre(text, names) -> str: run each selected pre fn (skip None) over text in descending pre_priority order.
   - Implement run_post(html, names, warnings=None) -> str: run each selected post fn (skip None) over html in descending post_priority order, passing warnings.
   - Implement describe() -> list[tuple[str, list[str]]].

3. REFACTOR: Keep the registry declarative; no per-extension branching in run_pre/run_post.

4. Run `just check`.
```

### Step 6: CLI Skeleton, `list`, `--version`, Entry Point

```text
1. RED: Create tests/test_cli.py:
   - Test main(["--version"]) returns 0 and prints a version string containing the package version
   - Test main(["list"]) returns 0 and prints every extension name with its stages (assert "youtube" and "fence" appear, and that a pre-only and a pre+post extension are labeled differently)
   - Test main(["bogus"]) returns 2 (argparse usage error)
   - Drive main via capsys for stdout/stderr capture.

2. GREEN: Create src/markwright/cli.py:
   - main(argv: list[str] | None = None) -> int using argparse with subparsers: pre, post, render, list; plus a top-level --version action.
   - Implement only `list` (print registry.describe()) and `--version` (read importlib.metadata.version("markwright")) in this step. Leave pre/post/render parsers defined but their handlers raising NotImplementedError or returning a clear "not yet implemented" is NOT allowed; instead defer creating those handlers until their steps by registering the subparsers now and wiring handlers in Steps 7 to 9. For this step, register only list and version; add pre/post/render subparsers in their own steps.
   - Return argparse's exit code conventions (0 success, 2 usage).

3. Wire packaging:
   - In pyproject.toml add [project.scripts] with `mw = "markwright.cli:main"`.

4. REFACTOR: Factor a helper that builds the ArgumentParser so tests and main share it.

5. Run `just check`.
```

### Step 7: CLI `post` Subcommand

**NOTE**: post is the complete path on its own (highlight + fence + script injection). Build it first of the transform subcommands.

```text
1. RED: Add to tests/test_cli.py class TestCliPost:
   - Test main(["post"]) reads stdin and writes transformed HTML to stdout (feed HTML with a codepen signature; assert the script is injected once). Use monkeypatch to set sys.stdin to an io.StringIO and capture stdout.
   - Test --use selects a subset (post --use highlight on HTML with both a codepen signature and an escaped mark injects NO script but DOES wrap the mark)
   - Test --exclude removes an extension
   - Test --warn on HTML containing a malformed mw-fence marker writes a warning to stderr, leaves stdout's body unchanged, and returns 0
   - Test without --warn the same malformed input produces no stderr and returns 0
   - Test an unknown --use name returns 2 and writes an error to stderr

2. GREEN:
   - Add the `post` handler in cli.py: read sys.stdin (UTF-8), call registry.select_extensions(use, exclude) (translate ValueError to exit 2 + stderr), build warnings = [] if --warn else None, call registry.run_post(html, names, warnings), write stdout, then if warnings print each to stderr. Return 0.
   - Add --use (append), --exclude (append), --warn (store_true) to the post subparser.

3. REFACTOR: Factor stdin-read/stdout-write and selection-error handling into helpers reused by later subcommands.

4. Run `just check`.
```

### Step 8: CLI `pre` Subcommand

```text
1. RED: Add to tests/test_cli.py class TestCliPre:
   - Test main(["pre"]) expands a [youtube ...] line on stdin to iframe HTML on stdout
   - Test pre wraps a standalone prose <^>mark<^> via the highlight pre stage
   - Test pre on a fence with [label x] emits an mw-fence comment and keeps the fence
   - Test --use / --exclude select the active pre stages
   - Test an unknown --use name returns 2

2. GREEN:
   - Add the `pre` handler: read stdin, select_extensions, call registry.run_pre(text, names), write stdout, return 0. Reuse the helpers from Step 7. (`--warn` is not offered on pre.)
   - Add --use/--exclude to the pre subparser.

3. Run `just check`.
```

### Step 9: CLI `render` Subcommand

**NOTE**: render uses the existing in-process Python-Markdown path, mirroring the site stack so fence and highlight render correctly.

```text
1. RED: Add to tests/test_cli.py class TestCliRender:
   - Test main(["render"]) on stdin markdown containing a [youtube ...] line and a <^>mark<^> produces final HTML with the iframe and a <mark> (assert against the in-process markwright render of the same input)
   - Test render --use youtube only loads youtube (a fence directive is NOT styled)
   - Test an unknown --use name returns 2

2. GREEN:
   - Add the `render` handler: read stdin, select_extensions, build a markdown.Markdown with extensions ["pymdownx.superfences", "pymdownx.highlight"] (configured pygments_lang_class=True) plus "markwright.<name>" for each selected name, convert, write stdout, return 0.
   - Add --use/--exclude to the render subparser.

3. REFACTOR: Confirm all four subcommands share the parser-builder and IO helpers.

4. Run `just check`.
```

### Step 10: Cross-Stage Round-Trip Integration Tests

**NOTE**: This is the safety net that proves pre + an external render + post equals the in-process render, and that priority ordering is correct.

```text
1. RED: Create tests/test_roundtrip.py:
   - Define a stub_render(markdown_text) -> html that runs markdown.Markdown(extensions=["pymdownx.superfences","pymdownx.highlight"], extension_configs={"pymdownx.highlight":{"pygments_lang_class":True}}).convert (a generic renderer with raw-HTML and comment passthrough, NO markwright extensions).
   - For a fixture document exercising every feature (a labeled command fence, an environment fence, line numbers, a youtube embed, a codepen embed, prose <^>highlight<^>, and in-code <^>highlight<^>):
     - Test that run_post(stub_render(run_pre(doc, all)), all, None) equals the in-process markwright render of doc (the `mw render` path). Normalize only insignificant whitespace if necessary; prefer an exact match.
   - Test idempotency at the integration level: running post twice over the rendered output does not double-inject any script and does not change a second time.
   - Test graceful degradation: a renderer stub that strips HTML comments (post-process the stub output to delete <!-- ... -->) yields unstyled fences but raises no error and still injects embed scripts.

2. GREEN: Adjust stage-priority values or function internals only as needed to make the round-trip match. No new features.

3. REFACTOR: If the fixture reveals ordering coupling between fence and highlight post, encode the intended order explicitly in the registry priorities and note it.

4. Run `just check`.
```

### Step 11: Docs

```text
1. Write docs/cli.md:
   - Document `mw pre|post|render|list`, the flags (--use, --exclude, --warn, --version), stdin/stdout filter behavior, exit codes, and UTF-8.
   - Show the canonical pipeline: `mw pre < in.md | some-renderer | mw post > out.html`.
2. Write docs/pipeline.md (pipeline integration guide):
   - The pre/render/post model, when to run only post vs both stages, and worked Hugo and plain-Unix examples.
3. Write docs/renderer-requirements.md:
   - The three renderer requirements (raw-HTML passthrough, comment preservation, span-based highlighting), the `mw-fence` marker contract and v1 schema, and which features degrade if a requirement is unmet.
4. Update mkdocs.yml nav to add a "CLI" section with these three pages.
5. Use Title Case headings and the project writing style. Run `just docs-build` (strict) and confirm no warnings.
```

### Step 12: Packaging Smoke Test

```text
1. RED: Create tests/test_packaging.py:
   - Test that the installed console script runs: subprocess.run(["mw","--version"], capture_output=True, text=True) returns code 0 and stdout contains the version. (Mark or skip gracefully if the script is not on PATH in the test environment; prefer invoking via `python -m markwright.cli` as a fallback assertion of the same main.)
   - Test `mw list` over subprocess returns 0 and lists extensions.
2. GREEN: Ensure the [project.scripts] entry from Step 6 is correct; `uv sync` installs `mw`. Fix any entry-point wiring needed to make the smoke test pass.
3. Run `just check`.
```

## Implementation Guidelines

- Load the `python` skill before writing any code each step.
- Work strictly RED then GREEN then REFACTOR. Write the failing test first and watch it fail for the right reason before implementing.
- Do not modify existing per-extension test classes; they pin the in-process behavior the adapters must preserve. Add new classes alongside them.
- Keep adapters thin: a Preprocessor/Postprocessor body should be a delegation to the pure function (plus the htmlStash wrapping for embed pre), not a second implementation.
- Test only markwright logic: stage transforms, selection rules, warning conditions, CLI wiring, and the round-trip equivalence. Do not test Python-Markdown, argparse, or pygments behavior.
- `just check` (pytest with 100% coverage, ruff, mypy strict) must pass before a step is considered complete. `just docs-build` must pass after Step 11.
- Every source file keeps its `# ABOUTME:` header, `from __future__ import annotations`, full type hints (no `Any`), absolute imports, and RST docstrings.

## Success Metrics

- `mw pre | <renderer> | mw post` reproduces the in-process markwright render for the full-feature fixture (Step 10).
- `mw post` alone fully styles externally rendered HTML, including in-code highlights and one-time script injection.
- `--use` / `--exclude` select stages correctly; unknown names exit 2 with a stderr message.
- `--warn` reports malformed payloads, unsupported versions, and unmatched markers to stderr while leaving stdout and the exit code unchanged.
- The `mw-fence` v1 marker round-trips through a comment-preserving renderer and degrades to a silent no-op through a comment-stripping one.
- All existing extension tests stay green; coverage stays at 100%; mypy strict and ruff stay clean.
- The installed `mw` console script runs (Step 12).
