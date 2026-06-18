# D2Q37 Ghost-Orthogonal Trace / Bulk Closure 推导

**最后更新**：2026-06-17  
**范围**：D2Q37 声衰减 trace / bulk closure 的 ghost-orthogonal / hydrodynamic-trace 候选推导  
**结论口径**：本文记录 ghost-orthogonal / hydrodynamic-trace 闭合族、symbol gate 和 diagnostic spectral collision 动态复核；默认 baseline 不变，不声明 final M2 production pass；后续若要进入 production 仍需 local closure 或更严格的 spectral/波数外推边界复核。

## 1. 目标

上一轮 scalar trace/bulk 扫描已经排除：

```text
T'_post = r T'_pre
```

这类 scalar local closure。原因是同一个 `r` 同时控制：

- acoustic hydrodynamic trace contribution；
- low-k trace ghost eigenmode。

`trace_scale>1` 可以让 hydrodynamic acoustic symbol 接近 target，但在 `diagnostic_zero` 下等价于 `r=-trace_scale`，会把 `k=0` trace ghost 放大到 `|lambda|=trace_scale`。`trace_scale<=1` 虽不放大 ghost，却无法同时满足 thermal/acoustic symbol gate。

因此需要拆成两个因子：

```text
r_g : trace ghost retention, 必须 |r_g| <= 1
r_h : hydrodynamic acoustic trace retention, 用于调 acoustic O(k^2) damping
```

最小闭合形式为：

```text
T'_post = r_g * (I - P_h) T' + r_h * P_h T'
```

其中 `P_h` 是 hydrodynamic acoustic trace projector；它必须对 pure trace ghost 为零，对 acoustic hydrodynamic manifold 为一。

## 2. Symbol-Level Projector

现有 collision 只有 `current_zero` 与 scalar `tau22` trace 分支。令：

```text
A0(k; h) = current_zero trace + heat retention h 的 one-step Fourier symbol
A1(k; h) = tau22 trace_scale=1 + heat retention h 的 one-step Fourier symbol
```

在 `diagnostic_zero` 下 `tau22=0.5`，所以 `A1 - A0` 表示把 trace post factor 从 `r_g=0` 改为 `r=-1` 的 trace 更新算子。

取 `A0` 的 acoustic 左右特征向量：

```text
A0 v_+ = lambda_+ v_+
A0 v_- = lambda_- v_-
w_i^* v_j = delta_ij
```

定义 acoustic projector：

```text
P_a(k) = v_+ w_+^* + v_- w_-^*
```

则 ghost-orthogonal hydrodynamic trace prototype 为：

```text
A_go(k) = A0(k; h) + alpha_h(tau32) * [A1(k; h) - A0(k; h)] * P_a(k)
```

这里 `alpha_h > 0` 对应 hydrodynamic trace post factor：

```text
r_h = -alpha_h
```

因为 `A1` 的 scalar trace factor 是 `r=-1`。对任何满足 `P_a x = 0` 的非 acoustic perturbation，尤其 pure trace ghost，新增项为零，因此 trace ghost 继承 `A0` 的 ghost-stable 行为，而 acoustic 子空间获得独立可调的 trace/bulk contribution。

## 3. 反推候选曲线

先保持 ghost branch 为 `current_zero`：

```text
r_g = 0
```

再用 symbol 原型反推 acoustic trace factor 与 heat retention。当前可复现的候选为：

```text
heat retention:
  h(tau32) = -0.504500678278
             + 0.726698353929 * (tau32 - 0.5)

hydrodynamic trace scale:
  alpha_h(tau32) = 0.699947491657
                   - 1.152605711210 * (tau32 - 0.5)

hydrodynamic trace factor:
  r_h(tau32) = -alpha_h(tau32)
```

该 `h(tau32)` 是为了让四个 Pr 点的 thermal symbol 同时回到 1% 以内；`alpha_h(tau32)` 是在该 heat curve 下逐 Pr 反推 acoustic `n=64/mode1` 后拟合得到。

反推点为：

| `Pr_target` | `tau32` | `h(tau32)` | `alpha_h` | `r_h` |
|---:|---:|---:|---:|---:|
| `0.5` | `0.621696329455` | `-0.416064156` | `0.559679607` | `-0.559679607` |
| `0.7061328707` | `0.586170984601` | `-0.441880366` | `0.600626323` | `-0.600626323` |
| `1.0` | `0.560848164727` | `-0.460282417` | `0.629813549` | `-0.629813549` |
| `2.0` | `0.530424082364` | `-0.482391548` | `0.664880521` | `-0.664880521` |

