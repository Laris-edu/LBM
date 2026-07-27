"""G3 contract tests (contract §8, Phase5 v1.2).

Certifies the G3 runner machinery — the contract seven-file run set, §16.2/
§16.3 field completeness against the machine-readable gate schema, the frozen
formal property-branch definitions, and the non-degeneracy of the gate logic
— via one toy-scaled ``--smoke`` run (module fixture, ~1 min).

Deliberate non-degeneracy design: the smoke protocol uses a coarse grid
ladder (cells/delta 2-4-8), so the grid-convergence row measures a clean
observed order ~2 while its finest-two 1% row FAILS — asserting that the
script refuses to hand out PASSED at coarse settings proves the gate has
teeth (recovered-not-input discipline). The authoritative production run
(ladder 6-12-24, real air) is a separate WP2 event; no Phase_5 gate status
is claimed by this test suite.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from reference.constants import default_params
from reference.nonlinear_nsf_1d import (
    G0_MEASURED_K_EXPONENT,
    G0_MEASURED_MU_EXPONENT,
    G0_MEASURED_PROPERTY_MODEL_ID,
    g0_measured_transport,
    lbm_equivalent_transport,
    physical_air_transport,
)
from scripts.phase5_g3_nsf1d_reference import GATES, run_g3

SCHEMA_PATH = Path(__file__).resolve().parent / "phase5_gate_schema.json"


@pytest.fixture(scope="module")
def smoke_run(tmp_path_factory) -> dict:
    out_root = tmp_path_factory.mktemp("g3_smoke")
    result = run_g3(out_root, smoke=True)
    out_dir = Path(result["out_dir"])
    with (out_dir / "summary.json").open(encoding="utf-8") as fh:
        summary = json.load(fh)
    with (out_dir / "gate_evaluation.json").open(encoding="utf-8") as fh:
        gate_eval = json.load(fh)
    with (out_dir / "harmonic_fit.json").open(encoding="utf-8") as fh:
        harmonic = json.load(fh)
    return {"result": result, "out_dir": out_dir, "summary": summary,
            "gate_eval": gate_eval, "harmonic": harmonic}


def test_seven_file_run_contract(smoke_run):
    with SCHEMA_PATH.open(encoding="utf-8") as fh:
        schema = json.load(fh)
    for name in schema["run_required_files"]:
        assert (smoke_run["out_dir"] / name).is_file(), f"missing contract file {name}"


def test_metadata_and_result_fields_complete(smoke_run):
    with SCHEMA_PATH.open(encoding="utf-8") as fh:
        schema = json.load(fh)
    summary = smoke_run["summary"]
    missing = [k for k in schema["run_metadata_required_keys"] if k not in summary]
    assert not missing, f"missing §16.2 metadata keys: {missing}"
    results = summary["results"]
    missing_r = [k for k in schema["run_result_required_keys"] if k not in results]
    assert not missing_r, f"missing §16.3 result keys: {missing_r}"
    # script-emittable verdicts only (D0-7)
    assert summary["gate_status"] in schema["gate_states"]["script_emittable"]
    assert summary["gate_id"] == "G3"
    assert summary["smoke_mode"] is True
    assert summary["no_clipping"] and summary["no_floor"] and summary["no_positivity_repair"]


def test_gate_logic_nondegenerate_at_coarse_smoke(smoke_run):
    rows = smoke_run["gate_eval"]["rows"]
    # rows that must pass even at toy-smoke fidelity (machine-level physics)
    assert rows["equilibrium_preservation"]["passed"]
    assert 0.0 <= rows["equilibrium_preservation"]["value"] < 1.0e-10
    assert rows["total_energy_residual"]["passed"]
    assert rows["total_energy_residual"]["value"] <= 1.0e-8  # measured ~1e-10
    assert rows["numerical_discipline"]["passed"]
    # leakage fixture: numerical floor AND physical-2f sensitivity counter-check
    leak = rows["linearization_leakage"]
    assert leak["passed"]
    for br in ("g0", "phys"):
        assert leak["by_branch"][br]["max_even_in_odd"] <= GATES["leakage_max"]
        assert (leak["by_branch"][br]["physical_2f_sensitivity"]
                >= GATES["leakage_sensitivity_min"])
    # low-Mach row: ringdown damping within the physical window, resolvability high
    lm = rows["low_mach_resolvability"]
    assert lm["passed"]
    assert 0.85 <= lm["ringdown_gamma_ratio"] <= 1.5
    # non-degeneracy: the coarse smoke ladder measures a real ~2nd order but
    # must FAIL the finest-two 1% row — the script does not hand out PASSED
    conv = rows["grid_convergence"]
    for br in ("g0", "phys"):
        order = conv["by_branch"][br]["observed_order"]
        assert np.isfinite(order) and 1.5 <= order <= 3.0
        assert conv["by_branch"][br]["finest_two_rel_diff"] > 0.0  # measured, not copied
    assert conv["passed"] is False
    assert smoke_run["result"]["verdict"] == "FAILED"
    # anchors are genuinely grid-sensitive (recovered, not input)
    ladder = smoke_run["result"]["ladder"]["g0"]
    assert ladder["coarse_pair_diff"] > ladder["fine_pair_diff"] > 0.0


def test_formal_branch_definitions_frozen(smoke_run):
    params = default_params()
    g0 = g0_measured_transport(params)
    phys = physical_air_transport(params)
    const = lbm_equivalent_transport(params)
    # G0-measured law frozen from the authoritative G0 run (model-freeze §1/§3)
    assert G0_MEASURED_K_EXPONENT == pytest.approx(1.04)
    assert G0_MEASURED_MU_EXPONENT == pytest.approx(-0.60)
    assert g0.property_model_id == G0_MEASURED_PROPERTY_MODEL_ID
    assert g0.property_model_id == "1D-lbm-equivalent_g0_measured_k1_v1"
    # all branches anchored at the frozen reference state (linear degeneracy)
    for tr in (g0, phys, const):
        assert float(tr.mu(params.T0)) == pytest.approx(params.mu, rel=1e-14)
        assert float(tr.k(params.T0)) == pytest.approx(params.kg, rel=1e-14)
    # the law is genuinely temperature-dependent with the frozen exponents
    assert float(g0.k(330.0)) / params.kg == pytest.approx((330.0 / 300.0) ** 1.04, rel=1e-12)
    assert float(g0.mu(330.0)) / params.mu == pytest.approx((330.0 / 300.0) ** -0.60, rel=1e-12)
    ids = {g0.property_model_id, phys.property_model_id, const.property_model_id}
    assert len(ids) == 3
    # run metadata carries the formal mapping
    pm = smoke_run["summary"]["property_model_id"]
    assert pm["1D-lbm-equivalent"] == g0.property_model_id
    assert pm["1D-physical"] == phys.property_model_id
    assert pm["diagnostic_lineage"] == const.property_model_id


def test_harmonic_payloads_and_review_blocks(smoke_run):
    harmonic = smoke_run["harmonic"]
    assert "anchor_g0_q" in harmonic
    for payload in harmonic.values():
        assert "exp(+i n Omega t)" in payload["phase_convention"]
        assert np.isfinite(payload["harmonic_fit_condition_number"])
        assert payload["detrend_order"] == 0  # §12.2 pre-registration
    review = smoke_run["gate_eval"]["review_blocks"]["p_side_dual_property_ablation"]
    table = review["table"]
    assert len(table) >= 1
    row = table[0]
    for br in ("const", "g0", "phys"):
        assert row[br]["H2_p_side"] > 0.0
        assert row[br]["H2_T_side"] > 0.0
    # branches measurably distinct on the p-side second harmonic at eps=0.05
    h2 = {br: row[br]["H2_p_side"] for br in ("const", "g0", "phys")}
    assert len({round(v, 12) for v in h2.values()}) == 3
    assert "dab2_pside" in row and row["dab2_pside"]["phys_over_g0"] > 0.0
