"""P3-6 Level A dynamic-admittance script machinery tests.

The committed 10 kHz dx2p6 run (~5 min) is the authoritative measurement and is recorded
in ``Phase3_STATUS.md`` §3 with its physics-core digest; these tests exercise the same code
path on a tiny domain at a synthetic high frequency (a few dozen steps per period), so they
assert machinery -- finiteness, gas-side non-degeneracy, exact wall pinning, contract §9
HDF5 metadata, digest reproducibility -- and deliberately do NOT assert the M3 gate value
(the physics is meaningless at the test frequency).
"""

from __future__ import annotations

import json
from pathlib import Path

import h5py
import numpy as np
import pytest

from core.unit_mapping import create_unit_mapping
from scripts.phase2_m2_verification import load_config
from scripts.phase3_levela_admittance import run_levela_admittance


GAS_CONFIG = Path("configs/gas_air_10k_d2q37_physical_timestep.yaml")


def _write_tiny_config(tmp_path: Path, *, steps_per_period: int = 32, periods: int = 2) -> Path:
    mapping = create_unit_mapping(load_config(GAS_CONFIG))
    f_test = 1.0 / (steps_per_period * float(mapping.lattice.dt_s))
    config = f"""
case:
  name: phase3_levela_admittance_machinery_test
  phase: Phase_3
  level: A
inheritance:
  gas_config_path: {GAS_CONFIG.as_posix()}
physical:
  frequency_Hz: {f_test!r}
  T0_K: 300.0
  wall_temperature_hat_K: 0.354
  kg_W_mK: 0.0263
  alpha0_m2_s: 2.2233775895e-5
level_a:
  wall_bc: thermal_grad
  grad_extrap: linear
  rho_wall_policy: pressure_preserving
numerics:
  nx: 6
  ny: 12
  periods: {periods}
gates:
  admittance_amplitude_relative_error: 0.05
  admittance_phase_error_deg: 5.0
"""
    path = tmp_path / "levela_admittance_test.yaml"
    path.write_text(config, encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def payload_and_dir(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("levela_admittance")
    config_path = _write_tiny_config(tmp_path)
    out_root = tmp_path / "results"
    payload = run_levela_admittance(config_path=config_path, output_root=out_root)
    return payload, out_root / payload["run_id"], config_path, out_root


def test_levela_admittance_is_finite_and_nondegenerate(payload_and_dir):
    payload, _out_dir, _cfg, _root = payload_and_dir
    assert payload["status"] == "PASSED"  # machinery health, not the M3 gate
    assert payload["stability_flags"]["no_nan"]
    # Gas-side non-degeneracy: the fitted near-wall flux response comes from the free
    # interior gas row (row 1), not an echo of the imposed wall value. The old clamp
    # wall-row artifact was ~1e-5 W/m^2; a real response to a ~0.35 K oscillation is
    # orders of magnitude larger even at the absurd test frequency.
    assert payload["q_g_hat_W_m2"]["abs"] > 0.1
    assert np.isfinite(payload["Y_measured"]["amp_rel_err"])
    assert payload["m3_gate"] in {"PASSED", "PHASE_PASS_AMPLITUDE_BOUNDARY", "NOT_PASSED"}


def test_grad_wall_pin_is_exact_at_reconstruction_instant():
    # The end-of-step readback in the script payload includes the solver's global
    # acoustic-phase corrections (small at production smoothness, large at the absurd
    # test frequency), so exactness is asserted here at the callback instant instead:
    # reconstruct row 0 on a perturbed state and recover theta directly.
    from boundary.wall_thermal_grad import apply_bottom_grad_wall_inplace
    from core.solver import GasSolver2D

    gas = load_config(GAS_CONFIG)
    gas["numerics"] = {**gas.get("numerics", {}), "nx": 6, "ny": 12}
    solver = GasSolver2D(gas)
    theta0 = float(solver.mapping.theta_ref_lu)
    solver.initialize_from_macro(
        solver.mapping.lattice.rho_ref_lu,
        np.zeros((solver.ny, solver.nx, 2), dtype=float),
        theta0 * (1.0 + 0.01 * np.cos(np.arange(solver.ny) / 3.0))[:, None] * np.ones((1, solver.nx)),
    )
    theta_w = theta0 * 1.005
    apply_bottom_grad_wall_inplace(solver, theta_w, extrap="linear")
    recovered = solver.get_temperature_lu()[0]
    assert np.max(np.abs(recovered - theta_w)) < 1.0e-12 * theta0


def test_levela_admittance_pin_readback_and_mass_are_recorded(payload_and_dir):
    payload, _out_dir, _cfg, _root = payload_and_dir
    pin = payload["theta_wall_pin_check"]
    assert np.isfinite(pin["amp_rel_err"]) and np.isfinite(pin["phase_deg_err"])
    # The pressure-preserving wall row legitimately exchanges mass as theta_w oscillates
    # (rho_w is prescribed); this is a does-not-explode sanity bound, not conservation.
    assert payload["mass_relative_drift"] < 1.0e-2


def test_levela_admittance_writes_contract_hdf5(payload_and_dir):
    payload, out_dir, _cfg, _root = payload_and_dir
    h5_path = out_dir / payload["artifacts"]["hdf5"]
    assert h5_path.exists()
    with h5py.File(h5_path, "r") as h5:
        meta = dict(h5["meta"].attrs)
        assert meta["phase"] == "Phase_3"
        assert meta["level"] == "A"
        assert meta["wall_bc"] == "thermal_grad"
        assert meta["complex_convention"] == "x(t)=Re[x_hat exp(i Omega t)]"
        for key in ("tau21", "tau22", "tau32", "heat_flux_sign_convention", "wall_normal_convention"):
            assert key in meta, f"contract §9 metadata key missing: {key}"
        n = payload["n_steps"] + 1
        assert h5["time"]["t_si"].shape == (n,)
        assert h5["wall"]["q_wall_extracted_si"].shape == (n,)
        assert h5["wall"]["theta_wall_lu"].shape == (n,)
        q_hat = h5["harmonic"]["q_g_hat_si"]
        assert q_hat.attrs["layout"] == "real_imag"
        assert np.allclose(
            np.asarray(q_hat),
            [payload["q_g_hat_W_m2"]["real"], payload["q_g_hat_W_m2"]["imag"]],
        )


def test_levela_admittance_digest_is_reproducible(payload_and_dir):
    payload, out_dir, config_path, out_root = payload_and_dir
    rerun = run_levela_admittance(config_path=config_path, output_root=out_root)
    assert rerun["summary_digest"] == payload["summary_digest"]
    on_disk = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    assert on_disk["summary_digest"] == payload["summary_digest"]
    assert "artifacts" in on_disk["summary_digest_scope"]  # artifacts excluded from digest
