"""P3-2 Level B prescribed wall heat-flux tests."""

from __future__ import annotations

import math

import numpy as np

from boundary.wall_neumann import (
    apply_bottom_neumann_wall,
    heat_flux_lu_from_inputs,
    sinusoidal_wall_heat_flux_lu,
)
from core.solver import GasSolver2D
from core.unit_mapping import d2q37_physical_timestep_config
from phase3_interfaces.complex_amplitude import complex_amplitude
from phase3_interfaces.heat_flux_extraction import convert_heat_flux_lu_to_phys


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


def test_levelb_neumann_wall_recovers_imposed_heat_flux_d2q37():
    solver = _small_d2q37_solver()
    q_wall_lu = 2.0e-9
    diag = apply_bottom_neumann_wall(solver, q_wall_lu=q_wall_lu)
    assert diag.velocity_set == "D2Q37"
    assert diag.Q == 37
    assert diag.finite
    np.testing.assert_allclose(diag.q_wall_recovered_lu, q_wall_lu, rtol=1.0e-12, atol=1.0e-18)
    assert diag.max_velocity_lu < 1.0e-12
    assert diag.max_tangential_heat_flux_lu < 1.0e-12


def test_levelb_neumann_wall_si_conversion_roundtrip():
    solver = _small_d2q37_solver()
    q_wall_si = 10.0
    expected_lu = heat_flux_lu_from_inputs(solver, q_wall_si=q_wall_si)
    diag = apply_bottom_neumann_wall(solver, q_wall_si=q_wall_si)
    assert math.isclose(diag.q_wall_imposed_lu, expected_lu, rel_tol=0.0, abs_tol=1.0e-18)
    np.testing.assert_allclose(diag.q_wall_recovered_si, q_wall_si, rtol=1.0e-12, atol=1.0e-9)
    np.testing.assert_allclose(
        diag.q_wall_recovered_si,
        convert_heat_flux_lu_to_phys(diag.q_wall_recovered_lu, solver.config),
        rtol=1.0e-12,
    )


def test_levelb_positive_flux_increases_gas_energy_with_audit():
    solver = _small_d2q37_solver()
    q_wall_lu = 3.0e-9
    diag = apply_bottom_neumann_wall(solver, q_wall_lu=q_wall_lu)
    expected = q_wall_lu * solver.nx
    np.testing.assert_allclose(diag.expected_energy_delta_lu, expected, rtol=0.0, atol=1.0e-24)
    np.testing.assert_allclose(diag.energy_delta_lu, expected, rtol=1.0e-9, atol=1.0e-18)
    assert diag.theta_wall_lu_after > diag.theta_wall_lu_before


def test_levelb_negative_flux_has_negative_sign_and_cools_wall():
    solver = _small_d2q37_solver()
    q_wall_lu = -2.0e-9
    diag = apply_bottom_neumann_wall(solver, q_wall_lu=q_wall_lu)
    np.testing.assert_allclose(diag.q_wall_recovered_lu, q_wall_lu, rtol=1.0e-12, atol=1.0e-18)
    assert diag.energy_delta_lu < 0.0
    assert diag.theta_wall_lu_after < diag.theta_wall_lu_before


def test_levelb_sinusoidal_flux_phase_convention_reads_back_field():
    solver = _small_d2q37_solver()
    f_hz = 10_000.0
    q_hat = 2.0e-9 - 7.0e-10j
    t = np.arange(128, dtype=float) / (128.0 * f_hz)
    recovered = []
    imposed = []
    for item in t:
        q_wall = sinusoidal_wall_heat_flux_lu(
            item,
            q0_lu=0.0,
            q_hat_lu=q_hat,
            frequency_hz=f_hz,
        )
        diag = apply_bottom_neumann_wall(solver, q_wall_lu=float(q_wall))
        imposed.append(q_wall)
        recovered.append(diag.q_wall_recovered_lu)
    q_fit = complex_amplitude(t, np.asarray(recovered), f_hz)
    q_input_fit = complex_amplitude(t, np.asarray(imposed), f_hz)
    np.testing.assert_allclose(q_fit, q_input_fit, rtol=1.0e-12, atol=1.0e-18)
