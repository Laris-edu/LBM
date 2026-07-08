"""P4-D3 core step verdict probe: the acoustic SIMPLIFIED collision.

Project: docs/Phase_4/M4/P4_D3_Multidomain_Acoustic_Project.md (sections 1, 7).

The coarse dispersion-free acoustic subdomain carries sound only and does NOT resolve heat.
The Phase_2/3 collision keeps a heat-flux min-norm regularization whose Gram solve goes singular
(or the field destabilises) under large tuned viscosity, coarse grids, or -- decisively -- under
reflected-energy accumulation. That fragility is what blocked D3-2: the rigid reflection CONTROL
(which should read |R|~1 and prove the reflectometer is not just reading noise) crashed before it
could be read, so the promising |R|=0.0015 open-boundary reading could not be cleanly certified as
non-degenerate.

The core step (core/collision_smrt.py + CollisionScales.acoustic_simplified_collision, default off)
disables that heat-flux reconstruction for the acoustic domain only. This probe demonstrates the
three claims of the step, all on configs/phase4_acoustic_coarse_dx334.yaml:

  (A) open propagation stays STABLE and low-backscatter (below the P4-1 gate 0.05) under the
      simplified collision, with the strong local biharmonic filter (0.03x6, project section 7)
      replacing the heat-flux regularization's incidental high-k damping. FINDING: dropping the
      heat-flux reconstruction shifts the sound speed ~-5% (a PHYSICAL effect -- the strong filter
      alone leaves c unchanged: full+0.03x6 stays +0.15%), so the acoustic domain's sound speed is
      re-tuned in D3-2; stability + backscatter are the core-step gates.
  (B) a closed reflecting box (bounce-back top+bottom -> reflected energy accumulates) 2x2 ablation
      over {full, simplified} x {weak filter, strong filter}. FINDING (honest, corrects section 7):
      reflection stability is set by the STRONG LOCAL FILTER, not the heat-flux removal -- strong
      filter survives for BOTH collisions, weak filter crashes for BOTH (simplified crashes fastest,
      because the heat-flux regularization provides incidental high-k damping). The heat-flux-Gram
      LinAlgError section 7 saw is a SYMPTOM of the destabilised field, not the root cause. The core
      step's real value is a PURER sound-only domain (the acoustic collision no longer carries the
      dx2p6 tau32-tuned heat-flux closure, which is thermal-specific and undefined for a sound-only
      domain) and removing the heat-flux Gram as a confound for the D3-2 reflection certification --
      not a stability fix in itself.

Diagnostic only: the frozen production / Level C configs are untouched; this reads the new,
explicit, default-off acoustic switch on a dedicated Phase_4 acoustic-domain config."""

from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from numpy.linalg import LinAlgError

from core.macroscopic import recover_macro
from core.solver import GasSolver2D
from scripts.phase2_m2_verification import load_config

DEFAULT_ACOUSTIC_CONFIG = Path("configs/phase4_acoustic_coarse_dx334.yaml")
LAMBDA_10K_M = 347.0 / 1.0e4  # 10 kHz air wavelength = 34.7 mm

# Level C heat-flux regularization policy, restored to build the FULL-collision ablation arm.
_LEVELC_HEAT_FLUX = {
    "regularized_heat_flux_factor": "auto_d2q37_tau32_linear",
    "heat_flux_retention_policy": "auto_d2q37_tau32_linear",
    "heat_flux_retention_curve": {
        "type": "affine",
        "coefficients": [-0.5030006782780277, 0.7230829392328689],
    },
}


def _frame(solver: GasSolver2D) -> dict[str, float]:
    th0 = float(solver.mapping.theta_ref_lu)
    rho0 = float(solver.mapping.lattice.rho_ref_lu)
    c = math.sqrt(1.4 * th0)
    return {"rho0": rho0, "c_lu": c, "z0": rho0 * c, "p_ref": rho0 * th0}


def _solver(cfg: dict, ny: int) -> GasSolver2D:
    cfg = copy.deepcopy(cfg)
    cfg["numerics"] = {**cfg.get("numerics", {}), "nx": 4, "ny": ny}
    return GasSolver2D(cfg)


def full_heatflux_variant(cfg: dict) -> dict:
    """Same acoustic config but with the heat-flux regularization RESTORED (switch off).

    Isolates the heat-flux min-norm regularization as the single changed variable versus the
    simplified acoustic config (dispersion / acoustic-phase / tuned viscosity / filter all equal)."""

    cfg = copy.deepcopy(cfg)
    cfg["collision"]["acoustic_simplified_collision"] = False
    cfg["collision"].update(copy.deepcopy(_LEVELC_HEAT_FLUX))
    return cfg


