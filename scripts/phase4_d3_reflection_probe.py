"""P4-D3 D3-2 closure: does the simplified-collision acoustic domain reach |R|<0.05 with a
non-degenerate reflectometer?

Project: docs/Phase_4/M4/P4_D3_Multidomain_Acoustic_Project.md (sections 7, 8; D3-2 gate).

Section 7 left D3-2 "certification not closed": a sponge top read |R|=0.0015 but the reading was
insensitive to sponge strength, and the decisive rigid-lid control (|R|~1) crashed on the heat-flux
Gram. The core step (section 8, acoustic_simplified_collision) removed that Gram, so the rigid-lid
control now runs -- this probe closes (or refutes) the certification.

Method (pulse characteristic reflectometry -- the well-conditioned split P4-1 endorsed, no
ill-conditioned pressure-LS): launch an OUTGOING Gaussian pulse (w+ only), let it hit the top
boundary, and read the reflected wave at a probe row via the local Riemann invariants
w+ = p' + Z0 v', w- = p' - Z0 v'. |R| = peak|w-| / peak|w+| at the probe. Non-degeneracy is settled
by CONTROLS on the SAME rig:
  * rigid lid (bounce-back)  -> should reflect, |R| ~ O(1)  (proves the rig can SEE reflection)
  * periodic (no boundary)   -> |R| at the medium backscatter floor  (a perfect-absorber proxy)
  * sponge (absorbing)       -> the D3-2 test; must sit near the floor AND far below the rigid lid
A sponge |R| that is (i) < 0.05, (ii) clearly below the rigid-lid control, and (iii) responds to
sponge strength certifies non-degenerately. If the sponge |R| equals the rigid-lid |R| (the strong
filter dissipates the reflected wave before the probe), the measurement is degenerate -> D3-2 fails.

Diagnostic only: reads configs/phase4_acoustic_coarse_dx334.yaml; frozen configs untouched."""

from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from numpy.linalg import LinAlgError

from boundary.open_sponge import make_top_sponge_callback
from core.macroscopic import recover_macro
from core.solver import GasSolver2D
from scripts.phase2_m2_verification import load_config

DEFAULT_ACOUSTIC_CONFIG = Path("configs/phase4_acoustic_coarse_dx334.yaml")
LAMBDA_10K_M = 347.0 / 1.0e4


def _frame(solver: GasSolver2D) -> dict[str, float]:
    th0 = float(solver.mapping.theta_ref_lu)
    rho0 = float(solver.mapping.lattice.rho_ref_lu)
    c = math.sqrt(1.4 * th0)
    return {"rho0": rho0, "c_lu": c, "z0": rho0 * c, "p_ref": rho0 * th0}


def make_top_rigid_lid_callback(solver: GasSolver2D):
    """Halfway bounce-back at the top row only (a fully reflecting rigid lid, |R|~1 control)."""

    cy = solver.lattice.c[:, 1]
    opp = solver.lattice.opposite
    down = np.where(cy < 0)[0]

    def cb(*, solver, f_post, g_post, f_stream, g_stream):
        top = f_stream.shape[0] - 1
        for a in down:  # populations entering the top wall from outside <- reflect up-going pops
            f_stream[top, :, a] = f_post[top, :, opp[a]]
            g_stream[top, :, a] = g_post[top, :, opp[a]]
        return f_stream, g_stream

    return cb


