# docs/Phase_5

**定位**：Phase_5 热声薄膜有限温升非线性换能（非线性入口与生产合同）的阶段文档目录。
**维护原则**：新增、删除、移动或改变 Phase_5 文档职责时，同步更新本 README、`Phase5_STATUS.md` 和 `Phase5_Output_Files_Guide.md`。

## 1. 文件索引（现存）

| 路径 | 类型 | 作用 | 维护触发 |
|---|---|---|---|
| `Phase5_instruct_v1.2.md` | contract/frozen | Phase_5 唯一规范性入口与生产合同（v1.2，2026-07-20 WP0 冻结；评审基线=master `b86459c`）。范围、Gate 定义与阈值、算例矩阵、数据合同、声明规则的权威出处。 | 实质修改必须升级版本号并更新 `Phase5_STATUS.md`（合同 §0.1/§23）；禁止静默覆盖。 |
| `Phase5_STATUS.md` | status | **阶段状态（2026-08-14 瘦身，52.8k→10.7k 字符）**：状态标签 + Gate 现值追踪 + 执行流水（做了什么/为什么/结果）+ WP4 生产数据（论文数字唯一家）+ 决策记录 + 生效风险 + 下一步。**技术细节一律在对应报告**；历史留档见 `x/phase5_execution_history.md`。 | 阶段进度、Gate 状态、决策或交付物变化时更新；新增执行单元时在“执行流水”加一行（目的/结果/指针），不写技术细节。 |
| `Phase5_Output_Files_Guide.md` | output-guide | Phase_5 跨目录总览：配置/验证/后处理/参考求解器/运行产物的落位关系与归档约定。 | 新增报告、配置、脚本、测试、run 归档或目录结构变化时更新。 |
| `x/nonlinear_model_freeze.md` | gate-report/frozen | **G0-B 交付（2026-07-23）**：有效物性律冻结（表格口径：α_eff(T,k) 指数 1.0→5.4 随 k、k1 处 k_eff∝T^1.04、路径 LU 简并、各向同性）+ 三个下游输出（1D 挂接/WP1-3 归因/G2 逐 k 物性）。权威 run `20260722T173919Z` 的脚本判定为 `SCOPED_CANDIDATE`；用户已按 D5-2 升级为 `SCOPED_PASSED_BY_USER`，围栏见 STATUS。 | mapping/色散/滤波变化触发 §23 复验重跑。 |
| `M5_runs/`（已迁出） | run-archive | **2026-08-06 迁至 `archive/M5_runs/`**（用户口径：数据不住文档层）。权威/诊断 run 精选摘要归档（不含 h5），当前 28 项，覆盖 G0/G3/G1-W/G1a/G1b 失败谱系/G2/G4a/WP3/WP4/TAN/QS-1k/JAB/JAB2/NSF 仲裁/wallfix/ghost 扫描。 | 新权威 run 归档时在 `archive/README.md` 与本行计数同步。 |
| `x/route_ab_decision_memo.md` | decision-memo | **WP1-5 交付（2026-07-22）**：双物性 1D 消融 + 独立验证（§2.1）+ D-AB-2 逐 QoI 判定 + **用户决策已记录（§7：2026-07-22 批准维持 `ROUTE_B_MAIN + 1D_REAL_AIR_BOUNDING`，升级条件预注册）** + G0 挂接复核（§8）+ **G3 闭合追记（§9：分支正式定义 + p-side 上界口径）**。 | 升级条件触发时重开。 |
| `x/nonlinear_entry_gate_report.md` | gate-report | **G1a 交付（2026-07-28，§A）+ G1b `FAILED` 终判（2026-07-30，§B——密封无沉 rig 耦合回路结构性阻断，D5-4 回退已执行；证据 run 摘要归档 `M5_runs/g1b_failed_*/`）**：幅值包络九行认证 `PASSED`+`G1A_PASSED_TO_0P05`（生产矩阵解锁至 ε=0.075；ε=0.10 出能量包络=场形幅值依赖实测 §A.3；H2 阶梯 §A.4；细化双轴 §A.5——dx1p3 以 mn 壁 978 步实测判死）。权威 run `20260728T085824Z`（摘要归档 `M5_runs/g1a_20260728T085824Z/`）。 | 生产壁/谱修正/滤波/拟合器变更或 G0 α_eff 升版 → §23 复验。 |
| `x/wall_nonlinearity_neutrality_report.md` | gate-report | **G1-W 交付（2026-07-27）**：热壁中性认证 `PASSED`（§6.1 八行 + Stage-1 归因闭合 §2 + 夹具重设计谱系 §3.2）+ **生产壁认证（v1.1 对称质量中性壁）** + 旧壁 `DIAGNOSTIC_ONLY` + 矩通道重标定常数（§23）。权威 run `20260727T083342Z`（摘要归档 `M5_runs/g1w_20260727T083342Z/`；首次尝试 `20260727T040121Z` FAILED 谱系在案）。 | 壁模块/审计/拟合器行为变更或 G0 α_eff 表升版 → §23 复验重跑。 |
| `x/nonlinear_1d_reference_report.md` | gate-report | **G3 交付（2026-07-26）**：1D NSF 参考仪器认证 `PASSED`（§8.2 七行 + 密封绝热 ringdown 重设计与等温热沉伪影诊断 §3.1）+ 正式分支定义冻结（§2）+ p-side H2 复核与 A1 底板（§4）。权威 run `20260726T082938Z`（摘要归档 `M5_runs/g3_20260726T082938Z/`；首次尝试 `20260726T074420Z` FAILED 谱系在案）。 | physics-core（1D 求解器/拟合器）行为变更或 G0 实测律升版 → §23 复验重跑。 |
| `x/harmonic_transfer_report.md` | gate-report | **G2-T/G2-A 交付（2026-07-30）**：10/20 kHz 热生成与纯声学传递链均 `PASSED`；20 kHz 载体的 +5.67% 色散与约 +4%/跨度增益作为下游携带属性归档。 | 生产壁、G0 表、传播载体或读出链变化时按合同 §23 复验。 |
| `x/harmonic_operator_ablation_report.md` | gate-report | **G2-O 交付（2026-07-30）**：算子底板、滤波敏感性与结构恒等行认证 `PASSED`；`HARMONIC_CLAIM_LEVEL_L2_2F` 的算子侧条件闭合。 | 谱修正/滤波强度、次数或顺序变化时重跑 G2-O。 |
| `x/dc_protocol_report.md` | gate-report | **G4a 交付（2026-08-01）**：帐篷双带 canonical 热沉、状态匹配域高、QS 判读与耦合行认证；`DYNAMIC_NONLINEAR_RESIDUAL_IDENTIFIED`。G4b 保持 `NOT_RUN`。 | canonical 热沉、`H_s` 角色、耦合记账或生产壁变化时复验。 |
| `wp4_hot_basestate_jacobian_ablation_guide.md` | topical-guide | **机理诊断指导（2026-08-08 交付；已执行）**：规定完整热基态矩阵无关切线、TAN 身份验证、A0–A6 粗细消融、判读与停止条件。用户 2026-08-08 授权执行，结果见 `wp4_jacobian_ablation_report.md`；规范原文冻结不回改。 | 切线接口/消融矩阵变化或第二轮（细粒度/趋势复核）授权时更新。 |
| `WP4_JAB_next_simulation_guide_simple.md` | topical-plan | **JAB 第二轮计划（PLAN_v1.1；已执行）**：A2 五子项+A3 四子项细粒度定位、冻结判读线与分类路由。权威 run `20260810T144425Z`：**A2=单项 A2-5（内能重钉扎）、A3=两族抵消束、路由 LBM 边界方法学**——结果唯一家=`wp4_jacobian_ablation_report.md` §7。 | 第三轮（边界方案复测/NSF 仲裁）授权时更新。 |
| `wp4_jacobian_ablation_report.md` | gate-report 族（诊断单元） | **WP4-JAB 权威结果（2026-08-09/10，run `20260809T195359Z` `COMPLETED`）**：V0–V5 全过（V4 身份门偏差 −0.000pp）；**`JAB_COUPLED_CANDIDATE_A2_A3`**——带重构 × 宏观/平衡两块热基态导数近可加承载全部工作点响应（双冻结后 d_OP=+0.006%/+0.020%），应力/热流/streaming/滤波/声学族实测排除。 | 第二轮消融、趋势复核或归档执行时更新。 |
| `NSF_hot_basestate_tangent_arbitration_plan_v1.0.md` | topical-plan | **连续 NSF 热基态切线仲裁计划（PLAN_v1.0，用户 2026-08-11 下达；已执行）**：真实热基态+完整梯度耦合的连续定温壁 NSF 频域切线，判定 LBM 负工作点趋势属连续物理还是热壁边界实现效应；full/no-gradient 模型对 + §9 判决树。结果唯一家=`NSF_hot_basestate_tangent_arbitration_report.md`。 | 后续轮（改进边界方案复测等）授权时更新。 |
| `NSF_hot_basestate_tangent_arbitration_report.md` | gate-report 族（诊断单元） | **NSF 仲裁权威结果（2026-08-11，run `20260811T055850Z` `COMPLETED`）**：V1–V7 全过（g0/physical 分支 BVP 切线与归档 DC 臂 raw 系列四位一致 ~1e-4 pp）；**LBM-equivalent 介质=情况 A/D（+1.18%/+2.34% 为正）；梯度动态耦合仅 −0.26/−0.51 pp（三分支一致，≈LBM 动力学残差的 5%）；常数输运分支情况 B 字面触发=静态分层系数效应（非动态机制）**——维持并强化 `ROUTE_LBM_BOUNDARY`，thermophone finite-bias physics 不重开。 | 改进边界方案复测或输运分支口径变化时更新。 |
| `wallfix_a2a5_counterproof_report.md` | gate-report 族（诊断单元） | **A2-5 修复性反证权威结果（2026-08-11，run `20260811T085347Z_auth` `COMPLETED`）**：结构论证（四不变量锁死壁切线标量通道）+合法族实测穷举——**`WALLFIX_FAMILY_NULL`：合法壁修改全体 \|S\|≤1.1e-6 pp vs 非法 A2-5 消融 +8.82 pp（7 个量级）；A2-5 异常=湿节点重钉扎范式结构性质，修复入口=放宽行钉扎语义（未立项）**。PROD 身份门 1e-5 pp 级复现 TAN。 | 面/通量一致钉扎单元立项或范式变更时更新。 |
| `ghost_relax_scan_report.md` | gate-report 族（诊断单元） | **ghost 自由弛豫参数扫描权威结果（2026-08-13/14，B 机双向 run `20260813T100957Z` / `20260813T194351Z` 均 `COMPLETED`）**：回答文献核查暴露的审稿线"离散效应传统的标准补救=调 ghost 自由弛豫参数，你们试过吗"。**双向失败**——τ>1 加重伪迹且 τ≥1.08 失稳；τ<1 方向正确但格式先失稳，外推穿越点 τ≈0.967 在崩溃区且需 −28% 冷态导纳代价。锚点 `fourth_order@τ=1.0` 复现 TAN 0.005/0.009 pp。使 `WALLFIX_FAMILY_NULL` 适用面扩至碰撞侧。 | 阶梯、闭合分支或判读线变化时更新。 |
| `crossstack_1a_plan_v1.0.md` | 计划书（诊断单元） | **跨栈普遍性单元 1a 立项计划（PLAN_v1.0，2026-08-14 用户下达）**：碰撞算子结构轴；自足执行入口；已核实两点=仓库无 BGK 但自写成本 2–4 天、开源生态无可用热力学自洽对照栈（勿重复调研）。判读线、分类、BGK 失稳回退路径在此冻结。 | 结果落地后只在计划变更时更新。 |
| `crossstack_collision_report.md` | gate-report 族（诊断单元） | **跨栈单元 1a 权威结果（2026-08-14；REPORT_v0.9=BGK 轴闭合、CFG 轴 auth 运行中）**：回答"这是普遍陷阱还是你们碰撞算子的特性"。**BGK 轴=生产工作点上无条件线性失稳**（无壁周期箱谱半径 1.46–2.02 vs 生产 1.000000；保 α 的整个可行区间无一稳定；只有退化为完全正则化极限才稳而那里 α 已 3.4×）→ 计划书 §3 回退路径 1 触发。CFG 轴（`deviatoric_stress_policy` / `trace_bulk_policy` / 组合 / 惰性对照）待 auth。 | auth 落地升 v1.0；1b/1c 立项时更新。 |
| `crossstack_1a_plan_v1.0.md` | topical-plan | **跨栈普遍性单元 1a 立项计划（2026-08-14，PLAN_v1.0，待执行）**：投稿适配评估暴露"只在自己一套栈上测过"是最大接受风险，本单元换碰撞算子结构轴复测伪迹。**已核实：仓库无 BGK/标准 MRT，只有 SMRT/RR**，故分层为 1a-1（配置轴 `deviatoric_stress_policy` / `trace_bulk_policy`，本次范围，1.5–2 天）/ 1a-2（D2Q21 点阵轴，条件）/ 1a-3（新写 BGK，不在本次范围）。判读线与活键门已冻结于计划。结果报告落 `crossstack_collision_report.md`（新建，勿并入他文）。 | 执行后更新执行状态并加结果报告行。 |
| `x/phase5_execution_history.md` | history-archive | **STATUS 瘦身移出的历史留档（2026-08-14）**：WP0/WP1 逐项交付与验证表原文、已闭合/已解除风险行原文、原始更新日志全文（2026-07-20→08-14）。日常只读 `Phase5_STATUS.md`；需要历史细节时来此。只读，不再增补。 | STATUS 再次瘦身时追加。 |
| `x/wp3_go_nogo_decision.md` | decision-material | **WP3 已启动（D5-5，2026-08-02）**：八信息单元学分记账、A1/P-DC2/P-1D 预注册与 §14.1 对照模板；权威 run 与最终用户决策待完成。 | WP3 权威 run、GO 条件或用户决策变化时更新。 |

