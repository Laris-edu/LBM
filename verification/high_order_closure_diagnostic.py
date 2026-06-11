"""Diagnostics for the D2Q21 fourth-order central-moment closure path."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import numpy as np

from verification.shear_wave_measurement import measure_shear_wave
from verification.thermal_diffusion_measurement import measure_thermal_diffusion


DEFAULT_HIGH_ORDER_TAU_VALUES = (0.7, 0.85, 1.0)
DEFAULT_TOLERANCE = 0.05


def _collision_config(base_config: dict[str, Any], tau: float) -> dict[str, Any]:
    config = deepcopy(base_config)
    collision = dict(config.get("collision", {}) or {})
    collision["central_moment_closure"] = "fourth_order"
    collision["high_order_relaxation"] = float(tau)
    config["collision"] = collision
    return config


def _with_shear_settings(config: dict[str, Any], *, mode_index: int, direction: str) -> dict[str, Any]:
    updated = deepcopy(config)
    updated["p2_04_shear_wave"] = {
        "nx": 64,
        "ny": 64,
        "steps": 120,
        "sample_interval": 1,
        "mode_index": mode_index,
        "amplitude": 1.0e-5,
        "fit_start": 10,
        "directions": [direction],
        "relative_tolerance": DEFAULT_TOLERANCE,
        "direction_tolerance": DEFAULT_TOLERANCE,
    }
    return updated


def _with_thermal_settings(config: dict[str, Any], *, mode_index: int) -> dict[str, Any]:
    updated = deepcopy(config)
    updated["p2_05_thermal_diffusion"] = {
        "nx": 64,
        "ny": 64,
        "steps": 160 if mode_index == 2 else 320,
        "sample_interval": 1,
        "mode_index": mode_index,
        "amplitude": 1.0e-5,
        "fit_start": 10,
        "directions": ["x"],
        "relative_tolerance": DEFAULT_TOLERANCE,
        "heat_flux_tolerance": DEFAULT_TOLERANCE,
    }
    return updated


def _shear_result(config: dict[str, Any], *, mode_index: int, direction: str) -> dict[str, Any]:
    result = measure_shear_wave(_with_shear_settings(config, mode_index=mode_index, direction=direction))
    return result["direction_results"][direction]


def _thermal_result(config: dict[str, Any], *, mode_index: int) -> dict[str, Any]:
    result = measure_thermal_diffusion(_with_thermal_settings(config, mode_index=mode_index))
    return result["direction_results"]["x"]


def _finite_max(values: list[float]) -> float:
    finite = [abs(float(item)) for item in values if np.isfinite(item)]
    return float(max(finite)) if finite else np.nan


def run_high_order_closure_diagnostic(
    base_config: dict[str, Any],
    *,
    tau_values: tuple[float, ...] = DEFAULT_HIGH_ORDER_TAU_VALUES,
) -> dict[str, Any]:
    """Run D2Q21 fourth-order closure measurements for selected ghost tau values."""

    rows: list[dict[str, Any]] = []
    for tau in tau_values:
        config = _collision_config(base_config, tau)
        shear_x_m1 = _shear_result(config, mode_index=1, direction="x")
        shear_x_m2 = _shear_result(config, mode_index=2, direction="x")
        shear_diag_m1 = _shear_result(config, mode_index=1, direction="diagonal")
        shear_diag_m2 = _shear_result(config, mode_index=2, direction="diagonal")
        thermal_m1 = _thermal_result(config, mode_index=1)
        thermal_m2 = _thermal_result(config, mode_index=2)
        metrics = [
            shear_x_m1["relative_error"],
            shear_x_m2["relative_error"],
            shear_diag_m1["relative_error"],
            shear_diag_m2["relative_error"],
            thermal_m1["relative_error"],
            thermal_m1["heat_flux_relative_error"],
            thermal_m2["relative_error"],
            thermal_m2["heat_flux_relative_error"],
        ]
        max_metric = _finite_max(metrics)
        rows.append(
            {
                "central_moment_closure": "fourth_order",
                "high_order_relaxation": float(tau),
                "status": "PASSED" if np.isfinite(max_metric) and max_metric <= DEFAULT_TOLERANCE else "FAILED",
                "max_metric": max_metric,
                "shear_x_mode1_error": shear_x_m1["relative_error"],
                "shear_x_mode2_error": shear_x_m2["relative_error"],
                "shear_diagonal_mode1_error": shear_diag_m1["relative_error"],
                "shear_diagonal_mode2_error": shear_diag_m2["relative_error"],
                "thermal_mode1_alpha_error": thermal_m1["relative_error"],
                "thermal_mode1_heat_flux_error": thermal_m1["heat_flux_relative_error"],
                "thermal_mode2_alpha_error": thermal_m2["relative_error"],
                "thermal_mode2_heat_flux_error": thermal_m2["heat_flux_relative_error"],
            }
        )
    best = min(rows, key=lambda item: item["max_metric"] if np.isfinite(item["max_metric"]) else np.inf)
    return {
        "scope": "D2Q21 fourth-order central-moment closure diagnostic; not a production pass",
        "tolerance": DEFAULT_TOLERANCE,
        "rows": rows,
        "joint_pass_exists": any(row["status"] == "PASSED" for row in rows),
        "best_high_order_relaxation": best["high_order_relaxation"],
        "best_max_metric": best["max_metric"],
    }
