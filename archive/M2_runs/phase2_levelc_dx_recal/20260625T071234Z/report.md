# Phase_3 Level C: move operating point onto the calibration k (option a)

- run_id: `20260625T071234Z`
- T_s_hat / p_hat certified at the Level C config: **yes**
- Level C config: `configs\gas_air_10k_d2q37_levelc_dx2p6.yaml` (sha256 `849699bb37f6416d...`)
- summary_digest: `d4968c1a9824972815fbf671986da39473a7a886f62cc6c9046a08611fbe4989`

- operating point: 10 kHz, delta_T 26.603 um -> dx 2.6117 um, dt 1.9588 ns, k_thermal/cal = 1
- heat-flux moment factor: prod 0.0422 -> Level C 0.06354
- tau: production tau21 0.5608 -> Level C 0.5932; nu_lu 0.002944 -> 0.004508

## Gates across the dx move

| gate | new dx + OLD coeffs | Level C (re-tuned) |
|---|---|---|
| P2-5 alpha axis | 0.004479 | 0.004476 |
| P2-5 Fourier-q axis | 0.3359 | **7.481e-05** |
| P2-6 acoustic | PASSED (c 0.007458) | PASSED (c 0.007458) |
| P2-4 shear nu axis (QoI-irrelevant) | 0.3377 | 0.3377 |
| P2-5 alpha diagonal (QoI-irrelevant) | 0.149 | 0.149 |

## Verdict

**Option (a) executed. Refining dx to 2.6118 um lands the 10 kHz thermal feature on the calibration k and the alpha-DECAY is already clean (axis 0.45%), but the production RR coefficients are tau-specific so at the new tau the shear nu and the Fourier-q EXPORT both regress ~34%. Re-tuning ONLY the conductive heat-flux export factor (x1.506, linear, QoI-relevant; the shear factor is nonlinear and QoI-irrelevant) restores axis Fourier-q to 0.0072% with axis alpha 0.45% and acoustic passing -> the near-wall THERMAL admittance is certified, so T_s_hat / p_hat are accurate at configs/gas_air_10k_d2q37_levelc_dx2p6.yaml. Residual shear nu ~34% and diagonal alpha ~15% are QoI-irrelevant (and not re-derived). q_g is energy-pinned. The default production baseline is unchanged.**

Diagnostic; baseline, gates and the default closure unchanged.
