"""Cross-stack unit 1a: the diagnostic BGK operator inside the frozen chains.

Two hookups, both following the ``core/tangent_wallfix.py`` stage-replacement
paradigm (mirror the frozen stage list, swap exactly ONE stage, keep a PROD
branch that is bitwise-anchored to production in the contract tests):

  * :class:`CrossStackSolver2D` -- ``GasSolver2D`` with the collision call
    selectable.  ``collision="PROD"`` runs ``collide_fg`` and is asserted
    BITWISE-identical to ``GasSolver2D.step`` (with and without a boundary
    callback); ``collision="BGK"`` runs ``core.collision_bgk.collide_fg_bgk``.
    Everything else -- spectral trace projector, pull streaming, boundary
    callback, acoustic phase family, biharmonic filter, step counter -- is the
    production body verbatim.
  * :class:`CrossStackTangentOperator` -- the frozen ``TangentOperator`` with
    the C stage swapped.  The PROD branch DELEGATES to the frozen
    ``TangentOperator.step`` (not a copy of it), so the anchor is identity by
    construction; the BGK branch replaces the three collision blocks
    (macro_eq / stress / heatflux) with the two BGK ones (macro_eq /
    bgk_relax) and leaves S, B, A and H untouched.

Also here: :func:`measure_mode_decay`, a periodic mode-decay transport probe.
It is the frozen G0/P2-4/P2-5 recipe (isobaric thermal sine or transverse shear
sine, modal amplitude, ``verification.shear_wave_measurement._fit_decay``
log-linear fit) with the solver injected, so BGK and PROD effective transport
are measured by the SAME instrument on the SAME grid.  The contract tests
anchor it against ``measure_thermal_diffusion_direction`` on the PROD solver --
without that anchor the probe would be a new, unvalidated instrument.

Blocks under ablation: this unit runs A0 only (``ablated=frozenset()``).  The
BGK branch has no ``stress``/``heatflux`` blocks to ablate, so naming them
fails loudly rather than silently ablating nothing.

DIAGNOSTIC ONLY (D0-7): production ``core/collision_smrt.py``,
``core/solver.py``, ``core/tangent_step.py`` are unchanged; nothing here is a
production configuration.
"""

from __future__ import annotations

import math
from typing import Any, Callable

import numpy as np

from core.collision_bgk import BgkParams, bgk_params_matching, bgk_relax, collide_fg_bgk
from core.collision_smrt import collide_fg
from core.solver import GasSolver2D, conservative_biharmonic_filter
from core.streaming import pull_stream_fg
from core.tangent_step import (
    BaseState,
    StageBases,
    TangentOperator,
    TangentStructureError,
    block_macro_eq,
    compute_stage_bases,
    stage_band,
    stage_filter,
    stage_stream,
)

__all__ = [
    "COLLISION_PROD",
    "COLLISION_BGK",
    "COLLISIONS",
    "CrossStackSolver2D",
    "CrossStackTangentOperator",
    "compose_collide_bgk",
    "compute_stage_bases_crossstack",
    "measure_mode_decay",
]

COLLISION_PROD = "PROD"
COLLISION_BGK = "BGK"
COLLISIONS = (COLLISION_PROD, COLLISION_BGK)

# Collision blocks of the frozen JAB decomposition that do not exist in the BGK
# branch (its whole collision is macro_eq + one linear relaxation block).
_PROD_ONLY_BLOCKS = frozenset({"stress", "heatflux"})


def _check_collision(collision: str) -> str:
    if collision not in COLLISIONS:
        raise ValueError(f"unknown collision branch: {collision!r} "
                         f"(expected one of {list(COLLISIONS)})")
    return collision


# ---------------------------------------------------------------------------
# solver with a selectable collision (settle / forward runs)
# ---------------------------------------------------------------------------

