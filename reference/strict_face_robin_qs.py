"""Strict-face Robin QS static references (A2a-STRICT_B, plan sections 3.8/3.9).

Plan authority: docs/Phase_5/a2a_strict_b_experiment_plan_v1.0.md (PLAN_v1.0).
These are the NEWLY BUILT static comparators for the strict-B face boundary:
the only thing reused from reference/strict_b_face_admission.py is the
linearized face law itself (plan section 3.8),

    dq = G_f (dT_w - dT_1) + (beta G_f / Tbar_w) dT_w (Tbar_w - Tbar_1),

with beta = 1.04 (the strict wall's frozen G0 constitutive exponent).
``sealed_face_dirichlet_reference`` is NOT called (plan prohibition), and the
original Dirichlet tent BVP (scripts.phase5_g4a_dc_basestate.tent_bvp_reference)
is NOT called.  Each reference grid keeps its first cell centre at
y = dy_ref/2 and uses G_f_ref = 2 k_f / dy_ref, so refinement removes only the
half-cell discretization error and never introduces a physical contact
resistance (plan section 3.8).

Physical family (the same sealed-column linearized conduction family already
certified as the strict admission reference; frequency domain, LU, R_lu = 1):

    i w rho_b c_p T' - i w <rho_b^2 T'>/<rho_b> =
        d/dy ( k_b dT'/dy + (dk/dtheta)_b (dtheta_b/dy) T' )

on a finite column y in (0, H) with BOTH faces closed by the Robin face law
above (cold face: dT_amb = 0, so only the direct term survives).

Three tiers (plan section 3.8/3.9):

  QS-0   uniform bulk coefficient k(Tbar_w); its OWN steady DC base (exact
         linear profile through the face values); mean density fixed to
         rho_bar = (M_wet/A)/H_s (cold denominator uses M_wet(0)).
  QS-1   measured strict-B base state U_0^B(y) mapped to the reference grid
         with the frozen interpolation rules (plan section 4): T linear with
         the PRESCRIBED face temperatures as endpoints, rho end-value constant
         extension, then a global rho rescale that restores M_wet/A exactly.
         Bulk k(theta) = k0 (theta/theta0)^beta plus its constitutive
         advective channel.
  QS-1k  the frozen G0 finite-k operator (certified alpha_eff(k) table with
         its hold-first/hold-last truncation) and the frozen elevation policy
         (uniform wall-value elevation (1+Theta)^e(k), per-k exponents e(k)
         from the same table), placed DIRECTLY into the same strict-face
         Robin closure via the mirror-even periodic extension of the strict-B
         half domain (period 2H; face sources appear as symmetric pairs).
         The old D_beyond * QS-1 factorization is forbidden (plan section
         3.9) and is not implemented here.

DIAGNOSTIC ONLY (D0-7): no gate claims; nothing here touches production code.
"""

from __future__ import annotations

import math
from typing import Any, Callable

import numpy as np

__all__ = [
    "map_strict_base_to_ref",
    "steady_uniform_base",
    "robin_face_readout",
    "robin_qs_matrix_bvp",
    "robin_qs_spectral_extension",
    "g0_alpha_of_k",
    "analytic_sealed_dirichlet_slab",
]


# ---------------------------------------------------------------------------
# frozen base-state mappings (plan section 4)
# ---------------------------------------------------------------------------

def map_strict_base_to_ref(theta_48: np.ndarray, rho_48: np.ndarray,
                           n_ref: int, *, theta_w: float, theta_amb: float,
                           mass_per_area: float,
                           h_lu: float) -> tuple[np.ndarray, np.ndarray]:
    """Map the measured strict base (N cells) to the reference grid (plan §4).

    T: linear interpolation on y/H in {0, (j+1/2)/N, 1} with the PRESCRIBED
    face temperatures as endpoints.  rho: linear interpolation of the cell
    values with end-value constant extension (np.interp semantics), then one
    global multiplicative rescale so that sum(rho)*dy == mass_per_area
    EXACTLY (M_wet/A recovery).
    """

    theta_48 = np.asarray(theta_48, dtype=float)
    rho_48 = np.asarray(rho_48, dtype=float)
    n_src = theta_48.shape[0]
    if rho_48.shape[0] != n_src:
        raise ValueError("theta/rho source grids differ")
    y_src = (np.arange(n_src) + 0.5) / n_src
    y_ref = (np.arange(int(n_ref)) + 0.5) / float(n_ref)
    y_t = np.concatenate(([0.0], y_src, [1.0]))
    t_t = np.concatenate(([float(theta_w)], theta_48, [float(theta_amb)]))
    theta_ref = np.interp(y_ref, y_t, t_t)
    rho_ref = np.interp(y_ref, y_src, rho_48)      # end-value constant ext.
    dy = float(h_lu) / float(n_ref)
    mass_now = float(np.sum(rho_ref) * dy)
    rho_ref = rho_ref * (float(mass_per_area) / mass_now)
    return theta_ref, rho_ref


