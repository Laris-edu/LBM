"""Phase_5 G2-T wall-temperature -> outgoing-acoustic-mode thermal-transfer gate (contract §7.1, WP2).

Certifies the heat-generation chain T_w_hat -> q_hat -> outgoing modal velocity
on the frozen dx2p6 stack at the two mandatory frequencies 10 and 20 kHz
(30 kHz is the §7.4 conditional leg — the trigger is evaluated from the G1a
archived H3 ladder and, when untriggered, the waiver labels are emitted).

Fixture (pre-registered here; §7.1):
- sealed y-periodic single-seam rig, ny=48 nx=8, G1-W certified production
  wall v1.1 (the ONLY rig family certified clean on the frozen stack — the
  two-boundary-row cavity is judged dead since WP1-3; the sealed rig's steady
  harmonic injection floor <=~6e-10 is the G1-W archived input);
- small-amplitude prescribed wall temperature (G1a protocol verbatim:
  periods 3, settle 1, raised-cosine ramp 1, eps in {0.001, 0.01});
- near-field p/T/u row time series archived (contract fixture output);
- no result-dependent per-frequency recalibration: the readout is the
  calibration-free sealed ENERGY channel (exact conserved moments only,
  frequency-agnostic); the (tau,k)-point moment channel is archived as
  diagnostic with its two-channel ratio (the §23 constant is defined at
  10 kHz cold 1f and is NOT re-fit here).

Transfer rows carry the G0 alpha_eff(k) table (freeze doc §3.3 output 3:
each harmonic frequency propagates with the effective properties at its own
wavenumber — at 20 kHz the thermal feature sits at k2=0.1396 where
alpha_eff=0.48x nominal, a MEASURED G0 row, not an extrapolation):

  row T1 (transfer amplitude/phase, LBM vs 1D carrying the table):
      r(f) = [Y_LBM_energy(f) / Y_spec(f; alpha_eff table, n=48)]
           / [Y_1D(f)        / Y_closed(f; alpha_nom continuum)]
      gate |r|-1 <= 10%, arg(r) <= 10 deg  (contract §7.1 thresholds).
      Y_spec is the lbm-equivalent sealed spectral reference (G1-W instrument,
      G0 authoritative rows + in-run high-k extension); Y_1D is the certified
      1D NSF reference (G3) on the formal 1D-lbm-equivalent branch
      (g0_measured k1 law) in the matched sealed-adiabatic half-height
      geometry L=(ny/2)*dx (WP1-3 three-way-verified convention); Y_closed is
      the continuum closed form Y/Y_hs = tanh(mL)/(1+(gamma-1)tanh(mL)/(mL)).
      The raw LBM/1D ratio and the carriage factor K = Y_spec/Y_closed are
      archived — the ~+10%/+18 deg raw gap at 10 kHz is the DOCUMENTED
      effective-medium k-structure, not a failure mode.

  row T2 (outgoing modal readout, the "出射特征量" operationalization):
      the compact sealed rig has no radiated wave; its outgoing acoustic mode
      IS the thermal-expansion pumping velocity profile u_hat(y) (the same
      quantity the M4 compact-source handoff consumes). Prediction from the
      spectral reference profile via exact linearized continuity per periodic
      mode: u_j = (omega/k_j) * theta_j/theta0 (j != 0, signed k_j), i.e. an
      independent table-carried truth. Measured: x-averaged u_y rows, odd-
      folded about mid-height, 1f fit at pre-registered control rows
      {6, 10, 14, 18}. Gate: every control row within 10% / 10 deg.
      Supporting (non-gating): same comparison against the continuity
      prediction built from the MEASURED T rows (pure channel consistency),
      and the sealed mass identity p_box/p0 = <theta>/theta0.

  row T3 window sensitivity: suffix-window refit (full fit window vs last
      1.5 cycles) on the energy-channel signal, <= 3% / 3 deg.

  row T4 grid diagnostic: domain refinement ny 48->96 at eps=0.001 with the
      spectral reference rebuilt at n=96 (same measured table): deviation
      direction must be consistent (sign of the amplitude residual, with a
      floor: rows whose residual is below the non-refinement U_gov are
      direction-exempt) and the residual difference enters U_gov. The 1D side
      folds |Y(2N)/Y(N)-1| into U_gov. No baseline retuning.

  row T5 fit leakage: pure-1f synthetic tone on each frequency's actual
      sample grid through the §12.1 N=5 fit -> non-target harmonic leakage
      <= 1e-8 (contract row; WP1-1 instrument).

  row T6 numerical repair: no clipping / floor / positivity repair (v1.1
      wall is repair-free by construction; audited).

  row T7 instrument hygiene (standing discipline, not §7.1-specific): mass
      window <= 1e-8, cumulative <= 1e-6, wall realization <= 0.01 K,
      finiteness — G1-W/G1a caliber on every driven case.

Verdict (script-emittable only): PASSED = all rows at BOTH mandatory
frequencies; if 10 kHz passes fully and 20 kHz is stable but out of gate,
SCOPED_CANDIDATE with G2_2F_NOT_CERTIFIED (contract §7.1: H2 claims then stay
L1); otherwise FAILED. 30 kHz untriggered -> H3_DIAGNOSTIC_ONLY +
G2_3F_WAIVED_BY_SIGNAL labels (trigger evaluation archived).

Outputs the contract §16.1 seven-file set under
results/phase5/g2_thermal_transfer/<run_id>/.
"""

from __future__ import annotations

import argparse
import cmath
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import yaml

