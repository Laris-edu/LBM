"""Periodic spectral response corrections for Phase 2 transport closures.

P4-1b (route b', user-approved 2026-07-04): the corrections are global periodic FFT
operators; boundary-row impositions (bottom wall / open top) make the y-profile of the
input moment fields kinked and wrap-discontinuous, and the correction multiplier turns
that broadband leakage into a delocalized wave injection every step (the P4-1
volume-injection floor, ``docs/Phase_4/M4/P4_1_Open_Boundary_Diagnostic_Report.md``).
Two seam-aware mechanisms exist, each matched to its operator's role (project doc
``P4_1b_Seam_Detrend_Project.md`` section 6):

1. ``boundary_rows`` on the correction functions -- boundary-row SUBSTITUTION
   (:func:`_apply_boundary_substituted`): imposed rows are replaced in the spectral
   input by a gain-1 zero-gradient continuation and excluded from the masked,
   moment-conserving delta. Corrections keep FULL strength on every free row.
2. :func:`seam_aware_boundary_window` -- the tapered window, used by the biharmonic
   FILTER only (top side only, wired in ``core/solver.py``): it severs the filter's
   wrap coupling while the bottom wall rows keep full grid-scale damping.

Refuted intermediates (details in the project doc sections 5-6): wrap-jump-only detrend
(x0.66 -- interior imposition kinks dominate); two-sided tapered window on the
corrections (taper rows lose the target<1 high-k damping the Grad-wall loop relies on;
the Level A rig went NaN over the 1e5-step horizon with windowed AND frozen filter).

Defaults (``boundary_rows=None`` / zero strip scalars) keep frozen behavior bit-identical.
"""

from __future__ import annotations

import numpy as np

_WINDOW_CACHE: dict[tuple[int, int, int, int], np.ndarray] = {}


def seam_aware_boundary_window(
    ny: int,
    bottom_rows: int,
    top_rows: int,
    taper_rows: int,
) -> np.ndarray | None:
    """Return the cached (ny,) seam-aware window, or None when disabled (all zeros)."""

    bottom_rows = int(bottom_rows)
    top_rows = int(top_rows)
    taper_rows = int(taper_rows)
    if bottom_rows <= 0 and top_rows <= 0:
        return None
    key = (int(ny), bottom_rows, top_rows, taper_rows)
    cached = _WINDOW_CACHE.get(key)
    if cached is not None:
        return cached
    if bottom_rows + top_rows + 2 * taper_rows >= ny:
        raise ValueError("seam-aware window leaves no interior rows (ny too small)")
    w = np.ones(int(ny), dtype=float)

    def _ramp(i: int) -> float:
        # C2 smootherstep of the raised cosine: steeper spectral skirts than the bare
        # C1 cosine, so the taper's own modulation of smooth physics stays further
        # below the correction band (the residual leakage channel of windowing).
        s = 0.5 * (1.0 - np.cos(np.pi * (i + 1) / (taper_rows + 1)))
        return s * s * (3.0 - 2.0 * s)

    if bottom_rows > 0:
        w[:bottom_rows] = 0.0
        for i in range(taper_rows):
            w[bottom_rows + i] = _ramp(i)
    if top_rows > 0:
        w[ny - top_rows:] = 0.0
        for i in range(taper_rows):
            w[ny - top_rows - 1 - i] = _ramp(i)
    _WINDOW_CACHE[key] = w
    return w


def _apply_windowed(arr: np.ndarray, window: np.ndarray, spectral_core) -> np.ndarray:
    """Seam-aware application: taper -> correct -> masked, moment-conserving delta."""

    w = window.reshape((arr.shape[0],) + (1,) * (arr.ndim - 1))
    mean = np.mean(arr, axis=(0, 1), keepdims=True)
    psi = mean + w * (arr - mean)
    delta = w * (spectral_core(psi) - psi)
    # exact global-moment conservation: remove the w-weighted mean of the masked delta
    total = np.sum(delta, axis=(0, 1), keepdims=True)
    delta = delta - w * (total / (np.sum(window) * arr.shape[1]))
    return arr + delta


