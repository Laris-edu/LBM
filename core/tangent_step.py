"""Matrix-free one-step tangent (JVP) machinery for WP4-JAB (hot-basestate
Jacobian ablation; guide docs/Phase_5/wp4_hot_basestate_jacobian_ablation_guide.md).

Scope (guide section 10): stage wrappers over the PRODUCTION one-step operator,
base-state snapshot structure, matrix-free stage/block JVPs and the per-variant
ablation assembly. NO experiment interpretation lives here.

The production step (core/solver.py::GasSolver2D.step with the G4a tent
boundary callbacks) is, on the frozen Level C config,

    F = H o A o B o S o C

  C : collide_fg               (macro/equilibrium -> stress -> heat-flux -> dG)
  S : pull_stream_fg           (permutation; exactly linear)
  B : hot band + sink band     (v1.1 symmetric mass-neutral reconstruction)
  A : acoustic phase family    (STRUCTURALLY IDENTITY on this rig geometry:
      zero qualifying diagonal low modes at nx=8, high-mode factors 1.0,
      spectral trace projector policy off, no pressure-memory trace. This is
      the G2-O S6 family of structural facts and MUST be re-asserted at
      runtime on the actual geometry -- never extrapolated. See
      ``assert_acoustic_stage_identity``.)
  H : conservative biharmonic filter (fixed coefficients; exactly linear)

The C stage is split into the guide's ablation blocks by calling the SAME
production internals in the SAME order (bitwise identity with collide_fg is
asserted in the contract tests -- this file does not fork an approximate
solver):

  block "macro_eq"  (A3): recover_macro + equilibrium_fg
  block "stress"    (A4): _regularized_f_collision + conserved-moment pinning
  block "heatflux"  (A5): _regularized_heat_flux_collision + pinning + delta_G
                          (the delta_G map itself is an exactly linear
                          functional: E_tot = 0.5*sum(f*|c|^2) + sum(g))

JVPs are central differences with the pre-registered macro normalization
  s = max(|drho|/rho0, |dtheta|/theta0, |du|/c0, |dT_w|/theta0),  c0=sqrt(g*th0)
computed ONCE per tangent step from the propagated state against the HOT base
linearization; the +h/-h branches share the same normalized direction, the
same caches and the same code path (guide section 4.3 error list).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from boundary.wall_thermal_mass_neutral import _mass_neutral_reconstruct_row0_symmetric
from core.collision_smrt import (
    _correct_f_conserved_moments,
    _regularized_f_collision,
    _regularized_heat_flux_collision,
    collide_fg,
)
from core.equilibrium import equilibrium_fg
from core.macroscopic import recover_macro
from core.solver import (
    ACOUSTIC_PHASE_HIGH_MODE_POLICY_SPECIFIED,
    TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_PRESSURE_MEMORY,
    TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL,
    TRACE_BULK_POLICY_GHOST_ORTHOGONAL_SPECTRAL,
    GasSolver2D,
    conservative_biharmonic_filter,
)
from core.streaming import pull_stream_fg


class TangentStructureError(RuntimeError):
    """A structural precondition of the tangent decomposition failed."""


# ---------------------------------------------------------------------------
# variant catalogue (guide section 6.2, frozen in the config)
# ---------------------------------------------------------------------------

VARIANT_BLOCKS: dict[str, frozenset[str]] = {
    "A0": frozenset(),
    "A1": frozenset({"acoustic_ref"}),
    "A2": frozenset({"band"}),
    "A3": frozenset({"macro_eq"}),
    "A4": frozenset({"stress"}),
    "A5": frozenset({"heatflux"}),
    "A6": frozenset({"stream_filter"}),
}


def ablated_blocks(variant: str) -> frozenset[str]:
    """Resolve a variant name ("A0".."A6") or combo ("A2+A4") to frozen blocks.

    Unknown names fail loudly (guide section 11 item 9)."""

    parts = [p.strip() for p in str(variant).split("+") if p.strip()]
    if not parts:
        raise ValueError(f"empty variant name: {variant!r}")
    blocks: set[str] = set()
    for p in parts:
        if p not in VARIANT_BLOCKS:
            raise ValueError(f"unknown ablation variant: {p!r} (from {variant!r})")
        blocks |= VARIANT_BLOCKS[p]
    return frozenset(blocks)


# ---------------------------------------------------------------------------
# structural facts of the acoustic stage on the actual geometry
# ---------------------------------------------------------------------------

def acoustic_stage_structural_report(solver: GasSolver2D) -> dict[str, Any]:
    """Measure (not assume) whether the acoustic stage is an identity here.

    G2-O S6 established the identity on the narrow-nx rig via two structural
    facts; the no-misread rule forbids extrapolating it, so every ingredient is
    re-measured on THIS solver geometry/config."""

    coll = solver.mapping.collision
    n_diag = len(solver._acoustic_phase_modes()) if coll.acoustic_phase_correction_enabled else 0
    high_identity = (
        not coll.acoustic_phase_correction_enabled
        or (
            coll.acoustic_phase_high_mode_policy == ACOUSTIC_PHASE_HIGH_MODE_POLICY_SPECIFIED
            and float(coll.acoustic_phase_high_mode_factor) == 1.0
            and float(coll.acoustic_phase_high_mode_diagonal_factor) == 1.0
        )
    )
    report = {
        "acoustic_phase_correction_enabled": bool(coll.acoustic_phase_correction_enabled),
        "diagonal_low_mode_count": int(n_diag),
        "high_mode_identity": bool(high_identity),
        "spectral_trace_projector_off": coll.trace_bulk_policy
        != TRACE_BULK_POLICY_GHOST_ORTHOGONAL_SPECTRAL,
        "pressure_memory_trace_off": coll.trace_bulk_policy
        not in {
            TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_PRESSURE_MEMORY,
            TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL,
        },
        "ny": int(solver.ny),
        "nx": int(solver.nx),
    }
    report["identity"] = bool(
        report["diagonal_low_mode_count"] == 0
        and report["high_mode_identity"]
        and report["spectral_trace_projector_off"]
        and report["pressure_memory_trace_off"]
    )
    return report


def assert_acoustic_stage_identity(solver: GasSolver2D) -> dict[str, Any]:
    """Fail loudly unless the acoustic stage is structurally an identity.

    If this ever fails (different geometry/config), the tangent needs a real
    A-stage JVP implementation before any run may proceed -- the A1 shortcut
    (S_A1 = 0 by construction) is only legal under this assert."""

    report = acoustic_stage_structural_report(solver)
    if not report["identity"]:
        raise TangentStructureError(
            "acoustic stage is NOT structurally identity on this geometry/config: "
            f"{report}; implement the A-stage JVP before running the tangent"
        )
    return report


# ---------------------------------------------------------------------------
# stage / block functions (production internals, verbatim order)
# ---------------------------------------------------------------------------

def block_macro_eq(f: np.ndarray, g: np.ndarray, mapping, lattice):
    """A3 block: macroscopic recovery + equilibrium construction."""

    m = recover_macro(f, g, D=mapping.lattice.D, S=mapping.lattice.S, lattice=lattice)
    f_eq, g_eq = equilibrium_fg(m.rho, m.u, m.theta, mapping.lattice.S, lattice)
    return m.rho, m.u, m.theta, f_eq, g_eq


def block_stress(f, f_eq, rho, u, theta, mapping, lattice):
    """A4 block: regularized stress collision + conserved-moment pinning."""

    f1 = _regularized_f_collision(
        f, f_eq, u, mapping, lattice, rho=rho, theta=theta, pressure_divergence=None
    )
    return _correct_f_conserved_moments(f1, f, lattice)


def block_heatflux_energy(f1, g_eq, f, g, u, mapping, lattice):
    """A5 block: heat-flux reconstruction + pinning + delta_G energy pin.

    The delta_G sub-map is an exactly linear functional of its inputs
    (E_tot = 0.5*sum(f |c|^2) + sum(g)); it is kept inside this block because
    the guide lists it as an A5 item -- its base dependence is structurally
    zero, which the contract tests assert."""

    D = mapping.lattice.D
    S = mapping.lattice.S
    f2, g_shape = _regularized_heat_flux_collision(f1, g_eq, f, g, u, mapping, lattice)
    f2 = _correct_f_conserved_moments(f2, f, lattice)
    macro_before = recover_macro(f, g, D=D, S=S, lattice=lattice)
    macro_mid = recover_macro(f2, g_shape, D=D, S=S, lattice=lattice)
    delta_g = macro_before.E_tot - macro_mid.E_tot
    return f2, g_shape + delta_g[..., None] * lattice.w


def compose_collide(f, g, mapping, lattice):
    """The C stage as the chained blocks; bitwise-identical to collide_fg
    (asserted in the contract tests; pressure-memory trace must be off)."""

    rho, u, theta, f_eq, g_eq = block_macro_eq(f, g, mapping, lattice)
    f1 = block_stress(f, f_eq, rho, u, theta, mapping, lattice)
    return block_heatflux_energy(f1, g_eq, f, g, u, mapping, lattice)


def stage_stream(f, g, lattice):
    """S stage: pull streaming (a permutation -- exactly linear)."""

    return pull_stream_fg(f, g, lattice=lattice, y_axis=0, x_axis=1)


def stage_band(solver: GasSolver2D, f_s: np.ndarray, g_s: np.ndarray,
               theta_hot: float, theta_amb: float, hs: int):
    """B stage: hot band (row 0) then sink band (row hs), with the EXACT
    bookkeeping observables of make_energy_audited_band (same expressions).

    Inputs are copied (the production reconstruction mutates in place)."""

    c2 = solver._tangent_c2 if hasattr(solver, "_tangent_c2") else np.sum(
        np.asarray(solver.lattice.c, dtype=float) ** 2, axis=-1)
    f_w = f_s.copy()
    g_w = g_s.copy()
    e0 = float(np.sum(0.5 * f_w * c2) + np.sum(g_w))
    f_w, g_w = _mass_neutral_reconstruct_row0_symmetric(
        solver, f_w, g_w, float(theta_hot), extrap="row1", row=0)
    e1 = float(np.sum(0.5 * f_w * c2) + np.sum(g_w))
    f_w, g_w = _mass_neutral_reconstruct_row0_symmetric(
        solver, f_w, g_w, float(theta_amb), extrap="row1", row=int(hs))
    e2 = float(np.sum(0.5 * f_w * c2) + np.sum(g_w))
    return f_w, g_w, e1 - e0, e2 - e1


def stage_filter(solver: GasSolver2D, f: np.ndarray, g: np.ndarray):
    """H stage: the solver's conservative biharmonic filter (exactly linear)."""

    for _ in range(solver.high_wavenumber_filter_passes):
        f = conservative_biharmonic_filter(
            f, solver.high_wavenumber_filter_strength, solver._filter_seam_window)
        g = conservative_biharmonic_filter(
            g, solver.high_wavenumber_filter_strength, solver._filter_seam_window)
    return f, g


