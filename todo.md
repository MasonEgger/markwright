# TODO: markwright step-55 Remediation

Mirrors `plan.md`. `/bpe:execute-plan` checks off sub-steps as it goes.
Steps 1-3 (the release blockers) landed 2026-09-08. D1 and D2 were resolved 2026-09-14 (both upstream parity, change-code; see spec.md Decisions), so Steps 4-10 are now queued below with their decided branches. D3 stays an in-code contingency inside Step 4.
The prior completed pipeline-CLI todo (12 steps, all checked) is preserved in git history (`git log -- todo.md`); this file now tracks the remediation cycle instead.

## Step 1: R1: Close the Stored XSS in the Fence Marker Comment (High)
- [x] 1. RED: add `TestFenceMarkerXss` to `tests/test_fence.py` with the step-55 probe (`[label foo --> <script>alert(1)</script>]`); assert no live `-->` breakout or live `<script>` on the `mw render` path and the `mw pre | post` path; add benign `>` / `-` round-trip cases; confirm the XSS cases FAIL against current code
- [x] 2. GREEN: escape `<` / `>` to `\uXXXX` in the serialized marker payload at `fence.py:232` via a small `_encode_marker_payload` helper; confirm `json.loads` round-trips it with no read-side change needed
- [x] 3. REFACTOR: keep the encode helper next to `COMMENT_RE`/`MARKER_NAME`; document the comment-safe, self-reversing contract in the module header
- [x] 4. Verify `--warn` / fail-soft (malformed marker, bad version, no-block) tests still pass; `just check`

## Step 2: R2 + R11: Packaging Pass: Runtime Dependency, Publish Metadata, Clean-Venv Probe (Medium-high + Low)
- [x] 1. RED: add `tests/integration/test_clean_install.py` (marked `integration`, skip if `uv` missing) that builds the wheel, installs it in an isolated venv with no dev group, and asserts `mw render` on a `[youtube ...]` doc exits 0 with no `ModuleNotFoundError`; also assert `uv build` emits no build-backend version warning
- [x] 2. RED: add `TestPublishMetadata` to `tests/test_packaging.py` asserting non-empty Classifier, Project-URL, and Keywords via `importlib.metadata.metadata("markwright")`; confirm both new tests FAIL against current `pyproject.toml`
- [x] 3. GREEN: move `pymdown-extensions>=10.5` from the dev group to `[project] dependencies`; widen the `uv_build` pin to admit current uv; add classifiers, `[project.urls]`, and keywords; run `uv sync`
- [x] 4. GREEN: re-run the metadata test and the clean-install probe; both pass
- [x] 5. REFACTOR: confirm the CI integration job already runs `tests/integration` (no workflow change needed unless path-filtered)
- [x] 6. Verify `just check` stays green (clean-install probe stays excluded via the `integration` marker; metadata test runs in-gate)

## Step 3: R3: Guard Zero and Negative Dimensions in the youtube Embed (Medium-high)
- [x] 1. RED: add `TestReduceFractionDegenerate` to `tests/test_util.py` (create if absent) covering `(0, 0)`, `(16, 0)`, `(0, 9)`, `(-16, 9)`, `(16, -9)`; none may raise; confirm FAIL against current `_util.py`
- [x] 2. RED: add `TestYouTubeDegenerateDimensions` to `tests/test_youtube.py` for `[youtube ID 0 0]`, a zero height, and a negative dimension, each asserting the default 16:9 fallback markup with no traceback; confirm existing valid-dimension case still passes; confirm degenerate cases FAIL against current code
- [x] 3. GREEN: in `_util.py`, make `reduce_fraction` return `(numerator, denominator)` unchanged when either is zero (document the zero behavior); in `youtube.py` `_render_match`, substitute the module default dimensions when width or height is `<= 0` before calling `reduce_fraction`
- [x] 4. REFACTOR: keep the 16:9 default dimensions declared once in `youtube.py`
- [x] 5. Verify existing youtube / `_util` tests pass and new zero/negative branches are covered; `just check`

