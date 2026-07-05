"""P4-1 open-top boundary tests (``boundary/open_cbc.py`` + reflection pipeline).

Non-degeneracy (Phase_3 lesson: level smokes must not pass by construction): the dynamic
absorb-vs-reflect test runs the SAME piston + probe + decomposition pipeline twice at a
diagnostic high frequency whose wavelength fits the test domain -- once against the CBC
open top, once against a deliberately reflecting rigid lid (u=0 Grad wall, R ~ +1). The
pipeline must both DETECT strong reflection and show the CBC absorbing it. (A reference-
equilibrium clamp is NOT a valid reflecting counterexample: it is the textbook crude
equilibrium open boundary and itself measures |R| ~ 0.2.) These tests use the D2Q37
production-baseline config at a diagnostic frequency; the 10 kHz P4-1 gate itself is only
ever claimed by ``scripts/phase4_open_boundary_reflection.py`` runs.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import yaml

from boundary.open_cbc import (
    compose_boundary_callbacks,
    make_top_open_boundary_callback,
    top_open_stencil,
)
from boundary.wall_thermal_grad import make_bottom_grad_wall_callback
from core.macroscopic import recover_macro
from core.solver import GasSolver2D
from core.unit_mapping import d2q37_physical_timestep_config
from phase3_interfaces.complex_amplitude import complex_amplitude
from scripts.phase4_open_boundary_reflection import (
    characteristic_split_reflection,
    decompose_incident_reflected,
    expected_thermoacoustic_pressure_pa,
    make_thermal_drive_wall_callback,
)

AIR_ALPHA0_M2_S = 2.2233775895e-5  # frozen air thermal diffusivity (configs/gas_air_*)


def _solver(nx: int, ny: int) -> GasSolver2D:
    cfg = d2q37_physical_timestep_config()
    cfg["numerics"] = {**cfg.get("numerics", {}), "nx": nx, "ny": ny}
    solver = GasSolver2D(cfg)
    solver.initialize_from_macro(
        solver.mapping.lattice.rho_ref_lu,
        np.zeros((ny, nx, 2)),
        solver.mapping.theta_ref_lu,
    )
    return solver


def _make_rigid_lid_top_callback():
    """Deliberately REFLECTING counterexample: halfway bounce-back lid at the top plane
    ``y = ny - 1/2`` (every from-above link takes the mirrored opposite-direction
    population; f AND g -> adiabatic no-slip lid, R ~ +1). Purely local and passive --
    it cannot join the periodic-seam feedback loops that refuted the reconstruction-based
    reflectors (a Grad u=0 lid paired with the bottom thermal wall destabilizes the
    column exactly like the refuted piston fixtures). Test-only; never a production BC.

    Note: a reference-equilibrium CLAMP is the wrong counterexample -- resetting the top
    rows to the reference state feeds the interior zero-perturbation down-going
    populations, i.e. it IS the textbook crude equilibrium open boundary (measured
    |R| ~ 0.2 here), not a strong reflector."""

    def _callback(*, solver, f_post, g_post, f_stream, g_stream):
        lattice = solver.lattice
        ny = int(solver.ny)
        st = top_open_stencil(lattice)
        opposite = np.asarray(lattice.opposite, dtype=int)
        for a in st.incoming:
            depth_max = -int(st.cy[a])                     # |cy_a|
            for depth in range(0, depth_max):              # rows ny-1 .. ny-|cy|
                row = ny - 1 - depth
                mirror = 2 * ny - 1 - row - depth_max      # halfway mirror across y=ny-1/2
                f_stream[row, :, a] = f_post[mirror, :, opposite[a]]
                g_stream[row, :, a] = g_post[mirror, :, opposite[a]]
        return f_stream, g_stream

    return _callback


def test_top_open_stencil_bookkeeping_d2q37():
    solver = _solver(4, 16)
    st = top_open_stencil(solver.lattice)
    assert st.max_down == 3
    assert st.affected_rows_below_top == (0, 1, 2)
    assert st.incoming.size == 15  # D2Q37: 15 downward, 15 upward, 7 grazing
    assert np.all(st.cy[st.incoming] < 0)
    # deep-link fill only ever touches rows ny-2 (cy<=-2) and ny-3 (cy=-3)
    assert int(np.sum(st.cy[st.incoming] <= -2)) == 8


def test_decompose_recovers_synthetic_reflection():
    rng = np.random.default_rng(20260703)
    k = 181.07  # rad/m, 10 kHz air
    y = np.arange(64, 449, 8, dtype=float) * 2.61175e-6
    a_inc = 2.0 * np.exp(1j * 0.7)
    for r_true in (0.03 * np.exp(1j * 1.1), 1.0 + 0.0j):  # near-gate case and standing wave
        p_hat = a_inc * (np.exp(-1j * k * y) + r_true * np.exp(1j * k * y))
        p_hat = p_hat + 1e-4 * (rng.standard_normal(y.size) + 1j * rng.standard_normal(y.size))
        out = decompose_incident_reflected(y, p_hat, k)
        assert abs(out["R_abs"] - abs(r_true)) < 5e-3
        assert out["residual_rel"] < 1e-3
    # model-adequacy metric must reject a non-two-wave field
    junk = rng.standard_normal(y.size) + 1j * rng.standard_normal(y.size)
    assert decompose_incident_reflected(y, junk, k)["residual_rel"] > 0.2


def test_quiescent_open_top_with_thermal_grad_wall_stays_quiescent():
    """Plumbing smoke: on the exact reference equilibrium, wall + open-top callbacks and
    the solver corrections must all be identity to roundoff (no spurious source)."""

    solver = _solver(8, 64)
    theta0 = float(solver.mapping.theta_ref_lu)
    p_ref = float(solver.mapping.lattice.rho_ref_lu) * theta0
    callback = compose_boundary_callbacks(
        make_bottom_grad_wall_callback(theta0, rho_policy="pressure_preserving", extrap="linear"),
        make_top_open_boundary_callback(),
    )
    solver.step(200, boundary_callback=callback)
    assert np.isfinite(solver.f).all() and np.isfinite(solver.g).all()
    p = recover_macro(solver.f, solver.g, D=2, S=3, lattice=solver.lattice).p
    assert float(np.max(np.abs(p - p_ref))) / p_ref < 1e-11


def test_thermal_bump_near_top_leaves_stably():
    """Contract §6.2 item 2: thermal/entropy content near the open boundary must stay
    stable and its acoustic part must actually leave (pressure transient decays)."""

    solver = _solver(8, 96)
    ny, nx = solver.ny, solver.nx
    theta0 = float(solver.mapping.theta_ref_lu)
    rows = np.arange(ny, dtype=float)[:, None]
    theta = theta0 * (1.0 + 1e-3 * np.exp(-((rows - 80.0) ** 2) / (2.0 * 4.0**2)) * np.ones((ny, nx)))
    solver.initialize_from_macro(solver.mapping.lattice.rho_ref_lu, np.zeros((ny, nx, 2)), theta)
    p_ref = float(solver.mapping.lattice.rho_ref_lu) * theta0
    p0_max = float(np.max(np.abs(recover_macro(solver.f, solver.g, D=2, S=3, lattice=solver.lattice).p - p_ref)))
    callback = compose_boundary_callbacks(
        make_bottom_grad_wall_callback(theta0, rho_policy="pressure_preserving", extrap="linear"),
        make_top_open_boundary_callback(),
    )
    solver.step(900, boundary_callback=callback)
    assert np.isfinite(solver.f).all() and np.isfinite(solver.g).all()
    macro = recover_macro(solver.f, solver.g, D=2, S=3, lattice=solver.lattice)
    # entropy residue may remain (zero mean flow: it only diffuses); no growth allowed
    assert float(np.max(np.abs(macro.theta - theta0))) < 1.3e-3 * theta0
    # the acoustic part must have left through the open top (clamped top would trap it)
    p_end_max = float(np.max(np.abs(macro.p - p_ref)))
    assert p_end_max < 0.3 * p0_max


def _measure_reflection(top_callback, *, period_steps: int, ny: int, nx: int = 4) -> dict:
    """Shared diagnostic-frequency pipeline: thermal drive -> probes -> harmonic fit -> R.

    The source is the production thermal_grad wall with an oscillating theta_w (the same
    thermoacoustic drive as the committed script -- the only bottom BC that is
    seed-stable against the open top; four velocity-piston fixtures were refuted).

    Timing contract: the trailing one-period fit window must start only after the first
    top reflection has swept the WHOLE probe band (transit ny/c_lu plus the way back),
    otherwise the down-going wave is simply absent from the data and any boundary looks
    absorbing (the first version of this test failed exactly that way).

    Regime contract: the drive must stay SUB-RESONANT (well below the first column
    eigenfrequency c_lu/(4*ny), full-clamp wall + top boundary). Driving a
    resonant-scale column (kL ~ 2.6, drive ~ eigenfrequency) rings the column's own
    standing modes, which the impedance-matched top cannot damp fast enough -- growth at
    c/(2L), c/(4L) was measured in the 2026-07-04 mechanism probes and is documented as
    a scoped validity boundary in Phase4_STATUS.md. The P4-1 certification regime sits
    6.5x BELOW the first eigenfrequency (10 kHz, ny=512, dx2p6), safely sub-resonant."""

    solver = _solver(nx, ny)
    dt = float(solver.mapping.lattice.dt_s)
    theta0 = float(solver.mapping.theta_ref_lu)
    gamma = 1.0 + 2.0 / (2 + 3)
    c_lu = math.sqrt(gamma * theta0)
    f_hz = 1.0 / (period_steps * dt)
    quarter_wave_freq = c_lu / (4.0 * ny)
    assert 1.0 / period_steps < 0.5 * quarter_wave_freq, "diagnostic drive must stay sub-resonant"
    omega = 2.0 * math.pi * f_hz
    theta_hat_lu = 1.18e-3 * theta0            # mirrors 0.354 K / 300 K (Level A amplitude)
    ramp_steps = period_steps

    callback = compose_boundary_callbacks(
        make_thermal_drive_wall_callback(
            theta0_lu=theta0,
            theta_hat_lu=theta_hat_lu,
            omega_si=omega,
            dt_si=dt,
            ramp_steps=ramp_steps,
        ),
        top_callback,
    )
    rows = np.arange(16, ny - 32 + 1, 4)
    sample_every = 8
    n_steps = int(round(2.25 * period_steps))
    fit_start_step = n_steps - period_steps
    first_reflection_at_lowest_probe = (ny + (ny - rows[0])) / c_lu
    assert fit_start_step > 1.2 * first_reflection_at_lowest_probe, "fit window opens before reflection arrives"
    n_samples = n_steps // sample_every
    t_sample = np.empty(n_samples)
    p_rows = np.empty((n_samples, rows.size))
    v_rows = np.empty((n_samples, rows.size))
    for i in range(n_samples):
        solver.step(sample_every, boundary_callback=callback)
        t_sample[i] = solver.t_lu * dt
        m = recover_macro(solver.f[rows], solver.g[rows], D=2, S=3, lattice=solver.lattice)
        p_rows[i] = np.mean(m.p, axis=-1)
        v_rows[i] = np.mean(m.u[..., 1], axis=-1)
    assert np.isfinite(p_rows).all() and np.isfinite(solver.f).all()

    mask = t_sample >= fit_start_step * dt  # trailing one period
    p_hat = np.empty(rows.size, dtype=complex)
    v_hat = np.empty(rows.size, dtype=complex)
    for j in range(rows.size):
        series = p_rows[mask, j]
        p_hat[j] = complex_amplitude(t_sample[mask], series - float(np.mean(series)), f_hz)
        series_v = v_rows[mask, j]
        v_hat[j] = complex_amplitude(t_sample[mask], series_v - float(np.mean(series_v)), f_hz)
    k_cell = omega * dt / c_lu
    z0_lu = float(solver.mapping.lattice.rho_ref_lu) * c_lu
    out = characteristic_split_reflection(rows.astype(float), p_hat, v_hat, k_cell, z0_lu)
    out["ls_cross_check"] = decompose_incident_reflected(rows.astype(float), p_hat, k_cell)
    # half-space thermoacoustic emission anchor, converted to LU pressure amplitude
    dx = float(solver.mapping.lattice.dx_m)
    expected_pa = expected_thermoacoustic_pressure_pa(
        rho0_kg_m3=1.177, c0_m_s=347.0, omega_rad_s=omega,
        alpha_m2_s=AIR_ALPHA0_M2_S, T_hat_K=0.354, T0_K=300.0,
    )
    out["A_inc_expected_lu"] = expected_pa / float(solver.mapping.pressure_scale)
    out["delta_T_cells"] = math.sqrt(2.0 * AIR_ALPHA0_M2_S / omega) / dx
    return out


def test_open_cbc_absorbs_where_reflecting_clamp_reflects():
    """Dynamic non-degeneracy counter-test at a SUB-RESONANT diagnostic frequency
    (period 3600 steps = 0.41x the 96-row column's quarter-wave eigenfrequency; domain
    crossed in ~370 steps so the trailing-period fit window sees many round trips; probe
    span 48 cells is ~0.6 rad of two-wave phase, conditioning covered by the synthetic
    test). NOT the 10 kHz gate: it certifies the pipeline detects reflection (rigid lid,
    R ~ +1) and the impedance CBC absorbs in the same regime class as the gate."""

    period_steps = 3600
    absorbed = _measure_reflection(
        make_top_open_boundary_callback(w_lowpass_steps=0.01 * period_steps),
        period_steps=period_steps, ny=96,
    )
    reflected = _measure_reflection(_make_rigid_lid_top_callback(), period_steps=period_steps, ny=96)
    # Source amplitude recovered from the gas, not from inputs. Order-of-magnitude
    # window only: at the diagnostic frequency delta_T ~ 2.2 cells (under-resolved
    # boundary layer, measured emission ~11x the half-space estimate), so this guards
    # against unit/scale errors, not emission physics; the 10 kHz certification run
    # reports the tight anchor comparison (delta_T ~ 10 cells, formula applicable).
    assert abs(absorbed["A_inc_mid"]) > 0.2 * absorbed["A_inc_expected_lu"]
    assert abs(absorbed["A_inc_mid"]) < 20.0 * absorbed["A_inc_expected_lu"]
    # Contrast thresholds calibrated by the 2026-07-04 control experiment in this exact
    # rig (charsplit): strip 0.30, equilibrium clamp 0.35, rigid lid 0.82. The compact
    # diagnostic rig carries O(0.1-0.2) systematics (1-period window, ring residue), so
    # this is a DETECT-vs-ABSORB contrast test, never the 10 kHz gate.
    assert absorbed["R_abs"] < 0.45
    assert reflected["R_abs"] > 0.65
    assert reflected["R_abs"] > 2.0 * absorbed["R_abs"]


def test_reflection_config_parses_and_carries_gate():
    cfg = yaml.safe_load(
        Path("configs/phase4_open_top_reflection_10k.yaml").read_text(encoding="utf-8")
    )
    assert cfg["case"]["p4_stage"] == "P4-1"
    assert float(cfg["gates"]["reflection_abs"]) == 0.05
    assert cfg["open_boundary"]["type"] == "open_cbc"
    assert cfg["inheritance"]["gas_config_path"].endswith("gas_air_10k_d2q37_levelc_dx2p6.yaml")
