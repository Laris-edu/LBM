"""WP3 first-round units machinery tests (contract §14/§15.1/§15.2 deliverable).

Mechanism-level certification of the A1 (P-LIN/P-AC1/P-AC2/P-AC3) and P-DC2
production runners: signed-pair separation algebra (odd isolates linear
content INCLUDING transients, even isolates 2f killing them — quantitative
with cross-contamination floors), the cold-instrument accounting constants
(c_row exact, G_inst ~ 0 for the certified mn wall), and the pre-registration
config freezes (ladder truncation at the G1a authorization boundary, G1-W
protocol constants verbatim, P-DC2 contract-frozen state point + the
pre-registered domain-recheck trigger). Authoritative physics numbers belong
to wp3_go_nogo_decision.md, not to these tests.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from postproc.multiharmonic_fit import fit_multiharmonic
from scripts.phase2_m2_verification import load_config
from scripts.phase5_a1_signed_zero_mean import measure_cold_instrument

A1_CFG = Path("configs/phase5/a1_signed_zero_mean/a1_wp3_10k_dx2p6.yaml")
PDC2_CFG = Path("configs/phase5/a2a_operating_point/pdc2_dc010_10k_dx2p6.yaml")
GAS = Path("configs/gas_air_10k_d2q37_levelc_dx2p6.yaml")


def test_signed_pair_separation_algebra():
    # odd keeps linear content INCLUDING its sign-flipping transient; even
    # isolates 2f and kills the linear transient — quantitative fixture
    # protocol-realistic window (14 periods, fit skip 12 = the G1-W constants):
    # the odd combination KEEPS the sign-flipping (linear) transient — that is
    # exactly why the settle-12 discipline exists; at the protocol window the
    # residual is ~e^-15 and the 1f recovery is clean.
    f = 1.0e4
    om = 2.0 * math.pi * f
    t = np.arange(0, 14.0 / f, 1.0 / f / 64.0)
    a1, b2, ctr = 1.0, 3e-3, 0.2
    tau = 0.8 / f
    plus = a1 * np.cos(om * t) + b2 * np.cos(2 * om * t + 0.4) + ctr * np.exp(-t / tau)
    minus = -a1 * np.cos(om * t) + b2 * np.cos(2 * om * t + 0.4) - ctr * np.exp(-t / tau)
    odd = 0.5 * (plus - minus)
    even = 0.5 * (plus + minus)
    mask = t >= 12.0 / f
    f_odd = fit_multiharmonic(t[mask], odd[mask], om, n_harmonics=5)
    f_even = fit_multiharmonic(t[mask], even[mask], om, n_harmonics=5)
    assert abs(f_odd.harmonic(1)) == pytest.approx(a1, rel=1e-6)
    # even content killed to the transient-leakage floor (~e^-15 * ctr into
    # the 2f bin), 6 orders below the injected b2
    assert abs(f_odd.harmonic(2)) < 1e-8
    assert abs(f_even.harmonic(2)) == pytest.approx(b2, rel=1e-6)
    assert abs(f_even.harmonic(1)) < 1e-12                     # linear content killed
    # non-degeneracy (early window, settle 4): the RAW series' 2f is
    # transient-biased there, while the EVEN combination at the SAME window is
    # exact — the pair buys window freedom for the 2f channel; and the odd 1f
    # still carries the (sign-flipping) transient bias — settle-12 has teeth
    mask4 = (t >= 4.0 / f) & (t <= 6.0 / f)
    f_raw4 = fit_multiharmonic(t[mask4], plus[mask4], om, n_harmonics=5)
    f_even4 = fit_multiharmonic(t[mask4], even[mask4], om, n_harmonics=5)
    f_odd4 = fit_multiharmonic(t[mask4], odd[mask4], om, n_harmonics=5)
    assert abs(abs(f_raw4.harmonic(2)) - b2) > 1e-7
    assert abs(f_even4.harmonic(2)) == pytest.approx(b2, rel=1e-9)
    assert abs(abs(f_odd4.harmonic(1)) - a1) > 1e-5


def test_cold_instrument_constants_mn_wall():
    gas = load_config(GAS)
    inst = measure_cold_instrument(gas, ny=16, nx=4, wall="mass_neutral_v1p1",
                                   log=lambda *_: None)
    # c_row = cv * rho0 * nx exactly on the uniform cold state
    assert inst["c_row_cv"] == pytest.approx(2.5 * 1.0 * 4, rel=1e-12)
    # certified accounting: instantaneous gas conductance ~ 0 (G4a A.4)
    assert abs(inst["G_inst"]) < 1e-3


def test_a1_pre_registration_frozen():
    cfg = load_config(A1_CFG)
    a1 = cfg["a1"]
    # first-round ladder truncated at the G1a authorization boundary 0.075
    assert [float(e) for e in a1["eps_ladder"]] == [0.001, 0.01, 0.05, 0.075]
    assert max(float(e) for e in a1["eps_ladder"]) <= 0.075
    # G1-W pair protocol constants verbatim
    assert (float(a1["ramp_periods"]), float(a1["periods"]),
            float(a1["fit_skip_periods"])) == (2.0, 14.0, 12.0)
    assert int(a1["ny"]) == 48 and int(a1["samples_per_period"]) == 64
    assert float(a1["wall_contrast_eps"]) == 0.05
    assert float(cfg["gates"]["mass_drift_max"]) == 1.0e-8
    # smoke block exists and is honest about its scope
    assert "a1_smoke" in cfg and float(cfg["a1_smoke"]["periods"]) < float(a1["periods"])


def test_pdc2_pre_registration_frozen():
    cfg = load_config(PDC2_CFG)
    p = cfg["pdc2"]
    assert float(p["theta_dc"]) == 0.10                  # §15.2 second canonical point
    assert [float(e) for e in p["eps_ac"]] == [0.005, 0.02]   # contract-frozen
    assert int(p["hs_rows"]) == 48                       # G4a canonical verbatim
    assert float(p["coupled_chi0"]) == 0.016
    assert float(p["qs_alpha_temperature_exponent"]) == 1.04
    # pre-registered domain re-check trigger present
    assert float(cfg["gates"]["domain_recheck_dop_abs"]) == 0.10
    assert "pdc2_smoke" in cfg
