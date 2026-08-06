# 论文一稿件架构（WP2 后工作版）

| 项目 | 当前口径 |
|---|---|
| 日期 | 2026-08-05(v0.2;v0.1=2026-08-02) |
| 文档状态 | `ARCHITECTURE_v0.2`；WP2/WP3/WP4 证据全部锁定(D5-6 子矩阵闭合 + QS-1k/WP4-TAN 机理判别),进入写作与定稿轨 |
| 基础投稿 | JASA 优先，JSV 备选；PRA 仅在合同升级条件满足后评估 |
| 科学主线 | 有限温升 thermophone 的工作点非线性、周期内动力学与经认证的 2f 出射声学模态 |
| 模型口径 | `ROUTE_B_MAIN + 1D_REAL_AIR_BOUNDING` |
| 生产口径 | `FINAL_PRODUCTION_NOT_CLAIMED`；本文档不构成 `SCOPED_GO` 或 WP4 授权 |
| 规范来源 | `Phase5_instruct_v1.2.md` §1、§14、§18–§20；状态与 Gate 现值以 `Phase5_STATUS.md` 为准 |

本文档把合同 §20 的通用八节结构实例化为**可写作、可制图、可追溯**的稿件蓝图。它只维护论文叙事、章节职责、主张—证据映射和图表接口；Gate 阈值、run 数值和阶段状态仍分别留在合同、专项报告与 `Phase5_STATUS.md`，避免重复维护。

---

## 1. 一句话论文与叙事选择

### 1.1 推荐的一句话论文

> 在参考态输运闭合的全非线性热 LBM 中，有限温升 thermophone 的增量换能不能由偏移工作点上的静态线性重求值充分预测；经质量中性热壁、有效物性、谐波传递与算子消融逐层认证后，可分辨出符号相反的动力学非线性残差，并将其与 2f 出射声学模态及膜—气热容竞争联系起来。

这句话分成两层(v0.2:两层均已锁定):

- **WP2 已锁定**：认证链成立；`Theta_DC=0.05` 处 `D_OP=-2.83%`，而 QS-0/QS-1 约为 `+2.4%`，符号相反；20 kHz 的 L2-2f 传递与算子侧条件已闭合。
- **WP3/WP4 已完成(2026-08-04/05)**：残差随 `Theta_DC` 的标度=五点近线性(`-101 pp/单位`,微亚线性;加密点落内插线 0.04pp);来源判别=**排除链闭合**(QS-1k:静态重求值族三级结构性失效;WP4-TAN R1:生产 `D_OP` 即切线响应,0.005pp;R2:残差场无高 k 色散带特征,箱尺度/全局)——机理最终归属按 §7.1 的 "consistent with" 口径如实开放;A1 生产 H2 全阶梯(H2_q/ε 四位恒定、m₂=1.999、D_G∝ε² 被分辨);1D 双分支互证(DC 臂五点单一约定系列);`chi_0/chi_eff` 统一图景(A5 v2 十点,7.1× 滚降,幅值线性)。数据唯一家=`Phase5_STATUS.md` §6.1。

因此现在应按**物理论文**组织，而不是把 Phase_1–5 写成开发流水账，也不建议改写成纯方法论文。方法与 Gate 的作用是让中心物理结论可信，而不是与中心结论争夺篇幅。

### 1.2 推荐题目方向

首选工作题目：

> **Dynamic nonlinear residuals in finite-temperature thermophone transduction resolved by a verified thermal lattice Boltzmann framework**

备选，更偏 JASA：

> **Operating-point and harmonic nonlinearities of a planar thermophone: a lattice Boltzmann and one-dimensional reference study**

中文内部题名：

> **有限温升平面热声换能中的工作点非线性与谐波响应：经认证的热格子 Boltzmann 与一维参考研究**

题名暂不使用 `real-air nonlinear LBM`、`far-field THD`、`finite-width CNT thermophone`，因为三者分别超出路线 B、L2-2f 和 G5 的当前授权。

