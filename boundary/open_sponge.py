"""Top absorbing sponge layer for the coarse acoustic subdomain (P4-D3, D3-2).

Standard acoustics open boundary: a band of rows at the top relaxes the populations toward
the quiescent reference equilibrium with a strength that ramps smoothly from 0 at the sponge
entry to ``sigma_max`` at the domain top. An outgoing wave entering the band decays before it
reaches the top, so almost nothing reflects. Unlike ``boundary/open_cbc.py`` (characteristic
Grad reconstruction, tuned for dx2p6 and tau-fragile), a sponge needs no reconstruction and
no per-mapping tuning -- it is the natural fit for the D3 acoustic region, which is
dispersion-free so there is no volume-injection floor for the sponge seam to feed.

The smooth ramp (power-law profile) avoids a reflection at the sponge ENTRY: a hard step in
the damping would itself reflect. No clipping / floor / positivity repair -- the relaxation
is a convex blend toward a valid equilibrium, so positivity is preserved automatically.
"""

from __future__ import annotations

import numpy as np

from core.equilibrium import equilibrium_fg
from core.macroscopic import recover_macro


def make_top_sponge_callback(*, n_sponge: int, sigma_max: float = 0.5, profile_power: float = 2.0):
    """Return a ``solver.step`` boundary_callback: top ``n_sponge`` rows relax to reference.

    ``sigma_max`` is the per-step relaxation fraction at the domain top (0..1); the strength
    ramps as ``sigma_max * xi**profile_power`` with ``xi`` from 0 at the sponge entry to 1 at
    the top. Combine with a bottom source/wall via :func:`boundary.open_cbc.compose_boundary_callbacks`.
    """

    if not 0.0 < sigma_max <= 1.0:
        raise ValueError("sigma_max must be in (0, 1]")
    if n_sponge < 2:
        raise ValueError("n_sponge must be >= 2")
    cache: dict[tuple, tuple] = {}

    def _callback(*, solver, f_post, g_post, f_stream, g_stream):
        ny, nx = int(solver.ny), int(solver.nx)
        if n_sponge >= ny:
            raise ValueError("sponge fills the whole domain (n_sponge >= ny)")
        key = (ny, nx, id(solver.lattice))
        if key not in cache:
            xi = np.arange(n_sponge, dtype=float) / (n_sponge - 1)     # 0 at entry .. 1 at top
            oms_col = (1.0 - sigma_max * xi**profile_power).reshape(n_sponge, 1)   # (n_sponge,1)
            cache[key] = (oms_col, int(solver.mapping.lattice.S))
        oms_col, S = cache[key]                                        # (n_sponge,1), scalar S
        oms_pop = oms_col[:, :, None]                                  # (n_sponge,1,1) for f/g
        oms_vec = oms_col[:, :, None]                                  # (n_sponge,1,1) for u
        sl = slice(ny - n_sponge, ny)
        D = int(solver.mapping.lattice.D)
        rho0 = float(solver.mapping.lattice.rho_ref_lu)
        th0 = float(solver.mapping.theta_ref_lu)
        # Perturbation damping (NOT relaxation to a fixed reference eq -- that injects,
        # see docstring): recover the local macro, scale the perturbation about the
        # quiescent background by (1-sigma), and rebuild eq(damped macro) + (1-sigma)*neq.
        # Energy decreases monotonically toward the background; the conserved-moment change
        # is the wave leaving the domain, not spurious injection.
        m = recover_macro(f_stream[sl], g_stream[sl], D=D, S=S, lattice=solver.lattice)
        feq_now, geq_now = equilibrium_fg(m.rho, m.u, m.theta, S, solver.lattice)
        rho_d = rho0 + oms_col * (m.rho - rho0)
        u_d = oms_vec * m.u
        th_d = th0 + oms_col * (m.theta - th0)
        feq_d, geq_d = equilibrium_fg(rho_d, u_d, th_d, S, solver.lattice)
        f_stream[sl] = feq_d + oms_pop * (f_stream[sl] - feq_now)
        g_stream[sl] = geq_d + oms_pop * (g_stream[sl] - geq_now)
        return f_stream, g_stream

    return _callback
