"""D1 candidate-B face-flux wall contract tests (D0-7 diagnostic unit).

Mechanism-level guards for boundary/wall_face_flux.py, core/tangent_faceflux.py
and scripts/phase5_faceflux_wall_scan.py:

- single-step contract (D1.72/D1.70): the band operation conserves total mass
  exactly, pins the band-row velocity to zero, touches only the band row, and
  changes the grid energy by EXACTLY the formula flux;
- A2-5 removal at instrument level (the unit's defining structural fact): the
  band's wall-temperature drive gain equals 2*nx*G_f and is INDEPENDENT of the
  band-row density — the production wall's c_v*rho_row storage gain is absent
  by construction, not by measurement;
- frozen conductance: G_f = k_nom/d_f with k_nom = alpha_lu*rho_ref*c_p, no
  hidden temperature/density dependence;
- geometry pairing: the faceflux rig runs hs_prod+1 (state matching, D1
  section 13.5 item 2);
- judgement reuse: the runner classifies with the PRE-REGISTERED wallfix
  classify() (same function object), and routes PROD payloads to the wallfix
  workers (bitwise production anchor inherited from the wallfix contract
  tests);
- fail-loud: non-positive face temperature, non-positive conductance, tiny
  grids, pathological negative row-temperature target.

No scan verdicts here — judgement lines live frozen in the runner constants.
"""

from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pytest

from boundary.wall_face_flux import (
    FACE_DISTANCE_LU,
    faceflux_conductance_lu,
    faceflux_formula_flux,
    faceflux_reconstruct_row_symmetric,
    make_faceflux_band_callback,
)
from core.macroscopic import recover_macro
from core.solver import GasSolver2D
from core.tangent_faceflux import (
    FaceFluxTangentOperator,
    compute_stage_bases_faceflux,
    stage_band_faceflux,
)
from core.tangent_step import BaseState
from scripts.phase2_m2_verification import load_config
from scripts.phase5_faceflux_wall_scan import (
    _dispatch_settle,
    _dispatch_tangent,
    proto_for,
)
from scripts.phase5_g4a_dc_basestate import make_energy_audited_band
from scripts.phase5_wallfix_arbitration import (
    PROTO,
    _settle_worker as _wallfix_settle_worker,
    _tangent_worker as _wallfix_tangent_worker,
    classify as wallfix_classify,
)
from scripts.phase5_faceflux_wall_scan import classify as runner_classify

BASE = load_config(Path("configs/gas_air_10k_d2q37_levelc_dx2p6.yaml"))


def _solver(ny=10, nx=4):
    cfg = copy.deepcopy(BASE)
    cfg["numerics"] = {**cfg["numerics"], "nx": nx, "ny": ny}
    return GasSolver2D(cfg)


def _seeded_tent(solver, theta_dc=0.05, steps=3):
    ny, nx = solver.ny, solver.nx
    th0 = float(solver.mapping.theta_ref_lu)
    rho0 = float(solver.mapping.lattice.rho_ref_lu)
    hs = ny // 2
    y = np.arange(ny)
    dist = np.minimum(y, ny - y)
    prof = th0 * (1.0 + theta_dc * (1.0 - dist / hs))
    theta = np.tile(prof[:, None], (1, nx))
    solver.initialize_from_macro(rho0 * th0 / theta, np.zeros((ny, nx, 2)), theta)
    solver.step(steps)
    return solver.f.copy(), solver.g.copy()


def test_single_step_contract_mass_velocity_energy_and_locality():
    s = _solver()
    f0, g0 = _seeded_tent(s)
    th0 = float(s.mapping.theta_ref_lu)
    theta_w = th0 * 1.05
    g_face = faceflux_conductance_lu(s.mapping)
    c2 = np.sum(np.asarray(s.lattice.c, float) ** 2, axis=-1)

    q_up, q_dn = faceflux_formula_flux(s, f0, g0, theta_w, row=0, g_face=g_face)
    f1, g1 = faceflux_reconstruct_row_symmetric(
        s, f0.copy(), g0.copy(), theta_w, row=0, g_face=g_face)

    # mass: total exactly conserved (streamed row density kept)
    assert abs(np.sum(f1) - np.sum(f0)) <= 1e-12 * abs(np.sum(f0))
    # locality: only the band row was written
    assert np.array_equal(f1[1:], f0[1:]) and np.array_equal(g1[1:], g0[1:])
    # velocity: band row pinned to u = 0 at machine precision
    m = recover_macro(f1[0:1], g1[0:1], D=2, S=3, lattice=s.lattice)
    assert float(np.max(np.abs(m.u))) < 1e-13
    # energy: grid delta equals the formula flux exactly (D1.70)
    de = (float(np.sum(0.5 * f1 * c2) + np.sum(g1))
          - float(np.sum(0.5 * f0 * c2) + np.sum(g0)))
    dq = float(np.sum(q_up + q_dn))
    # tolerance on the GRID-ENERGY scale: de is a difference of two O(10) LU
    # sums, so its floating noise floor is ~1e-15 absolute regardless of dq
    assert abs(de - dq) <= 1e-12