class CrossStackSolver2D(GasSolver2D):
    """``GasSolver2D`` with the collision operator selectable.

    The ``step`` body below is the production body with exactly one line
    changed (the collision call).  Because the two branches share every other
    stage, ``collision="PROD"`` must be bitwise-identical to the production
    solver -- the contract tests assert that over multiple steps, with and
    without the tent boundary callback.
    """

    def __init__(self, config: dict[str, Any], *, collision: str = COLLISION_PROD,
                 bgk_params: BgkParams | None = None):
        super().__init__(config)
        self.collision = _check_collision(collision)
        if self.collision == COLLISION_BGK:
            self.bgk_params = (bgk_params if bgk_params is not None
                               else bgk_params_matching(self.mapping))
        else:
            if bgk_params is not None:
                raise ValueError("bgk_params is only meaningful for collision='BGK'")
            self.bgk_params = None

    def _collide(self, f: np.ndarray, g: np.ndarray,
                 trace_bulk_pressure_divergence: np.ndarray | None):
        if self.collision == COLLISION_BGK:
            return collide_fg_bgk(f, g, self.mapping, self.bgk_params,
                                  lattice=self.lattice)
        return collide_fg(f, g, self.mapping, lattice=self.lattice,
                          trace_bulk_pressure_divergence=trace_bulk_pressure_divergence)

    def step(self, n_steps: int = 1, boundary_callback=None) -> None:
        """Production ``GasSolver2D.step`` verbatim except the collision call."""

        for _ in range(int(n_steps)):
            f, g = self._require_state()
            trace_bulk_pressure_divergence = self._pressure_memory_trace_divergence(f, g)
            f_post, g_post = self._collide(f, g, trace_bulk_pressure_divergence)
            f_post, g_post = self._apply_ghost_orthogonal_spectral_trace_projector(
                f, g, f_post, g_post)
            f_stream, g_stream = pull_stream_fg(f_post, g_post, lattice=self.lattice,
                                                y_axis=0, x_axis=1)
            if boundary_callback is not None:
                f_stream, g_stream = boundary_callback(
                    solver=self, f_post=f_post, g_post=g_post,
                    f_stream=f_stream, g_stream=g_stream)
            self.f, self.g = f_stream, g_stream
            self.f, self.g = self._apply_diagonal_acoustic_phase_correction(self.f, self.g)
            self.f, self.g = self._apply_high_mode_acoustic_phase_correction(self.f, self.g)
            for _ in range(self.high_wavenumber_filter_passes):
                self.f = conservative_biharmonic_filter(
                    self.f, self.high_wavenumber_filter_strength, self._filter_seam_window)
                self.g = conservative_biharmonic_filter(
                    self.g, self.high_wavenumber_filter_strength, self._filter_seam_window)
            self.t_lu += 1


# ---------------------------------------------------------------------------
# BGK collision blocks for the tangent chain
# ---------------------------------------------------------------------------

def compose_collide_bgk(f, g, mapping, lattice, params: BgkParams):
    """The BGK C stage as (macro_eq block) -> (bgk_relax block).

    Bitwise-identical to ``collide_fg_bgk`` (asserted in the contract tests):
    the split exists only so the tangent can linearize the nonlinear part
    (macro recovery + equilibrium) separately from the exactly-linear part.
    """

    rho, u, theta, f_eq, g_eq = block_macro_eq(f, g, mapping, lattice)
    return bgk_relax(f, g, f_eq, g_eq, params, lattice)


def compute_stage_bases_crossstack(solver: GasSolver2D, base: BaseState, *,
                                   collision: str,
                                   bgk_params: BgkParams | None = None) -> StageBases:
    """Stage/block base intermediates for the selected collision branch.

    ``collision="PROD"`` delegates to the frozen ``compute_stage_bases``.
    """

    _check_collision(collision)
    if collision == COLLISION_PROD:
        return compute_stage_bases(solver, base)
    if bgk_params is None:
        raise ValueError("collision='BGK' requires bgk_params")
    mapping = solver.mapping
    lattice = solver.lattice
    rho, u, theta, f_eq, g_eq = block_macro_eq(base.f, base.g, mapping, lattice)
    f2, g_post = bgk_relax(base.f, base.g, f_eq, g_eq, bgk_params, lattice)
    s_f, s_g = stage_stream(f2, g_post, lattice)
    b_f, b_g, hot_de, sink_de = stage_band(
        solver, s_f, s_g, base.theta_w, base.theta_amb, base.hs)
    h_f, h_g = stage_filter(solver, b_f, b_g)
    num = math.sqrt(float(np.sum((h_f - base.f) ** 2) + np.sum((h_g - base.g) ** 2)))
    den = math.sqrt(float(np.sum(base.f ** 2) + np.sum(base.g ** 2)))
    r_f = num / max(den, 1e-300)
    ref = (float(np.mean(rho)), float(np.mean(u[..., 0])),
           float(np.mean(u[..., 1])), float(np.mean(theta)))
    # f1 mirrors f2: the BGK branch has no separate stress block, and naming
    # one under ``ablated`` fails loudly in the operator constructor.
    return StageBases(f=base.f, g=base.g, rho=rho, u=u, theta=theta, f_eq=f_eq,
                      g_eq=g_eq, f1=f2, f2=f2, g_post=g_post, s_f=s_f, s_g=s_g,
                      b_f=b_f, b_g=b_g, hot_de=hot_de, sink_de=sink_de,
                      h_f=h_f, h_g=h_g, r_f=r_f, reference_triple=ref)


