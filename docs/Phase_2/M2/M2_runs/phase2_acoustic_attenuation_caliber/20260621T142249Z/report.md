# Phase 2 D2Q37 Acoustic-Attenuation Caliber + Diagonal Over-Constraint Diagnostic

- run_id: `20260621T142249Z`
- status: `DIAGNOSTIC_COMPLETE`
- closure: strain_rate_isotropic deviatoric + ghost_orthogonal_local (div) trace + diagnostic_zero bulk
- summary_digest: `3c7d47a6e4090d79016b8638395ed73a9a8c40384b385eb605d7c784131287a8`

## F1 -- measurement caliber (window-free eigenvalue vs dynamic fits)

| dir | eigen acoustic ratio (fwd) | Prony ratio | log|p'| 240 | log|p'| 480 | log|p'| 720 | shear nu_r | entropy alpha_r |
|---|---|---|---|---|---|---|---|
| x | 1.104 | 1.104 | 1.003 | 1.067 | 1.083 | 1 | 1.01 |
| diagonal | 1.41 | 1.411 | 1.233 | 1.437 | 1.458 | 1.002 | 1.019 |
| y | 1.104 | (=x) | - | - | - | 1 | 1.01 |

Eigenvalue == Prony; log|p'| is biased low at 240 and drifts up toward the eigenvalue. Shear/entropy are single real eigenvalues (no beating) -> clean.

## chi recalibration against the eigenvalue

- published chi = `1.085` -> eigen acoustic x ratio `1.104`
- eigen-recalibrated chi* = `1.105`
- at chi*: acoustic_fwd ratio x=1, y=1, diagonal=1.265
- at chi*: acoustic_bwd ratio x=1, y=1, diagonal=1.277
- at chi*: shear nu_ratio x=1, y=1, diagonal=1.002

## T1 -- D4 over-constraint sensitivity matrix  d(quantity)/d(knob)

| quantity \ knob | xy_factor (B2) | normal_factor (B1) | chi (bulk) |
|---|---|---|---|
| nu_T_axis | -16.37 | 4.862e-05 | 4.593e-05 |
| nu_T_diag | -0.0002723 | -8.162 | 0.0001112 |
| nu_L_axis | 0.0001691 | -5.215 | -5.214 |
| nu_L_diag | -10.45 | 1.267 | -5.133 |

- base quantities (published knobs): nu_T_axis=1, nu_T_diag=1.002, nu_L_axis=1.104, nu_L_diag=1.41
- d(nu_L,diag - nu_L,axis)/d(chi) = `0.08091` (≈0 -> chi cannot fix the diagonal excess)

## Interpretation

- **F1_caliber**: The exact one-step modal eigenvalue sigma=-log|lambda| is the window-free, fit-free, admixture-free acoustic damping; it equals the dynamic Prony fit. The production log|p'| decay fit is biased low at short windows by a weak forward/backward beating ripple (the init is not the exact discrete eigenmode) and drifts with the window. At the published knobs the true x/y acoustic ratio is ~1.10, not the 240-window ~1.00; recalibrating chi against the eigenvalue drives x/y to ratio = 1 EXACTLY.
- **T1_overconstraint**: On a square (D4) lattice the most general local linear viscous closure has exactly three coefficients: bulk (chi) and two shear moduli for irreps B1 (xx-yy = normal_factor) and B2 (xy = xy_factor). nu_T(axis)<-B2, nu_T(diag)<-B1, nu_L(axis)<-B1+chi, nu_L(diag)<-B2+chi. Pinning B2 (axis shear), B1 (diag shear) and chi (axis longitudinal) leaves nu_L(diag) DETERMINED: the diagonal residual is irreducible for any D4-covariant local linear closure. The sensitivity matrix confirms the couplings and d(nu_L,diag - nu_L,axis)/d(chi) ~ 0.
- **boundaries**: Diagnostic only; baseline unchanged. Any 4th degree of freedom able to close the diagonal residual must be non-local (Riesz / longitudinal projector), nonlinear, or memory-based. The production P2-6 log|p'| measurement is left unchanged; the eigenvalue/Prony caliber is the recommended diagnostic ground-truth.
