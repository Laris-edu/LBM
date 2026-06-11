"""Robustness probes for Phase 2 P2-4/P2-5/P2-7 transport checks."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import numpy as np

from core.unit_mapping import create_unit_mapping
from verification.prandtl_scan_measurement import measure_prandtl_scan
from verification.shear_wave_measurement import measure_shear_wave
from verification.thermal_diffusion_measurement import measure_thermal_diffusion


def _merge_section(config: dict[str, Any], section: str, updates: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(config)
    existing = dict(merged.get(section, {}) or {})
    existing.update(deepcopy(updates))
    merged[section] = existing
    return merged


def _finite_max(values: list[float]) -> float:
    finite = [float(value) for value in values if np.isfinite(value)]
    return float(max(finite)) if finite else np.nan


def _mapping_payload(config: dict[str, Any]) -> dict[str, Any]:
    mapping = create_unit_mapping(config)
    return {
        "velocity_set": mapping.lattice.velocity_set,
        "Q": mapping.lattice.Q,
        "theta_q_lu": mapping.lattice.theta_q_lu,
        "theta_ref_lu": mapping.theta_ref_lu,
        "theta_transport_lu": mapping.theta_transport_lu,
        "nu_lu": mapping.nu_lu,
        "alpha_lu": mapping.alpha_lu,
        "tau21": mapping.tau21,
        "tau32": mapping.tau32,
        "bulk_viscosity_policy": mapping.collision.bulk_viscosity_policy,
        "central_moment_closure": mapping.collision.central_moment_closure,
        "high_order_relaxation": mapping.collision.high_order_relaxation,
        "dispersion_correction_enabled": mapping.collision.dispersion_correction_enabled,
        "dispersion_correction_low_laplacian": mapping.collision.dispersion_correction_low_laplacian,
        "dispersion_correction_high_laplacian": mapping.collision.dispersion_correction_high_laplacian,
        "regularized_shear_xy_dispersion_target": mapping.collision.regularized_shear_xy_dispersion_target,
        "regularized_shear_normal_dispersion_target": mapping.collision.regularized_shear_normal_dispersion_target,
        "regularized_heat_flux_factor_policy": mapping.collision.regularized_heat_flux_factor_policy,
        "regularized_heat_flux_factor": mapping.collision.regularized_heat_flux_factor,
        "regularized_heat_flux_dispersion_target": mapping.collision.regularized_heat_flux_dispersion_target,
        "regularized_heat_flux_f_fraction": mapping.collision.regularized_heat_flux_f_fraction,
        "conductive_heat_flux_moment_factor_policy": (
            mapping.collision.conductive_heat_flux_moment_factor_policy
        ),
        "conductive_heat_flux_moment_factor": mapping.collision.conductive_heat_flux_moment_factor,
        "conductive_heat_flux_dispersion_target": mapping.collision.conductive_heat_flux_dispersion_target,
    }


def transport_pair_scenario(
    base_config: dict[str, Any],
    *,
    name: str,
    description: str,
    shear_wave: dict[str, Any],
    thermal_diffusion: dict[str, Any],
    required_for_production: bool = True,
    config_role: str = "physical_timestep",
) -> dict[str, Any]:
    """Run one paired P2-4/P2-5 robustness scenario."""

    scenario_config = _merge_section(base_config, "p2_04_shear_wave", shear_wave)
    scenario_config = _merge_section(scenario_config, "p2_05_thermal_diffusion", thermal_diffusion)
    shear = measure_shear_wave(scenario_config)
    thermal = measure_thermal_diffusion(scenario_config)
    passed = shear["p2_04_status"] == "PASSED" and thermal["p2_05_status"] == "PASSED"
    return {
        "name": name,
        "description": description,
        "scenario_type": "p2_04_p2_05_pair",
        "config_role": config_role,
        "required_for_production": required_for_production,
        "status": "PASSED" if passed else "FAILED",
        "mapping": _mapping_payload(scenario_config),
        "settings": {
            "p2_04_shear_wave": deepcopy(shear_wave),
            "p2_05_thermal_diffusion": deepcopy(thermal_diffusion),
        },
        "p2_04_status": shear["p2_04_status"],
        "p2_04_max_relative_error": shear["relative_error"],
        "p2_04_first_invalid_step": shear["first_invalid_step"],
        "p2_04_nan_detected": shear["nan_detected"],
        "p2_04_negative_theta_detected": shear["negative_theta_detected"],
        "p2_04_clipping_used": shear["clipping_used"],
        "p2_05_status": thermal["p2_05_status"],
        "p2_05_max_relative_error": thermal["relative_error"],
        "p2_05_heat_flux_relative_error": thermal["heat_flux_relative_error"],
        "p2_05_first_invalid_step": thermal["first_invalid_step"],
        "p2_05_nan_detected": thermal["nan_detected"],
        "p2_05_negative_theta_detected": thermal["negative_theta_detected"],
        "p2_05_clipping_used": thermal["clipping_used"],
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


def prandtl_scan_scenario(
    base_config: dict[str, Any],
    *,
    name: str,
    description: str,
    prandtl_scan: dict[str, Any],
    required_for_production: bool = True,
    config_role: str = "physical_timestep",
) -> dict[str, Any]:
    """Run one P2-7 robustness scenario."""

    scenario_config = _merge_section(base_config, "p2_07_prandtl_scan", prandtl_scan)
    scan = measure_prandtl_scan(scenario_config)
    passed = scan["p2_07_status"] == "PASSED"
    return {
        "name": name,
        "description": description,
        "scenario_type": "p2_07_prandtl_scan",
        "config_role": config_role,
        "required_for_production": required_for_production,
        "status": "PASSED" if passed else "FAILED",
        "mapping": _mapping_payload(scenario_config),
        "settings": {"p2_07_prandtl_scan": deepcopy(prandtl_scan)},
        "p2_07_status": scan["p2_07_status"],
        "baseline_pr_relative_error": scan["baseline_pr_relative_error"],
        "max_pr_relative_error": scan["max_pr_relative_error"],
        "measured_pr_span": scan["measured_pr_span"],
        "first_invalid_step": scan["first_invalid_step"],
        "nan_detected": scan["nan_detected"],
        "clipping_used": scan["clipping_used"],
        "scan": scan,
    }


def summarize_robustness_scenarios(scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    required = [item for item in scenarios if item["required_for_production"]]
    diagnostic = [item for item in scenarios if not item["required_for_production"]]
    required_passed = all(item["status"] == "PASSED" for item in required)
    return {
        "required_physical_status": "PASSED" if required_passed else "FAILED",
        "diagnostic_control_status": "PASSED"
        if diagnostic and all(item["status"] == "PASSED" for item in diagnostic)
        else "FAILED"
        if diagnostic
        else "NOT_RUN",
        "production_physics_status": "NOT_PASSED" if not required_passed else "IN_PROGRESS",
        "m2_decision": "GO-RISK / ROBUSTNESS_FAILED" if not required_passed else "GO-RISK / ROBUSTNESS_PASSED",
        "scenario_count": len(scenarios),
        "required_scenario_count": len(required),
        "diagnostic_scenario_count": len(diagnostic),
        "failed_required_scenarios": [
            item["name"] for item in required if item["status"] != "PASSED"
        ],
        "failed_diagnostic_scenarios": [
            item["name"] for item in diagnostic if item["status"] != "PASSED"
        ],
        "max_p2_04_relative_error": _finite_max(
            [
                item.get("p2_04_max_relative_error", np.nan)
                for item in scenarios
                if item["scenario_type"] == "p2_04_p2_05_pair"
            ]
        ),
        "max_p2_05_relative_error": _finite_max(
            [
                item.get("p2_05_max_relative_error", np.nan)
                for item in scenarios
                if item["scenario_type"] == "p2_04_p2_05_pair"
            ]
        ),
        "max_p2_05_heat_flux_relative_error": _finite_max(
            [
                item.get("p2_05_heat_flux_relative_error", np.nan)
                for item in scenarios
                if item["scenario_type"] == "p2_04_p2_05_pair"
            ]
        ),
        "max_p2_07_pr_relative_error": _finite_max(
            [
                item.get("max_pr_relative_error", np.nan)
                for item in scenarios
                if item["scenario_type"] == "p2_07_prandtl_scan"
            ]
        ),
        "nan_detected": any(item["nan_detected"] for item in scenarios),
        "clipping_used": any(item["clipping_used"] for item in scenarios),
    }
