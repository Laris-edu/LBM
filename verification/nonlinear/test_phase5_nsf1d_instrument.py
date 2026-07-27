"""WP1-2 nonlinear 1D NSF solver instrument tests (contract §8, Phase5 v1.2).

Instrument certification for ``reference/nonlinear_nsf_1d.py`` at mechanism
level (the formal G3 gate runs land in WP2 with the contract run-file set):

- exact discrete equilibrium preservation (gate row <1e-10; measured 0),
- acoustic ringdown: sound speed via phase drift + physical damping bound
  (a dissipative scheme would overshoot the bulk prediction),
- small-amplitude linear anchor against the Phase_1 half-space admittance
  with the closed-box pressure-work correction (raw vs corrected reported;
  the box correction magnitude itself is asserted against its prediction),
- two-grid convergence direction of the anchor phase error,
- signed-pair linearization leakage floor <=1e-8 with a physical-2f
  sensitivity counter-check (the rig must SEE genuine nonlinearity),
- dual-property-branch divergence at large epsilon (non-degeneracy of the
  1D-lbm-equivalent vs 1D-physical machinery),
- A1 signed zero-mean flux protocol smoke and film-ODE coupling smoke with
  machine-level mass/energy audits,
- transport-model anchoring and input validation.

Scaled ("toy") parameters are used for runtime: T0 x9 and rho0 /9 keep
R = p0/(rho0 T0) and raise c x3; kg=0.2912 sets alpha ~ 100x air. The NSF
equations and the Phase_1 reference are parameter-free in this respect, so
the anchor's validity is unchanged; a real-air 10 kHz single-point evidence
run is recorded in Phase5_STATUS §3. Suite runtime ~2 min (dominated by the
anchor and pair fixtures). No Phase_5 gate status is claimed here.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from reference.constants import default_params
from reference.nonlinear_nsf_1d import (
    NSF1DConfig,
    WallDrive,
    acoustic_ringdown_fixture,
    antisymmetric_pair_fixture,
    equilibrium_fixture,
    lbm_equivalent_transport,
    linear_admittance_fixture,
    physical_air_transport,
    power_law_transport,
    run_nsf1d,
)
from postproc.multiharmonic_fit import fit_multiharmonic

F0_HZ = 1.0e4
OMEGA = 2.0 * math.pi * F0_HZ
# alpha x100 (kg=0.2912), c x3 (T0 x9, rho0 /9 keeps R and p0): compact box
# with 13x box-mode separation at affordable acoustic CFL.
TOY = default_params(T0=2700.0, rho0=1.177 / 9.0, kg=0.2912)


def _toy_delta() -> float:
    alpha0 = TOY.kg / (TOY.rho0 * TOY.cp)
    return math.sqrt(2.0 * alpha0 / OMEGA)


def test_equilibrium_preservation_is_exact():
    eq = equilibrium_fixture()  # real-air params, undriven, 10 cycles
    assert eq["max_dp_rel"] <= 1.0e-13  # gate row: <1e-10; discrete equilibrium is exact
    assert eq["mass_drift_rel"] <= 1.0e-14
    assert eq["energy_residual_rel_total"] <= 1.0e-13
    assert eq["max_mach"] <= 1.0e-14


def test_acoustic_ringdown_sound_speed_and_low_dissipation():
    # nu x100 makes the 12-period decay measurable and viscosity-dominated;
    # bulk prediction is a lower bound — the isothermal ends add a fixed
    # unbuffered-wall-sink excess ~8e3/s (delta_kappa(f_box) << dy; G3
    # finding), ~+14% here where physical damping is ~5.9e4/s; a dissipative
    # scheme would blow the cap. The G3 gate row uses the sealed adiabatic
    # variant (true eigenmode, no boundary sink).
    ring = acoustic_ringdown_fixture(params=default_params(nu0=1.57e-3))
    assert 0.95 <= ring["gamma_ratio"] <= 1.45
    assert abs(ring["frequency_offset_rel"]) <= 0.01
    assert 0.25 <= ring["amplitude_retention"] <= 0.65
    assert ring["mass_drift_rel"] <= 1.0e-13


def test_linear_anchor_against_phase1_halfspace_admittance():
    lin = linear_admittance_fixture(
        params=TOY, transport=lbm_equivalent_transport(TOY), frequency_hz=F0_HZ
    )
    # corrected anchor (gate rows are 2%/2 deg; mechanism margins below)
    assert abs(lin["amp_error_corrected"]) <= 5.0e-3
    assert abs(lin["phase_error_deg_corrected"]) <= 0.5
    # the closed-box pressure-work effect is present at its predicted size
    # ((gamma-1)/(|m|H) ~ 1.9% at H=15 delta) and the correction removes it
    assert 0.012 <= lin["box_correction_rel"] <= 0.026
    assert abs(lin["amp_error_corrected"]) < abs(lin["amp_error_raw"])
    # audits: zero-mass-flux wall and RK-weighted energy accounting
    assert lin["mass_drift_rel"] <= 1.0e-13
    assert lin["energy_residual_rel_flux"] <= 1.0e-9


def test_linear_anchor_two_grid_convergence_direction():
    fine = linear_admittance_fixture(
        params=TOY, transport=lbm_equivalent_transport(TOY), frequency_hz=F0_HZ,
        cells_per_delta=12.0,
    )
    coarse = linear_admittance_fixture(
        params=TOY, transport=lbm_equivalent_transport(TOY), frequency_hz=F0_HZ,
        cells_per_delta=6.0,
    )
    assert abs(coarse["amp_error_corrected"]) <= 1.0e-2
    assert abs(coarse["phase_error_deg_corrected"]) <= 1.0
    # grid-driven phase error must shrink strongly under refinement
    # (measured ratio ~3.7 = observed order ~1.9; formal >=1.5-order ladder in G3)
    ratio = abs(coarse["phase_error_deg_corrected"]) / max(
        abs(fine["phase_error_deg_corrected"]), 1.0e-6
    )
    assert ratio >= 2.0


def test_signed_pair_leakage_floor_and_physical_sensitivity():
    pair = antisymmetric_pair_fixture(
        params=TOY, transport=lbm_equivalent_transport(TOY), frequency_hz=F0_HZ
    )
    # numerical harmonic floor of the discrete chain (gate row: <=1e-8)
    assert pair["max_even_leakage_odd_combination"] <= 1.0e-8
    assert pair["third_harmonic_odd_combination"] <= 1.0e-8
    assert pair["passed"] is True
    # sensitivity counter-check: the even combination must SEE the genuine
    # physical 2f (~C2*epsilon ~ 2e-6 at epsilon=1e-5), far above the floor
    assert pair["physical_2f_rel_even_combination"] >= 1.0e-7
    assert pair["mass_drift_rel"] <= 1.0e-13


def test_dual_property_branches_diverge_at_large_epsilon():
    # non-degeneracy of the 1D-lbm-equivalent vs 1D-physical machinery:
    # at epsilon=0.2 the T-dependent transport must visibly change the
    # harmonic response (calibrated: 2f differs ~60%, 1f ~0.24%)
    delta = _toy_delta()
    fits = {}
    for name, transport in (
        ("lbm", lbm_equivalent_transport(TOY)),
        ("phys", physical_air_transport(TOY)),
    ):
        drive = WallDrive(
            kind="temperature", frequency_hz=F0_HZ,
            amplitude=0.2 * TOY.T0, ramp_cycles=1.5,
        )
        cfg = NSF1DConfig(
            params=TOY, transport=transport, drive=drive,
            height_m=10.0 * delta, n_cells=80, n_cycles=6.0,
        )
        res = run_nsf1d(cfg)
        mask = res.t_samples >= 2.0 / F0_HZ
        fits[name] = fit_multiharmonic(
            res.t_samples[mask], res.q_wall_conductive[mask], OMEGA
        )
        assert res.max_mach < 1.0e-2
        assert res.mass_drift_rel <= 1.0e-13
    diff_1f = abs(fits["phys"].harmonic(1) - fits["lbm"].harmonic(1)) / abs(
        fits["lbm"].harmonic(1)
    )
    diff_2f = abs(fits["phys"].harmonic(2) - fits["lbm"].harmonic(2)) / abs(
        fits["lbm"].harmonic(2)
    )
    assert diff_2f > 0.1
    assert diff_1f > 5.0e-4


def test_a1_signed_zero_mean_flux_protocol_smoke():
    delta = _toy_delta()
    drive = WallDrive(
        kind="flux", frequency_hz=F0_HZ, amplitude=40.0, mean=0.0, ramp_cycles=1.0
    )
    cfg = NSF1DConfig(
        params=TOY, transport=lbm_equivalent_transport(TOY), drive=drive,
        height_m=4.0 * delta, n_cells=32, n_cycles=3.0,
    )
    res = run_nsf1d(cfg)
    # signed zero-mean caloric forcing: active cooling half-cycles are real
    assert float(np.min(res.q_wall_applied)) < -1.0
    assert float(np.max(res.q_wall_applied)) > 1.0
    # applied flux matches the pre-registered protocol at the sample times
    k = len(res.t_samples) // 2
    assert res.q_wall_applied[k] == pytest.approx(drive.forcing(res.t_samples[k]), abs=1e-12)
    # gas responds and audits close at machine level
    assert float(np.std(res.wall_temperature)) > 1.0e-4
    assert res.mass_drift_rel <= 1.0e-13
    assert res.energy_residual_rel_flux <= 1.0e-9
    assert np.all(np.isfinite(res.T_final)) and np.all(res.T_final > 0.0)


def test_film_ode_coupling_smoke():
    delta = _toy_delta()
    drive = WallDrive(
        kind="film", frequency_hz=F0_HZ, amplitude=1.0e5, mean=0.0,
        ramp_cycles=1.0, film_heat_capacity=0.35,
    )
    cfg = NSF1DConfig(
        params=TOY, transport=lbm_equivalent_transport(TOY), drive=drive,
        height_m=8.0 * delta, n_cells=64, n_cycles=4.0,
    )
    res = run_nsf1d(cfg)
    assert res.film_temperature is not None
    # coupling is non-degenerate: film moves and drives real gas-side flux
    assert float(np.max(np.abs(res.film_temperature - TOY.T0))) > 1.0
    assert float(np.max(np.abs(res.q_wall_conductive))) > 100.0
    # combined film+gas energy audit (P - q'' - q_lid bookkeeping) closes
    assert res.energy_residual_rel_flux <= 1.0e-9
    assert res.mass_drift_rel <= 1.0e-13


def test_transport_models_anchored_and_distinct():
    params = default_params()
    lbm = lbm_equivalent_transport(params)
    phys = physical_air_transport(params)
    power = power_law_transport(
        params, mu_exponent=0.76, k_exponent=0.85, property_model_id="g0_placeholder_v0"
    )
    # both branches anchored exactly at the frozen reference state
    assert float(lbm.mu(params.T0)) == pytest.approx(params.mu, rel=1e-15)
    assert float(lbm.k(params.T0)) == pytest.approx(params.kg, rel=1e-15)
    assert float(phys.mu(params.T0)) == pytest.approx(params.mu, rel=1e-15)
    assert float(phys.k(params.T0)) == pytest.approx(params.kg, rel=1e-15)
    assert float(power.mu(params.T0)) == pytest.approx(params.mu, rel=1e-15)
    # physical branch has the Sutherland shape: rising, sub-T^1.5
    t_hot = 400.0
    ratio_mu = float(phys.mu(t_hot)) / params.mu
    expected = (t_hot / 300.0) ** 1.5 * (300.0 + 110.4) / (t_hot + 110.4)
    assert ratio_mu == pytest.approx(expected, rel=1e-12)
    assert 1.0 < ratio_mu < (t_hot / 300.0) ** 1.5
    # constant branch is flat; ids are archived and distinct
    assert float(lbm.mu(t_hot)) == pytest.approx(params.mu, rel=1e-15)
    assert lbm.property_model_id != phys.property_model_id != power.property_model_id


def test_adiabatic_lid_mode_seals_energy():
    # sealed symmetry-plane analog (half-box of a both-sides-driven sealed box):
    # zero lid flux, all input from the wall; audits must still close exactly
    delta = _toy_delta()
    drive = WallDrive(
        kind="temperature", frequency_hz=F0_HZ,
        amplitude=1.0e-4 * TOY.T0, ramp_cycles=1.0,
    )
    cfg = NSF1DConfig(
        params=TOY, transport=lbm_equivalent_transport(TOY), drive=drive,
        height_m=2.5 * delta, n_cells=24, n_cycles=3.0, lid_bc="adiabatic",
    )
    res = run_nsf1d(cfg)
    assert res.energy_residual_rel_flux <= 1.0e-9
    assert res.mass_drift_rel <= 1.0e-13
    assert bool(np.all(np.isfinite(res.T_final)) and np.all(res.T_final > 0.0))
    # energy-balance identity on the sealed half-box: net wall input == d/dt of
    # (cv/R) * integral(p) — the calibration-free flux readout used by the
    # G1-W energy-balance discriminator (validated here on exact-flux data)
    with pytest.raises(ValueError):
        NSF1DConfig(
            params=TOY, transport=lbm_equivalent_transport(TOY), drive=drive,
            height_m=2.5 * delta, n_cells=24, n_cycles=1.0, lid_bc="mirror",
        )


def test_config_and_drive_validation():
    params = default_params()
    transport = lbm_equivalent_transport(params)
    with pytest.raises(ValueError):
        WallDrive(kind="voltage", frequency_hz=F0_HZ, amplitude=1.0)
    with pytest.raises(ValueError):
        WallDrive(kind="film", frequency_hz=F0_HZ, amplitude=1.0)  # missing C_A
    with pytest.raises(ValueError):
        WallDrive(kind="flux", frequency_hz=-1.0, amplitude=1.0)
    good = WallDrive(kind="temperature", frequency_hz=F0_HZ, amplitude=1.0)
    with pytest.raises(ValueError):
        NSF1DConfig(
            params=params, transport=transport, drive=good,
            height_m=1e-3, n_cells=4, n_cycles=1.0,
        )
    with pytest.raises(ValueError):
        NSF1DConfig(
            params=params, transport=transport, drive=good,
            height_m=-1e-3, n_cells=32, n_cycles=1.0,
        )
