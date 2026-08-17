"""Strict candidate-B half-domain mirror topology (D1 strict B, D0-7).

Design authority: docs/Phase_5/strict_faceflux_candidate_b_design_v1.0.md
(EXPERIMENT_PLAN_v1.0, frozen 2026-08-17).  Scope: canonical k_x=0,
column-replicated, two-sided symmetric problems ONLY.  No production wall,
frozen mapping or gate is touched; this module never imports the buffer
band reconstruction (boundary/wall_face_flux.py stays a frozen control).

TOPOLOGY (design section 1/2)
-----------------------------
The physical state is a SINGLE gas half-domain of N rows (no band row, no
wet node).  Both walls live on half-grid FACES: the hot face at y = -1/2
below row 0, the cold face at y = N-1/2 above row N-1; the first gas cell
centre sits d_f = dy/2 from its face.

Every stage rebuilds a temporary 2N mirror extension from the physical
state and restricts back afterwards; the mirror rows own NO volume, mass,
energy or observables and are never carried across stages:

    (P x)[N + r, a] = x[N - 1 - r, opp(a)]        (mirror_extend)
    (R X)[r]        = X[r],  r < N                (restrict_physical)

with R P = I and P R P = P.  rho/theta are even and velocity odd across
both faces by construction.  Periodic pull streaming ON THE EXTENSION is
then the UNIQUE realization of source-free opposite-direction bounce-back
for every crossing link: a population arriving at physical row j with
c_y > j pulls the opposite-direction population of the mirrored source row
— the halfway-reflection closure for all link depths (coverage counts
15/8/3 at face distances 0/1/2, asserted at build time).

ONE STEP (design section 2)
---------------------------
    physical -> P -> collision C -> streaming S -> R
             -> compute q -> boundary Bq (first-gas-cell g source; see
                boundary/wall_face_flux_strict.py)
             -> P -> acoustic A -> filter H -> R

All y-rolls, gradients, FFTs and caches of C/S/A/H run on the 2N
extension; calling periodic operators directly on the N-row physical
array is forbidden.  The face fluxes are computed AFTER restriction, from
the wrap-cleared first-gas-cell temperatures.  The acoustic stage must be
STRUCTURALLY identity on the extension geometry (asserted, never
extrapolated — G2-O S6 discipline); pressure-memory / cross-step spectral
state must be off (asserted).

Runner hard asserts (design section 1): column-replication error <=1e-12,
seam_aware_bottom/top/taper_rows == 0, _filter_seam_window is None.

DIAGNOSTIC ONLY (D0-7): no gate claims; the certified production wall is
untouched; strict-B files are not wired into any default path.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from core.collision_smrt import collide_fg
from core.macroscopic import recover_macro
from core.solver import (
    ACOUSTIC_PHASE_HIGH_MODE_POLICY_SPECIFIED,
    TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_PRESSURE_MEMORY,
    TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL,
    TRACE_BULK_POLICY_GHOST_ORTHOGONAL_SPECTRAL,
    GasSolver2D,
    conservative_biharmonic_filter,
)
from core.streaming import pull_stream_fg

__all__ = [
    "StrictBTopologyError",
    "mirror_extend",
    "restrict_physical",
    "mirror_residual_rel",
    "crossing_coverage_counts",
    "StrictBHalfDomain",
]


class StrictBTopologyError(RuntimeError):
    """A structural precondition of the strict-B topology failed (TOPOLOGY_INVALID)."""


# ---------------------------------------------------------------------------
# pure P / R operators
# ---------------------------------------------------------------------------

def mirror_extend(x: np.ndarray, opposite: np.ndarray) -> np.ndarray:
    """P: (N, nx, Q) physical -> (2N, nx, Q) mirror extension.

    (P x)[N + r, :, a] = x[N - 1 - r, :, opposite[a]].  Pure function; the
    returned array is freshly allocated every call (mirror rows are never
    carried across stages).
    """

    n = x.shape[0]
    ext = np.empty((2 * n,) + x.shape[1:], dtype=x.dtype)
    ext[:n] = x
    ext[n:] = x[::-1][..., opposite]
    return ext


def restrict_physical(x_ext: np.ndarray) -> np.ndarray:
    """R: (2N, ...) extension -> (N, ...) physical rows (copy)."""

    n2 = x_ext.shape[0]
    if n2 % 2 != 0:
        raise StrictBTopologyError(f"extension row count {n2} is odd")
    return x_ext[: n2 // 2].copy()


def mirror_residual_rel(x_ext: np.ndarray, opposite: np.ndarray) -> float:
    """r_P = ||X - P R X|| / ||X|| on an extension-shaped array."""

    rebuilt = mirror_extend(restrict_physical(x_ext), opposite)
    num = float(np.linalg.norm((x_ext - rebuilt).ravel()))
    den = float(np.linalg.norm(x_ext.ravel()))
    return num / max(den, 1e-300)


def crossing_coverage_counts(lattice) -> tuple[int, ...]:
    """Crossing-link coverage per face distance 0/1/2 (must be 15/8/3)."""

    cy = np.asarray(lattice.c[:, 1], dtype=int)
    max_cy = int(cy.max())
    return tuple(int(np.sum(cy > depth)) for depth in range(max_cy))


# ---------------------------------------------------------------------------
# extension stage carrier
# ---------------------------------------------------------------------------

class StrictBHalfDomain:
    """Stage wrapper: N-row physical state, 2N-row extension operators.

    Owns a 2N-geometry GasSolver2D purely as the frozen parameter carrier
    (mapping / filter coefficients / acoustic-stage config); its f/g state
    is never used.  All structural preconditions of the design are asserted
    at construction (fail-loud TOPOLOGY_INVALID).
    """

    def __init__(self, gas_cfg: dict[str, Any], *, n_phys: int, nx: int):
        import copy as _copy

        if int(n_phys) < 5:
            raise StrictBTopologyError("strict-B half domain needs N >= 5")
        self.n_phys = int(n_phys)
        self.nx = int(nx)
        cfg = _copy.deepcopy(gas_cfg)
        cfg["numerics"] = {**cfg["numerics"], "nx": self.nx,
                           "ny": 2 * self.n_phys}
        self.ext_solver = GasSolver2D(cfg)
        self.mapping = self.ext_solver.mapping
        self.lattice = self.ext_solver.lattice
        self.opposite = np.asarray(self.lattice.opposite, dtype=int)
        self.assert_structural()

    # -- structural gate (design sections 1/2) --
    def assert_structural(self) -> dict[str, Any]:
        coll = self.mapping.collision
        report: dict[str, Any] = {"ny_ext": 2 * self.n_phys, "nx": self.nx}

        # involution sanity of the opposite map
        if not np.array_equal(self.opposite[self.opposite],
                              np.arange(self.lattice.q)):
            raise StrictBTopologyError("opposite map is not an involution")

        # crossing coverage counts 15/8/3 (D2Q37 depth structure)
        counts = crossing_coverage_counts(self.lattice)
        report["crossing_coverage"] = counts
        if counts != (15, 8, 3):
            raise StrictBTopologyError(
                f"crossing coverage {counts} != (15, 8, 3)")

        # seam machinery must be entirely off
        if (coll.seam_aware_bottom_rows != 0 or coll.seam_aware_top_rows != 0
                or coll.seam_aware_taper_rows != 0):
            raise StrictBTopologyError("seam_aware rows must all be 0")
        if self.ext_solver._filter_seam_window is not None:
            raise StrictBTopologyError("_filter_seam_window must be None")

        # cross-step spectral state must be off
        if coll.trace_bulk_policy == TRACE_BULK_POLICY_GHOST_ORTHOGONAL_SPECTRAL:
            raise StrictBTopologyError("spectral trace projector must be off")
        if coll.trace_bulk_policy in {
            TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_PRESSURE_MEMORY,
            TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_TWO_CHANNEL,
        }:
            raise StrictBTopologyError("pressure-memory trace must be off")

        # acoustic stage must be structurally identity ON THIS EXTENSION
        n_diag = (len(self.ext_solver._acoustic_phase_modes())
                  if coll.acoustic_phase_correction_enabled else 0)
        high_identity = (
            not coll.acoustic_phase_correction_enabled
            or (coll.acoustic_phase_high_mode_policy
                == ACOUSTIC_PHASE_HIGH_MODE_POLICY_SPECIFIED
                and float(coll.acoustic_phase_high_mode_factor) == 1.0
                and float(coll.acoustic_phase_high_mode_diagonal_factor) == 1.0))
        report["acoustic_diagonal_low_mode_count"] = int(n_diag)
        report["acoustic_high_mode_identity"] = bool(high_identity)
        if n_diag != 0 or not high_identity:
            raise StrictBTopologyError(
                "acoustic stage is NOT structurally identity on the strict-B "
                f"extension geometry: {report}")
        self.structural_report = report
        return report

    # -- P / R bound to this lattice --
    def extend(self, x: np.ndarray) -> np.ndarray:
        return mirror_extend(x, self.opposite)

    def restrict(self, x_ext: np.ndarray) -> np.ndarray:
        return restrict_physical(x_ext)

    def r_p(self, x_ext: np.ndarray) -> float:
        return mirror_residual_rel(x_ext, self.opposite)

    # -- stages on the extension (each rebuilds P from the physical state) --
    def stage_collide_ext(self, f_ext: np.ndarray, g_ext: np.ndarray):
        """C on the extension (pressure-memory asserted off => divergence=None)."""

        return collide_fg(f_ext, g_ext, self.mapping, lattice=self.lattice,
                          trace_bulk_pressure_divergence=None)

    def stage_stream_ext(self, f_ext: np.ndarray, g_ext: np.ndarray):
        """S on the extension (P+S == source-free opposite-direction BB)."""

        return pull_stream_fg(f_ext, g_ext, lattice=self.lattice,
                              y_axis=0, x_axis=1)

    def stage_acoustic_ext(self, f_ext: np.ndarray, g_ext: np.ndarray):
        """A on the extension — asserted structural identity, bit-exact no-op.

        The production functions early-return before touching any lazy
        reference cache when the mode lists are empty / factors are 1.0;
        they are still CALLED so the chain remains the production chain.
        """

        f_ext, g_ext = self.ext_solver._apply_diagonal_acoustic_phase_correction(
            f_ext, g_ext)
        return self.ext_solver._apply_high_mode_acoustic_phase_correction(
            f_ext, g_ext)

    def stage_filter_ext(self, f_ext: np.ndarray, g_ext: np.ndarray):
        """H on the extension (seam window asserted None)."""

        for _ in range(self.ext_solver.high_wavenumber_filter_passes):
            f_ext = conservative_biharmonic_filter(
                f_ext, self.ext_solver.high_wavenumber_filter_strength, None)
            g_ext = conservative_biharmonic_filter(
                g_ext, self.ext_solver.high_wavenumber_filter_strength, None)
        return f_ext, g_ext

    # -- physical-state stage compositions (design section 2 one-step) --
    def stage_cs(self, f: np.ndarray, g: np.ndarray):
        """physical -> P -> C -> S -> R."""

        f_ext, g_ext = self.extend(f), self.extend(g)
        f_ext, g_ext = self.stage_collide_ext(f_ext, g_ext)
        f_ext, g_ext = self.stage_stream_ext(f_ext, g_ext)
        return self.restrict(f_ext), self.restrict(g_ext)

    def stage_ah(self, f: np.ndarray, g: np.ndarray):
        """physical -> P -> A -> H -> R."""

        f_ext, g_ext = self.extend(f), self.extend(g)
        f_ext, g_ext = self.stage_acoustic_ext(f_ext, g_ext)
        f_ext, g_ext = self.stage_filter_ext(f_ext, g_ext)
        return self.restrict(f_ext), self.restrict(g_ext)

    # -- first-gas-cell temperatures from the wrap-cleared physical state --
    def first_cell_thetas(self, f: np.ndarray, g: np.ndarray):
        """(theta_row0, theta_rowN-1) each shaped (1, nx)."""

        d = int(self.mapping.lattice.D)
        s = int(self.mapping.lattice.S)
        m_hot = recover_macro(f[0:1], g[0:1], D=d, S=s, lattice=self.lattice)
        m_cold = recover_macro(f[-1:], g[-1:], D=d, S=s, lattice=self.lattice)
        return m_hot.theta, m_cold.theta

    def strict_direct_step(self, f: np.ndarray, g: np.ndarray, *,
                           face_wall) -> tuple[np.ndarray, np.ndarray, float, float]:
        """One full strict-B step F(x, theta_w).

        ``face_wall`` is a boundary.wall_face_flux_strict.StrictFaceFluxWall
        (carries theta_w per face, the conductance branch and the per-face
        incoming-link ledger writer).  Returns (f', g', dE_hot, dE_cold) with
        the ledger quantities in LU energy per step (whole grid, all columns).
        """

        f_s, g_s = self.stage_cs(f, g)
        g_s, de_hot, de_cold = face_wall.apply(self, f_s, g_s)
        f_h, g_h = self.stage_ah(f_s, g_s)
        return f_h, g_h, de_hot, de_cold