def steady_uniform_base(n_ref: int, *, theta_w: float, theta_amb: float,
                        rho_bar: float) -> tuple[np.ndarray, np.ndarray]:
    """QS-0's own steady DC base: exact linear profile through the faces.

    With a uniform conductivity and G_f = 2k/dy links the discrete steady
    state IS the exact linear interpolant of the face values.  rho_b is the
    pressure-consistent closed-column density rho_b = p_bar/theta_b with
    (1/n) sum rho_b = rho_bar.
    """

    n = int(n_ref)
    y = (np.arange(n) + 0.5) / n
    theta_b = float(theta_w) + (float(theta_amb) - float(theta_w)) * y
    p_bar = float(rho_bar) * n / float(np.sum(1.0 / theta_b))
    rho_b = p_bar / theta_b
    return theta_b, rho_b


# ---------------------------------------------------------------------------
# the shared Robin face readout (the plan's dq formula; dT_w = 1)
# ---------------------------------------------------------------------------

def robin_face_readout(*, g_f_hot: float, beta: float, theta_w: float,
                       theta_1_base: float, t1_response: complex) -> dict[str, complex]:
    """Y = G_f (1 - T'_1) + beta G_f/Tbar_w (Tbar_w - Tbar_1) per unit dT_w."""

    y_direct = g_f_hot * (1.0 - t1_response)
    y_const = float(beta) * g_f_hot / float(theta_w) \
        * (float(theta_w) - float(theta_1_base))
    return {"Y": complex(y_direct + y_const),
            "Y_direct": complex(y_direct), "Y_constitutive": complex(y_const)}


# ---------------------------------------------------------------------------
# QS-0 / QS-1: real-space matrix BVP with Robin faces
# ---------------------------------------------------------------------------

def robin_qs_matrix_bvp(*, n_ref: int, h_lu: float, omega_lu: float,
                        k0: float, theta0: float, beta: float,
                        c_p: float, theta_w: float, theta_amb: float,
                        theta_base: np.ndarray, rho_base: np.ndarray,
                        bulk_mode: str) -> dict[str, Any]:
    """Sealed stratified column, strict-face Robin closure on both faces.

    bulk_mode:
      "uniform_at_tw"  : k_b(y) == k0 (theta_w/theta0)^beta, no bulk advective
                         channel (QS-0).
      "powerlaw_local" : k_b = k0 (theta_b/theta0)^beta with the constitutive
                         advective channel a = (dk/dtheta)_b dtheta_b/dy from
                         the mapped base gradients (QS-1).

    The face links always use the strict wall's own law: hot
    k_f = k0 (theta_w/theta0)^beta, cold k_f = k0 (theta_amb/theta0)^beta,
    G_f = 2 k_f / dy.  Returns Y in ENERGY-flux units per unit dT_w plus the
    profile and base arrays.
    """

    n = int(n_ref)
    if n < 8:
        raise ValueError("reference column needs at least 8 cells")
    dy = float(h_lu) / n
    th_b = np.asarray(theta_base, dtype=float)
    rho_b = np.asarray(rho_base, dtype=float)
    if th_b.shape[0] != n or rho_b.shape[0] != n:
        raise ValueError("base arrays must live on the reference grid")

    if bulk_mode == "uniform_at_tw":
        k_b = np.full(n, float(k0) * (float(theta_w) / float(theta0)) ** beta)
        a_cell = np.zeros(n)
    elif bulk_mode == "powerlaw_local":
        k_b = float(k0) * (th_b / float(theta0)) ** beta
        grad = np.gradient(th_b, dy)
        a_cell = beta * k_b / th_b * grad          # (dk/dth) dtheta_b/dy
    else:
        raise ValueError(f"unknown bulk_mode: {bulk_mode!r}")

    g_fh = 2.0 * float(k0) * (float(theta_w) / float(theta0)) ** beta / dy
    g_fc = 2.0 * float(k0) * (float(theta_amb) / float(theta0)) ** beta / dy

    # conduction operator A with (A T + drive) = [F_{r+1/2} - F_{r-1/2}]/dy,
    # F_int = k_mid (T_{r+1}-T_r)/dy + a_mid (T_{r+1}+T_r)/2,
    # F_{-1/2} = -q_hot = -[g_fh (1 - T_0) + C_h],  F_{n-1/2} = q_cold = -g_fc T_{n-1}
    k_mid = 0.5 * (k_b[:-1] + k_b[1:])
    a_mid = 0.5 * (a_cell[:-1] + a_cell[1:])
    a_mat = np.zeros((n, n), dtype=complex)
    drive = np.zeros(n, dtype=complex)
    for r in range(n):
        if r < n - 1:                              # upper interior face (+F)
            km, am = k_mid[r] / dy, a_mid[r]
            a_mat[r, r + 1] += (km + 0.5 * am) / dy
            a_mat[r, r] += (-km + 0.5 * am) / dy
        else:                                      # cold face: F = -g_fc T_{n-1}
            a_mat[r, r] += -g_fc / dy
        if r > 0:                                  # lower interior face (-F)
            km, am = k_mid[r - 1] / dy, a_mid[r - 1]
            a_mat[r, r - 1] -= (-km + 0.5 * am) / dy
            a_mat[r, r] -= (km + 0.5 * am) / dy
        else:                                      # hot face: -F_{-1/2} = q_hot
            c_h = beta * g_fh / float(theta_w) * (float(theta_w) - float(th_b[0]))
            a_mat[r, r] += -g_fh / dy              # from  q_hot = g_fh(1-T_0)+C_h
            drive[r] += (g_fh + c_h) / dy

    iw = 1j * float(omega_lu)
    time_mat = iw * (np.diag(rho_b * float(c_p))
                     - np.outer(np.ones(n), rho_b ** 2) / float(np.sum(rho_b)))
    profile = np.linalg.solve(time_mat - a_mat, drive)

    out = robin_face_readout(g_f_hot=g_fh, beta=beta, theta_w=theta_w,
                             theta_1_base=float(th_b[0]),
                             t1_response=complex(profile[0]))
    return {**out, "profile": profile, "theta_base": th_b, "rho_base": rho_b,
            "g_f_hot": g_fh, "g_f_cold": g_fc, "n_ref": n, "dy": dy,
            "bulk_mode": bulk_mode}


