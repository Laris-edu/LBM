"""Modal amplitude, decay and phase-speed fitting helpers."""

from __future__ import annotations

import numpy as np


def modal_amplitude(field, mode_index: int, direction: str = "x") -> complex:
    """Return ``A`` for ``field'(s) ~= Re[A exp(i k s)]``.

    Normalization is ``A = 2/N * sum_s field'(s) exp(-i k s)``.
    """

    arr = np.asarray(field, dtype=float)
    if direction == "x":
        profile = np.mean(arr, axis=0) if arr.ndim == 2 else arr
    elif direction == "y":
        profile = np.mean(arr, axis=1) if arr.ndim == 2 else arr
    elif direction == "diagonal":
        if arr.ndim != 2:
            profile = arr
        else:
            n = min(arr.shape)
            profile = np.asarray([arr[i, i] for i in range(n)], dtype=float)
    else:
        raise ValueError("direction must be x, y, or diagonal")
    profile = np.asarray(profile, dtype=float)
    profile = profile - np.mean(profile)
    n = profile.size
    s = np.arange(n, dtype=float)
    k = 2.0 * np.pi * int(mode_index) / n
    return complex((2.0 / n) * np.sum(profile * np.exp(-1j * k * s)))


def fit_exponential_decay(t, amplitudes, *, start: float | None = None, stop: float | None = None) -> tuple[float, float]:
    t = np.asarray(t, dtype=float)
    amplitudes = np.asarray(amplitudes, dtype=complex)
    mask = np.ones_like(t, dtype=bool)
    if start is not None:
        mask &= t >= start
    if stop is not None:
        mask &= t <= stop
    y = np.log(np.maximum(np.abs(amplitudes[mask]), 1.0e-300))
    matrix = np.column_stack((np.ones(np.count_nonzero(mask)), t[mask]))
    coeffs, *_ = np.linalg.lstsq(matrix, y, rcond=None)
    intercept, slope = coeffs
    return float(-slope), float(intercept)


def fit_phase_speed(t, amplitudes, k_lu: float) -> float:
    t = np.asarray(t, dtype=float)
    phase = np.unwrap(np.angle(np.asarray(amplitudes, dtype=complex)))
    matrix = np.column_stack((np.ones_like(t), t))
    coeffs, *_ = np.linalg.lstsq(matrix, phase, rcond=None)
    omega = coeffs[1]
    return float(omega / k_lu)

