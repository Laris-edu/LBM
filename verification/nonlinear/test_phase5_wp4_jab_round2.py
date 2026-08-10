"""WP4-JAB round-2 contract tests (plan step 0; sub-map instrument anchors).

Anchors and failing-first requirements for the fine-grained A2/A3 dissection
(docs/Phase_5/WP4_JAB_next_simulation_guide_simple.md, PLAN_v1.1):

  1  compose_band_row  == production v1.1 reconstruction (bitwise);
  2  compose_macro_eq  == round-1 block_macro_eq (bitwise);
  3  A0r2 (slot-separated instrument) == round-1 A0 at FD-noise order;
  4  CTRLr2 (linear-extraction slots frozen) == A0r2 (structural-zero
     control for round 2);
  5  block-union anchors: A2ALL == round-1 A2 and A3ALL == round-1 A3 at
     FD-noise order (freezing every sub-slot reproduces the whole-block
     ablation);
  6  each single sub-variant A2-1..A2-5 / A3-1..A3-4 genuinely moves the
     tangent and the sub-variants are mutually distinct (hot != cold);
     with hot == cold every sub-variant equals A0r2 bitwise;
  7  guide section 7.2 legality invariants per sub-variant: the hot-band
     tangent keeps zero row mass increment, zero wall velocity and
     d(theta_row) = eta (sink row pinned at zero);
  8  fail-loud: unknown round-2 variant / slot names raise.
"""

from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pytest

from boundary.wall_thermal_mass_neutral import _mass_neutral_reconstruct_row0_symmetric
from core.macroscopic import recover_macro
from core.solver import GasSolver2D
from core.tangent_step import TangentOperator, ablated_blocks, block_macro_eq, compute_stage_bases
from core.tangent_substep import (
    R2_SINGLE_VARIANTS,
    R2TangentOperator,
    compose_band_row,
    compose_macro_eq,
    compute_r2_bases,
    r2_ablated_slots,
)
from scripts.phase2_m2_verification import load_config
from scripts.phase5_g4a_dc_basestate import run_tent
from scripts.phase5_wp4_jacobian_ablation import snapshot_to_base

GAS_CFG_PATH = Path("configs/gas_air_10k_d2q37_levelc_dx2p6.yaml")
NY, NX, F_HZ = 10, 4, 1.0e6


@pytest.fixture(scope="module")
def rig():
    cfg = load_config(GAS_CFG_PATH)
    runs = {}
    for th in (0.0, 0.05):
        runs[th] = run_tent(copy.deepcopy(cfg), ny=NY, nx=NX, theta_dc=th,
                            frequency_hz=F_HZ, eps_ac=0.0, settle_periods=20.0,
                            drive_periods=0.0, samples_per_period=32,
                            snapshot=True, log=lambda *_: None)
        assert runs[th]["finite"]
    scfg = copy.deepcopy(cfg)
    scfg["numerics"] = {**scfg["numerics"], "ny": NY, "nx": NX}
    solver = GasSolver2D(scfg)
    hot = snapshot_to_base(runs[0.05])
    cold = snapshot_to_base(runs[0.0])
    return {
        "solver": solver, "hot": hot, "cold": cold,
        "hb1": compute_stage_bases(solver, hot),
        "cb1": compute_stage_bases(solver, cold),
        "hb2": compute_r2_bases(solver, hot),
        "cb2": compute_r2_bases(solver, cold),
    }


def _r1_step(rig, variant, df, dg, eta):
    op = TangentOperator(rig["solver"], rig["hot"], rig["hb1"], rig["cold"],
                         rig["cb1"], h=5e-5, ablated=ablated_blocks(variant))
    return op.step(df, dg, eta)


def _r2_step(rig, variant, df, dg, eta, *, cold_equals_hot=False):
    cold, cb2 = (rig["hot"], rig["hb2"]) if cold_equals_hot \
        else (rig["cold"], rig["cb2"])
    op = R2TangentOperator(rig["solver"], rig["hot"], rig["hb2"], cold, cb2,
                           h=5e-5, ablated=r2_ablated_slots(variant))
    return op.step(df, dg, eta)


