"""Cross-stack unit 1a contract tests (D0-7 diagnostic unit).

Mechanism-level guards for core/collision_bgk.py, core/tangent_bgk.py and
scripts/phase5_crossstack_collision_scan.py:

- PROD anchors: the selectable-collision solver, the settle replica and the
  tangent operator must be BITWISE production on the PROD branch -- otherwise
  every cross-stack delta would be contaminated by the instrument;
- BGK correctness: exact mass/momentum/total-energy conservation, exact
  linearity of the relaxation block, the transport inversion round-trip, and
  block composition == the single-shot collide;
- instrument anchoring: the mode-decay transport probe reproduces the frozen
  G0/P2-5 instrument bitwise on the PROD solver;
- fail-loud: unknown collision branch, ablating a block the BGK branch does not
  have, an out-of-reach (nu, alpha) request, tau <= 1/2;
- config plumbing: variant_gas_cfg is non-mutating and touches only collision
  keys; the frozen variant catalogue keeps PROD an empty override;
- pure analysis: partition_variants drops only dead variants, classify covers
  ROBUST / SENSITIVE / ABSENT / MIXED / live-key branches;
- checkpoint namespace uniqueness across the frozen variant catalogue.

No scan verdicts here -- judgement lines live frozen in the runner constants.
"""

from __future__ import annotations

import copy
import math
from pathlib import Path

import numpy as np
import pytest

from core.collision_bgk import (
    BgkParams,
    assert_bgk_conservation,
    bgk_params_from_transport,
    bgk_params_matching,
    bgk_relax,
    collide_fg_bgk,
)
from core.solver import GasSolver2D
from core.tangent_bgk import (
    COLLISION_BGK,
    COLLISION_PROD,
    CrossStackSolver2D,
    CrossStackTangentOperator,
    compose_collide_bgk,
    compute_stage_bases_crossstack,
    measure_mode_decay,
    one_step_spectral_radius,
)
from core.tangent_step import BaseState, TangentOperator, TangentStructureError, compute_stage_bases
from scripts.phase2_m2_verification import load_config
from scripts.phase5_crossstack_collision_scan import (
    LINE_CLASS_PP,
    LINE_LIVEKEY_Y0_REL,
    LINE_SPECTRAL_RADIUS,
    VARIANTS,
    classify,
    partition_variants,
    settle_tent_crossstack,
    variant_gas_cfg,
)
from scripts.phase5_g4a_dc_basestate import run_tent
from scripts.phase5_wallfix_arbitration import FREQUENCY_HZ

BASE = load_config(Path("configs/gas_air_10k_d2q37_levelc_dx2p6.yaml"))


def _mapping(cfg=None, ny=8, nx=4):
    c = copy.deepcopy(cfg or BASE)
    c["numerics"] = {**c["numerics"], "nx": nx, "ny": ny}
    return GasSolver2D(c).mapping


def _seeded(collision=COLLISION_PROD, ny=16, nx=4, steps=5, params=None):
    cfg = {**BASE, "numerics": {**BASE["numerics"], "nx": nx, "ny": ny}}
    s = CrossStackSolver2D(cfg, collision=collision, bgk_params=params)
    th0 = float(s.mapping.theta_ref_lu)
    rho0 = float(s.mapping.lattice.rho_ref_lu)
    prof = th0 * (1.0 + 0.05 * np.cos(2 * np.pi * np.arange(ny) / ny))[:, None]
    theta = np.tile(prof, (1, nx))
    s.initialize_from_macro(rho0 * th0 / theta, np.zeros((ny, nx, 2)), theta)
    s.step(steps)
    return s


# ---------------------------------------------------------------------------
# PROD anchors -- the instrument must be production on the PROD branch
# ---------------------------------------------------------------------------

def test_crossstack_solver_prod_branch_is_bitwise_production():
    cfg = {**BASE, "numerics": {**BASE["numerics"], "nx": 4, "ny": 16}}
    ref, mine = GasSolver2D(cfg), CrossStackSolver2D(cfg, collision=COLLISION_PROD)
    th0 = float(ref.mapping.theta_ref_lu)
    rho0 = float(ref.mapping.lattice.rho_ref_lu)
    prof = th0 * (1.0 + 0.05 * np.cos(2 * np.pi * np.arange(16) / 16))[:, None]
    theta = np.tile(prof, (1, 4))
    rho = rho0 * th0 / theta
    for s in (ref, mine):
        s.initialize_from_macro(rho.copy(), np.zeros((16, 4, 2)), theta.copy())
    ref.step(7)
    mine.step(7)
    assert np.array_equal(ref.f, mine.f)
    assert np.array_equal(ref.g, mine.g)


