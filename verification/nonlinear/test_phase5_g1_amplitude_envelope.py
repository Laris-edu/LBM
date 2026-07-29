"""G1a contract tests (contract §6.2, Phase5 v1.2).

Certifies the G1a runner machinery via one diagnostic-frequency ``--smoke``
run (module fixture, ~3 min): the seven-file run contract, §16.2/§16.3 field
completeness, and the non-degeneracy of the gate logic — the smoke's small
rig at 200 kHz is DESIGNED to fail the two fidelity-limited rows (small-
amplitude regression phase, domain-refinement D_G difference) while every
machine-level row (mass, wall temperature, finiteness, energy-audit drift,
window sensitivity) passes, so the script demonstrably refuses PASSED at
non-authoritative fidelity. The refinement row's gate is asserted to be
independent of the refinement difference itself (the self-satisfying-gate
bug caught during smoke calibration).

G1b rows will extend this module when the Level C coupled envelope lands.
No Phase_5 gate status is claimed here (authoritative run: STATUS §3).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scripts.phase5_g1a_amplitude_envelope import DEFAULT_CONFIG, run_g1a

SCHEMA_PATH = Path(__file__).resolve().parent / "phase5_gate_schema.json"


@pytest.fixture(scope="module")
def smoke_run(tmp_path_factory) -> dict:
    out_root = tmp_path_factory.mktemp("g1a_smoke")
    # workers=4: scheduling-layer parallelism only; serial/parallel bitwise
    # identity is verified by the archived A/B check (2026-07-28)
    result = run_g1a(DEFAULT_CONFIG, out_root, smoke=True, workers=4)
    out_dir = Path(result["out_dir"])
    with (out_dir / "summary.json").open(encoding="utf-8") as fh:
        summary = json.load(fh)
    with (out_dir / "gate_evaluation.json").open(encoding="utf-8") as fh:
        gate_eval = json.load(fh)
    return {"result": result, "out_dir": out_dir, "summary": summary,
            "gate_eval": gate_eval}


def test_seven_file_contract_and_fields(smoke_run):
    with SCHEMA_PATH.open(encoding="utf-8") as fh:
        schema = json.load(fh)
    for name in schema["run_required_files"]:
        assert (smoke_run["out_dir"] / name).is_file(), f"missing {name}"
    summary = smoke_run["summary"]
    missing = [k for k in schema["run_metadata_required_keys"] if k not in summary]
    assert not missing, f"missing §16.2 keys: {missing}"
    missing_r = [k for k in schema["run_result_required_keys"]
                 if k not in summary["results"]]
    assert not missing_r, f"missing §16.3 keys: {missing_r}"
    assert summary["gate_status"] in schema["gate_states"]["script_emittable"]
    assert summary["gate_id"] == "G1a"
    assert summary["smoke_mode"] is True
    assert "G1-W" in summary["wall_neutrality_gate_id"]  # certified-wall linkage


def test_machine_rows_pass_and_fidelity_rows_have_teeth(smoke_run):
    rows = smoke_run["gate_eval"]["rows"]
    # machine-level physics must pass even at diagnostic fidelity
    for name in ("wall_temperature", "global_mass", "finiteness",
                 "numerical_repair", "window_sensitivity",
                 "energy_audit_two_channel_drift", "minimum_amplitude_window"):
        assert rows[name]["passed"], f"row {name} unexpectedly failed"
    assert rows["wall_temperature"]["max_err_K"] <= 1.0e-9
    assert rows["global_mass"]["window_max"] <= 1.0e-10
    # two-channel drift: zero at eps_min BY CONSTRUCTION, measured >0 elsewhere
    drift = rows["energy_audit_two_channel_drift"]["drift_by_eps"]
    vals = [drift[k] for k in sorted(drift)]
    assert min(vals) == 0.0 and max(vals) > 0.0
    # fidelity-limited rows must FAIL at smoke -> script refuses PASSED
    assert rows["smallamp_regression"]["passed"] is False
    assert rows["diagnostic_refinement"]["passed"] is False
    assert smoke_run["result"]["verdict"] == "FAILED"
    # refinement gate must be independent of the refinement diff itself
    dom = rows["diagnostic_refinement"]["domain_axis"]
    assert dom["gate"] < dom["D_G_diff"]  # not self-satisfying
    assert dom["gate"] == pytest.approx(0.01, abs=1e-12)


def test_envelope_semantics_measured(smoke_run):
    per_eps = smoke_run["result"]["per_eps"]
    eps_sorted = sorted(per_eps, key=float)
    h2 = [per_eps[e]["H2_q"] for e in eps_sorted]
    # genuine nonlinearity: H2 grows with epsilon (measured, not copied)
    assert h2 == sorted(h2) and h2[-1] > 2.0 * h2[0] > 0.0
    # per-eps pass table present and boolean
    assert all(isinstance(per_eps[e]["passed"], bool) for e in eps_sorted)
    res = smoke_run["summary"]["results"]
    assert res["outgoing_mode_1f"] is None  # sealed rig honesty
    assert res["wall_boundary_sensitivity"]["moment_channel_recalibration_c_eps_min"]["abs"] > 0
