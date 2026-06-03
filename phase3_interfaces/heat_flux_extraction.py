"""Heat-flux extraction and conversion for Phase 3 handoff."""

from __future__ import annotations

from typing import Any

import numpy as np

from core.lattice_d2q21 import make_d2q21
from core.macroscopic import heat_flux_lu
from core.unit_mapping import (
    create_unit_mapping,
    heat_flux_lu_to_phys,
    pressure_lu_to_phys,
    temperature_lu_to_phys,
    temperature_phys_to_lu,
)


UPPER_GAS_WALL_NORMAL = np.array([0.0, 1.0])
HEAT_FLUX_SIGN_CONVENTION = "q_g''=-k_g*dT/dy|0+ is positive from film into upper gas"


def normal_heat_flux_lu(q_lu, wall_normal=UPPER_GAS_WALL_NORMAL):
    q = np.asarray(q_lu, dtype=float)
    normal = np.asarray(wall_normal, dtype=float)
    normal = normal / np.linalg.norm(normal)
    return np.sum(q * normal, axis=-1)


def extract_wall_heat_flux(f, g, wall_normal=UPPER_GAS_WALL_NORMAL, config: dict[str, Any] | None = None, return_physical: bool = False):
    mapping = create_unit_mapping(config) if config is not None else None
    q = heat_flux_lu(f, g, lattice=make_d2q21(), mapping=mapping)
    q_n = normal_heat_flux_lu(q, wall_normal)
    if return_physical:
        if mapping is None:
            raise ValueError("config is required for physical heat-flux conversion")
        return heat_flux_lu_to_phys(q_n, mapping)
    return q_n


def convert_heat_flux_lu_to_phys(q_lu, config: dict[str, Any]):
    return heat_flux_lu_to_phys(q_lu, create_unit_mapping(config))


def convert_temperature_phys_to_lu(T_phys, config: dict[str, Any]):
    return temperature_phys_to_lu(T_phys, create_unit_mapping(config))


def convert_pressure_lu_to_phys(p_lu, config: dict[str, Any]):
    return pressure_lu_to_phys(p_lu, create_unit_mapping(config))


def convert_temperature_lu_to_phys(theta_lu, config: dict[str, Any]):
    return temperature_lu_to_phys(theta_lu, create_unit_mapping(config))
