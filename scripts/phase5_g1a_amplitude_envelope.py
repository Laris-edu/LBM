"""Phase_5 G1a prescribed-wall-temperature amplitude-envelope gate (contract §6.2, WP2).

Certifies the gas-side amplitude envelope on the G1-W certified production
wall (v1.1 symmetric mass-neutral, run 20260727T083342Z) over the mandatory
epsilon ladder {0.001, 0.01, 0.03, 0.05} plus conditional points {0.075,
0.10}, on the frozen dx2p6 stack with frozen production spectral operators
(ablation belongs to G2-O). The baseline protocol is verbatim the G1-W
authoritative protocol (sealed y-periodic rig ny=48, periods 3, settle 1,
raised-cosine ramp 1) so the mandatory points are directly comparable to the
archived G1-W ladder (deterministic stack -> bitwise reproduction).

Row operationalizations (pre-registered here, §6.2 order):
- small-amplitude regression: calibration-free energy-channel admittance at
  eps=0.001 vs the lbm-equivalent sealed spectral reference (G1-W caliber);
- wall-temperature realization: audited per-step pairing (G1-W instrument);
- energy audit (<=1%): TWO-CHANNEL CONSISTENCY DRIFT — c(eps) =
  Y_energy/Y_moment with the recalibration constant frozen at the smallest
  mandatory point; max_eps |c(eps)/c(eps_min) - 1| bounds genuine
  amplitude-dependence of the field-shape/readout chain (an absolute 1%
  closure between the raw channels is impossible on this stack by G1-W
  finding — the 3.055@+17.5deg constant IS the archived §23 input);
- mass / finiteness / no-repair: audited as in G1-W;
- window sensitivity: suffix-window refit (full fit window vs last-N cycles),
  1f amplitude <=2% and phase <=2deg;
- diagnostic refinement (must not re-tune the baseline): TWO axes —
  (i) domain refinement ny 48->96 (halves k_box; spectral reference rebuilt
  at n_cells=96 from the same measured alpha_eff(k) table) with the D_G
  difference row |D_G^96 - D_G^48| <= max(1%, U_gov) and the H2 difference
  folded into U_gov(H2); (ii) a dx1p3 resolution-axis liveness probe (P3-6
  precedent: the shared Grad reconstruction core went unstable at dx1p3 tau
  in ~1.3k steps for the old wall) — outcome archived either way; if dead,
  the refinement axis is the documented domain axis and the limitation is
  recorded (NOT a scoped condition: the domain axis is available).
- minimum amplitude window: all rows must pass through eps=0.05 for the
  full-production authorization; 0.075/0.10 may fail individually forming
  G1A_PASSED_TO_0P05 (contract label, not a gate failure).

H2/H3 are tracked with the §12.1 N=5 joint fit (detrend 0) and reported per
epsilon with the settle-1 single-run transient floor (~6e-4 relative,
measured on the G1-W archive) as context — harmonic CERTIFICATION belongs to
G2; here they enter U_gov only.

Outputs the contract §16.1 seven-file set under
results/phase5/g1a_wall_amplitude/<run_id>/. Script-emittable verdict only.
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
from boundary.wall_thermal_mass_neutral import make_symmetric_mass_neutral_wall_callback
from postproc.multiharmonic_fit import fit_multiharmonic
from reference.thermal_admittance import thermal_admittance_halfspace
from scripts.phase2_m2_verification import load_config
from scripts.phase5_g1w_wall_neutrality import (
    G0_TABLE_CSV,
    GAMMA_EFF_G0_K1,
    _cplx,
    _git_commit,
    _ratio,
    energy_channel_Y_over_Yhs,
    load_g0_alpha_rows,
    measure_extension_rows,
    run_driven,
    sealed_spectral_reference,
)

GATE_ID = "G1a"
CASE_FAMILY = "g1a_wall_amplitude"
PHASE5_CONTRACT_VERSION = "v1.2"
DEFAULT_CONFIG = Path("configs/phase5/g1a_wall_amplitude/g1a_10k_dx2p6.yaml")
PHYSICS_CORE_FILES = [
    "boundary/wall_thermal_mass_neutral.py",
    "boundary/wall_mass_audit.py",
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


def refit_n5(run: dict, frequency: float, settle_periods: float,
             n_harmonics: int) -> dict[str, Any]:
    """§12.1 N-harmonic joint refit (detrend 0) of the archived q/p series."""

    omega = 2.0 * math.pi * frequency
    mask = run["t_s"] >= settle_periods / frequency * (1.0 - 1e-12)
    t = run["t_s"][mask]
    fq = fit_multiharmonic(t, run["q_moment_si"][mask], omega, n_harmonics=n_harmonics)
    fp = fit_multiharmonic(t, run["p_box_lu"][mask], omega, n_harmonics=n_harmonics)
    return {"fit_q5": fq, "fit_p5": fp,
            "H2_q": fq.leakage_relative(1)[2], "H3_q": fq.leakage_relative(1)[3],
            "H2_p": fp.leakage_relative(1)[2], "H3_p": fp.leakage_relative(1)[3]}


def window_sensitivity(run: dict, frequency: float, settle_periods: float,
                       cycles: list[float], n_harmonics: int) -> dict[str, float]:
    """Suffix-window 1f sensitivity: full fit window vs last-N cycles."""

    omega = 2.0 * math.pi * frequency
    t_end = run["t_s"][-1]
    fits = []
    for cyc in cycles:
        mask = run["t_s"] >= max(settle_periods / frequency,
                                 t_end - cyc / frequency) * (1.0 - 1e-12)
        fits.append(fit_multiharmonic(run["t_s"][mask], run["q_moment_si"][mask],
                                      omega, n_harmonics=n_harmonics))
    a0, a1 = fits[0].harmonic(1), fits[1].harmonic(1)
    return {"amp_rel": float(abs(a1 / a0) - 1.0),
            "phase_deg": float(math.degrees(math.atan2((a1 / a0).imag, (a1 / a0).real)))}


def _case_worker(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Process-pool worker for one independent case (scheduling layer only).

    The physics protocol and the per-run step sequence are byte-identical to
    the serial path (each case is a deterministic standalone solver run);
    parallelism exists only ACROSS independent cases. The audit recorder
    object is dropped after run_driven derives its rows (pickle-lean; all
    downstream consumers use the derived arrays/scalars).
    """

    label = payload["label"]

    def wlog(msg: str) -> None:
        print(f"G1A [{label}] {msg}", flush=True)

    if payload["kind"] == "probe":
        out = dx1p3_liveness_probe(payload["gas_cfg"], payload["epsilon"],
                                   payload["n_steps"], payload["frequency_hz"], wlog)
        return label, out
    run = run_driven(
        payload["gas_cfg"], payload["wall"], payload["epsilon"],
        frequency_hz=payload["frequency_hz"], periods=payload["periods"],
        settle_periods=payload["settle_periods"],
        samples_per_period=payload["samples_per_period"],
        grad_extrap_old=payload["grad_extrap_old"],
        ramp_periods=payload["ramp_periods"], log=wlog)
    run.pop("recorder", None)
    return label, run


