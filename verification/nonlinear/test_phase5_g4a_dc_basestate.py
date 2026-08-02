"""G4a DC base-state machinery tests (contract §9.1 deliverable, WP2).

Mechanism-level certification of the tent-rig instrument chain: the band
generalization of the certified v1.1 wall (bitwise identity at row 0 and
bitwise equality with the roll-composition — the construction is exactly the
certified one relocated), the tent reference family (two-source superposition
on the certified coefficient structure vs the variable-coefficient BVP — same
operator, machine agreement; continuum coth anchor; alpha_eff-table
sensitivity non-degeneracy), the exact band energy bookkeeping (calibrated
against a prescribed equilibrium jump), and the case-assembly/state-matching
pre-registration. The authoritative G4a run verdict is NOT asserted here
(physics belongs to the gate, Phase5_STATUS §3).
"""

from __future__ import annotations

import copy
import math
from pathlib import Path

import numpy as np
import pytest

from boundary.wall_thermal_mass_neutral import (
    make_symmetric_mass_neutral_band_callback,
    make_symmetric_mass_neutral_wall_callback,
)
from core.macroscopic import recover_macro
from core.solver import GasSolver2D
from scripts.phase2_m2_verification import load_config
from scripts.phase5_g4a_dc_basestate import (
    assemble_cases,
    conduction_seed,
    make_energy_audited_band,
    tent_bvp_reference,
    tent_spectral_reference,
)

GAS = Path("configs/gas_air_10k_d2q37_levelc_dx2p6.yaml")
G4A_CFG = Path("configs/phase5/g4_dc_base/g4a_canonical_10k_dx2p6.yaml")

DT_S = 1.95881e-9
DX_M = 2.61175e-6
ALPHA_LU = 2.2233775895e-5 * DT_S / DX_M**2


def _mini_solver(ny=24, nx=6):
    cfg = copy.deepcopy(load_config(GAS))
    cfg["numerics"] = {**cfg["numerics"], "nx": nx, "ny": ny}
    return GasSolver2D(cfg)


def _generic_state(s, seed=3):
    ny, nx = s.ny, s.nx
    th0 = float(s.mapping.theta_ref_lu)
    rng = np.random.default_rng(seed)
    prof = th0 * (1.0 + 0.03 * rng.normal(size=ny))
    rho = float(s.mapping.lattice.rho_ref_lu) * th0 / prof
    u = 1e-4 * rng.normal(size=(ny, nx, 2))
    s.initialize_from_macro(np.tile(rho[:, None], (1, nx)), u,
                            np.tile(prof[:, None], (1, nx)))
    s.step(3)


def test_band_generalization_is_certified_wall_relocated():
    s = _mini_solver()
    _generic_state(s)
    th_b = float(s.mapping.theta_ref_lu) * 1.02
    hs = s.ny // 2
    # (a) row-0 band == original certified wall, bitwise
    f1, g1 = s.f.copy(), s.g.copy()
    f2, g2 = s.f.copy(), s.g.copy()
    fa, ga = make_symmetric_mass_neutral_band_callback(th_b, 0)(
        solver=s, f_post=None, g_post=None, f_stream=f1, g_stream=g1)
    fb, gb = make_symmetric_mass_neutral_wall_callback(th_b)(
        solver=s, f_post=None, g_post=None, f_stream=f2, g_stream=g2)
    assert np.array_equal(fa, fb) and np.array_equal(ga, gb)
    # (b) mid-row band == roll -> certified wall -> roll back, bitwise
    f3, g3 = s.f.copy(), s.g.copy()
    f4, g4 = s.f.copy(), s.g.copy()
    fc, gc = make_symmetric_mass_neutral_band_callback(th_b, hs)(
        solver=s, f_post=None, g_post=None, f_stream=f3, g_stream=g3)
    fr = np.roll(f4, -hs, axis=0)
    gr = np.roll(g4, -hs, axis=0)
    fr, gr = make_symmetric_mass_neutral_wall_callback(th_b)(
        solver=s, f_post=None, g_post=None, f_stream=fr, g_stream=gr)
    assert np.array_equal(fc, np.roll(fr, hs, axis=0))
    assert np.array_equal(gc, np.roll(gr, hs, axis=0))
    # (c) mass neutrality and setpoint pinning at the relocated row
    m = recover_macro(fc, gc, D=2, S=3, lattice=s.lattice)
    assert np.max(np.abs(m.theta[hs, :] - th_b)) < 1e-12
    assert abs(np.sum(fc) / np.sum(f3) - 1.0) < 1e-14


