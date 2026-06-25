# Phase 2 D2Q37 Recursive-Regularized (Local) Closure Diagnostic

- run_id: `20260620T135213Z`
- status: `DIAGNOSTIC_COMPLETE`
- closure: strain_rate_isotropic deviatoric + ghost_orthogonal_local (div) trace + diagnostic_zero bulk
- summary_digest: `1a660d688edf9d15ed183aa1ba21613d7d74f23ce4f13e31514104e658d424ae`

## Calibration (decoupled knobs)

- xy_factor = `0.4764`  (<- nu_T(x))
- normal_factor = `0.8906`  (<- nu_T(diagonal))
- chi = `1.085`  (<- attenuation(x))

## Full gate (x/y/diagonal)

- P2-4 `PASSED`  nu_T/nu: x=1, y=1, diagonal=1.002  (dir_diff=0.001779)
- P2-6 `PASSED`  attenuation_ratio: x=1.003, y=1.003, diagonal=1.233  (c_err=0.004903, g_err=0.00983, dir_diff=0.004093)
- P2-6 stability: invalid={'x': None, 'y': None, 'diagonal': None}  neg_theta={'x': False, 'y': False, 'diagonal': False}
- P2-5 `PASSED`  alpha_err: x=0.0018, y=0.0018, diagonal=0.02115

## Interpretation

- **x_y_attenuation**: Local, stable closure drives x/y acoustic attenuation to ratio ~1 while keeping nu_T isotropic (x/y/diagonal) and P2-5 passing -- the first local closure to do so.
- **diagonal_residual**: Diagonal acoustic attenuation ratio ~1.23 remains: diagonal-longitudinal loads the xy channel (shear_rate) plus chi (div) with no free knob once xy_factor and chi are pinned by x; the residual is the divergence/channel stencil anisotropy.
- **boundaries**: Diagnostic only; baseline unchanged. P2-4/P2-5/P2-6 only; P2-7/P2-9/high-mode/long-window not run. Not a production pass.
