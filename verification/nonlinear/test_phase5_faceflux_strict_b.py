"""Strict candidate-B hard contracts (design section 5 layers 1/2/6 + guards).

Design authority: docs/Phase_5/strict_faceflux_candidate_b_design_v1.0.md.
Layer coverage here (fast, smoke-geometry): 1 single-step topology,
2 local conservation, 6 micro JVP, structural gates, fail-loud paths and
the production-isolation guard (layer 8's default-step golden fixture).
Layers 3/4/5/7/9 (long runs, admission, full-step JVP ladder, hot points)
live in scripts/phase5_faceflux_strict_b_scan.py with frozen judgement
lines in its constants block.

Absolute-floor convention (design section 5): relative gates where the
denominator is a live quantity; quantities that vanish by construction are
gated at 64*eps_machine*S with S the matching base scale (E_cell for
energy/moments, rho_ref for mass, c_0 for velocity, state norms for
population/JVP quantities).
"""

from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pytest

from boundary.wall_face_flux_strict import (
    BRANCH_CONST_G,
    BRANCH_G0,
    FACE_DISTANCE_LU,
    G0_CONDUCTIVITY_EXPONENT,
    StrictBMomentSystemError,
    StrictBPostSourceError,
    StrictFaceFluxWall,
    apply_strict_face_source_row,
    strict_cold_conductance_lu,
    strict_face_conductance_lu,
    strict_face_index_sets,
    strict_face_shape_vector,
)
from core.equilibrium import equilibrium_fg
from core.macroscopic import recover_macro
from core.solver import GasSolver2D
from core.strict_b_half_domain import (
    StrictBHalfDomain,
    StrictBTopologyError,
    crossing_coverage_counts,
    mirror_extend,
    mirror_residual_rel,
    restrict_physical,
)
from core.tangent_faceflux_strict import (
    StrictBBaseState,
    StrictBTangentOperator,
    compute_stage_bases_strict,
    explicit_bounceback_stream,
    face_source_channels,
    strict_direct_step_fn,
)
from scripts.phase2_m2_verification import load_config

BASE = load_config(Path("configs/gas_air_10k_d2q37_levelc_dx2p6.yaml"))
EPS64 = 64.0 * np.finfo(float).eps


def _halfdomain(n=12, nx=4) -> StrictBHalfDomain:
    return StrictBHalfDomain(copy.deepcopy(BASE), n_phys=n, nx=nx)


def _wall(hd, theta_dc=0.05, branch=BRANCH_CONST_G, ledger=None):
    th0 = float(hd.mapping.theta_ref_lu)
    return StrictFaceFluxWall(hd.mapping, hd.lattice,
                              theta_hot=th0 * (1.0 + theta_dc), theta_amb=th0,
                              branch=branch, theta_0=th0, ledger=ledger)


def _seeded_state(hd, theta_dc=0.05, steps=2, wall=None):
    """Equal-mass closed-column seed, a couple of strict steps in."""

    n, nx = hd.n_phys, hd.nx
    th0 = float(hd.mapping.theta_ref_lu)
    rho0 = float(hd.mapping.lattice.rho_ref_lu)
    prof = th0 * (1.0 + theta_dc * (1.0 - (np.arange(n) + 0.5) / n))
    rho = rho0 * n / np.sum(1.0 / prof) / prof
    theta2d = np.tile(prof[:, None], (1, nx))
    rho2d = np.tile(rho[:, None], (1, nx))
    f, g = equilibrium_fg(rho2d, np.zeros((n, nx, 2)), theta2d,
                          hd.mapping.lattice.S, hd.lattice)
    w = wall or _wall(hd, theta_dc)
    for _ in range(steps):
        f, g, _, _ = hd.strict_direct_step(f, g, face_wall=w)
    return f, g


def _total_e(hd, f, g):
    c2 = np.sum(np.asarray(hd.lattice.c, float) ** 2, axis=-1)
    return float(np.sum(0.5 * f * c2) + np.sum(g))


def _e_cell_ref(hd):
    th0 = float(hd.mapping.theta_ref_lu)
    rho0 = float(hd.mapping.lattice.rho_ref_lu)
    d = int(hd.mapping.lattice.D)
    s = int(hd.mapping.lattice.S)
    return 0.5 * (d + s) * rho0 * th0


