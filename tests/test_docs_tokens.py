# ABOUTME: Tests that reader-facing docs use the working [compare ...] directive token.
# Guards against the internal registry name "image_compare" leaking into copy-paste examples.

from __future__ import annotations

from pathlib import Path

from markwright.image_compare import expand_source

REPO_ROOT = Path(__file__).resolve().parent.parent
STALE_DIRECTIVE = "[image_compare "


def _doc_files() -> list[Path]:
    """Return README.md and every file under docs/.

    :returns: List of paths to scan for reader-facing example text.
    """
    doc_files = [REPO_ROOT / "README.md"]
    doc_files.extend(sorted((REPO_ROOT / "docs").rglob("*")))
    return [doc_file for doc_file in doc_files if doc_file.is_file()]


class TestAuthorFacingCompareToken:
    """Tests that the author-facing compare directive is [compare ...], not [image_compare ...]."""

    def test_no_stale_directive_form_in_docs(self) -> None:
        offending_files = []
        for doc_file in _doc_files():
            text = doc_file.read_text(encoding="utf-8")
            if STALE_DIRECTIVE in text:
                offending_files.append(str(doc_file.relative_to(REPO_ROOT)))
        assert offending_files == []

    def test_corrected_example_renders_compare_markup(self) -> None:
        result = expand_source("[compare before.jpg after.jpg]")
        assert '<div class="image-compare"' in result
