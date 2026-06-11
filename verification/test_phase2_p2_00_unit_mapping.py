import math

import yaml

from core.unit_mapping import (
    AUTO_TAU32_LINEAR_HEAT_FLUX_POLICY,
    AUTO_D2Q37_TAU32_LINEAR_HEAT_FLUX_POLICY,
    alpha_lu_from_tau32,
    create_unit_mapping,
    d2q37_physical_timestep_config,
    heat_flux_f_fraction_from_degrees,
    physical_timestep_config,
    quadrature_matched_config,
    regularized_heat_flux_factor_from_tau32,
)


def test_p2_0_physical_and_quadrature_mapping_are_explicit():
    physical = create_unit_mapping(physical_timestep_config())
    diagnostic = create_unit_mapping(quadrature_matched_config())

    assert math.isclose(physical.c0_lu, 0.26025, rel_tol=1.0e-12)
    assert math.isclose(physical.theta_ref_lu, physical.c0_lu**2 / 1.4, rel_tol=1.0e-12)
    assert math.isclose(physical.theta_transport_lu, physical.theta_ref_lu, rel_tol=1.0e-12)
    assert math.isclose(physical.Pr_lu, physical.nu_lu / physical.alpha_lu, rel_tol=1.0e-12)
    assert physical.tau32 > physical.tau21
    assert physical.collision.bulk_viscosity_policy == "diagnostic_zero"
    assert physical.collision.central_moment_closure == "second_order"
    assert physical.nu_b_lu == 0.0
    assert physical.collision.regularized_heat_flux_factor_policy == AUTO_TAU32_LINEAR_HEAT_FLUX_POLICY
    assert math.isclose(
        physical.collision.regularized_heat_flux_factor,
        regularized_heat_flux_factor_from_tau32(physical.tau32),
        rel_tol=1.0e-12,
    )
    assert math.isclose(
        alpha_lu_from_tau32(physical.tau32, physical.theta_transport_lu),
        physical.alpha_lu,
        rel_tol=1.0e-12,
    )
    assert math.isclose(
        physical.collision.regularized_heat_flux_f_fraction,
        heat_flux_f_fraction_from_degrees(physical.lattice.D, physical.lattice.S),
        rel_tol=1.0e-12,
    )

    assert math.isclose(diagnostic.theta_ref_lu, diagnostic.lattice.theta_q_lu, rel_tol=1.0e-12)
    assert diagnostic.tau32 > diagnostic.tau21

    d2q37 = create_unit_mapping(d2q37_physical_timestep_config())
    assert d2q37.lattice.velocity_set == "D2Q37"
    assert d2q37.lattice.Q == 37
    assert math.isclose(d2q37.lattice.theta_q_lu, 0.6979533220196852, rel_tol=1.0e-12)
    assert math.isclose(d2q37.theta_ref_lu, d2q37.c0_lu**2 / 1.4, rel_tol=1.0e-12)
    assert d2q37.collision.dispersion_correction_enabled
    assert math.isclose(d2q37.collision.regularized_shear_xy_dispersion_target, 0.786, rel_tol=1.0e-12)
    assert math.isclose(d2q37.collision.regularized_heat_flux_dispersion_target, 0.8512, rel_tol=1.0e-12)
    assert d2q37.collision.regularized_heat_flux_factor_policy == AUTO_D2Q37_TAU32_LINEAR_HEAT_FLUX_POLICY
    assert math.isclose(
        d2q37.collision.regularized_heat_flux_factor,
        regularized_heat_flux_factor_from_tau32(
            d2q37.tau32,
            policy=AUTO_D2Q37_TAU32_LINEAR_HEAT_FLUX_POLICY,
        ),
        rel_tol=1.0e-12,
    )
    assert math.isclose(
        alpha_lu_from_tau32(d2q37.tau32, d2q37.theta_transport_lu),
        d2q37.alpha_lu,
        rel_tol=1.0e-12,
    )


def test_p2_0_heat_flux_tau32_closure_parameters_are_family_specific():
    physical = create_unit_mapping(physical_timestep_config())
    d2q37 = create_unit_mapping(d2q37_physical_timestep_config())

    assert not physical.collision.dispersion_correction_enabled
    assert math.isclose(physical.collision.conductive_heat_flux_moment_factor, 0.05192359403391186)
    assert math.isclose(
        physical.collision.conductive_heat_flux_galilean_correction_factor,
        0.03272660408381829,
    )
    assert math.isclose(physical.collision.regularized_heat_flux_factor, -0.4649237356175009)

    assert math.isclose(d2q37.collision.conductive_heat_flux_moment_factor, 0.0422)
    assert math.isclose(
        d2q37.collision.conductive_heat_flux_galilean_correction_factor,
        0.03835608923273733,
    )
    assert math.isclose(d2q37.collision.regularized_heat_flux_factor, -0.4406919094556388)

    low_mode_x = 4.0 * math.sin(math.pi / 64.0) ** 2
    low_mode_diagonal = 2.0 * low_mode_x
    high_mode_x = 4.0 * math.sin(2.0 * math.pi / 64.0) ** 2
    assert math.isclose(d2q37.collision.dispersion_correction_low_laplacian, low_mode_diagonal)
    assert math.isclose(d2q37.collision.dispersion_correction_high_laplacian, high_mode_x)
    assert math.isclose(d2q37.collision.conductive_heat_flux_dispersion_target, 0.3201)


def test_p2_0_yaml_baseline_uses_diagnostic_zero_bulk_policy():
    with open("configs/gas_air_10k_physical_timestep.yaml", "r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    mapping = create_unit_mapping(config)
    meta = mapping.to_metadata()
    required = {
        "theta_q_lu",
        "theta_ref_lu",
        "theta_transport_lu",
        "dx_m",
        "dt_s",
        "tau21",
        "tau22",
        "tau32",
        "bulk_viscosity_policy",
        "heat_flux_scale",
    }
    assert required.issubset(meta)
    assert meta["bulk_viscosity_policy"] == "diagnostic_zero"
