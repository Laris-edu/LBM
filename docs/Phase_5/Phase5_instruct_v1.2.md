# Phase_5 指导文档 v1.2：热声薄膜有限温升非线性换能

> **正式名称**：Phase 5 Nonlinear Entry and Production Contract  
> **中文简称**：Phase 5 非线性入口与生产合同

| 项目 | 内容 |
|---|---|
| 版本 | `v1.2` |
| 修订日期 | 2026-07-20 |
| 建议入库路径 | `docs/Phase_5/Phase5_指导文档_v1.2.md` |
| 来源版本 | `Phase5_指导文档_v1.1.md`，2026-07-19 |
| 评审基线 | `Laris-edu/LBM`，`master`，冻结锚点 `b86459c590f406a2e0bfe452d6a73a61ede4b611` |
| 文档性质 | Phase 5 范围内的规范性入口合同、执行指导与决策记录；非投稿文本 |
| 基础投稿目标 | JASA / *Journal of Sound and Vibration* |
| 条件升级目标 | *Physical Review Applied* |
| 当前主路线 | 路线 B：参考态输运闭合下的全非线性理想气体分支 |
| 当前生产状态 | `FINAL_PRODUCTION_NOT_CLAIMED` |

## 规范性关键词

本文使用以下关键词：

- **必须**：缺失即对应 Gate 不通过，不能进入受该 Gate 约束的生产阶段。
- **应**：除非形成书面偏离记录，否则按本文执行。
- **可**：允许执行，但不构成当前主线的必要条件。
- **禁止**：不得通过局部调参、结果回调或措辞改写规避。

---

# 0. 权限、范围与已冻结决策

## 0.1 文档权限边界

本文档是 **Phase 5 范围内的唯一规范性入口与生产合同**，仅取代原创新点报告中的 Phase 5 算例矩阵、执行顺序、生产授权和声明口径。本文档不得覆盖或改写：

1. Phase 0 物理冻结；
2. M2、M3、M4 的 Closure Decision；
3. 已冻结的 10 kHz、dx2p6、特定 `(tau,k)` 校准边界；
4. M3 幅值边界与 M4 `PASSED_WITH_SCOPED_RISK` 的真实含义；
5. 用户级授权和既有停放项的重启条件。

规范性优先级冻结为：

```text
Phase 0 物理冻结
> M2/M3/M4 Closure Decision
> Phase 5 指导文档 v1.2
> Phase5_STATUS.md
> Gate 报告与路线决策备忘录
> 单个算例配置、运行摘要与后处理报告
```

本文档发生实质修改时，必须升级版本号并更新 `Phase5_STATUS.md`；禁止静默覆盖。

## 0.2 本版采用的决策

| 决策 ID | 冻结内容                                                                                                                        |
| ----- | --------------------------------------------------------------------------------------------------------------------------- |
| D0-1  | 本版按正式 `v1.2` 入库；`v1.0`、`v1.1` 保留为修订历史。本文档在 Phase 5 范围内具有规范性，但不覆盖 M2–M4 收尾决定。                                                |
| D0-2  | 基础投稿目标为 JASA / JSV；PRA 为证据触发的升级目标，不按 PRA 范围预先扩张项目。                                                                          |
| D0-3  | 默认采用路线 B；WP1 完成双物性 1D 消融后再作正式 A/B 决策。预授权默认结论为“路线 B 主线 + 1D 真实空气分支定界”。                                                       |
| D0-4  | A1 保留，但正式定义为 **有符号零均值热功率数值消融**，不作为真实 Joule 加热协议。                                                                            |
| D0-5  | **A2a + QS-1 是基础论文的首要物理锚点**；A1 用于分离周期内动力学并给出 `D_G/H2` 或非线性上界。A1 的 `D_G>3%` 不再是项目唯一成败条件。A2b 条件执行，先由 1D NSF 闭合。               |
| D0-6  | 非线性工程主阈值 `D_eng=3%`；1% 和 5% 作为敏感性口径。阈值以确定性数值不确定度控制，不采用同配置重复运行的伪统计标准差。                                                       |
| D0-7  | 允许 `SCOPED_PASS`，但只能由用户批准；脚本与报告只能产生 `SCOPED_CANDIDATE`，不得自动升级。                                                              |
| D0-8  | 基础论文的谐波目标为 **2f 的 L2 出射声学模态声明**。3f/H3 为条件升级项：只有在信号、阶次和 30 kHz 传递门同时满足时才进入 L2；否则只作 L1 诊断或不声明。L3 远场 THD 仍需逐频远场认证。             |
| D0-9  | G5 默认 `WAIVED_JASA_SCOPE`；可先执行 `G5-lite`。完整有限宽度二维仅在 PRA 升级条件满足后启动。                                                          |
| D0-10 | 执行顺序仍先做 A1 小矩阵以提供受控消融，但论文资源优先级冻结为：A2a/QS-1 → A1 的 H2 或上界 → A5 → 少量 A3 → 条件 A2b → 条件 H3/F1 → A4。                             |
| D0-11 | 在 G1a 前新增强制 `G1-W NONLINEAR_WALL_NEUTRALITY_GATE`。当前 `pressure_preserving` 整行 Grad 热壁在该 Gate 通过前只能作诊断，不得作为 DC/H2 物理归因的生产边界。 |
| D0-12 | G2 新增全局谱修正与高波数滤波的谐波消融门 `G2-O`。未通过前，2f/3f 不得解释为纯物理谐波。                                                                        |
| D0-13 | `H_s` 是 DC 热阻模型参数，而不是天然的纯数值域高。G4a 的数值收敛必须在固定目标 `Theta_DC` 下重匹配 `P_mean`，或保持等效热阻不变；固定 `P_mean` 改变 `H_s` 只能称为物理热沉敏感性。         |
| D0-14 | 更换生产热壁、谱修正、滤波或其相对执行顺序，均视为物理仪器变化，必须按 §23 触发 G1-W/G1/G2/G4a 的定向复验。                                                            |

## 0.3 当前状态标签

```text
PHASE5_NONLINEAR_ENTRY_CONTRACT_v1.2
PHASE5_SCOPE_FROZEN
ROUTE_B_DEFAULT_PENDING_WP1_EVIDENCE
MODEL_CLOSURE_PENDING
NONLINEAR_WALL_NEUTRALITY_NOT_CERTIFIED
AMPLITUDE_ENVELOPE_NOT_CERTIFIED
HARMONIC_TRANSFER_NOT_CERTIFIED
HARMONIC_OPERATOR_ABLATION_NOT_CERTIFIED
H2_BASE_TARGET_H3_CONDITIONAL
NONLINEAR_1D_REFERENCE_NOT_CERTIFIED
DC_PROTOCOL_NOT_CERTIFIED
FINITE_WIDTH_2D_DEFERRED_JASA_SCOPE
FINAL_PRODUCTION_NOT_CLAIMED
```

## 0.4 非谈判纪律

1. 不得为通过非线性 Gate 而按幅值逐点更换 dx、tau、热流导出因子、色散因子、Grad 壁参数或远场增益。
2. `q_feedback_relax`、拟合窗、去趋势阶数和滤波设置必须按算例族预注册；不得按结果逐点选择。
3. 禁止 clipping、floor、positivity repair、结果回调和针对答案的后处理调参。
4. 路线 A 一旦修改局部输运闭合，路线 B 下的 G0–G3 认证不得自动继承。
5. 未通过对应 Gate 的结果可以作为诊断，不得作为主论文的定量物理结论。
6. 在 G1-W 通过前，禁止把 `pressure_preserving` 热壁下的 DC 偏移、H2 或全域质量变化归因为气体有限温升非线性。
7. 谱修正和高波数滤波必须在算例族内冻结；其消融只能用于仪器识别，不得按结果挑选“更好看”的生产算子组合。
8. A1 的 `D_G` 未跨越 3% 不构成自动 `NO_GO`；只要 A2a/QS-1 或经认证的 H2 提供超出 `U_gov` 的可归因物理信息，项目仍可进入 scoped 或完整生产。

---

# 1. 科学范围与核心问题

## 1.1 研究对象定位

10 kHz 基线远场压力约 0.60 Pa，对应声学马赫数约 `4×10^-6`。因此本文研究对象不是传统的高声压非线性传播，而是：

> **有限温升条件下的热—流体换能非线性与平均工作点非线性**  
> *finite-temperature nonlinear thermoacoustic transduction*

主要非线性来源可能包括：

- 理想气体状态与质量、动量、能量方程的非线性；
- 压力功与对流；
- 膜—气体热反馈；
- 非均匀 DC 基态对增量传递函数的影响；
- 显式真实空气温变输运律，若路线 A 被触发；
- LBM 闭合、热壁质量约束、全局谱修正/高波数滤波与有限波数误差的幅值依赖，作为必须被排除或定界的数值因素。

## 1.2 核心无量纲状态变量

### 周期温升强度

$$
\varepsilon_{\rm AC}=\frac{|\hat T_s|}{\bar T_s}
$$

### 平均工作点偏移

$$
\Theta_{\rm DC}=\frac{\bar T_s-T_0}{T_0}
$$

### 设计输入的膜—气竞争参数

$$
\chi_0=\frac{\Omega C_A}{2|Y_g(T_0)|}
$$

### 工作点有效竞争参数

$$
\chi_{\rm eff}=\frac{\Omega C_A}{2|Y_g^{\rm inc}[U_0]|}
$$

其中 `Y_g^inc[U_0]` 是围绕均匀背景或非均匀 DC 基态 `U_0(y)` 的增量气侧热导纳。均匀背景下可近似写为 `Y_g(T_bar)`；非均匀基态下必须由基态线性化或小扰动测量得到，禁止直接套用 300 K 公式。

所有生产算例必须同时归档 `chi_0` 和 `chi_eff`。功率密度仅作为达到目标状态的控制输入，不作为跨材料、跨频率比较的唯一横轴。

## 1.3 基线数值

在 10 kHz、300 K 空气下：

- `|Y_g| ≈ 1.40×10^3 W/(m² K)`；
- `2|Y_g| ≈ 2.80×10^3 W/(m² K)`；
- 基线 `C_A=7×10^-4 J/(m² K)` 时，`chi_0≈0.016`；
- `chi_0=1` 的交叉面热容约为 `4.45×10^-2 J/(m² K)`；
- M3 canonical：`|T_hat_s|=0.37269 K @ P1=1000 W/m²`。

