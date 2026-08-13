"""NSF hot-base tangent arbitration instrument tests (plan v1.0 §10, D0-7).

Contract tests for ``reference/nsf_hot_base_linear_1d.py`` — the
frequency-domain linearized hot-base NSF BVP used by the arbitration runner
``scripts/phase5_nsf_hot_base_arbitration.py``:

- base state: constant-k closed forms (T_bar exactly linear; mass-constrained
  p_bar/p0 = Theta/ln(1+Theta) to 1e-10; mass integral audit) and power-law
  closed form T_bar = [T_w^m + (T0^m - T_w^m) y/H]^{1/m} (plan §10.4),
- Theta_DC=0 degeneracy: model="full" and model="nograd" assemble the SAME
  operator (exactly equal Y — plan §10.6) and the cold response matches the
  closed-box pressure-work-corrected Phase_1 half-space anchor (plan §10.1;
  the same identity certified for the G3 instrument in WP1-2),
- input-amplitude linearity: T_w_hat -> T_w_hat/2 leaves Y bitwise (plan
  §10.5, implemented as an exact homogeneity check of the solve),
- boundary conditions satisfied at machine level (plan §10.3),
- perturbation mass neutrality (closed column, automatic int rho_hat = 0),
- second-order grid convergence of Y on a cells-per-delta ladder (plan
  §10.2) and stability of the d_OP readout under Richardson refinement,
- model="nograd" surgery: operator difference lives ONLY in the frozen boxed
  coefficients (continuity/energy rows, u_hat column) and produces a
  distinct hot response (non-degeneracy),
- fail-loud validation (unknown model, too-small grid).

Pure instrument mechanics — no arbitration verdicts, no gate claims.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from reference.constants import default_params, omega_from_frequency
from reference.nonlinear_nsf_1d import (
    g0_measured_transport,
    lbm_equivalent_transport,
    physical_air_transport,
)
from reference.nsf_hot_base_linear_1d import (
    solve_base_state,
    solve_linear_response,
    transport_dk_dT,
)
from reference.thermal_admittance import thermal_admittance_halfspace

F0_HZ = 1.0e4
PARAMS = default_params()
HEIGHT_OVER_DELTA = 4.61  # G4a canonical tent H_s (DC-arm frozen value)


def _delta_t() -> float:
    alpha0 = PARAMS.kg / (PARAMS.rho0 * PARAMS.cp)
    return math.sqrt(2.0 * alpha0 / omega_from_frequency(F0_HZ))


def _height() -> float:
    return HEIGHT_OVER_DELTA * _delta_t()


def _n_nodes(cells_per_delta: float) -> int:
    return int(round(HEIGHT_OVER_DELTA * cells_per_delta)) + 1


def _solve(transport, theta, model="full", cpd=48.0, T_w_hat=1.0 + 0.0j):
    base = solve_base_state(
        PARAMS, transport, theta_dc=theta, height_m=_height(),
        n_nodes=_n_nodes(cpd),
    )
    return solve_linear_response(
        base, PARAMS, transport, frequency_hz=F0_HZ, model=model,
        T_w_hat=T_w_hat,
    )


def test_base_state_constant_k_closed_forms():
    tr = lbm_equivalent_transport(PARAMS)
    for theta in (0.05, 0.10):
        base = solve_base_state(
            PARAMS, tr, theta_dc=theta, height_m=_height(), n_nodes=200
        )
        # T_bar exactly linear between T_w and T0
        T_lin = base.T_wall + (PARAMS.T0 - base.T_wall) * base.y / base.height_m
        assert np.max(np.abs(base.T_bar - T_lin)) / PARAMS.T0 < 1e-12
        # mass-constrained p_bar closed form Theta/ln(1+Theta) (plan §3/§10.4)
        assert base.p_bar_closed_form_rel_dev < 1e-10
        assert base.mass_int_rel_dev < 1e-10
        assert base.p_bar > PARAMS.p0  # closed heated column pressurizes
        # exact p_bar=const identity: drho/dy = -rho T'/T
        lhs = base.drho_bar_dy
        rhs = -base.rho_bar * base.dT_bar_dy / base.T_bar
        assert np.max(np.abs(lhs - rhs)) <= 1e-12 * np.max(np.abs(rhs))


def test_base_state_power_law_closed_form():
    tr = g0_measured_transport(PARAMS)  # k ∝ T^{+1.04} (frozen G0 law)
    theta = 0.10
    base = solve_base_state(
        PARAMS, tr, theta_dc=theta, height_m=_height(), n_nodes=150
    )
    m = tr.k_exponent + 1.0
    T_ref = (
        base.T_wall ** m
        + (PARAMS.T0 ** m - base.T_wall ** m) * base.y / base.height_m
    ) ** (1.0 / m)
    assert np.max(np.abs(base.T_bar - T_ref)) / PARAMS.T0 < 1e-10
    assert base.mass_int_rel_dev < 1e-10
    # conductive flux k(T_bar) dT_bar/dy uniform at machine level
    flux = np.asarray(tr.k(base.T_bar)) * base.dT_bar_dy
    assert np.max(np.abs(flux - base.flux_const)) < 1e-10 * abs(base.flux_const)


def test_dk_dT_analytic_matches_fd():
    for tr in (
        lbm_equivalent_transport(PARAMS),
        g0_measured_transport(PARAMS),
        physical_air_transport(PARAMS),
    ):
        T = np.linspace(295.0, 335.0, 7)
        h = 1e-3
        fd = (np.asarray(tr.k(T + h)) - np.asarray(tr.k(T - h))) / (2 * h)
        ana = transport_dk_dT(tr, T)
        assert np.max(np.abs(ana - fd)) <= 1e-6 * (np.max(np.abs(fd)) + 1e-12)


def test_cold_degeneracy_full_equals_nograd_and_anchor():
    for tr in (lbm_equivalent_transport(PARAMS), g0_measured_transport(PARAMS)):
        full = _solve(tr, 0.0, model="full")
        nograd = _solve(tr, 0.0, model="nograd")
        # plan §10.6: identical operators at Theta_DC=0 -> exactly equal Y
        assert full.Y_raw == nograd.Y_raw
        # plan §10.1: closed-box corrected identity against the Phase_1
        # half-space single source (WP1-2 certified the same identity for the
        # G3 instrument at the ~0.1% level; 1% line documented as loose)
        y_hs = thermal_admittance_halfspace(F0_HZ, PARAMS)
        assert abs(full.Y_corrected - y_hs) / abs(y_hs) < 1e-2
        # readout stencil sensitivity is sub-dominant at this grid
        assert (
            abs(full.q_wall_hat_stencil3 - full.q_wall_hat)
            / abs(full.q_wall_hat)
            < 2e-3
        )


def test_linearity_and_bc_and_audits():
    tr = lbm_equivalent_transport(PARAMS)
    r1 = _solve(tr, 0.05, T_w_hat=1.0 + 0.0j)
    r2 = _solve(tr, 0.05, T_w_hat=0.5 + 0.0j)
    # plan §10.5: halving T_w_hat leaves Y unchanged (exact homogeneity)
    assert abs(r1.Y_raw - r2.Y_raw) <= 1e-12 * abs(r1.Y_raw)
    assert abs(r2.q_wall_hat - 0.5 * r1.q_wall_hat) <= 1e-12 * abs(r1.q_wall_hat)
    # plan §10.3: Dirichlet rows at solver-backward-error level (field scale 1)
    assert r1.bc_residual_abs < 1e-10
    assert r1.solve_residual_rel < 1e-12
    # closed column: perturbation mass neutrality holds to O(dy^2) truncation
    # (measured 1.2e-4 @ cpd=48, clean 2nd-order decay on the ladder)
    assert r1.mass_neutrality_rel < 5e-4
    # physical energy-integral audit at truncation level
    assert r1.energy_integral_rel_dev < 5e-3


def test_grid_convergence_second_order():
    tr = lbm_equivalent_transport(PARAMS)

    def dop(cpd):
        y0 = _solve(tr, 0.0, cpd=cpd).Y_raw
        y1 = _solve(tr, 0.10, cpd=cpd).Y_raw
        return (abs(y1 / y0) - 1.0) * 100.0

    # observed order on the d_OP QoI ladder (measured ~2.4/2.25; |Y| itself
    # shows readout-stencil error cancellation above 2 and a solver roundoff
    # floor ~4e-7 rel at cpd=192, so the QoI ladder is the honest metric)
    d12, d24, d48, d96 = dop(12.0), dop(24.0), dop(48.0), dop(96.0)
    order = math.log2(abs(d12 - d24) / abs(d24 - d48))
    assert 1.5 < order < 3.2
    # d_OP stable under refinement at the production grid: 48 -> 96 shift
    # below the frozen 0.02 pp line (measured ~1.2e-4 pp)
    assert abs(d96 - d48) < 0.02


def test_nograd_surgery_is_local_and_nondegenerate():
    tr = lbm_equivalent_transport(PARAMS)
    full = _solve(tr, 0.10, model="full")
    nograd = _solve(tr, 0.10, model="nograd")
    # hot base: the boxed terms matter — responses must differ
    assert abs(full.Y_raw - nograd.Y_raw) / abs(full.Y_raw) > 1e-5
    # the surgery removes ONLY the two boxed couplings: reconstruct the
    # difference operator action on the full solution and check it equals
    # s * (rho_bar' u_hat  [continuity rows] + rho_bar cv T_bar' u_hat
    # [energy rows]) — i.e. re-solving nograd with those source terms added
    # back on the RHS reproduces the full solution
    base = full.base
    from reference.nsf_hot_base_linear_1d import _assemble  # test-only probe

    omega = omega_from_frequency(F0_HZ)
    A_f, b, _, cv, _ = _assemble(
        base, PARAMS, tr, omega=omega, model="full", T_w_hat=1.0 + 0.0j
    )
    A_n, _, _, _, _ = _assemble(
        base, PARAMS, tr, omega=omega, model="nograd", T_w_hat=1.0 + 0.0j
    )
    D = (A_f - A_n).tocoo()
    n = base.y.size
    for r, c in zip(D.row, D.col):
        assert c % 3 == 1  # only u_hat columns touched
        assert r % 3 in (0, 2)  # only continuity/energy rows
        assert r // 3 == c // 3  # diagonal (local) coupling only
    x_full = np.empty(3 * n, dtype=np.complex128)
    x_full[0::3], x_full[1::3], x_full[2::3] = (
        full.rho_hat, full.u_hat, full.T_hat,
    )
    resid = A_n @ x_full - (b - D @ x_full)
    scale = float(np.max(abs(A_f) @ np.abs(x_full) + np.abs(b))) + 1e-300
    assert float(np.max(np.abs(resid))) / scale < 1e-12


def test_fail_loud_inputs():
    tr = lbm_equivalent_transport(PARAMS)
    base = solve_base_state(
        PARAMS, tr, theta_dc=0.05, height_m=_height(), n_nodes=64
    )
    with pytest.raises(ValueError):
        solve_linear_response(
            base, PARAMS, tr, frequency_hz=F0_HZ, model="not_a_model"
        )
    with pytest.raises(ValueError):
        solve_base_state(
            PARAMS, tr, theta_dc=0.05, height_m=_height(), n_nodes=10
        )
    with pytest.raises(ValueError):
        solve_base_state(
            PARAMS, tr, theta_dc=-0.01, height_m=_height(), n_nodes=64
        )