def test_settle_replica_prod_branch_is_bitwise_run_tent():
    kw = dict(ny=8, nx=4, theta_dc=0.05, frequency_hz=FREQUENCY_HZ,
              settle_periods=0.004, samples_per_period=8)
    ref = run_tent(BASE, eps_ac=0.0, drive_periods=0.0, snapshot=True,
                   log=lambda *_a, **_k: None, **kw)
    mine = settle_tent_crossstack(BASE, variant="PROD", **kw)
    assert np.array_equal(ref["snapshot"]["f"], mine["snapshot"]["f"])
    assert np.array_equal(ref["snapshot"]["g"], mine["snapshot"]["g"])
    for key in ("stationarity_per_period", "dc_closure_rel",
                "theta_dc_measured", "q_hot_dc_lu", "q_sink_dc_lu"):
        assert ref[key] == mine[key], key


def _tiny_base(solver, theta_dc=0.05):
    ny, nx = solver.ny, solver.nx
    th0 = float(solver.mapping.theta_ref_lu)
    rho0 = float(solver.mapping.lattice.rho_ref_lu)
    hs = ny // 2
    y = np.arange(ny)
    dist = np.minimum(y, ny - y)
    prof = th0 + (th0 * theta_dc) * (1.0 - dist / hs)
    theta = np.tile(prof[:, None], (1, nx))
    solver.initialize_from_macro(rho0 * th0 / theta, np.zeros((ny, nx, 2)), theta)
    return BaseState(f=solver.f.copy(), g=solver.g.copy(),
                     theta_w=th0 * (1.0 + theta_dc), theta_amb=th0, hs=hs,
                     theta_dc_target=theta_dc, meta={})


def test_tangent_operator_prod_branch_is_bitwise_frozen_chain():
    cfg = {**BASE, "numerics": {**BASE["numerics"], "nx": 4, "ny": 8}}
    solver = CrossStackSolver2D(cfg, collision=COLLISION_PROD)
    hot = _tiny_base(solver, 0.05)
    cold = _tiny_base(solver, 0.0)
    hb = compute_stage_bases(solver, hot)
    cb = compute_stage_bases(solver, cold)
    # the cross-stack stage bases must also be the frozen ones on PROD
    xb = compute_stage_bases_crossstack(solver, hot, collision=COLLISION_PROD)
    assert np.array_equal(hb.h_f, xb.h_f) and np.array_equal(hb.h_g, xb.h_g)
    frozen = TangentOperator(solver, hot, hb, cold, cb, h=5e-5,
                             ablated=frozenset())
    mine = CrossStackTangentOperator(solver, hot, hb, cold, cb, h=5e-5,
                                     ablated=frozenset(),
                                     collision=COLLISION_PROD)
    rng = np.random.default_rng(20260814)
    df = rng.standard_normal(hot.f.shape) * 1e-6
    dg = rng.standard_normal(hot.g.shape) * 1e-6
    a = frozen.step(df.copy(), dg.copy(), 1e-4)
    b = mine.step(df.copy(), dg.copy(), 1e-4)
    assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])
    assert a[2] == b[2] and a[3] == b[3]


# ---------------------------------------------------------------------------
# BGK operator correctness
# ---------------------------------------------------------------------------

def test_bgk_conserves_mass_momentum_and_total_energy_exactly():
    s = _seeded(COLLISION_PROD)
    params = bgk_params_matching(s.mapping)
    assert_bgk_conservation(s.f, s.g, s.mapping, params, lattice=s.lattice,
                            tol=1e-12)
    _, _, diag = collide_fg_bgk(s.f, s.g, s.mapping, params, lattice=s.lattice,
                                return_diagnostics=True)
    assert float(np.max(np.abs(diag.energy_residual))) < 1e-14


