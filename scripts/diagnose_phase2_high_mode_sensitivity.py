"""Diagnose Phase 2 high-mode scalar closure sensitivity.

Usage:
    python -m scripts.diagnose_phase2_high_mode_sensitivity
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
from verification.high_mode_sensitivity import run_high_mode_sensitivity


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


def _shear_rows(rows: list[dict], *, measured_key: str, error_key: str) -> list[str]:
    lines = []
    for row in rows:
        lines.append(
            "| "
            f"`{_format_value(row['value'])}` | "
            f"`{row['direction']}` | "
            f"`{_format_value(row[f'mode1_{measured_key}'])}` | "
            f"`{_format_value(row[f'mode1_{error_key}'])}` | "
            f"`{_format_value(row[f'mode2_{measured_key}'])}` | "
            f"`{_format_value(row[f'mode2_{error_key}'])}` | "
            f"`{row['joint_status']}` |"
        )
    return lines


def _heat_rows(rows: list[dict]) -> list[str]:
    lines = []
    for row in rows:
        lines.append(
            "| "
            f"`{_format_value(row['value'])}` | "
            f"`{row['direction']}` | "
            f"`{_format_value(row['mode1_alpha_measured_lu'])}` | "
            f"`{_format_value(row['mode1_alpha_relative_error'])}` | "
            f"`{_format_value(row['mode1_heat_flux_relative_error'])}` | "
            f"`{_format_value(row['mode2_alpha_measured_lu'])}` | "
            f"`{_format_value(row['mode2_alpha_relative_error'])}` | "
            f"`{_format_value(row['mode2_heat_flux_relative_error'])}` | "
            f"`{row['joint_status']}` |"
        )
    return lines


def _write_report(summary: dict, report_path: Path) -> None:
    groups = summary["scan_groups"]
    xy = groups["regularized_shear_xy_factor"]
    normal = groups["regularized_shear_normal_factor"]
    heat = groups["regularized_heat_flux_factor"]
    joint_pass_exists = any(group["summary"]["joint_pass_exists"] for group in groups.values())
    lines = [
        "# Phase_2 high-mode 标量敏感性诊断报告",
        "",
        "本文档由 `python -m scripts.diagnose_phase2_high_mode_sensitivity` 生成。它只诊断当前 D2Q21 physical-timestep collision 的经验标量，不修改 production baseline，不声明 final M2 production pass。",
        "",
        "## 结论",
        "",
        f"- run id：`{summary['run_id']}`",
        f"- 配置：`{summary['config']}`",
        f"- 容差：`{_format_value(summary['tolerance'])}`",
        f"- 扫描网格中是否存在同时通过 mode=1 和 mode=2 的标量组合：`{joint_pass_exists}`",
        "- 判读：当前 high-mode failure 不能靠单个 `regularized_shear_xy_factor`、`regularized_shear_normal_factor` 或 `regularized_heat_flux_factor` 的局部标量重调修复；继续推进应回到完整 central-Hermite/binomial 高阶闭合或 D2Q37/等价九阶速度集路线。",
        "",
        "## regularized_shear_xy_factor",
        "",
        f"- joint_pass_exists：`{xy['summary']['joint_pass_exists']}`",
        f"- best_value：`{_format_value(xy['summary']['best_value'])}`",
        f"- best_max_metric：`{_format_value(xy['summary']['best_max_metric'])}`",
        "",
        "| factor | direction | mode=1 nu_measured_lu | mode=1 relative_error | mode=2 nu_measured_lu | mode=2 relative_error | joint_status |",
        "|---|---|---|---|---|---|---|",
        *_shear_rows(xy["rows"], measured_key="nu_measured_lu", error_key="relative_error"),
        "",
        "## regularized_shear_normal_factor",
        "",
        f"- joint_pass_exists：`{normal['summary']['joint_pass_exists']}`",
        f"- best_value：`{_format_value(normal['summary']['best_value'])}`",
        f"- best_max_metric：`{_format_value(normal['summary']['best_max_metric'])}`",
        "",
        "| factor | direction | mode=1 nu_measured_lu | mode=1 relative_error | mode=2 nu_measured_lu | mode=2 relative_error | joint_status |",
        "|---|---|---|---|---|---|---|",
        *_shear_rows(normal["rows"], measured_key="nu_measured_lu", error_key="relative_error"),
        "",
        "## regularized_heat_flux_factor",
        "",
        f"- joint_pass_exists：`{heat['summary']['joint_pass_exists']}`",
        f"- best_value：`{_format_value(heat['summary']['best_value'])}`",
        f"- best_max_metric：`{_format_value(heat['summary']['best_max_metric'])}`",
        "",
        "| factor | direction | mode=1 alpha_measured_lu | mode=1 alpha_error | mode=1 heat_flux_error | mode=2 alpha_measured_lu | mode=2 alpha_error | mode=2 heat_flux_error | joint_status |",
        "|---|---|---|---|---|---|---|---|---|",
        *_heat_rows(heat["rows"]),
        "",
        "## 判读口径",
        "",
        "- 本诊断不是连续参数优化证明，只是当前经验标量在局部网格上的可复现实证排查。",
        "- 若某个标量能改善 mode=2，但同时破坏 mode=1 低模态 C2+ 结果，则不能作为 Phase_2 production 修复。",
        "- 后续若补全高阶闭合或切换 D2Q37，必须重新运行 P2-4/P2-5/P2-7 鲁棒性复核。",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/gas_air_10k_physical_timestep.yaml")
    parser.add_argument("--out-root", default="results/phase2_high_mode_sensitivity")
    parser.add_argument("--report-out", default="docs/Phase_2/Phase2_High_Mode_Sensitivity_Report.md")
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_root) / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    config = load_config(config_path)
    diagnostic = run_high_mode_sensitivity(config)
    summary = {
        "phase": "Phase_2",
        "run_id": timestamp,
        "timestamp": timestamp,
        "command": [sys.executable, "-m", "scripts.diagnose_phase2_high_mode_sensitivity", *sys.argv[1:]],
        "config": str(config_path),
        "config_sha256": sha256_file(config_path),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "production_physics_status": "NOT_PASSED",
        "m2_decision": "GO-RISK / HIGH_MODE_SCALAR_RESCAN_FAILED",
        **_json_safe(diagnostic),
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
