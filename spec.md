# markwright Remediation Specification

## Overview

markwright ports DigitalOcean's `do-markdownit` (JavaScript / markdown-it, Apache 2.0) into a set of Python-Markdown extensions plus an `mw` command-line tool that exposes those extensions as pre and post filter stages.
The build is complete and the design spec it was built from is preserved in git at `git show main:spec.md`.
A portfolio review on 2026-07-02 raised candidate findings against the built code.
Adversarial verification (step 55, `.ai-sessions/step-55-do-markdown-verified.md`) confirmed 12 defects with exact file and line references and refuted none.
This document defines the required behavior for fixing every confirmed defect.

The bar for this repository is a publish-candidate.
markwright is meant to be installed from a wheel and dropped into anyone's markdown toolchain, so two of the confirmed defects are release blockers on their face: a stored cross-site scripting hole through the fence marker (R1), and an `mw render` that dies with `ModuleNotFoundError` in every clean install (R2).
The project already has a gate, `just check` (test, lint, typecheck, with 100 percent line and branch coverage; CLAUDE.md:20,30).
That gate is green on the current tree and it missed all 12 of these.
It missed them because none of the confirmed defects had a test that fed the triggering input: no XSS probe through the fence marker, no clean-venv install check, no zero-dimension embed, no cross-consumer highlight comparison.
Every requirement below therefore carries a regression test or probe that would have caught the defect, so the gate that let these through starts catching their class.

The design spec is not edited.
It stays in git history at `git show main:spec.md` and this remediation spec replaces it at the repo root for the audit cycle.
Citations of the form "spec.md:N" refer to that frozen file (`git show main:spec.md` line N).
One design-spec claim is now false (the literal-marker promise at spec.md:200); R4 makes it true or corrects it.
The parity decisions that the verifier flagged as "change-spec defensible" are not written as blind code requirements; they are routed to the Decisions section below for `/bpe:brainstorm`.

## Scope

In scope: the 12 confirmed defects, their regression tests, the one false design-spec claim, and the two documentation fixes.
Out of scope: the concurred non-defects (step-55 note, "Non-defects" section), new extensions, and refactors beyond what a fix requires.

Severity triage used for ordering:

- High (R1): a stored XSS hole; any directive value can inject live script into the output.
- Medium-high (R2, R3): a shipped subcommand is dead in every clean install, or aborts a whole build on a benign input.
- Medium (R4, R5): two consumers of the same feature disagree and the design spec promises behavior the code does not deliver.
- Medium-low (R6, R7, R8): upstream-parity narrowing on the embeds, part firm and part pending a Decision.
- Low (R9, R10, R11): output-format parity drift, a copy-paste-breaking doc error, and packaging polish.

## Available Tooling

Tools the `bpe:validator` agent should consult when reviewing diffs in `/bpe:goal` runs.
`/bpe:plan` propagates these to per-section declarations in plan.md.

**Skills:**
- python:python (modern Pythonic style, strict type hints, uv workflows, pytest)

**Notes:** there is no Temporal in this repo; do not attach the Temporal MCP or the temporal-developer skill.
The repo gate is `just check` (CLAUDE.md:20): `just test` (pytest, 100 percent line and branch coverage, `--cov-branch --cov-fail-under=100`), `just lint` (ruff check plus ruff format --check), `just typecheck` (mypy --strict).
The Hugo integration test is excluded from the gate and run via `just test-integration` (CLAUDE.md:30,94).
Validator should hold every diff to the parity rule (Global Requirement 1) and to the security rule (Global Requirement 2).

## Global Requirements

These apply to every requirement below.

1. **Upstream parity.** Output must match `do-markdownit` unless a Decision below explicitly documents a divergence (CLAUDE.md:34).
   Where a requirement's direction is "change-code", the fix restores upstream behavior; where a Decision resolves "change-spec", the divergence is documented, not silently kept.
2. **Security.** No author-controlled directive text may produce live HTML or script in the output of any stage.
   Directive values are data, not markup.
3. **Gates.** `just check` (test, lint, typecheck; 100 percent line and branch coverage) passes after every requirement.
4. **Test-first.** Each fix starts with a failing test or probe that reproduces the defect, then the fix makes it pass.
   Where an existing test encodes the buggy behavior, updating it is part of the red step.
