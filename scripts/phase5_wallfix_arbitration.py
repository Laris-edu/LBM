"""Phase_5 A2-5 corrective counter-proof runner (wallfix arbitration, D0-7).

Question (user directive 2026-08-11): can a PRINCIPLED thermal-wall
modification — still mass-neutral, u_wall=0, exact wall-temperature
imposition, exact energy bookkeeping — make the LBM's finite-bias tangent
response agree with the continuum NSF isothermal wall, thereby proving the
JAB2-localized A2-5 anomaly is a removable boundary-implementation effect?

Design basis (frozen BEFORE any hot number from the v2 family; see the
wallfix report §2): the four invariants FORCE every scalar tangent channel
of the wall map, so the legal modification space is exactly

  repin  in {uniform (production), eqshape (equilibrium-shaped repin — the
             production C-step's own "no ghost content / min-norm" principle
             applied to the P step)},
  extrap in {row1 (production), linear (removes the O(dy) base-gradient
             offset of the copied non-equilibrium)},

implemented in boundary/wall_thermal_mass_neutral_v2.py (PROD = bitwise
production anchor) and measured with the frozen JAB tangent chain via
core/tangent_wallfix.py (propagate_tangent reused verbatim).

Protocols (transcribed from the frozen JAB config
configs/phase5/a2a_operating_point/jacobian_ablation_10k_dx2p6.yaml):
smoke = machinery/legality validation + shift screening ONLY — the smoke
grid does NOT reproduce the production sign (JAB1 smoke d_OP = +0.974%);
auth = the JAB authoritative grid (TAN windows verbatim), where the PROD
anchor must re-pass the 0.2 pp TAN identity gate.

Frozen judgement (auth mode, main points Theta in {0.05, 0.10}):
  gap = d_OP^NSF(g0) - d_OP^PROD;  move = (d_OP^V2 - d_OP^PROD)/gap
  WALLFIX_RESOLVED     : V2 positive at both points AND |V2 - NSF| <= 1.0 pp
  WALLFIX_SIGN_FLIPPED : V2 positive at both points, outside the NSF band
  WALLFIX_PARTIAL      : move >= 0.25 at both points, sign still negative
  WALLFIX_NULL         : move < 0.25 at either point
NSF reference = NSF hot-base arbitration lbm-equivalent(g0) full model
(run 20260811T055850Z): +1.1817 / +2.3445 pp. A NULL across the whole legal
family is itself decisive: no wall satisfying the four strict invariants can
remove the anomaly (the fix requires relaxing an invariant) — recorded as
WALLFIX_FAMILY_NULL.

Diagnostic unit: verdict vocabulary COMPLETED / LEGALITY_FAILED + labels;
no gate claims; production wall and frozen instruments untouched.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from boundary.wall_thermal_mass_neutral_v2 import (  # noqa: E402
    WALLFIX_VARIANTS,
    make_symmetric_band_callback_v2,
)
from core.macroscopic import recover_macro  # noqa: E402
from core.solver import GasSolver2D  # noqa: E402
from core.tangent_step import propagate_tangent  # noqa: E402
from core.tangent_wallfix import (  # noqa: E402
    WallfixTangentOperator,
    compute_stage_bases_wallfix,
)
from scripts.phase2_m2_verification import load_config  # noqa: E402
from scripts.phase5_g1a_amplitude_envelope import execute_cases  # noqa: E402
from scripts.phase5_g4a_dc_basestate import (  # noqa: E402
    conduction_seed,
    fit_admittance,
    make_energy_audited_band,
)
from scripts.phase5_wp4_jacobian_ablation import snapshot_to_base  # noqa: E402

UNIT = "WP4-WALLFIX"
GAS_CONFIG = "configs/gas_air_10k_d2q37_levelc_dx2p6.yaml"

# ---- frozen protocols (JAB config transcription; source in module docstring) ----
PROTO = {
    "smoke": {"hs_rows": 12, "nx": 4, "samples_per_period": 32,
              "theta_points": [0.05], "settle_periods": 2.0,
              "drive_periods": 2.0, "fit_skip_periods": 1.0,
              "h_ladder": [5.0e-5]},
    "auth": {"hs_rows": 48, "nx": 8, "samples_per_period": 64,
             "theta_points": [0.05, 0.10], "settle_periods": 5.0,
             "drive_periods": 4.0, "fit_skip_periods": 2.0,
             "h_ladder": [1.0e-4, 5.0e-5]},
}
FREQUENCY_HZ = 1.0e4

# ---- frozen legality gates (JAB config transcription) ----
GATE_STATIONARITY = 1.0e-3
GATE_DC_CLOSURE = 1.0e-3
GATE_R_F = 1.0e-5
GATE_V5_MASS = 1.0e-7
GATE_V5_ENERGY = 1.0e-5
GATE_V2_H_SPREAD = 1.0e-4          # |Y| rel spread across the auth h ladder
GATE_PROD_IDENTITY_PP = 0.2        # auth PROD vs frozen TAN references (V4 caliber)

# ---- frozen external references ----
TAN_DOP_PCT = {0.05: -2.8345129628396526, 0.10: -5.317059432017945}
NSF_G0_DOP_PCT = {0.05: 1.1816679235497007, 0.10: 2.344498614853485}
JAB1_SMOKE_DOP_PCT = 0.974          # smoke-grid PROD direction row (soft anchor)
CLASS_NSF_BAND_PP = 1.0
CLASS_MOVE_FRAC = 0.25
SCREEN_ACTIVE_PP = 0.1              # smoke |S| line flagging a live candidate

DEFAULT_VARIANTS = ["PROD", "V2EQ", "V2LIN", "V2EQL"]


# ---------------------------------------------------------------------------
# settle (run_tent phase-1 replica with the pluggable v2 wall family)
# ---------------------------------------------------------------------------

def settle_tent_wallfix(gas_cfg: dict, *, ny: int, nx: int, theta_dc: float,
                        frequency_hz: float, settle_periods: float,
                        samples_per_period: int, repin: str, extrap: str,
                        log=None) -> dict[str, Any]:
    """DC settle + snapshot with the v2 wall family on both bands.

    Faithful replica of scripts/phase5_g4a_dc_basestate.run_tent phase 1
    (same seed init, same audited-band composition, same step count and
    legality metrics); repin='uniform', extrap='row1' is asserted bitwise
    against run_tent(..., eps_ac=0, snapshot=True) in the contract tests.
    """

    cfg = copy.deepcopy(gas_cfg)
    cfg["numerics"] = {**cfg["numerics"], "nx": int(nx), "ny": int(ny)}
    solver = GasSolver2D(cfg)
    th0 = float(solver.mapping.theta_ref_lu)
    theta_amb = th0
    theta_hot_mean = th0 * (1.0 + float(theta_dc))
    rho0 = float(solver.mapping.lattice.rho_ref_lu)
    dt_s = float(solver.mapping.lattice.dt_s)
    lattice = solver.lattice
    D = int(solver.mapping.lattice.D)
    S = int(solver.mapping.lattice.S)
    hs = ny // 2
    steps_per_period = int(round(1.0 / (frequency_hz * dt_s)))
    sample_every = max(1, steps_per_period // int(samples_per_period))

    prof = conduction_seed(ny, theta_hot_mean, theta_amb)
    rho = rho0 * theta_amb / prof
    solver.initialize_from_macro(np.tile(rho[:, None], (1, nx)),
                                 np.zeros((ny, nx, 2)),
                                 np.tile(prof[:, None], (1, nx)))

    rec: dict[str, list[float]] = {}
    hot_inner = make_symmetric_band_callback_v2(
        float(theta_hot_mean), 0, repin=repin, extrap=extrap)
    sink_inner = make_symmetric_band_callback_v2(
        float(theta_amb), hs, repin=repin, extrap=extrap)
    hot_cb = make_energy_audited_band(hot_inner, rec, lattice, "hot")
    sink_cb = make_energy_audited_band(sink_inner, rec, lattice, "sink")

    def composed(**kw):
        f, g = hot_cb(**kw)
        kw2 = {**kw, "f_stream": f, "g_stream": g}
        return sink_cb(**kw2)

    n_settle = int(round(settle_periods * steps_per_period))
    stat_window = []
    mass_series = []
    for i in range(n_settle):
        solver.step(1, boundary_callback=composed)
        if i >= n_settle - steps_per_period and (i % sample_every == 0):
            m = recover_macro(solver.f, solver.g, D=D, S=S, lattice=lattice)
            prof_i = np.mean(m.theta, axis=1)
            if not np.all(np.isfinite(prof_i)):
                return {"finite": False, "phase": "settle", "step": i}
            stat_window.append(prof_i)
            mass_series.append(float(np.sum(solver.f)))
    stat = np.array(stat_window)
    base_profile = stat.mean(axis=0)
    stationarity = float(np.max(np.abs(stat[-1] - stat[0])) / theta_amb)
    per = steps_per_period
    q_hot_dc = float(np.mean(rec["hot_dE"][-per:]))
    q_sink_dc = float(np.mean(rec["sink_dE"][-per:]))
    dc_closure = abs(q_hot_dc + q_sink_dc) / max(abs(q_hot_dc), 1e-300)
    theta_dc_meas = float((base_profile[0] - theta_amb) / theta_amb)

    return {
        "finite": True, "ny": ny, "nx": nx, "hs": hs, "theta0": th0,
        "rho0": rho0, "dt_s": dt_s, "steps_per_period": steps_per_period,
        "stationarity_per_period": stationarity,
        "dc_closure_rel": dc_closure,
        "theta_dc_measured": theta_dc_meas,
        "q_hot_dc_lu": q_hot_dc, "q_sink_dc_lu": q_sink_dc,
        "mass_drift_settle": abs(mass_series[-1] / mass_series[0] - 1.0)
        if mass_series else float("nan"),
        "base_profile": base_profile,
        "snapshot": {
            "f": solver.f.copy(), "g": solver.g.copy(),
            "theta_hot_mean": float(theta_hot_mean),
            "theta_amb": float(theta_amb), "hs": int(hs),
            "ny": int(ny), "nx": int(nx),
            "theta_dc_target": float(theta_dc),
        },
    }


# ---------------------------------------------------------------------------
# picklable case workers (settle wave, tangent wave)
# ---------------------------------------------------------------------------

def _settle_ident(p: dict[str, Any]) -> dict[str, Any]:
    return {"variant": p["variant"], "theta_dc": float(p["theta_dc"]),
            "ny": int(p["ny"]), "nx": int(p["nx"]),
            "settle_periods": float(p["settle_periods"]),
            "samples_per_period": int(p["samples_per_period"])}


def _settle_worker(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    import os

    p = payload
    ident = _settle_ident(p)
    ck = Path(p["ckpt_dir"]) / f"settle_{p['label']}.npz" if p.get("ckpt_dir") else None
    if ck is not None and ck.exists():
        try:
            z = np.load(ck, allow_pickle=False)
            if json.loads(str(z["ident"])) == ident:
                meta = json.loads(str(z["meta"]))
                sident = json.loads(str(z["sident"]))
                run = {"finite": True, **meta,
                       "snapshot": {"f": z["f"], "g": z["g"], **sident},
                       "resumed_from_checkpoint": True}
                return p["label"], run
        except Exception:  # noqa: BLE001 - stale/corrupt checkpoint -> recompute
            pass
    repin, extrap = WALLFIX_VARIANTS[p["variant"]]
    run = settle_tent_wallfix(
        p["gas_cfg"], ny=p["ny"], nx=p["nx"], theta_dc=p["theta_dc"],
        frequency_hz=FREQUENCY_HZ, settle_periods=p["settle_periods"],
        samples_per_period=p["samples_per_period"], repin=repin, extrap=extrap)
    s = run.get("snapshot")
    if ck is not None and run.get("finite") and s is not None:
        tmp = ck.with_suffix(".tmp.npz")
        np.savez_compressed(
            tmp, f=s["f"], g=s["g"],
            meta=json.dumps({k: run[k] for k in (
                "stationarity_per_period", "dc_closure_rel",
                "theta_dc_measured", "mass_drift_settle",
                "steps_per_period")}),
            sident=json.dumps({k: s[k] for k in (
                "theta_hot_mean", "theta_amb", "hs", "ny", "nx",
                "theta_dc_target")}),
            ident=json.dumps(ident))
        os.replace(tmp, ck)
    return p["label"], run


def _tangent_worker(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    import os

    p = payload
    ident = {"variant": p["variant"], "h": float(p["h"]), "ny": int(p["ny"]),
             "nx": int(p["nx"]), "drive_periods": float(p["drive_periods"]),
             "fit_skip_periods": float(p["fit_skip_periods"]),
             "theta_hot_mean": float(p["hot_run"]["snapshot"]["theta_hot_mean"])}
    ck = (Path(p["ckpt_dir"]) / f"tangent_{p['label']}.json"
          if p.get("ckpt_dir") else None)
    if ck is not None and ck.exists():
        try:
            prev = json.loads(ck.read_text(encoding="utf-8"))
            if prev.get("ident") == ident:
                prev["resumed_from_checkpoint"] = True
                return p["label"], prev
        except Exception:  # noqa: BLE001
            pass
    repin, extrap = WALLFIX_VARIANTS[p["variant"]]
    cfg = copy.deepcopy(p["gas_cfg"])
    cfg["numerics"] = {**cfg["numerics"], "nx": int(p["nx"]), "ny": int(p["ny"])}
    solver = GasSolver2D(cfg)
    hot_base = snapshot_to_base(p["hot_run"])
    cold_base = snapshot_to_base(p["cold_run"])
    hot = compute_stage_bases_wallfix(solver, hot_base, repin=repin, extrap=extrap)
    cold = compute_stage_bases_wallfix(solver, cold_base, repin=repin, extrap=extrap)
    r_f_worst = max(hot.r_f, cold.r_f)
    op = WallfixTangentOperator(solver, hot_base, hot, cold_base, cold,
                                h=float(p["h"]), ablated=frozenset(),
                                repin=repin, extrap=extrap)
    run = propagate_tangent(op, frequency_hz=FREQUENCY_HZ,
                            drive_periods=p["drive_periods"],
                            samples_per_period=p["samples_per_period"],
                            log=None)
    fit = fit_admittance(run, FREQUENCY_HZ, p["fit_skip_periods"])
    out = {
        "Y": {"re": float(np.real(fit["Y_face_theta_units"])),
              "im": float(np.imag(fit["Y_face_theta_units"]))},
        "h2_q_rel": float(fit["h2_q_rel"]),
        "audits": run["audits"],
        "r_f_worst": float(r_f_worst),
        "finite": bool(run.get("finite", False)),
    }
    out["ident"] = ident
    if ck is not None:
        tmp = ck.with_suffix(".tmp")
        tmp.write_text(json.dumps(out, indent=1), encoding="utf-8")
        os.replace(tmp, ck)
    return p["label"], out


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------

def h_list_for(variant: str, proto: dict[str, Any]) -> list[float]:
    """Full h ladder for the primary candidate V2EQ (V2 spread check);
    single frozen h (ladder tail) for the other variants — keeps the auth
    wave inside one pool pass on the A machine."""

    return (list(proto["h_ladder"]) if variant == "V2EQ"
            else list(proto["h_ladder"])[-1:])


def _cplx_ratio_pct(y_hot: complex, y_cold: complex) -> dict[str, float]:
    d = y_hot / y_cold
    return {"d_op_pct": (abs(d) - 1.0) * 100.0,
            "phase_deg": math.degrees(math.atan2(d.imag, d.real))}


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              cwd=REPO_ROOT, capture_output=True, text=True,
                              timeout=10, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def classify(variant_rows: dict[float, dict], prod_rows: dict[float, dict],
             thetas: list[float]) -> dict[str, Any]:
    moves, v2_vals = [], []
    for th in thetas:
        d_v2 = variant_rows[th]["d_op_pct"]
        d_pr = prod_rows[th]["d_op_pct"]
        gap = NSF_G0_DOP_PCT[th] - d_pr
        moves.append((d_v2 - d_pr) / gap if abs(gap) > 1e-12 else 0.0)
        v2_vals.append(d_v2)
    pos = all(v > 0.0 for v in v2_vals)
    in_band = all(abs(v - NSF_G0_DOP_PCT[th]) <= CLASS_NSF_BAND_PP
                  for v, th in zip(v2_vals, thetas))
    if pos and in_band:
        label = "WALLFIX_RESOLVED"
    elif pos:
        label = "WALLFIX_SIGN_FLIPPED"
    elif all(m >= CLASS_MOVE_FRAC for m in moves):
        label = "WALLFIX_PARTIAL"
    else:
        label = "WALLFIX_NULL"
    return {"label": label, "d_op_pct": v2_vals,
            "move_frac": [float(m) for m in moves],
            "nsf_ref_pct": [NSF_G0_DOP_PCT[th] for th in thetas]}


def main() -> int:
    ap = argparse.ArgumentParser(description="A2-5 wallfix arbitration (D0-7)")
    ap.add_argument("--mode", choices=("smoke", "auth"), default="smoke")
    ap.add_argument("--variants", nargs="+", default=None,
                    help=f"subset of {list(WALLFIX_VARIANTS)} (PROD always added)")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--output-root", default=None)
    args = ap.parse_args()

    proto = PROTO[args.mode]
    variants = list(dict.fromkeys(["PROD"] + (args.variants or DEFAULT_VARIANTS)))
    for v in variants:
        if v not in WALLFIX_VARIANTS:
            raise SystemExit(f"unknown variant {v!r}")
    thetas = [float(t) for t in proto["theta_points"]]
    ny = 2 * int(proto["hs_rows"])
    nx = int(proto["nx"])
    import os
    workers = args.workers if args.workers is not None else max(1, (os.cpu_count() or 4) - 2)

    gas_cfg = load_config(REPO_ROOT / GAS_CONFIG)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = (Path(args.output_root) if args.output_root
                else REPO_ROOT / "results" / "phase5" / "wallfix_arbitration")
    out_dir = out_root / f"{run_id}_{args.mode}"
    out_dir.mkdir(parents=True, exist_ok=True)
    # checkpoint dir SHARED across relaunches (rule 3: per-case persistence +
    # identity-matching skip); keyed by mode + gas-config digest
    from scripts.phase2_m2_verification import sha256_file
    cfg_sha8 = sha256_file(REPO_ROOT / GAS_CONFIG)[:8]
    ckpt = out_root / f"checkpoints_{args.mode}_{cfg_sha8}"
    ckpt.mkdir(exist_ok=True)
    log = lambda msg: print(f"[{UNIT}] {msg}", flush=True)  # noqa: E731
    log(f"run {run_id} mode={args.mode} variants={variants} ny={ny} nx={nx} "
        f"h={proto['h_ladder']} workers={workers}")
    log("judgement frozen (module docstring): identity 0.2pp / legality "
        "JAB gates / RESOLVED band 1.0pp vs NSF g0 / move line 0.25 / "
        "smoke=screening-only")

    # ---- wave 1: settles (variant x (0 + thetas)) ----
    settle_payloads = []
    for v in variants:
        for th in [0.0] + thetas:
            settle_payloads.append({
                "label": f"{v}_th{th:g}", "variant": v, "theta_dc": th,
                "gas_cfg": gas_cfg, "ny": ny, "nx": nx,
                "settle_periods": proto["settle_periods"],
                "samples_per_period": proto["samples_per_period"],
                "ckpt_dir": str(ckpt),
            })
    settles = execute_cases(settle_payloads, workers, log, worker=_settle_worker)
    legality = {}
    legal_ok = True
    for lbl, run in settles.items():
        if "worker_exception" in run or not run.get("finite"):
            legality[lbl] = {"pass": False, "reason": run.get(
                "worker_exception", "non-finite settle")}
            legal_ok = False
            continue
        rows = {
            "stationarity_per_period": run["stationarity_per_period"],
            "dc_closure_rel": run["dc_closure_rel"],
            "theta_dc_measured": run["theta_dc_measured"],
            "mass_drift_settle": run["mass_drift_settle"],
        }
        th = run["snapshot"]["theta_dc_target"]
        rows["pass"] = bool(
            run["stationarity_per_period"] <= GATE_STATIONARITY
            and (th == 0.0 or run["dc_closure_rel"] <= GATE_DC_CLOSURE)
            and math.isfinite(run["mass_drift_settle"]))
        legality[lbl] = rows
        legal_ok = legal_ok and rows["pass"]
        log(f"settle {lbl}: stat={rows['stationarity_per_period']:.1e} "
            f"dc={rows['dc_closure_rel']:.1e} "
            f"theta_dc={rows['theta_dc_measured']:+.4f} "
            f"-> {'PASS' if rows['pass'] else 'FAIL'}")
    if not legal_ok:
        (out_dir / "summary.json").write_text(json.dumps(
            {"unit": UNIT, "run_id": run_id, "mode": args.mode,
             "verdict": "LEGALITY_FAILED", "stage": "settle",
             "legality": legality}, indent=1, default=str), encoding="utf-8")
        log("LEGALITY_FAILED at settle stage — aborting")
        return 1

    # ---- wave 2: tangent propagations (variant x theta_hot x h; cold shared) ----
    tang_payloads = []
    for v in variants:
        cold_run = settles[f"{v}_th0"]
        for h in h_list_for(v, proto):
            base_payload = {
                "variant": v, "h": h, "gas_cfg": gas_cfg, "ny": ny, "nx": nx,
                "cold_run": cold_run,
                "drive_periods": proto["drive_periods"],
                "samples_per_period": proto["samples_per_period"],
                "fit_skip_periods": proto["fit_skip_periods"],
                "ckpt_dir": str(ckpt),
            }
            # one cold leg per (variant, h) — shared by all hot points
            tang_payloads.append({**base_payload,
                                  "label": f"{v}_h{h:g}_cold",
                                  "hot_run": cold_run})
            for th in thetas:
                tang_payloads.append({**base_payload,
                                      "label": f"{v}_th{th:g}_h{h:g}_hot",
                                      "hot_run": settles[f"{v}_th{th:g}"]})
    tangs = execute_cases(tang_payloads, workers, log, worker=_tangent_worker)

    # ---- analysis ----
    audits_ok = True
    results: dict[str, dict] = {}
    for v in variants:
        rows: dict[float, dict] = {}
        for th in thetas:
            per_h = {}
            for h in h_list_for(v, proto):
                th_lbl = f"{v}_th{th:g}_h{h:g}_hot"
                c_lbl = f"{v}_h{h:g}_cold"
                rh, rc = tangs.get(th_lbl, {}), tangs.get(c_lbl, {})
                if "Y" not in rh or "Y" not in rc:
                    audits_ok = False
                    log(f"MISSING tangent case {th_lbl}/{c_lbl}")
                    continue
                for r, lbl in ((rh, th_lbl), (rc, c_lbl)):
                    a = r["audits"]
                    ok = (a["mass_tangent_rel_worst"] <= GATE_V5_MASS
                          and a["energy_account_rel_worst"] <= GATE_V5_ENERGY
                          and r["r_f_worst"] <= GATE_R_F)
                    if not ok:
                        audits_ok = False
                        log(f"AUDIT FAIL {lbl}: {a} r_f={r['r_f_worst']:.1e}")
                yh = complex(rh["Y"]["re"], rh["Y"]["im"])
                yc = complex(rc["Y"]["re"], rc["Y"]["im"])
                per_h[h] = _cplx_ratio_pct(yh, yc)
            ds = [per_h[h]["d_op_pct"] for h in per_h]
            spread = (max(ds) - min(ds)) if len(ds) > 1 else 0.0
            main_h = proto["h_ladder"][-1]
            rows[th] = {**per_h[main_h], "per_h": {f"{h:g}": per_h[h] for h in per_h},
                        "h_spread_pp": spread}
            log(f"{v} Theta={th:g}: d_OP={rows[th]['d_op_pct']:+.4f}pp"
                f"@{rows[th]['phase_deg']:+.3f}deg (h-spread {spread:.4f}pp)")
        results[v] = rows

    # PROD identity row
    identity = {}
    for th in thetas:
        d = results["PROD"][th]["d_op_pct"]
        if args.mode == "auth":
            dev = abs(d - TAN_DOP_PCT[th])
            identity[f"{th:g}"] = {"d_op_pct": d, "tan_ref_pct": TAN_DOP_PCT[th],
                                   "dev_pp": dev,
                                   "pass": bool(dev <= GATE_PROD_IDENTITY_PP)}
            audits_ok = audits_ok and identity[f"{th:g}"]["pass"]
        else:
            identity[f"{th:g}"] = {"d_op_pct": d,
                                   "jab1_smoke_ref_pct": JAB1_SMOKE_DOP_PCT,
                                   "dev_pp": abs(d - JAB1_SMOKE_DOP_PCT),
                                   "soft_anchor": True}
        log(f"PROD identity Theta={th:g}: {identity[f'{th:g}']}")

    classification = {}
    for v in variants:
        if v == "PROD":
            continue
        if args.mode == "auth":
            classification[v] = classify(results[v], results["PROD"], thetas)
        else:
            s = [results[v][th]["d_op_pct"] - results["PROD"][th]["d_op_pct"]
                 for th in thetas]
            classification[v] = {
                "label": ("SCREEN_ACTIVE" if any(abs(x) >= SCREEN_ACTIVE_PP for x in s)
                          else "SCREEN_WEAK"),
                "S_vs_prod_pp": [float(x) for x in s]}
        log(f"classify {v}: {classification[v]}")
    if args.mode == "auth" and classification and all(
            c["label"] == "WALLFIX_NULL" for c in classification.values()):
        classification["_family"] = {"label": "WALLFIX_FAMILY_NULL"}
        log("classify family: WALLFIX_FAMILY_NULL (no legal wall moves the anomaly)")

    verdict = "COMPLETED" if audits_ok else "LEGALITY_FAILED"
    summary = {
        "unit": UNIT, "run_id": run_id, "mode": args.mode, "verdict": verdict,
        "protocol": {**{k: v for k, v in proto.items()},
                     "frequency_Hz": FREQUENCY_HZ, "ny": ny, "nx": nx,
                     "variants": variants,
                     "gas_config": GAS_CONFIG,
                     "gates": {"stationarity": GATE_STATIONARITY,
                               "dc_closure": GATE_DC_CLOSURE, "r_f": GATE_R_F,
                               "v5_mass": GATE_V5_MASS,
                               "v5_energy": GATE_V5_ENERGY,
                               "prod_identity_pp": GATE_PROD_IDENTITY_PP,
                               "class_nsf_band_pp": CLASS_NSF_BAND_PP,
                               "class_move_frac": CLASS_MOVE_FRAC}},
        "legality_settle": legality,
        "prod_identity": identity,
        "results": {v: {f"{th:g}": results[v][th] for th in thetas}
                    for v in variants},
        "classification": classification,
        "external_references": {
            "tan_dop_pct": {f"{k:g}": v for k, v in TAN_DOP_PCT.items()},
            "nsf_g0_dop_pct": {f"{k:g}": v for k, v in NSF_G0_DOP_PCT.items()},
            "provenance": "TAN=archive/M5_runs/wp4_tan_20260805T092726Z_B; "
                          "NSF=results/phase5/nsf_arbitration/20260811T055850Z "
                          "(archived M5_runs/nsf_arb_20260811T055850Z)",
        },
        "machine": {"node": platform.node(), "platform": platform.platform(),
                    "python": sys.version.split()[0], "numpy": np.__version__,
                    "git_commit": _git_commit()},
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=1, default=str), encoding="utf-8")
    log(f"verdict={verdict}  outputs -> {out_dir}")
    return 0 if audits_ok else 1


if __name__ == "__main__":
    sys.exit(main())
