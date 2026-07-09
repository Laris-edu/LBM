"""P4-D3 D3-4 first knife: near-field SOURCE EXTRACTION quality on the frozen M3 stack.

Project: docs/Phase_4/M4/P4_D3_Multidomain_Acoustic_Project.md (D3-4; section 12).

The one-way architecture (section 11) needs the fine/M3 domain to hand the coarse acoustic
domain its EMISSION. This probe measured, in three rigs, whether that handoff can be extracted
-- and the answer reshapes D3-4 (all numbers 40 kHz shakedown on dx2p6 unless noted; 40 kHz is
OFF the (tau,k) calibration point, used for mechanics only):

RIG 1 -- run_closed_profile: the M3-NATIVE closed column (thermal_grad wall + y-periodic wrap,
frozen stack, no new boundaries). Result: the in-layer thermoacoustic pumping is REAL and hits
the analytic anchor -- peak in-layer |v_hat| = 1.03 x u_ac = Omega delta_T/sqrt(2) (T_hat/T0);
the temperature profile is a textbook decaying thermal wave; above the layer the velocity
collapses to a small anti-phase residual and |p_hat| is a uniform closed-box compression mode
(the reactive gamma p0 xi / L estimate lands within x0.6-0.7 of it). Everything is consistent:
THE SOURCE PHYSICS OF THE FROZEN STACK IS RIGHT, but a closed rig measures the box response,
so the naive "linear band fit -> u_src" compact-source extraction of an earlier revision of
this probe was model-invalid (the wrapped wall image pumps from both ends) and is deleted.

RIG 2 -- run_radiation_loaded(corrections_on=True): fine column radiating into a D3-2 style
perturbation-damping top sponge (anechoic load). The load itself is PERFECT -- the control band
sees |Z| = p_hat/v_hat = 1.005-1.009 x Z0 at -0.3 deg with 0.3-0.9% band flatness -- but the
amplitude is 31 x u_ac at 40 kHz and 57 x u_ac at 10 kHz (the calibrated gate frequency; the
injected absolute amplitude is roughly frequency-flat while u_ac ~ sqrt(Omega), so the swamping
worsens at 10 kHz): the volume-injection floor (global FFT corrections x boundary seams, the
P4-1 root cause) injects an outgoing wave that rides the same Z0 relation and SWAMPS the
physical emission. Extraction from a RADIATING fine domain is therefore dead -- a much stronger
form of the P4-1 obstacle (there it capped |R| at 0.2-0.3; here it dominates the signal).

RIG 3 -- run_radiation_loaded(corrections_on=False): attribution control. Turning the global
FFT corrections off collapses the excess 31x -> 2.6x, nailing the injection as the driver; the
control rig itself is degraded (the uncorrected fine stack is under-damped: mass drift ~1e-1,
band flatness ~3), so it supports the attribution without being a clean 1.0 x u_ac reference.

VERDICT for D3-4: do NOT extract by radiating the fine domain. The live handoff is the
COMPACT-SOURCE MAP: the certified near-wall state (Level C T_s_hat, +/-5.4%) determines the
pumping u_src analytically (u_ac relation, confirmed in-layer at 1.03x by RIG 1), and the
one-way soft source (section 11) injects dp = Z0 * u_src into the coarse domain. Quantitative
10 kHz confirmation of the in-layer pumping on the calibrated point is the next D3-4 step.

Diagnostic only: frozen configs untouched (ny raise is contract-authorized, section 2.1);
RIG 3 modifies collision keys in a COPY as an explicitly non-frozen attribution control."""

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
from core.macroscopic import recover_macro
from core.solver import GasSolver2D
from farfield.compact_source import (
    thermal_boundary_layer_thickness_m,
    thermal_pumping_velocity_m_s,
)
from phase3_interfaces.complex_amplitude import complex_amplitude
from scripts.phase2_m2_verification import load_config
from scripts.phase4_open_boundary_reflection import make_thermal_drive_wall_callback

GAS_CONFIG = Path("configs/gas_air_10k_d2q37_levelc_dx2p6.yaml")


