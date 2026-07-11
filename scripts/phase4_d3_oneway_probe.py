"""P4-D3 D3-3 (one-way reframe): non-reflecting soft-source injection into the coarse acoustic domain.

Project: docs/Phase_4/M4/P4_D3_Multidomain_Acoustic_Project.md (D3-3; section 11).

The two-way population-exchange interface reflects ~0.5 (section 10, intrinsic sharp-patch impedance
mismatch). The one-way reframe (user decision 2026-07-08) sidesteps it: the fine near-field drives
the coarse domain ONE-WAY (radiation condition -- the far field does not react back on the source),
as in hybrid CFD / FW-H acoustics. The coupling surface becomes a NON-REFLECTING soft-source
injection at the coarse bottom, so the near-field signal enters without the boundary contaminating
the far field. D3-2 already certified the sponge is non-reflecting (|R|=0.0004); the new piece is
the source.

Design: coarse acoustic domain (simplified collision), top sponge (far-field open), bottom sponge
(absorb), and an ADDITIVE upward-characteristic soft source at a source plane just above the bottom
sponge. Additive (not Dirichlet) => the coarse's OWN downward waves pass through the source row into
the bottom sponge (non-reflecting), while the source injects a clean upward wave (w- = p' - Z0 v' ~ 0).

Gates (D3-3 one-way):
  * run_injection: injected monochromatic wave is clean upward -- one-wayness w-/w+ < 0.05;
  * run_bottom_reflection: a downward test pulse at the injection boundary reflects below gate
    (|R| < 0.05), with a rigid-bottom control reading O(1) (the rig sees reflection -> non-degenerate).
Amplitude CALIBRATION (radiated vs driven) is deferred to D3-4; here the gates are cleanliness +
non-reflection + stability.

Diagnostic; reads configs/phase4_acoustic_coarse_dx334.yaml; frozen configs untouched."""

from __future__ import annotations

import argparse
import copy
import math
from pathlib import Path
from typing import Any

import numpy as np
from numpy.linalg import LinAlgError

from core.equilibrium import equilibrium_fg
from core.macroscopic import recover_macro
from core.solver import GasSolver2D
from boundary.open_sponge import make_top_sponge_callback
from scripts.phase2_m2_verification import load_config

ACOUSTIC_CONFIG = Path("configs/phase4_acoustic_coarse_dx334.yaml")
LAMBDA_10K_M = 347.0 / 1.0e4


def _frame(s: GasSolver2D) -> dict[str, float]:
    th0 = float(s.mapping.theta_ref_lu); rho0 = float(s.mapping.lattice.rho_ref_lu)
    c = math.sqrt(1.4 * th0)
    return {"rho0": rho0, "c": c, "z0": rho0 * c, "pref": rho0 * th0, "th0": th0}


def _bottom_sponge(solver, f_stream, g_stream, n, sigma_max=0.5, p=2.0):
    S = int(solver.mapping.lattice.S); D = int(solver.mapping.lattice.D)
    rho0 = float(solver.mapping.lattice.rho_ref_lu); th0 = float(solver.mapping.theta_ref_lu)
    xi = np.arange(n, dtype=float) / (n - 1)
    oms = (1.0 - sigma_max * (1.0 - xi) ** p).reshape(n, 1); sl = slice(0, n)
    m = recover_macro(f_stream[sl], g_stream[sl], D=D, S=S, lattice=solver.lattice)
    feq, geq = equilibrium_fg(m.rho, m.u, m.theta, S, solver.lattice)
    feq_d, geq_d = equilibrium_fg(rho0 + oms * (m.rho - rho0), oms[:, :, None] * m.u,
                                  th0 + oms * (m.theta - th0), S, solver.lattice)
    f_stream[sl] = feq_d + oms[:, :, None] * (f_stream[sl] - feq)
    g_stream[sl] = geq_d + oms[:, :, None] * (g_stream[sl] - geq)
    return f_stream, g_stream


