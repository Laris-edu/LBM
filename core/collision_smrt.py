"""Conservative central-Hermite SMRT-style collision for Phase 2.

The implementation follows the per-cell energy-correction algorithm frozen in
the Phase 2 implementation plan.  Relaxation rates are supplied exclusively by
``core.unit_mapping`` through :class:`core.unit_mapping.UnitMapping`.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from core.equilibrium import equilibrium_fg
from core.dispersion_correction import (
    apply_periodic_diagonal_low_mode_correction,
    apply_periodic_spectral_correction,
)
from core.hermite import monomial_exponents
from core.lattice import Lattice, make_lattice
from core.macroscopic import ENERGY_CLOSURE_DEFINITION, central_energy_flux_lu, recover_macro
from core.unit_mapping import (
    DEVIATORIC_STRESS_POLICY_STRAIN_RATE_ISOTROPIC,
    TRACE_BULK_POLICY_CALIBRATED,
    TRACE_BULK_POLICY_CURRENT_ZERO,
    TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL,
    TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_ENTROPY_MANIFOLD,
    TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_LAPLACIAN,
    TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_PRESSURE_MEMORY,
    TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL,
    TRACE_BULK_POLICY_GHOST_ORTHOGONAL_SPECTRAL,
    TRACE_BULK_POLICY_TAU22,
    UnitMapping,
    deviatoric_strain_rate_factor_from_tau21,
    trace_bulk_local_divergence_factor_from_tau32,
    trace_bulk_local_laplacian_factor_from_tau32,
    trace_bulk_local_thermal_factor_from_tau32,
)


@dataclass
class CollisionDiagnostics:
    mass_residual: np.ndarray
    momentum_residual: np.ndarray
    energy_residual: np.ndarray
    min_f_post: float
    min_g_post: float
    clipping_used: bool = False


def _central_second_moment_matrix(lattice: Lattice, u: np.ndarray) -> np.ndarray:
    """Return rows for ``1, xi_y, xi_x, xi_y^2, xi_x xi_y, xi_x^2``."""

    xi = lattice.c - u[..., None, :]
    xi_x = xi[..., 0]
    xi_y = xi[..., 1]
    return np.stack(
        (
            np.ones_like(xi_x),
            xi_y,
            xi_x,
            xi_y * xi_y,
            xi_x * xi_y,
            xi_x * xi_x,
        ),
        axis=-2,
    )


def _weighted_minimum_norm_second_order_delta(
    delta_moments: np.ndarray,
    u: np.ndarray,
    lattice: Lattice,
) -> np.ndarray:
    """Project second-order central moments back to populations.

    This is the binomial/central-Hermite regularization step used for the
    current Phase 2 collision.  It reconstructs only the non-equilibrium
    second-order stress content, with zero density and momentum increments,
    while minimizing the weighted population norm set by the lattice weights.
    """

    basis = _central_second_moment_matrix(lattice, u)
    weighted_basis = basis * lattice.w
    gram = np.einsum("...ia,...ja->...ij", weighted_basis, basis)
    multipliers = np.linalg.solve(gram, delta_moments[..., None])[..., 0]
    return np.einsum("...ia,...i,a->...a", basis, multipliers, lattice.w)


@lru_cache(maxsize=None)
def _central_monomial_exponents(max_order: int) -> tuple[tuple[int, int], ...]:
    return tuple(monomial_exponents(max_order))


def _central_moment_matrix(
    lattice: Lattice,
    u: np.ndarray,
    *,
    max_order: int,
) -> np.ndarray:
    """Return central monomial rows through ``max_order``.

    Rows use ``xi_x^m xi_y^n`` ordering from :func:`monomial_exponents`.
    This is the explicit binomial transform used for high-order central
    relaxation; raw moments are never relaxed directly.
    """

    xi = lattice.c - u[..., None, :]
    xi_x = xi[..., 0]
    xi_y = xi[..., 1]
    rows = [xi_x**m * xi_y**n for m, n in _central_monomial_exponents(max_order)]
    return np.stack(rows, axis=-2)


def _central_moments(
    distribution: np.ndarray,
    u: np.ndarray,
    lattice: Lattice,
    *,
    max_order: int,
) -> np.ndarray:
    basis = _central_moment_matrix(lattice, u, max_order=max_order)
    return np.einsum("...a,...ia->...i", distribution, basis)


def _weighted_minimum_norm_central_delta(
    delta_moments: np.ndarray,
    u: np.ndarray,
    lattice: Lattice,
    *,
    max_order: int,
) -> np.ndarray:
    """Project central moments through ``max_order`` back to populations."""

    basis = _central_moment_matrix(lattice, u, max_order=max_order)
    weighted_basis = basis * lattice.w
    gram = np.einsum("...ia,...ja->...ij", weighted_basis, basis)
    multipliers = np.linalg.solve(gram, delta_moments[..., None])[..., 0]
    return np.einsum("...ia,...i,a->...a", basis, multipliers, lattice.w)


def _central_first_moment_matrix(lattice: Lattice, u: np.ndarray) -> np.ndarray:
    """Return rows for ``1, xi_y, xi_x``."""

    xi = lattice.c - u[..., None, :]
    xi_x = xi[..., 0]
    xi_y = xi[..., 1]
    return np.stack((np.ones_like(xi_x), xi_y, xi_x), axis=-2)


def _weighted_minimum_norm_first_order_delta(
    delta_moments: np.ndarray,
    u: np.ndarray,
    lattice: Lattice,
) -> np.ndarray:
    """Project g first-order central internal-energy flux to populations."""

    basis = _central_first_moment_matrix(lattice, u)
    weighted_basis = basis * lattice.w
    gram = np.einsum("...ia,...ja->...ij", weighted_basis, basis)
    multipliers = np.linalg.solve(gram, delta_moments[..., None])[..., 0]
    return np.einsum("...ia,...i,a->...a", basis, multipliers, lattice.w)


def _central_heat_flux_moment_matrix(lattice: Lattice, u: np.ndarray) -> np.ndarray:
    """Return rows fixing lower f moments plus third-order heat flux.

    Row order is ``1, xi_y, xi_x, xi_y^2, xi_x xi_y, xi_x^2,
    0.5|xi|^2 xi_y, 0.5|xi|^2 xi_x``.  The last two rows correspond to the
    translational central energy flux components, while the preceding rows
    force zero density, momentum and second-order stress increments.
    """

    xi = lattice.c - u[..., None, :]
    xi_x = xi[..., 0]
    xi_y = xi[..., 1]
    xi2 = xi_x * xi_x + xi_y * xi_y
    return np.stack(
        (
            np.ones_like(xi_x),
            xi_y,
            xi_x,
            xi_y * xi_y,
            xi_x * xi_y,
            xi_x * xi_x,
            0.5 * xi2 * xi_y,
            0.5 * xi2 * xi_x,
        ),
        axis=-2,
    )


def _weighted_minimum_norm_heat_flux_delta(
    delta_moments: np.ndarray,
    u: np.ndarray,
    lattice: Lattice,
) -> np.ndarray:
    """Project f third-order translational heat flux to populations."""

    basis = _central_heat_flux_moment_matrix(lattice, u)
    weighted_basis = basis * lattice.w
    gram = np.einsum("...ia,...ja->...ij", weighted_basis, basis)
    multipliers = np.linalg.solve(gram, delta_moments[..., None])[..., 0]
    return np.einsum("...ia,...i,a->...a", basis, multipliers, lattice.w)


def _central_translational_energy_flux_lu(
    f: np.ndarray,
    u: np.ndarray,
    lattice: Lattice,
) -> np.ndarray:
    xi = lattice.c - u[..., None, :]
    xi2 = np.sum(xi * xi, axis=-1)
    return 0.5 * np.einsum("...a,...a,...ai->...i", f, xi2, xi)


def _central_internal_energy_flux_lu(
    g: np.ndarray,
    u: np.ndarray,
    lattice: Lattice,
) -> np.ndarray:
    xi = lattice.c - u[..., None, :]
    return np.einsum("...a,...ai->...i", g, xi)


def _nonequilibrium_central_stress(
    f: np.ndarray,
    f_eq: np.ndarray,
    u: np.ndarray,
    lattice: Lattice,
) -> np.ndarray:
    xi = lattice.c - u[..., None, :]
    return np.einsum("...a,...ai,...aj->...ij", f - f_eq, xi, xi)


def _relaxed_trace_bulk_stress(trace_pre: np.ndarray, mapping: UnitMapping) -> np.ndarray:
    """Return post-collision trace stress for the configured trace/bulk channel."""

    policy = mapping.collision.trace_bulk_policy
    if policy in {
        TRACE_BULK_POLICY_CURRENT_ZERO,
        TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL,
        TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_LAPLACIAN,
        TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_PRESSURE_MEMORY,
        TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL,
        TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_ENTROPY_MANIFOLD,
        TRACE_BULK_POLICY_GHOST_ORTHOGONAL_SPECTRAL,
    }:
        return np.zeros_like(trace_pre)
    if policy in {TRACE_BULK_POLICY_TAU22, TRACE_BULK_POLICY_CALIBRATED}:
        trace_factor = mapping.collision.trace_bulk_scale * (1.0 - 1.0 / mapping.tau22)
        return trace_factor * trace_pre
    raise ValueError(f"unknown trace_bulk_policy: {policy}")


def _periodic_central_velocity_divergence(u: np.ndarray) -> np.ndarray:
    if u.ndim < 3 or u.shape[-1] != 2:
        raise ValueError("u must have shape (..., ny, nx, 2)")
    y_axis = u.ndim - 3
    x_axis = u.ndim - 2
    dux_dx = 0.5 * (
        np.roll(u[..., 0], -1, axis=x_axis)
        - np.roll(u[..., 0], 1, axis=x_axis)
    )
    duy_dy = 0.5 * (
        np.roll(u[..., 1], -1, axis=y_axis)
        - np.roll(u[..., 1], 1, axis=y_axis)
    )
    return dux_dx + duy_dy


def _strain_rate_deviatoric(u: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return periodic finite-difference deviatoric strain-rate components.

    Returns ``(normal_dev, shear)`` where ``normal_dev = du_x/dx - du_y/dy`` and
    ``shear = du_x/dy + du_y/dx``.  These are the two independent traceless
    strain-rate combinations; both follow from a single isotropic shear
    viscosity, so reconstructing the deviatoric stress from them removes the
    transverse/longitudinal anisotropy of the measured central-moment closure.
    """

    if u.ndim < 3 or u.shape[-1] != 2:
        raise ValueError("u must have shape (..., ny, nx, 2)")
    y_axis = u.ndim - 3
    x_axis = u.ndim - 2
    dux_dx = 0.5 * (np.roll(u[..., 0], -1, axis=x_axis) - np.roll(u[..., 0], 1, axis=x_axis))
    duy_dy = 0.5 * (np.roll(u[..., 1], -1, axis=y_axis) - np.roll(u[..., 1], 1, axis=y_axis))
    dux_dy = 0.5 * (np.roll(u[..., 0], -1, axis=y_axis) - np.roll(u[..., 0], 1, axis=y_axis))
    duy_dx = 0.5 * (np.roll(u[..., 1], -1, axis=x_axis) - np.roll(u[..., 1], 1, axis=x_axis))
    return dux_dx - duy_dy, dux_dy + duy_dx


