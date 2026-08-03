"""Phase_5 WP4 A5 runner: chi_0 x eps_AC map (contract §15.4/§3.5; D5-6 SCOPED_GO).

Results III instrument: the coupled film-ODE transfer map G1(chi_0, eps_AC) =
T_hat_s,1 / P_hat_1 on the G4a-certified tent rig at the canonical working
point (Theta_DC=0.05), sweeping the film areal heat capacity C_A through
chi_0 = {0.01, 0.1, 0.3, 1, 3} x eps_AC = {0.01, 0.05} (0.10 truncated by the
G1a authorization boundary, §15.4). The coupled instrument is the G4a A.4
certified loop verbatim (cv repinning subtraction + semi-implicit vs measured
G_inst + per-step excursion guard) — run_tent's coupled path, zero
re-implementation; only the (C_A, P1) design per point is new.

DESIGN (pre-registered, non-negotiable §0.4 — no per-point tuning):

- chi_0 axis is COLD-referenced per the contract §15.4 table: C_A_lu =
  chi_0 * 2|Y_cold,area| / Omega_step with Y_cold measured in-run on the
  Theta_DC=0 increment anchor (the same cold anchor family as A2a chi_0;
  the archived SI C_A via the y_hs bridge reproduces the §15.4 table).
  NOTE the G4a/A2a coupled-row design value chi0=0.016 is WP-referenced
  (their C_A came from the working-point Y); the A5 axis follows the
  contract table instead — both references are archived per point
  (chi_eff = chi_0 * |Y_cold|/|Y_wp| is the WP-referenced value).
- P1 inversion targets the realized film amplitude: p1_over_pmean =
  eps_target * theta0 * |i Omega_step C_A + Y_wp,area| / P_mean,area
  through the certified closed form (the SAME formula family the G4a/A2a
  coupled rows validated at 1.0376/1.0363@~+1deg). |expected T_hat_s| =
  eps_target * theta0 exactly by construction; the measured/closed-form
  consistency ratio and its eps dependence are the map's physics output.
- Points with p1_over_pmean > 1 have SIGNED total power P(t): archived with
  total_power_signed=true. This is the D0-4 signed numerical-ablation
  caliber (A1 lineage) on the SINK-ANCHORED tent rig — the §3.3
  non-negativity clause binds base A2a points, not the A5 map; the G1b
  no-sink pathology family does not apply (sink anchor present).
- material_relevance per §3.5 comes from the pre-registered config table
  (supported | synthetic_regime_extension); large-C_A points are regime
  extensions, never CNT design points.
- Uniform coupled protocol (no per-chi tuning): drive 6 periods / fit skip 3
  covers the film AC pole up to chi=3 with >=2x margin (pole settle
  ~chi_eff/pi periods) on top of the standard ramp; box-relaxation settle
  follows the G4a canonical rung.

Pool discipline: reuses the G4a-certified worker/scheduler layer verbatim
(_g4a_case_worker + execute_cases) — the serial/parallel bitwise exemption is
pre-registered on the P-DC2 precedent (same worker family, orchestration
unchanged). Production runner: legality rows gate the exit code; the map
numbers are data (SCOPED_CANDIDATE-family verdicts only, D0-7).
"""

from __future__ import annotations

import argparse
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

from scripts.phase2_m2_verification import load_config  # noqa: E402
from scripts.phase5_g4a_dc_basestate import (  # noqa: E402
    _cplx,
    _g4a_case_worker,
    _ratio_row,
    fit_admittance,
)

CASE_FAMILY = "a5_chi_map"