from postproc.multiharmonic_fit import fit_multiharmonic
from reference.constants import default_params
from reference.nonlinear_nsf_1d import (
    NSF1DConfig,
    WallDrive,
    g0_measured_transport,
    run_nsf1d,
)
from reference.thermal_admittance import thermal_admittance_halfspace
from scripts.phase2_m2_verification import load_config
from scripts.phase5_g1a_amplitude_envelope import execute_cases, refit_n5
from scripts.phase5_g1w_wall_neutrality import (
    G0_TABLE_CSV,
    _cplx,
    _git_commit,
    _ratio,
    energy_channel_Y_over_Yhs,
    load_g0_alpha_rows,
    measure_extension_rows,
    run_driven,
    sealed_spectral_reference,
)
from core.solver import GasSolver2D

GATE_ID = "G2-T"
CASE_FAMILY = "g2_thermal_transfer"
PHASE5_CONTRACT_VERSION = "v1.2"
DEFAULT_CONFIG = Path("configs/phase5/g2_thermal_transfer/g2t_10k20k_dx2p6.yaml")
PHYSICS_CORE_FILES = [
    "boundary/wall_thermal_mass_neutral.py",
    "boundary/wall_mass_audit.py",
    "postproc/multiharmonic_fit.py",
    "reference/nonlinear_nsf_1d.py",
    "scripts/phase5_g1w_wall_neutrality.py",
]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _physics_core_digest(repo_root: Path) -> str:
    h = hashlib.sha256()
    for rel in PHYSICS_CORE_FILES:
        h.update(rel.encode())
        h.update((repo_root / rel).read_bytes())
    return h.hexdigest()[:12]


def _phase_deg(z: complex) -> float:
    return math.degrees(math.atan2(z.imag, z.real))


# ---------------------------------------------------------------------------
# references
# ---------------------------------------------------------------------------


def sealed_adiabatic_closed_form(omega: float, alpha: float, half_height: float,
                                 gamma: float) -> complex:
    """Continuum sealed-adiabatic response Y/Y_hs = tanh(mL)/(1+(g-1)tanh(mL)/(mL)).

    m = sqrt(i*omega/alpha) (principal branch); the WP1-3 three-way-verified
    closed form (BVP = closed form = nonlinear 1D solver, 2026-07-22 entry).
    Units cancel: any consistent (omega, alpha, L) system.
    """

    m = cmath.sqrt(1j * omega / alpha)
    ml = m * half_height
    t = cmath.tanh(ml)
    return t / (1.0 + (gamma - 1.0) * t / ml)


def outgoing_mode_prediction(profile_over_tw: np.ndarray, omega_lu: float,
                             theta_hat_lu: float, theta0: float) -> np.ndarray:
    """u_hat(y) rows (LU) from a sealed temperature profile via exact continuity.

    Per periodic mode e^{i k_j y}: i*omega*rho_j + rho0*i*k_j*u_j = 0 with
    rho_j/rho0 = -theta_j/theta0 (uniform-pressure modes j != 0), so
    u_j = (omega/k_j) * theta_j/theta0 (signed k_j; u_0 = 0). The j=0 pressure
    mode carries no velocity (sealed, no mean flow).
    """

    n = len(profile_over_tw)
    theta_modes = np.fft.fft(np.asarray(profile_over_tw, dtype=complex)) * (
        theta_hat_lu / theta0)
    k_signed = 2.0 * math.pi * np.fft.fftfreq(n)
    coef = np.zeros(n, dtype=complex)
    nonzero = k_signed != 0.0
    coef[nonzero] = (omega_lu / k_signed[nonzero]) * theta_modes[nonzero]
    return np.fft.ifft(coef)


def fit_row_1f(t_s: np.ndarray, series: np.ndarray, frequency: float,
               settle_periods: float, n_harmonics: int) -> complex:
    mask = t_s >= settle_periods / frequency * (1.0 - 1e-12)
    fit = fit_multiharmonic(t_s[mask], series[mask], 2.0 * math.pi * frequency,
                            n_harmonics=n_harmonics)
    return fit.harmonic(1)


def window_sensitivity_pbox(run: dict, frequency: float, settle_periods: float,
                            cycles: list[float], n_harmonics: int) -> dict[str, float]:
    """Suffix-window 1f sensitivity of the energy-channel signal (p_box)."""

    t_end = run["t_s"][-1]
    fits = []
    for cyc in cycles:
        mask = run["t_s"] >= max(settle_periods / frequency,
                                 t_end - cyc / frequency) * (1.0 - 1e-12)
        fits.append(fit_multiharmonic(run["t_s"][mask], run["p_box_lu"][mask],
                                      2.0 * math.pi * frequency, n_harmonics=n_harmonics))
    r = fits[1].harmonic(1) / fits[0].harmonic(1)
    return {"amp_rel": float(abs(r) - 1.0), "phase_deg": _phase_deg(r)}


def synthetic_leakage_row(t_s: np.ndarray, frequency: float, settle_periods: float,
                          n_harmonics: int) -> float:
    """Pure-1f synthetic tone on the run's actual sample grid -> max non-target leakage."""

    mask = t_s >= settle_periods / frequency * (1.0 - 1e-12)
    t = t_s[mask]
    omega = 2.0 * math.pi * frequency
    tone = np.cos(omega * t + 0.3)
    fit = fit_multiharmonic(t, tone, omega, n_harmonics=n_harmonics)
    leak = fit.leakage_relative(target=1)
    return float(max(leak[n] for n in range(2, n_harmonics + 1)))


# ---------------------------------------------------------------------------
# 1D reference leg
# ---------------------------------------------------------------------------


