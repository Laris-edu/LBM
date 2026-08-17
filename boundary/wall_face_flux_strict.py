"""Strict candidate-B face-flux wall: first-gas-cell incoming-g source (D0-7).

Design authority: docs/Phase_5/strict_faceflux_candidate_b_design_v1.0.md.
This is NOT the flux-fed buffer of boundary/wall_face_flux.py (that module
stays a frozen control and its band-row reconstruction is never imported
here).  There is no band row at all: the physical Dirichlet datum lives on
the half-grid faces and the ONLY boundary energy action is

    q_s   = G_s (theta_w,s - theta_1,s)          per face s, per column
    dE_s  = (dt/dy) q_s                          (dt = dy = 1 in LU)

delivered to the FIRST GAS CONTROL VOLUME by a fixed-weight minimum-norm
increment on the face's incoming unit-normal-speed g populations:

    I_s = { a : c_a . n_s = 1 }                  (|I_s| = 7 on D2Q37)
    min ||W^{-1/2} dg||_2   s.t.  sum(dg) = dE_s,  sum(c_t dg) = 0
    =>  dg = W A^T (A W A^T)^{-1} [dE_s, 0]^T,   A = [1^T ; c_t^T]_(I_s)

with W = diag(w_a) the FIXED lattice weights — the shape vector is a
constant of the lattice, so its state derivative vanishes (B_shape = 0 by
construction).  f and every other physical row are bit-untouched; the
reflection closure for crossing links lives entirely in P+S
(core/strict_b_half_domain.py), so this source never reflects.

Hard gates (design section 2): rank(A) = 2, cond(A W A^T) <= 1e10
(MOMENT_SYSTEM_INVALID), finite solution and post-source distributions,
recovered rho > 0 and theta > 0 (POST_SOURCE_STATE_INVALID).  q_s < 0 and
transient sign reversal are allowed; sign(q_s) = sign(theta_w - theta_1)
is an algebraic identity of the formula for G_s > 0 (G_s > 0 asserted).
No clipping, no uniform source, no extra flux shapes, no band energy
target, no factor 2 inside the source.

Conductance branches (design section 3):
  STRICT_B_CONST_G : G_f = k_0 / d_f frozen at the cold nominal for every
                     working point and both faces (topology/semantics
                     control; cannot alone judge D1 section 13.2).
  STRICT_B_G0      : k_f = k_0 (theta_w/theta_0)^1.04 evaluated at each
                     face's own wall temperature; the tangent keeps
                     dG_f = 1.04 G_f dtheta_w/theta_w through the chain
                     rule of the same formula (no separate code path).

The authoritative face-heat quantity is the per-face incoming-link ledger
(the dE_s this module returns); GasSolver2D.get_heat_flux_lu stays an
independent output diagnostic and is never used to calibrate the source.

DIAGNOSTIC ONLY (D0-7): no gate claims, no production-wall change.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "FACE_DISTANCE_LU",
    "G0_CONDUCTIVITY_EXPONENT",
    "BRANCH_CONST_G",
    "BRANCH_G0",
    "StrictBMomentSystemError",
    "StrictBPostSourceError",
    "strict_face_index_sets",
    "strict_face_shape_vector",
    "strict_cold_conductance_lu",
    "strict_face_conductance_lu",
    "apply_strict_face_source_row",
    "StrictFaceFluxWall",
]

# the physical Dirichlet plane sits half a cell outside the first gas row
FACE_DISTANCE_LU = 0.5
# frozen constitutive exponent of the G0 branch (design section 3; the
# certified G0 measured law k ~ T^{+1.04})
G0_CONDUCTIVITY_EXPONENT = 1.04
# moment-system conditioning gate (design section 2)
COND_GATE = 1.0e10

BRANCH_CONST_G = "CONST_G"
BRANCH_G0 = "G0"
_BRANCHES = (BRANCH_CONST_G, BRANCH_G0)


class StrictBMomentSystemError(RuntimeError):
    """The face moment system failed its hard gate (MOMENT_SYSTEM_INVALID)."""


class StrictBPostSourceError(RuntimeError):
    """The post-source state failed its hard gate (POST_SOURCE_STATE_INVALID)."""


# ---------------------------------------------------------------------------
# lattice-level constants
# ---------------------------------------------------------------------------

def strict_face_index_sets(lattice) -> tuple[np.ndarray, np.ndarray]:
    """(I_hot, I_cold): incoming unit-normal-speed sets for both faces.

    Hot face is below row 0 (n = +e_y): I_hot = {a : c_y = +1}.
    Cold face is above row N-1 (n = -e_y): I_cold = {a : c_y = -1}.
    """

    cy = np.asarray(lattice.c[:, 1], dtype=int)
    i_hot = np.where(cy == 1)[0]
    i_cold = np.where(cy == -1)[0]
    if len(i_hot) != 7 or len(i_cold) != 7:
        raise StrictBMomentSystemError(
            f"unit-normal incoming sets must have 7 members on D2Q37, got "
            f"{len(i_hot)}/{len(i_cold)}")
    return i_hot, i_cold


def strict_face_shape_vector(lattice, face_indices: np.ndarray) -> dict:
    """Fixed-weight minimum-norm shape vector for one face's I_s.

    Returns dict with s_vec (|I_s|,), the constraint matrix A, cond(AWA^T)
    and rank.  Hard gates: rank(A) = 2, cond <= 1e10, finite solution,
    constraint residuals at machine precision (MOMENT_SYSTEM_INVALID).
    """

    idx = np.asarray(face_indices, dtype=int)
    w = np.asarray(lattice.w, dtype=float)[idx]
    c_t = np.asarray(lattice.c, dtype=float)[idx, 0]     # tangential = c_x
    a_mat = np.vstack([np.ones_like(c_t), c_t])           # 2 x |I_s|
    rank = int(np.linalg.matrix_rank(a_mat))
    if rank != 2:
        raise StrictBMomentSystemError(f"rank(A) = {rank} != 2")
    awat = a_mat @ (w[:, None] * a_mat.T)
    cond = float(np.linalg.cond(awat))
    if not np.isfinite(cond) or cond > COND_GATE:
        raise StrictBMomentSystemError(f"cond(A W A^T) = {cond:.3e} > {COND_GATE:g}")
    s_vec = w * (a_mat.T @ np.linalg.solve(awat, np.array([1.0, 0.0])))
    if not np.all(np.isfinite(s_vec)):
        raise StrictBMomentSystemError("non-finite shape vector")
    res_e = abs(float(np.sum(s_vec)) - 1.0)
    res_t = abs(float(np.sum(c_t * s_vec)))
    if res_e > 1e-13 or res_t > 1e-13:
        raise StrictBMomentSystemError(
            f"shape-vector constraint residuals {res_e:.2e}/{res_t:.2e}")
    return {"s_vec": s_vec, "A": a_mat, "cond_awat": cond, "rank": rank,
            "indices": idx}


# ---------------------------------------------------------------------------
# conductance branches
# ---------------------------------------------------------------------------

def strict_cold_conductance_lu(mapping) -> float:
    """Frozen cold face conductance G_0 = k_0/d_f in bookkeeping LU.

    k_0 = alpha_lu * rho_ref * c_p with c_p = (D+S)/2 + 1 (R_lu = 1) — the
    cold nominal conductivity of the certified mapping.  Independent
    definition (the frozen buffer module is not imported).
    """

    d = int(mapping.lattice.D)
    s = int(mapping.lattice.S)
    c_p = 0.5 * (d + s) + 1.0
    k_0 = float(mapping.alpha_lu) * float(mapping.lattice.rho_ref_lu) * c_p
    return k_0 / FACE_DISTANCE_LU


def strict_face_conductance_lu(mapping, theta_w: float, *, branch: str,
                               theta_0: float) -> float:
    """Per-face conductance under the frozen branch semantics."""

    if branch not in _BRANCHES:
        raise ValueError(f"unknown strict-B conductance branch: {branch!r}")
    g_cold = strict_cold_conductance_lu(mapping)
    if branch == BRANCH_CONST_G:
        return g_cold
    if theta_w <= 0.0 or theta_0 <= 0.0:
        raise ValueError("G0 branch needs positive temperatures")
    return g_cold * (float(theta_w) / float(theta_0)) ** G0_CONDUCTIVITY_EXPONENT


# ---------------------------------------------------------------------------
# the source itself
# ---------------------------------------------------------------------------

def apply_strict_face_source_row(f: np.ndarray, g: np.ndarray, *, row: int,
                                 shape: dict, de_cols: np.ndarray,
                                 D: int, S: int, lattice) -> np.ndarray:
    """Add dg = s_vec * dE per column to row ``row``'s I_s g populations.

    Modifies ``g`` in place and returns it.  ``f`` is READ-ONLY (used for
    the post-source recovery gate).  Hard gates: finite increment and
    post-source distribution, recovered rho > 0 and theta > 0
    (POST_SOURCE_STATE_INVALID).
    """

    idx = shape["indices"]
    s_vec = shape["s_vec"]
    de = np.asarray(de_cols, dtype=float).reshape(-1)          # (nx,)
    if not np.all(np.isfinite(de)):
        raise StrictBPostSourceError("non-finite face energy increment")
    dg = de[:, None] * s_vec[None, :]                          # (nx, |I_s|)
    if not np.all(np.isfinite(dg)):
        raise StrictBPostSourceError("non-finite face source increment")
    g[row, :, idx] += dg.T                                     # fancy-axis first
    if not np.all(np.isfinite(g[row])):
        raise StrictBPostSourceError("non-finite post-source distribution")
    rho_row = np.sum(f[row], axis=-1)
    if not np.all(rho_row > 0.0):
        raise StrictBPostSourceError("non-positive post-source density")
    c2 = np.sum(np.asarray(lattice.c, dtype=float) ** 2, axis=-1)
    j_row = f[row] @ np.asarray(lattice.c, dtype=float)        # (nx, 2)
    e_int = (0.5 * np.sum(f[row] * c2, axis=-1) + np.sum(g[row], axis=-1)
             - 0.5 * np.sum(j_row ** 2, axis=-1) / rho_row)
    theta_row = 2.0 * e_int / ((D + S) * rho_row)
    if not np.all(theta_row > 0.0):
        raise StrictBPostSourceError("non-positive post-source temperature")
    return g


class StrictFaceFluxWall:
    """Both-face strict source with per-face conductance branch and ledger.

    ``theta_hot`` may be a float or a zero-argument callable (the drive
    protocol mutates a closure exactly like the production tent rig);
    ``theta_amb`` is the frozen cold-face temperature.  ``ledger`` (dict of
    lists) receives the per-step authoritative incoming-link energies
    "hot_dE"/"cold_dE" when provided.
    """

    def __init__(self, mapping, lattice, *, theta_hot, theta_amb: float,
                 branch: str, theta_0: float, ledger: dict | None = None):
        if branch not in _BRANCHES:
            raise ValueError(f"unknown strict-B conductance branch: {branch!r}")
        self.mapping = mapping
        self.lattice = lattice
        self.theta_hot = theta_hot
        self.theta_amb = float(theta_amb)
        self.branch = str(branch)
        self.theta_0 = float(theta_0)
        self.ledger = ledger
        if self.theta_amb <= 0.0 or self.theta_0 <= 0.0:
            raise ValueError("face temperatures must be positive")
        i_hot, i_cold = strict_face_index_sets(lattice)
        self.shape_hot = strict_face_shape_vector(lattice, i_hot)
        self.shape_cold = strict_face_shape_vector(lattice, i_cold)
        if strict_cold_conductance_lu(mapping) <= 0.0:
            raise ValueError("face conductance must be positive")
        self.D = int(mapping.lattice.D)
        self.S = int(mapping.lattice.S)

    def _theta_hot_now(self) -> float:
        th = self.theta_hot() if callable(self.theta_hot) else self.theta_hot
        th = float(th)
        if th <= 0.0:
            raise ValueError("hot face temperature must be positive")
        return th

    def face_fluxes_at(self, halfdomain, f: np.ndarray, g: np.ndarray,
                       theta_hot: float):
        """(q_hot_cols, q_cold_cols) each (1, nx), from the wrap-cleared state."""

        th_hot = float(theta_hot)
        if th_hot <= 0.0:
            raise ValueError("hot face temperature must be positive")
        th1_hot, th1_cold = halfdomain.first_cell_thetas(f, g)
        g_hot = strict_face_conductance_lu(
            self.mapping, th_hot, branch=self.branch, theta_0=self.theta_0)
        g_cold = strict_face_conductance_lu(
            self.mapping, self.theta_amb, branch=self.branch, theta_0=self.theta_0)
        q_hot = g_hot * (th_hot - th1_hot)
        q_cold = g_cold * (self.theta_amb - th1_cold)
        return q_hot, q_cold

    def apply(self, halfdomain, f: np.ndarray, g: np.ndarray):
        """Bq at the wall's own (possibly callable) hot setpoint."""

        return self.apply_at(halfdomain, f, g, self._theta_hot_now())

    def apply_at(self, halfdomain, f: np.ndarray, g: np.ndarray,
                 theta_hot: float):
        """Bq: compute q from (f, g), write both first-cell sources into g.

        Returns (g, dE_hot, dE_cold) with the ledger scalars summed over
        all columns (LU energy per step).  f is bit-untouched.
        """

        q_hot, q_cold = self.face_fluxes_at(halfdomain, f, g, theta_hot)
        de_hot_cols = q_hot.reshape(-1)      # (dt/dy) = 1 in LU
        de_cold_cols = q_cold.reshape(-1)
        g = apply_strict_face_source_row(
            f, g, row=0, shape=self.shape_hot, de_cols=de_hot_cols,
            D=self.D, S=self.S, lattice=self.lattice)
        g = apply_strict_face_source_row(
            f, g, row=f.shape[0] - 1, shape=self.shape_cold,
            de_cols=de_cold_cols, D=self.D, S=self.S, lattice=self.lattice)
        de_hot = float(np.sum(de_hot_cols))
        de_cold = float(np.sum(de_cold_cols))
        if self.ledger is not None:
            self.ledger.setdefault("hot_dE", []).append(de_hot)
            self.ledger.setdefault("cold_dE", []).append(de_cold)
        return g, de_hot, de_cold
