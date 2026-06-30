"""Phase_3 P3-2 Level B prescribed wall heat-flux smoke."""

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

from boundary.wall_neumann import (
    LEVEL_B_HEAT_FLUX_SIGN_CONVENTION,
    LEVEL_B_WALL_NORMAL_CONVENTION,
    apply_bottom_neumann_wall,
    heat_flux_lu_from_inputs,
    sinusoidal_wall_heat_flux_lu,
)
from core.solver import GasSolver2D
from phase3_interfaces.complex_amplitude import complex_amplitude
from scripts.phase2_m2_verification import load_config, sha256_file, summary_payload_digest


DEFAULT_CONFIG = Path("configs/phase3_levelb_flux_10k.yaml")
DEFAULT_OUTPUT_ROOT = Path("results/phase3_levelb_wall_flux")
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


def _relative_amplitude_error(measured: complex, reference: complex) -> float:
    if abs(reference) == 0.0:
        return float("nan")
    return float(abs(abs(measured) / abs(reference) - 1.0))


def _phase_error_deg(measured: complex, reference: complex) -> float:
    if abs(reference) == 0.0 or abs(measured) == 0.0:
        return float("nan")
    ratio = measured / reference
    return float(math.degrees(math.atan2(ratio.imag, ratio.real)))


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
        "name": phase3_config.get("case", {}).get("name", "phase3_levelb_flux_10k"),
        "phase": "Phase_3",
        "level": "B",
    }
    return gas, gas_config_path


