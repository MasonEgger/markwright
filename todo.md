# TODO: markwright step-55 Remediation

Mirrors `plan.md`'s Steps 1-3 (the three release blockers). `/bpe:execute-plan` checks off sub-steps as it goes.
Steps 4-10 are withheld: Step 4 folds in the D3 contingency and Steps 9-10 are hard-blocked on Mason's D1/D2 decisions, so they are not queued here yet.
The prior completed pipeline-CLI todo (12 steps, all checked) is preserved in git history (`git log -- todo.md`); this file now tracks the remediation cycle instead.

## Step 1: R1 — Close the Stored XSS in the Fence Marker Comment (High)
- [x] 1. RED: add `TestFenceMarkerXss` to `tests/test_fence.py` with the step-55 probe (`[label foo --> <script>alert(1)</script>]`); assert no live `-->` breakout or live `<script>` on the `mw render` path and the `mw pre | post` path; add benign `>` / `-` round-trip cases; confirm the XSS cases FAIL against current code
- [x] 2. GREEN: escape `<` / `>` to `\uXXXX` in the serialized marker payload at `fence.py:232` via a small `_encode_marker_payload` helper; confirm `json.loads` round-trips it with no read-side change needed
- [x] 3. REFACTOR: keep the encode helper next to `COMMENT_RE`/`MARKER_NAME`; document the comment-safe, self-reversing contract in the module header
- [x] 4. Verify `--warn` / fail-soft (malformed marker, bad version, no-block) tests still pass; `just check`

## Step 2: R2 + R11 — Packaging Pass: Runtime Dependency, Publish Metadata, Clean-Venv Probe (Medium-high + Low)
- [x] 1. RED: add `tests/integration/test_clean_install.py` (marked `integration`, skip if `uv` missing) that builds the wheel, installs it in an isolated venv with no dev group, and asserts `mw render` on a `[youtube ...]` doc exits 0 with no `ModuleNotFoundError`; also assert `uv build` emits no build-backend version warning
- [x] 2. RED: add `TestPublishMetadata` to `tests/test_packaging.py` asserting non-empty Classifier, Project-URL, and Keywords via `importlib.metadata.metadata("markwright")`; confirm both new tests FAIL against current `pyproject.toml`
- [x] 3. GREEN: move `pymdown-extensions>=10.5` from the dev group to `[project] dependencies`; widen the `uv_build` pin to admit current uv; add classifiers, `[project.urls]`, and keywords; run `uv sync`
- [x] 4. GREEN: re-run the metadata test and the clean-install probe; both pass
- [x] 5. REFACTOR: confirm the CI integration job already runs `tests/integration` (no workflow change needed unless path-filtered)
- [x] 6. Verify `just check` stays green (clean-install probe stays excluded via the `integration` marker; metadata test runs in-gate)

## Step 3: R3 — Guard Zero and Negative Dimensions in the youtube Embed (Medium-high)
- [x] 1. RED: add `TestReduceFractionDegenerate` to `tests/test_util.py` (create if absent) covering `(0, 0)`, `(16, 0)`, `(0, 9)`, `(-16, 9)`, `(16, -9)`; none may raise; confirm FAIL against current `_util.py`
- [x] 2. RED: add `TestYouTubeDegenerateDimensions` to `tests/test_youtube.py` for `[youtube ID 0 0]`, a zero height, and a negative dimension, each asserting the default 16:9 fallback markup with no traceback; confirm existing valid-dimension case still passes; confirm degenerate cases FAIL against current code
- [x] 3. GREEN: in `_util.py`, make `reduce_fraction` return `(numerator, denominator)` unchanged when either is zero (document the zero behavior); in `youtube.py` `_render_match`, substitute the module default dimensions when width or height is `<= 0` before calling `reduce_fraction`
- [x] 4. REFACTOR: keep the 16:9 default dimensions declared once in `youtube.py`
- [x] 5. Verify existing youtube / `_util` tests pass and new zero/negative branches are covered; `just check`
