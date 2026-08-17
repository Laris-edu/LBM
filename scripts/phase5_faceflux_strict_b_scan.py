"""D1 strict candidate-B measurement — half-domain mirror face-flux wall (D0-7).

DESIGN AUTHORITY: docs/Phase_5/strict_faceflux_candidate_b_design_v1.0.md
(EXPERIMENT_PLAN_v1.0, frozen 2026-08-17; status chain
STRICT_B_DESIGN_CONDITIONAL -> this implementation).  The band row is
DELETED: a single physical gas half-domain with per-stage zero-volume
mirror extension closes all D2Q37 deep links and global spectral operators
(core/strict_b_half_domain.py); hot/cold face heat is written ONLY into
each side's first gas control volume through the |c.n|=1 incoming-g
minimum-norm source (boundary/wall_face_flux_strict.py).

VERIFICATION MATRIX (design section 5) — layer-to-stage map:
  layer 1 single-step topology  pytest test_phase5_faceflux_strict_b.py
                                + stage "structural" runtime asserts
                                (column replication <=1e-12, seam off,
                                acoustic identity, coverage 15/8/3)
  layer 2 local conservation    pytest (same file)
  layer 3 wall position + soak  stage "slab" (N={16,32,64} manufactured,
                                finest <=1e-3 monotone) + stage "soak"
                                (uniform & perturbed 64 periods, hot-DC
                                16 periods with the A_late envelope row)
  layer 4 cold non-degeneracy   stage "cold": STRICT_B_CONST_G cold complex
                                admittance vs the FROZEN PROD cold anchor
                                (|ratio|-1 <= 10%, |phase| <= 5 deg)
  layer 5 G0 admission          stage "admission": independent CE/continuum
                                references (reference/strict_b_face_admission
                                .py), +-gradients, Theta={0,0.05,0.10},
                                N={16,32,64}; steady/G/derivative <=5%
                                finest + monotone; complex admittance
                                <=10%/5 deg; never self-certified by the
                                boundary's own q identity
  layer 6 micro JVP             pytest (channels, B_shape=0, B_ref)
  layer 7 full-step JVP         stage "jvp": h={1e-4,5e-5,2.5e-5};
                                odd <=1e-6, even ratios in [3,5] (guarded),
                                chain-vs-direct & h-spread <=1e-5
  layer 8 production regression stage "regression": full pytest suite,
                                0 failures; default-step golden fixture
                                bitwise (in the pytest file)
  layer 9 hot points            stage "hot": 10 kHz, N=48, nx=8,
                                Theta={0,0.05,0.10}, windows
                                settle/drive/sample/skip = 5/4/64/2 periods

FROZEN JUDGEMENT LINES (constants below, registered before any strict hot
number; the three machine details of design section 5 are frozen here):
  eps_g ladder {±1e-4,±5e-5,±2.5e-5} fixed-centre odd pairing; even-ratio
  guard even_norm > 1e-12*max(odd_norm); hot-DC A_late = 0.5||z_n-z_{n-1}||_inf
  <= max(1e-10, 1.5*A_early) on the last four same-phase period endpoints.
  Hot-point judgement h = 5e-5 (JAB/wallfix/buffer lineage).
  PROD/TAN frozen anchors d_OP = -2.83451296/-5.31705943 pp (0.2 pp gate);
  NSF g0 reference +1.1817/+2.3445 pp; PROD cold complex anchor from the
  wallfix auth checkpoint (value frozen below).

CLASSIFICATION (design section 6, STRICT_B_ prefix; CONST_G rows carry the
_CONTROL suffix and never judge D1 section 13.2):
  m = (d_B - d_PROD)/(d_NSF - d_PROD) per hot point;
  one positive & one non-positive        -> MIXED
  both positive, |d_B - NSF| <= 1 pp both -> RESOLVED
  both positive, outside the band         -> SIGN_FLIPPED
  both non-positive, m >= 0.25 both       -> PARTIAL
  anything else                           -> NULL
Only after ALL eight previous layers pass may STRICT_B_SCIENTIFICALLY_
VALIDATED be stamped and m computed.  Failure labels: TOPOLOGY_INVALID
(layer 1/structural), STRICT_B_COLD_ILLEGAL (layer 4; no interpretable hot
point may run), STRICT_B_BASESTATE_MISMATCH (ensemble gates),
MOMENT_SYSTEM_INVALID / POST_SOURCE_STATE_INVALID (raised by the wall).
Even a G0 NULL binds only THIS topology and micro closure — never the whole
face-flux boundary family (design section 6.5).

COMPARISON ENSEMBLE (design section 3): closed equal-mass column
M/A = rho_ref*H_s, same H_s and wall DC temperatures as PROD; hot points
never re-tune mass to match pressure.  Cold mass/pressure <=1e-12; hot
mass <=1e-10, measured Theta_DC <=1%, mean pressure <=1% else
STRICT_B_BASESTATE_MISMATCH.  Single-side energy admittance Y = q_hat_s /
theta_hat_w / (rho_ref c_p); the factor 2 exists only in final two-side
presentation rows, never inside gates (d_OP ratios cancel the bridge).

PROD anchor reuses the wallfix arbitration workers and their authoritative
checkpoints verbatim (identity-matched resume; zero new PROD compute).

DIAGNOSTIC ONLY (D0-7): verdict vocabulary COMPLETED / LEGALITY_FAILED +
labels; no gate claims; production wall, frozen instruments and buffer
控制 assets untouched.

Modes: smoke (N=12/nx=4 mechanism rehearsal; recorded, no design gates),
auth (judgement calibers, stages structural..regression), hot (layer 9;
refuses to run unless the auth preflight summary in the shared state file
is green), full (smoke then auth).  Per-case checkpoints + identity-matched
resume shared per mode+config digest.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import platform
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
    BRANCH_CONST_G,
    BRANCH_G0,
    G0_CONDUCTIVITY_EXPONENT,
    StrictFaceFluxWall,
    strict_cold_conductance_lu,
)
from core.strict_b_half_domain import StrictBHalfDomain  # noqa: E402
from core.tangent_faceflux_strict import (  # noqa: E402
    StrictBBaseState,
    StrictBTangentOperator,
    compute_stage_bases_strict,
    strict_direct_step_fn,
)
from core.tangent_step import make_probe, propagate_tangent  # noqa: E402
from reference.strict_b_face_admission import (  # noqa: E402
    sealed_face_dirichlet_reference,
    series_conductance,
    steady_powerlaw_flux,
    steady_powerlaw_profile,
)
from scripts.phase2_m2_verification import load_config, sha256_file  # noqa: E402
from scripts.phase5_g1a_amplitude_envelope import execute_cases  # noqa: E402
from scripts.phase5_wallfix_arbitration import (  # noqa: E402
    FREQUENCY_HZ,
    GAS_CONFIG,
    GATE_DC_CLOSURE,
    GATE_R_F,
    GATE_STATIONARITY,
    GATE_V5_ENERGY,
    GATE_V5_MASS,
    NSF_G0_DOP_PCT,
    TAN_DOP_PCT,
    _settle_worker as _prod_settle_worker,
    _tangent_worker as _prod_tangent_worker,
)

UNIT = "D1-STRICT-B"

# ---------------------------------------------------------------------------
# FROZEN JUDGEMENT LINES (design sections 3/5/6; registered pre-hot)
# ---------------------------------------------------------------------------
H_JVP = 5.0e-5                          # hot-point judgement h (JAB lineage)
H_LADDER_JVP = [1.0e-4, 5.0e-5, 2.5e-5]  # layer 7 full-step ladder
EPS_G_LADDER = [1.0e-4, 5.0e-5, 2.5e-5]  # admission odd-pair gradient ladder

LINE_TOPOLOGY = 1.0e-12                 # r_P / column replication / ledgers
LINE_WALLPOS_FINEST = 1.0e-3            # layer 3 finest wall-position error
SOAK_PERIODS = 64.0                     # uniform & perturbed soak length
SOAK_PERT_AMP = 1.0e-8                  # perturbation amplitude (relative)
SOAK_ENVELOPE_FACTOR = 1.05             # last-4-period norm envelope bound
SOAK_DRIFT = 1.0e-12                    # uniform mass/energy drift bound
HOTDC_PERIODS = 16.0                    # hot-DC AC-off soak length
HOTDC_STATIONARITY = 1.0e-3
HOTDC_FACE_CLOSURE = 1.0e-3             # |<q_h>+<q_c>| / max(...) row
A_LATE_FLOOR = 1.0e-10                  # z_j endpoint envelope floor
A_LATE_FACTOR = 1.5                     # A_late <= max(floor, 1.5*A_early)

LINE_COLD_AMP_REL = 0.10                # layer 4 |Y0 ratio - 1|
LINE_COLD_PHASE_DEG = 5.0               # layer 4 |arg ratio|
# frozen PROD cold complex anchor (wallfix auth checkpoint
# tangent_PROD_h5e-05_cold.json, run 20260811T085347Z_auth, machine A):
Y0_PROD_COLD = complex(0.0004998499198013624, 0.0009596625379939636)

ADM_STEADY_REL = 0.05                   # layer 5 finest steady/G/derivative
ADM_Y_AMP_REL = 0.10                    # layer 5 complex admittance amplitude
ADM_Y_PHASE_DEG = 5.0                   # layer 5 complex admittance phase
ADM_N_LADDER = [16, 32, 64]
ADM_THETA_POINTS = [0.0, 0.05, 0.10]

JVP_ODD_PAIRWISE = 1.0e-6               # layer 7 odd pairwise
JVP_EVEN_RATIO = (3.0, 5.0)             # layer 7 even decay window
JVP_EVEN_GUARD = 1.0e-12                # even judged only above this floor
JVP_IDENTITY = 1.0e-5                   # chain-vs-direct + h-spread

ENS_COLD_MASS_REL = 1.0e-12             # design section 3 ensemble gates
ENS_COLD_PRESSURE_REL = 1.0e-12
ENS_HOT_MASS_REL = 1.0e-10
ENS_HOT_THETADC_REL = 1.0e-2
ENS_HOT_PRESSURE_REL = 1.0e-2

LINE_PROD_ANCHOR_PP = 0.2               # PROD vs frozen TAN (V4 caliber)
CLASS_NSF_BAND_PP = 1.0
CLASS_MOVE_FRAC = 0.25

PROTO = {
    # smoke = mechanism rehearsal: shortened ladders/soaks, gates recorded
    # but never judged (design calibers live in "auth" only)
    "smoke": {"n_phys": 12, "nx": 4, "samples_per_period": 32,
              "theta_points": [0.05], "settle_periods": 2.0,
              "drive_periods": 2.0, "fit_skip_periods": 1.0,
              "slab_n_ladder": [8, 12], "soak_periods": 4.0,
              "hotdc_periods": 4.0, "adm_n_ladder": [12],
              "adm_theta_points": [0.0, 0.05],
              "jvp_h_ladder": [1.0e-4, 5.0e-5]},
    "auth": {"n_phys": 48, "nx": 8, "samples_per_period": 64,
             "theta_points": [0.05, 0.10], "settle_periods": 5.0,
             "drive_periods": 4.0, "fit_skip_periods": 2.0,
             "slab_n_ladder": ADM_N_LADDER, "soak_periods": SOAK_PERIODS,
             "hotdc_periods": HOTDC_PERIODS, "adm_n_ladder": ADM_N_LADDER,
             "adm_theta_points": ADM_THETA_POINTS,
             "jvp_h_ladder": H_LADDER_JVP},
}
BRANCHES = (BRANCH_CONST_G, BRANCH_G0)

# wallfix authoritative checkpoints (PROD anchor reuse, zero new compute)
WALLFIX_CKPT_AUTH = "results/phase5/wallfix_arbitration/checkpoints_auth_849699bb"
WALLFIX_CKPT_SMOKE = "results/phase5/wallfix_arbitration/checkpoints_smoke_849699bb"


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------

def quad_face_extrapolation(profile: np.ndarray) -> float:
    """Three-point quadratic extrapolation of an x-averaged theta profile to
    the hot face at y=-1/2 (cells at r+0 offsets 0.5/1.5/2.5 from the face).

    ARCHIVED DIAGNOSTIC ONLY: its sample rows 0..2 sit entirely inside the
    depth-3 crossing-link kinetic layer (coverage 15/8/3), so it reads the
    kinetic layer's shape, not the bulk continuation (measured on the N=48
    judgement geometry).  Gates use bulk_face_extrapolation."""

    return float(1.875 * profile[0] - 1.25 * profile[1] + 0.375 * profile[2])


BULK_EXCLUDE_ROWS = 3      # crossing-link kinetic layer depth (15/8/3)


def bulk_face_extrapolation(profile: np.ndarray, side: str) -> float:
    """Equivalent-Dirichlet face temperature: bulk linear fit continued to
    the face, excluding the near-face kinetic layer (rows < BULK_EXCLUDE).

    This is the standard wall-position metrology (the wall position IS the
    bulk solution's continuation), immune to the depth-3 kinetic layer the
    quadratic near-face stencil samples.  Rows are cell centres at r; the
    hot face sits at y=-1/2, the cold face at y=N-1/2."""

    n = len(profile)
    half = max(BULK_EXCLUDE_ROWS + 2, n // 2)
    if side == "hot":
        rows = np.arange(BULK_EXCLUDE_ROWS, half, dtype=float)
        y_face = -0.5
    elif side == "cold":
        rows = np.arange(n - half, n - BULK_EXCLUDE_ROWS, dtype=float)
        y_face = n - 0.5
    else:
        raise ValueError(f"unknown side {side!r}")
    coef = np.polyfit(rows, np.asarray(profile, dtype=float)[rows.astype(int)], 1)
    return float(np.polyval(coef, y_face))


def equal_mass_seed(hd: StrictBHalfDomain, theta_dc: float):
    """Closed equal-mass column seed: M/A = rho_ref * N exactly."""

    from core.equilibrium import equilibrium_fg

    n, nx = hd.n_phys, hd.nx
    th0 = float(hd.mapping.theta_ref_lu)
    rho0 = float(hd.mapping.lattice.rho_ref_lu)
    if theta_dc == 0.0:
        prof = np.full(n, th0)
    else:
        prof = th0 * (1.0 + float(theta_dc) * (1.0 - (np.arange(n) + 0.5) / n))
    rho = rho0 * n / np.sum(1.0 / prof) / prof
    theta2d = np.tile(prof[:, None], (1, nx))
    rho2d = np.tile(rho[:, None], (1, nx))
    return equilibrium_fg(rho2d, np.zeros((n, nx, 2)), theta2d,
                          hd.mapping.lattice.S, hd.lattice)


def make_wall(hd: StrictBHalfDomain, theta_hot, branch: str,
              ledger: dict | None = None) -> StrictFaceFluxWall:
    th0 = float(hd.mapping.theta_ref_lu)
    return StrictFaceFluxWall(hd.mapping, hd.lattice, theta_hot=theta_hot,
                              theta_amb=th0, branch=branch, theta_0=th0,
                              ledger=ledger)


def fit_admittance_strict(run: dict[str, Any], frequency_hz: float,
                          fit_skip_periods: float,
                          n_harmonics: int = 5) -> dict[str, Any]:
    """Single-face admittance from the strict ledger (theta-flux units).

    Y = (1f of q_hot / (rho0 * cp_eff * nx)) / (1f of theta_w) — NO /2:
    the strict rig has exactly one hot face (design section 3; the factor 2
    is presentation-only).  Directly comparable to the wallfix per-face fit."""

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
    y_face = (q1 / (run["rho0"] * run["cp_eff"] * run["nx"])) / w1
    return {"Y_face_theta_units": y_face, "theta_w_hat": w1,
            "q_hot_hat_lu": q1, "h2_q_rel": fit_q.leakage_relative(1)[2]}


def classify_strict(branch_rows: dict[float, dict], prod_rows: dict[float, dict],
                    thetas: list[float]) -> dict[str, Any]:
    """Design section 6.4 five-way classification (order as written)."""

    d_b = [branch_rows[th]["d_op_pct"] for th in thetas]
    moves = []
    for th, db in zip(thetas, d_b):
        d_pr = prod_rows[th]["d_op_pct"]
        gap = NSF_G0_DOP_PCT[th] - d_pr
        moves.append((db - d_pr) / gap if abs(gap) > 1e-12 else 0.0)
    pos = [v > 0.0 for v in d_b]
    in_band = all(abs(v - NSF_G0_DOP_PCT[th]) <= CLASS_NSF_BAND_PP
                  for v, th in zip(d_b, thetas))
    if any(pos) and not all(pos):
        label = "MIXED"
    elif all(pos) and in_band:
        label = "RESOLVED"
    elif all(pos):
        label = "SIGN_FLIPPED"
    elif (not any(pos)) and all(m >= CLASS_MOVE_FRAC for m in moves):
        label = "PARTIAL"
    else:
        label = "NULL"
    return {"label": label, "d_op_pct": d_b,
            "move_frac": [float(m) for m in moves],
            "nsf_ref_pct": [NSF_G0_DOP_PCT[th] for th in thetas]}


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              cwd=REPO_ROOT, capture_output=True, text=True,
                              timeout=10, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _steps_per_period(hd: StrictBHalfDomain) -> int:
    dt_s = float(hd.mapping.lattice.dt_s)
    return int(round(1.0 / (FREQUENCY_HZ * dt_s)))


# ---------------------------------------------------------------------------
# strict settle (equal-mass ensemble + legality + ensemble gates)
# ---------------------------------------------------------------------------

def settle_strict(gas_cfg: dict, *, n_phys: int, nx: int, theta_dc: float,
                  branch: str, settle_periods: float,
                  samples_per_period: int) -> dict[str, Any]:
    hd = StrictBHalfDomain(gas_cfg, n_phys=n_phys, nx=nx)
    th0 = float(hd.mapping.theta_ref_lu)
    rho0 = float(hd.mapping.lattice.rho_ref_lu)
    theta_hot_mean = th0 * (1.0 + float(theta_dc))
    ledger: dict = {}
    wall = make_wall(hd, theta_hot_mean, branch, ledger)
    f, g = equal_mass_seed(hd, theta_dc)
    mass_target = float(rho0) * n_phys * nx
    p_target = rho0 * th0

    spp = _steps_per_period(hd)
    sample_every = max(1, spp // int(samples_per_period))
    n_settle = int(round(settle_periods * spp))

    from core.macroscopic import recover_macro
    d = int(hd.mapping.lattice.D)
    s = int(hd.mapping.lattice.S)
    stat_window, mass_series = [], []
    for i in range(n_settle):
        f, g, _, _ = hd.strict_direct_step(f, g, face_wall=wall)
        if i % (10 * sample_every) == 0 and not np.all(np.isfinite(f)):
            return {"finite": False, "phase": "settle", "step": i}
        if i >= n_settle - spp and (i % sample_every == 0):
            m = recover_macro(f, g, D=d, S=s, lattice=hd.lattice)
            prof_i = np.mean(m.theta, axis=1)
            if not np.all(np.isfinite(prof_i)):
                return {"finite": False, "phase": "settle", "step": i}
            stat_window.append(prof_i)
            mass_series.append(float(np.sum(f)))
    stat = np.array(stat_window)
    base_profile = stat.mean(axis=0)
    stationarity = float(np.max(np.abs(stat[-1] - stat[0])) / th0)
    q_hot_dc = float(np.mean(ledger["hot_dE"][-spp:]))
    q_cold_dc = float(np.mean(ledger["cold_dE"][-spp:]))
    dc_closure = abs(q_hot_dc + q_cold_dc) / max(abs(q_hot_dc), 1e-300)

    # column-replication hard assert (canonical k_x=0 manifold)
    m_last = recover_macro(f, g, D=d, S=s, lattice=hd.lattice)
    col_dev = float(np.max(np.abs(m_last.theta - m_last.theta[:, :1])) / th0)

    # ensemble gates (design section 3).  The hot-point mean-pressure gate is
    # SELF-CONSISTENCY against the closed equal-mass isobaric expectation
    # p_exp = N rho_ref / sum(1/theta_r) built from the MEASURED profile —
    # heating a sealed equal-mass column raises p_bar physically (~Theta/2),
    # so a cold-reference comparison would gate on physics, not on ensemble
    # integrity.  Cold state: p_exp reduces to rho_ref*theta0 exactly.
    # Theta_DC measurement operator: near-face quadratic extrapolation.
    # Measured operator comparison on the N=48 judgement geometry: the bulk
    # linear continuation overshoots (+4.3% of the total difference — the
    # medium's low-k dispersion steepens the bulk slope past the flat
    # near-face layer), the quadratic reads -1.44%; quad is the closest
    # independent operator and gates, bulk is archived.
    mass = float(np.sum(f))
    mass_rel = abs(mass / mass_target - 1.0)
    p_mean = float(np.mean(m_last.p))
    p_exp = rho0 * n_phys / float(np.sum(1.0 / base_profile))
    p_rel = abs(p_mean / p_exp - 1.0)
    theta_face_ext = quad_face_extrapolation(base_profile)
    theta_face_bulk = bulk_face_extrapolation(base_profile, "hot")
    theta_dc_meas = (theta_face_ext - th0) / th0
    ens = {"mass_rel": mass_rel, "p_mean_rel_isobaric_exp": p_rel,
           "p_mean_lu": p_mean, "p_exp_lu": p_exp,
           "theta_dc_measured": float(theta_dc_meas),
           "theta_dc_bulk_archived": float((theta_face_bulk - th0) / th0)}
    if theta_dc == 0.0:
        ens["pass"] = bool(mass_rel <= ENS_COLD_MASS_REL
                           and p_rel <= ENS_COLD_PRESSURE_REL)
    else:
        theta_dc_err = abs(theta_dc_meas / float(theta_dc) - 1.0)
        ens["theta_dc_rel_err"] = float(theta_dc_err)
        ens["pass"] = bool(mass_rel <= ENS_HOT_MASS_REL
                           and theta_dc_err <= ENS_HOT_THETADC_REL
                           and p_rel <= ENS_HOT_PRESSURE_REL)

    return {
        "finite": True, "n_phys": n_phys, "nx": nx, "theta0": th0,
        "rho0": rho0, "dt_s": float(hd.mapping.lattice.dt_s),
        "steps_per_period": spp, "branch": branch,
        "stationarity_per_period": stationarity,
        "dc_closure_rel": dc_closure,
        "theta_dc_measured": float(theta_dc_meas),
        "column_replication_rel": col_dev,
        "mass_drift_settle": abs(mass_series[-1] / mass_series[0] - 1.0)
        if mass_series else float("nan"),
        "q_hot_dc_lu": q_hot_dc, "q_cold_dc_lu": q_cold_dc,
        "ensemble": ens,
        "base_profile": base_profile,
        "snapshot": {"f": f.copy(), "g": g.copy(),
                     "theta_hot_mean": float(theta_hot_mean),
                     "theta_amb": float(th0),
                     "n_phys": int(n_phys), "nx": int(nx),
                     "theta_dc_target": float(theta_dc),
                     "branch": branch},
    }


# ---------------------------------------------------------------------------
# picklable workers (strict; PROD reuses the wallfix workers verbatim)
# ---------------------------------------------------------------------------

def _sb_settle_ident(p: dict[str, Any]) -> dict[str, Any]:
    return {"variant": "STRICT_B", "branch": p["branch"],
            "theta_dc": float(p["theta_dc"]), "n_phys": int(p["n_phys"]),
            "nx": int(p["nx"]), "settle_periods": float(p["settle_periods"]),
            "samples_per_period": int(p["samples_per_period"]),
            "ens_v": 2}      # v2: isobaric self-consistency pressure gate


def _sb_settle_worker(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    p = payload
    ident = _sb_settle_ident(p)
    ck = (Path(p["ckpt_dir"]) / f"settle_{p['label']}.npz"
          if p.get("ckpt_dir") else None)
    if ck is not None and ck.exists():
        try:
            # context-manage the NpzFile: a dangling handle on an ident MISS
            # blocks the later os.replace on Windows (access denied)
            with np.load(ck, allow_pickle=False) as z:
                if json.loads(str(z["ident"])) == ident:
                    meta = json.loads(str(z["meta"]))
                    sident = json.loads(str(z["sident"]))
                    return p["label"], {"finite": True, **meta,
                                        "snapshot": {"f": z["f"], "g": z["g"],
                                                     **sident},
                                        "base_profile": z["base_profile"],
                                        "resumed_from_checkpoint": True}
        except Exception:  # noqa: BLE001 - stale checkpoint -> recompute
            pass
    run = settle_strict(p["gas_cfg"], n_phys=p["n_phys"], nx=p["nx"],
                        theta_dc=p["theta_dc"], branch=p["branch"],
                        settle_periods=p["settle_periods"],
                        samples_per_period=p["samples_per_period"])
    s = run.get("snapshot")
    if ck is not None and run.get("finite") and s is not None:
        tmp = ck.with_suffix(".tmp.npz")
        meta_keys = ("stationarity_per_period", "dc_closure_rel",
                     "theta_dc_measured", "column_replication_rel",
                     "mass_drift_settle", "q_hot_dc_lu", "q_cold_dc_lu",
                     "ensemble", "steps_per_period", "branch", "theta0",
                     "rho0", "dt_s", "n_phys", "nx")
        np.savez_compressed(
            tmp, f=s["f"], g=s["g"], base_profile=run["base_profile"],
            meta=json.dumps({k: run[k] for k in meta_keys}),
            sident=json.dumps({k: s[k] for k in (
                "theta_hot_mean", "theta_amb", "n_phys", "nx",
                "theta_dc_target", "branch")}),
            ident=json.dumps(ident))
        os.replace(tmp, ck)
    return p["label"], run


def _snapshot_to_strict_base(run: dict[str, Any]) -> StrictBBaseState:
    s = run["snapshot"]
    meta = {k: run.get(k) for k in (
        "stationarity_per_period", "theta_dc_measured", "dc_closure_rel",
        "mass_drift_settle", "steps_per_period", "ensemble")}
    return StrictBBaseState(f=np.asarray(s["f"]), g=np.asarray(s["g"]),
                            theta_w=float(s["theta_hot_mean"]),
                            theta_amb=float(s["theta_amb"]),
                            theta_dc_target=float(s["theta_dc_target"]),
                            meta=meta)


def _sb_tangent_worker(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    p = payload
    ident = {"variant": "STRICT_B", "branch": p["branch"], "h": float(p["h"]),
             "n_phys": int(p["n_phys"]), "nx": int(p["nx"]),
             "drive_periods": float(p["drive_periods"]),
             "fit_skip_periods": float(p["fit_skip_periods"]),
             "theta_hot_mean": float(p["hot_run"]["snapshot"]["theta_hot_mean"])}
    ck = (Path(p["ckpt_dir"]) / f"tangent_{p['label']}.json"
          if p.get("ckpt_dir") else None)
    if ck is not None and ck.exists():
        try:
            prev = json.loads(ck.read_text(encoding="utf-8"))
            if prev.get("ident") == ident:
                prev["resumed_from_checkpoint"] = True
                return p["label"], prev
        except Exception:  # noqa: BLE001
            pass
    hd = StrictBHalfDomain(p["gas_cfg"], n_phys=p["n_phys"], nx=p["nx"])
    hot_base = _snapshot_to_strict_base(p["hot_run"])
    cold_base = _snapshot_to_strict_base(p["cold_run"])
    wall = make_wall(hd, hot_base.theta_w, p["branch"])
    hot = compute_stage_bases_strict(hd, wall, hot_base)
    cold = compute_stage_bases_strict(hd, wall, cold_base)
    r_f_worst = max(hot.r_f, cold.r_f)
    op = StrictBTangentOperator(hd, wall, hot_base, hot, cold_base, cold,
                                h=float(p["h"]))
    run = propagate_tangent(op, frequency_hz=FREQUENCY_HZ,
                            drive_periods=p["drive_periods"],
                            samples_per_period=p["samples_per_period"],
                            log=None)
    fit = fit_admittance_strict(run, FREQUENCY_HZ, p["fit_skip_periods"])
    out = {
        "Y": {"re": float(np.real(fit["Y_face_theta_units"])),
              "im": float(np.imag(fit["Y_face_theta_units"]))},
        "h2_q_rel": float(fit["h2_q_rel"]),
        "audits": run["audits"],
        "r_f_worst": float(r_f_worst),
        "finite": bool(run.get("finite", False)),
        "ident": ident,
    }
    if ck is not None:
        tmp = ck.with_suffix(".tmp")
        tmp.write_text(json.dumps(out, indent=1), encoding="utf-8")
        os.replace(tmp, ck)
    return p["label"], out


def _steady_worker(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Adaptive steady slab (layer 3 wall position / layer 5 admission)."""

    p = payload
    ident = {"kind": "steady", "branch": p["branch"], "n_phys": int(p["n_phys"]),
             "nx": int(p["nx"]), "theta_hot_rel": float(p["theta_hot_rel"]),
             "theta_cold_rel": float(p["theta_cold_rel"]),
             "op_v": 2}   # v2: 3-quiet-pair/6-tau convergence + bulk metrology
    ck = (Path(p["ckpt_dir"]) / f"steady_{p['label']}.json"
          if p.get("ckpt_dir") else None)
    if ck is not None and ck.exists():
        try:
            prev = json.loads(ck.read_text(encoding="utf-8"))
            if prev.get("ident") == ident:
                prev["resumed_from_checkpoint"] = True
                return p["label"], prev
        except Exception:  # noqa: BLE001
            pass

    hd = StrictBHalfDomain(p["gas_cfg"], n_phys=p["n_phys"], nx=p["nx"])
    th0 = float(hd.mapping.theta_ref_lu)
    rho0 = float(hd.mapping.lattice.rho_ref_lu)
    n = hd.n_phys
    theta_hot = th0 * float(p["theta_hot_rel"])
    theta_cold = th0 * float(p["theta_cold_rel"])
    beta = G0_CONDUCTIVITY_EXPONENT if p["branch"] == BRANCH_G0 else 0.0

    # asymmetric wall: hot face theta_hot, cold face theta_cold
    ledger: dict = {}
    wall = StrictFaceFluxWall(hd.mapping, hd.lattice, theta_hot=theta_hot,
                              theta_amb=theta_cold, branch=p["branch"],
                              theta_0=th0, ledger=ledger)
    # seed on the exact continuum steady profile, equal-mass normalized
    from core.equilibrium import equilibrium_fg
    from core.macroscopic import recover_macro
    prof = steady_powerlaw_profile(n, theta_hot, theta_cold, beta)
    rho = rho0 * n / np.sum(1.0 / prof) / prof
    f, g = equilibrium_fg(np.tile(rho[:, None], (1, hd.nx)),
                          np.zeros((n, hd.nx, 2)),
                          np.tile(prof[:, None], (1, hd.nx)),
                          hd.mapping.lattice.S, hd.lattice)

    alpha_lu = float(hd.mapping.alpha_lu)
    tau_diff = n * n / (alpha_lu * math.pi ** 2)
    cap = int(min(15 * tau_diff, 4.0e6))
    # sealed-column acoustic transients ring at ~2*2N/c_lu steps; a single
    # window-pair comparison crosses zero on that oscillation and stops
    # early (measured: N=64 "converged" at 2.2 tau with a 10% transient
    # still in the profile).  Require a minimum of 6 diffusion times AND
    # three consecutive in-tolerance window pairs.
    min_steps = int(min(6.0 * tau_diff, cap))
    window = 500
    q_prev = None
    d_int = int(hd.mapping.lattice.D)
    s_int = int(hd.mapping.lattice.S)
    e_cell = 0.5 * (d_int + s_int) * rho0 * th0
    converged = False
    steps_done = 0
    quiet_pairs = 0
    while steps_done < cap:
        for _ in range(window):
            f, g, _, _ = hd.strict_direct_step(f, g, face_wall=wall)
        steps_done += window
        if not np.all(np.isfinite(f)):
            return p["label"], {"finite": False, "ident": ident,
                                "steps_done": steps_done}
        q_now = float(np.mean(ledger["hot_dE"][-window:])) / hd.nx
        if q_prev is not None:
            tol = max(1e-7 * abs(q_now), 1e-15 * e_cell)
            quiet_pairs = quiet_pairs + 1 if abs(q_now - q_prev) <= tol else 0
            if quiet_pairs >= 3 and steps_done >= min_steps:
                converged = True
                break
        q_prev = q_now
    m = recover_macro(f, g, D=d_int, S=s_int, lattice=hd.lattice)
    prof_meas = np.mean(m.theta, axis=1)
    prof_ref = steady_powerlaw_profile(n, theta_hot, theta_cold, beta)
    denom = max(abs(theta_hot - theta_cold), 1e-300)
    profile_err = float(np.max(np.abs(prof_meas - prof_ref)) / denom)
    # wall position: near-face quadratic extrapolation gates (measured to be
    # the closest independent operator on the N=48 judgement geometry); the
    # bulk linear continuation overshoots through the flat near-face layer
    # (medium low-k dispersion steepens the bulk slope) and is archived.
    face_ext = quad_face_extrapolation(prof_meas)
    cold_ext = float(1.875 * prof_meas[-1] - 1.25 * prof_meas[-2]
                     + 0.375 * prof_meas[-3])
    wallpos_hot = abs(face_ext - theta_hot) / denom
    wallpos_cold = abs(cold_ext - theta_cold) / denom
    bulk_hot = bulk_face_extrapolation(prof_meas, "hot")
    q_dc = float(np.mean(ledger["hot_dE"][-window:])) / hd.nx
    q_ref = steady_powerlaw_flux(n, theta_hot, theta_cold,
                                 strict_cold_conductance_lu(hd.mapping) * 0.5,
                                 th0, beta)
    # face-semantics consistency: the wall formula against INDEPENDENTLY
    # recorded observables (theta_1 from the state snapshot, q from the
    # ledger; the formula itself is never re-used to produce either).
    g_hot = strict_cold_conductance_lu(hd.mapping) \
        * (theta_hot / th0) ** beta
    face_consistency = abs(g_hot * (theta_hot - float(prof_meas[0]))
                           / q_dc - 1.0) if q_dc != 0 else None
    # bulk effective conductivity (interior slope method) — archived medium
    # row (the frozen medium's low-k dispersion, G0-B fence; NOT a gate)
    sel = slice(max(3, n // 8), max(4, n // 2))
    coef = np.polyfit(np.arange(n, dtype=float)[sel], prof_meas[sel], 1)
    k_eff_bulk = (-q_dc / coef[0]) if coef[0] != 0 else float("nan")
    out = {
        "finite": True, "converged": converged, "steps_done": steps_done,
        "profile_err_rel": profile_err,
        "wallpos_hot_rel": float(wallpos_hot),
        "wallpos_cold_rel": float(wallpos_cold),
        "wallpos_hot_bulk_archived": float(abs(bulk_hot - theta_hot) / denom),
        "face_consistency_rel": (float(face_consistency)
                                 if face_consistency is not None else None),
        "k_eff_bulk_over_nom": float(
            k_eff_bulk / (strict_cold_conductance_lu(hd.mapping) * 0.5)),
        "q_dc_per_col": q_dc, "q_ref_continuum": float(q_ref),
        "q_rel_err": float(abs(q_dc / q_ref - 1.0)) if q_ref != 0 else None,
        "column_replication_rel": float(
            np.max(np.abs(m.theta - m.theta[:, :1])) / th0),
        "ident": ident,
    }
    if ck is not None:
        tmp = ck.with_suffix(".tmp")
        tmp.write_text(json.dumps(out, indent=1), encoding="utf-8")
        os.replace(tmp, ck)
    return p["label"], out


def _soak_worker(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Layer 3 stability soaks: uniform / perturbed / hot-DC."""

    p = payload
    ident = {"kind": p["kind"], "branch": p["branch"],
             "n_phys": int(p["n_phys"]), "nx": int(p["nx"]),
             "periods": float(p["periods"]),
             "theta_dc": float(p.get("theta_dc", 0.0))}
    ck = (Path(p["ckpt_dir"]) / f"soak_{p['label']}.json"
          if p.get("ckpt_dir") else None)
    if ck is not None and ck.exists():
        try:
            prev = json.loads(ck.read_text(encoding="utf-8"))
            if prev.get("ident") == ident:
                prev["resumed_from_checkpoint"] = True
                return p["label"], prev
        except Exception:  # noqa: BLE001
            pass

    hd = StrictBHalfDomain(p["gas_cfg"], n_phys=p["n_phys"], nx=p["nx"])
    th0 = float(hd.mapping.theta_ref_lu)
    spp = _steps_per_period(hd)
    n_steps = int(round(float(p["periods"]) * spp))
    from core.macroscopic import recover_macro
    d_int = int(hd.mapping.lattice.D)
    s_int = int(hd.mapping.lattice.S)
    c2 = np.sum(np.asarray(hd.lattice.c, float) ** 2, axis=-1)

    def tot_e(f, g):
        return float(np.sum(0.5 * f * c2) + np.sum(g))

    out: dict[str, Any] = {"ident": ident, "finite": True}

    if p["kind"] in ("uniform", "perturbed"):
        wall = make_wall(hd, th0, p["branch"])       # cold wall both faces
        f, g = equal_mass_seed(hd, 0.0)
        if p["kind"] == "perturbed":
            # reflection-symmetric (automatic on the physical manifold),
            # zero-conserved-moment perturbation: g-only, zero mean
            rng = np.random.default_rng(20260817)
            phi = rng.standard_normal((hd.n_phys, hd.nx))
            phi -= phi.mean()
            e_cell = 0.5 * (d_int + s_int) * th0
            g = g + (SOAK_PERT_AMP * e_cell * phi)[..., None] \
                * np.asarray(hd.lattice.w)
            f0_ref, g0_ref = equal_mass_seed(hd, 0.0)
            norm0 = math.sqrt(float(np.sum((f - f0_ref) ** 2)
                                    + np.sum((g - g0_ref) ** 2)))
            out["norm0"] = norm0
        mass0, e0 = float(np.sum(f)), tot_e(f, g)
        period_norms = []
        for i in range(n_steps):
            f, g, _, _ = hd.strict_direct_step(f, g, face_wall=wall)
            if (i + 1) % spp == 0:
                if not np.all(np.isfinite(f)):
                    out["finite"] = False
                    break
                if p["kind"] == "perturbed":
                    period_norms.append(math.sqrt(float(
                        np.sum((f - f0_ref) ** 2) + np.sum((g - g0_ref) ** 2))))
        out["mass_drift_rel"] = abs(float(np.sum(f)) / mass0 - 1.0)
        out["energy_drift_rel"] = abs(tot_e(f, g) / e0 - 1.0)
        if p["kind"] == "uniform":
            out["pass"] = bool(out["finite"]
                               and out["mass_drift_rel"] <= SOAK_DRIFT
                               and out["energy_drift_rel"] <= SOAK_DRIFT)
        else:
            last4 = period_norms[-4:] if len(period_norms) >= 4 else period_norms
            out["envelope_last4_over_norm0"] = (max(last4) / out["norm0"]
                                                if last4 else None)
            out["pass"] = bool(out["finite"] and last4
                               and max(last4) <= SOAK_ENVELOPE_FACTOR
                               * out["norm0"])
    elif p["kind"] == "hotdc":
        # continue from the provided settle snapshot, AC off, 16 periods
        snap = p["settle_run"]["snapshot"]
        f = np.asarray(snap["f"]).copy()
        g = np.asarray(snap["g"]).copy()
        ledger: dict = {}
        wall = make_wall(hd, float(snap["theta_hot_mean"]), p["branch"], ledger)
        z_endpoints = []
        stat_first, stat_last = None, None
        for i in range(n_steps):
            f, g, _, _ = hd.strict_direct_step(f, g, face_wall=wall)
            if (i + 1) % spp == 0:
                if not np.all(np.isfinite(f)):
                    out["finite"] = False
                    break
                m = recover_macro(f, g, D=d_int, S=s_int, lattice=hd.lattice)
                z_endpoints.append(np.mean(m.theta, axis=1) / th0)
        if out["finite"] and len(z_endpoints) >= 4:
            z = z_endpoints
            a_late = 0.5 * float(np.max(np.abs(z[-1] - z[-2])))
            a_early = 0.5 * float(np.max(np.abs(z[-3] - z[-4])))
            stat_first, stat_last = z[0], z[-1]
            spp_stat = float(np.max(np.abs(z[-1] - z[-2])))
            q_h = float(np.mean(ledger["hot_dE"][-spp:]))
            q_c = float(np.mean(ledger["cold_dE"][-spp:]))
            closure = abs(q_h + q_c) / max(abs(q_h) + abs(q_c), 1e-300)
            out.update({
                "stationarity_per_period": spp_stat,
                "face_closure_rel": closure,
                "A_late": a_late, "A_early": a_early,
                "A_late_bound": max(A_LATE_FLOOR, A_LATE_FACTOR * a_early),
                "q_hot_dc": q_h, "q_cold_dc": q_c,
            })
            out["pass"] = bool(
                spp_stat <= HOTDC_STATIONARITY
                and closure <= HOTDC_FACE_CLOSURE
                and a_late <= out["A_late_bound"])
        else:
            out["pass"] = False
    else:
        raise ValueError(f"unknown soak kind {p['kind']!r}")

    if ck is not None:
        tmp = ck.with_suffix(".tmp")
        tmp.write_text(json.dumps(out, indent=1, default=float),
                       encoding="utf-8")
        os.replace(tmp, ck)
    return p["label"], out


def _jvp_probe_worker(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Layer 7 full-step JVP ladder probe on a settled base state."""

    p = payload
    ident = {"kind": "jvp", "branch": p["branch"], "n_phys": int(p["n_phys"]),
             "nx": int(p["nx"]),
             "h_ladder": [float(h) for h in p.get("h_ladder", H_LADDER_JVP)],
             "theta_dc": float(p["base_run"]["snapshot"]["theta_dc_target"])}
    ck = (Path(p["ckpt_dir"]) / f"jvp_{p['label']}.json"
          if p.get("ckpt_dir") else None)
    if ck is not None and ck.exists():
        try:
            prev = json.loads(ck.read_text(encoding="utf-8"))
            if prev.get("ident") == ident:
                prev["resumed_from_checkpoint"] = True
                return p["label"], prev
        except Exception:  # noqa: BLE001
            pass

    h_ladder = [float(h) for h in p.get("h_ladder", H_LADDER_JVP)]
    hd = StrictBHalfDomain(p["gas_cfg"], n_phys=p["n_phys"], nx=p["nx"])
    base = _snapshot_to_strict_base(p["base_run"])
    wall = make_wall(hd, base.theta_w, p["branch"])
    bases = compute_stage_bases_strict(hd, wall, base)
    vf, vg, eta = make_probe(base.f.shape, base.g.shape)
    op0 = StrictBTangentOperator(hd, wall, base, bases, base, bases,
                                 h=h_ladder[0])
    s = op0.macro_scale(vf, vg, eta)
    vf, vg, eta = vf / s, vg / s, eta / s
    rows, odd_vecs = [], []
    for h in h_ladder:
        fp, gp, qhp, _ = strict_direct_step_fn(
            hd, wall, base.f + h * vf, base.g + h * vg, base.theta_w + h * eta)
        fm, gm, qhm, _ = strict_direct_step_fn(
            hd, wall, base.f - h * vf, base.g - h * vg, base.theta_w - h * eta)
        f0, g0, _, _ = strict_direct_step_fn(hd, wall, base.f, base.g,
                                             base.theta_w)
        odd = np.concatenate([(fp - fm).ravel(), (gp - gm).ravel()]) / (2 * h)
        even = np.concatenate([(fp + fm - 2 * f0).ravel(),
                               (gp + gm - 2 * g0).ravel()])
        op = StrictBTangentOperator(hd, wall, base, bases, base, bases, h=h)
        cf, cg, cqh, _ = op.step(vf * s, vg * s, eta * s)
        chain = np.concatenate([cf.ravel(), cg.ravel()]) / s
        rows.append({
            "h": float(h),
            "odd_norm": float(np.linalg.norm(odd)),
            "even_norm": float(np.linalg.norm(even)),
            "dq_hot_odd": float((qhp - qhm) / (2 * h)),
            "chain_vs_singleshot_rel": float(
                np.linalg.norm(chain - odd)
                / max(np.linalg.norm(odd), 1e-300)),
        })
        odd_vecs.append(odd)
    pair_rel, even_ratio = [], []
    max_odd = max(r["odd_norm"] for r in rows)
    for i in range(len(h_ladder) - 1):
        pair_rel.append(float(np.linalg.norm(odd_vecs[i + 1] - odd_vecs[i])
                              / max(np.linalg.norm(odd_vecs[i]), 1e-300)))
        lo = rows[i + 1]["even_norm"]
        even_ratio.append(float(rows[i]["even_norm"] / lo) if lo > 0
                          else float("inf"))
    even_judged = all(r["even_norm"] > JVP_EVEN_GUARD * max_odd for r in rows)
    ok = (all(r <= JVP_ODD_PAIRWISE for r in pair_rel)
          and all(r["chain_vs_singleshot_rel"] <= JVP_IDENTITY for r in rows)
          and (not even_judged
               or all(JVP_EVEN_RATIO[0] <= er <= JVP_EVEN_RATIO[1]
                      for er in even_ratio)))
    out = {"rows": rows, "odd_pairwise_rel": pair_rel,
           "even_ratios": even_ratio, "even_judged": bool(even_judged),
           "pass": bool(ok), "ident": ident, "finite": True}
    if ck is not None:
        tmp = ck.with_suffix(".tmp")
        tmp.write_text(json.dumps(out, indent=1), encoding="utf-8")
        os.replace(tmp, ck)
    return p["label"], out


def _dispatch(payload):
    kind = payload.get("worker_kind")
    if kind == "prod_settle":
        return _prod_settle_worker(payload)
    if kind == "prod_tangent":
        return _prod_tangent_worker(payload)
    if kind == "sb_settle":
        return _sb_settle_worker(payload)
    if kind == "sb_tangent":
        return _sb_tangent_worker(payload)
    if kind == "steady":
        return _steady_worker(payload)
    if kind == "soak":
        return _soak_worker(payload)
    if kind == "jvp":
        return _jvp_probe_worker(payload)
    raise ValueError(f"unknown worker kind {kind!r}")


# ---------------------------------------------------------------------------
# stage orchestration
# ---------------------------------------------------------------------------

def _dop(y_hot: complex, y_cold: complex) -> dict[str, float]:
    d = y_hot / y_cold
    return {"d_op_pct": (abs(d) - 1.0) * 100.0,
            "phase_deg": math.degrees(math.atan2(d.imag, d.real))}


def stage_structural(gas_cfg, proto, log) -> dict[str, Any]:
    """Layer 1 runtime asserts on both geometries (build-time fail-loud)."""

    out: dict[str, Any] = {}
    for name, (n, nx) in {"judgement": (proto["n_phys"], proto["nx"]),
                          "minimal": (5, 2)}.items():
        hd = StrictBHalfDomain(gas_cfg, n_phys=n, nx=nx)
        out[name] = hd.structural_report
        log(f"structural[{name}]: {hd.structural_report}")
    out["pass"] = True
    return out


def stage_slab(gas_cfg, proto, workers, ckpt, log) -> dict[str, Any]:
    """Layer 3 wall-position convergence (CONST_G, N ladder)."""

    n_ladder = list(proto["slab_n_ladder"])
    payloads = []
    for n in n_ladder:
        payloads.append({
            "worker_kind": "steady", "label": f"slab_constg_N{n}",
            "branch": BRANCH_CONST_G, "gas_cfg": gas_cfg, "n_phys": n,
            "nx": 4, "theta_hot_rel": 1.05, "theta_cold_rel": 1.0,
            "ckpt_dir": str(ckpt)})
    res = execute_cases(payloads, workers, log, worker=_dispatch)
    rows, ok = {}, True
    wallpos = []
    for n in n_ladder:
        r = res.get(f"slab_constg_N{n}", {})
        if not r.get("finite") or not r.get("converged"):
            ok = False
            rows[f"N{n}"] = {"error": "not finite/converged", **{
                k: r.get(k) for k in ("steps_done",)}}
            continue
        wp = max(r["wallpos_hot_rel"], r["wallpos_cold_rel"])
        wallpos.append(wp)
        rows[f"N{n}"] = {k: r[k] for k in (
            "wallpos_hot_rel", "wallpos_cold_rel", "profile_err_rel",
            "q_rel_err", "column_replication_rel", "steps_done")}
        if r["column_replication_rel"] > LINE_TOPOLOGY:
            ok = False
        log(f"slab N{n}: wallpos={wp:.3e} profile={r['profile_err_rel']:.3e} "
            f"q_err={r['q_rel_err']:.3e}")
    if len(wallpos) == len(n_ladder):
        monotone = all(wallpos[i + 1] <= wallpos[i]
                       for i in range(len(wallpos) - 1))
        finest = wallpos[-1]
        ok = ok and monotone and finest <= LINE_WALLPOS_FINEST
        rows["monotone"] = bool(monotone)
        rows["finest_wallpos"] = float(finest)
    else:
        ok = False
    rows["pass"] = bool(ok)
    return rows


def stage_soak(gas_cfg, proto, workers, ckpt, log,
               settles: dict[str, Any]) -> dict[str, Any]:
    """Layer 3 stability soaks on the judgement geometry."""

    n, nx = proto["n_phys"], proto["nx"]
    payloads = [
        {"worker_kind": "soak", "label": "soak_uniform", "kind": "uniform",
         "branch": BRANCH_CONST_G, "gas_cfg": gas_cfg, "n_phys": n, "nx": nx,
         "periods": proto["soak_periods"], "ckpt_dir": str(ckpt)},
        {"worker_kind": "soak", "label": "soak_perturbed", "kind": "perturbed",
         "branch": BRANCH_CONST_G, "gas_cfg": gas_cfg, "n_phys": n, "nx": nx,
         "periods": proto["soak_periods"], "ckpt_dir": str(ckpt)},
    ]
    for th in proto["theta_points"]:
        lbl = f"CONST_G_th{th:g}"
        if lbl in settles and settles[lbl].get("finite"):
            payloads.append({
                "worker_kind": "soak", "label": f"soak_hotdc_th{th:g}",
                "kind": "hotdc", "branch": BRANCH_CONST_G, "gas_cfg": gas_cfg,
                "n_phys": n, "nx": nx, "periods": proto["hotdc_periods"],
                "theta_dc": th, "settle_run": settles[lbl],
                "ckpt_dir": str(ckpt)})
    res = execute_cases(payloads, workers, log, worker=_dispatch)
    ok = True
    for lbl, r in res.items():
        row = {k: r.get(k) for k in (
            "pass", "mass_drift_rel", "energy_drift_rel",
            "envelope_last4_over_norm0", "stationarity_per_period",
            "face_closure_rel", "A_late", "A_early", "A_late_bound")}
        log(f"{lbl}: {row}")
        if "worker_exception" in r or not r.get("pass"):
            ok = False
    res["pass"] = bool(ok)
    return res


def stage_cold(gas_cfg, proto, workers, ckpt, log,
               settles, tangs, mode: str = "auth") -> dict[str, Any]:
    """Layer 4: CONST_G cold complex admittance vs the frozen PROD anchor.

    The frozen anchor is the AUTH-geometry PROD cold admittance; on the
    smoke geometry the thermal layer spans the whole shallow column and the
    admittance is a different number, so smoke compares against the wallfix
    SMOKE checkpoint PROD value (same geometry) and records only."""

    rc = tangs.get(f"CONST_G_h{H_JVP:g}_cold", {})
    if "Y" not in rc:
        return {"pass": False, "reason": "cold tangent missing/failed"}
    y0 = complex(rc["Y"]["re"], rc["Y"]["im"])
    anchor = Y0_PROD_COLD
    anchor_src = "frozen auth checkpoint"
    if mode != "auth":
        ck = (REPO_ROOT / WALLFIX_CKPT_SMOKE
              / f"tangent_PROD_h{H_JVP:g}_cold.json")
        try:
            prev = json.loads(ck.read_text(encoding="utf-8"))
            anchor = complex(prev["Y"]["re"], prev["Y"]["im"])
            anchor_src = "wallfix smoke checkpoint (same geometry)"
        except Exception:  # noqa: BLE001 - keep frozen anchor, record only
            anchor_src = "frozen auth checkpoint (GEOMETRY MISMATCH, record only)"
    ratio = y0 / anchor
    amp = abs(ratio) - 1.0
    phase = math.degrees(math.atan2(ratio.imag, ratio.real))
    ok = abs(amp) <= LINE_COLD_AMP_REL and abs(phase) <= LINE_COLD_PHASE_DEG
    row = {"Y0_strict": {"re": y0.real, "im": y0.imag},
           "Y0_anchor": {"re": anchor.real, "im": anchor.imag},
           "anchor_source": anchor_src,
           "amp_rel": float(amp), "phase_deg": float(phase),
           "pass": bool(ok)}
    log(f"cold anchor[{anchor_src}]: |ratio|-1={amp:+.5f} "
        f"phase={phase:+.3f}deg -> "
        f"{'PASS' if ok else 'FAIL (STRICT_B_COLD_ILLEGAL)'}")
    return row


def stage_admission(gas_cfg, proto, workers, ckpt, log) -> dict[str, Any]:
    """Layer 5 G0 admission vs independent continuum references."""

    n_ladder = list(proto["adm_n_ladder"])
    theta_points = list(proto["adm_theta_points"])
    payloads = []
    # (a) +- gradient steady family, N ladder
    for n in n_ladder:
        for th in (0.05, 0.10):
            for sign, tag in ((+1, "pos"), (-1, "neg")):
                payloads.append({
                    "worker_kind": "steady",
                    "label": f"adm_ramp_N{n}_th{th:g}_{tag}",
                    "branch": BRANCH_G0, "gas_cfg": gas_cfg, "n_phys": n,
                    "nx": 4,
                    "theta_hot_rel": 1.0 + sign * th,
                    "theta_cold_rel": 1.0,
                    "ckpt_dir": str(ckpt)})
    # (b) odd-pair small-gradient family (fixed centre temperature)
    for n in n_ladder:
        for thc in theta_points:
            centre = 1.0 + thc
            for eps in EPS_G_LADDER:
                for sign, tag in ((+1, "p"), (-1, "m")):
                    payloads.append({
                        "worker_kind": "steady",
                        "label": f"adm_eps_N{n}_c{centre:g}_e{eps:g}_{tag}",
                        "branch": BRANCH_G0, "gas_cfg": gas_cfg, "n_phys": n,
                        "nx": 4,
                        "theta_hot_rel": centre * (1.0 + sign * eps / 2.0),
                        "theta_cold_rel": centre * (1.0 - sign * eps / 2.0),
                        "ckpt_dir": str(ckpt)})
    res = execute_cases(payloads, workers, log, worker=_dispatch)

    out: dict[str, Any] = {"ramp": {}, "conductance": {}}
    ok = True

    # ramp family: profile error finest <= 5%, monotone in N
    for th in (0.05, 0.10):
        for tag in ("pos", "neg"):
            errs = []
            for n in n_ladder:
                r = res.get(f"adm_ramp_N{n}_th{th:g}_{tag}", {})
                if not r.get("finite") or not r.get("converged"):
                    ok = False
                    errs = []
                    break
                errs.append(r["profile_err_rel"])
            key = f"th{th:g}_{tag}"
            if errs:
                monotone = all(errs[i + 1] <= errs[i] * 1.02
                               for i in range(len(errs) - 1))
                row_ok = errs[-1] <= ADM_STEADY_REL and monotone
                out["ramp"][key] = {"profile_err_by_N": errs,
                                    "monotone": bool(monotone),
                                    "pass": bool(row_ok)}
                ok = ok and row_ok
                log(f"admission ramp {key}: errs={['%.3e' % e for e in errs]} "
                    f"monotone={monotone}")
            else:
                out["ramp"][key] = {"pass": False, "reason": "case died"}

    # face-semantics consistency (GATE): the wall formula against the
    # independently recorded snapshot theta_1 and ledger q, worst case over
    # every finite steady case at the finest N (the N=48 direct measurement
    # separated face semantics ~0.5-2% from the medium's bulk dispersion)
    n_fin = n_ladder[-1]
    face_rows = []
    for lbl, r in res.items():
        if r.get("finite") and r.get("ident", {}).get("n_phys") == n_fin \
                and r.get("face_consistency_rel") is not None:
            face_rows.append((lbl, r["face_consistency_rel"]))
    if face_rows:
        worst = max(v for _, v in face_rows)
        out["face_consistency_worst_finest"] = {
            "value": float(worst), "cases": len(face_rows),
            "pass": bool(worst <= ADM_STEADY_REL)}
        ok = ok and worst <= ADM_STEADY_REL
        log(f"admission face consistency (N{n_fin}, {len(face_rows)} cases): "
            f"worst={worst:.3e}")
    else:
        out["face_consistency_worst_finest"] = {"pass": False,
                                                "reason": "no finite cases"}
        ok = False

    # conductance: odd-pair G_series per centre; the POWER-LAW EXPONENT is
    # the gate (the medium's k-dispersion multiplier cancels in the ratio);
    # absolute G_series vs the nominal continuum is ARCHIVED with the
    # G0-B fence (alpha_eff(k->0) does not converge to nominal, frozen).
    hd_probe = StrictBHalfDomain(gas_cfg, n_phys=n_ladder[0], nx=4)
    th0 = float(hd_probe.mapping.theta_ref_lu)
    k0 = strict_cold_conductance_lu(hd_probe.mapping) * 0.5   # k_0 = G_cold*d_f
    g_meas_by_n: dict[int, dict[float, float]] = {}
    for n in n_ladder:
        g_meas: dict[float, float] = {}
        for thc in theta_points:
            centre = 1.0 + thc
            slopes = []
            for eps in EPS_G_LADDER:
                rp = res.get(f"adm_eps_N{n}_c{centre:g}_e{eps:g}_p", {})
                rm = res.get(f"adm_eps_N{n}_c{centre:g}_e{eps:g}_m", {})
                if not (rp.get("finite") and rm.get("finite")):
                    ok = False
                    continue
                dq = rp["q_dc_per_col"] - rm["q_dc_per_col"]
                d_theta = 2.0 * eps * centre * th0    # theta_h - theta_c, both signs
                slopes.append(dq / (2.0 * d_theta) * 2.0)
            if slopes:
                g_meas[thc] = float(np.mean(slopes))
                spread = (max(slopes) - min(slopes)) / abs(np.mean(slopes))
                out["conductance"][f"N{n}_c{centre:g}_slope_spread"] = spread
        g_meas_by_n[n] = g_meas
    g_fin = g_meas_by_n.get(n_fin, {})
    cond_rows = {}
    for thc, g_val in g_fin.items():
        centre_theta = (1.0 + thc) * th0
        ref = series_conductance(centre_theta, n_fin, k0, th0,
                                 G0_CONDUCTIVITY_EXPONENT)
        rel = abs(g_val / ref["G_series"] - 1.0)
        cond_rows[f"c{1 + thc:g}_archived"] = {
            "G_meas": g_val, "G_ref_nominal": ref["G_series"],
            "rel_dev_vs_nominal": float(rel),
            "note": "medium low-k dispersion, G0-B fence; archived"}
        log(f"admission G(N{n_fin}, centre {1 + thc:g}) vs nominal: "
            f"{rel:+.3e} (archived, medium dispersion)")
    # power-law exponent gate across the centres (log-log slope vs 1.04)
    pos_centres = [thc for thc in theta_points if thc in g_fin
                   and g_fin[thc] > 0]
    if len(pos_centres) >= 2:
        xs = np.log([(1.0 + thc) * th0 for thc in pos_centres])
        ys = np.log([g_fin[thc] for thc in pos_centres])
        slope = float(np.polyfit(xs, ys, 1)[0])
        rel = abs(slope / G0_CONDUCTIVITY_EXPONENT - 1.0)
        cond_rows["powerlaw_exponent"] = {
            "meas": slope, "ref": G0_CONDUCTIVITY_EXPONENT,
            "rel_err": float(rel), "pass": bool(rel <= ADM_STEADY_REL)}
        ok = ok and rel <= ADM_STEADY_REL
        log(f"admission power-law exponent: {slope:.4f} vs "
            f"{G0_CONDUCTIVITY_EXPONENT} (rel {rel:.3e})")
    else:
        cond_rows["powerlaw_exponent"] = {"pass": False,
                                          "reason": "insufficient centres"}
        ok = False
    out["conductance"].update(cond_rows)
    out["k0_lu"] = k0
    out["k_eff_bulk_over_nom_archived"] = {
        lbl: r.get("k_eff_bulk_over_nom") for lbl, r in res.items()
        if r.get("finite") and r.get("ident", {}).get("n_phys") == n_fin}
    out["pass"] = bool(ok)
    return out


def stage_admission_ac(gas_cfg, proto, workers, ckpt, log) -> dict[str, Any]:
    """Layer 5 complex admittance vs the sealed stratified reference."""

    n_ladder = list(proto["adm_n_ladder"])
    theta_points = list(proto["adm_theta_points"])
    payloads = []
    for n in n_ladder:
        for th in theta_points:
            payloads.append({
                "worker_kind": "sb_settle", "label": f"admac_settle_N{n}_th{th:g}",
                "branch": BRANCH_G0, "theta_dc": th, "gas_cfg": gas_cfg,
                "n_phys": n, "nx": 4,
                "settle_periods": proto["settle_periods"],
                "samples_per_period": proto["samples_per_period"],
                "ckpt_dir": str(ckpt)})
    settles = execute_cases(payloads, workers, log, worker=_dispatch)

    tang_payloads = []
    for n in n_ladder:
        cold = settles.get(f"admac_settle_N{n}_th0", {})
        if not cold.get("finite"):
            continue
        for th in theta_points:
            hot = settles.get(f"admac_settle_N{n}_th{th:g}", {})
            if not hot.get("finite"):
                continue
            tang_payloads.append({
                "worker_kind": "sb_tangent", "label": f"admac_tan_N{n}_th{th:g}",
                "branch": BRANCH_G0, "h": H_JVP, "gas_cfg": gas_cfg,
                "n_phys": n, "nx": 4, "hot_run": hot, "cold_run": cold,
                "drive_periods": proto["drive_periods"],
                "samples_per_period": proto["samples_per_period"],
                "fit_skip_periods": proto["fit_skip_periods"],
                "ckpt_dir": str(ckpt)})
    tangs = execute_cases(tang_payloads, workers, log, worker=_dispatch)

    hd_probe = StrictBHalfDomain(gas_cfg, n_phys=n_ladder[0], nx=4)
    m = hd_probe.mapping
    th0 = float(m.theta_ref_lu)
    rho0 = float(m.lattice.rho_ref_lu)
    c_v = 0.5 * (int(m.lattice.D) + int(m.lattice.S))
    c_p = c_v + 1.0
    k0 = strict_cold_conductance_lu(m) * 0.5
    omega_lu = 2.0 * math.pi * FREQUENCY_HZ * float(m.lattice.dt_s)

    rows, ok = {}, True
    for n in n_ladder:
        for th in theta_points:
            r = tangs.get(f"admac_tan_N{n}_th{th:g}", {})
            if "Y" not in r:
                rows[f"N{n}_th{th:g}"] = {"pass": False, "reason": "missing"}
                ok = False
                continue
            y_lbm = complex(r["Y"]["re"], r["Y"]["im"])
            ref = sealed_face_dirichlet_reference(
                n_cells=n, omega_lu=omega_lu, k0=k0, theta0=th0,
                beta=G0_CONDUCTIVITY_EXPONENT, rho_ref=rho0, c_v=c_v,
                theta_dc=th)
            y_ref = complex(ref["Y_ref"]) / (rho0 * c_p)
            ratio = y_lbm / y_ref
            amp = abs(ratio) - 1.0
            ph = math.degrees(math.atan2(ratio.imag, ratio.real))
            row_ok = (abs(amp) <= ADM_Y_AMP_REL
                      and abs(ph) <= ADM_Y_PHASE_DEG)
            rows[f"N{n}_th{th:g}"] = {
                "Y_lbm": {"re": y_lbm.real, "im": y_lbm.imag},
                "Y_ref": {"re": y_ref.real, "im": y_ref.imag},
                "amp_rel": float(amp), "phase_deg": float(ph),
                "pass": bool(row_ok)}
            log(f"admission AC N{n} th{th:g}: amp={amp:+.4f} ph={ph:+.3f}deg")
            if n == n_ladder[-1]:
                ok = ok and row_ok
    rows["pass"] = bool(ok)
    return rows


def stage_jvp(gas_cfg, proto, workers, ckpt, log,
              settles) -> dict[str, Any]:
    """Layer 7 full-step JVP ladder on cold + hottest base states."""

    n, nx = proto["n_phys"], proto["nx"]
    payloads = []
    for th_lbl, run_lbl in (("cold", "CONST_G_th0"),
                            ("hot", f"CONST_G_th{proto['theta_points'][-1]:g}")):
        base = settles.get(run_lbl)
        if base is None or not base.get("finite"):
            return {"pass": False, "reason": f"missing base {run_lbl}"}
        payloads.append({
            "worker_kind": "jvp", "label": f"jvp_{th_lbl}",
            "branch": BRANCH_CONST_G, "gas_cfg": gas_cfg,
            "n_phys": n, "nx": nx, "base_run": base,
            "h_ladder": proto["jvp_h_ladder"], "ckpt_dir": str(ckpt)})
    res = execute_cases(payloads, workers, log, worker=_dispatch)
    ok = all(res.get(f"jvp_{k}", {}).get("pass") for k in ("cold", "hot"))
    for k in ("cold", "hot"):
        r = res.get(f"jvp_{k}", {})
        log(f"jvp[{k}]: pairwise={r.get('odd_pairwise_rel')} "
            f"even={r.get('even_ratios')} judged={r.get('even_judged')} "
            f"identity={[row['chain_vs_singleshot_rel'] for row in r.get('rows', [])]}")
    res["pass"] = bool(ok)
    return res


def stage_regression(log) -> dict[str, Any]:
    """Layer 8: full pytest suite, 0 failures."""

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=line", "-p", "no:cacheprovider"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=7200)
    tail = "\n".join(proc.stdout.strip().splitlines()[-15:])
    log(f"pytest exit={proc.returncode}\n{tail}")
    return {"exit_code": proc.returncode, "tail": tail,
            "pass": proc.returncode == 0}


def run_settle_wave(gas_cfg, proto, workers, ckpt, log,
                    branches=BRANCHES) -> dict[str, Any]:
    thetas = [float(t) for t in proto["theta_points"]]
    payloads = []
    for br in branches:
        for th in [0.0] + thetas:
            payloads.append({
                "worker_kind": "sb_settle", "label": f"{br}_th{th:g}",
                "branch": br, "theta_dc": th, "gas_cfg": gas_cfg,
                "n_phys": proto["n_phys"], "nx": proto["nx"],
                "settle_periods": proto["settle_periods"],
                "samples_per_period": proto["samples_per_period"],
                "ckpt_dir": str(ckpt)})
    settles = execute_cases(payloads, workers, log, worker=_dispatch)
    for lbl, run in settles.items():
        if "worker_exception" in run or not run.get("finite"):
            log(f"settle {lbl}: DEAD ({run.get('worker_exception', 'non-finite')})")
            continue
        log(f"settle {lbl}: stat={run['stationarity_per_period']:.2e} "
            f"dc={run['dc_closure_rel']:.2e} col={run['column_replication_rel']:.2e} "
            f"ens={run['ensemble']}")
    return settles


def settle_legality(settles, proto, log) -> dict[str, Any]:
    """Distinguish HARD death (non-finite / worker exception -> abort) from
    SOFT gate misses (finite, ensemble-labelled -> STRICT_B_BASESTATE_MISMATCH
    recorded, chain continues archived per design section 5)."""

    thetas = [float(t) for t in proto["theta_points"]]
    rows, ok, hard_dead = {}, True, False
    for br in BRANCHES:
        for th in [0.0] + thetas:
            lbl = f"{br}_th{th:g}"
            run = settles.get(lbl, {})
            if "worker_exception" in run or not run.get("finite"):
                rows[lbl] = {"pass": False, "hard_dead": True,
                             "reason": run.get("worker_exception", "dead")}
                ok = False
                hard_dead = True
                continue
            row = {
                "stationarity": run["stationarity_per_period"],
                "dc_closure": run["dc_closure_rel"],
                "column_replication": run["column_replication_rel"],
                "ensemble_pass": run["ensemble"]["pass"],
            }
            row["pass"] = bool(
                run["stationarity_per_period"] <= GATE_STATIONARITY
                and (th == 0.0 or run["dc_closure_rel"] <= GATE_DC_CLOSURE)
                and run["column_replication_rel"] <= LINE_TOPOLOGY
                and run["ensemble"]["pass"]
                and math.isfinite(run["mass_drift_settle"]))
            rows[lbl] = row
            ok = ok and row["pass"]
    rows["pass"] = bool(ok)
    rows["hard_dead"] = bool(hard_dead)
    if not ok:
        log("settle legality: FAILED rows present"
            + (" (HARD death)" if hard_dead else
               " (soft gate miss — STRICT_B_BASESTATE_MISMATCH recorded, "
               "chain continues archived)"))
    return rows


def stage_hot(gas_cfg, proto, workers, ckpt, log, mode: str,
              g0_admitted: bool) -> dict[str, Any]:
    """Layer 9: hot points, both branches; PROD anchor via wallfix reuse."""

    thetas = [float(t) for t in proto["theta_points"]]
    out: dict[str, Any] = {"thetas": [f"{t:g}" for t in thetas]}

    # STRICT settles (both branches; G0 hot only if admitted)
    branches = [BRANCH_CONST_G] + ([BRANCH_G0] if g0_admitted else [])
    out["branches_run"] = branches
    settles = run_settle_wave(gas_cfg, proto, workers, ckpt, log,
                              branches=branches)
    leg = settle_legality(settles, proto, log)
    out["settle_legality"] = {k: v for k, v in leg.items() if k != "pass"}
    if leg.get("hard_dead"):
        out["stage_verdict"] = "LEGALITY_FAILED"
        out["label"] = "STRICT_B_SETTLE_DEAD"
        return out
    if not leg["pass"]:
        out.setdefault("labels", []).append("STRICT_B_BASESTATE_MISMATCH")

    # PROD anchor payloads (wallfix workers + authoritative checkpoints)
    wallfix_mode = "auth" if mode == "auth" else "smoke"
    wallfix_ck = REPO_ROOT / (WALLFIX_CKPT_AUTH if wallfix_mode == "auth"
                              else WALLFIX_CKPT_SMOKE)
    hs_rows = 48 if wallfix_mode == "auth" else 12
    prod_settle_payloads = []
    for th in [0.0] + thetas:
        prod_settle_payloads.append({
            "worker_kind": "prod_settle", "label": f"PROD_th{th:g}",
            "variant": "PROD", "theta_dc": th, "gas_cfg": gas_cfg,
            "ny": 2 * hs_rows, "nx": proto["nx"],
            "settle_periods": proto["settle_periods"],
            "samples_per_period": proto["samples_per_period"],
            "ckpt_dir": str(wallfix_ck)})
    prod_settles = execute_cases(prod_settle_payloads, workers, log,
                                 worker=_dispatch)

    # tangent wave
    tang_payloads = []
    prod_cold = prod_settles.get("PROD_th0")
    if prod_cold is None or not prod_cold.get("finite"):
        out["stage_verdict"] = "LEGALITY_FAILED"
        out["label"] = "PROD_ANCHOR_DEAD"
        return out
    tang_payloads.append({
        "worker_kind": "prod_tangent", "label": f"PROD_h{H_JVP:g}_cold",
        "variant": "PROD", "h": H_JVP, "gas_cfg": gas_cfg,
        "ny": 2 * hs_rows, "nx": proto["nx"], "hot_run": prod_cold,
        "cold_run": prod_cold, "drive_periods": proto["drive_periods"],
        "samples_per_period": proto["samples_per_period"],
        "fit_skip_periods": proto["fit_skip_periods"],
        "ckpt_dir": str(wallfix_ck)})
    for th in thetas:
        tang_payloads.append({
            "worker_kind": "prod_tangent",
            "label": f"PROD_th{th:g}_h{H_JVP:g}_hot",
            "variant": "PROD", "h": H_JVP, "gas_cfg": gas_cfg,
            "ny": 2 * hs_rows, "nx": proto["nx"],
            "hot_run": prod_settles[f"PROD_th{th:g}"], "cold_run": prod_cold,
            "drive_periods": proto["drive_periods"],
            "samples_per_period": proto["samples_per_period"],
            "fit_skip_periods": proto["fit_skip_periods"],
            "ckpt_dir": str(wallfix_ck)})
    for br in branches:
        cold_run = settles[f"{br}_th0"]
        base = {"worker_kind": "sb_tangent", "branch": br, "h": H_JVP,
                "gas_cfg": gas_cfg, "n_phys": proto["n_phys"],
                "nx": proto["nx"], "cold_run": cold_run,
                "drive_periods": proto["drive_periods"],
                "samples_per_period": proto["samples_per_period"],
                "fit_skip_periods": proto["fit_skip_periods"],
                "ckpt_dir": str(ckpt)}
        tang_payloads.append({**base, "label": f"{br}_h{H_JVP:g}_cold",
                              "hot_run": cold_run})
        for th in thetas:
            tang_payloads.append({**base, "label": f"{br}_th{th:g}_h{H_JVP:g}_hot",
                                  "hot_run": settles[f"{br}_th{th:g}"]})
    tangs = execute_cases(tang_payloads, workers, log, worker=_dispatch)

    # audits + rows
    def _leg(lbl, fails):
        r = tangs.get(lbl, {})
        if "Y" not in r:
            fails.append(f"{lbl}: missing/failed")
            return None
        a = r["audits"]
        if not (a["mass_tangent_rel_worst"] <= GATE_V5_MASS
                and a["energy_account_rel_worst"] <= GATE_V5_ENERGY
                and r["r_f_worst"] <= GATE_R_F):
            fails.append(f"{lbl}: audit ({a}, r_f={r['r_f_worst']:.1e})")
            return None
        return r

    rows: dict[str, Any] = {}
    fails: list[str] = []
    for name in ["PROD"] + list(branches):
        per: dict[str, Any] = {}
        rc = _leg(f"{name}_h{H_JVP:g}_cold", fails)
        if rc is not None:
            yc = complex(rc["Y"]["re"], rc["Y"]["im"])
            per["Y0"] = {"re": yc.real, "im": yc.imag, "abs": abs(yc)}
            for th in thetas:
                rh = _leg(f"{name}_th{th:g}_h{H_JVP:g}_hot", fails)
                if rh is not None:
                    per[f"{th:g}"] = _dop(complex(rh["Y"]["re"], rh["Y"]["im"]), yc)
        rows[name] = per
        shown = {k: (round(v["d_op_pct"], 4) if isinstance(v, dict)
                     and "d_op_pct" in v else v)
                 for k, v in per.items() if k != "Y0"}
        log(f"{name}: {shown}")
    out["tangent_failures"] = fails
    out["rows"] = rows

    # PROD anchor vs frozen TAN
    anchor, a_ok = {}, True
    for th in thetas:
        key = f"{th:g}"
        if key not in rows.get("PROD", {}):
            a_ok = False
            continue
        dev = abs(rows["PROD"][key]["d_op_pct"] - TAN_DOP_PCT[th])
        anchor[key] = {"d_op_pct": rows["PROD"][key]["d_op_pct"],
                       "tan_ref_pct": TAN_DOP_PCT[th], "dev_pp": dev,
                       "pass": bool(dev <= LINE_PROD_ANCHOR_PP)}
        a_ok = a_ok and anchor[key]["pass"]
        log(f"PROD anchor th={th:g}: dev={dev:.5f}pp")
    out["prod_anchor"] = anchor
    if not a_ok or fails:
        out["stage_verdict"] = "LEGALITY_FAILED"
        return out

    # classification (auth caliber only; smoke is screening)
    cls = {}
    for br in branches:
        if all(f"{th:g}" in rows.get(br, {}) for th in thetas):
            branch_rows = {th: rows[br][f"{th:g}"] for th in thetas}
            prod_rows = {th: rows["PROD"][f"{th:g}"] for th in thetas}
            c = classify_strict(branch_rows, prod_rows, thetas)
            label = f"STRICT_B_{c['label']}"
            if br == BRANCH_CONST_G:
                label += "_CONTROL"
            if mode != "auth":
                label += "_SMOKE_SCREENING"   # steep rig, never a verdict
            c["label"] = label
            cls[br] = c
            log(f"classify[{br}]: {c}")
        else:
            cls[br] = {"label": "STRICT_B_HOT_INCOMPLETE"}
    out["classification"] = cls
    out["stage_verdict"] = "COMPLETED"
    return out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

PREFLIGHT_STAGES = ("structural", "slab", "soak", "cold", "admission",
                    "admission_ac", "jvp", "regression")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="D1 strict candidate-B measurement (D0-7)")
    ap.add_argument("--mode", choices=("smoke", "auth", "full"), default="smoke")
    ap.add_argument("--stage", choices=("preflight", "hot", "all"),
                    default="preflight",
                    help="preflight = layers 1-8; hot = layer 9 (requires a "
                         "green preflight state file); all = both")
    ap.add_argument("--only-stages", default=None,
                    help="comma-separated subset of preflight stages to run "
                         "(machine-split dispatch, e.g. 'soak' on machine B; "
                         "the shared state file is only written by a FULL "
                         "preflight pass on the machine that will run hot)")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--output-root", default=None)
    args = ap.parse_args()

    workers = (args.workers if args.workers is not None
               else max(1, (os.cpu_count() or 4) - 2))
    base_cfg = load_config(REPO_ROOT / GAS_CONFIG)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = (Path(args.output_root) if args.output_root
                else REPO_ROOT / "results" / "phase5" / "faceflux_strict_b")
    cfg_sha8 = sha256_file(REPO_ROOT / GAS_CONFIG)[:8]
    log = lambda m: print(f"[{UNIT}] {m}", flush=True)  # noqa: E731

    modes = ["smoke", "auth"] if args.mode == "full" else [args.mode]
    verdict = "COMPLETED"
    for mode in modes:
        proto = PROTO[mode]
        out_dir = out_root / f"{run_id}_{mode}"
        out_dir.mkdir(parents=True, exist_ok=True)
        ckpt = out_root / f"checkpoints_{mode}_{cfg_sha8}_strictb"
        ckpt.mkdir(parents=True, exist_ok=True)
        state_path = out_root / f"preflight_state_{mode}_{cfg_sha8}.json"

        summary: dict[str, Any] = {
            "unit": UNIT, "run_id": run_id, "mode": mode, "stage_arg": args.stage,
            "design": "docs/Phase_5/strict_faceflux_candidate_b_design_v1.0.md",
            "protocol": {
                "gas_config": GAS_CONFIG, "frequency_Hz": FREQUENCY_HZ,
                "h_jvp": H_JVP, "h_ladder_jvp": H_LADDER_JVP,
                "eps_g_ladder": EPS_G_LADDER, "proto": proto,
                "lines": {
                    "topology": LINE_TOPOLOGY,
                    "wallpos_finest": LINE_WALLPOS_FINEST,
                    "soak": {"periods": SOAK_PERIODS, "pert_amp": SOAK_PERT_AMP,
                             "envelope": SOAK_ENVELOPE_FACTOR,
                             "drift": SOAK_DRIFT},
                    "hotdc": {"periods": HOTDC_PERIODS,
                              "stationarity": HOTDC_STATIONARITY,
                              "closure": HOTDC_FACE_CLOSURE,
                              "a_late": [A_LATE_FLOOR, A_LATE_FACTOR]},
                    "cold_anchor": {"amp": LINE_COLD_AMP_REL,
                                    "phase_deg": LINE_COLD_PHASE_DEG,
                                    "y0_prod_frozen": [Y0_PROD_COLD.real,
                                                       Y0_PROD_COLD.imag]},
                    "admission": {"steady": ADM_STEADY_REL,
                                  "y_amp": ADM_Y_AMP_REL,
                                  "y_phase_deg": ADM_Y_PHASE_DEG,
                                  "n_ladder": ADM_N_LADDER},
                    "jvp": {"odd": JVP_ODD_PAIRWISE, "even": JVP_EVEN_RATIO,
                            "even_guard": JVP_EVEN_GUARD,
                            "identity": JVP_IDENTITY},
                    "ensemble": {"cold_mass": ENS_COLD_MASS_REL,
                                 "hot_mass": ENS_HOT_MASS_REL,
                                 "theta_dc": ENS_HOT_THETADC_REL,
                                 "pressure": ENS_HOT_PRESSURE_REL},
                    "prod_anchor_pp": LINE_PROD_ANCHOR_PP,
                    "class": {"nsf_band_pp": CLASS_NSF_BAND_PP,
                              "move_frac": CLASS_MOVE_FRAC},
                },
            },
            "external_references": {
                "tan_dop_pct": {f"{k:g}": v for k, v in TAN_DOP_PCT.items()},
                "nsf_g0_dop_pct": {f"{k:g}": v for k, v in NSF_G0_DOP_PCT.items()},
                "prod_cold_anchor_provenance":
                    "wallfix auth checkpoint tangent_PROD_h5e-05_cold.json "
                    "(run 20260811T085347Z_auth, machine A)",
            },
            "machine": {"node": platform.node(), "platform": platform.platform(),
                        "python": sys.version.split()[0],
                        "numpy": np.__version__,
                        "git_commit": _git_commit(), "workers": workers},
        }

        def _dump():
            (out_dir / "summary.json").write_text(
                json.dumps(summary, indent=1, default=str), encoding="utf-8")

        log(f"run {run_id} mode={mode} stage={args.stage} workers={workers}")
        log("judgement frozen (module docstring + constants block)")

        mode_verdict = "COMPLETED"
        settles_shared: dict[str, Any] = {}

        if args.stage in ("preflight", "all"):
            # settle wave needed by soak/cold/jvp stages
            log("---- settle wave (both branches) ----")
            settles_shared = run_settle_wave(base_cfg, proto, workers, ckpt, log)
            leg = settle_legality(settles_shared, proto, log)
            summary["settle_legality"] = {k: v for k, v in leg.items()
                                          if k != "pass"}
            _dump()
            settle_green = bool(leg["pass"])
            if not settle_green:
                if leg.get("hard_dead"):
                    summary["verdict"] = "LEGALITY_FAILED"
                    summary["label"] = "STRICT_B_SETTLE_DEAD"
                    _dump()
                    log("settle HARD death — aborting mode")
                    verdict = "LEGALITY_FAILED"
                    continue
                summary.setdefault("labels", []).append(
                    "STRICT_B_BASESTATE_MISMATCH")
                log("settle soft gate miss — STRICT_B_BASESTATE_MISMATCH "
                    "recorded; chain continues (archived semantics, design "
                    "section 5)")

            # cold tangent needed for the layer-4 anchor
            log("---- cold tangent (CONST_G) ----")
            cold_run = settles_shared["CONST_G_th0"]
            tangs_cold = execute_cases([{
                "worker_kind": "sb_tangent", "label": f"CONST_G_h{H_JVP:g}_cold",
                "branch": BRANCH_CONST_G, "h": H_JVP, "gas_cfg": base_cfg,
                "n_phys": proto["n_phys"], "nx": proto["nx"],
                "hot_run": cold_run, "cold_run": cold_run,
                "drive_periods": proto["drive_periods"],
                "samples_per_period": proto["samples_per_period"],
                "fit_skip_periods": proto["fit_skip_periods"],
                "ckpt_dir": str(ckpt)}], workers, log, worker=_dispatch)

            stage_results: dict[str, Any] = {}
            aborted = False
            only = ([s.strip() for s in args.only_stages.split(",") if s.strip()]
                    if args.only_stages else None)
            if only:
                unknown = set(only) - set(PREFLIGHT_STAGES)
                if unknown:
                    raise SystemExit(f"unknown stages: {sorted(unknown)}")
            for st in PREFLIGHT_STAGES:
                if only and st not in only:
                    continue
                log(f"---- stage {st} ----")
                if st == "structural":
                    r = stage_structural(base_cfg, proto, log)
                elif st == "slab":
                    r = stage_slab(base_cfg, proto, workers, ckpt, log)
                elif st == "soak":
                    r = stage_soak(base_cfg, proto, workers, ckpt, log,
                                   settles_shared)
                elif st == "cold":
                    r = stage_cold(base_cfg, proto, workers, ckpt, log,
                                   settles_shared, tangs_cold)
                elif st == "admission":
                    r = stage_admission(base_cfg, proto, workers, ckpt, log)
                elif st == "admission_ac":
                    r = stage_admission_ac(base_cfg, proto, workers, ckpt, log)
                elif st == "jvp":
                    r = stage_jvp(base_cfg, proto, workers, ckpt, log,
                                  settles_shared)
                elif st == "regression":
                    r = stage_regression(log)
                stage_results[st] = r
                summary[f"stage_{st}"] = r
                _dump()
                if not r.get("pass"):
                    label = {"structural": "TOPOLOGY_INVALID",
                             "slab": "STRICT_B_WALLPOS_FAILED",
                             "soak": "STRICT_B_SOAK_FAILED",
                             "cold": "STRICT_B_COLD_ILLEGAL",
                             "admission": "STRICT_B_G0_ADMISSION_FAILED",
                             "admission_ac": "STRICT_B_G0_ADMISSION_FAILED",
                             "jvp": "STRICT_B_JVP_FAILED",
                             "regression": "PRODUCTION_REGRESSION_FAILED",
                             }[st]
                    summary.setdefault("labels", []).append(label)
                    if st in ("admission", "admission_ac"):
                        # gates ONLY the G0 branch (design sections 3/6);
                        # the CONST_G control chain continues either mode
                        log(f"stage {st} FAILED ({label}) — G0 branch not "
                            "admitted; CONST_G control chain continues")
                    elif mode == "auth":
                        mode_verdict = "LEGALITY_FAILED"
                        log(f"stage {st} FAILED ({label}) — aborting preflight")
                        aborted = True
                        break
                    else:
                        log(f"stage {st} FAILED ({label}) — smoke mode records "
                            "and continues (no design gates at smoke caliber)")
            g0_admitted = bool(
                stage_results.get("admission", {}).get("pass")
                and stage_results.get("admission_ac", {}).get("pass"))
            # design section 3/6: the admission stages gate ONLY the G0
            # branch's hot points; the CONST_G control branch (and the hot
            # stage itself) needs every OTHER layer green.
            core_stages = [st for st in PREFLIGHT_STAGES
                           if st not in ("admission", "admission_ac")]
            preflight_green = (settle_green and not aborted) and all(
                stage_results.get(st, {}).get("pass") for st in core_stages)
            if only:
                # machine-split partial pass: never write the shared state
                # (the hot-machine's FULL pass aggregates via checkpoints)
                summary["partial_stages"] = only
                log(f"partial pass ({only}) — state file NOT written")
            else:
                state = {"run_id": run_id, "mode": mode,
                         "git_commit": _git_commit(),
                         "preflight_green": bool(preflight_green),
                         "settle_green": bool(settle_green),
                         "g0_admitted": g0_admitted,
                         "stages": {st: bool(stage_results.get(st, {}).get("pass"))
                                    for st in PREFLIGHT_STAGES}}
                state_path.write_text(json.dumps(state, indent=1),
                                      encoding="utf-8")
                summary["preflight_state"] = state
                log(f"preflight state -> {state_path}: green={preflight_green} "
                    f"g0_admitted={g0_admitted}")
            _dump()

        if args.stage in ("hot", "all") and mode_verdict == "COMPLETED":
            if not state_path.exists():
                log("HOT REFUSED: no preflight state file")
                summary["stage_hot"] = {"stage_verdict": "REFUSED_NO_PREFLIGHT"}
                mode_verdict = "LEGALITY_FAILED"
            else:
                state = json.loads(state_path.read_text(encoding="utf-8"))
                # design section 5: a failed earlier layer does NOT abort the
                # chain — later results are ARCHIVED, never mechanism-read.
                # A failed cold anchor additionally marks the hot points
                # uninterpretable (design 6.2).  Interpretation authority is
                # carried entirely by the stamp below.
                log("---- stage hot (layer 9) ----")
                r = stage_hot(base_cfg, proto, workers, ckpt, log, mode,
                              bool(state.get("g0_admitted")))
                green = bool(state.get("preflight_green"))
                cold_ok = bool(state.get("stages", {}).get("cold"))
                if mode == "auth" and r.get("stage_verdict") == "COMPLETED":
                    if green:
                        r["validation_stamp"] = "STRICT_B_SCIENTIFICALLY_VALIDATED"
                    elif not cold_ok:
                        r["validation_stamp"] = ("STRICT_B_HOT_ARCHIVED_"
                                                 "COLD_ILLEGAL_UNINTERPRETABLE")
                    else:
                        r["validation_stamp"] = ("STRICT_B_HOT_ARCHIVED_"
                                                 "PREFLIGHT_INCOMPLETE")
                    if not green:
                        # archived numbers must not carry verdict labels
                        for br, c in (r.get("classification") or {}).items():
                            if isinstance(c, dict) and "label" in c:
                                c["label"] += "_ARCHIVED_ONLY"
                summary["stage_hot"] = r
                summary["preflight_state_at_hot"] = state
                if r.get("stage_verdict") != "COMPLETED":
                    mode_verdict = "LEGALITY_FAILED"
            _dump()

        summary["verdict"] = mode_verdict
        _dump()
        log(f"mode {mode} verdict={mode_verdict}  outputs -> {out_dir}")
        if mode_verdict != "COMPLETED":
            verdict = "LEGALITY_FAILED"
            if args.mode == "full":
                log("aborting full chain")
                break

    return 0 if verdict == "COMPLETED" else 1


if __name__ == "__main__":
    sys.exit(main())