def _rig(base_cfg: dict, f_hz: float, ny: int, T_hat_K: float, fit_periods: float,
         sample_interval: int):
    cfg = copy.deepcopy(base_cfg)
    cfg["numerics"] = {**cfg.get("numerics", {}), "nx": 4, "ny": ny}
    solver = GasSolver2D(cfg)
    mp = solver.mapping
    dt, dx = float(mp.lattice.dt_s), float(mp.lattice.dx_m)
    omega = 2.0 * math.pi * f_hz
    alpha0 = float(cfg["physical"]["alpha0_m2_s"])
    T0 = float(cfg["physical"]["T0_K"])
    delta_t = math.sqrt(2.0 * alpha0 / omega)
    u_ac = omega * delta_t / math.sqrt(2.0) * (T_hat_K / T0)
    spp = 1.0 / (f_hz * dt)
    ramp = int(round(1.0 * spp))
    n_steps = int(round((1.5 + fit_periods) * spp))
    n_samples = n_steps // sample_interval
    wall = make_thermal_drive_wall_callback(
        theta0_lu=float(mp.theta_ref_lu),
        theta_hat_lu=T_hat_K / float(mp.temperature_scale),
        omega_si=omega, dt_si=dt, ramp_steps=ramp,
    )
    return solver, mp, dt, dx, delta_t, u_ac, spp, ramp, n_samples, wall


def _fit_rows(solver, rows, t, series, mask, f_hz, scale):
    out = np.empty(rows.size, dtype=complex)
    for j in range(rows.size):
        s = series[mask, j]
        out[j] = complex_amplitude(t[mask], s - float(np.mean(s)), f_hz) * scale
    return out


def run_closed_profile(base_cfg: dict, *, f_hz: float = 40e3, ny: int = 192,
                       T_hat_K: float = 10.0, fit_periods: float = 1.5,
                       sample_interval: int = 100) -> dict[str, Any]:
    """RIG 1: M3-native closed column; returns in-layer pumping vs u_ac + box response."""

    solver, mp, dt, dx, delta_t, u_ac, spp, ramp, n_samples, wall = _rig(
        base_cfg, f_hz, ny, T_hat_K, fit_periods, sample_interval)
    rows = np.unique(np.concatenate([np.arange(3, 26, 2), np.arange(30, ny - 2, 6)]))
    solver.initialize_from_macro(float(mp.lattice.rho_ref_lu), np.zeros((ny, solver.nx, 2)),
                                 float(mp.theta_ref_lu))
    mass0 = float(np.sum(solver.f))
    t = np.empty(n_samples); V = np.empty((n_samples, rows.size)); P = np.empty((n_samples, rows.size))
    TH = np.empty((n_samples, rows.size))
    for i in range(n_samples):
        solver.step(sample_interval, boundary_callback=wall)
        t[i] = solver.t_lu * dt
        m = recover_macro(solver.f[rows], solver.g[rows], D=2, S=3, lattice=solver.lattice)
        V[i] = np.mean(m.u[..., 1], axis=-1); P[i] = np.mean(m.p, axis=-1)
        TH[i] = np.mean(m.theta, axis=-1)
    if not np.isfinite(solver.f).all():
        return {"f_hz": f_hz, "crash": True}
    mask = t >= (ramp + 0.5 * spp) * dt
    v_hat = _fit_rows(solver, rows, t, V, mask, f_hz, dx / dt)
    p_hat = _fit_rows(solver, rows, t, P, mask, f_hz, float(mp.pressure_scale))
    th_hat = _fit_rows(solver, rows, t, TH, mask, f_hz, float(mp.temperature_scale))
    in_layer = rows <= int(math.ceil(3.0 * delta_t / dx))
    peak = float(np.max(np.abs(v_hat[in_layer])))
    bulk = rows >= int(math.ceil(10.0 * delta_t / dx))
    return {
        "f_hz": f_hz, "crash": False, "ny": ny, "T_hat_K": T_hat_K, "u_ac_m_s": u_ac,
        "in_layer_peak_v_m_s": peak, "in_layer_peak_over_u_ac": peak / u_ac,
        "p_box_abs_Pa": float(np.median(np.abs(p_hat[bulk]))),
        "bulk_v_over_u_ac": float(np.median(np.abs(v_hat[bulk]))) / u_ac,
        "mass_rel_drift": abs(float(np.sum(solver.f)) - mass0) / mass0,
        "rows": [int(r) for r in rows],
        "v_hat_re": [float(a) for a in v_hat.real], "v_hat_im": [float(a) for a in v_hat.imag],
        "th_hat_re": [float(a) for a in th_hat.real], "th_hat_im": [float(a) for a in th_hat.imag],
        "p_hat_abs": [float(a) for a in np.abs(p_hat)],
    }