5. **Coverage stays at 100 percent.** New branches (the zero-dimension guard, the payload escaping) carry their own cases; a line-only pass is not enough (CLAUDE.md:30,95).
6. **Spec citations.** "spec.md:N" means `git show main:spec.md` line N.
   The design spec file is not edited; the one false claim it contains is resolved in R4.
7. **Public prose.** All README and docs edits follow the repo writing rules: no em-dashes or en-dashes, straight quotes, plain voice.

## Requirements

### R1: Close the Stored XSS in the Fence Marker Comment (High)

**Defect.** `fence.py:232` serializes the fence directives as `f"<!-- {MARKER_NAME}:{json.dumps(payload)} -->"`.
`json.dumps` does not escape `>`, `<`, or `-`, so a directive value containing the literal ` --> ` closes the HTML comment early.
The capture regexes at `fence.py:39-43` (`LABEL_RE`, `SECONDARY_LABEL_RE`, `ENVIRONMENT_RE`) use `(.+)`, which matches `>` and `-`, and the raw values are stored unescaped at `fence.py:208` (label), `:212` (secondary_label), `:216` (environment), and `:72` (custom_prefix).
When the payload breaks the comment, `COMMENT_RE` (`fence.py:42`) captures a truncated group, that group is malformed JSON, and the post stage drops the marker fail-soft (the `json.JSONDecodeError` branch).
The `html.escape` at `fence.py:351` never runs because it is only reached after a successful parse.
Verified both paths: `mw render` on the step-55 probe emits a live `<script>alert(1)</script>` at the top of the document, and `mw pre | render | mw post` leaves the live `<script>` after post.
The reproduced probe is in the step-55 verification scratchpad (`verify-55/h1_input.md`, `h1_render.out`, `h1_post.out`).

**Root cause.** The marker uses HTML-comment encoding but serializes author-controlled text into it without escaping the comment's terminating sequence, and the only escaping in the pipeline (`fence.py:351`) sits after the parse that the breakout defeats.

**Required behavior.** No directive value can break out of the `mw-fence` marker comment.
An author who writes ` --> `, `<script>`, or any other markup inside a label, secondary_label, environment, or custom_prefix directive gets that text treated as inert data at every stage.
The implementer chooses the mechanism; any of these satisfies the requirement:

