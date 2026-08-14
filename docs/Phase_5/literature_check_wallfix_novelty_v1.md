# 投稿前文献核查（第一轮：边界发现的 novelty 与家族普遍性）

**版本**：LITCHECK_v1（第一轮，2026-08-11）
**性质**：文献检索记录，非模拟单元；不产生 gate 声明，不改变任何 Gate / `FINAL_PRODUCTION_NOT_CLAIMED`
**方法**：Crossref / OpenAlex / Semantic Scholar 三个开放 API 直连（会话内 WebSearch/WebFetch 后端不可用，改用 API 直查；查询语句与命中数逐条记录，可复现）
**核查对象**：`wallfix_a2a5_counterproof_report.md` + `NSF_hot_basestate_tangent_arbitration_report.md` 的对外声明

---

## 1. 结论摘要

| 待核查声明 | 状态 | 依据 |
|---|---|---|
| 湿节点/非平衡外推热壁家族"被广泛使用" | **已核实成立** | Guo–Zheng–Shi (2002, Phys. Fluids) 被引 **733**；Boundary conditions for thermal LBE method (JCP 2012) 被引 **204**；Thermal boundary condition for the thermal LBE (PRE 2005) 被引 95 |
| "有限温升下热壁给出错误响应趋势"此前已被系统报告 | **未发现正面命中**（第一轮，标题/摘要级） | 见 §3 各检索式与命中数；最近邻域是稀薄滑移离散效应（不同域）与大温差 bulk 建模（不同层） |
| LBM 用于 thermophone / 热声换能器 | **实为空白** | `thermophone` 全领域 159 篇；`thermophone AND "lattice Boltzmann"` **1 篇且不相关**（声子 Peierls–Callaway 输运）；`"lattice Boltzmann" AND thermoacoustic` 18 篇，全为热声机/谐振腔/制冷机，无膜致声 |
| LBM 语境下的 "thermal admittance" 观测量 | 命中 **0** | 该观测量在 LBM 文献中未被使用（我们经 Phase_1 半空间导纳引入） |

**第一轮判断**：核心声明（家族普遍性）已坐实；novelty 关口（趋势错误此前未被报告）**未被证伪，但也未被穷尽证实**——第一轮只做到标题/摘要级，尚缺引用网络追踪（见 §5）。

## 2. 已核实：边界家族的普遍性

| 文献 | 年 | 出处 | 被引 | 与本项目的关系 |
|---|---|---|---|---|
| An extrapolation method for boundary conditions in lattice Boltzmann method (Guo, Zheng, Shi) | 2002 | Phys. Fluids | **733** | 非平衡外推湿节点族的源头；我们的 v1.1 壁属同一构造谱系（平衡部分按规定宏观量重建 + 内部非平衡拷贝） |
| Boundary conditions for thermal lattice Boltzmann equation method | 2012 | J. Comput. Phys. | **204** | 热 LBE 边界条件的主流综述/构造工作 |
| Thermal boundary condition for the thermal lattice Boltzmann equation | 2005 | Phys. Rev. E | 95 | 热边界条件专文 |
| Discrete effects on boundary conditions for the LBE in simulating microscale gas flows | 2007 | Phys. Rev. E | 113–122 | **概念先例**：LBM 边界的离散效应可污染物理系数 |
| Discrete effects on thermal boundary conditions ... microscale gas flows | 2008 | EPL | 11–14 | 同上，热版本 |

→ 报告与论文中"该边界家族被广泛使用"的表述**可以保留**，并应引 Guo 2002 + JCP 2012 作为家族锚点。

## 3. Novelty 关口：检索式与命中（第一轮）

全部为 OpenAlex `title_and_abstract.search` 精确字段检索（除注明外）：