def fit_compact_source(result: dict[str, Any], *, alpha_m2_s: float, T0_K: float,
                       dx_m: float, wall_face_row: float = 2.5) -> dict[str, Any]:
    """Two-parameter compact-source fit of a RIG-1 profile against the farfield map.

    Model (farfield/compact_source.py shapes + a constant closed-box backflow):
        T_hat(y) = A exp(-(1+i) y/delta_T)                 (rows with y <= 3 delta_T)
        v_hat(y) = u_src (1 - exp(-(1+i) y/delta_T)) + c_box   (rows with y <= 4 delta_T)
    with y = (row - wall_face_row) dx (the Grad wall imposes rows 0..2; the half-cell face
    convention is worth ~5% amplitude / ~3 deg phase per half row at 10 kHz -- documented
    rig systematic, not hidden). The MAP CHECK compares the fitted u_src against
    thermal_pumping_velocity_m_s(A): if the frozen stack realizes the map, the ratio is ~1."""

    f_hz = float(result["f_hz"])
    omega = 2.0 * math.pi * f_hz
    delta = thermal_boundary_layer_thickness_m(alpha_m2_s, omega)
    rows = np.asarray(result["rows"], dtype=float)
    v_hat = np.asarray(result["v_hat_re"]) + 1j * np.asarray(result["v_hat_im"])
    th_hat = np.asarray(result["th_hat_re"]) + 1j * np.asarray(result["th_hat_im"])
    y = (rows - wall_face_row) * dx_m

    t_band = y <= 3.0 * delta
    phi = np.exp(-(1.0 + 1.0j) * y[t_band] / delta)
    A = complex(np.sum(th_hat[t_band] * np.conj(phi)) / np.sum(np.abs(phi) ** 2))
    t_resid = float(np.sqrt(np.mean(np.abs(th_hat[t_band] - A * phi) ** 2)) / abs(A))
    logmag = np.log(np.abs(th_hat[t_band]))
    slope = np.polyfit(y[t_band], logmag, 1)[0]
    delta_meas = -1.0 / slope

    v_band = y <= 4.0 * delta
    shape = 1.0 - np.exp(-(1.0 + 1.0j) * y[v_band] / delta)
    design = np.column_stack((shape, np.ones_like(shape)))
    coef, _, _, _ = np.linalg.lstsq(design, v_hat[v_band], rcond=None)
    u_src, c_box = complex(coef[0]), complex(coef[1])
    v_resid = float(np.sqrt(np.mean(np.abs(v_hat[v_band] - design @ coef) ** 2)) / abs(u_src))

    u_map = thermal_pumping_velocity_m_s(A, T0_K=T0_K, omega_rad_s=omega, alpha_m2_s=alpha_m2_s)
    ratio = u_src / u_map
    return {
        "wall_face_row": float(wall_face_row),
        "T_wall_fit_K_abs": abs(A), "T_wall_fit_phase_deg": math.degrees(np.angle(A)),
        "T_profile_resid_rel": t_resid,
        "delta_meas_over_analytic": delta_meas / delta,
        "u_src_fit_m_s": abs(u_src), "u_src_fit_phase_deg": math.degrees(np.angle(u_src)),
        "c_box_over_u_src": abs(c_box) / abs(u_src),
        "v_profile_resid_rel": v_resid,
        "map_check_abs": abs(ratio), "map_check_phase_deg": math.degrees(np.angle(ratio)),
        "n_rows_T": int(np.sum(t_band)), "n_rows_v": int(np.sum(v_band)),
    }


