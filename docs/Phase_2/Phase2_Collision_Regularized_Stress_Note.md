# Phase_2 Collision Regularized Stress / Heat-Flux Note

**最后更新**：2026-06-03

## 1. 目的

本文记录当前 `core/collision_smrt.py` 从 raw population scaffold 升级为 regularized central-Hermite/binomial stress/heat-flux collision 的实现口径、已验证效果和仍需推导固化的风险。

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
regularized_shear_normal_factor: 0.84
regularized_heat_flux_factor: -0.45
regularized_heat_flux_f_fraction: 0.5714285714285714
conductive_heat_flux_moment_factor: 0.05192359403391186
```

其中 `regularized_heat_flux_f_fraction=4/7` 对应 `D=2, S=3` 下按焓贡献分配 `f/g` 热流；`conductive_heat_flux_moment_factor` 用于把 raw central energy-flux moment 转换为 P2-5 和 Phase_3 handoff 使用的 conductive `q_lu`。这些系数是当前 D2Q21 physical-timestep mapping 下的工程闭合参数，并不应被解释为完整理论闭式推导已经完成。

## 3. 已验证效果

最新 physical-timestep run `20260603T143834Z` 中：

- P2-4 真实剪切波：`PASSED`。
- 三方向最大 `nu` 相对误差约 `0.242%`。
- P2-5 真实等压热扩散与 Fourier-law 热流：`PASSED`。
- 两方向最大 `alpha` 相对误差约 `2.022%`。
- Fourier-law 热流幅值误差约 `1.27e-6`。
- 无负温度、无 NaN、无 clipping。
- 质量、动量、选定中心总能量守恒测试继续通过。

这说明原 P2-4 负温度失稳主要来自 raw population 非平衡高阶噪声；原 P2-5 失败主要来自缺少 `g` 一阶内部能量通量、`f` 三阶平动能量通量和 conductive heat-flux 读数定义。当前实现已能在短时 C2 窗口内同时通过 P2-4/P2-5。

## 4. 仍需固化的问题

当前 P2-4/P2-5 通过仍是 physical-timestep baseline 下的短时工程验证，不是 final M2 production pass。后续仍需完成：

- 推导 `regularized_heat_flux_factor=-0.45` 与 `tau32`、D2Q21 moment closure 的关系；
- 推导 `conductive_heat_flux_moment_factor`，减少经验校准成分；
- 在更长时间窗口、更高模态、不同振幅和背景速度下复核 P2-4/P2-5；
- 将 P2-7 Pr 扫描升级为真实 `nu/alpha/Pr` 联合测量；
- 将 P2-6/P2-9 升级为真实 acoustic/Galilean production physics 测量。

## 5. 维护规则

- 不使用 clipping、floor 或 positivity repair 来制造 pass。
- 若调整 stress/heat-flux correction factor，必须同步更新 `core/unit_mapping.py`、HDF5 metadata、`docs/Phase_2/Phase2_STATUS.md` 和 M2 报告。
- P2-6/P2-7/P2-9 production physics 完成前，不声明 final M2 production pass，也不声明 Phase_3 Level C readiness。

