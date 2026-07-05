"""P4-1 terminal diagnostic: volume-operator wave injection floor (committed probe).

Reproduces the three decisive 2026-07-04 experiments that closed the P4-1 open-boundary
investigation on the frozen dx2p6 stack (see
``docs/Phase_4/M4/P4_1_Open_Boundary_Diagnostic_Report.md``):

1. ``seam``      -- tall fully-periodic column, production ``thermal_grad`` oscillating
                    wall at the bottom (the seam any boundary row creates), first-crossing
                    window only: the intrinsic |w-|/|w+| of the outgoing wave GROWS at
                    ~1.1e-4/step (0.003 -> 0.15 across the window).
2. ``ablation``  -- same rig with collision-correction switches: ``dispersion off``
                    cuts the growth ~4x; ``acoustic_phase off`` and
                    ``trace current_zero`` change nothing (bitwise-equal traces).
3. ``seam_free`` -- fully periodic, NO callbacks, smooth Gaussian w+ pulse whose
                    k-content stays below the correction band (sigma=200 cells):
                    |w-|/|w+| stays at the 1e-4 floor. The bulk transports smooth
                    periodic waves cleanly; the injection needs the seam.

Mechanism: any imposed boundary row is a y-discontinuity; the global periodic FFT
correction operators (dominantly the dispersion-correction pair) multiply that seam's
spectral leakage tail (k >= low_laplacian) by (target-1) every step, and the inverse
transform delivers a DELOCALIZED perturbation whose down-going part reads as reflection.
Steady state in a bounded column: injection rate x residence time ~ 1e-4 x L/c ~ 0.2-0.3
-- matching every boundary variant's measured |R| (clamp 0.28-0.33, strip 0.30+). The
P4-1 gate |R|<0.05 is therefore unreachable by ANY local top boundary on this stack;
the floor lives in the volume operators (contract 13.2 degradation path).

Diagnostic only: never claims a gate; config switches are probe-local (the frozen
production config is untouched).
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from core.macroscopic import recover_macro
from core.solver import GasSolver2D
from scripts.phase2_m2_verification import load_config, summary_payload_digest
from scripts.phase4_open_boundary_reflection import make_thermal_drive_wall_callback

DEFAULT_GAS_CONFIG = Path("configs/gas_air_10k_d2q37_levelc_dx2p6.yaml")
DEFAULT_OUTPUT_ROOT = Path("results/m4")
PROBE_FREQUENCY_HZ = 4.0e4      # diagnostic frequency: window fits before the wrap returns
VOLATILE_DIGEST_KEYS = ("run_id", "gas_config_path", "artifacts")


def _solver(gas_config_path: Path, ny: int, nx: int, collision_mods: dict[str, Any]) -> GasSolver2D:
    gas = load_config(gas_config_path)
    gas["numerics"] = {**gas.get("numerics", {}), "nx": nx, "ny": ny}
    for key, value in collision_mods.items():
        gas["collision"][key] = value
    solver = GasSolver2D(gas)
    solver.initialize_from_macro(
        solver.mapping.lattice.rho_ref_lu,
        np.zeros((ny, nx, 2)),
        solver.mapping.theta_ref_lu,
    )
    return solver


def _wave_frame(solver: GasSolver2D) -> dict[str, float]:
    theta0 = float(solver.mapping.theta_ref_lu)
    rho0 = float(solver.mapping.lattice.rho_ref_lu)
    c_lu = math.sqrt((1.0 + 2.0 / (2 + 3)) * theta0)
    return {"theta0": theta0, "rho0": rho0, "c_lu": c_lu, "z0": rho0 * c_lu, "p_ref": rho0 * theta0}


def _band_ratio(solver: GasSolver2D, rows: np.ndarray, frame: dict[str, float]) -> float:
    m = recover_macro(solver.f[rows], solver.g[rows], D=2, S=3, lattice=solver.lattice)
    p_prime = np.mean(m.p, axis=-1) - frame["p_ref"]
    v = np.mean(m.u[..., 1], axis=-1)
    w_minus = p_prime - frame["z0"] * v
    w_plus = p_prime + frame["z0"] * v
    return float(np.sqrt(np.mean(w_minus**2)) / max(np.sqrt(np.mean(w_plus**2)), 1e-300))


def seam_growth_trace(gas_config_path: Path, collision_mods: dict[str, Any] | None = None) -> list[float]:
    """Intrinsic |w-|/|w+| growth in the first-crossing window of a wall-seamed column."""

    solver = _solver(gas_config_path, ny=1024, nx=4, collision_mods=collision_mods or {})
    frame = _wave_frame(solver)
    dt = float(solver.mapping.lattice.dt_s)
    omega = 2.0 * math.pi * PROBE_FREQUENCY_HZ
    callback = make_thermal_drive_wall_callback(
        theta0_lu=frame["theta0"],
        theta_hat_lu=(0.354 / 300.0) * frame["theta0"],
        omega_si=omega,
        dt_si=dt,
        ramp_steps=int(0.35 / (PROBE_FREQUENCY_HZ * dt)),
    )
    rows = np.arange(64, 384, 16)
    trace = []
    now = 0
    for target in range(2400, 3801, 200):
        solver.step(target - now, boundary_callback=callback)
        now = target
        trace.append(_band_ratio(solver, rows, frame))
    return trace


def seam_free_pulse_trace(gas_config_path: Path) -> list[float]:
    """|w-|/|w+| of a smooth Gaussian w+ pulse in a fully periodic, callback-free column."""

    solver = _solver(gas_config_path, ny=2048, nx=4, collision_mods={})
    frame = _wave_frame(solver)
    ny, nx = solver.ny, solver.nx
    y = np.arange(ny, dtype=float)[:, None] * np.ones((1, nx))
    p_prime = 1e-6 * frame["p_ref"] * np.exp(-((y - 512.0) ** 2) / (2.0 * 200.0**2))
    rho = frame["rho0"] + p_prime / (frame["c_lu"] ** 2)
    u = np.zeros((ny, nx, 2))
    u[..., 1] = p_prime / frame["z0"]
    solver.initialize_from_macro(rho, u, (frame["p_ref"] + p_prime) / rho)
    rows = np.arange(900, 1500, 20)
    trace = []
    for target in (600, 1200, 1800, 2400, 3000):
        solver.step(target - solver.t_lu)
        trace.append(_band_ratio(solver, rows, frame))
    return trace


def run_probe(gas_config_path: Path, output_root: Path) -> dict[str, Any]:
    seam_baseline = seam_growth_trace(gas_config_path)
    ablations = {
        "acoustic_phase_off": seam_growth_trace(gas_config_path, {"acoustic_phase_correction_enabled": False}),
        "dispersion_off": seam_growth_trace(gas_config_path, {"dispersion_correction_enabled": False}),
        "trace_current_zero": seam_growth_trace(gas_config_path, {"trace_bulk_policy": "current_zero"}),
        # P4-1b route-b' fix under test: seam-aware windowed operators (corrections +
        # filter, one mechanism). History: the wrap-only detrend variant measured x0.66
        # (0.154 -> 0.102) and was refuted per gate G3 -- interior imposition kinks
        # dominate over the wrap jump (project doc sections 5-6, 2026-07-04).
        "seam_aware_window": seam_growth_trace(
            gas_config_path,
            {"seam_aware_bottom_rows": 1, "seam_aware_top_rows": 3, "seam_aware_taper_rows": 6},
        ),
    }
    seam_free = seam_free_pulse_trace(gas_config_path)

    growth_rate_per_step = (seam_baseline[-1] - seam_baseline[0]) / (3800 - 2400)
    payload: dict[str, Any] = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "status": "DIAGNOSTIC",
        "phase": "Phase_4",
        "p4_stage": "P4-1",
        "m4_gate": "NOT_CLAIMED",
        "scope": "P4-1_VOLUME_INJECTION_FLOOR_PROBE",
        "gas_config_path": str(gas_config_path),
        "probe_frequency_Hz": PROBE_FREQUENCY_HZ,
        "window_steps": [2400, 3800],
        "seam_baseline_w_minus_over_w_plus": seam_baseline,
        "seam_ablations": ablations,
        "seam_free_pulse": seam_free,
        "injection_rate_per_step": growth_rate_per_step,
        "steady_state_floor_estimate": {
            "residence_steps_ny512": 512 / 0.26025,
            "predicted_R_floor": growth_rate_per_step * 512 / 0.26025,
            "measured_clamp_R_20_40kHz": [0.2823, 0.3300],
        },
        "conclusion": (
            "any boundary-row seam feeds the global periodic FFT corrections (dominant: "
            "dispersion pair) which inject delocalized wave content at ~1e-4/step; the "
            "bounded-column steady state ~0.2-0.3 is a volume floor no local top boundary "
            "can beat; |R|<0.05 unreachable on the frozen stack (contract 13.2 path)"
        ),
    }
    digest_core = {k: v for k, v in payload.items() if k not in VOLATILE_DIGEST_KEYS}
    payload["summary_digest"] = summary_payload_digest(digest_core)
    payload["summary_digest_scope"] = "physics_core; excludes " + ", ".join(VOLATILE_DIGEST_KEYS)

    out_dir = output_root / payload["run_id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="P4-1 volume-injection floor probe (diagnostic).")
    parser.add_argument("--gas-config", type=Path, default=DEFAULT_GAS_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    payload = run_probe(args.gas_config, args.output_root)
    print("seam baseline :", [f"{v:.3f}" for v in payload["seam_baseline_w_minus_over_w_plus"]])
    for name, trace in payload["seam_ablations"].items():
        print(f"{name:18s}:", [f"{v:.3f}" for v in trace])
    print("seam-free     :", [f"{v:.4f}" for v in payload["seam_free_pulse"]])
    print(
        f"injection {payload['injection_rate_per_step']:.2e}/step -> predicted floor "
        f"{payload['steady_state_floor_estimate']['predicted_R_floor']:.2f} "
        f"(measured clamp 0.28-0.33); wrote {args.output_root / payload['run_id']}; "
        f"digest={payload['summary_digest']}"
    )


if __name__ == "__main__":
    main()
