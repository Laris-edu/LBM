"""Cross-machine / cross-environment numerical-consistency digest.

Runs the G1a contract smoke (serial scheduling, toy-scaled, ~1 min) and
prints a sha256 digest over the numerically meaningful outputs (gate rows +
N=5 harmonic payloads; volatile fields like run_id/timestamps/paths are
excluded by construction because neither payload contains them).

Usage (identical on every machine):

    python -m scripts.phase5_ab_smoke_digest

Discipline: two environments may host authoritative runs interchangeably
ONLY if their digests match bitwise. If they differ, either align versions
(requirements.txt pins python 3.14.x + numpy/h5py/PyYAML/pytest) or archive
the machine fingerprint in each run's provenance and treat cross-machine
reproduction as tolerance-level (gate margins >> 1e-15 FP scheduling
differences) — that downgrade is a documented decision, not a default.

The same check re-runs after ANY dependency upgrade on a single machine
(the digest is an environment regression anchor, not only a pairing tool).
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import tempfile
from pathlib import Path

from scripts.phase5_g1a_amplitude_envelope import DEFAULT_CONFIG, run_g1a


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ab_digest_") as tmp:
        result = run_g1a(DEFAULT_CONFIG, Path(tmp), smoke=True, workers=1)
        out_dir = Path(result["out_dir"])
        rows = json.load((out_dir / "gate_evaluation.json").open(encoding="utf-8"))["rows"]
        harmonics = json.load((out_dir / "harmonic_fit.json").open(encoding="utf-8"))
    payload = (json.dumps(rows, sort_keys=True) + json.dumps(harmonics, sort_keys=True))
    digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
    print("AB_SMOKE_DIGEST %s" % digest)
    print("machine: %s | %s | python %s | numpy %s" % (
        platform.node(), platform.processor() or platform.machine(),
        sys.version.split()[0],
        __import__("numpy").__version__))
    return 0


if __name__ == "__main__":
    sys.exit(main())
