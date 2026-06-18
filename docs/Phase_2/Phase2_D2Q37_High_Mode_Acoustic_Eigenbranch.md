# D2Q37 High-Mode Acoustic Eigen-Branch Closure 推导

**最后更新**：2026-06-18  
**范围**：D2Q37 `64/mode2` high-mode acoustic speed/gamma 失败边界、独立 eigen-branch phase closure 与外推边界复核  
**结论口径**：本文记录 diagnostic closure 推导；默认 baseline 不变，不能声明 final M2 production pass；matched acoustic attenuation 仍是 GO-RISK。

## 1. 失败边界

`20260610T141926Z` 的 P2-9 high-mode acoustic diagnostic 显示，mode=2 背景声学在 high-mode transport dispersion correction 开/关下均失败：

```text
enabled:  speed error ~= 4.8987%, gamma error ~= 10.0373%
disabled: speed error ~= 2.5376%, gamma error ~= 5.1395%
```

2026-06-18 当前配置复核进一步确认：

```text
mode=2 no background:
  x/y speed error       ~= 4.70%
  diagonal speed error  ~= 8.66%
  no NaN, no clipping, no early invalid step
```

这不是稳定性 failure，也不是 diagonal low-mode heat-flux/phase correction 的遗漏；它是 high-mode acoustic eigen-branch 的相速闭合问题。

## 2. 为什么单 cell symbol 不够

已有 low-mode acoustic phase correction 使用单 cell collision Jacobian：

```text
A_cell(k) = S(k) C_cell
```

该 symbol 能描述 local collision 与 streaming，但不能描述 collision 内部的 D2Q37 周期谱 high-mode transport correction：

```text
stress/heat high-mode correction targets:
  shear_xy     = 0.786
  shear_normal = 0.785
  heat_ret     = 0.8512
  heat_export  = 0.3201
```

这些 correction 是按 Fourier Laplacian symbol 对整个周期场施加的。对 `mode=2`，真实动态 one-step operator 是：

```text
A_full(k) = F(k) P_high(k) S(k) C(k)
```

其中 `P_high(k)` 包含 stress/heat spectral response，`F(k)` 是 conservative high-wavenumber filter。若继续用 `A_cell(k)` 构造 acoustic projector，phase correction 会瞄准错误的 eigen-branch；这正是先前 scalar high-mode phase factor 对 diagonal mode=2 基本无效的原因。

## 3. Full-Modal Symbol

对目标 Fourier mode 直接构造真实周期 one-step modal symbol：

```text
for each population basis e_j:
  X_j(y,x) = X0 + eps * e_j * cos(kx*x + ky*y)
  run one GasSolver2D step with high-mode acoustic phase factors disabled
  A_full(k)[:,j] = modal_amplitude(step(X_j) - X0) / eps
```

modal amplitude 用项目现有约定：

```text
hat{X}(k) = 2 / (Nx Ny) * sum_{x,y} X(x,y) exp[-i(kx*x + ky*y)]
```

这样得到的 `A_full(k)` 包含：

- collision regularized stress/heat-flux；
- D2Q37 high-mode stress/heat spectral correction；
- diagonal low-mode correction 的非目标影响；
- streaming；
- conservative high-wavenumber filter。

## 4. Eigen-Branch Phase Closure

令：

```text
A_full v_i = lambda_i v_i
W = V^{-1}
P_i = v_i w_i^*
```

选择相速最接近目标声速的一对 acoustic eigen-branches：

```text
c_i = |arg(lambda_i)| / |k|
c_target = sqrt(gamma * theta_ref_lu)
```

对选中 branch 施加 phase-only multiplier：

```text
m_i(phi) = exp[i * (phi - 1) * arg(lambda_i)]
A_corrected = (I + sum_i (m_i - 1) P_i) A_full
```

其中 `phi` 是 diagnostic high-mode acoustic phase factor。该操作只改选中 acoustic eigen-branch 的相位；衰减幅值不按该闭合修复。

实现位置：

