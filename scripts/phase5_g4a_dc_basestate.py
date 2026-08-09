"""Phase_5 G4a runner: steady DC base state + small increments (contract §9.1).

ARCHITECTURE (pre-registered 2026-07-30, dc_protocol_report.md §A.0): the tent
(symmetric-mirror) double-band rig — y-periodic domain of height 2*H_s with
TWO certified v1.1 symmetric mass-neutral bands: the hot band (film face,
theta_w(t)) at row 0 and the ambient sink band (canonical isothermal reservoir
T(H_s)=T_ambient) at row H_s. The field is a continuous tent profile with no
first-order jump anywhere — the WP1-3 lid-rig death variable (full Theta jump
across the wrap-adjacent wall|lid pair x closed cavity) is absent by
construction. The gas splits into two independent columns, each an exact
realization of the canonical problem (hot face -> H_s gas -> ambient face),
giving a built-in duplicate check (probe: bit-level column agreement 6.4e-14).

REFERENCE INSTRUMENTS (this module, anchored in the contract tests):
  tent_spectral_reference — small-amplitude cold-background response of the
    tent rig from TWO point sources superposed on the G1-W certified
    coefficient structure (per-mode alpha_eff(k) table), with the drive
    constraint T_hat(0)=1 and the sink constraint T_hat(hs)=0. Certifies the
    tent instrument chain before the DC base state enters (regression row).
  tent_bvp_reference — variable-coefficient spectral-operator BVP
    i w [th - (g-1)/g <th>] - D1 diag(alpha(y)) D1 th = 0 with the two band
    constraints; alpha(y) evaluated on the measured base state T0(y) via the
    G0 k1 temperature law (QS-1 operationalization, §11.3). In the
    constant-alpha limit it must reproduce tent_spectral_reference to
    machine precision (asserted in tests) — QS-0 and the regression reference
    are special cases of the same operator.
  conduction_seed — analytic tent conduction profile (pressure-uniform rho)
    used to seed the base-state settle (the stationarity row is the arbiter;
    the seed only buys settle time; init-condition branch row uses a uniform
    init instead and must converge to the same base state).
  make_energy_audited_band — wraps a band callback and records the EXACT
    per-step mass and energy deltas the band applies (the g-shift bookkeeping
    is the physical heat absorbed/injected by the reservoir): the DC closure
    row (q_hot vs q_sink) and the AC admittance readout both consume these
    exact bookkeeping observables (no transport calibration involved).

Continuum anchor: for constant alpha the tent response per hot face tends to
Y/Y_hs = coth(m H_s), m=sqrt(i w/alpha) (Dirichlet-Dirichlet slab); the
discrete-vs-continuum gap is the same machinery-identity family as G2-T
(archived, enters the documented budget).
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.macroscopic import recover_macro  # noqa: E402
from core.solver import GasSolver2D  # noqa: E402
from boundary.wall_thermal_mass_neutral import (  # noqa: E402
    make_symmetric_mass_neutral_band_callback,
    make_symmetric_mass_neutral_wall_callback,
)
from scripts.phase2_m2_verification import load_config  # noqa: E402


# ---------------------------------------------------------------------------
# reference instruments
# ---------------------------------------------------------------------------

def _mode_coeffs(n: int, omega_lu: float, alpha_nom: float,
                 k_tab: np.ndarray, a_tab: np.ndarray,
                 *, highk_policy: str, gamma: float) -> np.ndarray:
    """Per-mode response coefficients of the G1-W certified sealed operator."""

    def alpha_of(k: float) -> float:
        if k <= k_tab[0]:
            return float(a_tab[0])
        if k <= k_tab[-1]:
            return float(np.interp(k, k_tab, a_tab))
        return float(a_tab[-1]) if highk_policy == "hold_last" else alpha_nom

    coeffs = np.empty(n, dtype=complex)
    for j in range(n):
        k = 2.0 * math.pi * min(j, n - j) / n
        if j == 0:
            coeffs[j] = gamma / (1j * omega_lu * n)
        else:
            coeffs[j] = 1.0 / (n * (1j * omega_lu + alpha_of(k) * k * k))
    return coeffs


def tent_spectral_reference(n_cells: int, hs: int, omega_lu: float,
                            alpha_nom: float, k_tab: np.ndarray,
                            a_tab: np.ndarray, *, highk_policy: str,
                            gamma: float) -> dict[str, Any]:
    """Tent-rig small-amplitude reference: two point sources, two constraints.

    T_hat(y) = s0*G(y) + s1*G(y-hs) with G the certified periodic single-source
    response; constraints T_hat(0)=1 (drive), T_hat(hs)=0 (sink). Returns the
    per-hot-face admittance ratio Y/Y_hs at NOMINAL transport, the profile,
    the source strengths (exact bookkeeping counterparts: s0 = total injected
    by the hot band per unit T_hat_w, -s1 = total absorbed by the sink), and
    the continuum coth anchor.
    """

    n = int(n_cells)
    hs = int(hs)
    coeffs = _mode_coeffs(n, omega_lu, alpha_nom, k_tab, a_tab,
                          highk_policy=highk_policy, gamma=gamma)
    y = np.arange(n)
    modes = np.exp(2j * np.pi * np.outer(np.arange(n), y) / n)  # (j, y)
    green = (coeffs[:, None] * modes).sum(axis=0)                # G(y), G(0)=sum c_j
    g0 = green[0]
    ghs = green[hs % n]
    # [G(0) G(hs); G(hs) G(0)] [s0 s1]^T = [1 0]^T  (G is even on the lattice)
    det = g0 * g0 - ghs * ghs
    s0 = g0 / det
    s1 = -ghs / det
    profile = s0 * green + s1 * np.roll(green, hs)
    y_face = s0 / 2.0                                            # per hot face
    y_hs = complex(np.sqrt(1j * omega_lu * alpha_nom))
    m_hs = complex(np.sqrt(1j * omega_lu / alpha_nom)) * hs
    coth = 1.0 / np.tanh(m_hs)
    return {"Y_over_Yhs": y_face / y_hs, "profile_over_Tw": profile,
            "s_hot": s0, "s_sink": s1,
            "sink_transfer": s1 / s0,
            "coth_continuum_anchor": y_face / y_hs / coth,
            "highk_policy": highk_policy, "gamma": gamma}


def tent_bvp_reference(alpha_y: np.ndarray, hs: int, omega_lu: float,
                       alpha_nom: float, *, gamma: float) -> dict[str, Any]:
    """Variable-coefficient tent BVP (QS-1 operationalization, §11.3).

    Solves i w [th - (g-1)/g <th>] - D1 diag(alpha(y)) D1 th = 0 on the
    periodic lattice (spectral first-derivative D1, conservative form) with
    rows 0 and hs replaced by the Dirichlet constraints th(0)=1, th(hs)=0.
    In the constant-alpha limit this reproduces tent_spectral_reference to
    machine precision (mode-space identity; asserted in the contract tests).
    Returns the same observables built from the solved profile: per-face
    admittance from the spectral flux jump at the hot band.
    """

    alpha_y = np.asarray(alpha_y, dtype=float)
    n = alpha_y.shape[0]
    hs = int(hs)
    k = 2.0 * math.pi * np.fft.fftfreq(n)
    F = np.exp(-2j * np.pi * np.outer(np.arange(n), np.arange(n)) / n)  # DFT
    Fi = np.conj(F) / n                                                  # inverse
    D1 = Fi @ (1j * k[:, None] * F)
    L = D1 @ np.diag(alpha_y) @ D1                    # conservative d/dy(a d/dy)
    op = 1j * omega_lu * (np.eye(n) - (gamma - 1.0) / gamma * np.ones((n, n)) / n) - L
    rhs = np.zeros(n, dtype=complex)
    op[0, :] = 0.0
    op[0, 0] = 1.0
    rhs[0] = 1.0
    op[hs, :] = 0.0
    op[hs, hs] = 1.0
    rhs[hs] = 0.0
    profile = np.linalg.solve(op, rhs)
    # exact bookkeeping counterpart: injected source at the constrained rows =
    # residual of the unconstrained operator applied to the solution
    op_free = 1j * omega_lu * (np.eye(n) - (gamma - 1.0) / gamma
                               * np.ones((n, n)) / n) - L
    resid = op_free @ profile
    s0 = complex(resid[0])
    s1 = complex(resid[hs])
    y_hs = complex(np.sqrt(1j * omega_lu * alpha_nom))
    return {"Y_over_Yhs": (s0 / 2.0) / y_hs, "profile_over_Tw": profile,
            "s_hot": s0, "s_sink": s1, "gamma": gamma}


def conduction_seed(ny: int, theta_hot: float, theta_amb: float) -> np.ndarray:
    """Analytic tent conduction profile (linear per column) for the settle seed."""

    y = np.arange(ny)
    hs = ny // 2
    dist = np.minimum(y, ny - y)
    return theta_amb + (theta_hot - theta_amb) * (1.0 - dist / hs)


def make_energy_audited_band(inner_callback, recorder: dict[str, list[float]],
                             lattice, key: str):
    """Wrap a band callback; record EXACT per-step mass and energy deltas.

    The band's g-shift energy pinning is the physical reservoir exchange: the
    recorded per-step energy delta (kinetic trace + internal) over the band
    row is the exact heat the band injected (+) or absorbed (-) that step —
    the DC closure row and the AC admittance consume these observables (no
    transport calibration involved).
    """

    c2 = np.sum(np.asarray(lattice.c, dtype=float) ** 2, axis=-1)

    def _cb(*, solver, f_post, g_post, f_stream, g_stream):
        e_before = float(np.sum(0.5 * f_stream * c2) + np.sum(g_stream))
        m_before = float(np.sum(f_stream))
        f_stream, g_stream = inner_callback(
            solver=solver, f_post=f_post, g_post=g_post,
            f_stream=f_stream, g_stream=g_stream)
        recorder.setdefault(f"{key}_dE", []).append(
            float(np.sum(0.5 * f_stream * c2) + np.sum(g_stream)) - e_before)
        recorder.setdefault(f"{key}_dM", []).append(
            float(np.sum(f_stream)) - m_before)
        return f_stream, g_stream

    return _cb


# ---------------------------------------------------------------------------
# tent rig execution
# ---------------------------------------------------------------------------

def run_tent(gas_cfg: dict, *, ny: int, nx: int, theta_dc: float,
             frequency_hz: float, eps_ac: float,
             settle_periods: float, drive_periods: float,
             samples_per_period: int, init: str = "seed",
             theta_hot_mean_override: float | None = None,
             coupled: dict | None = None, snapshot: bool = False,
             log=print) -> dict[str, Any]:
    """One tent-rig case: DC settle then (optional) AC drive.

    Phase 1 (settle): both bands at their mean setpoints; the analytic
    conduction seed (init="seed") or a uniform ambient state (init="uniform",
    the §9.1 init-condition branch) relaxes to the base state. The last settle
    period is sampled for the stationarity row and the base profile T0(y).
    Phase 2 (drive): eps_ac>0 adds a cosine-ramped sinusoid on the hot band —
    prescribed-theta branch (i); with ``coupled`` the hot-band setpoint is the
    film ODE state driven by P(t) = P_mean + P1*cos and closed on the EXACT
    hot-band bookkeeping heat (free of transport calibration; the G1b moment-DC
    and sealed-energy-identity channels are both absent from this loop).
    Every step both bands run under the energy/mass audit wrapper.
    """

    cfg = copy.deepcopy(gas_cfg)
    cfg["numerics"] = {**cfg["numerics"], "nx": int(nx), "ny": int(ny)}
    solver = GasSolver2D(cfg)
    th0 = float(solver.mapping.theta_ref_lu)
    theta_amb = th0
    theta_hot_mean = (float(theta_hot_mean_override)
                      if theta_hot_mean_override is not None
                      else th0 * (1.0 + float(theta_dc)))
    rho0 = float(solver.mapping.lattice.rho_ref_lu)
    dt_s = float(solver.mapping.lattice.dt_s)
    lattice = solver.lattice
    D = int(solver.mapping.lattice.D)
    S = int(solver.mapping.lattice.S)
    cp_eff = 0.5 * (D + S) + 1.0    # rho*cp=1 units (certified reference caliber;
                                    # cp = cv + R_lu, cv = (D+S)/2, R_lu = 1; cp/cv = gamma)
    hs = ny // 2
    steps_per_period = int(round(1.0 / (frequency_hz * dt_s)))
    sample_every = max(1, steps_per_period // int(samples_per_period))
    om_si = 2.0 * math.pi * frequency_hz

    if init == "seed":
        prof = conduction_seed(ny, theta_hot_mean, theta_amb)
    elif init == "uniform":
        prof = np.full(ny, theta_amb)
        prof[0] = theta_hot_mean
    else:
        raise ValueError(f"unknown init: {init}")
    rho = rho0 * theta_amb / prof
    solver.initialize_from_macro(np.tile(rho[:, None], (1, nx)),
                                 np.zeros((ny, nx, 2)),
                                 np.tile(prof[:, None], (1, nx)))

    rec: dict[str, list[float]] = {}
    state = {"theta_w": float(theta_hot_mean), "t_lu_steps": 0,
             "coupled_Ts": float(theta_hot_mean), "unstable": False}

    def theta_hot_fn(_s):
        return state["theta_w"]

    hot_inner = make_symmetric_mass_neutral_wall_callback(theta_hot_fn)
    sink_inner = make_symmetric_mass_neutral_band_callback(float(theta_amb), hs)
    hot_cb = make_energy_audited_band(hot_inner, rec, lattice, "hot")
    sink_cb = make_energy_audited_band(sink_inner, rec, lattice, "sink")

    def composed(**kw):
        f, g = hot_cb(**kw)
        kw2 = {**kw, "f_stream": f, "g_stream": g}
        return sink_cb(**kw2)

    def x_avg_theta():
        m = recover_macro(solver.f, solver.g, D=D, S=S, lattice=lattice)
        return np.mean(m.theta, axis=1), m

    # ---- phase 1: DC settle ----
    n_settle = int(round(settle_periods * steps_per_period))
    stat_window = []           # per-sample profiles over the LAST settle period
    mass_series = []
    for i in range(n_settle):
        solver.step(1, boundary_callback=composed)
        if i >= n_settle - steps_per_period and (i % sample_every == 0):
            prof_i, m = x_avg_theta()
            if not np.all(np.isfinite(prof_i)):
                return {"finite": False, "phase": "settle", "step": i}
            stat_window.append(prof_i)
            mass_series.append(float(np.sum(solver.f)))
    stat = np.array(stat_window)
    base_profile = stat.mean(axis=0)
    stationarity = float(np.max(np.abs(stat[-1] - stat[0])) / theta_amb)
    # DC closure from bookkeeping over the last settle period (LU energy/step)
    per = steps_per_period
    q_hot_dc = float(np.mean(rec["hot_dE"][-per:]))
    q_sink_dc = float(np.mean(rec["sink_dE"][-per:]))
    dc_closure = abs(q_hot_dc + q_sink_dc) / max(abs(q_hot_dc), 1e-300)
    col_a = base_profile[1:hs]
    col_b = base_profile[ny - 1:hs:-1]
    duplicate = float(np.max(np.abs(col_a - col_b)) / theta_amb)
    theta_dc_meas = float((base_profile[0] - theta_amb) / theta_amb)

    out: dict[str, Any] = {
        "finite": True, "ny": ny, "nx": nx, "hs": hs, "theta0": th0, "rho0": rho0,
        "dt_s": dt_s, "steps_per_period": steps_per_period, "cp_eff": cp_eff,
        "base_profile": base_profile, "stationarity_per_period": stationarity,
        "dc_closure_rel": dc_closure, "column_duplicate_rel": duplicate,
        "q_hot_dc_lu": q_hot_dc, "q_sink_dc_lu": q_sink_dc,
        "theta_dc_measured": theta_dc_meas,
        "mass_drift_settle": abs(mass_series[-1] / mass_series[0] - 1.0)
        if mass_series else float("nan"),
    }
    # P_mean archive in SI (per unit film area): band energy/step -> W/m^2.
    # E_lu per step over nx columns; per-area: /(nx*dx) in lattice metric, SI
    # via the mapping energy scale — archived as the LU number plus the SI
    # conversion the config declares (kept exact and unit-annotated).
    dx_m = float(solver.mapping.lattice.dx_m)
    e_scale = float(getattr(solver.mapping, "energy_si_per_lu", 0.0)) or None
    out["p_mean_lu_per_area"] = q_hot_dc / (nx * dx_m)
    out["energy_si_per_lu"] = e_scale

    if snapshot:
        # WP4-JAB read-only DC base-state snapshot (guide section 4.1): the raw
        # settled state + band identity. Stage intermediates are recomputed by
        # core/tangent_step.py from these fields via the SAME production stage
        # functions, so no derived state is duplicated here. No behavior change
        # when the flag is off (default).
        out["snapshot"] = {
            "f": solver.f.copy(), "g": solver.g.copy(),
            "theta_hot_mean": float(theta_hot_mean),
            "theta_amb": float(theta_amb), "hs": int(hs),
            "ny": int(ny), "nx": int(nx),
            "theta_dc_target": float(theta_dc),
        }

    if eps_ac <= 0.0 and coupled is None:
        return out

    # ---- phase 2: AC drive ----
    n_drive = int(round(drive_periods * steps_per_period))
    t_samp, thw_samp, qhot_samp, qsink_samp = [], [], [], []
    prof_rows_samp = []
    cpl = None
    if coupled is not None:
        # film ODE state starts AT the base fixed point: P_mean balances the
        # measured DC heat exactly (no DC transient by construction).
        # COUPLED-LOOP ACCOUNTING (mechanism closed 2026-08-01, report A.4):
        # the band bookkeeping dE contains the band's OWN repinning energy
        # c_row_cv*delta_theta_w (cv = (D+S)/2 at fixed row density — no pdV);
        # feeding raw dE to the ODE creates a super-Nyquist derivative term
        # with per-step gain cv*rho_row/(nx*C_A) (= 1.244 at the chi0=0.016
        # baseline film -> the authoritative v1 instability; smoke sat at
        # 0.965 < 1). The gas-side instantaneous conductance G_inst is
        # measured open-loop in-run (cv-corrected; ~0 on this lattice) and a
        # semi-implicit update keeps the loop robust for any G_inst >= 0.
        m0 = recover_macro(solver.f, solver.g, D=D, S=S, lattice=lattice)
        rho_row_total = float(np.sum(m0.rho[0, :]))
        c_row_cv = 0.5 * (D + S) * rho_row_total
        n_pre = len(rec["hot_dE"])
        delta_probe = 1e-4 * th0
        state["theta_w"] = theta_hot_mean + delta_probe
        solver.step(1, boundary_callback=composed)
        g_inst = ((rec["hot_dE"][-1] - c_row_cv * delta_probe)
                  - rec["hot_dE"][n_pre - 1]) / nx / delta_probe
        state["theta_w"] = theta_hot_mean
        for _ in range(steps_per_period):       # wash the probe transient
            solver.step(1, boundary_callback=composed)
        q_hot_dc = float(np.mean(rec["hot_dE"][-steps_per_period:]))
        cpl = {"C_A_lu": float(coupled["c_areal_lu"]),
               "P_mean_lu": q_hot_dc / nx,      # per-column-area LU power
               "P1_over_Pmean": float(coupled["p1_over_pmean"]),
               "guard_factor": float(coupled.get("guard_factor", 5.0)),
               "expected_Ts_hat": float(coupled["expected_ts_hat_lu"]),
               "c_row_cv": c_row_cv, "G_inst": float(g_inst)}
        out["coupled_instrument"] = {"c_row_cv": c_row_cv, "G_inst": float(g_inst),
                                     "raw_gain_would_be": c_row_cv / nx
                                     / float(coupled["c_areal_lu"])}
        state["coupled_Ts"] = float(theta_hot_mean)
        state["prev_theta_w"] = float(theta_hot_mean)

    for i in range(n_drive):
        t = i / steps_per_period
        ramp = 0.5 * (1.0 - math.cos(math.pi * min(1.0, t))) if t < 1.0 else 1.0
        phase = om_si * (i * dt_s)
        if coupled is None:
            state["theta_w"] = theta_hot_mean + eps_ac * th0 * ramp * math.cos(phase)
        else:
            p_now = cpl["P_mean_lu"] * (1.0 + cpl["P1_over_Pmean"] * ramp * math.cos(phase))
            # gas heat only: subtract the band's own cv repinning energy
            q_gas = (rec["hot_dE"][-1]
                     - cpl["c_row_cv"] * (state["theta_w"] - state["prev_theta_w"])) / nx
            state["prev_theta_w"] = state["theta_w"]
            # semi-implicit vs the measured instantaneous conductance
            g_i = max(cpl["G_inst"], 0.0)
            state["coupled_Ts"] = ((state["coupled_Ts"]
                                    + (p_now - q_gas + g_i * state["theta_w"])
                                    / cpl["C_A_lu"])
                                   / (1.0 + g_i / cpl["C_A_lu"]))
            state["theta_w"] = state["coupled_Ts"]
            if abs(state["coupled_Ts"] - theta_hot_mean) > (
                    cpl["guard_factor"] * max(cpl["expected_Ts_hat"], 1e-12)):
                state["unstable"] = True
                out["coupled_unstable_at_step"] = i
                break
        solver.step(1, boundary_callback=composed)
        if i % sample_every == 0:
            prof_i, m = x_avg_theta()
            if not np.all(np.isfinite(prof_i)):
                out["finite"] = False
                out["phase"] = "drive"
                return out
            t_samp.append(i * dt_s)
            thw_samp.append(state["theta_w"])
            qhot_samp.append(rec["hot_dE"][-1])
            qsink_samp.append(rec["sink_dE"][-1])
            prof_rows_samp.append(prof_i)

    out["drive"] = {
        "t_s": np.array(t_samp), "theta_w": np.array(thw_samp),
        "q_hot_lu": np.array(qhot_samp), "q_sink_lu": np.array(qsink_samp),
        "profiles": np.array(prof_rows_samp),
        "coupled": None if cpl is None else {**cpl, "unstable": state["unstable"]},
    }
    return out


def fit_admittance(run: dict[str, Any], frequency_hz: float,
                   fit_skip_periods: float, n_harmonics: int = 5) -> dict[str, Any]:
    """Per-face admittance from the EXACT band bookkeeping (theta-flux units).

    Y_face = (1f of q_hot / (rho0 * cp_eff * nx)) / 2 / (1f of theta_w drive),
    directly comparable to the reference's s_hot/2 per unit T_hat_w. All gated
    quantities are ratios of such Y's (the unit bridge cancels); the absolute
    cold-background regression row against tent_spectral_reference carries the
    bridge and is archived with its residual.
    """

    from postproc.multiharmonic_fit import fit_multiharmonic

    d = run["drive"]
    om = 2.0 * math.pi * frequency_hz
    mask = d["t_s"] >= fit_skip_periods / frequency_hz
    fit_q = fit_multiharmonic(d["t_s"][mask], d["q_hot_lu"][mask], om,
                              n_harmonics=n_harmonics)
    fit_w = fit_multiharmonic(d["t_s"][mask], d["theta_w"][mask], om,
                              n_harmonics=n_harmonics)
    q1 = fit_q.harmonic(1)
    w1 = fit_w.harmonic(1)
    y_face = (q1 / (run["rho0"] * run["cp_eff"] * run["nx"])) / 2.0 / w1
    return {"Y_face_theta_units": y_face, "theta_w_hat": w1,
            "q_hot_hat_lu": q1, "h2_q_rel": fit_q.leakage_relative(1)[2]}


# ---------------------------------------------------------------------------
# case worker (module-level, picklable) and assembly
# ---------------------------------------------------------------------------

def _g4a_case_worker(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    label = payload["label"]
    lines: list[str] = []

    def wlog(msg):
        lines.append(str(msg))

    try:
        run = run_tent(payload["gas_cfg"], ny=payload["ny"], nx=payload["nx"],
                       theta_dc=payload["theta_dc"],
                       frequency_hz=payload["frequency_hz"],
                       eps_ac=payload["eps_ac"],
                       settle_periods=payload["settle_periods"],
                       drive_periods=payload["drive_periods"],
                       samples_per_period=payload["samples_per_period"],
                       init=payload.get("init", "seed"),
                       theta_hot_mean_override=payload.get("theta_hot_mean_override"),
                       coupled=payload.get("coupled"),
                       snapshot=payload.get("snapshot", False), log=wlog)
        # keep payload identity for the evaluator
        run["label"] = label
        run["payload_kind"] = payload.get("kind", "base")
        return label, {"ok": True, "run": run, "log": lines}
    except Exception as exc:  # measured death, not a pool crash (S4 discipline)
        return label, {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                       "log": lines}


def assemble_cases(proto: dict[str, Any], gas_cfg: dict) -> list[dict[str, Any]]:
    """Pre-registered case matrix (§9.1). All cases independent (pool-ready).

    State matching (D0-13) is BY CONSTRUCTION: every H_s rung prescribes the
    SAME theta_hot_mean, so the target Theta_DC agrees exactly and P_mean
    becomes the archived derived quantity per rung. The fixed-P_mean physics
    branch and the coupled film-ODE branch are separate follow-up phases run
    AFTER the pool (they consume pool outputs: canonical P_mean / canonical
    increment constants)."""

    f_hz = float(proto["frequency_Hz"])
    nx = int(proto["nx"])
    spp = int(proto["samples_per_period"])
    theta_dc = float(proto["theta_dc"])
    eps_list = [float(e) for e in proto["eps_ac"]]
    rungs = {str(r["name"]): r for r in proto["hs_rungs"]}
    cases: list[dict[str, Any]] = []

    def base_payload(name, rung, **over):
        ny = 2 * int(rung["hs_rows"])
        p = {"label": name, "kind": over.pop("kind", "base"),
             "gas_cfg": gas_cfg, "ny": ny, "nx": nx,
             "frequency_hz": f_hz, "samples_per_period": spp,
             "theta_dc": theta_dc, "eps_ac": 0.0,
             "settle_periods": float(rung["settle_periods"]),
             "drive_periods": 0.0}
        p.update(over)
        return p

    for name, rung in rungs.items():
        cases.append(base_payload(f"base_{name}", rung))
    canon = rungs[str(proto["canonical_rung"])]
    cases.append(base_payload("base_uniform_init", canon, init="uniform",
                              settle_periods=float(proto["uniform_init_settle_periods"])))
    for name, rung in rungs.items():
        for eps in eps_list:
            cases.append(base_payload(
                f"inc_{name}_eps{eps:g}", rung, kind="increment",
                eps_ac=eps, drive_periods=float(proto["drive_periods"])))
    # transverse grid axis (into U_gov): canonical largest-eps at nx doubled
    cases.append(base_payload(
        f"inc_{proto['canonical_rung']}_eps{max(eps_list):g}_nx{2*nx}",
        canon, kind="increment", nx=2 * nx, eps_ac=max(eps_list),
        drive_periods=float(proto["drive_periods"])))
    # cold-background increment anchor (Theta_DC=0): the measured denominator
    # of D_OP and chi_0; unit bridge cancels in every gated ratio
    cases.append(base_payload(
        f"inc_cold_eps{min(eps_list):g}", canon, kind="increment",
        theta_dc=0.0, eps_ac=min(eps_list),
        drive_periods=float(proto["drive_periods"])))
    return cases


# ---------------------------------------------------------------------------
# gate evaluation + run contract
# ---------------------------------------------------------------------------

def _cplx(z: complex) -> dict[str, float]:
    return {"re": float(np.real(z)), "im": float(np.imag(z)),
            "abs": float(abs(z)),
            "phase_deg": float(math.degrees(math.atan2(np.imag(z), np.real(z))))}


def _ratio_row(z: complex, amp_gate: float, phase_gate: float) -> dict[str, Any]:
    amp_err = abs(abs(z) - 1.0)
    ph_err = abs(math.degrees(math.atan2(np.imag(z), np.real(z))))
    return {"ratio": _cplx(z), "amp_rel_err": float(amp_err),
            "phase_deg_err": float(ph_err), "amp_gate": amp_gate,
            "phase_gate_deg": phase_gate,
            "passed": bool(amp_err <= amp_gate and ph_err <= phase_gate)}


def run_g4a(config_path: str | Path, output_root: str | Path | None = None,
            *, smoke: bool = False, workers: int | None = None) -> dict[str, Any]:
    import os

    import h5py
    import yaml

    from postproc.multiharmonic_fit import fit_multiharmonic
    from scripts.phase5_g1a_amplitude_envelope import execute_cases
    from scripts.phase5_g1w_wall_neutrality import (
        G0_TABLE_CSV,
        _git_commit,
        load_g0_alpha_rows,
        measure_extension_rows,
    )

    t_wall0 = datetime.now(timezone.utc)
    cfg_all = load_config(Path(config_path))
    proto = cfg_all["g4a_smoke" if smoke else "g4a"]
    gates = cfg_all["gates"]
    gas_cfg = load_config(REPO_ROOT / str(cfg_all["inheritance"]["gas_config"]))

    log_lines: list[str] = []

    def log(msg: str) -> None:
        line = f"G4A {msg}"
        print(line, flush=True)
        log_lines.append(line)

    f_hz = float(proto["frequency_Hz"])
    eps_list = [float(e) for e in proto["eps_ac"]]
    rungs = {str(r["name"]): r for r in proto["hs_rungs"]}
    canon_name = str(proto["canonical_rung"])
    fit_skip = float(proto["fit_skip_periods"])

    # ---- pool phase: pre-registered independent cases ----
    payloads = assemble_cases(proto, gas_cfg)
    n_workers = workers if workers is not None else max(1, (os.cpu_count() or 4) - 2)
    results = execute_cases(payloads, n_workers, log, worker=_g4a_case_worker)
    for label, res in sorted(results.items()):
        if res.get("ok"):
            r = res["run"]
            log(f"[{label}] finite={r['finite']} stat={r.get('stationarity_per_period', float('nan')):.2e} "
                f"closure={r.get('dc_closure_rel', float('nan')):.2e} "
                f"dup={r.get('column_duplicate_rel', float('nan')):.2e} "
                f"ThetaDC={r.get('theta_dc_measured', float('nan')):.4f}")
        else:
            log(f"[{label}] DEAD: {res['error']}")

    def run_of(label: str) -> dict[str, Any] | None:
        res = results.get(label)
        return res["run"] if res and res.get("ok") and res["run"].get("finite") else None

    # ---- admittances ----
    y_by = {}
    for label, res in results.items():
        if res.get("ok") and res["run"].get("drive") is not None and res["run"]["finite"]:
            y_by[label] = fit_admittance(res["run"], f_hz, fit_skip)
    canon_inc_label = f"inc_{canon_name}_eps{max(eps_list):g}"
    cold_label = f"inc_cold_eps{min(eps_list):g}"

    # ---- follow-up A: fixed-P_mean physics branch (sequential Newton) ----
    canon_base = run_of(f"base_{canon_name}")
    fixedp_rows: dict[str, Any] = {}
    if canon_base is not None and proto.get("fixed_p_branch", True):
        p_target = canon_base["q_hot_dc_lu"] / canon_base["nx"]
        theta_dc0 = float(proto["theta_dc"])
        fp_payloads = []
        for name, rung in rungs.items():
            if name == canon_name:
                continue
            ratio = float(rung["hs_rows"]) / float(rungs[canon_name]["hs_rows"])
            guess_dc = theta_dc0 * ratio          # linear-conduction first guess
            fp_payloads.append({**assemble_cases(proto, gas_cfg)[0],
                                "label": f"fixedP_{name}_guess", "kind": "fixedP",
                                "ny": 2 * int(rung["hs_rows"]),
                                "theta_dc": guess_dc,
                                "settle_periods": float(rung["settle_periods"]),
                                "drive_periods": 0.0, "eps_ac": 0.0})
        fp1 = execute_cases(fp_payloads, n_workers, log, worker=_g4a_case_worker)
        fp2_payloads = []
        for name, rung in rungs.items():
            if name == canon_name:
                continue
            g = fp1.get(f"fixedP_{name}_guess")
            if not (g and g.get("ok") and g["run"]["finite"]):
                fixedp_rows[name] = {"status": "guess_dead"}
                continue
            q_g = g["run"]["q_hot_dc_lu"] / g["run"]["nx"]
            dc_g = g["run"]["theta_dc_measured"]
            dc_corr = dc_g * p_target / q_g       # one Newton step (conduction ~linear)
            fp2_payloads.append({**fp_payloads[0], "label": f"fixedP_{name}",
                                 "ny": 2 * int(rung["hs_rows"]),
                                 "theta_dc": dc_corr,
                                 "settle_periods": float(rung["settle_periods"])})
        fp2 = execute_cases(fp2_payloads, n_workers, log, worker=_g4a_case_worker) if fp2_payloads else {}
        for name in rungs:
            if name == canon_name:
                continue
            r = fp2.get(f"fixedP_{name}")
            if r and r.get("ok") and r["run"]["finite"]:
                rr = r["run"]
                fixedp_rows[name] = {
                    "status": "ok",
                    "theta_dc_at_fixed_P": rr["theta_dc_measured"],
                    "p_rel_err_vs_target": abs(rr["q_hot_dc_lu"] / rr["nx"] / p_target - 1.0),
                }
            else:
                fixedp_rows.setdefault(name, {"status": "newton_dead"})

    # ---- follow-up B: coupled film-ODE branch (canonical rung) ----
    coupled_row: dict[str, Any] = {"status": "not_run"}
    if proto.get("coupled_branch", True) and canon_base is not None \
            and canon_inc_label in y_by:
        yfit = y_by[canon_inc_label]
        run_c = run_of(canon_inc_label)
        om_step = 2.0 * math.pi / run_c["steps_per_period"]
        y_area = 2.0 * yfit["Y_face_theta_units"] * run_c["rho0"] * run_c["cp_eff"]
        chi0 = float(proto["coupled_chi0"])
        c_a_lu = chi0 * 2.0 * abs(y_area) / om_step
        p1_over = float(proto["coupled_p1_over_pmean"])
        p_mean_area = canon_base["q_hot_dc_lu"] / canon_base["nx"]
        ts_hat_exp = abs(p1_over * p_mean_area
                         / (1j * om_step * c_a_lu + y_area))
        log(f"coupled branch: chi0={chi0} C_A_lu={c_a_lu:.4e} expected |Ts_hat|={ts_hat_exp:.3e}")
        cpl_payload = {"label": "coupled_canonical", "kind": "coupled",
                       "gas_cfg": gas_cfg, "ny": run_c["ny"],
                       "nx": int(proto["nx"]),
                       "frequency_hz": f_hz,
                       "samples_per_period": int(proto["samples_per_period"]),
                       "theta_dc": float(proto["theta_dc"]), "eps_ac": 0.0,
                       "settle_periods": float(rungs[canon_name]["settle_periods"]),
                       "drive_periods": float(proto["drive_periods"]),
                       "coupled": {"c_areal_lu": c_a_lu,
                                   "p1_over_pmean": p1_over,
                                   "guard_factor": 5.0,
                                   "expected_ts_hat_lu": ts_hat_exp}}
        cres = execute_cases([cpl_payload], 1, log, worker=_g4a_case_worker)
        cr = cres.get("coupled_canonical")
        if cr and cr.get("ok") and cr["run"].get("drive") is not None:
            rr = cr["run"]
            unstable = bool(rr["drive"]["coupled"]["unstable"])
            if not unstable and rr["finite"]:
                om = 2.0 * math.pi * f_hz
                d = rr["drive"]
                mask = d["t_s"] >= fit_skip / f_hz
                fw = fit_multiharmonic(d["t_s"][mask], d["theta_w"][mask], om, n_harmonics=5)
                ts1 = fw.harmonic(1)
                pred = p1_over * p_mean_area / (1j * om_step * c_a_lu + y_area)
                rr_ratio = ts1 / pred
                coupled_row = {
                    "status": "stable",
                    "Ts_hat_measured": _cplx(ts1),
                    "Ts_hat_ode_closed_form": _cplx(pred),
                    "consistency": _ratio_row(rr_ratio,
                                              float(gates["coupled_amp_rel"]),
                                              float(gates["coupled_phase_deg"])),
                    "chi0": chi0, "C_A_lu": c_a_lu,
                }
                log(f"coupled: |Ts_hat|={abs(ts1):.3e} vs ODE {abs(pred):.3e} "
                    f"ratio={abs(rr_ratio):.4f}@{math.degrees(math.atan2(rr_ratio.imag, rr_ratio.real)):+.2f}deg")
            else:
                coupled_row = {"status": "unstable",
                               "unstable_at_step": rr.get("coupled_unstable_at_step")}
        else:
            coupled_row = {"status": "dead",
                           "error": None if not cr else cr.get("error")}

    # ---- QS-0 / QS-1 / D_OP / chi (measured + BVP family predictions) ----
    probe_cfg = copy.deepcopy(gas_cfg)
    probe_cfg["numerics"] = {**probe_cfg["numerics"], "nx": 4, "ny": 8}
    mapping = GasSolver2D(probe_cfg).mapping
    alpha_nom_lu = float(mapping.alpha_lu)
    g0_rows = load_g0_alpha_rows(REPO_ROOT / G0_TABLE_CSV)
    ext_rows = measure_extension_rows(
        probe_cfg, [int(n) for n in proto.get("alpha_extension_ny", [12, 8, 6])],
        alpha_nom_lu, log)
    all_rows = sorted(g0_rows + [(r["k_lu"], r["alpha_eff_lu"]) for r in ext_rows])
    k_tab = np.array([r[0] for r in all_rows])
    a_tab = np.array([r[1] for r in all_rows])
    run_c = run_of(canon_inc_label)
    qs_rows: dict[str, Any] = {"status": "incomplete"}
    if run_c is not None and cold_label in y_by and canon_inc_label in y_by:
        ny_c = run_c["ny"]
        hs_c = run_c["hs"]
        om_lu = 2.0 * math.pi / run_c["steps_per_period"]
        th0 = run_c["theta0"]
        gamma = float(gas_cfg["physical"]["gamma"])
        t_exp = float(proto["qs_alpha_temperature_exponent"])
        prof = run_c["base_profile"] / th0            # T0(y)/T0
        alpha_cold = np.full(ny_c, alpha_nom_lu)
        alpha_qs1 = alpha_nom_lu * prof ** t_exp
        tbar_s = float(prof[0])
        alpha_qs0 = np.full(ny_c, alpha_nom_lu * tbar_s ** t_exp)
        bvp_cold = tent_bvp_reference(alpha_cold, hs_c, om_lu, alpha_nom_lu, gamma=gamma)
        bvp_qs0 = tent_bvp_reference(alpha_qs0, hs_c, om_lu, alpha_nom_lu, gamma=gamma)
        bvp_qs1 = tent_bvp_reference(alpha_qs1, hs_c, om_lu, alpha_nom_lu, gamma=gamma)
        d_op_meas = (y_by[canon_inc_label]["Y_face_theta_units"]
                     / y_by[cold_label]["Y_face_theta_units"])
        d_op_qs0 = bvp_qs0["Y_over_Yhs"] / bvp_cold["Y_over_Yhs"]
        d_op_qs1 = bvp_qs1["Y_over_Yhs"] / bvp_cold["Y_over_Yhs"]
        u_gov_dop = float(gates.get("u_gov_dop_floor", 0.0))
        # SI bridge (analytic, G1-W caliber): |Y_hs|(10 kHz, nominal air)
        y_hs_si = float(proto["y_hs_si_w_m2k"])
        y_cold_si = abs(y_by[cold_label]["Y_face_theta_units"]
                        / complex(np.sqrt(1j * om_lu * alpha_nom_lu))) * y_hs_si
        y_wp_si = abs(y_by[canon_inc_label]["Y_face_theta_units"]
                      / complex(np.sqrt(1j * om_lu * alpha_nom_lu))) * y_hs_si
        om_si = 2.0 * math.pi * f_hz
        c_a_si = float(proto["chi_c_areal_si"])
        qs_rows = {
            "status": "ok",
            "D_OP_measured": _cplx(d_op_meas),
            "D_OP_QS0_pred": _cplx(d_op_qs0),
            "D_OP_QS1_pred": _cplx(d_op_qs1),
            "qs0_residual": float(abs(d_op_meas - d_op_qs0)),
            "qs1_residual": float(abs(d_op_meas - d_op_qs1)),
            "qs_validity_tol": float(max(0.1 * abs(d_op_meas - 1.0), u_gov_dop)),
            "chi_0": float(om_si * c_a_si / (2.0 * y_cold_si)),
            "chi_eff": float(om_si * c_a_si / (2.0 * y_wp_si)),
            "Y_cold_si_w_m2k": y_cold_si, "Y_wp_si_w_m2k": y_wp_si,
            "alpha_temperature_exponent": t_exp,
            "tbar_s_over_t0": tbar_s,
        }
        qs_rows["qs0_valid"] = bool(qs_rows["qs0_residual"] <= qs_rows["qs_validity_tol"])
        qs_rows["qs1_valid"] = bool(qs_rows["qs1_residual"] <= qs_rows["qs_validity_tol"])
        if qs_rows["qs1_valid"]:
            qs_rows["label"] = ("QS0_ENGINEERING_VALID" if qs_rows["qs0_valid"]
                                else "QS1_BASESTATE_VALID")
        else:
            qs_rows["label"] = "DYNAMIC_NONLINEAR_RESIDUAL_IDENTIFIED"
        log(f"QS: D_OP meas {abs(d_op_meas):.4f}@{math.degrees(math.atan2(d_op_meas.imag, d_op_meas.real)):+.2f} "
            f"QS0 {abs(d_op_qs0):.4f} QS1 {abs(d_op_qs1):.4f} -> {qs_rows['label']} "
            f"chi0={qs_rows['chi_0']:.4f} chi_eff={qs_rows['chi_eff']:.4f}")

    # ---- gate rows ----
    rows: dict[str, Any] = {}
    base_labels = [f"base_{n}" for n in rungs] + ["base_uniform_init"]
    stat_vals = {lb: run_of(lb)["stationarity_per_period"]
                 for lb in base_labels if run_of(lb) is not None}
    rows["base_stationarity"] = {
        "by_case": stat_vals, "gate": float(gates["stationarity_per_period"]),
        "passed": bool(stat_vals and max(stat_vals.values()) <= float(gates["stationarity_per_period"]))}
    clos_vals = {lb: run_of(lb)["dc_closure_rel"]
                 for lb in base_labels if run_of(lb) is not None}
    rows["dc_energy_closure"] = {
        "by_case": clos_vals, "gate": float(gates["dc_closure_rel"]),
        "passed": bool(clos_vals and max(clos_vals.values()) <= float(gates["dc_closure_rel"]))}
    dup_vals = {lb: run_of(lb)["column_duplicate_rel"]
                for lb in base_labels if run_of(lb) is not None}
    rows["column_duplicate"] = {
        "by_case": dup_vals, "gate": float(gates["column_duplicate_rel"]),
        "passed": bool(dup_vals and max(dup_vals.values()) <= float(gates["column_duplicate_rel"]))}
    # state matching: Theta_DC per rung vs target (prescribed -> near-exact)
    sm = {}
    for name in rungs:
        r = run_of(f"base_{name}")
        if r is not None:
            sm[name] = {"theta_dc_measured": r["theta_dc_measured"],
                        "p_mean_lu_per_area": r["p_mean_lu_per_area"],
                        "rel_dev_vs_target": abs(r["theta_dc_measured"]
                                                 / float(proto["theta_dc"]) - 1.0)}
    rows["state_matching"] = {
        "by_rung": sm, "gate": float(gates["state_match_rel"]),
        "passed": bool(sm and max(v["rel_dev_vs_target"] for v in sm.values())
                       <= float(gates["state_match_rel"]))}
    # domain sensitivity: Y_inc per rung vs canonical at each eps
    dom = {}
    dom_pass = True
    for eps in eps_list:
        y0 = y_by.get(f"inc_{canon_name}_eps{eps:g}")
        for name in rungs:
            if name == canon_name:
                continue
            yr = y_by.get(f"inc_{name}_eps{eps:g}")
            if y0 is None or yr is None:
                dom_pass = False
                continue
            rr = yr["Y_face_theta_units"] / y0["Y_face_theta_units"]
            row = _ratio_row(rr, float(gates["domain_amp_rel"]),
                             float(gates["domain_phase_deg"]))
            dom[f"{name}_eps{eps:g}"] = row
            dom_pass = dom_pass and row["passed"]
    rows["state_matched_domain_sensitivity"] = {"by_case": dom, "passed": bool(dom and dom_pass)}
    # init-condition branch
    r_seed = run_of(f"base_{canon_name}")
    r_uni = run_of("base_uniform_init")
    if r_seed is not None and r_uni is not None:
        init_dev = float(np.max(np.abs(r_seed["base_profile"] - r_uni["base_profile"]))
                         / r_seed["theta0"])
        rows["init_condition_branch"] = {
            "max_profile_dev_rel": init_dev, "gate": float(gates["init_branch_rel"]),
            "passed": bool(init_dev <= float(gates["init_branch_rel"]))}
    else:
        rows["init_condition_branch"] = {"passed": False, "missing": True}
    # window sensitivity + eps-linearity + nx grid axis -> U_gov
    win_row = {"passed": False}
    u_parts: dict[str, float] = {}
    if run_c is not None:
        d = run_c["drive"]
        om = 2.0 * math.pi * f_hz
        fits = []
        for skip in (fit_skip, fit_skip + 0.5):
            mask = d["t_s"] >= skip / f_hz
            fq = fit_multiharmonic(d["t_s"][mask], d["q_hot_lu"][mask], om, n_harmonics=5)
            fw = fit_multiharmonic(d["t_s"][mask], d["theta_w"][mask], om, n_harmonics=5)
            fits.append(fq.harmonic(1) / fw.harmonic(1))
        wr = fits[1] / fits[0]
        win_row = _ratio_row(wr, float(gates["window_amp_rel"]),
                             float(gates["window_phase_deg"]))
        u_parts["window"] = win_row["amp_rel_err"]
    rows["window_sensitivity"] = win_row
    lin_row = {}
    y_lo = y_by.get(f"inc_{canon_name}_eps{min(eps_list):g}")
    y_hi = y_by.get(f"inc_{canon_name}_eps{max(eps_list):g}")
    if y_lo and y_hi:
        lr = y_hi["Y_face_theta_units"] / y_lo["Y_face_theta_units"]
        lin_row = {"ratio": _cplx(lr), "passed": True,
                   "note": "eps-pair linearity (archived; into U_det)"}
        u_parts["eps_pair"] = abs(abs(lr) - 1.0)
    rows["increment_linearity"] = lin_row
    nx_label = f"inc_{canon_name}_eps{max(eps_list):g}_nx{2*int(proto['nx'])}"
    if nx_label in y_by and canon_inc_label in y_by:
        gr = y_by[nx_label]["Y_face_theta_units"] / y_by[canon_inc_label]["Y_face_theta_units"]
        rows["grid_sensitivity_nx"] = {"ratio": _cplx(gr),
                                       "into_u_gov": abs(abs(gr) - 1.0),
                                       "note": "dx frozen by M3 inheritance; "
                                               "transverse axis only",
                                       "passed": True}
        u_parts["nx_axis"] = abs(abs(gr) - 1.0)
    else:
        rows["grid_sensitivity_nx"] = {"passed": False, "missing": True}
    u_gov = float(np.sqrt(np.sum(np.array(list(u_parts.values())) ** 2))) if u_parts else float("nan")
    # cold regression vs certified tent spectral reference (absolute, archived)
    reg_row = {}
    r_cold = run_of(cold_label)
    if r_cold is not None and cold_label in y_by:
        om_lu = 2.0 * math.pi / r_cold["steps_per_period"]
        ref = tent_spectral_reference(r_cold["ny"], r_cold["hs"], om_lu,
                                      alpha_nom_lu, k_tab, a_tab,
                                      highk_policy="hold_last",
                                      gamma=float(gas_cfg["physical"]["gamma"]))
        meas_ratio = (y_by[cold_label]["Y_face_theta_units"]
                      / (ref["s_hot"] / 2.0))
        reg_row = _ratio_row(meas_ratio, float(gates["regression_amp_rel"]),
                             float(gates["regression_phase_deg"]))
        reg_row["reference_Y_over_Yhs"] = _cplx(ref["Y_over_Yhs"])
        reg_row["coth_continuum_anchor"] = _cplx(ref["coth_continuum_anchor"])
    rows["cold_regression_vs_spectral_reference"] = reg_row or {"passed": False, "missing": True}
    rows["qs_chi"] = {**qs_rows, "passed": bool(qs_rows.get("status") == "ok")}
    rows["coupled_film_ode"] = {**coupled_row,
                                "passed": bool(coupled_row.get("status") == "stable"
                                               and coupled_row.get("consistency", {}).get("passed"))}
    rows["sink_physics_branch_fixed_P"] = {"by_rung": fixedp_rows,
                                           "note": "physics result, NOT gated (D0-13)",
                                           "passed": True}
    rows["numerical_repair"] = {"used": False, "passed": True}

    gated = ["base_stationarity", "dc_energy_closure", "column_duplicate",
             "state_matching", "state_matched_domain_sensitivity",
             "init_condition_branch", "window_sensitivity",
             "cold_regression_vs_spectral_reference", "qs_chi",
             "grid_sensitivity_nx", "numerical_repair"]
    all_pass = all(rows[k].get("passed") for k in gated)
    labels: list[str] = []
    if rows["state_matched_domain_sensitivity"].get("passed") and rows["state_matching"].get("passed"):
        labels.append("DC_BASESTATE_STATE_MATCHED_PASSED")
    elif not rows["state_matched_domain_sensitivity"].get("passed"):
        labels.append("DC_BASESTATE_DOMAIN_NOT_CONVERGED")
    if qs_rows.get("label"):
        labels.append(qs_rows["label"])
    if not rows["coupled_film_ode"]["passed"]:
        labels.append("LEVELC_COUPLED_ROW_NOT_CERTIFIED")
    verdict = "PASSED" if all_pass else "FAILED"
    if all_pass and not rows["coupled_film_ode"]["passed"]:
        verdict = "PASSED"  # coupled row is separately labelled, not blocking (pre-registered)
    log(f"verdict={verdict} labels={labels or '-'}")

    # ---- files ----
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = Path(output_root) if output_root else REPO_ROOT / "results" / "phase5" / "g4a_dc_base"
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    with h5py.File(out_dir / "signals.h5", "w") as h5:
        for label, res in results.items():
            if not (res.get("ok") and res["run"].get("finite")):
                continue
            r = res["run"]
            grp = h5.create_group(f"cases/{label}")
            grp.create_dataset("base_profile", data=r["base_profile"])
            if r.get("drive") is not None:
                for key in ("t_s", "theta_w", "q_hot_lu", "q_sink_lu"):
                    grp.create_dataset(key, data=r["drive"][key])
    digest_src = json.dumps({k: rows[k] for k in sorted(rows)}, sort_keys=True, default=str)
    digest = hashlib.sha256(digest_src.encode()).hexdigest()[:12]
    gate_eval = {"gate": "G4a", "verdict": verdict, "labels": labels,
                 "rows": rows, "u_gov": {"parts": u_parts, "combined": u_gov},
                 "smoke_mode": bool(smoke)}
    (out_dir / "gate_evaluation.json").write_text(
        json.dumps(gate_eval, indent=1, default=float), encoding="utf-8")
    harmonic = {lb: {"Y_face": _cplx(y["Y_face_theta_units"]),
                     "h2_q_rel": y["h2_q_rel"]} for lb, y in y_by.items()}
    (out_dir / "harmonic_fit.json").write_text(
        json.dumps(harmonic, indent=1, default=float), encoding="utf-8")
    summary = {
        "gate": "G4a", "run_id": run_id, "verdict": verdict, "labels": labels,
        "gate_status": verdict, "scoped_limitations": labels,
        "smoke_mode": bool(smoke),
        "architecture": "tent double-band (dc_protocol_report.md A.0; "
                        "probe-certified 2026-07-30)",
        "physics_core_digest": digest,
        "code_commit": _git_commit(),
        "frequency_Hz": f_hz, "theta_dc_target": float(proto["theta_dc"]),
        "eps_ac": eps_list,
        "hs_rungs": {n: int(r["hs_rows"]) for n, r in rungs.items()},
        "results": {
            "state_matching": sm,
            "qs_chi": qs_rows,
            "coupled": coupled_row,
            "fixed_P_branch": fixedp_rows,
            "U_gov": {"parts": u_parts, "combined": u_gov},
        },
        "wall_clock_min": (datetime.now(timezone.utc) - t_wall0).total_seconds() / 60.0,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=1, default=float), encoding="utf-8")
    (out_dir / "config_resolved.yaml").write_text(
        yaml.safe_dump(cfg_all, allow_unicode=True, sort_keys=False), encoding="utf-8")
    provenance = {"run_id": run_id, "gate": "G4a", "smoke": bool(smoke),
                  "argv": sys.argv, "python": sys.version,
                  "machine": os.environ.get("COMPUTERNAME", "unknown"),
                  "workers": n_workers,
                  "started_utc": t_wall0.isoformat(),
                  "finished_utc": datetime.now(timezone.utc).isoformat()}
    (out_dir / "provenance.json").write_text(
        json.dumps(provenance, indent=1, default=float), encoding="utf-8")
    report_lines = [f"# G4a run {run_id}", "",
                    f"verdict: **{verdict}**  labels: {labels}", "",
                    "| gated row | passed |", "|---|---|"]
    for k in gated + ["coupled_film_ode"]:
        report_lines.append(f"| {k} | {rows[k].get('passed')} |")
    report_lines += ["", "```text"] + log_lines + ["```", ""]
    (out_dir / "run_report.md").write_text("\n".join(report_lines), encoding="utf-8")
    log(f"outputs -> {out_dir}")
    return {"verdict": verdict, "labels": labels, "out_dir": str(out_dir),
            "rows": rows, "summary": summary}


def run_coupled_rerun(config_path: str | Path, prior_run_dir: str | Path,
                      output_root: str | Path | None = None) -> dict[str, Any]:
    """Re-run ONLY the coupled film-ODE case against an archived G4a run.

    Consumes the prior run's canonical P_mean and increment admittance (its
    pool rows are untouched and remain authoritative); runs the coupled case
    with the corrected accounting (cv repinning subtraction + semi-implicit
    G_inst, report A.4) and writes a supplementary run dir whose provenance
    points at the prior run id. The prior run's coupled row is superseded by
    this dir's coupled_row (G2-A v1/v2 archival family).
    """

    import os

    import yaml

    from postproc.multiharmonic_fit import fit_multiharmonic

    t0 = datetime.now(timezone.utc)
    cfg_all = load_config(Path(config_path))
    proto = cfg_all["g4a"]
    gates = cfg_all["gates"]
    gas_cfg = load_config(REPO_ROOT / str(cfg_all["inheritance"]["gas_config"]))
    prior = Path(prior_run_dir)
    prior_summary = json.loads((prior / "summary.json").read_text(encoding="utf-8"))
    prior_harm = json.loads((prior / "harmonic_fit.json").read_text(encoding="utf-8"))

    log_lines: list[str] = []

    def log(msg: str) -> None:
        line = f"G4A-CPL {msg}"
        print(line, flush=True)
        log_lines.append(line)

    f_hz = float(proto["frequency_Hz"])
    canon = {str(r["name"]): r for r in proto["hs_rungs"]}[str(proto["canonical_rung"])]
    eps_max = max(float(e) for e in proto["eps_ac"])
    canon_inc = prior_harm[f"inc_{proto['canonical_rung']}_eps{eps_max:g}"]
    y_face = complex(canon_inc["Y_face"]["re"], canon_inc["Y_face"]["im"])

    probe_cfg = copy.deepcopy(gas_cfg)
    probe_cfg["numerics"] = {**probe_cfg["numerics"], "nx": 4, "ny": 8}
    pm = GasSolver2D(probe_cfg).mapping
    dt_s = float(pm.lattice.dt_s)
    dx_m = float(pm.lattice.dx_m)
    rho0 = float(pm.lattice.rho_ref_lu)
    cp_eff = 0.5 * (2 + 3) + 1.0
    steps_per_period = int(round(1.0 / (f_hz * dt_s)))
    om_step = 2.0 * math.pi / steps_per_period

    p_mean_area = float(prior_summary["results"]["state_matching"]
                        [str(proto["canonical_rung"])]["p_mean_lu_per_area"]) * dx_m
    y_area = 2.0 * y_face * rho0 * cp_eff
    chi0 = float(proto["coupled_chi0"])
    c_a_lu = chi0 * 2.0 * abs(y_area) / om_step
    p1_over = float(proto["coupled_p1_over_pmean"])
    ts_hat_exp = abs(p1_over * p_mean_area / (1j * om_step * c_a_lu + y_area))
    log(f"prior run {prior.name}: P_mean={p_mean_area:.4e} C_A_lu={c_a_lu:.4e} "
        f"expected |Ts_hat|={ts_hat_exp:.3e}")

    payload = {"label": "coupled_canonical_rerun", "kind": "coupled",
               "gas_cfg": gas_cfg, "ny": 2 * int(canon["hs_rows"]),
               "nx": int(proto["nx"]), "frequency_hz": f_hz,
               "samples_per_period": int(proto["samples_per_period"]),
               "theta_dc": float(proto["theta_dc"]), "eps_ac": 0.0,
               "settle_periods": float(canon["settle_periods"]),
               "drive_periods": float(proto["drive_periods"]),
               "coupled": {"c_areal_lu": c_a_lu, "p1_over_pmean": p1_over,
                           "guard_factor": 5.0,
                           "expected_ts_hat_lu": ts_hat_exp}}
    label, res = _g4a_case_worker(payload)
    coupled_row: dict[str, Any]
    if res.get("ok") and res["run"].get("drive") is not None and res["run"]["finite"]:
        rr = res["run"]
        unstable = bool(rr["drive"]["coupled"]["unstable"])
        if not unstable:
            om = 2.0 * math.pi * f_hz
            d = rr["drive"]
            mask = d["t_s"] >= float(proto["fit_skip_periods"]) / f_hz
            fw = fit_multiharmonic(d["t_s"][mask], d["theta_w"][mask], om, n_harmonics=5)
            ts1 = fw.harmonic(1)
            pred = p1_over * p_mean_area / (1j * om_step * c_a_lu + y_area)
            ratio = ts1 / pred
            coupled_row = {
                "status": "stable",
                "Ts_hat_measured": _cplx(ts1),
                "Ts_hat_ode_closed_form": _cplx(pred),
                "consistency": _ratio_row(ratio, float(gates["coupled_amp_rel"]),
                                          float(gates["coupled_phase_deg"])),
                "chi0": chi0, "C_A_lu": c_a_lu,
                "instrument": rr.get("coupled_instrument"),
            }
            log(f"coupled rerun: |Ts|={abs(ts1):.3e} vs ODE {abs(pred):.3e} "
                f"ratio={abs(ratio):.4f}@{math.degrees(math.atan2(ratio.imag, ratio.real)):+.2f}deg "
                f"G_inst={rr['coupled_instrument']['G_inst']:.4f}")
        else:
            coupled_row = {"status": "unstable",
                           "unstable_at_step": rr.get("coupled_unstable_at_step"),
                           "instrument": rr.get("coupled_instrument")}
            log(f"coupled rerun STILL UNSTABLE at {rr.get('coupled_unstable_at_step')}")
    else:
        coupled_row = {"status": "dead", "error": res.get("error")}
        log(f"coupled rerun DEAD: {res.get('error')}")
    coupled_row["passed"] = bool(coupled_row.get("status") == "stable"
                                 and coupled_row.get("consistency", {}).get("passed"))
    coupled_row["accounting"] = ("cv repinning subtraction + semi-implicit "
                                 "G_inst (report A.4; supersedes the prior "
                                 "run's raw-feed coupled row)")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = Path(output_root) if output_root else REPO_ROOT / "results" / "phase5" / "g4a_dc_base"
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(json.dumps(coupled_row, sort_keys=True,
                                       default=str).encode()).hexdigest()[:12]
    gate_eval = {"gate": "G4a", "scope": "coupled_row_rerun",
                 "coupled_row": coupled_row,
                 "supersedes_coupled_row_of": prior.name,
                 "verdict_row": "PASSED" if coupled_row["passed"] else "FAILED"}
    (out_dir / "gate_evaluation.json").write_text(
        json.dumps(gate_eval, indent=1, default=float), encoding="utf-8")
    summary = {"gate": "G4a", "run_id": run_id, "scope": "coupled_row_rerun",
               "supersedes_coupled_row_of": prior.name,
               "coupled_row": coupled_row, "physics_core_digest": digest,
               "code_commit": None,
               "wall_clock_min": (datetime.now(timezone.utc) - t0).total_seconds() / 60.0}
    try:
        from scripts.phase5_g1w_wall_neutrality import _git_commit
        summary["code_commit"] = _git_commit()
    except Exception:
        pass
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=1, default=float), encoding="utf-8")
    (out_dir / "config_resolved.yaml").write_text(
        yaml.safe_dump(cfg_all, allow_unicode=True, sort_keys=False), encoding="utf-8")
    (out_dir / "provenance.json").write_text(json.dumps(
        {"run_id": run_id, "scope": "coupled_row_rerun",
         "prior_run": str(prior), "argv": sys.argv,
         "machine": os.environ.get("COMPUTERNAME", "unknown"),
         "python": sys.version,
         "started_utc": t0.isoformat(),
         "finished_utc": datetime.now(timezone.utc).isoformat()},
        indent=1), encoding="utf-8")
    (out_dir / "run_report.md").write_text(
        "\n".join([f"# G4a coupled-row rerun {run_id}",
                   f"supersedes coupled row of: {prior.name}", "",
                   f"row passed: **{coupled_row['passed']}**", "",
                   "```text"] + log_lines + ["```", ""]), encoding="utf-8")
    (out_dir / "harmonic_fit.json").write_text(
        json.dumps({"coupled": coupled_row}, indent=1, default=float), encoding="utf-8")
    log(f"outputs -> {out_dir}")
    return {"coupled_row": coupled_row, "out_dir": str(out_dir)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase_5 G4a DC base-state gate")
    ap.add_argument("--config", default=str(
        REPO_ROOT / "configs" / "phase5" / "g4_dc_base" / "g4a_canonical_10k_dx2p6.yaml"))
    ap.add_argument("--output-root", default=None)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--coupled-rerun-from", default=None,
                    help="prior G4a run dir: re-run ONLY the coupled row "
                         "with the corrected accounting (report A.4)")
    args = ap.parse_args()
    if args.coupled_rerun_from:
        result = run_coupled_rerun(args.config, args.coupled_rerun_from,
                                   args.output_root)
        return 0 if result["coupled_row"]["passed"] else 1
    result = run_g4a(args.config, args.output_root, smoke=args.smoke,
                     workers=args.workers)
    return 0 if result["verdict"] == "PASSED" else 1


if __name__ == "__main__":
    sys.exit(main())
