# docs/Phase_4

**定位**：Phase_4 开边界、控制面与 Kirchhoff 远场外推（M4）的阶段文档目录。
**维护原则**：新增、删除、移动或改变 Phase_4 文档职责时，同步更新本 README、`Phase4_STATUS.md` 和 `Phase4_Output_Files_Guide.md`。

## 1. 文件索引

| 路径 | 类型 | 作用 | 维护触发 |
|---|---|---|---|
| `phase4_instruction_v1.0.md` | contract/frozen | P4-0 冻结合同（2026-07-03）；Phase_4 实作以此为权威。 | Phase_4 合同边界、M4 gate 或阶段顺序变化时更新并记录版本。 |
| `Phase4_STATUS.md` | status | Phase_4 当前状态、验证记录、风险、下一步和更新日志。 | 阶段进度、验证结果、风险或交付物变化时更新。 |
| `Phase4_Output_Files_Guide.md` | output-guide | Phase_4 文件、配置、运行产物和长期归档约定。 | 新增报告、配置、脚本、测试、run 归档或目录结构变化时更新。 |
| `M4/` | report/archive | M4 报告与精选 run 摘要归档目录。当前含 **`P4_1_Open_Boundary_Diagnostic_Report.md`**（P4-1 终态 FAILED 诊断报告，合同 §13.2 交付物：体积注入底板机理链、12 变体否证、4 个 run 记录、路线选项 (a)/(b)/(c)）；`M4_Verification_Report.md`/`M4_Run_Summaries.md` 待主线解锁后产出。 | 新增报告或归档时更新。 |

## 2. 使用入口

- 主要入口：`docs/Phase_4/phase4_instruction_v1.0.md`
- 阶段状态：`docs/Phase_4/Phase4_STATUS.md`
- 启动授权与硬约束：`docs/Phase_3/M3/M3_Closure_Decision.md` §3
- meta/contract 配置：`configs/phase4_m4_smoke.yaml`
- 全局上下文：`docs/PROJECT_CONTEXT.md`

## 3. 边界

- P4-0 合同冻结的存在不表示开边界、控制面、Kirchhoff kernel 已实现，也不表示 M4 已通过。
- **P4-1 终态 FAILED（2026-07-04）**：开边界实现稳定但 `|R|<0.05` 在冻结栈上不可达（体积注入底板，非边界缺陷）；主线阻塞，路线决策见诊断报告 §6；不把该 FAILED 误读为 M2/M3 数值不可信（见 `PROJECT_CONTEXT.md` §3 规则）。
- 所有 Phase_4 产出必须携带 M3 收尾决策授权边界：单频 10 kHz、dx2p6 配置（不换 dx/tau）、幅值 ±5.4% 误差带、远场前置开顶/无反射边界。
- M3 是 `SCOPED_ACCEPTED`、非 clear PASS；M4 通过 ≠ final production pass；Phase_4 不做频扫/功率扫/参数景观（属 Phase_5）。
- Phase_1 只提供近场热参考，不得当作最终 Kirchhoff 远场 SPL 真值。
- x 向周期时不得声明有限宽条带 directivity/边缘辐射认证。
- 原始 HDF5/JSON/图件默认留在 `results/m4/<timestamp>/`，只有精选摘要进入 `docs/Phase_4/M4/`。