# ---------------------------------------------------------------------------
# tangent operator
# ---------------------------------------------------------------------------

class CrossStackTangentOperator(TangentOperator):
    """Frozen ``TangentOperator`` with the C stage swapped for BGK.

    PROD delegates to the frozen ``step`` -- the anchor is the same code, not a
    copy of it.  The BGK body reproduces the frozen S/B/A/H treatment line for
    line (streaming and filter applied exactly because they are exactly linear,
    band by central difference on the joint state + wall-temperature input);
    only the collision blocks differ.
    """

    def __init__(self, solver: GasSolver2D, hot_base: BaseState, hot: StageBases,
                 cold_base: BaseState, cold: StageBases, *, h: float,
                 ablated: frozenset, collision: str = COLLISION_PROD,
                 bgk_params: BgkParams | None = None):
        _check_collision(collision)
        if collision == COLLISION_BGK:
            named = frozenset(ablated) & _PROD_ONLY_BLOCKS
            if named:
                raise TangentStructureError(
                    f"blocks {sorted(named)} do not exist in the BGK collision "
                    "branch; ablating them would silently be a no-op")
            if bgk_params is None:
                raise ValueError("collision='BGK' requires bgk_params")
        elif bgk_params is not None:
            raise ValueError("bgk_params is only meaningful for collision='BGK'")
        super().__init__(solver, hot_base, hot, cold_base, cold, h=h, ablated=ablated)
        self.collision = collision
        self.bgk_params = bgk_params

    def step(self, df: np.ndarray, dg: np.ndarray, d_theta_w: float):
        if self.collision == COLLISION_PROD:
            return super().step(df, dg, d_theta_w)

        h = self.h
        s = self.macro_scale(df, dg, d_theta_w)
        if s <= 0.0 or not math.isfinite(s):
            if not math.isfinite(s):
                raise FloatingPointError("non-finite tangent state")
            zero = np.zeros_like(df)
            return zero, np.zeros_like(dg), 0.0, 0.0
        inv = 1.0 / s
        scale = s / (2.0 * h)
        mapping = self.solver.mapping
        lattice = self.solver.lattice

        # --- C stage, block "macro_eq" (nonlinear; frozen FD convention) ---
        b3 = self._bases("macro_eq")
        vf = h * inv * df
        vg = h * inv * dg
        p = block_macro_eq(b3.f + vf, b3.g + vg, mapping, lattice)
        m = block_macro_eq(b3.f - vf, b3.g - vg, mapping, lattice)
        _, _, _, d_feq, d_geq = [(a - b) * scale for a, b in zip(p, m)]

        # --- C stage, block "bgk_relax" (EXACTLY linear -> applied exactly,
        #     the frozen chain's convention for exactly-linear maps) ---
        d_f2, d_gpost = bgk_relax(df, dg, d_feq, d_geq, self.bgk_params, lattice,
                                  c2=self.c2)

        # --- S stage (exactly linear; A6 swaps in the cold-base FD) ---
        if "stream_filter" in self.ablated:
            bs = self.cold
            w_f2 = h * inv * d_f2
            w_gp = h * inv * d_gpost
            sp = stage_stream(bs.f2 + w_f2, bs.g_post + w_gp, lattice)
            sm = stage_stream(bs.f2 - w_f2, bs.g_post - w_gp, lattice)
            d_sf = (sp[0] - sm[0]) * scale
            d_sg = (sp[1] - sm[1]) * scale
        else:
            d_sf, d_sg = stage_stream(d_f2, d_gpost, lattice)

        # --- B stage (production v1.1 wall, unchanged; A2 -> cold) ---
        bb = self._bases("band")
        base_b = self.cold_base if "band" in self.ablated else self.hot_base
        w_sf = h * inv * d_sf
        w_sg = h * inv * d_sg
        w_tw = h * inv * float(d_theta_w)
        bp = stage_band(self.solver, bb.s_f + w_sf, bb.s_g + w_sg,
                        base_b.theta_w + w_tw, base_b.theta_amb, base_b.hs)
        bm = stage_band(self.solver, bb.s_f - w_sf, bb.s_g - w_sg,
                        base_b.theta_w - w_tw, base_b.theta_amb, base_b.hs)
        d_bf = (bp[0] - bm[0]) * scale
        d_bg = (bp[1] - bm[1]) * scale
        d_hot = (bp[2] - bm[2]) * scale
        d_sink = (bp[3] - bm[3]) * scale

        # --- A stage: structurally identity (asserted at construction) ---

        # --- H stage (exactly linear; A6 swaps in the cold-base FD) ---
        if "stream_filter" in self.ablated:
            bh = self.cold
            w_bf = h * inv * d_bf
            w_bg = h * inv * d_bg
            hp = stage_filter(self.solver, bh.b_f + w_bf, bh.b_g + w_bg)
            hm = stage_filter(self.solver, bh.b_f - w_bf, bh.b_g - w_bg)
            d_hf = (hp[0] - hm[0]) * scale
            d_hg = (hp[1] - hm[1]) * scale
        else:
            d_hf, d_hg = stage_filter(self.solver, d_bf, d_bg)

        return d_hf, d_hg, d_hot, d_sink


