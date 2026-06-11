# LBM 项目上下文入口

**最后更新**：2026-06-11
**用途**：新会话第一份必读文档，用于快速恢复项目当前指针、读取路线、不可误判规则和下一步优先级。
**定位**：本文是全项目生命周期唯一上下文入口，不是 Phase_2 专属文档。当前内容聚焦 Phase_2，只是因为项目当前处于 Phase_2。
**维护原则**：同次变更同步维护。本文只保留压缩摘要和入口索引；详细验证数据、长表格和完整历史由各阶段状态文档、M2/M3/M4 报告和专项诊断报告维护。

## 1. 新会话读取顺序

新会话继续本项目时，先读本文，再读当前阶段状态文档：

1. `docs/PROJECT_CONTEXT.md`
2. 当前阶段状态：`docs/Phase_2/Phase2_STATUS.md`
3. 当前 M2 汇总：`docs/M2_Verification_Report.md`
4. high-mode / D2Q21-D2Q37 决策：`docs/M2_Critical_Decision.md`
5. D2Q37 失败边界：`docs/Phase_2/Phase2_D2Q37_Failure_Diagnosis_Report.md`
6. D2Q37 低 k closure 推导：`docs/Phase_2/Phase2_D2Q37_LowK_Closure_Derivation.md`
7. heat-flux / `tau32` 闭合复核：`docs/Phase_2/Phase2_Heat_Flux_Tau32_Closure.md`
8. 声衰减 matched target 推导：`docs/Phase_2/Phase2_Acoustic_Attenuation_Target_Derivation.md`
9. D2Q37 鲁棒性复核：`docs/Phase_2/Phase2_D2Q37_Robustness_Report.md`
10. D2Q21 high-mode / high-order 诊断：`docs/Phase_2/Phase2_High_Mode_Sensitivity_Report.md`、`docs/Phase_2/Phase2_High_Order_Closure_Report.md`
11. 输运鲁棒性复核：`docs/Phase_2/Phase2_Transport_Robustness_Report.md`
12. collision / heat flux 口径：`docs/Phase_2/Phase2_Collision_Regularized_Stress_Note.md`
13. 文件职责：`docs/Phase_2/Phase2_Output_Files_Guide.md`
14. Phase_2 合同：`docs/Phase_2/phase2_instruction_v1.1.md`

推荐新会话提示词：

```text
请先阅读 docs/PROJECT_CONTEXT.md 和 docs/Phase_2/Phase2_STATUS.md，
然后继续 Phase_2 下一步工作。回答和文档均使用中文；暂不启动 Phase_3。
```

当前阶段变化时，必须在同一次变更中同步替换上述读取顺序中的阶段状态文档和阶段报告入口。

## 2. 当前项目指针

当前阶段：Phase_2 — gas-side thermal/compressible LBM core。

当前状态：

- Phase_2 framework：`PASSED`
- Contract-level verification：`PASSED`
- Production physics validation：`IN PROGRESS / GO-RISK`
- Final M2 production pass：`NOT YET CLAIMED`

最新主线事实：

