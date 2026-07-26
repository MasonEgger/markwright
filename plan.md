# Remediation Plan: markwright step-55 Audit Fixes

This plan turns the remediation `spec.md` (R1 through R11, plus Decisions D1, D2, D3) into TDD-sized steps.
The build is complete; this cycle fixes the 12 defects step-55 confirmed and adds, to each, the regression test or probe that would have caught it.
The prior pipeline-CLI plan is preserved in git history (`git show main:plan.md`); this remediation plan replaces it at the repo root for the audit cycle, the same way the remediation spec replaced the design spec.

Every step is test-first, keeps `just check` green (100 percent line and branch coverage), and holds output to upstream `do-markdownit` parity unless a Decision documents a divergence.

## Current Status

- [ ] Step 1: R1 — close the stored XSS in the fence marker comment (High, release blocker)
- [ ] Step 2: R2 + R11 — packaging pass (runtime dep, publish metadata, clean-venv probe)
- [ ] Step 3: R3 — guard zero and negative dimensions in the youtube embed
- [ ] Step 4: R4 — unify the highlight regexes, tilde fences, and the literal-marker promise (D3 contingency)
- [ ] Step 5: R7a — normalize the Instagram permalink (firm half of R7)
- [ ] Step 6: R8 — match the compare SVG to upstream
- [ ] Step 7: R9 — match the slideshow nav JavaScript to upstream
- [ ] Step 8: R10 — fix the image_compare token in the README and docs
- [ ] Step 9: D1 + R5 — decide and land single-image slideshow parity
- [ ] Step 10: D2 + R6 + R7b — decide and land embed URL grammar parity

Status: not started.

## Ordering and Dependencies

- **R1 lands first.** It is the release blocker (stored XSS); nothing depends on it, but it ships ahead of everything else.
- **R2 and R11 are one packaging pass**, both verified from the built wheel in a clean venv (spec Component Boundaries).
- **Steps 1 through 8 are firm** ("change-code" or firm output/doc fixes) and proceed without any Decision.
- **Steps 9 and 10 are brainstorm-gated.** D1 gates R5; D2 gates R6 and R7's grammar half. Each gated step resolves its Decision via `/bpe:brainstorm` and records the outcome in the `spec.md` Decisions section **before** writing the branch-specific code.
- **D3 is folded into Step 4** as a contingency: the preferred resolution is to make the literal-marker promise true by unifying the regexes; D3 is only invoked if some path cannot deliver the literal marker under Python-Markdown.

## Architecture Notes

- **Two consumers, one set of pure stage functions** (`expand_source`, `apply_html`). Every fix lands in the shared stage function so the in-process render and the CLI stay in agreement; that shared path is exactly why several of these defects diverged across consumers (R4) and why each fix asserts on both.
- **The `mw-fence` marker is a private, versioned cross-tool contract**, not upstream output. R1 may re-encode the payload freely as long as `apply_html` reads it back and fail-soft / `--warn` behavior is preserved.
- **`reduce_fraction` in `_util.py` is shared by the embeds.** R3's guard can live there (fixes every caller) or in the youtube parser; the plan guards `reduce_fraction` and validates in youtube so no caller can trip it.
- **The clean-venv install probe (R2) cannot run inside `just check`** (the dev group already has `pymdownx`, which is what masked the bug). It is a pytest marked `integration`, run by the CI integration job that already executes `tests/integration`, and skipped locally when `uv` is unavailable.

## Steps

### Step 1: R1 — Close the Stored XSS in the Fence Marker Comment (High)

**NOTE**: `fence.py:232` writes `f"<!-- {MARKER_NAME}:{json.dumps(payload)} -->"`. `json.dumps` leaves `<` and `>` literal, so a directive value containing `-->` closes the comment early; the truncated remainder becomes malformed JSON, `apply_html` drops the marker fail-soft, and the `html.escape` at `fence.py:351` never runs, leaving a live `<script>` in the output. The capture regexes (`LABEL_RE`, `SECONDARY_LABEL_RE`, `ENVIRONMENT_RE` at `fence.py:39-41`) use `(.+)` and store raw values. Chosen mechanism: escape `<` and `>` to their JSON `\uXXXX` forms in the serialized payload before writing at line 232. This is self-reversing (`json.loads` restores the characters on read, so `apply_html` needs no manual decode) and removes every literal `<`/`>` from inside the comment, so `-->` and `<!--` can never form. The existing `html.escape` at read time stays as defense in depth. Preserve `--warn` and fail-soft for genuinely malformed markers.

