"""Mass-neutral thermal wall v2 candidates — A2-5 corrective counter-proof family.

Context (WP4-JAB2 + NSF hot-base arbitration, 2026-08-10/11): the LBM's
anomalous negative working-point trend was localized to A2-5 — the wall
internal-energy target + uniform g repinning's base-state sensitivity
(delta_theta_row = eta * rho_w^cold/rho_w^hot operator-level propagation) —
and the continuum NSF arbitration confirmed no continuum hot-base mechanism
produces it. This module implements the LEGAL wall-modification family for
the corrective counter-proof ("can a principled boundary change remove the
anomaly without breaking the certified invariants?").

Invariant analysis (frozen design basis, see the wallfix report):
the four preserved requirements — (1) mass neutrality, (2) u_wall = 0,
(3) exact wall-temperature imposition on the row, (4) exact energy
bookkeeping — FORCE every scalar tangent channel of the wall map:
theta_hat_row = eta exactly (drive channel), energy response cv*theta_w to
incoming rho_hat (pinning channel), full absorption of incoming
non-equilibrium energy (repin channel). The only legal structural freedoms
are MICROSCOPIC:

  (a) the DISTRIBUTION of the repinned internal-energy increment over the
      g populations — production uses a UNIFORM delta/q shift (ghost-mode
      loaded); the v2 principle distributes it as an EQUILIBRIUM temperature
      increment (geq at the pinned temperature theta_pin), i.e. the same
      "smoothest possible / no ghost content" principle the production wall
      already applies to its mass/momentum cleanup step (the min-norm
      lesson, band_sub_C);
  (b) the non-equilibrium extrapolation order (row1 vs linear) — 'linear'
      removes the O(dy) base-gradient offset of the copied neq at finite
      bias (both modes existed in the certified v1 bottom wall; production
      froze row1).

``repin="uniform"`` + ``extrap="row1"`` reproduces the certified production
v1.1 reconstruction BITWISE (contract-test anchored) — the family is a
strict superset of production and touches no frozen path (default OFF
everywhere).

``repin="eqshape"``: replace ``g0 = geq_w + g_neq + delta/q`` by
``g0 = geq(rho_w, 0, theta_pin) + g_neq`` with the closed-form pinned
temperature

    theta_pin = (0.5 (D+S) rho_w theta_w - k_tr - sum g_neq) / (0.5 S rho_w)

(using sum geq(rho,0,theta) = 0.5 S rho theta exactly). The realized row
internal energy equals the SAME target, so theta = theta_w, u = 0, mass
neutrality and the bookkeeping identity are unchanged at machine level; only
the microscopic shape of the injected energy differs (equilibrium-shaped,
ghost-free, vs flat).

Diagnostic instrument family (D0-7): no production adoption is implied;
certification transfer is decided by the wallfix arbitration runner's
frozen legality battery + the G1-W-caliber checks, and any adoption would
trigger contract §23 re-verification.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from core.equilibrium import equilibrium_fg
from core.macroscopic import recover_macro
from core.solver import GasSolver2D

from .wall_common import bottom_wall_stencil

REPIN_MODES = ("uniform", "eqshape")
EXTRAP_MODES = ("row1", "linear")

# variant label -> (repin, extrap); PROD is the bitwise production anchor
WALLFIX_VARIANTS: dict[str, tuple[str, str]] = {
    "PROD": ("uniform", "row1"),
    "V2EQ": ("eqshape", "row1"),
    "V2LIN": ("uniform", "linear"),
    "V2EQL": ("eqshape", "linear"),
}


def reconstruct_row0_symmetric_v2(
    solver: GasSolver2D,
    f_stream: np.ndarray,
    g_stream: np.ndarray,
    theta_w: float,
    *,
    extrap: str,
    repin: str,
    row: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """v1.1 symmetric band reconstruction with the v2 repin family (in place).

    ``repin='uniform'`` follows the production expressions line by line (the
    bitwise anchor); ``repin='eqshape'`` differs ONLY in the final g
    assembly. Everything on the f side (mass neutrality, u=0) is shared.
    """

    if repin not in REPIN_MODES:
        raise ValueError(f"unsupported repin mode: {repin}")
    if extrap not in EXTRAP_MODES:
        raise ValueError(f"unsupported non-equilibrium extrapolation: {extrap}")
    if theta_w <= 0.0:
        raise ValueError("wall temperature must be positive")
    if solver.ny < 5:
        raise ValueError("symmetric two-sided wall needs ny >= 5")

    lattice = solver.lattice
    D = int(solver.mapping.lattice.D)
    S = int(solver.mapping.lattice.S)
    q = int(lattice.q)
    c = np.asarray(lattice.c, dtype=float)
    c2 = np.sum(c**2, axis=-1)

    ny = int(solver.ny)
    row = int(row) % ny
    nx = f_stream.shape[1]
    rho_w = np.sum(f_stream[row:row + 1], axis=-1)
    if not np.all(rho_w > 0.0):
        raise RuntimeError("non-positive streamed wall-row density")
    theta_row = np.full((1, nx), float(theta_w))
    zeros_u = np.zeros((1, nx, 2))
    feq_w, geq_w = equilibrium_fg(rho_w, zeros_u, theta_row, S, lattice)

    def interior_neq(j):
        m = recover_macro(f_stream[j:j + 1], g_stream[j:j + 1], D=D, S=S, lattice=lattice)
        feq_j, geq_j = equilibrium_fg(m.rho, m.u, m.theta, S, lattice)
        return f_stream[j:j + 1] - feq_j, g_stream[j:j + 1] - geq_j

    up_f, up_g = interior_neq((row + 1) % ny)
    dn_f, dn_g = interior_neq((row - 1) % ny)
    if extrap == "linear":
        up2_f, up2_g = interior_neq((row + 2) % ny)
        dn2_f, dn2_g = interior_neq((row - 2) % ny)
        up_f, up_g = 2.0 * up_f - up2_f, 2.0 * up_g - up2_g
        dn_f, dn_g = 2.0 * dn_f - dn2_f, 2.0 * dn_g - dn2_g

    st = bottom_wall_stencil(lattice)
    f_neq = np.empty_like(up_f)
    g_neq = np.empty_like(up_g)
    f_neq[..., st.incoming] = up_f[..., st.incoming]
    g_neq[..., st.incoming] = up_g[..., st.incoming]
    f_neq[..., st.outgoing] = dn_f[..., st.outgoing]
    g_neq[..., st.outgoing] = dn_g[..., st.outgoing]
    f_neq[..., st.grazing] = 0.5 * (up_f + dn_f)[..., st.grazing]
    g_neq[..., st.grazing] = 0.5 * (up_g + dn_g)[..., st.grazing]

    # exact mass/momentum removal via the equilibrium increment (production)
    drho = np.sum(f_neq, axis=-1)
    dj = np.einsum("yxq,qd->yxd", f_neq, c)
    rho_pert = rho_w + drho
    if not np.all(rho_pert > 0.0):
        raise RuntimeError("blended non-equilibrium exceeds wall density")
    u_pert = dj / rho_pert[..., None]
    feq_pert, geq_pert = equilibrium_fg(rho_pert, u_pert, theta_row, S, lattice)
    f_neq = f_neq - (feq_pert - feq_w)
    g_neq = g_neq - (geq_pert - geq_w)

    f0 = feq_w + f_neq                                  # rho_w & u=0 exact
    k_tr = 0.5 * np.sum(f0 * c2, axis=-1)
    target_int = 0.5 * (D + S) * rho_w * theta_w
    if repin == "uniform":
        # production lines verbatim (bitwise anchor)
        g_partial = np.sum(geq_w, axis=-1) + np.sum(g_neq, axis=-1)
        delta = (target_int - k_tr - g_partial) / q
        g0 = geq_w + g_neq + delta[..., None]
    else:
        # eqshape: the repinned energy enters with the local equilibrium
        # temperature-increment shape (ghost-free), not a flat 1/q shift.
        # sum geq(rho,0,theta_pin) = 0.5 S rho theta_pin exactly -> closed form.
        g_neq_sum = np.sum(g_neq, axis=-1)
        theta_pin = (target_int - k_tr - g_neq_sum) / (0.5 * S * rho_w)
        if not np.all(theta_pin > 0.0):
            raise RuntimeError("eqshape repin drove non-positive pin temperature")
        _, geq_pin = equilibrium_fg(rho_w, zeros_u, theta_pin, S, lattice)
        g0 = geq_pin + g_neq

    f_stream[row:row + 1] = f0
    g_stream[row:row + 1] = g0
    return f_stream, g_stream


def make_symmetric_band_callback_v2(
    theta_band_lu: float | Callable[[GasSolver2D], float],
    row: int,
    *,
    repin: str,
    extrap: str = "row1",
):
    """v2-family band callback (same signature family as the production
    ``make_symmetric_mass_neutral_band_callback``)."""

    if repin not in REPIN_MODES:
        raise ValueError(f"unsupported repin mode: {repin}")
    if extrap not in EXTRAP_MODES:
        raise ValueError(f"unsupported non-equilibrium extrapolation: {extrap}")

    def _callback(*, solver, f_post, g_post, f_stream, g_stream):
        theta_b = float(theta_band_lu(solver) if callable(theta_band_lu) else theta_band_lu)
        return reconstruct_row0_symmetric_v2(
            solver, f_stream, g_stream, theta_b,
            extrap=extrap, repin=repin, row=int(row),
        )

    return _callback
