"""G2-T / G2-A harmonic-transfer machinery tests (contract §7.1/§7.2 deliverable, WP2).

Mechanism-level certification of the transfer-gate instrument chain: the
continuum sealed-adiabatic closed form (anchored against the WP1-3 three-way
verified value — an INDEPENDENT number, not this code), the outgoing-mode
continuity construction (machine-exact mass consistency, odd symmetry, and a
quantitative half-space anchor against the M4 compact-source formula — an
independent module), the biharmonic-filter amplitude symbol (asserted against
the real ``conservative_biharmonic_filter``, not re-derived), and the
characteristic-decomposition non-degeneracy. The authoritative G2 runs
(full frequency matrix on the frozen stacks) are recorded in Phase5_STATUS §3;
their verdicts are NOT asserted here (physics belongs to the gate).
"""

from __future__ import annotations

import cmath
import math
from pathlib import Path

import numpy as np
import pytest

from core.solver import conservative_biharmonic_filter
from farfield.compact_source import thermal_pumping_velocity_m_s
from scripts.phase2_m2_verification import load_config
from scripts.phase5_g2a_acoustic_transfer import (
    filter_step_multiplier,
    measure_modal_symbol,
    span_decay_prediction,
    symbol_at,
    two_stage_phase_fit,
)
from scripts.phase5_g2t_thermal_transfer import (
    outgoing_mode_prediction,
    sealed_adiabatic_closed_form,
    synthetic_leakage_row,
)

DT_S = 1.95881e-9
DX_M = 2.61175e-6
ALPHA_SI = 2.2233775895e-5
ALPHA_LU = ALPHA_SI * DT_S / DX_M**2


def test_closed_form_anchors_three_way_verified_value():
    # WP1-3 (2026-07-22) three-way verification: BVP = closed form = nonlinear
    # 1D at L=2.356*delta, 10 kHz, gamma=1.4 -> Y/Y_hs = 0.9202 @ +3.53 deg.
    om = 2.0 * math.pi * 1.0e4 * DT_S
    y = sealed_adiabatic_closed_form(om, ALPHA_LU, 24.0, 1.4)
    assert abs(y) == pytest.approx(0.9202, abs=2e-4)
    assert math.degrees(math.atan2(y.imag, y.real)) == pytest.approx(3.53, abs=0.05)
    # limits: large box -> half-space (ratio -> 1); tiny box -> conduction-dominated
    y_hs = sealed_adiabatic_closed_form(om, ALPHA_LU, 5000.0, 1.4)
    assert abs(y_hs) == pytest.approx(1.0, abs=1e-3)


def test_closed_form_units_cancel():
    # SI evaluation must equal LU evaluation of the same physical box
    om_si = 2.0 * math.pi * 1.0e4
    y_si = sealed_adiabatic_closed_form(om_si, ALPHA_SI, 24.0 * DX_M, 1.4)
    y_lu = sealed_adiabatic_closed_form(om_si * DT_S, ALPHA_LU, 24.0, 1.4)
    assert y_si == pytest.approx(y_lu, rel=1e-12)