注意：`|r_h|` 可以不同于 `|r_g|`。它作用在 acoustic hydrodynamic projector 后，不是 trace ghost eigenvalue，因此不触发上一轮 scalar over-scaling 的 `k=0` ghost amplification。

## 4. Symbol Prototype 结果

用上式回代 `n=64/mode1` symbol：

| `Pr_target` | acoustic error | acoustic ratio | thermal error | thermal ratio | max radius |
|---:|---:|---:|---:|---:|---:|
| `0.5` | `-0.006329` | `0.993671` | `0.007496` | `1.007496` | `0.999974633` |
| `0.7061328707` | `-0.003358` | `0.996642` | `-0.005937` | `0.994063` | `0.999977853` |
| `1.0` | `-0.008423` | `0.991577` | `-0.006800` | `0.993200` | `0.999980307` |
| `2.0` | `-0.010046` | `0.989954` | `-0.007442` | `0.992558` | `0.999985919` |

baseline Pr 的 lower-k acoustic check：

```text
n=512/mode1:
  acoustic_error ~= 0.221630
  acoustic_ratio ~= 1.221630
  max_radius     ~= 0.999999576
```

这说明该 projector family 在 symbol 层满足当前候选筛选口径：

- hydrodynamic thermal symbol：四个 Pr 点最大误差约 `0.75%`；
- hydrodynamic acoustic symbol：四个 Pr 点 `n=64` 最大误差约 `1.0%`；
- baseline lower-k acoustic ratio 仍在 25% gate 内；
- low-k full-symbol spectral radius 未出现 ghost amplification。

上述 prototype 已接入诊断脚本：

```text
python -m scripts.diagnose_phase2_d2q37_acoustic_attenuation \
  --symbol-only \
  --trace-bulk-policy current_zero \
  --trace-bulk-scale-grid 1.0 \
  --heat-curve-type affine \
  --heat-curve-coefficients -0.504500678278 0.726698353929 \
  --evaluate-ghost-orthogonal-projector
```

run `20260617T061826Z` 给出：

```text
ghost_orthogonal_projector.candidate_symbol_pass = true
thermal_error_max_n64    ~= 0.007496
acoustic_error_max_n64   ~= 0.010046
baseline_acoustic_n512   ~= 0.221630
low_k_ghost_stability    = true
spectral_radius_max      ~= 0.9999998
dynamic_gate_status      = not_run_dynamic_disabled
```

## 5. Diagnostic Spectral Collision 实现

2026-06-17 已实现显式诊断策略：

```text
trace_bulk_policy = ghost_orthogonal_spectral
```

实现位置：

- `core/unit_mapping.py`
  - 新增 `TRACE_BULK_POLICY_GHOST_ORTHOGONAL_SPECTRAL`；
  - 新增 `trace_bulk_projector_alpha_curve` 与 `trace_bulk_projector_low_laplacian`；
  - 若策略为 `ghost_orthogonal_spectral` 且未显式给 alpha 曲线，默认使用本文反推的 D2Q37 affine 系数。
- `core/collision_smrt.py`
  - 本地 regularized collision 中该策略先按 `current_zero` 处理，即构造 ghost-stable `C0`。
- `core/solver.py`
  - 在 `collide_fg` 后、`pull_stream_fg` 前，对低 k Fourier 模态施加：

```text
delta_post_hat(k) =
  alpha_h(tau32) * S(k)^-1 * [A1(k) - A0(k)] * P_a(k) * delta_pre_hat(k)
```

其中 `S(k)` 是 pull-streaming full-step phase。这样 symbol-level 的 `A_go` 被转回 post-collision 空间，而不是把 full-step 更新误加到 streaming 后。实际实现只对

```text
0 < 4 sin(kx/2)^2 + 4 sin(ky/2)^2 <= trace_bulk_projector_low_laplacian
```

的低 k 模态生效，并使用直接 modal amplitude 投影/重构，不对全谱做 FFT。默认 D2Q37 配置的低 k 窗口为：

```text
trace_bulk_projector_low_laplacian = 0.019261093311212455
```

即覆盖 `64/mode1` 的 x/y 与 diagonal 低模态，不触碰高 k ghost/high-mode 内容。

## 6. 动态复核结果

完整 ghost projector 动态脚本：

```text
python -m scripts.diagnose_phase2_d2q37_acoustic_attenuation \
  --dynamic \
  --include-p2-9 \
  --trace-bulk-policy current_zero \
  --trace-bulk-scale-grid 1.0 \
  --heat-curve-type affine \
  --heat-curve-coefficients -0.504500678278 0.726698353929 \
  --evaluate-ghost-orthogonal-projector
```

run `20260617T063554Z` 已写出 `summary.json/report.md`，其中：

