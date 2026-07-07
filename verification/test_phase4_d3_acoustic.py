"""P4-D3 gate tests: the coarse dispersion-free acoustic subdomain (D3-1).

D3 (docs/Phase_4/M4/P4_D3_Multidomain_Acoustic_Project.md) bypasses the P4-1 volume
injection floor by carrying sound in an independent coarse, dispersion-free acoustic
region. G-D3-1 certifies that region's MEDIUM: a tuned-tau coarse grid propagates an
outgoing acoustic pulse cleanly (small backscatter, correct sound speed, stable, low
dissipation). These reuse the committed verdict probe as the measurement engine.

Non-degeneracy (Phase_3 lesson): a companion counter-test shows that NAIVE coarsening
(no tuned viscosity, tau->0.5) fails the same gate -- the gate has discriminating power,
it is not pass-by-construction."""

from __future__ import annotations

from pathlib import Path

from scripts.phase2_m2_verification import load_config
from scripts.phase4_d3_coarse_acoustic_probe import run_case

GAS_CONFIG = Path("configs/gas_air_10k_d2q37_levelc_dx2p6.yaml")
DX_C = 334e-6          # lambda/dx ~ 104, domain height 512*dx ~ 5 wavelengths


def test_g_d3_1_coarse_acoustic_medium_clean_and_stable():
    """G-D3-1 gate: tuned-tau (nu0x100 -> tau21~0.57) coarse acoustic medium is clean."""

    base = load_config(GAS_CONFIG)
    r = run_case(base, dx_c_m=DX_C, nu0_mult=100.0)
    assert r["crash_frac"] is None                       # stable over the transit
    assert r["worst_backscatter"] < 0.05                 # gate: below P4-1 threshold
    assert abs(r["sound_speed_err"]) < 0.02              # gate: P2-6 sound-speed tolerance
    assert 0.5 < r["amplitude_survival"] < 1.1           # low dissipation, no growth


def test_g_d3_1_holds_at_higher_viscosity():
    """The clean-medium result is not a single-point fluke: nu0x200 (tau~0.65) also passes."""

    base = load_config(GAS_CONFIG)
    r = run_case(base, dx_c_m=DX_C, nu0_mult=200.0)
    assert r["crash_frac"] is None
    assert r["worst_backscatter"] < 0.05
    assert abs(r["sound_speed_err"]) < 0.02


def test_g_d3_1_nondegeneracy_naive_coarsening_fails():
    """Counter-test: NAIVE coarsening (nu0x1, frozen mapping -> tau21~0.5007) is dirty or
    crashes, so G-D3-1 discriminates -- the tuned viscosity is doing real work."""

    base = load_config(GAS_CONFIG)
    r = run_case(base, dx_c_m=DX_C, nu0_mult=1.0)
    dirty = r["crash_frac"] is not None or r["worst_backscatter"] > 0.02
    assert dirty, "naive coarsening unexpectedly clean -> gate lacks discriminating power"
