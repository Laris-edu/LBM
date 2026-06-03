import h5py
import numpy as np

from core.solver import GasSolver2D
from core.unit_mapping import physical_timestep_config


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
        "regularized_shear_xy_factor",
        "regularized_shear_normal_factor",
        "regularized_heat_flux_factor",
        "regularized_heat_flux_f_fraction",
        "conductive_heat_flux_moment_factor",
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