def _make_bottom_rigid_lid(solver):
    cy = solver.lattice.c[:, 1]; opp = solver.lattice.opposite
    up = np.where(cy > 0)[0]

    def cb(*, solver, f_post, g_post, f_stream, g_stream):
        for a in up:  # bottom wall: incoming-from-below <- reflect the down-going post-collision pops
            f_stream[0, :, a] = f_post[0, :, opp[a]]
            g_stream[0, :, a] = g_post[0, :, opp[a]]
        return f_stream, g_stream

    return cb


def run_injection(base: dict, *, ny: int = 512, n_abs: int = 60, y_s: int = 90,
                  period: int = 400, eps: float = 1e-3, scale: float = 0.05,
                  n_periods: int = 8) -> dict[str, Any]:
    """Monochromatic soft-source drive; measure injected upward amplitude + one-wayness w-/w+."""

    s = GasSolver2D({**copy.deepcopy(base), "numerics": {**base["numerics"], "nx": 4, "ny": ny}})
    fr = _frame(s); S = s.mapping.lattice.S
    s.initialize_from_macro(fr["rho0"], np.zeros((ny, s.nx, 2)), fr["th0"])
    top = make_top_sponge_callback(n_sponge=n_abs)
    om = 2 * math.pi / period
    probe = int(0.55 * ny)
    f0, g0 = equilibrium_fg(np.full((1, s.nx), fr["rho0"]), np.zeros((1, s.nx, 2)),
                            np.full((1, s.nx), fr["th0"]), S, s.lattice)

    def cb(*, solver, f_post, g_post, f_stream, g_stream):
        f_stream, g_stream = top(solver=solver, f_post=f_post, g_post=g_post, f_stream=f_stream, g_stream=g_stream)
        f_stream, g_stream = _bottom_sponge(solver, f_stream, g_stream, n_abs)
        dp = eps * fr["pref"] * math.sin(om * (solver.t_lu + 1))
        drho = dp / fr["c"] ** 2; duy = dp / fr["z0"]
        u_src = np.zeros((1, solver.nx, 2)); u_src[..., 1] = duy
        fsrc, gsrc = equilibrium_fg(np.full((1, solver.nx), fr["rho0"] + drho), u_src,
                                    np.full((1, solver.nx), fr["th0"]), S, solver.lattice)
        f_stream[y_s:y_s + 1] += scale * (fsrc - f0); g_stream[y_s:y_s + 1] += scale * (gsrc - g0)
        return f_stream, g_stream

    pser, vser = [], []
    for _ in range(int(n_periods * period)):
        try:
            s.step(1, boundary_callback=cb)
        except LinAlgError:
            return {"crash": True}
        if not np.isfinite(s.f).all():
            return {"crash": True}
        m = recover_macro(s.f[probe:probe + 1], s.g[probe:probe + 1], D=2, S=3, lattice=s.lattice)
        pser.append(float(np.mean(m.p) - fr["pref"])); vser.append(float(np.mean(m.u[..., 1])))
    tail = slice(-3 * period, None)
    pp = np.array(pser[tail]); v = np.array(vser[tail])
    wp = pp + fr["z0"] * v; wm = pp - fr["z0"] * v
    wp_amp = float(np.sqrt(np.mean(wp ** 2))) * math.sqrt(2)
    wm_amp = float(np.sqrt(np.mean(wm ** 2))) * math.sqrt(2)
    return {"crash": False, "wplus_amp_rel": wp_amp / fr["pref"],
            "onewayness": wm_amp / max(wp_amp, 1e-300)}


