# Phase_5 阶段状态

**阶段**：Phase_5 — 热声薄膜有限温升非线性换能（Nonlinear Entry and Production Contract）
**合同**：`docs/Phase_5/Phase5_instruct_v1.2.md`（v1.2，2026-07-20 经 WP0 冻结为唯一规范性入口；评审基线 `b86459c`）
**最后更新**：2026-08-17（D1 strict-B 冻结设计已按用户要求压缩为 88 行实验执行清单；尚未实施，D1 科学判决保持开放）

**本文职责**：状态标签 + Gate 现值 + 执行流水（做了什么 / 为什么 / 结果）+ WP4 生产数据。
**本文不写**：技术细节、推导、诊断链——一律在对应报告，本文只给结论与指针。
**历史细节**（WP0/WP1 逐项交付表、已闭合风险原文、原始更新日志全文）：`x/phase5_execution_history.md`。

---

## 1. 当前状态

**WP0–WP4 授权范围全部完成**（2026-08-04），2026-08-06 起进入**毕业导向论文写作轨**。2026-08-08 起执行用户指令的**机理诊断单元序列**（JAB → JAB2 → NSF 仲裁 → wallfix 反证 → ghost 扫描 → 跨栈 1a → D1-B buffer 代理，见 §2）。2026-08-17 用户授权 strict-B 设计并确认主文档采用短版实验执行清单，但未授权实施或运行。上述工作均不改变任何 Gate 与 `FINAL_PRODUCTION_NOT_CLAIMED`；D1 科学判决保持开放。

状态标签（定义随合同 §0.3 冻结；**本表是唯一现值追踪处**）：

```text
PHASE5_NONLINEAR_ENTRY_CONTRACT_v1.2
PHASE5_SCOPE_FROZEN
ROUTE_B_MAIN
1D_REAL_AIR_BOUNDING
MODEL_CLOSURE_PASSED_ROUTE_B
NONLINEAR_WALL_NEUTRALITY_CERTIFIED
PRESSURE_PRESERVING_WALL_DIAGNOSTIC_ONLY
AMPLITUDE_ENVELOPE_NOT_CERTIFIED（G1a 已过带 G1A_PASSED_TO_0P05；耦合侧顺延 G4a）
G1A_PASSED_TO_0P05
HARMONIC_TRANSFER_CERTIFIED_10K20K
HARMONIC_OPERATOR_ABLATION_CERTIFIED
HARMONIC_CLAIM_LEVEL_L2_2F（H3 侧 H3_DIAGNOSTIC_ONLY + G2_3F_WAIVED_BY_SIGNAL）
H2_BASE_TARGET_H3_CONDITIONAL
NONLINEAR_1D_REFERENCE_CERTIFIED
DC_BASESTATE_STATE_MATCHED_PASSED
DYNAMIC_NONLINEAR_RESIDUAL_IDENTIFIED（核心科学发现：静态重求值族符号级失效）
LEVELC_COUPLED_ROW_PASSED
WP3_SCOPED_GO_BY_USER
WP4_SUBMATRIX_COMPLETE
ROUTE_LBM_BOUNDARY（生产算子 JAB2 簿记路线；不是 strict-B 因果判决，D1 科学 gate 开放）
D1_ALGEBRA_CLOSED
D1_B_BUFFER_DIAGNOSTIC_NULL
D1_BUDGET_PARTIAL
STRICT_B_DESIGN_CONDITIONAL
STRICT_B_IMPLEMENTATION_NOT_STARTED
D1_SCIENTIFIC_GATE_OPEN
FINITE_WIDTH_2D_DEFERRED_JASA_SCOPE
FINAL_PRODUCTION_NOT_CLAIMED
```

### Gate 现值（定义 / Fixture / 阈值见合同 §5–§10；证据与数值见各报告）

