from copy import deepcopy

from core.unit_mapping import create_unit_mapping, physical_timestep_config


def test_p2_7_prandtl_scan_independent_tau21_tau32_mapping():
    base = physical_timestep_config()
    base_mapping = create_unit_mapping(base)
    for pr in [0.5, 0.7061328707, 1.0, 2.0]:
        config = deepcopy(base)
        config["physical"] = {
            "nu0_m2_s": 1.57e-5,
            "alpha0_m2_s": 1.57e-5 / pr,
            "Pr": pr,
            "gamma": 1.4,
        }
        mapping = create_unit_mapping(config)
        assert abs(mapping.Pr_lu - pr) < 1.0e-12
        assert abs(mapping.nu_lu - base_mapping.nu_lu) < 1.0e-15
        if pr < 1.0:
            assert mapping.tau32 > mapping.tau21
        elif pr > 1.0:
            assert mapping.tau32 < mapping.tau21

