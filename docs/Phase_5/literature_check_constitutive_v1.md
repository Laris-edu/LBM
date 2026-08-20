# 投稿前文献核查（第三轮：本构根因定位的三个断言）

| 项 | 值 |
|---|---|
| 版本 | **CHECK_v1**（本构轮第一版，2026-08-20） |
| 性质 | 文献检索记录，非模拟单元；不产生 gate 声明，不改变任何 Gate / `FINAL_PRODUCTION_NOT_CLAIMED` |
| 检索源 | OpenAlex `title_and_abstract.search` 直连 API（主）；Semantic Scholar Graph API（元数据/OA 抽查）；arXiv API + e-print TeX 源码逐行 grep（全文级抽查 3 篇）。会话内 WebSearch / WebFetch 后端不可用（与 2026-08-11 LITCHECK_v1 轮相同），Scopus / ScienceDirect MCP 未挂载 |
| 方法口径 | skill `nature-academic-search` 的 No-MCP fallback 路径；全部检索式与命中数逐条记录（§5），可复现；执行日期 2026-08-20 |
| 核查对象 | 本构根因定位的三个对外断言：① 变弛豫 τ(T,ρ) 是否为热 LBM 成熟标准做法；② 常数 τ 本构（k∝ρ）误差是否已被定量刻画到符号级；③ 热声/thermophone LBM 应用的输运律处理现状 |
| 铁律执行 | 全部 DOI 逐条来自检索结果原文；verbatim 引句注明 arXiv 源码出处；"未检索到"（NOT_FOUND_IN_SEARCHED_SOURCES）与"不存在"严格区分 |
| 前序轮 | `literature_check_wallfix_novelty_v1.md`（LITCHECK_v1，2026-08-11）：边界发现 novelty + thermophone 空白首查 |

## 0. 判定一览

| # | 断言 | 判定 |
|---|---|---|
| 1 | 变弛豫 τ(T,ρ) 是热 LBM 文献的成熟标准做法 | **FOUND**（密度腿有 verbatim 本构理由；温度腿为大温差/可压缩族常规） |
| 2 | 常数 τ 本构（k∝ρ）在非 Boussinesq/大温差/有限偏置下的误差已被定量刻画 | **PARTIAL**：量级层面（Nu/流场）FOUND；**符号级/响应导数级/传递函数级 NOT_FOUND_IN_SEARCHED_SOURCES** |
| 3a | 热声引擎/制冷机/燃烧热声方向存在 LBM 应用 | FOUND（18+2 篇，全枚举 §3） |
| 3b | 该应用族对输运律密度依赖的处理（变 τ）与"传递函数/阻抗/导纳验证偏差归因输运律"的报告 | **NOT_FOUND_IN_SEARCHED_SOURCES**（摘要级全查 + 1 篇全文 grep；0 命中检索式 5 条） |
| 3c | LBM×thermophone 空白（2026-08-11 首查）复核 | **仍然成立**（1 篇且为声子 BTE，不相关；同义词族 0 命中） |

---

## 1. 断言 1：变弛豫 τ(T,ρ) 是热 LBM 成熟标准做法 —— FOUND

### 1.1 结构：变弛豫实践分两条腿

- **密度腿 τ(ρ)**（微流/稀薄族）：动机是真实气体的 μ 与密度无关（Kn ∝ 1/ρ），常数 τ 只在密度变化小时适用——**这正是"常数 τ ⇒ μ∝ρ 偏离真实气体"的本构理由，有 verbatim 出处**（下表 Nie 2002）。
- **温度腿 τ(T)**（大温差/可压缩/燃烧族）：动机写成"变物性 / temperature-dependent viscosity / μ(T) 幂律或 Sutherland"；τ = μ(T)/(ρT) 类处方中密度腿隐含其中。

### 1.2 代表作（全部字段来自检索结果原文）

