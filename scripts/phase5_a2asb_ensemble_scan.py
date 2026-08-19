"""A2a-STRICT_B ensemble-axis scan (D0-7 diagnostic; plan PLAN_v1.0).

Plan authority: docs/Phase_5/a2asb_ensemble_scan_plan_v1.0.md (frozen
2026-08-20).  Question: is the original-frame negative operating-point trend
primarily the stack's dynamic response to the BASE-STATE COLUMN-MASS
ensemble (slope ~0.95-0.96 pp per % mass in the cross-frame arithmetic of
a2a_strict_b_report.md section 5.4), with the boundary itself carrying only
the ~10.8% slice the A2a-STRICT_B retest isolated?

Single scanned variable: the settle mass target.  Boundary (strict-B G0
face), protocol, geometry, readout and worker code paths are the judgement
run's VERBATIM (scripts.phase5_a2a_strict_b workers, CODE_VERSION
unchanged) — wet-mass points and the shared cold anchor therefore resume
bit-for-bit from the judgement run's checkpoints (zero new compute for
them); only the synthetic-mass points step.

Mass scale: M0/A = M_wet(0)/A (reference pack cold value = the shared cold
denominator's own ensemble).  With r(Theta) = M_wet(Theta)/M0:
  Theta=0.05 grid: {r, (1+r)/2, 1, (3-r)/2, 2-r}   (symmetric five-point)
  Theta=0.10 grid: {r, (1+r)/2, 1}                  (cross-Theta slope check)
Wet points pass the pack floats VERBATIM (checkpoint ident equality).

Frozen judgement lines (plan section 2): five-point linear-fit residual
<= max(0.05 pp, 0.05*span); |s(0.10)/s(0.05)-1| <= 0.15; static-family
flatness |dQS1(m)-dQS1(1)| <= 0.20*|d_op(m)-d_op(1)| at every |dm|>0.1%
point.  Classification order: UNINTERPRETABLE_ENSEMBLE_SCAN >
ENSEMBLE_AXIS_CONFIRMED > ENSEMBLE_AXIS_PARTIAL >
ENSEMBLE_AXIS_NOT_CONFIRMED.  Report-only rows: surplus-point sign
reversal; tangent-frame reconciliation of the in-frame equal-mass points
against the archived strict tangent anchors (0.2 pp band); checkpoint-reuse
provenance.  All results carry g0_scope=G0_FENCE_PENDING_USER (inherited
G0-B fence semantics; user decision outstanding).

This unit grants no strict-B qualification, does not touch the judgement
run's four-level ruling (user-owned), and changes no Gate or production
state.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.strict_b_half_domain import StrictBHalfDomain  # noqa: E402
from scripts.phase2_m2_verification import load_config  # noqa: E402
from scripts.phase5_a2a_strict_b import (  # noqa: E402
    BRANCH,
    FIT_WINDOW_ALT,
    FIT_WINDOW_MAIN,
    G0_SCOPE,
    GATE_COLD_AMP_REL,
    GATE_COLD_PHASE_DEG,
    GATE_CONTRACT_REL,
    GATE_DC_CLOSURE,
    GATE_LINEARITY,
    GATE_MASS_DRIFT_REL,
    GATE_MASS_INIT_REL,
    GATE_PMEAN_REL_WET,
    GATE_STATIONARITY,
    N_REF_LADDER,
    Y0_WET_COLD,
    _cplx,
    _git_commit,
    _sb_a2a_drive_worker,
    _sb_a2a_settle_worker,
    _steps_per_period,
    _wrap_deg,
    fit_admittance_window,
    load_reference_pack,
    qs_family_for_point,
)
from scripts.phase5_g1a_amplitude_envelope import execute_cases  # noqa: E402
from scripts.phase5_g1w_wall_neutrality import G0_TABLE_CSV, load_g0_alpha_rows  # noqa: E402
from scripts.phase5_wp4_qs1k_mechanism import fit_exponents  # noqa: E402

UNIT = "A2ASB-ENSEMBLE-SCAN"
CASE_FAMILY = "a2asb_ensemble_scan"

# ---------------------------------------------------------------------------
# FROZEN JUDGEMENT LINES (plan section 2; registered before any hot number)
# ---------------------------------------------------------------------------
RESID_FLOOR_PP = 0.05          # linear-fit residual gate floor
RESID_FRAC = 0.05              # ... or this fraction of the grid span
SLOPE_AGREE_REL = 0.15         # |s(0.10)/s(0.05) - 1|
QS_FLAT_FRAC = 0.20            # static family explains <= 20% of the move
DM_ACTIVE_PCT = 0.1            # points with |dm| above this enter the gates
TAN_XCHECK_PP = 0.2            # report-only reconciliation band
# archived strict tangent anchors (equal-mass frame, G0 branch;
# archive/strict_b/hot_judgement.csv) — REPORT ONLY, never gating
TAN_EQ_ANCHORS_PCT = {0.05: -0.2132076984426745, 0.10: -0.24670587525119636}

CSV_COLUMNS = ["theta_dc", "mass_rel", "dm_pct", "mass_target", "Y_re", "Y_im",
               "d_op_pct", "phase_deg", "qs0_pct", "qs1_pct", "qs1k_pct",
               "r_ens_pp", "u_d_pp", "resumed", "g0_scope", "status"]


def five_point_grid(r: float) -> list[float]:
    return [r, 0.5 * (1.0 + r), 1.0, 0.5 * (3.0 - r), 2.0 - r]


def three_point_grid(r: float) -> list[float]:
    return [r, 0.5 * (1.0 + r), 1.0]


def classify_ensemble(points_by_theta: dict[float, list[dict[str, float]]],
                      *, resid_floor_pp: float = RESID_FLOOR_PP,
                      resid_frac: float = RESID_FRAC,
                      slope_agree_rel: float = SLOPE_AGREE_REL,
                      qs_flat_frac: float = QS_FLAT_FRAC) -> dict[str, Any]:
    """Frozen plan-section-2 classification (pure function, unit-tested).

    points_by_theta: {theta: [{dm_pct, d_op_pct, d_qs1_pct}, ...]} with the
    five-point grid on the smallest theta key carrying the linearity gate.
    """

    thetas = sorted(points_by_theta)
    th_lin = thetas[0]
    slopes: dict[float, float] = {}
    fits: dict[float, dict[str, Any]] = {}
    for th, pts in points_by_theta.items():
        dm = np.array([p["dm_pct"] for p in pts])
        dop = np.array([p["d_op_pct"] for p in pts])
        coef = np.polyfit(dm, dop, 1)
        resid = dop - np.polyval(coef, dm)
        slopes[th] = float(coef[0])
        fits[th] = {"slope_pp_per_pct": float(coef[0]),
                    "intercept_pp": float(coef[1]),
                    "max_abs_resid_pp": float(np.max(np.abs(resid))),
                    "span_pp": float(np.max(dop) - np.min(dop)),
                    "n_points": int(len(pts))}
    lin = fits[th_lin]
    lin_gate = max(resid_floor_pp, resid_frac * lin["span_pp"])
    lin_ok = lin["max_abs_resid_pp"] <= lin_gate

    s_lo = slopes[thetas[0]]
    s_hi = slopes[thetas[-1]] if len(thetas) > 1 else s_lo
    slope_ok = (abs(s_lo) > 1e-9
                and abs(s_hi / s_lo - 1.0) <= slope_agree_rel)

    qs_rows = []
    qs_ok = True
    for th, pts in points_by_theta.items():
        eq = min(pts, key=lambda p: abs(p["dm_pct"]))
        for p in pts:
            if abs(p["dm_pct"]) <= DM_ACTIVE_PCT:
                continue
            move = abs(p["d_op_pct"] - eq["d_op_pct"])
            qs_move = abs(p["d_qs1_pct"] - eq["d_qs1_pct"])
            ok = qs_move <= qs_flat_frac * move if move > 0 else False
            qs_rows.append({"theta": th, "dm_pct": p["dm_pct"],
                            "qs_move_pp": qs_move, "d_op_move_pp": move,
                            "frac": qs_move / move if move > 0 else float("inf"),
                            "ok": bool(ok)})
            qs_ok = qs_ok and ok

    if lin_ok and slope_ok and qs_ok:
        label = "ENSEMBLE_AXIS_CONFIRMED"
    elif lin_ok:
        label = "ENSEMBLE_AXIS_PARTIAL"
    else:
        label = "ENSEMBLE_AXIS_NOT_CONFIRMED"
    return {"label": label, "fits": {f"{t:g}": fits[t] for t in thetas},
            "lin_gate_pp": float(lin_gate), "lin_ok": bool(lin_ok),
            "slope_ratio": (float(s_hi / s_lo) if abs(s_lo) > 1e-9
                            else float("nan")),
            "slope_ok": bool(slope_ok), "qs_flat_rows": qs_rows,
            "qs_flat_ok": bool(qs_ok)}


def run_ensemble_scan(config_path: str | Path,
                      output_root: str | Path | None = None, *,
                      smoke: bool = False, workers: int | None = None,
                      ckpt_dir: str | Path | None = None) -> dict[str, Any]:
    import h5py
    import yaml

    t0 = datetime.now(timezone.utc)
    cfg_all = load_config(Path(config_path))
    proto = cfg_all["ensemble_scan_smoke" if smoke else "ensemble_scan"]
    gas_cfg = load_config(REPO_ROOT / str(cfg_all["inheritance"]["gas_config"]))

    log_lines: list[str] = []

    def log(msg: str) -> None:
        line = f"ENSSCAN {msg}"
        print(line, flush=True)
        log_lines.append(line)

    f_hz = float(proto["frequency_Hz"])
    n_phys = int(proto["n_phys"])
    nx = int(proto["nx"])
    spp_cfg = int(proto["samples_per_period"])
    settle_p = float(proto["settle_periods"])
    drive_p = float(proto["drive_periods"])
    eps_hot = float(proto["eps_ac_hot"])
    eps_cold = float(proto["eps_ac_cold"])
    n_ref_ladder = tuple(int(n) for n in proto.get("n_ref_ladder", N_REF_LADDER))
    win_main = tuple(float(v) for v in proto.get("fit_window_main",
                                                 FIT_WINDOW_MAIN))
    win_alt = tuple(float(v) for v in proto.get("fit_window_alt",
                                                FIT_WINDOW_ALT))
    if not smoke and (win_main != FIT_WINDOW_MAIN or win_alt != FIT_WINDOW_ALT
                      or n_ref_ladder != N_REF_LADDER):
        raise RuntimeError("auth protocol must keep the frozen fit windows "
                           "and N_ref ladder")

    mode = "smoke" if smoke else "auth"
    commit = _git_commit()
    ck_root = (Path(ckpt_dir) if ckpt_dir else
               REPO_ROOT / str(proto["ckpt_dir"]))
    ck_root.mkdir(parents=True, exist_ok=True)
    log(f"mode={mode} commit={commit} ckpt={ck_root} (judgement-run reuse)")

    # ---- mass scale and grids ----
    pack: dict[str, Any] | None = None
    if not smoke:
        pack = load_reference_pack(REPO_ROOT / str(proto["reference_pack"]))
        m0 = float(pack["points"]["0"]["m_wet_per_area"])
        log(f"reference pack ok; M0/A={m0:.12f}")
    else:
        probe0 = StrictBHalfDomain(gas_cfg, n_phys=n_phys, nx=nx)
        m0 = float(probe0.mapping.lattice.rho_ref_lu) * n_phys
        log(f"SMOKE equal-mass scale M0/A={m0}")

    scan_points: list[dict[str, Any]] = []   # theta, m_rel, mass, is_wet, labels
    for spec in proto["points"]:
        th = float(spec["theta_dc"])
        if "mass_rel" in spec:               # smoke: explicit grid, no wet flag
            grid = [(float(m), None) for m in spec["mass_rel"]]
        else:
            m_wet = float(pack["points"][f"{th:g}"]["m_wet_per_area"])
            r = m_wet / m0
            rel = (five_point_grid(r) if spec["grid"] == "five_point"
                   else three_point_grid(r))
            grid = [(m, (m_wet if i == 0 else None))
                    for i, m in enumerate(rel)]  # first entry = wet verbatim
        for m_rel, wet_mass in grid:
            is_wet = wet_mass is not None
            mass = wet_mass if is_wet else m_rel * m0
            slabel = f"th{th:g}" if is_wet else f"th{th:g}_mr{m_rel:.6f}"
            scan_points.append({"theta_dc": th, "m_rel": float(m_rel),
                                "mass": float(mass), "is_wet": is_wet,
                                "settle_label": slabel,
                                "drive_label": f"{slabel}_eps{eps_hot:g}"})

    common = dict(gas_cfg=gas_cfg, n_phys=n_phys, nx=nx, frequency_hz=f_hz,
                  samples_per_period=spp_cfg, ckpt_dir=str(ck_root))
    settle_payloads = [{**common, "label": "th0", "theta_dc": 0.0,
                        "settle_periods": settle_p, "mass_per_area": m0}]
    seen = {"th0"}
    for pt in scan_points:
        if pt["settle_label"] in seen:
            continue
        seen.add(pt["settle_label"])
        settle_payloads.append({**common, "label": pt["settle_label"],
                                "theta_dc": pt["theta_dc"],
                                "settle_periods": settle_p,
                                "mass_per_area": pt["mass"]})
    n_workers = workers if workers is not None else max(1, (os.cpu_count() or 4) - 2)
    settles = execute_cases(settle_payloads, n_workers, log,
                            worker=_sb_a2a_settle_worker)
    for lb in sorted(settles):
        r = settles[lb]
        if r.get("finite"):
            log(f"[settle {lb}] stat={r['stationarity_per_period']:.2e} "
                f"m_init={r['init_mass_rel']:.2e} "
                f"contract={r['contract_energy_rel_max']:.2e} "
                f"resumed={bool(r.get('resumed_from_checkpoint'))}")
        else:
            log(f"[settle {lb}] DEAD: {r}")
    if not all(settles.get(p["label"], {}).get("finite")
               for p in settle_payloads):
        raise RuntimeError("settle stage incomplete")

    drive_payloads = [{**common, "label": f"cold_eps{eps_cold:g}",
                       "theta_dc": 0.0, "eps_ac": eps_cold,
                       "drive_periods": drive_p, "settle_label": "th0",
                       "mass_per_area": m0}]
    for pt in scan_points:
        drive_payloads.append({**common, "label": pt["drive_label"],
                               "theta_dc": pt["theta_dc"], "eps_ac": eps_hot,
                               "drive_periods": drive_p,
                               "settle_label": pt["settle_label"],
                               "mass_per_area": pt["mass"]})
    drives = execute_cases(drive_payloads, n_workers, log,
                           worker=_sb_a2a_drive_worker)
    for lb in sorted(drives):
        r = drives[lb]
        if r.get("finite"):
            log(f"[drive {lb}] contract={r['contract_energy_rel_max']:.2e} "
                f"resumed={bool(r.get('resumed_from_checkpoint'))}")
        else:
            log(f"[drive {lb}] DEAD: {r}")

    # ---- post ----
    probe = StrictBHalfDomain(gas_cfg, n_phys=max(8, min(n_phys, 12)), nx=4)
    alpha_nom = float(probe.mapping.alpha_lu)
    rho_ref = float(probe.mapping.lattice.rho_ref_lu)
    theta0 = float(probe.mapping.theta_ref_lu)
    c_p = 0.5 * (int(probe.mapping.lattice.D) + int(probe.mapping.lattice.S)) + 1.0
    gamma = float(gas_cfg["physical"]["gamma"])
    om_lu = 2.0 * math.pi / _steps_per_period(probe, f_hz)
    g0_rows = load_g0_alpha_rows(REPO_ROOT / G0_TABLE_CSV)
    k_tab = np.array([r[0] for r in g0_rows])
    a_tab = np.array([r[1] for r in g0_rows])
    e_tab = np.array([e for _, e in fit_exponents(REPO_ROOT / G0_TABLE_CSV)])

    def fits_of(label: str):
        r = drives.get(label)
        if not (r and r.get("finite")):
            return None
        kw = dict(rho0=r["rho0"], cp_eff=r["cp_eff"], nx=r["nx"])
        return {"main": fit_admittance_window(r["drive"], f_hz, win_main, **kw),
                "alt": fit_admittance_window(r["drive"], f_hz, win_alt, **kw)}

    cold_label = f"cold_eps{eps_cold:g}"
    cold_fit = fits_of(cold_label)
    if cold_fit is None:
        raise RuntimeError("cold anchor case dead")
    y_cold = cold_fit["main"]["Y_face_theta_units"]
    y_cold_alt = cold_fit["alt"]["Y_face_theta_units"]
    ratio = y_cold / Y0_WET_COLD
    cold_anchor = {"amp_rel_err": float(abs(abs(ratio) - 1.0)),
                   "phase_deg_err": float(abs(_wrap_deg(math.degrees(
                       math.atan2(ratio.imag, ratio.real))))),
                   "passed": bool(abs(abs(ratio) - 1.0) <= GATE_COLD_AMP_REL
                                  and abs(_wrap_deg(math.degrees(math.atan2(
                                      ratio.imag, ratio.real))))
                                  <= GATE_COLD_PHASE_DEG)}
    cold_settle = settles["th0"]
    cold_legal = bool(
        cold_anchor["passed"]
        and cold_settle["contract_energy_rel_max"] <= GATE_CONTRACT_REL
        and cold_settle["init_mass_rel"] <= GATE_MASS_INIT_REL
        and cold_settle["mass_drift_rel_settle"] <= GATE_MASS_DRIFT_REL
        and cold_settle["stationarity_per_period"] <= GATE_STATIONARITY
        and cold_settle["q_dc_imbalance_abs"] <= cold_settle["closure_floor_lu"])

    rows: list[dict[str, Any]] = []
    points_by_theta: dict[float, list[dict[str, float]]] = {}
    all_legal = cold_legal
    for pt in scan_points:
        srow = settles[pt["settle_label"]]
        fit = fits_of(pt["drive_label"])
        drow = drives.get(pt["drive_label"], {})
        if fit is None or not srow.get("finite"):
            all_legal = False
            rows.append({"theta_dc": pt["theta_dc"], "mass_rel": pt["m_rel"],
                         "status": "CASE_DEAD", "g0_scope": G0_SCOPE})
            continue
        y = fit["main"]["Y_face_theta_units"]
        d_main = y / y_cold
        d_alt = fit["alt"]["Y_face_theta_units"] / y_cold_alt
        d_op = (abs(d_main) - 1.0) * 100.0
        dm_pct = (pt["mass"] / m0 - 1.0) * 100.0
        qs = qs_family_for_point(
            theta_dc=pt["theta_dc"],
            base_profile=np.array(srow["base_profile"]),
            rho_profile=np.array(srow["rho_profile"]),
            mass_per_area=pt["mass"], mass_per_area_cold=m0,
            cold_base_profile=np.array(cold_settle["base_profile"]),
            cold_rho_profile=np.array(cold_settle["rho_profile"]),
            n_phys=n_phys, omega_lu=om_lu, alpha_nom=alpha_nom,
            rho_ref=rho_ref, c_p=c_p, theta0=theta0, gamma=gamma,
            k_tab=k_tab, a_tab=a_tab, e_tab=e_tab,
            n_ref_ladder=n_ref_ladder)
        legality = {
            "contract": max(srow["contract_energy_rel_max"],
                            drow["contract_energy_rel_max"]) <= GATE_CONTRACT_REL,
            "init_mass": srow["init_mass_rel"] <= GATE_MASS_INIT_REL,
            "mass_drift": max(srow["mass_drift_rel_settle"],
                              drow["mass_drift_rel_drive"]) <= GATE_MASS_DRIFT_REL,
            "stationarity": srow["stationarity_per_period"] <= GATE_STATIONARITY,
            "dc_closure": srow["dc_closure_rel"] <= GATE_DC_CLOSURE,
        }
        if pt["is_wet"] and pack is not None:
            wp = pack["points"][f"{pt['theta_dc']:g}"]
            legality["pmean_vs_wet"] = (abs(srow["p_mean_lu"]
                                            / wp["p_mean_wet_lu"] - 1.0)
                                        <= GATE_PMEAN_REL_WET)
        legal = all(legality.values())
        all_legal = all_legal and legal
        row = {"theta_dc": pt["theta_dc"], "mass_rel": pt["m_rel"],
               "dm_pct": dm_pct, "mass_target": pt["mass"],
               "Y_re": y.real, "Y_im": y.imag,
               "d_op_pct": d_op,
               "phase_deg": math.degrees(math.atan2(d_main.imag, d_main.real)),
               "qs0_pct": qs["d_qs0_pct"], "qs1_pct": qs["d_qs1_pct"],
               "qs1k_pct": qs["d_qs1k_pct"],
               "r_ens_pp": d_op - qs["d_qs1_pct"],
               "u_d_pp": abs((abs(d_alt) - 1.0) * 100.0 - d_op),
               "resumed": bool(drow.get("resumed_from_checkpoint")),
               "g0_scope": G0_SCOPE,
               "status": ("wet_point;" if pt["is_wet"] else "scan_point;")
               + ("legal" if legal else "ILLEGAL")}
        rows.append(row)
        points_by_theta.setdefault(pt["theta_dc"], []).append(
            {"dm_pct": dm_pct, "d_op_pct": d_op, "d_qs1_pct": qs["d_qs1_pct"]})
        log(f"th={pt['theta_dc']:g} m_rel={pt['m_rel']:.6f} dm={dm_pct:+.3f}% "
            f"d_op={d_op:+.4f}% qs1={qs['d_qs1_pct']:+.4f}% legal={legal}")

    # ---- classification + report-only rows ----
    if all_legal and all(len(v) >= 3 for v in points_by_theta.values()):
        cls = classify_ensemble(points_by_theta)
        label = cls["label"]
    else:
        cls = {"label": "UNINTERPRETABLE_ENSEMBLE_SCAN"}
        label = cls["label"]
    if smoke:
        label = "SMOKE_" + label
    sign_reversal = [r for r in rows
                     if r.get("dm_pct", 0.0) > DM_ACTIVE_PCT
                     and r.get("d_op_pct", -1.0) > 0.0]
    tan_xcheck = {}
    for th, anchor in TAN_EQ_ANCHORS_PCT.items():
        pts = points_by_theta.get(th, [])
        eq = min(pts, key=lambda p: abs(p["dm_pct"])) if pts else None
        if eq is not None and abs(eq["dm_pct"]) <= DM_ACTIVE_PCT:
            diff = eq["d_op_pct"] - anchor
            tan_xcheck[f"{th:g}"] = {
                "in_frame_eq_mass_pct": eq["d_op_pct"],
                "tangent_anchor_pct": anchor, "diff_pp": diff,
                "reconciled_within_0p2pp": bool(abs(diff) <= TAN_XCHECK_PP)}
    log(f"classification={label} slopes={ {k: round(v['slope_pp_per_pct'],4) for k, v in cls.get('fits', {}).items()} } "
        f"sign_reversal_points={len(sign_reversal)}")

    # ---- files ----
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = (Path(output_root) if output_root
               else REPO_ROOT / "results" / "phase5" / CASE_FAMILY) / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "ensemble_scan.csv").open("w", newline="",
                                              encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, float("nan")) for k in CSV_COLUMNS})
    with h5py.File(out_dir / "signals.h5", "w") as h5:
        for lb, r in drives.items():
            if r.get("finite"):
                grp = h5.create_group(f"cases/{lb}")
                for key in ("t_s", "theta_w", "q_hot_lu", "q_cold_lu"):
                    grp.create_dataset(key, data=np.asarray(r["drive"][key]))
        for lb, r in settles.items():
            if r.get("finite"):
                grp = h5.create_group(f"settles/{lb}")
                grp.create_dataset("base_profile",
                                   data=np.array(r["base_profile"]))
                grp.create_dataset("rho_profile",
                                   data=np.array(r["rho_profile"]))
    digest = hashlib.sha256(json.dumps(
        {"rows": rows, "cls": cls}, sort_keys=True,
        default=str).encode()).hexdigest()[:12]
    summary = {
        "gate": UNIT, "run_id": run_id,
        "verdict": "COMPLETED" if all_legal else "LEGALITY_FAILED",
        "classification": label, "g0_scope": G0_SCOPE,
        "smoke_mode": bool(smoke), "branch": BRANCH,
        "mass_scale_m0_per_area": m0,
        "protocol": {"frequency_Hz": f_hz, "n_phys": n_phys, "nx": nx,
                     "samples_per_period": spp_cfg,
                     "settle_periods": settle_p, "drive_periods": drive_p,
                     "eps_ac_hot": eps_hot, "eps_ac_cold": eps_cold,
                     "fit_window_main": list(win_main),
                     "fit_window_alt": list(win_alt),
                     "n_ref_ladder": list(n_ref_ladder)},
        "frozen_lines": {"resid_floor_pp": RESID_FLOOR_PP,
                         "resid_frac": RESID_FRAC,
                         "slope_agree_rel": SLOPE_AGREE_REL,
                         "qs_flat_frac": QS_FLAT_FRAC,
                         "dm_active_pct": DM_ACTIVE_PCT,
                         "tan_xcheck_pp": TAN_XCHECK_PP,
                         "tan_eq_anchors_pct": {f"{k:g}": v for k, v in
                                                TAN_EQ_ANCHORS_PCT.items()},
                         "linearity_audit_gate": GATE_LINEARITY},
        "classification_detail": cls,
        "cold_anchor": {**cold_anchor, "Y_cold": _cplx(y_cold)},
        "cold_legal": cold_legal,
        "sign_reversal_rows": sign_reversal,
        "tangent_frame_xcheck": tan_xcheck,
        "rows": rows,
        "settle_metrics": {lb: {k: v for k, v in r.items()
                                if k not in ("base_profile", "rho_profile")}
                           for lb, r in settles.items() if r.get("finite")},
        "physics_core_digest": digest,
        "code_commit": commit,
        "wall_clock_min": (datetime.now(timezone.utc) - t0).total_seconds() / 60.0,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=1, default=float), encoding="utf-8")
    (out_dir / "config_resolved.yaml").write_text(
        yaml.safe_dump(cfg_all, allow_unicode=True, sort_keys=False),
        encoding="utf-8")
    (out_dir / "provenance.json").write_text(json.dumps(
        {"run_id": run_id, "family": CASE_FAMILY, "argv": sys.argv,
         "machine": os.environ.get("COMPUTERNAME", "unknown"),
         "python": sys.version, "workers": n_workers,
         "code_commit": commit, "ckpt_dir": str(ck_root),
         "started_utc": t0.isoformat(),
         "finished_utc": datetime.now(timezone.utc).isoformat()},
        indent=1), encoding="utf-8")
    (out_dir / "run_report.md").write_text("\n".join(
        [f"# {UNIT} run {run_id}", "",
         f"classification: **{label}** (g0_scope: {G0_SCOPE})", "", "```text"]
        + log_lines + ["```", ""]), encoding="utf-8")
    log(f"outputs -> {out_dir}")
    return {"verdict": summary["verdict"], "classification": label,
            "out_dir": str(out_dir), "summary": summary}


def main() -> int:
    ap = argparse.ArgumentParser(description="A2a-STRICT_B ensemble-axis scan")
    ap.add_argument("--config", default=str(
        REPO_ROOT / "configs" / "phase5" / "a2a_strict_b"
        / "ensemble_scan_10k_dx2p6.yaml"))
    ap.add_argument("--output-root", default=None)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--ckpt-dir", default=None)
    args = ap.parse_args()
    result = run_ensemble_scan(args.config, args.output_root, smoke=args.smoke,
                               workers=args.workers, ckpt_dir=args.ckpt_dir)
    return 0 if result["verdict"] == "COMPLETED" else 1


if __name__ == "__main__":
    sys.exit(main())
