"""SI <-> lattice-unit mapping for Phase 2.

This module is the single authority for transport and tau mapping.  Other
modules consume :class:`UnitMapping` and must not recompute ``nu_lu``,
``alpha_lu``, ``nu_b_lu``, ``theta_transport_lu``, ``tau21``, ``tau22`` or
``tau32`` directly.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from core.lattice import default_q, default_theta_q, normalize_velocity_set


AUTO_TAU32_LINEAR_HEAT_FLUX_POLICY = "auto_tau32_linear"
AUTO_TAU32_LINEAR_HEAT_FLUX_INTERCEPT = -0.5467
AUTO_TAU32_LINEAR_HEAT_FLUX_SLOPE = 0.949
AUTO_D2Q37_TAU32_LINEAR_HEAT_FLUX_POLICY = "auto_d2q37_tau32_linear"
AUTO_D2Q37_TAU32_LINEAR_HEAT_FLUX_INTERCEPT = -0.5030006782780277
AUTO_D2Q37_TAU32_LINEAR_HEAT_FLUX_SLOPE = 0.7230829392328689
HEAT_FLUX_TAU32_RELATION = (
    "alpha_lu = theta_transport_lu * (tau32 - 0.5); "
    "regularized_heat_flux_factor is a lattice-family projection closure h(tau32), "
    "not an independent transport knob"
)


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
    velocity_set: str = "D2Q21"
    Q: int = 21
    dx_m: float = 4.0e-6
    dt_s: float = 3.0e-9
    theta_q_lu: float = 2.0 / 3.0
    theta_ref_policy: str = "physical_sound_speed"
    theta_transport_policy: str = "theta_ref_lu"
    rho_ref_lu: float = 1.0
    D: int = 2
    S: int = 3


@dataclass(frozen=True)
class CollisionScales:
    bulk_viscosity_policy: str = "diagnostic_zero"
    nu_b_lu: float | str = "auto"
    central_moment_closure: str = "second_order"
    high_order_relaxation: float = 1.0
    dispersion_correction_enabled: bool = False
    dispersion_correction_low_laplacian: float = 0.0
    dispersion_correction_high_laplacian: float = 0.0
    regularized_shear_xy_factor: float = 1.0
    regularized_shear_normal_factor: float = 1.0
    regularized_shear_xy_dispersion_target: float = 1.0
    regularized_shear_normal_dispersion_target: float = 1.0
    regularized_heat_flux_factor_policy: str = "specified"
    regularized_heat_flux_factor: float = 0.0
    regularized_heat_flux_dispersion_target: float = 1.0
    regularized_heat_flux_f_fraction: float = 0.5714285714285714
    conductive_heat_flux_moment_factor_policy: str = "specified"
    conductive_heat_flux_moment_factor: float = 1.0
    conductive_heat_flux_dispersion_target: float = 1.0
    conductive_heat_flux_galilean_correction_factor: float = 0.0


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
            "velocity_set": self.lattice.velocity_set,
            "Q": self.lattice.Q,
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
            "central_moment_closure": self.collision.central_moment_closure,
            "nu_lu": self.nu_lu,
            "alpha_lu": self.alpha_lu,
            "nu_b_lu": self.nu_b_lu,
            "Pr_lu": self.Pr_lu,
            "tau21": self.tau21,
            "tau22": self.tau22,
            "tau32": self.tau32,
            "heat_flux_tau32_relation": HEAT_FLUX_TAU32_RELATION,
            "dispersion_correction_enabled": self.collision.dispersion_correction_enabled,
            "dispersion_correction_low_laplacian": self.collision.dispersion_correction_low_laplacian,
            "dispersion_correction_high_laplacian": self.collision.dispersion_correction_high_laplacian,
            "regularized_shear_xy_factor": self.collision.regularized_shear_xy_factor,
            "regularized_shear_normal_factor": self.collision.regularized_shear_normal_factor,
            "regularized_shear_xy_dispersion_target": self.collision.regularized_shear_xy_dispersion_target,
            "regularized_shear_normal_dispersion_target": self.collision.regularized_shear_normal_dispersion_target,
            "regularized_heat_flux_factor_policy": self.collision.regularized_heat_flux_factor_policy,
            "regularized_heat_flux_factor": self.collision.regularized_heat_flux_factor,
            "regularized_heat_flux_dispersion_target": self.collision.regularized_heat_flux_dispersion_target,
            "regularized_heat_flux_factor_tau32_linear_intercept": AUTO_TAU32_LINEAR_HEAT_FLUX_INTERCEPT,
            "regularized_heat_flux_factor_tau32_linear_slope": AUTO_TAU32_LINEAR_HEAT_FLUX_SLOPE,
            "regularized_heat_flux_factor_d2q37_tau32_linear_intercept": (
                AUTO_D2Q37_TAU32_LINEAR_HEAT_FLUX_INTERCEPT
            ),
            "regularized_heat_flux_factor_d2q37_tau32_linear_slope": (
                AUTO_D2Q37_TAU32_LINEAR_HEAT_FLUX_SLOPE
            ),
            "regularized_heat_flux_f_fraction": self.collision.regularized_heat_flux_f_fraction,
            "conductive_heat_flux_moment_factor_policy": self.collision.conductive_heat_flux_moment_factor_policy,
            "conductive_heat_flux_moment_factor": self.collision.conductive_heat_flux_moment_factor,
            "conductive_heat_flux_dispersion_target": self.collision.conductive_heat_flux_dispersion_target,
            "conductive_heat_flux_galilean_correction_factor": (
                self.collision.conductive_heat_flux_galilean_correction_factor
            ),
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
    velocity_set = normalize_velocity_set(lattice.get("velocity_set", "D2Q21"))
    return LatticeScales(
        velocity_set=velocity_set,
        Q=int(lattice.get("Q", default_q(velocity_set))),
        dx_m=float(lattice.get("dx_m", 4.0e-6)),
        dt_s=float(lattice.get("dt_s", 3.0e-9)),
        theta_q_lu=float(lattice.get("theta_q_lu", default_theta_q(velocity_set))),
        theta_ref_policy=str(lattice.get("theta_ref_policy", "physical_sound_speed")),
        theta_transport_policy=str(lattice.get("theta_transport_policy", "theta_ref_lu")),
        rho_ref_lu=float(lattice.get("rho_ref_lu", 1.0)),
        D=int(lattice.get("D", 2)),
        S=int(lattice.get("S", 3)),
    )


def _collision_from_config(config: dict[str, Any] | None) -> CollisionScales:
    collision = (config or {}).get("collision", {})
    regularized_heat_flux_factor = collision.get("regularized_heat_flux_factor", 0.0)
    regularized_heat_flux_factor_policy = str(
        collision.get("regularized_heat_flux_factor_policy", "specified")
    )
    if isinstance(regularized_heat_flux_factor, str):
        regularized_heat_flux_factor_policy = regularized_heat_flux_factor
        regularized_heat_flux_factor = 0.0

    conductive_heat_flux_moment_factor = collision.get("conductive_heat_flux_moment_factor", 1.0)
    conductive_heat_flux_moment_factor_policy = str(
        collision.get("conductive_heat_flux_moment_factor_policy", "specified")
    )
    if isinstance(conductive_heat_flux_moment_factor, str):
        conductive_heat_flux_moment_factor_policy = conductive_heat_flux_moment_factor
        conductive_heat_flux_moment_factor = 1.0

    return CollisionScales(
        bulk_viscosity_policy=str(collision.get("bulk_viscosity_policy", "diagnostic_zero")),
        nu_b_lu=collision.get("nu_b_lu", "auto"),
        central_moment_closure=str(collision.get("central_moment_closure", "second_order")),
        high_order_relaxation=float(collision.get("high_order_relaxation", 1.0)),
        dispersion_correction_enabled=bool(collision.get("dispersion_correction_enabled", False)),
        dispersion_correction_low_laplacian=float(collision.get("dispersion_correction_low_laplacian", 0.0)),
        dispersion_correction_high_laplacian=float(collision.get("dispersion_correction_high_laplacian", 0.0)),
        regularized_shear_xy_factor=float(collision.get("regularized_shear_xy_factor", 1.0)),
        regularized_shear_normal_factor=float(collision.get("regularized_shear_normal_factor", 1.0)),
        regularized_shear_xy_dispersion_target=float(
            collision.get("regularized_shear_xy_dispersion_target", 1.0)
        ),
        regularized_shear_normal_dispersion_target=float(
            collision.get("regularized_shear_normal_dispersion_target", 1.0)
        ),
        regularized_heat_flux_factor_policy=regularized_heat_flux_factor_policy,
        regularized_heat_flux_factor=float(regularized_heat_flux_factor),
        regularized_heat_flux_dispersion_target=float(
            collision.get("regularized_heat_flux_dispersion_target", 1.0)
        ),
        regularized_heat_flux_f_fraction=float(collision.get("regularized_heat_flux_f_fraction", 0.5714285714285714)),
        conductive_heat_flux_moment_factor_policy=conductive_heat_flux_moment_factor_policy,
        conductive_heat_flux_moment_factor=float(conductive_heat_flux_moment_factor),
        conductive_heat_flux_dispersion_target=float(
            collision.get("conductive_heat_flux_dispersion_target", 1.0)
        ),
        conductive_heat_flux_galilean_correction_factor=float(
            collision.get("conductive_heat_flux_galilean_correction_factor", 0.0)
        ),
    )


def regularized_heat_flux_factor_from_tau32(
    tau32: float,
    *,
    policy: str = AUTO_TAU32_LINEAR_HEAT_FLUX_POLICY,
) -> float:
    """Return the projection-space heat-flux retention closure ``h(tau32)``.

    ``tau32`` remains the only thermal diffusivity relaxation time:
    ``alpha_lu = theta_transport_lu * (tau32 - 0.5)``.  The returned factor is
    the family-specific post-collision raw central heat-flux retention used by
    the regularized f/g projection.  It is therefore a calibrated projection
    closure tied to ``tau32``, not a second independent diffusivity mapping.
    """

    if policy == AUTO_TAU32_LINEAR_HEAT_FLUX_POLICY:
        intercept = AUTO_TAU32_LINEAR_HEAT_FLUX_INTERCEPT
        slope = AUTO_TAU32_LINEAR_HEAT_FLUX_SLOPE
    elif policy == AUTO_D2Q37_TAU32_LINEAR_HEAT_FLUX_POLICY:
        intercept = AUTO_D2Q37_TAU32_LINEAR_HEAT_FLUX_INTERCEPT
        slope = AUTO_D2Q37_TAU32_LINEAR_HEAT_FLUX_SLOPE
    else:
        raise ValueError(f"unknown regularized_heat_flux_factor_policy: {policy}")
    return intercept + slope * (tau32 - 0.5)


def alpha_lu_from_tau32(tau32: float, theta_transport_lu: float) -> float:
    """Return thermal diffusivity implied by the Phase 2 tau32 convention."""

    return float(theta_transport_lu) * (float(tau32) - 0.5)


def tau32_from_alpha_lu(alpha_lu: float, theta_transport_lu: float) -> float:
    """Return tau32 from conductive thermal diffusivity in lattice units."""

    return 0.5 + float(alpha_lu) / float(theta_transport_lu)


def heat_flux_f_fraction_from_degrees(D: int, S: int) -> float:
    """Return the f-channel share of conductive enthalpy flux.

    For the current D=2, S=3 gas, this gives (D+2)/(D+S+2)=4/7; the remaining
    S/(D+S+2)=3/7 is carried by the g-channel internal-energy flux.
    """

    return (float(D) + 2.0) / (float(D) + float(S) + 2.0)


def _resolve_collision_closure(collision: CollisionScales, tau32: float) -> CollisionScales:
    factor_policy = collision.regularized_heat_flux_factor_policy
    if factor_policy == "specified":
        heat_flux_factor = collision.regularized_heat_flux_factor
    elif factor_policy in {
        AUTO_TAU32_LINEAR_HEAT_FLUX_POLICY,
        AUTO_D2Q37_TAU32_LINEAR_HEAT_FLUX_POLICY,
    }:
        heat_flux_factor = regularized_heat_flux_factor_from_tau32(tau32, policy=factor_policy)
    else:
        raise ValueError(f"unknown regularized_heat_flux_factor_policy: {factor_policy}")

    conductive_policy = collision.conductive_heat_flux_moment_factor_policy
    if conductive_policy != "specified":
        raise ValueError(f"unknown conductive_heat_flux_moment_factor_policy: {conductive_policy}")

    return replace(collision, regularized_heat_flux_factor=float(heat_flux_factor))


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
    tau32 = tau32_from_alpha_lu(alpha_lu, theta_transport_lu)
    collision = _resolve_collision_closure(collision, tau32)
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
            "velocity_set": "D2Q21",
            "Q": 21,
            "dx_m": 4.0e-6,
            "dt_s": 3.0e-9,
            "theta_q_lu": default_theta_q("D2Q21"),
            "theta_ref_policy": "physical_sound_speed",
            "theta_transport_policy": "theta_ref_lu",
        },
        "numerics": {
            "high_wavenumber_filter": {
                "enabled": True,
                "strength": 0.0065,
                "passes": 1,
            },
        },
        "collision": {
            "bulk_viscosity_policy": "diagnostic_zero",
            "nu_b_lu": "auto",
            "central_moment_closure": "second_order",
            "dispersion_correction_enabled": False,
            "regularized_shear_xy_factor": 0.965,
            "regularized_shear_normal_factor": 0.845,
            "regularized_heat_flux_factor": AUTO_TAU32_LINEAR_HEAT_FLUX_POLICY,
            "regularized_heat_flux_f_fraction": 0.5714285714285714,
            "conductive_heat_flux_moment_factor": 0.05192359403391186,
            "conductive_heat_flux_galilean_correction_factor": 0.03272660408381829,
        },
    }


def d2q37_physical_timestep_config() -> dict[str, Any]:
    config = physical_timestep_config()
    config["case"] = {
        "name": "gas_air_10k_d2q37_physical_timestep",
        "phase": "Phase_2",
        "purpose": "D2Q37 fallback diagnostic seed",
    }
    config["lattice"] = {
        **config["lattice"],
        "velocity_set": "D2Q37",
        "Q": 37,
        "theta_q_lu": default_theta_q("D2Q37"),
    }
    config["collision"] = {
        **config["collision"],
        "regularized_shear_xy_factor": 0.8739,
        "regularized_shear_normal_factor": 0.9,
        "dispersion_correction_enabled": True,
        "dispersion_correction_low_laplacian": 0.019261093311212455,
        "dispersion_correction_high_laplacian": 0.038429439193539104,
        "regularized_shear_xy_dispersion_target": 0.786,
        "regularized_shear_normal_dispersion_target": 0.785,
        "regularized_heat_flux_factor": AUTO_D2Q37_TAU32_LINEAR_HEAT_FLUX_POLICY,
        "regularized_heat_flux_dispersion_target": 0.8512,
        "conductive_heat_flux_moment_factor": 0.0422,
        "conductive_heat_flux_dispersion_target": 0.3201,
        "conductive_heat_flux_galilean_correction_factor": 0.03835608923273733,
    }
    return config


def quadrature_matched_config() -> dict[str, Any]:
    dx_m = 4.0e-6
    c0 = 347.0
    gamma = 1.4
    theta_q = default_theta_q("D2Q21")
    dt_s = dx_m * float(np.sqrt(gamma * theta_q)) / c0
    return {
        "physical": {"c0_m_s": c0, "gamma": gamma},
        "lattice": {
            "velocity_set": "D2Q21",
            "Q": 21,
            "dx_m": dx_m,
            "dt_s": dt_s,
            "theta_q_lu": theta_q,
            "theta_ref_policy": "quadrature_matched",
            "theta_transport_policy": "theta_ref_lu",
        },
        "collision": {
            "bulk_viscosity_policy": "diagnostic_zero",
            "nu_b_lu": "auto",
            "central_moment_closure": "second_order",
            "regularized_heat_flux_factor": 0.0,
            "regularized_heat_flux_f_fraction": 0.5714285714285714,
            "conductive_heat_flux_moment_factor": 1.0,
        },
    }


def validate_unit_mapping(mapping: UnitMapping) -> None:
    """Validate non-negotiable mapping invariants."""

    if mapping.lattice.Q != default_q(mapping.lattice.velocity_set):
        raise ValueError("Q is inconsistent with velocity_set")
    if not np.isclose(
        mapping.lattice.theta_q_lu,
        default_theta_q(mapping.lattice.velocity_set),
        rtol=0.0,
        atol=1.0e-15,
    ):
        raise ValueError("theta_q_lu is inconsistent with velocity_set")
    if not np.isclose(mapping.Pr_lu, mapping.nu_lu / mapping.alpha_lu, rtol=0.0, atol=1.0e-15):
        raise ValueError("Pr_lu is inconsistent with nu_lu/alpha_lu")
    if not np.isclose(mapping.gamma_from_degrees, mapping.physical.gamma, rtol=0.0, atol=1.0e-12):
        raise ValueError("D/S degrees of freedom do not reconstruct target gamma")
    if mapping.physical.Pr < 1.0 and not mapping.tau32 > mapping.tau21:
        raise ValueError("air Pr<1 requires tau32 > tau21 for this mapping")
    if mapping.collision.bulk_viscosity_policy == "diagnostic_zero" and mapping.nu_b_lu != 0.0:
        raise ValueError("diagnostic_zero bulk policy requires nu_b_lu=0")
    if mapping.collision.central_moment_closure not in {"second_order", "fourth_order"}:
        raise ValueError("central_moment_closure must be second_order or fourth_order")
    if mapping.collision.high_order_relaxation <= 0.0:
        raise ValueError("high_order_relaxation must be positive")
    if mapping.collision.dispersion_correction_enabled:
        if not 0.0 <= mapping.collision.dispersion_correction_low_laplacian:
            raise ValueError("dispersion_correction_low_laplacian must be non-negative")
        if (
            not mapping.collision.dispersion_correction_high_laplacian
            > mapping.collision.dispersion_correction_low_laplacian
        ):
            raise ValueError("dispersion_correction_high_laplacian must exceed the low threshold")
        targets = (
            mapping.collision.regularized_shear_xy_dispersion_target,
            mapping.collision.regularized_shear_normal_dispersion_target,
            mapping.collision.regularized_heat_flux_dispersion_target,
            mapping.collision.conductive_heat_flux_dispersion_target,
        )
        if any((not np.isfinite(item)) or item <= 0.0 for item in targets):
            raise ValueError("dispersion correction targets must be finite and positive")
    if not 0.0 <= mapping.collision.regularized_heat_flux_f_fraction <= 1.0:
        raise ValueError("regularized_heat_flux_f_fraction must be in [0, 1]")
    expected_f_fraction = heat_flux_f_fraction_from_degrees(mapping.lattice.D, mapping.lattice.S)
    if not np.isclose(
        mapping.collision.regularized_heat_flux_f_fraction,
        expected_f_fraction,
        rtol=0.0,
        atol=1.0e-15,
    ):
        raise ValueError("regularized_heat_flux_f_fraction must match the D/S enthalpy split")
    if not np.isfinite(mapping.collision.regularized_heat_flux_factor):
        raise ValueError("regularized_heat_flux_factor must be finite")
    if mapping.collision.conductive_heat_flux_moment_factor <= 0.0:
        raise ValueError("conductive_heat_flux_moment_factor must be positive")
    if not np.isfinite(mapping.collision.conductive_heat_flux_galilean_correction_factor):
        raise ValueError("conductive_heat_flux_galilean_correction_factor must be finite")


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
