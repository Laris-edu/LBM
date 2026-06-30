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
TRACE_BULK_POLICY_CURRENT_ZERO = "current_zero"
TRACE_BULK_POLICY_TAU22 = "tau22"
TRACE_BULK_POLICY_CALIBRATED = "calibrated"
TRACE_BULK_POLICY_GHOST_ORTHOGONAL_SPECTRAL = "ghost_orthogonal_spectral"
TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL = "ghost_orthogonal_local"
TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_LAPLACIAN = "ghost_orthogonal_local_laplacian"
TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_PRESSURE_MEMORY = "ghost_orthogonal_local_pressure_memory"
TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL = "ghost_orthogonal_local_two_channel"
TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_ENTROPY_MANIFOLD = (
    "ghost_orthogonal_local_entropy_manifold"
)
GHOST_ORTHOGONAL_TRACE_ALPHA_INTERCEPT = 0.699947491657
GHOST_ORTHOGONAL_TRACE_ALPHA_SLOPE = -1.152605711210
GHOST_ORTHOGONAL_LOCAL_TRACE_DIVERGENCE_INTERCEPT = 1.102631069
GHOST_ORTHOGONAL_LOCAL_TRACE_DIVERGENCE_SLOPE = -1.74075050
GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL_ACOUSTIC_INTERCEPT = GHOST_ORTHOGONAL_LOCAL_TRACE_DIVERGENCE_INTERCEPT
GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL_ACOUSTIC_SLOPE = GHOST_ORTHOGONAL_LOCAL_TRACE_DIVERGENCE_SLOPE
GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL_THERMAL_INTERCEPT = GHOST_ORTHOGONAL_LOCAL_TRACE_DIVERGENCE_INTERCEPT
GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL_THERMAL_SLOPE = GHOST_ORTHOGONAL_LOCAL_TRACE_DIVERGENCE_SLOPE
GHOST_ORTHOGONAL_LOCAL_LAPLACIAN_DIVERGENCE_INTERCEPT = 0.86390221
GHOST_ORTHOGONAL_LOCAL_LAPLACIAN_DIVERGENCE_SLOPE = -1.41574932
GHOST_ORTHOGONAL_LOCAL_LAPLACIAN_COEFFICIENT_INTERCEPT = 24.78889350
GHOST_ORTHOGONAL_LOCAL_LAPLACIAN_COEFFICIENT_SLOPE = -33.74907949
DEVIATORIC_STRESS_POLICY_MEASURED = "measured"
DEVIATORIC_STRESS_POLICY_STRAIN_RATE_ISOTROPIC = "strain_rate_isotropic"
HEAT_FLUX_RETENTION_POLICY_CALIBRATED_CURVE = "calibrated_curve"
HEAT_FLUX_TAU32_RELATION = (
    "alpha_lu = theta_transport_lu * (tau32 - 0.5); "
    "regularized_heat_flux_factor is a lattice-family projection closure h(tau32), "
    "not an independent transport knob"
)
ACOUSTIC_PHASE_HIGH_MODE_POLICY_SPECIFIED = "specified"
ACOUSTIC_PHASE_HIGH_MODE_POLICY_FULL_MODAL_TARGET = "full_modal_target"


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
    trace_bulk_policy: str = TRACE_BULK_POLICY_CURRENT_ZERO
    trace_bulk_scale: float = 1.0
    trace_bulk_calibration_id: str | None = None
    trace_bulk_projector_alpha_curve_type: str = "affine"
    trace_bulk_projector_alpha_curve_coefficients: tuple[float, ...] = ()
    trace_bulk_projector_low_laplacian: float = 0.0
    trace_bulk_local_divergence_curve_type: str = "affine"
    trace_bulk_local_divergence_curve_coefficients: tuple[float, ...] = ()
    trace_bulk_local_thermal_curve_type: str = "affine"
    trace_bulk_local_thermal_curve_coefficients: tuple[float, ...] = ()
    trace_bulk_local_laplacian_curve_type: str = "affine"
    trace_bulk_local_laplacian_curve_coefficients: tuple[float, ...] = ()
    deviatoric_stress_policy: str = DEVIATORIC_STRESS_POLICY_MEASURED
    deviatoric_strain_rate_curve_type: str = "affine"
    deviatoric_strain_rate_curve_coefficients: tuple[float, ...] = ()
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
    regularized_heat_flux_diagonal_low_mode_target: float = 1.0
    regularized_heat_flux_f_fraction: float = 0.5714285714285714
    heat_flux_retention_policy: str = "specified"
    heat_flux_retention_curve_type: str = "affine"
    heat_flux_retention_curve_coefficients: tuple[float, ...] = ()
    conductive_heat_flux_moment_factor_policy: str = "specified"
    conductive_heat_flux_moment_factor: float = 1.0
    conductive_heat_flux_dispersion_target: float = 1.0
    conductive_heat_flux_diagonal_low_mode_target: float = 1.0
    conductive_heat_flux_galilean_correction_factor: float = 0.0
    acoustic_phase_correction_enabled: bool = False
    acoustic_phase_correction_low_laplacian: float = 0.0
    acoustic_phase_diagonal_low_mode_factor: float = 1.0
    acoustic_phase_high_mode_policy: str = ACOUSTIC_PHASE_HIGH_MODE_POLICY_SPECIFIED
    acoustic_phase_high_mode_factor: float = 1.0
    acoustic_phase_high_mode_diagonal_factor: float = 1.0


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
            "trace_bulk_policy": self.collision.trace_bulk_policy,
            "trace_bulk_scale": self.collision.trace_bulk_scale,
            "trace_bulk_calibration_id": self.collision.trace_bulk_calibration_id,
            "trace_bulk_projector_alpha_curve_type": (
                self.collision.trace_bulk_projector_alpha_curve_type
            ),
            "trace_bulk_projector_alpha_curve_coefficients": (
                self.collision.trace_bulk_projector_alpha_curve_coefficients
            ),
            "trace_bulk_projector_low_laplacian": self.collision.trace_bulk_projector_low_laplacian,
            "trace_bulk_local_divergence_curve_type": (
                self.collision.trace_bulk_local_divergence_curve_type
            ),
            "trace_bulk_local_divergence_curve_coefficients": (
                self.collision.trace_bulk_local_divergence_curve_coefficients
            ),
            "trace_bulk_local_thermal_curve_type": (
                self.collision.trace_bulk_local_thermal_curve_type
            ),
            "trace_bulk_local_thermal_curve_coefficients": (
                self.collision.trace_bulk_local_thermal_curve_coefficients
            ),
            "trace_bulk_local_laplacian_curve_type": (
                self.collision.trace_bulk_local_laplacian_curve_type
            ),
            "trace_bulk_local_laplacian_curve_coefficients": (
                self.collision.trace_bulk_local_laplacian_curve_coefficients
            ),
            "deviatoric_stress_policy": self.collision.deviatoric_stress_policy,
            "deviatoric_strain_rate_curve_type": self.collision.deviatoric_strain_rate_curve_type,
            "deviatoric_strain_rate_curve_coefficients": (
                self.collision.deviatoric_strain_rate_curve_coefficients
            ),
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
            "regularized_heat_flux_diagonal_low_mode_target": (
                self.collision.regularized_heat_flux_diagonal_low_mode_target
            ),
            "regularized_heat_flux_factor_tau32_linear_intercept": AUTO_TAU32_LINEAR_HEAT_FLUX_INTERCEPT,
            "regularized_heat_flux_factor_tau32_linear_slope": AUTO_TAU32_LINEAR_HEAT_FLUX_SLOPE,
            "regularized_heat_flux_factor_d2q37_tau32_linear_intercept": (
                AUTO_D2Q37_TAU32_LINEAR_HEAT_FLUX_INTERCEPT
            ),
            "regularized_heat_flux_factor_d2q37_tau32_linear_slope": (
                AUTO_D2Q37_TAU32_LINEAR_HEAT_FLUX_SLOPE
            ),
            "regularized_heat_flux_f_fraction": self.collision.regularized_heat_flux_f_fraction,
            "heat_flux_retention_policy": self.collision.heat_flux_retention_policy,
            "heat_flux_retention_curve_type": self.collision.heat_flux_retention_curve_type,
            "heat_flux_retention_curve_coefficients": self.collision.heat_flux_retention_curve_coefficients,
            "conductive_heat_flux_moment_factor_policy": self.collision.conductive_heat_flux_moment_factor_policy,
            "conductive_heat_flux_moment_factor": self.collision.conductive_heat_flux_moment_factor,
            "conductive_heat_flux_dispersion_target": self.collision.conductive_heat_flux_dispersion_target,
            "conductive_heat_flux_diagonal_low_mode_target": (
                self.collision.conductive_heat_flux_diagonal_low_mode_target
            ),
            "conductive_heat_flux_galilean_correction_factor": (
                self.collision.conductive_heat_flux_galilean_correction_factor
            ),
            "acoustic_phase_correction_enabled": self.collision.acoustic_phase_correction_enabled,
            "acoustic_phase_correction_low_laplacian": (
                self.collision.acoustic_phase_correction_low_laplacian
            ),
            "acoustic_phase_diagonal_low_mode_factor": (
                self.collision.acoustic_phase_diagonal_low_mode_factor
            ),
            "acoustic_phase_high_mode_policy": self.collision.acoustic_phase_high_mode_policy,
            "acoustic_phase_high_mode_factor": self.collision.acoustic_phase_high_mode_factor,
            "acoustic_phase_high_mode_diagonal_factor": (
                self.collision.acoustic_phase_high_mode_diagonal_factor
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
    trace_bulk_policy = str(collision.get("trace_bulk_policy", TRACE_BULK_POLICY_CURRENT_ZERO))
    trace_bulk_calibration_id = collision.get("trace_bulk_calibration_id", None)
    if trace_bulk_calibration_id is not None:
        trace_bulk_calibration_id = str(trace_bulk_calibration_id)

    trace_bulk_projector_alpha_curve = dict(
        collision.get("trace_bulk_projector_alpha_curve", {}) or {}
    )
    trace_bulk_projector_alpha_curve_coefficients = tuple(
        float(item) for item in trace_bulk_projector_alpha_curve.get("coefficients", ())
    )
    if (
        trace_bulk_policy == TRACE_BULK_POLICY_GHOST_ORTHOGONAL_SPECTRAL
        and not trace_bulk_projector_alpha_curve_coefficients
    ):
        trace_bulk_projector_alpha_curve_coefficients = (
            GHOST_ORTHOGONAL_TRACE_ALPHA_INTERCEPT,
            GHOST_ORTHOGONAL_TRACE_ALPHA_SLOPE,
        )
    trace_bulk_projector_low_laplacian = float(
        collision.get(
            "trace_bulk_projector_low_laplacian",
            collision.get("dispersion_correction_low_laplacian", 0.0),
        )
    )
    trace_bulk_local_divergence_curve = dict(
        collision.get("trace_bulk_local_divergence_curve", {}) or {}
    )
    trace_bulk_local_divergence_curve_coefficients = tuple(
        float(item) for item in trace_bulk_local_divergence_curve.get("coefficients", ())
    )
    if not trace_bulk_local_divergence_curve_coefficients:
        if trace_bulk_policy in {
            TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL,
            TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_PRESSURE_MEMORY,
        }:
            trace_bulk_local_divergence_curve_coefficients = (
                GHOST_ORTHOGONAL_LOCAL_TRACE_DIVERGENCE_INTERCEPT,
                GHOST_ORTHOGONAL_LOCAL_TRACE_DIVERGENCE_SLOPE,
            )
        elif trace_bulk_policy == TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL:
            trace_bulk_local_divergence_curve_coefficients = (
                GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL_ACOUSTIC_INTERCEPT,
                GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL_ACOUSTIC_SLOPE,
            )
        elif trace_bulk_policy in {
            TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_LAPLACIAN,
            TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_ENTROPY_MANIFOLD,
        }:
            trace_bulk_local_divergence_curve_coefficients = (
                GHOST_ORTHOGONAL_LOCAL_LAPLACIAN_DIVERGENCE_INTERCEPT,
                GHOST_ORTHOGONAL_LOCAL_LAPLACIAN_DIVERGENCE_SLOPE,
            )
    trace_bulk_local_thermal_curve = dict(
        collision.get("trace_bulk_local_thermal_curve", {}) or {}
    )
    trace_bulk_local_thermal_curve_coefficients = tuple(
        float(item) for item in trace_bulk_local_thermal_curve.get("coefficients", ())
    )
    if (
        trace_bulk_policy
        in {
            TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL,
            TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_ENTROPY_MANIFOLD,
        }
        and not trace_bulk_local_thermal_curve_coefficients
    ):
        trace_bulk_local_thermal_curve_coefficients = (
            GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL_THERMAL_INTERCEPT,
            GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL_THERMAL_SLOPE,
        )
    trace_bulk_local_laplacian_curve = dict(
        collision.get("trace_bulk_local_laplacian_curve", {}) or {}
    )
    trace_bulk_local_laplacian_curve_coefficients = tuple(
        float(item) for item in trace_bulk_local_laplacian_curve.get("coefficients", ())
    )
    if (
        trace_bulk_policy
        in {
            TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_LAPLACIAN,
            TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_ENTROPY_MANIFOLD,
        }
        and not trace_bulk_local_laplacian_curve_coefficients
    ):
        trace_bulk_local_laplacian_curve_coefficients = (
            GHOST_ORTHOGONAL_LOCAL_LAPLACIAN_COEFFICIENT_INTERCEPT,
            GHOST_ORTHOGONAL_LOCAL_LAPLACIAN_COEFFICIENT_SLOPE,
        )

    deviatoric_stress_policy = str(
        collision.get("deviatoric_stress_policy", DEVIATORIC_STRESS_POLICY_MEASURED)
    )
    deviatoric_strain_rate_curve = dict(
        collision.get("deviatoric_strain_rate_curve", {}) or {}
    )
    deviatoric_strain_rate_curve_coefficients = tuple(
        float(item) for item in deviatoric_strain_rate_curve.get("coefficients", ())
    )

    regularized_heat_flux_factor = collision.get("regularized_heat_flux_factor", 0.0)
    regularized_heat_flux_factor_policy = str(
        collision.get("regularized_heat_flux_factor_policy", "specified")
    )
    if isinstance(regularized_heat_flux_factor, str):
        regularized_heat_flux_factor_policy = regularized_heat_flux_factor
        regularized_heat_flux_factor = 0.0

    heat_flux_retention_policy = str(
        collision.get("heat_flux_retention_policy", regularized_heat_flux_factor_policy)
    )
    if heat_flux_retention_policy != regularized_heat_flux_factor_policy and heat_flux_retention_policy != "specified":
        regularized_heat_flux_factor_policy = heat_flux_retention_policy

    heat_flux_retention_curve = dict(collision.get("heat_flux_retention_curve", {}) or {})
    heat_flux_retention_curve_coefficients = tuple(
        float(item) for item in heat_flux_retention_curve.get("coefficients", ())
    )

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
        trace_bulk_policy=trace_bulk_policy,
        trace_bulk_scale=float(collision.get("trace_bulk_scale", 1.0)),
        trace_bulk_calibration_id=trace_bulk_calibration_id,
        trace_bulk_projector_alpha_curve_type=str(
            trace_bulk_projector_alpha_curve.get("type", "affine")
        ),
        trace_bulk_projector_alpha_curve_coefficients=trace_bulk_projector_alpha_curve_coefficients,
        trace_bulk_projector_low_laplacian=trace_bulk_projector_low_laplacian,
        trace_bulk_local_divergence_curve_type=str(
            trace_bulk_local_divergence_curve.get("type", "affine")
        ),
        trace_bulk_local_divergence_curve_coefficients=trace_bulk_local_divergence_curve_coefficients,
        trace_bulk_local_thermal_curve_type=str(
            trace_bulk_local_thermal_curve.get("type", "affine")
        ),
        trace_bulk_local_thermal_curve_coefficients=trace_bulk_local_thermal_curve_coefficients,
        trace_bulk_local_laplacian_curve_type=str(
            trace_bulk_local_laplacian_curve.get("type", "affine")
        ),
        trace_bulk_local_laplacian_curve_coefficients=trace_bulk_local_laplacian_curve_coefficients,
        deviatoric_stress_policy=deviatoric_stress_policy,
        deviatoric_strain_rate_curve_type=str(deviatoric_strain_rate_curve.get("type", "affine")),
        deviatoric_strain_rate_curve_coefficients=deviatoric_strain_rate_curve_coefficients,
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
        regularized_heat_flux_diagonal_low_mode_target=float(
            collision.get("regularized_heat_flux_diagonal_low_mode_target", 1.0)
        ),
        regularized_heat_flux_f_fraction=float(collision.get("regularized_heat_flux_f_fraction", 0.5714285714285714)),
        heat_flux_retention_policy=heat_flux_retention_policy,
        heat_flux_retention_curve_type=str(heat_flux_retention_curve.get("type", "affine")),
        heat_flux_retention_curve_coefficients=heat_flux_retention_curve_coefficients,
        conductive_heat_flux_moment_factor_policy=conductive_heat_flux_moment_factor_policy,
        conductive_heat_flux_moment_factor=float(conductive_heat_flux_moment_factor),
        conductive_heat_flux_dispersion_target=float(
            collision.get("conductive_heat_flux_dispersion_target", 1.0)
        ),
        conductive_heat_flux_diagonal_low_mode_target=float(
            collision.get("conductive_heat_flux_diagonal_low_mode_target", 1.0)
        ),
        conductive_heat_flux_galilean_correction_factor=float(
            collision.get("conductive_heat_flux_galilean_correction_factor", 0.0)
        ),
        acoustic_phase_correction_enabled=bool(
            collision.get("acoustic_phase_correction_enabled", False)
        ),
        acoustic_phase_correction_low_laplacian=float(
            collision.get(
                "acoustic_phase_correction_low_laplacian",
                collision.get("dispersion_correction_low_laplacian", 0.0),
            )
        ),
        acoustic_phase_diagonal_low_mode_factor=float(
            collision.get("acoustic_phase_diagonal_low_mode_factor", 1.0)
        ),
        acoustic_phase_high_mode_policy=str(
            collision.get(
                "acoustic_phase_high_mode_policy",
                ACOUSTIC_PHASE_HIGH_MODE_POLICY_SPECIFIED,
            )
        ),
        acoustic_phase_high_mode_factor=float(
            collision.get("acoustic_phase_high_mode_factor", 1.0)
        ),
        acoustic_phase_high_mode_diagonal_factor=float(
            collision.get(
                "acoustic_phase_high_mode_diagonal_factor",
                collision.get("acoustic_phase_high_mode_factor", 1.0),
            )
        ),
    )


