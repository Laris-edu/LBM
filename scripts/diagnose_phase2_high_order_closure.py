"""Diagnose D2Q21 fourth-order central-moment closure for Phase 2.

Usage:
    python -m scripts.diagnose_phase2_high_order_closure
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
from verification.high_order_closure_diagnostic import run_high_order_closure_diagnostic


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


def _table_rows(rows: list[dict]) -> list[str]:
    lines = []
    for row in rows:
        lines.append(
            "| "
            f"`{_format_value(row['high_order_relaxation'])}` | "
            f"`{row['status']}` | "
            f"`{_format_value(row['max_metric'])}` | "
            f"`{_format_value(row['shear_x_mode1_error'])}` | "
            f"`{_format_value(row['shear_x_mode2_error'])}` | "
            f"`{_format_value(row['shear_diagonal_mode1_error'])}` | "
            f"`{_format_value(row['shear_diagonal_mode2_error'])}` | "
            f"`{_format_value(row['thermal_mode1_alpha_error'])}` | "
            f"`{_format_value(row['thermal_mode1_heat_flux_error'])}` | "
            f"`{_format_value(row['thermal_mode2_alpha_error'])}` | "
            f"`{_format_value(row['thermal_mode2_heat_flux_error'])}` |"
        )
    return lines


def _write_report(summary: dict, report_path: Path) -> None:
    lines = [
        "# Phase_2 D2Q21 高阶闭合诊断报告",
        "",
        "本文档由 `python -m scripts.diagnose_phase2_high_order_closure` 生成。它只诊断 D2Q21 的 `central_moment_closure=fourth_order` 路径，不修改 D2Q21 production baseline，也不声明 final M2 production pass。",
        "",
        "## 结论",
        "",
        f"- run id：`{summary['run_id']}`",
        f"- 配置：`{summary['config']}`",
        "- central_moment_closure：`fourth_order`",
        f"- 扫描容差：`{_format_value(summary['tolerance'])}`",
        f"- 是否存在通过的高阶松弛参数：`{summary['joint_pass_exists']}`",
        f"- best_high_order_relaxation：`{_format_value(summary['best_high_order_relaxation'])}`",
        f"- best_max_metric：`{_format_value(summary['best_max_metric'])}`",
        "- 判读：显式四阶 central/binomial 高阶闭合未能在当前 D2Q21 physical-timestep baseline 下同时满足低模态和 mode=2 的剪切、热扩散与 Fourier-law 热流要求；满足 M2-Critical 分支条件，应启动 D2Q37 或等价九阶速度集路线。",
        "",
        "## 扫描结果",
        "",
        "| high_order_relaxation | status | max_metric | shear x m1 err | shear x m2 err | shear diag m1 err | shear diag m2 err | thermal m1 alpha err | thermal m1 q err | thermal m2 alpha err | thermal m2 q err |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
        *_table_rows(summary["rows"]),
        "",
        "## 判读口径",
        "",
        "- `status=FAILED` 表示至少一个低模态或 mode=2 指标超过 5% 容差。",
        "- 本诊断没有使用 clipping、distribution floor 或 positivity repair。",
        "- D2Q37 路线只替换 Phase_2 velocity-space quadrature 和相关矩测试，不返工 Phase_1，也不启动 Phase_3。",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/gas_air_10k_physical_timestep.yaml")
    parser.add_argument("--out-root", default="results/phase2_high_order_closure")
    parser.add_argument("--report-out", default="docs/Phase_2/Phase2_High_Order_Closure_Report.md")
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_root) / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    config = load_config(config_path)
    diagnostic = run_high_order_closure_diagnostic(config)
    summary = {
        "phase": "Phase_2",
        "run_id": timestamp,
        "timestamp": timestamp,
        "command": [sys.executable, "-m", "scripts.diagnose_phase2_high_order_closure", *sys.argv[1:]],
        "config": str(config_path),
        "config_sha256": sha256_file(config_path),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "production_physics_status": "NOT_PASSED",
        "m2_decision": "GO-RISK / D2Q21_HIGH_ORDER_CLOSURE_FAILED",
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