def test_tent_reference_family_identity_and_anchors():
    om = 2.0 * math.pi * 1.0e4 * DT_S
    n, hs = 96, 48
    kt = np.array([0.01, 3.2])
    at = np.array([ALPHA_LU, ALPHA_LU])
    ref = tent_spectral_reference(n, hs, om, ALPHA_LU, kt, at,
                                  highk_policy="hold_last", gamma=1.4)
    bvp = tent_bvp_reference(np.full(n, ALPHA_LU), hs, om, ALPHA_LU, gamma=1.4)
    # same operator: superposition == BVP to machine precision
    assert abs(bvp["Y_over_Yhs"] / ref["Y_over_Yhs"] - 1.0) < 1e-12
    assert np.max(np.abs(ref["profile_over_Tw"] - bvp["profile_over_Tw"])) < 1e-12
    # constraints exact
    assert abs(ref["profile_over_Tw"][0] - 1.0) < 1e-14
    assert abs(ref["profile_over_Tw"][hs]) < 1e-14
    # continuum coth anchor: discrete identity within the documented band
    ca = ref["coth_continuum_anchor"]
    assert abs(abs(ca) - 1.0) < 0.05 and abs(math.degrees(math.atan2(ca.imag, ca.real))) < 5.0
    # sink transfer is a small evanescent fraction at H_s = 4.7 delta
    assert abs(ref["sink_transfer"]) < 0.10
    # non-degeneracy: an alpha_eff-shaped table must move the reference
    kt2 = np.array([0.049, 0.098, 0.131, 0.196, 0.26, 1.05])
    at2 = ALPHA_LU * np.array([1.0, 1.0, 1.518, 0.977, 1.58, 12.5])
    ref2 = tent_spectral_reference(n, hs, om, ALPHA_LU, kt2, at2,
                                   highk_policy="hold_last", gamma=1.4)
    assert abs(ref2["Y_over_Yhs"] / ref["Y_over_Yhs"] - 1.0) > 0.01
    # QS direction: a hotter uniform alpha (T^1.04 law at Theta_DC=0.05)
    # must move Y by a measurable, sign-definite amount
    bvp_hot = tent_bvp_reference(np.full(n, ALPHA_LU * 1.05 ** 1.04), hs, om,
                                 ALPHA_LU, gamma=1.4)
    shift = bvp_hot["Y_over_Yhs"] / bvp["Y_over_Yhs"]
    assert abs(shift - 1.0) > 5e-3


def test_energy_bookkeeping_exactness():
    # the audited band records EXACTLY the energy the callback writes into the
    # row: calibrate against a hand-built modification of known energy delta
    s = _mini_solver()
    _generic_state(s)
    lattice = s.lattice
    c2 = np.sum(np.asarray(lattice.c, dtype=float) ** 2, axis=-1)
    rec: dict[str, list[float]] = {}

    def fake_band(*, solver, f_post, g_post, f_stream, g_stream):
        g_stream[5, :, :] += 1.25e-6      # known internal-energy injection
        return f_stream, g_stream

    cb = make_energy_audited_band(fake_band, rec, lattice, "hot")
    f, g = s.f.copy(), s.g.copy()
    cb(solver=s, f_post=None, g_post=None, f_stream=f, g_stream=g)
    known = 1.25e-6 * s.nx * int(lattice.q)
    assert rec["hot_dE"][0] == pytest.approx(known, rel=1e-12)
    assert rec["hot_dM"][0] == pytest.approx(0.0, abs=1e-18)


