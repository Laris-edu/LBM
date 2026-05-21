"""PyCharm-friendly entry point for Phase 1 reference data generation."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.phase1_sweeps import generate_all  # noqa: E402


def main() -> None:
    for path in generate_all(ROOT / "results" / "phase1_reference"):
        print(path)


if __name__ == "__main__":
    main()