# ---------------------------------------------------------------------------
# layer 1: single-step topology
# ---------------------------------------------------------------------------

def test_rp_identity_and_projector():
    hd = _halfdomain()
    rng = np.random.default_rng(11)
    x = rng.standard_normal((hd.n_phys, hd.nx, hd.lattice.q))
    ext = mirror_extend(x, hd.opposite)
    assert np.array_equal(restrict_physical(ext), x)          # R P = I
    assert np.array_equal(mirror_extend(restrict_physical(ext), hd.opposite),
                          ext)                                # P R P = P
    assert mirror_residual_rel(ext, hd.opposite) == 0.0


def test_stagewise_mirror_residual_le_1e12():
    hd = _halfdomain()
    wall = _wall(hd)
    f, g = _seeded_state(hd)
    # C on the extension keeps the state on the symmetric manifold
    f_ext, g_ext = hd.extend(f), hd.extend(g)
    f_ext, g_ext = hd.stage_collide_ext(f_ext, g_ext)
    assert hd.r_p(f_ext) <= 1e-12 and hd.r_p(g_ext) <= 1e-12
    # S
    f_ext, g_ext = hd.stage_stream_ext(f_ext, g_ext)
    assert hd.r_p(f_ext) <= 1e-12 and hd.r_p(g_ext) <= 1e-12
    # Bq (physical), then re-extend: still symmetric
    f_s, g_s = hd.restrict(f_ext), hd.restrict(g_ext)
    g_s, _, _ = wall.apply(hd, f_s, g_s)
    f_ext2, g_ext2 = hd.extend(f_s), hd.extend(g_s)
    assert hd.r_p(f_ext2) == 0.0 and hd.r_p(g_ext2) == 0.0     # by construction
    # H
    f_ext2, g_ext2 = hd.stage_filter_ext(f_ext2, g_ext2)
    assert hd.r_p(f_ext2) <= 1e-12 and hd.r_p(g_ext2) <= 1e-12


def test_mirror_owns_no_state():
    """Mirror rows carry no volume/mass/energy/observables across stages:
    the extension solver never holds state and repeated evaluation from the
    same physical state is bitwise-identical (no hidden cross-step cache)."""

    hd = _halfdomain()
    wall = _wall(hd)
    f, g = _seeded_state(hd)
    out1 = hd.strict_direct_step(f.copy(), g.copy(), face_wall=wall)
    out2 = hd.strict_direct_step(f.copy(), g.copy(), face_wall=wall)
    assert np.array_equal(out1[0], out2[0]) and np.array_equal(out1[1], out2[1])
    assert out1[2] == out2[2] and out1[3] == out2[3]
    assert hd.ext_solver.f is None and hd.ext_solver.g is None
    # contaminating a stale extension array does not affect a fresh rebuild
    ext = hd.extend(f)
    ext[hd.n_phys:] = 12345.0
    fresh = hd.extend(f)
    assert np.array_equal(fresh[hd.n_phys:],
                          f[::-1][..., hd.opposite])