## 1.4 核心问题句

> 基频增量换能增益、源区谐波以及在相应传递门通过后可识别的出射声学模态谐波，如何随 `epsilon_AC`、`Theta_DC`、`chi_0/chi_eff` 变化？将线性理论在偏移工作点或完整 DC 基态上重新求值，能否预测这些偏离；若不能，剩余动力学非线性的来源、标度和可检测边界是什么？

## 1.5 对外创新声明

> 据本文覆盖的检索范围所知，本文首次对自由悬浮平面 thermophone 在规定周期热功率驱动下的气侧有限温升非线性进行谐波分辨的时域模拟，定量分离平均工作点偏移与周期内动态非线性，并给出其随膜—气热容竞争参数变化的标度及工作点修正规则的适用边界。

禁止使用：

- “从未有人做过”；
- “1917 年至今全部线性”；
- “实验永远无法分离”；
- “所有大信号算例完全在既有认证包络内”；
- “方法文是确定保底”。

## 1.6 明确排除项

基础 JASA/JSV 范围不要求：

- 非线性声波传播或激波；
- 完整 3D 阵列；
- 全频景观图；
- 未经逐频认证的远场 2f/3f THD；
- 把 3f/H3 作为基础论文的强制交付；
- 未经 Gate 的真实空气温变物性归因；
- 完整有限宽度孤立膜侧向开边界。

---

# 2. 物理模型路线与 A/B 决策

## 2.1 路线定义

| 路线 | 数学与代码定义 | 允许的论文表述 |
|---|---|---|
| 路线 A | 实现并验证局部 `mu(T)`、`k(T)`，必要时加入 `cp(T)`；建立局部或分区 `tau(T)`、闭合、热流导出和壁面重认证 | 真实空气有限温升非线性 |
| 路线 B | 保持参考态全局标量 tau 和现有校准闭合；质量、动量、总能量、EOS、压力功、对流及膜—气反馈保持全非线性 | 参考态输运闭合下的全非线性理想气体 |

## 2.2 路线 B 的准确科学地位

路线 B **不是纯 EOS-only 模型**。它保留：

- 非线性连续方程；
- 非线性动量与对流；
- 压力功；
- 密度和温度对宏观状态恢复的影响；
- 膜—气体反馈；
- 固定 tau 闭合自身可能具有的有效状态依赖；
- 壁面和有限波数链的幅值依赖。

路线 B 的作用是隔离：

> **显式真实空气温变输运律相对于参考态输运闭合的增量贡献。**

关于 `rho cp T` 的相消只允许写成：

> 在近似等压、定比热和前导阶假设下，`rho cp T` 对平均温度存在相消结构；该结构在有限热层、非均匀基态与完整耦合条件下是否仍主导响应，必须由 1D 消融和 LBM 对照检验。

禁止在结果出现前预设：

- `alpha_eff ∝ T`；
- 路线 B 捕捉了真实空气“一半指数”；
- EOS 必然是主导机制；
- 准静态修正规则必然成立。

## 2.3 独立 1D 模型的双分支

WP1 必须实现两个相互独立的 1D NSF 分支：

| 分支 | 用途 | 约束 |
|---|---|---|
| `1D-lbm-equivalent` | 使用 G0 实测的 LBM 有效输运律，隔离空间离散、壁面和闭合差异 | 不复制 Grad 壁点标定、LBM 热流导出因子或谐波修正 |
| `1D-physical` | 使用明确来源的真实空气物性律，作为物理定界参考 | 与 LBM 代码独立；物性模型 ID 必须归档 |

两个分支必须使用相同的热功率协议、相同的 DC 热沉模型、相同的谐波拟合定义与相同的 QoI。

## 2.4 WP1 后的路线决策指标

对每个主 QoI `Q ∈ {D_G, phase shift, H2, H3, QS error}`，定义显式物性增量：

$$
\Delta_{\rm prop}Q=Q_{\rm 1D-physical}-Q_{\rm 1D-lbm-equivalent}
$$

定义参考闭合分支的总非线性效应：

$$
\Delta_{\rm ref}Q=Q_{\rm 1D-lbm-equivalent}-Q_{\rm linear}
$$

### 默认决策 D-AB-2

若在主设计窗内满足：

$$
|\Delta_{\rm prop}Q|<\max\left(2U_{\rm gov}(Q),\ 0.3|\Delta_{\rm ref}Q|\right)
$$

则采用：

```text
ROUTE_B_MAIN
+ 1D_REAL_AIR_BOUNDING
```

即路线 B 作为 LBM 主线，真实空气物性影响由 1D 分支定界。

### 路线 A 触发条件

若任一主要 QoI 在连续两个以上状态点显著超过上述阈值，并且改变主结论的符号、阈值区间或工程判断，则形成：

```text
ROUTE_A_COST_REVIEW_REQUIRED
```

路线 A 不自动启动，必须由用户根据代价评估单独批准。

## 2.5 路线 A 的重新认证状态机

```text
路线 B 的 G0-B/G1-B/G2-B/G3-B
        ↓
路线 A 被批准
        ↓
实现局部输运与 metadata
        ↓
G0-A 重新闭合
        ↓
G1a-A / G1b-A 重新认证
        ↓
G2-T-A / G2-A-A 重新认证
        ↓
G3-A 重新认证
        ↓
才可进入路线 A 的 WP3/WP4
```

路线 B 的 Gate 结果不得直接复制为路线 A 的 Gate 结果。

## 2.6 路线 A 止损

路线 A 自正式启动起，若连续 6 周仍不能在不回调结果的条件下闭合 G0-A、G1a-A 和 G2-T-A，则默认执行：

```text
ROUTE_A_STOPPED_BY_SCOPE
ROUTE_B_MAIN
1D_REAL_AIR_BOUNDING_RETAINED
```

---

# 3. 驱动协议与基态定义

## 3.1 G0 均匀背景协议

G0 的背景温度扫描用于测定模型有效物性，不属于 A2a。主路径为等压均匀背景：

$$
\rho_b T_b=\rho_0T_0
$$

等密度背景只作为诊断，不作为 thermophone 工作点的主要物理解释。

## 3.2 A1：有符号零均值热功率数值消融

$$
P(t)=P_1\cos\Omega t
$$

半周期内 `P(t)<0`，对应主动抽热，因此 A1 是理想化数值消融，不是普通 Joule 加热协议。

A1 的唯一主目的：

- 去除 DC 工作点漂移；
- 测量周期内动态非线性；
- 建立 `D_G`、`H2`、`H3` 与 `epsilon_AC` 的弱非线性标度。

对外统一表述：

> signed zero-mean caloric forcing used as a controlled numerical ablation.

## 3.3 A2a：非均匀稳态 DC 基态上的增量响应

A2a 不使用“整个气体均匀升温”的假设。均匀升温属于 G0；A2a 必须先求得具有平均热流的非均匀稳态基态：

$$
U_0(y)=\{\rho_0(y),u_0(y),T_0(y),p_0(y)\}
$$

### Canonical DC 热沉

主热沉模型冻结为：

```text
有限距离 y=H_s 的等温热库：T(H_s)=T_ambient
```

`H_s` 必须进入 metadata，但其角色须严格区分：

1. **物理热沉参数**：在固定 `P_mean` 下改变 `H_s` 会改变导热热阻和 `Theta_DC`，属于真实模型参数扫描，不是纯数值收敛。
2. **状态匹配的数值域高检查**：比较不同 `H_s` 时，必须重新匹配 `P_mean`，使目标 `Theta_DC` 在 1% 内一致，再比较增量增益、QS-0/QS-1 和近壁基态。
3. **等效热阻保持检查**：若采用 Robin 热沉，可移动外边界，但必须同步调整 Robin 参数以保持总等效热阻不变。

因此，G4a 禁止把“固定 `P_mean`、改变 `H_s` 后结果变化”直接判成域高不收敛。该变化应单独报告为热沉物理敏感性。若后续有实验封装热阻，可增加等效热阻分支，但不得静默替换 canonical 分支。

在 DC 基态上叠加：

$$
P(t)=\bar P+P_1\cos\Omega t,\qquad \bar P\ge P_1
$$

基础 A2a 点应保持总热功率非负，以形成物理可实现的增量协议。

## 3.4 A2b：真实自热建立瞬态

A2b 研究从初始状态到 DC 工作点建立的过程，包含：

- `T_bar_s(t)`；
- 动态基频增益 `G1(t)`；
- 热沉时间常数；
- 周期响应相对慢变基态的滞后；
- QS-0/QS-1 的瞬态预测能力。

A2b 必须先由 1D NSF 闭合。LBM A2b 是条件任务；若 G4b-LBM 失败，基础论文可保留 A1、A2a、A5，并将 A2b 限定为 1D 结果或补充材料。

## 3.5 A5：`chi_0 × epsilon_AC` 地图

A5 按 `chi_0` 设计、按 `chi_eff` 解释。每个 `C_A` 点必须标记：

```text
material_relevance = supported | synthetic_regime_extension
```

没有材料数据支持时，不得把大 `C_A` 点写成实际 CNT 膜设计点；可写为无量纲工作区扩展。

---

# 4. Gate 管理规则

## 4.1 每个 Gate 的强制字段

每个 Gate 报告必须包含：

1. **Fixture**：配置、初始条件、边界、模型路线、代码提交；
2. **Metrics**：实际测量量；
3. **Thresholds**：数值通过标准；
4. **Required outputs**：JSON/HDF5/图表和摘要字段；
5. **Failure labels**：失败后的状态标签；
6. **Decision authority**：自动 Gate 与用户授权边界；
7. **Retest triggers**：哪些代码、配置或物理变化会强制复验。

## 4.2 Gate 状态

```text
NOT_RUN
RUNNING
PASSED
FAILED
SCOPED_CANDIDATE
SCOPED_PASSED_BY_USER
WAIVED_BY_SCOPE
```

脚本只能输出 `PASSED`、`FAILED` 或 `SCOPED_CANDIDATE`。`SCOPED_PASSED_BY_USER` 必须有单独决策记录。

## 4.3 Scoped Pass 的批准条件

只有同时满足以下条件才允许 scoped continuation：

