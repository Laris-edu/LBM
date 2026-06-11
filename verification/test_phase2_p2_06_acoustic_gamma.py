import math

import numpy as np

from core.unit_mapping import create_unit_mapping, d2q37_physical_timestep_config, physical_timestep_config
from phase3_interfaces.modal_fit import fit_phase_speed
from verification.acoustic_wave_measurement import (
    ACOUSTIC_ATTENUATION_STATUS,
    _matched_nsf_acoustic_attenuation_coeff_lu,
    measure_acoustic_wave,
)


def test_p2_6_synthetic_acoustic_wave_speed_and_gamma():
    mapping = create_unit_mapping(physical_timestep_config())
    nx = 128
    mode = 2
    k = 2.0 * np.pi * mode / nx
    c_target = math.sqrt(mapping.physical.gamma * mapping.theta_ref_lu)
    t = np.arange(0, 80, dtype=float)
    amps = np.exp(1j * k * c_target * t)
    c_measured = fit_phase_speed(t, amps, k)
    gamma_measured = c_measured**2 / mapping.theta_ref_lu
    assert abs(c_measured / c_target - 1.0) < 1.0e-12
    assert abs(gamma_measured / mapping.physical.gamma - 1.0) < 1.0e-12
    assert ACOUSTIC_ATTENUATION_STATUS.startswith("DIAGNOSTIC_ONLY")


def test_p2_6_d2q37_matched_nsf_acoustic_attenuation_target():
    mapping = create_unit_mapping(d2q37_physical_timestep_config())
    k = 2.0 * np.pi / 64.0

    expected_coeff = 0.5 * (
        2.0 * (mapping.lattice.D - 1.0) / mapping.lattice.D * mapping.nu_lu
        + mapping.nu_b_lu
        + (mapping.physical.gamma - 1.0) * mapping.alpha_lu
    )
    assert mapping.lattice.D == 2
    assert mapping.lattice.S == 3
    assert mapping.collision.bulk_viscosity_policy == "diagnostic_zero"
    assert mapping.nu_b_lu == 0.0
    assert math.isclose(
        _matched_nsf_acoustic_attenuation_coeff_lu(mapping),
        expected_coeff,
        rel_tol=0.0,
        abs_tol=1.0e-15,
    )
    assert math.isclose(expected_coeff * k * k, 2.22224320740558e-05, rel_tol=0.0, abs_tol=1.0e-15)


def test_p2_6_real_acoustic_wave_measurement_reports_status_fields():
    config = physical_timestep_config()
    config["p2_06_acoustic_wave"] = {
        "nx": 24,
        "ny": 24,
        "steps": 24,
        "sample_interval": 1,
        "mode_index": 1,
        "amplitude": 1.0e-6,
        "fit_start": 4,
        "directions": ["x"],
        "background_velocity_lu": [1.0e-3, 0.0],
    }
    result = measure_acoustic_wave(config)
    assert result["p2_06_status"] in {"PASSED", "FAILED"}
    assert result["directions"] == ["x"]
    assert result["mode_index"] == 1
    assert result["background_velocity_lu"] == [1.0e-3, 0.0]
    assert result["sound_speed_target_lu"] > 0.0
    assert result["gamma_target"] == 1.4
    assert result["attenuation_status"].startswith("DIAGNOSTIC_ONLY")
    assert result["acoustic_attenuation_target_policy"] == "MATCHED_LINEARIZED_NSF_D2_BULK_ZERO_CP_ALPHA"
    assert "x" in result["direction_results"]
    assert result["direction_results"]["x"]["sample_count"] > 0
    assert result["clipping_used"] is False


def test_p2_6_d2q37_real_acoustic_wave_passes_transport_candidate_boundary():
    config = d2q37_physical_timestep_config()
    config["p2_06_acoustic_wave"] = {
        "nx": 64,
        "ny": 64,
        "steps": 80,
        "sample_interval": 1,
        "mode_index": 1,
        "amplitude": 1.0e-6,
        "fit_start": 10,
        "directions": ["x", "y"],
        "sound_speed_tolerance": 0.02,
        "gamma_tolerance": 0.02,
        "direction_tolerance": 0.02,
    }
    result = measure_acoustic_wave(config)
    assert result["p2_06_status"] == "PASSED"
    assert result["sound_speed_relative_error"] < 0.02
    assert result["gamma_relative_error"] < 0.02
    assert result["direction_difference"] < 0.02
    assert result["attenuation_status"].startswith("DIAGNOSTIC_ONLY")
    assert result["acoustic_attenuation_target_coeff_lu"] > 0.0
    assert result["first_invalid_step"] is None
    assert result["nan_detected"] is False
    assert result["clipping_used"] is False
