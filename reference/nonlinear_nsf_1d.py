"""Phase_5 independent nonlinear 1D NSF reference solver (contract §8, WP1-2).

Fully nonlinear compressible Navier-Stokes-Fourier in 1D, conservative
finite-volume form with true time marching of mass, momentum and total energy:

    d(rho)/dt + d(rho u)/dy           = 0
    d(rho u)/dt + d(rho u^2 + p)/dy   = d(tau)/dy,        tau = mu_L du/dy
    d(E)/dt + d((E+p) u)/dy           = d(tau u - q)/dy,  q = -k(T) dT/dy

with ideal-gas EOS ``p = rho R T``, ``E = rho (cv T + u^2/2)`` and longitudinal
viscosity ``mu_L = 4/3 mu(T) + mu_bulk``. Discretization: uniform cell-centered
grid, second-order central fluxes (low dissipation — no shock-capturing per
contract §8.1; grid-scale modes are damped by the *physical* diffusivities),
classical RK4 in time with boundary fluxes accumulated under the same RK
weights so the mass/energy audits telescope to machine precision.

Thermodynamic closure: ``R = p0/(rho0 T0)`` and ``cv = cp - R`` are derived
from the frozen ``PhysicalParams`` so the initial state is an exact discrete
equilibrium; ``gamma_eff = cp/cv`` (=1.3996 for frozen air values, 0.03% from
the nominal 1.4 — documented, not hidden).

Boundaries (contract §8.1):
- wall (y=0): impermeable no-slip with **zero normal mass flux by
  construction** (convective wall flux is exactly [0, p_w, 0]) — the 1D solid
  wall that serves as G1-W's independent physical reference;
- lid (y=H): impermeable no-slip isothermal reservoir ``T(H)=T_ambient`` —
  the canonical DC heat sink (contract §3.3).

Wall thermal drive (A1/A2a/A2b protocols, §3): ``kind="temperature"``
(prescribed T_w(t), G1a-analog), ``kind="flux"`` (prescribed conductive heat
flux q''(t), signed zero-mean allowed = A1), ``kind="film"`` (film ODE
``C_A dT_s/dt = P(t) - 2 q''`` coupled inside the RK stages; the factor 2 is
the frozen freestanding double-sided convention).

Dual property branches (contract §2.3): ``lbm_equivalent_transport``
(reference-state constant transport = Route B closure; replace with the
G0-measured law via ``power_law_transport`` once G0 runs) and
``physical_air_transport`` (Sutherland-shape mu(T)/k(T) **anchored to the
frozen values at T0** so both branches coincide at the reference state and
``Delta_prop`` ablations are not polluted by a reference-point offset).

Complex amplitudes are extracted with ``postproc.multiharmonic_fit`` (frozen
convention ``x(t)=Re[x_hat e^{+i n Omega t}]``, shared per contract §8.1).

Closed-box linear anchor (used by ``linear_admittance_fixture``): with a
compact box (kH<<1) the uniform pressure oscillation feeds temperature
``T_p_hat = p_hat/(rho0 cp)`` back into the bulk, so the exact linear wall
flux is ``q_hat = Y_hs (T_s_hat - T_p_hat)`` with the Phase_1 half-space
admittance ``Y_hs = k m_T``. The fixture therefore reports both the raw and
the pressure-work-corrected admittance against the Phase_1 single source
(``reference.thermal_admittance``); the correction uses only measured in-run
quantities (no tuning).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from postproc.multiharmonic_fit import fit_multiharmonic
from reference.constants import PhysicalParams, default_params, omega_from_frequency
from reference.thermal_admittance import thermal_admittance_halfspace

__all__ = [
    "SOLVER_ID",
    "TransportModel",
    "lbm_equivalent_transport",
    "physical_air_transport",
    "power_law_transport",
    "WallDrive",
    "NSF1DConfig",
    "NSF1DResult",
    "run_nsf1d",
    "run_nsf1d_from_state",
    "equilibrium_fixture",
    "linear_admittance_fixture",
    "acoustic_ringdown_fixture",
    "antisymmetric_pair_fixture",
]

SOLVER_ID = "nonlinear_nsf_1d_fv_central_rk4_v1"


# --------------------------------------------------------------------------
# transport property branches (contract §2.3)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class TransportModel:
    """Temperature-dependent transport law mu(T), k(T) with archived model id."""

    property_model_id: str
    kind: str  # "constant" | "power_law" | "sutherland_anchored"
    mu_ref: float
    k_ref: float
    T_ref: float
    mu_exponent: float = 0.0
    k_exponent: float = 0.0
    sutherland_S_mu: float = 110.4
    sutherland_S_k: float = 194.0

    def mu(self, T: np.ndarray | float) -> np.ndarray | float:
        if self.kind == "constant":
            return self.mu_ref * np.ones_like(np.asarray(T, dtype=float))
        if self.kind == "power_law":
            return self.mu_ref * (np.asarray(T, dtype=float) / self.T_ref) ** self.mu_exponent
        if self.kind == "sutherland_anchored":
            T = np.asarray(T, dtype=float)
            s = self.sutherland_S_mu
            return self.mu_ref * (T / self.T_ref) ** 1.5 * (self.T_ref + s) / (T + s)
        raise ValueError(f"unknown transport kind {self.kind!r}")

    def k(self, T: np.ndarray | float) -> np.ndarray | float:
        if self.kind == "constant":
            return self.k_ref * np.ones_like(np.asarray(T, dtype=float))
        if self.kind == "power_law":
            return self.k_ref * (np.asarray(T, dtype=float) / self.T_ref) ** self.k_exponent
        if self.kind == "sutherland_anchored":
            T = np.asarray(T, dtype=float)
            s = self.sutherland_S_k
            return self.k_ref * (T / self.T_ref) ** 1.5 * (self.T_ref + s) / (T + s)
        raise ValueError(f"unknown transport kind {self.kind!r}")


def lbm_equivalent_transport(params: PhysicalParams) -> TransportModel:
    """Route-B reference-state closure: constant transport frozen at T0."""

    return TransportModel(
        property_model_id="1D-lbm-equivalent_reference_constant_v1",
        kind="constant",
        mu_ref=params.mu,
        k_ref=params.kg,
        T_ref=params.T0,
    )


def physical_air_transport(params: PhysicalParams) -> TransportModel:
    """Real-air Sutherland-shape mu(T)/k(T), anchored to frozen values at T0.

    Shape constants S_mu=110.4 K, S_k=194 K (standard air Sutherland forms);
    anchoring at (params.mu, params.kg, params.T0) keeps both branches
    identical at the reference state so Delta_prop isolates the T-dependence.
    """

    return TransportModel(
        property_model_id="1D-physical_air_sutherland_anchored_T0_v1",
        kind="sutherland_anchored",
        mu_ref=params.mu,
        k_ref=params.kg,
        T_ref=params.T0,
    )


def power_law_transport(
    params: PhysicalParams,
    *,
    mu_exponent: float,
    k_exponent: float,
    property_model_id: str,
) -> TransportModel:
    """General anchored power law — hook for the G0-measured effective law."""

    return TransportModel(
        property_model_id=property_model_id,
        kind="power_law",
        mu_ref=params.mu,
        k_ref=params.kg,
        T_ref=params.T0,
        mu_exponent=mu_exponent,
        k_exponent=k_exponent,
    )


# --------------------------------------------------------------------------
# drive protocols (contract §3)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class WallDrive:
    """Wall thermal protocol.

    kind="temperature": T_w(t) = T0 + ramp * (mean + amplitude cos(Omega t + phase))
                        (mean != 0 -> DC operating-point offset, the A2a-lite
                        prescribed-Theta_DC protocol: state matching by construction)
    kind="flux":        q''(t) = ramp * (mean + amplitude cos(Omega t + phase))
                        (signed zero-mean allowed -> A1 numerical ablation)
    kind="film":        P(t)  = ramp * (mean + amplitude cos(Omega t + phase)),
                        C_A dT_s/dt = P - 2 q'' (freestanding double-sided).
    """

    kind: str
    frequency_hz: float
    amplitude: float
    mean: float = 0.0
    phase_rad: float = 0.0
    ramp_cycles: float = 2.0
    film_heat_capacity: float | None = None

    def __post_init__(self) -> None:
        if self.kind not in ("temperature", "flux", "film"):
            raise ValueError(f"unknown drive kind {self.kind!r}")
        if not (self.frequency_hz > 0.0 and math.isfinite(self.frequency_hz)):
            raise ValueError("frequency_hz must be positive and finite")
        if self.kind == "film" and not (
            self.film_heat_capacity is not None and self.film_heat_capacity > 0.0
        ):
            raise ValueError("film drive requires film_heat_capacity > 0")

    def ramp(self, t: float) -> float:
        if self.ramp_cycles <= 0.0:
            return 1.0
        t_ramp = self.ramp_cycles / self.frequency_hz
        if t >= t_ramp:
            return 1.0
        return 0.5 * (1.0 - math.cos(math.pi * t / t_ramp))

    def oscillation(self, t: float) -> float:
        """amplitude * cos(Omega t + phase) — zero-mean part."""

        omega = omega_from_frequency(self.frequency_hz)
        return self.amplitude * math.cos(omega * t + self.phase_rad)

    def forcing(self, t: float) -> float:
        """ramp * (mean + oscillation) — flux/film drive value."""

        return self.ramp(t) * (self.mean + self.oscillation(t))


# --------------------------------------------------------------------------
# configuration / result
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class NSF1DConfig:
    params: PhysicalParams
    transport: TransportModel
    drive: WallDrive
    height_m: float
    n_cells: int
    n_cycles: float
    samples_per_cycle: int = 64
    cfl_acoustic: float = 0.4
    cfl_diffusive: float = 0.4
    lid_temperature_K: float | None = None  # default: params.T0 (canonical sink)
    lid_bc: str = "isothermal"  # "isothermal" (canonical sink) | "adiabatic" (sealed symmetry plane)
    film_initial_temperature_K: float | None = None

    def __post_init__(self) -> None:
        if self.lid_bc not in ("isothermal", "adiabatic"):
            raise ValueError(f"unknown lid_bc {self.lid_bc!r}")
        if self.n_cells < 8:
            raise ValueError("n_cells must be >= 8")
        if not (self.height_m > 0.0):
            raise ValueError("height_m must be positive")
        if self.n_cycles <= 0.0:
            raise ValueError("n_cycles must be positive")
        if self.samples_per_cycle < 8:
            raise ValueError("samples_per_cycle must be >= 8")


@dataclass
class NSF1DResult:
    config: NSF1DConfig
    solver_id: str
    property_model_id: str
    dt: float
    steps_per_cycle: int
    n_steps: int
    t_samples: np.ndarray
    q_wall_conductive: np.ndarray
    q_wall_applied: np.ndarray
    wall_temperature: np.ndarray
    film_temperature: np.ndarray | None
    p_wall: np.ndarray
    p_box_mean: np.ndarray
    dp_max_rel: np.ndarray
    mass_series: np.ndarray
    max_mach: float
    y_centers: np.ndarray
    rho_final: np.ndarray
    u_final: np.ndarray
    T_final: np.ndarray
    mass_drift_rel: float
    energy_residual_rel_flux: float
    energy_residual_rel_total: float

    def metadata(self) -> dict:
        return {
            "solver_id": self.solver_id,
            "property_model_id": self.property_model_id,
            "wall_drive_kind": self.config.drive.kind,
            "frequency_Hz": self.config.drive.frequency_hz,
            "n_cells": self.config.n_cells,
            "height_m": self.config.height_m,
            "dt_s": self.dt,
            "steps_per_cycle": self.steps_per_cycle,
            "n_steps": self.n_steps,
            "mass_drift_rel": self.mass_drift_rel,
            "energy_residual_rel_flux": self.energy_residual_rel_flux,
            "energy_residual_rel_total": self.energy_residual_rel_total,
            "max_mach": self.max_mach,
        }


# --------------------------------------------------------------------------
# core solver
# --------------------------------------------------------------------------


def _rhs(
    rho: np.ndarray,
    mom: np.ndarray,
    etot: np.ndarray,
    t_s_film: float,
    t: float,
    *,
    cfg: NSF1DConfig,
    dy: float,
    R: float,
    cv: float,
    mu_bulk: float,
    lid_T: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, dict]:
    tr = cfg.transport
    drive = cfg.drive

    u = mom / rho
    T = (etot / rho - 0.5 * u * u) / cv
    p = rho * R * T

    # wall thermal state
    if drive.kind == "temperature":
        T_wall = cfg.params.T0 + drive.ramp(t) * (drive.mean + drive.oscillation(t))
    elif drive.kind == "film":
        T_wall = t_s_film
    else:
        T_wall = None  # flux kind: no prescribed wall temperature

    # ---- interior faces (vectorized) ----
    u_f = 0.5 * (u[:-1] + u[1:])
    T_f = 0.5 * (T[:-1] + T[1:])
    mu_l_f = 4.0 / 3.0 * tr.mu(T_f) + mu_bulk
    k_f = tr.k(T_f)
    tau_f = mu_l_f * (u[1:] - u[:-1]) / dy
    q_f = -k_f * (T[1:] - T[:-1]) / dy
    conv_mom = mom * u + p
    conv_e = (etot + p) * u
    f_rho = 0.5 * (mom[:-1] + mom[1:])
    f_mom = 0.5 * (conv_mom[:-1] + conv_mom[1:]) - tau_f
    f_e = 0.5 * (conv_e[:-1] + conv_e[1:]) - tau_f * u_f + q_f

    # ---- wall face (y=0): impermeable no-slip, zero normal mass flux ----
    p_w = 1.5 * p[0] - 0.5 * p[1]
    if drive.kind == "flux":
        q_applied = drive.forcing(t)
        k0 = float(tr.k(T[0]))
        T_wall_report = float(T[0] + q_applied * (0.5 * dy) / k0)
        mu_l_w = 4.0 / 3.0 * float(tr.mu(T_wall_report)) + mu_bulk
        q_wall = q_applied
        q_wall_cond = q_applied  # applied flux *is* the wall conductive flux
    else:
        k_wf = float(tr.k(0.5 * (T_wall + T[0])))
        mu_l_w = 4.0 / 3.0 * float(tr.mu(0.5 * (T_wall + T[0]))) + mu_bulk
        q_wall_cond = k_wf * (T_wall - T[0]) * 2.0 / dy  # = -k dT/dy|0+ one-sided
        q_wall = q_wall_cond
        T_wall_report = float(T_wall)
    tau_w = mu_l_w * (u[0] - 0.0) * 2.0 / dy
    f_mom_w = p_w - tau_w
    f_e_w = q_wall  # (E+p)u = 0 and tau*u = 0 at a no-slip wall

    # ---- lid face (y=H): impermeable no-slip isothermal reservoir, or an
    # adiabatic sealed symmetry plane (u=0, q=0 — the exact half-box analog of
    # a both-sides-driven sealed box; far-plane viscous detail immaterial at
    # the small amplitudes this mode is used for) ----
    p_l = 1.5 * p[-1] - 0.5 * p[-2]
    if cfg.lid_bc == "adiabatic":
        q_lid = 0.0
        mu_l_l = 4.0 / 3.0 * float(tr.mu(T[-1])) + mu_bulk
    else:
        k_lf = float(tr.k(0.5 * (lid_T + T[-1])))
        mu_l_l = 4.0 / 3.0 * float(tr.mu(0.5 * (lid_T + T[-1]))) + mu_bulk
        q_lid = -k_lf * (lid_T - T[-1]) * 2.0 / dy  # +y energy flux leaving through lid
    tau_l = mu_l_l * (0.0 - u[-1]) * 2.0 / dy
    f_mom_l = p_l - tau_l
    f_e_l = q_lid

    flux_rho = np.concatenate(([0.0], f_rho, [0.0]))
    flux_mom = np.concatenate(([f_mom_w], f_mom, [f_mom_l]))
    flux_e = np.concatenate(([f_e_w], f_e, [f_e_l]))

    d_rho = -(flux_rho[1:] - flux_rho[:-1]) / dy
    d_mom = -(flux_mom[1:] - flux_mom[:-1]) / dy
    d_e = -(flux_e[1:] - flux_e[:-1]) / dy

    if drive.kind == "film":
        p_in = drive.forcing(t)
        d_ts = (p_in - 2.0 * q_wall_cond) / float(drive.film_heat_capacity)
        net_power = p_in - q_wall_cond - q_lid  # film + simulated side; mirror side lost
    else:
        d_ts = 0.0
        net_power = q_wall - q_lid

    aux = {
        "q_wall_cond": float(q_wall_cond),
        "q_wall_applied": float(q_wall),
        "q_lid": float(q_lid),
        "T_wall": T_wall_report,
        "net_power": float(net_power),
        "abs_power": abs(float(q_wall)) + abs(float(q_lid)),
    }
    return d_rho, d_mom, d_e, d_ts, aux


def run_nsf1d_from_state(
    cfg: NSF1DConfig,
    rho_init: np.ndarray,
    u_init: np.ndarray,
    temp_init: np.ndarray,
) -> NSF1DResult:
    """Integrate from a caller-supplied initial (rho, u, T) state."""

    params = cfg.params
    R = params.p0 / (params.rho0 * params.T0)
    cv = params.cp - R
    if cv <= 0.0:
        raise ValueError("derived cv = cp - R must be positive; check params")
    gamma_eff = params.cp / cv
    mu_bulk = params.mu_bulk
    lid_T = params.T0 if cfg.lid_temperature_K is None else float(cfg.lid_temperature_K)

    n = cfg.n_cells
    rho_init = np.asarray(rho_init, dtype=float)
    u_init = np.asarray(u_init, dtype=float)
    temp_init = np.asarray(temp_init, dtype=float)
    if not (rho_init.shape == u_init.shape == temp_init.shape == (n,)):
        raise ValueError("initial state arrays must have shape (n_cells,)")
    dy = cfg.height_m / n
    y_centers = (np.arange(n, dtype=float) + 0.5) * dy

    c0 = math.sqrt(gamma_eff * R * params.T0)
    nu_l0 = (4.0 / 3.0 * float(cfg.transport.mu(params.T0)) + mu_bulk) / params.rho0
    alpha0 = float(cfg.transport.k(params.T0)) / (params.rho0 * params.cp)
    d_max = max(nu_l0, gamma_eff * alpha0)
    dt_a = cfg.cfl_acoustic * dy / c0
    dt_d = cfg.cfl_diffusive * dy * dy / (2.0 * d_max)
    dt_stable = min(dt_a, dt_d)
    period = 1.0 / cfg.drive.frequency_hz
    steps_per_cycle = int(
        math.ceil(math.ceil(period / dt_stable) / cfg.samples_per_cycle)
        * cfg.samples_per_cycle
    )
    dt = period / steps_per_cycle
    stride = steps_per_cycle // cfg.samples_per_cycle
    n_steps = int(round(cfg.n_cycles * steps_per_cycle))

    rho = rho_init.copy()
    mom = rho_init * u_init
    etot = rho_init * (cv * temp_init + 0.5 * u_init * u_init)
    t_s = (
        params.T0
        if cfg.film_initial_temperature_K is None
        else float(cfg.film_initial_temperature_K)
    )

    mass0 = float(np.sum(rho) * dy)
    energy0 = float(np.sum(etot) * dy)
    if cfg.drive.kind == "film":
        energy0 += float(cfg.drive.film_heat_capacity) * t_s
    p0_ref = params.rho0 * R * params.T0  # == params.p0 exactly by construction

    n_samples = n_steps // stride + 1
    t_samples = np.empty(n_samples)
    q_cond_s = np.empty(n_samples)
    q_appl_s = np.empty(n_samples)
    t_wall_s = np.empty(n_samples)
    t_film_s = np.empty(n_samples) if cfg.drive.kind == "film" else None
    p_wall_s = np.empty(n_samples)
    p_box_s = np.empty(n_samples)
    dp_max_s = np.empty(n_samples)
    mass_s = np.empty(n_samples)

    rhs_kwargs = dict(cfg=cfg, dy=dy, R=R, cv=cv, mu_bulk=mu_bulk, lid_T=lid_T)

    def _sample(idx: int, t: float) -> None:
        u = mom / rho
        temp = (etot / rho - 0.5 * u * u) / cv
        p = rho * R * temp
        _, _, _, _, aux = _rhs(rho, mom, etot, t_s, t, **rhs_kwargs)
        t_samples[idx] = t
        q_cond_s[idx] = aux["q_wall_cond"]
        q_appl_s[idx] = aux["q_wall_applied"]
        t_wall_s[idx] = aux["T_wall"]
        if t_film_s is not None:
            t_film_s[idx] = t_s
        p_wall_s[idx] = 1.5 * p[0] - 0.5 * p[1]
        p_box_s[idx] = float(np.mean(p))
        dp_max_s[idx] = float(np.max(np.abs(p - p0_ref)) / p0_ref)
        mass_s[idx] = float(np.sum(rho) * dy)

    def _guard(step: int) -> float:
        u = mom / rho
        temp = (etot / rho - 0.5 * u * u) / cv
        if not (
            np.all(np.isfinite(rho))
            and np.all(np.isfinite(mom))
            and np.all(np.isfinite(etot))
            and np.all(rho > 0.0)
            and np.all(temp > 0.0)
            and math.isfinite(t_s)
        ):
            raise RuntimeError(f"non-finite or non-physical state at step {step}")
        c_loc = np.sqrt(gamma_eff * R * temp)
        signal = float(np.max(np.abs(u) + c_loc))
        if dt * signal / dy > 1.0:
            raise RuntimeError(f"CFL guard exceeded at step {step}: dt*(|u|+c)/dy > 1")
        return float(np.max(np.abs(u) / c_loc))

    energy_in = 0.0
    abs_flux_int = 0.0
    max_mach = 0.0
    sample_idx = 0
    for step in range(n_steps):
        t = step * dt
        if step % stride == 0:
            _sample(sample_idx, t)
            sample_idx += 1
            max_mach = max(max_mach, _guard(step))

        k1 = _rhs(rho, mom, etot, t_s, t, **rhs_kwargs)
        k2 = _rhs(
            rho + 0.5 * dt * k1[0], mom + 0.5 * dt * k1[1], etot + 0.5 * dt * k1[2],
            t_s + 0.5 * dt * k1[3], t + 0.5 * dt, **rhs_kwargs,
        )
        k3 = _rhs(
            rho + 0.5 * dt * k2[0], mom + 0.5 * dt * k2[1], etot + 0.5 * dt * k2[2],
            t_s + 0.5 * dt * k2[3], t + 0.5 * dt, **rhs_kwargs,
        )
        k4 = _rhs(
            rho + dt * k3[0], mom + dt * k3[1], etot + dt * k3[2],
            t_s + dt * k3[3], t + dt, **rhs_kwargs,
        )
        rho = rho + dt / 6.0 * (k1[0] + 2.0 * k2[0] + 2.0 * k3[0] + k4[0])
        mom = mom + dt / 6.0 * (k1[1] + 2.0 * k2[1] + 2.0 * k3[1] + k4[1])
        etot = etot + dt / 6.0 * (k1[2] + 2.0 * k2[2] + 2.0 * k3[2] + k4[2])
        t_s = t_s + dt / 6.0 * (k1[3] + 2.0 * k2[3] + 2.0 * k3[3] + k4[3])
        energy_in += dt / 6.0 * (
            k1[4]["net_power"] + 2.0 * k2[4]["net_power"]
            + 2.0 * k3[4]["net_power"] + k4[4]["net_power"]
        )
        abs_flux_int += dt / 6.0 * (
            k1[4]["abs_power"] + 2.0 * k2[4]["abs_power"]
            + 2.0 * k3[4]["abs_power"] + k4[4]["abs_power"]
        )

    _sample(sample_idx, n_steps * dt)
    max_mach = max(max_mach, _guard(n_steps))

    u_final = mom / rho
    temp_final = (etot / rho - 0.5 * u_final * u_final) / cv
    mass_end = float(np.sum(rho) * dy)
    energy_end = float(np.sum(etot) * dy)
    if cfg.drive.kind == "film":
        energy_end += float(cfg.drive.film_heat_capacity) * t_s
    energy_defect = abs((energy_end - energy0) - energy_in)

    return NSF1DResult(
        config=cfg,
        solver_id=SOLVER_ID,
        property_model_id=cfg.transport.property_model_id,
        dt=dt,
        steps_per_cycle=steps_per_cycle,
        n_steps=n_steps,
        t_samples=t_samples,
        q_wall_conductive=q_cond_s,
        q_wall_applied=q_appl_s,
        wall_temperature=t_wall_s,
        film_temperature=t_film_s,
        p_wall=p_wall_s,
        p_box_mean=p_box_s,
        dp_max_rel=dp_max_s,
        mass_series=mass_s,
        max_mach=max_mach,
        y_centers=y_centers,
        rho_final=rho,
        u_final=u_final,
        T_final=temp_final,
        mass_drift_rel=abs(mass_end - mass0) / mass0,
        energy_residual_rel_flux=energy_defect / max(abs_flux_int, 1e-300),
        energy_residual_rel_total=energy_defect / max(abs(energy0), 1e-300),
    )


def run_nsf1d(cfg: NSF1DConfig) -> NSF1DResult:
    """Time-march from the exact uniform equilibrium (rho0, u=0, T0)."""

    n = cfg.n_cells
    return run_nsf1d_from_state(
        cfg,
        np.full(n, cfg.params.rho0, dtype=float),
        np.zeros(n, dtype=float),
        np.full(n, cfg.params.T0, dtype=float),
    )


# --------------------------------------------------------------------------
# instrument fixtures (consumed by tests now, by the G3 runner in WP2)
# --------------------------------------------------------------------------


def _fit_window(result: NSF1DResult, settle_cycles: float) -> np.ndarray:
    t0 = settle_cycles / result.config.drive.frequency_hz
    mask = result.t_samples >= t0 * (1.0 - 1e-12)
    if int(np.sum(mask)) < 32:
        raise ValueError("fit window too short")
    return mask


def equilibrium_fixture(
    *,
    params: PhysicalParams | None = None,
    transport: TransportModel | None = None,
    frequency_hz: float = 1.0e4,
    n_cells: int = 32,
    height_m: float = 4.0e-3,
    n_cycles: float = 10.0,
) -> dict:
    """Undriven uniform state over n_cycles: max |p-p0|/p0 (gate row: <1e-10)."""

    params = params or default_params()
    transport = transport or lbm_equivalent_transport(params)
    drive = WallDrive(kind="temperature", frequency_hz=frequency_hz, amplitude=0.0)
    cfg = NSF1DConfig(
        params=params, transport=transport, drive=drive,
        height_m=height_m, n_cells=n_cells, n_cycles=n_cycles,
    )
    res = run_nsf1d(cfg)
    return {
        "max_dp_rel": float(np.max(res.dp_max_rel)),
        "max_mach": res.max_mach,
        "mass_drift_rel": res.mass_drift_rel,
        "energy_residual_rel_total": res.energy_residual_rel_total,
        "result": res,
    }


def linear_admittance_fixture(
    *,
    params: PhysicalParams,
    transport: TransportModel,
    frequency_hz: float,
    epsilon: float = 1.0e-4,
    height_over_delta: float = 15.0,
    cells_per_delta: float = 12.0,
    n_cycles: float = 8.0,
    settle_cycles: float = 3.0,
    samples_per_cycle: int = 64,
    n_harmonics: int = 5,
    lid_bc: str = "isothermal",
) -> dict:
    """Small-amplitude prescribed-T anchor vs the Phase_1 half-space admittance.

    Reports the raw measured admittance and the closed-box pressure-work
    corrected admittance Y = q_hat/(T_s_hat - p_hat/(rho0 cp)) (see module
    docstring); the reference is ``thermal_admittance_halfspace`` (Phase_1
    single source). All correction inputs are measured in-run — no tuning.
    """

    omega = omega_from_frequency(frequency_hz)
    alpha0 = float(transport.k(params.T0)) / (params.rho0 * params.cp)
    delta_t = math.sqrt(2.0 * alpha0 / omega)
    height = height_over_delta * delta_t
    n_cells = int(round(height_over_delta * cells_per_delta))
    drive = WallDrive(
        kind="temperature", frequency_hz=frequency_hz,
        amplitude=epsilon * params.T0, ramp_cycles=1.5,
    )
    cfg = NSF1DConfig(
        params=params, transport=transport, drive=drive,
        height_m=height, n_cells=n_cells, n_cycles=n_cycles,
        samples_per_cycle=samples_per_cycle, lid_bc=lid_bc,
    )
    res = run_nsf1d(cfg)
    mask = _fit_window(res, settle_cycles)
    t = res.t_samples[mask]
    fit_q = fit_multiharmonic(t, res.q_wall_conductive[mask], omega, n_harmonics=n_harmonics)
    fit_tw = fit_multiharmonic(t, res.wall_temperature[mask], omega, n_harmonics=n_harmonics)
    fit_p = fit_multiharmonic(t, res.p_box_mean[mask], omega, n_harmonics=n_harmonics)

    t_s_hat = fit_tw.harmonic(1)
    q_hat = fit_q.harmonic(1)
    p_hat = fit_p.harmonic(1)
    t_p_hat = p_hat / (params.rho0 * params.cp)

    y_raw = q_hat / t_s_hat
    y_corr = q_hat / (t_s_hat - t_p_hat)
    y_ref = thermal_admittance_halfspace(frequency_hz, params)

    def _errors(y: complex) -> tuple[float, float]:
        ratio = y / y_ref
        return (
            float(abs(ratio) - 1.0),
            float(math.degrees(math.atan2(ratio.imag, ratio.real))),
        )

    amp_raw, phase_raw = _errors(y_raw)
    amp_corr, phase_corr = _errors(y_corr)
    return {
        "Y_measured_raw": y_raw,
        "Y_measured_corrected": y_corr,
        "Y_reference_halfspace": y_ref,
        "amp_error_raw": amp_raw,
        "phase_error_deg_raw": phase_raw,
        "amp_error_corrected": amp_corr,
        "phase_error_deg_corrected": phase_corr,
        "box_correction_rel": abs(t_p_hat / t_s_hat),
        "T_s_hat": t_s_hat,
        "q_hat": q_hat,
        "p_box_hat": p_hat,
        "q_leakage_rel": fit_q.leakage_relative(target=1),
        "delta_T_m": delta_t,
        "height_m": height,
        "n_cells": n_cells,
        "mass_drift_rel": res.mass_drift_rel,
        "energy_residual_rel_flux": res.energy_residual_rel_flux,
        "result": res,
        "fits": {"q": fit_q, "T_wall": fit_tw, "p_box": fit_p},
    }


def acoustic_ringdown_fixture(
    *,
    params: PhysicalParams,
    transport: TransportModel | None = None,
    n_cells: int = 64,
    height_m: float = 5.0e-4,
    epsilon: float = 1.0e-4,
    n_periods: float = 12.0,
    samples_per_cycle: int = 32,
) -> dict:
    """Mode-1 standing-wave ringdown: sound speed + physical damping check.

    Initializes an adiabatic mode-1 pressure standing wave in the closed box,
    lets it ring for n_periods, and measures (i) the oscillation frequency via
    the inter-window phase drift against f_ac = c/(2H) and (ii) the amplitude
    decay rate against the laminar bulk prediction
    gamma = (k^2/2)(nu_L + (gamma_eff-1) alpha) — a *low-dissipation* check:
    a dissipative scheme overshoots the physical decay.
    """

    transport = transport or lbm_equivalent_transport(params)
    R = params.p0 / (params.rho0 * params.T0)
    cv = params.cp - R
    gamma_eff = params.cp / cv
    c0 = math.sqrt(gamma_eff * R * params.T0)
    f_ac = c0 / (2.0 * height_m)
    omega_ac = 2.0 * math.pi * f_ac

    drive = WallDrive(kind="temperature", frequency_hz=f_ac, amplitude=0.0)
    cfg = NSF1DConfig(
        params=params, transport=transport, drive=drive,
        height_m=height_m, n_cells=n_cells, n_cycles=n_periods,
        samples_per_cycle=samples_per_cycle,
    )

    k_mode = math.pi / height_m
    y = (np.arange(n_cells, dtype=float) + 0.5) * (height_m / n_cells)
    dp = epsilon * params.p0 * np.cos(k_mode * y)
    rho_init = params.rho0 * (1.0 + dp / (gamma_eff * params.p0))
    temp_init = params.T0 * (1.0 + (gamma_eff - 1.0) / gamma_eff * dp / params.p0)
    res = run_nsf1d_from_state(cfg, rho_init, np.zeros(n_cells), temp_init)

    p_rec = res.p_wall - params.p0
    t_rec = res.t_samples
    half = t_rec[0] + 0.5 * (t_rec[-1] - t_rec[0])
    m1 = t_rec < half
    m2 = ~m1
    fit1 = fit_multiharmonic(t_rec[m1], p_rec[m1], omega_ac, n_harmonics=1)
    fit2 = fit_multiharmonic(t_rec[m2], p_rec[m2], omega_ac, n_harmonics=1)
    t_c1 = 0.5 * (t_rec[m1][0] + t_rec[m1][-1])
    t_c2 = 0.5 * (t_rec[m2][0] + t_rec[m2][-1])
    gamma_meas = math.log(fit1.amplitude(1) / fit2.amplitude(1)) / (t_c2 - t_c1)
    dphi = (fit2.phase_rad(1) - fit1.phase_rad(1) + math.pi) % (2.0 * math.pi) - math.pi
    freq_offset_rel = dphi / (omega_ac * (t_c2 - t_c1))

    nu_l0 = (4.0 / 3.0 * float(transport.mu(params.T0)) + params.mu_bulk) / params.rho0
    alpha0 = float(transport.k(params.T0)) / (params.rho0 * params.cp)
    gamma_pred = 0.5 * k_mode * k_mode * (nu_l0 + (gamma_eff - 1.0) * alpha0)
    return {
        "f_acoustic_hz": f_ac,
        "gamma_measured": float(gamma_meas),
        "gamma_predicted_bulk": float(gamma_pred),
        "gamma_ratio": float(gamma_meas / gamma_pred),
        "frequency_offset_rel": float(freq_offset_rel),
        "amplitude_retention": float(fit2.amplitude(1) / fit1.amplitude(1)),
        "mass_drift_rel": res.mass_drift_rel,
        "result": res,
    }


def antisymmetric_pair_fixture(
    *,
    params: PhysicalParams,
    transport: TransportModel,
    frequency_hz: float,
    epsilon: float = 1.0e-5,
    height_over_delta: float = 4.0,
    cells_per_delta: float = 8.0,
    n_cycles: float = 11.0,
    settle_cycles: float = 7.0,
    threshold: float = 1.0e-8,
) -> dict:
    """Linearization-leakage fixture via signed-pair combinations.

    Runs the prescribed-wall-temperature protocol at +T1 and -T1 and forms
    both signed combinations of the wall-flux response q(t):

    - odd  = (q+ - q-)/2: even-order (DC, 2f, 4f) content cancels
      *analytically*, so surviving 2f/4f measures the numerical harmonic
      floor of the discrete operator chain (gate row: <=1e-8); 3f survives
      only at O(epsilon^2) (cubic), far below threshold at epsilon=1e-5.
    - even = (q+ + q-)/2: the slow settling transient (linear in the drive,
      the dominant leakage channel) cancels instead, exposing the *genuine*
      physical second harmonic at this epsilon — the fixture's sensitivity
      counter-check (it must SEE real nonlinearity, ~C2*epsilon).

    A prescribed-temperature (Dirichlet-Dirichlet) rig is used because its
    slowest diffusive mode decays ~4x faster than the flux-driven
    (Neumann-Dirichlet) rig, making the pre-registered settle window
    sufficient to push transient leakage below 1e-8; the small box
    (height_over_delta=4) further shortens tau_slow ~= H^2/(pi^2 alpha).
    The A1 flux-protocol leakage at production settle lengths is re-measured
    in the formal G3 runs.
    """

    omega = omega_from_frequency(frequency_hz)
    alpha0 = float(transport.k(params.T0)) / (params.rho0 * params.cp)
    delta_t = math.sqrt(2.0 * alpha0 / omega)
    t1 = epsilon * params.T0
    height = height_over_delta * delta_t
    n_cells = int(round(height_over_delta * cells_per_delta))

    def _one(sign: float) -> NSF1DResult:
        drive = WallDrive(
            kind="temperature", frequency_hz=frequency_hz,
            amplitude=sign * t1, ramp_cycles=1.5,
        )
        cfg = NSF1DConfig(
            params=params, transport=transport, drive=drive,
            height_m=height, n_cells=n_cells, n_cycles=n_cycles,
        )
        return run_nsf1d(cfg)

    res_plus = _one(+1.0)
    res_minus = _one(-1.0)
    mask = _fit_window(res_plus, settle_cycles)
    t = res_plus.t_samples[mask]
    q_odd = 0.5 * (res_plus.q_wall_conductive[mask] - res_minus.q_wall_conductive[mask])
    q_even = 0.5 * (res_plus.q_wall_conductive[mask] + res_minus.q_wall_conductive[mask])
    fit_odd = fit_multiharmonic(t, q_odd, omega, n_harmonics=5)
    fit_even = fit_multiharmonic(t, q_even, omega, n_harmonics=5)
    leak_odd = fit_odd.leakage_relative(target=1)
    base_1f = fit_odd.amplitude(1)
    even_max = max(leak_odd[2], leak_odd[4])
    physical_2f_rel = fit_even.amplitude(2) / base_1f
    return {
        "leakage_odd_combination": leak_odd,
        "max_even_leakage_odd_combination": float(even_max),
        "third_harmonic_odd_combination": float(leak_odd[3]),
        "physical_2f_rel_even_combination": float(physical_2f_rel),
        "threshold": float(threshold),
        "passed": bool(even_max <= threshold and leak_odd[3] <= threshold),
        "T1_K": float(t1),
        "mass_drift_rel": max(res_plus.mass_drift_rel, res_minus.mass_drift_rel),
        "results": (res_plus, res_minus),
    }
