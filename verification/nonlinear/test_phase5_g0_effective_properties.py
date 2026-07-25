"""G0-B effective-property machinery tests (contract §5 deliverable, WP2).

Mechanism-level certification of the G0 measurement chain: background-state
construction on the frozen mapping, background-temperature sensitivity of the
measured effective diffusivity (the non-degeneracy that makes G0 worth
running), and the runner's end-to-end file/gate contract on a micro matrix.
The authoritative G0 run (full temperature x wavenumber matrix on the dx2p6
production mapping) is recorded in Phase5_STATUS §3 with its digest; its
verdict is NOT asserted here (physics belongs to the gate, not the test).
P2-4/5/6 regression tests certify that the helper extensions leave the
Phase_2 default paths byte-identical.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scripts.phase2_m2_verification import load_config
from scripts.phase5_g0_effective_properties import run_g0
from verification.thermal_diffusion_measurement import (
    ThermalDiffusionSettings,
    _background_state,
    measure_thermal_diffusion_direction,
)

GAS_CONFIG = Path("configs/gas_air_10k_d2q37_physical_timestep.yaml")


class _MappingStub:
    theta_ref_lu = 0.6

    class lattice:  # noqa: N801 - mimic mapping.lattice attribute access
        rho_ref_lu = 1.0


def test_background_state_construction_and_validation():
    stub = _MappingStub()
    s_iso = ThermalDiffusionSettings(background_theta_lu=0.66, background_path="isobaric")
    theta_b, rho_b = _background_state(stub, s_iso)
    assert theta_b == pytest.approx(0.66)
    assert rho_b * theta_b == pytest.approx(1.0 * 0.6)  # p_b == p_ref exactly
    s_ed = ThermalDiffusionSettings(background_theta_lu=0.66, background_path="equal_density")
    _, rho_ed = _background_state(stub, s_ed)
    assert rho_ed == pytest.approx(1.0)
    s_def = ThermalDiffusionSettings()
    theta_d, rho_d = _background_state(stub, s_def)
    assert theta_d == pytest.approx(0.6) and rho_d == pytest.approx(1.0)
    with pytest.raises(ValueError):
        _background_state(stub, ThermalDiffusionSettings(background_theta_lu=-1.0))
    with pytest.raises(ValueError):
        _background_state(stub, ThermalDiffusionSettings(background_path="isochoric"))


def test_background_temperature_sensitivity_is_measurable():
    # the whole point of G0: the frozen-mapping effective diffusivity must move
    # with the background temperature (measured ~ +20% at 1.1*theta on dx2p6);
    # a flat response would mean the instrument cannot see the effective law
    gas = load_config(GAS_CONFIG)
    base = dict(nx=4, ny=48, steps=3000, sample_interval=8, fit_start=300, amplitude=1.0e-5)
    ref = measure_thermal_diffusion_direction(gas, "y", ThermalDiffusionSettings(**base))
    theta_ref = ref["background_theta_lu"]  # actual mapping reference, not hardcoded
    hot = measure_thermal_diffusion_direction(
        gas, "y",
        ThermalDiffusionSettings(background_theta_lu=1.1 * theta_ref, **base),
    )
    assert not ref["nan_detected"] and not hot["nan_detected"]
    assert hot["background_theta_lu"] == pytest.approx(1.1 * theta_ref)
    ratio = hot["alpha_measured_lu"] / ref["alpha_measured_lu"]
    assert ratio > 1.05  # temperature dependence clearly resolved
    # isobaric background: pressure stays at the reference value
    assert hot["background_rho_lu"] * hot["background_theta_lu"] == pytest.approx(
        ref["background_rho_lu"] * theta_ref
    )


def test_g0_runner_micro_matrix_end_to_end(tmp_path):
    config = f"""
case: {{name: g0_micro_test, phase: Phase_5, gate: G0-B, work_package: WP2}}
inheritance:
  gas_config_path: {GAS_CONFIG.as_posix()}
  phase5_contract: docs/Phase_5/Phase5_instruct_v1.2.md
  model_route: ROUTE_B_MAIN
