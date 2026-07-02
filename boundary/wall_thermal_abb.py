"""Boundary-aware thermal Dirichlet wall for D2Q37 (P3-5+ M3 admittance repair).

Replaces the P3-1 ``equilibrium clamp`` (which overwrites the wall row with a pure
equilibrium distribution and thereby kills the near-wall non-equilibrium heat flux,
underestimating the dynamic thermal admittance by ~38%). Here the wall is a halfway
reflection plane at ``y = -1/2`` and the wall-incoming populations (``cy>0`` pulled from
below the wall) are reconstructed *after* streaming, before the global periodic
corrections, using:

  f (no-slip, momentum): non-equilibrium bounce-back
      f_a = feq_a(rho_w, 0, T_w) + [f_post_{opp(a)}(reflected row) - feq_{opp(a)}(rho_w,0,T_w)]
  g (Dirichlet temperature): anti-bounce-back
      g_a = geq_a(rho_w, 0, T_w) - [g_post_{opp(a)}(reflected row) - geq_{opp(a)}(rho_w,0,T_w)]

The equilibrium parts are evaluated at the prescribed wall state so the recovered wall
temperature tends to ``T_w``, while the (anti)symmetric non-equilibrium parts retain the
near-wall heat flux. This is the doc §5.3 prototype; if the recovered wall temperature or
admittance is insufficient (polyatomic f/g energy coupling), escalate to the
moment-constrained reconstruction of doc §5.4.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from core.equilibrium import equilibrium_fg
from core.solver import GasSolver2D

from .wall_common import (
    BOTTOM_WALL_ROW,
    bottom_wall_stencil,
    pressure_preserving_rho,
    reflection_source_row,
)


def _wall_equilibrium(solver: GasSolver2D, rho_w: float, theta_w: float) -> tuple[np.ndarray, np.ndarray]:
    rho = np.full((1, 1), float(rho_w), dtype=float)
    u = np.zeros((1, 1, 2), dtype=float)
    theta = np.full((1, 1), float(theta_w), dtype=float)
    f_w, g_w = equilibrium_fg(rho, u, theta, solver.mapping.lattice.S, solver.lattice)
    return np.asarray(f_w[0, 0], dtype=float), np.asarray(g_w[0, 0], dtype=float)


def make_bottom_thermal_wall_callback(
    theta_wall_lu: float | Callable[[GasSolver2D], float],
    *,
    rho_policy: str = "pressure_preserving",
    row: int = BOTTOM_WALL_ROW,
):
    """Return a ``solver.step`` boundary_callback imposing a bottom thermal Dirichlet wall.

    ``theta_wall_lu`` may be a float or ``callable(solver) -> float`` (for time-varying
    wall temperature). The callback reconstructs wall-incoming (cy>0) populations at rows
    ``0..max_cy-1`` from the post-collision state, so no population wraps from the periodic
    top boundary.
    """

    if row != BOTTOM_WALL_ROW:
        raise ValueError("only the bottom wall (row 0) is supported")

    def _callback(*, solver, f_post, g_post, f_stream, g_stream):
        theta_w = float(theta_wall_lu(solver) if callable(theta_wall_lu) else theta_wall_lu)
        if theta_w <= 0.0:
            raise ValueError("wall temperature must be positive")
        if rho_policy == "pressure_preserving":
            rho_w = pressure_preserving_rho(theta_w, solver.mapping)
        elif rho_policy == "constant_density":
            rho_w = float(solver.mapping.lattice.rho_ref_lu)
        else:
            raise ValueError(f"unknown rho_policy: {rho_policy}")

        stencil = bottom_wall_stencil(solver.lattice)
        feq_w, geq_w = _wall_equilibrium(solver, rho_w, theta_w)

        f_out = f_stream
        g_out = g_stream
        for a in stencil.incoming:
            cy_a = int(stencil.cy[a])
            o = int(stencil.opposite[a])
            for y in range(cy_a):
                r = reflection_source_row(cy_a, y)  # reflected fluid row in [0, max_cy-1]
                f_out[y, :, a] = feq_w[a] + (f_post[r, :, o] - feq_w[o])
                g_out[y, :, a] = geq_w[a] - (g_post[r, :, o] - geq_w[o])
        return f_out, g_out

    return _callback