def test_outgoing_mode_prediction_continuity_and_symmetry():
    n = 48
    rng = np.random.default_rng(7)
    prof = rng.normal(size=n) + 1j * rng.normal(size=n)  # arbitrary complex profile
    om, th0, that = 0.01, 0.7, 7e-4
    u = outgoing_mode_prediction(prof, om, that, th0)
    # exact linearized continuity per mode: du/dy (spectral) == i*om*(theta-<theta>)/th0
    ks = 2.0 * math.pi * np.fft.fftfreq(n)
    du = np.fft.ifft(1j * ks * np.fft.fft(u))
    theta_field = prof * that / th0
    resid = np.max(np.abs(du - 1j * om * (theta_field - theta_field.mean())))
    assert resid < 1e-16
    # even (two-sided symmetric) profile -> odd velocity with wall/mid nulls
    y = np.arange(n)
    prof_even = np.cos(2 * math.pi * y / n) + 0.3 * np.cos(6 * math.pi * y / n)
    u = outgoing_mode_prediction(prof_even, om, that, th0)
    assert abs(u[0]) < 1e-18 and abs(u[n // 2]) < 1e-18
    assert np.max(np.abs(u[1:] + u[::-1][: n - 1])) < 1e-17


def test_outgoing_mode_prediction_halfspace_anchor_vs_compact_source():
    # In a box much taller than delta_T, the plateau velocity above the layer
    # must reproduce the M4 compact-source pumping formula (independent module).
    om_si = 2.0 * math.pi * 1.0e4
    delta_si = math.sqrt(2.0 * ALPHA_SI / om_si)
    n = 4096
    dy = delta_si / 16.0  # box height 256 delta: half-space regime
    y = (np.arange(n) - 0.0) * dy
    y_sym = np.minimum(y, n * dy - y)  # two-sided symmetric decaying layer
    prof = np.exp(-(1.0 + 1j) * y_sym / delta_si)
    t0, eps = 300.0, 1e-3
    om_grid = om_si * dy  # per-cell omega scaling: u comes out in m/s
    u = outgoing_mode_prediction(prof, om_grid, eps * t0, t0)
    j = int(8 * delta_si / dy)  # 8 delta above the wall (layer decayed to e^-8)
    # the sealed construction carries the exact box-return flow -i*om*<theta>*y
    # (the pressure mode absorbing the net pumped mass); remove it analytically
    # to expose the half-space limit: at y=8*delta it is 2y/H = 6.25% of u_hs
    theta_field = prof * eps
    backflow = 1j * om_grid * theta_field.mean() * j
    u_halfspace = u[j] + backflow
    u_ref = thermal_pumping_velocity_m_s(eps * t0, T0_K=t0, omega_rad_s=om_si,
                                         alpha_m2_s=ALPHA_SI)
    assert abs(u_halfspace - u_ref) / abs(u_ref) < 0.002
    # and the backflow itself is the dominant residual (documents the physics)
    assert abs(u[j] - u_ref) / abs(u_ref) == pytest.approx(2.0 * j / n, rel=0.05)


def test_filter_symbol_matches_real_filter():
    # amplitude multiplier of conservative_biharmonic_filter on a pure y-mode
    ny, nx = 64, 4
    k = 2.0 * math.pi * 5 / ny
    field = np.cos(k * np.arange(ny))[:, None, None] * np.ones((ny, nx, 1))
    strength = 0.03
    out = conservative_biharmonic_filter(field, strength, None)
    meas = float(np.max(np.abs(out[:, 0, 0])) / np.max(np.abs(field[:, 0, 0])))
    pred = filter_step_multiplier(k, strength, 1)
    assert meas == pytest.approx(pred, rel=1e-10)
    # passes compose multiplicatively
    out6 = field.copy()
    for _ in range(6):
        out6 = conservative_biharmonic_filter(out6, strength, None)
    assert float(np.max(np.abs(out6[:, 0, 0]))) == pytest.approx(
        filter_step_multiplier(k, strength, 6), rel=1e-9)


def test_span_decay_prediction_composition():
    pred = span_decay_prediction(k_lu=0.06, omega_lu=0.0157, c_lu=0.255,
                                 nu_lu=3.5e-3, alpha_lu=5.0e-3, gamma=1.4,
                                 strength=0.03, passes=6, span_cells=154.0)
    # both channels positive, total ratio in (0, 1); classical part matches formula
    a_cl = 0.0157**2 / (2 * 0.255**3) * (4.0 / 3.0 * 3.5e-3 + 0.4 * 5.0e-3)
    assert pred["per_cell_classical"] == pytest.approx(a_cl, rel=1e-12)
    assert 0.0 < pred["span_ratio"] < 1.0
    # zero-strength filter contributes exactly nothing
    p0 = span_decay_prediction(0.06, 0.0157, 0.255, 3.5e-3, 5.0e-3, 1.4, 0.0, 6, 154.0)
    assert p0["per_cell_filter"] == 0.0


def test_two_stage_phase_fit_immune_to_row_spacing_aliasing():
    # v1 REGRESSION: control-row spacing ~51 cells ~= lambda(20 kHz) ~52 cells
    # aliased the naive global unwrap (c_meas came out +1410%). The v2
    # two-stage fit (cluster-local k -> carrier detrend) must recover k
    # exactly on the same geometry.
    k_true = 0.1145  # realized 20 kHz wavenumber on the coarse domain
    control = [230, 282, 333, 384]
    d = 4
    sample = sorted(set(control + [r - d for r in control] + [r + d for r in control]))
    a0, grow = 7e-6, 2.2e-4  # includes the measured spatial gain
    p_hat = {r: a0 * math.exp(grow * r) * cmath.exp(-1j * k_true * r) for r in sample}
    fit = two_stage_phase_fit(p_hat, control, sample, d)
    assert fit["k_fit"] == pytest.approx(k_true, abs=1e-9)
    assert fit["max_residual_deg"] < 1e-6
    # the naive fit on cluster centers is demonstrably aliased on this geometry
    phases = np.unwrap([math.atan2(p_hat[r].imag, p_hat[r].real) for r in control])
    k_naive = -float(np.polyfit(np.array(control, float), phases, 1)[0])
    assert abs(k_naive - k_true) / k_true > 0.5


def test_z_eff_split_nondegenerate_on_dispersive_carrier():
    # pure outgoing wave in a band where c_eff = 1.057 c_nom (measured 20 kHz
    # dispersion): the nominal-z0 split manufactures |A-|/|A+| ~ delta/2 by
    # construction; the z_eff basis separates directions cleanly.
    z0, delta = 0.26, 0.057
    z_eff = z0 * (1.0 + delta)
    p = 1.0 + 0.3j
    v = p / z_eff
    am_over_ap_nominal = abs(0.5 * (p - z0 * v)) / abs(0.5 * (p + z0 * v))
    am_over_ap_eff = abs(0.5 * (p - z_eff * v)) / abs(0.5 * (p + z_eff * v))
    assert am_over_ap_nominal == pytest.approx(delta / 2, rel=0.06)
    assert am_over_ap_eff < 1e-15


def test_medium_symbol_measurement_and_interpolation():
    base = load_config(Path("configs/phase4_acoustic_coarse_dx334.yaml"))
    rows = measure_modal_symbol(base, ny=128, nx=4, modes=[1, 2], n_steps=400,
                                fit_skip_frac=0.33, eps_seed=1e-5,
                                log=lambda *_: None)
    assert len(rows) == 2
    for r in rows:
        assert math.isfinite(r["c_m_s"]) and math.isfinite(r["sigma_per_cell"])
        # sane acoustic band: near the calibrated air speed, tiny attenuation
        assert abs(r["c_m_s"] / 347.0 - 1.0) < 0.20
        assert abs(r["sigma_per_cell"]) < 1e-3
    fs = sorted(r["f_hz"] for r in rows)
    mid = 0.5 * (fs[0] + fs[1])
    s = symbol_at(rows, mid)
    assert min(r["c_m_s"] for r in rows) <= s["c_m_s"] <= max(r["c_m_s"] for r in rows)
    with pytest.raises(ValueError):
        symbol_at(rows, fs[1] * 3.0)


def test_characteristic_decomposition_nondegenerate():
    # synthetic outgoing wave p = Z0 v -> A- = 0; incoming -> A+ = 0
    z0 = 0.26
    p, v = 1.0 + 0.2j, (1.0 + 0.2j) / z0
    a_plus = 0.5 * (p + z0 * v)
    a_minus = 0.5 * (p - z0 * v)
    assert abs(a_minus) < 1e-15 and abs(a_plus) == pytest.approx(abs(p), rel=1e-12)
    p2, v2 = 1.0 + 0.2j, -(1.0 + 0.2j) / z0
    assert abs(0.5 * (p2 + z0 * v2)) < 1e-15


def test_synthetic_leakage_row_floor_and_detection():
    # pure tone on a realistic sample grid -> non-target leakage at machine floor
    f = 1.0e4
    t = np.arange(0, 3.0 / f, 1.0 / f / 64.0)
    leak = synthetic_leakage_row(t, f, 1.0, 5)
    assert leak <= 1e-10
    # non-degeneracy: the same fit DOES see a real 2f at its injected level
    from postproc.multiharmonic_fit import fit_multiharmonic
    om = 2.0 * math.pi * f
    mask = t >= 1.0 / f
    sig = np.cos(om * t[mask]) + 3e-6 * np.cos(2 * om * t[mask] + 0.5)
    fit = fit_multiharmonic(t[mask], sig, om, n_harmonics=5)
    assert fit.leakage_relative(1)[2] == pytest.approx(3e-6, rel=1e-3)


def test_g2t_and_g2a_configs_load_and_are_consistent():
    for rel, proto_key in (("configs/phase5/g2_thermal_transfer/g2t_10k20k_dx2p6.yaml", "g2t"),
                           ("configs/phase5/g2_acoustic_transfer/g2a_10k20k_coarse.yaml", "g2a")):
        cfg = load_config(Path(rel))
        assert proto_key in cfg and f"{proto_key}_smoke" in cfg and "gates" in cfg
    g2t = load_config(Path("configs/phase5/g2_thermal_transfer/g2t_10k20k_dx2p6.yaml"))
    # mandatory frequencies frozen by contract §7.1
    assert [float(f) for f in g2t["g2t"]["frequencies_Hz"]] == [1.0e4, 2.0e4]
    # control rows must avoid the wall-reconstruction rows and the mid-height null
    ny = int(g2t["g2t"]["ny"])
    for r in g2t["g2t"]["control_rows"]:
        assert 3 <= int(r) < ny // 2
    # contract §7.1 thresholds frozen
    assert float(g2t["gates"]["transfer_amp_rel"]) == 0.10
    assert float(g2t["gates"]["window_amp_rel"]) == 0.03
    g2a = load_config(Path("configs/phase5/g2_acoustic_transfer/g2a_10k20k_coarse.yaml"))
    freqs = [float(fp["frequency_Hz"]) for fp in g2a["g2a"]["frequencies"]]
    assert freqs == [1.0e4, 2.0e4]
    # v2 symbol rows pre-registered in BOTH protocol blocks
    for block in ("g2a", "g2a_smoke"):
        sym = g2a[block]["symbol"]
        assert len(sym["modes"]) >= 2 and int(sym["n_steps"]) >= 400
    # the 20 kHz leg must NOT gate c_dev (single-frequency M4 calibration guard)
    assert bool(g2a["g2a"]["frequencies"][0]["gate_c_dev"]) is True
    assert bool(g2a["g2a"]["frequencies"][1]["gate_c_dev"]) is False
    # control rows (+ FD stencil) stay below the top sponge
    ny, n_abs = int(g2a["g2a"]["ny"]), int(g2a["g2a"]["n_abs"])
    d = int(g2a["g2a"]["grad_stencil_cells"])
    for fr in g2a["g2a"]["control_rows_frac"]:
        assert int(round(float(fr) * ny)) + d < ny - n_abs
        assert int(round(float(fr) * ny)) - d > int(g2a["g2a"]["y_s"])
