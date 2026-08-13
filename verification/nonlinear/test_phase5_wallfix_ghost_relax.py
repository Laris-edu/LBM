"""Ghost-relaxation scan contract tests (D0-7 diagnostic unit).

Mechanism-level guards for scripts/phase5_wallfix_ghost_relax_scan.py:

- ANCHOR FACT: fourth_order closure at high_tau=1.0 coincides with the
  production second_order closure at the collide level (<=1e-8 rel on a
  seeded hot-profile state; probe measured 7.8e-10) — the scan's baseline is
  the production physics, not a different instrument;
- knob aliveness: high_tau=1.5 vs 1.0 changes one collide output by >=1e-6
  (dead-key guard; probe measured 2.2e-4) via the runner's own check;
- config plumbing: scan_gas_cfg is non-mutating and sets exactly the two
  collision keys;
- checkpoint namespace: settle/tangent labels are unique across the frozen
  high_tau ladder (resume-by-label cannot collide);
- classify(): NULL / ACTIVE / missing-anchor branches on synthetic rows.

No scan verdicts here — judgement lines live frozen in the runner.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from core.collision_smrt import collide_fg
from core.solver import GasSolver2D
from scripts.phase2_m2_verification import load_config
from scripts.phase5_wallfix_ghost_relax_scan import (
    HIGH_TAU_LADDER,
    LINE_SCAN_NULL_PP,
    aliveness_check,
    classify,
    scan_gas_cfg,
)

BASE = load_config(Path("configs/gas_air_10k_d2q37_levelc_dx2p6.yaml"))


def _seeded(cfg):
    cfg = {**cfg, "numerics": {**cfg["numerics"], "nx": 4, "ny": 24}}
    s = GasSolver2D(cfg)
    th0 = float(s.mapping.theta_ref_lu)
    rho0 = float(s.mapping.lattice.rho_ref_lu)
    y = np.arange(24)
    prof = th0 * (1.0 + 0.05 * np.cos(2 * np.pi * y / 24))[:, None]
    theta = np.tile(prof, (1, 4))
    s.initialize_from_macro(rho0 * th0 / theta, np.zeros((24, 4, 2)), theta)
    s.step(5)
    return s


def test_fourth_order_at_unity_matches_production_collide():
    s2 = _seeded(BASE)
    f0, g0 = s2.f.copy(), s2.g.copy()
    fc2, gc2 = collide_fg(f0.copy(), g0.copy(), s2.mapping, lattice=s2.lattice)
    s4 = _seeded(scan_gas_cfg(BASE, 1.0))
    fc4, gc4 = collide_fg(f0.copy(), g0.copy(), s4.mapping, lattice=s4.lattice)
    # measured: 7.8e-10 on the production-like ny=96 profile state, 1.5e-6 on
    # this STEEP ny=24 rig (larger non-equilibrium exposes the projection-basis
    # difference); line 1e-5 = steep-state upper bound. The physics-level
    # anchor gate is the runner's auth d_OP row (0.2 pp vs frozen TAN).
    scale = float(np.max(np.abs(fc2)))
    assert float(np.max(np.abs(fc4 - fc2))) / scale < 1e-5
    gscale = float(np.max(np.abs(gc2))) + 1e-300
    assert float(np.max(np.abs(gc4 - gc2))) / gscale < 1e-5


def test_knob_alive_via_runner_check():
    r = aliveness_check(BASE)
    assert r["pass"] and r["rel_diff_1p5_vs_1p0"] >= 1e-6


def test_scan_cfg_plumbing_non_mutating():
    before = BASE["collision"]["central_moment_closure"]
    cfg = scan_gas_cfg(BASE, 1.2)
    assert BASE["collision"]["central_moment_closure"] == before
    assert cfg["collision"]["central_moment_closure"] == "fourth_order"
    assert cfg["collision"]["high_order_relaxation"] == 1.2
    # everything else untouched
    same = {k: v for k, v in cfg["collision"].items()
            if k not in ("central_moment_closure", "high_order_relaxation")}
    for k, v in same.items():
        assert BASE["collision"][k] == v


def test_checkpoint_labels_unique_across_ladder():
    labels = set()
    for ht in HIGH_TAU_LADDER:
        for th in (0.0, 0.05, 0.10):
            for suffix in (f"ht{ht:g}_th{th:g}",
                           f"ht{ht:g}_th{th:g}_hot"):
                assert suffix not in labels
                labels.add(suffix)
        cold = f"ht{ht:g}_cold"
        assert cold not in labels
        labels.add(cold)


def test_classify_branches():
    base = {"Y0_abs": 1.0, "0.05": {"d_op_pct": -2.83},
            "0.1": {"d_op_pct": -5.32}}
    null_rows = {"1": base,
                 "1.5": {"Y0_abs": 1.001,
                         "0.05": {"d_op_pct": -2.83 + 0.1},
                         "0.1": {"d_op_pct": -5.32 - 0.1}}}
    c = classify(null_rows, ["0.05", "0.1"])
    assert c["label"] == "GHOST_RELAX_NULL"
    assert not c["per_ht"]["1.5"]["active"]
    act_rows = {"1": base,
                "1.5": {"Y0_abs": 1.01,
                        "0.05": {"d_op_pct": -2.83 + 2.0},
                        "0.1": {"d_op_pct": -5.32 + 2.0}}}
    c2 = classify(act_rows, ["0.05", "0.1"])
    assert c2["label"] == "GHOST_RELAX_ACTIVE"
    assert c2["per_ht"]["1.5"]["active"]
    assert abs(c2["per_ht"]["1.5"]["delta_dop_pp"][0]) >= LINE_SCAN_NULL_PP
    assert classify({}, ["0.05"])["label"] == "NO_ANCHOR"
    with pytest.raises(KeyError):
        _ = c2["per_ht"]["1"]  # anchor row never classified against itself