def fit_compact_source_y0_scan(result: dict[str, Any], *, alpha_m2_s: float, T0_K: float,
                               dx_m: float, y0_min: float = 1.5, y0_max: float = 3.5,
                               y0_step: float = 0.05) -> dict[str, Any]:
    """Resolve the wall-face y-origin systematic PRINCIPLED-ly (scoped-risk item 3 clearance).

    The half-cell face convention (wall_face_row=2.5 +/- 0.5) was the dominant systematic of
    the section-12.1 MAP CHECK phase (+5.3 deg at the pre-registered +/-5 deg edge). This scan
    picks y0 by minimizing the TEMPERATURE-profile fit residual ONLY -- a criterion independent
    of the map-check target (anti-self-calibration: choosing y0 to zero the map-check phase
    would be tuning; choosing it to best fit the diffusion-wave shape is measurement). The
    map check evaluated at the T-residual-optimal y0* is then an unbiased refinement, and the
    spread of the map check over the near-optimal y0 band (T-resid within 10% of min) is the
    honest remaining systematic."""

    y0s = np.arange(y0_min, y0_max + 1e-9, y0_step)
    fits = [fit_compact_source(result, alpha_m2_s=alpha_m2_s, T0_K=T0_K, dx_m=dx_m,
                               wall_face_row=float(y0)) for y0 in y0s]
    t_resids = np.array([f["T_profile_resid_rel"] for f in fits])
    j_best = int(np.argmin(t_resids))
    near = t_resids <= t_resids[j_best] * 1.10
    phases = np.array([f["map_check_phase_deg"] for f in fits])[near]
    mags = np.array([f["map_check_abs"] for f in fits])[near]
    return {
        "y0_best_row": float(y0s[j_best]),
        "t_resid_best": float(t_resids[j_best]),
        "t_resid_at_2p5": float(t_resids[int(np.argmin(np.abs(y0s - 2.5)))]),
        "fit_at_best": fits[j_best],
        "near_optimal_band_rows": [float(y0s[near][0]), float(y0s[near][-1])],
        "map_check_abs_band": [float(np.min(mags)), float(np.max(mags))],
        "map_check_phase_deg_band": [float(np.min(phases)), float(np.max(phases))],
    }


