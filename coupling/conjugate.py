"""Level C predictor-corrector coupling for Phase_3."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from boundary.wall_dirichlet import (
    LEVEL_A_HEAT_FLUX_SIGN_CONVENTION,
    LEVEL_A_WALL_NORMAL_CONVENTION,
    apply_bottom_dirichlet_wall,
)
from core.solver import GasSolver2D
from phase3_interfaces.heat_flux_extraction import (
    UPPER_GAS_WALL_NORMAL,
    extract_wall_heat_flux,
)
from phase3_interfaces.wall_state_contract import wall_state_from_temperature

from .drive import DriveSignal, evaluate_drive
from .energy_audit import EnergyAuditResult, audit_film_energy
from .film_ode import FilmOdeParams, film_rhs


BOTTOM_WALL_ROW = 0
LevelCScheme = Literal["heun_picard1", "heun", "explicit_lagged"]


@dataclass(frozen=True)
class LevelCCouplingResult:
    """Sampled Level C coupling trajectory."""

    t_si: np.ndarray
    T_s_K: np.ndarray
    P_in_si: np.ndarray
    q_g_one_sided_si: np.ndarray
    dT_s_dt_K_s: np.ndarray
    theta_wall_lu: np.ndarray
    T_wall_K: np.ndarray
    pressure_probe_Pa: np.ndarray
    temperature_probe_K: np.ndarray
    energy_audit: EnergyAuditResult
    coupling_scheme: str
    picard_iterations: int
    predictor_corrector_delta_K: np.ndarray
    wall_temperature_error_K: np.ndarray
    finite: bool
    no_clipping_or_floor_used: bool = True
    wall_normal_convention: str = LEVEL_A_WALL_NORMAL_CONVENTION
    heat_flux_sign_convention: str = LEVEL_A_HEAT_FLUX_SIGN_CONVENTION

    @property
    def passed_smoke(self) -> bool:
        return bool(self.finite and self.energy_audit.passed and self.no_clipping_or_floor_used)


def extract_bottom_wall_heat_flux_si(
    solver: GasSolver2D,
    *,
    row: int = BOTTOM_WALL_ROW,
    gas_offset: int = 1,
) -> float:
    """Extract the near-wall one-sided gas heat flux ``q_g''`` (SI, W/m^2).

    The conductive flux ``q_g''=-k_g dT/dy|0+`` is carried by the gas adjacent to the
    wall, not by the Dirichlet wall row: that row is clamped to an equilibrium state and
    therefore carries ~0 conductive flux. We follow the Phase_3 handoff convention
    (``scripts/phase2_phase3_handoff.py``): take the full-field conductive ``q_n(y)``
    profile and read the first interior gas row ``row + gas_offset``.
    """

    if row != BOTTOM_WALL_ROW:
        raise ValueError("P3-4 supports the bottom wall row only")
    if gas_offset < 1:
        raise ValueError("gas_offset must point into the gas (>=1), not at the clamped wall row")
    solver.get_macro()
    assert solver.f is not None and solver.g is not None
    q_field = extract_wall_heat_flux(
        solver.f,
        solver.g,
        wall_normal=UPPER_GAS_WALL_NORMAL,
        config=solver.config,
        return_physical=True,
    )
    q_n = np.mean(np.asarray(q_field, dtype=float), axis=1)  # per-row q_n(y)
    gas_row = min(row + gas_offset, solver.ny - 1)
    return float(q_n[gas_row])


def _pressure_probe_pa(solver: GasSolver2D, probe: tuple[int, int]) -> float:
    y, x = probe
    p_lu = float(solver.get_pressure_lu()[y, x])
    return float(p_lu * solver.mapping.pressure_scale)


def _temperature_probe_K(solver: GasSolver2D, probe: tuple[int, int]) -> float:
    y, x = probe
    theta_lu = float(solver.get_temperature_lu()[y, x])
    return float(theta_lu * solver.mapping.temperature_scale)


def _wall_temperature_error_K(solver: GasSolver2D, row: int, target_T_K: float) -> float:
    theta = solver.get_temperature_lu()[row]
    recovered_T = np.asarray(theta, dtype=float) * solver.mapping.temperature_scale
    return float(np.max(np.abs(recovered_T - float(target_T_K))))


def _apply_wall_temperature(
    solver: GasSolver2D,
    *,
    T_wall_K: float,
    rho_policy: str,
    row: int,
) -> float:
    apply_bottom_dirichlet_wall(
        solver,
        T_wall_K=float(T_wall_K),
        rho_policy=rho_policy,  # type: ignore[arg-type]
        row=row,
    )
    return float(wall_state_from_temperature(T_wall_K, solver.config)["theta_wall_lu"])


def initialize_levelc_state(
    solver: GasSolver2D,
    *,
    T_initial_K: float,
    rho_policy: str = "pressure_preserving",
    row: int = BOTTOM_WALL_ROW,
) -> None:
    """Initialize a uniform gas state and clamp the Level C wall temperature."""

    solver.initialize_from_macro(
        solver.mapping.lattice.rho_ref_lu,
        np.zeros((solver.ny, solver.nx, 2), dtype=float),
        solver.mapping.theta_ref_lu,
    )
    _apply_wall_temperature(
        solver,
        T_wall_K=T_initial_K,
        rho_policy=rho_policy,
        row=row,
    )


def run_levelc_predictor_corrector(
    *,
    solver: GasSolver2D,
    params: FilmOdeParams,
    drive: DriveSignal | float,
    n_steps: int,
    dt_si: float | None = None,
    T_initial_K: float | None = None,
    rho_policy: str = "pressure_preserving",
    row: int = BOTTOM_WALL_ROW,
    scheme: LevelCScheme = "heun_picard1",
    energy_tolerance: float = 1.0e-2,
    probe: tuple[int, int] | None = None,
) -> LevelCCouplingResult:
    """Run a short Level C predictor-corrector coupling trajectory."""

    if n_steps < 1:
        raise ValueError("n_steps must be positive")
    if scheme not in {"heun_picard1", "heun", "explicit_lagged"}:
        raise ValueError(f"unsupported Level C scheme: {scheme}")
    if row != BOTTOM_WALL_ROW:
        raise ValueError("P3-4 supports the bottom wall row only")

    dt = float(solver.mapping.lattice.dt_s if dt_si is None else dt_si)
    if dt <= 0.0:
        raise ValueError("dt_si must be positive")
    T0 = float(params.T_ref_K if T_initial_K is None else T_initial_K)
    probe_loc = probe or (min(max(row + 1, 0), solver.ny - 1), solver.nx // 2)

    initialize_levelc_state(
        solver,
        T_initial_K=T0,
        rho_policy=rho_policy,
        row=row,
    )

    t = np.arange(int(n_steps) + 1, dtype=float) * dt
    T_s = np.empty_like(t)
    P_in = np.empty_like(t)
    q_g = np.empty_like(t)
    dTdt = np.empty_like(t)
    theta_wall = np.empty_like(t)
    T_wall = np.empty_like(t)
    pressure_probe = np.empty_like(t)
    temperature_probe = np.empty_like(t)
    delta_pc = np.zeros_like(t)
    wall_error = np.empty_like(t)

    T_s[0] = T0
    P_in[0] = evaluate_drive(drive, float(t[0]))
    q_g[0] = extract_bottom_wall_heat_flux_si(solver, row=row)
    dTdt[0] = film_rhs(T_s[0], float(t[0]), params=params, drive=drive, q_g_one_sided_si=q_g[0])
    theta_wall[0] = wall_state_from_temperature(T_s[0], solver.config)["theta_wall_lu"]
    T_wall[0] = T_s[0]
    pressure_probe[0] = _pressure_probe_pa(solver, probe_loc)
    temperature_probe[0] = _temperature_probe_K(solver, probe_loc)
    wall_error[0] = _wall_temperature_error_K(solver, row, T_s[0])

    picard_iterations = 1 if scheme == "heun_picard1" else 0

    for i in range(int(n_steps)):
        t_n = float(t[i])
        t_np1 = float(t[i + 1])
        T_n = float(T_s[i])
        q_n = float(q_g[i])
        rhs_n = film_rhs(T_n, t_n, params=params, drive=drive, q_g_one_sided_si=q_n)

        if scheme == "explicit_lagged":
            T_next = T_n + dt * rhs_n
            theta_next = _apply_wall_temperature(
                solver,
                T_wall_K=T_next,
                rho_policy=rho_policy,
                row=row,
            )
            solver.step(1)
            theta_next = _apply_wall_temperature(
                solver,
                T_wall_K=T_next,
                rho_policy=rho_policy,
                row=row,
            )
            q_next = extract_bottom_wall_heat_flux_si(solver, row=row)
        else:
            T_predict = T_n + dt * rhs_n
            _apply_wall_temperature(
                solver,
                T_wall_K=T_predict,
                rho_policy=rho_policy,
                row=row,
            )
            solver.step(1)
            _apply_wall_temperature(
                solver,
                T_wall_K=T_predict,
                rho_policy=rho_policy,
                row=row,
            )
            q_end = extract_bottom_wall_heat_flux_si(solver, row=row)
            rhs_end = film_rhs(T_predict, t_np1, params=params, drive=drive, q_g_one_sided_si=q_end)
            T_next = T_n + 0.5 * dt * (rhs_n + rhs_end)
            delta_pc[i + 1] = T_next - T_predict
            for _ in range(picard_iterations):
                _apply_wall_temperature(
                    solver,
                    T_wall_K=T_next,
                    rho_policy=rho_policy,
                    row=row,
                )
                q_end = extract_bottom_wall_heat_flux_si(solver, row=row)
                rhs_end = film_rhs(T_next, t_np1, params=params, drive=drive, q_g_one_sided_si=q_end)
                T_next = T_n + 0.5 * dt * (rhs_n + rhs_end)
            theta_next = _apply_wall_temperature(
                solver,
                T_wall_K=T_next,
                rho_policy=rho_policy,
                row=row,
            )
            q_next = extract_bottom_wall_heat_flux_si(solver, row=row)

        T_s[i + 1] = T_next
        P_in[i + 1] = evaluate_drive(drive, t_np1)
        q_g[i + 1] = q_next
        dTdt[i + 1] = (T_s[i + 1] - T_s[i]) / dt
        theta_wall[i + 1] = theta_next
        T_wall[i + 1] = T_s[i + 1]
        pressure_probe[i + 1] = _pressure_probe_pa(solver, probe_loc)
        temperature_probe[i + 1] = _temperature_probe_K(solver, probe_loc)
        wall_error[i + 1] = _wall_temperature_error_K(solver, row, T_s[i + 1])

    audit = audit_film_energy(
        t_si=t,
        P_in_si=P_in,
        q_g_one_sided_si=q_g,
        T_s_K=T_s,
        params=params,
        tolerance=energy_tolerance,
    )
    finite = bool(
        np.isfinite(T_s).all()
        and np.isfinite(P_in).all()
        and np.isfinite(q_g).all()
        and np.isfinite(pressure_probe).all()
        and np.isfinite(temperature_probe).all()
        and np.isfinite(wall_error).all()
        and np.isfinite(solver.f).all()
        and np.isfinite(solver.g).all()
    )
    return LevelCCouplingResult(
        t_si=t,
        T_s_K=T_s,
        P_in_si=P_in,
        q_g_one_sided_si=q_g,
        dT_s_dt_K_s=dTdt,
        theta_wall_lu=theta_wall,
        T_wall_K=T_wall,
        pressure_probe_Pa=pressure_probe,
        temperature_probe_K=temperature_probe,
        energy_audit=audit,
        coupling_scheme=scheme,
        picard_iterations=picard_iterations,
        predictor_corrector_delta_K=delta_pc,
        wall_temperature_error_K=wall_error,
        finite=finite,
    )


__all__ = [
    "BOTTOM_WALL_ROW",
    "LevelCCouplingResult",
    "extract_bottom_wall_heat_flux_si",
    "initialize_levelc_state",
    "run_levelc_predictor_corrector",
]
