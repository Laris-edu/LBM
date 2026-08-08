# Phase 2 D2Q37 Physical Bulk Viscosity Diagnostic

- run_id: `20260619T095054Z`
- status: `DIAGNOSTIC_COMPLETE`
- config: `configs\gas_air_10k_d2q37_physical_timestep.yaml`
- summary_digest: `6f2297ef8b5255631bd02985414ab7e25227e28200c1e2374d4bfd9263380a14`
- effective_bulk_viscosity_slope (measured/nominal): `1.437`

## Stage A: attenuation + stability sweep (P2-6, direction x)

| variant | tau22 | trace_factor | measured | target | ratio | c_err | g_err | invalid | neg_theta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `current_zero` | 0.5 | 0 | 0.0001393 | 2.222e-05 | 6.27 | 0.00475 | 0.009523 | none | False |
| `tau22_nu_b=0.0nu` | 0.5 | -1 | 3.91e-05 | 2.222e-05 | 1.759 | 0.004791 | 0.009605 | none | False |
| `tau22_nu_b=0.3nu` | 0.5304 | -0.8853 | 4.522e-05 | 2.648e-05 | 1.708 | 0.004786 | 0.009596 | none | False |
| `tau22_nu_b=0.6nu` | 0.5608 | -0.783 | 5.133e-05 | 3.073e-05 | 1.67 | 0.004782 | 0.009587 | none | False |
| `tau22_nu_b=1.0nu` | 0.6014 | -0.6627 | 5.948e-05 | 3.641e-05 | 1.634 | 0.004777 | 0.009577 | none | False |

## Stage B: thermal ghost control (P2-5, x/y/diagonal)

| variant | trace_factor | P2-5 | alpha_err | heat_flux_err | any_invalid_step |
|---|---:|---|---:|---:|---|
| `current_zero` | 0 | `PASSED` | 0.004968 | 0.0003368 | False |
| `tau22_nu_b=0_marginal` | -1 | `FAILED` | 11.81 | 0.2152 | False |
| `tau22_nu_b=0.6nu` | -0.783 | `PASSED` | 0.0101 | 0.001283 | False |

## Stage B2: physical nu_b=0.6*nu full gate (existing heat curve)

- P2-5 thermal: `PASSED`  alpha_err=`0.0101`  heat_flux_err=`0.001283`
- P2-6 acoustic: `PASSED`  c_err=`0.004782`  g_err=`0.009587`  attenuation_ratio=`1.67`  direction_difference=`0.004406`
- P2-7 Pr scan: `PASSED`  baseline_pr_err=`0.00611`  max_pr_err=`0.04935`

## Stage C: normal_factor scan at physical nu_b (P2-6 x, P2-4 x/y/diagonal)

| normal_factor | P2-6 | attenuation_ratio | c_err | P2-4 | shear_x | shear_y | shear_diagonal |
|---:|---|---:|---:|---|---:|---:|---:|
| 0.7 | `PASSED` | 2.285 | 0.004765 | `FAILED` | 0.005291 | 0.005291 | 1.044 |
| 0.9 | `PASSED` | 1.67 | 0.004782 | `PASSED` | 0.005291 | 0.005291 | 0.006732 |
| 1 | `PASSED` | 1.403 | 0.00479 | `FAILED` | 0.005291 | 0.005291 | 0.4635 |
| 1.1 | `PASSED` | 1.159 | 0.004797 | `FAILED` | 0.005291 | 0.005291 | 0.8822 |
| 1.3 | `PASSED` | 0.7261 | 0.004811 | `FAILED` | 0.005291 | 0.005291 | 1.623 |

## Interpretation

- **trace_over_attenuation_source**: current_zero (trace_post=0) imposes a large effective bulk viscosity; the matched-NSF target assumes nu_b=0, hence ~6.27x over-attenuation.
- **marginal_ghost**: tau22 nu_b=0 has trace factor -1 (|lambda|=1, marginal ghost) that contaminates the longer thermal fit; a physical nu_b (factor ~-0.78) is strictly stable and keeps P2-5/P2-6/P2-7 passing with the existing heat curve.
- **normal_stress_isotropy_wall**: The residual attenuation (~1.67x) is a longitudinal normal-stress viscosity excess. A scalar regularized_shear_normal_factor that drives the attenuation ratio to 1 (~1.25) breaks P2-4 diagonal transverse shear; only 0.9 keeps diagonal shear correct. One scalar normal_factor cannot satisfy both.
- **conclusion**: Acoustic attenuation ratio -> ~1 is NOT reachable by local scalar calibration of the current closure. It needs an isotropic / recursive-regularized stress (and heat-flux) closure. Diagnostic only; baseline unchanged.