```text
ghost_orthogonal_projector.status              = DYNAMIC_PROJECTOR_EVALUATED
ghost_orthogonal_projector.dynamic_gate_status = passed
summary_digest                                 = 542cd1378dcabe111aabee1759fd864265891f8e6232d32057c8a4e0132c0f04
```

动态 hard gate 结果：

| gate | status | key metric |
|---|---|---:|
| P2-5 thermal | `PASSED` | `alpha_relative_error≈0.0193311` |
| P2-5 Fourier-law | `PASSED` | `heat_flux_relative_error≈0.0007503` |
| P2-6 acoustic speed/gamma | `PASSED` | `sound_speed_relative_error≈0.0046389`, `gamma_relative_error≈0.0092993` |
| P2-6 attenuation diagnostic | diagnostic | `attenuation_ratio≈0.881183`, `attenuation_relative_error≈0.118817` |
| P2-7 Pr scan | `PASSED` | `max_pr_relative_error≈0.0178784` |
| P2-9 Galilean | `PASSED` | `max_sound_speed_relative_error≈0.0037474`, `max_direction_difference≈0.0084729` |
| P2-9 masking | `PASSED` | `p2_09_dispersion_masking_status=PASSED` |

补充：同一实现的无 P2-9 动态 run `20260617T063727Z` 也通过 P2-5/P2-6/P2-7，`dynamic_gate_status=passed_without_p2_9`，`summary_digest=e6cf2ae4de9a88dda12fa6c6f9c8a4fe89125db1a88d4b81990da5af2a320be7`。

## 7. 仍不能直接合入 production 的原因

上述实现是 diagnostic spectral collision，不是 local production collision：

- `P_a(k)` 依赖 Fourier wave number 和当前 closure 的左右特征向量；
- 当前只对低 k 模态施加 projector，高 k trace/bulk 与 high-mode acoustic 边界仍依赖既有 spectral correction/诊断口径；
- 周期域全局谱 projector 适合验证闭合结构，但不适合直接作为一般边界、非周期或局部多物理耦合 production collision；
- n512 thermal symbol 在该原型中不是验收项，但后续若扩大 symbol gate 应单独记录；
- final M2 production pass 仍需要 production 可接受的 local closure 或明确接受 spectral diagnostic collision 的适用范围。

因此当前可更新的结论是：

```text
ghost-orthogonal 分离 r_g=0 与 r_h=-alpha_h(tau32) 足以通过当前 hydrodynamic symbol、low-k ghost stability、P2-5/P2-6/P2-7/P2-9 动态 gate。
```

但它仍不是 baseline production patch。

## 8. 后续实现路线

symbol gate 和 diagnostic spectral dynamic gate 已通过。剩余问题不是继续调 `alpha_h/h`，而是把该结构转化为可维护的 production closure。有两条路线：

1. **继续收紧 diagnostic spectral projector 的边界**  
   扩展 wave-number/Pr/Mach/diagonal acoustic 覆盖，记录 full P2-9 的运行时间和可重复性，确认低 k projector 不掩盖 high-mode acoustic 边界。

2. **local hydrodynamic-manifold approximation**  
   从 Chapman-Enskog / invariant-manifold 角度，把 `P_h T'` 近似为由 compressive acoustic hydrodynamic state 诱导的 trace nonequilibrium，而把 pure trace ghost 留给 `r_g=0` 或其它非放大值。该路线才可能进入 production collision，但推导成本更高。

下一步建议优先推导 local hydrodynamic-trace approximation：以当前 spectral projector 作为 oracle，拟合或推导一个不依赖全局 Fourier eigenbasis 的局部闭合，再复跑同一套 symbol/ghost/dynamic gate。

## 9. Local Hydrodynamic-Trace Closure

2026-06-17 进一步用 `ghost_orthogonal_spectral` 作为 oracle，反推不依赖 Fourier eigenbasis 的局部 hydrodynamic trace 近似。

### 9.1 局部量选择

oracle 对 acoustic 子空间给出的 post-collision trace 可以写成：

```text
T_post^oracle(k) = tr Pi_neq,post^oracle
```

对 x/y 方向 `64/mode1` acoustic eigenvector，计算：

```text
chi = T_post^oracle / [rho0 * theta0 * div_c(u)]

div_c(u) =
  0.5 * (u_x[y, x+1] - u_x[y, x-1])
+ 0.5 * (u_y[y+1, x] - u_y[y-1, x])
```

得到的 `chi` 基本为实数；虚部随左右行波换号，是有限 k 相位误差，不作为 local closure 系数。四个 Pr 点 x/y 平均值为：