1. 失败项不污染保留的主结论；
2. 可用明确频率、幅值、模型、几何或声明层级缩域；
3. 失败机制已定位，或至少有可重复的诊断边界；
4. 状态标签明确写出未认证内容；
5. 报告不得把 scoped pass 写成 clear pass；
6. 用户批准并记录理由。

---

# 5. G0：物理模型闭合门

## 5.1 G0-B Fixture

| 项 | 冻结要求 |
|---|---|
| Mapping | 所有背景温度使用同一 `UnitMapping`、同一 `tau21/tau32`、同一闭合与同一 dx/dt |
| 禁止项 | 禁止按每个背景温度重新调用 mapping 并重算 tau |
| 主热力学路径 | 等压均匀背景 |
| 诊断路径 | 等密度均匀背景 |
| 温度点 | `270, 300, 330, 360 K`；必要时增加 `375 K` 安全点 |
| 低波数层 | 至少两个低模态或两档波数，用于测构成律极限 |
| 生产波数层 | `k1≈0.098`、`k2≈0.139`、`k3≈0.170` 附近，用于测仪器响应 |
| 方向 | 主结果为壁面法向轴；x/对角作为各向异性诊断 |

## 5.2 G0-B 测量量

必须测量：

- `nu_eff(T_b,k)`；
- `alpha_eff(T_b,k)`；
- `mu_eff=rho_b nu_eff`；
- `k_eff=rho_b cp alpha_eff`；
- `c_eff(T_b,k)`；
- `gamma_eff(T_b,k)`；
- 低波数与生产波数之间的差异；
- 等压与等密度路径差异。

禁止在测量前强行拟合某个温度指数。若单一幂律不能在门限内描述，必须保存表格或分段插值，不得为叙事强行压缩。

## 5.3 G0-B 阈值

| 指标 | 通过标准 |
|---|---|
| 300 K 回归 | 轴向 `nu/alpha` 与既有验证目标偏差不超过 5%；`c/gamma` 不超过 2% |
| 重复测量一致性 | 不同拟合窗或等价测量法所得有效系数差异不超过 2% |
| 低波数收敛 | 最细两档低波数的外推差异不超过 2%，否则仅按有限波数有效系数报告 |
| 路径声明 | 等压与等密度结果均被归档，不得混写 |
| 一致性 | 代码、配置、公式、metadata、模型冻结表五方一致 |
| 数值纪律 | 无 clipping/floor/repair；所有测试可复现 |

## 5.4 G0 交付物

```text
docs/Phase_5/nonlinear_model_freeze.md
results/phase5/g0_effective_properties/<run_id>/summary.json
results/phase5/g0_effective_properties/<run_id>/property_table.csv
verification/nonlinear/test_phase5_g0_effective_properties.py
```

## 5.5 G0 失败标签

```text
MODEL_CLOSURE_FAILED
EFFECTIVE_PROPERTY_LAW_NOT_IDENTIFIED
BACKGROUND_PATH_DEPENDENCE_UNRESOLVED
```

G0 未通过时，禁止对非线性机制作物性归因；只允许做数值方法诊断或上界分析。

---

# 6. G1：壁面中性与非线性幅值包络门

G1 依次拆分为：

```text
G1-W：热壁非线性中性与质量约束
→ G1a：规定壁温气侧幅值包络
→ G1b：Level C 耦合幅值包络
```

G1-W 是 G1a/G1b 的前置硬门，不得跳过。

## 6.1 G1-W：非线性热壁中性门

### 风险依据

当前 `pressure_preserving` 整行 Grad 热壁规定：

$$
\rho_w=\frac{p_{\rm ref}}{\theta_w}.
$$

若：

$$
\theta_w=\theta_0(1+\varepsilon\cos\Omega t),
$$

则：

$$
\frac{\rho_w}{\rho_0}
=1-\varepsilon\cos\Omega t
+\frac{\varepsilon^2}{2}[1+\cos(2\Omega t)]
+O(\varepsilon^3).
$$

因此该边界在运动方程求解前已内生一个 `O(epsilon^2)` 的 DC 密度项和 2f 密度项。该现象不自动证明最终声场是伪影，但足以使当前边界在 G1-W 通过前失去 DC/H2 生产资格。

### Fixture

- 10 kHz、冻结 dx2p6 mapping；
- `epsilon_AC = 0.001, 0.01, 0.03, 0.05`；0.10 为条件点；
- 至少比较：
  1. 现有 `pressure_preserving` 整行 Grad 热壁，作为诊断对照；
  2. 一个生产候选的 **零法向质量通量、不可穿透、无滑移、温度可控** 热壁；优先采用受约束 incoming-population 重构或等价质量守恒 Grad/RR 重构；
  3. `constant_density` 可作辅助诊断，但单独通过不得替代质量守恒生产壁；
- 生产候选壁必须保留物理非平衡热流，而不是退化为 equilibrium clamp；
- 增加“边界—线性内部”制造夹具：内部方程/参考态按线性单频载波运行，用于检测边界算子自身产生的非目标 0f/2f/3f 声学或质量源；
- 对生产候选壁重跑小幅值 Level A 动态导纳；Level C 回归在 G1b 完成。

### Metrics 与阈值

| 指标 | 通过标准 |
|---|---|
| 法向质量通量 | 生产壁的归一化净质量通量 0f–3f 分量均 `≤1e-10`；定义和归一化必须进入报告 |
| 全域质量 | 拟合窗内 `|Delta M|/M0 ≤1e-8`，完整运行累计`≤1e-6` |
| 不可穿透/无滑移 | 壁面平均及 1f–3f 法向速度 `≤1e-8 c0`；切向平均速度同阶 |
| 壁温实现 | 最大壁温误差 `≤0.01 K` |
| 小幅值导纳回归 | 幅值误差 `≤5%`，相位误差 `≤5°` |
| 边界—线性内部夹具 | 非目标 2f/3f 出射声学分量相对 1f `≤1e-8` |
| 旧壁差异审计 | 必须给出 `D_G/H2/H3/DC` 的新旧壁差异；若差异超过 `max[U_gov(Q), 0.1|Q|]`，旧壁明确标记为`DIAGNOSTIC_ONLY` |
| 数值纪律 | 无 clipping/floor/repair；约束求解残差可审计 |

G1-W 的通过不要求新旧壁结果相同；它要求存在一个满足质量中性的生产壁，并把旧壁可能造成的二阶源项定量隔离。

### G1-W 决策

```text
PASSED
  → 生产算例统一使用已认证质量中性热壁

SCOPED_CANDIDATE
  → 仅允许基频小幅值或 1D 主线；不得声明 LBM DC/H2

FAILED
  → A1/A2a 的 LBM 非线性生产暂停
```

## 6.2 G1a：规定壁温气侧幅值包络

### Fixture

- 10 kHz；
- 路线 B 的冻结 dx2p6 mapping；
- 使用 G1-W 批准的生产热壁；
- 规定 `epsilon_AC = 0.001, 0.01, 0.03, 0.05`；0.075/0.10 为条件点；
- 规定壁温协议 `T_s(t)=T_0+T_1 cos(Omega t)`，其扰动均值为零；
- 基准网格 + 一档诊断细化；
- 诊断细化不得用于重新调校基准答案；
- 谱修正和高波数滤波采用冻结生产设置，消融在 G2-O 执行。

### Metrics 与阈值

| 指标 | 通过标准 |
|---|---|
| 小幅值回归 | `epsilon=0.001` 时，基频幅值误差 `≤5%`，相位误差 `≤5°` |
| 壁温实现 | 最大壁温误差 `≤0.01 K` |
| 能量审计 | 归一化能量残差 `≤1%` |
| 质量漂移 | 拟合窗 `≤1e-8`，完整运行 `≤1e-6`；不得再以“边界允许质量交换”规避 |
| 有限性 | f/g、rho、T、p 全部有限且状态合法 |
| 数值修复 | 必须为 false |
| 窗口敏感性 | 基频幅值变化 `≤2%`，相位变化 `≤2°` |
| 诊断细化 | `D_G` 差异 `≤max(1%, U_gov)`；H2 差异进入其 `U_gov` |
| 最低幅值窗 | 至少 `epsilon=0.05` 通过，方可进入主非线性生产 |

`epsilon=0.10` 可失败而形成 `G1A_PASSED_TO_0P05`；若 `epsilon=0.05` 未通过，则不授权完整生产矩阵。

## 6.3 G1b：Level C 耦合幅值包络

### Fixture

- 继承 M3 canonical 10 kHz、dx2p6；
- 使用与 G1a 相同的 G1-W 生产热壁；
- 由于生产热壁发生变化，必须重新执行小幅值 M3 Level C 回归，旧 M3 digest 仅作上游参考；
- `q_feedback_relax` 在算例族内固定，不得按幅值逐点调节；
- 耦合方案、Grad 外推、拟合协议固定；
- 通过自适应 `P1` 达到目标 `epsilon_AC`，实际值必须归档。

### Metrics 与阈值

| 指标 | 通过标准 |
|---|---|
| M3 小幅值回归 | `T_hat_s` 幅值在既有 M3 ±5.4% scoped 边界内，相位误差 `≤5°` |
| 目标状态 | 实测 `epsilon_AC` 与目标差异 `≤10%` |
| 壁温误差 | `≤0.01 K` |
| 膜能量审计 | `≤1%` |
| 全域质量 | 拟合窗 `≤1e-8`，完整运行 `≤1e-6` |
| 耦合稳定性 | 无发散、无 Nyquist 自激、无不可解释的预测—校正增长 |
| 参数冻结 | 不改变 dx/tau/导出因子/滤波/生产壁参数 |
| 数值修复 | 必须为 false |
| 最低幅值窗 | 至少 `epsilon=0.05` 通过 |

## 6.4 G1 输出

```text
docs/Phase_5/wall_nonlinearity_neutrality_report.md
docs/Phase_5/nonlinear_entry_gate_report.md
results/phase5/g1w_wall_neutrality/<run_id>/
results/phase5/g1a_wall_amplitude/<run_id>/
results/phase5/g1b_levelc_amplitude/<run_id>/
verification/nonlinear/test_phase5_g1w_wall_neutrality.py
verification/nonlinear/test_phase5_g1_amplitude_envelope.py
```

## 6.5 G1 失败标签

