# Plan: mw pre Skips Directives Inside Fenced Code (Issue #20)

`mw pre` expands standalone directive lines even when they sit inside a fenced code block, while the in-process render leaves them alone (the directive preprocessors run at priority 20, after `pymdownx.superfences` has stashed the fence).
So `mw pre | <renderer> | mw post` and the in-process render disagree on the same document.

Ten pre stages expand a directive line without consulting the fence scanner: the six embeds (`youtube`, `slideshow`, `image_compare`, `codepen`, `twitter`, `instagram`) and the four 0.4.0 directive stages (`button`, `lightbox`, `grid`, `annotate`).
`mermaid`, `fence`, `highlight`, and `icons` already scan through `_fences.py`.
The fix adds one fence-aware line mapper to `_fences.py` (the line-level twin of `map_prose`), moves the ten stages onto it, and extends the round-trip grammar so the parity net covers a directive placed inside a fence.

This is a correctness fix toward parity, not a divergence: `mw pre` is made to match the in-process reference. No dependency changes; every change is inside `src/markwright/**`, `tests/**`, and `CHANGELOG.md`, all within the spec's `paths:` fence. The version bump stays Mason's release step.

## Current Status

- [ ] Section 1: The fence-aware line mapper (Step 1)
- [ ] Section 2: Directive stages onto the mapper (Steps 2-3)
- [ ] Section 3: Cross-tool parity net and release note (Step 4)

## Ordering and Dependencies

- Section 1 lands `_fences.map_lines`, the only place a bug can hide (fence detection, indentation, one-to-many expansion). Everything else builds on it.
- Section 2 moves the ten directive stages onto the mapper, simplest first: Step 2 the eight one-to-one stages (a single call-site swap each), Step 3 the two one-to-many stages (`grid`, `annotate`), whose `_expand_lines` becomes a per-line transform. Each step adds a directive-in-fence regression test to the stage's own test file.
- Section 3 extends the round-trip hypothesis grammar so a directive can land inside a fence, proving `mw pre | stub | mw post` equals the in-process render for that case, and records the fix in the CHANGELOG.

## Why a line mapper, not `map_prose`

`map_prose` transforms multi-line prose runs between code and skips inline code spans mid-line; directive matching is line-anchored (`^\[button ...\]$`).
A line-level mapper that skips the lines inside each fenced block is the exact shape the ten stages need, and it reuses `find_fenced_blocks`, so an unclosed fence (not code) is still expanded and an indented in-list fence is still skipped, with no new fence logic.

---

## Section 1: The fence-aware line mapper

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: none

### Step 1: `_fences.map_lines`

**NOTE**: The line-level twin of `map_prose`, in the same module. `transform` returns the replacement lines for one source line: a single-element list for a one-to-one rewrite, several lines for a directive that expands to a marker plus a blank line, or the line itself to leave it unchanged. Lines inside a fenced block (per `find_fenced_blocks`) always pass through. Reuse `find_fenced_blocks`; add no new fence logic.

```text
1. RED: Write mapper tests first:
   - Create tests/test_fences_map_lines.py (import map_lines from markwright._fences):
     - Test a one-to-one transform (lambda line: [line.upper()]) uppercases a plain line: map_lines("hello", ...) == "HELLO".
     - Test a fenced block is skipped: map_lines("before\n```\ncode\n```\nafter", lambda line: [line.upper()]) == "BEFORE\n```\ncode\n```\nAFTER".
     - Test a one-to-many transform expands only outside a fence: with transform returning ["X", ""] for a line equal to "hit" and [line] otherwise, map_lines("hit\n```\nhit\n```") == "X\n\n```\nhit\n```".
     - Test an indented in-list fence is skipped: map_lines("- item\n\n    ```\n    hit\n    ```", lambda line: ["X"] if line.strip() == "hit" else [line]) keeps "    hit" unchanged (find_fenced_blocks recognizes the in-list fence via _fence_can_open).
     - Test an unclosed fence is NOT code, so a following line IS transformed: map_lines("```\nhit", lambda line: ["X"] if line.strip() == "hit" else [line]) == "```\nX".
   - Confirm these fail (symbol absent).

2. GREEN: Implement the mapper:
   - In src/markwright/_fences.py, add map_lines(text: str, transform: Callable[[str], list[str]]) -> str: split into lines, build the fenced-line index set from find_fenced_blocks exactly as map_prose does, then for each enumerated line output.extend([line]) when its index is fenced else output.extend(transform(line)); return "\n".join(output).
   - Keep it beside map_prose; Callable is already imported.

3. REFACTOR: none expected; the mapper is self-contained. Confirm map_prose and its tests are untouched.

4. Verify tests/test_fences_map_prose.py and tests/test_fences_map_lines.py pass.

5. Run `just check` and confirm green.
```

