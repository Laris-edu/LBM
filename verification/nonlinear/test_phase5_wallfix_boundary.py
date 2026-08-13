"""A2-5 wallfix counter-proof instrument tests (D0-7 diagnostic unit).

Contract tests for boundary/wall_thermal_mass_neutral_v2.py +
core/tangent_wallfix.py + the runner's settle replica:

- PROD anchor chain (the JAB2 anchoring pattern): v2 reconstruction ==
  production _mass_neutral_reconstruct_row0_symmetric BITWISE; stage_band_
  wallfix == frozen stage_band BITWISE; compute_stage_bases_wallfix ==
  frozen compute_stage_bases BITWISE; WallfixTangentOperator(PROD).step ==
  frozen TangentOperator.step BITWISE on a deterministic probe; the runner's
  settle replica snapshot == run_tent(eps_ac=0, snapshot=True) BITWISE,
- legality invariants per v2 variant (guide 7.2 caliber): wall-operation
  mass change exactly zero, u_row = 0 and theta_row = theta_w at machine
  level, row total energy (hence the exact bookkeeping deltas) repin-shape
  invariant,
- eqshape non-degeneracy: the injected g differs microscopically from the
  uniform repin (ghost-content difference) while all pinned moments agree,
  and the hot-base tangent step differs (the family is measurable),
- fail-loud on unknown repin/extrap modes.

No arbitration verdicts here — the counter-proof judgement belongs to
scripts/phase5_wallfix_arbitration.py's frozen lines.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from boundary.wall_thermal_mass_neutral import (
    _mass_neutral_reconstruct_row0_symmetric,
)
from boundary.wall_thermal_mass_neutral_v2 import (
    WALLFIX_VARIANTS,
    reconstruct_row0_symmetric_v2,
)
from core.macroscopic import recover_macro
from core.solver import GasSolver2D
from core.tangent_step import (
    TangentOperator,
    compute_stage_bases,
    make_probe,
    stage_band,
)
from core.tangent_wallfix import (
    WallfixTangentOperator,
    compute_stage_bases_wallfix,
    stage_band_wallfix,
)
from scripts.phase2_m2_verification import load_config
from scripts.phase5_g4a_dc_basestate import run_tent
from scripts.phase5_wallfix_arbitration import settle_tent_wallfix
from scripts.phase5_wp4_jacobian_ablation import snapshot_to_base

NY, NX, HS = 12, 4, 6
THETA_DC = 0.05
F_HZ = 1.0e4


@pytest.fixture(scope="module")
def rig():
    cfg = load_config(Path("configs/gas_air_10k_d2q37_levelc_dx2p6.yaml"))
    cfg["numerics"] = {**cfg["numerics"], "nx": NX, "ny": NY}
    solver = GasSolver2D(cfg)
    th0 = float(solver.mapping.theta_ref_lu)
    rho0 = float(solver.mapping.lattice.rho_ref_lu)
    rng = np.random.default_rng(20260811)
    y = np.arange(NY)
    prof = th0 * (1.0 + 0.03 * np.cos(2 * np.pi * y / NY))[:, None]
    theta = np.tile(prof, (1, NX)) * (1.0 + 1e-3 * rng.standard_normal((NY, NX)))
    rho = rho0 * th0 / theta
    u = 1e-4 * rng.standard_normal((NY, NX, 2))
    solver.initialize_from_macro(rho, u, theta)
    solver.step(3)  # develop genuine non-equilibrium content
    return {"cfg": cfg, "solver": solver, "th0": th0,
            "f": solver.f.copy(), "g": solver.g.copy()}


def test_prod_reconstruction_bitwise(rig):
    solver, th0 = rig["solver"], rig["th0"]
    theta_w = th0 * (1.0 + THETA_DC)
    for row in (0, HS):
        fa, ga = rig["f"].copy(), rig["g"].copy()
        fb, gb = rig["f"].copy(), rig["g"].copy()
        _mass_neutral_reconstruct_row0_symmetric(
            solver, fa, ga, theta_w, extrap="row1", row=row)
        reconstruct_row0_symmetric_v2(
            solver, fb, gb, theta_w, extrap="row1", repin="uniform", row=row)
        assert np.array_equal(fa, fb) and np.array_equal(ga, gb)


def test_v2_invariants_all_variants(rig):
    solver, th0 = rig["solver"], rig["th0"]
    lattice = solver.lattice
    D = int(solver.mapping.lattice.D)
    S = int(solver.mapping.lattice.S)
    theta_w = th0 * (1.0 + THETA_DC)
    c2 = np.sum(np.asarray(lattice.c, dtype=float) ** 2, axis=-1)
    ref_row_energy = None
    for name, (repin, extrap) in WALLFIX_VARIANTS.items():
        f, g = rig["f"].copy(), rig["g"].copy()
        mass_pre = float(np.sum(f))
        reconstruct_row0_symmetric_v2(
            solver, f, g, theta_w, extrap=extrap, repin=repin, row=0)
        # (1) mass neutrality: exact zero total-mass change
        assert float(np.sum(f)) == pytest.approx(mass_pre, rel=0, abs=1e-13)
        m = recover_macro(f[0:1], g[0:1], D=D, S=S, lattice=lattice)
        # (2) u_wall = 0, (3) exact theta pinning (fp-summation noise level;
        # the G1-W production gate line for wall metrics is 1e-10)
        assert float(np.max(np.abs(m.u))) < 1e-12
        assert float(np.max(np.abs(m.theta - theta_w))) < 1e-12 * theta_w
        # (4) row total energy (the bookkeeping delta source) is
        # repin-shape INVARIANT — same target, same f0
        e_row = float(np.sum(0.5 * f[0:1] * c2) + np.sum(g[0:1]))
        if ref_row_energy is None:
            ref_row_energy = e_row
        else:
            assert e_row == pytest.approx(ref_row_energy, rel=1e-13)
        del name


def test_eqshape_nondegenerate_but_moment_identical(rig):
    solver, th0 = rig["solver"], rig["th0"]
    theta_w = th0 * (1.0 + THETA_DC)
    fu, gu = rig["f"].copy(), rig["g"].copy()
    fe, ge = rig["f"].copy(), rig["g"].copy()
    reconstruct_row0_symmetric_v2(solver, fu, gu, theta_w,
                                  extrap="row1", repin="uniform", row=0)
    reconstruct_row0_symmetric_v2(solver, fe, ge, theta_w,
                                  extrap="row1", repin="eqshape", row=0)
    assert np.array_equal(fu, fe)  # f side untouched by the repin shape
    dg = ge[0] - gu[0]
    # microscopic ghost-content difference is REAL...
    assert float(np.max(np.abs(dg))) > 1e-12
    # ...but the pinned zeroth moment agrees at machine level per column
    assert float(np.max(np.abs(np.sum(dg, axis=-1)))) < 1e-13


def test_stage_and_bases_and_operator_prod_bitwise(rig):
    cfg, th0 = rig["cfg"], rig["th0"]
    theta_hot = th0 * (1.0 + THETA_DC)
    # settle replica anchor: PROD == run_tent (eps_ac=0, snapshot=True)
    hot_a = run_tent(cfg, ny=NY, nx=NX, theta_dc=THETA_DC, frequency_hz=F_HZ,
                     eps_ac=0.0, settle_periods=0.1, drive_periods=0.0,
                     samples_per_period=8, init="seed", snapshot=True, log=None)
    hot_b = settle_tent_wallfix(cfg, ny=NY, nx=NX, theta_dc=THETA_DC,
                                frequency_hz=F_HZ, settle_periods=0.1,
                                samples_per_period=8, repin="uniform",
                                extrap="row1")
    assert np.array_equal(hot_a["snapshot"]["f"], hot_b["snapshot"]["f"])
    assert np.array_equal(hot_a["snapshot"]["g"], hot_b["snapshot"]["g"])
    cold_b = settle_tent_wallfix(cfg, ny=NY, nx=NX, theta_dc=0.0,
                                 frequency_hz=F_HZ, settle_periods=0.1,
                                 samples_per_period=8, repin="uniform",
                                 extrap="row1")

    solver2 = GasSolver2D(cfg)
    hot_base = snapshot_to_base(hot_b)
    cold_base = snapshot_to_base(cold_b)
    # stage anchor
    sa = stage_band(solver2, hot_base.f, hot_base.g, theta_hot, th0, HS)
    sb = stage_band_wallfix(solver2, hot_base.f, hot_base.g, theta_hot, th0,
                            HS, repin="uniform", extrap="row1")
    assert np.array_equal(sa[0], sb[0]) and np.array_equal(sa[1], sb[1])
    assert sa[2] == sb[2] and sa[3] == sb[3]
    # bases anchor
    ba = compute_stage_bases(solver2, hot_base)
    bb = compute_stage_bases_wallfix(solver2, hot_base,
                                     repin="uniform", extrap="row1")
    assert np.array_equal(ba.h_f, bb.h_f) and np.array_equal(ba.h_g, bb.h_g)
    assert ba.r_f == bb.r_f
    ca = compute_stage_bases(solver2, cold_base)
    cb = compute_stage_bases_wallfix(solver2, cold_base,
                                     repin="uniform", extrap="row1")
    # operator anchor: one tangent step, deterministic probe
    op_a = TangentOperator(solver2, hot_base, ba, cold_base, ca,
                           h=5e-5, ablated=frozenset())
    op_b = WallfixTangentOperator(solver2, hot_base, bb, cold_base, cb,
                                  h=5e-5, ablated=frozenset(),
                                  repin="uniform", extrap="row1")
    vf, vg, _ = make_probe(hot_base.f.shape, hot_base.g.shape)
    ra = op_a.step(1e-6 * vf, 1e-6 * vg, 1e-6 * th0)
    rb = op_b.step(1e-6 * vf, 1e-6 * vg, 1e-6 * th0)
    assert np.array_equal(ra[0], rb[0]) and np.array_equal(ra[1], rb[1])
    assert ra[2] == rb[2] and ra[3] == rb[3]
    # hot-base non-degeneracy of the family: V2EQ tangent must differ
    op_c = WallfixTangentOperator(solver2, hot_base, bb, cold_base, cb,
                                  h=5e-5, ablated=frozenset(),
                                  repin="eqshape", extrap="row1")
    rc = op_c.step(1e-6 * vf, 1e-6 * vg, 1e-6 * th0)
    rel = float(np.max(np.abs(rc[1] - rb[1]))) / max(
        float(np.max(np.abs(rb[1]))), 1e-300)
    assert rel > 1e-10


def test_fail_loud_modes(rig):
    solver, th0 = rig["solver"], rig["th0"]
    f, g = rig["f"].copy(), rig["g"].copy()
    with pytest.raises(ValueError):
        reconstruct_row0_symmetric_v2(solver, f, g, th0,
                                      extrap="row1", repin="not_a_mode")
    with pytest.raises(ValueError):
        reconstruct_row0_symmetric_v2(solver, f, g, th0,
                                      extrap="cubic", repin="uniform")
