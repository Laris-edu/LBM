# Phase_5 阶段状态

**阶段**：Phase_5 — 热声薄膜有限温升非线性换能（Nonlinear Entry and Production Contract）
**合同**：`docs/Phase_5/Phase5_instruct_v1.2.md`（v1.2，2026-07-20 经 WP0 冻结为唯一规范性入口；评审基线 `b86459c`）
**最后更新**：2026-08-20（三单元同日闭合——偏置判别 `OFFSET_BEYOND_CONTINUUM`：等质量 Θ 偏置为超连续动理学残差（质量平坦、换本构无机制消除；家=`a2asb_offset_lenses_report.md`）；另两单元：① `A2a-STRICT_B` 判决 run `20260819T155402Z`——四点 d_OP 仍负、上移 +0.13→+0.57 pp、C_R≈0.48，机械候选=`NOT_RESOLVED_CANDIDATE`，**四级判决与 G0 围栏待用户**（家=`a2a_strict_b_report.md`）；② 用户指令**系综轴扫描** `20260819T193831Z`——`ENSEMBLE_AXIS_PARTIAL`：质量系综=原框架负趋势主承载（斜率 0.956/0.959 pp/%、盈余点符号翻正、等质量点与切线锚 0.006–0.007 pp 和解），连续静态族自带 ~55.5% 质量斜率→异常改述为"密度超额响应 1.80×连续 + 随 Θ 偏置 + 次要边界项 ~11%"（家=`a2asb_ensemble_scan_report.md`）。既有 strict-B 科学资格未授予、分类不激活、`D1_SCIENTIFIC_GATE_OPEN`、Gate、生产壁与 `FINAL_PRODUCTION_NOT_CLAIMED` 均不变。）

**本文职责**：状态标签 + Gate 现值 + 执行流水（做了什么 / 为什么 / 结果）+ WP4 生产数据。
**本文不写**：技术细节、推导、诊断链——一律在对应报告，本文只给结论与指针。
**历史细节**（WP0/WP1 逐项交付表、已闭合风险原文、原始更新日志全文）：`x/phase5_execution_history.md`。

---

## 1. 当前状态

