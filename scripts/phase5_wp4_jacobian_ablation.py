"""Phase_5 WP4 hot-basestate Jacobian ablation runner (WP4-JAB).

USER-AUTHORIZED EXECUTION 2026-08-08 of the pre-registered guide
docs/Phase_5/wp4_hot_basestate_jacobian_ablation_guide.md (GUIDE_v1.0).

DESIGN (frozen with configs/phase5/a2a_operating_point/
jacobian_ablation_10k_dx2p6.yaml BEFORE any hot-state number exists):

  Build the matrix-free tangent of the FULL production one-step operator
  F = H o A o B o S o C on the settled DC hot base states (canonical tent,
  certified instrument verbatim; Theta_DC in {0, 0.05, 0.10}), verify it
  V0-V5 (including the 0.2 pp TAN identity gate), then re-run the SAME
  chained tangent with exactly ONE derivative block evaluated at the COLD
  base intermediates (A1 acoustic reference / A2 band reconstruction /
  A3 macro+equilibrium / A4 stress closure / A5 heat-flux+energy) plus the
  A6 negative control (streaming+filter FD swap; exactly-linear stages, so
  numerically zero by construction) and one pairwise combo of the two
  largest |S_i| (rule frozen in the config).

  Per variant X and working point:  d_OP^X = (|Y0^X(Th)/Y0^X(0)| - 1)*100,
  S_i = d_OP^(-i) - d_OP^full  [pp],  R_dyn^X = d_OP^X - d_OP^QS1(archived),
  C_i = 1 - |R_dyn^(-i)|/|R_dyn^full|.  Y0 per (variant, point) is the
  (1, h^2) LSQ extrapolation of Y over the frozen three-rung JVP ladder
  (the same complex-LSQ instrument as WP4-TAN's eps extrapolation); the raw
  three-rung table is archived per variant (guide section 12).

  Cold anchor sharing (config variants.cold_anchor_shared): at Theta=0 the
  hot and cold snapshots are the same object, so EVERY ablation is
  definitionally identical to A0 -- the cold tangent is computed once per h
  with the A0 machinery and shared; recorded as shared_by_construction.

  A1 structural shortcut (config variants.A1): the acoustic phase family is
  asserted structurally identity on THIS rig geometry at runtime
  (assert_acoustic_stage_identity: 0 qualifying diagonal low modes at nx=8,
  high-mode factors 1.0, spectral trace projector off, no pressure-memory).
  Under that assert A1 == A0 bitwise by construction; S_A1 = 0 is recorded
  as by_construction and doubles as a second negative control. If the
  assert ever fails the runner refuses to run (fail-loud) -- no silent
  extrapolation of the G2-O S6 identity.

  Judgement labels (frozen, config interpretation block): per-module
  C_i >= 0.5 at BOTH points moving toward QS-1 -> primary candidate;
  singles < 0.5 but the pre-registered pair combo crossing 0.5 at both ->
  coupled candidate; single-point-only or wrong direction -> local
  sensitivity; nothing -> JAB_MECHANISM_NOT_CLOSED. Diagnostic unit:
  COMPLETED/LEGALITY_FAILED verdicts + labelled rows only (D0-7), no gate
  claim, no change to WP4_SUBMATRIX_COMPLETE / FINAL_PRODUCTION_NOT_CLAIMED.

  Hard stops (config interpretation.hard_stops, guide section 9.2) are
  enforced: V0-V5 failure blocks ablation interpretation (results archived,
  labels replaced by JAB_TANGENT_NOT_VERIFIED); negative-control excursion
  above the frozen line marks JAB_NEGATIVE_CONTROL_FAILED and blocks
  interpretation.

  The h ladder may only be frozen from the COLD smoke (config jvp block);
  this runner REFUSES any hot-state tangent while jvp.h_frozen is false.

Pool discipline: G4a-certified execute_cases worker/scheduler verbatim;
BLAS capped in children; module-level picklable workers; machine
fingerprint in provenance (D5-3). Pre-registration digests (sha256 of the
frozen config + core/tangent_step.py + this runner) are recorded in
provenance.json BEFORE case execution starts.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.solver import GasSolver2D  # noqa: E402
from core.tangent_step import (  # noqa: E402
    BaseState,
    TangentOperator,
    ablated_blocks,
    assert_acoustic_stage_identity,
    compute_stage_bases,
    propagate_tangent,
    v1_odd_even_probe,
)
from scripts.phase2_m2_verification import load_config  # noqa: E402
from scripts.phase5_g1w_wall_neutrality import _git_commit  # noqa: E402
from scripts.phase5_g4a_dc_basestate import (  # noqa: E402
    _cplx,
    _g4a_case_worker,
    fit_admittance,
)
from scripts.phase5_wp4_tangent_response import tangent_fit  # noqa: E402

CASE_FAMILY = "wp4_jacobian_ablation"
SINGLE_VARIANTS = ["A0", "A2", "A3", "A4", "A5", "A6"]   # A1 = structural row
COMBO_POOL = ["A2", "A3", "A4", "A5"]                     # controls excluded


# ---------------------------------------------------------------------------
# guards (contract-test targets; guide section 11 item 9)
# ---------------------------------------------------------------------------

def require_h_frozen(cfg_all: dict[str, Any]) -> list[float]:
    jvp = cfg_all.get("jvp", {})
    if not bool(jvp.get("h_frozen", False)):
        raise RuntimeError(
            "jvp.h_frozen is false: the JVP step window has not been frozen "
            "from the cold smoke -- hot-state tangent runs are forbidden "
            "(config jvp block; guide section 4.3)")
    ladder = [float(h) for h in jvp["h_ladder"]]
    if len(ladder) != 3:
        raise RuntimeError(f"frozen h ladder must have 3 rungs, got {ladder}")
    return ladder


def snapshot_to_base(run: dict[str, Any]) -> BaseState:
    if "snapshot" not in run:
        raise RuntimeError(
            "base run carries no snapshot -- run_tent must be invoked with "
            "snapshot=True for tangent work (guide section 4.1)")
    s = run["snapshot"]
    meta = {k: run.get(k) for k in (
        "stationarity_per_period", "theta_dc_measured", "dc_closure_rel",
        "column_duplicate_rel", "mass_drift_settle", "steps_per_period")}
    return BaseState(f=np.asarray(s["f"]), g=np.asarray(s["g"]),
                     theta_w=float(s["theta_hot_mean"]),
                     theta_amb=float(s["theta_amb"]), hs=int(s["hs"]),
                     theta_dc_target=float(s["theta_dc_target"]), meta=meta)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# per-case checkpoints (orchestration layer ONLY -- the per-case physics path
# is untouched; added 2026-08-09 after a mid-run power loss discarded a
# finished 14-case batch held in parent memory). Each completed case is
# atomically persisted with a scalar identity + the config digest; a relaunch
# skips cases whose checkpoint identity matches bitwise-reproducible inputs
# (same machine, D5-3). Interruptions now cost at most the in-flight batch.
# ---------------------------------------------------------------------------

def _checkpoint_wrap(worker, payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    path = payload.get("checkpoint_path")
    identity = payload.get("checkpoint_identity")
    if path:
        try:
            with open(path, "rb") as fh:
                blob = pickle.load(fh)
            if blob.get("identity") == identity and blob["result"].get("ok"):
                blob["result"].setdefault("log", []).append("checkpoint: reused")
                return payload["label"], blob["result"]
        except FileNotFoundError:
            pass
        except Exception:
            pass  # unreadable/mismatched checkpoint -> recompute
    label, result = worker(payload)
    if path and result.get("ok"):
        try:
            tmp = Path(str(path) + ".tmp")
            with open(tmp, "wb") as fh:
                pickle.dump({"identity": identity, "result": result}, fh)
            os.replace(tmp, path)
        except Exception as exc:
            result.setdefault("log", []).append(f"checkpoint save failed: {exc}")
    return label, result


def _jab_base_worker(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    return _checkpoint_wrap(_g4a_case_worker, payload)


def _jab_tangent_worker_ckpt(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    return _checkpoint_wrap(_jab_tangent_worker, payload)


def _snapshot_digest(run: dict[str, Any]) -> str:
    s = run["snapshot"]
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(s["f"]).tobytes())
    h.update(np.ascontiguousarray(s["g"]).tobytes())
    return h.hexdigest()[:16]


# ---------------------------------------------------------------------------
# tangent case worker (module-level, picklable)
# ---------------------------------------------------------------------------

def _jab_tangent_worker(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    label = payload["label"]
    lines: list[str] = []
    try:
        cfg = copy.deepcopy(payload["gas_cfg"])
        cfg["numerics"] = {**cfg["numerics"], "nx": int(payload["nx"]),
                           "ny": int(payload["ny"])}
        solver = GasSolver2D(cfg)
        hot_base = snapshot_to_base(payload["hot_run"])
        cold_base = snapshot_to_base(payload["cold_run"])
        hot = compute_stage_bases(solver, hot_base)
        cold = compute_stage_bases(solver, cold_base)
        op = TangentOperator(solver, hot_base, hot, cold_base, cold,
                             h=float(payload["h"]),
                             ablated=ablated_blocks(payload["variant"]))
        run = propagate_tangent(
            op, frequency_hz=float(payload["frequency_hz"]),
            drive_periods=float(payload["drive_periods"]),
            samples_per_period=int(payload["samples_per_period"]),
            log=None)
        run["label"] = label
        run["variant"] = payload["variant"]
        run["theta_dc"] = hot_base.theta_dc_target
        run["h"] = float(payload["h"])
        run["r_f_hot"] = hot.r_f
        run["r_f_cold"] = cold.r_f
        run["acoustic_report"] = op.acoustic_report
        run["reference_triple_used"] = list(
            (cold if "acoustic_ref" in op.ablated else hot).reference_triple)
        return label, {"ok": True, "run": run, "log": lines}
    except Exception as exc:  # measured death, not a pool crash (S4 discipline)
        return label, {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                       "log": lines}


# ---------------------------------------------------------------------------
# assembly + analysis
# ---------------------------------------------------------------------------

def _tangent_payloads(variants: list[str], thetas: list[float],
                      h_ladder: list[float], base_runs: dict[float, dict],
                      common: dict[str, Any],
                      ckpt: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """One payload per (variant, hot theta, h) + the shared cold anchor per h."""

    def entry(label, variant, h, th_hot):
        p = {**common, "label": label, "variant": variant, "h": h,
             "hot_run": base_runs[th_hot], "cold_run": base_runs[0.0]}
        if ckpt is not None:
            p["checkpoint_path"] = str(ckpt["dir"] / f"{label}.pkl")
            p["checkpoint_identity"] = {
                "kind": "tan", "variant": variant, "theta": th_hot, "h": h,
                "cfg": ckpt["cfg"], "hot": ckpt["snap"][th_hot],
                "cold": ckpt["snap"][0.0],
                **{k: common[k] for k in ("ny", "nx", "frequency_hz",
                                          "samples_per_period", "drive_periods")}}
        return p

    payloads = []
    for h in h_ladder:
        payloads.append(entry(f"tan_A0_th0_h{h:g}", "A0", h, 0.0))
    for variant in variants:
        for th in thetas:
            for h in h_ladder:
                payloads.append(entry(
                    f"tan_{variant.replace('+', '_')}_th{th:g}_h{h:g}",
                    variant, h, th))
    return payloads


def _extrapolate_y(y_by_h: dict[float, complex], h_ladder: list[float]) -> dict[str, Any]:
    hs = np.array(h_ladder)
    ys = np.array([y_by_h[h] for h in h_ladder])
    y0, curv, resid = tangent_fit(hs, ys)
    spread = 0.0
    for i in range(len(h_ladder)):
        for j in range(i + 1, len(h_ladder)):
            spread = max(spread, abs(ys[i] / ys[j] - 1.0))
    return {"Y0": y0, "h_fit_residual": resid, "h_spread_rel": float(spread),
            "Y_at_h": {f"{h:g}": _cplx(y_by_h[h]) for h in h_ladder},
            "Y0_cplx": _cplx(y0)}


def analyse_wave(results: dict[str, Any], variants: list[str],
                 thetas: list[float], h_ladder: list[float], f_hz: float,
                 skip: float, log) -> dict[str, Any]:
    """Fits + extrapolation + audit collection for one tangent wave."""

    def run_of(label):
        res = results.get(label)
        return res["run"] if res and res.get("ok") and res["run"].get("finite") else None

    table: dict[str, Any] = {}
    audits_worst = {"mass_tangent_rel_worst": 0.0, "energy_account_rel_worst": 0.0}
    dead: list[str] = []
    cold_y: dict[float, complex] = {}
    for h in h_ladder:
        r = run_of(f"tan_A0_th0_h{h:g}")
        if r is None:
            dead.append(f"tan_A0_th0_h{h:g}")
            continue
        cold_y[h] = fit_admittance(r, f_hz, skip)["Y_face_theta_units"]
        for k in audits_worst:
            audits_worst[k] = max(audits_worst[k], r["audits"][k])
    if len(cold_y) == len(h_ladder):
        table["cold_anchor"] = {**_extrapolate_y(cold_y, h_ladder),
                                "shared_by_construction": True}
    for variant in variants:
        for th in thetas:
            y_by_h: dict[float, complex] = {}
            for h in h_ladder:
                lb = f"tan_{variant.replace('+', '_')}_th{th:g}_h{h:g}"
                r = run_of(lb)
                if r is None:
                    dead.append(lb)
                    continue
                y_by_h[h] = fit_admittance(r, f_hz, skip)["Y_face_theta_units"]
                for k in audits_worst:
                    audits_worst[k] = max(audits_worst[k], r["audits"][k])
            if len(y_by_h) == len(h_ladder):
                table[f"{variant}|{th:g}"] = _extrapolate_y(y_by_h, h_ladder)
    return {"table": table, "audits_worst": audits_worst, "dead": dead}


def build_result_rows(table: dict[str, Any], variants: list[str],
                      thetas: list[float], refs: dict[str, Any]) -> dict[str, Any]:
    """d_OP / S_i / C_i per variant and working point (frozen formulas)."""

    y_cold = table["cold_anchor"]["Y0"]
    rows: dict[str, Any] = {}
    d_full: dict[float, float] = {}
    for th in thetas:
        d = table[f"A0|{th:g}"]["Y0"] / y_cold
        d_full[th] = (abs(d) - 1.0) * 100.0
    qs1 = {float(k): float(v) for k, v in refs["qs1_dop_pct"].items()}
    for variant in variants:
        vr: dict[str, Any] = {}
        for th in thetas:
            key = f"{variant}|{th:g}"
            if key not in table:
                vr[f"{th:g}"] = {"status": "dead"}
                continue
            d = table[key]["Y0"] / y_cold
            d_pct = (abs(d) - 1.0) * 100.0
            r_dyn = d_pct - qs1[th]
            r_full = d_full[th] - qs1[th]
            vr[f"{th:g}"] = {
                "status": "ok",
                "D_OP": _cplx(d), "d_OP_pct": d_pct,
                "delta_phi_deg": float(math.degrees(math.atan2(d.imag, d.real))),
                "S_pp": d_pct - d_full[th],
                "R_dyn_pp": r_dyn,
                "C_close": 1.0 - abs(r_dyn) / abs(r_full),
                "toward_qs1": bool((d_pct - d_full[th]) * (qs1[th] - d_full[th]) > 0),
                "h_spread_rel": table[key]["h_spread_rel"],
                "h_fit_residual": table[key]["h_fit_residual"],
            }
        rows[variant] = vr
    return {"rows": rows, "d_full_pct": {f"{t:g}": d_full[t] for t in thetas}}


def interpret(rows: dict[str, Any], combo_rows: dict[str, Any] | None,
              thetas: list[float], interp_cfg: dict[str, Any],
              neg_line_pp: float) -> dict[str, Any]:
    """Frozen judgement rules (config interpretation block; guide section 8)."""

    line = float(interp_cfg["close_line_frac"])
    per_module: dict[str, Any] = {}
    candidates: list[str] = []
    local_sens: list[str] = []
    for variant, vr in rows.items():
        if variant == "A0" or "+" in variant:   # combos judged via combo_rows
            continue
        oks = [vr.get(f"{t:g}", {}) for t in thetas]
        if any(r.get("status") != "ok" for r in oks):
            per_module[variant] = "dead"
            continue
        closes = [r["C_close"] >= line for r in oks]
        toward = [r["toward_qs1"] for r in oks]
        if variant in ("A6", "A1"):
            worst = max(abs(r["S_pp"]) for r in oks)
            per_module[variant] = {"control_abs_S_pp_worst": worst,
                                   "clean": bool(worst <= neg_line_pp)}
            continue
        if all(closes) and all(toward):
            per_module[variant] = "primary_candidate"
            candidates.append(variant)
        elif any(closes) or (any(toward) and not all(toward)):
            per_module[variant] = "local_sensitivity"
            local_sens.append(variant)
        else:
            per_module[variant] = "no_significant_effect"
    combo_label = None
    if combo_rows:
        for cname, vr in combo_rows.items():
            oks = [vr.get(f"{t:g}", {}) for t in thetas]
            if any(r.get("status") != "ok" for r in oks):
                continue
            if all(r["C_close"] >= line for r in oks) and not candidates:
                combo_label = f"coupled_candidate:{cname}"
    labels = []
    if candidates:
        labels.append("JAB_PRIMARY_CANDIDATE_" + "_".join(sorted(candidates)))
    elif combo_label:
        labels.append("JAB_COUPLED_CANDIDATE_" + combo_label.split(":", 1)[1].replace("+", "_"))
    else:
        labels.append("JAB_MECHANISM_NOT_CLOSED")
    if local_sens:
        labels.append("JAB_LOCAL_SENSITIVITY_" + "_".join(sorted(local_sens)))
    return {"per_module": per_module, "labels": labels}


# ---------------------------------------------------------------------------
# main runner
# ---------------------------------------------------------------------------

def run_jab(config_path: str | Path, output_root: str | Path | None = None,
            *, smoke: bool = False, workers: int | None = None,
            select_h: bool = False) -> dict[str, Any]:
    import h5py
    import yaml

    from scripts.phase5_g1a_amplitude_envelope import execute_cases

    t0 = datetime.now(timezone.utc)
    cfg_path = Path(config_path)
    cfg_all = load_config(cfg_path)
    proto = cfg_all["jab_smoke" if smoke else "jab"]
    gates = cfg_all["gates"]
    refs = cfg_all["references"]
    jvp_cfg = cfg_all["jvp"]
    gas_cfg = load_config(REPO_ROOT / str(cfg_all["inheritance"]["gas_config"]))

    log_lines: list[str] = []

    def log(msg: str) -> None:
        line = f"JAB {msg}"
        print(line, flush=True)
        log_lines.append(line)

    unit = str(proto.get("unit_label", "WP4-JAB"))
    f_hz = float(proto["frequency_Hz"])
    hs_rows = int(proto["hs_rows"])
    ny = 2 * hs_rows
    nx = int(proto["nx"])
    thetas = [float(t) for t in proto["theta_points"]]
    spp = int(proto["samples_per_period"])
    settle = float(proto["settle_periods"])
    drive_p = float(proto["drive_periods"])
    skip = float(proto["fit_skip_periods"])
    n_workers = workers if workers is not None else max(1, (os.cpu_count() or 4) - 2)

    prereg = {
        "config_sha256": _sha256(cfg_path),
        "tangent_step_sha256": _sha256(REPO_ROOT / "core" / "tangent_step.py"),
        "runner_sha256": _sha256(Path(__file__)),
        "frozen_before_execution_utc": t0.isoformat(),
    }
    log(f"pre-registration digests: {prereg['config_sha256']} / "
        f"{prereg['tangent_step_sha256']} / {prereg['runner_sha256']}")

    # structural assert on the actual geometry BEFORE anything runs (A1 legality)
    probe_cfg = copy.deepcopy(gas_cfg)
    probe_cfg["numerics"] = {**probe_cfg["numerics"], "nx": nx, "ny": ny}
    probe_solver = GasSolver2D(probe_cfg)
    acoustic_report = assert_acoustic_stage_identity(probe_solver)
    log(f"acoustic stage structural identity asserted: {acoustic_report}")

    # ---- base wave: settled snapshots for [0] + thetas (select-h: cold only) ----
    out_root = Path(output_root) if output_root else \
        REPO_ROOT / "results" / "phase5" / CASE_FAMILY
    ckpt_dir = out_root / "checkpoints" / \
        f"{'smoke' if smoke else 'auth'}_{prereg['config_sha256'][:8]}"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    log(f"checkpoint dir: {ckpt_dir}")
    base_thetas = [0.0] if select_h else [0.0] + thetas
    common_base = dict(gas_cfg=gas_cfg, ny=ny, nx=nx, frequency_hz=f_hz,
                      samples_per_period=spp, settle_periods=settle,
                      drive_periods=0.0, eps_ac=0.0, snapshot=True)
    base_payloads = []
    for th in base_thetas:
        base_payloads.append({
            **common_base, "label": f"base_th{th:g}", "kind": "base",
            "theta_dc": th,
            "checkpoint_path": str(ckpt_dir / f"base_th{th:g}.pkl"),
            "checkpoint_identity": {
                "kind": "base", "theta_dc": th, "ny": ny, "nx": nx,
                "spp": spp, "settle": settle, "f_hz": f_hz,
                "cfg": prereg["config_sha256"]}})
    base_results = execute_cases(base_payloads, n_workers, log, worker=_jab_base_worker)
    base_runs: dict[float, dict] = {}
    for th in base_thetas:
        res = base_results.get(f"base_th{th:g}")
        if not (res and res.get("ok") and res["run"].get("finite")):
            log(f"[base_th{th:g}] DEAD: {None if not res else res.get('error')}")
            continue
        base_runs[th] = res["run"]
        log(f"[base_th{th:g}] stat={res['run']['stationarity_per_period']:.2e} "
            f"closure={res['run']['dc_closure_rel']:.2e} "
            f"ThetaDC={res['run']['theta_dc_measured']:.4f}")

    # ---- V0 base legality ----
    v0 = {"all_bases_finite": len(base_runs) == len(base_thetas)}
    if v0["all_bases_finite"]:
        v0["stationarity_worst"] = max(base_runs[th]["stationarity_per_period"]
                                       for th in base_thetas)
        v0["state_match_worst"] = max(
            (abs(base_runs[th]["theta_dc_measured"] / th - 1.0)
             for th in base_thetas if th > 0.0), default=0.0)
        # dc closure is a HOT-base gate: at Theta_DC=0 both bands exchange
        # ~zero net heat and the closure ratio is a 0/0 artifact (recorded,
        # not gated -- same scoping as the TAN legality rows).
        v0["dc_closure_worst"] = max(
            (base_runs[th]["dc_closure_rel"] for th in base_thetas if th > 0.0),
            default=0.0)
        v0["dc_closure_cold_recorded"] = base_runs[0.0]["dc_closure_rel"]
        v0["passed"] = bool(
            v0["stationarity_worst"] <= float(gates["stationarity_per_period"])
            and v0["state_match_worst"] <= float(gates["state_match_rel"])
            and v0["dc_closure_worst"] <= float(gates["dc_closure_rel"]))
    else:
        v0["passed"] = False
    log(f"V0 base legality: {v0}")

    # ---- V1 probes (+ h-window selection mode) ----
    v1_rows: dict[str, Any] = {}
    r_f_by: dict[str, float] = {}
    if v0["all_bases_finite"]:
        h_probe = ([float(h) for h in jvp_cfg["h_scan"]] if select_h
                   else [float(h) for h in jvp_cfg["h_ladder"]])
        for th in ([0.0] if select_h else base_thetas):
            base = snapshot_to_base(base_runs[th])
            bases = compute_stage_bases(probe_solver, base)
            r_f_by[f"{th:g}"] = bases.r_f
            v1_rows[f"{th:g}"] = v1_odd_even_probe(
                probe_solver, base, bases, h_probe)
            log(f"V1 th={th:g}: r_F={bases.r_f:.3e} "
                f"odd_pairwise={['%.2e' % x for x in v1_rows[f'{th:g}']['odd_pairwise_rel']]} "
                f"even_ratios={['%.2f' % x for x in v1_rows[f'{th:g}']['even_ratios']]}")
    if select_h:
        # selection mode: report the scan and exit (no tangent propagation)
        out = {"mode": "select_h", "v1_scan": v1_rows, "r_f": r_f_by,
               "selection_rule": jvp_cfg["selection_rule"]}
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_root = Path(output_root) if output_root else \
            REPO_ROOT / "results" / "phase5" / CASE_FAMILY
        out_dir = out_root / f"{run_id}_select_h"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "h_selection.json").write_text(
            json.dumps(out, indent=1, default=float), encoding="utf-8")
        log(f"h-selection scan -> {out_dir}")
        return {"verdict": "H_SELECTION_SCAN", "out_dir": str(out_dir),
                "summary": out}

    h_ladder = require_h_frozen(cfg_all)   # refuses hot runs pre-freeze
    v1_pass = bool(v1_rows) and all(
        max(row["odd_pairwise_rel"]) <= float(gates["v1_odd_pairwise_rel"])
        for row in v1_rows.values())

    # r_F gate (frozen post-smoke; null = record-only until frozen)
    r_f_gate = cfg_all.get("snapshot", {}).get("r_f_max")
    r_f_pass = True if r_f_gate is None else all(
        v <= float(r_f_gate) for v in r_f_by.values())

    # ---- tangent wave 1 ----
    common_tan = dict(gas_cfg=gas_cfg, ny=ny, nx=nx, frequency_hz=f_hz,
                      samples_per_period=spp, drive_periods=drive_p)
    ckpt = None
    if v0["passed"]:
        ckpt = {"dir": ckpt_dir, "cfg": prereg["config_sha256"],
                "snap": {th: _snapshot_digest(base_runs[th]) for th in base_thetas}}
    variants1 = SINGLE_VARIANTS[1:] if not smoke else ["A2"]
    wave1_variants = ["A0"] + variants1
    payloads1 = _tangent_payloads(wave1_variants, thetas, h_ladder,
                                  base_runs, common_tan, ckpt) if v0["passed"] else []
    results1 = execute_cases(payloads1, n_workers, log,
                             worker=_jab_tangent_worker_ckpt) if payloads1 else {}
    wave1 = analyse_wave(results1, wave1_variants, thetas, h_ladder,
                         f_hz, skip, log)
    for key, row in sorted(wave1["table"].items()):
        log(f"[{key}] |Y0|={abs(row['Y0']):.6e} h_spread={row['h_spread_rel']:.2e}")

    # ---- verification rows V2-V5 ----
    table = wave1["table"]
    have_core = ("cold_anchor" in table
                 and all(f"A0|{t:g}" in table for t in thetas))
    v2_gate = gates.get("v2_y_h_spread_rel")
    v2_gate = float(v2_gate) if v2_gate is not None else float(gates["v2_y_h_spread_cap"])
    v2 = {"gate": v2_gate,
          "worst": max((row["h_spread_rel"] for row in table.values()), default=float("nan"))}
    v2["passed"] = bool(table) and v2["worst"] <= v2["gate"]
    v3 = {"passed": False}
    if smoke:
        v3 = {"passed": None,
              "not_applicable": "smoke grid differs from the archived "
                                "authoritative-grid TAN references"}
    elif have_core:
        y_cold_ref = complex(float(refs["y0_tangent_cold"]["re"]),
                             float(refs["y0_tangent_cold"]["im"]))
        ratio = table["cold_anchor"]["Y0"] / y_cold_ref
        v3 = {"ratio": _cplx(ratio),
              "amp_rel_err": abs(abs(ratio) - 1.0),
              "phase_deg_err": abs(math.degrees(math.atan2(ratio.imag, ratio.real))),
              "gate_amp": float(gates["v3_cold_amp_rel"]),
              "gate_phase_deg": float(gates["v3_cold_phase_deg"])}
        v3["passed"] = bool(v3["amp_rel_err"] <= v3["gate_amp"]
                            and v3["phase_deg_err"] <= v3["gate_phase_deg"])
    result_rows: dict[str, Any] = {}
    v4 = {"passed": False}
    if smoke and have_core:
        result_rows = build_result_rows(table, wave1_variants, thetas, refs)
        v4 = {"passed": None,
              "not_applicable": "smoke grid; the smoke identity row is the "
                                "FD direction check"}
    elif have_core:
        result_rows = build_result_rows(table, wave1_variants, thetas, refs)
        # YAML reference keys are quoted decimals ("0.10"); normalize to float
        # keys the same way build_result_rows treats qs1_dop_pct
        dop_ref = {float(k): float(v) for k, v in refs["dop_tan_pct"].items()}
        v4_rows = {}
        for th in thetas:
            ref_pct = dop_ref[th]
            dev = result_rows["d_full_pct"][f"{th:g}"] - ref_pct
            v4_rows[f"{th:g}"] = {"d_OP_tan_pct": result_rows["d_full_pct"][f"{th:g}"],
                                  "archived_tan_pct": ref_pct, "deviation_pp": dev,
                                  "within": abs(dev) <= float(gates["v4_tan_identity_pp"])}
        v4 = {"rows": v4_rows,
              "passed": all(r["within"] for r in v4_rows.values())}
        for th, r in v4_rows.items():
            log(f"V4 th={th}: d_OP_tan={r['d_OP_tan_pct']:+.3f}% vs TAN "
                f"{r['archived_tan_pct']:+.3f}% (dev {r['deviation_pp']:+.3f}pp)")
    v5 = {"mass_worst": wave1["audits_worst"]["mass_tangent_rel_worst"],
          "energy_account_worst": wave1["audits_worst"]["energy_account_rel_worst"],
          "gate_mass": float(gates["v5_mass_tangent_rel"]),
          "gate_energy": float(gates["v5_energy_account_rel"])}
    v5["passed"] = bool(table) and (v5["mass_worst"] <= v5["gate_mass"]
                                    and v5["energy_account_worst"] <= v5["gate_energy"])
    verification = {"V0": v0, "V1": {"rows": v1_rows, "passed": v1_pass},
                    "V2": v2, "V3": v3, "V4": v4, "V5": v5,
                    "r_F": {"values": r_f_by, "gate": r_f_gate, "passed": r_f_pass}}
    applicable = [k for k in ("V0", "V1", "V2", "V3", "V4", "V5")
                  if verification[k].get("passed") is not None]
    tangent_verified = all(verification[k].get("passed") for k in applicable) \
        and r_f_pass
    log(f"tangent verification: {'PASS V0-V5' if tangent_verified else 'NOT VERIFIED'}")

    # A1 structural rows (legal only under the runtime assert, done above)
    if result_rows and "A0" in result_rows["rows"]:
        a1_rows = {}
        for th in thetas:
            base_row = dict(result_rows["rows"]["A0"][f"{th:g}"])
            base_row.update({"S_pp": 0.0,
                             "C_close": result_rows["rows"]["A0"][f"{th:g}"].get("C_close"),
                             "by_construction": "structural_identity",
                             })
            a1_rows[f"{th:g}"] = base_row
        result_rows["rows"]["A1"] = a1_rows

    # ---- combo wave (frozen rule; only when verified and not smoke) ----
    combo_rows = None
    combo_pick = None
    if tangent_verified and not smoke and result_rows:
        scores = {}
        for v in COMBO_POOL:
            vr = result_rows["rows"].get(v, {})
            vals = [abs(vr.get(f"{t:g}", {}).get("S_pp", float("nan"))) for t in thetas]
            if all(math.isfinite(x) for x in vals):
                scores[v] = float(np.mean(vals))
        if len(scores) >= 2:
            top2 = sorted(scores, key=scores.get, reverse=True)[:2]
            combo_pick = "+".join(sorted(top2))
            log(f"combo pick (frozen rule, mean|S| ranking {scores}): {combo_pick}")
            payloads2 = _tangent_payloads([combo_pick], thetas, h_ladder,
                                          base_runs, common_tan, ckpt)
            payloads2 = [p for p in payloads2 if not p["label"].startswith("tan_A0_th0")]
            results2 = execute_cases(payloads2, n_workers, log,
                                     worker=_jab_tangent_worker_ckpt)
            wave2 = analyse_wave({**results1, **results2}, [combo_pick],
                                 thetas, h_ladder, f_hz, skip, log)
            table.update(wave2["table"])
            wave1["dead"].extend(wave2["dead"])
            v5["mass_worst"] = max(v5["mass_worst"],
                                   wave2["audits_worst"]["mass_tangent_rel_worst"])
            v5["energy_account_worst"] = max(
                v5["energy_account_worst"],
                wave2["audits_worst"]["energy_account_rel_worst"])
            v5["passed"] = bool(v5["mass_worst"] <= v5["gate_mass"]
                                and v5["energy_account_worst"] <= v5["gate_energy"])
            v2["worst"] = max(row["h_spread_rel"] for row in table.values())
            v2["passed"] = v2["worst"] <= v2["gate"]
            combo_full = build_result_rows(table, wave1_variants + [combo_pick],
                                           thetas, refs)
            result_rows = combo_full
            a1_rows = {}
            for th in thetas:
                base_row = dict(result_rows["rows"]["A0"][f"{th:g}"])
                base_row.update({"S_pp": 0.0, "by_construction": "structural_identity"})
                a1_rows[f"{th:g}"] = base_row
            result_rows["rows"]["A1"] = a1_rows
            combo_rows = {combo_pick: result_rows["rows"][combo_pick]}
            # synergy / overlap record (frozen formula)
            a, b = combo_pick.split("+")
            syn = {}
            for th in thetas:
                sa = result_rows["rows"][a][f"{th:g}"]["S_pp"]
                sb = result_rows["rows"][b][f"{th:g}"]["S_pp"]
                sc = result_rows["rows"][combo_pick][f"{th:g}"]["S_pp"]
                if abs(sc) > 1.25 * abs(sa + sb) and abs(sc - (sa + sb)) > 0.25:
                    tag = "synergy"
                elif abs(sc) < 0.75 * abs(sa + sb) and abs(sc - (sa + sb)) > 0.25:
                    tag = "overlap"
                else:
                    tag = "near_additive"
                syn[f"{th:g}"] = {"S_a": sa, "S_b": sb, "S_combo": sc, "tag": tag}
            combo_rows["synergy"] = syn

    # ---- smoke-only: finite-difference TAN direction check (guide section 11
    # item 8) -- production eps-ladder increments on the SAME smoke rig, the
    # same (1, eps^2) extrapolation, compared against the tangent d_OP ----
    smoke_direction = None
    if smoke and result_rows and v0["passed"]:
        fd_eps = [float(e) for e in proto["fd_eps_ladder"]]
        fd_payloads = []
        for th in [0.0] + thetas:
            for e in fd_eps:
                fd_payloads.append({**common_base, "snapshot": False,
                                    "label": f"fd_th{th:g}_eps{e:g}",
                                    "kind": "increment", "theta_dc": th,
                                    "eps_ac": e, "drive_periods": drive_p})
        fd_results = execute_cases(fd_payloads, n_workers, log,
                                   worker=_g4a_case_worker)

        def fd_run(label):
            res = fd_results.get(label)
            return res["run"] if res and res.get("ok") and res["run"].get("finite") else None

        fd_y0: dict[float, complex] = {}
        for th in [0.0] + thetas:
            ys = []
            for e in fd_eps:
                r = fd_run(f"fd_th{th:g}_eps{e:g}")
                if r is not None:
                    ys.append(fit_admittance(r, f_hz, skip)["Y_face_theta_units"])
            if len(ys) == len(fd_eps):
                fd_y0[th], _, _ = tangent_fit(np.array(fd_eps), np.array(ys))
        smoke_direction = {"rows": {}, "passed": bool(fd_y0)}
        for th in thetas:
            if 0.0 not in fd_y0 or th not in fd_y0:
                smoke_direction["rows"][f"{th:g}"] = {"status": "dead"}
                smoke_direction["passed"] = False
                continue
            d_fd = (abs(fd_y0[th] / fd_y0[0.0]) - 1.0) * 100.0
            d_tan = result_rows["d_full_pct"][f"{th:g}"]
            same_sign = bool(d_fd * d_tan > 0)
            smoke_direction["rows"][f"{th:g}"] = {
                "d_OP_fd_pct": d_fd, "d_OP_tangent_pct": d_tan,
                "deviation_pp": d_tan - d_fd, "same_sign": same_sign}
            smoke_direction["passed"] = smoke_direction["passed"] and same_sign
            log(f"smoke FD direction th={th:g}: fd={d_fd:+.3f}% tan={d_tan:+.3f}% "
                f"same_sign={same_sign}")

    # ---- interpretation (frozen rules) ----
    neg_line = float(gates["negative_control_max_abs_S_pp"])
    interp = None
    if result_rows:
        controls_clean = True
        for cv in ("A1", "A6"):
            vr = result_rows["rows"].get(cv, {})
            for th in thetas:
                s = vr.get(f"{th:g}", {}).get("S_pp")
                if s is not None and abs(s) > neg_line:
                    controls_clean = False
        if tangent_verified and controls_clean:
            interp = interpret(result_rows["rows"], combo_rows, thetas,
                               cfg_all["interpretation"], neg_line)
        elif not controls_clean:
            interp = {"labels": ["JAB_NEGATIVE_CONTROL_FAILED"],
                      "per_module": "interpretation blocked (hard stop)"}
        else:
            interp = {"labels": ["JAB_TANGENT_NOT_VERIFIED"],
                      "per_module": "interpretation blocked (V0-V5 not all green)"}
        log(f"labels: {interp['labels']}")

    verdict = "COMPLETED" if (v0["passed"] and table and not wave1["dead"]
                              and (smoke_direction is None
                                   or smoke_direction["passed"])) \
        else "LEGALITY_FAILED"
    log(f"verdict={verdict}")

    # ---- files (seven-file run contract) ----
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    with h5py.File(out_dir / "signals.h5", "w") as h5:
        for th, run in base_runs.items():
            grp = h5.create_group(f"bases/th{th:g}")
            grp.create_dataset("base_profile", data=run["base_profile"])
            grp.create_dataset("f_bar", data=run["snapshot"]["f"])
            grp.create_dataset("g_bar", data=run["snapshot"]["g"])
        for label, res in results1.items():
            if not (res.get("ok") and res["run"].get("finite")):
                continue
            grp = h5.create_group(f"tangent/{label}")
            for key in ("t_s", "theta_w", "q_hot_lu", "q_sink_lu"):
                grp.create_dataset(key, data=res["run"]["drive"][key])
    digest = hashlib.sha256(json.dumps(
        {"table": {k: v.get("Y0_cplx") for k, v in table.items()},
         "rows": None if not result_rows else result_rows["rows"]},
        sort_keys=True, default=str).encode()).hexdigest()[:12]
    summary = {
        "gate": unit, "run_id": run_id, "verdict": verdict,
        "gate_status": verdict, "scoped_limitations": [],
        "smoke_mode": bool(smoke),
        "protocol": {"theta_points": thetas, "h_ladder": h_ladder,
                     "hs_rows": hs_rows, "nx": nx,
                     "geometry": "G4a tent canonical verbatim",
                     "variants": wave1_variants + (["A1(structural)"]
                                                   + ([combo_pick] if combo_pick else [])),
                     "settle_periods": settle, "drive_periods": drive_p,
                     "fit_skip_periods": skip},
        "acoustic_structural_report": acoustic_report,
        "verification": verification,
        "results": {"main_table": None if not result_rows else result_rows,
                    "combo": combo_rows,
                    "interpretation": interp,
                    "smoke_fd_direction": smoke_direction,
                    "raw_y_table": {k: {kk: vv for kk, vv in v.items() if kk != "Y0"}
                                    for k, v in table.items()},
                    "dead_cases": wave1["dead"]},
        "pre_registration": prereg,
        "physics_core_digest": digest,
        "code_commit": _git_commit(),
        "wall_clock_min": (datetime.now(timezone.utc) - t0).total_seconds() / 60.0,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=1, default=float), encoding="utf-8")
    (out_dir / "gate_evaluation.json").write_text(json.dumps(
        {"gate": unit, "verdict": verdict, "verification": verification,
         "note": "diagnostic unit (D0-7): labelled rows, not gates; no change "
                 "to WP4_SUBMATRIX_COMPLETE / FINAL_PRODUCTION_NOT_CLAIMED"},
        indent=1, default=float), encoding="utf-8")
    (out_dir / "harmonic_fit.json").write_text(json.dumps(
        {"raw_y_table": summary["results"]["raw_y_table"]},
        indent=1, default=float), encoding="utf-8")
    (out_dir / "config_resolved.yaml").write_text(
        yaml.safe_dump(cfg_all, allow_unicode=True, sort_keys=False),
        encoding="utf-8")
    (out_dir / "provenance.json").write_text(json.dumps(
        {"run_id": run_id, "family": CASE_FAMILY, "argv": sys.argv,
         "machine": os.environ.get("COMPUTERNAME", "unknown"),
         "python": sys.version, "workers": n_workers,
         "pre_registration": prereg,
         "started_utc": t0.isoformat(),
         "finished_utc": datetime.now(timezone.utc).isoformat()},
        indent=1), encoding="utf-8")
    (out_dir / "run_report.md").write_text("\n".join(
        [f"# {unit} run {run_id}", "", f"verdict: **{verdict}**",
         f"labels: **{None if not interp else interp['labels']}**", "", "```text"]
        + log_lines + ["```", ""]), encoding="utf-8")
    log(f"outputs -> {out_dir}")
    return {"verdict": verdict, "out_dir": str(out_dir), "summary": summary}


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase_5 WP4 Jacobian ablation (WP4-JAB)")
    ap.add_argument("--config", default=str(
        REPO_ROOT / "configs" / "phase5" / "a2a_operating_point"
        / "jacobian_ablation_10k_dx2p6.yaml"))
    ap.add_argument("--output-root", default=None)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--select-h", action="store_true",
                    help="cold-smoke h-window selection scan only")
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()
    result = run_jab(args.config, args.output_root, smoke=args.smoke,
                     workers=args.workers, select_h=args.select_h)
    return 0 if result["verdict"] in ("COMPLETED", "H_SELECTION_SCAN") else 1


if __name__ == "__main__":
    sys.exit(main())