| Gate | 内容 | 现值 | 权威 run / 报告 |
|---|---|---|---|
| G0-B | 物理模型闭合门（路线 B 有效物性） | **`SCOPED_PASSED_BY_USER`**（2026-07-23，D5-2）。围栏=剪切 ν 不认证 + 低波数按有限-k 表格口径 | `20260722T173919Z` / `x/nonlinear_model_freeze.md` |
| G3 | 独立非线性 1D NSF 参考（双物性分支） | **`PASSED`**（2026-07-26；七行全过，分支正式定义冻结） | `20260726T082938Z` / `x/nonlinear_1d_reference_report.md` |
| G1-W | 热壁非线性中性与质量约束 | **`PASSED`**（2026-07-27；八行全过）。**生产壁=v1.1 对称质量中性壁**；矩通道重标定 3.055@+17.5° | `20260727T083342Z` / `x/wall_nonlinearity_neutrality_report.md` |
| G1a | 规定壁温气侧幅值包络 | **`PASSED` + `G1A_PASSED_TO_0P05`**（2026-07-28）——生产矩阵解锁至 ε=0.075 | `20260728T085824Z` / `x/nonlinear_entry_gate_report.md` §A |
| G1b | Level C 耦合幅值包络 | **`FAILED`（终判，2026-07-30，D5-4 回退执行）**——密封无沉 rig 耦合回路结构性不可闭合；耦合包络顺延 G4a | 四 run 归档 `M5_runs/g1b_failed_*` / 同上 §B |
| G2-T / G2-A / G2-O | 谐波传递链 / 声学链 / 算子消融（10+20 kHz） | **三门全 `PASSED`**（2026-07-30）→ `HARMONIC_CLAIM_LEVEL_L2_2F` 生效；H3 未触发 | `…095502Z` / `…104402Z` / `…125635Z`；`x/harmonic_transfer_report.md`、`x/harmonic_operator_ablation_report.md` |
| G4a | 稳态 DC 基态 + 小扰动（canonical 热沉） | **`PASSED`**（2026-08-01；十一行全过）——帐篷双带架构；**QS 判读产出 `DYNAMIC_NONLINEAR_RESIDUAL_IDENTIFIED`**；耦合行重跑闭合 | `20260801T081856Z` + `20260801T155507Z` / `x/dc_protocol_report.md` |
| G4b | 自热建立瞬态 | `NOT_RUN` | — |
| G5 | 完整有限宽度二维 | `WAIVED_JASA_SCOPE`（D0-9） | — |
| 30 kHz G2 链 | H3 条件触发项（§7.4） | 未触发；`H3_DIAGNOSTIC_ONLY` / `G2_3F_WAIVED_BY_SIGNAL` | — |

---

## 2. 执行流水

倒序。**目的 / 结果**为主，技术细节看"详情"列。