### 1.3 论文的三个贡献层

1. **物理主贡献**：区分平均工作点效应与周期内动力学；检验 QS-0/QS-1，给出静态重求值规则的适用边界及动力学残差。
2. **声学贡献**：在 10/20 kHz 传递与算子链认证后，对 2f 使用 outgoing acoustic-mode 的 L2 定量口径，而不是把固定近场点谐波误写为辐射 THD。
3. **方法支撑贡献**：D2Q37 热 LBM、质量中性热壁、帐篷式 canonical 热沉、双 1D 参考、多谐波拟合和确定性不确定度共同形成可审计证据链。

第三层只为前两层服务。G1b 失败谱系、P4-1 判死过程、跨机计算纪律等不进入主叙事，只在确有解释价值时进入补充材料。

---

## 2. 核心问题、主张与完成条件

### 2.1 论文问题树

```text
有限温升是否改变 thermophone 的增量换能？
├─ 平均工作点：D_OP(Theta_DC) 能否由 QS-0 / QS-1 预测？
│  ├─ 能 → 给出工作点修正规则与适用域
│  └─ 不能 → 定量动力学残差、标度、来源与检测边界
├─ 周期内动力学：D_G 与 H2 如何随 epsilon_AC 变化？
│  ├─ D_G 可检测 → 给出基频增益非线性起点
│  └─ D_G 近线性 → 给出严格上界，并以 H2 为主动态信号
└─ 膜—气竞争：上述规律如何随 chi_0 / chi_eff 迁移？
   ├─ 形成统一 regime map
   └─ 若材料外推 → 明示 material_relevance，不冒充 CNT 实际材料点
```

### 2.2 主张矩阵

| ID | 预期主张 | 当前状态(v0.2,2026-08-05) | 最少补证据 | 论文位置 |
|---|---|---|---|---|
| C1 | 热—膜—声链在线性极限和绝对基频远场上受控 | **已锁定，scoped** | 无；只需压缩成验证图/表 | Methods + Verification |
| C2 | 生产壁质量中性，幅值包络认证至 `epsilon_AC=0.075` | **已锁定** | 无；`0.10` 作为出包络点，不进入生产矩阵 | Verification |
| C3 | 实测增量增益与 QS-0/QS-1 符号相反，存在动力学非线性残差 | **已锁定(趋势全确认)** | 无——四工作点 {0.02,0.05,0.075,0.10} 全部反号(§6.1),1D 配对齐 | Results I |
| C4 | 动力学残差的来源与标度可被判别 | **已锁定(标度实测+来源排除链)** | 无——标度=五点近线性 −101pp/单位(加密点 0.04pp 命中);来源判别=三重排除:QS-1k(≠任何静态 α(T,k) 重求值,三级结构性失效)+TAN R1(≠有限幅值,切线恒等 0.005pp)+TAN R2(≠高 k 场异常→箱尺度/全局动力学);**最终机理归属按 §7.1 "consistent with" 口径如实开放,不属本主张范围** | Results I |
| C5 | A1 基频增益近线性或存在可检测偏离，并产生二阶标度 H2 | **已锁定** | 无——全阶梯七点:D_G∝ε² 被分辨(至 −2.85e-3,教科书 14.02 vs 14.06)、H2_q/ε 四位恒定跨 75×、m₂=1.9992、空检/旧壁/1D 齐 | Results II |
| C6 | 2f 可作为 L2 outgoing acoustic-mode harmonic 定量声明 | **已锁定(数据侧)** | 写作层组装:生产 H2(A1 阶梯)×G2 认证链数值拼接为 L2-2f 结果段;不得升级为 L3 远场 THD | Results II |
| C7 | `chi_0/chi_eff` 组织工作点与周期内非线性 regime | **已锁定(scoped)** | 无——A5 v2 十点全稳定:7.1× 滚降/相位→−86°/D_chi 幅值线性;围栏=χ₀=0.01 仪器稳定性边界截断(v1 实测)+大 `C_A` 点 material_relevance=synthetic | Results III |
| C8 | 1D 真实空气分支给出主结论的定量边界，而非把路线 B LBM 写成真实空气局部物性模型 | **已锁定** | 无——DC 臂五点双分支单一约定系列(δ/24 收敛 0.001pp)+A1 双分支腿;三层参照层级四点全成立 | Results I/II + Discussion |

