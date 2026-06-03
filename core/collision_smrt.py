"""Conservative central-Hermite SMRT-style collision for Phase 2.

The implementation follows the per-cell energy-correction algorithm frozen in
the Phase 2 implementation plan.  Relaxation rates are supplied exclusively by
``core.unit_mapping`` through :class:`core.unit_mapping.UnitMapping`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from core.equilibrium import equilibrium_fg
from core.lattice_d2q21 import LatticeD2Q21, make_d2q21
from core.macroscopic import ENERGY_CLOSURE_DEFINITION, central_energy_flux_lu, recover_macro
from core.unit_mapping import UnitMapping


@dataclass
class CollisionDiagnostics:
    mass_residual: np.ndarray
    momentum_residual: np.ndarray
    energy_residual: np.ndarray
    min_f_post: float
    min_g_post: float
    clipping_used: bool = False


def _central_second_moment_matrix(lattice: LatticeD2Q21, u: np.ndarray) -> np.ndarray:
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
    lattice: LatticeD2Q21,
) -> np.ndarray:
    """Project second-order central moments back to populations.

    This is the binomial/central-Hermite regularization step used for the
    current Phase 2 D2Q21 collision.  It reconstructs only the non-equilibrium
    second-order stress content, with zero density and momentum increments,
    while minimizing the weighted population norm set by the lattice weights.
    """

    basis = _central_second_moment_matrix(lattice, u)
    weighted_basis = basis * lattice.w
    gram = np.einsum("...ia,...ja->...ij", weighted_basis, basis)
    multipliers = np.linalg.solve(gram, delta_moments[..., None])[..., 0]
    return np.einsum("...ia,...i,a->...a", basis, multipliers, lattice.w)


def _central_first_moment_matrix(lattice: LatticeD2Q21, u: np.ndarray) -> np.ndarray:
    """Return rows for ``1, xi_y, xi_x``."""

    xi = lattice.c - u[..., None, :]
    xi_x = xi[..., 0]
    xi_y = xi[..., 1]
    return np.stack((np.ones_like(xi_x), xi_y, xi_x), axis=-2)


def _weighted_minimum_norm_first_order_delta(
    delta_moments: np.ndarray,
    u: np.ndarray,
    lattice: LatticeD2Q21,
) -> np.ndarray:
    """Project g first-order central internal-energy flux to populations."""

    basis = _central_first_moment_matrix(lattice, u)
    weighted_basis = basis * lattice.w
    gram = np.einsum("...ia,...ja->...ij", weighted_basis, basis)
    multipliers = np.linalg.solve(gram, delta_moments[..., None])[..., 0]
    return np.einsum("...ia,...i,a->...a", basis, multipliers, lattice.w)


def _central_heat_flux_moment_matrix(lattice: LatticeD2Q21, u: np.ndarray) -> np.ndarray:
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
    lattice: LatticeD2Q21,
) -> np.ndarray:
    """Project f third-order translational heat flux to populations."""

    basis = _central_heat_flux_moment_matrix(lattice, u)
    weighted_basis = basis * lattice.w
    gram = np.einsum("...ia,...ja->...ij", weighted_basis, basis)
    multipliers = np.linalg.solve(gram, delta_moments[..., None])[..., 0]
    return np.einsum("...ia,...i,a->...a", basis, multipliers, lattice.w)


def _nonequilibrium_central_stress(
    f: np.ndarray,
    f_eq: np.ndarray,
    u: np.ndarray,
    lattice: LatticeD2Q21,
) -> np.ndarray:
    xi = lattice.c - u[..., None, :]
    return np.einsum("...a,...ai,...aj->...ij", f - f_eq, xi, xi)


def _regularized_f_collision(
    f: np.ndarray,
    f_eq: np.ndarray,
    u: np.ndarray,
    mapping: UnitMapping,
    lattice: LatticeD2Q21,
) -> np.ndarray:
    """Relax the central second-order non-equilibrium stress.

    The previous scaffold relaxed every population-space non-equilibrium
    component with ``tau21``.  For cold physical-timestep mappings this allowed
    high-order population noise to drive the translational central energy
    negative.  This regularized form keeps only the stress content that controls
    shear transport and removes higher-order non-equilibrium content.
    """

    stress = _nonequilibrium_central_stress(f, f_eq, u, lattice)
    omega_shear = 1.0 / mapping.tau21
    shear_factor = 1.0 - omega_shear
    xy_factor = mapping.collision.regularized_shear_xy_factor
    normal_factor = mapping.collision.regularized_shear_normal_factor

    # Baseline bulk policy is diagnostic_zero.  For the regularized shear-wave
    # path we remove trace non-equilibrium content instead of over-relaxing it
    # with tau22=0.5, which was the dominant source of negative K_tr growth.
    trace_post = np.zeros_like(stress[..., 0, 0])
    dev_post = normal_factor * shear_factor * (stress[..., 0, 0] - stress[..., 1, 1])
    xy_post = xy_factor * shear_factor * stress[..., 0, 1]
    delta_xx = 0.5 * (trace_post + dev_post)
    delta_yy = 0.5 * (trace_post - dev_post)
    zeros = np.zeros_like(delta_xx)
    delta_moments = np.stack(
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
    return f_eq + _weighted_minimum_norm_second_order_delta(delta_moments, u, lattice)


def _regularized_heat_flux_collision(
    f_post: np.ndarray,
    g_eq: np.ndarray,
    f_before: np.ndarray,
    g_before: np.ndarray,
    u: np.ndarray,
    mapping: UnitMapping,
    lattice: LatticeD2Q21,
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
    target_heat_flux = heat_flux_factor * total_heat_flux
    f_fraction = mapping.collision.regularized_heat_flux_f_fraction
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
    lattice: LatticeD2Q21,
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
    lattice: LatticeD2Q21 | None = None,
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

    lattice = lattice or make_d2q21()
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

    f_post = _regularized_f_collision(f, f_eq, macro_before.u, mapping, lattice)
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
    lattice: LatticeD2Q21 | None = None,
) -> None:
    _, _, diagnostics = collide_fg(f, g, mapping, lattice=lattice, return_diagnostics=True)
    if np.max(np.abs(diagnostics.mass_residual)) > tol:
        raise AssertionError("collision mass conservation failed")
    if np.max(np.abs(diagnostics.momentum_residual)) > tol:
        raise AssertionError("collision momentum conservation failed")
    if np.max(np.abs(diagnostics.energy_residual)) > tol:
        raise AssertionError(f"{ENERGY_CLOSURE_DEFINITION} conservation failed")
