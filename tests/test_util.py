# ABOUTME: Tests for the shared _util module.
# Validates reduce_fraction, including the degenerate zero-operand behavior.

from __future__ import annotations

from markwright._util import reduce_fraction


class TestReduceFractionBasic:
    """Tests for ordinary fraction reduction."""

    def test_reduces_to_lowest_terms(self) -> None:
        assert reduce_fraction(16, 9) == (16, 9)

    def test_reduces_common_divisor(self) -> None:
        assert reduce_fraction(100, 100) == (1, 1)


class TestReduceFractionDegenerate:
    """Tests for zero and negative operands, which must never raise."""

    def test_both_zero_returns_unchanged(self) -> None:
        assert reduce_fraction(0, 0) == (0, 0)

    def test_zero_denominator_does_not_raise(self) -> None:
        assert reduce_fraction(16, 0) == (16, 0)

    def test_zero_numerator_does_not_raise(self) -> None:
        assert reduce_fraction(0, 9) == (0, 9)

    def test_negative_numerator_does_not_raise(self) -> None:
        reduce_fraction(-16, 9)

    def test_negative_denominator_does_not_raise(self) -> None:
        reduce_fraction(16, -9)