| # | 检索式 | 命中 | 判读 |
|---|---|---|---|
| A | `thermophone` | 159 | 领域规模小但真实（Arnold–Crandall 1917 起） |
| B | `thermophone AND "lattice Boltzmann"` | **1** | 唯一命中为声子输运，与热声无关 → **LBM×thermophone 空白** |
| C | `"lattice Boltzmann" AND thermoacoustic` | 18 | 全为热声发动机/谐振腔/制冷机（驻波热声），无膜致声 |
| D | `"lattice Boltzmann" AND "thermal admittance"` | **0** | 观测量本身未被使用 |
| E | `"lattice Boltzmann" AND "wet node"` | 5 | 均为浅水/多孔/反应流，与热边界无关（"wet node"一词在 LBM 里多用于自由面语境） |
| F | `"lattice Boltzmann" AND "thermal boundary condition" AND accuracy` | 9 | 曲面边界处理、通量评估类，无工作点趋势议题 |
| G | `"lattice Boltzmann" AND "large temperature difference"` | 12 | **最近邻域**：Regularized thermal LBM for natural convection with large temperature differences (2018, 55) 等——议题是 **bulk 模型**（非 Boussinesq、变物性），不是边界导致的响应趋势错误 |
| H | `"lattice Boltzmann" AND "non-Boussinesq"` | 12 | 同上 |
| I | `"lattice Boltzmann" AND thermal AND boundary AND spurious` | 5 | 均为多相/浸没边界伪流类，与本议题无关 |
| J | `"lattice Boltzmann" AND "boundary condition" AND "numerical artifact"` | 3 | 无关 |

**最近邻域的区分（须写进论文的 related work）**：

- **稀薄滑移离散效应（PRE 2007 / EPL 2008）**：域=微尺度稀薄（Knudsen 物理），格式=平衡分布+镜面/反弹**链式**格式，被污染量=**滑移/温度跳跃系数**，且作者给出了修正方案。
  **我们**：域=连续（无稀薄），格式=**湿节点整行重钉扎**，被污染量=**响应对基态的导数（工作点趋势符号）**，且证明了在四不变量内**不可修**。
  → 二者是同一"离散效应"大类下的**不同实例**；这条先例对我们有利（类别已被学界承认），应正面引用并明确区分。
- **大温差/非 Boussinesq 热 LBM（2018 等）**：处理的是**体相**闭合（变物性、可压缩性），与边界实现无关；与我们正交。

## 4. 对论文定位的影响

1. **家族普遍性声明可用**（§2），这是"发现具有普遍参考价值"的支点。
2. **novelty 第一轮未被证伪**：没有检索到"有限温升下热 LBM 壁的响应趋势错误"的既有报告。
3. **应用侧为空白**：LBM×thermophone 无先例，`thermal admittance` 观测量在 LBM 文献中未被使用——这支持"首次"类表述，但**必须限定**（"据我们所知/第一轮检索范围内"）。
4. **叙事建议**：把工作放进 PRE 2007/EPL 2008 开创的"LBM 边界离散效应"传统里，作为**连续域、响应导数层面的新实例 + 不可修性证明**，而不是孤立的新发现——既准确又更易被审稿人接受。

## 4b. 引用网络追踪（第二轮首段，2026-08-11 同日执行）

对四篇锚点（Guo2002 `W2069455332` 826 引、JCP2012 `W1995432234` 204 引、PRE2007 `W2114693935` 140 引、EPL2008 `W2071481679` 14 引，合计 1184 篇施引）做服务端联合过滤 `cites:<id>` × `title_and_abstract.search:<term>`：

| 施引筛选 | 命中 | 判读 |
|---|---|---|
| Guo2002 × `"temperature difference"` | 5 | 均为应用（眼内房水、微通道换热、状态方程耦合），无边界精度议题 |
| JCP2012 × `"temperature difference"` | 3 | 纳米流体自然对流、盖驱动腔、湍流通道——应用类 |
| PRE2007 × `"temperature difference"` | 0 | — |
| Guo2002 × `"discrete effect"` | 2 | 曲面无滑移壁、单节点对流扩散格式 |
| PRE2007 × `"discrete effect"` | 3 | **对流扩散方程边界格式的离散效应族** |
| JCP2012 × 热边界 ∧ (error∨accuracy) | 21 | 曲面边界/共轭传热/Neumann 格式/Dirichlet 格式——**无一涉及基态依赖的响应趋势** |

**发现的关键先例（须引用并区分）**：Zhang–Chai–Shi 一系的"边界格式离散效应"分析，代表作 *Discrete effect on the halfway bounce-back boundary condition of MRT LBM for convection-diffusion equations* (2016, 56 引)。其结构是：

