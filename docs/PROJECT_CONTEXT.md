# LBM 项目上下文入口

**最后更新**：2026-06-18
**用途**：新会话第一份必读文档，用于快速恢复项目当前阶段、读取路线、不可误判规则和下一步优先级。
**定位**：本文是全项目生命周期唯一上下文入口，不是 Phase_2 专属文档。
**维护原则**：本文只保留压缩摘要和入口索引；阶段流水、run 细节、长命令、完整数值和推导证据由阶段状态文档、M2/M3/M4 报告和专项诊断报告维护。

## 1. 新会话最小读取

新会话继续本项目时，按以下顺序读取：

1. `docs/PROJECT_CONTEXT.md`
2. 当前阶段状态：`docs/Phase_2/Phase2_STATUS.md`
3. 当前 M2 汇总：`docs/M2_Verification_Report.md`
4. high-mode / D2Q21-D2Q37 决策：`docs/M2_Critical_Decision.md`
5. high-mode acoustic eigen-branch：`docs/Phase_2/Phase2_D2Q37_High_Mode_Acoustic_Eigenbranch.md`
6. 当前声衰减主线：`docs/Phase_2/Phase2_D2Q37_Ghost_Orthogonal_Trace_Closure.md`
7. 声衰减 target 口径：`docs/Phase_2/Phase2_Acoustic_Attenuation_Target_Derivation.md`
8. heat-flux / `tau32` 口径：`docs/Phase_2/Phase2_Heat_Flux_Tau32_Closure.md`
9. 文件职责：`docs/Phase_2/Phase2_Output_Files_Guide.md`
10. Phase_2 合同：`docs/Phase_2/phase2_instruction_v1.1.md`

推荐新会话提示词：

```text
请先阅读 docs/PROJECT_CONTEXT.md 和 docs/Phase_2/Phase2_STATUS.md，
然后继续 Phase_2 下一步工作。回答和文档均使用中文；暂不启动 Phase_3。
```

当前阶段变化时，必须在同一次变更中同步替换读取顺序中的阶段状态文档和阶段报告入口。

## 2. 当前项目指针

当前阶段：Phase_2 — gas-side thermal/compressible LBM core。

当前状态：

- Phase_2 framework：`PASSED`
- Contract-level verification：`PASSED`
- Production physics validation：`IN PROGRESS / GO-RISK`
- Final M2 production pass：`NOT YET CLAIMED`

当前主线结论：

- D2Q21 低模态 physical-timestep P2-4/P2-5/P2-7 已通过，但 mode=2 high-mode 仍失败；D2Q21 继续保留为低模态 C2+ baseline，不作为 high-mode production 解。
- D2Q37 fallback 已完成 lattice-family 接入、低 k 长窗口 closure、mode=2 dispersion correction、真实 P2-6 声速/gamma 和 P2-9 Galilean 复核；当前可视为 transport + acoustic-speed/gamma + Galilean candidate。
- D2Q37 默认 baseline 仍不能声明 final M2 production pass；核心阻塞是 matched acoustic attenuation 与 high-mode acoustic 边界。
- matched linearized NSF 声衰减 target 已固化，默认 D2Q37 baseline measured/reference 仍显著失配，声衰减保持 diagnostic / GO-RISK。
- 2026-06-15 已将 D2Q37 trace / bulk 与 heat-flux retention 显式参数化；默认仍为 `trace_bulk_policy=current_zero` 和当前 `auto_d2q37_tau32_linear`，不改变 baseline。
- 2026-06-16 已排除 scalar trace retention + scalar heat retention 路线：放大型 trace 会触发低 k ghost amplification，非放大型 scalar 边界也无法同时满足 thermal/acoustic gate。
- 2026-06-17 `ghost_orthogonal_spectral` diagnostic projector 已通过当前 hydrodynamic symbol、low-k ghost stability、P2-5/P2-6/P2-7/P2-9 gate；但它是全局 spectral diagnostic collision，不是 local production baseline。
- 2026-06-17 local 路线仍未收敛：`ghost_orthogonal_local` 可通过 x/y low-k gate 但 diagonal/isotropy 不足；`ghost_orthogonal_local_laplacian`、`ghost_orthogonal_local_pressure_memory`、`ghost_orthogonal_local_two_channel` 和 `ghost_orthogonal_local_entropy_manifold` 已作为反例排除。
- `ghost_orthogonal_local_two_channel` 已实现 diagnostic pressure/thermal projector：`div_a=div_p`、`div_t=div_c(u)-div_p`、`T_post=rho*theta*(chi_a*div_a+chi_t*div_t)`；x/y P2-5/P2-6 可维持，但 diagonal P2-5/P2-6 gate 仍失败。
- 2026-06-18 已复核并修复 D2Q37 diagonal low-mode 分支：独立 diagonal heat-flux retention/export correction 使 P2-5 x/y/diagonal 通过；随后新增 diagonal acoustic phase correction，使 P2-6 x/y/diagonal 和 P2-9 通过。该修复仍是 spectral low-mode correction，不能写成 final M2 production pass。
- 2026-06-18 已推导并实现 D2Q37 high-mode acoustic full-modal eigen-branch diagnostic closure：默认 `acoustic_phase_high_mode_factor=1.0`、`acoustic_phase_high_mode_diagonal_factor=1.0` 不改变 baseline；诊断 seed `axis=0.955, diagonal=0.918` 可使原始 baseline `64/mode2` x/y/diagonal acoustic speed/gamma 全部进入 hard gate。外推复核 run `20260618T143220Z` 确认该 seed 只在同一离散 Laplacian / 原始 Pr / 无背景边界内成立，`Pr=0.5/2.0`、Mach `0.05` 背景和 `64/mode3` 均失败；attenuation 仍约 `8x..17x` 过阻尼，且仍是 diagnostic spectral，不是 production baseline。