| 文献 | 年 | 出处 / DOI | 被引 | 动机（是否明确到本构理由） |
|---|---|---|---|---|
| Nie, Doolen, Chen — *Lattice-Boltzmann Simulations of Fluid Flows in MEMS* | 2002 | J. Stat. Phys. / 10.1023/a:1014523007427 | 365 | **明确**。arXiv 源码（comp-gas/9806001）verbatim："lattice-BGK models, τ was chosen to be a constant"，适用前提是密度变化小；为此引入 **τ′ = 1/2 + (τ−1/2)/ρ**，动机原句 "To include the dependence of viscosity on density"；并定义 LBM 平均自由程 a(τ−0.5)/ρ |
| Zhang, Gu, Barber, Emerson — *Capturing Knudsen layer phenomena using a lattice Boltzmann model* | 2006 | Phys. Rev. E 74, 046704 / 10.1103/physreve.74.046704 | 155 | 明确（稀薄域）：有效平均自由程（壁距修正）驱动局部弛豫，超越滑移区 |
| Guo, Zheng, Shi — *LBE with multiple effective relaxation times for gaseous microscale flow* | 2008 | Phys. Rev. E 77, 036707 / 10.1103/physreve.77.036707 | 215 | 明确（稀薄域）：基于广义 NS 本构的有效弛豫时间；姊妹综述 Guo & Zheng, Int. J. Comput. Fluid Dyn. 2008 / 10.1080/10618560802253100（250 引）系统给出弛豫时间的确定 |
| Guo, Zhao — *LB simulation of natural convection with temperature-dependent viscosity in a porous cavity* | 2005 | Prog. Comput. Fluid Dyn. / 10.1504/pcfd.2005.005823 | 66 | 温度腿：变黏度 vs 常黏度直接对比（见断言 2） |
| Zhang, Cao — *A LB model for natural convection with a large temperature difference*（VPTLBGK） | 2011 | Prog. Comput. Fluid Dyn. / 10.1504/pcfd.2011.042179 | 8 | **明确到做法本身**。摘要 verbatim："replacing constant relaxation times by spatially varying ones"，以实现变输运系数 |
| Feng, Boivin, Jacob, Sagaut — *Hybrid recursive regularized thermal LB model for high subsonic compressible flows* | 2019 | J. Comput. Phys. / 10.1016/j.jcp.2019.05.031 | 137 | 温度腿（可压缩气动族）；同系燃烧应用 Tayyab, Zhao, Feng, Boivin, Combust. Flame 2019 / 10.1016/j.combustflame.2019.09.029（43 引）命中检索式 "temperature-dependent viscosity" |
| Saadat, Bösch, Karlin — *LB model for compressible flows on standard lattices: Variable Prandtl number and adiabatic exponent* | 2019 | Phys. Rev. E 99, 013306 / 10.1103/physreve.99.013306 | 71 | 可压缩族：输运自由度（Pr、γ）可调是模型设计目标本身 |
| Krüger, Kusumaatmaja, Kuzmin, Shardt 等 — *The Lattice Boltzmann Method: Principles and Practice*（教科书） | 2017 | Springer / 10.1007/978-3-319-44649-3 | 875 | 教科书锚点：τ↔ν 映射与局部 τ 调整实践的权威家（全书级内容，本轮未做全文核对） |

补充（未列入代表作但已核）：He–Chen–Doolen 1998 JCP（DDF 热 LBM 源头，10.1006/jcph.1998.6057，1398 引）与 Frapolli–Chikatamarla–Karlin 可压缩熵 LBM（PRE 2015 10.1103/physreve.92.061301，115 引；PRE 2016 10.1103/physreve.93.063302，68 引）作为框架谱系；Wang–Li–Kang–Rahman 页岩气微流综述（IJHMT 2015，10.1016/j.ijheatmasstransfer.2015.12.009，152 引）覆盖局部 Kn(ρ) 依赖 τ 的领域惯例。

### 1.3 对本项目最要害的一条：D2Q37 直系自己写出了 k∝ρ

Scagliarini, Biferale, Sbragaglia, Sugiyama 等 — *Lattice Boltzmann methods for thermal flows: Continuum limit and applications to compressible Rayleigh–Taylor systems*, Phys. Fluids 2010 / 10.1063/1.3392774（95 引；源头 Sbragaglia et al., J. Fluid Mech. 2009 / 10.1017/s002211200900665x，105 引）。其 arXiv 源码（1005.3639）连续极限推导 verbatim：