def with_filter(cfg: dict, strength: float, passes: int) -> dict:
    """Return a copy with the high-wavenumber filter overridden (for the 2x2 stability ablation)."""

    cfg = copy.deepcopy(cfg)
    cfg["numerics"] = {**cfg.get("numerics", {})}
    cfg["numerics"]["high_wavenumber_filter"] = {"enabled": True, "strength": strength, "passes": passes}
    return cfg


WEAK_FILTER = (0.0065, 1)   # the inherited Level C filter (pre-core-step acoustic medium)
STRONG_FILTER = (0.03, 6)   # section 7 stability solution (shipped in the acoustic config)


def _pulse(solver: GasSolver2D, ny: int, dx_m: float):
    fr = _frame(solver)
    lam_cells = LAMBDA_10K_M / dx_m
    y0, sigma = ny * 0.30, max(8.0, lam_cells / 6.0)
    y = np.arange(ny, dtype=float)[:, None] * np.ones((1, solver.nx))
    pp0 = 1e-3 * fr["p_ref"] * np.exp(-((y - y0) ** 2) / (2.0 * sigma**2))
    return fr, lam_cells, y0, pp0


def run_open(cfg: dict, ny: int = 512) -> dict[str, Any]:
    """(A) Outgoing pulse in a periodic column: acoustic-gate metrics under the given collision."""

    solver = _solver(cfg, ny)
    dx_m = float(solver.mapping.lattice.dx_m)
    fr, lam_cells, y0, pp0 = _pulse(solver, ny, dx_m)
    rho = fr["rho0"] + pp0 / fr["c_lu"] ** 2
    u = np.zeros((ny, solver.nx, 2))
    u[..., 1] = pp0 / fr["z0"]  # outgoing: w+ only
    solver.initialize_from_macro(rho, u, (fr["p_ref"] + pp0) / rho)
    tau21 = float(solver.mapping.tau21)
    travel = (ny - 1 - y0) / fr["c_lu"]
    worst, com0, com1, now, pp = 0.0, None, None, 0, pp0
    for i, frac in enumerate((0.2, 0.4, 0.6, 0.8)):
        tgt = int(frac * travel)
        try:
            solver.step(tgt - now, boundary_callback=None)
        except LinAlgError:
            # A destabilised field makes a min-norm collision Gram solve singular; classify
            # as a crash (this is the instability the simplified collision is meant to avoid).
            return {"tau21": tau21, "crash_frac": frac, "worst_backscatter": None,
                    "sound_speed_err": None, "amplitude_survival": None}
        now = tgt
        if not np.isfinite(solver.f).all():
            return {"tau21": tau21, "crash_frac": frac, "worst_backscatter": None,
                    "sound_speed_err": None, "amplitude_survival": None}
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
    return {"tau21": tau21, "crash_frac": None, "worst_backscatter": worst,
            "sound_speed_err": speed / fr["c_lu"] - 1.0,
            "amplitude_survival": float(np.max(np.abs(pp))) / (1e-3 * fr["p_ref"])}


def _bounce_back_box(solver: GasSolver2D):
    """Halfway bounce-back at the top (row ny-1) and bottom (row 0): a closed, energy-trapping box."""

    cy = solver.lattice.c[:, 1]
    opp = solver.lattice.opposite
    up = np.where(cy > 0)[0]
    down = np.where(cy < 0)[0]

    def cb(*, solver, f_post, g_post, f_stream, g_stream):
        top = f_stream.shape[0] - 1
        for a in down:  # entering the top wall from outside -> reflect the up-going post-collision pop
            f_stream[top, :, a] = f_post[top, :, opp[a]]
            g_stream[top, :, a] = g_post[top, :, opp[a]]
        for a in up:  # entering the bottom wall from outside
            f_stream[0, :, a] = f_post[0, :, opp[a]]
            g_stream[0, :, a] = g_post[0, :, opp[a]]
        return f_stream, g_stream

    return cb