---

## Section 2: Directive stages onto the mapper

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: none

### Step 2: The eight one-to-one directive stages

**NOTE**: Each of youtube, slideshow, image_compare, codepen, twitter, instagram, button, lightbox ends `expand_source` with `"\n".join(_render_match(line) or line for line in text.split("\n"))` (the four embeds that take a load mode call `_render_match(line, load)`). The swap is to `map_lines(text, lambda line: [_render_match(line) or line])`, capturing `load` in the closure where present. No existing test should assert a directive expanding inside a fence; if one does, it encoded the bug, so fix the stage and correct that test, do not keep the buggy assertion.

```text
1. RED: Add one directive-in-fence regression test to each stage's existing test file:
   - tests/test_youtube.py: expand_source("```\n[youtube dQw4w9WgXcQ]\n```") == "```\n[youtube dQw4w9WgXcQ]\n```" (call with no options, eager default).
   - tests/test_slideshow.py: a [slideshow ...] line inside a ```...``` fence is returned unchanged by expand_source.
   - tests/test_image_compare.py: an [image_compare ...] line inside a fence is unchanged.
   - tests/test_codepen.py, tests/test_twitter.py, tests/test_instagram.py: the stage's directive inside a fence is unchanged by expand_source called with no options.
   - tests/test_button.py: expand_source("```\n[button /start Go]\n```") == "```\n[button /start Go]\n```".
   - tests/test_lightbox.py: expand_source("```\n[lightbox /a.png Alt]\n```") == "```\n[lightbox /a.png Alt]\n```".
   - Use a real directive each stage recognizes so the test proves fence-skipping, not a parse miss. Confirm each fails (the current stage expands inside the fence).

2. GREEN: Move each stage onto map_lines:
   - In each of src/markwright/{youtube,codepen,twitter,instagram}.py, replace the expand_source return with `return map_lines(text, lambda line: [_render_match(line, load) or line])` (load already resolved above in the function).
   - In each of src/markwright/{slideshow,image_compare,button,lightbox}.py, replace with `return map_lines(text, lambda line: [_render_match(line) or line])`.
   - Add `from markwright._fences import map_lines` to each module (keep import order).

3. Verify every existing test in the eight stage suites still passes (behavior outside fences is unchanged), plus the eight new assertions. If a pre-existing test asserted expansion inside a fence, correct it to the fixed behavior and note it in the commit.

4. Run `just check` and confirm green.
```

### Step 3: `grid` and `annotate` (one-to-many)

**NOTE**: These expand one directive line into a marker line plus a blank line via `_expand_lines(lines) -> list[str]`. Convert each module's `_expand_lines` into a per-line `_transform_line(line) -> list[str]` (returns `[f"{indent}{marker}", ""]` for a match, else `[line]`) and call it through `map_lines`, so a `[grid]`/`[annotate]` inside a fence is left literal. The marker payload, indentation, and the trailing blank line stay identical outside fences; the existing grid and annotate suites are the guard.

```text
1. RED: Add a directive-in-fence regression test to each module's test file:
   - tests/test_grid.py: expand_source("```\n[grid cards]\n- a\n```") == "```\n[grid cards]\n- a\n```" (the marker is not emitted inside the fence); also a plain [grid] inside a fence is unchanged.
   - tests/test_annotate.py: expand_source("```\n[annotate]\nText (1)\n```") == "```\n[annotate]\nText (1)\n```".
   - Confirm both fail (the current stage emits a marker inside the fence).

2. GREEN: Move grid and annotate onto map_lines:
   - In src/markwright/grid.py, replace _expand_lines with _transform_line(line: str) -> list[str]: GRID_RE.match(line.strip()); on no match return [line]; else compute indent and payload exactly as now and return [f"{indent}{encode_marker(MARKER_NAME, payload)}", ""]. Change expand_source to `return map_lines(text, _transform_line)`.
   - In src/markwright/annotate.py, replace _expand_lines with _transform_line(line: str) -> list[str]: ANNOTATE_RE.match(line.strip()); on no match return [line]; else return [f"{indent}{encode_marker(MARKER_NAME, {})}", ""]. Change expand_source to `return map_lines(text, _transform_line)`.
   - Add `from markwright._fences import map_lines` to both modules. Delete the old _expand_lines definitions and their now-unused local list accumulation.

3. Verify the full tests/test_grid.py and tests/test_annotate.py suites pass unchanged (outside-fence behavior identical), plus the two new assertions.

4. Run `just check` and confirm green.
```