g0:
  temperatures_K: [300.0, 330.0]
  equal_density_diagnostic: {{temperatures_K: [330.0], wavenumbers: [kA]}}
  wavenumbers:
    - {{label: klowA, ny: 48, mode: 1, layer: low}}
    - {{label: klowB, ny: 64, mode: 1, layer: low}}
    - {{label: kA, ny: 32, mode: 1, layer: production}}
  acoustic_wavenumbers: [kA]
  nx: 4
  amplitudes: {{thermal: 1.0e-5, shear: 1.0e-5, acoustic: 1.0e-6}}
  steps_policy: {{diffusive_decay_fraction: 0.05, diffusive_min: 1200, diffusive_max: 2400,
                 acoustic_periods: 8, acoustic_min: 1200, acoustic_max: 2400}}
  window_consistency: {{temperature_K: 300.0, wavenumber: kA, fit_start_factors: [0.125, 0.25]}}
gates:
  regression_300K_transport_rel: 0.05
  regression_300K_acoustic_rel: 0.02
  window_consistency_rel: 0.02
  lowk_convergence_rel: 0.02
output: {{results_root: {tmp_path.as_posix()}/results}}
"""
    config_path = tmp_path / "g0_micro.yaml"
    config_path.write_text(config, encoding="utf-8")
    result = run_g0(config_path, tmp_path / "out")

    assert result["verdict"] in {"PASSED", "FAILED", "SCOPED_CANDIDATE"}  # script-emittable enum only
    out_dir = Path(result["out_dir"])
    for name in ("summary.json", "property_table.csv", "gate_evaluation.json", "run_report.md"):
        assert (out_dir / name).exists()
    summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    for key in ("run_id", "code_commit", "phase5_contract_version", "gate_id", "model_route",
                "config_digest", "gas_config_digest", "property_table_digest", "gate_status",
                "no_clipping", "no_floor", "no_positivity_repair"):
        assert key in summary
    assert summary["gate_id"] == "G0-B"
    gate_eval = json.loads((out_dir / "gate_evaluation.json").read_text(encoding="utf-8"))
    for row in ("regression_300K_alpha_at_calibration_k", "regression_300K_nu_at_calibration_k",
                "regression_300K_c_at_calibration_k", "window_consistency",
                "lowk_convergence", "paths_archived", "numerical_discipline"):
        assert row in gate_eval["rows"]
    assert "scoped_limitations" in summary
    # matrix bookkeeping: 2T x 3k isobaric + 1 equal-density + 2 window rows
    rows = result["rows"]
    assert len(rows) == 2 * 3 + 1 + 2
    # non-degeneracy at matrix level: alpha_eff moves with T on every wavenumber
    for label in ("klowA", "klowB", "kA"):
        a300 = next(r for r in rows if r["T_K"] == 300.0 and r["k_label"] == label and r["tag"] == "")
        a330 = next(r for r in rows if r["T_K"] == 330.0 and r["k_label"] == label and r["tag"] == "")
        assert a330["alpha_eff_lu"] / a300["alpha_eff_lu"] > 1.02
    # equal-density diagnostic: density stays at the reference value while the
    # background temperature is raised (contrast with the isobaric 330 K row)
    ed_row = next(r for r in rows if r["background_path"] == "equal_density")
    ref_rho = next(r for r in rows if r["T_K"] == 300.0 and r["tag"] == "")["rho_b_lu"]
    iso330_rho = next(
        r for r in rows if r["T_K"] == 330.0 and r["tag"] == "" and r["background_path"] == "isobaric"
    )["rho_b_lu"]
    assert ed_row["rho_b_lu"] == pytest.approx(ref_rho, rel=1e-12)
    assert iso330_rho < ref_rho  # isobaric background thins with heating
    assert ed_row["theta_b_lu"] > next(r for r in rows if r["T_K"] == 300.0)["theta_b_lu"]