> ν = T̄ ρ (τ − Δt/2)（动力黏度）；k = c_p T̄ ρ (τ − Δt/2)（热导率）

即**常数 τ 下 μ、k ∝ ρT 在谱系源头就是白纸黑字的推导结果**——但通篇作为"正确恢复了可压缩 Fourier–Navier–Stokes 方程"的系数表出现，从未被当作与真实气体（k 与 ρ 无关）相悖的误差源刻画。同文讨论 RT/Boussinesq 对比时的假设句（"if one may neglect the dependency of viscosity and thermal diffusivity from temperature"）只豁免了温度腿，密度腿未被讨论。

**断言 1 判定：FOUND。** 变弛豫是成熟标准做法；密度腿的本构理由在微流族有 verbatim 表述（Nie 2002）；本项目使用的 D2Q37 直系在源头论文中给出了 k∝ρ 表达式但从未将其作为误差源。

---

## 2. 断言 2：常数 τ 本构误差的定量刻画 —— PARTIAL

### 2.1 量级层面：FOUND（Nu / 流场结构层）

| 文献 | 年 | 出处 / DOI | 被引 | 刻画内容 |
|---|---|---|---|---|
| Guo, Zhao | 2005 | PCFD / 10.1504/pcfd.2005.005823 | 66 | 常黏度 vs 变黏度直接对比：变黏度流体换热率更高（方向+量级，Nu 层面） |
| Zhang(X.R.), Cao | 2011 | PCFD / 10.1504/pcfd.2011.042179 | 8 | 变输运系数下 Nu–Ra 幂律改变 |
| Cao | 2016 | IJHMT / 10.1016/j.ijheatmasstransfer.2016.07.052 | 14 | 变物性 LB 通量求解器（VPLBFS，低 Ma 极限） |
| Cao, Zhang | 2017 | IJHMT / 10.1016/j.ijheatmasstransfer.2017.04.071 | 24 | 同心环隙自然对流变物性解 |
| Cao | 2017 | IJHMT / 10.1016/j.ijheatmasstransfer.2017.05.025 | 5 | 温差比（到 1.0）对变物性解的效应 |
| Zhang(Yu), Cao | 2018 | Phys. Fluids / 10.1063/1.5010864 | 16 | **常物性解 vs 变物性解逐项对比**（VPLBFS 标准/简化版分解非 Boussinesq 效应来源） |
| Feng, Guo, Tao, Sagaut | 2018 | IJHMT / 10.1016/j.ijheatmasstransfer.2018.05.051 | 55 | 大温差自然对流正则化热 LBM（非 Boussinesq bulk 建模，LITCHECK_v1 §3-G 已识别） |
| Li, Luo, He, Gao | 2012 | PRE 85, 016710 / 10.1103/physreve.85.016710 | 114 | 标准格子上含黏性耗散/压缩功的 DDF 耦合模型（大温差框架文） |
| Huang, Wu, Adams | 2019 | JCP / 10.1016/j.jcp.2019.04.044 | 19 | 可调 EOS 热流体动力学耦合 |

邻接但不同层（须在论文 related work 中区分）：

- **Wang, Xu, Serre, Sagaut**, Phys. Fluids 2021 / 10.1063/5.0073178（5 引）：**封闭腔大温差**下边界节点质量泄漏的数学定量 + 局部质量修正——摘要 verbatim 结论级措辞：质量泄漏是获得可靠解的 "critical issue"，倾斜腔中导致溢出。→ 密封系综的质量完整性已被认识到关键，但其归因是**边界格式泄漏**（数值），不是介质本构；本项目 A2a-STRICT_B 已用严格零体积面通量边界排除该通道，系综扫描将主载体定位在质量系综×本构（0.956 pp/%）。
- **Hou, Liu, Huang**, J. Fluid Mech. 2025 / 10.1017/jfm.2025.243（2 引）：可压缩性致非 Oberbeck–Boussinesq（NOB-II）效应的 RB 对流——物理研究，LBM 为工具，模型先经解析/实验验证；非本构伪迹议题。
- "compressibility error" 家族（31 篇，如 Zou–Hou–Chen–Doolen 1995 / 10.1007/bf02179966，171 引）：不可压极限的量级伪迹，不同层。
- 模型开发文对"输运律不真实"的典型态度——**承认 + 用例豁免**：Kolluru, Atif, Namburi, Ansumali, PRE 2020 / 10.1103/physreve.101.013309 全文（arXiv 1909.08406）关于体黏度的原话 "not realistic for any fluid"，但认为只关心速度动力学时无碍。