- `core/solver.py`
  - `_high_acoustic_fourier_modes`：只选中 mode=2 axis 与 mode=2 diagonal Laplacian symbol；
  - `_high_mode_modal_symbol`：用真实 periodic one-step finite difference 构造 `A_full(k)`；
  - `_high_mode_acoustic_phase_operator`：在 `A_full(k)` 的 acoustic eigen-branches 上构造 phase projector；
  - `_apply_high_mode_acoustic_phase_correction`：在 streaming 后、filter 前施加 correction。
- `core/unit_mapping.py`
  - `acoustic_phase_high_mode_factor`
  - `acoustic_phase_high_mode_diagonal_factor`

默认值仍为：

```text
acoustic_phase_high_mode_factor = 1.0
acoustic_phase_high_mode_diagonal_factor = 1.0
```

因此 baseline 不变。

## 5. 反推结果

当前 `64/mode2` diagnostic seed：

```text
axis high-mode factor      = 0.955
diagonal high-mode factor  = 0.918
```

动态 P2-6 high-mode smoke：

| direction | status | speed error | gamma error | attenuation error |
|---|---|---:|---:|---:|
| x | `PASSED` | `0.1197%` | `0.2392%` | `11.3577` |
| y | `PASSED` | `0.1197%` | `0.2392%` | `11.3577` |
| diagonal | `PASSED` | `0.3885%` | `0.7756%` | `10.8976` |

Combined result:

```text
P2-6 mode=2 x/y/diagonal status = PASSED
max speed error                 ~= 0.3885%
max gamma error                 ~= 0.7756%
direction difference            ~= 0.2689%
no NaN, no clipping, no early invalid step
```

参数敏感性：

```text
diagonal factor 1.000: speed error ~= 8.659%, gamma error ~= 18.068%
diagonal factor 0.955: speed error ~= 3.635%, gamma error ~= 7.403%
diagonal factor 0.930: speed error ~= 0.905%, gamma error ~= 1.819%
diagonal factor 0.918: speed error ~= 0.389%, gamma error ~= 0.776%
diagonal factor 0.910: speed error ~= 1.245%, gamma error ~= 2.475%
```

因此 diagonal high-mode acoustic 不是 diagonal low-mode branch 的延伸；它需要基于 full-modal symbol 的 eigen-branch phase closure。

## 6. 外推边界复核

复核脚本：

```text
python -m scripts.diagnose_phase2_high_mode_acoustic_boundary
```

最新默认边界 run：

```text
results/phase2_high_mode_acoustic_boundary/20260618T143220Z/summary.json
results/phase2_high_mode_acoustic_boundary/20260618T143220Z/High_Mode_Acoustic_Boundary_Report.md
```

该 run 使用 diagnostic seed：

```text
axis high-mode factor      = 0.955
diagonal high-mode factor  = 0.918
steps                      = 80
fit_start                  = 10
directions                 = x/y/diagonal
```

外推矩阵：

| case | category | status | speed error | gamma error | direction difference | attenuation error | 判读 |
|---|---|---:|---:|---:|---:|---:|---|
| `n32_mode1_equivalent_laplacian` | `N/mode` | `PASSED` | `0.3885%` | `0.7756%` | `0.2689%` | `11.3577` | 同一离散 Laplacian symbol 可复现 seed。 |
| `n64_mode2_seed` | `N/mode` | `PASSED` | `0.3885%` | `0.7756%` | `0.2689%` | `11.3577` | 原始校准点成立。 |
| `n64_mode1_low_mode_control` | `mode` | `PASSED` | `0.6995%` | `1.3940%` | `0.8484%` | `8.4240` | low-mode control 仍由既有 low-mode/diagonal correction 维持。 |
| `n64_mode3_out_of_scope` | `mode` | `FAILED` | `22.7946%` | `50.7851%` | `11.8190%` | `13.4720` | 当前 high-mode closure 只瞄准 mode=2 Laplacian，不可外推到 mode=3。 |
| `n64_mode2_pr_0p5` | `Pr` | `FAILED` | `9.8410%` | `20.6504%` | `9.2101%` | `9.6135` | 同一 phase seed 不随 `tau32/Pr` 外推。 |
| `n64_mode2_pr_2p0` | `Pr` | `FAILED` | `6.5747%` | `13.5816%` | `7.8249%` | `17.4491` | 同一 phase seed 不随 `tau32/Pr` 外推。 |
| `n64_mode2_mach_0p05_x` | `Mach/background` | `FAILED` | `4.8492%` | `9.9335%` | `5.3034%` | `11.3860` | 背景速度 x 方向下同一 seed 不外推。 |
| `n64_mode2_mach_0p05_diagonal` | `Mach/background` | `FAILED` | `8.8855%` | `18.5606%` | `9.0359%` | `12.4064` | 背景速度 diagonal 下同一 seed 不外推。 |

