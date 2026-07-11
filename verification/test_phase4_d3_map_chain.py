"""P4-D3 D3-4(iii) gate: map -> soft-source injection -> coarse propagation chain smoke.

Project: docs/Phase_4/M4/P4_D3_Multidomain_Acoustic_Project.md (D3-4; section 12.2).

Chains the certified pieces (compact-source map 12.1 -> one-way soft source 11 -> coarse
domain -> D3-2 sponge) and gates the LINK MECHANICS (the additive soft source carries a fixed
complex rig constant G, so absolute amplitude is calibration, not a gate here):

  * linearity: G identical across a 10x drive range (chain is linear -- G is a rig constant);
  * one-wayness w-/w+ < 0.05 at the control band (section-11 gate holds in-chain);
  * clean traveling wave: linear phase along the band (tiny fit residual) + flat |w+|;
  * the SI phase velocity at the operating point meets the acoustic-domain certification
    (P2-6 wording <2% vs TRUE air c0): the (iv) decision calibrated the config's c0_m_s knob
    (347.0 -> 339.9175 = 347/1.020836, the G1-linear medium constant), landing the realized
    c_SI at +0.17% (ny=512 rig; measured against AIR_C0, never the config knob).

Smaller rig than the probe (ny=384, 8 periods) to keep runtime test-friendly."""

from __future__ import annotations

from pathlib import Path

from scripts.phase2_m2_verification import load_config
from scripts.phase4_d3_map_chain_smoke import evaluate_chain_runs, run_chain

ACOUSTIC_CONFIG = Path("configs/phase4_acoustic_coarse_dx334.yaml")
KW = dict(ny=384, total_periods=8.0, fit_periods=3.0)


def test_chain_linear_oneway_clean():
    """One chain pair: linearity across 10x drive + one-way + clean traveling wave."""

    base = load_config(ACOUSTIC_CONFIG)
    a = run_chain(base, T_s_hat_K=10.0, **KW)
    b = run_chain(base, T_s_hat_K=1.0, **KW)
    assert not a.get("crash") and not b.get("crash")
    for r in (a, b):
        assert r["mass_rel_drift"] < 1.0e-4
        assert r["onewayness"] < 0.05          # section-11 gate holds in-chain
        assert r["band_flatness"] < 0.02       # low dissipation across the band
        assert r["phase_fit_resid_rad"] < 0.02  # linear phase = clean traveling wave
    assert abs(a["G_abs"] / b["G_abs"] - 1.0) < 0.01      # G is a rig constant (linearity)
    assert abs(a["G_phase_deg"] - b["G_phase_deg"]) < 0.5
    passed, _gates = evaluate_chain_runs(a, b)
    assert passed


def test_chain_operating_point_sound_speed_certified():
    """(iv) certification: realized SI phase velocity within the P2-6 wording (<2%) of TRUE
    air c0 on the CALIBRATED medium (c0_m_s knob = 347/1.020836; ny=512 rig read +0.17%)."""

    base = load_config(ACOUSTIC_CONFIG)
    r = run_chain(base, T_s_hat_K=10.0, **KW)
    assert not r.get("crash")
    assert abs(r["c_si_over_air"] - 1.0) < 0.02


def test_chain_verdict_rejects_a_failed_physical_gate():
    good = {
        "crash": False,
        "G_abs": 0.158,
        "G_phase_deg": 152.4,
        "mass_rel_drift": 1.0e-6,
        "onewayness": 0.01,
        "band_flatness": 0.001,
        "phase_fit_resid_rad": 0.001,
        "c_si_over_air": 1.0,
    }
    bad = {**good, "onewayness": 0.2}
    passed, gates = evaluate_chain_runs(good, bad)
    assert not passed
    assert gates["onewayness_max"] == 0.2
