"""Scalar-closure sensitivity probes for Phase 2 high-mode transport."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import numpy as np

from verification.shear_wave_measurement import measure_shear_wave
from verification.thermal_diffusion_measurement import measure_thermal_diffusion


DEFAULT_SHEAR_XY_FACTORS = (0.85, 0.90, 0.965, 1.02)
DEFAULT_SHEAR_NORMAL_FACTORS = (0.70, 0.78, 0.845, 0.92)
DEFAULT_HEAT_FLUX_FACTORS = (-0.70, -0.55, -0.4649237356175009, -0.35, -0.20)
DEFAULT_TOLERANCE = 0.05


def metric_passes(*values: float, tolerance: float = DEFAULT_TOLERANCE) -> bool:
    """Return whether every finite metric is within the acceptance tolerance."""

    return all(np.isfinite(value) and abs(float(value)) <= tolerance for value in values)


def _with_collision_updates(config: dict[str, Any], updates: dict[str, float]) -> dict[str, Any]:
    updated = deepcopy(config)
    collision = dict(updated.get("collision", {}) or {})
    collision.update(updates)
    updated["collision"] = collision
    return updated


def _with_shear_settings(
    config: dict[str, Any],
    *,
    mode_index: int,
    direction: str,
    steps: int,
) -> dict[str, Any]:
    updated = deepcopy(config)
    updated["p2_04_shear_wave"] = {
        "nx": 64,
        "ny": 64,
        "steps": steps,
        "sample_interval": 1,
        "mode_index": mode_index,
        "amplitude": 1.0e-5,
        "fit_start": 10,
        "directions": [direction],
        "relative_tolerance": DEFAULT_TOLERANCE,
        "direction_tolerance": DEFAULT_TOLERANCE,
    }
    return updated


def _with_thermal_settings(
    config: dict[str, Any],
    *,
    mode_index: int,
    direction: str,
    steps: int,
) -> dict[str, Any]:
    updated = deepcopy(config)
    updated["p2_05_thermal_diffusion"] = {
        "nx": 64,
        "ny": 64,
        "steps": steps,
        "sample_interval": 1,
        "mode_index": mode_index,
        "amplitude": 1.0e-5,
        "fit_start": 10,
        "directions": [direction],
        "relative_tolerance": DEFAULT_TOLERANCE,
        "heat_flux_tolerance": DEFAULT_TOLERANCE,
    }
    return updated


def _shear_direction_result(config: dict[str, Any], *, mode_index: int, direction: str) -> dict[str, Any]:
    steps = 120 if mode_index == 2 else 120
    result = measure_shear_wave(_with_shear_settings(config, mode_index=mode_index, direction=direction, steps=steps))
    return result["direction_results"][direction]


def _thermal_direction_result(config: dict[str, Any], *, mode_index: int, direction: str) -> dict[str, Any]:
    steps = 160 if mode_index == 2 else 320
    result = measure_thermal_diffusion(
        _with_thermal_settings(config, mode_index=mode_index, direction=direction, steps=steps)
    )
    return result["direction_results"][direction]


def _row_status(*metric_values: float, tolerance: float = DEFAULT_TOLERANCE) -> str:
    return "PASSED" if metric_passes(*metric_values, tolerance=tolerance) else "FAILED"


def scan_shear_factor(
    base_config: dict[str, Any],
    *,
    parameter: str,
    values: tuple[float, ...],
    direction: str,
) -> list[dict[str, Any]]:
    """Scan one shear scalar against low-mode and high-mode measurements."""

    rows: list[dict[str, Any]] = []
    for value in values:
        config = _with_collision_updates(base_config, {parameter: value})
        low = _shear_direction_result(config, mode_index=1, direction=direction)
        high = _shear_direction_result(config, mode_index=2, direction=direction)
        row = {
            "parameter": parameter,
            "value": float(value),
            "direction": direction,
            "mode1_nu_measured_lu": low["nu_measured_lu"],
            "mode1_relative_error": low["relative_error"],
            "mode2_nu_measured_lu": high["nu_measured_lu"],
            "mode2_relative_error": high["relative_error"],
            "joint_status": _row_status(low["relative_error"], high["relative_error"]),
        }
        rows.append(row)
    return rows


def scan_heat_flux_factor(
    base_config: dict[str, Any],
    *,
    values: tuple[float, ...],
    direction: str = "x",
) -> list[dict[str, Any]]:
    """Scan heat-flux retention against low/high thermal diffusion and Fourier-law."""

    rows: list[dict[str, Any]] = []
    for value in values:
        config = _with_collision_updates(base_config, {"regularized_heat_flux_factor": value})
        low = _thermal_direction_result(config, mode_index=1, direction=direction)
        high = _thermal_direction_result(config, mode_index=2, direction=direction)
        row = {
            "parameter": "regularized_heat_flux_factor",
            "value": float(value),
            "direction": direction,
            "mode1_alpha_measured_lu": low["alpha_measured_lu"],
            "mode1_alpha_relative_error": low["relative_error"],
            "mode1_heat_flux_ratio_real": low["heat_flux_ratio_real"],
            "mode1_heat_flux_relative_error": low["heat_flux_relative_error"],
            "mode2_alpha_measured_lu": high["alpha_measured_lu"],
            "mode2_alpha_relative_error": high["relative_error"],
            "mode2_heat_flux_ratio_real": high["heat_flux_ratio_real"],
            "mode2_heat_flux_relative_error": high["heat_flux_relative_error"],
            "joint_status": _row_status(
                low["relative_error"],
                low["heat_flux_relative_error"],
                high["relative_error"],
                high["heat_flux_relative_error"],
            ),
        }
        rows.append(row)
    return rows


def summarize_rows(rows: list[dict[str, Any]], metric_names: tuple[str, ...]) -> dict[str, Any]:
    """Summarize whether a scalar scan found a joint low/high pass."""

    best: dict[str, Any] | None = None
    best_score = np.inf
    for row in rows:
        metrics = [abs(float(row[name])) for name in metric_names if np.isfinite(row[name])]
        score = max(metrics) if metrics else np.inf
        if score < best_score:
            best = row
            best_score = score
    return {
        "joint_pass_exists": any(row["joint_status"] == "PASSED" for row in rows),
        "best_value": None if best is None else best["value"],
        "best_max_metric": None if not np.isfinite(best_score) else float(best_score),
    }


def run_high_mode_sensitivity(base_config: dict[str, Any]) -> dict[str, Any]:
    """Run the Phase 2 scalar sensitivity diagnostic matrix."""

    shear_xy_rows = scan_shear_factor(
        base_config,
        parameter="regularized_shear_xy_factor",
        values=DEFAULT_SHEAR_XY_FACTORS,
        direction="x",
    )
    shear_normal_rows = scan_shear_factor(
        base_config,
        parameter="regularized_shear_normal_factor",
        values=DEFAULT_SHEAR_NORMAL_FACTORS,
        direction="diagonal",
    )
    heat_rows = scan_heat_flux_factor(
        base_config,
        values=DEFAULT_HEAT_FLUX_FACTORS,
        direction="x",
    )
    return {
        "scope": (
            "D2Q21 physical-timestep scalar sensitivity for mode=1/mode=2; "
            "diagnostic only, not a production pass"
        ),
        "tolerance": DEFAULT_TOLERANCE,
        "scan_groups": {
            "regularized_shear_xy_factor": {
                "rows": shear_xy_rows,
                "summary": summarize_rows(
                    shear_xy_rows,
                    ("mode1_relative_error", "mode2_relative_error"),
                ),
            },
            "regularized_shear_normal_factor": {
                "rows": shear_normal_rows,
                "summary": summarize_rows(
                    shear_normal_rows,
                    ("mode1_relative_error", "mode2_relative_error"),
                ),
            },
            "regularized_heat_flux_factor": {
                "rows": heat_rows,
                "summary": summarize_rows(
                    heat_rows,
                    (
                        "mode1_alpha_relative_error",
                        "mode1_heat_flux_relative_error",
                        "mode2_alpha_relative_error",
                        "mode2_heat_flux_relative_error",
                    ),
                ),
            },
        },
    }
