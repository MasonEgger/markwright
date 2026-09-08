# ABOUTME: Shared utility functions for markwright extensions.
# Provides fraction reduction helper used by embed extensions.

from __future__ import annotations

import math


def reduce_fraction(numerator: int, denominator: int) -> tuple[int, int]:
    """Reduce a fraction to its lowest terms.

    A zero operand has no defined greatest common divisor, so the fraction is
    returned unchanged rather than raising ``ZeroDivisionError``; the caller
    decides how to treat a degenerate zero numerator or denominator.

    :param numerator: The numerator of the fraction.
    :param denominator: The denominator of the fraction.
    :returns: Tuple of (reduced numerator, reduced denominator).
    """
    if numerator == 0 or denominator == 0:
        return numerator, denominator
    divisor = math.gcd(numerator, denominator)
    return numerator // divisor, denominator // divisor