边界结论：

- 该 seed 是离散 Laplacian branch seed，不是 `mode_index=2` 字面常数；`32/mode1` 与 `64/mode2` 因具有同一 Laplacian symbol 而复现相同结果。
- `mode3` 直接失败，说明当前 high-mode phase closure 没有覆盖更高 wave-number branch。
- `Pr=0.5/2.0` 失败，说明 factor 需要随 `tau32/heat-retention` 重新推导，不能把 `axis=0.955, diagonal=0.918` 写成 Pr 无关常数。
- Mach `0.05` 背景速度 x/diagonal 均失败，说明当前 full-modal operator 的背景速度外推不足；背景流下 acoustic eigen-branch 需要独立处理。
- 复核过程中确认 seed 对 `tau32/heat-retention` 数值口径极敏感；baseline case 必须保持原 YAML 的 `alpha0_m2_s`，不能用 `nu0/Pr` 重新反算后当作同一基线。
- 所有通过/失败 case 均无 NaN、无 clipping、无 early invalid step；失败是 eigen-branch 相速/gamma 外推失败，不是稳定性或 positivity failure。
- attenuation 全部仍为 `~8x..17x` 量级过阻尼，继续保持 diagnostic / GO-RISK。

## 7. P2-9 语义拆分

`verification/galilean_consistency_measurement.py` 已拆分：

- `transport_dispersion_masking_status`：P2-9 hard masking 语义，只检查 low-mode acoustic 在 high-mode transport dispersion target 开/关下的 enabled/disabled 差异，避免 spectral transport correction 伪造 Galilean pass。
- `acoustic_eigenbranch_diagnostic_status`：high-mode acoustic eigen-branch diagnostic 语义，只记录 high-mode acoustic branch 是否被当前 diagnostic closure 修正；不参与 P2-9 transport masking hard gate。
- 兼容字段 `dispersion_masking_status` 当前等同 transport masking hard status；旧 high-mode acoustic enabled-only pass 不再被写成 transport masking failure。

默认 D2Q37 YAML 中 high-mode acoustic diagnostic directions 已扩展为 `x/y/diagonal`，但 high-mode phase factors 仍为 `1.0`，因此 baseline 不被打开。

## 8. 当前限制

该 closure 只修复 high-mode acoustic speed/gamma：

- acoustic attenuation 仍过阻尼约 `11x`，不能作为 hard pass；
- full-modal finite-difference operator 是 diagnostic spectral closure，不是 local production collision；
- 当前 seed 的外推边界已确认很窄：仅原始 Pr、无背景、目标 Laplacian branch 通过；
- 进入 production 前仍需随 `N/mode/Pr/Mach/background` 推导可泛化 closure，并继续完成 matched attenuation closure。

当前可更新结论：

```text
D2Q37 mode=2 axis/diagonal acoustic speed-gamma failure can be explained as
a high-mode acoustic eigen-branch phase error once the full periodic spectral
transport operator is included.

The required closure is independent from diagonal low-mode thermal/acoustic
correction and should remain diagnostic until attenuation and wider robustness
are resolved.
```
