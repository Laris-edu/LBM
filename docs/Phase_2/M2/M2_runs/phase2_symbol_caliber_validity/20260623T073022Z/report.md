# Phase 2 One-Step Symbol Caliber Validity (§5.5 item 1: symbol vs dynamic Prony)

- run_id: `20260623T073022Z`  chi*: `1.105`
- summary_digest: `51aa8970632b5077be04fec0ed408014c6ff0735cf15b2779eb498fa8fb28819`

## Symbol eigenvalue vs dynamic Prony (chi*)

| dir | symbol eigen | Prony[240] | Prony[480] | Prony[720] | symbol-dynamic | #acoustic eig in band |
|---|---|---|---|---|---|---|
| x | 1 | 1 | 1 | 1 | 2.527e-05 | 2 |
| diagonal | 1.265 | 1.308 | 1.308 | 1.307 | -0.04207 | 2 |

## Root cause: periodic FFT corrections (diagonal)

- corrections ON : symbol 1.265, dynamic 1.307, gap 0.04207
- corrections OFF: symbol 1.876, dynamic 1.876, gap 2.76e-05

## Interpretation

- **x_exact**: x/y: one-step symbol eigenvalue == dynamic Prony exactly (1.000), window-independent.
- **diagonal_gap**: diagonal: symbol 1.2652 vs dynamic Prony 1.3073; Prony is window-independent (240/480/720 agree) so NOT a fit artifact, and only two acoustic eigenvalues sit in the band (no 1.307 eigenvalue) so NOT a selection error -- the single-mode one-step operator genuinely differs from the multi-step dynamic for diagonal.
- **root_cause**: The periodic FFT corrections drive the gap: corrections ON gap 0.0421, corrections OFF gap 0.0000 (EXACT agreement OFF). The single-mode one-step symbol does not faithfully represent the multi-step action of the global dispersion/acoustic-phase FFT corrections on the diagonal mode; x/y are unaffected.
- **conclusion**: Dynamic Prony is AUTHORITATIVE (real multi-step evolution; what production P2-6 reports). The one-step symbol caliber is exact for x/y but ~3% low for diagonal -- use the dynamic value (~1.31) for the diagonal acoustic residual. bounded-production-GO is unchanged: 1.27 vs 1.31 are both bounded ~1.3 and physically negligible under acoustic compactness (kL~0.04).
