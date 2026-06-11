# Phase_2 Collision Regularized Stress / Heat-Flux Note

**最后更新**：2026-06-11

## 1. 目的

本文记录当前 `core/collision_smrt.py` 从 raw population scaffold 升级为 regularized central-Hermite/binomial stress/heat-flux collision 的实现口径、已验证效果和剩余风险。heat-flux collision 与 `tau32` 的专项关系已另见 `docs/Phase_2/Phase2_Heat_Flux_Tau32_Closure.md`。

本文不是文献级 SMRT collision 完整推导；它是 Phase_2 当前工程实现状态说明。

## 2. 当前碰撞流程

当前逐 cell collision 仍保持 Phase_2 合同中的守恒闭合：

1. 从 `f/g` 恢复 `rho`、`u`、`theta`、`K_tr`、`G_int` 和中心总能量。
2. 构造 `f_eq/g_eq`。
3. 对 `f` 只保留二阶中心非平衡应力，使用带 D2Q21 权重的最小范数中心矩投影重构 population。
4. 对 `f` 三阶中心平动能量通量和 `g` 一阶中心内部能量通量做受约束投影；投影保持 `f` 的零密度、零动量、零二阶应力增量，以及 `g` 的零零阶矩增量。
5. 用 `g` 零阶矩逐 cell 修正，使选定中心总能量严格守恒。

所有输运映射仍由 `core/unit_mapping.py` 管理。当前 physical-timestep baseline 额外记录：

```yaml
regularized_shear_xy_factor: 0.965
regularized_shear_normal_factor: 0.845
central_moment_closure: second_order
high_order_relaxation: 1.0
high_wavenumber_filter: {enabled: true, strength: 0.0065, passes: 1}
regularized_heat_flux_factor_policy: auto_tau32_linear
regularized_heat_flux_factor: -0.4649237356175009  # baseline resolved value
regularized_heat_flux_f_fraction: 0.5714285714285714
conductive_heat_flux_moment_factor: 0.05192359403391186
conductive_heat_flux_galilean_correction_factor: 0.03272660408381829
```

其中 `regularized_heat_flux_f_fraction=4/7` 对应 `D=2, S=3` 下按焓贡献分配 `f/g` 热流；`auto_tau32_linear` 当前定义为：

```text
regularized_heat_flux_factor = -0.5467 + 0.949 * (tau32 - 0.5)
```

`conductive_heat_flux_moment_factor` 用于把 raw central energy-flux moment 转换为 P2-5 和 Phase_3 handoff 使用的 conductive `q_lu`；`conductive_heat_flux_galilean_correction_factor` 用于修正背景速度下的导热热流相位缺陷。上述系数是当前 D2Q21 physical-timestep mapping 下的 projection closure 参数；`tau32` 仍是唯一热扩散 relaxation time，关系为 `alpha_lu=theta_transport_lu*(tau32-0.5)`。

`central_moment_closure=second_order` 是当前 D2Q21 baseline 口径。`central_moment_closure=fourth_order` 已实现为 diagnostic-only 路径，用于显式四阶 central/binomial 高阶闭合复核；它当前不能作为 production baseline。

## 3. 已验证效果

最新 physical-timestep run `20260605T154824Z` 中：

- P2-4 真实剪切波：`PASSED`。
- 三方向最大 `nu` 相对误差约 `2.338%`。
- P2-5 真实等压热扩散与 Fourier-law 热流：`PASSED`。
- 两方向最大 `alpha` 相对误差约 `1.738%`。
- Fourier-law 热流幅值误差约 `0.534%`。
- P2-7 真实 Pr 扫描：`PASSED`；baseline air 点 `Pr_measured≈0.71026`，baseline 相对误差约 `0.585%`，targets `[0.5, 0.7061328707, 1.0, 2.0]` 的最大 Pr 相对误差约 `1.178%`。
- 无负温度、无 NaN、无 clipping。
- 质量、动量、选定中心总能量守恒测试继续通过。

