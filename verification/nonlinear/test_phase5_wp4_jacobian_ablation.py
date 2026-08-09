"""WP4-JAB contract tests (guide section 11; pre-registered before hot runs).

Covers the nine required failing-first tests plus the bitwise stage-identity
anchors that make the tangent a wrapper over the PRODUCTION operator rather
than a fork:

  1  known linear map (streaming / filter): central-difference JVP recovers
     the exact linear action;
  2  known cubic map: central difference converges at second order; the full
     one-step even combination decays ~h^2 (v1 probe);
  3  streaming and fixed-coefficient filter have identical hot/cold
     derivatives (exactly linear stages);
  4  wall tangent keeps zero mass increment, zero wall velocity and the
     prescribed wall-temperature increment (sink row pinned at zero);
  5  collision tangent conserves mass, momentum and total energy per cell;
  6  each variant A1-A5 changes ONLY the selected derivative block
     (hot==cold snapshots => every variant bitwise-equals A0; hot!=cold =>
     A2..A5 all differ from A0 and pairwise, A1 bitwise-equals A0 by the
     structural-identity assert, A6 equals A0 to rounding);
  7  A6 negative control is numerical zero on the synthetic fixture;
  8  the micro-rig full tangent reproduces the finite-difference TAN
     admittances (direction + magnitude) on the same rig;
  9  invalid variant names, an unfrozen step window and a missing base-state
     snapshot all fail loudly.

Anchors: compose_collide == collide_fg bitwise; direct_step == solver.step
with the composed audited band callbacks bitwise (state AND bookkeeping);
the band callbacks ignore f_post/g_post (the B-stage JVP interface
assumption); the acoustic-stage structural identity holds on the actual rig
geometries AND its assert fails on a geometry with qualifying diagonal
modes (non-degeneracy); the delta_G energy pin has zero base dependence.
"""

from __future__ import annotations

import copy
import math
from pathlib import Path

import numpy as np
import pytest

from boundary.wall_thermal_mass_neutral import (
    make_symmetric_mass_neutral_band_callback,
    make_symmetric_mass_neutral_wall_callback,
)
from core.collision_smrt import collide_fg
from core.macroscopic import recover_macro
from core.solver import GasSolver2D
from core.tangent_step import (
    BaseState,
    TangentOperator,
    TangentStructureError,
    ablated_blocks,
    acoustic_stage_structural_report,
    assert_acoustic_stage_identity,
    compose_collide,
    compute_stage_bases,
    direct_step,
    propagate_tangent,
    stage_band,
    stage_filter,
    stage_stream,
    v1_odd_even_probe,
)
from scripts.phase2_m2_verification import load_config
from scripts.phase5_g4a_dc_basestate import (
    fit_admittance,
    make_energy_audited_band,
    run_tent,
)
from scripts.phase5_wp4_jacobian_ablation import (
    require_h_frozen,
    snapshot_to_base,
)

GAS_CFG_PATH = Path("configs/gas_air_10k_d2q37_levelc_dx2p6.yaml")
MICRO_F_HZ = 1.0e6          # micro rig: 511 steps/period (dt frozen)
MICRO_NY, MICRO_NX = 10, 4
MICRO_SETTLE = 20.0
MICRO_DRIVE = 4.0
MICRO_SKIP = 2.0
MICRO_SPP = 32


def _solver(ny: int, nx: int) -> GasSolver2D:
    cfg = copy.deepcopy(load_config(GAS_CFG_PATH))
    cfg["numerics"] = {**cfg["numerics"], "ny": ny, "nx": nx}
    return GasSolver2D(cfg)


def _textured_state(solver: GasSolver2D, seed: int = 7):
    """Physical-ish state with genuine non-equilibrium content."""

    rng = np.random.default_rng(seed)
    th0 = float(solver.mapping.theta_ref_lu)
    ny, nx = solver.ny, solver.nx
    rho = 1.0 + 1e-3 * rng.standard_normal((ny, nx))
    theta = th0 * (1.0 + 2e-3 * rng.standard_normal((ny, nx)))
    u = 1e-4 * rng.standard_normal((ny, nx, 2))
    solver.initialize_from_macro(rho, u, theta)
    solver.step(2)
    return solver.f.copy(), solver.g.copy()