def test_audited_wrapper_measures_the_formula_flux():
    s = _solver()
    f0, g0 = _seeded_tent(s)
    th0 = float(s.mapping.theta_ref_lu)
    theta_w = th0 * 1.03
    g_face = faceflux_conductance_lu(s.mapping)
    rec: dict[str, list[float]] = {}
    cb = make_energy_audited_band(
        make_faceflux_band_callback(theta_w, 0, g_face=g_face),
        rec, s.lattice, "hot")
    q_up, q_dn = faceflux_formula_flux(s, f0, g0, theta_w, row=0, g_face=g_face)
    cb(solver=s, f_post=f0, g_post=g0, f_stream=f0.copy(), g_stream=g0.copy())
    dq = float(np.sum(q_up + q_dn))
    assert abs(rec["hot_dE"][-1] - dq) <= 1e-12
    # and the wall is mass-neutral in the wrapper's own reading
    assert abs(rec["hot_dM"][-1]) <= 1e-12


def test_drive_gain_is_transport_not_storage():
    """The unit's defining structural fact: d(heat)/d(theta_w) = 2*nx*G_f,
    independent of the band-row density (the production wall's c_v*rho_row
    storage gain is absent)."""

    s = _solver()
    f0, g0 = _seeded_tent(s)
    th0 = float(s.mapping.theta_ref_lu)
    g_face = faceflux_conductance_lu(s.mapping)
    # the formula is EXACTLY linear in theta_w, so a large step carries no
    # truncation error and lifts the signal above the O(1e-15) noise of the
    # grid-energy sums the bookkeeping differences
    h = 1e-3 * th0
    hs = s.ny // 2

    def drive_gain(f, g):
        bp = stage_band_faceflux(s, f, g, th0 * 1.05 + h, th0, hs, g_face=g_face)
        bm = stage_band_faceflux(s, f, g, th0 * 1.05 - h, th0, hs, g_face=g_face)
        return (bp[2] - bm[2]) / (2.0 * h)

    gain = drive_gain(f0, g0)
    expected = 2.0 * s.nx * g_face          # both faces, all columns
    assert gain == pytest.approx(expected, rel=1e-9)

    # scale the band-row f content by 1.2 (row density x1.2, neighbours
    # untouched): the drive gain must NOT move — no rho_row factor
    f_scaled = f0.copy()
    f_scaled[0] *= 1.2
    g_scaled = g0.copy()
    g_scaled[0] *= 1.2
    gain_scaled = drive_gain(f_scaled, g_scaled)
    assert gain_scaled == pytest.approx(expected, rel=1e-9)
    assert gain_scaled == pytest.approx(gain, rel=1e-9)


def test_frozen_conductance_value_and_formula():
    s = _solver()
    m = s.mapping
    c_p = 0.5 * (int(m.lattice.D) + int(m.lattice.S)) + 1.0
    expected = float(m.alpha_lu) * float(m.lattice.rho_ref_lu) * c_p \
        / FACE_DISTANCE_LU
    assert faceflux_conductance_lu(m) == pytest.approx(expected, rel=1e-14)
    # the formula flux is exactly linear in (theta_w - theta_1)
    f0, g0 = _seeded_tent(s)
    th0 = float(s.mapping.theta_ref_lu)
    q1_u, q1_d = faceflux_formula_flux(s, f0, g0, th0 * 1.02, row=0,
                                       g_face=expected)
    q2_u, q2_d = faceflux_formula_flux(s, f0, g0, th0 * 1.04, row=0,
                                       g_face=expected)
    dq = (q2_u + q2_d) - (q1_u + q1_d)
    assert np.allclose(dq, 2.0 * expected * 0.02 * th0, rtol=1e-12)


