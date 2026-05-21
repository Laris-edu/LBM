"""Generate Phase 1 reference CSV datasets."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from .continuum_1d_freq import solve_level_A_frequency, solve_level_B_frequency, solve_level_C_frequency
from .continuum_1d_time import run_level_C_step
from .constants import default_params


def _write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                fieldnames.append(key)
                seen.add(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def generate_baseline(output_dir: str | Path = "results/phase1_reference") -> Path:
    params = default_params()
    rows = [
        solve_level_A_frequency(10_000.0, 1.0, params=params).to_flat_dict(),
        solve_level_B_frequency(10_000.0, 1000.0, params=params).to_flat_dict(),
        solve_level_C_frequency(10_000.0, 1000.0, params.C_A, params=params).to_flat_dict(),
    ]
    path = Path(output_dir) / "baseline_10k.csv"
    _write_rows(path, rows)
    return path


def generate_frequency_sweep(output_dir: str | Path = "results/phase1_reference") -> Path:
    params = default_params()
    freqs = np.logspace(3.0, 5.0, 20)
    rows = [
        solve_level_C_frequency(float(f), 1000.0, params.C_A, params=params).to_flat_dict()
        for f in freqs
    ]
    path = Path(output_dir) / "frequency_sweep_levelC.csv"
    _write_rows(path, rows)
    return path


def generate_CA_sweep(output_dir: str | Path = "results/phase1_reference") -> Path:
    params = default_params()
    freqs = np.logspace(3.0, 5.0, 20)
    C_As = [1.0e-5, 1.0e-4, 7.0e-4, 1.0e-3, 1.0e-2]
    rows = []
    for C_A in C_As:
        for f_hz in freqs:
            rows.append(
                solve_level_C_frequency(float(f_hz), 1000.0, C_A, params=params).to_flat_dict()
            )
    path = Path(output_dir) / "CA_sweep_levelC.csv"
    _write_rows(path, rows)
    return path


def generate_power_sweep(output_dir: str | Path = "results/phase1_reference") -> Path:
    params = default_params()
    powers = np.logspace(2.0, 4.0, 10)
    rows = [
        solve_level_C_frequency(10_000.0, float(P), params.C_A, params=params).to_flat_dict()
        for P in powers
    ]
    path = Path(output_dir) / "power_sweep_levelC.csv"
    _write_rows(path, rows)
    return path


def generate_step_summaries(output_dir: str | Path = "results/phase1_reference") -> Path:
    rows = []
    for C_A in [1.0e-5, 7.0e-4, 1.0e-2]:
        result = run_level_C_step(C_A=C_A)
        rows.append(
            {
                "case_name": result.case_name,
                "C_A": C_A,
                "P_bar": 1000.0,
                "t_end": float(result.t[-1]),
                "T_s_final": float(result.T_s[-1]),
                "q_g_final": float(result.q_g[-1]),
                "energy_residual_rms": float(np.sqrt(np.mean(result.energy_residual**2))),
                "tau_s": float(result.metadata["tau_s"]),
                "time_model": str(result.metadata["time_model"]),
            }
        )
    path = Path(output_dir) / "step_summary_levelC.csv"
    _write_rows(path, rows)
    return path


def generate_step_time_series(output_dir: str | Path = "results/phase1_reference") -> list[Path]:
    paths: list[Path] = []
    for C_A in [1.0e-5, 7.0e-4, 1.0e-2]:
        result = run_level_C_step(C_A=C_A)
        rows = []
        for i in range(result.t.size):
            rows.append(
                {
                    "case_name": result.case_name,
                    "C_A": C_A,
                    "t": float(result.t[i]),
                    "P_in": float(result.P_in[i]),
                    "T_s": float(result.T_s[i]),
                    "q_g": float(result.q_g[i]),
                    "p_probe_y_8deltaT": float(result.p_probe[i]),
                    "energy_residual": float(result.energy_residual[i]),
                    "time_model": str(result.metadata["time_model"]),
                    "pressure_model": str(result.metadata["pressure_model"]),
                }
            )
        path = Path(output_dir) / f"step_transient_CA_{C_A:g}.csv"
        _write_rows(path, rows)
        paths.append(path)
    return paths


def generate_all(output_dir: str | Path = "results/phase1_reference") -> list[Path]:
    paths = [
        generate_baseline(output_dir),
        generate_frequency_sweep(output_dir),
        generate_CA_sweep(output_dir),
        generate_power_sweep(output_dir),
        generate_step_summaries(output_dir),
    ]
    paths.extend(generate_step_time_series(output_dir))
    return paths


if __name__ == "__main__":
    for generated in generate_all():
        print(generated)
