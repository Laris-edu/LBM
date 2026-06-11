import math

import numpy as np

from core.equilibrium import equilibrium_fg, gaussian_raw_moment_targets, raw_moments
from core.hermite import assert_discrete_orthogonality
from core.lattice import make_lattice
from core.macroscopic import recover_macro
from core.polyatomic_fg import assert_air_degrees, gamma_from_degrees
from core.unit_mapping import (
    create_unit_mapping,
    d2q37_physical_timestep_config,
    physical_timestep_config,
    quadrature_matched_config,
)


def _check_equilibrium_for_mapping(config):
    mapping = create_unit_mapping(config)
    lattice = make_lattice(mapping.lattice.velocity_set)
    rho = np.array([[1.0]])
    theta = np.array([[mapping.theta_ref_lu]])
    for mach, direction in [(0.0, np.array([1.0, 0.0])), (0.01, np.array([1.0, 1.0]) / math.sqrt(2.0))]:
        c_s = math.sqrt(mapping.physical.gamma * mapping.theta_ref_lu)
        u = (mach * c_s * direction).reshape(1, 1, 2)
        f_eq, g_eq = equilibrium_fg(rho, u, theta, mapping.lattice.S, lattice=lattice)
        f_mom = raw_moments(f_eq, lattice=lattice, max_order=4)
        targets = gaussian_raw_moment_targets(rho, u, theta, max_order=4)[0, 0]
        exponents = list(f_mom)
        for i, exp in enumerate(exponents):
            assert np.allclose(f_mom[exp], targets[i], rtol=1.0e-9, atol=1.0e-12)
        g_mom = raw_moments(g_eq, lattice=lattice, max_order=2)
        e_extra = 0.5 * mapping.lattice.S * rho * theta
        g_targets = gaussian_raw_moment_targets(e_extra, u, theta, max_order=2)[0, 0]
        for i, exp in enumerate(list(g_mom)):
            assert np.allclose(g_mom[exp], g_targets[i], rtol=1.0e-9, atol=1.0e-12)
        macro = recover_macro(f_eq, g_eq, D=mapping.lattice.D, S=mapping.lattice.S, lattice=lattice)
        assert np.allclose(macro.rho, rho, atol=1.0e-12)
        assert np.allclose(macro.u, u, atol=1.0e-12)
        assert np.allclose(macro.theta, theta, rtol=1.0e-9, atol=1.0e-12)
        assert math.isclose(macro.gamma, 1.4, rel_tol=1.0e-12)


def test_p2_2_hermite_equilibrium_macro_and_gamma():
    assert_discrete_orthogonality()
    assert_air_degrees()
    assert math.isclose(gamma_from_degrees(2, 3), 1.4)
    _check_equilibrium_for_mapping(physical_timestep_config())
    _check_equilibrium_for_mapping(quadrature_matched_config())
    _check_equilibrium_for_mapping(d2q37_physical_timestep_config())