| 日期 | 单元 | 目的 | 结果 | 详情 |
|---|---|---|---|---|
| 2026-08-17 | **D1 strict-B 实验执行清单** | 把 D1 §9.1 的零体积 ghost/删除 band 要求落实为可实现、可证伪的最短实验合同 | **`STRICT_B_DESIGN_CONDITIONAL / IMPLEMENTATION_NOT_STARTED / D1_SCIENTIFIC_GATE_OPEN`**：冻结设计按用户要求由 624 行压缩为 88 行；保留镜像半域、首气体单元 incoming-`g`、闭柱等质量、`CONST_G→G0 admission`、局部守恒、冷锚、三档 JVP、热两点分类和停止条件 | `strict_faceflux_candidate_b_design_v1.0.md`；仅文档，无代码、配置、测试或 run |
| 2026-08-17 | **D1-B buffer 面通量代理实测** | 检查共享 buffer 骨架内移除显式 `c_vρ̄δθ_w` 零阶储能源是否足以移动 d_OP | **`D1_B_BUFFER_DIAGNOSTIC_NULL / D1_BUDGET_PARTIAL`**：d_OP=−2.8078/−5.2788，对生产仅 +0.0268/+0.0383 pp；冷复比幅值 −2.446% 命中预算、相位 −3.959° 未命中。实现保留有限体积共享 band，且只跑单 h，故不能裁决严格 B、§13.2、纯气侧响应或能量语义 family | `faceflux_wall_report.md` REPORT_v1.1；A 机 `20260817T090753Z_full`；归档 `M5_runs/faceflux_20260817_A/` |
| 2026-08-14 | **跨栈单元 1a（碰撞算子结构轴）** | 补投稿最大缺口："只在自己一套栈上测过"——换碰撞算子复测伪迹是否仍在 | **两轴均闭合。① BGK 轴**：自写诊断 BGK（(τ_f,τ_g) 由冻结 mapping 导出，ν/α 与生产逐位相同）在**无壁周期箱**上谱半径 1.46–2.02（生产 1.000000）——**保 α 的整个可行区间无一稳定**，判决网格三个工作点 settle 全死 → 计划书 §3 回退路径 1 触发。**② CFG 轴 `CROSSSTACK_FAMILY_ROBUST`**：唯一有实质杠杆的存活开关 `DEVMEAS`（剪切 ν_eff ×4）只把 d_OP 推动连续参照缺口的 **10.5%**（−2.8345→−2.4121 / −5.3171→−4.5194 pp），符号不变；PROD 锚点复现 TAN **1.3e-05/2.5e-05 pp** | `crossstack_collision_report.md`（REPORT_v1.0）；`crossstack_1a_plan_v1.0.md`；B 机权威 `20260814T090824Z_full`（归档 `M5_runs/crossstack_1a_20260814_B/`）+ A 机 `20260814T090438Z_preflight` / `20260814T092631Z_smoke` |
| 2026-08-13/14 | **ghost 自由弛豫参数扫描** | 回答文献核查暴露的审稿线："离散效应传统的标准补救=调 ghost 自由弛豫参数，你们试过吗" | **双向失败**：τ>1 使伪迹加重且 τ≥1.08 失稳；τ<1 方向正确但仅 τ≥0.99 合法、外推穿越点 τ≈0.967 落在崩溃区且需 −28% 冷态导纳代价。锚点复现 TAN 0.005/0.009 pp | `ghost_relax_scan_report.md`；B 机 `20260813T100957Z` / `20260813T194351Z` |
| 2026-08-11/14 | **投稿前文献核查（第一轮）** | 核实"边界家族被广泛使用"与 novelty 关口 | 家族普遍性**坐实**（Guo 2002 被引 733、JCP 2012 被引 204）；novelty 未被证伪（含 1184 篇施引文献追踪）；**LBM×thermophone 空白**；定位升级为"标准补救可证明失效的首例" | `literature_check_wallfix_novelty_v1.md` |
| 2026-08-11 | **A2-5 修复性反证（wallfix）** | 检验能否用有原则的边界修正消除 A2-5 异常，同时不破坏既有认证 | **`WALLFIX_FAMILY_NULL`**：四不变量内合法壁族全体位移 ≤1.1e-6 pp（对照非法消融 +8.82 pp，差 7 个量级）→ 异常是**湿节点逐步重钉扎范式的结构性质**，范式内不可修 | `wallfix_a2a5_counterproof_report.md`；`20260811T085347Z_auth` |
| 2026-08-11 | **NSF 热基态切线仲裁** | 判定负工作点趋势属连续热声物理还是 LBM 热壁边界效应 | LBM-equivalent 介质**情况 A/D 为正**（+1.18/+2.34%）；两个基态梯度动态耦合项仅 −0.26/−0.51 pp（≈残差 5%）→ 连续 NSF 造不出该负号；维持生产算子 `ROUTE_LBM_BOUNDARY` 簿记路线，**不是 strict-B 因果闭合** | `NSF_hot_basestate_tangent_arbitration_report.md`；`20260811T055850Z` |
| 2026-08-10 | **JAB2 第二轮细粒度定位** | 把 JAB 定位的 A2/A3 两块拆解到子项 | **A2 整块=单项 A2-5**（壁面内能目标与 g 重钉扎的基态密度敏感度，σ=1.000 两点）；A3=两族抵消束 `A3_DISTRIBUTED`；冻结路由 **`ROUTE_LBM_BOUNDARY`** | `wp4_jacobian_ablation_report.md` §7；云端 96 核 `20260810T144425Z` |
| 2026-08-09/10 | **WP4-JAB 热基态 Jacobian 消融** | 定位负趋势的 LBM 内部来源（算子块级） | **`JAB_COUPLED_CANDIDATE_A2_A3`**：v1.1 带重构 × 宏观/平衡两块近可加承载全部工作点响应；应力/热流/streaming/滤波/声学族排除 | 同上；`20260809T195359Z` |
| 2026-08-06/08 | 数据层与文档层重整 | 数据不该住在文档层；入口文档瘦身 | `M5_runs`/`M2_runs` 迁入 `archive/`；`PROJECT_CONTEXT` 361→199 行；四层数据边界确立 | `archive/README.md`；历史日志 |
| 2026-08-06 | **论文架构 v0.3** | 毕业导向收缩 | 一主两辅、5 节 5 图；Results I 为唯一中心；投稿前不新增模拟 | `Manuscript/Paper1_Manuscript_Architecture.md` |
| 2026-08-05 | **WP4-TAN 切线响应诊断** | 排除"负趋势来自有限幅值"的解释 | **`TANGENT_CONFIRMED`**（生产 D_OP 与完整时域切线一致，偏差 ≤0.007 pp）+ `GLOBAL_OR_LOWK_LOCALIZED`（未见随工作点增强的高 k 局域特征） | §3.2；B 机 `20260805T092726Z` |
| 2026-08-04 | **QS-1k 机理判别** | 检验波数分辨的静态重求值能否恢复负号 | **`MECHANISM_NOT_CLOSED`**：QS-1k 反而更正（+2.08…+10.69%）——静态族三级（QS-0/QS-1/QS-1k）同向失效 | §3.2；`20260804T090947Z`（零新 LBM 算力） |
| 2026-08-03/04 | **WP4 认证子矩阵（A2a / A1 / A5 + 1D 臂）** | D5-6 `SCOPED_GO` 授权范围的生产证据 | 三支全部权威闭合：A2a 残差标度律五点、A1 的 H2/ε 四位恒定跨 75×、A5 传递滚降 7.1× 全图 | **数据见 §3**；双机分跑 D5-3 |
| 2026-08-02 | WP3 八信息单元 | Go/No-Go 决策材料 | 单日全部完成（双机分跑首例）；§14.1 对照支持 `SCOPED_GO` | `x/wp3_go_nogo_decision.md` |
| 2026-08-01 | **G4a 权威认证** | WP2 最后一门 + 论文主锚 | `PASSED`；**QS 判读=动力学非线性残差实锤**（D_OP −2.83% vs 静态族 +2.4%，符号相反）；耦合包络于沉几何闭合 | `x/dc_protocol_report.md` |
| 2026-07-30 | G2-T / G2-A / G2-O | 谐波传递与算子消融 | 三门单日全过；`HARMONIC_CLAIM_LEVEL_L2_2F` 生效 | 见 Gate 表 |
| 2026-07-29/30 | G1b 终判 | 耦合幅值包络 | `FAILED`（五通道证据链）；回退条款执行，耦合顺延 G4a | `x/nonlinear_entry_gate_report.md` §B |
| 2026-07-26/28 | G3 / G1-W / G1a | WP2 入口 Gate 序列 | 三门依次 `PASSED`；生产壁认证、生产矩阵解锁至 ε=0.075 | 见 Gate 表 |
| 2026-07-20/23 | WP0 冻结 + WP1 仪器 + G0-B | 合同冻结、独立仪器交付、模型闭合门 | WP0 全交付；WP1 五项仪器交付并经判别链收官；G0-B `SCOPED_PASSED_BY_USER`；路线决策 D5-1 | `x/phase5_execution_history.md` §A、`x/route_ab_decision_memo.md` |

