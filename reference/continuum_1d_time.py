"""Time-domain Phase 1 reference utilities.

The sinusoidal routines reconstruct the exact periodic response of the
frequency-domain reference. This gives a strict time-series check of the
post-processing, energy residual, and phase conventions before heavier NSF
time marching is introduced.
"""

from __future__ import annotations

import math
import numpy as np

from .constants import PhysicalParams, default_params, omega_from_frequency
from .continuum_1d_freq import (
    solve_level_A_frequency,
    solve_level_B_frequency,
    solve_level_C_frequency,
)
from .film_ode import energy_residual_time
from .result_schema import TimeSeriesResult


def _time_axis(
    f_hz: float,
    *,
    n_warmup_cycles: int = 10,
    n_fit_cycles: int = 3,
    samples_per_cycle: int = 120,
) -> np.ndarray:
    period = 1.0 / f_hz
    n_cycles = n_warmup_cycles + n_fit_cycles
    n_samples = n_cycles * samples_per_cycle
    return np.arange(n_samples, dtype=float) * period / samples_per_cycle


def _real_harmonic(x_hat: complex, Omega: float, t: np.ndarray) -> np.ndarray:
    return np.real(x_hat * np.exp(1j * Omega * t))


def _harmonic_result_to_time_series(
    result,
    *,
    n_warmup_cycles: int = 10,
    n_fit_cycles: int = 3,
    samples_per_cycle: int = 120,
    p_probe_y_over_delta_T: float = 8.0,
) -> TimeSeriesResult:
    t = _time_axis(
        result.f_Hz,
        n_warmup_cycles=n_warmup_cycles,
        n_fit_cycles=n_fit_cycles,
        samples_per_cycle=samples_per_cycle,
    )
    Omega = result.Omega
    P_hat = result.P_hat if result.P_hat is not None else 0.0 + 0.0j
    P_in = _real_harmonic(P_hat, Omega, t)
    T_s = _real_harmonic(result.T_s_hat, Omega, t)
    dT_s_dt = _real_harmonic(1j * Omega * result.T_s_hat, Omega, t)
    q_g = _real_harmonic(result.q_g_hat, Omega, t)
    p_probe = _real_harmonic(result.p_at(p_probe_y_over_delta_T), Omega, t)
    residual = energy_residual_time(
        P_in,
        q_g,
        T_s,
        dT_s_dt,
        C_A=result.C_A,
        beta0=result.beta0,
    )
    return TimeSeriesResult(
        case_name=result.case_name + "_time_periodic",
        level=result.level,
        f_Hz=result.f_Hz,
        Omega=Omega,
        t=t,
        T_s=T_s,
        q_g=q_g,
        p_probe=p_probe,
        P_in=P_in,
        energy_residual=residual,
        metadata={
            "time_model": "exact_periodic_reconstruction",
            "n_warmup_cycles": n_warmup_cycles,
            "n_fit_cycles": n_fit_cycles,
            "samples_per_cycle": samples_per_cycle,
            "p_probe_y_over_delta_T": p_probe_y_over_delta_T,
        },
    )


def run_level_A_time(
    f_hz: float,
    T_s_hat: complex,
    params: PhysicalParams | None = None,
    **kwargs: object,
) -> TimeSeriesResult:
    result = solve_level_A_frequency(f_hz, T_s_hat, params=params)
    return _harmonic_result_to_time_series(result, **kwargs)


def run_level_B_time(
    f_hz: float,
    q_hat: complex,
    params: PhysicalParams | None = None,
    **kwargs: object,
) -> TimeSeriesResult:
    result = solve_level_B_frequency(f_hz, q_hat, params=params)
    return _harmonic_result_to_time_series(result, **kwargs)


def run_level_C_time(
    f_hz: float = 10_000.0,
    P_hat: complex = 1000.0,
    C_A: float | None = None,
    params: PhysicalParams | None = None,
    *,
    beta0: float | None = None,
    **kwargs: object,
) -> TimeSeriesResult:
    result = solve_level_C_frequency(f_hz, P_hat, C_A=C_A, params=params, beta0=beta0)
    return _harmonic_result_to_time_series(result, **kwargs)


def run_level_C_step(
    *,
    P_bar: float = 1000.0,
    C_A: float = 7.0e-4,
    params: PhysicalParams | None = None,
    beta0: float = 0.0,
    f_ref_hz: float = 10_000.0,
    t_end: float | None = None,
    n_samples: int = 1000,
) -> TimeSeriesResult:
    """Reduced first-order Level C step reference for Phase 1 Fig.5 data."""

    params = params or default_params()
    Omega_ref = omega_from_frequency(f_ref_hz)
    delta_T_ref = math.sqrt(2.0 * params.alpha0 / Omega_ref)
    G_eff = 2.0 * params.kg / delta_T_ref + 2.0 * beta0
    tau = C_A / G_eff
    if t_end is None:
        t_end = 8.0 * tau
    t = np.linspace(0.0, t_end, n_samples)
    T_inf = P_bar / G_eff
    T_s = T_inf * (1.0 - np.exp(-t / tau))
    dT_s_dt = (T_inf / tau) * np.exp(-t / tau)
    P_in = np.full_like(t, P_bar)
    q_g = 0.5 * (P_in - C_A * dT_s_dt - 2.0 * beta0 * T_s)
    unit_pressure = solve_level_A_frequency(f_ref_hz, 1.0, params=params).p_at(8.0)
    pressure_derivative_gain = unit_pressure / (1j * Omega_ref)
    p_probe = float(np.real(pressure_derivative_gain)) * dT_s_dt
    residual = energy_residual_time(P_in, q_g, T_s, dT_s_dt, C_A=C_A, beta0=beta0)
    return TimeSeriesResult(
        case_name=f"phase1_levelC_step_CA_{C_A:g}",
        level="C-step",
        f_Hz=None,
        Omega=None,
        t=t,
        T_s=T_s,
        q_g=q_g,
        p_probe=p_probe,
        P_in=P_in,
        energy_residual=residual,
        metadata={
            "time_model": "first_order_effective_thermal_network",
            "pressure_model": "10k_small_signal_derivative_proxy",
            "tau_s": tau,
            "f_ref_hz": f_ref_hz,
        },
    )
