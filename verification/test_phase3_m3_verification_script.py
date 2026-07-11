"""P3-6 M3 verification script machinery tests (contract §9 HDF5 + digest stability).

The authoritative 10 kHz dx2p6 measurement is the committed run recorded in
``Phase3_STATUS.md`` §3 (physics-core digest ``26be2fde...``); these tests drive the same
``run_m3_verification`` code path on a tiny domain at a synthetic high frequency, so they
assert machinery (HDF5 schema, digest reproducibility, audit plumbing) and deliberately do
NOT assert the M3 gate value.
"""

from __future__ import annotations

import json
from pathlib import Path

import h5py
import numpy as np
import pytest

from core.unit_mapping import create_unit_mapping
from scripts.phase2_m2_verification import load_config
from scripts.phase3_m3_verification import m3_exit_code, run_m3_verification


GAS_CONFIG = Path("configs/gas_air_10k_d2q37_physical_timestep.yaml")


def _write_tiny_config(tmp_path: Path, *, steps_per_period: int = 32, periods: int = 2) -> Path:
    mapping = create_unit_mapping(load_config(GAS_CONFIG))
    f_test = 1.0 / (steps_per_period * float(mapping.lattice.dt_s))
    config = f"""
case:
  name: phase3_m3_verification_machinery_test
  phase: Phase_3
  level: C
inheritance:
  gas_config_path: {GAS_CONFIG.as_posix()}
physical:
  frequency_Hz: {f_test!r}
  T0_K: 300.0
  C_A_J_m2K: 7.0e-4
  P_mean_W_m2: 0.0
  P_hat_W_m2:
    real: 1000.0
    imag: 0.0
  kg_W_mK: 0.0263
  alpha0_m2_s: 2.2233775895e-5
level_c:
  wall_bc: thermal_grad
  q_feedback_relax: 0.02
  grad_extrap: linear
  coupling_scheme: heun_picard1
  rho_wall_policy: pressure_preserving
  gas_flux_factor: 2.0
numerics:
  nx: 6
  ny: 12
  periods: {periods}
  probe:
    y: 1
    x: 3
gates:
  T_s_hat_amplitude_relative_error: 0.05
  T_s_hat_phase_error_deg: 5.0
  wall_temperature_error_K: 1.0e-2
  energy_residual_relative: 1.0e-2
"""
    path = tmp_path / "m3_machinery_test.yaml"
    path.write_text(config, encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def payload_and_dir(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("m3_verification")
    config_path = _write_tiny_config(tmp_path)
    out_root = tmp_path / "results"
    payload = run_m3_verification(config_path=config_path, output_root=out_root)
    return payload, out_root / payload["run_id"], config_path, out_root


def test_m3_script_is_finite_and_audited(payload_and_dir):
    payload, _out_dir, _cfg, _root = payload_and_dir
    assert payload["stability_flags"]["no_nan"]
    assert payload["stability_flags"]["energy_audit_passed"]
    assert payload["m3_gate"] in {"PASSED", "PHASE_PASS_AMPLITUDE_BOUNDARY", "NOT_PASSED"}
    assert np.isfinite(payload["T_s_hat"]["amp_rel_err"])
    assert payload["wall_temperature"]["passed"]


def test_m3_exit_code_rejects_not_passed():
    assert m3_exit_code("PASSED") == 0
    assert m3_exit_code("PHASE_PASS_AMPLITUDE_BOUNDARY") == 0
    assert m3_exit_code("NOT_PASSED") == 1


def test_m3_script_writes_contract_hdf5(payload_and_dir):
    payload, out_dir, _cfg, _root = payload_and_dir
    h5_path = out_dir / payload["artifacts"]["hdf5"]
    assert h5_path.exists()
    with h5py.File(h5_path, "r") as h5:
        meta = dict(h5["meta"].attrs)
        assert meta["phase"] == "Phase_3"
        assert meta["level"] == "C"
        assert meta["wall_bc"] == "thermal_grad"
        assert meta["coupling_scheme"] == "heun_picard1"
        for key in (
            "tau21",
            "tau22",
            "tau32",
            "heat_flux_sign_convention",
            "wall_normal_convention",
            "complex_convention",
            "C_A_si",
            "P_in_definition",
        ):
            assert key in meta, f"contract §9 metadata key missing: {key}"
        n = payload["n_steps"] + 1
        assert h5["time"]["t_si"].shape == (n,)
        for name in ("T_s_si", "P_in_si", "q_g_one_sided_si", "dT_s_dt_si", "energy_residual_si"):
            assert h5["film"][name].shape == (n,), f"/film/{name} shape mismatch"
        assert h5["wall"]["theta_wall_lu"].shape == (n,)
        assert h5["probes"]["pressure_si"].shape == (n, 1)
        assert h5["harmonic"]["T_s_hat_si"].attrs["layout"] == "real_imag"
        assert "p_hat_si" in h5["harmonic"]
        ts_hat = np.asarray(h5["harmonic"]["T_s_hat_si"])
        measured = complex(ts_hat[0], ts_hat[1])
        assert abs(measured) == pytest.approx(payload["T_s_hat"]["abs"], rel=1e-12)


def test_m3_script_digest_excludes_artifacts_and_reproduces(payload_and_dir):
    payload, out_dir, config_path, out_root = payload_and_dir
    on_disk = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    assert "artifacts" in on_disk["summary_digest_scope"]
    rerun = run_m3_verification(config_path=config_path, output_root=out_root)
    assert rerun["summary_digest"] == payload["summary_digest"]