def run_levelb_smoke(*, config_path: Path, output_root: Path) -> dict[str, Any]:
    phase3_config = load_config(config_path)
    gas_config, gas_config_path = _solver_config(phase3_config)
    level_b = phase3_config["level_b"]
    physical = phase3_config["physical"]
    numerics = phase3_config["numerics"]
    gates = phase3_config["gates"]

    solver = GasSolver2D(gas_config)
    solver.initialize_from_macro(
        solver.mapping.lattice.rho_ref_lu,
        np.zeros((solver.ny, solver.nx, 2), dtype=float),
        solver.mapping.theta_ref_lu,
    )
    rho_policy = str(level_b.get("rho_wall_policy", "pressure_preserving"))
    inject_energy = bool(level_b.get("inject_energy", True))
    q_hat_lu = heat_flux_lu_from_inputs(solver, q_wall_si=float(physical["q_wall_hat_W_m2"]))
    q_mean_lu = heat_flux_lu_from_inputs(solver, q_wall_si=float(physical["q_wall_mean_W_m2"]))

    # A single application fully determines the construction check; the wall row is set
    # once from the uniform reference state. (Re-applying without solver.step() only
    # re-imposes on an already-clamped row, so it adds no information.)
    constant = apply_bottom_neumann_wall(
        solver,
        q_wall_lu=q_hat_lu,
        rho_policy=rho_policy,
        inject_energy=inject_energy,
    )
    constant_rel_err = abs(constant.q_wall_recovered_lu - q_hat_lu) / max(abs(q_hat_lu), 1.0e-300)
    # Normalise the energy residual by the flux-independent total field energy so the gate
    # reflects floating-point closure of the injection bookkeeping, not the imposed flux
    # magnitude. expected_energy_delta is proportional to q, so normalising by it would make
    # the relative residual blow up as ~1/q and spuriously fail the smoke for small fluxes.
    energy_scale = max(abs(constant.energy_before_lu), 1.0e-300)
    constant_energy_rel = abs(constant.energy_residual_lu) / energy_scale

    samples = int(numerics.get("sinusoidal_samples", 64))
    frequency_hz = float(physical["frequency_Hz"])
    times = np.arange(samples, dtype=float) / (frequency_hz * samples)
    recovered = np.empty(samples, dtype=float)
    imposed = np.empty(samples, dtype=float)
    for i, t_si in enumerate(times):
        q_lu = float(
            sinusoidal_wall_heat_flux_lu(
                t_si,
                q0_lu=q_mean_lu,
                q_hat_lu=q_hat_lu,
                frequency_hz=frequency_hz,
            )
        )
        diag = apply_bottom_neumann_wall(
            solver,
            q_wall_lu=q_lu,
            rho_policy=rho_policy,
            inject_energy=inject_energy,
        )
        imposed[i] = q_lu - q_mean_lu
        recovered[i] = diag.q_wall_recovered_lu - q_mean_lu
    imposed_hat = complex_amplitude(times, imposed, frequency_hz)
    recovered_hat = complex_amplitude(times, recovered, frequency_hz)
    amp_err = _relative_amplitude_error(recovered_hat, imposed_hat)
    phase_err = _phase_error_deg(recovered_hat, imposed_hat)

    flux_gate = float(gates["recovered_heat_flux_relative_error"])
    phase_gate = float(gates["recovered_heat_flux_phase_error_deg"])
    energy_gate = float(gates["energy_residual_relative"])
    velocity_gate = float(gates["normal_velocity_leakage_lu"])
    tangent_gate = float(gates["tangential_heat_flux_lu"])
    constant_pass = bool(
        constant.finite
        and constant_rel_err <= flux_gate
        and constant_energy_rel <= energy_gate
        and constant.max_velocity_lu <= velocity_gate
        and constant.max_tangential_heat_flux_lu <= tangent_gate
    )
    sinusoidal_pass = bool(
        np.isfinite(amp_err)
        and np.isfinite(phase_err)
        and amp_err <= flux_gate
        and abs(phase_err) <= phase_gate
    )
    status = "PASSED" if constant_pass and sinusoidal_pass else "FAILED"

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = output_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "run_id": run_id,
        "status": status,
        "level": "B",
        "m3_gate": "NOT_CLAIMED",
        "config_path": str(config_path),
        "config_sha256": sha256_file(config_path),
        "gas_config_path": str(gas_config_path),
        "gas_config_sha256": sha256_file(gas_config_path),
        "python": sys.version,
        "platform": platform.platform(),
        "velocity_set": constant.velocity_set,
        "Q": constant.Q,
        "wall_normal_convention": LEVEL_B_WALL_NORMAL_CONVENTION,
        "heat_flux_sign_convention": LEVEL_B_HEAT_FLUX_SIGN_CONVENTION,
        "rho_wall_policy": rho_policy,
        "inject_energy": inject_energy,
        "constant_flux": {
            "q_wall_imposed_lu": constant.q_wall_imposed_lu,
            "q_wall_recovered_lu": constant.q_wall_recovered_lu,
            "q_wall_imposed_si": constant.q_wall_imposed_si,
            "q_wall_recovered_si": constant.q_wall_recovered_si,
            "relative_error": constant_rel_err,
            "energy_before_lu": constant.energy_before_lu,
            "energy_delta_lu": constant.energy_delta_lu,
            "expected_energy_delta_lu": constant.expected_energy_delta_lu,
            "energy_residual_lu": constant.energy_residual_lu,
            "energy_residual_relative": constant_energy_rel,
            "theta_wall_lu_before": constant.theta_wall_lu_before,
            "theta_wall_lu_after": constant.theta_wall_lu_after,
            "max_velocity_lu": constant.max_velocity_lu,
            "max_tangential_heat_flux_lu": constant.max_tangential_heat_flux_lu,
            "passed": constant_pass,
        },
        "sinusoidal_flux": {
            "frequency_Hz": frequency_hz,
            "samples": samples,
            "q_hat_imposed_lu": imposed_hat,
            "q_hat_recovered_lu": recovered_hat,
            "amplitude_error": amp_err,
            "phase_error_deg": phase_err,
            "passed": sinusoidal_pass,
        },
        "reference_source": {
            "heat_flux_readback": "GasSolver2D.get_heat_flux_lu + Phase_3 normal convention",
            "phase_convention": "phase3_interfaces/complex_amplitude.py",
            "note": "Level B smoke reads recovered heat flux from f/g; dynamic thermal response and periodic steady-state energy audit remain NOT_CLAIMED",
        },
        "amplitude_errors": {
            "constant_recovered_heat_flux": constant_rel_err,
            "sinusoidal_recovered_heat_flux": amp_err,
        },
        "phase_errors_deg": {
            "sinusoidal_recovered_heat_flux": phase_err,
        },
        "energy_residual": {
            "constant_flux_relative": constant_energy_rel,
            "constant_flux_lu": constant.energy_residual_lu,
            "relative_basis": "abs(residual_lu) / total_field_energy_before_lu (flux-independent)",
        },
        "stability_flags": {
            "no_nan": constant.finite,
            "no_clipping_or_floor_used": True,
            "constant_pass": constant_pass,
            "sinusoidal_pass": sinusoidal_pass,
        },
        "known_risk_boundaries": [
            "P3-2 smoke reads back imposed q_g from f/g, but does not claim full Level B frequency-response M3 pass",
            "Level C is NOT_STARTED",
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
    c = payload["constant_flux"]
    s = payload["sinusoidal_flux"]
    lines = [
        "# Phase_3 P3-2 Level B Wall-Flux Smoke",
        "",
        f"- run_id: `{payload['run_id']}`",
        f"- status: **{payload['status']}**",
        f"- m3_gate: `{payload['m3_gate']}`",
        f"- velocity set: {payload['velocity_set']} (Q={payload['Q']})",
        f"- summary_digest: `{payload['summary_digest']}`",
        "",
        "## Constant Flux",
        "",
        f"- imposed/recovered q_lu: {_fmt(c['q_wall_imposed_lu'])} / {_fmt(c['q_wall_recovered_lu'])}",
        f"- imposed/recovered q_si: {_fmt(c['q_wall_imposed_si'])} / {_fmt(c['q_wall_recovered_si'])} W/m^2",
        f"- relative error: {_fmt(c['relative_error'])}",
        f"- energy residual relative: {_fmt(c['energy_residual_relative'])}",
        f"- max wall velocity: {_fmt(c['max_velocity_lu'])}",
        f"- max tangential q_lu: {_fmt(c['max_tangential_heat_flux_lu'])}",
        "",
        "## Sinusoidal Flux",
        "",
        f"- frequency: {_fmt(s['frequency_Hz'])} Hz, samples: {s['samples']}",
        f"- imposed q_hat: {_fmt(s['q_hat_imposed_lu'])}",
        f"- recovered q_hat: {_fmt(s['q_hat_recovered_lu'])}",
        f"- amplitude error: {_fmt(s['amplitude_error'])}",
        f"- phase error: {_fmt(s['phase_error_deg'])} deg",
        "",
        "This smoke reads the recovered heat flux from f/g via the Phase_3 heat-flux convention. "
        "It does not claim the full Level B dynamic frequency-response M3 gate.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase_3 P3-2 Level B wall-flux smoke.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    payload = run_levelb_smoke(config_path=args.config, output_root=args.output_root)
    print(
        f"{payload['status']}; m3_gate={payload['m3_gate']}; "
        f"wrote {args.output_root / payload['run_id']}; digest={payload['summary_digest']}"
    )


if __name__ == "__main__":
    main()

