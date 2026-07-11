import h5py
import numpy as np

from core.solver import GasSolver2D
from core.unit_mapping import d2q37_physical_timestep_config, physical_timestep_config
from scripts.phase2_m2_verification import (
    load_config,
    measurement_statuses_passed,
    resolved_config_sha256,
)


def test_effective_config_digest_changes_when_an_included_file_changes(tmp_path):
    parent = tmp_path / "parent.yaml"
    child = tmp_path / "child.yaml"
    parent.write_text("physical:\n  c0_m_s: 347.0\n", encoding="utf-8")
    child.write_text("include: parent.yaml\ncase:\n  name: digest-test\n", encoding="utf-8")

    first = resolved_config_sha256(load_config(child))
    parent.write_text("physical:\n  c0_m_s: 348.0\n", encoding="utf-8")
    second = resolved_config_sha256(load_config(child))

    assert first != second


def test_measurement_gate_requires_every_physical_status_to_pass():
    passed = ({"p2_04_status": "PASSED"}, "p2_04_status")
    failed = ({"p2_05_status": "FAILED"}, "p2_05_status")

    assert measurement_statuses_passed(passed)
    assert not measurement_statuses_passed(passed, failed)


def test_hdf5_metadata_minimum_schema(tmp_path):
    config = physical_timestep_config()
    config["case"] = {"name": "metadata_schema_test"}
    config["numerics"] = {"nx": 4, "ny": 3}
    solver = GasSolver2D(config)
    solver.initialize_from_macro(1.0, np.zeros(2), solver.mapping.theta_ref_lu)
    output = tmp_path / "phase2.h5"
    solver.save_hdf5(str(output))

    required_root = {
        "schema_name",
        "schema_version",
        "producer",
        "phase2_instruction_version",
        "validation_level",
        "case_name",
        "phase",
        "code_git_commit",
        "created_at",
        "pass_fail",
        "clipping_used",
    }
    required_lattice = {
        "velocity_set",
        "Q",
        "D",
        "S",
        "array_layout",
        "theta_q_lu",
        "theta_ref_lu",
        "theta_transport_lu",
        "dx_m",
        "dt_s",
    }
    required_collision = {
        "model",
        "bulk_viscosity_policy",
        "nu_b_lu",
        "tau21",
        "tau22",
        "tau32",
        "central_moment_closure",
        "trace_bulk_policy",
        "trace_bulk_scale",
        "trace_bulk_calibration_id",
        "dispersion_correction_enabled",
        "dispersion_correction_low_laplacian",
        "dispersion_correction_high_laplacian",
        "regularized_shear_xy_factor",
        "regularized_shear_normal_factor",
        "regularized_shear_xy_dispersion_target",
        "regularized_shear_normal_dispersion_target",
        "regularized_heat_flux_factor_policy",
        "regularized_heat_flux_factor",
        "regularized_heat_flux_dispersion_target",
        "regularized_heat_flux_diagonal_low_mode_target",
        "regularized_heat_flux_f_fraction",
        "heat_flux_retention_policy",
        "heat_flux_retention_curve_type",
        "heat_flux_retention_curve_coefficients",
        "conductive_heat_flux_moment_factor_policy",
        "conductive_heat_flux_moment_factor",
        "conductive_heat_flux_dispersion_target",
        "conductive_heat_flux_diagonal_low_mode_target",
        "conductive_heat_flux_galilean_correction_factor",
        "acoustic_phase_correction_enabled",
        "acoustic_phase_correction_low_laplacian",
        "acoustic_phase_diagonal_low_mode_factor",
        "acoustic_phase_high_mode_policy",
        "acoustic_phase_high_mode_factor",
        "acoustic_phase_high_mode_diagonal_factor",
        "high_order_relaxation",
        "energy_closure_definition",
    }
    required_results = {
        "measured_nu",
        "measured_alpha",
        "measured_Pr",
        "measured_gamma",
        "measured_sound_speed",
        "measured_acoustic_attenuation",
        "fit_window",
        "conservation_residual",
        "energy_residual",
        "heat_flux_residual",
    }
    with h5py.File(output, "r") as h5:
        assert required_root.issubset(h5.attrs.keys())
        assert h5.attrs["schema_name"] == "phase2_gas_core_handoff"
        assert h5.attrs["schema_version"] == "0.1.0"
        assert h5.attrs["producer"] == "GasSolver2D"
        assert h5.attrs["validation_level"] == "CONTRACT"
        schema = h5["metadata"]["schema"].attrs
        assert schema["name"] == "phase2_gas_core_handoff"
        assert schema["version"] == "0.1.0"
        handoff = h5["metadata"]["phase3_handoff"].attrs
        assert handoff["wall_normal_convention"] == "upper_half_domain_normal = +e_y"
        status = h5["metadata"]["verification_status"].attrs
        assert required_lattice.issubset(status.keys())
        assert required_collision.issubset(status.keys())
        assert required_results.issubset(status.keys())
        assert "fields/q_lu" in h5
        assert h5["fields/q_lu"].shape == (3, 4, 2)


def test_hdf5_metadata_records_d2q37_lattice_family(tmp_path):
    config = d2q37_physical_timestep_config()
    config["case"] = {"name": "metadata_d2q37_test"}
    config["numerics"] = {"nx": 4, "ny": 3}
    solver = GasSolver2D(config)
    solver.initialize_from_macro(1.0, np.zeros(2), solver.mapping.theta_ref_lu)
    output = tmp_path / "phase2_d2q37.h5"
    solver.save_hdf5(str(output))

    with h5py.File(output, "r") as h5:
        status = h5["metadata"]["verification_status"].attrs
        lattice = h5["metadata"]["lattice"].attrs
        assert status["velocity_set"] == "D2Q37"
        assert status["Q"] == 37
        assert lattice["velocity_set"] == "D2Q37"
        assert lattice["Q"] == 37
        assert h5["fields/f"].shape == (3, 4, 37)
        assert h5["fields/g"].shape == (3, 4, 37)
