"""Run Phase 2 transport robustness probes.

Usage:
    python -m scripts.run_phase2_transport_robustness
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys

import numpy as np

from scripts.run_m2_verification import load_config, sha256_file, summary_payload_digest
from verification.transport_robustness_measurement import (
    prandtl_scan_scenario,
    summarize_robustness_scenarios,
    transport_pair_scenario,
)


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


def _format_value(value) -> str:
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
) -> tuple[dict, dict]:
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


def _pr_long_settings() -> dict:
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


def _run_scenarios(physical_config: dict, quadrature_config: dict) -> list[dict]:
    scenarios: list[dict] = []

    shear, thermal = _pair_settings(shear_steps=240, thermal_steps=320, mode_index=1, amplitude=1.0e-5)
    scenarios.append(
        transport_pair_scenario(
            physical_config,
            name="physical_long_window",
            description="physical-timestep 长时间窗口复核",
            shear_wave=shear,
            thermal_diffusion=thermal,
        )
    )

    shear, thermal = _pair_settings(shear_steps=120, thermal_steps=160, mode_index=2, amplitude=1.0e-5)
    scenarios.append(
        transport_pair_scenario(
            physical_config,
            name="physical_high_mode_m2",
            description="physical-timestep 高模态 mode=2 复核",
            shear_wave=shear,
            thermal_diffusion=thermal,
        )
    )

    shear, thermal = _pair_settings(shear_steps=120, thermal_steps=320, mode_index=1, amplitude=3.0e-5)
    scenarios.append(
        transport_pair_scenario(
            physical_config,
            name="physical_amplitude_3e-5",
            description="physical-timestep 振幅 A=3e-5 复核",
            shear_wave=shear,
            thermal_diffusion=thermal,
        )
    )

    shear, thermal = _pair_settings(
        shear_steps=120,
        thermal_steps=320,
        mode_index=1,
        amplitude=1.0e-5,
        background_velocity_lu=[5.0e-3, 0.0],
    )
    scenarios.append(
        transport_pair_scenario(
            physical_config,
            name="physical_background_ux_0p005",
            description="physical-timestep 背景速度 ux=0.005 LU 复核",
            shear_wave=shear,
            thermal_diffusion=thermal,
        )
    )

    scenarios.append(
        prandtl_scan_scenario(
            physical_config,
            name="physical_pr_long_window",
            description="physical-timestep P2-7 长时间窗口 Pr 扫描复核",
            prandtl_scan=_pr_long_settings(),
        )
    )

    shear, thermal = _pair_settings(shear_steps=120, thermal_steps=160, mode_index=1, amplitude=1.0e-5)
    scenarios.append(
        transport_pair_scenario(
            quadrature_config,
            name="quadrature_matched_configured",
            description="quadrature-matched 诊断配置对照",
            shear_wave=shear,
            thermal_diffusion=thermal,
            required_for_production=False,
            config_role="quadrature_matched_diagnostic",
        )
    )

    return scenarios


def _scenario_table_rows(scenarios: list[dict]) -> list[str]:
    rows = []
    for item in scenarios:
        p2_04_err = item.get("p2_04_max_relative_error")
        p2_05_err = item.get("p2_05_max_relative_error")
        heat_err = item.get("p2_05_heat_flux_relative_error")
        pr_err = item.get("max_pr_relative_error")
        rows.append(
            "| "
            f"`{item['name']}` | "
            f"`{item['config_role']}` | "
            f"`{item['required_for_production']}` | "
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


def _write_report(summary: dict, report_path: Path) -> None:
    scenario_lines = _scenario_table_rows(summary["scenarios"])
    failed_required = summary["failed_required_scenarios"]
    failed_diag = summary["failed_diagnostic_scenarios"]
    lines = [
        "# Phase_2 输运鲁棒性复核报告",
        "",
        "本文档由 `python -m scripts.run_phase2_transport_robustness` 生成。它记录 P2-4/P2-5/P2-7 在长时间窗口、高模态、不同振幅、背景速度和 quadrature-matched 对照下的复核结果。",
        "",
        "## 结论",
        "",
        f"- run id：`{summary['run_id']}`",
        f"- required physical status：`{summary['required_physical_status']}`",
        f"- diagnostic control status：`{summary['diagnostic_control_status']}`",
        f"- production_physics_status：`{summary['production_physics_status']}`",
        f"- M2 决策：`{summary['m2_decision']}`",
        f"- 失败的 required physical 场景：`{', '.join(failed_required) if failed_required else 'none'}`",
        f"- 失败的 diagnostic 对照场景：`{', '.join(failed_diag) if failed_diag else 'none'}`",
        "",
        "当前报告不启动 Phase_3，也不声明 final M2 production pass。physical-timestep 短时 C2 通过仍需和本报告中的鲁棒性失败分开理解。",
        "",
        "## 场景汇总",
        "",
        "| 场景 | 配置角色 | production 必需 | 状态 | P2-4 最大相对误差 | P2-5 最大相对误差 | Fourier-law 误差 | P2-7 最大 Pr 误差 | first_invalid_step | NaN | clipping |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
        *scenario_lines,
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
        "- required physical 场景失败时，`production_physics_status` 保持 `NOT_PASSED`。",
        "- quadrature-matched 场景是诊断对照，不单独建立 production pass。",
        "- 本报告的背景速度场景只覆盖输运测量；P2-9 真实声学/Galilean 由 D2Q37 M2 run `20260610T141926Z` 接续通过。",
        "- 本报告暴露的问题优先回到 heat-flux/tau32 闭合、central-Hermite/binomial transform 和长时间稳定性分析。",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/gas_air_10k_physical_timestep.yaml")
    parser.add_argument("--quadrature-config", default="configs/gas_air_10k_quadrature_matched.yaml")
    parser.add_argument("--out-root", default="results/phase2_transport_robustness")
    parser.add_argument("--report-out", default="docs/Phase_2/Phase2_Transport_Robustness_Report.md")
    args = parser.parse_args(argv)

    physical_path = Path(args.config)
    quadrature_path = Path(args.quadrature_config)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_root) / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    physical_config = load_config(physical_path)
    quadrature_config = load_config(quadrature_path)
    scenarios = _run_scenarios(physical_config, quadrature_config)
    status_summary = summarize_robustness_scenarios(scenarios)
    summary = {
        "phase": "Phase_2",
        "run_id": timestamp,
        "timestamp": timestamp,
        "command": [sys.executable, "-m", "scripts.run_phase2_transport_robustness", *sys.argv[1:]],
        "config": str(physical_path),
        "quadrature_config": str(quadrature_path),
        "config_sha256": sha256_file(physical_path),
        "quadrature_config_sha256": sha256_file(quadrature_path),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "scenario_scope": (
            "long window, high mode, alternate amplitude, background velocity, "
            "quadrature-matched diagnostic control"
        ),
        "p2_scope": "P2-4/P2-5/P2-7 transport robustness; Phase_3 not started",
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