**WP0–WP4 授权范围全部完成**（2026-08-04）。2026-08-08 起的机理诊断序列已形成 G4a→TAN→JAB/JAB2→NSF→wallfix→ghost→跨栈 1a→D1-B buffer→strict-B 的证据链。strict-B 权威执行链与 `strict_b_report.md` `REPORT_v1.0` 已登记，但科学资格戳未授予、热点分类不激活。2026-08-18 用户以 D5-8 将 Paper 1 改为**有限热偏置 thermal-LBM 边界方法学条件架构**；2026-08-19 D5-9 冻结 A2a-STRICT_B 原协议复测方案，同日用户授权实施与运行，**判决 run 已完成（B 机 `20260819T155402Z`，合法性全绿）：机械候选=`NOT_RESOLVED_CANDIDATE`，正式四级判决与 G0 围栏语义待用户（数据唯一家=`a2a_strict_b_report.md`）**。上述变化不改变任何 Gate 与 `FINAL_PRODUCTION_NOT_CLAIMED`。

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
STRICT_B_IMPLEMENTED（六资产+16 项合同+权威执行链，2026-08-19）
STRICT_B_VALIDATION_STAMP_NOT_GRANTED（前八层未全绿：壁位/系综 Θ_DC/uniform 漂移/G0 admission 四行 FAIL，均有独立归因，见 strict_b_report §4.4/§4.5）
STRICT_B_HOT_ARCHIVED_PARTIAL_CONTROL_DIRECTION_EVIDENCE（热点分类不激活；CONST_G m=0.581/0.589 与 G0 archived m=0.653/0.662 双行方向证据）
D1_SCIENTIFIC_GATE_OPEN
A2A_STRICT_B_DATA_REGISTERED_JUDGEMENT_PENDING（判决 run `20260819T155402Z` 合法性全绿；机械候选=NOT_RESOLVED_CANDIDATE；四级判决与 G0 围栏语义=用户专属）
ENSEMBLE_AXIS_PARTIAL（系综轴扫描 `20260819T193831Z`：质量系综主承载实锤+切线框架和解；静态平坦前提否定→密度超额响应 1.80× 表述；不改判决归属）
OFFSET_BEYOND_CONTINUUM（偏置判别 `20260820T073200Z`：四静态透镜+完整 NSF 格子本构动力学均不复现等质量偏置——格子透镜下残差质量平坦 −2.6~−3.0/−5.0~−5.9 pp、随 Θ 线性=超连续动理学项；换本构无机制消除；方向线索=近壁 3 格动理学层）
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
| 2026-08-20 | **投稿前文献核查第三轮（本构框架；与偏置判别并行，后台代理执行）** | 核查本构根因定位的三个断言（用户点破前轮"没人量化过"为臆想后的补课） | ① 变弛豫 τ(T,ρ)=成熟标准做法 **FOUND**（Nie/Doolen/Chen 2002 给出 τ(ρ) 处方；**D2Q37 直系 Scagliarini 2010 源头论文自己写出 k=c_p·T̄·ρ·(τ−Δt/2)**——k∝ρ 不可作为发现声明）；② 常数 τ 误差定量刻画 **PARTIAL**：Nu/流场量级层 FOUND（Zhang&Cao 2011 与 VPLBFS 族），**符号级/响应导数/传递函数级 NOT_FOUND**（8 条 0 命中检索式在案）；③ 热声 LBM 应用 18+2 篇全枚举：变 τ 处理与输运归因的验证偏差报告 NOT_FOUND，thermophone×LBM 空白复核仍成立。**定位结论=情形 2（量级→符号级推进）为主张主体 + 情形 1（导纳观测量与应用侧空白）；全部"首次"带检索范围限定语**。局限：Scopus/SD 未挂载、全文库核查为第二轮待办 | 唯一家=`literature_check_constitutive_v1.md`（CHECK_v1；49 条 OpenAlex 检索式 + 3 篇 arXiv 全文 grep 在案） |
| 2026-08-20 | **偏置判别单元（offset lenses；用户"并行做吧"，与本构文献核查并行；D0-7 诊断，零 LBM 算力）** | 判定系综扫描剩余的等质量 Θ 偏置（wet 负趋势 ~58%）是格子本构的动力学表达还是超连续真残差——直接决定"换真实态本构负趋势是否消失" | 预注册 `6290cab`（QS 四透镜 L0/L1/L1b/L2 + NSF 格子本构通道 δk=1.04(k/T)T̂+(k/p̄)p̂，默认关闭位级惰性；输入=系综扫描 digest 钉定；34 合同测试绿）。判决 run A 机 `20260820T073200Z`：**`OFFSET_BEYOND_CONTINUUM`**——四静态透镜全部 \|R(eq)\|≥1.65 pp；NSF 完整动力学+格子本构反而更正（+2.38/+4.75% vs 实测 −0.21/−0.24%，距 +2.6/+5.0 pp）；**格子透镜下残差质量平坦（斜率 −0.07 pp/%）**。三层最终分账（报告 §3）：边界 ~11% + 本构质量轴（已闭合，参照随质量动）+ **超连续动理学残差 −2.6~−3.0/−5.0~−5.9 pp（最大单项，质量平坦、Θ 线性；方向线索=近壁 3 格动理学层，与 strict 壁位 FAIL 同层）**。换 τ(ρ) 本构只有机制消第 2 层。仪器自洽：NSF 锚复现至 4 位小数、L0 对扫描 2.5e-11 | 数据唯一家=`a2asb_offset_lenses_report.md` REPORT_v1.0；归档=`archive/M5_runs/a2asb_offlens_20260820_A/` |
| 2026-08-20 | **系综轴扫描（用户指令"执行系综轴扫描"当日闭合；D0-7 诊断）** | 边界固定 strict-B 只扫基态列质量，判别原框架负趋势主承载并验证两轴分解 | 预注册 `632652f` 先于热数值；B 机判决 run `20260819T193831Z`（94.9 min；wet 点/冷锚从判决 run checkpoint **位级复用零新算力**，新算 6 settle+6 drive；全点 legal）。**`ENSEMBLE_AXIS_PARTIAL`**：五点线性残差 0.0012 pp（span 的 0.03%）、斜率 **0.9556/0.9593 pp/%**（跨 Θ 比 1.0038）、**盈余质量符号翻正**（+1.21%→d_OP=+0.95%）、**等质量点与切线锚和解 0.0072/0.0060 pp**（两轴分解升级为同框架事实）；静态平坦门败=新信息：同系综连续 QS-1 自带 ~55.5% 质量斜率（六点常数）→ 异常改述为**密度超额响应 1.80×连续 + 质量无关随 Θ 偏置（−1.65/−3.12 pp）+ 次要边界项 ~11%**；完整解剖闭合 0.002 pp（报告 §3 表） | 数据唯一家=`a2asb_ensemble_scan_report.md` REPORT_v1.0；归档=`archive/M5_runs/a2asb_ensscan_20260820_B/` |
| 2026-08-19/20 | **A2a-STRICT_B 实施 + 判决 run 闭合（用户当日授权；判决权保留用户）** | 执行 D5-9 方案：单一边界替换下重跑 A2a 时域增量响应，回答"负工作点趋势是否随湿节点边界替换消失" | 仪器预注册 `237e810` + 判读线可测性修正 `596bcdb`/`d498eed`（步进零改动）；wet reference pack `1117736`（五重放位级一致、R_dyn^wet 舍入=冻结值、21 源文件 SHA-256）；smoke 两轮逐位复现；**判决 run B 机 `20260819T155402Z`（105 min，14 算例零死亡，合法性 11/11 全绿，冷锚 3.87%/3.87° PASS 且与切线冷锚 ~1e-5 相对吻合）**。结果：四点 d_OP 仍负 **−1.0469/−2.5208/−3.6632/−4.7396%**（保留 wet 幅值 ~89%）、上移一致 **+0.126/+0.305/+0.442/+0.570 pp**（全过 0.1 pp 门）、R_dyn=−1.11/−2.68/−3.91/−5.07 pp、**C_R⁻=0.460/0.476/0.482/0.487 恰低于冻结 0.5 线**、strict QS-1k 仍正号（+2.4→+12.5%）；机械候选=`NOT_RESOLVED_CANDIDATE`。**正式四级判决与 G0 围栏语义待用户**；框架对照守卫（切线等质量框架数字不可转写到本原协议框架）=报告 §5.4 | 数据唯一家=`a2a_strict_b_report.md` REPORT_v1.0；归档=`archive/M5_runs/a2asb_20260819_B/`+镜像 `results/mirror_from_B/a2a_strict_b/`；pack=`archive/a2a_strict_b/` |
| 2026-08-19 | **A2a-STRICT_B 原协议复测方案冻结（D5-9）** | 在非均匀 DC 基态上重跑 A2a 时域增量响应，以单一边界替换检验 strict-B 是否消除负趋势 | `PLAN_v1.0` 已冻结；工况=`Θ_DC {0,0.02,0.05,0.075,0.10} × ε_AC {0.005,0.02}`，重新计算 QS-0/QS-1/QS-1k 与动态残差。**方案交付本身不含授权；实施/运行授权与判决保留见上行** | `a2a_strict_b_experiment_plan_v1.0.md` |
| 2026-08-19 | **strict-B 权威执行链落盘（正式登记行）** | 完成设计九层验证矩阵与热点判决，回答"删除 band 行+严格面通量后负趋势是否仍在" | **机器精度级 PASS**：拓扑（P+S≡显式 BB 位级、覆盖 15/8/3）、守恒（Bq 恒等 ~1e-16）、冷锚（−3.87%/−3.87° vs 冻结 PROD 复锚）、micro/full JVP（odd 1.2e-10、even 比 4.0000、identity 1e-10 三档判决几何）、回归（333×3 轮+金样位级）。**FAIL（各有独立归因，留档语义）**：壁位 0.928%@N64（近壁 3 格动理学层 c/N，门 1e-3 需 N≈600）、系综 Θ_DC 1.33-1.48%（外推口径极限）、uniform 漂移 1.23e-11（3.27M 步浮点底噪，与 perturbed 逐位同幅=非物理）、G0 admission（面一致性 2.03% PASS，但幂律指数 2.04 vs 1.04 与 AC N64 +15-19%/+11-14° 被冻结介质低 k 色散挡住——G0-B 围栏原文）。**热点（archived，分类不激活）**：PROD 锚复验偏差 1.1e-5/2.4e-5 pp；CONST_G −0.5012/−0.8038 pp（m=0.581/0.589）；G0 −0.2132/−0.2467 pp（m=0.653/0.662）——**负趋势 ~58-66% 随 band 删除消失、残余仍负**；`STRICT_B_SCIENTIFICALLY_VALIDATED` 未授予，是否 scoped 采纳方向证据待用户 | `strict_b_report.md` REPORT_v1.0；判决 run `20260818T201520Z_auth`（A 机；hotdc soak=B 机 checkpoint 转移，D5-3）；归档 `archive/M5_runs/strictb_20260818_A/`；预注册 `d036e74`→语义修正 `929884a`/`18aa0ef`/`8556649` |
| 2026-08-18 | **Paper 1 方法学架构重建（D5-8）** | 将论文中心从 thermophone 模型差异与器件背景转为有限热偏置 thermal-LBM 边界的诊断、反证和条件面通量修复 | canonical=`ARCHITECTURE_v1.0_METHODS_CONDITIONAL`；固定 7 节、C1–C6、strict-B 三层门、6 图/1 表及成功/回退模板；thermophone 降为 benchmark，A1/A5 退出本稿。v0.3 逐字节归档；不新增模拟、不改 Gate/生产状态 | `Manuscript/Paper1_Manuscript_Architecture.md`；历史归档 `Paper1_Manuscript_Architecture_v0.3_OBSOLETE.md` |
| 2026-08-17 | **D1 strict-B 实验执行清单（设计冻结节点）** | 把 D1 §9.1 的零体积 ghost/删除 band 要求落实为可实现、可证伪的最短实验合同 | 当时冻结 88 行设计与 `D1_SCIENTIFIC_GATE_OPEN`；后续实施资产现值见 2026-08-18 行，不能继续引用本历史节点为“未实施” | `strict_faceflux_candidate_b_design_v1.0.md` |
| 2026-08-17 | **D1-B buffer 面通量代理实测** | 检查共享 buffer 骨架内移除显式 `c_vρ̄δθ_w` 零阶储能源是否足以移动 d_OP | **`D1_B_BUFFER_DIAGNOSTIC_NULL / D1_BUDGET_PARTIAL`**：d_OP=−2.8078/−5.2788，对生产仅 +0.0268/+0.0383 pp；冷复比幅值 −2.446% 命中预算、相位 −3.959° 未命中。实现保留有限体积共享 band，且只跑单 h，故不能裁决严格 B、§13.2、纯气侧响应或能量语义 family | `faceflux_wall_report.md` REPORT_v1.1；A 机 `20260817T090753Z_full`；归档 `M5_runs/faceflux_20260817_A/` |
| 2026-08-14 | **跨栈单元 1a（碰撞算子结构轴）** | 补投稿最大缺口："只在自己一套栈上测过"——换碰撞算子复测伪迹是否仍在 | **两轴均闭合。① BGK 轴**：自写诊断 BGK（(τ_f,τ_g) 由冻结 mapping 导出，ν/α 与生产逐位相同）在**无壁周期箱**上谱半径 1.46–2.02（生产 1.000000）——**保 α 的整个可行区间无一稳定**，判决网格三个工作点 settle 全死 → 计划书 §3 回退路径 1 触发。**② CFG 轴 `CROSSSTACK_FAMILY_ROBUST`**：唯一有实质杠杆的存活开关 `DEVMEAS`（剪切 ν_eff ×4）只把 d_OP 推动连续参照缺口的 **10.5%**（−2.8345→−2.4121 / −5.3171→−4.5194 pp），符号不变；PROD 锚点复现 TAN **1.3e-05/2.5e-05 pp** | `crossstack_collision_report.md`（REPORT_v1.0）；`crossstack_1a_plan_v1.0.md`；B 机权威 `20260814T090824Z_full`（归档 `M5_runs/crossstack_1a_20260814_B/`）+ A 机 `20260814T090438Z_preflight` / `20260814T092631Z_smoke` |
| 2026-08-13/14 | **ghost 自由弛豫参数扫描** | 回答文献核查暴露的审稿线："离散效应传统的标准补救=调 ghost 自由弛豫参数，你们试过吗" | **双向失败**：τ>1 使伪迹加重且 τ≥1.08 失稳；τ<1 方向正确但仅 τ≥0.99 合法、外推穿越点 τ≈0.967 落在崩溃区且需 −28% 冷态导纳代价。锚点复现 TAN 0.005/0.009 pp | `ghost_relax_scan_report.md`；B 机 `20260813T100957Z` / `20260813T194351Z` |
| 2026-08-11/14 | **投稿前文献核查（第一轮）** | 核实"边界家族被广泛使用"与 novelty 关口 | 家族普遍性**坐实**（Guo 2002 被引 733、JCP 2012 被引 204）；novelty 未被证伪（含 1184 篇施引文献追踪）；**LBM×thermophone 空白**；定位升级为"标准补救可证明失效的首例" | `literature_check_wallfix_novelty_v1.md` |
| 2026-08-11 | **A2-5 修复性反证（wallfix）** | 检验能否用有原则的边界修正消除 A2-5 异常，同时不破坏既有认证 | **`WALLFIX_FAMILY_NULL`**：四不变量内合法壁族全体位移 ≤1.1e-6 pp（对照非法消融 +8.82 pp，差 7 个量级）→ 异常是**湿节点逐步重钉扎范式的结构性质**，范式内不可修 | `wallfix_a2a5_counterproof_report.md`；`20260811T085347Z_auth` |
| 2026-08-11 | **NSF 热基态切线仲裁** | 判定负工作点趋势属连续热声物理还是 LBM 热壁边界效应 | LBM-equivalent 介质**情况 A/D 为正**（+1.18/+2.34%）；两个基态梯度动态耦合项仅 −0.26/−0.51 pp（≈残差 5%）→ 连续 NSF 造不出该负号；维持生产算子 `ROUTE_LBM_BOUNDARY` 簿记路线，**不是 strict-B 因果闭合** | `NSF_hot_basestate_tangent_arbitration_report.md`；`20260811T055850Z` |
| 2026-08-10 | **JAB2 第二轮细粒度定位** | 把 JAB 定位的 A2/A3 两块拆解到子项 | **A2 整块=单项 A2-5**（壁面内能目标与 g 重钉扎的基态密度敏感度，σ=1.000 两点）；A3=两族抵消束 `A3_DISTRIBUTED`；冻结路由 **`ROUTE_LBM_BOUNDARY`** | `wp4_jacobian_ablation_report.md` §7；云端 96 核 `20260810T144425Z` |
| 2026-08-09/10 | **WP4-JAB 热基态 Jacobian 消融** | 定位负趋势的 LBM 内部来源（算子块级） | **`JAB_COUPLED_CANDIDATE_A2_A3`**：v1.1 带重构 × 宏观/平衡两块近可加承载全部工作点响应；应力/热流/streaming/滤波/声学族排除 | 同上；`20260809T195359Z` |
| 2026-08-06/08 | 数据层与文档层重整 | 数据不该住在文档层；入口文档瘦身 | `M5_runs`/`M2_runs` 迁入 `archive/`；`PROJECT_CONTEXT` 361→199 行；四层数据边界确立 | `archive/README.md`；历史日志 |
| 2026-08-06 | **论文架构 v0.3（历史）** | 毕业导向收缩 | 一主两辅、5 节 5 图；Results I 为唯一中心；2026-08-18 被 D5-8 废止 | `Manuscript/Paper1_Manuscript_Architecture_v0.3_OBSOLETE.md` |
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

