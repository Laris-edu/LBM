from copy import deepcopy

from core.unit_mapping import create_unit_mapping, d2q37_physical_timestep_config, physical_timestep_config
from verification.prandtl_scan_measurement import measure_prandtl_scan


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


def test_p2_7_real_prandtl_scan_measurement_reports_status_fields():
    config = physical_timestep_config()
    config["p2_07_prandtl_scan"] = {
        "pr_targets": [0.7061328707, 1.0],
        "baseline_pr": 0.7061328707,
        "shear_wave": {
            "nx": 24,
            "ny": 24,
            "steps": 12,
            "sample_interval": 1,
            "mode_index": 1,
            "amplitude": 1.0e-5,
            "fit_start": 3,
            "directions": ["x"],
        },
        "thermal_diffusion": {
            "nx": 24,
            "ny": 24,
            "steps": 12,
            "sample_interval": 1,
            "mode_index": 1,
            "amplitude": 1.0e-5,
            "fit_start": 3,
            "directions": ["x"],
        },
    }
    result = measure_prandtl_scan(config)
    assert result["p2_07_status"] in {"PASSED", "FAILED"}
    assert result["pr_targets"] == [0.7061328707, 1.0]
    assert len(result["scan_points"]) == 2
    for point in result["scan_points"]:
        assert point["status"] in {"PASSED", "FAILED"}
        assert point["nu_target_lu"] > 0.0
        assert point["alpha_target_lu"] > 0.0
        assert "shear" in point
        assert "thermal" in point
    assert result["clipping_used"] is False


def test_p2_7_d2q37_prandtl_scan_diagnostic_runs_to_status():
    config = d2q37_physical_timestep_config()
    config["p2_07_prandtl_scan"] = {
        "pr_targets": [0.7061328707],
        "baseline_pr": 0.7061328707,
        "shear_wave": {
            "nx": 16,
            "ny": 16,
            "steps": 6,
            "sample_interval": 1,
            "mode_index": 1,
            "amplitude": 1.0e-5,
            "fit_start": 2,
            "directions": ["x"],
        },
        "thermal_diffusion": {
            "nx": 16,
            "ny": 16,
            "steps": 6,
            "sample_interval": 1,
            "mode_index": 1,
            "amplitude": 1.0e-5,
            "fit_start": 2,
            "directions": ["x"],
        },
    }
    result = measure_prandtl_scan(config)
    assert result["p2_07_status"] in {"PASSED", "FAILED"}
    assert result["pr_targets"] == [0.7061328707]
    assert len(result["scan_points"]) == 1
    assert result["scan_points"][0]["status"] in {"PASSED", "FAILED"}
    assert result["clipping_used"] is False
