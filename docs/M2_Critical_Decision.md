# M2-Critical 决策记录

**最后更新**：2026-06-11

## 1. 触发条件

Phase_2 输运鲁棒性 run `20260605T131957Z` 触发 M2-Critical：

- 长时间窗口、mode=2 高模态、背景速度和长窗口 P2-7 required physical 场景失败。
- mode=2 下 P2-4 剪切黏性和 P2-5 热扩散/热流误差远超 5%。
- quadrature-matched configured 诊断对照也失败。

按 `docs/Phase_2/phase2_instruction_v1.1.md`，`thermal diffusivity or viscosity error > 5%` 必须形成本决策记录。

## 2. 已完成排查与修复

本轮完成以下修复，并由 run `20260605T152845Z` 复核：

| 项目 | 修复内容 | 结果 |
|---|---|---|
| 长窗口 diagonal shear 负温度 | 增加配置化 conservative biharmonic population filter：`high_wavenumber_filter.strength=0.0065`，不使用 clipping/floor/positivity repair | `physical_long_window` 中 P2-4 通过，无负温度 |
| 长窗口 thermal alpha 漂移 | 将 `auto_tau32_linear` 从短窗口校准改为长窗口校准：`-0.5467 + 0.949*(tau32-0.5)` | `physical_long_window` 中 P2-5 通过 |
| 背景速度 Fourier-law 相位误差 | 增加 conductive heat-flux Galilean 修正：`conductive_heat_flux_galilean_correction_factor=0.03272660408381829` | `physical_background_ux_0p005` 通过 |
| 不同振幅复核 | thermal 子场景改为 320 步窗口，避开初始热流弛豫主导的短窗口拟合 | `physical_amplitude_3e-5` 通过 |
| 长窗口 P2-7 Pr 漂移 | P2-7 内核改为 shear 240 步、thermal 320 步，并使用新的 `tau32` 闭合 | `physical_pr_long_window` 通过，最大 Pr 误差约 `1.178%` |

最新 M2 run `20260605T154824Z` 中，P2-4/P2-5/P2-7 均为 `PASSED`，但仍只代表 automation/contract 和当前 C2/C2+ 输运窗口通过，不代表 final M2 production pass。

2026-06-06 进一步执行 high-mode 标量敏感性诊断 run `20260606T074742Z`：

| 扫描对象 | 结论 |
|---|---|
| `regularized_shear_xy_factor` | 局部网格中不存在同时通过 x 方向 mode=1 与 mode=2 剪切测量的单标量值；`0.9` 可让 mode=2 x 误差约 `1.935%`，但 mode=1 x 误差升至约 `31.271%` |
| `regularized_shear_normal_factor` | 局部网格中不存在同时通过 diagonal mode=1 与 mode=2 剪切测量的单标量值 |
| `regularized_heat_flux_factor` | 局部网格中不存在同时通过 mode=1 与 mode=2 thermal/Fourier-law 的单标量值；当前值 `-0.4649237356175009` 保住 mode=1，但 mode=2 `alpha` 和 heat flux 仍大幅失败 |

该诊断报告见 `docs/Phase_2/Phase2_High_Mode_Sensitivity_Report.md`。它不是连续参数优化证明，但足以排除“继续局部重调单个 stress/heat-flux 经验标量”作为下一步主线。

同日执行 D2Q21 显式四阶高阶闭合诊断 run `20260606T083915Z`：

| 项目 | 结果 |
|---|---|
| central_moment_closure | `fourth_order` |
| scanned high_order_relaxation | `[0.7, 0.85, 1.0]` |
| joint pass | `False` |
| best_high_order_relaxation | `1.0` |
| best_max_metric | `598.953` |

该诊断报告见 `docs/Phase_2/Phase2_High_Order_Closure_Report.md`。它表明当前 D2Q21 显式四阶 central/binomial 高阶闭合无法同时满足低模态和 mode=2 的剪切、热扩散与 Fourier-law 热流要求。

因此，本记录中的 D2Q37 / 等价九阶速度集 fallback 已实际启动。2026-06-06 首轮迁移已完成诊断入口：

| 项目 | 结果 |
|---|---|
| module | `core/lattice_d2q37.py` |
| registry | `core/lattice.py` |
| config | `configs/gas_air_10k_d2q37_physical_timestep.yaml` |
| tests | `verification/test_phase2_d2q37_fallback.py`，并扩展 P2-1/P2-2/P2-3/P2-4/P2-5/P2-7/HDF5 诊断 |
| Q/D | `Q=37, D=2` |
| theta_q | `0.6979533220196852` |
| coverage | 正权重、opposite map、八阶偶矩、九阶奇对称 |
| integration status | `D2Q37_DIAGNOSTIC_READY`，已接入 equilibrium/collision/solver/M2 runner，但不是 production baseline |
| latest run | `20260606T133901Z` |
| dynamic status | 低模态诊断窗口 P2-4/P2-5/P2-7 均 `PASSED`，但该 pass 已被后续鲁棒性复核限制为短窗口诊断 |
| D2Q37 low-k closure | `regularized_shear_xy_factor=0.8739`，`regularized_shear_normal_factor=0.9`，`auto_d2q37_tau32_linear=-0.5030006782780277+0.7230829392328689*(tau32-0.5)`，`conductive_heat_flux_moment_factor=0.0422`，`conductive_heat_flux_galilean_correction_factor=0.03835608923273733` |
| low-k derivation | `docs/Phase_2/Phase2_D2Q37_LowK_Closure_Derivation.md` |
| robustness run | `20260608T063346Z` |
| robustness status | `GO-RISK / D2Q37_ROBUSTNESS_PASSED`，D2Q37 candidate status `TRANSPORT_PRODUCTION_CANDIDATE` |
| robustness failures | `none`；`d2q37_long_window`、`d2q37_high_mode_m2`、`d2q37_background_mach_0p05`、`d2q37_pr_long_window` 全部通过；无 NaN、无负温度、无 clipping |
| failure diagnosis run | `20260607T073921Z` |
| failure diagnosis status | `D2Q37_WAVENUMBER_WINDOW_DEPENDENT_CLOSURE` |
| failure diagnosis finding | D2Q37 stress/heat-flux 经验闭合被短窗口较高波数场景校准；低 k 长窗口 shear 约为目标 `2.09x`，低 k thermal heat-flux ratio 约 `0.33`，关闭 filter 后仍同阶失败 |
| high-mode repair | `regularized_shear_xy_dispersion_target=0.786`、`regularized_shear_normal_dispersion_target=0.785`、`regularized_heat_flux_dispersion_target=0.8512`、`conductive_heat_flux_dispersion_target=0.3201` |

