"""P4-D3 D3-3 (one-way reframe) gate: non-reflecting soft-source injection into the coarse domain.

Project: docs/Phase_4/M4/P4_D3_Multidomain_Acoustic_Project.md (D3-3; section 11).

The two-way population-exchange interface reflects ~0.5 (section 10). The one-way reframe (user
decision) drives the coarse acoustic domain from the near-field ONE-WAY through a non-reflecting
soft-source injection at the coarse bottom. This certifies the two gates non-degenerately:

  * the injected monochromatic wave is clean upward (one-wayness w-/w+ < 0.05);
  * a downward test pulse at the injection boundary reflects below the gate (|R| < 0.05), with a
    rigid-bottom control reading O(1) (the rig sees reflection -> the sponge reading is real).

Fast height (ny=256); ny=512 gives the same (injection one-wayness 0.009, sponge 0.001, rigid 0.80).
Amplitude calibration (radiated vs driven) is deferred to D3-4."""

from __future__ import annotations

from pathlib import Path

from scripts.phase2_m2_verification import load_config
from scripts.phase4_d3_oneway_probe import run_injection, run_bottom_reflection

ACOUSTIC_CONFIG = Path("configs/phase4_acoustic_coarse_dx334.yaml")
NY = 256
N_ABS = 40
Y_S = 60


def test_injection_is_clean_upward():
    """The soft-source injects a clean upward wave: the downward invariant w- stays << w+."""

    r = run_injection(load_config(ACOUSTIC_CONFIG), ny=NY, n_abs=N_ABS, y_s=Y_S, n_periods=8)
    assert not r.get("crash")
    assert r["onewayness"] < 0.05


def test_injection_boundary_nonreflecting_and_nondegenerate():
    """A downward test pulse: the injection boundary (sponge) reflects below the gate, and a rigid
    bottom control reflects O(1) -> the rig sees reflection, so the sponge reading is not degenerate."""

    cfg = load_config(ACOUSTIC_CONFIG)
    rigid = run_bottom_reflection(cfg, ny=NY, n_abs=N_ABS, bottom="rigid")
    sponge = run_bottom_reflection(cfg, ny=NY, n_abs=N_ABS, bottom="sponge")
    assert rigid["crash_step"] is None and sponge["crash_step"] is None
    assert rigid["R_abs"] > 0.3        # non-degeneracy: the rig sees reflection
    assert sponge["R_abs"] < 0.05      # the injection boundary is non-reflecting
