"""Level B prescribed heat-flux wall helpers for Phase_3.

The P3-2 implementation is a contract smoke for the bottom wall of the upper
gas half-domain.  It injects the one-sided heat flux into the wall row energy
and adds a zero-sum g-population heat-flux moment so the exported conductive
``q_lu`` field reads back the imposed value through the normal Phase_3 handoff
path.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal

import numpy as np

from core.equilibrium import equilibrium_fg
from core.macroscopic import recover_macro, total_energy
from core.solver import GasSolver2D
from phase3_interfaces.heat_flux_extraction import (
    UPPER_GAS_WALL_NORMAL,
    convert_heat_flux_lu_to_phys,
    convert_heat_flux_phys_to_lu,
    normal_heat_flux_lu,
)


BOTTOM_WALL_ROW = 0
LEVEL_B_WALL_NORMAL_CONVENTION = "upper gas half-domain: wall_normal=+e_y"
LEVEL_B_HEAT_FLUX_SIGN_CONVENTION = "q_g''=-k_g*dT/dy|0+ positive from film into upper gas"
RhoWallPolicy = Literal["pressure_preserving", "constant_density"]


@dataclass(frozen=True)
class NeumannWallDiagnostics:
    row: int
    q_wall_imposed_lu: float
    q_wall_recovered_lu: float
    q_wall_imposed_si: float
    q_wall_recovered_si: float
    theta_wall_lu_before: float
    theta_wall_lu_after: float
    rho_wall_lu: float
    rho_wall_policy: str
    velocity_set: str
    Q: int
    max_velocity_lu: float
    max_tangential_heat_flux_lu: float
    energy_before_lu: float
    energy_after_lu: float
    energy_delta_lu: float
    expected_energy_delta_lu: float
    energy_residual_lu: float
    wall_normal_convention: str = LEVEL_B_WALL_NORMAL_CONVENTION
    heat_flux_sign_convention: str = LEVEL_B_HEAT_FLUX_SIGN_CONVENTION

    @property
    def finite(self) -> bool:
        values = (
            self.q_wall_imposed_lu,
            self.q_wall_recovered_lu,
            self.q_wall_imposed_si,
            self.q_wall_recovered_si,
            self.theta_wall_lu_before,
            self.theta_wall_lu_after,
            self.rho_wall_lu,
            self.max_velocity_lu,
            self.max_tangential_heat_flux_lu,
            self.energy_before_lu,
            self.energy_after_lu,
            self.energy_delta_lu,
            self.expected_energy_delta_lu,
            self.energy_residual_lu,
        )
        return all(math.isfinite(float(value)) for value in values)


def heat_flux_lu_from_inputs(
    solver: GasSolver2D,
    *,
    q_wall_lu: float | None = None,
    q_wall_si: float | None = None,
) -> float:
    """Resolve a one-sided wall heat flux from either lattice or SI units."""

    if (q_wall_lu is None) == (q_wall_si is None):
        raise ValueError("provide exactly one of q_wall_lu or q_wall_si")
    if q_wall_lu is not None:
        return float(q_wall_lu)
    return float(convert_heat_flux_phys_to_lu(q_wall_si, solver.config))


def _wall_density_lu(
    solver: GasSolver2D,
    theta_wall_lu: float,
    *,
    rho_policy: RhoWallPolicy,
) -> float:
    if rho_policy == "pressure_preserving":
        p_ref_lu = solver.mapping.lattice.rho_ref_lu * solver.mapping.theta_ref_lu
        return float(p_ref_lu / float(theta_wall_lu))
    if rho_policy == "constant_density":
        return float(solver.mapping.lattice.rho_ref_lu)
    raise ValueError(f"unknown rho_policy: {rho_policy}")


def _g_flux_shape(solver: GasSolver2D) -> np.ndarray:
    shape = np.asarray(solver.lattice.c[:, 1], dtype=float).copy()
    shape -= float(np.mean(shape))
    denom = float(np.dot(shape, solver.lattice.c[:, 1]))
    if abs(denom) <= 1.0e-30:
        raise ValueError("velocity set cannot represent a y heat-flux moment")
    return shape


def _calibrated_flux_shape_scale(
    solver: GasSolver2D,
    f_base: np.ndarray,
    g_base: np.ndarray,
    row: int,
    target_q_lu: float,
) -> tuple[np.ndarray, float]:
    """Return a g perturbation whose recovered wall-row q_y matches target."""

    shape = _g_flux_shape(solver)
    q_base = normal_heat_flux_lu(solver.get_heat_flux_lu(), UPPER_GAS_WALL_NORMAL)
    q_base_row = float(np.mean(q_base[row]))

    f_probe = f_base.copy()
    g_probe = g_base.copy()
    g_probe[row : row + 1] += shape.reshape(1, 1, solver.lattice.q)
    try:
        solver.f = f_probe
        solver.g = g_probe
        q_probe = normal_heat_flux_lu(solver.get_heat_flux_lu(), UPPER_GAS_WALL_NORMAL)
    finally:
        solver.f = f_base
        solver.g = g_base
    response = float(np.mean(q_probe[row])) - q_base_row
    if abs(response) <= 1.0e-30:
        raise ValueError("heat-flux moment calibration produced zero response")
    scale = (float(target_q_lu) - q_base_row) / response
    return shape * scale, q_base_row


def apply_bottom_neumann_wall(
    solver: GasSolver2D,
    *,
    q_wall_lu: float | None = None,
    q_wall_si: float | None = None,
    rho_policy: RhoWallPolicy = "pressure_preserving",
    inject_energy: bool = True,
    row: int = BOTTOM_WALL_ROW,
) -> NeumannWallDiagnostics:
    """Clamp bottom wall no-slip state and impose one-sided gas heat flux."""

    if row != BOTTOM_WALL_ROW:
        raise ValueError("P3-2 supports the bottom wall row only")
    q_target = heat_flux_lu_from_inputs(solver, q_wall_lu=q_wall_lu, q_wall_si=q_wall_si)
    solver.get_macro()  # lazily initializes state
    assert solver.f is not None and solver.g is not None

    macro_before = solver.get_macro()
    theta_before = float(np.mean(macro_before.theta[row]))
    rho_w = _wall_density_lu(solver, theta_before, rho_policy=rho_policy)
    energy_before_field = total_energy(
        solver.f,
        solver.g,
        D=solver.mapping.lattice.D,
        S=solver.mapping.lattice.S,
        lattice=solver.lattice,
    )
    energy_before = float(np.sum(energy_before_field))

    energy_increment = float(q_target) if inject_energy else 0.0
    theta_after = theta_before + 2.0 * energy_increment / (
        float(solver.mapping.lattice.D + solver.mapping.lattice.S) * rho_w
    )
    if theta_after <= 0.0:
        raise ValueError("imposed heat flux would make the wall temperature non-positive")

    rho = np.full((1, solver.nx), rho_w, dtype=float)
    u = np.zeros((1, solver.nx, 2), dtype=float)
    theta = np.full((1, solver.nx), theta_after, dtype=float)
    f_wall, g_wall = equilibrium_fg(
        rho,
        u,
        theta,
        solver.mapping.lattice.S,
        solver.lattice,
    )
    f_base = solver.f.copy()
    g_base = solver.g.copy()
    f_base[row : row + 1] = f_wall
    g_base[row : row + 1] = g_wall
    solver.f = f_base
    solver.g = g_base

    delta_g, _q_base_row = _calibrated_flux_shape_scale(
        solver,
        f_base,
        g_base,
        row,
        q_target,
    )
    solver.g[row : row + 1] += delta_g.reshape(1, 1, solver.lattice.q)
    expected_energy_delta = float(q_target) * float(solver.nx) if inject_energy else 0.0

    energy_after_probe = total_energy(
        solver.f,
        solver.g,
        D=solver.mapping.lattice.D,
        S=solver.mapping.lattice.S,
        lattice=solver.lattice,
    )
    energy_delta_probe = float(np.sum(energy_after_probe - energy_before_field))
    energy_correction = expected_energy_delta - energy_delta_probe
    if energy_correction != 0.0:
        solver.g[row : row + 1] += energy_correction / float(solver.nx * solver.lattice.q)
        delta_g, _q_base_row = _calibrated_flux_shape_scale(
            solver,
            solver.f.copy(),
            solver.g.copy(),
            row,
            q_target,
        )
        solver.g[row : row + 1] += delta_g.reshape(1, 1, solver.lattice.q)
        energy_after_probe = total_energy(
            solver.f,
            solver.g,
            D=solver.mapping.lattice.D,
            S=solver.mapping.lattice.S,
            lattice=solver.lattice,
        )
        final_energy_correction = expected_energy_delta - float(
            np.sum(energy_after_probe - energy_before_field)
        )
        if final_energy_correction != 0.0:
            solver.g[row : row + 1] += final_energy_correction / float(solver.nx * solver.lattice.q)

    macro_after = recover_macro(
        solver.f[row : row + 1],
        solver.g[row : row + 1],
        D=solver.mapping.lattice.D,
        S=solver.mapping.lattice.S,
        lattice=solver.lattice,
    )
    q_field = solver.get_heat_flux_lu()
    q_n = normal_heat_flux_lu(q_field, UPPER_GAS_WALL_NORMAL)
    q_recovered_lu = float(np.mean(q_n[row]))
    q_recovered_si = float(convert_heat_flux_lu_to_phys(q_recovered_lu, solver.config))
    q_imposed_si = float(convert_heat_flux_lu_to_phys(q_target, solver.config))
    energy_after_field = total_energy(
        solver.f,
        solver.g,
        D=solver.mapping.lattice.D,
        S=solver.mapping.lattice.S,
        lattice=solver.lattice,
    )
    energy_after = float(np.sum(energy_after_field))
    energy_delta = float(np.sum(energy_after_field - energy_before_field))
    return NeumannWallDiagnostics(
        row=row,
        q_wall_imposed_lu=float(q_target),
        q_wall_recovered_lu=q_recovered_lu,
        q_wall_imposed_si=q_imposed_si,
        q_wall_recovered_si=q_recovered_si,
        theta_wall_lu_before=theta_before,
        theta_wall_lu_after=float(np.mean(macro_after.theta)),
        rho_wall_lu=rho_w,
        rho_wall_policy=rho_policy,
        velocity_set=solver.mapping.lattice.velocity_set,
        Q=int(solver.lattice.q),
        max_velocity_lu=float(np.max(np.linalg.norm(macro_after.u, axis=-1))),
        max_tangential_heat_flux_lu=float(np.max(np.abs(q_field[row, :, 0]))),
        energy_before_lu=energy_before,
        energy_after_lu=energy_after,
        energy_delta_lu=energy_delta,
        expected_energy_delta_lu=expected_energy_delta,
        energy_residual_lu=energy_delta - expected_energy_delta,
    )


def sinusoidal_wall_heat_flux_lu(
    t_si,
    *,
    q0_lu: float,
    q_hat_lu: complex,
    frequency_hz: float,
):
    """Return ``q0 + Re[q_hat exp(i Omega t)]``."""

    t = np.asarray(t_si, dtype=float)
    omega = 2.0 * math.pi * float(frequency_hz)
    return float(q0_lu) + np.real(complex(q_hat_lu) * np.exp(1j * omega * t))
