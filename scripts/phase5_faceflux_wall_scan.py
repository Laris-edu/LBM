"""D1 candidate-B measurement — face-flux wall vs production, tangent d_OP (D0-7).

QUESTION (user directive 2026-08-17; derivation D1_v1.1, judgement transcribed
here because Manuscript/ is not in the repo): the paper-level tangent algebra
proved the face-temperature Dirichlet-to-flux wall (candidate B) removes the
A2-5 storage channel ``c_v rho_row * d(theta_w)`` from the macroscopic
boundary map (D1.43/D1.49) and judged it GO_TO_IMPLEMENTATION.  Does the
IMPLEMENTED candidate B flip the finite-bias operating-point tangent trend of
the certified stack toward the continuum reference?

INSTRUMENT: boundary/wall_face_flux.py (flux-fed buffer realization; design
rationale in its docstring) + core/tangent_faceflux.py (JAB tangent chain,
band stage swapped, wallfix paradigm).  The PROD variant reuses the wallfix
arbitration workers verbatim — their production path is bitwise-anchored to
the frozen instrument in the wallfix contract tests, so the anchor is
inherited, not reimplemented.

GEOMETRY (state matching, D1 section 13.5 item 2): the Dirichlet plane moves
from the band node to the faces at +-dy/2, so the faceflux rig runs
hs_ff = hs_prod + 1 (auth 49 vs 48, smoke 13 vs 12) — face-to-face slab
thickness equals the production node-to-node H_s exactly (48 dy auth,
H_s/delta_T = 4.7124 preserved).

FROZEN JUDGEMENT (constants below; registered before any faceflux hot number):

  single-step contract   every settle asserts wrapper-measured band energy ==
                         independently computed formula flux, worst ABSOLUTE
                         deviation <= 1e-10 LU (D1.70; the deviation is float
                         noise on O(10)-LU grid-energy sums, so the honest
                         scale is the grid energy, not the tiny flux); mass
                         drift and u=0 inherited machine-exact from the
                         certified machinery.
  PROD anchor (auth)     production d_OP within 0.2 pp of the frozen TAN
                         references (V4 caliber).  Fails -> LEGALITY_FAILED.
  cold diagnostic anchor |Y0_faceflux / Y0_prod - 1| <= 10% (D1 pre-registered
                         diagnostic window).  The D1 budget band expectation
                         [-6%, -1%] (lumped -4.78% .. open-loop -2.42%, plus
                         O(1%) buffer terms) is ARCHIVED, not gating.
  face-Dirichlet row     gas-side extrapolated DC face temperature
                         theta_face = theta_1 + (q_formula d_f / k_nom) vs
                         theta_w: |dev| / (theta_w - theta_amb) <= 1e-2,
                         archived consistency row (soft; miss flags, does not
                         fail the stage).
  legality               JAB gates verbatim: stationarity <= 1e-3, dc_closure
                         <= 1e-3, r_F <= 1e-5, V5 mass <= 1e-7, V5 energy
                         account <= 1e-5.
  classification (auth)  the PRE-REGISTERED wallfix lines verbatim (classify()
                         imported from the wallfix runner):
                           WALLFIX_RESOLVED     positive at both hot points AND
                                                |d_OP - NSF g0| <= 1.0 pp
                           WALLFIX_SIGN_FLIPPED positive both, outside the band
                           WALLFIX_PARTIAL      move >= 0.25 of the NSF gap at
                                                both points, sign still negative
                           WALLFIX_NULL         move < 0.25 at either point
                         NSF g0 reference: +1.1817 / +2.3445 pp (frozen).
  known channels         (archived interpretation aids, D1 section 13) the
                         face-resistance correction carries its own
                         operating-point dependence ~ +0.25/+0.50 pp at
                         Theta=0.05/0.10 (D1.76); the frozen G_f omits the
                         constitutive k(T) trend of the face conductance.

Failure semantics: an unstable/illegal faceflux case is archived as a measured
boundary (A5 chi-endpoint precedent); only a dead PROD anchor fails a stage.
If candidate B fails cold or does not flip hot, the D1 structural derivation
stands; the failure would mean removing A2-5 is insufficient for the full
operator (D1 section 10.2 last paragraph) — an archivable result either way.

DIAGNOSTIC ONLY (D0-7): verdict vocabulary COMPLETED / LEGALITY_FAILED +
labels; no gate claims; production wall and frozen instruments untouched;
the faceflux wall carries no production validity claim.

Modes: smoke (machinery + screening; steep rig, does NOT reproduce the
production sign), auth (judgement grid), full (smoke then auth).  Per-case
checkpoints + identity-matching resume shared per mode+config digest.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
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

from boundary.wall_face_flux import (  # noqa: E402
    FACE_DISTANCE_LU,
    faceflux_conductance_lu,
    faceflux_formula_flux,
    make_faceflux_band_callback,
)
from core.macroscopic import recover_macro  # noqa: E402
from core.solver import GasSolver2D  # noqa: E402
from core.tangent_step import propagate_tangent  # noqa: E402
from core.tangent_faceflux import (  # noqa: E402
    FaceFluxTangentOperator,
    compute_stage_bases_faceflux,
)
from scripts.phase2_m2_verification import load_config, sha256_file  # noqa: E402
from scripts.phase5_g1a_amplitude_envelope import execute_cases  # noqa: E402
from scripts.phase5_g4a_dc_basestate import (  # noqa: E402
    conduction_seed,
    fit_admittance,
    make_energy_audited_band,
)
from scripts.phase5_wallfix_arbitration import (  # noqa: E402
    FREQUENCY_HZ,
    GAS_CONFIG,
    GATE_DC_CLOSURE,
    GATE_R_F,
    GATE_STATIONARITY,
    GATE_V5_ENERGY,
    GATE_V5_MASS,
    NSF_G0_DOP_PCT,
    PROTO,
    TAN_DOP_PCT,
    classify,
    _settle_worker as _prod_settle_worker,
    _tangent_worker as _prod_tangent_worker,
)
from scripts.phase5_wp4_jacobian_ablation import snapshot_to_base  # noqa: E402

UNIT = "D1-FACEFLUX"

# ---------------------------------------------------------------------------
# FROZEN JUDGEMENT LINES (registered before any faceflux hot number)
# ---------------------------------------------------------------------------
H_JVP = 5.0e-5                       # frozen JVP step (JAB caliber)
LINE_PROD_ANCHOR_PP = 0.2            # auth PROD vs frozen TAN (V4 caliber)
LINE_COLD_DIAG_REL = 0.10            # |Y0_ff/Y0_prod - 1| diagnostic window (D1)
COLD_BUDGET_BAND_REL = (-0.06, -0.01)  # archived expectation, non-gating
LINE_STEP_CONTRACT_ABS_LU = 1.0e-10  # wrapper==formula worst ABS dev, LU (D1.70)
LINE_FACE_TEMP_DC_REL = 1.0e-2       # archived soft row (gas-side extrap face T)
JAB1_SMOKE_DOP_PCT = 0.974           # smoke-grid PROD soft anchor
# classification lines live in the imported wallfix classify() (frozen there):
# NSF band 1.0 pp, move fraction 0.25, references TAN_DOP_PCT / NSF_G0_DOP_PCT.

VARIANTS = ("PROD", "FACEFLUX")


def proto_for(mode: str, variant: str) -> dict[str, Any]:
    """Frozen protocol per variant: FACEFLUX runs hs+1 (state matching)."""

    p = dict(PROTO[mode])
    if variant == "FACEFLUX":
        p["hs_rows"] = int(p["hs_rows"]) + 1
    return p


# ---------------------------------------------------------------------------
# FACEFLUX settle (run_tent phase-1 replica with the candidate-B bands)
# ---------------------------------------------------------------------------

def settle_tent_faceflux(gas_cfg: dict, *, ny: int, nx: int, theta_dc: float,
                         frequency_hz: float, settle_periods: float,
                         samples_per_period: int) -> dict[str, Any]:
    """DC settle + snapshot with candidate-B bands on both rows.

    Same seed, audited-band composition, step count and legality metrics as
    scripts/phase5_g4a_dc_basestate.run_tent phase 1; additionally records the
    per-step wrapper-vs-formula identity (D1.70) and the gas-side extrapolated
    DC face temperature (face-Dirichlet consistency row).
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
    g_face = faceflux_conductance_lu(solver.mapping)
    k_nom = g_face * FACE_DISTANCE_LU
    steps_per_period = int(round(1.0 / (frequency_hz * dt_s)))
    sample_every = max(1, steps_per_period // int(samples_per_period))

    prof = conduction_seed(ny, theta_hot_mean, theta_amb)
    rho = rho0 * theta_amb / prof
    solver.initialize_from_macro(np.tile(rho[:, None], (1, nx)),
                                 np.zeros((ny, nx, 2)),
                                 np.tile(prof[:, None], (1, nx)))

    rec: dict[str, list[float]] = {}
    hot_inner = make_faceflux_band_callback(float(theta_hot_mean), 0,
                                            g_face=g_face)
    sink_inner = make_faceflux_band_callback(float(theta_amb), hs,
                                             g_face=g_face)
    hot_cb = make_energy_audited_band(hot_inner, rec, lattice, "hot")
    sink_cb = make_energy_audited_band(sink_inner, rec, lattice, "sink")

    contract_worst = 0.0

    def composed(**kw):
        nonlocal contract_worst
        # formula fluxes from the SAME streamed state the bands will consume
        # (hot first; the sink's neighbour rows are untouched by the hot band)
        qh_u, qh_d = faceflux_formula_flux(
            kw["solver"], kw["f_stream"], kw["g_stream"], theta_hot_mean,
            row=0, g_face=g_face)
        f, g = hot_cb(**kw)
        qs_u, qs_d = faceflux_formula_flux(
            kw["solver"], f, g, theta_amb, row=hs, g_face=g_face)
        kw2 = {**kw, "f_stream": f, "g_stream": g}
        f, g = sink_cb(**kw2)
        # D1.70: the wrapper's recorded delta must equal the formula sum
        # (absolute LU deviation; float noise floor of the O(10)-LU grid sums)
        dev = max(abs(rec["hot_dE"][-1] - float(np.sum(qh_u + qh_d))),
                  abs(rec["sink_dE"][-1] - float(np.sum(qs_u + qs_d))))
        contract_worst = max(contract_worst, dev)
        return f, g

    n_settle = int(round(settle_periods * steps_per_period))
    stat_window = []
    mass_series = []
    for i in range(n_settle):
        solver.step(1, boundary_callback=composed)
        if i % sample_every == 0 and not np.all(np.isfinite(solver.f)):
            return {"finite": False, "phase": "settle", "step": i,
                    "reason": "non-finite populations during settle"}
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

    # face-Dirichlet consistency: gas-side extrapolation to the hot face
    # theta_face = theta_1 + q_face * d_f / k_nom (per-side DC average)
    q_face_dc = 0.5 * q_hot_dc / nx        # per column, per face (symmetric)
    th1_up = float(base_profile[1 % ny])
    th1_dn = float(base_profile[(ny - 1) % ny])
    th_face = 0.5 * (th1_up + th1_dn) + q_face_dc * FACE_DISTANCE_LU / k_nom
    denom = max(abs(theta_hot_mean - theta_amb), 1e-300)
    face_dev_rel = abs(th_face - theta_hot_mean) / denom if theta_dc > 0 \
        else abs(th_face - theta_hot_mean) / theta_amb

    return {
        "finite": True, "ny": ny, "nx": nx, "hs": hs, "theta0": th0,
        "rho0": rho0, "dt_s": dt_s, "steps_per_period": steps_per_period,
        "stationarity_per_period": stationarity,
        "dc_closure_rel": dc_closure,
        "theta_dc_measured": float((th_face - theta_amb) / theta_amb),
        "step_contract_rel_worst": contract_worst,
        "face_temp_dev_rel": float(face_dev_rel),
        "q_hot_dc_lu": q_hot_dc, "q_sink_dc_lu": q_sink_dc,
        "mass_drift_settle": abs(mass_series[-1] / mass_series[0] - 1.0)
        if mass_series else float("nan"),
        "base_profile": base_profile,
        "g_face_lu": g_face,
        "snapshot": {
            "f": solver.f.copy(), "g": solver.g.copy(),
            "theta_hot_mean": float(theta_hot_mean),
            "theta_amb": float(theta_amb), "hs": int(hs),
            "ny": int(ny), "nx": int(nx),
            "theta_dc_target": float(theta_dc),
        },
    }


# ---------------------------------------------------------------------------
# picklable workers (FACEFLUX; PROD reuses the wallfix workers verbatim)
# ---------------------------------------------------------------------------

def _ff_settle_ident(p: dict[str, Any]) -> dict[str, Any]:
    return {"variant": "FACEFLUX", "theta_dc": float(p["theta_dc"]),
            "ny": int(p["ny"]), "nx": int(p["nx"]),
            "settle_periods": float(p["settle_periods"]),
            "samples_per_period": int(p["samples_per_period"])}


def _ff_settle_worker(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    p = payload
    ident = _ff_settle_ident(p)
    ck = (Path(p["ckpt_dir"]) / f"settle_{p['label']}.npz"
          if p.get("ckpt_dir") else None)
    if ck is not None and ck.exists():
        try:
            z = np.load(ck, allow_pickle=False)
            if json.loads(str(z["ident"])) == ident:
                meta = json.loads(str(z["meta"]))
                sident = json.loads(str(z["sident"]))
                return p["label"], {"finite": True, **meta,
                                    "snapshot": {"f": z["f"], "g": z["g"], **sident},
                                    "resumed_from_checkpoint": True}
        except Exception:  # noqa: BLE001 - stale checkpoint -> recompute
            pass
    run = settle_tent_faceflux(
        p["gas_cfg"], ny=p["ny"], nx=p["nx"], theta_dc=p["theta_dc"],
        frequency_hz=FREQUENCY_HZ, settle_periods=p["settle_periods"],
        samples_per_period=p["samples_per_period"])
    s = run.get("snapshot")
    if ck is not None and run.get("finite") and s is not None:
        tmp = ck.with_suffix(".tmp.npz")
        np.savez_compressed(
            tmp, f=s["f"], g=s["g"],
            meta=json.dumps({k: run[k] for k in (
                "stationarity_per_period", "dc_closure_rel",
                "theta_dc_measured", "mass_drift_settle", "steps_per_period",
                "step_contract_rel_worst", "face_temp_dev_rel", "g_face_lu")}),
            sident=json.dumps({k: s[k] for k in (
                "theta_hot_mean", "theta_amb", "hs", "ny", "nx",
                "theta_dc_target")}),
            ident=json.dumps(ident))
        os.replace(tmp, ck)
    return p["label"], run


def _ff_tangent_worker(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    p = payload
    ident = {"variant": "FACEFLUX", "h": float(p["h"]), "ny": int(p["ny"]),
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
    cfg = copy.deepcopy(p["gas_cfg"])
    cfg["numerics"] = {**cfg["numerics"], "nx": int(p["nx"]), "ny": int(p["ny"])}
    solver = GasSolver2D(cfg)
    g_face = faceflux_conductance_lu(solver.mapping)
    hot_base = snapshot_to_base(p["hot_run"])
    cold_base = snapshot_to_base(p["cold_run"])
    hot = compute_stage_bases_faceflux(solver, hot_base, g_face=g_face)
    cold = compute_stage_bases_faceflux(solver, cold_base, g_face=g_face)
    r_f_worst = max(hot.r_f, cold.r_f)
    op = FaceFluxTangentOperator(solver, hot_base, hot, cold_base, cold,
                                 h=float(p["h"]), ablated=frozenset(),
                                 g_face=g_face)
    run = propagate_tangent(op, frequency_hz=FREQUENCY_HZ,
                            drive_periods=p["drive_periods"],
                            samples_per_period=p["samples_per_period"], log=None)
    fit = fit_admittance(run, FREQUENCY_HZ, p["fit_skip_periods"])
    out = {
        "Y": {"re": float(np.real(fit["Y_face_theta_units"])),
              "im": float(np.imag(fit["Y_face_theta_units"]))},
        "h2_q_rel": float(fit["h2_q_rel"]),
        "audits": run["audits"],
        "r_f_worst": float(r_f_worst),
        "finite": bool(run.get("finite", False)),
        "ident": ident,
    }
    if ck is not None:
        tmp = ck.with_suffix(".tmp")
        tmp.write_text(json.dumps(out, indent=1), encoding="utf-8")
        os.replace(tmp, ck)
    return p["label"], out


def _dispatch_settle(payload):
    if payload["variant"] == "PROD":
        return _prod_settle_worker(payload)
    return _ff_settle_worker(payload)


def _dispatch_tangent(payload):
    if payload["variant"] == "PROD":
        return _prod_tangent_worker(payload)
    return _ff_tangent_worker(payload)


# ---------------------------------------------------------------------------
# stage orchestration
# ---------------------------------------------------------------------------

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


def run_stage(mode: str, base_cfg: dict, workers: int, ckpt: Path,
              log) -> dict[str, Any]:
    thetas = [float(t) for t in PROTO[mode]["theta_points"]]

    settle_payloads = []
    for v in VARIANTS:
        proto = proto_for(mode, v)
        ny = 2 * int(proto["hs_rows"])
        nx = int(proto["nx"])
        for th in [0.0] + thetas:
            settle_payloads.append({
                "label": f"{v}_th{th:g}", "variant": v, "theta_dc": th,
                "gas_cfg": base_cfg, "ny": ny, "nx": nx,
                "settle_periods": proto["settle_periods"],
                "samples_per_period": proto["samples_per_period"],
                "ckpt_dir": str(ckpt),
            })
    settles = execute_cases(settle_payloads, workers, log, worker=_dispatch_settle)

    legality: dict[str, Any] = {}
    status: dict[str, dict] = {}
    for v in VARIANTS:
        ok = True
        reasons: list[str] = []
        for th in [0.0] + thetas:
            lbl = f"{v}_th{th:g}"
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
            if v == "FACEFLUX":
                row["step_contract_abs_worst"] = run.get("step_contract_rel_worst")
                row["face_temp_dev_rel"] = run.get("face_temp_dev_rel")
                if (run.get("step_contract_rel_worst") is not None
                        and run["step_contract_rel_worst"] > LINE_STEP_CONTRACT_ABS_LU):
                    row["pass"] = False
                    reasons.append(f"{lbl}: step contract "
                                   f"{run['step_contract_rel_worst']:.2e}")
                if (run.get("face_temp_dev_rel") is not None
                        and run["face_temp_dev_rel"] > LINE_FACE_TEMP_DC_REL):
                    row["face_temp_flag"] = True  # soft: flagged, not failed
            legality[lbl] = row
            if not row["pass"]:
                ok = False
                if f"{lbl}: step contract" not in "; ".join(reasons):
                    reasons.append(f"{lbl}: legality gate")
        status[v] = {"ok": ok, "reason": "; ".join(reasons) or "all PASS"}
        log(f"variant {v} settles: {status[v]['reason']}")
    for lbl, row in legality.items():
        log(f"settle {lbl}: {row}")
    if not status["PROD"]["ok"]:
        return {"stage_verdict": "LEGALITY_FAILED", "legality": legality,
                "variant_status": status, "reason": "PROD anchor settles dead"}
    live = [v for v in VARIANTS if status[v]["ok"]]
    if live == ["PROD"]:
        # candidate B measured unusable at this grid: archived boundary
        return {"stage_verdict": "COMPLETED", "legality": legality,
                "variant_status": status, "rows": {},
                "faceflux_label": "FACEFLUX_MEASURED_UNSTABLE_OR_ILLEGAL",
                "thetas": [f"{t:g}" for t in thetas]}

    tang_payloads = []
    for v in live:
        proto = proto_for(mode, v)
        ny = 2 * int(proto["hs_rows"])
        nx = int(proto["nx"])
        cold_run = settles[f"{v}_th0"]
        base_payload = {
            "variant": v, "h": H_JVP, "gas_cfg": base_cfg, "ny": ny, "nx": nx,
            "cold_run": cold_run,
            "drive_periods": proto["drive_periods"],
            "samples_per_period": proto["samples_per_period"],
            "fit_skip_periods": proto["fit_skip_periods"],
            "ckpt_dir": str(ckpt),
        }
        tang_payloads.append({**base_payload, "label": f"{v}_h{H_JVP:g}_cold",
                              "hot_run": cold_run})
        for th in thetas:
            tang_payloads.append({**base_payload,
                                  "label": f"{v}_th{th:g}_h{H_JVP:g}_hot",
                                  "hot_run": settles[f"{v}_th{th:g}"]})
    tangs = execute_cases(tang_payloads, workers, log, worker=_dispatch_tangent)

    anchor_ok = True
    rows: dict[str, dict] = {}
    tangent_failed: dict[str, str] = {}
    for v in live:
        v_ok = True
        reasons: list[str] = []

        def _leg(lbl, _r=reasons):
            nonlocal v_ok
            r = tangs.get(lbl, {})
            if "Y" not in r:
                v_ok = False
                _r.append(f"{lbl}: missing/failed")
                return None
            a = r["audits"]
            if not (a["mass_tangent_rel_worst"] <= GATE_V5_MASS
                    and a["energy_account_rel_worst"] <= GATE_V5_ENERGY
                    and r["r_f_worst"] <= GATE_R_F):
                v_ok = False
                _r.append(f"{lbl}: audit gate ({a}, r_f={r['r_f_worst']:.1e})")
                return None
            return r

        rc = _leg(f"{v}_h{H_JVP:g}_cold")
        per: dict[str, Any] = {}
        if rc is not None:
            yc = complex(rc["Y"]["re"], rc["Y"]["im"])
            per["Y0_abs"] = abs(yc)
            for th in thetas:
                rh = _leg(f"{v}_th{th:g}_h{H_JVP:g}_hot")
                if rh is not None:
                    yh = complex(rh["Y"]["re"], rh["Y"]["im"])
                    per[f"{th:g}"] = _dop(yh, yc)
        if v_ok:
            rows[v] = per
            shown = {k: (round(x["d_op_pct"], 4) if isinstance(x, dict)
                         else round(x, 8)) for k, x in per.items()}
            log(f"variant {v}: {shown}")
        else:
            tangent_failed[v] = "; ".join(reasons)
            log(f"variant {v}: TANGENT_FAILED ({tangent_failed[v]})")
            if v == "PROD":
                anchor_ok = False

    return {"stage_verdict": "COMPLETED" if anchor_ok else "LEGALITY_FAILED",
            "legality": legality, "variant_status": status,
            "tangent_failed": tangent_failed, "rows": rows,
            "thetas": [f"{t:g}" for t in thetas]}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="D1 candidate-B face-flux wall measurement (D0-7)")
    ap.add_argument("--mode", choices=("smoke", "auth", "full"), default="full")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--output-root", default=None)
    args = ap.parse_args()

    workers = (args.workers if args.workers is not None
               else max(1, (os.cpu_count() or 4) - 2))
    base_cfg = load_config(REPO_ROOT / GAS_CONFIG)
    probe = copy.deepcopy(base_cfg)
    probe["numerics"] = {**probe["numerics"], "nx": 4, "ny": 8}
    g_face = faceflux_conductance_lu(GasSolver2D(probe).mapping)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = (Path(args.output_root) if args.output_root
                else REPO_ROOT / "results" / "phase5" / "faceflux_wall")
    out_dir = out_root / f"{run_id}_{args.mode}"
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg_sha8 = sha256_file(REPO_ROOT / GAS_CONFIG)[:8]
    log = lambda m: print(f"[{UNIT}] {m}", flush=True)  # noqa: E731
    log(f"run {run_id} mode={args.mode} h={H_JVP:g} workers={workers} "
        f"G_f={g_face:.8f} (frozen cold nominal, d_f={FACE_DISTANCE_LU})")
    log("judgement frozen (module docstring): step contract 1e-10 abs LU / "
        "PROD anchor 0.2pp vs TAN / cold diag |Y0 ratio-1|<=10% (budget band "
        "[-6%,-1%] archived) / face-T DC row 1e-2 soft / JAB legality / "
        "wallfix classify verbatim (RESOLVED band 1.0pp vs NSF g0, move 0.25)")

    summary: dict[str, Any] = {
        "unit": UNIT, "run_id": run_id, "mode": args.mode,
        "derivation": "Manuscript/Paper1_D1_FaceFlux_Pinning_Derivation.md "
                      "(D1_v1.1; not in repo — judgement transcribed in this "
                      "module docstring)",
        "protocol": {
            "gas_config": GAS_CONFIG, "frequency_Hz": FREQUENCY_HZ,
            "h_jvp": H_JVP, "g_face_lu": g_face,
            "face_distance_lu": FACE_DISTANCE_LU,
            "geometry": {m: {v: proto_for(m, v)["hs_rows"] for v in VARIANTS}
                         for m in ("smoke", "auth")},
            "lines": {"step_contract_abs_lu": LINE_STEP_CONTRACT_ABS_LU,
                      "prod_anchor_pp": LINE_PROD_ANCHOR_PP,
                      "cold_diag_rel": LINE_COLD_DIAG_REL,
                      "cold_budget_band_rel": list(COLD_BUDGET_BAND_REL),
                      "face_temp_dc_rel_soft": LINE_FACE_TEMP_DC_REL},
            "legality_gates": {"stationarity": GATE_STATIONARITY,
                               "dc_closure": GATE_DC_CLOSURE, "r_f": GATE_R_F,
                               "v5_mass": GATE_V5_MASS,
                               "v5_energy": GATE_V5_ENERGY},
        },
        "external_references": {
            "tan_dop_pct": {f"{k:g}": v for k, v in TAN_DOP_PCT.items()},
            "nsf_g0_dop_pct": {f"{k:g}": v for k, v in NSF_G0_DOP_PCT.items()},
            "provenance": "TAN=archive/M5_runs/wp4_tan_20260805T092726Z_B; "
                          "NSF=archive/M5_runs/nsf_arb_20260811T055850Z",
        },
        "machine": {"node": platform.node(), "platform": platform.platform(),
                    "python": sys.version.split()[0], "numpy": np.__version__,
                    "git_commit": _git_commit(), "workers": workers},
    }

    def _dump():
        (out_dir / "summary.json").write_text(
            json.dumps(summary, indent=1, default=str), encoding="utf-8")

    stages = (["smoke", "auth"] if args.mode == "full" else [args.mode])
    verdict = "COMPLETED"
    for stage in stages:
        log(f"---- stage {stage} ----")
        ckpt = out_root / f"checkpoints_{stage}_{cfg_sha8}_faceflux"
        ckpt.mkdir(parents=True, exist_ok=True)
        res = run_stage(stage, base_cfg, workers, ckpt, log)
        summary[f"stage_{stage}"] = res
        _dump()
        if res["stage_verdict"] != "COMPLETED":
            verdict = "LEGALITY_FAILED"
            log(f"stage {stage} LEGALITY_FAILED — aborting")
            break
        rows = res.get("rows", {})
        thetas = res["thetas"]

        # cold diagnostic anchor (both variants alive with cold Y)
        if "PROD" in rows and "FACEFLUX" in rows:
            ratio = rows["FACEFLUX"]["Y0_abs"] / rows["PROD"]["Y0_abs"] - 1.0
            cold_row = {"y0_ratio_minus_1": float(ratio),
                        "pass": bool(abs(ratio) <= LINE_COLD_DIAG_REL),
                        "budget_band_rel": list(COLD_BUDGET_BAND_REL),
                        "in_budget_band": bool(
                            COLD_BUDGET_BAND_REL[0] <= ratio
                            <= COLD_BUDGET_BAND_REL[1])}
            summary[f"cold_anchor_{stage}"] = cold_row
            log(f"cold diagnostic anchor[{stage}]: ratio-1={ratio:+.5f} "
                f"-> {'PASS' if cold_row['pass'] else 'FAIL'} "
                f"(budget band {COLD_BUDGET_BAND_REL}, "
                f"in_band={cold_row['in_budget_band']})")
            if stage == "auth" and not cold_row["pass"]:
                # candidate B cold-illegal at judgement caliber: its d_OP is
                # archived, not evidence (D1 pre-registered consequence)
                summary["faceflux_cold_illegal"] = True

        if stage == "auth":
            anchor = {}
            base_rows = rows.get("PROD", {})
            a_ok = True
            for t in thetas:
                if float(t) not in TAN_DOP_PCT or t not in base_rows:
                    continue
                dev = abs(base_rows[t]["d_op_pct"] - TAN_DOP_PCT[float(t)])
                anchor[t] = {"d_op_pct": base_rows[t]["d_op_pct"],
                             "tan_ref_pct": TAN_DOP_PCT[float(t)],
                             "dev_pp": dev,
                             "pass": bool(dev <= LINE_PROD_ANCHOR_PP)}
                a_ok = a_ok and anchor[t]["pass"]
                log(f"anchor PROD th={t}: dev={dev:.5f}pp "
                    f"-> {'PASS' if anchor[t]['pass'] else 'FAIL'}")
            summary["anchor_auth"] = anchor
            if not a_ok:
                verdict = "LEGALITY_FAILED"
            elif ("FACEFLUX" in rows
                  and all(t in rows["FACEFLUX"] for t in thetas)
                  and not summary.get("faceflux_cold_illegal")):
                ff = {float(t): rows["FACEFLUX"][t] for t in thetas}
                pr = {float(t): rows["PROD"][t] for t in thetas}
                cls = classify(ff, pr, [float(t) for t in thetas])
                summary["classification_auth"] = cls
                log(f"classification[auth]: {cls}")
        elif stage == "smoke":
            b = rows.get("PROD", {}).get("0.05")
            if b:
                summary["smoke_soft_anchor"] = {
                    "d_op_pct": b["d_op_pct"],
                    "jab1_smoke_ref_pct": JAB1_SMOKE_DOP_PCT,
                    "dev_pp": abs(b["d_op_pct"] - JAB1_SMOKE_DOP_PCT),
                    "soft_anchor": True}
                log(f"smoke soft anchor: {summary['smoke_soft_anchor']}")
            s = rows.get("FACEFLUX", {}).get("0.05")
            if s and b:
                log(f"smoke screening: FACEFLUX d_OP={s['d_op_pct']:+.4f} "
                    f"vs PROD {b['d_op_pct']:+.4f} (steep rig, NOT a verdict)")
        _dump()

    summary["verdict"] = verdict
    _dump()
    log(f"verdict={verdict}  outputs -> {out_dir}")
    return 0 if verdict == "COMPLETED" else 1


if __name__ == "__main__":
    sys.exit(main())