def test_bgk_relax_is_exactly_linear():
    s = _seeded(COLLISION_PROD)
    from core.equilibrium import equilibrium_fg
    from core.macroscopic import recover_macro
    m = recover_macro(s.f, s.g, D=2, S=3, lattice=s.lattice)
    f_eq, g_eq = equilibrium_fg(m.rho, m.u, m.theta, 3, s.lattice)
    params = bgk_params_matching(s.mapping)
    rng = np.random.default_rng(11)
    df = rng.standard_normal(s.f.shape)
    dg = rng.standard_normal(s.g.shape)
    a = bgk_relax(s.f + df, s.g + dg, f_eq, g_eq, params, s.lattice)
    b = bgk_relax(s.f, s.g, f_eq, g_eq, params, s.lattice)
    c = bgk_relax(df, dg, np.zeros_like(f_eq), np.zeros_like(g_eq), params,
                  s.lattice)
    for i in (0, 1):
        num = a[i] - b[i] - c[i]
        assert float(np.max(np.abs(num))) < 1e-14 * float(np.max(np.abs(a[i])))


def test_bgk_block_composition_matches_single_shot_collide():
    s = _seeded(COLLISION_PROD)
    params = bgk_params_matching(s.mapping)
    f1, g1 = collide_fg_bgk(s.f, s.g, s.mapping, params, lattice=s.lattice)
    f2, g2 = compose_collide_bgk(s.f, s.g, s.mapping, s.lattice, params)
    assert np.array_equal(f1, f2) and np.array_equal(g1, g2)


def test_bgk_transport_inversion_round_trip():
    m = _mapping()
    p = bgk_params_matching(m)
    assert p.nu_lu == pytest.approx(float(m.nu_lu), rel=1e-14)
    assert p.alpha_lu == pytest.approx(float(m.alpha_lu), rel=1e-13)
    assert p.Pr_lu == pytest.approx(float(m.Pr_lu), rel=1e-12)
    # tau_f is the same shear relaxation the frozen mapping derives
    assert p.tau_f == pytest.approx(float(m.tau21), rel=1e-14)
    back = bgk_params_from_transport(p.nu_lu, p.alpha_lu,
                                     float(m.theta_transport_lu))
    assert back.tau_f == pytest.approx(p.tau_f, rel=1e-14)
    assert back.tau_g == pytest.approx(p.tau_g, rel=1e-13)


def test_bgk_params_fail_loud_outside_reach():
    m = _mapping()
    theta_t = float(m.theta_transport_lu)
    with pytest.raises(ValueError):
        BgkParams(tau_f=0.5, tau_g=0.7, theta_transport_lu=theta_t)
    with pytest.raises(ValueError):
        BgkParams(tau_f=0.6, tau_g=float("nan"), theta_transport_lu=theta_t)
    # alpha far below what tau_f alone already contributes -> tau_g <= 1/2
    with pytest.raises(ValueError):
        bgk_params_from_transport(float(m.nu_lu), 1e-6, theta_t)


# ---------------------------------------------------------------------------
# instrument anchoring: the transport probe IS the frozen G0/P2-5 instrument
# ---------------------------------------------------------------------------