### 2.3 可以立即写与必须等待的边界(v0.2:数据等待全部解除)

现在可完成：**全部八节**,含摘要定量结论句、Results I 趋势图与机理排除段、Results II 生产 H2 标度、Results III regime map、结论设计规则。主图 I/II/III 工作版已由 `scripts/phase5_wp4_results_figures.py` 从 M5_runs 归档生成。题目取向:数据支持突出 `dynamic residual`(不可约性已由 QS-1k/TAN 排除链证明,`operating-point correction` 作为被否定的对照概念进入正文)。

仍必须等待:投稿前文献核查(合同 §22,落笔"据本文覆盖的检索范围所知")、终稿 C1–C8 逐句审计与 §6 不可误判审计、Table 3 数值终填。

---

## 3. 正文章节架构

### 1. Introduction

#### 1.1 Thermophone 的线性图景与应用背景

- 用最短篇幅建立 Joule 加热—膜温—气侧热边界层—声辐射链。
- 说明目标声学马赫数极低，本文研究的不是非线性声传播或激波，而是有限温升下的换能非线性。

#### 1.2 现有缺口

- 传统线性/小扰动模型不能自动回答平均温升后的增量增益、源区谐波和膜—气反馈如何变化。
- 数值上，热壁质量源、有限波数有效输运和谱/滤波算子都可能伪造 DC/H2，因此“算出谐波”不等于识别物理谐波。
- 文献首创性只在投稿前检索后落笔，统一使用“据本文覆盖的检索范围所知”。

#### 1.3 本文问题与变量

- 引出 `epsilon_AC`、`Theta_DC`、`chi_0/chi_eff` 三变量框架。
- 给出核心问题：工作点重求值是否足够；若不足，剩余动力学非线性的来源、标度和检测边界是什么。

#### 1.4 贡献概述

- 一项物理贡献、一项声学谐波贡献、一项方法支撑贡献，各写一句。
- 不在引言列举 G0/G1/G2/G3/G4 编号；Gate 名称只在 Methods/Verification 出现。

### 2. Methods

#### 2.1 Physical configuration and nondimensional state variables

- 自由悬浮平面薄膜、对称双侧空气、10 kHz 基线、法向/周期范围。
- 三个无量纲变量与 `C_A`、`P_mean/P_1` 的关系。
- 区分 A1 有符号零均值数值消融、A2a 稳态工作点增量、A5 膜—气竞争地图。

#### 2.2 Thermal lattice Boltzmann model

- D2Q37 `f-g`、SMRT、全非线性守恒方程、状态恢复与冻结映射。
- 准确定义路线 B：参考态输运闭合下的全非线性理想气体；明确它不是 EOS-only，也不等价于局部真实空气 `mu(T),k(T)`。
- 有效物性采用 G0 的有限波数表格携带，不以单一幂律外推整个波数域。

#### 2.3 Film–gas boundary and coupling

- v1.1 对称质量中性热壁及边界质量/能量审计。
- 帐篷双带几何是 canonical `T(H_s)=T_ambient` 的周期实现，不写成新热沉模型。
- 膜 ODE、`cv` 重钉扎记账与半隐式耦合；只声明 G4a canonical 沉几何、`chi_0=0.016` 点已认证。

#### 2.4 Reference hierarchy and operating-point corrections