def run_bottom_reflection(base: dict, *, ny: int = 512, n_abs: int = 60, bottom: str = "sponge") -> dict[str, Any]:
    """Downward test pulse at the injection boundary; |R| = peak reflected(w+)/incident(w-).

    ``bottom`` in {"sponge" (the injection boundary, source off), "rigid" (non-degeneracy control)}."""

    s = GasSolver2D({**copy.deepcopy(base), "numerics": {**base["numerics"], "nx": 4, "ny": ny}})
    fr = _frame(s)
    boundary = n_abs if bottom == "sponge" else 0
    y0 = ny * 0.78; sigma = max(8.0, (LAMBDA_10K_M / float(base["lattice"]["dx_m"])) / 6.0)
    probe = int(0.58 * ny)
    top = make_top_sponge_callback(n_sponge=n_abs)
    rigid = _make_bottom_rigid_lid(s) if bottom == "rigid" else None
    y = np.arange(ny, dtype=float)[:, None] * np.ones((1, s.nx))
    pp0 = 1e-3 * fr["pref"] * np.exp(-((y - y0) ** 2) / (2.0 * sigma ** 2))
    u = np.zeros((ny, s.nx, 2)); u[..., 1] = -pp0 / fr["z0"]  # DOWNWARD: w- only
    rho = fr["rho0"] + pp0 / fr["c"] ** 2
    s.initialize_from_macro(rho, u, (fr["pref"] + pp0) / rho)

    def cb(*, solver, f_post, g_post, f_stream, g_stream):
        f_stream, g_stream = top(solver=solver, f_post=f_post, g_post=g_post, f_stream=f_stream, g_stream=g_stream)
        if bottom == "sponge":
            f_stream, g_stream = _bottom_sponge(solver, f_stream, g_stream, n_abs)
        else:
            f_stream, g_stream = rigid(solver=solver, f_post=f_post, g_post=g_post, f_stream=f_stream, g_stream=g_stream)
        return f_stream, g_stream

    n_steps = int(2.2 * ny / fr["c"]); down_time = (y0 - boundary) / fr["c"]
    wm_peak = wp_after = 0.0; check = max(1, n_steps // 120)
    for st in range(n_steps):
        try:
            s.step(1, boundary_callback=cb)
        except LinAlgError:
            return {"bottom": bottom, "crash_step": st, "R_abs": None}
        if st % check == 0:
            if not np.isfinite(s.f).all():
                return {"bottom": bottom, "crash_step": st, "R_abs": None}
            m = recover_macro(s.f[probe:probe + 1], s.g[probe:probe + 1], D=2, S=3, lattice=s.lattice)
            pp = float(np.mean(m.p) - fr["pref"]); v = float(np.mean(m.u[..., 1]))
            wp, wm = pp + fr["z0"] * v, pp - fr["z0"] * v
            wm_peak = max(wm_peak, abs(wm))
            if st > down_time:
                wp_after = max(wp_after, abs(wp))
    return {"bottom": bottom, "crash_step": None, "R_abs": float(wp_after / max(wm_peak, 1e-300))}


def evaluate_oneway_gate(injection: dict, rigid: dict, sponge: dict) -> bool:
    return bool(
        not injection.get("crash", True)
        and injection["onewayness"] < 0.05
        and rigid.get("crash_step") is None
        and sponge.get("crash_step") is None
        and rigid.get("R_abs") is not None
        and rigid["R_abs"] > 0.3
        and sponge.get("R_abs") is not None
        and sponge["R_abs"] < 0.05
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="P4-D3 D3-3 one-way soft-source injection (diagnostic).")
    ap.add_argument("--acoustic-config", type=Path, default=ACOUSTIC_CONFIG)
    ap.add_argument("--ny", type=int, default=512)
    args = ap.parse_args()
    base = load_config(args.acoustic_config)

    print("(1) soft-source injection: clean upward wave?")
    inj = run_injection(base, ny=args.ny)
    if inj.get("crash"):
        print("    CRASH")
    else:
        print(f"    injected w+ amp = {inj['wplus_amp_rel']:.3e} (rel pref);  one-wayness w-/w+ = "
              f"{inj['onewayness']:.4f}  (gate <0.05)")

    print("\n(2) injection-boundary non-reflection (downward test pulse) + rigid control:")
    reflection = {}
    for bottom in ("rigid", "sponge"):
        r = run_bottom_reflection(base, ny=args.ny, bottom=bottom)
        reflection[bottom] = r
        v = f"CRASH@{r['crash_step']}" if r["R_abs"] is None else f"|R|={r['R_abs']:.4f}"
        print(f"    bottom={bottom:7s} {v}")

    passed = evaluate_oneway_gate(inj, reflection["rigid"], reflection["sponge"])
    print(f"\nVERDICT: {'PASSED' if passed else 'FAILED'} -- one-wayness, sponge reflection, and "
          "rigid non-degeneracy gates evaluated.")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
