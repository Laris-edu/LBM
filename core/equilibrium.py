"""Moment-matched Hermite equilibrium distributions for Phase 2."""

from __future__ import annotations

from functools import lru_cache

import numpy as np

from core.hermite import monomial_exponents
from core.lattice_d2q21 import LatticeD2Q21, make_d2q21


def _normal_raw_moment_1d(order: int, mean: np.ndarray, theta: np.ndarray) -> np.ndarray:
    if order == 0:
        return np.ones_like(mean, dtype=float)
    if order == 1:
        return mean
    if order == 2:
        return mean**2 + theta
    if order == 3:
        return mean**3 + 3.0 * mean * theta
    if order == 4:
        return mean**4 + 6.0 * mean**2 * theta + 3.0 * theta**2
    raise ValueError("moments above fourth order are not used in equilibrium")


def gaussian_raw_moment_targets(
    rho_like: np.ndarray,
    u: np.ndarray,
    theta: np.ndarray,
    max_order: int,
) -> np.ndarray:
    """Return raw Gaussian moment targets for all monomials through max order."""

    rho_like = np.asarray(rho_like, dtype=float)
    u = np.asarray(u, dtype=float)
    theta = np.asarray(theta, dtype=float)
    targets = []
    ux = u[..., 0]
    uy = u[..., 1]
    for m, n in monomial_exponents(max_order):
        mx = _normal_raw_moment_1d(m, ux, theta)
        my = _normal_raw_moment_1d(n, uy, theta)
        targets.append(rho_like * mx * my)
    return np.stack(targets, axis=-1)


@lru_cache(maxsize=None)
def _moment_solution_matrix(max_order: int) -> tuple[np.ndarray, tuple[tuple[int, int], ...]]:
    lattice = make_d2q21()
    exponents = tuple(monomial_exponents(max_order))
    a = []
    cx = lattice.c[:, 0]
    cy = lattice.c[:, 1]
    for m, n in exponents:
        a.append(cx**m * cy**n)
    matrix = np.asarray(a, dtype=float)
    # The minimum-norm solution map for A f = b.  The monomial rows contain
    # symmetry-induced linear dependencies on D2Q21, so use the Moore-Penrose
    # pseudo-inverse rather than assuming full row rank.
    solution = np.linalg.pinv(matrix)
    return solution, exponents


def _solve_moment_matched(targets: np.ndarray, max_order: int) -> np.ndarray:
    solution, _ = _moment_solution_matrix(max_order)
    return np.einsum("...m,am->...a", targets, solution)


def feq_hermite4(
    rho: np.ndarray,
    u: np.ndarray,
    theta: np.ndarray,
    lattice: LatticeD2Q21 | None = None,
) -> np.ndarray:
    """Fourth-order Hermite/moment-matched equilibrium for ``f``.

    ``theta`` is the thermodynamic lattice temperature.  The D2Q21
    quadrature temperature remains available from ``lattice.theta_q`` and is
    not used as a thermodynamic substitute.
    """

    lattice = lattice or make_d2q21()
    del lattice
    targets = gaussian_raw_moment_targets(rho, u, theta, max_order=4)
    return _solve_moment_matched(targets, max_order=4)


def geq_polyatomic(
    rho: np.ndarray,
    u: np.ndarray,
    theta: np.ndarray,
    S: float,
    lattice: LatticeD2Q21 | None = None,
    order: int = 2,
) -> np.ndarray:
    """Polyatomic internal-energy equilibrium for ``g``.

    The zero moment is ``(S/2) rho theta`` and the default moment recovery is
    second order, as required by the Phase 2 contract.
    """

    if order < 2 or order > 4:
        raise ValueError("g equilibrium order must be 2, 3, or 4")
    lattice = lattice or make_d2q21()
    del lattice
    e_int_extra = 0.5 * float(S) * np.asarray(rho, dtype=float) * np.asarray(theta, dtype=float)
    targets = gaussian_raw_moment_targets(e_int_extra, u, theta, max_order=order)
    return _solve_moment_matched(targets, max_order=order)


def equilibrium_fg(
    rho: np.ndarray,
    u: np.ndarray,
    theta: np.ndarray,
    S: float,
    lattice: LatticeD2Q21 | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    lattice = lattice or make_d2q21()
    return feq_hermite4(rho, u, theta, lattice), geq_polyatomic(rho, u, theta, S, lattice)


def raw_moments(distribution: np.ndarray, lattice: LatticeD2Q21 | None = None, max_order: int = 4) -> dict[tuple[int, int], np.ndarray]:
    lattice = lattice or make_d2q21()
    f = np.asarray(distribution, dtype=float)
    cx = lattice.c[:, 0]
    cy = lattice.c[:, 1]
    out: dict[tuple[int, int], np.ndarray] = {}
    for m, n in monomial_exponents(max_order):
        out[(m, n)] = np.sum(f * (cx**m * cy**n), axis=-1)
    return out
