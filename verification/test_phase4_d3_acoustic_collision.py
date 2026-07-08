"""P4-D3 core-step tests: the acoustic simplified-collision switch.

Project: docs/Phase_4/M4/P4_D3_Multidomain_Acoustic_Project.md (sections 1, 7).

The core step adds ``CollisionScales.acoustic_simplified_collision`` (default off), wired through
``core.collision_smrt.collide_fg``: the coarse sound-only acoustic subdomain drops the heat-flux
min-norm regularization (its Gram is fragile; the tau32-tuned closure is thermal-specific and
undefined for a sound-only domain). These tests certify:

  * SAFETY: default off on every frozen config; switch-on is bit-identical to the known
    regularized_heat_flux_factor==0 fast path; the heat-flux Gram is never solved in acoustic mode.
  * PHYSICS: the shipped acoustic config (configs/phase4_acoustic_coarse_dx334.yaml) is a stable,
    low-backscatter medium.
  * HONEST FINDING (corrects section 7): reflection-accumulation stability is set by the STRONG
    LOCAL FILTER, not the heat-flux removal -- the strong filter survives the reflecting box for
    both collisions, while the simplified collision with only the weak inherited filter crashes.

Note (documented, not asserted as a gate): dropping the heat-flux reconstruction lowers the sound
speed ~5% (a physical effect -- the strong filter alone leaves c unchanged); the acoustic domain's
sound speed is re-tuned in D3-2. Backscatter and stability are the core-step gates here."""

from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pytest

import core.collision_smrt as csm
from core.collision_smrt import collide_fg
from core.equilibrium import equilibrium_fg
from core.lattice import make_lattice
from core.unit_mapping import create_unit_mapping
from scripts.phase2_m2_verification import load_config
from scripts.phase4_d3_acoustic_collision_probe import (
    STRONG_FILTER,
    WEAK_FILTER,
    full_heatflux_variant,
    run_closed_box,
    run_open,
    with_filter,
)

ACOUSTIC_CONFIG = Path("configs/phase4_acoustic_coarse_dx334.yaml")
FROZEN_CONFIGS = [
    Path("configs/gas_air_10k_d2q37_levelc_dx2p6.yaml"),
    Path("configs/gas_air_10k_d2q37_physical_timestep.yaml"),
    Path("configs/phase3_m3_grad_10k_dx2p6.yaml"),
]


def _perturbed_state(mapping, lattice, seed=0):
    rng = np.random.default_rng(seed)
    ny, nx = 6, 5
    rho = 1.0 + 0.01 * rng.standard_normal((ny, nx))
    u = 0.005 * rng.standard_normal((ny, nx, 2))
    theta = float(mapping.theta_ref_lu) * (1.0 + 0.01 * rng.standard_normal((ny, nx)))
    f, g = equilibrium_fg(rho, u, theta, mapping.lattice.S, lattice)
    f = f * (1.0 + 0.001 * rng.standard_normal(f.shape))
    g = g * (1.0 + 0.001 * rng.standard_normal(g.shape))
    return f, g


# ---------------------------------------------------------------- safety (fast)

@pytest.mark.parametrize("cfg_path", FROZEN_CONFIGS)
def test_default_off_on_frozen_configs(cfg_path):
    """Every frozen Phase_2/3 config leaves acoustic_simplified_collision off (bit-identical)."""

    m = create_unit_mapping(load_config(cfg_path))
    assert m.collision.acoustic_simplified_collision is False
    assert m.to_metadata()["acoustic_simplified_collision"] is False


def test_switch_equals_heatflux_zero_fast_path():
    """Switch on is numerically identical to regularized_heat_flux_factor==0 (specified)."""

    base = load_config(ACOUSTIC_CONFIG)
    lattice = make_lattice("D2Q37")
    m_on = create_unit_mapping(base)  # the config already sets the switch on
    assert m_on.collision.acoustic_simplified_collision is True

    zeroed = copy.deepcopy(base)
    zeroed["collision"]["acoustic_simplified_collision"] = False
    zeroed["collision"]["regularized_heat_flux_factor"] = 0.0
    zeroed["collision"]["regularized_heat_flux_factor_policy"] = "specified"
    zeroed["collision"]["heat_flux_retention_policy"] = "specified"
    m_zero = create_unit_mapping(zeroed)

    f, g = _perturbed_state(m_on, lattice)
    f_on, g_on = collide_fg(f, g, m_on, lattice=lattice)
    f_z, g_z = collide_fg(f, g, m_zero, lattice=lattice)
    assert np.array_equal(f_on, f_z)
    assert np.array_equal(g_on, g_z)


