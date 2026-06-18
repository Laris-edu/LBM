# Phase_2 D2Q37 Acoustic Attenuation Diagnosis

**最后更新**：2026-06-16  
**范围**：D2Q37 P2-6 声衰减相对 matched NSF target 过阻尼来源诊断  
**结论口径**：本文是诊断报告，不声明 final M2 production pass；2026-06-15 已完成参数化改造，2026-06-16 已执行 trace / bulk + heat-retention 联合扫描，但默认 production-candidate baseline 行为保持不变。

## 1. 问题概述

D2Q37 在 P2-6 真实 periodic acoustic eigenmode 测量中，声速、由声速反推的 `gamma` 和方向差异已通过 hard gate，但声衰减相对 matched linearized NSF target 显著过阻尼。

最新主线 run `20260610T141926Z` 的记录为：

```text
acoustic_attenuation_measured_lu  ~= 1.393385e-4
acoustic_attenuation_reference_lu =  2.22224320740558e-05
relative_error                   ~= 5.270175
measured/reference               ~= 6.270175
```

注意：文档中常写的 `5.27x` 是 `abs(measured/reference - 1)` 的 relative error 口径；若按衰减率倍数看，当前 measured 约为 reference 的 `6.27x`。

## 2. Matched Target 口径

当前声衰减 reference 已按 `D=2, S=3`、`bulk_viscosity_policy=diagnostic_zero` 和 D2Q37 conductive heat-flux convention 固化。小波数 linearized NSF 振幅衰减率为：

```text
sigma_a = Gamma_a * k^2
Gamma_a = 0.5 * [nu_L + (gamma - 1) * alpha]
nu_L    = nu_b + 2*(D - 1)/D * nu
```

当前配置下：

```text
D = 2
S = 3
gamma = 1.4
nu_b_lu = 0
nu_L = nu
Gamma_a = 0.5*nu_lu + 0.2*alpha_lu
```

数值为：

```text
nu_lu    = 0.00294375
alpha_lu = 0.0041688329803125
k        = 2*pi/64
target   = 2.22224320740558e-05
```

因此，当前主要问题不是 target 推导错误，而是 D2Q37 collision / closure 对 acoustic 模态产生了额外阻尼。

## 3. 已排查因素

### 3.1 拟合窗口

P2-6 pressure amplitude 的指数衰减拟合不是完全干净的单指数，拟合窗口会改变 measured attenuation。例如 `10..80`、`10..240` 和若干晚窗口给出的衰减率不同。

但是，直接构造 `64/mode1` 的线性 Fourier symbol 后，真实 acoustic eigenvalue 本身也已经明显过阻尼：

```text
linear acoustic sigma ~= 1.3269e-4
sigma/reference       ~= 5.97
```

判定：拟合窗口不是根因，只是会扰动 summary 中的最终 measured 值。

### 3.2 High-Wavenumber Filter

`64/mode1` 下 conservative biharmonic filter 的一步阻尼量约为 `6e-7`，远小于额外声衰减的 `~1e-4` 量级。

判定：filter 不是主因。

### 3.3 D2Q37 Spectral Dispersion Correction

当前 D2Q37 high-mode spectral correction 对 `64/mode1` 基本不生效。关掉 correction 后，低模态 P2-6 声衰减变化可以忽略。

判定：spectral correction 不是低模态 P2-6 过阻尼主因。

### 3.4 Trace / Bulk Stress Closure

历史 production collision 中，二阶非平衡 trace stress 被直接隐式清零；2026-06-15 后该行为已改成显式 `trace_bulk_policy=current_zero` 默认分支：

```python
if trace_bulk_policy == "current_zero":
    trace_post = np.zeros_like(trace_pre)
```

这与 unit mapping 中 `diagnostic_zero => nu_b_lu=0, tau22=0.5` 的 matched NSF 声衰减 target 口径不一致。

诊断中把 trace 改为按 `tau22` 处理后，P2-6 声衰减显著改善：

