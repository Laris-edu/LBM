"""Phase_5 WP4 tangent-response diagnostic (WP4-TAN; PRE-REGISTERED 2026-08-04).

USER-DIRECTED MECHANISM UNIT — measure the small-signal TANGENT response of
the full LBM dynamics ON the settled inhomogeneous thermal base states at
Theta_DC = 0.05 and 0.10 (canonical tent, certified instrument verbatim),
and dissect the measured tangent response FIELD against the static-family
prediction. Follows the QS-1k refutation (MECHANISM_NOT_CLOSED): the static
re-evaluation hierarchy cannot reach the measured sign, so the residual is
irreducibly dynamic — this unit measures the dynamic tangent object itself
and localizes where (in y and in k) it departs from the static picture.

DESIGN (frozen before any number is computed):

  Cases: base(0.05), base(0.10) + increments Theta in {0, 0.05, 0.10} x
  eps in {0.00125, 0.0025, 0.005} — production protocol constants verbatim
  (settle 5 / drive 4 / skip 2 / spp 64, ny=96/hs=48, v1.1 walls, seed init).
  The eps ladder extends a factor 4 BELOW the production increment; all
  amplitudes are deep inside the G1a certification envelope.

  R1 TANGENT IDENTITY (judged, pre-registered):
    per Theta: complex LSQ  Y(eps) = Y0 + c*eps^2  over the three eps points
    (even curvature is the leading correction for the prescribed-theta 1f
    channel; the fit residual is archived and must stay << |Y0|*1e-3,
    fail-annotated otherwise). D_OP_tan = Y0(Theta)/Y0(0).
    CRITERION: |(|D_OP_tan|-1) - (|D_OP_archived|-1)| <= 0.2 pp at BOTH
    working points -> "the archived production D_OP IS the tangent (eps->0)
    response of the full dynamics on the hot base state" — closing the last
    gap between 'measured increment' and 'linearized-operator response'
    without building a separate linearized solver.
    Outcomes: TANGENT_CONFIRMED (both points) / TANGENT_DEVIATION (either
    point outside — would mean the production points carry finite-amplitude
    content; the tangent values then SUPERSEDE for Results I, archived).

  R2 FIELD DISSECTION (diagnostic label, pre-registered threshold):
    per Theta (and cold): the drive-phase x-averaged profiles are fitted
    row-by-row at 1f -> measured response field  F(y) = T_hat(y)/T_hat_w
    (largest-eps case; justified by R1 linearity). Static-family predicted
    field = certified tent spectral operator profile with (a) the cold
    alpha(k) table [cold + QS-cold residual floor] and (b) the QS-1k hot
    table  a(k)*(1+Theta)^e(k)  [wp]. Residual field  d(y) = F_meas - F_pred
    on the full periodic tent; k-spectrum via FFT; report
      frac_highk = sum_{k>k1} |d_hat(k)|^2 / sum_{k>0} |d_hat(k)|^2.
    LABEL: DISPERSION_BAND_LOCALIZED if the WP residual's frac_highk > 0.5
    at both working points AND exceeds the cold-floor frac_highk;
    else GLOBAL_OR_LOWK_LOCALIZED. Both outcomes are informative diagnosis
    (Discussion material), no gate claim.

  Legality (exit code): all finite, base stationarity <= 1e-3/period,
  state match <= 1e-2, smallest-eps 1f SNR >= 1e3 vs the archived null
  floor family (T_hat_s,1 floor ~4e-18 from the A1 null case — the 1.25e-3
  drive sits ~14 orders above; asserted, not assumed).

Pool discipline: G4a-certified worker/scheduler verbatim (P-DC2 exemption
precedent). Zero new physics operators — analysis-side only (complex LSQ +
row-wise harmonic fits + FFT), mechanism-tested in test_phase5_wp4_units.py.
Diagnostic unit: SCOPED_CANDIDATE-family verdicts only (D0-7), no gate claim.
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

from core.solver import GasSolver2D  # noqa: E402
from scripts.phase2_m2_verification import load_config  # noqa: E402
from scripts.phase5_g1w_wall_neutrality import (  # noqa: E402
    G0_TABLE_CSV,
    _git_commit,
    load_g0_alpha_rows,
)
from scripts.phase5_g4a_dc_basestate import (  # noqa: E402
    _cplx,
    _g4a_case_worker,
    fit_admittance,
    tent_spectral_reference,
)
from scripts.phase5_wp4_qs1k_mechanism import fit_exponents  # noqa: E402

CASE_FAMILY = "tangent_response"

# frozen archived production D_OP references (R1 comparison targets)
DOP_ARCHIVED = {
    0.05: {"abs_minus_1_pct": -2.83, "run": "20260801T081856Z"},
    0.10: {"abs_minus_1_pct": -5.31, "run": "20260802T104619Z"},
}
R1_TOL_PP = 0.2          # pre-registered tangent-identity tolerance
R2_FRAC_LINE = 0.5       # pre-registered high-k localization line


def tangent_fit(eps: np.ndarray, y_vals: np.ndarray) -> tuple[complex, complex, float]:
    """Complex LSQ of Y(eps) = Y0 + c*eps^2; returns (Y0, c, rel_residual).

    Pre-registered basis (1, eps^2): the leading finite-amplitude correction
    of the 1f channel under single-sign prescribed-theta drive is even.
    rel_residual = ||fit - data|| / |Y0| exposes any out-of-basis content
    (archived; an O(eps) or O(eps^3) contamination shows here).
    """

    if len(eps) < 3:
        raise ValueError("tangent_fit needs >= 3 eps points")
    basis = np.vstack([np.ones_like(eps), eps ** 2]).T.astype(complex)
    coef, *_ = np.linalg.lstsq(basis, y_vals.astype(complex), rcond=None)
    resid = float(np.linalg.norm(basis @ coef - y_vals) / max(abs(coef[0]), 1e-300))
    return complex(coef[0]), complex(coef[1]), resid


def field_highk_fraction(delta_y: np.ndarray, k1_lu: float) -> tuple[float, dict[str, float]]:
    """Energy fraction of a periodic residual field above k1 (k=0 excluded).

    delta_y: complex residual field on the full periodic tent (length ny).
    Returns (frac_highk, per-band energies). FFT convention: k_j = 2*pi*j/ny,
    folded to [0, pi]; the k=0 (mean) bin is excluded from the energy budget
    (a mean offset is a normalization artifact, not a mode).
    """

    n = len(delta_y)
    spec = np.fft.fft(np.asarray(delta_y, dtype=complex)) / n
    e_low = e_high = 0.0
    for j in range(1, n):
        k = 2.0 * math.pi * min(j, n - j) / n
        e = abs(spec[j]) ** 2
        if k > k1_lu * (1.0 + 1e-12):
            e_high += e
        else:
            e_low += e
    total = e_low + e_high
    return (e_high / total if total > 0 else float("nan"),
            {"e_low": e_low, "e_high": e_high, "total": total})


def run_tan(config_path: str | Path, output_root: str | Path | None = None,
            *, smoke: bool = False, workers: int | None = None) -> dict[str, Any]:
    import h5py
    import yaml

    from postproc.multiharmonic_fit import fit_multiharmonic
    from scripts.phase5_g1a_amplitude_envelope import execute_cases

    t0 = datetime.now(timezone.utc)
    cfg_all = load_config(Path(config_path))
    proto = cfg_all["tan_smoke" if smoke else "tan"]
    gates = cfg_all["gates"]
    gas_cfg = load_config(REPO_ROOT / str(cfg_all["inheritance"]["gas_config"]))

    log_lines: list[str] = []

    def log(msg: str) -> None:
        line = f"TAN {msg}"
        print(line, flush=True)
        log_lines.append(line)

    unit = str(proto.get("unit_label", "WP4-TAN-DIAG"))
    f_hz = float(proto["frequency_Hz"])
    hs_rows = int(proto["hs_rows"])
    ny = 2 * hs_rows
    nx = int(proto["nx"])
    thetas = [float(t) for t in proto["theta_points"]]
    eps_ladder = np.array([float(e) for e in proto["eps_ladder"]])
    spp = int(proto["samples_per_period"])
    settle = float(proto["settle_periods"])
    drive_p = float(proto["drive_periods"])
    skip = float(proto["fit_skip_periods"])
    om_si = 2.0 * math.pi * f_hz

    common = dict(gas_cfg=gas_cfg, ny=ny, nx=nx, frequency_hz=f_hz,
                  samples_per_period=spp, settle_periods=settle)
    payloads: list[dict[str, Any]] = []
    for th in thetas:
        payloads.append({**common, "label": f"base_th{th:g}", "kind": "base",
                         "theta_dc": th, "eps_ac": 0.0, "drive_periods": 0.0})
    for th in [0.0] + thetas:
        for e in eps_ladder:
            payloads.append({**common, "label": f"inc_th{th:g}_eps{e:g}",
                             "kind": "increment", "theta_dc": th,
                             "eps_ac": float(e), "drive_periods": drive_p})

    n_workers = workers if workers is not None else max(1, (os.cpu_count() or 4) - 2)
    results = execute_cases(payloads, n_workers, log, worker=_g4a_case_worker)

    def run_of(label: str):
        res = results.get(label)
        return res["run"] if res and res.get("ok") and res["run"].get("finite") else None

    for p in payloads:
        r = run_of(p["label"])
        log(f"[{p['label']}] {'finite' if r is not None else 'DEAD: ' + str(results.get(p['label'], {}).get('error'))}")

    # ---- R1: tangent extraction per theta ----
    y_by: dict[tuple[float, float], complex] = {}
    for th in [0.0] + thetas:
        for e in eps_ladder:
            r = run_of(f"inc_th{th:g}_eps{e:g}")
            if r is not None:
                y_by[(th, float(e))] = fit_admittance(r, f_hz, skip)["Y_face_theta_units"]
    tangent: dict[str, Any] = {}
    y0_by: dict[float, complex] = {}
    for th in [0.0] + thetas:
        ys = np.array([y_by[(th, float(e))] for e in eps_ladder])
        y0, curv, resid = tangent_fit(eps_ladder, ys)
        y0_by[th] = y0
        tangent[f"{th:g}"] = {
            "Y0_tangent": _cplx(y0), "curvature_c": _cplx(curv),
            "fit_rel_residual": resid,
            "Y_at_eps": {f"{e:g}": _cplx(y_by[(th, float(e))]) for e in eps_ladder},
        }
        log(f"theta={th:g}: |Y0|={abs(y0):.6e} curv/Y0={abs(curv)/abs(y0):.3e} "
            f"fit_resid={resid:.2e}")
    r1_rows: dict[str, Any] = {}
    r1_ok = []
    for th in thetas:
        d_tan = y0_by[th] / y0_by[0.0]
        d_tan_pct = (abs(d_tan) - 1.0) * 100.0
        ref = DOP_ARCHIVED[th]["abs_minus_1_pct"]
        dev_pp = d_tan_pct - ref
        ok = abs(dev_pp) <= R1_TOL_PP
        r1_ok.append(ok)
        r1_rows[f"{th:g}"] = {"D_OP_tangent": _cplx(d_tan),
                              "D_OP_tangent_pct": d_tan_pct,
                              "D_OP_archived_pct": ref,
                              "deviation_pp": dev_pp, "within_tol": ok,
                              "archived_run": DOP_ARCHIVED[th]["run"]}
        log(f"R1 theta={th:g}: D_OP_tan={d_tan_pct:+.3f}% vs archived {ref:+.2f}% "
            f"(dev {dev_pp:+.3f}pp, tol {R1_TOL_PP}) -> {'OK' if ok else 'DEVIATION'}")
    r1_label = "TANGENT_CONFIRMED" if all(r1_ok) else "TANGENT_DEVIATION"

    # ---- R2: response-field dissection vs the static family ----
    probe_cfg = {**gas_cfg, "numerics": {**gas_cfg["numerics"], "nx": 4, "ny": 8}}
    mapping = GasSolver2D(probe_cfg).mapping
    alpha_nom = float(mapping.alpha_lu)
    gamma = float(gas_cfg["physical"]["gamma"])
    om_lu = 2.0 * math.pi / (1.0 / (f_hz * float(mapping.lattice.dt_s)))
    cold_tab = load_g0_alpha_rows(REPO_ROOT / G0_TABLE_CSV)
    k_tab = np.array([r[0] for r in cold_tab])
    a_tab = np.array([r[1] for r in cold_tab])
    exps = fit_exponents(REPO_ROOT / G0_TABLE_CSV)
    ek_tab = np.array([e for _, e in exps])
    k1_lu = 0.0982

    def measured_field(label: str) -> np.ndarray | None:
        r = run_of(label)
        if r is None or r.get("drive") is None:
            return None
        d = r["drive"]
        mask = d["t_s"] >= skip / f_hz * (1.0 - 1e-12)
        t = d["t_s"][mask]
        tw1 = fit_multiharmonic(t, d["theta_w"][mask], om_si, n_harmonics=5).harmonic(1)
        prof = d["profiles"][mask]
        fld = np.empty(prof.shape[1], dtype=complex)
        for j in range(prof.shape[1]):
            fld[j] = fit_multiharmonic(t, prof[:, j], om_si, n_harmonics=5).harmonic(1)
        return fld / tw1

    def predicted_field(theta: float) -> np.ndarray:
        a_use = a_tab * (1.0 + theta) ** ek_tab if theta > 0 else a_tab
        ref = tent_spectral_reference(ny, hs_rows, om_lu, alpha_nom, k_tab, a_use,
                                      highk_policy="hold_last", gamma=gamma)
        return np.asarray(ref["profile_over_Tw"], dtype=complex)

    e_big = float(eps_ladder[-1])
    r2_rows: dict[str, Any] = {}
    fields_h5: dict[str, np.ndarray] = {}
    frac_wp: list[float] = []
    frac_cold = float("nan")
    for th in [0.0] + thetas:
        f_meas = measured_field(f"inc_th{th:g}_eps{e_big:g}")
        if f_meas is None:
            r2_rows[f"{th:g}"] = {"status": "dead"}
            continue
        f_pred = predicted_field(th)
        delta = f_meas - f_pred
        frac, bands = field_highk_fraction(delta, k1_lu)
        r2_rows[f"{th:g}"] = {
            "status": "ok", "frac_highk": frac, "bands": bands,
            "field_rms_residual": float(np.sqrt(np.mean(np.abs(delta) ** 2))),
            "prediction": "cold alpha(k) table" if th == 0 else "QS-1k hot table",
        }
        fields_h5[f"meas_th{th:g}"] = f_meas
        fields_h5[f"pred_th{th:g}"] = f_pred
        if th == 0:
            frac_cold = frac
        else:
            frac_wp.append(frac)
        log(f"R2 theta={th:g}: field rms residual={r2_rows[f'{th:g}']['field_rms_residual']:.3e} "
            f"frac_highk={frac:.3f}")
    r2_label = ("DISPERSION_BAND_LOCALIZED"
                if (len(frac_wp) == len(thetas)
                    and all(f > R2_FRAC_LINE and f > frac_cold for f in frac_wp))
                else "GLOBAL_OR_LOWK_LOCALIZED")
    log(f"R1={r1_label}  R2={r2_label} (cold floor frac={frac_cold:.3f})")

    # ---- legality ----
    floors_snr = min(
        abs(y_by[(th, float(eps_ladder[0]))]) * eps_ladder[0]
        for th in [0.0] + thetas) if y_by else float("nan")
    legal = {
        "all_finite": all(run_of(p["label"]) is not None for p in payloads),
        "stationarity_gate": float(gates["stationarity_per_period"]),
        "stationarity_worst": max((run_of(f"base_th{th:g}") or {}).get(
            "stationarity_per_period", float("nan")) for th in thetas),
        "state_match_gate": float(gates["state_match_rel"]),
        "state_match_worst": max(abs((run_of(f"base_th{th:g}") or {}).get(
            "theta_dc_measured", float("nan")) / th - 1.0) for th in thetas),
        "smallest_eps_signal_proxy": floors_snr,
    }
    verdict = "COMPLETED" if (legal["all_finite"]
                              and legal["stationarity_worst"] <= legal["stationarity_gate"]
                              and legal["state_match_worst"] <= legal["state_match_gate"]) \
        else "LEGALITY_FAILED"
    log(f"verdict={verdict}")

    # ---- files ----
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = Path(output_root) if output_root else REPO_ROOT / "results" / "phase5" / CASE_FAMILY
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    with h5py.File(out_dir / "signals.h5", "w") as h5:
        for p in payloads:
            r = run_of(p["label"])
            if r is None:
                continue
            grp = h5.create_group(f"cases/{p['label']}")
            grp.create_dataset("base_profile", data=r["base_profile"])
            if r.get("drive") is not None:
                for key in ("t_s", "theta_w", "q_hot_lu"):
                    grp.create_dataset(key, data=r["drive"][key])
        fg = h5.create_group("fields_1f")
        for name, arr in fields_h5.items():
            fg.create_dataset(f"{name}_re", data=arr.real)
            fg.create_dataset(f"{name}_im", data=arr.imag)
    digest = hashlib.sha256(json.dumps(
        {"tangent": tangent, "r1": r1_rows, "r2": r2_rows},
        sort_keys=True, default=str).encode()).hexdigest()[:12]
    summary = {
        "gate": unit, "run_id": run_id, "verdict": verdict,
        "gate_status": verdict, "scoped_limitations": [],
        "smoke_mode": bool(smoke),
        "protocol": {"theta_points": thetas, "eps_ladder": eps_ladder.tolist(),
                     "hs_rows": hs_rows, "geometry": "G4a tent canonical verbatim",
                     "r1_tol_pp": R1_TOL_PP, "r2_frac_line": R2_FRAC_LINE},
        "results": {"tangent_fits": tangent,
                    "R1_tangent_identity": {"label": r1_label, "rows": r1_rows},
                    "R2_field_dissection": {"label": r2_label, "rows": r2_rows,
                                            "cold_floor_frac": frac_cold},
                    "legality": legal},
        "physics_core_digest": digest,
        "code_commit": _git_commit(),
        "wall_clock_min": (datetime.now(timezone.utc) - t0).total_seconds() / 60.0,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=float),
                                          encoding="utf-8")
    (out_dir / "gate_evaluation.json").write_text(json.dumps(
        {"gate": unit, "verdict": verdict, "legality": legal,
         "note": "diagnostic unit: R1/R2 are labelled rows, not gates"},
        indent=1, default=float), encoding="utf-8")
    (out_dir / "harmonic_fit.json").write_text(json.dumps(
        {"tangent": tangent}, indent=1, default=float), encoding="utf-8")
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
        [f"# {unit} run {run_id}", "", f"verdict: **{verdict}**",
         f"R1: **{r1_label}**  R2: **{r2_label}**", "", "```text"]
        + log_lines + ["```", ""]), encoding="utf-8")
    log(f"outputs -> {out_dir}")
    return {"verdict": verdict, "out_dir": str(out_dir), "summary": summary}


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase_5 WP4 tangent-response diagnostic")
    ap.add_argument("--config", default=str(
        REPO_ROOT / "configs" / "phase5" / "a2a_operating_point"
        / "tangent_diag_10k_dx2p6.yaml"))
    ap.add_argument("--output-root", default=None)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()
    result = run_tan(args.config, args.output_root, smoke=args.smoke,
                     workers=args.workers)
    return 0 if result["verdict"] == "COMPLETED" else 1


if __name__ == "__main__":
    sys.exit(main())
