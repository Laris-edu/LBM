"""Cross-stack universality unit 1a — collision-operator structure axis (D0-7).

Question (plan docs/Phase_5/crossstack_1a_plan_v1.0.md, user directive
2026-08-14): every measurement of the finite-bias tangent artifact so far comes
from ONE collision stack (SMRT central-Hermite regularized stress + RR
closure).  A reviewer's first question is "general trap or property of your
operator?".  This unit answers the collision-structure half of it by
re-measuring d_OP with the collision changed and everything else -- production
v1.1 wall, canonical tent geometry, 10 kHz, dx2p6, frozen JAB tangent chain,
settle/drive windows -- held fixed.

TWO AXES, one instrument:

  1a-BGK  the textbook operator: ``core/collision_bgk.py``, two relaxation
          times, (tau_f, tau_g) DERIVED (never tuned) from the frozen mapping
          so nu_lu and alpha_lu -- hence delta_T and H_s/delta_T -- are
          production's.  Plan section 3 pre-registers the fallback if it is
          unstable: record the instability, keep it in the report as a
          methodological result, move the main path to 1a-CFG, and NEVER touch
          a production frozen quantity to stabilise it.
  1a-CFG  the supported configuration axis: the deviatoric-stress closure and
          the trace/bulk channel, plus their combination (the closest available
          analogue of a textbook regularized-BGK closure) and one structurally
          inert control.

FROZEN JUDGEMENT (constants below; registered before any variant hot number):

  aliveness    per variant, one-collide max-abs relative difference vs PROD on
               the seeded smoke state >= 1e-6 (dead-key guard, ghost-scan
               caliber).  A variant failing this is a dead key: archived,
               excluded from evidence.
  live key     cold |Y0| relative shift vs PROD >= 1e-4 (plan section 5).  Below
               the line the switch is structurally inert on this rig and its
               d_OP carries NO discriminating power -- archived, not evidence.
               (Phase_3 "smokes pass by construction" lesson.)
  anchor       auth PROD d_OP within 0.2 pp of the frozen TAN references
               (V4 caliber).  Failure => whole stage LEGALITY_FAILED.
  legality     JAB gates verbatim: stationarity <=1e-3, dc_closure <=1e-3,
               r_F <=1e-5, V5 mass <=1e-7, V5 energy account <=1e-5.
  stability    pre-flight: spectral radius of the linearized one-step operator
               on a wall-free periodic box <= 1 + 1e-6.
  class        auth grid, both hot points Theta in {0.05, 0.10} must agree:
                 CROSSSTACK_ROBUST    both still negative, |delta d_OP| < 1.0 pp
                 CROSSSTACK_SENSITIVE both still negative, |delta d_OP| >= 1.0 pp
                 CROSSSTACK_ABSENT    both flipped positive
                 CROSSSTACK_MIXED     the two points disagree
  caveats      (reported, never gating) cold |Y0| shift > 30% or alpha_eff
               shift > 2% vs PROD => the variant's d_OP is a CROSS-CALIBRATION
               comparison and must be quoted as such.  Plan section 5: it is
               forbidden to assume a base-state-independent multiplicative
               error cancels in the ratio -- that assumption is already
               falsified by the DC-arm raw/corrected pair.

Unstable or illegal variants are archived as MEASURED_UNSTABLE_OR_ILLEGAL and
dropped from the tangent wave (A5 chi-endpoint precedent); only a dead PROD
anchor fails the stage.

DIAGNOSTIC ONLY (D0-7): no gate claims, no production validity claim for any
variant, production collision/solver/tangent modules untouched.  Verdict
vocabulary COMPLETED / LEGALITY_FAILED + the labels above.

Modes: preflight (stability + transport + aliveness only), smoke (machinery
validation on the JAB smoke grid -- does NOT reproduce the production sign),
auth (production grid, the only judgement grid), full (all three in order).
Per-case checkpoints + identity-matching resume, shared per mode+config digest.
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

from boundary.wall_thermal_mass_neutral import (  # noqa: E402
    make_symmetric_mass_neutral_band_callback,
    make_symmetric_mass_neutral_wall_callback,
)
from core.collision_bgk import BgkParams, bgk_params_matching, collide_fg_bgk  # noqa: E402
from core.collision_smrt import collide_fg  # noqa: E402
from core.macroscopic import recover_macro  # noqa: E402
from core.solver import GasSolver2D  # noqa: E402
from core.tangent_bgk import (  # noqa: E402
    COLLISION_BGK,
    COLLISION_PROD,
    CrossStackSolver2D,
    CrossStackTangentOperator,
    compute_stage_bases_crossstack,
    measure_mode_decay,
    one_step_spectral_radius,
)
from core.tangent_step import propagate_tangent  # noqa: E402
from scripts.phase2_m2_verification import load_config, sha256_file  # noqa: E402
from scripts.phase5_g1a_amplitude_envelope import execute_cases  # noqa: E402
from scripts.phase5_g4a_dc_basestate import (  # noqa: E402
    conduction_seed,
    fit_admittance,
    make_energy_audited_band,
    tent_bvp_reference,
)
from scripts.phase5_wallfix_arbitration import (  # noqa: E402
    FREQUENCY_HZ,
    GAS_CONFIG,
    GATE_DC_CLOSURE,
    GATE_R_F,
    GATE_STATIONARITY,
    GATE_V5_ENERGY,
    GATE_V5_MASS,
    NSF_G0_DOP_PCT,
    PROTO,
    TAN_DOP_PCT,
)
from scripts.phase5_wp4_jacobian_ablation import snapshot_to_base  # noqa: E402

UNIT = "CROSSSTACK-1A"

# ---------------------------------------------------------------------------
# frozen variant catalogue (collision structure only; wall/geometry untouched)
# ---------------------------------------------------------------------------
# Each entry: (collision branch, collision-config overrides, one-line meaning).
# PROD overrides are EMPTY by construction -- the anchor must be the frozen
# production collision bit for bit.
VARIANTS: dict[str, dict[str, Any]] = {
    "PROD": {
        "collision": COLLISION_PROD, "cfg": {},
        "meaning": "production SMRT central-Hermite regularized stress (anchor)",
    },
    "BGK": {
        "collision": COLLISION_BGK, "cfg": {},
        "meaning": "textbook two-relaxation-time BGK, (tau_f,tau_g) derived from "
                   "the frozen nu_lu/alpha_lu",
    },
    "DEVMEAS": {
        "collision": COLLISION_PROD,
        "cfg": {"deviatoric_stress_policy": "measured"},
        "meaning": "deviatoric stress rebuilt from the MEASURED non-equilibrium "
                   "second moment instead of the strain rate",
    },
    "TRTAU22": {
        "collision": COLLISION_PROD,
        "cfg": {"trace_bulk_policy": "tau22"},
        "meaning": "trace/bulk channel relaxed at tau22 instead of the "
                   "ghost-orthogonal local hydrodynamic reconstruction",
    },
    "TRZERO": {
        "collision": COLLISION_PROD,
        "cfg": {"trace_bulk_policy": "current_zero"},
        "meaning": "trace/bulk channel zeroed (D2Q37 transport-candidate baseline)",
    },
    "REGBGK": {
        "collision": COLLISION_PROD,
        "cfg": {"deviatoric_stress_policy": "measured",
                "trace_bulk_policy": "tau22"},
        "meaning": "both hydrodynamic channels from the measured non-equilibrium "
                   "moment = closest available analogue of a textbook "
                   "regularized-BGK closure",
    },
    "CTRL4TH": {
        "collision": COLLISION_PROD,
        "cfg": {"central_moment_closure": "fourth_order",
                "high_order_relaxation": 1.0},
        "meaning": "fourth_order at the full-regularization limit = structurally "
                   "INERT positive control for the live-key gate",
    },
}
DEFAULT_VARIANTS = list(VARIANTS)

# The trace policy 'calibrated' is NOT offered: with trace_bulk_scale=1.0 its
# factor is numerically identical to 'tau22' on this config, and it additionally
# demands a trace_bulk_calibration_id that does not exist for this stack.
# Inventing one would be fabricating a calibration.  The four excluded trace
# variants (*_laplacian / *_pressure_memory / *_two_channel / *_entropy_manifold)
# stay excluded -- PROJECT_CONTEXT section 3 counter-examples, not revivable.

# ---------------------------------------------------------------------------
# FROZEN JUDGEMENT LINES (registered before any variant hot number)
# ---------------------------------------------------------------------------
H_JVP = 5.0e-5                      # frozen JVP step (JAB/ghost-scan caliber)
LINE_ALIVENESS_REL = 1.0e-6         # dead-key guard on one collide vs PROD
LINE_LIVEKEY_Y0_REL = 1.0e-4        # plan section 5 live-key line (cold |Y0|)
LINE_ANCHOR_PP = 0.2                # auth PROD vs frozen TAN (V4 caliber)
LINE_CLASS_PP = 1.0                 # ROBUST/SENSITIVE split (plan section 5)
LINE_XCAL_Y0_REL = 0.30             # cross-calibration caveat on cold |Y0|
LINE_XCAL_ALPHA_REL = 0.02          # cross-calibration caveat on alpha_eff
LINE_BGK_COLD_ANCHOR_REL = 0.10     # plan section 5 BGK cold anchor (unused if BGK dies)
LINE_SPECTRAL_RADIUS = 1.0 + 1.0e-6  # linear stability line (pre-flight)
JAB1_SMOKE_DOP_PCT = 0.974          # smoke-grid soft anchor (JAB1 direction row)

# pre-flight geometry: k = 2*pi/64 is the CALIBRATION wavenumber this stack's dx
# was chosen to land the thermal feature on (config header); ny=96 is the auth
# box height.  The G0 authoritative table row at k=0.09817 is alpha_eff=6.495461e-3.
PREFLIGHT_TRANSPORT_NY = (64, 96)
G0_ALPHA_EFF_K64_LU = 6.495461e-3   # archive/M5_runs/g0_20260722T173919Z/property_table.csv
PREFLIGHT_SPECTRAL_NY = 8
PREFLIGHT_SPECTRAL_NX = 4
# BGK tau ladders for the stability map.  Branch A holds alpha_lu at the frozen
# production value (tau_g solved from tau_f); branch B is the Pr=1 line, which
# is where BGK can be pushed toward stability at the cost of alpha.
BGK_ALPHA_PRESERVING_TAU_F = (0.5932, 0.62, 0.65, 0.68, 0.70, 0.72, 0.73)
BGK_PR1_TAU = (0.6320, 0.70, 0.80, 0.90, 0.95, 1.00, 1.10, 1.20, 1.50)


# ---------------------------------------------------------------------------
# config plumbing
# ---------------------------------------------------------------------------

def variant_gas_cfg(base_cfg: dict, variant: str) -> dict:
    """Deep-copied gas config with ONLY the variant's collision keys changed."""

    if variant not in VARIANTS:
        raise ValueError(f"unknown variant: {variant!r}")
    cfg = copy.deepcopy(base_cfg)
    overrides = VARIANTS[variant]["cfg"]
    if overrides:
        cfg["collision"] = {**cfg["collision"], **overrides}
    return cfg


