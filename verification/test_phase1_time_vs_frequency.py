import math

import numpy as np

from postproc.harmonic_fit import fit_complex_amplitude
from reference.continuum_1d_freq import solve_level_C_frequency
from reference.continuum_1d_time import run_level_C_time
from reference.constants import default_params, relative_error


def _phase_error_deg(value, expected):
    return abs(math.degrees(np.angle(value / expected)))


def test_level_C_periodic_time_reconstruction_matches_frequency():
    params = default_params()
    freq = solve_level_C_frequency(10_000.0, 1000.0, params.C_A, params=params)
    time = run_level_C_time(
        10_000.0,
        1000.0,
        params.C_A,
        params=params,
        n_warmup_cycles=10,
        n_fit_cycles=3,
        samples_per_cycle=128,
    )

    n = 3 * 128
    t = time.t[-n:]
    Ts_hat = fit_complex_amplitude(t, time.T_s[-n:], freq.Omega)
    q_hat = fit_complex_amplitude(t, time.q_g[-n:], freq.Omega)
    p_hat = fit_complex_amplitude(t, time.p_probe[-n:], freq.Omega)

    assert relative_error(Ts_hat, freq.T_s_hat) < 2.0e-2
    assert relative_error(q_hat, freq.q_g_hat) < 2.0e-2
    assert relative_error(p_hat, freq.p_at(8.0)) < 5.0e-2
    assert _phase_error_deg(Ts_hat, freq.T_s_hat) < 5.0
    assert _phase_error_deg(q_hat, freq.q_g_hat) < 5.0
    assert _phase_error_deg(p_hat, freq.p_at(8.0)) < 5.0
    assert np.sqrt(np.mean(time.energy_residual[-n:] ** 2)) / (1000.0 / math.sqrt(2.0)) < 1.0e-2