- D2Q21 physical-timestep 低模态/长窗口 P2-4、P2-5、P2-7 当前已通过，最新 M2 run 为 `20260605T154824Z`。
- D2Q21 mode=2 high-mode required physical 场景仍失败，已触发 `docs/M2_Critical_Decision.md`。
- D2Q21 单标量重调诊断 `20260606T074742Z` 失败；D2Q21 `central_moment_closure=fourth_order` 诊断 `20260606T083915Z` 失败。
- D2Q37 fallback 已接入并达到 `D2Q37_DIAGNOSTIC_READY`，低模态短窗口 run `20260606T133901Z` 通过。
- D2Q37 失败诊断 run `20260607T073921Z` 将旧口径问题定位为 `D2Q37_WAVENUMBER_WINDOW_DEPENDENT_CLOSURE`：旧 D2Q37 stress/heat-flux 经验闭合被短窗口较高波数场景校准，不能外推到低 k 长窗口 hydrodynamic 极限。
- D2Q37 低 k 长窗口 closure 已重新推导并固化：`regularized_shear_xy_factor=0.8739`、`regularized_shear_normal_factor=0.9`、`auto_d2q37_tau32_linear=-0.5030006782780277+0.7230829392328689*(tau32-0.5)`、`conductive_heat_flux_moment_factor=0.0422`、`conductive_heat_flux_galilean_correction_factor=0.03835608923273733`。
- D2Q37 mode=2 high-mode 已通过单独的周期谱 dispersion correction 修复：stress correction targets 为 `regularized_shear_xy_dispersion_target=0.786`、`regularized_shear_normal_dispersion_target=0.785`，heat-flux retention/export targets 为 `0.8512/0.3201`，低 k 长窗口 closure 未回退。
- heat-flux collision 与 `tau32` 的当前关系已固化为 lattice-family projection closure：`alpha_lu=theta_transport_lu*(tau32-0.5)` 是唯一热扩散映射；`regularized_heat_flux_factor=h_family(tau32)` 只作为 raw central heat-flux projection retention；D2Q21/D2Q37 的 conductive scale、Galilean correction 和 D2Q37 spectral correction 已在 `docs/Phase_2/Phase2_Heat_Flux_Tau32_Closure.md` 中复核。
- 最新 D2Q37 鲁棒性 run `20260608T063346Z` 为 `PASSED / TRANSPORT_PRODUCTION_CANDIDATE`：`d2q37_long_window`、`d2q37_high_mode_m2`、`d2q37_background_mach_0p05`、`d2q37_pr_long_window` 全部通过；最大 P2-4 误差约 `1.3635%`，最大 P2-5 alpha 误差约 `0.5707%`，最大 Fourier-law 误差约 `0.0813%`，最大 Pr 误差约 `4.6079%`；无 NaN、无 clipping。
- D2Q37 真实 P2-6 acoustic eigenmode 已接入并通过；最新 M2 run `20260610T141926Z` 中 x/y 方向 `c_target_lu=0.26025`、`c_measured_lu≈0.261486`、声速最大相对误差约 `0.4750%`，`gamma_measured≈1.41333`、gamma 最大相对误差约 `0.9523%`，方向差异约 `2.3e-10`；无 NaN、无 clipping。matched linearized NSF 声衰减 target 已推导为 `2.22224320740558e-05` LU/step，但 measured≈`1.393385e-4`，相对差异约 `5.27`，因此声衰减仍是 diagnostic/GO-RISK，不是 hard pass。
- D2Q37 P2-9 已扩展为背景速度下真实输运和声学测量并通过 run `20260610T141926Z`：Mach `0.02/0.05`、背景方向 `x/diagonal` 四个场景全部 `PASSED`；最大 `nu` 漂移约 `0.0211%`，最大 `alpha` 漂移约 `0.4502%`，扣除 `k·U0` 后最大声速误差约 `0.1660%`，最大声速漂移约 `0.0170%`，最大方向差异约 `0.8370%`；D2Q37 dispersion masking check 为 `PASSED`，mode=2 背景声学在 correction 开/关下均 `FAILED`，判定 `NO_MASKING_DETECTED`。

最近确认：

```text
python -m pytest -q verification/test_phase2_p2_09_galilean_consistency.py
3 passed

python -m pytest -q verification tests
58 passed

python -m scripts.run_m2_verification --config configs/gas_air_10k_d2q37_physical_timestep.yaml
34 passed inside runner; wrote results/m2/20260610T141926Z

python -m ruff check core phase3_interfaces scripts verification
All checks passed
```

## 3. 不可误判规则

