"""Boundary mass/state audit tool (Phase_5 WP1-3; G1-W metrics, contract §6.1).

Wraps ANY bottom-wall ``boundary_callback`` and records, at the callback
instant of every step:

- the net mass change caused by the wall operation (full-field sum of ``f``
  before vs after the wrapped callback) — the wall's mass source, complete by
  construction (row rewrites, deep links, everything the callback touches);
- the post-callback wall-row mean normal/tangential velocity (impermeability
  and no-slip metrics);
- the post-callback wall-row mean temperature (wall-temperature realization).

Normalization (archived here per contract §6.1 "定义和归一化必须进入报告"):

    dm_rel(t)   = [M_after(t) - M_before(t)] / (rho_ref_lu * nx)
                  -> net wall-operation mass change per step, per wall column,
                     in units of the reference density; with dt_lu = dx_lu = 1
                     this is the dimensionless instantaneous normal mass flux
                     m_dot/(rho_ref * c_lattice) at the wall.
    u/c0        -> row-0 mean velocity divided by c0_lu = sqrt(theta_ref_lu)
                  (isothermal lattice sound scale; the sqrt(gamma)=1.18 factor
                   is immaterial at the 1e-8 gate level and is documented, not
                   hidden).

``harmonic_components`` fits the 0f..3f content of any recorded series with
the frozen multiharmonic fitter (detrend order 0; the a0 trend coefficient is
the 0f/DC component). This tool takes no side on which wall passes G1-W — it
is the measuring instrument for both the frozen ``pressure_preserving``
diagnostic wall and the mass-neutral production candidate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from core.macroscopic import recover_macro
from postproc.multiharmonic_fit import fit_multiharmonic

NORMALIZATION_DEFINITION = (
    "dm_rel = (M_after - M_before)_callback / (rho_ref_lu * nx): net wall-operation "
    "mass change per step per wall column in reference-density units "
    "(= dimensionless normal mass flux for dt_lu=dx_lu=1); velocities are row-0 "
    "means divided by c0_lu = sqrt(theta_ref_lu)."
)


@dataclass
class WallAuditRecorder:
    """Per-step record of wall mass source and wall-row state."""

    steps: list[int] = field(default_factory=list)
    dm_rel: list[float] = field(default_factory=list)
    u_normal_over_c0: list[float] = field(default_factory=list)
    u_tangential_over_c0: list[float] = field(default_factory=list)
    theta_wall_lu: list[float] = field(default_factory=list)
    mass_before_first: float | None = None
    mass_after_last: float | None = None
    cumulative_dm: float = 0.0

    def as_arrays(self) -> dict[str, np.ndarray]:
        return {
            "steps": np.asarray(self.steps, dtype=float),
            "dm_rel": np.asarray(self.dm_rel, dtype=float),
            "u_normal_over_c0": np.asarray(self.u_normal_over_c0, dtype=float),
            "u_tangential_over_c0": np.asarray(self.u_tangential_over_c0, dtype=float),
            "theta_wall_lu": np.asarray(self.theta_wall_lu, dtype=float),
        }

    def cumulative_mass_drift_rel(self) -> float:
        """|sum of wall-attributed mass changes| / initial total mass."""

        if self.mass_before_first is None or self.mass_before_first == 0.0:
            return float("nan")
        return abs(self.cumulative_dm) / abs(self.mass_before_first)


def make_mass_audited_callback(inner_callback, recorder: WallAuditRecorder):
    """Wrap ``inner_callback`` so every invocation is mass/state audited."""

    def _callback(*, solver, f_post, g_post, f_stream, g_stream):
        mass_before = float(np.sum(f_stream))
        f_new, g_new = inner_callback(
            solver=solver, f_post=f_post, g_post=g_post,
            f_stream=f_stream, g_stream=g_stream,
        )
        mass_after = float(np.sum(f_new))

        lattice = solver.lattice
        macro = recover_macro(
            f_new[0:1], g_new[0:1],
            D=int(solver.mapping.lattice.D), S=int(solver.mapping.lattice.S),
            lattice=lattice,
        )
        c0_lu = math.sqrt(float(solver.mapping.theta_ref_lu))
        rho_ref = float(solver.mapping.lattice.rho_ref_lu)
        nx = f_new.shape[1]

        if recorder.mass_before_first is None:
            recorder.mass_before_first = mass_before
        recorder.mass_after_last = mass_after
        recorder.cumulative_dm += mass_after - mass_before
        recorder.steps.append(int(solver.t_lu))
        recorder.dm_rel.append((mass_after - mass_before) / (rho_ref * nx))
        recorder.u_normal_over_c0.append(float(np.mean(macro.u[..., 1])) / c0_lu)
        recorder.u_tangential_over_c0.append(float(np.mean(macro.u[..., 0])) / c0_lu)
        recorder.theta_wall_lu.append(float(np.mean(macro.theta)))
        return f_new, g_new

    return _callback


def harmonic_components(
    recorder: WallAuditRecorder,
    series: str,
    *,
    dt_s: float,
    frequency_hz: float,
    settle_periods: float = 1.0,
    n_harmonics: int = 3,
) -> dict:
    """0f..3f components of a recorded series (0f = |a0| of the detrend-0 fit).

    Returns absolute component magnitudes in the series' own normalized units
    plus the fit payload; the caller compares against the contract thresholds
    (e.g. G1-W: normalized net mass-flux components 0f-3f <= 1e-10).
    """

    arrays = recorder.as_arrays()
    if series not in arrays:
        raise ValueError(f"unknown series {series!r}")
    t = arrays["steps"] * float(dt_s)
    x = arrays[series]
    mask = t >= settle_periods / float(frequency_hz) * (1.0 - 1e-12)
    if int(np.sum(mask)) < 2 * (2 * n_harmonics + 1):
        raise ValueError("audit window too short for the harmonic fit")
    omega = 2.0 * math.pi * float(frequency_hz)
    fit = fit_multiharmonic(t[mask], x[mask], omega, n_harmonics=n_harmonics, detrend_order=0)
    components = {0: abs(float(fit.trend_coeffs_raw[0]))}
    for n in range(1, n_harmonics + 1):
        components[n] = fit.amplitude(n)
    return {
        "series": series,
        "components": components,
        "max_component": max(components.values()),
        "normalization": NORMALIZATION_DEFINITION,
        "fit": fit,
    }
