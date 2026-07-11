"""Phase_4 P4-1 open-top boundary reflection measurement (10 kHz normal incidence).

Launches a plane acoustic wave up the dx2p6 gas column by THERMOACOUSTIC EMISSION from
the production-proven Grad thermal wall (``boundary/wall_thermal_grad.py``, the Phase_3
Level A pattern with an oscillating ``theta_w(t)``): the wall thermal boundary layer
pumps an outgoing wave of expected amplitude ``p' ~ rho0 c0 (Omega delta_T/sqrt(2))
(T_hat/T0)`` (~0.57 Pa at 10 kHz for T_hat=0.354 K). The wave leaves through the
characteristic-impedance open-top boundary (``boundary/open_cbc.py``); the harmonic
pressure field over an interior probe band is decomposed into up-/down-going components

    p_hat(y) = A_inc exp(-i k y) + A_ref exp(+i k y),   k = Omega/c0,

reporting ``R = A_ref/A_inc`` against the P4-1 hard gate ``|R| < 0.05`` (contract §6.3).
The domain is sub-wavelength (lambda = 34.7 mm >> ny*dx), so the two-exponential least
squares is nearly collinear; conditioning, model residual and k-sensitivity are reported.
Bottom re-reflections at the wall only feed the steady-state up-going amplitude -- the
down/up ratio in the probe band remains the top-boundary reflection coefficient.

The thermal drive uses the SAME wall BC as production Level C -- no fixture-only bottom
boundary remains: four refuted velocity-piston fixtures (each destabilized the coupled
column; negative results in ``Phase4_STATUS.md`` 2026-07-04) are replaced by this
source. ``status`` reports script health; the P4-1 verdict lives in
``open_boundary.gate`` -- ``m4_gate`` stays NOT_CLAIMED. All outputs carry the M3
closure authorization boundary (M3_Closure_Decision.md §3).
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import platform
import sys
import time
from typing import Any

import numpy as np

from boundary.open_cbc import compose_boundary_callbacks, make_top_open_boundary_callback
from boundary.wall_thermal_grad import make_bottom_grad_wall_callback
from core.macroscopic import recover_macro
from core.solver import GasSolver2D
from phase3_interfaces.complex_amplitude import complex_amplitude
from phase3_interfaces.run_hdf5 import (
    PHASE3_COMPLEX_CONVENTION,
    phase3_hdf5_metadata,
    write_phase3_run_hdf5,
)
from scripts.phase2_m2_verification import load_config, sha256_file, summary_payload_digest


DEFAULT_CONFIG = Path("configs/phase4_open_top_reflection_10k.yaml")
DEFAULT_OUTPUT_ROOT = Path("results/m4")
VOLATILE_DIGEST_KEYS = (
    "run_id",
    "python",
    "platform",
    "config_path",
    "gas_config_path",
    "artifacts",
    "wall_clock_s",
)


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


def make_thermal_drive_wall_callback(
    *,
    theta0_lu: float,
    theta_hat_lu: float,
    omega_si: float,
    dt_si: float,
    ramp_steps: int,
    rho_policy: str = "pressure_preserving",
    extrap: str = "linear",
):
    """Acoustic source = the PRODUCTION Grad thermal wall with an oscillating temperature.

    Reuses ``boundary/wall_thermal_grad.py`` exactly as the Phase_3 Level A dynamic
    admittance runs do (callable ``theta_w``, ``fill_deep_links=False``): the wall thermal
    boundary layer thermoacoustically pumps an outgoing plane wave of expected amplitude
    ``p' ~ rho0 c0 (Omega delta_T / sqrt(2)) (T_hat/T0)``. The wall temperature ramps in
    with a cosine over ``ramp_steps`` and is imposed at the end-of-step time (Phase_3
    convention). No fixture-only bottom boundary is involved: four velocity-piston
    fixtures were refuted (each destabilized the coupled piston+open-top column through
    the periodic seam or the u-pinning full-state clamp; negative results recorded in
    ``Phase4_STATUS.md`` 2026-07-04), while this thermal_grad + open-top pairing is
    seed-stable (decaying noise floor over 19k+ steps).
    """

    ramp_t = float(ramp_steps) * dt_si

    def theta_w(solver: GasSolver2D) -> float:
        t_now = (solver.t_lu + 1) * dt_si
        if ramp_steps <= 0 or t_now >= ramp_t:
            ramp = 1.0
        else:
            ramp = 0.5 * (1.0 - math.cos(math.pi * t_now / ramp_t))
        return theta0_lu + theta_hat_lu * ramp * math.sin(omega_si * t_now)

    return make_bottom_grad_wall_callback(
        theta_w, rho_policy=rho_policy, extrap=extrap, fill_deep_links=False
    )


def expected_thermoacoustic_pressure_pa(
    *,
    rho0_kg_m3: float,
    c0_m_s: float,
    omega_rad_s: float,
    alpha_m2_s: float,
    T_hat_K: float,
    T0_K: float,
) -> float:
    """Half-space thermoacoustic emission estimate ``|p'| = rho0 c0 |u_ac|`` with
    ``|u_ac| = Omega delta_T / sqrt(2) * (T_hat/T0)``, ``delta_T = sqrt(2 alpha/Omega)``
    (ideal-gas expansion of the oscillating wall thermal boundary layer). Order-of-
    magnitude anchor for the measured incident amplitude, not a certified reference."""

    delta_t = math.sqrt(2.0 * alpha_m2_s / omega_rad_s)
    return rho0_kg_m3 * c0_m_s * (omega_rad_s * delta_t / math.sqrt(2.0)) * (T_hat_K / T0_K)


def decompose_incident_reflected(
    y_m: np.ndarray,
    p_hat: np.ndarray,
    k_rad_m: float,
) -> dict[str, Any]:
    """Least-squares split of ``p_hat(y)`` into ``A_inc e^{-iky} + A_ref e^{+iky}``.

    Returns amplitudes, ``R = A_ref/A_inc``, the relative model residual and the basis
    condition number (the two exponentials are nearly collinear when ``k*span << 1``).
    """

    y_m = np.asarray(y_m, dtype=float)
    p_hat = np.asarray(p_hat, dtype=complex)
    basis = np.column_stack((np.exp(-1j * k_rad_m * y_m), np.exp(+1j * k_rad_m * y_m)))
    coeffs, _, _, singular_values = np.linalg.lstsq(basis, p_hat, rcond=None)
    a_inc, a_ref = complex(coeffs[0]), complex(coeffs[1])
    model = basis @ coeffs
    residual_rel = float(np.linalg.norm(p_hat - model) / max(np.linalg.norm(p_hat), 1e-300))
    r_complex = a_ref / a_inc if a_inc != 0 else complex("nan")
    return {
        "A_inc": a_inc,
        "A_ref": a_ref,
        "R_complex": r_complex,
        "R_abs": abs(r_complex),
        "residual_rel": residual_rel,
        "condition_number": float(singular_values[0] / singular_values[-1]),
        "k_rad_m": float(k_rad_m),
    }


def characteristic_split_reflection(
    y_m: np.ndarray,
    p_hat: np.ndarray,
    v_hat: np.ndarray,
    k_rad_m: float,
    z0_rayl: float,
) -> dict[str, Any]:
    """Per-probe algebraic wave split: ``A_inc=(p_hat+Z0 v_hat)/2, A_ref=(p_hat-Z0 v_hat)/2``.

    Well-conditioned at every probe row regardless of ``k*span`` -- unlike the
    pressure-only two-exponential fit, whose near-collinear basis amplifies systematic
    contamination by its condition number (a rigid-lid control measured a nonphysical
    |R|=1.23 with it, vs 0.82 with this split). ``R`` is referenced to ``y=0`` via
    ``exp(-2iky)`` per row and taken as the componentwise median over rows; the
    row-to-row spread is the internal consistency diagnostic.
    """

    y_m = np.asarray(y_m, dtype=float)
    a_inc = 0.5 * (np.asarray(p_hat, dtype=complex) + z0_rayl * np.asarray(v_hat, dtype=complex))
    a_ref = 0.5 * (np.asarray(p_hat, dtype=complex) - z0_rayl * np.asarray(v_hat, dtype=complex))
    r_rows = (a_ref / a_inc) * np.exp(-2j * k_rad_m * y_m)
    r_med = complex(float(np.median(r_rows.real)) + 1j * float(np.median(r_rows.imag)))
    mid = int(y_m.size // 2)
    return {
        "R_complex": r_med,
        "R_abs": abs(r_med),
        "R_abs_rows_std": float(np.std(np.abs(r_rows))),
        "R_rows": r_rows,
        "A_inc_mid": complex(a_inc[mid]),
        "A_ref_mid": complex(a_ref[mid]),
        "k_rad_m": float(k_rad_m),
        "z0_rayl": float(z0_rayl),
    }




def _solver_config(cfg: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    gas_config_path = Path(cfg["inheritance"]["gas_config_path"])
    gas = load_config(gas_config_path)
    numerics = cfg["numerics"]
    gas["numerics"] = {
        **gas.get("numerics", {}),
        "nx": int(numerics["nx"]),
        "ny": int(numerics["ny"]),
    }
    # P4-1b: explicit, auditable collision overrides (e.g. spectral_correction_seam_detrend).
    # The frozen gas config file itself is never modified; overrides land in the summary.
    overrides = cfg.get("collision_overrides", {}) or {}
    if overrides:
        gas["collision"] = {**gas.get("collision", {}), **overrides}
    gas["case"] = {
        **gas.get("case", {}),
        "name": cfg.get("case", {}).get("name"),
        "phase": "Phase_4",
        "p4_stage": "P4-1",
    }
    return gas, gas_config_path


def run_reflection_measurement(
    *,
    config_path: Path,
    output_root: Path | None = None,
    max_steps_override: int | None = None,
) -> dict[str, Any]:
    cfg = load_config(config_path)
    gas_config, gas_config_path = _solver_config(cfg)
    physical = cfg["physical"]
    numerics = cfg["numerics"]
    probes_cfg = cfg["probes"]
    gates = cfg["gates"]
    open_cfg = cfg["open_boundary"]
    out_root = Path(cfg.get("output", {}).get("results_root", "results/m4")) if output_root is None else output_root

    f_hz = float(physical["frequency_Hz"])
    omega = 2.0 * math.pi * f_hz
    c0 = float(physical["c0_m_s"])
    t_hat_k = float(physical["wall_temperature_hat_K"])
    t0_k = float(gas_config["physical"]["T0_K"])
    alpha0 = float(physical["alpha0_m2_s"])

    solver = GasSolver2D(gas_config)
    mapping = solver.mapping
    dx = float(mapping.lattice.dx_m)
    dt = float(mapping.lattice.dt_s)
    steps_per_period = (1.0 / f_hz) / dt
    ramp_steps = int(round(float(numerics["ramp_periods"]) * steps_per_period))
    settle_steps = int(round(float(numerics["settle_periods"]) * steps_per_period))
    fit_steps = int(round(float(numerics["fit_periods"]) * steps_per_period))
    planned_steps = ramp_steps + settle_steps + fit_steps
    n_steps = planned_steps
    if max_steps_override is not None:
        n_steps = min(n_steps, int(max_steps_override))
    truncated = bool(n_steps < planned_steps)
    sample_interval = int(numerics["sample_interval_steps"])

    rows = np.arange(int(probes_cfg["row_start"]), int(probes_cfg["row_stop"]) + 1, int(probes_cfg["row_step"]))
    if rows[-1] > solver.ny - 4 or rows[0] < 3:
        raise ValueError("probe rows must stay clear of the reconstructed boundary rows")
    y_m = rows.astype(float) * dx

    theta0 = float(mapping.theta_ref_lu)
    rho0_lu = float(mapping.lattice.rho_ref_lu)
    p_ref_lu = rho0_lu * theta0
    solver.initialize_from_macro(rho0_lu, np.zeros((solver.ny, solver.nx, 2)), theta0)
    mass_ref = float(np.sum(solver.f))

    expected_p_pa = expected_thermoacoustic_pressure_pa(
        rho0_kg_m3=float(physical["rho0_kg_m3"]),
        c0_m_s=c0,
        omega_rad_s=omega,
        alpha_m2_s=alpha0,
        T_hat_K=t_hat_k,
        T0_K=t0_k,
    )
    callback = compose_boundary_callbacks(
        make_thermal_drive_wall_callback(
            theta0_lu=theta0,
            theta_hat_lu=t_hat_k / float(mapping.temperature_scale),
            omega_si=omega,
            dt_si=dt,
            ramp_steps=ramp_steps,
        ),
        make_top_open_boundary_callback(
            mean_pressure_relax=float(open_cfg.get("mean_pressure_relax", 0.0)),
            w_lowpass_steps=float(open_cfg.get("w_lowpass_periods", 0.0)) * steps_per_period,
        ),
    )

    n_samples = n_steps // sample_interval
    if n_samples < 8:
        raise ValueError("run too short: need at least 8 samples (raise max_steps or lower sample_interval)")
    n_steps = n_samples * sample_interval
    t_sample = np.empty(n_samples, dtype=float)
    p_rows_lu = np.empty((n_samples, rows.size), dtype=float)
    v_rows_lu = np.empty((n_samples, rows.size), dtype=float)
    p_top_lu = np.empty(n_samples, dtype=float)
    v_top_lu = np.empty(n_samples, dtype=float)

    wall_clock_start = time.perf_counter()
    D = int(mapping.lattice.D)
    S = int(mapping.lattice.S)
    for i_sample in range(n_samples):
        solver.step(sample_interval, boundary_callback=callback)
        t_sample[i_sample] = solver.t_lu * dt
        m_rows = recover_macro(solver.f[rows], solver.g[rows], D=D, S=S, lattice=solver.lattice)
        p_rows_lu[i_sample] = np.mean(m_rows.p, axis=-1)
        v_rows_lu[i_sample] = np.mean(m_rows.u[..., 1], axis=-1)
        m_top = recover_macro(solver.f[-1:], solver.g[-1:], D=D, S=S, lattice=solver.lattice)
        p_top_lu[i_sample] = float(np.mean(m_top.p))
        v_top_lu[i_sample] = float(np.mean(m_top.u[..., 1]))
    wall_clock_s = time.perf_counter() - wall_clock_start

    finite = bool(
        np.isfinite(p_rows_lu).all() and np.isfinite(solver.f).all() and np.isfinite(solver.g).all()
    )
    mass_rel_drift = float(abs(np.sum(solver.f) - mass_ref) / mass_ref)

    # Harmonic fit over the trailing fit window, mean-subtracted per probe (contract §2.3).
    fit_t0 = (ramp_steps + settle_steps) * dt
    if truncated:
        fit_t0 = float(t_sample[n_samples // 2])  # diagnostic fallback: trailing half
    mask = t_sample >= fit_t0
    pressure_scale = float(mapping.pressure_scale)
    p_hat_pa = np.empty(rows.size, dtype=complex)
    for j in range(rows.size):
        series = p_rows_lu[mask, j]
        p_hat_pa[j] = complex_amplitude(t_sample[mask], series - float(np.mean(series)), f_hz) * pressure_scale

    velocity_scale = dx / dt
    v_hat_ms = np.empty(rows.size, dtype=complex)
    for j in range(rows.size):
        series = v_rows_lu[mask, j]
        v_hat_ms[j] = complex_amplitude(t_sample[mask], series - float(np.mean(series)), f_hz) * velocity_scale

    k_si = omega / c0
    z0_si = float(physical["rho0_kg_m3"]) * c0
    char = characteristic_split_reflection(y_m, p_hat_pa, v_hat_ms, k_si, z0_si)
    decomp = decompose_incident_reflected(y_m, p_hat_pa, k_si)   # pressure-only cross-check
    k_sens = {}
    for k_rel in cfg.get("decomposition", {}).get("k_sensitivity_rel", [0.99, 1.01]):
        k_sens[f"k_x{k_rel:g}"] = float(
            characteristic_split_reflection(y_m, p_hat_pa, v_hat_ms, k_si * float(k_rel), z0_si)["R_abs"]
        )
    y_top_m = (solver.ny - 1) * dx
    r_at_top = char["R_complex"] * complex(np.exp(2j * k_si * y_top_m))

    r_gate = float(gates["reflection_abs"])
    r_abs = float(char["R_abs"])
    reflection_passed = bool(finite and not truncated and r_abs < r_gate)
    mass_ok = bool(mass_rel_drift < float(gates["mass_relative_drift_max"]))
    status = "DIAGNOSTIC" if truncated else ("PASSED" if (finite and mass_ok) else "FAILED")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    inherited = cfg.get("inheritance", {})
    payload: dict[str, Any] = {
        "run_id": run_id,
        "status": status,
        "phase": "Phase_4",
        "p4_stage": "P4-1",
        "m4_gate": "NOT_CLAIMED",
        "scope": "P4-1_OPEN_TOP_REFLECTION_10KHZ_NORMAL_INCIDENCE_DX2P6",
        "config_path": str(config_path),
        "config_sha256": sha256_file(config_path),
        "gas_config_path": str(gas_config_path),
        "gas_config_sha256": sha256_file(gas_config_path),
        "collision_overrides": cfg.get("collision_overrides", {}) or {},
        "python": sys.version,
        "platform": platform.platform(),
        "velocity_set": mapping.lattice.velocity_set,
        "Q": int(solver.lattice.q),
        "boundary_y_top": str(open_cfg.get("type", "open_cbc")),
        "mean_pressure_relax": float(open_cfg.get("mean_pressure_relax", 0.0)),
        "w_lowpass_periods": float(open_cfg.get("w_lowpass_periods", 0.0)),
        "boundary_y_bottom": "thermal_grad (production Grad wall, oscillating theta_w drive; Level A pattern)",
        "dx_si": dx,
        "dt_si": dt,
        "nx": int(solver.nx),
        "ny": int(solver.ny),
        "frequency_Hz": f_hz,
        "wall_temperature_hat_K": t_hat_k,
        "expected_thermoacoustic_p_Pa": expected_p_pa,
        "steps": {
            "ramp": ramp_steps,
            "settle": settle_steps,
            "fit": fit_steps,
            "total_run": n_steps,
            "steps_per_period": steps_per_period,
            "truncated_diagnostic": truncated,
        },
        "sample_interval_steps": sample_interval,
        "open_boundary": {
            "type": str(open_cfg.get("type", "open_cbc")),
            "R_abs": r_abs,
            "R_complex_y0_ref": char["R_complex"],
            "R_complex_at_top": r_at_top,
            "R_abs_rows_std": char["R_abs_rows_std"],
            "A_inc_Pa": char["A_inc_mid"],
            "A_ref_Pa": char["A_ref_mid"],
            "gate": "NOT_CLAIMED" if truncated else ("PASSED" if reflection_passed else "FAILED"),
            "gate_threshold_abs": r_gate,
            "incidence": "normal (+y), x-uniform (kx=0)",
            "method": (
                "characteristic split per probe row: A_inc=(p_hat+Z0 v_hat)/2, "
                "A_ref=(p_hat-Z0 v_hat)/2, R=median over rows referenced to y=0"
            ),
        },
        "decomposition": {
            "primary_method": "characteristic_split (p_hat AND v_hat, well-conditioned at every probe)",
            "cross_check_method": "pressure-only two-exponential LS (near-collinear at k*span<<1; "
                                  "rigid-lid control read a nonphysical |R|=1.23 with it -- never the gate)",
            "wave_model": "p_hat(y)=A_inc exp(-iky)+A_ref exp(+iky), y from row-0 center",
            "k_rad_m": float(k_si),
            "k_source": "k = Omega/c0 (ideal); measured sound speed within 0.75% (P2-6)",
            "z0_source": "Z0 = rho0*c0 (reference impedance; 0.75% c error -> ~0.4% R floor)",
            "R_abs_ls_cross_check": float(decomp["R_abs"]),
            "residual_rel_ls": decomp["residual_rel"],
            "condition_number_ls": decomp["condition_number"],
            "R_abs_k_sensitivity": k_sens,
            "probe_rows": rows.tolist(),
            "probe_y_m": {"min": float(y_m[0]), "max": float(y_m[-1]), "n": int(rows.size)},
            "fit_window_s": [float(fit_t0), float(t_sample[-1])],
            "fit_window_definition": "trailing fit_periods window, per-probe mean-subtracted",
        },
        "top_row_diagnostics": {
            "p_prime_final_Pa": float((p_top_lu[-1] - p_ref_lu) * pressure_scale),
            "v_final_m_s": float(v_top_lu[-1] * dx / dt),
            "p_prime_drift_Pa": float((np.mean(p_top_lu[mask]) - p_ref_lu) * pressure_scale),
        },
        "mass_relative_drift": mass_rel_drift,
        "gates": {
            "R_abs<gate": reflection_passed,
            "mass_drift_bounded": mass_ok,
            "no_nan": finite,
        },
        "stability_flags": {"no_nan": finite, "no_clipping_or_floor_used": True},
        "inherited_m3": {
            "decision": str(inherited.get("m3_decision_state", "SCOPED_ACCEPTED_route_a_2026-07-03")),
            "amp_error_band": float(inherited.get("inherited_m3_amp_error_band", 0.054)),
            "config": str(inherited.get("gas_config_path", "")),
            "closure_owner": str(inherited.get("m3_closure_decision", "docs/Phase_3/M3/M3_Closure_Decision.md")),
        },
        "known_risk_boundaries": [
            "single-frequency 10 kHz normal incidence only; oblique/edge radiation not certified (x periodic)",
            "sub-wavelength probe span: near-collinear two-wave basis, conditioning and k-sensitivity reported",
            "thermoacoustic source amplitude anchor is a half-space estimate, not a certified reference",
            "M3 inherited: SCOPED_ACCEPTED (not clear PASS), amplitude band +/-5.4%",
        ],
        "wall_clock_s": wall_clock_s,
    }
    safe = _json_safe(payload)
    digest_core = {k: v for k, v in safe.items() if k not in VOLATILE_DIGEST_KEYS}
    safe["summary_digest"] = summary_payload_digest(digest_core)
    safe["summary_digest_scope"] = "physics_core; excludes " + ", ".join(VOLATILE_DIGEST_KEYS)

    h5_path = out_dir / "timeseries.h5"
    meta = phase3_hdf5_metadata(
        mapping,
        case_name=str(cfg.get("case", {}).get("name", "phase4_open_top_reflection_10k")),
        level="P4-1",
        pass_fail=payload["open_boundary"]["gate"],
        config_sha256=safe["config_sha256"],
        extra={
            "schema_name": "phase4_run",
            "phase": "Phase_4",
            "inherited_m3_decision": safe["inherited_m3"]["decision"],
            "inherited_m3_error_band_amp": safe["inherited_m3"]["amp_error_band"],
            "frequency_Hz": f_hz,
            "config_source": str(gas_config_path),
            "wall_bc": "thermal_grad",
            "open_boundary_type": safe["boundary_y_top"],
            "open_boundary_reflection_target": r_gate,
            "no_clipping_or_floor_used": True,
        },
    )
    write_phase3_run_hdf5(
        h5_path,
        meta=meta,
        time_si=t_sample,
        groups={
            "probes": {
                "rows": rows,
                "y_m": y_m,
                "pressure_prime_Pa": (p_rows_lu - p_ref_lu) * pressure_scale,
                "p_top_prime_Pa": (p_top_lu - p_ref_lu) * pressure_scale,
                "v_top_m_s": v_top_lu * dx / dt,
            },
            "reflection": {
                "incident_hat": char["A_inc_mid"],
                "reflected_hat": char["A_ref_mid"],
                "R_complex": char["R_complex"],
                "R_abs": r_abs,
                "R_rows": np.asarray(char["R_rows"]),
                "R_abs_ls_cross_check": float(decomp["R_abs"]),
                "method": "characteristic_split_primary_ls_cross_check",
                "probe_locations_m": y_m,
                "p_hat_Pa": p_hat_pa,
                "v_hat_m_s": v_hat_ms,
                "fit_window_s": np.asarray([fit_t0, float(t_sample[-1])]),
                "convention": PHASE3_COMPLEX_CONVENTION,
            },
        },
    )
    safe["artifacts"] = {"hdf5": h5_path.name}
    (out_dir / "summary.json").write_text(json.dumps(safe, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "report.md").write_text(_render_report(safe), encoding="utf-8")
    return safe


def _render_report(p: dict[str, Any]) -> str:
    ob = p["open_boundary"]
    dc = p["decomposition"]
    return "\n".join([
        "# Phase_4 P4-1 Open-Top Boundary Reflection (10 kHz normal incidence)",
        "",
        f"- run_id: `{p['run_id']}`  status: **{p['status']}**",
        f"- open-boundary gate (|R|<{ob['gate_threshold_abs']:g}): **{ob['gate']}**  |R| = {ob['R_abs']:.4f}",
        f"- boundary_y_top: `{p['boundary_y_top']}` (mean_pressure_relax={p['mean_pressure_relax']:g})",
        f"- m4_gate: {p['m4_gate']} (P4-1 alone never claims M4)",
        f"- summary_digest: `{p['summary_digest']}`",
        "",
        "## Decomposition (characteristic split primary)",
        f"- A_inc = {ob['A_inc_Pa']['abs']:.4g} Pa (thermoacoustic estimate ~{p['expected_thermoacoustic_p_Pa']:.3g} Pa), "
        f"A_ref = {ob['A_ref_Pa']['abs']:.4g} Pa; row spread of |R|: {ob['R_abs_rows_std']:.4f}",
        f"- pressure-only LS cross-check |R|: {dc['R_abs_ls_cross_check']:.4f} "
        f"(residual {dc['residual_rel_ls']:.3e}, condition {dc['condition_number_ls']:.1f}; never the gate)",
        f"- |R| k-sensitivity: {dc['R_abs_k_sensitivity']}",
        f"- probes: {dc['probe_y_m']['n']} rows, y in [{dc['probe_y_m']['min']:.3e}, {dc['probe_y_m']['max']:.3e}] m; "
        f"fit window {dc['fit_window_s']} s",
        "",
        "## Stability / sanity",
        f"- no NaN: {p['stability_flags']['no_nan']}   mass relative drift: {p['mass_relative_drift']:.3e} "
        f"(open system bound, gate: {p['gates']['mass_drift_bounded']})",
        f"- top-row mean p' over fit window: {p['top_row_diagnostics']['p_prime_drift_Pa']:.3e} Pa",
        "",
        "## Inherited M3 boundary",
        f"- {p['inherited_m3']['decision']}; amplitude error band +/-{p['inherited_m3']['amp_error_band']:.3f}; "
        f"config {p['inherited_m3']['config']}",
        "",
        "Known risk boundaries: " + "; ".join(p["known_risk_boundaries"]),
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase_4 P4-1 open-top boundary reflection measurement.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="diagnostic truncation of the run length (marks the summary DIAGNOSTIC; gate stays NOT_CLAIMED)",
    )
    args = parser.parse_args()
    payload = run_reflection_measurement(
        config_path=args.config,
        output_root=args.output_root,
        max_steps_override=args.max_steps,
    )
    ob = payload["open_boundary"]
    print(
        f"status={payload['status']}; open_boundary.gate={ob['gate']}; |R|={ob['R_abs']:.4f} "
        f"(gate {ob['gate_threshold_abs']:g}); wrote results/.../{payload['run_id']}; "
        f"digest={payload['summary_digest']}"
    )
    return 0 if ob["gate"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
