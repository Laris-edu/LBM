"""Diagnose D2Q37 acoustic attenuation closure candidates.

Usage:
    python -m scripts.diagnose_phase2_d2q37_acoustic_attenuation
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import platform
import sys
from typing import Any

import numpy as np

import core.collision_smrt as collision_smrt
import core.unit_mapping as unit_mapping
from core.equilibrium import equilibrium_fg
from core.solver import GasSolver2D
from scripts.run_m2_verification import load_config, sha256_file, summary_payload_digest
from verification.acoustic_wave_measurement import measure_acoustic_wave
from verification.galilean_consistency_measurement import measure_galilean_consistency
from verification.prandtl_scan_measurement import measure_prandtl_scan
from verification.thermal_diffusion_measurement import measure_thermal_diffusion


DEFAULT_PR_TARGETS = (0.5, 0.7061328707, 1.0, 2.0)
LOW_K_GHOST_STABILITY_RADIUS_MAX = 1.01
DEFAULT_TRACE_BOUNDARY_HEAT_FACTOR_MIN = -0.70
DEFAULT_TRACE_BOUNDARY_HEAT_FACTOR_MAX = -0.20
DEFAULT_TRACE_BOUNDARY_HEAT_FACTOR_COUNT = 51
DEFAULT_GHOST_PROJECTOR_HEAT_COEFFICIENTS = (-0.504500678278, 0.726698353929)
DEFAULT_GHOST_PROJECTOR_ALPHA_COEFFICIENTS = (0.699947491657, -1.152605711210)


@dataclass(frozen=True)
class HeatFluxCurve:
    name: str
    curve_type: str
    coefficients: tuple[float, ...]

    def value(self, tau32: float) -> float:
        return unit_mapping.regularized_heat_flux_factor_from_tau32(
            tau32,
            policy=unit_mapping.HEAT_FLUX_RETENTION_POLICY_CALIBRATED_CURVE,
            curve_type=self.curve_type,
            coefficients=self.coefficients,
        )


@dataclass(frozen=True)
class SymbolResult:
    sigma_lu: float
    reference_lu: float
    ratio: float
    signed_relative_error: float
    phase_speed_lu: float
    phase_speed_relative_error: float
    lambda_abs: float
    lambda_angle: float


@dataclass(frozen=True)
class LowKGhostStability:
    spectral_radius_max: float
    max_k_label: str
    unstable_count: int
    radius_limit: float
    passed: bool


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and np.isnan(value):
        return None
    return value


def _format_value(value: Any) -> str:
    if value is None:
        return "none"
    if isinstance(value, float):
        if value != value:
            return "not_recorded"
        return f"{value:.6g}"
    return str(value)


def _heat_curves(
    curve_type: str,
    coefficients: tuple[float, ...],
    *,
    affine_intercepts: tuple[float, ...] = (),
    affine_slopes: tuple[float, ...] = (),
) -> list[HeatFluxCurve]:
    """Return a small diagnostic grid around the current D2Q37 closure."""

    slope = unit_mapping.AUTO_D2Q37_TAU32_LINEAR_HEAT_FLUX_SLOPE
    current = unit_mapping.AUTO_D2Q37_TAU32_LINEAR_HEAT_FLUX_INTERCEPT
    if affine_intercepts or affine_slopes:
        if curve_type != "affine":
            raise ValueError("heat affine coefficient grids require --heat-curve-type affine")
        if coefficients:
            raise ValueError("use either --heat-curve-coefficients or affine coefficient grids, not both")
        if not affine_intercepts or not affine_slopes:
            raise ValueError("both --heat-affine-intercept-grid and --heat-affine-slope-grid are required")
        return [
            HeatFluxCurve(f"affine_i{i}_j{j}", "affine", (intercept, slope_value))
            for i, intercept in enumerate(affine_intercepts)
            for j, slope_value in enumerate(affine_slopes)
        ]
    if coefficients:
        return [HeatFluxCurve(f"custom_{curve_type}", curve_type, coefficients)]
    if curve_type != "affine":
        raise ValueError("non-affine heat curve scans require --heat-curve-coefficients")
    return [
        HeatFluxCurve("current", "affine", (current, slope)),
        HeatFluxCurve("intercept_minus_0p012", "affine", (current - 0.012, slope)),
        HeatFluxCurve("intercept_minus_0p006", "affine", (current - 0.006, slope)),
        HeatFluxCurve("intercept_plus_0p006", "affine", (current + 0.006, slope)),
        HeatFluxCurve("intercept_plus_0p012", "affine", (current + 0.012, slope)),
    ]


def _candidate_config(
    base_config: dict[str, Any],
    *,
    pr_target: float | None,
    trace_policy: str,
    trace_scale: float,
    heat_curve: HeatFluxCurve,
    include_high_mode: bool = True,
) -> dict[str, Any]:
    config = deepcopy(base_config)
    if pr_target is not None:
        physical = dict(config.get("physical", {}) or {})
        nu0 = float(physical.get("nu0_m2_s", 1.57e-5))
        physical["nu0_m2_s"] = nu0
        physical["alpha0_m2_s"] = nu0 / float(pr_target)
        physical["Pr"] = float(pr_target)
        config["physical"] = physical

    collision = dict(config.get("collision", {}) or {})
    collision["trace_bulk_policy"] = trace_policy
    collision["trace_bulk_scale"] = float(trace_scale)
    if trace_policy == unit_mapping.TRACE_BULK_POLICY_CALIBRATED:
        collision["trace_bulk_calibration_id"] = "diagnostic_candidate"
    else:
        collision.setdefault("trace_bulk_calibration_id", None)
    collision["heat_flux_retention_curve"] = {
        "type": heat_curve.curve_type,
        "coefficients": list(heat_curve.coefficients),
    }
    if heat_curve.name == "current":
        current_policy = collision.get(
            "regularized_heat_flux_factor",
            unit_mapping.AUTO_D2Q37_TAU32_LINEAR_HEAT_FLUX_POLICY,
        )
        collision["regularized_heat_flux_factor"] = current_policy
        collision["heat_flux_retention_policy"] = collision.get(
            "heat_flux_retention_policy",
            current_policy if isinstance(current_policy, str) else "specified",
        )
    else:
        collision["regularized_heat_flux_factor"] = unit_mapping.HEAT_FLUX_RETENTION_POLICY_CALIBRATED_CURVE
        collision["heat_flux_retention_policy"] = unit_mapping.HEAT_FLUX_RETENTION_POLICY_CALIBRATED_CURVE
    config["collision"] = collision
    if not include_high_mode:
        p2_09 = dict(config.get("p2_09_galilean_consistency", {}) or {})
        p2_09["run_high_mode_acoustic_diagnostic"] = False
        config["p2_09_galilean_consistency"] = p2_09
    return config


def _build_symbol(config: dict[str, Any], k: float) -> tuple[np.ndarray, Any, Any]:
    solver = GasSolver2D(config)
    mapping = solver.mapping
    lattice = solver.lattice
    q = int(lattice.q)
    n_state = 2 * q

    rho0 = mapping.lattice.rho_ref_lu
    theta0 = mapping.theta_ref_lu
    f0, g0 = equilibrium_fg(
        np.ones((1, 1)) * rho0,
        np.zeros((1, 1, 2), dtype=float),
        np.ones((1, 1)) * theta0,
        mapping.lattice.S,
        lattice,
    )
    f_base, g_base = collision_smrt.collide_fg(f0, g0, mapping, lattice=lattice)
    y_base = np.concatenate([f_base.reshape(q), g_base.reshape(q)])

    eps = 1.0e-8
    jacobian = np.empty((n_state, n_state), dtype=float)
    for index in range(n_state):
        f_probe = f0.copy()
        g_probe = g0.copy()
        if index < q:
            f_probe.reshape(q)[index] += eps
        else:
            g_probe.reshape(q)[index - q] += eps
        f_post, g_post = collision_smrt.collide_fg(f_probe, g_probe, mapping, lattice=lattice)
        y_post = np.concatenate([f_post.reshape(q), g_post.reshape(q)])
        jacobian[:, index] = (y_post - y_base) / eps

    streaming_phase = np.exp(-1j * k * lattice.c[:, 0])
    streaming = np.concatenate([streaming_phase, streaming_phase])
    filter_config = config.get("numerics", {}).get("high_wavenumber_filter", {}) or {}
    strength = float(filter_config.get("strength", 0.0)) if bool(filter_config.get("enabled", False)) else 0.0
    mu = 4.0 * math.sin(0.5 * k) ** 2
    filter_multiplier = 1.0 - strength * mu * mu
    symbol = (streaming * filter_multiplier)[:, None] * jacobian
    return symbol, mapping, lattice


def _linear_observables(vector: np.ndarray, mapping: Any, lattice: Any) -> dict[str, complex]:
    q = int(lattice.q)
    df = np.asarray(vector[:q], dtype=complex)
    dg = np.asarray(vector[q:], dtype=complex)
    rho0 = mapping.lattice.rho_ref_lu
    theta0 = mapping.theta_ref_lu
    degrees = float(mapping.lattice.D + mapping.lattice.S)

    rho_prime = np.sum(df)
    momentum_prime = np.einsum("a,ai->i", df, lattice.c)
    c2 = np.sum(lattice.c * lattice.c, axis=-1)
    internal_prime = 0.5 * np.sum(df * c2) + np.sum(dg)
    theta_prime = 2.0 * internal_prime / (degrees * rho0) - theta0 * rho_prime / rho0
    pressure_prime = theta0 * rho_prime + rho0 * theta_prime
    return {
        "rho": rho_prime,
        "ux": momentum_prime[0] / rho0,
        "uy": momentum_prime[1] / rho0,
        "theta": theta_prime,
        "pressure": pressure_prime,
    }


def _acoustic_reference(mapping: Any, k: float) -> float:
    coeff = (
        0.5 * (mapping.physical.gamma - 1.0) * mapping.alpha_lu
        + ((mapping.lattice.D - 1.0) / mapping.lattice.D) * mapping.nu_lu
        + 0.5 * mapping.nu_b_lu
    )
    return float(coeff * k * k)


def _thermal_reference(mapping: Any, k: float) -> float:
    return float(mapping.alpha_lu * k * k)


def _eigenpairs(symbol: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    values, vectors = np.linalg.eig(symbol)
    return values, vectors


def _select_acoustic_mode(values: np.ndarray, vectors: np.ndarray, mapping: Any, k: float) -> tuple[complex, np.ndarray]:
    c_target = float(math.sqrt(mapping.physical.gamma * mapping.theta_ref_lu))
    candidates: list[tuple[float, complex, np.ndarray]] = []
    for index, value in enumerate(values):
        magnitude = abs(value)
        if magnitude <= 0.0 or not np.isfinite(magnitude):
            continue
        phase_speed = -float(np.angle(value)) / k
        speed_error = abs(abs(phase_speed) / c_target - 1.0)
        candidates.append((speed_error, value, vectors[:, index]))
    if not candidates:
        raise RuntimeError("no acoustic eigenvalue candidates found")
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1], candidates[0][2]


def _select_acoustic_indices(values: np.ndarray, mapping: Any, k: float) -> list[int]:
    """Return the two propagating acoustic indices closest to target sound speed."""

    c_target = float(math.sqrt(mapping.physical.gamma * mapping.theta_ref_lu))
    candidates: list[tuple[float, int]] = []
    for index, value in enumerate(values):
        magnitude = abs(value)
        if magnitude <= 0.0 or not np.isfinite(magnitude):
            continue
        angle = abs(float(np.angle(value)))
        if angle <= 1.0e-5:
            continue
        phase_speed = -float(np.angle(value)) / k
        speed_error = abs(abs(phase_speed) / c_target - 1.0)
        candidates.append((speed_error, index))
    if len(candidates) < 2:
        raise RuntimeError("no acoustic eigenvalue pair found")
    candidates.sort(key=lambda item: item[0])
    return [candidates[0][1], candidates[1][1]]


def _acoustic_projector(symbol: np.ndarray, mapping: Any, k: float) -> tuple[np.ndarray, list[int]]:
    """Return the biorthogonal projector onto the two acoustic modes."""

    values, vectors = np.linalg.eig(symbol)
    acoustic_indices = _select_acoustic_indices(values, mapping, k)
    inverse_vectors = np.linalg.inv(vectors)
    projector = np.zeros_like(symbol, dtype=complex)
    for index in acoustic_indices:
        projector += np.outer(vectors[:, index], inverse_vectors[index, :])
    return projector, acoustic_indices


def _select_thermal_mode(
    values: np.ndarray,
    vectors: np.ndarray,
    mapping: Any,
    lattice: Any,
    k: float,
) -> tuple[complex, np.ndarray]:
    reference = _thermal_reference(mapping, k)
    candidates: list[tuple[float, complex, np.ndarray]] = []
    for index, value in enumerate(values):
        magnitude = abs(value)
        if magnitude <= 0.0 or not np.isfinite(magnitude):
            continue
        angle = abs(float(np.angle(value)))
        sigma = -math.log(magnitude)
        if angle > 1.0e-3 or sigma <= 0.0 or sigma > 1.0e-3:
            continue
        obs = _linear_observables(vectors[:, index], mapping, lattice)
        theta_amp = abs(obs["theta"])
        pressure_amp = abs(obs["pressure"])
        if theta_amp <= 1.0e-14:
            continue
        pressure_score = pressure_amp / theta_amp
        sigma_score = abs(sigma / reference - 1.0) if reference > 0.0 else abs(sigma)
        candidates.append((sigma_score + 0.05 * pressure_score, value, vectors[:, index]))
    if not candidates:
        raise RuntimeError("no thermal eigenvalue candidates found")
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1], candidates[0][2]


def _symbol_result(value: complex, reference: float, mapping: Any, k: float, *, acoustic: bool) -> SymbolResult:
    magnitude = abs(value)
    sigma = -math.log(magnitude)
    phase_speed = -float(np.angle(value)) / k
    if acoustic:
        c_target = float(math.sqrt(mapping.physical.gamma * mapping.theta_ref_lu))
        phase_error = abs(abs(phase_speed) / c_target - 1.0)
    else:
        phase_error = abs(float(np.angle(value)))
    ratio = sigma / reference if reference != 0.0 else np.nan
    return SymbolResult(
        sigma_lu=float(sigma),
        reference_lu=float(reference),
        ratio=float(ratio),
        signed_relative_error=float(ratio - 1.0) if np.isfinite(ratio) else np.nan,
        phase_speed_lu=float(phase_speed),
        phase_speed_relative_error=float(phase_error),
        lambda_abs=float(magnitude),
        lambda_angle=float(np.angle(value)),
    )


def _low_k_ghost_stability(config: dict[str, Any]) -> LowKGhostStability:
    """Check full low-k symbol stability, including non-hydrodynamic trace modes."""

    k_values = (
        ("k0", 0.0),
        ("mode1", 2.0 * math.pi / float(config.get("p2_05_thermal_diffusion", {}).get("nx", 64))),
    )
    spectral_radius_max = -np.inf
    max_k_label = "not_evaluated"
    unstable_count = 0
    for label, k in k_values:
        symbol, _, _ = _build_symbol(config, k)
        values = np.linalg.eigvals(symbol)
        radii = np.abs(values)
        if not np.all(np.isfinite(radii)):
            spectral_radius = np.inf
            count = radii.size
        else:
            spectral_radius = float(np.max(radii))
            count = int(np.count_nonzero(radii > LOW_K_GHOST_STABILITY_RADIUS_MAX))
        if spectral_radius > spectral_radius_max:
            spectral_radius_max = spectral_radius
            max_k_label = label
        unstable_count += count
    return LowKGhostStability(
        spectral_radius_max=float(spectral_radius_max),
        max_k_label=max_k_label,
        unstable_count=int(unstable_count),
        radius_limit=LOW_K_GHOST_STABILITY_RADIUS_MAX,
        passed=bool(spectral_radius_max <= LOW_K_GHOST_STABILITY_RADIUS_MAX and unstable_count == 0),
    )


def _affine_value(tau: float, coefficients: tuple[float, float]) -> float:
    intercept, slope = coefficients
    return float(intercept + slope * (float(tau) - 0.5))


def _build_ghost_orthogonal_projector_symbol(
    base_config: dict[str, Any],
    *,
    pr_target: float,
    heat_curve: HeatFluxCurve,
    alpha_coefficients: tuple[float, float],
    k: float,
) -> tuple[np.ndarray, Any, Any, float, list[int]]:
    """Build the symbol-level ghost-orthogonal trace projector prototype.

    ``A0`` is the current-zero trace closure.  ``A1`` is the tau22
    ``trace_scale=1`` closure, which supplies the hydrodynamic trace update.
    The update is applied only after projecting the input perturbation onto the
    two acoustic modes of ``A0``.  At k=0 the acoustic projector is degenerate;
    for the low-k ghost gate we intentionally fall back to ``A0`` so pure trace
    ghost modes inherit the stable current-zero branch.
    """

    config_current_zero = _candidate_config(
        base_config,
        pr_target=pr_target,
        trace_policy=unit_mapping.TRACE_BULK_POLICY_CURRENT_ZERO,
        trace_scale=1.0,
        heat_curve=heat_curve,
    )
    symbol_current_zero, mapping, lattice = _build_symbol(config_current_zero, k)
    alpha_h = _affine_value(mapping.tau32, alpha_coefficients)
    if abs(k) <= 1.0e-14:
        return symbol_current_zero, mapping, lattice, alpha_h, []

    config_tau22 = _candidate_config(
        base_config,
        pr_target=pr_target,
        trace_policy=unit_mapping.TRACE_BULK_POLICY_TAU22,
        trace_scale=1.0,
        heat_curve=heat_curve,
    )
    symbol_tau22, _, _ = _build_symbol(config_tau22, k)
    projector, acoustic_indices = _acoustic_projector(symbol_current_zero, mapping, k)
    projected_update = (symbol_tau22 - symbol_current_zero) @ projector
    return symbol_current_zero + alpha_h * projected_update, mapping, lattice, alpha_h, acoustic_indices


def _low_k_ghost_orthogonal_projector_stability(
    base_config: dict[str, Any],
    *,
    heat_curve: HeatFluxCurve,
    alpha_coefficients: tuple[float, float],
) -> LowKGhostStability:
    """Check low-k stability for the ghost-orthogonal projector prototype."""

    k_values = (
        ("k0", 0.0),
        ("mode1", 2.0 * math.pi / float(base_config.get("p2_05_thermal_diffusion", {}).get("nx", 64))),
    )
    spectral_radius_max = -np.inf
    max_k_label = "not_evaluated"
    unstable_count = 0
    for label, k in k_values:
        symbol, _, _, _, _ = _build_ghost_orthogonal_projector_symbol(
            base_config,
            pr_target=DEFAULT_PR_TARGETS[1],
            heat_curve=heat_curve,
            alpha_coefficients=alpha_coefficients,
            k=k,
        )
        values = np.linalg.eigvals(symbol)
        radii = np.abs(values)
        if not np.all(np.isfinite(radii)):
            spectral_radius = np.inf
            count = radii.size
        else:
            spectral_radius = float(np.max(radii))
            count = int(np.count_nonzero(radii > LOW_K_GHOST_STABILITY_RADIUS_MAX))
        if spectral_radius > spectral_radius_max:
            spectral_radius_max = spectral_radius
            max_k_label = label
        unstable_count += count
    return LowKGhostStability(
        spectral_radius_max=float(spectral_radius_max),
        max_k_label=max_k_label,
        unstable_count=int(unstable_count),
        radius_limit=LOW_K_GHOST_STABILITY_RADIUS_MAX,
        passed=bool(spectral_radius_max <= LOW_K_GHOST_STABILITY_RADIUS_MAX and unstable_count == 0),
    )


def _evaluate_ghost_orthogonal_projector_case(
    base_config: dict[str, Any],
    *,
    heat_curve: HeatFluxCurve,
    alpha_coefficients: tuple[float, float],
    pr_target: float,
    n_equiv: int,
) -> dict[str, Any]:
    k = 2.0 * math.pi / float(n_equiv)
    symbol, mapping, lattice, alpha_h, acoustic_indices = _build_ghost_orthogonal_projector_symbol(
        base_config,
        pr_target=pr_target,
        heat_curve=heat_curve,
        alpha_coefficients=alpha_coefficients,
        k=k,
    )
    values, vectors = _eigenpairs(symbol)
    acoustic_value, acoustic_vector = _select_acoustic_mode(values, vectors, mapping, k)
    thermal_value, thermal_vector = _select_thermal_mode(values, vectors, mapping, lattice, k)
    acoustic = _symbol_result(acoustic_value, _acoustic_reference(mapping, k), mapping, k, acoustic=True)
    thermal = _symbol_result(thermal_value, _thermal_reference(mapping, k), mapping, k, acoustic=False)
    acoustic_obs = _linear_observables(acoustic_vector, mapping, lattice)
    thermal_obs = _linear_observables(thermal_vector, mapping, lattice)
    return {
        "closure": "ghost_orthogonal_projector",
        "heat_curve_type": heat_curve.curve_type,
        "heat_curve_coefficients": heat_curve.coefficients,
        "alpha_h_curve_type": "affine",
        "alpha_h_curve_coefficients": alpha_coefficients,
        "regularized_heat_flux_factor": heat_curve.value(mapping.tau32),
        "alpha_h": alpha_h,
        "hydrodynamic_trace_factor": -alpha_h,
        "ghost_trace_factor": 0.0,
        "pr_target": pr_target,
        "tau32": mapping.tau32,
        "n_equiv": n_equiv,
        "k_lu": k,
        "acoustic_projector_indices": acoustic_indices,
        "acoustic": acoustic.__dict__,
        "thermal": thermal.__dict__,
        "thermal_pressure_to_theta": (
            float(abs(thermal_obs["pressure"]) / abs(thermal_obs["theta"]))
            if abs(thermal_obs["theta"]) > 0.0
            else np.nan
        ),
        "acoustic_pressure_abs": float(abs(acoustic_obs["pressure"])),
        "spectral_radius": float(np.max(np.abs(values))),
    }


def _evaluate_ghost_orthogonal_projector(
    base_config: dict[str, Any],
    *,
    heat_coefficients: tuple[float, float],
    alpha_coefficients: tuple[float, float],
) -> dict[str, Any]:
    """Evaluate the derived ghost-orthogonal projector at symbol level."""

    heat_curve = HeatFluxCurve("ghost_orthogonal_affine", "affine", heat_coefficients)
    rows: list[dict[str, Any]] = []
    for pr_target in DEFAULT_PR_TARGETS:
        for n_equiv in (64, 512):
            rows.append(
                _evaluate_ghost_orthogonal_projector_case(
                    base_config,
                    heat_curve=heat_curve,
                    alpha_coefficients=alpha_coefficients,
                    pr_target=pr_target,
                    n_equiv=n_equiv,
                )
            )
    low_k_stability = _low_k_ghost_orthogonal_projector_stability(
        base_config,
        heat_curve=heat_curve,
        alpha_coefficients=alpha_coefficients,
    )
    n64_rows = [row for row in rows if row["n_equiv"] == 64]
    baseline_n64 = [
        row for row in n64_rows if np.isclose(row["pr_target"], DEFAULT_PR_TARGETS[1])
    ][0]
    baseline_n512 = [
        row
        for row in rows
        if row["n_equiv"] == 512 and np.isclose(row["pr_target"], DEFAULT_PR_TARGETS[1])
    ][0]
    thermal_error_max_n64 = float(max(abs(row["thermal"]["signed_relative_error"]) for row in n64_rows))
    acoustic_error_max_n64 = float(max(abs(row["acoustic"]["signed_relative_error"]) for row in n64_rows))
    baseline_acoustic_error_n64 = float(abs(baseline_n64["acoustic"]["signed_relative_error"]))
    baseline_acoustic_error_n512 = float(abs(baseline_n512["acoustic"]["signed_relative_error"]))
    spectral_radius_max = float(max(row["spectral_radius"] for row in rows))
    candidate_symbol_pass = bool(
        thermal_error_max_n64 <= 0.05
        and acoustic_error_max_n64 <= 0.25
        and baseline_acoustic_error_n512 <= 0.25
        and low_k_stability.passed
    )
    return {
        "closure": "ghost_orthogonal_projector",
        "status": "SPECTRAL_PROJECTOR_SYMBOL_EVALUATED",
        "heat_curve": heat_curve.__dict__,
        "alpha_h_curve": {
            "curve_type": "affine",
            "coefficients": alpha_coefficients,
        },
        "rows": rows,
        "summary": {
            "thermal_error_max_n64": thermal_error_max_n64,
            "acoustic_error_max_n64": acoustic_error_max_n64,
            "baseline_acoustic_error_n64": baseline_acoustic_error_n64,
            "baseline_acoustic_error_n512": baseline_acoustic_error_n512,
            "baseline_acoustic_ratio_n512": float(baseline_n512["acoustic"]["ratio"]),
            "spectral_radius_max": spectral_radius_max,
            "low_k_ghost_stability": low_k_stability.__dict__,
            "candidate_symbol_pass": candidate_symbol_pass,
            "dynamic_gate_status": "not_run_dynamic_disabled",
        },
        "interpretation": (
            "The projector separates r_g=0 trace ghost retention from hydrodynamic r_h=-alpha_h(tau32). "
            "The dynamic implementation is an explicit diagnostic spectral collision applied to low-k Fourier modes."
        ),
    }


def _default_trace_projector_low_laplacian(config: dict[str, Any]) -> float:
    collision = dict(config.get("collision", {}) or {})
    low_laplacian = float(collision.get("dispersion_correction_low_laplacian", 0.0))
    if low_laplacian > 0.0:
        return low_laplacian
    p2 = dict(config.get("p2_05_thermal_diffusion", {}) or {})
    nx = int(p2.get("nx", config.get("numerics", {}).get("nx", 64)))
    return float(8.0 * math.sin(math.pi / float(nx)) ** 2)


def _ghost_projector_dynamic_config(
    base_config: dict[str, Any],
    *,
    heat_curve: HeatFluxCurve,
    alpha_coefficients: tuple[float, float],
    include_high_mode: bool,
) -> dict[str, Any]:
    config = _candidate_config(
        base_config,
        pr_target=None,
        trace_policy=unit_mapping.TRACE_BULK_POLICY_GHOST_ORTHOGONAL_SPECTRAL,
        trace_scale=1.0,
        heat_curve=heat_curve,
        include_high_mode=include_high_mode,
    )
    collision = dict(config.get("collision", {}) or {})
    collision["trace_bulk_projector_alpha_curve"] = {
        "type": "affine",
        "coefficients": list(alpha_coefficients),
    }
    collision["trace_bulk_projector_low_laplacian"] = _default_trace_projector_low_laplacian(config)
    config["collision"] = collision
    return config


def _run_ghost_projector_dynamic_confirmation(
    base_config: dict[str, Any],
    *,
    heat_curve: HeatFluxCurve,
    alpha_coefficients: tuple[float, float],
    include_p2_9: bool,
    include_high_mode: bool,
) -> dict[str, Any]:
    config = _ghost_projector_dynamic_config(
        base_config,
        heat_curve=heat_curve,
        alpha_coefficients=alpha_coefficients,
        include_high_mode=include_high_mode,
    )
    thermal = measure_thermal_diffusion(deepcopy(config))
    acoustic = measure_acoustic_wave(deepcopy(config))
    pr_scan = measure_prandtl_scan(deepcopy(config))
    row: dict[str, Any] = {
        "trace_policy": unit_mapping.TRACE_BULK_POLICY_GHOST_ORTHOGONAL_SPECTRAL,
        "trace_scale": 1.0,
        "heat_curve_type": heat_curve.curve_type,
        "heat_curve_coefficients": heat_curve.coefficients,
        "alpha_h_curve_type": "affine",
        "alpha_h_curve_coefficients": alpha_coefficients,
        "trace_bulk_projector_low_laplacian": (
            config["collision"]["trace_bulk_projector_low_laplacian"]
        ),
        "p2_05_status": thermal["p2_05_status"],
        "alpha_relative_error": thermal["relative_error"],
        "heat_flux_relative_error": thermal["heat_flux_relative_error"],
        "p2_06_status": acoustic["p2_06_status"],
        "sound_speed_relative_error": acoustic["sound_speed_relative_error"],
        "gamma_relative_error": acoustic["gamma_relative_error"],
        "attenuation_ratio": (
            acoustic["acoustic_attenuation_measured_lu"]
            / acoustic["acoustic_attenuation_reference_lu"]
        ),
        "attenuation_relative_error": acoustic["acoustic_attenuation_relative_error"],
        "p2_07_status": pr_scan["p2_07_status"],
        "baseline_pr_relative_error": pr_scan["baseline_pr_relative_error"],
        "max_pr_relative_error": pr_scan["max_pr_relative_error"],
    }
    status_keys = ["p2_05_status", "p2_06_status", "p2_07_status"]
    if include_p2_9:
        galilean = measure_galilean_consistency(deepcopy(config))
        row.update(
            {
                "p2_09_status": galilean["p2_09_status"],
                "p2_09_max_sound_speed_relative_error": galilean["max_sound_speed_relative_error"],
                "p2_09_max_direction_difference": galilean["max_direction_difference"],
                "p2_09_dispersion_masking_status": galilean["dispersion_masking_status"],
            }
        )
        status_keys.append("p2_09_status")
    dynamic_pass = all(row[key] == "PASSED" for key in status_keys)
    if dynamic_pass and include_p2_9:
        gate_status = "passed"
    elif dynamic_pass:
        gate_status = "passed_without_p2_9"
    else:
        gate_status = "failed"
    return {
        "status": gate_status,
        "include_p2_9": include_p2_9,
        "include_high_mode": include_high_mode,
        "row": row,
    }


def _evaluate_symbol_case(
    base_config: dict[str, Any],
    *,
    trace_policy: str,
    trace_scale: float,
    heat_curve: HeatFluxCurve,
    pr_target: float,
    n_equiv: int,
) -> dict[str, Any]:
    config = _candidate_config(
        base_config,
        pr_target=pr_target,
        trace_policy=trace_policy,
        trace_scale=trace_scale,
        heat_curve=heat_curve,
    )
    k = 2.0 * math.pi / float(n_equiv)
    symbol, mapping, lattice = _build_symbol(config, k)
    values, vectors = _eigenpairs(symbol)
    acoustic_value, acoustic_vector = _select_acoustic_mode(values, vectors, mapping, k)
    thermal_value, thermal_vector = _select_thermal_mode(values, vectors, mapping, lattice, k)
    acoustic = _symbol_result(acoustic_value, _acoustic_reference(mapping, k), mapping, k, acoustic=True)
    thermal = _symbol_result(thermal_value, _thermal_reference(mapping, k), mapping, k, acoustic=False)
    acoustic_obs = _linear_observables(acoustic_vector, mapping, lattice)
    thermal_obs = _linear_observables(thermal_vector, mapping, lattice)
    low_k_stability = (
        _low_k_ghost_stability(config)
        if n_equiv == 64 and np.isclose(pr_target, DEFAULT_PR_TARGETS[1])
        else None
    )
    return {
        "trace_policy": trace_policy,
        "trace_scale": trace_scale,
        "heat_line": heat_curve.name,
        "heat_curve_type": heat_curve.curve_type,
        "heat_curve_coefficients": heat_curve.coefficients,
        "regularized_heat_flux_factor": heat_curve.value(mapping.tau32),
        "pr_target": pr_target,
        "tau32": mapping.tau32,
        "n_equiv": n_equiv,
        "k_lu": k,
        "acoustic": acoustic.__dict__,
        "thermal": thermal.__dict__,
        "thermal_pressure_to_theta": (
            float(abs(thermal_obs["pressure"]) / abs(thermal_obs["theta"]))
            if abs(thermal_obs["theta"]) > 0.0
            else np.nan
        ),
        "acoustic_pressure_abs": float(abs(acoustic_obs["pressure"])),
        "low_k_ghost_stability": low_k_stability.__dict__ if low_k_stability is not None else None,
    }

def _summarize_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, float, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["trace_policy"], float(row["trace_scale"]), row["heat_line"])
        grouped.setdefault(key, []).append(row)

    summary = []
    for (trace_policy, trace_scale, heat_line), items in grouped.items():
        baseline = [item for item in items if np.isclose(item["pr_target"], 0.7061328707)]
        low_k = [item for item in items if item["n_equiv"] == 512 and np.isclose(item["pr_target"], 0.7061328707)]
        transport_errors = [
            abs(item["thermal"]["signed_relative_error"])
            for item in items
            if item["n_equiv"] == 64 and np.isfinite(item["thermal"]["signed_relative_error"])
        ]
        acoustic_errors = [
            abs(item["acoustic"]["signed_relative_error"])
            for item in baseline
            if item["n_equiv"] == 64 and np.isfinite(item["acoustic"]["signed_relative_error"])
        ]
        low_k_stability_rows = [
            item["low_k_ghost_stability"]
            for item in baseline
            if item["n_equiv"] == 64 and item.get("low_k_ghost_stability") is not None
        ]
        low_k_stability = low_k_stability_rows[0] if low_k_stability_rows else None
        low_k_stability_passed = bool(low_k_stability and low_k_stability["passed"])
        low_k_spectral_radius = (
            float(low_k_stability["spectral_radius_max"]) if low_k_stability else np.nan
        )
        transport_error = float(max(transport_errors)) if transport_errors else np.nan
        acoustic_error = float(acoustic_errors[0]) if acoustic_errors else np.nan
        symbol_score = max(
            transport_error / 0.05 if np.isfinite(transport_error) else float("inf"),
            acoustic_error / 0.25 if np.isfinite(acoustic_error) else float("inf"),
            (
                low_k_spectral_radius / LOW_K_GHOST_STABILITY_RADIUS_MAX
                if np.isfinite(low_k_spectral_radius)
                else float("inf")
            ),
        )
        summary.append(
            {
                "trace_policy": trace_policy,
                "trace_scale": trace_scale,
                "heat_line": heat_line,
                "heat_curve_type": items[0]["heat_curve_type"],
                "heat_curve_coefficients": items[0]["heat_curve_coefficients"],
                "symbol_transport_error_max": transport_error,
                "baseline_acoustic_error_n64": acoustic_error,
                "baseline_acoustic_ratio_n512": (
                    float(low_k[0]["acoustic"]["ratio"]) if low_k else np.nan
                ),
                "low_k_ghost_spectral_radius_max": low_k_spectral_radius,
                "low_k_ghost_stability_pass": low_k_stability_passed,
                "low_k_ghost_unstable_count": (
                    int(low_k_stability["unstable_count"]) if low_k_stability else -1
                ),
                "low_k_ghost_max_k_label": (
                    str(low_k_stability["max_k_label"]) if low_k_stability else "not_recorded"
                ),
                "symbol_score": float(symbol_score),
                "candidate_symbol_pass": bool(
                    transport_errors
                    and max(transport_errors) <= 0.05
                    and acoustic_errors
                    and acoustic_errors[0] <= 0.25
                    and low_k_stability_passed
                ),
            }
        )
    summary.sort(
        key=lambda item: (
            not item["candidate_symbol_pass"],
            item["symbol_score"] if np.isfinite(item["symbol_score"]) else float("inf"),
        )
    )
    return summary


def _run_dynamic_confirmation(
    base_config: dict[str, Any],
    candidates: list[dict[str, Any]],
    heat_curves: list[HeatFluxCurve],
    *,
    include_p2_9: bool,
    include_high_mode: bool,
) -> list[dict[str, Any]]:
    rows = []
    for candidate in candidates:
        heat_curve = next(curve for curve in heat_curves if curve.name == candidate["heat_line"])
        config = _candidate_config(
            base_config,
            pr_target=None,
            trace_policy=candidate["trace_policy"],
            trace_scale=float(candidate["trace_scale"]),
            heat_curve=heat_curve,
            include_high_mode=include_high_mode,
        )
        thermal = measure_thermal_diffusion(deepcopy(config))
        acoustic = measure_acoustic_wave(deepcopy(config))
        pr_scan = measure_prandtl_scan(deepcopy(config))
        row = {
            "trace_policy": candidate["trace_policy"],
            "trace_scale": candidate["trace_scale"],
            "heat_line": candidate["heat_line"],
            "heat_curve_type": heat_curve.curve_type,
            "heat_curve_coefficients": heat_curve.coefficients,
            "p2_05_status": thermal["p2_05_status"],
            "alpha_relative_error": thermal["relative_error"],
            "heat_flux_relative_error": thermal["heat_flux_relative_error"],
            "p2_06_status": acoustic["p2_06_status"],
            "sound_speed_relative_error": acoustic["sound_speed_relative_error"],
            "gamma_relative_error": acoustic["gamma_relative_error"],
            "attenuation_ratio": (
                acoustic["acoustic_attenuation_measured_lu"] / acoustic["acoustic_attenuation_reference_lu"]
            ),
            "attenuation_relative_error": acoustic["acoustic_attenuation_relative_error"],
            "p2_07_status": pr_scan["p2_07_status"],
            "baseline_pr_relative_error": pr_scan["baseline_pr_relative_error"],
            "max_pr_relative_error": pr_scan["max_pr_relative_error"],
        }
        if include_p2_9:
            galilean = measure_galilean_consistency(deepcopy(config))
            row.update(
                {
                    "p2_09_status": galilean["p2_09_status"],
                    "p2_09_max_sound_speed_relative_error": galilean["max_sound_speed_relative_error"],
                    "p2_09_max_direction_difference": galilean["max_direction_difference"],
                    "p2_09_dispersion_masking_status": galilean["dispersion_masking_status"],
                }
            )
        rows.append(row)
    return rows


def _derive_nonamplifying_trace_boundary(
    base_config: dict[str, Any],
    *,
    trace_scales: tuple[float, ...],
    heat_factors: tuple[float, ...],
) -> dict[str, Any]:
    """Necessary-condition scan for scalar non-amplifying trace retention."""

    rows: list[dict[str, Any]] = []
    for trace_scale in trace_scales:
        for heat_factor in heat_factors:
            heat_curve = HeatFluxCurve("constant_h", "affine", (float(heat_factor), 0.0))
            config = _candidate_config(
                base_config,
                pr_target=DEFAULT_PR_TARGETS[1],
                trace_policy=unit_mapping.TRACE_BULK_POLICY_TAU22,
                trace_scale=float(trace_scale),
                heat_curve=heat_curve,
            )
            stability = _low_k_ghost_stability(config)
            if not stability.passed:
                continue
            row = _evaluate_symbol_case(
                base_config,
                trace_policy=unit_mapping.TRACE_BULK_POLICY_TAU22,
                trace_scale=float(trace_scale),
                heat_curve=heat_curve,
                pr_target=DEFAULT_PR_TARGETS[1],
                n_equiv=64,
            )
            thermal_error = abs(row["thermal"]["signed_relative_error"])
            acoustic_error = abs(row["acoustic"]["signed_relative_error"])
            score = max(
                thermal_error / 0.05 if np.isfinite(thermal_error) else float("inf"),
                acoustic_error / 0.25 if np.isfinite(acoustic_error) else float("inf"),
                stability.spectral_radius_max / stability.radius_limit,
            )
            rows.append(
                {
                    "trace_scale": float(trace_scale),
                    "trace_factor": -float(trace_scale),
                    "heat_factor": float(heat_factor),
                    "thermal_symbol_error": float(thermal_error),
                    "acoustic_symbol_error": float(acoustic_error),
                    "acoustic_symbol_ratio": float(row["acoustic"]["ratio"]),
                    "low_k_ghost_spectral_radius_max": stability.spectral_radius_max,
                    "score": float(score),
                    "boundary_pass": bool(thermal_error <= 0.05 and acoustic_error <= 0.25),
                }
            )

    rows.sort(key=lambda item: item["score"] if np.isfinite(item["score"]) else float("inf"))
    thermal_pass = [row for row in rows if row["thermal_symbol_error"] <= 0.05]
    acoustic_pass = [row for row in rows if row["acoustic_symbol_error"] <= 0.25]
    boundary_pass = [row for row in rows if row["boundary_pass"]]
    return {
        "scope": "baseline Pr, scalar trace retention, constant heat retention",
        "trace_policy": unit_mapping.TRACE_BULK_POLICY_TAU22,
        "trace_scale_grid": list(trace_scales),
        "heat_factor_grid": list(heat_factors),
        "row_count": len(rows),
        "boundary_pass_count": len(boundary_pass),
        "best_overall": rows[:10],
        "best_thermal_pass": thermal_pass[:10],
        "best_acoustic_pass": acoustic_pass[:10],
        "interpretation": (
            "No boundary pass means scalar non-amplifying trace retention plus scalar heat retention "
            "cannot satisfy even the baseline hydrodynamic thermal/acoustic symbol gates."
        ),
    }


def run_diagnostic(
    *,
    config_path: Path,
    output_root: Path,
    run_dynamic: bool,
    max_dynamic_candidates: int,
    trace_policies: tuple[str, ...],
    trace_scales: tuple[float, ...],
    heat_curve_type: str,
    heat_curve_coefficients: tuple[float, ...],
    heat_affine_intercepts: tuple[float, ...],
    heat_affine_slopes: tuple[float, ...],
    include_p2_9: bool,
    include_high_mode: bool,
    derive_nonamplifying_trace_boundary: bool,
    trace_boundary_heat_factors: tuple[float, ...],
    evaluate_ghost_orthogonal_projector: bool,
    ghost_projector_heat_coefficients: tuple[float, float],
    ghost_projector_alpha_coefficients: tuple[float, float],
) -> dict[str, Any]:
    base_config = load_config(config_path)
    trace_candidates = []
    for policy in trace_policies:
        if policy == unit_mapping.TRACE_BULK_POLICY_CURRENT_ZERO:
            trace_candidates.append((policy, 1.0))
        else:
            trace_candidates.extend((policy, scale) for scale in trace_scales)
    heat_curves = _heat_curves(
        heat_curve_type,
        heat_curve_coefficients,
        affine_intercepts=heat_affine_intercepts,
        affine_slopes=heat_affine_slopes,
    )
    pr_targets = list(DEFAULT_PR_TARGETS)
    n_values = [64, 512]

    rows: list[dict[str, Any]] = []
    for trace_policy, trace_scale in trace_candidates:
        for heat_curve in heat_curves:
            for pr_target in pr_targets:
                for n_equiv in n_values:
                    rows.append(
                        _evaluate_symbol_case(
                            base_config,
                            trace_policy=trace_policy,
                            trace_scale=trace_scale,
                            heat_curve=heat_curve,
                            pr_target=pr_target,
                            n_equiv=n_equiv,
                        )
                    )

    candidates = _summarize_candidates(rows)
    dynamic_candidates = [candidate for candidate in candidates if candidate["candidate_symbol_pass"]]
    selected_dynamic_candidates = dynamic_candidates[:max_dynamic_candidates]
    dynamic_rows = []
    if run_dynamic:
        dynamic_rows = _run_dynamic_confirmation(
            base_config,
            selected_dynamic_candidates,
            heat_curves,
            include_p2_9=include_p2_9,
            include_high_mode=include_high_mode,
        )
    trace_boundary = None
    if derive_nonamplifying_trace_boundary:
        heat_factor_grid = trace_boundary_heat_factors
        if not heat_factor_grid:
            heat_factor_grid = tuple(
                np.linspace(
                    DEFAULT_TRACE_BOUNDARY_HEAT_FACTOR_MIN,
                    DEFAULT_TRACE_BOUNDARY_HEAT_FACTOR_MAX,
                    DEFAULT_TRACE_BOUNDARY_HEAT_FACTOR_COUNT,
                )
            )
        trace_boundary = _derive_nonamplifying_trace_boundary(
            base_config,
        trace_scales=trace_scales,
        heat_factors=heat_factor_grid,
    )
    ghost_projector = None
    if evaluate_ghost_orthogonal_projector:
        ghost_projector = _evaluate_ghost_orthogonal_projector(
            base_config,
            heat_coefficients=ghost_projector_heat_coefficients,
            alpha_coefficients=ghost_projector_alpha_coefficients,
        )
        if run_dynamic and ghost_projector["summary"]["candidate_symbol_pass"]:
            heat_curve = HeatFluxCurve(
                "ghost_orthogonal_affine",
                "affine",
                ghost_projector_heat_coefficients,
            )
            dynamic_confirmation = _run_ghost_projector_dynamic_confirmation(
                base_config,
                heat_curve=heat_curve,
                alpha_coefficients=ghost_projector_alpha_coefficients,
                include_p2_9=include_p2_9,
                include_high_mode=include_high_mode,
            )
            ghost_projector["status"] = "DYNAMIC_PROJECTOR_EVALUATED"
            ghost_projector["dynamic_confirmation"] = dynamic_confirmation
            ghost_projector["summary"]["dynamic_gate_status"] = dynamic_confirmation["status"]
        elif run_dynamic:
            ghost_projector["dynamic_confirmation"] = {
                "status": "not_run_symbol_or_low_k_gate_failed",
                "include_p2_9": include_p2_9,
                "include_high_mode": include_high_mode,
                "row": None,
            }
            ghost_projector["summary"]["dynamic_gate_status"] = (
                "not_run_symbol_or_low_k_gate_failed"
            )
        else:
            ghost_projector["dynamic_confirmation"] = {
                "status": "not_run_dynamic_disabled",
                "include_p2_9": include_p2_9,
                "include_high_mode": include_high_mode,
                "row": None,
            }
            ghost_projector["summary"]["dynamic_gate_status"] = "not_run_dynamic_disabled"

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = output_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "run_id": run_id,
        "status": "DIAGNOSTIC_COMPLETE",
        "config_path": str(config_path),
        "config_sha256": sha256_file(config_path),
        "python": sys.version,
        "platform": platform.platform(),
        "trace_candidates": [
            {"trace_policy": name, "trace_scale": scale} for name, scale in trace_candidates
        ],
        "heat_curves": [curve.__dict__ for curve in heat_curves],
        "symbol_rows": rows,
        "candidate_summary": candidates,
        "dynamic_confirmation": dynamic_rows,
        "nonamplifying_trace_boundary": trace_boundary,
        "ghost_orthogonal_projector": ghost_projector,
        "interpretation": {
            "symbol_candidate_count": len(candidates),
            "symbol_pass_count": sum(1 for item in candidates if item["candidate_symbol_pass"]),
            "dynamic_enabled": run_dynamic,
            "dynamic_eligible_count": len(dynamic_candidates),
            "dynamic_selected_count": len(selected_dynamic_candidates) if run_dynamic else 0,
            "include_p2_9": include_p2_9,
            "include_high_mode": include_high_mode,
            "derive_nonamplifying_trace_boundary": derive_nonamplifying_trace_boundary,
            "evaluate_ghost_orthogonal_projector": evaluate_ghost_orthogonal_projector,
            "note": (
                "current_zero is the production trace closure; tau22/calibrated variants are diagnostic candidates. "
                "A production fix requires hydrodynamic symbol matching, low-k full-symbol ghost stability, "
                "and dynamic P2-5/P2-6/P2-7/P2-9 confirmation."
            ),
        },
    }
    payload["summary_digest"] = summary_payload_digest(payload)

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(_json_safe(payload), indent=2), encoding="utf-8")
    report_path = out_dir / "report.md"
    report_path.write_text(_render_report(payload), encoding="utf-8")
    return payload


def _render_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase 2 D2Q37 Acoustic Attenuation Closure Diagnostic",
        "",
        f"- run_id: `{payload['run_id']}`",
        f"- status: `{payload['status']}`",
        f"- config: `{payload['config_path']}`",
        f"- summary_digest: `{payload['summary_digest']}`",
        "",
        "## Candidate Summary",
        "",
        "| trace_policy | trace_scale | heat_line | max thermal symbol error | baseline acoustic error n64 | baseline acoustic ratio n512 | low-k ghost radius | ghost pass | score | symbol pass |",
        "|---|---:|---|---:|---:|---:|---:|---|---:|---|",
    ]
    for row in payload["candidate_summary"]:
        lines.append(
            "| "
            f"`{row['trace_policy']}` | "
            f"`{_format_value(row['trace_scale'])}` | "
            f"`{row['heat_line']}` | "
            f"`{_format_value(row['symbol_transport_error_max'])}` | "
            f"`{_format_value(row['baseline_acoustic_error_n64'])}` | "
            f"`{_format_value(row['baseline_acoustic_ratio_n512'])}` | "
            f"`{_format_value(row['low_k_ghost_spectral_radius_max'])}` | "
            f"`{row['low_k_ghost_stability_pass']}` | "
            f"`{_format_value(row['symbol_score'])}` | "
            f"`{row['candidate_symbol_pass']}` |"
        )
    if payload["dynamic_confirmation"]:
        lines.extend(
            [
                "",
                "## Dynamic Confirmation",
                "",
                "| trace_policy | trace_scale | heat_line | P2-5 | alpha err | P2-6 | attenuation ratio | attenuation err | P2-7 | max Pr err |",
                "|---|---:|---|---|---:|---|---:|---:|---|---:|",
            ]
        )
        for row in payload["dynamic_confirmation"]:
            lines.append(
                "| "
                f"`{row['trace_policy']}` | "
                f"`{_format_value(row['trace_scale'])}` | "
                f"`{row['heat_line']}` | "
                f"`{row['p2_05_status']}` | "
                f"`{_format_value(row['alpha_relative_error'])}` | "
                f"`{row['p2_06_status']}` | "
                f"`{_format_value(row['attenuation_ratio'])}` | "
                f"`{_format_value(row['attenuation_relative_error'])}` | "
                f"`{row['p2_07_status']}` | "
                f"`{_format_value(row['max_pr_relative_error'])}` |"
            )
    elif payload["interpretation"]["dynamic_enabled"]:
        lines.extend(
            [
                "",
                "## Dynamic Confirmation",
                "",
                "No dynamic confirmation was run because no candidate passed the hydrodynamic symbol and low-k ghost stability gates.",
            ]
        )
    if payload.get("nonamplifying_trace_boundary"):
        boundary = payload["nonamplifying_trace_boundary"]
        lines.extend(
            [
                "",
                "## Non-Amplifying Trace Boundary",
                "",
                f"- row_count: `{boundary['row_count']}`",
                f"- boundary_pass_count: `{boundary['boundary_pass_count']}`",
                "",
                "| trace_scale | trace_factor | heat_factor | thermal error | acoustic error | acoustic ratio | ghost radius | score | pass |",
                "|---:|---:|---:|---:|---:|---:|---:|---:|---|",
            ]
        )
        for row in boundary["best_overall"]:
            lines.append(
                "| "
                f"`{_format_value(row['trace_scale'])}` | "
                f"`{_format_value(row['trace_factor'])}` | "
                f"`{_format_value(row['heat_factor'])}` | "
                f"`{_format_value(row['thermal_symbol_error'])}` | "
                f"`{_format_value(row['acoustic_symbol_error'])}` | "
                f"`{_format_value(row['acoustic_symbol_ratio'])}` | "
                f"`{_format_value(row['low_k_ghost_spectral_radius_max'])}` | "
                f"`{_format_value(row['score'])}` | "
                f"`{row['boundary_pass']}` |"
            )
    if payload.get("ghost_orthogonal_projector"):
        projector = payload["ghost_orthogonal_projector"]
        summary = projector["summary"]
        stability = summary["low_k_ghost_stability"]
        lines.extend(
            [
                "",
                "## Ghost-Orthogonal Projector",
                "",
                f"- status: `{projector['status']}`",
                f"- heat_curve: `{projector['heat_curve']['coefficients']}`",
                f"- alpha_h_curve: `{projector['alpha_h_curve']['coefficients']}`",
                f"- candidate_symbol_pass: `{summary['candidate_symbol_pass']}`",
                f"- dynamic_gate_status: `{summary['dynamic_gate_status']}`",
                "",
                "| metric | value |",
                "|---|---:|",
                f"| thermal_error_max_n64 | `{_format_value(summary['thermal_error_max_n64'])}` |",
                f"| acoustic_error_max_n64 | `{_format_value(summary['acoustic_error_max_n64'])}` |",
                f"| baseline_acoustic_error_n64 | `{_format_value(summary['baseline_acoustic_error_n64'])}` |",
                f"| baseline_acoustic_error_n512 | `{_format_value(summary['baseline_acoustic_error_n512'])}` |",
                f"| baseline_acoustic_ratio_n512 | `{_format_value(summary['baseline_acoustic_ratio_n512'])}` |",
                f"| spectral_radius_max | `{_format_value(summary['spectral_radius_max'])}` |",
                f"| low_k_ghost_radius | `{_format_value(stability['spectral_radius_max'])}` |",
                f"| low_k_ghost_pass | `{stability['passed']}` |",
                "",
                "| Pr | n | h | alpha_h | acoustic err | thermal err | spectral radius |",
                "|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in projector["rows"]:
            lines.append(
                "| "
                f"`{_format_value(row['pr_target'])}` | "
                f"`{row['n_equiv']}` | "
                f"`{_format_value(row['regularized_heat_flux_factor'])}` | "
                f"`{_format_value(row['alpha_h'])}` | "
                f"`{_format_value(row['acoustic']['signed_relative_error'])}` | "
                f"`{_format_value(row['thermal']['signed_relative_error'])}` | "
                f"`{_format_value(row['spectral_radius'])}` |"
            )
        dynamic = projector.get("dynamic_confirmation", {})
        dynamic_row = dynamic.get("row")
        lines.extend(
            [
                "",
                "### Dynamic Confirmation",
                "",
                f"- status: `{dynamic.get('status', 'not_recorded')}`",
                f"- include_p2_9: `{dynamic.get('include_p2_9', False)}`",
                f"- include_high_mode: `{dynamic.get('include_high_mode', False)}`",
            ]
        )
        if dynamic_row is not None:
            lines.extend(
                [
                    "",
                    "| metric | value |",
                    "|---|---:|",
                    f"| P2-5 | `{dynamic_row['p2_05_status']}` |",
                    f"| alpha_relative_error | `{_format_value(dynamic_row['alpha_relative_error'])}` |",
                    f"| heat_flux_relative_error | `{_format_value(dynamic_row['heat_flux_relative_error'])}` |",
                    f"| P2-6 | `{dynamic_row['p2_06_status']}` |",
                    f"| attenuation_ratio | `{_format_value(dynamic_row['attenuation_ratio'])}` |",
                    f"| attenuation_relative_error | `{_format_value(dynamic_row['attenuation_relative_error'])}` |",
                    f"| P2-7 | `{dynamic_row['p2_07_status']}` |",
                    f"| max_pr_relative_error | `{_format_value(dynamic_row['max_pr_relative_error'])}` |",
                ]
            )
            if "p2_09_status" in dynamic_row:
                lines.extend(
                    [
                        f"| P2-9 | `{dynamic_row['p2_09_status']}` |",
                        f"| P2-9 sound_speed_error | `{_format_value(dynamic_row['p2_09_max_sound_speed_relative_error'])}` |",
                        f"| P2-9 direction_difference | `{_format_value(dynamic_row['p2_09_max_direction_difference'])}` |",
                        f"| P2-9 dispersion_masking | `{dynamic_row['p2_09_dispersion_masking_status']}` |",
                    ]
                )
        lines.extend(["", projector["interpretation"]])
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            payload["interpretation"]["note"],
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/gas_air_10k_d2q37_physical_timestep.yaml"))
    parser.add_argument("--output-root", type=Path, default=Path("results/phase2_d2q37_acoustic_attenuation_diagnostic"))
    parser.add_argument(
        "--trace-bulk-policy",
        nargs="+",
        choices=[
            unit_mapping.TRACE_BULK_POLICY_CURRENT_ZERO,
            unit_mapping.TRACE_BULK_POLICY_TAU22,
            unit_mapping.TRACE_BULK_POLICY_CALIBRATED,
        ],
        default=[unit_mapping.TRACE_BULK_POLICY_CURRENT_ZERO, unit_mapping.TRACE_BULK_POLICY_TAU22],
    )
    parser.add_argument("--trace-bulk-scale-grid", nargs="+", type=float, default=[0.8, 1.0, 1.2])
    parser.add_argument(
        "--heat-curve-type",
        choices=["affine", "quadratic", "piecewise_affine"],
        default="affine",
    )
    parser.add_argument("--heat-curve-coefficients", nargs="*", type=float, default=[])
    parser.add_argument(
        "--heat-affine-intercept-grid",
        nargs="*",
        type=float,
        default=[],
        help="Explicit affine intercept grid; requires --heat-affine-slope-grid",
    )
    parser.add_argument(
        "--heat-affine-slope-grid",
        nargs="*",
        type=float,
        default=[],
        help="Explicit affine slope grid; requires --heat-affine-intercept-grid",
    )
    parser.add_argument("--symbol-only", action="store_true")
    parser.add_argument(
        "--dynamic",
        action="store_true",
        help="Run slow P2-5/P2-6/P2-7 confirmation on candidates that passed symbol and ghost gates",
    )
    parser.add_argument("--max-dynamic-candidates", type=int, default=2)
    parser.add_argument("--include-p2-9", action="store_true", help="Include slow P2-9 Galilean dynamic confirmation")
    parser.add_argument("--include-high-mode", action="store_true", help="Keep high-mode acoustic diagnostic enabled in P2-9")
    parser.add_argument(
        "--derive-nonamplifying-trace-boundary",
        action="store_true",
        help="Scan the necessary scalar non-amplifying trace/constant heat boundary at baseline Pr",
    )
    parser.add_argument(
        "--trace-boundary-heat-factor-grid",
        nargs="*",
        type=float,
        default=[],
        help="Optional heat-factor grid for --derive-nonamplifying-trace-boundary",
    )
    parser.add_argument(
        "--evaluate-ghost-orthogonal-projector",
        action="store_true",
        help="Evaluate the symbol-level ghost-orthogonal acoustic trace projector prototype",
    )
    parser.add_argument(
        "--ghost-projector-heat-coefficients",
        nargs=2,
        type=float,
        default=list(DEFAULT_GHOST_PROJECTOR_HEAT_COEFFICIENTS),
        metavar=("INTERCEPT", "SLOPE"),
        help="Affine h(tau32) coefficients for the ghost-orthogonal projector prototype",
    )
    parser.add_argument(
        "--ghost-projector-alpha-coefficients",
        nargs=2,
        type=float,
        default=list(DEFAULT_GHOST_PROJECTOR_ALPHA_COEFFICIENTS),
        metavar=("INTERCEPT", "SLOPE"),
        help="Affine alpha_h(tau32) coefficients for the ghost-orthogonal projector prototype",
    )
    args = parser.parse_args()
    payload = run_diagnostic(
        config_path=args.config,
        output_root=args.output_root,
        run_dynamic=args.dynamic and not args.symbol_only,
        max_dynamic_candidates=args.max_dynamic_candidates,
        trace_policies=tuple(args.trace_bulk_policy),
        trace_scales=tuple(args.trace_bulk_scale_grid),
        heat_curve_type=args.heat_curve_type,
        heat_curve_coefficients=tuple(args.heat_curve_coefficients),
        heat_affine_intercepts=tuple(args.heat_affine_intercept_grid),
        heat_affine_slopes=tuple(args.heat_affine_slope_grid),
        include_p2_9=args.include_p2_9,
        include_high_mode=args.include_high_mode,
        derive_nonamplifying_trace_boundary=args.derive_nonamplifying_trace_boundary,
        trace_boundary_heat_factors=tuple(args.trace_boundary_heat_factor_grid),
        evaluate_ghost_orthogonal_projector=args.evaluate_ghost_orthogonal_projector,
        ghost_projector_heat_coefficients=tuple(args.ghost_projector_heat_coefficients),
        ghost_projector_alpha_coefficients=tuple(args.ghost_projector_alpha_coefficients),
    )
    print(json.dumps(_json_safe({
        "run_id": payload["run_id"],
        "status": payload["status"],
        "summary_digest": payload["summary_digest"],
        "best_candidates": payload["candidate_summary"][:5],
        "dynamic_confirmation": payload["dynamic_confirmation"],
        "nonamplifying_trace_boundary": payload["nonamplifying_trace_boundary"],
        "ghost_orthogonal_projector": payload["ghost_orthogonal_projector"],
    }), indent=2))


if __name__ == "__main__":
    main()
