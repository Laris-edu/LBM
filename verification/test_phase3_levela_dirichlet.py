"""P3-1 Level A prescribed wall-temperature tests."""

from __future__ import annotations

import math

import numpy as np

from boundary.wall_dirichlet import (
    advance_with_bottom_dirichlet_wall,
    apply_bottom_dirichlet_wall,
    sinusoidal_wall_temperature_lu,
)
from core.solver import GasSolver2D
from core.unit_mapping import d2q37_physical_timestep_config
from phase3_interfaces.complex_amplitude import complex_amplitude
from phase3_interfaces.wall_state_contract import wall_state_from_temperature


def _small_d2q37_solver(nx=16, ny=12):
    config = d2q37_physical_timestep_config()
    config["numerics"] = {**config.get("numerics", {}), "nx": nx, "ny": ny}
    solver = GasSolver2D(config)
    theta0 = solver.mapping.theta_ref_lu
    solver.initialize_from_macro(
        solver.mapping.lattice.rho_ref_lu,
        np.zeros((ny, nx, 2), dtype=float),
        theta0,
    )
    return solver


def test_levela_dirichlet_wall_recovers_temperature_and_no_slip_d2q37():
    solver = _small_d2q37_solver()
    theta_wall = solver.mapping.theta_ref_lu * 1.0001
    diag = apply_bottom_dirichlet_wall(solver, theta_wall_lu=theta_wall)
    macro = solver.get_macro()
    assert diag.velocity_set == "D2Q37"
    assert diag.Q == 37
    assert np.isfinite(solver.f).all()
    assert np.isfinite(solver.g).all()
    np.testing.assert_allclose(macro.theta[0], theta_wall, rtol=0.0, atol=1.0e-12)
    np.testing.assert_allclose(macro.u[0], 0.0, rtol=0.0, atol=1.0e-12)
    assert diag.max_theta_error_lu < 1.0e-12
    assert diag.max_velocity_lu < 1.0e-12


def test_levela_dirichlet_wall_si_conversion_uses_wall_state_contract():
    solver = _small_d2q37_solver()
    t_wall = 301.0
    expected = wall_state_from_temperature(t_wall, solver.config)["theta_wall_lu"]
    diag = apply_bottom_dirichlet_wall(solver, T_wall_K=t_wall)
    assert math.isclose(diag.theta_wall_lu, expected, rel_tol=0.0, abs_tol=1.0e-15)
    assert math.isclose(diag.T_wall_K, t_wall, rel_tol=0.0, abs_tol=1.0e-12)


def test_levela_dirichlet_reference_wall_has_no_mass_drift_after_step():
    solver = _small_d2q37_solver()
    initial_mass = float(np.sum(solver.f))
    diag = advance_with_bottom_dirichlet_wall(
        solver,
        theta_wall_lu=solver.mapping.theta_ref_lu,
        n_steps=2,
    )
    final_mass = float(np.sum(solver.f))
    assert diag.finite
    assert abs(final_mass - initial_mass) < 1.0e-10
    np.testing.assert_allclose(solver.get_macro().theta[0], solver.mapping.theta_ref_lu, atol=1.0e-12)


def test_levela_sinusoidal_wall_temperature_phase_convention():
    solver = _small_d2q37_solver()
    f_hz = 10_000.0
    theta0 = solver.mapping.theta_ref_lu
    theta_hat = 2.5e-5 - 1.0e-5j
    t = np.arange(128, dtype=float) / (128.0 * f_hz)
    response = []
    for item in t:
        theta_wall = sinusoidal_wall_temperature_lu(
            item,
            theta0_lu=theta0,
            theta_hat_lu=theta_hat,
            frequency_hz=f_hz,
        )
        diag = apply_bottom_dirichlet_wall(solver, theta_wall_lu=float(theta_wall))
        response.append(diag.recovered_theta_wall_lu - theta0)
    fitted = complex_amplitude(t, np.asarray(response), f_hz)
    np.testing.assert_allclose(fitted, theta_hat, rtol=1.0e-12, atol=1.0e-14)

