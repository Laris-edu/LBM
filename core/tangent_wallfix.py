"""Wallfix tangent instrument — JAB tangent chain with the v2 wall family.

A2-5 corrective counter-proof measurement layer (D0-7 diagnostic): the
frozen round-1 instrument (core/tangent_step.py) is NOT touched; this module
mirrors its band stage and TangentOperator with the wall reconstruction
swapped for boundary/wall_thermal_mass_neutral_v2.reconstruct_row0_symmetric_v2
(applied to BOTH the hot band and the sink band — a wall methodology is
changed consistently or not at all).

``repin='uniform', extrap='row1'`` is the production anchor: stage and
operator are asserted BITWISE-identical to the frozen tangent_step versions
in the contract tests (the same anchoring pattern round 2 used for
compose_band_row). ``propagate_tangent`` from the frozen instrument is
reused verbatim — it only consumes ``op.step``/bookkeeping, so the drive
protocol, sampling, ramp and V5-family audits stay identical across wall
variants.
"""

from __future__ import annotations

import math

import numpy as np

from boundary.wall_thermal_mass_neutral_v2 import (
    EXTRAP_MODES,
    REPIN_MODES,
    reconstruct_row0_symmetric_v2,
)
from core.solver import GasSolver2D
from core.tangent_step import (
    BaseState,
    StageBases,
    TangentOperator,
    block_heatflux_energy,
    block_macro_eq,
    block_stress,
    stage_filter,
    stage_stream,
)

__all__ = [
    "stage_band_wallfix",
    "compute_stage_bases_wallfix",
    "WallfixTangentOperator",
]


def _check_modes(repin: str, extrap: str) -> None:
    if repin not in REPIN_MODES:
        raise ValueError(f"unsupported repin mode: {repin}")
    if extrap not in EXTRAP_MODES:
        raise ValueError(f"unsupported non-equilibrium extrapolation: {extrap}")


def stage_band_wallfix(solver: GasSolver2D, f_s: np.ndarray, g_s: np.ndarray,
                       theta_hot: float, theta_amb: float, hs: int,
                       *, repin: str, extrap: str):
    """B stage with the v2 wall family (hot band row 0 + sink band row hs).

    Mirrors core.tangent_step.stage_band line by line (copies, exact
    bookkeeping deltas); repin='uniform', extrap='row1' is bitwise-anchored
    to the frozen stage in the contract tests.
    """

    _check_modes(repin, extrap)
    c2 = solver._tangent_c2 if hasattr(solver, "_tangent_c2") else np.sum(
        np.asarray(solver.lattice.c, dtype=float) ** 2, axis=-1)
    f_w = f_s.copy()
    g_w = g_s.copy()
    e0 = float(np.sum(0.5 * f_w * c2) + np.sum(g_w))
    f_w, g_w = reconstruct_row0_symmetric_v2(
        solver, f_w, g_w, float(theta_hot), extrap=extrap, repin=repin, row=0)
    e1 = float(np.sum(0.5 * f_w * c2) + np.sum(g_w))
    f_w, g_w = reconstruct_row0_symmetric_v2(
        solver, f_w, g_w, float(theta_amb), extrap=extrap, repin=repin,
        row=int(hs))
    e2 = float(np.sum(0.5 * f_w * c2) + np.sum(g_w))
    return f_w, g_w, e1 - e0, e2 - e1


def compute_stage_bases_wallfix(solver: GasSolver2D, base: BaseState,
                                *, repin: str, extrap: str) -> StageBases:
    """compute_stage_bases with the wallfix band stage (same caching layout)."""

    _check_modes(repin, extrap)
    mapping = solver.mapping
    lattice = solver.lattice
    rho, u, theta, f_eq, g_eq = block_macro_eq(base.f, base.g, mapping, lattice)
    f1 = block_stress(base.f, f_eq, rho, u, theta, mapping, lattice)
    f2, g_post = block_heatflux_energy(f1, g_eq, base.f, base.g, u, mapping, lattice)
    s_f, s_g = stage_stream(f2, g_post, lattice)
    b_f, b_g, hot_de, sink_de = stage_band_wallfix(
        solver, s_f, s_g, base.theta_w, base.theta_amb, base.hs,
        repin=repin, extrap=extrap)
    h_f, h_g = stage_filter(solver, b_f, b_g)
    num = math.sqrt(float(np.sum((h_f - base.f) ** 2) + np.sum((h_g - base.g) ** 2)))
    den = math.sqrt(float(np.sum(base.f ** 2) + np.sum(base.g ** 2)))
    r_f = num / max(den, 1e-300)
    ref = (float(np.mean(rho)), float(np.mean(u[..., 0])),
           float(np.mean(u[..., 1])), float(np.mean(theta)))
    return StageBases(f=base.f, g=base.g, rho=rho, u=u, theta=theta, f_eq=f_eq,
                      g_eq=g_eq, f1=f1, f2=f2, g_post=g_post, s_f=s_f, s_g=s_g,
                      b_f=b_f, b_g=b_g, hot_de=hot_de, sink_de=sink_de,
                      h_f=h_f, h_g=h_g, r_f=r_f, reference_triple=ref)