def regularized_heat_flux_factor_from_tau32(
    tau32: float,
    *,
    policy: str = AUTO_TAU32_LINEAR_HEAT_FLUX_POLICY,
    curve_type: str = "affine",
    coefficients: tuple[float, ...] = (),
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
    elif policy == HEAT_FLUX_RETENTION_POLICY_CALIBRATED_CURVE:
        return _heat_flux_retention_curve_value(
            tau32,
            curve_type=curve_type,
            coefficients=coefficients,
        )
    else:
        raise ValueError(f"unknown regularized_heat_flux_factor_policy: {policy}")
    return intercept + slope * (tau32 - 0.5)


def _heat_flux_retention_curve_value(
    tau32: float,
    *,
    curve_type: str,
    coefficients: tuple[float, ...],
) -> float:
    x = float(tau32) - 0.5
    if curve_type == "affine":
        if len(coefficients) != 2:
            raise ValueError("affine heat_flux_retention_curve requires [a, b]")
        a, b = coefficients
        return a + b * x
    if curve_type == "quadratic":
        if len(coefficients) != 3:
            raise ValueError("quadratic heat_flux_retention_curve requires [a, b, c]")
        a, b, c = coefficients
        return a + b * x + c * x * x
    if curve_type == "piecewise_affine":
        if len(coefficients) < 4 or len(coefficients) % 2 != 0:
            raise ValueError("piecewise_affine heat_flux_retention_curve requires [x0, y0, x1, y1, ...]")
        points = sorted(
            (float(coefficients[index]), float(coefficients[index + 1]))
            for index in range(0, len(coefficients), 2)
        )
        if any(np.isclose(points[index][0], points[index - 1][0]) for index in range(1, len(points))):
            raise ValueError("piecewise_affine heat_flux_retention_curve x values must be unique")
        if x <= points[0][0]:
            left, right = points[0], points[1]
        elif x >= points[-1][0]:
            left, right = points[-2], points[-1]
        else:
            left, right = next(
                (points[index - 1], points[index])
                for index in range(1, len(points))
                if points[index - 1][0] <= x <= points[index][0]
            )
        slope = (right[1] - left[1]) / (right[0] - left[0])
        return left[1] + slope * (x - left[0])
    raise ValueError(f"unknown heat_flux_retention_curve type: {curve_type}")


def trace_bulk_projector_alpha_from_tau32(
    tau32: float,
    *,
    curve_type: str,
    coefficients: tuple[float, ...],
) -> float:
    """Return the spectral trace/bulk projector amplitude alpha_h(tau32)."""

    x = float(tau32) - 0.5
    if curve_type == "constant":
        if len(coefficients) != 1:
            raise ValueError("constant trace_bulk_projector_alpha_curve requires [a]")
        return float(coefficients[0])
    if curve_type == "affine":
        if len(coefficients) != 2:
            raise ValueError("affine trace_bulk_projector_alpha_curve requires [a, b]")
        a, b = coefficients
        return float(a + b * x)
    if curve_type == "quadratic":
        if len(coefficients) != 3:
            raise ValueError("quadratic trace_bulk_projector_alpha_curve requires [a, b, c]")
        a, b, c = coefficients
        return float(a + b * x + c * x * x)
    raise ValueError(f"unknown trace_bulk_projector_alpha_curve type: {curve_type}")


def trace_bulk_local_divergence_factor_from_tau32(
    tau32: float,
    *,
    curve_type: str,
    coefficients: tuple[float, ...],
) -> float:
    """Return chi(tau32) for the local hydrodynamic trace divergence channel."""

    x = float(tau32) - 0.5
    if curve_type == "constant":
        if len(coefficients) != 1:
            raise ValueError("constant trace_bulk_local_divergence_curve requires [a]")
        return float(coefficients[0])
    if curve_type == "affine":
        if len(coefficients) != 2:
            raise ValueError("affine trace_bulk_local_divergence_curve requires [a, b]")
        a, b = coefficients
        return float(a + b * x)
    if curve_type == "quadratic":
        if len(coefficients) != 3:
            raise ValueError("quadratic trace_bulk_local_divergence_curve requires [a, b, c]")
        a, b, c = coefficients
        return float(a + b * x + c * x * x)
    raise ValueError(f"unknown trace_bulk_local_divergence_curve type: {curve_type}")


def trace_bulk_local_thermal_factor_from_tau32(
    tau32: float,
    *,
    curve_type: str,
    coefficients: tuple[float, ...],
) -> float:
    """Return chi_t(tau32) for the two-channel local thermal trace channel."""

    x = float(tau32) - 0.5
    if curve_type == "constant":
        if len(coefficients) != 1:
            raise ValueError("constant trace_bulk_local_thermal_curve requires [a]")
        return float(coefficients[0])
    if curve_type == "affine":
        if len(coefficients) != 2:
            raise ValueError("affine trace_bulk_local_thermal_curve requires [a, b]")
        a, b = coefficients
        return float(a + b * x)
    if curve_type == "quadratic":
        if len(coefficients) != 3:
            raise ValueError("quadratic trace_bulk_local_thermal_curve requires [a, b, c]")
        a, b, c = coefficients
        return float(a + b * x + c * x * x)
    raise ValueError(f"unknown trace_bulk_local_thermal_curve type: {curve_type}")


def trace_bulk_local_laplacian_factor_from_tau32(
    tau32: float,
    *,
    curve_type: str,
    coefficients: tuple[float, ...],
) -> float:
    """Return b(tau32) for local trace ``a*div(u) + b*(-L div(u))``."""

    x = float(tau32) - 0.5
    if curve_type == "constant":
        if len(coefficients) != 1:
            raise ValueError("constant trace_bulk_local_laplacian_curve requires [b]")
        return float(coefficients[0])
    if curve_type == "affine":
        if len(coefficients) != 2:
            raise ValueError("affine trace_bulk_local_laplacian_curve requires [a, b]")
        a, b = coefficients
        return float(a + b * x)
    if curve_type == "quadratic":
        if len(coefficients) != 3:
            raise ValueError("quadratic trace_bulk_local_laplacian_curve requires [a, b, c]")
        a, b, c = coefficients
        return float(a + b * x + c * x * x)
    raise ValueError(f"unknown trace_bulk_local_laplacian_curve type: {curve_type}")


def deviatoric_strain_rate_factor_from_tau21(
    tau21: float,
    *,
    curve_type: str,
    coefficients: tuple[float, ...],
) -> float:
    """Return the isotropic deviatoric strain-rate coefficient G(tau21).

    For ``deviatoric_stress_policy=strain_rate_isotropic`` the post-collision
    deviatoric stress is reconstructed from the finite-difference strain rate
    with a single coefficient, so transverse shear and longitudinal compression
    share one isotropic shear viscosity by construction rather than relaxing the
    measured central-moment stress with separate xy/normal factors.
    """

    x = float(tau21) - 0.5
    if curve_type == "constant":
        if len(coefficients) != 1:
            raise ValueError("constant deviatoric_strain_rate_curve requires [a]")
        return float(coefficients[0])
    if curve_type == "affine":
        if len(coefficients) != 2:
            raise ValueError("affine deviatoric_strain_rate_curve requires [a, b]")
        a, b = coefficients
        return float(a + b * x)
    if curve_type == "quadratic":
        if len(coefficients) != 3:
            raise ValueError("quadratic deviatoric_strain_rate_curve requires [a, b, c]")
        a, b, c = coefficients
        return float(a + b * x + c * x * x)
    raise ValueError(f"unknown deviatoric_strain_rate_curve type: {curve_type}")


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
    elif factor_policy == HEAT_FLUX_RETENTION_POLICY_CALIBRATED_CURVE:
        heat_flux_factor = regularized_heat_flux_factor_from_tau32(
            tau32,
            policy=factor_policy,
            curve_type=collision.heat_flux_retention_curve_type,
            coefficients=collision.heat_flux_retention_curve_coefficients,
        )
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
            "trace_bulk_policy": TRACE_BULK_POLICY_CURRENT_ZERO,
            "trace_bulk_scale": 1.0,
            "trace_bulk_calibration_id": None,
            "dispersion_correction_enabled": False,
            "regularized_shear_xy_factor": 0.965,
            "regularized_shear_normal_factor": 0.845,
            "regularized_heat_flux_factor": AUTO_TAU32_LINEAR_HEAT_FLUX_POLICY,
            "heat_flux_retention_policy": AUTO_TAU32_LINEAR_HEAT_FLUX_POLICY,
            "heat_flux_retention_curve": {
                "type": "affine",
                "coefficients": [
                    AUTO_TAU32_LINEAR_HEAT_FLUX_INTERCEPT,
                    AUTO_TAU32_LINEAR_HEAT_FLUX_SLOPE,
                ],
            },
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
        "deviatoric_stress_policy": DEVIATORIC_STRESS_POLICY_STRAIN_RATE_ISOTROPIC,
        "deviatoric_strain_rate_curve": {"type": "constant", "coefficients": [1.0]},
        "trace_bulk_policy": TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL,
        "trace_bulk_local_divergence_curve": {"type": "constant", "coefficients": [1.1052362846829455]},
        "regularized_shear_xy_factor": 0.4763606253137551,
        "regularized_shear_normal_factor": 0.8906391739599911,
        "dispersion_correction_enabled": True,
        "dispersion_correction_low_laplacian": 0.019261093311212455,
        "dispersion_correction_high_laplacian": 0.038429439193539104,
        "regularized_shear_xy_dispersion_target": 0.786,
        "regularized_shear_normal_dispersion_target": 0.785,
        "regularized_heat_flux_factor": AUTO_D2Q37_TAU32_LINEAR_HEAT_FLUX_POLICY,
        "heat_flux_retention_policy": AUTO_D2Q37_TAU32_LINEAR_HEAT_FLUX_POLICY,
        "heat_flux_retention_curve": {
            "type": "affine",
            "coefficients": [
                AUTO_D2Q37_TAU32_LINEAR_HEAT_FLUX_INTERCEPT,
                AUTO_D2Q37_TAU32_LINEAR_HEAT_FLUX_SLOPE,
            ],
        },
        "regularized_heat_flux_dispersion_target": 0.8512,
        "regularized_heat_flux_diagonal_low_mode_target": 0.908799,
        "conductive_heat_flux_moment_factor": 0.0422,
        "conductive_heat_flux_dispersion_target": 0.3201,
        "conductive_heat_flux_diagonal_low_mode_target": 0.610151,
        "conductive_heat_flux_galilean_correction_factor": 0.03835608923273733,
        "acoustic_phase_correction_enabled": True,
        "acoustic_phase_correction_low_laplacian": 0.019261093311212455,
        "acoustic_phase_diagonal_low_mode_factor": 0.98405,
        "acoustic_phase_high_mode_policy": ACOUSTIC_PHASE_HIGH_MODE_POLICY_SPECIFIED,
        "acoustic_phase_high_mode_factor": 1.0,
        "acoustic_phase_high_mode_diagonal_factor": 1.0,
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
    if mapping.collision.trace_bulk_policy not in {
        TRACE_BULK_POLICY_CURRENT_ZERO,
        TRACE_BULK_POLICY_TAU22,
        TRACE_BULK_POLICY_CALIBRATED,
        TRACE_BULK_POLICY_GHOST_ORTHOGONAL_SPECTRAL,
        TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL,
        TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_LAPLACIAN,
        TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_PRESSURE_MEMORY,
        TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL,
        TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_ENTROPY_MANIFOLD,
    }:
        raise ValueError(
            "trace_bulk_policy must be current_zero, tau22, calibrated, "
            "ghost_orthogonal_spectral, ghost_orthogonal_local, "
            "ghost_orthogonal_local_laplacian, "
            "ghost_orthogonal_local_pressure_memory, "
            "ghost_orthogonal_local_two_channel, "
            "or ghost_orthogonal_local_entropy_manifold"
        )
    if not np.isfinite(mapping.collision.trace_bulk_scale):
        raise ValueError("trace_bulk_scale must be finite")
    if mapping.collision.trace_bulk_policy == TRACE_BULK_POLICY_CALIBRATED:
        if not mapping.collision.trace_bulk_calibration_id:
            raise ValueError("calibrated trace_bulk_policy requires trace_bulk_calibration_id")
    if mapping.collision.trace_bulk_policy == TRACE_BULK_POLICY_GHOST_ORTHOGONAL_SPECTRAL:
        if mapping.lattice.velocity_set != "D2Q37":
            raise ValueError("ghost_orthogonal_spectral trace_bulk_policy is currently D2Q37-only")
        trace_bulk_projector_alpha_from_tau32(
            mapping.tau32,
            curve_type=mapping.collision.trace_bulk_projector_alpha_curve_type,
            coefficients=mapping.collision.trace_bulk_projector_alpha_curve_coefficients,
        )
        if not mapping.collision.trace_bulk_projector_low_laplacian > 0.0:
            raise ValueError("ghost_orthogonal_spectral requires trace_bulk_projector_low_laplacian > 0")
    if mapping.collision.trace_bulk_policy == TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL:
        if mapping.lattice.velocity_set != "D2Q37":
            raise ValueError("ghost_orthogonal_local trace_bulk_policy is currently D2Q37-only")
        trace_bulk_local_divergence_factor_from_tau32(
            mapping.tau32,
            curve_type=mapping.collision.trace_bulk_local_divergence_curve_type,
            coefficients=mapping.collision.trace_bulk_local_divergence_curve_coefficients,
        )
    if mapping.collision.trace_bulk_policy == TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_PRESSURE_MEMORY:
        if mapping.lattice.velocity_set != "D2Q37":
            raise ValueError(
                "ghost_orthogonal_local_pressure_memory trace_bulk_policy is currently D2Q37-only"
            )
        trace_bulk_local_divergence_factor_from_tau32(
            mapping.tau32,
            curve_type=mapping.collision.trace_bulk_local_divergence_curve_type,
            coefficients=mapping.collision.trace_bulk_local_divergence_curve_coefficients,
        )
    if mapping.collision.trace_bulk_policy == TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL:
        if mapping.lattice.velocity_set != "D2Q37":
            raise ValueError(
                "ghost_orthogonal_local_two_channel trace_bulk_policy is currently D2Q37-only"
            )
        trace_bulk_local_divergence_factor_from_tau32(
            mapping.tau32,
            curve_type=mapping.collision.trace_bulk_local_divergence_curve_type,
            coefficients=mapping.collision.trace_bulk_local_divergence_curve_coefficients,
        )
        trace_bulk_local_thermal_factor_from_tau32(
            mapping.tau32,
            curve_type=mapping.collision.trace_bulk_local_thermal_curve_type,
            coefficients=mapping.collision.trace_bulk_local_thermal_curve_coefficients,
        )
    if mapping.collision.trace_bulk_policy == TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_ENTROPY_MANIFOLD:
        if mapping.lattice.velocity_set != "D2Q37":
            raise ValueError(
                "ghost_orthogonal_local_entropy_manifold trace_bulk_policy is currently D2Q37-only"
            )
        trace_bulk_local_divergence_factor_from_tau32(
            mapping.tau32,
            curve_type=mapping.collision.trace_bulk_local_divergence_curve_type,
            coefficients=mapping.collision.trace_bulk_local_divergence_curve_coefficients,
        )
        trace_bulk_local_laplacian_factor_from_tau32(
            mapping.tau32,
            curve_type=mapping.collision.trace_bulk_local_laplacian_curve_type,
            coefficients=mapping.collision.trace_bulk_local_laplacian_curve_coefficients,
        )
        trace_bulk_local_thermal_factor_from_tau32(
            mapping.tau32,
            curve_type=mapping.collision.trace_bulk_local_thermal_curve_type,
            coefficients=mapping.collision.trace_bulk_local_thermal_curve_coefficients,
        )
    if mapping.collision.trace_bulk_policy == TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_LAPLACIAN:
        if mapping.lattice.velocity_set != "D2Q37":
            raise ValueError("ghost_orthogonal_local_laplacian trace_bulk_policy is currently D2Q37-only")
        trace_bulk_local_divergence_factor_from_tau32(
            mapping.tau32,
            curve_type=mapping.collision.trace_bulk_local_divergence_curve_type,
            coefficients=mapping.collision.trace_bulk_local_divergence_curve_coefficients,
        )
        trace_bulk_local_laplacian_factor_from_tau32(
            mapping.tau32,
            curve_type=mapping.collision.trace_bulk_local_laplacian_curve_type,
            coefficients=mapping.collision.trace_bulk_local_laplacian_curve_coefficients,
        )
    if mapping.collision.deviatoric_stress_policy not in {
        DEVIATORIC_STRESS_POLICY_MEASURED,
        DEVIATORIC_STRESS_POLICY_STRAIN_RATE_ISOTROPIC,
    }:
        raise ValueError("deviatoric_stress_policy must be measured or strain_rate_isotropic")
    if mapping.collision.deviatoric_stress_policy == DEVIATORIC_STRESS_POLICY_STRAIN_RATE_ISOTROPIC:
        if not mapping.collision.deviatoric_strain_rate_curve_coefficients:
            raise ValueError(
                "strain_rate_isotropic deviatoric_stress_policy requires deviatoric_strain_rate_curve coefficients"
            )
        deviatoric_strain_rate_factor_from_tau21(
            mapping.tau21,
            curve_type=mapping.collision.deviatoric_strain_rate_curve_type,
            coefficients=mapping.collision.deviatoric_strain_rate_curve_coefficients,
        )
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
            mapping.collision.regularized_heat_flux_diagonal_low_mode_target,
            mapping.collision.conductive_heat_flux_dispersion_target,
            mapping.collision.conductive_heat_flux_diagonal_low_mode_target,
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
    if mapping.collision.heat_flux_retention_policy != mapping.collision.regularized_heat_flux_factor_policy:
        raise ValueError("heat_flux_retention_policy must match regularized_heat_flux_factor_policy")
    if mapping.collision.heat_flux_retention_policy == HEAT_FLUX_RETENTION_POLICY_CALIBRATED_CURVE:
        regularized_heat_flux_factor_from_tau32(
            mapping.tau32,
            policy=mapping.collision.heat_flux_retention_policy,
            curve_type=mapping.collision.heat_flux_retention_curve_type,
            coefficients=mapping.collision.heat_flux_retention_curve_coefficients,
        )
    if not np.isfinite(mapping.collision.regularized_heat_flux_factor):
        raise ValueError("regularized_heat_flux_factor must be finite")
    if mapping.collision.conductive_heat_flux_moment_factor <= 0.0:
        raise ValueError("conductive_heat_flux_moment_factor must be positive")
    if not np.isfinite(mapping.collision.conductive_heat_flux_galilean_correction_factor):
        raise ValueError("conductive_heat_flux_galilean_correction_factor must be finite")
    if mapping.collision.acoustic_phase_correction_enabled:
        if mapping.lattice.velocity_set != "D2Q37":
            raise ValueError("acoustic_phase_correction is currently D2Q37-only")
        if not mapping.collision.acoustic_phase_correction_low_laplacian > 0.0:
            raise ValueError("acoustic_phase_correction_low_laplacian must be positive")
        if not np.isfinite(mapping.collision.acoustic_phase_diagonal_low_mode_factor):
            raise ValueError("acoustic_phase_diagonal_low_mode_factor must be finite")
        if mapping.collision.acoustic_phase_diagonal_low_mode_factor <= 0.0:
            raise ValueError("acoustic_phase_diagonal_low_mode_factor must be positive")
        if mapping.collision.acoustic_phase_high_mode_policy not in {
            ACOUSTIC_PHASE_HIGH_MODE_POLICY_SPECIFIED,
            ACOUSTIC_PHASE_HIGH_MODE_POLICY_FULL_MODAL_TARGET,
        }:
            raise ValueError("unknown acoustic_phase_high_mode_policy")
        for value in (
            mapping.collision.acoustic_phase_high_mode_factor,
            mapping.collision.acoustic_phase_high_mode_diagonal_factor,
        ):
            if not np.isfinite(value):
                raise ValueError("acoustic_phase high-mode factors must be finite")
            if value <= 0.0:
                raise ValueError("acoustic_phase high-mode factors must be positive")


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


def heat_flux_phys_to_lu(q_phys: np.ndarray, mapping: UnitMapping) -> np.ndarray:
    return np.asarray(q_phys) / mapping.heat_flux_scale
