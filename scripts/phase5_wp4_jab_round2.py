"""Phase_5 WP4-JAB round 2: fine-grained A2/A3 sub-map ablation (WP4-JAB2).

Plan: docs/Phase_5/WP4_JAB_next_simulation_guide_simple.md (PLAN_v1.1).
Instrument: core/tangent_substep.py (slot-separated chained sub-map JVP;
bitwise compose anchors + block-union anchors contract-tested in
verification/nonlinear/test_phase5_wp4_jab_round2.py, 8 green).

Waves (single invocation, per-case checkpoints, analysis between waves):

  A  anchors: A0r2 (cold + both hot points), CTRLr2 structural control,
     A2ALL/A3ALL block-union anchors -> V0/V1r2/V2/V3/V4/V5 + anchor rows
     (A0r2 must re-pass the 0.2pp TAN identity gate: instrument changed);
  B  A2-1..A2-5 -> sigma shares vs A2ALL -> major pick (frozen sigma>=0.5
     both points, same direction) -> top-2 confirmation combo (>=80% line);
  C  A3-1..A3-4 -> sigma shares vs A3ALL -> major pick (+ top-2 combo only
     if no single major);
  D  A2_major+A3_major pair (+ Theta=0.075 trend column) -> closure line
     |d_OP^pair| <= 0.2x|d_OP^full| both points;
  E  frozen classification routing (discrete_boundary vs continuum_physical;
     mixed case follows A2's class; A2 top-2 sigma both < 0.7 -> A2_SPLIT ->
     NSF arbitration).

Diagnostic unit (D0-7): COMPLETED/LEGALITY_FAILED + labelled rows only; no
gate claims; no change to WP4_SUBMATRIX_COMPLETE / FINAL_PRODUCTION_NOT_CLAIMED.
"""

from __future__ import annotations

import argparse
import copy
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

from core.solver import GasSolver2D  # noqa: E402
from core.tangent_step import direct_step, propagate_tangent  # noqa: E402
from core.tangent_substep import (  # noqa: E402
    R2TangentOperator,
    compute_r2_bases,
    r2_ablated_slots,
)
from scripts.phase2_m2_verification import load_config  # noqa: E402
from scripts.phase5_g1w_wall_neutrality import _git_commit  # noqa: E402
from scripts.phase5_g4a_dc_basestate import _cplx, fit_admittance  # noqa: E402
from scripts.phase5_wp4_jacobian_ablation import (  # noqa: E402
    _checkpoint_wrap,
    _extrapolate_y,
    _jab_base_worker,
    _sha256,
    _snapshot_digest,
    snapshot_to_base,
)
from scripts.phase5_wp4_tangent_response import tangent_fit  # noqa: E402

CASE_FAMILY = "wp4_jacobian_ablation_r2"
A2_SINGLES = ["A2-1", "A2-2", "A2-3", "A2-4", "A2-5"]
A3_SINGLES = ["A3-1", "A3-2", "A3-3", "A3-4"]


# ---------------------------------------------------------------------------
# workers (module-level, picklable, checkpointed)
# ---------------------------------------------------------------------------

