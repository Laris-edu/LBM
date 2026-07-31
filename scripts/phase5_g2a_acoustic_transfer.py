"""Phase_5 G2-A pure acoustic propagation / readout chain gate (contract §7.2, WP2).

Certifies the outgoing-mode acoustic instrument chain — injection, propagation,
control surfaces and the (p, u_n) characteristic decomposition readout — at the
two mandatory frequencies 10 and 20 kHz, WITHOUT membrane thermal feedback.

Carrier (pre-registered): the Phase_4 D3 coarse acoustic domain
(``configs/phase4_acoustic_coarse_dx334.yaml``, simplified collision, local
biharmonic filter 0.03 x 6, top/bottom sponges) with the D3-3 one-way additive
soft source. This is the ONLY certified traveling-wave carrier in the project
(the frozen dx2p6 stack cannot host 10-30 kHz traveling waves: wavelength
~13k cells and the P4-1 volume-injection floor); Phase_5's outgoing-mode
claims ride the M4 compact-source handoff whose far leg lives here.

Scope guard (documented, not hidden): the coarse medium's c0 knob is the M4
(iv) calibration certified AT 10 kHz ONLY. G2-A does not recalibrate at
20 kHz: the 10 kHz leg gates the realized SI phase velocity against air c0
(inherited-consistency, P2-6 wording <=2%); the 20 kHz leg MEASURES and
archives the realized phase velocity as instrument characterization (its
consequence: near-field L2-2f claims are carried by G2-T on the fine stack;
any future far-field 2f SPL (L3) would need an M4-style per-frequency medium
calibration — already excluded from the base scope, contract §1.6).

FIXTURE v2 (2026-07-30, pre-registered BEFORE the v2 certification run).
The v1 authoritative run 20260730T095503Z is archived as the DIAGNOSTIC run
that exposed three v1 operationalization errors, all instrument-side (the
medium itself is frozen and untouched):
  (1) v1's span reference (classical nu x100 absorption + filter symbol) is
      the WRONG physics for the simplified-collision longitudinal mode: the
      canonical one-step modal eigenvalue measurement (P2-6 caliber) shows
      the medium is attenuation-NEUTRAL at the 10 kHz calibration point
      (sigma_spatial ~ -5e-6/cell) and carries a small spatial GAIN at the
      20 kHz band (~ -3e-4/cell, c +5-7%): the artificial-viscosity classical
      formula never applied.
  (2) v1's global phase fit aliased at 20 kHz: the control-row spacing
      (~51 cells) ~= lambda(20 kHz) (~52 cells), so unwrap folded the phase
      advance (garbage c_meas +1410%); the +/-4-cell stencil rows are
      alias-free (local k -> c = 366-368 m/s, consistent across clusters).
  (3) v1's characteristic split used the NOMINAL z0 = rho0*c_nom: in the
      dispersive 20 kHz band (c_eff +5.7%) that mixes directions by
      construction (~delta/2 ~ 2.8% spurious A-) and the aliased k made the
      A5 sinc correction ~1 (the 3.55% v1 channel error).

Rows per mandatory frequency (monochromatic soft-source drive at the exact SI
frequency, §12.1 multiharmonic readout at pre-registered control rows):
  A0 medium symbol rows (v2, in-run instrument): clean fully-periodic domain
     (no source/sponges), seeded traveling acoustic modes at integer
     wavenumbers bracketing the working band; per mode the one-step modal
     complex amplitude gives (f_m, c_m, sigma_m). (c, sigma_spatial) at each
     drive frequency by interpolation IN MEASURED MODAL FREQUENCY (no
     circularity through k). Archived with the classical+filter model delta
     (the medium-characterization discovered by the v1 diagnostic).
  A1 amplitude error <=5%: measured |A+| span transfer across the control-row
     span vs exp(-sigma_spatial(f)*span) from the A0 symbol rows. This
     certifies the injection+sponge+propagation+readout CHAIN against the
     medium's own certified symbol (the medium never pretended to have air
     absorption: nu x100 artificial).
  A2 phase error <=5 deg: TWO-STAGE alias-free fit — stage 1: local k from
     each control cluster's +/-4-cell phase difference (spacing 4 cells <<
     lambda/2 at both frequencies); stage 2: carrier-detrend ALL sample rows
     by the median local k, unwrap the (small) residual phases, LS-refit ->
     k_fit; gate = max residual of the stage-2 line; realized phase velocity
     c_meas = omega*dx/(k_fit*dt) archived; 10 kHz additionally gates
     |c_meas/347 - 1| <= 2% (inherited M4 calibration consistency; 20 kHz
     characterization-only per the scope guard).
  A3 reflection/contamination |A-|/|A+| < 0.05 steady-state at every control
     row, with the v2 decomposition basis z_eff = rho0*omega_lu/k_fit (the
     realized carrier's characteristic impedance — fully determined by the
     measured k_fit, no free parameter; the nominal-z0 split is archived as
     a diagnostic column). TWO non-degeneracy/inheritance controls: rigid-TOP
     steady control reads O(1) (the reflectometer sees reflection when it
     exists) and the D3-3 downward-pulse rows at the injection boundary
     (sponge |R|<0.05, rigid bottom control >0.3).
  A4 control-surface position sensitivity <=5%: scatter of |A+| across the
     four control rows after normalizing by the A0 symbol decay/gain.
  A5 channel consistency <=10%/10 deg: velocity channel u_hat vs the
     pressure-gradient channel -(dp/dy)/(i omega rho0) (central difference
     over +/-4 cells with the exact sinc factor sin(k_fit d)/(k_fit d)).
Supporting archives: compact-source map numbers u_src(f) via
``farfield.compact_source`` for the M3 canonical T_s_hat, at nominal alpha and
— for the 20 kHz (=2f) leg — at the G0 table alpha_eff(k2) (the table-carriage
the 2f source mapping must use; freeze doc §3.3 output 3).

Verdict (script-emittable): PASSED = all rows at both frequencies; 10 kHz
full pass + 20 kHz stable-but-out-of-gate -> SCOPED_CANDIDATE
(G2_2F_NOT_CERTIFIED); else FAILED.

Outputs the contract §16.1 seven-file set under
results/phase5/g2_acoustic_transfer/<run_id>/.
"""

