import numpy as np

from phase3_interfaces.modal_fit import modal_amplitude


def test_p2_8_modal_amplitude_consistent_for_x_y_and_diagonal_modes():
    n = 64
    mode = 2
    s = np.arange(n)
    k = 2.0 * np.pi * mode / n
    x_field = np.sin(k * s)[None, :] * np.ones((n, 1))
    y_field = np.sin(k * s)[:, None] * np.ones((1, n))
    diag_field = np.zeros((n, n))
    for i in range(n):
        diag_field[i, i] = np.sin(k * i)
    ax = abs(modal_amplitude(x_field, mode, "x"))
    ay = abs(modal_amplitude(y_field, mode, "y"))
    ad = abs(modal_amplitude(diag_field, mode, "diagonal"))
    assert abs(ax - ay) < 1.0e-12
    assert abs(ax - ad) < 1.0e-12

