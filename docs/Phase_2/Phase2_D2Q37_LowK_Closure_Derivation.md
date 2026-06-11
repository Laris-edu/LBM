# Phase_2 D2Q37 低 k 长窗口闭合推导

**最后更新**：2026-06-11

本文以 D2Q37 `20260607T073921Z` 失败诊断为边界，重新推导当前 D2Q37 stress projection 与 heat-flux closure 的低 k 长窗口口径。2026-06-08 追加 mode=2 high-mode dispersion correction 复核口径。本文只覆盖 D2Q37 fallback 的输运闭合，不声明 final M2 production pass，不启动 Phase_3。

## 1. 边界条件

`20260607T073921Z` 已确认旧 D2Q37 closure 是波数/窗口依赖闭合：

- 旧 `32/mode1/24 steps` 与 `64/mode2` 属于较高波数短窗口，不代表 `64/mode1` hydrodynamic 极限。
- 旧 `64/mode1` shear 长窗口约为目标 `2.09x`；关闭 high-wavenumber filter 后仍同阶失败。
- 旧 `64/mode1` thermal 长窗口 heat-flux ratio 实部约 `0.33`，conductive scale 不能外推。

因此本轮硬约束改为：

```text
shear:   64/mode1, steps=240, fit_start=10, directions=[x,y,diagonal]
thermal: 64/mode1, steps=320, fit_start=10, directions=[x,y]
Pr:      targets=[0.5, 0.7061328707, 1.0, 2.0],
         shear 240 steps + thermal 320 steps
```

验收量仍使用现有 P2 后处理定义：

```text
nu_measured    = shear_decay_rate / k^2
alpha_measured = thermal_decay_rate / k^2
heat_flux_ratio = q_hat / (-i k kappa_lu theta_hat)
```

其中 exported `q_lu` 是 `raw central energy flux * conductive_heat_flux_moment_factor` 后的导热热流。

## 2. Stress Projection

当前 `core/collision_smrt.py` 的二阶中心应力 post-collision 残留为：

```text
Pi_xy^post  = regularized_shear_xy_factor     * (1 - 1/tau21) * Pi_xy^neq
Pi_dev^post = regularized_shear_normal_factor * (1 - 1/tau21) * Pi_dev^neq
```

旧短窗口因子：

```text
regularized_shear_xy_factor     = 0.6870275878906249
regularized_shear_normal_factor = 0.7061810302734374
```

在低 k 长窗口下给出 `nu≈0.00615481`，约为目标 `2.09x`。以 `64/mode1` 长窗口重新约束后得到：

```text
regularized_shear_xy_factor     = 0.8739
regularized_shear_normal_factor = 0.9000
```

验证结果：

| 方向 | `nu_measured_lu` | signed error |
|---|---:|---:|
| x | `0.002943476133` | `-9.30e-5` |
| y | `0.002943476131` | `-9.30e-5` |
| diagonal | `0.002935441003` | `-0.2823%` |

三方向最大相对误差约 `0.2823%`，direction difference 约 `0.2730%`，满足低 k 长窗口硬约束。

## 3. Heat-Flux Closure

当前 heat-flux collision 将 raw central total energy flux 保留为：

```text
q_raw^target = regularized_heat_flux_factor(tau32) * q_raw^pre
```

并按 `regularized_heat_flux_f_fraction=4/7` 分配到 `f` 三阶中心平动能量通量与 `g` 一阶中心内部能量通量。导出的 Fourier-law 热流再乘：

```text
conductive_heat_flux_moment_factor
```

旧 D2Q37 短窗口口径：

```text
regularized_heat_flux_factor = -0.3936302646597617
                               + 0.17313512881054283 * (tau32 - 0.5)
conductive_heat_flux_moment_factor = 0.013426658536906303
```

低 k 长窗口下，先固定 baseline air 点 `Pr=0.7061328707`，以 `alpha_measured≈alpha_target` 反推：