- Escape `>` and `-` (or the ` --> ` sequence) in the serialized payload before it is written at `fence.py:232`, and reverse the escaping on read in the post stage.
- Move off HTML-comment encoding to a marker that cannot be closed by author text (for example a hidden element carrying a `data-mw-fence` attribute, already contemplated in the design spec's Future Directions).
- Escape or reject the directive text before serialization, at the capture points (`fence.py:208,212,216,72`).

Whichever mechanism is chosen, the post stage still applies the directives to legitimate input unchanged, and the `--warn` and fail-soft behavior for genuinely malformed markers is preserved.

**Acceptance criteria.**
- The two reproduced probes render inert: the `mw render` path and the `mw pre | render | mw post` path over the step-55 XSS input (`verify-55/h1_input.md`) produce output with no live `<script>` tag and no comment breakout.
- Both probes are committed as pytest regression tests (one per path) that assert the injected `<script>` appears only as escaped text or not at all, and fail against the pre-fix code.
- A round-trip test asserts a benign label containing a `>` or a `-` still styles its code block correctly (the fix does not over-escape legitimate directives).
- `just check` passes.

**Test notes.** The step-55 probe input is `[label foo --> <script>alert(1)</script>]` above a fenced block; reuse it verbatim so the regression matches the reproduced finding.
Assert on both consumers, since the two paths reach the marker differently.

### R2: Add pymdown-extensions to Runtime Dependencies (Medium-high)

**Defect.** `cli.py:119-121` builds the `render` pipeline with `pymdownx.superfences` and `pymdownx.highlight`.
`pyproject.toml:11-13` declares only `markdown>=3.4` as a runtime dependency; `pymdown-extensions` is in the dev dependency group.
Verified against the built wheel in a clean uv venv: `mw list`, `mw pre`, and `mw post` work, but `mw render` raises `ModuleNotFoundError: No module named 'pymdownx'`.
The README standalone and MkDocs examples fail identically.
The package is not publishable as-is.

**Root cause.** A runtime import path depends on a package that is declared only for development.

**Required behavior.** `mw render` works from the built wheel in a clean environment with no dev group installed.
`pymdown-extensions` moves to the runtime `dependencies` in `pyproject.toml` with an appropriate lower bound.

**Acceptance criteria.**
- A clean-venv check installs the built wheel with no dev dependencies and runs `mw render` over a small document successfully (no `ModuleNotFoundError`).
- The check is encoded so it can run in CI (a script or a test that builds the wheel, installs it into an isolated venv, and asserts `mw render` exits 0).
- `pymdown-extensions` no longer appears only in the dev group; it is a runtime dependency.
- `just check` passes.

**Test notes.** The clean-venv reproduction is in the step-55 scratchpad (`verify-55/cleanvenv`, `dist/markwright-0.1.0-py3-none-any.whl`).
The in-process test suite already has pymdownx via the dev group, so a unit test alone cannot catch this; the install check is the load-bearing regression.

### R3: Guard Zero and Negative Dimensions in the youtube Embed (Medium-high)

**Defect.** `[youtube ID 0 0]`, or any zero height, triggers an unhandled `ZeroDivisionError`.
`youtube.py:36` calls `reduce_fraction(width, height)`, which reaches `_util.py:17`: `numerator // divisor` where `divisor = math.gcd(0, 0) = 0`, a division by zero.
Verified traceback in `mw pre` and `mw render`; run in-process inside a MkDocs build, it aborts the whole build.
The 100 percent coverage gate never feeds a zero dimension, so it did not catch this.

**Root cause.** `reduce_fraction` assumes a nonzero gcd, and the youtube parser passes author-supplied dimensions straight through without validating them.

**Required behavior.** A zero or negative width or height in a `[youtube ...]` directive does not raise.
The fix guards the degenerate input in `reduce_fraction` or in the youtube parser (for example, fall back to the default aspect ratio, or reject the directive as invalid input); either is acceptable as long as no input produces an unhandled exception.

**Acceptance criteria.**
- A pytest case feeds `[youtube ID 0 0]` (and a zero height, and a negative dimension) through the youtube stage and asserts it returns without raising.
- The chosen fallback is asserted (a valid aspect ratio, or a documented rejection), not just the absence of a traceback.
- The existing valid-dimension cases still pass.
- `just check` passes.

**Test notes.** Cover both `reduce_fraction(0, 0)` at the unit level and the `[youtube ID 0 0]` directive at the stage level, since the guard could live in either place.

### R4: Unify the Two Highlight Regexes and Make the Literal-Marker Promise True (Medium)

**Defect.** Two divergences in the `<^>...<^>` highlight feature, one fix.
First, the escape guard is inconsistent across consumers: `_ESCAPED_HIGHLIGHT_RE` (`highlight.py:16`, post stage) and `_PROSE_HIGHLIGHT_RE` (`highlight.py:23`, pre stage) both carry the `(?<!\\)` guard, but the base `_HIGHLIGHT_PATTERN` at `highlight.py:14` lacks it.
On input `a \<^>x\<^> b`, the two consumers disagree: `mw render` emits `\<mark>x\</mark>` while `mw pre` and `mw pre | post` emit the literal `a <^>x<^> b`.
Because the in-process render does not preserve the `\<^>` escape as a literal marker, the design-spec claim at spec.md:200 ("The `\<^>` escape survives both stages and renders as a literal marker, as it does in-process today") is false.
Second, the pre stage highlights markers inside tilde-delimited code fences: `_CODE_REGION_RE` at `highlight.py:28-31` recognizes only backtick fences, so `~~~ ... <^>x<^> ... ~~~` emits `<mark>` inside code while the backtick fence is correctly skipped.
Verified both.
(Findings C1 and P3.)

**Root cause.** The highlight feature grew three regexes that should share one contract; the escape guard and the code-region awareness were added to some consumers and not others.

**Required behavior.** The escape guard and the code-region skipping are unified so every highlight consumer agrees on the same two rules: `\<^>` is a literal escaped marker that is never wrapped, and markers inside any fenced code region (backtick or tilde) are left for the post stage, never highlighted by the pre stage.
`_CODE_REGION_RE` recognizes tilde fences as well as backtick fences.
The spec.md:200 literal-marker promise is made true: the escape renders as a literal marker consistently across `mw render`, `mw pre`, and `mw pre | post`.
If parity with the in-process render cannot deliver the literal marker on every path, the requirement is instead to record the corrected promise in the Decisions section (D3) and reconcile the two consumers on the achievable behavior; the false claim must not survive either way.

**Acceptance criteria.**
- A pytest case asserts `a \<^>x\<^> b` produces identical highlight output across `mw render`, `mw pre`, and `mw pre | post` (a literal marker, no `<mark>`), and fails against the pre-fix code.
- A pytest case asserts `<^>x<^>` inside a `~~~` tilde fence is not wrapped by the pre stage, matching the backtick-fence behavior.
- The three regexes share the escape guard (no consumer lacks it); a code-level or table-driven test pins that the escaped, raw, and base patterns agree.
- Either the literal-marker behavior at spec.md:200 holds on every path, or Decision D3 records the corrected promise; no doc contains a false literal-marker claim.
- `just check` passes.

**Test notes.** Drive all three consumers from one parametrized test so a future divergence fails loudly.
The step-55 note records the exact divergent outputs to assert against.

### R5: Restore or Document Single-Image Slideshow Parity (Medium-low)

**Defect.** `slideshow.py:37` requires `len(urls) >= 2`, so a single-image slideshow is dropped.
Upstream `slideshow.js:82` rejects only `!images.length`, accepting one or more images.
(Finding C2.)

**Root cause.** The port tightened the minimum image count from one to two.

**Required behavior.** Resolve per Decision D1 below.
If D1 chooses code parity, `slideshow.py:37` accepts one or more images (`len(urls) >= 1`), matching upstream.
If D1 chooses to document the divergence, the design intent (a slideshow needs at least two slides) is stated in the slideshow docs and this stays as a deliberate, recorded difference.
Do not change the code blindly ahead of D1.

**Acceptance criteria.**
- If code parity: a pytest case asserts a single-image `[slideshow URL]` produces the same markup shape upstream would, and the two-image case is unchanged.
- If documented divergence: the slideshow docs state the two-image minimum and the reason, and a test pins the `>= 2` behavior as intentional.
- `just check` passes.

**Test notes.** Blocked on D1; land the Decision first.

### R6: Restore or Document Twitter URL Grammar Parity (Medium-low)

**Defect.** The Twitter directive regex mandates a scheme, forbids `www.`, and requires a full URL.
Upstream `twitter.js:89` makes the scheme, `www.`, and prefix optional and accepts a bare `user/status/id`.
(Finding C3.)

**Root cause.** The port narrowed the accepted input grammar.

**Required behavior.** Resolve per Decision D2 below (paired with R7's regex half).
If D2 chooses code parity, the Twitter regex accepts the optional scheme, optional `www.`, and bare `user/status/id` forms upstream accepts.
If D2 chooses to keep the stricter grammar, the accepted input is documented in the twitter docs as a deliberate narrowing.
Do not change the code blindly ahead of D2.

**Acceptance criteria.**
- If code parity: pytest cases assert each upstream-accepted form (scheme-less, `www.`-prefixed, bare `user/status/id`) produces the expected blockquote, and fail against the pre-fix regex.
- If documented divergence: the twitter docs state the required URL grammar, and a test pins it.
- `just check` passes.

**Test notes.** Blocked on D2; pair with R7.

### R7: Fix the Instagram Permalink and Resolve Shortcode Grammar Parity (Medium-low)

**Defect.** Two divergences.
First, output format: `instagram.py:87` reuses the raw input URL for `data-instgrm-permalink`, while upstream `instagram.js:170` forces `https://www.instagram.com/p/${post}`.
The upstream embed script (`embed.js`) needs the `www` host, so the raw-URL permalink is an output-format defect.
Second, input grammar: the Instagram regex at `instagram.py:15` requires a full URL and rejects the shortcodes upstream `instagram.js:89` accepts.
(Finding C4.)

**Root cause.** The port both changed the emitted permalink and narrowed the accepted input, the same grammar narrowing as R6.

**Required behavior.** The permalink half is firm change-code (output format, Global Requirement 1): `instagram.py:87` emits `https://www.instagram.com/p/${post}` for `data-instgrm-permalink`, matching upstream, so the embed script resolves.
The shortcode-acceptance half is input grammar and is resolved per Decision D2 (paired with R6): if D2 chooses code parity, the regex accepts bare shortcodes as upstream does; if D2 keeps the stricter grammar, the accepted input is documented.

**Acceptance criteria.**
- A pytest case asserts the emitted `data-instgrm-permalink` is the normalized `https://www.instagram.com/p/${post}` form for a valid input, and fails against the pre-fix code.
- The shortcode-grammar cases follow D2 (parity test or documented-narrowing test), same shape as R6.
- `just check` passes.

**Test notes.** Split the test file into the firm permalink assertion (land now) and the D2-gated grammar assertions (land with the Decision).

### R8: Match the Compare SVG to Upstream (Low)

**Defect.** `image_compare.py:18-23` emits a `viewBox 0 0 100 100` two-polygon SVG; upstream `compare.js:110` emits a `viewBox 0 0 512 512` single-path SVG.
(Finding C5.)

**Root cause.** The port drew a different handle icon than upstream.

**Required behavior.** The emitted compare SVG matches upstream: `viewBox 0 0 512 512`, single path (Global Requirement 1, output format).

**Acceptance criteria.**
- A pytest case asserts the emitted SVG has the upstream `viewBox` and path, and fails against the pre-fix two-polygon markup.
- `just check` passes.

**Test notes.** Copy the exact path data from `compare.js:110`.

### R9: Match the Slideshow Nav JavaScript to Upstream (Low)

**Defect.** `slideshow.py:113-115` emits `parentElement.querySelector('.slides').scrollBy(+/-width, 0)`; upstream `slideshow.js:112-113` emits a `getElementsByClassName[0].scrollLeft += / -= width` IIFE.
(Finding C6.)

**Root cause.** The port rewrote the nav handler instead of porting it.

**Required behavior.** The emitted nav JavaScript matches upstream's `scrollLeft` IIFE form (Global Requirement 1, output format).

**Acceptance criteria.**
- A pytest case asserts the emitted nav script matches the upstream shape, and fails against the pre-fix `scrollBy` form.
- `just check` passes.

**Test notes.** Assert on the emitted string; this is a pure output comparison.

### R10: Fix the image_compare Token in the Spec and README (Low, Doc Fix)

**Defect.** The author-facing token is `[compare ...]` (`image_compare.py:13`, `docs/extensions/image-compare.md:19`), matching upstream.
The registered name `image_compare` (`registry.py:45`) is internal only.
The design-spec Stage Matrix at spec.md:66 and `README.md:141` tell the reader to write `[image_compare ...]`, which renders nothing when copy-pasted.
(Finding C7.)

**Root cause.** The Stage Matrix and README used the internal registry name instead of the author-facing token.

**Required behavior.** The reader-facing examples use the working `[compare ...]` token.
`README.md:141` is corrected to `[compare ...]`.
The old design-spec Stage Matrix row at spec.md:66 stays frozen in history; since this remediation spec replaces spec.md at the root, any surviving Stage Matrix reference here uses the correct token, and the correction is noted in the Decisions section.

**Acceptance criteria.**
- `README.md:141` reads `[compare before.jpg after.jpg]` (or equivalent), and a copy-paste of that example through `mw render` produces the compare markup.
- No reader-facing doc instructs the author to write `[image_compare ...]`; a grep over `README.md` and `docs/` for the author-facing `[image_compare` token returns nothing.
- `just check` passes (docs edits do not break the gate).

**Test notes.** Pure doc fix; the grep probe plus a render of the corrected example is the test.

### R11: Fix the Packaging Polish for Publish (Low)

**Defect.** `pyproject.toml:31` pins `uv_build>=0.9.17,<0.10.0`, which excludes the installed uv 0.10.9 and makes `uv build` warn.
The package also lacks `classifiers`, `[project.urls]`, and `keywords`.
(Finding P4.)

**Root cause.** The build-backend pin was written against an older uv and the publish metadata was never filled in.

**Required behavior.** `uv build` runs without the version-pin warning, and the package carries the metadata a publish expects.
Widen or update the `uv_build` pin to admit current uv, and add `classifiers`, `[project.urls]`, and `keywords` to `[project]`.

**Acceptance criteria.**
- `uv build` completes with no build-backend version warning.
- `pyproject.toml` has non-empty `classifiers`, `[project.urls]`, and `keywords`.
- `just check` passes.

**Test notes.** Land with R2 (both are packaging changes verified from the built wheel).

## Decisions

These parity items carry a "change-spec defensible" direction from the step-55 verification.
They are not written as blind code requirements; each needs a decision before its requirement's code path is chosen.
Route them through `/bpe:brainstorm`.

- **D1 (drives R5): single-image slideshow.** Upstream accepts one or more images; markwright requires two (`slideshow.py:37` vs `slideshow.js:82`).
  Decide: restore `>= 1` for strict upstream parity, or keep `>= 2` as a deliberate design choice (a slideshow needs at least two slides) and document it.
  The verifier called the change-spec (document) direction acceptable and change-code the strict-parity option.
- **D2 (drives R6 and R7's grammar half): embed URL grammar.** Upstream accepts scheme-less, `www.`-optional, and bare `user/status/id` or shortcode forms for Twitter and Instagram; markwright's regexes require full URLs (`twitter.js:89`, `instagram.js:89` vs the twitter regex, `instagram.py:15`).
  Decide once for both embeds: restore the permissive upstream grammar (change-code, the verifier's preferred direction), or keep the stricter full-URL grammar as a documented input contract (change-spec, defensible).
  R7's permalink half (`data-instgrm-permalink` normalization) is not part of this decision; it is firm change-code regardless.
- **D3 (drives R4's fallback): the literal-marker promise.** spec.md:200 promises `\<^>` renders as a literal marker consistently, which the in-process render does not currently deliver.
  Preferred resolution is to make it true (unify the regexes so every path preserves the literal marker).
  If some path cannot deliver it under Python-Markdown, decide the corrected promise here and reconcile the consumers on the achievable behavior.

## Open Questions

None block the fixes.
The three Decisions above gate only R5, the grammar half of R6 and R7, and the fallback branch of R4; the firm requirements (R1, R2, R3, the R4 unification, R7's permalink, R8, R9, R10, R11) proceed without them.

## Component Boundaries

Each requirement is independently implementable, with these batching notes:

- R1 stands alone and lands first; it is the release blocker.
- R2 and R11 are one packaging pass, both verified from the built wheel in a clean venv.
- R4 unifies three regexes across two consumers; land C1 and P3 together since they share the fix.
- R6 and R7's grammar half share Decision D2; land them together once D2 resolves.
- R8, R9, and R10 are independent low-severity output and doc fixes.

## Verification

The cycle is done when:

1. Every acceptance criterion above has a passing test or probe, observed failing first where behavior changed.
2. `just check` passes (test, lint, typecheck; 100 percent line and branch coverage).
3. The two XSS probes (R1) render inert and are committed as regression tests.
4. The clean-venv `mw render` check (R2) passes against a freshly built wheel with no dev dependencies.
5. Decisions D1, D2, and D3 are resolved before R5, the R6/R7 grammar half, and the R4 fallback land.

## Review Record

Kept for auditability of the step-55 verification (`.ai-sessions/step-55-do-markdown-verified.md`): 12 confirmed, 0 refuted.

Concurred non-defects (no requirement issued):

- Slideshow and compare image `src` values are not scheme-validated, but they are attribute-escaped and sit in a non-navigation context.
- Twitter and Instagram scripts drop `type="text/javascript"`; the v1 plan omitted it deliberately, a strict-parity nit only.
- `requires-python >= 3.14` with 3.10-compatible code is deliberate.
- The deselected integration test runs in CI.
- `uv build` is otherwise correct (the only issue is the version pin, R11).
