import math

import yaml

from core.unit_mapping import create_unit_mapping, physical_timestep_config, quadrature_matched_config


def test_p2_0_physical_and_quadrature_mapping_are_explicit():
    physical = create_unit_mapping(physical_timestep_config())
    diagnostic = create_unit_mapping(quadrature_matched_config())

    assert math.isclose(physical.c0_lu, 0.26025, rel_tol=1.0e-12)
    assert math.isclose(physical.theta_ref_lu, physical.c0_lu**2 / 1.4, rel_tol=1.0e-12)
    assert math.isclose(physical.theta_transport_lu, physical.theta_ref_lu, rel_tol=1.0e-12)
    assert math.isclose(physical.Pr_lu, physical.nu_lu / physical.alpha_lu, rel_tol=1.0e-12)
    assert physical.tau32 > physical.tau21
    assert physical.collision.bulk_viscosity_policy == "diagnostic_zero"
    assert physical.nu_b_lu == 0.0

    assert math.isclose(diagnostic.theta_ref_lu, diagnostic.lattice.theta_q_lu, rel_tol=1.0e-12)
    assert diagnostic.tau32 > diagnostic.tau21


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

