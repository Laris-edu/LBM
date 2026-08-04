"""Phase_5 WP4 QS-1k mechanism discriminator (PRE-REGISTERED 2026-08-04).

QUESTION — does a k-RESOLVED static re-evaluation, built ONLY from the
independently measured medium properties (the G0 alpha_eff(k, T_b) table,
270-360 K x six k-layers), reproduce the measured dynamic residual sign
(and magnitude band) of D_OP at all four A2a working points? This closes or
refutes the pre-registered mechanism suspect of the
DYNAMIC_NONLINEAR_RESIDUAL_IDENTIFIED finding (G4a/WP3/WP4): "the k-resolved
temperature dependence of alpha_eff beyond the k1 law".

OPERATIONALIZATION (frozen before any number is computed):

  e(k)        : per-k-layer log-log fit of alpha_eff_lu vs T_K over the four
                G0 backgrounds (isobaric path, y axis — the certified table
                convention, same row filter as load_g0_alpha_rows).
  D_beyond    = Y_spec[a_cold(k) * (1+Theta)^e(k)]
              / Y_spec[a_cold(k) * (1+Theta)^e(k1)]
                on the CERTIFIED tent spectral operator (tent_spectral_reference
                verbatim, production hold_last high-k policy, ny=96/hs=48
                canonical geometry) — isolates exactly the beyond-k1-law
                content; instrument constants cancel in the double ratio.
  D_QS1k      = D_beyond * D_QS1_archived  (the archived QS-1 already carries
                the y-resolved base-state + k1-law part; factorization error
                is bounded by the archived |QS1-QS0| ~ 0.05 pp).
  Uniform (1+Theta) elevation (wall value) is the primary temperature choice —
  the same scalar convention as the archived QS-0, justified by the archived
  QS0/QS1 proximity (the AC layer hugs the wall).

PRE-REGISTERED CRITERIA (three-state; judged on |.|-1 in percent):

  f(Theta) = [ (|D_QS1k|-1) - (|QS1|-1) ] / [ (|D_OP|-1) - (|QS1|-1) ]
             (fraction of the dynamic residual explained by the k-part)

  MECHANISM_CLOSED      sign of (|D_QS1k|-1) negative at ALL four Theta
                        AND f in [0.5, 1.5] at ALL four points
  MECHANISM_PARTIAL     sign negative at ALL four points, f outside the band
                        at one or more points
  MECHANISM_NOT_CLOSED  sign not reproduced at any point

INTERPRETATIONS (written in advance; none is a failure of the paper):
  CLOSED   -> the measured alpha_eff(k,T) dispersion law explains the residual;
              the "is the LBM right" question dissolves into the independently
              measured medium characterization. Static k1-law re-evaluation
              stays refuted; a k-resolved static law is the fix.
  PARTIAL  -> k-dispersion is a real, quantified component; a genuinely
              dynamic remainder exists beyond any static re-evaluation.
  NOT_CLOSED -> the residual is dynamic in origin even against the k-resolved
              static family — strengthens the core claim (static family fails
              structurally); mechanism remains open and is stated as such.

SENSITIVITY ROWS (archived, non-judging):
  S1 high-k exponent policy: primary = hold e(k3) above the measured k range
     (the operator's own hold_last); variant = relax to e(k1) by pi.
  S2 mean-elevation variant: (1+Theta/2) in place of (1+Theta) in D_beyond.
  IDENTITY check (fail-loud): e(k) == e(k1) everywhere must give
     D_beyond == 1 to machine precision.

Pure reference computation — zero new LBM runs; consumes only committed
M5_runs archives and the certified spectral operator. Diagnostic unit:
produces data + the pre-registered three-state label; no gate claim.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.solver import GasSolver2D  # noqa: E402
from scripts.phase2_m2_verification import load_config  # noqa: E402
from scripts.phase5_g1w_wall_neutrality import G0_TABLE_CSV, load_g0_alpha_rows  # noqa: E402
from scripts.phase5_g4a_dc_basestate import tent_spectral_reference  # noqa: E402

M5 = REPO_ROOT / "docs" / "Phase_5" / "M5_runs"
GAS_CFG = REPO_ROOT / "configs" / "gas_air_10k_d2q37_levelc_dx2p6.yaml"

# frozen archived working points (Theta_DC -> summary path)
POINTS = {
    0.02: "wp4_a2a_dc002_20260803T185241Z/summary.json",
    0.05: "g4a_20260801T081856Z/summary.json",
    0.075: "wp4_a2a_dc0075_20260803T185101Z/summary.json",
    0.10: "wp3_pdc2_20260802T104619Z/summary.json",
}
F_BAND = (0.5, 1.5)          # pre-registered magnitude band
NY, HS = 96, 48              # canonical tent geometry
F_HZ = 1.0e4


def fit_exponents(csv_path: Path) -> list[tuple[float, float]]:
    """Per-k temperature exponents e(k): log-log fit of alpha_eff_lu vs T_K.

    Same row convention as the certified table loader (isobaric, y axis,
    untagged rows); requires all four backgrounds per k layer (fail-loud).
    """

    by_k: dict[float, list[tuple[float, float]]] = {}
    with csv_path.open(encoding="utf-8") as fh:
        for rec in csv.DictReader(fh):
            if (rec["tag"] == "" and rec["background_path"] == "isobaric"
                    and rec["direction"] == "y"):
                by_k.setdefault(float(rec["k_lu"]), []).append(
                    (float(rec["T_K"]), float(rec["alpha_eff_lu"])))
    out: list[tuple[float, float]] = []
    for k, rows in sorted(by_k.items()):
        if len(rows) < 4:
            raise RuntimeError(f"k={k}: only {len(rows)} backgrounds")
        t = np.log([r[0] for r in rows])
        a = np.log([r[1] for r in rows])
        out.append((k, float(np.polyfit(t, a, 1)[0])))
    return out


def _c(d: dict) -> complex:
    return complex(d["re"], d["im"])


def main() -> int:
    # ---- anchors from the frozen stack (probe mapping; no LBM stepping) ----
    gas_cfg = load_config(GAS_CFG)
    gas_cfg["numerics"] = {**gas_cfg["numerics"], "nx": 4, "ny": 8}
    mapping = GasSolver2D(gas_cfg).mapping
    alpha_nom = float(mapping.alpha_lu)
    gamma = float(load_config(GAS_CFG)["physical"]["gamma"])
    steps_per_period = int(round(1.0 / (F_HZ * float(mapping.lattice.dt_s))))
    om_lu = 2.0 * math.pi / steps_per_period

    cold = load_g0_alpha_rows(REPO_ROOT / G0_TABLE_CSV)
    k_tab = np.array([r[0] for r in cold])
    a_tab = np.array([r[1] for r in cold])
    exps = fit_exponents(REPO_ROOT / G0_TABLE_CSV)
    ek_tab = np.array([e for _, e in exps])
    k_exp = np.array([k for k, _ in exps])
    if not np.allclose(k_exp, k_tab, rtol=1e-12):
        raise RuntimeError("exponent table and alpha table k-grids differ")
    e_k1 = float(ek_tab[int(np.argmin(np.abs(k_tab - 0.0982)))])
    print("e(k) table:", {f"{k:.4f}": round(e, 3) for k, e in exps})
    print(f"e(k1) = {e_k1:.3f}  alpha_nom = {alpha_nom:.5e}  om_lu = {om_lu:.5e}")

    def y_spec(a_vals: np.ndarray) -> complex:
        ref = tent_spectral_reference(NY, HS, om_lu, alpha_nom, k_tab, a_vals,
                                      highk_policy="hold_last", gamma=gamma)
        return complex(ref["Y_over_Yhs"])

    def d_beyond(theta: float, *, elev: float = 1.0, e_hi_k1: bool = False) -> complex:
        r = (1.0 + elev * theta)
        e_use = ek_tab.copy()
        a_hot = a_tab * r ** e_use
        a_ref = a_tab * r ** e_k1
        if e_hi_k1:
            k_ext = np.append(k_tab, math.pi)
            a_hot = np.append(a_hot, a_tab[-1] * r ** e_k1)
            a_ref = np.append(a_ref, a_tab[-1] * r ** e_k1)
            y_h = tent_spectral_reference(NY, HS, om_lu, alpha_nom, k_ext, a_hot,
                                          highk_policy="hold_last", gamma=gamma)
            y_r = tent_spectral_reference(NY, HS, om_lu, alpha_nom, k_ext, a_ref,
                                          highk_policy="hold_last", gamma=gamma)
            return complex(y_h["Y_over_Yhs"]) / complex(y_r["Y_over_Yhs"])
        return y_spec(a_hot) / y_spec(a_ref)

    # IDENTITY check (pre-registered fail-loud)
    ident = abs(y_spec(a_tab * 1.05 ** e_k1) / y_spec(a_tab * 1.05 ** e_k1) - 1.0)
    e_save = ek_tab.copy()
    ek_flat = np.full_like(ek_tab, e_k1)
    ek_tab[:] = ek_flat
    ident2 = abs(d_beyond(0.10) - 1.0)
    ek_tab[:] = e_save
    if ident > 1e-14 or ident2 > 1e-14:
        raise RuntimeError(f"identity check failed: {ident:.2e}/{ident2:.2e}")

    # ---- per-point evaluation against the archived measurements ----
    rows: dict[str, dict] = {}
    signs_ok, f_ok = [], []
    for th, rel in POINTS.items():
        qs = json.loads((M5 / rel).read_text(encoding="utf-8"))["results"]["qs_chi"]
        dop = (abs(_c(qs["D_OP_measured"])) - 1.0) * 100.0
        q1 = (abs(_c(qs["D_OP_QS1_pred"])) - 1.0) * 100.0
        db = d_beyond(th)
        d_qs1k = (abs(db * _c(qs["D_OP_QS1_pred"])) - 1.0) * 100.0
        f = (d_qs1k - q1) / (dop - q1)
        s_ok = d_qs1k < 0.0
        signs_ok.append(s_ok)
        f_ok.append(F_BAND[0] <= f <= F_BAND[1])
        rows[f"{th:g}"] = {
            "D_OP_measured_pct": dop, "QS1_pct": q1,
            "D_beyond_abs_minus_1_pct": (abs(db) - 1.0) * 100.0,
            "D_QS1k_pct": d_qs1k,
            "fraction_explained": f, "sign_reproduced": s_ok,
            "sens_highk_e_k1_pct": (abs(d_beyond(th, e_hi_k1=True)
                                        * _c(qs["D_OP_QS1_pred"])) - 1.0) * 100.0,
            "sens_mean_elevation_pct": (abs(d_beyond(th, elev=0.5)
                                            * _c(qs["D_OP_QS1_pred"])) - 1.0) * 100.0,
        }
        print(f"Theta={th:g}: measured {dop:+.2f}%  QS1 {q1:+.2f}%  "
              f"QS1k {d_qs1k:+.2f}%  f={f:+.3f}  sign_ok={s_ok}")

    if all(signs_ok) and all(f_ok):
        label = "MECHANISM_CLOSED"
    elif all(signs_ok):
        label = "MECHANISM_PARTIAL"
    else:
        label = "MECHANISM_NOT_CLOSED"
    print(f"pre-registered verdict: {label}")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = REPO_ROOT / "results" / "phase5" / "qs1k_mechanism" / run_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps({
        "unit": "WP4-QS1K-MECHANISM", "run_id": run_id,
        "verdict_pre_registered": label,
        "criteria": {"f_band": F_BAND, "sign": "negative at all four points",
                     "judged_on": "abs-1 percent"},
        "exponent_table": {f"{k:g}": e for k, e in exps},
        "e_k1": e_k1, "geometry": {"ny": NY, "hs": HS},
        "points": rows,
        "sources": {"alpha_table": str(G0_TABLE_CSV),
                    "working_points": {f"{t:g}": p for t, p in POINTS.items()}},
    }, indent=1), encoding="utf-8")
    print("outputs ->", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
