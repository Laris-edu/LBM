"""汇总 Phase 2 M2 验证输出到 docs/Phase_2/M2/M2_Verification_Report.md。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _fallback_statuses(data: dict) -> dict[str, str]:
    config = str(data.get("config", ""))
    old_status = str(data.get("status", "not_run"))
    passed = old_status == "PASSED"
    diagnostic = "quadrature" in config.lower()
    d2q37 = "d2q37" in config.lower() or str(data.get("velocity_set", "")).upper() == "D2Q37"
    if not passed:
        return {
            "automation_status": "FAILED",
            "contract_validation_status": "FAILED",
            "production_physics_status": "NOT_PASSED",
            "m2_decision": "NO-GO",
            "validation_level": "FAILED",
        }
    if diagnostic:
        return {
            "automation_status": "PASSED",
            "contract_validation_status": "DIAGNOSTIC_PASSED",
            "production_physics_status": "N/A",
            "m2_decision": "DIAGNOSTIC_ONLY",
            "validation_level": "CONTRACT",
        }
    if d2q37:
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


def _format_value(value) -> str:
    if value is None:
        return "none"
    if isinstance(value, float):
        if value != value:
            return "not_recorded"
        return f"{value:.6g}"
    return str(value)


def _format_attenuation_status(value) -> str:
    if value == "DIAGNOSTIC_ONLY_UNTIL_MATCHED_NSF_TARGET_DERIVATION":
        return "DIAGNOSTIC_ONLY_MATCHED_NSF_TARGET_DERIVED_GO_RISK"
    return str(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", default="results/m2")
    parser.add_argument("--out", default="docs/Phase_2/M2/M2_Verification_Report.md")
    args = parser.parse_args(argv)

    results_dir = Path(args.results_dir)
    summaries = sorted(results_dir.glob("*/summary.json"))
    rows = []
    for path in summaries:
        data = json.loads(path.read_text(encoding="utf-8"))
        statuses = _fallback_statuses(data)
        rows.append(
            {
                "run": data.get("run_id", path.parent.name),
                "config": data.get("config", ""),
                "automation_status": data.get("automation_status", statuses["automation_status"]),
                "contract_validation_status": data.get(
                    "contract_validation_status",
                    statuses["contract_validation_status"],
                ),
                "production_physics_status": data.get(
                    "production_physics_status",
                    statuses["production_physics_status"],
                ),
                "m2_decision": data.get("m2_decision", statuses["m2_decision"]),
                "validation_level": data.get("validation_level", statuses["validation_level"]),
                "bulk_viscosity_policy": data.get("bulk_viscosity_policy", ""),
                "velocity_set": data.get("velocity_set", "D2Q21"),
                "Q": data.get("Q", 21),
                "theta_q_lu": data.get("theta_q_lu", "not_recorded"),
                "central_moment_closure": data.get("central_moment_closure", "not_recorded"),
                "high_order_relaxation": data.get("high_order_relaxation", "not_recorded"),
                "trace_bulk_policy": data.get("trace_bulk_policy", "not_recorded"),
                "trace_bulk_scale": data.get("trace_bulk_scale", "not_recorded"),
                "regularized_heat_flux_factor_policy": data.get(
                    "regularized_heat_flux_factor_policy",
                    "specified",
                ),
                "regularized_heat_flux_factor": data.get("regularized_heat_flux_factor", "not_recorded"),
                "regularized_heat_flux_f_fraction": data.get(
                    "regularized_heat_flux_f_fraction",
                    "not_recorded",
                ),
                "heat_flux_retention_policy": data.get("heat_flux_retention_policy", "not_recorded"),
                "heat_flux_retention_curve_type": data.get("heat_flux_retention_curve_type", "not_recorded"),
                "conductive_heat_flux_moment_factor": data.get(
                    "conductive_heat_flux_moment_factor",
                    "not_recorded",
                ),
                "conductive_heat_flux_moment_factor_policy": data.get(
                    "conductive_heat_flux_moment_factor_policy",
                    "specified",
                ),
                "conductive_heat_flux_galilean_correction_factor": data.get(
                    "conductive_heat_flux_galilean_correction_factor",
                    "not_recorded",
                ),
                "high_wavenumber_filter_enabled": data.get(
                    "high_wavenumber_filter_enabled",
                    "not_recorded",
                ),
                "high_wavenumber_filter_strength": data.get(
                    "high_wavenumber_filter_strength",
                    "not_recorded",
                ),
                "config_sha256": data.get("config_sha256", "not_recorded"),
                "summary_json_sha256": data.get("summary_json_sha256", "not_recorded"),
                "p2_04_status": data.get("p2_04_status", "not_recorded"),
                "nu_target_lu": data["nu_target_lu"] if "nu_target_lu" in data else "not_recorded",
                "nu_measured_lu": data["nu_measured_lu"] if "nu_measured_lu" in data else "not_recorded",
                "relative_error": data["relative_error"] if "relative_error" in data else "not_recorded",
                "first_invalid_step": (
                    data["first_invalid_step"] if "first_invalid_step" in data else "not_recorded"
                ),
                "nan_detected": data["nan_detected"] if "nan_detected" in data else "not_recorded",
                "clipping_used": data["clipping_used"] if "clipping_used" in data else "not_recorded",
                "directions": data.get("directions", []),
                "p2_05_status": data.get("p2_05_status", "not_recorded"),
                "alpha_target_lu": data["alpha_target_lu"] if "alpha_target_lu" in data else "not_recorded",
                "alpha_measured_lu": (
                    data["alpha_measured_lu"] if "alpha_measured_lu" in data else "not_recorded"
                ),
                "alpha_relative_error": (
                    data["alpha_relative_error"] if "alpha_relative_error" in data else "not_recorded"
                ),
                "heat_flux_relative_error": (
                    data["heat_flux_relative_error"] if "heat_flux_relative_error" in data else "not_recorded"
                ),
                "heat_flux_sign_passed": (
                    data["heat_flux_sign_passed"] if "heat_flux_sign_passed" in data else "not_recorded"
                ),
                "p2_07_status": data.get("p2_07_status", "not_recorded"),
                "pr_targets": data.get("pr_targets", []),
                "baseline_pr": data["baseline_pr"] if "baseline_pr" in data else "not_recorded",
                "baseline_pr_measured": (
                    data["baseline_pr_measured"] if "baseline_pr_measured" in data else "not_recorded"
                ),
                "baseline_pr_relative_error": (
                    data["baseline_pr_relative_error"] if "baseline_pr_relative_error" in data else "not_recorded"
                ),
                "max_pr_relative_error": (
                    data["max_pr_relative_error"] if "max_pr_relative_error" in data else "not_recorded"
                ),
                "measured_pr_span": data["measured_pr_span"] if "measured_pr_span" in data else "not_recorded",
                "pr_first_invalid_step": (
                    data["pr_first_invalid_step"] if "pr_first_invalid_step" in data else "not_recorded"
                ),
                "pr_nan_detected": data["pr_nan_detected"] if "pr_nan_detected" in data else "not_recorded",
                "pr_clipping_used": (
                    data["pr_clipping_used"] if "pr_clipping_used" in data else "not_recorded"
                ),
                "pr_scan_points": data.get("p2_07_prandtl_scan", {}).get("scan_points", []),
                "thermal_first_invalid_step": (
                    data["thermal_first_invalid_step"] if "thermal_first_invalid_step" in data else "not_recorded"
                ),
                "thermal_nan_detected": (
                    data["thermal_nan_detected"] if "thermal_nan_detected" in data else "not_recorded"
                ),
                "thermal_clipping_used": (
                    data["thermal_clipping_used"] if "thermal_clipping_used" in data else "not_recorded"
                ),
                "thermal_directions": data.get("thermal_directions", []),
                "p2_06_status": data.get("p2_06_status", "not_recorded"),
                "sound_speed_target_lu": (
                    data["sound_speed_target_lu"] if "sound_speed_target_lu" in data else "not_recorded"
                ),
                "sound_speed_measured_lu": (
                    data["sound_speed_measured_lu"] if "sound_speed_measured_lu" in data else "not_recorded"
                ),
                "sound_speed_relative_error": (
                    data["sound_speed_relative_error"] if "sound_speed_relative_error" in data else "not_recorded"
                ),
                "gamma_target": data["gamma_target"] if "gamma_target" in data else "not_recorded",
                "gamma_measured": data["gamma_measured"] if "gamma_measured" in data else "not_recorded",
                "gamma_relative_error": (
                    data["gamma_relative_error"] if "gamma_relative_error" in data else "not_recorded"
                ),
                "acoustic_attenuation_measured_lu": (
                    data["acoustic_attenuation_measured_lu"]
                    if "acoustic_attenuation_measured_lu" in data
                    else "not_recorded"
                ),
                "acoustic_attenuation_reference_lu": (
                    data["acoustic_attenuation_reference_lu"]
                    if "acoustic_attenuation_reference_lu" in data
                    else "not_recorded"
                ),
                "acoustic_attenuation_relative_error": (
                    data["acoustic_attenuation_relative_error"]
                    if "acoustic_attenuation_relative_error" in data
                    else "not_recorded"
                ),
                "acoustic_attenuation_status": data.get(
                    "acoustic_attenuation_status",
                    "not_recorded",
                ),
                "acoustic_direction_difference": (
                    data["acoustic_direction_difference"]
                    if "acoustic_direction_difference" in data
                    else "not_recorded"
                ),
                "acoustic_first_invalid_step": (
                    data["acoustic_first_invalid_step"] if "acoustic_first_invalid_step" in data else "not_recorded"
                ),
                "acoustic_nan_detected": (
                    data["acoustic_nan_detected"] if "acoustic_nan_detected" in data else "not_recorded"
                ),
                "acoustic_clipping_used": (
                    data["acoustic_clipping_used"] if "acoustic_clipping_used" in data else "not_recorded"
                ),
                "acoustic_directions": data.get("acoustic_directions", []),
                "p2_09_status": data.get("p2_09_status", "not_recorded"),
                "p2_09_mach_numbers": data.get("p2_09_mach_numbers", []),
                "p2_09_background_directions": data.get("p2_09_background_directions", []),
                "p2_09_max_nu_drift_from_mach0": data.get(
                    "p2_09_max_nu_drift_from_mach0",
                    "not_recorded",
                ),
                "p2_09_max_alpha_drift_from_mach0": data.get(
                    "p2_09_max_alpha_drift_from_mach0",
                    "not_recorded",
                ),
                "p2_09_max_sound_speed_relative_error": data.get(
                    "p2_09_max_sound_speed_relative_error",
                    "not_recorded",
                ),
                "p2_09_max_sound_speed_drift_from_mach0": data.get(
                    "p2_09_max_sound_speed_drift_from_mach0",
                    "not_recorded",
                ),
                "p2_09_max_direction_difference": data.get(
                    "p2_09_max_direction_difference",
                    "not_recorded",
                ),
                "p2_09_dispersion_masking_status": data.get(
                    "p2_09_dispersion_masking_status",
                    "not_recorded",
                ),
                "p2_09_transport_dispersion_masking_status": data.get(
                    "p2_09_transport_dispersion_masking_status",
                    data.get("p2_09_dispersion_masking_status", "not_recorded"),
                ),
                "p2_09_acoustic_eigenbranch_diagnostic_status": data.get(
                    "p2_09_acoustic_eigenbranch_diagnostic_status",
                    "not_recorded",
                ),
                "p2_09_first_invalid_step": data.get(
                    "p2_09_first_invalid_step",
                    "not_recorded",
                ),
                "p2_09_nan_detected": data.get("p2_09_nan_detected", "not_recorded"),
                "p2_09_clipping_used": data.get("p2_09_clipping_used", "not_recorded"),
                "p2_09_scenarios": data.get("p2_09_galilean_consistency", {}).get(
                    "scenarios",
                    [],
                ),
            }
        )

    lines = [
        "# Phase_2 M2 验证报告",
        "",
        "本文档由 `python -m scripts.phase2_m2_summarize` 生成。",
        "",
        "## 报告范围",
        "",
        "本文档记录 Phase_2 自动化测试和合同级验证状态。除非 physical-timestep mapping 的 `production_physics_status` 明确标记为 `PASSED`，否则本文档不声明最终 M2 production pass。",
        "",
        "quadrature-matched mapping 默认为诊断路径，不能单独建立 M2 production pass。",
        "",
        "## M2 Decision",
        "",
        "- Automation suite：见下表 `automation_status`。",
        "- Contract-level Phase_2 checks：见下表 `contract_validation_status`。",
        "- Production physical validation：当前仍为 `NOT_PASSED` 或 `N/A`。",
        "- Current decision：`GO-RISK / IN-PROGRESS`，不是 final M2 production pass。",
        "- 2026-06-15 note：D2Q37 trace / bulk 与 heat-flux retention 已显式参数化；默认仍为 `trace_bulk_policy=current_zero` 和当前 `auto_d2q37_tau32_linear`，该改造只提供后续声衰减联合扫描入口。",
        "",
        "## 汇总运行",
        "",
        "| 运行批次 | 配置 | velocity_set | Q | theta_q_lu | automation_status | contract_validation_status | production_physics_status | M2 决策 | validation_level | bulk_viscosity_policy | central_moment_closure | high_order_relaxation | trace_policy | trace_scale | heat_flux_policy | heat_flux_factor | heat_curve_policy | heat_curve_type | f_fraction | conductive_policy | conductive_factor | Galilean_q_factor | high_k_filter | config_sha256 | summary_json_sha256 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    if rows:
        for row in rows:
            lines.append(
                "| "
                f"`{row['run']}` | "
                f"`{row['config']}` | "
                f"`{row['velocity_set']}` | "
                f"`{row['Q']}` | "
                f"`{_format_value(row['theta_q_lu'])}` | "
                f"`{row['automation_status']}` | "
                f"`{row['contract_validation_status']}` | "
                f"`{row['production_physics_status']}` | "
                f"`{row['m2_decision']}` | "
                f"`{row['validation_level']}` | "
                f"`{row['bulk_viscosity_policy']}` | "
                f"`{row['central_moment_closure']}` | "
                f"`{_format_value(row['high_order_relaxation'])}` | "
                f"`{row['trace_bulk_policy']}` | "
                f"`{_format_value(row['trace_bulk_scale'])}` | "
                f"`{row['regularized_heat_flux_factor_policy']}` | "
                f"`{_format_value(row['regularized_heat_flux_factor'])}` | "
                f"`{row['heat_flux_retention_policy']}` | "
                f"`{row['heat_flux_retention_curve_type']}` | "
                f"`{_format_value(row['regularized_heat_flux_f_fraction'])}` | "
                f"`{row['conductive_heat_flux_moment_factor_policy']}` | "
                f"`{_format_value(row['conductive_heat_flux_moment_factor'])}` | "
                f"`{_format_value(row['conductive_heat_flux_galilean_correction_factor'])}` | "
                f"`{_format_value(row['high_wavenumber_filter_enabled'])}:{_format_value(row['high_wavenumber_filter_strength'])}` | "
                f"`{str(row['config_sha256'])[:12]}` | "
                f"`{str(row['summary_json_sha256'])[:12]}` |"
            )
    else:
        lines.append(
            "| n/a | n/a | n/a | n/a | n/a | not_run | not_run | not_run | not_run | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |"
        )

    lines.extend(
        [
            "",
            "## P2-4 真实剪切波黏性测量",
            "",
            "本节记录真实周期域 shear-wave decay 测量。该表用于推进 production physics validation；若 physical-timestep mapping 的 P2-4 状态为 `FAILED`，则应保持 `production_physics_status=NOT_PASSED`，不得声明 final M2 production pass。",
            "",
            "| 运行批次 | P2-4 状态 | nu_target_lu | nu_measured_lu | 最大相对误差 | first_invalid_step | NaN | clipping | directions |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    if rows:
        for row in rows:
            lines.append(
                "| "
                f"`{row['run']}` | "
                f"`{row['p2_04_status']}` | "
                f"`{_format_value(row['nu_target_lu'])}` | "
                f"`{_format_value(row['nu_measured_lu'])}` | "
                f"`{_format_value(row['relative_error'])}` | "
                f"`{_format_value(row['first_invalid_step'])}` | "
                f"`{_format_value(row['nan_detected'])}` | "
                f"`{_format_value(row['clipping_used'])}` | "
                f"`{','.join(row['directions']) if row['directions'] else 'not_recorded'}` |"
            )
    else:
        lines.append("| n/a | not_run | n/a | n/a | n/a | n/a | n/a | n/a | n/a |")

    lines.extend(
        [
            "",
            "## P2-5 真实热扩散与 Fourier-law 热流验证",
            "",
            "本节记录真实等压 thermal sine decay 和 Fourier-law 热流符号/幅值检查。若 physical-timestep mapping 的 P2-5 状态为 `FAILED`，则应保持 `production_physics_status=NOT_PASSED`，不得声明 final M2 production pass。",
            "",
            "| 运行批次 | P2-5 状态 | alpha_target_lu | alpha_measured_lu | 最大相对误差 | Fourier-law 误差 | 热流符号 | first_invalid_step | NaN | clipping | directions |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    if rows:
        for row in rows:
            lines.append(
                "| "
                f"`{row['run']}` | "
                f"`{row['p2_05_status']}` | "
                f"`{_format_value(row['alpha_target_lu'])}` | "
                f"`{_format_value(row['alpha_measured_lu'])}` | "
                f"`{_format_value(row['alpha_relative_error'])}` | "
                f"`{_format_value(row['heat_flux_relative_error'])}` | "
                f"`{_format_value(row['heat_flux_sign_passed'])}` | "
                f"`{_format_value(row['thermal_first_invalid_step'])}` | "
                f"`{_format_value(row['thermal_nan_detected'])}` | "
                f"`{_format_value(row['thermal_clipping_used'])}` | "
                f"`{','.join(row['thermal_directions']) if row['thermal_directions'] else 'not_recorded'}` |"
            )
    else:
        lines.append("| n/a | not_run | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |")

    lines.extend(
        [
            "",
            "## P2-6 真实声学 eigenmode、声速与 gamma",
            "",
            "本节记录真实周期域 acoustic eigenmode 演化。声速和由声速反推的 `gamma` 是 hard metric；声衰减 reference 已按 `D=2, S=3`、`diagnostic_zero` bulk policy 和 conductive heat-flux convention 匹配为 linearized NSF target，但当前仍只作为 diagnostic/GO-RISK 指标记录。",
            "",
            "| 运行批次 | P2-6 状态 | c_target_lu | c_measured_lu | 声速最大相对误差 | gamma_target | gamma_measured | gamma 最大相对误差 | 声衰减 measured | 声衰减 reference | 声衰减误差 | 声衰减状态 | 方向差异 | first_invalid_step | NaN | clipping | directions |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    if rows:
        for row in rows:
            lines.append(
                "| "
                f"`{row['run']}` | "
                f"`{row['p2_06_status']}` | "
                f"`{_format_value(row['sound_speed_target_lu'])}` | "
                f"`{_format_value(row['sound_speed_measured_lu'])}` | "
                f"`{_format_value(row['sound_speed_relative_error'])}` | "
                f"`{_format_value(row['gamma_target'])}` | "
                f"`{_format_value(row['gamma_measured'])}` | "
                f"`{_format_value(row['gamma_relative_error'])}` | "
                f"`{_format_value(row['acoustic_attenuation_measured_lu'])}` | "
                f"`{_format_value(row['acoustic_attenuation_reference_lu'])}` | "
                f"`{_format_value(row['acoustic_attenuation_relative_error'])}` | "
                f"`{_format_attenuation_status(row['acoustic_attenuation_status'])}` | "
                f"`{_format_value(row['acoustic_direction_difference'])}` | "
                f"`{_format_value(row['acoustic_first_invalid_step'])}` | "
                f"`{_format_value(row['acoustic_nan_detected'])}` | "
                f"`{_format_value(row['acoustic_clipping_used'])}` | "
                f"`{','.join(row['acoustic_directions']) if row['acoustic_directions'] else 'not_recorded'}` |"
            )
    else:
        lines.append("| n/a | not_run | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |")

    lines.extend(
        [
            "",
            "## P2-7 真实 Pr 扫描",
            "",
            "本节记录多点真实 `nu/alpha/Pr` 联合测量。当前 P2-7 若为 `FAILED`，表示 `tau21/tau32` 的合同映射通过但生产级热扩散独立控制尚未证明；不得声明 final M2 production pass。",
            "",
            "| 运行批次 | P2-7 状态 | baseline Pr | baseline Pr_measured | baseline 相对误差 | 最大 Pr 相对误差 | measured Pr span | first_invalid_step | NaN | clipping | targets |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    if rows:
        for row in rows:
            targets = ",".join(_format_value(item) for item in row["pr_targets"]) if row["pr_targets"] else "not_recorded"
            lines.append(
                "| "
                f"`{row['run']}` | "
                f"`{row['p2_07_status']}` | "
                f"`{_format_value(row['baseline_pr'])}` | "
                f"`{_format_value(row['baseline_pr_measured'])}` | "
                f"`{_format_value(row['baseline_pr_relative_error'])}` | "
                f"`{_format_value(row['max_pr_relative_error'])}` | "
                f"`{_format_value(row['measured_pr_span'])}` | "
                f"`{_format_value(row['pr_first_invalid_step'])}` | "
                f"`{_format_value(row['pr_nan_detected'])}` | "
                f"`{_format_value(row['pr_clipping_used'])}` | "
                f"`{targets}` |"
            )
    else:
        lines.append("| n/a | not_run | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |")

    lines.extend(
        [
            "",
            "### P2-7 扫描点明细",
            "",
            "| 运行批次 | Pr_target | Pr_measured | Pr 相对误差 | 状态 | tau32 | heat_flux_factor | nu_measured_lu | alpha_measured_lu | alpha 相对误差 | heat flux error |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    detail_rows = 0
    for row in rows:
        for point in row["pr_scan_points"]:
            detail_rows += 1
            lines.append(
                "| "
                f"`{row['run']}` | "
                f"`{_format_value(point.get('pr_target'))}` | "
                f"`{_format_value(point.get('pr_measured'))}` | "
                f"`{_format_value(point.get('pr_relative_error'))}` | "
                f"`{point.get('status', 'not_recorded')}` | "
                f"`{_format_value(point.get('tau32'))}` | "
                f"`{_format_value(point.get('regularized_heat_flux_factor'))}` | "
                f"`{_format_value(point.get('nu_measured_lu'))}` | "
                f"`{_format_value(point.get('alpha_measured_lu'))}` | "
                f"`{_format_value(point.get('alpha_relative_error'))}` | "
                f"`{_format_value(point.get('heat_flux_relative_error'))}` |"
            )
    if detail_rows == 0:
        lines.append("| n/a | n/a | n/a | n/a | not_recorded | n/a | n/a | n/a | n/a | n/a | n/a |")

    lines.extend(
        [
            "",
            "## P2-9 真实 Galilean consistency",
            "",
            "本节记录背景速度下真实剪切波、热扩散和 acoustic eigenmode 测量。`nu/alpha` 以相对 Mach 0 的漂移作为 hard metric；声学在扣除 `k·U0` 后检查声速误差和方向差异。D2Q37 dispersion correction 开/关对照只作为 transport masking hard check；high-mode acoustic eigen-branch 另列 diagnostic，不与 masking hard status 混用。",
            "",
            "| 运行批次 | P2-9 状态 | Mach 列表 | 背景方向 | 最大 nu 漂移 | 最大 alpha 漂移 | 最大声速误差 | 最大声速漂移 | 最大方向差异 | transport masking | acoustic eigenbranch diag | legacy masking | first_invalid_step | NaN | clipping |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    if rows:
        for row in rows:
            machs = (
                ",".join(_format_value(item) for item in row["p2_09_mach_numbers"])
                if row["p2_09_mach_numbers"]
                else "not_recorded"
            )
            background_directions = (
                ",".join(row["p2_09_background_directions"])
                if row["p2_09_background_directions"]
                else "not_recorded"
            )
            lines.append(
                "| "
                f"`{row['run']}` | "
                f"`{row['p2_09_status']}` | "
                f"`{machs}` | "
                f"`{background_directions}` | "
                f"`{_format_value(row['p2_09_max_nu_drift_from_mach0'])}` | "
                f"`{_format_value(row['p2_09_max_alpha_drift_from_mach0'])}` | "
                f"`{_format_value(row['p2_09_max_sound_speed_relative_error'])}` | "
                f"`{_format_value(row['p2_09_max_sound_speed_drift_from_mach0'])}` | "
                f"`{_format_value(row['p2_09_max_direction_difference'])}` | "
                f"`{row['p2_09_transport_dispersion_masking_status']}` | "
                f"`{row['p2_09_acoustic_eigenbranch_diagnostic_status']}` | "
                f"`{row['p2_09_dispersion_masking_status']}` | "
                f"`{_format_value(row['p2_09_first_invalid_step'])}` | "
                f"`{_format_value(row['p2_09_nan_detected'])}` | "
                f"`{_format_value(row['p2_09_clipping_used'])}` |"
            )
    else:
        lines.append("| n/a | not_run | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |")

    lines.extend(
        [
            "",
            "### P2-9 场景明细",
            "",
            "| 运行批次 | 场景 | Mach | 背景方向 | u_lu | 状态 | nu 漂移 | alpha 漂移 | 声速误差 | 声速漂移 | Fourier-law 误差 | 方向差异 |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    p2_09_detail_rows = 0
    for row in rows:
        for scenario in row["p2_09_scenarios"]:
            p2_09_detail_rows += 1
            u_lu = scenario.get("background_velocity_lu", [])
            u_lu_text = ",".join(_format_value(item) for item in u_lu) if u_lu else "not_recorded"
            lines.append(
                "| "
                f"`{row['run']}` | "
                f"`{scenario.get('name', 'not_recorded')}` | "
                f"`{_format_value(scenario.get('mach'))}` | "
                f"`{scenario.get('background_direction', 'not_recorded')}` | "
                f"`{u_lu_text}` | "
                f"`{scenario.get('status', 'not_recorded')}` | "
                f"`{_format_value(scenario.get('nu_drift_from_mach0'))}` | "
                f"`{_format_value(scenario.get('alpha_drift_from_mach0'))}` | "
                f"`{_format_value(scenario.get('sound_speed_relative_error'))}` | "
                f"`{_format_value(scenario.get('sound_speed_drift_from_mach0'))}` | "
                f"`{_format_value(scenario.get('heat_flux_relative_error'))}` | "
                f"`{_format_value(scenario.get('direction_difference'))}` |"
            )
    if p2_09_detail_rows == 0:
        lines.append("| n/a | n/a | n/a | n/a | n/a | not_recorded | n/a | n/a | n/a | n/a | n/a | n/a |")

    lines.extend(
        [
            "",
            "## 验证编号",
            "",
            "验证编号冻结为 P2-0 到 P2-9。后处理与 HDF5 schema 检查属于支撑测试，不新增 P2 编号。",
            "",
            "## 基线策略",
            "",
            "- 基线 `bulk_viscosity_policy`：`diagnostic_zero`。",
            "- 当前 NSF 线性声衰减目标已完成匹配推导；因 D2Q37 measured/reference 仍显著偏离，声衰减保持 diagnostic/GO-RISK 指标。",
            "- 当前 heat-flux/tau32 关系已固化为 projection closure：`alpha_lu=theta_transport_lu*(tau32-0.5)` 是唯一热扩散映射，`regularized_heat_flux_factor=h_family(tau32)` 只作为 raw central heat-flux retention。",
            "- M2 pass/fail 运行不得使用 clipping、distribution floor 或 positivity repair。",
            "",
            "## Phase_1 回归",
            "",
            "Phase_2 合并前，`verification/` 和 `tests/` 下的 Phase_1 回归测试必须继续通过。",
            "",
        ]
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
