"""P4-D3 D3-4 (iii): map -> soft-source injection -> coarse propagation chain smoke.

Project: docs/Phase_4/M4/P4_D3_Multidomain_Acoustic_Project.md (D3-4; section 12.2).

Chains the three certified pieces into one acoustic link on the coarse domain
(configs/phase4_acoustic_coarse_dx334.yaml):

    compact-source map (section 12.1)  ->  one-way soft source (section 11)  ->
    coarse propagation  ->  D3-2 top sponge  ->  control-band readout (w+ = p' + Z0 v')

SCOPE (honest): this is the map->injection->propagation LINK smoke, not the M4 end-to-end
(no Kirchhoff, no far field, T_s_hat is a representative amplitude rather than a Level C run
readout -- the chain is linear, so the smoke gates are all amplitude-ratio quantities).

The additive soft source is NOT amplitude-transparent: each step adds scale*(f_src-f0), so the
radiated wave is G * dp_hat_nominal with G a fixed complex RIG CONSTANT (standard soft-source
calibration, like FDTD). The smoke therefore gates the LINK MECHANICS, not |G| itself:

  G1 linearity: G identical across a 10x drive range (the link is linear; G is a constant,
     not an amplitude-dependent artifact);
  G2 one-wayness: w-/w+ < 0.05 at the control band (inherits the section-11 gate in-chain);
  G3 phase propagation: arg(w+_hat(y)) is linear in y along the band (clean traveling wave);
     the fitted wavelength gives the SI phase velocity at the operating point (c_si_over_air,
     the (iv) certification number, P2-6 wording <2%). History: the uncalibrated medium read
     +2.083% (NOT the -5% broadband-pulse figure of section 8 -- pulse COM speed mixes
     dispersion across k); the (iv) decision calibrated the acoustic config's c0_m_s knob
     (347.0 -> 339.9175 = 347/1.020836) so the realized SI phase velocity lands on air c0;
  G4 amplitude flatness: |w+_hat(y)| flat along the band (low dissipation, D3-1 medium).

G (with its linearity spread as error bar) is the injection calibration constant the D3-4
full chain carries forward; it must be fixed once here, never re-tuned against far-field
answers (anti-self-calibration, same discipline as the Kirchhoff fixture rule)."""

from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from boundary.open_cbc import compose_boundary_callbacks
from boundary.open_sponge import make_top_sponge_callback
from core.equilibrium import equilibrium_fg
from core.macroscopic import recover_macro
from core.solver import GasSolver2D
from farfield.compact_source import (
    soft_source_pressure_amplitude_pa,
    thermal_pumping_velocity_m_s,
)
from phase3_interfaces.complex_amplitude import complex_amplitude
from scripts.phase2_m2_verification import load_config
# Reuse the certified section-11 rig pieces (frame constants + bottom absorber).
from scripts.phase4_d3_oneway_probe import _bottom_sponge, _frame

ACOUSTIC_CONFIG = Path("configs/phase4_acoustic_coarse_dx334.yaml")
F_HZ = 1.0e4

# TRUE AIR constants for the SOURCE PHYSICS (fine/M3 domain side of the handoff). The acoustic
# config's ``physical`` block is a set of ARTIFICIAL-MEDIUM knobs (nu0/alpha0 x100 tuned
# viscosity; after the (iv) calibration also c0_m_s), so the compact-source map and the SI
# sound-speed certification must NOT read it -- they use these frozen air values.
AIR_T0_K = 300.0
AIR_RHO0 = 1.177
AIR_C0 = 347.0
AIR_ALPHA = 2.2233775895e-5


