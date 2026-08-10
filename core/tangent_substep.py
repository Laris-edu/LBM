"""WP4-JAB round-2 sub-map tangent layer (fine-grained A2/A3 dissection).

Plan: docs/Phase_5/WP4_JAB_next_simulation_guide_simple.md (PLAN_v1.1, step 0).
Round-1 instrument (core/tangent_step.py) is FROZEN as executed; this module
adds the finer decomposition WITHOUT touching it:

  band reconstruction  -> L (rho_w linear extraction)
                          W (wall equilibrium; slots rho_w [A2-1], theta_w [A2-2])
                          N (neighbour non-equilibrium copy + blend   [A2-3])
                          C (mass/momentum equilibrium-increment cleanup [A2-4])
                          P (internal-energy target + g repinning     [A2-5])
  macro/equilibrium    -> R (rho linear extraction)
                          U (u = j/rho; slot rho                      [A3-2])
                          T (theta recovery; slot rho                 [A3-1])
                          E1 (f_eq construction; slot theta           [A3-3])
                          E2 (g_eq construction; all slots            [A3-4])

Every sub-map calls the SAME production ingredients (equilibrium_fg,
recover_macro-equivalent expressions, bottom_wall_stencil) in the SAME
floating-point order; ``compose_band_row`` and ``compose_macro_eq`` are
asserted bitwise-identical to the production functions in the contract tests.

The round-2 JVP is uniformly SLOT-SEPARATED central differences: for a
sub-map M(x1..xk) the Jacobian action is the sum over input slots of a
central difference in that slot alone, each slot evaluated at the hot or the
cold base per the variant (guide section 6.1 mixed-tangent semantics, one
level deeper). A0 under this instrument differs from round 1 at FD-noise
order only and MUST re-pass the V4 identity gate (plan step 0.3).

The guide section 7.2 legality invariants (mass neutrality, zero wall
velocity, wall-temperature pinning) hold per sub-variant BY CONSTRUCTION of
W/C/P (asserted per-step in the runner's V5-family audits and in the tests).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from boundary.wall_common import bottom_wall_stencil
from core.equilibrium import equilibrium_fg
from core.solver import GasSolver2D
from core.tangent_step import (
    BaseState,
    StageBases,
    TangentStructureError,
    assert_acoustic_stage_identity,
    block_heatflux_energy,
    block_stress,
    compute_stage_bases,
    stage_filter,
    stage_stream,
)

# ---------------------------------------------------------------------------
# round-2 variant catalogue: variant -> set of (group, submap, slot) frozen cold
# ("*" = every slot of that sub-map). Frozen in the round-2 config.
# ---------------------------------------------------------------------------

R2_SINGLE_VARIANTS: dict[str, frozenset[tuple[str, str, str]]] = {
    "A0r2": frozenset(),
    "A2-1": frozenset({("band", "W", "rho_w")}),
    "A2-2": frozenset({("band", "W", "theta_w")}),
    "A2-3": frozenset({("band", "N", "*")}),
    "A2-4": frozenset({("band", "C", "*")}),
    "A2-5": frozenset({("band", "P", "*")}),
    "A3-1": frozenset({("macro", "T", "rho")}),
    "A3-2": frozenset({("macro", "U", "rho")}),
    "A3-3": frozenset({("macro", "E1", "theta")}),
    "A3-4": frozenset({("macro", "E2", "*")}),
    # structural-zero negative control: L and R are exactly linear extractions
    "CTRLr2": frozenset({("band", "L", "*"), ("macro", "R", "*")}),
    # block-union anchors: must reproduce the round-1 whole-block ablations
    "A2ALL": frozenset({("band", "L", "*"), ("band", "W", "*"),
                        ("band", "N", "*"), ("band", "C", "*"),
                        ("band", "P", "*")}),
    "A3ALL": frozenset({("macro", "R", "*"), ("macro", "U", "*"),
                        ("macro", "T", "*"), ("macro", "E1", "*"),
                        ("macro", "E2", "*")}),
}


def r2_ablated_slots(variant: str) -> frozenset[tuple[str, str, str]]:
    """Resolve a round-2 variant name or '+'-combo to frozen slots (fail-loud)."""

    parts = [p.strip() for p in str(variant).split("+") if p.strip()]
    if not parts:
        raise ValueError(f"empty round-2 variant name: {variant!r}")
    slots: set[tuple[str, str, str]] = set()
    for p in parts:
        if p not in R2_SINGLE_VARIANTS:
            raise ValueError(f"unknown round-2 variant: {p!r} (from {variant!r})")
        slots |= R2_SINGLE_VARIANTS[p]
    return frozenset(slots)


# ---------------------------------------------------------------------------
# band sub-maps (production expressions verbatim; row-local pure functions)
# ---------------------------------------------------------------------------

def band_sub_L(f_row: np.ndarray) -> np.ndarray:
    """L: column-wise streamed wall-row density (exactly linear)."""

    return np.sum(f_row, axis=-1)                      # (1, nx)


def band_sub_W(rho_w: np.ndarray, theta_w: float, solver: GasSolver2D):
    """W: wall equilibrium at (rho_w, u=0, theta_w) (production lines)."""

    if theta_w <= 0.0:
        raise ValueError("wall temperature must be positive")
    if not np.all(rho_w > 0.0):
        raise RuntimeError("non-positive streamed wall-row density")
    nx = rho_w.shape[1]
    theta_row = np.full((1, nx), float(theta_w))
    return equilibrium_fg(rho_w, np.zeros((1, nx, 2)), theta_row,
                          solver.mapping.lattice.S, solver.lattice)


def band_sub_N(f_up, g_up, f_dn, g_dn, solver: GasSolver2D):
    """N: per-direction non-equilibrium copy + stencil blend (extrap='row1')."""

    from core.macroscopic import recover_macro

    lattice = solver.lattice
    D = int(solver.mapping.lattice.D)
    S = int(solver.mapping.lattice.S)

    def neq(fj, gj):
        m = recover_macro(fj, gj, D=D, S=S, lattice=lattice)
        feq_j, geq_j = equilibrium_fg(m.rho, m.u, m.theta, S, lattice)
        return fj - feq_j, gj - geq_j

    up_f, up_g = neq(f_up, g_up)
    dn_f, dn_g = neq(f_dn, g_dn)
    st = bottom_wall_stencil(lattice)
    f_neq = np.empty_like(up_f)
    g_neq = np.empty_like(up_g)
    f_neq[..., st.incoming] = up_f[..., st.incoming]
    g_neq[..., st.incoming] = up_g[..., st.incoming]
    f_neq[..., st.outgoing] = dn_f[..., st.outgoing]
    g_neq[..., st.outgoing] = dn_g[..., st.outgoing]
    f_neq[..., st.grazing] = 0.5 * (up_f + dn_f)[..., st.grazing]
    g_neq[..., st.grazing] = 0.5 * (up_g + dn_g)[..., st.grazing]
    return f_neq, g_neq


def band_sub_C(f_neq, g_neq, rho_w, feq_w, geq_w, theta_w: float,
               solver: GasSolver2D):
    """C: exact mass/momentum removal via the equilibrium increment."""

    lattice = solver.lattice
    c = np.asarray(lattice.c, dtype=float)
    nx = rho_w.shape[1]
    drho = np.sum(f_neq, axis=-1)
    dj = np.einsum("yxq,qd->yxd", f_neq, c)
    rho_pert = rho_w + drho
    if not np.all(rho_pert > 0.0):
        raise RuntimeError("blended non-equilibrium exceeds wall density")
    u_pert = dj / rho_pert[..., None]
    theta_row = np.full((1, nx), float(theta_w))
    feq_pert, geq_pert = equilibrium_fg(rho_pert, u_pert, theta_row,
                                        solver.mapping.lattice.S, lattice)
    return f_neq - (feq_pert - feq_w), g_neq - (geq_pert - geq_w)


def band_sub_P(f_neq, g_neq, rho_w, feq_w, geq_w, theta_w: float,
               solver: GasSolver2D):
    """P: internal-energy target + uniform g repinning (production lines)."""

    lattice = solver.lattice
    D = int(solver.mapping.lattice.D)
    S = int(solver.mapping.lattice.S)
    q = int(lattice.q)
    c2 = np.sum(np.asarray(lattice.c, dtype=float) ** 2, axis=-1)
    f0 = feq_w + f_neq
    k_tr = 0.5 * np.sum(f0 * c2, axis=-1)
    g_partial = np.sum(geq_w, axis=-1) + np.sum(g_neq, axis=-1)
    target_int = 0.5 * (D + S) * rho_w * theta_w
    delta = (target_int - k_tr - g_partial) / q
    return f0, geq_w + g_neq + delta[..., None]


def compose_band_row(solver: GasSolver2D, f_stream: np.ndarray,
                     g_stream: np.ndarray, theta_w: float, row: int):
    """The v1.1 symmetric band via the sub-maps; bitwise == production
    _mass_neutral_reconstruct_row0_symmetric (contract-test anchored).
    Non-mutating: returns fresh arrays."""

    ny = int(solver.ny)
    row = int(row) % ny
    up = (row + 1) % ny
    dn = (row - 1) % ny
    rho_w = band_sub_L(f_stream[row:row + 1])
    feq_w, geq_w = band_sub_W(rho_w, theta_w, solver)
    f_neq, g_neq = band_sub_N(f_stream[up:up + 1], g_stream[up:up + 1],
                              f_stream[dn:dn + 1], g_stream[dn:dn + 1], solver)
    f_neq, g_neq = band_sub_C(f_neq, g_neq, rho_w, feq_w, geq_w, theta_w, solver)
    f0, g0 = band_sub_P(f_neq, g_neq, rho_w, feq_w, geq_w, theta_w, solver)
    out_f = f_stream.copy()
    out_g = g_stream.copy()
    out_f[row:row + 1] = f0
    out_g[row:row + 1] = g0
    return out_f, out_g


# ---------------------------------------------------------------------------
# macro/equilibrium sub-maps (production expressions verbatim)
# ---------------------------------------------------------------------------

def macro_sub_R(f: np.ndarray) -> np.ndarray:
    """R: density (exactly linear)."""

    return np.sum(np.asarray(f, dtype=float), axis=-1)


def macro_sub_U(f: np.ndarray, rho: np.ndarray, lattice) -> np.ndarray:
    """U: u = j/rho (slot 'rho' carries the A3-2 density cross term)."""

    momentum = np.einsum("...a,ai->...i", np.asarray(f, dtype=float), lattice.c)
    return momentum / rho[..., None]


def macro_sub_T(f, g, u, rho, *, D: int, S: int, lattice) -> np.ndarray:
    """T: theta = 2(K_tr+G_int)/((D+S) rho) (slot 'rho' = A3-1 cross term)."""

    peculiar = lattice.c - np.asarray(u, dtype=float)[..., None, :]
    c2 = np.sum(peculiar ** 2, axis=-1)
    k_tr = 0.5 * np.sum(np.asarray(f, dtype=float) * c2, axis=-1)
    g_int = np.sum(np.asarray(g, dtype=float), axis=-1)
    return 2.0 * (k_tr + g_int) / ((D + S) * rho)


def macro_sub_E1(rho, u, theta, *, S: int, lattice) -> np.ndarray:
    """E1: f_eq construction (slot 'theta' = A3-3 temperature moments)."""

    f_eq, _ = equilibrium_fg(rho, u, theta, S, lattice)
    return f_eq


def macro_sub_E2(rho, u, theta, *, S: int, lattice) -> np.ndarray:
    """E2: g_eq construction (A3-4: rho*theta zeroth moment + higher)."""

    _, g_eq = equilibrium_fg(rho, u, theta, S, lattice)
    return g_eq


def compose_macro_eq(f, g, mapping, lattice):
    """block_macro_eq via the sub-maps; bitwise == core.tangent_step.block_macro_eq
    (contract-test anchored). Note E1/E2 call equilibrium_fg once each; the
    equality holds because equilibrium_fg is deterministic on identical inputs."""

    D = int(mapping.lattice.D)
    S = int(mapping.lattice.S)
    rho = macro_sub_R(f)
    u = macro_sub_U(f, rho, lattice)
    theta = macro_sub_T(f, g, u, rho, D=D, S=S, lattice=lattice)
    f_eq = macro_sub_E1(rho, u, theta, S=S, lattice=lattice)
    g_eq = macro_sub_E2(rho, u, theta, S=S, lattice=lattice)
    return rho, u, theta, f_eq, g_eq


# ---------------------------------------------------------------------------
# slot-separated JVP helper
# ---------------------------------------------------------------------------

def slot_jvp(fn, bases_hot: list, bases_cold: list, deltas: list,
             cold_slots: set[int], *, h: float, inv: float, scale: float,
             n_out: int):
    """Joint central-difference JVP of ``fn`` at the MIXED base point.

    Slot i's base is the cold one iff i in cold_slots; the evaluation point
    P carries every slot at its own (hot/cold) base and ONE +/-h pair
    perturbs all active slots jointly:

        [fn(P + h v) - fn(P - h v)] / (2h)  =  sum_i dfn/dx_i|_P . d_i + O(h^2)

    This is the same estimand as the per-slot difference sum (every slot's
    derivative is taken at the same mixed point P either way) at ~1/k the
    cost, and the FD expression STRUCTURE is variant-independent -- with
    hot == cold bases every variant reproduces A0r2 bitwise (contract-test
    anchor). Zero-delta slots are skipped. Returns ``n_out`` output deltas."""

    def base_at(j: int):
        return (bases_cold if j in cold_slots else bases_hot)[j]

    active = [i for i, d in enumerate(deltas)
              if not (d is None or (np.isscalar(d) and d == 0.0)
                      or (not np.isscalar(d) and not np.any(d)))]
    if not active:
        r0 = fn(*[base_at(j) for j in range(len(deltas))])
        if not isinstance(r0, tuple):
            r0 = (r0,)
        outs = [0.0 if np.isscalar(r) else np.zeros_like(np.asarray(r))
                for r in r0]
    else:
        args_p = [base_at(j) for j in range(len(deltas))]
        args_m = list(args_p)
        for i in active:
            step = (h * inv) * deltas[i]
            args_p[i] = args_p[i] + step
            args_m[i] = args_m[i] - step
        rp = fn(*args_p)
        rm = fn(*args_m)
        if not isinstance(rp, tuple):
            rp, rm = (rp,), (rm,)
        outs = [(a - b) * scale for a, b in zip(rp, rm)]
    if len(outs) != n_out:
        raise TangentStructureError(
            f"slot_jvp arity mismatch: got {len(outs)}, expected {n_out}")
    return outs


# ---------------------------------------------------------------------------
# cached sub-map base values (hot/cold) per band instance and macro block
# ---------------------------------------------------------------------------

@dataclass
class BandSubBases:
    """Base values of every band sub-map input/output at one band instance."""

    f_row: np.ndarray
    g_row: np.ndarray
    f_up: np.ndarray
    g_up: np.ndarray
    f_dn: np.ndarray
    g_dn: np.ndarray
    theta_w: float
    rho_w: np.ndarray
    feq_w: np.ndarray
    geq_w: np.ndarray
    f_neq_blend: np.ndarray
    g_neq_blend: np.ndarray
    f_neq_clean: np.ndarray
    g_neq_clean: np.ndarray
    f0: np.ndarray
    g0: np.ndarray


def compute_band_sub_bases(solver: GasSolver2D, f_stream: np.ndarray,
                           g_stream: np.ndarray, theta_w: float,
                           row: int) -> BandSubBases:
    ny = int(solver.ny)
    row = int(row) % ny
    up = (row + 1) % ny
    dn = (row - 1) % ny
    f_row = f_stream[row:row + 1]
    g_row = g_stream[row:row + 1]
    f_up, g_up = f_stream[up:up + 1], g_stream[up:up + 1]
    f_dn, g_dn = f_stream[dn:dn + 1], g_stream[dn:dn + 1]
    rho_w = band_sub_L(f_row)
    feq_w, geq_w = band_sub_W(rho_w, theta_w, solver)
    f_nb, g_nb = band_sub_N(f_up, g_up, f_dn, g_dn, solver)
    f_nc, g_nc = band_sub_C(f_nb, g_nb, rho_w, feq_w, geq_w, theta_w, solver)
    f0, g0 = band_sub_P(f_nc, g_nc, rho_w, feq_w, geq_w, theta_w, solver)
    return BandSubBases(f_row=f_row, g_row=g_row, f_up=f_up, g_up=g_up,
                        f_dn=f_dn, g_dn=g_dn, theta_w=float(theta_w),
                        rho_w=rho_w, feq_w=feq_w, geq_w=geq_w,
                        f_neq_blend=f_nb, g_neq_blend=g_nb,
                        f_neq_clean=f_nc, g_neq_clean=g_nc, f0=f0, g0=g0)


@dataclass
class MacroSubBases:
    """Base values of the macro/equilibrium sub-map chain."""

    f: np.ndarray
    g: np.ndarray
    rho: np.ndarray
    u: np.ndarray
    theta: np.ndarray
    f_eq: np.ndarray
    g_eq: np.ndarray


def compute_macro_sub_bases(solver: GasSolver2D, f: np.ndarray,
                            g: np.ndarray) -> MacroSubBases:
    rho, u, theta, f_eq, g_eq = compose_macro_eq(f, g, solver.mapping,
                                                 solver.lattice)
    return MacroSubBases(f=f, g=g, rho=rho, u=u, theta=theta,
                         f_eq=f_eq, g_eq=g_eq)


@dataclass
class R2Bases:
    """Round-2 base bundle: round-1 stage bases + sub-map bases."""

    stage: StageBases
    macro: MacroSubBases
    band_hot: BandSubBases     # hot band instance (row 0) on post-stream state
    band_sink: BandSubBases    # sink band instance (row hs) on post-hot state


def compute_r2_bases(solver: GasSolver2D, base: BaseState) -> R2Bases:
    stage = compute_stage_bases(solver, base)
    macro = compute_macro_sub_bases(solver, base.f, base.g)
    band_hot = compute_band_sub_bases(solver, stage.s_f, stage.s_g,
                                      base.theta_w, 0)
    # sink instance sees the post-hot-band state (production order)
    f_mid = stage.s_f.copy()
    g_mid = stage.s_g.copy()
    f_mid[0:1] = band_hot.f0
    g_mid[0:1] = band_hot.g0
    band_sink = compute_band_sub_bases(solver, f_mid, g_mid,
                                       base.theta_amb, base.hs)
    return R2Bases(stage=stage, macro=macro, band_hot=band_hot,
                   band_sink=band_sink)


# ---------------------------------------------------------------------------
# round-2 tangent operator (slot-separated chained JVP)
# ---------------------------------------------------------------------------

class R2TangentOperator:
    """Fine-grained tangent: macro sub-chain + A4/A5 blocks + band sub-chains.

    Slots listed in ``ablated`` take their base from the COLD bundle; all
    other slots stay hot. The instrument is uniformly slot-separated, so A0r2
    must re-pass the V4 identity gate (plan step 0.3)."""

    def __init__(self, solver: GasSolver2D, hot_base: BaseState, hot: R2Bases,
                 cold_base: BaseState, cold: R2Bases, *, h: float,
                 ablated: frozenset):
        if hot_base.f.shape != cold_base.f.shape:
            raise TangentStructureError("hot/cold snapshots differ in geometry")
        known = {s for ss in R2_SINGLE_VARIANTS.values() for s in ss}
        unknown = {s for s in ablated if s not in known}
        if unknown:
            raise ValueError(f"unknown round-2 slots: {sorted(unknown)}")
        self.solver = solver
        self.hot_base = hot_base
        self.cold_base = cold_base
        self.hot = hot
        self.cold = cold
        self.h = float(h)
        self.ablated = frozenset(ablated)
        self.acoustic_report = assert_acoustic_stage_identity(solver)
        lattice = solver.lattice
        self.c2 = np.sum(np.asarray(lattice.c, dtype=float) ** 2, axis=-1)
        self.c_vec = np.asarray(lattice.c, dtype=float)
        self.D = int(solver.mapping.lattice.D)
        self.S = int(solver.mapping.lattice.S)
        self.rho0 = float(solver.mapping.lattice.rho_ref_lu)
        self.theta0 = float(solver.mapping.theta_ref_lu)
        self.c0 = math.sqrt(float(solver.mapping.physical.gamma) * self.theta0)

    def _cold_slots(self, group: str, submap: str,
                    slot_names: list[str]) -> set[int]:
        cold: set[int] = set()
        for i, name in enumerate(slot_names):
            if (group, submap, "*") in self.ablated \
                    or (group, submap, name) in self.ablated:
                cold.add(i)
        return cold

    # -- macro normalization (round-1 formula verbatim, hot-base fields) --
    def macro_scale(self, df, dg, d_theta_w: float) -> float:
        m = self.hot.macro
        drho = np.sum(df, axis=-1)
        dj = np.einsum("yxq,qd->yxd", df, self.c_vec)
        du = (dj - m.u * drho[..., None]) / m.rho[..., None]
        de = 0.5 * np.sum(df * self.c2, axis=-1) + np.sum(dg, axis=-1)
        de_int = de - np.einsum("yxd,yxd->yx", m.u, dj) \
            + 0.5 * np.sum(m.u ** 2, axis=-1) * drho
        dtheta = 2.0 * de_int / ((self.D + self.S) * m.rho) \
            - m.theta * drho / m.rho
        return float(max(
            np.max(np.abs(drho)) / self.rho0,
            np.max(np.abs(dtheta)) / self.theta0,
            np.max(np.abs(du)) / self.c0,
            abs(float(d_theta_w)) / self.theta0,
        ))

    def _band_jvp(self, bases_hot: BandSubBases, bases_cold: BandSubBases,
                  d_full_f, d_full_g, d_theta_w: float, row: int,
                  *, h, inv, scale):
        ny = int(self.solver.ny)
        row = int(row) % ny
        up, dn = (row + 1) % ny, (row - 1) % ny
        d_frow = d_full_f[row:row + 1]
        d_grow = d_full_g[row:row + 1]
        d_fup, d_gup = d_full_f[up:up + 1], d_full_g[up:up + 1]
        d_fdn, d_gdn = d_full_f[dn:dn + 1], d_full_g[dn:dn + 1]

        def cs(sm, names):
            return self._cold_slots("band", sm, names)

        (d_rho_w,) = slot_jvp(band_sub_L, [bases_hot.f_row], [bases_cold.f_row],
                              [d_frow], cs("L", ["f_row"]),
                              h=h, inv=inv, scale=scale, n_out=1)
        d_feq_w, d_geq_w = slot_jvp(
            lambda rw, tw: band_sub_W(rw, tw, self.solver),
            [bases_hot.rho_w, bases_hot.theta_w],
            [bases_cold.rho_w, bases_cold.theta_w],
            [d_rho_w, d_theta_w], cs("W", ["rho_w", "theta_w"]),
            h=h, inv=inv, scale=scale, n_out=2)
        d_fnb, d_gnb = slot_jvp(
            lambda a, b, c, d: band_sub_N(a, b, c, d, self.solver),
            [bases_hot.f_up, bases_hot.g_up, bases_hot.f_dn, bases_hot.g_dn],
            [bases_cold.f_up, bases_cold.g_up, bases_cold.f_dn, bases_cold.g_dn],
            [d_fup, d_gup, d_fdn, d_gdn],
            cs("N", ["f_up", "g_up", "f_dn", "g_dn"]),
            h=h, inv=inv, scale=scale, n_out=2)
        d_fnc, d_gnc = slot_jvp(
            lambda fn_, gn_, rw, fw, gw, tw: band_sub_C(
                fn_, gn_, rw, fw, gw, tw, self.solver),
            [bases_hot.f_neq_blend, bases_hot.g_neq_blend, bases_hot.rho_w,
             bases_hot.feq_w, bases_hot.geq_w, bases_hot.theta_w],
            [bases_cold.f_neq_blend, bases_cold.g_neq_blend, bases_cold.rho_w,
             bases_cold.feq_w, bases_cold.geq_w, bases_cold.theta_w],
            [d_fnb, d_gnb, d_rho_w, d_feq_w, d_geq_w, d_theta_w],
            cs("C", ["f_neq", "g_neq", "rho_w", "feq_w", "geq_w", "theta_w"]),
            h=h, inv=inv, scale=scale, n_out=2)
        d_f0, d_g0 = slot_jvp(
            lambda fn_, gn_, rw, fw, gw, tw: band_sub_P(
                fn_, gn_, rw, fw, gw, tw, self.solver),
            [bases_hot.f_neq_clean, bases_hot.g_neq_clean, bases_hot.rho_w,
             bases_hot.feq_w, bases_hot.geq_w, bases_hot.theta_w],
            [bases_cold.f_neq_clean, bases_cold.g_neq_clean, bases_cold.rho_w,
             bases_cold.feq_w, bases_cold.geq_w, bases_cold.theta_w],
            [d_fnc, d_gnc, d_rho_w, d_feq_w, d_geq_w, d_theta_w],
            cs("P", ["f_neq", "g_neq", "rho_w", "feq_w", "geq_w", "theta_w"]),
            h=h, inv=inv, scale=scale, n_out=2)
        dq = float(np.sum(0.5 * (d_f0 - d_frow) * self.c2)
                   + np.sum(d_g0 - d_grow))
        d_out_f = d_full_f.copy()
        d_out_g = d_full_g.copy()
        d_out_f[row:row + 1] = d_f0
        d_out_g[row:row + 1] = d_g0
        return d_out_f, d_out_g, dq

    def step(self, df, dg, d_theta_w: float):
        """One round-2 tangent step; returns (df', dg', d_hot_dE, d_sink_dE)."""

        h = self.h
        s = self.macro_scale(df, dg, d_theta_w)
        if s <= 0.0 or not math.isfinite(s):
            if not math.isfinite(s):
                raise FloatingPointError("non-finite tangent state")
            return (np.zeros_like(df), np.zeros_like(dg), 0.0, 0.0)
        inv = 1.0 / s
        scale = s / (2.0 * h)
        solver = self.solver
        mapping = solver.mapping
        lattice = solver.lattice
        hb, cb = self.hot, self.cold

        def cs(sm, names):
            return self._cold_slots("macro", sm, names)

        # --- C stage: macro sub-chain (R, U, T, E1, E2) ---
        (d_rho,) = slot_jvp(macro_sub_R, [hb.macro.f], [cb.macro.f], [df],
                            cs("R", ["f"]), h=h, inv=inv, scale=scale, n_out=1)
        (d_u,) = slot_jvp(lambda f_, r_: macro_sub_U(f_, r_, lattice),
                          [hb.macro.f, hb.macro.rho],
                          [cb.macro.f, cb.macro.rho], [df, d_rho],
                          cs("U", ["f", "rho"]),
                          h=h, inv=inv, scale=scale, n_out=1)
        (d_theta,) = slot_jvp(
            lambda f_, g_, u_, r_: macro_sub_T(
                f_, g_, u_, r_, D=self.D, S=self.S, lattice=lattice),
            [hb.macro.f, hb.macro.g, hb.macro.u, hb.macro.rho],
            [cb.macro.f, cb.macro.g, cb.macro.u, cb.macro.rho],
            [df, dg, d_u, d_rho], cs("T", ["f", "g", "u", "rho"]),
            h=h, inv=inv, scale=scale, n_out=1)
        (d_feq,) = slot_jvp(
            lambda r_, u_, t_: macro_sub_E1(r_, u_, t_, S=self.S, lattice=lattice),
            [hb.macro.rho, hb.macro.u, hb.macro.theta],
            [cb.macro.rho, cb.macro.u, cb.macro.theta],
            [d_rho, d_u, d_theta], cs("E1", ["rho", "u", "theta"]),
            h=h, inv=inv, scale=scale, n_out=1)
        (d_geq,) = slot_jvp(
            lambda r_, u_, t_: macro_sub_E2(r_, u_, t_, S=self.S, lattice=lattice),
            [hb.macro.rho, hb.macro.u, hb.macro.theta],
            [cb.macro.rho, cb.macro.u, cb.macro.theta],
            [d_rho, d_u, d_theta], cs("E2", ["rho", "u", "theta"]),
            h=h, inv=inv, scale=scale, n_out=1)

        # --- A4 stress block (joint FD, always hot in round 2) ---
        st = hb.stage
        vf = h * inv * df
        vg = h * inv * dg
        f1_p = block_stress(st.f + vf, st.f_eq + h * inv * d_feq,
                            st.rho + h * inv * d_rho, st.u + h * inv * d_u,
                            st.theta + h * inv * d_theta, mapping, lattice)
        f1_m = block_stress(st.f - vf, st.f_eq - h * inv * d_feq,
                            st.rho - h * inv * d_rho, st.u - h * inv * d_u,
                            st.theta - h * inv * d_theta, mapping, lattice)
        d_f1 = (f1_p - f1_m) * scale
        # --- A5 heat-flux + energy block (joint FD, hot) ---
        p5 = block_heatflux_energy(st.f1 + h * inv * d_f1, st.g_eq + h * inv * d_geq,
                                   st.f + vf, st.g + vg, st.u + h * inv * d_u,
                                   mapping, lattice)
        m5 = block_heatflux_energy(st.f1 - h * inv * d_f1, st.g_eq - h * inv * d_geq,
                                   st.f - vf, st.g - vg, st.u - h * inv * d_u,
                                   mapping, lattice)
        d_f2 = (p5[0] - m5[0]) * scale
        d_gpost = (p5[1] - m5[1]) * scale

        # --- S stage (exact linear) ---
        d_sf, d_sg = stage_stream(d_f2, d_gpost, lattice)

        # --- B stage: hot band then sink band (sub-chained) ---
        d_bf, d_bg, d_hot = self._band_jvp(
            hb.band_hot, cb.band_hot, d_sf, d_sg,
            float(d_theta_w), 0, h=h, inv=inv, scale=scale)
        d_bf, d_bg, d_sink = self._band_jvp(
            hb.band_sink, cb.band_sink, d_bf, d_bg,
            0.0, self.hot_base.hs, h=h, inv=inv, scale=scale)

        # --- A structurally identity; H exact linear ---
        d_hf, d_hg = stage_filter(solver, d_bf, d_bg)
        return d_hf, d_hg, d_hot, d_sink
