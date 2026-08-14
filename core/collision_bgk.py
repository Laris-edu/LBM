"""Diagnostic BGK collision for the cross-stack universality unit 1a (D0-7).

WHY THIS FILE EXISTS
--------------------
Every piece of evidence for the finite-bias tangent artifact (WP4-JAB ->
A2-5 -> wallfix counter-proof -> ghost-relaxation scan) was measured on ONE
collision stack: ``core/collision_smrt.py``'s
``SMRT_central_Hermite_regularized_stress`` (RR closure).  The reviewer
question "is this a general trap or a property of your operator?" cannot be
answered from inside that stack.  This module supplies the most standard
possible independent collision operator -- BGK/SRT -- on the SAME lattice,
SAME equilibrium, SAME wall, SAME geometry, so the artifact can be re-measured
with the collision structure swapped out.

The production operator is NOT touched: ``core/collision_smrt.py`` is
byte-for-byte unchanged and this module is never imported by it or by
``core/solver.py``.  Selection happens explicitly at the diagnostic call site
(``core/tangent_bgk.BgkGasSolver2D``).

THE OPERATOR
------------
Two relaxation times, one per population::

    f_post = f - (f - f_eq) / tau_f          (mass, momentum, translational E)
    g_post = g - (g - g_eq) / tau_g          (internal energy of the S extra DOF)

with ``f_eq``/``g_eq`` from the frozen ``core.equilibrium.equilibrium_fg``
(identical to production -- the equilibrium is NOT the axis under test).
Unlike the production operator this relaxes EVERY non-equilibrium central
moment -- second, third, fourth and every ghost moment the lattice carries --
at the single rate ``1/tau``; no strain-rate reconstruction, no ghost-orthogonal
trace projector, no dispersion correction, no per-moment calibration factors.
That is the structural difference the unit is measuring.

CONSERVATIVE CLOSING (identical convention to production, not an extra model)
---------------------------------------------------------------------------
``equilibrium_fg`` matches the raw Gaussian moments exactly, so BGK conserves
mass and momentum to round-off; ``_correct_f_conserved_moments`` (the SAME
production helper) pins them exactly, as in ``collide_fg``.

Total energy needs one more term.  With ``E_tot = 0.5*sum_a f_a |c_a|^2 +
sum_a g_a`` (the closure definition used by the whole stack, including the band
bookkeeping) the two populations exchange energy whenever ``tau_f != tau_g``::

    E_post - E = (K - K_eq) * (1/tau_g - 1/tau_f),   K - K_eq = -(G - G_eq)

so a bare two-relaxation-time f-g BGK is NOT total-energy conserving.  Every
double-distribution polyatomic model closes this the same way; we close it with
the SAME device production uses -- a uniform ``delta_G * w_a`` shift of ``g``
(``collide_fg`` step 5).  Consequences, all deliberate:

  * total energy is conserved EXACTLY per cell (the V5 energy-account audit and
    the exact band bookkeeping stay meaningful and unchanged);
  * ``delta_G`` has zero first moment (``sum_a w_a c_a = 0``), so it does not
    touch either heat-flux channel -- the transport derivation below is
    unaffected;
  * translational/internal equipartition then relaxes at ``1/tau_f`` rather
    than ``1/tau_g``; the internal-energy FLUX still relaxes at ``1/tau_g``.

TRANSPORT (analytic; measured against a mode-decay probe before any hot run)
---------------------------------------------------------------------------
Chapman-Enskog for this f-g pair at ``u -> 0`` on the conduction problem
(``rho*theta = p`` locally isobaric), in lattice units with the standard
discrete -1/2 shift:

  shear viscosity     nu    = theta_t * (tau_f - 1/2)
  translational k     k_tr  = (D+2)/2 * rho*theta * (tau_f - 1/2)
  internal k          k_int = S/2     * rho*theta * (tau_g - 1/2)
  thermal diffusivity alpha = k/(rho*c_p),  c_p = (D+S+2)/2
                            = theta_t * [ (D+2)(tau_f-1/2) + S(tau_g-1/2) ]
                              / (D+S+2)

Inverting those two relations gives the (tau_f, tau_g) that put BGK on the SAME
PHYSICAL PROBLEM as the production stack -- identical ``nu_lu`` and identical
``alpha_lu``, hence identical thermal penetration depth and identical
``H_s/delta_T`` at the frozen geometry.  Nothing is tuned to make an answer come
out: the pair is DERIVED from the frozen mapping (``bgk_params_matching``).

DIAGNOSTIC ONLY (D0-7): no production validity claim, no gate claim.  The BGK
rows are a cross-stack control, never a proposed configuration.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from core.collision_smrt import CollisionDiagnostics, _correct_f_conserved_moments
from core.equilibrium import equilibrium_fg
from core.lattice import Lattice, make_lattice
from core.macroscopic import ENERGY_CLOSURE_DEFINITION, recover_macro
from core.unit_mapping import UnitMapping

__all__ = [
    "BGK_MODEL_NAME",
    "BgkParams",
    "bgk_params_from_transport",
    "bgk_params_matching",
    "bgk_relax",
    "collide_fg_bgk",
    "assert_bgk_conservation",
]

BGK_MODEL_NAME = "BGK_two_relaxation_time_fg_diagnostic"

# tau must exceed 1/2 for positive transport; the guard is a hard failure, not
# a clamp (no silent repair anywhere in this project).
TAU_FLOOR = 0.5


@dataclass(frozen=True)
class BgkParams:
    """Relaxation times of the diagnostic BGK operator + their transport.

    ``theta_transport_lu``, ``D`` and ``S`` come from the frozen
    :class:`core.unit_mapping.UnitMapping`; this class never re-derives a unit
    mapping (PROJECT_CONTEXT rule: ``core/unit_mapping.py`` is the only entry
    for transport mapping).  It only inverts the BGK Chapman-Enskog relations
    documented in the module docstring.
    """

    tau_f: float
    tau_g: float
    theta_transport_lu: float
    D: int = 2
    S: int = 3

    def __post_init__(self) -> None:
        for name in ("tau_f", "tau_g"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value <= TAU_FLOOR:
                raise ValueError(
                    f"BGK {name}={value!r} must be finite and > {TAU_FLOOR} "
                    "(tau <= 1/2 is negative transport)"
                )
        if float(self.theta_transport_lu) <= 0.0:
            raise ValueError("theta_transport_lu must be positive")

    # -- transport (analytic; module docstring carries the derivation) --
    @property
    def nu_lu(self) -> float:
        return float(self.theta_transport_lu) * (float(self.tau_f) - 0.5)

    @property
    def alpha_lu(self) -> float:
        d, s = int(self.D), int(self.S)
        return float(self.theta_transport_lu) * (
            (d + 2) * (float(self.tau_f) - 0.5) + s * (float(self.tau_g) - 0.5)
        ) / (d + s + 2)

    @property
    def Pr_lu(self) -> float:
        return self.nu_lu / self.alpha_lu

    # -- structural read-outs (reported, never gated) --
    @property
    def retention_f(self) -> float:
        """1 - 1/tau_f: the factor every f non-equilibrium moment survives with.

        For the production stack the corresponding number exists only for the
        ghost sector (``fourth_order``'s ``1 - 1/high_tau``); here it applies to
        the WHOLE non-equilibrium content, which is exactly the structural
        difference under test.
        """

        return 1.0 - 1.0 / float(self.tau_f)

    @property
    def retention_g(self) -> float:
        return 1.0 - 1.0 / float(self.tau_g)

    def as_dict(self) -> dict[str, float | int | str]:
        return {
            "model": BGK_MODEL_NAME,
            "tau_f": float(self.tau_f),
            "tau_g": float(self.tau_g),
            "theta_transport_lu": float(self.theta_transport_lu),
            "D": int(self.D),
            "S": int(self.S),
            "nu_lu": self.nu_lu,
            "alpha_lu": self.alpha_lu,
            "Pr_lu": self.Pr_lu,
            "retention_f": self.retention_f,
            "retention_g": self.retention_g,
        }


def bgk_params_from_transport(nu_lu: float, alpha_lu: float,
                              theta_transport_lu: float,
                              *, D: int = 2, S: int = 3) -> BgkParams:
    """Invert the BGK transport relations for (tau_f, tau_g).

    Fails loudly if the requested (nu, alpha) pair is outside the model's
    reach (tau <= 1/2) instead of clamping to a "nearest feasible" answer --
    a clamped pair would silently put BGK on a DIFFERENT physical problem,
    which is the one thing this unit must not do.
    """

    theta_t = float(theta_transport_lu)
    if theta_t <= 0.0:
        raise ValueError("theta_transport_lu must be positive")
    d, s = int(D), int(S)
    tau_f = 0.5 + float(nu_lu) / theta_t
    tau_g = 0.5 + ((d + s + 2) * float(alpha_lu) / theta_t
                   - (d + 2) * (tau_f - 0.5)) / s
    return BgkParams(tau_f=tau_f, tau_g=tau_g, theta_transport_lu=theta_t,
                     D=d, S=s)


def bgk_params_matching(mapping: UnitMapping) -> BgkParams:
    """The BGK pair that reproduces the frozen mapping's nu_lu and alpha_lu.

    This is the ONLY (tau_f, tau_g) the unit runs: derived, never tuned.  Same
    nu and same alpha => same delta_T => same H_s/delta_T at the frozen
    geometry, so the BGK rig poses the same physical problem as production.
    """

    return bgk_params_from_transport(
        float(mapping.nu_lu), float(mapping.alpha_lu),
        float(mapping.theta_transport_lu),
        D=int(mapping.lattice.D), S=int(mapping.lattice.S))


def bgk_relax(f: np.ndarray, g: np.ndarray, f_eq: np.ndarray, g_eq: np.ndarray,
              params: BgkParams, lattice: Lattice,
              *, c2: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """BGK relaxation + conservative closing, EXACTLY LINEAR in its arguments.

    Linearity is structural (relaxation, moment pinning and the delta_G shift
    are all linear maps), and it is what lets the tangent chain apply this
    block exactly instead of by finite difference -- the same convention the
    frozen instrument uses for its exactly-linear stages (stream, filter).
    The contract tests assert both the linearity and the conservation.

    ``delta_G`` is written directly as the energy defect
    ``0.5*sum((f-f_post)|c|^2) + sum(g-g_shape)``.  This is algebraically the
    production expression ``E_tot(before) - E_tot(mid)`` with the
    ``0.5*rho|u|^2`` cancellation done on paper rather than in floating point,
    which is what makes the block exactly linear (and exactly conservative)
    instead of conservative-to-round-off.
    """

    if c2 is None:
        c2 = np.sum(np.asarray(lattice.c, dtype=float) ** 2, axis=-1)
    ret_f = params.retention_f
    ret_g = params.retention_g
    f_shape = f_eq + ret_f * (f - f_eq)
    f_post = _correct_f_conserved_moments(f_shape, f, lattice)
    g_shape = g_eq + ret_g * (g - g_eq)
    delta_g = (0.5 * np.sum((f - f_post) * c2, axis=-1)
               + np.sum(g - g_shape, axis=-1))
    g_post = g_shape + delta_g[..., None] * lattice.w
    return f_post, g_post


def collide_fg_bgk(
    f: np.ndarray,
    g: np.ndarray,
    mapping: UnitMapping,
    params: BgkParams,
    *,
    lattice: Lattice | None = None,
    return_diagnostics: bool = False,
) -> tuple[np.ndarray, np.ndarray] | tuple[np.ndarray, np.ndarray, CollisionDiagnostics]:
    """One BGK collision step; signature mirrors ``collide_fg``.

    ``mapping`` supplies only D/S and the lattice metadata -- every relaxation
    rate comes from ``params``.  The pre-collision macro recovery and the
    equilibrium construction are the production functions, unchanged.
    """

    lattice = lattice or make_lattice()
    f = np.asarray(f, dtype=float)
    g = np.asarray(g, dtype=float)
    d = int(mapping.lattice.D)
    s = int(mapping.lattice.S)
    macro_before = recover_macro(f, g, D=d, S=s, lattice=lattice)
    f_eq, g_eq = equilibrium_fg(macro_before.rho, macro_before.u,
                               macro_before.theta, s, lattice)
    f_post, g_post = bgk_relax(f, g, f_eq, g_eq, params, lattice)

    if not return_diagnostics:
        return f_post, g_post

    macro_after = recover_macro(f_post, g_post, D=d, S=s, lattice=lattice)
    return f_post, g_post, CollisionDiagnostics(
        mass_residual=np.sum(f_post - f, axis=-1),
        momentum_residual=np.einsum("...a,ai->...i", f_post - f, lattice.c),
        energy_residual=macro_after.E_tot - macro_before.E_tot,
        min_f_post=float(np.min(f_post)),
        min_g_post=float(np.min(g_post)),
        clipping_used=False,
    )


def assert_bgk_conservation(f: np.ndarray, g: np.ndarray, mapping: UnitMapping,
                            params: BgkParams, *, tol: float = 1.0e-12,
                            lattice: Lattice | None = None) -> None:
    """Same acceptance shape as ``assert_collision_conservation``."""

    _, _, diagnostics = collide_fg_bgk(f, g, mapping, params, lattice=lattice,
                                       return_diagnostics=True)
    if np.max(np.abs(diagnostics.mass_residual)) > tol:
        raise AssertionError("BGK collision mass conservation failed")
    if np.max(np.abs(diagnostics.momentum_residual)) > tol:
        raise AssertionError("BGK collision momentum conservation failed")
    if np.max(np.abs(diagnostics.energy_residual)) > tol:
        raise AssertionError(f"BGK {ENERGY_CLOSURE_DEFINITION} conservation failed")
