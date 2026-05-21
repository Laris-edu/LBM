import numpy as np

from reference.continuum_1d_freq import solve_level_C_frequency
from reference.constants import default_params


def _relative_variation(values):
    values = np.asarray(values, dtype=np.complex128)
    center = np.mean(values)
    return float(np.max(np.abs(values - center)) / max(abs(center), 1e-300))


def test_level_C_linear_power_scaling():
    params = default_params()
    powers = [100.0, 300.0, 1000.0, 3000.0]
    results = [
        solve_level_C_frequency(10_000.0, P, params.C_A, params=params)
        for P in powers
    ]

    Ts_ratios = [r.T_s_hat / P for r, P in zip(results, powers)]
    q_ratios = [r.q_g_hat / P for r, P in zip(results, powers)]
    p_ratios = [r.p_at(8.0) / P for r, P in zip(results, powers)]

    assert _relative_variation(Ts_ratios) < 5.0e-3
    assert _relative_variation(q_ratios) < 5.0e-3
    assert _relative_variation(p_ratios) < 5.0e-3