### 3.1 A2a 工作点地图（有限偏置诊断主锚；A 机谱系，commit `fefee6b`）

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

### 3.3 A1 幅值阶梯（项目证据；D5-8 后不进入 Paper 1；B 机 `20260803T113507Z`，digest `194ff1249fe6`）

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

### 3.4 A5 χ 地图（项目证据；D5-8 后不进入 Paper 1；A 机 `20260804T002154Z`，10/10 稳定）

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
| D5-9 | 2026-08-19 | 冻结 `A2a-STRICT_B` 原协议复测方案：保持 A2a 工况/读出，只替换 strict-B 面边界，并与重新计算的 QS 静态族对照；本决策不授权实现或运行 | 用户 |
| D5-8 | 2026-08-18 | Paper 1 采用 `ARCHITECTURE_v1.0_METHODS_CONDITIONAL`：通用计算方法学核心；thermophone 只作诊断 benchmark；A1/H2、A5、远场声学与效率退出本稿；strict-B 正式终判后激活成功/回退分支 | 用户 |
| D5-7 | 2026-08-17 | 先冻结 strict-B 短版实验执行清单；同日后续授权实施。该授权不预判科学资格、热点分类或生产替换 | 用户 |
| D5-6 | 2026-08-03 | WP3 判定 **`SCOPED_GO`**，启动 WP4；授权范围=A2a/A1/A5 认证子矩阵（A3/A2b/H3/F1 不在授权内） | 用户 |
| D5-5 | 2026-08-02 | 启动 WP3 首轮八信息单元 | 用户 |
| D5-4 | 2026-07-29/30 | G1b 批准第四耦合设计 → 预注册回退条款触发并执行（耦合顺延 G4a） | 用户 |
| D5-3 | 2026-07-29 | 跨机口径**「每机逐位、跨机容差」**；权威 run 记机器指纹 | 用户 |
| D5-2 | 2026-07-23 | G0-B `SCOPED_CANDIDATE` → **`SCOPED_PASSED_BY_USER`**（围栏：剪切 ν 不认证 + 低波数表格口径） | 用户 |
| D5-1 | 2026-07-22 | 路线决策：维持 **`ROUTE_B_MAIN + 1D_REAL_AIR_BOUNDING`**（升级条件预注册） | 用户 |
| D5-0 | 2026-07-20 | **Phase_5 立项**，采纳合同 v1.2；Phase_4 转维护态 | 用户 |