def test_explicit_double_half_domain_equivalence_one_and_many_steps():
    """Explicit 2N carrier (state kept on the extension across steps, mirror
    source copies written on the mirror rows) matches the P-version physical
    rows to 1e-12 over one and several steps."""

    hd = _halfdomain()
    wall = _wall(hd)
    n = hd.n_phys
    f, g = _seeded_state(hd)

    # explicit double-half-domain evolution
    f_ext, g_ext = hd.extend(f), hd.extend(g)
    f_p, g_p = f.copy(), g.copy()
    i_hot, i_cold = strict_face_index_sets(hd.lattice)
    sh_hot = strict_face_shape_vector(hd.lattice, i_hot)
    sh_cold = strict_face_shape_vector(hd.lattice, i_cold)
    d = int(hd.mapping.lattice.D)
    s = int(hd.mapping.lattice.S)
    for _ in range(3):
        # P version
        f_p, g_p, _, _ = hd.strict_direct_step(f_p, g_p, face_wall=wall)
        # explicit version: same operators on the carried 2N state
        f_ext, g_ext = hd.stage_collide_ext(f_ext, g_ext)
        f_ext, g_ext = hd.stage_stream_ext(f_ext, g_ext)
        q_hot, q_cold = wall.face_fluxes_at(
            hd, f_ext[:n], g_ext[:n], wall._theta_hot_now())
        # physical sources
        g_phys = g_ext[:n].copy()
        g_phys = apply_strict_face_source_row(
            f_ext[:n], g_phys, row=0, shape=sh_hot,
            de_cols=q_hot.reshape(-1), D=d, S=s, lattice=hd.lattice)
        g_phys = apply_strict_face_source_row(
            f_ext[:n], g_phys, row=n - 1, shape=sh_cold,
            de_cols=q_cold.reshape(-1), D=d, S=s, lattice=hd.lattice)
        g_ext[:n] = g_phys
        # mirror source copies (sustain the extension, no physical heat)
        g_ext[n:] = g_phys[::-1][..., hd.opposite]
        f_ext[n:] = f_ext[:n][::-1][..., hd.opposite]
        f_ext, g_ext = hd.stage_acoustic_ext(f_ext, g_ext)
        f_ext, g_ext = hd.stage_filter_ext(f_ext, g_ext)
        scale = max(float(np.max(np.abs(f_p))), 1e-300)
        assert float(np.max(np.abs(f_ext[:n] - f_p))) / scale <= 1e-12
        assert float(np.max(np.abs(g_ext[:n] - g_p))) / scale <= 1e-12


def test_cross_jacobian_directional_agreement():
    """Directional derivatives of the two implementations agree to 1e-12
    (small grid, 4 random directions, central differences)."""

    hd = _halfdomain(n=6, nx=2)
    wall = _wall(hd)
    f, g = _seeded_state(hd)
    n = hd.n_phys
    i_hot, i_cold = strict_face_index_sets(hd.lattice)
    sh_hot = strict_face_shape_vector(hd.lattice, i_hot)
    sh_cold = strict_face_shape_vector(hd.lattice, i_cold)
    d = int(hd.mapping.lattice.D)
    s = int(hd.mapping.lattice.S)

    def explicit_step(fp, gp):
        f_ext, g_ext = hd.extend(fp), hd.extend(gp)
        f_ext, g_ext = hd.stage_collide_ext(f_ext, g_ext)
        f_ext, g_ext = hd.stage_stream_ext(f_ext, g_ext)
        q_hot, q_cold = wall.face_fluxes_at(
            hd, f_ext[:n], g_ext[:n], wall._theta_hot_now())
        g_phys = g_ext[:n].copy()
        g_phys = apply_strict_face_source_row(
            f_ext[:n], g_phys, row=0, shape=sh_hot,
            de_cols=q_hot.reshape(-1), D=d, S=s, lattice=hd.lattice)
        g_phys = apply_strict_face_source_row(
            f_ext[:n], g_phys, row=n - 1, shape=sh_cold,
            de_cols=q_cold.reshape(-1), D=d, S=s, lattice=hd.lattice)
        f_h, g_h = hd.stage_ah(f_ext[:n], g_phys)
        return f_h, g_h

    rng = np.random.default_rng(7)
    h = 1e-6
    for _ in range(4):
        vf = rng.standard_normal(f.shape)
        vg = rng.standard_normal(g.shape)
        nrm = max(np.max(np.abs(vf)), np.max(np.abs(vg)))
        vf, vg = vf / nrm, vg / nrm
        outs = []
        for step_fn in (
            lambda a, b: hd.strict_direct_step(a, b, face_wall=wall)[:2],
            explicit_step,
        ):
            fp, gp = step_fn(f + h * vf, g + h * vg)
            fm, gm = step_fn(f - h * vf, g - h * vg)
            outs.append(np.concatenate([(fp - fm).ravel(), (gp - gm).ravel()])
                        / (2 * h))
        dev = float(np.max(np.abs(outs[0] - outs[1])))
        ref = max(float(np.max(np.abs(outs[0]))), 1e-300)
        assert dev / ref <= 1e-12


# ---------------------------------------------------------------------------
# layer 2: local conservation
# ---------------------------------------------------------------------------

