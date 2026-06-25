# Phase_3 Level C Triage: which scale/transport drives each QoI

- run_id: `20260623T164538Z`
- binding near-wall layer for QoI: **THERMAL (alpha), not VISCOUS (nu)**
- viscous (Stokes) layer irrelevant to all QoI: **yes**
- config dx sufficient for ALL QoI: **no**
- summary_digest: `6b4543767d29a014b614defe47f37d9318b688531ac52fcc0984f7067f6c283e`

- scales @config dx: delta_T 6.651 cells (k_thermal 0.1504 = 1.532x cal), delta_nu 5.589 cells, acoustic lambda 8675 cells

## 1. Per-QoI scale/transport decomposition (Level C closed form)

| QoI | dominant scale | transport | d ln|QoI|/d ln(alpha) | d ln|QoI|/d ln(nu) | viscous Stokes? |
|---|---|---|---|---|---|
| q_g (wall heat flux) | energy-conservation-pinned (q_g ~ P_hat/2), integral | alpha (axis), but immune (energy-pinned) | -0.00556 | 0 | no |
| T_s_hat (film temp) | near-wall THERMAL layer delta_T (gas-thermal-admittance dominated) | alpha (wall-normal axis); NOT nu | 0.4944 | 0 | no |
| p_hat (probe) | near-wall THERMAL source delta_T + acoustically COMPACT radiation (kL~0.04) | alpha (thermal source, sensitivity ~1); nu only via negligible longitudinal attenuation | 0.9944 | 0 | no |

- gas-load / film-inertia in T_s denominator = **63.58x** (T_s set by gas thermal admittance, not film heat capacity)
- q_g / (P_hat/2) = **0.9889** (q_g is energy-conservation-pinned)

## 2. Near-wall transport fidelity (Prony one-step eigenvalue caliber)

### 2a. fixed grid 64, k-specificity (alpha ratio, Fourier-q err, nu err; x/y/diagonal)

| mode | dir | k_lu | alpha_ratio(prony) | Fourier-q_err | nu_err |
|---|---|---|---|---|---|
| 1 | x | 0.09817 | 1.025 | 0.0009633 | 2.139e-05 |
| 1 | y | 0.09817 | 1.025 | 0.0009633 | 2.139e-05 |
| 1 | diagonal | 0.1388 | 1.025 | 0.00194 | 0.001758 |
| 2 | x | 0.1963 | 0.945 | 0.006114 | 1.94 |
| 2 | y | 0.1963 | 0.945 | 0.006114 | 1.94 |
| 2 | diagonal | 0.2777 | 0.2691 | 0.8085 | 0.4352 |
| 3 | x | 0.2945 | 0.1141 | 1.114 | 5.087 |
| 3 | y | 0.2945 | 0.1141 | 1.114 | 5.087 |
| 3 | diagonal | 0.4165 | 1.011 | 2.884 | 1.18 |

### 2b. feature wavenumber on the wall-normal (y) axis, per dx

| dx (um) | delta_T cells | k_thermal (xcal) | alpha_ratio(prony) | alpha_ratio(log) | thermal clean? | delta_nu cells | k_viscous (xcal) | nu_err |
|---|---|---|---|---|---|---|---|---|
| 4 | 6.651 | 0.1504 (1.532x) | -0.3689 | -0.3724 | no | 5.589 | 0.1789 (1.823x) | 1.498 |
| 2.6 | 10.23 | 0.09773 (0.9955x) | 1.015 | 1.008 | yes | 8.598 | 0.1163 (1.185x) | 0.247 |
| 1.8 | 14.78 | 0.06766 (0.6892x) | 1.662 | 1.648 | no | 12.42 | 0.08052 (0.8202x) | 0.1997 |

- Prony == log at every k -> the strong off-calibration k-specificity is real (closure), not a fit artifact.
- Only dx where k_thermal hits the calibration k (~0.098) is thermal clean; config dx (k~0.15) is off-calibration.

### 2c. correction toggle at the config-dx thermal feature k = 0.1496 (alpha ratio, axis y, Prony)

- RR default: -0.3689 | corrections OFF: -0.5066 | filter OFF: -0.4037
- off-calibration behaviour intrinsic to the BASE RR closure (not the spectral corrections): **yes** (so re-tuning the dispersion/phase corrections alone will not clean the thermal feature; the lever is dx/resolution or a deeper thermal-closure re-tune)

## 3. Acoustic viscous-loss order of magnitude in p_hat

- kL at probe = 0.03854 (<<1, compact)
- longitudinal attenuation over probe = 2.999e-07 (2x RR nu: 5.998e-07)
- shear Stokes layer excited: no -- Wall-normal (y) acoustic propagation off a planar film -> acoustic particle velocity is normal to the wall, so NO tangential velocity at the wall and the viscous SHEAR Stokes layer (delta_nu) is geometrically not excited in the leading-order p_hat. The only viscous channel is longitudinal attenuation, ~3.00e-07 over the compact probe (~6.00e-07 even at 2x RR nu): negligible vs |p_hat|~0.4. The Phase_1 pressure reference is itself inviscid.

## 4. Verdict

**The near-wall layer the QoI care about is the THERMAL one (alpha, wall-normal axis), NOT the viscous (Stokes) layer the envelope flagged: q_g/T_s_hat/p_hat have ZERO nu sensitivity and the shear Stokes layer is geometrically not excited (normal propagation). So the RR shear-dispersion regression (option 2) is IRRELEVANT to every QoI. q_g is energy-conservation-pinned (q_g~P/2, alpha-sensitivity ~0.006) -> config dx sufficient. T_s_hat (alpha-sensitivity ~0.5) and p_hat (~1.0) ride the near-wall THERMAL admittance; the RR thermal alpha is clean only near the calibration k~0.098 and is wild off-calibration (intrinsic to the base closure, not the spectral corrections), and the config-dx thermal feature k~0.15 is off-calibration -> config dx is NOT certified for T_s_hat/p_hat. Relevant lever = THERMAL resolution (dx so k_thermal -> calibration k, i.e. dx~2.6um where the feature is verified clean; or re-tune the RR THERMAL dispersion), NOT the shear/nu re-tune. Definitive QoI-level check if config dx is kept: a driven 10 kHz near-wall thermal-layer sim.**

| QoI | viscous-Stokes dep | near-wall-thermal dep | config dx sufficient | relevant lever |
|---|---|---|---|---|
| q_g (wall heat flux) | no | no | yes | none (config dx sufficient) |
| T_s_hat (film temp) | no | yes | no | thermal resolution: dx so k_thermal -> calibration k (option 1); NOT shear/nu re-tune (option 2) |
| p_hat (probe) | no | yes | no | thermal resolution: dx so k_thermal -> calibration k (option 1); NOT shear/nu re-tune (option 2) |

Diagnostic; baseline, gates and closure unchanged.