def variant_collision(variant: str) -> str:
    return VARIANTS[variant]["collision"]


def make_variant_solver(cfg: dict, variant: str) -> CrossStackSolver2D:
    """Solver for a variant; BGK gets the derived (tau_f, tau_g), never a tuned pair."""

    collision = variant_collision(variant)
    if collision == COLLISION_BGK:
        probe = copy.deepcopy(cfg)
        probe["numerics"] = {**probe["numerics"], "nx": 4, "ny": 8}
        params = bgk_params_matching(GasSolver2D(probe).mapping)
        return CrossStackSolver2D(cfg, collision=collision, bgk_params=params)
    return CrossStackSolver2D(cfg, collision=collision)


# ---------------------------------------------------------------------------
# pre-flight instruments
# ---------------------------------------------------------------------------

def aliveness_check(base_cfg: dict, variants: list[str]) -> dict[str, Any]:
    """Dead-key guard: each variant must change ONE collide output vs PROD."""

    def seeded(cfg: dict):
        c = copy.deepcopy(cfg)
        c["numerics"] = {**c["numerics"], "nx": 4, "ny": 24}
        s = GasSolver2D(c)
        th0 = float(s.mapping.theta_ref_lu)
        rho0 = float(s.mapping.lattice.rho_ref_lu)
        y = np.arange(24)
        prof = th0 * (1.0 + 0.05 * np.cos(2 * np.pi * y / 24))[:, None]
        theta = np.tile(prof, (1, 4))
        s.initialize_from_macro(rho0 * th0 / theta, np.zeros((24, 4, 2)), theta)
        s.step(5)
        return s

    ref_solver = seeded(base_cfg)
    f_seed, g_seed = ref_solver.f.copy(), ref_solver.g.copy()
    f_ref, _ = collide_fg(f_seed.copy(), g_seed.copy(), ref_solver.mapping,
                          lattice=ref_solver.lattice)
    scale = max(float(np.max(np.abs(f_ref))), 1e-300)
    rows: dict[str, Any] = {}
    for v in variants:
        cfg = variant_gas_cfg(base_cfg, v)
        c = copy.deepcopy(cfg)
        c["numerics"] = {**c["numerics"], "nx": 4, "ny": 24}
        solver = GasSolver2D(c)
        if variant_collision(v) == COLLISION_BGK:
            params = bgk_params_matching(solver.mapping)
            f_v, _ = collide_fg_bgk(f_seed.copy(), g_seed.copy(), solver.mapping,
                                    params, lattice=solver.lattice)
        else:
            f_v, _ = collide_fg(f_seed.copy(), g_seed.copy(), solver.mapping,
                                lattice=solver.lattice)
        rel = float(np.max(np.abs(f_v - f_ref))) / scale
        rows[v] = {"rel_diff_vs_prod": rel,
                   "live": bool(v == "PROD" or rel >= LINE_ALIVENESS_REL)}
    return rows