```text
regularized_heat_flux_factor ≈ -0.4407
conductive_heat_flux_moment_factor ≈ 0.0422
```

baseline 验证：

| `h` | conductive factor | `alpha_measured_lu` | alpha signed error | heat-flux ratio | heat-flux error |
|---:|---:|---:|---:|---:|---:|
| `-0.4407` | `0.0421` | `0.004163249324` | `-0.1339%` | `0.99747` | `0.2530%` |
| `-0.4407` | `0.0423` | `0.004163249324` | `-0.1339%` | `1.00221` | `0.2208%` |
| `-0.4415` | `0.0422` | `0.004109857020` | `-1.4147%` | `0.99941` | `0.0593%` |

为保持 P2-7 多 Pr 长窗口硬约束，对四个 Pr 点分别反推 `h(tau32)`，并拟合线性式：

| `Pr_target` | `tau32` | chosen `h` | alpha signed error | heat-flux error |
|---:|---:|---:|---:|---:|
| `0.5` | `0.621696329455` | `-0.4150` | `0.2725%` | `1.3918%` |
| `0.7061328707` | `0.586170984597` | `-0.4407` | `-0.1339%` | `<0.3%` |
| `1.0` | `0.560848164727` | `-0.4590` | `0.3277%` | `0.9949%` |
| `2.0` | `0.530424082364` | `-0.4810` | `3.9525%` | `2.1464%` |

得到新的 D2Q37 low-k closure：

```text
regularized_heat_flux_factor =
    -0.5030006782780277
    + 0.7230829392328689 * (tau32 - 0.5)

conductive_heat_flux_moment_factor = 0.0422
conductive_heat_flux_galilean_correction_factor = 0.0
```

用该线性式执行 P2-7 低 k 长窗口扫描：

| `Pr_target` | resolved `h` | `Pr_measured` | Pr error | alpha error | heat-flux error |
|---:|---:|---:|---:|---:|---:|
| `0.5` | `-0.415004138682` | `0.4970734128` | `0.5853%` | `0.2677%` | `1.3915%` |
| `0.7061328707` | `-0.440691909456` | `0.7032472584` | `0.4087%` | `0.1210%` | `0.0157%` |
| `1.0` | `-0.459002408480` | `0.9900663041` | `0.9934%` | `0.3223%` | `0.9950%` |
| `2.0` | `-0.481001543379` | `1.907841901` | `4.6079%` | `3.9458%` | `2.1465%` |

P2-7 低 k 长窗口状态为 `PASSED`；baseline Pr error 约 `0.4087%`，最大 Pr error 约 `4.6079%`。

## 4. 背景速度 Galilean Heat Flux

低 k 零背景 closure 不能自动保证背景速度下的导热热流相位。D2Q37 `Mach=0.05` 背景速度复核显示：

```text
heat_flux_ratio_x ≈ 1.000000894 - 0.347875842 i
```

实部已经满足 Fourier-law 幅值，失败来自虚部相位项。当前导出热流实现允许加：

```text
q_lu = q_conductive + C_galilean * u * theta'
```

对 x 方向热模态，有：

```text
ratio_extra = C_galilean * u_x / (-i k kappa_lu) = i * C_galilean * u_x / (k kappa_lu)
```

令虚部补偿 `+0.347875842 i`，并取 `k=2*pi/64`、`u_x=0.05*sqrt(gamma*theta_ref_lu)=0.0130125`、`kappa_lu=0.014614060419233948`，得到：

```text
C_galilean = 0.03835608923273733
```

单独复核背景速度场景：

| 方向 | alpha error | heat-flux ratio | heat-flux error |
|---|---:|---:|---:|
| x | `0.5707%` | `1.000000894 - 8.97e-13 i` | `8.94e-7` |
| y | `0.1963%` | `0.999868471` | `0.0132%` |

背景速度 P2-4/P2-5/Fourier-law paired scenario 状态为 `PASSED`。

## 5. 固化参数