| `Pr_target` | `tau32` | `chi_xy` |
|---:|---:|---:|
| `0.5` | `0.621696329455` | `0.890676979` |
| `0.7061328707` | `0.586170984601` | `0.952752600` |
| `1.0` | `0.560848164727` | `0.996814289` |
| `2.0` | `0.530424082364` | `1.049553777` |

仿射拟合：

```text
chi(tau32) = 1.102631069
             - 1.74075050 * (tau32 - 0.5)
```

四点最大拟合残差约 `1.2e-4`，足以作为第一版 local oracle approximation。

### 9.2 Local Closure 形式

新增 diagnostic local policy：

```text
trace_bulk_policy = ghost_orthogonal_local
```

其 trace/bulk post moment 定义为：

```text
T_post^local = chi(tau32) * rho * theta * div_c(u)
```

然后沿用现有 second-order central moment reconstruction，把：

```text
delta_xx = 0.5 * (T_post^local + dev_post)
delta_yy = 0.5 * (T_post^local - dev_post)
```

投回 `f_post`。这给出局部 ghost-orthogonal 性质：

- pure trace ghost 不改变 `rho/u/theta`，因此 `div_c(u)=0`，`T_post^local=0`；
- isobaric thermal mode 初始无速度散度，因此不会直接激活 trace channel；
- acoustic hydrodynamic mode 有 `div_c(u)`，因此获得 oracle 反推的 hydrodynamic trace contribution。

实现位置：

- `core/unit_mapping.py`
  - `TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL`
  - `trace_bulk_local_divergence_curve`
  - `trace_bulk_local_divergence_factor_from_tau32`
- `core/collision_smrt.py`
  - `_local_hydrodynamic_trace_stress`
  - `_periodic_central_velocity_divergence`
  - `ghost_orthogonal_local` 分支在 `_regularized_f_collision` 中直接构造 `trace_post`
- `core/solver.py`
  - HDF5 collision metadata 记录 local divergence curve

### 9.3 动态复核

使用 oracle heat curve：

```text
h(tau32) = -0.504500678278
           + 0.726698353929 * (tau32 - 0.5)
```

并使用默认 local divergence curve：

```text
chi(tau32) = 1.102631069
             - 1.74075050 * (tau32 - 0.5)
```

当前手动动态复核：

| gate | status | key metric |
|---|---|---:|
| P2-5 thermal | `PASSED` | `alpha_relative_error≈0.0194615` |
| P2-5 Fourier-law | `PASSED` | `heat_flux_relative_error≈0.0008429` |
| P2-6 acoustic speed/gamma | `PASSED` | `sound_speed_relative_error≈0.0047735`, `gamma_relative_error≈0.0095697` |
| P2-6 attenuation diagnostic | diagnostic | `attenuation_ratio≈0.887212`, `attenuation_relative_error≈0.112788` |
| P2-7 Pr scan | `PASSED` | `max_pr_relative_error≈0.0179971` |
| P2-9 single Mach/background smoke | `PASSED` | Mach `0.02`, background `x`, directions `x/y`; `sound_speed_error≈0.0037899`, `direction_difference≈0.0005950` |

上述结果说明：x/y low-k acoustic gate 中，local divergence closure 已足够接近 spectral oracle；声衰减 ratio 从 baseline 约 `6.27x` 过阻尼区域拉回到约 `0.887`。

### 9.4 当前限制

同一反推在 diagonal `64/mode1` 上给出更大的 oracle 系数：

| `Pr_target` | `chi_xy` | `chi_diagonal` |
|---:|---:|---:|
| `0.5` | `0.890677` | `1.089752` |
| `0.7061328707` | `0.952753` | `1.163590` |
| `1.0` | `0.996814` | `1.215864` |
| `2.0` | `1.049554` | `1.278288` |

因此单标量 `chi(tau32)` 是 x/y low-k oracle approximation，不是完整各向同性 projector。

当前结论：

```text
ghost_orthogonal_local 是第一个可运行的 local hydrodynamic-trace diagnostic closure；
它通过 x/y low-k 动态 gate，但尚未具备 production 级 diagonal/isotropy 证明。
```

## 10. Laplacian Isotropy Attempt

为修正 diagonal oracle 系数偏大，尝试了两项局部 stencil：

```text
T_post = rho * theta * [ a(tau32) * div_c(u)
                       + b(tau32) * (-L div_c(u)) ]
```

其中 `L` 是周期五点 Laplacian，`-L` 在 Fourier 空间对应正的 discrete Laplacian symbol：

```text
mu(k) = 4 sin(kx/2)^2 + 4 sin(ky/2)^2
```

用 x/y 与 diagonal `64/mode1` oracle 同时反推：

```text
a(tau32) = 0.86390221
           - 1.41574932 * (tau32 - 0.5)

b(tau32) = 24.78889350
           - 33.74907949 * (tau32 - 0.5)
```

