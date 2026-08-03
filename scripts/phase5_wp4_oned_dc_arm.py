"""Phase_5 WP4 1D DC-arm legs: the A2a map's continuum reference tier (§15.2).

Computes D_OP_1D(Theta_DC) = Y(Theta_DC)/Y(0) - 1 on the certified 1D NSF
instrument (G3) in the canonical sink geometry (lid_bc="isothermal", height =
the tent H_s in thermal-depth units), for BOTH formal branches
(1D-lbm-equivalent_g0_measured_k1_v1 and physical air) across the full WP4
Theta_DC set {0.02, 0.05, 0.075, 0.10}. This is the middle tier of the
measured three-tier reference hierarchy (QS static > 1D full-nonlinear NSF >
LBM sign-flip) — the WP3 P-DC2 §5.3 DC arm formalized into a repo script
(one convention, one provenance, five points) and extended to the WP4 map.

Protocol (pre-registered, the A2a-lite prescribed-Theta_DC family):
WallDrive(kind="temperature", mean=Theta_DC*T0, amplitude=eps*T0) — state
matching by construction; eps = 0.005 (the A2a increment family's linear
probe); closed-box pressure-work corrected admittance is the primary readout
(raw archived alongside; the correction largely cancels in the D_OP ratio).

The WP3 scratch-analysis pair (0.05: +0.76%@-0.06 deg, 0.10: +1.51%@-0.13 deg,
lbm-eq corrected) serves as the reproduction check; if conventions differ at
the 0.1pp level the five-point series from THIS script supersedes the scratch
pair for the paper trend (single-convention series), with the deviation
archived. Pure 1D analysis leg — no LBM, no gate claims.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from postproc.multiharmonic_fit import fit_multiharmonic  # noqa: E402
from reference.constants import default_params  # noqa: E402
from reference.nonlinear_nsf_1d import (  # noqa: E402
    NSF1DConfig,
    WallDrive,
    g0_measured_transport,
    omega_from_frequency,
    physical_air_transport,
    run_nsf1d,
)

THETA_SET = [0.0, 0.02, 0.05, 0.075, 0.10]
WP3_SCRATCH_REPRO = {  # lbm-eq corrected D_OP from wp3_go_nogo_decision.md §5.2
    0.05: {"abs_minus_1": +0.0076, "phase_deg": -0.06},
    0.10: {"abs_minus_1": +0.0151, "phase_deg": -0.13},
}


def measure_wp_admittance(params, transport, *, theta_dc: float, eps: float,
                          frequency_hz: float, height_over_delta: float,
                          cells_per_delta: float, n_cycles: float,
                          settle_cycles: float) -> dict:
    omega = omega_from_frequency(frequency_hz)
    alpha0 = float(transport.k(params.T0)) / (params.rho0 * params.cp)
    delta_t = math.sqrt(2.0 * alpha0 / omega)
    drive = WallDrive(kind="temperature", frequency_hz=frequency_hz,
                      amplitude=eps * params.T0, mean=theta_dc * params.T0,
                      ramp_cycles=2.0)
    cfg = NSF1DConfig(params=params, transport=transport, drive=drive,
                      height_m=height_over_delta * delta_t,
                      n_cells=int(round(height_over_delta * cells_per_delta)),
                      n_cycles=n_cycles, samples_per_cycle=64,
                      lid_bc="isothermal")
    res = run_nsf1d(cfg)
    mask = res.t_samples >= settle_cycles / frequency_hz * (1.0 - 1e-12)
    t = res.t_samples[mask]
    q1 = fit_multiharmonic(t, res.q_wall_conductive[mask], omega,
                           n_harmonics=5).harmonic(1)
    tw1 = fit_multiharmonic(t, res.wall_temperature[mask], omega,
                            n_harmonics=5).harmonic(1)
    p1 = fit_multiharmonic(t, res.p_box_mean[mask], omega,
                           n_harmonics=5).harmonic(1)
    t_p1 = p1 / (params.rho0 * params.cp)
    return {
        "Y_raw": q1 / tw1,
        "Y_corrected": q1 / (tw1 - t_p1),
        "theta_dc": theta_dc,
        "mass_drift_rel": res.mass_drift_rel,
        "energy_residual_rel_flux": res.energy_residual_rel_flux,
    }


def _cplx(z: complex) -> dict:
    return {"re": float(np.real(z)), "im": float(np.imag(z)),
            "abs": float(abs(z)),
            "phase_deg": float(math.degrees(math.atan2(np.imag(z), np.real(z))))}


def main() -> int:
    ap = argparse.ArgumentParser(description="WP4 1D DC-arm legs (A2a map reference tier)")
    ap.add_argument("--frequency", type=float, default=1.0e4)
    ap.add_argument("--height-over-delta", type=float, default=4.61,
                    help="tent H_s in thermal-depth units (G4a canonical)")
    ap.add_argument("--cells-per-delta", type=float, default=12.0)
    ap.add_argument("--eps", type=float, default=0.005)
    ap.add_argument("--cycles", type=float, default=14.0)
    ap.add_argument("--settle", type=float, default=12.0)
    ap.add_argument("--output-root", default=None)
    args = ap.parse_args()

    params = default_params()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = (Path(args.output_root) if args.output_root
                else REPO_ROOT / "results" / "phase5" / "oned_dc_arm")
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    branches = {"lbm_equivalent_g0": g0_measured_transport(params),
                "physical_air": physical_air_transport(params)}
    rows: dict[str, dict] = {}
    for bname, transport in branches.items():
        y_by: dict[float, dict] = {}
        for th in THETA_SET:
            y_by[th] = measure_wp_admittance(
                params, transport, theta_dc=th, eps=args.eps,
                frequency_hz=args.frequency,
                height_over_delta=args.height_over_delta,
                cells_per_delta=args.cells_per_delta,
                n_cycles=args.cycles, settle_cycles=args.settle)
            print(f"[{bname}] Theta_DC={th:g}: |Y_corr|={abs(y_by[th]['Y_corrected']):.6e} "
                  f"mass={y_by[th]['mass_drift_rel']:.1e}", flush=True)
        y0 = y_by[0.0]["Y_corrected"]
        y0_raw = y_by[0.0]["Y_raw"]
        rows[bname] = {
            f"{th:g}": {
                "D_OP_corrected": _cplx(y_by[th]["Y_corrected"] / y0),
                "D_OP_raw": _cplx(y_by[th]["Y_raw"] / y0_raw),
                "legality": {k: y_by[th][k] for k in
                             ("mass_drift_rel", "energy_residual_rel_flux")},
            } for th in THETA_SET if th > 0.0
        }
        for th in THETA_SET[1:]:
            d = rows[bname][f"{th:g}"]["D_OP_corrected"]
            print(f"[{bname}] D_OP_1D({th:g}) = {d['abs'] - 1.0:+.4%} @ "
                  f"{d['phase_deg']:+.3f} deg", flush=True)

    repro = {}
    for th, ref in WP3_SCRATCH_REPRO.items():
        got = rows["lbm_equivalent_g0"][f"{th:g}"]["D_OP_corrected"]
        repro[f"{th:g}"] = {
            "wp3_scratch": ref,
            "this_script": {"abs_minus_1": got["abs"] - 1.0,
                            "phase_deg": got["phase_deg"]},
            "abs_dev_pp": (got["abs"] - 1.0 - ref["abs_minus_1"]) * 100.0,
        }
        print(f"repro check Theta_DC={th:g}: this {got['abs'] - 1.0:+.4%} vs "
              f"WP3 scratch {ref['abs_minus_1']:+.2%} "
              f"(dev {repro[f'{th:g}']['abs_dev_pp']:+.3f} pp)", flush=True)

    summary = {
        "unit": "WP4-1D-DC-ARM", "run_id": run_id,
        "protocol": {"frequency_Hz": args.frequency,
                     "height_over_delta": args.height_over_delta,
                     "cells_per_delta": args.cells_per_delta,
                     "eps": args.eps, "cycles": args.cycles,
                     "settle": args.settle, "theta_set": THETA_SET,
                     "lid_bc": "isothermal",
                     "readout": "closed-box pressure-work corrected Y "
                                "(raw archived); D_OP = Y(Theta)/Y(0)"},
        "branches": rows,
        "wp3_scratch_reproduction": repro,
        "note": "single-convention five-point series; supersedes the WP3 "
                "scratch pair for the paper trend if deviations are at the "
                "convention level (archived above)",
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1),
                                          encoding="utf-8")
    print(f"outputs -> {out_dir}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