def test_tangent_operator_runs_and_is_finite():
    s = _solver(ny=10, nx=4)
    th0 = float(s.mapping.theta_ref_lu)
    g_face = faceflux_conductance_lu(s.mapping)
    f0, g0 = _seeded_tent(s, theta_dc=0.05)
    hs = s.ny // 2
    base_h = BaseState(f=f0, g=g0, theta_w=th0 * 1.05, theta_amb=th0, hs=hs,
                       theta_dc_target=0.05, meta={})
    f0c, g0c = _seeded_tent(_solver(ny=10, nx=4), theta_dc=0.0)
    base_c = BaseState(f=f0c, g=g0c, theta_w=th0, theta_amb=th0, hs=hs,
                       theta_dc_target=0.0, meta={})
    bh = compute_stage_bases_faceflux(s, base_h, g_face=g_face)
    bc = compute_stage_bases_faceflux(s, base_c, g_face=g_face)
    op = FaceFluxTangentOperator(s, base_h, bh, base_c, bc, h=5e-5,
                                 ablated=frozenset(), g_face=g_face)
    rng = np.random.default_rng(20260817)
    df = rng.standard_normal(f0.shape) * 1e-7
    dg = rng.standard_normal(g0.shape) * 1e-7
    d_hf, d_hg, d_hot, d_sink = op.step(df, dg, 1e-4 * th0)
    assert np.all(np.isfinite(d_hf)) and np.all(np.isfinite(d_hg))
    assert np.isfinite(d_hot) and np.isfinite(d_sink)
    # zero input -> exactly zero output (frozen-chain convention)
    z = op.step(np.zeros_like(df), np.zeros_like(dg), 0.0)
    assert float(np.max(np.abs(z[0]))) == 0.0 and z[2] == 0.0


def test_geometry_pairing_state_matching():
    for mode in ("smoke", "auth"):
        assert proto_for(mode, "PROD")["hs_rows"] == PROTO[mode]["hs_rows"]
        assert proto_for(mode, "FACEFLUX")["hs_rows"] \
            == PROTO[mode]["hs_rows"] + 1
    # face-to-face thickness equals the production node-to-node H_s
    assert (proto_for("auth", "FACEFLUX")["hs_rows"] - 1) \
        == PROTO["auth"]["hs_rows"]


def test_runner_reuses_preregistered_judgement_and_prod_workers():
    assert runner_classify is wallfix_classify
    # dispatchers route PROD to the wallfix workers (bitwise anchor inherited)
    import scripts.phase5_faceflux_wall_scan as ff

    assert ff._prod_settle_worker is _wallfix_settle_worker
    assert ff._prod_tangent_worker is _wallfix_tangent_worker
    assert _dispatch_settle.__module__ == ff.__name__
    assert _dispatch_tangent.__module__ == ff.__name__


def test_fail_loud_paths():
    s = _solver()
    f0, g0 = _seeded_tent(s)
    g_face = faceflux_conductance_lu(s.mapping)
    with pytest.raises(ValueError):
        faceflux_reconstruct_row_symmetric(s, f0.copy(), g0.copy(), -1.0,
                                           row=0, g_face=g_face)
    with pytest.raises(ValueError):
        make_faceflux_band_callback(0.05, 0, g_face=0.0)
    tiny = _solver(ny=4, nx=4)
    tiny.initialize_from_macro(
        np.ones((4, 4)), np.zeros((4, 4, 2)),
        np.full((4, 4), float(tiny.mapping.theta_ref_lu)))
    with pytest.raises(ValueError):
        faceflux_reconstruct_row_symmetric(tiny, tiny.f, tiny.g, 0.05,
                                           row=0, g_face=g_face)
    # pathological negative row-temperature target fails loudly: a huge frozen
    # conductance with theta_w far below theta_1 drives E_target negative
    s2 = _solver()
    f2, g2 = _seeded_tent(s2)
    with pytest.raises(RuntimeError):
        faceflux_reconstruct_row_symmetric(
            s2, f2.copy(), g2.copy(),
            1.0e-3 * float(s2.mapping.theta_ref_lu),
            row=0, g_face=g_face * 1e6)
