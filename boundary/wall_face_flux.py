"""Face-temperature/face-flux thermal band — D1 candidate B (diagnostic, D0-7).

WHAT THIS IS
------------
The paper-level derivation (Manuscript/Paper1_D1_FaceFlux_Pinning_Derivation.md,
D1_v1.1 — not in the repo; its judgement lines are transcribed into the runner)
localized the A2-5 finite-bias tangent channel to the DEFINITION of the current
wet-node wall: every step it resets the whole finite-volume wall row to the
reservoir energy ``E* = c_v rho_row theta_w`` and books that reset as physical
heat, so the wall-temperature drive gain is the storage coefficient
``c_v rho_row`` — density-sensitive by thermodynamic identity (D1.13), the
paradigm-locked channel wallfix proved unremovable from within.

Candidate B changes WHAT THE BOUNDARY EXCHANGES, not the reconstruction's
spectral shape: the physical Dirichlet datum lives on the zero-volume face
between the band row and its first gas neighbours, and the physical heat is
the discrete face flux

    q_s = G_f (theta_w - theta_1s),      G_f = k_nom / d_f,   d_f = dy/2,

per side ``s`` (both faces of the symmetric band), CONSERVATIVELY delivered to
the gas.  The drive gain becomes the transport coefficient ``G_f`` — no
``c_v rho_row`` factor (D1.43/D1.49).

REALIZATION CHOSEN HERE (flux-fed buffer; pre-registered design decision)
------------------------------------------------------------------------
D1 section 9.1 demands the band row lose its reservoir identity.  Of the two
options we keep the row as a FLUX-FED BUFFER: the certified v1.1 reconstruction
machinery is reused verbatim (per-column streamed density kept -> mass-neutral,
u=0 exact, per-direction non-equilibrium blend + equilibrium-increment cleanup)
with exactly ONE semantic change — the row's post-reconstruction energy target
is

    E_target = E_streamed + dt/dy * (q_+ + q_-)        (per column)

instead of the reservoir value ``c_v rho_row theta_w``.  The row temperature
floats (theta_target = E_target / (c_v rho_row)); nothing pins the node; the
face Dirichlet condition is enforced through the flux formula (the standard
half-cell Dirichlet-to-flux mapping, Robin-consistent).  Consequences, all by
construction:

  * the energy-audited band wrapper (make_energy_audited_band) measures
    EXACTLY the formula flux — the D1.70 audit identity is the wrapper's own
    reading, and the runner asserts wrapper == formula at machine precision;
  * mass neutrality and u=0 are inherited unchanged from the certified
    machinery (D1.72 first two conditions);
  * the A2-5 storage channel is absent from the boundary map: d(row energy
    after)/d(theta_w) = dt/dy * dq/dtheta_w = G_f per face — no rho factor;
  * the buffer adds a parallel heat-capacity node between the two faces; the
    lumped budget (D1 section 7 + section 13.3) bounds the cold-state cost to
    the band [-4.8%, -2.4%] with O(1%) buffer corrections (pole at
    ~alpha/dy^2 = 50x the 10 kHz drive — benign; D1.77 damping rate 0.018/step,
    no memory operator, no self-driven DC loop).

GEOMETRY / STATE MATCHING (D1 section 13.5 item 2)
--------------------------------------------------
The Dirichlet plane moves from the band-row NODE to the FACES at +-dy/2, so a
faceflux tent with sink band at row ``hs`` has face-to-face slab thickness
``(hs-1) dy`` per side.  The state-matched rig therefore uses hs_ff = hs_prod+1
(auth 49 vs 48, smoke 13 vs 12): face-to-face = production node-to-node
H_s exactly, preserving H_s/delta_T = 4.7124.

FROZEN CONSTITUTIVE CHOICE (D1 sections 5.3 / 9.3)
--------------------------------------------------
G_f is FROZEN at the cold nominal conductivity k_nom = alpha_lu * rho_ref *
c_p (c_p = (D+S)/2 + 1, R_lu = 1): delta G_f = 0 within a tangent step
(D1.42) and across working points.  The omitted constitutive T-dependence of
G_f multiplies the STATIC face drop (tiny at these scales) and is a documented
omission, never a tuning knob; any future correction must come from
independent cold-state analysis, never from the hot-state d_OP target
(anti-self-calibration, D1 section 9.3).

DIAGNOSTIC ONLY (D0-7): no gate claims, no production-wall change; the
certified production wall (boundary/wall_thermal_mass_neutral.py) is untouched
and remains the only certified wall.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from core.equilibrium import equilibrium_fg
from core.macroscopic import recover_macro
from core.solver import GasSolver2D

from .wall_common import bottom_wall_stencil

__all__ = [
    "faceflux_conductance_lu",
    "faceflux_formula_flux",
    "faceflux_reconstruct_row_symmetric",
    "make_faceflux_band_callback",
    "FACE_DISTANCE_LU",
]

# half-cell face: the physical Dirichlet plane sits between the band row and
# its first gas neighbour (D1.5)
FACE_DISTANCE_LU = 0.5


def faceflux_conductance_lu(mapping) -> float:
    """Frozen face conductance G_f = k_nom/d_f in bookkeeping LU.

    k_nom = alpha_lu * rho_ref * c_p with c_p = (D+S)/2 + 1 (R_lu = 1) — the
    cold nominal conductivity of the certified mapping; no temperature or
    density dependence (frozen, D1.42).
    """

    d = int(mapping.lattice.D)
    s = int(mapping.lattice.S)
    c_p = 0.5 * (d + s) + 1.0
    k_nom = float(mapping.alpha_lu) * float(mapping.lattice.rho_ref_lu) * c_p
    return k_nom / FACE_DISTANCE_LU


def _neighbour_theta(f_stream: np.ndarray, g_stream: np.ndarray, j: int,
                     D: int, S: int, lattice) -> np.ndarray:
    m = recover_macro(f_stream[j:j + 1], g_stream[j:j + 1], D=D, S=S,
                      lattice=lattice)
    return m.theta  # (1, nx)


def faceflux_formula_flux(solver: GasSolver2D, f_stream: np.ndarray,
                          g_stream: np.ndarray, theta_w: float, *, row: int,
                          g_face: float) -> tuple[np.ndarray, np.ndarray]:
    """Per-column face fluxes (q_up, q_dn) of the band at ``row`` (pure).

    q_s = G_f (theta_w - theta_{1,s}) evaluated on the STREAMED state — the
    same quantity the reconstruction injects; exposed separately so the runner
    and the contract tests can assert wrapper-measured == formula at machine
    precision (D1.70).
    """

    lattice = solver.lattice
    D = int(solver.mapping.lattice.D)
    S = int(solver.mapping.lattice.S)
    ny = int(solver.ny)
    row = int(row) % ny
    th_up = _neighbour_theta(f_stream, g_stream, (row + 1) % ny, D, S, lattice)
    th_dn = _neighbour_theta(f_stream, g_stream, (row - 1) % ny, D, S, lattice)
    q_up = float(g_face) * (float(theta_w) - th_up)
    q_dn = float(g_face) * (float(theta_w) - th_dn)
    return q_up, q_dn


def faceflux_reconstruct_row_symmetric(
    solver: GasSolver2D,
    f_stream: np.ndarray,
    g_stream: np.ndarray,
    theta_w: float,
    *,
    row: int,
    g_face: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Candidate-B band operation at ``row`` (in place).

    Reuses the certified v1.1 reconstruction skeleton verbatim (streamed
    density kept per column, u=0 exact, per-direction non-equilibrium blend,
    equilibrium-increment mass/momentum cleanup, uniform g zero-moment pin)
    with the single semantic change: the per-column energy target is
    ``E_streamed + (q_up + q_dn)`` (flux-fed) instead of the reservoir value
    ``c_v rho_row theta_w``.  theta_w enters ONLY through the flux formula.
    """

    lattice = solver.lattice
    D = int(solver.mapping.lattice.D)
    S = int(solver.mapping.lattice.S)
    q = int(lattice.q)
    c = np.asarray(lattice.c, dtype=float)
    c2 = np.sum(c**2, axis=-1)

    if theta_w <= 0.0:
        raise ValueError("face temperature must be positive")
    if solver.ny < 5:
        raise ValueError("symmetric face-flux band needs ny >= 5")

    ny = int(solver.ny)
    row = int(row) % ny
    nx = f_stream.shape[1]

    # -- face fluxes from the streamed state (theta_w enters HERE only) --
    q_up, q_dn = faceflux_formula_flux(
        solver, f_stream, g_stream, theta_w, row=row, g_face=g_face)

    # -- streamed row content (kept: mass; fed: energy) --
    rho_w = np.sum(f_stream[row:row + 1], axis=-1)          # (1, nx)
    if not np.all(rho_w > 0.0):
        raise RuntimeError("non-positive streamed wall-row density")
    e_streamed = (0.5 * np.sum(f_stream[row:row + 1] * c2, axis=-1)
                  + np.sum(g_stream[row:row + 1], axis=-1))  # (1, nx)
    e_target = e_streamed + q_up + q_dn                      # (1, nx)

    c_v = 0.5 * (D + S)
    theta_target = e_target / (c_v * rho_w)                  # (1, nx), floats
    if not np.all(theta_target > 0.0):
        raise RuntimeError("non-positive face-flux row temperature target")

    zeros_u = np.zeros((1, nx, 2))
    feq_w, geq_w = equilibrium_fg(rho_w, zeros_u, theta_target, S, lattice)

    def interior_neq(j):
        m = recover_macro(f_stream[j:j + 1], g_stream[j:j + 1], D=D, S=S,
                          lattice=lattice)
        feq_j, geq_j = equilibrium_fg(m.rho, m.u, m.theta, S, lattice)
        return f_stream[j:j + 1] - feq_j, g_stream[j:j + 1] - geq_j

    up_f, up_g = interior_neq((row + 1) % ny)
    dn_f, dn_g = interior_neq((row - 1) % ny)

    st = bottom_wall_stencil(lattice)
    f_neq = np.empty_like(up_f)
    g_neq = np.empty_like(up_g)
    f_neq[..., st.incoming] = up_f[..., st.incoming]
    g_neq[..., st.incoming] = up_g[..., st.incoming]
    f_neq[..., st.outgoing] = dn_f[..., st.outgoing]
    g_neq[..., st.outgoing] = dn_g[..., st.outgoing]
    f_neq[..., st.grazing] = 0.5 * (up_f + dn_f)[..., st.grazing]
    g_neq[..., st.grazing] = 0.5 * (up_g + dn_g)[..., st.grazing]

    # exact mass/momentum removal via the equilibrium increment (v1.1 lesson)
    drho = np.sum(f_neq, axis=-1)
    dj = np.einsum("yxq,qd->yxd", f_neq, c)
    rho_pert = rho_w + drho
    if not np.all(rho_pert > 0.0):
        raise RuntimeError("blended non-equilibrium exceeds wall density")
    u_pert = dj / rho_pert[..., None]
    feq_pert, geq_pert = equilibrium_fg(rho_pert, u_pert, theta_target, S, lattice)
    f_neq = f_neq - (feq_pert - feq_w)
    g_neq = g_neq - (geq_pert - geq_w)

    f0 = feq_w + f_neq                                       # rho_w & u=0 exact
    k_tr = 0.5 * np.sum(f0 * c2, axis=-1)
    g_partial = np.sum(geq_w, axis=-1) + np.sum(g_neq, axis=-1)
    delta = (e_target - k_tr - g_partial) / q                # exact energy pin
    g0 = geq_w + g_neq + delta[..., None]

    f_stream[row:row + 1] = f0
    g_stream[row:row + 1] = g0
    return f_stream, g_stream


def make_faceflux_band_callback(
    theta_band_lu: float | Callable[[GasSolver2D], float],
    row: int,
    *,
    g_face: float,
):
    """``solver.step`` boundary_callback applying the candidate-B band.

    Signature family matches ``make_symmetric_mass_neutral_band_callback`` so
    ``make_energy_audited_band`` wraps it identically — and by construction
    the wrapper's recorded per-step energy delta IS the formula heat.
    """

    if float(g_face) <= 0.0:
        raise ValueError("face conductance must be positive")

    def _callback(*, solver, f_post, g_post, f_stream, g_stream):
        theta_b = float(theta_band_lu(solver) if callable(theta_band_lu)
                        else theta_band_lu)
        return faceflux_reconstruct_row_symmetric(
            solver, f_stream, g_stream, theta_b, row=int(row),
            g_face=float(g_face))

    return _callback