def bgk_stability_map(base_cfg: dict, log) -> dict[str, Any]:
    """Linear stability of the BGK branch on a wall-free periodic box.

    Two ladders (module constants): the alpha-preserving line -- every pair on
    it poses EXACTLY the production thermal problem -- and the Pr=1 line, along
    which alpha is allowed to drift.  Reports the spectral radius of the
    linearized one-step operator for each, plus the PROD reference.
    """

    probe = copy.deepcopy(base_cfg)
    probe["numerics"] = {**probe["numerics"], "nx": 4, "ny": 8}
    mapping = GasSolver2D(probe).mapping
    theta_t = float(mapping.theta_transport_lu)
    alpha_nom = float(mapping.alpha_lu)
    nu_nom = float(mapping.nu_lu)
    d, s_int = int(mapping.lattice.D), int(mapping.lattice.S)
    matched = bgk_params_matching(mapping)

    def spectral(params: BgkParams | None) -> dict[str, Any]:
        if params is None:
            factory = lambda c: CrossStackSolver2D(c, collision=COLLISION_PROD)  # noqa: E731
        else:
            factory = lambda c: CrossStackSolver2D(  # noqa: E731
                c, collision=COLLISION_BGK, bgk_params=params)
        return one_step_spectral_radius(factory, base_cfg,
                                        ny=PREFLIGHT_SPECTRAL_NY,
                                        nx=PREFLIGHT_SPECTRAL_NX)

    prod = spectral(None)
    log(f"spectral PROD: rho(J)={prod['spectral_radius']:.6f} "
        f"unstable_modes={prod['unstable_mode_count']} "
        f"fixed_point_resid={prod['fixed_point_residual']:.2e}")

    def tau_g_alpha_preserving(tau_f: float) -> float:
        return 0.5 + ((d + s_int + 2) * alpha_nom / theta_t
                      - (d + 2) * (tau_f - 0.5)) / s_int

    alpha_branch = []
    for tau_f in BGK_ALPHA_PRESERVING_TAU_F:
        tau_g = tau_g_alpha_preserving(tau_f)
        if tau_g <= 0.5:
            alpha_branch.append({"tau_f": tau_f, "tau_g": tau_g,
                                 "feasible": False})
            continue
        p = BgkParams(tau_f=tau_f, tau_g=tau_g, theta_transport_lu=theta_t,
                      D=d, S=s_int)
        r = spectral(p)
        row = {"tau_f": tau_f, "tau_g": tau_g, "feasible": True,
               "spectral_radius": r["spectral_radius"],
               "unstable_mode_count": r["unstable_mode_count"],
               "alpha_over_nominal": p.alpha_lu / alpha_nom,
               "nu_over_nominal": p.nu_lu / nu_nom,
               "retention_f": p.retention_f, "retention_g": p.retention_g,
               "stable": bool(r["spectral_radius"] <= LINE_SPECTRAL_RADIUS)}
        alpha_branch.append(row)
        log(f"spectral BGK alpha-preserving tau_f={tau_f:.4f} tau_g={tau_g:.4f}: "
            f"rho(J)={row['spectral_radius']:.6f} "
            f"-> {'STABLE' if row['stable'] else 'UNSTABLE'}")

    pr1_branch = []
    for tau in BGK_PR1_TAU:
        p = BgkParams(tau_f=tau, tau_g=tau, theta_transport_lu=theta_t,
                      D=d, S=s_int)
        r = spectral(p)
        row = {"tau": tau, "spectral_radius": r["spectral_radius"],
               "unstable_mode_count": r["unstable_mode_count"],
               "alpha_over_nominal": p.alpha_lu / alpha_nom,
               "nu_over_nominal": p.nu_lu / nu_nom,
               "retention": p.retention_f,
               "stable": bool(r["spectral_radius"] <= LINE_SPECTRAL_RADIUS)}
        pr1_branch.append(row)
        log(f"spectral BGK Pr=1 tau={tau:.4f}: rho(J)={row['spectral_radius']:.6f} "
            f"alpha/nom={row['alpha_over_nominal']:.3f} "
            f"-> {'STABLE' if row['stable'] else 'UNSTABLE'}")

    feasible = [r for r in alpha_branch if r.get("feasible")]
    any_alpha_stable = any(r["stable"] for r in feasible)
    stable_pr1 = [r for r in pr1_branch if r["stable"]]
    verdict = ("BGK_USABLE_AT_PRODUCTION_PROBLEM" if any_alpha_stable
               else "BGK_LINEARLY_UNSTABLE_ON_THE_PRODUCTION_PROBLEM")
    return {
        "line_spectral_radius": LINE_SPECTRAL_RADIUS,
        "prod_reference": prod,
        "matched_params": matched.as_dict(),
        "alpha_preserving_branch": alpha_branch,
        "pr1_branch": pr1_branch,
        "alpha_preserving_tau_f_upper_bound": 0.5 + ((d + s_int + 2) * alpha_nom
                                                     / theta_t) / (d + 2),
        "min_spectral_radius_alpha_preserving": (
            min((r["spectral_radius"] for r in feasible), default=float("nan"))),
        "first_stable_pr1_tau": (stable_pr1[0]["tau"] if stable_pr1 else None),
        "first_stable_pr1_alpha_over_nominal": (
            stable_pr1[0]["alpha_over_nominal"] if stable_pr1 else None),
        "verdict": verdict,
    }