def _periodic_laplacian_scalar(field: np.ndarray) -> np.ndarray:
    y_axis = field.ndim - 2
    x_axis = field.ndim - 1
    return (
        np.roll(field, 1, axis=y_axis)
        + np.roll(field, -1, axis=y_axis)
        + np.roll(field, 1, axis=x_axis)
        + np.roll(field, -1, axis=x_axis)
        - 4.0 * field
    )


def _entropy_manifold_thermal_divergence(
    rho: np.ndarray,
    theta: np.ndarray,
    mapping: UnitMapping,
) -> np.ndarray:
    gamma = float(mapping.physical.gamma)
    rho_ref = float(mapping.lattice.rho_ref_lu)
    theta_ref = float(mapping.theta_ref_lu)
    entropy_linear = (theta - theta_ref) / theta_ref - (gamma - 1.0) * (rho - rho_ref) / rho_ref
    return (mapping.alpha_lu / gamma) * _periodic_laplacian_scalar(entropy_linear)


def _local_hydrodynamic_trace_stress(
    rho: np.ndarray,
    theta: np.ndarray,
    u: np.ndarray,
    mapping: UnitMapping,
    pressure_divergence: np.ndarray | None = None,
) -> np.ndarray:
    divergence_coefficient = trace_bulk_local_divergence_factor_from_tau32(
        mapping.tau32,
        curve_type=mapping.collision.trace_bulk_local_divergence_curve_type,
        coefficients=mapping.collision.trace_bulk_local_divergence_curve_coefficients,
    )
    policy = mapping.collision.trace_bulk_policy
    if policy == TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_PRESSURE_MEMORY:
        if pressure_divergence is None:
            raise ValueError(
                "ghost_orthogonal_local_pressure_memory requires pressure_divergence"
            )
        divergence = np.asarray(pressure_divergence, dtype=float)
        divergence = divergence_coefficient * divergence
    elif policy == TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL:
        if pressure_divergence is None:
            raise ValueError(
                "ghost_orthogonal_local_two_channel requires pressure_divergence"
            )
        acoustic_divergence = np.asarray(pressure_divergence, dtype=float)
        velocity_divergence = _periodic_central_velocity_divergence(u)
        thermal_coefficient = trace_bulk_local_thermal_factor_from_tau32(
            mapping.tau32,
            curve_type=mapping.collision.trace_bulk_local_thermal_curve_type,
            coefficients=mapping.collision.trace_bulk_local_thermal_curve_coefficients,
        )
        divergence = (
            divergence_coefficient * acoustic_divergence
            + thermal_coefficient * (velocity_divergence - acoustic_divergence)
        )
    elif policy == TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_ENTROPY_MANIFOLD:
        velocity_divergence = _periodic_central_velocity_divergence(u)
        thermal_divergence = _entropy_manifold_thermal_divergence(rho, theta, mapping)
        acoustic_divergence = velocity_divergence - thermal_divergence
        laplacian_coefficient = trace_bulk_local_laplacian_factor_from_tau32(
            mapping.tau32,
            curve_type=mapping.collision.trace_bulk_local_laplacian_curve_type,
            coefficients=mapping.collision.trace_bulk_local_laplacian_curve_coefficients,
        )
        thermal_coefficient = trace_bulk_local_thermal_factor_from_tau32(
            mapping.tau32,
            curve_type=mapping.collision.trace_bulk_local_thermal_curve_type,
            coefficients=mapping.collision.trace_bulk_local_thermal_curve_coefficients,
        )
        divergence = (
            divergence_coefficient * acoustic_divergence
            - laplacian_coefficient * _periodic_laplacian_scalar(acoustic_divergence)
            + thermal_coefficient * thermal_divergence
        )
    elif policy == TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_LAPLACIAN:
        divergence = _periodic_central_velocity_divergence(u)
        laplacian_coefficient = trace_bulk_local_laplacian_factor_from_tau32(
            mapping.tau32,
            curve_type=mapping.collision.trace_bulk_local_laplacian_curve_type,
            coefficients=mapping.collision.trace_bulk_local_laplacian_curve_coefficients,
        )
        divergence = (
            divergence_coefficient * divergence
            - laplacian_coefficient * _periodic_laplacian_scalar(divergence)
        )
    else:
        divergence = _periodic_central_velocity_divergence(u)
        divergence = divergence_coefficient * divergence
    return rho * theta * divergence


