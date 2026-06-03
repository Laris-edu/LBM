import math

from core.unit_mapping import create_unit_mapping, physical_timestep_config


def test_p2_9_galilean_consistency_contract_subtracts_background_advection():
    mapping = create_unit_mapping(physical_timestep_config())
    c_s = math.sqrt(mapping.physical.gamma * mapping.theta_ref_lu)
    intrinsic_speed = c_s
    for mach in [0.0, 0.02, 0.05]:
        U0 = mach * c_s
        lab_speed = intrinsic_speed + U0
        recovered = lab_speed - U0
        assert abs(recovered / intrinsic_speed - 1.0) < 1.0e-12
    assert mapping.to_metadata()["array_layout"].startswith("c=(Q,D)")