def _apply_boundary_substituted(arr: np.ndarray, bottom_rows: int, top_rows: int, spectral_core) -> np.ndarray:
    """Boundary-row SUBSTITUTION form for the FFT corrections (P4-1b final design).

    The imposed boundary rows are replaced in the spectral-analysis input ``psi`` by a
    zero-gradient continuation of the adjacent interior row (gain-1, no taper), so the
    imposition kinks never enter the FFT; the correction delta is masked off the
    substituted rows (they are wholly re-imposed by the boundary callbacks every step)
    and recentered for exact global-moment conservation. Unlike the tapered-WINDOW form
    (kept for the filter), this leaves the corrections at FULL strength on every free
    interior row -- the bottom-tapered window removed the corrections' target<1 high-k
    damping exactly where the Grad-wall loop relies on it, and the Level A rig went NaN
    over the 1e5-step horizon (twice: with windowed and with frozen filter).
    """

    ny = arr.shape[0]
    if bottom_rows + top_rows + 4 >= ny:
        raise ValueError("boundary substitution leaves no interior rows (ny too small)")
    psi = arr.copy()
    if bottom_rows > 0:
        psi[:bottom_rows] = arr[bottom_rows]
    if top_rows > 0:
        psi[ny - top_rows:] = arr[ny - top_rows - 1]
    # Substitution alone leaves the WRAP jump of psi (bottom-local vs top-local values,
    # e.g. hot thermal-boundary-layer rows against the quiescent far field) fully in the
    # spectrum -- the dynamic injection ran right back to the frozen baseline without
    # this. Detrend psi's excess wrap jump with the gain-1 zero-mean sawtooth (the trend
    # passes through the correction untouched); smooth periodic fields have
    # J = O(dy^3 d3f) ~ 0 and are unaffected.
    jump = (psi[0] - psi[-1]) - 0.5 * ((psi[1] - psi[0]) + (psi[-1] - psi[-2]))
    sawtooth = -(np.arange(ny, dtype=float) - 0.5 * (ny - 1)) / ny
    trend = sawtooth.reshape((ny,) + (1,) * (arr.ndim - 1)) * jump[None, ...]
    psi_smooth = psi - trend
    delta = (spectral_core(psi_smooth) + trend) - psi
    mask = np.ones(ny, dtype=float)
    if bottom_rows > 0:
        mask[:bottom_rows] = 0.0
    if top_rows > 0:
        mask[ny - top_rows:] = 0.0
    m = mask.reshape((ny,) + (1,) * (arr.ndim - 1))
    delta = m * delta
    total = np.sum(delta, axis=(0, 1), keepdims=True)
    delta = delta - m * (total / (np.sum(mask) * arr.shape[1]))
    return arr + delta


def apply_periodic_spectral_correction(
    field: np.ndarray,
    *,
    enabled: bool,
    target: float,
    low_laplacian: float,
    high_laplacian: float,
    boundary_rows: tuple[int, int] | None = None,
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

    def _core(a: np.ndarray) -> np.ndarray:
        ny, nx = a.shape[:2]
        ky = 2.0 * np.pi * np.fft.fftfreq(ny)
        kx = 2.0 * np.pi * np.fft.fftfreq(nx)
        mu_y = 4.0 * np.sin(0.5 * ky) ** 2
        mu_x = 4.0 * np.sin(0.5 * kx) ** 2
        mu = mu_y[:, None] + mu_x[None, :]
        ramp = np.clip((mu - low_laplacian) / (high_laplacian - low_laplacian), 0.0, 1.0)
        smooth = ramp * ramp * (3.0 - 2.0 * ramp)
        multiplier = 1.0 + (float(target) - 1.0) * smooth
        while multiplier.ndim < a.ndim:
            multiplier = multiplier[..., None]
        spectrum = np.fft.fftn(a, axes=(0, 1))
        return np.real_if_close(np.fft.ifftn(spectrum * multiplier, axes=(0, 1)), tol=1000).real

    if boundary_rows is None or (boundary_rows[0] <= 0 and boundary_rows[1] <= 0):
        return _core(arr)
    return _apply_boundary_substituted(arr, int(boundary_rows[0]), int(boundary_rows[1]), _core)


def apply_periodic_diagonal_low_mode_correction(
    field: np.ndarray,
    *,
    enabled: bool,
    target: float,
    low_laplacian: float,
    boundary_rows: tuple[int, int] | None = None,
) -> np.ndarray:
    """Apply a multiplier only to low-k diagonal periodic modes.

    This is intentionally separate from the high-wavenumber smoothstep
    correction: D2Q37 diagonal mode=1 sits on the current low-laplacian
    boundary, so the generic dispersion correction preserves it exactly.
    """

    arr = np.asarray(field, dtype=float)
    if (
        not enabled
        or arr.ndim < 2
        or arr.shape[0] < 2
        or arr.shape[1] < 2
        or target == 1.0
        or low_laplacian <= 0.0
    ):
        return arr

    def _core(a: np.ndarray) -> np.ndarray:
        ny, nx = a.shape[:2]
        ky = 2.0 * np.pi * np.fft.fftfreq(ny)
        kx = 2.0 * np.pi * np.fft.fftfreq(nx)
        mu_y = 4.0 * np.sin(0.5 * ky) ** 2
        mu_x = 4.0 * np.sin(0.5 * kx) ** 2
        mu = mu_y[:, None] + mu_x[None, :]
        diagonal = (np.abs(ky)[:, None] > 0.0) & (np.abs(kx)[None, :] > 0.0)
        low = mu <= float(low_laplacian) * (1.0 + 1.0e-12)
        multiplier = np.where(diagonal & low, float(target), 1.0)
        while multiplier.ndim < a.ndim:
            multiplier = multiplier[..., None]
        spectrum = np.fft.fftn(a, axes=(0, 1))
        return np.real_if_close(np.fft.ifftn(spectrum * multiplier, axes=(0, 1)), tol=1000).real

    if boundary_rows is None or (boundary_rows[0] <= 0 and boundary_rows[1] <= 0):
        return _core(arr)
    return _apply_boundary_substituted(arr, int(boundary_rows[0]), int(boundary_rows[1]), _core)
