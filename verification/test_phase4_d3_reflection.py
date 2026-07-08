"""P4-D3 D3-2 gate: the simplified-collision acoustic domain reaches |R|<0.05 non-degenerately.

Project: docs/Phase_4/M4/P4_D3_Multidomain_Acoustic_Project.md (D3-2; sections 7/8/9).

Section 7 left D3-2 open: a sponge read |R|~0.0015 but could not be certified non-degenerate,
because the decisive rigid-lid control (|R|~1) crashed on the heat-flux Gram. The core step
(acoustic_simplified_collision) removed that Gram, so the control now runs. This test closes the
certification with pulse characteristic reflectometry (|R| = peak|w-|/peak|w+| at a probe row) and
the three controls that make it non-degenerate:

  * rigid-lid control reflects strongly (|R| >> gate) -> the rig CAN see reflection through the same
    probe path, so a small sponge |R| is real absorption, NOT the strong filter dissipating the
    reflected wave before the probe (the section-7 degeneracy worry, here refuted);
  * the production sponge sits far below the 0.05 gate;
  * |R| responds monotonically to sponge thickness -> the rig reads absorption strength, not a fixed
    floor (section 7's insensitivity red flag, here resolved).

Fast height (ny=256); the certified 5-wavelength height ny=512 gives the same result (rigid 1.26,
production sponge 0.0004, thin 0.066). The pulse |R| is representative of the 10 kHz gate because the
acoustic medium is dispersion-free (|R| is frequency-independent)."""

from __future__ import annotations

from pathlib import Path

from scripts.phase2_m2_verification import load_config
from scripts.phase4_d3_reflection_probe import run_reflection

ACOUSTIC_CONFIG = Path("configs/phase4_acoustic_coarse_dx334.yaml")
NY = 256


def test_rigid_lid_control_sees_reflection():
    """Non-degeneracy: a fully-reflecting rigid lid reads |R| = O(1) through the same probe path,
    so the strong filter does NOT dissipate the reflected wave before the probe."""

    r = run_reflection(load_config(ACOUSTIC_CONFIG), ny=NY, top="rigid")
    assert r["crash_step"] is None                # the control runs (unlocked by the core step)
    assert r["R_abs"] > 0.5                        # the rig clearly sees reflection


def test_periodic_floor_below_gate():
    """A periodic (no-boundary) top leaves only the medium backscatter floor, below the gate."""

    r = run_reflection(load_config(ACOUSTIC_CONFIG), ny=NY, top="periodic")
    assert r["R_abs"] is not None and r["R_abs"] < 0.05


def test_production_sponge_below_gate_and_responsive():
    """D3-2 gate: the production (thick) sponge reflects below 0.05; and a thin sponge reflects
    clearly more (monotone thickness response) -> the reflectometer reads absorption, not a floor."""

    cfg = load_config(ACOUSTIC_CONFIG)
    thick = run_reflection(cfg, ny=NY, top="sponge", n_sponge=80, sigma_max=0.5)
    thin = run_reflection(cfg, ny=NY, top="sponge", n_sponge=4, sigma_max=0.5)
    assert thick["crash_step"] is None and thin["crash_step"] is None
    assert thick["R_abs"] < 0.05                   # D3-2 gate met (production sponge)
    assert thin["R_abs"] > 3.0 * thick["R_abs"]    # rig responds to absorption strength (non-degenerate)