```text
P2-6 attenuation measured: 1.393e-4 -> 3.91e-5
attenuation ratio:         6.27     -> 1.76
```

判定：trace / bulk closure 是过阻尼的主要来源。

### 3.5 Heat-Flux Retention / h(tau32)

trace 修复后，P2-6 声衰减显著改善，但 P2-5 和 P2-7 会失败。这说明当前 D2Q37 `auto_d2q37_tau32_linear` heat-flux retention 曲线，是和旧 trace 清零 closure 一起标定出来的。

判定：trace closure 改变后，热扩散和 Pr 扫描需要同步耦合标定；`h(tau32)` 不能作为独立声衰减旋钮。

## 4. 直接修复候选验证

### 4.1 只改 trace 为 tau22

候选：

```text
trace_policy = tau22
trace_scale  = 1.0
heat_line    = current
```

动态确认结果：

```text
P2-6: PASSED
attenuation_ratio          ~= 1.759
attenuation_relative_error ~= 0.759

P2-5: FAILED
alpha_relative_error ~= 0.1487

P2-7: FAILED
baseline_pr_relative_error ~= 0.1260
max_pr_relative_error      ~= 0.4644
```

判定：该候选虽能大幅改善声衰减，但会回退 P2-5/P2-7，不能直接落地。

### 4.2 增大 trace scale

候选：

```text
trace_policy = tau22
trace_scale  = 1.4
heat_line    = current
```

线性符号诊断中该候选的 acoustic error 较小，但真实动态确认失败：

```text
P2-5: FAILED
P2-6: FAILED
P2-7: FAILED
attenuation_ratio ~= -10250
```

判定：trace over-scaling 在真实 `64/mode1` 演化中失稳，不能用于 production。

### 4.3 单独调 heat-flux retention

局部调整 `h(tau32)` 可以让部分 P2-5 窗口通过，但不能同时保持：

- P2-5 热扩散；
- P2-7 多 Pr 点扫描；
- P2-6 acoustic attenuation；
- P2-6 声速 / gamma。

判定：单独重调 heat-flux retention 不能形成安全修复组合。

## 5. 为什么没有可直接落地的安全修复组合

当前排查说明：

- 声衰减过阻尼主要来自 trace / bulk stress closure；
- 现有 D2Q37 heat-flux retention 曲线与旧 trace 清零 closure 耦合；
- 只修 trace 会破坏 P2-5 / P2-7；
- 只调 `h(tau32)` 不能同时保证声衰减、热扩散和 Pr 扫描；
- trace over-scaling 虽可让 linear symbol 接近 target，但真实动态会失稳；
- 符号诊断通过不等价于真实 P2-5 / P2-6 / P2-7 动态通过。

因此，当前没有找到可直接落地的安全修复组合。D2Q37 声衰减仍应保持 diagnostic / GO-RISK，不应升级为 hard pass。2026-06-15 的代码改动只完成 trace / bulk 与 heat-retention 的显式参数化，为联合扫描提供入口；默认 `current_zero + auto_d2q37_tau32_linear` 行为未变。

2026-06-16 联合扫描进一步确认：局部 affine `h(tau32)` 网格可以让部分 `tau22 trace_scale` 候选通过 linear symbol gate，但这些候选在真实 P2-5/P2-6/P2-7 动态复核中全部失败；首选候选加跑 P2-9/high-mode 也失败。因此，当前问题不是缺少一个更细的 affine 单点，而是 symbol 层匹配与真实演化稳定性之间存在缺口。

继续复盘后，直接机制已定位：当前 `bulk_viscosity_policy=diagnostic_zero` 使 `tau22=0.5`，因此 `tau22` trace branch 的实际 post factor 为：

```text
trace_post = trace_scale * (1 - 1/tau22) * trace_pre
           = -trace_scale * trace_pre
```

也就是说，`trace_scale>1` 不是温和增强 bulk relaxation，而是把非流体 trace ghost mode 反号并放大。完整 one-step symbol 显示：