def direct_step(solver: GasSolver2D, f, g, theta_hot: float, theta_amb: float, hs: int):
    """One full production step F(x, T_w) via the stage functions.

    Bitwise-identical to GasSolver2D.step with the composed audited band
    callbacks (asserted in the contract tests). Returns (f', g', hot_dE,
    sink_dE)."""

    f_c, g_c = compose_collide(f, g, solver.mapping, solver.lattice)
    f_s, g_s = stage_stream(f_c, g_c, solver.lattice)
    f_b, g_b, hot_de, sink_de = stage_band(solver, f_s, g_s, theta_hot, theta_amb, hs)
    # A stage: structurally identity (asserted by the caller at build time)
    f_h, g_h = stage_filter(solver, f_b, g_b)
    return f_h, g_h, hot_de, sink_de


# ---------------------------------------------------------------------------
# base-state snapshot and cached stage inputs
# ---------------------------------------------------------------------------

@dataclass
class BaseState:
    """Read-only DC base-state snapshot (guide section 4.1)."""

    f: np.ndarray
    g: np.ndarray
    theta_w: float          # hot-band mean setpoint theta_hot_mean
    theta_amb: float        # sink band temperature
    hs: int
    theta_dc_target: float
    meta: dict[str, Any]    # settle legality metrics + provenance


