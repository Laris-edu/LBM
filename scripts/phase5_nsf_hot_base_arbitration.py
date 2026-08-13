"""Phase_5 NSF hot-base-state tangent arbitration runner (plan v1.0, D0-7).

Executes docs/Phase_5/NSF_hot_basestate_tangent_arbitration_plan_v1.0.md on
the frequency-domain linearized hot-base NSF instrument
(reference/nsf_hot_base_linear_1d.py): the continuum counterpart of the LBM
TAN/JAB tangent, with the plan §6 model pair

  model="full"    — full hot-base linearized NSF (all base-gradient terms),
  model="nograd"  — diagnostic with ONLY the two boxed couplings removed
                    (u_hat rho_bar' in continuity, rho_bar cv u_hat T_bar'
                    in energy; all coefficients stay hot-base local),

on the canonical column (H_s = 4.61 delta_T, 10 kHz, isothermal sink) at
Theta_DC in {0, 0.02, 0.05, 0.075, 0.10} (plan §6 main matrix {0, 0.05,
0.10}; 0.02/0.075 are trend supplements matching the A2a/DC-arm five-point
series).

TRANSPORT BRANCHES (execution decision, recorded in the report):
- "route_b_frozen_const" — the plan §3 primary: k, mu, cp, cv frozen at T0
  (Route-B reference-state constants; the arbitration-literal instrument).
- "lbm_equivalent_g0"    — G3's formal 1D-lbm-equivalent branch (G0-measured
  k ∝ T^{+1.04}, mu ∝ T^{-0.60} at k1). NOT a plan deviation: it is the
  certified continuum surrogate of the frozen LBM bulk and the branch behind
  the plan §8 row "现有 1D NSF" (DC-arm authoritative series, POSITIVE), so
  it is required (a) to validate this new instrument against that archived
  series and (b) to keep the §9 verdict from conflating "hot-base structure
  at frozen transport" with "LBM-equivalent bulk medium".
- "physical_air"         — Sutherland-anchored real-air shape (DC-arm second
  branch), validation/appendix row only (plan §11 keeps温变真实空气物性 out
  of the primary arbitration; here it never carries the verdict).

Judgement lines (FROZEN before any hot-base number is produced; plan §10):
  V1  Theta=0 degeneracy: model pair exactly equal Y; closed-box corrected
      identity vs Phase_1 half-space anchor <= 1% (WP1-2-certified identity);
  V2  grid: d_OP(cpd=96) - d_OP(cpd=48) within 0.02 pp per case; full ladder
      {24,48,96,192} archived;
  V3  BCs at solver backward-error level (<=1e-10 abs on unit T_w_hat);
  V4  base state: mass integral <=1e-10; const-branch closed form
      p_bar/p0 = Theta/ln(1+Theta) <=1e-10;
  V5  linearity: T_w_hat -> T_w_hat/2 leaves Y to <=1e-12 rel;
  V6  cross-instrument (certified G3 nonlinear time-domain solver, DC-arm
      protocol eps=0.005, delta/12, 12-cycle settle): |Delta d_OP| <= 0.15 pp
      per point — fresh runs for the const branch; archived authoritative
      DC-arm raw series (run 20260803T083909Z) for g0/physical;
  V7  no tuning: all constants imported from frozen sources; T_w_hat is the
      only drive and enters linearly.

Classification (plan §9, per branch, FROZEN): sign calls on the main points
{0.05, 0.10} with significance guard U_SIG = 0.3 pp (>= 15x the instrument
uncertainty budget V2+V6). Case A: full positive; Case B: full negative
(same-order qualifier vs LBM if 1/3 <= |ratio| <= 3); Case C: full negative
AND nograd positive (gradient-coupling mechanism); Case D: full AND nograd
positive (label "AD" when A and D both hold). Anything else INCONCLUSIVE.

Diagnostic unit (D0-7): no gate claims; changes no Gate /
FINAL_PRODUCTION_NOT_CLAIMED status. Verdict vocabulary: COMPLETED / FAILED
(fail-loud on any frozen validation line) + classification labels.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from postproc.multiharmonic_fit import fit_multiharmonic  # noqa: E402
from reference.constants import default_params, omega_from_frequency  # noqa: E402
from reference.nonlinear_nsf_1d import (  # noqa: E402
    NSF1DConfig,
    WallDrive,
    g0_measured_transport,
    lbm_equivalent_transport,
    physical_air_transport,
    run_nsf1d,
)
from reference.nsf_hot_base_linear_1d import (  # noqa: E402
    INSTRUMENT_ID,
    solve_base_state,
    solve_linear_response,
)
from reference.thermal_admittance import thermal_admittance_halfspace  # noqa: E402

UNIT = "NSF-HOT-BASE-ARB"
PLAN_DOC = "docs/Phase_5/NSF_hot_basestate_tangent_arbitration_plan_v1.0.md"

# ---- frozen protocol (plan §2/§6/§10) ----
FREQUENCY_HZ = 1.0e4
HEIGHT_OVER_DELTA = 4.61  # G4a canonical tent H_s (DC-arm frozen value)
THETA_MAIN = (0.05, 0.10)  # plan §6 verdict points
THETA_SET = (0.0, 0.02, 0.05, 0.075, 0.10)  # + A2a/DC-arm trend supplements
CPD_MAIN = 96.0
CPD_LADDER = (24.0, 48.0, 96.0, 192.0)
MODELS = ("full", "nograd")

# ---- frozen judgement lines (see module docstring) ----
LINE_ANCHOR_REL = 1e-2  # V1 closed-box corrected identity vs Phase_1 anchor
LINE_GRID_PP = 0.02  # V2 d_OP(96) vs d_OP(48)
LINE_BC_ABS = 1e-10  # V3
LINE_BASE_REL = 1e-10  # V4
LINE_LINEARITY_REL = 1e-12  # V5
LINE_XINST_PP = 0.15  # V6 vs certified time-domain instrument
U_SIG_PP = 0.3  # classification sign-significance guard

# ---- time-domain cross-check protocol (DC-arm frozen; provenance:
# scripts/phase5_wp4_oned_dc_arm.py authoritative run 20260803T083909Z) ----
TD_EPS = 0.005
TD_CELLS_PER_DELTA = 12.0
TD_CYCLES = 14.0
TD_SETTLE = 12.0

# ---- frozen external references (final-table rows + V6 archived series) ----
# LBM production D_OP (A2a map, Phase5_STATUS §6.1; runs 20260803T185241Z /
# 20260801T081856Z / 20260803T185101Z / 20260802T104619Z):
LBM_PRODUCTION = {
    0.02: {"d_op_pct": -1.17, "phase_deg": -0.57},
    0.05: {"d_op_pct": -2.83, "phase_deg": -1.38},
    0.075: {"d_op_pct": -4.11, "phase_deg": -2.02},
    0.10: {"d_op_pct": -5.31, "phase_deg": -2.62},
}
# LBM TAN tangent (WP4-TAN R1, B-machine run 20260805T092726Z): the
# apples-to-apples tangent row for this arbitration.
LBM_TAN = {0.05: -2.835, 0.10: -5.317}
# QS static family (G4a §11 protocol, STATUS §6.1 table):
QS0 = {0.02: +0.97, 0.05: +2.40, 0.075: +3.58, 0.10: +4.74}
QS1 = {0.02: +0.95, 0.05: +2.35, 0.075: +3.50, 0.10: +4.64}
# 1D DC-arm authoritative five-point series (run 20260803T083909Z,
# results/phase5/oned_dc_arm; RAW D_OP ratios — same readout family as this
# runner's primary Y_raw; corrected values in that run's summary.json):
DC_ARM_RAW = {
    "lbm_equivalent_g0": {
        0.02: {"d_op_pct": +0.4750, "phase_deg": -0.008},
        0.05: {"d_op_pct": +1.1817, "phase_deg": -0.021},
        0.075: {"d_op_pct": +1.7654, "phase_deg": -0.032},
        0.10: {"d_op_pct": +2.3444, "phase_deg": -0.045},
    },
    "physical_air": {
        0.02: {"d_op_pct": +0.3244, "phase_deg": -0.006},
        0.05: {"d_op_pct": +0.7992, "phase_deg": -0.016},
        0.075: {"d_op_pct": +1.1843, "phase_deg": -0.024},
        0.10: {"d_op_pct": +1.5605, "phase_deg": -0.033},
    },
}


def _cplx(z: complex) -> dict:
    return {
        "re": float(np.real(z)),
        "im": float(np.imag(z)),
        "abs": float(abs(z)),
        "phase_deg": float(math.degrees(math.atan2(np.imag(z), np.real(z)))),
    }


def _dop(y_theta: complex, y_cold: complex) -> dict:
    d = y_theta / y_cold
    out = _cplx(d)
    out["d_op_pct"] = (abs(d) - 1.0) * 100.0
    return out


def _n_nodes(cpd: float) -> int:
    return int(round(HEIGHT_OVER_DELTA * cpd)) + 1


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT,
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001 - provenance best-effort
        return "unknown"


def solve_point(params, transport, *, theta: float, model: str, cpd: float,
                T_w_hat: complex = 1.0 + 0.0j):
    base = solve_base_state(
        params, transport, theta_dc=theta,
        height_m=HEIGHT_OVER_DELTA * _delta_t(params),
        n_nodes=_n_nodes(cpd),
    )
    return solve_linear_response(
        base, params, transport, frequency_hz=FREQUENCY_HZ, model=model,
        T_w_hat=T_w_hat,
    )


def _delta_t(params) -> float:
    alpha0 = params.kg / (params.rho0 * params.cp)
    return math.sqrt(2.0 * alpha0 / omega_from_frequency(FREQUENCY_HZ))


def time_domain_admittance(params, transport, *, theta_dc: float) -> dict:
    """Certified G3 nonlinear time-domain solver, DC-arm protocol (V6)."""

    omega = omega_from_frequency(FREQUENCY_HZ)
    drive = WallDrive(
        kind="temperature", frequency_hz=FREQUENCY_HZ,
        amplitude=TD_EPS * params.T0, mean=theta_dc * params.T0,
        ramp_cycles=2.0,
    )
    cfg = NSF1DConfig(
        params=params, transport=transport, drive=drive,
        height_m=HEIGHT_OVER_DELTA * _delta_t(params),
        n_cells=int(round(HEIGHT_OVER_DELTA * TD_CELLS_PER_DELTA)),
        n_cycles=TD_CYCLES, samples_per_cycle=64, lid_bc="isothermal",
    )
    res = run_nsf1d(cfg)
    mask = res.t_samples >= TD_SETTLE / FREQUENCY_HZ * (1.0 - 1e-12)
    t = res.t_samples[mask]
    q1 = fit_multiharmonic(t, res.q_wall_conductive[mask], omega,
                           n_harmonics=5).harmonic(1)
    tw1 = fit_multiharmonic(t, res.wall_temperature[mask], omega,
                            n_harmonics=5).harmonic(1)
    p1 = fit_multiharmonic(t, res.p_box_mean[mask], omega,
                           n_harmonics=5).harmonic(1)
    return {
        "Y_raw": q1 / tw1,
        "Y_corrected": q1 / (tw1 - p1 / (params.rho0 * params.cp)),
        "mass_drift_rel": res.mass_drift_rel,
        "energy_residual_rel_flux": res.energy_residual_rel_flux,
    }


def run_cold_validations(params, branches) -> tuple[dict, bool]:
    """Frozen V1/V3/V4/V5 lines on the cold point — abort before hot output."""

    report: dict[str, dict] = {}
    ok = True
    y_hs = thermal_admittance_halfspace(FREQUENCY_HZ, params)
    for bname, tr in branches.items():
        full = solve_point(params, tr, theta=0.0, model="full", cpd=CPD_MAIN)
        nograd = solve_point(params, tr, theta=0.0, model="nograd", cpd=CPD_MAIN)
        half = solve_point(params, tr, theta=0.0, model="full", cpd=CPD_MAIN,
                           T_w_hat=0.5 + 0.0j)
        anchor_rel = abs(full.Y_corrected - y_hs) / abs(y_hs)
        lin_rel = abs(half.Y_raw - full.Y_raw) / abs(full.Y_raw)
        degen_exact = full.Y_raw == nograd.Y_raw
        base_dev = full.base.mass_int_rel_dev
        rows = {
            "V1_degeneracy_full_equals_nograd_exact": bool(degen_exact),
            "V1_anchor_corrected_vs_halfspace_rel": float(anchor_rel),
            "V3_bc_residual_abs": float(full.bc_residual_abs),
            "V4_mass_integral_rel": float(base_dev),
            "V5_linearity_rel": float(lin_rel),
            "Y_raw_cold": _cplx(full.Y_raw),
            "Y_corrected_cold": _cplx(full.Y_corrected),
        }
        rows["pass"] = bool(
            degen_exact
            and anchor_rel <= LINE_ANCHOR_REL
            and full.bc_residual_abs <= LINE_BC_ABS
            and base_dev <= LINE_BASE_REL
            and lin_rel <= LINE_LINEARITY_REL
        )
        ok = ok and rows["pass"]
        report[bname] = rows
        print(f"[cold V] {bname}: degen_exact={degen_exact} "
              f"anchor={anchor_rel:.2e} bc={full.bc_residual_abs:.1e} "
              f"mass={base_dev:.1e} lin={lin_rel:.1e} "
              f"-> {'PASS' if rows['pass'] else 'FAIL'}", flush=True)
    return report, ok


def classify(branch_rows: dict, lbm_tan: dict) -> dict:
    """Plan §9 decision tree on the main points with the U_SIG guard."""

    def sig_sign(vals):
        if all(v > +U_SIG_PP for v in vals):
            return "pos"
        if all(v < -U_SIG_PP for v in vals):
            return "neg"
        return "mixed"

    d_full = [branch_rows[th]["full"]["d_op_pct"] for th in THETA_MAIN]
    d_nog = [branch_rows[th]["nograd"]["d_op_pct"] for th in THETA_MAIN]
    s_full, s_nog = sig_sign(d_full), sig_sign(d_nog)
    if s_full == "pos":
        case = "AD" if s_nog == "pos" else "A"
    elif s_full == "neg":
        case = "C" if s_nog == "pos" else ("B" if s_nog == "neg" else "B")
        if s_nog == "mixed":
            case = "B_NOGRAD_MIXED"
    else:
        case = "INCONCLUSIVE"
    ratios = [d / lbm_tan[th] for d, th in zip(d_full, THETA_MAIN)]
    same_order = all(1.0 / 3.0 <= r <= 3.0 for r in ratios)
    return {
        "d_op_full_main_pp": d_full,
        "d_op_nograd_main_pp": d_nog,
        "sign_full": s_full,
        "sign_nograd": s_nog,
        "case": case,
        "same_order_as_lbm_tangent": bool(same_order),
        "full_over_lbm_ratio": [float(r) for r in ratios],
        "grad_coupling_delta_pp": [
            float(a - b) for a, b in zip(d_full, d_nog)
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="NSF hot-base tangent arbitration")
    ap.add_argument("--output-root", default=None)
    ap.add_argument("--skip-time-domain", action="store_true",
                    help="smoke mode: BVP matrix only (V6 marked SKIPPED)")
    args = ap.parse_args()

    params = default_params()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = (Path(args.output_root) if args.output_root
                else REPO_ROOT / "results" / "phase5" / "nsf_arbitration")
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    branches = {
        "route_b_frozen_const": lbm_equivalent_transport(params),
        "lbm_equivalent_g0": g0_measured_transport(params),
        "physical_air": physical_air_transport(params),
    }
    print(f"[{UNIT}] run {run_id} instrument={INSTRUMENT_ID} "
          f"plan={PLAN_DOC}", flush=True)
    print(f"[{UNIT}] frozen lines: anchor<={LINE_ANCHOR_REL} "
          f"grid<={LINE_GRID_PP}pp bc<={LINE_BC_ABS} base<={LINE_BASE_REL} "
          f"lin<={LINE_LINEARITY_REL} xinst<={LINE_XINST_PP}pp "
          f"U_sig={U_SIG_PP}pp  (judgement frozen BEFORE hot numbers)",
          flush=True)

    # ---- stage 1: cold validations (fail-loud, before any hot number) ----
    cold_report, cold_ok = run_cold_validations(params, branches)
    if not cold_ok:
        summary = {"unit": UNIT, "run_id": run_id, "verdict": "FAILED",
                   "failed_stage": "cold_validations",
                   "cold_validations": cold_report}
        (out_dir / "summary.json").write_text(
            json.dumps(summary, indent=1), encoding="utf-8")
        print(f"[{UNIT}] COLD VALIDATION FAILED — aborting before hot matrix",
              flush=True)
        return 1

    # ---- stage 2: hot matrix + grid ladder ----
    results: dict[str, dict] = {}
    ladder_report: dict[str, dict] = {}
    grid_ok = True
    for bname, tr in branches.items():
        by_theta: dict[float, dict] = {}
        y_cold: dict[str, dict[float, complex]] = {"full": {}, "nograd": {}}
        for cpd in CPD_LADDER:
            for model in MODELS:
                y_cold[model][cpd] = solve_point(
                    params, tr, theta=0.0, model=model, cpd=cpd).Y_raw
        for theta in THETA_SET:
            row: dict[str, dict] = {}
            for model in MODELS:
                per_grid = {}
                resp_main = None
                for cpd in CPD_LADDER:
                    resp = solve_point(params, tr, theta=theta, model=model,
                                       cpd=cpd)
                    per_grid[cpd] = {
                        "Y_raw": _cplx(resp.Y_raw),
                        "d_op_pct": _dop(resp.Y_raw, y_cold[model][cpd])[
                            "d_op_pct"],
                    }
                    if cpd == CPD_MAIN:
                        resp_main = resp
                d96 = per_grid[96.0]["d_op_pct"]
                d48 = per_grid[48.0]["d_op_pct"]
                grid_dev = abs(d96 - d48)
                grid_ok = grid_ok and (grid_dev <= LINE_GRID_PP)
                dop = _dop(resp_main.Y_raw, y_cold[model][CPD_MAIN])
                row[model] = {
                    **dop,
                    "Y_raw": _cplx(resp_main.Y_raw),
                    "Y_corrected": _cplx(resp_main.Y_corrected),
                    "p_bar_over_p0": resp_main.base.p_bar / params.p0,
                    "audits": {
                        "bc_residual_abs": resp_main.bc_residual_abs,
                        "solve_residual_rel": resp_main.solve_residual_rel,
                        "mass_neutrality_rel": resp_main.mass_neutrality_rel,
                        "energy_integral_rel_dev":
                            resp_main.energy_integral_rel_dev,
                        "V2_grid_dev_pp": grid_dev,
                        "readout_stencil3_shift_rel": abs(
                            resp_main.q_wall_hat_stencil3
                            - resp_main.q_wall_hat
                        ) / abs(resp_main.q_wall_hat),
                    },
                    "ladder": {f"{c:g}": per_grid[c] for c in CPD_LADDER},
                }
            by_theta[theta] = row
            print(f"[{bname}] Theta={theta:g}: "
                  f"full d_OP={row['full']['d_op_pct']:+.4f}pp"
                  f"@{row['full']['phase_deg']:+.3f}deg  "
                  f"nograd d_OP={row['nograd']['d_op_pct']:+.4f}pp"
                  f"@{row['nograd']['phase_deg']:+.3f}deg  "
                  f"(V2 dev {row['full']['audits']['V2_grid_dev_pp']:.5f}pp)",
                  flush=True)
        results[bname] = by_theta
        ladder_report[bname] = {"grid_line_pass": grid_ok}

    # ---- stage 3: V6 cross-instrument checks ----
    xinst: dict[str, dict] = {}
    xinst_ok = True
    if args.skip_time_domain:
        xinst["status"] = "SKIPPED (smoke mode)"
    else:
        # fresh time-domain runs for the const branch (no archived series)
        td_rows: dict[float, dict] = {}
        for theta in (0.0,) + THETA_MAIN:
            td_rows[theta] = time_domain_admittance(
                params, branches["route_b_frozen_const"], theta_dc=theta)
            print(f"[V6 td-const] Theta={theta:g} "
                  f"|Y_raw|={abs(td_rows[theta]['Y_raw']):.4f} "
                  f"mass={td_rows[theta]['mass_drift_rel']:.1e}", flush=True)
        rows = {}
        for theta in THETA_MAIN:
            d_td = (abs(td_rows[theta]["Y_raw"] / td_rows[0.0]["Y_raw"])
                    - 1.0) * 100.0
            d_bvp = results["route_b_frozen_const"][theta]["full"]["d_op_pct"]
            dev = abs(d_bvp - d_td)
            rows[f"{theta:g}"] = {
                "d_op_bvp_pp": d_bvp, "d_op_timedomain_pp": d_td,
                "dev_pp": dev, "pass": bool(dev <= LINE_XINST_PP),
            }
            xinst_ok = xinst_ok and rows[f"{theta:g}"]["pass"]
            print(f"[V6 const] Theta={theta:g}: BVP {d_bvp:+.4f}pp vs "
                  f"time-domain {d_td:+.4f}pp (dev {dev:.4f}pp) "
                  f"-> {'PASS' if rows[f'{theta:g}']['pass'] else 'FAIL'}",
                  flush=True)
        xinst["route_b_frozen_const_fresh_td"] = rows
        # archived DC-arm authoritative raw series for g0/physical
        for bname in ("lbm_equivalent_g0", "physical_air"):
            rows = {}
            for theta in THETA_MAIN:
                ref = DC_ARM_RAW[bname][theta]["d_op_pct"]
                d_bvp = results[bname][theta]["full"]["d_op_pct"]
                dev = abs(d_bvp - ref)
                rows[f"{theta:g}"] = {
                    "d_op_bvp_pp": d_bvp, "d_op_dcarm_raw_pp": ref,
                    "dev_pp": dev, "pass": bool(dev <= LINE_XINST_PP),
                }
                xinst_ok = xinst_ok and rows[f"{theta:g}"]["pass"]
                print(f"[V6 {bname}] Theta={theta:g}: BVP {d_bvp:+.4f}pp vs "
                      f"DC-arm raw {ref:+.4f}pp (dev {dev:.4f}pp) "
                      f"-> {'PASS' if rows[f'{theta:g}']['pass'] else 'FAIL'}",
                      flush=True)
            xinst[f"{bname}_vs_archived_dcarm"] = rows

    # ---- stage 4: plan §9 classification ----
    classification = {
        bname: classify(results[bname], LBM_TAN) for bname in branches
    }
    for bname, cls in classification.items():
        print(f"[classify] {bname}: case {cls['case']} "
              f"(full {cls['sign_full']}, nograd {cls['sign_nograd']}; "
              f"grad-coupling delta "
              f"{['%+.3f' % v for v in cls['grad_coupling_delta_pp']]} pp; "
              f"same-order-as-LBM={cls['same_order_as_lbm_tangent']})",
              flush=True)

    all_pass = cold_ok and grid_ok and (args.skip_time_domain or xinst_ok)
    verdict = "COMPLETED" if all_pass else "FAILED"

    summary = {
        "unit": UNIT,
        "run_id": run_id,
        "verdict": verdict,
        "plan_doc": PLAN_DOC,
        "instrument_id": INSTRUMENT_ID,
        "protocol": {
            "frequency_Hz": FREQUENCY_HZ,
            "height_over_delta": HEIGHT_OVER_DELTA,
            "theta_set": list(THETA_SET),
            "theta_main": list(THETA_MAIN),
            "cpd_main": CPD_MAIN,
            "cpd_ladder": list(CPD_LADDER),
            "models": list(MODELS),
            "readout": "Y_raw = q_hat_w/T_w_hat (plan §7; corrected archived)",
            "time_domain_protocol": {
                "eps": TD_EPS, "cells_per_delta": TD_CELLS_PER_DELTA,
                "cycles": TD_CYCLES, "settle": TD_SETTLE,
            },
            "frozen_lines": {
                "anchor_rel": LINE_ANCHOR_REL, "grid_pp": LINE_GRID_PP,
                "bc_abs": LINE_BC_ABS, "base_rel": LINE_BASE_REL,
                "linearity_rel": LINE_LINEARITY_REL,
                "xinst_pp": LINE_XINST_PP, "u_sig_pp": U_SIG_PP,
            },
        },
        "cold_validations": cold_report,
        "branches": {
            b: {f"{th:g}": results[b][th] for th in THETA_SET}
            for b in branches
        },
        "cross_instrument_V6": xinst,
        "classification": classification,
        "external_references": {
            "lbm_production_a2a": {f"{k:g}": v for k, v in
                                   LBM_PRODUCTION.items()},
            "lbm_tan_tangent_pct": {f"{k:g}": v for k, v in LBM_TAN.items()},
            "qs0_pct": {f"{k:g}": v for k, v in QS0.items()},
            "qs1_pct": {f"{k:g}": v for k, v in QS1.items()},
            "dc_arm_raw": {b: {f"{k:g}": v for k, v in d.items()}
                           for b, d in DC_ARM_RAW.items()},
            "provenance": "Phase5_STATUS.md §6.1; oned_dc_arm run "
                          "20260803T083909Z summary.json (raw D_OP)",
        },
        "machine": {
            "node": platform.node(),
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "git_commit": _git_commit(),
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1),
                                          encoding="utf-8")
    print(f"[{UNIT}] verdict={verdict}  outputs -> {out_dir}", flush=True)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
