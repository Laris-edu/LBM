# Phase_2 D2Q37 Recursive-Regularized (Local) Closure 里程碑

**最后更新**：2026-06-22
**范围**：本地各向同性 / recursive-regularized 二阶闭合(应变率偏量 + `div` 迹)对声衰减的修复、其完整门况,以及声衰减**测量口径修正(F1)**与**对角过约束定理(T1)**(第 8 节)
**结论口径**：diagnostic;baseline 不变;不声明 final M2 production pass。`deviatoric_stress_policy=measured` + `trace_bulk_policy=current_zero` 仍是 baseline。
**权威 run**：
- 完整门况:`results/phase2_recursive_regularized_closure/20260621T083625Z`(`summary_digest=60c7f8940256d98276173b5e9059296f5b09cff5a035fb606ef83e7048d9ef84`,含 P2-4/5/6/7/9 + 长窗口)
- 测量口径 + 过约束(第 8 节 F1/T1):`results/phase2_acoustic_attenuation_caliber/20260621T142249Z`(`summary_digest=3c7d47a6e4090d79016b8638395ed73a9a8c40384b385eb605d7c784131287a8`)
- 各向异性边界 + 声学紧致(第 8 节 决策 A):`results/phase2_acoustic_attenuation_anisotropy/20260621T142501Z`(`summary_digest=d2e0b9862be4dc08b86bad3454c4f43fe9e911ca5df838ad35836cb2bc5557b7`)
**复现脚本**：`scripts/phase2_closure_recursive_regularized.py`、`scripts/phase2_acoustic_attenuation_caliber.py`、`scripts/phase2_acoustic_attenuation_anisotropy.py`

## 1. 背景

`docs/Phase_2/acoustic/Phase2_D2Q37_Physical_Bulk_Viscosity_Diagnosis.md` 已定位:声衰减残差是纵波 normal-stress 黏性,且与 diagonal 热流同属各向同性/完备性缺陷,指向各向同性 / recursive-regularized 应力+热流闭合。复核分两步:

1. **仅偏量应变率重构**(`deviatoric_stress_policy=strain_rate_isotropic`):`ν_T` 可做成各向同性,**但声衰减仍 2.3×**——纵波 `ν_L,dev` 在 `normal_factor` 钉死 `ν_T,diag` 后被推到 ~3.8ν。即仅偏量各向同性不修声衰减。
2. **完整 RR(本文)**:偏量应变率重构 **+** 迹由 `div(u)` 重构(`trace_bulk_policy=ghost_orthogonal_local`)。比"应变率偏量 + 实测 tau22 迹"多出 `chi`(迹散度系数)这个独立纵波旋钮。

## 2. 闭合结构

```text
deviatoric_stress_policy = strain_rate_isotropic
  dev_post = normal_factor * rho*theta * (d_x u_x - d_y u_y)   # FD 应变率
  xy_post  = xy_factor     * rho*theta * (d_x u_y + d_y u_x)
trace_bulk_policy = ghost_orthogonal_local
  trace_post = chi * rho*theta * div_c(u)                       # 纯 ghost div=0 → ghost 稳定
bulk_viscosity_policy = diagnostic_zero                          # nu_b=0 → matched target nu_L=nu
```

三旋钮低 k 解耦:`xy_factor←ν_T(x)`(x 横波只走 xy 通道)、`normal_factor←ν_T(diagonal)`(diagonal 横波只走 normal 通道)、`chi←ν_L(x)`(x 纵波 `div≠0`,`normal_factor` 钉死后 `chi` 独立调 `ν_L`)。

## 3. 完整门况(run `20260621T083625Z`)

标定:`xy_factor=0.4764`、`normal_factor=0.8906`、`chi=1.085`(`chi` 正、`div`-based → ghost 稳定)。

| 门 | 状态 | 关键结果 |
|---|---|---|
| P2-4 横波 `ν_T/ν` | `PASSED` | x/y/diagonal=1.000/1.000/1.002;dir_diff 0.18% |
| P2-5 热扩散 alpha_err | `PASSED` | x/y 0.18%,diagonal 2.11% |
| P2-6 声衰减 ratio | x/y `PASSED` | **x/y=1.003**,diagonal=**1.233**;c_err 0.49%,g_err 0.98%;三方向无 invalid/负温 |
| P2-7 Pr | `FAILED`(边缘) | baseline **0.18%**,scan max **5.24%**(scan_tol 5%) |
| P2-9 Galilean | `PASSED` | max sound-speed err 0.77%,max dir-diff 2.24%,masking `PASSED` |
| 长窗口 3×(720/960/720) | 稳定 | P2-4 `ν` 一致(x 2e-5,diag 0.18%)、P2-5 `α` 一致(x 0.22%,diag 1.80%);P2-6 衰减 x=**1.083**、diag=**1.458**;无 invalid/负温 |

