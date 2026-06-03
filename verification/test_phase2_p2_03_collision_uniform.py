import numpy as np

from core.collision_smrt import assert_collision_conservation, collide_fg
from core.equilibrium import equilibrium_fg
from core.solver import GasSolver2D
from core.unit_mapping import create_unit_mapping, physical_timestep_config


def test_p2_3_collision_conserves_mass_momentum_and_total_energy():
    mapping = create_unit_mapping(physical_timestep_config())
    rho = np.ones((3, 5))
    theta = np.full((3, 5), mapping.theta_ref_lu)
    u = np.zeros((3, 5, 2))
    u[..., 0] = 1.0e-4
    f, g = equilibrium_fg(rho, u, theta, mapping.lattice.S)
    rng = np.random.default_rng(42)
    f = f + 1.0e-10 * rng.normal(size=f.shape)
    g = g + 1.0e-10 * rng.normal(size=g.shape)
    assert_collision_conservation(f, g, mapping, tol=5.0e-12)
    _, _, diagnostics = collide_fg(f, g, mapping, return_diagnostics=True)
    assert diagnostics.clipping_used is False


def test_p2_3_uniform_state_has_no_drift_over_periodic_steps():
    config = physical_timestep_config()
    config["numerics"] = {"nx": 8, "ny": 4}
    solver = GasSolver2D(config)
    solver.initialize_from_macro(1.0, np.zeros(2), create_unit_mapping(config).theta_ref_lu)
    before = solver.get_macro()
    solver.step(10)
    after = solver.get_macro()
    assert np.max(np.abs(after.rho - before.rho)) < 1.0e-12
    assert np.max(np.abs(after.u - before.u)) < 1.0e-12
    assert np.max(np.abs(after.theta - before.theta)) < 1.0e-12