@pytest.fixture(scope="module")
def micro():
    """Settled micro tent bases (hot Theta_DC=0.05 + cold) on the 10x4 rig."""

    cfg = copy.deepcopy(load_config(GAS_CFG_PATH))
    runs = {}
    for th in (0.0, 0.05):
        runs[th] = run_tent(cfg, ny=MICRO_NY, nx=MICRO_NX, theta_dc=th,
                            frequency_hz=MICRO_F_HZ, eps_ac=0.0,
                            settle_periods=MICRO_SETTLE, drive_periods=0.0,
                            samples_per_period=MICRO_SPP, snapshot=True,
                            log=lambda *_: None)
        assert runs[th]["finite"]
    solver = _solver(MICRO_NY, MICRO_NX)
    hot = snapshot_to_base(runs[0.05])
    cold = snapshot_to_base(runs[0.0])
    return {"solver": solver, "runs": runs, "hot": hot, "cold": cold,
            "hot_bases": compute_stage_bases(solver, hot),
            "cold_bases": compute_stage_bases(solver, cold)}


def _op(micro, variant: str, h: float = 5.0e-5, cold_equals_hot: bool = False):
    hot, cold = micro["hot"], micro["cold"]
    hb, cb = micro["hot_bases"], micro["cold_bases"]
    if cold_equals_hot:
        cold, cb = hot, hb
    return TangentOperator(micro["solver"], hot, hb, cold, cb, h=h,
                           ablated=ablated_blocks(variant))


def _probe(shapes, seed=11):
    rng = np.random.default_rng(seed)
    return rng.standard_normal(shapes[0]), rng.standard_normal(shapes[1])


# ---------------------------------------------------------------------------
# 1 + 3: linear stages -- exact JVP recovery, hot/cold derivative identity
# ---------------------------------------------------------------------------

def test_linear_stage_jvp_exact_and_base_independent(micro):
    solver = micro["solver"]
    lattice = solver.lattice
    hb, cb = micro["hot_bases"], micro["cold_bases"]
    df, dg = _probe((hb.f.shape, hb.g.shape))
    h = 1e-4
    for base_f, base_g in ((hb.f2, hb.g_post), (cb.f2, cb.g_post)):
        sp = stage_stream(base_f + h * df, base_g + h * dg, lattice)
        sm = stage_stream(base_f - h * df, base_g - h * dg, lattice)
        exact = stage_stream(df, dg, lattice)
        jf = (sp[0] - sm[0]) / (2 * h)
        jg = (sp[1] - sm[1]) / (2 * h)
        assert np.max(np.abs(jf - exact[0])) <= 1e-10 * max(1.0, np.max(np.abs(exact[0])))
        assert np.max(np.abs(jg - exact[1])) <= 1e-10 * max(1.0, np.max(np.abs(exact[1])))
    for base_f, base_g in ((hb.b_f, hb.b_g), (cb.b_f, cb.b_g)):
        hp = stage_filter(solver, base_f + h * df, base_g + h * dg)
        hm = stage_filter(solver, base_f - h * df, base_g - h * dg)
        exact = stage_filter(solver, df, dg)
        jf = (hp[0] - hm[0]) / (2 * h)
        jg = (hp[1] - hm[1]) / (2 * h)
        assert np.max(np.abs(jf - exact[0])) <= 1e-9 * max(1.0, np.max(np.abs(exact[0])))
        assert np.max(np.abs(jg - exact[1])) <= 1e-9 * max(1.0, np.max(np.abs(exact[1])))


# ---------------------------------------------------------------------------
# 2: second-order convergence (synthetic cubic + full-step even combination)
# ---------------------------------------------------------------------------