```text
NONLINEAR_WALL_NEUTRALITY_FAILED
PRESSURE_PRESERVING_WALL_DIAGNOSTIC_ONLY
MASS_NEUTRAL_WALL_NOT_AVAILABLE
AMPLITUDE_ENVELOPE_FAILED_BELOW_0P03
G1A_ONLY_PASSED
LEVELC_NONLINEAR_COUPLING_NOT_CERTIFIED
HERMITE_TEMPERATURE_WINDOW_SCOPED
```

---

# 7. G2：谐波传递与数值算子消融门

G2 拆分为热生成链、纯声学传播/读出链和数值算子消融链：

```text
G2-T：热生成
G2-A：声学传播/读出
G2-O：谱修正与高波数滤波消融
```

10/20 kHz 为基础强制频率；30 kHz 仅在 H3 条件触发后成为强制频率。

## 7.1 G2-T：壁温到出射声学模态的热生成链

### Fixture

- 10、20 kHz 强制；30 kHz 条件执行；
- 小幅值规定壁温；
- 使用 G1-W 生产壁；
- 路线 B 与 `1D-lbm-equivalent` 对照；
- 不使用结果依赖的频率逐点回调；
- 输出近场 `p,T,u` 和出射特征量。

### Metrics 与阈值

| 指标 | 通过标准 |
|---|---|
| 传递幅值 | LBM 与 1D 对应传递函数差异 `≤10%` |
| 传递相位 | 差异 `≤10°` |
| 窗口敏感性 | 幅值 `≤3%`，相位 `≤3°` |
| 网格诊断 | 方向一致，且差异进入 `U_gov` |
| 拟合泄漏 | 合成信号夹具中非目标谐波相对泄漏 `≤1e-8` |
| 数值修复 | 必须为 false |

若 20 kHz 仅能给出稳定但偏差大于门限的传递函数，可形成 `SCOPED_CANDIDATE`，此时 H2 只能停留在 L1。30 kHz 失败不阻塞基础论文，但 H3 不得作 L2 定量声明。

## 7.2 G2-A：纯声学传播与读出链

### Fixture

- 10、20 kHz 强制，30 kHz 条件；
- 小幅值平面波、特征波或 compact-source 夹具；
- 不经过膜热反馈；
- 采用 `(p,u_n)` 出射/入射分解；
- 验证边界、控制面和读出。

### Metrics 与阈值

| 指标 | 通过标准 |
|---|---|
| 幅值误差 | `≤5%` |
| 相位误差 | `≤5°` |
| 反射系数 | `|R|<0.05` |
| 控制面位置敏感性 | `≤5%` |
| 通道一致性 | 压力梯度/速度通道差异 `≤10% / 10°` |

## 7.3 G2-O：谱修正与高波数滤波谐波消融

### 目的

当前求解链在壁面 callback 之后继续施加全局声学谱修正和高波数滤波。即使这些算子在形式上主要用于线性色散/稳定性控制，也必须证明它们不会生成、选择性放大或压低目标 H2/H3。

### Fixture

1. **算子单音夹具**：线性化单频载波通过完整算子栈，检查是否出现非目标 2f/3f。
2. **归一化非线性消融**：在稳定范围内比较：
   - 冻结生产算子栈；
   - 关闭声学谱修正的诊断变体；
   - 关闭或降低高波数滤波强度的诊断变体；
   - 必要时增加算子执行顺序诊断，但不得把诊断顺序回写为生产顺序。
3. 每个诊断变体必须用其自身的小幅值 1f 基线归一化，避免把线性色散变化误判成非线性变化。
4. 所有消融只用于仪器识别；生产结果始终使用预注册冻结栈。

### Metrics 与阈值

| 指标 | 通过标准 |
|---|---|
| 算子单音泄漏 | 2f/3f 相对 1f `≤1e-8` |
| `D_G` 算子敏感性 | `|Delta D_G| ≤ max[1 percentage point, U_gov(D_G)]` |
| H2 算子敏感性 | `|Delta H2| ≤ max[0.1 H2_ref, U_gov(H2)]`，且弱非线性标度方向不变 |
| H3 算子敏感性 | 仅在声明 H3 时要求；阈值同 H2，并保持 `m3` 阶次判读 |
| 稳定性 | 至少一个非生产消融序列可稳定完成；若所有关闭/减弱变体均失稳，只能形成 `SCOPED_CANDIDATE` |
| 可归因性 | 主结论的符号、阈值区间与 QS 判定不得由某一算子开关单独决定 |

## 7.4 H3 条件触发

30 kHz G2-T/G2-A/G2-O 只有在下列任一条件满足时成为强制项：

1. P-AC2/P-AC3 中 H3 高于空检底 3 倍且高于 `2U_gov(H3)`；
2. 至少三个幅值点给出 `2.5≤m3≤3.5` 的可重复弱非线性标度；
3. 论文主结论主动包含 H3。

否则统一标记：

```text
H3_DIAGNOSTIC_ONLY
G2_3F_WAIVED_BY_SIGNAL
```

## 7.5 谐波声明层级

| 层级 | 允许声明 | 必要条件 |
|---|---|---|
| L1 | `source-region harmonic content` | G1-W、多谐波拟合、空检、窗口、网格通过 |
| L2-2f | `outgoing acoustic-mode second harmonic` | 20 kHz 的 G2-T/G2-A/G2-O 全部通过 |
| L2-3f | `outgoing acoustic-mode third harmonic` | H3 条件触发且 30 kHz 的 G2-T/G2-A/G2-O 全部通过 |
| L3 | 远场谐波 SPL / radiated THD | 对应 20/30 kHz 远场链逐频认证 |

基础 JASA/JSV 版本目标为 L2-2f。L2-3f 和 L3 均不是当前必要项。

## 7.6 G2 交付物与标签

```text
docs/Phase_5/harmonic_transfer_report.md
docs/Phase_5/harmonic_operator_ablation_report.md
results/phase5/g2_thermal_transfer/<run_id>/
results/phase5/g2_acoustic_transfer/<run_id>/
results/phase5/g2_operator_ablation/<run_id>/
verification/nonlinear/test_phase5_g2_harmonic_transfer.py
verification/nonlinear/test_phase5_g2_operator_ablation.py
```

失败/缩域标签：

```text
G2_1F_PASSED
G2_2F_NOT_CERTIFIED
G2_3F_NOT_CERTIFIED
G2_3F_WAIVED_BY_SIGNAL
HARMONIC_OPERATOR_ABLATION_FAILED
HARMONIC_CLAIM_LEVEL_L1_ONLY
HARMONIC_CLAIM_LEVEL_L2_2F
HARMONIC_CLAIM_LEVEL_L2_3F
```

---

# 8. G3：独立非线性 1D NSF 门

## 8.1 求解器要求

新增：

```text
reference/nonlinear_nsf_1d.py
```

必须具备：

- 质量、动量、总能量的真正时间推进；
- `1D-lbm-equivalent` 与 `1D-physical` 两套物性；
- 与 LBM 相同的 A1/A2a/A2b 热功率协议；
- canonical DC 热沉；
- 低马赫、低耗散、基态平衡保持；
- 独立于 LBM Grad 壁与导出标定；1D 固壁采用不可穿透、零法向质量通量条件，并作为 G1-W 的独立物理参照；
- 与 `multiharmonic_fit.py` 共用复幅值约定。

通用高耗散激波捕捉格式不得直接作为主参考，除非证明其数值耗散低于 2f/3f 可测量底。

## 8.2 1D Gate 阈值

| 指标 | 通过标准 |
|---|---|
| 无驱动平衡保持 | 10 个基频周期内 `max|p-p0|/p0 <1e-10`，或给出等价严格残差界 |
| 线性极限幅值 | 与 Phase 1 频域解差异 ≤2% |
| 线性极限相位 | 差异 ≤2° |
| 网格收敛 | 观察阶次 ≥1.5，最细两档主 QoI 差异 ≤1% |
| 总能量残差 | ≤0.5% |
| 线性化泄漏夹具 | 非目标谐波 ≤1e-8 |
| 低马赫可分辨性 | 基线声学扰动不被数值耗散淹没，残差谱可审计 |

## 8.3 G3 交付物

```text
docs/Phase_5/nonlinear_1d_reference_report.md
reference/nonlinear_nsf_1d.py
verification/nonlinear/test_phase5_g3_nsf1d.py
results/phase5/g3_nsf1d/<run_id>/
```

失败标签：

```text
NONLINEAR_1D_REFERENCE_FAILED
LOW_MACH_RESOLUTION_INSUFFICIENT
CROSS_VALIDATION_NOT_AVAILABLE
```

G3 未通过时，不进入完整非线性物理矩阵。

---

# 9. G4：DC 基态与自热协议门

## 9.1 G4a：稳态 DC 基态 + 小扰动

### Fixture

- 使用 G1-W 批准的生产热壁；
- canonical 等温热库 `T(H_s)=T_ambient`；
- 选定一个明确的 canonical `H_s`，作为基础论文的物理热沉参数；
- 状态匹配的数值检查至少使用三档 `H_s`：`H_s, 1.5H_s, 2H_s` 或等价序列，但每一档必须重新匹配 `P_mean`，使目标 `Theta_DC` 在 1% 内一致；
- 另行保留“固定 `P_mean` 改变 `H_s`”的热沉物理敏感性分支，不把它混入收敛 Gate；
- 若采用 Robin 热沉替代检查，移动边界时必须保持总等效热阻不变；
- 求得非均匀稳态 `U0(y)`；
- 在基态上施加 `epsilon_AC=0.005, 0.02` 的增量扰动；
- 计算 `chi_eff`、`D_OP`、QS-0、QS-1。

### 阈值

| 指标 | 通过标准 |
|---|---|
| 基态稳态性 | 一个基频周期内基态 QoI 漂移 `<0.1%` |
| DC 能量闭合 | `≤0.5%` |
| 状态匹配 | 不同 `H_s` 的 `Theta_DC` 偏差 `≤1%`；对应 `P_mean` 必须归档 |
| 状态匹配域高敏感性 | 增量增益幅值 `≤2%`，相位 `≤2°` |
| 热沉物理敏感性 | 固定 `P_mean` 扫描只作物理结果，不作为 Gate 失败；必须与状态匹配结果分图、分表 |
| 网格敏感性 | 进入 `U_gov`，主结论不改变符号 |
| 窗口敏感性 | 幅值 `≤1%`，相位 `≤1°` |
| 初始条件 | 不同合理初态收敛到同一基态分支 |
| `chi_eff` | 由增量导纳测得，不用 300 K 公式替代 |
| QS-1 独立性 | QS-1 必须围绕完整 `U0(y)` 构建，不以调节代表温度拟合非线性结果 |

