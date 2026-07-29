"""G1b contract tests (contract §6.3, Phase5 v1.2).

Certifies the G1b runner machinery via one diagnostic-frequency smoke
(module fixture, ~2 min, pooled): seven-file run contract, §16.2/§16.3
completeness, the coupled-instrument row design, and non-degeneracy — the
smoke MUST fail exactly where its fidelity is limited:

- the epsilon-targeting row uses the pre-registered PRODUCTION §23 recal
  constant (3.055@+17.54deg, measured on the production rig), which is wrong
  for the smoke rig by construction — the measured in-run recal (~4.6@+35deg
  at the diagnostic frequency) must differ from it and the targeting row must
  FAIL, proving the row measures rather than assumes;
- the gated regression row (coupled energy-channel admittance vs the sealed
  spectral reference — the quantity in which the moment-channel
  miscalibration cancels exactly) must already be amplitude-clean (few %) at
  smoke fidelity while the phase carries the known smoke-grade reference
  mismatch, and machine-level rows (film audit, mass, stability, finiteness)
  must pass outright.

The energy-balance time-domain feedback instability (self-excitation through
box modes, measured growth ~25x in the first smoke) is frozen as DIAGNOSTIC
ONLY in the conjugate docstring; this suite pins the enum validation. No
Phase_5 gate status is claimed here.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from coupling.conjugate import run_levelc_predictor_corrector
from scripts.phase5_g1b_levelc_amplitude import DEFAULT_CONFIG, run_g1b

SCHEMA_PATH = Path(__file__).resolve().parent / "phase5_gate_schema.json"


@pytest.fixture(scope="module")
def smoke_run(tmp_path_factory) -> dict:
    out_root = tmp_path_factory.mktemp("g1b_smoke")
    result = run_g1b(DEFAULT_CONFIG, out_root, smoke=True, workers=2)
    out_dir = Path(result["out_dir"])
    payload = {"result": result, "out_dir": out_dir}
    for name in ("summary", "gate_evaluation", "harmonic_fit", "provenance"):
        with (out_dir / f"{name}.json").open(encoding="utf-8") as fh:
            payload[name] = json.load(fh)
    return payload


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
    assert summary["gate_id"] == "G1b"
    assert summary["smoke_mode"] is True
    assert summary["q_feedback_relax"] == pytest.approx(0.02)


def test_machine_level_rows_pass_and_fidelity_rows_fail(smoke_run):
    rows = smoke_run["gate_evaluation"]["rows"]
    # machine-level physics must hold even at smoke fidelity
    assert rows["film_energy_audit"]["passed"]
    assert max(rows["film_energy_audit"]["by_eps"].values()) <= 1.0e-10
    assert rows["global_mass"]["passed"]
    assert rows["coupling_stability"]["passed"]
    for growth in rows["coupling_stability"]["delta_pc_growth_by_eps"].values():
        assert (not np.isfinite(growth)) or growth <= 1.5  # measured ~0.01
    # wall row FAILS at smoke by timing geometry (omega 20x production pushes
    # the end-of-step error over the raw 0.01 K gate), while the timing RATIO
    # proves it is sampling geometry, not wall failure (measured ~0.80,
    # amplitude-invariant to ~2% across 5x epsilon)
    wall = rows["wall_temperature"]
    assert wall["passed"] is False
    ratios = list(wall["timing_ratio_by_eps"].values())
    for ratio in ratios:
        assert 0.6 <= ratio <= 1.0
    assert abs(ratios[0] / ratios[1] - 1.0) < 0.1  # proportionality law
    # non-degeneracy: production §23 recal constant is WRONG for the smoke rig
    # by construction -> targeting row must FAIL (the row measures, not assumes)
    assert rows["target_epsilon"]["passed"] is False
    assert max(abs(v) for v in rows["target_epsilon"]["by_eps"].values()) > 0.2
    assert smoke_run["result"]["verdict"] == "FAILED"
    assert "LEVELC_NONLINEAR_COUPLING_NOT_CERTIFIED" in smoke_run["result"]["labels"]


def test_energy_channel_cancellation_and_inrun_recal(smoke_run):
    rows = smoke_run["gate_evaluation"]["rows"]
    reg = rows["m3_smallamp_regression"]
    # the gated quantity (energy channel vs spectral ref) is amplitude-clean at
    # smoke fidelity — the moment miscalibration (x4.6 on this rig) cancelled
    assert abs(reg["ratio"]["amp_rel_err"]) < 0.15
    # in-run recal is a genuine measurement: finite, far from 1, and NOT equal
    # to the configured production constant (rig-dependent, recovered not input)
    rc = reg["recal_inrun_vs_g1w_constant"]
    assert np.isfinite(rc["amp_rel_err"]) and abs(rc["amp_rel_err"]) > 0.2
    per = smoke_run["gate_evaluation"]["per_epsilon"]
    h2 = {k: v["H2_Ts"] for k, v in per.items()}
    eps_sorted = sorted(h2, key=float)
    assert h2[eps_sorted[-1]] > h2[eps_sorted[0]] > 0.0  # genuine nonlinearity


def test_conjugate_enum_validation():
    with pytest.raises(ValueError, match="q_extraction"):
        run_levelc_predictor_corrector(
            solver=None, params=None, drive=1.0, n_steps=1,
            q_extraction="derivative_feedback")
    with pytest.raises(ValueError, match="wall_bc"):
        run_levelc_predictor_corrector(
            solver=None, params=None, drive=1.0, n_steps=1,
            wall_bc="mass_neutral_v2")