@dataclass
class StageBases:
    """Base intermediates at every stage/block boundary (guide section 4.1)."""

    f: np.ndarray
    g: np.ndarray
    rho: np.ndarray
    u: np.ndarray
    theta: np.ndarray
    f_eq: np.ndarray
    g_eq: np.ndarray
    f1: np.ndarray
    f2: np.ndarray
    g_post: np.ndarray
    s_f: np.ndarray
    s_g: np.ndarray
    b_f: np.ndarray
    b_g: np.ndarray
    hot_de: float
    sink_de: float
    h_f: np.ndarray
    h_g: np.ndarray
    r_f: float
    reference_triple: tuple[float, float, float, float]


def compute_stage_bases(solver: GasSolver2D, base: BaseState) -> StageBases:
    """Evaluate and cache every stage/block base input/output once."""

    mapping = solver.mapping
    lattice = solver.lattice
    rho, u, theta, f_eq, g_eq = block_macro_eq(base.f, base.g, mapping, lattice)
    f1 = block_stress(base.f, f_eq, rho, u, theta, mapping, lattice)
    f2, g_post = block_heatflux_energy(f1, g_eq, base.f, base.g, u, mapping, lattice)
    s_f, s_g = stage_stream(f2, g_post, lattice)
    b_f, b_g, hot_de, sink_de = stage_band(
        solver, s_f, s_g, base.theta_w, base.theta_amb, base.hs)
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


