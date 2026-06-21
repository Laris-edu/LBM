# Phase_2 D2Q37 Physical Bulk Viscosity / Acoustic Attenuation 路线诊断

**最后更新**：2026-06-19
**范围**：D2Q37 P2-6 声衰减过阻尼的来源分解,以及"物理体积黏性 vs `ν_b=0`"对修复路线的影响
**结论口径**：本文是诊断报告,不改变 baseline,不声明 final M2 production pass。`current_zero + auto_d2q37_tau32_linear` 仍是 baseline。
**权威 run**：`results/phase2_physical_bulk_viscosity/20260619T095054Z`(`summary_digest=6f2297ef8b5255631bd02985414ab7e25227e28200c1e2374d4bfd9263380a14`)
**复现脚本**：`scripts/diagnose_phase2_physical_bulk_viscosity.py`

## 1. 背景与动机

`docs/Phase_2/Phase2_D2Q37_Acoustic_Attenuation_Diagnosis.md` 已定位过阻尼主要来自 trace / bulk closure,并沿 ghost-orthogonal projector 方向推进(spectral 通过、local 系列在 diagonal 失败)。本文换一个口径复核:既然 `bulk_viscosity_policy=diagnostic_zero` 在物理上不准确(空气有 `ν_b≈0.6ν`),且 `ν_b=0` 在数值上恰好是迹弛豫的临界稳定点,那么用**物理一致**的设置(`bulk_viscosity_policy=specified` + `nu_b_lu>0` + `trace_bulk_policy=tau22`,使 target 公式自动含同一 `ν_b`)能否绕开 ghost 难题。

`tau22` 迹弛豫的标量保留因子在 `diagnostic_zero` 外为 `1-1/tau22`:`ν_b=0` 对应因子 `-1`(`|λ|=1`,临界),物理 `ν_b>0` 对应因子 `∈(-1,0)`(严格衰减)。

## 2. Stage A:过阻尼来源与体积黏性映射

P2-6(x 方向)衰减与稳定性扫描(run `20260619T095054Z` Stage A):

| 变体 | tau22 | 迹因子 | measured LU/step | target LU/step | ratio | c_err | g_err | invalid | 负温 |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| `current_zero` | 0.5000 | 0.000 | 1.393e-4 | 2.222e-5 | 6.270 | 0.48% | 0.95% | none | False |
| `tau22 ν_b=0.0ν` | 0.5000 | −1.000 | 3.910e-5 | 2.222e-5 | 1.759 | 0.48% | 0.96% | none | False |
| `tau22 ν_b=0.3ν` | 0.5304 | −0.885 | 4.522e-5 | 2.648e-5 | 1.708 | 0.48% | 0.96% | none | False |
| `tau22 ν_b=0.6ν` | 0.5608 | −0.783 | 5.133e-5 | 3.073e-5 | 1.670 | 0.48% | 0.96% | none | False |
| `tau22 ν_b=1.0ν` | 0.6014 | −0.663 | 5.948e-5 | 3.641e-5 | 1.634 | 0.48% | 0.96% | none | False |

判读:

- `current_zero`(`trace_post=0`)的 6.27× 过阻尼对应一个未声明的有效体积黏性。沿 `tau22` 扫描得 `effective_bulk_viscosity_slope = d(measured_coeff)/d(target_coeff) ≈ 1.437`,即该 regularized 中心矩迹弛豫的实际体积黏性约为名义 `nu_b_lu` 的 **1.44×**——`create_unit_mapping` 中 `tau22` 用的 `2S·θ/(D(D+S))=0.6θ` 系数低估了真实值。
- 所有 `tau22` 物理 `ν_b` 变体(因子 −0.66 ~ −0.88,严格稳定)在 240 步窗口内无 invalid、无负温;声速/gamma 不受影响(只动阻尼,不动色散)。
- ratio 不随 `ν_b` 趋于 1,而是趋于约 1.44(由上面的映射偏差给出的渐近),说明体积黏性映射偏差(a)只是次要项;主导项是与 `ν_b` 无关的残差(见 Stage C)。

