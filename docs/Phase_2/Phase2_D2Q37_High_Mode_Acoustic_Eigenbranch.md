# D2Q37 High-Mode Acoustic Eigen-Branch Closure 推导

**最后更新**：2026-06-19
**范围**：D2Q37 `mode=2/3` high-mode acoustic speed/gamma 失败边界、独立 eigen-branch phase closure 与 `Pr/tau32`、Mach/background、wave-number branch 外推复核
**结论口径**：本文记录 diagnostic closure 推导；默认 baseline 仍保持 `specified` policy，不声明 final M2 production pass；matched acoustic attenuation 仍是 GO-RISK。

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
A_full(k; tau32, U0) v_i = lambda_i v_i
W = V^{-1}
P_i = v_i w_i
```

其中 `A_full` 是上节的真实周期 one-step modal symbol，已经包含当前 `tau32/Pr`、背景速度 `U0`、spectral stress/heat high-mode correction、streaming 和 filter。

### 4.1 `specified` seed policy

旧 diagnostic seed 只选择相速最接近目标声速的一对 acoustic eigen-branches：

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

该 policy 对应：

```text
acoustic_phase_high_mode_policy = specified
acoustic_phase_high_mode_factor = axis seed
acoustic_phase_high_mode_diagonal_factor = diagonal seed
```

默认 YAML 仍使用 `specified` 且两个 high-mode factor 均为 `1.0`，因此 baseline 不变。

### 4.2 `full_modal_target` branch policy

外推失败说明 `phi` 不能写成 Pr/Mach/wave-number 无关常数。新的 diagnostic closure 直接把每个被观测到的 acoustic eigen-branch 相位移动到目标 branch：

```text
theta_i      = Arg(lambda_i)
theta_bg     = k · U0
theta_i^I    = theta_i + theta_bg
s_i          = sign(theta_i^I)
c0           = sqrt(gamma * theta0)
theta_i^*    = -theta_bg + s_i * c0 * |k|
M_i          = exp[i * (theta_i^* - theta_i)]
A_corrected  = (I + sum_i (M_i - 1) P_i) A_full
```

这里 `theta_i^I` 是扣除背景平流后的 intrinsic acoustic branch phase；`theta_i^*` 是同一 branch 在当前背景速度下的目标 lab-frame phase。该形式使 closure 显式随 `tau32/Pr`、`U0` 和 `k` 变化，而不是复用固定 factor。

branch 选择不能只按相速最近排序，因为高维 D2Q37 symbol 中存在幅值极小、宏观不可观测但相速偶然接近的数值 branch。当前实现先过滤 `|lambda_i| <= 1e-6`，再用压力和纵向速度可观测性筛选 acoustic branch：

```text
rho'_i  = sum_a f'_{i,a}
u'_i    = (sum_a c_a f'_{i,a} - U0 rho'_i) / rho0
E'_i    = 0.5 * sum_a f'_{i,a} |c_a-U0|^2 + sum_a g'_{i,a}
p'_i    = 2 E'_i / (D+S)
O_i     = sqrt(|p'_i/p0|^2 + |u'_{i,parallel}/c0|^2) / ||v_i||
```

每个正/负 intrinsic branch sign 内，先保留接近该 sign 最大可观测性的 branch，再按相速误差选择。这样可以排除背景流下的 near-zero ghost/numerical eigenvalue，并把 correction 作用到 acoustic 初始条件真正激发的 branch。

### 4.3 wave-number branch family

`specified` policy 保持旧范围：只选中 calibration high Laplacian 的 axis branch 与对应 diagonal branch。

`full_modal_target` policy 改为 diagnostic branch family：设 high-mode seed 的 axis wavenumber 为

```text
k_h = 2 asin(sqrt(mu_h) / 2)
```

则选取满足

```text
mu(kx,ky) >= mu_h
max(|kx|, |ky|) <= 1.5 k_h
```

的 Fourier modes。对当前 `64/mode2` seed，这覆盖 `mode=2` 与相邻 `mode=3` branch；对 `32/mode1` 等同 Laplacian case 仍保持同一 seed branch。该范围仍是 diagnostic branch-family 外推，不是全波数 production closure。

实现位置：

- `core/solver.py`
  - `_high_acoustic_fourier_modes`：`specified` 只选中 mode=2 axis 与 mode=2 diagonal Laplacian symbol；`full_modal_target` 选中相邻 high-mode branch family；
  - `_high_mode_modal_symbol`：用真实 periodic one-step finite difference 构造 `A_full(k)`；
  - `_high_mode_acoustic_phase_operator`：在 `A_full(k)` 的 acoustic eigen-branches 上构造 phase projector；
  - `_acoustic_eigenprojector_target_phase_correction`：实现随 `tau32/Pr`、背景相位和 wave-number branch 变化的 target-phase closure；
  - `_apply_high_mode_acoustic_phase_correction`：在 streaming 后、filter 前施加 correction。
- `core/unit_mapping.py`
  - `acoustic_phase_high_mode_policy`
  - `acoustic_phase_high_mode_factor`
  - `acoustic_phase_high_mode_diagonal_factor`

默认值仍为：

```text
acoustic_phase_high_mode_policy = specified
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
python -m scripts.diagnose_phase2_high_mode_acoustic_boundary --closure-policy full_modal_target
```

### 6.1 `specified` seed 边界

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

`specified` 边界结论：

- 该 seed 是离散 Laplacian branch seed，不是 `mode_index=2` 字面常数；`32/mode1` 与 `64/mode2` 因具有同一 Laplacian symbol 而复现相同结果。
- `mode3` 直接失败，说明当前 high-mode phase closure 没有覆盖更高 wave-number branch。
- `Pr=0.5/2.0` 失败，说明 factor 需要随 `tau32/heat-retention` 重新推导，不能把 `axis=0.955, diagonal=0.918` 写成 Pr 无关常数。
- Mach `0.05` 背景速度 x/diagonal 均失败，说明固定 phase seed 的背景速度外推不足；背景流下 acoustic eigen-branch 需要按 `k·U0` 独立处理。
- 复核过程中确认 seed 对 `tau32/heat-retention` 数值口径极敏感；baseline case 必须保持原 YAML 的 `alpha0_m2_s`，不能用 `nu0/Pr` 重新反算后当作同一基线。
- 所有通过/失败 case 均无 NaN、无 clipping、无 early invalid step；失败是 eigen-branch 相速/gamma 外推失败，不是稳定性或 positivity failure。
- attenuation 全部仍为 `~8x..17x` 量级过阻尼，继续保持 diagnostic / GO-RISK。

### 6.2 `full_modal_target` 外推 smoke

2026-06-19 手动 smoke 使用同一测量窗口：

```text
closure policy = full_modal_target
steps          = 80
fit_start      = 10
directions     = x/y/diagonal
```

该 policy 不再使用固定 `axis/diagonal` phase factor 作为闭合目标，而是对每个 case 的 `A_full(k; tau32,U0)` 重选 acoustic eigen-branch 并外推到目标 branch phase。

| case | category | status | speed error | gamma error | direction difference | attenuation error | 判读 |
|---|---|---:|---:|---:|---:|---:|---|
| `baseline_n64_mode2` | `N/mode` | `PASSED` | `0.4301%` | `0.8584%` | `0.5119%` | `11.3179` | 原始 mode=2 seed branch 仍通过。 |
| `pr_0p5_n64_mode2` | `Pr` | `PASSED` | `0.5008%` | `0.9992%` | `0.5948%` | `9.7221` | branch target 随 `tau32/Pr` 重选后通过。 |
| `pr_2p0_n64_mode2` | `Pr` | `PASSED` | `0.3228%` | `0.6446%` | `0.3857%` | `17.0026` | branch target 随 `tau32/Pr` 重选后通过。 |
| `mach_0p05_x_n64_mode2` | `Mach/background` | `PASSED` | `0.4531%` | `0.9041%` | `0.5348%` | `11.8920` | 目标相位显式扣除 `k·U0` 后通过。 |
| `mach_0p05_diag_n64_mode2` | `Mach/background` | `PASSED` | `0.4625%` | `0.9228%` | `0.5382%` | `11.7225` | diagonal 背景流下通过。 |
| `mode3_n64` | `mode` | `PASSED` | `0.4538%` | `0.9056%` | `0.3932%` | `12.3249` | 相邻 high-mode branch family 覆盖 mode=3。 |

`full_modal_target` 边界结论：

- speed/gamma failure 可由独立 high-mode acoustic eigen-branch target closure 修复，不应继续通过 diagonal low-mode factor 调参解决。
- 该 smoke 只覆盖相邻 wave-number branch、`Pr={0.5, 2.0}` 和 Mach `0.05` 两类背景方向；还不是宽网格生产证明。
- attenuation 仍为 `~9x..17x` 过阻尼，说明当前 closure 只修相位/声速，不修振幅衰减。
- full-modal finite-difference symbol 仍是周期谱 diagnostic closure，不是 local production collision。

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
- `full_modal_target` 已给出随 `Pr/tau32`、Mach/background 和相邻 wave-number branch 变化的可运行 diagnostic closure，但仅完成 smoke 级复核；
- 进入 production 前仍需更宽 `N/mode/Pr/Mach/background` 网格、localizable collision 形式，并继续完成 matched attenuation closure。

当前可更新结论：

```text
D2Q37 mode=2/3 axis/diagonal acoustic speed-gamma failure can be explained
as a high-mode acoustic eigen-branch phase error once the full periodic
spectral transport operator, tau32/Pr, background phase, and wave-number
branch are included.

The required closure is independent from diagonal low-mode thermal/acoustic
correction and should remain diagnostic until attenuation and wider robustness
are resolved.
```
