import numpy as np

from core.lattice_d2q21 import assert_d2q21_moments, make_d2q21, moment


def test_p2_1_layout_opposite_and_moment_contract():
    lattice = make_d2q21()
    assert lattice.c.shape == (21, 2)
    assert lattice.w.shape == (21,)
    assert lattice.q == 21
    assert lattice.d == 2
    assert np.array_equal(lattice.c[lattice.opposite], -lattice.c)
    assert_d2q21_moments(tol=1.0e-12)


def test_p2_1_even_through_6_odd_symmetry_through_7_only():
    theta = 2.0 / 3.0
    assert abs(moment((6, 0)) - 15.0 * theta**3) < 1.0e-12
    assert abs(moment((4, 2)) - 3.0 * theta**3) < 1.0e-12
    for total in (1, 3, 5, 7):
        for m in range(total + 1):
            assert abs(moment((m, total - m))) < 1.0e-12

