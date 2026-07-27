"""Phase_5 G3 formal certification runner (contract §8, WP2).

Certifies ``reference/nonlinear_nsf_1d.py`` as the independent nonlinear 1D
NSF reference against the seven contract §8.2 gate rows, on real-air 10 kHz
production parameters, for BOTH formal property branches (contract §2.3,
formal definitions frozen here per route memo §8 / model-freeze doc §3):

  1D-lbm-equivalent = ``g0_measured_transport``  (G0-measured law at k1)
  1D-physical       = ``physical_air_transport`` (Sutherland anchored at T0)

Gate rows (§8.2)                     -> implementation
  equilibrium preservation           -> undriven production rig, 10 cycles
  linear-limit amplitude/phase       -> closed-box-corrected admittance anchor
                                        vs the Phase_1 half-space solution
  grid convergence                   -> 3-level ladder delta/3 -> /6 -> /12,
                                        Richardson order on complex Y >= 1.5,
                                        finest-two |dY/Y| <= 1%
  total energy residual              -> RK-weighted audit, max over all runs
  linearization leakage fixture      -> Dirichlet signed pair (pre-registered
                                        settle discipline) <= 1e-8 + physical
                                        2f sensitivity counter-check
  low-Mach resolvability             -> real-air acoustic ringdown (damping
                                        ratio vs laminar prediction, freq
                                        offset) + anchor SNR + residual
                                        spectra archived to signals.h5

Pre-registered review blocks (informational, NOT gate rows):
  - p-side dual-property H2 ablation (route memo §6/§7: "p-side H2 归 G3"):
    A1 signed-zero-mean flux ladder, eps in {0.005, 0.03, 0.05, 0.10}, on
    const (diagnostic lineage) / g0 (formal lbm-equivalent) / phys branches;
    QoI = box-pressure harmonics (p-side) with wall-T (T-side) continuity.
  - A1 flux-protocol leakage floor at the production settle length (pair
    fixture docstring pre-registration): archived as the rig measurement
    floor (U_det input), explicitly NOT the 1e-8 gate row.

Outputs: the full contract §16.1 seven-file set under
``results/phase5/g3_nsf1d/<run_id>/``. Verdict is script-emittable
PASSED/FAILED only (all seven rows are hard instrument certification; scoped
upgrades would be user decisions and no scoped row is defined for G3).
"""

from __future__ import annotations

import argparse
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

from postproc.multiharmonic_fit import fit_multiharmonic, residual_spectrum_fft
from reference.constants import PhysicalParams, default_params, omega_from_frequency
from reference.nonlinear_nsf_1d import (
    NSF1DConfig,
    NSF1DResult,
    SOLVER_ID,
    WallDrive,
    acoustic_ringdown_fixture,
    antisymmetric_pair_fixture,
    equilibrium_fixture,
    g0_measured_transport,
    lbm_equivalent_transport,
    linear_admittance_fixture,
    physical_air_transport,
    run_nsf1d,
)
from reference.thermal_admittance import thermal_admittance_halfspace

GATE_ID = "G3"
CASE_FAMILY = "g3_nsf1d"
PHASE5_CONTRACT_VERSION = "v1.2"
PARENT_BASELINE_RUN = "g0_effective_properties/20260722T173919Z"

# ---------------------------------------------------------------------------
# pre-registered protocols (frozen before the authoritative run; the smoke
# protocol exists for the contract test only and marks summary.smoke_mode)
# ---------------------------------------------------------------------------

PRODUCTION_PROTOCOL: dict[str, Any] = {
    "label": "g3_production_real_air_10kHz",
    "frequency_hz": 1.0e4,
    "params_overrides": {},  # frozen Phase_0 air
    "equilibrium": {"n_cycles": 10.0, "cells_per_delta": 12.0, "height_over_delta": 15.0},
    "anchor": {
        "epsilon": 1.0e-4,
        "height_over_delta": 15.0,
        "n_cycles": 8.0,
        "settle_cycles": 3.0,
        "samples_per_cycle": 64,
        "n_harmonics": 5,
        # ladder placed deep in the asymptotic range (smoke evidence: observed
        # order ~2.0 over cpd 2-8); the production grid cpd=12 (= WP1-5 rig)
        # is the gate-evaluation grid and is bracketed by the finest-two row
        "ladder_cells_per_delta": [6.0, 12.0, 24.0],
        "anchor_eval_cells_per_delta": 12.0,
    },
    "pair": {  # pre-registered settle discipline (STATUS §3 2026-07-21)
        "epsilon": 1.0e-5,
        "height_over_delta": 4.0,
        "cells_per_delta": 8.0,
        "n_cycles": 11.0,
        "settle_cycles": 7.0,
    },
    "ringdown": {
        "height_m": 5.0e-4,
        "n_cells": 64,
        "epsilon": 1.0e-4,
        "n_periods": 12.0,
        # sealed adiabatic box: mode-1 is a true discrete eigenmode (velocity
        # nodes + temperature antinodes at the walls), measured decay = pure
        # bulk prediction — the clean low-dissipation certification. The
        # isothermal variant is an unbuffered-wall-sink DIAGNOSTIC (first
        # authoritative attempt 20260726T074420Z measured its ~14x artifact).
        "boundary": "adiabatic",
        "gamma_ratio_window": [0.85, 1.25],
        "freq_offset_max": 0.01,
        "isothermal_diagnostic_n_cells": [64, 32],  # sink ~ 1/dy scaling probe
    },
    "a1_ablation": {
        "epsilons": [0.005, 0.03, 0.05, 0.10],
        "m2_fit_epsilons": [0.03, 0.05, 0.10],  # memo §2.1 reliable region
        "height_over_delta": 15.0,
        "cells_per_delta": 12.0,
        "n_cycles": 8.0,
        "settle_cycles": 3.0,
        "ramp_cycles": 1.5,
        "representative_epsilon": 0.05,
    },
    "a1_floor_pair": {"epsilon": 0.005, "enabled": True},
    "resolvability_min": 1.0e2,  # amplitude / U95_fit on the 1f line
}