## 4. 结论

**这是第一个本地、稳定且让 x/y 声衰减 ratio→~1、同时保 `ν_T` 各向同性 + P2-5 + P2-9 的闭合**,把项目核心阻塞(x/y 声衰减 6.27×)修到 ~1。此前只有非本地 `ghost_orthogonal_spectral` projector 拿到过 ratio≈0.88。

> **口径修正(见第 8 节,run `20260621T142249Z`)**:本节"x/y=1.003"是 240 步 `log|p'|` 短窗口拟合值,已证为弱阻尼 beating 偏低伪影。窗口无关的精确本征值真值在**已发布 `chi`** 下为 x/y≈**1.104**;用本征值口径重标 `chi*=1.10524` 后 x/y 声学=**1.000(精确)**、diagonal=**1.265**(45°)。即 x/y 声衰减→1 在窗口无关口径下严格成立,diagonal 真实残差为 1.265(已按决策 A 接受为有界 GO-RISK 边界)。关键是完整 RR 的一致重构:`div`-based 迹提供独立纵波旋钮 `chi`,在 `ν_T` 各向同性钉死后单独把 `ν_L,x` 调到 ν,且对纯 trace ghost(`div=0`)自动为零 → ghost 稳定。

## 5. 已表征的残差(均非发散,均有清晰机理)

1. **diagonal 声衰减残差**(窗口无关真值 **1.265** @45°,见第 8 节;`log|p'|` 短窗口读到 1.23):本质是 **4 约束(`ν_T,轴/ν_T,对角/ν_L,轴/ν_L,对角`)对 3 旋钮的过约束**,并已在第 8 节 **T1** 中证明为方形(D4)点阵局部线性闭合的**不可约**结构性残差;各向同性 `div`/应变率 stencil 必然无效(理论 + 实测共同确认)。**已按决策 A 接受为有界结构性 GO-RISK 边界**(轴向精确、45° 上界 1.265、声学紧致 `kL≈0.04` 下对 `p_hat` 影响可忽略,见第 8 节)。
2. **声衰减随拟合窗口漂移**(此前列为残差,已由第 8 节 **F1** 定性为**测量侧**):声阻尼极弱(`σ≈2.2e-5/step`),`log|p'|` 线性拟合被前/后向声模态弱 beating 涟漪在短窗口压低、随窗口漂移;精确一步模态本征值 `σ=-log|λ|`(= 动态 Prony)窗口无关、无拟合、无混入。**不是闭合不稳**;真值口径应为本征值/Prony。
3. **P2-7 极值 5.24%**:Pr 扫描变 `α`(tau32)而非 `ν`(tau21 固定),故 `g_dev(tau21)` 对其无影响;失败点 `Pr=2` 由 α/heat-flux 既有特性(≈baseline 4.94%)+ 高 Pr 小 RR `ν` 误差合成,非偏量旋钮可修。
4. **high-mode acoustic** 未覆盖(RR 修的是低模态,high-mode 是另一轴,需与 high-mode 修正组合)。

## 6. 定性与边界

- **定性:强 GO-RISK 候选**,把核心阻塞从 6.27× 修到 x/y ~1.0(本地、稳定);但因 diagonal 残差 + 声衰减窗口依赖 + P2-7 边缘 + high-mode 未覆盖,**不是窗口无关的干净 production pass**。
- diagnostic;baseline 不变(默认 `measured` + `current_zero`)。
- 不把本里程碑写成 final M2 production pass。

## 7. 下一步