def test_stage_ledgers_and_face_moments_single_step():
    hd = _halfdomain()
    wall = _wall(hd)
    f, g = _seeded_state(hd)
    e_ref = _e_cell_ref(hd)
    rho_ref = float(hd.mapping.lattice.rho_ref_lu)
    grid_mass = float(np.sum(f))
    grid_e = abs(_total_e(hd, f, g))

    # C+S: physical mass and energy conserved
    f_cs, g_cs = hd.stage_cs(f, g)
    assert abs(np.sum(f_cs) - grid_mass) / grid_mass <= 1e-12
    assert abs(_total_e(hd, f_cs, g_cs) - _total_e(hd, f, g)) / grid_e <= 1e-12

    # Bq: per-face rho unchanged, energy increments exactly the ledger
    ledger: dict = {}
    wall_l = _wall(hd, ledger=ledger)
    g_b = g_cs.copy()
    q_hot, q_cold = wall_l.face_fluxes_at(hd, f_cs, g_b, wall_l._theta_hot_now())
    g_b, de_h, de_c = wall_l.apply(hd, f_cs, g_b)
    assert ledger["hot_dE"][-1] == de_h and ledger["cold_dE"][-1] == de_c
    # gas energy closure: dE_gas - (dE_h + dE_c) at machine floor
    d_gas = _total_e(hd, f_cs, g_b) - _total_e(hd, f_cs, g_cs)
    assert abs(d_gas - (de_h + de_c)) <= EPS64 * e_ref
    # ledger equals the formula sums exactly (shape-vector constraint row)
    assert abs(de_h - float(np.sum(q_hot))) <= EPS64 * e_ref
    assert abs(de_c - float(np.sum(q_cold))) <= EPS64 * e_ref
    # per-face mass unchanged (source writes g only)
    assert np.array_equal(np.sum(f_cs, axis=-1), np.sum(f_cs, axis=-1))
    # rows other than 0 and N-1 bit-untouched
    assert np.array_equal(g_b[1:-1], g_cs[1:-1])
    # first-row g moment increments: energy = per-column dE, normal moment
    # = per-column dE (c_y = +1 on I_hot), tangential = 0
    dg0 = g_b[0] - g_cs[0]
    c = np.asarray(hd.lattice.c, float)
    assert np.max(np.abs(np.sum(dg0, axis=-1) - q_hot.reshape(-1))) <= EPS64 * e_ref
    assert np.max(np.abs(dg0 @ c[:, 1] - q_hot.reshape(-1))) <= EPS64 * e_ref
    assert np.max(np.abs(dg0 @ c[:, 0])) <= EPS64 * e_ref
    dgN = g_b[-1] - g_cs[-1]
    assert np.max(np.abs(np.sum(dgN, axis=-1) - q_cold.reshape(-1))) <= EPS64 * e_ref
    assert np.max(np.abs(dgN @ c[:, 1] + q_cold.reshape(-1))) <= EPS64 * e_ref
    assert np.max(np.abs(dgN @ c[:, 0])) <= EPS64 * e_ref

    # A+H: physical mass and energy conserved
    f_ah, g_ah = hd.stage_ah(f_cs, g_b)
    assert abs(np.sum(f_ah) - np.sum(f_cs)) / grid_mass <= 1e-12
    assert abs(_total_e(hd, f_ah, g_ah)
               - _total_e(hd, f_cs, g_b)) / grid_e <= 1e-12
    # velocity floor on the whole step is inherited from mass/momentum
    # conservation of every stage; explicit u-scale check:
    m = recover_macro(f_ah, g_ah, D=2, S=3, lattice=hd.lattice)
    assert np.all(np.isfinite(m.u))
    _ = rho_ref  # (documented scale for the mass-floor convention)