## 3. 不可误判规则

- 不把 automation/contract `PASSED` 写成 final M2 production pass。
- 不把 D2Q21 低模态 C2+ 通过写成高模态或 production C3 通过。
- 不把 D2Q37 输运鲁棒性、P2-6 声速/gamma、P2-9 Galilean 或 heat-flux/tau32 projection closure 固化写成 final M2 production pass。
- 不把 `ghost_orthogonal_spectral` diagnostic projector 通过写成 local production collision 通过。
- 不把 `ghost_orthogonal_local` 的 x/y low-k 通过写成 diagonal/isotropy 或 production closure 通过。
- 不把 `ghost_orthogonal_local_two_channel` 的实现或 x/y smoke 写成 diagonal/isotropy 或 production closure 通过。
- 不把 `ghost_orthogonal_local_entropy_manifold` 的形式区分能力写成 diagonal thermal gate 通过。
- 不把 quadrature-matched 诊断通过等同于 physical-timestep production pass。
- 不使用 clipping、distribution floor 或 positivity repair 制造 pass。
- 不修改 Phase_1 CSV、manifest 或封版报告；Phase_1 reference 只用于 handoff/reference alignment 和回归保护。
- 不启动 Phase_3 Level C production coupling；只可在明确需要时做 Phase_3 Level A/B interface debugging。
- scripts 和 docs 不硬编码 `.venv\Scripts\python.exe`；脚本使用 `sys.executable` 或 `python -m`。
- 默认使用项目工作区内 `.venv` 虚拟环境及其中的项目依赖运行命令；若项目环境缺少必要依赖，可安装与当前 Python 版本匹配的依赖包。
- 回答和新增文档使用中文。

## 4. 当前关键决策

- tau / transport mapping 只能在 `core/unit_mapping.py` 中完成；其他模块只能消费 `UnitMapping`。
- baseline `bulk_viscosity_policy=diagnostic_zero`；声衰减保持 diagnostic / GO-RISK，不能作为 hard pass。
- array layout 冻结：`c=(Q,D)`，`w=(Q,)`，`f/g=(...,Q)`，`u/q_lu=(...,D)`。
- Phase_2 周期验证使用 pull streaming，速度轴始终是最后一维。
- heat flux 分为 raw central energy flux 和 conductive `q_lu`：collision 内部可用 raw moment；`GasSolver2D`、HDF5、P2-5 Fourier-law 和 Phase_3 handoff 使用 conductive `q_lu`。
- `tau32` 是唯一热扩散 relaxation time：`alpha_lu=theta_transport_lu*(tau32-0.5)`；`regularized_heat_flux_factor` 是随 `tau32` 变化的 lattice-family projection retention，不是独立热扩散旋钮。
- D2Q37 spectral correction 现在分层记录：baseline `h(tau32)`、high-mode transport dispersion target、diagonal low-mode heat-flux retention/export target、diagonal low-mode acoustic phase factor，以及 high-mode acoustic diagnostic phase factors；conductive `q_lu` 仍只由 `GasSolver2D`/HDF5/P2-5/Phase_3 handoff 导出。
- P2-9 语义已拆分：`transport_dispersion_masking_status` 是 hard masking 语义，`acoustic_eigenbranch_diagnostic_status` 只记录 high-mode acoustic branch 诊断结果；不得再把 acoustic eigen-branch diagnostic 写成 transport masking 结论。
- D2Q37 trace / bulk channel 已显式参数化；默认 `trace_bulk_policy=current_zero` 只保留既有输运候选基线。
- scalar trace/bulk scaling、local Laplacian、pressure-only、two-channel pressure/thermal projector 和 entropy-manifold trace estimator 已被排除为当前 production 修复方向；ghost-orthogonal spectral 已证明分离 `r_g` 与 `r_h` 可行，但 local production closure 仍未完成。
- D2Q21 当前保留 `central_moment_closure=second_order` 作为低模态 C2+ baseline；`fourth_order` 仅为 diagnostic。
- D2Q37 是 M2-Critical fallback 路线；当前只可升级为 transport + acoustic-speed/gamma + Galilean candidate。

