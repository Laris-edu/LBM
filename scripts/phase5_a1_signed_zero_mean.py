"""Phase_5 WP3 A1 units runner: signed zero-mean periodic heating (contract §3.2/§15.1).

Units P-LIN / P-AC1 / P-AC2 / P-AC3 (first-round ladder eps_AC = {0.001, 0.01,
0.05, 0.075}; the §15.1 full ladder is WP4; 0.10 truncated by the G1a
authorization boundary G1A_PASSED_TO_0P05->0.075).

PROTOCOL — FIXTURE v2 (pre-registered 2026-08-02, wp3_go_nogo_decision.md §2):
sealed y-periodic single-band rig (ny=48 x nx=8, the G1-W/G1a certified
lineage where all the priors live), PRESCRIBED-theta signed drive with the
MEASURED zero-mean power normalization: theta_w(t) = theta0*(1 +
sign*eps*env*cos(Omega t)) (G1a protocol verbatim) and P(t) = 2q''(t) from
the certified cv-corrected band bookkeeping; G1 = T_hat_1 / P_hat_1 is a
measured transfer ratio (D0-4 numerical-ablation caliber: the realized power
is signed, zero-mean, archived per case).

The v1 coupled film-ODE power drive was probe-REJECTED before the
authoritative run: on the sealed NO-SINK rig at the chi0=0.016 light film
every drive AND the null case explode within ~250 steps (the G4a tent loop
with identical cv accounting is stable for 153k steps — the sealed box lacks
the sink anchor; G1b channel-2 box-feedback family). A1 does not need a loop;
the coupled drive stays where it is certified: the sink-anchored A2a/A5
protocols (G4a).

Signed pairs per eps (G1-W fixture lineage, protocol constants verbatim:
ramp 2 / settle 12 / periods 14 / 64 samples/period / detrend 0): the odd
combination isolates 1f/3f (G1, fundamental phase, m3 diagnostics); the even
combination isolates 2f killing linear transients (H2 primary signal).
Null-drive case (P1 = 0) measures the whole-chain floor; the DIAGNOSTIC_ONLY
pressure_preserving wall runs one contrast pair at eps = 0.05 (§15.1 wall
difference output; a large difference proves the contrast has teeth, it is
NOT a production uncertainty component). Operator-ablation sensitivity is
consumed from the certified G2-O bounds (same rig family; |dH2| <= 1.3%,
|dD_G| <= 7.2e-5) rather than re-run — pre-registered bookkeeping.

Observables (§12.3/§15.1): G1 = |T_hat_s,1| / P1 (coupled-drive caliber;
p_hat_box channel archived alongside — NOT the same caliber as the G1a
prescribed-theta readouts, do not mix tables), D_G = G1(eps)/G1(0.001) - 1,
fundamental phase shift, H2 (even combination, q and p channels), m2 ladder
log-slope, H3 archived diagnostic-only, mass/energy/finiteness legality,
U_gov = window (+) pair-consistency (+) fit.

This is a PRODUCTION runner, not a gate: the exit verdict reflects legality
and floor rows only; the physics numbers go to wp3_go_nogo_decision.md.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.macroscopic import recover_macro  # noqa: E402
from core.solver import GasSolver2D  # noqa: E402
from boundary.wall_thermal_grad import make_bottom_grad_wall_callback  # noqa: E402
from boundary.wall_thermal_mass_neutral import (  # noqa: E402
    make_symmetric_mass_neutral_wall_callback,
)
from scripts.phase2_m2_verification import load_config  # noqa: E402
from scripts.phase5_g4a_dc_basestate import make_energy_audited_band  # noqa: E402

CASE_FAMILY = "a1_signed_zero_mean"


def run_a1_case(gas_cfg: dict, *, ny: int, nx: int, wall: str,
                eps_signed: float, frequency_hz: float, ramp_periods: float,
                periods: float, samples_per_period: int,
                log=print) -> dict[str, Any]:
    """One signed-drive case: PRESCRIBED-theta signed drive, measured power.

    FIXTURE v2 (2026-08-02, pre-registered before the authoritative run): the
    v1 coupled power drive (film ODE) is measured UNSTABLE on the sealed
    no-sink rig at the chi0=0.016 light film (all drives AND the null case
    explode within ~250 steps; the G4a tent loop with identical accounting is
    stable 153k steps — the sealed box lacks the sink anchor, the G1b
    channel-2 box-feedback family). A1 does not need the loop: causality is
    inverted — theta_w(t) = theta0*(1 + sign*eps*env*cos) is PRESCRIBED (the
    G1a/G1-W certified protocol verbatim) and the signed zero-mean heat power
    P(t) = 2q''(t) is MEASURED from the certified cv-corrected bookkeeping.
    G1 = |T_hat_1| / |P_hat_1| becomes a measured transfer ratio; all §15.1
    observables follow with zero loop-stability risk (D0-4 numerical-ablation
    caliber: the realized power is signed, zero-mean, archived)."""

    cfg = copy.deepcopy(gas_cfg)
    cfg["numerics"] = {**cfg["numerics"], "nx": int(nx), "ny": int(ny)}
    solver = GasSolver2D(cfg)
    th0 = float(solver.mapping.theta_ref_lu)
    rho0 = float(solver.mapping.lattice.rho_ref_lu)
    dt_s = float(solver.mapping.lattice.dt_s)
    lattice = solver.lattice
    D = int(solver.mapping.lattice.D)
    S = int(solver.mapping.lattice.S)
    cv_row = 0.5 * (D + S)
    steps_per_period = int(round(1.0 / (frequency_hz * dt_s)))
    om_step = 2.0 * math.pi / steps_per_period
    stride = max(1, steps_per_period // int(samples_per_period))

    prof = np.full(ny, th0)
    solver.initialize_from_macro(np.full((ny, nx), rho0), np.zeros((ny, nx, 2)),
                                 np.tile(prof[:, None], (1, nx)))
    rec: dict[str, list[float]] = {}
    state = {"theta_w": th0, "prev_theta_w": th0}

    def theta_w_fn(_s):
        return state["theta_w"]

    if wall == "mass_neutral_v1p1":
        inner_static = make_symmetric_mass_neutral_wall_callback(theta_w_fn)

        def wall_cb(**kw):
            return inner_static(**kw)
    elif wall == "pressure_preserving_grad":
        def wall_cb(**kw):
            inner = make_bottom_grad_wall_callback(
                state["theta_w"], rho_policy="pressure_preserving",
                extrap="linear", fill_deep_links=False)
            return inner(**kw)
    else:
        raise ValueError(wall)

    audited = make_energy_audited_band(wall_cb, rec, lattice, "hot")
    c_row_cv = cv_row * rho0 * nx     # uniform cold state: exact row mass

    n_total = int(round(periods * steps_per_period))
    mass0 = float(np.sum(solver.f))
    t_samp: list[float] = []
    ts_samp: list[float] = []
    q_samp: list[float] = []
    p_samp: list[float] = []
    solver.step(1, boundary_callback=audited)   # prime the bookkeeping
    for i in range(n_total):
        t = i / steps_per_period
        env = 1.0 if (ramp_periods <= 0.0 or t >= ramp_periods) else \
            0.5 * (1.0 - math.cos(math.pi * t / ramp_periods))
        prev = state["theta_w"]
        state["prev_theta_w"] = prev
        state["theta_w"] = th0 * (1.0 + eps_signed * env * math.cos(om_step * i))
        solver.step(1, boundary_callback=audited)
        # measured signed zero-mean power: cv-corrected gas heat this step
        q_gas = (rec["hot_dE"][-1]
                 - c_row_cv * (state["theta_w"] - prev)) / nx
        if (i + 1) % stride == 0:
            m = recover_macro(solver.f, solver.g, D=D, S=S, lattice=lattice)
            if not np.all(np.isfinite(m.theta)):
                return {"finite": False, "nan_at": i, "theta0": th0,
                        "steps_per_period": steps_per_period}
            t_samp.append(i * dt_s)
            ts_samp.append(state["theta_w"])
            q_samp.append(q_gas)
            p_samp.append(float(np.mean(m.p)))
    return {
        "finite": True, "theta0": th0, "rho0": rho0, "nx": nx, "ny": ny,
        "dt_s": dt_s, "steps_per_period": steps_per_period,
        "mass_drift": abs(float(np.sum(solver.f)) / mass0 - 1.0),
        "t_s": np.array(t_samp), "Ts": np.array(ts_samp),
        "q_lu": np.array(q_samp), "p_box": np.array(p_samp),
        "c_row_cv": c_row_cv,
    }


def measure_cold_instrument(gas_cfg: dict, *, ny: int, nx: int,
                            wall: str, log=print) -> dict[str, float]:
    """Open-loop G_inst probe on the uniform cold state (G4a A.4 instrument)."""

    cfg = copy.deepcopy(gas_cfg)
    cfg["numerics"] = {**cfg["numerics"], "nx": int(nx), "ny": int(ny)}
    solver = GasSolver2D(cfg)
    th0 = float(solver.mapping.theta_ref_lu)
    rho0 = float(solver.mapping.lattice.rho_ref_lu)
    lattice = solver.lattice
    D = int(solver.mapping.lattice.D)
    S = int(solver.mapping.lattice.S)
    prof = np.full(ny, th0)
    solver.initialize_from_macro(np.full((ny, nx), rho0), np.zeros((ny, nx, 2)),
                                 np.tile(prof[:, None], (1, nx)))
    rec: dict[str, list[float]] = {}
    state = {"theta_w": th0}

    def theta_w_fn(_s):
        return state["theta_w"]

    if wall == "mass_neutral_v1p1":
        inner = make_symmetric_mass_neutral_wall_callback(theta_w_fn)

        def wall_cb(**kw):
            return inner(**kw)
    else:
        def wall_cb(**kw):
            cb = make_bottom_grad_wall_callback(
                state["theta_w"], rho_policy="pressure_preserving",
                extrap="linear", fill_deep_links=False)
            return cb(**kw)

    audited = make_energy_audited_band(wall_cb, rec, lattice, "hot")
    c_row_cv = 0.5 * (D + S) * rho0 * nx
    for _ in range(32):                       # micro-settle the uniform state
        solver.step(1, boundary_callback=audited)
    n_pre = len(rec["hot_dE"])
    delta = 1e-4 * th0
    state["theta_w"] = th0 + delta
    solver.step(1, boundary_callback=audited)
    g_inst = ((rec["hot_dE"][-1] - c_row_cv * delta)
              - rec["hot_dE"][n_pre - 1]) / nx / delta
    log(f"  cold instrument [{wall}]: c_row_cv={c_row_cv:.3f} G_inst={g_inst:.5f}")
    return {"c_row_cv": c_row_cv, "G_inst": float(g_inst), "theta0": th0}


# ---------------------------------------------------------------------------
# worker + orchestration
# ---------------------------------------------------------------------------

def _a1_case_worker(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    label = payload["label"]
    lines: list[str] = []
    try:
        run = run_a1_case(payload["gas_cfg"], ny=payload["ny"], nx=payload["nx"],
                          wall=payload["wall"], eps_signed=payload["eps_signed"],
                          frequency_hz=payload["frequency_hz"],
                          ramp_periods=payload["ramp_periods"],
                          periods=payload["periods"],
                          samples_per_period=payload["samples_per_period"],
                          log=lambda m: lines.append(str(m)))
        return label, {"ok": True, "run": run, "log": lines}
    except Exception as exc:
        return label, {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                       "log": lines}


def _cplx(z: complex) -> dict[str, float]:
    return {"re": float(np.real(z)), "im": float(np.imag(z)),
            "abs": float(abs(z)),
            "phase_deg": float(math.degrees(math.atan2(np.imag(z), np.real(z))))}


def _fit_series(t: np.ndarray, y: np.ndarray, f_hz: float, skip_periods: float,
                n_harm: int = 5):
    from postproc.multiharmonic_fit import fit_multiharmonic

    mask = t >= skip_periods / f_hz * (1.0 - 1e-12)
    return fit_multiharmonic(t[mask], y[mask], 2.0 * math.pi * f_hz,
                             n_harmonics=n_harm)


def run_a1(config_path: str | Path, output_root: str | Path | None = None,
           *, smoke: bool = False, workers: int | None = None) -> dict[str, Any]:
    import h5py
    import yaml

    from scripts.phase5_g1a_amplitude_envelope import execute_cases
    from scripts.phase5_g1w_wall_neutrality import _git_commit

    t0 = datetime.now(timezone.utc)
    cfg_all = load_config(Path(config_path))
    proto = cfg_all["a1_smoke" if smoke else "a1"]
    gates = cfg_all["gates"]
    gas_cfg = load_config(REPO_ROOT / str(cfg_all["inheritance"]["gas_config"]))

    log_lines: list[str] = []

    def log(msg: str) -> None:
        line = f"A1 {msg}"
        print(line, flush=True)
        log_lines.append(line)

    f_hz = float(proto["frequency_Hz"])
    ny, nx = int(proto["ny"]), int(proto["nx"])
    eps_ladder = [float(e) for e in proto["eps_ladder"]]
    eps_ref = min(eps_ladder)
    spp = int(proto["samples_per_period"])
    skip = float(proto["fit_skip_periods"])

    probe_cfg = copy.deepcopy(gas_cfg)
    probe_cfg["numerics"] = {**probe_cfg["numerics"], "nx": 4, "ny": 8}
    mapping = GasSolver2D(probe_cfg).mapping
    th0 = float(mapping.theta_ref_lu)

    # ---- case matrix (pre-registered; fixture v2 prescribed-theta pairs) ----
    common = dict(gas_cfg=gas_cfg, ny=ny, nx=nx, frequency_hz=f_hz,
                  ramp_periods=float(proto["ramp_periods"]),
                  periods=float(proto["periods"]),
                  samples_per_period=spp)
    payloads: list[dict[str, Any]] = []
    for eps in eps_ladder:
        for sign, tag in ((1.0, "plus"), (-1.0, "minus")):
            payloads.append({**common, "label": f"eps{eps:g}_{tag}",
                             "wall": "mass_neutral_v1p1",
                             "eps_signed": sign * eps})
    payloads.append({**common, "label": "null_drive",
                     "wall": "mass_neutral_v1p1", "eps_signed": 0.0})
    eps_c = float(proto["wall_contrast_eps"])
    for sign, tag in ((1.0, "plus"), (-1.0, "minus")):
        payloads.append({**common, "label": f"oldwall_eps{eps_c:g}_{tag}",
                         "wall": "pressure_preserving_grad",
                         "eps_signed": sign * eps_c})

    n_workers = workers if workers is not None else max(1, (os.cpu_count() or 4) - 2)
    results = execute_cases(payloads, n_workers, log, worker=_a1_case_worker)
    for label in sorted(results):
        res = results[label]
        if res.get("ok") and res["run"].get("finite"):
            log(f"[{label}] finite mass_drift={res['run']['mass_drift']:.2e}")
        else:
            log(f"[{label}] DEAD: {res.get('error') or res['run']}")

    def series(label: str) -> dict[str, Any] | None:
        res = results.get(label)
        return res["run"] if res and res.get("ok") and res["run"].get("finite") else None

    # ---- pair combinations and observables ----
    def pair_obs(base_label: str, _unused: float = 0.0) -> dict[str, Any] | None:
        rp = series(f"{base_label}_plus")
        rm = series(f"{base_label}_minus")
        if rp is None or rm is None:
            return None
        t = rp["t_s"]
        odd = {ch: 0.5 * (rp[ch] - rm[ch]) for ch in ("Ts", "q_lu", "p_box")}
        even = {ch: 0.5 * (rp[ch] + rm[ch]) for ch in ("Ts", "q_lu", "p_box")}
        f_odd = {ch: _fit_series(t, odd[ch], f_hz, skip) for ch in odd}
        f_even = {ch: _fit_series(t, even[ch], f_hz, skip) for ch in even}
        ts1 = f_odd["Ts"].harmonic(1)
        p1h = f_odd["p_box"].harmonic(1)
        q1h = f_odd["q_lu"].harmonic(1)     # measured signed power, 1f (both faces)
        h2_p = abs(f_even["p_box"].harmonic(2)) / max(abs(p1h), 1e-300)
        h2_q = abs(f_even["q_lu"].harmonic(2)) / max(abs(q1h), 1e-300)
        h3_p = abs(f_odd["p_box"].harmonic(3)) / max(abs(p1h), 1e-300)
        g1 = ts1 / q1h if abs(q1h) > 0 else complex("nan")
        # window sensitivity: half-period-shifted refit of the transfer ratio
        f_win_t = _fit_series(t, odd["Ts"], f_hz, skip + 0.5)
        f_win_q = _fit_series(t, odd["q_lu"], f_hz, skip + 0.5)
        g1_win = f_win_t.harmonic(1) / f_win_q.harmonic(1)
        win = g1_win / g1 if abs(g1) > 0 else complex("nan")
        # pair asymmetry on the measured-power channel (even 1f contamination)
        f_p = _fit_series(t, rp["q_lu"], f_hz, skip)
        f_m = _fit_series(t, rm["q_lu"], f_hz, skip)
        asym = abs(f_p.harmonic(1) + f_m.harmonic(1)) / max(abs(q1h), 1e-300)
        return {
            "P1_measured_lu": float(abs(q1h)),
            "P_mean_rectified_lu": float(0.5 * (np.mean(rp["q_lu"]) + np.mean(rm["q_lu"]))),
            "G1_transfer": _cplx(g1),
            "p_box_1f": _cplx(p1h), "q_1f": _cplx(q1h), "Ts_1f": _cplx(ts1),
            "eps_realized": float(abs(ts1) / th0),
            "H2_p": float(h2_p), "H2_q": float(h2_q),
            "H3_p_diagnostic": float(h3_p),
            "window_ratio": _cplx(win),
            "pair_asymmetry_rel": float(asym),
            "mass_drift_max": max(rp["mass_drift"], rm["mass_drift"]),
        }

    obs: dict[str, Any] = {}
    for eps in eps_ladder:
        o = pair_obs(f"eps{eps:g}")
        if o is not None:
            obs[f"{eps:g}"] = o
            log(f"eps={eps:g}: P1={o['P1_measured_lu']:.4e} "
                f"|G1|={o['G1_transfer']['abs']:.4e}@{o['G1_transfer']['phase_deg']:+.2f} "
                f"H2_p={o['H2_p']:.3e} H2_q={o['H2_q']:.3e} asym={o['pair_asymmetry_rel']:.2e}")
    old_obs = pair_obs(f"oldwall_eps{eps_c:g}")
    if old_obs is not None:
        log(f"oldwall eps={eps_c:g}: |G1|={old_obs['G1_transfer']['abs']:.4e}"
            f"@{old_obs['G1_transfer']['phase_deg']:+.2f} H2_p={old_obs['H2_p']:.3e}")

    # null floors
    null_run = series("null_drive")
    floors = None
    if null_run is not None:
        fN = {ch: _fit_series(null_run["t_s"], null_run[ch], f_hz, skip)
              for ch in ("Ts", "q_lu", "p_box")}
        floors = {ch: {"h1": float(abs(fN[ch].harmonic(1))),
                       "h2": float(abs(fN[ch].harmonic(2)))} for ch in fN}
        log(f"null floors: Ts1={floors['Ts']['h1']:.2e} p1={floors['p_box']['h1']:.2e} "
            f"p2={floors['p_box']['h2']:.2e}")

    # ---- ladder observables: D_G, phase shift, m2 ----
    ladder_rows: dict[str, Any] = {}
    ref_key = f"{eps_ref:g}"
    if ref_key in obs:
        g1_ref = complex(obs[ref_key]["G1_transfer"]["re"], obs[ref_key]["G1_transfer"]["im"])
        for key, o in obs.items():
            g1 = complex(o["G1_transfer"]["re"], o["G1_transfer"]["im"])
            ladder_rows[key] = {
                "D_G": float(abs(g1) / abs(g1_ref) - 1.0),
                "phase_shift_deg": float(math.degrees(
                    math.atan2((g1 / g1_ref).imag, (g1 / g1_ref).real))),
            }
        eps_arr = sorted(float(k) for k in obs)
        if len(eps_arr) >= 3:
            lg_p1 = [math.log(obs[f"{e:g}"]["P1_measured_lu"]) for e in eps_arr[1:]]
            lg_h2 = [math.log(max(obs[f"{e:g}"]["H2_p"]
                                  * abs(complex(obs[f"{e:g}"]["p_box_1f"]["re"],
                                                obs[f"{e:g}"]["p_box_1f"]["im"])), 1e-300))
                     for e in eps_arr[1:]]
            m2 = float(np.polyfit(lg_p1, lg_h2, 1)[0])
            ladder_rows["m2_log_slope"] = m2
            log(f"m2 (|p2| vs P1 log-slope, eps>={eps_arr[1]:g}): {m2:.3f}")

    # ---- legality verdict (production runner: legality + floors only) ----
    mn_labels = [p["label"] for p in payloads if p["wall"] == "mass_neutral_v1p1"]
    legal = {
        "all_finite": all(series(p["label"]) is not None for p in payloads),
        "mass_gate": float(gates["mass_drift_max"]),
        "mass_worst": max((series(lb)["mass_drift"] for lb in mn_labels
                           if series(lb) is not None), default=float("nan")),
        "old_wall_mass_drift_archived": max(
            (series(p["label"])["mass_drift"] for p in payloads
             if p["wall"] == "pressure_preserving_grad"
             and series(p["label"]) is not None), default=float("nan")),
        "pair_asymmetry_gate": float(gates["pair_asymmetry_rel"]),
        "pair_asymmetry_worst": max((o["pair_asymmetry_rel"] for o in obs.values()),
                                    default=float("nan")),
        "floor_gate_p2_rel": float(gates["floor_p2_rel_of_smallest"]),
    }
    floor_ok = True
    if floors is not None and ref_key in obs:
        p1_small = abs(complex(obs[ref_key]["p_box_1f"]["re"],
                               obs[ref_key]["p_box_1f"]["im"]))
        legal["floor_p2_over_smallest_p1"] = floors["p_box"]["h2"] / max(p1_small, 1e-300)
        floor_ok = legal["floor_p2_over_smallest_p1"] <= legal["floor_gate_p2_rel"]
    verdict = "COMPLETED" if (legal["all_finite"]
                              and legal["mass_worst"] <= legal["mass_gate"]
                              and legal["pair_asymmetry_worst"] <= legal["pair_asymmetry_gate"]
                              and floor_ok) else "LEGALITY_FAILED"
    log(f"verdict={verdict}")

    # ---- 1D twin legs (P-1D, A1 part): both branches at the contrast eps ----
    oned = {}
    if proto.get("oned_legs", True):
        from reference.nonlinear_nsf_1d import (
            g0_measured_transport,
            physical_air_transport,
        )
        from reference.constants import default_params
        from scripts.phase5_g3_nsf1d_reference import _a1_run
        params = default_params()
        p1d = dict(proto["oned"])
        for bname, ctor in (("lbm_equivalent_g0", g0_measured_transport),
                            ("physical_air", physical_air_transport)):
            pair = {}
            for sign, tag in ((1.0, "plus"), (-1.0, "minus")):
                pair[tag] = _a1_run(params, ctor(params), p1d,
                                    float(proto["wall_contrast_eps"]), f_hz, sign)
            fp, fm = pair["plus"], pair["minus"]
            t1 = 0.5 * (fp["fit_T"].harmonic(1) - fm["fit_T"].harmonic(1))
            p2e = 0.5 * (fp["fit_p"].harmonic(2) + fm["fit_p"].harmonic(2))
            p1o = 0.5 * (fp["fit_p"].harmonic(1) - fm["fit_p"].harmonic(1))
            oned[bname] = {"T1": _cplx(t1), "H2_p": float(abs(p2e) / max(abs(p1o), 1e-300)),
                           "q1_si": fp["q1"]}
            log(f"1D[{bname}]: |T1|={abs(t1):.4e} H2_p={oned[bname]['H2_p']:.3e}")

    # ---- files (seven-file contract) ----
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = Path(output_root) if output_root else REPO_ROOT / "results" / "phase5" / CASE_FAMILY
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    with h5py.File(out_dir / "signals.h5", "w") as h5:
        for p in payloads:
            r = series(p["label"])
            if r is None:
                continue
            grp = h5.create_group(f"cases/{p['label']}")
            for key in ("t_s", "Ts", "q_lu", "p_box"):
                grp.create_dataset(key, data=r[key])
    digest = hashlib.sha256(json.dumps(
        {"obs": obs, "ladder": ladder_rows, "old": old_obs, "floors": floors},
        sort_keys=True, default=str).encode()).hexdigest()[:12]
    summary = {
        "gate": "WP3-A1", "run_id": run_id, "verdict": verdict,
        "gate_status": verdict, "scoped_limitations": [],
        "smoke_mode": bool(smoke),
        "protocol": {"eps_ladder": eps_ladder,
                     "wall_contrast_eps": eps_c,
                     "drive": "fixture v2: prescribed-theta signed pairs, "
                              "measured zero-mean power (G1=|T1|/|P1_meas|; "
                              "D0-4 numerical ablation caliber; v1 coupled "
                              "loop measured unstable on the sealed no-sink "
                              "rig — pre-registered rejection)"},
        "results": {"per_eps": obs, "ladder": ladder_rows,
                    "old_wall_contrast": old_obs, "null_floors": floors,
                    "legality": legal, "oned_legs": oned,
                    "operator_ablation_bound": "G2-O certified: |dH2|<=1.3%, "
                                               "|dD_G|<=7.2e-5 (cited, not rerun)"},
        "physics_core_digest": digest,
        "code_commit": _git_commit(),
        "wall_clock_min": (datetime.now(timezone.utc) - t0).total_seconds() / 60.0,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=float),
                                          encoding="utf-8")
    (out_dir / "gate_evaluation.json").write_text(json.dumps(
        {"gate": "WP3-A1", "verdict": verdict, "legality": legal,
         "note": "production runner: physics rows are data, not gates"},
        indent=1, default=float), encoding="utf-8")
    (out_dir / "harmonic_fit.json").write_text(json.dumps(
        {"per_eps": obs, "old_wall": old_obs, "floors": floors},
        indent=1, default=float), encoding="utf-8")
    (out_dir / "config_resolved.yaml").write_text(
        yaml.safe_dump(cfg_all, allow_unicode=True, sort_keys=False), encoding="utf-8")
    (out_dir / "provenance.json").write_text(json.dumps(
        {"run_id": run_id, "family": CASE_FAMILY, "argv": sys.argv,
         "machine": os.environ.get("COMPUTERNAME", "unknown"),
         "python": sys.version, "workers": n_workers,
         "started_utc": t0.isoformat(),
         "finished_utc": datetime.now(timezone.utc).isoformat()},
        indent=1), encoding="utf-8")
    (out_dir / "run_report.md").write_text("\n".join(
        [f"# WP3-A1 run {run_id}", "", f"verdict: **{verdict}**", "", "```text"]
        + log_lines + ["```", ""]), encoding="utf-8")
    log(f"outputs -> {out_dir}")
    return {"verdict": verdict, "out_dir": str(out_dir), "summary": summary}


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase_5 WP3 A1 units runner")
    ap.add_argument("--config", default=str(
        REPO_ROOT / "configs" / "phase5" / "a1_signed_zero_mean" / "a1_wp3_10k_dx2p6.yaml"))
    ap.add_argument("--output-root", default=None)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()
    result = run_a1(args.config, args.output_root, smoke=args.smoke,
                    workers=args.workers)
    return 0 if result["verdict"] == "COMPLETED" else 1


if __name__ == "__main__":
    sys.exit(main())
