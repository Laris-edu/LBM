# docs/Phase_5

**定位**：Phase_5 热声薄膜有限温升非线性换能（非线性入口与生产合同）的阶段文档目录。
**维护原则**：新增、删除、移动或改变 Phase_5 文档职责时，同步更新本 README、`Phase5_STATUS.md` 和 `Phase5_Output_Files_Guide.md`。

## 1. 文件索引（现存）

| 路径 | 类型 | 作用 | 维护触发 |
|---|---|---|---|
| `Phase5_instruct_v1.2.md` | contract/frozen | Phase_5 唯一规范性入口与生产合同（v1.2，2026-07-20 WP0 冻结；评审基线=master `b86459c`）。范围、Gate 定义与阈值、算例矩阵、数据合同、声明规则的权威出处。 | 实质修改必须升级版本号并更新 `Phase5_STATUS.md`（合同 §0.1/§23）；禁止静默覆盖。 |
| `Phase5_STATUS.md` | status | Phase_5 当前状态、状态标签与 Gate 现值追踪、决策记录（含范围对齐）、验证记录、风险、下一步与更新日志。 | 阶段进度、Gate 状态、决策或交付物变化时更新。 |
| `Phase5_Output_Files_Guide.md` | output-guide | Phase_5 跨目录总览：配置/验证/后处理/参考求解器/运行产物的落位关系与归档约定。 | 新增报告、配置、脚本、测试、run 归档或目录结构变化时更新。 |
| `nonlinear_model_freeze.md` | gate-report/frozen | **G0-B 交付（2026-07-23）**：有效物性律冻结（表格口径：α_eff(T,k) 指数 1.0→5.4 随 k、k1 处 k_eff∝T^1.04、路径 LU 简并、各向同性）+ §5.3 门行（verdict `SCOPED_CANDIDATE`，升级属用户）+ 三个下游输出（1D 挂接/WP1-3 归因/G2 逐 k 物性）。权威 run `20260722T173919Z`（摘要归档 `M5_runs/`）。 | mapping/色散/滤波变化触发 §23 复验重跑；用户 scoped 决策后更新判定行。 |
| `M5_runs/` | run-archive | 权威 run 精选摘要归档（summary/gate_evaluation/run_report/property_table；不含 h5）。当前：`g0_20260722T173919Z/`。 | 新权威 run 归档时追加。 |
| `route_ab_decision_memo.md` | decision-memo | **WP1-5 交付（2026-07-22）**：双物性 1D 消融 + 独立验证（§2.1）+ D-AB-2 逐 QoI 判定 + **用户决策已记录（§7：2026-07-22 批准维持 `ROUTE_B_MAIN + 1D_REAL_AIR_BOUNDING`，升级条件预注册）**。 | G0 实测律挂接后复核 §2/§6；升级条件触发时重开。 |

## 2. 合同规划交付物（尚未创建；落地时移入上表）

按合同 §13/§17，以下文档随对应工作包/Gate 产出（当前均**不存在**，不得引用为已交付）：

| 规划路径 | 归属 |
|---|---|
| `wall_nonlinearity_neutrality_report.md` | G1-W |
| `nonlinear_entry_gate_report.md` | G1a/G1b |
| `harmonic_transfer_report.md` | G2-T/G2-A |
| `harmonic_operator_ablation_report.md` | G2-O |
| `nonlinear_1d_reference_report.md` | G3 |
| `dc_protocol_report.md` | G4a/G4b |
| `wp3_go_nogo_decision.md` | WP3 |
| `nonlinear_production_report.md` | WP4 |

合同 §17 树中另列 `论文一创新点评审与修订实施方案.md`（合同的上游评审文档），未随库提供；如需入库由用户提供原件。

## 3. 使用入口

- 主要入口：`docs/Phase_5/Phase5_instruct_v1.2.md`
- 阶段状态：`docs/Phase_5/Phase5_STATUS.md`
- Gate schema（机器可读）：`verification/nonlinear/phase5_gate_schema.json`
- 配置目录规范：`configs/phase5/README.md`
- 继承授权与硬约束：`docs/Phase_3/M3/M3_Closure_Decision.md` §3/§4
- 全局上下文：`docs/PROJECT_CONTEXT.md`

## 4. 边界

- WP0 合同冻结只是入口；**不等价任何 Gate 通过或生产授权**。当前全部 Gate `NOT_RUN`、`FINAL_PRODUCTION_NOT_CLAIMED`。
- 所有 Phase_5 产出携带继承边界：M3 `SCOPED_ACCEPTED`（幅值 ±5.4%、单频 10 kHz、dx2p6 不换 dx/tau）；M4 `PASSED_WITH_SCOPED_RISK`（非 clear PASS）。
- G1-W 通过前，`pressure_preserving` 热壁只作诊断；未通过 G2-O 前，2f/3f 不得解释为纯物理谐波；H3/30 kHz 为条件项。
- 脚本与报告只能产出 `PASSED/FAILED/SCOPED_CANDIDATE`；`SCOPED_PASSED_BY_USER`、路线 A 启动、PRA 升级均属用户决策。
- 原始运行产物默认留在 `results/phase5/<族>/<run_id>/`（不入库）；只有精选摘要进入本目录（归档约定见 `Phase5_Output_Files_Guide.md`）。