# ---------------------------------------------------------------------------
# tangent operator
# ---------------------------------------------------------------------------

class TangentOperator:
    """Chained stage/block JVP of the one-step operator on a frozen base.

    ``ablated`` names the blocks whose derivative is evaluated at the COLD
    base intermediates instead of the hot ones (guide section 6.1); everything
    else stays hot. "A0" = empty set. The hot and cold snapshots must share
    the geometry. All variants use the SAME chained instrument."""

    def __init__(self, solver: GasSolver2D, hot_base: BaseState, hot: StageBases,
                 cold_base: BaseState, cold: StageBases, *, h: float,
                 ablated: frozenset[str]):
        if hot_base.f.shape != cold_base.f.shape:
            raise TangentStructureError("hot/cold snapshots differ in geometry")
        unknown = set(ablated) - {b for bs in VARIANT_BLOCKS.values() for b in bs}
        if unknown:
            raise ValueError(f"unknown ablation blocks: {sorted(unknown)}")
        self.solver = solver
        self.hot_base = hot_base
        self.cold_base = cold_base
        self.hot = hot
        self.cold = cold
        self.h = float(h)
        self.ablated = frozenset(ablated)
        self.acoustic_report = assert_acoustic_stage_identity(solver)
        # pin the (inert, asserted-identity) phase-correction reference triple
        # so the +h/-h branches can never diverge through a lazily-computed
        # cache; A1 semantics = the cold triple (identity either way).
        triple = (cold if "acoustic_ref" in self.ablated else hot).reference_triple
        solver._ghost_projector_reference = triple
        lattice = solver.lattice
        self.c2 = np.sum(np.asarray(lattice.c, dtype=float) ** 2, axis=-1)
        solver._tangent_c2 = self.c2
        self.D = int(solver.mapping.lattice.D)
        self.S = int(solver.mapping.lattice.S)
        self.rho0 = float(solver.mapping.lattice.rho_ref_lu)
        self.theta0 = float(solver.mapping.theta_ref_lu)
        self.c0 = math.sqrt(float(solver.mapping.physical.gamma) * self.theta0)
        self.c_vec = np.asarray(lattice.c, dtype=float)
        # hot-base macro linearization fields for the normalization
        self._n_rho = self.hot.rho
        self._n_u = self.hot.u
        self._n_theta = self.hot.theta

    # -- pre-registered macro normalization (config jvp block) --
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

    def _bases(self, block: str) -> StageBases:
        return self.cold if block in self.ablated else self.hot

    def step(self, df: np.ndarray, dg: np.ndarray, d_theta_w: float):
        """Advance the tangent one step; returns (df', dg', d_hot_dE, d_sink_dE)."""

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

        # --- B stage (joint state + wall-temperature input JVP; A2 -> cold) ---
        bb = self._bases("band")
        base_b = self.cold_base if "band" in self.ablated else self.hot_base
        w_sf = h * inv * d_sf
        w_sg = h * inv * d_sg
        w_tw = h * inv * float(d_theta_w)
        bp = stage_band(self.solver, bb.s_f + w_sf, bb.s_g + w_sg,
                        base_b.theta_w + w_tw, base_b.theta_amb, base_b.hs)
        bm = stage_band(self.solver, bb.s_f - w_sf, bb.s_g - w_sg,
                        base_b.theta_w - w_tw, base_b.theta_amb, base_b.hs)
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


