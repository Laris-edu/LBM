# 连续 NSF 热基态切线仲裁模拟计划书

**版本**：PLAN_v1.0  
**日期**：2026-08-11  
**执行状态**：EXECUTED（2026-08-11，A 机权威 run `20260811T055850Z` `COMPLETED`；结果唯一家=`NSF_hot_basestate_tangent_arbitration_report.md`——LBM-equivalent 介质情况 A/D、`ROUTE_LBM_BOUNDARY` 维持强化；本计划原文冻结不回改）  
**性质**：专项数值仲裁计划；用于判断当前 LBM 负工作点响应属于连续热声物理还是 LBM 热壁有限热偏置下的边界实现效应  
**直接背景**：WP4-JAB 第二轮已定位 A2 的强负贡献几乎全部来自 A2-5（壁面内能目标与 `g` 重钉扎），A3 为多个 bulk 项强相消后的净补偿结构。

---

## 1. 模拟目的

当前结果显示：

\[
d_{OP}^{LBM}(0.05)=-2.835\%,
\qquad
d_{OP}^{LBM}(0.10)=-5.317\%,
\]

而 QS-1 给出相反的正趋势：

\[
d_{OP}^{QS1}(0.05)\approx+2.35\%,
\qquad
d_{OP}^{QS1}(0.10)\approx+4.64\%.
\]

同时，A2 细粒度消融已经表明，LBM 热壁中的 **A2-5：内能目标与 `g` population 重钉扎的热态 Jacobian** 承担了 A2 几乎全部负贡献。

因此本计划只回答一个决定性问题：

> **在没有任何 LBM `g`-population 重钉扎操作的连续 NSF 中，仅依靠真实热基态、完整 bulk 动力学和定温壁边界，是否也会得到负的工作点增量热导纳趋势？**

若连续 NSF 仍为正，则 LBM 反号主要应归入热壁 finite-bias tangent consistency / boundary methodology 问题。

若连续 NSF 也为负，则说明存在真实连续体热基态动力学，需要继续研究 QS 为什么失效。

---

# 2. 几何与工况

采用与当前 G4a/JAB 对应的一维 canonical column：

\[
0<y<H_s.
\]

- \(y=0\)：热壁 / 膜面；
- \(y=H_s\)：环境等温热沉；
- 频率：10 kHz；
- 保持与现有 canonical sink 相同的 \(H_s\)；
- 不引入横向变化；
- 不考虑有限宽二维效应。

工作点：

\[
\Theta_{DC}
=
\frac{\bar T_w-T_0}{T_0}
\in
\{0,\ 0.05,\ 0.10\}.
\]

对应：

\[
\bar T_w
=
T_0(1+\Theta_{DC}).
\]

---

# 3. 第一步：求连续 NSF 的 DC 热基态

基态设：

\[
\bar u(y)=0.
\]

稳态压力：

\[
\frac{d\bar p}{dy}=0,
\]

因此：

\[
\bar p=\mathrm{const}.
\]

稳态温度满足：

\[
\frac{d}{dy}
\left(
k\frac{d\bar T}{dy}
\right)=0.
\]

第一轮仲裁建议先采用与 Route-B 对应的冻结输运参数：

\[
k,\mu,c_p,c_v=\mathrm{const}.
\]

因此：

\[
\bar T(y)
=
\bar T_w
-
\frac{\bar T_w-T_0}{H_s}y.
\]

密度由理想气体状态方程：

\[
\bar\rho(y)=\frac{\bar p}{R\bar T(y)}.
\]

### 质量约束

连续模型必须与 LBM canonical column 保持同一总质量。

因此 \(\bar p\) 由下式确定：

\[
\int_0^{H_s}\bar\rho(y)\,dy
=
\rho_0 H_s.
\]

禁止简单固定：

\[
\bar p=p_0
\]

而忽略热基态导致的封闭列平均压力调整。

---

# 4. 第二步：构造完整热基态线性化 NSF

令：

\[
\rho=\bar\rho+\rho',
\qquad
u=u',
\qquad
T=\bar T+T',
\qquad
p=\bar p+p'.
\]

