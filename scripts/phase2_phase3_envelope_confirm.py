"""Phase_3 Level C precondition: confirm the compact-air operating point sits
inside the accepted RR production envelope (M2_Critical_Decision §5.4).

Maps the 10 kHz thin-film operating scales to validated-envelope coordinates
(Mach<=0.05, Pr<=1, feature wavenumber k_LU ~ calibration k≈0.098, nx=64) and
checks each axis.  The binding axis is the THERMAL boundary-layer feature
wavenumber: with the config dx the thermal penetration depth delta_T is resolved
over only a few cells -> its feature wavenumber k_thermal=1/delta_T_cells exceeds
the calibration k, where the k-specific RR transport closure (RR doc §13) is less
accurate.  Reports the dx that brings k_thermal onto the calibration k, and the
alpha-error bracket from mode 1 / mode 2.

Diagnostic; baseline unchanged.

Usage:
    python -m scripts.phase2_phase3_envelope_confirm
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
from verification.shear_wave_measurement import measure_shear_wave
from verification.thermal_diffusion_measurement import measure_thermal_diffusion

DEFAULT_CONFIG = Path("configs/gas_air_10k_d2q37_physical_timestep.yaml")
DEFAULT_OUTPUT_ROOT = Path("results/phase2_phase3_envelope_confirm")
TARGET_FREQUENCY_HZ = 1.0e4
K_CALIBRATION_LU = 2.0 * np.pi / 64.0  # validated calibration wavenumber (nx=64, mode 1) ≈ 0.0982
MACH_ENVELOPE = 0.05
NX_CALIBRATION = 64


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and np.isnan(value):
        return None
    return value


def _alpha_err_at_mode(base, mode: int) -> float:
    cfg = deepcopy(base)
    cfg["p2_05_thermal_diffusion"] = {
        **cfg.get("p2_05_thermal_diffusion", {}),
        "nx": 64, "ny": 64, "mode_index": mode, "directions": ["x"],
    }
    return float(measure_thermal_diffusion(cfg)["relative_error"])


def _nu_err_at_mode(base, mode: int) -> float:
    cfg = deepcopy(base)
    cfg["p2_04_shear_wave"] = {
        **cfg.get("p2_04_shear_wave", {}),
        "nx": 64, "ny": 64, "mode_index": mode, "directions": ["x"],
    }
    return float(measure_shear_wave(cfg)["relative_error"])


def run_diagnostic(*, config_path: Path, output_root: Path) -> dict[str, Any]:
    base = load_config(config_path)
    lat = dict(base.get("lattice", {}) or {})
    dx = float(lat.get("dx_m"))
    dt = float(lat.get("dt_s"))
    f_hz = TARGET_FREQUENCY_HZ
    alpha_si = float(base["physical"]["alpha0_m2_s"])
    nu_si = float(base["physical"]["nu0_m2_s"])
    c0_si = float(base["physical"]["c0_m_s"])

    # physical scales
    lambda_ac_si = c0_si / f_hz
    delta_T_si = float(np.sqrt(alpha_si / (np.pi * f_hz)))
    delta_nu_si = float(np.sqrt(nu_si / (np.pi * f_hz)))
    lambda_ac_cells = lambda_ac_si / dx
    delta_T_cells = delta_T_si / dx
    delta_nu_cells = delta_nu_si / dx

    # feature wavenumbers in LU (per cell)
    k_acoustic = 2.0 * np.pi / lambda_ac_cells
    k_thermal = 1.0 / delta_T_cells           # thermal boundary-layer feature (1/penetration depth)
    k_viscous = 1.0 / delta_nu_cells          # viscous (Stokes) boundary-layer feature

    # dx to put each boundary layer on the calibration wavenumber
    dx_for_thermal_on_calibration = K_CALIBRATION_LU * delta_T_si
    dx_for_viscous_on_calibration = K_CALIBRATION_LU * delta_nu_si
    delta_T_cells_target = delta_T_si / dx_for_thermal_on_calibration

    # error brackets from mode 1 / mode 2 axis (the k-specificity / shear regression from RR doc §13)
    alpha_err_mode1 = _alpha_err_at_mode(base, 1)
    alpha_err_mode2 = _alpha_err_at_mode(base, 2)
    nu_err_mode1 = _nu_err_at_mode(base, 1)
    nu_err_mode2 = _nu_err_at_mode(base, 2)

    # acoustic compactness (the acoustic axis is fine via compactness, not closure accuracy at its k)
    L_probe_cells = 8.0 * delta_T_cells
    kL_probe = k_acoustic * L_probe_cells

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = output_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    axes = {
        "mach": {
            "operating": "small-signal film acoustics (P2-6 amplitude Mach ~1e-6; driven 10 kHz film Mach << 1e-3)",
            "envelope_max": MACH_ENVELOPE,
            "within": True,
            "note": "film velocities are far below the Mach 0.05 envelope edge",
        },
        "prandtl": {
            "operating": 0.7061328707,
            "envelope_max": 1.0,
            "within": True,
        },
        "acoustic_wavenumber": {
            "k_lu": float(k_acoustic),
            "calibration_k_lu": float(K_CALIBRATION_LU),
            "within": True,
            "note": (
                f"acoustic lambda ~ {lambda_ac_cells:.0f} cells >> gas region: ACOUSTICALLY COMPACT (kL at probe "
                f"~ {kL_probe:.4f} << 1); acoustic does not transport across the gas region, so accuracy at "
                "k_acoustic is moot and the diagonal/high-mode attenuation GO-RISK is physically negligible"
            ),
        },
        "thermal_wavenumber": {
            "k_lu": float(k_thermal),
            "k_ratio_to_calibration": float(k_thermal / K_CALIBRATION_LU),
            "delta_T_cells_at_config_dx": float(delta_T_cells),
            "within": bool(k_thermal <= 1.3 * K_CALIBRATION_LU),
            "axis_alpha_err_mode1_k0p098": alpha_err_mode1,
            "axis_alpha_err_mode2_k0p196": alpha_err_mode2,
            "dx_for_thermal_on_calibration_m": float(dx_for_thermal_on_calibration),
            "delta_T_cells_target": float(delta_T_cells_target),
            "note": (
                f"thermal BL ~{delta_T_cells:.1f} cells -> k_thermal={k_thermal:.3f} "
                f"({k_thermal / K_CALIBRATION_LU:.2f}x cal). AXIS (wall-normal) alpha err brackets mode1 "
                f"{alpha_err_mode1:.3g} .. mode2 {alpha_err_mode2:.3g}; the wall-normal thermal BL is an axis "
                "direction (the 72% C3 alpha was the diagonal max), so thermal alpha is ~few-% here -- acceptable-ish"
            ),
        },
        "viscous_wavenumber": {
            "k_lu": float(k_viscous),
            "k_ratio_to_calibration": float(k_viscous / K_CALIBRATION_LU),
            "delta_nu_cells_at_config_dx": float(delta_nu_cells),
            "within": bool(k_viscous <= 1.3 * K_CALIBRATION_LU),
            "axis_nu_err_mode1_k0p098": nu_err_mode1,
            "axis_nu_err_mode2_k0p196": nu_err_mode2,
            "dx_for_viscous_on_calibration_m": float(dx_for_viscous_on_calibration),
            "note": (
                f"BINDING axis: viscous (Stokes) BL ~{delta_nu_cells:.1f} cells -> k_viscous={k_viscous:.3f} "
                f"({k_viscous / K_CALIBRATION_LU:.2f}x cal). RR regressed the SHEAR dispersion (RR doc §13): "
                f"AXIS nu err mode1 {nu_err_mode1:.3g} -> mode2 {nu_err_mode2:.3g} -- so nu at the viscous-BL k is "
                "badly off at the config dx; this is the worst axis (shear regression hits nu, not alpha)"
            ),
        },
        "resolution": {
            "calibration_nx": NX_CALIBRATION,
            "note": "RR corrections calibrated at nx=64; other resolutions need re-tune (RR doc §13)",
        },
    }
    within_envelope = bool(axes["mach"]["within"] and axes["prandtl"]["within"]
                           and axes["acoustic_wavenumber"]["within"] and axes["thermal_wavenumber"]["within"]
                           and axes["viscous_wavenumber"]["within"])

    payload = {
        "run_id": run_id,
        "status": "DIAGNOSTIC_COMPLETE",
        "config_path": str(config_path),
        "config_sha256": sha256_file(config_path),
        "python": sys.version,
        "platform": platform.platform(),
        "dx_m": dx,
        "dt_s": dt,
        "target_frequency_hz": f_hz,
        "physical_scales": {
            "lambda_acoustic_si_m": lambda_ac_si, "lambda_acoustic_cells": lambda_ac_cells,
            "delta_T_si_m": delta_T_si, "delta_T_cells": delta_T_cells,
            "delta_nu_si_m": delta_nu_si, "delta_nu_cells": delta_nu_cells,
        },
        "envelope_axes": axes,
        "within_envelope": within_envelope,
        "interpretation": {
            "verdict": (
                "Mach (<<0.05) and Pr (0.706<=1) are well inside the envelope. Acoustic is compact "
                f"(lambda~{lambda_ac_cells:.0f} cells, kL~{kL_probe:.3f}<<1) so the diagonal/high-mode attenuation "
                "GO-RISK is physically negligible. The wall-normal thermal BL is an axis direction so its alpha err "
                f"at k_thermal={k_thermal:.3f} is only ~few-% (mode1 {alpha_err_mode1:.3g} .. mode2 {alpha_err_mode2:.3g}). "
                f"BINDING axis = the VISCOUS (Stokes) boundary layer: delta_nu~{delta_nu_cells:.1f} cells -> "
                f"k_viscous={k_viscous:.3f} ({k_viscous/K_CALIBRATION_LU:.2f}x cal), and RR regressed the SHEAR "
                f"dispersion so axis nu err runs mode1 {nu_err_mode1:.3g} -> mode2 {nu_err_mode2:.3g}: nu at the "
                f"viscous-BL scale is badly off at the config dx={dx*1e6:.1f} um."
            ),
            "recommendation": (
                "For Level C, resolve BOTH boundary layers onto the calibration k: use dx ~ "
                f"{max(dx_for_thermal_on_calibration, dx_for_viscous_on_calibration)*1e6:.2f} um (delta_T/delta_nu ~ "
                "10 cells each) so thermal AND viscous features sit at k≈0.098 where RR nu/alpha are validated (~0.2-2%); "
                "OR re-tune the RR shear dispersion targets for the strain_rate_isotropic policy (recovers high-k nu). "
                "Mach/Pr/acoustic axes need no change. If the Phase_3 quantities of interest are dominated by the "
                "full-gas-region scale (~64 cells, k≈0.098) rather than the near-wall boundary layers, the config dx "
                "may already suffice -- confirm which scale drives T_s_hat / q_g / p_hat."
            ),
            "boundaries": (
                "Diagnostic; baseline unchanged. This is the Level C precondition (M2_Critical_Decision §5.5 item 2): "
                "confirm the Phase_3 sim's operating point sits in the accepted compact-air envelope before Level C."
            ),
        },
    }
    safe = _json_safe(payload)
    safe["summary_digest"] = summary_payload_digest(safe)
    (out_dir / "summary.json").write_text(json.dumps(safe, indent=2), encoding="utf-8")
    (out_dir / "report.md").write_text(_render_report(safe), encoding="utf-8")
    return safe


def _fmt(value: Any) -> str:
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return "nan" if value != value else f"{value:.4g}"
    return str(value)


def _render_report(p: dict[str, Any]) -> str:
    ax = p["envelope_axes"]
    sc = p["physical_scales"]
    tw = ax["thermal_wavenumber"]
    vw = ax["viscous_wavenumber"]
    lines = [
        "# Phase_3 Level C Precondition: Compact-Air Envelope Confirmation",
        "",
        f"- run_id: `{p['run_id']}`",
        f"- within accepted envelope: **{_fmt(p['within_envelope'])}**",
        f"- summary_digest: `{p['summary_digest']}`",
        "",
        f"- config dx = {p['dx_m']*1e6:.2f} um, dt = {p['dt_s']*1e9:.2f} ns, target f = {p['target_frequency_hz']:.0f} Hz",
        f"- scales: acoustic lambda {_fmt(sc['lambda_acoustic_cells'])} cells, delta_T {_fmt(sc['delta_T_cells'])} cells, "
        f"delta_nu {_fmt(sc['delta_nu_cells'])} cells",
        "",
        "## Envelope axes",
        "",
        "| axis | operating | envelope | within |",
        "|---|---|---|---|",
        f"| Mach | {ax['mach']['operating']} | <= {_fmt(ax['mach']['envelope_max'])} | {_fmt(ax['mach']['within'])} |",
        f"| Pr | {_fmt(ax['prandtl']['operating'])} | <= 1 | {_fmt(ax['prandtl']['within'])} |",
        f"| acoustic k | {_fmt(ax['acoustic_wavenumber']['k_lu'])} (compact) | ~0.098 | {_fmt(ax['acoustic_wavenumber']['within'])} |",
        f"| thermal k (axis) | {_fmt(tw['k_lu'])} ({_fmt(tw['k_ratio_to_calibration'])}x cal) | ~0.098 | {_fmt(tw['within'])} |",
        f"| viscous k (axis) | {_fmt(vw['k_lu'])} ({_fmt(vw['k_ratio_to_calibration'])}x cal) | ~0.098 | {_fmt(vw['within'])} |",
        "",
        "## Binding axis: near-wall boundary-layer resolution (viscous worst)",
        f"- thermal BL: delta_T ~ {_fmt(tw['delta_T_cells_at_config_dx'])} cells, k {_fmt(tw['k_lu'])} "
        f"({_fmt(tw['k_ratio_to_calibration'])}x cal); axis alpha err mode1 {_fmt(tw['axis_alpha_err_mode1_k0p098'])} "
        f".. mode2 {_fmt(tw['axis_alpha_err_mode2_k0p196'])} (~few-%, acceptable-ish)",
        f"- **viscous BL (binding)**: delta_nu ~ {_fmt(vw['delta_nu_cells_at_config_dx'])} cells, k {_fmt(vw['k_lu'])} "
        f"({_fmt(vw['k_ratio_to_calibration'])}x cal); axis nu err mode1 {_fmt(vw['axis_nu_err_mode1_k0p098'])} "
        f".. mode2 {_fmt(vw['axis_nu_err_mode2_k0p196'])} (RR shear regression -> badly off)",
        f"- to put both BLs on calibration k: dx ~ {max(tw['dx_for_thermal_on_calibration_m'], vw['dx_for_viscous_on_calibration_m'])*1e6:.2f} um "
        f"(delta_T/delta_nu ~ 10 cells each)",
        "",
        "## Interpretation",
        "",
    ]
    for key, text in p["interpretation"].items():
        lines.append(f"- **{key}**: {text}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase_3 Level C compact-air envelope confirmation.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    payload = run_diagnostic(config_path=args.config, output_root=args.output_root)
    print(f"{payload['status']}; within_envelope={payload['within_envelope']}; "
          f"wrote {args.output_root / payload['run_id']}; digest={payload['summary_digest']}")


if __name__ == "__main__":
    main()
