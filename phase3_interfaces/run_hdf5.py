"""Phase_3 run HDF5 output per contract §9 (`docs/Phase_3/phase3_instruction_v1.0.md`).

Shared by the Level A/B/C run scripts so the wall/film/coupling metadata set required by
the contract (velocity set, theta_q/theta_ref/theta_transport, tau21/tau22/tau32, heat-flux
sign, wall normal, coupling scheme, dx/dt, C_A, phase convention) is written once, from
`core.unit_mapping.UnitMapping.to_metadata()` via `core.solver.minimum_hdf5_metadata` --
no second derivation of any mapping quantity happens here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import h5py
import numpy as np

from core.solver import minimum_hdf5_metadata, write_metadata
from core.unit_mapping import UnitMapping


PHASE3_COMPLEX_CONVENTION = "x(t)=Re[x_hat exp(i Omega t)]"
PHASE3_P_IN_DEFINITION = "P_in = absorbed areal power density (W/m^2); film ODE C_A dT_s/dt = P_in - 2 q_g''"


def phase3_hdf5_metadata(
    mapping: UnitMapping,
    *,
    case_name: str,
    level: str,
    pass_fail: str,
    config_sha256: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Contract §9 ``/meta`` payload: Phase_2 mapping metadata + Phase_3 run identity."""

    meta = minimum_hdf5_metadata(mapping, case_name, pass_fail=pass_fail)
    meta.update(
        {
            "schema_name": "phase3_run",
            "schema_version": "0.1.0",
            "phase": "Phase_3",
            "level": str(level),
            "config_sha256": config_sha256,
            "complex_convention": PHASE3_COMPLEX_CONVENTION,
            "P_in_definition": PHASE3_P_IN_DEFINITION,
        }
    )
    if extra:
        meta.update(extra)
    return meta


def _write_group(group: h5py.Group, data: dict[str, Any]) -> None:
    for key, value in data.items():
        if isinstance(value, complex):
            dset = group.create_dataset(key, data=np.asarray([value.real, value.imag], dtype=float))
            dset.attrs["layout"] = "real_imag"
        elif isinstance(value, str) or isinstance(value, bool):
            group.attrs[key] = value
        elif np.isscalar(value):
            group.attrs[key] = float(value)
        else:
            group.create_dataset(key, data=np.asarray(value))


def write_phase3_run_hdf5(
    path: Path | str,
    *,
    meta: dict[str, Any],
    time_si: np.ndarray,
    groups: dict[str, dict[str, Any]],
) -> None:
    """Write a contract §9 run file: ``/meta`` attrs, ``/time/t_si``, then one group per
    entry of ``groups`` (``film`` / ``wall`` / ``probes`` / ``harmonic``); complex scalars
    are stored as ``[real, imag]`` datasets, strings/bools/scalars as group attrs."""

    with h5py.File(str(path), "w") as h5:
        write_metadata(h5.create_group("meta"), meta)
        h5.create_group("time").create_dataset("t_si", data=np.asarray(time_si, dtype=float))
        for name, data in groups.items():
            _write_group(h5.create_group(name), data)


__all__ = [
    "PHASE3_COMPLEX_CONVENTION",
    "PHASE3_P_IN_DEFINITION",
    "phase3_hdf5_metadata",
    "write_phase3_run_hdf5",
]
