"""Frozen D2Q21 multispeed lattice for Phase 2.

Array layout is part of the Phase 2 contract:

* ``c`` has shape ``(Q, D) == (21, 2)`` and columns ``(cx, cy)``.
* ``w`` has shape ``(Q,)`` and uses the same velocity-axis order as ``c``.
* Distribution arrays ``f`` and ``g`` use velocity as the last axis.

The quadrature validation is deliberately stated as even raw moments through
sixth order plus odd-symmetry checks through seventh order.  It does not claim
complete seventh/eighth-order quadrature.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import product

import numpy as np


THETA_Q = 2.0 / 3.0


@dataclass(frozen=True)
class LatticeD2Q21:
    c: np.ndarray
    w: np.ndarray
    theta_q: float
    opposite: np.ndarray
    q: int
    d: int


def make_d2q21(dtype=np.float64) -> LatticeD2Q21:
    """Return the frozen D2Q21 lattice in the documented velocity order."""

    c = np.array(
        [
            (0, 0),
            (1, 0),
            (-1, 0),
            (0, 1),
            (0, -1),
            (1, 1),
            (1, -1),
            (-1, 1),
            (-1, -1),
            (2, 0),
            (-2, 0),
            (0, 2),
            (0, -2),
            (2, 2),
            (2, -2),
            (-2, 2),
            (-2, -2),
            (3, 0),
            (-3, 0),
            (0, 3),
            (0, -3),
        ],
        dtype=dtype,
    )
    weights = [
        Fraction(91, 324),
        Fraction(1, 12),
        Fraction(1, 12),
        Fraction(1, 12),
        Fraction(1, 12),
        Fraction(2, 27),
        Fraction(2, 27),
        Fraction(2, 27),
        Fraction(2, 27),
        Fraction(7, 360),
        Fraction(7, 360),
        Fraction(7, 360),
        Fraction(7, 360),
        Fraction(1, 432),
        Fraction(1, 432),
        Fraction(1, 432),
        Fraction(1, 432),
        Fraction(1, 1620),
        Fraction(1, 1620),
        Fraction(1, 1620),
        Fraction(1, 1620),
    ]
    w = np.array([float(x) for x in weights], dtype=dtype)
    opposite = np.array(
        [0, 2, 1, 4, 3, 8, 7, 6, 5, 10, 9, 12, 11, 16, 15, 14, 13, 18, 17, 20, 19],
        dtype=np.int64,
    )
    return LatticeD2Q21(c=c, w=w, theta_q=THETA_Q, opposite=opposite, q=21, d=2)


def get_opposite_indices() -> np.ndarray:
    """Return the frozen opposite-velocity map."""

    return make_d2q21().opposite.copy()


def moment(exponents: tuple[int, int], lattice: LatticeD2Q21 | None = None) -> float:
    """Return ``sum_a w_a cx_a**m cy_a**n`` for the frozen lattice."""

    lattice = lattice or make_d2q21()
    m, n = exponents
    return float(np.sum(lattice.w * lattice.c[:, 0] ** m * lattice.c[:, 1] ** n))


def _assert_close(name: str, value: float, expected: float, tol: float) -> None:
    err = abs(value - expected)
    if err > tol:
        raise AssertionError(f"{name}: got {value:.17g}, expected {expected:.17g}, err={err:.3e}")


def assert_d2q21_moments(tol: float = 1.0e-12) -> None:
    """Validate the frozen D2Q21 quadrature contract."""

    lattice = make_d2q21()
    theta = lattice.theta_q
    _assert_close("M00", moment((0, 0), lattice), 1.0, tol)
    for total in range(1, 8, 2):
        for m in range(total + 1):
            n = total - m
            _assert_close(f"M{m}{n}", moment((m, n), lattice), 0.0, tol)

    targets = {
        (2, 0): theta,
        (0, 2): theta,
        (1, 1): 0.0,
        (4, 0): 3.0 * theta**2,
        (0, 4): 3.0 * theta**2,
        (2, 2): theta**2,
        (6, 0): 15.0 * theta**3,
        (0, 6): 15.0 * theta**3,
        (4, 2): 3.0 * theta**3,
        (2, 4): 3.0 * theta**3,
    }
    for exponents, expected in targets.items():
        _assert_close(f"M{exponents[0]}{exponents[1]}", moment(exponents, lattice), expected, tol)

    for i, opp in enumerate(lattice.opposite):
        if not np.allclose(lattice.c[i] + lattice.c[opp], 0.0, atol=tol, rtol=0.0):
            raise AssertionError(f"opposite[{i}]={opp} is not the negative velocity")


def even_moment_table_through_6(lattice: LatticeD2Q21 | None = None) -> dict[tuple[int, int], float]:
    """Return all nonzero even raw moments with total degree <= 6."""

    lattice = lattice or make_d2q21()
    table: dict[tuple[int, int], float] = {}
    for m, n in product(range(7), repeat=2):
        total = m + n
        if total <= 6 and total % 2 == 0:
            table[(m, n)] = moment((m, n), lattice)
    return table