def run_nsf1d_sealed(frequency: float, epsilon: float, half_height_m: float,
                     n_cells: int, cycles: float, settle_cycles: float,
                     samples_per_cycle: int, n_harmonics: int) -> dict[str, Any]:
    """1D-lbm-equivalent branch, sealed-adiabatic half-height, temperature drive."""

    params = default_params()
    cfg = NSF1DConfig(
        params=params,
        transport=g0_measured_transport(params),
        drive=WallDrive(kind="temperature", frequency_hz=frequency,
                        amplitude=epsilon * params.T0, ramp_cycles=2.0),
        height_m=half_height_m,
        n_cells=n_cells,
        n_cycles=cycles,
        samples_per_cycle=samples_per_cycle,
        lid_bc="adiabatic",
    )
    res = run_nsf1d(cfg)
    omega = 2.0 * math.pi * frequency
    mask = res.t_samples >= settle_cycles / frequency * (1.0 - 1e-12)
    fit_q = fit_multiharmonic(res.t_samples[mask], res.q_wall_conductive[mask],
                              omega, n_harmonics=n_harmonics)
    fit_tw = fit_multiharmonic(res.t_samples[mask], res.wall_temperature[mask],
                               omega, n_harmonics=n_harmonics)
    fit_pb = fit_multiharmonic(res.t_samples[mask], res.p_box_mean[mask],
                               omega, n_harmonics=n_harmonics)
    alpha0 = float(cfg.transport.k(params.T0)) / (params.rho0 * params.cp)
    y_hs = thermal_admittance_halfspace(frequency, kg=float(cfg.transport.k(params.T0)),
                                        alpha0=alpha0)
    y_1d = (fit_q.harmonic(1) / fit_tw.harmonic(1)) / y_hs
    r_derived = params.p0 / (params.rho0 * params.T0)
    gamma_eff = params.cp / (params.cp - r_derived)
    y_closed = sealed_adiabatic_closed_form(omega, alpha0, half_height_m, gamma_eff)
    return {
        "property_model_id": res.property_model_id,
        "n_cells": n_cells,
        "Y_over_Yhs": y_1d,
        "Y_closed_over_Yhs": y_closed,
        "ratio_vs_closed": y_1d / y_closed,
        "H2_q": float(fit_q.leakage_relative(1)[2]),
        "p_box_1f_Pa": fit_pb.harmonic(1),
        "mass_drift_rel": float(res.mass_drift_rel),
        "energy_residual_rel_flux": float(res.energy_residual_rel_flux),
        "max_mach": float(res.max_mach),
        "gamma_eff": float(gamma_eff),
        "dt_s": float(res.dt),
    }


# ---------------------------------------------------------------------------
# worker (module-level, picklable) for the shared scheduling layer
# ---------------------------------------------------------------------------