采用单频形式：

\[
\{\rho',u',T',p'\}
=
\Re
\left[
\{\hat\rho,\hat u,\hat T,\hat p\}
e^{i\omega t}
\right].
\]

## 4.1 连续方程

\[
i\omega\hat\rho
+
\frac{d}{dy}
(\bar\rho\hat u)
=
0.
\]

即：

\[
i\omega\hat\rho
+
\bar\rho\frac{d\hat u}{dy}
+
\hat u\frac{d\bar\rho}{dy}
=
0.
\]

必须保留：

\[
\boxed{
\hat u\,\bar\rho_y
}
\]

这一热基态梯度项。

## 4.2 动量方程

\[
i\omega\bar\rho\hat u
=
-\frac{d\hat p}{dy}
+
\mu_L\frac{d^2\hat u}{dy^2}.
\]

其中 \(\mu_L\) 为一维纵向有效黏性系数。

第一轮可采用现有 1D NSF 仪器中已经验证的黏性定义，不另行发明新的闭合。

## 4.3 能量方程

采用温度形式：

\[
i\omega\bar\rho c_v\hat T
+
\bar\rho c_v
\hat u
\frac{d\bar T}{dy}
=
-\bar p
\frac{d\hat u}{dy}
+
k
\frac{d^2\hat T}{dy^2}.
\]

必须保留：

\[
\boxed{
\bar\rho c_v\hat u\,\bar T_y
}
\]

这一扰动速度与 DC 温度梯度耦合项。

## 4.4 状态方程

\[
\hat p
=
R
\left(
\bar T\hat\rho
+
\bar\rho\hat T
\right).
\]

这一步必须围绕局部热基态 \(\bar T(y),\bar\rho(y)\) 线性化，而不是统一使用冷态 \(T_0,\rho_0\)。

---

# 5. 第三步：边界条件

## 5.1 热壁 \(y=0\)

施加真正的连续定温壁增量条件：

\[
\boxed{
\hat T(0)=\hat T_w
}
\]

以及无渗透：

\[
\boxed{
\hat u(0)=0.
}
\]

不额外规定：

\[
\hat\rho(0)
\]

也不人为规定壁面内能扰动：

\[
\hat E_w
=
c_v
(\bar\rho\hat T+\bar T\hat\rho).
\]

密度、压力及所需热流均由连续方程组自动决定。

## 5.2 等温热沉 \(y=H_s\)

\[
\hat T(H_s)=0,
\]

\[
\hat u(H_s)=0.
\]

---

# 6. 核心模拟矩阵

只做 6 个主算例。

## 模型 A：Full hot-base NSF

保留全部热基态梯度项：

- \(\hat u\bar\rho_y\)；
- \(\hat u\bar T_y\)；
- 局部 \(\bar\rho(y),\bar T(y)\)；
- 完整 EOS 线性化。

工作点：

1. `NSF_FULL_DC000`
2. `NSF_FULL_DC005`
3. `NSF_FULL_DC010`

## 模型 B：No-base-gradient diagnostic

使用完全相同的 DC 基态和边界条件，但人为去掉：

\[
\hat u\bar\rho_y
\]

和：

\[
\bar\rho c_v\hat u\bar T_y.
\]

其它系数仍在热基态求值。

该模型不是物理模型，只用于回答：

> LBM/QS 差异是否可能来自扰动场与非均匀 DC 基态梯度之间的动态耦合？

工作点：

4. `NSF_NOGRAD_DC000`
5. `NSF_NOGRAD_DC005`
6. `NSF_NOGRAD_DC010`

---

# 7. 统一输出量

只使用与现有 LBM/JAB 同定义的气侧增量热导纳：

\[
Y_g
=
\frac{\hat q_w}{\hat T_w}.
\]

连续 NSF 中：

\[
\hat q_w
=
-k
\frac{d\hat T}{dy}
\bigg|_{y=0}.
\]

因此：

\[
Y_g
=
-
\frac{
k\,\hat T_y(0)
}{
\hat T_w
}.
\]