def test_central_difference_second_order_synthetic():
    rng = np.random.default_rng(3)
    x = rng.standard_normal(64)
    v = rng.standard_normal(64)

    def fn(z):
        return z ** 3

    exact = 3.0 * x ** 2 * v
    errs = []
    for h in (1e-2, 5e-3, 2.5e-3):
        jv = (fn(x + h * v) - fn(x - h * v)) / (2 * h)
        errs.append(np.max(np.abs(jv - exact)))
    assert errs[0] / errs[1] == pytest.approx(4.0, rel=0.05)
    assert errs[1] / errs[2] == pytest.approx(4.0, rel=0.05)


def test_full_step_even_combination_decays_h2(micro):
    row = v1_odd_even_probe(micro["solver"], micro["hot"], micro["hot_bases"],
                            [1e-3, 5e-4, 2.5e-4])
    floor = 1e-12 * max(r["odd_norm"] for r in row["rows"])
    ratios = row["even_ratios"]
    evens = [r["even_norm"] for r in row["rows"]]
    for i, ratio in enumerate(ratios):
        if evens[i + 1] > floor:
            assert 2.5 <= ratio <= 6.0, (ratios, evens)
    assert max(row["odd_pairwise_rel"]) <= 1e-5
    assert max(r["chain_vs_singleshot_rel"] for r in row["rows"]) <= 1e-5


# ---------------------------------------------------------------------------
# 4: wall tangent invariants (B-stage JVP with the wall-temperature input)
# ---------------------------------------------------------------------------

def test_wall_tangent_invariants(micro):
    solver = micro["solver"]
    hb = micro["hot"]
    bases = micro["hot_bases"]
    lattice = solver.lattice
    D = int(solver.mapping.lattice.D)
    S = int(solver.mapping.lattice.S)
    th0 = float(solver.mapping.theta_ref_lu)
    h = 5e-5
    eta = th0  # unit wall-temperature increment in theta units
    bp = stage_band(solver, bases.s_f, bases.s_g, hb.theta_w + h * eta,
                    hb.theta_amb, hb.hs)
    bm = stage_band(solver, bases.s_f, bases.s_g, hb.theta_w - h * eta,
                    hb.theta_amb, hb.hs)
    d_bf = (bp[0] - bm[0]) / (2 * h)
    d_bg = (bp[1] - bm[1]) / (2 * h)
    # zero mass increment and zero wall velocity on the hot band row
    assert abs(float(np.sum(d_bf[0]))) <= 1e-9 * eta
    dj = np.einsum("xq,qd->d", d_bf[0], np.asarray(lattice.c, dtype=float))
    assert np.max(np.abs(dj)) <= 1e-9 * eta
    # prescribed wall-temperature increment: d(theta_row0) == eta
    mp = recover_macro(bp[0][0:1], bp[1][0:1], D=D, S=S, lattice=lattice)
    mm = recover_macro(bm[0][0:1], bm[1][0:1], D=D, S=S, lattice=lattice)
    d_theta_row = (mp.theta - mm.theta) / (2 * h)
    assert d_theta_row == pytest.approx(eta, rel=1e-9)
    # sink row stays pinned: d(theta_hs) == 0
    d_theta_sink = (recover_macro(bp[0][hb.hs:hb.hs + 1], bp[1][hb.hs:hb.hs + 1],
                                  D=D, S=S, lattice=lattice).theta
                    - recover_macro(bm[0][hb.hs:hb.hs + 1], bm[1][hb.hs:hb.hs + 1],
                                    D=D, S=S, lattice=lattice).theta) / (2 * h)
    assert np.max(np.abs(d_theta_sink)) <= 1e-9 * eta


# ---------------------------------------------------------------------------
# 5: collision tangent conservation (per cell)
# ---------------------------------------------------------------------------

