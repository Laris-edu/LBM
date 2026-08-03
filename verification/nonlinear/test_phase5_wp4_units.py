"""WP4 submatrix machinery tests (D5-6 SCOPED_GO; contract §15.1/§15.2/§15.4).

Mechanism-level certification of the A5 chi-map design algebra (the only
net-new WP4 implementation surface) and the WP4 config pre-registration
freezes (A2a map points, A1 full ladder, A5 grid). The coupled-loop
integrator itself is the G4a-certified instrument (its discrete-map fixture
lives in test_phase5_g4a_dc_basestate.py) — not re-tested here.
Authoritative physics numbers belong to the WP4 runs, not to these tests.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from scripts.phase2_m2_verification import load_config
from scripts.phase5_a5_chi_map import (
    amplitude_residual_rows,
    chi_case_label,
    design_chi_point,
)

A5_CFG = Path("configs/phase5/a5_chi_map/a5_wp4_10k_dx2p6.yaml")
A2A_DC002_CFG = Path("configs/phase5/a2a_operating_point/a2a_wp4_dc002_10k_dx2p6.yaml")
A2A_DC0075_CFG = Path("configs/phase5/a2a_operating_point/a2a_wp4_dc0075_10k_dx2p6.yaml")
A1_WP4_CFG = Path("configs/phase5/a1_signed_zero_mean/a1_wp4_full_ladder_10k_dx2p6.yaml")


def _cplx_to_c(d):
    return complex(d["re"], d["im"])


def test_design_chi_point_axis_and_inversion():
    # synthetic-but-realistic anchors: |Y| ~ 2e-3 (LU areal), wp state a few %
    # softer than cold, P_mean from Theta_DC=0.05 with G_DC/|Y_AC| ~ 0.08
    om_step = 2.0 * math.pi / 1280.0
    th0 = 0.35
    y_cold = 2.0e-3 * complex(math.cos(0.72), math.sin(0.72))
    y_wp = 0.97 * y_cold * complex(math.cos(-0.02), math.sin(-0.02))
    p_mean = 0.05 * th0 * 0.08 * abs(y_cold)
    for chi0 in (0.01, 0.3, 3.0):
        for eps_t in (0.01, 0.05):
            d = design_chi_point(chi0=chi0, eps_target=eps_t,
                                 y_cold_area=y_cold, y_wp_area=y_wp,
                                 p_mean_area=p_mean, om_step=om_step, th0=th0)
            # (a) cold-referenced chi axis roundtrip is EXACT
            assert om_step * d["c_a_lu"] / (2.0 * abs(y_cold)) == pytest.approx(
                chi0, rel=1e-14)
            # (b) closed-form inversion: |P1 * G1_closed| == eps_target*th0 exact
            p1 = d["p1_over_pmean"] * p_mean
            assert abs(p1 * d["g1_closed_form"]) == pytest.approx(
                eps_t * th0, rel=1e-13)
            assert d["expected_ts_hat_lu"] == pytest.approx(eps_t * th0, rel=1e-14)
            # (c) WP-referenced chi_eff
            assert d["chi_eff"] == pytest.approx(
                chi0 * abs(y_cold) / abs(y_wp), rel=1e-14)
            # (d) signed-power flag is the p1_over>1 predicate
            assert d["total_power_signed"] == (d["p1_over_pmean"] > 1.0)
    # design consequence (pre-registered expectation, documented so it cannot
    # be silently "fixed" later): with the realistic G_DC/|Y_AC| ~ 0.08 anchor
    # every eps_target=0.05 point requires SIGNED total power (p1/pmean >> 1)
    d = design_chi_point(chi0=0.01, eps_target=0.05, y_cold_area=y_cold,
                         y_wp_area=y_wp, p_mean_area=p_mean, om_step=om_step,
                         th0=th0)
    assert d["p1_over_pmean"] > 5.0 and d["total_power_signed"]
    # large-chi points need MORE drive for the same amplitude (capacity rolloff)
    d3 = design_chi_point(chi0=3.0, eps_target=0.05, y_cold_area=y_cold,
                          y_wp_area=y_wp, p_mean_area=p_mean, om_step=om_step,
                          th0=th0)
    assert d3["p1_over_pmean"] > 3.0 * d["p1_over_pmean"]


def test_design_chi_point_si_table_reproduction():
    # the cold-referenced axis reproduces the contract §15.4 C_A table through
    # the y_hs bridge: C_A_si = chi0 * 2 * y_hs_si / om_si (table is rounded
    # to 3 significant digits -> 2% tolerance)
    om_si = 2.0 * math.pi * 1.0e4
    y_hs_si = 1393.4
    table = {0.01: 4.45e-4, 0.1: 4.45e-3, 0.3: 1.34e-2, 1.0: 4.45e-2, 3.0: 1.34e-1}
    for chi0, c_a_expect in table.items():
        assert chi0 * 2.0 * y_hs_si / om_si == pytest.approx(c_a_expect, rel=2e-2)


def test_design_chi_point_fail_loud():
    om_step = 2.0 * math.pi / 1280.0
    good = dict(chi0=0.1, eps_target=0.01, y_cold_area=2e-3 + 1e-3j,
                y_wp_area=2e-3 + 1e-3j, p_mean_area=1e-5, om_step=om_step,
                th0=0.35)
    with pytest.raises(ValueError):
        design_chi_point(**{**good, "p_mean_area": 0.0})
    with pytest.raises(ValueError):
        design_chi_point(**{**good, "chi0": -0.1})
    with pytest.raises(ValueError):
        design_chi_point(**{**good, "y_wp_area": complex("nan")})
    with pytest.raises(ValueError):
        design_chi_point(**{**good, "y_cold_area": 0.0 + 0.0j})


def test_amplitude_residual_pairing():
    def row(c):
        return {"status": "stable",
                "consistency_ratio": {"re": c.real, "im": c.imag}}

    c_lo, c_hi = 1.03 * np.exp(1j * 0.02), 1.06 * np.exp(1j * 0.05)
    points = {chi_case_label(0.1, 0.01): row(c_lo),
              chi_case_label(0.1, 0.05): row(c_hi),
              chi_case_label(3.0, 0.01): row(c_lo),
              chi_case_label(3.0, 0.05): {"status": "unstable"}}
    rows = amplitude_residual_rows(points, [0.1, 3.0, 0.3], [0.01, 0.05])
    # complete pair: D_chi = c_hi / c_lo (complex, both axes)
    got = _cplx_to_c(rows["0.1"]["D_chi"])
    assert got == pytest.approx(c_hi / c_lo, rel=1e-12)
    assert rows["0.1"]["eps_lo"] == 0.01 and rows["0.1"]["eps_hi"] == 0.05
    # missing/unstable arms are reported incomplete, never silently dropped
    assert rows["3"]["status"] == "incomplete"
    assert rows["0.3"]["status"] == "incomplete"


def test_a5_pre_registration_frozen():
    cfg = load_config(A5_CFG)
    a5 = cfg["a5"]
    # §15.4 grid verbatim; eps 0.10 truncated by the G1a authorization boundary
    assert [float(c) for c in a5["chi_ladder"]] == [0.01, 0.1, 0.3, 1.0, 3.0]
    assert [float(e) for e in a5["eps_targets"]] == [0.01, 0.05]
    assert max(float(e) for e in a5["eps_targets"]) <= 0.075
    # canonical working point + G4a tent geometry verbatim
    assert float(a5["theta_dc"]) == 0.05 and int(a5["hs_rows"]) == 48
    assert float(a5["guard_factor"]) == 5.0
    assert float(a5["settle_periods"]) == 5.0
    # uniform coupled protocol (no per-chi tuning), film-pole margin at chi=3
    assert float(a5["drive_coupled_periods"]) == 6.0
    assert float(a5["fit_skip_coupled_periods"]) == 3.0
    # §3.5 material relevance: complete over the ladder, legal values only,
    # large-C_A points pre-registered as regime extensions (not CNT points)
    rel = {str(k): str(v) for k, v in a5["material_relevance"].items()}
    for chi0 in a5["chi_ladder"]:
        assert f"{float(chi0):g}" in rel
    assert set(rel.values()) <= {"supported", "synthetic_regime_extension"}
    assert rel["1"] == "synthetic_regime_extension"
    assert rel["3"] == "synthetic_regime_extension"
    # G1a envelope hard guard
    assert float(a5["eps_realized_max"]) <= 0.08
    assert "a5_smoke" in cfg
    assert float(cfg["a5_smoke"]["drive_coupled_periods"]) < float(
        a5["drive_coupled_periods"])


def test_a2a_wp4_configs_frozen():
    for path, theta, tag in ((A2A_DC002_CFG, 0.02, "dc002"),
                             (A2A_DC0075_CFG, 0.075, "dc0075")):
        cfg = load_config(path)
        p = cfg["pdc2"]
        assert float(p["theta_dc"]) == theta
        assert str(p["label_tag"]) == tag
        # G4a canonical instrument verbatim (only theta_dc + naming differ)
        assert [float(e) for e in p["eps_ac"]] == [0.005, 0.02]
        assert int(p["hs_rows"]) == 48 and int(p["nx"]) == 8
        assert float(p["coupled_chi0"]) == 0.016
        assert float(p["qs_alpha_temperature_exponent"]) == 1.04
        assert float(cfg["gates"]["domain_recheck_dop_abs"]) == 0.10
        # archived trend chain present for the monotonicity readout
        refs = {float(r["theta_dc"]): float(r["dop_abs_minus_1"])
                for r in p["dop_reference_points"]}
        assert refs[0.05] == pytest.approx(-0.0283) and refs[0.10] == pytest.approx(-0.0531)
        assert "pdc2_smoke" in cfg


def test_a1_wp4_full_ladder_frozen():
    cfg = load_config(A1_WP4_CFG)
    a1 = cfg["a1"]
    # §15.1 full ladder truncated at the G1a authorization boundary 0.075
    assert [float(e) for e in a1["eps_ladder"]] == [
        0.001, 0.003, 0.01, 0.02, 0.03, 0.05, 0.075]
    assert max(float(e) for e in a1["eps_ladder"]) <= 0.075
    # G1-W pair protocol constants verbatim (WP3 lineage unchanged)
    assert (float(a1["ramp_periods"]), float(a1["periods"]),
            float(a1["fit_skip_periods"])) == (2.0, 14.0, 12.0)
    assert int(a1["ny"]) == 48 and int(a1["samples_per_period"]) == 64
    assert float(a1["wall_contrast_eps"]) == 0.05
    assert float(cfg["gates"]["mass_drift_max"]) == 1.0e-8
    assert "a1_smoke" in cfg
