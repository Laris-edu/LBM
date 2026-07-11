from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import numpy as np

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - import-time dependency guard
    raise RuntimeError("PyYAML is required: install PyYAML==6.0.3") from exc


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "configs" / "phase1_reference_manifest.yaml"


def load_manifest() -> dict:
    with MANIFEST.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(rel_path: str) -> list[dict[str, str]]:
    with (ROOT / rel_path).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def header_columns(rel_path: str) -> int:
    with (ROOT / rel_path).open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        return len(next(reader))


def as_float(rows: list[dict[str, str]], key: str) -> np.ndarray:
    return np.asarray([float(row[key]) for row in rows], dtype=float)


def as_complex(rows: list[dict[str, str]], prefix: str) -> np.ndarray:
    return as_float(rows, f"{prefix}_real") + 1j * as_float(rows, f"{prefix}_imag")


def file_entries() -> list[dict]:
    return load_manifest()["files"]


def entry_by_name(name: str) -> dict:
    for entry in file_entries():
        if Path(entry["path"]).name == name:
            return entry
    raise AssertionError(f"missing manifest entry: {name}")


def rows_by_name(name: str) -> list[dict[str, str]]:
    return read_rows(entry_by_name(name)["path"])


def test_phase1_reference_files_exist_rows_columns_and_hashes():
    manifest = load_manifest()
    assert manifest["manifest_format"] == "yaml"
    assert manifest["hash_policy"] == "sha256_of_raw_file_bytes_no_newline_normalization"
    assert manifest["path_policy"] == "repository_relative_paths"
    assert "PyYAML==6.0.3" in manifest["requires"]

    for entry in manifest["files"]:
        rel_path = entry["path"]
        assert not Path(rel_path).is_absolute(), rel_path
        path = ROOT / rel_path
        assert path.exists(), rel_path
        rows = read_rows(rel_path)
        assert len(rows) == entry["rows"], rel_path
        assert header_columns(rel_path) == entry["columns"], rel_path
        assert sha256(path) == entry["sha256"], rel_path


def test_manifest_top_level_contract():
    manifest = load_manifest()
    assert manifest["reference_version"] == "phase1_reference_v1.1"
    assert manifest["m1_status"] == "passed"
    assert manifest["decision"] == "proceed_to_phase_2"
    assert manifest["risk_status"] == "GO-RISK"
    assert len(manifest["files"]) == 8


def test_manifest_conventions_are_locked():
    manifest = load_manifest()
    conventions = manifest["conventions"]
    assert "Re[x_hat exp(i Omega t)]" in conventions["time_harmonic"]
    assert "sqrt(2)" in conventions["amplitude"]
    assert "20e-6" in conventions["spl"]
    assert manifest["baseline_parameters"]["probe_primary"] == "y=8*delta_T"


def test_baseline_levels_and_energy_residual():
    rows = rows_by_name("baseline_10k.csv")
    assert {row["level"] for row in rows} == {"A", "B", "C"}
    assert np.max(np.abs(as_float(rows, "energy_residual_rel"))) < 1e-12
    assert np.max(np.abs(as_complex(rows, "u_hat_y_0"))) < 1e-14


def test_frequency_sweep_contract():
    rows = rows_by_name("frequency_sweep_levelC.csv")
    f_hz = as_float(rows, "f_Hz")
    assert len(rows) == 20
    assert all(row["level"] == "C" for row in rows)
    assert np.isclose(np.min(f_hz), 1e3)
    assert np.isclose(np.max(f_hz), 1e5)
    assert len(set(as_float(rows, "C_A"))) == 1
    assert np.max(np.abs(as_float(rows, "energy_residual_rel"))) < 1e-12


def test_power_sweep_linearity_contract():
    rows = rows_by_name("power_sweep_levelC.csv")
    P = np.hypot(as_float(rows, "P_hat_real"), as_float(rows, "P_hat_imag"))
    p = as_complex(rows, "p_hat_y_8")
    assert len(rows) == 10
    assert np.isclose(np.min(P), 100.0)
    assert np.isclose(np.max(P), 10000.0)
    gain = np.abs(p) / P
    deviation = gain / gain[0] - 1.0
    assert np.max(np.abs(deviation)) < 1e-10
    assert np.max(np.abs(as_float(rows, "energy_residual_rel"))) < 1e-12


def test_CA_sweep_contract_and_grid_label():
    entry = entry_by_name("CA_sweep_levelC.csv")
    assert entry["grid_type"] == "baseline_inserted_grid"
    rows = rows_by_name("CA_sweep_levelC.csv")
    C_A = as_float(rows, "C_A")
    expected = np.asarray([1e-5, 1e-4, 7e-4, 1e-3, 1e-2])
    actual = np.asarray(sorted(set(np.round(C_A, 12))))
    assert np.allclose(actual, np.round(expected, 12))
    for value in expected:
        assert np.sum(np.isclose(C_A, value)) == 20
    assert np.max(np.abs(as_float(rows, "energy_residual_rel"))) < 1e-12


def test_step_summary_is_labeled_as_thermal_network_proxy():
    entry = entry_by_name("step_summary_levelC.csv")
    assert entry["proxy_type"] == "first_order_effective_thermal_network"
    rows = rows_by_name("step_summary_levelC.csv")
    assert all(row["time_model"] == "first_order_effective_thermal_network" for row in rows)


def test_step_transient_is_labeled_as_pressure_proxy():
    for name in [
        "step_transient_CA_1e-05.csv",
        "step_transient_CA_0.0007.csv",
        "step_transient_CA_0.01.csv",
    ]:
        entry = entry_by_name(name)
        assert entry["proxy_type"] == "pressure_small_signal_derivative_proxy"
        rows = rows_by_name(name)
        assert all(row["time_model"] == "first_order_effective_thermal_network" for row in rows)
        assert all(row["pressure_model"] == "10k_small_signal_derivative_proxy" for row in rows)