def _regularized_f_collision(
    f: np.ndarray,
    f_eq: np.ndarray,
    u: np.ndarray,
    mapping: UnitMapping,
    lattice: Lattice,
    *,
    rho: np.ndarray | None = None,
    theta: np.ndarray | None = None,
    pressure_divergence: np.ndarray | None = None,
) -> np.ndarray:
    """Relax central f moments through fourth order.

    The previous scaffold relaxed every population-space non-equilibrium
    component with ``tau21``.  For cold physical-timestep mappings this allowed
    high-order population noise to drive the translational central energy
    negative.  This regularized form relaxes hydrodynamic second-order stress
    and explicitly damps third/fourth central ghost content through the same
    binomial transform instead of leaving it to the minimum-norm nullspace.
    """

    stress = _nonequilibrium_central_stress(f, f_eq, u, lattice)
    stress_xy = apply_periodic_spectral_correction(
        stress[..., 0, 1],
        enabled=mapping.collision.dispersion_correction_enabled,
        target=mapping.collision.regularized_shear_xy_dispersion_target,
        low_laplacian=mapping.collision.dispersion_correction_low_laplacian,
        high_laplacian=mapping.collision.dispersion_correction_high_laplacian,
    )
    stress_dev = apply_periodic_spectral_correction(
        stress[..., 0, 0] - stress[..., 1, 1],
        enabled=mapping.collision.dispersion_correction_enabled,
        target=mapping.collision.regularized_shear_normal_dispersion_target,
        low_laplacian=mapping.collision.dispersion_correction_low_laplacian,
        high_laplacian=mapping.collision.dispersion_correction_high_laplacian,
    )
    omega_shear = 1.0 / mapping.tau21
    shear_factor = 1.0 - omega_shear
    xy_factor = mapping.collision.regularized_shear_xy_factor
    normal_factor = mapping.collision.regularized_shear_normal_factor

    # The default current_zero branch preserves the D2Q37 transport-candidate
    # baseline.  tau22/calibrated are explicit diagnostic/candidate channels.
    trace = stress[..., 0, 0] + stress[..., 1, 1]
    if mapping.collision.trace_bulk_policy in {
        TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL,
        TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_LAPLACIAN,
        TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_PRESSURE_MEMORY,
        TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL,
        TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_ENTROPY_MANIFOLD,
    }:
        if rho is None or theta is None:
            raise ValueError("ghost_orthogonal_local trace policy requires rho and theta")
        trace_post = _local_hydrodynamic_trace_stress(
            rho,
            theta,
            u,
            mapping,
            pressure_divergence=pressure_divergence,
        )
    else:
        trace_post = _relaxed_trace_bulk_stress(trace, mapping)
    if mapping.collision.deviatoric_stress_policy == DEVIATORIC_STRESS_POLICY_STRAIN_RATE_ISOTROPIC:
        if rho is None or theta is None:
            raise ValueError("strain_rate_isotropic deviatoric policy requires rho and theta")
        g_dev = deviatoric_strain_rate_factor_from_tau21(
            mapping.tau21,
            curve_type=mapping.collision.deviatoric_strain_rate_curve_type,
            coefficients=mapping.collision.deviatoric_strain_rate_curve_coefficients,
        )
        normal_dev, shear_rate = _strain_rate_deviatoric(u)
        rho_theta = rho * theta
        # Reconstruct both deviatoric stress components directly from the strain
        # rate.  ``normal_factor``/``xy_factor`` carry the fixed lattice
        # geometric ratio between the (xx-yy) and xy channels (the same lattice
        # anisotropy the measured closure compensates); ``g_dev`` is the single
        # isotropic shear-viscosity knob shared by both channels, so transverse
        # and longitudinal deviatoric viscosity follow from one mu.
        dev_post = g_dev * normal_factor * rho_theta * normal_dev
        xy_post = g_dev * xy_factor * rho_theta * shear_rate
    else:
        dev_post = normal_factor * shear_factor * stress_dev
        xy_post = xy_factor * shear_factor * stress_xy
    delta_xx = 0.5 * (trace_post + dev_post)
    delta_yy = 0.5 * (trace_post - dev_post)
    zeros = np.zeros_like(delta_xx)

    if mapping.collision.central_moment_closure == "second_order":
        delta_moments_second = np.stack(
            (
                zeros,
                zeros,
                zeros,
                delta_yy,
                xy_post,
                delta_xx,
            ),
            axis=-1,
        )
        return f_eq + _weighted_minimum_norm_second_order_delta(delta_moments_second, u, lattice)

    noneq_central = _central_moments(f - f_eq, u, lattice, max_order=4)
    high_tau = mapping.collision.high_order_relaxation
    high_order_factor = 1.0 - 1.0 / high_tau
    delta_moments = np.zeros_like(noneq_central)
    for index, exponent in enumerate(_central_monomial_exponents(4)):
        if exponent == (0, 2):
            delta_moments[..., index] = delta_yy
        elif exponent == (1, 1):
            delta_moments[..., index] = xy_post
        elif exponent == (2, 0):
            delta_moments[..., index] = delta_xx
        elif sum(exponent) == 4:
            delta_moments[..., index] = high_order_factor * noneq_central[..., index]
    return f_eq + _weighted_minimum_norm_central_delta(delta_moments, u, lattice, max_order=4)


