"""Run the Phase 2 M2 verification suite.

Usage:
    python -m scripts.run_m2_verification --config configs/gas_air_10k_physical_timestep.yaml
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

import h5py
import numpy as np
import yaml

from core.solver import GasSolver2D
from verification.acoustic_wave_measurement import measure_acoustic_wave
from verification.galilean_consistency_measurement import measure_galilean_consistency
from verification.prandtl_scan_measurement import measure_prandtl_scan
from verification.shear_wave_measurement import measure_shear_wave
from verification.thermal_diffusion_measurement import measure_thermal_diffusion


P2_TESTS = [
    "verification/test_phase2_p2_00_unit_mapping.py",
    "verification/test_phase2_p2_01_lattice_d2q21.py",
    "verification/test_phase2_p2_02_equilibrium_macro.py",
    "verification/test_phase2_p2_03_collision_uniform.py",
    "verification/test_phase2_p2_04_streaming_shear.py",
    "verification/test_phase2_p2_05_thermal_heat_flux.py",
    "verification/test_phase2_p2_06_acoustic_gamma.py",
    "verification/test_phase2_p2_07_prandtl_scan.py",
    "verification/test_phase2_p2_08_rotational_isotropy.py",
    "verification/test_phase2_p2_09_galilean_consistency.py",
    "verification/test_phase2_postprocess_modal_fit.py",
    "verification/test_phase2_hdf5_metadata.py",
    "verification/test_phase2_d2q37_fallback.py",
]


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}
    include = config.get("include")
    if include:
        parent = load_config(path.parent / include)
        parent.update({k: v for k, v in config.items() if k != "include"})
        return parent
    return config


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def summary_payload_digest(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def status_layers(config_path: Path, config: dict, passed: bool) -> dict[str, str]:
    theta_policy = str(config.get("lattice", {}).get("theta_ref_policy", ""))
    velocity_set = str(config.get("lattice", {}).get("velocity_set", "D2Q21")).upper()
    is_diagnostic = "quadrature" in str(config_path).lower() or theta_policy == "quadrature_matched"
    if not passed:
        return {
            "automation_status": "FAILED",
            "contract_validation_status": "FAILED",
            "production_physics_status": "NOT_PASSED",
            "m2_decision": "NO-GO",
            "validation_level": "FAILED",
        }
    if is_diagnostic:
        return {
            "automation_status": "PASSED",
            "contract_validation_status": "DIAGNOSTIC_PASSED",
            "production_physics_status": "N/A",
            "m2_decision": "DIAGNOSTIC_ONLY",
            "validation_level": "CONTRACT",
        }
    if velocity_set == "D2Q37":
        return {
            "automation_status": "PASSED",
            "contract_validation_status": "D2Q37_DIAGNOSTIC_READY",
            "production_physics_status": "NOT_PASSED",
            "m2_decision": "GO-RISK / D2Q37_DYNAMIC_DIAGNOSTIC",
            "validation_level": "CONTRACT",
        }
    return {
        "automation_status": "PASSED",
        "contract_validation_status": "PASSED",
        "production_physics_status": "NOT_PASSED",
        "m2_decision": "GO-RISK / IN-PROGRESS",
        "validation_level": "CONTRACT",
    }


def _json_safe(value):
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and np.isnan(value):
        return None
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/gas_air_10k_physical_timestep.yaml")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out) if args.out else Path("results") / "m2" / timestamp
    raw_dir = out_dir / "raw"
    figures_dir = out_dir / "figures"
    raw_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    config = load_config(config_path)
    solver = GasSolver2D(config)
    solver.initialize_from_macro(1.0, [0.0, 0.0], solver.mapping.theta_ref_lu)
    h5_path = raw_dir / "uniform_state.h5"
    solver.save_hdf5(str(h5_path))

    command = [sys.executable, "-m", "pytest", "-q", *P2_TESTS]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    passed = result.returncode == 0
    p2_04 = measure_shear_wave(config)
    p2_05 = measure_thermal_diffusion(config)
    p2_06 = measure_acoustic_wave(config)
    p2_07 = measure_prandtl_scan(config)
    p2_09 = measure_galilean_consistency(config)
    layered_status = status_layers(config_path, config, passed)
    summary = {
        "phase": "Phase_2",
        "run_id": timestamp,
        "config": str(config_path),
        "config_sha256": sha256_file(config_path),
        "timestamp": timestamp,
        "command": command,
        "returncode": result.returncode,
        "status": layered_status["automation_status"],
        **layered_status,
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "h5py_version": h5py.__version__,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "raw_hdf5": str(h5_path),
        "p2_numbering": "P2-0 through P2-9 only; postprocess/HDF5 schema tests are support tests",
        "bulk_viscosity_policy": solver.mapping.collision.bulk_viscosity_policy,
        "velocity_set": solver.mapping.lattice.velocity_set,
        "Q": solver.mapping.lattice.Q,
        "theta_q_lu": solver.mapping.lattice.theta_q_lu,
        "central_moment_closure": solver.mapping.collision.central_moment_closure,
        "high_order_relaxation": solver.mapping.collision.high_order_relaxation,
        "trace_bulk_policy": solver.mapping.collision.trace_bulk_policy,
        "trace_bulk_scale": solver.mapping.collision.trace_bulk_scale,
        "trace_bulk_calibration_id": solver.mapping.collision.trace_bulk_calibration_id,
        "regularized_heat_flux_factor_policy": solver.mapping.collision.regularized_heat_flux_factor_policy,
        "regularized_heat_flux_factor": solver.mapping.collision.regularized_heat_flux_factor,
        "regularized_heat_flux_f_fraction": solver.mapping.collision.regularized_heat_flux_f_fraction,
        "heat_flux_retention_policy": solver.mapping.collision.heat_flux_retention_policy,
        "heat_flux_retention_curve_type": solver.mapping.collision.heat_flux_retention_curve_type,
        "heat_flux_retention_curve_coefficients": (
            solver.mapping.collision.heat_flux_retention_curve_coefficients
        ),
        "conductive_heat_flux_moment_factor_policy": (
            solver.mapping.collision.conductive_heat_flux_moment_factor_policy
        ),
        "conductive_heat_flux_moment_factor": solver.mapping.collision.conductive_heat_flux_moment_factor,
        "regularized_heat_flux_diagonal_low_mode_target": (
            solver.mapping.collision.regularized_heat_flux_diagonal_low_mode_target
        ),
        "conductive_heat_flux_galilean_correction_factor": (
            solver.mapping.collision.conductive_heat_flux_galilean_correction_factor
        ),
        "conductive_heat_flux_diagonal_low_mode_target": (
            solver.mapping.collision.conductive_heat_flux_diagonal_low_mode_target
        ),
        "acoustic_phase_correction_enabled": solver.mapping.collision.acoustic_phase_correction_enabled,
        "acoustic_phase_correction_low_laplacian": (
            solver.mapping.collision.acoustic_phase_correction_low_laplacian
        ),
        "acoustic_phase_diagonal_low_mode_factor": (
            solver.mapping.collision.acoustic_phase_diagonal_low_mode_factor
        ),
        "acoustic_phase_high_mode_factor": solver.mapping.collision.acoustic_phase_high_mode_factor,
        "acoustic_phase_high_mode_diagonal_factor": (
            solver.mapping.collision.acoustic_phase_high_mode_diagonal_factor
        ),
        "high_wavenumber_filter_enabled": solver.high_wavenumber_filter_enabled,
        "high_wavenumber_filter_strength": solver.high_wavenumber_filter_strength,
        "high_wavenumber_filter_passes": solver.high_wavenumber_filter_passes,
        "p2_04_shear_wave": _json_safe(p2_04),
        "p2_04_status": p2_04["p2_04_status"],
        "nu_target_lu": p2_04["nu_target_lu"],
        "nu_measured_lu": p2_04["nu_measured_lu"],
        "relative_error": p2_04["relative_error"],
        "mode_index": p2_04["mode_index"],
        "fitting_window": _json_safe(p2_04["fitting_window"]),
        "residual_norm": p2_04["residual_norm"],
        "directions": p2_04["directions"],
        "first_invalid_step": p2_04["first_invalid_step"],
        "nan_detected": p2_04["nan_detected"],
        "clipping_used": p2_04["clipping_used"],
        "p2_05_thermal_diffusion": _json_safe(p2_05),
        "p2_05_status": p2_05["p2_05_status"],
        "alpha_target_lu": p2_05["alpha_target_lu"],
        "alpha_measured_lu": p2_05["alpha_measured_lu"],
        "alpha_relative_error": p2_05["relative_error"],
        "thermal_mode_index": p2_05["mode_index"],
        "thermal_fitting_window": _json_safe(p2_05["fitting_window"]),
        "thermal_residual_norm": p2_05["residual_norm"],
        "thermal_directions": p2_05["directions"],
        "thermal_first_invalid_step": p2_05["first_invalid_step"],
        "thermal_nan_detected": p2_05["nan_detected"],
        "thermal_clipping_used": p2_05["clipping_used"],
        "heat_flux_relative_error": p2_05["heat_flux_relative_error"],
        "heat_flux_sign_passed": p2_05["heat_flux_sign_passed"],
        "p2_06_acoustic_wave": _json_safe(p2_06),
        "p2_06_status": p2_06["p2_06_status"],
        "sound_speed_target_lu": p2_06["sound_speed_target_lu"],
        "sound_speed_measured_lu": p2_06["sound_speed_measured_lu"],
        "sound_speed_relative_error": p2_06["sound_speed_relative_error"],
        "gamma_target": p2_06["gamma_target"],
        "gamma_measured": p2_06["gamma_measured"],
        "gamma_relative_error": p2_06["gamma_relative_error"],
        "acoustic_attenuation_measured_lu": p2_06["acoustic_attenuation_measured_lu"],
        "acoustic_attenuation_reference_lu": p2_06["acoustic_attenuation_reference_lu"],
        "acoustic_attenuation_relative_error": p2_06["acoustic_attenuation_relative_error"],
        "acoustic_attenuation_target_policy": p2_06["acoustic_attenuation_target_policy"],
        "acoustic_attenuation_target_coeff_lu": p2_06["acoustic_attenuation_target_coeff_lu"],
        "acoustic_attenuation_status": p2_06["attenuation_status"],
        "acoustic_direction_difference": p2_06["direction_difference"],
        "acoustic_mode_index": p2_06["mode_index"],
        "acoustic_fitting_window": _json_safe(p2_06["fitting_window"]),
        "acoustic_phase_residual_norm": p2_06["phase_residual_norm"],
        "acoustic_decay_residual_norm": p2_06["decay_residual_norm"],
        "acoustic_directions": p2_06["directions"],
        "acoustic_first_invalid_step": p2_06["first_invalid_step"],
        "acoustic_nan_detected": p2_06["nan_detected"],
        "acoustic_clipping_used": p2_06["clipping_used"],
        "p2_07_prandtl_scan": _json_safe(p2_07),
        "p2_07_status": p2_07["p2_07_status"],
        "pr_targets": p2_07["pr_targets"],
        "baseline_pr": p2_07["baseline_pr"],
        "baseline_pr_measured": p2_07["baseline_pr_measured"],
        "baseline_pr_relative_error": p2_07["baseline_pr_relative_error"],
        "max_pr_relative_error": p2_07["max_pr_relative_error"],
        "measured_pr_span": p2_07["measured_pr_span"],
        "pr_first_invalid_step": p2_07["first_invalid_step"],
        "pr_nan_detected": p2_07["nan_detected"],
        "pr_clipping_used": p2_07["clipping_used"],
        "p2_09_galilean_consistency": _json_safe(p2_09),
        "p2_09_status": p2_09["p2_09_status"],
        "p2_09_mach_numbers": p2_09["mach_numbers"],
        "p2_09_background_directions": p2_09["background_directions"],
        "p2_09_max_nu_drift_from_mach0": p2_09["max_nu_drift_from_mach0"],
        "p2_09_max_alpha_drift_from_mach0": p2_09["max_alpha_drift_from_mach0"],
        "p2_09_max_sound_speed_relative_error": p2_09["max_sound_speed_relative_error"],
        "p2_09_max_sound_speed_drift_from_mach0": p2_09["max_sound_speed_drift_from_mach0"],
        "p2_09_max_direction_difference": p2_09["max_direction_difference"],
        "p2_09_dispersion_masking_status": p2_09["dispersion_masking_status"],
        "p2_09_transport_dispersion_masking_status": p2_09[
            "transport_dispersion_masking_status"
        ],
        "p2_09_acoustic_eigenbranch_diagnostic_status": p2_09[
            "acoustic_eigenbranch_diagnostic_status"
        ],
        "p2_09_first_invalid_step": p2_09["first_invalid_step"],
        "p2_09_nan_detected": p2_09["nan_detected"],
        "p2_09_clipping_used": p2_09["clipping_used"],
    }
    summary["summary_json_sha256_policy"] = "sha256 of canonical summary payload before adding this digest field"
    summary["summary_json_sha256"] = summary_payload_digest(summary)
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path = out_dir / "M2_report.md"
    report_path.write_text(
        "\n".join(
            [
                "# Phase_2 M2 单次验证报告",
                "",
                f"- 配置：`{config_path}`",
                f"- 自动化状态：`{summary['automation_status']}`",
                f"- 合同级验证状态：`{summary['contract_validation_status']}`",
                f"- 生产级物理验证状态：`{summary['production_physics_status']}`",
                f"- M2 决策：`{summary['m2_decision']}`",
                f"- velocity_set：`{summary['velocity_set']}`",
                f"- Q：`{summary['Q']}`",
                f"- theta_q_lu：`{summary['theta_q_lu']}`",
                f"- P2-4 真实剪切波状态：`{summary['p2_04_status']}`",
                f"- P2-4 `nu_target_lu`：`{summary['nu_target_lu']}`",
                f"- P2-4 `nu_measured_lu`：`{summary['nu_measured_lu']}`",
                f"- P2-4 最大相对误差：`{summary['relative_error']}`",
                f"- P2-4 first_invalid_step：`{summary['first_invalid_step']}`",
                f"- P2-5 真实热扩散状态：`{summary['p2_05_status']}`",
                f"- P2-5 `alpha_target_lu`：`{summary['alpha_target_lu']}`",
                f"- P2-5 `alpha_measured_lu`：`{summary['alpha_measured_lu']}`",
                f"- P2-5 最大相对误差：`{summary['alpha_relative_error']}`",
                f"- P2-5 Fourier-law 热流误差：`{summary['heat_flux_relative_error']}`",
                f"- P2-6 真实 acoustic eigenmode 状态：`{summary['p2_06_status']}`",
                f"- P2-6 `sound_speed_target_lu`：`{summary['sound_speed_target_lu']}`",
                f"- P2-6 `sound_speed_measured_lu`：`{summary['sound_speed_measured_lu']}`",
                f"- P2-6 声速最大相对误差：`{summary['sound_speed_relative_error']}`",
                f"- P2-6 `gamma_measured`：`{summary['gamma_measured']}`",
                f"- P2-6 gamma 最大相对误差：`{summary['gamma_relative_error']}`",
                f"- P2-6 声衰减诊断 measured/reference：`{summary['acoustic_attenuation_measured_lu']} / {summary['acoustic_attenuation_reference_lu']}`",
                f"- P2-6 声衰减 target policy：`{summary['acoustic_attenuation_target_policy']}`",
                f"- P2-6 声衰减状态：`{summary['acoustic_attenuation_status']}`",
                f"- P2-7 真实 Pr 扫描状态：`{summary['p2_07_status']}`",
                f"- P2-7 baseline `Pr_measured`：`{summary['baseline_pr_measured']}`",
                f"- P2-7 最大 Pr 相对误差：`{summary['max_pr_relative_error']}`",
                f"- P2-9 真实 Galilean consistency 状态：`{summary['p2_09_status']}`",
                f"- P2-9 Mach 列表：`{summary['p2_09_mach_numbers']}`",
                f"- P2-9 背景速度方向：`{summary['p2_09_background_directions']}`",
                f"- P2-9 最大 `nu` 漂移：`{summary['p2_09_max_nu_drift_from_mach0']}`",
                f"- P2-9 最大 `alpha` 漂移：`{summary['p2_09_max_alpha_drift_from_mach0']}`",
                f"- P2-9 最大声速误差：`{summary['p2_09_max_sound_speed_relative_error']}`",
                f"- P2-9 最大声速漂移：`{summary['p2_09_max_sound_speed_drift_from_mach0']}`",
                f"- P2-9 dispersion masking 状态：`{summary['p2_09_dispersion_masking_status']}`",
                f"- P2-9 transport dispersion masking 状态：`{summary['p2_09_transport_dispersion_masking_status']}`",
                f"- P2-9 acoustic eigen-branch diagnostic 状态：`{summary['p2_09_acoustic_eigenbranch_diagnostic_status']}`",
                f"- regularized_heat_flux_factor_policy：`{summary['regularized_heat_flux_factor_policy']}`",
                f"- bulk_viscosity_policy：`{summary['bulk_viscosity_policy']}`",
                f"- central_moment_closure：`{summary['central_moment_closure']}`",
                f"- high_order_relaxation：`{summary['high_order_relaxation']}`",
                f"- regularized_heat_flux_factor：`{summary['regularized_heat_flux_factor']}`",
                f"- regularized_heat_flux_f_fraction：`{summary['regularized_heat_flux_f_fraction']}`",
                f"- conductive_heat_flux_moment_factor：`{summary['conductive_heat_flux_moment_factor']}`",
                f"- conductive_heat_flux_galilean_correction_factor：`{summary['conductive_heat_flux_galilean_correction_factor']}`",
                f"- high_wavenumber_filter：`enabled={summary['high_wavenumber_filter_enabled']}, strength={summary['high_wavenumber_filter_strength']}, passes={summary['high_wavenumber_filter_passes']}`",
                f"- HDF5 输出：`{h5_path}`",
                f"- config_sha256：`{summary['config_sha256']}`",
                f"- summary_json_sha256：`{summary['summary_json_sha256']}`",
                "",
                "## Pytest 输出",
                "",
                "```text",
                result.stdout.strip(),
                result.stderr.strip(),
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote {summary_path}")
    print(f"Wrote {report_path}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
