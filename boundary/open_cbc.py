"""Characteristic-impedance open-top boundary for the upper gas half-domain (P4-1).

Phase_4 removes the y-periodic topology inherited from Phase_2/3: the film wall stays at
the bottom (row 0, ``wall_thermal_grad``) and the top of the gas column becomes an open,
non-reflecting boundary so acoustic/thermal disturbances can leave the domain (contract
``docs/Phase_4/phase4_instruction_v1.0.md`` §6, gate: normal-incidence 10 kHz |R| < 0.05).

Scheme -- algebraic characteristic (impedance-matched) reconstruction with the
Grad/regularized DNA proven by ``wall_thermal_grad.py``:

1. Outgoing characteristic from clean interior rows, transport-delayed. ``w+ = p' +
   Z0*v`` (``Z0 = rho0*c0``, ``c0 = sqrt(gamma*theta_ref)``) is read from post-collision
   rows ``ny-1-source_offset`` and the row below and TWO-ROW AVERAGED (gain <= 1 at every
   k_y; a linear extrapolation has checkerboard gain ``|1+2*offset|`` and blows up the
   coupled column from roundoff), then ADVECTED to the boundary along the characteristic
   through a ring buffer of ``(offset+0.5)/c0 - 1`` samples (method of characteristics:
   the boundary re-emits only what has physically arrived; imposing the sample early
   makes the boundary anticipatory and weakly ACTIVE -- see refuted variant 3). The
   source rows sit below the top strip that the solver's PERIODIC corrections pollute
   every step (the biharmonic filter is a double periodic Laplacian: rows ny-1, ny-2
   couple to the bottom wall rows through the wrap); the delay is 13.4 steps = 0.095 deg
   of phase at 10 kHz -- negligible against the |R|<0.05 gate.
2. Incoming characteristic actively zeroed. The boundary state is built from ``w- = 0``:
   ``p'_b = w+/2``, ``v_b = w+/(2*Z0)``, ``rho_b = rho0 + p'_b/c0^2`` (linear-isentropic,
   no entropy inflow). This enforces the matched impedance ``p' = Z0*v`` exactly at every
   step, so any injected ``w-`` (filter seam, spectral projectors, neq lag) is wiped
   instead of integrated, and a uniform domain overpressure is actively vented at the
   impedance rate (k=0 decay time ``tau = 2*L/c0`` steps).
3. FULL-STRIP Grad imposition with per-row characteristic delays. D2Q37 has ``|cy|`` up
   to 3, so the top 3 rows all pull populations from above the domain (periodic
   streaming wraps them from the BOTTOM wall rows). Each strip row ``ny-1-d`` is rebuilt
   whole as ``feq(target_d) + neq(source row)`` where ``target_d`` uses the delayed w+
   sample for ITS OWN distance ``(offset+0.5-d)`` from the source centroid -- the strip
   carries the traveling-wave gradient, and no wrapped or partially-overwritten link
   survives anywhere (rows below the strip pull only from in-domain rows). The zero
   mass/momentum non-equilibrium makes rho/u exact; a uniform ``delta`` on ``g`` pins
   the internal energy (theta exact).

REFUTED variants (kept as negative results; mechanism probes 2026-07-04):

1. Euler-LODI *inheriting the actual top-row state* (run ``results/m4/20260704T024300Z``):
   only preserves ``w-`` instead of zeroing it and leaves the k=0 mass/pressure mode of
   the open column with no absolute anchor; every per-step numerical bias integrates into
   the boundary state. Over the 1e5-step 10 kHz certification run the domain inflated
   monotonically (mass drift +104%, top-row p' ~ 2e5 Pa) and the drift ramp leaked into
   the harmonic fit as a y-uniform component, reading a fake |R| ~ 1.0 (A_inc ~ A_ref ~
   13.5 kPa vs the 2 Pa physical wave, k-insensitive).
2. Linear w+ extrapolation to the boundary row: checkerboard (k_y=pi) gain 7 -> blowup
   from roundoff within ~80 steps in the coupled wall+open column.
3. Undelayed (anticipatory) w+ imposition: the sample needs (offset+0.5)/c0 ~ 13.4 steps
   to physically reach the boundary; imposing it after 1 step anticipates the wave and
   contributes an active component (no-drive seed growth persisted; the 10 kHz
   certification run died on the rho_b>0 guard after >8k steps). The transport-delay
   ring buffer is kept on physical grounds even though it was not sufficient alone.
4. Partial deep-link overwrites at rows ny-2/ny-3 (single imposed row + link surgery):
   4a. zero-gradient copy from the boundary row: boundary state re-enters the interior
       at ~2.8% weight per step, feeds the w+ source rows, gain-locks near-neutral modes
       (no-drive seed growth, e-fold ~4.3k steps);
   4b. zero-transport persistence (hold the site's pre-streaming value): same loop
       through stale content, grows FASTER (e-fold ~2.9k steps);
   4c. zero-gradient PLATEAU strip (all 3 rows = one state, single 3.5-cell delay) with
       the source adjacent to the strip: delayed-feedback loop, violent blowup ~2k steps.
5. Single imposed row + method-of-characteristics GHOST values on the wrapped links
   (delays extended to ghost heights): stable (seed test decaying), but the mixed
   imposed/free rows form a 2-cell impedance modulation inside the strip -- a Bragg-like
   scatterer pinned at the top. Measured harmonic profiles: |w-| ~ 0.014 at the imposed
   row itself yet ~0.3-0.45 born across the strip, R rising as the drive frequency drops
   (0.66 at the 92.6 kHz diagnostic, ~1.0 at half that) -- fatal for the 10 kHz gate.
   The full-strip per-row-delay imposition (scheme point 3) removes the mixed rows
   entirely.

No clipping / floor / positivity repair; an unphysical target fails loudly.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from core.equilibrium import equilibrium_fg
from core.lattice import Lattice
from core.macroscopic import recover_macro


@dataclass(frozen=True)
class TopOpenStencil:
    cy: np.ndarray                  # integer wall-normal velocity component per direction
    incoming: np.ndarray            # direction indices with cy < 0 (pulled from above the top)
    max_down: int                   # max(|cy|) among incoming -> deepest affected row count
    affected_rows_below_top: tuple[int, ...]  # row offsets below ny-1 whose incoming links wrap


def top_open_stencil(lattice: Lattice) -> TopOpenStencil:
    cy = np.asarray(lattice.c[:, 1], dtype=int)
    max_down = int(-cy.min())
    return TopOpenStencil(
        cy=cy,
        incoming=np.where(cy < 0)[0],
        max_down=max_down,
        affected_rows_below_top=tuple(range(max_down)),
    )


def make_top_open_boundary_callback(
    *,
    mean_pressure_relax: float = 0.0,
    p_ref_lu: float | None = None,
    source_offset: int = 6,
    w_lowpass_steps: float = 0.0,
):
    """Return a ``solver.step`` boundary_callback imposing an impedance-matched open top.

    ``mean_pressure_relax`` blends a pressure-release component into the incoming
    characteristic (``w- = -relax * p'_src``): a diagnostic knob with direct reflection
    cost ``|R| ~ relax/2``; the default ``0.0`` is the pure matched-impedance condition
    (the k=0 overpressure vent needs no extra anchor -- it decays at rate ``c0/(2*L)``
    per step by construction). ``p_ref_lu`` defaults to the solver's reference pressure.
    ``source_offset`` picks the w+ source row ``ny-1-source_offset``; keep >= 3 so the
    source stays clear of the periodic filter seam (rows ny-1, ny-2). Combine with the
    bottom wall callback via :func:`compose_boundary_callbacks` -- the two write disjoint
    row sets (top: ``ny-1..ny-3``; bottom: ``0..2``), so ``ny >= 10`` is required.
    """

    relax = float(mean_pressure_relax)
    lp_steps = float(w_lowpass_steps)
    offset = int(source_offset)
    if offset < 5:
        raise ValueError(
            "source_offset must be >= 5: the w+ source rows must sit below the imposed "
            "top strip (3 rows) plus a buffer row, and clear of the periodic filter seam"
        )

    # Transport-delay buffer for w+ (method of characteristics): the sample measured at
    # the source centroid (offset+0.5 cells below the top) physically arrives at the
    # boundary (offset+0.5)/c0 steps later. Imposing it EARLY makes the boundary
    # anticipatory, i.e. weakly ACTIVE: the undelayed variant self-amplifies column
    # eigenmodes from roundoff (no-drive seed growth e-fold ~3.8k steps; certification
    # run died on the rho_b>0 guard after >8k steps). One callback instance per run.
    state: dict[str, object] = {"buffer": None, "t0": None}

    def _callback(*, solver, f_post, g_post, f_stream, g_stream):
        lattice = solver.lattice
        D = int(solver.mapping.lattice.D)
        S = int(solver.mapping.lattice.S)
        q = int(lattice.q)
        gamma = 1.0 + 2.0 / (D + S)
        ny = int(solver.ny)
        if ny < offset + 7:
            raise ValueError("open top boundary needs ny >= source_offset + 7 (clear of bottom wall rows)")
        j_top = ny - 1
        j_src = j_top - offset
        rho0 = float(solver.mapping.lattice.rho_ref_lu)
        theta_ref = float(solver.mapping.theta_ref_lu)
        p_ref = rho0 * theta_ref if p_ref_lu is None else float(p_ref_lu)
        c0 = float(np.sqrt(gamma * theta_ref))
        z0 = rho0 * c0

        def row_macro(j: int):
            return recover_macro(f_post[j:j + 1], g_post[j:j + 1], D=D, S=S, lattice=lattice)

        m_src = row_macro(j_src)
        m_src2 = row_macro(j_src - 1)

        def w_plus(m):
            return (m.p[0] - p_ref) + z0 * m.u[0, :, 1]          # (nx,)

        # Two-row average (checkerboard-safe, gain <= 1 at every k_y). A linear
        # extrapolation to the boundary row has gain |1+2*offset| = 7 on grid-scale
        # (k_y=pi) content and destabilizes the coupled wall+open column from roundoff
        # within ~80 steps; the averaged 0th-order source only costs an O(k*offset)
        # phase lag (~1.7e-3 rad at 10 kHz -- negligible against the |R|<0.05 gate).
        w_now = 0.5 * (w_plus(m_src) + w_plus(m_src2))

        # Advect w+ along the outgoing characteristic (method of characteristics): the
        # sample measured at the source centroid ((offset+0.5) cells below the top) at
        # time n physically reaches height h above the top row at
        # n + (offset+0.5+h)/c0; we impose at post-stream time n+1, so read the ring
        # buffer (offset+0.5+h)/c0 - 1 samples back (linear interpolation,
        # quiescent-zero history at startup). h=0 is the boundary row itself; h=1,2 are
        # the ghost rows feeding the wrapped deep links (|cy|>=2) of rows ny-2/ny-3.
        max_ghost = 2
        delay0 = (offset + 0.5) / c0 - 1.0
        n_hist = int(np.ceil(delay0 + max_ghost / c0)) + 3
        if state["buffer"] is None or state["t0"] != solver.t_lu:
            state["buffer"] = np.zeros((n_hist, w_now.shape[0]))
            state["count"] = 0
            state["w_ema"] = np.zeros_like(w_now)
        # Low-pass the sampled characteristic (EMA, time constant ``w_lowpass_steps``).
        # The parasitic boundary<->near-zone feedback loops live at loop periods of tens
        # of steps (fastest measured ignition: e-fold ~143 steps in the dead-band
        # geometry), 3 orders of magnitude above the 10 kHz signal (~5.1e4 steps/period):
        # an EMA scaled to ~1% of the drive period suppresses the loop gain by >30x at
        # its own frequency while costing a known, reportable group-delay bias
        # |R| ~ omega*tau/2 (~0.03 at tau = 0.01 period, any drive frequency). The
        # boundary stays frequency-agnostic: the caller supplies the time constant.
        if lp_steps > 0.0:
            state["w_ema"] = state["w_ema"] + (w_now - state["w_ema"]) / lp_steps
            w_push = state["w_ema"]
        else:
            w_push = w_now
        buf = state["buffer"]
        count = int(state["count"])
        buf[count % n_hist] = w_push
        state["count"] = count + 1
        state["t0"] = solver.t_lu + 1                            # next expected call time

        def _sample(i: int) -> np.ndarray:
            return buf[i % n_hist] if i >= 0 else np.zeros_like(w_now)

        def _delayed(delay_samples: float) -> np.ndarray:
            read = count - delay_samples
            j0 = int(np.floor(read))
            fr = read - j0
            return (1.0 - fr) * _sample(j0) + fr * _sample(j0 + 1)

        # Grad reconstruction: feq(target) + interior non-equilibrium (zero mass/momentum).
        feq_s, geq_s = equilibrium_fg(m_src.rho, m_src.u, m_src.theta, S, lattice)
        f_neq = f_post[j_src:j_src + 1] - feq_s
        g_neq = g_post[j_src:j_src + 1] - geq_s
        c_arr = np.asarray(lattice.c, dtype=float)
        u_x_src = m_src.u[0, :, 0]

        def _reconstruct(w_vec: np.ndarray, w_minus_vec: np.ndarray | float):
            p_prime = 0.5 * (w_vec + w_minus_vec)
            v = (w_vec - w_minus_vec) / (2.0 * z0)
            rho = rho0 + p_prime / (c0 * c0)                     # linear-isentropic, no entropy inflow
            if np.any(rho <= 0.0):
                raise FloatingPointError("open boundary target density became unphysical (no repair applied)")
            theta = (p_ref + p_prime) / rho
            if np.any(theta <= 0.0):
                raise FloatingPointError("open boundary target temperature became unphysical (no repair applied)")
            u = np.stack((u_x_src, v), axis=-1)[None, ...]       # (1,nx,2)
            feq_b, geq_b = equilibrium_fg(rho[None, :], u, theta[None, :], S, lattice)
            f_row = feq_b + f_neq                                # rho, u exact
            peculiar = c_arr[None, None, :, :] - u[:, :, None, :]
            c2 = np.sum(peculiar**2, axis=-1)                    # (1,nx,q)
            k_tr = 0.5 * np.sum(f_row * c2, axis=-1)             # (1,nx)
            target_int = 0.5 * (D + S) * rho[None, :] * theta[None, :]
            delta = (target_int - k_tr - np.sum(geq_b + g_neq, axis=-1)) / q
            return f_row, geq_b + g_neq + delta[..., None]

        # FULL-STRIP characteristic imposition (no partial-link surgery anywhere).
        # Every construction that leaves a row with a partially overwritten or stuck
        # population subset turns that row into an ACTIVE defect through the RR
        # collision (refuted variants 4-6: wrapped links, ghost links, constant dead
        # band -- ignition e-folds 0.14k-4k steps). The top max_down rows are therefore
        # rebuilt WHOLE, each from the delayed w+ sample matching its own distance from
        # the source centroid (traveling-wave-consistent strip); free rows below pull
        # only from whole imposed rows or real gas. The strip's own feedback path runs
        # entirely through the sampled w+ -- which the EMA low-pass suppresses at the
        # parasitic loop frequencies (see the buffer comment above).
        strip = top_open_stencil(lattice).max_down               # 3 for D2Q37
        w_minus = -relax * (m_src.p[0] - p_ref)
        for d in range(strip):
            w_d = _delayed((offset + 0.5 - d) / c0 - 1.0)
            f_row, g_row = _reconstruct(w_d, w_minus if d == 0 else 0.0)
            f_stream[j_top - d:j_top - d + 1] = f_row
            g_stream[j_top - d:j_top - d + 1] = g_row
        return f_stream, g_stream

    return _callback

def compose_boundary_callbacks(*callbacks):
    """Compose ``solver.step`` boundary callbacks (applied in order, e.g. bottom wall then
    top open boundary). Callbacks must write disjoint row sets; both read the shared
    ``f_post/g_post`` (pre-streaming), so the composition order is not physics-relevant."""

    def _composed(*, solver, f_post, g_post, f_stream, g_stream):
        for callback in callbacks:
            f_stream, g_stream = callback(
                solver=solver, f_post=f_post, g_post=g_post,
                f_stream=f_stream, g_stream=g_stream,
            )
        return f_stream, g_stream

    return _composed