def _jab2_tangent_worker_raw(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    label = payload["label"]
    try:
        cfg = copy.deepcopy(payload["gas_cfg"])
        cfg["numerics"] = {**cfg["numerics"], "nx": int(payload["nx"]),
                           "ny": int(payload["ny"])}
        solver = GasSolver2D(cfg)
        hot_base = snapshot_to_base(payload["hot_run"])
        cold_base = snapshot_to_base(payload["cold_run"])
        hot = compute_r2_bases(solver, hot_base)
        cold = compute_r2_bases(solver, cold_base)
        op = R2TangentOperator(solver, hot_base, hot, cold_base, cold,
                               h=float(payload["h"]),
                               ablated=r2_ablated_slots(payload["variant"]))
        run = propagate_tangent(
            op, frequency_hz=float(payload["frequency_hz"]),
            drive_periods=float(payload["drive_periods"]),
            samples_per_period=int(payload["samples_per_period"]), log=None)
        run["label"] = label
        run["variant"] = payload["variant"]
        run["theta_dc"] = hot_base.theta_dc_target
        run["h"] = float(payload["h"])
        return label, {"ok": True, "run": run, "log": []}
    except Exception as exc:
        return label, {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                       "log": []}


def _jab2_tangent_worker(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    return _checkpoint_wrap(_jab2_tangent_worker_raw, payload)


# ---------------------------------------------------------------------------
# assembly / analysis helpers
# ---------------------------------------------------------------------------

def _payloads(variants: list[str], thetas: list[float], h_ladder: list[float],
              base_runs: dict[float, dict], common: dict[str, Any],
              ckpt: dict[str, Any], *, include_cold_anchor: bool) -> list[dict]:
    out = []

    def entry(label, variant, h, th):
        p = {**common, "label": label, "variant": variant, "h": h,
             "hot_run": base_runs[th], "cold_run": base_runs[0.0],
             "checkpoint_path": str(ckpt["dir"] / f"{label}.pkl"),
             "checkpoint_identity": {
                 "kind": "tan_r2", "variant": variant, "theta": th, "h": h,
                 "cfg": ckpt["cfg"], "instr": ckpt["instr"],
                 "hot": ckpt["snap"][th], "cold": ckpt["snap"][0.0],
                 **{k: common[k] for k in ("ny", "nx", "frequency_hz",
                                           "samples_per_period",
                                           "drive_periods")}}}
        return p

    if include_cold_anchor:
        for h in h_ladder:
            out.append(entry(f"t2_A0r2_th0_h{h:g}", "A0r2", h, 0.0))
    for v in variants:
        for th in thetas:
            for h in h_ladder:
                out.append(entry(
                    f"t2_{v.replace('+', '_')}_th{th:g}_h{h:g}", v, h, th))
    return out


def _collect(results: dict, variants: list[str], thetas: list[float],
             h_ladder: list[float], f_hz: float, skip: float,
             table: dict, audits: dict, dead: list) -> None:
    def run_of(label):
        res = results.get(label)
        return res["run"] if res and res.get("ok") and res["run"].get("finite") else None

    if "cold_anchor" not in table:
        y = {}
        for h in h_ladder:
            r = run_of(f"t2_A0r2_th0_h{h:g}")
            if r is None:
                dead.append(f"t2_A0r2_th0_h{h:g}")
                continue
            y[h] = fit_admittance(r, f_hz, skip)["Y_face_theta_units"]
            for k in audits:
                audits[k] = max(audits[k], r["audits"][k])
        if len(y) == len(h_ladder):
            table["cold_anchor"] = _extrapolate_y(y, h_ladder)
    for v in variants:
        for th in thetas:
            key = f"{v}|{th:g}"
            if key in table:
                continue
            y = {}
            for h in h_ladder:
                lb = f"t2_{v.replace('+', '_')}_th{th:g}_h{h:g}"
                r = run_of(lb)
                if r is None:
                    dead.append(lb)
                    continue
                y[h] = fit_admittance(r, f_hz, skip)["Y_face_theta_units"]
                for k in audits:
                    audits[k] = max(audits[k], r["audits"][k])
            if len(y) == len(h_ladder):
                table[key] = _extrapolate_y(y, h_ladder)


def _dop(table: dict, key: str) -> float:
    d = table[key]["Y0"] / table["cold_anchor"]["Y0"]
    return (abs(d) - 1.0) * 100.0


def _s_pp(table: dict, variant: str, th: float, d_full: dict) -> float:
    return _dop(table, f"{variant}|{th:g}") - d_full[f"{th:g}"]


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def run_jab2(config_path: str | Path, output_root: str | Path | None = None,
             *, smoke: bool = False, workers: int | None = None) -> dict[str, Any]:
    import h5py
    import yaml

    from scripts.phase5_g1a_amplitude_envelope import execute_cases

    t0 = datetime.now(timezone.utc)
    cfg_path = Path(config_path)
    cfg_all = load_config(cfg_path)
    proto = cfg_all["jab2_smoke" if smoke else "jab2"]
    gates = cfg_all["gates"]
    refs = cfg_all["references"]
    interp_cfg = cfg_all["interpretation"]
    gas_cfg = load_config(REPO_ROOT / str(cfg_all["inheritance"]["gas_config"]))

    log_lines: list[str] = []

    def log(msg: str) -> None:
        line = f"JAB2 {msg}"
        print(line, flush=True)
        log_lines.append(line)

    unit = str(proto.get("unit_label", "WP4-JAB2"))
    f_hz = float(proto["frequency_Hz"])
    ny = 2 * int(proto["hs_rows"])
    nx = int(proto["nx"])
    thetas = [float(t) for t in proto["theta_points"]]
    trend_th = float(proto.get("trend_theta", 0.0)) if not smoke else 0.0
    spp = int(proto["samples_per_period"])
    settle = float(proto["settle_periods"])
    drive_p = float(proto["drive_periods"])
    skip = float(proto["fit_skip_periods"])
    h_ladder = [float(h) for h in cfg_all["jvp"]["h_ladder"]]
    if not bool(cfg_all["jvp"]["h_frozen"]):
        raise RuntimeError("round-2 requires the inherited frozen h ladder")
    n_workers = workers if workers is not None else max(1, (os.cpu_count() or 4) - 2)

    prereg = {
        "config_sha256": _sha256(cfg_path),
        "tangent_step_sha256": _sha256(REPO_ROOT / "core" / "tangent_step.py"),
        "tangent_substep_sha256": _sha256(REPO_ROOT / "core" / "tangent_substep.py"),
        "runner_sha256": _sha256(Path(__file__)),
        "frozen_before_execution_utc": t0.isoformat(),
    }
    log(f"pre-registration digests: {prereg}")

    out_root = Path(output_root) if output_root else \
        REPO_ROOT / "results" / "phase5" / CASE_FAMILY
    ckpt_dir = out_root / "checkpoints" / \
        f"{'smoke' if smoke else 'auth'}_{prereg['config_sha256'][:8]}"
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    # ---- base wave ----
    base_thetas = [0.0] + thetas + ([trend_th] if trend_th else [])
    common_base = dict(gas_cfg=gas_cfg, ny=ny, nx=nx, frequency_hz=f_hz,
                       samples_per_period=spp, settle_periods=settle,
                       drive_periods=0.0, eps_ac=0.0, snapshot=True)
    base_payloads = [{**common_base, "label": f"base_th{th:g}", "kind": "base",
                      "theta_dc": th,
                      "checkpoint_path": str(ckpt_dir / f"base_th{th:g}.pkl"),
                      "checkpoint_identity": {
                          "kind": "base", "theta_dc": th, "ny": ny, "nx": nx,
                          "spp": spp, "settle": settle, "f_hz": f_hz,
                          "cfg": prereg["config_sha256"]}}
                     for th in base_thetas]
    base_results = execute_cases(base_payloads, n_workers, log,
                                 worker=_jab_base_worker)
    base_runs: dict[float, dict] = {}
    for th in base_thetas:
        res = base_results.get(f"base_th{th:g}")
        if res and res.get("ok") and res["run"].get("finite"):
            base_runs[th] = res["run"]
            log(f"[base_th{th:g}] stat={res['run']['stationarity_per_period']:.2e} "
                f"ThetaDC={res['run']['theta_dc_measured']:.4f}")
    v0 = {"all_bases_finite": len(base_runs) == len(base_thetas)}
    if v0["all_bases_finite"]:
        v0["stationarity_worst"] = max(base_runs[t]["stationarity_per_period"]
                                       for t in base_thetas)
        v0["state_match_worst"] = max(
            (abs(base_runs[t]["theta_dc_measured"] / t - 1.0)
             for t in base_thetas if t > 0.0), default=0.0)
        v0["dc_closure_worst"] = max(
            (base_runs[t]["dc_closure_rel"] for t in base_thetas if t > 0.0),
            default=0.0)
        v0["passed"] = bool(
            v0["stationarity_worst"] <= float(gates["stationarity_per_period"])
            and v0["state_match_worst"] <= float(gates["state_match_rel"])
            and v0["dc_closure_worst"] <= float(gates["dc_closure_rel"]))
    else:
        v0["passed"] = False
    log(f"V0: {v0}")
    if not v0["passed"]:
        raise SystemExit("V0 base legality failed; aborting round 2")

    # ---- V1r2: chained R2 JVP vs singleshot full-step FD on the hot bases ----
    probe_cfg = copy.deepcopy(gas_cfg)
    probe_cfg["numerics"] = {**probe_cfg["numerics"], "nx": nx, "ny": ny}
    probe_solver = GasSolver2D(probe_cfg)
    v1r2 = {}
    cold_base = snapshot_to_base(base_runs[0.0])
    cold_bases = compute_r2_bases(probe_solver, cold_base)
    r_f_by = {}
    for th in thetas:
        hot_base = snapshot_to_base(base_runs[th])
        hb = compute_r2_bases(probe_solver, hot_base)
        r_f_by[f"{th:g}"] = hb.stage.r_f
        rng = np.random.default_rng(20260810)
        df = rng.standard_normal(hot_base.f.shape)
        dg = rng.standard_normal(hot_base.g.shape)
        op = R2TangentOperator(probe_solver, hot_base, hb, cold_base,
                               cold_bases, h=h_ladder[1],
                               ablated=frozenset())
        s = op.macro_scale(df, dg, op.theta0)
        h = h_ladder[1]
        vf, vg, eta = df / s, dg / s, op.theta0 / s
        cf, cg, _, _ = op.step(df, dg, op.theta0)
        fp, gp, _, _ = direct_step(probe_solver, hot_base.f + h * vf,
                                   hot_base.g + h * vg,
                                   hot_base.theta_w + h * eta,
                                   hot_base.theta_amb, hot_base.hs)
        fm, gm, _, _ = direct_step(probe_solver, hot_base.f - h * vf,
                                   hot_base.g - h * vg,
                                   hot_base.theta_w - h * eta,
                                   hot_base.theta_amb, hot_base.hs)
        odd = np.concatenate([(fp - fm).ravel(), (gp - gm).ravel()]) * (s / (2 * h))
        chain = np.concatenate([cf.ravel(), cg.ravel()])
        rel = float(np.linalg.norm(chain - odd) / max(np.linalg.norm(odd), 1e-300))
        v1r2[f"{th:g}"] = rel
        log(f"V1r2 th={th:g}: chain-vs-singleshot rel={rel:.2e} r_F={hb.stage.r_f:.2e}")
    v1r2_pass = all(v <= float(gates["chain_vs_singleshot_rel"])
                    for v in v1r2.values())
    r_f_pass = all(v <= float(gates["r_f_max"]) for v in r_f_by.values())

    common_tan = dict(gas_cfg=gas_cfg, ny=ny, nx=nx, frequency_hz=f_hz,
                      samples_per_period=spp, drive_periods=drive_p)
    ckpt = {"dir": ckpt_dir, "cfg": prereg["config_sha256"],
            "instr": prereg["tangent_substep_sha256"],
            "snap": {th: _snapshot_digest(base_runs[th]) for th in base_thetas}}
    table: dict[str, Any] = {}
    audits = {"mass_tangent_rel_worst": 0.0, "energy_account_rel_worst": 0.0}
    dead: list[str] = []

    def run_wave(variants, ths, *, cold_anchor=False):
        return run_mixed([(variants, ths)], cold_anchor=cold_anchor)

    def run_mixed(specs, *, cold_anchor=False):
        """One pool batch over several (variants, thetas) shapes."""
        pl = []
        for i, (variants, ths) in enumerate(specs):
            pl += _payloads(variants, ths, h_ladder, base_runs, common_tan,
                            ckpt, include_cold_anchor=cold_anchor and i == 0)
        res = execute_cases(pl, n_workers, log, worker=_jab2_tangent_worker)
        for variants, ths in specs:
            _collect(res, variants, ths, h_ladder, f_hz, skip, table, audits,
                     dead)
        return res

    # ---- wave 1: anchors + control + ALL singles in ONE pool batch ----
    # (A2/A3 singles depend only on the base snapshots, not on wave-A
    # analysis; merging them fills a 96-core batch instead of serializing
    # three small waves. Interpretation stays gated on verification below.)
    anchors = ["A0r2", "CTRLr2"] + ([] if smoke else ["A2ALL", "A3ALL"])
    wave1 = anchors + ([] if smoke else A2_SINGLES + A3_SINGLES)
    run_wave(wave1, thetas, cold_anchor=True)
    have = "cold_anchor" in table and all(f"A0r2|{t:g}" in table for t in thetas)
    if not have:
        raise SystemExit(f"anchor wave incomplete (dead: {dead})")
    d_full = {f"{t:g}": _dop(table, f"A0r2|{t:g}") for t in thetas}
    # V2/V3/V4/V5
    v2 = {"worst": max(r["h_spread_rel"] for r in table.values()),
          "gate": float(gates["v2_y_h_spread_rel"])}
    v2["passed"] = v2["worst"] <= v2["gate"]
    if smoke:
        v3 = {"passed": None, "not_applicable": "smoke grid vs archived refs"}
        v4 = {"passed": None, "not_applicable": "smoke grid vs archived refs"}
        for th in thetas:
            log(f"smoke d_OP th={th:g}: {d_full[f'{th:g}']:+.3f}%")
    else:
        y_ref = complex(float(refs["y0_tangent_cold"]["re"]),
                        float(refs["y0_tangent_cold"]["im"]))
        ratio = table["cold_anchor"]["Y0"] / y_ref
        v3 = {"amp_rel_err": abs(abs(ratio) - 1.0),
              "phase_deg_err": abs(math.degrees(math.atan2(ratio.imag, ratio.real)))}
        v3["passed"] = (v3["amp_rel_err"] <= float(gates["v3_cold_amp_rel"])
                        and v3["phase_deg_err"] <= float(gates["v3_cold_phase_deg"]))
        dop_ref = {float(k): float(v) for k, v in refs["dop_tan_pct"].items()}
        v4 = {"rows": {}}
        for th in thetas:
            dev = d_full[f"{th:g}"] - dop_ref[th]
            v4["rows"][f"{th:g}"] = {"d_OP_pct": d_full[f"{th:g}"],
                                     "deviation_pp": dev,
                                     "within": abs(dev) <= float(gates["v4_tan_identity_pp"])}
            log(f"V4r2 th={th:g}: d_OP={d_full[f'{th:g}']:+.3f}% dev={dev:+.4f}pp")
        v4["passed"] = all(r["within"] for r in v4["rows"].values())
    v5 = {"mass_worst": audits["mass_tangent_rel_worst"],
          "energy_worst": audits["energy_account_rel_worst"]}
    v5["passed"] = (v5["mass_worst"] <= float(gates["v5_mass_tangent_rel"])
                    and v5["energy_worst"] <= float(gates["v5_energy_account_rel"]))
    ctrl_worst = max(abs(_s_pp(table, "CTRLr2", t, d_full)) for t in thetas)
    ctrl_clean = ctrl_worst <= float(interp_cfg["negative_control_max_abs_S_pp"])
    log(f"CTRLr2 worst |S|={ctrl_worst:.2e} pp -> {'clean' if ctrl_clean else 'FAIL'}")
    anchor_rows = {}
    anchors_ok = True
    if not smoke:
        r1s = {k: {float(t): float(x) for t, x in v.items()}
               for k, v in refs["r1_S_pp"].items()}
        for union, blk in (("A2ALL", "A2"), ("A3ALL", "A3")):
            for th in thetas:
                s_now = _s_pp(table, union, th, d_full)
                devi = s_now - r1s[blk][th]
                ok = abs(devi) <= float(interp_cfg["block_anchor_tol_pp"])
                anchors_ok = anchors_ok and ok
                anchor_rows[f"{union}|{th:g}"] = {"S_pp": s_now,
                                                  "r1_S_pp": r1s[blk][th],
                                                  "dev_pp": devi, "within": ok}
                log(f"anchor {union} th={th:g}: S={s_now:+.3f} vs r1 "
                    f"{r1s[blk][th]:+.3f} (dev {devi:+.4f}pp)")
    verification = {"V0": v0, "V1r2": {"rows": v1r2, "passed": v1r2_pass},
                    "V2": v2, "V3": v3, "V4": v4, "V5": v5,
                    "r_F": {"values": r_f_by, "passed": r_f_pass},
                    "control": {"worst_abs_S_pp": ctrl_worst, "clean": ctrl_clean},
                    "block_anchors": {"rows": anchor_rows, "passed": anchors_ok}}
    applicable = [x["passed"] for x in (v0, v2, v5) if x.get("passed") is not None]
    applicable += [x["passed"] for x in (v3, v4) if x.get("passed") is not None]
    verified = all(applicable + [v1r2_pass, r_f_pass, ctrl_clean, anchors_ok])
    log(f"round-2 verification: {'PASS' if verified else 'NOT VERIFIED'}")

    labels: list[str] = []
    sigma_tab: dict[str, Any] = {}
    picks: dict[str, Any] = {}
    if verified and not smoke:
        sig_line = float(interp_cfg["sigma_major"])
        split_line = float(interp_cfg["split_line"])

        def sigma_stage(singles, union_key, stage_tag):
            # singles already computed in wave 1; _collect is idempotent
            run_wave(singles, thetas)
            rows = {}
            for v in singles:
                sig = {}
                for th in thetas:
                    s_v = _s_pp(table, v, th, d_full)
                    s_all = _s_pp(table, union_key, th, d_full)
                    sig[f"{th:g}"] = {"S_pp": s_v, "sigma": s_v / s_all}
                rows[v] = sig
                log(f"{stage_tag} {v}: " + " ".join(
                    f"th{t}: S={sig[f'{t:g}']['S_pp']:+.3f} "
                    f"sigma={sig[f'{t:g}']['sigma']:+.3f}" for t in thetas))
            ranked = sorted(singles, key=lambda v: -np.mean(
                [abs(rows[v][f"{t:g}"]["sigma"]) for t in thetas]))
            major = ranked[0]
            is_major = all(rows[major][f"{t:g}"]["sigma"] >= sig_line
                           for t in thetas)
            return rows, ranked, major, is_major

        # ---- sigma analysis for BOTH blocks (wave-1 data; no new compute) ----
        a2_rows, a2_rank, a2_major, a2_is = sigma_stage(A2_SINGLES, "A2ALL", "A2")
        sigma_tab["A2"] = a2_rows
        a3_rows, a3_rank, a3_major, a3_is = sigma_stage(A3_SINGLES, "A3ALL", "A3")
        sigma_tab["A3"] = a3_rows

        # ---- wave 2 (single merged batch): A2 confirmation pair + major
        # pair + trend column ----
        confirm_pair = f"{a2_rank[0]}+{a2_rank[1]}"
        pair = f"{a2_major}+{a3_major}"
        trend_ths = [trend_th] if trend_th else []
        specs = [([confirm_pair, pair], thetas)]
        if trend_ths:
            specs.append(([pair, "A0r2"], trend_ths))
        run_mixed(specs)

        conf = {}
        for th in thetas:
            frac = _s_pp(table, confirm_pair, th, d_full) / _s_pp(table, "A2ALL", th, d_full)
            conf[f"{th:g}"] = frac
        conf_ok = all(f >= float(interp_cfg["confirm_frac"]) for f in conf.values())
        picks["A2"] = {"ranked": a2_rank, "major": a2_major,
                       "major_passes_line": a2_is, "confirm_pair": confirm_pair,
                       "confirm_frac": conf, "confirm_ok": conf_ok}
        top2_sigma = [np.mean([a2_rows[v][f"{t:g}"]["sigma"] for t in thetas])
                      for v in a2_rank[:2]]
        a2_split = all(s < split_line for s in top2_sigma)
        labels.append(f"JAB2_A2_MAIN_{a2_major.replace('-', '_')}" if a2_is
                      else ("JAB2_A2_SPLIT" if a2_split else
                            f"JAB2_A2_TOP2_{a2_rank[0].replace('-', '_')}_"
                            f"{a2_rank[1].replace('-', '_')}"))
        picks["A3"] = {"ranked": a3_rank, "major": a3_major,
                       "major_passes_line": a3_is}
        labels.append(f"JAB2_A3_MAIN_{a3_major.replace('-', '_')}" if a3_is
                      else "JAB2_A3_DISTRIBUTED")
        close = {}
        for th in thetas:
            close[f"{th:g}"] = abs(_dop(table, f"{pair}|{th:g}")) \
                / abs(d_full[f"{th:g}"])
        close_ok = all(c <= float(interp_cfg["combo_close_frac"])
                       for c in close.values())
        picks["pair"] = {"pair": pair, "close_frac": close,
                         "closed": close_ok}
        if trend_th and f"{pair}|{trend_th:g}" in table \
                and f"A0r2|{trend_th:g}" in table:
            picks["pair"]["trend_column"] = {
                "theta": trend_th,
                "d_OP_full_pct": _dop(table, f"A0r2|{trend_th:g}"),
                "d_OP_pair_pct": _dop(table, f"{pair}|{trend_th:g}")}
        labels.append("JAB2_PAIR_CLOSED" if close_ok else "JAB2_PAIR_NOT_CLOSED")

        # ---- classification routing (frozen table) ----
        cls = interp_cfg["classification"]
        a2_class = ("discrete_boundary" if a2_major in cls["discrete_boundary"]
                    else "continuum_physical")
        if a2_split:
            route = "JAB2_ROUTE_NSF_ARBITRATION"
        elif a2_class == "discrete_boundary":
            route = "JAB2_ROUTE_LBM_BOUNDARY"
        else:
            route = "JAB2_ROUTE_NSF_ARBITRATION"
        labels.append(route)
        log(f"labels: {labels}")
    elif not verified:
        labels = ["JAB2_TANGENT_NOT_VERIFIED"]

    verdict = "COMPLETED" if (verified and not dead) else "LEGALITY_FAILED"
    log(f"verdict={verdict}")

    # ---- files (seven-file contract) ----
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    with h5py.File(out_dir / "signals.h5", "w") as h5:
        for th, run in base_runs.items():
            grp = h5.create_group(f"bases/th{th:g}")
            grp.create_dataset("base_profile", data=run["base_profile"])
    digest = hashlib.sha256(json.dumps(
        {k: v.get("Y0_cplx") for k, v in table.items()},
        sort_keys=True, default=str).encode()).hexdigest()[:12]
    summary = {
        "gate": unit, "run_id": run_id, "verdict": verdict,
        "gate_status": verdict, "scoped_limitations": [],
        "smoke_mode": bool(smoke),
        "protocol": {"theta_points": thetas, "trend_theta": trend_th,
                     "h_ladder": h_ladder, "hs_rows": int(proto["hs_rows"]),
                     "nx": nx, "geometry": "G4a tent canonical verbatim"},
        "verification": verification,
        "results": {
            "d_OP_full_pct": d_full if have else None,
            "sigma_table": sigma_tab, "picks": picks, "labels": labels,
            "raw_y_table": {k: {kk: vv for kk, vv in v.items() if kk != "Y0"}
                            for k, v in table.items()},
            "dead_cases": dead},
        "pre_registration": prereg,
        "physics_core_digest": digest,
        "code_commit": _git_commit(),
        "wall_clock_min": (datetime.now(timezone.utc) - t0).total_seconds() / 60.0,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=1, default=float), encoding="utf-8")
    (out_dir / "gate_evaluation.json").write_text(json.dumps(
        {"gate": unit, "verdict": verdict, "verification": verification,
         "note": "diagnostic unit (D0-7): labelled rows, not gates"},
        indent=1, default=float), encoding="utf-8")
    (out_dir / "harmonic_fit.json").write_text(json.dumps(
        {"raw_y_table": summary["results"]["raw_y_table"]},
        indent=1, default=float), encoding="utf-8")
    (out_dir / "config_resolved.yaml").write_text(
        yaml.safe_dump(cfg_all, allow_unicode=True, sort_keys=False),
        encoding="utf-8")
    (out_dir / "provenance.json").write_text(json.dumps(
        {"run_id": run_id, "family": CASE_FAMILY, "argv": sys.argv,
         "machine": os.environ.get("COMPUTERNAME",
                                   os.environ.get("HOSTNAME", "unknown")),
         "python": sys.version, "workers": n_workers,
         "pre_registration": prereg,
         "started_utc": t0.isoformat(),
         "finished_utc": datetime.now(timezone.utc).isoformat()},
        indent=1), encoding="utf-8")
    (out_dir / "run_report.md").write_text("\n".join(
        [f"# {unit} run {run_id}", "", f"verdict: **{verdict}**",
         f"labels: **{labels}**", "", "```text"] + log_lines + ["```", ""]),
        encoding="utf-8")
    log(f"outputs -> {out_dir}")
    return {"verdict": verdict, "out_dir": str(out_dir), "summary": summary}


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase_5 WP4-JAB round 2")
    ap.add_argument("--config", default=str(
        REPO_ROOT / "configs" / "phase5" / "a2a_operating_point"
        / "jacobian_ablation_r2_10k_dx2p6.yaml"))
    ap.add_argument("--output-root", default=None)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()
    result = run_jab2(args.config, args.output_root, smoke=args.smoke,
                      workers=args.workers)
    return 0 if result["verdict"] == "COMPLETED" else 1


if __name__ == "__main__":
    sys.exit(main())
