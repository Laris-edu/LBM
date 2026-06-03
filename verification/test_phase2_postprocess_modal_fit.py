import math

import numpy as np

from phase3_interfaces.complex_amplitude import complex_amplitude, spl_db_from_p_hat
from phase3_interfaces.modal_fit import fit_exponential_decay, fit_phase_speed, modal_amplitude


def test_postprocess_complex_amplitude_phase_speed_decay_and_spl():
    f_hz = 10_000.0
    omega = 2.0 * math.pi * f_hz
    t = np.linspace(0.0, 10.0 / f_hz, 1000, endpoint=False)
    x_hat = 2.0 - 0.5j
    signal = np.real(x_hat * np.exp(1j * omega * t))
    fitted = complex_amplitude(t, signal, f_hz)
    assert abs(fitted - x_hat) < 1.0e-12

    n = 64
    mode = 3
    s = np.arange(n)
    k = 2.0 * np.pi * mode / n
    field = np.sin(k * s)
    assert abs(abs(modal_amplitude(field, mode, "x")) - 1.0) < 1.0e-12

    decay_target = 0.003
    times = np.arange(100, dtype=float)
    amps = np.exp(-decay_target * times) * np.exp(1j * 0.02 * times)
    decay, _ = fit_exponential_decay(times, amps)
    assert abs(decay - decay_target) < 1.0e-12
    assert abs(fit_phase_speed(times, amps, 0.1) - 0.2) < 1.0e-12

    assert math.isclose(spl_db_from_p_hat(math.sqrt(2.0) * 20.0e-6), 0.0, abs_tol=1.0e-12)

