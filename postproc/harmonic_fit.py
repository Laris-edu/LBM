"""Harmonic post-processing for Phase 1 time-domain outputs."""

from __future__ import annotations

import math
import numpy as np

from reference.result_schema import HarmonicResult


def fit_complex_amplitude(t: np.ndarray, x: np.ndarray, Omega: float) -> complex:
    """Fit x_hat under x(t) = Re[x_hat exp(i Omega t)]."""

    t = np.asarray(t, dtype=float)
    x = np.asarray(x, dtype=float)
    return complex(2.0 * np.mean(x * np.exp(-1j * Omega * t)))


def fit_complex_amplitude_lstsq(t: np.ndarray, x: np.ndarray, Omega: float) -> complex:
    """Least-squares fit for non-integer periods or nonuniform sampling."""

    t = np.asarray(t, dtype=float)
    x = np.asarray(x, dtype=float)
    matrix = np.column_stack((np.cos(Omega * t), np.sin(Omega * t)))
    coeffs, *_ = np.linalg.lstsq(matrix, x, rcond=None)
    A, B = coeffs
    return complex(A - 1j * B)


def harmonic_summary(x_hat: complex) -> HarmonicResult:
    peak = abs(x_hat)
    rms = peak / math.sqrt(2.0)
    phase = math.atan2(float(np.imag(x_hat)), float(np.real(x_hat)))
    return HarmonicResult(
        x_hat=complex(x_hat),
        peak_abs=float(peak),
        rms_abs=float(rms),
        phase_rad=float(phase),
        phase_deg=float(math.degrees(phase)),
    )


def spl_db_from_p_hat(p_hat: complex, p_ref: float = 20.0e-6) -> float:
    p_rms = abs(p_hat) / math.sqrt(2.0)
    return float(20.0 * math.log10(p_rms / p_ref))


def last_cycles_mask(t: np.ndarray, f_hz: float, n_cycles: int) -> np.ndarray:
    t = np.asarray(t, dtype=float)
    start = t[-1] - n_cycles / f_hz
    return t >= start