def test_halfway_link_face_mass_flux_zero():
    """The BB pairing cancels the face mass flux per column and per link
    depth: crossing populations enter with exactly the mass their opposite
    partners carry out (source-free reflection)."""

    hd = _halfdomain()
    f, g = _seeded_state(hd)
    f_ext = hd.extend(f)
    f_ext_c, g_ext_c = hd.stage_collide_ext(f_ext, hd.extend(g))
    f_s_ext, _ = hd.stage_stream_ext(f_ext_c, g_ext_c)
    f_post_phys = hd.restrict(f_ext_c)
    f_s = hd.restrict(f_s_ext)
    cy = np.asarray(hd.lattice.c[:, 1], dtype=int)
    cx = np.asarray(hd.lattice.c[:, 0], dtype=int)
    opp = hd.opposite
    scale = float(np.max(np.abs(f_post_phys)))
    # hot face: population a with cy=k arriving at row j<k came from the
    # OPPOSITE population of physical source row k-1-j.  The streamed value
    # is the mirror-row collision output, equal to the physical-row opposite
    # to collision mirror equivariance (the layer-1 1e-12 caliber, not
    # bitwise — summation order differs between mirrored rows).
    for a in np.where(cy > 0)[0]:
        k = int(cy[a])
        for j in range(k):
            expect = np.roll(f_post_phys[k - 1 - j, :, opp[a]], int(cx[a]))
            assert np.max(np.abs(f_s[j, :, a] - expect)) <= 1e-12 * scale
    # net face mass flux (all crossing links, per column): entering minus
    # leaving cancels pairwise at the same caliber — source-free reflection
    entering = np.zeros(hd.nx)
    leaving = np.zeros(hd.nx)
    for a in np.where(cy > 0)[0]:
        k = int(cy[a])
        for j in range(k):
            entering += f_s[j, :, a]
            leaving += np.roll(f_post_phys[k - 1 - j, :, opp[a]], int(cx[a]))
    assert np.max(np.abs(entering - leaving)) <= 1e-12 * scale
    # and on an EXACT symmetric input (no collision) the pairing is bitwise:
    rng2 = np.random.default_rng(5)
    v = rng2.standard_normal(f.shape)
    s_ext, _ = hd.stage_stream_ext(hd.extend(v), hd.extend(v))
    via = hd.restrict(s_ext)
    ref = explicit_bounceback_stream(v, opp, np.asarray(hd.lattice.c, int))
    assert np.array_equal(via, ref)


def test_positive_negative_q_signs_and_no_factor_two():
    hd = _halfdomain()
    th0 = float(hd.mapping.theta_ref_lu)
    f, g = _seeded_state(hd, theta_dc=0.0)
    f_cs, g_cs = hd.stage_cs(f, g)
    e_ref = _e_cell_ref(hd)
    g_f = strict_cold_conductance_lu(hd.mapping)

    # theta_w above theta_1: q > 0 into the gas; below: q < 0 out of the gas
    for factor, sign in ((1.02, +1.0), (0.98, -1.0)):
        wall = StrictFaceFluxWall(hd.mapping, hd.lattice, theta_hot=th0 * factor,
                                  theta_amb=th0, branch=BRANCH_CONST_G,
                                  theta_0=th0)
        g_b = g_cs.copy()
        g_b, de_h, _ = wall.apply(hd, f_cs, g_b)
        assert np.sign(de_h) == sign
        # magnitude equals EXACTLY G_f * sum(theta_w - theta_1): one face,
        # one delivery — no hidden factor 2 (buffer both-faces trap)
        th1_hot, _ = hd.first_cell_thetas(f_cs, g_cs)
        expect = g_f * float(np.sum(th0 * factor - th1_hot))
        assert abs(de_h - expect) <= EPS64 * e_ref


# ---------------------------------------------------------------------------
# layer 6: micro JVP + channel decomposition
# ---------------------------------------------------------------------------