def test_collision_tangent_conservation(micro):
    solver = micro["solver"]
    lattice = solver.lattice
    mapping = solver.mapping
    hb = micro["hot_bases"]
    df, dg = _probe((hb.f.shape, hb.g.shape), seed=23)
    h = 5e-5
    p = compose_collide(hb.f + h * df, hb.g + h * dg, mapping, lattice)
    m = compose_collide(hb.f - h * df, hb.g - h * dg, mapping, lattice)
    d_f2 = (p[0] - m[0]) / (2 * h)
    d_g2 = (p[1] - m[1]) / (2 * h)
    c = np.asarray(lattice.c, dtype=float)
    c2 = np.sum(c ** 2, axis=-1)
    scale = float(np.max(np.abs(df)))
    # mass and momentum of the f tangent are conserved per cell
    assert np.max(np.abs(np.sum(d_f2, axis=-1) - np.sum(df, axis=-1))) <= 1e-8 * scale
    dj_in = np.einsum("yxq,qd->yxd", df, c)
    dj_out = np.einsum("yxq,qd->yxd", d_f2, c)
    assert np.max(np.abs(dj_out - dj_in)) <= 1e-8 * scale
    # total energy tangent conserved per cell (delta_G pin)
    de_in = 0.5 * np.sum(df * c2, axis=-1) + np.sum(dg, axis=-1)
    de_out = 0.5 * np.sum(d_f2 * c2, axis=-1) + np.sum(d_g2, axis=-1)
    assert np.max(np.abs(de_out - de_in)) <= 1e-7 * scale


# ---------------------------------------------------------------------------
# 6 + 7: variants change only the selected block; A6/A1 are negative controls
# ---------------------------------------------------------------------------

def _one_step(op, seed=31):
    rng = np.random.default_rng(seed)
    df = rng.standard_normal(op.hot_base.f.shape)
    dg = rng.standard_normal(op.hot_base.g.shape)
    eta = 0.3 * op.theta0
    return op.step(df, dg, eta)


def test_variants_identity_when_cold_equals_hot(micro):
    ref = _one_step(_op(micro, "A0", cold_equals_hot=True))
    for variant in ("A1", "A2", "A3", "A4", "A5"):
        out = _one_step(_op(micro, variant, cold_equals_hot=True))
        for a, b in zip(ref, out, strict=True):
            assert np.array_equal(np.asarray(a), np.asarray(b)), variant
    out6 = _one_step(_op(micro, "A6", cold_equals_hot=True))
    denom = max(float(np.max(np.abs(ref[0]))), 1e-300)
    assert float(np.max(np.abs(out6[0] - ref[0]))) <= 1e-8 * denom
    assert float(np.max(np.abs(out6[1] - ref[1]))) <= 1e-8 * denom


def test_variants_change_only_selected_block(micro):
    ref = _one_step(_op(micro, "A0"))
    denom = max(float(np.max(np.abs(ref[0]))), float(np.max(np.abs(ref[1]))))
    outs = {}
    for variant in ("A1", "A2", "A3", "A4", "A5", "A6"):
        outs[variant] = _one_step(_op(micro, variant))
    # A1: structural identity => bitwise A0
    for a, b in zip(ref, outs["A1"], strict=True):
        assert np.array_equal(np.asarray(a), np.asarray(b))
    # A6: exactly-linear stages => numerical zero shift (negative control)
    assert float(np.max(np.abs(outs["A6"][0] - ref[0]))) <= 1e-8 * denom
    assert float(np.max(np.abs(outs["A6"][1] - ref[1]))) <= 1e-8 * denom
    # A2..A5: each genuinely moves the tangent, and mutually differently
    deltas = {}
    for variant in ("A2", "A3", "A4", "A5"):
        d = float(np.max(np.abs(outs[variant][0] - ref[0]))) / denom
        deltas[variant] = d
        assert d > 1e-10, f"{variant} did not change the tangent"
    pairs = [("A2", "A3"), ("A2", "A4"), ("A2", "A5"),
             ("A3", "A4"), ("A3", "A5"), ("A4", "A5")]
    for a, b in pairs:
        diff = float(np.max(np.abs(outs[a][0] - outs[b][0]))) / denom
        assert diff > 1e-10, f"{a} and {b} produced identical ablations"


# ---------------------------------------------------------------------------
# 8: micro-rig tangent reproduces the finite-difference admittances
# ---------------------------------------------------------------------------

