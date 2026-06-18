"""Diagnose D2Q37 high-mode acoustic eigen-branch extrapolation boundaries.

Usage:
    python -m scripts.diagnose_phase2_high_mode_acoustic_boundary
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
from typing import Any

import numpy as np
import yaml

from core.unit_mapping import create_unit_mapping
from scripts.run_m2_verification import load_config, sha256_file, summary_payload_digest
from verification.acoustic_wave_measurement import measure_acoustic_wave
from verification.galilean_consistency_measurement import measure_galilean_consistency


BASELINE_PR = 0.7061328707


@dataclass(frozen=True)
class BoundaryCase:
    name: str
    category: str
    n: int
    mode_index: int
    pr: float
    mach: float
    background_direction: str
    directions: tuple[str, ...]
    expected_scope: str


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


def _axis_laplacian(n: int, mode_index: int) -> float:
    k = 2.0 * np.pi * float(mode_index) / float(n)
    return float(4.0 * np.sin(0.5 * k) ** 2)


def _with_pr(config: dict[str, Any], pr: float) -> dict[str, Any]:
    updated = deepcopy(config)
    physical = dict(updated.get("physical", {}) or {})
    current_pr = float(physical.get("Pr", BASELINE_PR))
    if np.isclose(float(pr), current_pr, rtol=0.0, atol=1.0e-15):
        return updated
    nu0 = float(physical.get("nu0_m2_s", 1.57e-5))
    physical["nu0_m2_s"] = nu0
    physical["alpha0_m2_s"] = nu0 / float(pr)
    physical["Pr"] = float(pr)
    updated["physical"] = physical
    return updated


def _with_high_mode_factors(
    config: dict[str, Any],
    *,
    axis_factor: float,
    diagonal_factor: float,
) -> dict[str, Any]:
    updated = deepcopy(config)
    collision = dict(updated.get("collision", {}) or {})
    collision["acoustic_phase_correction_enabled"] = True
    collision["acoustic_phase_high_mode_factor"] = float(axis_factor)
    collision["acoustic_phase_high_mode_diagonal_factor"] = float(diagonal_factor)
    updated["collision"] = collision
    return updated


def _background_velocity(config: dict[str, Any], mach: float, direction: str) -> list[float]:
    if mach == 0.0 or direction == "none":
        return [0.0, 0.0]
    mapping = create_unit_mapping(config)
    c_s = float(np.sqrt(mapping.physical.gamma * mapping.theta_ref_lu))
    if direction == "x":
        unit = np.array([1.0, 0.0])
    elif direction == "y":
        unit = np.array([0.0, 1.0])
    elif direction == "diagonal":
        unit = np.array([1.0, 1.0]) / np.sqrt(2.0)
    else:
        raise ValueError("background direction must be none, x, y, or diagonal")
    return [float(item) for item in mach * c_s * unit]


def _case_config(
    base_config: dict[str, Any],
    case: BoundaryCase,
    *,
    axis_factor: float,
    diagonal_factor: float,
    steps: int,
    fit_start: int,
) -> dict[str, Any]:
    config = _with_pr(base_config, case.pr)
    config = _with_high_mode_factors(
        config,
        axis_factor=axis_factor,
        diagonal_factor=diagonal_factor,
    )
    numerics = dict(config.get("numerics", {}) or {})
    numerics["nx"] = case.n
    numerics["ny"] = case.n
    config["numerics"] = numerics
    config["p2_06_acoustic_wave"] = {
        "nx": case.n,
        "ny": case.n,
        "steps": steps,
        "sample_interval": 1,
        "mode_index": case.mode_index,
        "amplitude": 1.0e-6,
        "fit_start": fit_start,
        "directions": list(case.directions),
        "sound_speed_tolerance": 0.02,
        "gamma_tolerance": 0.02,
        "direction_tolerance": 0.02,
        "background_velocity_lu": _background_velocity(config, case.mach, case.background_direction),
    }
    case_meta = dict(config.get("case", {}) or {})
    case_meta["name"] = f"phase2_high_mode_acoustic_boundary_{case.name}"
    config["case"] = case_meta
    return config


def _boundary_cases(*, include_n128: bool, full_grid: bool) -> list[BoundaryCase]:
    cases = [
        BoundaryCase(
            "n32_mode1_equivalent_laplacian",
            "N/mode",
            32,
            1,
            BASELINE_PR,
            0.0,
            "none",
            ("x", "y", "diagonal"),
            "same_discrete_laplacian_as_64_mode2",
        ),
        BoundaryCase(
            "n64_mode2_seed",
            "N/mode",
            64,
            2,
            BASELINE_PR,
            0.0,
            "none",
            ("x", "y", "diagonal"),
            "calibrated_seed_scope",
        ),
        BoundaryCase(
            "n64_mode1_low_mode_control",
            "mode",
            64,
            1,
            BASELINE_PR,
            0.0,
            "none",
            ("x", "y", "diagonal"),
            "low_mode_control_not_high_mode_target",
        ),
        BoundaryCase(
            "n64_mode3_out_of_scope",
            "mode",
            64,
            3,
            BASELINE_PR,
            0.0,
            "none",
            ("x", "y", "diagonal"),
            "outside_targeted_high_mode_symbol",
        ),
    ]
    if include_n128:
        cases.append(
            BoundaryCase(
                "n128_mode4_equivalent_laplacian",
                "N/mode",
                128,
                4,
                BASELINE_PR,
                0.0,
                "none",
                ("x", "y", "diagonal"),
                "same_discrete_laplacian_as_64_mode2",
            )
        )
    pr_values = (0.5, 1.0, 2.0) if full_grid else (0.5, 2.0)
    for pr in pr_values:
        cases.append(
            BoundaryCase(
                f"n64_mode2_pr_{str(pr).replace('.', 'p')}",
                "Pr",
                64,
                2,
                pr,
                0.0,
                "none",
                ("x", "y", "diagonal"),
                "same_seed_different_tau32",
            )
        )
    mach_values = (0.02, 0.05) if full_grid else (0.05,)
    for mach in mach_values:
        for direction in ("x", "diagonal"):
            cases.append(
                BoundaryCase(
                    f"n64_mode2_mach_{str(mach).replace('.', 'p')}_{direction}",
                    "Mach/background",
                    64,
                    2,
                    BASELINE_PR,
                    mach,
                    direction,
                    ("x", "y", "diagonal"),
                    "background_velocity_boundary",
                )
            )
    return cases


def _case_row(case: BoundaryCase, result: dict[str, Any]) -> dict[str, Any]:
    attenuation_errors = [
        item.get("acoustic_attenuation_relative_error", np.nan)
        for item in result.get("direction_results", {}).values()
    ]
    return {
        "name": case.name,
        "category": case.category,
        "n": case.n,
        "mode_index": case.mode_index,
        "pr": case.pr,
        "mach": case.mach,
        "background_direction": case.background_direction,
        "directions": list(case.directions),
        "expected_scope": case.expected_scope,
        "axis_laplacian": _axis_laplacian(case.n, case.mode_index),
        "diagonal_laplacian": 2.0 * _axis_laplacian(case.n, case.mode_index),
        "status": result["p2_06_status"],
        "sound_speed_relative_error": result["sound_speed_relative_error"],
        "gamma_relative_error": result["gamma_relative_error"],
        "direction_difference": result["direction_difference"],
        "acoustic_attenuation_relative_error": (
            float(max(item for item in attenuation_errors if np.isfinite(item)))
            if any(np.isfinite(item) for item in attenuation_errors)
            else np.nan
        ),
        "first_invalid_step": result["first_invalid_step"],
        "nan_detected": result["nan_detected"],
        "clipping_used": result["clipping_used"],
        "raw": result,
    }


def _p2_9_semantic_smoke_config(base_config: dict[str, Any]) -> dict[str, Any]:
    config = _with_high_mode_factors(
        deepcopy(base_config),
        axis_factor=0.955,
        diagonal_factor=0.918,
    )
    config["p2_09_galilean_consistency"] = {
        "mach_numbers": [0.0, 0.02],
        "background_directions": ["x"],
        "run_dispersion_masking_check": True,
        "run_high_mode_acoustic_diagnostic": True,
        "shear_wave": {
            "nx": 16,
            "ny": 16,
            "steps": 8,
            "sample_interval": 1,
            "mode_index": 1,
            "amplitude": 1.0e-5,
            "fit_start": 2,
            "directions": ["x"],
        },
        "thermal_diffusion": {
            "nx": 16,
            "ny": 16,
            "steps": 8,
            "sample_interval": 1,
            "mode_index": 1,
            "amplitude": 1.0e-5,
            "fit_start": 2,
            "directions": ["x"],
        },
        "acoustic_wave": {
            "nx": 16,
            "ny": 16,
            "steps": 8,
            "sample_interval": 1,
            "mode_index": 1,
            "amplitude": 1.0e-6,
            "fit_start": 2,
            "directions": ["x"],
        },
        "high_mode_acoustic": {
            "nx": 16,
            "ny": 16,
            "steps": 8,
            "sample_interval": 1,
            "mode_index": 2,
            "amplitude": 1.0e-6,
            "fit_start": 2,
            "directions": ["x"],
        },
    }
    return config


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    rows = summary["cases"]
    lines = [
        "# D2Q37 High-Mode Acoustic Boundary Diagnostic",
        "",
        "本文档由 `python -m scripts.diagnose_phase2_high_mode_acoustic_boundary` 生成。",
        "该报告只复核 diagnostic high-mode acoustic eigen-branch seed 的外推边界；默认 baseline 不变，不声明 final M2 production pass。",
        "",
        "## 配置",
        "",
        f"- config: `{summary['config']}`",
        f"- config_sha256: `{summary['config_sha256']}`",
        f"- axis factor: `{summary['axis_factor']}`",
        f"- diagonal factor: `{summary['diagonal_factor']}`",
        f"- steps: `{summary['steps']}`",
        f"- fit_start: `{summary['fit_start']}`",
        "",
        "## 总结",
        "",
        f"- case_count: `{summary['case_count']}`",
        f"- passed_count: `{summary['passed_count']}`",
        f"- failed_count: `{summary['failed_count']}`",
        f"- max_speed_error: `{_format_value(summary['max_sound_speed_relative_error'])}`",
        f"- max_gamma_error: `{_format_value(summary['max_gamma_relative_error'])}`",
        f"- max_direction_difference: `{_format_value(summary['max_direction_difference'])}`",
        f"- max_attenuation_error: `{_format_value(summary['max_acoustic_attenuation_relative_error'])}`",
        "",
        "## 外推矩阵",
        "",
        "| case | category | N | mode | Pr | Mach | background | scope | status | speed err | gamma err | dir diff | atten err | first_invalid | NaN | clipping |",
        "|---|---|---:|---:|---:|---:|---|---|---|---:|---:|---:|---:|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            f"`{row['name']}` | "
            f"`{row['category']}` | "
            f"`{row['n']}` | "
            f"`{row['mode_index']}` | "
            f"`{_format_value(row['pr'])}` | "
            f"`{_format_value(row['mach'])}` | "
            f"`{row['background_direction']}` | "
            f"`{row['expected_scope']}` | "
            f"`{row['status']}` | "
            f"`{_format_value(row['sound_speed_relative_error'])}` | "
            f"`{_format_value(row['gamma_relative_error'])}` | "
            f"`{_format_value(row['direction_difference'])}` | "
            f"`{_format_value(row['acoustic_attenuation_relative_error'])}` | "
            f"`{_format_value(row['first_invalid_step'])}` | "
            f"`{_format_value(row['nan_detected'])}` | "
            f"`{_format_value(row['clipping_used'])}` |"
        )
    p2_9 = summary["p2_9_semantic_smoke"]
    lines.extend(
        [
            "",
            "## P2-9 语义拆分 Smoke",
            "",
            "该 smoke 使用短 `16x16/8-step` 配置，只验证输出字段和 hard/diagnostic 语义拆分；不作为 P2-9 物理通过性证据。",
            f"- p2_09_status: `{p2_9['p2_09_status']}`",
            f"- dispersion_masking_status: `{p2_9['dispersion_masking_status']}`",
            f"- transport_dispersion_masking_status: `{p2_9['transport_dispersion_masking_status']}`",
            f"- acoustic_eigenbranch_diagnostic_status: `{p2_9['acoustic_eigenbranch_diagnostic_status']}`",
            "",
            "解释：`transport_dispersion_masking_status` 是 P2-9 hard masking 语义；`acoustic_eigenbranch_diagnostic_status` 只记录 high-mode acoustic branch 诊断结果，不参与 transport masking hard gate。",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/gas_air_10k_d2q37_physical_timestep.yaml"))
    parser.add_argument("--out-root", type=Path, default=Path("results/phase2_high_mode_acoustic_boundary"))
    parser.add_argument("--axis-factor", type=float, default=0.955)
    parser.add_argument("--diagonal-factor", type=float, default=0.918)
    parser.add_argument("--steps", type=int, default=80)
    parser.add_argument("--fit-start", type=int, default=10)
    parser.add_argument("--include-n128", action="store_true")
    parser.add_argument("--full-grid", action="store_true")
    args = parser.parse_args(argv)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.out_root / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    base_config = load_config(args.config)
    cases: list[dict[str, Any]] = []
    for case in _boundary_cases(include_n128=args.include_n128, full_grid=args.full_grid):
        config = _case_config(
            base_config,
            case,
            axis_factor=args.axis_factor,
            diagonal_factor=args.diagonal_factor,
            steps=args.steps,
            fit_start=args.fit_start,
        )
        result = measure_acoustic_wave(config)
        cases.append(_case_row(case, result))

    finite_speed = [row["sound_speed_relative_error"] for row in cases if np.isfinite(row["sound_speed_relative_error"])]
    finite_gamma = [row["gamma_relative_error"] for row in cases if np.isfinite(row["gamma_relative_error"])]
    finite_direction = [row["direction_difference"] for row in cases if np.isfinite(row["direction_difference"])]
    finite_attenuation = [
        row["acoustic_attenuation_relative_error"]
        for row in cases
        if np.isfinite(row["acoustic_attenuation_relative_error"])
    ]

    p2_9_semantic_smoke = measure_galilean_consistency(_p2_9_semantic_smoke_config(base_config))

    summary = {
        "phase": "Phase_2",
        "diagnostic": "D2Q37 high-mode acoustic full-modal eigen-branch boundary",
        "run_id": timestamp,
        "timestamp": timestamp,
        "command": [sys.executable, "-m", "scripts.diagnose_phase2_high_mode_acoustic_boundary", *sys.argv[1:]],
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "yaml_version": yaml.__version__,
        "config": str(args.config),
        "config_sha256": sha256_file(args.config),
        "axis_factor": args.axis_factor,
        "diagonal_factor": args.diagonal_factor,
        "steps": args.steps,
        "fit_start": args.fit_start,
        "include_n128": bool(args.include_n128),
        "full_grid": bool(args.full_grid),
        "case_count": len(cases),
        "passed_count": sum(1 for row in cases if row["status"] == "PASSED"),
        "failed_count": sum(1 for row in cases if row["status"] != "PASSED"),
        "max_sound_speed_relative_error": max(finite_speed) if finite_speed else np.nan,
        "max_gamma_relative_error": max(finite_gamma) if finite_gamma else np.nan,
        "max_direction_difference": max(finite_direction) if finite_direction else np.nan,
        "max_acoustic_attenuation_relative_error": max(finite_attenuation) if finite_attenuation else np.nan,
        "cases": _json_safe(cases),
        "p2_9_semantic_smoke": _json_safe(p2_9_semantic_smoke),
    }
    summary["summary_json_sha256_policy"] = "sha256 of canonical summary payload before adding this digest field"
    summary["summary_json_sha256"] = summary_payload_digest(_json_safe(summary))

    summary_path = out_dir / "summary.json"
    report_path = out_dir / "High_Mode_Acoustic_Boundary_Report.md"
    summary_path.write_text(json.dumps(_json_safe(summary), indent=2, ensure_ascii=False), encoding="utf-8")
    _write_report(report_path, summary)
    print(f"Wrote {summary_path}")
    print(f"Wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
