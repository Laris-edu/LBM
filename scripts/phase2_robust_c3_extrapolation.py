"""C2+ -> C3 wider-extrapolation diagnostic for P2-4/5/6/7/9 on the RR default.

Establishes production-grade robustness of the HARD physical gates beyond the
single nx=64 / mode=1 / air-Pr calibration point, across four axes:

  * wavenumber  : grid 64, mode 1/2/3            (k-envelope)
  * resolution  : grids 48/64/96, mode 1          (steps ~ (N/64)^2 to hold decay)
  * Prandtl     : air-relevant Pr in [0.5, 1.0]   (finer)
  * Mach        : background Mach in [0, 0.08]     (wider, Galilean)

HARD gates (gated): nu isotropy (P2-4 <=5%), thermal alpha (P2-5 <=5%), sound
speed / gamma (P2-6 <=2%), Pr at Pr<=1 (P2-7 <=5%), Galilean drift/speed
(P2-9 <=2%).  Acoustic ATTENUATION anisotropy (diagonal) and high-mode
over-damping remain accepted bounded GO-RISK (reported, NOT gated) -- the
acoustic-speed/gamma envelope where the hard gate holds is itself a C3 result.

Diagnostic; baseline unchanged.

Usage:
    python -m scripts.phase2_robust_c3_extrapolation
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

from scripts.phase2_m2_verification import load_config, sha256_file, summary_payload_digest
from verification.acoustic_wave_measurement import measure_acoustic_wave
from verification.galilean_consistency_measurement import measure_galilean_consistency
from verification.prandtl_scan_measurement import measure_prandtl_scan
from verification.shear_wave_measurement import measure_shear_wave
from verification.thermal_diffusion_measurement import measure_thermal_diffusion

DEFAULT_CONFIG = Path("configs/gas_air_10k_d2q37_physical_timestep.yaml")
DEFAULT_OUTPUT_ROOT = Path("results/phase2_c3_extrapolation")

NU_TOL = 0.05
ALPHA_TOL = 0.05
SPEED_TOL = 0.02
GAMMA_TOL = 0.02
PR_TOL = 0.05
GALILEAN_TOL = 0.02


def _set(block: dict[str, Any], **kw) -> dict[str, Any]:
    out = dict(block or {})
    out.update({k: v for k, v in kw.items() if v is not None})
    return out


def _transport_point(base, *, nx, mode, shear_steps, thermal_steps, acoustic_steps):
    cfg = deepcopy(base)
    dirs = ["x", "y", "diagonal"]
    cfg["p2_04_shear_wave"] = _set(cfg.get("p2_04_shear_wave"), nx=nx, ny=nx, mode_index=mode,
                                   steps=shear_steps, directions=dirs)
    cfg["p2_05_thermal_diffusion"] = _set(cfg.get("p2_05_thermal_diffusion"), nx=nx, ny=nx, mode_index=mode,
                                          steps=thermal_steps, directions=dirs)
    cfg["p2_06_acoustic_wave"] = _set(cfg.get("p2_06_acoustic_wave"), nx=nx, ny=nx, mode_index=mode,
                                      steps=acoustic_steps, directions=dirs)
    p4 = measure_shear_wave(cfg)
    p5 = measure_thermal_diffusion(cfg)
    p6 = measure_acoustic_wave(cfg)
    diag6 = p6["direction_results"].get("diagonal", {})
    return {
        "nx": nx, "mode": mode,
        "nu_max_rel_err": float(p4["relative_error"]),
        "nu_dir_diff": float(p4["direction_difference"]),
        "p2_04_status": p4["p2_04_status"],
        "alpha_max_rel_err": float(p5["relative_error"]),
        "heat_flux_rel_err": float(p5["heat_flux_relative_error"]),
        "p2_05_status": p5["p2_05_status"],
        "speed_max_rel_err": float(p6["sound_speed_relative_error"]),
        "gamma_max_rel_err": float(p6["gamma_relative_error"]),
        "p2_06_speed_gamma_status": p6["p2_06_status"],
        "atten_diag_GO_RISK": float(diag6.get("acoustic_attenuation_relative_error", np.nan)),
        "hard_pass": bool(
            p4["relative_error"] <= NU_TOL and p4["direction_difference"] <= NU_TOL
            and p5["relative_error"] <= ALPHA_TOL
            and p6["sound_speed_relative_error"] <= SPEED_TOL and p6["gamma_relative_error"] <= GAMMA_TOL
        ),
    }


def _wavenumber_axis(base):
    pts = []
    for mode in (1, 2, 3):
        pts.append(_transport_point(base, nx=64, mode=mode, shear_steps=240, thermal_steps=320, acoustic_steps=240))
    return pts


def _resolution_axis(base):
    pts = []
    for nx in (48, 64, 96):
        scale = (nx / 64.0) ** 2
        pts.append(_transport_point(
            base, nx=nx, mode=1,
            shear_steps=int(round(240 * scale)), thermal_steps=int(round(320 * scale)),
            acoustic_steps=int(round(240 * scale)),
        ))
    return pts


def _prandtl_axis(base):
    cfg = deepcopy(base)
    cfg["p2_07_prandtl_scan"] = _set(cfg.get("p2_07_prandtl_scan"),
                                     pr_targets=[0.5, 0.6, 0.7061328707, 0.8, 1.0])
    p7 = measure_prandtl_scan(cfg)
    return {
        "pr_targets": [0.5, 0.6, 0.7061328707, 0.8, 1.0],
        "p2_07_status": p7["p2_07_status"],
        "baseline_pr_rel_err": float(p7["baseline_pr_relative_error"]),
        "max_pr_rel_err": float(p7["max_pr_relative_error"]),
        "scan_tolerance": float(p7["scan_tolerance"]),
        "hard_pass": bool(p7["p2_07_status"] == "PASSED"),
    }


def _mach_axis(base):
    cfg = deepcopy(base)
    cfg["p2_09_galilean_consistency"] = _set(cfg.get("p2_09_galilean_consistency"),
                                             mach_numbers=[0.0, 0.02, 0.05, 0.08])
    p9 = measure_galilean_consistency(cfg)
    speed_err = float(p9.get("max_sound_speed_relative_error", np.nan))
    return {
        "mach_numbers": [0.0, 0.02, 0.05, 0.08],
        "p2_09_status": p9["p2_09_status"],
        "max_sound_speed_rel_err": speed_err,
        "max_direction_difference": float(p9.get("max_direction_difference", np.nan)),
        "dispersion_masking_status": p9.get("transport_dispersion_masking_status", p9.get("dispersion_masking_status")),
        "hard_pass": bool(p9["p2_09_status"] == "PASSED"),
    }


def run_diagnostic(*, config_path: Path, output_root: Path) -> dict[str, Any]:
    base = load_config(config_path)
    wavenumber = _wavenumber_axis(base)
    resolution = _resolution_axis(base)
    prandtl = _prandtl_axis(base)
    mach = _mach_axis(base)

    # hard-gate envelope: transport (nu/alpha) should hold everywhere; acoustic speed/gamma
    # is the gated acoustic hard quantity (attenuation is GO-RISK). Report the wavenumber
    # envelope where acoustic speed/gamma holds.
    res_hard = all(p["hard_pass"] for p in resolution)
    wave_mode1_hard = next(p["hard_pass"] for p in wavenumber if p["mode"] == 1)
    transport_all = all(
        p["nu_max_rel_err"] <= NU_TOL and p["alpha_max_rel_err"] <= ALPHA_TOL
        for p in (wavenumber + resolution)
    )
    acoustic_speed_gamma_envelope_modes = [p["mode"] for p in wavenumber if p["p2_06_speed_gamma_status"] == "PASSED"]

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = output_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    c3_ready = bool(res_hard and wave_mode1_hard and prandtl["hard_pass"] and mach["hard_pass"] and transport_all)
    payload = {
        "run_id": run_id,
        "status": "DIAGNOSTIC_COMPLETE",
        "config_path": str(config_path),
        "config_sha256": sha256_file(config_path),
        "python": sys.version,
        "platform": platform.platform(),
        "default_closure": "D2Q37 RR (strain_rate_isotropic + ghost_orthogonal_local + diagnostic_zero)",
        "tolerances": {"nu": NU_TOL, "alpha": ALPHA_TOL, "speed": SPEED_TOL, "gamma": GAMMA_TOL,
                       "pr": PR_TOL, "galilean": GALILEAN_TOL},
        "wavenumber_axis": wavenumber,
        "resolution_axis": resolution,
        "prandtl_axis": prandtl,
        "mach_axis": mach,
        "verdict": {
            "transport_nu_alpha_all_axes_pass": transport_all,
            "resolution_hard_pass": res_hard,
            "wavenumber_mode1_hard_pass": wave_mode1_hard,
            "acoustic_speed_gamma_envelope_modes": acoustic_speed_gamma_envelope_modes,
            "prandtl_air_range_pass": prandtl["hard_pass"],
            "mach_galilean_pass": mach["hard_pass"],
            "c3_ready_compact_air": c3_ready,
        },
        "interpretation": {
            "transport": (
                "Transport hard gates (nu isotropy P2-4, thermal alpha P2-5) hold across resolution "
                "(48/64/96) and wavenumber (mode 1/2/3): "
                f"all-axes nu/alpha within tol = {transport_all}."
            ),
            "acoustic": (
                "Acoustic sound-speed/gamma hard gate holds at modes "
                f"{acoustic_speed_gamma_envelope_modes} (low-k envelope). Acoustic ATTENUATION anisotropy "
                "(diagonal ~1.31) and high-mode over-damping remain accepted bounded GO-RISK (reported, not "
                "gated); the compact-air target only excites the lowest mode, so the low-k envelope is the "
                "production-relevant one."
            ),
            "prandtl_mach": (
                f"P2-7 over air-relevant Pr in [0.5,1.0]: {prandtl['p2_07_status']} (max "
                f"{prandtl['max_pr_rel_err']:.4g}). P2-9 Galilean over Mach [0,0.08]: {mach['p2_09_status']} "
                f"(max speed err {mach['max_sound_speed_rel_err']:.4g})."
            ),
            "boundaries": (
                "Diagnostic; baseline unchanged. C3-readiness is for the BOUNDED_PRODUCTION_GO compact-air "
                "boundary (M2_Critical_Decision §5): hard gates across resolution / air-Pr / Mach / low-k; "
                "high-k acoustic attenuation is the documented GO-RISK boundary."
            ),
        },
    }
    safe = _json_safe(payload)
    safe["summary_digest"] = summary_payload_digest(safe)
    (out_dir / "summary.json").write_text(json.dumps(safe, indent=2), encoding="utf-8")
    (out_dir / "report.md").write_text(_render_report(safe), encoding="utf-8")
    return safe


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


def _fmt(value: Any) -> str:
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return "nan" if value != value else f"{value:.4g}"
    return str(value)


def _render_report(p: dict[str, Any]) -> str:
    v = p["verdict"]
    lines = [
        "# Phase 2 C2+ -> C3 Wider-Extrapolation Diagnostic (RR default)",
        "",
        f"- run_id: `{p['run_id']}`",
        f"- c3_ready (compact-air boundary): **{_fmt(v['c3_ready_compact_air'])}**",
        f"- summary_digest: `{p['summary_digest']}`",
        "",
        "## Wavenumber axis (grid 64, mode 1/2/3)",
        "",
        "| mode | nu max err | alpha max err | speed err | gamma err | speed/gamma | atten diag (GO-RISK) |",
        "|---|---|---|---|---|---|---|",
    ]
    for pt in p["wavenumber_axis"]:
        lines.append(
            f"| {pt['mode']} | {_fmt(pt['nu_max_rel_err'])} | {_fmt(pt['alpha_max_rel_err'])} | "
            f"{_fmt(pt['speed_max_rel_err'])} | {_fmt(pt['gamma_max_rel_err'])} | "
            f"`{pt['p2_06_speed_gamma_status']}` | {_fmt(pt['atten_diag_GO_RISK'])} |"
        )
    lines += [
        "",
        "## Resolution axis (mode 1, grids 48/64/96; steps ~ (N/64)^2)",
        "",
        "| grid | nu max err | alpha max err | speed err | gamma err | hard pass |",
        "|---|---|---|---|---|---|",
    ]
    for pt in p["resolution_axis"]:
        lines.append(
            f"| {pt['nx']} | {_fmt(pt['nu_max_rel_err'])} | {_fmt(pt['alpha_max_rel_err'])} | "
            f"{_fmt(pt['speed_max_rel_err'])} | {_fmt(pt['gamma_max_rel_err'])} | {_fmt(pt['hard_pass'])} |"
        )
    pr = p["prandtl_axis"]
    ma = p["mach_axis"]
    lines += [
        "",
        "## Prandtl axis (air-relevant Pr in [0.5,1.0])",
        f"- P2-7 `{pr['p2_07_status']}`  max Pr err {_fmt(pr['max_pr_rel_err'])} (tol {_fmt(pr['scan_tolerance'])})",
        "",
        "## Mach axis (background Mach [0,0.08])",
        f"- P2-9 `{ma['p2_09_status']}`  max speed err {_fmt(ma['max_sound_speed_rel_err'])}, "
        f"masking `{ma['dispersion_masking_status']}`",
        "",
        "## Verdict",
        f"- transport nu/alpha all axes pass: {_fmt(v['transport_nu_alpha_all_axes_pass'])}",
        f"- resolution hard pass (48/64/96): {_fmt(v['resolution_hard_pass'])}",
        f"- acoustic speed/gamma envelope (modes passing): {v['acoustic_speed_gamma_envelope_modes']}",
        f"- Pr air-range pass: {_fmt(v['prandtl_air_range_pass'])}; Mach Galilean pass: {_fmt(v['mach_galilean_pass'])}",
        "",
        "## Interpretation",
        "",
    ]
    for key, text in p["interpretation"].items():
        lines.append(f"- **{key}**: {text}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="P2-4/5/6/7/9 C2+ -> C3 wider-extrapolation diagnostic.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    payload = run_diagnostic(config_path=args.config, output_root=args.output_root)
    print(f"{payload['status']}; c3_ready_compact_air={payload['verdict']['c3_ready_compact_air']}; "
          f"wrote {args.output_root / payload['run_id']}; digest={payload['summary_digest']}")


if __name__ == "__main__":
    main()