def run_reflection(cfg: dict, *, ny: int = 512, top: str = "sponge",
                   n_sponge: int = 80, sigma_max: float = 0.5) -> dict[str, Any]:
    """Launch an outgoing pulse, measure |R| = peak|w-|/peak|w+| at a probe row below the boundary.

    ``top`` in {"sponge", "rigid", "periodic"}."""

    cfg = copy.deepcopy(cfg)
    cfg["numerics"] = {**cfg.get("numerics", {}), "nx": 4, "ny": ny}
    solver = GasSolver2D(cfg)
    fr = _frame(solver)
    dx = float(solver.mapping.lattice.dx_m)
    lam_cells = LAMBDA_10K_M / dx

    boundary_top = ny - n_sponge if top == "sponge" else ny - 1
    y0, sigma = ny * 0.22, max(8.0, lam_cells / 6.0)
    probe = int(0.42 * ny)                       # clean row: below the boundary, above the launch
    y = np.arange(ny, dtype=float)[:, None] * np.ones((1, solver.nx))
    pp0 = 1e-3 * fr["p_ref"] * np.exp(-((y - y0) ** 2) / (2.0 * sigma**2))
    rho = fr["rho0"] + pp0 / fr["c_lu"] ** 2
    u = np.zeros((ny, solver.nx, 2)); u[..., 1] = pp0 / fr["z0"]   # outgoing: w+ only
    solver.initialize_from_macro(rho, u, (fr["p_ref"] + pp0) / rho)

    if top == "sponge":
        cb = make_top_sponge_callback(n_sponge=n_sponge, sigma_max=sigma_max)
    elif top == "rigid":
        cb = make_top_rigid_lid_callback(solver)
    elif top == "periodic":
        cb = None
    else:
        raise ValueError(f"unknown top: {top}")

    # Run ~2.2 full-height transits: pulse up to the boundary, reflect, back down past the probe.
    n_steps = int(2.2 * ny / fr["c_lu"])
    up_time = (boundary_top - y0) / fr["c_lu"]
    wp_peak, wm_peak, wm_after = 0.0, 0.0, 0.0
    check = max(1, n_steps // 120)
    for s in range(n_steps):
        try:
            solver.step(1, boundary_callback=cb)
        except LinAlgError:
            return {"top": top, "sigma_max": sigma_max, "crash_step": s, "R_abs": None}
        if s % check == 0:
            if not np.isfinite(solver.f).all():
                return {"top": top, "sigma_max": sigma_max, "crash_step": s, "R_abs": None}
            m = recover_macro(solver.f[probe:probe + 1], solver.g[probe:probe + 1],
                              D=2, S=3, lattice=solver.lattice)
            pp = float(np.mean(m.p) - fr["p_ref"])
            v = float(np.mean(m.u[..., 1]))
            wp, wm = pp + fr["z0"] * v, pp - fr["z0"] * v
            wp_peak = max(wp_peak, abs(wp))
            wm_peak = max(wm_peak, abs(wm))
            if s > up_time:                       # reflected-wave window (after pulse hit boundary)
                wm_after = max(wm_after, abs(wm))
    r_abs = wm_after / max(wp_peak, 1e-300)
    return {"top": top, "sigma_max": sigma_max, "n_sponge": (n_sponge if top == "sponge" else 0),
            "crash_step": None, "R_abs": float(r_abs),
            "w_plus_peak": float(wp_peak), "w_minus_reflected": float(wm_after),
            "probe_row": probe, "boundary_top": boundary_top, "n_steps": n_steps}


def main() -> None:
    parser = argparse.ArgumentParser(description="P4-D3 D3-2 acoustic open-boundary reflectometer (diagnostic).")
    parser.add_argument("--acoustic-config", type=Path, default=DEFAULT_ACOUSTIC_CONFIG)
    parser.add_argument("--ny", type=int, default=512)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    aco = load_config(args.acoustic_config)

    print(f"config: {args.acoustic_config}  ny={args.ny}")
    print("pulse characteristic reflectometry: |R| = peak|w-|(reflected) / peak|w+|(incident) at a probe row\n")
    results = []

    print("controls (same rig, different top):")
    for top in ("periodic", "rigid"):
        r = run_reflection(aco, ny=args.ny, top=top)
        results.append(r)
        v = f"CRASH@{r['crash_step']}" if r["R_abs"] is None else f"|R|={r['R_abs']:.4f}"
        print(f"    top={top:9s} {v}")

    # Sponge THICKNESS sweep (the real non-degeneracy check): a thin sponge absorbs less and so
    # must reflect MORE -- a monotone response proves the rig reads absorption, not a fixed floor.
    print("\nsponge (D3-2 test) thickness sweep at sigma_max=0.5:")
    for n_sp in (4, 16, 40, 80):
        r = run_reflection(aco, ny=args.ny, top="sponge", n_sponge=n_sp, sigma_max=0.5)
        results.append(r)
        v = f"CRASH@{r['crash_step']}" if r["R_abs"] is None else f"|R|={r['R_abs']:.4f}"
        print(f"    sponge n_sponge={n_sp:3d}  {v}")

    rigid = next((x for x in results if x["top"] == "rigid"), None)
    periodic = next((x for x in results if x["top"] == "periodic"), None)
    sponge = [x for x in results if x["top"] == "sponge" and x["R_abs"] is not None]
    thin = min(sponge, key=lambda x: x["n_sponge"]) if sponge else None    # fewest sponge rows
    thick = max(sponge, key=lambda x: x["n_sponge"]) if sponge else None   # most sponge rows (production)
    print("\nVERDICT:")
    if rigid and rigid["R_abs"] is not None and thin and thick:
        prod = thick["R_abs"]
        rig_ok = rigid["R_abs"] > 0.5                          # the rig can SEE reflection
        gate_ok = prod < 0.05                                  # production sponge below the gate
        monotone = thin["R_abs"] > thick["R_abs"] * 3.0        # thinner sponge reflects more
        non_degen = rig_ok and gate_ok and monotone
        print(f"    rigid-lid control |R|={rigid['R_abs']:.4f} (O(1) -> rig sees reflection, NOT filter-degenerate)")
        print(f"    production sponge (thickest) |R|={prod:.4f} (gate <0.05)")
        print(f"    thickness response: thin |R|={thin['R_abs']:.4f} > thick |R|={thick['R_abs']:.4f} "
              f"({'monotone' if monotone else 'flat -> suspect'})")
        print(f"    -> {'D3-2 CERTIFIED (non-degenerate: rig sees reflection, responds to absorption, sponge below gate)' if non_degen else 'NOT certified'}")
    else:
        print("    inconclusive (a control crashed or produced no reading)")
    if args.out:
        args.out.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