```text
trace_scale=1.4:
  k=0    max |lambda| ~= 1.400000
  mode1  max |lambda| ~= 1.385198

trace_scale=1.45:
  k=0    max |lambda| ~= 1.450000
  mode1  max |lambda| ~= 1.434758
```

最大特征向量主要是 trace stress ghost：在 `k=0` 下守恒量、pressure 和 theta 对 eigenvector norm 的占比约 `1e-9`，而 trace stress 占比约 `4.014`。P2-5 x-direction 短演化也验证了这一点：

```text
trace_scale=1.4:
  trace_max: step 10 ~= 1.03e-8, step 40 ~= 1.84e-4
  first_invalid_step = 74, theta_min < 0

trace_scale=1.45:
  trace_max: step 10 ~= 1.41e-8, step 40 ~= 7.20e-4
  first_invalid_step = 67, theta_min < 0
```

因此，2026-06-16 的 false positives 是 hydrodynamic acoustic/thermal eigenvalue 局部匹配掩盖了低 k trace ghost instability。诊断脚本已加入 low-k full-symbol ghost stability gate；后续 `candidate_symbol_pass` 必须同时通过 hydrodynamic error 和 ghost stability。

随后诊断脚本的流程已进一步收紧：动态确认阶段只接收 `candidate_symbol_pass=True` 的候选；若没有候选同时满足 hydrodynamic acoustic/thermal symbol 与 low-k ghost stability，则不启动 P2-5/P2-6/P2-7/P2-9 动态复核。脚本也新增了显式 affine intercept/slope 网格入口，用于复现 heat-retention curve 局部扫描。

## 6. 已新增诊断工具

新增脚本：

```text
scripts/diagnose_phase2_d2q37_acoustic_attenuation.py
```

用途：

- 扫描 trace closure 策略；
- 扫描 D2Q37 `h(tau32)` heat-flux line / curve；
- 用 linear Fourier symbol 快速评估 acoustic / thermal eigenvalue；
- 可选 `--dynamic` 跑慢速 P2-5 / P2-6 / P2-7 动态确认；
- 可选 `--include-p2-9` 与 `--include-high-mode` 扩展到背景速度声学和 high-mode acoustic 诊断。

运行方式：

```text
python -m scripts.diagnose_phase2_d2q37_acoustic_attenuation
python -m scripts.diagnose_phase2_d2q37_acoustic_attenuation --dynamic --max-dynamic-candidates 2
python -m scripts.diagnose_phase2_d2q37_acoustic_attenuation --symbol-only --trace-bulk-policy current_zero tau22 --trace-bulk-scale-grid 1.0 --heat-curve-type affine --heat-curve-coefficients -0.5030006782780277 0.7230829392328689
```

已生成诊断结果：

```text
results/phase2_d2q37_acoustic_attenuation_diagnostic/20260611T074941Z
results/phase2_d2q37_acoustic_attenuation_diagnostic/20260611T074321Z
results/phase2_d2q37_acoustic_attenuation_diagnostic/20260615T063832Z
results/phase2_d2q37_acoustic_attenuation_diagnostic/20260616T065526Z
results/phase2_d2q37_acoustic_attenuation_diagnostic/20260616T070540Z
results/phase2_d2q37_acoustic_attenuation_diagnostic/20260616T071505Z
results/phase2_d2q37_acoustic_attenuation_diagnostic/20260616T073305Z
results/phase2_d2q37_acoustic_attenuation_diagnostic/20260616T074540Z
results/phase2_d2q37_acoustic_attenuation_diagnostic/20260616T074949Z
results/phase2_d2q37_acoustic_attenuation_diagnostic/20260616T075841Z
```

快速符号扫描最新 run `20260611T074941Z` 中，最佳候选仍未达到 symbol pass：

```text
trace_policy = tau22
trace_scale  = 1.4
heat_line    = current

symbol_transport_error_max ~= 0.0635
baseline_acoustic_error_n64 ~= 0.1086
candidate_symbol_pass = false
```