> 边界格式产生**数值滑移**（∝ 格距二阶）→ **通过调节 MRT 中与二阶矩对应的自由弛豫参数可以消除**（BGK/SRT 除非取特殊值否则消不掉）。

**与本工作的对照（论文 related work 的核心段落）**：

| | Zhang–Chai–Shi 传统 | 本工作 |
|---|---|---|
| 伪迹形态 | 数值滑移/跳跃（边界值偏移） | **响应对基态的导数**（工作点趋势符号）出错 |
| 载体 | ghost 矩经自由弛豫参数传播 | **宏观能量记账**（cv·ρ·θ_w）——微观形状自由度实测惰性 ≤1.1e-6 pp |
| 补救 | **存在**：调自由弛豫参数即可消除 | **证明不存在**（四不变量内穷举，`WALLFIX_FAMILY_NULL`） |

→ 定位建议升级为：**"在离散效应分析的传统里，我们给出第一个标准补救策略（利用格式自由度）可证明失效的实例"**——比"发现一个新伪迹"更强、也更容易被该子领域的审稿人接受。

**由此暴露的审稿问题——已于 2026-08-13/14 用测量回答（B 机双向权威 run，详见 `ghost_relax_scan_report.md`）**：

> **τ>1（保留 ghost）把 d_OP 推得更负（−2.83→−4.24 @Θ=0.05），远离连续解，τ≥1.08 失稳；τ<1（标准过弛豫）方向正确但生产网格上仅 τ≥0.99 合法，最后合法点仍差 3.03/5.83 pp，外推穿越点 τ≈0.967 落在崩溃区内、且需付出 −28% 冷态导纳偏移。标准补救双向失败。**

因此本报告 §1 的定位（"第一个标准补救策略可证明失效的实例"）由**结构论证 + 双向实测**共同支撑，不再只是论证。以下为该问题被回答前的原始记录（保留以存溯源）：该传统的标准补救是**调自由弛豫参数**，而 wallfix 穷举只覆盖了**边界重构侧**的自由度，没有直接测过"改弛豫参数能否移动 d_OP"。

- 结构论证（间接）：A2-5 的密度因子是宏观记账事实（行内能必须 = cv·ρ_w·θ_w），不经 ghost 模传播；而本单元实测"一切 ghost 形状变化惰性"恰恰佐证该效应非 ghost 介导——弛豫参数作用于 ghost 衰减率，因此预期无效。
- 但这是论证不是测量。**建议第二轮补一个廉价诊断**：在 wallfix rig 上扫描自由弛豫参数（纯诊断口径，不改生产标定——生产 (tau,k) 由 Phase_2/3 输运标定钉死，合同禁止为过门改动），看 d_OP 是否移动。若不动，这条审稿线即被封死。

## 5. 第一轮的局限与第二轮清单（未完成）

**局限**：仅标题/摘要级关键词匹配。这类结论很可能藏在方法论文的验证小节里而不进标题/摘要，因此**当前不足以支撑"首次报告"的强声明**。

**第二轮必做**：

1. **引用网络追踪**：取 Guo 2002、JCP 2012、PRE 2005、PRE 2007 的**施引文献**（各数百篇），按"边界精度/温度依赖/验证"筛选，读候选者的验证小节。
2. **全文级检索**：用支持全文的库（Google Scholar / Scopus / Web of Science，需机构权限）跑 §3 的检索式，特别是 G/H 两族的全文。
3. **邻近学科**：有限差分/有限体积热边界的"离散壁厚"类误差是否有对应文献（可提供更一般的语言）。
4. **待读全文**：PRE 2007（113 引）与 EPL 2008 的正文——确认其分析框架是否可直接迁移到我们的连续域情形（若可，我们的结构论证可挂靠其形式主义，增强说服力）。
5. **期刊定位复核**：thermophone 领域 159 篇的主要载体（J. Appl. Phys./APL/Nanoscale 等）与方法学载体（PRE/JCP/Comput. Fluids）如何取舍，结合 APC 与学院认定。

**检索可复现性**：全部检索经 OpenAlex/Crossref/Semantic Scholar 公开 API，检索式如上表逐条记录；执行日期 2026-08-11。