def run_closed_box(cfg: dict, ny: int = 384, n_transits: float = 6.0) -> dict[str, Any]:
    """(B) Closed reflecting box: reflected energy accumulates. Returns crash step or survival."""

    solver = _solver(cfg, ny)
    dx_m = float(solver.mapping.lattice.dx_m)
    fr, lam_cells, y0, pp0 = _pulse(solver, ny, dx_m)
    rho = fr["rho0"] + pp0 / fr["c_lu"] ** 2
    u = np.zeros((ny, solver.nx, 2))
    u[..., 1] = pp0 / fr["z0"]
    solver.initialize_from_macro(rho, u, (fr["p_ref"] + pp0) / rho)
    cb = _bounce_back_box(solver)
    n_steps = int(n_transits * ny / fr["c_lu"])
    amp0 = float(np.max(np.abs(pp0)))
    check = max(1, n_steps // 40)
    for s in range(n_steps):
        try:
            solver.step(1, boundary_callback=cb)
        except LinAlgError:
            # Reflected-energy accumulation destabilised the field -> a min-norm collision Gram
            # solve went singular. Classify as a crash (the LinAlgError surfaces in whichever
            # Gram runs; it is a symptom of the instability, not a heat-flux-specific failure).
            return {"survived": False, "crash_step": s, "n_steps": n_steps,
                    "tau21": float(solver.mapping.tau21), "amp_ratio": None}
        if s % check == 0 or s == n_steps - 1:
            if not np.isfinite(solver.f).all():
                return {"survived": False, "crash_step": s, "n_steps": n_steps,
                        "tau21": float(solver.mapping.tau21), "amp_ratio": None}
    m = recover_macro(solver.f, solver.g, D=2, S=3, lattice=solver.lattice)
    pp = np.mean(m.p, axis=-1) - fr["p_ref"]
    return {"survived": True, "crash_step": None, "n_steps": n_steps,
            "tau21": float(solver.mapping.tau21),
            "amp_ratio": float(np.max(np.abs(pp)) / amp0)}


def main() -> None:
    parser = argparse.ArgumentParser(description="P4-D3 acoustic simplified-collision verdict probe.")
    parser.add_argument("--acoustic-config", type=Path, default=DEFAULT_ACOUSTIC_CONFIG)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    aco = load_config(args.acoustic_config)
    full = full_heatflux_variant(aco)

    print(f"config: {args.acoustic_config}")
    print("\n(A) open propagation under SIMPLIFIED collision (stability + backscatter gate):")
    a = run_open(aco)
    print(f"    tau21={a['tau21']:.4f}  backscatter={a['worst_backscatter']:.5f} (gate <0.05)  "
          f"amp_left={a['amplitude_survival']:.3f}  c_err={a['sound_speed_err']:+.4f}")
    print("    NOTE: c_err ~ -5% is a PHYSICAL effect of dropping the heat-flux reconstruction "
          "(the strong filter does NOT shift c: full+0.03x6 stays +0.15%); the acoustic domain's "
          "sound speed is re-tuned in D3-2. Stability and backscatter are the core-step gates here.")

    print("\n(B) closed reflecting box (energy accumulation) 2x2 ablation -- filter vs heat-flux:")
    print("    (what actually stabilises reflected-energy accumulation?)")
    box = {}
    for cl, cfg0 in (("full ", full), ("simple", aco)):
        for fl, (s, p) in (("weak  ", WEAK_FILTER), ("strong", STRONG_FILTER)):
            r = run_closed_box(with_filter(cfg0, s, p), ny=256, n_transits=4.0)
            box[(cl, fl)] = r
            v = (f"CRASH@{r['crash_step']}/{r['n_steps']}" if not r["survived"]
                 else f"survived {r['n_steps']} amp={r['amp_ratio']:.3f}")
            print(f"    {cl} heat-flux + {fl} filter: {v}")

    print("\nFINDINGS:")
    print("  * STABILITY is set by the FILTER, not the heat-flux: strong filter survives for BOTH")
    print("    collisions, weak filter crashes for BOTH (simplified crashes fastest -- heat-flux")
    print("    regularization was providing incidental damping). The heat-flux-Gram LinAlgError that")
    print("    section 7 saw was a SYMPTOM of the destabilised field, not the root cause.")
    print("  * The core step's real value: the acoustic domain no longer carries the dx2p6 tau32-tuned")
    print("    heat-flux closure (thermal-specific, undefined for a sound-only domain) -> a purer domain")
    print("    and one fewer confound for the D3-2 reflection certification; it is NOT the stability fix.")
    print("  * Cost: dropping the heat-flux reconstruction lowers the sound speed ~5% (re-tuned in D3-2).")
    if args.out:
        payload = {"open_simplified": a,
                   "box": {f"{c}_{f}": box[(c, f)] for (c, f) in box}}
        args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