### 2.2 符号级 / 响应导数级 / 传递函数级：NOT_FOUND_IN_SEARCHED_SOURCES

- 0 命中检索式（原文见 §5 日志 #20, 21, 25, 26, 27, 31, 44, 45）：密度依赖输运伪迹、常数弛豫误差、符号错误/符号反转、热传递函数/导纳、热声阻抗/导纳/传递函数、热声 vs 线性理论（Rott/Swift）。
- 12 篇 non-Boussinesq、12 篇大温差、14 篇变物性 LBM 文的摘要中，无一出现"响应对基态导数 / 工作点趋势 / 传递函数符号"层面的误差刻画；全部停在 Nu、流场结构、稳定性层面。
- 谱系源头（§1.3）给出 k∝ρ 表达式但从未联系到有限偏置协议下的响应误差。

**断言 2 判定：PARTIAL。** "变物性 vs 常物性有多大差别"在 Nu/流场量级层面有成熟文献；"常数 τ 本构在有限偏置/密封系综下造成**符号级**响应失效"未检索到任何报告——该空白在本轮检索范围内成立（注意：摘要级为主，见 §4 局限）。

---

## 3. 断言 3：热声 / 共轭传热 LBM 应用的输运律处理现状

### 3.1 全枚举（OpenAlex `"lattice Boltzmann" AND thermoacoustic` 18 篇 + 连字符变体新增 2 篇）

**A. 模型开发文，热声波仅作测试算例**（4 篇）

| 文献 | 年 | DOI | 被引 | 输运处理 |
|---|---|---|---|---|
| Atif, Namburi, Ansumali（higher-order BCC 热流体） | 2018 | 10.1103/physreve.98.053311 | 33 | 摘要未及；同组下文全文已核 |
| Kolluru, Atif, Namburi, Ansumali（弱可压缩） | 2020 | 10.1103/physreve.101.013309 | 13 | **全文 grep（arXiv 1909.08406）：单一常数 τ（τ=ν/c_s²）、固定 Pr=1、单原子理想气体；体黏度承认不真实但豁免** |
| Kam, So, Fu（二维腔热声波一步模拟） | 2016 | 10.1016/j.compfluid.2016.10.005 | 10 | 摘要未及 |
| Wang, He, Huang, Li（IMEX FD-LBM 谐振腔气体振荡） | 2008 | 10.1002/fld.1843 | 23 | 摘要未及 |

**B. 热声引擎 / 制冷机 / 驻波装置应用**（5 项）

| 文献 | 年 | DOI | 被引 | 备注 |
|---|---|---|---|---|
| Miled, Dhahri, Mhimid（太阳能热声制冷机多孔 stack） | 2014* | 10.1177/1687814020930843 | 12 | 多孔 Darcy–Brinkman–Forchheimer + 热 LBM；摘要无输运律议题（*OpenAlex 年份 2014，DOI 串含 2020，年份存疑待刊面核对） |
| Slimene, Yahya, Dhahri, Naji（驻波热声引擎 Rayleigh 声流与传热） | 2022 | 10.1007/s10765-022-03016-x | 6 | 热 LBM；S2 无 OA 全文，τ 处理摘要级不可判定 |
| Rafat, Habibi, Mongeau（驻波管声流 DNS/LES） | 2013 | 10.1121/1.4800937；10.1121/1.4805174 | 9；4 | 简化热声制冷机内 stack 致声流 |
| LANL 进展报告（thermoacoustic engine simulations with LB CFD） | 1995 | 10.2172/206550 | 0 | 历史报告，非期刊 |
| Zhao, Xu, Zhang（平行板振荡多相传热，伪势 MRT） | 2018 | 10.1115/power2018-7544（arXiv 1803.01756） | 1 | 热声制冷机湿空气冷凝方向 |