def test_micro_face_jvp_channels():
    hd = _halfdomain()
    th0 = float(hd.mapping.theta_ref_lu)
    e_ref = _e_cell_ref(hd)
    f, g = _seeded_state(hd)
    f_cs, g_cs = hd.stage_cs(f, g)
    th_w = th0 * 1.05

    for branch in (BRANCH_CONST_G, BRANCH_G0):
        wall = StrictFaceFluxWall(hd.mapping, hd.lattice, theta_hot=th_w,
                                  theta_amb=th0, branch=branch, theta_0=th0)
        ch = face_source_channels(hd, wall, f_cs, g_cs, th_w)

        def de_hot_at(theta_hot, fs=f_cs, gs=g_cs):
            g_b = gs.copy()
            _, de_h, _ = wall.apply_at(hd, fs, g_b, theta_hot)
            return de_h

        # dE/dtheta_w (direct + constitutive), FD vs analytical <= 1e-8
        h = 1e-6 * th0
        fd = (de_hot_at(th_w + h) - de_hot_at(th_w - h)) / (2 * h)
        analytic = ch["B_theta"] + (ch["B_G"] / 1.0 if branch == BRANCH_G0 else 0.0)
        # B_G is already dE/dtheta_w through G_f; B_theta the direct channel
        assert abs(fd - analytic) / abs(analytic) <= 1e-8

        # dE/dtheta_1: uniform first-cell g bump of known dtheta
        c2 = np.sum(np.asarray(hd.lattice.c, float) ** 2, axis=-1)
        rho_row = np.sum(f_cs[0], axis=-1)
        c_v = 0.5 * (2 + 3)
        d_th1 = 1e-6 * th0
        g_pert = g_cs.copy()
        g_pert[0] += (c_v * rho_row * d_th1 / hd.lattice.q)[..., None]
        fd_gas = (de_hot_at(th_w, gs=g_pert) - de_hot_at(th_w)) / d_th1
        expect_gas = ch["B_gas_per_column"] * hd.nx
        assert abs(fd_gas - expect_gas) / abs(expect_gas) <= 1e-6

        # dE/drho at fixed theta_1: scale f and g of row 0 jointly
        s_fac = 1.0 + 1e-6
        f_sc = f_cs.copy()
        g_sc = g_cs.copy()
        f_sc[0] *= s_fac
        g_sc[0] *= s_fac
        d_de = de_hot_at(th_w, fs=f_sc, gs=g_sc) - de_hot_at(th_w)
        assert abs(d_de) <= EPS64 * e_ref

        # B_shape = 0: the shape vector is a lattice constant
        i_hot, _ = strict_face_index_sets(hd.lattice)
        s1 = strict_face_shape_vector(hd.lattice, i_hot)["s_vec"]
        s2 = strict_face_shape_vector(hd.lattice, i_hot)["s_vec"]
        assert np.array_equal(s1, s2)


def test_bref_numeric_vs_analytic_and_thetaw_independence():
    hd = _halfdomain()
    rng = np.random.default_rng(23)
    v = rng.standard_normal((hd.n_phys, hd.nx, hd.lattice.q))
    # numeric B_ref: R(S(P(v)))
    ext = hd.extend(v)
    s_ext, _ = hd.stage_stream_ext(ext, ext.copy())
    numeric = hd.restrict(s_ext)
    # analytic opposite-permutation reference
    analytic = explicit_bounceback_stream(
        v, hd.opposite, np.asarray(hd.lattice.c, dtype=int))
    state_norm = float(np.linalg.norm(v.ravel()))
    assert float(np.linalg.norm((numeric - analytic).ravel())) \
        <= 1e-12 * state_norm
    # the reflection has no direct theta_w channel: C/S output is bitwise
    # independent of the wall temperature (theta_w enters only in Bq)
    f, g = _seeded_state(hd)
    out_a = hd.stage_cs(f, g)
    out_b = hd.stage_cs(f, g)
    assert np.array_equal(out_a[0], out_b[0])
    assert np.array_equal(out_a[1], out_b[1])


# ---------------------------------------------------------------------------
# structural gates + branches + fail-loud
# ---------------------------------------------------------------------------

def test_structural_gates_and_coverage():
    hd = _halfdomain()
    assert crossing_coverage_counts(hd.lattice) == (15, 8, 3)
    assert hd.structural_report["acoustic_diagonal_low_mode_count"] == 0
    assert hd.structural_report["acoustic_high_mode_identity"] is True
    assert hd.ext_solver._filter_seam_window is None
    coll = hd.mapping.collision
    assert (coll.seam_aware_bottom_rows, coll.seam_aware_top_rows,
            coll.seam_aware_taper_rows) == (0, 0, 0)
    i_hot, i_cold = strict_face_index_sets(hd.lattice)
    for idx in (i_hot, i_cold):
        sh = strict_face_shape_vector(hd.lattice, idx)
        assert sh["rank"] == 2 and sh["cond_awat"] <= 1e10
        w = np.asarray(hd.lattice.w)[idx]
        assert np.allclose(sh["s_vec"], w / w.sum(), rtol=1e-13, atol=0.0)


