"""A2a-STRICT_B wet reference pack builder (plan section 3.1; A-machine only).

Plan authority: docs/Phase_5/a2a_strict_b_experiment_plan_v1.0.md.  The four
authoritative wet runs (STATUS section 3.1, A-machine lineage) archived their
raw drive time series and base profiles but NOT the settled f snapshots, so
M_wet/A and pbar_wet are missing raw quantities.  Per the plan, the missing
cases are REPLAYED bit-for-bit with the ORIGINAL config and worker
(scripts.phase5_g4a_dc_basestate.run_tent via _g4a_case_worker, snapshot=True
— the flag only copies the settled state, the stepping is untouched), on the
SAME machine lineage (D5-3: per-machine bit-exact).  Replay fidelity gates:

  * the replayed base_profile must equal the archived one bit-for-bit
    (fallback tolerance 1e-12 relative, recorded as fp_equal);
  * every d_OP recomputed from the ARCHIVED raw series must sit within
    0.2 pp of the STATUS anchors (plan replay guard; the series are read
    directly, so the replay-deviation term of U_d^wet is 0);
  * the four runs' cold cases must agree bit-for-bit (same protocol).

Outputs (committed under archive/a2a_strict_b/ so both machines receive the
identical pre-registered inputs via git):

  wet_reference_pack.json         scalars, wet U_d parts, QS fields,
                                  provenance + SHA-256 of every source file
  wet_reference_pack_series.npz   raw wet series + base profiles (verbatim)
  wet_reference_pack.sha256       digest of the json itself

M_wet/A = (2 nx)^-1 sum_j sum_x sum_a f_wet (the two shared wet rows at half
weight each; plan section 1) and pbar_wet = (96 nx)^-1 sum rho*theta via the
canonical macroscopic recovery operator, both on the replayed settled
snapshot.  Wet window/eps-pair d_OP variants for U_d^wet are computed from
the archived series with the SAME windowed fit as the strict runner
(fit_admittance_window; the /2 of the wet double-band fitter cancels in
every d_OP ratio and is checked against the archived harmonic_fit.json).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.macroscopic import recover_macro  # noqa: E402
from core.solver import GasSolver2D  # noqa: E402
from scripts.phase2_m2_verification import load_config  # noqa: E402
from scripts.phase5_a2a_strict_b import (  # noqa: E402
    FIT_WINDOW_ALT,
    FIT_WINDOW_MAIN,
    fit_admittance_window,
    _sha256,
)
from scripts.phase5_g1a_amplitude_envelope import execute_cases  # noqa: E402
from scripts.phase5_g4a_dc_basestate import _g4a_case_worker  # noqa: E402

REPLAY_DOP_GUARD_PP = 0.2               # plan section 3.1 replay guard
FP_EQUAL_REL = 1.0e-12                  # bitwise-fallback tolerance

# frozen wet sources (STATUS section 3.1; results dirs = A-machine originals)
WET_SOURCES: dict[str, dict[str, Any]] = {
    "0.02": {"run_id": "20260803T185241Z",
             "results": "results/phase5/a2a_operating_point/20260803T185241Z",
             "archive": "archive/M5_runs/wp4_a2a_dc002_20260803T185241Z",
             "base": "base_dc002", "cold": "inc_cold",
             "hot": {"0.005": "inc_dc002_eps0.005",
                     "0.02": "inc_dc002_eps0.02"},
             "proto_key": "pdc2", "d_op_anchor_pct": -1.17,
             "r_dyn_frozen_pp": -2.12},
    "0.05": {"run_id": "20260801T081856Z",
             "results": "results/phase5/g4a_dc_base/20260801T081856Z",
             "archive": "archive/M5_runs/g4a_20260801T081856Z",
             "base": "base_100", "cold": "inc_cold_eps0.005",
             "hot": {"0.005": "inc_100_eps0.005", "0.02": "inc_100_eps0.02"},
             "proto_key": "g4a", "d_op_anchor_pct": -2.83,
             "r_dyn_frozen_pp": -5.18},
    "0.075": {"run_id": "20260803T185101Z",
              "results": "results/phase5/a2a_operating_point/20260803T185101Z",
              "archive": "archive/M5_runs/wp4_a2a_dc0075_20260803T185101Z",
              "base": "base_dc0075", "cold": "inc_cold",
              "hot": {"0.005": "inc_dc0075_eps0.005",
                      "0.02": "inc_dc0075_eps0.02"},
              "proto_key": "pdc2", "d_op_anchor_pct": -4.11,
              "r_dyn_frozen_pp": -7.61},
    "0.1": {"run_id": "20260802T104619Z",
            "results": "results/phase5/a2a_operating_point/20260802T104619Z",
            "archive": "archive/M5_runs/wp3_pdc2_20260802T104619Z",
            "base": "base_dc010", "cold": "inc_cold",
            "hot": {"0.005": "inc_dc010_eps0.005",
                    "0.02": "inc_dc010_eps0.02"},
            "proto_key": "pdc2", "d_op_anchor_pct": -5.31,
            "r_dyn_frozen_pp": -9.95},
}
COLD_REPLAY_POINT = "0.1"               # pinned cold-replay lineage (dc010)


def _read_case(h5path: Path, label: str) -> dict[str, np.ndarray]:
    import h5py

    out: dict[str, np.ndarray] = {}
    with h5py.File(h5path, "r") as h5:
        grp = h5[f"cases/{label}"]
        for k in grp.keys():
            out[k] = np.asarray(grp[k])
    return out


def _proto_of(src: dict[str, Any]) -> dict[str, Any]:
    """Original per-run protocol scalars from the archived resolved config."""

    cfg = load_config(REPO_ROOT / src["results"] / "config_resolved.yaml")
    p = cfg[src["proto_key"]]
    if src["proto_key"] == "g4a":
        rung = {str(r["name"]): r for r in p["hs_rungs"]}[str(p["canonical_rung"])]
        hs_rows = int(rung["hs_rows"])
        settle = float(rung["settle_periods"])
    else:
        hs_rows = int(p["hs_rows"])
        settle = float(p["settle_periods"])
    return {"frequency_Hz": float(p["frequency_Hz"]), "nx": int(p["nx"]),
            "samples_per_period": int(p["samples_per_period"]),
            "theta_dc": float(p["theta_dc"]), "hs_rows": hs_rows,
            "settle_periods": settle,
            "drive_periods": float(p["drive_periods"]),
            "fit_skip_periods": float(p["fit_skip_periods"]),
            "gas_config": str(cfg["inheritance"]["gas_config"])}


def _snapshot_mass_pressure(snap: dict[str, Any]) -> tuple[float, float]:
    """M_wet/A (plan section 1 half-weight rule) and pbar_wet."""

    f = np.asarray(snap["f"])
    g = np.asarray(snap["g"])
    ny, nx = f.shape[0], f.shape[1]
    # probe solver only to reach the canonical recovery operator constants
    m_wet_per_area = float(np.sum(f)) / (2.0 * nx)
    return m_wet_per_area, ny, nx, f, g


def build_pack(out_dir: Path, workers: int | None = None) -> dict[str, Any]:
    t0 = datetime.now(timezone.utc)
    log_lines: list[str] = []

    def log(msg: str) -> None:
        line = f"REFPACK {msg}"
        print(line, flush=True)
        log_lines.append(line)

    # ---- replay payloads (original config/worker, snapshot flag only) ----
    payloads = []
    protos: dict[str, dict[str, Any]] = {}
    for key, src in WET_SOURCES.items():
        proto = _proto_of(src)
        protos[key] = proto
        gas_cfg = load_config(REPO_ROOT / proto["gas_config"])
        common = dict(gas_cfg=gas_cfg, ny=2 * proto["hs_rows"],
                      nx=proto["nx"], frequency_hz=proto["frequency_Hz"],
                      samples_per_period=proto["samples_per_period"],
                      settle_periods=proto["settle_periods"],
                      snapshot=True, drive_periods=0.0, eps_ac=0.0)
        payloads.append({**common, "label": f"replay_base_{key}",
                         "kind": "base", "theta_dc": proto["theta_dc"]})
        if key == COLD_REPLAY_POINT:
            payloads.append({**common, "label": "replay_cold",
                             "kind": "base", "theta_dc": 0.0})
    n_workers = workers if workers is not None else max(1, (os.cpu_count() or 4) - 2)
    log(f"replaying {len(payloads)} wet settle cases on {n_workers} workers "
        "(original worker, snapshot=True)")
    results = execute_cases(payloads, n_workers, log, worker=_g4a_case_worker)

    pack: dict[str, Any] = {"points": {}, "provenance": {}, "sha256": {}}
    series_arrays: dict[str, np.ndarray] = {}
    fidelity: dict[str, Any] = {}

    def run_of(label: str):
        r = results.get(label)
        if not (r and r.get("ok") and r["run"].get("finite")):
            raise RuntimeError(f"replay case dead: {label}: "
                               f"{None if not r else r.get('error')}")
        return r["run"]

    # ---- cold point (Theta = 0) ----
    src0 = WET_SOURCES[COLD_REPLAY_POINT]
    cold_run = run_of("replay_cold")
    cold_arch = _read_case(REPO_ROOT / src0["results"] / "signals.h5",
                           src0["cold"])
    bp_rep = np.asarray(cold_run["base_profile"])
    bp_arch = np.asarray(cold_arch["base_profile"])
    if np.array_equal(bp_rep, bp_arch):
        fidelity["cold_base_profile"] = "bitwise"
    else:
        dev = float(np.max(np.abs(bp_rep - bp_arch)) / cold_run["theta0"])
        if dev > FP_EQUAL_REL:
            raise RuntimeError(f"cold replay base_profile deviates {dev:.3e}")
        fidelity["cold_base_profile"] = f"fp_equal({dev:.1e})"
    snap = cold_run["snapshot"]
    f0 = np.asarray(snap["f"])
    g0 = np.asarray(snap["g"])
    ny, nx = f0.shape[0], f0.shape[1]
    solver_probe = None  # canonical recovery needs only D/S/lattice
    gas_cfg0 = load_config(REPO_ROOT / protos[COLD_REPLAY_POINT]["gas_config"])
    cfg_probe = {**gas_cfg0, "numerics": {**gas_cfg0["numerics"], "nx": nx,
                                          "ny": ny}}
    solver_probe = GasSolver2D(cfg_probe)
    d_int = int(solver_probe.mapping.lattice.D)
    s_int = int(solver_probe.mapping.lattice.S)
    m0 = recover_macro(f0, g0, D=d_int, S=s_int, lattice=solver_probe.lattice)
    pack["points"]["0"] = {
        "m_wet_per_area": float(np.sum(f0)) / (2.0 * nx),
        "p_mean_wet_lu": float(np.mean(np.asarray(m0.rho)
                                       * np.asarray(m0.theta))),
        "theta_dc": 0.0, "run_id": src0["run_id"],
        "replay_label": "replay_cold",
        "source_case": src0["cold"],
    }
    log(f"cold: M/A={pack['points']['0']['m_wet_per_area']:.12f} "
        f"pbar={pack['points']['0']['p_mean_wet_lu']:.12e} "
        f"fidelity={fidelity['cold_base_profile']}")

    # cross-run cold consistency (same protocol -> bitwise expected)
    cold_x: dict[str, str] = {}
    for key, src in WET_SOURCES.items():
        arch = _read_case(REPO_ROOT / src["results"] / "signals.h5", src["cold"])
        same = np.array_equal(np.asarray(arch["base_profile"]), bp_arch)
        cold_x[key] = "bitwise" if same else "DIFFERS"
    fidelity["cold_cross_run"] = cold_x
    if any(v != "bitwise" for v in cold_x.values()):
        log(f"WARNING: cold cases differ across runs: {cold_x}")

    # ---- hot points ----
    for key, src in WET_SOURCES.items():
        proto = protos[key]
        run = run_of(f"replay_base_{key}")
        arch_base = _read_case(REPO_ROOT / src["results"] / "signals.h5",
                               src["base"])
        bp_rep = np.asarray(run["base_profile"])
        bp_arch = np.asarray(arch_base["base_profile"])
        if np.array_equal(bp_rep, bp_arch):
            fidelity[f"base_profile_{key}"] = "bitwise"
        else:
            dev = float(np.max(np.abs(bp_rep - bp_arch)) / run["theta0"])
            if dev > FP_EQUAL_REL:
                raise RuntimeError(
                    f"replay base_profile theta={key} deviates {dev:.3e}")
            fidelity[f"base_profile_{key}"] = f"fp_equal({dev:.1e})"
        snap = run["snapshot"]
        f_s = np.asarray(snap["f"])
        g_s = np.asarray(snap["g"])
        m = recover_macro(f_s, g_s, D=d_int, S=s_int,
                          lattice=solver_probe.lattice)
        m_wet = float(np.sum(f_s)) / (2.0 * f_s.shape[1])
        p_wet = float(np.mean(np.asarray(m.rho) * np.asarray(m.theta)))

        # wet fits from the ARCHIVED series (direct read; replay dev term = 0)
        h5p = REPO_ROOT / src["results"] / "signals.h5"
        cold_arch = _read_case(h5p, src["cold"])
        hot_hi = _read_case(h5p, src["hot"]["0.02"])
        hot_lo = _read_case(h5p, src["hot"]["0.005"])
        kw = dict(frequency_hz=proto["frequency_Hz"])
        rho0, cp_eff = run["rho0"], run["cp_eff"]

        def fitw(case: dict[str, np.ndarray], window) -> complex:
            d = {"t_s": case["t_s"], "theta_w": case["theta_w"],
                 "q_hot_lu": case["q_hot_lu"]}
            return fit_admittance_window(
                d, proto["frequency_Hz"], window, rho0=rho0, cp_eff=cp_eff,
                nx=proto["nx"])["Y_face_theta_units"]

        d_main = fitw(hot_hi, FIT_WINDOW_MAIN) / fitw(cold_arch, FIT_WINDOW_MAIN)
        d_alt = fitw(hot_hi, FIT_WINDOW_ALT) / fitw(cold_arch, FIT_WINDOW_ALT)
        d_lo = fitw(hot_lo, FIT_WINDOW_MAIN) / fitw(cold_arch, FIT_WINDOW_MAIN)
        d_main_pct = (abs(d_main) - 1.0) * 100.0
        u_d_wet = max(abs((abs(d_alt) - 1.0) * 100.0 - d_main_pct),
                      abs((abs(d_lo) - 1.0) * 100.0 - d_main_pct))

        # archived summary QS fields (frozen; never recomputed with new QS)
        summ = json.loads((REPO_ROOT / src["results"] / "summary.json")
                          .read_text(encoding="utf-8"))
        qs = summ["results"]["qs_chi"]
        d_arch = complex(qs["D_OP_measured"]["re"], qs["D_OP_measured"]["im"])
        d_arch_pct = (abs(d_arch) - 1.0) * 100.0
        qs1_pct = (abs(complex(qs["D_OP_QS1_pred"]["re"],
                               qs["D_OP_QS1_pred"]["im"])) - 1.0) * 100.0
        r_dyn = d_arch_pct - qs1_pct
        if abs(d_main_pct - d_arch_pct) > 1e-6:
            raise RuntimeError(
                f"theta={key}: recomputed d_OP {d_main_pct:.6f} != archived "
                f"{d_arch_pct:.6f} (fit machinery drifted)")
        if abs(d_main_pct - src["d_op_anchor_pct"]) > REPLAY_DOP_GUARD_PP:
            raise RuntimeError(
                f"theta={key}: d_OP {d_main_pct:.4f} beyond "
                f"{REPLAY_DOP_GUARD_PP} pp of STATUS anchor "
                f"{src['d_op_anchor_pct']}")
        if round(r_dyn, 2) != src["r_dyn_frozen_pp"]:
            raise RuntimeError(
                f"theta={key}: R_dyn_wet {r_dyn:.4f} rounds to "
                f"{round(r_dyn, 2)} != frozen {src['r_dyn_frozen_pp']}")

        pack["points"][key] = {
            "theta_dc": proto["theta_dc"], "run_id": src["run_id"],
            "m_wet_per_area": m_wet, "p_mean_wet_lu": p_wet,
            "d_op_pct": d_main_pct,
            "d_op_phase_deg": math.degrees(math.atan2(d_main.imag,
                                                      d_main.real)),
            "d_op_alt_pct": (abs(d_alt) - 1.0) * 100.0,
            "d_op_lo_pct": (abs(d_lo) - 1.0) * 100.0,
            "u_d_wet_pp": u_d_wet,
            "replay_dev_pp": 0.0,       # direct archived-series read
            "qs1_pct_archived": qs1_pct,
            "r_dyn_wet_pp": r_dyn,
            "D_OP_measured_archived": qs["D_OP_measured"],
            "D_OP_QS1_pred_archived": qs["D_OP_QS1_pred"],
            "source_cases": {"base": src["base"], "cold": src["cold"],
                             **{f"hot_{e}": lb for e, lb in src["hot"].items()}},
        }
        for tag, case in (("cold", cold_arch), ("hot0.005", hot_lo),
                          ("hot0.02", hot_hi)):
            for arr_k in ("t_s", "theta_w", "q_hot_lu", "q_sink_lu"):
                if arr_k in case:
                    series_arrays[f"{key}/{tag}/{arr_k}"] = case[arr_k]
        series_arrays[f"{key}/base_profile"] = bp_arch
        log(f"theta={key}: M/A={m_wet:.12f} pbar={p_wet:.12e} "
            f"d_op={d_main_pct:+.4f}% (anchor {src['d_op_anchor_pct']:+.2f}) "
            f"R_wet={r_dyn:+.4f} pp U_d_wet={u_d_wet:.4f} pp "
            f"fidelity={fidelity[f'base_profile_{key}']}")

        pack["provenance"][key] = {
            "results_dir": src["results"], "archive_dir": src["archive"],
            "proto": proto,
            "archived_provenance": json.loads(
                (REPO_ROOT / src["results"] / "provenance.json")
                .read_text(encoding="utf-8")),
        }
        for fname in ("signals.h5", "summary.json", "harmonic_fit.json",
                      "config_resolved.yaml", "provenance.json"):
            fp = REPO_ROOT / src["results"] / fname
            if fp.exists():
                pack["sha256"][f"{src['run_id']}/{fname}"] = _sha256(fp)

    pack["replay_fidelity"] = fidelity
    pack["frozen"] = {
        "replay_dop_guard_pp": REPLAY_DOP_GUARD_PP,
        "fp_equal_rel": FP_EQUAL_REL,
        "r_dyn_wet_frozen_pp": {k: s["r_dyn_frozen_pp"]
                                for k, s in WET_SOURCES.items()},
        "d_op_anchors_pct": {k: s["d_op_anchor_pct"]
                             for k, s in WET_SOURCES.items()},
        "fit_window_main": FIT_WINDOW_MAIN, "fit_window_alt": FIT_WINDOW_ALT,
    }
    pack["built_utc"] = t0.isoformat()
    pack["machine"] = os.environ.get("COMPUTERNAME", "unknown")
    pack["builder_argv"] = sys.argv
    try:
        import subprocess
        pack["code_commit"] = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT,
            capture_output=True, text=True, timeout=10,
            check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        pack["code_commit"] = "unknown"

    # ---- write pack (npz first so its digest lands inside the json) ----
    out_dir.mkdir(parents=True, exist_ok=True)
    npz_path = out_dir / "wet_reference_pack_series.npz"
    tmp = npz_path.with_suffix(".tmp.npz")
    np.savez_compressed(tmp, **series_arrays)
    os.replace(tmp, npz_path)
    pack["series_npz"] = npz_path.name
    pack["sha256"]["series_npz"] = _sha256(npz_path)
    json_path = out_dir / "wet_reference_pack.json"
    json_path.write_text(json.dumps(pack, indent=1, default=float),
                         encoding="utf-8")
    (out_dir / "wet_reference_pack.sha256").write_text(
        _sha256(json_path) + "  wet_reference_pack.json\n", encoding="utf-8")
    (out_dir / "build_log.md").write_text(
        "\n".join(["# wet_reference_pack build log", "", "```text"]
                  + log_lines + ["```", ""]), encoding="utf-8")
    log(f"pack -> {json_path}")
    log(f"wall {((datetime.now(timezone.utc) - t0).total_seconds() / 60.0):.1f} min")
    return pack


def main() -> int:
    ap = argparse.ArgumentParser(description="A2a-STRICT_B wet reference pack")
    ap.add_argument("--out-dir",
                    default=str(REPO_ROOT / "archive" / "a2a_strict_b"))
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()
    build_pack(Path(args.out_dir), workers=args.workers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