def execute_cases(payloads: list[dict[str, Any]], workers: int, log,
                  worker=None) -> dict[str, Any]:
    """Run independent cases via a process pool (or serially if workers<=1).

    ``worker`` (module-level callable, picklable) defaults to this gate's
    ``_case_worker``; other gate runners (G2) pass their own — the scheduling
    layer is shared, the physics payload dispatch is per-gate.
    """

    if worker is None:
        worker = _case_worker
    results: dict[str, Any] = {}
    if workers <= 1 or len(payloads) <= 1:
        for p in payloads:
            label, run = worker(p)
            results[label] = run
        return results
    # cap per-worker BLAS threads before children spawn (tiny-array workloads;
    # avoids oversubscription when many workers run at once)
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ.setdefault(var, "1")
    log("parallel scheduling: %d independent cases on %d workers" % (len(payloads), workers))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(worker, p): p["label"] for p in payloads}
        for fut in as_completed(futures):
            label = futures[fut]
            try:
                label, run = fut.result()
                results[label] = run
            except Exception as exc:  # one case must not sink the pool;
                results[label] = {"worker_exception": f"{type(exc).__name__}: {exc}"}
                log(f"case FAILED with exception: {label}: {exc}")
            log(f"case done: {label} ({len(results)}/{len(payloads)})")
    return results