- Phase_1 线性参考、1D-lbm-equivalent、1D-physical-air 三者职责。
- QS-0：代表工作点标量重求值；QS-1：完整 DC 基态线性化。
- 定义 `G1`、`D_G`、`D_OP`、H2/H3、`U_gov`。

#### 2.5 Harmonic and outgoing-mode analysis

- N=5 多谐波联合拟合、`x(t)=Re[x_hat exp(i Omega t)]`、预注册窗口与去趋势。
- 2f 声明链：源区 H2 → 20 kHz G2-T → G2-A/G2-O → L2 outgoing acoustic mode。
- 明示 L2 不等于远场 L3；20 kHz 粗声学载体的 `+5.67%` 色散和约 `+4%/跨度` 增益是携带属性。

#### 2.6 Verification and uncertainty protocol

- 用一段解释 Gate 哲学：每个物理主张先排除模型、壁面、幅值、传递和算子混淆。
- `U_gov=max(U_det,U_95,fit)`，网格/窗口/状态匹配域高/空检进入确定性预算。
- 说明 scoped 继承：M3 幅值约 `±5.4%`；M4 是 `PASSED_WITH_SCOPED_RISK`；无 clipping/floor/positivity repair/结果回调。

### 3. Verification

#### 3.1 Linear thermofluid and acoustic chain

- 压缩呈现 M2/M3/M4：热/声核、Level A/B/C 互证、10 kHz 基频远场 `0.60 Pa / 86.6 dB`。
- 绝对幅值携带 M3/M4 scoped 误差；该结果只作基线可信度，不抢占非线性 Results。

#### 3.2 Nonlinear reference and effective transport

- G3 的平衡、收敛、能量与 ringdown 认证。
- G0 的 `alpha_eff(T,k)` 表格与路线 B/1D 分支定义；强调有限波数口径。

#### 3.3 Boundary and amplitude envelope

- 质量中性、旧壁诊断性、导纳小幅值回归。
- `epsilon_AC<=0.075` 认证；`0.10` 的 1.41% 双通道漂移作为包络边界实测，不写成求解器崩溃。

#### 3.4 Harmonic transfer and operator cleanliness

- G2-T 10/20 kHz；G2-A outgoing-mode 纯度；G2-O 算子敏感性 `Delta H2<=1.3%` 与数值底板。
- H3 未触发，统一留在 diagnostic-only。

#### 3.5 DC base state and coupled row

- 状态匹配域高、稳态、窗口、初态和双柱对照。
- 耦合行 1.0376@+1.05° 只证明 canonical 沉几何的基线闭环，不补写成 G1b 全幅值包络通过。

### 4. Results I — Operating-point nonlinearity

这是全文的第一主结果，篇幅与图位优先级最高。

#### 4.1 State-matched DC base states

- 展示 `Theta_DC={0,0.02,0.05,0.10}` 基态剖面和状态匹配。
- 固定目标 `Theta_DC` 的域高检查与固定 `P_mean` 的物理热沉敏感性必须分图或分面，不能混称收敛。

#### 4.2 Incremental gain versus operating point

- 主横轴 `Theta_DC`，主纵轴复 `D_OP`（幅值与相位）。
- 每个点同时给 LBM、QS-0、QS-1、1D-lbm-equivalent、1D-physical-air 与 `U_gov`。

#### 4.3 Failure boundary of static re-evaluation

- 以 `Theta_DC=0.05` 的符号相反结果为锚,四点 {0.02,0.05,0.075,0.10} 标度已实测(0.075=预注册加密点,图注注明非 §15.2 网格点)。
- 正式量名(对外统一,图轴/正文一致):**dynamic–quasi-static discrepancy** `R_dyn=D_OP^LBM-D_OP^QS1`——避免只用"QS 失败"定性描述;内部文档的"残差标度律"即此量。
- 实测:QS-0≈QS-1(差 ~0.05pp)但两者均反号于 LBM → 基态形状修正不足实证成立;`R_dyn` 五点近线性 −101pp/单位、微亚线性 ~6%。

