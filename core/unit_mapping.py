"""SI <-> lattice-unit mapping for Phase 2.

This module is the single authority for transport and tau mapping.  Other
modules consume :class:`UnitMapping` and must not recompute ``nu_lu``,
``alpha_lu``, ``nu_b_lu``, ``theta_transport_lu``, ``tau21``, ``tau22`` or
``tau32`` directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from core.lattice_d2q21 import THETA_Q


@dataclass(frozen=True)
class PhysicalScales:
    T0_K: float = 300.0
    p0_Pa: float = 101_325.0
    rho0_kg_m3: float = 1.177
    c0_m_s: float = 347.0
    gamma: float = 1.4
    cp_J_kgK: float = 1005.0
    kg_W_mK: float = 0.0263
    nu0_m2_s: float = 1.57e-5
    alpha0_m2_s: float = 2.2233775895e-5
    Pr: float = 0.7061328707


@dataclass(frozen=True)
class LatticeScales:
    dx_m: float = 4.0e-6
    dt_s: float = 3.0e-9
    theta_q_lu: float = THETA_Q
    theta_ref_policy: str = "physical_sound_speed"
    theta_transport_policy: str = "theta_ref_lu"
    rho_ref_lu: float = 1.0
    D: int = 2
    S: int = 3


@dataclass(frozen=True)
class CollisionScales:
    bulk_viscosity_policy: str = "diagnostic_zero"
    nu_b_lu: float | str = "auto"
    high_order_relaxation: float = 1.0
    regularized_shear_xy_factor: float = 1.0
    regularized_shear_normal_factor: float = 1.0
    regularized_heat_flux_factor: float = 0.0
    regularized_heat_flux_f_fraction: float = 0.5714285714285714
    conductive_heat_flux_moment_factor: float = 1.0


@dataclass(frozen=True)
class UnitMapping:
    physical: PhysicalScales
    lattice: LatticeScales
    collision: CollisionScales
    c0_lu: float
    theta_ref_lu: float
    theta_transport_lu: float
    nu_lu: float
    alpha_lu: float
    Pr_lu: float
    nu_b_lu: float
    tau21: float
    tau22: float
    tau32: float
    rho_scale: float
    velocity_scale: float
    pressure_scale: float
    temperature_scale: float
    heat_flux_scale: float
    heat_flux_scale_definition: str

    @property
    def gamma_from_degrees(self) -> float:
        return 1.0 + 2.0 / (self.lattice.D + self.lattice.S)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "velocity_set": "D2Q21",
            "Q": 21,
            "D": self.lattice.D,
            "S": self.lattice.S,
            "array_layout": "c=(Q,D) columns=(cx,cy); w=(Q,); f,g=(...,Q); u,q=(...,D)",
            "theta_q_lu": self.lattice.theta_q_lu,
            "theta_ref_lu": self.theta_ref_lu,
            "theta_transport_lu": self.theta_transport_lu,
            "dx_m": self.lattice.dx_m,
            "dt_s": self.lattice.dt_s,
            "T0_K": self.physical.T0_K,
            "p0_Pa": self.physical.p0_Pa,
            "rho0_kg_m3": self.physical.rho0_kg_m3,
            "c0_m_s": self.physical.c0_m_s,
            "gamma_target": self.physical.gamma,
            "cp_J_kgK": self.physical.cp_J_kgK,
            "kg_W_mK": self.physical.kg_W_mK,
            "nu0_m2_s": self.physical.nu0_m2_s,
            "alpha0_m2_s": self.physical.alpha0_m2_s,
            "Pr_target": self.physical.Pr,
            "bulk_viscosity_policy": self.collision.bulk_viscosity_policy,
            "nu_lu": self.nu_lu,
            "alpha_lu": self.alpha_lu,
            "nu_b_lu": self.nu_b_lu,
            "Pr_lu": self.Pr_lu,
            "tau21": self.tau21,
            "tau22": self.tau22,
            "tau32": self.tau32,
            "regularized_shear_xy_factor": self.collision.regularized_shear_xy_factor,
            "regularized_shear_normal_factor": self.collision.regularized_shear_normal_factor,
            "regularized_heat_flux_factor": self.collision.regularized_heat_flux_factor,
            "regularized_heat_flux_f_fraction": self.collision.regularized_heat_flux_f_fraction,
            "conductive_heat_flux_moment_factor": self.collision.conductive_heat_flux_moment_factor,
            "rho_scale": self.rho_scale,
            "velocity_scale": self.velocity_scale,
            "pressure_scale": self.pressure_scale,
            "temperature_scale": self.temperature_scale,
            "heat_flux_scale": self.heat_flux_scale,
            "heat_flux_scale_definition": self.heat_flux_scale_definition,
        }


def _physical_from_config(config: dict[str, Any] | None) -> PhysicalScales:
    physical = (config or {}).get("physical", {})
    alpha = physical.get("alpha0_m2_s", None)
    if alpha is None:
        alpha = physical.get("kg_W_mK", 0.0263) / (
            physical.get("rho0_kg_m3", 1.177) * physical.get("cp_J_kgK", 1005.0)
        )
    pr = physical.get("Pr", physical.get("nu0_m2_s", 1.57e-5) / alpha)
    return PhysicalScales(
        T0_K=float(physical.get("T0_K", 300.0)),
        p0_Pa=float(physical.get("p0_Pa", 101_325.0)),
        rho0_kg_m3=float(physical.get("rho0_kg_m3", 1.177)),
        c0_m_s=float(physical.get("c0_m_s", 347.0)),
        gamma=float(physical.get("gamma", 1.4)),
        cp_J_kgK=float(physical.get("cp_J_kgK", 1005.0)),
        kg_W_mK=float(physical.get("kg_W_mK", 0.0263)),
        nu0_m2_s=float(physical.get("nu0_m2_s", 1.57e-5)),
        alpha0_m2_s=float(alpha),
        Pr=float(pr),
    )


def _lattice_from_config(config: dict[str, Any] | None) -> LatticeScales:
    lattice = (config or {}).get("lattice", {})
    return LatticeScales(
        dx_m=float(lattice.get("dx_m", 4.0e-6)),
        dt_s=float(lattice.get("dt_s", 3.0e-9)),
        theta_q_lu=float(lattice.get("theta_q_lu", THETA_Q)),
        theta_ref_policy=str(lattice.get("theta_ref_policy", "physical_sound_speed")),
        theta_transport_policy=str(lattice.get("theta_transport_policy", "theta_ref_lu")),
        rho_ref_lu=float(lattice.get("rho_ref_lu", 1.0)),
        D=int(lattice.get("D", 2)),
        S=int(lattice.get("S", 3)),
    )


def _collision_from_config(config: dict[str, Any] | None) -> CollisionScales:
    collision = (config or {}).get("collision", {})
    return CollisionScales(
        bulk_viscosity_policy=str(collision.get("bulk_viscosity_policy", "diagnostic_zero")),
        nu_b_lu=collision.get("nu_b_lu", "auto"),
        high_order_relaxation=float(collision.get("high_order_relaxation", 1.0)),
        regularized_shear_xy_factor=float(collision.get("regularized_shear_xy_factor", 1.0)),
        regularized_shear_normal_factor=float(collision.get("regularized_shear_normal_factor", 1.0)),
        regularized_heat_flux_factor=float(collision.get("regularized_heat_flux_factor", 0.0)),
        regularized_heat_flux_f_fraction=float(collision.get("regularized_heat_flux_f_fraction", 0.5714285714285714)),
        conductive_heat_flux_moment_factor=float(collision.get("conductive_heat_flux_moment_factor", 1.0)),
    )


def create_unit_mapping(config: dict[str, Any] | None = None) -> UnitMapping:
    """Create the complete Phase 2 mapping from a config dictionary."""

    physical = _physical_from_config(config)
    lattice = _lattice_from_config(config)
    collision = _collision_from_config(config)

    c0_lu = physical.c0_m_s * lattice.dt_s / lattice.dx_m
    if lattice.theta_ref_policy == "quadrature_matched":
        theta_ref_lu = lattice.theta_q_lu
    elif lattice.theta_ref_policy == "physical_sound_speed":
        theta_ref_lu = c0_lu**2 / physical.gamma
    else:
        theta_ref_lu = float((config or {}).get("lattice", {}).get("theta_ref_lu"))

    if lattice.theta_transport_policy == "theta_q_lu":
        theta_transport_lu = lattice.theta_q_lu
    elif lattice.theta_transport_policy == "theta_ref_lu":
        theta_transport_lu = theta_ref_lu
    else:
        theta_transport_lu = float((config or {}).get("lattice", {}).get("theta_transport_lu"))

    nu_lu = physical.nu0_m2_s * lattice.dt_s / lattice.dx_m**2
    alpha_lu = physical.alpha0_m2_s * lattice.dt_s / lattice.dx_m**2
    Pr_lu = nu_lu / alpha_lu

    policy = collision.bulk_viscosity_policy
    if policy == "diagnostic_zero":
        nu_b_lu = 0.0
    elif policy == "specified":
        if collision.nu_b_lu == "auto":
            nu_b_lu = 0.0
        else:
            nu_b_lu = float(collision.nu_b_lu)
    elif policy == "stokes_hypothesis":
        nu_b_lu = 0.0
    else:
        raise ValueError(f"unknown bulk_viscosity_policy: {policy}")

    tau21 = 0.5 + nu_lu / theta_transport_lu
    tau32 = 0.5 + alpha_lu / theta_transport_lu
    if nu_b_lu == 0.0:
        tau22 = 0.5
    else:
        factor = 2.0 * lattice.S * theta_transport_lu / (lattice.D * (lattice.D + lattice.S))
        tau22 = 0.5 + nu_b_lu / factor

    rho_scale = physical.rho0_kg_m3 / lattice.rho_ref_lu
    velocity_scale = lattice.dx_m / lattice.dt_s
    pressure_scale = rho_scale * velocity_scale**2
    temperature_scale = physical.T0_K / theta_ref_lu
    heat_flux_scale = rho_scale * velocity_scale**3
    heat_flux_scale_definition = (
        "q_phys = q_lu * rho_scale * (dx_m/dt_s)^3; exported q_lu is conductive heat flux "
        "after conductive_heat_flux_moment_factor"
    )

    mapping = UnitMapping(
        physical=physical,
        lattice=lattice,
        collision=collision,
        c0_lu=c0_lu,
        theta_ref_lu=theta_ref_lu,
        theta_transport_lu=theta_transport_lu,
        nu_lu=nu_lu,
        alpha_lu=alpha_lu,
        Pr_lu=Pr_lu,
        nu_b_lu=nu_b_lu,
        tau21=tau21,
        tau22=tau22,
        tau32=tau32,
        rho_scale=rho_scale,
        velocity_scale=velocity_scale,
        pressure_scale=pressure_scale,
        temperature_scale=temperature_scale,
        heat_flux_scale=heat_flux_scale,
        heat_flux_scale_definition=heat_flux_scale_definition,
    )
    validate_unit_mapping(mapping)
    return mapping


def physical_timestep_config() -> dict[str, Any]:
    return {
        "lattice": {
            "dx_m": 4.0e-6,
            "dt_s": 3.0e-9,
            "theta_ref_policy": "physical_sound_speed",
            "theta_transport_policy": "theta_ref_lu",
        },
        "collision": {
            "bulk_viscosity_policy": "diagnostic_zero",
            "nu_b_lu": "auto",
            "regularized_shear_xy_factor": 0.965,
            "regularized_shear_normal_factor": 0.84,
            "regularized_heat_flux_factor": -0.45,
            "regularized_heat_flux_f_fraction": 0.5714285714285714,
            "conductive_heat_flux_moment_factor": 0.05192359403391186,
        },
    }


def quadrature_matched_config() -> dict[str, Any]:
    dx_m = 4.0e-6
    c0 = 347.0
    gamma = 1.4
    dt_s = dx_m * float(np.sqrt(gamma * THETA_Q)) / c0
    return {
        "physical": {"c0_m_s": c0, "gamma": gamma},
        "lattice": {
            "dx_m": dx_m,
            "dt_s": dt_s,
            "theta_ref_policy": "quadrature_matched",
            "theta_transport_policy": "theta_ref_lu",
        },
        "collision": {
            "bulk_viscosity_policy": "diagnostic_zero",
            "nu_b_lu": "auto",
            "regularized_heat_flux_factor": 0.0,
            "regularized_heat_flux_f_fraction": 0.5714285714285714,
            "conductive_heat_flux_moment_factor": 1.0,
        },
    }


def validate_unit_mapping(mapping: UnitMapping) -> None:
    """Validate non-negotiable mapping invariants."""

    if not np.isclose(mapping.Pr_lu, mapping.nu_lu / mapping.alpha_lu, rtol=0.0, atol=1.0e-15):
        raise ValueError("Pr_lu is inconsistent with nu_lu/alpha_lu")
    if not np.isclose(mapping.gamma_from_degrees, mapping.physical.gamma, rtol=0.0, atol=1.0e-12):
        raise ValueError("D/S degrees of freedom do not reconstruct target gamma")
    if mapping.physical.Pr < 1.0 and not mapping.tau32 > mapping.tau21:
        raise ValueError("air Pr<1 requires tau32 > tau21 for this mapping")
    if mapping.collision.bulk_viscosity_policy == "diagnostic_zero" and mapping.nu_b_lu != 0.0:
        raise ValueError("diagnostic_zero bulk policy requires nu_b_lu=0")
    if not 0.0 <= mapping.collision.regularized_heat_flux_f_fraction <= 1.0:
        raise ValueError("regularized_heat_flux_f_fraction must be in [0, 1]")
    if mapping.collision.conductive_heat_flux_moment_factor <= 0.0:
        raise ValueError("conductive_heat_flux_moment_factor must be positive")


def pressure_lu_to_phys(p_lu: np.ndarray, mapping: UnitMapping) -> np.ndarray:
    return np.asarray(p_lu) * mapping.pressure_scale


def pressure_prime_lu_to_phys(p_lu: np.ndarray, mapping: UnitMapping, p_ref_lu: float | None = None) -> np.ndarray:
    ref = mapping.lattice.rho_ref_lu * mapping.theta_ref_lu if p_ref_lu is None else p_ref_lu
    return (np.asarray(p_lu) - ref) * mapping.pressure_scale


def temperature_lu_to_phys(theta_lu: np.ndarray, mapping: UnitMapping) -> np.ndarray:
    return np.asarray(theta_lu) * mapping.temperature_scale


def temperature_phys_to_lu(T_phys: np.ndarray, mapping: UnitMapping) -> np.ndarray:
    return np.asarray(T_phys) / mapping.temperature_scale


def heat_flux_lu_to_phys(q_lu: np.ndarray, mapping: UnitMapping) -> np.ndarray:
    return np.asarray(q_lu) * mapping.heat_flux_scale