```text
1. RED: Write XSS regression tests in tests/test_fence.py. Add a new class TestFenceMarkerXss; do NOT modify existing classes.
   - Define the step-55 probe input verbatim: a "[label foo --> <script>alert(1)</script>]" directive line above a fenced code block.
   - Test expand_source(probe) emits an mw-fence comment whose serialized payload contains no literal "-->" and no literal "<script>" substring (assert "-->" appears only as the single comment terminator, and "<script>" is absent from the emitted marker line).
   - Test the mw render path: render the probe through the in-process markwright render (use the existing render_fence helper / md_with_superfences fixture) and assert the output contains no live "<script>alert(1)</script>" (it appears only escaped, as "&lt;script&gt;", or not at all).
   - Test the mw pre | post path: assert apply_html(stub_render(expand_source(probe))) over the probe leaves no live "<script>" (use the round-trip stub renderer from tests/test_roundtrip.py or a minimal comment-preserving stub).
   - Test round-trip fidelity: a benign label containing a ">" ("[label a > b]") and one containing a "-" ("[label build-all]") still produce their label div correctly through expand_source + apply_html (the fix does not over-escape legitimate directives).
   - Run the suite and confirm the two XSS tests FAIL against current code (live script present) and the benign tests pass.

2. GREEN: Make the marker breakout-proof in src/markwright/fence.py.
   - At line 232, escape the serialized payload for HTML-comment safety: after json.dumps(payload), replace "<" with "\\u003c" and ">" with "\\u003e" before interpolating into the comment. Keep it as a small named helper (e.g. _encode_marker_payload(payload: dict) -> str) so both the constant and the transform are in one place.
   - Confirm the read side needs no change: COMMENT_RE captures the escaped JSON, json.loads decodes "\\u003c"/"\\u003e" back to "<"/">" automatically, and the existing html.escape at line 351 (and :379 for secondary_label, :147 for prefix) still escapes the applied directive text.
   - Re-run: the two XSS tests now pass; the benign and all existing fence tests stay green.

3. REFACTOR: Ensure the encode helper and COMMENT_RE/MARKER_NAME live together and the escaping is documented in the module header as part of the marker contract (payload is comment-safe, self-reversing).

4. Verify --warn and fail-soft are unaffected: run the existing malformed-marker / bad-version / no-block tests. Then run `just check`.
```

### Step 2: R2 + R11 — Packaging Pass: Runtime Dependency, Publish Metadata, Clean-Venv Probe (Medium-high + Low)

**NOTE**: `cli.py` builds the `render` pipeline with `pymdownx.superfences` and `pymdownx.highlight`, but `pyproject.toml` declares `pymdown-extensions>=10.5` only in the dev group (line 21), so `mw render` raises `ModuleNotFoundError` from the built wheel in a clean env. The in-process suite has `pymdownx` via dev, so a unit test cannot catch this; the install probe is the load-bearing regression. R11 rides along: the `uv_build>=0.9.17,<0.10.0` pin (line 31) excludes current uv and warns on build, and the package lacks `classifiers`, `[project.urls]`, and `keywords`.