决策全文与依据：`Manuscript/Paper1_Manuscript_Architecture.md`（D5-8）、`x/wp3_go_nogo_decision.md` §7（D5-6）、`x/route_ab_decision_memo.md` §7（D5-1）、`x/nonlinear_entry_gate_report.md` §B（D5-4）、`scripts/README.md`（D5-3 详录）。
预授权口径（无需再决策）：路线 A 启动、scoped 升级、`SCOPED_GO`、PRA 升级、完整 G5 均属**用户专属决策**，脚本与报告不得自动作出。

---

## 5. 生效中的风险与边界

- **继承硬约束**：单频 10 kHz、dx2p6 mapping，不换 dx/dt/tau/热流导出因子/Grad 壁重构（M3 决策 §3；触发即走停放项重启流程）。
- **热壁边界**：生产壁=v1.1 对称质量中性壁（已认证）；旧壁 `pressure_preserving` 为 `DIAGNOSTIC_ONLY`。A2-5 已证明是**四不变量湿节点整格胞重钉扎范式内**的结构性质；buffer 代理没有离开共享有限体积行，不能把该结论外推到 strict-B。strict-B 权威执行链已登记，但现值仍为科学资格戳未授予、热点分类不激活；D5-9 仅冻结 A2a-STRICT_B 复测方案。任何生产化仍须另过 G1-W 级重认证。
- **Paper 1 条件门**：报告草稿、运行目录或局部热点不得激活论文分支。只有本文件正式登记 `STRICT_B_SCIENTIFICALLY_VALIDATED` 后才读取 `RESOLVED/SIGN_FLIPPED/PARTIAL/NULL/MIXED`；前置合法性失败时不解释热点，合法 `NULL` 也只约束该 micro-closure。A1/H2、A5 数据继续作为项目证据保留，但不进入 Paper 1 正文/SI。
- **算子消融纪律**：禁止按结果挑"更好看"的算子栈；诊断用的 `fourth_order`/τ≠1 各行**无生产有效性声明**。
- **规划非承诺**：合同附录 E 工期为非规范性估计；禁用"N 算例 M 周"式高置信承诺。
- **`results/phase5/` 不入库**；权威 run 精选摘要归档见 `Phase5_Output_Files_Guide.md`（当前 `archive/M5_runs/` 30 项）。
- 已闭合/已解除的风险行原文见 `x/phase5_execution_history.md` §B。

