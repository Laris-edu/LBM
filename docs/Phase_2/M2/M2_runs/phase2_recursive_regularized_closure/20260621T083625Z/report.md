# Phase 2 D2Q37 Recursive-Regularized (Local) Closure Diagnostic

- run_id: `20260621T083625Z`
- status: `DIAGNOSTIC_COMPLETE`
- closure: strain_rate_isotropic deviatoric + ghost_orthogonal_local (div) trace + diagnostic_zero bulk
- summary_digest: `60c7f8940256d98276173b5e9059296f5b09cff5a035fb606ef83e7048d9ef84`

## Calibration (decoupled knobs)

- xy_factor = `0.4764`  (<- nu_T(x))
- normal_factor = `0.8906`  (<- nu_T(diagonal))
- chi = `1.085`  (<- attenuation(x))

## Full gate (x/y/diagonal)

- P2-4 `PASSED`  nu_T/nu: x=1, y=1, diagonal=1.002  (dir_diff=0.001779)
- P2-6 `PASSED`  attenuation_ratio: x=1.003, y=1.003, diagonal=1.233  (c_err=0.004903, g_err=0.00983, dir_diff=0.004093)
- P2-6 stability: invalid={'x': None, 'y': None, 'diagonal': None}  neg_theta={'x': False, 'y': False, 'diagonal': False}
- P2-5 `PASSED`  alpha_err: x=0.0018, y=0.0018, diagonal=0.02115

## Extended gate (P2-7 Pr scan, P2-9 Galilean)

- P2-7 `FAILED`  baseline_pr_err=0.001781  max_pr_err=0.05238  (scan_tol=0.05)
- P2-9 `PASSED`  max_sound_speed_err=0.007654  max_dir_diff=0.02237  masking=`PASSED`

## Long window (3x; steps P2-4/5/6 = 720/960/720)

- P2-4 `PASSED`  nu_err: x=2.139e-05, diagonal=0.001758
- P2-5 `PASSED`  alpha_err: x=0.002219, diagonal=0.01804
- P2-6 attenuation_ratio: x=1.083, diagonal=1.458  invalid={'x': None, 'diagonal': None}  neg_theta={'x': False, 'diagonal': False}

## Interpretation

- **x_y_attenuation**: Local, stable closure drives x/y acoustic attenuation to ratio ~1 while keeping nu_T isotropic (x/y/diagonal) and P2-5 passing -- the first local closure to do so.
- **diagonal_residual**: Diagonal acoustic attenuation ratio ~1.23 remains: diagonal-longitudinal loads the xy channel (shear_rate) plus chi (div) with no free knob once xy_factor and chi are pinned by x; the residual is the divergence/channel stencil anisotropy (isotropic div/strain-rate stencils do not close it -- it is the 4-constraint/3-knob over-constraint).
- **p2_07_pr**: Pr scan varies alpha (tau32) at fixed tau21, so g_dev(tau21) does not affect it. The scan-extreme error (~5.3% at Pr=2) is dominated by the alpha/heat-flux closure (~baseline 4.94%) plus a small RR shear error at high Pr; not closable via the deviatoric knob.
- **p2_09_galilean**: P2-9 Galilean (low-mode) passes with the RR closure.
- **long_window**: Long-window (3x) is stable (no invalid step / negative theta); nu and alpha are window-consistent. Acoustic attenuation drifts with the fit window (x ~1.0->~1.08, diagonal ~1.23->~1.46): the damping is very weak (~1.6% amplitude change over 720 steps) so the attenuation fit is sensitive; the larger diagonal drift may indicate a slow diagonal effect.
- **boundaries**: Diagnostic only; baseline unchanged. high-mode acoustic not addressed. Strong GO-RISK candidate; not a window-independent production pass.