## 5. 下一步优先级

1. 基于 high-mode acoustic 外推复核结果，推导可随 `Pr/tau32`、Mach/background 和 wave-number branch 变化的 eigen-branch closure；当前 `axis=0.955, diagonal=0.918` 只能保留为窄边界 diagnostic seed。
2. 继续复核 matched acoustic attenuation 失配；当前 low-mode 与 high-mode 声衰减仍是 diagnostic / GO-RISK，不能作为 hard pass。
3. 对任何下一 candidate 直接运行 x/y/diagonal P2-5、x/y/diagonal P2-6、P2-7 和 P2-9 smoke；候选必须同时通过 hydrodynamic symbol、low-k ghost stability、P2-5/P2-6/P2-7/P2-9 动态 gate。
4. 将 P2-8/P2-9 后续方向统计扩展到 high-mode acoustic wave direction，并保留 transport masking 与 acoustic eigen-branch diagnostic 的分离字段。
5. 在更宽网格/波数/Pr 范围继续复核 heat-flux/tau32 projection closure、Galilean correction 和 D2Q37 spectral correction 的外推边界。
6. 复核 quadrature-matched 诊断配置的 stress/heat-flux 参数口径，明确它是实现诊断还是可替代 lattice scaling 路径。
7. 保持 D2Q21 `central_moment_closure=second_order` 作为低模态 C2+ baseline，不把 `fourth_order` 诊断失败写成 production regression。
8. 完善 HDF5 probe 输出，供 Phase_3 Level A/B 后续复用。

## 6. 详细事实入口

- 阶段总状态、验证记录、风险和更新日志：`docs/Phase_2/Phase2_STATUS.md`
- 当前 M2 汇总结果：`docs/M2_Verification_Report.md`
- D2Q21 high-mode 失败与 D2Q37 fallback 决策：`docs/M2_Critical_Decision.md`
- D2Q37 声衰减和 trace / bulk 最新推导：`docs/Phase_2/Phase2_D2Q37_Ghost_Orthogonal_Trace_Closure.md`
- D2Q37 high-mode acoustic eigen-branch：`docs/Phase_2/Phase2_D2Q37_High_Mode_Acoustic_Eigenbranch.md`
- D2Q37 失败边界：`docs/Phase_2/Phase2_D2Q37_Failure_Diagnosis_Report.md`
- D2Q37 低 k closure：`docs/Phase_2/Phase2_D2Q37_LowK_Closure_Derivation.md`
- heat-flux / `tau32` closure：`docs/Phase_2/Phase2_Heat_Flux_Tau32_Closure.md`
- 声衰减 matched target：`docs/Phase_2/Phase2_Acoustic_Attenuation_Target_Derivation.md`
- D2Q37 鲁棒性复核：`docs/Phase_2/Phase2_D2Q37_Robustness_Report.md`
- D2Q21 high-mode / high-order 诊断：`docs/Phase_2/Phase2_High_Mode_Sensitivity_Report.md`、`docs/Phase_2/Phase2_High_Order_Closure_Report.md`
- 输运鲁棒性复核：`docs/Phase_2/Phase2_Transport_Robustness_Report.md`
- collision / heat flux 口径：`docs/Phase_2/Phase2_Collision_Regularized_Stress_Note.md`
- Phase_1 reference 边界：`docs/Phase_1/Phase1_STATUS.md`

## 7. 维护规则

`docs/PROJECT_CONTEXT.md` 是全项目唯一上下文入口。不得为每个阶段创建新的 `PROJECT_CONTEXT.md`；进入 Phase_3 或后续阶段时更新同一个文件。

发生以下变化时，必须在同一次代码或文档改动中同步更新本文档：

- 阶段完成、阶段启动或当前阶段指针变化。
- M2/M3/M4 等阶段决策变化。
- 新的 M2/M3/M4 run 成为最新权威运行。
- P2-4、P2-5、P2-6、P2-7、P2-9 或后续阶段关键测试状态变化。
- collision、unit mapping、heat-flux definition、bulk viscosity policy 或 lattice scaling 改变。
- Phase_3 启动口径、production pass 口径或 Level A/B/C 边界改变。
- 下一步优先级改变。

同步更新时至少修改：

- `最后更新`
- `新会话最小读取`
- `当前项目指针`
- `不可误判规则`
- `当前关键决策`
- `下一步优先级`

维护边界：

- 入口文档只写结论、判断口径和链接。
- 不复制长表格、完整历史、全部 run 数值、完整命令或 YAML 参数块。
- 阶段内部状态、风险、更新日志和详细 run 记录放在 `docs/Phase_N/PhaseN_STATUS.md`。
- 完整验证数据放在 `docs/M2_Verification_Report.md` 或后续 M3/M4 报告。
- 推导证据和反例放在对应专项报告，不回填到本文。
