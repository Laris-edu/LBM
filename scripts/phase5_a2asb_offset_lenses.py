"""Offset-lens discriminator for the A2a-STRICT_B ensemble scan (D0-7).

Plan authority: docs/Phase_5/a2asb_offset_lenses_plan_v1.0.md (PLAN_v1.0,
frozen 2026-08-20).  Question: is the equal-mass Theta-scaled offset left by
the ensemble scan (R_ens(eq) = -1.653/-3.125 pp at Theta=0.05/0.10) the
DYNAMIC EXPRESSION of the lattice constitutive k = alpha(T) rho c_p (in
which case swapping to a real-gas transport law would remove essentially the
whole negative trend), or a genuine beyond-continuum dynamic residual?

Two legs, zero LBM compute:

  QS static lenses (L0/L1/L1b/L2)  — the strict-face Robin BVP family with
    four frozen bulk-constitutive choices, evaluated on the ensemble scan's
    MEASURED base states (inputs digest-pinned).
  NSF dynamic leg — the certified linearized hot-base NSF instrument with
    the lattice constitutive channel: base and dk/dT channel are EXACTLY the
    registered k~T^1.04 branch (p_bar/p0-rescaled anchors), the single new
    physics is the conservative flux -((k/p_bar) T_bar' p_hat)' (the EOS
    identity splits delta_k|lattice = 1.04 (k/T) T_hat + (k/p_bar) p_hat).
    The channel is OFF by default in the instrument; contract tests pin the
    off-path bit-identical and the cold column exactly unaffected.

Verdict (frozen, plan section 2): OFFSET_CONSTITUTIVE_DYNAMIC /
OFFSET_BEYOND_CONTINUUM / OFFSET_MIXED, with the static sub-verdict
(OFFSET_*_STATIC) always reported and NSF_LEG_NOT_COMPUTED as the audit
escape hatch.  This unit grants no qualification and does not touch the
judgement run's user-owned ruling; g0_scope semantics carry over.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.strict_b_half_domain import StrictBHalfDomain  # noqa: E402
from reference.constants import default_params  # noqa: E402
from reference.nonlinear_nsf_1d import (  # noqa: E402
    TransportModel,
    G0_MEASURED_K_EXPONENT,
    G0_MEASURED_MU_EXPONENT,
    g0_measured_transport,
)
from reference.nsf_hot_base_linear_1d import (  # noqa: E402
    solve_base_state,
    solve_linear_response,
)
from reference.strict_face_robin_qs import (  # noqa: E402
    map_strict_base_to_ref,
    robin_qs_matrix_bvp,
)
from scripts.phase2_m2_verification import load_config  # noqa: E402
from scripts.phase5_a2a_strict_b import G0_SCOPE, _wrap_deg  # noqa: E402
from scripts.phase5_wallfix_arbitration import NSF_G0_DOP_PCT  # noqa: E402

UNIT = "A2ASB-OFFSET-LENSES"
CASE_FAMILY = "a2asb_offset_lenses"

# ---------------------------------------------------------------------------
# FROZEN INPUT ANCHORS + JUDGEMENT LINES (plan section 2; before hot numbers)
# ---------------------------------------------------------------------------
SCAN_RUN_DIR = "results/mirror_from_B/a2asb_ensemble_scan/20260819T193831Z"
SCAN_SHA256 = {  # digest-pinned inputs (ensemble scan judgement run, B)
    "summary.json":
        "7786e41fbcf649d9bf861a17629d38760f2a9ee78d6ce6420d8205297a01b614",
    "signals.h5":
        "a7d52200d7872fd67ea01f7ef19b5b21cf1f67d9d319d8434ac76200151a76da",
}
D_EQ_MEASURED_PCT = {0.05: -0.20595875450180046, 0.10: -0.24073966354708487}
NSF_G0_ANCHORS_PCT = dict(NSF_G0_DOP_PCT)     # {0.05: +1.1817, 0.10: +2.3445}
ALPHA_EXPONENT = 2.04                          # G0 freeze doc section 1 (k1)
K_ISOBARIC_EXPONENT = G0_MEASURED_K_EXPONENT   # 1.04 (registered convention)

BAND_DYNAMIC_PP = 0.5     # NSF lattice leg within this of measured -> closed
BAND_FAR_PP = 1.0         # everything >= this away at both Theta -> beyond
BAND_STATIC_PP = 0.3      # static lens closes the eq offset
BAND_STATIC_SLOPE = 0.1   # ... and stays mass-flat (pp per % mass)
NSF_ANCHOR_TOL_PP = 0.05  # plain-branch recompute vs registered anchors
NSF_GRID_TOL_PP = 0.02    # cpd 48 -> 96 convergence row (arbitration line)
CPD_MAIN, CPD_HALF = 96.0, 48.0
HEIGHT_OVER_DELTA = 4.61
FREQUENCY_HZ = 1.0e4
N_REF_LADDER = (192, 384, 768)

LENSES = {
    # bulk_mode, bulk_beta, adv_beta   (face law frozen at wall's 1.04)
    "L0": ("powerlaw_local", 1.04, 1.04),   # registered QS-1
    "L1": ("lattice_local", ALPHA_EXPONENT, ALPHA_EXPONENT),
    "L1b": ("lattice_local", ALPHA_EXPONENT, K_ISOBARIC_EXPONENT),
    "L2": ("powerlaw_local", ALPHA_EXPONENT, ALPHA_EXPONENT),
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              cwd=REPO_ROOT, capture_output=True, text=True,
                              timeout=10, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def classify_offset(nsf_row: dict[str, Any] | None,
                    static_rows: dict[str, dict[float, float]],
                    d_eq_meas: dict[float, float],
                    static_slopes: dict[str, float]) -> dict[str, Any]:
    """Frozen plan-section-2 classification (pure function, unit-tested).

    nsf_row: {"d_latt_pct": {theta: value}} or None (escape hatch).
    static_rows: lens -> {theta: R_l(eq) [pp]}   (d_eq_meas - d_lens(eq)).
    static_slopes: lens -> dR_l/d(dm%) on the Theta=0.05 mass grid.
    """

    thetas = sorted(d_eq_meas)
    # static sub-verdict (always computed)
    static_label = "OFFSET_STATIC_MIXED"
    closing = [ln for ln in ("L1", "L2")
               if all(abs(static_rows[ln][t]) <= BAND_STATIC_PP for t in thetas)
               and abs(static_slopes.get(ln, float("inf"))) <= BAND_STATIC_SLOPE]
    if closing:
        static_label = "OFFSET_CONSTITUTIVE_STATIC"
    elif all(abs(static_rows[ln][t]) >= BAND_FAR_PP
             for ln in static_rows for t in thetas):
        static_label = "OFFSET_BEYOND_STATIC"

    if nsf_row is None:
        return {"label": f"NSF_LEG_NOT_COMPUTED/{static_label}",
                "static_label": static_label, "closing_static_lenses": closing}

    d_latt = nsf_row["d_latt_pct"]
    delta = {t: d_latt[t] - d_eq_meas[t] for t in thetas}
    if all(abs(delta[t]) <= BAND_DYNAMIC_PP and d_latt[t] < 0.0
           for t in thetas):
        label = "OFFSET_CONSTITUTIVE_DYNAMIC"
    elif (all(delta[t] >= BAND_FAR_PP for t in thetas)
          and static_label != "OFFSET_CONSTITUTIVE_STATIC"
          and all(abs(static_rows[ln][t]) >= BAND_FAR_PP
                  for ln in static_rows for t in thetas)):
        label = "OFFSET_BEYOND_CONTINUUM"
    else:
        label = "OFFSET_MIXED"
    return {"label": label, "static_label": static_label,
            "closing_static_lenses": closing,
            "nsf_minus_measured_pp": {f"{t:g}": delta[t] for t in thetas}}


# ---------------------------------------------------------------------------
# NSF lattice leg
# ---------------------------------------------------------------------------

def _lattice_transport(params, p_bar: float) -> TransportModel:
    """The lattice constitutive on the isobaric base: the registered
    k~T^1.04 / mu~T^-0.60 shapes with anchors rescaled by p_bar/p0
    (k = alpha(T) rho c_p with rho = p_bar/(R T))."""

    s = float(p_bar) / float(params.p0)
    return TransportModel(
        property_model_id="lattice_g0_k1_pbar_scaled_v1",
        kind="power_law", mu_ref=params.mu * s, k_ref=params.kg * s,
        T_ref=params.T0, mu_exponent=G0_MEASURED_MU_EXPONENT,
        k_exponent=G0_MEASURED_K_EXPONENT)


def _delta_t(params) -> float:
    alpha0 = params.kg / (params.rho0 * params.cp)
    return math.sqrt(2.0 * alpha0 / (2.0 * math.pi * FREQUENCY_HZ))


def _n_nodes(cpd: float) -> int:
    return int(round(HEIGHT_OVER_DELTA * cpd)) + 1


def nsf_point(params, theta: float, *, cpd: float, lattice: bool) -> dict[str, Any]:
    tr_g0 = g0_measured_transport(params)
    height = HEIGHT_OVER_DELTA * _delta_t(params)
    base0 = solve_base_state(params, tr_g0, theta_dc=theta, height_m=height,
                             n_nodes=_n_nodes(cpd))
    tr = _lattice_transport(params, base0.p_bar) if lattice else tr_g0
    base = (solve_base_state(params, tr, theta_dc=theta, height_m=height,
                             n_nodes=_n_nodes(cpd)) if lattice else base0)
    resp = solve_linear_response(base, params, tr,
                                 frequency_hz=FREQUENCY_HZ, model="full",
                                 lattice_pressure_channel=lattice)
    return {"Y": complex(resp.Y_raw),
            "audits": {"mass_neutrality_rel": resp.mass_neutrality_rel,
                       "energy_integral_rel_dev": resp.energy_integral_rel_dev,
                       "solve_residual_rel": resp.solve_residual_rel,
                       "bc_residual_abs": resp.bc_residual_abs},
            "p_bar": float(base.p_bar)}


def run_nsf_leg(log) -> dict[str, Any] | None:
    params = default_params()
    thetas = sorted(D_EQ_MEASURED_PCT)
    out: dict[str, Any] = {"d_latt_pct": {}, "d_g0_pct": {}, "rows": {}}
    for cpd in (CPD_HALF, CPD_MAIN):
        cold_g0 = nsf_point(params, 0.0, cpd=cpd, lattice=False)
        cold_lat = nsf_point(params, 0.0, cpd=cpd, lattice=True)
        # cold column: T_bar' = 0 -> the channel must be exactly inert
        cold_dev = abs(cold_lat["Y"] / cold_g0["Y"] - 1.0)
        if cold_dev > 1e-12:
            log(f"NSF leg audit FAIL: cold channel not inert ({cold_dev:.2e})")
            return None
        for th in thetas:
            g0 = nsf_point(params, th, cpd=cpd, lattice=False)
            lat = nsf_point(params, th, cpd=cpd, lattice=True)
            d_g0 = (abs(g0["Y"] / cold_g0["Y"]) - 1.0) * 100.0
            d_lat = (abs(lat["Y"] / cold_lat["Y"]) - 1.0) * 100.0
            # audit-degradation guard vs the certified plain branch
            for key, val in lat["audits"].items():
                ref = g0["audits"][key]
                if val > max(10.0 * ref, 1e-8):
                    log(f"NSF leg audit FAIL: {key}={val:.2e} vs plain "
                        f"{ref:.2e} (theta={th}, cpd={cpd})")
                    return None
            out["rows"][f"cpd{cpd:g}_th{th:g}"] = {
                "d_g0_pct": d_g0, "d_latt_pct": d_lat,
                "p_bar_over_p0": lat["p_bar"] / params.p0,
                "audits_lat": lat["audits"]}
            if cpd == CPD_MAIN:
                out["d_g0_pct"][th] = d_g0
                out["d_latt_pct"][th] = d_lat
    # plain-branch anchor + grid rows (fail-loud)
    for th in thetas:
        if abs(out["d_g0_pct"][th] - NSF_G0_ANCHORS_PCT[th]) > NSF_ANCHOR_TOL_PP:
            log(f"NSF leg FAIL: plain-branch anchor dev "
                f"{out['d_g0_pct'][th]:.4f} vs {NSF_G0_ANCHORS_PCT[th]:.4f}")
            return None
        grid_dev = abs(out["rows"][f"cpd{CPD_MAIN:g}_th{th:g}"]["d_latt_pct"]
                       - out["rows"][f"cpd{CPD_HALF:g}_th{th:g}"]["d_latt_pct"])
        out["rows"][f"grid_dev_th{th:g}_pp"] = grid_dev
        if grid_dev > NSF_GRID_TOL_PP:
            log(f"NSF leg FAIL: grid row {grid_dev:.4f} pp > {NSF_GRID_TOL_PP}")
            return None
        log(f"NSF th={th:g}: g0 {out['d_g0_pct'][th]:+.4f}% (anchor "
            f"{NSF_G0_ANCHORS_PCT[th]:+.4f}) lattice {out['d_latt_pct'][th]:+.4f}% "
            f"grid_dev {grid_dev:.4f} pp")
    return out


# ---------------------------------------------------------------------------
# QS lens leg
# ---------------------------------------------------------------------------

def run_qs_leg(log) -> dict[str, Any]:
    import h5py

    scan = REPO_ROOT / SCAN_RUN_DIR
    for fname, want in SCAN_SHA256.items():
        got = _sha256(scan / fname)
        if want != "REPLACED_AT_PREREG" and got != want:
            raise RuntimeError(f"scan input digest mismatch: {fname}")
    summary = json.loads((scan / "summary.json").read_text(encoding="utf-8"))
    rows_in = [r for r in summary["rows"] if "d_op_pct" in r]
    m0 = float(summary["mass_scale_m0_per_area"])

    gas_cfg = load_config(REPO_ROOT / "configs"
                          / "gas_air_10k_d2q37_levelc_dx2p6.yaml")
    hd = StrictBHalfDomain(gas_cfg, n_phys=12, nx=4)
    alpha_nom = float(hd.mapping.alpha_lu)
    rho_ref = float(hd.mapping.lattice.rho_ref_lu)
    theta0 = float(hd.mapping.theta_ref_lu)
    c_p = 0.5 * (int(hd.mapping.lattice.D) + int(hd.mapping.lattice.S)) + 1.0
    k0 = alpha_nom * rho_ref * c_p
    spp = int(round(1.0 / (FREQUENCY_HZ * float(hd.mapping.lattice.dt_s))))
    om_lu = 2.0 * math.pi / spp
    h_lu = 48.0

    h5 = h5py.File(scan / "signals.h5", "r")
    cold_bp = np.array(h5["settles/th0/base_profile"])
    cold_rp = np.array(h5["settles/th0/rho_profile"])

    def solve(bp, rp, mass, theta_w, lens, n_ref):
        mode, b_bulk, b_adv = LENSES[lens]
        tb, rb = map_strict_base_to_ref(bp, rp, n_ref, theta_w=theta_w,
                                        theta_amb=theta0, mass_per_area=mass,
                                        h_lu=h_lu)
        return robin_qs_matrix_bvp(
            n_ref=n_ref, h_lu=h_lu, omega_lu=om_lu, k0=k0, theta0=theta0,
            beta=1.04, c_p=c_p, theta_w=theta_w, theta_amb=theta0,
            theta_base=tb, rho_base=rb, bulk_mode=mode, bulk_beta=b_bulk,
            adv_beta=b_adv, rho_ref_lu=rho_ref)["Y"]

    n_fine, n_mid = N_REF_LADDER[-1], N_REF_LADDER[-2]
    cold_y = {(lens, n): solve(cold_bp, cold_rp, m0, theta0, lens, n)
              for lens in LENSES for n in (n_mid, n_fine)}
    points = []
    for r in sorted(rows_in, key=lambda x: (x["theta_dc"], x["dm_pct"])):
        th, m_rel, mass = r["theta_dc"], r["mass_rel"], r["mass_target"]
        lbl = (f"th{th:g}" if r["status"].startswith("wet_point")
               else f"th{th:g}_mr{m_rel:.6f}")
        bp = np.array(h5[f"settles/{lbl}/base_profile"])
        rp = np.array(h5[f"settles/{lbl}/rho_profile"])
        tw = theta0 * (1.0 + th)
        row = {"theta_dc": th, "mass_rel": m_rel, "dm_pct": r["dm_pct"],
               "d_op_pct": r["d_op_pct"], "lenses": {}}
        for lens in LENSES:
            d_fine = (abs(solve(bp, rp, mass, tw, lens, n_fine)
                          / cold_y[(lens, n_fine)]) - 1.0) * 100.0
            d_mid = (abs(solve(bp, rp, mass, tw, lens, n_mid)
                         / cold_y[(lens, n_mid)]) - 1.0) * 100.0
            row["lenses"][lens] = {"d_pct": d_fine,
                                   "u_ref_pp": abs(d_fine - d_mid),
                                   "r_pp": r["d_op_pct"] - d_fine}
        points.append(row)
        log(f"th={th:g} dm={r['dm_pct']:+.3f}%: " + " ".join(
            f"{ln}:R={row['lenses'][ln]['r_pp']:+.3f}" for ln in LENSES))
    h5.close()

    # L0 consistency vs the scan's own qs1 column (same solver family)
    l0_dev = max(abs(p["lenses"]["L0"]["d_pct"]
                     - next(rr["qs1_pct"] for rr in rows_in
                            if rr["theta_dc"] == p["theta_dc"]
                            and abs(rr["dm_pct"] - p["dm_pct"]) < 1e-9))
                 for p in points)
    log(f"L0 vs scan qs1 consistency: {l0_dev:.2e} pp")

    # eq offsets and mass slopes per lens
    static_rows: dict[str, dict[float, float]] = {ln: {} for ln in LENSES}
    static_slopes: dict[str, float] = {}
    for ln in LENSES:
        for th in sorted({p["theta_dc"] for p in points}):
            eq = min((p for p in points if p["theta_dc"] == th),
                     key=lambda p: abs(p["dm_pct"]))
            static_rows[ln][th] = eq["lenses"][ln]["r_pp"]
        grid05 = [p for p in points if p["theta_dc"] == 0.05]
        dm = np.array([p["dm_pct"] for p in grid05])
        rr = np.array([p["lenses"][ln]["r_pp"] for p in grid05])
        static_slopes[ln] = float(np.polyfit(dm, rr, 1)[0])
    return {"points": points, "static_rows": static_rows,
            "static_slopes": static_slopes, "l0_consistency_pp": l0_dev,
            "m0": m0}


def run_offset_lenses(output_root: str | Path | None = None, *,
                      skip_nsf: bool = False) -> dict[str, Any]:
    t0 = datetime.now(timezone.utc)
    log_lines: list[str] = []

    def log(msg: str) -> None:
        line = f"OFFLENS {msg}"
        print(line, flush=True)
        log_lines.append(line)

    commit = _git_commit()
    log(f"commit={commit} scan={SCAN_RUN_DIR}")
    qs = run_qs_leg(log)
    nsf = None if skip_nsf else run_nsf_leg(log)
    if nsf is None:
        log("NSF leg: NOT COMPUTED (hatch or --skip-nsf)")

    cls = classify_offset(nsf, qs["static_rows"], D_EQ_MEASURED_PCT,
                          qs["static_slopes"])
    log(f"classification={cls['label']} (static={cls['static_label']})")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = (Path(output_root) if output_root
               else REPO_ROOT / "results" / "phase5" / CASE_FAMILY) / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "offset_lenses.csv").open("w", newline="",
                                              encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["theta_dc", "mass_rel", "dm_pct", "d_op_pct", "lens",
                    "d_lens_pct", "r_pp", "u_ref_pp", "g0_scope"])
        for p in qs["points"]:
            for ln, v in p["lenses"].items():
                w.writerow([p["theta_dc"], p["mass_rel"], p["dm_pct"],
                            p["d_op_pct"], ln, v["d_pct"], v["r_pp"],
                            v["u_ref_pp"], G0_SCOPE])
    summary = {
        "gate": UNIT, "run_id": run_id,
        "verdict": "COMPLETED",
        "classification": cls, "g0_scope": G0_SCOPE,
        "frozen_lines": {"band_dynamic_pp": BAND_DYNAMIC_PP,
                         "band_far_pp": BAND_FAR_PP,
                         "band_static_pp": BAND_STATIC_PP,
                         "band_static_slope": BAND_STATIC_SLOPE,
                         "nsf_anchor_tol_pp": NSF_ANCHOR_TOL_PP,
                         "nsf_grid_tol_pp": NSF_GRID_TOL_PP,
                         "d_eq_measured_pct": {f"{k:g}": v for k, v in
                                               D_EQ_MEASURED_PCT.items()},
                         "nsf_g0_anchors_pct": {f"{k:g}": v for k, v in
                                                NSF_G0_ANCHORS_PCT.items()},
                         "alpha_exponent": ALPHA_EXPONENT,
                         "lenses": {k: list(v) for k, v in LENSES.items()}},
        "inputs": {"scan_run": SCAN_RUN_DIR,
                   "sha256": {f: _sha256(REPO_ROOT / SCAN_RUN_DIR / f)
                              for f in SCAN_SHA256}},
        "qs_leg": {"static_rows": {ln: {f"{t:g}": v for t, v in d.items()}
                                   for ln, d in qs["static_rows"].items()},
                   "static_slopes": qs["static_slopes"],
                   "l0_consistency_pp": qs["l0_consistency_pp"],
                   "points": qs["points"]},
        "nsf_leg": nsf,
        "code_commit": commit,
        "wall_clock_min": (datetime.now(timezone.utc) - t0).total_seconds() / 60.0,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=1, default=float), encoding="utf-8")
    (out_dir / "provenance.json").write_text(json.dumps(
        {"run_id": run_id, "family": CASE_FAMILY, "argv": sys.argv,
         "machine": os.environ.get("COMPUTERNAME", "unknown"),
         "python": sys.version, "code_commit": commit,
         "started_utc": t0.isoformat(),
         "finished_utc": datetime.now(timezone.utc).isoformat()},
        indent=1), encoding="utf-8")
    (out_dir / "run_report.md").write_text("\n".join(
        [f"# {UNIT} run {run_id}", "",
         f"classification: **{cls['label']}**", "", "```text"]
        + log_lines + ["```", ""]), encoding="utf-8")
    log(f"outputs -> {out_dir}")
    return {"verdict": "COMPLETED", "classification": cls["label"],
            "out_dir": str(out_dir), "summary": summary}


def main() -> int:
    ap = argparse.ArgumentParser(description="A2a-STRICT_B offset lenses")
    ap.add_argument("--output-root", default=None)
    ap.add_argument("--skip-nsf", action="store_true")
    args = ap.parse_args()
    run_offset_lenses(args.output_root, skip_nsf=args.skip_nsf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
