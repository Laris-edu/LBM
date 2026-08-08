# Phase 2 D2Q37 Acoustic Attenuation Closure Diagnostic

- run_id: `20260617T063727Z`
- status: `DIAGNOSTIC_COMPLETE`
- config: `configs\gas_air_10k_d2q37_physical_timestep.yaml`
- summary_digest: `e6cf2ae4de9a88dda12fa6c6f9c8a4fe89125db1a88d4b81990da5af2a320be7`

## Candidate Summary

| trace_policy | trace_scale | heat_line | max thermal symbol error | baseline acoustic error n64 | baseline acoustic ratio n512 | low-k ghost radius | ghost pass | score | symbol pass |
|---|---:|---|---:|---:|---:|---:|---|---:|---|
| `current_zero` | `1` | `custom_affine` | `0.0074964` | `4.98022` | `4.99131` | `1` | `True` | `19.9209` | `False` |

## Dynamic Confirmation

No dynamic confirmation was run because no candidate passed the hydrodynamic symbol and low-k ghost stability gates.

## Ghost-Orthogonal Projector

- status: `DYNAMIC_PROJECTOR_EVALUATED`
- heat_curve: `(-0.504500678278, 0.726698353929)`
- alpha_h_curve: `(0.699947491657, -1.15260571121)`
- candidate_symbol_pass: `True`
- dynamic_gate_status: `passed_without_p2_9`

| metric | value |
|---|---:|
| thermal_error_max_n64 | `0.0074964` |
| acoustic_error_max_n64 | `0.0100461` |
| baseline_acoustic_error_n64 | `0.00335796` |
| baseline_acoustic_error_n512 | `0.22163` |
| baseline_acoustic_ratio_n512 | `1.22163` |
| spectral_radius_max | `1` |
| low_k_ghost_radius | `1` |
| low_k_ghost_pass | `True` |

| Pr | n | h | alpha_h | acoustic err | thermal err | spectral radius |
|---:|---:|---:|---:|---:|---:|---:|
| `0.5` | `64` | `-0.416064` | `0.55968` | `-0.0063294` | `0.0074964` | `0.999975` |
| `0.5` | `512` | `-0.416064` | `0.55968` | `0.179269` | `-0.232299` | `1` |
| `0.706133` | `64` | `-0.44188` | `0.600626` | `-0.00335796` | `-0.00593658` | `0.999978` |
| `0.706133` | `512` | `-0.44188` | `0.600626` | `0.22163` | `0.0817686` | `1` |
| `1` | `64` | `-0.460282` | `0.629814` | `-0.00842266` | `-0.00680047` | `0.99998` |
| `1` | `512` | `-0.460282` | `0.629814` | `-0.116381` | `0.535904` | `1` |
| `2` | `64` | `-0.482392` | `0.664881` | `-0.0100461` | `-0.00744193` | `0.999986` |
| `2` | `512` | `-0.482392` | `0.664881` | `-0.081234` | `2.06508` | `1` |

### Dynamic Confirmation

- status: `passed_without_p2_9`
- include_p2_9: `False`
- include_high_mode: `False`

| metric | value |
|---|---:|
| P2-5 | `PASSED` |
| alpha_relative_error | `0.019331` |
| heat_flux_relative_error | `0.000750239` |
| P2-6 | `PASSED` |
| attenuation_ratio | `0.881183` |
| attenuation_relative_error | `0.119058` |
| P2-7 | `PASSED` |
| max_pr_relative_error | `0.0178784` |

The projector separates r_g=0 trace ghost retention from hydrodynamic r_h=-alpha_h(tau32). The dynamic implementation is an explicit diagnostic spectral collision applied to low-k Fourier modes.

## Interpretation

current_zero is the production trace closure; tau22/calibrated variants are diagnostic candidates. A production fix requires hydrodynamic symbol matching, low-k full-symbol ghost stability, and dynamic P2-5/P2-7/P2-6 confirmation.