```text
1. RED: Write the clean-venv install probe.
   - Create tests/integration/test_clean_install.py, marked with @pytest.mark.integration (the marker already exists in pyproject.toml).
   - Skip the whole module if "uv" is not on PATH (shutil.which).
   - Test build_and_render_in_clean_venv:
     - Run "uv build" in a tmp dist dir; assert exit 0 AND assert the combined stdout/stderr contains no build-backend version warning (grep for "uv_build" + "warn"/"does not satisfy"/version-conflict text; assert absent).
     - Create an isolated venv (python -m venv), pip install ONLY the built wheel (no dev group, no editable install).
     - Run the installed "mw render" over a tiny document containing a [youtube dQw4w9WgXcQ] line via subprocess; assert exit 0 and stdout contains "<iframe" and no "ModuleNotFoundError".
   - Run: pytest tests/integration/test_clean_install.py -m integration and confirm it FAILS against current pyproject (ModuleNotFoundError on render).

2. RED: Add an in-gate metadata test in tests/test_packaging.py (new class TestPublishMetadata):
   - Using importlib.metadata.metadata("markwright"): assert at least one "Classifier" entry is present, at least one "Project-URL" entry is present, and "Keywords" is non-empty.
   - Confirm this FAILS against current metadata.

3. GREEN: Edit pyproject.toml.
   - Move "pymdown-extensions>=10.5" from the dev group into [project] dependencies (line 11-13 block), keeping the >=10.5 lower bound. Remove it from the dev group only if nothing else there needs it duplicated (dev may still resolve it transitively; do not double-declare).
   - Widen/update the build pin at line 31 to admit current uv (e.g. "uv_build>=0.9.17,<0.11.0" or the current minor), so "uv build" no longer warns.
   - Add non-empty classifiers, [project.urls], and keywords to [project]. Use accurate values: license Apache-2.0 classifier, Python 3.14 classifier, Topic :: Text Processing :: Markup :: Markdown; urls for Homepage/Repository/Documentation; keywords markdown, python-markdown, do-markdownit, mkdocs, hugo.
   - Run "uv sync" so the lockfile reflects the moved dependency.

4. GREEN: Re-run the metadata test (now passes) and the clean-install probe (now passes: mw render works from the wheel with no dev group, uv build is warning-free).

5. REFACTOR: Confirm the CI integration job runs tests/integration (it already does for the Hugo test) so the clean-install probe is exercised in CI; no workflow change needed unless the job path-filters exclude the new file.

6. Verify `just check` still passes (the clean-install test is marked integration and excluded from the gate; the metadata test runs in-gate).
```

### Step 3: R3 — Guard Zero and Negative Dimensions in the youtube Embed (Medium-high)

**NOTE**: `[youtube ID 0 0]` (or any zero height) reaches `reduce_fraction(width, height)` (`youtube.py:36`), which computes `divisor = math.gcd(0, 0) = 0` then `numerator // divisor` (`_util.py:16-17`), an unhandled ZeroDivisionError that aborts a whole MkDocs build in-process. Guard at both levels: make `reduce_fraction` total, and reject/normalize degenerate dimensions in the youtube parser. Chosen fallback: a zero or negative dimension in a youtube directive falls back to the default 16:9 aspect ratio (no raise, valid embed).

```text
1. RED: Write the unit guard test in tests/test_util.py (create if absent), class TestReduceFractionDegenerate:
   - Test reduce_fraction(0, 0) returns without raising and yields a documented sentinel (choose and assert: returns (0, 0) unchanged).
   - Test reduce_fraction(16, 0) and reduce_fraction(0, 9) do not raise.
   - Test reduce_fraction(-16, 9) and reduce_fraction(16, -9) do not raise.
   - Confirm these FAIL against current _util.py (ZeroDivisionError / unexpected behavior).

2. RED: Write the stage-level test in tests/test_youtube.py, class TestYouTubeDegenerateDimensions:
   - Test expand_source("[youtube dQw4w9WgXcQ 0 0]") returns without raising and produces an iframe whose padding/aspect markup uses the default 16:9 ratio (assert the fallback ratio appears, not a 0-based value).
   - Test a zero height ("[youtube ID 480 0]") and a negative dimension ("[youtube ID -1 9]") likewise return with the default ratio and no traceback.
   - Test the existing valid case ("[youtube dQw4w9WgXcQ 800 450]") still yields its 16:9 markup unchanged.
   - Confirm the degenerate cases FAIL against current code.

3. GREEN: Implement the guards.
   - In src/markwright/_util.py: at the top of reduce_fraction, if numerator == 0 or denominator == 0, return (numerator, denominator) unchanged (gcd is undefined; caller decides). Keep the type signature and RST docstring; document the zero behavior.
   - In src/markwright/youtube.py _render_match: before calling reduce_fraction, if width <= 0 or height <= 0, substitute the module default dimensions (the same defaults used when the directive omits size) so the aspect ratio is valid.

4. REFACTOR: Keep one source of the default dimensions in youtube.py; do not duplicate the 16:9 literals.

5. Verify existing youtube and _util-dependent tests pass, then run `just check` (assert the new branches are covered: zero and negative both exercised).
```

### Step 4: R4 — Unify the Highlight Regexes, Tilde Fences, and the Literal-Marker Promise (Medium; D3 contingency)