## Step 4: R4: Unify the Highlight Regexes, Tilde Fences, and the Literal-Marker Promise (Medium; D3 contingency)
- [x] 1. RED: add `TestHighlightConsumerParity` to `tests/test_highlight.py` (new class) running one input through all three consumers (in-process render, `run_pre(text, ["highlight"])`, and the `run_post(stub_render(run_pre(...)))` pre|post path); assert `a \<^>x\<^> b` yields a literal marker with NO `<mark>` on all three (FAILS now: in-process emits `\<mark>`), and `a <^>x<^> b` yields `<mark>x</mark>` on all three (unchanged)
- [x] 2. RED: add `TestHighlightTildeFence` asserting `expand_source` leaves a `<^>` marker inside a `~~~` tilde fence untouched (matching the backtick-fence behavior, which stays a regression guard)
- [x] 3. RED: add `TestHighlightPatternGuards` asserting all three patterns (`_HIGHLIGHT_PATTERN`, `_ESCAPED_HIGHLIGHT_RE`, `_PROSE_HIGHLIGHT_RE`) carry the `(?<!\\)` escape guard; update any existing test that pins the old base-pattern `\<mark>` behavior (part of the red step)
- [x] 4. GREEN: add the `(?<!\\)` escape guard to `_HIGHLIGHT_PATTERN`; extend `_CODE_REGION_RE` so the fence branch matches `~~~` tilde fences as well as backtick fences; all three consumers agree
- [x] 5. D3 CHECKPOINT: confirm the literal-marker promise now holds on all three paths; grep README.md and docs/ for any now-inaccurate literal-marker wording and correct it; record in spec.md Decisions (D3) that the promise was made true by unification. Only if a path CANNOT deliver the literal marker under Python-Markdown: stop, resolve D3, record the corrected promise, reconcile the consumers and tests
- [x] 6. REFACTOR: keep the escaped/raw/prose patterns sharing one guard source; keep the span-safe wrapper in `apply_html` only
- [x] 7. Verify existing highlight and round-trip tests pass, new tilde and escape branches covered; `just check`

## Step 5: R7a: Normalize the Instagram Permalink (Medium-low, Firm Half of R7)
- [x] 1. RED: add `TestInstagramPermalinkNormalization` to `tests/test_instagram.py` asserting the emitted `data-instgrm-permalink` is the canonical `https://www.instagram.com/p/${post}` built from the extracted post id (regardless of input host/scheme, and for inputs with a trailing query/path); confirm FAIL against current raw-URL reuse; leave a placeholder note for the D2-gated shortcode-grammar tests (Step 10)
- [x] 2. GREEN: in `instagram.py`, extract the post id and build `data-instgrm-permalink` as `f"https://www.instagram.com/p/{post_id}"` (attribute-escaped), replacing the raw `escaped_url` reuse; do not change the accepted input grammar in this step
- [x] 3. REFACTOR: keep the canonical permalink template in one place shared with the test
- [x] 4. Verify existing instagram tests pass (update only the one pinning the raw-URL permalink, as part of the red step); `just check`

## Step 6: R8: Match the Compare SVG to Upstream (Low)
- [x] 1. RED: add `TestCompareSvgUpstreamParity` to `tests/test_image_compare.py` asserting the emitted compare HTML has a single `<svg>` with `viewBox="0 0 512 512"`, exactly one `<path>` (no `<polygon>`), and the `d` attribute equal to the exact upstream path string from `compare.js:110`; confirm FAIL against the current two-polygon markup
- [x] 2. GREEN: in `image_compare.py`, replace the two-polygon `viewBox="0 0 100 100"` SVG with the upstream single-path `viewBox="0 0 512 512"` SVG (path data verbatim from `compare.js:110`), preserving the existing class attribute and wrapper markup
- [x] 3. REFACTOR: keep the SVG as one module constant
- [x] 4. Verify existing image_compare tests pass (update the one pinning the old SVG, as part of the red step); `just check`

