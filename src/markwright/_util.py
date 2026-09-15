# ABOUTME: Shared utility functions and constants for markwright extensions.
# Provides fraction reduction and the permissive URL-prefix grammar used by embed extensions.

from __future__ import annotations

import math

URL_SCHEME_WWW_PREFIX = r"(?:(?:https?:)?//)?(?:www\.)?"
"""Regex fragment matching an optional ``scheme://`` and an optional ``www.``.

Shared by the Twitter and Instagram embed grammars (upstream ``twitter.js``
and ``instagram.js``), which both accept a URL prefix ranging from nothing
(a bare path) up to a full ``https://www.<host>``.
"""


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
