"""Phase_3 Level A/B handoff pre-risk diagnostic.

Two handoff deliverables on the D2Q37 RR default baseline:

1. §798 near-wall Fourier-law check (real space).  The production P2-5 check is
   modal (Fourier-amplitude); Phase_3 Level B/C near-wall conjugate coupling needs
   the actual normal heat flux at an interior cross-section.  This imposes a
   wall-normal (y) isobaric thermal sine, evolves it, and compares the extracted
   conductive normal heat flux q_n(y) to the analytic Fourier law -k_th dθ/dy in
   REAL space (x-averaged profile), in both LU and SI.

2. Handoff-interface exercise.  Confirms the (lattice-aware) wall heat-flux
   extraction matches the solver for the D2Q37 default, the LU<->SI conversion
   round-trips, and probe sampling returns the fields Phase_3 consumes.

Diagnostic / pre-risk check; not a hard gate.  Does not change the baseline.

Usage:
    python -m scripts.phase2_phase3_handoff
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
from typing import Any

import numpy as np

from core.solver import GasSolver2D
from core.unit_mapping import heat_flux_lu_to_phys
from phase3_interfaces.heat_flux_extraction import (
    UPPER_GAS_WALL_NORMAL,
    extract_wall_heat_flux,
    normal_heat_flux_lu,
)
from scripts.phase2_m2_verification import load_config, sha256_file, summary_payload_digest
from verification.thermal_diffusion_measurement import _fourier_heat_flux_coefficient_lu

DEFAULT_CONFIG = Path("configs/gas_air_10k_d2q37_physical_timestep.yaml")
DEFAULT_OUTPUT_ROOT = Path("results/phase2_phase3_handoff")
NX = 64
NY = 64
AMPLITUDE = 1.0e-5
STEPS = 40
FOURIER_REFERENCE_TOLERANCE = 0.05  # P2-5 heat-flux tolerance, used as a pre-risk reference


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


def _build_thermal_gradient_solver(config: dict[str, Any]) -> GasSolver2D:
    cfg = {**config, "numerics": {**config.get("numerics", {}), "nx": NX, "ny": NY}}
    cfg["case"] = {**cfg.get("case", {}), "name": "phase3_handoff_near_wall"}
    solver = GasSolver2D(cfg)
    theta0 = solver.mapping.theta_ref_lu
    ky = 2.0 * np.pi / NY
    profile = theta0 * (1.0 + AMPLITUDE * np.sin(ky * np.arange(NY, dtype=float)))
    theta = np.repeat(profile[:, None], NX, axis=1)
    p0 = solver.mapping.lattice.rho_ref_lu * theta0
    rho = p0 / theta
    u = np.zeros((NY, NX, 2), dtype=float)
    solver.initialize_from_macro(rho, u, theta)
    solver.step(STEPS)
    return solver, cfg


def _periodic_ddy(field_1d: np.ndarray) -> np.ndarray:
    """Periodic central difference d/dy of a 1-D y-profile (unit grid spacing)."""
    return 0.5 * (np.roll(field_1d, -1) - np.roll(field_1d, 1))


def _near_wall_fourier_check(solver: GasSolver2D, cfg: dict[str, Any]) -> dict[str, Any]:
    macro = solver.get_macro()
    theta = macro.theta  # (ny, nx)
    # extracted conductive normal (y) heat flux, x-averaged 1-D profile
    q_n_field = extract_wall_heat_flux(solver.f, solver.g, config=cfg, wall_normal=UPPER_GAS_WALL_NORMAL)
    q_n = np.mean(q_n_field, axis=1)  # (ny,)
    theta_y = np.mean(theta, axis=1)  # (ny,)
    coeff_lu = _fourier_heat_flux_coefficient_lu(solver)
    q_n_analytic = -coeff_lu * _periodic_ddy(theta_y)  # Fourier law -k dθ/dy (LU)

    denom = float(np.max(np.abs(q_n_analytic)))
    abs_err = np.abs(q_n - q_n_analytic)
    l2_rel = float(np.linalg.norm(q_n - q_n_analytic) / np.linalg.norm(q_n_analytic)) if denom > 0 else np.nan
    max_rel = float(np.max(abs_err) / denom) if denom > 0 else np.nan
    # SI peak (exercise LU->SI conversion)
    q_n_peak_lu = float(np.max(np.abs(q_n)))
    q_n_peak_si = float(heat_flux_lu_to_phys(q_n_peak_lu, solver.mapping))
    ky = 2.0 * np.pi / NY
    discrete_gradient_factor = float(np.sin(ky) / ky)  # sin(k)/k discrete-difference artifact
    return {
        "nx": NX,
        "ny": NY,
        "steps": STEPS,
        "k_y_lu": ky,
        "fourier_coeff_lu": float(coeff_lu),
        "discrete_gradient_factor_sin_k_over_k": discrete_gradient_factor,
        "q_n_peak_lu": q_n_peak_lu,
        "q_n_peak_si_W_m2": q_n_peak_si,
        "real_space_l2_relative_error": l2_rel,
        "real_space_max_relative_error": max_rel,
        "reference_tolerance": FOURIER_REFERENCE_TOLERANCE,
        "within_reference_tolerance": bool(np.isfinite(l2_rel) and l2_rel <= FOURIER_REFERENCE_TOLERANCE),
    }


def _interface_exercise(solver: GasSolver2D, cfg: dict[str, Any]) -> dict[str, Any]:
    q_n_extracted = extract_wall_heat_flux(solver.f, solver.g, config=cfg)
    q_n_solver = normal_heat_flux_lu(solver.get_heat_flux_lu(), UPPER_GAS_WALL_NORMAL)
    extraction_matches_solver = bool(np.allclose(q_n_extracted, q_n_solver, rtol=1e-10, atol=1e-300))
    q_n_phys = extract_wall_heat_flux(solver.f, solver.g, config=cfg, return_physical=True)
    si_roundtrip = bool(np.allclose(q_n_phys, heat_flux_lu_to_phys(q_n_extracted, solver.mapping), rtol=1e-12))
    samples = solver.sample_probe([(NY // 4, NX // 4), (NY // 2, NX // 2)])
    probe_fields_ok = all({"rho_lu", "u_lu", "theta_lu", "p_lu", "q_lu"} <= set(s) for s in samples.values())
    return {
        "velocity_set": solver.mapping.lattice.velocity_set,
        "extraction_matches_solver_heat_flux": extraction_matches_solver,
        "lu_si_roundtrip_ok": si_roundtrip,
        "probe_count": len(samples),
        "probe_fields_ok": probe_fields_ok,
        "heat_flux_sign_convention": "q_g''=-k_g*dT/dy|0+ positive from film into upper gas",
    }


def run_diagnostic(*, config_path: Path, output_root: Path) -> dict[str, Any]:
    base = load_config(config_path)
    solver, cfg = _build_thermal_gradient_solver(base)
    near_wall = _near_wall_fourier_check(solver, cfg)
    interfaces = _interface_exercise(solver, cfg)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = output_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    handoff_ready = bool(
        near_wall["within_reference_tolerance"]
        and interfaces["extraction_matches_solver_heat_flux"]
        and interfaces["lu_si_roundtrip_ok"]
        and interfaces["probe_fields_ok"]
    )
    payload = {
        "run_id": run_id,
        "status": "DIAGNOSTIC_COMPLETE",
        "config_path": str(config_path),
        "config_sha256": sha256_file(config_path),
        "python": sys.version,
        "platform": platform.platform(),
        "default_closure": "D2Q37 RR (strain_rate_isotropic + ghost_orthogonal_local + diagnostic_zero)",
        "near_wall_fourier_check": near_wall,
        "handoff_interfaces": interfaces,
        "handoff_ready_level_ab": handoff_ready,
        "interpretation": {
            "near_wall": (
                "Real-space (§798) interior-cross-section conductive q_n(y) vs analytic Fourier law "
                f"-k_th dθ/dy: L2 rel err {near_wall['real_space_l2_relative_error']:.4g}, max rel err "
                f"{near_wall['real_space_max_relative_error']:.4g} (reference tol {FOURIER_REFERENCE_TOLERANCE}). "
                "At low k the discrete-gradient sin(k)/k artifact is ~"
                f"{1.0 - near_wall['discrete_gradient_factor_sin_k_over_k']:.4g}, so the residual reflects the "
                "LBM conductive-flux Fourier consistency. Complements the modal P2-5 check for Level B/C near-wall coupling."
            ),
            "interfaces": (
                "Lattice-aware wall heat-flux extraction matches the solver for the D2Q37 default "
                f"({interfaces['extraction_matches_solver_heat_flux']}); LU<->SI round-trips "
                f"({interfaces['lu_si_roundtrip_ok']}); probe sampling returns Phase_3 handoff fields "
                f"({interfaces['probe_fields_ok']})."
            ),
            "boundaries": (
                "Diagnostic / pre-risk check; baseline unchanged. Supports Phase_3 Level A/B handoff readiness "
                "within the BOUNDED_PRODUCTION_GO compact-air boundary (M2_Critical_Decision §5)."
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
    nw = p["near_wall_fourier_check"]
    it = p["handoff_interfaces"]
    lines = [
        "# Phase 2 -> Phase 3 Level A/B Handoff Pre-Risk Diagnostic",
        "",
        f"- run_id: `{p['run_id']}`",
        f"- default closure: {p['default_closure']}",
        f"- handoff_ready (Level A/B): **{_fmt(p['handoff_ready_level_ab'])}**",
        f"- summary_digest: `{p['summary_digest']}`",
        "",
        "## §798 near-wall Fourier-law check (real space, D2Q37 default)",
        "",
        f"- grid {nw['nx']}x{nw['ny']}, steps {nw['steps']}, k_y={_fmt(nw['k_y_lu'])}",
        f"- conductive q_n(y) vs analytic -k_th dθ/dy: L2 rel err **{_fmt(nw['real_space_l2_relative_error'])}**, "
        f"max rel err {_fmt(nw['real_space_max_relative_error'])} (ref tol {_fmt(nw['reference_tolerance'])}) "
        f"-> within tol: {_fmt(nw['within_reference_tolerance'])}",
        f"- q_n peak: {_fmt(nw['q_n_peak_lu'])} LU = {_fmt(nw['q_n_peak_si_W_m2'])} W/m^2",
        f"- discrete-gradient sin(k)/k factor: {_fmt(nw['discrete_gradient_factor_sin_k_over_k'])}",
        "",
        "## Handoff interfaces (D2Q37 default)",
        "",
        f"- velocity_set: {it['velocity_set']}",
        f"- extraction matches solver heat flux: {_fmt(it['extraction_matches_solver_heat_flux'])}",
        f"- LU<->SI round-trip: {_fmt(it['lu_si_roundtrip_ok'])}",
        f"- probe fields ok ({it['probe_count']} probes): {_fmt(it['probe_fields_ok'])}",
        f"- heat-flux sign: {it['heat_flux_sign_convention']}",
        "",
        "## Interpretation",
        "",
    ]
    for key, text in p["interpretation"].items():
        lines.append(f"- **{key}**: {text}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase_3 Level A/B handoff pre-risk diagnostic.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    payload = run_diagnostic(config_path=args.config, output_root=args.output_root)
    print(f"{payload['status']}; handoff_ready_level_ab={payload['handoff_ready_level_ab']}; "
          f"wrote {args.output_root / payload['run_id']}; digest={payload['summary_digest']}")


if __name__ == "__main__":
    main()
