"""Phase_5 G0-B effective-property measurement runner (contract §5, WP2).

Measures the frozen-mapping LBM's effective transport/acoustic laws
``nu_eff/alpha_eff/c_eff/gamma_eff(T_b, k)`` on uniform non-reference
backgrounds (isobaric main path, equal-density diagnostic), reusing the
certified Phase_2 measurement kernels (`verification/*_measurement.py`,
extended with background support in WP2 — P2 defaults byte-identical).

Frozen-mapping discipline (§5.1) holds BY CONSTRUCTION: the UnitMapping is
created once from the inherited gas config; backgrounds enter only through
the initial condition — tau/closure/dx/dt are never re-derived per T_b.

Outputs (results/phase5/g0_effective_properties/<run_id>/):
  summary.json          gate metadata + gate rows + matrix digest
  property_table.csv    long-format effective-property table (contract §5.4)
  gate_evaluation.json  §5.3 rows -> PASSED / FAILED / SCOPED_CANDIDATE
  run_report.md         human-readable report

No fitting of a temperature exponent is performed here (contract §5.2 forbids
pre-imposing a law); the table IS the deliverable, and the model-freeze doc
decides law-vs-table.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from core.unit_mapping import create_unit_mapping
from scripts.phase2_m2_verification import load_config
from verification.acoustic_wave_measurement import (
    AcousticWaveSettings,
    measure_acoustic_wave_direction,
)
from verification.shear_wave_measurement import ShearWaveSettings, measure_shear_wave_direction
from verification.thermal_diffusion_measurement import (
    ThermalDiffusionSettings,
    measure_thermal_diffusion_direction,
)

GATE_ID = "G0-B"
PHASE5_CONTRACT_VERSION = "v1.2"


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _diffusive_steps(k_lu: float, d_nom: float, policy: dict[str, Any]) -> tuple[int, int, int]:
    frac = float(policy.get("diffusive_decay_fraction", 0.35))
    steps = int(math.ceil(frac / max(d_nom * k_lu * k_lu, 1e-30)))
    steps = int(min(max(steps, int(policy.get("diffusive_min", 4000))), int(policy.get("diffusive_max", 44000))))
    interval = max(1, steps // 400)  # ~400 samples: ample for the decay fit, keeps
    return steps, interval, max(steps // 8, 10)  # the per-sample macro/heat-flux cost bounded

def _acoustic_steps(k_lu: float, c_nom: float, policy: dict[str, Any]) -> tuple[int, int, int]:
    periods = float(policy.get("acoustic_periods", 14))
    steps = int(math.ceil(periods * 2.0 * math.pi / max(c_nom * k_lu, 1e-30)))
    steps = int(min(max(steps, int(policy.get("acoustic_min", 2000))), int(policy.get("acoustic_max", 20000))))
    interval = max(1, steps // 800)
    return steps, interval, max(steps // 10, 10)


def run_g0(config_path: Path, output_root: Path | None = None) -> dict[str, Any]:
    cfg = load_config(config_path)
    g0 = cfg["g0"]
    gates = cfg["gates"]
    gas_config_path = Path(cfg["inheritance"]["gas_config_path"])
    gas = load_config(gas_config_path)
    mapping = create_unit_mapping(gas)

    theta_ref = float(mapping.theta_ref_lu)
    rho_ref = float(mapping.lattice.rho_ref_lu)
    temp_scale = float(mapping.temperature_scale)
    dx = float(mapping.lattice.dx_m)
    dt = float(mapping.lattice.dt_s)
    x2t = dx * dx / dt          # LU diffusivity -> SI
    v_scale = dx / dt           # LU speed -> SI
    alpha_nom = float(mapping.alpha_lu)
    nu_nom = float(mapping.nu_lu)
    gamma_nom = float(mapping.physical.gamma)
    cp_si = float(mapping.physical.cp_J_kgK) if hasattr(mapping.physical, "cp_J_kgK") else 1005.0
    rho0_si = float(getattr(mapping.physical, "rho0_kg_m3", 1.177))
    d_nom = max(alpha_nom, nu_nom)
    policy = g0.get("steps_policy", {})
    nx = int(g0.get("nx", 4))
    amp = g0.get("amplitudes", {})

    wn_list = list(g0["wavenumbers"])
    wn_by_label = {w["label"]: w for w in wn_list}
    acoustic_labels = list(g0.get("acoustic_wavenumbers", []))
    temps = [float(t) for t in g0["temperatures_K"]]
    ed = g0.get("equal_density_diagnostic", {}) or {}
    ed_temps = [float(t) for t in ed.get("temperatures_K", [])]
    ed_labels = list(ed.get("wavenumbers", []))

    rows: list[dict[str, Any]] = []
    problems: list[str] = []

    def theta_b_lu(temp_k: float) -> float | None:
        return None if abs(temp_k - theta_ref * temp_scale) < 1e-9 else temp_k / temp_scale

    def add_row(temp_k: float, path: str, wn: dict[str, Any], direction: str,
                fit_start_factor: float | None = None, tag: str = "") -> dict[str, Any]:
        ny = int(wn["ny"])
        mode = int(wn.get("mode", 1))
        k_lu = 2.0 * math.pi * mode / (ny if direction == "y" else ny)
        tb = theta_b_lu(temp_k)
        theta_b_val = theta_ref if tb is None else tb
        rho_b = rho_ref * theta_ref / theta_b_val if path == "isobaric" else rho_ref

        steps, interval, fit_start = _diffusive_steps(k_lu, d_nom, policy)
        if fit_start_factor is not None:
            fit_start = max(int(steps * fit_start_factor), 10)
        common = dict(nx=(ny if direction == "x" else nx), ny=(nx if direction == "x" else ny),
                      steps=steps, sample_interval=interval, fit_start=fit_start,
                      mode_index=mode, background_theta_lu=tb, background_path=path)
        r_th = measure_thermal_diffusion_direction(
            gas, direction, ThermalDiffusionSettings(amplitude=float(amp.get("thermal", 1e-5)), **common)
        )
        r_sh = measure_shear_wave_direction(
            gas, direction, ShearWaveSettings(amplitude=float(amp.get("shear", 1e-5)), **common)
        )
        row: dict[str, Any] = {
            "tag": tag, "T_K": temp_k, "background_path": path, "direction": direction,
            "k_label": wn["label"], "layer": wn.get("layer", ""), "ny": ny, "mode": mode,
            "k_lu": k_lu, "theta_b_lu": theta_b_val, "rho_b_lu": rho_b,
            "alpha_eff_lu": r_th["alpha_measured_lu"],
            "alpha_eff_m2_s": r_th["alpha_measured_lu"] * x2t,
            "nu_eff_lu": r_sh["nu_measured_lu"],
            "nu_eff_m2_s": r_sh["nu_measured_lu"] * x2t,
            "heat_flux_ratio_vs_ref_fourier": r_th["heat_flux_ratio_real"],
            "c_eff_lu": np.nan, "c_eff_m_s": np.nan, "gamma_eff": np.nan,
            "steps": steps, "fit_start": fit_start,
            "thermal_finite": not r_th["nan_detected"], "shear_finite": not r_sh["nan_detected"],
            "acoustic_finite": None,
        }
        rho_b_si = rho0_si * rho_b / rho_ref
        row["mu_eff_Pa_s"] = rho_b_si * row["nu_eff_m2_s"]
        row["k_eff_W_mK"] = rho_b_si * cp_si * row["alpha_eff_m2_s"]
        if wn["label"] in acoustic_labels and direction == "y" and fit_start_factor is None:
            c_nom = math.sqrt(gamma_nom * theta_b_val)
            a_steps, a_int, a_fit = _acoustic_steps(k_lu, c_nom, policy)
            r_ac = measure_acoustic_wave_direction(
                gas, direction,
                AcousticWaveSettings(
                    nx=nx, ny=ny, steps=a_steps, sample_interval=a_int, fit_start=a_fit,
                    mode_index=mode, amplitude=float(amp.get("acoustic", 1e-6)),
                    background_theta_lu=tb, background_path=path,
                ),
            )
            row["c_eff_lu"] = r_ac["sound_speed_measured_lu"]
            row["c_eff_m_s"] = r_ac["sound_speed_measured_lu"] * v_scale
            row["gamma_eff"] = r_ac["gamma_measured"]
            row["acoustic_finite"] = not r_ac["nan_detected"]
        if r_th["nan_detected"] or r_sh["nan_detected"]:
            problems.append(f"non-finite state at T={temp_k} {path} {wn['label']} {direction}")
        rows.append(row)
        print(
            "G0 T=%5.0fK %-13s %-8s %s alpha=%.5e nu=%.5e c=%s  [steps=%d]"
            % (temp_k, path, wn["label"], direction, row["alpha_eff_lu"], row["nu_eff_lu"],
               ("%.5f" % row["c_eff_lu"]) if np.isfinite(row["c_eff_lu"]) else "-", steps),
            flush=True,
        )
        return row

    # ---- main isobaric matrix (wall-normal y axis) ----
    for temp_k in temps:
        for wn in wn_list:
            add_row(temp_k, "isobaric", wn, "y")
    # ---- equal-density diagnostic subset ----
    for temp_k in ed_temps:
        for label in ed_labels:
            add_row(temp_k, "equal_density", wn_by_label[label], "y", tag="equal_density_diag")
    # ---- anisotropy diagnostic (x axis at 300 K, k1) ----
    aniso = g0.get("anisotropy_check", {}) or {}
    if aniso:
        wn_a = {"label": "k1_x", "ny": int(aniso.get("wavenumber_ny", 64)), "mode": 1, "layer": "anisotropy_diag"}
        add_row(float(aniso.get("temperature_K", 300.0)), "isobaric", wn_a, "x", tag="anisotropy")
    # ---- window-consistency pair (300 K, k1) ----
    wc = g0.get("window_consistency", {}) or {}
    wc_rows: list[dict[str, Any]] = []
    if wc:
        for factor in wc.get("fit_start_factors", [0.125, 0.25]):
            wc_rows.append(
                add_row(float(wc.get("temperature_K", 300.0)), "isobaric",
                        wn_by_label[wc.get("wavenumber", "k1")], "y",
                        fit_start_factor=float(factor), tag=f"window_consistency_{factor}")
            )

    # ---- gate evaluation (contract §5.3) ----
    def _find(temp_k: float, label: str, path: str = "isobaric") -> dict[str, Any]:
        for r in rows:
            if (abs(r["T_K"] - temp_k) < 1e-9 and r["k_label"] == label
                    and r["background_path"] == path and r["direction"] == "y" and r["tag"] == ""):
                return r
        raise KeyError((temp_k, label, path))

    # 300 K regression caliber: evaluated at the config's CALIBRATION wavenumber
    # (dx2p6 is a (tau,k) point-calibrated instrument — its documented validity
    # anchor is k1~0.098, NOT the k->0 limit; the low-k layer is archived as the
    # finite-k constitutive map with its own convergence row).
    low_labels = [w["label"] for w in wn_list if w.get("layer") == "low"]
    reg_label = str(g0.get("regression_wavenumber",
                           next(w["label"] for w in wn_list if w.get("layer") == "production")))
    r300 = _find(300.0, reg_label)
    reg_alpha = abs(r300["alpha_eff_lu"] / alpha_nom - 1.0)
    reg_nu = abs(r300["nu_eff_lu"] / nu_nom - 1.0)
    ac300 = next((r for r in rows if r["T_K"] == 300.0 and r["k_label"] == reg_label
                  and np.isfinite(r["c_eff_lu"]) and r["tag"] == ""), None)
    if ac300 is None:
        ac300 = next((r for r in rows if r["T_K"] == 300.0 and np.isfinite(r["c_eff_lu"])
                      and r["tag"] == ""), None)
    reg_c = abs(ac300["c_eff_lu"] / math.sqrt(gamma_nom * theta_ref) - 1.0) if ac300 else np.nan
    reg_gamma = abs(ac300["gamma_eff"] / gamma_nom - 1.0) if ac300 else np.nan

    conv_rows = []
    for temp_k in temps:
        a = _find(temp_k, low_labels[0])
        b = _find(temp_k, low_labels[1])
        conv_rows.append({
            "T_K": temp_k,
            "alpha_rel_diff": abs(a["alpha_eff_lu"] / b["alpha_eff_lu"] - 1.0),
            "nu_rel_diff": abs(a["nu_eff_lu"] / b["nu_eff_lu"] - 1.0),
        })
    conv_max = max(max(c["alpha_rel_diff"], c["nu_rel_diff"]) for c in conv_rows)

    wc_dev = np.nan
    if len(wc_rows) == 2:
        wc_dev = max(
            abs(wc_rows[0]["alpha_eff_lu"] / wc_rows[1]["alpha_eff_lu"] - 1.0),
            abs(wc_rows[0]["nu_eff_lu"] / wc_rows[1]["nu_eff_lu"] - 1.0),
        )

    finite_ok = not problems
    gate_rows = {
        "regression_300K_alpha_at_calibration_k": {
            "wavenumber": reg_label, "value": reg_alpha,
            "gate": gates["regression_300K_transport_rel"],
            "passed": bool(reg_alpha <= gates["regression_300K_transport_rel"])},
        "regression_300K_nu_at_calibration_k": {
            "wavenumber": reg_label, "value": reg_nu,
            "gate": gates["regression_300K_transport_rel"],
            "passed": bool(reg_nu <= gates["regression_300K_transport_rel"]),
            "caliber_note": "shear is a documented non-QoI on dx2p6 (Phase_3); "
                            "failure here scopes, it does not hard-fail"},
        "regression_300K_c_at_calibration_k": {
            "value": reg_c, "gate": gates["regression_300K_acoustic_rel"],
            "passed": bool(np.isfinite(reg_c) and reg_c <= gates["regression_300K_acoustic_rel"])},
        "regression_300K_gamma_at_calibration_k": {
            "value": reg_gamma, "gate": gates["regression_300K_acoustic_rel"],
            "passed": bool(np.isfinite(reg_gamma) and reg_gamma <= gates["regression_300K_acoustic_rel"])},
        "window_consistency": {"value": wc_dev, "gate": gates["window_consistency_rel"],
                               "passed": bool(np.isfinite(wc_dev) and wc_dev <= gates["window_consistency_rel"])},
        "lowk_convergence": {"value": conv_max, "gate": gates["lowk_convergence_rel"],
                             "passed": bool(conv_max <= gates["lowk_convergence_rel"]),
                             "caliber_note": "if failed: low-k layer reported as finite-k "
                                             "effective coefficients (contract §5.3); scopes, "
                                             "does not hard-fail"},
        "paths_archived": {"passed": bool(ed_temps), "note": "isobaric main + equal-density diagnostic archived"},
        "numerical_discipline": {"passed": finite_ok, "no_clipping": True, "no_floor": True,
                                 "no_positivity_repair": True, "problems": problems},
    }
    # hard rows protect the thermal/acoustic QoI chain the nonlinear program
    # consumes; the shear channel and the k->0 extrapolation scope the claim
    # instead of killing it (mirrors the frozen M3 scoped-boundary structure).
    hard_rows = ["regression_300K_alpha_at_calibration_k", "regression_300K_c_at_calibration_k",
                 "regression_300K_gamma_at_calibration_k", "window_consistency",
                 "paths_archived", "numerical_discipline"]
    scoped_rows = ["regression_300K_nu_at_calibration_k", "lowk_convergence"]
    all_hard = all(gate_rows[k]["passed"] for k in hard_rows)
    scoped_failures = [k for k in scoped_rows if not gate_rows[k]["passed"]]
    if all_hard and not scoped_failures:
        verdict = "PASSED"
    elif all_hard:
        verdict = "SCOPED_CANDIDATE"  # scoped upgrade is a user decision (D0-7)
    else:
        verdict = "FAILED"

    # ---- outputs ----
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = Path(output_root) if output_root else Path(cfg["output"]["results_root"])
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    fieldnames = list(rows[0].keys())
    with (out_dir / "property_table.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    table_digest = hashlib.sha256(
        json.dumps([[r[k] for k in fieldnames] for r in rows], default=str).encode()
    ).hexdigest()[:12]
    summary = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "code_commit": _git_commit(),
        "phase5_contract_version": PHASE5_CONTRACT_VERSION,
        "work_package": "WP2",
        "gate_id": GATE_ID,
        "model_route": "ROUTE_B_MAIN",
        "config_path": str(config_path),
        "config_digest": _sha256_file(config_path)[:12],
        "gas_config_path": str(gas_config_path),
        "gas_config_digest": _sha256_file(gas_config_path)[:12],
        "mapping": {"dx_m": dx, "dt_s": dt, "theta_ref_lu": theta_ref,
                    "alpha_lu_nominal": alpha_nom, "nu_lu_nominal": nu_nom, "gamma": gamma_nom},
        "background_paths": ["isobaric", "equal_density(diagnostic)"],
        "temperatures_K": temps,
        "n_measurement_rows": len(rows),
        "property_table_digest": table_digest,
        "gate_status": verdict,
        "scoped_limitations": scoped_failures,
        "regression_wavenumber": reg_label,
        "no_clipping": True, "no_floor": True, "no_positivity_repair": True,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    (out_dir / "gate_evaluation.json").write_text(
        json.dumps({"gate_id": GATE_ID, "verdict": verdict, "rows": gate_rows,
                    "lowk_convergence_by_T": conv_rows}, indent=1, default=float),
        encoding="utf-8",
    )
    report = [
        f"# G0-B run {run_id}", "",
        f"- verdict: **{verdict}** (script-emittable only; scoped upgrades are user decisions)",
        f"- gas config: {gas_config_path} (digest {summary['gas_config_digest']})",
        f"- rows: {len(rows)}; table digest {table_digest}; commit {summary['code_commit'][:12]}",
        "", "## Gate rows (contract §5.3)", "",
    ]
    for name, row in gate_rows.items():
        val = row.get("value")
        val_s = ("%.4e" % val) if isinstance(val, float) and np.isfinite(val) else "-"
        report.append(f"- {name}: value={val_s} gate={row.get('gate', '-')} passed={row['passed']}")
    (out_dir / "run_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"G0 verdict={verdict}  rows={len(rows)}  -> {out_dir}", flush=True)
    return {"verdict": verdict, "out_dir": str(out_dir), "summary": summary,
            "gate_rows": gate_rows, "rows": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase_5 G0-B effective-property runner")
    parser.add_argument("--config", type=Path,
                        default=Path("configs/phase5/g0_effective_properties/g0_10k_dx2p6.yaml"))
    parser.add_argument("--output-root", type=Path, default=None)
    args = parser.parse_args()
    result = run_g0(args.config, args.output_root)
    return 0 if result["verdict"] in {"PASSED", "SCOPED_CANDIDATE"} else 1


if __name__ == "__main__":
    sys.exit(main())
