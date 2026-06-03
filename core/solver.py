"""Minimal Phase 2 gas solver shell."""

from __future__ import annotations

from datetime import datetime, timezone
import subprocess
from typing import Any

import h5py
import numpy as np

from core.collision_smrt import collide_fg
from core.equilibrium import equilibrium_fg
from core.lattice_d2q21 import LatticeD2Q21, make_d2q21
from core.macroscopic import ENERGY_CLOSURE_DEFINITION, MacroState, heat_flux_lu, recover_macro
from core.streaming import pull_stream_fg
from core.unit_mapping import UnitMapping, create_unit_mapping


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return "unknown"
    return result.stdout.strip() or "unknown"


def minimum_hdf5_metadata(mapping: UnitMapping, case_name: str, pass_fail: str = "not_run") -> dict[str, Any]:
    meta = mapping.to_metadata()
    meta.update(
        {
            "schema_name": "phase2_gas_core_handoff",
            "schema_version": "0.1.0",
            "producer": "GasSolver2D",
            "phase2_instruction_version": "v1.1",
            "validation_level": "CONTRACT",
            "case_name": case_name,
            "phase": "Phase_2",
            "code_git_commit": _git_commit(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "pass_fail": pass_fail,
            "clipping_used": False,
            "model": "SMRT_central_Hermite_regularized_stress",
            "high_order_relaxation": mapping.collision.high_order_relaxation,
            "energy_closure_definition": ENERGY_CLOSURE_DEFINITION,
            "mapping_name": mapping.lattice.theta_ref_policy,
            "clipping_allowed": False,
            "heat_flux_sign_convention": "q_g'' = -k_g dT/dy|0+",
            "wall_normal_convention": "upper_half_domain_normal = +e_y",
            "complex_convention": "Re[x_hat exp(i Omega t)]",
            "measured_nu": np.nan,
            "measured_alpha": np.nan,
            "measured_Pr": np.nan,
            "measured_gamma": np.nan,
            "measured_sound_speed": np.nan,
            "measured_acoustic_attenuation": np.nan,
            "fit_window": "",
            "conservation_residual": np.nan,
            "energy_residual": np.nan,
            "heat_flux_residual": np.nan,
        }
    )
    return meta


def write_metadata(group: h5py.Group, metadata: dict[str, Any]) -> None:
    for key, value in metadata.items():
        if value is None:
            value = ""
        group.attrs[key] = value


class GasSolver2D:
    """Periodic 2D Phase_2 gas solver with velocity-last f/g layout."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.case_name = config.get("case", {}).get("name", "phase2_case")
        self.lattice: LatticeD2Q21 = make_d2q21()
        self.mapping: UnitMapping = create_unit_mapping(config)
        numerics = config.get("numerics", {})
        self.ny = int(numerics.get("ny", 4))
        self.nx = int(numerics.get("nx", 64))
        self.t_lu = 0
        self.f: np.ndarray | None = None
        self.g: np.ndarray | None = None

    def initialize_from_macro(self, rho: np.ndarray | float, u: np.ndarray, theta: np.ndarray | float) -> None:
        rho_arr = np.broadcast_to(np.asarray(rho, dtype=float), (self.ny, self.nx))
        theta_arr = np.broadcast_to(np.asarray(theta, dtype=float), (self.ny, self.nx))
        u_arr = np.asarray(u, dtype=float)
        if u_arr.shape == (2,):
            u_arr = np.broadcast_to(u_arr, (self.ny, self.nx, 2))
        else:
            u_arr = np.broadcast_to(u_arr, (self.ny, self.nx, 2))
        self.f, self.g = equilibrium_fg(rho_arr, u_arr, theta_arr, self.mapping.lattice.S, self.lattice)

    def _require_state(self) -> tuple[np.ndarray, np.ndarray]:
        if self.f is None or self.g is None:
            self.initialize_from_macro(
                self.mapping.lattice.rho_ref_lu,
                np.zeros(2, dtype=float),
                self.mapping.theta_ref_lu,
            )
        assert self.f is not None and self.g is not None
        return self.f, self.g

    def step(self, n_steps: int = 1) -> None:
        for _ in range(int(n_steps)):
            f, g = self._require_state()
            f_post, g_post = collide_fg(f, g, self.mapping, lattice=self.lattice)
            self.f, self.g = pull_stream_fg(f_post, g_post, lattice=self.lattice, y_axis=0, x_axis=1)
            self.t_lu += 1

    def get_macro(self) -> MacroState:
        f, g = self._require_state()
        return recover_macro(f, g, D=self.mapping.lattice.D, S=self.mapping.lattice.S, lattice=self.lattice)

    def get_pressure_lu(self) -> np.ndarray:
        return self.get_macro().p

    def get_temperature_lu(self) -> np.ndarray:
        return self.get_macro().theta

    def get_heat_flux_lu(self) -> np.ndarray:
        f, g = self._require_state()
        return heat_flux_lu(f, g, lattice=self.lattice, mapping=self.mapping)

    def sample_probe(self, locations) -> dict[str, dict[str, np.ndarray]]:
        state = self.get_macro()
        q = self.get_heat_flux_lu()
        samples: dict[str, dict[str, np.ndarray]] = {}
        for i, loc in enumerate(locations):
            y, x = loc
            name = f"probe_{i}"
            samples[name] = {
                "rho_lu": np.asarray(state.rho[y, x]),
                "u_lu": np.asarray(state.u[y, x]),
                "theta_lu": np.asarray(state.theta[y, x]),
                "p_lu": np.asarray(state.p[y, x]),
                "q_lu": np.asarray(q[y, x]),
            }
        return samples

    def save_hdf5(self, path: str) -> None:
        f, g = self._require_state()
        state = self.get_macro()
        q = self.get_heat_flux_lu()
        metadata = minimum_hdf5_metadata(self.mapping, self.case_name)
        with h5py.File(path, "w") as h5:
            write_metadata(h5, metadata)
            time_group = h5.create_group("time")
            time_group.create_dataset("t_lu", data=np.asarray([self.t_lu], dtype=np.int64))
            time_group.create_dataset("t_s", data=np.asarray([self.t_lu * self.mapping.lattice.dt_s], dtype=float))
            fields = h5.create_group("fields")
            fields.create_dataset("rho_lu", data=state.rho)
            fields.create_dataset("u_lu", data=state.u)
            fields.create_dataset("theta_lu", data=state.theta)
            fields.create_dataset("p_lu", data=state.p)
            fields.create_dataset("q_lu", data=q)
            fields.create_dataset("f", data=f)
            fields.create_dataset("g", data=g)
            meta = h5.create_group("metadata")
            write_metadata(meta.create_group("unit_mapping"), self.mapping.to_metadata())
            write_metadata(meta.create_group("lattice"), {"velocity_set": "D2Q21", "Q": 21, "D": 2})
            write_metadata(
                meta.create_group("collision"),
                {
                    "model": metadata["model"],
                    "bulk_viscosity_policy": self.mapping.collision.bulk_viscosity_policy,
                    "tau21": self.mapping.tau21,
                    "tau22": self.mapping.tau22,
                    "tau32": self.mapping.tau32,
                    "regularized_shear_xy_factor": self.mapping.collision.regularized_shear_xy_factor,
                    "regularized_shear_normal_factor": self.mapping.collision.regularized_shear_normal_factor,
                    "regularized_heat_flux_factor": self.mapping.collision.regularized_heat_flux_factor,
                    "regularized_heat_flux_f_fraction": self.mapping.collision.regularized_heat_flux_f_fraction,
                    "conductive_heat_flux_moment_factor": (
                        self.mapping.collision.conductive_heat_flux_moment_factor
                    ),
                    "energy_closure_definition": ENERGY_CLOSURE_DEFINITION,
                    "clipping_allowed": False,
                },
            )
            write_metadata(
                meta.create_group("schema"),
                {
                    "name": metadata["schema_name"],
                    "version": metadata["schema_version"],
                    "producer": metadata["producer"],
                    "phase2_instruction_version": metadata["phase2_instruction_version"],
                    "validation_level": metadata["validation_level"],
                },
            )
            write_metadata(
                meta.create_group("phase3_handoff"),
                {
                    "heat_flux_sign_convention": metadata["heat_flux_sign_convention"],
                    "wall_normal_convention": metadata["wall_normal_convention"],
                    "complex_convention": metadata["complex_convention"],
                },
            )
            write_metadata(meta.create_group("verification_status"), metadata)