def test_switch_changes_collision_versus_full_heatflux():
    """Non-triviality: with the heat-flux regularization active the result differs from acoustic mode."""

    base = load_config(ACOUSTIC_CONFIG)
    lattice = make_lattice("D2Q37")
    m_simple = create_unit_mapping(base)
    m_full = create_unit_mapping(full_heatflux_variant(base))
    assert m_full.collision.acoustic_simplified_collision is False
    assert m_full.collision.regularized_heat_flux_factor != 0.0

    f, g = _perturbed_state(m_simple, lattice)
    _, g_simple = collide_fg(f, g, m_simple, lattice=lattice)
    _, g_full = collide_fg(f, g, m_full, lattice=lattice)
    assert not np.array_equal(g_simple, g_full)


def test_acoustic_mode_never_solves_the_heatflux_gram(monkeypatch):
    """By construction: acoustic mode bypasses the heat-flux min-norm Gram entirely; the full
    heat-flux collision does invoke it (so the spy is not vacuous)."""

    calls = {"n": 0}
    real = csm._weighted_minimum_norm_heat_flux_delta

    def spy(*args, **kwargs):
        calls["n"] += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(csm, "_weighted_minimum_norm_heat_flux_delta", spy)
    base = load_config(ACOUSTIC_CONFIG)
    lattice = make_lattice("D2Q37")

    m_simple = create_unit_mapping(base)
    f, g = _perturbed_state(m_simple, lattice)
    collide_fg(f, g, m_simple, lattice=lattice)
    assert calls["n"] == 0  # acoustic mode: heat-flux Gram never solved

    m_full = create_unit_mapping(full_heatflux_variant(base))
    collide_fg(f, g, m_full, lattice=lattice)
    assert calls["n"] > 0  # full heat-flux: the Gram IS solved -> the spy is meaningful


# ---------------------------------------------------------------- physics (solver runs)

def test_acoustic_medium_stable_and_low_backscatter():
    """The shipped simplified acoustic config carries an outgoing pulse: stable, backscatter < gate."""

    r = run_open(load_config(ACOUSTIC_CONFIG), ny=512)
    assert r["crash_frac"] is None                # stable over the transit
    assert r["worst_backscatter"] < 0.05          # gate: below the P4-1 threshold
    assert 0.5 < r["amplitude_survival"] < 1.1    # low dissipation, no growth
    # Documented residual (not a gate): dropping the heat-flux reconstruction lowers c ~5%.
    assert r["sound_speed_err"] < -0.02           # the physical shift is present (re-tuned in D3-2)


def test_reflection_stability_is_the_filter_not_the_heatflux():
    """Honest finding: the STRONG local filter -- not the heat-flux removal -- stabilises reflected-
    energy accumulation. Strong filter survives the box for the simplified collision AND the full
    heat-flux collision; the simplified collision with only the weak inherited filter crashes."""

    aco = load_config(ACOUSTIC_CONFIG)
    full = full_heatflux_variant(aco)

    simple_strong = run_closed_box(with_filter(aco, *STRONG_FILTER), ny=256, n_transits=4.0)
    simple_weak = run_closed_box(with_filter(aco, *WEAK_FILTER), ny=256, n_transits=4.0)
    full_strong = run_closed_box(with_filter(full, *STRONG_FILTER), ny=256, n_transits=4.0)

    assert simple_strong["survived"], "simplified + strong filter should survive the reflecting box"
    assert full_strong["survived"], "full heat-flux + strong filter also survives -> filter is the key"
    assert not simple_weak["survived"], "simplified + weak filter crashes -> the strong filter is needed"