### G4a 判读

- 状态匹配后仍对 `H_s` 敏感：标记 `DC_BASESTATE_DOMAIN_NOT_CONVERGED`；
- 仅固定 `P_mean` 扫描敏感：视为热沉物理依赖，不自动失败；
- QS-0 失败而 QS-1 通过：形成可发表的“标量工作点不足、完整基态线性化有效”结论；
- QS-1 仍失败且超过 `U_gov`：才进入动力学非线性归因。

## 9.2 G4b：自热建立瞬态

### 必须顺序

```text
先 1D NSF
→ 热沉模型/等效热阻/初态闭合
→ 状态匹配域高检查
→ 再评估 LBM 实现
```

LBM G4b 只有在 G1-W、G2-O 均通过，且不重新触发边界缝、体积注入和全局谱算子故障时才执行。

### 通过标准

- `T_bar_s(t)` 与热沉能量记账闭合；
- 动态增益在滑动窗口与多窗口拟合下稳定；
- 在相同目标 `Theta_DC(t)` 或相同等效热阻下，域高变化不改变主要时间常数超过 5%；
- 去趋势阶数变化不改变主结论；
- 1D 与 LBM 的方向和标度一致；
- 无数值修复。

若 G4b-LBM 失败，可标记：

```text
A2B_LBM_WAIVED_BY_SCOPE
A2B_1D_ONLY
```

这不阻塞 A1、A2a、A5 的 JASA/JSV 路线。

---

# 10. G5：二维增量门

## 10.1 默认决策

```text
FINITE_WIDTH_2D_WAIVED_JASA_SCOPE
```

完整有限宽度二维不是基础论文入口门。

## 10.2 G5-lite

可先执行 x 向周期单元中的有限宽加热带：

- 单元内有加热带边缘；
- x 向仍周期；
- 比较中心区与边缘区非线性；
- 不声称孤立膜自由场指向性。

该路径能提供二维增量，同时降低侧向开边界风险。

## 10.3 完整 G5 启动条件

只有同时满足：

1. WP3 已证明非线性信号明确；
2. LBM 与 1D 互证；
3. 投稿目标升级为 PRA；
4. 独立风险评估接受 3–6 周以上开发风险；
5. 侧向开边界、膜端角点和 Grad 壁端接有明确止损线；

才可启动完整有限宽度二维。

失败标签：

```text
FINITE_WIDTH_2D_FAILED_BOUNDARY_ARTIFACT
FINITE_WIDTH_2D_WAIVED_JASA_SCOPE
```

---

# 11. 准静态修正规则

## 11.1 非线性实际传递函数

$$
H_{\rm NL}=\frac{\hat p_1^{\rm nonlinear}}{\hat P_1}
$$

## 11.2 QS-0：标量工作点模型

主 QS-0 冻结为：

$$
H_{\rm QS0}=H_{\rm lin}(\bar T_s,\chi_{\rm eff})
$$

主代表温度固定使用膜平均温度 `T_bar_s`，不得在结果出来后选择“最合适”的气体平均温度。热流加权气体温度仅作为预注册敏感性分支。

## 11.3 QS-1：完整 DC 基态线性化

$$
H_{\rm QS1}=\mathcal{L}[U_0(y)]
$$

其中 `L[U0]` 是对完整非均匀 DC 基态的线性化增量传递函数。

## 11.4 修正规则误差

$$
E_A^{(j)}=\frac{|H_{\rm NL}-H_{\rm QSj}|}{|H_{\rm NL}|}
$$

$$
E_\phi^{(j)}=|\arg H_{\rm NL}-\arg H_{\rm QSj}|,\qquad j=0,1
$$

## 11.5 预注册判定

| 标签 | 判定 |
|---|---|
| `QS0_ENGINEERING_VALID` | `E_A^(0) ≤ max(U_gov,3%)` 且 `E_phi^(0) ≤ max(U_phi,3°)` |
| `QS1_BASESTATE_VALID` | `E_A^(1) ≤ max(U_gov,2%)` 且 `E_phi^(1) ≤ max(U_phi,2°)` |
| `DYNAMIC_NONLINEAR_RESIDUAL_IDENTIFIED` | QS-1 仍系统性超过门限，并通过网格、窗口、模型与谐波 Gate |

若 QS-0 失败而 QS-1 通过，结论是“标量工作点不足，但 DC 基态线性化可解释”；只有 QS-1 也失败时，才把剩余量称为周期内动力学非线性。

---

# 12. 后处理与不确定度

## 12.1 多谐波联合拟合器

新增：

```text
postproc/multiharmonic_fit.py
```

模型：

$$
x(t)=a_0+a_1t+a_2t^2+\sum_{n=1}^{N}[A_n\cos(n\Omega t)+B_n\sin(n\Omega t)]
$$

默认 `N=5`，相位约定：

$$
x(t)=\Re[\hat x e^{+i\Omega t}]
$$

必须输出：

- 复幅值与协方差；
- 设计矩阵条件数；
- 残差谱；
- 拟合窗定义；
- 去趋势阶数；
- 多窗口敏感性；
- 合成夹具泄漏结果。

## 12.2 去趋势预注册

| 协议 | 主拟合 | 敏感性拟合 |
|---|---|---|
| A1 | 常数项；无时间趋势 | 一次趋势，仅作检查 |
| A2a | 常数项 | 一次趋势，仅作检查 |
| A2b | 一次趋势 | 二次趋势，仅作敏感性 |
| G2 线性夹具 | 常数项 | 不允许按结果更换 |

二次趋势不得作为 A1/A2a 的主拟合，以免吸收真实慢变物理。

## 12.3 可观测量

### 基频增益

$$
G_1=\frac{|\hat p_1|}{P_1}
$$

### A1 动态增益偏离

$$
D_G=\frac{G_1(\varepsilon_{\rm AC})}{G_{1,0}}-1
$$

### A2a 工作点增益偏离

$$
D_{\rm OP}(\Theta_{\rm DC})
=\frac{|H_{\rm inc}[U_0(\Theta_{\rm DC})]|}
{|H_{\rm inc}[U_0(0)]|}-1
$$

`D_OP` 是基础论文首要物理量之一，必须与 QS-0/QS-1 误差同时报告。

### 谐波比

$$
H_2=\frac{|\hat p_2|}{|\hat p_1|},\qquad
H_3=\frac{|\hat p_3|}{|\hat p_1|}
$$

H2 是基础谐波目标；H3 为条件目标。

### 弱非线性标度

$$
m_n=\frac{d\log|\hat p_n|}{d\log P_1}
$$

弱非线性预期仅作为诊断：`m1≈1`、`m2≈2`、`m3≈3`；不得把偏离预期自动解释为物理饱和，必须先排除工作点漂移、热壁质量源与数值算子污染。

## 12.4 确定性数值不确定度

同一配置的确定性重复运行不能作为统计样本。对 QoI `Q`，定义规定敏感性集合：

- 网格；
- 状态匹配的域高/热沉实现；
- 拟合窗；
- 去趋势阶数；
- 时间步或采样；
- 初始相位/初态；
- 模型分支；
- 热壁实现；
- 谐波传递校准；
- 谱修正和高波数滤波消融。

保守敏感性包络：

$$
U_{\rm det}(Q)=\max_j|Q_j-Q_{\rm ref}|
$$

回归拟合可给出 `U_95,fit`，但它只表示拟合不确定度。最终控制量：

$$
U_{\rm gov}(Q)=\max[U_{\rm det}(Q),U_{95,\rm fit}(Q)]
$$

## 12.5 科学信号与非线性起点

### A1 动态基频起点

主工程阈值冻结为 `D_eng=3%`：

$$
|D_G|>\max[U_{\rm gov}(D_G),3\%]
$$

首次跨越只报告区间：

$$
\varepsilon_T^*\in[\varepsilon_-,\varepsilon_+]
$$

### A2a 工作点效应

工作点效应被认为可检测，当：

$$
|D_{\rm OP}|>\max[U_{\rm gov}(D_{\rm OP}),3\%],
$$

或 QS-0 与 QS-1 的差异形成稳定、可复现且超过 `U_gov` 的机制判别，即使 `D_G` 未跨越 3%。

### 谐波效应

H2/H3 使用 §12.6 的声明条件，不使用 `D_G=3%` 阈值替代。

### 项目 Go/No-Go 原则

以下任一结果可构成进入 scoped/完整物理生产的科学信号：

1. A2a 的 `D_OP` 或 QS-0/QS-1 判别超出 `U_gov`；
2. 经 G1-W 与 20 kHz G2-T/G2-A/G2-O 认证的 H2；
3. A1 的 `D_G` 超出 `U_gov` 与 3%；
4. 严格且有价值的非线性上界，前提是壁面、算子和 1D 参考均闭合。

因此，A1 的 `D_G` 未跨越 3% 不得被单独用作项目终止判据。1% 和 5% 阈值仍作为敏感性结果。

## 12.6 谐波可声明条件

全部满足方可进入主结论：

1. G1-W 已通过；
2. 幅值高于小幅值空检底的 3 倍；
3. 高于 `U_gov`；
4. 拟合窗变化不改变结论；
5. 网格/分辨率方向一致；
6. 弱非线性区具有合理阶次标度；
7. 对应 G2-T/G2-A 频率通过；
8. G2-O 算子消融通过；
9. 不依赖 clipping/floor/repair/结果回调。

H3 还必须满足 §7.4 的条件触发；未触发时不得因“已经计算出 3f 数值”而升级声明。

# 13. 工作包与执行顺序

## WP0：范围与合同冻结

交付：

- 本文档入库；
- `Phase5_STATUS.md`；
- 状态标签；
- 目录与命名规范；
- Gate schema；
- 导师/用户范围对齐记录。

## WP1：独立仪器开发

交付：

- `1D-lbm-equivalent`；
- `1D-physical`；
- 多谐波拟合器；
- 低马赫夹具；
- 质量中性热壁设计与边界通量审计工具；
- WP1 双物性消融；
- `route_ab_decision_memo.md`。