---

## 3. WP4 生产数据（论文数字唯一家）

### 3.1 A2a 工作点地图（Results I 主锚；A 机谱系，commit `fefee6b`）

| Θ_DC | D_OP 实测 | QS-0 | QS-1 | 残差(实测−QS1) | χ_eff | 耦合点 | run |
|---|---|---|---|---|---|---|---|
| 0.02 | **−1.17%@−0.57°** | +0.97% | +0.95% | **−2.12pp** | 0.0131 | 1.0383@+1.03° | `20260803T185241Z` |
| 0.05(=G4a) | −2.83%@−1.38° | +2.40% | +2.35% | −5.18pp | 0.0133 | 1.0376@+1.05° | `20260801T081856Z` |
| 0.075(加密点) | **−4.11%@−2.02°** | +3.58% | +3.50% | **−7.61pp** | 0.0135 | 1.0369@+1.06° | `20260803T185101Z` |
| 0.10 | −5.31%@−2.62° | +4.74% | +4.64% | −9.95pp | 0.0137 | 1.0363@+1.07° | `20260802T104619Z` |

- **动力学残差标度律五点闭合**（含 0 平凡点）：残差/Θ_DC = −106/−104/−101/−99 pp——近线性、轻微亚线性，符号全程一致；**QS 静态族在每个点反号**。加密点落在内插线上（偏差 0.04pp）。
- 耦合仪器跨四工作点稳健（1.036–1.038@+1.0–1.1°）；χ_0=0.0129 双 run 复现；状态匹配 ≤4.2e-5。

### 3.2 机理判别行（无独立报告，数值家在此）