from __future__ import annotations

import argparse
import cmath
import copy
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import yaml

from boundary.open_sponge import make_top_sponge_callback
from core.equilibrium import equilibrium_fg
from core.macroscopic import recover_macro
from core.solver import GasSolver2D
from farfield.compact_source import thermal_pumping_velocity_m_s
from postproc.multiharmonic_fit import fit_multiharmonic
from scripts.phase2_m2_verification import load_config
from scripts.phase4_d3_oneway_probe import (
    _bottom_sponge,
    _frame,
    run_bottom_reflection,
)
from scripts.phase5_g1w_wall_neutrality import (
    G0_TABLE_CSV,
    _cplx,
    _git_commit,
    load_g0_alpha_rows,
)

GATE_ID = "G2-A"
CASE_FAMILY = "g2_acoustic_transfer"
PHASE5_CONTRACT_VERSION = "v1.2"
DEFAULT_CONFIG = Path("configs/phase5/g2_acoustic_transfer/g2a_10k20k_coarse.yaml")
AIR_C0_M_S = 347.0  # true air constant (never the medium knob; see acoustic config)
PHYSICS_CORE_FILES = [
    "core/solver.py",
    "boundary/open_sponge.py",
    "farfield/compact_source.py",
    "postproc/multiharmonic_fit.py",
    "scripts/phase4_d3_oneway_probe.py",
]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _phase_deg(z: complex) -> float:
    return math.degrees(math.atan2(z.imag, z.real))


def filter_step_multiplier(k_lu: float, strength: float, passes: int) -> float:
    """Exact per-step biharmonic-filter amplitude multiplier at wavenumber k."""

    per_pass = 1.0 - 16.0 * strength * math.sin(0.5 * k_lu) ** 4
    return per_pass ** passes


def span_decay_prediction(k_lu: float, omega_lu: float, c_lu: float,
                          nu_lu: float, alpha_lu: float, gamma: float,
                          strength: float, passes: int, span_cells: float) -> dict[str, float]:
    """|A+| decay over the control-row span: classical absorption + filter symbol."""

    a_classical = omega_lu**2 / (2.0 * c_lu**3) * (4.0 / 3.0 * nu_lu
                                                   + (gamma - 1.0) * alpha_lu)
    filt = filter_step_multiplier(k_lu, strength, passes)
    a_filter = -math.log(max(filt, 1e-12)) / c_lu  # per cell of travel
    total = (a_classical + a_filter) * span_cells
    return {"per_cell_classical": a_classical, "per_cell_filter": a_filter,
            "span_ratio": math.exp(-total)}


def measure_modal_symbol(base: dict, *, ny: int, nx: int, modes: list[int],
                         n_steps: int, fit_skip_frac: float, eps_seed: float,
                         log) -> list[dict[str, float]]:
    """Medium symbol rows: (f, c, sigma) per seeded traveling acoustic mode.

    Clean fully-periodic domain (no callbacks). Seed a +y adiabatic traveling
    wave at k = 2 pi m / ny; project the x-averaged pressure onto e^{iky}
    each step; the complex modal amplitude a(t) gives omega = d arg(a)/dt and
    sigma = -d ln|a|/dt (the canonical one-step eigenvalue caliber, P2-6).
    """

    import copy as _copy
    rows: list[dict[str, float]] = []
    for m in modes:
        cfg = {**_copy.deepcopy(base), "numerics": {**base["numerics"], "nx": nx, "ny": ny}}
        s = GasSolver2D(cfg)
        th0 = float(s.mapping.theta_ref_lu)
        rho0 = float(s.mapping.lattice.rho_ref_lu)
        gamma = float(cfg["physical"]["gamma"])
        c_ad = math.sqrt(gamma * th0)
        dt = float(s.mapping.lattice.dt_s)
        dx = float(s.mapping.lattice.dx_m)
        k = 2.0 * math.pi * m / ny
        y = np.arange(ny)
        rho = rho0 * (1.0 + eps_seed * np.cos(k * y))[:, None] * np.ones((1, nx))
        th = th0 * (1.0 + (gamma - 1.0) * eps_seed * np.cos(k * y))[:, None] * np.ones((1, nx))
        u = np.zeros((ny, nx, 2))
        u[..., 1] = c_ad * eps_seed * np.cos(k * y)[:, None]
        s.initialize_from_macro(rho, u, th)
        amps = np.empty(n_steps, dtype=complex)
        for i in range(n_steps):
            s.step(1)
            mac = recover_macro(s.f, s.g, D=2, S=3, lattice=s.lattice)
            amps[i] = np.mean(np.mean(mac.p, axis=1) * np.exp(-1j * k * y)) * 2.0
        i0 = int(round(fit_skip_frac * n_steps))
        tt = np.arange(i0, n_steps, dtype=float)
        sigma = -float(np.polyfit(tt, np.log(np.abs(amps[i0:])), 1)[0])
        omega_meas = abs(float(np.polyfit(tt, np.unwrap(np.angle(amps[i0:])), 1)[0]))
        c_lu = omega_meas / k
        row = {"m": int(m), "k_lu": float(k),
               "f_hz": float(omega_meas / (2.0 * math.pi) / dt),
               "c_m_s": float(c_lu * dx / dt),
               "sigma_per_step": sigma,
               "sigma_per_cell": float(sigma / c_lu)}
        rows.append(row)
        log("  symbol m=%d k=%.4f: f=%.2f kHz c=%.2f m/s sigma=%.3e/cell %s" % (
            m, k, row["f_hz"] / 1e3, row["c_m_s"], row["sigma_per_cell"],
            "GAIN" if sigma < 0 else "decay"))
    return rows


