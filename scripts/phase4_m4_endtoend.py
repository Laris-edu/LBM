"""P4-5/E2: M4 end-to-end far-field verification on the D3 one-way architecture.

Project: docs/Phase_4/M4/P4_D3_Multidomain_Acoustic_Project.md (section 13); contract
sections 10 (P4-5, gates E1/E2, reference layers R0/R1/R2) and 11 (M4 report inputs).

CHAIN (every constant frozen upstream, nothing tuned here):

  M3 canonical T_s_hat                    0.37269 K @ -47.535 deg
    (Level C full-period canonical run 20260702T114339Z, physics-core digest 26be2fde3cc2;
     carries the M3 +/-5.4% amplitude band, M3 = PHASE_PASS_AMPLITUDE_BOUNDARY, not clear pass)
  -> compact-source map (section 12.1)    u_src = (1+i)/2 Omega delta_T T_s_hat/T0
     (on-stack realization anchored: MAP CHECK 1.001 @ +5.3 deg at the 10 kHz point)
  -> physical handoff                     dp_phys = Z0_air * u_src   (~0.60 Pa, per side)
  -> G-precompensated soft source         dp_drive = dp_phys / G
     (G = 0.1580 @ +152.4 deg, frozen in section 12.3 BEFORE any far-field existed --
      using it here is instrument calibration, not tuning; G maps nominal drive to the
      realized wave at the G-reference plane, band row 150)
  -> calibrated coarse acoustic domain    (c_SI +0.17%, section 12.3; open top |R|=0.0004,
      section 9; one-way injection boundary, section 11)
  -> control surface (p_hat, v_hat)       two dp/dn channels: momentum (-i Omega rho0 v_n,
      PRIMARY) vs outgoing-assumption (-i k p_hat); contract section 6: if they differ by
      >10%/10 deg investigate the data chain, never the kernel
  -> K0 Kirchhoff kernel (section 12.4)   x-uniform tiling over a wide aperture (x-periodic
      normal-emission scope: certifies normal radiation ONLY, no finite-width directivity)
  -> far-field p_hat / SPL at observers above.

REFERENCE (contract 10.3): R1 = compact thermophone far-field formula -- the outgoing plane
wave dp_phys exp(-i k_air (y - y_ref)) radiated by the mapped source. The E2 ratio therefore
certifies the TRANSPORT + EXTRACTION + KERNEL chain against an analytic reference that shares
only the frozen source amplitude; the map itself is anchored independently (section 12.1),
and the M3 +/-5.4% band applies to the ABSOLUTE SPL claim, not to the E2 ratio. R2 =
control-surface self-consistency: the far field must not depend on which control row feeds
Kirchhoff (<5% suggested gate).

Error budget (contract 10.4 item 5) is assembled from the frozen per-stage anchors and the
in-run measured channel/R2 numbers; no clipping/floor/positivity repair/prefactor tuning."""

from __future__ import annotations

import argparse
import cmath
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from farfield.compact_source import (
    soft_source_pressure_amplitude_pa,
    thermal_pumping_velocity_m_s,
)
from farfield.kirchhoff_2d import (
    GREEN_OUTGOING,
    dpdn_from_velocity,
    kirchhoff_2d_frequency,
)
from scripts.phase2_m2_verification import load_config, summary_payload_digest
from scripts.phase4_d3_map_chain_smoke import (
    AIR_ALPHA,
    AIR_C0,
    AIR_RHO0,
    AIR_T0_K,
    F_HZ,
    run_chain,
)

ACOUSTIC_CONFIG = Path("configs/phase4_acoustic_coarse_dx334.yaml")
VOLATILE_DIGEST_KEYS = ("run_id", "artifacts")

# M3 canonical Level C readout (results/m3/20260702T114339Z/summary.json; recorded in
# docs/Phase_3/M3/M3_Run_Summaries.md; physics-core digest 26be2fde3cc2...). The handoff
# quantity of the compact-source architecture -- the fine/M3 domain is NOT re-run here.
T_S_HAT_ABS_K = 0.37269065970502574
T_S_HAT_PHASE_DEG = -47.53498321692854
T_S_HAT_PROVENANCE = "results/m3/20260702T114339Z summary.json, physics-core digest 26be2fde3cc2"

# Injection rig constant, frozen in project section 12.3 (calibrated medium, ny=512, y_s=90,
# scale=0.05, G-reference plane = band row 150, 10 kHz). Locked before any far-field result.
G_ABS = 0.1580
G_PHASE_DEG = +152.4

