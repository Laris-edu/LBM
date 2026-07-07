"""D1 verdict probe: can the global dispersion correction be LOCALIZED to a compact stencil?

Route-b' follow-on (2026-07-05). The P4-1 volume-injection floor is fed by the global
periodic FFT dispersion correction acting on boundary seams. D1 asks whether that
correction can be replaced by a compact real-space stencil (which would be single-side-able
at a boundary, killing the injection). Two knives, both cheap:

1. ABLATION -- run the P2-4/5/6 transport gates on the frozen D2Q37 baseline with the
   dispersion correction ON (frozen) vs OFF, to see WHICH gates it actually guards.
   Result (2026-07-05): P2-6 sound speed 0.49%->0.55% (unaffected), P2-4 shear
   0.18%->3.72% (still in gate), P2-5 thermal alpha 2.1%->104% and heat flux 0.19%->61%
   (BOTH break the 5% gate). The correction is THERMAL-transport-only and mandatory there.

2. K-SPACE FIT -- the dispersion multiplier is a near-step high-k plateau low-pass:
   multiplier(mu)=1 for mu<low, =target(0.32) for mu>=high, over a 0.019-wide transition
   (mu = 4sin^2(ky/2)+4sin^2(kx/2), the discrete-Laplacian symbol). A radius-n stencil has
   k-response = degree-n polynomial in mu, which CANNOT represent a high-k constant plateau
   (polynomials diverge at large mu). Measured: degree-8 (radius-8 stencil) still leaves 50%
   residual for the conductive target -- far outside the 5% gate.

VERDICT: FIR local stencil replacement is refuted in principle (near-step plateau is not a
low-degree polynomial) while the correction is mandatory for the thermal gates. Boundary-only
localization = route b' (four designs refuted, constraint pair). The only unrefuted D1
variant is an implicit/IIR local operator -- no longer a cheap verdict, a D3/D2-scale
investment. See docs/Phase_4/M4/P4_1b_Seam_Detrend_Project.md section 8.

Diagnostic only: no gate is claimed; the ablation toggles are probe-local (frozen config
untouched)."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

import numpy as np

from scripts.phase2_m2_verification import load_config
from verification.acoustic_wave_measurement import measure_acoustic_wave
from verification.shear_wave_measurement import measure_shear_wave
from verification.thermal_diffusion_measurement import measure_thermal_diffusion

DEFAULT_BASELINE = Path("configs/gas_air_10k_d2q37_physical_timestep.yaml")


def run_ablation(baseline: Path) -> dict[str, Any]:
    """Dispersion ON vs OFF across the P2 transport gates (which gates does it guard?)."""

    cfg_on = load_config(baseline)
    cfg_off = copy.deepcopy(cfg_on)
    cfg_off["collision"]["dispersion_correction_enabled"] = False
    out: dict[str, Any] = {"baseline": str(baseline), "gates": {}}
    specs = [
        ("P2-6_sound_speed", measure_acoustic_wave, "sound_speed_relative_error", 0.02),
        ("P2-4_shear_nu", measure_shear_wave, "relative_error", 0.05),
        ("P2-5_alpha", measure_thermal_diffusion, "relative_error", 0.05),
        ("P2-5_heat_flux", measure_thermal_diffusion, "heat_flux_relative_error", 0.05),
    ]
    cache: dict[int, tuple] = {}
    for name, fn, key, gate in specs:
        if fn not in cache:
            cache[fn] = (fn(cfg_on), fn(cfg_off))
        on, off = cache[fn]
        out["gates"][name] = {
            "on": float(on[key]), "off": float(off[key]), "gate": gate,
            "off_breaks_gate": bool(abs(off[key]) > gate),
        }
    return out


def run_kspace_fit(baseline: Path) -> dict[str, Any]:
    """Degree-n polynomial (=radius-n stencil) fit residual for the dispersion multiplier."""

    coll = load_config(baseline)["collision"]
    low = float(coll["dispersion_correction_low_laplacian"])
    high = float(coll["dispersion_correction_high_laplacian"])
    targets = {
        "shear_xy": float(coll.get("regularized_shear_xy_dispersion_target", 1.0)),
        "heat_flux": float(coll.get("regularized_heat_flux_dispersion_target", 1.0)),
        "conductive": float(coll.get("conductive_heat_flux_dispersion_target", 1.0)),
    }

    def multiplier(mu, target):
        ramp = np.clip((mu - low) / (high - low), 0.0, 1.0)
        return 1.0 + (target - 1.0) * ramp * ramp * (3.0 - 2.0 * ramp)

    mu = np.linspace(0.0, 8.0, 2001)
    fits: dict[str, Any] = {}
    for tname, tgt in targets.items():
        if tgt == 1.0:
            continue
        m = multiplier(mu, tgt)
        fits[tname] = {
            f"deg{n}": float(np.max(np.abs(np.polyval(np.polyfit(mu, m, n), mu) - m)))
            for n in (1, 2, 4, 8)
        }
    return {"low_laplacian": low, "high_laplacian": high, "targets": targets, "fit_residual": fits}


def main() -> None:
    parser = argparse.ArgumentParser(description="D1 dispersion-localization verdict probe (diagnostic).")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    ablation = run_ablation(args.baseline)
    kspace = run_kspace_fit(args.baseline)

    print("== D1 knife 1: dispersion ablation (which P2 gates does it guard?) ==")
    for name, g in ablation["gates"].items():
        flag = "  <-- OFF BREAKS GATE" if g["off_breaks_gate"] else ""
        print(f"  {name:18s}: ON={g['on']:+.4e}  OFF={g['off']:+.4e}  (gate {g['gate']}){flag}")
    print("\n== D1 knife 2: multiplier polynomial (=stencil) fit residual ==")
    for tname, res in kspace["fit_residual"].items():
        print(f"  {tname:12s} (target {kspace['targets'][tname]:.3f}):  "
              + "  ".join(f"{k}:{v:.3f}" for k, v in res.items()))
    print("\nVERDICT: FIR local stencil refuted (near-step plateau, deg-8 residual ~50%) while "
          "the correction is mandatory for the thermal gates (P2-5 off -> 104%/61%).")

    if args.out:
        args.out.write_text(json.dumps({"ablation": ablation, "kspace": kspace}, indent=2), encoding="utf-8")
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