def design_chi_point(*, chi0: float, eps_target: float, y_cold_area: complex,
                     y_wp_area: complex, p_mean_area: float, om_step: float,
                     th0: float) -> dict[str, Any]:
    """Design one coupled map point from the measured in-run anchors.

    Pure function (contract-tested): cold-referenced C_A (the §15.4 chi_0
    axis), certified-closed-form P1 inversion to the target realized film
    amplitude, WP-referenced chi_eff, and the signed-power flag. Raises on
    non-finite or non-positive anchors (fail-loud, no silent repair).
    """

    if not (chi0 > 0.0 and eps_target > 0.0 and p_mean_area > 0.0
            and om_step > 0.0 and th0 > 0.0):
        raise ValueError("design_chi_point: non-positive anchor")
    if not (np.isfinite(abs(y_cold_area)) and np.isfinite(abs(y_wp_area))
            and abs(y_cold_area) > 0.0 and abs(y_wp_area) > 0.0):
        raise ValueError("design_chi_point: bad admittance anchor")
    c_a_lu = chi0 * 2.0 * abs(y_cold_area) / om_step
    denom = 1j * om_step * c_a_lu + y_wp_area
    p1_over = eps_target * th0 * abs(denom) / p_mean_area
    return {
        "chi0": float(chi0),
        "eps_target": float(eps_target),
        "c_a_lu": float(c_a_lu),
        "p1_over_pmean": float(p1_over),
        "expected_ts_hat_lu": float(eps_target * th0),
        "g1_closed_form": 1.0 / denom,
        "chi_eff": float(chi0 * abs(y_cold_area) / abs(y_wp_area)),
        "total_power_signed": bool(p1_over > 1.0),
    }


def chi_case_label(chi0: float, eps_target: float) -> str:
    return f"chi{chi0:g}_eps{eps_target:g}"


def amplitude_residual_rows(point_rows: dict[str, dict[str, Any]],
                            chi_ladder: list[float],
                            eps_targets: list[float]) -> dict[str, Any]:
    """Per-chi coupled amplitude residual: consistency(eps_hi)/consistency(eps_lo).

    The coupled-loop analogue of D_OP: the eps dependence of the measured/
    closed-form ratio at fixed chi_0 (linear-instrument drift cancels in the
    ratio). Requires exactly the two pre-registered eps targets; chi points
    with a missing arm are reported as incomplete, never silently dropped.
    """

    lo, hi = min(eps_targets), max(eps_targets)
    rows: dict[str, Any] = {}
    for chi0 in chi_ladder:
        k_lo, k_hi = chi_case_label(chi0, lo), chi_case_label(chi0, hi)
        r_lo, r_hi = point_rows.get(k_lo), point_rows.get(k_hi)
        if not (r_lo and r_hi and r_lo.get("status") == "stable"
                and r_hi.get("status") == "stable"):
            rows[f"{chi0:g}"] = {"status": "incomplete"}
            continue
        c_lo = complex(r_lo["consistency_ratio"]["re"], r_lo["consistency_ratio"]["im"])
        c_hi = complex(r_hi["consistency_ratio"]["re"], r_hi["consistency_ratio"]["im"])
        rows[f"{chi0:g}"] = {"status": "ok", "D_chi": _cplx(c_hi / c_lo),
                             "eps_lo": lo, "eps_hi": hi}
    return rows


