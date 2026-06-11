"""Real Prandtl-number scan for Phase 2 P2-7."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from core.unit_mapping import create_unit_mapping
from verification.shear_wave_measurement import measure_shear_wave
from verification.thermal_diffusion_measurement import measure_thermal_diffusion


DEFAULT_PR_TARGETS = (0.5, 0.7061328707, 1.0, 2.0)
DEFAULT_SCAN_TOLERANCE = 0.05
DEFAULT_BASELINE_TOLERANCE = 0.03


@dataclass(frozen=True)
class PrandtlScanSettings:
    pr_targets: tuple[float, ...] = DEFAULT_PR_TARGETS
    scan_tolerance: float = DEFAULT_SCAN_TOLERANCE
    baseline_tolerance: float = DEFAULT_BASELINE_TOLERANCE
    baseline_pr: float = 0.7061328707
    shear_wave: dict[str, Any] = field(default_factory=dict)
    thermal_diffusion: dict[str, Any] = field(default_factory=dict)


def _compact_transport_settings(kind: str) -> dict[str, Any]:
    if kind == "shear":
        return {
            "nx": 64,
            "ny": 64,
            "steps": 240,
            "sample_interval": 1,
            "mode_index": 1,
            "amplitude": 1.0e-5,
            "fit_start": 10,
            "directions": ["x"],
            "relative_tolerance": 0.05,
        }
    if kind == "thermal":
        return {
            "nx": 64,
            "ny": 64,
            "steps": 320,
            "sample_interval": 1,
            "mode_index": 1,
            "amplitude": 1.0e-5,
            "fit_start": 10,
            "directions": ["x"],
            "relative_tolerance": 0.05,
            "heat_flux_tolerance": 0.05,
        }
    raise ValueError("kind must be shear or thermal")


def _settings_from_config(config: dict[str, Any]) -> PrandtlScanSettings:
    p2 = dict(config.get("p2_07_prandtl_scan", {}) or {})
    targets = p2.get("pr_targets", DEFAULT_PR_TARGETS)
    if isinstance(targets, int | float):
        targets = [targets]
    pr_targets = tuple(float(item) for item in targets)
    if not pr_targets:
        pr_targets = DEFAULT_PR_TARGETS

    shear_wave = _compact_transport_settings("shear")
    shear_wave.update(dict(p2.get("shear_wave", {}) or {}))
    thermal_diffusion = _compact_transport_settings("thermal")
    thermal_diffusion.update(dict(p2.get("thermal_diffusion", {}) or {}))

    physical = dict(config.get("physical", {}) or {})
    baseline_pr = float(p2.get("baseline_pr", physical.get("Pr", 0.7061328707)))
    return PrandtlScanSettings(
        pr_targets=pr_targets,
        scan_tolerance=float(p2.get("scan_tolerance", DEFAULT_SCAN_TOLERANCE)),
        baseline_tolerance=float(p2.get("baseline_tolerance", DEFAULT_BASELINE_TOLERANCE)),
        baseline_pr=baseline_pr,
        shear_wave=shear_wave,
        thermal_diffusion=thermal_diffusion,
    )


def _point_config(config: dict[str, Any], pr_target: float, settings: PrandtlScanSettings) -> dict[str, Any]:
    point_config = deepcopy(config)
    physical = dict(point_config.get("physical", {}) or {})
    nu0 = float(physical.get("nu0_m2_s", 1.57e-5))
    physical["nu0_m2_s"] = nu0
    physical["alpha0_m2_s"] = nu0 / pr_target
    physical["Pr"] = pr_target
    physical.setdefault("gamma", 1.4)
    point_config["physical"] = physical
    point_config["p2_04_shear_wave"] = dict(settings.shear_wave)
    point_config["p2_05_thermal_diffusion"] = dict(settings.thermal_diffusion)
    point_config["case"] = dict(point_config.get("case", {}) or {})
    point_config["case"]["name"] = f"p2_07_prandtl_scan_Pr_{pr_target:g}"
    return point_config


def _finite_ratio(numerator: float, denominator: float) -> float:
    if not np.isfinite(numerator) or not np.isfinite(denominator) or denominator == 0.0:
        return np.nan
    return float(numerator / denominator)


def _point_tolerance(pr_target: float, settings: PrandtlScanSettings) -> float:
    if np.isclose(pr_target, settings.baseline_pr, rtol=0.0, atol=1.0e-12):
        return settings.baseline_tolerance
    return settings.scan_tolerance


def measure_prandtl_scan_point(
    config: dict[str, Any],
    pr_target: float,
    settings: PrandtlScanSettings,
) -> dict[str, Any]:
    point_config = _point_config(config, pr_target, settings)
    mapping = create_unit_mapping(point_config)
    shear = measure_shear_wave(point_config)
    thermal = measure_thermal_diffusion(point_config)
    nu_measured = shear["nu_measured_lu"]
    alpha_measured = thermal["alpha_measured_lu"]
    pr_measured = _finite_ratio(nu_measured, alpha_measured)
    pr_relative_error = abs(pr_measured / pr_target - 1.0) if np.isfinite(pr_measured) else np.nan
    tolerance = _point_tolerance(pr_target, settings)
    passed = (
        shear["p2_04_status"] == "PASSED"
        and thermal["p2_05_status"] == "PASSED"
        and np.isfinite(pr_relative_error)
        and pr_relative_error <= tolerance
    )
    return {
        "pr_target": float(pr_target),
        "pr_measured": float(pr_measured) if np.isfinite(pr_measured) else np.nan,
        "pr_relative_error": float(pr_relative_error) if np.isfinite(pr_relative_error) else np.nan,
        "point_tolerance": float(tolerance),
        "status": "PASSED" if passed else "FAILED",
        "nu_target_lu": shear["nu_target_lu"],
        "nu_measured_lu": nu_measured,
        "nu_relative_error": shear["relative_error"],
        "alpha_target_lu": thermal["alpha_target_lu"],
        "alpha_measured_lu": alpha_measured,
        "alpha_relative_error": thermal["relative_error"],
        "tau21": mapping.tau21,
        "tau32": mapping.tau32,
        "central_moment_closure": mapping.collision.central_moment_closure,
        "high_order_relaxation": mapping.collision.high_order_relaxation,
        "dispersion_correction_enabled": mapping.collision.dispersion_correction_enabled,
        "regularized_shear_xy_dispersion_target": mapping.collision.regularized_shear_xy_dispersion_target,
        "regularized_shear_normal_dispersion_target": mapping.collision.regularized_shear_normal_dispersion_target,
        "regularized_heat_flux_factor": mapping.collision.regularized_heat_flux_factor,
        "regularized_heat_flux_factor_policy": mapping.collision.regularized_heat_flux_factor_policy,
        "regularized_heat_flux_dispersion_target": mapping.collision.regularized_heat_flux_dispersion_target,
        "conductive_heat_flux_moment_factor": mapping.collision.conductive_heat_flux_moment_factor,
        "conductive_heat_flux_moment_factor_policy": mapping.collision.conductive_heat_flux_moment_factor_policy,
        "conductive_heat_flux_dispersion_target": mapping.collision.conductive_heat_flux_dispersion_target,
        "heat_flux_relative_error": thermal["heat_flux_relative_error"],
        "heat_flux_sign_passed": thermal["heat_flux_sign_passed"],
        "shear_status": shear["p2_04_status"],
        "thermal_status": thermal["p2_05_status"],
        "first_invalid_step": min(
            step
            for step in (shear["first_invalid_step"], thermal["first_invalid_step"])
            if step is not None
        )
        if shear["first_invalid_step"] is not None or thermal["first_invalid_step"] is not None
        else None,
        "nan_detected": shear["nan_detected"] or thermal["nan_detected"],
        "clipping_used": shear["clipping_used"] or thermal["clipping_used"],
        "shear": shear,
        "thermal": thermal,
    }


def _measured_pr_span(scan_points: list[dict[str, Any]]) -> float:
    measured = [point["pr_measured"] for point in scan_points if np.isfinite(point["pr_measured"])]
    if len(measured) < 2:
        return np.nan
    return float(max(measured) - min(measured))


def measure_prandtl_scan(config: dict[str, Any]) -> dict[str, Any]:
    settings = _settings_from_config(config)
    scan_points = [
        measure_prandtl_scan_point(config, pr_target, settings)
        for pr_target in settings.pr_targets
    ]
    finite_errors = [
        point["pr_relative_error"]
        for point in scan_points
        if np.isfinite(point["pr_relative_error"])
    ]
    max_relative_error = float(max(finite_errors)) if finite_errors else np.nan
    baseline_points = [
        point
        for point in scan_points
        if np.isclose(point["pr_target"], settings.baseline_pr, rtol=0.0, atol=1.0e-12)
    ]
    baseline = baseline_points[0] if baseline_points else scan_points[0]
    passed = all(point["status"] == "PASSED" for point in scan_points)
    return {
        "p2_07_status": "PASSED" if passed else "FAILED",
        "pr_targets": [float(item) for item in settings.pr_targets],
        "scan_tolerance": float(settings.scan_tolerance),
        "baseline_tolerance": float(settings.baseline_tolerance),
        "baseline_pr": float(settings.baseline_pr),
        "baseline_pr_measured": baseline["pr_measured"],
        "baseline_pr_relative_error": baseline["pr_relative_error"],
        "max_pr_relative_error": max_relative_error,
        "measured_pr_span": _measured_pr_span(scan_points),
        "scan_points": scan_points,
        "first_invalid_step": min(
            step
            for step in (point["first_invalid_step"] for point in scan_points)
            if step is not None
        )
        if any(point["first_invalid_step"] is not None for point in scan_points)
        else None,
        "nan_detected": any(point["nan_detected"] for point in scan_points),
        "clipping_used": any(point["clipping_used"] for point in scan_points),
        "acceptance": {
            "baseline_pr_relative_error_max": float(settings.baseline_tolerance),
            "scan_pr_relative_error_max": float(settings.scan_tolerance),
            "requires_p2_04_pass": True,
            "requires_p2_05_pass": True,
            "requires_no_nan": True,
            "requires_no_clipping": True,
        },
    }
