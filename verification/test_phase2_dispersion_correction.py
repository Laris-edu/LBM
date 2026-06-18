import math

import numpy as np

from core.dispersion_correction import (
    apply_periodic_diagonal_low_mode_correction,
    apply_periodic_spectral_correction,
)


def _mode_field(nx: int, ny: int, mode: int) -> np.ndarray:
    x = np.arange(nx, dtype=float)
    phase = 2.0 * np.pi * mode * x / nx
    return np.broadcast_to(np.sin(phase), (ny, nx)).copy()


def _diagonal_mode_field(nx: int, ny: int, mode: int) -> np.ndarray:
    x = np.arange(nx, dtype=float)
    y = np.arange(ny, dtype=float)
    phase = 2.0 * np.pi * mode * x[None, :] / nx + 2.0 * np.pi * mode * y[:, None] / ny
    return np.sin(phase)


def _mode_amplitude(field: np.ndarray, mode: int) -> float:
    ny, nx = field.shape
    x = np.arange(nx, dtype=float)
    phase = 2.0 * np.pi * mode * x / nx
    return float((2.0 / field.size) * np.sum(field * np.sin(phase)))


def _diagonal_mode_amplitude(field: np.ndarray, mode: int) -> float:
    ny, nx = field.shape
    x = np.arange(nx, dtype=float)
    y = np.arange(ny, dtype=float)
    phase = 2.0 * np.pi * mode * x[None, :] / nx + 2.0 * np.pi * mode * y[:, None] / ny
    return float((2.0 / field.size) * np.sum(field * np.sin(phase)))


def test_dispersion_correction_preserves_low_mode_and_targets_high_mode():
    nx = ny = 64
    low = 2.0 * 4.0 * math.sin(math.pi / nx) ** 2
    high = 4.0 * math.sin(2.0 * math.pi / nx) ** 2
    target = 0.32

    low_field = _mode_field(nx, ny, 1)
    high_field = _mode_field(nx, ny, 2)
    low_corrected = apply_periodic_spectral_correction(
        low_field,
        enabled=True,
        target=target,
        low_laplacian=low,
        high_laplacian=high,
    )
    high_corrected = apply_periodic_spectral_correction(
        high_field,
        enabled=True,
        target=target,
        low_laplacian=low,
        high_laplacian=high,
    )

    assert math.isclose(_mode_amplitude(low_corrected, 1), 1.0, rel_tol=0.0, abs_tol=1.0e-12)
    assert math.isclose(_mode_amplitude(high_corrected, 2), target, rel_tol=0.0, abs_tol=1.0e-12)


def test_diagonal_low_mode_correction_only_targets_low_diagonal_modes():
    nx = ny = 64
    low = 2.0 * 4.0 * math.sin(math.pi / nx) ** 2
    target = 0.61

    x_field = _mode_field(nx, ny, 1)
    diagonal_field = _diagonal_mode_field(nx, ny, 1)
    x_corrected = apply_periodic_diagonal_low_mode_correction(
        x_field,
        enabled=True,
        target=target,
        low_laplacian=low,
    )
    diagonal_corrected = apply_periodic_diagonal_low_mode_correction(
        diagonal_field,
        enabled=True,
        target=target,
        low_laplacian=low,
    )

    assert math.isclose(_mode_amplitude(x_corrected, 1), 1.0, rel_tol=0.0, abs_tol=1.0e-12)
    assert math.isclose(
        _diagonal_mode_amplitude(diagonal_corrected, 1),
        target,
        rel_tol=0.0,
        abs_tol=1.0e-12,
    )