**NOTE**: Two divergences, one fix (findings C1 and P3). (1) The base `_HIGHLIGHT_PATTERN` (`highlight.py:14`) lacks the `(?<!\\)` escape guard that `_ESCAPED_HIGHLIGHT_RE` (:17) and `_PROSE_HIGHLIGHT_RE` (:23) carry, so the in-process InlineProcessor wraps `\<^>x\<^>` as `\<mark>x\</mark>` while the CLI pre stage emits the literal, making the spec.md:200 literal-marker promise false. (2) `_CODE_REGION_RE` (:28-31) matches only backtick fences (` ``` `), so the pre stage highlights markers inside `~~~` tilde fences. Preferred resolution: unify so every consumer preserves the literal marker; D3 is the fallback only if some path cannot deliver it.

```text
1. RED: Write the cross-consumer parity tests in tests/test_highlight.py; add new classes, do NOT modify existing ones.
   - Add class TestHighlightConsumerParity with a parametrized helper that runs one input through all three consumers: (a) the in-process render (render_highlight / md fixture), (b) run_pre(text, ["highlight"]), (c) run_post(stub_render(run_pre(text, ["highlight"])), ["highlight"]) — the mw pre | post path.
     - Test "a \<^>x\<^> b" produces a literal marker with NO <mark> on all three consumers (identical highlight result). Confirm this FAILS against current code (in-process emits \<mark>).
     - Test "a <^>x<^> b" (unescaped) produces <mark>x</mark> on all three consumers (unchanged behavior).
   - Add class TestHighlightTildeFence:
     - Test expand_source("~~~\n<^>x<^>\n~~~") leaves the marker untouched (no <mark>), matching the existing backtick-fence behavior.
     - Test the backtick case ("```\n<^>x<^>\n```") is still untouched (regression guard).
   - Add class TestHighlightPatternGuards (code-level pin):
     - Assert all three patterns carry the escape guard: that _HIGHLIGHT_PATTERN, _ESCAPED_HIGHLIGHT_RE.pattern, and _PROSE_HIGHLIGHT_RE.pattern each contain the "(?<!\\)" lookbehind (or a shared constant), so a future divergence fails loudly.
   - If any existing test pins the old base-pattern behavior (e.g. an in-process test asserting \<mark> on an escaped marker), update it as part of this red step and note that the buggy expectation was corrected.

2. GREEN: Unify the contract in src/markwright/highlight.py.
   - Add the "(?<!\\)" escape guard to _HIGHLIGHT_PATTERN (line 14) so the in-process InlineProcessor honors the backslash escape like the other two consumers. Factor the guard/marker into a shared constant if it reduces drift.
   - Extend _CODE_REGION_RE (lines 28-31) so the "fence" alternative matches tilde fences as well as backtick fences (add a "~~~" fence branch alongside the "```" branch, same DOTALL/MULTILINE handling).
   - Re-run: the parity and tilde tests pass; all three consumers agree.

3. D3 CHECKPOINT: Verify the literal-marker promise now holds on mw render, mw pre, and mw pre | post (the parity test is green).
   - If every path delivers the literal marker: the spec.md:200 claim is true by behavior; ensure no CURRENT doc repeats a false claim — grep README.md and docs/ for the literal-marker wording and correct any that is now inaccurate. Record in the spec.md Decisions section (D3) that the promise was made true by unification.
   - If some path CANNOT deliver the literal marker under Python-Markdown: STOP, run /bpe:brainstorm on D3, record the corrected promise in the spec.md Decisions section, reconcile the consumers on the achievable behavior, and update the tests to the corrected contract. The false claim must not survive either branch.

4. REFACTOR: Keep the escaped, raw, and prose patterns sharing one guard source; keep the span-boundary-safe wrapper used only by apply_html.

5. Verify existing highlight and round-trip tests pass, then run `just check` (new tilde and escape branches covered).
```

### Step 5: R7a — Normalize the Instagram Permalink (Medium-low, Firm Half of R7)

**NOTE**: `instagram.py:87` reuses the raw input URL for `data-instgrm-permalink` (`escaped_url`), but upstream `instagram.js:170` forces `https://www.instagram.com/p/${post}`; the embed script (`embed.js`) needs the `www` host to resolve. This is the firm change-code (output format) half of R7. The shortcode-grammar half is D2-gated and lands in Step 10; split the test file accordingly.

```text
1. RED: Write the permalink test in tests/test_instagram.py, class TestInstagramPermalinkNormalization:
   - Test that for a valid input ("[instagram https://www.instagram.com/p/CkQuv3_LRgS]") the emitted data-instgrm-permalink attribute is exactly "https://www.instagram.com/p/CkQuv3_LRgS" (the normalized www form built from the extracted post id), regardless of the input host/scheme.
   - Test that an input without the www host or with a trailing query/path still yields the normalized "https://www.instagram.com/p/${post}" permalink (post id extracted, canonical URL rebuilt).
   - Confirm these FAIL against current code (raw input URL reused).
   - Leave a placeholder note for the D2-gated shortcode-grammar tests (Step 10); do not add them here.

2. GREEN: In src/markwright/instagram.py, extract the post id from the matched input and build data-instgrm-permalink as f"https://www.instagram.com/p/{post_id}" (attribute-escaped), replacing the raw escaped_url reuse at line 87. Do not change the accepted input grammar in this step.

3. REFACTOR: Keep the canonical permalink format in one place (a module constant/template) shared with any test.

4. Verify existing instagram tests pass (update only the one that pins the raw-URL permalink, as part of the red step), then run `just check`.
```

### Step 6: R8 — Match the Compare SVG to Upstream (Low)

**NOTE**: `image_compare.py:18-23` emits a `viewBox="0 0 100 100"` two-polygon SVG; upstream `compare.js:110` emits a `viewBox="0 0 512 512"` single-path handle icon. Output-format parity (Global Requirement 1). Copy the exact path data from `compare.js:110`.

```text
1. RED: In tests/test_image_compare.py add class TestCompareSvgUpstreamParity:
   - Test the emitted compare HTML contains a single <svg ...> with viewBox="0 0 512 512" and exactly one <path ...> element (assert result.count("<path") == 1 and "<polygon" not in result).
   - Test the path "d" attribute equals the exact upstream path string from compare.js:110.
   - Confirm these FAIL against the current two-polygon markup.

2. GREEN: In src/markwright/image_compare.py, replace the two-polygon SVG constant (lines 18-23) with the upstream single-path viewBox="0 0 512 512" SVG, copying the path data verbatim from compare.js:110. Preserve the existing class attribute ("control-arrow") and any wrapper markup.

3. REFACTOR: Keep the SVG as one module constant.

4. Verify existing image_compare tests pass (update the one that pins the old SVG as part of the red step), then run `just check`.
```

### Step 7: R9 — Match the Slideshow Nav JavaScript to Upstream (Low)

**NOTE**: `slideshow.py:113` emits `this.parentElement.querySelector('.slides').scrollBy(...)`; upstream `slideshow.js:112-113` emits a `getElementsByClassName('slides')[0].scrollLeft += / -= width` IIFE. Pure output-string parity (Global Requirement 1).

```text
1. RED: In tests/test_slideshow.py add class TestSlideshowNavUpstreamParity:
   - Test the emitted nav markup contains the upstream scrollLeft IIFE form: assert "getElementsByClassName" and "scrollLeft" appear and "scrollBy" does NOT, for both the previous (-=) and next (+=) buttons.
   - Test the exact emitted onclick/handler string matches the upstream shape for a two-image slideshow.
   - Confirm these FAIL against the current scrollBy form.

2. GREEN: In src/markwright/slideshow.py, replace the scroll_js at line 113 (and its +/- usages around 113-115) with the upstream getElementsByClassName(...)[0].scrollLeft += width / -= width IIFE, porting the exact upstream string.

3. REFACTOR: Keep the nav handler string(s) as named constants shared by both buttons.

4. Verify existing slideshow tests pass (update any that pin the old nav string as part of the red step), then run `just check`.
```

### Step 8: R10 — Fix the image_compare Token in the README and Docs (Low, Doc Fix)

**NOTE**: The working author-facing token is `[compare ...]` (`COMPARE_RE`, `image_compare.py:13`); `image_compare` is the internal registry name only (`registry.py:45`). `README.md:141` tells the reader to write `[image_compare before.jpg after.jpg]`, which renders nothing when copy-pasted. Public prose follows the repo writing rules (no em/en dashes, straight quotes).

```text
1. RED: Write the doc probe in tests/test_docs_tokens.py (create), class TestAuthorFacingCompareToken:
   - Test a grep-style scan: read README.md and every file under docs/, assert the author-facing token "[image_compare" does not appear (the internal name may still appear in prose describing the registry, so scope the assertion to the directive-in-example form "[image_compare " with a trailing space/arg).
   - Test that rendering "[compare before.jpg after.jpg]" through the in-process markwright render (or expand_source) produces the compare markup (a "<div class=\"image-compare\"" or the compare SVG), proving the corrected example works when copy-pasted.
   - Confirm the grep test FAILS against current README.md:141.

2. GREEN: Edit README.md line 141: change "[image_compare before.jpg after.jpg]" to "[compare before.jpg after.jpg]". Scan docs/ for any other reader-facing "[image_compare ..." example and correct it to "[compare ...".
   - If this remediation spec.md carries a Stage Matrix reference using the internal token, correct it to the author-facing token and note the correction in the spec.md Decisions section (the frozen design-spec row stays in git history untouched).

3. REFACTOR: None (doc-only).

4. Verify `just check` still passes (docs edits do not break the gate) and, if the docs build is part of verification, `just docs-build --strict` is clean.
```

### Step 9: D1 + R5 — Decide and Land Single-Image Slideshow Parity (Medium-low, Brainstorm-Gated)

**NOTE**: `slideshow.py:37` requires `len(urls) >= 2`, dropping a single-image slideshow; upstream `slideshow.js:82` rejects only `!images.length`. This step is gated on Decision D1 (restore `>= 1` for strict parity, or keep `>= 2` as a documented design choice). Do NOT change the code before D1 is recorded.

```text
1. DECIDE: Resolve D1 via /bpe:brainstorm. Record the outcome (code parity vs documented divergence) in the spec.md Decisions section before writing any branch code.

2. RED (branch on D1):
   - If CODE PARITY (>= 1): in tests/test_slideshow.py add class TestSingleImageSlideshow:
     - Test expand_source("[slideshow https://a.jpg]") produces the same slideshow markup shape as the two-image case (a "<div class=\"slideshow\"" with one slide), matching what upstream would emit.
     - Test the existing two-image case is unchanged.
     - Update the existing test that pins ">= 2 drops single image" to the new accepting behavior (part of the red step).
     - Confirm the single-image test FAILS against current code.
   - If DOCUMENTED DIVERGENCE (keep >= 2): in tests/test_slideshow.py add class TestSlideshowMinimumImages:
     - Test expand_source("[slideshow https://a.jpg]") returns the line unchanged (single image rejected), pinning >= 2 as intentional.
     - And update docs/extensions/slideshow.md (or the relevant doc) to state the two-image minimum and the reason (a slideshow needs at least two slides).

3. GREEN (branch on D1):
   - If code parity: change slideshow.py line 37 to len(urls) < 1 (accept one or more), leaving the rest of the builder unchanged.
   - If documented divergence: no code change; ensure the doc states the minimum and the test pins it.

4. Verify existing slideshow tests pass, then run `just check`.
```

### Step 10: D2 + R6 + R7b — Decide and Land Embed URL Grammar Parity (Medium-low, Brainstorm-Gated)

**NOTE**: The Twitter regex (`twitter.py:14`) and the Instagram regex (`instagram.py:14`) require full URLs; upstream (`twitter.js:89`, `instagram.js:89`) accepts scheme-less, `www.`-optional, and bare `user/status/id` or shortcode forms. D2 decides once for BOTH embeds (restore the permissive grammar, or keep the stricter grammar as a documented input contract). R7's permalink half already landed in Step 5 and is NOT part of this decision.

```text
1. DECIDE: Resolve D2 via /bpe:brainstorm. Record the outcome (code parity vs documented narrowing) in the spec.md Decisions section before writing any branch code.

2. RED (branch on D2), Twitter — tests/test_twitter.py class TestTwitterUrlGrammar:
   - If CODE PARITY: test each upstream-accepted form produces the expected blockquote: scheme-less ("[twitter twitter.com/user/status/123]"), www-prefixed ("[twitter https://www.twitter.com/user/status/123]"), and bare ("[twitter user/status/123]"). Confirm they FAIL against the current regex.
   - If DOCUMENTED NARROWING: test the required full-URL grammar is enforced (bare/scheme-less forms are rejected / left unchanged), pinning the narrowing, and update docs/extensions/twitter.md to state the accepted grammar.

3. RED (branch on D2), Instagram — tests/test_instagram.py class TestInstagramShortcodeGrammar:
   - If CODE PARITY: test that a bare shortcode ("[instagram CkQuv3_LRgS]") and scheme-less/host-optional forms produce the embed, AND that the permalink is still normalized to https://www.instagram.com/p/${post} (the Step 5 behavior holds for the new input forms). Confirm they FAIL against the current regex.
   - If DOCUMENTED NARROWING: test the full-URL requirement is enforced and update docs/extensions/instagram.md.

4. GREEN (branch on D2):
   - If code parity: widen TWITTER_RE (twitter.py:14) and INSTAGRAM_RE (instagram.py:14) to make scheme, "www.", and the URL prefix optional and to accept the bare user/status/id and shortcode forms, porting the upstream grammar. Re-derive the post id extraction so R7's permalink normalization still emits the canonical www URL for the new input shapes.
   - If documented narrowing: no regex change; ensure both docs state the grammar and the tests pin it.

5. REFACTOR: If both embeds share the same optional-scheme/optional-www structure, factor the common URL-grammar fragment so the two regexes stay in agreement (they diverged the same way; keep them fixed the same way).

6. Verify existing twitter and instagram tests pass (update any that pinned the old grammar as part of the red step), then run `just check`.
```

## Implementation Guidelines

- Load the `python` skill before writing any code each step.
- Work strictly RED then GREEN then REFACTOR. Write the failing test first and watch it fail for the right reason (the actual defect) before implementing. Where an existing test encodes the buggy behavior, updating it is part of the red step (Global Requirement 4).
- Every fix carries the regression test or probe that would have caught it. The gate missed all 12 because no test fed the triggering input; do not let a fix land without that input under test.
- Hold every diff to upstream parity (Global Requirement 1) and the security rule (Global Requirement 2): no author-controlled directive text may produce live HTML or script at any stage.
- Do not modify existing per-extension test classes that pin unchanged in-process behavior; add new classes alongside them. The exception is a test that encodes a defect being fixed, which the red step updates deliberately.
- Coverage stays at 100 percent line AND branch. New branches (the R1 payload escaping, the R3 zero and negative guards, the R4 tilde and escape paths) carry their own cases; a line-only pass is not enough.
- The brainstorm-gated branches (D1, D2, and the D3 contingency) must have their Decision recorded in the spec.md Decisions section before the branch code lands.
- Test only markwright logic. Do not test Python-Markdown, pymdownx, argparse, or pygments behavior.
- `just check` (pytest with 100 percent coverage, ruff, mypy strict) must pass before a step is considered complete. The clean-install probe (R2) runs in the CI integration job, not the local gate.
- Every source file keeps its `# ABOUTME:` header, `from __future__ import annotations`, full type hints (no `Any`), absolute imports, and RST docstrings.
- Public prose (README, docs) follows the repo writing rules: no em-dashes or en-dashes, straight quotes, plain voice.

## Success Metrics

- The two step-55 XSS probes render inert on both the `mw render` and `mw pre | render | mw post` paths, committed as regression tests that fail against pre-fix code (R1).
- `mw render` runs from the built wheel in a clean venv with no dev group; `uv build` is warning-free; the package carries classifiers, urls, and keywords (R2, R11).
- No youtube dimension input (zero, negative) raises; the fallback aspect ratio is asserted (R3).
- `\<^>` renders as a literal marker identically across `mw render`, `mw pre`, and `mw pre | post`; markers inside tilde fences are left for the post stage; the three patterns share one escape guard; the literal-marker promise is true or D3 records the corrected promise (R4).
- The Instagram `data-instgrm-permalink` is the normalized `https://www.instagram.com/p/${post}` form (R7a).
- The compare SVG matches upstream (`viewBox 0 0 512 512`, single path); the slideshow nav JS matches upstream's `scrollLeft` IIFE (R8, R9).
- No reader-facing doc instructs `[image_compare ...]`; the corrected `[compare ...]` example renders when copy-pasted (R10).
- D1, D2, and D3 are resolved and recorded before R5, the R6/R7 grammar half, and the R4 fallback land; the chosen branch is under test (Steps 4, 9, 10).
- All existing extension tests stay green; coverage stays at 100 percent; mypy strict and ruff stay clean; `just check` passes after every step.