def test_micro_tangent_matches_finite_difference(micro):
    cfg = copy.deepcopy(load_config(GAS_CFG_PATH))
    eps = 2e-3
    y_fd = {}
    for th in (0.0, 0.05):
        run = run_tent(cfg, ny=MICRO_NY, nx=MICRO_NX, theta_dc=th,
                       frequency_hz=MICRO_F_HZ, eps_ac=eps,
                       settle_periods=MICRO_SETTLE, drive_periods=MICRO_DRIVE,
                       samples_per_period=MICRO_SPP, log=lambda *_: None)
        assert run["finite"]
        y_fd[th] = fit_admittance(run, MICRO_F_HZ, MICRO_SKIP)["Y_face_theta_units"]
    y_tan = {}
    for th in (0.0, 0.05):
        base_key = "cold" if th == 0.0 else "hot"
        op = TangentOperator(
            micro["solver"],
            micro[base_key], micro[f"{base_key}_bases"],
            micro["cold"], micro["cold_bases"],
            h=5e-5, ablated=frozenset())
        run = propagate_tangent(op, frequency_hz=MICRO_F_HZ,
                                drive_periods=MICRO_DRIVE,
                                samples_per_period=MICRO_SPP)
        y_tan[th] = fit_admittance(run, MICRO_F_HZ, MICRO_SKIP)["Y_face_theta_units"]
        # V5 audits hold on the micro rig too (frozen floor-derived gates)
        assert run["audits"]["mass_tangent_rel_worst"] <= 1e-7
        assert run["audits"]["energy_account_rel_worst"] <= 1e-5
    for th in (0.0, 0.05):
        ratio = y_tan[th] / y_fd[th]
        assert abs(ratio) == pytest.approx(1.0, abs=0.05), (th, ratio)
        assert math.degrees(math.atan2(ratio.imag, ratio.real)) == pytest.approx(
            0.0, abs=3.0), (th, ratio)
    d_fd = (abs(y_fd[0.05] / y_fd[0.0]) - 1.0) * 100.0
    d_tan = (abs(y_tan[0.05] / y_tan[0.0]) - 1.0) * 100.0
    if abs(d_fd) > 0.5:
        assert d_fd * d_tan > 0.0, (d_fd, d_tan)


# ---------------------------------------------------------------------------
# 9: fail-loud guards
# ---------------------------------------------------------------------------

def test_fail_loud_guards(micro):
    with pytest.raises(ValueError):
        ablated_blocks("A9")
    with pytest.raises(ValueError):
        ablated_blocks("A2+bogus")
    with pytest.raises(RuntimeError):
        require_h_frozen({"jvp": {"h_frozen": False, "h_ladder": [1e-4, 5e-5, 2.5e-5]}})
    with pytest.raises(RuntimeError):
        require_h_frozen({"jvp": {"h_frozen": True, "h_ladder": [1e-4]}})
    with pytest.raises(RuntimeError):
        snapshot_to_base({"finite": True})   # no snapshot captured


# ---------------------------------------------------------------------------
# bitwise anchors: the tangent wraps the production operator, not a fork
# ---------------------------------------------------------------------------

def test_compose_collide_bitwise_vs_production(micro):
    solver = _solver(8, 4)
    f, g = _textured_state(solver)
    ours = compose_collide(f, g, solver.mapping, solver.lattice)
    prod = collide_fg(f, g, solver.mapping, lattice=solver.lattice,
                      trace_bulk_pressure_divergence=None)
    assert np.array_equal(ours[0], prod[0])
    assert np.array_equal(ours[1], prod[1])


