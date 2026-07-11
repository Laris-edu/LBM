"""Phase_3 P3-1 Level A prescribed wall-temperature smoke."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import platform
import sys
from typing import Any

import numpy as np

from boundary.wall_dirichlet import (
    LEVEL_A_HEAT_FLUX_SIGN_CONVENTION,
    LEVEL_A_WALL_NORMAL_CONVENTION,
    advance_with_bottom_dirichlet_wall,
    apply_bottom_dirichlet_wall,
    sinusoidal_wall_temperature_lu,
)
from core.solver import GasSolver2D
from phase3_interfaces.complex_amplitude import complex_amplitude
from reference.thermal_admittance import thermal_admittance_halfspace
from scripts.phase2_m2_verification import load_config, sha256_file, summary_payload_digest


DEFAULT_CONFIG = Path("configs/phase3_levela_isothermal_10k.yaml")
DEFAULT_OUTPUT_ROOT = Path("results/phase3_levela_wall_temperature")

# Keys excluded from summary_digest so the digest is a reproducible physics anchor
# instead of a one-off fingerprint that changes with the run timestamp or machine.
VOLATILE_DIGEST_KEYS = ("run_id", "python", "platform", "config_path", "gas_config_path")


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, complex):
        return {"real": value.real, "imag": value.imag, "abs": abs(value)}
    if isinstance(value, float) and np.isnan(value):
        return None
    return value


def _phase_error_deg(measured: complex, reference: complex) -> float:
    if abs(reference) == 0.0 or abs(measured) == 0.0:
        return float("nan")
    ratio = measured / reference
    return float(math.degrees(math.atan2(ratio.imag, ratio.real)))


def _relative_amplitude_error(measured: complex, reference: complex) -> float:
    if abs(reference) == 0.0:
        return float("nan")
    return float(abs(abs(measured) / abs(reference) - 1.0))


def _solver_config(phase3_config: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    gas_config_path = Path(phase3_config["inheritance"]["gas_config_path"])
    gas = load_config(gas_config_path)
    numerics = phase3_config.get("numerics", {})
    gas["numerics"] = {
        **gas.get("numerics", {}),
        "nx": int(numerics.get("nx", gas.get("numerics", {}).get("nx", 16))),
        "ny": int(numerics.get("ny", gas.get("numerics", {}).get("ny", 16))),
    }
    gas["case"] = {
        **gas.get("case", {}),
        "name": phase3_config.get("case", {}).get("name", "phase3_levela_isothermal_10k"),
        "phase": "Phase_3",
        "level": "A",
    }
    return gas, gas_config_path


def run_levela_smoke(*, config_path: Path, output_root: Path) -> dict[str, Any]:
    phase3_config = load_config(config_path)
    gas_config, gas_config_path = _solver_config(phase3_config)
    level_a = phase3_config["level_a"]
    gates = phase3_config["gates"]
    physical = phase3_config["physical"]
    numerics = phase3_config["numerics"]

    solver = GasSolver2D(gas_config)
    theta0 = float(solver.mapping.theta_ref_lu)
    t0_k = float(physical.get("T0_K", solver.mapping.physical.T0_K))
    rho_policy = str(level_a.get("rho_wall_policy", "pressure_preserving"))
    steps = int(numerics.get("constant_wall_steps", 4))
    constant_diag = advance_with_bottom_dirichlet_wall(
        solver,
        T_wall_K=t0_k,
        rho_policy=rho_policy,
        n_steps=steps,
    )
    macro = solver.get_macro()
    finite = bool(np.isfinite(solver.f).all() and np.isfinite(solver.g).all() and np.isfinite(macro.theta).all())
    uniform_mass = solver.nx * solver.ny * solver.mapping.lattice.rho_ref_lu
    total_mass_rel_drift = float(abs(np.sum(solver.f) - uniform_mass) / uniform_mass)

    samples = int(numerics.get("sinusoidal_samples", 64))
    frequency_hz = float(physical["frequency_Hz"])
    theta_hat = complex(float(physical["wall_temperature_hat_K"]) / solver.mapping.temperature_scale)
    times = np.arange(samples, dtype=float) / (frequency_hz * samples)
    theta_response = np.empty(samples, dtype=float)
    for i, t_si in enumerate(times):
        theta_wall = float(
            sinusoidal_wall_temperature_lu(
                t_si,
                theta0_lu=theta0,
                theta_hat_lu=theta_hat,
                frequency_hz=frequency_hz,
            )
        )
        diag = apply_bottom_dirichlet_wall(
            solver,
            theta_wall_lu=theta_wall,
            rho_policy=rho_policy,
        )
        # Fit the macrostate actually recovered from the clamped wall row, not the
        # prescribed input, so the smoke fails if the equilibrium clamp is broken.
        theta_response[i] = diag.recovered_theta_wall_lu - theta0
    theta_hat_fit = complex_amplitude(times, theta_response, frequency_hz)
    amp_err = _relative_amplitude_error(theta_hat_fit, theta_hat)
    phase_err = _phase_error_deg(theta_hat_fit, theta_hat)

    thermal_admittance = thermal_admittance_halfspace(frequency_hz)
    q_hat_ref = thermal_admittance * complex(float(physical["wall_temperature_hat_K"]))
    wall_theta_rel_gate = float(gates["wall_theta_relative_error_lu"])
    velocity_gate = float(gates["normal_velocity_leakage_lu"])
    amp_gate = float(gates["sinusoidal_wall_amplitude_error"])
    phase_gate = float(gates["sinusoidal_wall_phase_error_deg"])
    constant_pass = bool(
        constant_diag.finite
        and constant_diag.max_theta_error_lu <= wall_theta_rel_gate * max(abs(theta0), 1.0)
        and constant_diag.max_velocity_lu <= velocity_gate
        and finite
    )
    sinusoidal_pass = bool(
        np.isfinite(amp_err)
        and np.isfinite(phase_err)
        and amp_err <= amp_gate
        and abs(phase_err) <= phase_gate
    )
    status = "PASSED" if constant_pass and sinusoidal_pass else "FAILED"

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = output_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "run_id": run_id,
        "status": status,
        "level": "A",
        "m3_gate": "NOT_CLAIMED",
        "config_path": str(config_path),
        "config_sha256": sha256_file(config_path),
        "gas_config_path": str(gas_config_path),
        "gas_config_sha256": sha256_file(gas_config_path),
        "python": sys.version,
        "platform": platform.platform(),
        "velocity_set": constant_diag.velocity_set,
        "Q": constant_diag.Q,
        "wall_normal_convention": LEVEL_A_WALL_NORMAL_CONVENTION,
        "heat_flux_sign_convention": LEVEL_A_HEAT_FLUX_SIGN_CONVENTION,
        "rho_wall_policy": rho_policy,
        "constant_wall": {
            "steps": steps,
            "theta_wall_lu": constant_diag.theta_wall_lu,
            "T_wall_K": constant_diag.T_wall_K,
            "max_theta_error_lu": constant_diag.max_theta_error_lu,
            "max_velocity_lu": constant_diag.max_velocity_lu,
            "total_mass_relative_drift_vs_uniform_reference": total_mass_rel_drift,
            "finite": finite,
            "passed": constant_pass,
        },
        "sinusoidal_wall": {
            "frequency_Hz": frequency_hz,
            "samples": samples,
            "theta_hat_prescribed_lu": theta_hat,
            "theta_hat_recovered_lu": theta_hat_fit,
            "amplitude_error": amp_err,
            "phase_error_deg": phase_err,
            "passed": sinusoidal_pass,
        },
        "reference_source": {
            "phase_convention": "phase3_interfaces/complex_amplitude.py",
            "thermal_admittance_reference": "reference/thermal_admittance.py",
            "note": "thermal admittance is analytic reference only; no Level A dynamic admittance M3 claim in this smoke",
            "q_hat_ref_W_m2": q_hat_ref,
        },
        "amplitude_errors": {
            "sinusoidal_wall_temperature": amp_err,
        },
        "phase_errors_deg": {
            "sinusoidal_wall_temperature": phase_err,
        },
        "stability_flags": {
            "no_nan": finite,
            "no_clipping_or_floor_used": True,
            "constant_pass": constant_pass,
            "sinusoidal_pass": sinusoidal_pass,
        },
        "known_risk_boundaries": [
            "P3-1 smoke clamps the recoverable wall macrostate; M3 thermal-admittance certification remains NOT_CLAIMED",
            "Level B and Level C are NOT_STARTED",
            "final production claim remains NOT_CLAIMED",
        ],
    }
    safe = _json_safe(payload)
    digest_core = {key: value for key, value in safe.items() if key not in VOLATILE_DIGEST_KEYS}
    safe["summary_digest"] = summary_payload_digest(digest_core)
    safe["summary_digest_scope"] = (
        "physics_core; excludes " + ", ".join(VOLATILE_DIGEST_KEYS)
    )
    (out_dir / "summary.json").write_text(json.dumps(safe, indent=2, ensure_ascii=False), encoding="utf-8")
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


def _render_report(payload: dict[str, Any]) -> str:
    c = payload["constant_wall"]
    s = payload["sinusoidal_wall"]
    lines = [
        "# Phase_3 P3-1 Level A Wall-Temperature Smoke",
        "",
        f"- run_id: `{payload['run_id']}`",
        f"- status: **{payload['status']}**",
        f"- m3_gate: `{payload['m3_gate']}`",
        f"- velocity set: {payload['velocity_set']} (Q={payload['Q']})",
        f"- summary_digest: `{payload['summary_digest']}`",
        "",
        "## Constant Wall",
        "",
        f"- steps: {c['steps']}",
        f"- theta error: {_fmt(c['max_theta_error_lu'])}",
        f"- max wall velocity: {_fmt(c['max_velocity_lu'])}",
        f"- mass drift vs uniform reference: {_fmt(c['total_mass_relative_drift_vs_uniform_reference'])}",
        f"- finite/no NaN: {_fmt(c['finite'])}",
        "",
        "## Sinusoidal Wall",
        "",
        f"- frequency: {_fmt(s['frequency_Hz'])} Hz, samples: {s['samples']}",
        f"- prescribed theta_hat: {_fmt(s['theta_hat_prescribed_lu'])}",
        f"- recovered theta_hat: {_fmt(s['theta_hat_recovered_lu'])}",
        f"- amplitude error: {_fmt(s['amplitude_error'])}",
        f"- phase error: {_fmt(s['phase_error_deg'])} deg",
        "",
        "Analytic thermal-admittance reference is recorded for later P3/M3 comparison; "
        "this smoke does not claim a dynamic LBM admittance pass.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase_3 P3-1 Level A wall-temperature smoke.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    payload = run_levela_smoke(config_path=args.config, output_root=args.output_root)
    print(
        f"{payload['status']}; m3_gate={payload['m3_gate']}; "
        f"wrote {args.output_root / payload['run_id']}; digest={payload['summary_digest']}"
    )
    return 0 if payload["status"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
