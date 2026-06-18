import math

import pytest
import yaml

from core.unit_mapping import (
    AUTO_TAU32_LINEAR_HEAT_FLUX_POLICY,
    AUTO_D2Q37_TAU32_LINEAR_HEAT_FLUX_POLICY,
    GHOST_ORTHOGONAL_TRACE_ALPHA_INTERCEPT,
    GHOST_ORTHOGONAL_TRACE_ALPHA_SLOPE,
    GHOST_ORTHOGONAL_LOCAL_TRACE_DIVERGENCE_INTERCEPT,
    GHOST_ORTHOGONAL_LOCAL_TRACE_DIVERGENCE_SLOPE,
    GHOST_ORTHOGONAL_LOCAL_LAPLACIAN_COEFFICIENT_INTERCEPT,
    GHOST_ORTHOGONAL_LOCAL_LAPLACIAN_COEFFICIENT_SLOPE,
    GHOST_ORTHOGONAL_LOCAL_LAPLACIAN_DIVERGENCE_INTERCEPT,
    GHOST_ORTHOGONAL_LOCAL_LAPLACIAN_DIVERGENCE_SLOPE,
    GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL_ACOUSTIC_INTERCEPT,
    GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL_ACOUSTIC_SLOPE,
    GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL_THERMAL_INTERCEPT,
    GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL_THERMAL_SLOPE,
    TRACE_BULK_POLICY_CURRENT_ZERO,
    TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL,
    TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_ENTROPY_MANIFOLD,
    TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_LAPLACIAN,
    TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_PRESSURE_MEMORY,
    TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL,
    TRACE_BULK_POLICY_GHOST_ORTHOGONAL_SPECTRAL,
    alpha_lu_from_tau32,
    create_unit_mapping,
    d2q37_physical_timestep_config,
    heat_flux_f_fraction_from_degrees,
    physical_timestep_config,
    quadrature_matched_config,
    regularized_heat_flux_factor_from_tau32,
    trace_bulk_projector_alpha_from_tau32,
    trace_bulk_local_divergence_factor_from_tau32,
    trace_bulk_local_laplacian_factor_from_tau32,
    trace_bulk_local_thermal_factor_from_tau32,
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
    assert math.isclose(
        d2q37.collision.regularized_heat_flux_diagonal_low_mode_target,
        0.908799,
        rel_tol=1.0e-12,
    )
    assert d2q37.collision.acoustic_phase_correction_enabled
    assert math.isclose(
        d2q37.collision.acoustic_phase_diagonal_low_mode_factor,
        0.98405,
        rel_tol=1.0e-12,
    )
    assert math.isclose(d2q37.collision.acoustic_phase_high_mode_factor, 1.0, rel_tol=1.0e-12)
    assert math.isclose(
        d2q37.collision.acoustic_phase_high_mode_diagonal_factor,
        1.0,
        rel_tol=1.0e-12,
    )
    assert d2q37.collision.trace_bulk_policy == TRACE_BULK_POLICY_CURRENT_ZERO
    assert math.isclose(d2q37.collision.trace_bulk_scale, 1.0, rel_tol=1.0e-12)
    assert d2q37.collision.trace_bulk_calibration_id is None
    assert d2q37.collision.regularized_heat_flux_factor_policy == AUTO_D2Q37_TAU32_LINEAR_HEAT_FLUX_POLICY
    assert d2q37.collision.heat_flux_retention_policy == AUTO_D2Q37_TAU32_LINEAR_HEAT_FLUX_POLICY
    assert d2q37.collision.heat_flux_retention_curve_type == "affine"
    assert d2q37.collision.heat_flux_retention_curve_coefficients == (
        -0.5030006782780277,
        0.7230829392328689,
    )
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
    assert math.isclose(d2q37.collision.conductive_heat_flux_diagonal_low_mode_target, 0.610151)
    assert math.isclose(d2q37.collision.acoustic_phase_correction_low_laplacian, low_mode_diagonal)


def test_p2_0_d2q37_ghost_orthogonal_spectral_trace_policy_is_explicit():
    config = d2q37_physical_timestep_config()
    config["collision"]["trace_bulk_policy"] = TRACE_BULK_POLICY_GHOST_ORTHOGONAL_SPECTRAL
    mapping = create_unit_mapping(config)

    assert mapping.collision.trace_bulk_policy == TRACE_BULK_POLICY_GHOST_ORTHOGONAL_SPECTRAL
    assert mapping.collision.trace_bulk_projector_alpha_curve_type == "affine"
    assert mapping.collision.trace_bulk_projector_alpha_curve_coefficients == (
        GHOST_ORTHOGONAL_TRACE_ALPHA_INTERCEPT,
        GHOST_ORTHOGONAL_TRACE_ALPHA_SLOPE,
    )
    assert math.isclose(
        mapping.collision.trace_bulk_projector_low_laplacian,
        mapping.collision.dispersion_correction_low_laplacian,
        rel_tol=1.0e-12,
    )
    assert math.isfinite(
        trace_bulk_projector_alpha_from_tau32(
            mapping.tau32,
            curve_type=mapping.collision.trace_bulk_projector_alpha_curve_type,
            coefficients=mapping.collision.trace_bulk_projector_alpha_curve_coefficients,
        )
    )

    invalid = physical_timestep_config()
    invalid["collision"]["trace_bulk_policy"] = TRACE_BULK_POLICY_GHOST_ORTHOGONAL_SPECTRAL
    invalid["collision"]["trace_bulk_projector_low_laplacian"] = 1.0e-2
    with pytest.raises(ValueError, match="D2Q37-only"):
        create_unit_mapping(invalid)


def test_p2_0_d2q37_ghost_orthogonal_local_trace_policy_is_explicit():
    config = d2q37_physical_timestep_config()
    config["collision"]["trace_bulk_policy"] = TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL
    mapping = create_unit_mapping(config)

    assert mapping.collision.trace_bulk_policy == TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL
    assert mapping.collision.trace_bulk_local_divergence_curve_type == "affine"
    assert mapping.collision.trace_bulk_local_divergence_curve_coefficients == (
        GHOST_ORTHOGONAL_LOCAL_TRACE_DIVERGENCE_INTERCEPT,
        GHOST_ORTHOGONAL_LOCAL_TRACE_DIVERGENCE_SLOPE,
    )
    assert math.isfinite(
        trace_bulk_local_divergence_factor_from_tau32(
            mapping.tau32,
            curve_type=mapping.collision.trace_bulk_local_divergence_curve_type,
            coefficients=mapping.collision.trace_bulk_local_divergence_curve_coefficients,
        )
    )

    invalid = physical_timestep_config()
    invalid["collision"]["trace_bulk_policy"] = TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL
    with pytest.raises(ValueError, match="D2Q37-only"):
        create_unit_mapping(invalid)


def test_p2_0_d2q37_ghost_orthogonal_local_laplacian_trace_policy_is_explicit():
    config = d2q37_physical_timestep_config()
    config["collision"]["trace_bulk_policy"] = TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_LAPLACIAN
    mapping = create_unit_mapping(config)

    assert mapping.collision.trace_bulk_policy == TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_LAPLACIAN
    assert mapping.collision.trace_bulk_local_divergence_curve_coefficients == (
        GHOST_ORTHOGONAL_LOCAL_LAPLACIAN_DIVERGENCE_INTERCEPT,
        GHOST_ORTHOGONAL_LOCAL_LAPLACIAN_DIVERGENCE_SLOPE,
    )
    assert mapping.collision.trace_bulk_local_laplacian_curve_coefficients == (
        GHOST_ORTHOGONAL_LOCAL_LAPLACIAN_COEFFICIENT_INTERCEPT,
        GHOST_ORTHOGONAL_LOCAL_LAPLACIAN_COEFFICIENT_SLOPE,
    )
    assert math.isfinite(
        trace_bulk_local_divergence_factor_from_tau32(
            mapping.tau32,
            curve_type=mapping.collision.trace_bulk_local_divergence_curve_type,
            coefficients=mapping.collision.trace_bulk_local_divergence_curve_coefficients,
        )
    )
    assert math.isfinite(
        trace_bulk_local_laplacian_factor_from_tau32(
            mapping.tau32,
            curve_type=mapping.collision.trace_bulk_local_laplacian_curve_type,
            coefficients=mapping.collision.trace_bulk_local_laplacian_curve_coefficients,
        )
    )

    invalid = physical_timestep_config()
    invalid["collision"]["trace_bulk_policy"] = TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_LAPLACIAN
    with pytest.raises(ValueError, match="D2Q37-only"):
        create_unit_mapping(invalid)


def test_p2_0_d2q37_ghost_orthogonal_local_pressure_memory_policy_is_explicit():
    config = d2q37_physical_timestep_config()
    config["collision"]["trace_bulk_policy"] = TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_PRESSURE_MEMORY
    mapping = create_unit_mapping(config)

    assert mapping.collision.trace_bulk_policy == TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_PRESSURE_MEMORY
    assert mapping.collision.trace_bulk_local_divergence_curve_coefficients == (
        GHOST_ORTHOGONAL_LOCAL_TRACE_DIVERGENCE_INTERCEPT,
        GHOST_ORTHOGONAL_LOCAL_TRACE_DIVERGENCE_SLOPE,
    )
    assert math.isfinite(
        trace_bulk_local_divergence_factor_from_tau32(
            mapping.tau32,
            curve_type=mapping.collision.trace_bulk_local_divergence_curve_type,
            coefficients=mapping.collision.trace_bulk_local_divergence_curve_coefficients,
        )
    )

    invalid = physical_timestep_config()
    invalid["collision"]["trace_bulk_policy"] = TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_PRESSURE_MEMORY
    with pytest.raises(ValueError, match="D2Q37-only"):
        create_unit_mapping(invalid)


def test_p2_0_d2q37_ghost_orthogonal_local_two_channel_policy_is_explicit():
    config = d2q37_physical_timestep_config()
    config["collision"]["trace_bulk_policy"] = TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL
    mapping = create_unit_mapping(config)

    assert mapping.collision.trace_bulk_policy == TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL
    assert mapping.collision.trace_bulk_local_divergence_curve_coefficients == (
        GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL_ACOUSTIC_INTERCEPT,
        GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL_ACOUSTIC_SLOPE,
    )
    assert mapping.collision.trace_bulk_local_thermal_curve_coefficients == (
        GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL_THERMAL_INTERCEPT,
        GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL_THERMAL_SLOPE,
    )
    assert math.isfinite(
        trace_bulk_local_divergence_factor_from_tau32(
            mapping.tau32,
            curve_type=mapping.collision.trace_bulk_local_divergence_curve_type,
            coefficients=mapping.collision.trace_bulk_local_divergence_curve_coefficients,
        )
    )
    assert math.isfinite(
        trace_bulk_local_thermal_factor_from_tau32(
            mapping.tau32,
            curve_type=mapping.collision.trace_bulk_local_thermal_curve_type,
            coefficients=mapping.collision.trace_bulk_local_thermal_curve_coefficients,
        )
    )

    invalid = physical_timestep_config()
    invalid["collision"]["trace_bulk_policy"] = TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL
    with pytest.raises(ValueError, match="D2Q37-only"):
        create_unit_mapping(invalid)


def test_p2_0_d2q37_ghost_orthogonal_local_entropy_manifold_policy_is_explicit():
    config = d2q37_physical_timestep_config()
    config["collision"]["trace_bulk_policy"] = TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_ENTROPY_MANIFOLD
    mapping = create_unit_mapping(config)

    assert mapping.collision.trace_bulk_policy == TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_ENTROPY_MANIFOLD
    assert mapping.collision.trace_bulk_local_divergence_curve_coefficients == (
        GHOST_ORTHOGONAL_LOCAL_LAPLACIAN_DIVERGENCE_INTERCEPT,
        GHOST_ORTHOGONAL_LOCAL_LAPLACIAN_DIVERGENCE_SLOPE,
    )
    assert mapping.collision.trace_bulk_local_laplacian_curve_coefficients == (
        GHOST_ORTHOGONAL_LOCAL_LAPLACIAN_COEFFICIENT_INTERCEPT,
        GHOST_ORTHOGONAL_LOCAL_LAPLACIAN_COEFFICIENT_SLOPE,
    )
    assert mapping.collision.trace_bulk_local_thermal_curve_coefficients == (
        GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL_THERMAL_INTERCEPT,
        GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL_THERMAL_SLOPE,
    )
    assert math.isfinite(
        trace_bulk_local_divergence_factor_from_tau32(
            mapping.tau32,
            curve_type=mapping.collision.trace_bulk_local_divergence_curve_type,
            coefficients=mapping.collision.trace_bulk_local_divergence_curve_coefficients,
        )
    )
    assert math.isfinite(
        trace_bulk_local_laplacian_factor_from_tau32(
            mapping.tau32,
            curve_type=mapping.collision.trace_bulk_local_laplacian_curve_type,
            coefficients=mapping.collision.trace_bulk_local_laplacian_curve_coefficients,
        )
    )
    assert math.isfinite(
        trace_bulk_local_thermal_factor_from_tau32(
            mapping.tau32,
            curve_type=mapping.collision.trace_bulk_local_thermal_curve_type,
            coefficients=mapping.collision.trace_bulk_local_thermal_curve_coefficients,
        )
    )

    invalid = physical_timestep_config()
    invalid["collision"]["trace_bulk_policy"] = TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_ENTROPY_MANIFOLD
    with pytest.raises(ValueError, match="D2Q37-only"):
        create_unit_mapping(invalid)


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
