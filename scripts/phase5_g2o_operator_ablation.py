"""Phase_5 G2-O spectral-correction / high-wavenumber-filter harmonic ablation gate (contract §7.3, WP2).

The frozen production chain applies, after the wall callback, two global
operator families: the acoustic phase corrections (diagonal + high-mode global
FFT operators) and the conservative biharmonic high-wavenumber filter
(strength 0.0065 x 1 pass). G2-O certifies that these operators do not
generate, selectively amplify or suppress the target harmonics. All ablations
are INSTRUMENT IDENTIFICATION only — production results always use the frozen
pre-registered stack (§0.4); no diagnostic setting is written back.

Operator variants (pre-registered; in-memory config mutations, frozen files
untouched):
  v0_frozen                 production stack (baseline)
  v1_acoustic_corr_off      collision.acoustic_phase_correction_enabled=false.
                            STRUCTURALLY IDENTITY on this rig geometry+config
                            (pre-run mechanism test, before any authoritative
                            run): the diagonal branch has ZERO qualifying
                            modes (needs kx!=0 AND ky!=0 below the frozen
                            low_laplacian 0.01926 — smallest diagonal
                            laplacian on 48x8 is ~0.63) and the high-mode
                            branch early-returns (both high-mode factors are
                            exactly 1.0). An identity operator can neither
                            generate nor suppress harmonics, so for THIS
                            operator family the §7.3 conclusion is EXACT —
                            provided the identity is proven, which is the S6
                            row (byte-level series comparison, falsifiable),
                            not a trivially-passing ablation delta.
  v2_filter_off             numerics.high_wavenumber_filter.enabled=false
  v3_filter_half            numerics.high_wavenumber_filter.strength x 0.5
  v4_dispersion_off_diag    collision.dispersion_correction_enabled=false —
                            EXTRA diagnostic column (both mandatory
                            frequencies, excluded from gating): the
                            in-collision dispersion correction is part of the
                            G0-calibrated transport closure applied BEFORE the
                            wall callback, not a §7.3 post-callback operator —
                            but it is the only ACTIVE global-FFT spectral
                            operator on this rig (P4-1 seam-injection suspect
                            family), so its harmonic sensitivity is archived
                            for attribution completeness.

Fixture set (contract §7.3):
1. Single-tone operator fixture (rows S1): a linearized single-frequency
   carrier through the COMPLETE frozen operator stack. Instrument = the G1-W
   certified signed-pair protocol (eps=1e-4, ramp 2; 10 kHz settle 12 /
   periods 14 verbatim): the odd combination kills all even-order physical
   content (its 2f is the operator/asymmetry floor) and the eps^2-scaled
   physical 3f sits below the gate (G1-W measured 2f=3.3e-10 / 3f=2.77e-9 at
   10 kHz). Run at BOTH mandatory frequencies on the frozen stack.
   SETTLE RULE (learned from the 20260730T103844Z diagnostic run, two-window
   decay discrimination): settle transfers across frequency in BOX-RELAXATION
   units, not periods — tau_box = 1.1 periods @10 kHz but 1.47 @20 kHz
   (measured; window-to-window decay ratio 0.507 = pure transient, zero
   operator platform), so equal-period settle left the 20 kHz odd-2f
   transient at 1.5e-7. Per-frequency overrides keep every frequency at
   >= ~11 tau_box (20 kHz: settle 20 / periods 22 = 13.6 tau). Ring-down
   acoustic carriers are pre-registered as NOT viable for this row: a
   decaying tone leaks ~gamma/omega (~1e-3) into neighbouring LS-fit bins —
   orders above the 1e-8 gate — so only driven steady carriers qualify.
2. Normalized nonlinear ablation (rows S2/S3): per variant x frequency, a
   small-amplitude 1f baseline (eps=0.001) plus a production point
   (eps=0.05), G1a protocol verbatim (periods 3 / settle 1 / ramp 1).
   Each variant is normalized by its OWN baseline (contract fixture item 3:
   an operator toggle changes the linear effective medium — alpha_eff(k) was
   measured WITH the frozen stack — and that linear change must not be
   misread as nonlinearity):
     D_G(v)  = |Y_energy(0.05)| / |Y_energy(0.001)| - 1     (within-variant)
     H2q(v)  = 2f/1f of the wall heat-flux moment at eps=0.05 (N=5 joint fit)
   Gates: |D_G(v) - D_G(v0)| <= max[1 pp, U_gov(D_G)];
          |H2q(v) - H2q(v0)| <= max[0.1 * H2q(v0), U_gov(H2)] and the weak-
          nonlinear direction (H2 grows with eps) preserved in every variant.
   U_gov from the pre-registered half-period window pair + fit U95 (no
   refinement axis here; G2-T carries the grid axis).
3. Stability row (S4): at least one non-production ablation sequence
   completes stably (contract: if ALL off/reduced variants go unstable the
   verdict can only be SCOPED_CANDIDATE).
4. Attributability row (S5): no single operator toggle flips the main-
   conclusion signs/regimes — operationalized: complex-2f phase shift vs v0
   <= 90 deg, H2 magnitude ratio within [0.5, 2], D_G sign preserved, for
   every gated variant x frequency.
5. Spectral-identity row (S6): for variants pre-registered with
   identity_expected (v1), the recorded q/p series must be EXACTLY equal to
   v0's (max abs diff == 0.0) at every frequency x epsilon. This converts the
   otherwise by-construction-trivial v1 ablation deltas into a falsifiable
   claim: any future threshold/factor/geometry change that re-activates the
   operator breaks S6 instead of silently passing.

Verdict (script-emittable): PASSED = S1+S2+S3+S5+S6 pass and S4 stable;
SCOPED_CANDIDATE = only S4 fails (all ablations unstable) with the other
rows evaluable on the stable subset; FAILED otherwise
(HARMONIC_OPERATOR_ABLATION_FAILED).

Outputs the contract §16.1 seven-file set under
results/phase5/g2_operator_ablation/<run_id>/.
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

import h5py
import numpy as np
import yaml

from postproc.multiharmonic_fit import fit_multiharmonic
from scripts.phase2_m2_verification import load_config
from scripts.phase5_g1a_amplitude_envelope import execute_cases, refit_n5
from scripts.phase5_g1w_wall_neutrality import (
    _cplx,
    _git_commit,
    energy_channel_Y_over_Yhs,
    run_driven,
)
from core.solver import GasSolver2D

GATE_ID = "G2-O"
CASE_FAMILY = "g2_operator_ablation"
PHASE5_CONTRACT_VERSION = "v1.2"
DEFAULT_CONFIG = Path("configs/phase5/g2_operator_ablation/g2o_10k20k_dx2p6.yaml")
PHYSICS_CORE_FILES = [
    "boundary/wall_thermal_mass_neutral.py",
    "boundary/wall_mass_audit.py",
    "postproc/multiharmonic_fit.py",
    "scripts/phase5_g1w_wall_neutrality.py",
    "core/solver.py",
]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _phase_deg(z: complex) -> float:
    return math.degrees(math.atan2(z.imag, z.real))


def apply_mutations(gas_cfg: dict, mutations: dict[str, Any]) -> dict:
    """Deep-copied config with dotted-path mutations (frozen file untouched)."""

    out = copy.deepcopy(gas_cfg)
    for path, value in mutations.items():
        node = out
        keys = path.split(".")
        for k in keys[:-1]:
            node = node.setdefault(k, {})
        node[keys[-1]] = value
    return out


def _g2o_case_worker(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    label = payload["label"]

    def wlog(msg: str) -> None:
        print(f"G2O [{label}] {msg}", flush=True)

    run = run_driven(
        payload["gas_cfg"], payload["wall"], payload["epsilon"],
        frequency_hz=payload["frequency_hz"], periods=payload["periods"],
        settle_periods=payload["settle_periods"],
        samples_per_period=payload["samples_per_period"],
        grad_extrap_old="linear", ramp_periods=payload["ramp_periods"], log=wlog)
    run.pop("recorder", None)
    return label, run


def odd_pair_leakage(plus: dict, minus: dict, frequency: float,
                     settle_periods: float) -> dict[str, Any]:
    """G1-W signed-pair instrument: odd/even combinations, non-target leakage."""

    mask = plus["t_s"] >= settle_periods / frequency * (1.0 - 1e-12)
    t_fit = plus["t_s"][mask]
    out: dict[str, Any] = {}
    for sig in ("q_moment_si", "p_box_lu"):
        odd = 0.5 * (plus[sig][mask] - minus[sig][mask])
        even = 0.5 * (plus[sig][mask] + minus[sig][mask])
        fit_odd = fit_multiharmonic(t_fit, odd, 2.0 * math.pi * frequency, n_harmonics=3)
        fit_even = fit_multiharmonic(t_fit, even, 2.0 * math.pi * frequency, n_harmonics=3)
        leak = fit_odd.leakage_relative(target=1)
        out[sig] = {"odd_2f_rel": float(leak[2]), "odd_3f_rel": float(leak[3]),
                    "even_2f_rel_1f": float(fit_even.amplitude(2) / fit_odd.amplitude(1))}
    out["max_nontarget"] = max(max(v["odd_2f_rel"], v["odd_3f_rel"])
                               for k, v in out.items() if isinstance(v, dict))
    return out


def two_window_sensitivity(run: dict, frequency: float, settle_periods: float,
                           n_harmonics: int) -> dict[str, Any]:
    """Half-period-shifted window pair: U_det proxies for |Y| and H2."""

    omega = 2.0 * math.pi * frequency
    fits = []
    for shift in (0.0, 0.5):
        mask = run["t_s"] >= (settle_periods + shift) / frequency * (1.0 - 1e-12)
        fits.append({
            "p": fit_multiharmonic(run["t_s"][mask], run["p_box_lu"][mask], omega,
                                   n_harmonics=n_harmonics),
            "q": fit_multiharmonic(run["t_s"][mask], run["q_moment_si"][mask], omega,
                                   n_harmonics=n_harmonics)})
    amp_rel = abs(fits[1]["p"].harmonic(1) / fits[0]["p"].harmonic(1)) - 1.0
    h2_pair = [float(f["q"].leakage_relative(1)[2]) for f in fits]
    return {"p1f_amp_rel": float(abs(amp_rel)), "H2q_windows": h2_pair,
            "H2q_diff": float(abs(h2_pair[1] - h2_pair[0]))}


def run_g2o(config_path: Path, output_root: Path | None = None,
            smoke: bool = False, workers: int = 1) -> dict[str, Any]:
    cfg = load_config(config_path)
    proto = cfg["g2o_smoke"] if smoke else cfg["g2o"]
    gates = cfg["gates"]
    gas_cfg_path = Path(cfg["inheritance"]["gas_config_path"])
    repo_root = Path(__file__).resolve().parents[1]

    def log(msg: str) -> None:
        print(f"G2O {msg}", flush=True)

    def make_gas(ny: int, nx: int) -> dict:
        gas = load_config(gas_cfg_path)
        gas["numerics"] = {**gas.get("numerics", {}), "nx": nx, "ny": ny}
        return gas

    frequencies = [float(f) for f in proto["frequencies_Hz"]]
    ny = int(proto["ny"])
    nx = int(proto["nx"])
    n_harm = int(proto["n_harmonics"])
    eps_small = float(proto["epsilon_baseline"])
    eps_prod = float(proto["epsilon_production"])
    variants = list(proto["variants"])
    pair_proto = proto["pair"]

    probe_solver = GasSolver2D(make_gas(8, 4))
    mapping = probe_solver.mapping
    alpha_nom = float(mapping.alpha_lu)
    gamma = float(mapping.physical.gamma)
    dt = float(mapping.lattice.dt_s)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = Path(output_root) if output_root else repo_root / "results" / "phase5" / CASE_FAMILY
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    h5 = h5py.File(out_dir / "signals.h5", "w")

    base_gas = make_gas(ny, nx)
    frozen_filter = base_gas["numerics"]["high_wavenumber_filter"]
    log("frozen operator stack: acoustic_phase=%s dispersion=%s filter=%s@%s" % (
        base_gas["collision"]["acoustic_phase_correction_enabled"],
        base_gas["collision"]["dispersion_correction_enabled"],
        frozen_filter["enabled"], frozen_filter["strength"]))

    # ---- payloads: ablation matrix + frozen-stack signed pairs ----
    scalars = dict(periods=float(proto["periods"]),
                   settle_periods=float(proto["settle_periods"]),
                   samples_per_period=int(proto["samples_per_period"]),
                   ramp_periods=float(proto["ramp_periods"]))
    settle = scalars["settle_periods"]
    payloads: list[dict[str, Any]] = []
    for var in variants:
        vid = str(var["id"])
        mut = dict(var.get("mutations", {}))
        v_freqs = [float(x) for x in var.get("frequencies_Hz", frequencies)]
        for f in v_freqs:
            for eps in (eps_small, eps_prod):
                payloads.append({
                    "kind": "driven", "label": f"{vid}_f{f:g}_eps{eps:g}",
                    "gas_cfg": apply_mutations(base_gas, mut),
                    "wall": "mass_neutral_v1p1", "epsilon": eps,
                    "frequency_hz": f, **scalars})
    # settle discipline: >= ~11 box-relaxation times at EVERY frequency
    # (tau_box measured 1.1 periods @10 kHz, 1.47 @20 kHz — settle in PERIODS
    # does not transfer across frequency; per-frequency overrides are the
    # pre-registered physical rule, not per-point tuning)
    def pair_proto_for(f: float) -> dict[str, float]:
        eff = {k: float(pair_proto[k])
               for k in ("epsilon", "ramp_periods", "settle_periods", "periods")}
        for ov in pair_proto.get("overrides", []):
            if abs(float(ov["frequency_Hz"]) - f) <= 1e-6 * f:
                eff.update({k: float(v) for k, v in ov.items() if k != "frequency_Hz"})
        return eff

    pair_eps = float(pair_proto["epsilon"])
    for f in frequencies:
        eff = pair_proto_for(f)
        for sign, tag in ((1.0, "plus"), (-1.0, "minus")):
            payloads.append({
                "kind": "driven", "label": f"pair_{tag}_f{f:g}",
                "gas_cfg": apply_mutations(base_gas, {}),
                "wall": "mass_neutral_v1p1", "epsilon": sign * eff["epsilon"],
                "frequency_hz": f, "periods": eff["periods"],
                "settle_periods": eff["settle_periods"],
                "ramp_periods": eff["ramp_periods"],
                "samples_per_period": int(proto["samples_per_period"])})

    case_results = execute_cases(payloads, workers, log, worker=_g2o_case_worker)

    # variant instability is a MEASUREMENT for S4, not a runner error; the
    # frozen stack (v0) and the pair runs must complete
    for label, res in case_results.items():
        crashed = isinstance(res, dict) and "worker_exception" in res
        if crashed and (label.startswith("v0_") or label.startswith("pair_")):
            raise RuntimeError(f"frozen-stack case {label} crashed: {res['worker_exception']}")

    # ---- S1: single-tone operator fixture (frozen stack, both frequencies) ----
    s1 = {}
    for f in frequencies:
        plus = case_results[f"pair_plus_f{f:g}"]
        minus = case_results[f"pair_minus_f{f:g}"]
        s1[f"{f:g}"] = odd_pair_leakage(plus, minus, f,
                                        pair_proto_for(f)["settle_periods"])
        s1[f"{f:g}"]["pair_protocol_effective"] = pair_proto_for(f)
        log("S1 f=%g: odd-pair max nontarget = %.2e (gate %.0e)" % (
            f, s1[f"{f:g}"]["max_nontarget"], gates["single_tone_leakage_rel"]))
    s1_max = max(v["max_nontarget"] for v in s1.values())

    # ---- per-variant evaluation ----
    per_variant: dict[str, dict[str, Any]] = {}
    for var in variants:
        vid = str(var["id"])
        v_freqs = [float(x) for x in var.get("frequencies_Hz", frequencies)]
        vv: dict[str, Any] = {"diagnostic_only": bool(var.get("diagnostic_only", False)),
                              "frequencies": v_freqs, "by_freq": {}}
        for f in v_freqs:
            omega_lu = 2.0 * math.pi * f * dt
            rs = case_results.get(f"{vid}_f{f:g}_eps{eps_small:g}")
            rp = case_results.get(f"{vid}_f{f:g}_eps{eps_prod:g}")
            dead = any(isinstance(r, dict) and ("worker_exception" in r or not r.get("finite", False))
                       for r in (rs, rp))
            if dead:
                vv["by_freq"][f"{f:g}"] = {"stable": False}
                continue
            y_s = energy_channel_Y_over_Yhs(rs, omega_lu, alpha_nom, gamma)
            y_p = energy_channel_Y_over_Yhs(rp, omega_lu, alpha_nom, gamma)
            f5s = refit_n5(rs, f, settle, n_harm)
            f5p = refit_n5(rp, f, settle, n_harm)
            wsen = two_window_sensitivity(rp, f, settle, n_harm)
            c2 = f5p["fit_q5"].harmonic(2) / f5p["fit_q5"].harmonic(1)
            vv["by_freq"][f"{f:g}"] = {
                "stable": True,
                "Y_baseline": y_s, "Y_production": y_p,
                "D_G": float(abs(y_p) / abs(y_s) - 1.0),
                "H2q_production": float(f5p["H2_q"]),
                "H2q_baseline": float(f5s["H2_q"]),
                "H3q_production": float(f5p["H3_q"]),
                "c2_complex": c2,
                "window": wsen,
                "u95_H2": float(f5p["fit_q5"].amplitude_u95(2)
                                / max(f5p["fit_q5"].amplitude(1), 1e-300)),
                "baseline_shift_vs_v0": None,  # filled after v0 known
            }
            log("%s f=%g: D_G=%+.4f H2q=%.4e (base %.4e) Y=%.4f@%+.2f" % (
                vid, f, vv["by_freq"][f"{f:g}"]["D_G"], f5p["H2_q"], f5s["H2_q"],
                abs(y_s), _phase_deg(y_s)))
        per_variant[vid] = vv

    v0 = per_variant["v0_frozen"]
    for vid, vv in per_variant.items():
        for fk, d in vv["by_freq"].items():
            if d.get("stable") and fk in v0["by_freq"]:
                d["baseline_shift_vs_v0"] = _cplx(d["Y_baseline"] / v0["by_freq"][fk]["Y_baseline"])

    # ---- gate rows ----
    gated = [str(v["id"]) for v in variants
             if not v.get("diagnostic_only", False) and str(v["id"]) != "v0_frozen"]

    def ugov_dg(fk: str) -> float:
        w = v0["by_freq"][fk]["window"]
        return float(2.0 * w["p1f_amp_rel"])  # ratio of two 1f fits: 2x single-window proxy

    def ugov_h2(fk: str) -> float:
        w = v0["by_freq"][fk]["window"]
        return float(max(w["H2q_diff"], v0["by_freq"][fk]["u95_H2"]))

    s2_rows = {}
    s3_rows = {}
    s5_rows = {}
    for vid in gated:
        for fk, d in per_variant[vid]["by_freq"].items():
            key = f"{vid}@{fk}"
            if not d.get("stable"):
                s2_rows[key] = {"stable": False, "passed": False}
                s3_rows[key] = {"stable": False, "passed": False}
                s5_rows[key] = {"stable": False, "passed": False}
                continue
            ref = v0["by_freq"][fk]
            dd = abs(d["D_G"] - ref["D_G"])
            dg_gate = max(float(gates["dg_sensitivity_pp"]), ugov_dg(fk))
            dh = abs(d["H2q_production"] - ref["H2q_production"])
            h2_gate = max(float(gates["h2_sensitivity_fraction"]) * ref["H2q_production"],
                          ugov_h2(fk))
            direction = d["H2q_production"] > d["H2q_baseline"]
            phase_shift = abs(_phase_deg(d["c2_complex"] / ref["c2_complex"]))
            mag_ratio = d["H2q_production"] / max(ref["H2q_production"], 1e-300)
            dg_sign = (math.copysign(1, d["D_G"]) == math.copysign(1, ref["D_G"])
                       or min(abs(d["D_G"]), abs(ref["D_G"])) <= ugov_dg(fk))
            s2_rows[key] = {"stable": True, "delta_D_G": dd, "gate": dg_gate,
                            "D_G_variant": d["D_G"], "D_G_frozen": ref["D_G"],
                            "passed": bool(dd <= dg_gate)}
            s3_rows[key] = {"stable": True, "delta_H2q": dh, "gate": h2_gate,
                            "H2q_variant": d["H2q_production"],
                            "H2q_frozen": ref["H2q_production"],
                            "scaling_direction_preserved": bool(direction),
                            "passed": bool(dh <= h2_gate and direction)}
            s5_rows[key] = {"stable": True, "c2_phase_shift_deg": phase_shift,
                            "H2_magnitude_ratio": float(mag_ratio),
                            "D_G_sign_preserved": bool(dg_sign),
                            "passed": bool(phase_shift <= float(gates["attribution_phase_deg"])
                                           and float(gates["attribution_mag_lo"]) <= mag_ratio
                                           <= float(gates["attribution_mag_hi"])
                                           and dg_sign)}

    stable_variants = [vid for vid in gated
                       if all(d.get("stable") for d in per_variant[vid]["by_freq"].values())]

    # ---- S6: spectral-identity row (falsifiable byte-level claim) ----
    s6_rows: dict[str, Any] = {}
    for var in variants:
        if not var.get("identity_expected", False):
            continue
        vid = str(var["id"])
        v_freqs = [float(x) for x in var.get("frequencies_Hz", frequencies)]
        for f in v_freqs:
            for eps in (eps_small, eps_prod):
                key = f"{vid}@f{f:g}_eps{eps:g}"
                rv = case_results.get(f"{vid}_f{f:g}_eps{eps:g}")
                r0 = case_results.get(f"v0_frozen_f{f:g}_eps{eps:g}")
                ok = (isinstance(rv, dict) and isinstance(r0, dict)
                      and "t_s" in rv and "t_s" in r0)
                if ok:
                    diff = max(float(np.max(np.abs(rv["q_moment_si"] - r0["q_moment_si"]))),
                               float(np.max(np.abs(rv["p_box_lu"] - r0["p_box_lu"]))))
                    s6_rows[key] = {"max_abs_series_diff": diff,
                                    "passed": bool(diff == 0.0)}
                else:
                    s6_rows[key] = {"max_abs_series_diff": None, "passed": False}
                log("S6 %s: max|series diff| = %s" % (
                    key, s6_rows[key]["max_abs_series_diff"]))

    gate_rows = {
        "single_tone_leakage": {
            "by_freq": s1, "value_max": s1_max,
            "gate": float(gates["single_tone_leakage_rel"]),
            "instrument": "G1-W signed-pair protocol verbatim (odd combination; "
                          "ring-down carriers pre-registered non-viable: decaying-"
                          "tone bin leakage ~gamma/omega >> 1e-8)",
            "passed": bool(s1_max <= float(gates["single_tone_leakage_rel"])),
        },
        "dg_operator_sensitivity": {
            "rows": s2_rows,
            "passed": bool(s2_rows and all(r["passed"] for r in s2_rows.values())),
        },
        "h2_operator_sensitivity": {
            "rows": s3_rows,
            "passed": bool(s3_rows and all(r["passed"] for r in s3_rows.values())),
        },
        "h3_operator_sensitivity": {
            "required": False,
            "note": "H3 untriggered (G2-T §7.4 evaluation; H3_DIAGNOSTIC_ONLY) — "
                    "H3q archived per variant, no gate",
            "H3q_by_variant": {vid: {fk: d.get("H3q_production")
                                     for fk, d in per_variant[vid]["by_freq"].items()}
                               for vid in per_variant},
            "passed": True,
        },
        "stability": {
            "stable_nonproduction_variants": stable_variants,
            "passed": bool(len(stable_variants) >= 1),
        },
        "attributability": {
            "rows": s5_rows,
            "passed": bool(s5_rows and all(r["passed"] for r in s5_rows.values())),
        },
        "spectral_identity": {
            "rows": s6_rows,
            "claim": "acoustic phase correction family is identity on this "
                     "rig geometry+config (0 qualifying diagonal modes at the "
                     "frozen low_laplacian; high-mode factors exactly 1.0) — "
                     "an identity operator can neither generate nor suppress "
                     "harmonics, making the §7.3 conclusion EXACT for this "
                     "family; row falsifies on any nonzero series difference",
            "applicable": bool(s6_rows),
            "passed": bool(all(r["passed"] for r in s6_rows.values())
                           if s6_rows else True),
        },
        "numerical_repair": {"no_clipping": True, "no_floor": True,
                             "no_positivity_repair": True, "passed": True},
    }

    hard = ["single_tone_leakage", "dg_operator_sensitivity", "h2_operator_sensitivity",
            "attributability", "spectral_identity", "numerical_repair"]
    labels: list[str] = []
    if all(gate_rows[k]["passed"] for k in hard):
        if gate_rows["stability"]["passed"]:
            verdict = "PASSED"
        else:
            verdict = "SCOPED_CANDIDATE"
            labels.append("HARMONIC_OPERATOR_ABLATION_ALL_VARIANTS_UNSTABLE")
    else:
        verdict = "FAILED"
        labels.append("HARMONIC_OPERATOR_ABLATION_FAILED")
    log("verdict=%s labels=%s" % (verdict, labels or "-"))

    # ---- archive series ----
    for label, r in case_results.items():
        if not isinstance(r, dict) or "t_s" not in r:
            continue
        g = h5.create_group(f"runs/{label}")
        for name in ("t_s", "p_box_lu", "q_moment_si", "mass"):
            g.create_dataset(name, data=r[name])
        g.attrs.update({"epsilon": r["epsilon"], "finite": r["finite"]})

    # ---- outputs (contract §16.1 seven files) ----
    resolved = {"gate_id": GATE_ID, "case_family": CASE_FAMILY, "protocol": proto,
                "gates": gates, "config_path": str(config_path)}
    config_yaml = yaml.safe_dump(resolved, allow_unicode=True, sort_keys=False)
    (out_dir / "config_resolved.yaml").write_text(config_yaml, encoding="utf-8")

    fk_all = [f"{f:g}" for f in frequencies]
    na = "not_applicable_g2o"
    v0f0 = v0["by_freq"][fk_all[0]]
    summary = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "code_commit": _git_commit(),
        "config_digest": _sha256_bytes(config_yaml.encode())[:12],
        "physics_core_digest": hashlib.sha256(
            b"".join((repo_root / p).read_bytes() for p in PHYSICS_CORE_FILES)
        ).hexdigest()[:12],
        "parent_baseline_run": str(cfg["inheritance"]["g1a_certified_run"]),
        "phase5_contract_version": PHASE5_CONTRACT_VERSION,
        "work_package": "WP2", "gate_id": GATE_ID, "case_family": CASE_FAMILY,
        "model_route": "ROUTE_B_MAIN",
        "property_model_id": "frozen_dx2p6_route_b_closure",
        "tau_policy": "frozen (M3 closure §3)",
        "mapping_digest": _sha256_bytes(Path(gas_cfg_path).read_bytes())[:12],
        "background_path": "uniform_reference_state",
        "forcing_protocol": "prescribed_wall_temperature_zero_mean_sinusoid",
        "P_mean_W_m2": 0.0, "P_mean_rematched": False, "target_Theta_DC": 0.0,
        "frequency_Hz": frequencies,
        "T_ambient_K": 300.0, "T_mean_K": 300.0,
        "epsilon_AC_measured": {"baseline": eps_small, "production": eps_prod,
                                "pair": pair_eps},
        "Theta_DC_measured": 0.0,
        "chi_0": None, "chi_eff": None, "C_A_J_m2K": None,
        "dc_heat_sink_model": na, "dc_heat_sink_parameters": None,
        "H_s_role": "rig domain height (sealed periodic)",
        "thermal_resistance_effective": None,
        "grid_shape": [ny, nx], "dx_m": float(mapping.lattice.dx_m), "dt_s": dt,
        "domain_height_m": ny * float(mapping.lattice.dx_m),
        "boundary_model": "mass_neutral_v1p1_symmetric (G1-W certified production wall)",
        "wall_mass_policy": "mass_neutral_by_construction",
        "wall_neutrality_gate_id": "G1-W PASSED (20260727T083342Z)",
        "boundary_mass_flux_definition": "wall_mass_audit.NORMALIZATION_DEFINITION",
        "boundary_mass_flux_0f_to_3f": None,
        "spectral_operator_stack_id": "frozen_production_dx2p6 + pre-registered "
                                      "diagnostic variants (instrument identification only)",
        "spectral_correction_enabled": True,
        "high_wavenumber_filter_enabled": True,
        "high_wavenumber_filter_strength": f"frozen_production ({frozen_filter['strength']})",
        "operator_ablation_run_id": run_id,
        "q_feedback_relax": None,
        "fit_window": {"settle_periods": settle,
                       "fit_periods": float(proto["periods"]) - settle},
        "fit_cycles": float(proto["periods"]) - settle,
        "detrend_order": 0, "harmonic_order_max": n_harm,
        "harmonic_fit_condition_number": None,
        "U_det": {fk: {"window_p1f": v0["by_freq"][fk]["window"]["p1f_amp_rel"],
                       "window_H2q_diff": v0["by_freq"][fk]["window"]["H2q_diff"]}
                  for fk in fk_all},
        "U95_fit": {fk: v0["by_freq"][fk]["u95_H2"] for fk in fk_all},
        "U_gov": {fk: {"D_G": ugov_dg(fk), "H2": ugov_h2(fk)} for fk in fk_all},
        "no_clipping": True, "no_floor": True, "no_positivity_repair": True,
        "gate_status": verdict,
        "scoped_limitations": labels,
        "smoke_mode": bool(smoke),
        "results": {
            "T_s_hat_1f": None, "p_hat_1f": None, "p_hat_2f": None, "p_hat_3f": None,
            "outgoing_mode_1f": None, "outgoing_mode_2f": None, "outgoing_mode_3f": None,
            "outgoing_mode_note": "G2-T quantity",
            "G1": {fk: float(abs(v0["by_freq"][fk]["Y_baseline"])) for fk in fk_all},
            "D_G": {fk: v0["by_freq"][fk]["D_G"] for fk in fk_all},
            "D_OP": None, "D_OP_note": "A2a quantity (WP3)",
            "H2": {fk: v0["by_freq"][fk]["H2q_production"] for fk in fk_all},
            "H3": {fk: v0["by_freq"][fk]["H3q_production"] for fk in fk_all},
            "m1": None, "m2": None, "m3": None,
            "m_note": "scaling direction row uses the two-eps pair per variant",
            "QS0_error_amplitude": None, "QS0_error_phase": None,
            "QS1_error_amplitude": None, "QS1_error_phase": None,
            "wall_boundary_sensitivity": None,
            "operator_sensitivity_D_G": {k: v.get("delta_D_G") for k, v in s2_rows.items()},
            "operator_sensitivity_H2": {k: v.get("delta_H2q") for k, v in s3_rows.items()},
            "operator_sensitivity_H3": None,
            "operator_note": "per-variant own-baseline normalization (contract §7.3 "
                             "fixture item 3); baseline linear shifts archived",
            "baseline_linear_shifts": {
                vid: {fk: d.get("baseline_shift_vs_v0")
                      for fk, d in per_variant[vid]["by_freq"].items()}
                for vid in per_variant},
            "boundary_mass_flux_0f_to_3f": None,
            "energy_residual": None,
            "mass_or_flux_residual": None,
            "wall_temperature_error": None,
            "single_tone_leakage": s1,
        },
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=1, default=float), encoding="utf-8")

    harmonic_payloads = {}
    for vid in per_variant:
        for fk in per_variant[vid]["by_freq"]:
            r = case_results.get(f"{vid}_f{fk}_eps{eps_prod:g}")
            if isinstance(r, dict) and "fit_q" in r:
                harmonic_payloads[f"{vid}_f{fk}_q"] = r["fit_q"].to_json_payload()
    (out_dir / "harmonic_fit.json").write_text(
        json.dumps(harmonic_payloads, indent=1, default=float), encoding="utf-8")

    provenance = {
        "run_id": run_id, "command": " ".join(sys.argv), "workers": workers,
        "python": sys.version.split()[0], "numpy": np.__version__,
        "code_commit": summary["code_commit"],
        "physics_core_digest": summary["physics_core_digest"],
        "variants": [{"id": str(v["id"]), "mutations": dict(v.get("mutations", {})),
                      "diagnostic_only": bool(v.get("diagnostic_only", False)),
                      "identity_expected": bool(v.get("identity_expected", False))}
                     for v in variants],
        "g1w_pair_instrument": "eps/ramp/settle/periods verbatim from the G1-W "
                               "certified pair protocol",
    }
    (out_dir / "provenance.json").write_text(json.dumps(provenance, indent=1, default=float),
                                             encoding="utf-8")
    (out_dir / "gate_evaluation.json").write_text(
        json.dumps({"gate_id": GATE_ID, "verdict": verdict, "labels": labels,
                    "rows": gate_rows}, indent=1, default=float), encoding="utf-8")

    report = [f"# G2-O run {run_id}", "",
              f"- verdict: **{verdict}** labels={labels or '-'}",
              f"- smoke_mode: {smoke}", "", "## Gate rows (contract §7.3)", ""]
    for name, row in gate_rows.items():
        report.append(f"- {name}: passed={row['passed']}")
    report += ["", "## Variant table (production eps)", ""]
    for vid in per_variant:
        for fk, d in per_variant[vid]["by_freq"].items():
            if d.get("stable"):
                report.append("- %s@%s: D_G=%+.4f H2q=%.4e baseline_shift=%s" % (
                    vid, fk, d["D_G"], d["H2q_production"],
                    json.dumps(d.get("baseline_shift_vs_v0"), default=float)))
            else:
                report.append(f"- {vid}@{fk}: UNSTABLE (S4 measurement)")
    (out_dir / "run_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    h5.close()
    log(f"outputs -> {out_dir}")
    return {"verdict": verdict, "labels": labels, "out_dir": str(out_dir),
            "summary": summary, "gate_rows": gate_rows}


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase_5 G2-O operator-ablation gate")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--workers", type=int,
                        default=max(1, (os.cpu_count() or 2) - 2))
    args = parser.parse_args()
    result = run_g2o(args.config, args.output_root, smoke=args.smoke,
                     workers=args.workers)
    return 0 if result["verdict"] in {"PASSED", "SCOPED_CANDIDATE"} else 1


if __name__ == "__main__":
    sys.exit(main())