def symbol_at(rows: list[dict[str, float]], f_hz: float) -> dict[str, float]:
    """(c, sigma_per_cell) at a drive frequency by interpolation in measured f."""

    fs = np.array([r["f_hz"] for r in rows])
    order = np.argsort(fs)
    fs = fs[order]
    if not (fs[0] <= f_hz <= fs[-1]):
        raise ValueError(f"symbol rows do not bracket {f_hz} Hz (span {fs[0]}..{fs[-1]})")
    cs = np.array([r["c_m_s"] for r in rows])[order]
    sg = np.array([r["sigma_per_cell"] for r in rows])[order]
    return {"c_m_s": float(np.interp(f_hz, fs, cs)),
            "sigma_per_cell": float(np.interp(f_hz, fs, sg))}


def two_stage_phase_fit(p_hat: dict[int, complex], control_rows: list[int],
                        sample_rows: list[int], d_st: int) -> dict[str, Any]:
    """Alias-free k fit: cluster-local k median -> carrier-detrended global LS.

    Stage 1 uses the +/-d_st stencil pairs (spacing 2*d_st << lambda/2 for any
    plausible c), immune to the control-row-spacing aliasing that broke the v1
    global fit. Stage 2 detrends ALL sample rows by the median local k so the
    residual phases are small and unwrap is trivial; the refit slope corrects
    k and the max residual is the linearity gate quantity.
    """

    k_loc = {}
    for r in control_rows:
        ratio = p_hat[r + d_st] / p_hat[r - d_st]
        k_loc[r] = -math.atan2(ratio.imag, ratio.real) / (2.0 * d_st)
    k_est = float(np.median(list(k_loc.values())))
    ys = np.array(sorted(sample_rows), dtype=float)
    psi = np.unwrap([math.atan2((p_hat[int(r)] * cmath.exp(1j * k_est * r)).imag,
                                (p_hat[int(r)] * cmath.exp(1j * k_est * r)).real)
                     for r in ys])
    slope, icpt = np.polyfit(ys, psi, 1)
    k_fit = k_est - float(slope)
    resid_deg = float(np.max(np.abs(np.degrees(psi - (slope * ys + icpt)))))
    return {"k_fit": k_fit, "k_local_by_row": k_loc, "k_est_stage1": k_est,
            "max_residual_deg": resid_deg}


def _make_top_rigid_lid(solver):
    cy = solver.lattice.c[:, 1]
    opp = solver.lattice.opposite
    down = np.where(cy < 0)[0]

    def cb(*, solver, f_post, g_post, f_stream, g_stream):
        for a in down:  # top wall: incoming-from-above <- reflect the up-going pops
            f_stream[-1, :, a] = f_post[-1, :, opp[a]]
            g_stream[-1, :, a] = g_post[-1, :, opp[a]]
        return f_stream, g_stream

    return cb


