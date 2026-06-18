import numpy as np

from core.collision_smrt import assert_collision_conservation, collide_fg
from core.equilibrium import equilibrium_fg
from core.lattice import make_lattice
from core.solver import GasSolver2D, conservative_biharmonic_filter
from core.unit_mapping import (
    TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_ENTROPY_MANIFOLD,
    TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_PRESSURE_MEMORY,
    TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL,
    create_unit_mapping,
    d2q37_physical_timestep_config,
    physical_timestep_config,
)


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


def test_p2_3_d2q37_collision_conserves_mass_momentum_and_total_energy():
    config = d2q37_physical_timestep_config()
    mapping = create_unit_mapping(config)
    lattice = make_lattice(mapping.lattice.velocity_set)
    rho = np.ones((2, 3))
    theta = np.full((2, 3), mapping.theta_ref_lu)
    u = np.zeros((2, 3, 2))
    u[..., 0] = 1.0e-4
    f, g = equilibrium_fg(rho, u, theta, mapping.lattice.S, lattice=lattice)
    rng = np.random.default_rng(43)
    f = f + 1.0e-10 * rng.normal(size=f.shape)
    g = g + 1.0e-10 * rng.normal(size=g.shape)
    assert_collision_conservation(f, g, mapping, tol=5.0e-12, lattice=lattice)
    _, _, diagnostics = collide_fg(f, g, mapping, lattice=lattice, return_diagnostics=True)
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


def test_p2_3_d2q37_uniform_state_has_no_drift_over_periodic_steps():
    config = d2q37_physical_timestep_config()
    config["numerics"] = {"nx": 6, "ny": 4}
    solver = GasSolver2D(config)
    solver.initialize_from_macro(1.0, np.zeros(2), create_unit_mapping(config).theta_ref_lu)
    before = solver.get_macro()
    solver.step(4)
    after = solver.get_macro()
    assert np.max(np.abs(after.rho - before.rho)) < 1.0e-12
    assert np.max(np.abs(after.u - before.u)) < 1.0e-12
    assert np.max(np.abs(after.theta - before.theta)) < 1.0e-12


def test_p2_3_d2q37_pressure_memory_trace_policy_uniform_state_has_no_drift():
    config = d2q37_physical_timestep_config()
    config["collision"]["trace_bulk_policy"] = TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_PRESSURE_MEMORY
    config["numerics"] = {"nx": 6, "ny": 4}
    solver = GasSolver2D(config)
    solver.initialize_from_macro(1.0, np.zeros(2), create_unit_mapping(config).theta_ref_lu)
    before = solver.get_macro()
    solver.step(4)
    after = solver.get_macro()
    assert np.max(np.abs(after.rho - before.rho)) < 1.0e-12
    assert np.max(np.abs(after.u - before.u)) < 1.0e-12
    assert np.max(np.abs(after.theta - before.theta)) < 1.0e-12


def test_p2_3_d2q37_two_channel_trace_policy_uniform_state_has_no_drift():
    config = d2q37_physical_timestep_config()
    config["collision"]["trace_bulk_policy"] = TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL
    config["numerics"] = {"nx": 6, "ny": 4}
    solver = GasSolver2D(config)
    solver.initialize_from_macro(1.0, np.zeros(2), create_unit_mapping(config).theta_ref_lu)
    before = solver.get_macro()
    solver.step(4)
    after = solver.get_macro()
    assert np.max(np.abs(after.rho - before.rho)) < 1.0e-12
    assert np.max(np.abs(after.u - before.u)) < 1.0e-12
    assert np.max(np.abs(after.theta - before.theta)) < 1.0e-12


def test_p2_3_d2q37_entropy_manifold_trace_policy_uniform_state_has_no_drift():
    config = d2q37_physical_timestep_config()
    config["collision"]["trace_bulk_policy"] = TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_ENTROPY_MANIFOLD
    config["numerics"] = {"nx": 6, "ny": 4}
    solver = GasSolver2D(config)
    solver.initialize_from_macro(1.0, np.zeros(2), create_unit_mapping(config).theta_ref_lu)
    before = solver.get_macro()
    solver.step(4)
    after = solver.get_macro()
    assert np.max(np.abs(after.rho - before.rho)) < 1.0e-12
    assert np.max(np.abs(after.u - before.u)) < 1.0e-12
    assert np.max(np.abs(after.theta - before.theta)) < 1.0e-12


def test_p2_3_high_wavenumber_filter_preserves_sum_and_damps_checkerboard():
    y, x = np.indices((8, 8))
    field = ((-1.0) ** (x + y))[..., None] * np.ones((1, 1, 3))
    filtered = conservative_biharmonic_filter(field, strength=0.02)
    assert np.allclose(np.sum(filtered, axis=(0, 1)), np.sum(field, axis=(0, 1)))
    assert np.max(np.abs(filtered)) < np.max(np.abs(field))
