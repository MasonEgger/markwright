# Session 2026-07-02: Step 56, markwright Remediation Spec

## What this was

Stage P6 output of the portfolio audit for `do-markdown` (markwright).
Wrote the remediation spec that replaces `spec.md` at the repo root, built from the 12 confirmed findings in `.ai-sessions/step-55-do-markdown-verified.md` (12 confirmed, 0 refuted).
The old design spec stays in history at `git show main:spec.md`.

## Format

Followed the bartleby remediation format (reference: `git -C /home/mmegger/Code/Temporal/samples-perl show portfolio-audit:spec.md`).
Sections: Overview, Scope, Available Tooling, Global Requirements, Requirements (numbered, severity-ordered), Decisions, Open Questions, Component Boundaries, Verification, Review Record.
Each requirement carries Defect, Root cause, Required behavior, Acceptance criteria, Test notes, and cites the confirmed finding's file and line.

## Requirement-to-finding mapping (11 requirements, 12 findings)

- R1 = H1 (High): stored XSS via fence-directive comment breakout.
- R2 = P1 (Medium-high): mw render dead in every clean install (pymdownx dev-only).
- R3 = P2 (Medium-high): [youtube ID 0 0] ZeroDivisionError.
- R4 = C1 + P3 (Medium): unify the two highlight regexes (escape guard + tilde-fence awareness), make the spec.md:200 literal-marker promise true or corrected. One requirement per the writer guidance since both share the fix.
- R5 = C2 (Medium-low): single-image slideshow parity, gated on Decision D1.
- R6 = C3 (Medium-low): Twitter URL grammar parity, gated on Decision D2.
- R7 = C4 (Medium-low): Instagram permalink (firm change-code) plus shortcode grammar (gated on D2).
- R8 = C5 (Low): compare SVG output parity.
- R9 = C6 (Low): slideshow nav JS output parity.
- R10 = C7 (Low): [image_compare ...] to [compare ...] doc fix (spec.md:66, README.md:141).
- R11 = P4 (Low): packaging polish (uv_build pin, classifiers, urls, keywords).

Count by severity: High 1, Medium-high 2, Medium 1 (covers C1 and P3), Medium-low 3, Low 4.

## Decisions routed to /bpe:brainstorm

- D1: single-image slideshow (change-code parity vs change-spec document). Drives R5.
- D2: Twitter/Instagram URL grammar (change-code parity vs change-spec document). Drives R6 and R7's grammar half. R7's permalink half is firm change-code regardless.
- D3: the spec.md:200 literal-marker promise (make true, preferred, vs correct the promise). Drives R4's fallback branch.

## Key framing

The Overview states the bar (publish-candidate), names the two release blockers (R1 XSS, R2 broken clean install), and notes the project's own gate (`just check`) is green yet missed all 12, which is why every requirement carries a regression test that would have caught it.

## Tooling

Available Tooling declares python:python only; explicitly no Temporal MCP or temporal-developer skill (this is a Python repo, not Temporal).

## Commit

Branch: portfolio-audit (off main, clean tree).
Replaced spec.md with the remediation spec; wrote this session note.
`.ai-sessions/` is tracked (not gitignored), so this note is committed alongside the spec.
