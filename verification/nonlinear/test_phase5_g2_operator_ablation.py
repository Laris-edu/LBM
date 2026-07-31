"""G2-O operator-ablation machinery tests (contract §7.3 deliverable, WP2).

Mechanism-level certification of the ablation instrument chain: mutation
plumbing (dotted paths reach REAL solver switches and change solver behavior —
a typo'd path would silently create a dead key), the signed-pair single-tone
instrument (odd combination kills drive-even physical content, KEEPS
operator-like sign-linear 2f — the non-degeneracy that makes S1 worth
running), window-pair sensitivity, and the runner's end-to-end file/gate
contract on a micro matrix. The authoritative G2-O run (10/20 kHz, five
variants, dx2p6 production rig) is recorded in Phase5_STATUS §3; its verdict
is NOT asserted here (physics belongs to the gate, not the test).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest
import yaml

from core.solver import GasSolver2D
from scripts.phase2_m2_verification import load_config
from scripts.phase5_g2o_operator_ablation import (
    apply_mutations,
    odd_pair_leakage,
    run_g2o,
    two_window_sensitivity,
)

GAS_CONFIG = Path("configs/gas_air_10k_d2q37_levelc_dx2p6.yaml")
G2O_CONFIG = Path("configs/phase5/g2_operator_ablation/g2o_10k20k_dx2p6.yaml")


def _walk(cfg: dict, dotted: str):
    node = cfg
    for k in dotted.split("."):
        assert isinstance(node, dict) and k in node, f"dead mutation path: {dotted}"
        node = node[k]
    return node


def test_apply_mutations_paths_exist_and_frozen_copy_untouched():
    gas = load_config(GAS_CONFIG)
    g2o = load_config(G2O_CONFIG)
    for block in ("g2o", "g2o_smoke"):
        for var in g2o[block]["variants"]:
            for dotted, value in dict(var.get("mutations", {})).items():
                before = _walk(gas, dotted)  # path must pre-exist in frozen config
                mutated = apply_mutations(gas, {dotted: value})
                assert _walk(mutated, dotted) == value
                assert _walk(gas, dotted) == before  # deep copy: original untouched


def test_mutations_reach_solver_and_change_behavior():
    gas = load_config(GAS_CONFIG)
    gas["numerics"] = {**gas.get("numerics", {}), "nx": 4, "ny": 16}
    s0 = GasSolver2D(apply_mutations(gas, {}))
    s1 = GasSolver2D(apply_mutations(
        gas, {"collision.acoustic_phase_correction_enabled": False}))
    s2 = GasSolver2D(apply_mutations(
        gas, {"numerics.high_wavenumber_filter.enabled": False}))
    s4 = GasSolver2D(apply_mutations(
        gas, {"collision.dispersion_correction_enabled": False}))
    assert s0.mapping.collision.acoustic_phase_correction_enabled is True
    assert s1.mapping.collision.acoustic_phase_correction_enabled is False
    assert s0.high_wavenumber_filter_enabled and not s2.high_wavenumber_filter_enabled
    assert s0.high_wavenumber_filter_strength == pytest.approx(0.0065)
    # same seed field, few steps: v2/v4 must DIVERGE (active operators);
    # v1 must stay byte-identical (structural identity, asserted below)
    rng = np.random.default_rng(3)
    theta0 = float(s0.mapping.theta_ref_lu)
    bump = theta0 * (1.0 + 1e-4 * rng.normal(size=(16, 4)))
    u0 = np.zeros((16, 4, 2))
    for s in (s0, s1, s2, s4):
        s.initialize_from_macro(1.0, u0, bump)
        for _ in range(20):
            s.step()
    t0f, t1f, t2f, t4f = (s.get_temperature_lu() for s in (s0, s1, s2, s4))
    assert np.max(np.abs(t2f - t0f)) > 1e-12   # filter is a real active operator
    assert np.max(np.abs(t4f - t0f)) > 1e-12   # dispersion corr (v4 diagnostic) active
    assert np.max(np.abs(t1f - t0f)) == 0.0    # see structural-identity test below


def test_acoustic_phase_correction_is_structurally_identity_on_g2_rig():
    # The §7.3 post-callback "spectral correction" family is IDENTITY on the
    # sealed-rig geometry + frozen config, for two independently checkable
    # reasons. The G2-O runner's S6 row asserts byte-identity of the recorded
    # series; this test pins the two structural facts so any future change to
    # threshold/factors/geometry that re-activates the operator FAILS here
    # (and S6 falsifies at run level) instead of silently changing the gate.
    from core.solver import _low_diagonal_fourier_modes
    gas = load_config(GAS_CONFIG)
    ll = float(gas["collision"]["acoustic_phase_correction_low_laplacian"])
    # (1) diagonal branch needs kx != 0 AND ky != 0 below the laplacian
    # threshold: zero qualifying modes on the production and smoke rigs
    for ny, nx in ((48, 8), (16, 4)):
        assert _low_diagonal_fourier_modes(ny, nx, ll) == []
    # (2) high-mode branch early-returns because both factors are exactly 1.0
    assert gas["collision"]["acoustic_phase_high_mode_policy"] == "specified"
    assert float(gas["collision"]["acoustic_phase_high_mode_factor"]) == 1.0
    assert float(gas["collision"]["acoustic_phase_high_mode_diagonal_factor"]) == 1.0


def _pair_stub(operator_2f_rel: float, physical_2f_rel: float):
    """Synthetic ± drive pair: physical 2f is drive-even, operator 2f is
    sign-linear (flips with the carrier)."""

    f = 1.0e4
    om = 2.0 * math.pi * f
    t = np.arange(0, 4.0 / f, 1.0 / f / 64.0)
    runs = {}
    for sign in (1.0, -1.0):
        carrier = sign * np.cos(om * t)
        phys2 = physical_2f_rel * np.cos(2 * om * t + 0.7)          # ~eps^2: even
        oper2 = sign * operator_2f_rel * np.cos(2 * om * t - 0.2)   # ~eps^1: odd
        sig = carrier + phys2 + oper2
        runs[sign] = {"t_s": t, "q_moment_si": sig, "p_box_lu": 0.5 * sig}
    return runs[1.0], runs[-1.0], f


def test_odd_pair_kills_physical_2f_keeps_operator_2f():
    # floor: physical (drive-even) 2f at 1e-4 relative -> odd combination clean
    plus, minus, f = _pair_stub(operator_2f_rel=0.0, physical_2f_rel=1e-4)
    out = odd_pair_leakage(plus, minus, f, settle_periods=1.0)
    assert out["max_nontarget"] <= 1e-10
    # even channel still SEES the physical 2f (instrument archives it)
    assert out["q_moment_si"]["even_2f_rel_1f"] == pytest.approx(1e-4, rel=1e-3)
    # non-degeneracy: sign-linear operator 2f SURVIVES the odd combination at
    # its injected level -- this is exactly what S1 gates at 1e-8
    plus, minus, f = _pair_stub(operator_2f_rel=3e-7, physical_2f_rel=1e-4)
    out = odd_pair_leakage(plus, minus, f, settle_periods=1.0)
    assert out["q_moment_si"]["odd_2f_rel"] == pytest.approx(3e-7, rel=1e-3)
    assert out["max_nontarget"] > 1e-8


def test_two_window_sensitivity_detects_drift():
    f = 1.0e4
    om = 2.0 * math.pi * f
    t = np.arange(0, 4.0 / f, 1.0 / f / 64.0)
    clean = {"t_s": t, "p_box_lu": np.cos(om * t) + 1e-3 * np.cos(2 * om * t),
             "q_moment_si": np.cos(om * t) + 1e-3 * np.cos(2 * om * t)}
    w = two_window_sensitivity(clean, f, settle_periods=1.0, n_harmonics=5)
    assert w["p1f_amp_rel"] < 1e-12 and w["H2q_diff"] < 1e-15
    drift = 1.0 + 0.05 * (t * f / 4.0)
    drifty = {"t_s": t, "p_box_lu": drift * clean["p_box_lu"],
              "q_moment_si": drift * clean["q_moment_si"]}
    w = two_window_sensitivity(drifty, f, settle_periods=1.0, n_harmonics=5)
    assert w["p1f_amp_rel"] > 1e-3  # drifting amplitude is visible to the pair


def test_authoritative_config_is_contract_frozen():
    cfg = load_config(G2O_CONFIG)
    proto, gates = cfg["g2o"], cfg["gates"]
    assert [float(f) for f in proto["frequencies_Hz"]] == [1.0e4, 2.0e4]
    # S1 instrument = G1-W certified signed-pair protocol at 10 kHz verbatim;
    # settle transfers across frequency in BOX-RELAXATION units (>= ~11 tau_box,
    # tau_box = 1.47 periods @20 kHz) — the 20 kHz override is the pre-registered
    # physical rule, not tuning
    pair = proto["pair"]
    assert (float(pair["epsilon"]), float(pair["ramp_periods"]),
            float(pair["settle_periods"]), float(pair["periods"])) == (1e-4, 2.0, 12.0, 14.0)
    ov20 = [ov for ov in pair["overrides"] if float(ov["frequency_Hz"]) == 2.0e4]
    assert len(ov20) == 1 and float(ov20[0]["settle_periods"]) >= 11 * 1.47
    assert float(ov20[0]["periods"]) - float(ov20[0]["settle_periods"]) >= 2.0
    # contract §7.3 thresholds
    assert float(gates["single_tone_leakage_rel"]) == 1e-8
    assert float(gates["dg_sensitivity_pp"]) == pytest.approx(0.01)
    assert float(gates["h2_sensitivity_fraction"]) == pytest.approx(0.1)
    # v0 present; v4 (in-collision dispersion) is diagnostic-only, not gated
    variants = {str(v["id"]): v for v in proto["variants"]}
    assert "v0_frozen" in variants and not variants["v0_frozen"].get("mutations")
    assert variants["v4_dispersion_off_diag"].get("diagnostic_only") is True
    # v1 is the structurally-identity family: must carry the S6 flag in BOTH
    # protocol blocks (the falsifiable byte-identity row replaces a trivially-
    # passing ablation delta)
    for block in ("g2o", "g2o_smoke"):
        v1 = {str(v["id"]): v for v in cfg[block]["variants"]}["v1_acoustic_corr_off"]
        assert v1.get("identity_expected") is True
    # gated variants cover the post-callback operator families of §7.3
    muts = [m for vid, v in variants.items() if not v.get("diagnostic_only")
            for m in v.get("mutations", {})]
    assert any("acoustic_phase_correction" in m for m in muts)
    assert any("high_wavenumber_filter" in m for m in muts)


def test_runner_end_to_end_micro_contract(tmp_path):
    # micro matrix (diagnostic frequency, tiny rig): certifies the seven-file
    # run contract, gate-row structure and own-baseline normalization plumbing;
    # verdict NOT asserted (physics belongs to the authoritative gate run)
    cfg = load_config(G2O_CONFIG)
    micro = {
        "case": cfg["case"], "inheritance": cfg["inheritance"],
        "gates": cfg["gates"],
        "g2o_smoke": {**cfg["g2o_smoke"],
                      "variants": [{"id": "v0_frozen", "mutations": {}},
                                   {"id": "v1_acoustic_corr_off", "identity_expected": True,
                                    "mutations": {"collision.acoustic_phase_correction_enabled": False}},
                                   {"id": "v2_filter_off",
                                    "mutations": {"numerics.high_wavenumber_filter.enabled": False}}]},
        "g2o": cfg["g2o"],
    }
    micro_path = tmp_path / "g2o_micro.yaml"
    micro_path.write_text(yaml.safe_dump(micro, allow_unicode=True), encoding="utf-8")
    result = run_g2o(micro_path, output_root=tmp_path / "out", smoke=True, workers=1)
    out_dir = Path(result["out_dir"])
    for fname in ("config_resolved.yaml", "summary.json", "harmonic_fit.json",
                  "provenance.json", "gate_evaluation.json", "run_report.md",
                  "signals.h5"):
        assert (out_dir / fname).is_file(), fname
    summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["gate_status"] in {"PASSED", "FAILED", "SCOPED_CANDIDATE"}
    assert summary["smoke_mode"] is True
    assert summary["spectral_correction_enabled"] is True  # frozen stack untouched
    rows = result["gate_rows"]
    for row in ("single_tone_leakage", "dg_operator_sensitivity",
                "h2_operator_sensitivity", "stability", "attributability",
                "spectral_identity"):
        assert row in rows
    # S6 exercised end-to-end: identity rows present and exactly zero
    s6 = rows["spectral_identity"]
    assert s6["applicable"] and s6["rows"]
    assert all(r["max_abs_series_diff"] == 0.0 for r in s6["rows"].values())
    # own-baseline normalization plumbing: linear shift archived for the variant
    shifts = summary["results"]["baseline_linear_shifts"]["v2_filter_off"]
    assert any(v is not None for v in shifts.values())
