"""Run Phase 1 verification without requiring pytest.

This is useful in PyCharm when the interpreter has NumPy but pytest is not
installed. It executes every zero-argument test function in
verification/test_phase1_*.py and exits nonzero on the first failed batch.
"""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path
import sys
import traceback


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    failures: list[tuple[str, str, str]] = []
    for path in sorted((ROOT / "verification").glob("test_phase1_*.py")):
        module_name = f"verification.{path.stem}"
        module = importlib.import_module(module_name)
        for name, func in inspect.getmembers(module, inspect.isfunction):
            if not name.startswith("test_"):
                continue
            try:
                func()
                print(f"PASS {module_name}.{name}")
            except Exception:
                failures.append((module_name, name, traceback.format_exc()))
                print(f"FAIL {module_name}.{name}")

    if failures:
        print("\nFAILURES")
        for module_name, name, tb in failures:
            print(f"--- {module_name}.{name} ---")
            print(tb)
        raise SystemExit(1)

    print("\nAll direct Phase_1 verification tests passed.")


if __name__ == "__main__":
    main()