---

## Section 3: Cross-tool parity net and release note

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: none

### Step 4: Round-trip grammar coverage and the CHANGELOG entry

**NOTE**: The round-trip test's hypothesis grammar never placed a directive inside a fence, which is why the parity property missed this bug. Extend the grammar so it can, then the property (`run_post(stub_render(run_pre(doc)))` equals the in-process render) guards the fix: the in-process render never expands inside a fence, and now `mw pre` does not either. Add one explicit fixture test too, so a reader sees the case without reading the grammar.

```text
1. RED/extend: Round-trip parity (tests/test_roundtrip.py):
   - Add a composite strategy _directive_in_fence that draws one directive line from a small set (a [button ...], a [lightbox ...], a [youtube ...], a [grid], an [annotate]) and wraps it in a ```...``` fence, producing a fenced block whose body is that directive line.
   - Add _directive_in_fence to the st.one_of block-sampler so a generated document can contain a fenced directive.
   - Add an explicit TestRoundTripFencedDirective test with a fixed document that fences each of the five directive forms: assert run_pre(doc) leaves every directive literal inside its fence (no "<a class=\"mw-button\"", no "mw-grid" marker comment, no "<pre class=\"mermaid\"" from these lines), and assert run_post(stub_render(run_pre(doc))) equals the in-process render of doc.
   - Confirm the explicit test fails before the Section 2 and 3 code is in place if run in isolation; run after Steps 1-3 it passes.

2. GREEN: no source changes expected (the fix landed in Steps 1-3). If a hypothesis example fails, fix the responsible stage, not the test.

3. Document: add the Fixed entry to CHANGELOG.md:
   - Under the existing "## [Unreleased]" heading, add a "### Fixed" subsection (before "### Added" or after it, matching Keep a Changelog ordering): "mw pre no longer expands directive lines inside fenced code blocks: the six embeds, button, lightbox, grid, and annotate now leave a directive literal inside a fence, matching the in-process render (#20)."
   - One sentence per line, straight quotes, no em-dashes, no banned vocabulary.

4. Verify:
   - `just check` green.
   - `just test-integration` green (the pre stage is renderer-agnostic; confirm nothing regressed).

5. Run `just check` and `just test-integration`; confirm both green.
```

---

## Implementation Guidelines

- TDD: RED (failing test) then GREEN (minimal code) then REFACTOR, per the `python:python` skill. `just check` must pass before a step is considered complete.
- Every source file keeps its 2-line `# ABOUTME:` header and `from __future__ import annotations`, RST docstrings, descriptive names (never single letters), and frozen pydantic models, per CLAUDE.md.
- The fix is toward parity: `mw pre` is made to match the in-process reference, which never expands a directive inside a fenced block. Do not change any outside-fence behavior; the existing stage suites are the guard.
- Test the project's own logic only: `map_lines` directly, each stage's `expand_source` directly, and the round-trip property. Do not test Python-Markdown, pymdownx, or Pygments.
- No dependency changes (`deps: frozen`). No version bump; the 0.4.0 bump is Mason's release step and the CHANGELOG entry sits under `## [Unreleased]`.
- Never commit to `main`; the work is on a feature branch, one PR, merged by Mason.

## Success Metrics

- `just check` green: ruff, ruff format, mypy strict, pytest, coverage reported (test or delete every uncovered line).
- `just test-integration` green: the `mw pre | hugo | mw post` pipeline and the clean-venv wheel install unaffected.
- `mw pre` leaves every directive (the six embeds, button, lightbox, grid, annotate) literal inside a fenced code block, and the round-trip property holds for a document with a fenced directive.
- `CHANGELOG.md` records the fix under `## [Unreleased]` with the issue reference; no existing extension's outside-fence output changed.
