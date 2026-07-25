"""WP1-3 mass-neutral wall candidate + boundary flux audit tests (contract §6.1).

Instrument certification on a tiny domain (nx=6, ny=12) at a synthetic
frequency (32 steps/period), mirroring the Phase_3 machinery-test pattern:

- the audit tool is calibrated against a synthetic KNOWN mass injection,
- the frozen ``pressure_preserving`` wall's mass source is *quantified*
  (the G1-W risk basis: 1f ~ O(eps), 2f/1f ~ eps from the per-step time
  derivative of the O(eps^2/2) density term — the audit must SEE it),
- the mass-neutral candidate sits at the floating-point floor on every
  G1-W mass/velocity metric (gate rows are 1e-10/1e-8; measured ~1e-16),
- exact theta/u pinning, non-equilibrium flux retention (not a clamp),
- long-run stability, and detectability of the old-vs-new difference.

The tiny rig's *admittance* difference between the walls is dominated by
their different acoustic characters (pressure clamped vs dynamic wall
pressure) blown up at grid-scale frequency; the production-scale (10 kHz,
dx2p6, ny=48) admittance verdict is recorded in Phase5_STATUS §3 and the
formal ±5%/5° regression belongs to the G1-W gate (WP2). No gate status is
claimed here.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from boundary.wall_mass_audit import (
    NORMALIZATION_DEFINITION,
    WallAuditRecorder,
    harmonic_components,
    make_mass_audited_callback,
)
from boundary.wall_thermal_grad import make_bottom_grad_wall_callback
from boundary.open_cbc import compose_boundary_callbacks
from boundary.wall_thermal_mass_neutral import (
    apply_bottom_mass_neutral_wall_inplace,
    make_bottom_mass_neutral_wall_callback,
    make_symmetric_mass_neutral_wall_callback,
    make_top_mass_neutral_lid_callback,
)
from core.solver import GasSolver2D
from postproc.multiharmonic_fit import fit_multiharmonic, signed_pair_combination
from scripts.phase2_m2_verification import load_config

GAS_CONFIG = Path("configs/gas_air_10k_d2q37_physical_timestep.yaml")
STEPS_PER_PERIOD = 32


def _make_solver(nx: int = 6, ny: int = 12) -> GasSolver2D:
    gas = load_config(GAS_CONFIG)
    gas["numerics"] = {**gas.get("numerics", {}), "nx": nx, "ny": ny}
    solver = GasSolver2D(gas)
    solver.initialize_from_macro(
        float(solver.mapping.lattice.rho_ref_lu),
        np.zeros((solver.ny, solver.nx, 2)),
        float(solver.mapping.theta_ref_lu),
    )
    return solver


def _theta_schedule(theta0: float, eps: float):
    def _theta(solver: GasSolver2D) -> float:
        phase = 2.0 * math.pi * solver.t_lu / STEPS_PER_PERIOD
        return theta0 * (1.0 + eps * math.cos(phase))

    return _theta


def _run_audited(callback_factory, *, eps: float, periods: int):
    solver = _make_solver()
    theta0 = float(solver.mapping.theta_ref_lu)
    recorder = WallAuditRecorder()
    callback = make_mass_audited_callback(
        callback_factory(_theta_schedule(theta0, eps)), recorder
    )
    mass0 = float(np.sum(solver.f))
    solver.step(periods * STEPS_PER_PERIOD, boundary_callback=callback)
    solver_drift = abs(float(np.sum(solver.f)) - mass0) / mass0
    dt_s = float(solver.mapping.lattice.dt_s)
    f_hz = 1.0 / (STEPS_PER_PERIOD * dt_s)
    components = harmonic_components(
        recorder, "dm_rel", dt_s=dt_s, frequency_hz=f_hz, settle_periods=1.0
    )
    return solver, recorder, components, solver_drift, f_hz


def _grad_factory(theta_schedule):
    return make_bottom_grad_wall_callback(
        theta_schedule, rho_policy="pressure_preserving", extrap="row1"
    )


def _mass_neutral_factory(theta_schedule):
    return make_bottom_mass_neutral_wall_callback(theta_schedule, extrap="row1")


def test_audit_tool_calibrated_against_known_injection():
    amplitude = 1.0e-4

    def injector(*, solver, f_post, g_post, f_stream, g_stream):
        phase = 2.0 * math.pi * solver.t_lu / STEPS_PER_PERIOD
        f_stream[0] *= 1.0 + amplitude * math.cos(phase)
        return f_stream, g_stream

    solver = _make_solver()
    recorder = WallAuditRecorder()
    solver.step(
        5 * STEPS_PER_PERIOD,
        boundary_callback=make_mass_audited_callback(injector, recorder),
    )
    dt_s = float(solver.mapping.lattice.dt_s)
    f_hz = 1.0 / (STEPS_PER_PERIOD * dt_s)
    comp = harmonic_components(recorder, "dm_rel", dt_s=dt_s, frequency_hz=f_hz)
    # scaling row-0 (rho ~= rho_ref per column) by (1 + a cos) injects a*cos
    # per column per step -> the 1f component must recover `a` quantitatively
    assert comp["components"][1] == pytest.approx(amplitude, rel=1.0e-2)
    assert comp["normalization"] == NORMALIZATION_DEFINITION


def test_pressure_preserving_wall_mass_source_is_quantified():
    eps = 0.02
    _, recorder, comp, solver_drift, _ = _run_audited(
        _grad_factory, eps=eps, periods=5
    )
    c = comp["components"]
    # the G1-W risk basis, measured (calibrated: 1f=6.7e-3, 2f=1.35e-4, 0f=4.3e-5)
    assert c[1] > 1.0e-3          # O(eps) 1f mass source, far above the 1e-10 gate
    assert c[2] > 3.0e-5          # O(eps^2) 2f term exists
    assert c[0] > 1.0e-5          # O(eps^2) DC term exists
    # per-step injection is the time derivative of the row density: the 2f/1f
    # ratio doubles the static eps/2 to ~eps (measured 0.0203 at eps=0.02)
    assert 0.5 * eps < c[2] / c[1] < 2.0 * eps
    # the wall is the domain's only mass non-conserver: wall-attributed and
    # solver-level drift must agree (audit completeness + downstream operators
    # conserve mass)
    cumulative = recorder.cumulative_mass_drift_rel()
    assert cumulative > 1.0e-4
    assert solver_drift == pytest.approx(cumulative, rel=5.0e-2)


def test_mass_neutral_wall_components_at_machine_floor():
    _, recorder, comp, solver_drift, f_hz = _run_audited(
        _mass_neutral_factory, eps=0.02, periods=5
    )
    # G1-W gate rows: components <=1e-10, |dM|/M0 window <=1e-8; measured ~1e-16
    assert comp["max_component"] <= 1.0e-14
    assert recorder.cumulative_mass_drift_rel() <= 1.0e-15
    assert solver_drift <= 1.0e-13
    # impermeability / no-slip at the callback instant (gate: <=1e-8 c0)
    dt_s = 1.0 / (STEPS_PER_PERIOD * f_hz)
    for series in ("u_normal_over_c0", "u_tangential_over_c0"):
        u_comp = harmonic_components(
            recorder, series, dt_s=dt_s, frequency_hz=f_hz, settle_periods=1.0
        )
        assert u_comp["max_component"] <= 1.0e-14


def test_mass_neutral_wall_pins_theta_and_u_exactly():
    solver = _make_solver()
    theta0 = float(solver.mapping.theta_ref_lu)
    solver.initialize_from_macro(
        float(solver.mapping.lattice.rho_ref_lu),
        np.zeros((solver.ny, solver.nx, 2)),
        theta0
        * (1.0 + 0.01 * np.cos(np.arange(solver.ny) / 3.0))[:, None]
        * np.ones((1, solver.nx)),
    )
    theta_w = theta0 * 1.005
    apply_bottom_mass_neutral_wall_inplace(solver, theta_w)
    macro = solver.get_macro()
    assert float(np.max(np.abs(solver.get_temperature_lu()[0] - theta_w))) < 1.0e-12 * theta0
    assert float(np.max(np.abs(macro.u[0]))) < 1.0e-13
    # wall-temperature realization in SI against the 0.01 K gate (machine level here)
    temp_scale = float(solver.mapping.temperature_scale)
    assert float(np.max(np.abs(solver.get_temperature_lu()[0] - theta_w))) * temp_scale < 1.0e-9


def test_mass_neutral_wall_retains_conductive_flux():
    # sustained wall overheat: the retained interior non-equilibrium must keep a
    # real conductive flux (the equilibrium clamp killed it, P3-5 history);
    # same order as the Grad wall (calibrated ratio 0.58 — the different wall
    # density states under sustained heating explain the O(1) factor; the
    # dynamic-admittance verdict is production-scale business, see STATUS)
    q = {}
    for name, factory in (("grad", _grad_factory), ("mn", _mass_neutral_factory)):
        solver = _make_solver()
        theta0 = float(solver.mapping.theta_ref_lu)
        callback = factory(lambda s, th=theta0: th * 1.02)
        solver.step(60, boundary_callback=callback)
        q[name] = float(np.mean(solver.get_heat_flux_lu()[1, :, 1]))
    assert q["grad"] != 0.0
    assert 0.3 <= q["mn"] / q["grad"] <= 1.2


def test_walls_differ_detectably_in_dynamic_response():
    # non-degeneracy of the G1-W old-vs-new difference audit: the two walls are
    # genuinely different boundary operators (pressure clamped vs dynamic wall
    # pressure), so the tiny-rig dynamic response must differ measurably. The
    # magnitude of the difference at this grid-scale synthetic frequency is a
    # rig artifact (acoustic character dominates) — do not read it as the
    # production admittance delta (see Phase5_STATUS §3 for the 10 kHz number).
    fits = {}
    for name, factory in (("grad", _grad_factory), ("mn", _mass_neutral_factory)):
        solver = _make_solver()
        theta0 = float(solver.mapping.theta_ref_lu)
        callback = factory(_theta_schedule(theta0, 0.002))
        dt_s = float(solver.mapping.lattice.dt_s)
        f_hz = 1.0 / (STEPS_PER_PERIOD * dt_s)
        t_list, q_list = [], []
        for _ in range(6 * STEPS_PER_PERIOD):
            solver.step(1, boundary_callback=callback)
            t_list.append(solver.t_lu * dt_s)
            q_list.append(float(np.mean(solver.get_heat_flux_lu()[1, :, 1])))
        t = np.asarray(t_list)
        x = np.asarray(q_list)
        mask = t >= 2.0 / f_hz
        fits[name] = fit_multiharmonic(
            t[mask], x[mask], 2.0 * math.pi * f_hz, n_harmonics=3
        ).harmonic(1)
    ratio = fits["mn"] / fits["grad"]
    assert np.isfinite(ratio.real) and np.isfinite(ratio.imag)
    assert abs(ratio) > 0.0
    assert abs(ratio - 1.0) > 0.05  # difference resolvable by the audit chain


def test_long_run_stability_and_neutrality():
    solver, recorder, comp, solver_drift, _ = _run_audited(
        _mass_neutral_factory, eps=0.05, periods=20
    )
    assert bool(np.all(np.isfinite(solver.f)) and np.all(np.isfinite(solver.g)))
    assert comp["max_component"] <= 1.0e-14
    assert solver_drift <= 1.0e-13
    assert recorder.cumulative_mass_drift_rel() <= 1.0e-14


def test_top_lid_pins_theta_and_composes_mass_neutrally():
    # canonical A2a heat-sink lid (contract §3.3) in mass-neutral form
    solver = _make_solver()
    theta0 = float(solver.mapping.theta_ref_lu)
    solver.initialize_from_macro(
        float(solver.mapping.lattice.rho_ref_lu),
        np.zeros((solver.ny, solver.nx, 2)),
        theta0
        * (1.0 + 0.01 * np.cos(np.arange(solver.ny) / 3.0))[:, None]
        * np.ones((1, solver.nx)),
    )
    mass0 = float(np.sum(solver.f))
    lid = make_top_mass_neutral_lid_callback(theta0, extrap="row1")
    lid(solver=solver, f_post=solver.f, g_post=solver.g, f_stream=solver.f, g_stream=solver.g)
    macro = solver.get_macro()
    # exact pin at the callback instant on the TOP row; mass untouched
    assert float(np.max(np.abs(solver.get_temperature_lu()[-1] - theta0))) < 1.0e-12 * theta0
    assert float(np.max(np.abs(macro.u[-1]))) < 1.0e-13
    assert abs(float(np.sum(solver.f)) - mass0) / mass0 <= 1.0e-15

    # composed bottom wall + lid: still globally mass-neutral and stable
    solver2 = _make_solver()
    composed = compose_boundary_callbacks(
        make_bottom_mass_neutral_wall_callback(_theta_schedule(theta0, 0.01), extrap="row1"),
        make_top_mass_neutral_lid_callback(theta0, extrap="row1"),
    )
    mass0 = float(np.sum(solver2.f))
    solver2.step(2 * STEPS_PER_PERIOD, boundary_callback=composed)
    assert bool(np.all(np.isfinite(solver2.f)) and np.all(np.isfinite(solver2.g)))
    assert abs(float(np.sum(solver2.f)) - mass0) / mass0 <= 1.0e-13
    # bottom wall drives, lid holds: the field carries real wall-normal structure
    theta_field = solver2.get_temperature_lu()
    row_means = np.mean(theta_field, axis=1)
    assert float(np.max(row_means) - np.min(row_means)) > 1.0e-3 * theta0
    with pytest.raises(ValueError):
        make_top_mass_neutral_lid_callback(theta0, extrap="cubic")


def test_symmetric_wall_exactness_neutrality_and_two_sidedness():
    # v1.1: per-direction two-sided neq blend with exact equilibrium-increment
    # mass/momentum removal — pinning and neutrality must stay machine-exact
    solver = _make_solver()
    theta0 = float(solver.mapping.theta_ref_lu)
    solver.initialize_from_macro(
        float(solver.mapping.lattice.rho_ref_lu),
        np.zeros((solver.ny, solver.nx, 2)),
        theta0
        * (1.0 + 0.01 * np.cos(np.arange(solver.ny) / 2.0))[:, None]
        * np.ones((1, solver.nx)),
    )
    theta_w = theta0 * 1.005
    mass0 = float(np.sum(solver.f))
    cb = make_symmetric_mass_neutral_wall_callback(theta_w, extrap="row1")
    cb(solver=solver, f_post=solver.f, g_post=solver.g, f_stream=solver.f, g_stream=solver.g)
    macro = solver.get_macro()
    assert float(np.max(np.abs(solver.get_temperature_lu()[0] - theta_w))) < 1.0e-12 * theta0
    assert float(np.max(np.abs(macro.u[0]))) < 1.0e-12
    assert abs(float(np.sum(solver.f)) - mass0) / mass0 <= 1.0e-14

    # dynamic: audited run stays mass-neutral at the floor and finite
    _, recorder, comp, solver_drift, _ = _run_audited(
        lambda th: make_symmetric_mass_neutral_wall_callback(th, extrap="row1"),
        eps=0.02, periods=5,
    )
    assert comp["max_component"] <= 1.0e-13
    assert solver_drift <= 1.0e-12

    # non-degeneracy: the symmetric wall genuinely differs from v1 on the
    # wrap side — compare the top-adjacent row response between the variants
    responses = {}
    for name, factory in (
        ("v1", _mass_neutral_factory),
        ("v11", lambda th: make_symmetric_mass_neutral_wall_callback(th, extrap="row1")),
    ):
        s = _make_solver()
        t0 = float(s.mapping.theta_ref_lu)
        s.step(3 * STEPS_PER_PERIOD, boundary_callback=factory(_theta_schedule(t0, 0.01)))
        theta_field = s.get_temperature_lu()
        responses[name] = float(np.mean(np.abs(theta_field[-1] - t0)))  # wrap-side row
    assert responses["v11"] != pytest.approx(responses["v1"], rel=1.0e-3)

    with pytest.raises(ValueError):
        make_symmetric_mass_neutral_wall_callback(1.0, extrap="cubic")


def _pair_run(sign: float, eps: float, *, spp: int, ramp_periods: float, periods: int):
    solver = _make_solver()
    theta0 = float(solver.mapping.theta_ref_lu)

    def theta(s):
        tt = s.t_lu / spp
        ramp = 1.0 if tt >= ramp_periods else 0.5 * (1.0 - math.cos(math.pi * tt / ramp_periods))
        return theta0 * (1.0 + sign * eps * ramp * math.cos(2.0 * math.pi * s.t_lu / spp))

    callback = make_symmetric_mass_neutral_wall_callback(theta)
    t_list, q_list = [], []
    for k in range(periods * spp):
        solver.step(1, boundary_callback=callback)
        if k % 2 == 0:
            t_list.append(float(solver.t_lu))
            q_list.append(float(np.mean(solver.get_heat_flux_lu()[1, :, 1])))
    return np.asarray(t_list), np.asarray(q_list)


def test_signed_pair_boundary_fixture_floor_and_rig_discipline():
    """WP1-4: the practical "boundary + linearized interior" fixture (contract
    §6.1) on the LBM stack via signed-pair cancellation.

    On a QUIET rig (drive far below the box acoustic mode, slow ramp, long
    settle) the odd-combination even-harmonic content decays to the ring
    residue (measured 4.5e-8 here and still settle-decaying; at production
    frequency the box-mode separation is ~1500x so the G1-W gate floor 1e-8
    is reachable — asserted there, not on this toy rig). Counter-demonstration:
    the near-resonant rig (32 steps/period vs box mode ~34 steps) shows an
    amplitude-independent ~2e-3 ring floor — fixing the fixture's
    pre-registration discipline: off-resonance drive + settle >> ring decay.
    """

    eps = 1.0e-4
    # quiet rig: 128 steps/period, ramp 4, settle 14 of 18 periods
    t, q_plus = _pair_run(+1.0, eps, spp=128, ramp_periods=4.0, periods=18)
    _, q_minus = _pair_run(-1.0, eps, spp=128, ramp_periods=4.0, periods=18)
    mask = t >= 14 * 128
    quiet = signed_pair_combination(
        t[mask], q_plus[mask], q_minus[mask], 2.0 * math.pi / 128.0
    )
    assert quiet["max_even_leakage_odd_combination"] <= 2.0e-7
    assert quiet["third_harmonic_odd_combination"] <= 1.0e-7
    # sensitivity: genuine physical 2f is seen far above the floor
    assert quiet["physical_2f_rel_even_combination"] >= 1.0e-6

    # near-resonant rig counterexample: ring floor is orders of magnitude worse
    t_r, qp_r = _pair_run(+1.0, eps, spp=STEPS_PER_PERIOD, ramp_periods=1.5, periods=6)
    _, qm_r = _pair_run(-1.0, eps, spp=STEPS_PER_PERIOD, ramp_periods=1.5, periods=6)
    mask_r = t_r >= 2 * STEPS_PER_PERIOD
    resonant = signed_pair_combination(
        t_r[mask_r], qp_r[mask_r], qm_r[mask_r], 2.0 * math.pi / STEPS_PER_PERIOD
    )
    assert (
        resonant["max_even_leakage_odd_combination"]
        > 100.0 * quiet["max_even_leakage_odd_combination"]
    )


def test_validation_errors():
    with pytest.raises(ValueError):
        make_bottom_mass_neutral_wall_callback(1.0, extrap="cubic")
    with pytest.raises(ValueError):
        make_bottom_mass_neutral_wall_callback(1.0, row=1)
    solver = _make_solver()
    with pytest.raises(ValueError):
        apply_bottom_mass_neutral_wall_inplace(solver, -1.0)