代码中作为显式失败诊断策略保留：

```text
trace_bulk_policy = ghost_orthogonal_local_laplacian
```

### 10.1 动态结果

使用同一 oracle heat curve：

```text
h(tau32) = -0.504500678278
           + 0.726698353929 * (tau32 - 0.5)
```

动态 smoke 结果：

| gate | status | key metric |
|---|---|---:|
| P2-5 x/y/diagonal | `FAILED` | max `alpha_relative_error≈1.287394`, max Fourier-law error≈`0.625195` |
| P2-6 x/y/diagonal | `FAILED` | max sound speed error≈`0.0102883`, max gamma error≈`0.0206824` |
| P2-6 x | `PASSED` | attenuation ratio≈`0.887212` |
| P2-6 y | `PASSED` | attenuation ratio≈`0.887212` |
| P2-6 diagonal | `FAILED` | attenuation ratio≈`1.426890` |
| P2-7 | `PASSED` | max Pr error≈`0.0179971` |

对照：不含 Laplacian 的 `ghost_orthogonal_local` 在 x/y gate 通过，但加入 diagonal 后也失败：

| gate | status | key metric |
|---|---|---:|
| P2-5 x/y/diagonal | `FAILED` | max `alpha_relative_error≈1.059714`, max Fourier-law error≈`0.615832` |
| P2-6 x/y/diagonal | `FAILED` | max gamma error≈`0.0205112`; diagonal attenuation ratio≈`2.554143` |

### 10.2 判定

简单 Laplacian 修正不是可行 production 方向。原因是：

- 为了在 `64/mode1` diagonal 上补约 `20%` trace response，`b(tau32)` 必须约为 `20-24`，该高阶导数项会放大 diagonal thermal 中由数值耦合产生的小速度散度；
- 它只区分 wave-number magnitude，不能区分 acoustic pressure-bearing compression 与 isobaric thermal contamination；
- x/y acoustic 保持通过不代表 diagonal thermal/acoustic projector 正确。

下一步不应继续调大局部 Laplacian 系数，而应引入能区分 acoustic 与 thermal 的局部 hydrodynamic projector。例如：

1. 基于 pressure-gradient / compressive velocity 的局部 acoustic discriminator；
2. 使用 pressure-equilibrium constraint 构造 `div_acoustic = div(u) - div_thermal_estimator`；
3. 从 invariant manifold 推导只作用于 pressure-bearing acoustic hydrodynamic manifold 的 trace estimator。

当前可保留的候选仍是：

```text
ghost_orthogonal_spectral: 通过完整当前 dynamic gate，但非 local production；
ghost_orthogonal_local: x/y low-k diagnostic local closure，diagonal/isotropy 未过；
ghost_orthogonal_local_laplacian: diagonal 修正失败分支，仅作反例记录。
```

## 11. Local Acoustic/Thermal Discriminator

### 11.1 约束

Laplacian 反例给出一个重要约束：下一版 local closure 不能只拟合
`T_post / [rho0 * theta0 * div_c(u)]` 的数值系数。它必须同时满足：

```text
pure trace ghost:       T_post = 0
isobaric thermal mode:  T_post = 0 + higher-order leakage
acoustic mode:          T_post = chi(tau32) * rho0 * theta0 * div_acoustic
```

其中 `div_acoustic` 必须是 pressure-bearing compression，而不是任何由热扩散数值耦合产生的速度散度。

对任意 memoryless、平移不变、局部线性 stencil，低 k 标量 trace estimator 的一般形式可写成：

```text
D_loc(k) = A_u(k) dot u_hat + A_rho(k) rho_hat + A_theta(k) theta_hat
```

在各向同性和奇偶性约束下：

```text
A_u(k) dot u_hat = i * a0 * k dot u_hat + O(k^3)
A_rho(k) rho_hat + A_theta(k) theta_hat = O(k^2)
```

因此所有 memoryless local stencil 的 leading `O(k)` trace channel 都退化为 `div(u)`。这解释了两个现象：

- `ghost_orthogonal_local` 能通过 x/y low-k acoustic gate，因为 acoustic leading term 正是 `div(u)`；
- `ghost_orthogonal_local_laplacian` 无法成为 production 修正，因为 Laplacian 只改变 `O(k^3)` 或固定波数响应，不能在 leading order 区分 acoustic compression 与 thermal contamination。

结论：若不引入时间记忆或非局部投影，memoryless local scalar stencil 没有足够自由度同时满足 diagonal acoustic 与 isobaric thermal gate。

### 11.2 Pressure-Memory Projector Candidate

局部可运行的下一候选应使用 linearized pressure equation：

```text
D_t p' + gamma * p0 * div(u) = O(k^2)
```