# Kirchhoff aperture (same discretization family as the K0 fixture config).
APERTURE_WAVELENGTHS = 600.0
SAMPLES_PER_WAVELENGTH = 12.0
OBSERVER_HEIGHTS_WAVELENGTHS = (20.0, 50.0, 100.0)


def _spl_db(p_abs_pa: float) -> float:
    return 20.0 * math.log10(p_abs_pa / math.sqrt(2.0) / 20.0e-6)


def _kirchhoff_from_control_row(p_c: complex, dpdn_c: complex, y_c_m: float,
                                observer_y_m: np.ndarray) -> np.ndarray:
    lam = AIR_C0 / F_HZ
    n = int(round(APERTURE_WAVELENGTHS * SAMPLES_PER_WAVELENGTH))
    xs = np.linspace(-APERTURE_WAVELENGTHS * lam / 2.0, APERTURE_WAVELENGTHS * lam / 2.0, n)
    return kirchhoff_2d_frequency(
        surface_x_m=xs, surface_y_m=np.full(n, y_c_m),
        normal_x=np.zeros(n), normal_y=np.ones(n),
        ds_m=np.full(n, xs[1] - xs[0]),
        p_hat_Pa=np.full(n, p_c), dpdn_hat_Pa_m=np.full(n, dpdn_c),
        observer_x_m=np.zeros(observer_y_m.size), observer_y_m=observer_y_m,
        omega_rad_s=2.0 * math.pi * F_HZ, c0_m_s=AIR_C0,
        green_convention=GREEN_OUTGOING)


def evaluate_m4_gates(gates: dict[str, float]) -> bool:
    """Evaluate every declared E2/R2/control-channel threshold."""

    return bool(
        gates["E2_amp_rel_err_max"] < 0.10
        and gates["E2_phase_err_deg_max"] < 10.0
        and gates["R2_control_surface_sensitivity"] < 0.05
        and abs(gates["channel_diff_amp_primary"]) < 0.10
        and abs(gates["channel_diff_phase_deg_primary"]) < 10.0
    )


