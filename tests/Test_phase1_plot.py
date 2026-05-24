"""PyCharm-friendly entry point for Phase_1 figure generation."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.plot_phase1_reference import main  # noqa: E402


if __name__ == "__main__":
    main()