def _probe(rig, seed=5):
    rng = np.random.default_rng(seed)
    df = rng.standard_normal(rig["hot"].f.shape)
    dg = rng.standard_normal(rig["hot"].g.shape)
    eta = 0.3 * float(rig["solver"].mapping.theta_ref_lu)
    return df, dg, eta


def test_band_compose_bitwise_vs_production(rig):
    hot = rig["hot"]
    prod_f, prod_g = _mass_neutral_reconstruct_row0_symmetric(
        rig["solver"], hot.f.copy(), hot.g.copy(), hot.theta_w,
        extrap="row1", row=0)
    mine_f, mine_g = compose_band_row(rig["solver"], hot.f, hot.g,
                                      hot.theta_w, 0)
    assert np.array_equal(prod_f, mine_f)
    assert np.array_equal(prod_g, mine_g)
    # sink-row instance too
    prod_f, prod_g = _mass_neutral_reconstruct_row0_symmetric(
        rig["solver"], hot.f.copy(), hot.g.copy(), hot.theta_amb,
        extrap="row1", row=hot.hs)
    mine_f, mine_g = compose_band_row(rig["solver"], hot.f, hot.g,
                                      hot.theta_amb, hot.hs)
    assert np.array_equal(prod_f, mine_f)
    assert np.array_equal(prod_g, mine_g)


def test_macro_compose_bitwise_vs_round1(rig):
    r1 = block_macro_eq(rig["hot"].f, rig["hot"].g, rig["solver"].mapping,
                        rig["solver"].lattice)
    r2 = compose_macro_eq(rig["hot"].f, rig["hot"].g, rig["solver"].mapping,
                          rig["solver"].lattice)
    for a, b in zip(r1, r2, strict=True):
        assert np.array_equal(a, b)


def test_a0r2_matches_round1_a0_and_control_is_zero(rig):
    df, dg, eta = _probe(rig)
    a0_1 = _r1_step(rig, "A0", df, dg, eta)
    a0_2 = _r2_step(rig, "A0r2", df, dg, eta)
    den = max(float(np.max(np.abs(a0_1[0]))), float(np.max(np.abs(a0_1[1]))))
    for i in (0, 1):
        assert float(np.max(np.abs(a0_2[i] - a0_1[i]))) <= 1e-6 * den
    assert abs(a0_2[2] - a0_1[2]) <= 1e-6 * max(abs(a0_1[2]), 1e-300)
    ctrl = _r2_step(rig, "CTRLr2", df, dg, eta)
    for i in (0, 1):
        assert float(np.max(np.abs(ctrl[i] - a0_2[i]))) <= 1e-7 * den


def test_block_union_anchors_reproduce_round1_blocks(rig):
    df, dg, eta = _probe(rig)
    den = None
    for union, blk in (("A2ALL", "A2"), ("A3ALL", "A3")):
        u = _r2_step(rig, union, df, dg, eta)
        b = _r1_step(rig, blk, df, dg, eta)
        if den is None:
            den = max(float(np.max(np.abs(b[0]))), float(np.max(np.abs(b[1]))))
        for i in (0, 1):
            assert float(np.max(np.abs(u[i] - b[i]))) <= 1e-5 * den, (union, i)


SINGLES = ("A2-1", "A2-2", "A2-3", "A2-4", "A2-5",
           "A3-1", "A3-2", "A3-3", "A3-4")


def test_sub_variants_identity_when_cold_equals_hot(rig):
    df, dg, eta = _probe(rig, seed=17)
    ref = _r2_step(rig, "A0r2", df, dg, eta, cold_equals_hot=True)
    for variant in SINGLES:
        out = _r2_step(rig, variant, df, dg, eta, cold_equals_hot=True)
        for a, b in zip(ref, out, strict=True):
            assert np.array_equal(np.asarray(a), np.asarray(b)), variant