def test_direct_step_bitwise_vs_solver_step(micro):
    hb = micro["hot"]
    stepper = _solver(MICRO_NY, MICRO_NX)
    stepper.f = hb.f.copy()
    stepper.g = hb.g.copy()
    rec: dict[str, list[float]] = {}
    hot_inner = make_symmetric_mass_neutral_wall_callback(lambda s: hb.theta_w)
    sink_inner = make_symmetric_mass_neutral_band_callback(hb.theta_amb, hb.hs)
    hot_cb = make_energy_audited_band(hot_inner, rec, stepper.lattice, "hot")
    sink_cb = make_energy_audited_band(sink_inner, rec, stepper.lattice, "sink")

    def composed(**kw):
        f, g = hot_cb(**kw)
        return sink_cb(**{**kw, "f_stream": f, "g_stream": g})

    stepper.step(1, boundary_callback=composed)
    f_d, g_d, hot_de, sink_de = direct_step(
        micro["solver"], hb.f, hb.g, hb.theta_w, hb.theta_amb, hb.hs)
    assert np.array_equal(stepper.f, f_d)
    assert np.array_equal(stepper.g, g_d)
    assert rec["hot_dE"][0] == hot_de
    assert rec["sink_dE"][0] == sink_de


def test_band_callback_ignores_post_collision_populations(micro):
    """The B-stage JVP treats B as f(streamed, T_w) -- assert the production
    band callbacks really ignore f_post/g_post (poisoned inputs)."""

    hb = micro["hot"]
    bases = micro["hot_bases"]
    solver = micro["solver"]
    hot_inner = make_symmetric_mass_neutral_wall_callback(lambda s: hb.theta_w)
    sink_inner = make_symmetric_mass_neutral_band_callback(hb.theta_amb, hb.hs)
    poison = np.full_like(bases.f2, np.nan)
    f1, g1 = hot_inner(solver=solver, f_post=poison, g_post=poison,
                       f_stream=bases.s_f.copy(), g_stream=bases.s_g.copy())
    f1, g1 = sink_inner(solver=solver, f_post=poison, g_post=poison,
                        f_stream=f1, g_stream=g1)
    f2, g2, _, _ = stage_band(solver, bases.s_f, bases.s_g, hb.theta_w,
                              hb.theta_amb, hb.hs)
    assert np.array_equal(f1, f2)
    assert np.array_equal(g1, g2)


def test_acoustic_structural_identity_and_nondegeneracy():
    # identity holds on the actual rig geometries (smoke, authoritative, micro)
    for ny, nx in ((24, 4), (96, 8), (MICRO_NY, MICRO_NX)):
        report = assert_acoustic_stage_identity(_solver(ny, nx))
        assert report["identity"] and report["diagonal_low_mode_count"] == 0
    # non-degeneracy: a wide 64x64 box HAS qualifying diagonal modes -> the
    # assert must refuse (protects against silent S6 extrapolation)
    wide = _solver(64, 64)
    report = acoustic_stage_structural_report(wide)
    assert report["diagonal_low_mode_count"] > 0 and not report["identity"]
    with pytest.raises(TangentStructureError):
        assert_acoustic_stage_identity(wide)


def test_delta_g_energy_pin_has_no_base_dependence(micro):
    """E_tot is the exact linear moment 0.5*sum(f|c|^2)+sum(g): its tangent is
    base-independent (the guide's A5 item 4 is structurally inert)."""

    solver = micro["solver"]
    lattice = solver.lattice
    D = int(solver.mapping.lattice.D)
    S = int(solver.mapping.lattice.S)
    hb, cb = micro["hot_bases"], micro["cold_bases"]
    df, dg = _probe((hb.f.shape, hb.g.shape), seed=41)
    h = 1e-4
    outs = []
    for base in (hb, cb):
        ep = recover_macro(base.f + h * df, base.g + h * dg, D=D, S=S,
                           lattice=lattice).E_tot
        em = recover_macro(base.f - h * df, base.g - h * dg, D=D, S=S,
                           lattice=lattice).E_tot
        outs.append((ep - em) / (2 * h))
    c2 = np.sum(np.asarray(lattice.c, dtype=float) ** 2, axis=-1)
    linear = 0.5 * np.sum(df * c2, axis=-1) + np.sum(dg, axis=-1)
    scale = max(float(np.max(np.abs(linear))), 1e-300)
    assert np.max(np.abs(outs[0] - outs[1])) <= 1e-7 * scale
    assert np.max(np.abs(outs[0] - linear)) <= 1e-6 * scale