## WP2：入口 Gate

执行顺序：

```text
G0
→ G3
→ G1-W
→ G1a
→ G1b
→ G2-T / G2-A / G2-O（10、20 kHz）
→ G4a
→ 条件 G2-T / G2-A / G2-O（30 kHz）
→ 条件 G4b
```

## WP3：首轮信息单元与 Go/No-Go

完成 §14 的 8 个信息单元及其必要网格、窗口、空检、热壁对照、算子消融和 1D 对照。

## WP4：完整物理矩阵

仅在 WP3 正式 `GO` 或用户批准的 `SCOPED_GO` 后执行。WP4 的默认物理优先级为：

```text
A2a/QS-1 主地图
→ A1 动态消融与 H2/上界
→ A5 chi 地图
→ 少量 A3
→ 条件 A2b/H3/F1
```

## WP5：条件升级

- G5-lite；
- 完整 G5；
- 实验形状对照；
- PRA 范围扩展；
- 论文图表与误差预算。

---

# 14. 首轮 8 个高信息量单元

以下是 8 个信息单元，不等于 8 次运行；计入网格、窗口、空检、热壁和算子消融后，预计包含约 20–40 次实际运行。G1-W/G0/G3 属入口 Gate，不计入这 8 个物理信息单元。

| 编号 | 协议 | 目标状态 | 主要目的 |
|---|---|---|---|
| P-LIN | A1，10 kHz | `epsilon_AC≈0.001` | 回归新生产壁下的小幅值链、测空检底 |
| P-AC1 | A1，10 kHz | `epsilon_AC≈0.01` | 检查初始曲率与 H2 阶次 |
| P-AC2 | A1，10 kHz | `epsilon_AC≈0.05` | 动态主入口：`D_G/H2`，H3 仅诊断 |
| P-AC3 | A1，10 kHz | `epsilon_AC≈0.10` 或稳定上限 | 条件测幅值窗与失稳边界 |
| P-DC1 | A2a | `Theta_DC≈0.05`，小 AC | QS-0/QS-1 与 `D_OP` 主检验 |
| P-DC2 | A2a | `Theta_DC≈0.10`，小 AC | 工作点趋势、单调性与模型分辨力 |
| P-H2 | G2-T/A/O，20 kHz | 小幅值 | 2f 传递与数值算子认证 |
| P-1D | 对应 P-AC2/P-DC1/P-DC2 | 双 1D 分支 | 独立互证与 A/B 消融 |

P-H3 不再是首轮强制单元。只有 §7.4 条件触发后，才新增 30 kHz 信息单元。

## 14.1 完整生产 GO

必须同时满足：

1. G0、G3、G1-W、G1a、G1b、20 kHz 的 G2-T/G2-A/G2-O、G4a 达到所需声明范围；
2. 至少 `epsilon_AC=0.05` 被认证；
3. 下列科学信号至少一项成立：
   - P-DC1/P-DC2 的 `D_OP` 或 QS-0/QS-1 判别超过 `U_gov`；
   - P-AC2 的 H2 超过空检与 `U_gov`，且 20 kHz L2 链通过；
   - P-AC2/P-AC3 的 `D_G` 超过 `U_gov` 与 3%；
4. 结果对窗口、网格、状态匹配域高、生产壁和算子消融稳定；
5. 1D 与 LBM 在方向和标度上互证；
6. P-DC1/P-DC2 不由未匹配的 `H_s` 或运行长度主导；
7. 无数值修复或结果回调。

若 A1 的 `D_G` 未超过 3%，但 A2a/QS-1 或 H2 满足上述条件，仍允许 `GO`。若所有非线性指标均低于不确定度，但形成严格上界，可形成用户批准的 `SCOPED_GO_UPPER_BOUND`。

## 14.2 决策结果

```text
GO
  → 执行完整 WP4

SCOPED_GO
  → 只执行被认证的 A2a/A1-H2/A5 或上界子矩阵
  → 必须用户批准

NO_GO
  → 不跑完整矩阵
  → 转模型差异、壁面/算子方法学或重新设计
```

默认规则：未满足 Gate 即 `NO_GO`，不得以进度理由人为改判。

---

# 15. 完整生产矩阵

## 15.1 A1：有符号零均值周期温升扫描

目标 `epsilon_AC`：

```text
0.001, 0.003, 0.01, 0.02, 0.03, 0.05, 0.075, 0.10
```

若 G1 只认证到 0.05，则自动截断高幅值点。

输出：

- `G1/G1,0`；
- `D_G`；
- 基频相位偏移；
- **H2 为基础谐波结果**；
- H3 仅在 §7.4 触发且 30 kHz G2 全通过后升级；
- `m1/m2`，条件 `m3`；
- 热壁差异与算子消融敏感性；
- `U_gov`；
- 能量、质量与状态合法性；
- LBM 与双 1D 分支差异。

A1 的主要作用是隔离周期内动力学、测 H2 或给出严格上界，不要求 `D_G` 必然跨越 3%。

## 15.2 A2a：稳态工作点增量地图（基础论文主锚）

```text
Theta_DC = 0, 0.02, 0.05, 0.10
epsilon_AC = 0.005, 0.02
```

每个 `Theta_DC` 点的 canonical 结果使用同一物理热沉模型。状态匹配域高检查必须按 §9.1 重匹配 `P_mean`。

输出：

- 非均匀 DC 基态；
- `chi_0/chi_eff`；
- 增量基频增益；
- `D_OP`；
- QS-0/QS-1 误差；
- 固定 `P_mean` 的热沉物理敏感性，单独报告；
- DC 对 H2 的影响；H3 条件；
- 1D 双物性消融。

## 15.3 A2b：自热瞬态，条件执行

代表点应覆盖：

- 一个气侧控制点；
- 一个交叉区点；
- 两档功率或 `Theta_DC`。

1D NSF 为必须结果；LBM 为条件结果。LBM 必须继承 G1-W 和 G2-O 的生产仪器。

## 15.4 A5：`chi_0 × epsilon_AC` 地图

建议设计网格：

| `chi_0` | `C_A`，10 kHz | 角色 |
|---:|---:|---|
| 0.01 | `4.45×10^-4 J/(m² K)` | 基线邻近、强气侧控制 |
| 0.1 | `4.45×10^-3` | 气侧控制 |
| 0.3 | `1.34×10^-2` | 过渡前段 |
| 1 | `4.45×10^-2` | 交叉区、通常为 regime extension |
| 3 | `1.34×10^-1` | 膜热容控制、通常为 regime extension |

与：

```text
epsilon_AC = 0.01, 0.05, 0.10
```

组合。若 0.10 未认证，则截断。

结果必须同时按 `chi_0` 和 `chi_eff` 作图。大 `C_A` 点必须明确标注材料支持状态。A5 优先解释 A2a/QS-1 的工作点规律，再讨论 A1 动态残差。

## 15.5 A3：阶跃或包络建立

少量代表 `chi_0` 点。小信号阶跃必须能恢复线性频响；大信号建立用于验证工作点迁移与动态增益。

## 15.6 F1：稀疏频点，条件项

5/20/40 kHz 只用于：

- G2 仪器标定；
- 修正规则可迁移性；
- 少量趋势验证。

不恢复为大规模频率景观。每个物理频点必须支付完整的重标定、G1-W 适用性与 Level A/B/C 复验成本。

## 15.7 A4：双音互调，最后考虑

仅在单音 H2 链闭合后评估。若需要声明 3f 或相关和频，必须先触发并通过 30 kHz G2。差频、和频离开认证点，默认不进入基础论文。

---

# 16. 数据、元数据与复现合同

## 16.1 每次运行的强制文件

```text
<run_id>/
├── config_resolved.yaml
├── summary.json
├── signals.h5
├── harmonic_fit.json
├── provenance.json
├── gate_evaluation.json
└── run_report.md
```

## 16.2 强制 metadata

```text
run_id
created_at
code_commit
config_digest
physics_core_digest
parent_baseline_run
phase5_contract_version
work_package
gate_id
case_family
model_route
property_model_id
tau_policy
mapping_digest
background_path
forcing_protocol
P_mean_W_m2
P_mean_rematched
target_Theta_DC
frequency_Hz
T_ambient_K
T_mean_K
epsilon_AC_measured
Theta_DC_measured
chi_0
chi_eff
C_A_J_m2K
dc_heat_sink_model
dc_heat_sink_parameters
H_s_role
thermal_resistance_effective
grid_shape
dx_m
dt_s
domain_height_m
boundary_model
wall_mass_policy
wall_neutrality_gate_id
boundary_mass_flux_definition
boundary_mass_flux_0f_to_3f
spectral_operator_stack_id
spectral_correction_enabled
high_wavenumber_filter_enabled
high_wavenumber_filter_strength
operator_ablation_run_id
q_feedback_relax
fit_window
fit_cycles
detrend_order
harmonic_order_max
harmonic_fit_condition_number
U_det
U95_fit
U_gov
no_clipping
no_floor
no_positivity_repair
gate_status
scoped_limitations
```

## 16.3 结果字段

至少包含：

```text
T_s_hat_1f
p_hat_1f
p_hat_2f
p_hat_3f
outgoing_mode_1f
outgoing_mode_2f
outgoing_mode_3f
G1
D_G
D_OP
H2
H3
m1
m2
m3
QS0_error_amplitude
QS0_error_phase
QS1_error_amplitude
QS1_error_phase
wall_boundary_sensitivity
operator_sensitivity_D_G
operator_sensitivity_H2
operator_sensitivity_H3
boundary_mass_flux_0f_to_3f
energy_residual
mass_or_flux_residual
wall_temperature_error
```

---

# 17. 仓库目录结构

