"""P3-4 Level C predictor-corrector coupling smoke tests."""

from __future__ import annotations

import numpy as np
import pytest

from core.solver import GasSolver2D
from core.unit_mapping import d2q37_physical_timestep_config
from coupling.conjugate import (
    extract_bottom_wall_heat_flux_si,
    initialize_levelc_state,
    run_levelc_predictor_corrector,
)
from coupling.drive import ConstantDrive, SinusoidalDrive
from coupling.energy_audit import audit_film_energy
from coupling.film_ode import FilmOdeParams


def _small_solver(nx=16, ny=8):
    config = d2q37_physical_timestep_config()
    config["numerics"] = {**config.get("numerics", {}), "nx": nx, "ny": ny}
    config["case"] = {**config.get("case", {}), "phase": "Phase_3", "level": "C"}
    return GasSolver2D(config)


def test_levelc_initial_uniform_wall_extracts_finite_heat_flux():
    # At the uniform initial state (wall == gas temperature) there is no gradient, so the
    # near-wall flux is legitimately ~0. This is the *only* state where q_g ~ 0 is correct;
    # see test_levelc_coupling_is_nondegenerate for the developed-gradient case.
    solver = _small_solver()
    initialize_levelc_state(solver, T_initial_K=300.0)
    q_si = extract_bottom_wall_heat_flux_si(solver)
    assert np.isfinite(q_si)
    assert abs(q_si) < 1.0e-4


def test_levelc_coupling_is_nondegenerate_gas_feeds_back():
    # Regression for the degenerate coupling bug: q_g'' must be read from the near-wall
    # gas, not the clamped equilibrium wall row. With a constant drive the wall heats
    # relative to the gas, a real gradient develops, and q_g'' grows to O(100) W/m^2 and
    # cools the film well below the adiabatic ramp.
    solver = _small_solver()
    params = FilmOdeParams(C_A_si=7.0e-4, T_ref_K=300.0)
    result = run_levelc_predictor_corrector(
        solver=solver,
        params=params,
        drive=ConstantDrive(power_density_si=1000.0),
        n_steps=64,
        energy_tolerance=1.0e-2,
        scheme="heun_picard1",
    )
    q = np.abs(result.q_g_one_sided_si)
    assert q[0] < 1.0e-3  # uniform start -> ~0
    assert q[-1] > 1.0  # developed flux is O(100) W/m^2, not the ~1e-5 wall-row artifact
    assert q[-1] > 1.0e3 * q[0]  # grew by many orders as the gradient developed
    # Real feedback: the 2*q_g'' cooling holds T_s well below the adiabatic ramp.
    adiabatic_delta = 1000.0 * (result.t_si[-1] - result.t_si[0]) / params.C_A_si
    assert 0.0 < (result.T_s_K[-1] - result.T_s_K[0]) < 0.5 * adiabatic_delta
    # The predictor-corrector is now actually exercised (non-trivial correction).
    assert np.max(np.abs(result.predictor_corrector_delta_K)) > 1.0e-6


def test_levelc_heun_picard_smoke_heats_film_and_audits_energy():
    solver = _small_solver()
    params = FilmOdeParams(C_A_si=7.0e-4, T_ref_K=300.0)
    result = run_levelc_predictor_corrector(
        solver=solver,
        params=params,
        drive=ConstantDrive(power_density_si=1000.0),
        n_steps=8,
        energy_tolerance=1.0e-2,
        scheme="heun_picard1",
    )
    assert result.coupling_scheme == "heun_picard1"
    assert result.picard_iterations == 1
    assert result.finite
    assert result.energy_audit.passed
    assert result.T_s_K[-1] > result.T_s_K[0]
    assert np.max(np.abs(result.wall_temperature_error_K)) < 1.0e-8
    assert np.isfinite(result.q_g_one_sided_si).all()
    assert np.isfinite(solver.f).all()
    assert np.isfinite(solver.g).all()