#### 4.4 Mechanism discrimination and real-air bounding(已执行,写作按排除链组织)

- **排除链(全部预注册、先提交后出数)**:①QS-1k——G0 实测 α_eff(k,T) 全表的 k 分辨静态重求值更正不更负(+2.1→+10.7%),高 k 温度指数(4.0/5.4/3.1)均大于 k1(2.04)→ 静态族结构性够不到负号;②WP4-TAN R1——切线(ε→0)外推与生产值差 0.005/0.007pp → 排除有限幅值;③TAN R2——残差场高 k 能量分数低于冷底板且随 Θ 下降 → 排除高 k 色散带场异常。收窄结论:箱尺度/全局动力学效应。
- 双 1D 分支:全非线性连续介质(携 k1 实测律)仍正号 → 残差不在"变物性连续介质"内;真实空气定量由 physical 分支定界。
- 最终机理归属用 "consistent with" 口径;三判别 run(`M5_runs/wp4_qs1k_*`、`wp4_tan_*_B`)为 Discussion §7.1 的直接证据。

### 5. Results II — In-cycle dynamics and harmonic generation

#### 5.1 Fundamental incremental response

- A1 全阶梯七点已闭合(WP4 单 run `20260803T113507Z`,参照/空检/对照自含;与 WP3 四重合点打印位一致=复现行)。
- 报告 `G1/G1,0`、`D_G` 和相位:`D_G∝ε²` 被分辨(非上界口径——至 −2.85e-3,远小于 3% 但成干净标度,按"被分辨的微小偏离"写)。

#### 5.2 Second-harmonic scaling

- H2 主图采用符号对偶组合、空检底、`U_gov` 和局部斜率 `m2`。
- 生产壁为主数据；旧壁只作为“诊断对照有牙齿”，不得进入不确定度带。
- 1D 两分支给出真实空气定量边界与路线 B 的模型内结果。

#### 5.3 From source harmonic to outgoing acoustic mode

- 把生产 H2 接入 G2 认证链，给 L2-2f outgoing-mode 结果。
- 不使用 `far-field THD`；除非未来逐频完成 L3 认证，否则 2f 远场 SPL 不进入正文结论。

#### 5.4 Upper bounds and third harmonic

- H3 只报诊断或上界；不增加 30 kHz 主图。
- 若 H2 某通道接近底板，优先写成可复现的严格上界与检测边界。

### 6. Results III — Regime map

#### 6.1 `chi_0 × epsilon_AC` response map

- 主图同时提供 `chi_0` 设计坐标与 `chi_eff` 解释坐标。
- 基线邻近点优先；`chi_0>=1` 视材料支持状态标为 regime extension。

#### 6.2 Unified interpretation

- 在同一图中组织 `D_OP`、`R_dyn`、H2 和可选 `D_G` 的主导区。
- 目标是给出“工作点修正有效区—动力学残差区—膜热容控制区”的可复用规则，而不是堆参数热图。

#### 6.3 Conditional transient evidence

- 少量 A3 可用于说明工作点迁移；A2b 先 1D、LBM 条件执行。
- 若不增加对主线的解释力，A3/A2b 放补充材料，不占 Results III 主图位。

### 7. Discussion

#### 7.1 Physical meaning of the dynamic residual

- 讨论为什么偏移工作点的静态线性理论会给出错误符号，以及有限波数闭合/动态热层如何进入。
- 只讨论数据能区分的机制；对尚未独立分离者使用“consistent with”而非“caused by”。

#### 7.2 What is universal and what is model-bounded

- 普适结构：工作点与周期内动力学的分离、QS 检验框架、`chi` 组织方式、H2 声明层级。
- 模型定量：路线 B LBM 数值。
- 真实空气边界：1D-physical 分支；不得把其数值回填成 LBM 的局部物性结论。

#### 7.3 Numerical confounders as scientific controls

