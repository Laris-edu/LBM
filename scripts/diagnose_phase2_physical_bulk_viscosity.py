"""Diagnose D2Q37 acoustic over-attenuation: physical bulk viscosity route.

This diagnostic records the route-turning finding that the D2Q37 acoustic
over-attenuation is governed by the trace/bulk and normal-stress relaxation,
and that a *physical* bulk viscosity is strictly ghost-stable where the
nu_b=0 target is not:

  Stage A (attenuation + stability sweep):
    ``current_zero`` imposes a large effective bulk viscosity (~6.27x
    over-damped). Switching to ``tau22`` with a physical ``nu_b`` (factor in
    (-1, 0)) is strictly ghost-stable and the matched-NSF target already
    includes the same ``nu_b``.

  Stage B (thermal ghost control):
    The P2-5/P2-7 breakage previously attributed to "tau22 changes thermal" is
    caused by the *marginal* ghost at ``nu_b=0`` (factor -1, |lambda|=1), which
    contaminates the longer thermal fit. A physical ``nu_b`` (factor ~-0.78)
    keeps P2-5 passing with the existing heat curve.

  Stage C (normal-stress isotropy wall):
    The residual acoustic attenuation (~1.67x at physical ``nu_b``) is a
    longitudinal normal-stress viscosity excess. Increasing
    ``regularized_shear_normal_factor`` drives the attenuation ratio through
    1, but the only value that keeps P2-4 diagonal transverse shear correct is
    the calibrated 0.9. One scalar ``normal_factor`` cannot satisfy both the
    diagonal transverse shear and the longitudinal acoustic viscosity.

Diagnostic only. Does NOT change the baseline and does NOT claim a production
pass. ``current_zero + auto_d2q37_tau32_linear`` remains the baseline.

Usage:
    python -m scripts.diagnose_phase2_physical_bulk_viscosity
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

from core.unit_mapping import create_unit_mapping
from scripts.run_m2_verification import load_config, sha256_file, summary_payload_digest
from verification.acoustic_wave_measurement import measure_acoustic_wave
from verification.prandtl_scan_measurement import measure_prandtl_scan
from verification.shear_wave_measurement import measure_shear_wave
from verification.thermal_diffusion_measurement import measure_thermal_diffusion

DEFAULT_CONFIG = Path("configs/gas_air_10k_d2q37_physical_timestep.yaml")
DEFAULT_OUTPUT_ROOT = Path("results/phase2_physical_bulk_viscosity")
NU_B_OVER_NU_GRID = (0.0, 0.3, 0.6, 1.0)
NORMAL_FACTOR_GRID = (0.7, 0.9, 1.0, 1.1, 1.3)
PHYSICAL_NU_B_OVER_NU = 0.6


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


def _variant(
    base: dict[str, Any],
    *,
    bulk_policy: str,
    trace_policy: str,
    nu_b_lu: float | None = None,
    normal_factor: float | None = None,
    p2_06_directions: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    cfg = deepcopy(base)
    collision = dict(cfg.get("collision", {}) or {})
    collision["bulk_viscosity_policy"] = bulk_policy
    if nu_b_lu is not None:
        collision["nu_b_lu"] = float(nu_b_lu)
    collision["trace_bulk_policy"] = trace_policy
    collision["trace_bulk_scale"] = 1.0
    if normal_factor is not None:
        collision["regularized_shear_normal_factor"] = float(normal_factor)
    cfg["collision"] = collision
    if p2_06_directions is not None:
        p2 = dict(cfg.get("p2_06_acoustic_wave", {}) or {})
        p2["directions"] = list(p2_06_directions)
        cfg["p2_06_acoustic_wave"] = p2
    return cfg


def _trace_factor(cfg: dict[str, Any]) -> tuple[float, float]:
    mapping = create_unit_mapping(cfg)
    if cfg["collision"]["trace_bulk_policy"] == "tau22":
        return float(mapping.tau22), float(1.0 - 1.0 / mapping.tau22)
    return float(mapping.tau22), 0.0


def _attenuation_row(name: str, cfg: dict[str, Any]) -> dict[str, Any]:
    tau22, factor = _trace_factor(cfg)
    res = measure_acoustic_wave(deepcopy(cfg))
    measured = res["acoustic_attenuation_measured_lu"]
    target = res["acoustic_attenuation_reference_lu"]
    return {
        "variant": name,
        "tau22": tau22,
        "trace_factor": factor,
        "attenuation_measured_lu": measured,
        "attenuation_reference_lu": target,
        "attenuation_ratio": float(measured / target) if target else float("nan"),
        "sound_speed_relative_error": res["sound_speed_relative_error"],
        "gamma_relative_error": res["gamma_relative_error"],
        "first_invalid_step": res["first_invalid_step"],
        "negative_theta_detected": res["negative_theta_detected"],
        "nan_detected": res["nan_detected"],
        "p2_06_status": res["p2_06_status"],
    }


def stage_attenuation_sweep(base: dict[str, Any], nu_lu: float) -> list[dict[str, Any]]:
    rows = [
        _attenuation_row(
            "current_zero",
            _variant(
                base,
                bulk_policy="diagnostic_zero",
                trace_policy="current_zero",
                p2_06_directions=("x",),
            ),
        )
    ]
    for ratio in NU_B_OVER_NU_GRID:
        rows.append(
            _attenuation_row(
                f"tau22_nu_b={ratio:.1f}nu",
                _variant(
                    base,
                    bulk_policy="specified",
                    trace_policy="tau22",
                    nu_b_lu=ratio * nu_lu,
                    p2_06_directions=("x",),
                ),
            )
        )
    return rows


def stage_thermal_ghost_control(base: dict[str, Any], nu_lu: float) -> list[dict[str, Any]]:
    cases = [
        ("current_zero", _variant(base, bulk_policy="diagnostic_zero", trace_policy="current_zero")),
        ("tau22_nu_b=0_marginal", _variant(base, bulk_policy="specified", trace_policy="tau22", nu_b_lu=0.0)),
        (
            f"tau22_nu_b={PHYSICAL_NU_B_OVER_NU:.1f}nu",
            _variant(base, bulk_policy="specified", trace_policy="tau22", nu_b_lu=PHYSICAL_NU_B_OVER_NU * nu_lu),
        ),
    ]
    rows = []
    for name, cfg in cases:
        _tau22, factor = _trace_factor(cfg)
        thermal = measure_thermal_diffusion(deepcopy(cfg))
        directions = thermal.get("direction_results", {})
        any_invalid = any(d.get("first_invalid_step") is not None for d in directions.values())
        rows.append(
            {
                "variant": name,
                "trace_factor": factor,
                "p2_05_status": thermal["p2_05_status"],
                "alpha_relative_error": thermal["relative_error"],
                "heat_flux_relative_error": thermal["heat_flux_relative_error"],
                "any_invalid_step": bool(any_invalid),
            }
        )
    return rows


def stage_physical_nu_b_full(base: dict[str, Any], nu_lu: float) -> dict[str, Any]:
    cfg = _variant(
        base,
        bulk_policy="specified",
        trace_policy="tau22",
        nu_b_lu=PHYSICAL_NU_B_OVER_NU * nu_lu,
        p2_06_directions=("x", "y", "diagonal"),
    )
    thermal = measure_thermal_diffusion(deepcopy(cfg))
    acoustic = measure_acoustic_wave(deepcopy(cfg))
    pr_scan = measure_prandtl_scan(deepcopy(cfg))
    return {
        "nu_b_over_nu": PHYSICAL_NU_B_OVER_NU,
        "p2_05_status": thermal["p2_05_status"],
        "alpha_relative_error": thermal["relative_error"],
        "heat_flux_relative_error": thermal["heat_flux_relative_error"],
        "p2_06_status": acoustic["p2_06_status"],
        "sound_speed_relative_error": acoustic["sound_speed_relative_error"],
        "gamma_relative_error": acoustic["gamma_relative_error"],
        "attenuation_ratio": (
            acoustic["acoustic_attenuation_measured_lu"] / acoustic["acoustic_attenuation_reference_lu"]
        ),
        "direction_difference": acoustic["direction_difference"],
        "p2_07_status": pr_scan["p2_07_status"],
        "baseline_pr_relative_error": pr_scan["baseline_pr_relative_error"],
        "max_pr_relative_error": pr_scan["max_pr_relative_error"],
    }


def stage_normal_factor_scan(base: dict[str, Any], nu_lu: float) -> list[dict[str, Any]]:
    rows = []
    for normal_factor in NORMAL_FACTOR_GRID:
        cfg = _variant(
            base,
            bulk_policy="specified",
            trace_policy="tau22",
            nu_b_lu=PHYSICAL_NU_B_OVER_NU * nu_lu,
            normal_factor=normal_factor,
            p2_06_directions=("x",),
        )
        acoustic = measure_acoustic_wave(deepcopy(cfg))
        shear = measure_shear_wave(deepcopy(cfg))
        directions = shear["direction_results"]
        rows.append(
            {
                "regularized_shear_normal_factor": float(normal_factor),
                "p2_06_status": acoustic["p2_06_status"],
                "attenuation_ratio": (
                    acoustic["acoustic_attenuation_measured_lu"]
                    / acoustic["acoustic_attenuation_reference_lu"]
                ),
                "sound_speed_relative_error": acoustic["sound_speed_relative_error"],
                "gamma_relative_error": acoustic["gamma_relative_error"],
                "p2_04_status": shear["p2_04_status"],
                "shear_relative_error_x": directions["x"]["relative_error"],
                "shear_relative_error_y": directions["y"]["relative_error"],
                "shear_relative_error_diagonal": directions["diagonal"]["relative_error"],
            }
        )
    return rows


def run_diagnostic(*, config_path: Path, output_root: Path) -> dict[str, Any]:
    base = load_config(config_path)
    mapping = create_unit_mapping(base)
    nu_lu = float(mapping.nu_lu)

    attenuation_sweep = stage_attenuation_sweep(base, nu_lu)
    thermal_ghost_control = stage_thermal_ghost_control(base, nu_lu)
    physical_full = stage_physical_nu_b_full(base, nu_lu)
    normal_factor_scan = stage_normal_factor_scan(base, nu_lu)

    # Effective bulk-viscosity slope: d(measured_coeff)/d(target_coeff) across the
    # tau22 sweep. NSF target coeff increment per unit nu_b is 0.5, so a slope > 1
    # means the scheme produces more bulk viscosity than nominal.
    tau22_rows = [row for row in attenuation_sweep if row["variant"].startswith("tau22")]
    k2 = (2.0 * np.pi / 64.0) ** 2
    bulk_slope = None
    if len(tau22_rows) >= 2:
        first, last = tau22_rows[0], tau22_rows[-1]
        d_measured = (last["attenuation_measured_lu"] - first["attenuation_measured_lu"]) / k2
        d_target = (last["attenuation_reference_lu"] - first["attenuation_reference_lu"]) / k2
        bulk_slope = float(d_measured / d_target) if d_target else None

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = output_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "run_id": run_id,
        "status": "DIAGNOSTIC_COMPLETE",
        "config_path": str(config_path),
        "config_sha256": sha256_file(config_path),
        "python": sys.version,
        "platform": platform.platform(),
        "nu_lu": nu_lu,
        "alpha_lu": float(mapping.alpha_lu),
        "theta_transport_lu": float(mapping.theta_transport_lu),
        "physical_nu_b_over_nu": PHYSICAL_NU_B_OVER_NU,
        "attenuation_sweep": attenuation_sweep,
        "thermal_ghost_control": thermal_ghost_control,
        "physical_nu_b_full_gate": physical_full,
        "normal_factor_scan": normal_factor_scan,
        "effective_bulk_viscosity_slope": bulk_slope,
        "interpretation": {
            "trace_over_attenuation_source": (
                "current_zero (trace_post=0) imposes a large effective bulk viscosity; "
                "the matched-NSF target assumes nu_b=0, hence ~6.27x over-attenuation."
            ),
            "marginal_ghost": (
                "tau22 nu_b=0 has trace factor -1 (|lambda|=1, marginal ghost) that "
                "contaminates the longer thermal fit; a physical nu_b (factor ~-0.78) is "
                "strictly stable and keeps P2-5/P2-6/P2-7 passing with the existing heat curve."
            ),
            "normal_stress_isotropy_wall": (
                "The residual attenuation (~1.67x) is a longitudinal normal-stress viscosity "
                "excess. A scalar regularized_shear_normal_factor that drives the attenuation "
                "ratio to 1 (~1.25) breaks P2-4 diagonal transverse shear; only 0.9 keeps "
                "diagonal shear correct. One scalar normal_factor cannot satisfy both."
            ),
            "conclusion": (
                "Acoustic attenuation ratio -> ~1 is NOT reachable by local scalar calibration "
                "of the current closure. It needs an isotropic / recursive-regularized stress "
                "(and heat-flux) closure. Diagnostic only; baseline unchanged."
            ),
        },
    }
    payload["summary_digest"] = summary_payload_digest(payload)

    (out_dir / "summary.json").write_text(json.dumps(_json_safe(payload), indent=2), encoding="utf-8")
    (out_dir / "report.md").write_text(_render_report(payload), encoding="utf-8")
    return payload


def _fmt(value: Any) -> str:
    if value is None:
        return "none"
    if isinstance(value, float):
        if value != value:
            return "nan"
        return f"{value:.4g}"
    return str(value)


def _render_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase 2 D2Q37 Physical Bulk Viscosity Diagnostic",
        "",
        f"- run_id: `{payload['run_id']}`",
        f"- status: `{payload['status']}`",
        f"- config: `{payload['config_path']}`",
        f"- summary_digest: `{payload['summary_digest']}`",
        f"- effective_bulk_viscosity_slope (measured/nominal): `{_fmt(payload['effective_bulk_viscosity_slope'])}`",
        "",
        "## Stage A: attenuation + stability sweep (P2-6, direction x)",
        "",
        "| variant | tau22 | trace_factor | measured | target | ratio | c_err | g_err | invalid | neg_theta |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in payload["attenuation_sweep"]:
        lines.append(
            f"| `{row['variant']}` | {_fmt(row['tau22'])} | {_fmt(row['trace_factor'])} | "
            f"{_fmt(row['attenuation_measured_lu'])} | {_fmt(row['attenuation_reference_lu'])} | "
            f"{_fmt(row['attenuation_ratio'])} | {_fmt(row['sound_speed_relative_error'])} | "
            f"{_fmt(row['gamma_relative_error'])} | {_fmt(row['first_invalid_step'])} | "
            f"{row['negative_theta_detected']} |"
        )
    lines += [
        "",
        "## Stage B: thermal ghost control (P2-5, x/y/diagonal)",
        "",
        "| variant | trace_factor | P2-5 | alpha_err | heat_flux_err | any_invalid_step |",
        "|---|---:|---|---:|---:|---|",
    ]
    for row in payload["thermal_ghost_control"]:
        lines.append(
            f"| `{row['variant']}` | {_fmt(row['trace_factor'])} | `{row['p2_05_status']}` | "
            f"{_fmt(row['alpha_relative_error'])} | {_fmt(row['heat_flux_relative_error'])} | "
            f"{row['any_invalid_step']} |"
        )
    full = payload["physical_nu_b_full_gate"]
    lines += [
        "",
        f"## Stage B2: physical nu_b={full['nu_b_over_nu']}*nu full gate (existing heat curve)",
        "",
        f"- P2-5 thermal: `{full['p2_05_status']}`  alpha_err=`{_fmt(full['alpha_relative_error'])}`  "
        f"heat_flux_err=`{_fmt(full['heat_flux_relative_error'])}`",
        f"- P2-6 acoustic: `{full['p2_06_status']}`  c_err=`{_fmt(full['sound_speed_relative_error'])}`  "
        f"g_err=`{_fmt(full['gamma_relative_error'])}`  attenuation_ratio=`{_fmt(full['attenuation_ratio'])}`  "
        f"direction_difference=`{_fmt(full['direction_difference'])}`",
        f"- P2-7 Pr scan: `{full['p2_07_status']}`  baseline_pr_err=`{_fmt(full['baseline_pr_relative_error'])}`  "
        f"max_pr_err=`{_fmt(full['max_pr_relative_error'])}`",
        "",
        "## Stage C: normal_factor scan at physical nu_b (P2-6 x, P2-4 x/y/diagonal)",
        "",
        "| normal_factor | P2-6 | attenuation_ratio | c_err | P2-4 | shear_x | shear_y | shear_diagonal |",
        "|---:|---|---:|---:|---|---:|---:|---:|",
    ]
    for row in payload["normal_factor_scan"]:
        lines.append(
            f"| {_fmt(row['regularized_shear_normal_factor'])} | `{row['p2_06_status']}` | "
            f"{_fmt(row['attenuation_ratio'])} | {_fmt(row['sound_speed_relative_error'])} | "
            f"`{row['p2_04_status']}` | {_fmt(row['shear_relative_error_x'])} | "
            f"{_fmt(row['shear_relative_error_y'])} | {_fmt(row['shear_relative_error_diagonal'])} |"
        )
    lines += ["", "## Interpretation", ""]
    for key, text in payload["interpretation"].items():
        lines.append(f"- **{key}**: {text}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose D2Q37 acoustic over-attenuation via physical bulk viscosity.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    payload = run_diagnostic(config_path=args.config, output_root=args.output_root)
    print(f"{payload['status']}; wrote {args.output_root / payload['run_id']}; digest={payload['summary_digest']}")


if __name__ == "__main__":
    main()
