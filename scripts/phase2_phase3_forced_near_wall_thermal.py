"""Phase_3 Level C: driven 10 kHz near-wall thermal-layer sim (gas-side proxy).

Definitive QoI-level check that the periodic free-mode caliber cannot give: drive a
wall-normal (y) thermal layer off a film at the production operating point and lock-in
the FORCED thermal admittance Y_LBM = q_g_hat / theta_wall_hat, then compare to the
analytic half-space value coeff_lu * m_T (m_T = sqrt(i Omega / alpha)).  Y_LBM is the
single quantity that sets all three Phase_3 QoI through the Level C closed form
(T_s_hat = P/(i Omega C_A + 2 k_g m_T); q_g = k_g m_T T_s; p_hat ~ T_s/m_T), so its
fidelity certifies T_s_hat / p_hat at the production discretization.

Design (no baseline change, pure diagnostic):
  * Run at the PRODUCTION config (dx, dt, tau) unchanged -> no dx/tau confound.  The
    closure's operating point is swept by FREQUENCY (k_thermal_LU = dx*sqrt(pi f/alpha)):
    the config f=10 kHz puts k_thermal ~ 0.15 (off the calibration k~0.098); a lower
    f puts it on the calibration k (clean) and validates the BC + lock-in.
  * Film at y=0 driven as an isobaric temperature wall theta_wall(t)=theta0(1+A cos(Omega t))
    (the standard linearized thermo-acoustic near-wall BC: the thermal layer is nearly
    isobaric since lambda_acoustic >> delta_T).  Periodic in y with L >= 16 delta_T so the
    film and its periodic image radiate two non-overlapping half-space thermal layers
    (the two-sided film of Phase_1 Level C).
  * Initialise from the analytic forced profile so the sim starts near steady-periodic,
    settle, then lock-in theta_wall and q_g over a whole period.

Usage:
    python -m scripts.phase2_phase3_forced_near_wall_thermal
    python -m scripts.phase2_phase3_forced_near_wall_thermal --frequencies 10000 4260
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
import time
from typing import Any

import numpy as np

from core.equilibrium import equilibrium_fg
from core.solver import GasSolver2D
from scripts.phase2_m2_verification import load_config, sha256_file, summary_payload_digest
from verification.thermal_diffusion_measurement import _fourier_heat_flux_coefficient_lu

DEFAULT_CONFIG = Path("configs/gas_air_10k_d2q37_physical_timestep.yaml")
DEFAULT_OUTPUT_ROOT = Path("results/phase2_forced_near_wall_thermal")
NX = 4
DELTA_T_DOMAIN_FACTOR = 16.0   # L >= 16 delta_T so film + periodic-image layers do not overlap
AMPLITUDE = 1.0e-3
SETTLE_PERIODS = 0.25          # init is the analytic forced profile, so little settling is needed
LOCKIN_PERIODS = 1.0
MAX_STEPS = 50000              # safety cap per frequency (~1.25 periods at 10 kHz)
WALL_CLOCK_CAP_S = 900.0       # hard self-abort per frequency so the run cannot hang for hours


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, complex):
        return {"real": value.real, "imag": value.imag, "abs": abs(value)}
    if isinstance(value, float) and np.isnan(value):
        return None
    return value


def _level_c_from_mT(m_t, *, omega, kg, c_a, p_hat, p0, t0, c0):
    k_a = omega / c0
    t_s = p_hat / (1j * omega * c_a + 2.0 * kg * m_t)
    q_g = kg * m_t * t_s
    p_probe = -1j * k_a * (p0 / t0) * t_s / m_t
    return {"T_s_hat": t_s, "q_g_hat": q_g, "p_hat_probe": p_probe}


def _drive_wall(solver: GasSolver2D, theta_wall: float, p0_lu: float) -> None:
    rho_w = np.full((1, solver.nx), p0_lu / theta_wall)
    u_w = np.zeros((1, solver.nx, 2))
    th_w = np.full((1, solver.nx), theta_wall)
    f_w, g_w = equilibrium_fg(rho_w, u_w, th_w, solver.mapping.lattice.S, solver.lattice)
    solver.f[0:1] = f_w
    solver.g[0:1] = g_w


def run_one_frequency(base: dict[str, Any], *, f_hz: float) -> dict[str, Any]:
    phys = base["physical"]
    alpha_si = float(phys["alpha0_m2_s"])
    dx = float(base["lattice"]["dx_m"])
    dt = float(base["lattice"]["dt_s"])
    omega_si = 2.0 * np.pi * f_hz
    omega_lu = omega_si * dt
    alpha_lu_phys = alpha_si * dt / (dx * dx)        # physical alpha in LU (target)
    delta_T_si = float(np.sqrt(alpha_si / (np.pi * f_hz)))
    delta_T_cells = delta_T_si / dx
    m_t_lu = np.sqrt(1j * omega_lu / alpha_lu_phys)  # analytic thermal wavenumber, LU (1/cell)
    k_thermal_lu = 1.0 / delta_T_cells

    ny = int(np.ceil(DELTA_T_DOMAIN_FACTOR * delta_T_cells / 2.0) * 2)
    period = 2.0 * np.pi / omega_lu
    settle = int(SETTLE_PERIODS * period)
    lockin = min(int(LOCKIN_PERIODS * period), MAX_STEPS - settle)

    cfg = deepcopy(base)
    cfg["numerics"] = {**base["numerics"], "nx": NX, "ny": ny}
    cfg["case"] = {**base.get("case", {}), "name": f"forced_near_wall_{int(f_hz)}"}
    solver = GasSolver2D(cfg)
    theta0 = float(solver.mapping.theta_ref_lu)
    p0_lu = float(solver.mapping.lattice.rho_ref_lu * theta0)
    coeff_lu = _fourier_heat_flux_coefficient_lu(solver)

    # analytic forced profile at t=0 (real part), isobaric
    y = np.arange(ny, dtype=float)
    theta_profile = theta0 * (1.0 + AMPLITUDE * np.real(np.exp(-m_t_lu * y)))
    theta_field = np.repeat(theta_profile[:, None], NX, axis=1)
    rho_field = p0_lu / theta_field
    solver.initialize_from_macro(rho_field, np.zeros((ny, NX, 2)), theta_field)

    nan_detected = False
    timed_out = False
    min_theta = np.inf
    t_start = time.perf_counter()
    # settle
    for step in range(settle):
        _drive_wall(solver, theta0 * (1.0 + AMPLITUDE * np.cos(omega_lu * step)), p0_lu)
        solver.step(1)
        if time.perf_counter() - t_start > WALL_CLOCK_CAP_S:
            timed_out = True
            break
    # lock-in over one period
    acc_wall = 0.0 + 0.0j
    acc_qg = 0.0 + 0.0j
    n_samp = 0
    qg_row = 1
    theta_amp = np.zeros(ny, dtype=complex)
    for j in range(lockin if not timed_out else 0):
        step = settle + j
        theta_wall = theta0 * (1.0 + AMPLITUDE * np.cos(omega_lu * step))
        _drive_wall(solver, theta_wall, p0_lu)
        solver.step(1)
        macro = solver.get_macro()
        if not np.isfinite(macro.theta).all():
            nan_detected = True
            break
        if time.perf_counter() - t_start > WALL_CLOCK_CAP_S:
            timed_out = True
            break
        min_theta = min(min_theta, float(macro.theta.min()))
        phase = np.exp(-1j * omega_lu * (step + 1))
        q_n = float(np.mean(solver.get_heat_flux_lu()[qg_row, :, 1]))
        theta_wall_resp = float(np.mean(macro.theta[0, :]))
        acc_wall += (theta_wall_resp - theta0) * phase
        acc_qg += q_n * phase
        theta_amp += (np.mean(macro.theta, axis=1) - theta0) * phase
        n_samp += 1

    norm = 2.0 / max(n_samp, 1)
    theta_wall_hat = acc_wall * norm
    qg_hat = acc_qg * norm
    theta_amp = theta_amp * norm

    y_lbm_lu = qg_hat / theta_wall_hat if abs(theta_wall_hat) > 0 else np.nan
    m_t_lbm_lu = y_lbm_lu / coeff_lu
    ratio = m_t_lbm_lu / m_t_lu                      # complex; deviation from 1 = admittance error
    # measured penetration depth from the lock-in amplitude profile (rows 1..8 delta_T)
    upper = max(int(8 * delta_T_cells), 6)
    yy = np.arange(1, min(upper, ny // 2))
    amp = np.abs(theta_amp[yy])
    good = amp > 0
    delta_T_lbm_cells = float(-1.0 / np.polyfit(yy[good], np.log(amp[good]), 1)[0]) if np.count_nonzero(good) >= 3 else np.nan

    omega_kwargs = {"omega": omega_si, "kg": float(phys["kg_W_mK"]), "c_a": 7.0e-4,
                    "p_hat": 1000.0, "p0": float(phys["p0_Pa"]), "t0": float(phys["T0_K"]),
                    "c0": float(phys["c0_m_s"])}
    m_t_si = np.sqrt(1j * omega_si / alpha_si)
    qoi_true = _level_c_from_mT(m_t_si, **omega_kwargs)
    qoi_lbm = _level_c_from_mT(ratio * m_t_si, **omega_kwargs)
    qoi_err = {k: float(abs(qoi_lbm[k] / qoi_true[k] - 1.0)) for k in qoi_true}

    return {
        "f_hz": f_hz,
        "ny": ny,
        "nx": NX,
        "delta_T_cells": float(delta_T_cells),
        "k_thermal_lu": float(k_thermal_lu),
        "k_thermal_x_cal": float(k_thermal_lu / (2.0 * np.pi / 64.0)),
        "settle_steps": settle,
        "lockin_steps": int(n_samp),
        "amplitude": AMPLITUDE,
        "m_T_analytic_lu": m_t_lu,
        "Y_LBM_lu": y_lbm_lu,
        "m_T_LBM_over_analytic": ratio,
        "admittance_abs_err": float(abs(abs(ratio) - 1.0)),
        "admittance_complex_err": float(abs(ratio - 1.0)),
        "delta_T_lbm_cells": delta_T_lbm_cells,
        "delta_T_lbm_over_analytic": float(delta_T_lbm_cells / delta_T_cells) if np.isfinite(delta_T_lbm_cells) else None,
        "qoi_rel_err_from_forced_admittance": qoi_err,
        "nan_detected": nan_detected,
        "timed_out": timed_out,
        "min_theta_lu": float(min_theta),
        "positivity_ok": bool(min_theta > 0.0 and not nan_detected),
        "complete": bool(not timed_out and not nan_detected and n_samp >= int(0.5 * lockin)),
    }


def run_diagnostic(*, config_path: Path, output_root: Path, frequencies: list[float]) -> dict[str, Any]:
    base = load_config(config_path)
    results = [run_one_frequency(base, f_hz=f) for f in frequencies]

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = output_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    config_result = next((r for r in results if abs(r["f_hz"] - 1.0e4) < 1.0), results[0])
    config_qoi = config_result["qoi_rel_err_from_forced_admittance"]
    # T_s_hat / p_hat certified at the production operating point if the forced admittance is accurate
    ts_certified = bool(config_qoi["T_s_hat"] < 0.05)
    p_certified = bool(config_qoi["p_hat_probe"] < 0.10)
    validation = next((r for r in results if 0.9 < r["k_thermal_x_cal"] < 1.1), None)

    payload = {
        "run_id": run_id,
        "status": "DIAGNOSTIC_COMPLETE",
        "config_path": str(config_path),
        "config_sha256": sha256_file(config_path),
        "python": sys.version,
        "platform": platform.platform(),
        "design": "driven isobaric-temperature film wall; forced thermal admittance Y=q_g/theta_wall by lock-in; "
                  "production dx/dt/tau unchanged, operating point swept by frequency (no tau confound)",
        "per_frequency": results,
        "verdict": {
            "config_operating_point_f_hz": 1.0e4,
            "config_k_thermal_x_cal": config_result["k_thermal_x_cal"],
            "config_forced_admittance_complex_err": config_result["admittance_complex_err"],
            "config_qoi_rel_err": config_qoi,
            "T_s_hat_certified_at_config_dx": ts_certified,
            "p_hat_certified_at_config_dx": p_certified,
            "validation_frequency_present": validation is not None,
            "validation_admittance_complex_err": (validation["admittance_complex_err"] if validation else None),
            "overall": (
                "Forced near-wall thermal-layer sim at the PRODUCTION config (dx/dt/tau unchanged). The forced "
                "thermal admittance Y=q_g/theta_wall sets T_s_hat/q_g/p_hat through the Level C closed form. "
                "Read config_forced_admittance_complex_err and config_qoi_rel_err: small (<5-10%) -> config dx "
                "certifies T_s_hat/p_hat (free-mode caliber was over-pessimistic for the forced response); large "
                "-> config dx is inadequate and the operating point must be moved onto the calibration k (lower "
                "the thermal feature wavenumber, e.g. dx~2.6um with the closure re-verified at the new tau, or "
                "re-tune the RR thermal dispersion). q_g in Level C is separately energy-pinned (~P/2)."
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
    if isinstance(value, dict) and {"real", "imag", "abs"} <= set(value):
        return f"{value['real']:.4g}{value['imag']:+.4g}j (|{value['abs']:.4g}|)"
    if isinstance(value, float):
        return "nan" if value != value else f"{value:.4g}"
    return str(value)


def _render_report(p: dict[str, Any]) -> str:
    v = p["verdict"]
    lines = [
        "# Phase_3 Level C: Forced Near-Wall Thermal-Layer Sim (gas-side proxy)",
        "",
        f"- run_id: `{p['run_id']}`",
        f"- T_s_hat certified at config dx: **{_fmt(v['T_s_hat_certified_at_config_dx'])}**",
        f"- p_hat certified at config dx: **{_fmt(v['p_hat_certified_at_config_dx'])}**",
        f"- summary_digest: `{p['summary_digest']}`",
        "",
        f"- design: {p['design']}",
        "",
        "## Forced thermal admittance per operating frequency (production dx/dt/tau)",
        "",
        "| f (Hz) | grid | delta_T cells | k_thermal (xcal) | lock-in steps | |m_T_LBM/m_T| | admittance err | delta_T_LBM/analytic | T_s err | q_g err | p_hat err | pos ok |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in p["per_frequency"]:
        q = r["qoi_rel_err_from_forced_admittance"]
        lines.append(
            f"| {_fmt(r['f_hz'])} | {r['nx']}x{r['ny']} | {_fmt(r['delta_T_cells'])} | "
            f"{_fmt(r['k_thermal_lu'])} ({_fmt(r['k_thermal_x_cal'])}x) | {r['lockin_steps']} | "
            f"{_fmt(r['m_T_LBM_over_analytic']['abs'])} | {_fmt(r['admittance_complex_err'])} | "
            f"{_fmt(r['delta_T_lbm_over_analytic'])} | {_fmt(q['T_s_hat'])} | {_fmt(q['q_g_hat'])} | "
            f"{_fmt(q['p_hat_probe'])} | {_fmt(r['positivity_ok'])} |"
        )
    lines += [
        "",
        "- The validation frequency (k_thermal ~ calibration k, ~1.0x) checks the BC + lock-in: its admittance "
        "error should be small if the setup is faithful.  The config point (10 kHz, k_thermal ~ 1.5x) is the test.",
        "",
        "## Verdict",
        "",
        f"**{v['overall']}**",
        "",
        f"- config operating point: f={_fmt(v['config_operating_point_f_hz'])} Hz, "
        f"k_thermal={_fmt(v['config_k_thermal_x_cal'])}x cal, forced admittance complex err "
        f"**{_fmt(v['config_forced_admittance_complex_err'])}**",
        f"- config QoI rel err (from forced admittance): T_s_hat {_fmt(v['config_qoi_rel_err']['T_s_hat'])}, "
        f"q_g {_fmt(v['config_qoi_rel_err']['q_g_hat'])}, p_hat {_fmt(v['config_qoi_rel_err']['p_hat_probe'])}",
        f"- validation admittance err (calibration-k operating point): {_fmt(v['validation_admittance_complex_err'])}",
        "",
        "Diagnostic; baseline, gates and closure unchanged.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase_3 Level C forced near-wall thermal-layer sim.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    # Default: config operating point only (~1.25 periods, a few minutes). Add the
    # calibration-k validation point explicitly, e.g. --frequencies 10000 4260, when
    # you can afford the longer (lower-frequency) period.
    parser.add_argument("--frequencies", type=float, nargs="+", default=[1.0e4])
    args = parser.parse_args()
    payload = run_diagnostic(config_path=args.config, output_root=args.output_root, frequencies=args.frequencies)
    v = payload["verdict"]
    print(f"{payload['status']}; config_admittance_err={v['config_forced_admittance_complex_err']:.4g}; "
          f"T_s_certified={v['T_s_hat_certified_at_config_dx']}; p_hat_certified={v['p_hat_certified_at_config_dx']}; "
          f"wrote {args.output_root / payload['run_id']}; digest={payload['summary_digest']}")


if __name__ == "__main__":
    main()