其中：

```text
p = rho * theta
p0 = rho0 * theta0
D_t p' = (p^n - p^(n-1)) / dt + U0 dot grad_c(p^n)
```

由此定义 pressure-bearing compression estimator：

```text
div_p = - D_t p' / (gamma * p0)
T_post = chi(tau32) * rho * theta * div_p
```

该形式的预期性质：

- acoustic mode：`div_p = div(u) + O(k^2)`，因此保留 spectral oracle 反推的 acoustic trace contribution；
- isobaric thermal mode：`p' ~= 0`，`D_t p'` 只保留高阶数值 leakage，因此不会像 Laplacian 修正那样放大 thermal diagonal contamination；
- pure trace ghost：宏观 `rho/u/theta/p` 不变，`div_p=0`，保持 ghost-orthogonal；
- diagonal mode：公式只依赖标量压力时间导数，不依赖 x/y 方向特化，天然比 `div_c + beta * L div_c` 更适合各向同性复核。

实现上这不是当前 `collide_fg` 的无记忆局部 collision；需要 `GasSolver2D` 在 collision 前保存上一时刻 pressure field，或在 collision API 中显式传入 `pressure_material_derivative_lu`。第一步应作为 diagnostic policy 实现，例如：

```text
trace_bulk_policy = ghost_orthogonal_local_pressure_memory
trace_bulk_pressure_memory_curve = chi(tau32)
```

并保持默认 baseline 不变。首个动态 gate 必须直接包含 x/y/diagonal：

```text
P2-5 directions = x, y, diagonal
P2-6 directions = x, y, diagonal
P2-7 Pr scan
P2-9 Mach/background smoke plus diagonal acoustic direction
```

若该 pressure-memory candidate 仍无法通过 thermal/acoustic gate，则下一层才应进入非局部但可局域近似的 invariant-manifold estimator，而不是继续调高阶 Laplacian 系数。

## 12. Pressure-Memory Diagnostic Attempt

### 12.1 实现

已新增 diagnostic policy：

```text
trace_bulk_policy = ghost_orthogonal_local_pressure_memory
```

实现位置：

- `core/unit_mapping.py`：显式 policy、D2Q37-only 校验，默认复用 `ghost_orthogonal_local` 的 `chi(tau32)` 曲线；
- `core/collision_smrt.py`：`collide_fg(..., trace_bulk_pressure_divergence=...)` 可接收 solver 提供的 `div_p`；
- `core/solver.py`：`GasSolver2D` 保存上一 pre-collision pressure field，第一步用 `div_c(u)` bootstrap，后续使用

```text
div_p = -[(p^n - p^(n-1)) + mean(u^n) dot grad_c(p^n)] / (gamma * p0)
T_post = chi(tau32) * rho * theta * div_p
```

默认 `trace_bulk_policy=current_zero` 不变。

### 12.2 Dynamic Smoke

使用 spectral oracle heat curve：

```text
h(tau32) = -0.504500678278 + 0.726698353929 * (tau32 - 0.5)
```

手动 smoke 结果：

| gate | status | main diagnostics |
|---|---|---:|
| P2-5 x/y/diagonal | `FAILED` | max `alpha_relative_error≈1.040714`, max Fourier-law error≈`0.616072`, direction difference≈`0.830623` |
| P2-6 x/y/diagonal | `PASSED` for speed/gamma | max sound-speed error≈`0.9665%`, max gamma error≈`1.9423%`; attenuation remains diagnostic, diagonal ratio≈`1.5881` |

Direction detail:

```text
P2-5 x:        alpha error≈0.210091, heat-flux error≈0.004947
P2-5 y:        alpha error≈0.210091, heat-flux error≈0.004947
P2-5 diagonal: alpha error≈1.040714, heat-flux error≈0.616072

P2-6 x:        sound error≈0.4800%, gamma error≈0.9624%, attenuation ratio error≈0.9345
P2-6 y:        sound error≈0.4800%, gamma error≈0.9624%, attenuation ratio error≈0.9345
P2-6 diagonal: sound error≈0.9665%, gamma error≈1.9423%, attenuation ratio error≈1.5881
```

没有 NaN、负温度或 invalid step。

### 12.3 判定

`ghost_orthogonal_local_pressure_memory` 证明 pressure-bearing acoustic discriminator 可以保持 P2-6 声速/gamma gate，但 pressure-only trace 会过度抑制 thermal 侧的 trace contribution，导致 P2-5 失败。当前候选不得作为 production closure。

下一步不应回退到单一 `div(u)` 或单一 `div_p`，而应构造 two-channel local projector：