- 质量源、有限波数表、算子消融、状态匹配域高如何把伪非线性排除在主张之外。
- G1b 密封无沉 rig 的结构性失败只作为“为什么生产几何必须有物理热沉”的控制证据；不展开四 run 开发史。

#### 7.4 Scope and transferability

- 10 kHz 主基频、20 kHz 2f、法向/x 周期、紧致薄膜、G5 waived。
- M3/M4 scoped 继承、无有限宽 directivity、无 L3、无 H3 强声明、无路线 A。
- 讨论低 HCPUA/基线 CNT 参数与大 `C_A` 合成 regime-extension 点的材料相关性。

### 8. Conclusion

结论只回答四件事：

1. 工作点重求值在何处有效、何处失效；
2. 动力学残差与 H2 的量级/标度/检测边界；
3. `chi_0/chi_eff` 如何组织设计区间；
4. 哪些结论是路线 B 模型内、哪些由 1D 真实空气分支定界。

不在结论复述开发过程、Gate 编号或所有误差数字。

---

## 4. 主图与表格架构

### 4.1 正文主图（建议 7 张）

| 图 | 核心问题 | 建议面板 | 当前就绪度 | 证据入口 |
|---|---|---|---|---|
| Fig. 1 | 研究对象与判别框架是什么？ | (a) 薄膜—双侧气体—热沉几何；(b) A1/A2a/A5；(c) `epsilon_AC,Theta_DC,chi`；(d) QS-0/QS-1 与动力学残差逻辑 | 可制作 | 合同 §1/§3/§11；`dc_protocol_report.md` |
| Fig. 2 | 模型链是否可信？ | (a) Level A/B/C 线性互证；(b) 1D 收敛；(c) 10 kHz 基频远场链；(d) 总误差/范围条 | 数据已锁定 | M3/M4 报告；`nonlinear_1d_reference_report.md` |
| Fig. 3 | 数值伪非线性是否被排除？ | (a) `alpha_eff(T,k)`；(b) 质量中性/旧壁对照；(c) 幅值包络；(d) G2-T/A/O 谐波认证摘要 | 数据已锁定 | G0、G1-W、G1a、G2 报告 |
| Fig. 4 | 工作点如何改变增量换能？ | (a) DC 基态；(b) `D_OP(Theta_DC)`；(c) 相位；(d) 状态匹配域高/固定 P 分离 | **数据齐**(G4a/P-DC2/dc002/dc0075 四 run;基态剖面在各 run signals) | G4a + P-DC2 + A2a-WP4 |
| Fig. 5 | 静态修正为何失效？ | (a) LBM vs QS-0/QS-1/**QS-1k**；(b) **dynamic–quasi-static discrepancy** 标度+U_gov 带；(c) 1D 双分支；(d) **切线外推 Y(ε) vs ε²(TAN R1)+ 排除链摘要** | **数据齐**;工作版=`figures/fig_results_I`(生成器 `phase5_wp4_results_figures.py`) | G4a、P-1D、QS-1k、WP4-TAN |
| Fig. 6 | 周期内非线性如何出现并进入声学 2f？ | (a) `D_G` ε² 标度；(b) H2 阶梯与 `m2`；(c) 空检/旧壁/算子控制；(d) L2 outgoing-mode H2 | **数据齐**;工作版=`figures/fig_results_II`((d) 待写作层拼接 G2 链) | A1 全阶梯、G2 |
| Fig. 7 | 膜—气竞争如何组织 regime？ | (a) `chi_0×epsilon` 传递滚降；(b) `chi_eff` 坐标；(c) 相位/一致性;(d) material relevance+仪器边界 | **数据齐**(A5 v2 十点;v1=边界诊断);工作版=`figures/fig_results_III` | A5 |

如果期刊版面需要压缩，优先把 Fig. 2 与 Fig. 3 各保留两块主面板，其余移补充材料；Fig. 4–6 不压缩，因为它们承载论文的物理主张。

### 4.2 正文表格

| 表 | 内容 | 备注 |
|---|---|---|
| Table 1 | 模型路线、协议和状态变量 | 只列读者理解正文所需的定义，不复制合同 metadata |
| Table 2 | 认证链与允许声明 | 用“混淆因素—控制—剩余范围”三列，替代大段 Gate 史 |
| Table 3 | 代表性主结果与不确定度 | 最终稿再填；只放能支撑 C3–C7 的数值 |

### 4.3 补充材料

- S1：D2Q37/SMRT 与映射细节、速度集和闭合公式。
- S2：M2–M4 完整验证、Kirchhoff manufactured cases、误差预算。
- S3：G0 有效物性表、插值和有限波数范围。
- S4：质量中性壁构造、旧壁对照、G1b 密封无沉 rig 失败与 canonical 沉几何闭合。
- S5：多谐波拟合、窗口/空检、G2-T/A/O 全表与算子消融。
- S6：WP3/WP4 全算例矩阵、1D 双分支、材料相关性标记和复现 metadata。

---

## 5. WP3/WP4 与论文图表的直接接口

### 5.1 WP3 当前八单元如何入稿

| 单元 | 论文消费位置 | 必须形成的可画量 |
|---|---|---|
| P-LIN | Fig. 6 基准/空检 | `G1,0`、相位、H2 底板、合法性 |
| P-AC1 | Fig. 6 初始 H2 标度 | H2、局部 `m2`、`D_G` |
| P-AC2 | Fig. 6 主动态点 | H2 vs `U_gov`/空检、L2 接口、1D 双分支 |
| P-AC3 | Fig. 6 认证上限 | 0.075 点与包络边界；不得补跑 0.10 生产点 |
| P-DC1 | Fig. 4/5 中央锚 | 已有 `D_OP=-2.83%` 与 QS 符号相反 |
| P-DC2 | Fig. 4/5 趋势 | `Theta_DC=0.10` 的 `D_OP`、QS 残差、H2、`chi_eff` |
| P-H2 | Fig. 3/6 认证链 | 已有 G2-T/A/O 三门与 20 kHz 携带属性 |
| P-1D | Fig. 5/6 模型定界 | A1 0.05 与 A2a 0.05/0.10 双分支方向和标度 |

WP3 的直接目的不是“再证明有论文”，而是决定 C4–C6 能否组成同一条机制链，并为 `SCOPED_GO` 提供认证子矩阵依据。

### 5.2 WP4 子矩阵执行结清(v0.2;D5-6 批准,2026-08-03/04 全部完成)

对照 v0.1 的最小集合,执行与偏差记录:

1. A2a:✅ 0.02 补全 + **0.075 加密点也已执行**(预注册可选项,标 densification 非网格点)——五点标度律。
2. A1:✅ 全阶梯以**单 run 自含**方式重跑七点(优于拼接;四重合点=复现行)。
3. A5:✅ 含 `chi_0=3`(十点全稳定);**`chi_0=0.01` 被仪器稳定性边界实测判死**(v1 诊断归档),v2 换认证基线 0.016——"ε=0.10 截断"同族处理。
4. 定向机制单元:✅ QS-1k(静态族三级否证)+ WP4-TAN(切线恒等+场解剖)——正是围绕 Fig. 5 判别力设计的两刀。
5. A3/A2b:未执行(不在 SCOPED_GO 授权内;现有材料未显示其对主线的解释增益,维持补充材料/1D 口径)。

H3/30 kHz、F1、大规模频扫、完整 G5 和路线 A 均未执行,不属于本稿集合(不变)。

### 5.3 叙事分支决议(v0.2:数据已选路)

| v0.1 预设分支 | 决议 |
|---|---|
| `D_OP` 趋势稳定，1D 与 LBM 方向/标度互证 | **部分成立→合并升级**:趋势五点稳定;1D 在认证域互证、在 D_OP 上与 LBM 分歧——按预注册判读,该分歧即发现本身 |
| `D_OP` 稳定但 1D 与 LBM 分歧明显 | **与上行合并为现行主叙事**:dynamic residual(不可约性由排除链证明)+ 模型差异由 1D 双分支定界;真实空气机制不归因 |
| A1 `D_G` 弱、H2 清楚 | **落空(更好)**:D_G 未跨 3% 但被分辨为干净 ε² 标度——Results II 双信号(H2 主 + D_G 标度),无需上界口径 |
| A1 H2 也接近底板 | 未发生(H2 四位恒定,高于底板 ~4 量级) |
| P-DC2 触发域高或稳定性复验 | 未触发(全部四点 \|D_OP\|<10% 预注册线) |

---

## 6. 写作纪律与不可误判表

| 不写 | 应写 |
|---|---|
| 真实空气有限温升 LBM | 参考态输运闭合下的全非线性理想气体 LBM；真实空气由 1D 分支定界 |
| 远场 THD | source-region H2 或 L2 outgoing acoustic-mode H2 |
| A1 代表真实 Joule 加热 | A1 是有符号零均值热功率数值消融 |
| 帐篷双带是新热沉模型 | canonical 等温热库在周期域中的无跳变实现 |
| G1b 证明膜—气系统物理不稳定 | 密封无沉 fixture 的反馈结构不可闭合；canonical 有沉几何的耦合行已通过 |
| epsilon=0.10 生产失败 | 0.10 超出双通道能量审计认证包络；生产上限为 0.075 |
| 20 kHz 介质缺陷 | 20 kHz 载体的已表征色散/空间增益，作为下游携带属性 |
| H3 是第三谐波主结果 | H3 diagnostic-only，30 kHz 未触发 |
| 所有点是实际 CNT 材料 | 大 `C_A` 点按 material relevance 标为 regime extension |
| Gate PASSED 等于 final production | WP2 只完成入口认证；最终生产仍未声明 |

---

## 7. 写作与制图顺序(v0.2:步骤 1–3 已完成)

1. ~~现在~~ ✅ 骨架与接口建立(v0.1)。
2. ~~WP3 权威 run 后~~ ✅ 八单元完成,`SCOPED_GO` 材料成立(D5-6 批准)。
3. ~~用户批准 WP4 后~~ ✅ 子矩阵闭合 + 机理判别两单元;Fig. I/II/III 工作版已生成(`figures/`,可再生)。
4. **当前步骤——生产矩阵已冻结**:写 Introduction/Methods/Verification/Results I–III 全稿与摘要、结论、题目定稿、Table 3;做投稿前文献复查(合同 §22),确定 JASA/JSV 首投。
5. **终稿前**：逐句执行 C1–C8 主张审计与本文件 §6 不可误判审计；所有图注写明模型路线、Gate 层级和 scoped 范围(0.075 加密点、χ 边界截断、material_relevance 必须入图注)。

---

## 8. 当前架构结论(v0.2)

- 论文的中心不是“我们搭建了一个复杂 LBM 工具链”，而是“静态工作点修正何时失效，以及失效后剩余动力学非线性如何被识别和组织”——**该中心命题的证据现已全量在库**:失效=三级静态族结构性反号;识别=切线恒等+排除链;组织=标度律与 χ regime map。
- 全部 C1–C8 主张锁定(C4/C6 的机理归属与 L2 拼接属写作口径,非数据缺口);`FINAL_PRODUCTION_NOT_CLAIMED` 在论文层面对应"模型内结论+1D 定界"的声明纪律,不阻塞投稿轨。
- 剩余工作全部在写作层:八节全稿、Table 3、图注审计、文献核查、题目定稿(数据支持突出 dynamic residual)。
- 当前最现实且最聚焦的首投范围是 JASA；JSV 保留为更偏数值方法/系统响应的备选定位。
