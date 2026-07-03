"""汇总 Phase_3 M3 运行 summary 到 docs/Phase_3/M3/M3_Run_Summaries.md（生成型文档）。

扫描 Level C（results/m3）与 Level A/B 动态导纳（results/phase3_levela_admittance、
results/phase3_levelb_admittance）的 summary.json，按 run 生成一张证据总表。
本脚本只做只读聚合，不重算物理量；权威判读仍以 `docs/Phase_3/M3/M3_Verification_Report.md`
（手写）与 `Phase3_STATUS.md` §3 记录的 physics-core digest 为准。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_ROOTS = (
    "results/m3",
    "results/phase3_levela_admittance",
    "results/phase3_levelb_admittance",
)
DEFAULT_OUT = "docs/Phase_3/M3/M3_Run_Summaries.md"


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return "nan" if value != value else f"{value:.4g}"
    return str(value)


def _error_cells(data: dict[str, Any]) -> str:
    amp = data.get("amplitude_errors", {}) or {}
    phase = data.get("phase_errors_deg", {}) or {}
    parts = []
    for key in sorted(set(amp) | set(phase)):
        a = amp.get(key)
        p = phase.get(key)
        a_txt = f"{a:+.4f}" if isinstance(a, int | float) and a == a else "n/a"
        p_txt = f"{p:+.2f}deg" if isinstance(p, int | float) and p == p else "n/a"
        parts.append(f"{key}: {a_txt}/{p_txt}")
    return "; ".join(parts) if parts else "n/a"


def _energy_cell(data: dict[str, Any]) -> str:
    energy = data.get("energy_residual")
    if isinstance(energy, dict):
        if "max_relative" in energy:
            return _fmt(energy.get("max_relative"))
        if "note" in energy:
            return "n/a (see note)"
    if isinstance(energy, int | float):
        return _fmt(energy)
    return "n/a"


def collect_rows(roots: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for root in roots:
        for path in sorted(root.glob("*/summary.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            rows.append(
                {
                    "run_id": str(data.get("run_id", path.parent.name)),
                    "root": root.as_posix(),
                    "level": str(data.get("level", "?")),
                    "scope": str(data.get("scope", data.get("case", ""))) or "n/a",
                    "status": str(data.get("status", "n/a")),
                    "m3_gate": str(data.get("m3_gate", "NOT_CLAIMED")),
                    "wall_bc": str(data.get("wall_bc", "n/a")),
                    "errors": _error_cells(data),
                    "energy": _energy_cell(data),
                    "hdf5": _fmt(bool((data.get("artifacts") or {}).get("hdf5"))),
                    "digest": str(data.get("summary_digest", ""))[:12],
                }
            )
    return rows


def render(rows: list[dict[str, str]], roots: list[Path]) -> str:
    lines = [
        "# Phase_3 M3 运行汇总（生成型）",
        "",
        "本文档由 `python -m scripts.phase3_m3_summarize` 生成，只聚合本机 `results/` 下的",
        "run summary，不构成判定；M3 判读口径见 `M3_Verification_Report.md` 与",
        "`Phase3_STATUS.md` §3（physics-core digest 为验证锚点）。`results/` 不入库，",
        "重新生成前请先复跑对应脚本。",
        "",
        f"扫描根目录：{', '.join('`' + r.as_posix() + '`' for r in roots)}",
        "",
        "| run_id | 来源 | level | scope | status | m3_gate | wall_bc | 幅值/相位误差 | 能量残差 | HDF5 | digest(12) |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    if rows:
        for r in rows:
            lines.append(
                f"| `{r['run_id']}` | `{r['root']}` | {r['level']} | `{r['scope']}` | `{r['status']}` "
                f"| `{r['m3_gate']}` | `{r['wall_bc']}` | {r['errors']} | `{r['energy']}` "
                f"| {r['hdf5']} | `{r['digest']}` |"
            )
    else:
        lines.append("| n/a | n/a | n/a | n/a | not_run | n/a | n/a | n/a | n/a | n/a | n/a |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize Phase_3 M3 run summaries into a generated doc.")
    parser.add_argument("--results-roots", nargs="*", default=list(DEFAULT_ROOTS))
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    roots = [Path(r) for r in args.results_roots]
    rows = collect_rows(roots)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(rows, roots), encoding="utf-8")
    print(f"Wrote {out} ({len(rows)} runs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