动态确认 run `20260611T074321Z` 中：

```text
current_zero + current:
  P2-5 PASSED
  P2-6 PASSED
  P2-7 PASSED
  attenuation_ratio ~= 6.27

tau22 trace_scale=1.4 + current:
  P2-5 FAILED
  P2-6 FAILED
  P2-7 FAILED
```

另行确认 `tau22 trace_scale=1.0 + current`：

```text
P2-6 PASSED, attenuation_ratio ~= 1.759
P2-5 FAILED
P2-7 FAILED
```

2026-06-15 参数化后执行的轻量 symbol-only CLI 验证 `20260615T063832Z` 只覆盖 `current_zero/tau22`、`trace_scale=1.0` 与当前 affine heat curve，用于确认新配置路径可运行，不作为 production 候选：

```text
tau22 + current affine:
  symbol_transport_error_max ~= 0.0681
  baseline_acoustic_error_n64 ~= 0.8060
  candidate_symbol_pass = false

current_zero + current affine:
  symbol_transport_error_max ~= 0.0559
  baseline_acoustic_error_n64 ~= 4.9709
  candidate_symbol_pass = false
```

2026-06-16 宽 trace grid + 默认 heat-line symbol-only run `20260616T065526Z` 覆盖 `trace_bulk_policy=current_zero/tau22/calibrated`、`trace_scale=0.6..1.6` 和默认五条 affine heat line，结果无 symbol pass。最佳仍是 `tau22` / `calibrated` 的 `trace_scale=1.4 + current`：

```text
symbol_transport_error_max ~= 0.063477
baseline_acoustic_error_n64 ~= 0.108640
baseline_acoustic_ratio_n512 ~= 1.272126
candidate_symbol_pass = false
```

随后执行局部 affine `h(tau32)=a+b*(tau32-0.5)` 网格，发现当前线附近有 symbol-pass 区域。代表候选：

```text
trace_policy = tau22
trace_scale  = 1.45
a = -0.5047506782780278
b =  0.7375445980175264

symbol_transport_error_max ~= 0.022307
baseline_acoustic_error_n64 ~= 0.041132
baseline_acoustic_ratio_n512 ~= 1.214857
candidate_symbol_pass = true
```

但是动态确认 run `20260616T071505Z` 对 `trace_scale=1.35,1.4,1.45,1.5,1.55,1.6` 的 symbol-pass 候选全部失败：

```text
trace_scale=1.45:
  P2-5 FAILED, alpha_relative_error ~= 4744.64
  P2-6 FAILED, sound_speed_relative_error ~= 0.5132
  attenuation_ratio ~= -11552.30
  P2-7 FAILED, max_pr_relative_error ~= 1.00046

trace_scale=1.5:
  P2-5 FAILED, alpha_relative_error ~= 5382.55
  P2-6 FAILED, sound_speed_relative_error ~= 0.1029
  attenuation_ratio ~= -12943.88
  P2-7 FAILED, max_pr_relative_error ~= 1.00043
```

含 P2-9/high-mode 的首选动态确认 run `20260616T070540Z` 也失败：

```text
trace_policy = tau22
trace_scale  = 1.4
heat_flux_retention_curve = [-0.5047506782780278, 0.7375445980175264]

P2-5 FAILED
P2-6 FAILED
P2-7 FAILED
P2-9 FAILED
p2_09_dispersion_masking_status = FAILED
```

判读：linear symbol pass 只能作为候选筛选，不能作为修复证据。当前 affine heat-retention 重标定和 `tau22/calibrated` trace over-scaling 的组合在真实有限振幅演化中不稳定或模态拟合失效，不能合入 production baseline。

加入 low-k ghost gate 后重新运行同一 affine symbol-only 网格 `20260616T073305Z`：

```text
trace_scale=1.35:
  low_k_ghost_spectral_radius_max ~= 1.350000
  low_k_ghost_stability_pass = false
  candidate_symbol_pass = false

trace_scale=1.45:
  low_k_ghost_spectral_radius_max ~= 1.450000
  low_k_ghost_stability_pass = false
  candidate_symbol_pass = false
```

