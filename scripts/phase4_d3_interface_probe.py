"""P4-D3 D3-3 minimal interface fixture (life/death knife). DIAGNOSTIC.

Project: docs/Phase_4/M4/P4_D3_Multidomain_Acoustic_Project.md (D3-3; section 10).

Question: can a fine<->coarse grid-refinement interface pass a normal-incidence acoustic wave
with |R_iface| < 0.05 (and flux conservation)? Two GasSolver2D (fine below, coarse above), both
the simplified acoustic collision, coupled at the interface; a pulse crosses fine->coarse and
|R_iface| = peak|w-|/peak|w+| at a fine probe.

TWO findings (section 10):

1. STABILITY (solved). A naive coupling driven through the monolithic solver.step() is
   explosively unstable (rest-state seed grows ~1e6x): the culprit is the 1-step temporal LAG
   (each domain streams using the neighbour's PREVIOUS post-collision populations). A custom
   LAG-FREE stepper -- collide BOTH domains, then exchange their SAME-TIME post-collision
   populations, then stream+filter -- plus FAR-END absorbers (each periodic domain otherwise
   wraps its interface edge back into its far end and re-injects) makes the rest state STABLE
   (seed decays). run_rest_stability() reproduces the ladder.

2. REFLECTION (fails the gate). Even with stability solved, the sharp population-patch interface
   REFLECTS ~0.5 of the wave at ratio 1 (exact copy, no refinement) vs a single-domain baseline
   floor ~0.009 -- an intrinsic impedance mismatch of the sharp patch, not the refinement and not
   the measurement (the single-domain baseline is clean). Transmission is only ~5%.
   |R_iface| ~ 0.5 >> gate 0.05. run_interface_reflection() vs run_single_baseline() reproduces it.

VERDICT: the minimal fixture judges |R_iface| ~ 0.5, NOT compressible to the gate with this naive
sharp-interface coupling. Per project section 4, D3 hangs unless a better coupling passes: the
standard fix is an OVERLAP-region continuous-streaming refinement coupling (not a sharp patch), or
a one-way near->far reframe. Decision recorded in section 10.

DIAGNOSTIC only; frozen configs untouched. Slow (coupled runs are O(1e3-1e4) coupled steps);
default sizes are modest -- the headline numbers hold at ny 512/1024 (docstring of section 10)."""

from __future__ import annotations

import argparse
import copy
import math
from pathlib import Path
from typing import Any

import numpy as np
from numpy.linalg import LinAlgError

from core.collision_smrt import collide_fg
from core.equilibrium import equilibrium_fg
from core.macroscopic import recover_macro
from core.solver import GasSolver2D, conservative_biharmonic_filter
from core.streaming import pull_stream_fg
from boundary.open_sponge import make_top_sponge_callback
from scripts.phase2_m2_verification import load_config

ACOUSTIC_CONFIG = Path("configs/phase4_acoustic_coarse_dx334.yaml")
DT_OVER_DX = 1.95881e-9 / 2.61175e-6
LAMBDA_10K_M = 347.0 / 1.0e4


def _frame(s: GasSolver2D) -> dict[str, float]:
    th0 = float(s.mapping.theta_ref_lu); rho0 = float(s.mapping.lattice.rho_ref_lu)
    c = math.sqrt(1.4 * th0)
    return {"rho0": rho0, "c": c, "z0": rho0 * c, "pref": rho0 * th0, "th0": th0}


def _coarse_cfg(base: dict, N: int) -> dict:
    cfg = copy.deepcopy(base); dxf = float(base["lattice"]["dx_m"])
    cfg["lattice"]["dx_m"] = N * dxf
    cfg["lattice"]["dt_s"] = N * dxf * DT_OVER_DX
    cfg["physical"]["nu0_m2_s"] = float(base["physical"]["nu0_m2_s"]) * N
    cfg["physical"]["alpha0_m2_s"] = float(base["physical"]["alpha0_m2_s"]) * N
    return cfg


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