- 不把 automation/contract `PASSED` 写成 final M2 production pass。
- 不把 D2Q21 低模态 C2+ 通过写成高模态或 production C3 通过。
- 不把 D2Q37 输运鲁棒性、P2-6 声速/gamma、P2-9 Galilean 或 heat-flux/tau32 projection closure 固化写成 final M2 production pass；当前 D2Q37 只能视为 transport + acoustic-speed/gamma + Galilean candidate，声衰减 matched target 已推导但 measured/reference 显著失配，high-mode acoustic 边界仍未完成。
- 不把 quadrature-matched 诊断通过等同于 physical-timestep production pass。
- 不使用 clipping、distribution floor 或 positivity repair 制造 pass。
- 不修改 Phase_1 CSV、manifest 或封版报告；Phase_1 reference 只用于 handoff/reference alignment 和回归保护。
- 不启动 Phase_3 Level C production coupling；只可在明确需要时做 Phase_3 Level A/B interface debugging。
- scripts 和 docs 不硬编码 `.venv\Scripts\python.exe`；脚本使用 `sys.executable` 或 `python -m`。
- 默认使用项目工作区内 `.venv` 虚拟环境及其中的项目依赖运行命令；若该项目环境缺少必要依赖，可自行下载并安装与当前项目环境和 Python 版本匹配的依赖包。
- 回答和新增文档使用中文。

## 4. 当前关键决策

- tau / transport mapping 只能在 `core/unit_mapping.py` 中完成；其他模块只能消费 `UnitMapping`。
- baseline `bulk_viscosity_policy=diagnostic_zero`；声衰减 matched NSF target 已推导，但当前 D2Q37 measured/reference 显著失配，继续保持 diagnostic / GO-RISK。
- array layout 冻结：`c=(Q,D)`，`w=(Q,)`，`f/g=(...,Q)`，`u/q_lu=(...,D)`。
- Phase_2 周期验证使用 pull streaming，速度轴始终是最后一维。
- heat flux 分为 raw central energy flux 和 conductive `q_lu`：collision 内部可用 raw moment；`GasSolver2D`、HDF5、P2-5 Fourier-law 和 Phase_3 handoff 使用 conductive `q_lu`。
- `tau32` 是唯一热扩散 relaxation time：`alpha_lu=theta_transport_lu*(tau32-0.5)`；`regularized_heat_flux_factor` 是随 `tau32` 变化的 lattice-family projection retention，不是独立热扩散旋钮。
- D2Q21 当前保留 `central_moment_closure=second_order` 作为低模态 C2+ baseline；`fourth_order` 仅为 diagnostic。
- D2Q37 是 M2-Critical fallback 路线；低 k 长窗口 stress/heat-flux closure 已固化，mode=2 high-mode 由周期谱 dispersion correction 单独修复，P2-6 声速/gamma 和 P2-9 背景速度 Galilean 已通过，但当前仍只可升级为 transport + acoustic-speed/gamma + Galilean candidate。

## 5. 下一步优先级

1. 定位 D2Q37 P2-6 声衰减相对 matched NSF target 过阻尼约 `5.27x` 的来源；修复前声衰减保持 diagnostic/GO-RISK。
2. 复核 D2Q37 mode=2 背景声学失败边界，明确 high-mode acoustic 是否需要独立 dispersion/closure 处理；当前 P2-9 masking check 只证明 spectral correction 未掩盖该误差。
3. 将 P2-8/P2-9 后续方向统计扩展到 diagonal acoustic wave direction。
4. 在更宽网格/波数/Pr 范围继续复核 heat-flux/tau32 projection closure、Galilean correction 和 D2Q37 spectral correction 的外推边界。
5. 复核 quadrature-matched 诊断配置的 stress/heat-flux 参数口径，明确它是实现诊断还是可替代 lattice scaling 路径。
6. 保持 D2Q21 `central_moment_closure=second_order` 作为低模态 C2+ baseline，不把 `fourth_order` 诊断失败写成 production regression。
7. 完善 HDF5 probe 输出，供 Phase_3 Level A/B 后续复用。

## 6. 维护规则

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
- `新会话读取顺序`
- `当前项目指针`
- `不可误判规则`
- `当前关键决策`
- `下一步优先级`

维护边界：

- 不复制长表格、完整历史、全部 run 数值或 YAML 参数块。
- 详细验证数据放在 `docs/M2_Verification_Report.md` 或后续 M3/M4 报告。
- 阶段内部状态、风险和更新日志放在对应的 `docs/Phase_N/PhaseN_STATUS.md`。
