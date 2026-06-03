"""Polyatomic f-g helpers for Phase 2 air."""

from __future__ import annotations


def internal_degrees_of_freedom(gamma: float, D: int = 2) -> float:
    """Return ``S = 2/(gamma-1) - D``."""

    return 2.0 / (float(gamma) - 1.0) - float(D)


def gamma_from_degrees(D: int = 2, S: float = 3.0) -> float:
    return 1.0 + 2.0 / (float(D) + float(S))


def assert_air_degrees(D: int = 2, gamma: float = 1.4, tol: float = 1.0e-12) -> None:
    S = internal_degrees_of_freedom(gamma, D)
    recovered = gamma_from_degrees(D, S)
    if abs(recovered - gamma) > tol:
        raise AssertionError(f"gamma reconstruction failed: {recovered} != {gamma}")