这说明原 P2-4 负温度失稳主要来自 raw population 非平衡高阶噪声；原 P2-5 失败主要来自缺少 `g` 一阶内部能量通量、`f` 三阶平动能量通量和 conductive heat-flux 读数定义；P2-7 失败则来自固定 `regularized_heat_flux_factor=-0.45` 未随 `tau32` 改变。本轮进一步通过 conservative high-wavenumber filter、长窗口 `auto_tau32_linear` 和 Galilean heat-flux 修正，使低模态长窗口 P2-4/P2-5/P2-7 同时通过。

最新输运鲁棒性 run `20260605T152845Z` 表明，长时间窗口、不同振幅、背景速度和长窗口 P2-7 required physical 场景已经通过；剩余 required failure 是 `physical_high_mode_m2`，quadrature-matched configured 诊断对照也失败。具体报告见 `docs/Phase_2/Phase2_Transport_Robustness_Report.md`，M2-Critical 决策见 `docs/M2_Critical_Decision.md`。

high-mode 标量敏感性 run `20260606T074742Z` 进一步表明，单独重调 `regularized_shear_xy_factor`、`regularized_shear_normal_factor` 或 `regularized_heat_flux_factor` 的局部网格中不存在同时通过 mode=1 与 mode=2 的组合。报告见 `docs/Phase_2/Phase2_High_Mode_Sensitivity_Report.md`。因此，当前不应继续把单个经验标量重调作为 high-mode production 修复主线。

D2Q21 四阶高阶闭合诊断 run `20260606T083915Z` 表明，`central_moment_closure=fourth_order` 与 `high_order_relaxation=[0.7, 0.85, 1.0]` 的扫描均不能同时满足低模态和 mode=2 的剪切、热扩散与 Fourier-law 热流要求。报告见 `docs/Phase_2/Phase2_High_Order_Closure_Report.md`。因此，D2Q37 / 等价九阶速度集 fallback 已启动；当前已从静态 lattice 推进到 `D2Q37_DIAGNOSTIC_READY`，并接入 equilibrium、collision、solver、HDF5 metadata、M2 runner 和 P2-4/P2-5/P2-7 动态诊断。旧 run `20260606T133901Z` 的低模态短窗口通过已由 `20260607T073921Z` 限定为波数/窗口依赖闭合；当前已在 `docs/Phase_2/Phase2_D2Q37_LowK_Closure_Derivation.md` 中固化低 k 长窗口 D2Q37 closure，并通过周期谱 dispersion correction 修复 mode=2 high-mode。run `20260608T063346Z` 中 D2Q37 四个 required robustness 场景全部通过，D2Q37 当前为 `TRANSPORT_PRODUCTION_CANDIDATE`，但还不是 final M2 production baseline。

## 4. 仍需固化的问题

当前 P2-4/P2-5/P2-7 通过仍是 physical-timestep baseline 下的低模态工程验证，不是 final M2 production pass。后续仍需完成：

- 修复 `20260605T152845Z` 中仍失败的 mode=2 shear/thermal/heat-flux 失配；
- 在单标量重调和当前 D2Q21 四阶高阶闭合均已排除后，继续推进 D2Q37 / 等价九阶速度集迁移；
- 在 D2Q37 输运候选基础上继续复核 high-mode spectral correction 的网格/波数外推和声学影响；
- 在更宽 Pr/模态/背景速度范围内继续复核 `auto_tau32_linear`、`conductive_heat_flux_moment_factor` 和 Galilean correction 不掩盖 `tau32` 热扩散控制问题；
- 继续解释或修复 P2-6 声衰减相对 matched NSF target 的过阻尼；
- 将 P2-8/P2-9 后续方向统计扩展到 diagonal acoustic wave direction。

## 5. 维护规则

- 不使用 clipping、floor 或 positivity repair 来制造 pass。
- 若调整 stress/heat-flux correction factor，必须同步更新 `core/unit_mapping.py`、HDF5 metadata、`docs/Phase_2/Phase2_STATUS.md` 和 M2 报告。
- 声衰减过阻尼和 high-mode acoustic 边界完成前，不声明 final M2 production pass，也不声明 Phase_3 Level C readiness。
