from reference.continuum_1d_freq import (
    solve_level_A_frequency,
    solve_level_B_frequency,
    solve_level_C_frequency,
)
from reference.continuum_1d_time import run_level_C_time
from reference.constants import default_params


def test_phase1_baseline_cases_are_constructible():
    params = default_params()
    a = solve_level_A_frequency(10_000.0, 1.0, params=params)
    b = solve_level_B_frequency(10_000.0, 1000.0, params=params)
    c = solve_level_C_frequency(10_000.0, 1000.0, params.C_A, params=params)
    t = run_level_C_time(10_000.0, 1000.0, params.C_A, params=params)

    assert a.level == "A"
    assert b.level == "B"
    assert c.level == "C"
    assert t.level == "C"
    assert c.energy_residual_rel < 1.0e-3