**C. 燃烧热声不稳定**（4 篇）

| 文献 | 年 | DOI | 被引 | 备注 |
|---|---|---|---|---|
| Chen, Yang, Yang, Shan（Rijke 管，谱 MRT + 新热源项） | 2024 | 10.1017/jfm.2024.1031 | 1 | **验证口径 = LSA 转变点/增长率，报告"良好一致"；加热器为规定体积热源（火焰模型），非解析共轭有限偏置边界——不激发质量系综通道** |
| Zhao, Bhairapurada, Tayyab, Mercier 等（PRECCINSTA 燃烧器） | 2023 | 10.1016/j.compfluid.2023.105898 | 13 | ProLB 系 |
| Bhairapurada, Denet, Boivin（预混火焰热声不稳定） | 2022 | 10.1016/j.combustflame.2022.112049 | 17 | 连字符变体命中；ProLB 系（其方法学文 Tayyab 2019 用 temperature-dependent viscosity，见 §1.2） |
| Wang, Sun, He, Tao（Rijke 管热声起振） | 2015 | 10.1140/epjp/i2015-15009-5 | 12 | — |

**D. 多孔/纤维介质热声性质**（会议摘要族）：Jensen & Raspet, JASA 2009 / 10.1121/1.3248403（1 引）与 Jensen, JASA 2007 / 10.1121/1.4808541、10.1121/1.2942767（0 引）——用热 LBM 从声学响应计算纤维材料热声性质，是"响应函数"方向最近先例，但为**多孔材料均质化参数**且均系会议摘要，未检索到正式期刊全文。

**E. 声流 × 对流封闭腔**（最新邻接）：Zhang, Zheng, Xu, Phys. Fluids 2026 / 10.1063/5.0315629（0 引）——差分加热封闭腔中驻波声流与自然对流竞争，混合 LBM-FD；观测量为 Nu 调制（+400% / −41.6%），无输运律议题。

### 3.2 输运律处理与验证偏差归因：NOT_FOUND

- 摘要级全查：上述 20 项中无一在标题/摘要提及变 τ、温度/密度依赖输运律或输运保真度问题。
- 全文级抽查 1 篇（Kolluru 2020）：常数 τ、固定 Pr=1。
- "热声传递函数/阻抗/导纳的验证偏差并归因输运律"：0 命中（§5 日志 #31、#44）；唯一接近响应层面的 JFM 2024 报告的是**一致**而非偏差，且其构型（规定热源）不会暴露本构密度腿。

### 3.3 thermophone 空白复核：仍然成立

- `thermophone AND "lattice Boltzmann"`：仍 1 篇——Biswas, Lee, Roy, Cukurel, J. Appl. Phys. 2026 / 10.1063/5.0332327：声子 Peierls–Callaway BTE 闭合介观热导，**与热声发声无关**（与 LITCHECK_v1 §3-B 同一唯一命中的续代版本）。
- 同义词族 `("thermoacoustic loudspeaker" OR "thermoacoustic sound generation" OR "thermoacoustic emission") AND "lattice Boltzmann"`：0 命中。
- 连字符变体 `"lattice Boltzmann" AND "thermo-acoustic"`：4 命中，均为燃烧热声/声流对流（上表 C/E），无膜致声。

**断言 3 判定：** 应用存在（FOUND，热声机/Rijke/声流方向）；**输运律密度依赖的处理与输运归因的验证偏差报告 NOT_FOUND_IN_SEARCHED_SOURCES**；thermophone×LBM 空白行**继续成立**。

---

## 4. 定位建议

### 4.1 三种情形的措辞预案