def test_conduction_seed_shape():
    prof = conduction_seed(32, 0.72, 0.70)
    assert prof[0] == pytest.approx(0.72) and prof[16] == pytest.approx(0.70)
    assert prof[8] == pytest.approx(0.71) and prof[24] == pytest.approx(0.71)
    assert np.max(np.abs(prof[1:16] - prof[31:16:-1])) < 1e-15  # tent symmetry


def test_coupled_loop_accounting_map_fixture():
    # discrete-map fixture of the A.4 mechanism (2026-08-01): feeding the raw
    # band bookkeeping (which contains the cv repinning energy) to the film
    # ODE creates x(t+1) = x(t) - g*(x(t) - x(t-1)) with g = cv*rho_row/(nx*C_A);
    # g > 1 diverges oscillating (authoritative v1: g = 1.244, dead @180 steps;
    # smoke: g = 0.965, stable) while the cv-subtracted feed removes the term
    # entirely (loop = physical film pole, stable).
    def run_map(g, n=400, x0=1e-12):
        x_prev, x = 0.0, x0
        for _ in range(n):
            x, x_prev = x - g * (x - x_prev), x
            if abs(x) > 1.0:
                return "diverged"
        return abs(x)
    assert run_map(1.244) == "diverged"          # production raw gain
    assert run_map(0.965) != "diverged"          # smoke raw gain (marginal)
    assert run_map(0.0) == pytest.approx(1e-12)  # cv-subtracted: term gone
    # gain arithmetic pinned: cv = (D+S)/2 = 2.5, production rig numbers
    cv = 2.5
    rho_row, nx, c_a = 7.62, 8, 1.9137           # sum(rho_row) ~ 8*0.952
    g_prod = cv * rho_row / (nx * c_a)
    assert g_prod == pytest.approx(1.244, abs=0.02)
    # the cp-vs-cv over-subtraction produces exactly -(cp-cv)*rho/nx spurious
    # conductance (measured -0.9527 in the diagnosis)
    assert (3.5 - 2.5) * rho_row / nx == pytest.approx(0.9525, abs=0.01)


def test_case_assembly_pre_registration():
    cfg = load_config(G4A_CFG)
    for proto_key in ("g4a", "g4a_smoke"):
        proto = cfg[proto_key]
        cases = assemble_cases(proto, {"numerics": {}})
        labels = [c["label"] for c in cases]
        # every rung has a base case and every (rung, eps) an increment case
        for r in proto["hs_rungs"]:
            assert f"base_{r['name']}" in labels
            for eps in proto["eps_ac"]:
                assert f"inc_{r['name']}_eps{float(eps):g}" in labels
        assert "base_uniform_init" in labels
        assert any(lb.startswith("inc_cold_") for lb in labels)
        # state matching BY CONSTRUCTION: identical theta_dc on every rung case
        dcs = {c["theta_dc"] for c in cases if not c["label"].startswith("inc_cold")}
        assert dcs == {float(proto["theta_dc"])}
        cold = [c for c in cases if c["label"].startswith("inc_cold")][0]
        assert cold["theta_dc"] == 0.0
        # rig height is twice H_s (tent) on every case
        by_rung = {str(r["name"]): int(r["hs_rows"]) for r in proto["hs_rungs"]}
        for c in cases:
            for name, hsr in by_rung.items():
                if f"_{name}_" in c["label"] or c["label"].endswith(name):
                    assert c["ny"] == 2 * hsr
    # contract §9.1 numbers frozen in the authoritative protocol
    g4a = cfg["g4a"]
    assert [float(e) for e in g4a["eps_ac"]] == [0.005, 0.02]
    assert float(g4a["theta_dc"]) == 0.05
    rungs = sorted(int(r["hs_rows"]) for r in g4a["hs_rungs"])
    assert rungs == [48, 72, 96]  # H_s, 1.5H_s, 2H_s
    assert float(cfg["gates"]["state_match_rel"]) == 1.0e-2
    assert float(cfg["gates"]["domain_amp_rel"]) == 2.0e-2
    assert float(cfg["gates"]["stationarity_per_period"]) == 1.0e-3
    assert float(cfg["gates"]["dc_closure_rel"]) == 5.0e-3