## 3. 剩余失败

run `20260605T152845Z`、D2Q37 专项 run `20260607T140122Z` 和修复后 run `20260608T063346Z` 后，仍有以下关键失败/未完成项：

| 场景 | 角色 | 失败内容 |
|---|---|---|
| `physical_high_mode_m2` | required physical | P2-4 最大误差约 `193.095%`；P2-5 alpha 误差约 `284.896%`；Fourier-law 误差约 `184.702%` |
| `quadrature_matched_configured` | diagnostic control | configured heat-flux 参数下 P2-5 alpha 与热流严重失配；该配置不能作为 production pass 替代路径 |
| P2-6/P2-9/声衰减 | D2Q37 后续 production physics | D2Q37 输运鲁棒性已通过；P2-6 真实 acoustic eigenmode 的声速/gamma 和 P2-9 背景速度真实 Galilean 已由 run `20260610T141926Z` 通过；matched acoustic attenuation target 已推导，但声衰减 measured/reference 仍显著失配 |

线性谱排查显示，physical-timestep D2Q21 当前 collision 在高波数存在放大根；保守高波数 filter 可修复长窗口低模态稳定性，但不能在不破坏低模态输运误差的前提下同时修复 mode=2 dispersion/heat-flux 失配。

run `20260606T074742Z` 将上述判断进一步收敛：当前经验标量的单参数局部重调无法同时通过低模态与 mode=2，不能作为 production 修复方案。run `20260606T083915Z` 进一步表明，当前 D2Q21 显式四阶高阶闭合路径也不能作为 production 修复方案。run `20260606T142620Z` 表明旧 D2Q37 新标定口径只通过短窗口低模态诊断，不能通过长窗口和 Pr 鲁棒性外推，也不能升级为 production 候选。run `20260607T073921Z` 进一步确认其共同来源是波数/窗口依赖闭合：`32/mode1` 或 `64/mode2` 较高波数短窗口标定不能代表 `64/mode1` 低 k 长窗口 hydrodynamic 极限。随后 `docs/Phase_2/Phase2_D2Q37_LowK_Closure_Derivation.md` 已将低 k 长窗口作为硬约束重新推导并固化 closure；run `20260607T140122Z` 证明低 k 长窗口、Mach 0.05 背景速度和 Pr 长窗口已通过，但 mode=2 high-mode 成为唯一剩余 D2Q37 required failure。2026-06-08 已在不回退低 k closure 的前提下加入 D2Q37 周期谱 dispersion correction，run `20260608T063346Z` 将该 high-mode failure 修复并使四个 D2Q37 required robustness 场景全部通过。2026-06-11 已在 `docs/Phase_2/Phase2_Heat_Flux_Tau32_Closure.md` 固化 heat-flux collision 与 `tau32` 的 projection closure 口径。

## 4. 当前决策

当前不批准 final M2 production pass，也不启动 Phase_3 Level C production coupling。

当前保留 D2Q21 physical-timestep `central_moment_closure=second_order` 作为短窗口和低模态继续调试基线，但 high-mode required physical 失败已经进入 M2-Critical，且单个经验标量重调和当前 D2Q21 四阶高阶闭合均已被实测排除为主线修复。后续路线更新为：

1. D2Q21 `second_order` baseline 仅作为低模态 C2+ 调试基线保留，不声明 final M2 production pass；
2. D2Q21 `fourth_order` central/binomial 高阶闭合保持 diagnostic-only，除非后续有新的理论闭合和实测报告推翻 `20260606T083915Z`；
3. D2Q37 或等价九阶速度集路线已完成首轮诊断迁移、旧失败诊断、低 k 长窗口 closure 固化和 mode=2 high-mode dispersion/heat-flux 修复；`20260608T063346Z` 鲁棒性复核已通过，D2Q37 当前可作为输运 production candidate，不返工 Phase_1。

D2Q37 输运候选通过且 P2-6 声速/gamma 通过后，Phase_2 状态仍保持 `GO-RISK / IN-PROGRESS`。production_physics_status 从 D2Q37 输运、声速/gamma 和 P2-9 Galilean 角度为 `IN_PROGRESS`，但 final M2 production pass 仍未声明；下一步必须解释或修复 matched 声衰减 target 下的过阻尼，并继续诊断 high-mode acoustic 边界。