def _regularized_heat_flux_collision(
    f_post: np.ndarray,
    g_eq: np.ndarray,
    f_before: np.ndarray,
    g_before: np.ndarray,
    u: np.ndarray,
    mapping: UnitMapping,
    lattice: Lattice,
) -> tuple[np.ndarray, np.ndarray]:
    """Apply regularized total heat-flux content before energy correction.

    ``f`` carries the third-order central translational energy flux and ``g``
    carries the first-order central internal-energy flux.  The split is stored
    in :mod:`core.unit_mapping` so the collision implementation does not hide a
    transport mapping decision.
    """

    heat_flux_factor = mapping.collision.regularized_heat_flux_factor
    if heat_flux_factor == 0.0:
        return f_post, g_eq.copy()

    total_heat_flux = central_energy_flux_lu(f_before, g_before, u=u, lattice=lattice)
    total_heat_flux = apply_periodic_spectral_correction(
        total_heat_flux,
        enabled=mapping.collision.dispersion_correction_enabled,
        target=mapping.collision.regularized_heat_flux_dispersion_target,
        low_laplacian=mapping.collision.dispersion_correction_low_laplacian,
        high_laplacian=mapping.collision.dispersion_correction_high_laplacian,
    )
    total_heat_flux = apply_periodic_diagonal_low_mode_correction(
        total_heat_flux,
        enabled=mapping.collision.dispersion_correction_enabled,
        target=mapping.collision.regularized_heat_flux_diagonal_low_mode_target,
        low_laplacian=mapping.collision.dispersion_correction_low_laplacian,
    )
    target_heat_flux = heat_flux_factor * total_heat_flux
    f_fraction = mapping.collision.regularized_heat_flux_f_fraction
    if mapping.collision.central_moment_closure == "fourth_order":
        f_heat_flux = f_fraction * target_heat_flux - _central_translational_energy_flux_lu(
            f_post,
            u,
            lattice,
        )
        g_heat_flux = (1.0 - f_fraction) * target_heat_flux - _central_internal_energy_flux_lu(
            g_eq,
            u,
            lattice,
        )
    else:
        f_heat_flux = f_fraction * target_heat_flux
        g_heat_flux = (1.0 - f_fraction) * target_heat_flux

    zeros = np.zeros_like(f_heat_flux[..., 0])
    f_delta_moments = np.stack(
        (
            zeros,
            zeros,
            zeros,
            zeros,
            zeros,
            zeros,
            f_heat_flux[..., 1],
            f_heat_flux[..., 0],
        ),
        axis=-1,
    )
    f_with_heat_flux = f_post + _weighted_minimum_norm_heat_flux_delta(f_delta_moments, u, lattice)

    g_delta_moments = np.stack((zeros, g_heat_flux[..., 1], g_heat_flux[..., 0]), axis=-1)
    g_with_heat_flux = g_eq + _weighted_minimum_norm_first_order_delta(g_delta_moments, u, lattice)
    return f_with_heat_flux, g_with_heat_flux


