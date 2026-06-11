"""Run D2Q37 Phase 2 transport robustness probes.

Usage:
    python -m scripts.run_phase2_d2q37_transport_robustness
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
from typing import Any

import numpy as np

from core.unit_mapping import create_unit_mapping
from scripts.run_m2_verification import load_config, sha256_file, summary_payload_digest
from verification.transport_robustness_measurement import (
    prandtl_scan_scenario,
    summarize_robustness_scenarios,
    transport_pair_scenario,
)


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


def _pair_settings(
    *,
    shear_steps: int,
    thermal_steps: int,
    mode_index: int,
    amplitude: float,
    background_velocity_lu: list[float] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    shear = {
        "nx": 64,
        "ny": 64,
        "steps": shear_steps,
        "sample_interval": 1,
        "mode_index": mode_index,
        "amplitude": amplitude,
        "fit_start": 10,
        "directions": ["x", "y", "diagonal"],
        "relative_tolerance": 0.05,
        "direction_tolerance": 0.05,
    }
    thermal = {
        "nx": 64,
        "ny": 64,
        "steps": thermal_steps,
        "sample_interval": 1,
        "mode_index": mode_index,
        "amplitude": amplitude,
        "fit_start": 10,
        "directions": ["x", "y"],
        "relative_tolerance": 0.05,
        "heat_flux_tolerance": 0.05,
    }
    if background_velocity_lu is not None:
        shear["background_velocity_lu"] = list(background_velocity_lu)
        thermal["background_velocity_lu"] = list(background_velocity_lu)
    return shear, thermal


def _pr_long_settings() -> dict[str, Any]:
    return {
        "pr_targets": [0.5, 0.7061328707, 1.0, 2.0],
        "baseline_pr": 0.7061328707,
        "baseline_tolerance": 0.03,
        "scan_tolerance": 0.05,
        "shear_wave": {
            "nx": 64,
            "ny": 64,
            "steps": 240,
            "sample_interval": 1,
            "mode_index": 1,
            "amplitude": 1.0e-5,
            "fit_start": 10,
            "directions": ["x"],
            "relative_tolerance": 0.05,
        },
        "thermal_diffusion": {
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
        },
    }


def _run_scenarios(config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    mapping = create_unit_mapping(config)
    if mapping.lattice.velocity_set != "D2Q37":
        raise ValueError("D2Q37 robustness runner requires lattice.velocity_set=D2Q37")

    c_s_lu = float(np.sqrt(mapping.physical.gamma * mapping.theta_ref_lu))
    background_mach = 0.05
    high_background_velocity = [background_mach * c_s_lu, 0.0]
    context = {
        "velocity_set": mapping.lattice.velocity_set,
        "Q": mapping.lattice.Q,
        "theta_q_lu": mapping.lattice.theta_q_lu,
        "theta_ref_lu": mapping.theta_ref_lu,
        "c_s_lu": c_s_lu,
        "background_mach": background_mach,
        "high_background_velocity_lu": high_background_velocity,
    }

    scenarios: list[dict[str, Any]] = []

    shear, thermal = _pair_settings(
        shear_steps=240,
        thermal_steps=320,
        mode_index=1,
        amplitude=1.0e-5,
    )
    scenarios.append(
        transport_pair_scenario(
            config,
            name="d2q37_long_window",
            description="D2Q37 长时间窗口复核",
            shear_wave=shear,
            thermal_diffusion=thermal,
            config_role="d2q37_physical_timestep",
        )
    )

    shear, thermal = _pair_settings(
        shear_steps=120,
        thermal_steps=160,
        mode_index=2,
        amplitude=1.0e-5,
    )
    scenarios.append(
        transport_pair_scenario(
            config,
            name="d2q37_high_mode_m2",
            description="D2Q37 高模态 mode=2 复核",
            shear_wave=shear,
            thermal_diffusion=thermal,
            config_role="d2q37_physical_timestep",
        )
    )

    shear, thermal = _pair_settings(
        shear_steps=120,
        thermal_steps=320,
        mode_index=1,
        amplitude=1.0e-5,
        background_velocity_lu=high_background_velocity,
    )
    scenarios.append(
        transport_pair_scenario(
            config,
            name="d2q37_background_mach_0p05",
            description="D2Q37 高背景速度 Mach=0.05 输运复核",
            shear_wave=shear,
            thermal_diffusion=thermal,
            config_role="d2q37_physical_timestep",
        )
    )

    scenarios.append(
        prandtl_scan_scenario(
            config,
            name="d2q37_pr_long_window",
            description="D2Q37 P2-7 长时间窗口 Pr 扫描复核",
            prandtl_scan=_pr_long_settings(),
            config_role="d2q37_physical_timestep",
        )
    )

    return scenarios, context


def _scenario_table_rows(scenarios: list[dict[str, Any]]) -> list[str]:
    rows = []
    for item in scenarios:
        p2_04_err = item.get("p2_04_max_relative_error")
        p2_05_err = item.get("p2_05_max_relative_error")
        heat_err = item.get("p2_05_heat_flux_relative_error")
        pr_err = item.get("max_pr_relative_error")
        rows.append(
            "| "
            f"`{item['name']}` | "
            f"`{item['status']}` | "
            f"`{_format_value(p2_04_err)}` | "
            f"`{_format_value(p2_05_err)}` | "
            f"`{_format_value(heat_err)}` | "
            f"`{_format_value(pr_err)}` | "
            f"`{_format_value(item['first_invalid_step'])}` | "
            f"`{_format_value(item['nan_detected'])}` | "
            f"`{_format_value(item['clipping_used'])}` |"
        )
    return rows


def _write_report(summary: dict[str, Any], report_path: Path) -> None:
    failed_required = summary["failed_required_scenarios"]
    mapping = summary["scenarios"][0].get("mapping", {}) if summary.get("scenarios") else {}
    dispersion_enabled = mapping.get("dispersion_correction_enabled", False)
    lines = [
        "# Phase_2 D2Q37 输运鲁棒性复核报告",
        "",
        "本文档由 `python -m scripts.run_phase2_d2q37_transport_robustness` 生成。它只覆盖 D2Q37 fallback 新标定口径下的长窗口、mode=2 高模态、高背景速度和 P2-7 Pr 长窗口复核。",
        "",
        "## 结论",
        "",
        f"- run id：`{summary['run_id']}`",
        f"- required D2Q37 robustness status：`{summary['required_physical_status']}`",
        f"- D2Q37 candidate status：`{summary['d2q37_candidate_status']}`",
        f"- production_physics_status：`{summary['production_physics_status']}`",
        f"- M2 决策：`{summary['m2_decision']}`",
        f"- 失败场景：`{', '.join(failed_required) if failed_required else 'none'}`",
        "",
        "当前报告不启动 Phase_3，也不声明 final M2 production pass。后续 D2Q37 M2 run `20260610T141926Z` 已接续通过 P2-6 真实声学和 P2-9 真实 Galilean；matched 声衰减目标已推导，但 measured/reference 仍显著失配。",
        "",
        "## 背景速度口径",
        "",
        f"- `theta_ref_lu`：`{_format_value(summary['d2q37_context']['theta_ref_lu'])}`",
        f"- `c_s_lu=sqrt(gamma*theta_ref_lu)`：`{_format_value(summary['d2q37_context']['c_s_lu'])}`",
        f"- 高背景速度 Mach：`{_format_value(summary['d2q37_context']['background_mach'])}`",
        f"- 高背景速度 `u_lu`：`{_format_value(summary['d2q37_context']['high_background_velocity_lu'])}`",
        "",
        "## D2Q37 high-mode correction",
        "",
        f"- dispersion correction enabled：`{_format_value(dispersion_enabled)}`",
        f"- Laplacian thresholds：`[{_format_value(mapping.get('dispersion_correction_low_laplacian'))}, {_format_value(mapping.get('dispersion_correction_high_laplacian'))}]`",
        f"- stress targets：`xy={_format_value(mapping.get('regularized_shear_xy_dispersion_target'))}`, `normal={_format_value(mapping.get('regularized_shear_normal_dispersion_target'))}`",
        f"- heat-flux targets：`retention={_format_value(mapping.get('regularized_heat_flux_dispersion_target'))}`, `export={_format_value(mapping.get('conductive_heat_flux_dispersion_target'))}`",
        "",
        "## 场景汇总",
        "",
        "| 场景 | 状态 | P2-4 最大相对误差 | P2-5 最大相对误差 | Fourier-law 误差 | P2-7 最大 Pr 误差 | first_invalid_step | NaN | clipping |",
        "|---|---|---|---|---|---|---|---|---|",
        *_scenario_table_rows(summary["scenarios"]),
        "",
        "## 最大误差摘要",
        "",
        f"- P2-4 最大相对误差：`{_format_value(summary['max_p2_04_relative_error'])}`",
        f"- P2-5 最大相对误差：`{_format_value(summary['max_p2_05_relative_error'])}`",
        f"- P2-5 Fourier-law 最大误差：`{_format_value(summary['max_p2_05_heat_flux_relative_error'])}`",
        f"- P2-7 最大 Pr 相对误差：`{_format_value(summary['max_p2_07_pr_relative_error'])}`",
        f"- 任一场景 NaN：`{summary['nan_detected']}`",
        f"- 任一场景 clipping：`{summary['clipping_used']}`",
        "",
        "## 判读口径",
        "",
        "- required D2Q37 robustness 失败时，D2Q37 不能升级为 production candidate。",
        "- required D2Q37 robustness 通过时，D2Q37 只能升级为输运 production candidate；final M2 production pass 仍未声明。",
        "- 本报告的背景速度场景只覆盖输运测量；后续 D2Q37 M2 run `20260610T141926Z` 已将真实声学/Galilean 并入 P2-9 并通过。",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/gas_air_10k_d2q37_physical_timestep.yaml")
    parser.add_argument("--out-root", default="results/phase2_d2q37_transport_robustness")
    parser.add_argument("--report-out", default="docs/Phase_2/Phase2_D2Q37_Robustness_Report.md")
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_root) / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    config = load_config(config_path)
    scenarios, d2q37_context = _run_scenarios(config)
    status_summary = summarize_robustness_scenarios(scenarios)
    if status_summary["required_physical_status"] == "PASSED":
        status_summary["d2q37_candidate_status"] = "TRANSPORT_PRODUCTION_CANDIDATE"
        status_summary["production_physics_status"] = "IN_PROGRESS"
        status_summary["m2_decision"] = "GO-RISK / D2Q37_ROBUSTNESS_PASSED"
    else:
        status_summary["d2q37_candidate_status"] = "NOT_READY"
        status_summary["production_physics_status"] = "NOT_PASSED"
        status_summary["m2_decision"] = "GO-RISK / D2Q37_ROBUSTNESS_FAILED"

    summary = {
        "phase": "Phase_2",
        "run_id": timestamp,
        "timestamp": timestamp,
        "command": [sys.executable, "-m", "scripts.run_phase2_d2q37_transport_robustness", *sys.argv[1:]],
        "config": str(config_path),
        "config_sha256": sha256_file(config_path),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "scenario_scope": "D2Q37 long window, mode=2 high mode, high background Mach=0.05, Pr long window",
        "p2_scope": "P2-4/P2-5/P2-7 D2Q37 transport robustness; Phase_3 not started",
        "d2q37_context": _json_safe(d2q37_context),
        "scenarios": _json_safe(scenarios),
        **_json_safe(status_summary),
    }
    summary["summary_json_sha256_policy"] = "sha256 of canonical summary payload before adding this digest field"
    summary["summary_json_sha256"] = summary_payload_digest(summary)

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_report(summary, Path(args.report_out))
    print(f"Wrote {summary_path}")
    print(f"Wrote {args.report_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
