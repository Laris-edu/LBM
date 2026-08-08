"""Phase_5 G1-W nonlinear wall-neutrality gate runner (contract §6.1, WP2).

Certifies the mass-neutral production-wall candidate (v1.1 symmetric two-sided,
``boundary/wall_thermal_mass_neutral.py``) against the eight §6.1 gate rows on
the frozen 10 kHz dx2p6 stack, with the frozen ``pressure_preserving`` Grad
wall as the mandated diagnostic contrast:

  1. normalized net wall mass flux, 0f-3f components   <= 1e-10  (production wall)
  2. global mass: fit-window |dM|/M0 <= 1e-8, cumulative <= 1e-6
  3. impermeability/no-slip: wall-row u_n mean & 1f-3f <= 1e-8 c0 (tangential mean too)
  4. wall-temperature realization                       <= 0.01 K
  5. small-amplitude admittance regression              <= 5% / 5 deg
  6. boundary-linear-interior fixture: odd-pair non-target 2f/3f <= 1e-8
  7. old-vs-new difference audit (D_G/H2/H3/DC)  -> old wall DIAGNOSTIC_ONLY marking
  8. numerical discipline (no clipping/floor/repair; constraint residual audited)

Admittance regression reference (pre-registered path, Phase5_STATUS §5): the
sealed y-periodic rig is compared against the **lbm-equivalent sealed spectral
reference** — the sealed symmetric-wall response computed per periodic mode
k_j = 2*pi*j/ny with the G0-measured effective diffusivity alpha_eff(k_j)
(authoritative G0 table + in-run high-k extension rows measured with the same
frozen instrument; policy band archived). Stage-1 attribution (2026-07-26,
run archive) showed this closes the WP1-3 open +13%/+20% energy excess to
~-3.4%/-2.2 deg: the frozen stack's strongly non-monotonic alpha_eff(k)
(0.48x..12.5x nominal across the response band) IS the sealed-box physics of
this instrument; the readout is the calibration-free energy-balance channel
q_side = i*Omega*(N/2)*p_box/(gamma-1) (exact conserved moments only).

The moment-channel export factor on the mn field shape is measured and
archived as the §23 pre-registered wall-change recalibration input (it is NOT
used to pass any gate row here).

Outputs: contract §16.1 seven-file set under
``results/phase5/g1w_wall_neutrality/<run_id>/``. Verdict (script-emittable):
PASSED (all rows), SCOPED_CANDIDATE (neutrality hard rows pass, regression or
fixture row fails), FAILED (any neutrality hard row fails).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import yaml

from boundary.wall_mass_audit import (
    NORMALIZATION_DEFINITION,
    WallAuditRecorder,
    harmonic_components,
    make_mass_audited_callback,
)
from boundary.wall_thermal_grad import make_bottom_grad_wall_callback
from boundary.wall_thermal_mass_neutral import make_symmetric_mass_neutral_wall_callback
from core.solver import GasSolver2D
from coupling.conjugate import extract_bottom_wall_heat_flux_si
from postproc.multiharmonic_fit import fit_multiharmonic
from reference.thermal_admittance import thermal_admittance_halfspace
from scripts.phase2_m2_verification import load_config, sha256_file
from verification.thermal_diffusion_measurement import (
    ThermalDiffusionSettings,
    measure_thermal_diffusion_direction,
)

GATE_ID = "G1-W"
CASE_FAMILY = "g1w_wall_neutrality"
PHASE5_CONTRACT_VERSION = "v1.2"
G0_TABLE_CSV = Path("archive/M5_runs/g0_20260722T173919Z/property_table.csv")
PARENT_BASELINE_RUN = "g0_effective_properties/20260722T173919Z"
GAMMA_EFF_G0_K1 = 1.4230  # G0 sensitivity variant (nonlinear_model_freeze.md §1)

DEFAULT_CONFIG = Path("configs/phase5/g1w_wall_neutrality/g1w_10k_dx2p6.yaml")


def _git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except Exception:
        return "unknown"


def _cplx(z: complex) -> dict[str, float]:
    z = complex(z)
    return {"re": z.real, "im": z.imag, "abs": abs(z),
            "phase_deg": math.degrees(math.atan2(z.imag, z.real))}


def _ratio(a: complex, b: complex) -> dict[str, float]:
    r = a / b
    return {"amp_rel_err": float(abs(r) - 1.0),
            "phase_deg_err": float(math.degrees(math.atan2(r.imag, r.real)))}


# ---------------------------------------------------------------------------
# alpha_eff(k) table: G0 authoritative rows + in-run extension rows
# ---------------------------------------------------------------------------


def load_g0_alpha_rows(csv_path: Path) -> list[tuple[float, float]]:
    """300 K isobaric y-axis (k_lu, alpha_eff_lu) rows from the archived G0 table."""

    rows: list[tuple[float, float]] = []
    with csv_path.open(encoding="utf-8") as fh:
        for rec in csv.DictReader(fh):
            if (rec["tag"] == "" and float(rec["T_K"]) == 300.0
                    and rec["background_path"] == "isobaric" and rec["direction"] == "y"):
                rows.append((float(rec["k_lu"]), float(rec["alpha_eff_lu"])))
    if len(rows) < 4:
        raise RuntimeError(f"G0 table parse produced only {len(rows)} rows")
    return sorted(rows)


def measure_extension_rows(gas_cfg: dict, ny_list: list[int], alpha_nom: float,
                           log) -> list[dict[str, Any]]:
    """High-k alpha_eff rows with the same frozen G0 instrument (300 K, y axis)."""

    out = []
    for ny in ny_list:
        k = 2.0 * math.pi / ny
        steps = max(int(0.9 / (alpha_nom * k * k)), 300)
        r = measure_thermal_diffusion_direction(gas_cfg, "y", ThermalDiffusionSettings(
            amplitude=1e-5, nx=4, ny=ny, steps=steps,
            sample_interval=max(1, steps // 400), fit_start=max(steps // 12, 10),
            mode_index=1))
        row = {"ny": ny, "k_lu": k, "alpha_eff_lu": float(r["alpha_measured_lu"]),
               "ratio_vs_nominal": float(r["alpha_measured_lu"] / alpha_nom),
               "steps": steps, "finite": not r["nan_detected"]}
        out.append(row)
        log("alpha_ext ny=%2d k=%.4f alpha=%.6f (%.2fx nom)" % (
            ny, k, row["alpha_eff_lu"], row["ratio_vs_nominal"]))
    return out


def sealed_spectral_reference(
    n_cells: int, omega_lu: float, alpha_nom: float,
    k_tab: np.ndarray, a_tab: np.ndarray,
    *, highk_policy: str, gamma: float,
) -> dict[str, Any]:
    """Sealed symmetric-wall response with per-mode alpha_eff(k) (rho*cp = 1 units).

    Returns Y_side/Y_hs (Y_hs at NOMINAL transport) and the row profile
    T_hat(y)/T_hat_w on the periodic grid (wall row at y=0).
    """

    def alpha_of(k: float) -> float:
        if k <= k_tab[0]:
            return float(a_tab[0])
        if k <= k_tab[-1]:
            return float(np.interp(k, k_tab, a_tab))
        return float(a_tab[-1]) if highk_policy == "hold_last" else alpha_nom

    n = n_cells
    denom_sum = 0.0 + 0.0j
    coeffs = np.empty(n, dtype=complex)
    for j in range(n):
        k = 2.0 * math.pi * min(j, n - j) / n
        if j == 0:
            coeffs[j] = gamma / (1j * omega_lu * n)
        else:
            coeffs[j] = 1.0 / (n * (1j * omega_lu + alpha_of(k) * k * k))
        denom_sum += coeffs[j]
    s_hat = 1.0 / denom_sum                       # T_hat_w = 1
    y_side = s_hat / 2.0
    y_hs = complex(np.sqrt(1j * omega_lu * alpha_nom))
    # T_hat(y_i)/T_hat_w = sum_j coeffs_j * S_hat * e^{i k_j y_i}
    modes = np.exp(2j * np.pi * np.outer(np.arange(n), np.arange(n)) / n)  # (j, y)
    profile = (coeffs[:, None] * modes).sum(axis=0) * s_hat
    return {"Y_over_Yhs": y_side / y_hs, "profile_over_Tw": profile,
            "highk_policy": highk_policy, "gamma": gamma}


# ---------------------------------------------------------------------------
# driven sealed run
# ---------------------------------------------------------------------------


def run_driven(
    gas_cfg: dict, wall: str, epsilon: float, *,
    frequency_hz: float, periods: float, settle_periods: float,
    samples_per_period: int, grad_extrap_old: str, log,
    ramp_periods: float = 1.0, record_field_rows: bool = False,
) -> dict[str, Any]:
    """Driven sealed-rig run (G1-W caliber).

    ``record_field_rows=False`` (default) is byte-identical to the original
    G1-W/G1a instrument; ``True`` additionally samples x-averaged u_y and
    pressure rows (pure observation added for G2-T near-field p/T/u output —
    the step sequence is untouched).
    """
    solver = GasSolver2D(gas_cfg)
    mapping = solver.mapping
    dt = float(mapping.lattice.dt_s)
    theta0 = float(mapping.theta_ref_lu)
    temp_scale = float(mapping.temperature_scale)
    omega = 2.0 * math.pi * frequency_hz
    theta_hat = epsilon * theta0
    steps_per_period = int(round((1.0 / frequency_hz) / dt))
    n_steps = int(round(periods * steps_per_period))
    stride = max(1, steps_per_period // samples_per_period)

    solver.initialize_from_macro(
        mapping.lattice.rho_ref_lu, np.zeros((solver.ny, solver.nx, 2)), theta0)
    mass0 = float(np.sum(solver.f))

    recorder = WallAuditRecorder()
    n_samples = n_steps // stride + 1
    t_s = np.empty(n_samples)
    p_box = np.empty(n_samples)
    q_mom = np.empty(n_samples)
    mass_t = np.empty(n_samples)
    t_rows = np.empty((n_samples, solver.ny))
    theta_imposed = np.empty(n_samples)
    uy_rows = np.empty((n_samples, solver.ny)) if record_field_rows else None
    p_rows = np.empty((n_samples, solver.ny)) if record_field_rows else None

    def sample(idx: int, step: int, theta_w_now: float) -> None:
        t_s[idx] = step * dt
        p_field = solver.get_pressure_lu()
        p_box[idx] = float(np.mean(p_field))
        q_mom[idx] = extract_bottom_wall_heat_flux_si(solver)
        mass_t[idx] = float(np.sum(solver.f))
        t_rows[idx] = np.mean(solver.get_temperature_lu(), axis=1)
        theta_imposed[idx] = theta_w_now
        if record_field_rows:
            uy_rows[idx] = np.mean(solver.get_macro().u[:, :, 1], axis=1)
            p_rows[idx] = np.mean(p_field, axis=1)

    sample(0, 0, theta0)
    sample_idx = 1
    imposed_per_step: list[float] = []
    t_ramp = ramp_periods / frequency_hz
    for i in range(n_steps):
        t_end = (i + 1) * dt
        # raised-cosine amplitude ramp (pre-registered transient discipline,
        # WP1-4): adiabatic switch-on suppresses the slow homogeneous mode
        env = 1.0 if (ramp_periods <= 0.0 or t_end >= t_ramp) else \
            0.5 * (1.0 - math.cos(math.pi * t_end / t_ramp))
        theta_w = theta0 + env * theta_hat * math.cos(omega * t_end)
        imposed_per_step.append(theta_w)
        if wall == "mass_neutral_v1p1":
            inner = make_symmetric_mass_neutral_wall_callback(theta_w, extrap="row1")
        elif wall == "pressure_preserving_grad":
            inner = make_bottom_grad_wall_callback(
                theta_w, rho_policy="pressure_preserving",
                extrap=grad_extrap_old, fill_deep_links=False)
        else:
            raise ValueError(wall)
        solver.step(1, boundary_callback=make_mass_audited_callback(inner, recorder))
        if (i + 1) % stride == 0:
            sample(sample_idx, i + 1, theta_w)
            sample_idx += 1

    finite = bool(np.isfinite(solver.f).all() and np.isfinite(solver.g).all()
                  and np.isfinite(p_box).all() and np.isfinite(q_mom).all())
    n_used = sample_idx
    t_s, p_box, q_mom, mass_t = t_s[:n_used], p_box[:n_used], q_mom[:n_used], mass_t[:n_used]
    t_rows, theta_imposed = t_rows[:n_used], theta_imposed[:n_used]
    if record_field_rows:
        uy_rows, p_rows = uy_rows[:n_used], p_rows[:n_used]

    # fits over the pre-registered window
    mask = t_s >= settle_periods / frequency_hz * (1.0 - 1e-12)
    fit_p = fit_multiharmonic(t_s[mask], p_box[mask], omega, n_harmonics=3)
    fit_q = fit_multiharmonic(t_s[mask], q_mom[mask], omega, n_harmonics=3)

    # window-pair sensitivity (U_det proxy): second window starting half a period later
    mask2 = t_s >= (settle_periods + 0.5) / frequency_hz * (1.0 - 1e-12)
    fit_p2 = fit_multiharmonic(t_s[mask2], p_box[mask2], omega, n_harmonics=3)

    # global-mass rows
    m_win = mass_t[mask]
    window_dm_rel = float(np.max(np.abs(m_win - m_win[0])) / mass0)
    total_drift_rel = float(abs(mass_t[-1] - mass0) / mass0)

    # wall-temperature realization at the callback instants: realized (audited)
    # row temperature vs the exact per-step imposed value (paired one-to-one)
    arrays = recorder.as_arrays()
    theta_target = np.asarray(imposed_per_step, dtype=float)
    wall_temp_err_K = float(np.max(np.abs(arrays["theta_wall_lu"] - theta_target)) * temp_scale)
    if int(np.sum(arrays["steps"] * dt >= settle_periods / frequency_hz)) < 14:
        raise RuntimeError("audit window too short for harmonic components")

    # audit harmonics (0f..3f)
    audit = {}
    for series in ("dm_rel", "u_normal_over_c0", "u_tangential_over_c0"):
        audit[series] = harmonic_components(
            recorder, series, dt_s=dt, frequency_hz=frequency_hz,
            settle_periods=settle_periods)

    log("run %-26s eps=%-6g |p1f|=%.4e q1f=%.4e dm_max=%.2e u_n=%.2e Terr=%.2e K" % (
        wall, epsilon, fit_p.amplitude(1), fit_q.amplitude(1),
        audit["dm_rel"]["max_component"], audit["u_normal_over_c0"]["max_component"],
        wall_temp_err_K))
    return {
        "wall": wall, "epsilon": epsilon, "finite": finite,
        "solver_meta": {"ny": solver.ny, "nx": solver.nx, "dt_s": dt,
                        "steps_per_period": steps_per_period, "n_steps": n_steps},
        "t_s": t_s, "p_box_lu": p_box, "q_moment_si": q_mom, "mass": mass_t,
        "t_rows_lu": t_rows, "theta_imposed_lu": theta_imposed,
        "uy_rows_lu": uy_rows, "p_rows_lu": p_rows,
        "fit_p": fit_p, "fit_q": fit_q, "fit_p_window2": fit_p2,
        "recorder": recorder, "audit": audit,
        "window_dm_rel": window_dm_rel, "total_drift_rel": total_drift_rel,
        "wall_temp_err_K": wall_temp_err_K, "theta_hat_lu": theta_hat,
        "theta0_lu": theta0, "mass0": mass0,
    }


def energy_channel_Y_over_Yhs(run: dict, omega_lu: float, alpha_nom: float,
                              gamma: float) -> complex:
    """Calibration-free sealed energy readout: q_side = i*Omega*(N/2)*p_box/(gamma-1)."""

    ny = run["solver_meta"]["ny"]
    p_hat_lu = run["fit_p"].harmonic(1)
    q_side_lu = 1j * omega_lu * (ny / 2.0) * p_hat_lu / (gamma - 1.0)
    # Y_hs in the same rho*cp-explicit LU convention: k_lu = rho*cp*alpha = (gamma/(gamma-1))*alpha
    y_hs_lu = (gamma / (gamma - 1.0)) * alpha_nom * complex(np.sqrt(1j * omega_lu / alpha_nom))
    return (q_side_lu / run["theta_hat_lu"]) / y_hs_lu


# ---------------------------------------------------------------------------
# main gate
# ---------------------------------------------------------------------------


def run_g1w(config_path: Path, output_root: Path | None = None, smoke: bool = False) -> dict[str, Any]:
    cfg = load_config(config_path)
    proto = cfg["g1w_smoke"] if smoke else cfg["g1w"]
    gates = cfg["gates"]
    gas_cfg_path = Path(cfg["inheritance"]["gas_config_path"])
    repo_root = Path(__file__).resolve().parents[1]

    def log(msg: str) -> None:
        print(f"G1W {msg}", flush=True)

    def make_gas(ny: int, nx: int) -> dict:
        gas = load_config(gas_cfg_path)
        gas["numerics"] = {**gas.get("numerics", {}), "nx": nx, "ny": ny}
        return gas

    frequency = float(proto["frequency_Hz"])
    ny = int(proto["ny"])
    nx = int(proto["nx"])
    gas_cfg = make_gas(ny, nx)
    probe_solver = GasSolver2D(make_gas(8, 4))
    mapping = probe_solver.mapping
    alpha_nom = float(mapping.alpha_lu)
    gamma = float(mapping.physical.gamma)
    dt = float(mapping.lattice.dt_s)
    omega_lu = 2.0 * math.pi * frequency * dt
    temp_scale = float(mapping.temperature_scale)
    kg_si = float(getattr(mapping.physical, "kg_W_mK", 0.0263))
    alpha_si = alpha_nom * mapping.lattice.dx_m**2 / dt

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = Path(output_root) if output_root else repo_root / "results" / "phase5" / CASE_FAMILY
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    h5 = h5py.File(out_dir / "signals.h5", "w")

    # ---- alpha_eff(k) table: G0 authoritative + in-run extension ----
    g0_rows = load_g0_alpha_rows(repo_root / G0_TABLE_CSV)
    ext_rows = measure_extension_rows(
        make_gas(8, 4), [int(n) for n in proto["alpha_extension_ny"]], alpha_nom, log)
    all_rows = sorted(g0_rows + [(r["k_lu"], r["alpha_eff_lu"]) for r in ext_rows])
    k_tab = np.array([r[0] for r in all_rows])
    a_tab = np.array([r[1] for r in all_rows])
    grp = h5.create_group("alpha_eff_table")
    grp.create_dataset("k_lu", data=k_tab)
    grp.create_dataset("alpha_eff_lu", data=a_tab)
    grp.attrs["g0_source"] = str(G0_TABLE_CSV)
    grp.attrs["extension_note"] = ("high-k rows measured in-run with the frozen G0 "
                                   "instrument (300 K isobaric y); interpolation only "
                                   "within measured range")

    # ---- sealed spectral reference (primary + policy band) ----
    refs = {}
    for pol in ("hold_last", "nominal"):
        for gam_name, gam in (("gamma_nominal", gamma), ("gamma_eff_g0", GAMMA_EFF_G0_K1)):
            refs[f"{pol}|{gam_name}"] = sealed_spectral_reference(
                ny, omega_lu, alpha_nom, k_tab, a_tab, highk_policy=pol, gamma=gam)
    primary_key = f"{proto['highk_policy_primary']}|gamma_nominal"
    y_ref_primary = refs[primary_key]["Y_over_Yhs"]
    band = [v["Y_over_Yhs"] for v in refs.values()]
    log("sealed reference primary=%s: %.4f@%+.2f deg (band %.4f..%.4f)" % (
        primary_key, abs(y_ref_primary),
        math.degrees(math.atan2(y_ref_primary.imag, y_ref_primary.real)),
        min(abs(b) for b in band), max(abs(b) for b in band)))
    rg = h5.create_group("sealed_reference")
    for key, v in refs.items():
        gg = rg.create_group(key.replace("|", "_"))
        gg.create_dataset("profile_over_Tw_re", data=v["profile_over_Tw"].real)
        gg.create_dataset("profile_over_Tw_im", data=v["profile_over_Tw"].imag)
        gg.attrs["Y_over_Yhs_re"] = v["Y_over_Yhs"].real
        gg.attrs["Y_over_Yhs_im"] = v["Y_over_Yhs"].imag

    # ---- driven matrix ----
    common = dict(frequency_hz=frequency, periods=float(proto["periods"]),
                  settle_periods=float(proto["settle_periods"]),
                  samples_per_period=int(proto["samples_per_period"]),
                  grad_extrap_old=str(proto.get("grad_extrap_old", "linear")),
                  ramp_periods=float(proto.get("ramp_periods", 1.0)), log=log)
    runs: dict[str, dict[str, Any]] = {}
    for eps in proto["epsilon_ladder_mn"]:
        r = run_driven(make_gas(ny, nx), "mass_neutral_v1p1", float(eps), **common)
        runs[f"mn_{eps:g}"] = r
        y_e = energy_channel_Y_over_Yhs(r, omega_lu, alpha_nom, gamma)
        log("  mn eps=%g energy-channel Y/Yhs = %.4f@%+.2f deg" % (
            eps, abs(y_e), math.degrees(math.atan2(y_e.imag, y_e.real))))
    for eps in proto["epsilon_ladder_old"]:
        runs[f"old_{eps:g}"] = run_driven(make_gas(ny, nx), "pressure_preserving_grad", float(eps), **common)
    # signed pair with its own pre-registered transient discipline (identical
    # +/- protocols; the odd-combination floor needs the long-settle ramp)
    pair_proto = proto["pair"]
    pair_eps = float(pair_proto["epsilon"])
    pair_common = dict(common, periods=float(pair_proto["periods"]),
                       settle_periods=float(pair_proto["settle_periods"]),
                       ramp_periods=float(pair_proto["ramp_periods"]))
    runs["mn_pair_plus"] = run_driven(make_gas(ny, nx), "mass_neutral_v1p1", pair_eps, **pair_common)
    runs["mn_pair_minus"] = run_driven(make_gas(ny, nx), "mass_neutral_v1p1", -pair_eps, **pair_common)

    for label, run in runs.items():
        g = h5.create_group(f"runs/{label}")
        for name in ("t_s", "p_box_lu", "q_moment_si", "mass", "theta_imposed_lu"):
            g.create_dataset(name, data=run[name])
        g.create_dataset("t_rows_lu", data=run["t_rows_lu"])
        for name, arr in run["recorder"].as_arrays().items():
            g.create_dataset(f"audit_{name}", data=arr)
        g.attrs.update({"wall": run["wall"], "epsilon": run["epsilon"],
                        "window_dm_rel": run["window_dm_rel"],
                        "total_drift_rel": run["total_drift_rel"],
                        "wall_temp_err_K": run["wall_temp_err_K"]})

    mn_small = runs[f"mn_{proto['epsilon_ladder_mn'][0]:g}"]
    old_small = runs.get(f"old_{proto['epsilon_ladder_old'][0]:g}")
    mn_prod = [runs[f"mn_{eps:g}"] for eps in proto["epsilon_ladder_mn"]]

    # ---- row 5: admittance regression (energy channel vs sealed spectral ref) ----
    y_energy = energy_channel_Y_over_Yhs(mn_small, omega_lu, alpha_nom, gamma)
    reg = _ratio(y_energy, y_ref_primary)
    reg_band = {k: _ratio(y_energy, v["Y_over_Yhs"]) for k, v in refs.items()}
    # window-pair sensitivity on the energy channel (U_det proxy)
    p2 = mn_small["fit_p_window2"].harmonic(1)
    y_energy_w2 = y_energy * (p2 / mn_small["fit_p"].harmonic(1))
    u_det_window = abs(y_energy_w2 / y_energy - 1.0)

    # moment-channel recalibration constant (§23 archived input; NOT a gate row)
    y_hs_si = thermal_admittance_halfspace(frequency, kg=kg_si, alpha0=alpha_si)
    t_hat_si = mn_small["theta_hat_lu"] * temp_scale
    y_mom_mn = (mn_small["fit_q"].harmonic(1) / t_hat_si) / y_hs_si
    moment_recal = y_energy / y_mom_mn if abs(y_mom_mn) > 0 else complex("nan")

    # old-wall chain validation (moment channel vs half-space, M3 caliber)
    chain = None
    if old_small is not None:
        y_old = (old_small["fit_q"].harmonic(1) / (old_small["theta_hat_lu"] * temp_scale)) / y_hs_si
        chain = {"Y_over_Yhs": _cplx(y_old), "vs_M3": _ratio(y_old, 0.9468 * complex(
            math.cos(math.radians(2.198)), math.sin(math.radians(2.198))))}

    # profile check (supporting, non-gating): measured T row profile vs spectral prediction
    def profile_check(run: dict) -> dict[str, float]:
        mask = run["t_s"] >= common["settle_periods"] / frequency * (1.0 - 1e-12)
        t_fit = run["t_s"][mask]
        prof_ref = refs[primary_key]["profile_over_Tw"]
        devs = []
        rows = range(1, min(run["solver_meta"]["ny"], len(prof_ref)))
        for iy in rows:
            fit = fit_multiharmonic(t_fit, run["t_rows_lu"][mask, iy], 2.0 * math.pi * frequency,
                                    n_harmonics=1)
            meas = fit.harmonic(1) / run["theta_hat_lu"]
            devs.append(abs(meas - prof_ref[iy]))
        scale = max(abs(prof_ref[1]), 1e-30)
        return {"rms_dev_over_row1": float(np.sqrt(np.mean(np.square(devs))) / scale),
                "max_dev_over_row1": float(np.max(devs) / scale)}

    profile = profile_check(mn_small)
    log("regression: energy Y=%.4f@%+.2f  vs ref: %+.2f%%/%+.2f deg  profile rms=%.3f" % (
        abs(y_energy), math.degrees(math.atan2(y_energy.imag, y_energy.real)),
        100 * reg["amp_rel_err"], reg["phase_deg_err"], profile["rms_dev_over_row1"]))

    # ---- row 6: boundary-linear-interior fixture (signed pair, odd combination) ----
    plus = runs["mn_pair_plus"]
    minus = runs["mn_pair_minus"]
    mask = plus["t_s"] >= float(pair_proto["settle_periods"]) / frequency * (1.0 - 1e-12)
    t_fit = plus["t_s"][mask]
    fixture = {}
    for sig in ("q_moment_si", "p_box_lu"):
        odd = 0.5 * (plus[sig][mask] - minus[sig][mask])
        even = 0.5 * (plus[sig][mask] + minus[sig][mask])
        fit_odd = fit_multiharmonic(t_fit, odd, 2.0 * math.pi * frequency, n_harmonics=3)
        fit_even = fit_multiharmonic(t_fit, even, 2.0 * math.pi * frequency, n_harmonics=3)
        leak = fit_odd.leakage_relative(target=1)
        fixture[sig] = {"odd_2f_rel": float(leak[2]), "odd_3f_rel": float(leak[3]),
                        "even_2f_abs": float(fit_even.amplitude(2)),
                        "even_2f_rel_1f": float(fit_even.amplitude(2) / fit_odd.amplitude(1))}
    fixture_max = max(max(v["odd_2f_rel"], v["odd_3f_rel"]) for v in fixture.values())
    log("fixture odd-pair: q 2f=%.2e 3f=%.2e | p 2f=%.2e 3f=%.2e" % (
        fixture["q_moment_si"]["odd_2f_rel"], fixture["q_moment_si"]["odd_3f_rel"],
        fixture["p_box_lu"]["odd_2f_rel"], fixture["p_box_lu"]["odd_3f_rel"]))

    # ---- row 7: old-vs-new difference audit ----
    def g1_of(run: dict) -> float:
        return float(run["fit_q"].amplitude(1) / (run["theta_hat_lu"] * temp_scale))

    def h_rel(run: dict, n: int, sig: str = "fit_p") -> float:
        fit = run[sig]
        return float(fit.amplitude(n) / max(fit.amplitude(1), 1e-300))

    def dc_shift(run: dict) -> float:
        return float(abs(run["fit_p"].trend_coeffs_raw[0]
                         - run["theta0_lu"] * mapping.lattice.rho_ref_lu)
                     / (run["theta0_lu"] * mapping.lattice.rho_ref_lu))

    eps_hi = float(proto["epsilon_ladder_old"][-1])
    mn_hi, old_hi = runs[f"mn_{eps_hi:g}"], runs[f"old_{eps_hi:g}"]
    eps_lo_old = float(proto["epsilon_ladder_old"][0])
    diff_audit = {
        "epsilon_compare": eps_hi,
        "D_G": {"mn": abs(g1_of(mn_hi) / g1_of(runs[f"mn_{eps_lo_old:g}"]) - 1.0),
                "old": abs(g1_of(old_hi) / g1_of(runs[f"old_{eps_lo_old:g}"]) - 1.0)},
        "H2_pbox": {"mn": h_rel(mn_hi, 2), "old": h_rel(old_hi, 2)},
        "H3_pbox": {"mn": h_rel(mn_hi, 3), "old": h_rel(old_hi, 3)},
        "DC_pbox_rel": {"mn": dc_shift(mn_hi), "old": dc_shift(old_hi)},
        "DC_mass_flux_0f": {"mn": mn_hi["audit"]["dm_rel"]["components"][0],
                            "old": old_hi["audit"]["dm_rel"]["components"][0]},
        "mass_flux_1f": {"mn": mn_hi["audit"]["dm_rel"]["components"][1],
                         "old": old_hi["audit"]["dm_rel"]["components"][1]},
    }
    frac = float(gates["old_wall_difference_fraction"])
    old_diagnostic_only = False
    for qname, d in diff_audit.items():
        if not isinstance(d, dict) or "mn" not in d:
            continue
        gap = abs(d["mn"] - d["old"])
        thresh = max(u_det_window, frac * max(abs(d["mn"]), abs(d["old"])))
        d["difference"] = gap
        d["threshold"] = thresh
        d["exceeds"] = bool(gap > thresh and max(abs(d["mn"]), abs(d["old"])) > 0)
        old_diagnostic_only = old_diagnostic_only or d["exceeds"]

    # ---- gate rows ----
    def mn_component_max(series: str) -> float:
        return max(r["audit"][series]["max_component"] for r in mn_prod)

    mass_flux_max = mn_component_max("dm_rel")
    u_n_max = mn_component_max("u_normal_over_c0")
    u_t_mean_max = max(r["audit"]["u_tangential_over_c0"]["components"][0] for r in mn_prod)
    window_mass_max = max(r["window_dm_rel"] for r in mn_prod)
    cumulative_max = max(max(r["total_drift_rel"],
                             r["recorder"].cumulative_mass_drift_rel()) for r in mn_prod)
    wall_temp_max = max(r["wall_temp_err_K"] for r in mn_prod)
    finite_all = all(r["finite"] for r in runs.values())

    gate_rows = {
        "normal_mass_flux_components": {
            "value_max_0f_3f": mass_flux_max, "gate": float(gates["mass_flux_component"]),
            "normalization": NORMALIZATION_DEFINITION,
            "passed": bool(mass_flux_max <= float(gates["mass_flux_component"]))},
        "global_mass": {
            "window_max": window_mass_max, "gate_window": float(gates["mass_window_rel"]),
            "cumulative_max": cumulative_max, "gate_cumulative": float(gates["mass_cumulative_rel"]),
            "passed": bool(window_mass_max <= float(gates["mass_window_rel"])
                           and cumulative_max <= float(gates["mass_cumulative_rel"]))},
        "impermeability_no_slip": {
            "u_normal_max_0f_3f_over_c0": u_n_max,
            "u_tangential_mean_over_c0": u_t_mean_max,
            "gate": float(gates["velocity_over_c0"]),
            "passed": bool(u_n_max <= float(gates["velocity_over_c0"])
                           and u_t_mean_max <= float(gates["velocity_over_c0"]))},
        "wall_temperature_realization": {
            "max_error_K": wall_temp_max, "gate_K": float(gates["wall_temperature_error_K"]),
            "note": "callback-instant realization (audit series); end-of-step readback "
                    "perturbation by the global corrections is the documented M3 plumbing note",
            "passed": bool(wall_temp_max <= float(gates["wall_temperature_error_K"]))},
        "admittance_regression": {
            "channel": "sealed energy balance (calibration-free)",
            "reference": f"lbm-equivalent sealed spectral reference [{primary_key}]",
            "Y_measured_over_Yhs": _cplx(y_energy),
            "Y_reference_over_Yhs": _cplx(y_ref_primary),
            "amp_rel_err": reg["amp_rel_err"], "phase_deg_err": reg["phase_deg_err"],
            "gate_amp": float(gates["admittance_amp_rel"]),
            "gate_phase_deg": float(gates["admittance_phase_deg"]),
            "policy_band": {k: v for k, v in reg_band.items()},
            "window_sensitivity_rel": float(u_det_window),
            "profile_check_supporting": profile,
            "passed": bool(abs(reg["amp_rel_err"]) <= float(gates["admittance_amp_rel"])
                           and abs(reg["phase_deg_err"]) <= float(gates["admittance_phase_deg"]))},
        "boundary_linear_interior_fixture": {
            "odd_pair_nontarget": fixture, "value_max": fixture_max,
            "gate": float(gates["fixture_nontarget_rel"]),
            "passed": bool(fixture_max <= float(gates["fixture_nontarget_rel"]))},
        "old_wall_difference_audit": {
            "table": diff_audit,
            "old_wall_marking": "DIAGNOSTIC_ONLY" if old_diagnostic_only else "no_material_difference",
            "chain_validation_old_wall_vs_M3": chain,
            "passed": True},
        "numerical_discipline": {
            "no_clipping": True, "no_floor": True, "no_positivity_repair": True,
            "finite": finite_all,
            "constraint_residual_note": "v1.1 removes blended-neq mass/momentum exactly via "
                                        "the equilibrium increment; the per-step audited "
                                        "dm_rel IS the residual (machine level)",
            "passed": bool(finite_all)},
    }

    hard = ["normal_mass_flux_components", "global_mass", "impermeability_no_slip",
            "wall_temperature_realization", "numerical_discipline"]
    soft = ["admittance_regression", "boundary_linear_interior_fixture"]
    if all(gate_rows[k]["passed"] for k in hard):
        verdict = "PASSED" if all(gate_rows[k]["passed"] for k in soft) else "SCOPED_CANDIDATE"
    else:
        verdict = "FAILED"
    log("verdict=%s (old wall: %s)" % (verdict, gate_rows["old_wall_difference_audit"]["old_wall_marking"]))

    # ---- outputs (contract §16.1) ----
    resolved = {"gate_id": GATE_ID, "case_family": CASE_FAMILY, "smoke_mode": smoke,
                "protocol": proto, "gates": gates,
                "gas_config": str(gas_cfg_path), "config_path": str(config_path)}
    config_yaml = yaml.safe_dump(resolved, allow_unicode=True, sort_keys=False)
    (out_dir / "config_resolved.yaml").write_text(config_yaml, encoding="utf-8")

    harmonic_payloads = {
        "mn_small_p_box": mn_small["fit_p"].to_json_payload(),
        "mn_small_q_moment": mn_small["fit_q"].to_json_payload(),
    }
    if old_small:
        harmonic_payloads["old_small_q_moment"] = old_small["fit_q"].to_json_payload()
    (out_dir / "harmonic_fit.json").write_text(
        json.dumps(harmonic_payloads, indent=1, default=float), encoding="utf-8")

    na = "not_applicable_g1w"
    summary = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "code_commit": _git_commit(),
        "config_digest": hashlib.sha256(config_yaml.encode()).hexdigest()[:12],
        "physics_core_digest": hashlib.sha256(
            b"".join((repo_root / p).read_bytes() for p in (
                "boundary/wall_thermal_mass_neutral.py", "boundary/wall_mass_audit.py",
                "boundary/wall_thermal_grad.py", "postproc/multiharmonic_fit.py"))
        ).hexdigest()[:12],
        "parent_baseline_run": PARENT_BASELINE_RUN,
        "phase5_contract_version": PHASE5_CONTRACT_VERSION,
        "work_package": "WP2", "gate_id": GATE_ID, "case_family": CASE_FAMILY,
        "model_route": "ROUTE_B_MAIN",
        "property_model_id": "frozen_dx2p6_stack + alpha_eff(k) table (G0 + in-run extension)",
        "tau_policy": "frozen dx2p6 mapping (inherited, unchanged)",
        "mapping_digest": hashlib.sha256(str(sorted({
            "dx": mapping.lattice.dx_m, "dt": dt, "alpha_lu": alpha_nom}.items())).encode()
        ).hexdigest()[:12],
        "background_path": "uniform_theta0_reference",
        "forcing_protocol": "prescribed_sinusoidal_wall_temperature (G1a analog)",
        "P_mean_W_m2": 0.0, "P_mean_rematched": False, "target_Theta_DC": 0.0,
        "frequency_Hz": frequency, "T_ambient_K": 300.0, "T_mean_K": 300.0,
        "epsilon_AC_measured": {"mn_ladder": list(proto["epsilon_ladder_mn"]),
                                "old_ladder": list(proto["epsilon_ladder_old"]),
                                "pair": pair_eps},
        "Theta_DC_measured": 0.0, "chi_0": None, "chi_eff": None, "C_A_J_m2K": None,
        "dc_heat_sink_model": na + " (sealed periodic rig; canonical sink enters at G4a)",
        "dc_heat_sink_parameters": None, "H_s_role": "sealed rig height (ny)",
        "thermal_resistance_effective": None,
        "grid_shape": [ny, nx], "dx_m": mapping.lattice.dx_m, "dt_s": dt,
        "domain_height_m": ny * mapping.lattice.dx_m,
        "boundary_model": "v1.1 symmetric mass-neutral Grad wall (production candidate) "
                          "+ pressure_preserving Grad wall (diagnostic contrast)",
        "wall_mass_policy": "mass_neutral_by_construction (v1.1)",
        "wall_neutrality_gate_id": f"{GATE_ID}/{run_id}",
        "boundary_mass_flux_definition": NORMALIZATION_DEFINITION,
        "boundary_mass_flux_0f_to_3f": [
            mn_small["audit"]["dm_rel"]["components"][n] for n in range(4)],
        "spectral_operator_stack_id": "frozen_dx2p6_dispersion_correction_stack",
        "spectral_correction_enabled": True,
        "high_wavenumber_filter_enabled": False, "high_wavenumber_filter_strength": 0.0,
        "operator_ablation_run_id": None, "q_feedback_relax": None,
        "fit_window": {"settle_periods": proto["settle_periods"],
                       "fit_periods": float(proto["periods"]) - float(proto["settle_periods"])},
        "fit_cycles": float(proto["periods"]) - float(proto["settle_periods"]),
        "detrend_order": 0, "harmonic_order_max": 3,
        "harmonic_fit_condition_number": harmonic_payloads["mn_small_p_box"][
            "harmonic_fit_condition_number"],
        "U_det": {"window_pair_rel": float(u_det_window)},
        "U95_fit": {"p_box_1f_amp": harmonic_payloads["mn_small_p_box"]["amplitude_u95_fit"][0]},
        "U_gov": float(max(u_det_window,
                           harmonic_payloads["mn_small_p_box"]["amplitude_u95_fit"][0]
                           / max(harmonic_payloads["mn_small_p_box"]["amplitude"][0], 1e-300))),
        "no_clipping": True, "no_floor": True, "no_positivity_repair": True,
        "gate_status": verdict,
        "scoped_limitations": ([] if verdict == "PASSED" else
                               ["regression/fixture row outside gate; see gate_evaluation"]),
        "smoke_mode": smoke,
        "results": {
            "T_s_hat_1f": _cplx(mn_small["theta_hat_lu"] * temp_scale + 0j),
            "p_hat_1f": _cplx(mn_small["fit_p"].harmonic(1)),
            "p_hat_2f": _cplx(mn_small["fit_p"].harmonic(2)),
            "p_hat_3f": _cplx(mn_small["fit_p"].harmonic(3)),
            "outgoing_mode_1f": None, "outgoing_mode_2f": None, "outgoing_mode_3f": None,
            "outgoing_mode_note": "sealed rig has no outgoing mode; G2 quantity",
            "G1": float(g1_of(mn_small)), "D_G": diff_audit["D_G"],
            "D_OP": None, "D_OP_note": "A2a quantity (G4a)",
            "H2": h_rel(mn_hi, 2), "H3": h_rel(mn_hi, 3),
            "m1": None, "m2": None, "m3": None,
            "m_note": "scaling exponents belong to G1a/production; ladder harmonics archived",
            "QS0_error_amplitude": None, "QS0_error_phase": None,
            "QS1_error_amplitude": None, "QS1_error_phase": None,
            "QS_note": na,
            "wall_boundary_sensitivity": {
                "moment_channel_recalibration_Y_energy_over_Y_moment": _cplx(moment_recal),
                "note": "§23 pre-registered wall-change recalibration input; archived, "
                        "not used to pass any gate row"},
            "operator_sensitivity_D_G": None, "operator_sensitivity_H2": None,
            "operator_sensitivity_H3": None, "operator_note": "G2-O quantity",
            "boundary_mass_flux_0f_to_3f": [
                mn_small["audit"]["dm_rel"]["components"][n] for n in range(4)],
            "energy_residual": None,
            "energy_residual_note": "sealed energy identity IS the readout; its closure vs "
                                    "the spectral reference is the regression row",
            "mass_or_flux_residual": float(cumulative_max),
            "wall_temperature_error": float(wall_temp_max),
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=float),
                                          encoding="utf-8")
    provenance = {
        "run_id": run_id, "command": " ".join(sys.argv),
        "python": sys.version.split()[0], "numpy": np.__version__,
        "code_commit": summary["code_commit"],
        "physics_core_digest": summary["physics_core_digest"],
        "gas_config_sha256": sha256_file(gas_cfg_path),
        "g0_table_source": str(G0_TABLE_CSV),
        "alpha_extension_rows": ext_rows,
        "stage1_attribution": "scratchpad probe 2026-07-26: alpha_eff(k) spectral sealed "
                              "reference closes the WP1-3 +13%/+20 deg energy excess",
    }
    (out_dir / "provenance.json").write_text(json.dumps(provenance, indent=1, default=float),
                                             encoding="utf-8")
    gate_eval = {"gate_id": GATE_ID, "verdict": verdict, "rows": gate_rows}
    (out_dir / "gate_evaluation.json").write_text(
        json.dumps(gate_eval, indent=1, default=float), encoding="utf-8")

    report = [f"# G1-W run {run_id}", "",
              f"- verdict: **{verdict}** (script-emittable; scoped upgrades are user decisions)",
              f"- smoke_mode: {smoke}",
              f"- old wall marking: {gate_rows['old_wall_difference_audit']['old_wall_marking']}",
              "", "## Gate rows (contract §6.1)", ""]
    for name, row in gate_rows.items():
        keep = {k: v for k, v in row.items()
                if k not in ("passed", "table", "policy_band", "odd_pair_nontarget",
                             "chain_validation_old_wall_vs_M3", "profile_check_supporting")}
        report.append(f"- {name}: passed={row['passed']}  "
                      + json.dumps(keep, default=float)[:240])
    (out_dir / "run_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    h5.close()
    log(f"outputs -> {out_dir}")
    return {"verdict": verdict, "out_dir": str(out_dir), "summary": summary,
            "gate_rows": gate_rows, "refs": {k: _cplx(v["Y_over_Yhs"]) for k, v in refs.items()}}


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase_5 G1-W wall-neutrality gate runner")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--smoke", action="store_true",
                        help="machinery run (diagnostic frequency, small rig); not authoritative")
    parser.add_argument("--output-root", type=Path, default=None)
    args = parser.parse_args()
    result = run_g1w(args.config, args.output_root, smoke=args.smoke)
    return 0 if result["verdict"] in {"PASSED", "SCOPED_CANDIDATE"} else 1


if __name__ == "__main__":
    sys.exit(main())