- **QS-1k**（2026-08-04，`20260804T090947Z`）：用 G0 实测 α_eff(k,T) 表构造 k 分辨静态重求值——**判定 `MECHANISM_NOT_CLOSED`**：结果 +2.08/+5.25/+7.94/+10.69%（解释分数 −0.53~−0.61），比 QS-1 更正。结构性结论：高 k 温度指数均大于 k1，所测试的静态重求值层级只能给出正号。**排除静态解释族，不等于识别唯一动力学机理。**
- **WP4-TAN**（2026-08-05，B 机 `20260805T092726Z`，131 min）：Θ_DC∈{0,0.05,0.10}×ε{0.00125,0.0025,0.005} 复数 (1,ε²) 切线外推。**R1=`TANGENT_CONFIRMED`**：D_OP_tan=−2.835%/−5.317% vs 生产 −2.83%/−5.31%，偏差 −0.005/−0.007pp（容差 1/40）→ **排除有限幅值解释**。R2=`GLOBAL_OR_LOWK_LOCALIZED`（未发现随工作点增强的高 k 局域异常；与低波数或全局响应一致，唯一机制开放）。

### 3.3 A1 幅值阶梯（Results II 主表；B 机 `20260803T113507Z`，digest `194ff1249fe6`）

| ε | D_G | 相位偏移 | H2_q/ε |
|---|---|---|---|
| 0.001 | 0(参照) | 0 | 0.4253 |
| 0.003 | −4.1e-6 | −0.0001° | 0.4253 |
| 0.01 | −5.1e-5 | −0.0017° | 0.4253 |
| 0.02 | −2.0e-4 | −0.0067° | 0.4253 |
| 0.03 | −4.6e-4 | −0.0151° | 0.4252 |
| 0.05 | −1.27e-3 | −0.0418° | 0.4252 |
| 0.075 | −2.85e-3 | −0.0941° | 0.4251 |

- **H2_q/ε 四位恒定跨 75× 幅值窗**；m₂=1.9992；**D_G ∝ ε² 教科书**（14.02 vs 预测 14.06）。与 WP3 四个重合点**打印位逐位一致**（同机复现纪律实证）。

### 3.4 A5 χ 地图（Results III；A 机 `20260804T002154Z`，10/10 稳定）

| χ_0(冷参照) | χ_eff | \|G1\|@相位(ε=0.01) | 一致性比 | D_chi | H2_Ts(ε=0.01) | C_A_si [J/m²K] | material |
|---|---|---|---|---|---|---|---|
| 0.016 | 0.0165 | 136.8@−60.9° | 1.0361@+1.07° | 0.9994 | 2.5e-3 | 7.10e-4 | **supported**（基线膜） |
| 0.1 | 0.103 | 118.5@−65.1° | 1.0326@+0.80° | 0.9995 | 2.2e-3 | 4.44e-3 | synthetic |
| 0.3 | 0.309 | 88.8@−71.6° | 1.0260@+0.45° | 0.9996 | 1.8e-3 | 1.33e-2 | synthetic |
| 1 | 1.029 | 46.4@−80.5° | 1.0149@+0.12° | 0.9998 | 1.2e-3 | 4.44e-2 | synthetic |
| 3 | 3.088 | 19.4@−86.1° | 1.0065@+0.02° | 0.9999 | 5.6e-4 | 1.33e-1 | synthetic |

- **传递滚降 7.1× 跨图、相位 −60.9°→−86.1°**（趋向纯积分器）=气控→容控 regime 转变完整实测；**D_chi 全图 0.9994–0.9999**（耦合回路不放大气侧非线性）。χ=0.01 端点被仪器稳定性边界截断（v1 诊断判死，**非物理悬崖**）；ε=0.10 列被 G1a 授权截断。

### 3.5 1D DC 臂（连续参照中间层；`oned_dc_arm/20260803T083909Z`）

五点双分支单一约定系列（修正读出）：**lbm-eq +0.50/+1.24/+1.86/+2.47%**、**physical +0.34/+0.84/+1.25/+1.65%** @Θ_DC={0.02,0.05,0.075,0.10}；δ/24 复核收敛 0.001pp。**三层参照层级（QS > 1D 全非线性 > LBM 反号）在全部四个工作点成立。**

---

## 4. 决策记录

