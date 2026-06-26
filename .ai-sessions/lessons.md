# Lessons Learned

## Recent
<!-- 10 most recent lessons, newest first -->
- When a coverage gap points at one line, trace it to the exact code path before writing the test — `highlight.py:36` lived in the postprocessor's `_wrap_highlight_segments`, not the inline path that an existing empty-marker test already covered (2026-06-26)
- Adding a parallel code path for an existing behavior needs its own test even when an analogous test exists for the old path (2026-06-26)

## Testing
- When a coverage gap points at one line, trace it to the exact code path before writing the test — a same-looking input may exercise a different path (2026-06-26)
- Adding a parallel code path for an existing behavior needs its own test even when an analogous test exists for the old path (2026-06-26)

## Tooling
- `.coverage` is a tracked binary artifact in this repo that shows as modified after every test run; do not stage it (2026-06-26)
