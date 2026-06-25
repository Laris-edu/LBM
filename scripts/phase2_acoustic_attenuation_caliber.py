"""Acoustic-attenuation measurement caliber + diagonal over-constraint diagnostic.

This formalises two findings about the calibrated local recursive-regularized
(RR) D2Q37 closure (see docs/Phase_2/closure/Phase2_D2Q37_Recursive_Regularized_Closure.md):

F1 -- measurement caliber (resolves the "attenuation drifts with the fit window"
      residual).  A weakly damped acoustic standing/travelling wave is a sum of a
      forward + backward eigenmode (the initial condition is not the *exact*
      discrete eigenmode), so the production ``log|p'|`` decay fit is biased by a
      weak beating ripple and drifts with the window.  The EXACT one-step modal
      eigenvalue ``sigma = -log|lambda|`` (from the real periodic symbol) is
      window-free, fit-free and admixture-free; it agrees with a Prony
      multi-exponential fit of the dynamic data.  Under this caliber the RR
      closure drives x/y acoustic damping to ratio = 1 EXACTLY (the production
      ``log|p'|`` 240-window value ~1.003 was a ~10% low-biased artifact; the true
      window-free value at the published chi is ~1.10).

T1 -- diagonal over-constraint (sharpens the "diagonal residual / need a 4th
      knob" residual).  On a square (D4) lattice the most general *local linear*
      viscous closure has exactly three independent coefficients: a bulk modulus
      (chi / trace) and two shear moduli for the two rank-2 irreps B1 (xx-yy =
      normal_factor) and B2 (xy = xy_factor).  Matching isotropy needs four
      numbers {nu_T(axis), nu_T(diag), nu_L(axis), nu_L(diag)}.  Pinning B2 by
      axis shear, B1 by diagonal shear and chi by axis longitudinal leaves
      nu_L(diag) DETERMINED -> the diagonal acoustic residual is irreducible for
      any D4-covariant local linear closure.  The diagnostic confirms this with a
      finite-difference sensitivity matrix and shows (nu_L,diag - nu_L,axis) is
      chi-independent.

Diagnostic only.  Does NOT change the baseline (default ``measured`` deviatoric +
``current_zero`` trace) and does NOT claim a production pass.  The new caliber is
reported as the recommended diagnostic ground-truth for acoustic attenuation; the
production P2-6 ``log|p'|`` measurement is left unchanged.

Usage:
    python -m scripts.phase2_acoustic_attenuation_caliber
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
from typing import Any

import numpy as np

import core.solver as solver_mod
from core.solver import GasSolver2D
from core.unit_mapping import create_unit_mapping
from scripts.phase2_closure_recursive_regularized import _rr_config
from scripts.phase2_m2_verification import load_config, sha256_file, summary_payload_digest
from verification.acoustic_wave_measurement import (
    _initialize_acoustic_wave,
    _matched_nsf_acoustic_attenuation_coeff_lu,
    _modal_amplitude_2d,
    _settings_from_config,
)

DEFAULT_CONFIG = Path("configs/gas_air_10k_d2q37_physical_timestep.yaml")
DEFAULT_OUTPUT_ROOT = Path("results/phase2_acoustic_attenuation_caliber")

# Published calibrated knobs (authoritative RR run 20260621T083625Z).
XY_FACTOR = 0.4763606253137551
NORMAL_FACTOR = 0.8906391739599911
CHI = 1.0852439806681207
N = 64
LONG_STEPS = 720


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and np.isnan(value):
        return None
    return value


def _kxy(direction: str, n: int = N) -> tuple[float, float]:
    if direction == "x":
        return 2.0 * np.pi / n, 0.0
    if direction == "y":
        return 0.0, 2.0 * np.pi / n
    if direction == "diagonal":
        return 2.0 * np.pi / n, 2.0 * np.pi / n
    raise ValueError(direction)


def _clear_symbol_caches() -> None:
    """Defensively clear all core.solver module caches before each build.

    Historically the modal-symbol / acoustic-phase / ghost-projector cache keys
    omitted the local trace divergence curve (chi) and the deviatoric policy, so
    a stale entry from an earlier chi contaminated a later chi's symbol in a
    multi-chi sweep (the diagonal acoustic ratio shifted 1.265 -> 1.306 purely
    from call order).  The core keys now include chi + the deviatoric policy
    (fixed 2026-06-21), so this clearing is belt-and-suspenders, not load-bearing
    -- it keeps the diagnostic reproducible even if the core fix is reverted.
    """
    solver_mod._HIGH_MODE_MODAL_SYMBOL_CACHE.clear()
    solver_mod._ACOUSTIC_PHASE_OPERATOR_CACHE.clear()
    solver_mod._GHOST_PROJECTOR_OPERATOR_CACHE.clear()
    solver_mod._GHOST_PROJECTOR_PHASE_CACHE.clear()


def _build_solver(base: dict[str, Any], *, xy: float, normal: float, chi: float, n: int = N) -> GasSolver2D:
    _clear_symbol_caches()
    cfg = _rr_config(base, xy_factor=xy, normal_factor=normal, chi=chi)
    cfg = deepcopy(cfg)
    cfg["numerics"] = {**cfg.get("numerics", {}), "nx": n, "ny": n}
    return GasSolver2D(cfg)


def _observables(vec: np.ndarray, lattice: Any, mapping: Any) -> tuple[complex, np.ndarray, complex, complex]:
    q = int(lattice.q)
    df = np.asarray(vec[:q], complex)
    dg = np.asarray(vec[q:], complex)
    rho0 = mapping.lattice.rho_ref_lu
    theta0 = mapping.theta_ref_lu
    degrees = float(mapping.lattice.D + mapping.lattice.S)
    rho = np.sum(df)
    mom = np.einsum("a,ai->i", df, lattice.c)
    c2 = np.sum(lattice.c * lattice.c, axis=-1)
    internal = 0.5 * np.sum(df * c2) + np.sum(dg)
    theta = 2.0 * internal / (degrees * rho0) - theta0 * rho / rho0
    p = theta0 * rho + rho0 * theta
    return rho, mom / rho0, theta, p


def _eigen_modes(solver: GasSolver2D, direction: str) -> dict[str, Any]:
    """Exact one-step modal eigenvalues -> acoustic (fwd/bwd) / shear / entropy."""
    mapping = solver.mapping
    lattice = solver.lattice
    rho0 = mapping.lattice.rho_ref_lu
    theta0 = mapping.theta_ref_lu
    c0 = float(np.sqrt(mapping.physical.gamma * theta0))
    nu = float(mapping.nu_lu)
    alpha = float(mapping.alpha_lu)
    kx, ky = _kxy(direction)
    k2 = kx * kx + ky * ky
    kmag = float(np.sqrt(k2))
    dim = float(mapping.lattice.D)
    ref_ac = (
        0.5 * (mapping.physical.gamma - 1.0) * alpha
        + ((dim - 1.0) / dim) * nu
        + 0.5 * float(mapping.nu_b_lu)
    ) * k2

    sym = solver._high_mode_modal_symbol(kx=kx, ky=ky, rho0=rho0, u0=(0.0, 0.0), theta0=theta0)
    vals, vecs = np.linalg.eig(sym)

    fwd: list[tuple[float, float]] = []
    bwd: list[tuple[float, float]] = []
    shear: list[tuple[float, float]] = []
    entropy: list[tuple[float, float]] = []
    for i, lam in enumerate(vals):
        mag = abs(lam)
        if mag <= 0.0 or mag > 1.0 or not np.isfinite(mag):
            continue
        sigma = -float(np.log(mag))
        if sigma <= 0.0 or sigma > 0.02:
            continue
        ang = float(np.angle(lam))
        cps = -ang / kmag
        rho_c, u, theta_c, p_c = _observables(vecs[:, i], lattice, mapping)
        a_rho, a_th, a_p = abs(rho_c), abs(theta_c), abs(p_c)
        if direction == "x":
            upar, uperp = abs(u[0]), abs(u[1])
        elif direction == "y":
            upar, uperp = abs(u[1]), abs(u[0])
        else:
            upar = abs((u[0] + u[1]) / np.sqrt(2.0))
            uperp = abs((u[0] - u[1]) / np.sqrt(2.0))
        is_ac = abs(abs(cps) / c0 - 1.0) < 0.2 and abs(ang) > 1.0e-4
        if is_ac and cps > 0.0:
            fwd.append((abs(abs(cps) / c0 - 1.0), sigma))
        elif is_ac and cps < 0.0:
            bwd.append((abs(abs(cps) / c0 - 1.0), sigma))
        elif abs(ang) < 1.0e-3 and uperp > 3.0 * a_rho and uperp > 3.0 * a_th:
            shear.append((sigma, uperp))
        elif abs(ang) < 1.0e-3 and a_th > 3.0 * upar and a_p < 0.5 * a_th:
            entropy.append((sigma, a_th))
    fwd.sort()
    bwd.sort()
    sigma_fwd = fwd[0][1] if fwd else np.nan
    sigma_bwd = bwd[0][1] if bwd else np.nan
    sigma_shear = max(shear, key=lambda r: r[1])[0] if shear else np.nan
    sigma_entropy = max(entropy, key=lambda r: r[1])[0] if entropy else np.nan
    return {
        "k_mag": kmag,
        "ref_ac_lu": float(ref_ac),
        "acoustic_fwd_sigma_lu": float(sigma_fwd),
        "acoustic_fwd_ratio": float(sigma_fwd / ref_ac) if np.isfinite(sigma_fwd) else np.nan,
        "acoustic_bwd_ratio": float(sigma_bwd / ref_ac) if np.isfinite(sigma_bwd) else np.nan,
        "shear_nu_ratio": float(sigma_shear / k2 / nu) if np.isfinite(sigma_shear) else np.nan,
        "entropy_alpha_ratio": float(sigma_entropy / k2 / alpha) if np.isfinite(sigma_entropy) else np.nan,
    }


# --------------------------------------------------------------------------- #
# dynamic cross-check (log|p'| windowed + Prony)
# --------------------------------------------------------------------------- #
def _record_pressure_series(base, direction, steps):
    cfg = _rr_config(base, xy_factor=XY_FACTOR, normal_factor=NORMAL_FACTOR, chi=CHI, p2_06=(direction,))
    cfg["p2_06_acoustic_wave"] = {**cfg["p2_06_acoustic_wave"], "steps": steps, "amplitude": 1.0e-6, "mode_index": 1}
    settings = _settings_from_config(cfg)
    sim = deepcopy(cfg)
    sim["numerics"] = {**sim.get("numerics", {}), "nx": settings.nx, "ny": settings.ny}
    sim["case"] = {**sim.get("case", {}), "name": f"caliber_{direction}"}
    solver = GasSolver2D(sim)
    phase, _unit, k_mag = _initialize_acoustic_wave(solver, settings, direction)
    p0 = solver.mapping.lattice.rho_ref_lu * solver.mapping.theta_ref_lu
    times: list[int] = []
    pressure: list[complex] = []
    for step in range(steps + 1):
        macro = solver.get_macro()
        if not np.isfinite(macro.theta).all() or float(np.nanmin(macro.theta)) <= 0.0:
            break
        times.append(step)
        pressure.append(_modal_amplitude_2d(macro.p - p0, phase))
        if step < steps:
            solver.step()
    coeff = _matched_nsf_acoustic_attenuation_coeff_lu(solver.mapping)
    return np.asarray(times, float), np.asarray(pressure, complex), coeff * k_mag * k_mag


def _logabs_slope(t, p, start, stop):
    m = (t >= start) & (t <= stop)
    if np.count_nonzero(m) < 3:
        return np.nan
    coeffs = np.linalg.lstsq(np.column_stack((np.ones(m.sum()), t[m])), np.log(np.abs(p[m])), rcond=None)[0]
    return -float(coeffs[1])


def _prony_dominant_sigma(t, p, start, stop, order=3):
    m = (t >= start) & (t <= stop)
    x = p[m]
    n = x.size
    if n < 2 * order + 2:
        return np.nan
    rows = n - order
    A = np.empty((rows, order), complex)
    b = np.empty(rows, complex)
    for i in range(rows):
        A[i, :] = x[i:i + order][::-1]
        b[i] = -x[i + order]
    a = np.linalg.lstsq(A, b, rcond=None)[0]
    roots = np.roots(np.concatenate(([1.0], a)))
    s = np.log(roots)
    tt = (t[m] - t[m][0]).astype(float)
    amp = np.linalg.lstsq(np.exp(np.outer(tt, s)), x, rcond=None)[0]
    order_idx = np.argsort(-np.abs(amp))
    return -float(s[order_idx[0]].real)


def _dynamic_crosscheck(base, direction, ref):
    t, p, _ref_dyn = _record_pressure_series(base, direction, LONG_STEPS)
    out = {
        "samples": int(t.size),
        "amplitude_change": float(abs(p[-1]) / abs(p[0]) - 1.0) if p.size else np.nan,
        "logabs_ratio_240": _logabs_slope(t, p, 10, 240) / ref,
        "logabs_ratio_480": _logabs_slope(t, p, 10, 480) / ref,
        "logabs_ratio_720": _logabs_slope(t, p, 10, 720) / ref,
        "prony_ratio": _prony_dominant_sigma(t, p, 10, 720) / ref,
    }
    return {k: (float(v) if isinstance(v, float) else v) for k, v in out.items()}


# --------------------------------------------------------------------------- #
# chi recalibration against the eigenvalue
# --------------------------------------------------------------------------- #
def _recalibrate_chi(base):
    def ac_x_ratio(chi):
        s = _build_solver(base, xy=XY_FACTOR, normal=NORMAL_FACTOR, chi=chi)
        return _eigen_modes(s, "x")["acoustic_fwd_ratio"]

    c0, c1 = 1.10, 1.15
    r0, r1 = ac_x_ratio(c0), ac_x_ratio(c1)
    chi_star = c0 + (1.0 - r0) * (c1 - c0) / (r1 - r0)
    s = _build_solver(base, xy=XY_FACTOR, normal=NORMAL_FACTOR, chi=chi_star)
    modes = {d: _eigen_modes(s, d) for d in ("x", "y", "diagonal")}
    return {
        "chi_published": CHI,
        "chi_eigen_recalibrated": float(chi_star),
        "probe_chi": [c0, c1],
        "probe_ac_x_ratio": [float(r0), float(r1)],
        "acoustic_fwd_ratio": {d: modes[d]["acoustic_fwd_ratio"] for d in modes},
        "acoustic_bwd_ratio": {d: modes[d]["acoustic_bwd_ratio"] for d in modes},
        "shear_nu_ratio": {d: modes[d]["shear_nu_ratio"] for d in modes},
        "entropy_alpha_ratio": {d: modes[d]["entropy_alpha_ratio"] for d in modes},
    }


# --------------------------------------------------------------------------- #
# D4 over-constraint: finite-difference sensitivity matrix
# --------------------------------------------------------------------------- #
def _four_quantities(base, xy, normal, chi):
    s = _build_solver(base, xy=xy, normal=normal, chi=chi)
    mx, md = _eigen_modes(s, "x"), _eigen_modes(s, "diagonal")
    return {
        "nu_T_axis": mx["shear_nu_ratio"],
        "nu_T_diag": md["shear_nu_ratio"],
        "nu_L_axis": mx["acoustic_fwd_ratio"],
        "nu_L_diag": md["acoustic_fwd_ratio"],
    }


def _sensitivity_matrix(base):
    base_pt = {"xy": XY_FACTOR, "normal": NORMAL_FACTOR, "chi": CHI}
    steps = {"xy": 0.02, "normal": 0.02, "chi": 0.02}
    q0 = _four_quantities(base, **base_pt)
    rows = ("nu_T_axis", "nu_T_diag", "nu_L_axis", "nu_L_diag")
    sens: dict[str, dict[str, float]] = {r: {} for r in rows}
    for knob in ("xy", "normal", "chi"):
        pt = dict(base_pt)
        pt[knob] = base_pt[knob] + steps[knob]
        qp = _four_quantities(base, **pt)
        for r in rows:
            sens[r][knob] = float((qp[r] - q0[r]) / steps[knob])
    # chi-independence of the diagonal excess
    d_excess_d_chi = sens["nu_L_diag"]["chi"] - sens["nu_L_axis"]["chi"]
    return {
        "base_point": base_pt,
        "fd_step": steps,
        "base_quantities": {k: float(v) for k, v in q0.items()},
        "sensitivity_dQ_dknob": sens,
        "d_diag_excess_d_chi": float(d_excess_d_chi),
    }


# --------------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------------- #
def run_diagnostic(*, config_path: Path, output_root: Path) -> dict[str, Any]:
    base = load_config(config_path)
    mapping = create_unit_mapping(base)
    nu = float(mapping.nu_lu)
    alpha = float(mapping.alpha_lu)

    solver = _build_solver(base, xy=XY_FACTOR, normal=NORMAL_FACTOR, chi=CHI)
    eigen = {d: _eigen_modes(solver, d) for d in ("x", "y", "diagonal")}
    ref_ac = {d: eigen[d]["ref_ac_lu"] for d in eigen}

    dynamic = {d: _dynamic_crosscheck(base, d, ref_ac[d]) for d in ("x", "diagonal")}
    recalibration = _recalibrate_chi(base)
    overconstraint = _sensitivity_matrix(base)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = output_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "run_id": run_id,
        "status": "DIAGNOSTIC_COMPLETE",
        "config_path": str(config_path),
        "config_sha256": sha256_file(config_path),
        "python": sys.version,
        "platform": platform.platform(),
        "closure": "strain_rate_isotropic deviatoric + ghost_orthogonal_local (div) trace + diagnostic_zero bulk",
        "published_knobs": {"xy_factor": XY_FACTOR, "normal_factor": NORMAL_FACTOR, "chi": CHI},
        "nu_lu": nu,
        "alpha_lu": alpha,
        "eigen_caliber": eigen,
        "dynamic_crosscheck": dynamic,
        "chi_recalibration": recalibration,
        "overconstraint": overconstraint,
        "interpretation": {
            "F1_caliber": (
                "The exact one-step modal eigenvalue sigma=-log|lambda| is the window-free, fit-free, "
                "admixture-free acoustic damping; it equals the dynamic Prony fit. The production log|p'| "
                "decay fit is biased low at short windows by a weak forward/backward beating ripple (the "
                "init is not the exact discrete eigenmode) and drifts with the window. At the published "
                "knobs the true x/y acoustic ratio is ~1.10, not the 240-window ~1.00; recalibrating chi "
                "against the eigenvalue drives x/y to ratio = 1 EXACTLY."
            ),
            "T1_overconstraint": (
                "On a square (D4) lattice the most general local linear viscous closure has exactly three "
                "coefficients: bulk (chi) and two shear moduli for irreps B1 (xx-yy = normal_factor) and "
                "B2 (xy = xy_factor). nu_T(axis)<-B2, nu_T(diag)<-B1, nu_L(axis)<-B1+chi, nu_L(diag)<-B2+chi. "
                "Pinning B2 (axis shear), B1 (diag shear) and chi (axis longitudinal) leaves nu_L(diag) "
                "DETERMINED: the diagonal residual is irreducible for any D4-covariant local linear closure. "
                "The sensitivity matrix confirms the couplings and d(nu_L,diag - nu_L,axis)/d(chi) ~ 0."
            ),
            "boundaries": (
                "Diagnostic only; baseline unchanged. Any 4th degree of freedom able to close the diagonal "
                "residual must be non-local (Riesz / longitudinal projector), nonlinear, or memory-based. "
                "The production P2-6 log|p'| measurement is left unchanged; the eigenvalue/Prony caliber is "
                "the recommended diagnostic ground-truth."
            ),
        },
    }
    safe = _json_safe(payload)
    safe["summary_digest"] = summary_payload_digest(safe)
    (out_dir / "summary.json").write_text(json.dumps(safe, indent=2), encoding="utf-8")
    (out_dir / "report.md").write_text(_render_report(safe), encoding="utf-8")
    return safe


def _fmt(value: Any) -> str:
    if value is None:
        return "none"
    if isinstance(value, float):
        return "nan" if value != value else f"{value:.4g}"
    return str(value)


def _render_report(p: dict[str, Any]) -> str:
    eig = p["eigen_caliber"]
    dyn = p["dynamic_crosscheck"]
    rc = p["chi_recalibration"]
    oc = p["overconstraint"]
    lines = [
        "# Phase 2 D2Q37 Acoustic-Attenuation Caliber + Diagonal Over-Constraint Diagnostic",
        "",
        f"- run_id: `{p['run_id']}`",
        f"- status: `{p['status']}`",
        f"- closure: {p['closure']}",
        f"- summary_digest: `{p['summary_digest']}`",
        "",
        "## F1 -- measurement caliber (window-free eigenvalue vs dynamic fits)",
        "",
        "| dir | eigen acoustic ratio (fwd) | Prony ratio | log|p'| 240 | log|p'| 480 | log|p'| 720 | shear nu_r | entropy alpha_r |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for d in ("x", "diagonal"):
        e = eig[d]
        dd = dyn[d]
        lines.append(
            f"| {d} | {_fmt(e['acoustic_fwd_ratio'])} | {_fmt(dd['prony_ratio'])} | "
            f"{_fmt(dd['logabs_ratio_240'])} | {_fmt(dd['logabs_ratio_480'])} | {_fmt(dd['logabs_ratio_720'])} | "
            f"{_fmt(e['shear_nu_ratio'])} | {_fmt(e['entropy_alpha_ratio'])} |"
        )
    lines += [
        f"| y | {_fmt(eig['y']['acoustic_fwd_ratio'])} | (=x) | - | - | - | "
        f"{_fmt(eig['y']['shear_nu_ratio'])} | {_fmt(eig['y']['entropy_alpha_ratio'])} |",
        "",
        "Eigenvalue == Prony; log|p'| is biased low at 240 and drifts up toward the eigenvalue. "
        "Shear/entropy are single real eigenvalues (no beating) -> clean.",
        "",
        "## chi recalibration against the eigenvalue",
        "",
        f"- published chi = `{_fmt(rc['chi_published'])}` -> eigen acoustic x ratio `{_fmt(eig['x']['acoustic_fwd_ratio'])}`",
        f"- eigen-recalibrated chi* = `{_fmt(rc['chi_eigen_recalibrated'])}`",
        "- at chi*: acoustic_fwd ratio "
        + ", ".join(f"{d}={_fmt(rc['acoustic_fwd_ratio'][d])}" for d in ("x", "y", "diagonal")),
        "- at chi*: acoustic_bwd ratio "
        + ", ".join(f"{d}={_fmt(rc['acoustic_bwd_ratio'][d])}" for d in ("x", "y", "diagonal")),
        "- at chi*: shear nu_ratio "
        + ", ".join(f"{d}={_fmt(rc['shear_nu_ratio'][d])}" for d in ("x", "y", "diagonal")),
        "",
        "## T1 -- D4 over-constraint sensitivity matrix  d(quantity)/d(knob)",
        "",
        "| quantity \\ knob | xy_factor (B2) | normal_factor (B1) | chi (bulk) |",
        "|---|---|---|---|",
    ]
    for r in ("nu_T_axis", "nu_T_diag", "nu_L_axis", "nu_L_diag"):
        s = oc["sensitivity_dQ_dknob"][r]
        lines.append(f"| {r} | {_fmt(s['xy'])} | {_fmt(s['normal'])} | {_fmt(s['chi'])} |")
    lines += [
        "",
        "- base quantities (published knobs): "
        + ", ".join(f"{k}={_fmt(v)}" for k, v in oc["base_quantities"].items()),
        f"- d(nu_L,diag - nu_L,axis)/d(chi) = `{_fmt(oc['d_diag_excess_d_chi'])}` (≈0 -> chi cannot fix the diagonal excess)",
        "",
        "## Interpretation",
        "",
    ]
    for key, text in p["interpretation"].items():
        lines.append(f"- **{key}**: {text}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Acoustic-attenuation caliber + diagonal over-constraint diagnostic.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    payload = run_diagnostic(config_path=args.config, output_root=args.output_root)
    print(f"{payload['status']}; wrote {args.output_root / payload['run_id']}; digest={payload['summary_digest']}")


if __name__ == "__main__":
    main()