这使诊断脚本的 symbol pass 语义从“只看 hydrodynamic acoustic/thermal eigenvalue”升级为“同时拒绝低 k ghost instability”。

按新流程重跑 stable trace 区间后，默认 heat-line run `20260616T074540Z`：

```text
trace_bulk_policy = current_zero/tau22/calibrated
trace_scale_grid  = 0.0, 0.2, 0.4, 0.6, 0.8, 1.0

symbol_candidate_count = 65
symbol_pass_count = 0
dynamic_enabled = true
dynamic_eligible_count = 0
dynamic_selected_count = 0

best candidate:
  trace_policy = tau22
  trace_scale = 1.0
  heat_line = current
  symbol_transport_error_max ~= 0.068145
  baseline_acoustic_error_n64 ~= 0.806017
  low_k_ghost_spectral_radius_max ~= 1.000000
  candidate_symbol_pass = false
```

进一步使用显式 affine coefficient coarse grid 的 run `20260616T074949Z` 也没有产生动态候选：

```text
heat_affine_intercept_grid = current + [-0.024, ..., +0.024]
heat_affine_slope_grid = current_slope * [0.70, 0.85, 1.00, 1.15, 1.30]

symbol_candidate_count = 585
symbol_pass_count = 0
dynamic_enabled = true
dynamic_eligible_count = 0
dynamic_selected_count = 0

best candidate:
  trace_policy = tau22
  trace_scale = 1.0
  heat_line = affine_i3_j3
  heat_curve_coefficients = [-0.5090006782780278, 0.831545380117799]
  symbol_transport_error_max ~= 0.107449
  baseline_acoustic_error_n64 ~= 0.781260
  low_k_ghost_spectral_radius_max ~= 1.000000
  candidate_symbol_pass = false
```

判读：在 ghost-stable trace 区间内，coarse affine heat-retention 网格无法同时满足 hydrodynamic thermal 和 acoustic symbol gate；因此没有候选进入 P2-5/P2-6/P2-7/P2-9 动态复核。这不是漏跑动态，而是 gate 约束下没有动态 eligible candidate。

### 非放大 scalar trace/bulk 必要边界

继续把 trace nonequilibrium 写成 scalar local closure：

```text
T'_post = r T'_pre
```

low-k full-symbol ghost stability 至少要求：

```text
|r| <= 1
```

在当前 `diagnostic_zero` 配置下，`tau22=0.5`，因此 `tau22` trace policy 的 scalar factor 为：

```text
r = trace_scale * (1 - 1 / tau22) = -trace_scale
```

也就是说，非放大 scalar trace 区间对应 `trace_scale=0..1`。run `20260616T075841Z` 在 baseline Pr 上扫描：

```text
trace_policy = tau22
trace_scale_grid = 0.0, 0.1, ..., 1.0
heat_factor_grid = -0.70, -0.69, ..., -0.20
row_count = 561
boundary_pass_count = 0
```

最佳整体点仍然不满足 acoustic gate：

```text
trace_scale = 1.0
r = -1.0
heat_factor = -0.44
thermal_symbol_error ~= 0.028800
acoustic_symbol_error ~= 0.801618
acoustic_symbol_ratio ~= 1.801618
low_k_ghost_spectral_radius_max ~= 1.000000
boundary_pass = false
```

热扩散和声衰减目标在该 scalar closure family 中拉向不同的 heat-retention 区间：

```text
thermal-pass side:
  r = -1.0, h = -0.44
  thermal_symbol_error ~= 0.028800
  acoustic_symbol_error ~= 0.801618

acoustic-pass side:
  r = -0.6, h = -0.21
  acoustic_symbol_error ~= 0.022405
  thermal_symbol_error ~= 0.282058
```

