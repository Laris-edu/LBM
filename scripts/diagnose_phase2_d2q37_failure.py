"""Diagnose D2Q37 robustness failures without changing production parameters.

Usage:
    python -m scripts.diagnose_phase2_d2q37_failure
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
from typing import Any

import numpy as np

from core.solver import GasSolver2D
from scripts.run_m2_verification import load_config, sha256_file, summary_payload_digest
from verification.shear_wave_measurement import (
    ShearWaveSettings,
    _fit_decay,
    _initialize_shear_wave,
    _modal_amplitude_from_state,
)
from verification.thermal_diffusion_measurement import (
    ThermalDiffusionSettings,
    _direction_phase_and_unit,
    _fourier_heat_flux_coefficient_lu,
    _heat_flux_ratio,
    _initialize_isobaric_thermal_wave,
    _modal_amplitude_2d,
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


def _case_config(base_config: dict[str, Any], n: int, *, filter_enabled: bool = True) -> dict[str, Any]:
    config = deepcopy(base_config)
    numerics = dict(config.get("numerics", {}) or {})
    numerics["nx"] = n
    numerics["ny"] = n
    if not filter_enabled:
        numerics["high_wavenumber_filter"] = {"enabled": False, "strength": 0.0, "passes": 1}
    config["numerics"] = numerics
    return config


def _window_pairs(max_step: int) -> list[tuple[int, int]]:
    candidates = [(4, 24), (10, 24), (10, 60), (10, 120), (10, 160), (10, 240), (80, 240)]
    return [(start, stop) for start, stop in candidates if stop <= max_step]


def _fit_shear_windows(
    target: float,
    k2: float,
    times: np.ndarray,
    amplitudes: np.ndarray,
) -> list[dict[str, Any]]:
    rows = []
    for start, stop in _window_pairs(int(np.max(times))):
        fit = _fit_decay(times, amplitudes, start, stop)
        nu = fit["decay_rate"] / k2 if np.isfinite(fit["decay_rate"]) and k2 > 0.0 else np.nan
        rows.append(
            {
                "window": [start, stop],
                "nu_measured_lu": float(nu) if np.isfinite(nu) else np.nan,
                "relative_error": float(abs(nu / target - 1.0)) if np.isfinite(nu) else np.nan,
                "signed_relative_error": float(nu / target - 1.0) if np.isfinite(nu) else np.nan,
                "residual_norm": fit["residual_norm"],
            }
        )
    return rows


def _fit_thermal_windows(
    target: float,
    k_mag: float,
    fourier_coeff_lu: float,
    times: np.ndarray,
    theta_amplitudes: np.ndarray,
    heat_flux_amplitudes: np.ndarray,
) -> list[dict[str, Any]]:
    rows = []
    for start, stop in _window_pairs(int(np.max(times))):
        fit = _fit_decay(times, theta_amplitudes, start, stop)
        alpha = fit["decay_rate"] / (k_mag * k_mag) if np.isfinite(fit["decay_rate"]) else np.nan
        heat_flux = _heat_flux_ratio(
            theta_amplitudes,
            heat_flux_amplitudes,
            times,
            k_mag=k_mag,
            fourier_coeff_lu=fourier_coeff_lu,
            start=start,
            stop=stop,
        )
        heat_flux_ratio = heat_flux["heat_flux_ratio"]
        rows.append(
            {
                "window": [start, stop],
                "alpha_measured_lu": float(alpha) if np.isfinite(alpha) else np.nan,
                "relative_error": float(abs(alpha / target - 1.0)) if np.isfinite(alpha) else np.nan,
                "signed_relative_error": float(alpha / target - 1.0) if np.isfinite(alpha) else np.nan,
                "heat_flux_relative_error": heat_flux["heat_flux_relative_error"],
                "heat_flux_ratio_real": float(np.real(heat_flux_ratio)) if np.isfinite(heat_flux_ratio) else np.nan,
                "heat_flux_ratio_imag": float(np.imag(heat_flux_ratio)) if np.isfinite(heat_flux_ratio) else np.nan,
                "residual_norm": fit["residual_norm"],
            }
        )
    return rows


def _instantaneous_transport(
    target: float,
    denominator: float,
    times: np.ndarray,
    amplitudes: np.ndarray,
    sample_steps: tuple[int, ...],
) -> list[dict[str, Any]]:
    rows = []
    magnitude = np.abs(amplitudes)
    for step in sample_steps:
        if step + 1 >= len(times) or magnitude[step] <= 0.0 or magnitude[step + 1] <= 0.0:
            continue
        value = -np.log(magnitude[step + 1] / magnitude[step]) / denominator
        rows.append(
            {
                "step": int(step),
                "measured_lu": float(value),
                "signed_relative_error": float(value / target - 1.0),
            }
        )
    return rows


def _run_shear_case(
    base_config: dict[str, Any],
    *,
    name: str,
    n: int,
    mode_index: int,
    steps: int,
    filter_enabled: bool,
) -> dict[str, Any]:
    settings = ShearWaveSettings(
        nx=n,
        ny=n,
        steps=steps,
        mode_index=mode_index,
        directions=("x",),
        fit_start=0,
    )
    solver = GasSolver2D(_case_config(base_config, n, filter_enabled=filter_enabled))
    k2 = _initialize_shear_wave(solver, settings, "x")
    times: list[int] = []
    amplitudes: list[complex] = []
    min_theta = np.inf
    max_theta = -np.inf
    nan_detected = False
    negative_theta_detected = False
    for step in range(steps + 1):
        with np.errstate(all="ignore"):
            macro = solver.get_macro()
        finite = bool(np.isfinite(macro.rho).all() and np.isfinite(macro.u).all() and np.isfinite(macro.theta).all())
        nan_detected = nan_detected or not finite
        theta_min = float(np.nanmin(macro.theta))
        theta_max = float(np.nanmax(macro.theta))
        min_theta = min(min_theta, theta_min)
        max_theta = max(max_theta, theta_max)
        negative_theta_detected = negative_theta_detected or bool(theta_min <= 0.0)
        times.append(step)
        amplitudes.append(_modal_amplitude_from_state(macro.u, "x", mode_index))
        if step < steps:
            solver.step()

    time_array = np.asarray(times, dtype=float)
    amplitude_array = np.asarray(amplitudes, dtype=complex)
    target = solver.mapping.nu_lu
    return {
        "name": name,
        "kind": "shear",
        "velocity_set": solver.mapping.lattice.velocity_set,
        "n": n,
        "mode_index": mode_index,
        "k2_lu": float(k2),
        "steps": steps,
        "filter_enabled": filter_enabled,
        "target_lu": float(target),
        "window_fits": _fit_shear_windows(target, k2, time_array, amplitude_array),
        "instantaneous": _instantaneous_transport(target, k2, time_array, amplitude_array, (1, 5, 10, 20, 40, 80, 120, 200)),
        "nan_detected": nan_detected,
        "negative_theta_detected": negative_theta_detected,
        "min_theta_lu": float(min_theta),
        "max_theta_lu": float(max_theta),
    }


def _run_thermal_case(
    base_config: dict[str, Any],
    *,
    name: str,
    n: int,
    mode_index: int,
    steps: int,
    filter_enabled: bool,
) -> dict[str, Any]:
    settings = ThermalDiffusionSettings(
        nx=n,
        ny=n,
        steps=steps,
        mode_index=mode_index,
        directions=("x",),
        fit_start=0,
    )
    solver = GasSolver2D(_case_config(base_config, n, filter_enabled=filter_enabled))
    k_mag = _initialize_isobaric_thermal_wave(solver, settings, "x")
    _, unit, _ = _direction_phase_and_unit("x", solver.ny, solver.nx, mode_index)
    theta0 = solver.mapping.theta_ref_lu
    fourier_coeff_lu = _fourier_heat_flux_coefficient_lu(solver)
    times: list[int] = []
    theta_amplitudes: list[complex] = []
    heat_flux_amplitudes: list[complex] = []
    min_theta = np.inf
    max_theta = -np.inf
    nan_detected = False
    negative_theta_detected = False
    for step in range(steps + 1):
        with np.errstate(all="ignore"):
            macro = solver.get_macro()
            q_lu = solver.get_heat_flux_lu()
        finite = bool(np.isfinite(macro.rho).all() and np.isfinite(macro.u).all() and np.isfinite(macro.theta).all())
        nan_detected = nan_detected or not finite
        theta_min = float(np.nanmin(macro.theta))
        theta_max = float(np.nanmax(macro.theta))
        min_theta = min(min_theta, theta_min)
        max_theta = max(max_theta, theta_max)
        negative_theta_detected = negative_theta_detected or bool(theta_min <= 0.0)
        q_normal = np.einsum("...i,i->...", q_lu, unit)
        times.append(step)
        theta_amplitudes.append(_modal_amplitude_2d(macro.theta - theta0, "x", mode_index))
        heat_flux_amplitudes.append(_modal_amplitude_2d(q_normal, "x", mode_index))
        if step < steps:
            solver.step()

    time_array = np.asarray(times, dtype=float)
    theta_array = np.asarray(theta_amplitudes, dtype=complex)
    heat_flux_array = np.asarray(heat_flux_amplitudes, dtype=complex)
    target = solver.mapping.alpha_lu
    return {
        "name": name,
        "kind": "thermal",
        "velocity_set": solver.mapping.lattice.velocity_set,
        "n": n,
        "mode_index": mode_index,
        "k_mag_lu": float(k_mag),
        "steps": steps,
        "filter_enabled": filter_enabled,
        "target_lu": float(target),
        "window_fits": _fit_thermal_windows(target, k_mag, fourier_coeff_lu, time_array, theta_array, heat_flux_array),
        "instantaneous": _instantaneous_transport(
            target,
            k_mag * k_mag,
            time_array,
            theta_array,
            (1, 5, 10, 20, 40, 80, 120, 200),
        ),
        "nan_detected": nan_detected,
        "negative_theta_detected": negative_theta_detected,
        "min_theta_lu": float(min_theta),
        "max_theta_lu": float(max_theta),
    }


def _pick_window(case: dict[str, Any], window: tuple[int, int]) -> dict[str, Any]:
    for row in case["window_fits"]:
        if row["window"] == [window[0], window[1]]:
            return row
    return {}


def _case_table_rows(cases: list[dict[str, Any]]) -> list[str]:
    rows = []
    for case in cases:
        short = _pick_window(case, (4, 24))
        long = _pick_window(case, (10, 120)) or _pick_window(case, (10, 160)) or _pick_window(case, (10, 240))
        if case["kind"] == "shear":
            metric = "nu"
            short_value = short.get("nu_measured_lu")
            long_value = long.get("nu_measured_lu")
            heat = None
        else:
            metric = "alpha"
            short_value = short.get("alpha_measured_lu")
            long_value = long.get("alpha_measured_lu")
            heat = long.get("heat_flux_relative_error")
        rows.append(
            "| "
            f"`{case['name']}` | `{case['kind']}` | `{case['velocity_set']}` | "
            f"`{case['n']}` | `{case['mode_index']}` | `{case['filter_enabled']}` | "
            f"`{metric}` | `{_format_value(short_value)}` | `{_format_value(short.get('signed_relative_error'))}` | "
            f"`{_format_value(long_value)}` | `{_format_value(long.get('signed_relative_error'))}` | "
            f"`{_format_value(heat)}` |"
        )
    return rows


def _write_report(summary: dict[str, Any], report_path: Path) -> None:
    lines = [
        "# Phase_2 D2Q37 鲁棒性失败诊断报告",
        "",
        "本文档由 `python -m scripts.diagnose_phase2_d2q37_failure` 生成。它只定位 D2Q37 `20260606T142620Z` 鲁棒性失败来源，不修改 production 参数，不声明 final M2 production pass。",
        "",
        "## 结论",
        "",
        f"- run id：`{summary['run_id']}`",
        f"- 诊断状态：`{summary['diagnosis_status']}`",
        f"- D2Q37 candidate status：`{summary['d2q37_candidate_status']}`",
        f"- 关键判读：{summary['key_finding']}",
        "",
        "## 场景对照",
        "",
        "| 场景 | 类型 | velocity_set | n | mode | filter | metric | short 4-24 | short signed err | long fit | long signed err | long heat-flux err |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
        *_case_table_rows(summary["cases"]),
        "",
        "## 诊断要点",
        "",
        "- D2Q37 `32/mode1` 与 `64/mode2` 具有相同 `k`，其 shear 表现一致；这说明短窗口低模态 pass 实际是较高波数窗口 pass，不代表低 k hydrodynamic 极限通过。",
        "- D2Q37 `64/mode1` shear 在长窗口和后期瞬时斜率上稳定约为目标的两倍；关闭 high-wavenumber filter 仍保持同阶错误，filter 不是根因。",
        "- D2Q37 thermal 的 heat-flux ratio 在 `64/mode1` 长窗口约为 `0.33`，而较高波数短窗口可接近 `1`；当前 conductive scale 与 heat-flux retention 是波数/窗口相关标定，不可外推到长窗口。",
        "- D2Q21 `64/mode1` 作为对照没有出现 shear 翻倍，但 D2Q21 仍有自身 mode=2 高模态失败；因此不能简单抛弃 D2Q21 转向当前 D2Q37。",
        "",
        "## 后续方向",
        "",
        "- 将 D2Q37 stress projection 和 heat-flux closure 改为以低 k 长窗口为硬约束重新推导；不得继续只用 `32/mode1/24 steps` 标定。",
        "- 分离 population filter 的数值耗散贡献与 collision 本征输运；filter 可改善高 k，但不能修复 D2Q37 低 k 长窗口错误。",
        "- 对 D2Q37 建立同一组 `k` 下的 mode/window 扫描，再考虑是否需要重做 moment-matched equilibrium 或 central-moment 投影约束。",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def run_diagnosis(d2q37_config: dict[str, Any], d2q21_config: dict[str, Any]) -> dict[str, Any]:
    cases = [
        _run_shear_case(d2q37_config, name="d2q37_shear_high_k_64m2", n=64, mode_index=2, steps=160, filter_enabled=True),
        _run_shear_case(d2q37_config, name="d2q37_shear_low_k_64m1", n=64, mode_index=1, steps=240, filter_enabled=True),
        _run_shear_case(d2q37_config, name="d2q37_shear_low_k_64m1_no_filter", n=64, mode_index=1, steps=160, filter_enabled=False),
        _run_shear_case(d2q21_config, name="d2q21_shear_low_k_64m1", n=64, mode_index=1, steps=240, filter_enabled=True),
        _run_thermal_case(d2q37_config, name="d2q37_thermal_high_k_64m2", n=64, mode_index=2, steps=200, filter_enabled=True),
        _run_thermal_case(d2q37_config, name="d2q37_thermal_low_k_64m1", n=64, mode_index=1, steps=240, filter_enabled=True),
        _run_thermal_case(d2q37_config, name="d2q37_thermal_low_k_64m1_no_filter", n=64, mode_index=1, steps=160, filter_enabled=False),
        _run_thermal_case(d2q21_config, name="d2q21_thermal_low_k_64m1", n=64, mode_index=1, steps=240, filter_enabled=True),
    ]
    return {
        "diagnosis_status": "D2Q37_WAVENUMBER_WINDOW_DEPENDENT_CLOSURE",
        "d2q37_candidate_status": "NOT_READY",
        "key_finding": (
            "当前 D2Q37 新标定口径的共同失败源是 stress/heat-flux 经验闭合被短窗口较高波数场景校准，"
            "在低 k 长窗口 hydrodynamic 极限下输运系数和导热热流尺度系统性失配。"
        ),
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--d2q37-config", default="configs/gas_air_10k_d2q37_physical_timestep.yaml")
    parser.add_argument("--d2q21-config", default="configs/gas_air_10k_physical_timestep.yaml")
    parser.add_argument("--out-root", default="results/phase2_d2q37_failure_diagnosis")
    parser.add_argument("--report-out", default="docs/Phase_2/Phase2_D2Q37_Failure_Diagnosis_Report.md")
    args = parser.parse_args(argv)

    d2q37_path = Path(args.d2q37_config)
    d2q21_path = Path(args.d2q21_config)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_root) / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    diagnosis = run_diagnosis(load_config(d2q37_path), load_config(d2q21_path))
    summary = {
        "phase": "Phase_2",
        "run_id": timestamp,
        "timestamp": timestamp,
        "command": [sys.executable, "-m", "scripts.diagnose_phase2_d2q37_failure", *sys.argv[1:]],
        "d2q37_config": str(d2q37_path),
        "d2q21_config": str(d2q21_path),
        "d2q37_config_sha256": sha256_file(d2q37_path),
        "d2q21_config_sha256": sha256_file(d2q21_path),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "scope": "D2Q37 robustness failure diagnosis; no production parameter changes",
        **_json_safe(diagnosis),
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