## 3. Stage B:`ν_b=0` 临界 ghost 才是 P2-5/P2-7 失败真因

`Phase2_D2Q37_Acoustic_Attenuation_Diagnosis.md` §4.1 曾以 `tau22 trace_scale=1`(即 `ν_b=0`,因子 −1)失败为由,判定"改 trace 会破坏 P2-5/P2-7"。本文对照(Stage B,P2-5 x/y/diagonal)显示该判定需要修正:

| 变体 | 迹因子 | P2-5 | alpha 误差 | heat-flux 误差 | 任一方向 invalid |
|---|---:|---|---:|---:|---|
| `current_zero` | 0.000 | `PASSED` | 0.497% | 0.034% | False |
| `tau22 ν_b=0`(临界) | −1.000 | `FAILED` | **1181%** | 21.5% | **False** |
| `tau22 ν_b=0.6ν` | −0.783 | `PASSED` | 1.010% | 0.128% | False |

判读:

- 三者均无负温(`invalid=False`),所以 `ν_b=0` 的失败不是硬发散,而是**临界迹 ghost(`|λ|=1` 不衰减)污染了较长的热扩散模态拟合**(1181% 是拟合被污染,不是真实 α 改变,因为 α 由 `tau32`/heat-flux 决定,与迹无关)。
- 非单调模式(因子 0 通过、−1 灾难性失败、−0.78 通过)精确指向 `−1` 这个临界点本身,而不是"改 trace"。
- **物理 `ν_b`(因子 −0.78,严格衰减)让 ghost 衰减,P2-5/P2-6/P2-7 在 x/y/diagonal 上全过,且无需重标 heat curve。** Stage B2(物理 `ν_b=0.6ν`,沿用现有 heat curve):

  - P2-5:`PASSED`,alpha 误差 1.010%,Fourier-law 0.128%;
  - P2-6:`PASSED`,c_err 0.48%,g_err 0.96%,衰减 ratio 1.670,方向差 0.441%;
  - P2-7:`PASSED`,baseline Pr 误差 0.611%,全扫描最大 4.935%。

- 附带:标量 `tau22`(缩放实测迹)天然各向同性,因此 diagonal P2-5 也过(1.01%);这与 `ghost_orthogonal_local` 系列(用 `div_c(u)` 五点差分重构迹)在 diagonal 上 ~105% 失败形成对照——后者的 diagonal 问题来自方向性散度 stencil,不是迹闭合本身。
- 附带:`_low_k_ghost_stability` symbol 门(阈值 1.01)对临界 ghost 是盲的——因子 0/−1/−0.78 的低 k 谱半径都报 1.0(被守恒模的 `|λ|=1` 盖住),所以 `ν_b=0` 能"symbol 通过却动态 1181% 失败"。这是历史上"symbol pass ≠ dynamic pass"缺口的一个具体来源。

## 4. Stage C:纵波各向同性墙(声衰减残差的真正瓶颈)

物理 `ν_b` 下衰减仍 ~1.67×(诊断级)。残差分解:在 `ν_b=0.6ν` 处超出量约 82% 与 `ν_b` 无关;因 P2-5 的 α 已校到 1%,声学里的热阻尼 `0.2α` 应当正确,故残差最可能是**纵波(normal-stress)黏性**。固定物理 `ν_b=0.6ν` 扫 `regularized_shear_normal_factor`(Stage C,P2-6 x + P2-4 x/y/diagonal):

