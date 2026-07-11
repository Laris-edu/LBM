import math

import numpy as np

from reference.analytical_models import (
    mcdonald_wetsel_like,
    pressure_profile_from_exponential_temperature,
)
from reference.continuum_1d_freq import (
    solve_level_A_frequency,
    solve_level_B_frequency,
    solve_level_C_frequency,
)
from reference.constants import default_params, relative_error


def _phase_error_deg(value, expected):
    return abs(math.degrees(np.angle(value / expected)))


def _assert_pressure_matches(result, reference):
    p_ref = reference["p_hat"][result.probe_index(8.0)]
    p_num = result.p_at(8.0)
    assert relative_error(p_num, p_ref) < 5.0e-2
    assert _phase_error_deg(p_num, p_ref) < 5.0
    assert relative_error(result.T_at(1.0), reference["T_hat"][result.probe_index(1.0)]) < 2.0e-2
    assert relative_error(result.q_g_hat, reference["q_g_hat"]) < 2.0e-2


def test_pressure_temperature_coupling_level_A_B_C():
    params = default_params()

    cases = [
        (
            solve_level_A_frequency(10_000.0, 1.0, params=params),
            {"T_s_hat": 1.0},
        ),
        (
            solve_level_B_frequency(10_000.0, 1000.0, params=params),
            {"q_hat": 1000.0},
        ),
        (
            solve_level_C_frequency(10_000.0, 1000.0, params.C_A, params=params),
            {"P_hat": 1000.0, "C_A": params.C_A},
        ),
    ]

    for result, kwargs in cases:
        reference = mcdonald_wetsel_like(
            10_000.0,
            y=result.probes_y,
            params=params,
            **kwargs,
        )
        _assert_pressure_matches(result, reference)


def test_halfspace_velocity_satisfies_impermeable_wall():
    params = default_params()
    p_hat, u_hat = pressure_profile_from_exponential_temperature(
        10_000.0,
        1.0 + 0.0j,
        np.asarray([0.0]),
        params,
    )

    assert abs(p_hat[0]) > 0.0
    assert abs(u_hat[0]) < 1.0e-14
