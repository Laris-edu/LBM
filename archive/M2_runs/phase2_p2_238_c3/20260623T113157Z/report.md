# Phase 2 P2-2 / P2-3 / P2-8 C1 -> C3 Diagnostic (RR default)

- run_id: `20260623T113157Z`
- all C3 pass (compact-air envelope): **no**
- summary_digest: `7ec4408578871eac961b2f87fa9cced44d50e92198f850ef58ece4b5d47f682f`

## P2-2 admissibility + perturbation stability
- f_eq admissible: no (min f_eq -0.03983, min g_eq -0.002414)
- perturbation stable: yes (decay ratio 0.8743, min theta 0.04837, invalid step none)
- **P2-2 C3: no**

## P2-3 long-time uniform stability + invariants
| run | steps | mass drift | momentum drift | energy drift | theta excursion | stable |
|---|---|---|---|---|---|---|
| rest (M0) | 2000 | 8.882e-16 | 2.956e-12 | 1.776e-15 | 5.065e-16 | yes |
| background (M0.05) | 2000 | 8.882e-16 | 1.87e-11 | 1.776e-15 | 6.453e-16 | yes |
- **P2-3 C3: yes**

## P2-8 directional error statistics (mode 1, x/y/diagonal)
- directional spread: nu 0.001778, alpha 0.01958, c 0.004072, gamma 0.008138
- max directional spread: 0.01958
- **P2-8 C3: yes**

## Interpretation

- **p2_2**: f_eq admissible (min -3.983e-02 >= 0) across the envelope; a real multi-mode perturbation is stable (decay ratio 0.8743, no NaN/negative theta).
- **p2_3**: Uniform rest/background states stable over 2000 steps; invariant drift (mass 8.88e-16, energy 1.78e-15) and fixed-point excursion (theta 6.45e-16) are at/near machine precision.
- **p2_8**: Directional (x/y/diagonal) isotropy at mode 1: max spread 0.01958 (nu/alpha/c/gamma), within 5%.
- **boundaries**: Diagnostic; baseline unchanged. C3 evidence within the accepted compact-air mode1/low-k envelope (M2_Critical_Decision §5). High-k / other-resolution behaviour is the documented GO-RISK boundary.
