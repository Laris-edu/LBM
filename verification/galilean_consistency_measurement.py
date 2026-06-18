"""Real Galilean-consistency measurements for Phase 2 P2-9."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

import numpy as np

from core.unit_mapping import create_unit_mapping
from verification.acoustic_wave_measurement import measure_acoustic_wave
from verification.shear_wave_measurement import measure_shear_wave
from verification.thermal_diffusion_measurement import measure_thermal_diffusion


DEFAULT_MACH_NUMBERS = (0.0, 0.02, 0.05)
DEFAULT_BACKGROUND_DIRECTIONS = ("x", "diagonal")
DEFAULT_DRIFT_TOLERANCE = 0.02
DEFAULT_SOUND_SPEED_TOLERANCE = 0.02
DEFAULT_GAMMA_TOLERANCE = 0.02
DEFAULT_DIRECTION_TOLERANCE = 0.02
DEFAULT_DISPERSION_DELTA_TOLERANCE = 0.005


@dataclass(frozen=True)
class GalileanConsistencySettings:
    mach_numbers: tuple[float, ...] = DEFAULT_MACH_NUMBERS
    background_directions: tuple[str, ...] = DEFAULT_BACKGROUND_DIRECTIONS
    drift_tolerance: float = DEFAULT_DRIFT_TOLERANCE
    sound_speed_tolerance: float = DEFAULT_SOUND_SPEED_TOLERANCE
    gamma_tolerance: float = DEFAULT_GAMMA_TOLERANCE
    direction_tolerance: float = DEFAULT_DIRECTION_TOLERANCE
    dispersion_delta_tolerance: float = DEFAULT_DISPERSION_DELTA_TOLERANCE
    run_dispersion_masking_check: bool = True
    run_high_mode_acoustic_diagnostic: bool = True
    shear_wave: dict[str, Any] | None = None
    thermal_diffusion: dict[str, Any] | None = None
    acoustic_wave: dict[str, Any] | None = None
    high_mode_acoustic: dict[str, Any] | None = None


def _sequence(value: Any, default: tuple[Any, ...]) -> tuple[Any, ...]:
    if value is None:
        return default
    if isinstance(value, str):
        return (value,)
    items = tuple(value)
    return items or default


def _settings_from_config(config: dict[str, Any]) -> GalileanConsistencySettings:
    p2 = dict(config.get("p2_09_galilean_consistency", {}) or {})
    return GalileanConsistencySettings(
        mach_numbers=tuple(float(item) for item in _sequence(p2.get("mach_numbers"), DEFAULT_MACH_NUMBERS)),
        background_directions=tuple(
            str(item) for item in _sequence(p2.get("background_directions"), DEFAULT_BACKGROUND_DIRECTIONS)
        ),
        drift_tolerance=float(p2.get("drift_tolerance", DEFAULT_DRIFT_TOLERANCE)),
        sound_speed_tolerance=float(p2.get("sound_speed_tolerance", DEFAULT_SOUND_SPEED_TOLERANCE)),
        gamma_tolerance=float(p2.get("gamma_tolerance", DEFAULT_GAMMA_TOLERANCE)),
        direction_tolerance=float(p2.get("direction_tolerance", DEFAULT_DIRECTION_TOLERANCE)),
        dispersion_delta_tolerance=float(
            p2.get("dispersion_delta_tolerance", DEFAULT_DISPERSION_DELTA_TOLERANCE)
        ),
        run_dispersion_masking_check=bool(p2.get("run_dispersion_masking_check", True)),
        run_high_mode_acoustic_diagnostic=bool(p2.get("run_high_mode_acoustic_diagnostic", True)),
        shear_wave=deepcopy(p2.get("shear_wave")),
        thermal_diffusion=deepcopy(p2.get("thermal_diffusion")),
        acoustic_wave=deepcopy(p2.get("acoustic_wave")),
        high_mode_acoustic=deepcopy(p2.get("high_mode_acoustic")),
    )


def _default_shear_settings() -> dict[str, Any]:
    return {
        "nx": 64,
        "ny": 64,
        "steps": 120,
        "sample_interval": 1,
        "mode_index": 1,
        "amplitude": 1.0e-5,
        "fit_start": 10,
        "directions": ["x", "y", "diagonal"],
        "relative_tolerance": 0.05,
        "direction_tolerance": 0.05,
    }


def _default_thermal_settings() -> dict[str, Any]:
    return {
        "nx": 64,
        "ny": 64,
        "steps": 320,
        "sample_interval": 1,
        "mode_index": 1,
        "amplitude": 1.0e-5,
        "fit_start": 10,
        "directions": ["x", "y"],
        "relative_tolerance": 0.05,
        "heat_flux_tolerance": 0.05,
    }


def _default_acoustic_settings() -> dict[str, Any]:
    return {
        "nx": 64,
        "ny": 64,
        "steps": 80,
        "sample_interval": 1,
        "mode_index": 1,
        "amplitude": 1.0e-6,
        "fit_start": 10,
        "directions": ["x", "y"],
        "sound_speed_tolerance": DEFAULT_SOUND_SPEED_TOLERANCE,
        "gamma_tolerance": DEFAULT_GAMMA_TOLERANCE,
        "direction_tolerance": DEFAULT_DIRECTION_TOLERANCE,
    }


def _merge_settings(defaults: dict[str, Any], overrides: dict[str, Any] | None) -> dict[str, Any]:
    merged = deepcopy(defaults)
    if overrides:
        merged.update(deepcopy(overrides))
    return merged


def _unit_vector(direction: str) -> np.ndarray:
    if direction == "x":
        return np.array([1.0, 0.0])
    if direction == "y":
        return np.array([0.0, 1.0])
    if direction == "diagonal":
        return np.array([1.0, 1.0]) / np.sqrt(2.0)
    raise ValueError("background direction must be x, y, or diagonal")


def _background_velocity(c_s_lu: float, mach: float, direction: str) -> list[float]:
    if mach == 0.0:
        return [0.0, 0.0]
    return [float(item) for item in mach * c_s_lu * _unit_vector(direction)]


def _scenario_name(mach: float, direction: str | None = None) -> str:
    label = f"mach_{mach:.3g}".replace(".", "p").replace("-", "m")
    return label if direction is None else f"{label}_{direction}"


def _scenario_config(
    base_config: dict[str, Any],
    *,
    settings: GalileanConsistencySettings,
    background_velocity_lu: list[float],
    acoustic_overrides: dict[str, Any] | None = None,
    dispersion_correction_enabled: bool | None = None,
) -> dict[str, Any]:
    config = deepcopy(base_config)
    shear = _merge_settings(_default_shear_settings(), settings.shear_wave)
    thermal = _merge_settings(_default_thermal_settings(), settings.thermal_diffusion)
    acoustic = _merge_settings(_default_acoustic_settings(), settings.acoustic_wave)
    if acoustic_overrides:
        acoustic.update(deepcopy(acoustic_overrides))

    shear["background_velocity_lu"] = list(background_velocity_lu)
    thermal["background_velocity_lu"] = list(background_velocity_lu)
    acoustic["background_velocity_lu"] = list(background_velocity_lu)
    acoustic["sound_speed_tolerance"] = settings.sound_speed_tolerance
    acoustic["gamma_tolerance"] = settings.gamma_tolerance
    acoustic["direction_tolerance"] = settings.direction_tolerance

    config["p2_04_shear_wave"] = shear
    config["p2_05_thermal_diffusion"] = thermal
    config["p2_06_acoustic_wave"] = acoustic
    if dispersion_correction_enabled is not None:
        collision = dict(config.get("collision", {}) or {})
        collision["dispersion_correction_enabled"] = bool(dispersion_correction_enabled)
        config["collision"] = collision
    return config


def _disable_high_mode_dispersion_targets(config: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(config)
    collision = dict(updated.get("collision", {}) or {})
    collision["dispersion_correction_enabled"] = True
    collision["regularized_shear_xy_dispersion_target"] = 1.0
    collision["regularized_shear_normal_dispersion_target"] = 1.0
    collision["regularized_heat_flux_dispersion_target"] = 1.0
    collision["conductive_heat_flux_dispersion_target"] = 1.0
    updated["collision"] = collision
    return updated


def _finite_max(values: list[float]) -> float:
    finite = [float(item) for item in values if np.isfinite(item)]
    return float(max(finite)) if finite else np.nan


def _directional_drift(
    background: dict[str, Any],
    reference: dict[str, Any],
    *,
    result_key: str,
    value_key: str,
) -> float:
    bg_results = background.get(result_key, {})
    ref_results = reference.get(result_key, {})
    drifts: list[float] = []
    for direction, bg_item in bg_results.items():
        ref_item = ref_results.get(direction)
        if not ref_item:
            continue
        bg_value = bg_item.get(value_key, np.nan)
        ref_value = ref_item.get(value_key, np.nan)
        if np.isfinite(bg_value) and np.isfinite(ref_value) and ref_value != 0.0:
            drifts.append(abs(float(bg_value) / float(ref_value) - 1.0))
    return _finite_max(drifts)


def _component_invalid(*results: dict[str, Any]) -> tuple[int | None, bool, bool]:
    invalid_steps = [item.get("first_invalid_step") for item in results if item.get("first_invalid_step") is not None]
    nan_detected = any(bool(item.get("nan_detected", False)) for item in results)
    clipping_used = any(bool(item.get("clipping_used", False)) for item in results)
    return (min(invalid_steps) if invalid_steps else None, nan_detected, clipping_used)


def _run_triplet(config: dict[str, Any]) -> dict[str, Any]:
    shear = measure_shear_wave(config)
    thermal = measure_thermal_diffusion(config)
    acoustic = measure_acoustic_wave(config)
    first_invalid_step, nan_detected, clipping_used = _component_invalid(shear, thermal, acoustic)
    return {
        "shear": shear,
        "thermal": thermal,
        "acoustic": acoustic,
        "first_invalid_step": first_invalid_step,
        "nan_detected": nan_detected,
        "clipping_used": clipping_used,
    }


def _scenario_summary(
    *,
    name: str,
    mach: float,
    direction: str | None,
    background_velocity_lu: list[float],
    result: dict[str, Any],
    reference: dict[str, Any],
    settings: GalileanConsistencySettings,
) -> dict[str, Any]:
    shear = result["shear"]
    thermal = result["thermal"]
    acoustic = result["acoustic"]
    nu_drift = _directional_drift(
        shear,
        reference["shear"],
        result_key="direction_results",
        value_key="nu_measured_lu",
    )
    alpha_drift = _directional_drift(
        thermal,
        reference["thermal"],
        result_key="direction_results",
        value_key="alpha_measured_lu",
    )
    sound_speed_drift = _directional_drift(
        acoustic,
        reference["acoustic"],
        result_key="direction_results",
        value_key="sound_speed_measured_lu",
    )
    direction_difference = _finite_max(
        [
            shear.get("direction_difference", np.nan),
            thermal.get("direction_difference", np.nan),
            acoustic.get("direction_difference", np.nan),
        ]
    )
    passed = (
        shear["p2_04_status"] == "PASSED"
        and thermal["p2_05_status"] == "PASSED"
        and acoustic["p2_06_status"] == "PASSED"
        and np.isfinite(nu_drift)
        and nu_drift <= settings.drift_tolerance
        and np.isfinite(alpha_drift)
        and alpha_drift <= settings.drift_tolerance
        and np.isfinite(acoustic["sound_speed_relative_error"])
        and acoustic["sound_speed_relative_error"] <= settings.sound_speed_tolerance
        and np.isfinite(acoustic["direction_difference"])
        and acoustic["direction_difference"] <= settings.direction_tolerance
        and result["first_invalid_step"] is None
        and not result["nan_detected"]
        and not result["clipping_used"]
    )
    return {
        "name": name,
        "mach": float(mach),
        "background_direction": direction if direction is not None else "reference",
        "background_velocity_lu": list(background_velocity_lu),
        "status": "PASSED" if passed else "FAILED",
        "p2_04_status": shear["p2_04_status"],
        "nu_relative_error": shear["relative_error"],
        "nu_drift_from_mach0": float(nu_drift) if np.isfinite(nu_drift) else np.nan,
        "p2_05_status": thermal["p2_05_status"],
        "alpha_relative_error": thermal["relative_error"],
        "alpha_drift_from_mach0": float(alpha_drift) if np.isfinite(alpha_drift) else np.nan,
        "heat_flux_relative_error": thermal["heat_flux_relative_error"],
        "heat_flux_sign_passed": thermal["heat_flux_sign_passed"],
        "p2_06_status": acoustic["p2_06_status"],
        "sound_speed_relative_error": acoustic["sound_speed_relative_error"],
        "sound_speed_drift_from_mach0": (
            float(sound_speed_drift) if np.isfinite(sound_speed_drift) else np.nan
        ),
        "gamma_relative_error": acoustic["gamma_relative_error"],
        "direction_difference": float(direction_difference) if np.isfinite(direction_difference) else np.nan,
        "first_invalid_step": result["first_invalid_step"],
        "nan_detected": result["nan_detected"],
        "clipping_used": result["clipping_used"],
        "shear": shear,
        "thermal": thermal,
        "acoustic": acoustic,
    }


def _max_mach(settings: GalileanConsistencySettings) -> float:
    finite = [abs(float(item)) for item in settings.mach_numbers if np.isfinite(item)]
    return max(finite) if finite else 0.0


def _dispersion_masking_check(
    base_config: dict[str, Any],
    *,
    settings: GalileanConsistencySettings,
    c_s_lu: float,
) -> dict[str, Any]:
    mapping = create_unit_mapping(base_config)
    if mapping.lattice.velocity_set != "D2Q37" or not mapping.collision.dispersion_correction_enabled:
        return {
            "status": "NOT_APPLICABLE",
            "reason": "requires D2Q37 with dispersion_correction_enabled=true",
        }

    mach = _max_mach(settings)
    directions = list(settings.background_directions)
    low_mode_checks = []
    for direction in directions:
        background_velocity = _background_velocity(c_s_lu, mach, direction)
        enabled_config = _scenario_config(
            base_config,
            settings=settings,
            background_velocity_lu=background_velocity,
            dispersion_correction_enabled=True,
        )
        disabled_config = _scenario_config(
            base_config,
            settings=settings,
            background_velocity_lu=background_velocity,
            dispersion_correction_enabled=True,
        )
        disabled_config = _disable_high_mode_dispersion_targets(disabled_config)
        enabled = measure_acoustic_wave(enabled_config)
        disabled = measure_acoustic_wave(disabled_config)
        speed_delta = _directional_drift(
            enabled,
            disabled,
            result_key="direction_results",
            value_key="sound_speed_measured_lu",
        )
        low_mode_checks.append(
            {
                "background_direction": direction,
                "mach": mach,
                "background_velocity_lu": background_velocity,
                "status": "PASSED"
                if (
                    enabled["p2_06_status"] == "PASSED"
                    and disabled["p2_06_status"] == "PASSED"
                    and np.isfinite(speed_delta)
                    and speed_delta <= settings.dispersion_delta_tolerance
                )
                else "FAILED",
                "sound_speed_delta_enabled_vs_disabled": (
                    float(speed_delta) if np.isfinite(speed_delta) else np.nan
                ),
                "enabled_sound_speed_relative_error": enabled["sound_speed_relative_error"],
                "disabled_sound_speed_relative_error": disabled["sound_speed_relative_error"],
                "enabled_gamma_relative_error": enabled["gamma_relative_error"],
                "disabled_gamma_relative_error": disabled["gamma_relative_error"],
                "enabled_status": enabled["p2_06_status"],
                "disabled_status": disabled["p2_06_status"],
                "enabled": enabled,
                "disabled": disabled,
            }
        )

    high_mode = {"status": "NOT_RUN", "hard_gate_role": "diagnostic_only_not_transport_masking"}
    if settings.run_high_mode_acoustic_diagnostic:
        direction = directions[0] if directions else "x"
        background_velocity = _background_velocity(c_s_lu, mach, direction)
        high_mode_overrides = _merge_settings(
            {"mode_index": 2, "steps": 80, "directions": ["x", "y"]},
            settings.high_mode_acoustic,
        )
        enabled_config = _scenario_config(
            base_config,
            settings=settings,
            background_velocity_lu=background_velocity,
            acoustic_overrides=high_mode_overrides,
            dispersion_correction_enabled=True,
        )
        disabled_config = _scenario_config(
            base_config,
            settings=settings,
            background_velocity_lu=background_velocity,
            acoustic_overrides=high_mode_overrides,
            dispersion_correction_enabled=True,
        )
        disabled_config = _disable_high_mode_dispersion_targets(disabled_config)
        enabled = measure_acoustic_wave(enabled_config)
        disabled = measure_acoustic_wave(disabled_config)
        legacy_masking_detected = enabled["p2_06_status"] == "PASSED" and disabled["p2_06_status"] != "PASSED"
        acoustic_branch_passed = enabled["p2_06_status"] == "PASSED"
        high_mode = {
            "status": "PASSED" if acoustic_branch_passed else "FAILED",
            "interpretation": (
                "ACOUSTIC_EIGENBRANCH_DIAGNOSTIC_PASS"
                if acoustic_branch_passed
                else "ACOUSTIC_EIGENBRANCH_CLOSURE_REQUIRED_OR_OUT_OF_SCOPE"
            ),
            "legacy_masking_interpretation": (
                "MASKING_DETECTED" if legacy_masking_detected else "NO_MASKING_DETECTED"
            ),
            "hard_gate_role": "diagnostic_only_not_transport_masking",
            "background_direction": direction,
            "mach": mach,
            "background_velocity_lu": background_velocity,
            "enabled_status": enabled["p2_06_status"],
            "disabled_status": disabled["p2_06_status"],
            "enabled_sound_speed_relative_error": enabled["sound_speed_relative_error"],
            "disabled_sound_speed_relative_error": disabled["sound_speed_relative_error"],
            "enabled_gamma_relative_error": enabled["gamma_relative_error"],
            "disabled_gamma_relative_error": disabled["gamma_relative_error"],
            "enabled": enabled,
            "disabled": disabled,
        }

    transport_passed = all(item["status"] == "PASSED" for item in low_mode_checks)
    return {
        "status": "PASSED" if transport_passed else "FAILED",
        "transport_masking_status": "PASSED" if transport_passed else "FAILED",
        "low_mode_checks": low_mode_checks,
        "high_mode_acoustic_diagnostic": high_mode,
        "high_mode_acoustic_eigenbranch_diagnostic": high_mode,
        "acceptance": {
            "low_mode_enabled_disabled_sound_speed_delta_max": settings.dispersion_delta_tolerance,
            "transport_masking_uses_low_mode_enabled_disabled_delta_only": True,
            "high_mode_acoustic_is_eigenbranch_diagnostic_only": True,
        },
    }


def measure_galilean_consistency(config: dict[str, Any]) -> dict[str, Any]:
    """Run P2-9 background-velocity transport and acoustic measurements."""

    settings = _settings_from_config(config)
    mapping = create_unit_mapping(config)
    c_s_lu = float(np.sqrt(mapping.physical.gamma * mapping.theta_ref_lu))

    reference_config = _scenario_config(
        config,
        settings=settings,
        background_velocity_lu=[0.0, 0.0],
    )
    reference = _run_triplet(reference_config)
    scenarios: list[dict[str, Any]] = []
    for mach in settings.mach_numbers:
        if mach == 0.0:
            continue
        for direction in settings.background_directions:
            background_velocity = _background_velocity(c_s_lu, mach, direction)
            scenario_config = _scenario_config(
                config,
                settings=settings,
                background_velocity_lu=background_velocity,
            )
            result = _run_triplet(scenario_config)
            scenarios.append(
                _scenario_summary(
                    name=_scenario_name(mach, direction),
                    mach=mach,
                    direction=direction,
                    background_velocity_lu=background_velocity,
                    result=result,
                    reference=reference,
                    settings=settings,
                )
            )

    dispersion_check = (
        _dispersion_masking_check(config, settings=settings, c_s_lu=c_s_lu)
        if settings.run_dispersion_masking_check
        else {"status": "NOT_RUN"}
    )
    first_invalid_steps = [
        reference["first_invalid_step"],
        *[
            item["first_invalid_step"] for item in scenarios if item["first_invalid_step"] is not None
        ],
    ]
    first_invalid_steps = [item for item in first_invalid_steps if item is not None]
    max_nu_drift = _finite_max([item["nu_drift_from_mach0"] for item in scenarios])
    max_alpha_drift = _finite_max([item["alpha_drift_from_mach0"] for item in scenarios])
    max_sound_speed_error = _finite_max([item["sound_speed_relative_error"] for item in scenarios])
    max_sound_speed_drift = _finite_max([item["sound_speed_drift_from_mach0"] for item in scenarios])
    max_direction_difference = _finite_max([item["direction_difference"] for item in scenarios])
    reference_pass = (
        reference["shear"]["p2_04_status"] == "PASSED"
        and reference["thermal"]["p2_05_status"] == "PASSED"
        and reference["acoustic"]["p2_06_status"] == "PASSED"
        and reference["first_invalid_step"] is None
        and not reference["nan_detected"]
        and not reference["clipping_used"]
    )
    all_scenarios_pass = bool(scenarios) and all(item["status"] == "PASSED" for item in scenarios)
    dispersion_pass = dispersion_check["status"] in {"PASSED", "NOT_APPLICABLE", "NOT_RUN"}
    passed = reference_pass and all_scenarios_pass and dispersion_pass

    return {
        "p2_09_status": "PASSED" if passed else "FAILED",
        "velocity_set": mapping.lattice.velocity_set,
        "c_s_lu": c_s_lu,
        "mach_numbers": [float(item) for item in settings.mach_numbers],
        "background_directions": list(settings.background_directions),
        "scenario_count": len(scenarios),
        "reference": {
            "name": _scenario_name(0.0),
            "mach": 0.0,
            "background_velocity_lu": [0.0, 0.0],
            "p2_04_status": reference["shear"]["p2_04_status"],
            "p2_05_status": reference["thermal"]["p2_05_status"],
            "p2_06_status": reference["acoustic"]["p2_06_status"],
            "status": "PASSED" if reference_pass else "FAILED",
            "first_invalid_step": reference["first_invalid_step"],
            "nan_detected": reference["nan_detected"],
            "clipping_used": reference["clipping_used"],
            "shear": reference["shear"],
            "thermal": reference["thermal"],
            "acoustic": reference["acoustic"],
        },
        "scenarios": scenarios,
        "max_nu_drift_from_mach0": float(max_nu_drift) if np.isfinite(max_nu_drift) else np.nan,
        "max_alpha_drift_from_mach0": float(max_alpha_drift) if np.isfinite(max_alpha_drift) else np.nan,
        "max_sound_speed_relative_error": (
            float(max_sound_speed_error) if np.isfinite(max_sound_speed_error) else np.nan
        ),
        "max_sound_speed_drift_from_mach0": (
            float(max_sound_speed_drift) if np.isfinite(max_sound_speed_drift) else np.nan
        ),
        "max_direction_difference": (
            float(max_direction_difference) if np.isfinite(max_direction_difference) else np.nan
        ),
        "dispersion_masking_check": dispersion_check,
        "dispersion_masking_status": dispersion_check["status"],
        "transport_dispersion_masking_status": dispersion_check.get(
            "transport_masking_status",
            dispersion_check["status"],
        ),
        "acoustic_eigenbranch_diagnostic_status": dispersion_check.get(
            "high_mode_acoustic_eigenbranch_diagnostic",
            {},
        ).get("status", "NOT_RUN"),
        "first_invalid_step": min(first_invalid_steps) if first_invalid_steps else None,
        "nan_detected": reference["nan_detected"] or any(item["nan_detected"] for item in scenarios),
        "clipping_used": reference["clipping_used"] or any(item["clipping_used"] for item in scenarios),
        "acceptance": {
            "nu_drift_from_mach0_max": settings.drift_tolerance,
            "alpha_drift_from_mach0_max": settings.drift_tolerance,
            "sound_speed_relative_error_max": settings.sound_speed_tolerance,
            "sound_speed_drift_from_mach0_max": settings.drift_tolerance,
            "direction_difference_max": settings.direction_tolerance,
            "requires_no_nan": True,
            "requires_no_clipping": True,
            "requires_positive_theta": True,
        },
    }