# ---------------------------------------------------------------------------
# tangent propagation (drive protocol verbatim) + conservation audits
# ---------------------------------------------------------------------------

def propagate_tangent(op: TangentOperator, *, frequency_hz: float,
                      drive_periods: float, samples_per_period: int,
                      log=None) -> dict[str, Any]:
    """Drive the tangent with d(theta_w) = th0*ramp*cos(Omega t) and read the
    exact-bookkeeping tangent observables (guide section 4.4).

    Sampling, ramp and windows mirror scripts/phase5_g4a_dc_basestate.py::
    run_tent verbatim. Returns a run-like dict consumable by fit_admittance,
    plus the V5 audit worst cases."""

    solver = op.solver
    dt_s = float(solver.mapping.lattice.dt_s)
    th0 = op.theta0
    steps_per_period = int(round(1.0 / (frequency_hz * dt_s)))
    sample_every = max(1, steps_per_period // int(samples_per_period))
    om_si = 2.0 * math.pi * frequency_hz
    n_drive = int(round(drive_periods * steps_per_period))

    df = np.zeros_like(op.hot_base.f)
    dg = np.zeros_like(op.hot_base.g)
    t_samp: list[float] = []
    thw_samp: list[float] = []
    qhot_samp: list[float] = []
    qsink_samp: list[float] = []
    mass_worst = 0.0
    grid_mass = float(np.sum(op.hot_base.f))   # V5 normalization scale
    energy_acct_worst = 0.0
    q_scale = 1e-300
    for i in range(n_drive):
        t = i / steps_per_period
        ramp = 0.5 * (1.0 - math.cos(math.pi * min(1.0, t))) if t < 1.0 else 1.0
        phase = om_si * (i * dt_s)
        d_thw = th0 * ramp * math.cos(phase)
        e_before = float(np.sum(0.5 * df * op.c2) + np.sum(dg))
        df, dg, dqh, dqs = op.step(df, dg, d_thw)
        if not (np.isfinite(dqh) and np.isfinite(dqs)):
            raise FloatingPointError("non-finite tangent bookkeeping")
        e_after = float(np.sum(0.5 * df * op.c2) + np.sum(dg))
        q_scale = max(q_scale, abs(dqh), abs(dqs))
        energy_acct_worst = max(
            energy_acct_worst, abs(e_after - e_before - dqh - dqs) / q_scale)
        mass_worst = max(mass_worst, abs(float(np.sum(df))) / grid_mass)
        if i % sample_every == 0:
            t_samp.append(i * dt_s)
            thw_samp.append(d_thw)
            qhot_samp.append(dqh)
            qsink_samp.append(dqs)
            if not np.all(np.isfinite(df[0])):
                raise FloatingPointError("non-finite tangent state")
        if log is not None and steps_per_period >= 4 \
                and i % (steps_per_period // 4) == 0:
            log(f"tangent step {i}/{n_drive} |dq_hot|={abs(dqh):.3e}")
    return {
        "drive": {
            "t_s": np.array(t_samp),
            "theta_w": np.array(thw_samp),
            "q_hot_lu": np.array(qhot_samp),
            "q_sink_lu": np.array(qsink_samp),
        },
        "rho0": op.rho0,
        "cp_eff": 0.5 * (op.D + op.S) + 1.0,
        "nx": int(solver.nx),
        "finite": True,
        "audits": {
            "mass_tangent_rel_worst": mass_worst,
            "energy_account_rel_worst": energy_acct_worst,
        },
        "steps_per_period": steps_per_period,
    }


# ---------------------------------------------------------------------------
# V1 probe: +h/-h odd/even decomposition of the FULL one-step operator
# ---------------------------------------------------------------------------

def make_probe(shape_f, shape_g, seed: int = 20260808):
    """Deterministic pseudo-random probe (state + unit wall-temperature input)."""

    rng = np.random.default_rng(seed)
    vf = rng.standard_normal(shape_f)
    vg = rng.standard_normal(shape_g)
    return vf, vg, 1.0


def v1_odd_even_probe(solver: GasSolver2D, base: BaseState, bases: StageBases,
                      h_values: list[float], *, seed: int = 20260808,
                      ablated: frozenset[str] = frozenset()) -> dict[str, Any]:
    """Guide V1: odd combinations stable, even combinations decay ~h^2.

    Uses the singleshot full-step F for the odd/even split and the chained
    operator for the chain-vs-singleshot consistency row. The probe direction
    is normalized with the pre-registered macro scale before h is applied."""

    vf, vg, eta = make_probe(base.f.shape, base.g.shape, seed)
    op0 = TangentOperator(solver, base, bases, base, bases, h=h_values[0],
                          ablated=ablated)
    s = op0.macro_scale(vf, vg, eta)
    vf = vf / s
    vg = vg / s
    eta = eta / s
    f0, g0, q0h, q0s = direct_step(solver, base.f, base.g, base.theta_w,
                                   base.theta_amb, base.hs)
    rows = []
    odd_vecs = []
    for h in h_values:
        fp, gp, qhp, qsp = direct_step(solver, base.f + h * vf, base.g + h * vg,
                                       base.theta_w + h * eta, base.theta_amb, base.hs)
        fm, gm, qhm, qsm = direct_step(solver, base.f - h * vf, base.g - h * vg,
                                       base.theta_w - h * eta, base.theta_amb, base.hs)
        odd = np.concatenate([(fp - fm).ravel(), (gp - gm).ravel()]) / (2.0 * h)
        even = np.concatenate([(fp + fm - 2.0 * f0).ravel(),
                               (gp + gm - 2.0 * g0).ravel()])
        op = TangentOperator(solver, base, bases, base, bases, h=h, ablated=ablated)
        cf, cg, cqh, cqs = op.step(vf * s, vg * s, eta * s)
        chain = np.concatenate([cf.ravel(), cg.ravel()]) / s
        rows.append({
            "h": float(h),
            "odd_norm": float(np.linalg.norm(odd)),
            "even_norm": float(np.linalg.norm(even)),
            "dq_hot_odd": float((qhp - qhm) / (2.0 * h)),
            "chain_vs_singleshot_rel": float(
                np.linalg.norm(chain - odd) / max(np.linalg.norm(odd), 1e-300)),
        })
        odd_vecs.append(odd)
    pair_rel = []
    for i in range(len(h_values) - 1):
        denom = max(np.linalg.norm(odd_vecs[i]), 1e-300)
        pair_rel.append(float(np.linalg.norm(odd_vecs[i + 1] - odd_vecs[i]) / denom))
    even_ratio = []
    for i in range(len(h_values) - 1):
        lo = rows[i + 1]["even_norm"]
        even_ratio.append(float(rows[i]["even_norm"] / lo) if lo > 0 else float("inf"))
    return {"rows": rows, "odd_pairwise_rel": pair_rel, "even_ratios": even_ratio,
            "probe_seed": seed, "scale_applied": float(s)}
