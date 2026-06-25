"""Phase_3 Level A/B handoff interface tests.

Covers the gas-side handoff surface Phase_3 consumes: lattice-aware conductive
wall heat-flux extraction (must work for the D2Q37 default baseline, not only
D2Q21), LU<->SI conversion, and probe sampling.  Previously the extraction path
hardcoded D2Q21 and had no test coverage.
"""

from __future__ import annotations

import numpy as np

from core.solver import GasSolver2D
from core.unit_mapping import (
    d2q37_physical_timestep_config,
    physical_timestep_config,
)
from phase3_interfaces.heat_flux_extraction import (
    UPPER_GAS_WALL_NORMAL,
    convert_heat_flux_lu_to_phys,
    extract_wall_heat_flux,
    normal_heat_flux_lu,
)


def _thermal_gradient_solver(config, nx=16, ny=16, amplitude=1.0e-5, steps=5):
    cfg = {**config, "numerics": {**config.get("numerics", {}), "nx": nx, "ny": ny}}
    solver = GasSolver2D(cfg)
    theta0 = solver.mapping.theta_ref_lu
    ky = 2.0 * np.pi / ny
    profile = theta0 * (1.0 + amplitude * np.sin(ky * np.arange(ny, dtype=float)))
    theta = np.repeat(profile[:, None], nx, axis=1)
    p0 = solver.mapping.lattice.rho_ref_lu * theta0
    rho = p0 / theta
    u = np.zeros((ny, nx, 2), dtype=float)
    solver.initialize_from_macro(rho, u, theta)
    solver.step(steps)
    return solver, cfg


def test_extract_wall_heat_flux_matches_solver_d2q37():
    """Lattice-aware extraction must handle the D2Q37 default and match the solver."""
    solver, cfg = _thermal_gradient_solver(d2q37_physical_timestep_config())
    q_n = extract_wall_heat_flux(solver.f, solver.g, config=cfg)
    expected = normal_heat_flux_lu(solver.get_heat_flux_lu(), UPPER_GAS_WALL_NORMAL)
    assert q_n.shape == expected.shape
    assert np.isfinite(q_n).all()
    np.testing.assert_allclose(q_n, expected, rtol=1.0e-10, atol=1.0e-300)


def test_extract_wall_heat_flux_backward_compat_d2q21():
    """With no config-implied D2Q37, the legacy D2Q21 path still works."""
    solver, cfg = _thermal_gradient_solver(physical_timestep_config())
    q_n = extract_wall_heat_flux(solver.f, solver.g, config=cfg)
    expected = normal_heat_flux_lu(solver.get_heat_flux_lu(), UPPER_GAS_WALL_NORMAL)
    np.testing.assert_allclose(q_n, expected, rtol=1.0e-10, atol=1.0e-300)


def test_extract_wall_heat_flux_physical_roundtrip():
    solver, cfg = _thermal_gradient_solver(d2q37_physical_timestep_config())
    q_n_lu = extract_wall_heat_flux(solver.f, solver.g, config=cfg)
    q_n_phys = extract_wall_heat_flux(solver.f, solver.g, config=cfg, return_physical=True)
    np.testing.assert_allclose(q_n_phys, convert_heat_flux_lu_to_phys(q_n_lu, cfg), rtol=1.0e-12)


def test_sample_probe_returns_handoff_fields():
    solver, _ = _thermal_gradient_solver(d2q37_physical_timestep_config())
    samples = solver.sample_probe([(2, 3), (8, 8)])
    assert set(samples) == {"probe_0", "probe_1"}
    for sample in samples.values():
        assert {"rho_lu", "u_lu", "theta_lu", "p_lu", "q_lu"} <= set(sample)
        assert np.isfinite(sample["q_lu"]).all()
        assert sample["u_lu"].shape == (2,)
        assert sample["q_lu"].shape == (2,)