# ---------------------------------------------------------------------------
# effective-transport probe (same instrument for every collision branch)
# ---------------------------------------------------------------------------

def one_step_spectral_radius(solver_factory: Callable[[dict[str, Any]], GasSolver2D],
                             gas_cfg: dict[str, Any], *, ny: int, nx: int,
                             h: float = 1.0e-7, tol: float = 1.0e-6,
                             return_eigenvalues: bool = False) -> dict[str, Any]:
    """Spectral radius of the linearized one-step operator on a PERIODIC box.

    The uniform reference state (rho_ref, u=0, theta_ref) is a fixed point of
    the full production step, so the one-step Jacobian around it is exactly the
    linear amplification matrix of the scheme -- collision, streaming, acoustic
    phase family and biharmonic filter included, walls excluded.  ``rho(J) > 1``
    is an unconditional linear instability of the COLLISION OPERATOR on this
    lattice at this operating point; it cannot be attributed to the wall, the
    geometry, the drive amplitude or the base-state gradient, because none of
    them is present.

    The acoustic stage must be structurally an identity on the probe geometry
    (same no-extrapolation rule as the tangent chain); this fails loudly
    otherwise, since a live phase-correction stage would make the map
    state-dependent and the Jacobian meaningless.

    ``tol`` is the finite-difference noise floor of the Jacobian (round-off/h,
    ~1e-9 at the default h; the conserved modes land on |lambda| = 1 to that
    accuracy).  ``unstable_mode_count`` counts eigenvalues beyond ``1 + tol``,
    so a genuinely marginal scheme reads zero rather than a handful of
    round-off "instabilities".
    """

    from core.tangent_step import assert_acoustic_stage_identity

    cfg = {**gas_cfg, "numerics": {**gas_cfg["numerics"], "nx": int(nx), "ny": int(ny)}}
    solver = solver_factory(cfg)
    acoustic = assert_acoustic_stage_identity(solver)
    rho0 = float(solver.mapping.lattice.rho_ref_lu)
    th0 = float(solver.mapping.theta_ref_lu)
    solver.initialize_from_macro(np.full((ny, nx), rho0), np.zeros((ny, nx, 2)),
                                 np.full((ny, nx), th0))
    f0, g0 = solver.f.copy(), solver.g.copy()
    n_f = f0.size
    dim = n_f + g0.size

    def _advance(vec: np.ndarray) -> np.ndarray:
        solver.f = vec[:n_f].reshape(f0.shape).copy()
        solver.g = vec[n_f:].reshape(g0.shape).copy()
        solver.step(1)
        return np.concatenate([solver.f.ravel(), solver.g.ravel()])

    x0 = np.concatenate([f0.ravel(), g0.ravel()])
    fixed_point_residual = float(np.max(np.abs(_advance(x0) - x0)))
    jac = np.empty((dim, dim), dtype=float)
    probe = np.zeros(dim)
    for j in range(dim):
        probe[:] = 0.0
        probe[j] = h
        jac[:, j] = (_advance(x0 + probe) - _advance(x0 - probe)) / (2.0 * h)
    eigenvalues = np.linalg.eigvals(jac)
    magnitude = np.abs(eigenvalues)
    order = np.argsort(magnitude)[::-1]
    out: dict[str, Any] = {
        "ny": int(ny), "nx": int(nx), "dim": int(dim), "h": float(h),
        "tol": float(tol),
        "spectral_radius": float(magnitude[order[0]]),
        "top_magnitudes": [float(v) for v in magnitude[order[:8]]],
        "unstable_mode_count": int(np.count_nonzero(magnitude > 1.0 + tol)),
        "fixed_point_residual": fixed_point_residual,
        "acoustic_stage_identity": acoustic["identity"],
    }
    if return_eigenvalues:
        out["eigenvalues"] = eigenvalues[order]
    return out