def run_m4_endtoend(base_cfg: dict, *, control_row_primary: int = 246,
                    control_row_check: int = 318) -> dict[str, Any]:
    omega = 2.0 * math.pi * F_HZ
    k_air = omega / AIR_C0
    lam = AIR_C0 / F_HZ

    # Frozen source chain: canonical T_s_hat -> map -> physical handoff -> G-precompensation.
    ts_hat = T_S_HAT_ABS_K * cmath.exp(1j * math.radians(T_S_HAT_PHASE_DEG))
    u_src = thermal_pumping_velocity_m_s(ts_hat, T0_K=AIR_T0_K, omega_rad_s=omega,
                                         alpha_m2_s=AIR_ALPHA)
    dp_phys = soft_source_pressure_amplitude_pa(u_src, rho0_kg_m3=AIR_RHO0, c0_m_s=AIR_C0)
    g = G_ABS * cmath.exp(1j * math.radians(G_PHASE_DEG))
    dp_drive = dp_phys / g

    r = run_chain(base_cfg, dp_pa_override=dp_drive, return_band=True)
    if r.get("crash"):
        return {"crash": True}
    rows = np.asarray(r["rows"])
    dx = float(r["dx_m"])
    p_band = np.asarray(r["p_band_Pa"])
    v_band = np.asarray(r["v_band_m_s"])
    y_ref_m = float(rows[0]) * dx                     # G-reference plane (band row 150)
    observer_y_m = y_ref_m + np.asarray(OBSERVER_HEIGHTS_WAVELENGTHS) * lam

    def _expected_at(y_m: float) -> complex:
        return dp_phys * cmath.exp(-1j * k_air * (y_m - y_ref_m))

    # Handoff-plane reproducibility: applying the frozen G blind, the realized wave at the
    # G-reference plane must reproduce the physical handoff amplitude/phase.
    handoff_ratio = complex(p_band[0] / dp_phys)

    # Gas CV audit, coarse domain (scoped-risk item 2, quantified): time-averaged acoustic
    # energy flux I(y) = 1/2 Re[p_hat conj(v_hat)] along the traveling-wave band. Between the
    # source and the top sponge the flux must be conserved up to medium+filter dissipation;
    # its start->end drop IS the coarse-domain CV closure statement. The fine domain never
    # opens under D3 (M3 film audit 1.9e-14 inherited); contract section 7 wording is kept:
    # this stays a DIAGNOSTIC (quantified), never a PASSED claim.
    flux = 0.5 * np.real(p_band * np.conj(v_band))
    cv_audit = {
        "flux_start_W_m2": float(flux[0]), "flux_end_W_m2": float(flux[-1]),
        "flux_rel_drop_start_to_end": float(1.0 - flux[-1] / flux[0]),
        "flux_flatness_std_over_mean": float(np.std(flux) / np.mean(flux)),
        "status": "GAS_CV_AUDIT_DIAGNOSTIC_QUANTIFIED",
    }

    results_ff = {}
    for label, row in (("primary", control_row_primary), ("check", control_row_check)):
        j = int(np.argmin(np.abs(rows - row)))
        y_c_m = float(rows[j]) * dx
        p_c, v_c = complex(p_band[j]), complex(v_band[j])
        dpdn_v = complex(dpdn_from_velocity(v_c, omega_rad_s=omega, rho0_kg_m3=AIR_RHO0))
        dpdn_p = -1j * k_air * p_c                    # outgoing-plane-wave channel (cross-check)
        channel_ratio = dpdn_v / dpdn_p
        p_ff = _kirchhoff_from_control_row(p_c, dpdn_v, y_c_m, observer_y_m)
        entries = []
        for oy, pf in zip(observer_y_m, p_ff, strict=True):
            ref = _expected_at(float(oy))
            ratio = complex(pf / ref)
            entries.append({
                "observer_y_m": float(oy),
                "p_ff_abs_Pa": abs(pf), "spl_db": _spl_db(abs(pf)),
                "amp_rel_err": abs(ratio) - 1.0,
                "phase_err_deg": math.degrees(cmath.phase(ratio)),
            })
        results_ff[label] = {
            "control_row": int(rows[j]), "y_c_m": y_c_m,
            "p_c_abs_Pa": abs(p_c),
            "channel_diff_amp": abs(channel_ratio) - 1.0,
            "channel_diff_phase_deg": math.degrees(cmath.phase(channel_ratio)),
            "farfield": entries,
        }

    prim = results_ff["primary"]; chk = results_ff["check"]
    e2_amp_max = max(abs(e["amp_rel_err"]) for e in prim["farfield"])
    e2_phase_max = max(abs(e["phase_err_deg"]) for e in prim["farfield"])
    r2_amp = max(
        abs(primary["p_ff_abs_Pa"] / check["p_ff_abs_Pa"] - 1.0)
        for primary, check in zip(prim["farfield"], chk["farfield"], strict=True)
    )

    return {
        "crash": False,
        "T_s_hat": {"abs_K": T_S_HAT_ABS_K, "phase_deg": T_S_HAT_PHASE_DEG,
                    "provenance": T_S_HAT_PROVENANCE},
        "u_src_m_s": {"abs": abs(u_src), "phase_deg": math.degrees(cmath.phase(u_src))},
        "dp_phys_Pa": {"abs": abs(dp_phys), "phase_deg": math.degrees(cmath.phase(dp_phys))},
        "G_frozen": {"abs": G_ABS, "phase_deg": G_PHASE_DEG,
                     "provenance": "project section 12.3, locked before any far-field"},
        "dp_drive_Pa_abs": abs(dp_drive),
        "handoff_plane": {"row": int(rows[0]),
                          "amp_rel_err": abs(handoff_ratio) - 1.0,
                          "phase_err_deg": math.degrees(cmath.phase(handoff_ratio))},
        "chain_diagnostics": {
            "onewayness": r["onewayness"], "band_flatness": r["band_flatness"],
            "c_si_over_air": r["c_si_over_air"], "mass_rel_drift": r["mass_rel_drift"],
        },
        "cv_audit": cv_audit,
        "control_surface": results_ff,
        "gates": {
            "E2_amp_rel_err_max": e2_amp_max,       # contract hard gate 4: < 0.10
            "E2_phase_err_deg_max": e2_phase_max,   # suggested gate: < 10 deg
            "R2_control_surface_sensitivity": r2_amp,   # suggested gate: < 5%
            "channel_diff_amp_primary": prim["channel_diff_amp"],   # contract sec.6: < 10%
            "channel_diff_phase_deg_primary": prim["channel_diff_phase_deg"],  # < 10 deg
        },
        "spl_farfield_db": prim["farfield"][0]["spl_db"],
        "error_budget": {
            "m3_inherited_amplitude_band": "+/-5.4% (PHASE_PASS_AMPLITUDE_BOUNDARY, absolute claim only)",
            "source_map_onstack_realization": (
                "amp 1.0006 +/- ~3% (fit-residual bound; y0-origin IMMUNE by ratio invariance, "
                "section 12.1 y0 scan); phase +5.34 deg = real stack-map offset, absolute-phase "
                "line item only (E2 ratio independent)"),
            "injection_G_linearity": "<0.1% (section 12.2), rounding <0.05%",
            "open_boundary_reflection": "|R|=0.0004 -> <0.1% (section 9)",
            "sound_speed_calibration": "+0.17% -> phase ~1-2 deg over the propagation path (section 12.3)",
            "kirchhoff_kernel": "<0.5%/<0.5 deg measured on fixtures (section 12.4, gate <2%/<2 deg)",
            "control_surface_derivative": "measured channel diff (this run, gates block)",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="P4-5 E2: M4 end-to-end far-field verification.")
    ap.add_argument("--acoustic-config", type=Path, default=ACOUSTIC_CONFIG)
    ap.add_argument("--out-root", type=Path, default=Path("results/m4"))
    args = ap.parse_args()
    base = load_config(args.acoustic_config)

    r = run_m4_endtoend(base)
    if r.get("crash"):
        print("E2: CRASH")
        return 1
    print("M4 end-to-end (D3 one-way architecture; R1 = compact thermophone plane-wave formula)\n")
    print(f"source: T_s_hat = {r['T_s_hat']['abs_K']:.5f} K @ {r['T_s_hat']['phase_deg']:+.2f} deg "
          f"(M3 canonical, digest 26be2fde) -> u_src = {r['u_src_m_s']['abs']:.4e} m/s -> "
          f"dp_phys = {r['dp_phys_Pa']['abs']:.4f} Pa")
    hp = r["handoff_plane"]
    print(f"handoff plane (row {hp['row']}): amp err {hp['amp_rel_err']:+.4f}, "
          f"phase err {hp['phase_err_deg']:+.2f} deg  (frozen G applied blind)")
    prim = r["control_surface"]["primary"]
    print(f"control surface row {prim['control_row']}: |p_c| = {prim['p_c_abs_Pa']:.4f} Pa; "
          f"channel diff {prim['channel_diff_amp']:+.4f} / {prim['channel_diff_phase_deg']:+.2f} deg")
    cv = r["cv_audit"]
    print(f"CV audit (coarse flux): I_start = {cv['flux_start_W_m2']:.4e} W/m2, "
          f"start->end drop {cv['flux_rel_drop_start_to_end']:+.4f}, "
          f"flatness {cv['flux_flatness_std_over_mean']:.4f}  [{cv['status']}]")
    for e in prim["farfield"]:
        print(f"  farfield y = {e['observer_y_m']:.3f} m: |p| = {e['p_ff_abs_Pa']:.4f} Pa "
              f"({e['spl_db']:.2f} dB SPL)  amp err {e['amp_rel_err']:+.4f}  "
              f"phase err {e['phase_err_deg']:+.2f} deg")
    g = r["gates"]
    print(f"\nE2 amp err max = {g['E2_amp_rel_err_max']:.4f} (hard gate <0.10)   "
          f"E2 phase err max = {g['E2_phase_err_deg_max']:.2f} deg (<10)")
    print(f"R2 control-surface sensitivity = {g['R2_control_surface_sensitivity']:.4f} (<0.05)   "
          f"channel diff = {g['channel_diff_amp_primary']:+.4f} / "
          f"{g['channel_diff_phase_deg_primary']:+.2f} deg (<0.10/<10 deg)")
    passed = evaluate_m4_gates(g)
    print(f"\nE2 verdict: {'PASSED' if passed else 'FAILED'} "
          "(M4 gate wording stays PASSED_WITH_SCOPED_RISK; see M4 report)")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {"run_id": run_id, "scope": "P4-5_E2_D3_ONEWAY_10KHZ_NORMAL_EMISSION",
               "e2_passed": passed, **r}
    safe = json.loads(json.dumps(payload, default=str))
    digest_core = {k: v for k, v in safe.items() if k not in VOLATILE_DIGEST_KEYS}
    safe["summary_digest"] = summary_payload_digest(digest_core)
    safe["summary_digest_scope"] = "physics_core; excludes " + ", ".join(VOLATILE_DIGEST_KEYS)
    out_dir = args.out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(safe, indent=2), encoding="utf-8")
    print(f"wrote {out_dir / 'summary.json'}  digest {safe['summary_digest'][:12]}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
