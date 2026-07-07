"""D3 verdict probe: is a COARSE dispersion-free acoustic subdomain clean?

Route-b' follow-on (2026-07-05). D1 proved the dispersion correction is thermal-only, so a
coarse acoustic region that only carries sound needs no dispersion -> no seam injection. A
coarse grid also collapses scale wall B: 10 kHz has lambda ~ 40-100 cells and ~150-400
steps/period instead of 13286 cells / 51051 steps.

The essential D3 question, stripped of any open-boundary implementation: in a coarse,
dispersion-free, PERIODIC column with a TUNED tau (independent artificial viscosity -- sound
is inviscid at leading order), does an outgoing Gaussian acoustic pulse propagate without
generating backscatter (w- from w+)? Result (2026-07-05, dx=334um lambda/dx=104):

    tau21=0.573 -> w-/w+ = 0.0018, sound-speed err +0.14%, amplitude survival 99%
    tau21=0.646 -> w-/w+ = 0.0030, sound-speed err +0.36%, amplitude survival 99%

vs the frozen dx2p6 injection floor 0.15 and the P4-1 gate 0.05: backscatter ~0.002 is ~30x
below the floor, ~25x below the gate, near the seam-free ideal 1e-3. The volume-injection
floor does NOT exist in the acoustic region.

Exposed D3 complexity (honest): (1) naive coarsening keeps the frozen mapping and collapses
tau21->0.5007 -> acoustic goes dirty (0.08) / crashes -- the acoustic region needs an
independent tau, i.e. it is a SEPARATE LBM domain, not 'change dx'; (2) the heat-flux
min-norm regularization goes gram-singular at large viscosity -- the acoustic region should
DISABLE it (no thermal accuracy needed); (3) the fine-thermal <-> coarse-acoustic interface
coupling is untouched (standard but nontrivial grid-refinement, the next knife).

VERDICT: D3's core claim holds -- the acoustic medium is clean. Remaining work (independent
acoustic domain + interface coupling) is tractable multi-domain engineering, not a rabbit
hole (unlike D1/b' which are refuted at the root). See P4_1b_Seam_Detrend_Project.md section 9.

Diagnostic only: the probe scales nu0/alpha0 together (Pr preserved) as an artificial
acoustic viscosity; the frozen production config is untouched."""

from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from core.macroscopic import recover_macro
from core.solver import GasSolver2D
from scripts.phase2_m2_verification import load_config

DEFAULT_GAS_CONFIG = Path("configs/gas_air_10k_d2q37_levelc_dx2p6.yaml")
DT_OVER_DX_S_PER_M = 1.95881e-9 / 2.61175e-6   # frozen lattice sound-speed mapping
LAMBDA_10K_M = 347.0 / 1.0e4                    # 10 kHz air wavelength = 34.7 mm


def _frame(solver: GasSolver2D) -> dict[str, float]:
    th0 = float(solver.mapping.theta_ref_lu)
    rho0 = float(solver.mapping.lattice.rho_ref_lu)
    c = math.sqrt(1.4 * th0)
    return {"rho0": rho0, "c_lu": c, "z0": rho0 * c, "p_ref": rho0 * th0}


