"""汇总 Phase 2 M2 验证输出到 docs/M2_Verification_Report.md。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _fallback_statuses(data: dict) -> dict[str, str]:
    config = str(data.get("config", ""))
    old_status = str(data.get("status", "not_run"))
    passed = old_status == "PASSED"
    diagnostic = "quadrature" in config.lower()
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", default="results/m2")
    parser.add_argument("--out", default="docs/M2_Verification_Report.md")
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
                "regularized_heat_flux_factor": data.get("regularized_heat_flux_factor", "not_recorded"),
                "regularized_heat_flux_f_fraction": data.get(
                    "regularized_heat_flux_f_fraction",
                    "not_recorded",
                ),
                "conductive_heat_flux_moment_factor": data.get(
                    "conductive_heat_flux_moment_factor",
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
            }
        )

    lines = [
        "# Phase_2 M2 验证报告",
        "",
        "本文档由 `python -m scripts.summarize_m2` 生成。",
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
        "",
        "## 汇总运行",
        "",
        "| 运行批次 | 配置 | automation_status | contract_validation_status | production_physics_status | M2 决策 | validation_level | bulk_viscosity_policy | heat_flux_factor | f_fraction | conductive_factor | config_sha256 | summary_json_sha256 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    if rows:
        for row in rows:
            lines.append(
                "| "
                f"`{row['run']}` | "
                f"`{row['config']}` | "
                f"`{row['automation_status']}` | "
                f"`{row['contract_validation_status']}` | "
                f"`{row['production_physics_status']}` | "
                f"`{row['m2_decision']}` | "
                f"`{row['validation_level']}` | "
                f"`{row['bulk_viscosity_policy']}` | "
                f"`{_format_value(row['regularized_heat_flux_factor'])}` | "
                f"`{_format_value(row['regularized_heat_flux_f_fraction'])}` | "
                f"`{_format_value(row['conductive_heat_flux_moment_factor'])}` | "
                f"`{str(row['config_sha256'])[:12]}` | "
                f"`{str(row['summary_json_sha256'])[:12]}` |"
            )
    else:
        lines.append("| n/a | n/a | not_run | not_run | not_run | not_run | n/a | n/a | n/a | n/a | n/a | n/a | n/a |")

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
            "## 验证编号",
            "",
            "验证编号冻结为 P2-0 到 P2-9。后处理与 HDF5 schema 检查属于支撑测试，不新增 P2 编号。",
            "",
            "## 基线策略",
            "",
            "- 基线 `bulk_viscosity_policy`：`diagnostic_zero`。",
            "- 在完成与当前 NSF 线性声衰减目标匹配的推导前，声衰减保持为 diagnostic/GO-RISK 指标。",
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