## 2. 合同规划交付物（尚未创建；落地时移入上表）

按合同 §13/§17，当前只剩以下规划文档尚未落地，不得引用为已交付：

| 规划路径 | 归属 |
|---|---|
| `nonlinear_production_report.md` | WP4 |

合同 §17 树中另列 `论文一创新点评审与修订实施方案.md`（合同的上游评审文档），未随库提供；如需入库由用户提供原件。

## 3. 使用入口

- 主要入口：`docs/Phase_5/Phase5_instruct_v1.2.md`
- 阶段状态：`docs/Phase_5/Phase5_STATUS.md`
- 论文架构（跨目录、按用户要求不入库）：`Manuscript/Paper1_Manuscript_Architecture.md`（`ARCHITECTURE_v0.3`；一主两辅、5 节、5 图）
- WP3 决策材料：`docs/Phase_5/x/wp3_go_nogo_decision.md`
- 机理诊断指导与结果：`wp4_hot_basestate_jacobian_ablation_guide.md`（规范）+ `wp4_jacobian_ablation_report.md`（权威结果，`JAB_COUPLED_CANDIDATE_A2_A3`）
- Gate schema（机器可读）：`verification/nonlinear/phase5_gate_schema.json`
- 配置目录规范：`configs/phase5/README.md`
- 继承授权与硬约束：`docs/Phase_3/M3/M3_Closure_Decision.md` §3/§4
- 全局上下文：`docs/PROJECT_CONTEXT.md`

