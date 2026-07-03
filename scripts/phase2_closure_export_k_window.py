"""Conductive heat-flux EXPORT k-window diagnostic (Phase_2 readout chain).

Motivated by Phase_3 P3-6 (M3 amplitude boundary): the exported conductive ``q_lu`` is a
single-scalar (``conductive_heat_flux_moment_factor``) point calibration of the raw central
energy-flux moment. This script characterizes, per axis wavenumber ``k = 2*pi/grid`` on a
mid-decay isobaric thermal sine (the P2-5 setting):

1. ``export ratio(k)``  -- full production readout (``heat_flux_lu`` with mapping: spectral
   corrections + moment factor + Galilean term) vs the analytic Fourier flux
   ``F = -(D+S+2)/2 * rho * alpha_lu * grad(theta)``;
2. the analytic spectral-correction multiplier at that ``k`` (from the config constants),
   so the raw-moment shape can be deconvolved from the window;
3. the equilibrium-streaming artifact decomposition: ``M_art`` = raw moment of the
   one-step-streamed local equilibria vs ``M_full`` = raw moment of the actual ``(f, g)``
   and ``M_eq0`` = raw moment of unstreamed equilibria (~0 by construction).

Findings anchored by this script (see docs/Phase_2/closure/Phase2_Conductive_Export_K_Window.md):
the raw moment is dominated by the streaming finite-difference artifact of the EQUILIBRIA
(M_eq0 ~ 0, M_art/M_full ~ 1.4, both ~ k^2, ~16x the physical flux at the calibration k),
so the export is only correct in a narrow band around the calibrated ``k`` and a k-robust
moment-based export requires modelling the neq k^2 channel (research), not a rescale.

Diagnostic only: no pass/fail gate, no production claim.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import platform
import sys
from typing import Any

import numpy as np

from core.equilibrium import equilibrium_fg
from core.macroscopic import central_energy_flux_lu, heat_flux_lu, recover_macro
from core.solver import GasSolver2D
from core.streaming import pull_stream_fg
from scripts.phase2_m2_verification import load_config, sha256_file, summary_payload_digest


DEFAULT_CONFIG = Path("configs/gas_air_10k_d2q37_levelc_dx2p6.yaml")
DEFAULT_OUTPUT_ROOT = Path("results/phase2_export_window")
DEFAULT_GRIDS = (32, 48, 64, 96, 128)
VOLATILE_DIGEST_KEYS = ("run_id", "python", "platform", "config_path")


def _modal_amp_x(field: np.ndarray, mode_index: int = 1) -> complex:
    """Complex amplitude of the x-direction mode (matches P2-5 conventions)."""

    arr = np.asarray(field, dtype=float)
    nx = arr.shape[1]
    phase = 2.0 * np.pi * mode_index * np.arange(nx) / nx
    centered = arr - np.mean(arr)
    return complex((2.0 / centered.size) * np.sum(centered * np.exp(-1j * phase)[None, :]))


def spectral_correction_multiplier(k: float, *, target: float, low: float, high: float) -> float:
    """Exact axis-mode multiplier of ``apply_periodic_spectral_correction``."""

    mu = 4.0 * math.sin(0.5 * k) ** 2
    ramp = min(max((mu - low) / (high - low), 0.0), 1.0)
    smooth = ramp * ramp * (3.0 - 2.0 * ramp)
    return 1.0 + (target - 1.0) * smooth


def probe_grid(config: dict[str, Any], grid: int, *, steps: int) -> dict[str, Any]:
    cfg = json.loads(json.dumps(config))  # deep copy
    cfg["numerics"] = {**cfg.get("numerics", {}), "nx": grid, "ny": grid}
    solver = GasSolver2D(cfg)
    mapping = solver.mapping
    theta0 = float(mapping.theta_ref_lu)
    phase = 2.0 * np.pi * np.arange(grid) / grid
    theta = theta0 * (1.0 + 1.0e-5 * np.sin(phase))[None, :] * np.ones((grid, 1))
    rho = (mapping.lattice.rho_ref_lu * theta0) / theta
    solver.initialize_from_macro(rho, np.zeros((grid, grid, 2)), theta)
    solver.step(steps)

    f, g = solver.f.copy(), solver.g.copy()
    D, S, lat = mapping.lattice.D, mapping.lattice.S, solver.lattice
    macro = recover_macro(f, g, D=D, S=S, lattice=lat)
    theta_hat = _modal_amp_x(macro.theta)
    k = 2.0 * math.pi / grid

    # Full production export chain (spectral corrections + factor + Galilean term).
    q_export = heat_flux_lu(f, g, lattice=lat, mapping=mapping)[..., 0]
    export_hat = _modal_amp_x(q_export)
    # Analytic Fourier flux of the resolved theta field: F = -cp_lu * rho * alpha_lu * dtheta/dx,
    # cp_lu = (D + S + 2) / 2 for the ideal polyatomic pair (rho ~ rho_ref at 1e-5 amplitude).
    cp_lu = 0.5 * (D + S + 2.0)
    fourier_hat = -1j * k * cp_lu * float(mapping.lattice.rho_ref_lu) * float(mapping.alpha_lu) * theta_hat
    ratio = export_hat / fourier_hat

    # Raw-moment decomposition (no corrections, no factor).
    qx_raw = lambda ff, gg: central_energy_flux_lu(ff, gg, lattice=lat)[..., 0]
    feq, geq = equilibrium_fg(macro.rho, macro.u, macro.theta, S, lat)
    feq_s, geq_s = pull_stream_fg(feq, geq, lattice=lat, y_axis=0, x_axis=1)
    M_full = _modal_amp_x(qx_raw(f, g))
    M_art = _modal_amp_x(qx_raw(feq_s, geq_s))
    M_eq0 = _modal_amp_x(qx_raw(feq, geq))

    corr = spectral_correction_multiplier(
        k,
        target=float(mapping.collision.conductive_heat_flux_dispersion_target),
        low=float(mapping.collision.dispersion_correction_low_laplacian),
        high=float(mapping.collision.dispersion_correction_high_laplacian),
    )
    return {
        "grid": grid,
        "k": k,
        "steps": steps,
        "export_ratio_real": float(np.real(ratio)),
        "export_ratio_abs": float(abs(ratio)),
        "correction_multiplier": corr,
        "raw_shape_deconvolved": float(abs(ratio)) / corr,
        "M_full_per_theta": float(abs(M_full) / abs(theta_hat)),
        "M_art_per_theta": float(abs(M_art) / abs(theta_hat)),
        "M_eq0_per_theta": float(abs(M_eq0) / abs(theta_hat)),
        "M_art_over_M_full": float(abs(M_art) / abs(M_full)),
        "fourier_per_theta": float(abs(fourier_hat) / abs(theta_hat)),
        "raw_over_fourier": float(abs(M_full) / abs(fourier_hat)),
    }


def run_window_probe(*, config_path: Path, output_root: Path, grids: tuple[int, ...], steps: int) -> dict[str, Any]:
    config = load_config(config_path)
    rows = [probe_grid(config, grid, steps=steps) for grid in grids]

    # k-scaling exponents of the artifact and full raw moment between extreme grids.
    lo = rows[-1]  # largest grid -> smallest k
    hi_candidates = [r for r in rows if r["correction_multiplier"] > 0.999]
    hi = hi_candidates[0] if hi_candidates else rows[0]

    def _exponent(a: dict[str, Any], b: dict[str, Any], key: str) -> float:
        return float(math.log(a[key] / b[key]) / math.log(a["k"] / b["k"]))

    payload: dict[str, Any] = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "status": "DIAGNOSTIC",
        "scope": "PHASE2_CONDUCTIVE_EXPORT_K_WINDOW",
        "config_path": str(config_path),
        "config_sha256": sha256_file(config_path),
        "python": sys.version,
        "platform": platform.platform(),
        "grids": list(grids),
        "steps": steps,
        "rows": rows,
        "artifact_k_exponent": _exponent(hi, lo, "M_art_per_theta"),
        "full_moment_k_exponent": _exponent(hi, lo, "M_full_per_theta"),
        "note": "export ratio is a (tau,k) point calibration; raw moment is dominated by the "
                "equilibrium-streaming artifact (~k^2, ~alpha-independent); see "
                "docs/Phase_2/closure/Phase2_Conductive_Export_K_Window.md",
    }
    safe = payload
    digest_core = {kk: vv for kk, vv in safe.items() if kk not in VOLATILE_DIGEST_KEYS}
    safe["summary_digest"] = summary_payload_digest(digest_core)
    safe["summary_digest_scope"] = "physics_core; excludes " + ", ".join(VOLATILE_DIGEST_KEYS)
    out_dir = output_root / payload["run_id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(safe, indent=2, ensure_ascii=False), encoding="utf-8")
    return safe


def main() -> None:
    parser = argparse.ArgumentParser(description="Conductive heat-flux export k-window diagnostic (Phase_2).")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--grids", type=int, nargs="*", default=list(DEFAULT_GRIDS))
    parser.add_argument("--steps", type=int, default=50)
    args = parser.parse_args()
    payload = run_window_probe(
        config_path=args.config, output_root=args.output_root, grids=tuple(args.grids), steps=args.steps
    )
    print(f"{'grid':>5} {'k':>7} {'ratio':>8} {'corr':>7} {'raw(deconv)':>11} "
          f"{'M_art/M_full':>12} {'raw/Fourier':>11} {'M_eq0/theta':>11}")
    for r in payload["rows"]:
        print(f"{r['grid']:>5} {r['k']:>7.4f} {r['export_ratio_real']:>8.4f} {r['correction_multiplier']:>7.4f} "
              f"{r['raw_shape_deconvolved']:>11.4f} {r['M_art_over_M_full']:>12.4f} "
              f"{r['raw_over_fourier']:>11.2f} {r['M_eq0_per_theta']:>11.2e}")
    print(f"artifact k-exponent ~ {payload['artifact_k_exponent']:.3f}; "
          f"full-moment k-exponent ~ {payload['full_moment_k_exponent']:.3f}; "
          f"digest={payload['summary_digest']}")


if __name__ == "__main__":
    main()