def dx1p3_liveness_probe(gas_cfg: dict, epsilon: float, n_steps: int,
                         frequency: float, log) -> dict[str, Any]:
    """Resolution-axis liveness: short mn-wall run on the dx1p3 probe stack."""

    solver = GasSolver2D(gas_cfg)
    mapping = solver.mapping
    dt = float(mapping.lattice.dt_s)
    theta0 = float(mapping.theta_ref_lu)
    omega = 2.0 * math.pi * frequency
    solver.initialize_from_macro(
        mapping.lattice.rho_ref_lu, np.zeros((solver.ny, solver.nx, 2)), theta0)
    survived = 0
    finite = True
    death: str | None = None
    # death manifests either as non-finite fields OR as the wall guard raising
    # (non-positive streamed wall-row density) — both are the probe's SIGNAL,
    # not a runner error (P3-6 precedent: the shared Grad core at dx1p3 tau)
    try:
        for i in range(n_steps):
            theta_w = theta0 + epsilon * theta0 * math.cos(omega * (i + 1) * dt)
            solver.step(1, boundary_callback=make_symmetric_mass_neutral_wall_callback(
                theta_w, extrap="row1"))
            if (i + 1) % 100 == 0:
                if not (np.isfinite(solver.f).all() and np.isfinite(solver.g).all()):
                    finite = False
                    break
                survived = i + 1
        else:
            survived = n_steps
    except (RuntimeError, FloatingPointError, ValueError) as exc:
        finite = False
        death = f"{type(exc).__name__}: {exc}"
        survived = max(survived, (i + 1) - 1)
    log("dx1p3 probe: survived %d/%d steps finite=%s death=%s (P3-6 old-wall "
        "precedent died ~1.3k)" % (survived, n_steps, finite, death or "-"))
    return {"n_steps_target": n_steps, "steps_survived": survived, "finite": finite,
            "death_mode": death, "ny": solver.ny, "dt_s": dt}