def _modal_amplitude_y(field: np.ndarray, mode_index: int) -> complex:
    arr = np.asarray(field, dtype=float)
    ny = arr.shape[0]
    phase = (2.0 * np.pi * mode_index / ny) * np.arange(ny)[:, None]
    centered = arr - np.mean(arr)
    return complex((2.0 / centered.size) * np.sum(centered * np.exp(-1j * phase)))


def measure_mode_decay(solver_factory: Callable[[dict[str, Any]], GasSolver2D],
                       gas_cfg: dict[str, Any], *, channel: str, ny: int,
                       nx: int = 4, mode_index: int = 1, amplitude: float = 1.0e-5,
                       steps: int, sample_interval: int = 1,
                       fit_start: int = 10) -> dict[str, Any]:
    """Periodic y-axis mode decay -> alpha_eff (thermal) or nu_eff (shear).

    Frozen P2-4/P2-5/G0 recipe with the solver injected: isobaric thermal sine
    (``channel="thermal"``) or transverse shear sine (``channel="shear"``) at
    ``mode_index`` along y, modal amplitude per sample, log-linear decay fit
    with the frozen ``_fit_decay``.  Anchored against
    ``measure_thermal_diffusion_direction`` on the PROD solver in the contract
    tests.

    The measured rate is the AS-RUN one: it includes the biharmonic filter and
    every other solver-level stage, exactly as the tent rig runs them.  That is
    the point -- PROD and BGK are compared through one instrument, not through
    two different analytic idealizations.
    """

    from verification.shear_wave_measurement import _fit_decay

    if channel not in ("thermal", "shear"):
        raise ValueError(f"unknown channel: {channel!r}")
    if amplitude > 1.0e-4:
        raise ValueError("mode-decay amplitude must satisfy A/ref <= 1e-4 "
                         "(frozen P2-4/P2-5 caliber)")
    cfg = {**gas_cfg, "numerics": {**gas_cfg["numerics"], "nx": int(nx), "ny": int(ny)}}
    solver = solver_factory(cfg)
    mapping = solver.mapping
    theta_b = float(mapping.theta_ref_lu)
    rho_b = float(mapping.lattice.rho_ref_lu)
    k_mag = 2.0 * np.pi * int(mode_index) / int(ny)
    phase = k_mag * np.arange(ny, dtype=float)[:, None] * np.ones((1, nx))

    if channel == "thermal":
        theta = theta_b * (1.0 + amplitude * np.sin(phase))
        rho = (rho_b * theta_b) / theta                  # locally isobaric
        u = np.zeros((ny, nx, 2))
    else:
        theta = np.full((ny, nx), theta_b)
        rho = np.full((ny, nx), rho_b)
        u = np.zeros((ny, nx, 2))
        c_lu = math.sqrt(float(mapping.physical.gamma) * theta_b)
        u[..., 0] = amplitude * c_lu * np.sin(phase)
    solver.initialize_from_macro(rho, u, theta)

    times: list[int] = []
    amps: list[complex] = []
    nan_detected = False
    for step in range(int(steps) + 1):
        with np.errstate(all="ignore"):
            macro = solver.get_macro()
        finite = bool(np.isfinite(macro.theta).all() and np.isfinite(macro.u).all()
                      and np.isfinite(macro.rho).all())
        if not finite or float(np.nanmin(macro.theta)) <= 0.0:
            nan_detected = True
            break
        if step % int(sample_interval) == 0:
            field = (macro.theta - theta_b) if channel == "thermal" else macro.u[..., 0]
            times.append(step)
            amps.append(_modal_amplitude_y(field, mode_index))
        if step < int(steps):
            with np.errstate(all="ignore"):
                solver.step()

    fit = _fit_decay(np.asarray(times, dtype=float), np.asarray(amps, dtype=complex),
                     int(fit_start), None)
    rate = fit["decay_rate"]
    value = rate / (k_mag * k_mag) if np.isfinite(rate) else float("nan")
    nominal = float(mapping.alpha_lu if channel == "thermal" else mapping.nu_lu)
    return {
        "channel": channel, "ny": int(ny), "nx": int(nx), "k_lu": float(k_mag),
        "measured_lu": float(value), "nominal_mapping_lu": nominal,
        "ratio_vs_nominal": float(value / nominal) if np.isfinite(value) else float("nan"),
        "steps": int(steps), "fit": {k: fit[k] for k in
                                     ("fitting_window", "residual_norm",
                                      "fit_sample_count")},
        "finite": not nan_detected, "sample_count": len(times),
    }
