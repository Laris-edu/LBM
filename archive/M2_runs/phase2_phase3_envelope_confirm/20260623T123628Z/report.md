# Phase_3 Level C Precondition: Compact-Air Envelope Confirmation

- run_id: `20260623T123628Z`
- within accepted envelope: **no**
- summary_digest: `86d379cc93d168da23a369986446ba3b5863d4876c2496ba71bd298dd2fe6efe`

- config dx = 4.00 um, dt = 3.00 ns, target f = 10000 Hz
- scales: acoustic lambda 8675 cells, delta_T 6.651 cells, delta_nu 5.589 cells

## Envelope axes

| axis | operating | envelope | within |
|---|---|---|---|
| Mach | small-signal film acoustics (P2-6 amplitude Mach ~1e-6; driven 10 kHz film Mach << 1e-3) | <= 0.05 | yes |
| Pr | 0.7061 | <= 1 | yes |
| acoustic k | 0.0007243 (compact) | ~0.098 | yes |
| thermal k (axis) | 0.1504 (1.532x cal) | ~0.098 | no |
| viscous k (axis) | 0.1789 (1.823x cal) | ~0.098 | no |

## Binding axis: near-wall boundary-layer resolution (viscous worst)
- thermal BL: delta_T ~ 6.651 cells, k 0.1504 (1.532x cal); axis alpha err mode1 0.001781 .. mode2 0.06993 (~few-%, acceptable-ish)
- **viscous BL (binding)**: delta_nu ~ 5.589 cells, k 0.1789 (1.823x cal); axis nu err mode1 2.139e-05 .. mode2 1.94 (RR shear regression -> badly off)
- to put both BLs on calibration k: dx ~ 2.61 um (delta_T/delta_nu ~ 10 cells each)

## Interpretation

- **verdict**: Mach (<<0.05) and Pr (0.706<=1) are well inside the envelope. Acoustic is compact (lambda~8675 cells, kL~0.039<<1) so the diagonal/high-mode attenuation GO-RISK is physically negligible. The wall-normal thermal BL is an axis direction so its alpha err at k_thermal=0.150 is only ~few-% (mode1 0.00178 .. mode2 0.0699). BINDING axis = the VISCOUS (Stokes) boundary layer: delta_nu~5.6 cells -> k_viscous=0.179 (1.82x cal), and RR regressed the SHEAR dispersion so axis nu err runs mode1 2.14e-05 -> mode2 1.94: nu at the viscous-BL scale is badly off at the config dx=4.0 um.
- **recommendation**: For Level C, resolve BOTH boundary layers onto the calibration k: use dx ~ 2.61 um (delta_T/delta_nu ~ 10 cells each) so thermal AND viscous features sit at k≈0.098 where RR nu/alpha are validated (~0.2-2%); OR re-tune the RR shear dispersion targets for the strain_rate_isotropic policy (recovers high-k nu). Mach/Pr/acoustic axes need no change. If the Phase_3 quantities of interest are dominated by the full-gas-region scale (~64 cells, k≈0.098) rather than the near-wall boundary layers, the config dx may already suffice -- confirm which scale drives T_s_hat / q_g / p_hat.
- **boundaries**: Diagnostic; baseline unchanged. This is the Level C precondition (M2_Critical_Decision §5.5 item 2): confirm the Phase_3 sim's operating point sits in the accepted compact-air envelope before Level C.
