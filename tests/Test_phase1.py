"""Direct PyCharm smoke test for Phase 1 reference models.

Run this file the same way as tests/Test_numba.py. It does not require pytest.
"""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.continuum_1d_freq import solve_level_C_frequency  # noqa: E402
from reference.constants import default_params  # noqa: E402
from reference.phase1_sweeps import generate_all  # noqa: E402
from scripts.phase1_verify_direct import main as run_phase1_verification  # noqa: E402


if __name__ == "__main__":
    params = default_params()
    result = solve_level_C_frequency(10_000.0, 1000.0, params.C_A, params=params)

    print("Phase 1 baseline Level C:")
    print(f"T_s_hat = {result.T_s_hat}")
    print(f"q_g_hat = {result.q_g_hat}")
    print(f"p_hat(y=8delta_T) = {result.p_at(8.0)}")
    print(f"energy_residual_rel = {result.energy_residual_rel:.3e}")
    print()

    print("Running Phase 1 direct verification...")
    run_phase1_verification()
    print()

    print("Regenerating Phase 1 reference CSV files...")
    for path in generate_all(ROOT / "results" / "phase1_reference"):
        print(path)

