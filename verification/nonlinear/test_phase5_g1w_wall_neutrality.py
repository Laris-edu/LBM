"""G1-W contract tests (contract §6.1, Phase5 v1.2).

Certifies the G1-W runner machinery via one small ``--smoke`` run (diagnostic
frequency, small sealed rig) plus a closed-form anchor for the sealed spectral
reference builder:

- seven-file §16.1 run contract + §16.2 metadata completeness + three-state
  verdicts (D0-7);
- wall-discriminating non-degeneracy: the mass-neutral candidate passes the
  machine-level neutrality rows while the frozen ``pressure_preserving`` wall's
  mass source is measured orders above the gate and triggers the
  DIAGNOSTIC_ONLY marking (recovered, not asserted by construction);
- the lbm-equivalent sealed spectral reference reproduces the independent
  continuum closed form (tanh sealed solution with pressure feedback) when fed
  constant nominal transport — a non-tautological anchor of the reference
  builder (the G0-table physics enters only through measured rows).

The authoritative G1-W physics verdict is a gate run (Phase5_STATUS §3), not
asserted here.
"""

from __future__ import annotations

import cmath
import json
import math
from pathlib import Path

import numpy as np
import pytest

from scripts.phase5_g1w_wall_neutrality import (
    DEFAULT_CONFIG,
    run_g1w,
    sealed_spectral_reference,
)

SCHEMA_PATH = Path(__file__).resolve().parent / "phase5_gate_schema.json"


@pytest.fixture(scope="module")
def smoke_run(tmp_path_factory) -> dict:
    out_root = tmp_path_factory.mktemp("g1w_smoke")
    result = run_g1w(DEFAULT_CONFIG, out_root, smoke=True)
    out_dir = Path(result["out_dir"])
    with (out_dir / "summary.json").open(encoding="utf-8") as fh:
        summary = json.load(fh)
    with (out_dir / "gate_evaluation.json").open(encoding="utf-8") as fh:
        gate_eval = json.load(fh)
    return {"result": result, "out_dir": out_dir, "summary": summary,
            "gate_eval": gate_eval}


def test_seven_file_contract_and_metadata(smoke_run):
    with SCHEMA_PATH.open(encoding="utf-8") as fh:
        schema = json.load(fh)
    for name in schema["run_required_files"]:
        assert (smoke_run["out_dir"] / name).is_file(), f"missing {name}"
    summary = smoke_run["summary"]
    missing = [k for k in schema["run_metadata_required_keys"] if k not in summary]
    assert not missing, f"missing §16.2 keys: {missing}"
    missing_r = [k for k in schema["run_result_required_keys"] if k not in summary["results"]]
    assert not missing_r, f"missing §16.3 keys: {missing_r}"
    assert summary["gate_status"] in schema["gate_states"]["script_emittable"]
    assert summary["gate_id"] == "G1-W"
    assert summary["smoke_mode"] is True
    assert summary["boundary_mass_flux_definition"]  # normalization archived (§6.1)


def test_wall_discrimination_is_measured(smoke_run):
    rows = smoke_run["gate_eval"]["rows"]
    # production candidate: machine-level neutrality rows genuinely pass
    assert rows["normal_mass_flux_components"]["passed"]
    assert rows["normal_mass_flux_components"]["value_max_0f_3f"] <= 1.0e-10
    assert rows["normal_mass_flux_components"]["value_max_0f_3f"] > 0.0  # measured
    assert rows["global_mass"]["passed"]
    assert rows["impermeability_no_slip"]["passed"]
    assert rows["wall_temperature_realization"]["passed"]
    assert rows["wall_temperature_realization"]["max_error_K"] <= 0.01
    assert rows["numerical_discipline"]["passed"]
    # frozen wall: mass source measured orders above the gate -> DIAGNOSTIC_ONLY
    audit = rows["old_wall_difference_audit"]
    assert audit["old_wall_marking"] == "DIAGNOSTIC_ONLY"
    flux = audit["table"]["mass_flux_1f"]
    assert flux["old"] > 1.0e3 * flux["mn"]  # discrimination is real, not narrative
    assert flux["old"] > 1.0e-10
    # regression row carries the reference band + both errors
    reg = rows["admittance_regression"]
    assert np.isfinite(reg["amp_rel_err"]) and np.isfinite(reg["phase_deg_err"])
    assert len(reg["policy_band"]) == 4
    # fixture rows measured on both signals
    fx = rows["boundary_linear_interior_fixture"]["odd_pair_nontarget"]
    for sig in ("q_moment_si", "p_box_lu"):
        assert fx[sig]["odd_2f_rel"] > 0.0 and np.isfinite(fx[sig]["odd_2f_rel"])


def test_sealed_reference_matches_independent_closed_form():
    # constant nominal transport: the spectral builder must reproduce the
    # continuum sealed closed form (tanh profile + uniform-pressure feedback)
    alpha = 0.006384727
    omega = 1.230757e-4
    n = 48
    ref = sealed_spectral_reference(
        n, omega, alpha, np.array([0.01, 4.0]), np.array([alpha, alpha]),
        highk_policy="hold_last", gamma=1.4)
    y_spec = ref["Y_over_Yhs"]

    m = cmath.sqrt(1j * omega / alpha)
    L = n / 2.0
    tanh_ml = cmath.tanh(m * L)
    tau_l = tanh_ml / (m * L)
    beta = (1.4 - 1.0) / 1.4
    t_mean = tau_l / (1.0 - beta * (1.0 - tau_l))          # <T>/T_w
    y_closed = tanh_ml * (1.0 - beta * t_mean)              # (km(T_w-T_p)tanh)/ (km T_w)
    rel = y_spec / y_closed
    assert abs(rel) - 1.0 == pytest.approx(0.0, abs=0.03)   # point-pin/discrete-mode level
    assert math.degrees(cmath.phase(rel)) == pytest.approx(0.0, abs=1.5)
    # and the profile is a genuine near-wall layer decaying onto the sealed
    # pressure-feedback floor (T_p != 0): pinned at the wall, ~0.4x by midplane
    prof = ref["profile_over_Tw"]
    assert abs(prof[0]) == pytest.approx(1.0, rel=1e-9)     # pin at the wall row
    assert abs(prof[6]) < 0.75 * abs(prof[1])
    assert abs(prof[24]) < 0.5 * abs(prof[1])               # midplane

def test_alpha_extension_rows_archived(smoke_run):
    prov = json.loads((smoke_run["out_dir"] / "provenance.json").read_text(encoding="utf-8"))
    rows = prov["alpha_extension_rows"]
    assert len(rows) >= 2
    for r in rows:
        assert r["finite"] and r["alpha_eff_lu"] > 0.0
    # the measured high-k recovery (the Stage-1 attribution driver) is present
    assert max(r["ratio_vs_nominal"] for r in rows) > 2.0