# ---------------------------------------------------------------------------
# QS-1k: frozen G0 finite-k operator inside the same Robin closure
# ---------------------------------------------------------------------------

def g0_alpha_of_k(k_tab: np.ndarray, a_tab: np.ndarray,
                  e_tab: np.ndarray | None, *, theta_dc: float,
                  elevation: float = 1.0) -> Callable[[float], float]:
    """alpha(k) from the certified G0 table under the frozen policies.

    Truncation mirrors the certified operator convention exactly
    (_mode_coeffs family): hold-first below the table, linear interpolation
    inside, hold-last above.  Elevation policy: uniform wall-value elevation
    alpha(k) -> alpha(k) * (1 + elevation*Theta)^e(k) with e(k) held at the
    table ends the same way (e_tab None means no elevation).
    """

    k_tab = np.asarray(k_tab, dtype=float)
    a_tab = np.asarray(a_tab, dtype=float)
    if e_tab is not None:
        e_tab = np.asarray(e_tab, dtype=float)
        if e_tab.shape != k_tab.shape:
            raise ValueError("e(k) table must share the alpha table k grid")
    r = 1.0 + float(elevation) * float(theta_dc)

    def alpha_of(k: float) -> float:
        if k <= k_tab[0]:
            a, e = float(a_tab[0]), (float(e_tab[0]) if e_tab is not None else 0.0)
        elif k <= k_tab[-1]:
            a = float(np.interp(k, k_tab, a_tab))
            e = float(np.interp(k, k_tab, e_tab)) if e_tab is not None else 0.0
        else:
            a, e = float(a_tab[-1]), (float(e_tab[-1]) if e_tab is not None else 0.0)
        return a * r ** e

    return alpha_of


