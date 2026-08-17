"""Strict candidate-B tangent instrument — full-step JVP on the mirror topology.

Design authority: docs/Phase_5/strict_faceflux_candidate_b_design_v1.0.md
(sections 2/4/5).  The frozen round-1 instrument (core/tangent_step.py) is
NOT touched; this module mirrors its chained-JVP structure with

  * every C block evaluated ON THE 2N MIRROR EXTENSION (P is linear, so
    the direction is extended with the same operator as the base);
  * S exactly linear THROUGH the extension (P -> pull stream -> R): the
    crossing-link reflection channel B_ref rides in here;
  * the band stage replaced by the strict first-gas-cell face source
    (boundary/wall_face_flux_strict.py), central-differenced jointly in
    (state, theta_w) exactly like the frozen B stage — the G0 branch's
    constitutive channel dG_f = 1.04 G_f dtheta_w/theta_w is carried by
    the chain rule of the SAME production formula, never a separate path;
  * A structurally identity (asserted at construction on the extension);
  * H exactly linear through the extension.

Face-source channel decomposition (design section 5 row 6):
  B_theta  = dE derivative through the direct Dirichlet channel  G_f * nx
  B_gas    = dE derivative through the first-cell temperature    -G_f
  B_G      = G0 constitutive channel  1.04 G_f/theta_w * sum(theta_w-theta_1)
  B_shape  = 0 by construction (fixed lattice-weight shape vector)
  B_ref    = the P+S crossing-link reflection (no direct theta_w channel)
analytical values from ``face_source_channels``; the explicit
opposite-permutation reference for B_ref is ``explicit_bounceback_stream``.

``propagate_tangent`` from the frozen instrument is reused verbatim by the
runner (drive protocol, ramp, sampling, V5 audits); this operator exposes
the same interface surface (step/hot_base/c2/theta0/rho0/D/S/solver).

DIAGNOSTIC ONLY (D0-7).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from boundary.wall_face_flux_strict import (
    G0_CONDUCTIVITY_EXPONENT,
    BRANCH_CONST_G,
    StrictFaceFluxWall,
    strict_face_conductance_lu,
)
from core.strict_b_half_domain import StrictBHalfDomain
from core.tangent_step import (
    block_heatflux_energy,
    block_macro_eq,
    block_stress,
)

__all__ = [
    "StrictBBaseState",
    "StrictBStageBases",
    "compute_stage_bases_strict",
    "StrictBTangentOperator",
    "face_source_channels",
    "explicit_bounceback_stream",
    "strict_direct_step_fn",
]


@dataclass
class StrictBBaseState:
    """Read-only DC base-state snapshot on the PHYSICAL half domain."""

    f: np.ndarray            # (N, nx, Q)
    g: np.ndarray
    theta_w: float           # hot-face mean setpoint
    theta_amb: float         # cold-face temperature
    theta_dc_target: float
    meta: dict[str, Any]


@dataclass
class StrictBStageBases:
    """Base intermediates at every strict stage/block boundary.

    C-block intermediates live on the 2N extension (they are what the
    +-h branches perturb); the face-source input state is physical.
    """

    f: np.ndarray            # physical base
    g: np.ndarray
    f_ext: np.ndarray        # P(base)
    g_ext: np.ndarray
    rho: np.ndarray          # 2N macro_eq block outputs
    u: np.ndarray
    theta: np.ndarray
    f_eq: np.ndarray
    g_eq: np.ndarray
    f1: np.ndarray           # 2N stress block output
    f2: np.ndarray           # 2N heatflux block outputs
    g_post: np.ndarray
    s_f: np.ndarray          # 2N streamed
    s_g: np.ndarray
    p_f: np.ndarray          # physical after R (face-source input)
    p_g: np.ndarray
    b_g: np.ndarray          # physical after the face source (f unchanged)
    de_hot: float
    de_cold: float
    h_f: np.ndarray          # physical final state after A/H
    h_g: np.ndarray
    r_f: float
    reference_triple: tuple[float, float, float, float]


def strict_direct_step_fn(halfdomain: StrictBHalfDomain,
                          wall: StrictFaceFluxWall,
                          f: np.ndarray, g: np.ndarray, theta_hot: float):
    """One full strict step F(x, theta_w) with an explicit theta_hot value.

    Pure wrapper over the production stage functions (the same objects the
    runner drives); returns (f', g', dE_hot, dE_cold)."""

    f_s, g_s = halfdomain.stage_cs(f, g)
    g_s = g_s.copy()
    g_s, de_hot, de_cold = wall.apply_at(halfdomain, f_s, g_s, theta_hot)
    f_h, g_h = halfdomain.stage_ah(f_s, g_s)
    return f_h, g_h, de_hot, de_cold


def compute_stage_bases_strict(halfdomain: StrictBHalfDomain,
                               wall: StrictFaceFluxWall,
                               base: StrictBBaseState) -> StrictBStageBases:
    """Evaluate and cache every strict stage/block base input/output once."""

    mapping = halfdomain.mapping
    lattice = halfdomain.lattice
    f_ext = halfdomain.extend(base.f)
    g_ext = halfdomain.extend(base.g)
    rho, u, theta, f_eq, g_eq = block_macro_eq(f_ext, g_ext, mapping, lattice)
    f1 = block_stress(f_ext, f_eq, rho, u, theta, mapping, lattice)
    f2, g_post = block_heatflux_energy(f1, g_eq, f_ext, g_ext, u, mapping, lattice)
    s_f_ext, s_g_ext = halfdomain.stage_stream_ext(f2, g_post)
    p_f = halfdomain.restrict(s_f_ext)
    p_g = halfdomain.restrict(s_g_ext)
    b_g = p_g.copy()
    b_g, de_hot, de_cold = wall.apply_at(halfdomain, p_f, b_g, base.theta_w)
    h_f, h_g = halfdomain.stage_ah(p_f, b_g)
    num = math.sqrt(float(np.sum((h_f - base.f) ** 2) + np.sum((h_g - base.g) ** 2)))
    den = math.sqrt(float(np.sum(base.f ** 2) + np.sum(base.g ** 2)))
    r_f = num / max(den, 1e-300)
    n = halfdomain.n_phys
    ref = (float(np.mean(rho[:n])), float(np.mean(u[:n, ..., 0])),
           float(np.mean(u[:n, ..., 1])), float(np.mean(theta[:n])))
    return StrictBStageBases(
        f=base.f, g=base.g, f_ext=f_ext, g_ext=g_ext, rho=rho, u=u,
        theta=theta, f_eq=f_eq, g_eq=g_eq, f1=f1, f2=f2, g_post=g_post,
        s_f=s_f_ext, s_g=s_g_ext, p_f=p_f, p_g=p_g, b_g=b_g,
        de_hot=de_hot, de_cold=de_cold, h_f=h_f, h_g=h_g, r_f=r_f,
        reference_triple=ref)


class StrictBTangentOperator:
    """Chained stage/block JVP of the strict one-step operator.

    Interface-compatible with core.tangent_step.propagate_tangent
    (step / hot_base / c2 / theta0 / rho0 / D / S / solver).  No ablation
    semantics — the strict unit runs the full chain only (A0-style).
    """

    def __init__(self, halfdomain: StrictBHalfDomain, wall: StrictFaceFluxWall,
                 hot_base: StrictBBaseState, hot: StrictBStageBases,
                 cold_base: StrictBBaseState, cold: StrictBStageBases, *,
                 h: float):
        if hot_base.f.shape != cold_base.f.shape:
            raise ValueError("hot/cold snapshots differ in geometry")
        self.halfdomain = halfdomain
        self.wall = wall
        self.solver = halfdomain.ext_solver     # parameter carrier (dt_s, nx)
        self.hot_base = hot_base
        self.cold_base = cold_base
        self.hot = hot
        self.cold = cold
        self.h = float(h)
        # acoustic stage identity re-asserted on the actual extension geometry
        halfdomain.assert_structural()
        lattice = halfdomain.lattice
        self.c2 = np.sum(np.asarray(lattice.c, dtype=float) ** 2, axis=-1)
        self.D = int(halfdomain.mapping.lattice.D)
        self.S = int(halfdomain.mapping.lattice.S)
        self.rho0 = float(halfdomain.mapping.lattice.rho_ref_lu)
        self.theta0 = float(halfdomain.mapping.theta_ref_lu)
        self.c0 = math.sqrt(float(halfdomain.mapping.physical.gamma) * self.theta0)
        self.c_vec = np.asarray(lattice.c, dtype=float)
        # hot-base PHYSICAL macro linearization fields for the normalization
        n = halfdomain.n_phys
        self._n_rho = hot.rho[:n]
        self._n_u = hot.u[:n]
        self._n_theta = hot.theta[:n]

    # pre-registered macro normalization (JAB caliber, physical domain)
    def macro_scale(self, df: np.ndarray, dg: np.ndarray, d_theta_w: float) -> float:
        drho = np.sum(df, axis=-1)
        dj = np.einsum("yxq,qd->yxd", df, self.c_vec)
        du = (dj - self._n_u * drho[..., None]) / self._n_rho[..., None]
        de = 0.5 * np.sum(df * self.c2, axis=-1) + np.sum(dg, axis=-1)
        de_int = de - np.einsum("yxd,yxd->yx", self._n_u, dj) \
            + 0.5 * np.sum(self._n_u ** 2, axis=-1) * drho
        ds = self.D + self.S
        dtheta = 2.0 * de_int / (ds * self._n_rho) - self._n_theta * drho / self._n_rho
        return float(max(
            np.max(np.abs(drho)) / self.rho0,
            np.max(np.abs(dtheta)) / self.theta0,
            np.max(np.abs(du)) / self.c0,
            abs(float(d_theta_w)) / self.theta0,
        ))

    def _face_source_eval(self, p_f: np.ndarray, p_g: np.ndarray,
                          theta_hot: float):
        g_out = p_g.copy()
        g_out, de_hot, de_cold = self.wall.apply_at(
            self.halfdomain, p_f, g_out, theta_hot)
        return g_out, de_hot, de_cold

    def step(self, df: np.ndarray, dg: np.ndarray, d_theta_w: float):
        """Advance the tangent one strict step; returns (df', dg', d_hot, d_cold)."""

        h = self.h
        s = self.macro_scale(df, dg, d_theta_w)
        if s <= 0.0 or not math.isfinite(s):
            if not math.isfinite(s):
                raise FloatingPointError("non-finite tangent state")
            zero = np.zeros_like(df)
            return zero, np.zeros_like(dg), 0.0, 0.0
        inv = 1.0 / s
        scale = s / (2.0 * h)
        hd = self.halfdomain
        mapping = hd.mapping
        lattice = hd.lattice
        b = self.hot

        # direction extended with the SAME linear operator as the base
        vf = hd.extend(h * inv * df)
        vg = hd.extend(h * inv * dg)

        # --- C stage, block "macro_eq" (on the extension) ---
        p = block_macro_eq(b.f_ext + vf, b.g_ext + vg, mapping, lattice)
        m = block_macro_eq(b.f_ext - vf, b.g_ext - vg, mapping, lattice)
        d_rho, d_u, d_theta, d_feq, d_geq = [(a - c) * scale for a, c in zip(p, m)]

        # --- C stage, block "stress" ---
        w_rho = h * inv * d_rho
        w_u = h * inv * d_u
        w_th = h * inv * d_theta
        w_feq = h * inv * d_feq
        f1_p = block_stress(b.f_ext + vf, b.f_eq + w_feq, b.rho + w_rho,
                            b.u + w_u, b.theta + w_th, mapping, lattice)
        f1_m = block_stress(b.f_ext - vf, b.f_eq - w_feq, b.rho - w_rho,
                            b.u - w_u, b.theta - w_th, mapping, lattice)
        d_f1 = (f1_p - f1_m) * scale

        # --- C stage, block "heatflux" ---
        w_f1 = h * inv * d_f1
        w_geq = h * inv * d_geq
        p5 = block_heatflux_energy(b.f1 + w_f1, b.g_eq + w_geq, b.f_ext + vf,
                                   b.g_ext + vg, b.u + w_u, mapping, lattice)
        m5 = block_heatflux_energy(b.f1 - w_f1, b.g_eq - w_geq, b.f_ext - vf,
                                   b.g_ext - vg, b.u - w_u, mapping, lattice)
        d_f2 = (p5[0] - m5[0]) * scale
        d_gpost = (p5[1] - m5[1]) * scale

        # --- S stage (exactly linear on the extension; carries B_ref) ---
        d_sf_ext, d_sg_ext = hd.stage_stream_ext(d_f2, d_gpost)
        d_pf = hd.restrict(d_sf_ext)
        d_pg = hd.restrict(d_sg_ext)

        # --- Bq stage (joint state + wall-temperature JVP, physical) ---
        w_pf = h * inv * d_pf
        w_pg = h * inv * d_pg
        w_tw = h * inv * float(d_theta_w)
        bp = self._face_source_eval(b.p_f + w_pf, b.p_g + w_pg,
                                    self.hot_base.theta_w + w_tw)
        bm = self._face_source_eval(b.p_f - w_pf, b.p_g - w_pg,
                                    self.hot_base.theta_w - w_tw)
        d_bg = (bp[0] - bm[0]) * scale
        d_hot = (bp[1] - bm[1]) * scale
        d_cold = (bp[2] - bm[2]) * scale
        d_bf = d_pf                        # the source never touches f

        # --- A stage: structurally identity (asserted at construction) ---

        # --- H stage (exactly linear through the extension) ---
        d_hf_ext = hd.extend(d_bf)
        d_hg_ext = hd.extend(d_bg)
        d_hf_ext, d_hg_ext = hd.stage_filter_ext(d_hf_ext, d_hg_ext)
        return (hd.restrict(d_hf_ext), hd.restrict(d_hg_ext), d_hot, d_cold)


# ---------------------------------------------------------------------------
# analytical channel decomposition (design section 5 row 6)
# ---------------------------------------------------------------------------

def face_source_channels(halfdomain: StrictBHalfDomain,
                         wall: StrictFaceFluxWall,
                         f: np.ndarray, g: np.ndarray,
                         theta_hot: float) -> dict[str, float]:
    """Analytical hot-face dE channels at the given state.

    B_theta  : direct Dirichlet drive channel  d(dE_hot)/d(theta_w)|_G  = G_f*nx
    B_G      : constitutive channel through G_f(theta_w)  (0 for CONST_G)
    B_gas    : first-cell temperature channel  d(dE_hot)/d(theta_1) = -G_f
               (per column; reported as the uniform-column value)
    B_shape  : 0 by construction (fixed-weight shape vector)
    """

    th1_hot, _ = halfdomain.first_cell_thetas(f, g)
    g_f = strict_face_conductance_lu(
        wall.mapping, float(theta_hot), branch=wall.branch, theta_0=wall.theta_0)
    if wall.branch == BRANCH_CONST_G:
        g_prime = 0.0
    else:
        g_prime = G0_CONDUCTIVITY_EXPONENT * g_f / float(theta_hot)
    nx = f.shape[1]
    return {
        "B_theta": g_f * nx,
        "B_G": g_prime * float(np.sum(float(theta_hot) - th1_hot)),
        "B_gas_per_column": -g_f,
        "B_shape": 0.0,
        "G_f": g_f,
    }


def explicit_bounceback_stream(f: np.ndarray, opposite: np.ndarray,
                               c_int: np.ndarray) -> np.ndarray:
    """Explicit opposite-permutation halfway-reflection streaming (B_ref ref).

    Independent index-level reference for the P+S crossing-link closure on
    the PHYSICAL half domain: interior links pull periodically (x always,
    y within the physical rows); every face-crossing link pulls the
    OPPOSITE population from the mirrored source row —

        arriving at row j with c_y = k > j        ->  source row k-1-j
        arriving at row j with c_y = -kk, j>=N-kk ->  source row 2N-1-kk-j

    both with the same x displacement (out[j,x,a] = f[src, x-c_x, opp(a)],
    the mirror only flips y).  No mirror_extend machinery is used here.
    """

    n = f.shape[0]
    out = np.empty_like(f)
    cx = c_int[:, 0].astype(int)
    cy = c_int[:, 1].astype(int)
    for a in range(f.shape[-1]):
        k = int(cy[a])
        m = int(cx[a])
        out[..., a] = np.roll(f[..., a], shift=(k, m), axis=(0, 1))
        if k > 0:
            for j in range(min(k, n)):
                src = k - 1 - j
                out[j, :, a] = np.roll(f[src, :, opposite[a]], m)
        elif k < 0:
            kk = -k
            for j in range(max(0, n - kk), n):
                src = 2 * n - 1 - kk - j
                out[j, :, a] = np.roll(f[src, :, opposite[a]], m)
    return out
