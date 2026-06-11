# Phase_2 D2Q37 输运鲁棒性复核报告

本文档由 `python -m scripts.run_phase2_d2q37_transport_robustness` 生成。它只覆盖 D2Q37 fallback 新标定口径下的长窗口、mode=2 高模态、高背景速度和 P2-7 Pr 长窗口复核。

## 结论

- run id：`20260608T063346Z`
- required D2Q37 robustness status：`PASSED`
- D2Q37 candidate status：`TRANSPORT_PRODUCTION_CANDIDATE`
- production_physics_status：`IN_PROGRESS`
- M2 决策：`GO-RISK / D2Q37_ROBUSTNESS_PASSED`
- 失败场景：`none`

当前报告不启动 Phase_3，也不声明 final M2 production pass。后续 run `20260610T141926Z` 已完成 P2-6 真实声学声速/gamma hard gate 和 P2-9 真实 Galilean hard gate；matched 声衰减目标已推导，但 measured/reference 仍显著失配。

## 背景速度口径

- `theta_ref_lu`：`0.0483786`
- `c_s_lu=sqrt(gamma*theta_ref_lu)`：`0.26025`
- 高背景速度 Mach：`0.05`
- 高背景速度 `u_lu`：`[0.013012500000000003, 0.0]`

## D2Q37 high-mode correction

- dispersion correction enabled：`True`
- Laplacian thresholds：`[0.0192611, 0.0384294]`
- stress targets：`xy=0.786`，`normal=0.785`
- heat-flux targets：`retention=0.8512`，`export=0.3201`

## 场景汇总

| 场景 | 状态 | P2-4 最大相对误差 | P2-5 最大相对误差 | Fourier-law 误差 | P2-7 最大 Pr 误差 | first_invalid_step | NaN | clipping |
|---|---|---|---|---|---|---|---|---|
| `d2q37_long_window` | `PASSED` | `0.0136351` | `0.0012098` | `0.000156652` | `none` | `none` | `False` | `False` |
| `d2q37_high_mode_m2` | `PASSED` | `0.00406784` | `0.00282651` | `0.000813136` | `none` | `none` | `False` | `False` |
| `d2q37_background_mach_0p05` | `PASSED` | `0.0135277` | `0.00570682` | `0.000131529` | `none` | `none` | `False` | `False` |
| `d2q37_pr_long_window` | `PASSED` | `none` | `none` | `none` | `0.0460789` | `none` | `False` | `False` |

## 最大误差摘要

- P2-4 最大相对误差：`0.0136351`
- P2-5 最大相对误差：`0.00570682`
- P2-5 Fourier-law 最大误差：`0.000813136`
- P2-7 最大 Pr 相对误差：`0.0460789`
- 任一场景 NaN：`False`
- 任一场景 clipping：`False`

## 判读口径

- required D2Q37 robustness 失败时，D2Q37 不能升级为 production candidate。
- required D2Q37 robustness 通过时，D2Q37 只能升级为输运 production candidate；final M2 production pass 仍未声明。
- 本报告的背景速度场景只覆盖输运测量；后续 run `20260610T141926Z` 已将真实声学/Galilean 并入 P2-9 并通过。