本轮将以下参数写入 `core/unit_mapping.py` 与 `configs/gas_air_10k_d2q37_physical_timestep.yaml`：

```yaml
regularized_shear_xy_factor: 0.8739
regularized_shear_normal_factor: 0.9
regularized_heat_flux_factor: auto_d2q37_tau32_linear
regularized_heat_flux_f_fraction: 0.5714285714285714
conductive_heat_flux_moment_factor: 0.0422
conductive_heat_flux_galilean_correction_factor: 0.03835608923273733
```

```text
auto_d2q37_tau32_linear:
  intercept = -0.5030006782780277
  slope     =  0.7230829392328689
```

同时，D2Q37 YAML 的 P2-4/P2-5/P2-7 默认动态窗口已从旧 `32/mode1/24 steps` 改为本文的低 k 长窗口硬约束。

## 6. High-Mode Dispersion Correction

低 k closure 固化后，run `20260607T140122Z` 表明 `d2q37_long_window`、`d2q37_background_mach_0p05` 和 `d2q37_pr_long_window` 已通过，唯一剩余 required failure 为 `d2q37_high_mode_m2`：

| 指标 | 失败值 |
|---|---:|
| mode=2 shear 最大误差 | `160.34%` |
| mode=2 thermal alpha 误差 | `315.24%` |
| mode=2 Fourier-law 热流误差 | `210.46%` |

排查结论是：保守 high-wavenumber filter 只提供小的正耗散，关闭 filter 后 mode=2 仍为负扩散；根因是 D2Q37 低 k closure 的高波数 dispersion 响应。单独回退 `regularized_shear_xy_factor`、`regularized_shear_normal_factor` 或 heat-flux scalar 会破坏本文低 k 硬约束，因此修复采用周期谱 correction，在离散 Laplacian 符号上保持低 k 不变、只压低高模态响应。

固化参数如下：

| 项目 | 当前值 |
|---|---:|
| `dispersion_correction_enabled` | `true` |
| low Laplacian threshold | `0.019261093311212455` |
| high Laplacian threshold | `0.038429439193539104` |
| `regularized_shear_xy_dispersion_target` | `0.786` |
| `regularized_shear_normal_dispersion_target` | `0.785` |
| `regularized_heat_flux_dispersion_target` | `0.8512` |
| `conductive_heat_flux_dispersion_target` | `0.3201` |

该 correction 分别作用于：

- collision 内部 nonequilibrium stress；
- collision 内部 raw central total heat-flux retention；
- 导出的 conductive `q_lu`。

run `20260608T063346Z` 复核结果：

| 场景 | 状态 | 关键结果 |
|---|---|---|
| `d2q37_long_window` | `PASSED` | P2-4 最大误差约 `1.3635%`，P2-5 alpha 误差约 `0.1210%`，Fourier-law 误差约 `0.0157%` |
| `d2q37_high_mode_m2` | `PASSED` | mode=2 shear 最大误差约 `0.4068%`，thermal alpha 误差约 `0.2827%`，Fourier-law 误差约 `0.0813%` |
| `d2q37_background_mach_0p05` | `PASSED` | P2-4 最大误差约 `1.3528%`，P2-5 alpha 误差约 `0.5707%`，Fourier-law 误差约 `0.0132%` |
| `d2q37_pr_long_window` | `PASSED` | baseline Pr 误差约 `0.4087%`，全扫描最大 Pr 误差约 `4.6079%` |

## 7. 剩余风险

低 k 长窗口和 mode=2 high-mode 通过是 D2Q37 输运候选的必要条件，不等价于 final M2 production pass。固化后仍必须完成：

- P2-6 acoustic attenuation 相对 matched NSF target 的过阻尼来源；
- P2-9 后续 diagonal acoustic wave direction 统计；
- heat-flux collision 与 `tau32`、Galilean correction、spectral correction 的理论关系复核。

如果后续声学或更宽网格/波数复核失败，应记录为新的剩余风险；不得回退到旧短窗口标定来制造 pass。
