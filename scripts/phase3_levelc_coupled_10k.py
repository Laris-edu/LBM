"""Phase_3 P3-4 Level C coupled film-gas smoke."""

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

from core.solver import GasSolver2D
from coupling.conjugate import run_levelc_predictor_corrector
from coupling.drive import SinusoidalDrive
from coupling.film_ode import FilmOdeParams
from scripts.phase2_m2_verification import load_config, sha256_file, summary_payload_digest


DEFAULT_CONFIG = Path("configs/phase3_levelc_coupled_10k_dx2p6.yaml")
DEFAULT_OUTPUT_ROOT = Path("results/m3")
VOLATILE_DIGEST_KEYS = ("run_id", "python", "platform", "config_path", "gas_config_path")


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_json_safe(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, complex):
        return {"real": value.real, "imag": value.imag, "abs": abs(value)}
    if isinstance(value, float) and np.isnan(value):
        return None
    return value


def _solver_config(phase3_config: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    gas_config_path = Path(phase3_config["inheritance"]["gas_config_path"])
    gas = load_config(gas_config_path)
    numerics = phase3_config.get("numerics", {})
    gas["numerics"] = {
        **gas.get("numerics", {}),
        "nx": int(numerics.get("nx", gas.get("numerics", {}).get("nx", 64))),
        "ny": int(numerics.get("ny", gas.get("numerics", {}).get("ny", 8))),
    }
    gas["case"] = {
        **gas.get("case", {}),
        "name": phase3_config.get("case", {}).get("name", "phase3_levelc_coupled_10k_dx2p6"),
        "phase": "Phase_3",
        "level": "C",
    }
    return gas, gas_config_path


def _p_hat(config: dict[str, Any]) -> complex:
    p_hat = config["physical"]["P_hat_W_m2"]
    return complex(float(p_hat.get("real", 0.0)), float(p_hat.get("imag", 0.0)))


def run_levelc_smoke(*, config_path: Path, output_root: Path) -> dict[str, Any]:
    phase3_config = load_config(config_path)
    gas_config, gas_config_path = _solver_config(phase3_config)
    physical = phase3_config["physical"]
    numerics = phase3_config["numerics"]
    level_c = phase3_config["level_c"]
    gates = phase3_config["gates"]

    solver = GasSolver2D(gas_config)
    params = FilmOdeParams(
        C_A_si=float(physical["C_A_J_m2K"]),
        T_ref_K=float(physical["T0_K"]),
        gas_flux_factor=2.0,
    )
    drive = SinusoidalDrive(
        mean_si=float(physical["P_mean_W_m2"]),
        amplitude_hat_si=_p_hat(phase3_config),
        frequency_hz=float(physical["frequency_Hz"]),
    )
    probe_cfg = numerics.get("probe", {})
    probe = (
        int(probe_cfg.get("y", 1)),
        int(probe_cfg.get("x", int(numerics.get("nx", 64)) // 2)),
    )
    result = run_levelc_predictor_corrector(
        solver=solver,
        params=params,
        drive=drive,
        n_steps=int(numerics["steps"]),
        T_initial_K=float(physical["T0_K"]),
        rho_policy=str(level_c.get("rho_wall_policy", "pressure_preserving")),
        scheme=str(level_c.get("coupling_scheme", "heun_picard1")),
        energy_tolerance=float(gates["energy_residual_relative"]),
        probe=probe,
    )
    wall_gate = float(gates["final_wall_temperature_error_K"])
    pc_warn = float(gates["predictor_corrector_delta_warn_K"])
    wall_pass = bool(np.max(np.abs(result.wall_temperature_error_K)) <= wall_gate)
    finite_pass = bool(result.finite)
    no_repair = bool(gates.get("no_clipping_or_floor", True) and result.no_clipping_or_floor_used)
    status = "PASSED" if result.energy_audit.passed and wall_pass and finite_pass and no_repair else "FAILED"

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = output_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "run_id": run_id,
        "status": status,
        "level": "C",
        "m3_gate": "NOT_CLAIMED",
        "scope": "P3-4_LEVEL_C_SHORT_SMOKE_DX2P6",
        "config_path": str(config_path),
        "config_sha256": sha256_file(config_path),
        "gas_config_path": str(gas_config_path),
        "gas_config_sha256": sha256_file(gas_config_path),
        "python": sys.version,
        "platform": platform.platform(),
        "velocity_set": solver.mapping.lattice.velocity_set,
        "Q": int(solver.lattice.q),
        "theta_q_lu": solver.mapping.lattice.theta_q_lu,
        "theta_ref_lu": solver.mapping.theta_ref_lu,
        "theta_transport_lu": solver.mapping.theta_transport_lu,
        "tau21": solver.mapping.tau21,
        "tau22": solver.mapping.tau22,
        "tau32": solver.mapping.tau32,
        "dx_si": solver.mapping.lattice.dx_m,
        "dt_si": solver.mapping.lattice.dt_s,
        "C_A_si": params.C_A_si,
        "P_in_definition": {
            "mean_W_m2": drive.mean_si,
            "P_hat_W_m2": drive.amplitude_hat_si,
            "frequency_Hz": drive.frequency_hz,
            "phase_convention": "x(t)=Re[x_hat exp(i Omega t)]",
        },
        "coupling_scheme": result.coupling_scheme,
        "picard_iterations": result.picard_iterations,
        "wall_normal_convention": result.wall_normal_convention,
        "heat_flux_sign_convention": result.heat_flux_sign_convention,
        "film": {
            "samples": int(result.t_si.size),
            "t_start_si": float(result.t_si[0]),
            "t_end_si": float(result.t_si[-1]),
            "T_s_initial_K": float(result.T_s_K[0]),
            "T_s_final_K": float(result.T_s_K[-1]),
            "T_s_delta_K": float(result.T_s_K[-1] - result.T_s_K[0]),
            "P_in_initial_W_m2": float(result.P_in_si[0]),
            "P_in_final_W_m2": float(result.P_in_si[-1]),
            "q_g_initial_W_m2": float(result.q_g_one_sided_si[0]),
            "q_g_final_W_m2": float(result.q_g_one_sided_si[-1]),
            "max_abs_q_g_W_m2": float(np.max(np.abs(result.q_g_one_sided_si))),
            "max_abs_predictor_corrector_delta_K": float(np.max(np.abs(result.predictor_corrector_delta_K))),
        },
        "wall": {
            "theta_wall_initial_lu": float(result.theta_wall_lu[0]),
            "theta_wall_final_lu": float(result.theta_wall_lu[-1]),
            "T_wall_final_K": float(result.T_wall_K[-1]),
            "max_wall_temperature_error_K": float(np.max(np.abs(result.wall_temperature_error_K))),
            "wall_temperature_passed": wall_pass,
        },
        "probe": {
            "location_yx": list(probe),
            "pressure_initial_Pa": float(result.pressure_probe_Pa[0]),
            "pressure_final_Pa": float(result.pressure_probe_Pa[-1]),
            "temperature_initial_K": float(result.temperature_probe_K[0]),
            "temperature_final_K": float(result.temperature_probe_K[-1]),
        },
        "energy_audit": {
            "max_abs_residual_si": result.energy_audit.max_abs_residual_si,
            "final_residual_si": result.energy_audit.final_residual_si,
            "scale_si": result.energy_audit.scale_si,
            "max_relative_residual": result.energy_audit.max_relative_residual,
            "tolerance": result.energy_audit.tolerance,
            "passed": result.energy_audit.passed,
            "basis": "contract integrated film residual R_E(t0,t_i), not pointwise rhs residual",
        },
        "stability_flags": {
            "no_nan": finite_pass,
            "no_clipping_or_floor_used": no_repair,
            "wall_temperature_passed": wall_pass,
            "energy_audit_passed": result.energy_audit.passed,
            "predictor_corrector_delta_below_warning": bool(
                np.max(np.abs(result.predictor_corrector_delta_K)) <= pc_warn
            ),
        },
        "reference_source": {
            "heat_flux_interface": "phase3_interfaces/heat_flux_extraction.py",
            "wall_temperature_interface": "boundary/wall_dirichlet.py",
            "film_ode_owner": "coupling/film_ode.py",
            "energy_audit_owner": "coupling/energy_audit.py",
            "gas_scoped_config": str(gas_config_path),
            "note": "P3-4 is a short coupling smoke; dynamic Level A/B gates and M3 frequency-response claims remain NOT_CLAIMED",
        },
        "known_risk_boundaries": [
            "P3-4 smoke checks stability, wall/film consistency and integrated energy audit only",
            "No full-period 10 kHz T_s_hat/q_g_hat/p_hat M3 claim is made by this run",
            "Level A/B dynamic admittance/frequency-response gates remain NOT_CLAIMED",
            "Final production claim remains NOT_CLAIMED",
        ],
    }
    safe = _json_safe(payload)
    digest_core = {key: value for key, value in safe.items() if key not in VOLATILE_DIGEST_KEYS}
    safe["summary_digest"] = summary_payload_digest(digest_core)
    safe["summary_digest_scope"] = "physics_core; excludes " + ", ".join(VOLATILE_DIGEST_KEYS)
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
    film = payload["film"]
    wall = payload["wall"]
    energy = payload["energy_audit"]
    lines = [
        "# Phase_3 P3-4 Level C Coupled Smoke",
        "",
        f"- run_id: `{payload['run_id']}`",
        f"- status: **{payload['status']}**",
        f"- scope: `{payload['scope']}`",
        f"- m3_gate: `{payload['m3_gate']}`",
        f"- coupling_scheme: `{payload['coupling_scheme']}`",
        f"- velocity set: {payload['velocity_set']} (Q={payload['Q']})",
        f"- summary_digest: `{payload['summary_digest']}`",
        "",
        "## Film",
        "",
        f"- samples: {film['samples']}",
        f"- time window: {_fmt(film['t_start_si'])} to {_fmt(film['t_end_si'])} s",
        f"- T_s initial/final: {_fmt(film['T_s_initial_K'])} / {_fmt(film['T_s_final_K'])} K",
        f"- q_g initial/final: {_fmt(film['q_g_initial_W_m2'])} / {_fmt(film['q_g_final_W_m2'])} W/m^2",
        f"- max predictor-corrector delta: {_fmt(film['max_abs_predictor_corrector_delta_K'])} K",
        "",
        "## Wall And Energy",
        "",
        f"- max wall temperature error: {_fmt(wall['max_wall_temperature_error_K'])} K",
        f"- energy max relative residual: {_fmt(energy['max_relative_residual'])}",
        f"- energy tolerance: {_fmt(energy['tolerance'])}",
        "",
        "This is a short Level C coupling smoke. It does not claim the full M3 frequency-response gate.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase_3 P3-4 Level C coupled smoke.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    payload = run_levelc_smoke(config_path=args.config, output_root=args.output_root)
    print(
        f"{payload['status']}; m3_gate={payload['m3_gate']}; "
        f"wrote {args.output_root / payload['run_id']}; digest={payload['summary_digest']}"
    )


if __name__ == "__main__":
    main()
