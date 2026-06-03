"""Periodic pull streaming for integer on-lattice D2Q21 velocities."""

from __future__ import annotations

import numpy as np

from core.lattice_d2q21 import LatticeD2Q21, make_d2q21


def pull_stream(
    distribution: np.ndarray,
    *,
    lattice: LatticeD2Q21 | None = None,
    y_axis: int = 0,
    x_axis: int = 1,
) -> np.ndarray:
    """Return periodic pull-streamed distribution.

    Velocity is the last axis.  For a standard field ``f[y, x, a]`` this
    implements

    ``f_new[y, x, a] = f_post[y - cy[a], x - cx[a], a]``.

    Equivalently, with explicit axes:

    ``f_new[..., a] = roll(f_post[..., a], shift=(cy[a], cx[a]), axes=(y_axis, x_axis))``.
    """

    lattice = lattice or make_d2q21()
    dist = np.asarray(distribution, dtype=float)
    if dist.shape[-1] != lattice.q:
        raise ValueError(f"velocity axis must be last and have length {lattice.q}")
    out = np.empty_like(dist)
    for a, (cx, cy) in enumerate(lattice.c.astype(int)):
        out[..., a] = np.roll(dist[..., a], shift=(int(cy), int(cx)), axis=(y_axis, x_axis))
    return out


def pull_stream_fg(
    f: np.ndarray,
    g: np.ndarray,
    *,
    lattice: LatticeD2Q21 | None = None,
    y_axis: int = 0,
    x_axis: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    lattice = lattice or make_d2q21()
    return (
        pull_stream(f, lattice=lattice, y_axis=y_axis, x_axis=x_axis),
        pull_stream(g, lattice=lattice, y_axis=y_axis, x_axis=x_axis),
    )