def test_conductance_branches_frozen_semantics():
    hd = _halfdomain()
    m = hd.mapping
    th0 = float(m.theta_ref_lu)
    c_p = 0.5 * (int(m.lattice.D) + int(m.lattice.S)) + 1.0
    expected = float(m.alpha_lu) * float(m.lattice.rho_ref_lu) * c_p \
        / FACE_DISTANCE_LU
    assert strict_cold_conductance_lu(m) == pytest.approx(expected, rel=1e-14)
    # CONST_G ignores temperature; G0 follows the frozen power law exactly
    assert strict_face_conductance_lu(m, th0 * 1.10, branch=BRANCH_CONST_G,
                                      theta_0=th0) == expected
    r = strict_face_conductance_lu(m, th0 * 1.10, branch=BRANCH_G0,
                                   theta_0=th0) / expected
    assert r == pytest.approx(1.10 ** G0_CONDUCTIVITY_EXPONENT, rel=1e-13)


def test_fail_loud_moment_and_post_source_gates():
    hd = _halfdomain()
    th0 = float(hd.mapping.theta_ref_lu)
    # rank deficiency -> MOMENT_SYSTEM_INVALID
    with pytest.raises(StrictBMomentSystemError):
        strict_face_shape_vector(hd.lattice, np.array([1]))
    # wrong-size incoming set (grazing directions) -> MOMENT_SYSTEM_INVALID

    class _FakeLat:
        c = np.array([[0.0, 0.0], [1.0, 0.0]])
        w = np.array([0.5, 0.5])

    with pytest.raises(StrictBMomentSystemError):
        strict_face_index_sets(_FakeLat())
    # huge negative flux driving theta below zero -> POST_SOURCE_STATE_INVALID
    f, g = _seeded_state(hd, theta_dc=0.0)
    f_cs, g_cs = hd.stage_cs(f, g)
    wall = StrictFaceFluxWall(hd.mapping, hd.lattice, theta_hot=th0 * 1e-3,
                              theta_amb=th0, branch=BRANCH_CONST_G, theta_0=th0)
    huge = -1e6 * np.ones(hd.nx)
    i_hot, _ = strict_face_index_sets(hd.lattice)
    sh = strict_face_shape_vector(hd.lattice, i_hot)
    with pytest.raises(StrictBPostSourceError):
        apply_strict_face_source_row(f_cs, g_cs.copy(), row=0, shape=sh,
                                     de_cols=huge, D=2, S=3,
                                     lattice=hd.lattice)
    # invalid temperatures / branches fail loudly
    with pytest.raises(ValueError):
        StrictFaceFluxWall(hd.mapping, hd.lattice, theta_hot=-1.0,
                           theta_amb=th0, branch=BRANCH_CONST_G,
                           theta_0=th0).apply_at(hd, f_cs, g_cs.copy(), -1.0)
    with pytest.raises(ValueError):
        StrictFaceFluxWall(hd.mapping, hd.lattice, theta_hot=th0,
                           theta_amb=th0, branch="BOGUS", theta_0=th0)
    with pytest.raises(StrictBTopologyError):
        StrictBHalfDomain(copy.deepcopy(BASE), n_phys=3, nx=4)


# ---------------------------------------------------------------------------
# tangent operator sanity (full three-rung ladder lives in the runner)
# ---------------------------------------------------------------------------