def _transport_worker(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Pool worker for the mode-decay transport probe (module level = picklable)."""

    p = payload
    cfg = p["gas_cfg"]
    variant = p["variant"]
    try:
        row = measure_mode_decay(
            lambda c: make_variant_solver(c, variant), cfg,
            channel=p["channel"], ny=int(p["ny"]), nx=4,
            steps=int(p["steps"]), sample_interval=max(1, int(p["steps"]) // 400),
            fit_start=max(int(p["steps"]) // 12, 10))
    except Exception as exc:  # noqa: BLE001 - a dead variant is a measurement
        return p["label"], {"worker_exception": f"{type(exc).__name__}: {exc}",
                            "finite": False}
    return p["label"], row


def transport_probe(base_cfg: dict, variants: list[str], workers: int,
                    log) -> dict[str, Any]:
    """alpha_eff (and nu_eff, archived) per variant through ONE instrument.

    The probe is the frozen G0/P2-5 recipe with the solver injected and is
    anchored bitwise against ``measure_thermal_diffusion_direction`` in the
    contract tests, and against the archived G0 table row at the calibration
    wavenumber here.
    """

    probe = copy.deepcopy(base_cfg)
    probe["numerics"] = {**probe["numerics"], "nx": 4, "ny": 8}
    mapping = GasSolver2D(probe).mapping
    alpha_nom = float(mapping.alpha_lu)
    nu_nom = float(mapping.nu_lu)

    payloads = []
    for ny in PREFLIGHT_TRANSPORT_NY:
        k = 2.0 * math.pi / ny
        for channel, nom in (("thermal", alpha_nom), ("shear", nu_nom)):
            steps = max(int(0.9 / (nom * k * k)), 300)
            for v in variants:
                payloads.append({"label": f"{v}_{channel}_ny{ny}", "variant": v,
                                 "channel": channel, "ny": ny, "steps": steps,
                                 "gas_cfg": variant_gas_cfg(base_cfg, v)})
    raw = execute_cases(payloads, workers, log, worker=_transport_worker)

    rows: dict[str, Any] = {}
    for v in variants:
        entry: dict[str, Any] = {}
        for ny in PREFLIGHT_TRANSPORT_NY:
            for channel in ("thermal", "shear"):
                r = raw.get(f"{v}_{channel}_ny{ny}", {})
                entry[f"{channel}_ny{ny}"] = {
                    "measured_lu": r.get("measured_lu"),
                    "finite": bool(r.get("finite", False)),
                    "k_lu": r.get("k_lu"),
                    "error": r.get("worker_exception"),
                }
        rows[v] = entry
    prod64 = rows.get("PROD", {}).get("thermal_ny64", {}).get("measured_lu")
    for v in variants:
        a = rows[v].get("thermal_ny64", {}).get("measured_lu")
        shift = (float(a) / float(prod64) - 1.0
                 if (a and prod64 and np.isfinite(a) and np.isfinite(prod64))
                 else float("nan"))
        rows[v]["alpha_eff_shift_vs_prod"] = shift
        rows[v]["cross_calibration_caveat"] = bool(
            np.isfinite(shift) and abs(shift) > LINE_XCAL_ALPHA_REL)
        log(f"transport {v}: alpha_eff(k=cal)={a} shift_vs_PROD={shift:+.4f} "
            f"caveat={rows[v]['cross_calibration_caveat']}")
    g0_dev = (abs(float(prod64) / G0_ALPHA_EFF_K64_LU - 1.0)
              if prod64 and np.isfinite(prod64) else float("nan"))
    log(f"transport instrument anchor: PROD alpha_eff(k=cal) vs archived G0 row "
        f"{G0_ALPHA_EFF_K64_LU:.6e} -> dev={g0_dev:.4e}")
    return {"alpha_nominal_lu": alpha_nom, "nu_nominal_lu": nu_nom,
            "g0_reference_alpha_eff_k64_lu": G0_ALPHA_EFF_K64_LU,
            "prod_vs_g0_table_rel_dev": g0_dev,
            "line_cross_calibration_alpha_rel": LINE_XCAL_ALPHA_REL,
            "by_variant": rows}


# ---------------------------------------------------------------------------
# settle (run_tent phase-1 replica with the collision selectable)
# ---------------------------------------------------------------------------

def settle_tent_crossstack(gas_cfg: dict, *, variant: str, ny: int, nx: int,
                           theta_dc: float, frequency_hz: float,
                           settle_periods: float,
                           samples_per_period: int) -> dict[str, Any]:
    """DC settle + snapshot; production v1.1 wall on both bands, unchanged.

    Faithful replica of ``scripts/phase5_g4a_dc_basestate.run_tent`` phase 1
    (same seed, same audited-band composition, same step count and legality
    metrics).  ``variant='PROD'`` is asserted bitwise against
    ``run_tent(..., eps_ac=0, snapshot=True)`` in the contract tests.
    """

    cfg = copy.deepcopy(gas_cfg)
    cfg["numerics"] = {**cfg["numerics"], "nx": int(nx), "ny": int(ny)}
    solver = make_variant_solver(cfg, variant)
    th0 = float(solver.mapping.theta_ref_lu)
    theta_amb = th0
    theta_hot_mean = th0 * (1.0 + float(theta_dc))
    rho0 = float(solver.mapping.lattice.rho_ref_lu)
    dt_s = float(solver.mapping.lattice.dt_s)
    lattice = solver.lattice
    D = int(solver.mapping.lattice.D)
    S = int(solver.mapping.lattice.S)
    hs = ny // 2
    steps_per_period = int(round(1.0 / (frequency_hz * dt_s)))
    sample_every = max(1, steps_per_period // int(samples_per_period))

    prof = conduction_seed(ny, theta_hot_mean, theta_amb)
    rho = rho0 * theta_amb / prof
    solver.initialize_from_macro(np.tile(rho[:, None], (1, nx)),
                                 np.zeros((ny, nx, 2)),
                                 np.tile(prof[:, None], (1, nx)))

    rec: dict[str, list[float]] = {}
    hot_inner = make_symmetric_mass_neutral_wall_callback(
        lambda _s: float(theta_hot_mean))
    sink_inner = make_symmetric_mass_neutral_band_callback(float(theta_amb), hs)
    hot_cb = make_energy_audited_band(hot_inner, rec, lattice, "hot")
    sink_cb = make_energy_audited_band(sink_inner, rec, lattice, "sink")

    def composed(**kw):
        f, g = hot_cb(**kw)
        kw2 = {**kw, "f_stream": f, "g_stream": g}
        return sink_cb(**kw2)

    n_settle = int(round(settle_periods * steps_per_period))
    stat_window = []
    mass_series = []
    for i in range(n_settle):
        solver.step(1, boundary_callback=composed)
        # cheap divergence trip: a variant that blows up must not burn a full
        # settle on NaNs.  Only ever fires on a non-finite state, so it cannot
        # change the numbers of a surviving case (bitwise PROD anchor intact).
        if i % sample_every == 0 and not np.all(np.isfinite(solver.f)):
            return {"finite": False, "phase": "settle", "step": i,
                    "reason": "non-finite populations during settle"}
        if i >= n_settle - steps_per_period and (i % sample_every == 0):
            m = recover_macro(solver.f, solver.g, D=D, S=S, lattice=lattice)
            prof_i = np.mean(m.theta, axis=1)
            if not np.all(np.isfinite(prof_i)):
                return {"finite": False, "phase": "settle", "step": i}
            stat_window.append(prof_i)
            mass_series.append(float(np.sum(solver.f)))
    stat = np.array(stat_window)
    base_profile = stat.mean(axis=0)
    stationarity = float(np.max(np.abs(stat[-1] - stat[0])) / theta_amb)
    per = steps_per_period
    q_hot_dc = float(np.mean(rec["hot_dE"][-per:]))
    q_sink_dc = float(np.mean(rec["sink_dE"][-per:]))
    dc_closure = abs(q_hot_dc + q_sink_dc) / max(abs(q_hot_dc), 1e-300)

    return {
        "finite": True, "ny": ny, "nx": nx, "hs": hs, "theta0": th0,
        "rho0": rho0, "dt_s": dt_s, "steps_per_period": steps_per_period,
        "stationarity_per_period": stationarity,
        "dc_closure_rel": dc_closure,
        "theta_dc_measured": float((base_profile[0] - theta_amb) / theta_amb),
        "q_hot_dc_lu": q_hot_dc, "q_sink_dc_lu": q_sink_dc,
        "mass_drift_settle": abs(mass_series[-1] / mass_series[0] - 1.0)
        if mass_series else float("nan"),
        "base_profile": base_profile,
        "snapshot": {
            "f": solver.f.copy(), "g": solver.g.copy(),
            "theta_hot_mean": float(theta_hot_mean),
            "theta_amb": float(theta_amb), "hs": int(hs),
            "ny": int(ny), "nx": int(nx),
            "theta_dc_target": float(theta_dc),
        },
    }


# ---------------------------------------------------------------------------
# picklable case workers
# ---------------------------------------------------------------------------

def _settle_ident(p: dict[str, Any]) -> dict[str, Any]:
    return {"variant": p["variant"], "theta_dc": float(p["theta_dc"]),
            "ny": int(p["ny"]), "nx": int(p["nx"]),
            "settle_periods": float(p["settle_periods"]),
            "samples_per_period": int(p["samples_per_period"])}


def _settle_worker(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    p = payload
    ident = _settle_ident(p)
    ck = (Path(p["ckpt_dir"]) / f"settle_{p['label']}.npz"
          if p.get("ckpt_dir") else None)
    if ck is not None and ck.exists():
        try:
            z = np.load(ck, allow_pickle=False)
            if json.loads(str(z["ident"])) == ident:
                meta = json.loads(str(z["meta"]))
                sident = json.loads(str(z["sident"]))
                return p["label"], {"finite": True, **meta,
                                    "snapshot": {"f": z["f"], "g": z["g"], **sident},
                                    "resumed_from_checkpoint": True}
        except Exception:  # noqa: BLE001 - stale/corrupt checkpoint -> recompute
            pass
    run = settle_tent_crossstack(
        p["gas_cfg"], variant=p["variant"], ny=p["ny"], nx=p["nx"],
        theta_dc=p["theta_dc"], frequency_hz=FREQUENCY_HZ,
        settle_periods=p["settle_periods"],
        samples_per_period=p["samples_per_period"])
    s = run.get("snapshot")
    if ck is not None and run.get("finite") and s is not None:
        tmp = ck.with_suffix(".tmp.npz")
        np.savez_compressed(
            tmp, f=s["f"], g=s["g"],
            meta=json.dumps({k: run[k] for k in (
                "stationarity_per_period", "dc_closure_rel",
                "theta_dc_measured", "mass_drift_settle", "steps_per_period")}),
            sident=json.dumps({k: s[k] for k in (
                "theta_hot_mean", "theta_amb", "hs", "ny", "nx",
                "theta_dc_target")}),
            ident=json.dumps(ident))
        os.replace(tmp, ck)
    return p["label"], run


def _tangent_worker(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    p = payload
    ident = {"variant": p["variant"], "h": float(p["h"]), "ny": int(p["ny"]),
             "nx": int(p["nx"]), "drive_periods": float(p["drive_periods"]),
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
    variant = p["variant"]
    collision = variant_collision(variant)
    cfg = copy.deepcopy(p["gas_cfg"])
    cfg["numerics"] = {**cfg["numerics"], "nx": int(p["nx"]), "ny": int(p["ny"])}
    solver = make_variant_solver(cfg, variant)
    bgk_params = solver.bgk_params if collision == COLLISION_BGK else None
    hot_base = snapshot_to_base(p["hot_run"])
    cold_base = snapshot_to_base(p["cold_run"])
    hot = compute_stage_bases_crossstack(solver, hot_base, collision=collision,
                                         bgk_params=bgk_params)
    cold = compute_stage_bases_crossstack(solver, cold_base, collision=collision,
                                          bgk_params=bgk_params)
    r_f_worst = max(hot.r_f, cold.r_f)
    op = CrossStackTangentOperator(solver, hot_base, hot, cold_base, cold,
                                   h=float(p["h"]), ablated=frozenset(),
                                   collision=collision, bgk_params=bgk_params)
    run = propagate_tangent(op, frequency_hz=FREQUENCY_HZ,
                            drive_periods=p["drive_periods"],
                            samples_per_period=p["samples_per_period"], log=None)
    fit = fit_admittance(run, FREQUENCY_HZ, p["fit_skip_periods"])
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


# ---------------------------------------------------------------------------
# pure analysis helpers (unit-tested)
# ---------------------------------------------------------------------------

def partition_variants(settles: dict[str, Any], variants: list[str],
                       thetas: list[float]) -> tuple[dict, dict]:
    """Per-variant settle legality partition (pure).

    A variant survives only if ALL its settles (cold + hot) exist, are finite
    and pass the JAB legality gates.  Same A5 chi-endpoint caliber as the ghost
    scan: a dead variant is an archived stability boundary, not a scan failure.
    """

    legality: dict[str, Any] = {}
    status: dict[str, dict] = {}
    for v in variants:
        ok = True
        reasons: list[str] = []
        for th in [0.0] + list(thetas):
            lbl = f"{v}_th{th:g}"
            run = settles.get(lbl, {})
            if "worker_exception" in run or not run.get("finite"):
                legality[lbl] = {"pass": False, "reason": run.get(
                    "worker_exception", "non-finite or missing settle")}
                ok = False
                reasons.append(f"{lbl}: {legality[lbl]['reason']}")
                continue
            row = {k: run[k] for k in (
                "stationarity_per_period", "dc_closure_rel",
                "theta_dc_measured", "mass_drift_settle")}
            row["pass"] = bool(
                run["stationarity_per_period"] <= GATE_STATIONARITY
                and (th == 0.0 or run["dc_closure_rel"] <= GATE_DC_CLOSURE)
                and math.isfinite(run["mass_drift_settle"]))
            legality[lbl] = row
            if not row["pass"]:
                ok = False
                reasons.append(f"{lbl}: legality gate")
        status[v] = {"ok": ok, "reason": "; ".join(reasons) or "all PASS"}
    return legality, status


def _dop(y_hot: complex, y_cold: complex) -> dict[str, float]:
    d = y_hot / y_cold
    return {"d_op_pct": (abs(d) - 1.0) * 100.0,
            "phase_deg": math.degrees(math.atan2(d.imag, d.real))}


def classify(rows: dict[str, dict], thetas: list[str]) -> dict[str, Any]:
    """Per-variant cross-stack classification against the PROD anchor (pure)."""

    base = rows.get("PROD")
    if base is None:
        return {"label": "NO_ANCHOR"}
    out: dict[str, Any] = {}
    for name, r in rows.items():
        if name == "PROD":
            continue
        pts = [t for t in thetas if t in r and t in base]
        if not pts:
            out[name] = {"label": "NO_POINTS"}
            continue
        deltas = [r[t]["d_op_pct"] - base[t]["d_op_pct"] for t in pts]
        values = [r[t]["d_op_pct"] for t in pts]
        y0_shift = r["Y0_abs"] / base["Y0_abs"] - 1.0
        if all(v > 0.0 for v in values):
            label = "CROSSSTACK_ABSENT"
        elif all(v < 0.0 for v in values):
            label = ("CROSSSTACK_ROBUST" if all(abs(x) < LINE_CLASS_PP for x in deltas)
                     else "CROSSSTACK_SENSITIVE")
        else:
            label = "CROSSSTACK_MIXED"
        live = bool(abs(y0_shift) >= LINE_LIVEKEY_Y0_REL)
        out[name] = {
            "label": label,
            "d_op_pct": [float(v) for v in values],
            "delta_dop_pp": [float(x) for x in deltas],
            "y0_abs_shift_rel": float(y0_shift),
            "live_key": live,
            "cross_calibration_caveat": bool(abs(y0_shift) > LINE_XCAL_Y0_REL),
            "evidence": live,
        }
    live_labels = [row["label"] for row in out.values()
                   if row.get("evidence") and row["label"].startswith("CROSSSTACK_")]
    if live_labels and all(x == "CROSSSTACK_ROBUST" for x in live_labels):
        family = "CROSSSTACK_FAMILY_ROBUST"
    elif live_labels and all(x == "CROSSSTACK_ABSENT" for x in live_labels):
        family = "CROSSSTACK_FAMILY_ABSENT"
    elif live_labels:
        family = "CROSSSTACK_FAMILY_SPLIT"
    else:
        family = "NO_LIVE_VARIANT"
    return {"per_variant": out, "family": family,
            "live_variant_count": len(live_labels),
            "nsf_ref_pct": {t: NSF_G0_DOP_PCT[float(t)] for t in thetas
                            if float(t) in NSF_G0_DOP_PCT}}


def cold_reference_rows(y0_abs: float, alpha_nom_lu: float, omega_lu: float,
                        ny: int, hs: int, gamma: float) -> dict[str, float]:
    """Absolute cold-admittance context (archived; only BGK gates on it).

    ``ratio_vs_halfspace`` compares the measured cold |Y| with the continuum
    half-space |sqrt(i*omega*alpha)|; ``ratio_vs_tent_bvp`` compares it with the
    SAME rig solved analytically at nominal transport.  Production sits well
    above both (a documented lattice property: the certified reference uses the
    measured alpha_eff(k), not alpha_nominal), so these rows are context, never
    a pass/fail on the configuration axis.
    """

    y_hs = abs(complex(np.sqrt(1j * omega_lu * alpha_nom_lu)))
    ref = tent_bvp_reference(np.full(ny, alpha_nom_lu), hs, omega_lu,
                             alpha_nom_lu, gamma=gamma)
    return {"y0_abs": float(y0_abs),
            "ratio_vs_halfspace": float(y0_abs / y_hs),
            "ratio_vs_tent_bvp": float(y0_abs / (y_hs * abs(ref["Y_over_Yhs"]))),
            "tent_bvp_over_halfspace": float(abs(ref["Y_over_Yhs"]))}


# ---------------------------------------------------------------------------
# stage orchestration
# ---------------------------------------------------------------------------

def run_stage(mode: str, base_cfg: dict, variants: list[str], workers: int,
              ckpt: Path, log) -> dict[str, Any]:
    proto = PROTO[mode]
    thetas = [float(t) for t in proto["theta_points"]]
    ny = 2 * int(proto["hs_rows"])
    nx = int(proto["nx"])

    settle_payloads = []
    for v in variants:
        for th in [0.0] + thetas:
            settle_payloads.append({
                "label": f"{v}_th{th:g}", "variant": v, "theta_dc": th,
                "gas_cfg": variant_gas_cfg(base_cfg, v), "ny": ny, "nx": nx,
                "settle_periods": proto["settle_periods"],
                "samples_per_period": proto["samples_per_period"],
                "ckpt_dir": str(ckpt),
            })
    settles = execute_cases(settle_payloads, workers, log, worker=_settle_worker)
    legality, status = partition_variants(settles, variants, thetas)
    for lbl, row in legality.items():
        log(f"settle {lbl}: {row}")
    live = [v for v in variants if status[v]["ok"]]
    for v in variants:
        if v not in live:
            log(f"variant {v}: MEASURED_UNSTABLE_OR_ILLEGAL ({status[v]['reason']}) "
                f"— dropped from the tangent wave, archived as a "
                f"stability-boundary finding")
    if "PROD" not in live or len(live) < 2:
        return {"stage_verdict": "LEGALITY_FAILED", "legality": legality,
                "variant_status": status,
                "reason": "PROD anchor dead or <2 surviving variants"}

    tang_payloads = []
    for v in live:
        cold_run = settles[f"{v}_th0"]
        base_payload = {
            "variant": v, "h": H_JVP, "gas_cfg": variant_gas_cfg(base_cfg, v),
            "ny": ny, "nx": nx, "cold_run": cold_run,
            "drive_periods": proto["drive_periods"],
            "samples_per_period": proto["samples_per_period"],
            "fit_skip_periods": proto["fit_skip_periods"],
            "ckpt_dir": str(ckpt),
        }
        tang_payloads.append({**base_payload, "label": f"{v}_cold",
                              "hot_run": cold_run})
        for th in thetas:
            tang_payloads.append({**base_payload, "label": f"{v}_th{th:g}_hot",
                                  "hot_run": settles[f"{v}_th{th:g}"]})
    tangs = execute_cases(tang_payloads, workers, log, worker=_tangent_worker)

    anchor_ok = True
    tangent_failed: dict[str, str] = {}
    rows: dict[str, dict] = {}
    for v in live:
        v_ok = True
        reasons: list[str] = []

        def _leg(lbl, _reasons=reasons):
            nonlocal v_ok
            r = tangs.get(lbl, {})
            if "Y" not in r:
                v_ok = False
                _reasons.append(f"{lbl}: missing/failed")
                return None
            a = r["audits"]
            if not (a["mass_tangent_rel_worst"] <= GATE_V5_MASS
                    and a["energy_account_rel_worst"] <= GATE_V5_ENERGY
                    and r["r_f_worst"] <= GATE_R_F):
                v_ok = False
                _reasons.append(f"{lbl}: audit gate ({a}, r_f={r['r_f_worst']:.1e})")
                return None
            return r

        rc = _leg(f"{v}_cold")
        per_theta: dict[str, Any] = {}
        if rc is not None:
            yc = complex(rc["Y"]["re"], rc["Y"]["im"])
            per_theta["Y0_abs"] = abs(yc)
            for th in thetas:
                rh = _leg(f"{v}_th{th:g}_hot")
                if rh is not None:
                    yh = complex(rh["Y"]["re"], rh["Y"]["im"])
                    per_theta[f"{th:g}"] = _dop(yh, yc)
        if v_ok:
            rows[v] = per_theta
            shown = {k: (round(x["d_op_pct"], 4) if isinstance(x, dict) else
                         round(x, 8)) for k, x in per_theta.items()}
            log(f"variant {v}: {shown}")
        else:
            tangent_failed[v] = "; ".join(reasons)
            log(f"variant {v}: TANGENT_FAILED ({tangent_failed[v]})")
            if v == "PROD":
                anchor_ok = False

    stage_ok = anchor_ok and len(rows) >= 2
    return {"stage_verdict": "COMPLETED" if stage_ok else "LEGALITY_FAILED",
            "legality": legality, "variant_status": status,
            "tangent_failed": tangent_failed, "rows": rows,
            "thetas": [f"{t:g}" for t in thetas],
            "ny": ny, "nx": nx,
            "steps_per_period": settles["PROD_th0"].get("steps_per_period")}


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              cwd=REPO_ROOT, capture_output=True, text=True,
                              timeout=10, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="cross-stack collision-structure scan (unit 1a, D0-7)")
    ap.add_argument("--mode", choices=("preflight", "smoke", "auth", "full"),
                    default="full")
    ap.add_argument("--variants", nargs="+", default=None,
                    help=f"subset of {DEFAULT_VARIANTS} (PROD always added)")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--output-root", default=None)
    ap.add_argument("--skip-preflight", action="store_true",
                    help="smoke/auth only; the pre-flight rows must already be "
                         "archived from an earlier run of the same commit")
    args = ap.parse_args()

    variants = list(dict.fromkeys(["PROD"] + (args.variants or DEFAULT_VARIANTS)))
    for v in variants:
        if v not in VARIANTS:
            raise SystemExit(f"unknown variant {v!r}")
    workers = (args.workers if args.workers is not None
               else max(1, (os.cpu_count() or 4) - 2))
    base_cfg = load_config(REPO_ROOT / GAS_CONFIG)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = (Path(args.output_root) if args.output_root
                else REPO_ROOT / "results" / "phase5" / "crossstack_collision")
    out_dir = out_root / f"{run_id}_{args.mode}"
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg_sha8 = sha256_file(REPO_ROOT / GAS_CONFIG)[:8]
    log = lambda m: print(f"[{UNIT}] {m}", flush=True)  # noqa: E731
    log(f"run {run_id} mode={args.mode} variants={variants} h={H_JVP:g} "
        f"workers={workers}")
    log("judgement frozen (module docstring): aliveness>=1e-6 / live key "
        ">=1e-4 on cold |Y0| / anchor 0.2pp vs TAN / class line 1.0pp / "
        "stability rho(J)<=1+1e-6 / caveats at 30% |Y0| and 2% alpha_eff")

    summary: dict[str, Any] = {
        "unit": UNIT, "run_id": run_id, "mode": args.mode,
        "plan": "docs/Phase_5/crossstack_1a_plan_v1.0.md",
        "protocol": {
            "gas_config": GAS_CONFIG, "frequency_Hz": FREQUENCY_HZ,
            "h_jvp": H_JVP, "wall": "production v1.1 symmetric mass-neutral "
                                    "(unchanged)",
            "variants": {v: VARIANTS[v]["meaning"] for v in variants},
            "variant_collision_cfg": {v: VARIANTS[v]["cfg"] for v in variants},
            "lines": {"aliveness_rel": LINE_ALIVENESS_REL,
                      "livekey_y0_rel": LINE_LIVEKEY_Y0_REL,
                      "anchor_pp": LINE_ANCHOR_PP,
                      "class_pp": LINE_CLASS_PP,
                      "xcal_y0_rel": LINE_XCAL_Y0_REL,
                      "xcal_alpha_rel": LINE_XCAL_ALPHA_REL,
                      "bgk_cold_anchor_rel": LINE_BGK_COLD_ANCHOR_REL,
                      "spectral_radius": LINE_SPECTRAL_RADIUS},
            "legality_gates": {"stationarity": GATE_STATIONARITY,
                               "dc_closure": GATE_DC_CLOSURE, "r_f": GATE_R_F,
                               "v5_mass": GATE_V5_MASS,
                               "v5_energy": GATE_V5_ENERGY},
        },
        "external_references": {
            "tan_dop_pct": {f"{k:g}": v for k, v in TAN_DOP_PCT.items()},
            "nsf_g0_dop_pct": {f"{k:g}": v for k, v in NSF_G0_DOP_PCT.items()},
            "provenance": "TAN=archive/M5_runs/wp4_tan_20260805T092726Z_B; "
                          "NSF=archive/M5_runs/nsf_arb_20260811T055850Z; "
                          "G0 alpha_eff table=archive/M5_runs/g0_20260722T173919Z",
        },
        "machine": {"node": platform.node(), "platform": platform.platform(),
                    "python": sys.version.split()[0], "numpy": np.__version__,
                    "git_commit": _git_commit(), "workers": workers},
    }

    def _dump():
        (out_dir / "summary.json").write_text(
            json.dumps(summary, indent=1, default=str), encoding="utf-8")

    # ---- pre-flight ----
    if args.mode in ("preflight", "full") and not args.skip_preflight:
        log("---- stage preflight ----")
        alive = aliveness_check(base_cfg, variants)
        summary["aliveness"] = alive
        for v, row in alive.items():
            log(f"aliveness {v}: rel_diff_vs_PROD={row['rel_diff_vs_prod']:.3e} "
                f"-> {'LIVE' if row['live'] else 'DEAD KEY'}")
        summary["bgk_stability"] = bgk_stability_map(base_cfg, log)
        log(f"BGK stability verdict: {summary['bgk_stability']['verdict']}")
        summary["transport"] = transport_probe(base_cfg, variants, workers, log)
        _dump()
        if args.mode == "preflight":
            summary["verdict"] = "COMPLETED"
            _dump()
            log(f"verdict=COMPLETED  outputs -> {out_dir}")
            return 0

    stages = (["smoke", "auth"] if args.mode == "full" else [args.mode])
    verdict = "COMPLETED"
    for stage in stages:
        log(f"---- stage {stage} ----")
        ckpt = out_root / f"checkpoints_{stage}_{cfg_sha8}_crossstack"
        ckpt.mkdir(parents=True, exist_ok=True)
        res = run_stage(stage, base_cfg, variants, workers, ckpt, log)
        summary[f"stage_{stage}"] = res
        _dump()
        if res["stage_verdict"] != "COMPLETED":
            verdict = "LEGALITY_FAILED"
            log(f"stage {stage} LEGALITY_FAILED — aborting")
            break
        thetas = res["thetas"]
        cls = classify(res["rows"], thetas)
        summary[f"classification_{stage}"] = cls
        log(f"classification[{stage}]: family={cls['family']} "
            f"live={cls['live_variant_count']}")
        for name, row in cls["per_variant"].items():
            log(f"  {name}: {row}")

        # absolute cold-admittance context for every surviving variant
        om_lu = 2.0 * math.pi / int(res["steps_per_period"])
        probe = copy.deepcopy(base_cfg)
        probe["numerics"] = {**probe["numerics"], "nx": 4, "ny": 8}
        alpha_nom = float(GasSolver2D(probe).mapping.alpha_lu)
        gamma = float(base_cfg["physical"]["gamma"])
        summary[f"cold_context_{stage}"] = {
            v: cold_reference_rows(r["Y0_abs"], alpha_nom, om_lu,
                                   int(res["ny"]), int(res["ny"]) // 2, gamma)
            for v, r in res["rows"].items() if "Y0_abs" in r}

        if stage == "auth":
            anchor = {}
            base_rows = res["rows"].get("PROD", {})
            a_ok = True
            for t in thetas:
                if float(t) not in TAN_DOP_PCT or t not in base_rows:
                    continue
                dev = abs(base_rows[t]["d_op_pct"] - TAN_DOP_PCT[float(t)])
                anchor[t] = {"d_op_pct": base_rows[t]["d_op_pct"],
                             "tan_ref_pct": TAN_DOP_PCT[float(t)],
                             "dev_pp": dev,
                             "pass": bool(dev <= LINE_ANCHOR_PP)}
                a_ok = a_ok and anchor[t]["pass"]
                log(f"anchor PROD th={t}: dev={dev:.5f}pp "
                    f"-> {'PASS' if anchor[t]['pass'] else 'FAIL'}")
            summary["anchor_auth"] = anchor
            if not a_ok:
                verdict = "LEGALITY_FAILED"
        elif stage == "smoke":
            b = res["rows"].get("PROD", {}).get("0.05")
            if b:
                summary["smoke_soft_anchor"] = {
                    "d_op_pct": b["d_op_pct"],
                    "jab1_smoke_ref_pct": JAB1_SMOKE_DOP_PCT,
                    "dev_pp": abs(b["d_op_pct"] - JAB1_SMOKE_DOP_PCT),
                    "soft_anchor": True}
                log(f"smoke soft anchor: {summary['smoke_soft_anchor']}")
        _dump()

    summary["verdict"] = verdict
    _dump()
    log(f"verdict={verdict}  outputs -> {out_dir}")
    return 0 if verdict == "COMPLETED" else 1


if __name__ == "__main__":
    sys.exit(main())