1. **空白坐实**（无人做过符号级/本构归因）→ 可用"to our knowledge, the first"类表述，但**必须限定**检索范围（"in the sources searched (OpenAlex/CrossRef/arXiv title-abstract level plus targeted full texts)"），沿用 LITCHECK_v1 的限定纪律。
2. **有量级无符号级** → 措辞模板："Variable-property effects in thermal LBM have been quantified at the level of Nusselt number and flow structure [Guo & Zhao 2005; Cao et al. 2016–2018; Feng et al. 2018]; here we show that under a sealed finite-bias protocol the constant-τ lattice constitutive law k = α ρ c_p ∝ ρ is expressed as a **sign-level** failure of the working-point response, and we quantify the carrier (mass-ensemble slope 0.956 pp/% vs lattice-constitutive prediction 1.015 vs real-gas prediction 0.529)."
3. **有很近工作** → 直接对话、正面区分（本轮未发现需要此情形的对象）。

### 4.2 当前证据支持：情形 2（主张主体）+ 情形 1（观测量与应用侧）

- **不要声称发现了 k∝ρ 本身**：该表达式在 D2Q37 谱系源头（Scagliarini 2010）白纸黑字；微流族（Nie 2002）二十多年前就给出了密度腿修复处方 τ′=1/2+(τ−1/2)/ρ。正确的声称是三件事：
  (a) 有限偏置密封系综协议把这一**休眠**本构性质表达为**符号级**工作点失效（此前无人报告——情形 1 成立，限定语必带）;
  (b) 十轴诊断证明边界/ghost/碰撞结构不可修（与 Zhang–Chai–Shi"调自由参数可消除"传统的对照，沿用 LITCHECK_v1 §4b 定位）;
  (c) 质量轴斜率的两本构判别测量（1.015 vs 0.529，实测 0.956 pp/%）把归因钉在介质本构而非边界/数值泄漏——与 Wang 2021 PoF 的"边界质量泄漏"议题正面区分。
- **对热声/换能器应用侧**：LBM×thermophone 空白 + "thermal admittance"观测量空白（LITCHECK_v1 §3-D，0 命中，本轮 #26 复核一致）继续支持"首次"类应用表述。
- **related work 结构建议**（在 LITCHECK_v1 §4 基础上追加两段）：变弛豫标准做法段（§1.2 密度腿+温度腿，落点：修复处方是现成的，我们解释了为什么必须用它）；变物性定量对比段（§2.1，落点：此前最深到 Nu 量级，我们推进到响应导数符号）。

### 4.3 与 LITCHECK_v1 的关系

wallfix/novelty 轮的定位（"离散效应传统中首个标准补救可证明失效的实例"）保持成立；本轮把根因层从"边界离散效应"上移到"格子介质本构"，novelty 声明的核心从边界格式转移到**协议×本构**的乘积上。两份核查互为补充，均为投稿 related work 的证据底座。

### 4.4 局限（诚实条款）

- 以标题/摘要级为主；全文级仅 3 篇 arXiv 源码 grep（comp-gas/9806001、1005.3639、1909.08406）+ 1 篇 OA 元数据（Feng 2019 JCP 有 OA PDF 未做文本抽取）。"符号级失效藏在某文验证小节而不进摘要"的可能性不能排除——与 LITCHECK_v1 §5 同款局限，全文库（Scopus/WoS/Google Scholar）核查仍是待办。
- WebSearch/WebFetch 后端不可用；Scopus/ScienceDirect 未覆盖（MCP 未挂载，Elsevier 层缺席）。
- 断言 3 的 τ 处理判定：20 项中 19 项停在摘要级"未提及"（≠"未使用"）；仅 Kolluru 2020 为全文核实的常数 τ。若审稿需要，第二轮应抽 3–5 篇应用文全文核对 τ 设定。
- Miled et al. 年份（2014 vs DOI 串 2020）存疑，引用前需刊面核对。

---

## 5. 检索日志（全部可复现）

### 5.1 OpenAlex `title_and_abstract.search`（api.openalex.org/works，2026-08-20，按执行序）

