"""Minimal Phase 2 gas solver shell."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import subprocess
from typing import Any

import h5py
import numpy as np

from core.collision_smrt import collide_fg
from core.equilibrium import equilibrium_fg
from core.lattice import Lattice, make_lattice
from core.macroscopic import ENERGY_CLOSURE_DEFINITION, MacroState, heat_flux_lu, recover_macro
from core.streaming import pull_stream_fg
from core.unit_mapping import (
    ACOUSTIC_PHASE_HIGH_MODE_POLICY_FULL_MODAL_TARGET,
    ACOUSTIC_PHASE_HIGH_MODE_POLICY_SPECIFIED,
    TRACE_BULK_POLICY_CURRENT_ZERO,
    TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_PRESSURE_MEMORY,
    TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL,
    TRACE_BULK_POLICY_GHOST_ORTHOGONAL_SPECTRAL,
    TRACE_BULK_POLICY_TAU22,
    UnitMapping,
    create_unit_mapping,
    trace_bulk_projector_alpha_from_tau32,
)


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
            "central_moment_closure": mapping.collision.central_moment_closure,
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


def _periodic_laplacian(field: np.ndarray) -> np.ndarray:
    return (
        np.roll(field, 1, axis=0)
        + np.roll(field, -1, axis=0)
        + np.roll(field, 1, axis=1)
        + np.roll(field, -1, axis=1)
        - 4.0 * field
    )


def _periodic_central_gradient(field: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    grad_x = 0.5 * (np.roll(field, -1, axis=1) - np.roll(field, 1, axis=1))
    grad_y = 0.5 * (np.roll(field, -1, axis=0) - np.roll(field, 1, axis=0))
    return grad_x, grad_y


def _periodic_central_velocity_divergence(u: np.ndarray) -> np.ndarray:
    dux_dx = 0.5 * (np.roll(u[..., 0], -1, axis=1) - np.roll(u[..., 0], 1, axis=1))
    duy_dy = 0.5 * (np.roll(u[..., 1], -1, axis=0) - np.roll(u[..., 1], 1, axis=0))
    return dux_dx + duy_dy


def conservative_biharmonic_filter(field: np.ndarray, strength: float) -> np.ndarray:
    """Damp grid-scale periodic content while preserving global moments."""

    if strength == 0.0:
        return field
    return field - strength * _periodic_laplacian(_periodic_laplacian(field))


_GHOST_PROJECTOR_OPERATOR_CACHE: dict[tuple[Any, ...], np.ndarray] = {}
_GHOST_PROJECTOR_PHASE_CACHE: dict[tuple[int, int, float, float], tuple[np.ndarray, np.ndarray]] = {}
_ACOUSTIC_PHASE_OPERATOR_CACHE: dict[tuple[Any, ...], np.ndarray] = {}
_HIGH_MODE_MODAL_SYMBOL_CACHE: dict[tuple[Any, ...], np.ndarray] = {}


def _modal_phase_pair(ny: int, nx: int, kx: float, ky: float) -> tuple[np.ndarray, np.ndarray]:
    key = (int(ny), int(nx), round(float(kx), 15), round(float(ky), 15))
    if key not in _GHOST_PROJECTOR_PHASE_CACHE:
        x = np.arange(nx, dtype=float)
        y = np.arange(ny, dtype=float)
        phase = float(kx) * x[None, :] + float(ky) * y[:, None]
        forward = np.exp(-1j * phase)
        inverse = np.exp(1j * phase) / float(ny * nx)
        _GHOST_PROJECTOR_PHASE_CACHE[key] = (forward, inverse)
    return _GHOST_PROJECTOR_PHASE_CACHE[key]


def _mapping_with_trace_policy(mapping: UnitMapping, policy: str, trace_scale: float) -> UnitMapping:
    return replace(
        mapping,
        collision=replace(
            mapping.collision,
            trace_bulk_policy=policy,
            trace_bulk_scale=float(trace_scale),
        ),
    )


def _single_cell_equilibrium_state(
    *,
    rho0: float,
    u0: tuple[float, float],
    theta0: float,
    mapping: UnitMapping,
    lattice: Lattice,
) -> tuple[np.ndarray, np.ndarray]:
    rho = np.ones((1, 1), dtype=float) * float(rho0)
    u = np.zeros((1, 1, 2), dtype=float)
    u[..., 0] = float(u0[0])
    u[..., 1] = float(u0[1])
    theta = np.ones((1, 1), dtype=float) * float(theta0)
    return equilibrium_fg(rho, u, theta, mapping.lattice.S, lattice)


def _collision_jacobian(
    *,
    mapping: UnitMapping,
    lattice: Lattice,
    rho0: float,
    u0: tuple[float, float],
    theta0: float,
) -> np.ndarray:
    q = int(lattice.q)
    n_state = 2 * q
    f0, g0 = _single_cell_equilibrium_state(
        rho0=rho0,
        u0=u0,
        theta0=theta0,
        mapping=mapping,
        lattice=lattice,
    )
    f_base, g_base = collide_fg(f0, g0, mapping, lattice=lattice)
    y_base = np.concatenate([f_base.reshape(q), g_base.reshape(q)])

    eps = 1.0e-8
    jacobian = np.empty((n_state, n_state), dtype=float)
    for index in range(n_state):
        f_probe = f0.copy()
        g_probe = g0.copy()
        if index < q:
            f_probe.reshape(q)[index] += eps
        else:
            g_probe.reshape(q)[index - q] += eps
        f_post, g_post = collide_fg(f_probe, g_probe, mapping, lattice=lattice)
        y_post = np.concatenate([f_post.reshape(q), g_post.reshape(q)])
        jacobian[:, index] = (y_post - y_base) / eps
    return jacobian


def _acoustic_projector(
    symbol: np.ndarray,
    *,
    mapping: UnitMapping,
    k_norm: float,
) -> np.ndarray:
    values, vectors = np.linalg.eig(symbol)
    c_target = float(np.sqrt(mapping.physical.gamma * mapping.theta_ref_lu))
    candidates: list[tuple[float, int]] = []
    for index, value in enumerate(values):
        magnitude = abs(value)
        if magnitude <= 0.0 or not np.isfinite(magnitude):
            continue
        angle = abs(float(np.angle(value)))
        if angle <= 1.0e-8:
            continue
        phase_speed = angle / k_norm
        speed_error = abs(phase_speed / c_target - 1.0)
        candidates.append((speed_error, index))
    if len(candidates) < 2:
        raise RuntimeError("no acoustic eigenvalue pair found for spectral trace projector")
    candidates.sort(key=lambda item: item[0])
    inverse_vectors = np.linalg.inv(vectors)
    projector = np.zeros_like(symbol, dtype=complex)
    for _, index in candidates[:2]:
        projector += np.outer(vectors[:, index], inverse_vectors[index, :])
    return projector


def _acoustic_eigenprojector_correction(
    symbol: np.ndarray,
    *,
    mapping: UnitMapping,
    k_norm: float,
    phase_factor: float,
) -> np.ndarray:
    values, vectors = np.linalg.eig(symbol)
    c_target = float(np.sqrt(mapping.physical.gamma * mapping.theta_ref_lu))
    candidates: list[tuple[float, int]] = []
    for index, value in enumerate(values):
        magnitude = abs(value)
        if magnitude <= 0.0 or not np.isfinite(magnitude):
            continue
        angle = abs(float(np.angle(value)))
        if angle <= 1.0e-8:
            continue
        phase_speed = angle / k_norm
        speed_error = abs(phase_speed / c_target - 1.0)
        candidates.append((speed_error, index))
    if len(candidates) < 2:
        raise RuntimeError("no acoustic eigenvalue pair found for acoustic phase correction")
    candidates.sort(key=lambda item: item[0])
    inverse_vectors = np.linalg.inv(vectors)
    correction = np.zeros_like(symbol, dtype=complex)
    for _, index in candidates[:2]:
        angle = float(np.angle(values[index]))
        multiplier = np.exp(1j * (float(phase_factor) - 1.0) * angle)
        projector = np.outer(vectors[:, index], inverse_vectors[index, :])
        correction += (multiplier - 1.0) * projector
    return correction


def _acoustic_eigenprojector_target_phase_correction(
    symbol: np.ndarray,
    *,
    mapping: UnitMapping,
    lattice: Lattice,
    kx: float,
    ky: float,
    rho0: float,
    u0: tuple[float, float],
    theta0: float,
) -> np.ndarray:
    k_norm = float(np.hypot(kx, ky))
    if k_norm <= 1.0e-14:
        return np.zeros_like(symbol, dtype=complex)

    values, vectors = np.linalg.eig(symbol)
    c_target = float(np.sqrt(mapping.physical.gamma * theta0))
    background_phase = float(kx) * float(u0[0]) + float(ky) * float(u0[1])
    candidates_by_sign: dict[int, list[tuple[float, float, int, float]]] = {-1: [], 1: []}
    fallback: list[tuple[float, float, int, float]] = []
    for index, value in enumerate(values):
        magnitude = abs(value)
        if magnitude <= 1.0e-6 or not np.isfinite(magnitude):
            continue
        angle = float(np.angle(value))
        intrinsic_angle = angle + background_phase
        if abs(intrinsic_angle) <= 1.0e-8:
            continue
        phase_speed = abs(intrinsic_angle) / k_norm
        speed_error = abs(phase_speed / c_target - 1.0)
        sign = 1 if intrinsic_angle >= 0.0 else -1
        observability = _acoustic_eigenvector_observability(
            vectors[:, index],
            mapping=mapping,
            lattice=lattice,
            kx=kx,
            ky=ky,
            rho0=rho0,
            u0=u0,
            theta0=theta0,
        )
        candidate = (speed_error, observability, index, intrinsic_angle)
        fallback.append(candidate)
        candidates_by_sign[sign].append(candidate)

    selected: list[tuple[float, float, int, float]] = []
    for sign in (-1, 1):
        sign_candidates = candidates_by_sign[sign]
        if not sign_candidates:
            continue
        max_observability = max(candidate[1] for candidate in sign_candidates)
        observed_candidates = [
            candidate
            for candidate in sign_candidates
            if candidate[1] >= max(1.0e-8, 1.0e-4 * max_observability)
        ]
        pool = observed_candidates or sign_candidates
        pool.sort(key=lambda item: (item[0], -item[1]))
        selected.append(pool[0])
    if len(selected) < 2:
        fallback.sort(key=lambda item: (item[0], -item[1]))
        selected = fallback[:2]
    if len(selected) < 2:
        raise RuntimeError("no acoustic eigenvalue pair found for target phase correction")

    inverse_vectors = np.linalg.inv(vectors)
    correction = np.zeros_like(symbol, dtype=complex)
    for _speed_error, _observability, index, intrinsic_angle in selected:
        sign = 1.0 if intrinsic_angle >= 0.0 else -1.0
        current_angle = float(np.angle(values[index]))
        target_angle = -background_phase + sign * c_target * k_norm
        multiplier = np.exp(1j * (target_angle - current_angle))
        projector = np.outer(vectors[:, index], inverse_vectors[index, :])
        correction += (multiplier - 1.0) * projector
    return correction


def _acoustic_eigenvector_observability(
    vector: np.ndarray,
    *,
    mapping: UnitMapping,
    lattice: Lattice,
    kx: float,
    ky: float,
    rho0: float,
    u0: tuple[float, float],
    theta0: float,
) -> float:
    q = int(lattice.q)
    norm = float(np.linalg.norm(vector))
    if norm <= 0.0 or not np.isfinite(norm):
        return 0.0
    k_norm = float(np.hypot(kx, ky))
    if k_norm <= 0.0:
        return 0.0

    f_vec = vector[:q]
    g_vec = vector[q:]
    rho_prime = np.sum(f_vec)
    momentum_prime = np.einsum("a,ai->i", f_vec, lattice.c)
    u0_array = np.asarray(u0, dtype=float)
    velocity_prime = (momentum_prime - u0_array * rho_prime) / float(rho0)
    peculiar = lattice.c - u0_array[None, :]
    translational_prime = 0.5 * np.sum(f_vec * np.sum(peculiar * peculiar, axis=1))
    internal_prime = translational_prime + np.sum(g_vec)
    pressure_prime = 2.0 * internal_prime / float(mapping.lattice.D + mapping.lattice.S)
    k_unit = np.array([kx, ky], dtype=float) / k_norm
    longitudinal_velocity_prime = np.dot(velocity_prime, k_unit)
    c_target = float(np.sqrt(mapping.physical.gamma * theta0))
    observable = np.hypot(
        abs(pressure_prime / (float(rho0) * float(theta0))),
        abs(longitudinal_velocity_prime / c_target),
    )
    return float(observable / norm)


def _acoustic_phase_correction_operator(
    *,
    mapping: UnitMapping,
    lattice: Lattice,
    kx: float,
    ky: float,
    phase_factor: float,
    rho0: float,
    u0: tuple[float, float],
    theta0: float,
) -> np.ndarray:
    k_norm = float(np.hypot(kx, ky))
    if k_norm <= 1.0e-14:
        q = int(lattice.q)
        return np.zeros((2 * q, 2 * q), dtype=complex)

    jacobian = _collision_jacobian(
        mapping=mapping,
        lattice=lattice,
        rho0=rho0,
        u0=u0,
        theta0=theta0,
    )
    streaming_phase = np.exp(-1j * (kx * lattice.c[:, 0] + ky * lattice.c[:, 1]))
    streaming = np.concatenate([streaming_phase, streaming_phase])
    symbol = streaming[:, None] * jacobian
    return _acoustic_eigenprojector_correction(
        symbol,
        mapping=mapping,
        k_norm=k_norm,
        phase_factor=phase_factor,
    )


def _ghost_orthogonal_trace_collision_operator(
    *,
    mapping: UnitMapping,
    lattice: Lattice,
    kx: float,
    ky: float,
    rho0: float,
    u0: tuple[float, float],
    theta0: float,
) -> np.ndarray:
    k_norm = float(np.hypot(kx, ky))
    if k_norm <= 1.0e-14:
        q = int(lattice.q)
        return np.zeros((2 * q, 2 * q), dtype=complex)

    mapping_zero = _mapping_with_trace_policy(
        mapping,
        TRACE_BULK_POLICY_CURRENT_ZERO,
        trace_scale=1.0,
    )
    mapping_tau22 = _mapping_with_trace_policy(
        mapping,
        TRACE_BULK_POLICY_TAU22,
        trace_scale=1.0,
    )
    jacobian_zero = _collision_jacobian(
        mapping=mapping_zero,
        lattice=lattice,
        rho0=rho0,
        u0=u0,
        theta0=theta0,
    )
    jacobian_tau22 = _collision_jacobian(
        mapping=mapping_tau22,
        lattice=lattice,
        rho0=rho0,
        u0=u0,
        theta0=theta0,
    )
    streaming_phase = np.exp(-1j * (kx * lattice.c[:, 0] + ky * lattice.c[:, 1]))
    streaming = np.concatenate([streaming_phase, streaming_phase])
    symbol_zero = streaming[:, None] * jacobian_zero
    symbol_tau22 = streaming[:, None] * jacobian_tau22
    acoustic_projector = _acoustic_projector(
        symbol_zero,
        mapping=mapping,
        k_norm=k_norm,
    )
    full_step_update = (symbol_tau22 - symbol_zero) @ acoustic_projector
    return (1.0 / streaming)[:, None] * full_step_update


def _low_fourier_modes(ny: int, nx: int, low_laplacian: float) -> list[tuple[int, int, float, float]]:
    if low_laplacian <= 0.0:
        return []
    modes: list[tuple[int, int, float, float]] = []
    kx_values = 2.0 * np.pi * np.fft.fftfreq(nx)
    ky_values = 2.0 * np.pi * np.fft.fftfreq(ny)
    threshold = float(low_laplacian) * (1.0 + 1.0e-12)
    for iy, ky in enumerate(ky_values):
        for ix, kx in enumerate(kx_values):
            if ix == 0 and iy == 0:
                continue
            mu = 4.0 * np.sin(0.5 * kx) ** 2 + 4.0 * np.sin(0.5 * ky) ** 2
            if float(mu) <= threshold:
                modes.append((iy, ix, float(kx), float(ky)))
    return modes


def _low_diagonal_fourier_modes(ny: int, nx: int, low_laplacian: float) -> list[tuple[int, int, float, float]]:
    return [
        (iy, ix, kx, ky)
        for iy, ix, kx, ky in _low_fourier_modes(ny, nx, low_laplacian)
        if abs(kx) > 0.0 and abs(ky) > 0.0
    ]


def _high_acoustic_fourier_modes(
    ny: int,
    nx: int,
    high_laplacian: float,
    *,
    include_branch_family: bool = False,
) -> list[tuple[int, int, float, float]]:
    if high_laplacian <= 0.0:
        return []
    modes: list[tuple[int, int, float, float]] = []
    kx_values = 2.0 * np.pi * np.fft.fftfreq(nx)
    ky_values = 2.0 * np.pi * np.fft.fftfreq(ny)
    axis_target = float(high_laplacian)
    diagonal_target = 2.0 * axis_target
    tolerance = max(1.0e-12, 1.0e-10 * axis_target)
    branch_k_limit = np.inf
    if include_branch_family:
        clipped = min(1.0, 0.5 * np.sqrt(axis_target))
        branch_k_limit = 1.5 * float(2.0 * np.arcsin(clipped)) + tolerance
    for iy, ky in enumerate(ky_values):
        for ix, kx in enumerate(kx_values):
            if ix == 0 and iy == 0:
                continue
            mu = 4.0 * np.sin(0.5 * kx) ** 2 + 4.0 * np.sin(0.5 * ky) ** 2
            if include_branch_family:
                if (
                    float(mu) >= axis_target - tolerance
                    and max(abs(float(kx)), abs(float(ky))) <= branch_k_limit
                ):
                    modes.append((iy, ix, float(kx), float(ky)))
            elif abs(float(mu) - axis_target) <= tolerance or abs(float(mu) - diagonal_target) <= tolerance:
                modes.append((iy, ix, float(kx), float(ky)))
    return modes


class GasSolver2D:
    """Periodic 2D Phase_2 gas solver with velocity-last f/g layout."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.case_name = config.get("case", {}).get("name", "phase2_case")
        self.mapping: UnitMapping = create_unit_mapping(config)
        self.lattice: Lattice = make_lattice(self.mapping.lattice.velocity_set)
        numerics = config.get("numerics", {})
        self.ny = int(numerics.get("ny", 4))
        self.nx = int(numerics.get("nx", 64))
        filter_config = numerics.get("high_wavenumber_filter", {}) or {}
        if isinstance(filter_config, bool):
            filter_config = {"enabled": filter_config}
        self.high_wavenumber_filter_enabled = bool(filter_config.get("enabled", False))
        self.high_wavenumber_filter_strength = float(filter_config.get("strength", 0.0))
        self.high_wavenumber_filter_passes = int(filter_config.get("passes", 1))
        if not self.high_wavenumber_filter_enabled:
            self.high_wavenumber_filter_strength = 0.0
        if not 0.0 <= self.high_wavenumber_filter_strength <= 0.03125:
            raise ValueError("high_wavenumber_filter strength must be in [0, 0.03125]")
        if self.high_wavenumber_filter_passes < 1:
            raise ValueError("high_wavenumber_filter passes must be positive")
        self.t_lu = 0
        self.f: np.ndarray | None = None
        self.g: np.ndarray | None = None
        self._ghost_projector_reference: tuple[float, float, float, float] | None = None
        self._ghost_projector_modes_cache: dict[tuple[int, int, float], list[tuple[int, int, float, float]]] = {}
        self._acoustic_phase_modes_cache: dict[tuple[int, int, float], list[tuple[int, int, float, float]]] = {}
        self._acoustic_phase_high_modes_cache: dict[tuple[int, int, float, str], list[tuple[int, int, float, float]]] = {}
        self._previous_pressure_for_trace: np.ndarray | None = None

    def initialize_from_macro(self, rho: np.ndarray | float, u: np.ndarray, theta: np.ndarray | float) -> None:
        rho_arr = np.broadcast_to(np.asarray(rho, dtype=float), (self.ny, self.nx))
        theta_arr = np.broadcast_to(np.asarray(theta, dtype=float), (self.ny, self.nx))
        u_arr = np.asarray(u, dtype=float)
        if u_arr.shape == (2,):
            u_arr = np.broadcast_to(u_arr, (self.ny, self.nx, 2))
        else:
            u_arr = np.broadcast_to(u_arr, (self.ny, self.nx, 2))
        self.f, self.g = equilibrium_fg(rho_arr, u_arr, theta_arr, self.mapping.lattice.S, self.lattice)
        self._previous_pressure_for_trace = None

    def _require_state(self) -> tuple[np.ndarray, np.ndarray]:
        if self.f is None or self.g is None:
            self.initialize_from_macro(
                self.mapping.lattice.rho_ref_lu,
                np.zeros(2, dtype=float),
                self.mapping.theta_ref_lu,
            )
        assert self.f is not None and self.g is not None
        return self.f, self.g

    def _ghost_projector_modes(self) -> list[tuple[int, int, float, float]]:
        low_laplacian = self.mapping.collision.trace_bulk_projector_low_laplacian
        key = (self.ny, self.nx, float(low_laplacian))
        if key not in self._ghost_projector_modes_cache:
            self._ghost_projector_modes_cache[key] = _low_fourier_modes(
                self.ny,
                self.nx,
                low_laplacian,
            )
        return self._ghost_projector_modes_cache[key]

    def _acoustic_phase_modes(self) -> list[tuple[int, int, float, float]]:
        low_laplacian = self.mapping.collision.acoustic_phase_correction_low_laplacian
        key = (self.ny, self.nx, float(low_laplacian))
        if key not in self._acoustic_phase_modes_cache:
            self._acoustic_phase_modes_cache[key] = _low_diagonal_fourier_modes(
                self.ny,
                self.nx,
                low_laplacian,
            )
        return self._acoustic_phase_modes_cache[key]

    def _acoustic_phase_high_modes(self) -> list[tuple[int, int, float, float]]:
        high_laplacian = self.mapping.collision.dispersion_correction_high_laplacian
        high_mode_policy = self.mapping.collision.acoustic_phase_high_mode_policy
        key = (self.ny, self.nx, float(high_laplacian), high_mode_policy)
        if key not in self._acoustic_phase_high_modes_cache:
            self._acoustic_phase_high_modes_cache[key] = _high_acoustic_fourier_modes(
                self.ny,
                self.nx,
                high_laplacian,
                include_branch_family=high_mode_policy
                == ACOUSTIC_PHASE_HIGH_MODE_POLICY_FULL_MODAL_TARGET,
            )
        return self._acoustic_phase_high_modes_cache[key]

    def _ghost_projector_reference_state(
        self,
        f: np.ndarray,
        g: np.ndarray,
    ) -> tuple[float, tuple[float, float], float]:
        if self._ghost_projector_reference is None:
            macro = recover_macro(
                f,
                g,
                D=self.mapping.lattice.D,
                S=self.mapping.lattice.S,
                lattice=self.lattice,
            )
            rho0 = float(np.mean(macro.rho))
            u0x = float(np.mean(macro.u[..., 0]))
            u0y = float(np.mean(macro.u[..., 1]))
            theta0 = float(np.mean(macro.theta))
            self._ghost_projector_reference = (rho0, u0x, u0y, theta0)
        rho0, u0x, u0y, theta0 = self._ghost_projector_reference
        return rho0, (u0x, u0y), theta0

    def _ghost_projector_operator(
        self,
        *,
        kx: float,
        ky: float,
        rho0: float,
        u0: tuple[float, float],
        theta0: float,
    ) -> np.ndarray:
        collision = self.mapping.collision
        key = (
            self.mapping.lattice.velocity_set,
            round(float(kx), 15),
            round(float(ky), 15),
            round(float(rho0), 15),
            round(float(u0[0]), 15),
            round(float(u0[1]), 15),
            round(float(theta0), 15),
            round(float(self.mapping.theta_ref_lu), 15),
            round(float(self.mapping.tau21), 15),
            round(float(self.mapping.tau22), 15),
            round(float(self.mapping.tau32), 15),
            round(float(self.mapping.physical.gamma), 15),
            round(float(collision.regularized_heat_flux_factor), 15),
            round(float(collision.regularized_heat_flux_f_fraction), 15),
            round(float(collision.conductive_heat_flux_moment_factor), 15),
            round(float(collision.conductive_heat_flux_galilean_correction_factor), 15),
            round(float(collision.regularized_shear_xy_factor), 15),
            round(float(collision.regularized_shear_normal_factor), 15),
            collision.central_moment_closure,
            round(float(collision.high_order_relaxation), 15),
            tuple(round(float(item), 15) for item in collision.heat_flux_retention_curve_coefficients),
        )
        if key not in _GHOST_PROJECTOR_OPERATOR_CACHE:
            _GHOST_PROJECTOR_OPERATOR_CACHE[key] = _ghost_orthogonal_trace_collision_operator(
                mapping=self.mapping,
                lattice=self.lattice,
                kx=kx,
                ky=ky,
                rho0=rho0,
                u0=u0,
                theta0=theta0,
            )
        return _GHOST_PROJECTOR_OPERATOR_CACHE[key]

    def _acoustic_phase_operator(
        self,
        *,
        kx: float,
        ky: float,
        phase_factor: float,
        rho0: float,
        u0: tuple[float, float],
        theta0: float,
    ) -> np.ndarray:
        collision = self.mapping.collision
        key = (
            self.mapping.lattice.velocity_set,
            round(float(kx), 15),
            round(float(ky), 15),
            round(float(rho0), 15),
            round(float(u0[0]), 15),
            round(float(u0[1]), 15),
            round(float(theta0), 15),
            round(float(self.mapping.theta_ref_lu), 15),
            round(float(self.mapping.tau21), 15),
            round(float(self.mapping.tau22), 15),
            round(float(self.mapping.tau32), 15),
            round(float(self.mapping.physical.gamma), 15),
            round(float(collision.regularized_heat_flux_factor), 15),
            round(float(collision.regularized_heat_flux_f_fraction), 15),
            round(float(collision.regularized_shear_xy_factor), 15),
            round(float(collision.regularized_shear_normal_factor), 15),
            round(float(phase_factor), 15),
            collision.central_moment_closure,
            round(float(collision.high_order_relaxation), 15),
            collision.trace_bulk_policy,
            round(float(collision.trace_bulk_scale), 15),
        )
        if key not in _ACOUSTIC_PHASE_OPERATOR_CACHE:
            _ACOUSTIC_PHASE_OPERATOR_CACHE[key] = _acoustic_phase_correction_operator(
                mapping=self.mapping,
                lattice=self.lattice,
                kx=kx,
                ky=ky,
                phase_factor=phase_factor,
                rho0=rho0,
                u0=u0,
                theta0=theta0,
            )
        return _ACOUSTIC_PHASE_OPERATOR_CACHE[key]

    def _high_mode_modal_symbol(
        self,
        *,
        kx: float,
        ky: float,
        rho0: float,
        u0: tuple[float, float],
        theta0: float,
    ) -> np.ndarray:
        collision = self.mapping.collision
        key = (
            "high_mode_modal_symbol",
            self.mapping.lattice.velocity_set,
            self.ny,
            self.nx,
            round(float(kx), 15),
            round(float(ky), 15),
            round(float(rho0), 15),
            round(float(u0[0]), 15),
            round(float(u0[1]), 15),
            round(float(theta0), 15),
            round(float(self.mapping.theta_ref_lu), 15),
            round(float(self.mapping.tau21), 15),
            round(float(self.mapping.tau22), 15),
            round(float(self.mapping.tau32), 15),
            round(float(self.mapping.physical.gamma), 15),
            round(float(collision.regularized_heat_flux_factor), 15),
            round(float(collision.regularized_heat_flux_f_fraction), 15),
            round(float(collision.regularized_shear_xy_factor), 15),
            round(float(collision.regularized_shear_normal_factor), 15),
            round(float(collision.regularized_shear_xy_dispersion_target), 15),
            round(float(collision.regularized_shear_normal_dispersion_target), 15),
            round(float(collision.regularized_heat_flux_dispersion_target), 15),
            round(float(collision.regularized_heat_flux_diagonal_low_mode_target), 15),
            round(float(collision.dispersion_correction_low_laplacian), 15),
            round(float(collision.dispersion_correction_high_laplacian), 15),
            round(float(self.high_wavenumber_filter_strength), 15),
            int(self.high_wavenumber_filter_passes),
            collision.central_moment_closure,
            collision.trace_bulk_policy,
            round(float(collision.trace_bulk_scale), 15),
        )
        if key in _HIGH_MODE_MODAL_SYMBOL_CACHE:
            return _HIGH_MODE_MODAL_SYMBOL_CACHE[key]

        config = deepcopy(self.config)
        config.setdefault("numerics", {})
        config["numerics"]["ny"] = self.ny
        config["numerics"]["nx"] = self.nx
        config.setdefault("collision", {})
        config["collision"]["acoustic_phase_high_mode_policy"] = ACOUSTIC_PHASE_HIGH_MODE_POLICY_SPECIFIED
        config["collision"]["acoustic_phase_high_mode_factor"] = 1.0
        config["collision"]["acoustic_phase_high_mode_diagonal_factor"] = 1.0

        reference_solver = GasSolver2D(config)
        q = int(reference_solver.lattice.q)
        f0, g0 = _single_cell_equilibrium_state(
            rho0=rho0,
            u0=u0,
            theta0=theta0,
            mapping=reference_solver.mapping,
            lattice=reference_solver.lattice,
        )
        f_base = np.broadcast_to(f0.reshape(q), (self.ny, self.nx, q)).copy()
        g_base = np.broadcast_to(g0.reshape(q), (self.ny, self.nx, q)).copy()
        forward_phase, _inverse_phase = _modal_phase_pair(self.ny, self.nx, kx, ky)
        carrier = np.real(np.conj(forward_phase))
        extractor = forward_phase

        n_state = 2 * q
        eps = 1.0e-7
        symbol = np.empty((n_state, n_state), dtype=complex)
        for index in range(n_state):
            probe = GasSolver2D(config)
            probe.f = f_base.copy()
            probe.g = g_base.copy()
            probe.t_lu = 0
            if index < q:
                probe.f[..., index] += eps * carrier
            else:
                probe.g[..., index - q] += eps * carrier
            probe.step(1)
            perturbation = np.concatenate(
                [
                    probe.f - f_base,
                    probe.g - g_base,
                ],
                axis=-1,
            )
            symbol[:, index] = (
                (2.0 / float(self.ny * self.nx))
                * np.einsum("yx,yxs->s", extractor, perturbation)
                / eps
            )
        _HIGH_MODE_MODAL_SYMBOL_CACHE[key] = symbol
        return symbol

    def _high_mode_acoustic_phase_operator(
        self,
        *,
        kx: float,
        ky: float,
        phase_factor: float,
        rho0: float,
        u0: tuple[float, float],
        theta0: float,
    ) -> np.ndarray:
        symbol = self._high_mode_modal_symbol(
            kx=kx,
            ky=ky,
            rho0=rho0,
            u0=u0,
            theta0=theta0,
        )
        if self.mapping.collision.acoustic_phase_high_mode_policy == (
            ACOUSTIC_PHASE_HIGH_MODE_POLICY_FULL_MODAL_TARGET
        ):
            return _acoustic_eigenprojector_target_phase_correction(
                symbol,
                mapping=self.mapping,
                lattice=self.lattice,
                kx=kx,
                ky=ky,
                rho0=rho0,
                u0=u0,
                theta0=theta0,
            )
        return _acoustic_eigenprojector_correction(
            symbol,
            mapping=self.mapping,
            k_norm=float(np.hypot(kx, ky)),
            phase_factor=phase_factor,
        )

    def _apply_ghost_orthogonal_spectral_trace_projector(
        self,
        f_pre: np.ndarray,
        g_pre: np.ndarray,
        f_post: np.ndarray,
        g_post: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        if self.mapping.collision.trace_bulk_policy != TRACE_BULK_POLICY_GHOST_ORTHOGONAL_SPECTRAL:
            return f_post, g_post

        modes = self._ghost_projector_modes()
        if not modes:
            return f_post, g_post

        q = int(self.lattice.q)
        rho0, u0, theta0 = self._ghost_projector_reference_state(f_pre, g_pre)
        f_ref, g_ref = _single_cell_equilibrium_state(
            rho0=rho0,
            u0=u0,
            theta0=theta0,
            mapping=self.mapping,
            lattice=self.lattice,
        )
        perturbation = np.concatenate(
            [
                f_pre - f_ref.reshape(q),
                g_pre - g_ref.reshape(q),
            ],
            axis=-1,
        )
        correction = np.zeros_like(perturbation, dtype=complex)
        alpha_h = trace_bulk_projector_alpha_from_tau32(
            self.mapping.tau32,
            curve_type=self.mapping.collision.trace_bulk_projector_alpha_curve_type,
            coefficients=self.mapping.collision.trace_bulk_projector_alpha_curve_coefficients,
        )
        for _iy, _ix, kx, ky in modes:
            operator = self._ghost_projector_operator(
                kx=kx,
                ky=ky,
                rho0=rho0,
                u0=u0,
                theta0=theta0,
            )
            forward_phase, inverse_phase = _modal_phase_pair(self.ny, self.nx, kx, ky)
            amplitude = np.einsum("yx,yxs->s", forward_phase, perturbation)
            correction_amplitude = alpha_h * (operator @ amplitude)
            correction += inverse_phase[..., None] * correction_amplitude
        correction_real = correction.real
        return f_post + correction_real[..., :q], g_post + correction_real[..., q:]

    def _apply_diagonal_acoustic_phase_correction(
        self,
        f_state: np.ndarray,
        g_state: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        if not self.mapping.collision.acoustic_phase_correction_enabled:
            return f_state, g_state

        modes = self._acoustic_phase_modes()
        if not modes:
            return f_state, g_state

        q = int(self.lattice.q)
        rho0, u0, theta0 = self._ghost_projector_reference_state(f_state, g_state)
        f_ref, g_ref = _single_cell_equilibrium_state(
            rho0=rho0,
            u0=u0,
            theta0=theta0,
            mapping=self.mapping,
            lattice=self.lattice,
        )
        perturbation = np.concatenate(
            [
                f_state - f_ref.reshape(q),
                g_state - g_ref.reshape(q),
            ],
            axis=-1,
        )
        correction = np.zeros_like(perturbation, dtype=complex)
        for _iy, _ix, kx, ky in modes:
            forward_phase, inverse_phase = _modal_phase_pair(self.ny, self.nx, kx, ky)
            amplitude = np.einsum("yx,yxs->s", forward_phase, perturbation)
            if float(np.linalg.norm(amplitude)) <= 1.0e-18:
                continue
            operator = self._acoustic_phase_operator(
                kx=kx,
                ky=ky,
                phase_factor=self.mapping.collision.acoustic_phase_diagonal_low_mode_factor,
                rho0=rho0,
                u0=u0,
                theta0=theta0,
            )
            correction += inverse_phase[..., None] * (operator @ amplitude)
        correction_real = correction.real
        return f_state + correction_real[..., :q], g_state + correction_real[..., q:]

    def _apply_high_mode_acoustic_phase_correction(
        self,
        f_state: np.ndarray,
        g_state: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        collision = self.mapping.collision
        if not collision.acoustic_phase_correction_enabled:
            return f_state, g_state
        high_mode_policy = collision.acoustic_phase_high_mode_policy
        if (
            high_mode_policy == ACOUSTIC_PHASE_HIGH_MODE_POLICY_SPECIFIED
            and collision.acoustic_phase_high_mode_factor == 1.0
            and collision.acoustic_phase_high_mode_diagonal_factor == 1.0
        ):
            return f_state, g_state

        modes = self._acoustic_phase_high_modes()
        if not modes:
            return f_state, g_state

        q = int(self.lattice.q)
        rho0, u0, theta0 = self._ghost_projector_reference_state(f_state, g_state)
        f_ref, g_ref = _single_cell_equilibrium_state(
            rho0=rho0,
            u0=u0,
            theta0=theta0,
            mapping=self.mapping,
            lattice=self.lattice,
        )
        perturbation = np.concatenate(
            [
                f_state - f_ref.reshape(q),
                g_state - g_ref.reshape(q),
            ],
            axis=-1,
        )
        correction = np.zeros_like(perturbation, dtype=complex)
        for _iy, _ix, kx, ky in modes:
            phase_factor = (
                collision.acoustic_phase_high_mode_diagonal_factor
                if abs(kx) > 0.0 and abs(ky) > 0.0
                else collision.acoustic_phase_high_mode_factor
            )
            if (
                high_mode_policy == ACOUSTIC_PHASE_HIGH_MODE_POLICY_SPECIFIED
                and phase_factor == 1.0
            ):
                continue
            forward_phase, inverse_phase = _modal_phase_pair(self.ny, self.nx, kx, ky)
            amplitude = np.einsum("yx,yxs->s", forward_phase, perturbation)
            if float(np.linalg.norm(amplitude)) <= 1.0e-18:
                continue
            operator = self._high_mode_acoustic_phase_operator(
                kx=kx,
                ky=ky,
                phase_factor=phase_factor,
                rho0=rho0,
                u0=u0,
                theta0=theta0,
            )
            correction += inverse_phase[..., None] * (operator @ amplitude)
        correction_real = correction.real
        return f_state + correction_real[..., :q], g_state + correction_real[..., q:]

    def _pressure_memory_trace_divergence(self, f: np.ndarray, g: np.ndarray) -> np.ndarray | None:
        if (
            self.mapping.collision.trace_bulk_policy
            not in {
                TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_PRESSURE_MEMORY,
                TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL,
            }
        ):
            return None
        macro = recover_macro(
            f,
            g,
            D=self.mapping.lattice.D,
            S=self.mapping.lattice.S,
            lattice=self.lattice,
        )
        pressure = np.asarray(macro.p, dtype=float)
        previous = self._previous_pressure_for_trace
        self._previous_pressure_for_trace = pressure.copy()
        if previous is None or previous.shape != pressure.shape:
            return _periodic_central_velocity_divergence(macro.u)

        grad_x, grad_y = _periodic_central_gradient(pressure)
        u_mean = np.mean(macro.u, axis=(0, 1))
        pressure_material_derivative = (
            pressure
            - previous
            + float(u_mean[0]) * grad_x
            + float(u_mean[1]) * grad_y
        )
        p0 = self.mapping.lattice.rho_ref_lu * self.mapping.theta_ref_lu
        return -pressure_material_derivative / (self.mapping.physical.gamma * p0)

    def step(self, n_steps: int = 1) -> None:
        for _ in range(int(n_steps)):
            f, g = self._require_state()
            trace_bulk_pressure_divergence = self._pressure_memory_trace_divergence(f, g)
            f_post, g_post = collide_fg(
                f,
                g,
                self.mapping,
                lattice=self.lattice,
                trace_bulk_pressure_divergence=trace_bulk_pressure_divergence,
            )
            f_post, g_post = self._apply_ghost_orthogonal_spectral_trace_projector(
                f,
                g,
                f_post,
                g_post,
            )
            self.f, self.g = pull_stream_fg(f_post, g_post, lattice=self.lattice, y_axis=0, x_axis=1)
            self.f, self.g = self._apply_diagonal_acoustic_phase_correction(self.f, self.g)
            self.f, self.g = self._apply_high_mode_acoustic_phase_correction(self.f, self.g)
            for _ in range(self.high_wavenumber_filter_passes):
                self.f = conservative_biharmonic_filter(self.f, self.high_wavenumber_filter_strength)
                self.g = conservative_biharmonic_filter(self.g, self.high_wavenumber_filter_strength)
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
        metadata.update(
            {
                "high_wavenumber_filter_enabled": self.high_wavenumber_filter_enabled,
                "high_wavenumber_filter_strength": self.high_wavenumber_filter_strength,
                "high_wavenumber_filter_passes": self.high_wavenumber_filter_passes,
            }
        )
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
            write_metadata(
                meta.create_group("lattice"),
                {
                    "velocity_set": self.mapping.lattice.velocity_set,
                    "Q": self.mapping.lattice.Q,
                    "D": self.mapping.lattice.D,
                    "theta_q_lu": self.mapping.lattice.theta_q_lu,
                },
            )
            write_metadata(
                meta.create_group("collision"),
                {
                    "model": metadata["model"],
                    "bulk_viscosity_policy": self.mapping.collision.bulk_viscosity_policy,
                    "central_moment_closure": self.mapping.collision.central_moment_closure,
                    "trace_bulk_policy": self.mapping.collision.trace_bulk_policy,
                    "trace_bulk_scale": self.mapping.collision.trace_bulk_scale,
                    "trace_bulk_calibration_id": self.mapping.collision.trace_bulk_calibration_id,
                    "trace_bulk_projector_alpha_curve_type": (
                        self.mapping.collision.trace_bulk_projector_alpha_curve_type
                    ),
                    "trace_bulk_projector_alpha_curve_coefficients": (
                        self.mapping.collision.trace_bulk_projector_alpha_curve_coefficients
                    ),
                    "trace_bulk_projector_low_laplacian": (
                        self.mapping.collision.trace_bulk_projector_low_laplacian
                    ),
                    "trace_bulk_local_divergence_curve_type": (
                        self.mapping.collision.trace_bulk_local_divergence_curve_type
                    ),
                    "trace_bulk_local_divergence_curve_coefficients": (
                        self.mapping.collision.trace_bulk_local_divergence_curve_coefficients
                    ),
                    "trace_bulk_local_thermal_curve_type": (
                        self.mapping.collision.trace_bulk_local_thermal_curve_type
                    ),
                    "trace_bulk_local_thermal_curve_coefficients": (
                        self.mapping.collision.trace_bulk_local_thermal_curve_coefficients
                    ),
                    "trace_bulk_local_laplacian_curve_type": (
                        self.mapping.collision.trace_bulk_local_laplacian_curve_type
                    ),
                    "trace_bulk_local_laplacian_curve_coefficients": (
                        self.mapping.collision.trace_bulk_local_laplacian_curve_coefficients
                    ),
                    "deviatoric_stress_policy": self.mapping.collision.deviatoric_stress_policy,
                    "deviatoric_strain_rate_curve_type": (
                        self.mapping.collision.deviatoric_strain_rate_curve_type
                    ),
                    "deviatoric_strain_rate_curve_coefficients": (
                        self.mapping.collision.deviatoric_strain_rate_curve_coefficients
                    ),
                    "tau21": self.mapping.tau21,
                    "tau22": self.mapping.tau22,
                    "tau32": self.mapping.tau32,
                    "dispersion_correction_enabled": self.mapping.collision.dispersion_correction_enabled,
                    "dispersion_correction_low_laplacian": (
                        self.mapping.collision.dispersion_correction_low_laplacian
                    ),
                    "dispersion_correction_high_laplacian": (
                        self.mapping.collision.dispersion_correction_high_laplacian
                    ),
                    "regularized_shear_xy_factor": self.mapping.collision.regularized_shear_xy_factor,
                    "regularized_shear_normal_factor": self.mapping.collision.regularized_shear_normal_factor,
                    "regularized_shear_xy_dispersion_target": (
                        self.mapping.collision.regularized_shear_xy_dispersion_target
                    ),
                    "regularized_shear_normal_dispersion_target": (
                        self.mapping.collision.regularized_shear_normal_dispersion_target
                    ),
                    "regularized_heat_flux_factor_policy": (
                        self.mapping.collision.regularized_heat_flux_factor_policy
                    ),
                    "regularized_heat_flux_factor": self.mapping.collision.regularized_heat_flux_factor,
                    "regularized_heat_flux_dispersion_target": (
                        self.mapping.collision.regularized_heat_flux_dispersion_target
                    ),
                    "regularized_heat_flux_diagonal_low_mode_target": (
                        self.mapping.collision.regularized_heat_flux_diagonal_low_mode_target
                    ),
                    "regularized_heat_flux_f_fraction": self.mapping.collision.regularized_heat_flux_f_fraction,
                    "heat_flux_retention_policy": self.mapping.collision.heat_flux_retention_policy,
                    "heat_flux_retention_curve_type": self.mapping.collision.heat_flux_retention_curve_type,
                    "heat_flux_retention_curve_coefficients": (
                        self.mapping.collision.heat_flux_retention_curve_coefficients
                    ),
                    "conductive_heat_flux_moment_factor_policy": (
                        self.mapping.collision.conductive_heat_flux_moment_factor_policy
                    ),
                    "conductive_heat_flux_moment_factor": (
                        self.mapping.collision.conductive_heat_flux_moment_factor
                    ),
                    "conductive_heat_flux_dispersion_target": (
                        self.mapping.collision.conductive_heat_flux_dispersion_target
                    ),
                    "conductive_heat_flux_diagonal_low_mode_target": (
                        self.mapping.collision.conductive_heat_flux_diagonal_low_mode_target
                    ),
                    "conductive_heat_flux_galilean_correction_factor": (
                        self.mapping.collision.conductive_heat_flux_galilean_correction_factor
                    ),
                    "acoustic_phase_correction_enabled": (
                        self.mapping.collision.acoustic_phase_correction_enabled
                    ),
                    "acoustic_phase_correction_low_laplacian": (
                        self.mapping.collision.acoustic_phase_correction_low_laplacian
                    ),
                    "acoustic_phase_diagonal_low_mode_factor": (
                        self.mapping.collision.acoustic_phase_diagonal_low_mode_factor
                    ),
                    "acoustic_phase_high_mode_policy": (
                        self.mapping.collision.acoustic_phase_high_mode_policy
                    ),
                    "acoustic_phase_high_mode_factor": (
                        self.mapping.collision.acoustic_phase_high_mode_factor
                    ),
                    "acoustic_phase_high_mode_diagonal_factor": (
                        self.mapping.collision.acoustic_phase_high_mode_diagonal_factor
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
