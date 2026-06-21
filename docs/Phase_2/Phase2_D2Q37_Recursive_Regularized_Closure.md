# Phase_2 D2Q37 Recursive-Regularized (Local) Closure 里程碑

**最后更新**：2026-06-21
**范围**：本地各向同性 / recursive-regularized 二阶闭合(应变率偏量 + `div` 迹)对声衰减的修复,及其完整门况
**结论口径**：diagnostic;baseline 不变;不声明 final M2 production pass。`deviatoric_stress_policy=measured` + `trace_bulk_policy=current_zero` 仍是 baseline。
**权威 run**：`results/phase2_recursive_regularized_closure/20260621T083625Z`(`summary_digest=60c7f8940256d98276173b5e9059296f5b09cff5a035fb606ef83e7048d9ef84`,含 P2-4/5/6/7/9 + 长窗口)
**复现脚本**：`scripts/diagnose_phase2_recursive_regularized_closure.py`

## 1. 背景

`docs/Phase_2/Phase2_D2Q37_Physical_Bulk_Viscosity_Diagnosis.md` 已定位:声衰减残差是纵波 normal-stress 黏性,且与 diagonal 热流同属各向同性/完备性缺陷,指向各向同性 / recursive-regularized 应力+热流闭合。复核分两步:

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

**这是第一个本地、稳定且让 x/y 声衰减 ratio→~1、同时保 `ν_T` 各向同性 + P2-5 + P2-9 的闭合**,把项目核心阻塞(x/y 声衰减 6.27×)修到 1.003。此前只有非本地 `ghost_orthogonal_spectral` projector 拿到过 ratio≈0.88。关键是完整 RR 的一致重构:`div`-based 迹提供独立纵波旋钮 `chi`,在 `ν_T` 各向同性钉死后单独把 `ν_L,x` 调到 ν,且对纯 trace ghost(`div=0`)自动为零 → ghost 稳定。

## 5. 已表征的残差(均非发散,均有清晰机理)

1. **diagonal 声衰减** 1.23(长窗口到 1.46):diagonal-纵波(`normal_dev=0`、`shear_rate≠0`、`div≠0`)走 **xy 通道 + `chi`**,而 x-纵波走 **normal 通道 + `chi`**;`xy_factor` 与 `chi` 都被 x 钉死后 diagonal-纵波黏性被动确定。本质是 **4 约束(`ν_T,x/ν_T,diag/ν_L,x/ν_L,diag`)对 3 旋钮的过约束**;各向同性 `div`/应变率 stencil 均不能闭合(实测无效)。
2. **声衰减随拟合窗口漂移**(x 1.00→1.08,diag 1.23→1.46):声阻尼极弱(`σ≈2.2e-5/step`,720 步振幅仅变 ~1.6%),衰减拟合对微小扰动敏感;diagonal 漂移更大,可能含慢效应。
3. **P2-7 极值 5.24%**:Pr 扫描变 `α`(tau32)而非 `ν`(tau21 固定),故 `g_dev(tau21)` 对其无影响;失败点 `Pr=2` 由 α/heat-flux 既有特性(≈baseline 4.94%)+ 高 Pr 小 RR `ν` 误差合成,非偏量旋钮可修。
4. **high-mode acoustic** 未覆盖(RR 修的是低模态,high-mode 是另一轴,需与 high-mode 修正组合)。

## 6. 定性与边界

- **定性:强 GO-RISK 候选**,把核心阻塞从 6.27× 修到 x/y ~1.0(本地、稳定);但因 diagonal 残差 + 声衰减窗口依赖 + P2-7 边缘 + high-mode 未覆盖,**不是窗口无关的干净 production pass**。
- diagnostic;baseline 不变(默认 `measured` + `current_zero`)。
- 不把本里程碑写成 final M2 production pass。

## 7. 下一步

1. diagonal 声衰减:4 约束/3 旋钮过约束需要第 4 个自由度(区分 diagonal-纵波 xy 通道贡献的项),或接受其为 GO-RISK 残差。
2. 声衰减窗口依赖:复核是否为弱阻尼拟合敏感(测量侧)或 diagonal 慢效应(闭合侧);必要时改进声衰减测量口径。
3. P2-7 极值:属 heat-flux 高 Pr 特性,与 RR 解耦,后续在 heat-flux 闭合工作中处理。
4. high-mode:评估 RR 与 high-mode acoustic 修正的组合。
5. 若残差收敛或明确接受为 Phase_3 限定边界,再评估是否把 RR 升级为默认 baseline(届时同步 core/config/unit mapping/全套文档)。