def _correct_f_conserved_moments(
    f_post: np.ndarray,
    f_before: np.ndarray,
    lattice: Lattice,
) -> np.ndarray:
    rho_before = np.sum(f_before, axis=-1)
    rho_after = np.sum(f_post, axis=-1)
    corrected = f_post + (rho_before - rho_after)[..., None] * lattice.w
    momentum_before = np.einsum("...a,ai->...i", f_before, lattice.c)
    momentum_after = np.einsum("...a,ai->...i", corrected, lattice.c)
    dm = momentum_before - momentum_after
    cx = lattice.c[:, 0]
    cy = lattice.c[:, 1]
    denom_x = float(np.sum(lattice.w * cx * cx))
    denom_y = float(np.sum(lattice.w * cy * cy))
    corrected = corrected + (dm[..., 0, None] * lattice.w * cx / denom_x)
    return corrected + (dm[..., 1, None] * lattice.w * cy / denom_y)


def collide_fg(
    f: np.ndarray,
    g: np.ndarray,
    mapping: UnitMapping,
    *,
    lattice: Lattice | None = None,
    trace_bulk_pressure_divergence: np.ndarray | None = None,
    return_diagnostics: bool = False,
) -> tuple[np.ndarray, np.ndarray] | tuple[np.ndarray, np.ndarray, CollisionDiagnostics]:
    """Collide ``f`` and ``g`` while conserving mass, momentum and total energy.

    Per-cell algorithm:

    1. Recover pre-collision macro state and selected central total energy.
    2. Build ``f_eq`` and ``g_eq`` from the same macro state.
    3. Relax central-Hermite f stress content with ``tau21`` and discard
       unrelated higher-order non-equilibrium content.
    4. Reconstruct f third-order central translational energy flux and g
       first-order central internal-energy flux from the configured
       heat-flux retention factor.
    5. Correct the zero moment of g by adding ``delta_G * w_a`` so the selected
       central total energy is exactly conserved per cell.
    """

    lattice = lattice or make_lattice()
    f = np.asarray(f, dtype=float)
    g = np.asarray(g, dtype=float)
    macro_before = recover_macro(f, g, D=mapping.lattice.D, S=mapping.lattice.S, lattice=lattice)
    f_eq, g_eq = equilibrium_fg(
        macro_before.rho,
        macro_before.u,
        macro_before.theta,
        mapping.lattice.S,
        lattice,
    )

    f_post = _regularized_f_collision(
        f,
        f_eq,
        macro_before.u,
        mapping,
        lattice,
        rho=macro_before.rho,
        theta=macro_before.theta,
        pressure_divergence=trace_bulk_pressure_divergence,
    )
    f_post = _correct_f_conserved_moments(f_post, f, lattice)

    f_post, g_shape = _regularized_heat_flux_collision(
        f_post,
        g_eq,
        f,
        g,
        macro_before.u,
        mapping,
        lattice,
    )
    f_post = _correct_f_conserved_moments(f_post, f, lattice)

    macro_mid = recover_macro(f_post, g_shape, D=mapping.lattice.D, S=mapping.lattice.S, lattice=lattice)
    delta_G = macro_before.E_tot - macro_mid.E_tot
    g_post = g_shape + delta_G[..., None] * lattice.w

    if not return_diagnostics:
        return f_post, g_post

    macro_after = recover_macro(f_post, g_post, D=mapping.lattice.D, S=mapping.lattice.S, lattice=lattice)
    mass_residual = np.sum(f_post - f, axis=-1)
    momentum_residual = np.einsum("...a,ai->...i", f_post - f, lattice.c)
    energy_residual = macro_after.E_tot - macro_before.E_tot
    diagnostics = CollisionDiagnostics(
        mass_residual=mass_residual,
        momentum_residual=momentum_residual,
        energy_residual=energy_residual,
        min_f_post=float(np.min(f_post)),
        min_g_post=float(np.min(g_post)),
        clipping_used=False,
    )
    return f_post, g_post, diagnostics


def assert_collision_conservation(
    f: np.ndarray,
    g: np.ndarray,
    mapping: UnitMapping,
    *,
    tol: float = 1.0e-12,
    lattice: Lattice | None = None,
) -> None:
    _, _, diagnostics = collide_fg(f, g, mapping, lattice=lattice, return_diagnostics=True)
    if np.max(np.abs(diagnostics.mass_residual)) > tol:
        raise AssertionError("collision mass conservation failed")
    if np.max(np.abs(diagnostics.momentum_residual)) > tol:
        raise AssertionError("collision momentum conservation failed")
    if np.max(np.abs(diagnostics.energy_residual)) > tol:
        raise AssertionError(f"{ENERGY_CLOSURE_DEFINITION} conservation failed")