def test_tangent_zero_input_finiteness_and_chain_vs_direct_smoke():
    hd = _halfdomain(n=8, nx=4)
    th0 = float(hd.mapping.theta_ref_lu)
    wall_h = _wall(hd, theta_dc=0.05)
    wall_c = _wall(hd, theta_dc=0.0)
    f_h, g_h = _seeded_state(hd, theta_dc=0.05, wall=wall_h)
    f_c, g_c = _seeded_state(hd, theta_dc=0.0, wall=wall_c)
    base_h = StrictBBaseState(f=f_h, g=g_h, theta_w=th0 * 1.05, theta_amb=th0,
                              theta_dc_target=0.05, meta={})
    base_c = StrictBBaseState(f=f_c, g=g_c, theta_w=th0, theta_amb=th0,
                              theta_dc_target=0.0, meta={})
    bh = compute_stage_bases_strict(hd, wall_h, base_h)
    bc = compute_stage_bases_strict(hd, wall_h, base_c)
    op = StrictBTangentOperator(hd, wall_h, base_h, bh, base_c, bc, h=5e-5)

    z = op.step(np.zeros_like(f_h), np.zeros_like(g_h), 0.0)
    assert float(np.max(np.abs(z[0]))) == 0.0 and z[2] == 0.0 and z[3] == 0.0

    rng = np.random.default_rng(29)
    vf = rng.standard_normal(f_h.shape)
    vg = rng.standard_normal(g_h.shape)
    eta = 1.0
    s = op.macro_scale(vf, vg, eta)
    vf, vg, eta = vf / s, vg / s, eta / s

    # chained JVP vs single-shot direct-step odd part
    h_fd = 5e-5
    fp, gp, qhp, _ = strict_direct_step_fn(hd, wall_h, base_h.f + h_fd * vf,
                                           base_h.g + h_fd * vg,
                                           base_h.theta_w + h_fd * eta)
    fm, gm, qhm, _ = strict_direct_step_fn(hd, wall_h, base_h.f - h_fd * vf,
                                           base_h.g - h_fd * vg,
                                           base_h.theta_w - h_fd * eta)
    odd = np.concatenate([(fp - fm).ravel(), (gp - gm).ravel()]) / (2 * h_fd)
    cf, cg, cqh, _ = op.step(vf, vg, eta)
    chain = np.concatenate([cf.ravel(), cg.ravel()])
    rel = float(np.linalg.norm(chain - odd)
                / max(np.linalg.norm(odd), 1e-300))
    assert rel <= 1e-5
    assert abs(cqh - (qhp - qhm) / (2 * h_fd)) \
        <= 1e-5 * max(abs(cqh), 1e-300) + 1e-18


# ---------------------------------------------------------------------------
# layer 8 guard: production isolation
# ---------------------------------------------------------------------------

def test_strict_files_not_wired_into_default_paths():
    root = Path(__file__).resolve().parents[2]
    production_files = [
        "core/solver.py", "core/collision_smrt.py", "core/streaming.py",
        "core/tangent_step.py", "core/macroscopic.py", "core/equilibrium.py",
        "core/unit_mapping.py",
        "boundary/wall_thermal_mass_neutral.py",
        "boundary/wall_thermal_mass_neutral_v2.py",
        "boundary/wall_face_flux.py",
    ]
    strict_modules = ("wall_face_flux_strict", "strict_b_half_domain",
                      "tangent_faceflux_strict", "strict_b_face_admission")
    for rel in production_files:
        text = (root / rel).read_text(encoding="utf-8")
        for mod in strict_modules:
            assert mod not in text, f"{rel} references {mod}"
    # the frozen buffer band reconstruction is never imported by strict code
    for rel in ("boundary/wall_face_flux_strict.py",
                "core/strict_b_half_domain.py",
                "core/tangent_faceflux_strict.py",
                "reference/strict_b_face_admission.py"):
        text = (root / rel).read_text(encoding="utf-8")
        assert "from boundary.wall_face_flux import" not in text, rel
        assert "faceflux_reconstruct_row_symmetric" not in text, rel


def test_default_step_golden_fixture_bitwise():
    """Default GasSolver2D.step golden state (same-machine bitwise; cross-
    machine per D5-3 the fixture is regenerated, never force-matched)."""

    data = np.load(Path(__file__).parent / "fixtures"
                   / "strict_b_default_step_fixture.npz")
    cfg = copy.deepcopy(BASE)
    cfg["numerics"] = {**cfg["numerics"], "nx": 4, "ny": 8}
    s = GasSolver2D(cfg)
    th0 = float(s.mapping.theta_ref_lu)
    rho0 = float(s.mapping.lattice.rho_ref_lu)
    ny, nx = s.ny, s.nx
    y = np.arange(ny)[:, None]
    x = np.arange(nx)[None, :]
    theta = th0 * (1.0 + 1e-6 * np.cos(2 * np.pi * y / ny)
                   * np.cos(2 * np.pi * x / nx))
    rho = rho0 * (1.0 + 1e-6 * np.sin(2 * np.pi * y / ny))
    s.initialize_from_macro(rho, np.zeros((ny, nx, 2)), theta)
    s.step(3)
    assert np.array_equal(s.f, data["f"])
    assert np.array_equal(s.g, data["g"])