```text
div_a = div_p
div_t = div_c(u) - div_p
T_post = rho * theta * [chi_a(tau32) * div_a + chi_t(tau32) * div_t]
```

其中 `chi_a` 继续由 spectral oracle acoustic trace response 约束，`chi_t` 必须由 isobaric thermal P2-5 gate 约束，并且二者都要通过 low-k full-symbol ghost stability 与 x/y/diagonal dynamic gate。若 two-channel projector 仍失败，再进入 invariant-manifold trace estimator。

## 13. Two-Channel Local Projector Attempt

### 13.1 实现

已新增 diagnostic policy：

```text
trace_bulk_policy = ghost_orthogonal_local_two_channel
```

实现位置：

- `core/unit_mapping.py`：新增显式 policy、D2Q37-only 校验、`trace_bulk_local_divergence_curve` 作为 acoustic `chi_a(tau32)`，以及 `trace_bulk_local_thermal_curve` 作为 thermal `chi_t(tau32)`；
- `core/collision_smrt.py`：在 local trace 分支中构造

```text
div_a = div_p
div_t = div_c(u) - div_p
T_post = rho * theta * [chi_a(tau32) * div_a + chi_t(tau32) * div_t]
```

- `core/solver.py`：two-channel policy 复用 pressure-memory 的上一 pre-collision pressure field 与 material pressure derivative：

```text
div_p = -[(p^n - p^(n-1)) + mean(u^n) dot grad_c(p^n)] / (gamma * p0)
```

默认 `trace_bulk_policy=current_zero` 不变。two-channel 默认 `chi_a/chi_t` 均使用已有 x/y local diagnostic seed：

```text
chi(tau32) = 1.102631069 - 1.74075050 * (tau32 - 0.5)
```

这是为了保持默认诊断种子保守；diagonal acoustic oracle 拟合

```text
chi_diag(tau32) ~= 1.34136394 - 2.06579753 * (tau32 - 0.5)
```

只作为显式配置扫描方向，不写成默认。

### 13.2 Dynamic Smoke

使用 spectral oracle heat curve：

```text
h(tau32) = -0.504500678278 + 0.726698353929 * (tau32 - 0.5)
```

基础回归：

```text
python -m pytest verification/test_phase2_p2_00_unit_mapping.py \
  verification/test_phase2_p2_03_collision_uniform.py \
  verification/test_phase2_hdf5_metadata.py
```

结果：`17 passed`。

x/y/diagonal smoke 结果：

| gate | status | key metric |
|---|---|---:|
| P2-5 x/y | `PASSED` | `alpha_relative_error≈1.946%`, Fourier-law error≈`0.0843%` |
| P2-5 diagonal | `FAILED` | `alpha_relative_error≈105.97%`, Fourier-law error≈`61.58%` |
| P2-6 x/y | `PASSED` | `sound_speed_relative_error≈0.4773%`, `gamma_relative_error≈0.9570%` |
| P2-6 diagonal | `FAILED` | `sound_speed_relative_error≈1.0204%`, `gamma_relative_error≈2.0511%`, attenuation ratio≈`2.5541` |

补充短窗口扫描：

- `chi_t=-2..5` 时 diagonal P2-5 alpha error 仍约 `104%`，未出现通过区间；
- `chi_a=-5..5` 时 diagonal P2-5 alpha error 仍约 `104%`，未出现通过区间；
- diagonal thermal failure 因而不是单独增减 `chi_a` 或 `chi_t` 可以修复的问题。

### 13.3 判定

two-channel local projector 已实现，但仍不能作为 production closure：

- pressure/thermal 两通道能保持 x/y low-k smoke；
- diagonal isobaric thermal contamination 仍无法由 `div_c(u)-div_p` 局部分解消除；
- diagonal acoustic hard gate 仍在 gamma 约 `2%` 边界外；
- 该候选不改变默认 D2Q37 baseline，不声明 final M2 production pass。

下一步应进入 invariant-manifold / 更强局部 trace estimator，而不是继续调 scalar `chi_a/chi_t`。

## 14. Entropy-Manifold Local Estimator Attempt

### 14.1 推导

two-channel 反例说明：

```text
div_t = div_c(u) - div_p
```

不是合格 thermal projector。它仍把 diagonal isobaric thermal 中的数值速度散度混入 trace channel，且单独扫描 `chi_a/chi_t` 不能修复 diagonal P2-5。

下一层 local invariant-manifold 估计应先构造热力学不变量。线性 entropy variable 定义为：

```text
s = theta' / theta0 - (gamma - 1) * rho' / rho0
```

对 acoustic mode：

```text
s = 0 + O(k^2)
```

对 isobaric thermal mode：

```text
p' = 0
rho'/rho0 = -theta'/theta0
s = gamma * theta'/theta0
```

