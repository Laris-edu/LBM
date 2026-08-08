# Phase 2 C2+ -> C3 Wider-Extrapolation Diagnostic (RR default)

- run_id: `20260623T091003Z`
- c3_ready (compact-air boundary): **no**
- summary_digest: `c4dd2e5302461493b5585ffa8dfe11b9fa692077333a6f120b00a02f4f3ab810`

## Wavenumber axis (grid 64, mode 1/2/3)

| mode | nu max err | alpha max err | speed err | gamma err | speed/gamma | atten diag (GO-RISK) |
|---|---|---|---|---|---|---|
| 1 | 0.001758 | 0.0212 | 0.004905 | 0.009834 | `PASSED` | 0.308 |
| 2 | 1.94 | 0.7231 | 0.09268 | 0.1939 | `FAILED` | 5.912 |
| 3 | 5.087 | 0.8729 | 0.2286 | 0.5096 | `FAILED` | 13.06 |

## Resolution axis (mode 1, grids 48/64/96; steps ~ (N/64)^2)

| grid | nu max err | alpha max err | speed err | gamma err | hard pass |
|---|---|---|---|---|---|
| 48 | 0.4746 | 0.9068 | 0.03522 | 0.07167 | no |
| 64 | 0.001758 | 0.0212 | 0.004905 | 0.009834 | yes |
| 96 | 0.3396 | 0.778 | 0.008649 | 0.01722 | no |

## Prandtl axis (air-relevant Pr in [0.5,1.0])
- P2-7 `PASSED`  max Pr err 0.01006 (tol 0.05)

## Mach axis (background Mach [0,0.08])
- P2-9 `FAILED`  max speed err 0.009527, masking `PASSED`

## Verdict
- transport nu/alpha all axes pass: no
- resolution hard pass (48/64/96): no
- acoustic speed/gamma envelope (modes passing): [1]
- Pr air-range pass: yes; Mach Galilean pass: no

## Interpretation

- **transport**: Transport hard gates (nu isotropy P2-4, thermal alpha P2-5) hold across resolution (48/64/96) and wavenumber (mode 1/2/3): all-axes nu/alpha within tol = False.
- **acoustic**: Acoustic sound-speed/gamma hard gate holds at modes [1] (low-k envelope). Acoustic ATTENUATION anisotropy (diagonal ~1.31) and high-mode over-damping remain accepted bounded GO-RISK (reported, not gated); the compact-air target only excites the lowest mode, so the low-k envelope is the production-relevant one.
- **prandtl_mach**: P2-7 over air-relevant Pr in [0.5,1.0]: PASSED (max 0.01006). P2-9 Galilean over Mach [0,0.08]: FAILED (max speed err 0.009527).
- **boundaries**: Diagnostic; baseline unchanged. C3-readiness is for the BOUNDED_PRODUCTION_GO compact-air boundary (M2_Critical_Decision §5): hard gates across resolution / air-Pr / Mach / low-k; high-k acoustic attenuation is the documented GO-RISK boundary.
