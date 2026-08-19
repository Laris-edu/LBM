"""Contract tests for the A2a-STRICT_B ensemble-axis scan (plan PLAN_v1.0)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.phase5_a2asb_ensemble_scan import (  # noqa: E402
    CSV_COLUMNS,
    DM_ACTIVE_PCT,
    QS_FLAT_FRAC,
    RESID_FLOOR_PP,
    RESID_FRAC,
    SLOPE_AGREE_REL,
    TAN_EQ_ANCHORS_PCT,
    TAN_XCHECK_PP,
    classify_ensemble,
    five_point_grid,
    three_point_grid,
)


def test_grid_formulas():
    r = 0.9758028
    g5 = five_point_grid(r)
    assert g5[0] == r                       # wet point exactly first
    assert g5[2] == 1.0
    assert abs(sum(g5) / 5.0 - 1.0) < 1e-15  # symmetric about equal mass
    assert abs((g5[0] + g5[4]) / 2.0 - 1.0) < 1e-15
    assert abs((g5[1] + g5[3]) / 2.0 - 1.0) < 1e-15
    g3 = three_point_grid(r)
    assert g3 == [r, 0.5 * (1 + r), 1.0]


def _pts(dm_list, slope, intercept, qs_slope=0.0, noise=None):
    out = []
    for i, dm in enumerate(dm_list):
        d = slope * dm + intercept + (noise[i] if noise else 0.0)
        out.append({"dm_pct": dm, "d_op_pct": d, "d_qs1_pct": qs_slope * dm})
    return out


def test_classification_confirmed():
    dm5 = [-2.42, -1.21, 0.0, 1.21, 2.42]
    dm3 = [-4.69, -2.34, 0.0]
    cls = classify_ensemble({
        0.05: _pts(dm5, 0.95, -0.21, qs_slope=0.05),
        0.10: _pts(dm3, 1.00, -0.25, qs_slope=0.05)})
    assert cls["label"] == "ENSEMBLE_AXIS_CONFIRMED", cls
    assert abs(cls["fits"]["0.05"]["slope_pp_per_pct"] - 0.95) < 1e-9
    assert cls["slope_ok"] and cls["qs_flat_ok"] and cls["lin_ok"]


def test_classification_partial_slope_mismatch():
    dm5 = [-2.42, -1.21, 0.0, 1.21, 2.42]
    dm3 = [-4.69, -2.34, 0.0]
    cls = classify_ensemble({
        0.05: _pts(dm5, 0.95, -0.21),
        0.10: _pts(dm3, 0.60, -0.25)})     # 37% slope mismatch
    assert cls["label"] == "ENSEMBLE_AXIS_PARTIAL"
    assert cls["lin_ok"] and not cls["slope_ok"]


def test_classification_partial_qs_not_flat():
    dm5 = [-2.42, -1.21, 0.0, 1.21, 2.42]
    dm3 = [-4.69, -2.34, 0.0]
    cls = classify_ensemble({
        0.05: _pts(dm5, 0.95, -0.21, qs_slope=0.5),   # QS carries > 20%
        0.10: _pts(dm3, 0.95, -0.25, qs_slope=0.5)})
    assert cls["label"] == "ENSEMBLE_AXIS_PARTIAL"
    assert not cls["qs_flat_ok"]


def test_classification_not_confirmed_nonlinear():
    dm5 = [-2.42, -1.21, 0.0, 1.21, 2.42]
    noise = [1.5, -1.5, 1.5, -1.5, 1.5]     # gross nonlinearity vs span
    dm3 = [-4.69, -2.34, 0.0]
    cls = classify_ensemble({
        0.05: _pts(dm5, 0.95, -0.21, noise=noise),
        0.10: _pts(dm3, 0.95, -0.25)})
    assert cls["label"] == "ENSEMBLE_AXIS_NOT_CONFIRMED"
    assert not cls["lin_ok"]


def test_frozen_lines():
    assert RESID_FLOOR_PP == 0.05
    assert RESID_FRAC == 0.05
    assert SLOPE_AGREE_REL == 0.15
    assert QS_FLAT_FRAC == 0.20
    assert DM_ACTIVE_PCT == 0.1
    assert TAN_XCHECK_PP == 0.2
    assert TAN_EQ_ANCHORS_PCT == {0.05: -0.2132076984426745,
                                  0.10: -0.24670587525119636}


def test_csv_schema():
    assert CSV_COLUMNS == ["theta_dc", "mass_rel", "dm_pct", "mass_target",
                           "Y_re", "Y_im", "d_op_pct", "phase_deg", "qs0_pct",
                           "qs1_pct", "qs1k_pct", "r_ens_pp", "u_d_pp",
                           "resumed", "g0_scope", "status"]


def test_diagnostic_labels_are_preregistered_set():
    src = (REPO_ROOT / "scripts" / "phase5_a2asb_ensemble_scan.py").read_text(
        encoding="utf-8")
    for name in ("ENSEMBLE_AXIS_CONFIRMED", "ENSEMBLE_AXIS_PARTIAL",
                 "ENSEMBLE_AXIS_NOT_CONFIRMED",
                 "UNINTERPRETABLE_ENSEMBLE_SCAN"):
        assert f'"{name}"' in src
    # the judgement run's four-level plan labels stay user-owned: the scan
    # must never emit them
    for name in ("EFFECTIVE_RESOLUTION", "EFFECTIVE_MITIGATION",
                 '"NOT_RESOLVED"', "STRICT_B_SCIENTIFICALLY_VALIDATED"):
        assert name not in src.replace("ENSEMBLE_AXIS_NOT_CONFIRMED", "")
