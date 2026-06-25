# Phase_2 输运鲁棒性复核报告

本文档由 `python -m scripts.phase2_robust_transport` 生成。它记录 P2-4/P2-5/P2-7 在长时间窗口、高模态、不同振幅、背景速度和 quadrature-matched 对照下的复核结果。

## 结论

- run id：`20260605T152845Z`
- required physical status：`FAILED`
- diagnostic control status：`FAILED`
- production_physics_status：`NOT_PASSED`
- M2 决策：`GO-RISK / ROBUSTNESS_FAILED`
- 失败的 required physical 场景：`physical_high_mode_m2`
- 失败的 diagnostic 对照场景：`quadrature_matched_configured`

当前报告不启动 Phase_3，也不声明 final M2 production pass。physical-timestep 短时 C2 通过仍需和本报告中的鲁棒性失败分开理解。

## 场景汇总

| 场景 | 配置角色 | production 必需 | 状态 | P2-4 最大相对误差 | P2-5 最大相对误差 | Fourier-law 误差 | P2-7 最大 Pr 误差 | first_invalid_step | NaN | clipping |
|---|---|---|---|---|---|---|---|---|---|---|
| `physical_long_window` | `physical_timestep` | `True` | `PASSED` | `0.0233287` | `0.0173799` | `0.00534162` | `none` | `none` | `False` | `False` |
| `physical_high_mode_m2` | `physical_timestep` | `True` | `FAILED` | `1.93095` | `2.84896` | `1.84702` | `none` | `none` | `False` | `False` |
| `physical_amplitude_3e-5` | `physical_timestep` | `True` | `PASSED` | `0.0233782` | `0.0173799` | `0.00534162` | `none` | `none` | `False` | `False` |
| `physical_background_ux_0p005` | `physical_timestep` | `True` | `PASSED` | `0.0233883` | `0.0173599` | `0.00534435` | `none` | `none` | `False` | `False` |
| `physical_pr_long_window` | `physical_timestep` | `True` | `PASSED` | `none` | `none` | `none` | `0.0117829` | `none` | `False` | `False` |
| `quadrature_matched_configured` | `quadrature_matched_diagnostic` | `False` | `FAILED` | `0.0687923` | `20.7021` | `42.0839` | `none` | `none` | `False` | `False` |

## 最大误差摘要

- P2-4 最大相对误差：`1.93095`
- P2-5 最大相对误差：`20.7021`
- P2-5 Fourier-law 最大误差：`42.0839`
- P2-7 最大 Pr 相对误差：`0.0117829`
- 任一场景 NaN：`False`
- 任一场景 clipping：`False`

## 判读口径

- required physical 场景失败时，`production_physics_status` 保持 `NOT_PASSED`。
- quadrature-matched 场景是诊断对照，不单独建立 production pass。
- 本报告的背景速度场景只覆盖输运测量；后续 D2Q37 run `20260610T141926Z` 已将真实声学/Galilean 并入 P2-9 并通过。
- 本报告暴露的问题优先回到 heat-flux/tau32 闭合、central-Hermite/binomial transform 和长时间稳定性分析。
