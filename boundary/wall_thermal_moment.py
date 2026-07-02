"""Moment-constrained regularized thermal Dirichlet wall for D2Q37 (doc §5.4).

The ABB prototype (``wall_thermal_abb``) removes the periodic-streaming checkerboard but
over-injects energy for the polyatomic f/g pair (near-wall T overshoots the imposed value)
because every wall-crossing link is pushed toward the wall equilibrium. This module instead
imposes the wall macrostate as a *constraint*:

After streaming, at the bottom wall row 0 the populations with ``cy <= 0`` are known (they
streamed from the gas above / same row and carry the gas response, including the emergent
near-wall heat flux). The unknown incoming populations (``cy > 0``, which would wrap from
the periodic top) are solved so the row-0 moments equal the wall target

    mass:      sum f            = rho_w        (pressure_preserving or constant_density)
    momentum:  sum f c          = 0            (no-slip u = 0)
    energy:    0.5 sum f|c|^2 + sum g = 0.5 (D+S) rho_w theta_w   (Dirichlet T = theta_w)

with the minimum-norm correction around the wall equilibrium (so no spurious high moments
are injected and the outgoing heat-flux non-equilibrium is retained). Rows ``1..max_cy-1``
have only their deep (``cy>=2``) below-wall links reconstructed by zero-gradient from the
post-collision wall row, avoiding periodic-top contamination without forcing them to T_w.

No clipping / floor / positivity repair is used.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from core.equilibrium import equilibrium_fg
from core.solver import GasSolver2D

from .wall_common import BOTTOM_WALL_ROW, bottom_wall_stencil, pressure_preserving_rho


def make_bottom_moment_wall_callback(
    theta_wall_lu: float | Callable[[GasSolver2D], float],
    *,
    rho_policy: str = "pressure_preserving",
    row: int = BOTTOM_WALL_ROW,
):
    """Return a ``solver.step`` boundary_callback imposing a moment-constrained bottom wall."""

    if row != BOTTOM_WALL_ROW:
        raise ValueError("only the bottom wall (row 0) is supported")

    def _callback(*, solver, f_post, g_post, f_stream, g_stream):
        lattice = solver.lattice
        st = bottom_wall_stencil(lattice)
        incoming = st.incoming
        known = np.where(st.cy <= 0)[0]
        n_in = incoming.size

        cx = np.asarray(lattice.c[:, 0], dtype=float)
        cy = np.asarray(lattice.c[:, 1], dtype=float)
        c2 = cx * cx + cy * cy
        D = float(solver.mapping.lattice.D)
        S = float(solver.mapping.lattice.S)

        theta_w = float(theta_wall_lu(solver) if callable(theta_wall_lu) else theta_wall_lu)
        if theta_w <= 0.0:
            raise ValueError("wall temperature must be positive")
        if rho_policy == "pressure_preserving":
            rho_w = pressure_preserving_rho(theta_w, solver.mapping)
        elif rho_policy == "constant_density":
            rho_w = float(solver.mapping.lattice.rho_ref_lu)
        else:
            raise ValueError(f"unknown rho_policy: {rho_policy}")

        # Constraint matrix on the unknown incoming populations x = [f_u (n_in); g_u (n_in)].
        A = np.zeros((4, 2 * n_in), dtype=float)
        A[0, :n_in] = 1.0
        A[1, :n_in] = cx[incoming]
        A[2, :n_in] = cy[incoming]
        A[3, :n_in] = 0.5 * c2[incoming]
        A[3, n_in:] = 1.0
        AAt_inv = np.linalg.inv(A @ A.T)

        # Reference = wall equilibrium (satisfies the target if the known part were eq too).
        f_w, g_w = equilibrium_fg(
            np.full((1, 1), rho_w), np.zeros((1, 1, 2)), np.full((1, 1), theta_w),
            solver.mapping.lattice.S, lattice,
        )
        x0 = np.concatenate([np.asarray(f_w[0, 0])[incoming], np.asarray(g_w[0, 0])[incoming]])  # (2 n_in,)

        # Known-population moments at row 0 (cy <= 0 streamed from the gas / same row).
        fk = f_stream[0][:, known]            # (nx, n_known)
        gk = g_stream[0][:, known]
        m_mass = fk.sum(axis=1)
        m_jx = fk @ cx[known]
        m_jy = fk @ cy[known]
        m_energy = 0.5 * (fk @ c2[known]) + gk.sum(axis=1)
        m_known = np.stack([m_mass, m_jx, m_jy, m_energy], axis=0)   # (4, nx)

        target = np.array([rho_w, 0.0, 0.0, 0.5 * (D + S) * rho_w * theta_w], dtype=float)
        b = target[:, None] - m_known                                # (4, nx)
        r = b - (A @ x0)[:, None]                                    # (4, nx)
        x = x0[:, None] + A.T @ (AAt_inv @ r)                        # (2 n_in, nx)

        f_stream[0][:, incoming] = x[:n_in].T
        g_stream[0][:, incoming] = x[n_in:].T

        # Deep below-wall links for rows 1..max_cy-1: zero-gradient from post-collision row 0.
        for a in incoming:
            for y in range(1, int(st.cy[a])):
                f_stream[y, :, a] = f_post[0, :, a]
                g_stream[y, :, a] = g_post[0, :, a]
        return f_stream, g_stream

    return _callback
