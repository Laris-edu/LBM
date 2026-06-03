import numpy as np

from core.unit_mapping import create_unit_mapping, heat_flux_lu_to_phys, physical_timestep_config
from phase3_interfaces.heat_flux_extraction import UPPER_GAS_WALL_NORMAL, normal_heat_flux_lu
from phase3_interfaces.modal_fit import fit_exponential_decay, modal_amplitude
from verification.thermal_diffusion_measurement import measure_thermal_diffusion


def test_p2_5_isobaric_thermal_diffusion_measures_target_alpha():
    mapping = create_unit_mapping(physical_timestep_config())
    nx = 64
    mode = 1
    k = 2.0 * np.pi * mode / nx
    t = np.arange(0, 80, dtype=float)
    x = np.arange(nx, dtype=float)
    fields = np.array([np.exp(-mapping.alpha_lu * k * k * ti) * np.sin(k * x) for ti in t])
    amps = np.array([modal_amplitude(field, mode, "x") for field in fields])
    decay, _ = fit_exponential_decay(t, amps)
    alpha_measured = decay / (k * k)
    assert abs(alpha_measured / mapping.alpha_lu - 1.0) < 1.0e-10


def test_p2_5_fourier_heat_flux_scale_and_upper_gas_sign():
    mapping = create_unit_mapping(physical_timestep_config())
    dTdy_phys = -10_000.0  # K/m, temperature decreases away from hot film
    q_phys_expected = -mapping.physical.kg_W_mK * dTdy_phys
    q_lu_y = q_phys_expected / mapping.heat_flux_scale
    q_n_lu = normal_heat_flux_lu(np.array([0.0, q_lu_y]), UPPER_GAS_WALL_NORMAL)
    q_phys = heat_flux_lu_to_phys(q_n_lu, mapping)
    assert q_n_lu > 0.0
    assert abs(q_phys / q_phys_expected - 1.0) < 1.0e-12


def test_p2_5_real_thermal_diffusion_measurement_reports_status_fields():
    config = physical_timestep_config()
    config["p2_05_thermal_diffusion"] = {
        "nx": 24,
        "ny": 24,
        "steps": 12,
        "sample_interval": 1,
        "mode_index": 1,
        "amplitude": 1.0e-5,
        "fit_start": 3,
        "directions": ["x"],
    }
    result = measure_thermal_diffusion(config)
    assert result["p2_05_status"] in {"PASSED", "FAILED"}
    assert result["directions"] == ["x"]
    assert result["mode_index"] == 1
    assert result["alpha_target_lu"] > 0.0
    assert "x" in result["direction_results"]
    assert result["direction_results"]["x"]["sample_count"] > 0
    assert result["clipping_used"] is False
