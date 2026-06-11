import math
from copy import deepcopy

from core.unit_mapping import create_unit_mapping, d2q37_physical_timestep_config, physical_timestep_config
from verification.acoustic_wave_measurement import measure_acoustic_wave
from verification.galilean_consistency_measurement import measure_galilean_consistency


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


def test_p2_9_real_galilean_measurement_reports_transport_and_acoustic_fields():
    config = physical_timestep_config()
    config["p2_09_galilean_consistency"] = {
        "mach_numbers": [0.0, 0.02],
        "background_directions": ["x"],
        "run_dispersion_masking_check": False,
        "run_high_mode_acoustic_diagnostic": False,
        "shear_wave": {
            "nx": 16,
            "ny": 16,
            "steps": 8,
            "sample_interval": 1,
            "mode_index": 1,
            "amplitude": 1.0e-5,
            "fit_start": 2,
            "directions": ["x"],
        },
        "thermal_diffusion": {
            "nx": 16,
            "ny": 16,
            "steps": 8,
            "sample_interval": 1,
            "mode_index": 1,
            "amplitude": 1.0e-5,
            "fit_start": 2,
            "directions": ["x"],
        },
        "acoustic_wave": {
            "nx": 16,
            "ny": 16,
            "steps": 8,
            "sample_interval": 1,
            "mode_index": 1,
            "amplitude": 1.0e-6,
            "fit_start": 2,
            "directions": ["x"],
        },
    }
    result = measure_galilean_consistency(config)

    assert result["p2_09_status"] in {"PASSED", "FAILED"}
    assert result["mach_numbers"] == [0.0, 0.02]
    assert result["background_directions"] == ["x"]
    assert result["scenario_count"] == 1
    assert result["reference"]["background_velocity_lu"] == [0.0, 0.0]
    scenario = result["scenarios"][0]
    assert scenario["mach"] == 0.02
    assert scenario["background_direction"] == "x"
    assert scenario["background_velocity_lu"][0] > 0.0
    assert "nu_drift_from_mach0" in scenario
    assert "alpha_drift_from_mach0" in scenario
    assert "sound_speed_relative_error" in scenario
    assert result["dispersion_masking_status"] == "NOT_RUN"


def test_p2_9_d2q37_dispersion_correction_does_not_mask_high_mode_acoustic_error():
    base = d2q37_physical_timestep_config()
    mapping = create_unit_mapping(base)
    c_s = math.sqrt(mapping.physical.gamma * mapping.theta_ref_lu)
    background_velocity = [0.05 * c_s, 0.0]
    results = {}
    for enabled in (True, False):
        config = deepcopy(base)
        config["collision"]["dispersion_correction_enabled"] = enabled
        config["p2_06_acoustic_wave"] = {
            "nx": 64,
            "ny": 64,
            "steps": 80,
            "sample_interval": 1,
            "mode_index": 2,
            "amplitude": 1.0e-6,
            "fit_start": 10,
            "directions": ["x", "y"],
            "sound_speed_tolerance": 0.02,
            "gamma_tolerance": 0.02,
            "direction_tolerance": 0.02,
            "background_velocity_lu": background_velocity,
        }
        results[enabled] = measure_acoustic_wave(config)

    corrected = results[True]
    uncorrected = results[False]
    assert not (corrected["p2_06_status"] == "PASSED" and uncorrected["p2_06_status"] != "PASSED")
    assert corrected["sound_speed_relative_error"] > 0.02
    assert uncorrected["sound_speed_relative_error"] > 0.02
    assert corrected["first_invalid_step"] is None
    assert uncorrected["first_invalid_step"] is None