def test_sub_variants_change_only_selected_and_are_distinct(rig):
    df, dg, eta = _probe(rig, seed=23)
    ref = _r2_step(rig, "A0r2", df, dg, eta)
    den = max(float(np.max(np.abs(ref[0]))), float(np.max(np.abs(ref[1]))))
    outs = {v: _r2_step(rig, v, df, dg, eta) for v in SINGLES}
    for v, out in outs.items():
        moved = float(np.max(np.abs(out[0] - ref[0]))) / den
        assert moved > 1e-12, f"{v} did not change the tangent"
    names = list(SINGLES)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            diff = float(np.max(np.abs(outs[names[i]][0] - outs[names[j]][0]))) / den
            assert diff > 1e-12, f"{names[i]} == {names[j]}"


def test_wall_tangent_invariants_per_sub_variant(rig):
    """Guide 7.2: mass neutrality, u=0 and theta pinning hold in EVERY
    sub-variant (tangent caliber: row-mass/momentum deltas ~0; sink pinned)."""

    solver = rig["solver"]
    lattice = solver.lattice
    c = np.asarray(lattice.c, dtype=float)
    D = int(solver.mapping.lattice.D)
    S = int(solver.mapping.lattice.S)
    hot = rig["hot"]
    df = np.zeros_like(hot.f)
    dg = np.zeros_like(hot.g)
    eta = float(solver.mapping.theta_ref_lu)
    for variant in SINGLES + ("A0r2",):
        d_hf, d_hg, dqh, dqs = _r2_step(rig, variant, df, dg, eta)
        assert np.all(np.isfinite(d_hf)) and np.all(np.isfinite(d_hg)), variant
        # the filter mixes rows, so probe the band invariants pre-filter via a
        # bare band JVP: rebuild through the operator internals
        op = R2TangentOperator(solver, hot, rig["hb2"], rig["cold"],
                               rig["cb2"], h=5e-5,
                               ablated=r2_ablated_slots(variant))
        s = op.macro_scale(df, dg, eta)
        d_bf, d_bg, dq = op._band_jvp(op.hot.band_hot, op.cold.band_hot,
                                      np.zeros_like(hot.f), np.zeros_like(hot.g),
                                      eta, 0, h=op.h, inv=1.0 / s, scale=s / (2 * op.h))
        assert abs(float(np.sum(d_bf[0]))) <= 1e-9 * eta, variant       # mass
        dj = np.einsum("xq,qd->d", d_bf[0], c)
        assert np.max(np.abs(dj)) <= 1e-9 * eta, variant                # u=0
        # theta pinning in tangent caliber: theta_row(base + e*d) - theta_w
        # equals e*eta to linear order. EXACT for every variant except A2-5:
        # P's algebraic energy pin overrides any upstream mixed derivative,
        # so only freezing P's own slots leaves a bounded O(Theta_DC) factor
        # (measured eta * rho_w_cold/rho_w_hot -- the deliberately frozen
        # pinning density sensitivity, i.e. the A2-5 ablation content itself).
        e2 = 1e-6
        m_lin = recover_macro(op.hot.band_hot.f0 + e2 * d_bf[0:1],
                              op.hot.band_hot.g0 + e2 * d_bg[0:1],
                              D=D, S=S, lattice=lattice)
        d_theta_row = (np.asarray(m_lin.theta) - hot.theta_w) / e2
        if variant == "A2-5":
            theta_dc = hot.theta_dc_target
            assert np.max(np.abs(d_theta_row - eta)) <= 2.0 * theta_dc * eta, variant
        else:
            assert np.max(np.abs(d_theta_row - eta)) <= 1e-5 * eta, variant


def test_fail_loud_unknown_round2_names():
    with pytest.raises(ValueError):
        r2_ablated_slots("A2-9")
    with pytest.raises(ValueError):
        r2_ablated_slots("A2-1+bogus")
    with pytest.raises(ValueError):
        r2_ablated_slots("")
    assert r2_ablated_slots("A2-1+A3-4") == (
        R2_SINGLE_VARIANTS["A2-1"] | R2_SINGLE_VARIANTS["A3-4"])
