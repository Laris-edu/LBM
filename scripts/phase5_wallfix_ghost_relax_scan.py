"""Ghost-relaxation scan — the reviewer-line experiment (wallfix follow-up, D0-7).

Question (literature check §4b, user-directed 2026-08-11): the discrete-effect
tradition's standard remedy for boundary artifacts is TUNING THE FREE
RELAXATION PARAMETER of the non-hydrodynamic (ghost) moments (Zhang-Chai-Shi
line). Our stack's production closure (central_moment_closure=second_order)
sits at the full-regularization limit where that knob is projected out. This
scan re-opens the knob legitimately: switch to the supported fourth_order
closure branch, whose ``high_order_relaxation`` (high_tau) retains 4th-order
central non-equilibrium moments with factor (1 - 1/high_tau), anchor at
high_tau=1.0 (measured collide-level agreement with production second_order:
7.8e-10 relative on the seeded hot-profile state), and scan high_tau upward.

If d_OP does not move while the knob measurably changes the operator (and the
absolute admittance), the standard remedy is proven inapplicable to this
artifact — closing the "did you try the free relaxation parameter?" reviewer
line with a measurement instead of an argument.

Frozen judgement (before any scan number):
  ALIVENESS (dead-key guard, run start): one-collide rel diff between
      high_tau=1.5 and 1.0 on the seeded smoke state >= 1e-6 (probe: 2.2e-4);
  ANCHOR (auth): d_OP(high_tau=1.0) vs frozen TAN references within 0.2 pp
      (V4 caliber; probe predicts ~1e-5 pp level), deviation archived;
  SCAN: DELTA(ht) = d_OP(ht) - d_OP(1.0) at both hot points;
      all |DELTA| < 0.3 pp           -> GHOST_RELAX_NULL
      any ht with |DELTA| >= 0.3 pp
        at both points               -> GHOST_RELAX_ACTIVE (direction vs the
                                        NSF g0 reference reported)
  NON-DEGENERACY archive: |Y0|(ht)/|Y0|(1.0) - 1 per ht (measured knob
      response of the absolute admittance; no gate — the aliveness gate is
      at operator level).
Legality gates: JAB transcription, identical to the wallfix runner. The
production wall (PROD) is used unchanged in every case — this scan varies the
COLLISION ghost sector only.

DIAGNOSTIC ONLY (D0-7): high_tau != 1 rows carry no production validity
claim (production (tau,k) calibration is frozen by contract; this unit never
proposes retuning); no gate claims; verdict vocabulary COMPLETED /
LEGALITY_FAILED + scan labels.

Modes: smoke (machinery validation on the JAB smoke grid), auth (production
grid), full (smoke stage then auth stage, abort between on failure) — full is
the B-machine dispatch default. Per-case checkpoints + identity-matching
resume (labels carry high_tau; shared checkpoint dir per mode+config digest).
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

from core.collision_smrt import collide_fg  # noqa: E402
from core.solver import GasSolver2D  # noqa: E402
from scripts.phase2_m2_verification import load_config, sha256_file  # noqa: E402
from scripts.phase5_g1a_amplitude_envelope import execute_cases  # noqa: E402
from scripts.phase5_wallfix_arbitration import (  # noqa: E402
    FREQUENCY_HZ,
    GATE_DC_CLOSURE,
    GATE_R_F,
    GATE_STATIONARITY,
    GATE_V5_ENERGY,
    GATE_V5_MASS,
    GAS_CONFIG,
    NSF_G0_DOP_PCT,
    PROTO,
    TAN_DOP_PCT,
    _settle_worker,
    _tangent_worker,
)

UNIT = "WP4-GHOSTSCAN"

# ---- frozen scan protocol ----
HIGH_TAU_LADDER = (1.0, 1.05, 1.1, 1.2, 1.5)
CLOSURE = "fourth_order"
H_JVP = 5.0e-5                       # frozen mid-ladder JVP step (JAB caliber)
LINE_ALIVENESS_REL = 1.0e-6          # dead-key guard (probe measured 2.2e-4)
LINE_ANCHOR_PP = 0.2                 # auth ht=1.0 vs TAN frozen refs (V4 caliber)
LINE_SCAN_NULL_PP = 0.3              # per-ht |DELTA d_OP| null line
JAB1_SMOKE_DOP_PCT = 0.974           # smoke-grid soft anchor (JAB1 direction row)


def scan_gas_cfg(base_cfg: dict, high_tau: float) -> dict:
    cfg = copy.deepcopy(base_cfg)
    cfg["collision"] = {**cfg["collision"],
                        "central_moment_closure": CLOSURE,
                        "high_order_relaxation": float(high_tau)}
    return cfg


def aliveness_check(base_cfg: dict) -> dict[str, Any]:
    """Dead-key guard: the high_tau knob must change one collide output."""

    outs = {}
    for ht in (1.0, 1.5):
        cfg = scan_gas_cfg(base_cfg, ht)
        cfg["numerics"] = {**cfg["numerics"], "nx": 4, "ny": 24}
        s = GasSolver2D(cfg)
        th0 = float(s.mapping.theta_ref_lu)
        rho0 = float(s.mapping.lattice.rho_ref_lu)
        y = np.arange(24)
        prof = th0 * (1.0 + 0.05 * np.cos(2 * np.pi * y / 24))[:, None]
        theta = np.tile(prof, (1, 4))
        s.initialize_from_macro(rho0 * th0 / theta, np.zeros((24, 4, 2)), theta)
        s.step(5)
        fc, _ = collide_fg(s.f.copy(), s.g.copy(), s.mapping, lattice=s.lattice)
        outs[ht] = (fc, float(np.max(np.abs(fc))))
    rel = float(np.max(np.abs(outs[1.5][0] - outs[1.0][0]))) / max(
        outs[1.0][1], 1e-300)
    return {"rel_diff_1p5_vs_1p0": rel,
            "pass": bool(rel >= LINE_ALIVENESS_REL)}


def partition_ht(settles: dict[str, Any], ht_list: list[float],
                 thetas: list[float]) -> tuple[dict, dict]:
    """Per-ht settle legality partition (pure; unit-tested).

    Returns (legality rows per label, ht_status per ht with ok/reason).
    A ladder point survives only if ALL its settles (cold + hot) exist,
    are finite and pass the JAB legality gates.
    """

    legality: dict[str, Any] = {}
    ht_status: dict[str, dict] = {}
    for ht in ht_list:
        ok = True
        reasons: list[str] = []
        for th in [0.0] + list(thetas):
            lbl = f"ht{ht:g}_th{th:g}"
            run = settles.get(lbl, {})
            if "worker_exception" in run or not run.get("finite"):
                legality[lbl] = {"pass": False, "reason": run.get(
                    "worker_exception", "non-finite or missing settle")}
                ok = False
                reasons.append(f"{lbl}: {legality[lbl]['reason']}")
                continue
            row = {k: run[k] for k in (
                "stationarity_per_period", "dc_closure_rel",
                "theta_dc_measured", "mass_drift_settle")}
            row["pass"] = bool(
                run["stationarity_per_period"] <= GATE_STATIONARITY
                and (th == 0.0 or run["dc_closure_rel"] <= GATE_DC_CLOSURE)
                and math.isfinite(run["mass_drift_settle"]))
            legality[lbl] = row
            if not row["pass"]:
                ok = False
                reasons.append(f"{lbl}: legality gate")
        ht_status[f"{ht:g}"] = {"ok": ok,
                                "reason": "; ".join(reasons) or "all PASS"}
    return legality, ht_status


def _dop(y_hot: complex, y_cold: complex) -> dict[str, float]:
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


def run_stage(mode: str, base_cfg: dict, ht_list: list[float], workers: int,
              ckpt: Path, log) -> dict[str, Any]:
    proto = PROTO[mode]
    thetas = [float(t) for t in proto["theta_points"]]
    ny = 2 * int(proto["hs_rows"])
    nx = int(proto["nx"])

    # ---- settle wave: ht x (0 + thetas), PROD wall unchanged ----
    settle_payloads = []
    for ht in ht_list:
        for th in [0.0] + thetas:
            settle_payloads.append({
                "label": f"ht{ht:g}_th{th:g}", "variant": "PROD",
                "theta_dc": th, "gas_cfg": scan_gas_cfg(base_cfg, ht),
                "ny": ny, "nx": nx,
                "settle_periods": proto["settle_periods"],
                "samples_per_period": proto["samples_per_period"],
                "ckpt_dir": str(ckpt),
            })
    settles = execute_cases(settle_payloads, workers, log, worker=_settle_worker)
    legality, ht_status = partition_ht(settles, ht_list, thetas)
    for lbl, row in legality.items():
        log(f"settle {lbl}: {row}")
    ht_ok = [ht for ht in ht_list if ht_status[f"{ht:g}"]["ok"]]
    for ht in ht_list:
        if ht not in ht_ok:
            # A5 chi=0.01 precedent: an unstable ladder POINT is a measured
            # instrument-stability boundary, archived — not a scan failure.
            log(f"ht={ht:g}: MEASURED_UNSTABLE_OR_ILLEGAL "
                f"({ht_status[f'{ht:g}']['reason']}) — dropped from the "
                f"tangent wave, archived as a stability-boundary finding")
    if 1.0 not in ht_ok or len(ht_ok) < 2:
        return {"stage_verdict": "LEGALITY_FAILED", "legality": legality,
                "ht_status": ht_status,
                "reason": "anchor ht=1.0 dead or <2 surviving ladder points"}
    ht_list = ht_ok

    # ---- tangent wave: ht x (cold + hot points), single frozen h ----
    tang_payloads = []
    for ht in ht_list:
        cold_run = settles[f"ht{ht:g}_th0"]
        base_payload = {
            "variant": "PROD", "h": H_JVP,
            "gas_cfg": scan_gas_cfg(base_cfg, ht), "ny": ny, "nx": nx,
            "cold_run": cold_run,
            "drive_periods": proto["drive_periods"],
            "samples_per_period": proto["samples_per_period"],
            "fit_skip_periods": proto["fit_skip_periods"],
            "ckpt_dir": str(ckpt),
        }
        tang_payloads.append({**base_payload, "label": f"ht{ht:g}_cold",
                              "hot_run": cold_run})
        for th in thetas:
            tang_payloads.append({**base_payload,
                                  "label": f"ht{ht:g}_th{th:g}_hot",
                                  "hot_run": settles[f"ht{ht:g}_th{th:g}"]})
    tangs = execute_cases(tang_payloads, workers, log, worker=_tangent_worker)

    anchor_ok = True
    tangent_failed: dict[str, str] = {}
    rows: dict[str, dict] = {}
    for ht in ht_list:
        ht_ok_t = True
        reasons: list[str] = []

        def _leg(lbl):
            nonlocal ht_ok_t
            r = tangs.get(lbl, {})
            if "Y" not in r:
                ht_ok_t = False
                reasons.append(f"{lbl}: missing/failed")
                return None
            a = r["audits"]
            if not (a["mass_tangent_rel_worst"] <= GATE_V5_MASS
                    and a["energy_account_rel_worst"] <= GATE_V5_ENERGY
                    and r["r_f_worst"] <= GATE_R_F):
                ht_ok_t = False
                reasons.append(f"{lbl}: audit gate ({a}, r_f={r['r_f_worst']:.1e})")
                return None
            return r

        rc = _leg(f"ht{ht:g}_cold")
        per_theta: dict[str, Any] = {}
        if rc is not None:
            yc = complex(rc["Y"]["re"], rc["Y"]["im"])
            per_theta["Y0_abs"] = abs(yc)
            for th in thetas:
                rh = _leg(f"ht{ht:g}_th{th:g}_hot")
                if rh is not None:
                    yh = complex(rh["Y"]["re"], rh["Y"]["im"])
                    per_theta[f"{th:g}"] = _dop(yh, yc)
        if ht_ok_t:
            rows[f"{ht:g}"] = per_theta
            shown = {k: (round(v["d_op_pct"], 4) if isinstance(v, dict) else
                         round(v, 6)) for k, v in per_theta.items()}
            log(f"ht={ht:g}: {shown}")
        else:
            # anchor failure kills the stage; a scan point failing in the
            # TANGENT wave (after a legal settle) is archived and dropped —
            # same measured-boundary caliber as the settle partition.
            tangent_failed[f"{ht:g}"] = "; ".join(reasons)
            log(f"ht={ht:g}: TANGENT_FAILED ({tangent_failed[f'{ht:g}']})")
            if ht == 1.0:
                anchor_ok = False
    stage_ok = anchor_ok and len(rows) >= 2
    return {"stage_verdict": "COMPLETED" if stage_ok else "LEGALITY_FAILED",
            "legality": legality, "ht_status": ht_status,
            "tangent_failed": tangent_failed, "rows": rows,
            "thetas": [f"{t:g}" for t in thetas]}


def classify(rows: dict[str, dict], thetas: list[str]) -> dict[str, Any]:
    base = rows.get("1")
    if base is None:
        return {"label": "NO_ANCHOR"}
    out = {}
    any_active = False
    for ht_key, r in rows.items():
        if ht_key == "1":
            continue
        deltas = [r[t]["d_op_pct"] - base[t]["d_op_pct"] for t in thetas
                  if t in r and t in base]
        y0_shift = r["Y0_abs"] / base["Y0_abs"] - 1.0
        active = bool(deltas and all(abs(d) >= LINE_SCAN_NULL_PP
                                     for d in deltas))
        any_active = any_active or active
        out[ht_key] = {"delta_dop_pp": [float(d) for d in deltas],
                       "y0_abs_shift_rel": float(y0_shift),
                       "active": active}
    label = "GHOST_RELAX_ACTIVE" if any_active else "GHOST_RELAX_NULL"
    return {"label": label, "per_ht": out,
            "nsf_ref_pct": {t: NSF_G0_DOP_PCT[float(t)] for t in thetas
                            if float(t) in NSF_G0_DOP_PCT}}


def main() -> int:
    ap = argparse.ArgumentParser(description="ghost-relaxation d_OP scan (D0-7)")
    ap.add_argument("--mode", choices=("smoke", "auth", "full"), default="full")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--output-root", default=None)
    args = ap.parse_args()

    import os
    workers = args.workers if args.workers is not None else max(
        1, (os.cpu_count() or 4) - 2)
    base_cfg = load_config(REPO_ROOT / GAS_CONFIG)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = (Path(args.output_root) if args.output_root
                else REPO_ROOT / "results" / "phase5" / "wallfix_ghost_relax")
    out_dir = out_root / f"{run_id}_{args.mode}"
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg_sha8 = sha256_file(REPO_ROOT / GAS_CONFIG)[:8]
    log = lambda m: print(f"[{UNIT}] {m}", flush=True)  # noqa: E731
    log(f"run {run_id} mode={args.mode} closure={CLOSURE} "
        f"ht={list(HIGH_TAU_LADDER)} h={H_JVP:g} workers={workers}")
    log("judgement frozen (module docstring): aliveness>=1e-6 / anchor 0.2pp "
        "vs TAN / scan null <0.3pp / Y0 shifts archived / PROD wall unchanged")

    alive = aliveness_check(base_cfg)
    log(f"aliveness collide rel-diff ht1.5 vs 1.0 = "
        f"{alive['rel_diff_1p5_vs_1p0']:.3e} -> "
        f"{'PASS' if alive['pass'] else 'FAIL (dead key)'}")
    summary: dict[str, Any] = {
        "unit": UNIT, "run_id": run_id, "mode": args.mode,
        "protocol": {"closure": CLOSURE, "high_tau_ladder": list(HIGH_TAU_LADDER),
                     "h_jvp": H_JVP, "gas_config": GAS_CONFIG,
                     "wall": "PROD (production v1.1, unchanged)",
                     "lines": {"aliveness_rel": LINE_ALIVENESS_REL,
                               "anchor_pp": LINE_ANCHOR_PP,
                               "scan_null_pp": LINE_SCAN_NULL_PP}},
        "aliveness": alive,
        "machine": {"node": platform.node(), "platform": platform.platform(),
                    "python": sys.version.split()[0], "numpy": np.__version__,
                    "git_commit": _git_commit()},
    }
    if not alive["pass"]:
        summary["verdict"] = "LEGALITY_FAILED"
        (out_dir / "summary.json").write_text(
            json.dumps(summary, indent=1, default=str), encoding="utf-8")
        log("verdict=LEGALITY_FAILED (dead knob) — aborting")
        return 1

    stages = (["smoke", "auth"] if args.mode == "full" else [args.mode])
    verdict = "COMPLETED"
    for stage in stages:
        log(f"---- stage {stage} ----")
        ckpt = out_root / f"checkpoints_{stage}_{cfg_sha8}_ghost"
        ckpt.mkdir(parents=True, exist_ok=True)
        res = run_stage(stage, base_cfg, list(HIGH_TAU_LADDER), workers,
                        ckpt, log)
        summary[f"stage_{stage}"] = res
        if res["stage_verdict"] != "COMPLETED":
            verdict = "LEGALITY_FAILED"
            log(f"stage {stage} LEGALITY_FAILED — aborting")
            break
        thetas = res["thetas"]
        cls = classify(res["rows"], thetas)
        summary[f"classification_{stage}"] = cls
        log(f"classification[{stage}]: {cls['label']}")
        if stage == "auth":
            anchor = {}
            base_rows = res["rows"].get("1", {})
            a_ok = True
            for t in thetas:
                if float(t) not in TAN_DOP_PCT or t not in base_rows:
                    continue
                dev = abs(base_rows[t]["d_op_pct"] - TAN_DOP_PCT[float(t)])
                anchor[t] = {"d_op_pct": base_rows[t]["d_op_pct"],
                             "tan_ref_pct": TAN_DOP_PCT[float(t)],
                             "dev_pp": dev,
                             "pass": bool(dev <= LINE_ANCHOR_PP)}
                a_ok = a_ok and anchor[t]["pass"]
                log(f"anchor ht=1.0 th={t}: dev={dev:.5f}pp "
                    f"-> {'PASS' if anchor[t]['pass'] else 'FAIL'}")
            summary["anchor_auth"] = anchor
            if not a_ok:
                verdict = "LEGALITY_FAILED"
        elif stage == "smoke":
            b = res["rows"].get("1", {}).get("0.05")
            if b:
                summary["smoke_soft_anchor"] = {
                    "d_op_pct": b["d_op_pct"],
                    "jab1_smoke_ref_pct": JAB1_SMOKE_DOP_PCT,
                    "dev_pp": abs(b["d_op_pct"] - JAB1_SMOKE_DOP_PCT),
                    "soft_anchor": True}
                log(f"smoke soft anchor: {summary['smoke_soft_anchor']}")

    summary["verdict"] = verdict
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=1, default=str), encoding="utf-8")
    log(f"verdict={verdict}  outputs -> {out_dir}")
    return 0 if verdict == "COMPLETED" else 1


if __name__ == "__main__":
    sys.exit(main())
