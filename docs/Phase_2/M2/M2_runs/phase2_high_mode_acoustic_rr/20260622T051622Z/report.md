# Phase 2 D2Q37 High-Mode Acoustic Over-Damping under RR (residual #3)

- run_id: `20260622T051622Z`
- status: `DIAGNOSTIC_COMPLETE`
- chi*: `1.105`
- summary_digest: `337bd893f58f84fe83ff9759847c0dcffe23641538d0b0d24d1e7604f2fd5ac4`

## Acoustic damping ratio sigma/(coeff*k^2) -- eigenvalue caliber (window-free)

| dir | mode | baseline (current_zero) | RR (chi*) | speed_err (RR) |
|---|---|---|---|---|
| axis | 1 | 5.971 | 1 | 0.005389 |
| axis | 2 | 7.914 | 5.368 | 0.04628 |
| axis | 3 | 9.647 | 12.27 | 0.1113 |
| diagonal | 1 | 6.996 | 1.265 | 0.001207 |
| diagonal | 2 | 10.87 | 6.911 | 0.09299 |
| diagonal | 3 | none | none | none |

## Filter contribution (RR axis, ratio[filter on] - ratio[filter off])

- mode1=0.02714, mode2=0.108, mode3=0.241  (small vs the 4-11 dispersion excess -> over-damping is dispersion, not the filter)

## k^2 hyperviscous fit (RR axis): `ratio = 1 + beta*((k/k1)^2 - 1)`  beta=`1.415` (residual `0.07549`)

## Interpretation

- **rr_vs_baseline**: RR fixes the LOW mode only (mode1 axis ~6 -> 1.000, diagonal ~7 -> 1.265). At high mode RR does NOT fix the over-damping and its effect is mode-dependent: vs baseline it is better at mode2 (axis 7.9->5.4, diag 10.9->6.9) but worse at mode3 axis (9.6->12.3). The high-mode over-damping (5-12x) persists for both -> it is a separate axis the RR low-mode calibration does not address.
- **filter_vs_dispersion**: The high-wavenumber filter contributes only ~0.03/0.11/0.24 to the mode1/2/3 ratio (its per-step damping ~strength*k^4 divided by the equally small NSF reference coeff*k^2); this is small vs the 4-11 dispersion excess, so the high-mode over-damping is closure/lattice DISPERSION, not the filter.
- **k_scaling**: RR axis excess(ratio-1) ~ 1.415*((k/k1)^2 - 1) (residual 0.075): the extra acoustic damping is hyperviscous (~k^4 in sigma) and grows with wavenumber.
- **speed_correction**: At high mode the phase speed is also off (RR speed_err ~4.6% mode2, ~11% mode3 axis) with the default acoustic_phase_high_mode_factor=1.0. The project's high-mode phase corrections target SPEED/gamma, not attenuation, so even with the speed seed the attenuation stays over-damped.
- **physical_relevance**: The 10 kHz thin-film target is acoustically compact (lambda ~ 8675 cells >> film ~ tens of cells), operating in the k->0 limit; high-mode acoustic resonances do not occur in the gas film, so the high-mode over-damping is physically irrelevant for p_hat -- the same compactness argument as decision A, extended to high modes.
- **boundaries**: Diagnostic only; baseline unchanged. High-mode acoustic over-damping is a real, RR-independent, dispersion-driven axis; like the diagonal residual it is a bounded GO-RISK boundary, physically irrelevant for the compact 10 kHz target. A production high-mode acoustic-attenuation fix (if ever needed) would require a wavenumber-dependent (spectral/dispersion) mechanism, not a local closure.
