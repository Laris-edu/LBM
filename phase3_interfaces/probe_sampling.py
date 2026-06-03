"""Probe sampling helpers for Phase 2/3 HDF5-compatible fields."""

from __future__ import annotations

import numpy as np


def sample_grid_locations(fields: dict[str, np.ndarray], locations) -> dict[str, dict[str, np.ndarray]]:
    samples: dict[str, dict[str, np.ndarray]] = {}
    for i, (y, x) in enumerate(locations):
        samples[f"probe_{i}"] = {name: np.asarray(value[y, x]) for name, value in fields.items()}
    return samples