| # | 检索式 | 命中 | 用途 |
|---|---|---|---|
| 1 | `"lattice Boltzmann" AND "variable relaxation time"` | 4 | 断言1（原词罕用） |
| 2 | `"lattice Boltzmann" AND "temperature-dependent viscosity"` | 28 | 断言1 温度腿族 |
| 3 | `"lattice Boltzmann" AND "relaxation time" AND "temperature dependent"` | 5 | 断言1 |
| 4 | `"lattice Boltzmann" AND Sutherland AND viscosity` | 1 | 断言1 |
| 5 | `"lattice Boltzmann" AND "local relaxation time"` | 3 | 断言1 |
| 6 | `"lattice Boltzmann" AND "effective relaxation times" AND microscale` | 1 | Guo–Zheng–Shi 2008 定位 |
| 7 | `"lattice Boltzmann" AND MEMS AND "relaxation time"` | 5 | 断言1 密度腿 |
| 8 | `"lattice Boltzmann" AND "Knudsen" AND "relaxation time" AND density` | 17 | 断言1 密度腿 |
| 9 | `"lattice Boltzmann" AND compressible AND "variable Prandtl number"` | 1 | Saadat 2019 定位 |
| 10 | `"Lattice-Boltzmann simulations of fluid flows in MEMS"` | 2 | Nie 2002 定位 |
| 11 | `"lattice Boltzmann" AND "Knudsen layer"` | 57 | 断言1 密度腿族规模 |
| 12 | `"lattice Boltzmann" AND "thermohydrodynamic"` | 47 | 框架谱系 |
| 13 | `"lattice Boltzmann" AND thermal AND "Rayleigh-Taylor"` | 16 | D2Q37 直系定位 |
| 14 | `"Analysis of lattice Boltzmann equation for microscale gas flows"` | 1 | Guo–Zheng 2008 综述 |
| 15 | `"lattice Boltzmann model for compressible flows on standard lattices"` | 1 | Saadat 摘要 |
| 16 | `"entropic lattice Boltzmann" AND compressible` | 16 | Karlin 系 |
| 17 | `"hybrid recursive regularized" AND "lattice Boltzmann" AND thermal` | 9 | Feng/Sagaut 系 |
| 18 | `"lattice Boltzmann" AND "non-Boussinesq"` | 12 | 断言2 全枚举 |
| 19 | `"lattice Boltzmann" AND "large temperature difference"` | 12 | 断言2 全枚举 |
| 20 | `"lattice Boltzmann" AND "density-dependent" AND ("thermal conductivity" OR viscosity)` | **0** | 断言2 否定证据 |
| 21 | `"lattice Boltzmann" AND "constant relaxation time" AND (error OR artifact OR spurious)` | **0** | 断言2 否定证据 |
| 22 | `"lattice Boltzmann" AND "compressibility error"` | 31 | 邻接伪迹家族 |
| 23 | `"lattice Boltzmann" AND thermal AND "variable transport coefficients"` | 1 | Zhang–Cao 2011 定位 |
| 24 | `"lattice Boltzmann" AND "variable property" AND (convection OR thermal)` | 14 | 断言2 变物性族 |
| 25 | `"lattice Boltzmann" AND ("sign error" OR "wrong sign" OR "sign reversal") AND thermal` | **0** | 断言2 否定证据（符号级） |
| 26 | `"lattice Boltzmann" AND thermal AND ("transfer function" OR admittance)` | 1（不相关） | 断言2/3；复核 LITCHECK_v1 §3-D |
| 27 | `"lattice Boltzmann" AND "heat flux" AND response AND (oscillating OR periodic) AND thermal` | 1（不相关） | 断言2 |
| 28 | `"lattice Boltzmann" AND thermoacoustic` | 18 | 断言3 全枚举（与 2026-08-11 持平） |
| 29 | `thermophone AND "lattice Boltzmann"` | 1（不相关） | 断言3c 复核 |
| 30 | `"lattice Boltzmann" AND "thermoacoustic engine"` | 6 | 断言3 |
| 31 | `"lattice Boltzmann" AND thermoacoustic AND (impedance OR admittance OR "transfer function")` | **0** | 断言3 否定证据 |
| 32 | `thermoacoustic AND fibrous AND "lattice Boltzmann"` | 2 | Jensen–Raspet 定位 |
| 33 | `"Lattice Boltzmann methods for thermal flows: Continuum limit"` | 2 | Scagliarini 2010 摘要 |
| 34 | `"The Lattice Boltzmann Method: Principles and Practice"` | 4 | 教科书锚点 |
| 35 | `"self-consistent" AND "lattice" AND "thermo-hydrodynamic equilibria"` | 1 | Sbragaglia JFM 2009 |
| 36 | `"Analysis and lattice Boltzmann simulation of thermoacoustic instability in a Rijke tube"` | 1 | Chen 2024 全摘要 |
| 37 | `"lattice Boltzmann" AND combustion AND "variable density"` | 0 | （措辞不匹配，改由 #42 定位 Tayyab） |
| 38 | `"Entropic lattice Boltzmann model for gas dynamics"` | 1 | Frapolli 2016 摘要 |
| 39 | `"lattice Boltzmann" AND ("Le Quere" OR "non-Oberbeck")` | 4 | 断言2 基准族 |
| 40 | `"Large temperature difference heat dominated flow simulations"` | 1 | Wang 2021 全摘要 |
| 41 | `"lattice Boltzmann" AND "non-Oberbeck"` | 4 | Hou 2025 全摘要 |
| 42 | `"Hybrid regularized Lattice-Boltzmann modelling of premixed and non-premixed combustion"` | 1 | Tayyab 2019 确认 |
| 43 | `"natural convection with temperature-dependent viscosity in a porous cavity"` | 1 | Guo–Zhao 2005 摘要 |
| 44 | `"lattice Boltzmann" AND thermoacoustic AND (Rott OR Swift OR "linear theory")` | **0** | 断言3 否定证据（线性热声理论对标） |
| 45 | `"constant relaxation time" AND "lattice Boltzmann"`（双向序复测） | **0** | 断言2 否定证据 |
| 46 | `"Capturing Knudsen layer phenomena using a lattice Boltzmann model"` | 1 | Zhang 2006 摘要 |
| 47 | `"lattice Boltzmann" AND "thermo-acoustic"` | 4 | 断言3 连字符变体（+2 新条目） |
| 48 | `("thermoacoustic loudspeaker" OR "thermoacoustic sound generation" OR "thermoacoustic emission") AND "lattice Boltzmann"` | **0** | 断言3c 同义词族 |
| 49 | `"Thermo-acoustic coupling in a differentially heated enclosure"` | 1 | Zhang 2026 全摘要 |