isobaric thermal manifold 上，连续方程与热扩散给出：

```text
div_t = D_t theta' / theta0 = alpha * L(theta'/theta0)
      = (alpha / gamma) * L s
```

其中 `L` 是周期五点 Laplacian，Fourier 空间对 sine mode 给出负的 `k^2` leading term。于是 acoustic compression estimator 为：

```text
div_a = div_c(u) - div_t
```

trace post moment 采用 acoustic/thermal 分通道：

```text
T_post = rho * theta * [
    a(tau32) * div_a
  - b(tau32) * L div_a
  + chi_t(tau32) * div_t
]
```

这里：

- `a,b` 复用此前 acoustic x/y/diagonal oracle 的 Laplacian trace response；
- `chi_t` 默认复用 x/y local thermal diagnostic seed；
- pure trace ghost 不改变 `rho/theta/u`，所以 `s=0`、`div_t=0`、`div_a=0`；
- acoustic mode 上 `s≈0`，因此只走 acoustic branch；
- isobaric thermal mode 上 `div_t` 由 entropy diffusion 给出，而不是由 pressure memory 或 raw velocity divergence 猜测。

### 14.2 实现

新增 diagnostic policy：

```text
trace_bulk_policy = ghost_orthogonal_local_entropy_manifold
```

实现位置：

- `core/unit_mapping.py`
  - 新增 `TRACE_BULK_POLICY_GHOST_ORTHOGONAL_LOCAL_ENTROPY_MANIFOLD`；
  - D2Q37-only 校验；
  - 默认 `trace_bulk_local_divergence_curve` 使用 Laplacian acoustic `a(tau32)`；
  - 默认 `trace_bulk_local_laplacian_curve` 使用 Laplacian acoustic `b(tau32)`；
  - 默认 `trace_bulk_local_thermal_curve` 使用 two-channel thermal seed。
- `core/collision_smrt.py`
  - 新增 `_entropy_manifold_thermal_divergence`；
  - 在 `_local_hydrodynamic_trace_stress` 中构造 `div_t`、`div_a` 和上式 `T_post`。

该 policy 不需要 solver pressure history，默认 `trace_bulk_policy=current_zero` 不变。

### 14.3 Dynamic Smoke

使用 spectral oracle heat curve：

```text
h(tau32) = -0.504500678278 + 0.726698353929 * (tau32 - 0.5)
```

基础回归：

```text
python -m pytest verification/test_phase2_p2_00_unit_mapping.py \
  verification/test_phase2_p2_03_collision_uniform.py \
  verification/test_phase2_hdf5_metadata.py
```

结果：`19 passed`。

x/y/diagonal smoke：

| gate | status | key metric |
|---|---|---:|
| P2-5 x/y | `PASSED` | `alpha_relative_error≈1.946%`, Fourier-law error≈`0.0843%` |
| P2-5 diagonal | `FAILED` | `alpha_relative_error≈112.15%`, Fourier-law error≈`60.84%` |
| P2-6 x/y | `PASSED` | `sound_speed_relative_error≈0.4773%`, `gamma_relative_error≈0.9570%` |
| P2-6 diagonal | `FAILED` | `sound_speed_relative_error≈1.0288%`, `gamma_relative_error≈2.0683%`, attenuation ratio error≈`42.69%` |

补充判别：

- `chi_t` 与 acoustic Laplacian coefficient 的短窗口扫描中，diagonal P2-5 alpha error 仍约 `104%`，heat-flux error 仍约 `61%`；
- `ghost_orthogonal_spectral` 使用 exact acoustic projector 时，diagonal P2-5 也失败：x 方向通过，diagonal `alpha_relative_error≈105.98%`、Fourier-law error≈`61.58%`；
- 因此 diagonal P2-5 不是 local trace estimator 单独可修复的问题。

### 14.4 判定

`ghost_orthogonal_local_entropy_manifold` 达到了形式目标：它能用 entropy invariant 区分 pressure-bearing acoustic compression 与 isobaric thermal manifold，并且不触发 pure trace ghost。

但动态 gate 仍失败，且失败边界指向 D2Q37 diagonal thermal/heat-flux branch：

- exact spectral acoustic projector 不能修复 diagonal P2-5；
- local trace 系数扫描几乎不改变 diagonal thermal alpha/heat-flux 误差；
- diagonal P2-5 heat-flux error 约 `61%`，这直接指向 heat-flux retention/export 或 conductive heat-flux projection 的方向性问题。

当前结论：

```text
entropy-manifold trace estimator 不是 production closure；
下一步应复核 D2Q37 diagonal isobaric thermal heat-flux/dispersion branch，
而不是继续只调 trace estimator。
```
