"""Grad / regularized wet-node thermal Dirichlet wall for D2Q37 (doc §5.4, stabilized).

Both prior attempts failed: the ABB prototype over-injects energy for the polyatomic f/g
pair, and the min-norm moment reconstruction excites an unstable near-wall momentum ghost
mode. This module reconstructs the whole bottom wall row 0 as a *regularized* distribution

    f_row0 = feq(rho_w, 0, theta_w) + f1_neq
    g_row0 = geq(rho_w, 0, theta_w) + g1_neq + delta

where ``f1_neq/g1_neq`` are the NON-equilibrium parts extrapolated from the first interior
gas row (row 1) -- a physically regularized (RR) interior state, so no arbitrary ghost
content is injected (the source of the min-norm instability). Because ``feq_hermite4``
matches mass/momentum exactly, ``f1_neq`` has zero mass/momentum, so ``u = 0`` and
``rho = rho_w`` hold exactly; the uniform ``delta`` on ``g`` pins the total internal energy
to ``0.5 (D+S) rho_w theta_w`` (i.e. ``theta = theta_w`` exactly) without changing the
heat flux (``sum_a c_a = 0``). The retained ``f1_neq`` shear + f/g heat-flux non-equilibrium
lets the near-wall conductive flux persist (the equilibrium clamp killed it).

No clipping / floor / positivity repair is used.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from core.equilibrium import equilibrium_fg
from core.macroscopic import recover_macro
from core.solver import GasSolver2D

from .wall_common import BOTTOM_WALL_ROW, bottom_wall_stencil, pressure_preserving_rho


def make_bottom_grad_wall_callback(
    theta_wall_lu: float | Callable[[GasSolver2D], float],
    *,
    rho_policy: str = "pressure_preserving",
    extrap: str = "row1",
    fill_deep_links: bool = False,
    row: int = BOTTOM_WALL_ROW,
):
    """Return a ``solver.step`` boundary_callback imposing a Grad/regularized bottom wall.

    ``extrap`` selects the near-wall non-equilibrium extrapolation: ``"row1"`` (0th order,
    copy row 1) or ``"linear"`` (``2*neq1 - neq2``).
    """

    if row != BOTTOM_WALL_ROW:
        raise ValueError("only the bottom wall (row 0) is supported")

    def _callback(*, solver, f_post, g_post, f_stream, g_stream):
        lattice = solver.lattice
        D = int(solver.mapping.lattice.D)
        S = int(solver.mapping.lattice.S)
        q = int(lattice.q)
        c2 = np.sum(np.asarray(lattice.c, dtype=float) ** 2, axis=-1)  # (q,)

        theta_w = float(theta_wall_lu(solver) if callable(theta_wall_lu) else theta_wall_lu)
        if theta_w <= 0.0:
            raise ValueError("wall temperature must be positive")
        if rho_policy == "pressure_preserving":
            rho_w = pressure_preserving_rho(theta_w, solver.mapping)
        elif rho_policy == "constant_density":
            rho_w = float(solver.mapping.lattice.rho_ref_lu)
        else:
            raise ValueError(f"unknown rho_policy: {rho_policy}")

        f_w, g_w = equilibrium_fg(
            np.full((1, 1), rho_w), np.zeros((1, 1, 2)), np.full((1, 1), theta_w),
            S, lattice,
        )
        feq_w = np.asarray(f_w[0, 0], dtype=float)  # (q,)
        geq_w = np.asarray(g_w[0, 0], dtype=float)

        def interior_neq(j):
            m = recover_macro(f_stream[j:j + 1], g_stream[j:j + 1], D=D, S=S, lattice=lattice)
            feq_j, geq_j = equilibrium_fg(m.rho, m.u, m.theta, S, lattice)
            return f_stream[j:j + 1] - feq_j, g_stream[j:j + 1] - geq_j  # (1,nx,q)

        f1n, g1n = interior_neq(1)
        if extrap == "linear" and solver.ny >= 3:
            f2n, g2n = interior_neq(2)
            f_neq = 2.0 * f1n - f2n
            g_neq = 2.0 * g1n - g2n
        else:
            f_neq, g_neq = f1n, g1n

        f0 = feq_w[None, None, :] + f_neq                      # (1,nx,q); rho_w & u=0 exact
        k_tr = 0.5 * np.sum(f0 * c2, axis=-1)                  # (1,nx)  (u=0 -> |c-u|^2=|c|^2)
        g_partial = float(np.sum(geq_w)) + np.sum(g_neq, axis=-1)   # (1,nx)
        target_int = 0.5 * (D + S) * rho_w * theta_w
        delta = (target_int - k_tr - g_partial) / q           # (1,nx)
        g0 = geq_w[None, None, :] + g_neq + delta[..., None]

        f_stream[0:1] = f0
        g_stream[0:1] = g0

        # Optional: deep below-wall links for rows 1..max_cy-1 zero-gradient from the wall row.
        # Off by default -- forcing rows 1,2 specific directions to the wall value injects an
        # odd/even wall-normal mode; leaving them as the periodic-top (~far-field mean) stream
        # is smoother for small perturbations.
        if fill_deep_links:
            st = bottom_wall_stencil(lattice)
            f0row = f_stream[0].copy()
            g0row = g_stream[0].copy()
            for a in st.incoming:
                for y in range(1, int(st.cy[a])):
                    f_stream[y, :, a] = f0row[:, a]
                    g_stream[y, :, a] = g0row[:, a]
        return f_stream, g_stream

    return _callback


def apply_bottom_grad_wall_inplace(
    solver: GasSolver2D,
    theta_wall_lu: float,
    *,
    rho_policy: str = "pressure_preserving",
    extrap: str = "linear",
) -> None:
    """Reconstruct the bottom wall row 0 in place on the current solver state.

    Reuses the callback with the current ``solver.f/g`` as the post-stream field (row 1's
    non-equilibrium is read from the live state). Used by the Level C coupler to re-impose
    the wall temperature at the corrected film temperature outside a streaming step (row 1
    is unaffected, so the extracted near-wall q_g is unchanged).
    """

    cb = make_bottom_grad_wall_callback(
        float(theta_wall_lu), rho_policy=rho_policy, extrap=extrap, fill_deep_links=False
    )
    cb(solver=solver, f_post=solver.f, g_post=solver.g, f_stream=solver.f, g_stream=solver.g)