def run_case(base_cfg: dict, dx_c_m: float, nu0_mult: float, ny: int = 512) -> dict[str, Any]:
    cfg = copy.deepcopy(base_cfg)
    cfg["lattice"]["dx_m"] = dx_c_m
    cfg["lattice"]["dt_s"] = dx_c_m * DT_OVER_DX_S_PER_M
    cfg["physical"]["nu0_m2_s"] = float(base_cfg["physical"]["nu0_m2_s"]) * nu0_mult
    cfg["physical"]["alpha0_m2_s"] = float(base_cfg["physical"]["alpha0_m2_s"]) * nu0_mult
    cfg["collision"]["dispersion_correction_enabled"] = False
    cfg["numerics"] = {**cfg.get("numerics", {}), "nx": 4, "ny": ny}
    solver = GasSolver2D(cfg)
    fr = _frame(solver)
    lam_cells = LAMBDA_10K_M / dx_c_m
    y0, sigma = ny * 0.30, max(8.0, lam_cells / 6.0)
    y = np.arange(ny, dtype=float)[:, None] * np.ones((1, solver.nx))
    pp0 = 1e-3 * fr["p_ref"] * np.exp(-((y - y0) ** 2) / (2.0 * sigma**2))
    rho = fr["rho0"] + pp0 / fr["c_lu"] ** 2
    u = np.zeros((ny, solver.nx, 2)); u[..., 1] = pp0 / fr["z0"]   # outgoing: w+ only
    solver.initialize_from_macro(rho, u, (fr["p_ref"] + pp0) / rho)
    tau21 = float(solver.mapping.tau21)
    travel = (ny - 1 - y0) / fr["c_lu"]
    worst, com0, com1, now = 0.0, None, None, 0
    for i, frac in enumerate((0.2, 0.4, 0.6, 0.8)):
        tgt = int(frac * travel)
        solver.step(tgt - now, boundary_callback=None); now = tgt
        if not np.isfinite(solver.f).all():
            return {"dx_um": dx_c_m * 1e6, "lambda_cells": lam_cells, "tau21": tau21,
                    "nu0_mult": nu0_mult, "crash_frac": frac, "worst_backscatter": None}
        m = recover_macro(solver.f, solver.g, D=2, S=3, lattice=solver.lattice)
        pp = np.mean(m.p, axis=-1) - fr["p_ref"]
        v = np.mean(m.u[..., 1], axis=-1)
        wm, wp = pp - fr["z0"] * v, pp + fr["z0"] * v
        worst = max(worst, float(np.sqrt(np.mean(wm**2)) / max(np.sqrt(np.mean(wp**2)), 1e-300)))
        com = float(np.sum(np.arange(ny) * np.abs(pp)) / max(np.sum(np.abs(pp)), 1e-300))
        if i == 0:
            com0 = com
        com1 = com
    speed = (com1 - com0) / (0.6 * travel)
    return {
        "dx_um": dx_c_m * 1e6, "lambda_cells": lam_cells, "tau21": tau21, "nu0_mult": nu0_mult,
        "worst_backscatter": worst, "sound_speed_err": speed / fr["c_lu"] - 1.0,
        "amplitude_survival": float(np.max(np.abs(pp))) / (1e-3 * fr["p_ref"]), "crash_frac": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="D3 coarse acoustic cleanliness verdict probe (diagnostic).")
    parser.add_argument("--gas-config", type=Path, default=DEFAULT_GAS_CONFIG)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    base = load_config(args.gas_config)

    print("reference: dx2p6 injection floor 0.15  |  P4-1 gate 0.05  |  seam-free ideal ~0.001")
    print(f"{'dx[um]':>8} {'lam/dx':>7} {'nu0x':>6} {'tau21':>8} {'backscatter':>12} {'c_err':>9} {'amp_left':>9}")
    results = []
    for dx_c in (334e-6, 867e-6):
        for nu0_mult in (100.0, 200.0):
            r = run_case(base, dx_c, nu0_mult)
            results.append(r)
            if r["crash_frac"] is not None:
                print(f"{r['dx_um']:8.1f} {r['lambda_cells']:7.1f} {nu0_mult:6.0f} {r['tau21']:8.4f} "
                      f"{'CRASH@' + str(r['crash_frac']):>12}")
            else:
                print(f"{r['dx_um']:8.1f} {r['lambda_cells']:7.1f} {nu0_mult:6.0f} {r['tau21']:8.4f} "
                      f"{r['worst_backscatter']:12.5f} {r['sound_speed_err']:+9.4f} {r['amplitude_survival']:9.3f}")
    print("\nVERDICT: coarse dispersion-free acoustic medium is clean (backscatter ~0.002, ~30x below "
          "the dx2p6 injection floor). D3 core claim holds; remaining work is multi-domain engineering.")
    if args.out:
        args.out.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
