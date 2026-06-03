import math

import numpy as np

from core.unit_mapping import create_unit_mapping, physical_timestep_config
from phase3_interfaces.modal_fit import fit_phase_speed


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
    attenuation_status = "diagnostic_only_until_matched_NSF_bulk_policy_derivation"
    assert "diagnostic" in attenuation_status