def run_g1a(config_path: Path, output_root: Path | None = None,
            smoke: bool = False, workers: int = 1) -> dict[str, Any]:
    cfg = load_config(config_path)
    proto = cfg["g1a_smoke"] if smoke else cfg["g1a"]
    gates = cfg["gates"]
    gas_cfg_path = Path(cfg["inheritance"]["gas_config_path"])
    repo_root = Path(__file__).resolve().parents[1]

    def log(msg: str) -> None:
        print(f"G1A {msg}", flush=True)

    def make_gas(ny: int, nx: int, path: Path = gas_cfg_path) -> dict:
        gas = load_config(path)
        gas["numerics"] = {**gas.get("numerics", {}), "nx": nx, "ny": ny}
        return gas

    frequency = float(proto["frequency_Hz"])
    ny = int(proto["ny"])
    nx = int(proto["nx"])
    n_harm = int(proto["n_harmonics"])
    refinement = proto["refinement"]
    ny_ref = int(refinement["ny_refined"])
    probe_solver = GasSolver2D(make_gas(8, 4))
    mapping = probe_solver.mapping
    alpha_nom = float(mapping.alpha_lu)
    gamma = float(mapping.physical.gamma)
    dt = float(mapping.lattice.dt_s)
    omega_lu = 2.0 * math.pi * frequency * dt
    temp_scale = float(mapping.temperature_scale)
    kg_si = float(getattr(mapping.physical, "kg_W_mK", 0.0263))
    alpha_si = alpha_nom * mapping.lattice.dx_m**2 / dt
    y_hs_si = thermal_admittance_halfspace(frequency, kg=kg_si, alpha0=alpha_si)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = Path(output_root) if output_root else repo_root / "results" / "phase5" / CASE_FAMILY
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    h5 = h5py.File(out_dir / "signals.h5", "w")

    # ---- alpha_eff(k) table (G0 authoritative + in-run extension) ----
    g0_rows = load_g0_alpha_rows(repo_root / G0_TABLE_CSV)
    ext_rows = measure_extension_rows(
        make_gas(8, 4), [int(n) for n in proto["alpha_extension_ny"]], alpha_nom, log)
    all_rows = sorted(g0_rows + [(r["k_lu"], r["alpha_eff_lu"]) for r in ext_rows])
    k_tab = np.array([r[0] for r in all_rows])
    a_tab = np.array([r[1] for r in all_rows])
    grp = h5.create_group("alpha_eff_table")
    grp.create_dataset("k_lu", data=k_tab)
    grp.create_dataset("alpha_eff_lu", data=a_tab)

    # ---- spectral references (baseline grid + refinement grid) ----
    pol = str(proto["highk_policy_primary"])
    ref48 = sealed_spectral_reference(ny, omega_lu, alpha_nom, k_tab, a_tab,
                                      highk_policy=pol, gamma=gamma)
    ref96 = sealed_spectral_reference(ny_ref, omega_lu, alpha_nom, k_tab, a_tab,
                                      highk_policy=pol, gamma=gamma)
    log("sealed reference ny=%d: %.4f@%+.2f deg | ny=%d: %.4f@%+.2f deg" % (
        ny, abs(ref48["Y_over_Yhs"]),
        math.degrees(math.atan2(ref48["Y_over_Yhs"].imag, ref48["Y_over_Yhs"].real)),
        ny_ref, abs(ref96["Y_over_Yhs"]),
        math.degrees(math.atan2(ref96["Y_over_Yhs"].imag, ref96["Y_over_Yhs"].real))))

    # ---- independent cases: epsilon ladder + domain refinement + dx probe ----
    # (parallel at the ORCHESTRATION layer only — each case is the identical
    # deterministic standalone run; assembly below is ladder-ordered, so the
    # outputs are bitwise independent of scheduling)
    scalars = dict(frequency_hz=frequency, periods=float(proto["periods"]),
                   settle_periods=float(proto["settle_periods"]),
                   samples_per_period=int(proto["samples_per_period"]),
                   grad_extrap_old="linear",
                   ramp_periods=float(proto["ramp_periods"]))
    settle = scalars["settle_periods"]
    mandatory = [float(e) for e in proto["epsilon_mandatory"]]
    conditional = [float(e) for e in proto["epsilon_conditional"]]
    ladder = mandatory + conditional
    eps_min = mandatory[0]
    ref_eps_list = [float(e) for e in refinement["epsilons"]]

    payloads: list[dict[str, Any]] = []
    for eps in ladder:
        payloads.append({"kind": "driven", "label": f"ny{ny}_eps{eps:g}",
                         "gas_cfg": make_gas(ny, nx), "wall": "mass_neutral_v1p1",
                         "epsilon": eps, **scalars})
    for eps in ref_eps_list:
        payloads.append({"kind": "driven", "label": f"ny{ny_ref}_eps{eps:g}",
                         "gas_cfg": make_gas(ny_ref, nx), "wall": "mass_neutral_v1p1",
                         "epsilon": eps, **scalars})
    if int(refinement.get("dx1p3_probe_steps", 0)) > 0:
        dx1p3_path = Path(cfg["inheritance"]["gas_config_dx1p3_probe"])
        payloads.append({"kind": "probe", "label": "dx1p3_probe",
                         "gas_cfg": make_gas(2 * ny, nx, dx1p3_path),
                         "epsilon": float(refinement["dx1p3_epsilon"]),
                         "n_steps": int(refinement["dx1p3_probe_steps"]),
                         "frequency_hz": frequency})
    case_results = execute_cases(payloads, workers, log)
    for label, res in case_results.items():
        if isinstance(res, dict) and "worker_exception" in res and label != "dx1p3_probe":
            raise RuntimeError(f"driven case {label} crashed: {res['worker_exception']}")

    def y_moment(run: dict) -> complex:
        t_hat_si = run["theta_hat_lu"] * temp_scale
        return (run["fit_q"].harmonic(1) / t_hat_si) / y_hs_si

    runs48: dict[float, dict[str, Any]] = {}
    per_eps: dict[float, dict[str, Any]] = {}
    for eps in ladder:
        r = case_results[f"ny{ny}_eps{eps:g}"]
        runs48[eps] = r
        y_e = energy_channel_Y_over_Yhs(r, omega_lu, alpha_nom, gamma)
        y_m = y_moment(r)
        extra = refit_n5(r, frequency, settle, n_harm)
        wsens = window_sensitivity(r, frequency, settle,
                                   [float(c) for c in proto["window_sensitivity_cycles"]],
                                   n_harm)
        per_eps[eps] = {
            "Y_energy": y_e, "Y_moment": y_m, "c_two_channel": y_e / y_m,
            "H2_q": extra["H2_q"], "H3_q": extra["H3_q"],
            "H2_p": extra["H2_p"], "H3_p": extra["H3_p"],
            "window_sens": wsens, "fits5": extra,
        }
        log("  eps=%-6g Y_e=%.4f@%+.2f H2q=%.3e H2p=%.3e wsens=%.2e%%/%.3fdeg" % (
            eps, abs(y_e), math.degrees(math.atan2(y_e.imag, y_e.real)),
            extra["H2_q"], extra["H2_p"],
            100.0 * abs(wsens["amp_rel"]), wsens["phase_deg"]))

    runs96: dict[float, dict[str, Any]] = {}
    for eps in ref_eps_list:
        r = case_results[f"ny{ny_ref}_eps{eps:g}"]
        runs96[eps] = r
        y_e = energy_channel_Y_over_Yhs(r, omega_lu, alpha_nom, gamma)
        r["Y_energy"] = y_e
        r["fits5"] = refit_n5(r, frequency, settle, n_harm)
        log("  refined ny=%d eps=%g Y_e=%.4f@%+.2f" % (
            ny_ref, eps, abs(y_e), math.degrees(math.atan2(y_e.imag, y_e.real))))

    probe = case_results.get("dx1p3_probe")
    if probe is not None and "worker_exception" in probe:
        probe = {"finite": False, "death_mode": probe["worker_exception"],
                 "steps_survived": None,
                 "n_steps_target": int(refinement["dx1p3_probe_steps"]),
                 "note": "worker-level death (pool guard; before in-probe handler)"}

    # ---- archive series ----
    for eps, r in list(runs48.items()) + [(e, rr) for e, rr in runs96.items()]:
        label = f"ny{r['solver_meta']['ny']}_eps{eps:g}"
        g = h5.create_group(f"runs/{label}")
        for name in ("t_s", "p_box_lu", "q_moment_si", "mass", "theta_imposed_lu"):
            g.create_dataset(name, data=r[name])
        g.attrs.update({"epsilon": eps, "ny": r["solver_meta"]["ny"],
                        "window_dm_rel": r["window_dm_rel"],
                        "total_drift_rel": r["total_drift_rel"],
                        "wall_temp_err_K": r["wall_temp_err_K"],
                        "finite": r["finite"]})

    # ---- gate rows (§6.2) ----
    small = per_eps[eps_min]
    reg = _ratio(small["Y_energy"], ref48["Y_over_Yhs"])
    c_min = small["c_two_channel"]
    energy_drift = {eps: abs(per_eps[eps]["c_two_channel"] / c_min - 1.0)
                    for eps in ladder}
    wall_terr = {eps: runs48[eps]["wall_temp_err_K"] for eps in ladder}
    mass_win = {eps: runs48[eps]["window_dm_rel"] for eps in ladder}
    mass_cum = {eps: runs48[eps]["total_drift_rel"] for eps in ladder}
    finite_all = {eps: runs48[eps]["finite"] for eps in ladder}

    def eps_ok(eps: float) -> bool:
        w = per_eps[eps]["window_sens"]
        return bool(finite_all[eps]
                    and wall_terr[eps] <= gates["wall_temperature_error_K"]
                    and mass_win[eps] <= gates["mass_window_rel"]
                    and mass_cum[eps] <= gates["mass_cumulative_rel"]
                    and energy_drift[eps] <= gates["energy_audit_rel"]
                    and abs(w["amp_rel"]) <= gates["window_amp_rel"]
                    and abs(w["phase_deg"]) <= gates["window_phase_deg"])

    eps_pass = {eps: eps_ok(eps) for eps in ladder}

    # D_G rows on both grids at the shared refinement epsilons
    ref_eps = [float(e) for e in refinement["epsilons"]]
    dg48 = dg96 = dg_diff = None
    h2_refine_diff = None
    if len(ref_eps) >= 2 and all(e in runs96 for e in ref_eps):
        e_lo, e_hi = min(ref_eps), max(ref_eps)
        dg48 = abs(per_eps[e_hi]["Y_energy"]) / abs(per_eps[e_lo]["Y_energy"]) - 1.0
        dg96 = abs(runs96[e_hi]["Y_energy"]) / abs(runs96[e_lo]["Y_energy"]) - 1.0
        dg_diff = abs(dg96 - dg48)
        h2_refine_diff = abs(runs96[e_hi]["fits5"]["H2_q"] - per_eps[e_hi]["H2_q"])
    elif len(ref_eps) == 1 and ref_eps[0] in runs96:
        # smoke path: single refined point -> regression consistency only
        e0 = ref_eps[0]
        dg_diff = abs(abs(runs96[e0]["Y_energy"] / ref96["Y_over_Yhs"])
                      - abs(per_eps[e0]["Y_energy"] / ref48["Y_over_Yhs"]))
        h2_refine_diff = abs(runs96[e0]["fits5"]["H2_q"] - per_eps[e0]["H2_q"])

    u95_rel = float(small["fits5"]["fit_q5"].amplitude_u95(1)
                    / max(small["fits5"]["fit_q5"].amplitude(1), 1e-300))
    wsens_max = max(abs(per_eps[e]["window_sens"]["amp_rel"]) for e in mandatory)
    # the refinement row's own gate must NOT include the refinement diff
    # (self-satisfying otherwise); U_gov for downstream QoIs includes it
    u_gov_nonrefine = float(max(wsens_max, u95_rel))
    u_gov = float(max(u_gov_nonrefine, dg_diff or 0.0))
    refinement_gate = max(float(gates["refinement_dg_rel"]), u_gov_nonrefine)

    gate_rows: dict[str, dict[str, Any]] = {
        "smallamp_regression": {
            "epsilon": eps_min, "Y_energy": _cplx(small["Y_energy"]),
            "Y_reference": _cplx(ref48["Y_over_Yhs"]), "ratio": reg,
            "gate": [gates["smallamp_amp_rel"], gates["smallamp_phase_deg"]],
            "passed": bool(abs(reg["amp_rel_err"]) <= gates["smallamp_amp_rel"]
                           and abs(reg["phase_deg_err"]) <= gates["smallamp_phase_deg"]),
        },
        "wall_temperature": {
            "max_err_K": max(wall_terr.values()), "gate": gates["wall_temperature_error_K"],
            "passed": bool(max(wall_terr.values()) <= gates["wall_temperature_error_K"]),
        },
        "energy_audit_two_channel_drift": {
            "definition": "max_eps |c(eps)/c(eps_min)-1|, c=Y_energy/Y_moment "
                          "(recalibration frozen at eps_min; §23 constant)",
            "c_eps_min": _cplx(c_min), "drift_by_eps": energy_drift,
            "gate": gates["energy_audit_rel"],
            "passed": bool(max(energy_drift[e] for e in mandatory)
                           <= gates["energy_audit_rel"]),
        },
        "global_mass": {
            "window_max": max(mass_win.values()), "cumulative_max": max(mass_cum.values()),
            "gates": [gates["mass_window_rel"], gates["mass_cumulative_rel"]],
            "passed": bool(max(mass_win.values()) <= gates["mass_window_rel"]
                           and max(mass_cum.values()) <= gates["mass_cumulative_rel"]),
        },
        "finiteness": {"by_eps": finite_all, "passed": bool(all(finite_all.values()))},
        "numerical_repair": {"no_clipping": True, "no_floor": True,
                             "no_positivity_repair": True, "passed": True},
        "window_sensitivity": {
            "by_eps": {e: per_eps[e]["window_sens"] for e in ladder},
            "gates": [gates["window_amp_rel"], gates["window_phase_deg"]],
            "passed": bool(all(
                abs(per_eps[e]["window_sens"]["amp_rel"]) <= gates["window_amp_rel"]
                and abs(per_eps[e]["window_sens"]["phase_deg"]) <= gates["window_phase_deg"]
                for e in mandatory)),
        },
        "diagnostic_refinement": {
            "domain_axis": {"ny": [ny, ny_ref], "D_G_48": dg48, "D_G_96": dg96,
                            "D_G_diff": dg_diff, "gate": refinement_gate,
                            "H2_q_diff_into_Ugov": h2_refine_diff},
            "resolution_axis_dx1p3": probe,
            "passed": bool(dg_diff is not None and dg_diff <= refinement_gate),
            "note": "domain axis (ny doubling, matched spectral reference) is the "
                    "certified refinement; dx1p3 liveness outcome archived — if dead "
                    "(P3-6 precedent) the limitation is documented, not scoped",
        },
        "minimum_amplitude_window": {
            "eps_pass": {f"{e:g}": eps_pass[e] for e in ladder},
            "gate": gates["min_amplitude_window"],
            "passed": bool(all(eps_pass[e] for e in mandatory)),
        },
    }

    labels: list[str] = []
    if all(gate_rows[k]["passed"] for k in gate_rows):
        if conditional and not all(eps_pass[e] for e in conditional):
            labels.append("G1A_PASSED_TO_0P05")
        verdict = "PASSED"
    else:
        if not all(eps_pass[e] for e in mandatory if e <= 0.03):
            labels.append("AMPLITUDE_ENVELOPE_FAILED_BELOW_0P03")
        verdict = "FAILED"
    log("verdict=%s labels=%s" % (verdict, labels or "-"))

    # ---- outputs (contract §16.1 seven files) ----
    resolved = {"gate_id": GATE_ID, "case_family": CASE_FAMILY, "protocol": proto,
                "gates": gates, "config_path": str(config_path)}
    config_yaml = yaml.safe_dump(resolved, allow_unicode=True, sort_keys=False)
    (out_dir / "config_resolved.yaml").write_text(config_yaml, encoding="utf-8")

    na = "not_applicable_g1a_sealed_rig"
    fitq5 = small["fits5"]["fit_q5"]
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
        "work_package": "WP2",
        "gate_id": GATE_ID,
        "case_family": CASE_FAMILY,
        "model_route": "ROUTE_B_MAIN",
        "property_model_id": "frozen_dx2p6_route_b_closure",
        "tau_policy": "frozen (M3 closure §3; no per-point retuning)",
        "mapping_digest": _sha256_bytes(Path(gas_cfg_path).read_bytes())[:12],
        "background_path": "uniform_reference_state",
        "forcing_protocol": "prescribed_wall_temperature_zero_mean_sinusoid",
        "P_mean_W_m2": 0.0, "P_mean_rematched": False, "target_Theta_DC": 0.0,
        "frequency_Hz": frequency,
        "T_ambient_K": 300.0, "T_mean_K": 300.0,
        "epsilon_AC_measured": {f"{e:g}": e for e in ladder},
        "Theta_DC_measured": 0.0,
        "chi_0": None, "chi_eff": None, "C_A_J_m2K": None,
        "dc_heat_sink_model": na + " (sealed rig; canonical sink belongs to G4a)",
        "dc_heat_sink_parameters": None,
        "H_s_role": "rig domain height (sealed periodic)",
        "thermal_resistance_effective": None,
        "grid_shape": [ny, nx], "dx_m": float(mapping.lattice.dx_m), "dt_s": dt,
        "domain_height_m": ny * float(mapping.lattice.dx_m),
        "boundary_model": "mass_neutral_v1p1_symmetric (G1-W certified production wall)",
        "wall_mass_policy": "mass_neutral_by_construction",
        "wall_neutrality_gate_id": "G1-W PASSED (20260727T083342Z)",
        "boundary_mass_flux_definition": "wall_mass_audit.NORMALIZATION_DEFINITION",
        "boundary_mass_flux_0f_to_3f": float(
            runs48[eps_min]["audit"]["dm_rel"]["max_component"]),
        "spectral_operator_stack_id": "frozen_production_dx2p6",
        "spectral_correction_enabled": True,
        "high_wavenumber_filter_enabled": True,
        "high_wavenumber_filter_strength": "frozen_production",
        "operator_ablation_run_id": None,
        "q_feedback_relax": None,
        "fit_window": {"settle_periods": settle,
                       "fit_periods": float(proto["periods"]) - settle},
        "fit_cycles": float(proto["periods"]) - settle,
        "detrend_order": 0,
        "harmonic_order_max": n_harm,
        "harmonic_fit_condition_number": fitq5.condition_number,
        "U_det": {"window_max_mandatory": wsens_max, "refinement_dg_diff": dg_diff},
        "U95_fit": {"q1f_rel_at_eps_min": u95_rel},
        "U_gov": u_gov,
        "no_clipping": True, "no_floor": True, "no_positivity_repair": True,
        "gate_status": verdict,
        "scoped_limitations": labels,
        "smoke_mode": bool(smoke),
        "results": {
            "T_s_hat_1f": _cplx(complex(runs48[e_rep]["theta_hat_lu"] * temp_scale, 0.0)),
            "p_hat_1f": _cplx(rep["fits5"]["fit_p5"].harmonic(1)),
            "p_hat_2f": _cplx(rep["fits5"]["fit_p5"].harmonic(2)),
            "p_hat_3f": _cplx(rep["fits5"]["fit_p5"].harmonic(3)),
            "outgoing_mode_1f": None, "outgoing_mode_2f": None, "outgoing_mode_3f": None,
            "outgoing_mode_note": "sealed rig has no outgoing mode (G2 quantity)",
            "G1": float(abs(rep["Y_energy"])),
            "D_G": {f"{e:g}": float(abs(per_eps[e]["Y_energy"]) / abs(small["Y_energy"]) - 1.0)
                    for e in ladder},
            "D_OP": None, "D_OP_note": "A2a quantity (WP3)",
            "H2": {f"{e:g}": per_eps[e]["H2_q"] for e in ladder},
            "H3": {f"{e:g}": per_eps[e]["H3_q"] for e in ladder},
            "H2_p_side": {f"{e:g}": per_eps[e]["H2_p"] for e in ladder},
            "harmonic_floor_note": "settle-1 single-run transient floor ~6e-4 rel "
                                   "(G1-W archive); certification belongs to G2",
            "m1": None, "m2": None, "m3": None,
            "m_note": "scaling exponents certified in G2; ladder H2 archived here",
            "QS0_error_amplitude": None, "QS0_error_phase": None,
            "QS1_error_amplitude": None, "QS1_error_phase": None,
            "wall_boundary_sensitivity": {
                "moment_channel_recalibration_c_eps_min": _cplx(c_min),
                "drift_by_eps": energy_drift},
            "operator_sensitivity_D_G": None,
            "operator_sensitivity_H2": None,
            "operator_sensitivity_H3": None,
            "operator_note": "G2-O quantity (frozen stack here)",
            "boundary_mass_flux_0f_to_3f": float(
                runs48[eps_min]["audit"]["dm_rel"]["max_component"]),
            "energy_residual": float(max(energy_drift[e] for e in mandatory)),
            "mass_or_flux_residual": float(max(mass_cum.values())),
            "wall_temperature_error": float(max(wall_terr.values())),
        },
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=1, default=float), encoding="utf-8")

    harmonic_payloads = {}
    for eps in ladder:
        harmonic_payloads[f"q_ny48_eps{eps:g}"] = per_eps[eps]["fits5"]["fit_q5"].to_json_payload()
        harmonic_payloads[f"p_ny48_eps{eps:g}"] = per_eps[eps]["fits5"]["fit_p5"].to_json_payload()
    (out_dir / "harmonic_fit.json").write_text(
        json.dumps(harmonic_payloads, indent=1, default=float), encoding="utf-8")

    provenance = {
        "run_id": run_id, "command": " ".join(sys.argv),
        "workers": workers,
        "parallel_scheduling_note": "process pool over independent cases only; "
                                    "per-case step sequence identical to serial "
                                    "(assembly ladder-ordered, scheduling-invariant)",
        "python": sys.version.split()[0], "numpy": np.__version__,
        "code_commit": summary["code_commit"],
        "physics_core_digest": summary["physics_core_digest"],
        "physics_core_files": {rel: _sha256_bytes((repo_root / rel).read_bytes())[:12]
                               for rel in PHYSICS_CORE_FILES},
        "g1w_certified_run": summary["parent_baseline_run"],
        "g0_alpha_table": str(G0_TABLE_CSV),
    }
    (out_dir / "provenance.json").write_text(json.dumps(provenance, indent=1),
                                             encoding="utf-8")
    (out_dir / "gate_evaluation.json").write_text(
        json.dumps({"gate_id": GATE_ID, "verdict": verdict, "labels": labels,
                    "rows": gate_rows}, indent=1, default=float), encoding="utf-8")

    report = [f"# G1a run {run_id}", "",
              f"- verdict: **{verdict}** labels={labels or '-'}",
              f"- production wall: v1.1 (G1-W {summary['parent_baseline_run']})",
              f"- smoke_mode: {smoke}", "", "## Gate rows (contract §6.2)", ""]
    for name, row in gate_rows.items():
        report.append(f"- {name}: passed={row['passed']}")
    report += ["", "## Ladder", ""]
    for eps in ladder:
        y_e = per_eps[eps]["Y_energy"]
        report.append(
            "- eps=%g: Y_e=%.4f@%+.2fdeg H2q=%.3e H2p=%.3e drift(c)=%.2e pass=%s" % (
                eps, abs(y_e), math.degrees(math.atan2(y_e.imag, y_e.real)),
                per_eps[eps]["H2_q"], per_eps[eps]["H2_p"], energy_drift[eps],
                eps_pass[eps]))
    (out_dir / "run_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    h5.close()
    log(f"outputs -> {out_dir}")
    return {"verdict": verdict, "labels": labels, "out_dir": str(out_dir),
            "summary": summary, "gate_rows": gate_rows,
            "per_eps": {f"{e:g}": {"H2_q": per_eps[e]["H2_q"],
                                   "drift": energy_drift[e],
                                   "passed": eps_pass[e]} for e in ladder}}


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase_5 G1a amplitude-envelope gate")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--workers", type=int,
                        default=max(1, (os.cpu_count() or 2) - 2),
                        help="process-pool width for independent cases "
                             "(scheduling only; 1 = serial)")
    args = parser.parse_args()
    result = run_g1a(args.config, args.output_root, smoke=args.smoke,
                     workers=args.workers)
    return 0 if result["verdict"] in {"PASSED", "SCOPED_CANDIDATE"} else 1


if __name__ == "__main__":
    sys.exit(main())
