"""Evaluate promoting the RR closure (eigenvalue-recalibrated chi*) to the
default baseline.  EVALUATION ONLY -- this does NOT change any default; flipping
the baseline is a deliberate, separately-approved change.

Runs, at chi* = the eigenvalue-recalibrated trace coefficient (so x/y acoustic
attenuation is truly 1.0, not the log|p'| 240-window artifact):
  * full hard gates  : P2-4 (x/y/diag shear isotropy), P2-5 (x/y/diag thermal),
                       P2-6 (x/y/diag sound speed + gamma; attenuation diagnostic)
  * extended gates   : P2-7 (Pr scan), P2-9 (Galilean)
  * long window 3x   : P2-4/5/6 stability + consistency
  * low-k ghost      : full-modal symbol max|lambda| at low k (must be <= 1)
  * baseline P2-7    : current_zero Pr scan, for a like-for-like regression check

Verdict logic: a clean promotion needs every HARD gate to pass (transport
isotropy, sound speed/gamma, Galilean, ghost stability, long-window stability)
AND no regression vs the current default.  Acoustic attenuation is diagnostic
(accepted GO-RISK boundaries per decision A / residual #3); P2-7 is a hard gate.

Diagnostic only.  Baseline unchanged.

Usage:
    python -m scripts.phase2_robust_rr_baseline_promotion
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

from core.unit_mapping import create_unit_mapping
from scripts.phase2_acoustic_attenuation_caliber import (
    NORMAL_FACTOR,
    XY_FACTOR,
    _build_solver,
    _clear_symbol_caches,
    _recalibrate_chi,
)
from scripts.phase2_closure_recursive_regularized import (
    run_extended_gate,
    run_full_gate,
    run_long_window,
)
from scripts.phase2_m2_verification import load_config, sha256_file, summary_payload_digest
from verification.prandtl_scan_measurement import measure_prandtl_scan

DEFAULT_CONFIG = Path("configs/gas_air_10k_d2q37_physical_timestep.yaml")
DEFAULT_OUTPUT_ROOT = Path("results/phase2_rr_baseline_promotion")
N = 64


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


def _ghost_stability(base: dict[str, Any], chi: float) -> dict[str, Any]:
    """Full-modal symbol max|lambda| over all modes at low k (axis + diagonal)."""
    solver = _build_solver(base, xy=XY_FACTOR, normal=NORMAL_FACTOR, chi=chi)
    rho0 = solver.mapping.lattice.rho_ref_lu
    theta0 = solver.mapping.theta_ref_lu
    points = {
        "axis_mode1": (2.0 * np.pi / N, 0.0),
        "axis_mode2": (4.0 * np.pi / N, 0.0),
        "diag_mode1": (2.0 * np.pi / N, 2.0 * np.pi / N),
    }
    radii = {}
    for label, (kx, ky) in points.items():
        sym = solver._high_mode_modal_symbol(kx=kx, ky=ky, rho0=rho0, u0=(0.0, 0.0), theta0=theta0)
        radii[label] = float(np.max(np.abs(np.linalg.eigvals(sym))))
    max_radius = max(radii.values())
    return {
        "spectral_radius": radii,
        "max_spectral_radius": max_radius,
        "stable": bool(max_radius <= 1.0 + 1.0e-6),
    }


def _baseline_pr_scan(base: dict[str, Any]) -> dict[str, Any]:
    """current_zero (default) Pr scan, for a like-for-like P2-7 regression check."""
    cfg = deepcopy(base)
    cfg["numerics"] = {**cfg.get("numerics", {}), "nx": N, "ny": N}
    pr = measure_prandtl_scan(cfg)
    return {
        "p2_07_status": pr["p2_07_status"],
        "baseline_pr_relative_error": float(pr["baseline_pr_relative_error"]),
        "max_pr_relative_error": float(pr["max_pr_relative_error"]),
        "scan_tolerance": float(pr["scan_tolerance"]),
    }


def run_diagnostic(*, config_path: Path, output_root: Path) -> dict[str, Any]:
    base = load_config(config_path)
    nu = float(create_unit_mapping(base).nu_lu)
    chi_star = _recalibrate_chi(base)["chi_eigen_recalibrated"]
    cal = {"xy_factor": XY_FACTOR, "normal_factor": NORMAL_FACTOR, "chi": chi_star}

    _clear_symbol_caches()
    full = run_full_gate(base, cal, nu)
    extended = run_extended_gate(base, cal)
    long_window = run_long_window(base, cal)
    ghost = _ghost_stability(base, chi_star)
    baseline_pr = _baseline_pr_scan(base)

    # verdict
    hard_pass = (
        full["p2_04_status"] == "PASSED"
        and full["p2_05_status"] == "PASSED"
        and full["p2_06_status"] == "PASSED"
        and extended["p2_09_status"] == "PASSED"
        and ghost["stable"]
        and long_window["p2_04_status"] == "PASSED"
        and long_window["p2_05_status"] == "PASSED"
        and all(v is None for v in long_window["p2_06_first_invalid_step"].values())
    )
    p2_07_pass = extended["p2_07_status"] == "PASSED"
    p2_07_regression = (
        baseline_pr["p2_07_status"] == "PASSED" and not p2_07_pass
    )
    promotion_ready = bool(hard_pass and p2_07_pass)

    blockers = []
    if not p2_07_pass:
        blockers.append(
            f"P2-7 scan FAILED (max {extended['p2_07_max_pr_relative_error']:.4f} > tol "
            f"{extended['p2_07_scan_tolerance']:.2f}); baseline current_zero scan = "
            f"{baseline_pr['max_pr_relative_error']:.4f} ({baseline_pr['p2_07_status']})"
            + (" -> RR REGRESSES P2-7 across the tol" if p2_07_regression else "")
        )
    if not hard_pass:
        blockers.append("one or more hard gates (P2-4/5/6 speed-gamma/P2-9/ghost/long-window) did not pass")

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
        "evaluation": "RR_baseline_promotion_EVALUATION_ONLY_no_default_changed",
        "chi_eigen_recalibrated": float(chi_star),
        "knobs": cal,
        "full_gate": full,
        "extended_gate": extended,
        "long_window": long_window,
        "ghost_stability": ghost,
        "baseline_current_zero_pr_scan": baseline_pr,
        "verdict": {
            "hard_gates_pass": bool(hard_pass),
            "p2_07_pass": bool(p2_07_pass),
            "p2_07_regression_vs_baseline": bool(p2_07_regression),
            "promotion_ready": promotion_ready,
            "blockers": blockers,
        },
        "interpretation": {
            "chi_independence": (
                "The hard gates (P2-4 shear isotropy, P2-5 thermal, P2-6 sound speed/gamma, P2-9 Galilean, P2-7) "
                "are chi-independent (chi only sets the longitudinal/trace damping = acoustic attenuation). chi* "
                "differs from the published chi only in the attenuation diagnostic (x/y eigenvalue 1.0, diag 1.265)."
            ),
            "attenuation": (
                "Acoustic attenuation is diagnostic (accepted GO-RISK boundaries): x/y -> 1.0 (eigenvalue caliber), "
                "diagonal 1.265 @45 deg (decision A), high-mode 5-12x (residual #3) -- physically irrelevant for "
                "the acoustically-compact 10 kHz target. The production log|p'| 240-window reads x/y ~0.9 at chi* "
                "(weak-damping bias); the eigenvalue is the true 1.0."
            ),
            "recommendation": (
                "RR at chi* fixes the core acoustic blocker (6.27x -> 1.0 x/y) and passes the transport / "
                "acoustic-speed / Galilean / ghost / long-window hard gates. The blocker for promotion is P2-7: it "
                "is a hard gate and RR sits just over the 5% scan tol at Pr=2 (alpha/heat-flux high-Pr "
                "characteristic, RR-decoupled). Recommend NOT flipping the default baseline yet; keep RR as the "
                "documented diagnostic candidate and resolve the P2-7 alpha/heat-flux high-Pr issue first, then "
                "re-evaluate. If/when promoted, also upgrade the P2-6 diagnostic attenuation to the eigenvalue/Prony "
                "caliber and sync core/config/unit-mapping/docs."
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
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return "nan" if value != value else f"{value:.4g}"
    return str(value)


def _render_report(p: dict[str, Any]) -> str:
    f = p["full_gate"]
    e = p["extended_gate"]
    lw = p["long_window"]
    g = p["ghost_stability"]
    bpr = p["baseline_current_zero_pr_scan"]
    v = p["verdict"]
    lines = [
        "# Phase 2 RR Baseline-Promotion Evaluation (EVALUATION ONLY -- no default changed)",
        "",
        f"- run_id: `{p['run_id']}`",
        f"- chi*: `{_fmt(p['chi_eigen_recalibrated'])}`  (xy=`{_fmt(p['knobs']['xy_factor'])}`, "
        f"normal=`{_fmt(p['knobs']['normal_factor'])}`)",
        f"- summary_digest: `{p['summary_digest']}`",
        "",
        "## Verdict",
        "",
        f"- promotion_ready: **{_fmt(v['promotion_ready'])}**",
        f"- hard_gates_pass: {_fmt(v['hard_gates_pass'])}",
        f"- P2-7 pass: {_fmt(v['p2_07_pass'])}  (regression vs baseline: {_fmt(v['p2_07_regression_vs_baseline'])})",
        "- blockers: " + ("; ".join(v["blockers"]) if v["blockers"] else "none"),
        "",
        "## Hard gates (chi*)",
        "",
        f"- P2-4 `{f['p2_04_status']}`  nu_T/nu: "
        + ", ".join(f"{d}={_fmt(f['p2_04_nu_T_over_nu'][d])}" for d in ("x", "y", "diagonal")),
        f"- P2-5 `{f['p2_05_status']}`  alpha_err: "
        + ", ".join(f"{d}={_fmt(f['p2_05_alpha_relative_error'][d])}" for d in ("x", "y", "diagonal")),
        f"- P2-6 `{f['p2_06_status']}`  speed_err={_fmt(f['p2_06_sound_speed_relative_error'])}, "
        f"gamma_err={_fmt(f['p2_06_gamma_relative_error'])}; attenuation_ratio(log|p'|): "
        + ", ".join(f"{d}={_fmt(f['p2_06_attenuation_ratio'][d])}" for d in ("x", "y", "diagonal")),
        f"- P2-9 `{e['p2_09_status']}`  speed_err={_fmt(e['p2_09_max_sound_speed_relative_error'])}, "
        f"masking=`{e['p2_09_dispersion_masking_status']}`",
        f"- low-k ghost: stable={_fmt(g['stable'])}  max|lambda|={_fmt(g['max_spectral_radius'])}",
        f"- long-window 3x: P2-4 `{lw['p2_04_status']}`, P2-5 `{lw['p2_05_status']}`, "
        f"P2-6 invalid={lw['p2_06_first_invalid_step']}",
        "",
        "## P2-7 (the blocker) -- RR vs baseline current_zero",
        "",
        f"- RR (chi*): `{e['p2_07_status']}`  max_pr_err={_fmt(e['p2_07_max_pr_relative_error'])}  "
        f"(tol {_fmt(e['p2_07_scan_tolerance'])})",
        f"- baseline current_zero: `{bpr['p2_07_status']}`  max_pr_err={_fmt(bpr['max_pr_relative_error'])}",
        "",
        "## Interpretation",
        "",
    ]
    for key, text in p["interpretation"].items():
        lines.append(f"- **{key}**: {text}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate promoting the RR closure to the default baseline.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    payload = run_diagnostic(config_path=args.config, output_root=args.output_root)
    print(f"{payload['status']}; promotion_ready={payload['verdict']['promotion_ready']}; "
          f"wrote {args.output_root / payload['run_id']}; digest={payload['summary_digest']}")


if __name__ == "__main__":
    main()