# Toy scaling identical to the instrument tests (alpha x100, c x3): the NSF
# equations and the Phase_1 reference are parameter-free in this respect.
SMOKE_PROTOCOL: dict[str, Any] = {
    "label": "g3_smoke_toy_scaled",
    "frequency_hz": 1.0e4,
    "params_overrides": {"T0": 2700.0, "rho0": 1.177 / 9.0, "kg": 0.2912},
    "equilibrium": {"n_cycles": 10.0, "cells_per_delta": 2.0, "height_over_delta": 6.0},
    "anchor": {
        "epsilon": 1.0e-4,
        "height_over_delta": 6.0,
        "n_cycles": 5.0,
        "settle_cycles": 2.0,
        "samples_per_cycle": 64,
        "n_harmonics": 5,
        "ladder_cells_per_delta": [2.0, 4.0, 8.0],
        "anchor_eval_cells_per_delta": 8.0,
    },
    "pair": {  # same pre-registered settle discipline as production
        "epsilon": 1.0e-5,
        "height_over_delta": 4.0,
        "cells_per_delta": 4.0,
        "n_cycles": 11.0,
        "settle_cycles": 7.0,
    },
    "ringdown": {
        "height_m": 5.0e-4,
        "n_cells": 32,
        "epsilon": 1.0e-4,
        "n_periods": 8.0,
        "boundary": "adiabatic",
        "gamma_ratio_window": [0.85, 1.25],
        "freq_offset_max": 0.01,
        "isothermal_diagnostic_n_cells": [],
        "params_overrides": {"nu0": 1.57e-3},  # measurable decay in 8 periods
    },
    "a1_ablation": {
        "epsilons": [0.05],
        "m2_fit_epsilons": [],
        "height_over_delta": 6.0,
        "cells_per_delta": 4.0,
        "n_cycles": 5.0,
        "settle_cycles": 2.0,
        "ramp_cycles": 1.5,
        "representative_epsilon": 0.05,
    },
    "a1_floor_pair": {"epsilon": 0.005, "enabled": False},
    "resolvability_min": 1.0e2,
}

GATES: dict[str, float] = {  # contract §8.2 thresholds (frozen)
    "equilibrium_dp_rel": 1.0e-10,
    "linear_limit_amp_rel": 0.02,
    "linear_limit_phase_deg": 2.0,
    "convergence_order_min": 1.5,
    "finest_two_rel": 0.01,
    "energy_residual_rel": 0.005,
    "leakage_max": 1.0e-8,
    "leakage_sensitivity_min": 1.0e-7,
}

PHYSICS_CORE_FILES = [
    "reference/nonlinear_nsf_1d.py",
    "postproc/multiharmonic_fit.py",
    "reference/constants.py",
    "reference/thermal_admittance.py",
]


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _physics_core_digest(repo_root: Path) -> str:
    h = hashlib.sha256()
    for rel in PHYSICS_CORE_FILES:
        h.update(rel.encode())
        h.update((repo_root / rel).read_bytes())
    return h.hexdigest()[:12]


def _cplx(z: complex) -> dict[str, float]:
    return {"re": float(z.real), "im": float(z.imag), "abs": float(abs(z)),
            "phase_deg": float(math.degrees(math.atan2(z.imag, z.real)))}


def _branches(params: PhysicalParams) -> dict[str, Any]:
    return {
        "g0": g0_measured_transport(params),          # formal 1D-lbm-equivalent
        "phys": physical_air_transport(params),        # formal 1D-physical
        "const": lbm_equivalent_transport(params),     # diagnostic lineage (WP1-5)
    }


# ---------------------------------------------------------------------------
# measurement blocks
# ---------------------------------------------------------------------------


def _store_series(h5: h5py.File, label: str, res: NSF1DResult, **attrs: Any) -> None:
    grp = h5.create_group(f"runs/{label}")
    grp.create_dataset("t", data=res.t_samples)
    grp.create_dataset("q_wall_conductive", data=res.q_wall_conductive)
    grp.create_dataset("q_wall_applied", data=res.q_wall_applied)
    grp.create_dataset("T_wall", data=res.wall_temperature)
    grp.create_dataset("p_wall", data=res.p_wall)
    grp.create_dataset("p_box_mean", data=res.p_box_mean)
    grp.create_dataset("mass", data=res.mass_series)
    for key, val in {**res.metadata(), **attrs}.items():
        grp.attrs[key] = val if val is not None else "none"


def _store_spectrum(h5: h5py.File, label: str, fit) -> None:
    freq, mag = residual_spectrum_fft(fit)
    grp = h5.create_group(f"residual_spectra/{label}")
    grp.create_dataset("freq_hz", data=freq)
    grp.create_dataset("magnitude", data=mag)


def _a1_run(
    params: PhysicalParams,
    transport,
    proto: dict[str, Any],
    epsilon: float,
    frequency_hz: float,
    sign: float = 1.0,
) -> dict[str, Any]:
    """One A1 signed-zero-mean flux run; returns T-side and p-side fits."""

    omega = omega_from_frequency(frequency_hz)
    y_hs = thermal_admittance_halfspace(frequency_hz, params)
    q1 = epsilon * params.T0 * abs(y_hs)
    alpha0 = float(transport.k(params.T0)) / (params.rho0 * params.cp)
    delta_t = math.sqrt(2.0 * alpha0 / omega)
    n_cells = int(round(proto["height_over_delta"] * proto["cells_per_delta"]))
    drive = WallDrive(
        kind="flux", frequency_hz=frequency_hz, amplitude=sign * q1,
        mean=0.0, ramp_cycles=float(proto["ramp_cycles"]),
    )
    cfg = NSF1DConfig(
        params=params, transport=transport, drive=drive,
        height_m=proto["height_over_delta"] * delta_t, n_cells=n_cells,
        n_cycles=float(proto["n_cycles"]),
    )
    res = run_nsf1d(cfg)
    mask = res.t_samples >= float(proto["settle_cycles"]) / frequency_hz * (1.0 - 1e-12)
    t = res.t_samples[mask]
    fit_tw = fit_multiharmonic(t, res.wall_temperature[mask], omega, n_harmonics=5)
    fit_p = fit_multiharmonic(t, res.p_box_mean[mask], omega, n_harmonics=5)
    fit_q = fit_multiharmonic(t, res.q_wall_applied[mask], omega, n_harmonics=5)
    return {"result": res, "q1": q1, "fit_T": fit_tw, "fit_p": fit_p, "fit_q": fit_q}