def run_rest_stability(base: dict, mode: str, ny: int = 256, nsteps: int = 3000,
                       seed: float = 1e-8, nsp: int = 40) -> dict[str, Any]:
    """Rest-state seed growth for coupling ``mode`` in {lagged, lagfree, lagfree_farend}."""

    A = GasSolver2D({**copy.deepcopy(base), "numerics": {**base["numerics"], "nx": 4, "ny": ny}})
    B = GasSolver2D({**copy.deepcopy(base), "numerics": {**base["numerics"], "nx": 4, "ny": ny}})
    lat = A.lattice
    th0 = float(A.mapping.theta_ref_lu); rho0 = float(A.mapping.lattice.rho_ref_lu)
    rng = np.random.default_rng(0)
    A.initialize_from_macro(rho0 * (1 + seed * rng.standard_normal((ny, A.nx))), np.zeros((ny, A.nx, 2)), th0)
    B.initialize_from_macro(rho0, np.zeros((ny, B.nx, 2)), th0)
    cy = lat.c[:, 1].astype(int); down = np.where(cy < 0)[0]; up = np.where(cy > 0)[0]
    strength, passes = A.high_wavenumber_filter_strength, A.high_wavenumber_filter_passes
    B_top = make_top_sponge_callback(n_sponge=nsp)
    amp0 = seed * rho0

    def flt(x):
        for _ in range(passes):
            x = conservative_biharmonic_filter(x, strength, None)
        return x

    buf = {k: np.zeros((3, A.nx, lat.q)) for k in ("aF", "aG", "bF", "bG")}

    def lagged_cbs():
        def A_cb(*, solver, f_post, g_post, f_stream, g_stream):
            buf["aF"][:] = f_post[ny-1:ny-4:-1]; buf["aG"][:] = g_post[ny-1:ny-4:-1]
            for a in down:
                k = -cy[a]-1; f_stream[ny-1, :, a] = buf["bF"][k, :, a]; g_stream[ny-1, :, a] = buf["bG"][k, :, a]
            return f_stream, g_stream
        def B_cb(*, solver, f_post, g_post, f_stream, g_stream):
            buf["bF"][:] = f_post[0:3]; buf["bG"][:] = g_post[0:3]
            for a in up:
                k = cy[a]-1; f_stream[0, :, a] = buf["aF"][k, :, a]; g_stream[0, :, a] = buf["aG"][k, :, a]
            return f_stream, g_stream
        return A_cb, B_cb

    try:
        if mode == "lagged":
            A_cb, B_cb = lagged_cbs()
            for s in range(nsteps):
                A.step(1, boundary_callback=A_cb); B.step(1, boundary_callback=B_cb)
                if not (np.isfinite(A.f).all() and np.isfinite(B.f).all()):
                    return {"mode": mode, "crash": s, "growth": None}
        else:
            farend = (mode == "lagfree_farend")
            for s in range(nsteps):
                fAp, gAp = collide_fg(A.f, A.g, A.mapping, lattice=lat)
                fBp, gBp = collide_fg(B.f, B.g, B.mapping, lattice=lat)
                fAs, gAs = pull_stream_fg(fAp, gAp, lattice=lat, y_axis=0, x_axis=1)
                fBs, gBs = pull_stream_fg(fBp, gBp, lattice=lat, y_axis=0, x_axis=1)
                for a in down:
                    k = -cy[a]-1; fAs[ny-1, :, a] = fBp[k, :, a]; gAs[ny-1, :, a] = gBp[k, :, a]
                for a in up:
                    k = cy[a]-1; fBs[0, :, a] = fAp[ny-1-k, :, a]; gBs[0, :, a] = gAp[ny-1-k, :, a]
                if farend:
                    fAs, gAs = _bottom_sponge(A, fAs, gAs, nsp)
                    fBs, gBs = B_top(solver=B, f_post=fBp, g_post=gBp, f_stream=fBs, g_stream=gBs)
                A.f, A.g = flt(fAs), flt(gAs); B.f, B.g = flt(fBs), flt(gBs)
                if not (np.isfinite(A.f).all() and np.isfinite(B.f).all()):
                    return {"mode": mode, "crash": s, "growth": None}
    except LinAlgError:
        return {"mode": mode, "crash": "LinAlgError", "growth": None}
    mA = A.get_macro(); mB = B.get_macro()
    amp = max(float(np.max(np.abs(mA.rho - rho0))), float(np.max(np.abs(mB.rho - rho0))))
    return {"mode": mode, "crash": None, "growth": amp / amp0}