定义工作点比：

\[
D_{OP}(\Theta_{DC})
=
\frac{
Y_g(\Theta_{DC})
}{
Y_g(0)
}.
\]

主幅值指标：

\[
d_{OP}
=
\left(
|D_{OP}|-1
\right)\times100\%.
\]

同时报告相位：

\[
\Delta\phi_{OP}
=
\arg D_{OP}.
\]

---

# 8. 必须对照的现有结果

最终只需形成下面这张表：

| 模型 | \(d_{OP}(0.05)\) | \(d_{OP}(0.10)\) | 相位趋势 |
|---|---:|---:|---|
| QS-1 | +2.35% | +4.64% | 已有 |
| 现有 1D NSF | 正值 | 正值 | 已有 |
| LBM TAN/JAB | −2.835% | −5.317% | −1.38° / −2.62° |
| Full hot-base NSF | 待算 | 待算 | 待算 |
| No-gradient NSF | 待算 | 待算 | 待算 |

---

# 9. 结果判决

## 情况 A：Full NSF 为正

若：

\[
d_{OP}^{NSF}>0
\]

并与 QS-1 / 现有 1D NSF 同向，而 LBM 仍为负：

\[
QS\approx NSF>0,
\qquad
LBM<0,
\]

则结论优先为：

> **LBM 的负工作点趋势不是连续 NSF 在该 canonical 热基态下的物理结果，而主要与当前热壁 A2-5 energy-repinning Jacobian / boundary–bulk tangent consistency 有关。**

下一步进入 LBM boundary methodology 路线。

## 情况 B：Full NSF 为负

若：

\[
d_{OP}^{NSF}<0
\]

且幅值与 LBM 同量级，则说明：

> **负工作点趋势可以由连续 NSF 的热基态增量动力学产生。**

此时重新打开 thermophone finite-bias physics 路线，并继续追问：

> QS-1 漏掉了哪些完整热基态动态项？

## 情况 C：Full NSF 为负，但 No-gradient NSF 转正

若：

\[
d_{OP}^{NSF,full}<0
\]

而：

\[
d_{OP}^{NSF,nograd}>0,
\]

则可明确判断：

> **反号主要来自扰动速度与非均匀 DC 温度/密度基态梯度的动态耦合。**

这将成为真实连续体机制的强候选。

## 情况 D：Full NSF 与 No-gradient NSF 都为正

则：

> 基态梯度动态项不足以解释 LBM 反号；现有证据进一步支持 LBM 热壁 finite-bias tangent inconsistency。

---

# 10. 数值验证要求

该仲裁模拟不需要复杂 Gate，但至少必须完成：

1. \(\Theta_{DC}=0\) 时退化回既有冷态线性 NSF；
2. 网格细化后 \(Y_g\) 收敛；
3. 热壁和热沉 Dirichlet 条件满足；
4. 总质量约束对应的 DC 基态压力求解正确；
5. 输入 \(\hat T_w\) 缩小一半后 \(Y_g\) 不变；
6. Full 与 No-gradient 在 \(\Theta_{DC}=0\) 必须重合；
7. 不通过人为调节参数使 NSF 靠近 LBM 或 QS。

---

# 11. 当前不做的内容

本阶段不做：

- 温变真实空气物性；
- Route-A；
- 新频率；
- H2/H3；
- 大幅值非线性；
- 二维有限宽 thermophone；
- 修改 LBM 热壁；
- A3 进一步组合穷举。

这些都应等待连续 NSF 仲裁结果后决定。

---

# 12. 最终验收问题

本轮模拟只需要回答两句话：

1. **没有任何 `g`-population 重钉扎的连续定温壁 NSF，是否会自然得到与 LBM 相同的负 \(d_{OP}\)？**
2. **若会，负趋势是否由 \(\hat u\bar T_y\) / \(\hat u\bar\rho_y\) 这类热基态梯度耦合产生？**

只要这两个问题得到明确答案，当前研究就可以决定下一阶段究竟进入：

```text
thermophone finite-bias physics
```

还是：

```text
LBM thermal-boundary methodology
```