def robin_qs_spectral_extension(*, n_ref: int, h_lu: float, omega_lu: float,
                                gamma: float, alpha_of_k, alpha_face_hot: float,
                                alpha_face_cold: float, beta: float,
                                theta_w: float, theta_amb: float,
                                theta_1_base: float,
                                rho_bar_over_ref: float = 1.0) -> dict[str, Any]:
    """Strict-face Robin closure on the mirror-even periodic extension.

    The strict-B topology extends the half domain evenly across both faces
    (period 2H); a face source therefore appears as a symmetric pair of
    cell sources straddling the face.  The interior operator is the frozen
    G0 finite-k medium: per-mode coefficients of the certified sealed
    operator (mode 0: gamma/(i w n); mode j: 1/(n (i w + alpha(k_j) k_j^2)))
    with k_j = 2 pi min(j, n-j)/(2H) INDEPENDENT of the reference refinement.

    alpha-form units: face conductances g_f = 2 alpha_face/dy; the returned
    Y is converted back to the SAME energy-per-(rho_ref c_p) observable via
    rho_bar_over_ref (= rho_bar/rho_ref of this working point's ensemble).
    """

    n = int(n_ref)
    n_ext = 2 * n
    dy = float(h_lu) / n
    length = n_ext * dy                            # 2H in LU
    j = np.arange(n_ext)
    k_j = 2.0 * math.pi * np.minimum(j, n_ext - j) / length
    coeffs = np.empty(n_ext, dtype=complex)
    iw = 1j * float(omega_lu)
    coeffs[0] = float(gamma) / (iw * n_ext)
    for m in range(1, n_ext):
        coeffs[m] = 1.0 / (n_ext * (iw + alpha_of_k(float(k_j[m])) * k_j[m] ** 2))
    modes = np.exp(2j * np.pi * np.outer(j, j) / n_ext)
    green = (coeffs[:, None] * modes).sum(axis=0)  # G(r), even by construction

    # responses at the two first cells per unit alpha-flux through each face
    gh0 = (green[0] + green[1]) / dy               # own face pair -> T'_first
    gc0 = (green[n - 1] + green[n]) / dy           # opposite face pair
    g_fh = 2.0 * float(alpha_face_hot) / dy
    g_fc = 2.0 * float(alpha_face_cold) / dy
    c_h = float(beta) * g_fh / float(theta_w) * (float(theta_w) - float(theta_1_base))
    # q_h = g_fh (1 - T'_0) + C_h ;  q_c = -g_fc T'_{n-1}
    # T'_0 = gh0 q_h + gc0 q_c ;    T'_{n-1} = gc0 q_h + gh0 q_c
    a11 = 1.0 + g_fh * gh0
    a12 = g_fh * gc0
    a21 = g_fc * gc0
    a22 = 1.0 + g_fc * gh0
    b1 = g_fh + c_h
    det = a11 * a22 - a12 * a21
    q_h = (b1 * a22) / det
    q_c = (-a21 * b1) / det
    t0 = gh0 * q_h + gc0 * q_c
    scale = float(rho_bar_over_ref)                # alpha-units -> theta units
    return {"Y": complex(q_h * scale),
            "Y_direct": complex(g_fh * (1.0 - t0) * scale),
            "Y_constitutive": complex(c_h * scale),
            "q_cold": complex(q_c * scale), "t_first_response": complex(t0),
            "n_ref": n, "dy": dy}


# ---------------------------------------------------------------------------
# analytic contract anchor (test-side): sealed slab, Dirichlet faces
# ---------------------------------------------------------------------------

def analytic_sealed_dirichlet_slab(*, h_lu: float, omega_lu: float,
                                   alpha_lu: float, gamma: float) -> dict[str, Any]:
    """Closed form of i w (T - (g-1)/g <T>) = alpha T'' with T(0)=1, T(H)=0.

    The G_f -> infinity (refinement) limit of the uniform cold Robin family;
    used only by the contract tests as an independent convergence anchor.
    Returns the exact face admittance Y = -alpha rho c_p dT/dy ... in
    alpha-units per unit drive: Y_alpha = -alpha dT/dy|_0 (theta-flux form).
    """

    delta = (float(gamma) - 1.0) / float(gamma)
    m = complex(np.sqrt(1j * float(omega_lu) / float(alpha_lu)))
    h = float(h_lu)
    # T = A e^{m y} + B e^{-m y} + delta*c ; BCs and c = <T> self-consistency
    e_p, e_m = np.exp(m * h), np.exp(-m * h)

    def coeffs(c: complex) -> tuple[complex, complex]:
        # solve  A + B = rhs1 ; A e_p + B e_m = rhs2
        rhs1 = 1.0 - delta * c
        rhs2 = -delta * c
        a = (rhs2 - rhs1 * e_m) / (e_p - e_m)
        b = rhs1 - a
        return a, b

    # <T> = (1/h) int T dy = [A(e^{mh}-1) - B(e^{-mh}-1)]/(m h) + delta c
    # linear in c: <T> = p + q c ; c = p/(1-q)
    a0, b0 = coeffs(0.0)
    a1, b1 = coeffs(1.0)
    mean0 = (a0 * (e_p - 1.0) - b0 * (e_m - 1.0)) / (m * h)
    mean1 = (a1 * (e_p - 1.0) - b1 * (e_m - 1.0)) / (m * h) + delta
    q_lin = mean1 - mean0
    c = mean0 / (1.0 - q_lin)
    a, b = coeffs(c)
    y_alpha = -float(alpha_lu) * (a * m - b * m)   # -alpha dT/dy at y=0
    return {"Y_alpha": complex(y_alpha), "mean_T": complex(c), "m": m}
