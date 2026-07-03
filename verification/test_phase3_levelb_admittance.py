"""P3-6 Level B dynamic-flux-response script machinery tests.

Same philosophy as ``test_phase3_levela_admittance.py``: the committed 10 kHz dx2p6 run is
the authoritative measurement (recorded in ``Phase3_STATUS.md`` §3 with its physics-core
digest); these tests exercise the code path on a tiny domain at a synthetic high frequency
and assert machinery only -- the flux-to-Dirichlet stencil identity, finiteness, response
non-degeneracy, contract §9 HDF5 metadata, digest reproducibility -- never the M3 gate.
"""

from __future__ import annotations

import json
from pathlib import Path

import h5py
import numpy as np
import pytest

from boundary.wall_thermal_grad import neumann_theta_wall_lu
from core.macroscopic import recover_macro
from core.solver import GasSolver2D
from core.unit_mapping import create_unit_mapping
from scripts.phase2_m2_verification import load_config
from scripts.phase3_levelb_admittance import run_levelb_admittance


GAS_CONFIG = Path("configs/gas_air_10k_d2q37_physical_timestep.yaml")


def _write_tiny_config(tmp_path: Path, *, steps_per_period: int = 32, periods: int = 2) -> Path:
    mapping = create_unit_mapping(load_config(GAS_CONFIG))
    f_test = 1.0 / (steps_per_period * float(mapping.lattice.dt_s))
    config = f"""
case:
  name: phase3_levelb_admittance_machinery_test
  phase: Phase_3
  level: B
inheritance:
  gas_config_path: {GAS_CONFIG.as_posix()}
physical:
  frequency_Hz: {f_test!r}
  T0_K: 300.0
  q_wall_hat_W_m2:
    real: 500.0
    imag: 0.0
  q_wall_mean_W_m2: 0.0
  kg_W_mK: 0.0263
  alpha0_m2_s: 2.2233775895e-5
level_b:
  wall_bc: thermal_grad
  controller: moment_flux_servo
  grad_extrap: linear
  theta_relax: 0.02   # production servo gain (large gains are Nyquist-unstable; see config comment)
  q_measurement_filter: 0.02
  rho_wall_policy: pressure_preserving
numerics:
  nx: 6
  ny: 12
  periods: {periods}
gates:
  impedance_amplitude_relative_error: 0.05
  impedance_phase_error_deg: 5.0
"""
    path = tmp_path / "levelb_admittance_test.yaml"
    path.write_text(config, encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def payload_and_dir(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("levelb_admittance")
    config_path = _write_tiny_config(tmp_path)
    out_root = tmp_path / "results"
    payload = run_levelb_admittance(config_path=config_path, output_root=out_root)
    return payload, out_root / payload["run_id"], config_path, out_root


def test_neumann_flux_to_dirichlet_stencil_is_exact():
    # neumann_theta_wall_lu is a kept-but-REFUTED controller helper (FD-gradient pinning
    # over-delivers the moment flux ~2.5x; the committed script uses the moment servo).
    # As a formula it must still satisfy the one-sided second-order identity
    # (-3 T_0 + 4 T_1 - T_2) / (2 dx) = -q / k exactly on the recovered interior rows.
    gas = load_config(GAS_CONFIG)
    gas["numerics"] = {**gas.get("numerics", {}), "nx": 6, "ny": 12}
    solver = GasSolver2D(gas)
    theta0 = float(solver.mapping.theta_ref_lu)
    profile = theta0 * (1.0 + 0.002 * np.linspace(0.0, 1.0, solver.ny))[:, None] * np.ones((1, solver.nx))
    solver.initialize_from_macro(
        solver.mapping.lattice.rho_ref_lu,
        np.zeros((solver.ny, solver.nx, 2), dtype=float),
        profile,
    )
    q_si = 750.0
    kg = 0.0263
    theta_w = neumann_theta_wall_lu(solver, solver.f, solver.g, q_si, kg_si=kg, flux_stencil="second_order")
    scale = float(solver.mapping.temperature_scale)
    dx = float(solver.mapping.lattice.dx_m)

    def row_T(j):
        m = recover_macro(
            solver.f[j:j + 1], solver.g[j:j + 1],
            D=solver.mapping.lattice.D, S=solver.mapping.lattice.S, lattice=solver.lattice,
        )
        return float(np.mean(m.theta)) * scale

    T0_w = theta_w * scale
    grad = (-3.0 * T0_w + 4.0 * row_T(1) - row_T(2)) / (2.0 * dx)
    assert grad == pytest.approx(-q_si / kg, rel=1.0e-12)
    # First-order variant: T_0 = T_1 + dx q / k.
    theta_w1 = neumann_theta_wall_lu(solver, solver.f, solver.g, q_si, kg_si=kg, flux_stencil="first_order")
    assert theta_w1 * scale == pytest.approx(row_T(1) + dx * q_si / kg, rel=1.0e-12)


def test_levelb_admittance_is_finite_and_nondegenerate(payload_and_dir):
    payload, _out_dir, _cfg, _root = payload_and_dir
    assert payload["status"] == "PASSED"  # machinery health, not the M3 gate
    assert payload["stability_flags"]["no_nan"]
    # The wall temperature must actually respond to the imposed flux oscillation
    # (T_wall_hat is the servo-driven wall value shaped by the free interior response,
    # not an echo of a prescribed temperature).
    assert payload["T_wall_hat_vs_prescribed"]["abs"] > 0.0
    assert np.isfinite(payload["T_wall_hat_vs_prescribed"]["amp_rel_err"])
    assert np.isfinite(payload["q_tracking_hat"]["amp_rel_err"])
    assert "BY CONSTRUCTION" in payload["q_tracking_hat"]["note"]  # control target, not a physics gate
    assert payload["m3_gate"] in {"PASSED", "PHASE_PASS_AMPLITUDE_BOUNDARY", "NOT_PASSED"}
    # Does-not-explode sanity (the prescribed-flux wall legitimately exchanges mass).
    assert payload["mass_relative_drift"] < 1.0e-2


def test_levelb_admittance_writes_contract_hdf5(payload_and_dir):
    payload, out_dir, _cfg, _root = payload_and_dir
    h5_path = out_dir / payload["artifacts"]["hdf5"]
    assert h5_path.exists()
    with h5py.File(h5_path, "r") as h5:
        meta = dict(h5["meta"].attrs)
        assert meta["phase"] == "Phase_3"
        assert meta["level"] == "B"
        assert meta["wall_bc"] == "thermal_grad"
        assert meta["controller"] == "moment_flux_servo"
        for key in ("tau21", "tau22", "tau32", "heat_flux_sign_convention", "wall_normal_convention"):
            assert key in meta, f"contract §9 metadata key missing: {key}"
        n = payload["n_steps"] + 1
        assert h5["time"]["t_si"].shape == (n,)
        # Contract §9 Level B: both the imposed and the extracted wall flux series.
        assert h5["wall"]["q_wall_imposed_si"].shape == (n,)
        assert h5["wall"]["q_wall_extracted_si"].shape == (n,)
        assert h5["harmonic"]["T_wall_hat_si"].attrs["layout"] == "real_imag"


def test_levelb_admittance_digest_is_reproducible(payload_and_dir):
    payload, out_dir, config_path, out_root = payload_and_dir
    rerun = run_levelb_admittance(config_path=config_path, output_root=out_root)
    assert rerun["summary_digest"] == payload["summary_digest"]
    on_disk = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    assert on_disk["summary_digest"] == payload["summary_digest"]
    assert "artifacts" in on_disk["summary_digest_scope"]
