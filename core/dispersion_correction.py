"""Periodic spectral response corrections for Phase 2 transport closures."""

from __future__ import annotations

import numpy as np


def apply_periodic_spectral_correction(
    field: np.ndarray,
    *,
    enabled: bool,
    target: float,
    low_laplacian: float,
    high_laplacian: float,
) -> np.ndarray:
    """Apply a bounded high-wavenumber response multiplier on periodic fields.

    ``low_laplacian`` and ``high_laplacian`` are positive symbols of the
    negative periodic discrete Laplacian.  Modes at or below the low threshold
    are unchanged; modes at or above the high threshold are multiplied by
    ``target``.  A smoothstep ramp connects both limits.
    """

    arr = np.asarray(field, dtype=float)
    if (
        not enabled
        or arr.ndim < 2
        or arr.shape[0] < 2
        or arr.shape[1] < 2
        or target == 1.0
    ):
        return arr
    if high_laplacian <= low_laplacian:
        raise ValueError("high_laplacian must exceed low_laplacian")

    ny, nx = arr.shape[:2]
    ky = 2.0 * np.pi * np.fft.fftfreq(ny)
    kx = 2.0 * np.pi * np.fft.fftfreq(nx)
    mu_y = 4.0 * np.sin(0.5 * ky) ** 2
    mu_x = 4.0 * np.sin(0.5 * kx) ** 2
    mu = mu_y[:, None] + mu_x[None, :]
    ramp = np.clip((mu - low_laplacian) / (high_laplacian - low_laplacian), 0.0, 1.0)
    smooth = ramp * ramp * (3.0 - 2.0 * ramp)
    multiplier = 1.0 + (float(target) - 1.0) * smooth
    while multiplier.ndim < arr.ndim:
        multiplier = multiplier[..., None]

    spectrum = np.fft.fftn(arr, axes=(0, 1))
    corrected = np.fft.ifftn(spectrum * multiplier, axes=(0, 1))
    return np.real_if_close(corrected, tol=1000).real