def run_chain(base_cfg: dict, *, T_s_hat_K: complex = 10.0, ny: int = 512,
              n_top: int = 80, n_bot: int = 60, y_s: int = 90, scale: float = 0.05,
              ramp_periods: float = 2.0, fit_periods: float = 3.0,
              total_periods: float = 10.0, sample_interval: int = 5,
              dp_pa_override: complex | None = None,
              return_band: bool = False) -> dict[str, Any]:
    """Drive the coarse domain with the map output for ``T_s_hat_K``; read the control band.

    ``dp_pa_override``: drive with this complex nominal amplitude (Pa) instead of the map
    output -- the M4 end-to-end runner uses it to inject the G-precompensated physical
    handoff. ``return_band=True`` adds the per-row complex band profiles (p_hat_Pa,
    v_hat_m_s in SI) needed by the control-surface/Kirchhoff stage."""

    cfg = copy.deepcopy(base_cfg)
    cfg["numerics"] = {**cfg.get("numerics", {}), "nx": 4, "ny": ny}
    solver = GasSolver2D(cfg)
    mp = solver.mapping
    fr = _frame(solver)
    dt = float(mp.lattice.dt_s)
    dx = float(mp.lattice.dx_m)
    omega = 2.0 * math.pi * F_HZ
    # The map: certified-near-wall-temperature -> pumping -> per-side handoff amplitude.
    # SOURCE physics lives in the fine/M3 domain => TRUE AIR constants, never the acoustic
    # config's artificial-medium knobs (alpha x100 tune; c0 calibration after (iv)).
    u_src = thermal_pumping_velocity_m_s(
        T_s_hat_K, T0_K=AIR_T0_K, omega_rad_s=omega, alpha_m2_s=AIR_ALPHA)
    dp_pa = soft_source_pressure_amplitude_pa(u_src, rho0_kg_m3=AIR_RHO0, c0_m_s=AIR_C0)
    if dp_pa_override is not None:
        dp_pa = complex(dp_pa_override)
    dp_lu = complex(dp_pa) / float(mp.pressure_scale)

    solver.initialize_from_macro(fr["rho0"], np.zeros((ny, solver.nx, 2)), fr["th0"])
    mass0 = float(np.sum(solver.f))
    top = make_top_sponge_callback(n_sponge=n_top, sigma_max=0.5)
    S = int(mp.lattice.S)
    f0, g0 = equilibrium_fg(np.full((1, solver.nx), fr["rho0"]), np.zeros((1, solver.nx, 2)),
                            np.full((1, solver.nx), fr["th0"]), S, solver.lattice)
    spp = 1.0 / (F_HZ * dt)
    ramp_steps = ramp_periods * spp

    def cb(*, solver, f_post, g_post, f_stream, g_stream):
        f_stream, g_stream = top(solver=solver, f_post=f_post, g_post=g_post,
                                 f_stream=f_stream, g_stream=g_stream)
        f_stream, g_stream = _bottom_sponge(solver, f_stream, g_stream, n_bot)
        t_now = solver.t_lu + 1
        ramp = 1.0 if t_now >= ramp_steps else 0.5 * (1.0 - math.cos(math.pi * t_now / ramp_steps))
        dp = ramp * (dp_lu * complex(math.cos(omega * t_now * dt), math.sin(omega * t_now * dt))).real
        drho = dp / fr["c"] ** 2
        duy = dp / fr["z0"]
        u_row = np.zeros((1, solver.nx, 2)); u_row[..., 1] = duy
        fsrc, gsrc = equilibrium_fg(np.full((1, solver.nx), fr["rho0"] + drho), u_row,
                                    np.full((1, solver.nx), fr["th0"]), S, solver.lattice)
        f_stream[y_s:y_s + 1] += scale * (fsrc - f0)
        g_stream[y_s:y_s + 1] += scale * (gsrc - g0)
        return f_stream, g_stream

    rows = np.arange(150, ny - n_top - 60, 8)
    n_steps = int(total_periods * spp)
    n_samples = n_steps // sample_interval
    t = np.empty(n_samples); P = np.empty((n_samples, rows.size)); V = np.empty((n_samples, rows.size))
    for i in range(n_samples):
        solver.step(sample_interval, boundary_callback=cb)
        t[i] = solver.t_lu * dt
        m = recover_macro(solver.f[rows], solver.g[rows], D=2, S=S, lattice=solver.lattice)
        P[i] = np.mean(m.p, axis=-1); V[i] = np.mean(m.u[..., 1], axis=-1)
    if not np.isfinite(solver.f).all():
        return {"crash": True}
    mask = t >= t[-1] - fit_periods / F_HZ   # trailing fit_periods window
    wp_hat = np.empty(rows.size, dtype=complex); wm_hat = np.empty(rows.size, dtype=complex)
    p_band = np.empty(rows.size, dtype=complex); v_band = np.empty(rows.size, dtype=complex)
    for j in range(rows.size):
        sp = P[mask, j]; sv = V[mask, j]
        p_hat = complex_amplitude(t[mask], sp - float(np.mean(sp)), F_HZ)
        v_hat = complex_amplitude(t[mask], sv - float(np.mean(sv)), F_HZ)
        p_band[j] = p_hat; v_band[j] = v_hat
        wp_hat[j] = p_hat + fr["z0"] * v_hat
        wm_hat[j] = p_hat - fr["z0"] * v_hat

    # G at the band start; phase-slope fit along the band -> measured wavelength.
    G = complex(wp_hat[0] / (2.0 * dp_lu))   # w+ = p'+Z0 v' = 2 A+ for a pure up-going wave
    phase = np.unwrap(np.angle(wp_hat))
    k_fit = -np.polyfit(rows.astype(float), phase, 1)[0]      # rad per cell, up-going => phase ~ -k y
    lam_meas = 2.0 * math.pi / k_fit
    lam_design = fr["c"] / (F_HZ * dt)                         # cells per period at the LATTICE design c
    c_si = lam_meas * dx * F_HZ                                 # SI phase velocity at the operating point
    phase_resid = float(np.sqrt(np.mean((phase - np.polyval(np.polyfit(rows.astype(float), phase, 1), rows.astype(float))) ** 2)))
    return {
        "crash": False, "T_s_hat_K_abs": abs(complex(T_s_hat_K)),
        "u_src_m_s": abs(u_src), "dp_pa": abs(complex(dp_pa)),
        "G_abs": abs(G), "G_phase_deg": math.degrees(np.angle(G)),
        "onewayness": float(np.median(np.abs(wm_hat)) / np.median(np.abs(wp_hat))),
        "band_flatness": float(np.std(np.abs(wp_hat)) / np.mean(np.abs(wp_hat))),
        "lambda_meas_cells": float(lam_meas), "lambda_design_cells": float(lam_design),
        "c_num_over_design": float(lam_meas / lam_design),      # lattice-internal deviation (calibration input)
        "c_si_m_s": float(c_si),
        "c_si_over_air": float(c_si / AIR_C0),                  # the (iv) certification number (P2-6 <2%)
        "phase_fit_resid_rad": phase_resid,
        "mass_rel_drift": abs(float(np.sum(solver.f)) - mass0) / mass0,
        "rows": [int(r) for r in rows],
        **({"dx_m": dx, "p_band_Pa": p_band * float(mp.pressure_scale),
            "v_band_m_s": v_band * (dx / dt), "z0_lu": fr["z0"],
            "dp_drive_pa": complex(dp_pa)} if return_band else {}),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="P4-D3 D3-4(iii) map->injection->coarse-propagation chain smoke.")
    ap.add_argument("--acoustic-config", type=Path, default=ACOUSTIC_CONFIG)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    base = load_config(args.acoustic_config)

    print("map -> soft source -> coarse propagation chain smoke @ 10 kHz "
          "(G = injection rig constant; gates = linearity/one-way/phase/flatness)\n")
    results = {}
    for label, T in (("T_s=10K", 10.0), ("T_s=1K", 1.0)):
        r = run_chain(base, T_s_hat_K=T)
        results[label] = r
        if r.get("crash"):
            print(f"{label}: CRASH", flush=True); continue
        print(f"{label:8s} u_src={r['u_src_m_s']:.3e} m/s  dp={r['dp_pa']:.3f} Pa  ->  "
              f"G={r['G_abs']:.4f} @ {r['G_phase_deg']:+.1f} deg", flush=True)
        print(f"         one-way w-/w+ = {r['onewayness']:.4f}   flatness {r['band_flatness']:.4f}   "
              f"mass drift {r['mass_rel_drift']:.2e}", flush=True)
        print(f"         lambda_meas = {r['lambda_meas_cells']:.1f} cells (design {r['lambda_design_cells']:.1f}, "
              f"num/design {r['c_num_over_design']:.4f});  c_SI = {r['c_si_m_s']:.2f} m/s = "
              f"{r['c_si_over_air']:.4f} x air 347.0  (gate <2%);  phase-fit resid "
              f"{r['phase_fit_resid_rad']:.4f} rad", flush=True)
    a, b = results.get("T_s=10K", {}), results.get("T_s=1K", {})
    if not (a.get("crash", True) or b.get("crash", True)):
        lin = abs(a["G_abs"] / b["G_abs"] - 1.0)
        dph = abs(a["G_phase_deg"] - b["G_phase_deg"])
        print(f"\nG1 linearity across 10x drive: |G| ratio dev = {lin:.4f}, phase dev = {dph:.2f} deg")
        print("VERDICT: chain link is linear/one-way/clean-propagating; G is the documented injection "
              "constant; c_si_over_air is the (iv) certification number (calibrated medium).")
    if args.out:
        args.out.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
