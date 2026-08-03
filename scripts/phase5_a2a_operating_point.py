"""Phase_5 WP3 P-DC2 runner: A2a operating-point production point (contract §15.2).

Theta_DC = 0.10 production point on the G4a-certified tent instrument
(pre-registered wp3_go_nogo_decision.md §3): geometry/protocol verbatim from
the G4a canonical rung (tent ny=96, prescribed theta_w_mean = theta0*1.10 ->
exact state matching, analytic seed + settle, P_mean archived measured).

Cases (all independent, one pool): base_dc010, increments eps={0.005, 0.02},
cold anchor rerun (in-run self-contained D_OP denominator), coupled point
(chi0=0.016, corrected accounting). Outputs (§15.2): D_OP(0.10) with the
G4a D_OP(0.05) = -2.83% trend/monotonicity comparison (the unit's main
purpose), QS-0/QS-1 residual trend (same pre-registered BVP family: G0 k1
temperature law on the measured T0(y)), chi_eff(0.10), DC-on-H2 (increment
2f ladder), coupled consistency. Domain-height sensitivity is NOT re-run
(G4a certified state-matched convergence at 0.05; pre-registered re-check
trigger: |D_OP(0.10)| > 10%).

Production runner: legality rows gate the exit code; physics numbers feed
wp3_go_nogo_decision.md. All instruments imported from the certified G4a
module (zero re-implementation).

WP4 (D5-6 SCOPED_GO): the same runner serves every A2a map point — theta_dc,
label_tag and unit_label are config-driven (defaults preserve the WP3 P-DC2
config behavior bit-for-bit). WP4 configs: a2a_wp4_dc002 (the §15.2 map
completion point) and a2a_wp4_dc0075 (pre-registered optional densification
point for the residual scaling law).
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
from scripts.phase2_m2_verification import load_config  # noqa: E402
from scripts.phase5_g4a_dc_basestate import (  # noqa: E402
    _cplx,
    _g4a_case_worker,
    _ratio_row,
    fit_admittance,
    tent_bvp_reference,
    tent_spectral_reference,
)

CASE_FAMILY = "a2a_operating_point"


def run_pdc2(config_path: str | Path, output_root: str | Path | None = None,
             *, smoke: bool = False, workers: int | None = None) -> dict[str, Any]:
    import h5py
    import yaml

    from postproc.multiharmonic_fit import fit_multiharmonic
    from scripts.phase5_g1a_amplitude_envelope import execute_cases
    from scripts.phase5_g1w_wall_neutrality import (
        G0_TABLE_CSV,
        _git_commit,
        load_g0_alpha_rows,
        measure_extension_rows,
    )

    t0 = datetime.now(timezone.utc)
    cfg_all = load_config(Path(config_path))
    proto = cfg_all["pdc2_smoke" if smoke else "pdc2"]
    gates = cfg_all["gates"]
    gas_cfg = load_config(REPO_ROOT / str(cfg_all["inheritance"]["gas_config"]))

    log_lines: list[str] = []

    def log(msg: str) -> None:
        line = f"PDC2 {msg}"
        print(line, flush=True)
        log_lines.append(line)

    f_hz = float(proto["frequency_Hz"])
    hs_rows = int(proto["hs_rows"])
    ny = 2 * hs_rows
    nx = int(proto["nx"])
    theta_dc = float(proto["theta_dc"])
    # orchestration-level naming only (physics untouched): defaults preserve
    # the WP3 P-DC2 config behavior bit-for-bit; WP4 configs override both.
    tag = str(proto.get("label_tag", "dc010"))
    unit = str(proto.get("unit_label", "WP3-PDC2"))
    eps_list = [float(e) for e in proto["eps_ac"]]
    spp = int(proto["samples_per_period"])
    settle = float(proto["settle_periods"])
    drive_p = float(proto["drive_periods"])
    fit_skip = float(proto["fit_skip_periods"])

    common = dict(gas_cfg=gas_cfg, ny=ny, nx=nx, frequency_hz=f_hz,
                  samples_per_period=spp, settle_periods=settle)
    payloads: list[dict[str, Any]] = [
        {**common, "label": f"base_{tag}", "kind": "base",
         "theta_dc": theta_dc, "eps_ac": 0.0, "drive_periods": 0.0},
        {**common, "label": "inc_cold", "kind": "increment",
         "theta_dc": 0.0, "eps_ac": min(eps_list), "drive_periods": drive_p},
    ]
    for eps in eps_list:
        payloads.append({**common, "label": f"inc_{tag}_eps{eps:g}",
                         "kind": "increment", "theta_dc": theta_dc,
                         "eps_ac": eps, "drive_periods": drive_p})

    n_workers = workers if workers is not None else max(1, (os.cpu_count() or 4) - 2)
    results = execute_cases(payloads, n_workers, log, worker=_g4a_case_worker)

    def run_of(label: str):
        res = results.get(label)
        return res["run"] if res and res.get("ok") and res["run"].get("finite") else None

    for label in sorted(results):
        r = run_of(label)
        if r is not None:
            log(f"[{label}] finite stat={r.get('stationarity_per_period', float('nan')):.2e} "
                f"ThetaDC={r.get('theta_dc_measured', float('nan')):.4f}")
        else:
            log(f"[{label}] DEAD: {results[label].get('error')}")

    y_by = {lb: fit_admittance(run_of(lb), f_hz, fit_skip)
            for lb in results if run_of(lb) is not None
            and run_of(lb).get("drive") is not None}

    # ---- coupled point at the working point (corrected accounting; sequential)
    base = run_of(f"base_{tag}")
    canon_inc = f"inc_{tag}_eps{max(eps_list):g}"
    coupled_row: dict[str, Any] = {"status": "not_run"}
    if proto.get("coupled_branch", True) and base is not None and canon_inc in y_by:
        run_c = run_of(canon_inc)
        om_step = 2.0 * math.pi / run_c["steps_per_period"]
        y_area = 2.0 * y_by[canon_inc]["Y_face_theta_units"] * run_c["rho0"] * run_c["cp_eff"]
        chi0 = float(proto["coupled_chi0"])
        c_a_lu = chi0 * 2.0 * abs(y_area) / om_step
        p_mean_area = base["q_hot_dc_lu"] / base["nx"]
        p1_over = float(proto["coupled_p1_over_pmean"])
        ts_exp = abs(p1_over * p_mean_area / (1j * om_step * c_a_lu + y_area))
        cpl_payload = {**common, "label": f"coupled_{tag}", "kind": "coupled",
                       "theta_dc": theta_dc, "eps_ac": 0.0,
                       "drive_periods": drive_p,
                       "coupled": {"c_areal_lu": c_a_lu, "p1_over_pmean": p1_over,
                                   "guard_factor": 5.0,
                                   "expected_ts_hat_lu": ts_exp}}
        cres = execute_cases([cpl_payload], 1, log, worker=_g4a_case_worker)
        cr = cres.get(f"coupled_{tag}")
        if cr and cr.get("ok") and cr["run"].get("drive") is not None and cr["run"]["finite"]:
            rr = cr["run"]
            if not rr["drive"]["coupled"]["unstable"]:
                om = 2.0 * math.pi * f_hz
                d = rr["drive"]
                mask = d["t_s"] >= fit_skip / f_hz
                ts1 = fit_multiharmonic(d["t_s"][mask], d["theta_w"][mask], om,
                                        n_harmonics=5).harmonic(1)
                pred = p1_over * p_mean_area / (1j * om_step * c_a_lu + y_area)
                coupled_row = {"status": "stable",
                               "Ts_hat_measured": _cplx(ts1),
                               "Ts_hat_ode_closed_form": _cplx(pred),
                               "consistency": _ratio_row(
                                   ts1 / pred, float(gates["coupled_amp_rel"]),
                                   float(gates["coupled_phase_deg"])),
                               "instrument": rr.get("coupled_instrument")}
                log(f"coupled@{theta_dc:g}: ratio={abs(ts1/pred):.4f}"
                    f"@{math.degrees(math.atan2((ts1/pred).imag, (ts1/pred).real)):+.2f}deg")
            else:
                coupled_row = {"status": "unstable",
                               "unstable_at_step": rr.get("coupled_unstable_at_step")}
        else:
            coupled_row = {"status": "dead",
                           "error": None if not cr else cr.get("error")}

    # ---- D_OP(0.10) + QS family + chi ----
    probe_cfg = copy.deepcopy(gas_cfg)
    probe_cfg["numerics"] = {**probe_cfg["numerics"], "nx": 4, "ny": 8}
    mapping = GasSolver2D(probe_cfg).mapping
    alpha_nom = float(mapping.alpha_lu)
    g0_rows = load_g0_alpha_rows(REPO_ROOT / G0_TABLE_CSV)
    ext_rows = measure_extension_rows(
        probe_cfg, [int(n) for n in proto.get("alpha_extension_ny", [12, 8, 6])],
        alpha_nom, log)
    all_rows = sorted(g0_rows + [(r["k_lu"], r["alpha_eff_lu"]) for r in ext_rows])
    k_tab = np.array([r[0] for r in all_rows])
    a_tab = np.array([r[1] for r in all_rows])

    qs: dict[str, Any] = {"status": "incomplete"}
    run_c = run_of(canon_inc)
    if run_c is not None and "inc_cold" in y_by and canon_inc in y_by:
        om_lu = 2.0 * math.pi / run_c["steps_per_period"]
        th0 = run_c["theta0"]
        gamma = float(gas_cfg["physical"]["gamma"])
        t_exp = float(proto["qs_alpha_temperature_exponent"])
        prof = run_c["base_profile"] / th0
        alpha_cold = np.full(ny, alpha_nom)
        bvp_cold = tent_bvp_reference(alpha_cold, hs_rows, om_lu, alpha_nom, gamma=gamma)
        bvp_qs0 = tent_bvp_reference(np.full(ny, alpha_nom * float(prof[0]) ** t_exp),
                                     hs_rows, om_lu, alpha_nom, gamma=gamma)
        bvp_qs1 = tent_bvp_reference(alpha_nom * prof ** t_exp, hs_rows, om_lu,
                                     alpha_nom, gamma=gamma)
        d_op = (y_by[canon_inc]["Y_face_theta_units"]
                / y_by["inc_cold"]["Y_face_theta_units"])
        d_qs0 = bvp_qs0["Y_over_Yhs"] / bvp_cold["Y_over_Yhs"]
        d_qs1 = bvp_qs1["Y_over_Yhs"] / bvp_cold["Y_over_Yhs"]
        y_hs_si = float(proto["y_hs_si_w_m2k"])
        y_hs_lu = complex(np.sqrt(1j * om_lu * alpha_nom))
        y_wp_si = abs(y_by[canon_inc]["Y_face_theta_units"] / y_hs_lu) * y_hs_si
        y_cold_si = abs(y_by["inc_cold"]["Y_face_theta_units"] / y_hs_lu) * y_hs_si
        om_si = 2.0 * math.pi * f_hz
        c_a_si = float(proto["chi_c_areal_si"])
        qs = {"status": "ok",
              "D_OP_measured": _cplx(d_op),
              "D_OP_QS0_pred": _cplx(d_qs0), "D_OP_QS1_pred": _cplx(d_qs1),
              "qs0_residual": float(abs(d_op - d_qs0)),
              "qs1_residual": float(abs(d_op - d_qs1)),
              "chi_0": float(om_si * c_a_si / (2.0 * y_cold_si)),
              "chi_eff": float(om_si * c_a_si / (2.0 * y_wp_si)),
              "g4a_dop_005_reference": {"abs_minus_1": -0.0283,
                                        "run": "20260801T081856Z"},
              "dop_reference_points": proto.get("dop_reference_points"),
              "trend_note": "monotonicity vs the archived Theta_DC reference "
                            "points is the unit's main output"}
        log(f"D_OP({theta_dc:g})={abs(d_op):.4f}@{math.degrees(math.atan2(d_op.imag, d_op.real)):+.2f} "
            f"QS0 {abs(d_qs0):.4f} QS1 {abs(d_qs1):.4f} chi_eff={qs['chi_eff']:.4f}")

    # DC-on-H2: increment 2f content per eps at 0.10 vs cold
    h2_rows = {lb: y["h2_q_rel"] for lb, y in y_by.items()}

    legal = {
        "all_finite": all(run_of(p["label"]) is not None for p in payloads),
        "stationarity_gate": float(gates["stationarity_per_period"]),
        "stationarity_base": (base or {}).get("stationarity_per_period", float("nan")),
        "state_match_dev": abs((base or {}).get("theta_dc_measured", float("nan"))
                               / theta_dc - 1.0) if base else float("nan"),
        "state_match_gate": float(gates["state_match_rel"]),
        "domain_recheck_trigger": bool(qs.get("status") == "ok"
                                       and abs(abs(complex(qs["D_OP_measured"]["re"],
                                                           qs["D_OP_measured"]["im"])) - 1.0)
                                       > float(gates["domain_recheck_dop_abs"])),
    }
    verdict = "COMPLETED" if (legal["all_finite"]
                              and legal["stationarity_base"] <= legal["stationarity_gate"]
                              and legal["state_match_dev"] <= legal["state_match_gate"]
                              and qs.get("status") == "ok") else "LEGALITY_FAILED"
    log(f"verdict={verdict} domain_recheck_trigger={legal['domain_recheck_trigger']}")

    # ---- files ----
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = Path(output_root) if output_root else REPO_ROOT / "results" / "phase5" / CASE_FAMILY
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    with h5py.File(out_dir / "signals.h5", "w") as h5:
        for p in payloads + ([] if coupled_row.get("status") != "stable" else []):
            r = run_of(p["label"])
            if r is None:
                continue
            grp = h5.create_group(f"cases/{p['label']}")
            grp.create_dataset("base_profile", data=r["base_profile"])
            if r.get("drive") is not None:
                for key in ("t_s", "theta_w", "q_hot_lu", "q_sink_lu"):
                    grp.create_dataset(key, data=r["drive"][key])
    digest = hashlib.sha256(json.dumps(
        {"qs": qs, "h2": h2_rows, "coupled": coupled_row},
        sort_keys=True, default=str).encode()).hexdigest()[:12]
    summary = {
        "gate": unit, "run_id": run_id, "verdict": verdict,
        "gate_status": verdict, "scoped_limitations": [],
        "smoke_mode": bool(smoke),
        "protocol": {"theta_dc": theta_dc, "eps_ac": eps_list, "hs_rows": hs_rows,
                     "geometry": "G4a tent canonical verbatim"},
        "results": {"qs_chi": qs, "h2_by_case": h2_rows,
                    "coupled": coupled_row,
                    "p_mean_lu_per_area": (base or {}).get("p_mean_lu_per_area"),
                    "legality": legal},
        "physics_core_digest": digest,
        "code_commit": _git_commit(),
        "wall_clock_min": (datetime.now(timezone.utc) - t0).total_seconds() / 60.0,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=float),
                                          encoding="utf-8")
    (out_dir / "gate_evaluation.json").write_text(json.dumps(
        {"gate": unit, "verdict": verdict, "legality": legal,
         "note": "production runner: physics rows are data, not gates"},
        indent=1, default=float), encoding="utf-8")
    (out_dir / "harmonic_fit.json").write_text(json.dumps(
        {lb: {"Y_face": _cplx(y["Y_face_theta_units"]), "h2_q_rel": y["h2_q_rel"]}
         for lb, y in y_by.items()}, indent=1, default=float), encoding="utf-8")
    (out_dir / "config_resolved.yaml").write_text(
        yaml.safe_dump(cfg_all, allow_unicode=True, sort_keys=False), encoding="utf-8")
    (out_dir / "provenance.json").write_text(json.dumps(
        {"run_id": run_id, "family": CASE_FAMILY, "argv": sys.argv,
         "machine": os.environ.get("COMPUTERNAME", "unknown"),
         "python": sys.version, "workers": n_workers,
         "started_utc": t0.isoformat(),
         "finished_utc": datetime.now(timezone.utc).isoformat()},
        indent=1), encoding="utf-8")
    (out_dir / "run_report.md").write_text("\n".join(
        [f"# {unit} run {run_id}", "", f"verdict: **{verdict}**", "", "```text"]
        + log_lines + ["```", ""]), encoding="utf-8")
    log(f"outputs -> {out_dir}")
    return {"verdict": verdict, "out_dir": str(out_dir), "summary": summary}


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase_5 WP3 P-DC2 runner")
    ap.add_argument("--config", default=str(
        REPO_ROOT / "configs" / "phase5" / "a2a_operating_point" / "pdc2_dc010_10k_dx2p6.yaml"))
    ap.add_argument("--output-root", default=None)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()
    result = run_pdc2(args.config, args.output_root, smoke=args.smoke,
                      workers=args.workers)
    return 0 if result["verdict"] == "COMPLETED" else 1


if __name__ == "__main__":
    sys.exit(main())