## 4. 边界

- **WP2 入口 Gate 序列、WP3 八信息单元和 D5-6 授权的 WP4 认证子矩阵均已完成（2026-08-04）**；其中 G1b 保持 `FAILED`，其顺延的 canonical 有沉耦合问题已在 G4a 单点闭合。当前进入论文写作轨，仍为 `FINAL_PRODUCTION_NOT_CLAIMED`。
- 所有 Phase_5 产出携带继承边界：M3 `SCOPED_ACCEPTED`（幅值 ±5.4%、单频 10 kHz、dx2p6 不换 dx/tau）；M4 `PASSED_WITH_SCOPED_RISK`（非 clear PASS）。
- 生产壁仅为 v1.1 对称质量中性壁；`pressure_preserving` 旧壁只作诊断。G2-T/A/O 已支持 L2-2f，H3/30 kHz 仍为未触发条件项，L3 远场谐波不在基础范围。
- 脚本与报告只能产出 `PASSED/FAILED/SCOPED_CANDIDATE`；`SCOPED_PASSED_BY_USER` 与路线 A 启动均属用户决策。冻结合同中的 PRA 升级路线保留为历史范围设计，但当前毕业导向稿件不启动该扩项。
- 原始运行产物默认留在 `results/phase5/<族>/<run_id>/`（不入库）；只有精选摘要进入本目录（归档约定见 `Phase5_Output_Files_Guide.md`）。
