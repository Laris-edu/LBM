# Phase_2 Heat-Flux / tau32 闭合复核

**最后更新**：2026-06-11

本文固化当前 heat-flux collision 与 `tau32` 的理论口径，并分别复核 D2Q21/D2Q37 的 heat-flux scale、Galilean correction 和 D2Q37 high-mode spectral correction。本文只收敛 heat-flux/`tau32` 闭合口径，不声明无差别 final M2 production pass。（Phase_3 Level C 的启动口径不在本文，见 `docs/Phase_2/M2/M2_Critical_Decision.md` 第 5 节 `BOUNDED_PRODUCTION_GO`：紧致空气目标边界内已授权。）

## 1. 核心结论

`tau32` 是 Phase_2 热扩散的唯一 relaxation time 入口：

```text
alpha_lu = theta_transport_lu * (tau32 - 0.5)
tau32    = 0.5 + alpha_lu / theta_transport_lu
```

collision 内部的 `regularized_heat_flux_factor` 不是第二个独立热扩散系数；它是 regularized f/g projection 下的 raw central heat-flux post-collision retention：

```text
q_raw^target = h_family(tau32) * q_raw^pre
```

其中 `h_family(tau32)` 必须随 `tau32` 变化，以保证 P2-7 多 Pr 扫描中 `alpha_lu` 仍由 `tau32` 控制。原始 BGK 直觉会给出 `1 - 1/tau32`，baseline air 点约为 `-0.706`；当前实现不能直接使用该值，因为 collision 会丢弃 population nullspace、用最小范数 central-moment projection 重建 f/g heat flux，并且导出的 Fourier-law `q_lu` 还要经过 family-specific conductive moment factor。因此当前固化为 lattice-family 线性投影闭合：

```text
D2Q21: h(tau32) = -0.5467 + 0.949 * (tau32 - 0.5)
D2Q37: h(tau32) = -0.5030006782780277
                   + 0.7230829392328689 * (tau32 - 0.5)
```

这两个式子是 `tau32 -> heat-flux projection retention` 的当前理论/数值闭合边界：`tau32` 仍负责目标 `alpha_lu`，`h_family` 负责把 regularized projection 的 raw heat-flux 残留调到该 `alpha_lu`。

## 2. f/g 热流分配

Phase_2 当前气体自由度为：

```text
D = 2
S = 3
gamma = 1 + 2/(D + S) = 1.4
```

导热 heat flux 按焓贡献拆分到 f/g 两个通道：

```text
f_fraction = (D + 2) / (D + S + 2) = 4/7
g_fraction = S / (D + S + 2) = 3/7
```

该关系已固化在 `core/unit_mapping.py`：`heat_flux_f_fraction_from_degrees(D, S)` 返回理论值，`validate_unit_mapping()` 会拒绝不匹配 D/S 焓分配的 `regularized_heat_flux_f_fraction`。

## 3. Heat-Flux Scale 复核

`core.macroscopic.central_energy_flux_lu()` 返回 raw central total energy-flux moment；`GasSolver2D.get_heat_flux_lu()`、HDF5、P2-5 Fourier-law 和 Phase_3 handoff 使用 conductive `q_lu`：

```text
q_lu = conductive_heat_flux_moment_factor * q_raw
q_phys = q_lu * rho_scale * (dx_m/dt_s)^3
```

当前 `rho_scale * (dx_m/dt_s)^3 ~= 2.7899259259e9`。该 LU/SI scale 对 D2Q21/D2Q37 相同；不同的是 raw moment 到 conductive heat flux 的 projection/export factor：

| velocity set | `conductive_heat_flux_moment_factor` | baseline `h(tau32)` | 口径 |
|---|---:|---:|---|
| D2Q21 | `0.05192359403391186` | `-0.4649237356` | 低模态 physical-timestep 工程闭合；mode=2 high-mode 仍失败 |
| D2Q37 | `0.0422` | `-0.4406919095` | 低 k 长窗口 closure；输运候选 |

因此 Fourier-law 导出尺度不能再额外乘进 NSF acoustic attenuation target：`alpha_lu` 已经是 conductive convention 下的 `k/(rho cp)`，P2-5 已用同一 `q_lu` 定义复核热流幅值。

## 4. Galilean Correction 复核