def _lagfree_farend_step(fine, coarse, N, cy, down, up, strf, pf, strc, pc,
                         r_c2f, r_f2c, Sf, Sc, latf, latc, ny_f, B_top, nsp):
    def fltf(x):
        for _ in range(pf):
            x = conservative_biharmonic_filter(x, strf, None)
        return x
    def fltc(x):
        for _ in range(pc):
            x = conservative_biharmonic_filter(x, strc, None)
        return x
    fcp, gcp = collide_fg(coarse.f, coarse.g, coarse.mapping, lattice=latc)
    mc = recover_macro(fcp[0:3], gcp[0:3], D=2, S=Sc, lattice=latc)
    feqc, geqc = equilibrium_fg(mc.rho, mc.u, mc.theta, Sc, latc)
    fghost_c = feqc + r_c2f * (fcp[0:3] - feqc); gghost_c = geqc + r_c2f * (gcp[0:3] - geqc)
    fcs, gcs = pull_stream_fg(fcp, gcp, lattice=latc, y_axis=0, x_axis=1)
    acc_f = np.zeros((3, fine.nx, latf.q)); acc_g = np.zeros((3, fine.nx, latf.q))
    for _ in range(N):
        ffp, gfp = collide_fg(fine.f, fine.g, fine.mapping, lattice=latf)
        ffs, gfs = pull_stream_fg(ffp, gfp, lattice=latf, y_axis=0, x_axis=1)
        for a in down:
            k = -cy[a]-1; ffs[ny_f-1, :, a] = fghost_c[k, :, a]; gfs[ny_f-1, :, a] = gghost_c[k, :, a]
        ffs, gfs = _bottom_sponge(fine, ffs, gfs, nsp)
        fine.f, fine.g = fltf(ffs), fltf(gfs)
        acc_f += ffp[ny_f-1:ny_f-4:-1]; acc_g += gfp[ny_f-1:ny_f-4:-1]
    ftp, gtp = acc_f / N, acc_g / N
    mf = recover_macro(ftp, gtp, D=2, S=Sf, lattice=latf)
    feqf, geqf = equilibrium_fg(mf.rho, mf.u, mf.theta, Sf, latf)
    fghost_f = feqf + r_f2c * (ftp - feqf); gghost_f = geqf + r_f2c * (gtp - geqf)
    for a in up:
        k = cy[a]-1; fcs[0, :, a] = fghost_f[k, :, a]; gcs[0, :, a] = gghost_f[k, :, a]
    fcs, gcs = B_top(solver=coarse, f_post=fcp, g_post=gcp, f_stream=fcs, g_stream=gcs)
    coarse.f, coarse.g = fltc(fcs), fltc(gcs)


def run_interface_reflection(base: dict, N: int, ny_f: int = 512, nsp: int = 60) -> dict[str, Any]:
    """Coupled pulse crossing fine->coarse; |R_iface| at a fine probe (stable lag-free recipe)."""

    ny_c = ny_f // N
    fine = GasSolver2D({**copy.deepcopy(base), "numerics": {**base["numerics"], "nx": 4, "ny": ny_f}})
    coarse = GasSolver2D({**_coarse_cfg(base, N), "numerics": {**base["numerics"], "nx": 4, "ny": ny_c}})
    latf, latc = fine.lattice, coarse.lattice
    frf = _frame(fine); frc = _frame(coarse)
    cy = latf.c[:, 1].astype(int); down = np.where(cy < 0)[0]; up = np.where(cy > 0)[0]
    Sf, Sc = fine.mapping.lattice.S, coarse.mapping.lattice.S
    tau_f, tau_c = float(fine.mapping.tau21), float(coarse.mapping.tau21)
    r_c2f = (tau_f-0.5)/(tau_c-0.5); r_f2c = (tau_c-0.5)/(tau_f-0.5)
    strf, pf = fine.high_wavenumber_filter_strength, fine.high_wavenumber_filter_passes
    strc, pc = coarse.high_wavenumber_filter_strength, coarse.high_wavenumber_filter_passes
    B_top = make_top_sponge_callback(n_sponge=nsp)

    y0, sig = ny_f * 0.30, max(8.0, (LAMBDA_10K_M / float(base["lattice"]["dx_m"])) / 6.0)
    probe = int(0.55 * ny_f)
    y = np.arange(ny_f, dtype=float)[:, None] * np.ones((1, fine.nx))
    pp0 = 1e-3 * frf["pref"] * np.exp(-((y - y0) ** 2) / (2 * sig ** 2))
    u = np.zeros((ny_f, fine.nx, 2)); u[..., 1] = pp0 / frf["z0"]; rho = frf["rho0"] + pp0 / frf["c"] ** 2
    fine.initialize_from_macro(rho, u, (frf["pref"] + pp0) / rho)
    coarse.initialize_from_macro(frc["rho0"], np.zeros((ny_c, coarse.nx, 2)), frc["th0"])

    n_coarse = int(2.0 * ny_f / frf["c"] / N)
    wp_peak = wm_after = 0.0
    for cs in range(n_coarse):
        try:
            _lagfree_farend_step(fine, coarse, N, cy, down, up, strf, pf, strc, pc,
                                 r_c2f, r_f2c, Sf, Sc, latf, latc, ny_f, B_top, nsp)
        except LinAlgError:
            return {"N": N, "crash": cs, "R_abs": None, "trans_amp": None}
        if not (np.isfinite(fine.f).all() and np.isfinite(coarse.f).all()):
            return {"N": N, "crash": cs, "R_abs": None, "trans_amp": None}
        mp = recover_macro(fine.f[probe:probe+1], fine.g[probe:probe+1], D=2, S=Sf, lattice=latf)
        pp = float(np.mean(mp.p) - frf["pref"]); v = float(np.mean(mp.u[..., 1]))
        wp, wm = pp + frf["z0"] * v, pp - frf["z0"] * v
        wp_peak = max(wp_peak, abs(wp))
        if cs > 0.45 * n_coarse:
            wm_after = max(wm_after, abs(wm))
    mc = recover_macro(coarse.f, coarse.g, D=2, S=Sc, lattice=latc)
    trans = float(np.max(np.abs(np.mean(mc.p, axis=-1) - frc["pref"]))) / (1e-3 * frf["pref"])
    return {"N": N, "crash": None, "R_abs": wm_after / max(wp_peak, 1e-300), "trans_amp": trans}


