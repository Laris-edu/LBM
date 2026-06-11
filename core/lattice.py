"""Lattice family registry for Phase 2 velocity-set migration."""

from __future__ import annotations

from typing import Protocol

import numpy as np

from core.lattice_d2q21 import THETA_Q as THETA_Q_D2Q21
from core.lattice_d2q21 import LatticeD2Q21, make_d2q21
from core.lattice_d2q37 import THETA_Q_D2Q37, LatticeD2Q37, make_d2q37


class Lattice(Protocol):
    c: np.ndarray
    w: np.ndarray
    theta_q: float
    opposite: np.ndarray
    q: int
    d: int


LatticeFamily = LatticeD2Q21 | LatticeD2Q37

_CANONICAL_NAMES = {
    "D2Q21": "D2Q21",
    "D2Q37": "D2Q37",
}


def normalize_velocity_set(value: str | None) -> str:
    name = "D2Q21" if value is None else str(value).strip().upper()
    if name not in _CANONICAL_NAMES:
        raise ValueError(f"unsupported velocity_set: {value}")
    return _CANONICAL_NAMES[name]


def make_lattice(velocity_set: str | None = None, dtype=np.float64) -> LatticeFamily:
    name = normalize_velocity_set(velocity_set)
    if name == "D2Q21":
        return make_d2q21(dtype=dtype)
    if name == "D2Q37":
        return make_d2q37(dtype=dtype)
    raise ValueError(f"unsupported velocity_set: {velocity_set}")


def lattice_family(lattice: Lattice) -> str:
    if lattice.q == 21 and lattice.d == 2:
        return "D2Q21"
    if lattice.q == 37 and lattice.d == 2:
        return "D2Q37"
    raise ValueError(f"unsupported lattice shape: Q={lattice.q}, D={lattice.d}")


def default_theta_q(velocity_set: str | None = None) -> float:
    name = normalize_velocity_set(velocity_set)
    if name == "D2Q21":
        return THETA_Q_D2Q21
    if name == "D2Q37":
        return THETA_Q_D2Q37
    raise ValueError(f"unsupported velocity_set: {velocity_set}")


def default_q(velocity_set: str | None = None) -> int:
    return make_lattice(velocity_set).q