def test_mode_decay_probe_matches_frozen_thermal_instrument():
    from verification.thermal_diffusion_measurement import (
        ThermalDiffusionSettings,
        measure_thermal_diffusion_direction,
    )

    ny, steps = 24, 400
    kw = dict(ny=ny, nx=4, steps=steps, sample_interval=max(1, steps // 400),
              fit_start=max(steps // 12, 10))
    ref = measure_thermal_diffusion_direction(
        BASE, "y", ThermalDiffusionSettings(amplitude=1e-5, mode_index=1, **kw))
    mine = measure_mode_decay(lambda c: CrossStackSolver2D(c, collision=COLLISION_PROD),
                              BASE, channel="thermal", **kw)
    assert mine["measured_lu"] == ref["alpha_measured_lu"]
    assert mine["fit"]["fitting_window"] == ref["fitting_window"]


def test_spectral_radius_probe_is_stable_on_production():
    r = one_step_spectral_radius(
        lambda c: CrossStackSolver2D(c, collision=COLLISION_PROD), BASE,
        ny=4, nx=4)
    assert r["acoustic_stage_identity"]
    # the uniform reference state is a fixed point of the production step
    assert r["fixed_point_residual"] < 1e-12
    # four conserved modes sit on the unit circle to the FD noise floor, and
    # nothing sits outside it -- the same frozen line the runner judges with
    assert r["spectral_radius"] <= LINE_SPECTRAL_RADIUS
    assert r["unstable_mode_count"] == 0
    assert sum(1 for v in r["top_magnitudes"] if v > 1.0 - 1e-6) >= 4


# ---------------------------------------------------------------------------
# fail-loud
# ---------------------------------------------------------------------------

def test_unknown_collision_branch_fails_loud():
    cfg = {**BASE, "numerics": {**BASE["numerics"], "nx": 4, "ny": 8}}
    with pytest.raises(ValueError):
        CrossStackSolver2D(cfg, collision="SRT_MAYBE")


def test_bgk_branch_refuses_prod_only_ablation_blocks():
    cfg = {**BASE, "numerics": {**BASE["numerics"], "nx": 4, "ny": 8}}
    solver = CrossStackSolver2D(cfg, collision=COLLISION_BGK)
    base = _tiny_base(solver, 0.0)
    bases = compute_stage_bases_crossstack(solver, base, collision=COLLISION_BGK,
                                           bgk_params=solver.bgk_params)
    for block in ("stress", "heatflux"):
        with pytest.raises(TangentStructureError):
            CrossStackTangentOperator(solver, base, bases, base, bases, h=5e-5,
                                      ablated=frozenset({block}),
                                      collision=COLLISION_BGK,
                                      bgk_params=solver.bgk_params)
    with pytest.raises(ValueError):
        CrossStackTangentOperator(solver, base, bases, base, bases, h=5e-5,
                                  ablated=frozenset(), collision=COLLISION_BGK,
                                  bgk_params=None)


def test_prod_branch_refuses_bgk_params():
    cfg = {**BASE, "numerics": {**BASE["numerics"], "nx": 4, "ny": 8}}
    p = bgk_params_matching(_mapping())
    with pytest.raises(ValueError):
        CrossStackSolver2D(cfg, collision=COLLISION_PROD, bgk_params=p)


# ---------------------------------------------------------------------------
# config plumbing + frozen catalogue
# ---------------------------------------------------------------------------

def test_variant_cfg_plumbing_non_mutating_and_collision_only():
    before = copy.deepcopy(BASE)
    for name in VARIANTS:
        cfg = variant_gas_cfg(BASE, name)
        assert BASE == before, "variant_gas_cfg mutated the base config"
        overrides = VARIANTS[name]["cfg"]
        for section in ("physical", "lattice", "numerics"):
            assert cfg[section] == BASE[section], section
        for key, value in cfg["collision"].items():
            expected = overrides.get(key, BASE["collision"][key])
            assert value == expected, f"{name}:{key}"
        assert set(cfg["collision"]) == set(BASE["collision"])
    with pytest.raises(ValueError):
        variant_gas_cfg(BASE, "NOT_A_VARIANT")


def test_prod_variant_is_an_empty_override():
    assert VARIANTS["PROD"]["cfg"] == {}
    assert VARIANTS["PROD"]["collision"] == COLLISION_PROD
    # the four excluded trace policies must never reappear in the catalogue
    banned = {"ghost_orthogonal_local_laplacian",
              "ghost_orthogonal_local_pressure_memory",
              "ghost_orthogonal_local_two_channel",
              "ghost_orthogonal_local_entropy_manifold",
              "ghost_orthogonal_spectral", "calibrated"}
    for spec in VARIANTS.values():
        assert spec["cfg"].get("trace_bulk_policy") not in banned


def test_checkpoint_labels_unique_across_variant_catalogue():
    labels = set()
    for v in VARIANTS:
        for suffix in [f"{v}_th0", f"{v}_th0.05", f"{v}_th0.1", f"{v}_cold",
                       f"{v}_th0.05_hot", f"{v}_th0.1_hot"]:
            assert suffix not in labels
            labels.add(suffix)


# ---------------------------------------------------------------------------
# pure analysis helpers
# ---------------------------------------------------------------------------

def _good(th):
    return {"finite": True, "stationarity_per_period": 1e-6,
            "dc_closure_rel": 5e-5, "theta_dc_measured": th,
            "mass_drift_settle": 1e-13, "snapshot": {"theta_dc_target": th}}


def test_partition_variants_drops_only_dead_variants():
    settles = {
        "PROD_th0": _good(0.0), "PROD_th0.05": _good(0.05),
        "BGK_th0": {"worker_exception": "RuntimeError: non-positive wall-row density"},
        "BGK_th0.05": {"finite": False},
        "TRTAU22_th0": _good(0.0),
        "TRTAU22_th0.05": {**_good(0.05), "stationarity_per_period": 1.0},
        "DEVMEAS_th0": _good(0.0), "DEVMEAS_th0.05": _good(0.05),
    }
    legality, status = partition_variants(
        settles, ["PROD", "BGK", "TRTAU22", "DEVMEAS"], [0.05])
    assert status["PROD"]["ok"] and status["DEVMEAS"]["ok"]
    assert not status["BGK"]["ok"] and "BGK_th0" in status["BGK"]["reason"]
    assert not status["TRTAU22"]["ok"]
    assert "legality gate" in status["TRTAU22"]["reason"]
    assert legality["PROD_th0.05"]["pass"]
    assert not legality["TRTAU22_th0.05"]["pass"]


def _rows(**variants):
    base = {"Y0_abs": 1.0e-3, "0.05": {"d_op_pct": -2.83},
            "0.1": {"d_op_pct": -5.32}}
    return {"PROD": base, **variants}


def test_classify_robust_sensitive_absent_mixed_and_livekey():
    thetas = ["0.05", "0.1"]
    robust = _rows(V={"Y0_abs": 1.1e-3, "0.05": {"d_op_pct": -2.90},
                      "0.1": {"d_op_pct": -5.40}})
    c = classify(robust, thetas)
    assert c["per_variant"]["V"]["label"] == "CROSSSTACK_ROBUST"
    assert c["per_variant"]["V"]["live_key"] and c["family"] == "CROSSSTACK_FAMILY_ROBUST"

    sensitive = _rows(V={"Y0_abs": 1.1e-3, "0.05": {"d_op_pct": -5.0},
                         "0.1": {"d_op_pct": -8.0}})
    assert classify(sensitive, thetas)["per_variant"]["V"]["label"] \
        == "CROSSSTACK_SENSITIVE"

    absent = _rows(V={"Y0_abs": 1.1e-3, "0.05": {"d_op_pct": 1.2},
                      "0.1": {"d_op_pct": 2.3}})
    ca = classify(absent, thetas)
    assert ca["per_variant"]["V"]["label"] == "CROSSSTACK_ABSENT"
    assert ca["family"] == "CROSSSTACK_FAMILY_ABSENT"

    mixed = _rows(V={"Y0_abs": 1.1e-3, "0.05": {"d_op_pct": 1.2},
                     "0.1": {"d_op_pct": -5.4}})
    assert classify(mixed, thetas)["per_variant"]["V"]["label"] == "CROSSSTACK_MIXED"

    # a structurally inert switch is NOT evidence, whatever its d_OP says
    inert = _rows(CTRL4TH={"Y0_abs": 1.0e-3 * (1 + 0.1 * LINE_LIVEKEY_Y0_REL),
                           "0.05": {"d_op_pct": -2.83},
                           "0.1": {"d_op_pct": -5.32}})
    ci = classify(inert, thetas)
    assert not ci["per_variant"]["CTRL4TH"]["live_key"]
    assert not ci["per_variant"]["CTRL4TH"]["evidence"]
    assert ci["family"] == "NO_LIVE_VARIANT" and ci["live_variant_count"] == 0

    assert classify({}, thetas)["label"] == "NO_ANCHOR"


def test_classify_line_is_the_frozen_one_and_caveat_flags():
    thetas = ["0.05", "0.1"]
    just_under = _rows(V={"Y0_abs": 1.1e-3,
                          "0.05": {"d_op_pct": -2.83 - 0.999 * LINE_CLASS_PP},
                          "0.1": {"d_op_pct": -5.32 - 0.999 * LINE_CLASS_PP}})
    assert classify(just_under, thetas)["per_variant"]["V"]["label"] \
        == "CROSSSTACK_ROBUST"
    just_over = _rows(V={"Y0_abs": 1.1e-3,
                         "0.05": {"d_op_pct": -2.83 - 1.001 * LINE_CLASS_PP},
                         "0.1": {"d_op_pct": -5.32 - 1.001 * LINE_CLASS_PP}})
    assert classify(just_over, thetas)["per_variant"]["V"]["label"] \
        == "CROSSSTACK_SENSITIVE"
    # a >30% cold |Y0| shift raises the cross-calibration caveat (never gates)
    shifted = _rows(V={"Y0_abs": 1.5e-3, "0.05": {"d_op_pct": -2.9},
                       "0.1": {"d_op_pct": -5.4}})
    row = classify(shifted, thetas)["per_variant"]["V"]
    assert row["cross_calibration_caveat"] and row["evidence"]


def test_dop_sign_convention_matches_the_frozen_definition():
    from scripts.phase5_crossstack_collision_scan import _dop

    row = _dop(complex(0.9, 0.0), complex(1.0, 0.0))
    assert row["d_op_pct"] == pytest.approx(-10.0)
    assert row["phase_deg"] == pytest.approx(0.0)
    assert math.isfinite(row["phase_deg"])