## Step 7: R9: Match the Slideshow Nav JavaScript to Upstream (Low)
- [ ] 1. RED: add `TestSlideshowNavUpstreamParity` to `tests/test_slideshow.py` asserting the emitted nav markup uses the upstream `getElementsByClassName('slides')[0].scrollLeft += / -= width` IIFE form (`getElementsByClassName` and `scrollLeft` present, `scrollBy` absent) for both the previous and next buttons; confirm FAIL against the current `scrollBy` form
- [ ] 2. GREEN: in `slideshow.py`, replace the `scrollBy` nav handler with the upstream `getElementsByClassName(...)[0].scrollLeft += width / -= width` IIFE, porting the exact upstream string
- [ ] 3. REFACTOR: keep the nav handler string(s) as named constants shared by both buttons
- [ ] 4. Verify existing slideshow tests pass (update any pinning the old nav string, as part of the red step); `just check`

## Step 8: R10: Fix the image_compare Token in the README and Docs (Low, Doc Fix)
- [ ] 1. RED: add `TestAuthorFacingCompareToken` to `tests/test_docs_tokens.py` (create): a grep-style scan asserting the directive-in-example form `[image_compare ` (trailing space/arg) does not appear in README.md or under docs/; plus a test that rendering `[compare before.jpg after.jpg]` produces the compare markup; confirm the grep test FAILS against current `README.md:141`
- [ ] 2. GREEN: change `README.md:141` `[image_compare before.jpg after.jpg]` to `[compare before.jpg after.jpg]`; scan docs/ for any other reader-facing `[image_compare ...` example and correct it; follow the repo writing rules (no em/en dashes, straight quotes)
- [ ] 3. Verify `just check` passes and `just docs-build` is clean (strict)

## Step 9: R5: Land Single-Image Slideshow Parity (Medium-low; D1 resolved: accept 1+)
- [ ] 1. RED: add `TestSingleImageSlideshow` to `tests/test_slideshow.py` asserting `expand_source("[slideshow https://a.jpg]")` produces the slideshow markup shape (a `<div class="slideshow">` with one slide) and the two-image case is unchanged; update the existing test that pins ">= 2 drops single image" to the new accepting behavior (part of the red step); confirm the single-image test FAILS against current code
- [ ] 2. GREEN: relax the `slideshow.py:37` guard from `len(urls) < 2` to `len(urls) < 1` (accept one or more), leaving the rest of the builder unchanged
- [ ] 3. Verify existing slideshow tests pass; `just check`

## Step 10: R6 + R7b: Land Permissive Embed URL Grammar Parity (Medium-low; D2 resolved: permissive)
- [ ] 1. RED (Twitter): add `TestTwitterUrlGrammar` to `tests/test_twitter.py` asserting each upstream-accepted form produces the expected blockquote: scheme-less (`[twitter twitter.com/user/status/123]`), www-prefixed (`[twitter https://www.twitter.com/user/status/123]`), and bare (`[twitter user/status/123]`); confirm FAIL against the current regex
- [ ] 2. RED (Instagram): add `TestInstagramShortcodeGrammar` to `tests/test_instagram.py` asserting a bare shortcode (`[instagram CkQuv3_LRgS]`) and scheme-less/host-optional forms produce the embed AND that the permalink is still normalized to `https://www.instagram.com/p/${post}` (Step 5 behavior holds for the new input forms); confirm FAIL against the current regex
- [ ] 3. GREEN: widen `TWITTER_RE` (`twitter.py:14`) and `INSTAGRAM_RE` (`instagram.py:14`) to make scheme, `www.`, and the URL prefix optional and to accept the bare `user/status/id` and shortcode forms, porting the upstream grammar; re-derive the post id extraction so R7's permalink normalization still emits the canonical www URL for the new input shapes
- [ ] 4. REFACTOR: if both embeds share the same optional-scheme/optional-www structure, factor the common URL-grammar fragment so the two regexes stay in agreement
- [ ] 5. Verify existing twitter and instagram tests pass (update any that pinned the old grammar, as part of the red step); `just check`