1. **diagonal 声衰减(残差 #1,已由 T1 重定性 + 决策 A 接受)**:已证为 D4 局部线性闭合的不可约过约束(第 8 节),并已**按决策 A 接受为有界结构性 GO-RISK 边界**(对角真值 1.265@45°、轴向精确、声学紧致下对 `p_hat` 影响可忽略)。各向同性局部 stencil 不必再试。仅当后续物理目标确需对角声衰减精度时,才考虑非局部(Riesz/纵波投影)、非线性或带记忆的第 4 自由度(代价:失去"本地"性,回到 spectral 类)。
2. **声衰减测量口径(残差 #2,已由 F1 收口)**:窗口漂移是测量侧弱阻尼拟合伪影;本征值/Prony 为窗口无关真值口径,已落地为诊断脚本。默认 P2-6 `log|p'|` 不变;如需把 P2-6 诊断 attenuation 升级为本征值/Prony 口径,再单独评估(不改 hard gate)。
3. P2-7 极值:属 heat-flux 高 Pr 特性,与 RR 解耦,后续在 heat-flux 闭合工作中处理。
4. **high-mode(残差 #3,已评估 + 接受)**:已用本征值口径评估 RR 与 high-mode 的组合(第 9 节)——high-mode 声学过阻尼 5–12× 是真实、色散驱动(非 filter)、RR 无关(RR 只修 mode1)、对紧致 10 kHz 目标物理无关的轴,已接受为有界 GO-RISK 边界。production 修复(若非紧致目标需要)需 spectral/dispersion 的衰减机制,不在当前范围。组合所需的 `core/solver.py` 缓存键不含 `chi`/deviatoric 的陷阱已于 2026-06-21 在 core 修复。
5. 若残差明确接受为 Phase_3 限定边界,再评估是否把 RR(用本征值口径重标的 `chi*`)升级为默认 baseline(届时同步 core/config/unit mapping/全套文档)。

## 8. 测量口径修正(F1)、对角过约束定理(T1)与边界接受(决策 A)

**权威 run**:
- 口径 + 过约束(F1/T1):`results/phase2_acoustic_attenuation_caliber/20260621T142249Z`(`summary_digest=3c7d47a6e4090d79016b8638395ed73a9a8c40384b385eb605d7c784131287a8`)
- 各向异性边界 + 声学紧致(决策 A):`results/phase2_acoustic_attenuation_anisotropy/20260621T142501Z`(`summary_digest=d2e0b9862be4dc08b86bad3454c4f43fe9e911ca5df838ad35836cb2bc5557b7`)
**脚本**:`scripts/phase2_acoustic_attenuation_caliber.py`、`scripts/phase2_acoustic_attenuation_anisotropy.py`
**口径**:diagnostic;baseline 不变(默认 `measured`+`current_zero`);默认 P2-6 `log|p'|` 测量不变,本征值/Prony 作为推荐诊断真值口径。
**复现性(缓存键已修)**:此前 `core/solver.py` 的 `_HIGH_MODE_MODAL_SYMBOL_CACHE`/`_ACOUSTIC_PHASE_OPERATOR_CACHE`/`_GHOST_PROJECTOR_OPERATOR_CACHE` 键**不含 `chi`(局部迹散度曲线)与 deviatoric 策略/曲线**,同进程内跨多个 `chi` 求 symbol 会被前一个 `chi` 的缓存污染(对角声学 ratio 随调用顺序在 1.265↔1.306 间漂移),曾导致一版 caliber run 误存 1.306。**2026-06-21 已在 core 给这三个缓存键补上 `chi`/deviatoric 字段(纯 correctness,单配置值不变,`pytest` 70 passed,并经"不清缓存按污染顺序"探针验证 chi_star 对角稳定回 1.265)**。诊断脚本仍保留清缓存为防御性兜底。下方数值为干净值。

### F1 声衰减测量口径(收口残差 #2)

- 弱阻尼声波的压力模态幅值是**前/后向两个声本征模之和**(初值不是精确离散本征模);`log|p'|` 线性拟合被微弱 beating 涟漪在短窗口压低、并随窗口漂移。压力天然隔离熵模态(熵等压 `p'=0`,在 `p'` 里不可见)。
- 精确**一步模态本征值** `σ=-log|λ|`(`core/solver.py:_high_mode_modal_symbol` 的真实周期 symbol)窗口无关、无拟合、无混入,且与动态 **Prony** 多指数分解完全一致。

| 方向 | 本征值(前向) | 动态 Prony | `log|p'|` 240 | `log|p'|` 480 | `log|p'|` 720 | 剪切 ν_ratio | 熵 α_ratio |
|---|---|---|---|---|---|---|---|
| x | **1.104** | 1.104 | 1.003 | 1.067 | 1.083 | 1.000 | 1.010 |
| diagonal | **1.410** | 1.411 | 1.233 | 1.437 | 1.458 | 1.002 | 1.019 |
| y | 1.104 | (=x) | — | — | — | 1.000 | 1.010 |

- 剪切/熵是**单一实本征值(无 beating)**,故动态拟合干净 → ν_T/α 标定本就正确。声学有共轭对 → `log|p'|` 偏置。
- 结论:窗口漂移是测量侧伪影,**不是闭合不稳**。

### 用本征值口径重标 `chi`

- 以本征值 x 声学=1 重标:`chi` 1.0852→`chi*=1.10524`。
- `chi*` 下窗口无关真值:x/y 声学=**1.000(精确)**、diagonal=**1.265**(前向;后向 1.277,近乎相等→无显著前后向劈裂),剪切/熵不变(1.000/1.002、1.010/1.019)。
- 即"x/y 声衰减→1"在窗口无关口径下严格成立;此前"1.003"为短窗口伪影;**diagonal 真实残差 = 1.265**(非短窗口的 1.23,也非缓存污染的 1.306;已发布 `chi` 下前向为 1.410)。

### T1 对角声衰减过约束定理(重定性残差 #1)

- 方形(D4)点阵下,最一般**局部线性**黏性闭合恰有 3 个独立系数:bulk(`chi`/λ,迹/A1)+ 两个剪切不可约表示模量 **B1**(`xx−yy`=`normal_factor`)与 **B2**(`xy`=`xy_factor`)。Schur 引理保证该三者是仅有的独立 D4 协变系数。
- 通道映射:`ν_T(轴)←B2`、`ν_T(对角)←B1`、`ν_L(轴)←B1+λ`、`ν_L(对角)←B2+λ`。
- 用 B2(轴剪切)、B1(对角剪切)、λ(轴纵波)钉死 3 旋钮后,`ν_L(对角)` 被**强制确定** → 对角残差对任何 D4 协变局部线性闭合**不可约**。
- symbol 有限差分敏感度矩阵 `d(quantity)/d(knob)` 数值证明该耦合结构(对角项为零、纵波双耦合 `ν_L,轴/d(chi)≈−5.21`、`ν_L,对角/d(chi)≈−5.13`),且 **d(ν_L,对角 − ν_L,轴)/d(chi)=0.081 ≪ 5.2 共模**:`chi` 几乎同步移动两个 `ν_L`,对角超出量(≈0.265×ref)~98% 与 `chi` 无关。
- 推论:能闭合对角残差的第 4 自由度**必须**非局部(Riesz / 纵波投影 `k̂k̂`)、非线性或带记忆;纯局部线性各向同性 stencil 必然无效。这把此前"实测无效"的反例提升为结构性 no-go。

### 决策 A:接受对角残差为有界结构性 GO-RISK 边界

权威 run `20260621T142501Z`(脚本 `scripts/phase2_acoustic_attenuation_anisotropy.py`)给出两条量化边界证据:

**(1) 各向异性边界(残差 #1)**。本征值口径(`chi*`)下声学 ratio 在点阵轴(0°/90°,含薄膜法向 y)为 **1.000(精确)**,沿 T1 的 B1/B2 角形 `1 + 0.265·sin²(2θ)` 单调升到 45° 对角的 **1.265(最大)**。残差被 45° 对角上界,轴向精确。`mode≥2` 的 ratio(轴 5.37、对角 6.91)是**另一根轴 high-mode 过阻尼(残差 #3)**主导,与低模态对角各向异性无关;故低模态对角边界在 mode1 陈述。

**(2) 声学紧致(物理可接受性)**。10 kHz 薄膜目标气体区由热/黏渗透深度定尺度:`δ_T≈26.6 μm≈6.65 cells`、`δ_ν≈22.4 μm≈5.59 cells`;声波长 `λ≈34.7 mm≈8675 cells`,`λ/δ_T≈1304`。在 Phase_1 探针位置 `y=8δ_T≈53 cells` 处 `kL≈0.0385 ≪ 1`(声学紧致),跨该距离累积的声幅衰减 `≈2.5e-7`,其中对角 30% 误差带来的额外项 `≈6.6e-8`——对 `p_hat` 影响可忽略。主导物理是各向同性正确的热/黏扩散(`α`、`ν`)与硬门各向同性量(`c`、`γ`、Galilean);薄膜法向是 y 轴(精确),45° 残差几何上偏离问题轴。

**结论(决策 A)**:对角声衰减残差 **1.265**(45°,本征值口径)为**有界、结构性(T1 不可约)、物理可接受**的 GO-RISK 边界,予以接受。不再尝试局部线性各向同性 stencil。残差 #2 已由 F1 收口(测量侧),残差 #3(high-mode 过阻尼)与残差 #1 解耦、单列。

## 9. 残差 #3:high-mode 声学过阻尼(RR 组合评估)

**权威 run**:`results/phase2_high_mode_acoustic_rr/20260622T051622Z`(`summary_digest=337bd893f58f84fe83ff9759847c0dcffe23641538d0b0d24d1e7604f2fd5ac4`)
**脚本**:`scripts/phase2_acoustic_high_mode_rr.py`
**口径**:diagnostic;baseline 不变。用本征值口径(high-mode 下 `log|p'|` 更不可靠)表征 high-mode 声学过阻尼及其与 RR 的组合。

声学阻尼 ratio `σ/(coeff·k²)`(本征值,窗口无关):

| 方向 | mode | baseline(current_zero) | RR(chi*) | 速度误差(RR) |
|---|---|---|---|---|
| 轴 | 1 | 5.97 | **1.000** | 0.5% |
| 轴 | 2 | 7.91 | 5.37 | 4.6% |
| 轴 | 3 | 9.65 | 12.27 | 11.1% |
| 对角 | 1 | 7.00 | **1.265** | 0.1% |
| 对角 | 2 | 10.87 | 6.91 | 9.3% |

**评估结论**:

1. **RR 只修 mode1**:轴 5.97→1.000、对角 7.00→1.265(=决策 A 的对角残差)。这复核了 baseline 低模态 ~6.27× 过阻尼(原始核心阻塞)。
2. **RR 与 high-mode 解耦**:高模态 RR 是 mode-dependent 混合效应(vs baseline:mode2 更好 7.9→5.4、10.9→6.9;mode3 轴更差 9.6→12.3),但**都仍 5–12× 过阻尼** → RR 的低模态标定不解决 high-mode,high-mode 是独立的另一根轴。
3. **过阻尼是闭合色散,非 filter**:high-wavenumber filter 对 ratio 仅贡献 0.03/0.11/0.24(mode1/2/3),远小于 4–11 的色散 excess;RR 轴 `excess ≈ 1.415·((k/k1)²−1)`(残差 0.075),即 ~k⁴ hyperviscous 色散过阻尼。
4. **速度也偏(默认 phase factor=1.0)**:高模态速度误差 4.6%/11.1%(轴 mode2/3)、9.3%(对角 mode2);项目既有 high-mode phase 修正只针对**速度/gamma**,不针对衰减,故即便修了速度,衰减仍过阻尼(与历史一致)。
5. **对 10 kHz 薄膜目标物理无关**:气体区声学紧致(`λ≈8675 cells ≫` 膜 ~几十 cells),工作在 `k→0` 极限,气膜内不发生 high-mode 声共振 → high-mode 过阻尼对 `p_hat` 物理无关(决策 A 的紧致论证推广到高模态)。

**处置(镜像决策 A)**:high-mode 声学过阻尼是**真实、色散驱动、RR 无关、有界、对紧致目标物理无关**的轴,接受为有界 GO-RISK 边界。production 级修复(若将来非紧致目标需要)需波数相关(spectral/dispersion)的衰减机制,与"本地闭合"目标冲突 —— 不在当前范围。

## 10. baseline 升级评估(评估记录;升级已于 2026-06-22 执行,见第 11 节)

**权威 run**:`results/phase2_rr_baseline_promotion/20260622T060549Z`(`summary_digest=8c3660c0566819581aa786f120c67e5b18f3f527befabcce14a3d609a2cce034`)
**脚本**:`scripts/phase2_robust_rr_baseline_promotion.py`
**口径**:本节为升级前的**评估记录**;基于此评估,RR 已于 2026-06-22 升级为默认 baseline(执行见第 11 节)。

在 `chi*=1.10524`(本征值重标)下跑 RR 全套门 + 长窗口 + ghost,并对照 baseline current_zero 的 P2-7:

| 门 | 结果(RR @ chi*) |
|---|---|
| P2-4 各向同性 | `PASSED`(x/y/diag=1.000/1.000/1.002) |
| P2-5 热扩散 | `PASSED` |
| P2-6 声速/gamma | `PASSED`(速度 0.49%、gamma 0.98%) |
| P2-6 衰减(诊断) | log\|p'\| 240 窗口 x/y=0.890、diag=1.127(弱阻尼偏低;本征值真值 x/y=1.000、diag=1.265,已接受 GO-RISK) |
| P2-9 Galilean | `PASSED`(0.77%、masking PASS) |
| low-k ghost | 稳定(max\|λ\|=1.000) |
| 长窗口 3× | 稳定(无 invalid/负温) |
| P2-7 整体扫描 | `FAILED`,但**仅 Pr=2 合成极值**失败(见下分点) |

**P2-7 分点明细(关键)**:目标气体是**空气,Pr≈0.706 < 1**;`pr_targets=[0.5,0.706,1.0,2.0]` 是**鲁棒性/通用性扫描**,非工作点集合。空气点容差 3%(`baseline_tolerance`),扫描点容差 5%(`scan_tolerance`)。

| Pr | baseline current_zero | RR @ chi* |
|---|---|---|
| 0.5 | 0.59% ✅ | 0.88% ✅ |
| **0.706(空气工作点)** | 0.41% ✅ | **0.18% ✅** |
| 1.0 | 0.99% ✅ | 1.01% ✅ |
| 2.0(合成,非空气) | 4.61% ✅ | 5.24% ❌(>5%) |

**判定(修订):RR @ chi* 在所有物理相关硬门上通过,包括空气工作点 P2-7(0.18%,优于 baseline 0.41%);唯一失败是非物理的 Pr=2 合成扫描极值(5.24% vs tol 5%,且仅边缘性地比 baseline 4.61% 略差)。** P2-7 与 `chi` 无关(两 `chi` 都 5.24%),Pr=2 的小误差来自 RR 偏量策略 `strain_rate_isotropic` 在高 Pr 的小剪切误差。

因此"是否升级"不再卡在物理门上,而是一个**验证口径策略问题**:P2-7 的 Pr=2 扫描点对**空气目标**应算硬 production 门,还是有界鲁棒性 GO-RISK?物理上(空气 Pr<1,Pr=2 永不出现)支持后者——按决策 A / 残差 #3 同样的"对物理无关的合成极值作 GO-RISK"逻辑,RR @ chi* 对空气目标实质已过全部物理相关门。

**决定(2026-06-22):已批准把 Pr=2 作有界鲁棒性 GO-RISK,并升级 RR 为默认 baseline。**

## 11. 升级执行(2026-06-22,默认 baseline 已翻转为 RR)

**已执行**(默认 baseline 从 `measured`+`current_zero` 翻转为 RR `chi*=1.1052362846829455`):

1. **配置** `configs/gas_air_10k_d2q37_physical_timestep.yaml` 翻转为 RR(`deviatoric_stress_policy=strain_rate_isotropic`、`trace_bulk_policy=ghost_orthogonal_local`、`trace_bulk_local_divergence_curve=[chi*]`、shear `0.4763606/0.8906392`);旧 current_zero 存为 `configs/gas_air_10k_d2q37_current_zero_baseline.yaml`。
2. **unit-mapping** `core/unit_mapping.py:d2q37_physical_timestep_config()`(规范 D2Q37 fixture)同步翻转为 RR;`core` 代码默认(策略未指定 fallback)保持 `measured`/`current_zero`,只由配置/fixture 选 RR。P2-00 测试更新为 RR 默认 + per-policy 默认曲线测试加 `pop` 兜底。
3. **P2-7 口径** `verification/prandtl_scan_measurement.py` 加 `hard_pr_max`:Pr>1 重分类为**鲁棒性 GO-RISK**(测量、上报 `robustness_status`、不阻塞 `p2_07_status`),硬门只卡 Pr≤1。生产配置设 `hard_pr_max: 1.0`。
4. **P2-6 口径** `verification/acoustic_wave_measurement.py` 加 `_prony_decay_rate`:上报 `acoustic_attenuation_measured_lu` 改为**窗口无关 Prony 口径**,`acoustic_attenuation_logabs_lu` 留次级,`acoustic_attenuation_caliber` 标记。

**生产验证(RR 默认下,动态/权威):**

| 门 | 结果 |
|---|---|
| P2-4 各向同性 | `PASSED`(x/y/diag=1.000/1.000/1.002) |
| P2-5 热扩散 | `PASSED` |
| P2-6 声速/gamma | `PASSED`(速度 0.49%、gamma 0.98%) |
| P2-6 衰减(Prony,诊断) | **x/y=1.000**、diag≈**1.31**(`log|p'|` 240 窗口 x/y=0.89、diag=1.13,弱阻尼偏低) |
| P2-7 | `PASSED`(硬门 Pr≤1 max 1.01%);Pr=2 鲁棒性 `GO_RISK`(5.24%) |
| P2-9 Galilean | `PASSED` |
| low-k ghost / 长窗口 | 稳定 |
| pytest(含 RR fixture) | 70 passed |

**口径注记(symbol vs dynamic,已复核 2026-06-23,见第 12 节)**:动态 Prony(生产 P2-6)给 diag≈**1.31**(权威);symbol 一步本征值口径给 diag≈**1.265**(对 diagonal 低 ~3%)。根因已查明(`scripts/phase2_acoustic_symbol_caliber_validity.py`,run `20260623T073022Z`):**单模态一步 symbol 抓不到周期 FFT 修正(dispersion + acoustic-phase)对 diagonal 模态的多步作用**——关掉这些修正,symbol 与动态对 diagonal 精确相等(均 1.876,gap=0);x/y 无此耦合故 symbol 与动态恒精确相等(1.000)。**结论:动态 Prony 为权威;凡 diagonal 声衰减取 ≈1.31。** 文中早前由 symbol 口径得出的 diag「1.265」均指此单模态值,真值以动态 1.31 为准;不影响任何结论(x/y=1.000 两口径一致、硬门全过、对角 1.27 与 1.31 在紧致目标下均物理可忽略,bounded-GO 不变)。

## 12. symbol 一步本征值口径的有效性边界(§5.5 item 1,2026-06-23 已复核)

**权威 run**:`results/phase2_symbol_caliber_validity/20260623T073022Z`(`summary_digest=51aa8970632b5077be04fec0ed408014c6ff0735cf15b2779eb498fa8fb28819`),脚本 `scripts/phase2_acoustic_symbol_caliber_validity.py`。

复核 symbol 一步本征值口径(F1/T1/anisotropy 用它)与动态 Prony(生产 P2-6 用它)在 `chi*` 对角的 ~3% 差异(symbol 1.265 vs 动态 1.307)。三步排除 + 定根因:

1. **非拟合窗口伪影**:动态 Prony 在 [10,240]/[480]/[720] 三窗口都 ≈1.307(窗口无关);x 三窗口都 =1.000。
2. **非选模错误**:diagonal symbol 在 c0 附近**只有两个**声学本征值(前 1.265 / 后 1.277,压力投影相同),**没有 1.307** 可选 → 单模态算子本身不含 1.307。
3. **根因 = 周期 FFT 修正**:对 diagonal,修正 **ON** gap=0.042(symbol 1.265 / 动态 1.307),修正 **OFF** gap=2.8e-5(symbol=动态=1.876,精确)。即 `dispersion_correction` + `acoustic_phase_correction` 这两类全局 FFT 修正对 diagonal 模态的**多步作用**,被单模态一步 symbol 漏掉;x/y 无此耦合,symbol 与动态恒精确一致(1.000)。

**结论**:**动态 Prony 为权威口径**(真实多步演化,生产 P2-6 即用它)。symbol 一步本征值口径**对 x/y 精确、对 diagonal 低 ~3%**;凡 diagonal 声衰减残差取动态 **≈1.31**(此前各处 symbol 口径的「1.265」为单模态低估值)。对结论无影响:升级判据(x/y=1.000)、T1 过约束(结构性,不依赖对角精确值)、决策 A / bounded-GO(对角 1.27 与 1.31 在 `kL≈0.04` 紧致目标下均物理可忽略)均不变。诊断;baseline 不变。

**口径**:默认 baseline 现为 RR;**升级 ≠ 声明 final M2 production pass**——默认携带已接受的声衰减 GO-RISK(对角 ≈1.31、high-mode 5–12×、P2-7 Pr=2 鲁棒性),`production_physics_status` 仍非 final pass。回退路径:`configs/…_current_zero_baseline.yaml` + `core` fallback 默认。

## 13. C2+→C3 更宽外推:RR 默认的 k-特异性与 high-mode 输运回归(2026-06-23,告诫性)

**权威 run**:`results/phase2_c3_extrapolation/20260623T091003Z`(`summary_digest=c4dd2e5302461493b5585ffa8dfe11b9fa692077333a6f120b00a02f4f3ab810`),脚本 `scripts/phase2_robust_c3_extrapolation.py`。四轴外推 RR 默认的硬门:

| 轴 | 结果 |
|---|---|
| **Pr(空气 0.5–1.0)** | P2-7 `PASSED`,max 1.0% ✓ 稳健 |
| **Mach(0–0.08)** | 验证到 0.05;0.08 处 P2-9 `FAILED`(速度误差本身仅 0.95%,某 sub-metric 在 0.08 超界)→ Galilean 包络 ≤0.05 |
| **波数(grid 64,mode 1/2/3)** | mode1 全硬门过;**mode2/3 全面失败**(ν 194%/509%、α 72%/87%、声速/gamma fail) |
| **分辨率(48/64/96,mode1)** | 仅 64 过;48(k=0.131)ν 47%、96(k=0.065)ν 34% |

**统一根因 — k 特异性**:误差随 |k − 0.098|(=nx64-mode1 标定 k)单调增长(96/mode1 k=0.065 误差最小,64/mode3 k=0.295 最大)。波数轴在**固定 64 grid**(无步数缩放干扰)独立确认 → **RR 默认输运闭合只在标定波数 k≈0.098 准,不随 k 泛化**。

**确认 high-mode 输运回归(关键,已验证)**:同一 mode2/x 剪切,**旧 current_zero baseline ν 误差 0.22%(`PASSED`)** vs **RR 默认 194%(`FAILED`)**。机制:dispersion 修正(`regularized_shear_*_dispersion_target=0.786/0.785` 等)是为旧 `measured` 偏量策略调的;RR 改用 `strain_rate_isotropic`(FD 应变率,自带 sin(k)/k 等高 k 因子),旧 dispersion targets 不再修正其高 k 应力 → mode≥2 输运失配。**即 RR 升级以"低 k 声衰减 6.27×→1.0"换取了"high-mode 输运(旧 baseline 本已通过)"。**

**对 bounded-production-GO 的影响**:紧致空气目标只激发最低模(mode1),mode1 全硬门通过 → **bounded-GO 仍成立**。但本发现把 RR 的代价刻画完整:不仅 high-mode 声衰减是 GO-RISK,**high-mode 输运也已回归**;RR 默认生产有效包络 = **(nx=64、mode1/k≈0.098、Pr 0.5–1.0、Mach≤0.05)**,比旧 baseline 在 k 维更窄。

**C3 判定**:**未建立广义 C3**。包络内(nx=64/低 k/Pr≤1/Mach≤0.05)硬门全过 → "包络内 C3"成立;超出包络(其他分辨率/高 k/Mach>0.05)闭合不泛化,须重标。

**决定(2026-06-23):接受 mode1-only 窄包络**。RR 默认 + bounded-GO 维持现状;RR 生产有效包络正式定为 **(nx=64、mode1/低 k —— 含输运与声学、Pr 0.5–1.0、Mach≤0.05)**;**high-mode(mode≥2)输运回归**与 high-mode/对角声学 GO-RISK 一并记为**已接受的有界边界**(紧致空气只激发 mode1,mode1 全硬门过)。**前提**:Phase_3 Level C 紧致空气 sim 须在此包络内运行(nx=64/低 k/Mach≤0.05)——列为 Level C 前置确认项。**不重标**高 k 修正,除非将来出现非紧致/高 k/其他分辨率目标(届时为 RR `strain_rate_isotropic` 策略重做高 k 标定)。说明:分辨率点的测量-vs-闭合未完全隔离(缩放步数拟合),但固定-grid 波数轴 + 旧/新 baseline 对照已使主结论(k 特异 + high-mode 回归)稳固,不影响本决定。
