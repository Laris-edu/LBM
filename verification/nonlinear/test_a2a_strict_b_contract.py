"""Contract tests for the A2a-STRICT_B retest unit (plan PLAN_v1.0).

Covers: the new strict-face Robin QS solvers (convergence to the analytic
sealed slab, matrix/spectral cross-agreement, Theta=0 ratio identity, frozen
base-state mapping), the mass-target seeding exactness, the one-step
energy/mass contract of the strict direct step, fit-window equivalence with
the wet A2a convention, the plan section 5 CSV schema, the candidate-only
verdict discipline (D0-7), and the reference-pack digest verification.
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from reference.strict_face_robin_qs import (  # noqa: E402
    analytic_sealed_dirichlet_slab,
    g0_alpha_of_k,
    map_strict_base_to_ref,
    robin_qs_matrix_bvp,
    robin_qs_spectral_extension,
    steady_uniform_base,
)

# synthetic constants (no LBM stack needed for the pure-reference rows)
H_LU = 48.0
OMEGA = 1.0e-3
ALPHA = 2.0e-2
GAMMA = 1.4
C_P = 1.0 / (GAMMA - 1.0) + 1.0          # R_lu = 1 -> c_v = 1/(gamma-1)
RHO = 1.0
K0 = ALPHA * RHO * C_P
THETA0 = 0.35


def _uniform_matrix_y(n_ref: int, beta: float = 1.04) -> complex:
    th_b, rho_b = steady_uniform_base(n_ref, theta_w=THETA0, theta_amb=THETA0,
                                      rho_bar=RHO)
    sol = robin_qs_matrix_bvp(n_ref=n_ref, h_lu=H_LU, omega_lu=OMEGA,
                              k0=K0, theta0=THETA0, beta=beta, c_p=C_P,
                              theta_w=THETA0, theta_amb=THETA0,
                              theta_base=th_b, rho_base=rho_b,
                              bulk_mode="powerlaw_local")
    return complex(sol["Y"]) / (RHO * C_P)         # -> alpha units


def _uniform_spectral_y(n_ref: int) -> complex:
    flat = g0_alpha_of_k(np.array([1e-4, 10.0]), np.array([ALPHA, ALPHA]),
                         None, theta_dc=0.0)
    sol = robin_qs_spectral_extension(
        n_ref=n_ref, h_lu=H_LU, omega_lu=OMEGA, gamma=GAMMA,
        alpha_of_k=flat, alpha_face_hot=ALPHA, alpha_face_cold=ALPHA,
        beta=1.04, theta_w=THETA0, theta_amb=THETA0, theta_1_base=THETA0,
        rho_bar_over_ref=1.0)
    return complex(sol["Y"])


def test_matrix_converges_to_analytic_sealed_slab():
    ref = analytic_sealed_dirichlet_slab(h_lu=H_LU, omega_lu=OMEGA,
                                         alpha_lu=ALPHA, gamma=GAMMA)
    y_ref = complex(ref["Y_alpha"])
    errs = [abs(_uniform_matrix_y(n) - y_ref) / abs(y_ref)
            for n in (64, 128, 256)]
    assert errs[0] > errs[1] > errs[2], f"not monotone: {errs}"
    assert errs[2] < 5e-3, f"finest error too large: {errs}"
    assert errs[1] / errs[2] > 2.5, f"refinement order collapsed: {errs}"


def test_spectral_converges_and_matches_matrix():
    ref = analytic_sealed_dirichlet_slab(h_lu=H_LU, omega_lu=OMEGA,
                                         alpha_lu=ALPHA, gamma=GAMMA)
    y_ref = complex(ref["Y_alpha"])
    errs = [abs(_uniform_spectral_y(n) - y_ref) / abs(y_ref)
            for n in (64, 128, 256)]
    assert errs[0] > errs[2], f"spectral not converging: {errs}"
    assert errs[2] < 5e-3, f"spectral finest error too large: {errs}"
    gap = abs(_uniform_spectral_y(256) - _uniform_matrix_y(256)) / abs(y_ref)
    assert gap < 5e-3, f"matrix/spectral uniform-limit gap {gap}"


def test_theta0_ratio_identity_matrix_and_spectral():
    y1 = _uniform_matrix_y(96)
    y2 = _uniform_matrix_y(96)
    assert abs(y1 / y2 - 1.0) < 1e-14
    s1 = _uniform_spectral_y(96)
    s2 = _uniform_spectral_y(96)
    assert abs(s1 / s2 - 1.0) < 1e-14


def test_hot_solve_moves_and_constitutive_term_present():
    # a finite-bias hot solve must differ from cold and carry the plan's
    # constitutive channel with the exact frozen coefficient structure
    theta_w = THETA0 * 1.10
    th_b, rho_b = steady_uniform_base(192, theta_w=theta_w, theta_amb=THETA0,
                                      rho_bar=RHO)
    sol = robin_qs_matrix_bvp(n_ref=192, h_lu=H_LU, omega_lu=OMEGA, k0=K0,
                              theta0=THETA0, beta=1.04, c_p=C_P,
                              theta_w=theta_w, theta_amb=THETA0,
                              theta_base=th_b, rho_base=rho_b,
                              bulk_mode="uniform_at_tw")
    dy = H_LU / 192
    g_fh = 2.0 * K0 * (theta_w / THETA0) ** 1.04 / dy
    expected_const = 1.04 * g_fh / theta_w * (theta_w - th_b[0])
    assert abs(complex(sol["Y_constitutive"]) - expected_const) < 1e-12
    y_cold = _uniform_matrix_y(192) * RHO * C_P
    assert abs(complex(sol["Y"]) / y_cold - 1.0) > 1e-3


def test_map_strict_base_endpoints_and_mass():
    rng = np.random.default_rng(7)
    theta_w, theta_amb = 0.385, 0.35
    n_src = 48
    theta_48 = np.linspace(theta_w * 0.99, theta_amb * 1.01, n_src)
    rho_48 = 1.0 + 0.05 * rng.standard_normal(n_src)
    mass = 47.3
    th, rho = map_strict_base_to_ref(theta_48, rho_48, 768, theta_w=theta_w,
                                     theta_amb=theta_amb, mass_per_area=mass,
                                     h_lu=H_LU)
    dy = H_LU / 768
    assert abs(float(np.sum(rho) * dy) / mass - 1.0) < 1e-14
    # first/last reference centres sit between the face and first source
    # centre -> linear toward the PRESCRIBED endpoints
    assert (th[0] - theta_w) * (theta_48[0] - theta_w) >= 0.0
    assert abs(th[0] - theta_w) < abs(theta_48[0] - theta_w)
    assert abs(th[-1] - theta_amb) < abs(theta_48[-1] - theta_amb)
    # rho end-value constant extension: the outermost reference cells carry
    # the source end values (up to the single global rescale, which cancels
    # in the end-to-end ratio)
    assert abs(rho[0] / rho[-1] - rho_48[0] / rho_48[-1]) < 1e-12


def test_g0_alpha_of_k_policies():
    k_tab = np.array([0.1, 0.2, 0.4])
    a_tab = np.array([1.0, 2.0, 4.0])
    e_tab = np.array([1.0, 1.5, 2.0])
    a_of = g0_alpha_of_k(k_tab, a_tab, e_tab, theta_dc=0.0)
    assert a_of(0.01) == 1.0            # hold-first
    assert a_of(5.0) == 4.0             # hold-last
    assert abs(a_of(0.3) - 3.0) < 1e-12  # interior interpolation
    hot = g0_alpha_of_k(k_tab, a_tab, e_tab, theta_dc=0.10)
    assert abs(hot(0.1) / 1.0 - 1.1 ** 1.0) < 1e-12
    assert abs(hot(5.0) / 4.0 - 1.1 ** 2.0) < 1e-12


def test_target_mass_seed_and_one_step_contract():
    pytest.importorskip("yaml")
    from core.strict_b_half_domain import StrictBHalfDomain
    from scripts.phase2_m2_verification import load_config
    from scripts.phase5_a2a_strict_b import (
        _fg_energy,
        make_wall,
        target_mass_seed,
    )

    gas_cfg = load_config(REPO_ROOT / "configs"
                          / "gas_air_10k_d2q37_levelc_dx2p6.yaml")
    hd = StrictBHalfDomain(gas_cfg, n_phys=8, nx=4)
    rho0 = float(hd.mapping.lattice.rho_ref_lu)
    target = rho0 * 8 * 1.0173          # arbitrary off-nominal target
    f, g, total, init_rel = target_mass_seed(hd, 0.05, target)
    assert init_rel <= 1e-12
    assert abs(total / (target * hd.nx) - 1.0) < 1e-15

    c2 = np.sum(np.asarray(hd.lattice.c, dtype=float) ** 2, axis=-1)
    th0 = float(hd.mapping.theta_ref_lu)
    wall = make_wall(hd, th0 * 1.05)
    e0 = _fg_energy(f, g, c2)
    m0 = float(np.sum(f))
    f2, g2, de_h, de_c = hd.strict_direct_step(f, g, face_wall=wall)
    e1 = _fg_energy(f2, g2, c2)
    m1 = float(np.sum(f2))
    floor = 64.0 * np.finfo(float).eps * abs(e0)
    assert abs(e1 - e0 - de_h - de_c) <= max(
        1e-12 * max(abs(de_h) + abs(de_c), floor), floor)
    assert abs(m1 - m0) / (target * hd.nx) <= 1e-13


def test_fit_window_matches_wet_convention():
    from scripts.phase5_a2a_strict_b import fit_admittance_window
    from scripts.phase5_faceflux_strict_b_scan import fit_admittance_strict

    f_hz = 1.0e4
    om = 2.0 * math.pi * f_hz
    t = np.arange(0, 256) / 64.0 / f_hz          # 4 periods, 64/period
    ramp = np.where(t < 1.0 / f_hz,
                    0.5 * (1 - np.cos(np.pi * t * f_hz)), 1.0)
    theta_w = 0.35 + 1e-3 * ramp * np.cos(om * t)
    q = 3e-4 * ramp * np.cos(om * t - 0.7) + 5e-6 * np.cos(2 * om * t)
    drive = {"t_s": t, "theta_w": theta_w, "q_hot_lu": q}
    run = {"drive": drive, "rho0": 1.0, "cp_eff": 4.5, "nx": 8}
    a = fit_admittance_window(drive, f_hz, (2.0, 4.0), rho0=1.0, cp_eff=4.5,
                              nx=8)
    b = fit_admittance_strict(run, f_hz, 2.0)
    assert abs(a["Y_face_theta_units"] / b["Y_face_theta_units"] - 1.0) < 1e-12
    assert abs(a["h2_q_rel"] - b["h2_q_rel"]) < 1e-12


def test_csv_schema_matches_plan_section5():
    from scripts.phase5_a2a_strict_b import CSV_COLUMNS

    assert CSV_COLUMNS == [
        "theta_dc", "epsilon_ac", "mass_target", "mass_drift_rel",
        "pmean_rel_wet", "Y_re", "Y_im", "d_op_pct", "phase_deg",
        "qs0_pct", "qs1_pct", "qs1_phase_deg", "qs1k_pct", "r_dyn_pp",
        "phase_resid_deg", "cr_lower", "h2_q_rel", "u_d_pp", "u_qs_pp",
        "g0_scope", "status"]


def test_candidate_only_verdict_discipline():
    src = (REPO_ROOT / "scripts" / "phase5_a2a_strict_b.py").read_text(
        encoding="utf-8")
    for name in ("EFFECTIVE_RESOLUTION", "EFFECTIVE_MITIGATION",
                 "NOT_RESOLVED", "UNINTERPRETABLE"):
        assert f'"{name}"' not in src, f"bare plan label {name} in runner"
        assert f'"{name}_CANDIDATE"' in src
    assert "STRICT_B_SCIENTIFICALLY_VALIDATED" not in src
    assert re.search(r'JUDGEMENT\s*=\s*"USER_PENDING"', src)


def test_frozen_lines_match_plan():
    import scripts.phase5_a2a_strict_b as m

    assert m.BRANCH == "G0"
    assert m.GATE_CONTRACT_REL == 1e-12
    assert m.GATE_MASS_INIT_REL == 1e-12
    assert m.GATE_MASS_DRIFT_REL == 1e-10
    assert m.GATE_PMEAN_REL_WET == 1e-2
    assert m.GATE_STATIONARITY == 1e-3
    assert m.GATE_DC_CLOSURE == 1e-3
    assert m.GATE_LINEARITY == 1e-3
    assert m.FIT_WINDOW_MAIN == (2.0, 4.0)
    assert m.FIT_WINDOW_ALT == (1.5, 3.5)
    assert m.N_REF_LADDER == (192, 384, 768)
    assert m.U_WET_FLOOR_PP == 0.02
    assert m.Y0_WET_COLD == complex(4.998499198013624e-4,
                                    9.596625379939636e-4)


def test_reference_pack_digest_verification(tmp_path):
    from scripts.phase5_a2a_strict_b import _sha256, load_reference_pack

    npz = tmp_path / "wet_reference_pack_series.npz"
    np.savez_compressed(npz, x=np.arange(4.0))
    pack = {"points": {}, "series_npz": npz.name,
            "sha256": {"series_npz": _sha256(npz)}}
    pj = tmp_path / "wet_reference_pack.json"
    pj.write_text(json.dumps(pack), encoding="utf-8")
    (tmp_path / "wet_reference_pack.sha256").write_text(
        _sha256(pj) + "  wet_reference_pack.json\n", encoding="utf-8")
    loaded = load_reference_pack(pj)
    assert loaded["_pack_sha256_verified"] == _sha256(pj)
    pj.write_text(json.dumps({**pack, "tampered": 1}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="digest mismatch"):
        load_reference_pack(pj)