def run_injection_readout(base: dict, *, frequency_hz: float, ny: int, nx: int,
                          n_abs: int, y_s: int, eps: float, scale: float,
                          periods: float, fit_periods: float,
                          sample_rows: list[int], top: str, log) -> dict[str, Any]:
    """Monochromatic one-way soft-source drive with row-resolved (p, v) readout."""

    s = GasSolver2D({**copy.deepcopy(base),
                     "numerics": {**base["numerics"], "nx": nx, "ny": ny}})
    fr = _frame(s)
    S = int(s.mapping.lattice.S)
    dt = float(s.mapping.lattice.dt_s)
    omega_lu = 2.0 * math.pi * frequency_hz * dt
    s.initialize_from_macro(fr["rho0"], np.zeros((ny, s.nx, 2)), fr["th0"])
    top_cb = make_top_sponge_callback(n_sponge=n_abs) if top == "sponge" else _make_top_rigid_lid(s)
    f0, g0 = equilibrium_fg(np.full((1, s.nx), fr["rho0"]), np.zeros((1, s.nx, 2)),
                            np.full((1, s.nx), fr["th0"]), S, s.lattice)

    def cb(*, solver, f_post, g_post, f_stream, g_stream):
        f_stream, g_stream = top_cb(solver=solver, f_post=f_post, g_post=g_post,
                                    f_stream=f_stream, g_stream=g_stream)
        f_stream, g_stream = _bottom_sponge(solver, f_stream, g_stream, n_abs)
        dp = eps * fr["pref"] * math.sin(omega_lu * (solver.t_lu + 1))
        drho = dp / fr["c"] ** 2
        duy = dp / fr["z0"]
        u_src = np.zeros((1, solver.nx, 2))
        u_src[..., 1] = duy
        fsrc, gsrc = equilibrium_fg(np.full((1, solver.nx), fr["rho0"] + drho), u_src,
                                    np.full((1, solver.nx), fr["th0"]), S, solver.lattice)
        f_stream[y_s:y_s + 1] += scale * (fsrc - f0)
        g_stream[y_s:y_s + 1] += scale * (gsrc - g0)
        return f_stream, g_stream

    n_steps = int(round(periods / frequency_hz / dt))
    rows = sorted(set(sample_rows))
    t_arr = np.empty(n_steps)
    p_arr = np.empty((n_steps, len(rows)))
    v_arr = np.empty((n_steps, len(rows)))
    for i in range(n_steps):
        s.step(1, boundary_callback=cb)
        if not (i % 500) and not np.isfinite(s.f).all():
            return {"finite": False}
        m = recover_macro(s.f[rows], s.g[rows], D=2, S=3, lattice=s.lattice)
        t_arr[i] = (i + 1) * dt
        p_arr[i] = np.mean(m.p, axis=1) - fr["pref"]
        v_arr[i] = np.mean(m.u[..., 1], axis=1)
    finite = bool(np.isfinite(s.f).all() and np.isfinite(p_arr).all())

    mask = t_arr >= (periods - fit_periods) / frequency_hz * (1.0 - 1e-12)
    omega = 2.0 * math.pi * frequency_hz
    p_hat: dict[int, complex] = {}
    v_hat: dict[int, complex] = {}
    for j, r in enumerate(rows):
        p_hat[r] = fit_multiharmonic(t_arr[mask], p_arr[mask, j], omega,
                                     n_harmonics=3).harmonic(1)
        v_hat[r] = fit_multiharmonic(t_arr[mask], v_arr[mask, j], omega,
                                     n_harmonics=3).harmonic(1)
    log("  %s top=%s: %d steps finite=%s |p|@rows %s" % (
        f"{frequency_hz:g}Hz", top, n_steps, finite,
        ["%.2e" % abs(p_hat[r]) for r in rows]))
    return {"finite": finite, "rows": rows, "p_hat": p_hat, "v_hat": v_hat,
            "frame": fr, "dt_s": dt, "omega_lu": omega_lu,
            "t_s": t_arr, "p_rows": p_arr, "v_rows": v_arr}


