"""Independent CE/continuum face-conductance admission references (strict B).

Design authority: docs/Phase_5/strict_faceflux_candidate_b_design_v1.0.md
section 5 row 5 (G0 admission).  This module is the INDEPENDENT side of the
admission: closed-form / matrix continuum references built from the frozen
CE nominal transport scalars only.  It imports NOTHING from the strict-B
implementation (no boundary/, no core/ strict modules) so the gas-side
evidence can never certify itself through the boundary's own bookkeeping.

Physical family: the sealed-column linearized conduction family already
certified as the tent spectral reference (G3/G4a caliber) — heat diffusion
plus the sealed-box uniform-pressure compression coupling — generalized to

  * half-grid Dirichlet FACES (ghost elimination, faces at y = 0 and y = H
    with cell centres at y_r = r + 1/2, H = N dy);
  * a power-law conductivity k(theta) = k0 (theta/theta0)^beta with its
    exact steady base state (Phi = theta^{beta+1} linear in y);
  * the pressure-consistent stratified base density rho_b = p_bar/theta_b
    with p_bar fixed by the closed-column mass constraint
    (1/H) integral rho_b dy = rho_ref.

Frequency-domain equation (LU, R_lu = 1, c_p = c_v + 1):

  i w rho_b c_p T' - i w <rho_b^2 T'>/<rho_b> =
      d/dy( k_b dT'/dy + (dk/dtheta)_b T' dtheta_b/dy )

with T'(face_hot) = 1, T'(face_cold) = 0.  The reference face admittance is
reported in the SAME observable structure as the strict wall's ledger
tangent (per face, per unit hot-face temperature):

  Y_ref = G_f (T'_face - T'_0) + [G0 branch] beta G_f/theta_w T'_face (theta_w - theta_1b)

Cold state (theta_dc = 0) reduces exactly to the certified constant-alpha
sealed reference with half-grid Dirichlet faces.

DIAGNOSTIC ONLY (D0-7); no gate claims.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "steady_powerlaw_profile",
    "steady_powerlaw_flux",
    "series_conductance",
    "sealed_face_dirichlet_reference",
]


# ---------------------------------------------------------------------------
# steady nonlinear slab (closed form)
# ---------------------------------------------------------------------------

def steady_powerlaw_profile(n_cells: int, theta_hot: float, theta_cold: float,
                            beta: float) -> np.ndarray:
    """Exact steady profile at cell centres for k ~ theta^beta.

    Faces at y=0 and y=H=n_cells (dy=1), centres at y_r = r + 1/2.
    Phi = theta^{beta+1} is linear between the face values.
    """

    if theta_hot <= 0.0 or theta_cold <= 0.0:
        raise ValueError("face temperatures must be positive")
    p = float(beta) + 1.0
    y = (np.arange(int(n_cells)) + 0.5) / float(n_cells)
    phi = theta_hot ** p + (theta_cold ** p - theta_hot ** p) * y
    return phi ** (1.0 / p)


def steady_powerlaw_flux(n_cells: int, theta_hot: float, theta_cold: float,
                         k0: float, theta0: float, beta: float) -> float:
    """Exact steady conductive flux (positive from hot face into the gas)."""

    p = float(beta) + 1.0
    h = float(n_cells)
    return float(k0) / (float(theta0) ** float(beta)) \
        * (theta_hot ** p - theta_cold ** p) / (p * h)


def series_conductance(theta_bar: float, n_cells: int, k0: float,
                       theta0: float, beta: float) -> dict[str, float]:
    """Small-gradient series conductance G_series = k(theta_bar)/H and its
    theta_bar derivative (the admission's odd-slope targets)."""

    k_bar = float(k0) * (float(theta_bar) / float(theta0)) ** float(beta)
    h = float(n_cells)
    return {
        "G_series": k_bar / h,
        "dG_series_dtheta": float(beta) * k_bar / (float(theta_bar) * h),
    }


# ---------------------------------------------------------------------------
# sealed-column complex reference with half-grid Dirichlet faces
# ---------------------------------------------------------------------------

def sealed_face_dirichlet_reference(
    *,
    n_cells: int,
    omega_lu: float,
    k0: float,
    theta0: float,
    beta: float,
    rho_ref: float,
    c_v: float,
    theta_dc: float,
) -> dict[str, object]:
    """Complex response of the sealed stratified column, faces Dirichlet.

    Returns the profile T'(y) per unit hot-face drive, the reference face
    admittance Y_ref in the strict ledger observable structure, and the
    base-state arrays.  theta_dc = 0 gives the certified constant-alpha
    sealed cold reference.
    """

    n = int(n_cells)
    if n < 4:
        raise ValueError("reference column needs at least 4 cells")
    c_p = float(c_v) + 1.0
    theta_hot = float(theta0) * (1.0 + float(theta_dc))
    theta_cold = float(theta0)

    # exact steady base state
    th_b = steady_powerlaw_profile(n, theta_hot, theta_cold, beta)
    # pressure-consistent closed-column base density: rho_b = p_bar/theta_b,
    # (1/H) sum rho_b = rho_ref  ->  p_bar = rho_ref * n / sum(1/theta_b)
    p_bar = float(rho_ref) * n / float(np.sum(1.0 / th_b))
    rho_b = p_bar / th_b
    k_b = float(k0) * (th_b / float(theta0)) ** float(beta)
    dk_dth_b = float(beta) * k_b / th_b
    # exact steady base flux and gradient (for the constitutive channel)
    q_b = steady_powerlaw_flux(n, theta_hot, theta_cold, k0, theta0, beta)
    dth_b_dy = -q_b / k_b                       # k dtheta/dy = -q exactly

    # gradient-flux operator, conservative form: cell r gains
    #   F_{r+1/2} - F_{r-1/2},   F = k dT'/dy + (dk/dth dth_b/dy) T'
    # interior face r+1/2:  F = k_mid (T_{r+1}-T_r) + a_mid (T_{r+1}+T_r)/2
    # hot face (T'_face = 1, ghost = 2 - T_0):
    #   F_{-1/2} = k_fh (T_0 - ghost) + a_fh (T_0+ghost)/2
    #            = 2 k_fh T_0 - 2 k_fh + a_fh
    # cold face (T'_face = 0, ghost = -T_{n-1}):
    #   F_{top}  = k_fc (ghost - T_{n-1}) + a_fc (ghost+T_{n-1})/2
    #            = -2 k_fc T_{n-1}
    # face-value transport evaluated at the EXACT face base temperatures.
    k_face_mid = 0.5 * (k_b[:-1] + k_b[1:])
    adv_mid = 0.5 * (dk_dth_b[:-1] * dth_b_dy[:-1]
                     + dk_dth_b[1:] * dth_b_dy[1:])
    k_fh = float(k0) * (theta_hot / float(theta0)) ** float(beta)
    k_fc = float(k0) * (theta_cold / float(theta0)) ** float(beta)
    a_fh = -float(beta) * q_b / theta_hot       # dk/dth * dth_b/dy at hot face

    a_mat = np.zeros((n, n), dtype=complex)
    drive = np.zeros(n, dtype=complex)          # constant part of the flux div
    for r in range(n):
        if r < n - 1:                            # upper interior face
            km, am = k_face_mid[r], adv_mid[r]
            a_mat[r, r + 1] += km + 0.5 * am
            a_mat[r, r] += -km + 0.5 * am
        else:                                    # cold boundary face
            a_mat[r, r] += -2.0 * k_fc
        if r > 0:                                # lower interior face (minus)
            km, am = k_face_mid[r - 1], adv_mid[r - 1]
            a_mat[r, r - 1] -= -km + 0.5 * am
            a_mat[r, r] -= km + 0.5 * am
        else:                                    # hot boundary face (minus)
            a_mat[r, r] -= 2.0 * k_fh
            drive[r] += 2.0 * k_fh - a_fh        # -( -2 k_fh + a_fh )

    # time term: i w rho_b c_p T' - i w <rho_b^2 T'>/<rho_b>
    iw = 1j * float(omega_lu)
    time_mat = iw * (np.diag(rho_b * c_p)
                     - np.outer(np.ones(n), rho_b ** 2) / float(np.sum(rho_b)))
    # (time - conduction) T' = drive
    profile = np.linalg.solve(time_mat - a_mat, drive)

    # reference face admittance in the strict ledger observable structure
    g_f_hot = k_fh / 0.5                         # k(theta_w)/d_f
    theta_1b = float(th_b[0])
    y_direct = g_f_hot * (1.0 - profile[0])
    if beta != 0.0:
        y_const = float(beta) * g_f_hot / theta_hot * (theta_hot - theta_1b)
    else:
        y_const = 0.0
    return {
        "profile": profile,
        "theta_base": th_b,
        "rho_base": rho_b,
        "p_bar": p_bar,
        "q_base": q_b,
        "Y_ref": complex(y_direct + y_const),
        "Y_ref_direct": complex(y_direct),
        "Y_ref_constitutive": complex(y_const),
        "G_f_hot": g_f_hot,
    }