布尔语法有效性由 #39（括号+OR 返回 4 条相关结果）交叉验证；0 命中非语法假象。

### 5.2 Semantic Scholar Graph API（DOI 元数据/OA 抽查）

10.1023/a:1014523007427（Nie，无 OA PDF）；10.1016/j.jcp.2019.05.031（Feng 2019，有 OA accepted manuscript，本轮未做 PDF 文本抽取）；10.1007/s10765-022-03016-x（Slimene，无 OA）；10.1103/physreve.77.036707（Guo 2008，无 OA）。

### 5.3 arXiv API + e-print 源码 grep（全文级）

| arXiv ID | 对应文献 | grep 结果要点 |
|---|---|---|
| comp-gas/9806001 | Nie–Doolen–Chen 2002 | τ′=1/2+(τ−1/2)/ρ 处方 + "To include the dependence of viscosity on density" 动机原句 + ν=c_s²(2τ−1)/(2ρ) + 平均自由程 a(τ−0.5)/ρ |
| 1005.3639 | Scagliarini et al. 2010（D2Q37 直系） | ν=T̄ρ(τ−Δt/2)；k=c_p T̄ρ(τ−Δt/2)；理想 EOS p=ρT̄；"neglect the dependency ... from temperature" 假设句 |
| 1909.08406 | Kolluru et al. 2020 | τ=ν/c_s² 单常数；Pr 固定为 1；体黏度 "not realistic for any fluid" + 用例豁免 |

### 5.4 不可用源（记录在案）

WebSearch / WebFetch：后端模型错误不可用（与 2026-08-11 轮相同）。academic-search MCP（search_papers / Scopus / ScienceDirect 工具）：未挂载，走 No-MCP fallback。CNKI/万方：未覆盖（中文文献层缺席，与前轮一致）。