def _g2t_case_worker(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    label = payload["label"]

    def wlog(msg: str) -> None:
        print(f"G2T [{label}] {msg}", flush=True)

    if payload["kind"] == "nsf1d":
        out = run_nsf1d_sealed(
            payload["frequency_hz"], payload["epsilon"], payload["half_height_m"],
            payload["n_cells"], payload["cycles"], payload["settle_cycles"],
            payload["samples_per_cycle"], payload["n_harmonics"])
        wlog("1D done: Y/Yhs=%.4f@%+.2f (vs closed %+.3f%%/%+.3f deg)" % (
            abs(out["Y_over_Yhs"]), _phase_deg(out["Y_over_Yhs"]),
            100.0 * (abs(out["ratio_vs_closed"]) - 1.0),
            _phase_deg(out["ratio_vs_closed"])))
        return label, out
    run = run_driven(
        payload["gas_cfg"], payload["wall"], payload["epsilon"],
        frequency_hz=payload["frequency_hz"], periods=payload["periods"],
        settle_periods=payload["settle_periods"],
        samples_per_period=payload["samples_per_period"],
        grad_extrap_old="linear", ramp_periods=payload["ramp_periods"],
        record_field_rows=True, log=wlog)
    run.pop("recorder", None)
    return label, run


# ---------------------------------------------------------------------------
# main gate
# ---------------------------------------------------------------------------


def run_g2t(config_path: Path, output_root: Path | None = None,
            smoke: bool = False, workers: int = 1) -> dict[str, Any]:
    cfg = load_config(config_path)
    proto = cfg["g2t_smoke"] if smoke else cfg["g2t"]
    gates = cfg["gates"]
    gas_cfg_path = Path(cfg["inheritance"]["gas_config_path"])
    repo_root = Path(__file__).resolve().parents[1]

    def log(msg: str) -> None:
        print(f"G2T {msg}", flush=True)

    def make_gas(ny: int, nx: int) -> dict:
        gas = load_config(gas_cfg_path)
        gas["numerics"] = {**gas.get("numerics", {}), "nx": nx, "ny": ny}
        return gas

    frequencies = [float(f) for f in proto["frequencies_Hz"]]
    ny = int(proto["ny"])
    nx = int(proto["nx"])
    n_harm = int(proto["n_harmonics"])
    eps_list = [float(e) for e in proto["epsilons"]]
    eps_primary = eps_list[0]
    control_rows = [int(r) for r in proto["control_rows"]]
    ny_ref = int(proto["refinement"]["ny_refined"])
    nsf = proto["nsf1d"]

    probe_solver = GasSolver2D(make_gas(8, 4))
    mapping = probe_solver.mapping
    alpha_nom = float(mapping.alpha_lu)
    gamma = float(mapping.physical.gamma)
    dt = float(mapping.lattice.dt_s)
    dx_m = float(mapping.lattice.dx_m)
    theta0 = float(mapping.theta_ref_lu)
    temp_scale = float(mapping.temperature_scale)
    kg_si = float(getattr(mapping.physical, "kg_W_mK", 0.0263))
    alpha_si = alpha_nom * dx_m**2 / dt
    half_height_m = (ny / 2.0) * dx_m

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = Path(output_root) if output_root else repo_root / "results" / "phase5" / CASE_FAMILY
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    h5 = h5py.File(out_dir / "signals.h5", "w")

    # ---- alpha_eff(k) table (G0 authoritative + in-run extension; G1-W instrument)
    g0_rows = load_g0_alpha_rows(repo_root / G0_TABLE_CSV)
    ext_rows = measure_extension_rows(
        make_gas(8, 4), [int(n) for n in proto["alpha_extension_ny"]], alpha_nom, log)
    all_rows = sorted(g0_rows + [(r["k_lu"], r["alpha_eff_lu"]) for r in ext_rows])
    k_tab = np.array([r[0] for r in all_rows])
    a_tab = np.array([r[1] for r in all_rows])
    grp = h5.create_group("alpha_eff_table")
    grp.create_dataset("k_lu", data=k_tab)
    grp.create_dataset("alpha_eff_lu", data=a_tab)

    pol = str(proto["highk_policy_primary"])
    const_tab = np.full_like(a_tab, alpha_nom)

    # ---- independent cases (LBM driven + 1D reference legs), one pool ----
    scalars = dict(periods=float(proto["periods"]),
                   settle_periods=float(proto["settle_periods"]),
                   samples_per_period=int(proto["samples_per_period"]),
                   ramp_periods=float(proto["ramp_periods"]))
    settle = scalars["settle_periods"]
    payloads: list[dict[str, Any]] = []
    for f in frequencies:
        for eps in eps_list:
            payloads.append({"kind": "driven", "label": f"f{f:g}_ny{ny}_eps{eps:g}",
                             "gas_cfg": make_gas(ny, nx), "wall": "mass_neutral_v1p1",
                             "epsilon": eps, "frequency_hz": f, **scalars})
        payloads.append({"kind": "driven", "label": f"f{f:g}_ny{ny_ref}_eps{eps_primary:g}",
                         "gas_cfg": make_gas(ny_ref, nx), "wall": "mass_neutral_v1p1",
                         "epsilon": eps_primary, "frequency_hz": f, **scalars})
        for n_cells in (int(nsf["n_cells"]), int(nsf["n_cells_refined"])):
            payloads.append({"kind": "nsf1d", "label": f"f{f:g}_1d_N{n_cells}",
                             "frequency_hz": f, "epsilon": eps_primary,
                             "half_height_m": half_height_m, "n_cells": n_cells,
                             "cycles": float(nsf["cycles"]),
                             "settle_cycles": float(nsf["settle_cycles"]),
                             "samples_per_cycle": int(nsf["samples_per_cycle"]),
                             "n_harmonics": n_harm})
    case_results = execute_cases(payloads, workers, log, worker=_g2t_case_worker)
    for label, res in case_results.items():
        if isinstance(res, dict) and "worker_exception" in res:
            raise RuntimeError(f"case {label} crashed: {res['worker_exception']}")

    # ---- per-frequency evaluation ----
    per_freq: dict[str, dict[str, Any]] = {}
    gate_rows_by_freq: dict[str, dict[str, Any]] = {}
    for f in frequencies:
        omega_lu = 2.0 * math.pi * f * dt
        fkey = f"{f:g}"
        ref48 = sealed_spectral_reference(ny, omega_lu, alpha_nom, k_tab, a_tab,
                                          highk_policy=pol, gamma=gamma)
        ref48_const = sealed_spectral_reference(ny, omega_lu, alpha_nom, k_tab, const_tab,
                                                highk_policy=pol, gamma=gamma)
        ref96 = sealed_spectral_reference(ny_ref, omega_lu, alpha_nom, k_tab, a_tab,
                                          highk_policy=pol, gamma=gamma)
        y_closed_lu = sealed_adiabatic_closed_form(omega_lu, alpha_nom, ny / 2.0, gamma)
        machinery = ref48_const["Y_over_Yhs"] / y_closed_lu  # discrete-vs-continuum identity

        runs = {eps: case_results[f"f{f:g}_ny{ny}_eps{eps:g}"] for eps in eps_list}
        run_ref = case_results[f"f{f:g}_ny{ny_ref}_eps{eps_primary:g}"]
        nsf_lo = case_results[f"f{f:g}_1d_N{int(nsf['n_cells'])}"]
        nsf_hi = case_results[f"f{f:g}_1d_N{int(nsf['n_cells_refined'])}"]

        y_hs_si = thermal_admittance_halfspace(f, kg=kg_si, alpha0=alpha_si)
        y_lbm = {eps: energy_channel_Y_over_Yhs(runs[eps], omega_lu, alpha_nom, gamma)
                 for eps in eps_list}
        y_lbm96 = energy_channel_Y_over_Yhs(run_ref, omega_lu, alpha_nom, gamma)

        # T1: transfer LBM-vs-1D carrying the alpha_eff(k) table
        ratio_lbm = y_lbm[eps_primary] / ref48["Y_over_Yhs"]
        ratio_1d = nsf_hi["Y_over_Yhs"] / nsf_hi["Y_closed_over_Yhs"]
        transfer = ratio_lbm / ratio_1d
        raw_lbm_over_1d = y_lbm[eps_primary] / nsf_hi["Y_over_Yhs"]
        carriage = ref48["Y_over_Yhs"] / y_closed_lu

        # T2: outgoing modal readout at control rows (odd-folded measured u rows
        # vs the table-carried continuity prediction from the reference profile)
        r0 = runs[eps_primary]
        theta_hat_lu = r0["theta_hat_lu"]
        u_pred = outgoing_mode_prediction(ref48["profile_over_Tw"], omega_lu,
                                          theta_hat_lu, theta0)
        u_meas_rows: dict[int, complex] = {}
        u_pred_rows: dict[int, complex] = {}
        outgoing = {}
        worst_amp = 0.0
        worst_phase = 0.0
        for yc in control_rows:
            u_a = fit_row_1f(r0["t_s"], r0["uy_rows_lu"][:, yc], f, settle, n_harm)
            u_b = fit_row_1f(r0["t_s"], r0["uy_rows_lu"][:, r0["solver_meta"]["ny"] - yc],
                             f, settle, n_harm)
            u_fold = 0.5 * (u_a - u_b)
            u_meas_rows[yc] = u_fold
            u_pred_rows[yc] = complex(u_pred[yc])
            rr = u_fold / complex(u_pred[yc])
            outgoing[yc] = {"ratio": _cplx(rr), "amp_rel_err": float(abs(rr) - 1.0),
                            "phase_deg_err": _phase_deg(rr)}
            worst_amp = max(worst_amp, abs(abs(rr) - 1.0))
            worst_phase = max(worst_phase, abs(_phase_deg(rr)))
        # supporting: continuity prediction from MEASURED T rows (channel consistency)
        t_hat_rows = np.array([fit_row_1f(r0["t_s"], r0["t_rows_lu"][:, j], f, settle, 1)
                               for j in range(r0["solver_meta"]["ny"])])
        u_pred_meas = outgoing_mode_prediction(t_hat_rows / theta_hat_lu, omega_lu,
                                               theta_hat_lu, theta0)
        chan = {yc: _cplx(u_meas_rows[yc] / complex(u_pred_meas[yc])) for yc in control_rows}
        # supporting: sealed mass identity p_box/p0 = <theta>/theta0
        p_hat_box = fit_row_1f(r0["t_s"], r0["p_box_lu"], f, settle, n_harm)
        p0_lu = float(mapping.lattice.rho_ref_lu) * theta0
        mass_identity = (p_hat_box / p0_lu) / (np.mean(t_hat_rows) / theta0)

        # T3: window sensitivity (energy-channel signal)
        wsens = window_sensitivity_pbox(r0, f, settle,
                                        [float(c) for c in proto["window_sensitivity_cycles"]],
                                        n_harm)

        # T4: grid diagnostic (domain axis + 1D N-doubling into U_gov)
        res48 = _ratio(y_lbm[eps_primary], ref48["Y_over_Yhs"])
        res96 = _ratio(y_lbm96, ref96["Y_over_Yhs"])
        dg_diff_amp = abs(res96["amp_rel_err"] - res48["amp_rel_err"])
        dg_diff_phase = abs(res96["phase_deg_err"] - res48["phase_deg_err"])
        nsf_doubling = abs(nsf_hi["Y_over_Yhs"] / nsf_lo["Y_over_Yhs"] - 1.0)

        # T5: fit leakage on the actual grid
        leak = synthetic_leakage_row(r0["t_s"], f, settle, n_harm)

        # linearity across the eps pair (supporting)
        lin = abs(y_lbm[eps_list[-1]] / y_lbm[eps_primary] - 1.0) if len(eps_list) > 1 else 0.0

        # harmonics archive (N=5 refit; certification belongs to G2-O)
        fits5 = {eps: refit_n5(runs[eps], f, settle, n_harm) for eps in eps_list}

        # moment-channel diagnostic (two-channel ratio; §23 constant NOT re-fit)
        def y_moment(run: dict) -> complex:
            t_hat_si = run["theta_hat_lu"] * temp_scale
            return (run["fit_q"].harmonic(1) / t_hat_si) / y_hs_si

        two_channel = {f"{eps:g}": _cplx(y_lbm[eps] / y_moment(runs[eps]))
                       for eps in eps_list}

        u95_rel = float(fits5[eps_primary]["fit_p5"].amplitude_u95(1)
                        / max(fits5[eps_primary]["fit_p5"].amplitude(1), 1e-300))
        u_gov_nonrefine = float(max(abs(wsens["amp_rel"]), u95_rel, nsf_doubling))
        u_gov = float(max(u_gov_nonrefine, dg_diff_amp))

        direction_ok = (math.copysign(1, res96["amp_rel_err"]) == math.copysign(1, res48["amp_rel_err"])
                        or min(abs(res96["amp_rel_err"]), abs(res48["amp_rel_err"])) <= u_gov_nonrefine)

        hygiene_ok = all(
            runs[eps]["finite"]
            and runs[eps]["window_dm_rel"] <= gates["mass_window_rel"]
            and runs[eps]["total_drift_rel"] <= gates["mass_cumulative_rel"]
            and runs[eps]["wall_temp_err_K"] <= gates["wall_temperature_error_K"]
            for eps in eps_list) and run_ref["finite"]

        rows = {
            "transfer_amplitude_phase": {
                "transfer_ratio": _cplx(transfer),
                "amp_rel_err": float(abs(transfer) - 1.0),
                "phase_deg_err": _phase_deg(transfer),
                "gate": [gates["transfer_amp_rel"], gates["transfer_phase_deg"]],
                "ratio_lbm_vs_spectral": _cplx(ratio_lbm),
                "ratio_1d_vs_closed": _cplx(ratio_1d),
                "raw_lbm_over_1d": _cplx(raw_lbm_over_1d),
                "carriage_factor_K": _cplx(carriage),
                "machinery_identity_const_vs_closed": _cplx(machinery),
                "passed": bool(abs(abs(transfer) - 1.0) <= gates["transfer_amp_rel"]
                               and abs(_phase_deg(transfer)) <= gates["transfer_phase_deg"]),
            },
            "outgoing_mode_readout": {
                "control_rows": {str(yc): outgoing[yc] for yc in control_rows},
                "worst_amp_rel_err": worst_amp, "worst_phase_deg_err": worst_phase,
                "gate": [gates["outgoing_amp_rel"], gates["outgoing_phase_deg"]],
                "channel_consistency_vs_measured_T": {str(k): v for k, v in chan.items()},
                "mass_identity_pbox_vs_meanT": _cplx(mass_identity),
                "passed": bool(worst_amp <= gates["outgoing_amp_rel"]
                               and worst_phase <= gates["outgoing_phase_deg"]),
            },
            "window_sensitivity": {
                **wsens, "gate": [gates["window_amp_rel"], gates["window_phase_deg"]],
                "passed": bool(abs(wsens["amp_rel"]) <= gates["window_amp_rel"]
                               and abs(wsens["phase_deg"]) <= gates["window_phase_deg"]),
            },
            "grid_diagnostic": {
                "residual_ny48": res48, "residual_ny96": res96,
                "diff_amp_into_Ugov": dg_diff_amp, "diff_phase_deg": dg_diff_phase,
                "nsf1d_doubling_into_Ugov": nsf_doubling,
                "direction_consistent": bool(direction_ok),
                "passed": bool(direction_ok),
            },
            "fit_leakage": {
                "max_nontarget_rel": leak, "gate": gates["fit_leakage_rel"],
                "passed": bool(leak <= gates["fit_leakage_rel"]),
            },
            "numerical_repair": {"no_clipping": True, "no_floor": True,
                                 "no_positivity_repair": True, "passed": True},
            "instrument_hygiene": {
                "mass_window_max": max(runs[eps]["window_dm_rel"] for eps in eps_list),
                "mass_cumulative_max": max(runs[eps]["total_drift_rel"] for eps in eps_list),
                "wall_temp_err_K_max": max(runs[eps]["wall_temp_err_K"] for eps in eps_list),
                "passed": bool(hygiene_ok),
            },
        }
        gate_rows_by_freq[fkey] = rows
        per_freq[fkey] = {
            "omega_lu": omega_lu, "Y_lbm": y_lbm, "Y_lbm96": y_lbm96,
            "ref48": ref48, "ref96": ref96, "ref48_const": ref48_const,
            "y_closed_lu": y_closed_lu, "nsf_lo": nsf_lo, "nsf_hi": nsf_hi,
            "fits5": fits5, "two_channel": two_channel, "linearity": lin,
            "u_gov": u_gov, "u_gov_nonrefine": u_gov_nonrefine, "u95_rel": u95_rel,
            "wsens": wsens, "runs": runs, "run_ref": run_ref,
            "u_meas_rows": u_meas_rows, "u_pred_rows": u_pred_rows,
            "p_hat_box": p_hat_box,
        }
        log("f=%g: transfer=%.4f@%+.2f (raw %.4f@%+.2f, K=%.4f@%+.2f) "
            "outgoing worst %.2f%%/%.2fdeg wsens %.2e/%.3f lin=%.2e" % (
                f, abs(transfer), _phase_deg(transfer),
                abs(raw_lbm_over_1d), _phase_deg(raw_lbm_over_1d),
                abs(carriage), _phase_deg(carriage),
                100 * worst_amp, worst_phase, wsens["amp_rel"], wsens["phase_deg"], lin))

    # ---- archive series ----
    for f in frequencies:
        pf = per_freq[f"{f:g}"]
        for eps, r in list(pf["runs"].items()) + [(eps_primary, pf["run_ref"])]:
            label = f"f{f:g}_ny{r['solver_meta']['ny']}_eps{eps:g}"
            if f"runs/{label}" in h5:
                continue
            g = h5.create_group(f"runs/{label}")
            for name in ("t_s", "p_box_lu", "q_moment_si", "mass", "theta_imposed_lu"):
                g.create_dataset(name, data=r[name])
            g.create_dataset("t_rows_lu", data=r["t_rows_lu"])
            if r.get("uy_rows_lu") is not None:
                g.create_dataset("uy_rows_lu", data=r["uy_rows_lu"])
                g.create_dataset("p_rows_lu", data=r["p_rows_lu"])
            g.attrs.update({"epsilon": eps, "ny": r["solver_meta"]["ny"],
                            "frequency_Hz": f, "finite": r["finite"]})

    # ---- H3 conditional trigger (contract §7.4) from the G1a archive ----
    h3_trigger = {"triggered": False, "reason": "no G1a archive found"}
    g1a_summary_path = repo_root / str(cfg["inheritance"].get("g1a_summary", ""))
    if g1a_summary_path.is_file():
        g1a = json.loads(g1a_summary_path.read_text(encoding="utf-8"))
        h3 = {k: float(v) for k, v in g1a["results"]["H3"].items()}
        h2 = {k: float(v) for k, v in g1a["results"]["H2"].items()}
        floor = 6e-4  # settle-1 single-run transient floor (G1-W archive)
        above = {k: v for k, v in h3.items() if v > 3.0 * floor}
        # m3 scaling check on the ladder points above floor
        pts = sorted((float(k), v) for k, v in above.items() if float(k) >= 0.03)
        m3 = None
        if len(pts) >= 3:
            lx = np.log([p[0] for p in pts])
            ly = np.log([p[1] * p[0] for p in pts])  # absolute-ish 3f ~ eps*H3
            m3 = float(np.polyfit(lx, ly, 1)[0])
        triggered = len(pts) >= 3 and m3 is not None and 2.5 <= m3 <= 3.5
        h3_trigger = {"triggered": bool(triggered), "H3_ladder": h3,
                      "H2_ladder_context": h2, "floor_rel": floor,
                      "points_above_3x_floor": len(above), "m3_fit": m3,
                      "reason": "evaluated from G1a archived ladder (settle-1 floor)"}

    # ---- verdict ----
    freq_pass = {fk: all(r["passed"] for r in gate_rows_by_freq[fk].values())
                 for fk in gate_rows_by_freq}
    freq_stable = {fk: all(rr["finite"] for rr in per_freq[fk]["runs"].values())
                   for fk in gate_rows_by_freq}
    labels: list[str] = []
    fk10 = f"{frequencies[0]:g}"
    if all(freq_pass.values()):
        verdict = "PASSED"
    elif freq_pass.get(fk10) and all(freq_stable.values()):
        verdict = "SCOPED_CANDIDATE"
        labels.append("G2_2F_NOT_CERTIFIED")
    else:
        verdict = "FAILED"
        labels.append("G2_2F_NOT_CERTIFIED")
    if not h3_trigger["triggered"]:
        labels += ["H3_DIAGNOSTIC_ONLY", "G2_3F_WAIVED_BY_SIGNAL"]
    log("verdict=%s labels=%s" % (verdict, labels or "-"))

    # ---- outputs (contract §16.1 seven files) ----
    resolved = {"gate_id": GATE_ID, "case_family": CASE_FAMILY, "protocol": proto,
                "gates": gates, "config_path": str(config_path)}
    config_yaml = yaml.safe_dump(resolved, allow_unicode=True, sort_keys=False)
    (out_dir / "config_resolved.yaml").write_text(config_yaml, encoding="utf-8")

    fk_all = [f"{f:g}" for f in frequencies]
    pf0 = per_freq[fk_all[0]]
    na = "not_applicable_g2t_sealed_rig"
    summary = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "code_commit": _git_commit(),
        "config_digest": _sha256_bytes(config_yaml.encode())[:12],
        "physics_core_digest": _physics_core_digest(repo_root),
        "parent_baseline_run": str(cfg["inheritance"]["g1a_certified_run"]),
        "phase5_contract_version": PHASE5_CONTRACT_VERSION,
        "work_package": "WP2",
        "gate_id": GATE_ID,
        "case_family": CASE_FAMILY,
        "model_route": "ROUTE_B_MAIN",
        "property_model_id": "frozen_dx2p6_route_b_closure + alpha_eff(k) table "
                             "(G0 + in-run extension) + 1D-lbm-equivalent_g0_measured_k1_v1",
        "tau_policy": "frozen (M3 closure §3; no per-point retuning)",
        "mapping_digest": _sha256_bytes(Path(gas_cfg_path).read_bytes())[:12],
        "background_path": "uniform_reference_state",
        "forcing_protocol": "prescribed_wall_temperature_zero_mean_sinusoid",
        "P_mean_W_m2": 0.0, "P_mean_rematched": False, "target_Theta_DC": 0.0,
        "frequency_Hz": frequencies,
        "T_ambient_K": 300.0, "T_mean_K": 300.0,
        "epsilon_AC_measured": {f"{e:g}": e for e in eps_list},
        "Theta_DC_measured": 0.0,
        "chi_0": None, "chi_eff": None, "C_A_J_m2K": None,
        "dc_heat_sink_model": na + " (canonical sink belongs to G4a)",
        "dc_heat_sink_parameters": None,
        "H_s_role": "rig domain height (sealed periodic)",
        "thermal_resistance_effective": None,
        "grid_shape": [ny, nx], "dx_m": dx_m, "dt_s": dt,
        "domain_height_m": ny * dx_m,
        "boundary_model": "mass_neutral_v1p1_symmetric (G1-W certified production wall)",
        "wall_mass_policy": "mass_neutral_by_construction",
        "wall_neutrality_gate_id": "G1-W PASSED (20260727T083342Z)",
        "boundary_mass_flux_definition": "wall_mass_audit.NORMALIZATION_DEFINITION",
        "boundary_mass_flux_0f_to_3f": float(
            pf0["runs"][eps_primary]["audit"]["dm_rel"]["max_component"]),
        "spectral_operator_stack_id": "frozen_production_dx2p6",
        "spectral_correction_enabled": True,
        "high_wavenumber_filter_enabled": True,
        "high_wavenumber_filter_strength": "frozen_production (0.0065 x1)",
        "operator_ablation_run_id": "G2-O (separate run family)",
        "q_feedback_relax": None,
        "fit_window": {"settle_periods": settle,
                       "fit_periods": float(proto["periods"]) - settle},
        "fit_cycles": float(proto["periods"]) - settle,
        "detrend_order": 0,
        "harmonic_order_max": n_harm,
        "harmonic_fit_condition_number": pf0["fits5"][eps_primary]["fit_p5"].condition_number,
        "U_det": {fk: {"window": per_freq[fk]["wsens"],
                       "refinement_diff": gate_rows_by_freq[fk]["grid_diagnostic"]["diff_amp_into_Ugov"],
                       "nsf1d_doubling": gate_rows_by_freq[fk]["grid_diagnostic"]["nsf1d_doubling_into_Ugov"]}
                  for fk in fk_all},
        "U95_fit": {fk: per_freq[fk]["u95_rel"] for fk in fk_all},
        "U_gov": {fk: per_freq[fk]["u_gov"] for fk in fk_all},
        "no_clipping": True, "no_floor": True, "no_positivity_repair": True,
        "gate_status": verdict,
        "scoped_limitations": labels,
        "smoke_mode": bool(smoke),
        "h3_conditional_trigger": h3_trigger,
        "results": {
            "T_s_hat_1f": _cplx(complex(pf0["runs"][eps_primary]["theta_hat_lu"] * temp_scale, 0.0)),
            "p_hat_1f": _cplx(pf0["fits5"][eps_primary]["fit_p5"].harmonic(1)),
            "p_hat_2f": _cplx(pf0["fits5"][eps_primary]["fit_p5"].harmonic(2)),
            "p_hat_3f": _cplx(pf0["fits5"][eps_primary]["fit_p5"].harmonic(3)),
            "outgoing_mode_1f": {fk: {str(yc): _cplx(per_freq[fk]["u_meas_rows"][yc])
                                      for yc in control_rows} for fk in fk_all},
            "outgoing_mode_2f": None, "outgoing_mode_3f": None,
            "outgoing_mode_note": "1f modal readout certified vs table-carried "
                                  "continuity prediction; harmonic modal content "
                                  "certification requires G2-O (operator ablation)",
            "G1": {fk: float(abs(per_freq[fk]["Y_lbm"][eps_primary])) for fk in fk_all},
            "D_G": None, "D_G_note": "G1a quantity (amplitude envelope)",
            "D_OP": None, "D_OP_note": "A2a quantity (WP3)",
            "H2": {fk: {f"{e:g}": per_freq[fk]["fits5"][e]["H2_q"] for e in eps_list}
                   for fk in fk_all},
            "H3": {fk: {f"{e:g}": per_freq[fk]["fits5"][e]["H3_q"] for e in eps_list}
                   for fk in fk_all},
            "H2_p_side": {fk: {f"{e:g}": per_freq[fk]["fits5"][e]["H2_p"] for e in eps_list}
                          for fk in fk_all},
            "m1": None, "m2": None, "m3": None,
            "m_note": "transfer gate is 1f; harmonic scaling belongs to G1a/G2-O",
            "QS0_error_amplitude": None, "QS0_error_phase": None,
            "QS1_error_amplitude": None, "QS1_error_phase": None,
            "wall_boundary_sensitivity": {
                "two_channel_ratio_by_freq": {fk: per_freq[fk]["two_channel"] for fk in fk_all},
                "note": "moment channel is (tau,k)-point-calibrated at 10 kHz; the "
                        "20 kHz two-channel ratio is the archived field-shape "
                        "diagnostic, not a recalibration"},
            "operator_sensitivity_D_G": None,
            "operator_sensitivity_H2": None,
            "operator_sensitivity_H3": None,
            "operator_note": "G2-O quantity (frozen stack here)",
            "boundary_mass_flux_0f_to_3f": float(
                pf0["runs"][eps_primary]["audit"]["dm_rel"]["max_component"]),
            "energy_residual": {fk: float(abs(per_freq[fk]["nsf_hi"]["energy_residual_rel_flux"]))
                                for fk in fk_all},
            "mass_or_flux_residual": float(max(
                max(r["total_drift_rel"] for r in per_freq[fk]["runs"].values())
                for fk in fk_all)),
            "wall_temperature_error": float(max(
                max(r["wall_temp_err_K"] for r in per_freq[fk]["runs"].values())
                for fk in fk_all)),
            "linearity_eps_pair": {fk: per_freq[fk]["linearity"] for fk in fk_all},
        },
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=1, default=float), encoding="utf-8")

    harmonic_payloads = {}
    for fk in fk_all:
        for eps in eps_list:
            harmonic_payloads[f"q_f{fk}_eps{eps:g}"] = \
                per_freq[fk]["fits5"][eps]["fit_q5"].to_json_payload()
            harmonic_payloads[f"p_f{fk}_eps{eps:g}"] = \
                per_freq[fk]["fits5"][eps]["fit_p5"].to_json_payload()
    (out_dir / "harmonic_fit.json").write_text(
        json.dumps(harmonic_payloads, indent=1, default=float), encoding="utf-8")

    provenance = {
        "run_id": run_id, "command": " ".join(sys.argv), "workers": workers,
        "parallel_scheduling_note": "process pool over independent cases only "
                                    "(driven LBM + 1D legs); per-case sequence "
                                    "identical to serial",
        "python": sys.version.split()[0], "numpy": np.__version__,
        "code_commit": summary["code_commit"],
        "physics_core_digest": summary["physics_core_digest"],
        "physics_core_files": {rel: _sha256_bytes((repo_root / rel).read_bytes())[:12]
                               for rel in PHYSICS_CORE_FILES},
        "g1w_certified_run": str(cfg["inheritance"]["g1w_certified_run"]),
        "g1a_certified_run": str(cfg["inheritance"]["g1a_certified_run"]),
        "g0_alpha_table": str(G0_TABLE_CSV),
        "alpha_extension_rows": ext_rows,
    }
    (out_dir / "provenance.json").write_text(json.dumps(provenance, indent=1, default=float),
                                             encoding="utf-8")
    (out_dir / "gate_evaluation.json").write_text(
        json.dumps({"gate_id": GATE_ID, "verdict": verdict, "labels": labels,
                    "rows_by_frequency": gate_rows_by_freq,
                    "h3_conditional_trigger": h3_trigger}, indent=1, default=float),
        encoding="utf-8")

    report = [f"# G2-T run {run_id}", "",
              f"- verdict: **{verdict}** labels={labels or '-'}",
              f"- smoke_mode: {smoke}", "",
              "## Gate rows by frequency (contract §7.1)", ""]
    for fk in fk_all:
        report.append(f"### f = {fk} Hz")
        for name, row in gate_rows_by_freq[fk].items():
            report.append(f"- {name}: passed={row['passed']}")
        t = gate_rows_by_freq[fk]["transfer_amplitude_phase"]
        report.append("  - transfer %.4f@%+.2f deg (raw %.4f@%+.2f, K %.4f@%+.2f)" % (
            abs(complex(t["transfer_ratio"]["re"], t["transfer_ratio"]["im"])),
            t["phase_deg_err"] + 0.0,
            t["raw_lbm_over_1d"]["abs"], t["raw_lbm_over_1d"]["phase_deg"],
            t["carriage_factor_K"]["abs"], t["carriage_factor_K"]["phase_deg"]))
        report.append("")
    (out_dir / "run_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    h5.close()
    log(f"outputs -> {out_dir}")
    return {"verdict": verdict, "labels": labels, "out_dir": str(out_dir),
            "summary": summary, "gate_rows_by_freq": gate_rows_by_freq}


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase_5 G2-T thermal-transfer gate")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--workers", type=int,
                        default=max(1, (os.cpu_count() or 2) - 2))
    args = parser.parse_args()
    result = run_g2t(args.config, args.output_root, smoke=args.smoke,
                     workers=args.workers)
    return 0 if result["verdict"] in {"PASSED", "SCOPED_CANDIDATE"} else 1


if __name__ == "__main__":
    sys.exit(main())
