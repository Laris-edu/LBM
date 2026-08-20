"""Contract tests for the offset-lens discriminator (plan PLAN_v1.0)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from reference.constants import default_params  # noqa: E402
from reference.nonlinear_nsf_1d import g0_measured_transport  # noqa: E402
from reference.nsf_hot_base_linear_1d import (  # noqa: E402
    solve_base_state,
    solve_linear_response,
)
from reference.strict_face_robin_qs import robin_qs_matrix_bvp  # noqa: E402
from scripts.phase5_a2asb_offset_lenses import (  # noqa: E402
    ALPHA_EXPONENT,
    BAND_DYNAMIC_PP,
    BAND_FAR_PP,
    BAND_STATIC_PP,
    BAND_STATIC_SLOPE,
    D_EQ_MEASURED_PCT,
    LENSES,
    NSF_G0_ANCHORS_PCT,
    classify_offset,
    _lattice_transport,
)

H_LU, OMEGA, ALPHA, THETA0, RHO = 48.0, 1.0e-3, 2.0e-2, 0.35, 1.0
CP = 1.0 / (1.4 - 1.0) + 1.0
K0 = ALPHA * RHO * CP


def test_lattice_local_isobaric_identity():
    """On an exactly isobaric base at reference pressure, the lattice lens
    (k ~ rho T^2.04, isobaric adv derivative) IS the k~T^1.04 lens."""

    n = 192
    y = (np.arange(n) + 0.5) / n
    th_w = THETA0 * 1.05
    th_b = THETA0 * (1.0 + 0.05 * (1.0 - y) ** 1.3)      # arbitrary smooth
    p_bar = RHO * THETA0                                  # reference pressure
    rho_b = p_bar / th_b
    kw = dict(n_ref=n, h_lu=H_LU, omega_lu=OMEGA, k0=K0, theta0=THETA0,
              beta=1.04, c_p=CP, theta_w=th_w, theta_amb=THETA0,
              theta_base=th_b, rho_base=rho_b)
    y_latt = robin_qs_matrix_bvp(**kw, bulk_mode="lattice_local",
                                 bulk_beta=2.04, adv_beta=1.04,
                                 rho_ref_lu=RHO)["Y"]
    y_pow = robin_qs_matrix_bvp(**kw, bulk_mode="powerlaw_local",
                                bulk_beta=1.04, adv_beta=1.04)["Y"]
    assert abs(y_latt / y_pow - 1.0) < 1e-12
    # fixed-density adv derivative (default lattice lens) must differ finitely
    y_latt2 = robin_qs_matrix_bvp(**kw, bulk_mode="lattice_local",
                                  bulk_beta=2.04, adv_beta=2.04,
                                  rho_ref_lu=RHO)["Y"]
    assert 1e-12 < abs(y_latt2 / y_pow - 1.0) < 0.05


def test_legacy_defaults_unchanged():
    n = 96
    y = (np.arange(n) + 0.5) / n
    th_b = THETA0 * (1.0 + 0.05 * (1.0 - y))
    rho_b = np.full(n, RHO)
    kw = dict(n_ref=n, h_lu=H_LU, omega_lu=OMEGA, k0=K0, theta0=THETA0,
              beta=1.04, c_p=CP, theta_w=THETA0 * 1.05, theta_amb=THETA0,
              theta_base=th_b, rho_base=rho_b, bulk_mode="powerlaw_local")
    assert robin_qs_matrix_bvp(**kw)["Y"] == robin_qs_matrix_bvp(
        **kw, bulk_beta=1.04, adv_beta=1.04)["Y"]


@pytest.fixture(scope="module")
def nsf_setup():
    params = default_params()
    tr = g0_measured_transport(params)
    alpha0 = params.kg / (params.rho0 * params.cp)
    import math
    delta = math.sqrt(2.0 * alpha0 / (2.0 * math.pi * 1.0e4))
    return params, tr, 4.61 * delta


def test_nsf_channel_cold_inert_and_off_identical(nsf_setup):
    params, tr, height = nsf_setup
    base = solve_base_state(params, tr, theta_dc=0.0, height_m=height,
                            n_nodes=222)
    y_off = solve_linear_response(base, params, tr, frequency_hz=1e4,
                                  model="full").Y_raw
    y_on = solve_linear_response(base, params, tr, frequency_hz=1e4,
                                 model="full",
                                 lattice_pressure_channel=True).Y_raw
    assert abs(y_on / y_off - 1.0) < 1e-13   # T_bar' = 0 -> exactly inert


def test_nsf_channel_hot_finite_and_audited(nsf_setup):
    params, tr, height = nsf_setup
    base = solve_base_state(params, tr, theta_dc=0.05, height_m=height,
                            n_nodes=222)
    r_off = solve_linear_response(base, params, tr, frequency_hz=1e4,
                                  model="full")
    tr_lat = _lattice_transport(params, base.p_bar)
    base_lat = solve_base_state(params, tr_lat, theta_dc=0.05,
                                height_m=height, n_nodes=222)
    r_on = solve_linear_response(base_lat, params, tr_lat, frequency_hz=1e4,
                                 model="full", lattice_pressure_channel=True)
    assert abs(r_on.Y_raw / r_off.Y_raw - 1.0) > 1e-6   # channel does work
    # audit contract = NO DEGRADATION vs the certified plain branch (the
    # absolute audit levels are discretization-limited instrument properties)
    assert r_on.mass_neutrality_rel <= 1.5 * r_off.mass_neutrality_rel
    assert r_on.energy_integral_rel_dev <= 1.5 * r_off.energy_integral_rel_dev
    assert r_on.solve_residual_rel <= max(10.0 * r_off.solve_residual_rel,
                                          1e-14)


def test_classification_logic():
    thetas = {0.05: -0.206, 0.10: -0.241}
    static_far = {ln: {0.05: -2.8, 0.10: -5.3} for ln in ("L0", "L1", "L1b", "L2")}
    slopes0 = {ln: 0.0 for ln in static_far}
    # constitutive-dynamic: NSF lattice lands on the measurement
    cls = classify_offset({"d_latt_pct": {0.05: -0.30, 0.10: -0.60}},
                          static_far, thetas, slopes0)
    assert cls["label"] == "OFFSET_CONSTITUTIVE_DYNAMIC"
    # beyond-continuum: NSF stays far positive, statics far
    cls = classify_offset({"d_latt_pct": {0.05: 1.2, 0.10: 2.4}},
                          static_far, thetas, slopes0)
    assert cls["label"] == "OFFSET_BEYOND_CONTINUUM"
    # mixed: one theta close, one far
    cls = classify_offset({"d_latt_pct": {0.05: -0.3, 0.10: 2.0}},
                          static_far, thetas, slopes0)
    assert cls["label"] == "OFFSET_MIXED"
    # static closure branch + hatch
    static_close = dict(static_far)
    static_close["L1"] = {0.05: 0.1, 0.10: -0.2}
    cls = classify_offset(None, static_close, thetas, slopes0)
    assert cls["label"].startswith("NSF_LEG_NOT_COMPUTED/")
    assert cls["static_label"] == "OFFSET_CONSTITUTIVE_STATIC"
    assert cls["closing_static_lenses"] == ["L1"]


def test_frozen_lines():
    assert BAND_DYNAMIC_PP == 0.5 and BAND_FAR_PP == 1.0
    assert BAND_STATIC_PP == 0.3 and BAND_STATIC_SLOPE == 0.1
    assert ALPHA_EXPONENT == 2.04
    assert set(LENSES) == {"L0", "L1", "L1b", "L2"}
    assert abs(D_EQ_MEASURED_PCT[0.05] + 0.20595875450180046) < 1e-15
    assert abs(D_EQ_MEASURED_PCT[0.10] + 0.24073966354708487) < 1e-15
    assert abs(NSF_G0_ANCHORS_PCT[0.05] - 1.1816679235497007) < 1e-12
