"""Hermite helpers for the Phase 2 D2Q21 implementation."""

from __future__ import annotations

from functools import lru_cache

import numpy as np

from core.lattice_d2q21 import LatticeD2Q21, make_d2q21


def hermite_0(c: np.ndarray, theta_q: float) -> np.ndarray:
    return np.ones(c.shape[:-1], dtype=float)


def hermite_1(c: np.ndarray, theta_q: float) -> np.ndarray:
    return np.asarray(c, dtype=float)


def hermite_2(c: np.ndarray, theta_q: float) -> np.ndarray:
    c = np.asarray(c, dtype=float)
    eye = np.eye(c.shape[-1], dtype=float)
    return c[..., :, None] * c[..., None, :] - theta_q * eye


def hermite_3(c: np.ndarray, theta_q: float) -> np.ndarray:
    c = np.asarray(c, dtype=float)
    d = c.shape[-1]
    out = c[..., :, None, None] * c[..., None, :, None] * c[..., None, None, :]
    eye = np.eye(d, dtype=float)
    for i in range(d):
        for j in range(d):
            for k in range(d):
                out[..., i, j, k] -= theta_q * (
                    c[..., i] * eye[j, k] + c[..., j] * eye[i, k] + c[..., k] * eye[i, j]
                )
    return out


def hermite_4(c: np.ndarray, theta_q: float) -> np.ndarray:
    c = np.asarray(c, dtype=float)
    d = c.shape[-1]
    out = (
        c[..., :, None, None, None]
        * c[..., None, :, None, None]
        * c[..., None, None, :, None]
        * c[..., None, None, None, :]
    )
    eye = np.eye(d, dtype=float)
    for i in range(d):
        for j in range(d):
            for k in range(d):
                for ell in range(d):
                    out[..., i, j, k, ell] -= theta_q * (
                        c[..., i] * c[..., j] * eye[k, ell]
                        + c[..., i] * c[..., k] * eye[j, ell]
                        + c[..., i] * c[..., ell] * eye[j, k]
                        + c[..., j] * c[..., k] * eye[i, ell]
                        + c[..., j] * c[..., ell] * eye[i, k]
                        + c[..., k] * c[..., ell] * eye[i, j]
                    )
                    out[..., i, j, k, ell] += theta_q**2 * (
                        eye[i, j] * eye[k, ell]
                        + eye[i, k] * eye[j, ell]
                        + eye[i, ell] * eye[j, k]
                    )
    return out


def monomial_exponents(max_order: int) -> list[tuple[int, int]]:
    """Return 2D monomial exponents with total degree <= ``max_order``."""

    return [(m, total - m) for total in range(max_order + 1) for m in range(total + 1)]


@lru_cache(maxsize=None)
def moment_matrix(max_order: int, q: int = 21) -> tuple[np.ndarray, tuple[tuple[int, int], ...]]:
    lattice = make_d2q21()
    if q != lattice.q:
        raise ValueError("only D2Q21 is supported")
    exponents = tuple(monomial_exponents(max_order))
    rows = []
    cx = lattice.c[:, 0]
    cy = lattice.c[:, 1]
    for m, n in exponents:
        rows.append(cx**m * cy**n)
    return np.asarray(rows, dtype=float), exponents


def project_raw_moments(distribution: np.ndarray, max_order: int, lattice: LatticeD2Q21 | None = None) -> dict[tuple[int, int], np.ndarray]:
    lattice = lattice or make_d2q21()
    values: dict[tuple[int, int], np.ndarray] = {}
    cx = lattice.c[:, 0]
    cy = lattice.c[:, 1]
    f = np.asarray(distribution, dtype=float)
    for m, n in monomial_exponents(max_order):
        values[(m, n)] = np.sum(f * (cx**m * cy**n), axis=-1)
    return values


def assert_discrete_orthogonality(tol: float = 1.0e-12) -> None:
    lattice = make_d2q21()
    c = lattice.c
    w = lattice.w
    h1 = hermite_1(c, lattice.theta_q)
    h2 = hermite_2(c, lattice.theta_q)
    if np.max(np.abs(np.sum(w[:, None] * h1, axis=0))) > tol:
        raise AssertionError("first-order Hermite mean is not zero")
    h1h1 = np.einsum("a,ai,aj->ij", w, h1, h1)
    if np.max(np.abs(h1h1 - lattice.theta_q * np.eye(2))) > tol:
        raise AssertionError("first-order Hermite orthogonality failed")
    if np.max(np.abs(np.einsum("a,aij->ij", w, h2))) > tol:
        raise AssertionError("second-order Hermite mean is not zero")
