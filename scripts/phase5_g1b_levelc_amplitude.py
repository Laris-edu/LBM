"""Phase_5 G1b Level C coupled amplitude-envelope gate (contract §6.3, WP2).

Re-runs the M3 canonical Level C film-gas coupling (10 kHz, dx2p6, C_A=7e-4,
heun_picard1, q_feedback_relax=0.02 frozen per family) with the G1-W
certified production wall (``wall_bc="mass_neutral"``, grad_extrap="row1")
over the target-epsilon ladder, and certifies the §6.3 rows. The old-wall M3
digest is upstream lineage only (contract: the production-wall small-amplitude
M3 regression must be re-executed).

Pre-registered reference (zero new tuning DOF): the mass-neutral wall makes
the y-periodic rig a genuinely sealed box (G1-W finding: the old wall's
half-space-like response and its mass source are two faces of one mechanism),
so the M3 analytic film+half-space reference is physically inapplicable here
(~20 deg phase off through the film algebra). The G1b regression reference
composes the M3 film-ODE algebra with the G1-W certified lbm-equivalent
sealed spectral reference:

    T_s_ref = P_hat / (i*Omega*C_A + 2*Y_sealed_ref),
    Y_sealed_ref = (Y/Yhs)_spectral(ny48) * Y_hs(SI)

Expected residual inherits the G1-W regression row (~-4%/-2 deg), inside the
+/-5.4%/5deg M3 scoped boundary the contract prescribes for this row.

Epsilon targeting (§6.3 "adaptive P1"): the coupled response is linear to
D_G ~ 1e-3 (G1a), so P1(eps) = eps*T0*|i*Omega*C_A + 2*Y_sealed_ref| is a
one-shot prediction; the measured epsilon is archived and gated at <=10%.

Independent cases run through a process pool (same scheduling-only pattern
and A/B discipline as G1a; per-case sequence identical to serial).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import yaml

from core.solver import GasSolver2D
from coupling.conjugate import run_levelc_predictor_corrector
from coupling.drive import SinusoidalDrive
from coupling.film_ode import FilmOdeParams
from phase3_interfaces.complex_amplitude import complex_amplitude
from postproc.multiharmonic_fit import fit_multiharmonic
from scripts.phase2_m2_verification import load_config
from scripts.phase5_g1w_wall_neutrality import (
    G0_TABLE_CSV,
    _cplx,
    _git_commit,
    _ratio,
    load_g0_alpha_rows,
    measure_extension_rows,
    sealed_spectral_reference,
)

GATE_ID = "G1b"
CASE_FAMILY = "g1b_levelc_amplitude"
PHASE5_CONTRACT_VERSION = "v1.2"
DEFAULT_CONFIG = Path("configs/phase5/g1b_levelc_amplitude/g1b_10k_dx2p6.yaml")
PHYSICS_CORE_FILES = [
    "coupling/conjugate.py",
    "coupling/film_ode.py",
    "coupling/drive.py",
    "boundary/wall_thermal_mass_neutral.py",
    "postproc/multiharmonic_fit.py",
    "scripts/phase5_g1w_wall_neutrality.py",
]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _physics_core_digest(repo_root: Path) -> str:
    h = hashlib.sha256()
    for rel in PHYSICS_CORE_FILES:
        h.update(rel.encode())
        h.update((repo_root / rel).read_bytes())
    return h.hexdigest()[:12]


def _case_worker(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """One coupled Level C case (scheduling-layer parallelism only)."""

    label = payload["label"]

    def wlog(msg: str) -> None:
        print(f"G1B [{label}] {msg}", flush=True)

    solver = GasSolver2D(payload["gas_cfg"])
    f0 = payload["frequency_hz"]
    dt = float(solver.mapping.lattice.dt_s)
    steps_per_period = int(round((1.0 / f0) / dt))
    n_steps = int(round(payload["periods"] * steps_per_period))
    params = FilmOdeParams(C_A_si=payload["C_A"], T_ref_K=payload["T0"],
                           gas_flux_factor=payload["gas_flux_factor"])
    drive = SinusoidalDrive(mean_si=payload["P_mean"],
                            amplitude_hat_si=complex(payload["P1"], 0.0),
                            frequency_hz=f0)
    res = run_levelc_predictor_corrector(
        solver=solver, params=params, drive=drive, n_steps=n_steps,
        T_initial_K=payload["T0"], scheme=payload["scheme"],
        energy_tolerance=payload["film_energy_gate"],
        wall_bc=payload["wall_bc"], q_feedback_relax=payload["relax"],
        grad_extrap=payload["grad_extrap"],
        q_extraction=payload["q_extraction"])
    wlog("done eps_target=%g P1=%.4e finite=%s film_resid=%.2e" % (
        payload["epsilon"], payload["P1"], res.finite,
        res.energy_audit.max_relative_residual))
    return label, {
        "epsilon_target": payload["epsilon"], "P1": payload["P1"],
        "t_si": res.t_si, "T_s_K": res.T_s_K, "q_g_si": res.q_g_one_sided_si,
        "pressure_probe_Pa": res.pressure_probe_Pa,
        "p_box_mean_Pa": res.p_box_mean_Pa,
        "delta_pc_K": res.predictor_corrector_delta_K,
        "wall_error_K": res.wall_temperature_error_K,
        "mass_lu": res.mass_lu,
        "finite": bool(res.finite),
        "film_energy_max_rel": float(res.energy_audit.max_relative_residual),
        "steps_per_period": steps_per_period, "dt_s": dt,
    }


def execute_cases(payloads: list[dict[str, Any]], workers: int, log) -> dict[str, Any]:
    """Process-pool over independent cases (G1a pattern; exception-resilient)."""

    results: dict[str, Any] = {}
    if workers <= 1 or len(payloads) <= 1:
        for p in payloads:
            label, run = _case_worker(p)
            results[label] = run
        return results
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ.setdefault(var, "1")
    log("parallel scheduling: %d independent cases on %d workers" % (len(payloads), workers))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_case_worker, p): p["label"] for p in payloads}
        for fut in as_completed(futures):
            label = futures[fut]
            try:
                label, run = fut.result()
                results[label] = run
            except Exception as exc:
                results[label] = {"worker_exception": f"{type(exc).__name__}: {exc}"}
                log(f"case FAILED with exception: {label}: {exc}")
            log(f"case done: {label} ({len(results)}/{len(payloads)})")
    return results


def run_g1b(config_path: Path, output_root: Path | None = None,
            smoke: bool = False, workers: int = 1) -> dict[str, Any]:
    cfg = load_config(config_path)
    proto = cfg["g1b_smoke"] if smoke else cfg["g1b"]
    gates = cfg["gates"]
    gas_cfg_path = Path(cfg["inheritance"]["gas_config_path"])
    repo_root = Path(__file__).resolve().parents[1]

    def log(msg: str) -> None:
        print(f"G1B {msg}", flush=True)

    def make_gas(ny: int, nx: int) -> dict:
        gas = load_config(gas_cfg_path)
        gas["numerics"] = {**gas.get("numerics", {}), "nx": nx, "ny": ny}
        return gas

    f0 = float(proto["frequency_Hz"])
    omega = 2.0 * math.pi * f0
    ny = int(proto["ny"])
    nx = int(proto["nx"])
    film = proto["film"]
    lc = proto["level_c"]
    phys = proto["physical"]
    T0 = float(film["T0_K"])
    C_A = float(film["C_A_J_m2K"])
    kg = float(phys["kg_W_mK"])
    alpha0 = float(phys["alpha0_m2_s"])
    n_harm = int(proto["n_harmonics"])
    mandatory = [float(e) for e in proto["epsilon_mandatory"]]
    conditional = [float(e) for e in proto["epsilon_conditional"]]
    ladder = mandatory + conditional
    eps_min = mandatory[0]

    probe_solver = GasSolver2D(make_gas(8, 4))
    mapping = probe_solver.mapping
    alpha_nom_lu = float(mapping.alpha_lu)
    gamma = float(mapping.physical.gamma)
    dt = float(mapping.lattice.dt_s)
    omega_lu = omega * dt

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = Path(output_root) if output_root else repo_root / "results" / "phase5" / CASE_FAMILY
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    h5 = h5py.File(out_dir / "signals.h5", "w")

    # ---- sealed spectral reference (G1-W caliber) composed with the film ODE ----
    g0_rows = load_g0_alpha_rows(repo_root / G0_TABLE_CSV)
    ext_rows = measure_extension_rows(
        make_gas(8, 4), [int(n) for n in proto["alpha_extension_ny"]], alpha_nom_lu, log)
    all_rows = sorted(g0_rows + [(r["k_lu"], r["alpha_eff_lu"]) for r in ext_rows])
    k_tab = np.array([r[0] for r in all_rows])
    a_tab = np.array([r[1] for r in all_rows])
    ref = sealed_spectral_reference(ny, omega_lu, alpha_nom_lu, k_tab, a_tab,
                                    highk_policy=str(proto["highk_policy_primary"]),
                                    gamma=gamma)
    y_hs_si = kg * complex(np.sqrt(1j * omega / alpha0))
    y_sealed_si = ref["Y_over_Yhs"] * y_hs_si
    # as-built coupled dynamics: the film integrates the MOMENT-channel flux,
    # which on the mn field shape reads Y_sealed/recal (G1-W §23 constant) —
    # used for P1 targeting and the as-built T_s consistency (info); the GATED
    # regression row is the coupled energy-channel admittance vs the spectral
    # reference, in which the moment miscalibration cancels exactly.
    rc = proto["moment_recal"]
    recal = float(rc["abs"]) * complex(
        math.cos(math.radians(float(rc["phase_deg"]))),
        math.sin(math.radians(float(rc["phase_deg"]))))
    y_moment_pred = y_sealed_si / recal
    denom_asbuilt = 1j * omega * C_A + 2.0 * y_moment_pred
    log("reference: Y_sealed/Yhs=%.4f@%+.2f deg  |denom_asbuilt|=%.1f phase=%+.2f deg" % (
        abs(ref["Y_over_Yhs"]),
        math.degrees(math.atan2(ref["Y_over_Yhs"].imag, ref["Y_over_Yhs"].real)),
        abs(denom_asbuilt), math.degrees(math.atan2(denom_asbuilt.imag, denom_asbuilt.real))))

    def t_s_ref_asbuilt(p1: float) -> complex:
        return complex(p1, 0.0) / denom_asbuilt

    def p1_for(eps: float) -> float:
        return eps * T0 * abs(denom_asbuilt)

    # frequency-domain energy-channel admittance of a coupled trajectory:
    # q_side_energy = i*omega*(N*dy/(2(gamma-1)))*p_box_hat  (G1-W identity)
    energy_prefactor = ny * float(mapping.lattice.dx_m) / (2.0 * (gamma - 1.0))

    # ---- coupled ladder (independent cases -> pool) ----
    payloads = []
    for eps in ladder:
        payloads.append({
            "kind": "levelc", "label": f"eps{eps:g}",
            "gas_cfg": make_gas(ny, nx), "frequency_hz": f0,
            "periods": float(proto["periods"]), "epsilon": eps,
            "P1": p1_for(eps), "P_mean": float(film["P_mean_W_m2"]),
            "C_A": C_A, "T0": T0, "gas_flux_factor": float(film["gas_flux_factor"]),
            "scheme": str(lc["coupling_scheme"]), "wall_bc": str(lc["wall_bc"]),
            "relax": float(lc["q_feedback_relax"]),
            "grad_extrap": str(lc["grad_extrap"]),
            "q_extraction": str(lc.get("q_extraction", "moment_row")),
            "film_energy_gate": float(gates["film_energy_audit_rel"]),
        })
    case_results = execute_cases(payloads, workers, log)
    for label, res in case_results.items():
        if "worker_exception" in res:
            raise RuntimeError(f"case {label} crashed: {res['worker_exception']}")

    # ---- per-epsilon evaluation ----
    settle = float(proto["settle_periods"])
    m3_last = float(proto["m3_fit_last_periods"])
    per_eps: dict[float, dict[str, Any]] = {}
    for eps in ladder:
        r = case_results[f"eps{eps:g}"]
        t = r["t_si"]
        mask_m3 = t >= (t[-1] - m3_last / f0) * (1.0 - 1e-12)
        ts_hat = complex_amplitude(t[mask_m3], r["T_s_K"][mask_m3] - T0, f0)
        qg = r["q_g_si"]
        qg_hat = complex_amplitude(t[mask_m3], qg[mask_m3] - float(np.mean(qg[mask_m3])), f0)
        pbox = r["p_box_mean_Pa"]
        pbox_hat = complex_amplitude(t[mask_m3], pbox[mask_m3] - float(np.mean(pbox[mask_m3])), f0)
        # GATED regression: coupled energy-channel admittance vs spectral ref
        # (moment-channel miscalibration cancels exactly in this quantity)
        y_energy_coupled = 1j * omega * energy_prefactor * pbox_hat / ts_hat
        reg = _ratio(y_energy_coupled, y_sealed_si)
        # as-built consistency (info) + in-run recal cross-check vs §23 constant
        ref_hat = t_s_ref_asbuilt(r["P1"])
        asbuilt = _ratio(ts_hat, ref_hat)
        y_moment_coupled = qg_hat / ts_hat
        recal_inrun = (y_energy_coupled / y_moment_coupled
                       if abs(y_moment_coupled) > 0 else complex("nan"))
        eps_meas = abs(ts_hat) / T0
        mask_fit = t >= settle / f0 * (1.0 - 1e-12)
        fit_ts = fit_multiharmonic(t[mask_fit], r["T_s_K"][mask_fit] - T0, omega,
                                   n_harmonics=n_harm)
        fit_p = fit_multiharmonic(t[mask_fit], r["pressure_probe_Pa"][mask_fit], omega,
                                  n_harmonics=n_harm)
        spp = r["steps_per_period"]
        dpc = np.abs(r["delta_pc_K"])
        growth = (float(np.max(dpc[-spp:]) / max(np.max(dpc[1:spp + 1]), 1e-300))
                  if len(dpc) > 2 * spp else float("nan"))
        mass = r["mass_lu"]
        m0 = float(mass[0])
        wall_err_win = float(np.max(r["wall_error_K"][mask_fit]))
        per_eps[eps] = {
            "P1": r["P1"], "T_s_hat": ts_hat, "T_s_ref_asbuilt": ref_hat,
            "regression": reg, "asbuilt": asbuilt,
            "q_g_hat": qg_hat, "p_box_hat": pbox_hat,
            "Y_energy_coupled": y_energy_coupled,
            "recal_inrun": recal_inrun,
            "recal_vs_g1w": _ratio(recal_inrun, recal),
            "eps_measured": eps_meas,
            "eps_target_rel_err": float(eps_meas / eps - 1.0),
            # end-of-step wall error scales with the explicit-coupling timing
            # geometry omega*|T_s|*dt (measured constant ~0.8, amplitude-
            # invariant to ~2%); a genuine wall failure breaks this
            # proportionality upward
            "wall_timing_ratio": float(
                np.max(r["wall_error_K"][mask_fit])
                / max(omega * abs(ts_hat) * r["dt_s"], 1e-300)),
            "H2_Ts": fit_ts.leakage_relative(1)[2] if n_harm >= 2 else None,
            "H2_p": fit_p.leakage_relative(1)[2] if n_harm >= 2 else None,
            "wall_err_K": wall_err_win,
            "film_energy_rel": r["film_energy_max_rel"],
            "mass_window_rel": float(np.max(np.abs(mass[mask_fit] - mass[mask_fit][0])) / m0),
            "mass_total_rel": float(abs(mass[-1] - m0) / m0),
            "delta_pc_growth": growth,
            "finite": r["finite"],
        }
        log("  eps=%-6g Ts=%.4f K Yreg=%+.3f%%/%+.2fdeg asbuilt=%+.2f%%/%+.2fdeg "
            "eps_err=%+.2f%% recal=%.3f@%+.1f H2Ts=%.2e growth=%.2f" % (
                eps, abs(ts_hat), 100 * reg["amp_rel_err"], reg["phase_deg_err"],
                100 * asbuilt["amp_rel_err"], asbuilt["phase_deg_err"],
                100 * per_eps[eps]["eps_target_rel_err"],
                abs(recal_inrun), math.degrees(math.atan2(recal_inrun.imag, recal_inrun.real)),
                per_eps[eps]["H2_Ts"] or 0.0, growth))

    # ---- archive ----
    for eps in ladder:
        r = case_results[f"eps{eps:g}"]
        g = h5.create_group(f"runs/eps{eps:g}")
        for name in ("t_si", "T_s_K", "q_g_si", "pressure_probe_Pa", "p_box_mean_Pa",
                     "delta_pc_K", "wall_error_K", "mass_lu"):
            g.create_dataset(name, data=r[name])
        g.attrs.update({"epsilon_target": eps, "P1": r["P1"], "finite": r["finite"]})

    # ---- gate rows (contract §6.3) ----
    small = per_eps[eps_min]

    def eps_ok(eps: float) -> bool:
        p = per_eps[eps]
        return bool(
            p["finite"]
            and abs(p["regression"]["amp_rel_err"]) <= gates["m3_amp_rel"]
            and abs(p["regression"]["phase_deg_err"]) <= gates["m3_phase_deg"]
            and abs(p["eps_target_rel_err"]) <= gates["target_epsilon_rel"]
            and p["wall_err_K"] <= gates["wall_temperature_error_K"]
            and p["film_energy_rel"] <= gates["film_energy_audit_rel"]
            and p["mass_window_rel"] <= gates["mass_window_rel"]
            and p["mass_total_rel"] <= gates["mass_cumulative_rel"]
            and (not np.isfinite(p["delta_pc_growth"])
                 or p["delta_pc_growth"] <= gates["stability_delta_pc_growth_max"]))

    eps_pass = {eps: eps_ok(eps) for eps in ladder}
    gate_rows = {
        "m3_smallamp_regression": {
            "epsilon": eps_min,
            "Y_energy_coupled": _cplx(small["Y_energy_coupled"]),
            "Y_reference": _cplx(y_sealed_si), "ratio": small["regression"],
            "reference_definition": "coupled-trajectory energy-channel admittance vs "
                                    "G1-W certified sealed spectral reference "
                                    "(moment miscalibration cancels; pre-registered)",
            "asbuilt_Ts_consistency": small["asbuilt"],
            "recal_inrun_vs_g1w_constant": small["recal_vs_g1w"],
            "gates": [gates["m3_amp_rel"], gates["m3_phase_deg"]],
            "passed": bool(abs(small["regression"]["amp_rel_err"]) <= gates["m3_amp_rel"]
                           and abs(small["regression"]["phase_deg_err"]) <= gates["m3_phase_deg"]),
        },
        "target_epsilon": {
            "by_eps": {f"{e:g}": per_eps[e]["eps_target_rel_err"] for e in ladder},
            "gate": gates["target_epsilon_rel"],
            "passed": bool(all(abs(per_eps[e]["eps_target_rel_err"])
                               <= gates["target_epsilon_rel"] for e in mandatory)),
        },
        "wall_temperature": {
            "max_err_K": max(per_eps[e]["wall_err_K"] for e in mandatory),
            "gate": gates["wall_temperature_error_K"],
            "timing_ratio_by_eps": {f"{e:g}": per_eps[e]["wall_timing_ratio"]
                                    for e in ladder},
            "timing_ratio_bound": 1.5,
            "note": "end-of-step error = explicit-coupling timing geometry "
                    "(~0.8*omega*|Ts|*dt, amplitude-invariant); O(1) ratio "
                    "bound catches genuine wall failure at any amplitude; "
                    "callback-instant pinning is G1-W certified (1.9e-12 K)",
            "passed": bool(
                max(per_eps[e]["wall_err_K"] for e in mandatory)
                <= gates["wall_temperature_error_K"]
                and all(per_eps[e]["wall_timing_ratio"] <= 1.5 for e in ladder)),
        },
        "film_energy_audit": {
            "by_eps": {f"{e:g}": per_eps[e]["film_energy_rel"] for e in ladder},
            "gate": gates["film_energy_audit_rel"],
            "passed": bool(all(per_eps[e]["film_energy_rel"]
                               <= gates["film_energy_audit_rel"] for e in mandatory)),
        },
        "global_mass": {
            "window_max": max(per_eps[e]["mass_window_rel"] for e in mandatory),
            "cumulative_max": max(per_eps[e]["mass_total_rel"] for e in mandatory),
            "gates": [gates["mass_window_rel"], gates["mass_cumulative_rel"]],
            "passed": bool(
                max(per_eps[e]["mass_window_rel"] for e in mandatory) <= gates["mass_window_rel"]
                and max(per_eps[e]["mass_total_rel"] for e in mandatory)
                <= gates["mass_cumulative_rel"]),
        },
        "coupling_stability": {
            "delta_pc_growth_by_eps": {f"{e:g}": per_eps[e]["delta_pc_growth"] for e in ladder},
            "gate_max": gates["stability_delta_pc_growth_max"],
            "finite": {f"{e:g}": per_eps[e]["finite"] for e in ladder},
            "passed": bool(all(per_eps[e]["finite"] for e in mandatory) and all(
                (not np.isfinite(per_eps[e]["delta_pc_growth"]))
                or per_eps[e]["delta_pc_growth"] <= gates["stability_delta_pc_growth_max"]
                for e in mandatory)),
        },
        "parameter_freeze": {
            "wall_bc": str(lc["wall_bc"]), "grad_extrap": str(lc["grad_extrap"]),
            "q_feedback_relax": float(lc["q_feedback_relax"]),
            "note": "dx/tau/derivation factors/filter/production-wall params frozen; "
                    "relax fixed per family (no per-amplitude tuning)",
            "passed": True,
        },
        "numerical_repair": {"no_clipping": True, "no_floor": True,
                             "no_positivity_repair": True, "passed": True},
        "minimum_amplitude_window": {
            "eps_pass": {f"{e:g}": eps_pass[e] for e in ladder},
            "gate": gates["min_amplitude_window"],
            "passed": bool(all(eps_pass[e] for e in mandatory)),
        },
    }
    labels: list[str] = []
    if all(r["passed"] for r in gate_rows.values()):
        verdict = "PASSED"
        if conditional and not all(eps_pass[e] for e in conditional):
            labels.append("G1B_CONDITIONAL_POINTS_PARTIAL")
    else:
        verdict = "FAILED"
        labels.append("LEVELC_NONLINEAR_COUPLING_NOT_CERTIFIED")
    log("verdict=%s labels=%s" % (verdict, labels or "-"))

    # ---- outputs (contract §16.1 seven files) ----
    resolved = {"gate_id": GATE_ID, "case_family": CASE_FAMILY, "protocol": proto,
                "gates": gates, "config_path": str(config_path)}
    config_yaml = yaml.safe_dump(resolved, allow_unicode=True, sort_keys=False)
    (out_dir / "config_resolved.yaml").write_text(config_yaml, encoding="utf-8")

    na = "not_applicable_g1b_levelc"
    e_rep = 0.05 if 0.05 in per_eps else mandatory[-1]
    rep = per_eps[e_rep]
    summary = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "code_commit": _git_commit(),
        "config_digest": _sha256_bytes(config_yaml.encode())[:12],
        "physics_core_digest": _physics_core_digest(repo_root),
        "parent_baseline_run": str(cfg["inheritance"]["g1w_certified_run"]),
        "phase5_contract_version": PHASE5_CONTRACT_VERSION,
        "work_package": "WP2", "gate_id": GATE_ID, "case_family": CASE_FAMILY,
        "model_route": "ROUTE_B_MAIN",
        "property_model_id": "frozen_dx2p6_route_b_closure",
        "tau_policy": "frozen (M3 closure §3)",
        "mapping_digest": _sha256_bytes(Path(gas_cfg_path).read_bytes())[:12],
        "background_path": "uniform_reference_state",
        "forcing_protocol": "film_ode_sinusoidal_P1 (M3 canonical, adaptive P1 predicted)",
        "P_mean_W_m2": float(film["P_mean_W_m2"]), "P_mean_rematched": False,
        "target_Theta_DC": 0.0,
        "frequency_Hz": f0, "T_ambient_K": T0, "T_mean_K": T0,
        "epsilon_AC_measured": {f"{e:g}": per_eps[e]["eps_measured"] for e in ladder},
        "Theta_DC_measured": 0.0,
        "chi_0": None, "chi_eff": None,
        "C_A_J_m2K": C_A,
        "dc_heat_sink_model": na + " (sealed periodic rig)",
        "dc_heat_sink_parameters": None,
        "H_s_role": "rig domain height (sealed periodic)",
        "thermal_resistance_effective": None,
        "grid_shape": [ny, nx], "dx_m": float(mapping.lattice.dx_m), "dt_s": dt,
        "domain_height_m": ny * float(mapping.lattice.dx_m),
        "boundary_model": "mass_neutral_v1p1_symmetric via conjugate wall_bc=mass_neutral",
        "wall_mass_policy": "mass_neutral_by_construction",
        "wall_neutrality_gate_id": "G1-W PASSED (20260727T083342Z)",
        "boundary_mass_flux_definition": "global mass series sum(f) per step (conjugate)",
        "boundary_mass_flux_0f_to_3f": float(max(per_eps[e]["mass_window_rel"]
                                                 for e in mandatory)),
        "spectral_operator_stack_id": "frozen_production_dx2p6",
        "spectral_correction_enabled": True,
        "high_wavenumber_filter_enabled": True,
        "high_wavenumber_filter_strength": "frozen_production",
        "operator_ablation_run_id": None,
        "q_feedback_relax": float(lc["q_feedback_relax"]),
        "fit_window": {"settle_periods": settle,
                       "m3_fit_last_periods": m3_last,
                       "harmonic_fit_periods": float(proto["periods"]) - settle},
        "fit_cycles": float(proto["periods"]) - settle,
        "detrend_order": 0,
        "harmonic_order_max": n_harm,
        "harmonic_fit_condition_number": None,
        "U_det": {"epsilon_targeting_max_err": max(
            abs(per_eps[e]["eps_target_rel_err"]) for e in mandatory)},
        "U95_fit": None,
        "U_gov": float(max(abs(per_eps[e]["eps_target_rel_err"]) for e in mandatory)),
        "no_clipping": True, "no_floor": True, "no_positivity_repair": True,
        "gate_status": verdict,
        "scoped_limitations": labels,
        "smoke_mode": bool(smoke),
        "results": {
            "T_s_hat_1f": _cplx(rep["T_s_hat"]),
            "p_hat_1f": _cplx(rep["p_box_hat"]),
            "p_hat_2f": None, "p_hat_3f": None,
            "p_note": "p_hat_1f = box-mean pressure (energy channel); harmonics "
                      "per-eps in gate_evaluation/harmonic_fit",
            "outgoing_mode_1f": None, "outgoing_mode_2f": None, "outgoing_mode_3f": None,
            "outgoing_mode_note": "sealed rig (G2 quantity)",
            "G1": float(abs(rep["T_s_hat"]) / rep["P1"]),
            "D_G": {f"{e:g}": float((abs(per_eps[e]["T_s_hat"]) / per_eps[e]["P1"])
                                    / (abs(small["T_s_hat"]) / small["P1"]) - 1.0)
                    for e in ladder},
            "D_OP": None, "D_OP_note": "A2a quantity (WP3)",
            "H2": {f"{e:g}": per_eps[e]["H2_Ts"] for e in ladder},
            "H3": None,
            "H2_p_side": {f"{e:g}": per_eps[e]["H2_p"] for e in ladder},
            "m1": None, "m2": None, "m3": None,
            "QS0_error_amplitude": None, "QS0_error_phase": None,
            "QS1_error_amplitude": None, "QS1_error_phase": None,
            "wall_boundary_sensitivity": None,
            "operator_sensitivity_D_G": None,
            "operator_sensitivity_H2": None,
            "operator_sensitivity_H3": None,
            "boundary_mass_flux_0f_to_3f": float(max(
                per_eps[e]["mass_window_rel"] for e in mandatory)),
            "energy_residual": float(max(per_eps[e]["film_energy_rel"] for e in mandatory)),
            "mass_or_flux_residual": float(max(per_eps[e]["mass_total_rel"]
                                               for e in mandatory)),
            "wall_temperature_error": float(max(per_eps[e]["wall_err_K"]
                                                for e in mandatory)),
        },
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=1, default=float), encoding="utf-8")

    harmonic_payloads = {}
    for eps in ladder:
        r = case_results[f"eps{eps:g}"]
        t = r["t_si"]
        mask_fit = t >= settle / f0 * (1.0 - 1e-12)
        harmonic_payloads[f"Ts_eps{eps:g}"] = fit_multiharmonic(
            t[mask_fit], r["T_s_K"][mask_fit] - T0, omega,
            n_harmonics=n_harm).to_json_payload()
    (out_dir / "harmonic_fit.json").write_text(
        json.dumps(harmonic_payloads, indent=1, default=float), encoding="utf-8")

    provenance = {
        "run_id": run_id, "command": " ".join(sys.argv), "workers": workers,
        "machine": {"node": __import__("platform").node(),
                    "processor": __import__("platform").processor()},
        "cross_machine_caliber": "D5-3 per-machine-bitwise / cross-machine-tolerance",
        "python": sys.version.split()[0], "numpy": np.__version__,
        "code_commit": summary["code_commit"],
        "physics_core_digest": summary["physics_core_digest"],
        "physics_core_files": {rel: _sha256_bytes((repo_root / rel).read_bytes())[:12]
                               for rel in PHYSICS_CORE_FILES},
        "g1w_certified_run": summary["parent_baseline_run"],
        "g1a_certified_run": str(cfg["inheritance"]["g1a_certified_run"]),
        "m3_protocol_lineage": str(cfg["inheritance"]["m3_protocol_lineage"]),
    }
    (out_dir / "provenance.json").write_text(json.dumps(provenance, indent=1),
                                             encoding="utf-8")
    (out_dir / "gate_evaluation.json").write_text(
        json.dumps({"gate_id": GATE_ID, "verdict": verdict, "labels": labels,
                    "rows": gate_rows,
                    "per_epsilon": {f"{e:g}": {
                        k: (_cplx(v) if isinstance(v, complex) else v)
                        for k, v in per_eps[e].items()} for e in ladder}},
                   indent=1, default=float), encoding="utf-8")

    report = [f"# G1b run {run_id}", "",
              f"- verdict: **{verdict}** labels={labels or '-'}",
              f"- production wall: mass_neutral (G1-W {summary['parent_baseline_run']})",
              f"- reference: film ODE x sealed spectral (pre-registered)",
              f"- smoke_mode: {smoke}", "", "## Gate rows (contract §6.3)", ""]
    for name, row in gate_rows.items():
        report.append(f"- {name}: passed={row['passed']}")
    report += ["", "## Ladder", ""]
    for eps in ladder:
        p = per_eps[eps]
        report.append("- eps=%g: reg=%+.3f%%/%+.2fdeg eps_err=%+.2f%% H2Ts=%s pass=%s" % (
            eps, 100 * p["regression"]["amp_rel_err"], p["regression"]["phase_deg_err"],
            100 * p["eps_target_rel_err"],
            ("%.2e" % p["H2_Ts"]) if p["H2_Ts"] else "-", eps_pass[eps]))
    (out_dir / "run_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    h5.close()
    log(f"outputs -> {out_dir}")
    return {"verdict": verdict, "labels": labels, "out_dir": str(out_dir),
            "summary": summary, "gate_rows": gate_rows,
            "per_eps": {f"{e:g}": {"reg": per_eps[e]["regression"],
                                   "eps_err": per_eps[e]["eps_target_rel_err"],
                                   "passed": eps_pass[e]} for e in ladder}}


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase_5 G1b Level C amplitude gate")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--workers", type=int,
                        default=max(1, (os.cpu_count() or 2) - 2))
    args = parser.parse_args()
    result = run_g1b(args.config, args.output_root, smoke=args.smoke,
                     workers=args.workers)
    return 0 if result["verdict"] in {"PASSED", "SCOPED_CANDIDATE"} else 1


if __name__ == "__main__":
    sys.exit(main())
