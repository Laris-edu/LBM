"""P4-5 gate E2: M4 end-to-end far field on the D3 one-way architecture (contract section 10).

Runs the frozen chain of scripts/phase4_m4_endtoend.py -- M3 canonical T_s_hat (digest
26be2fde) -> compact-source map -> G-precompensated injection -> calibrated coarse domain ->
control surface -> K0 Kirchhoff -> far field -- and asserts the contract gates against the R1
compact-thermophone plane-wave reference:

  * E2 amplitude error < 10% (hard gate 4; measured 2.3%, aperture-truncation dominated);
  * far-field phase error < 10 deg (suggested gate; measured 1.2 deg);
  * R2 control-surface-location sensitivity < 5% (suggested gate; measured 0.2%);
  * dp/dn two-channel difference < 10% (contract section 6; measured 0.4%);
  * the frozen G reproduces the physical handoff blind (amp within 5%; measured 1.2%).

Nothing is tuned in-run: T_s_hat, the map, G, the medium calibration and the kernel are all
frozen upstream (sections 12.1-12.4). M4 gate wording stays PASSED_WITH_SCOPED_RISK (see
docs/Phase_4/M4/M4_Verification_Report.md); this test binds the E2 numbers only."""

from __future__ import annotations

from pathlib import Path

from scripts.phase2_m2_verification import load_config
from scripts.phase4_m4_endtoend import evaluate_m4_gates, run_m4_endtoend

ACOUSTIC_CONFIG = Path("configs/phase4_acoustic_coarse_dx334.yaml")


def test_e2_end_to_end_farfield_gates():
    r = run_m4_endtoend(load_config(ACOUSTIC_CONFIG))
    assert not r.get("crash")
    g = r["gates"]
    assert g["E2_amp_rel_err_max"] < 0.10            # contract hard gate 4
    assert g["E2_phase_err_deg_max"] < 10.0          # suggested phase gate
    assert g["R2_control_surface_sensitivity"] < 0.05
    assert abs(g["channel_diff_amp_primary"]) < 0.10  # contract section 6 threshold
    assert abs(g["channel_diff_phase_deg_primary"]) < 10.0
    assert evaluate_m4_gates(g)
    assert abs(r["handoff_plane"]["amp_rel_err"]) < 0.05   # frozen G applied blind
    primary_observers = [item["observer_y_m"] for item in r["control_surface"]["primary"]["farfield"]]
    check_observers = [item["observer_y_m"] for item in r["control_surface"]["check"]["farfield"]]
    assert primary_observers == check_observers


def test_e2_gate_rejects_channel_phase_failure():
    gates = {
        "E2_amp_rel_err_max": 0.01,
        "E2_phase_err_deg_max": 1.0,
        "R2_control_surface_sensitivity": 0.01,
        "channel_diff_amp_primary": 0.01,
        "channel_diff_phase_deg_primary": 11.0,
    }
    assert not evaluate_m4_gates(gates)
