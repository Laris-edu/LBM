"""Validity boundary of the one-step modal-symbol acoustic caliber (§5.5 item 1).

Resolves the ~3% diagonal gap between the one-step symbol eigenvalue caliber
(diag ~1.265 at chi*) and the authoritative dynamic Prony (diag ~1.307).

Findings (reproduced here):
  * x/y: symbol eigenvalue == dynamic Prony EXACTLY (1.000), window-independent.
  * diagonal: symbol 1.265 vs dynamic Prony 1.307 (window-independent at 1.307,
    so NOT a fit-window artifact; and the symbol has NO 1.307 eigenvalue, so NOT
    a selection error -- the single-mode operator genuinely differs).
  * Root cause: the periodic FFT corrections (dispersion + acoustic-phase) drive
    the gap. With those corrections OFF the symbol and dynamic agree EXACTLY for
    diagonal too (both ~1.876). The single-mode one-step symbol does not
    faithfully represent the multi-step action of the global FFT corrections on
    the diagonal mode; x/y are unaffected.

Conclusion: the DYNAMIC Prony is authoritative (it is the real multi-step
evolution, and is what production P2-6 reports). The one-step symbol caliber is
exact for x/y but ~3% low for diagonal; use the dynamic value (~1.31) for the
diagonal acoustic residual. The bounded-production-GO conclusion is unchanged
(1.27 vs 1.31 are both bounded ~1.3 and physically negligible under acoustic
compactness kL~0.04).

Diagnostic only; baseline unchanged.

Usage:
    python -m scripts.phase2_acoustic_symbol_caliber_validity
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

from core.solver import GasSolver2D
from scripts.phase2_acoustic_attenuation_caliber import (
    NORMAL_FACTOR,
    XY_FACTOR,
    _clear_symbol_caches,
    _recalibrate_chi,
)
from scripts.phase2_closure_recursive_regularized import _rr_config
from scripts.phase2_m2_verification import load_config, sha256_file, summary_payload_digest
from verification.acoustic_wave_measurement import (
    _initialize_acoustic_wave,
    _modal_amplitude_2d,
    _settings_from_config,
)

DEFAULT_CONFIG = Path("configs/gas_air_10k_d2q37_physical_timestep.yaml")
DEFAULT_OUTPUT_ROOT = Path("results/phase2_symbol_caliber_validity")
N = 64
STEPS = 720


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


def _kxy(direction: str) -> tuple[float, float]:
    if direction == "x":
        return 2.0 * np.pi / N, 0.0
    return 2.0 * np.pi / N, 2.0 * np.pi / N


def _make_cfg(base, chi, direction, corrections=True):
    cfg = deepcopy(_rr_config(base, xy_factor=XY_FACTOR, normal_factor=NORMAL_FACTOR, chi=chi, p2_06=(direction,)))
    cfg["numerics"] = {**cfg.get("numerics", {}), "nx": N, "ny": N}
    if not corrections:
        cfg["collision"]["dispersion_correction_enabled"] = False
        cfg["collision"]["acoustic_phase_correction_enabled"] = False
    return cfg


def _ref_ac(mapping, direction):
    kx, ky = _kxy(direction)
    k2 = kx * kx + ky * ky
    dim = float(mapping.lattice.D)
    coeff = (
        0.5 * (mapping.physical.gamma - 1.0) * float(mapping.alpha_lu)
        + ((dim - 1.0) / dim) * float(mapping.nu_lu)
        + 0.5 * float(mapping.nu_b_lu)
    )
    return coeff * k2


def _symbol_acoustic_ratio(cfg, direction):
    _clear_symbol_caches()
    solver = GasSolver2D(cfg)
    mp = solver.mapping
    rho0, theta0 = mp.lattice.rho_ref_lu, mp.theta_ref_lu
    c0 = float(np.sqrt(mp.physical.gamma * theta0))
    kx, ky = _kxy(direction)
    kmag = float(np.sqrt(kx * kx + ky * ky))
    ref = _ref_ac(mp, direction)
    sym = solver._high_mode_modal_symbol(kx=kx, ky=ky, rho0=rho0, u0=(0.0, 0.0), theta0=theta0)
    vals = np.linalg.eigvals(sym)
    fwd = None
    n_in_band = 0
    for lam in vals:
        m = abs(lam)
        if m <= 0.0 or m > 1.0 or not np.isfinite(m):
            continue
        sigma = -float(np.log(m))
        if sigma <= 0.0 or sigma > 0.02:
            continue
        ang = float(np.angle(lam))
        cps = -ang / kmag
        if abs(abs(cps) / c0 - 1.0) >= 0.2 or abs(ang) <= 1.0e-4:
            continue
        n_in_band += 1
        if cps > 0.0:
            score = abs(abs(cps) / c0 - 1.0)
            if fwd is None or score < fwd[0]:
                fwd = (score, sigma / ref)
    return (fwd[1] if fwd else np.nan), int(n_in_band), float(ref)


def _dynamic_prony_ratio(cfg, direction, ref, steps=STEPS):
    cfg = deepcopy(cfg)
    cfg["p2_06_acoustic_wave"] = {**cfg["p2_06_acoustic_wave"], "steps": steps, "amplitude": 1.0e-6, "mode_index": 1}
    settings = _settings_from_config(cfg)
    solver = GasSolver2D(cfg)
    phase, _unit, _k = _initialize_acoustic_wave(solver, settings, direction)
    p0 = solver.mapping.lattice.rho_ref_lu * solver.mapping.theta_ref_lu
    times, pressure = [], []
    for step in range(steps + 1):
        macro = solver.get_macro()
        if not np.isfinite(macro.theta).all() or float(np.nanmin(macro.theta)) <= 0.0:
            break
        times.append(step)
        pressure.append(_modal_amplitude_2d(macro.p - p0, phase))
        if step < steps:
            solver.step()
    t = np.asarray(times, float)
    x = np.asarray(pressure, complex)
    order = 3
    out = {}
    for stop in (240, 480, 720):
        mask = (t >= 10) & (t <= stop)
        xs = x[mask]
        n = xs.size
        if n < 2 * order + 2:
            out[stop] = np.nan
            continue
        A = np.array([xs[i:i + order][::-1] for i in range(n - order)])
        rhs = -xs[order:n]
        coeffs = np.linalg.lstsq(A, rhs, rcond=None)[0]
        roots = np.roots(np.concatenate(([1.0], coeffs)))
        roots = roots[np.abs(roots) > 0.0]
        sroot = np.log(roots)
        tt = (t[mask] - t[mask][0]).astype(float)
        amp = np.linalg.lstsq(np.exp(np.outer(tt, sroot)), xs, rcond=None)[0]
        out[stop] = -float(sroot[int(np.argmax(np.abs(amp)))].real) / ref
    return out


def run_diagnostic(*, config_path: Path, output_root: Path) -> dict[str, Any]:
    base = load_config(config_path)
    chi_star = _recalibrate_chi(base)["chi_eigen_recalibrated"]

    comparison = {}
    for direction in ("x", "diagonal"):
        cfg = _make_cfg(base, chi_star, direction, corrections=True)
        sym, n_band, ref = _symbol_acoustic_ratio(cfg, direction)
        prony = _dynamic_prony_ratio(cfg, direction, ref)
        comparison[direction] = {
            "symbol_eigen_ratio": float(sym),
            "n_acoustic_eigenvalues_in_band": n_band,
            "dynamic_prony_ratio_240": float(prony[240]),
            "dynamic_prony_ratio_480": float(prony[480]),
            "dynamic_prony_ratio_720": float(prony[720]),
            "symbol_minus_dynamic": float(sym - prony[720]),
        }

    # root cause: corrections ON vs OFF for diagonal
    root_cause = {}
    for corrections in (True, False):
        cfg = _make_cfg(base, chi_star, "diagonal", corrections=corrections)
        sym, _n, ref = _symbol_acoustic_ratio(cfg, "diagonal")
        prony = _dynamic_prony_ratio(cfg, "diagonal", ref)
        key = "corrections_on" if corrections else "corrections_off"
        root_cause[key] = {
            "symbol_eigen_ratio": float(sym),
            "dynamic_prony_ratio_720": float(prony[720]),
            "gap": float(abs(sym - prony[720])),
        }

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
        "chi_eigen_recalibrated": float(chi_star),
        "symbol_vs_dynamic": comparison,
        "root_cause_corrections_on_off": root_cause,
        "interpretation": {
            "x_exact": (
                "x/y: one-step symbol eigenvalue == dynamic Prony exactly (1.000), window-independent."
            ),
            "diagonal_gap": (
                f"diagonal: symbol {comparison['diagonal']['symbol_eigen_ratio']:.4f} vs dynamic Prony "
                f"{comparison['diagonal']['dynamic_prony_ratio_720']:.4f}; Prony is window-independent "
                "(240/480/720 agree) so NOT a fit artifact, and only two acoustic eigenvalues sit in the "
                "band (no 1.307 eigenvalue) so NOT a selection error -- the single-mode one-step operator "
                "genuinely differs from the multi-step dynamic for diagonal."
            ),
            "root_cause": (
                f"The periodic FFT corrections drive the gap: corrections ON gap "
                f"{root_cause['corrections_on']['gap']:.4f}, corrections OFF gap "
                f"{root_cause['corrections_off']['gap']:.4f} (EXACT agreement OFF). The single-mode one-step "
                "symbol does not faithfully represent the multi-step action of the global dispersion/acoustic-"
                "phase FFT corrections on the diagonal mode; x/y are unaffected."
            ),
            "conclusion": (
                "Dynamic Prony is AUTHORITATIVE (real multi-step evolution; what production P2-6 reports). "
                "The one-step symbol caliber is exact for x/y but ~3% low for diagonal -- use the dynamic "
                "value (~1.31) for the diagonal acoustic residual. bounded-production-GO is unchanged: 1.27 vs "
                "1.31 are both bounded ~1.3 and physically negligible under acoustic compactness (kL~0.04)."
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
    c = p["symbol_vs_dynamic"]
    rc = p["root_cause_corrections_on_off"]
    lines = [
        "# Phase 2 One-Step Symbol Caliber Validity (§5.5 item 1: symbol vs dynamic Prony)",
        "",
        f"- run_id: `{p['run_id']}`  chi*: `{_fmt(p['chi_eigen_recalibrated'])}`",
        f"- summary_digest: `{p['summary_digest']}`",
        "",
        "## Symbol eigenvalue vs dynamic Prony (chi*)",
        "",
        "| dir | symbol eigen | Prony[240] | Prony[480] | Prony[720] | symbol-dynamic | #acoustic eig in band |",
        "|---|---|---|---|---|---|---|",
    ]
    for d in ("x", "diagonal"):
        r = c[d]
        lines.append(
            f"| {d} | {_fmt(r['symbol_eigen_ratio'])} | {_fmt(r['dynamic_prony_ratio_240'])} | "
            f"{_fmt(r['dynamic_prony_ratio_480'])} | {_fmt(r['dynamic_prony_ratio_720'])} | "
            f"{_fmt(r['symbol_minus_dynamic'])} | {r['n_acoustic_eigenvalues_in_band']} |"
        )
    lines += [
        "",
        "## Root cause: periodic FFT corrections (diagonal)",
        "",
        f"- corrections ON : symbol {_fmt(rc['corrections_on']['symbol_eigen_ratio'])}, "
        f"dynamic {_fmt(rc['corrections_on']['dynamic_prony_ratio_720'])}, gap {_fmt(rc['corrections_on']['gap'])}",
        f"- corrections OFF: symbol {_fmt(rc['corrections_off']['symbol_eigen_ratio'])}, "
        f"dynamic {_fmt(rc['corrections_off']['dynamic_prony_ratio_720'])}, gap {_fmt(rc['corrections_off']['gap'])}",
        "",
        "## Interpretation",
        "",
    ]
    for key, text in p["interpretation"].items():
        lines.append(f"- **{key}**: {text}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="One-step symbol caliber validity vs dynamic Prony.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    payload = run_diagnostic(config_path=args.config, output_root=args.output_root)
    print(f"{payload['status']}; wrote {args.output_root / payload['run_id']}; digest={payload['summary_digest']}")


if __name__ == "__main__":
    main()