class WallfixTangentOperator(TangentOperator):
    """TangentOperator with the band stage swapped for the v2 wall family.

    ``step`` is the frozen round-1 body verbatim except the two band-stage
    evaluation lines; the PROD variant is asserted bitwise-identical to the
    frozen operator in the contract tests. ``ablated`` keeps its round-1
    semantics (the counter-proof runs A0-style, ablated=frozenset()).
    """

    def __init__(self, solver: GasSolver2D, hot_base: BaseState,
                 hot: StageBases, cold_base: BaseState, cold: StageBases, *,
                 h: float, ablated: frozenset, repin: str, extrap: str):
        _check_modes(repin, extrap)
        super().__init__(solver, hot_base, hot, cold_base, cold,
                         h=h, ablated=ablated)
        self.repin = str(repin)
        self.extrap = str(extrap)

    def step(self, df: np.ndarray, dg: np.ndarray, d_theta_w: float):
        h = self.h
        s = self.macro_scale(df, dg, d_theta_w)
        if s <= 0.0 or not math.isfinite(s):
            if not math.isfinite(s):
                raise FloatingPointError("non-finite tangent state")
            zero = np.zeros_like(df)
            return zero, np.zeros_like(dg), 0.0, 0.0
        inv = 1.0 / s
        scale = s / (2.0 * h)
        mapping = self.solver.mapping
        lattice = self.solver.lattice

        # --- C stage, block "macro_eq" (A3) ---
        b3 = self._bases("macro_eq")
        vf = h * inv * df
        vg = h * inv * dg
        p = block_macro_eq(b3.f + vf, b3.g + vg, mapping, lattice)
        m = block_macro_eq(b3.f - vf, b3.g - vg, mapping, lattice)
        d_rho, d_u, d_theta, d_feq, d_geq = [(a - b) * scale for a, b in zip(p, m)]

        # --- C stage, block "stress" (A4) ---
        b4 = self._bases("stress")
        w_rho = h * inv * d_rho
        w_u = h * inv * d_u
        w_th = h * inv * d_theta
        w_feq = h * inv * d_feq
        f1_p = block_stress(b4.f + vf, b4.f_eq + w_feq, b4.rho + w_rho,
                            b4.u + w_u, b4.theta + w_th, mapping, lattice)
        f1_m = block_stress(b4.f - vf, b4.f_eq - w_feq, b4.rho - w_rho,
                            b4.u - w_u, b4.theta - w_th, mapping, lattice)
        d_f1 = (f1_p - f1_m) * scale

        # --- C stage, block "heatflux" (A5) ---
        b5 = self._bases("heatflux")
        w_f1 = h * inv * d_f1
        w_geq = h * inv * d_geq
        p5 = block_heatflux_energy(b5.f1 + w_f1, b5.g_eq + w_geq, b5.f + vf,
                                   b5.g + vg, b5.u + w_u, mapping, lattice)
        m5 = block_heatflux_energy(b5.f1 - w_f1, b5.g_eq - w_geq, b5.f - vf,
                                   b5.g - vg, b5.u - w_u, mapping, lattice)
        d_f2 = (p5[0] - m5[0]) * scale
        d_gpost = (p5[1] - m5[1]) * scale

        # --- S stage (exactly linear; A6 swaps in the cold-base FD) ---
        if "stream_filter" in self.ablated:
            bs = self.cold
            w_f2 = h * inv * d_f2
            w_gp = h * inv * d_gpost
            sp = stage_stream(bs.f2 + w_f2, bs.g_post + w_gp, lattice)
            sm = stage_stream(bs.f2 - w_f2, bs.g_post - w_gp, lattice)
            d_sf = (sp[0] - sm[0]) * scale
            d_sg = (sp[1] - sm[1]) * scale
        else:
            d_sf, d_sg = stage_stream(d_f2, d_gpost, lattice)

        # --- B stage (WALLFIX: v2 family band JVP; A2 -> cold) ---
        bb = self._bases("band")
        base_b = self.cold_base if "band" in self.ablated else self.hot_base
        w_sf = h * inv * d_sf
        w_sg = h * inv * d_sg
        w_tw = h * inv * float(d_theta_w)
        bp = stage_band_wallfix(self.solver, bb.s_f + w_sf, bb.s_g + w_sg,
                                base_b.theta_w + w_tw, base_b.theta_amb,
                                base_b.hs, repin=self.repin, extrap=self.extrap)
        bm = stage_band_wallfix(self.solver, bb.s_f - w_sf, bb.s_g - w_sg,
                                base_b.theta_w - w_tw, base_b.theta_amb,
                                base_b.hs, repin=self.repin, extrap=self.extrap)
        d_bf = (bp[0] - bm[0]) * scale
        d_bg = (bp[1] - bm[1]) * scale
        d_hot = (bp[2] - bm[2]) * scale
        d_sink = (bp[3] - bm[3]) * scale

        # --- A stage: structurally identity (asserted at construction) ---

        # --- H stage (exactly linear; A6 swaps in the cold-base FD) ---
        if "stream_filter" in self.ablated:
            bh = self.cold
            w_bf = h * inv * d_bf
            w_bg = h * inv * d_bg
            hp = stage_filter(self.solver, bh.b_f + w_bf, bh.b_g + w_bg)
            hm = stage_filter(self.solver, bh.b_f - w_bf, bh.b_g - w_bg)
            d_hf = (hp[0] - hm[0]) * scale
            d_hg = (hp[1] - hm[1]) * scale
        else:
            d_hf, d_hg = stage_filter(self.solver, d_bf, d_bg)

        return d_hf, d_hg, d_hot, d_sink