结论：即使排除 `trace_scale>1` 的 ghost amplification，`T'_post=r T'_pre` 这种 scalar 非放大 trace retention 再配合 scalar heat retention，也不能同时满足 baseline hydrodynamic thermal/acoustic symbol gate。热扩散 gate 需要 `h≈-0.44`，声衰减 gate 需要 `h≈-0.21..-0.28`；两者不是局部微调可以消除的同一约束。

因此，下一类候选不应继续扩大 `tau22/calibrated` scalar scaling 网格，而应显式分离：

1. hydrodynamic compressive trace contribution；
2. low-k trace ghost subspace；
3. heat-flux / energy projection 对 acoustic `O(k^2)` damping 的贡献。

可接受候选的最小形式应当是 ghost-orthogonal / hydrodynamic-trace projection closure：它可以改变声学 `O(k^2)` 阻尼，但不能让 `k=0` 或 mode1 low-k trace ghost 的 full-symbol spectral radius 超过稳定阈值。

该方向已在 `docs/Phase_2/Phase2_D2Q37_Ghost_Orthogonal_Trace_Closure.md` 中推进到 symbol-level prototype。推导把 trace closure 写为：

```text
A_go(k) = A0(k; h) + alpha_h(tau32) * [A1(k; h) - A0(k; h)] * P_a(k)
```

其中 `A0` 是 `current_zero` ghost-stable symbol，`A1` 是 `tau22 trace_scale=1` symbol，`P_a(k)` 是 acoustic 左右特征向量 projector。反推候选为：

```text
h(tau32) =
    -0.504500678278
    + 0.726698353929 * (tau32 - 0.5)

alpha_h(tau32) =
     0.699947491657
    -1.152605711210 * (tau32 - 0.5)

r_g = 0
r_h = -alpha_h
```

该 symbol 原型中四个 Pr 的 `n=64` acoustic/thermal error 均约 1% 内，baseline `n=512` acoustic error 约 `22.16%`，max radius 约 `0.9999996`。run `20260617T060205Z` 已把该 prototype 接入 `--evaluate-ghost-orthogonal-projector` 并确认 `candidate_symbol_pass=true`、low-k ghost stability pass。但它依赖 Fourier/eigen projector，尚不是 local collision，也尚未通过动态 P2-5/P2-6/P2-7/P2-9 gate；当前动态状态是 `not_applicable_until_spectral_or_local_projector_collision_exists`。

## 7. 后续建议

下一步不建议继续提交单点修复。2026-06-16 联合扫描和非放大 scalar boundary 之后，2026-06-17 已给出 ghost-orthogonal / hydrodynamic-trace symbol prototype；后续应先实现 diagnostic spectral projector，再决定是否需要推导 local production approximation：

1. 不再沿 `tau22/calibrated` 简单 scaling 方向扩大动态扫描；`trace_scale>1` 已被 ghost gate 排除，`trace_scale<=1` 的 scalar trace/heat 必要边界也未通过 baseline hydrodynamic symbol。
2. 若继续推进 trace / bulk，应先实现动态可运行的 spectral 或 local projector collision，再用 hydrodynamic symbol + low-k full-symbol ghost gate + P2-5/P2-6/P2-7/P2-9 dynamic gate 流程复核。
3. 联合约束至少包括：
   - P2-5 long-window thermal alpha；
   - P2-7 多 Pr 点扫描；
   - P2-6 acoustic speed / gamma；
   - P2-6 acoustic attenuation eigenvalue；
   - P2-9 Galilean low-mode acoustic；
   - mode=2 high-mode acoustic 边界。
4. 任何候选必须先通过 hydrodynamic linear symbol 和 low-k full-symbol ghost stability 筛选，再通过真实动态 P2-5 / P2-6 / P2-7 / P2-9 复核；若候选在动态中出现数千量级 alpha error、负 attenuation ratio 或早期负温度，应优先作为稳定性/模态诊断样本，而不是继续局部微调。

修复前，D2Q37 仍只能声明为 transport + acoustic-speed/gamma + Galilean candidate，不能声明 final M2 production pass。