```text
docs/Phase_5/
├── README.md
├── Phase5_STATUS.md
├── Phase5_指导文档_v1.0.md                 # 历史草案，保留
├── Phase5_指导文档_v1.1.md                 # 上一正式版，保留
├── Phase5_指导文档_v1.2.md                 # 本文档
├── 论文一创新点评审与修订实施方案.md
├── nonlinear_model_freeze.md
├── wall_nonlinearity_neutrality_report.md
├── nonlinear_1d_reference_report.md
├── nonlinear_entry_gate_report.md
├── harmonic_transfer_report.md
├── harmonic_operator_ablation_report.md
├── dc_protocol_report.md
├── route_ab_decision_memo.md
├── wp3_go_nogo_decision.md
└── nonlinear_production_report.md

configs/phase5/
├── g0_effective_properties/
├── g1w_wall_neutrality/
├── g1a_wall_amplitude/
├── g1b_levelc_amplitude/
├── g2_thermal_transfer/
├── g2_acoustic_transfer/
├── g2_operator_ablation/
├── g4_dc_base/
├── a1_signed_zero_mean/
├── a2a_operating_point/
├── a2b_self_heating/
├── a5_chi_map/
└── finite_width/

verification/nonlinear/
├── test_phase5_g1w_wall_neutrality.py
├── test_phase5_g2_operator_ablation.py
└── ...

postproc/multiharmonic_fit.py
reference/nonlinear_nsf_1d.py
results/phase5/
```

---

# 18. 声明语言规则

## 18.1 通过对应 Gate 后可声明

- 参考态输运闭合下的模型内在有限温升非线性；
- 质量中性热壁下的稳态工作点增量效应；
- `D_OP` 与 QS-0/QS-1 的适用区间；
- `epsilon_T*` 区间及 1%/3%/5% 敏感性，若 A1 动态起点可检测；
- 经 20 kHz G2-T/G2-A/G2-O 认证的 L2-2f 出射声学模态 H2；
- H3 仅按实际触发和认证层级声明；
- `chi_0/chi_eff` 工作区趋势；
- 1D 真实空气物性分支对主结论的定界；
- 若 A1 信号很弱，可声明经壁面与算子排除后的非线性上界。

## 18.2 当前或路线 B 下不可声明

- 真实空气 `mu(T)/k(T)` 是 LBM 结果的主导机制；
- `alpha∝T^1.7` 已由 LBM 求解；
- `pressure_preserving` 整行热壁下的 DC/H2 已被证明是气体物理；
- 未经 G2-O 的 H2/H3 不受谱修正或滤波影响；
- 固定近场点的谐波比就是 radiated THD；
- 30 kHz 未认证时的 H3 是 L2 出射模态结论；
- 固定 `P_mean` 改变 `H_s` 是纯数值域高收敛；
- 所有大信号仍处于 M3/M4 原认证包络；
- A1 是真实 Joule 功率协议；
- 大 `C_A` 合成点就是实际 CNT 膜材料点；
- scoped pass 等同 clear pass。

## 18.3 推荐替换语

| 禁止语 | 推荐语 |
|---|---|
| 实验无法分离两个通道 | 直接热功率驱动提供实验中较难实现的严格数值消融 |
| 完全在认证包络内 | 继承 10 kHz 线性基础，并经壁面中性、幅值、谐波与算子入口门重新认证 |
| 纯 EOS 非线性 | 参考态输运闭合下的全非线性理想气体响应 |
| 远场 THD | source-region 或 outgoing-mode harmonic ratio，按 Gate 层级 |
| 域高收敛 | 在固定目标工作点或固定等效热阻下的状态匹配域高检查 |
| 第一个做 | 据本文覆盖的检索范围所知 |

---

# 19. 决策树

```text
WP1 双 1D 分支与质量中性热壁候选完成？
├─ 否 → 不进入非线性 LBM 生产认证
└─ 是
   ↓
显式真实物性增量显著？
├─ 否 → ROUTE_B_MAIN + 1D_REAL_AIR_BOUNDING
└─ 是 → ROUTE_A_COST_REVIEW_REQUIRED
             ├─ 用户不批准 → 保持路线 B
             └─ 用户批准 → 路线 A 实现并重跑 G0–G3
   ↓
G0/G3/G1-W 通过？
├─ 否 → 停止 LBM DC/H2 物理归因
└─ 是
   ↓
G1a/G1b + 20 kHz G2-T/G2-A/G2-O + G4a 满足目标范围？
├─ 否 → FAILED 或 SCOPED_CANDIDATE
└─ 是
   ↓
WP3 是否至少出现一种可归因科学信号？
├─ A2a 的 D_OP/QS 判别
├─ 经认证 H2
├─ A1 的 D_G>阈值
└─ 严格非线性上界
   ↓
LBM 与 1D 方向和标度互证？
├─ 否 → 定位模型差异，不进完整生产
└─ 是
   ↓
GO 或用户批准的 SCOPED_GO
   ↓
优先执行 A2a/QS-1 → A1/H2或上界 → A5 → 少量 A3
   ↓
H3 信号触发？
├─ 否 → 30 kHz waived，H3 diagnostic-only
└─ 是 → 完成 30 kHz G2-T/G2-A/G2-O 后再决定声明
   ↓
A2b 条件执行
   ↓
投稿范围：
├─ JASA/JSV → G5 默认 waived
└─ PRA 升级 → G5-lite / 完整 G5 + 实验锚 + 必要时路线 A
```

---

# 20. 论文结构与投稿定位

## 20.1 基础论文结构

1. **Introduction**：线性 thermophone 背景、有限温升缺口、规定热功率消融价值、三变量框架、审慎创新声明；
2. **Methods**：D2Q37 f-g/SMRT、质量中性热壁、膜—气耦合、路线 B 准确定义、双 1D 模型、多谐波拟合、谱/滤波算子消融、Gate 与不确定度；
3. **Verification**：M3 小幅值回归、G0、G3、G1-W、G1、20 kHz G2、G4a、网格/窗口/状态匹配域高/空检；
4. **Results I — Operating-point nonlinearity**：A2a、`D_OP`、QS-0/QS-1 成立域，作为主物理锚；
5. **Results II — In-cycle dynamics**：A1 的 `D_G`、经认证 H2 或严格上界；H3 条件；
6. **Results III — Regime map**：A5 和少量 A3，条件 A2b；
7. **Discussion**：显式真实物性定界、壁面/算子残差、低 HCPUA 与大信号线性度、范围限制；
8. **Conclusion**：给出工作点修正规则、可检测边界或上界，不超出 Gate。

## 20.2 投稿定位

| 完成范围 | 现实定位 |
|---|---|
| G0/G3/G1-W/G1/G4a + A2a/QS-1 清楚，1D 互证 | JASA / JSV 可行；即使 A1 `D_G` 较弱也不自动失去论文单元 |
| 再取得 20 kHz L2-2f H2 | 显著增强 JASA/JSV 的声学机制贡献 |
| H3 被触发且 30 kHz 全链通过 | 作为加分结果，不是基础录用前提 |
| 再加入实验锚、G5-lite 或完整 G5、必要时路线 A | PRA 条件具备 |
| 只有 A1 `D_G` 弱，但上界严格且壁面/算子方法具有普适性 | 方法学/非线性上界路线，需扩大 tau/k/边界验证 |

方法学路线不是免费保底。若转方法文，必须增加多 tau、多波数、多网格和至少两类质量约束热壁/边界构型的普适性证明。

---

# 21. 风险登记与止损

| 风险 | 触发信号 | 止损动作 |
|---|---|---|
| `pressure_preserving` 热壁产生 DC/H2 质量源 | `rho_w` 展开、全域质量漂移或新旧壁差异超预算 | G1-W 前不得生产；开发质量中性壁，旧壁降为 `DIAGNOSTIC_ONLY` |
| 质量中性壁破坏 M3 导纳 | 小幅值幅值/相位超门或热流被夹死 | 不进入 G1a；修约束重构，不用 equilibrium clamp 代替 |
| 谱修正/滤波控制 H2/H3 | G2-O 开关改变符号、阈值或阶次 | 谐波降为 L1/诊断；不得按结果挑算子栈 |
| Hermite 温度窗过低 | `epsilon_AC=0.03` 已失稳 | 停止大信号主线，转 A2a 小扰动、上界或方法路线 |
| G1b 耦合失败 | G1a 通过而 Level C 失稳 | 保留规定壁温气侧结果；Level C 主张降级或停放 |
| 20 kHz H2 不可认证 | G2-T/A/O 任一失败 | H2 降为 L1 或移出主结论；A2a/QS-1 仍可作为主线 |
| H3 很弱或 30 kHz 失败 | 未满足 §7.4 或 G2 3f 失败 | `H3_DIAGNOSTIC_ONLY`；不阻塞基础论文 |
| A1 `D_G` 未超过 3% | 动态基频近似线性 | 不自动停项；优先 A2a/QS-1、H2 或严格上界 |
| 1D 低马赫求解不足 | G3 线性极限失败 | 不做 LBM 非线性主结论，先修参考仪器 |
| `H_s` 物理效应被误判为域高误差 | 固定 `P_mean` 扫描变化很大 | 改为固定 `Theta_DC` 重匹配，或保持等效热阻；物理敏感性另报 |
| DC 协议状态匹配后仍不收敛 | G4a 在同 `Theta_DC` 下对域高敏感 | A2a/A2b 暂停，只保留 A1/H2或上界 |
| A2b LBM 重新触发边界故障 | 体积注入、边界缝或全局算子伪影 | `A2B_LBM_WAIVED_BY_SCOPE`，保留 1D A2b |
| 路线 A 失控 | 6 周仍未闭合核心 Gate | 返回路线 B + 1D 真实空气定界 |
| G5 撞 D2 领地 | 侧开边界注入伪影 | `FINITE_WIDTH_2D_WAIVED_JASA_SCOPE` |
| 结果依赖调参冲动 | 想逐幅值修改 dx/tau/export/filter/wall | 立即停止；按停放项重启流程处理 |

---

# 22. 投稿前文献核查

投稿前必须重新检索并记录截止日期。关键词至少包括：

```text
thermophone nonlinear
thermoacoustic emission finite temperature
finite-amplitude thermophone
nonlinear thermoacoustic transduction
harmonic distortion thermophone
CNT thermophone nonlinear simulation
热声换能 非线性
大信号 热声
```

重点复查 2023 年以后论文、综述和预印本。首创表述统一使用：

> 据本文覆盖的检索范围所知。

---

# 23. 版本升级与变更控制

以下变更强制升级文档版本并触发相应 Gate 复验：