| ID | 日期 | 决策 | 决策方 |
|---|---|---|---|
| D5-7 | 2026-08-17 | 先完成 strict-B 设计，并确认权威主文档采用短版实验执行清单；实施、代码与 run 均待后续明确批准 | 用户 |
| D5-6 | 2026-08-03 | WP3 判定 **`SCOPED_GO`**，启动 WP4；授权范围=A2a/A1/A5 认证子矩阵（A3/A2b/H3/F1 不在授权内） | 用户 |
| D5-5 | 2026-08-02 | 启动 WP3 首轮八信息单元 | 用户 |
| D5-4 | 2026-07-29/30 | G1b 批准第四耦合设计 → 预注册回退条款触发并执行（耦合顺延 G4a） | 用户 |
| D5-3 | 2026-07-29 | 跨机口径**「每机逐位、跨机容差」**；权威 run 记机器指纹 | 用户 |
| D5-2 | 2026-07-23 | G0-B `SCOPED_CANDIDATE` → **`SCOPED_PASSED_BY_USER`**（围栏：剪切 ν 不认证 + 低波数表格口径） | 用户 |
| D5-1 | 2026-07-22 | 路线决策：维持 **`ROUTE_B_MAIN + 1D_REAL_AIR_BOUNDING`**（升级条件预注册） | 用户 |
| D5-0 | 2026-07-20 | **Phase_5 立项**，采纳合同 v1.2；Phase_4 转维护态 | 用户 |

决策全文与依据：`x/wp3_go_nogo_decision.md` §7（D5-6）、`x/route_ab_decision_memo.md` §7（D5-1）、`x/nonlinear_entry_gate_report.md` §B（D5-4）、`scripts/README.md`（D5-3 详录）。
预授权口径（无需再决策）：路线 A 启动、scoped 升级、`SCOPED_GO`、PRA 升级、完整 G5 均属**用户专属决策**，脚本与报告不得自动作出。

---

## 5. 生效中的风险与边界

- **继承硬约束**：单频 10 kHz、dx2p6 mapping，不换 dx/dt/tau/热流导出因子/Grad 壁重构（M3 决策 §3；触发即走停放项重启流程）。
- **热壁边界**：生产壁=v1.1 对称质量中性壁（已认证）；旧壁 `pressure_preserving` 为 `DIAGNOSTIC_ONLY`。A2-5 已证明是**四不变量湿节点整格胞重钉扎范式内**的结构性质；buffer 代理没有离开共享有限体积行，不能把该结论外推到 strict-B。strict-B 仅完成设计、未实施；即使未来翻正，生产化仍须另过 G1-W 级重认证。
- **算子消融纪律**：禁止按结果挑"更好看"的算子栈；诊断用的 `fourth_order`/τ≠1 各行**无生产有效性声明**。
- **规划非承诺**：合同附录 E 工期为非规范性估计；禁用"N 算例 M 周"式高置信承诺。
- **`results/phase5/` 不入库**；权威 run 精选摘要归档见 `Phase5_Output_Files_Guide.md`（当前 `archive/M5_runs/` 30 项）。
- 已闭合/已解除的风险行原文见 `x/phase5_execution_history.md` §B。

---

## 6. 下一步（论文写作轨；生产证据冻结）

**当前首要决策点是是否授权 strict-B 实施。** 短版实验执行清单已经确认，但 buffer 代理仍不能完成严格面通量复测；因此机理链保持开放，论文不得写成“严格 B 已失败”或“边界能量语义整族已排除”。生产证据继续冻结。

| # | 任务 | 说明 | 依赖 |
|---|---|---|---|
| 1 | **用户决定是否授权 strict-B 实施** | 权威短版清单已完成；当前仍无代码、测试或 run 授权 | `strict_faceflux_candidate_b_design_v1.0.md` |
| 2 | **获授权后先做实现预注册** | 冻结剩余机器细节，依次过局部合同、基态、G0 admission、冷锚和完整 JVP；预注册先于热点 | 用户批准 |
| 3 | **收紧 Results I 机理段** | 保留 JAB2/NSF/wallfix/ghost 的已证范围；把 faceflux 写成 buffer 代理 null，并明写 strict-B 与科学 gate 尚开放 | 1；无需新增数据 |
| 4 | 完成 Fig. 3 与两项配套结果 | Fig. 3=LBM/QS/1D 趋势 + `R_dyn` + `U_gov` + TAN；Results II/III 维持一主两辅边界 | 3 |
| 5 | 补充材料与 related work | 诊断链溯源入 SI；“首次/普遍性”措辞继续受第二轮全文文献核查约束 | 机构权限 |

**可选、未立项**（是否投算力由用户决定，均不影响首投）：

- **strict-B 实施**——仅在用户批准设计与后续实施计划后启动；先过 code/cold/JVP 门，再决定是否发热点 auth。
- **反弹类家族趋势对照**——检验伪迹是否为湿节点family 特有（须先解决"非质量中性 vs 质量中性"的混淆变量，并验证误差因子的基态无关性，不能假设在比值中抵消）。

**不做**：A3/A2b/H3/30 kHz/频扫/有限宽/路线 A（投稿前不新增生产模拟的默认不变）。
