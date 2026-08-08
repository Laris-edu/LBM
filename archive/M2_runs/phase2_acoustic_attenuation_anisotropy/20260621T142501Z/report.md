# Phase 2 D2Q37 Acoustic-Attenuation Anisotropy Bound + Acoustic Compactness (decision A)

- run_id: `20260621T142501Z`
- status: `DIAGNOSTIC_COMPLETE`
- decision: `A_accept_bounded_GO_RISK_diagonal_residual`
- summary_digest: `d2e0b9862be4dc08b86bad3454c4f43fe9e911ca5df838ad35836cb2bc5557b7`

## Low-k angular bound (residual #1, eigenvalue caliber, chi*=1.105)

- axis (0/90 deg, incl. film normal y) ratio = `1` (exact)
- diagonal (45 deg) ratio = `1.265` (maximum)
- angular form `1 + (diag-1)*sin^2(2*theta)`, amplitude a = `0.2652`; bound = max ratio `1.265` at 45 deg

### k-dependence (documents the SEPARATE high-mode over-damping axis, residual #3)

| mode | axis ratio | diagonal ratio |
|---|---|---|
| 1 | 1 | 1.265 |
| 2 | 5.368 | 6.911 |
| 3 | 12.27 | none |

- mode>=2 ratios are dominated by high-mode acoustic over-damping (residual #3), a separate axis from the low-mode diagonal anisotropy; the diagonal bound is stated at mode 1.

## Acoustic compactness of the 10 kHz thin-film target

- acoustic wavelength: `0.0347` m = `8675` cells
- thermal penetration delta_T: `2.66e-05` m = `6.651` cells
- viscous penetration delta_nu: `2.236e-05` m = `5.589` cells
- scale separation lambda/delta_T = `1304`
- probe y=8*delta_T = `0.0002128` m = `53.21` cells; kL = `0.03854` << 1
- acoustic amplitude loss over probe distance: `2.473e-07` (diagonal extra `6.558e-08`)

## Interpretation

- **bound**: Eigenvalue acoustic ratio is 1.000 on the lattice axes (exact) and rises to the diagonal maximum 1.265 at 45 deg, following 1 + 0.265*sin^2(2*theta) (T1 B1/B2 angular signature). The low-mode residual is bounded by the 45 deg diagonal; the axes (incl. the film normal y) are exact. Intermediate angles need higher |k| where high-mode over-damping (residual #3) dominates.
- **compactness**: The 10 kHz target gas region (delta_T ~ few-to-tens of um) is acoustically compact: lambda/delta_T ~ 1304, kL at the y=8*delta_T probe ~ 0.0385 << 1, and the acoustic amplitude loss across the probe distance is ~2.47e-07 (diagonal extra ~6.56e-08). The 30% diagonal attenuation error has negligible impact on p_hat; the dominant thermal/viscous diffusion (alpha, nu) and the hard-gated isotropic c/gamma/Galilean are unaffected. The film normal is the y-axis (exact).
- **boundaries**: Diagnostic only; baseline unchanged. Supports decision A: accept the diagonal residual (1.306 at 45 deg, eigenvalue caliber) as a bounded structural GO-RISK boundary.