- 路线 B → 路线 A；
- 修改 dx、dt、tau、热流导出或碰撞闭合；
- 修改生产热壁、质量约束、Grad 非平衡外推或边界执行位置：重跑 G1-W、G1a、G1b，并复核 G2-T；
- 修改谱修正、高波数滤波强度/次数/顺序：重跑 G2-O，必要时重跑 G1/G2；
- 更换 canonical DC 热沉、`H_s` 角色或等效热阻定义：重跑 G4a；
- 更换拟合主模型或去趋势规则；
- 将谐波声明从 L1 升级到 L2-2f/L2-3f/L3；
- 将投稿目标从 JASA/JSV 升级为 PRA 并启动 G5；
- 改变主要工程阈值 `D_eng=3%`。

每次升级必须更新：

```text
Phase5_STATUS.md
revision_history
retest_matrix
affected_claims
production_wall_id
spectral_operator_stack_id
```

## 23.1 v1.2 定向复验矩阵

| 变化 | 强制复验 |
|---|---|
| 从现有 `pressure_preserving` 壁切换到质量中性生产壁 | G1-W、G1a、G1b、G2-T 10/20 kHz、G4a |
| 仅改变诊断壁，不改变生产壁 | G1-W 差异审计 |
| 改变谱修正或滤波 | G2-O；若 1f 线性基线变化 >2%，同时重跑 G1a/G1b |
| 改变 `H_s` 但固定 `P_mean` | 作为热沉物理扫描，不自动触发“收敛通过” |
| 改变 `H_s` 并状态匹配 `Theta_DC` | G4a 状态匹配域高复验 |

---

# 附录 A：关键数值速查

| 量 | 值 | 口径 |
|---|---:|---|
| M3 canonical | `|T_hat_s|=0.37269 K @ 1000 W/m²` | 10 kHz、dx2p6 |
| 基线远场 | `≈0.60 Pa / 86.6 dB` | 10 kHz 法向，每侧 |
| `|Y_g|` | `≈1.40×10^3 W/(m² K)` | 300 K 线性估计 |
| 基线 `chi_0` | `≈0.016` | `C_A=7×10^-4` |
| `chi_0=1` | `C_A≈4.45×10^-2 J/(m² K)` | 10 kHz |
| 原 C_A 网格上限 | `1×10^-2`，`chi≈0.22` | 未跨交叉区 |
| `epsilon_AC=0.05` 预估功率 | `≈4×10^4 W/m²` | 线性外推，仅设计用 |
| `epsilon_AC=0.10` 预估功率 | `≈8×10^4 W/m²` | 线性外推，仅设计用 |
| 热谐波波数 | `k1≈0.098, k2≈0.139, k3≈0.170` | `sqrt(n)` 标度 |
| M3 域 | `ny=48`，约 `125 µm` | 近壁域 |
| 跨域扩散时间 | `≈0.7 ms`，约 7 周期 | 参考估计 |
| M3 幅值边界 | `±5.4%` | 非 clear pass |
| M4 E2/R2 | `1.62% / 2.63%` | scoped 远场链 |
| 现有热壁二阶结构 | `rho_w/rho_0 = 1 - epsilon cos + (epsilon^2/2)(1+cos2Omega t)+...` | G1-W 风险依据 |
| 基础谐波目标 | H2 / 20 kHz / L2-2f | H3 为条件项 |

---

# 附录 B：状态标签建议

```text
# 模型
MODEL_CLOSURE_PENDING
MODEL_CLOSURE_PASSED_ROUTE_B
MODEL_CLOSURE_PASSED_ROUTE_A

# 热壁
NONLINEAR_WALL_NEUTRALITY_NOT_CERTIFIED
NONLINEAR_WALL_NEUTRALITY_PASSED
PRESSURE_PRESERVING_WALL_DIAGNOSTIC_ONLY
MASS_NEUTRAL_WALL_NOT_AVAILABLE

# 1D
NONLINEAR_1D_REFERENCE_NOT_CERTIFIED
NONLINEAR_1D_REFERENCE_PASSED

# 幅值
AMPLITUDE_ENVELOPE_NOT_CERTIFIED
AMPLITUDE_ENVELOPE_PASSED_TO_0P05
AMPLITUDE_ENVELOPE_PASSED_TO_0P10

# 谐波与算子
HARMONIC_TRANSFER_NOT_CERTIFIED
HARMONIC_OPERATOR_ABLATION_NOT_CERTIFIED
HARMONIC_OPERATOR_ABLATION_PASSED
HARMONIC_CLAIM_LEVEL_L1
HARMONIC_CLAIM_LEVEL_L2_2F
HARMONIC_CLAIM_LEVEL_L2_3F
HARMONIC_CLAIM_LEVEL_L3
H3_DIAGNOSTIC_ONLY
G2_3F_WAIVED_BY_SIGNAL

# DC
DC_PROTOCOL_NOT_CERTIFIED
DC_BASESTATE_STATE_MATCHED_PASSED
DC_BASESTATE_DOMAIN_NOT_CONVERGED
DC_HEATSINK_PHYSICAL_SENSITIVITY_RECORDED
A2B_1D_ONLY
A2B_LBM_PASSED

# 生产
PHASE5_NONLINEAR_PRODUCTION_GO
PHASE5_NONLINEAR_PRODUCTION_GO_SCOPED
PHASE5_NONLINEAR_PRODUCTION_GO_UPPER_BOUND
PHASE5_NONLINEAR_PRODUCTION_NO_GO

# 几何
FINITE_WIDTH_2D_DEFERRED_JASA_SCOPE
FINITE_WIDTH_2D_LITE_PASSED
FINITE_WIDTH_2D_PASSED
FINITE_WIDTH_2D_WAIVED_JASA_SCOPE
```

---

# 附录 C：v1.1 相对 v1.0 的主要修订

| # | 修订 |
|---:|---|
| 1 | 冻结 Phase 5 权限层级，取消“本文可覆盖所有上游文档”的过宽表述。 |
| 2 | 正式采用 JASA/JSV 基础范围、PRA 条件升级范围。 |
| 3 | 路线 B 改为“参考态输运闭合下的全非线性理想气体”，删除“纯 EOS 分离体”表述。 |
| 4 | G0 强制同 mapping/同 tau，增加 270 K 点，区分等压与等密度路径。 |
| 5 | G0 分为低波数构成律与 `k1/k2/k3` 生产波数仪器响应。 |
| 6 | 1D NSF 分为 `1D-lbm-equivalent` 与 `1D-physical`，增加低马赫和平衡保持 Gate。 |
| 7 | A1 定义为有符号零均值数值消融。 |
| 8 | A2a 改为非均匀 DC 基态上的增量响应；均匀升温背景移回 G0。 |
| 9 | A2b 拆成 1D 必须、LBM 条件任务。 |
| 10 | G1 拆为 G1a/G1b；G2 拆为 G2-T/G2-A。 |
| 11 | 新增 QS-0/QS-1 的公式、误差和预注册阈值。 |
| 12 | 新增 `chi_0/chi_eff` 双口径和材料支持标签。 |
| 13 | 用确定性 `U_gov` 替代重复运行 `3 sigma`；主工程阈值冻结为 3%。 |
| 14 | 谐波声明分为 L1/L2/L3；基础论文目标冻结为 L2。 |
| 15 | 新增 Gate 统一字段、用户 scoped pass 权限和路线 A 重认证状态机。 |
| 16 | 新增完整数据 schema、metadata 和运行文件合同。 |
| 17 | 首轮“8 点”改为“8 个信息单元”，明确实际运行数更高。 |
| 18 | G5 默认 waived，增加 G5-lite。 |
| 19 | 工期移至非规范性规划附录，不构成 Gate 承诺。 |

---

# 附录 D：v1.2 相对 v1.1 的主要修订

| # | 修订 |
|---:|---|
| 1 | 新增强制 `G1-W`，把热壁质量中性和二阶边界源从一般幅值 Gate 中独立出来。 |
| 2 | 明确现有 `pressure_preserving` 整行 Grad 壁会在规定正弦温度下内生 DC 与 2f 密度项；通过前降为诊断用途。 |
| 3 | 要求开发零法向质量通量、不可穿透、保留物理非平衡热流的生产壁，并重新回归 Level A/Level C。 |
| 4 | G2 新增 `G2-O`，对全局谱修正和高波数滤波执行单音泄漏与归一化非线性消融。 |
| 5 | 基础谐波目标收缩为 H2 / 20 kHz / L2-2f；H3 / 30 kHz 改为信号触发的条件项。 |
| 6 | 把 A2a + QS-1 提升为基础论文首要物理锚点；A1 `D_G>3%` 不再是唯一 Go 条件。 |
| 7 | 首轮 8 个信息单元用第二个 DC 工作点替代强制 P-H3，增强工作点趋势判别。 |
| 8 | 新增 `D_OP`，并把 A2a 工作点效应纳入独立的可检测判据。 |
| 9 | 修正 `H_s` 口径：固定 `P_mean` 改变 `H_s` 是热沉物理扫描；数值域高检查必须固定 `Theta_DC` 或等效热阻。 |
| 10 | 更新 WP2 Gate 顺序、WP4 物理优先级和 Go/No-Go 判据。 |
| 11 | metadata 增加生产壁、边界质量通量、谱算子栈、算子消融和状态匹配热沉字段。 |
| 12 | 更新论文结构：A2a/QS-1 为 Results I，A1/H2 或上界为 Results II。 |
| 13 | 风险表新增热壁伪 H2、谱/滤波控制谐波、H3 条件化及 `H_s` 物理混淆。 |
| 14 | 版本复验矩阵明确生产壁、谱算子和热沉变化所触发的 Gate。 |

---

# 附录 E：非规范性规划估计

> 本附录仅用于资源规划，不构成合同承诺。

| 工作包 | 规划估计 |
|---|---:|
| WP0 | 3–5 天 |
| WP1 | 2–4 周 |
| WP2 | 2–4 周，可与 WP1 部分并行 |
| WP3 | 1–2 周 |
| WP4 | 3–6 周 |
| 路线 A | 额外 1–3 个月，6 周核心 Gate 止损 |
| G5-lite | 约 1–3 周 |
| 完整 G5 | 额外 3–6 周以上，带独立失败风险 |

生产物理点与验证、网格、窗口、空检和消融点必须分别预算。不得再使用“40 个算例、两周完成”作为高置信度承诺。

---

*本文档自入库之日起作为 Phase 5 范围内的正式执行合同。技术 Gate 由冻结阈值判定；范围选择、scoped continuation、路线 A 启动和 PRA 升级由用户决策。v1.2 新增的生产壁与算子消融要求在通过前具有阻断效力。*