def run_single_baseline(base: dict, ny: int = 512, nsp: int = 60) -> dict[str, Any]:
    """Single domain (no interface): |R| floor with the SAME probe/pulse/sponge measurement."""

    s = GasSolver2D({**copy.deepcopy(base), "numerics": {**base["numerics"], "nx": 4, "ny": ny}})
    fr = _frame(s)
    y0, sig = ny * 0.30, max(8.0, (LAMBDA_10K_M / float(base["lattice"]["dx_m"])) / 6.0)
    probe = int(0.55 * ny)
    y = np.arange(ny, dtype=float)[:, None] * np.ones((1, s.nx))
    pp0 = 1e-3 * fr["pref"] * np.exp(-((y - y0) ** 2) / (2 * sig ** 2))
    u = np.zeros((ny, s.nx, 2)); u[..., 1] = pp0 / fr["z0"]; rho = fr["rho0"] + pp0 / fr["c"] ** 2
    s.initialize_from_macro(rho, u, (fr["pref"] + pp0) / rho)
    top = make_top_sponge_callback(n_sponge=nsp)
    def cb(*, solver, f_post, g_post, f_stream, g_stream):
        f_stream, g_stream = top(solver=solver, f_post=f_post, g_post=g_post, f_stream=f_stream, g_stream=g_stream)
        return _bottom_sponge(solver, f_stream, g_stream, nsp)
    n = int(2.0 * ny / fr["c"]); wp_peak = wm_after = 0.0
    for cs in range(n):
        s.step(1, boundary_callback=cb)
        m = recover_macro(s.f[probe:probe+1], s.g[probe:probe+1], D=2, S=3, lattice=s.lattice)
        pp = float(np.mean(m.p) - fr["pref"]); v = float(np.mean(m.u[..., 1]))
        wp_peak = max(wp_peak, abs(pp + fr["z0"] * v))
        if cs > 0.45 * n:
            wm_after = max(wm_after, abs(pp - fr["z0"] * v))
    return {"R_abs": wm_after / max(wp_peak, 1e-300)}


def main() -> None:
    ap = argparse.ArgumentParser(description="P4-D3 D3-3 minimal interface fixture (diagnostic).")
    ap.add_argument("--acoustic-config", type=Path, default=ACOUSTIC_CONFIG)
    ap.add_argument("--ny", type=int, default=256)
    args = ap.parse_args()
    base = load_config(args.acoustic_config)

    print("(1) rest-state stability ladder (coupling feedback vs the lag; ny=%d):" % args.ny)
    for mode in ("lagged", "lagfree", "lagfree_farend"):
        r = run_rest_stability(base, mode, ny=args.ny)
        v = f"CRASH@{r['crash']}" if r["growth"] is None else f"seed x{r['growth']:.2e}"
        print(f"    {mode:16s} {v}  ({'STABLE' if (r['growth'] is not None and r['growth'] < 3) else 'UNSTABLE'})")

    print("\n(2) interface reflection vs single-domain baseline (ny=%d):" % args.ny)
    base_r = run_single_baseline(base, ny=args.ny)["R_abs"]
    print(f"    single-domain baseline  |R|={base_r:.4f}  (measurement floor)")
    for N in (1, 2):
        r = run_interface_reflection(base, N, ny_f=args.ny)
        if r["R_abs"] is None:
            print(f"    coupled ratio {N}         CRASH@{r['crash']}")
        else:
            print(f"    coupled ratio {N}         |R_iface|={r['R_abs']:.4f}  transmitted_amp={r['trans_amp']:.3f}")

    print("\nVERDICT: stability is solvable (lag-free + far-end absorbers -> rest decays), but the sharp "
          "population-patch interface reflects ~0.5 (>> gate 0.05, >> baseline). D3-3 needs an "
          "overlap-region continuous-streaming coupling or a one-way reframe (project section 10).")


if __name__ == "__main__":
    main()