def run_g2a(config_path: Path, output_root: Path | None = None,
            smoke: bool = False) -> dict[str, Any]:
    cfg = load_config(config_path)
    proto = cfg["g2a_smoke"] if smoke else cfg["g2a"]
    gates = cfg["gates"]
    acoustic_cfg_path = Path(cfg["inheritance"]["acoustic_config_path"])
    repo_root = Path(__file__).resolve().parents[1]
    base = load_config(acoustic_cfg_path)

    def log(msg: str) -> None:
        print(f"G2A {msg}", flush=True)

    ny = int(proto["ny"])
    nx = int(proto["nx"])
    n_abs = int(proto["n_abs"])
    y_s = int(proto["y_s"])
    eps = float(proto["epsilon"])
    scale = float(proto["scale"])
    d_st = int(proto["grad_stencil_cells"])
    control_rows = [int(round(fr * ny)) for fr in proto["control_rows_frac"]]
    sample_rows = sorted(set(control_rows
                             + [r - d_st for r in control_rows]
                             + [r + d_st for r in control_rows]))
    freq_protos = proto["frequencies"]

    filt = base["numerics"]["high_wavenumber_filter"]
    gamma = float(base["physical"]["gamma"])
    dx_m = float(base["lattice"]["dx_m"])
    dt_s = float(base["lattice"]["dt_s"])
    nu_lu = float(base["physical"]["nu0_m2_s"]) * dt_s / dx_m**2
    alpha_lu = float(base["physical"]["alpha0_m2_s"]) * dt_s / dx_m**2

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = Path(output_root) if output_root else repo_root / "results" / "phase5" / CASE_FAMILY
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    h5 = h5py.File(out_dir / "signals.h5", "w")

    # ---- A0: medium symbol rows (v2 in-run instrument; clean periodic domain)
    sym_proto = proto["symbol"]
    log("A0 medium symbol rows (canonical modal eigenvalue, periodic clean domain):")
    symbol_rows = measure_modal_symbol(
        base, ny=ny, nx=nx, modes=[int(m) for m in sym_proto["modes"]],
        n_steps=int(sym_proto["n_steps"]),
        fit_skip_frac=float(sym_proto["fit_skip_frac"]),
        eps_seed=float(sym_proto["eps_seed"]), log=log)

    # ---- injection + rigid-top control per frequency ----
    per_freq: dict[str, dict[str, Any]] = {}
    gate_rows_by_freq: dict[str, dict[str, Any]] = {}
    for fp in freq_protos:
        f = float(fp["frequency_Hz"])
        fkey = f"{f:g}"
        inj = run_injection_readout(
            base, frequency_hz=f, ny=ny, nx=nx, n_abs=n_abs, y_s=y_s, eps=eps,
            scale=scale, periods=float(fp["periods"]),
            fit_periods=float(fp["fit_periods"]), sample_rows=sample_rows,
            top="sponge", log=log)
        rigid = run_injection_readout(
            base, frequency_hz=f, ny=ny, nx=nx, n_abs=n_abs, y_s=y_s, eps=eps,
            scale=scale, periods=float(fp["periods"]),
            fit_periods=float(fp["fit_periods"]), sample_rows=sample_rows,
            top="rigid", log=log)
        if not inj["finite"]:
            raise RuntimeError(f"injection run at {f:g} Hz went non-finite")
        fr = inj["frame"]
        omega_lu = inj["omega_lu"]

        # A2 (v2): two-stage alias-free phase fit -> k_fit, residual, c_meas
        fit2 = two_stage_phase_fit(inj["p_hat"], control_rows, sample_rows, d_st)
        k_fit = fit2["k_fit"]
        resid_deg = fit2["max_residual_deg"]
        c_meas_si = omega_lu / max(abs(k_fit), 1e-300) * (dx_m / dt_s)
        c_dev = c_meas_si / AIR_C0_M_S - 1.0

        # A3 (v2): characteristic split with the realized carrier impedance
        z_eff = fr["rho0"] * omega_lu / max(abs(k_fit), 1e-300)
        z0 = fr["z0"]  # nominal split kept as diagnostic column
        a_plus = {r: 0.5 * (inj["p_hat"][r] + z_eff * inj["v_hat"][r]) for r in control_rows}
        a_minus = {r: 0.5 * (inj["p_hat"][r] - z_eff * inj["v_hat"][r]) for r in control_rows}
        incoming = {r: abs(a_minus[r]) / max(abs(a_plus[r]), 1e-300) for r in control_rows}
        incoming_nominal_z0 = {
            r: abs(0.5 * (inj["p_hat"][r] - z0 * inj["v_hat"][r]))
            / max(abs(0.5 * (inj["p_hat"][r] + z0 * inj["v_hat"][r])), 1e-300)
            for r in control_rows}
        rigid_incoming = {}
        if rigid["finite"]:
            rigid_incoming = {r: abs(0.5 * (rigid["p_hat"][r] - z_eff * rigid["v_hat"][r]))
                              / max(abs(0.5 * (rigid["p_hat"][r] + z_eff * rigid["v_hat"][r])), 1e-300)
                              for r in control_rows}

        # A1/A4 (v2): span vs the A0 symbol prediction + symbol-normalized scatter
        rows_sorted = sorted(control_rows)
        span = float(rows_sorted[-1] - rows_sorted[0])
        sym = symbol_at(symbol_rows, f)
        pred_span_symbol = math.exp(-sym["sigma_per_cell"] * span)
        model = span_decay_prediction(abs(k_fit), omega_lu, fr["c"], nu_lu, alpha_lu,
                                      gamma, float(filt["strength"]),
                                      int(filt["passes"]), span)
        meas_span = abs(a_plus[rows_sorted[-1]]) / abs(a_plus[rows_sorted[0]])
        amp_err = abs(meas_span - pred_span_symbol)
        per_cell_meas = -math.log(meas_span) / span if meas_span > 0 else float("nan")
        decay_norm = {r: abs(a_plus[r]) * math.exp((r - rows_sorted[0])
                                                   * sym["sigma_per_cell"])
                      for r in rows_sorted}
        dvals = np.array([decay_norm[r] for r in rows_sorted])
        scatter = float((dvals.max() - dvals.min()) / dvals.mean())

        # A5: velocity channel vs pressure-gradient channel (sinc at v2 k_fit)
        sinc = math.sin(abs(k_fit) * d_st) / max(abs(k_fit) * d_st, 1e-300)
        chan = {}
        worst_chan_amp = 0.0
        worst_chan_phase = 0.0
        for r in control_rows:
            dpdy = (inj["p_hat"][r + d_st] - inj["p_hat"][r - d_st]) / (2.0 * d_st)
            u_grad = -dpdy / (1j * omega_lu * fr["rho0"]) / sinc
            rr = inj["v_hat"][r] / u_grad
            chan[r] = _cplx(rr)
            worst_chan_amp = max(worst_chan_amp, abs(abs(rr) - 1.0))
            worst_chan_phase = max(worst_chan_phase, abs(_phase_deg(rr)))

        rows = {
            "amplitude_span_vs_prediction": {
                "measured_span_ratio": float(meas_span),
                "predicted_span_ratio_symbol": float(pred_span_symbol),
                "symbol_at_f": sym,
                "per_cell_measured": per_cell_meas,
                "model_vs_symbol_diagnostic": {
                    "classical_filter_span_ratio": model["span_ratio"],
                    "per_cell_classical": model["per_cell_classical"],
                    "per_cell_filter": model["per_cell_filter"],
                    "note": "v1 reference formula, archived as medium "
                            "characterization delta (wrong physics for the "
                            "simplified-collision longitudinal mode)"},
                "abs_err": float(amp_err), "gate": gates["amplitude_span_rel"],
                "passed": bool(amp_err <= gates["amplitude_span_rel"]),
            },
            "phase_linearity": {
                "max_residual_deg": resid_deg, "gate": gates["phase_residual_deg"],
                "k_fit_lu": float(k_fit),
                "k_local_stage1": {str(r): v for r, v in fit2["k_local_by_row"].items()},
                "c_meas_m_s": float(c_meas_si),
                "c_dev_vs_air": float(c_dev),
                "c_gate_note": ("10 kHz leg gates |c_dev|<=2% (inherited M4 "
                                "calibration); other frequencies archived as "
                                "instrument characterization"),
                "c_gated_here": bool(fp.get("gate_c_dev", False)),
                "passed": bool(resid_deg <= gates["phase_residual_deg"]
                               and (not fp.get("gate_c_dev", False)
                                    or abs(c_dev) <= gates["c_dev_rel_10k"])),
            },
            "incoming_contamination": {
                "by_row": {str(r): incoming[r] for r in control_rows},
                "value_max": float(max(incoming.values())), "gate": gates["incoming_ratio"],
                "z_eff_over_z0": float(z_eff / z0),
                "nominal_z0_diagnostic": {str(r): incoming_nominal_z0[r]
                                          for r in control_rows},
                "rigid_top_control_min": float(min(rigid_incoming.values()))
                if rigid_incoming else None,
                "rigid_control_gate": gates["rigid_control_min"],
                "passed": bool(max(incoming.values()) <= gates["incoming_ratio"]
                               and rigid_incoming
                               and min(rigid_incoming.values()) >= gates["rigid_control_min"]),
            },
            "control_surface_position_sensitivity": {
                "scatter_rel": scatter, "gate": gates["position_scatter_rel"],
                "passed": bool(scatter <= gates["position_scatter_rel"]),
            },
            "channel_consistency": {
                "by_row": {str(r): chan[r] for r in control_rows},
                "worst_amp_rel": worst_chan_amp, "worst_phase_deg": worst_chan_phase,
                "sinc_correction": float(sinc),
                "gate": [gates["channel_amp_rel"], gates["channel_phase_deg"]],
                "passed": bool(worst_chan_amp <= gates["channel_amp_rel"]
                               and worst_chan_phase <= gates["channel_phase_deg"]),
            },
            "stability": {"injection_finite": inj["finite"],
                          "rigid_control_finite": rigid["finite"],
                          "passed": bool(inj["finite"] and rigid["finite"])},
        }
        gate_rows_by_freq[fkey] = rows
        per_freq[fkey] = {"inj": inj, "a_plus": a_plus, "a_minus": a_minus,
                          "incoming": incoming, "rigid_incoming": rigid_incoming,
                          "k_fit": k_fit, "c_meas": c_meas_si,
                          "symbol": sym, "pred_span_symbol": pred_span_symbol,
                          "model_diag": model}
        log("f=%s: A- max %.4f | span %.4f vs symbol %.4f | resid %.2f deg | "
            "c_meas %.2f (%+.2f%%) | z_eff/z0 %.4f | chan worst %.2f%%/%.2f deg" % (
                fkey, max(incoming.values()), meas_span, pred_span_symbol,
                resid_deg, c_meas_si, 100 * c_dev, z_eff / z0,
                100 * worst_chan_amp, worst_chan_phase))

        g = h5.create_group(f"freq_{fkey}")
        g.create_dataset("t_s", data=inj["t_s"])
        g.create_dataset("p_rows", data=inj["p_rows"])
        g.create_dataset("v_rows", data=inj["v_rows"])
        g.attrs["rows"] = inj["rows"]
        g.attrs["frequency_Hz"] = f

    # ---- D3-3 inherited pulse rows at the injection boundary ----
    pulse = {}
    for bottom in ("rigid", "sponge"):
        r = run_bottom_reflection(base, ny=ny, n_abs=n_abs, bottom=bottom)
        pulse[bottom] = r
        log("pulse bottom=%s: %s" % (bottom, r))
    pulse_ok = (pulse["sponge"].get("R_abs") is not None
                and pulse["sponge"]["R_abs"] < gates["incoming_ratio"]
                and pulse["rigid"].get("R_abs") is not None
                and pulse["rigid"]["R_abs"] > gates["rigid_control_min"])
    injection_boundary_row = {
        "sponge_R": pulse["sponge"].get("R_abs"), "rigid_R": pulse["rigid"].get("R_abs"),
        "gates": [gates["incoming_ratio"], gates["rigid_control_min"]],
        "passed": bool(pulse_ok),
    }

    # ---- compact-source map carriage numbers (supporting archive) ----
    g0_rows = load_g0_alpha_rows(repo_root / G0_TABLE_CSV)
    k_tab = np.array([r[0] for r in g0_rows])
    a_tab = np.array([r[1] for r in g0_rows])
    t_s_hat_ref = float(proto["compact_source_T_s_hat_K"])
    alpha0_si = 2.2233775895e-5  # frozen air value (fine-stack physical block)
    k1_lu = float(proto["k1_lu_fine_stack"])
    k2_lu = float(proto["k2_lu_fine_stack"])
    # alpha_eff(k2)/alpha_eff(k1): the table-carriage factor for the 2f source map
    ratio_k2 = float(np.interp(k2_lu, k_tab, a_tab) / np.interp(k1_lu, k_tab, a_tab))
    compact_source = {}
    for fp in freq_protos:
        f = float(fp["frequency_Hz"])
        omega = 2.0 * math.pi * f
        u_nom = thermal_pumping_velocity_m_s(t_s_hat_ref, T0_K=300.0,
                                             omega_rad_s=omega, alpha_m2_s=alpha0_si)
        compact_source[f"{f:g}"] = {"u_src_nominal_alpha": _cplx(u_nom)}
    u_2f_carried = thermal_pumping_velocity_m_s(
        t_s_hat_ref, T0_K=300.0, omega_rad_s=2.0 * math.pi * 2.0e4,
        alpha_m2_s=ratio_k2 * alpha0_si)
    compact_source["carriage_2f_at_k2"] = {
        "alpha_eff_k2_over_alpha_eff_k1": ratio_k2,
        "u_src_20k_alpha_eff_k2": _cplx(u_2f_carried),
        "note": "2f source mapping must use alpha_eff(k2) from the G0 table "
                "(freeze doc §3.3 output 3); sqrt(alpha) enters via delta_T",
    }

    # ---- verdict ----
    freq_pass = {fk: all(r["passed"] for r in gate_rows_by_freq[fk].values())
                 for fk in gate_rows_by_freq}
    all_pass = all(freq_pass.values()) and pulse_ok
    fk10 = f"{float(freq_protos[0]['frequency_Hz']):g}"
    stable = all(gate_rows_by_freq[fk]["stability"]["passed"] for fk in gate_rows_by_freq)
    labels: list[str] = []
    if all_pass:
        verdict = "PASSED"
    elif freq_pass.get(fk10) and pulse_ok and stable:
        verdict = "SCOPED_CANDIDATE"
        labels.append("G2_2F_NOT_CERTIFIED")
    else:
        verdict = "FAILED"
        labels.append("G2_2F_NOT_CERTIFIED")
    log("verdict=%s labels=%s" % (verdict, labels or "-"))

    # ---- outputs (contract §16.1 seven files) ----
    resolved = {"gate_id": GATE_ID, "case_family": CASE_FAMILY, "protocol": proto,
                "gates": gates, "config_path": str(config_path),
                "acoustic_config": str(acoustic_cfg_path)}
    config_yaml = yaml.safe_dump(resolved, allow_unicode=True, sort_keys=False)
    (out_dir / "config_resolved.yaml").write_text(config_yaml, encoding="utf-8")

    na = "not_applicable_g2a_acoustic_carrier"
    fk_all = list(gate_rows_by_freq.keys())
    summary = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "code_commit": _git_commit(),
        "config_digest": _sha256_bytes(config_yaml.encode())[:12],
        "physics_core_digest": hashlib.sha256(
            b"".join((repo_root / p).read_bytes() for p in PHYSICS_CORE_FILES)
        ).hexdigest()[:12],
        "parent_baseline_run": "M4 d69bf24d881e (acoustic-domain chain) + G1a 20260728T085824Z",
        "phase5_contract_version": PHASE5_CONTRACT_VERSION,
        "work_package": "WP2", "gate_id": GATE_ID, "case_family": CASE_FAMILY,
        "model_route": "ROUTE_B_MAIN",
        "property_model_id": "phase4_acoustic_coarse_dx334 (simplified collision; "
                             "c0 knob = M4 (iv) 10 kHz calibration, not re-fit)",
        "tau_policy": "acoustic-domain artificial nu x100 (frozen Phase_4 asset)",
        "mapping_digest": _sha256_bytes(Path(acoustic_cfg_path).read_bytes())[:12],
        "background_path": "uniform_reference_state",
        "forcing_protocol": "one_way_additive_soft_source_monochromatic (no thermal feedback)",
        "P_mean_W_m2": 0.0, "P_mean_rematched": False, "target_Theta_DC": 0.0,
        "frequency_Hz": [float(fp["frequency_Hz"]) for fp in freq_protos],
        "T_ambient_K": 300.0, "T_mean_K": 300.0,
        "epsilon_AC_measured": {"pressure_rel": eps},
        "Theta_DC_measured": 0.0,
        "chi_0": None, "chi_eff": None, "C_A_J_m2K": None,
        "dc_heat_sink_model": na, "dc_heat_sink_parameters": None,
        "H_s_role": "acoustic domain height (sponged open)",
        "thermal_resistance_effective": None,
        "grid_shape": [ny, nx], "dx_m": dx_m, "dt_s": dt_s,
        "domain_height_m": ny * dx_m,
        "boundary_model": "top/bottom sponges + additive soft source (D3-3 one-way)",
        "wall_mass_policy": na,
        "wall_neutrality_gate_id": na,
        "boundary_mass_flux_definition": na, "boundary_mass_flux_0f_to_3f": None,
        "spectral_operator_stack_id": "acoustic_simplified_collision (no dispersion / "
                                      "no acoustic-phase); biharmonic filter 0.03 x 6",
        "spectral_correction_enabled": False,
        "high_wavenumber_filter_enabled": True,
        "high_wavenumber_filter_strength": float(filt["strength"]),
        "operator_ablation_run_id": "G2-O (fine-stack operators; separate family)",
        "q_feedback_relax": None,
        "fit_window": {"per_frequency_fit_periods": {
            f"{float(fp['frequency_Hz']):g}": float(fp["fit_periods"]) for fp in freq_protos}},
        "fit_cycles": None, "detrend_order": 0, "harmonic_order_max": 3,
        "harmonic_fit_condition_number": None,
        "U_det": {fk: {"position_scatter": gate_rows_by_freq[fk][
            "control_surface_position_sensitivity"]["scatter_rel"]} for fk in fk_all},
        "U95_fit": None,
        "U_gov": {fk: gate_rows_by_freq[fk]["control_surface_position_sensitivity"][
            "scatter_rel"] for fk in fk_all},
        "no_clipping": True, "no_floor": True, "no_positivity_repair": True,
        "gate_status": verdict, "scoped_limitations": labels,
        "smoke_mode": bool(smoke),
        "fixture_version": "v2 (symbol-referenced span + two-stage phase fit + "
                           "z_eff characteristic basis)",
        "v1_diagnostic_run": "20260730T095503Z (aliasing + medium-symbol "
                             "mismatch exposed; archived, superseded)",
        "medium_symbol_rows": symbol_rows,
        "results": {
            "T_s_hat_1f": None, "p_hat_1f": None, "p_hat_2f": None, "p_hat_3f": None,
            "outgoing_mode_1f": {fk: {str(r): _cplx(per_freq[fk]["a_plus"][r])
                                      for r in sorted(per_freq[fk]["a_plus"])}
                                 for fk in fk_all},
            "outgoing_mode_2f": None, "outgoing_mode_3f": None,
            "outgoing_mode_note": "A+ characteristic amplitude at control rows "
                                  "(carrier certification; thermal 2f content is "
                                  "a G2-T/fine-stack quantity)",
            "G1": None, "D_G": None, "D_OP": None,
            "H2": None, "H3": None, "m1": None, "m2": None, "m3": None,
            "m_note": na,
            "QS0_error_amplitude": None, "QS0_error_phase": None,
            "QS1_error_amplitude": None, "QS1_error_phase": None,
            "wall_boundary_sensitivity": None,
            "operator_sensitivity_D_G": None, "operator_sensitivity_H2": None,
            "operator_sensitivity_H3": None, "operator_note": na,
            "boundary_mass_flux_0f_to_3f": None,
            "energy_residual": None, "mass_or_flux_residual": None,
            "wall_temperature_error": None,
            "realized_phase_velocity_m_s": {fk: per_freq[fk]["c_meas"] for fk in fk_all},
            "injection_boundary_pulse": injection_boundary_row,
            "compact_source_map": compact_source,
        },
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=1, default=float), encoding="utf-8")
    (out_dir / "harmonic_fit.json").write_text(
        json.dumps({"note": "monochromatic carrier; 1f readout archived in summary; "
                            "row time series in signals.h5"}, indent=1),
        encoding="utf-8")
    provenance = {
        "run_id": run_id, "command": " ".join(sys.argv),
        "python": sys.version.split()[0], "numpy": np.__version__,
        "code_commit": summary["code_commit"],
        "physics_core_digest": summary["physics_core_digest"],
        "acoustic_config_sha256": _sha256_bytes(Path(acoustic_cfg_path).read_bytes()),
        "d3_lineage": "D3-2 sponge |R| PASS; D3-3 one-way injection PASS; M4 "
                      "PASSED_WITH_SCOPED_RISK (10 kHz E2 1.62%)",
        "g0_alpha_table": str(G0_TABLE_CSV),
    }
    (out_dir / "provenance.json").write_text(json.dumps(provenance, indent=1, default=float),
                                             encoding="utf-8")
    (out_dir / "gate_evaluation.json").write_text(
        json.dumps({"gate_id": GATE_ID, "verdict": verdict, "labels": labels,
                    "rows_by_frequency": gate_rows_by_freq,
                    "injection_boundary_pulse": injection_boundary_row},
                   indent=1, default=float), encoding="utf-8")

    report = [f"# G2-A run {run_id}", "",
              f"- verdict: **{verdict}** labels={labels or '-'}",
              f"- smoke_mode: {smoke}", "",
              "## Gate rows by frequency (contract §7.2)", ""]
    for fk in fk_all:
        report.append(f"### f = {fk} Hz")
        for name, row in gate_rows_by_freq[fk].items():
            report.append(f"- {name}: passed={row['passed']}")
        report.append("- realized phase velocity: %.2f m/s (%+.2f%% vs air)" % (
            per_freq[fk]["c_meas"], 100 * (per_freq[fk]["c_meas"] / AIR_C0_M_S - 1)))
        report.append("")
    report.append(f"- injection boundary pulse rows: passed={injection_boundary_row['passed']}")
    (out_dir / "run_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    h5.close()
    log(f"outputs -> {out_dir}")
    return {"verdict": verdict, "labels": labels, "out_dir": str(out_dir),
            "summary": summary, "gate_rows_by_freq": gate_rows_by_freq,
            "injection_boundary_pulse": injection_boundary_row}


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase_5 G2-A acoustic-transfer gate")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--output-root", type=Path, default=None)
    args = parser.parse_args()
    result = run_g2a(args.config, args.output_root, smoke=args.smoke)
    return 0 if result["verdict"] in {"PASSED", "SCOPED_CANDIDATE"} else 1


if __name__ == "__main__":
    sys.exit(main())