| normal_factor | P2-6 | 衰减 ratio | c_err | P2-4 | shear_x | shear_y | **shear_diag** |
|---:|---|---:|---:|---|---:|---:|---:|
| 0.70 | `PASSED` | 2.285 | 0.48% | `FAILED` | 0.53% | 0.53% | 104% |
| **0.90** | `PASSED` | **1.670** | 0.48% | `PASSED` | 0.53% | 0.53% | **0.67%** |
| 1.00 | `PASSED` | 1.403 | 0.48% | `FAILED` | 0.53% | 0.53% | 46% |
| 1.10 | `PASSED` | 1.159 | 0.48% | `FAILED` | 0.53% | 0.53% | 88% |
| 1.30 | `PASSED` | 0.726 | 0.48% | `FAILED` | 0.53% | 0.53% | 162% |

判读:

- 增大 `normal_factor` 单调把衰减 ratio 从 2.285 拉到 0.726,约 `normal_factor≈1.25` 穿过 1——证实残差是纵波黏性,且纵波黏性确实是可调的杠杆。
- 但 `normal_factor=0.9` 是**唯一**让 P2-4 diagonal 横波剪切正确的值(0.67%);任何偏离都灾难性破坏 diagonal 剪切(46%/88%/104%/162%)。x/y 横波剪切全程 0.53% 不变(走 `xy_factor`,与 `normal_factor` 无关)。
- 自由度已用尽:`xy_factor` 被 x/y 剪切钉死,`normal_factor` 被 diagonal 剪切钉死,纵波声学黏性是被动确定的(=1.67×),无独立旋钮。迹通道也补不上:它只能把纵向黏性降到 `ν_b=0` 临界点(ratio 1.76),再低即因子 `<−1` 的 ghost 失稳。
- **一个标量 `normal_factor` 无法同时满足 diagonal 横波剪切和纵波声学黏性。** 理想各向同性牛顿流体里同一个 μ 决定所有方向横波剪切和纵波偏量黏性,本应自动一致;这里需要 `xy_factor=0.8739 ≠ normal_factor=0.9` 两个标量补各向异性,而该补偿只对横波成立、对纵波声学不成立。

## 5. 结论与对修复路线的影响

1. **声衰减 ratio→~1 无法靠当前闭合的局部标量标定实现。** 残差是纵波/normal-stress 黏性过大,与 diagonal 横波剪切共用同一 `normal_factor` 而彼此冲突;ghost-orthogonal 路线(修 trace 通道)也到不了 ~1,因为瓶颈不在 trace。
2. **统一根因**:声衰减残差(纵波各向同性墙)与 diagonal P2-5 热流失败(见 `Phase2_D2Q37_Ghost_Orthogonal_Trace_Closure.md` §14.4)是**同一类缺陷**——regularized 应力/热流投影不是真正各向同性/完备的,逐通道标量因子补不齐 D2Q37 的方向性。
3. **物理 `ν_b` 路线的价值**:本地标量 `tau22` + 物理 `ν_b`(严格稳定)让 transport gate(含 diagonal)全过、无 ghost、无投影,并把声衰减从 6.27× 改善到 ~1.67×。它是比 `current_zero` 更干净的 baseline 候选,但本身**不是** final M2 production pass(声衰减仍诊断级,且尚未跑 P2-9/high-mode/长窗口)。
4. **推荐下一步**:推进各向同性 / recursive-regularized 的应力(及热流)闭合——让偏量黏性真正各向同性,横波/纵波由单一 μ 自动一致,从根上同时解决声衰减残差与 diagonal 热流,而不再依赖逐通道标量补偿。

## 6. 边界与不可误判

- 本文全部为 diagnostic;未改 baseline,未声明任何 production pass。
- 物理 `ν_b` 候选只跑了 P2-4/P2-5/P2-6/P2-7;**未**跑 P2-9 Galilean、high-mode acoustic 和长窗口鲁棒性,不能据此声明输运/声学 production。
- `effective_bulk_viscosity_slope≈1.44` 与"normal_factor 增大减小 ν_L"的解析解释只作定性指引;精确系数需在各向同性闭合推导中给出。
- 不把"物理 `ν_b` 严格稳定且保 transport gate"写成"声衰减已修复";声衰减 hard pass 仍受纵波各向同性墙阻塞。