def run_a5(config_path: str | Path, output_root: str | Path | None = None,
           *, smoke: bool = False, workers: int | None = None) -> dict[str, Any]:
    import h5py
    import yaml

    from postproc.multiharmonic_fit import fit_multiharmonic
    from scripts.phase5_g1a_amplitude_envelope import execute_cases
    from scripts.phase5_g1w_wall_neutrality import _git_commit

    t0 = datetime.now(timezone.utc)
    cfg_all = load_config(Path(config_path))
    proto = cfg_all["a5_smoke" if smoke else "a5"]
    gates = cfg_all["gates"]
    gas_cfg = load_config(REPO_ROOT / str(cfg_all["inheritance"]["gas_config"]))

    log_lines: list[str] = []

    def log(msg: str) -> None:
        line = f"A5 {msg}"
        print(line, flush=True)
        log_lines.append(line)

    unit = str(proto.get("unit_label", "WP4-A5"))
    f_hz = float(proto["frequency_Hz"])
    hs_rows = int(proto["hs_rows"])
    ny = 2 * hs_rows
    nx = int(proto["nx"])
    theta_dc = float(proto["theta_dc"])
    eps_probe = float(proto["eps_probe"])
    chi_ladder = [float(c) for c in proto["chi_ladder"]]
    eps_targets = [float(e) for e in proto["eps_targets"]]
    spp = int(proto["samples_per_period"])
    settle = float(proto["settle_periods"])
    drive_probe = float(proto["drive_probe_periods"])
    skip_probe = float(proto["fit_skip_probe_periods"])
    drive_cpl = float(proto["drive_coupled_periods"])
    skip_cpl = float(proto["fit_skip_coupled_periods"])
    relevance = {str(k): str(v) for k, v in proto["material_relevance"].items()}
    for chi0 in chi_ladder:
        if f"{chi0:g}" not in relevance:
            raise KeyError(f"material_relevance missing for chi0={chi0:g} (§3.5)")

    common = dict(gas_cfg=gas_cfg, ny=ny, nx=nx, frequency_hz=f_hz,
                  samples_per_period=spp, settle_periods=settle)
    setup_payloads: list[dict[str, Any]] = [
        {**common, "label": "base_wp", "kind": "base",
         "theta_dc": theta_dc, "eps_ac": 0.0, "drive_periods": 0.0},
        {**common, "label": "inc_cold", "kind": "increment",
         "theta_dc": 0.0, "eps_ac": eps_probe, "drive_periods": drive_probe},
        {**common, "label": "inc_wp", "kind": "increment",
         "theta_dc": theta_dc, "eps_ac": eps_probe, "drive_periods": drive_probe},
    ]
    n_workers = workers if workers is not None else max(1, (os.cpu_count() or 4) - 2)
    results = execute_cases(setup_payloads, n_workers, log, worker=_g4a_case_worker)

    def run_of(label: str):
        res = results.get(label)
        return res["run"] if res and res.get("ok") and res["run"].get("finite") else None

    base = run_of("base_wp")
    r_cold, r_wp = run_of("inc_cold"), run_of("inc_wp")
    if base is None or r_cold is None or r_wp is None:
        raise RuntimeError(f"A5 setup wave dead: base={base is not None} "
                           f"cold={r_cold is not None} wp={r_wp is not None}")
    y_fit = {lb: fit_admittance(run_of(lb), f_hz, skip_probe)
             for lb in ("inc_cold", "inc_wp")}
    om_step = 2.0 * math.pi / r_wp["steps_per_period"]
    th0 = r_wp["theta0"]
    bridge = r_wp["rho0"] * r_wp["cp_eff"]
    y_cold_area = 2.0 * y_fit["inc_cold"]["Y_face_theta_units"] * bridge
    y_wp_area = 2.0 * y_fit["inc_wp"]["Y_face_theta_units"] * bridge
    p_mean_area = base["q_hot_dc_lu"] / base["nx"]
    om_si = 2.0 * math.pi * f_hz
    y_hs_si = float(proto["y_hs_si_w_m2k"])
    log(f"anchors: |Y_cold|={abs(y_cold_area):.4e} |Y_wp|={abs(y_wp_area):.4e} "
        f"P_mean={p_mean_area:.4e} ThetaDC={base['theta_dc_measured']:.4f}")

    # ---- design all map points from the measured anchors (pure function) ----
    designs: dict[str, dict[str, Any]] = {}
    cpl_payloads: list[dict[str, Any]] = []
    for chi0 in chi_ladder:
        for eps_t in eps_targets:
            d = design_chi_point(chi0=chi0, eps_target=eps_t,
                                 y_cold_area=y_cold_area, y_wp_area=y_wp_area,
                                 p_mean_area=p_mean_area, om_step=om_step,
                                 th0=th0)
            lb = chi_case_label(chi0, eps_t)
            designs[lb] = d
            cpl_payloads.append(
                {**common, "label": lb, "kind": "coupled",
                 "theta_dc": theta_dc, "eps_ac": 0.0,
                 "drive_periods": drive_cpl,
                 "coupled": {"c_areal_lu": d["c_a_lu"],
                             "p1_over_pmean": d["p1_over_pmean"],
                             "guard_factor": float(proto["guard_factor"]),
                             "expected_ts_hat_lu": d["expected_ts_hat_lu"]}})
            log(f"design {lb}: C_A_lu={d['c_a_lu']:.4e} "
                f"p1/pmean={d['p1_over_pmean']:.3f} signed={d['total_power_signed']}")

    cres = execute_cases(cpl_payloads, n_workers, log, worker=_g4a_case_worker)

    def cpl_run_of(label: str):
        res = cres.get(label)
        return res["run"] if res and res.get("ok") and res["run"].get("finite") else None

    # ---- per-point observables ----
    point_rows: dict[str, dict[str, Any]] = {}
    for p in cpl_payloads:
        lb = p["label"]
        d = designs[lb]
        rr = cpl_run_of(lb)
        if rr is None:
            point_rows[lb] = {"status": "dead",
                              "error": None if lb not in cres else cres[lb].get("error")}
            log(f"[{lb}] DEAD: {point_rows[lb]['error']}")
            continue
        if rr["drive"]["coupled"]["unstable"]:
            point_rows[lb] = {"status": "unstable",
                              "unstable_at_step": rr.get("coupled_unstable_at_step"),
                              "instrument": rr.get("coupled_instrument")}
            log(f"[{lb}] UNSTABLE at step {rr.get('coupled_unstable_at_step')}")
            continue
        dr = rr["drive"]
        mask = dr["t_s"] >= skip_cpl / f_hz * (1.0 - 1e-12)
        fit_ts = fit_multiharmonic(dr["t_s"][mask], dr["theta_w"][mask],
                                   om_si, n_harmonics=5)
        ts1 = fit_ts.harmonic(1)
        h2_ts = abs(fit_ts.harmonic(2)) / max(abs(ts1), 1e-300)
        y_row = fit_admittance(rr, f_hz, skip_cpl)   # gas Y under the coupled drive
        p_mean_case = dr["coupled"]["P_mean_lu"]
        p1_hat = d["p1_over_pmean"] * p_mean_case
        g1_meas = ts1 / p1_hat
        pred = p1_hat * d["g1_closed_form"]
        eps_real = abs(ts1) / th0
        point_rows[lb] = {
            "status": "stable",
            "chi0": d["chi0"], "eps_target": d["eps_target"],
            "chi_eff": d["chi_eff"],
            "C_A_lu": d["c_a_lu"],
            "C_A_si_j_m2k": float(d["chi0"] * 2.0 * y_hs_si / om_si),
            "material_relevance": relevance[f"{d['chi0']:g}"],
            "p1_over_pmean": d["p1_over_pmean"],
            "total_power_signed": d["total_power_signed"],
            "G1_measured": _cplx(g1_meas),
            "G1_closed_form": _cplx(d["g1_closed_form"]),
            "consistency_ratio": _cplx(ts1 / pred),
            "consistency": _ratio_row(ts1 / pred,
                                      float(gates["coupled_amp_rel"]),
                                      float(gates["coupled_phase_deg"])),
            "eps_realized": float(eps_real),
            "H2_Ts": float(h2_ts),
            "H2_q": float(y_row["h2_q_rel"]),
            "Y_gas_under_drive": _cplx(2.0 * y_row["Y_face_theta_units"] * bridge),
            "p_mean_in_case_over_base": float(p_mean_case / p_mean_area),
            "instrument": rr.get("coupled_instrument"),
        }
        log(f"[{lb}] ratio={abs(ts1 / pred):.4f}"
            f"@{math.degrees(math.atan2((ts1 / pred).imag, (ts1 / pred).real)):+.2f}deg "
            f"eps_real={eps_real:.4f} H2_Ts={h2_ts:.2e}")

    resid = amplitude_residual_rows(point_rows, chi_ladder, eps_targets)
    for chi_key, row in resid.items():
        if row.get("status") == "ok":
            log(f"D_chi(chi0={chi_key}): {row['D_chi']['abs']:.4f}"
                f"@{row['D_chi']['phase_deg']:+.2f}deg")

    # ---- legality (production runner: map numbers are data, not gates) ----
    eps_band = [float(b) for b in proto["eps_realized_band"]]
    stable_rows = [r for r in point_rows.values() if r.get("status") == "stable"]
    legal = {
        "setup_all_finite": True,
        "stationarity_gate": float(gates["stationarity_per_period"]),
        "stationarity_base": base["stationarity_per_period"],
        "state_match_dev": abs(base["theta_dc_measured"] / theta_dc - 1.0),
        "state_match_gate": float(gates["state_match_rel"]),
        "all_points_stable": all(r.get("status") == "stable"
                                 for r in point_rows.values()),
        "n_stable": len(stable_rows), "n_points": len(point_rows),
        "eps_realized_band": eps_band,
        "eps_realized_band_ok": all(
            eps_band[0] <= r["eps_realized"] / r["eps_target"] <= eps_band[1]
            for r in stable_rows),
        "eps_realized_max_authorized": float(proto["eps_realized_max"]),
        "eps_realized_max_ok": all(
            r["eps_realized"] <= float(proto["eps_realized_max"])
            for r in stable_rows),
    }
    verdict = "COMPLETED" if (
        legal["all_points_stable"]
        and legal["stationarity_base"] <= legal["stationarity_gate"]
        and legal["state_match_dev"] <= legal["state_match_gate"]
        and legal["eps_realized_band_ok"] and legal["eps_realized_max_ok"]
    ) else "LEGALITY_FAILED"
    log(f"verdict={verdict} stable={legal['n_stable']}/{legal['n_points']}")

    # ---- files (seven-file contract) ----
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = Path(output_root) if output_root else REPO_ROOT / "results" / "phase5" / CASE_FAMILY
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    with h5py.File(out_dir / "signals.h5", "w") as h5:
        for lb in ("base_wp", "inc_cold", "inc_wp"):
            r = run_of(lb)
            if r is None:
                continue
            grp = h5.create_group(f"cases/{lb}")
            grp.create_dataset("base_profile", data=r["base_profile"])
            if r.get("drive") is not None:
                for key in ("t_s", "theta_w", "q_hot_lu", "q_sink_lu"):
                    grp.create_dataset(key, data=r["drive"][key])
        for p in cpl_payloads:
            r = cpl_run_of(p["label"])
            if r is None or r.get("drive") is None:
                continue
            grp = h5.create_group(f"cases/{p['label']}")
            grp.create_dataset("base_profile", data=r["base_profile"])
            for key in ("t_s", "theta_w", "q_hot_lu", "q_sink_lu"):
                grp.create_dataset(key, data=r["drive"][key])
    digest = hashlib.sha256(json.dumps(
        {"points": point_rows, "resid": resid}, sort_keys=True,
        default=str).encode()).hexdigest()[:12]
    summary = {
        "gate": unit, "run_id": run_id, "verdict": verdict,
        "gate_status": verdict, "scoped_limitations": [],
        "smoke_mode": bool(smoke),
        "protocol": {
            "theta_dc": theta_dc, "chi_ladder": chi_ladder,
            "eps_targets": eps_targets, "eps_probe": eps_probe,
            "hs_rows": hs_rows, "geometry": "G4a tent canonical verbatim",
            "chi_axis": "cold-referenced (contract §15.4 table); chi_eff "
                        "= WP-referenced archived per point",
            "drive": "coupled film-ODE loop (G4a A.4 certified accounting); "
                     "P1 inverted from the certified closed form to the "
                     "target realized film amplitude; signed total power "
                     "= D0-4 numerical-ablation caliber (archived per point)",
        },
        "results": {
            "anchors": {"Y_cold_area": _cplx(y_cold_area),
                        "Y_wp_area": _cplx(y_wp_area),
                        "p_mean_lu_per_area": p_mean_area,
                        "chi_eff_over_chi0": float(abs(y_cold_area) / abs(y_wp_area)),
                        "theta_dc_measured": base["theta_dc_measured"]},
            "map_points": point_rows,
            "amplitude_residual_D_chi": resid,
            "legality": legal,
        },
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
        {"points": {lb: {k: r[k] for k in
                         ("G1_measured", "consistency_ratio", "H2_Ts", "H2_q")
                         if k in r}
                    for lb, r in point_rows.items()},
         "anchors": {lb: _cplx(y["Y_face_theta_units"]) for lb, y in y_fit.items()}},
        indent=1, default=float), encoding="utf-8")
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
    ap = argparse.ArgumentParser(description="Phase_5 WP4 A5 chi-map runner")
    ap.add_argument("--config", default=str(
        REPO_ROOT / "configs" / "phase5" / "a5_chi_map" / "a5_wp4_10k_dx2p6.yaml"))
    ap.add_argument("--output-root", default=None)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()
    result = run_a5(args.config, args.output_root, smoke=args.smoke,
                    workers=args.workers)
    return 0 if result["verdict"] == "COMPLETED" else 1


if __name__ == "__main__":
    sys.exit(main())