def run_g3(output_root: Path | None = None, smoke: bool = False) -> dict[str, Any]:
    proto = SMOKE_PROTOCOL if smoke else PRODUCTION_PROTOCOL
    repo_root = Path(__file__).resolve().parents[1]
    f0 = float(proto["frequency_hz"])
    omega = omega_from_frequency(f0)
    params = default_params(**proto["params_overrides"])
    branches = _branches(params)
    formal = ["g0", "phys"]

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = Path(output_root) if output_root else repo_root / "results" / "phase5" / CASE_FAMILY
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    h5 = h5py.File(out_dir / "signals.h5", "w")
    harmonic_payloads: dict[str, Any] = {}

    def log(msg: str) -> None:
        print(f"G3 {msg}", flush=True)

    # ---- 1. equilibrium preservation (branch-independent: all laws anchored
    #         at T0 coincide on the uniform state by construction) ----
    eq_proto = proto["equilibrium"]
    eq = equilibrium_fixture(
        params=params, transport=branches["g0"], frequency_hz=f0,
        n_cells=int(round(eq_proto["cells_per_delta"] * eq_proto["height_over_delta"])),
        height_m=eq_proto["height_over_delta"]
        * math.sqrt(2.0 * params.alpha0 / omega),
        n_cycles=float(eq_proto["n_cycles"]),
    )
    _store_series(h5, "equilibrium", eq["result"], block="equilibrium", branch="g0")
    log("equilibrium: max|dp|/p0=%.3e mach=%.3e" % (eq["max_dp_rel"], eq["max_mach"]))

    # ---- 2+3. linear anchor + grid ladder, per formal branch ----
    anchor_proto = proto["anchor"]
    ladder = list(anchor_proto["ladder_cells_per_delta"])
    eval_cpd = float(anchor_proto["anchor_eval_cells_per_delta"])
    anchors: dict[str, dict[float, dict[str, Any]]] = {}
    for br in formal:
        anchors[br] = {}
        for cpd in ladder:
            lin = linear_admittance_fixture(
                params=params, transport=branches[br], frequency_hz=f0,
                epsilon=float(anchor_proto["epsilon"]),
                height_over_delta=float(anchor_proto["height_over_delta"]),
                cells_per_delta=float(cpd),
                n_cycles=float(anchor_proto["n_cycles"]),
                settle_cycles=float(anchor_proto["settle_cycles"]),
                samples_per_cycle=int(anchor_proto["samples_per_cycle"]),
                n_harmonics=int(anchor_proto["n_harmonics"]),
            )
            anchors[br][cpd] = lin
            label = f"anchor_{br}_cpd{cpd:g}"
            _store_series(h5, label, lin["result"], block="anchor", branch=br,
                          cells_per_delta=cpd)
            log("anchor %s cpd=%g: amp_corr=%+.4f%% phase_corr=%+.4f deg" % (
                br, cpd, 100.0 * lin["amp_error_corrected"],
                lin["phase_error_deg_corrected"]))
        eval_lin = anchors[br][eval_cpd]
        harmonic_payloads[f"anchor_{br}_q"] = eval_lin["fits"]["q"].to_json_payload()
        harmonic_payloads[f"anchor_{br}_p_box"] = eval_lin["fits"]["p_box"].to_json_payload()
        _store_spectrum(h5, f"anchor_{br}_q", eval_lin["fits"]["q"])
        _store_spectrum(h5, f"anchor_{br}_p_box", eval_lin["fits"]["p_box"])

    def _ladder_metrics(br: str) -> dict[str, Any]:
        ys = [anchors[br][c]["Y_measured_corrected"] for c in ladder]
        d_coarse = abs(ys[0] - ys[1])
        d_fine = abs(ys[1] - ys[2])
        order = (math.log(d_coarse / d_fine) / math.log(2.0)
                 if d_coarse > 0 and d_fine > 0 else float("nan"))
        finest_two = abs(ys[1] - ys[2]) / abs(ys[2])
        return {
            "ladder_cells_per_delta": ladder,
            "Y_corrected": [_cplx(y) for y in ys],
            "coarse_pair_diff": float(d_coarse),
            "fine_pair_diff": float(d_fine),
            "observed_order": float(order),
            "finest_two_rel_diff": float(finest_two),
        }

    ladder_rows = {br: _ladder_metrics(br) for br in formal}
    for br in formal:
        log("ladder %s: order=%.2f finest_two=%.3e" % (
            br, ladder_rows[br]["observed_order"], ladder_rows[br]["finest_two_rel_diff"]))

    # ---- 5. linearization-leakage fixture (pre-registered Dirichlet pair) ----
    pair_proto = proto["pair"]
    pairs: dict[str, dict[str, Any]] = {}
    for br in formal:
        pairs[br] = antisymmetric_pair_fixture(
            params=params, transport=branches[br], frequency_hz=f0,
            epsilon=float(pair_proto["epsilon"]),
            height_over_delta=float(pair_proto["height_over_delta"]),
            cells_per_delta=float(pair_proto["cells_per_delta"]),
            n_cycles=float(pair_proto["n_cycles"]),
            settle_cycles=float(pair_proto["settle_cycles"]),
            threshold=GATES["leakage_max"],
        )
        for tag, res_pm in zip(("plus", "minus"), pairs[br]["results"]):
            _store_series(h5, f"pair_{br}_{tag}", res_pm, block="pair", branch=br)
        log("pair %s: even=%.3e 3f=%.3e physical2f=%.3e" % (
            br, pairs[br]["max_even_leakage_odd_combination"],
            pairs[br]["third_harmonic_odd_combination"],
            pairs[br]["physical_2f_rel_even_combination"]))

    # ---- 7. low-Mach resolvability: real-air ringdown + anchor SNR ----
    ring_proto = proto["ringdown"]
    # ringdown uses its own params (production: pure frozen air; smoke boosts
    # nu only — mixing in the toy alpha x100 scaling would make the diffusive
    # CFL dominate and blow the runtime without adding certification content)
    ring_params = default_params(**ring_proto.get("params_overrides", {}))
    ring = acoustic_ringdown_fixture(
        params=ring_params, transport=None,
        n_cells=int(ring_proto["n_cells"]), height_m=float(ring_proto["height_m"]),
        epsilon=float(ring_proto["epsilon"]), n_periods=float(ring_proto["n_periods"]),
        boundary=str(ring_proto["boundary"]),
    )
    _store_series(h5, "ringdown", ring["result"], block="ringdown", branch="const",
                  boundary=ring["boundary"])
    log("ringdown[%s]: gamma_ratio=%.3f freq_offset=%.5f retention=%.3f" % (
        ring["boundary"], ring["gamma_ratio"], ring["frequency_offset_rel"],
        ring["amplitude_retention"]))

    # isothermal-end DIAGNOSTIC (informational): the unbuffered wall sink at
    # the pressure antinode gives parasitic damping ~ 2k/dy, i.e. the excess
    # over bulk should roughly HALVE from N=64 to N=32 — the opposite trend
    # of scheme dissipation (which grows on coarser grids). Non-degeneracy
    # evidence for the adiabatic gate-row design.
    iso_diag: list[dict[str, Any]] = []
    iso_diag_results: list[NSF1DResult] = []
    for n_iso in ring_proto.get("isothermal_diagnostic_n_cells", []):
        r_iso = acoustic_ringdown_fixture(
            params=ring_params, transport=None,
            n_cells=int(n_iso), height_m=float(ring_proto["height_m"]),
            epsilon=float(ring_proto["epsilon"]),
            n_periods=float(ring_proto["n_periods"]), boundary="isothermal",
        )
        _store_series(h5, f"ringdown_iso_n{n_iso}", r_iso["result"],
                      block="ringdown_diagnostic", branch="const", boundary="isothermal")
        iso_diag_results.append(r_iso["result"])
        iso_diag.append({
            "n_cells": int(n_iso),
            "gamma_ratio": r_iso["gamma_ratio"],
            "gamma_measured": r_iso["gamma_measured"],
            "gamma_excess_over_bulk": r_iso["gamma_measured"] - r_iso["gamma_predicted_bulk"],
        })
        log("ringdown[isothermal diag] N=%d: gamma_ratio=%.3f excess=%.1f/s" % (
            n_iso, r_iso["gamma_ratio"], iso_diag[-1]["gamma_excess_over_bulk"]))

    # resolvability = 1f amplitude / U95_fit (statistically grounded: the
    # residual contains the physical box-mode transient, which must not be
    # penalized; raw residual-rms SNR is kept as info, spectra are archived)
    resolvability: dict[str, dict[str, float]] = {}
    snr_info: dict[str, dict[str, float]] = {}
    for br in formal:
        fits = anchors[br][eval_cpd]["fits"]
        resolvability[br] = {
            sig: float(fits[sig].amplitude(1) / max(fits[sig].amplitude_u95(1), 1e-300))
            for sig in ("q", "p_box")}
        snr_info[br] = {
            sig: float(fits[sig].amplitude(1) / max(fits[sig].residual_rms, 1e-300))
            for sig in ("q", "p_box")}
    log("anchor resolvability amp/u95: g0 q=%.2e p=%.2e | phys q=%.2e p=%.2e" % (
        resolvability["g0"]["q"], resolvability["g0"]["p_box"],
        resolvability["phys"]["q"], resolvability["phys"]["p_box"]))

    # ---- review block A: p-side dual-property H2 ablation (pre-registered) ----
    abl_proto = proto["a1_ablation"]
    ablation: dict[str, dict[float, dict[str, Any]]] = {}
    for br in ("const", "g0", "phys"):
        ablation[br] = {}
        for eps in abl_proto["epsilons"]:
            one = _a1_run(params, branches[br], abl_proto, float(eps), f0)
            ablation[br][float(eps)] = one
            res = one["result"]
            label = f"a1_{br}_eps{eps:g}"
            _store_series(h5, label, res, block="a1_ablation", branch=br, epsilon=eps)
            log("a1 %s eps=%.3f: G1=%.5e H2p=%.3e H2T=%.3e" % (
                br, eps,
                one["fit_T"].amplitude(1) / one["q1"],
                one["fit_p"].leakage_relative(target=1)[2],
                one["fit_T"].leakage_relative(target=1)[2]))
    rep_eps = float(abl_proto["representative_epsilon"])
    for br in ("const", "g0", "phys"):
        harmonic_payloads[f"a1_{br}_eps{rep_eps:g}_p_box"] = (
            ablation[br][rep_eps]["fit_p"].to_json_payload())
        harmonic_payloads[f"a1_{br}_eps{rep_eps:g}_T_wall"] = (
            ablation[br][rep_eps]["fit_T"].to_json_payload())
        _store_spectrum(h5, f"a1_{br}_eps{rep_eps:g}_p_box", ablation[br][rep_eps]["fit_p"])

    def _h2p(br: str, eps: float) -> float:
        return float(ablation[br][eps]["fit_p"].leakage_relative(target=1)[2])

    def _h2t(br: str, eps: float) -> float:
        return float(ablation[br][eps]["fit_T"].leakage_relative(target=1)[2])

    abl_table = []
    for eps in abl_proto["epsilons"]:
        eps = float(eps)
        row: dict[str, Any] = {"epsilon": eps}
        for br in ("const", "g0", "phys"):
            one = ablation[br][eps]
            row[br] = {
                "G1_T_side_K_per_Wm2": float(one["fit_T"].amplitude(1) / one["q1"]),
                "p1f_Pa": float(one["fit_p"].amplitude(1)),
                "H2_p_side": _h2p(br, eps),
                "H3_p_side": float(one["fit_p"].leakage_relative(target=1)[3]),
                "H2_T_side": _h2t(br, eps),
                "H3_T_side": float(one["fit_T"].leakage_relative(target=1)[3]),
            }
        if all(_h2p(b, eps) > 0 for b in ("g0", "phys")):
            d_prop = _h2p("phys", eps) - _h2p("g0", eps)
            d_ref = _h2p("g0", eps)
            row["dab2_pside"] = {
                "delta_prop": float(d_prop),
                "delta_ref": float(d_ref),
                "ratio_vs_0p3_delta_ref": float(abs(d_prop) / (0.3 * abs(d_ref)))
                if d_ref else float("nan"),
                "phys_over_g0": float(_h2p("phys", eps) / _h2p("g0", eps)),
            }
        abl_table.append(row)

    # m2 (p-side, g0 branch) over the pre-registered reliable region
    m2_eps = [float(e) for e in abl_proto["m2_fit_epsilons"]]
    m2_pside: dict[str, float] = {}
    if len(m2_eps) >= 2:
        for br in ("const", "g0", "phys"):
            x = np.log([e for e in m2_eps])
            y = np.log([_h2p(br, e) * ablation[br][e]["fit_p"].amplitude(1)
                        for e in m2_eps])  # absolute 2f amplitude scaling
            m2_pside[br] = float(np.polyfit(x, y, 1)[0])

    # D_G from the flux-protocol ladder (T-side gain, per branch)
    eps_list = [float(e) for e in abl_proto["epsilons"]]
    d_g: dict[str, float] = {}
    if len(eps_list) >= 2:
        for br in ("const", "g0", "phys"):
            g_small = ablation[br][eps_list[0]]["fit_T"].amplitude(1) / ablation[br][eps_list[0]]["q1"]
            g_large = ablation[br][eps_list[-1]]["fit_T"].amplitude(1) / ablation[br][eps_list[-1]]["q1"]
            d_g[br] = float(abs(g_large / g_small - 1.0))

    # ---- review block B: A1 flux-protocol leakage floor at production settle ----
    a1_floor: dict[str, Any] | None = None
    floor_results: list[NSF1DResult] = []
    if proto["a1_floor_pair"]["enabled"]:
        eps_f = float(proto["a1_floor_pair"]["epsilon"])
        plus = _a1_run(params, branches["g0"], abl_proto, eps_f, f0, sign=+1.0)
        minus = _a1_run(params, branches["g0"], abl_proto, eps_f, f0, sign=-1.0)
        rp, rm = plus["result"], minus["result"]
        _store_series(h5, "a1_floor_plus", rp, block="a1_floor", branch="g0")
        _store_series(h5, "a1_floor_minus", rm, block="a1_floor", branch="g0")
        floor_results.extend([rp, rm])
        mask = rp.t_samples >= float(abl_proto["settle_cycles"]) / f0 * (1.0 - 1e-12)
        t = rp.t_samples[mask]
        q_odd = 0.5 * (rp.wall_temperature[mask] - rm.wall_temperature[mask])
        fit_odd = fit_multiharmonic(t, q_odd, omega, n_harmonics=5)
        leak = fit_odd.leakage_relative(target=1)
        a1_floor = {
            "protocol": "a1_flux_signed_pair_odd_combination_T_side",
            "epsilon": eps_f,
            "settle_cycles": float(abl_proto["settle_cycles"]),
            "leakage_2f": float(leak[2]),
            "leakage_3f": float(leak[3]),
            "leakage_4f": float(leak[4]),
            "note": "rig measurement floor at production settle (U_det input); "
                    "NOT the <=1e-8 gate row (that row is the Dirichlet pair "
                    "fixture with pre-registered settle discipline)",
        }
        log("a1 floor: 2f=%.3e 3f=%.3e 4f=%.3e" % (
            a1_floor["leakage_2f"], a1_floor["leakage_3f"], a1_floor["leakage_4f"]))

    # ---- energy / mass residual collection (all certification runs) ----
    def _collect_results() -> list[NSF1DResult]:
        out = [eq["result"], ring["result"]]
        out.extend(iso_diag_results)
        for br in formal:
            out.extend(anchors[br][c]["result"] for c in ladder)
            out.extend(pairs[br]["results"])
        for br in ablation:
            out.extend(one["result"] for one in ablation[br].values())
        out.extend(floor_results)
        return out

    all_results = _collect_results()
    # rel_flux is meaningful for FLUX-CARRYING runs only; the undriven
    # equilibrium run and the sealed adiabatic ringdown have integrated-|flux|
    # denominators at machine zero (the ratio is noise/noise) — their energy
    # closure is gated via rel_total in their own rows
    zero_flux = {id(eq["result"])}
    if ring["boundary"] == "adiabatic":
        zero_flux.add(id(ring["result"]))
    driven_results = [r for r in all_results if id(r) not in zero_flux]
    energy_max = max(r.energy_residual_rel_flux for r in driven_results)
    mass_max = max(r.mass_drift_rel for r in all_results)
    mach_max = max(r.max_mach for r in all_results)

    # ---- gate evaluation (contract §8.2) ----
    lin_amp = {br: abs(anchors[br][eval_cpd]["amp_error_corrected"]) for br in formal}
    lin_phase = {br: abs(anchors[br][eval_cpd]["phase_error_deg_corrected"]) for br in formal}
    gr = ring_proto["gamma_ratio_window"]
    gate_rows: dict[str, dict[str, Any]] = {
        "equilibrium_preservation": {
            "value": eq["max_dp_rel"], "gate": GATES["equilibrium_dp_rel"],
            "n_cycles": eq_proto["n_cycles"],
            "energy_residual_rel_total": float(eq["result"].energy_residual_rel_total),
            "passed": bool(eq["max_dp_rel"] < GATES["equilibrium_dp_rel"]
                           and eq["result"].energy_residual_rel_total <= 1.0e-12),
            "note": "branch-independent: anchored laws coincide on the uniform state; "
                    "undriven energy closure gated on rel_total (flux integral is "
                    "machine zero, rel_flux is noise/noise)",
        },
        "linear_limit_amplitude": {
            "value_by_branch": lin_amp, "gate": GATES["linear_limit_amp_rel"],
            "eval_cells_per_delta": eval_cpd,
            "reference": "Phase_1 half-space admittance (closed-box corrected)",
            "passed": bool(all(v <= GATES["linear_limit_amp_rel"] for v in lin_amp.values())),
        },
        "linear_limit_phase": {
            "value_by_branch": lin_phase, "gate": GATES["linear_limit_phase_deg"],
            "eval_cells_per_delta": eval_cpd,
            "passed": bool(all(v <= GATES["linear_limit_phase_deg"] for v in lin_phase.values())),
        },
        "grid_convergence": {
            "by_branch": ladder_rows,
            "gate_order_min": GATES["convergence_order_min"],
            "gate_finest_two_rel": GATES["finest_two_rel"],
            "passed": bool(all(
                np.isfinite(ladder_rows[br]["observed_order"])
                and ladder_rows[br]["observed_order"] >= GATES["convergence_order_min"]
                and ladder_rows[br]["finest_two_rel_diff"] <= GATES["finest_two_rel"]
                for br in formal)),
        },
        "total_energy_residual": {
            "value": float(energy_max), "gate": GATES["energy_residual_rel"],
            "definition": "max over all runs of |dE - int(net flux)| / int(|flux|)",
            "passed": bool(energy_max <= GATES["energy_residual_rel"]),
        },
        "linearization_leakage": {
            "by_branch": {br: {
                "max_even_in_odd": pairs[br]["max_even_leakage_odd_combination"],
                "third_harmonic": pairs[br]["third_harmonic_odd_combination"],
                "physical_2f_sensitivity": pairs[br]["physical_2f_rel_even_combination"],
            } for br in formal},
            "gate": GATES["leakage_max"],
            "sensitivity_min": GATES["leakage_sensitivity_min"],
            "passed": bool(all(
                pairs[br]["max_even_leakage_odd_combination"] <= GATES["leakage_max"]
                and pairs[br]["third_harmonic_odd_combination"] <= GATES["leakage_max"]
                and pairs[br]["physical_2f_rel_even_combination"]
                >= GATES["leakage_sensitivity_min"]
                for br in formal)),
            "note": "pass requires the numerical floor AND the physical-2f "
                    "sensitivity counter-check (non-degenerate fixture)",
        },
        "low_mach_resolvability": {
            "ringdown_boundary": ring["boundary"],
            "ringdown_gamma_ratio": ring["gamma_ratio"],
            "ringdown_freq_offset_rel": ring["frequency_offset_rel"],
            "ringdown_window": gr,
            "ringdown_energy_residual_rel_total": float(
                ring["result"].energy_residual_rel_total),
            "isothermal_sink_diagnostic": iso_diag or None,
            "anchor_resolvability_amp_over_u95": resolvability,
            "resolvability_min": proto["resolvability_min"],
            "anchor_snr_info_amp_over_residual_rms": snr_info,
            "max_mach": float(mach_max),
            "passed": bool(
                gr[0] <= ring["gamma_ratio"] <= gr[1]
                and abs(ring["frequency_offset_rel"]) <= ring_proto["freq_offset_max"]
                and ring["result"].energy_residual_rel_total <= 1.0e-12
                and all(v >= proto["resolvability_min"]
                        for br in resolvability.values() for v in br.values())),
            "note": "sealed adiabatic ringdown (mode-1 = true discrete "
                    "eigenmode): measured decay vs pure bulk prediction is "
                    "the direct scheme-dissipation bound; the isothermal "
                    "variant is an unbuffered-wall-sink diagnostic (excess "
                    "~1/dy, opposite of scheme dissipation). 1f amplitudes "
                    "resolved above fit uncertainty; residual spectra "
                    "archived in signals.h5 (physical box-mode transient "
                    "audited, not penalized)",
        },
        "numerical_discipline": {
            "no_clipping": True, "no_floor": True, "no_positivity_repair": True,
            "max_mass_drift_rel": float(mass_max),
            "passed": bool(mass_max <= 1.0e-12),
        },
    }
    verdict = "PASSED" if all(r["passed"] for r in gate_rows.values()) else "FAILED"
    log("verdict=%s (energy=%.2e mass=%.2e mach=%.2e)" % (
        verdict, energy_max, mass_max, mach_max))

    # ---- §16.3 result fields (representative point: g0 branch, A1 eps=0.05) ----
    rep = ablation["g0"][rep_eps]
    na = "not_applicable_1d_reference"
    results_block = {
        "representative_point": {"branch": "g0", "protocol": "a1_flux", "epsilon": rep_eps},
        "T_s_hat_1f": _cplx(rep["fit_T"].harmonic(1)),
        "p_hat_1f": _cplx(rep["fit_p"].harmonic(1)),
        "p_hat_2f": _cplx(rep["fit_p"].harmonic(2)),
        "p_hat_3f": _cplx(rep["fit_p"].harmonic(3)),
        "outgoing_mode_1f": None, "outgoing_mode_2f": None, "outgoing_mode_3f": None,
        "outgoing_mode_note": "no outgoing acoustic mode in the closed 1D rig",
        "G1": float(rep["fit_T"].amplitude(1) / rep["q1"]),
        "D_G": d_g,
        "D_OP": None,
        "D_OP_note": "A2a operating point not re-run in G3; measured in the "
                     "G0-hookup review (route memo §8: g0 +1.25%, phys +0.87%)",
        "H2": _h2p("g0", rep_eps),
        "H3": float(rep["fit_p"].leakage_relative(target=1)[3]),
        "H3_note": "upper-bound caliber: at/below the rig floor (see a1_leakage_floor)",
        "m1": None,
        "m2": m2_pside if m2_pside else None,
        "m3": None,
        "m3_note": "3f below measurement floor; upper bound only",
        "QS0_error_amplitude": None, "QS0_error_phase": None,
        "QS1_error_amplitude": None, "QS1_error_phase": None,
        "QS_note": "QS rules are exercised in the A2a review (memo §2/§8), not in G3",
        "wall_boundary_sensitivity": None,
        "wall_boundary_note": na + " (G1-W quantity; this solver is its reference)",
        "operator_sensitivity_D_G": None,
        "operator_sensitivity_H2": None,
        "operator_sensitivity_H3": None,
        "operator_note": na + " (no spectral correction/filter operators in 1D FV)",
        "boundary_mass_flux_0f_to_3f": [0.0, 0.0, 0.0, 0.0],
        "boundary_mass_flux_note": "zero normal mass flux by construction; "
                                   "measured mass drift is the audit",
        "energy_residual": float(energy_max),
        "mass_or_flux_residual": float(mass_max),
        "wall_temperature_error": float(
            abs(anchors["g0"][eval_cpd]["T_s_hat"])
            / (float(anchor_proto["epsilon"]) * params.T0) - 1.0),
    }

    # ---- resolved config / metadata / provenance ----
    finest_lin = anchors["g0"][eval_cpd]  # production-representative grid
    dy = finest_lin["height_m"] / finest_lin["n_cells"]
    resolved_config = {
        "gate_id": GATE_ID, "case_family": CASE_FAMILY, "protocol": proto,
        "gates": GATES,
        "branches": {
            "formal": {
                "1D-lbm-equivalent": branches["g0"].property_model_id,
                "1D-physical": branches["phys"].property_model_id,
            },
            "diagnostic_lineage": branches["const"].property_model_id,
            "g0_measured_exponents": {"k": branches["g0"].k_exponent,
                                      "mu": branches["g0"].mu_exponent},
            "anchor_note": "all branches anchored at frozen (mu, kg, T0); "
                           "k1 single-point surrogate caveat frozen in "
                           "reference/nonlinear_nsf_1d.py docstring",
        },
        "params_si": {"T0": params.T0, "p0": params.p0, "rho0": params.rho0,
                      "cp": params.cp, "kg": params.kg, "nu0": params.nu0,
                      "mu_bulk": params.mu_bulk},
    }
    config_yaml = yaml.safe_dump(resolved_config, allow_unicode=True, sort_keys=False)
    (out_dir / "config_resolved.yaml").write_text(config_yaml, encoding="utf-8")

    fit_q_payload = harmonic_payloads["anchor_g0_q"]
    summary = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "code_commit": _git_commit(),
        "config_digest": _sha256_bytes(config_yaml.encode())[:12],
        "physics_core_digest": _physics_core_digest(repo_root),
        "parent_baseline_run": PARENT_BASELINE_RUN,
        "phase5_contract_version": PHASE5_CONTRACT_VERSION,
        "work_package": "WP2",
        "gate_id": GATE_ID,
        "case_family": CASE_FAMILY,
        "model_route": "ROUTE_B_MAIN",
        "property_model_id": {
            "1D-lbm-equivalent": branches["g0"].property_model_id,
            "1D-physical": branches["phys"].property_model_id,
            "diagnostic_lineage": branches["const"].property_model_id,
        },
        "tau_policy": na + " (transport laws archived per branch)",
        "mapping_digest": na,
        "background_path": "uniform_T0_equilibrium",
        "forcing_protocol": "temperature_anchor + a1_signed_zero_mean_flux "
                            "+ dirichlet_signed_pair + acoustic_ringdown",
        "P_mean_W_m2": 0.0,
        "P_mean_rematched": False,
        "target_Theta_DC": 0.0,
        "frequency_Hz": f0,
        "T_ambient_K": params.T0,
        "T_mean_K": params.T0,
        "epsilon_AC_measured": {"anchor": anchor_proto["epsilon"],
                                "pair": pair_proto["epsilon"],
                                "a1_ladder": abl_proto["epsilons"]},
        "Theta_DC_measured": 0.0,
        "chi_0": None, "chi_eff": None, "C_A_J_m2K": None,
        "chi_note": "no film protocol in G3 certification blocks "
                    "(film ODE smoke-tested at instrument level)",
        "dc_heat_sink_model": "canonical_isothermal_lid_T_ambient",
        "dc_heat_sink_parameters": {
            "lid_temperature_K": params.T0,
            "height_over_delta": anchor_proto["height_over_delta"]},
        "H_s_role": "rig domain height (certification); not a heat-sink study",
        "thermal_resistance_effective": None,
        "grid_shape": [finest_lin["n_cells"]],
        "dx_m": dy,
        "dt_s": finest_lin["result"].dt,
        "domain_height_m": finest_lin["height_m"],
        "boundary_model": "nsf1d_zero_mass_flux_noslip_wall + isothermal_reservoir_lid",
        "wall_mass_policy": "zero_normal_mass_flux_by_construction",
        "wall_neutrality_gate_id": na + " (independent reference for G1-W)",
        "boundary_mass_flux_definition": "convective wall flux == [0, p_w, 0] exactly",
        "boundary_mass_flux_0f_to_3f": [0.0, 0.0, 0.0, 0.0],
        "spectral_operator_stack_id": "none_1d_fv_central_rk4",
        "spectral_correction_enabled": False,
        "high_wavenumber_filter_enabled": False,
        "high_wavenumber_filter_strength": 0.0,
        "operator_ablation_run_id": None,
        "q_feedback_relax": None,
        "fit_window": {"settle_cycles": anchor_proto["settle_cycles"],
                       "fit_cycles": anchor_proto["n_cycles"] - anchor_proto["settle_cycles"]},
        "fit_cycles": anchor_proto["n_cycles"] - anchor_proto["settle_cycles"],
        "detrend_order": 0,
        "harmonic_order_max": 5,
        "harmonic_fit_condition_number": fit_q_payload["harmonic_fit_condition_number"],
        "U_det": {"grid_finest_two_rel": {br: ladder_rows[br]["finest_two_rel_diff"]
                                          for br in formal}},
        "U95_fit": {"anchor_g0_q_1f_amp": fit_q_payload["amplitude_u95_fit"][0]},
        "U_gov": float(max(max(ladder_rows[br]["finest_two_rel_diff"] for br in formal),
                           fit_q_payload["amplitude_u95_fit"][0]
                           / max(fit_q_payload["amplitude"][0], 1e-300))),
        "no_clipping": True, "no_floor": True, "no_positivity_repair": True,
        "gate_status": verdict,
        "scoped_limitations": [],
        "smoke_mode": bool(smoke),
        "solver_id": SOLVER_ID,
        "results": results_block,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=1, default=float), encoding="utf-8")

    (out_dir / "harmonic_fit.json").write_text(
        json.dumps(harmonic_payloads, indent=1, default=float), encoding="utf-8")

    provenance = {
        "run_id": run_id,
        "command": " ".join(sys.argv),
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "code_commit": summary["code_commit"],
        "physics_core_digest": summary["physics_core_digest"],
        "physics_core_files": {
            rel: _sha256_bytes((repo_root / rel).read_bytes())[:12]
            for rel in PHYSICS_CORE_FILES},
        "solver_id": SOLVER_ID,
        "parent_baseline_run": PARENT_BASELINE_RUN,
        "g0_law_source": "docs/Phase_5/nonlinear_model_freeze.md §1/§3 "
                         "(k_eff∝T^1.04, mu_eff∝T^-0.60 at k1, 270-360 K)",
    }
    (out_dir / "provenance.json").write_text(
        json.dumps(provenance, indent=1), encoding="utf-8")

    gate_eval = {
        "gate_id": GATE_ID, "verdict": verdict, "rows": gate_rows,
        "review_blocks": {
            "p_side_dual_property_ablation": {
                "preregistration": "route_ab_decision_memo.md §6/§7 (p-side H2 归 G3)",
                "table": abl_table,
                "m2_pside_absolute_2f_scaling": m2_pside or None,
                "D_G_flux_ladder": d_g,
                "note": "informational review, not a gate row; feeds the route memo",
            },
            "a1_leakage_floor": a1_floor,
        },
    }
    (out_dir / "gate_evaluation.json").write_text(
        json.dumps(gate_eval, indent=1, default=float), encoding="utf-8")

    report = [
        f"# G3 run {run_id}", "",
        f"- verdict: **{verdict}** (script-emittable; PASSED/FAILED only for G3)",
        f"- smoke_mode: {smoke}",
        f"- solver: {SOLVER_ID}; commit {summary['code_commit'][:12]}; "
        f"physics core digest {summary['physics_core_digest']}",
        f"- formal branches: 1D-lbm-equivalent={branches['g0'].property_model_id}, "
        f"1D-physical={branches['phys'].property_model_id}",
        "", "## Gate rows (contract §8.2)", "",
    ]
    for name, row in gate_rows.items():
        detail = {k: v for k, v in row.items() if k not in ("passed", "note", "by_branch")}
        report.append(f"- {name}: passed={row['passed']}  "
                      + json.dumps(detail, default=float)[:200])
    report += ["", "## Review blocks", ""]
    for row in abl_table:
        line = f"- eps={row['epsilon']:g}: " + ", ".join(
            f"{br} H2p={row[br]['H2_p_side']:.3e}" for br in ("const", "g0", "phys"))
        if "dab2_pside" in row:
            line += f"  | phys/g0={row['dab2_pside']['phys_over_g0']:.2f} " \
                    f"ratio_vs_0.3dref={row['dab2_pside']['ratio_vs_0p3_delta_ref']:.2f}"
        report.append(line)
    if a1_floor:
        report.append(f"- a1 floor (T-side odd pair, settle "
                      f"{a1_floor['settle_cycles']:g}): 2f={a1_floor['leakage_2f']:.3e} "
                      f"3f={a1_floor['leakage_3f']:.3e}")
    (out_dir / "run_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    h5.close()
    log(f"outputs -> {out_dir}")
    return {"verdict": verdict, "out_dir": str(out_dir), "summary": summary,
            "gate_rows": gate_rows, "ablation_table": abl_table,
            "a1_floor": a1_floor, "ladder": ladder_rows}


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase_5 G3 1D NSF reference certification")
    parser.add_argument("--smoke", action="store_true",
                        help="toy-scaled machinery run (contract test only; not authoritative)")
    parser.add_argument("--output-root", type=Path, default=None)
    args = parser.parse_args()
    result = run_g3(args.output_root, smoke=args.smoke)
    return 0 if result["verdict"] == "PASSED" else 1


if __name__ == "__main__":
    sys.exit(main())