---

## 6. 下一步（Paper 1 方法学写作轨；生产证据冻结）

**A2a-STRICT_B 判决 run 已完成（2026-08-19/20，数据登记于 `a2a_strict_b_report.md`）。** 判决权与 G0 围栏语义保留用户：机械候选=`NOT_RESOLVED_CANDIDATE`（合法性全绿、上移四点全过、C_R⁻ 0.476/0.487<0.5），正式四级判决由用户按方案 §4 裁决后登记于本文件。既有 strict-B 四项 SCOPED 裁决仍待用户，未被本单元静默清偿；生产证据继续冻结。

| # | 任务 | 说明 | 依赖 |
|---|---|---|---|
| 1 | **用户裁决 A2a-STRICT_B 结果** | 决定 G0 围栏 scoped 放行与四级判决（照判 NOT_RESOLVED / 另行 scoped 裁决均属用户）；裁决时可并读系综轴扫描的机制细化（质量主承载+1.80× 超额响应）；登记本文件后 Paper 1 Section 5 方可读取 | `a2a_strict_b_report.md` §6；`a2asb_ensemble_scan_report.md` §4；方案 §4 |
| 2 | **完成 C1–C4 与 Section 2–4 初稿** | 现象→TAN→JAB/JAB2→NSF→wallfix/ghost/collision→面通量修复要求；不依赖新 run | 新架构 v1.0 |
| 3 | **用户四项 SCOPED 裁决** | 既有 strict-B 报告的四项冲突清单仍独立待决；任何升级只能由用户批准并留档 | `strict_b_report.md` REPORT_v1.0 |
| 4 | **按正式证据激活 Section 5/Fig. 6** | 合并本 STATUS 正式 strict-B 状态与未来 A2a-STRICT_B 判决；当前仍不得升级论文主张 | 1、3 |
| 5 | **终判后选刊、压缩与补充材料** | 诊断链溯源入 SI；“首次/普遍性”措辞继续受全文文献核查约束 | 4 |

**不纳入 Paper 1**：A1/H2、A5、远场声学、器件效率、A3/A2b/H3/30 kHz/频扫/有限宽/路线 A；数据不删除，可供未来稿件使用。
