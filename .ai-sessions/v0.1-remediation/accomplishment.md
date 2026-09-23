# Accomplishment: markwright step-55 Remediation (R1-R11)

**Archived**: 2026-09-16
**Convergence**: converged (all 11 requirements landed, shipped as 0.1.0)

## Spec Slice

The step-55 audit remediation: fix the 12 confirmed defects in the built markwright extensions and CLI, each with the regression test or probe that would have caught it, holding output to upstream do-markdownit parity unless a Decision documented a divergence.

## What Got Done

- R1: closed the stored XSS in the fence marker comment.
- R2 + R11: moved pymdown-extensions to a runtime dependency (fixes `mw render` in a clean install); publish metadata; clean-venv install probe.
- R3: guarded zero and negative youtube dimensions.
- R4: unified the highlight regexes across all consumers; made the literal-marker promise true (D3); tilde-fence awareness.
- R5: single-image slideshows accepted (D1, upstream parity).
- R6 + R7: Instagram permalink normalized; permissive Twitter/Instagram URL grammar (D2).
- R8, R9, R10: compare SVG, slideshow nav JS, and the README `[compare]` token matched to upstream.
- Shipped as markwright 0.1.0 on PyPI; CI moved to a 3.11-3.14 matrix off Node 20; docs reframed.

## Deferred or Dropped

- None from the remediation scope. Follow-on work (a config system, CLI selection simplification) is a separate 0.2.0 cycle.

## Notable Decisions

- D1: slideshow accepts one or more images (upstream parity).
- D2: restore the permissive upstream URL grammar for both embeds.
- D3: the literal-marker promise was made true by unifying the regexes, not corrected.
- Python floor set to 3.11 (3.10 EOLs 2026-10); license stays MIT with the ported portions attributed under Apache-2.0 in NOTICE.

## Files Touched

- src/markwright/: fence.py, _util.py, youtube.py, highlight.py, instagram.py, twitter.py, image_compare.py, slideshow.py
- tests/: the matching test files plus test_util.py, test_docs_tokens.py, tests/integration/test_clean_install.py
- pyproject.toml, .github/workflows/, docs/, README.md, NOTICE, LICENSE-Apache-2.0

## Lessons Cross-Reference

- See `.ai-sessions/lessons.md` entries dated 2026-09-07 and 2026-09-08 (todo.md regeneration, dev-group blindness, reduce_fraction totality, JSON-in-comment escaping, cross-consumer parity testing) and 2026-09-14/15/16 (release prep, action-tag resolution).
