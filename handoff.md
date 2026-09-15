# markwright Remediation Handoff

This is the baton for the markwright remediation cycle.
Start here with no other context.
markwright ports DigitalOcean's `do-markdownit` into Python-Markdown extensions plus an `mw` CLI, and a portfolio audit (step 55) confirmed 12 defects against the built code.
`spec.md` is the reviewed remediation spec (requirements R1 through R11, Decisions D1, D2, D3).
`plan.md` is the TDD roadmap that turns those requirements into ordered steps.

## Current State

- Branch: `portfolio-audit` (not `main`; never commit to `main`).
- `spec.md`: the reviewed remediation spec, committed. Do not edit it. It is frozen for the audit cycle, and "spec.md:N" citations inside it mean `git show main:spec.md` line N.
- `plan.md`: present at the repo root. As of this handoff it is an uncommitted working-tree modification in Mason's tree. Leave it for Mason to commit; do not stage or revert it.
- Fixes done: 0. Nothing in the plan has started (`plan.md` Current Status is "not started").

## The Green-Gate Irony

The repo has a gate, `just check` (pytest at 100 percent line and branch coverage, plus ruff and mypy strict).
That gate is green on the current tree.
It still shipped a stored XSS hole, an `mw render` that dies in every clean install, and a build-aborting crash on a benign input.
It missed all 12 defects for one reason: no test ever fed the triggering input.
There was no XSS probe through the fence marker, no clean-venv install check, and no zero-dimension embed case.
Every requirement in the plan therefore adds the regression test or probe that would have caught its defect, so the class of bug that slipped through starts getting caught.
The lesson to carry: a fix does not land without the triggering input under test.

## Fix Order

Work the plan in order.
The ordering is load-bearing, not cosmetic.

1. **R1: the stored XSS, first (Step 1).**
   `fence.py:232` serializes directive values into an HTML comment with `json.dumps`, which does not escape `>`, `<`, or `-`, so a directive value containing ` --> ` closes the `mw-fence` comment early and injects live markup.
   It reproduces on both the in-process `mw render` path and the `mw pre | render | mw post` path.
   Acceptance: the two reproduced breakout inputs render inert.
   Use the step-55 probe verbatim, `[label foo --> <script>alert(1)</script>]` above a fenced block, and commit one pytest regression per path asserting the injected `<script>` appears only escaped or not at all, failing against pre-fix code.
   Add a round-trip test that a benign label with a `>` or a `-` still styles its block, so the fix does not over-escape.

2. **The two clean-install blockers, next (Steps 2 and 3).**
   R2 (Step 2): `mw render` raises `ModuleNotFoundError: No module named 'pymdownx'` from the built wheel because `pymdown-extensions` is declared only in the dev group.
   Move it to runtime `dependencies` in `pyproject.toml` and add a clean-venv install probe (marked `integration`, runs in CI, not in the local gate) that builds the wheel, installs it with no dev group, and asserts `mw render` exits 0.
   R11 rides along in Step 2 (widen the `uv_build` pin, add classifiers, urls, keywords).
   R3 (Step 3): `[youtube ID 0 0]` (or any zero or negative dimension) hits `reduce_fraction` with `math.gcd(0, 0) = 0` and raises `ZeroDivisionError`, which aborts a whole MkDocs build in-process.
   Guard both `reduce_fraction` in `_util.py` and the youtube parser; the chosen fallback is the default 16:9 aspect ratio, and the test asserts the fallback, not just the absence of a traceback.

3. **Correctness and parity, after the blockers (Steps 4 through 10).**
   R4 unifies the three highlight regexes, adds tilde-fence awareness, and makes the literal-marker promise true (D3 is a contingency inside this step).
   R7a normalizes the Instagram permalink (firm half).
   R8 and R9 match the compare SVG and the slideshow nav JS to upstream.
   R10 fixes the `[image_compare ...]` token to the working `[compare ...]` in the README and docs.
   Steps 9 and 10 are the brainstorm-gated parity items (below); their Decision must be recorded before their code lands.

## Decisions Carried to Mason

Three parity items are decisions for Mason, not silent implementer picks.
Each is routed through `/bpe:brainstorm` and its outcome recorded in the `spec.md` Decisions section before the gated code lands.

- **D1 (gates R5, Step 9): single-image slideshow.**
  Upstream accepts one or more images; markwright's `slideshow.py:37` requires two.
  Decide: restore `>= 1` for strict upstream parity, or keep `>= 2` as a deliberate design choice (a slideshow needs at least two slides) and document it.
- **D2 (gates R6 and R7's grammar half, Step 10): embed URL grammar.**
  Upstream accepts scheme-less, `www.`-optional, and bare `user/status/id` or shortcode forms for Twitter and Instagram; markwright's regexes require full URLs.
  Decide once for both embeds: restore the permissive upstream grammar, or keep the stricter full-URL grammar as a documented input contract.
  R7's permalink normalization is firm change-code and is not part of this decision (it lands in Step 5).
- **D3 (folded into R4, Step 4): the literal-marker promise.**
  `spec.md:200` promises `\<^>` renders as a literal marker consistently, which the in-process render does not currently deliver.
  Preferred resolution is to make it true by unifying the regexes; only if some path cannot deliver the literal marker under Python-Markdown does D3 record a corrected promise and reconcile the consumers.
  The false claim must not survive either branch.

## Known Risks

- The clean-venv probe (R2) cannot run inside `just check`, because the dev group already has `pymdownx`, which is exactly what masked the bug; it must run in the CI integration job or it catches nothing.
- Coverage stays at 100 percent line and branch; the new branches (R1 payload escaping, R3 zero and negative guards, R4 tilde and escape paths) each need their own case, since a line-only pass will not exercise them.
- R4 crosses two consumers over three regexes; drive all three consumers (`mw render`, `mw pre`, `mw pre | post`) from one parametrized test so a future divergence fails loudly.
- Do not modify existing per-extension test classes that pin unchanged in-process behavior; add new classes alongside them, except where an existing test encodes the defect being fixed (updating it is the red step).
- Steps 9 and 10 are blocked until D1 and D2 are recorded in `spec.md`; do not write branch code ahead of the Decision.

## Next Action

Start Step 1 in `plan.md`: load the `python` skill, then write the failing XSS regression tests in `tests/test_fence.py` using the step-55 probe verbatim, confirm they fail against current code, then implement the fence marker escaping in `src/markwright/fence.py`.