def run_radiation_loaded(base_cfg: dict, *, f_hz: float = 40e3, ny: int = 256,
                         n_sponge: int = 60, T_hat_K: float = 10.0,
                         corrections_on: bool = True, fit_periods: float = 1.5,
                         sample_interval: int = 100) -> dict[str, Any]:
    """RIG 2/3: fine column radiating into a top sponge; band u, Z=p/u, flatness.

    ``corrections_on=False`` is the non-frozen attribution control (RIG 3)."""

    cfg = copy.deepcopy(base_cfg)
    if not corrections_on:
        cfg["collision"]["dispersion_correction_enabled"] = False
        cfg["collision"]["acoustic_phase_correction_enabled"] = False
    solver, mp, dt, dx, delta_t, u_ac, spp, ramp, n_samples, wall = _rig(
        cfg, f_hz, ny, T_hat_K, fit_periods, sample_interval)
    z0 = float(cfg["physical"]["rho0_kg_m3"]) * float(cfg["physical"]["c0_m_s"])
    y_c = int(math.ceil(8.0 * delta_t / dx))
    rows = np.arange(y_c, min(y_c + 40, ny - n_sponge - 10), 2)
    solver.initialize_from_macro(float(mp.lattice.rho_ref_lu), np.zeros((ny, solver.nx, 2)),
                                 float(mp.theta_ref_lu))
    mass0 = float(np.sum(solver.f))
    cb = compose_boundary_callbacks(wall, make_top_sponge_callback(n_sponge=n_sponge, sigma_max=0.5))
    t = np.empty(n_samples); V = np.empty((n_samples, rows.size)); P = np.empty((n_samples, rows.size))
    for i in range(n_samples):
        solver.step(sample_interval, boundary_callback=cb)
        t[i] = solver.t_lu * dt
        m = recover_macro(solver.f[rows], solver.g[rows], D=2, S=3, lattice=solver.lattice)
        V[i] = np.mean(m.u[..., 1], axis=-1); P[i] = np.mean(m.p, axis=-1)
    if not np.isfinite(solver.f).all():
        return {"f_hz": f_hz, "corrections_on": corrections_on, "crash": True}
    mask = t >= (ramp + 0.5 * spp) * dt
    v_hat = _fit_rows(solver, rows, t, V, mask, f_hz, dx / dt)
    p_hat = _fit_rows(solver, rows, t, P, mask, f_hz, float(mp.pressure_scale))
    u_med = complex(np.median(v_hat.real) + 1j * np.median(v_hat.imag))
    z_rows = p_hat / v_hat
    z_med = complex(np.median(z_rows.real) + 1j * np.median(z_rows.imag))
    return {
        "f_hz": f_hz, "corrections_on": corrections_on, "crash": False, "ny": ny,
        "u_ac_m_s": u_ac, "u_band_over_u_ac": abs(u_med) / u_ac,
        "u_band_phase_deg": math.degrees(np.angle(u_med)),
        "z_over_z0": abs(z_med) / z0, "z_phase_deg": math.degrees(np.angle(z_med)),
        "band_flatness": float(np.std(np.abs(v_hat)) / max(abs(u_med), 1e-300)),
        "mass_rel_drift": abs(float(np.sum(solver.f)) - mass0) / mass0,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="P4-D3 D3-4 source-extraction three-rig probe (diagnostic).")
    ap.add_argument("--gas-config", type=Path, default=GAS_CONFIG)
    ap.add_argument("--frequency", type=float, default=40e3,
                    help="40e3 = cheap mechanics shakedown (off-calibration); 10e3 = calibrated point (slow)")
    ap.add_argument("--rigs", type=str, default="123",
                    help="which rigs to run, e.g. '1' for the closed profile + map fit only")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    base = load_config(args.gas_config)
    f = args.frequency
    payload: dict[str, Any] = {}

    print(f"three-rig source-extraction diagnostic at {f/1e3:.0f} kHz (frozen M3 stack unless noted)\n")
    if "1" in args.rigs:
        r1 = run_closed_profile(base, f_hz=f)
        payload["rig1"] = r1
        print(f"RIG1 closed (M3-native): in-layer peak = {r1['in_layer_peak_over_u_ac']:.3f} x u_ac; "
              f"bulk residual {r1['bulk_v_over_u_ac']:.3f} x u_ac; p_box {r1['p_box_abs_Pa']:.2f} Pa; "
              f"mass drift {r1['mass_rel_drift']:.2e}", flush=True)
        fit = fit_compact_source(
            r1, alpha_m2_s=float(base["physical"]["alpha0_m2_s"]),
            T0_K=float(base["physical"]["T0_K"]), dx_m=float(base["lattice"]["dx_m"]))
        payload["rig1_fit"] = fit
        print(f"     compact-source fit: T_wall = {fit['T_wall_fit_K_abs']:.3f} K (drive {r1['T_hat_K']:.1f} K), "
              f"T-resid {fit['T_profile_resid_rel']:.3f}, delta/analytic = {fit['delta_meas_over_analytic']:.3f}", flush=True)
        print(f"     u_src = {fit['u_src_fit_m_s']:.4e} m/s @ {fit['u_src_fit_phase_deg']:+.1f} deg, "
              f"c_box/u_src = {fit['c_box_over_u_src']:.3f}, v-resid {fit['v_profile_resid_rel']:.3f}", flush=True)
        print(f"     MAP CHECK u_src/map(T_wall_fit) = {fit['map_check_abs']:.3f} @ "
              f"{fit['map_check_phase_deg']:+.1f} deg  (1.0 @ 0 deg = frozen stack realizes the map)", flush=True)
    if "2" in args.rigs:
        r2 = run_radiation_loaded(base, f_hz=f, corrections_on=True)
        payload["rig2"] = r2
        print(f"RIG2 radiating (frozen):  u_band = {r2['u_band_over_u_ac']:.2f} x u_ac; "
              f"Z = {r2['z_over_z0']:.3f} x Z0 @ {r2['z_phase_deg']:+.1f} deg; "
              f"flatness {r2['band_flatness']:.4f}; mass drift {r2['mass_rel_drift']:.2e}", flush=True)
    if "3" in args.rigs:
        r3 = run_radiation_loaded(base, f_hz=f, corrections_on=False)
        payload["rig3"] = r3
        print(f"RIG3 radiating (corr OFF, non-frozen control): u_band = {r3['u_band_over_u_ac']:.2f} x u_ac; "
              f"Z = {r3['z_over_z0']:.3f} x Z0; flatness {r3['band_flatness']:.4f}; "
              f"mass drift {r3['mass_rel_drift']:.2e}", flush=True)
    print("\nreading: RIG1 pumping ~ map (source physics right) + RIG2 Z ~ Z0 but amplitude >> u_ac "
          "(injection swamps radiation) + RIG3 collapse when corrections off (attribution) "
          "=> hand off via the compact-source map (certified T_s_hat -> u_src), not by radiating the fine domain.")
    if args.out:
        args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
