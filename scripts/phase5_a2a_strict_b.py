"""Phase_5 A2a-STRICT_B original-protocol retest runner (D5-9 plan).

Plan authority: docs/Phase_5/a2a_strict_b_experiment_plan_v1.0.md (PLAN_v1.0,
frozen 2026-08-19).  Purpose: keep the A2a operating conditions and readout
UNCHANGED and replace ONLY the wet-node boundary with the strict-B face
boundary (STRICT_B_HALF_DOMAIN_MIRROR_V1 + strict face-flux wall, G0 branch),
then re-run the time-domain incremental response on mass-matched non-uniform
DC base states and compare against the NEW strict-face Robin QS static family
(QS-0/QS-1/QS-1k, reference/strict_face_robin_qs.py).

Protocol (plan section 2, A2a verbatim): 10 kHz, N=48/nx=8, 64 samples per
period, settle 5 / drive 4 periods, main fit window 2.0T-4.0T (alternate
1.5T-3.5T), Theta_DC in {0, 0.02, 0.05, 0.075, 0.10}, eps_AC cold 0.005 and
hot {0.005, 0.02}; judgement pair hot 0.02 / cold 0.005; hot 0.005 is the
linearity audit only.  The authoritative single-face admittance is
Y_E = (nx^-1 sum_x qhat_hot_x)/That_w / (rho_ref c_p) read from the hot-face
incoming-link ledger with NO /2 (plan section 1).

Mass discipline (plan sections 1/3): each Theta_DC settles its own strict-B
non-uniform DC base with the wet reference pack's M_wet(Theta)/A as the
EXACT initial column mass (single multiplicative seed rescale; no mass or
mean-pressure adjustment afterwards).  Legality gates: finite; per-step
local mass/energy contract <= 1e-12 (design section 5 floor normalization);
initial mass <= 1e-12 of target; whole-run mass drift <= 1e-10;
|pbar_B/pbar_wet - 1| <= 1e-2; stationarity <= 1e-3; DC energy closure
<= 1e-3 (design floor).  Any failure -> UNINTERPRETABLE.

VERDICT DISCIPLINE: this runner outputs DATA plus the mechanical evaluation
of the frozen plan-section-4 rules as ``verdict_candidate`` ONLY (D0-7 /
user decision 2026-08-19: judgement belongs to the user; G0 admission is
FAIL under the G0-B fence, the fence release is a user decision, so every
row carries g0_scope = G0_FENCE_PENDING_USER).  Nothing here grants
scientific qualification, activates hot-point classification, or changes
any Gate / production state.

Checkpointing (B-machine external-termination history): every settle/drive
case checkpoints its full state each period (resume is bit-exact: no RNG,
the drive waveform is a pure function of the step index) and the finished
case is cached by ident; re-running the same command resumes.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from boundary.wall_face_flux_strict import (  # noqa: E402
    BRANCH_G0,
    G0_CONDUCTIVITY_EXPONENT,
    StrictFaceFluxWall,
)
from core.equilibrium import equilibrium_fg  # noqa: E402
from core.macroscopic import recover_macro  # noqa: E402
from core.strict_b_half_domain import StrictBHalfDomain  # noqa: E402
from reference.strict_face_robin_qs import (  # noqa: E402
    g0_alpha_of_k,
    map_strict_base_to_ref,
    robin_qs_matrix_bvp,
    robin_qs_spectral_extension,
    steady_uniform_base,
)
from scripts.phase2_m2_verification import load_config  # noqa: E402
from scripts.phase5_faceflux_strict_b_scan import (  # noqa: E402
    bulk_face_extrapolation,
    quad_face_extrapolation,
)
from scripts.phase5_g1a_amplitude_envelope import execute_cases  # noqa: E402
from scripts.phase5_g1w_wall_neutrality import G0_TABLE_CSV, load_g0_alpha_rows  # noqa: E402
from scripts.phase5_wp4_qs1k_mechanism import fit_exponents  # noqa: E402

UNIT = "A2A-STRICT-B"
CASE_FAMILY = "a2a_strict_b"
CODE_VERSION = "A2A_STRICTB_V1"        # checkpoint ident version

# ---------------------------------------------------------------------------
# FROZEN JUDGEMENT LINES (plan sections 2/3/4; pre-registered, no hot number)
# ---------------------------------------------------------------------------
BRANCH = BRANCH_G0                      # the strict face law under test
GATE_CONTRACT_REL = 1.0e-12             # per-step mass/energy contract
GATE_MASS_INIT_REL = 1.0e-12            # initial mass vs pack target
GATE_MASS_DRIFT_REL = 1.0e-10           # whole-run mass drift vs target
GATE_PMEAN_REL_WET = 1.0e-2             # |pbar_B/pbar_wet - 1|
GATE_STATIONARITY = 1.0e-3              # last-settle-period profile change
GATE_DC_CLOSURE = 1.0e-3                # |<q_h>+<q_c>| (design-floor norm)
GATE_LINEARITY = 1.0e-3                 # |Y_hot(0.02)/Y_hot(0.005) - 1|
GATE_COLD_AMP_REL = 0.10                # plan section 3.5
GATE_COLD_PHASE_DEG = 5.0
# frozen wet cold anchor (single-face, no extra /2; run 20260811T085347Z_auth,
# tangent_PROD_h5e-05_cold.json — plan section 3.5 verbatim)
Y0_WET_COLD = complex(4.998499198013624e-4, 9.596625379939636e-4)
FIT_WINDOW_MAIN = (2.0, 4.0)            # periods (plan section 4)
FIT_WINDOW_ALT = (1.5, 3.5)
N_REF_LADDER = (192, 384, 768)          # strict static reference grids
U_WET_FLOOR_PP = 0.02                   # ceil of the original U_gov=0.016 pp
UPLIFT_FLOOR_PP = 0.1                   # d_op_B - d_op_wet > max(0.1, 2 U_D)
CR_LOWER_MIN = 0.5                      # at 0.05 / 0.10
RESID_CAP_PP = 1.0                      # |R_B| + 2 U_R^B <= 1 pp
PHASE_CAP_DEG = 1.0                     # |dphi| + 2 U_phi <= 1 deg
G0_SCOPE = "G0_FENCE_PENDING_USER"      # user defers the fence decision
JUDGEMENT = "USER_PENDING"              # runner emits candidates only

# plan section 5 minimal-output schema (verbatim order)
CSV_COLUMNS = ["theta_dc", "epsilon_ac", "mass_target", "mass_drift_rel",
               "pmean_rel_wet", "Y_re", "Y_im", "d_op_pct", "phase_deg",
               "qs0_pct", "qs1_pct", "qs1_phase_deg", "qs1k_pct",
               "r_dyn_pp", "phase_resid_deg", "cr_lower", "h2_q_rel",
               "u_d_pp", "u_qs_pp", "g0_scope", "status"]

_EPS = float(np.finfo(float).eps)


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------

def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              cwd=REPO_ROOT, capture_output=True, text=True,
                              timeout=10, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _cplx(z: complex) -> dict[str, float]:
    z = complex(z)
    return {"re": z.real, "im": z.imag, "abs": abs(z),
            "phase_deg": math.degrees(math.atan2(z.imag, z.real))}


def _wrap_deg(x: float) -> float:
    return float((x + 180.0) % 360.0 - 180.0)


def _fg_energy(f: np.ndarray, g: np.ndarray, c2: np.ndarray) -> float:
    """Whole-grid kinetic-trace + internal energy (audited-band caliber)."""

    return float(np.sum(0.5 * f * c2) + np.sum(g))


def target_mass_seed(hd: StrictBHalfDomain, theta_dc: float,
                     mass_per_area: float | None):
    """Linear conduction seed rescaled ONCE to the exact pack mass target.

    mass_per_area = M_wet(Theta)/A from the reference pack (None -> the
    equal-mass rho_ref*N smoke fallback).  Returns (f, g, mass_target_total,
    init_mass_rel).  Nothing downstream may adjust mass or mean pressure
    again (plan section 1).
    """

    n, nx = hd.n_phys, hd.nx
    th0 = float(hd.mapping.theta_ref_lu)
    rho0 = float(hd.mapping.lattice.rho_ref_lu)
    if theta_dc == 0.0:
        prof = np.full(n, th0)
    else:
        prof = th0 * (1.0 + float(theta_dc) * (1.0 - (np.arange(n) + 0.5) / n))
    rho = rho0 * n / np.sum(1.0 / prof) / prof
    f, g = equilibrium_fg(np.tile(rho[:, None], (1, nx)),
                          np.zeros((n, nx, 2)),
                          np.tile(prof[:, None], (1, nx)),
                          hd.mapping.lattice.S, hd.lattice)
    target_area = (float(mass_per_area) if mass_per_area is not None
                   else rho0 * n)
    target_total = target_area * nx
    m_now = float(np.sum(f))
    scale = target_total / m_now
    f = f * scale
    g = g * scale                       # equilibrium is linear in rho
    init_rel = abs(float(np.sum(f)) / target_total - 1.0)
    return f, g, target_total, init_rel


def make_wall(hd: StrictBHalfDomain, theta_hot) -> StrictFaceFluxWall:
    th0 = float(hd.mapping.theta_ref_lu)
    return StrictFaceFluxWall(hd.mapping, hd.lattice, theta_hot=theta_hot,
                              theta_amb=th0, branch=BRANCH, theta_0=th0,
                              ledger=None)


def fit_admittance_window(drive: dict[str, np.ndarray], frequency_hz: float,
                          window_periods: tuple[float, float],
                          rho0: float, cp_eff: float, nx: int,
                          n_harmonics: int = 5) -> dict[str, Any]:
    """Single-face admittance on a CLOSED fit window [lo, hi] periods.

    Identical harmonic machinery and normalization family as the wet A2a fit
    (postproc.multiharmonic_fit, 5 harmonics) with the strict single-face
    rule: NO /2 (plan section 1).
    """

    from postproc.multiharmonic_fit import fit_multiharmonic

    lo, hi = window_periods
    t = np.asarray(drive["t_s"], dtype=float)
    mask = (t >= lo / frequency_hz) & (t <= hi / frequency_hz * (1.0 + 1e-12))
    om = 2.0 * math.pi * frequency_hz
    fit_q = fit_multiharmonic(t[mask], np.asarray(drive["q_hot_lu"])[mask], om,
                              n_harmonics=n_harmonics)
    fit_w = fit_multiharmonic(t[mask], np.asarray(drive["theta_w"])[mask], om,
                              n_harmonics=n_harmonics)
    q1 = fit_q.harmonic(1)
    w1 = fit_w.harmonic(1)
    y_face = (q1 / (rho0 * cp_eff * nx)) / w1
    return {"Y_face_theta_units": y_face, "theta_w_hat": w1,
            "q_hot_hat_lu": q1, "h2_q_rel": float(fit_q.leakage_relative(1)[2])}


# ---------------------------------------------------------------------------
# case workers (module-level, picklable; per-period in-case checkpoints)
# ---------------------------------------------------------------------------

def _steps_per_period(hd: StrictBHalfDomain, frequency_hz: float) -> int:
    return int(round(1.0 / (frequency_hz * float(hd.mapping.lattice.dt_s))))


def _progress_save(path: Path, ident: dict, step: int, f, g, extra: dict) -> None:
    tmp = path.with_suffix(".tmp.npz")
    np.savez_compressed(tmp, ident=json.dumps(ident), step=step, f=f, g=g,
                        **{k: np.asarray(v) for k, v in extra.items()})
    os.replace(tmp, path)


def _progress_load(path: Path, ident: dict):
    if not path.exists():
        return None
    try:
        with np.load(path, allow_pickle=False) as z:
            if json.loads(str(z["ident"])) != ident:
                return None
            return {k: z[k] for k in z.files if k != "ident"}
    except Exception:  # noqa: BLE001 - stale/corrupt progress -> recompute
        return None


def _sb_a2a_settle_worker(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    p = payload
    label = p["label"]
    ident = {"unit": CODE_VERSION, "kind": "settle", "branch": BRANCH,
             "theta_dc": float(p["theta_dc"]), "n_phys": int(p["n_phys"]),
             "nx": int(p["nx"]), "settle_periods": float(p["settle_periods"]),
             "samples_per_period": int(p["samples_per_period"]),
             "frequency_hz": float(p["frequency_hz"]),
             "mass_per_area": (None if p.get("mass_per_area") is None
                               else float(p["mass_per_area"]))}
    ck_dir = Path(p["ckpt_dir"])
    ck_dir.mkdir(parents=True, exist_ok=True)
    ck = ck_dir / f"settle_{label}.npz"
    if ck.exists():
        try:
            with np.load(ck, allow_pickle=False) as z:
                if json.loads(str(z["ident"])) == ident:
                    meta = json.loads(str(z["meta"]))
                    return label, {**meta, "finite": True,
                                   "snapshot_path": str(ck),
                                   "resumed_from_checkpoint": True}
        except Exception:  # noqa: BLE001
            pass

    hd = StrictBHalfDomain(p["gas_cfg"], n_phys=p["n_phys"], nx=p["nx"])
    th0 = float(hd.mapping.theta_ref_lu)
    rho0 = float(hd.mapping.lattice.rho_ref_lu)
    d_int = int(hd.mapping.lattice.D)
    s_int = int(hd.mapping.lattice.S)
    c2 = np.sum(np.asarray(hd.lattice.c, dtype=float) ** 2, axis=-1)
    theta_hot_mean = th0 * (1.0 + float(p["theta_dc"]))
    wall = make_wall(hd, theta_hot_mean)
    spp = _steps_per_period(hd, float(p["frequency_hz"]))
    sample_every = max(1, spp // int(p["samples_per_period"]))
    n_settle = int(round(float(p["settle_periods"]) * spp))

    f, g, mass_target, init_rel = target_mass_seed(
        hd, float(p["theta_dc"]), p.get("mass_per_area"))
    e_cell_ref = 0.5 * (d_int + s_int) * rho0 * th0
    e_floor = 64.0 * _EPS * e_cell_ref * hd.nx           # design section 5 floor
    e0_total = _fg_energy(f, g, c2)
    e_step_floor = 64.0 * _EPS * abs(e0_total)

    prog = ck_dir / f"settle_{label}.progress.npz"
    start = 0
    q_hot_hist: list[float] = []
    q_cold_hist: list[float] = []
    contract_e_max = 0.0
    contract_m_max = 0.0
    mass_min, mass_max = float(np.sum(f)), float(np.sum(f))
    stat_stack: list[np.ndarray] = []
    resume = _progress_load(prog, ident)
    if resume is not None:
        start = int(resume["step"])
        f, g = resume["f"], resume["g"]
        q_hot_hist = list(resume["q_hot"])
        q_cold_hist = list(resume["q_cold"])
        contract_e_max = float(resume["c_e"])
        contract_m_max = float(resume["c_m"])
        mass_min, mass_max = float(resume["m_min"]), float(resume["m_max"])
        stat_stack = [row for row in resume["stat"]] if "stat" in resume else []

    for i in range(start, n_settle):
        e_before = _fg_energy(f, g, c2)
        m_before = float(np.sum(f))
        f, g, de_h, de_c = hd.strict_direct_step(f, g, face_wall=wall)
        e_after = _fg_energy(f, g, c2)
        m_after = float(np.sum(f))
        contract_e_max = max(contract_e_max,
                             abs(e_after - e_before - de_h - de_c)
                             / max(abs(de_h) + abs(de_c), e_step_floor))
        contract_m_max = max(contract_m_max,
                             abs(m_after - m_before) / mass_target)
        mass_min = min(mass_min, m_after)
        mass_max = max(mass_max, m_after)
        q_hot_hist.append(de_h)
        q_cold_hist.append(de_c)
        if i >= n_settle - spp and (i % sample_every == 0):
            m = recover_macro(f, g, D=d_int, S=s_int, lattice=hd.lattice)
            prof_i = np.mean(m.theta, axis=1)
            if not np.all(np.isfinite(prof_i)):
                return label, {"finite": False, "phase": "settle", "step": i}
            stat_stack.append(prof_i)
        if (i + 1) % spp == 0 and (i + 1) < n_settle:
            if not np.all(np.isfinite(f)):
                return label, {"finite": False, "phase": "settle", "step": i}
            _progress_save(prog, ident, i + 1, f, g,
                           {"q_hot": q_hot_hist, "q_cold": q_cold_hist,
                            "c_e": contract_e_max, "c_m": contract_m_max,
                            "m_min": mass_min, "m_max": mass_max,
                            "stat": np.array(stat_stack) if stat_stack
                            else np.zeros((0, hd.n_phys))})

    if not np.all(np.isfinite(f)) or not np.all(np.isfinite(g)):
        return label, {"finite": False, "phase": "settle", "step": n_settle}
    stat = np.array(stat_stack)
    base_profile = stat.mean(axis=0)
    stationarity = float(np.max(np.abs(stat[-1] - stat[0])) / th0)
    q_hot_dc = float(np.mean(q_hot_hist[-spp:]))
    q_cold_dc = float(np.mean(q_cold_hist[-spp:]))
    dc_closure = abs(q_hot_dc + q_cold_dc) / max(abs(q_hot_dc) + abs(q_cold_dc),
                                                 e_floor)
    m_last = recover_macro(f, g, D=d_int, S=s_int, lattice=hd.lattice)
    rho_profile = np.mean(m_last.rho, axis=1)
    p_mean = float(np.mean(m_last.p))
    mass_drift = max(abs(mass_max / mass_target - 1.0),
                     abs(mass_min / mass_target - 1.0))
    meta = {
        "n_phys": int(hd.n_phys), "nx": int(hd.nx), "theta0": th0,
        "rho0": rho0, "dt_s": float(hd.mapping.lattice.dt_s),
        "steps_per_period": spp, "branch": BRANCH,
        "theta_dc_target": float(p["theta_dc"]),
        "theta_hot_mean": float(theta_hot_mean),
        "mass_target_total": float(mass_target),
        "mass_per_area": float(mass_target) / hd.nx,
        "init_mass_rel": float(init_rel),
        "mass_drift_rel_settle": float(mass_drift),
        "contract_energy_rel_max": float(contract_e_max),
        "contract_mass_rel_max": float(contract_m_max),
        "stationarity_per_period": stationarity,
        "dc_closure_rel": float(dc_closure),
        "q_hot_dc_lu": q_hot_dc, "q_cold_dc_lu": q_cold_dc,
        "p_mean_lu": p_mean,
        "theta_dc_quad_extrap": float((quad_face_extrapolation(base_profile)
                                       - th0) / th0),
        "theta_dc_bulk_extrap": float((bulk_face_extrapolation(base_profile,
                                                               "hot")
                                       - th0) / th0),
        "column_replication_rel": float(np.max(np.abs(m_last.theta
                                                      - m_last.theta[:, :1]))
                                        / th0),
        "base_profile": [float(v) for v in base_profile],
        "rho_profile": [float(v) for v in rho_profile],
    }
    tmp = ck.with_suffix(".tmp.npz")
    np.savez_compressed(tmp, ident=json.dumps(ident), meta=json.dumps(meta),
                        f=f, g=g, base_profile=base_profile,
                        rho_profile=rho_profile)
    os.replace(tmp, ck)
    if prog.exists():
        prog.unlink()
    return label, {**meta, "finite": True, "snapshot_path": str(ck)}


def _sb_a2a_drive_worker(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    p = payload
    label = p["label"]
    ident = {"unit": CODE_VERSION, "kind": "drive", "branch": BRANCH,
             "theta_dc": float(p["theta_dc"]), "eps_ac": float(p["eps_ac"]),
             "n_phys": int(p["n_phys"]), "nx": int(p["nx"]),
             "drive_periods": float(p["drive_periods"]),
             "samples_per_period": int(p["samples_per_period"]),
             "frequency_hz": float(p["frequency_hz"]),
             "settle_label": str(p["settle_label"]),
             "mass_per_area": (None if p.get("mass_per_area") is None
                               else float(p["mass_per_area"]))}
    ck_dir = Path(p["ckpt_dir"])
    ck = ck_dir / f"drive_{label}.npz"
    if ck.exists():
        try:
            with np.load(ck, allow_pickle=False) as z:
                if json.loads(str(z["ident"])) == ident:
                    meta = json.loads(str(z["meta"]))
                    drive = {k: z[k] for k in
                             ("t_s", "theta_w", "q_hot_lu", "q_cold_lu")}
                    ledg = {k: z[k] for k in ("ledger_hot", "ledger_cold")}
                    return label, {**meta, "finite": True, "drive": drive,
                                   "ledgers": ledg,
                                   "resumed_from_checkpoint": True}
        except Exception:  # noqa: BLE001
            pass

    # settle snapshot (ident-checked)
    sck = ck_dir / f"settle_{p['settle_label']}.npz"
    with np.load(sck, allow_pickle=False) as z:
        smeta = json.loads(str(z["meta"]))
        f = z["f"].copy()
        g = z["g"].copy()
    if (int(smeta["n_phys"]) != int(p["n_phys"])
            or float(smeta["theta_dc_target"]) != float(p["theta_dc"])
            or (p.get("mass_per_area") is not None
                and abs(float(smeta["mass_per_area"])
                        / float(p["mass_per_area"]) - 1.0) > 1e-12)):
        return label, {"finite": False,
                       "error": "settle snapshot ident mismatch"}

    hd = StrictBHalfDomain(p["gas_cfg"], n_phys=p["n_phys"], nx=p["nx"])
    th0 = float(hd.mapping.theta_ref_lu)
    d_int = int(hd.mapping.lattice.D)
    s_int = int(hd.mapping.lattice.S)
    c2 = np.sum(np.asarray(hd.lattice.c, dtype=float) ** 2, axis=-1)
    theta_hot_mean = float(smeta["theta_hot_mean"])
    mass_target = float(smeta["mass_target_total"])
    spp = int(smeta["steps_per_period"])
    dt_s = float(smeta["dt_s"])
    sample_every = max(1, spp // int(p["samples_per_period"]))
    n_drive = int(round(float(p["drive_periods"]) * spp))
    om_si = 2.0 * math.pi * float(p["frequency_hz"])
    eps_ac = float(p["eps_ac"])

    state = {"theta_w": theta_hot_mean}
    wall = make_wall(hd, lambda: state["theta_w"])
    e0_total = _fg_energy(f, g, c2)
    e_step_floor = 64.0 * _EPS * abs(e0_total)

    prog = ck_dir / f"drive_{label}.progress.npz"
    start = 0
    led_h: list[float] = []
    led_c: list[float] = []
    t_samp: list[float] = []
    thw_samp: list[float] = []
    qh_samp: list[float] = []
    qc_samp: list[float] = []
    contract_e_max = 0.0
    contract_m_max = 0.0
    mass_min, mass_max = float(np.sum(f)), float(np.sum(f))
    resume = _progress_load(prog, ident)
    if resume is not None:
        start = int(resume["step"])
        f, g = resume["f"], resume["g"]
        led_h, led_c = list(resume["led_h"]), list(resume["led_c"])
        t_samp, thw_samp = list(resume["t_s"]), list(resume["thw"])
        qh_samp, qc_samp = list(resume["qh"]), list(resume["qc"])
        contract_e_max = float(resume["c_e"])
        contract_m_max = float(resume["c_m"])
        mass_min, mass_max = float(resume["m_min"]), float(resume["m_max"])

    for i in range(start, n_drive):
        t = i / spp
        ramp = 0.5 * (1.0 - math.cos(math.pi * min(1.0, t))) if t < 1.0 else 1.0
        phase = om_si * (i * dt_s)
        state["theta_w"] = theta_hot_mean + eps_ac * th0 * ramp * math.cos(phase)
        e_before = _fg_energy(f, g, c2)
        m_before = float(np.sum(f))
        f, g, de_h, de_c = hd.strict_direct_step(f, g, face_wall=wall)
        e_after = _fg_energy(f, g, c2)
        m_after = float(np.sum(f))
        contract_e_max = max(contract_e_max,
                             abs(e_after - e_before - de_h - de_c)
                             / max(abs(de_h) + abs(de_c), e_step_floor))
        contract_m_max = max(contract_m_max,
                             abs(m_after - m_before) / mass_target)
        mass_min = min(mass_min, m_after)
        mass_max = max(mass_max, m_after)
        led_h.append(de_h)
        led_c.append(de_c)
        if i % sample_every == 0:
            if not np.all(np.isfinite(f)):
                return label, {"finite": False, "phase": "drive", "step": i}
            t_samp.append(i * dt_s)
            thw_samp.append(state["theta_w"])
            qh_samp.append(de_h)
            qc_samp.append(de_c)
        if (i + 1) % spp == 0 and (i + 1) < n_drive:
            _progress_save(prog, ident, i + 1, f, g,
                           {"led_h": led_h, "led_c": led_c, "t_s": t_samp,
                            "thw": thw_samp, "qh": qh_samp, "qc": qc_samp,
                            "c_e": contract_e_max, "c_m": contract_m_max,
                            "m_min": mass_min, "m_max": mass_max})

    if not np.all(np.isfinite(f)) or not np.all(np.isfinite(g)):
        return label, {"finite": False, "phase": "drive", "step": n_drive}
    m_last = recover_macro(f, g, D=d_int, S=s_int, lattice=hd.lattice)
    mass_drift = max(abs(mass_max / mass_target - 1.0),
                     abs(mass_min / mass_target - 1.0))
    meta = {
        "theta_dc": float(p["theta_dc"]), "eps_ac": eps_ac,
        "theta0": th0, "rho0": float(smeta["rho0"]),
        "cp_eff": 0.5 * (d_int + s_int) + 1.0,
        "nx": int(hd.nx), "steps_per_period": spp,
        "mass_target_total": mass_target,
        "mass_drift_rel_drive": float(mass_drift),
        "contract_energy_rel_max": float(contract_e_max),
        "contract_mass_rel_max": float(contract_m_max),
        "p_mean_lu_end": float(np.mean(m_last.p)),
        "ledger_entries": len(led_h),
        "settle_label": str(p["settle_label"]),
    }
    drive = {"t_s": np.array(t_samp), "theta_w": np.array(thw_samp),
             "q_hot_lu": np.array(qh_samp), "q_cold_lu": np.array(qc_samp)}
    tmp = ck.with_suffix(".tmp.npz")
    np.savez_compressed(tmp, ident=json.dumps(ident), meta=json.dumps(meta),
                        ledger_hot=np.array(led_h), ledger_cold=np.array(led_c),
                        **drive)
    os.replace(tmp, ck)
    if prog.exists():
        prog.unlink()
    return label, {**meta, "finite": True, "drive": drive,
                   "ledgers": {"ledger_hot": np.array(led_h),
                               "ledger_cold": np.array(led_c)}}


# ---------------------------------------------------------------------------
# QS family evaluation (per working point)
# ---------------------------------------------------------------------------

def qs_family_for_point(*, theta_dc: float, base_profile: np.ndarray,
                        rho_profile: np.ndarray, mass_per_area: float,
                        mass_per_area_cold: float, cold_base_profile: np.ndarray,
                        cold_rho_profile: np.ndarray, n_phys: int,
                        omega_lu: float, alpha_nom: float, rho_ref: float,
                        c_p: float, theta0: float, gamma: float,
                        k_tab: np.ndarray, a_tab: np.ndarray,
                        e_tab: np.ndarray, n_ref_ladder=N_REF_LADDER) -> dict[str, Any]:
    """QS-0 / QS-1 / QS-1k D_OP predictions on the reference ladder.

    Every tier divides its hot solve by ITS OWN cold solve built with the
    cold-point mass M_wet(0) (plan section 3.8); QS-1's cold uses the
    measured strict cold base mapped with the same frozen rules.
    """

    h_lu = float(n_phys)
    k0 = alpha_nom * rho_ref * c_p
    beta = G0_CONDUCTIVITY_EXPONENT
    theta_w = theta0 * (1.0 + theta_dc)
    rho_bar_hot = mass_per_area / h_lu
    rho_bar_cold = mass_per_area_cold / h_lu
    out: dict[str, Any] = {"n_ref_ladder": list(n_ref_ladder)}
    for tier in ("qs0", "qs1", "qs1k"):
        out[tier] = {}
    for n_ref in n_ref_ladder:
        # --- QS-0: uniform bulk coefficient at Tbar_w, own linear base ---
        th_b0, rho_b0 = steady_uniform_base(n_ref, theta_w=theta_w,
                                            theta_amb=theta0,
                                            rho_bar=rho_bar_hot)
        hot0 = robin_qs_matrix_bvp(n_ref=n_ref, h_lu=h_lu, omega_lu=omega_lu,
                                   k0=k0, theta0=theta0, beta=beta, c_p=c_p,
                                   theta_w=theta_w, theta_amb=theta0,
                                   theta_base=th_b0, rho_base=rho_b0,
                                   bulk_mode="uniform_at_tw")
        th_c0, rho_c0 = steady_uniform_base(n_ref, theta_w=theta0,
                                            theta_amb=theta0,
                                            rho_bar=rho_bar_cold)
        cold0 = robin_qs_matrix_bvp(n_ref=n_ref, h_lu=h_lu, omega_lu=omega_lu,
                                    k0=k0, theta0=theta0, beta=beta, c_p=c_p,
                                    theta_w=theta0, theta_amb=theta0,
                                    theta_base=th_c0, rho_base=rho_c0,
                                    bulk_mode="uniform_at_tw")
        out["qs0"][n_ref] = complex(hot0["Y"]) / complex(cold0["Y"])

        # --- QS-1: measured strict base, frozen mapping (plan section 4) ---
        th_b1, rho_b1 = map_strict_base_to_ref(base_profile, rho_profile,
                                               n_ref, theta_w=theta_w,
                                               theta_amb=theta0,
                                               mass_per_area=mass_per_area,
                                               h_lu=h_lu)
        hot1 = robin_qs_matrix_bvp(n_ref=n_ref, h_lu=h_lu, omega_lu=omega_lu,
                                   k0=k0, theta0=theta0, beta=beta, c_p=c_p,
                                   theta_w=theta_w, theta_amb=theta0,
                                   theta_base=th_b1, rho_base=rho_b1,
                                   bulk_mode="powerlaw_local")
        th_c1, rho_c1 = map_strict_base_to_ref(cold_base_profile,
                                               cold_rho_profile, n_ref,
                                               theta_w=theta0, theta_amb=theta0,
                                               mass_per_area=mass_per_area_cold,
                                               h_lu=h_lu)
        cold1 = robin_qs_matrix_bvp(n_ref=n_ref, h_lu=h_lu, omega_lu=omega_lu,
                                    k0=k0, theta0=theta0, beta=beta, c_p=c_p,
                                    theta_w=theta0, theta_amb=theta0,
                                    theta_base=th_c1, rho_base=rho_c1,
                                    bulk_mode="powerlaw_local")
        out["qs1"][n_ref] = complex(hot1["Y"]) / complex(cold1["Y"])

        # --- QS-1k: frozen G0 finite-k operator + elevation, same closure ---
        dy = h_lu / n_ref
        th1b_hot = theta_w + (theta0 - theta_w) * (0.5 / n_ref)  # linear base
        for tag, th_dc_i, rho_bar_i, th_w_i, th1b_i in (
                ("hot", theta_dc, rho_bar_hot, theta_w, th1b_hot),
                ("cold", 0.0, rho_bar_cold, theta0, theta0)):
            a_of = g0_alpha_of_k(k_tab, a_tab, e_tab, theta_dc=th_dc_i,
                                 elevation=1.0)
            dens = rho_ref / rho_bar_i
            sol = robin_qs_spectral_extension(
                n_ref=n_ref, h_lu=h_lu, omega_lu=omega_lu, gamma=gamma,
                alpha_of_k=lambda k, _a=a_of, _d=dens: _a(k) * _d,
                alpha_face_hot=alpha_nom * (th_w_i / theta0) ** beta * dens,
                alpha_face_cold=alpha_nom * dens, beta=beta,
                theta_w=th_w_i, theta_amb=theta0, theta_1_base=th1b_i,
                rho_bar_over_ref=rho_bar_i / rho_ref)
            out.setdefault("_qs1k_parts", {}).setdefault(n_ref, {})[tag] = \
                complex(sol["Y"])
        parts = out["_qs1k_parts"][n_ref]
        out["qs1k"][n_ref] = parts["hot"] / parts["cold"]
    fine = n_ref_ladder[-1]
    mid = n_ref_ladder[-2]
    out["d_qs0_pct"] = (abs(out["qs0"][fine]) - 1.0) * 100.0
    out["d_qs1_pct"] = (abs(out["qs1"][fine]) - 1.0) * 100.0
    out["d_qs1k_pct"] = (abs(out["qs1k"][fine]) - 1.0) * 100.0
    out["qs1_phase_deg"] = math.degrees(math.atan2(out["qs1"][fine].imag,
                                                   out["qs1"][fine].real))
    out["qs1k_phase_deg"] = math.degrees(math.atan2(out["qs1k"][fine].imag,
                                                    out["qs1k"][fine].real))
    out["u_qs_pp"] = abs(abs(out["qs1"][fine]) - abs(out["qs1"][mid])) * 100.0
    out["u_qs_phase_deg"] = abs(_wrap_deg(
        math.degrees(math.atan2(out["qs1"][fine].imag, out["qs1"][fine].real)
                     - math.atan2(out["qs1"][mid].imag, out["qs1"][mid].real))))
    out["qs1k_status"] = "COMPUTED"
    return out


# ---------------------------------------------------------------------------
# run assembly
# ---------------------------------------------------------------------------

def load_reference_pack(pack_json: Path) -> dict[str, Any]:
    pack = json.loads(pack_json.read_text(encoding="utf-8"))
    sha_file = pack_json.with_suffix(".sha256")
    if sha_file.exists():
        expected = sha_file.read_text(encoding="utf-8").split()[0]
        actual = _sha256(pack_json)
        if actual != expected:
            raise RuntimeError(
                f"reference pack digest mismatch: {actual} != {expected}")
        pack["_pack_sha256_verified"] = actual
    npz_rel = pack.get("series_npz")
    if npz_rel:
        npz_path = pack_json.parent / npz_rel
        actual = _sha256(npz_path)
        if actual != pack["sha256"]["series_npz"]:
            raise RuntimeError("reference pack series npz digest mismatch")
    return pack


def run_a2a_strict_b(config_path: str | Path, output_root: str | Path | None = None,
                     *, smoke: bool = False, workers: int | None = None,
                     stage: str = "all",
                     ckpt_dir: str | Path | None = None) -> dict[str, Any]:
    import h5py
    import yaml

    t0 = datetime.now(timezone.utc)
    cfg_all = load_config(Path(config_path))
    proto = cfg_all["a2a_strict_b_smoke" if smoke else "a2a_strict_b"]
    gas_cfg = load_config(REPO_ROOT / str(cfg_all["inheritance"]["gas_config"]))

    log_lines: list[str] = []

    def log(msg: str) -> None:
        line = f"A2ASB {msg}"
        print(line, flush=True)
        log_lines.append(line)

    f_hz = float(proto["frequency_Hz"])
    n_phys = int(proto["n_phys"])
    nx = int(proto["nx"])
    spp_cfg = int(proto["samples_per_period"])
    theta_grid = [float(t) for t in proto["theta_dc_grid"]]
    hot_thetas = [t for t in theta_grid if t > 0.0]
    eps_hot = [float(e) for e in proto["eps_ac_hot"]]
    eps_cold = float(proto["eps_ac_cold"])
    settle_p = float(proto["settle_periods"])
    drive_p = float(proto["drive_periods"])
    n_ref_ladder = tuple(int(n) for n in proto.get("n_ref_ladder", N_REF_LADDER))
    win_main = tuple(float(v) for v in proto.get("fit_window_main",
                                                 FIT_WINDOW_MAIN))
    win_alt = tuple(float(v) for v in proto.get("fit_window_alt",
                                                FIT_WINDOW_ALT))
    if not smoke and (win_main != FIT_WINDOW_MAIN or win_alt != FIT_WINDOW_ALT
                      or n_ref_ladder != N_REF_LADDER):
        raise RuntimeError("auth protocol must keep the frozen fit windows "
                           "and N_ref ladder (plan section 4)")

    mode = "smoke" if smoke else "auth"
    commit = _git_commit()
    ck_root = (Path(ckpt_dir) if ckpt_dir else
               REPO_ROOT / "results" / "phase5" / CASE_FAMILY
               / f"checkpoints_{mode}_{commit}")
    ck_root.mkdir(parents=True, exist_ok=True)
    log(f"mode={mode} commit={commit} ckpt={ck_root}")

    # ---- reference pack (plan section 3.1) ----
    pack: dict[str, Any] | None = None
    pack_path = REPO_ROOT / str(proto["reference_pack"])
    if pack_path.exists():
        pack = load_reference_pack(pack_path)
        log(f"reference pack loaded: {pack_path.name} "
            f"sha_ok={'_pack_sha256_verified' in pack}")
    elif not smoke:
        raise RuntimeError(f"reference pack missing: {pack_path} "
                           "(auth runs require the pre-registered pack)")
    else:
        log("SMOKE without reference pack: equal-mass fallback targets")

    def wet_point(theta: float) -> dict[str, Any] | None:
        if pack is None:
            return None
        return pack["points"][f"{theta:g}"]

    def _mass_of(theta: float):
        # smoke geometry (N != 48) cannot carry the wet per-column mass
        # targets; it rehearses mechanics on the equal-mass fallback.
        if smoke:
            return None
        wp = wet_point(theta)
        return None if wp is None else float(wp["m_wet_per_area"])

    # ---- stage: settles (one per Theta, pooled, checkpointed) ----
    common = dict(gas_cfg=gas_cfg, n_phys=n_phys, nx=nx, frequency_hz=f_hz,
                  samples_per_period=spp_cfg, ckpt_dir=str(ck_root))
    settle_payloads = []
    for th in theta_grid:
        settle_payloads.append({**common, "label": f"th{th:g}",
                                "theta_dc": th,
                                "settle_periods": settle_p,
                                "mass_per_area": _mass_of(th)})
    n_workers = workers if workers is not None else max(1, (os.cpu_count() or 4) - 2)
    settles: dict[str, Any] = {}
    if stage in ("all", "settle", "drive", "post"):
        settles = execute_cases(settle_payloads, n_workers, log,
                                worker=_sb_a2a_settle_worker)
        for lb in sorted(settles):
            r = settles[lb]
            if r.get("finite"):
                log(f"[settle {lb}] stat={r['stationarity_per_period']:.2e} "
                    f"closure={r['dc_closure_rel']:.2e} "
                    f"m_init={r['init_mass_rel']:.2e} "
                    f"drift={r['mass_drift_rel_settle']:.2e} "
                    f"contract={r['contract_energy_rel_max']:.2e}")
            else:
                log(f"[settle {lb}] DEAD: {r}")
    if stage == "settle":
        return {"verdict": "SETTLE_STAGE_DONE", "settles": {
            lb: {k: v for k, v in r.items() if k != "base_profile"}
            for lb, r in settles.items()}}

    # ---- stage: drives (cold anchor + hot points, pooled, checkpointed) ----
    drive_payloads = [{**common, "label": f"cold_eps{eps_cold:g}",
                       "theta_dc": 0.0, "eps_ac": eps_cold,
                       "drive_periods": drive_p, "settle_label": "th0",
                       "mass_per_area": _mass_of(0.0)}]
    for th in hot_thetas:
        for eps in eps_hot:
            drive_payloads.append({**common, "label": f"th{th:g}_eps{eps:g}",
                                   "theta_dc": th, "eps_ac": eps,
                                   "drive_periods": drive_p,
                                   "settle_label": f"th{th:g}",
                                   "mass_per_area": _mass_of(th)})
    drives: dict[str, Any] = {}
    if stage in ("all", "drive", "post"):
        ok_settles = all(settles.get(f"th{th:g}", {}).get("finite")
                         for th in theta_grid)
        if not ok_settles:
            log("settle stage incomplete -> drives skipped")
        else:
            drives = execute_cases(drive_payloads, n_workers, log,
                                   worker=_sb_a2a_drive_worker)
            for lb in sorted(drives):
                r = drives[lb]
                if r.get("finite"):
                    log(f"[drive {lb}] drift={r['mass_drift_rel_drive']:.2e} "
                        f"contract={r['contract_energy_rel_max']:.2e}")
                else:
                    log(f"[drive {lb}] DEAD: {r}")
    if stage == "drive":
        return {"verdict": "DRIVE_STAGE_DONE"}

    # ---- post: fits / QS family / budgets / candidate labels ----
    probe = StrictBHalfDomain(gas_cfg, n_phys=max(8, min(n_phys, 12)), nx=4)
    alpha_nom = float(probe.mapping.alpha_lu)
    rho_ref = float(probe.mapping.lattice.rho_ref_lu)
    theta0 = float(probe.mapping.theta_ref_lu)
    d_int = int(probe.mapping.lattice.D)
    s_int = int(probe.mapping.lattice.S)
    c_p = 0.5 * (d_int + s_int) + 1.0
    gamma = float(gas_cfg["physical"]["gamma"])
    spp = _steps_per_period(probe, f_hz)
    om_lu = 2.0 * math.pi / spp
    g0_rows = load_g0_alpha_rows(REPO_ROOT / G0_TABLE_CSV)
    k_tab = np.array([r[0] for r in g0_rows])
    a_tab = np.array([r[1] for r in g0_rows])
    exps = fit_exponents(REPO_ROOT / G0_TABLE_CSV)
    e_tab = np.array([e for _, e in exps])
    if not np.allclose(np.array([k for k, _ in exps]), k_tab, rtol=1e-12):
        raise RuntimeError("G0 exponent/alpha k-grids differ")

    def fits_of(label: str) -> dict[str, Any] | None:
        r = drives.get(label)
        if not (r and r.get("finite")):
            return None
        kw = dict(rho0=r["rho0"], cp_eff=r["cp_eff"], nx=r["nx"])
        return {"main": fit_admittance_window(r["drive"], f_hz, win_main, **kw),
                "alt": fit_admittance_window(r["drive"], f_hz, win_alt, **kw)}

    cold_label = f"cold_eps{eps_cold:g}"
    cold_fit = fits_of(cold_label)
    y_cold = cold_fit["main"]["Y_face_theta_units"] if cold_fit else None
    y_cold_alt = cold_fit["alt"]["Y_face_theta_units"] if cold_fit else None

    cold_anchor_row: dict[str, Any] = {"passed": False, "missing": True}
    if y_cold is not None:
        ratio = y_cold / Y0_WET_COLD
        amp_err = abs(abs(ratio) - 1.0)
        ph_err = abs(_wrap_deg(math.degrees(math.atan2(ratio.imag, ratio.real))))
        cold_anchor_row = {"Y_cold": _cplx(y_cold),
                           "Y0_wet_anchor": _cplx(Y0_WET_COLD),
                           "amp_rel_err": float(amp_err),
                           "phase_deg_err": float(ph_err),
                           "gates": [GATE_COLD_AMP_REL, GATE_COLD_PHASE_DEG],
                           "passed": bool(amp_err <= GATE_COLD_AMP_REL
                                          and ph_err <= GATE_COLD_PHASE_DEG)}
        log(f"cold anchor: amp {amp_err:+.4f} phase {ph_err:+.3f} deg "
            f"pass={cold_anchor_row['passed']}")

    # per-point evaluation
    points: dict[str, Any] = {}
    cold_settle = settles.get("th0", {})
    for th in hot_thetas:
        srow = settles.get(f"th{th:g}", {})
        wp = wet_point(th)
        pt: dict[str, Any] = {"theta_dc": th}
        fit_hi = fits_of(f"th{th:g}_eps{max(eps_hot):g}")
        fit_lo = fits_of(f"th{th:g}_eps{min(eps_hot):g}")
        if not (fit_hi and fit_lo and y_cold is not None and srow.get("finite")):
            pt["status"] = "CASE_DEAD"
            points[f"{th:g}"] = pt
            continue
        y_hi = fit_hi["main"]["Y_face_theta_units"]
        y_lo = fit_lo["main"]["Y_face_theta_units"]
        lin = abs(y_hi / y_lo - 1.0)
        d_main = y_hi / y_cold
        d_alt = fit_hi["alt"]["Y_face_theta_units"] / y_cold_alt
        d_lo = y_lo / y_cold
        pt["Y_hot"] = _cplx(y_hi)
        pt["Y_hot_lo"] = _cplx(y_lo)
        pt["linearity_abs"] = float(lin)
        pt["linearity_passed"] = bool(lin <= GATE_LINEARITY)
        pt["D_OP"] = _cplx(d_main)
        pt["d_op_pct"] = (abs(d_main) - 1.0) * 100.0
        pt["d_op_alt_pct"] = (abs(d_alt) - 1.0) * 100.0
        pt["d_op_lo_pct"] = (abs(d_lo) - 1.0) * 100.0
        pt["phase_deg"] = math.degrees(math.atan2(d_main.imag, d_main.real))
        pt["u_d_pp"] = max(abs(pt["d_op_alt_pct"] - pt["d_op_pct"]),
                           abs(pt["d_op_lo_pct"] - pt["d_op_pct"]))
        pt["u_phase_win_eps_deg"] = max(
            abs(_wrap_deg(math.degrees(math.atan2(d_alt.imag, d_alt.real))
                          - pt["phase_deg"])),
            abs(_wrap_deg(math.degrees(math.atan2(d_lo.imag, d_lo.real))
                          - pt["phase_deg"])))
        pt["h2_q_rel"] = fit_hi["main"]["h2_q_rel"]
        # QS family on the strict measured base
        if cold_settle.get("finite"):
            m_hot = srow["mass_per_area"]
            m_cold = cold_settle["mass_per_area"]
            qs = qs_family_for_point(
                theta_dc=th,
                base_profile=np.array(srow["base_profile"]),
                rho_profile=np.array(srow["rho_profile"]),
                mass_per_area=m_hot, mass_per_area_cold=m_cold,
                cold_base_profile=np.array(cold_settle["base_profile"]),
                cold_rho_profile=np.array(cold_settle["rho_profile"]),
                n_phys=n_phys, omega_lu=om_lu, alpha_nom=alpha_nom,
                rho_ref=rho_ref, c_p=c_p, theta0=theta0, gamma=gamma,
                k_tab=k_tab, a_tab=a_tab, e_tab=e_tab,
                n_ref_ladder=n_ref_ladder)
            fine = n_ref_ladder[-1]
            pt["qs"] = {k: qs[k] for k in ("d_qs0_pct", "d_qs1_pct",
                                           "d_qs1k_pct", "qs1_phase_deg",
                                           "qs1k_phase_deg", "u_qs_pp",
                                           "u_qs_phase_deg", "qs1k_status")}
            pt["qs_ladder"] = {t: {str(n): _cplx(qs[t][n]) for n in n_ref_ladder}
                               for t in ("qs0", "qs1", "qs1k")}
            qs1 = qs["qs1"][fine]
            pt["r_dyn_pp"] = pt["d_op_pct"] - qs["d_qs1_pct"]
            pt["phase_resid_deg"] = _wrap_deg(
                pt["phase_deg"] - math.degrees(math.atan2(qs1.imag, qs1.real)))
            pt["u_r_pp"] = math.hypot(pt["u_d_pp"], qs["u_qs_pp"])
            pt["u_phi_deg"] = math.hypot(pt["u_phase_win_eps_deg"],
                                         qs["u_qs_phase_deg"])
        # wet comparison (plan section 4)
        if wp is not None:
            pt["wet"] = {"d_op_pct": wp["d_op_pct"],
                         "r_dyn_wet_pp": wp["r_dyn_wet_pp"],
                         "u_d_wet_pp": wp["u_d_wet_pp"],
                         "run": wp["run_id"]}
            pt["uplift_pp"] = pt["d_op_pct"] - wp["d_op_pct"]
            pt["u_delta_pp"] = math.hypot(pt["u_d_pp"], wp["u_d_wet_pp"])
            u_r_wet = max(U_WET_FLOOR_PP, wp["u_d_wet_pp"])
            r_wet = abs(wp["r_dyn_wet_pp"])
            denom = r_wet - 2.0 * u_r_wet
            if "r_dyn_pp" in pt and denom > 0.0:
                pt["c_r"] = 1.0 - abs(pt["r_dyn_pp"]) / r_wet
                pt["c_r_lower"] = 1.0 - (abs(pt["r_dyn_pp"])
                                         + 2.0 * pt["u_r_pp"]) / denom
            else:
                pt["c_r_lower_invalid"] = True
        pt["legality"] = {
            "finite": True,
            "contract": max(srow["contract_energy_rel_max"],
                            drives[f"th{th:g}_eps{max(eps_hot):g}"]
                            ["contract_energy_rel_max"]) <= GATE_CONTRACT_REL,
            "init_mass": srow["init_mass_rel"] <= GATE_MASS_INIT_REL,
            "mass_drift": max(srow["mass_drift_rel_settle"],
                              drives[f"th{th:g}_eps{max(eps_hot):g}"]
                              ["mass_drift_rel_drive"],
                              drives[f"th{th:g}_eps{min(eps_hot):g}"]
                              ["mass_drift_rel_drive"]) <= GATE_MASS_DRIFT_REL,
            "stationarity": srow["stationarity_per_period"] <= GATE_STATIONARITY,
            "dc_closure": srow["dc_closure_rel"] <= GATE_DC_CLOSURE,
        }
        if wp is not None:
            pmean_rel = abs(srow["p_mean_lu"] / wp["p_mean_wet_lu"] - 1.0)
            pt["pmean_rel_wet"] = float(pmean_rel)
            pt["legality"]["pmean_vs_wet"] = pmean_rel <= GATE_PMEAN_REL_WET
        pt["legal"] = bool(all(pt["legality"].values()))
        points[f"{th:g}"] = pt
        log(f"th={th:g}: d_op {pt['d_op_pct']:+.4f}% "
            f"qs1 {pt.get('qs', {}).get('d_qs1_pct', float('nan')):+.3f}% "
            f"r_dyn {pt.get('r_dyn_pp', float('nan')):+.3f} pp "
            f"lin {lin:.2e} legal={pt['legal']}")

    # cold-point legality
    cold_ok = bool(cold_settle.get("finite")) and cold_fit is not None
    cold_legality = {}
    if cold_ok:
        cr = drives.get(cold_label, {})
        cold_legality = {
            "contract": max(cold_settle["contract_energy_rel_max"],
                            cr.get("contract_energy_rel_max", 1.0))
            <= GATE_CONTRACT_REL,
            "init_mass": cold_settle["init_mass_rel"] <= GATE_MASS_INIT_REL,
            "mass_drift": max(cold_settle["mass_drift_rel_settle"],
                              cr.get("mass_drift_rel_drive", 1.0))
            <= GATE_MASS_DRIFT_REL,
            "stationarity": cold_settle["stationarity_per_period"]
            <= GATE_STATIONARITY,
            "dc_closure": cold_settle["dc_closure_rel"] <= GATE_DC_CLOSURE,
            "cold_anchor": bool(cold_anchor_row.get("passed")),
        }
        if pack is not None:
            wp0 = wet_point(0.0)
            pmean_rel = abs(cold_settle["p_mean_lu"] / wp0["p_mean_wet_lu"] - 1.0)
            cold_legality["pmean_vs_wet"] = pmean_rel <= GATE_PMEAN_REL_WET
            cold_settle["pmean_rel_wet"] = float(pmean_rel)
    cold_legal = cold_ok and all(cold_legality.values())

    # ---- candidate verdict (mechanical application of plan section 4) ----
    verdict_candidate = "UNINTERPRETABLE_CANDIDATE"
    hot_rows = [points.get(f"{t:g}", {}) for t in hot_thetas]
    all_present = (pack is not None and cold_legal
                   and all(r.get("legal") and r.get("linearity_passed")
                           and "uplift_pp" in r and "r_dyn_pp" in r
                           for r in hot_rows))
    if all_present:
        uplift_ok = all(r["uplift_pp"] > max(UPLIFT_FLOOR_PP,
                                             2.0 * r["u_delta_pp"])
                        for r in hot_rows)
        anchor_pts = [points.get(f"{t:g}", {}) for t in hot_thetas
                      if abs(t - 0.05) < 1e-12 or abs(t - 0.10) < 1e-12]
        cr_ok = all(("c_r_lower" in r and r["c_r_lower"] >= CR_LOWER_MIN)
                    for r in anchor_pts)
        resid_ok = all(abs(r["r_dyn_pp"]) + 2.0 * r["u_r_pp"] <= RESID_CAP_PP
                       for r in anchor_pts)
        phase_ok = all(abs(r["phase_resid_deg"]) + 2.0 * r["u_phi_deg"]
                       <= PHASE_CAP_DEG for r in anchor_pts)
        if uplift_ok and cr_ok and resid_ok and phase_ok:
            verdict_candidate = "EFFECTIVE_RESOLUTION_CANDIDATE"
        elif uplift_ok and cr_ok:
            verdict_candidate = "EFFECTIVE_MITIGATION_CANDIDATE"
        else:
            verdict_candidate = "NOT_RESOLVED_CANDIDATE"
    if smoke:
        verdict_candidate = "SMOKE_" + verdict_candidate
    log(f"verdict_candidate={verdict_candidate} (judgement={JUDGEMENT}, "
        f"g0_scope={G0_SCOPE})")

    # ---- files ----
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = (Path(output_root) if output_root
                else REPO_ROOT / "results" / "phase5" / CASE_FAMILY)
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    rows_csv: list[dict[str, Any]] = []

    def _row(theta: float, eps: float, y: complex | None, drift: float,
             pt: dict | None, status: str, h2: float | None) -> dict[str, Any]:
        srow = settles.get(f"th{theta:g}", {})
        qs = (pt or {}).get("qs", {})
        return {
            "theta_dc": theta, "epsilon_ac": eps,
            "mass_target": srow.get("mass_per_area", float("nan")),
            "mass_drift_rel": drift,
            "pmean_rel_wet": (pt or {}).get("pmean_rel_wet",
                                            (srow or {}).get("pmean_rel_wet",
                                                             float("nan"))),
            "Y_re": (y.real if y is not None else float("nan")),
            "Y_im": (y.imag if y is not None else float("nan")),
            "d_op_pct": (pt or {}).get("d_op_pct", float("nan")),
            "phase_deg": (pt or {}).get("phase_deg", float("nan")),
            "qs0_pct": qs.get("d_qs0_pct", float("nan")),
            "qs1_pct": qs.get("d_qs1_pct", float("nan")),
            "qs1_phase_deg": qs.get("qs1_phase_deg", float("nan")),
            "qs1k_pct": qs.get("d_qs1k_pct", float("nan")),
            "r_dyn_pp": (pt or {}).get("r_dyn_pp", float("nan")),
            "phase_resid_deg": (pt or {}).get("phase_resid_deg", float("nan")),
            "cr_lower": (pt or {}).get("c_r_lower", float("nan")),
            "h2_q_rel": (h2 if h2 is not None else float("nan")),
            "u_d_pp": (pt or {}).get("u_d_pp", float("nan")),
            "u_qs_pp": qs.get("u_qs_pp", float("nan")),
            "g0_scope": G0_SCOPE, "status": status,
        }

    if cold_fit is not None:
        rows_csv.append(_row(
            0.0, eps_cold, y_cold,
            max(cold_settle.get("mass_drift_rel_settle", float("nan")),
                drives.get(cold_label, {}).get("mass_drift_rel_drive",
                                               float("nan"))),
            None, "cold_anchor;" + ("legal" if cold_legal else "ILLEGAL"),
            cold_fit["main"]["h2_q_rel"]))
    for th in hot_thetas:
        pt = points.get(f"{th:g}", {})
        for eps in sorted(eps_hot):
            dr = drives.get(f"th{th:g}_eps{eps:g}", {})
            fit = fits_of(f"th{th:g}_eps{eps:g}")
            y = fit["main"]["Y_face_theta_units"] if fit else None
            drift = max(settles.get(f"th{th:g}", {}).get(
                "mass_drift_rel_settle", float("nan")),
                dr.get("mass_drift_rel_drive", float("nan")))
            tag = "judgement_pair" if eps == max(eps_hot) else "linearity_audit"
            status = f"{tag};" + ("legal" if pt.get("legal") else "ILLEGAL")
            rows_csv.append(_row(th, eps, y, drift, pt, status,
                                 fit["main"]["h2_q_rel"] if fit else None))
    with (out_dir / "a2a_strict_b.csv").open("w", newline="",
                                             encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for row in rows_csv:
            w.writerow(row)

    with h5py.File(out_dir / "signals.h5", "w") as h5:
        for th in theta_grid:
            srow = settles.get(f"th{th:g}")
            if srow and srow.get("finite"):
                grp = h5.create_group(f"settles/th{th:g}")
                grp.create_dataset("base_profile",
                                   data=np.array(srow["base_profile"]))
                grp.create_dataset("rho_profile",
                                   data=np.array(srow["rho_profile"]))
        for lb, r in drives.items():
            if not (r and r.get("finite")):
                continue
            grp = h5.create_group(f"cases/{lb}")
            for key in ("t_s", "theta_w", "q_hot_lu", "q_cold_lu"):
                grp.create_dataset(key, data=np.asarray(r["drive"][key]))
            for key, arr in r.get("ledgers", {}).items():
                grp.create_dataset(key, data=np.asarray(arr))

    digest = hashlib.sha256(json.dumps(
        {"points": {k: {kk: vv for kk, vv in v.items()
                        if kk not in ("qs_ladder",)}
                    for k, v in points.items()},
         "cold_anchor": cold_anchor_row}, sort_keys=True,
        default=str).encode()).hexdigest()[:12]
    summary = {
        "gate": UNIT, "run_id": run_id,
        "verdict": "COMPLETED" if drives else "INCOMPLETE",
        "verdict_candidate": verdict_candidate,
        "judgement": JUDGEMENT, "g0_scope": G0_SCOPE,
        "smoke_mode": bool(smoke),
        "branch": BRANCH,
        "protocol": {"frequency_Hz": f_hz, "n_phys": n_phys, "nx": nx,
                     "samples_per_period": spp_cfg,
                     "theta_dc_grid": theta_grid,
                     "eps_ac_hot": eps_hot, "eps_ac_cold": eps_cold,
                     "settle_periods": settle_p, "drive_periods": drive_p,
                     "fit_window_main": list(win_main),
                     "fit_window_alt": list(win_alt),
                     "n_ref_ladder": list(n_ref_ladder)},
        "frozen_lines": {
            "contract_rel": GATE_CONTRACT_REL,
            "mass_init_rel": GATE_MASS_INIT_REL,
            "mass_drift_rel": GATE_MASS_DRIFT_REL,
            "pmean_rel_wet": GATE_PMEAN_REL_WET,
            "stationarity": GATE_STATIONARITY,
            "dc_closure": GATE_DC_CLOSURE,
            "linearity": GATE_LINEARITY,
            "cold_anchor": [GATE_COLD_AMP_REL, GATE_COLD_PHASE_DEG],
            "Y0_wet_cold": _cplx(Y0_WET_COLD),
            "u_wet_floor_pp": U_WET_FLOOR_PP,
            "uplift_floor_pp": UPLIFT_FLOOR_PP,
            "cr_lower_min": CR_LOWER_MIN,
            "resid_cap_pp": RESID_CAP_PP, "phase_cap_deg": PHASE_CAP_DEG},
        "reference_pack": (None if pack is None else
                           {"path": str(pack_path.relative_to(REPO_ROOT)),
                            "sha256_verified": pack.get("_pack_sha256_verified")}),
        "cold_anchor": cold_anchor_row,
        "cold_legality": cold_legality,
        "settles": {lb: {k: v for k, v in r.items()
                         if k not in ("base_profile", "rho_profile")}
                    for lb, r in settles.items()},
        "points": points,
        "physics_core_digest": digest,
        "code_commit": commit,
        "wall_clock_min": (datetime.now(timezone.utc) - t0).total_seconds() / 60.0,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=1, default=float), encoding="utf-8")
    (out_dir / "config_resolved.yaml").write_text(
        yaml.safe_dump(cfg_all, allow_unicode=True, sort_keys=False),
        encoding="utf-8")
    (out_dir / "provenance.json").write_text(json.dumps(
        {"run_id": run_id, "family": CASE_FAMILY, "argv": sys.argv,
         "machine": os.environ.get("COMPUTERNAME", "unknown"),
         "python": sys.version, "workers": n_workers,
         "code_commit": commit, "ckpt_dir": str(ck_root),
         "started_utc": t0.isoformat(),
         "finished_utc": datetime.now(timezone.utc).isoformat()},
        indent=1), encoding="utf-8")
    (out_dir / "run_report.md").write_text("\n".join(
        [f"# {UNIT} run {run_id}", "",
         f"verdict_candidate: **{verdict_candidate}** "
         f"(judgement: {JUDGEMENT}; g0_scope: {G0_SCOPE})", "", "```text"]
        + log_lines + ["```", ""]), encoding="utf-8")
    log(f"outputs -> {out_dir}")
    return {"verdict": summary["verdict"],
            "verdict_candidate": verdict_candidate,
            "out_dir": str(out_dir), "summary": summary}


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase_5 A2a-STRICT_B runner")
    ap.add_argument("--config", default=str(
        REPO_ROOT / "configs" / "phase5" / "a2a_strict_b"
        / "a2a_strict_b_10k_dx2p6.yaml"))
    ap.add_argument("--output-root", default=None)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--stage", choices=("all", "settle", "drive", "post"),
                    default="all")
    ap.add_argument("--ckpt-dir", default=None)
    args = ap.parse_args()
    result = run_a2a_strict_b(args.config, args.output_root, smoke=args.smoke,
                              workers=args.workers, stage=args.stage,
                              ckpt_dir=args.ckpt_dir)
    return 0 if result["verdict"] in ("COMPLETED", "SETTLE_STAGE_DONE",
                                      "DRIVE_STAGE_DONE") else 1


if __name__ == "__main__":
    sys.exit(main())