背景速度下的热模态会在导出的 conductive heat flux 中暴露相位缺陷。当前修正只作用于导出 `q_lu`：

```text
q_lu = q_conductive + C_galilean * u * theta'
theta' = theta - theta_ref_lu
```

它不改变 collision 中的 `tau32`、`alpha_lu` 或 raw heat-flux retention。当前固化值为：

| velocity set | `conductive_heat_flux_galilean_correction_factor` | 复核边界 |
|---|---:|---|
| D2Q21 | `0.03272660408381829` | Mach 背景速度低模态热扩散/Fourier-law 通过；D2Q21 high-mode 不因此通过 |
| D2Q37 | `0.03835608923273733` | Mach `0.05` 背景速度热流虚部补偿；P2-9 真实 Galilean hard metrics 通过 |

D2Q37 的值来自 `64/mode1`、Mach `0.05` x 向热模态中 `heat_flux_ratio ~= 1.000000894 - 0.347875842 i` 的虚部补偿：

```text
ratio_extra = i * C_galilean * u_x / (k * kappa_lu)
```

该项是导出热流 Galilean phase correction，不得用于重调 `tau32` 或掩盖 P2-7 Pr 扫描。

## 5. D2Q37 High-Mode Spectral Correction

D2Q37 低 k closure 固化后，mode=2 high-mode 的 shear/thermal/Fourier-law 仍失败；直接回退 stress 或 heat-flux scalar 会破坏低 k 长窗口硬约束。因此当前只对周期谱高波数响应加 bounded multiplier：

```text
mu(kx, ky) = 4 sin^2(kx/2) + 4 sin^2(ky/2)
low threshold  = 0.019261093311212455  # 64x64 diagonal mode=1
high threshold = 0.038429439193539104  # 64x64 x/y mode=2
```

谱修正对 `mu <= low` 的 mode 不生效，对 `mu >= high` 的 mode 达到 target，中间用 smoothstep 过渡。当前 targets：

| 修正对象 | target |
|---|---:|
| nonequilibrium `Pi_xy` | `0.786` |
| nonequilibrium normal stress | `0.785` |
| collision raw heat-flux retention | `0.8512` |
| exported conductive `q_lu` | `0.3201` |

这说明 D2Q37 `64/mode1` x/y 热扩散和 P2-6 baseline acoustic target 不被 spectral correction 改写；`64/mode1` diagonal 正好处于 low threshold，也保持 low-k closure 口径。P2-9 masking check 已确认 correction 没有把 mode=2 背景声学误差伪装成通过，但 mode=2 背景声学仍失败，后续仍需单独诊断 high-mode acoustic 边界。

## 6. 固化到实现的约束

本轮已在 `core/unit_mapping.py` 固化以下不变量：

- `alpha_lu_from_tau32()` 与 `tau32_from_alpha_lu()` 明确 `alpha_lu <-> tau32` 的单入口关系；
- `regularized_heat_flux_factor_from_tau32()` 的注释明确 `h(tau32)` 是 projection retention，不是独立 diffusivity；
- `heat_flux_f_fraction_from_degrees()` 固化 `(D+2)/(D+S+2)`；
- `UnitMapping.to_metadata()` 输出 `heat_flux_tau32_relation`；
- P2-0 回归测试覆盖 D2Q21/D2Q37 的 `h(tau32)`、conductive moment factor、Galilean factor 和 D2Q37 spectral thresholds/targets。

## 7. 剩余风险

完成上述固化后，heat-flux/tau32 口径不再是未记录的隐式经验参数；但以下风险仍不解除：

- D2Q21 low-mode 通过不等价于 high-mode 或 final production pass；
- D2Q37 仍是 transport + acoustic-speed/gamma + Galilean candidate，不是 final M2 production pass；
- D2Q37 P2-6 acoustic attenuation 相对 matched NSF target 仍过阻尼约 `5.27x`；
- D2Q37 mode=2 背景声学失败边界仍需继续诊断；
- 后续若调整 `h(tau32)`、conductive factor、Galilean factor 或 spectral target，必须同步更新本文件、`core/unit_mapping.py`、P2-0 元数据/映射测试、`docs/Phase_2/Phase2_STATUS.md` 和 `docs/PROJECT_CONTEXT.md`。
