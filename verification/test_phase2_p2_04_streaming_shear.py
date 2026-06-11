import numpy as np

from core.lattice_d2q21 import make_d2q21
from core.streaming import pull_stream
from core.unit_mapping import create_unit_mapping, d2q37_physical_timestep_config, physical_timestep_config
from phase3_interfaces.modal_fit import fit_exponential_decay, modal_amplitude
from verification.shear_wave_measurement import measure_shear_wave


def test_p2_4_pull_streaming_uses_velocity_axis_last_and_pull_formula():
    lattice = make_d2q21()
    f = np.zeros((5, 7, lattice.q))
    f[2, 3, 1] = 1.0  # cx=1, cy=0
    streamed = pull_stream(f, lattice=lattice)
    assert streamed[2, 4, 1] == 1.0
    assert streamed.shape == f.shape


def test_p2_4_synthetic_shear_wave_measures_target_nu():
    mapping = create_unit_mapping(physical_timestep_config())
    nx = 64
    mode = 2
    k = 2.0 * np.pi * mode / nx
    t = np.arange(0, 80, dtype=float)
    x = np.arange(nx, dtype=float)
    fields = np.array([np.exp(-mapping.nu_lu * k * k * ti) * np.sin(k * x) for ti in t])
    amps = np.array([modal_amplitude(field, mode, "x") for field in fields])
    decay, _ = fit_exponential_decay(t, amps)
    nu_measured = decay / (k * k)
    assert abs(nu_measured / mapping.nu_lu - 1.0) < 1.0e-10


def test_p2_4_real_shear_wave_measurement_reports_status_fields():
    config = physical_timestep_config()
    config["p2_04_shear_wave"] = {
        "nx": 24,
        "ny": 24,
        "steps": 12,
        "sample_interval": 1,
        "mode_index": 1,
        "amplitude": 1.0e-5,
        "fit_start": 3,
        "directions": ["x"],
        "background_velocity_lu": [1.0e-3, 0.0],
    }
    result = measure_shear_wave(config)
    assert result["p2_04_status"] in {"PASSED", "FAILED"}
    assert result["directions"] == ["x"]
    assert result["mode_index"] == 1
    assert result["background_velocity_lu"] == [1.0e-3, 0.0]
    assert result["nu_target_lu"] > 0.0
    assert "x" in result["direction_results"]
    assert result["direction_results"]["x"]["background_velocity_lu"] == [1.0e-3, 0.0]
    assert result["direction_results"]["x"]["sample_count"] > 0
    assert result["clipping_used"] is False


def test_p2_4_d2q37_shear_wave_diagnostic_runs_to_status():
    config = d2q37_physical_timestep_config()
    config["p2_04_shear_wave"] = {
        "nx": 16,
        "ny": 16,
        "steps": 6,
        "sample_interval": 1,
        "mode_index": 1,
        "amplitude": 1.0e-5,
        "fit_start": 2,
        "directions": ["x"],
    }
    result = measure_shear_wave(config)
    assert result["p2_04_status"] in {"PASSED", "FAILED"}
    assert result["directions"] == ["x"]
    assert result["direction_results"]["x"]["sample_count"] > 0
    assert result["clipping_used"] is False
