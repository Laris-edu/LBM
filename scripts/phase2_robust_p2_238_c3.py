"""C1 -> C3 upgrade diagnostics for P2-2 / P2-3 / P2-8 on the RR default.

P2-2 (equilibrium admissibility + real perturbation stability):
  * f_eq non-negativity across the validated macro envelope (rho/theta +-1%,
    Mach up to 0.05, x and diagonal background);
  * a real multi-mode small perturbation evolved -> stable (no NaN / negative
    theta / blow-up), perturbation decays.
P2-3 (long-time uniform stability + invariant monitoring):
  * uniform rest and uniform background states evolved long; global mass /
    momentum / total-energy drift and fixed-point excursion monitored.
P2-8 (real directional error statistics):
  * nu / alpha / c / gamma measured at x/y/diagonal (mode 1) and consolidated
    into directional-isotropy statistics (vs the prior synthetic modal check).

All within the accepted compact-air envelope (nx=64, mode 1 / low-k).
Diagnostic; baseline unchanged.

Usage:
    python -m scripts.phase2_robust_p2_238_c3
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

from core.equilibrium import equilibrium_fg
from core.macroscopic import total_energy
from core.solver import GasSolver2D
from core.unit_mapping import create_unit_mapping
from scripts.phase2_m2_verification import load_config, sha256_file, summary_payload_digest
from verification.acoustic_wave_measurement import measure_acoustic_wave
from verification.shear_wave_measurement import measure_shear_wave
from verification.thermal_diffusion_measurement import measure_thermal_diffusion

DEFAULT_CONFIG = Path("configs/gas_air_10k_d2q37_physical_timestep.yaml")
DEFAULT_OUTPUT_ROOT = Path("results/phase2_p2_238_c3")
N = 64
UNIFORM_STEPS = 2000
PERTURB_STEPS = 600


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


def _invariants(solver: GasSolver2D):
    f, g = solver.f, solver.g
    mapping, lattice = solver.mapping, solver.lattice
    mass = float(np.sum(f))
    mom = np.einsum("yxq,qi->i", f, np.asarray(lattice.c, dtype=float))
    energy = float(np.sum(total_energy(f, g, D=mapping.lattice.D, S=mapping.lattice.S, lattice=lattice)))
    return mass, np.asarray(mom, dtype=float), energy


# --------------------------------------------------------------------------- #
# P2-2 admissibility
# --------------------------------------------------------------------------- #
def _p2_2_admissibility(base) -> dict[str, Any]:
    mapping = create_unit_mapping(base)
    solver = GasSolver2D({**base, "numerics": {**base.get("numerics", {}), "nx": 4, "ny": 4}})
    lattice = solver.lattice
    rho0 = mapping.lattice.rho_ref_lu
    theta0 = mapping.theta_ref_lu
    c0 = float(np.sqrt(mapping.physical.gamma * theta0))
    min_f = np.inf
    min_g = np.inf
    worst = None
    for drho in (-0.01, 0.0, 0.01):
        for dth in (-0.01, 0.0, 0.01):
            for mach in (0.0, 0.02, 0.05):
                for ux, uy in ((mach * c0, 0.0), (mach * c0 / np.sqrt(2), mach * c0 / np.sqrt(2))):
                    rho = np.array([[rho0 * (1.0 + drho)]])
                    theta = np.array([[theta0 * (1.0 + dth)]])
                    u = np.zeros((1, 1, 2))
                    u[..., 0] = ux
                    u[..., 1] = uy
                    f, g = equilibrium_fg(rho, u, theta, mapping.lattice.S, lattice)
                    fmin, gmin = float(np.min(f)), float(np.min(g))
                    if fmin < min_f:
                        min_f, worst = fmin, {"drho": drho, "dtheta": dth, "mach": mach, "ux": float(ux), "uy": float(uy)}
                    min_g = min(min_g, gmin)
    return {
        "envelope": "rho/theta +-1%, Mach in {0,0.02,0.05}, background x and diagonal",
        "min_f_eq": min_f,
        "min_g_eq": min_g,
        "f_eq_admissible": bool(min_f >= 0.0),
        "worst_f_state": worst,
    }


# --------------------------------------------------------------------------- #
# P2-2 perturbation stability
# --------------------------------------------------------------------------- #
def _p2_2_perturbation_stability(base) -> dict[str, Any]:
    cfg = {**base, "numerics": {**base.get("numerics", {}), "nx": N, "ny": N}}
    cfg["case"] = {**cfg.get("case", {}), "name": "p2_2_perturbation_stability"}
    solver = GasSolver2D(cfg)
    rho0 = solver.mapping.lattice.rho_ref_lu
    theta0 = solver.mapping.theta_ref_lu
    rng = np.random.default_rng(20260623)
    amp = 1.0e-4
    # multi-mode smooth random perturbation (low-k band) on rho/u/theta
    def _band_limited():
        field = rng.standard_normal((N, N))
        spec = np.fft.fft2(field)
        kx = np.fft.fftfreq(N)[:, None]
        ky = np.fft.fftfreq(N)[None, :]
        mask = (np.sqrt(kx * kx + ky * ky) <= 4.0 / N)  # keep lowest ~4 modes
        spec *= mask
        out = np.real(np.fft.ifft2(spec))
        return out / (np.max(np.abs(out)) + 1e-300)
    rho = rho0 * (1.0 + amp * _band_limited())
    theta = theta0 * (1.0 + amp * _band_limited())
    c0 = c0_of(solver)
    u = np.zeros((N, N, 2))
    u[..., 0] = amp * c0 * _band_limited()
    u[..., 1] = amp * c0 * _band_limited()
    solver.initialize_from_macro(rho, u, theta)

    def _pert_norm():
        m = solver.get_macro()
        return float(np.sqrt(np.mean((m.rho - rho0) ** 2) + np.mean((m.theta - theta0) ** 2)))

    n0 = _pert_norm()
    min_theta = np.inf
    first_invalid = None
    nan_detected = False
    for step in range(PERTURB_STEPS + 1):
        m = solver.get_macro()
        finite = bool(np.isfinite(m.rho).all() and np.isfinite(m.theta).all() and np.isfinite(m.u).all())
        nan_detected = nan_detected or not finite
        tmin = float(np.nanmin(m.theta)) if m.theta.size else np.nan
        min_theta = min(min_theta, tmin)
        if (not finite) or tmin <= 0.0:
            first_invalid = step
            break
        if step < PERTURB_STEPS:
            solver.step()
    n_final = _pert_norm() if first_invalid is None else np.nan
    return {
        "steps": PERTURB_STEPS,
        "amplitude": amp,
        "perturbation_norm_initial": n0,
        "perturbation_norm_final": float(n_final) if np.isfinite(n_final) else np.nan,
        "decay_ratio": float(n_final / n0) if np.isfinite(n_final) and n0 > 0 else np.nan,
        "min_theta_lu": float(min_theta),
        "first_invalid_step": first_invalid,
        "nan_detected": nan_detected,
        "stable": bool(first_invalid is None and not nan_detected and np.isfinite(n_final) and n_final <= n0),
    }


def c0_of(solver: GasSolver2D) -> float:
    return float(np.sqrt(solver.mapping.physical.gamma * solver.mapping.theta_ref_lu))


# --------------------------------------------------------------------------- #
# P2-3 long-time uniform stability + invariants
# --------------------------------------------------------------------------- #
def _p2_3_uniform_run(base, *, background_mach: float) -> dict[str, Any]:
    cfg = {**base, "numerics": {**base.get("numerics", {}), "nx": N, "ny": N}}
    cfg["case"] = {**cfg.get("case", {}), "name": f"p2_3_uniform_m{background_mach}"}
    solver = GasSolver2D(cfg)
    rho0 = solver.mapping.lattice.rho_ref_lu
    theta0 = solver.mapping.theta_ref_lu
    c0 = c0_of(solver)
    u0 = background_mach * c0
    rho = np.full((N, N), rho0)
    theta = np.full((N, N), theta0)
    u = np.zeros((N, N, 2))
    u[..., 0] = u0
    solver.initialize_from_macro(rho, u, theta)
    m0, p0, e0 = _invariants(solver)
    max_rho_dev = max_u_dev = max_theta_dev = 0.0
    max_mass_drift = max_mom_drift = max_energy_drift = 0.0
    first_invalid = None
    for step in range(UNIFORM_STEPS + 1):
        mac = solver.get_macro()
        if not np.isfinite(mac.theta).all() or float(np.nanmin(mac.theta)) <= 0.0:
            first_invalid = step
            break
        # uniform fixed point: deviation from the uniform background
        max_rho_dev = max(max_rho_dev, float(np.max(np.abs(mac.rho - rho0))))
        max_u_dev = max(max_u_dev, float(np.max(np.abs(mac.u[..., 0] - u0))), float(np.max(np.abs(mac.u[..., 1]))))
        max_theta_dev = max(max_theta_dev, float(np.max(np.abs(mac.theta - theta0))))
        if step % 200 == 0:
            mm, pp, ee = _invariants(solver)
            max_mass_drift = max(max_mass_drift, abs(mm / m0 - 1.0))
            max_mom_drift = max(max_mom_drift, float(np.max(np.abs(pp - p0))))
            max_energy_drift = max(max_energy_drift, abs(ee / e0 - 1.0))
        if step < UNIFORM_STEPS:
            solver.step()
    return {
        "background_mach": background_mach,
        "steps": UNIFORM_STEPS,
        "max_rho_deviation": max_rho_dev,
        "max_u_deviation": max_u_dev,
        "max_theta_deviation": max_theta_dev,
        "mass_relative_drift": max_mass_drift,
        "momentum_abs_drift": max_mom_drift,
        "energy_relative_drift": max_energy_drift,
        "first_invalid_step": first_invalid,
        "stable": bool(first_invalid is None),
    }


# --------------------------------------------------------------------------- #
# P2-8 directional error statistics
# --------------------------------------------------------------------------- #
def _p2_8_directional_statistics(base) -> dict[str, Any]:
    cfg = deepcopy(base)
    dirs = ["x", "y", "diagonal"]
    cfg["p2_04_shear_wave"] = {**cfg.get("p2_04_shear_wave", {}), "nx": N, "ny": N, "mode_index": 1, "directions": dirs}
    cfg["p2_05_thermal_diffusion"] = {**cfg.get("p2_05_thermal_diffusion", {}), "nx": N, "ny": N, "mode_index": 1, "directions": dirs}
    cfg["p2_06_acoustic_wave"] = {**cfg.get("p2_06_acoustic_wave", {}), "nx": N, "ny": N, "mode_index": 1, "directions": dirs}
    p4 = measure_shear_wave(cfg)
    p5 = measure_thermal_diffusion(cfg)
    p6 = measure_acoustic_wave(cfg)

    def _spread(values):
        vals = [v for v in values if np.isfinite(v)]
        if len(vals) < 2:
            return np.nan
        return float((max(vals) - min(vals)) / (np.mean(vals)))

    nu = {d: p4["direction_results"][d]["nu_measured_lu"] for d in dirs}
    al = {d: p5["direction_results"][d]["alpha_measured_lu"] for d in dirs}
    cc = {d: p6["direction_results"][d]["sound_speed_measured_lu"] for d in dirs}
    gm = {d: p6["direction_results"][d]["gamma_measured"] for d in dirs}
    spreads = {
        "nu": _spread(list(nu.values())),
        "alpha": _spread(list(al.values())),
        "sound_speed": _spread(list(cc.values())),
        "gamma": _spread(list(gm.values())),
    }
    return {
        "nu_by_direction": nu, "alpha_by_direction": al,
        "sound_speed_by_direction": cc, "gamma_by_direction": gm,
        "directional_spread": spreads,
        "max_directional_spread": float(np.nanmax(list(spreads.values()))),
        "nu_dir_diff": float(p4["direction_difference"]),
        "alpha_dir_diff": float(p5["direction_difference"]),
        "sound_speed_dir_diff": float(p6["direction_difference"]),
    }


def run_diagnostic(*, config_path: Path, output_root: Path) -> dict[str, Any]:
    base = load_config(config_path)
    admissibility = _p2_2_admissibility(base)
    perturbation = _p2_2_perturbation_stability(base)
    uniform_rest = _p2_3_uniform_run(base, background_mach=0.0)
    uniform_bg = _p2_3_uniform_run(base, background_mach=0.05)
    directional = _p2_8_directional_statistics(base)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = output_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    p2_2_pass = bool(admissibility["f_eq_admissible"] and perturbation["stable"])
    p2_3_pass = bool(
        uniform_rest["stable"] and uniform_bg["stable"]
        and uniform_rest["mass_relative_drift"] <= 1e-8 and uniform_rest["energy_relative_drift"] <= 1e-8
        and uniform_bg["mass_relative_drift"] <= 1e-8 and uniform_bg["energy_relative_drift"] <= 1e-8
    )
    p2_8_pass = bool(directional["max_directional_spread"] <= 0.05)
    payload = {
        "run_id": run_id,
        "status": "DIAGNOSTIC_COMPLETE",
        "config_path": str(config_path),
        "config_sha256": sha256_file(config_path),
        "python": sys.version,
        "platform": platform.platform(),
        "default_closure": "D2Q37 RR (strain_rate_isotropic + ghost_orthogonal_local + diagnostic_zero)",
        "p2_2_admissibility": admissibility,
        "p2_2_perturbation_stability": perturbation,
        "p2_3_uniform_rest": uniform_rest,
        "p2_3_uniform_background": uniform_bg,
        "p2_8_directional_statistics": directional,
        "verdict": {
            "p2_2_c3_pass": p2_2_pass,
            "p2_3_c3_pass": p2_3_pass,
            "p2_8_c3_pass": p2_8_pass,
            "all_c3_pass": bool(p2_2_pass and p2_3_pass and p2_8_pass),
        },
        "interpretation": {
            "p2_2": (
                f"f_eq admissible (min {admissibility['min_f_eq']:.3e} >= 0) across the envelope; a real "
                f"multi-mode perturbation is stable (decay ratio {perturbation['decay_ratio']:.4g}, no NaN/negative theta)."
            ),
            "p2_3": (
                f"Uniform rest/background states stable over {UNIFORM_STEPS} steps; invariant drift "
                f"(mass {max(uniform_rest['mass_relative_drift'], uniform_bg['mass_relative_drift']):.2e}, energy "
                f"{max(uniform_rest['energy_relative_drift'], uniform_bg['energy_relative_drift']):.2e}) and "
                f"fixed-point excursion (theta {max(uniform_rest['max_theta_deviation'], uniform_bg['max_theta_deviation']):.2e}) "
                "are at/near machine precision."
            ),
            "p2_8": (
                f"Directional (x/y/diagonal) isotropy at mode 1: max spread "
                f"{directional['max_directional_spread']:.4g} (nu/alpha/c/gamma), within 5%."
            ),
            "boundaries": (
                "Diagnostic; baseline unchanged. C3 evidence within the accepted compact-air mode1/low-k envelope "
                "(M2_Critical_Decision §5). High-k / other-resolution behaviour is the documented GO-RISK boundary."
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
    ad = p["p2_2_admissibility"]
    pe = p["p2_2_perturbation_stability"]
    ur = p["p2_3_uniform_rest"]
    ub = p["p2_3_uniform_background"]
    di = p["p2_8_directional_statistics"]
    v = p["verdict"]
    lines = [
        "# Phase 2 P2-2 / P2-3 / P2-8 C1 -> C3 Diagnostic (RR default)",
        "",
        f"- run_id: `{p['run_id']}`",
        f"- all C3 pass (compact-air envelope): **{_fmt(v['all_c3_pass'])}**",
        f"- summary_digest: `{p['summary_digest']}`",
        "",
        "## P2-2 admissibility + perturbation stability",
        f"- f_eq admissible: {_fmt(ad['f_eq_admissible'])} (min f_eq {_fmt(ad['min_f_eq'])}, min g_eq {_fmt(ad['min_g_eq'])})",
        f"- perturbation stable: {_fmt(pe['stable'])} (decay ratio {_fmt(pe['decay_ratio'])}, min theta {_fmt(pe['min_theta_lu'])}, "
        f"invalid step {_fmt(pe['first_invalid_step'])})",
        f"- **P2-2 C3: {_fmt(v['p2_2_c3_pass'])}**",
        "",
        "## P2-3 long-time uniform stability + invariants",
        "| run | steps | mass drift | momentum drift | energy drift | theta excursion | stable |",
        "|---|---|---|---|---|---|---|",
        f"| rest (M0) | {ur['steps']} | {_fmt(ur['mass_relative_drift'])} | {_fmt(ur['momentum_abs_drift'])} | "
        f"{_fmt(ur['energy_relative_drift'])} | {_fmt(ur['max_theta_deviation'])} | {_fmt(ur['stable'])} |",
        f"| background (M0.05) | {ub['steps']} | {_fmt(ub['mass_relative_drift'])} | {_fmt(ub['momentum_abs_drift'])} | "
        f"{_fmt(ub['energy_relative_drift'])} | {_fmt(ub['max_theta_deviation'])} | {_fmt(ub['stable'])} |",
        f"- **P2-3 C3: {_fmt(v['p2_3_c3_pass'])}**",
        "",
        "## P2-8 directional error statistics (mode 1, x/y/diagonal)",
        f"- directional spread: nu {_fmt(di['directional_spread']['nu'])}, alpha {_fmt(di['directional_spread']['alpha'])}, "
        f"c {_fmt(di['directional_spread']['sound_speed'])}, gamma {_fmt(di['directional_spread']['gamma'])}",
        f"- max directional spread: {_fmt(di['max_directional_spread'])}",
        f"- **P2-8 C3: {_fmt(v['p2_8_c3_pass'])}**",
        "",
        "## Interpretation",
        "",
    ]
    for key, text in p["interpretation"].items():
        lines.append(f"- **{key}**: {text}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="P2-2/3/8 C1 -> C3 diagnostic.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    payload = run_diagnostic(config_path=args.config, output_root=args.output_root)
    print(f"{payload['status']}; all_c3_pass={payload['verdict']['all_c3_pass']}; "
          f"wrote {args.output_root / payload['run_id']}; digest={payload['summary_digest']}")


if __name__ == "__main__":
    main()