def test_levelc_sinusoidal_drive_uses_phase3_drive_convention():
    solver = _small_solver()
    params = FilmOdeParams(C_A_si=7.0e-4, T_ref_K=300.0)
    drive = SinusoidalDrive(mean_si=0.0, amplitude_hat_si=1000.0 + 0.0j, frequency_hz=10_000.0)
    result = run_levelc_predictor_corrector(
        solver=solver,
        params=params,
        drive=drive,
        n_steps=6,
        energy_tolerance=2.0e-2,
        scheme="heun_picard1",
    )
    assert result.finite
    assert result.energy_audit.passed
    assert result.P_in_si[0] == 1000.0
    assert result.T_wall_K[-1] == pytest.approx(result.T_s_K[-1], abs=1.0e-10)


def test_levelc_energy_audit_detects_tampered_trajectory():
    solver = _small_solver()
    params = FilmOdeParams(C_A_si=7.0e-4, T_ref_K=300.0)
    result = run_levelc_predictor_corrector(
        solver=solver,
        params=params,
        drive=ConstantDrive(power_density_si=1000.0),
        n_steps=8,
        energy_tolerance=1.0e-2,
        scheme="heun_picard1",
    )
    tampered = result.T_s_K.copy()
    tampered[-1] += 1.0
    audit = audit_film_energy(
        t_si=result.t_si,
        P_in_si=result.P_in_si,
        q_g_one_sided_si=result.q_g_one_sided_si,
        T_s_K=tampered,
        params=params,
        tolerance=1.0e-2,
    )
    assert not audit.passed


def test_levelc_thermal_grad_wall_is_stable_and_audited():
    # P3-5+ Grad regularized wall through the coupler: stable, self-consistent integrated
    # energy audit (film integrates the under-relaxed q_fb, which is recorded), real
    # gas->film feedback (nonzero near-wall q_g), and records the wall_bc/relax metadata.
    solver = _small_solver()
    params = FilmOdeParams(C_A_si=7.0e-4, T_ref_K=300.0)
    result = run_levelc_predictor_corrector(
        solver=solver,
        params=params,
        drive=ConstantDrive(power_density_si=1000.0),
        n_steps=64,
        energy_tolerance=1.0e-2,
        wall_bc="thermal_grad",
        q_feedback_relax=0.02,
    )
    assert result.wall_bc == "thermal_grad"
    assert result.q_feedback_relax == 0.02
    assert result.finite
    assert result.energy_audit.passed
    assert np.max(np.abs(result.q_g_one_sided_si)) > 1.0  # real near-wall flux, not ~1e-5 clamp artifact
    assert np.all(np.abs(result.T_wall_K - result.T_s_K) <= result.wall_temperature_error_K + 1.0e-12)
    assert np.max(np.abs(result.T_wall_K - result.T_s_K)) > 0.0
    # Coupling is active: T_s deviates strongly from the adiabatic (q_g=0) ramp.
    adiabatic = 1000.0 * (result.t_si[-1] - result.t_si[0]) / params.C_A_si
    assert abs((result.T_s_K[-1] - result.T_s_K[0]) - adiabatic) > 0.3 * adiabatic
    assert np.isfinite(solver.f).all() and np.isfinite(solver.g).all()


def test_levelc_rejects_unknown_wall_bc_and_bad_relax():
    solver = _small_solver()
    params = FilmOdeParams(C_A_si=7.0e-4, T_ref_K=300.0)
    with pytest.raises(ValueError):
        run_levelc_predictor_corrector(
            solver=solver, params=params, drive=ConstantDrive(power_density_si=1000.0),
            n_steps=2, wall_bc="nonsense",
        )
    with pytest.raises(ValueError):
        run_levelc_predictor_corrector(
            solver=solver, params=params, drive=ConstantDrive(power_density_si=1000.0),
            n_steps=2, q_feedback_relax=0.0,
        )
    with pytest.raises(ValueError, match="grad_extrap"):
        run_levelc_predictor_corrector(
            solver=solver, params=params, drive=ConstantDrive(power_density_si=1000.0),
            n_steps=2, grad_extrap="typo",
        )


def test_levelc_rejects_a_film_clock_that_differs_from_the_gas_clock():
    solver = _small_solver()
    params = FilmOdeParams(C_A_si=7.0e-4, T_ref_K=300.0)
    with pytest.raises(ValueError, match="subcycling"):
        run_levelc_predictor_corrector(
            solver=solver,
            params=params,
            drive=ConstantDrive(power_density_si=1000.0),
            n_steps=2,
            dt_si=2.0 * solver.mapping.lattice.dt_s,
        )
